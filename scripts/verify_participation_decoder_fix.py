"""Offline correction replay. Originals and frozen packages are read-only.

python -B -m scripts.verify_participation_decoder_fix --source-root ORIGINAL \
    --audit-root PRIOR_AUDIT --output audit-output/decoder-fix
"""
import argparse
from collections import Counter, defaultdict
import copy
import csv
from dataclasses import asdict
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from scripts import decoder_fix_independent as independent
from src import statsbomb_participation as corrected
from scripts.check_decoder_fix_geometry import normalized
from src.private_five_attribute import aggregate, score_players, freeze_reference
from src.source_reconstruction import appearance_rows, flatten_events, measurements


def main(source, audit, output):
    if output.exists():
        raise ValueError('Use a new output directory; never overwrite evidence')
    output.mkdir(parents=True)
    receipts = {}

    def read(path, expected=None):
        path = Path(path)
        raw = path.read_bytes()
        h = hashlib.sha256(raw).hexdigest()
        if expected is not None:
            assert h == expected, ('source hash mismatch', str(path))
        receipts[str(path.resolve())] = dict(sha256=h, bytes=len(raw))
        return raw

    def js(path, expected=None):
        return json.loads(read(path, expected))

    def lines(path):
        return [json.loads(x) for x in read(path).decode('utf8').splitlines()]

    def table(path):
        return list(csv.DictReader(read(path).decode('utf-8-sig').splitlines()))

    def dump(name, value):
        (output/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str)+'\n', encoding='utf8')

    prior = audit/'audit-output/full-player-audit'
    for name in ('docs/full-player-data-integrity-audit.md', 'docs/data-correction-roadmap.md'):
        read(audit/name)
    historical = table(prior/'appearances.csv')
    aliases = table(prior/'decoder-alias-evidence.csv')
    prior_impacts = table(prior/'hypothetical-decoder-impact.csv')
    prior_players = {int(p['player_id']):p for p in table(prior/'players.csv')}
    prior_hashes = js(prior/'input-hashes.json')
    published = js(Path('frontend/public/data/player-ratings-2015-16-v1.json'))
    public = {int(p['player_id']):p for p in published['players']}
    assert len(public) == len(published['players']) == 691
    pkg = source/'data/derived/private-five-attribute-v2'
    manifest = js(pkg/'manifest.json')
    for name,h in manifest['artifacts'].items():
        read(pkg/name,h)
    for seal in manifest['inputs']['source_seals']:
        read(source/seal['path'],seal['sha256'])
        for name,h in seal['artifacts'].items():read(source/Path(seal['path']).parent/name,h)
    for path,h in manifest['inputs']['measurement_files'].items():read(source/path,h)
    reference = js(pkg/'frozen-reference.json')
    canonical = lines(source/'data/derived/fifth-attribute-private-v1/player-measurements.jsonl')
    allfacts = lines(pkg/'measurement-facts.jsonl')
    facts = {(r['player_id'],r['match_id']):r for r in allfacts if r['player_id'] in public}
    assert len(facts) == len(historical) == 14979
    assert {(int(a['player_id']),int(a['match_id'])) for a in historical} == set(facts)
    oldmeasured = aggregate(canonical, allfacts)
    assert freeze_reference(oldmeasured,input_binding=reference['input_binding']) == reference
    oldscored = {p['player_id']:p for p in score_players(oldmeasured,reference)}
    original_measured = {p['player_id']:p for p in lines(pkg/'player-measurements.jsonl')}
    assert {p['player_id']:p for p in oldmeasured} == original_measured
    changedfacts = copy.deepcopy(facts)
    # Execute the exact baseline source with the same dependencies, without editing it.
    baseline_bytes = subprocess.check_output(['git','show','HEAD:src/statsbomb_participation.py'])
    baseline_path = output/'baseline_statsbomb_participation.py'
    baseline_path.write_bytes(baseline_bytes)
    spec = importlib.util.spec_from_file_location('decoder_fix_baseline',baseline_path)
    baseline = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = baseline
    spec.loader.exec_module(baseline)
    # Memoize the pure exact timestamp parser only in this diagnostic process.
    # Every source event and every validation still executes; no filtering/tolerance.
    baseline._timestamp=lru_cache(maxsize=8192)(baseline._timestamp)
    corrected._timestamp=lru_cache(maxsize=8192)(corrected._timestamp)
    bymatch = defaultdict(list)
    for a in historical:bymatch[int(a['match_id'])].append(a)
    alias_keys = {(int(a['player_id']),int(a['match_id'])) for a in aliases}
    affected = {pid for pid,mid in alias_keys}
    disputed = {(23349,3879602),(40430,3879772),(3577,3879863),(13730,3901259)}
    position_additions=defaultdict(lambda:defaultdict(F))
    changes = []; all_apps = []; recovered = set(); unexpected = []; issues = []
    outside = []; counts = Counter(); seen_uuids = set(); source_names = defaultdict(set)
    dbpath = source/'data/derived/phase3-step2-source-reconstruction-2026-10-27/event-associations.sqlite'
    read(dbpath)
    db = sqlite3.connect(dbpath.as_uri()+'?mode=ro&immutable=1',uri=True)
    delivered = defaultdict(dict)
    for uid,mid,tid,pid,comp,season,typ in db.execute('select id,mid,team,player,competition,season,type from delivered'):
        assert uid not in delivered[mid]
        delivered[mid][uid]=(tid,pid,comp,season,typ)
    db.close()
    print(f'Reference/facts verified; replaying {len(bymatch)} original fixtures',flush=True)
    for n,(mid,apps) in enumerate(sorted(bymatch.items()),1):
        evref = json.loads(apps[0]['evidence'])
        report = js(evref['report_path'],evref['report_sha256'])
        eb,lb,fb = report['artifacts']['events'],report['artifacts']['lineups'],report['fixture_document']
        eraw = read(eb['path'],eb['sha256']); lraw = read(lb['path'],lb['sha256']); fraw = read(fb['path'],fb['sha256'])
        assert hashlib.sha256(eraw).hexdigest() == evref['events_sha256']
        assert hashlib.sha256(lraw).hexdigest() == evref['lineups_sha256']
        events,lineups,fixtures = map(json.loads,(eraw,lraw,fraw))
        fixture = next(f for f in fixtures if f['match_id']==mid)
        ei = {e['id']:e for e in events}
        assert len(ei)==len(events) and not seen_uuids.intersection(ei)
        seen_uuids.update(ei);counts['original_events']+=len(events)
        tids={fixture[s][s+'_id'] for s in ('home_team','away_team')}
        roster={(t['team_id'],p['player_id']):p for t in lineups for p in t['lineup']}
        assert len(roster)==sum(len(t['lineup']) for t in lineups)
        for (tid,pid),p in roster.items():source_names[pid].add(p['player_name'])
        sets=defaultdict(lambda:defaultdict(set)); actor_events=defaultdict(list)
        transition_events=[]
        for e in events:
            uid=e['id'];pid=e.get('player',{}).get('id');tid=e['team']['id']
            assert tid in tids
            if pid is not None:
                assert (tid,pid) in roster and e['player']['name']==roster[tid,pid]['player_name']
                actor_events[tid,pid].append(e)
            if uid in delivered[mid]:
                dt,dp,dc,ds,dy=delivered[mid][uid]
                import unicodedata
                norm=lambda x:' '.join(unicodedata.normalize('NFC',x or '').split())
                assert norm(dp)==norm(e.get('player',{}).get('name'))
                assert corrected._team_name_agrees(tid,e['team']['name'],dt,fixture)
                assert (dc,ds,dy)==(report['competition_name'],report['season_name'],independent.typ(e))
                counts['delivered_uuid_context_checks']+=1
            for attr in independent.selected(e):sets[tid,pid][attr].add(uid)
            if independent.typ(e) in ('Starting XI','Tactical Shift','Substitution','Player On','Player Off') or independent.card(e) in ('Red Card','Second Yellow'):
                transition_events.append(e)
        assert not set(delivered[mid])-set(ei)
        docs = [corrected.SourceDocument(raw,b['source_reference'],'pinned-original') for raw,b in ((fraw,fb),(lraw,lb),(eraw,eb))]
        old = baseline.adapt_match(mid,*(baseline.SourceDocument(d.raw,d.reference,d.revision) for d in docs),clock_document_reference='Pinned original StatsBomb period-local clock; exact 0/45 display offsets')
        new = corrected.adapt_match(mid,*docs,clock_document_reference='Pinned original StatsBomb period-local clock; exact 0/45 display offsets')
        oldres = {r.context.player_id:r for r in old.validate()}
        newres = {r.context.player_id:r for r in new.validate()}
        bounds,bissues,_=independent.boundaries(events,tids)
        # Re-run production event selectors/support for changed fixture inputs.
        production_metrics = None
        if any((int(a['player_id']),mid) in alias_keys for a in apps):
            def jsonable(v):
                if isinstance(v,F):return {'numerator':v.numerator,'denominator':v.denominator}
                if isinstance(v,dict):return {k:jsonable(x) for k,x in v.items()}
                if isinstance(v,(list,tuple)):return [jsonable(x) for x in v]
                return v
            rebuilt=copy.deepcopy(report)
            # Serialization matches the existing review report schema.
            from scripts.source_verification_batch import payload
            def serialize(v):return json.loads(payload(asdict(v) if hasattr(v,'__dataclass_fields__') else [asdict(x) for x in v]))
            rebuilt['players']=[{'player':serialize(p),'validation':serialize(r)} for p,r in zip(new.players,new.validate())]
            rebuilt['boundaries']=serialize(new.boundaries)
            ars=appearance_rows(rebuilt,fixture,lineups)
            frame=flatten_events(events,fixture,ars)
            mm,unknown,_=measurements(frame,ars)
            production_metrics={r['player_id']:r for r in mm}
        for a in apps:
            pid,tid=int(a['player_id']),int(a['team_id']);key=pid,mid;f=facts[key];o,c=oldres[pid],newres[pid]
            assert o.status==a['current_status']
            assert o.elapsed_seconds==independent.rational(f['seconds'])
            r=independent.reconstruct(pid,tid,roster[tid,pid],transition_events,bounds,bissues)
            changed=(o.status,o.elapsed_seconds,o.position_allocation)!=(c.status,c.elapsed_seconds,c.position_allocation)
            # Issue wording may resolve in an appearance that remains rejected.
            if changed and key not in alias_keys:unexpected.append(dict(player_id=pid,match_id=mid))
            if o.status=='STRUCTURALLY_VALID':
                assert o==c
                counts['previously_accepted_unchanged']+=1
            if c.elapsed_seconds is not None:
                assert c.elapsed_seconds==r['seconds']==r['lineup_seconds']
                intervals=[((o.start.period,F(o.start.seconds)),(o.end.period,F(o.end.seconds))) for o in c.observations]
                assert normalized(intervals,bounds)==normalized(r['intervals'],bounds)
                counts['accepted_geometry_checks']+=1
            for attr,m in f['metrics'].items():
                raw=sets[tid,pid][attr]
                assert len(m['numerator_ids'])==len(set(m['numerator_ids'])) and set(m['numerator_ids'])==raw
                if attr=='press_resistance':
                    assert set(m['denominator_ids'])==sets[tid,pid]['press_attempts']
                counts['raw_metric_uuid_set_checks']+=1
            if o.elapsed_seconds is None and c.elapsed_seconds is not None:
                assert key in alias_keys and key not in disputed and not r['issues']
                recovered.add(key);nf=changedfacts[key]
                for allocation in c.position_allocation:position_additions[pid][allocation.position]+=allocation.elapsed_seconds
                nf['seconds']={'numerator':c.elapsed_seconds.numerator,'denominator':c.elapsed_seconds.denominator}
                def within(uid):
                    t=independent.clock(ei[uid]);return t[0] in bounds and bounds[t[0]][0]<=t[1]<=bounds[t[0]][1] and any(x<=t<=y for x,y in r['intervals'])
                for attr,m in nf['metrics'].items():
                    m['seconds']=nf['seconds']
                    if attr=='press_resistance':continue # Existing action-ratio scope is deliberate.
                    comp='progressive_passes' if attr=='progressive_passing' else attr
                    pm=production_metrics[pid]['components'][comp]
                    assert set(pm['event_ids'])==set(m['numerator_ids'])
                    if attr=='progressive_passing':
                        pass_out=[e['id'] for e in actor_events[tid,pid] if independent.typ(e)=='Pass' and not within(e['id'])]
                        reasons=pm['reasons']+(['PASS_OUTSIDE_SUPPORTED_EXPOSURE'] if pass_out else [])
                    else:reasons=pm['reasons']
                    if mid==3879594:reasons+=['PENDING_DELIVERED_FIXTURE_SCOPE']
                    m['supported']=not reasons;m['reasons']=sorted(set(reasons))
                    assert m['supported']==(mid!=3879594 and all(within(u) for u in m['numerator_ids']))
            for e in actor_events[tid,pid]:
                t=independent.clock(e)
                if r['seconds'] is not None and (t[0] not in bounds or not bounds[t[0]][0]<=t[1]<=bounds[t[0]][1] or not any(x<=t<=y for x,y in r['intervals'])):
                    outside.append(dict(player_id=pid,match_id=mid,event_id=e['id'],type=independent.typ(e),clock=t,selected=sorted(independent.selected(e))))
            row=dict(player_id=pid,match_id=mid,team_id=tid,before_status=o.status,after_status=c.status,
                before_seconds=str(o.elapsed_seconds) if o.elapsed_seconds is not None else None,after_seconds=str(c.elapsed_seconds) if c.elapsed_seconds is not None else None,
                production_intervals=[((s.start.period,str(s.start.seconds)),(s.end.period,str(s.end.seconds))) for s in c.observations if s.start and s.end],
                before_minutes=float(o.elapsed_seconds/60) if o.elapsed_seconds is not None else None,after_minutes=float(c.elapsed_seconds/60) if c.elapsed_seconds is not None else None,
                independently_reconstructed_intervals=r['intervals'],independent_seconds=str(r['seconds']),independent_lineup_seconds=str(r['lineup_seconds']),
                independent_issues=r['issues'],remaining_production_issues=[asdict(i) for i in c.issues],source_transition_event_uuids=r['event_ids'],
                original_positions=roster[tid,pid]['positions'],events_path=eb['path'],events_sha256=eb['sha256'],lineups_path=lb['path'],lineups_sha256=lb['sha256'],
                report_path=evref['report_path'],report_sha256=evref['report_sha256'],changed=changed)
            all_apps.append(row)
            if key in alias_keys:changes.append(row)
        if n%25==0:print(f'Replayed {n}/{len(bymatch)} fixtures; recovered {len(recovered)} appearances',flush=True)
    assert not unexpected,unexpected
    for pid,p in public.items():assert p['name'] in source_names[pid]
    # Recompute position dominance with recovered source positional exposure.
    from scripts.verify_bundesliga_readiness import position_group
    canonical_index={p['player_id']:p for p in canonical}
    fine_changes=[]
    for pid in public:
        oldp=canonical_index[pid];pg=defaultdict(F)
        for position,seconds in oldp['position_seconds'].items():pg[position_group(position)]+=independent.rational(seconds)
        for position,seconds in position_additions[pid].items():pg[position_group(position)]+=seconds
        high=max(pg.values());dominant=sorted(k for k,v in pg.items() if v==high and high>0)
        group=('MID' if dominant[0] in ('DM','CM') else dominant[0]) if len(dominant)==1 else None
        assert group==oldp['comparison_group'],(pid,group,oldp['comparison_group'])
        if dominant!=oldp['dominant_fine_groups']:fine_changes.append(dict(player_id=pid,before=oldp['dominant_fine_groups'],after=dominant))
    assert all(new['after_seconds'] is None for new in changes if (new['player_id'],new['match_id']) in disputed)
    # Re-run approved production aggregation/scoring; independently reproduce every
    # exact input, percentile, Formula B result and eligibility predicate below.
    newfacts=[changedfacts.get((f['player_id'],f['match_id']),f) for f in allfacts]
    measured=aggregate(canonical,newfacts)
    scored={p['player_id']:p for p in score_players(measured,reference)}
    bypid=defaultdict(list)
    for key,f in facts.items():bypid[key[0]].append(key)
    population=[];metric_deltas=Counter();prior_discrepancies=[]
    def calculate(pid,fs,production):
        known=sum((independent.rational(f['seconds']) for f in fs if f['seconds'] is not None),F(0))/60
        attrs={};eligible=True;membership=True
        for attr in independent.ATTRS:
            good=[f for f in fs if f['metrics'][attr]['supported']]
            secs=sum((independent.rational(f['metrics'][attr]['seconds']) for f in good if f['metrics'][attr]['seconds'] is not None),F(0))
            num=sum(len(f['metrics'][attr]['numerator_ids']) for f in good)
            attempts=sum(len(f['metrics'][attr]['denominator_ids']) for f in good) if attr=='press_resistance' else None
            val=F(100*num,attempts) if attempts else F(num*5400,1)/secs if attr!='press_resistance' and secs else None
            pool=reference['pools'][production['comparison_group']][attr]
            rating,pct=independent.score(val,known if attr=='press_resistance' else secs/60,known,production['limited_data'],pool)
            pm=production['attributes'][attr]
            assert independent.rational(pm['exact_value'])==val and pm['experimental_rating']==rating and pm['percentile']==pct
            member=pid in pool['member_ids'];membership &= member
            eligible &= bool(val is not None and len(good)==len(fs) and all(f['seconds'] is not None and independent.rational(f['seconds'])>0 for f in fs) and known>=900 and not production['limited_data'] and (attr=='press_resistance' or secs/60>=900) and (attr!='press_resistance' or attempts>=40) and all(f['match_id']!=3879594 for f in fs))
            attrs[attr]=dict(rating=rating,percentile=pct,exact_value=str(val) if val is not None else None,numerator=num,attempts=attempts,supported_minutes=float(secs/60),supported_seconds=str(secs),supported_match_ids=[f['match_id'] for f in good],excluded=[dict(match_id=f['match_id'],reasons=f['metrics'][attr]['reasons']) for f in fs if not f['metrics'][attr]['supported']],frozen_member=member)
        return dict(minutes=float(known),exact_minutes=str(known),attributes=attrs,overall=independent.overall([m['rating'] for m in attrs.values()]),eligible=bool(eligible and membership),complete_except_membership=bool(eligible),frozen_member=bool(membership))
    for pid,p in sorted(public.items()):
        keys=sorted(bypid[pid]);before=calculate(pid,[facts[k] for k in keys],oldscored[pid]);after=calculate(pid,[changedfacts[k] for k in keys],scored[pid])
        for attr,m in before['attributes'].items():
            pub=p['attributes'][independent.PUBLIC.get(attr,attr)]
            assert (pub['rating'],pub['percentile'])==(m['rating'],m['percentile'])
        assert before['overall']==p['ovr']['value']
        assert before['eligible']==p['ovr']['eligible']
        assert before['eligible']==json.loads(prior_players[pid]['current_ranking_status'].lower())
        changed_attrs=[a for a in independent.ATTRS if before['attributes'][a]!=after['attributes'][a]]
        for attr in changed_attrs:metric_deltas[attr]+=1
        numerical_attrs=[a for a in independent.ATTRS if before['attributes'][a]['rating']!=after['attributes'][a]['rating']]
        if pid not in affected:assert before==after
        reasons=[dict(match_id=a['match_id'],issues=a['remaining_production_issues']) for a in all_apps if a['player_id']==pid and a['after_seconds'] is None]
        population.append(dict(player_id=pid,season='2015/2016',name=p.get('name'),affected_by_alias=pid in affected,
            appearance_count=len(keys),recovered_appearance_ids=[mid for pp,mid in sorted(recovered) if pp==pid],
            before_minutes=before['minutes'],after_minutes=after['minutes'],added_minutes=after['minutes']-before['minutes'],
            current_published_rating=before['overall'],corrected_diagnostic_rating=after['overall'],overall_delta=after['overall']-before['overall'] if before['overall'] is not None and after['overall'] is not None else None,
            changed_input_attributes=changed_attrs,changed_rating_attributes=numerical_attrs,before_attributes=before['attributes'],after_attributes=after['attributes'],
            current_eligible=before['eligible'],diagnostic_eligible=after['eligible'],diagnostic_complete_except_membership=after['complete_except_membership'],frozen_member=after['frozen_member'],remaining_exclusions=reasons,
            verification='CONFIRMED_CORRECTION' if changed_attrs else 'REMAINING_SOURCE_CONFLICT' if reasons else 'UNCHANGED_VERIFIED_OBSERVED_SCOPE',
            prior_audit_classification=prior_players[pid]['classification']))
    for old in prior_impacts:
        now=next(p for p in population if p['player_id']==int(old['player_id']))
        if (float(old['diagnostic_overall']) if old['diagnostic_overall'] else None)!=now['corrected_diagnostic_rating']:prior_discrepancies.append(now['player_id'])
    assert not prior_discrepancies,prior_discrepancies
    impacted=[p for p in population if p['affected_by_alias']]
    numeric=[p for p in population if p['overall_delta'] is not None and p['overall_delta']!=0]
    summary=dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),published_players=len(population),appearances=len(all_apps),fixtures=len(bymatch),
        alias_affected_appearances=len(changes),alias_affected_players=len(impacted),recovered_appearances=len(recovered),players_with_added_minutes=len({p for p,m in recovered}),
        players_with_changed_attribute_inputs=sum(bool(p['changed_input_attributes']) for p in population),players_with_changed_attribute_ratings=sum(bool(p['changed_rating_attributes']) for p in population),
        players_with_changed_overall=len(numeric),attribute_input_change_counts=metric_deltas,largest_positive=max(numeric,key=lambda p:p['overall_delta'])['player_id'],largest_negative=min(numeric,key=lambda p:p['overall_delta'])['player_id'],
        eligibility_changes=sum(p['current_eligible']!=p['diagnostic_eligible'] for p in population),newly_complete_without_frozen_membership=sum(not p['current_eligible'] and p['diagnostic_complete_except_membership'] and not p['frozen_member'] for p in population),
        unchanged_other_players=len(public)-len(affected),unexpected_changes=unexpected,prior_diagnostic_rating_discrepancies=prior_discrepancies,
        disputed_appearances=[a for a in changes if (a['player_id'],a['match_id']) in disputed],source_checks=counts,outside_verified_participation_events=len(outside),
        canonical_id_name_checks=len(public),comparison_group_changes=0,dominant_fine_group_changes=fine_changes,original_upstream_reference_candidates_checked=len(oldmeasured),frozen_reference_semantic_sha256=reference['sha256'],publication_authorized=False)
    independent.write_csv(output/'appearance-comparison.csv',changes)
    independent.write_csv(output/'all-appearance-comparison.csv',all_apps)
    independent.write_csv(output/'player-impact.csv',impacted)
    independent.write_csv(output/'full-population-comparison.csv',population)
    independent.write_csv(output/'events-outside-participation.csv',outside)
    # Verify every original receipt consumed by this replay against the earlier
    # pinned receipts, where the audit recorded it; originals remain unmodified.
    checks=0
    for path,receipt in list(receipts.items()):
        if path in prior_hashes:
            assert receipt['sha256']==prior_hashes[path]['sha256'];checks+=1
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==receipt['sha256']
    summary['prior_input_receipts_reverified']=checks
    for path in (Path('src/statsbomb_participation.py'),Path('src/independent_source_checks.py'),Path(__file__),Path(independent.__file__),Path('scripts/check_decoder_fix_geometry.py')):
        read(path)
    dump('summary.json',summary);dump('input-hashes.json',receipts)
    dump('output-hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
    print(json.dumps({k:v for k,v in summary.items() if k!='disputed_appearances'},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--audit-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.source_root.resolve(),a.audit_root.resolve(),a.output.resolve())
