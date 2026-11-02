"""Offline Batch 2B production replay, independent source and frozen-score checks.

Run from the isolated checkout with retained sibling source/audit workspaces.
Refuses existing output. Does not publish, fit references or alter source bytes.
"""
import copy
import csv
from collections import Counter,defaultdict
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
import unicodedata

from scripts import decoder_fix_independent as raw
from scripts import off_field_card_independent as independent
from scripts.source_verification_batch import payload
from src import statsbomb_participation as corrected
from src.source_reconstruction import appearance_rows,flatten_events,measurements
from src.private_five_attribute import aggregate,score_players,validate_reference
from src.private_ovr_formula_c import exclusion_reasons
from src.provisional_ovr import formula_b


def main():
    root=Path.cwd();source=root.parent/'Soccer-Impact-Engine-Index'
    audit=root.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit'
    b1=root.parent/'Soccer-Impact-Engine-Index-participation-decoder-fix'
    reconciliation=root.parent/'Soccer-Impact-Engine-Index-source-evidence-reconciliation'
    out=root/'audit-output/source-backed-entry-fix'
    batch2a=root.parent/'Soccer-Impact-Engine-Index-off-field-card-fix'
    capps={(int(a['player_id']),int(a['match_id'])):a for a in csv.DictReader((batch2a/'audit-output/off-field-card-fix/all-appearance-comparison.csv').open(encoding='utf-8-sig'))}
    cpopulation={int(p['player_id']):p for p in csv.DictReader((batch2a/'audit-output/off-field-card-fix/full-population-comparison.csv').open(encoding='utf-8-sig'))}
    if out.exists():raise ValueError('Preserve prior evidence; use a fresh output directory')
    out.mkdir(parents=True);receipts={};checks=Counter();preserved={}
    def bind(path,expected=None):
        path=Path(path).resolve()
        with path.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
        if expected:assert h==expected,str(path)
        receipts[str(path)]=dict(sha256=h,bytes=path.stat().st_size);return h
    def read(path,expected=None):
        bind(path,expected);return Path(path).read_bytes()
    def js(path,expected=None):return json.loads(read(path,expected))
    def table(path):return list(csv.DictReader(read(path).decode('utf-8-sig').splitlines()))
    def lines(path):return [json.loads(x) for x in read(path).decode('utf8').splitlines()]
    def dump(name,value):(out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf8')
    def serialize(value):return json.loads(payload(asdict(value) if hasattr(value,'__dataclass_fields__') else [asdict(x) for x in value]))
    for path in (reconciliation/'docs/source-evidence-reconciliation-report.md',reconciliation/'docs/source-reconciliation-correction-plan.md',b1/'docs/participation-decoder-fix-report.md'):read(path)
    for workspace,rel in ((batch2a,'audit-output/off-field-card-fix/output-hashes.json'),(audit,'audit-output/full-player-audit/output-hashes.json'),(b1,'audit-output/decoder-fix/output-hashes.json'),(reconciliation,'audit-output/source-reconciliation/output-hashes.json')):
        for name,h in js(workspace/rel).items():
            path=workspace/name if (workspace/name).is_file() else workspace/Path(rel).parent/name
            bind(path,h);preserved[str(path.resolve())]=h
    history=table(audit/'audit-output/full-player-audit/appearances.csv')
    b1apps={(int(a['player_id']),int(a['match_id'])):a for a in table(b1/'audit-output/decoder-fix/all-appearance-comparison.csv')}
    b1population={int(p['player_id']):p for p in table(b1/'audit-output/decoder-fix/full-population-comparison.csv')}
    prior_impact={int(p['player_id']):p for p in table(reconciliation/'audit-output/source-reconciliation/full-population-comparison.csv')}
    published=js(root/'frontend/public/data/player-ratings-2015-16-v1.json')
    public={int(p['player_id']):p for p in published['players']};assert len(public)==len(published['players'])==691
    pkg=source/'data/derived/private-five-attribute-v2';manifest=js(pkg/'manifest.json')
    for name,h in manifest['artifacts'].items():bind(pkg/name,h)
    reference=validate_reference(js(pkg/'frozen-reference.json'))
    canonical=lines(source/'data/derived/fifth-attribute-private-v1/player-measurements.jsonl')
    original_facts=lines(pkg/'measurement-facts.jsonl')
    originals={(f['player_id'],f['match_id']):f for f in original_facts}
    baseline_facts=copy.deepcopy(original_facts);baseline_index={(f['player_id'],f['match_id']):f for f in baseline_facts}
    pending={};removed=set();changed_keys=set();allapps=[];changes=[];cards=[];positions_b1=defaultdict(lambda:defaultdict(F));positions_new=defaultdict(lambda:defaultdict(F))
    # Execute merged baseline code without modifying the checkout or its evidence.
    baseline_path=out/'merged_baseline_statsbomb_participation.py'
    baseline_path.write_bytes(subprocess.check_output(['git','show','HEAD:src/statsbomb_participation.py']))
    spec=importlib.util.spec_from_file_location('merged_card_fix_baseline',baseline_path);baseline=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=baseline;spec.loader.exec_module(baseline)
    for module in (baseline,corrected):
        module._timestamp=lru_cache(maxsize=8192)(module._timestamp)
        original_check=module._check_original_transitions
        def indexed_check(tid,pid,observations,events,reference,check=original_check):
            # Only omit events that cannot enter any branch of this unchanged
            # source-check function. Off-field proofs still see ALL raw events.
            relevant=[e for e in events if e['team']['id']==tid and (raw.typ(e) in ('Starting XI','Tactical Shift')
                or e.get('player',{}).get('id')==pid and (raw.typ(e) in ('Player On','Player Off','Substitution') or raw.card(e) in ('Red Card','Second Yellow'))
                or raw.typ(e)=='Substitution' and e['substitution']['replacement']['id']==pid)]
            return check(tid,pid,observations,relevant,reference)
        module._check_original_transitions=indexed_check
    bymatch=defaultdict(list)
    for a in history:bymatch[int(a['match_id'])].append(a)
    assert len(history)==len(b1apps)==14979 and len(bymatch)==1551
    dbpath=source/'data/derived/phase3-step2-source-reconstruction-2026-10-27/event-associations.sqlite';bind(dbpath)
    db=sqlite3.connect(dbpath.as_uri()+'?mode=ro&immutable=1',uri=True)
    # Read the existing match index one fixture at a time. Original DB is read-only.
    seen=sqlite3.connect(out/'uuid-conservation.sqlite')
    seen.execute('create table seen (uuid text primary key) without rowid')
    names=defaultdict(set)
    expected_published={(4817,3754026),(3605,3754047),(3644,3754047),(5540,3754080),(24149,3825640),(6771,3825684),(3118,3829502),(7771,3879611),(7461,3879666),(3421,3900560)}
    expected_all=expected_published
    genuine={(5201,267533),(5201,3825879),(3608,3754058),(4506,3829490),(23349,3879602),(40430,3879772),(3577,3879863),(13730,3901259),(3414,3829490)}
    raw_card_ids=set();retained_card_ids=set()
    for n,(mid,apps) in enumerate(sorted(bymatch.items()),1):
        delivered={}
        for uid,tid,pid,comp,season,typ in db.execute('select id,team,player,competition,season,type from delivered where mid=?',(mid,)):
            assert uid not in delivered
            delivered[uid]=(tid,pid,comp,season,typ)
        lead=json.loads(apps[0]['evidence']);report=js(lead['report_path'],lead['report_sha256'])
        fb,lb,eb=report['fixture_document'],report['artifacts']['lineups'],report['artifacts']['events']
        bindings=(fb,lb,eb);bytesets=[read(b['path'],b['sha256']) for b in bindings]
        fixtures,lineups,events=map(json.loads,bytesets);fixture=next(f for f in fixtures if f['match_id']==mid)
        roster={(t['team_id'],p['player_id']):p for t in lineups for p in t['lineup']}
        assert len(roster)==sum(len(t['lineup']) for t in lineups)
        ei={e['id']:e for e in events};assert len(ei)==len(events)
        # A disk-backed primary key rejects duplicates across all fixtures.
        seen.executemany('insert into seen values (?)',((uid,) for uid in ei))
        seen.commit();checks['original_events']+=len(events)
        selected=defaultdict(lambda:defaultdict(set));actors=defaultdict(list)
        for (tid,pid),p in roster.items():names[pid].add(p['player_name'])
        for e in events:
            uid=e['id'];tid=e['team']['id'];pid=e.get('player',{}).get('id')
            if pid is not None:
                assert roster[tid,pid]['player_name']==e['player']['name'];actors[tid,pid].append(e)
            if raw.card(e) in ('Red Card','Second Yellow'):
                assert uid not in raw_card_ids;raw_card_ids.add(uid)
            if uid in delivered:
                dt,dp,dc,ds,dy=delivered[uid];norm=lambda v:' '.join(unicodedata.normalize('NFC',v or '').split())
                assert norm(dp)==norm(e.get('player',{}).get('name'))
                assert corrected._team_name_agrees(tid,e['team']['name'],dt,fixture)
                assert (dc,ds,dy)==(report['competition_name'],report['season_name'],raw.typ(e));checks['delivered_uuid_contexts']+=1
            for attr in raw.selected(e):selected[tid,pid][attr].add(uid)
        assert not set(delivered)-set(ei)
        old=baseline.adapt_match(mid,*(baseline.SourceDocument(b,c['source_reference'],'pinned-original') for b,c in zip(bytesets,bindings)),clock_document_reference='Pinned exact source period-local clocks; 0/45 offsets')
        new=corrected.adapt_match(mid,*(corrected.SourceDocument(b,c['source_reference'],'pinned-original') for b,c in zip(bytesets,bindings)),clock_document_reference='Pinned exact source period-local clocks; 0/45 offsets')
        oldr={r.context.player_id:r for r in old.validate()};newr={r.context.player_id:r for r in new.validate()}
        oldp={p.context.player_id:p for p in old.players};newp={p.context.player_id:p for p in new.players}
        assert set(oldp)==set(newp)=={p for t,p in roster}
        bounds,bissues,_=raw.boundaries(events,{t['team_id'] for t in lineups})
        transitions=[e for e in events if raw.typ(e) in ('Starting XI','Tactical Shift','Substitution','Player On','Player Off') or raw.card(e) in ('Red Card','Second Yellow')]
        source_oracles={};fixture_updates={}
        for pid,p in newp.items():
            o=oldp[pid];r=newr[pid];before=oldr[pid];key=pid,mid
            assert (p.context,p.team_id,p.player_name,p.raw_positions)==(o.context,o.team_id,o.player_name,o.raw_positions)
            assert [asdict(d) for d in p.off_field_discipline]==[asdict(d) for d in o.off_field_discipline]
            actual_change=before!=r
            if not p.reconstructed_entries:
                assert not actual_change and p.observations==o.observations and [asdict(c) for c in p.source_checks]==[asdict(c) for c in o.source_checks]
                continue
            changed_keys.add(key)
            assert actual_change and (key in expected_all or pid not in public),('unexpected published source change',key)
            assert len(p.reconstructed_entries)==1
            # Geometry, allocation labels and original provenance stay identical.
            assert len(p.observations)==len(o.observations)
            for i,(ns,os) in enumerate(zip(p.observations,o.observations)):
                assert (ns.start.period,ns.start.seconds,ns.end,ns.position,ns.exit_kind,ns.evidence_refs,ns.provenance_refs)==(os.start.period,os.start.seconds,os.end,os.position,os.exit_kind,os.evidence_refs,os.provenance_refs)
                if i:assert ns==os
            oracle=independent.reconstruct(pid,p.team_id,roster[p.team_id,pid],events,bounds,bissues,transition_events=transitions);source_oracles[pid]=oracle
            assert not oracle['issues']
            proof=p.reconstructed_entries[0];entry=ei[proof.entry_ref.rsplit('/',1)[-1]];shift=ei[proof.shift_ref.rsplit('/',1)[-1]]
            assert raw.clock(entry)==raw.clock(shift)
            cards.append(dict(player_id=pid,match_id=mid,published=pid in public,team_id=p.team_id,entry_id=entry['id'],entry_type=raw.typ(entry),entry_period=entry['period'],entry_timestamp=entry['timestamp'],entry_index=entry.get('index'),shift_id=shift['id'],shift_period=shift['period'],shift_timestamp=shift['timestamp'],shift_index=shift.get('index'),proof=asdict(proof),independent=oracle,original_positions=roster[p.team_id,pid]['positions'],original_entry={k:v for k,v in entry.items() if k!='_audit_clock'},original_shift={k:v for k,v in shift.items() if k!='_audit_clock'},events_path=eb['path'],events_sha256=eb['sha256'],lineups_path=lb['path'],lineups_sha256=lb['sha256'],fixture_path=fb['path'],fixture_sha256=fb['sha256']))
            oldactive=bool(o.observations or o.source_checks);active=bool(p.observations or p.source_checks)
            changes.append(dict(player_id=pid,name=p.player_name,match_id=mid,team_id=p.team_id,published=pid in public,before_active=oldactive,after_active=active,before_status=before.status,after_status=r.status if active else 'BENCH_NO_ASSERTED_APPEARANCE',before_seconds=str(before.elapsed_seconds) if before.elapsed_seconds is not None else None,after_seconds=str(r.elapsed_seconds) if r.elapsed_seconds is not None else None,after_minutes=float(r.elapsed_seconds/60) if r.elapsed_seconds is not None else None,old_source_checks=[asdict(c) for c in o.source_checks],new_source_checks=[asdict(c) for c in p.source_checks],reconstructed_entries=[asdict(c) for c in p.reconstructed_entries],independent=oracle,original_positions=roster[p.team_id,pid]['positions'],events_path=eb['path'],events_sha256=eb['sha256'],lineups_path=lb['path'],lineups_sha256=lb['sha256'],fixture_path=fb['path'],fixture_sha256=fb['sha256'],report_path=lead['report_path'],report_sha256=lead['report_sha256']))
            if not active:
                assert not p.observations and not p.source_checks and not oracle['active'] and r.elapsed_seconds is None
                if pid in public:removed.add(key)
            else:
                assert r.elapsed_seconds==oracle['seconds']==oracle['lineup_seconds']
                assert independent.union(oracle['intervals'],bounds)==independent.union(oracle['lineup_intervals'],bounds)
                if pid in public:pending[key]=copy.deepcopy(originals[key]);fixture_updates[pid]=(r,oracle,pending[key])
        for a in apps:
            pid,tid=int(a['player_id']),int(a['team_id']);key=pid,mid;o,c=oldr[pid],newr[pid];sealed=capps[key];f=originals[key]
            assert (o.status==sealed['corrected_status'] or key==(26023,3825670) and sealed['corrected_status']=='BENCH_NO_ASSERTED_APPEARANCE') and (str(o.elapsed_seconds) if o.elapsed_seconds is not None else '')==sealed['corrected_seconds']
            issue_fields=[dict(status=i.status,code=i.code,observation_ids=list(i.observation_ids)) for i in o.issues]
            assert issue_fields==json.loads(sealed['corrected_issues']),('baseline issue differences',key,issue_fields,sealed['corrected_issues'])
            checks['merged_baseline_decisions_reproduced']+=1
            for attr,m in f['metrics'].items():
                assert set(m['numerator_ids'])==selected[tid,pid][attr] and len(m['numerator_ids'])==len(set(m['numerator_ids']))
                if attr=='press_resistance':assert set(m['denominator_ids'])==selected[tid,pid]['press_attempts']
                checks['raw_metric_uuid_sets']+=1
            oracle=source_oracles.get(pid)
            if oracle is None:oracle=independent.reconstruct(pid,tid,roster[tid,pid],events,bounds,bissues,transition_events=transitions)
            if o.elapsed_seconds is not None:
                assert o==c;checks['previously_accepted_unchanged']+=1
            if c.elapsed_seconds is not None:
                assert c.elapsed_seconds==oracle['seconds']==oracle['lineup_seconds']
                intervals=[((s.start.period,F(s.start.seconds)),(s.end.period,F(s.end.seconds))) for s in c.observations]
                assert independent.union(intervals,bounds)==independent.union(oracle['intervals'],bounds)==independent.union(oracle['lineup_intervals'],bounds)
                checks['corrected_exact_interval_unions']+=1
            if key in genuine:assert o==c and c.elapsed_seconds is None;checks['priority_conflicts_preserved']+=1
            if f['seconds'] is None and o.elapsed_seconds is not None:
                assert b1apps[key]['changed']=='True' or key==(3256,3900519)
                checks['batch1_recoveries_preserved' if key!=(3256,3900519) else 'batch2a_recovery_preserved']+=1
                fixture_updates[pid]=(o,oracle,baseline_index[key])
                for allocation in o.position_allocation:positions_b1[pid][allocation.position]+=allocation.elapsed_seconds
            if key in pending:
                for allocation in c.position_allocation:positions_new[pid][allocation.position]+=allocation.elapsed_seconds
            if key in removed:
                assert all(not m['numerator_ids'] and not (m['denominator_ids'] or []) for m in f['metrics'].values())
            if key not in expected_published:assert o==c
            allapps.append(dict(player_id=pid,match_id=mid,team_id=tid,v1_seconds=str(raw.rational(f['seconds'])) if f['seconds'] is not None else None,baseline_status=o.status,baseline_seconds=str(o.elapsed_seconds) if o.elapsed_seconds is not None else None,corrected_status=c.status if key not in removed else 'BENCH_NO_ASSERTED_APPEARANCE',corrected_seconds=str(c.elapsed_seconds) if c.elapsed_seconds is not None else None,removed_nonappearance=key in removed,baseline_issues=[asdict(i) for i in o.issues],corrected_issues=[asdict(i) for i in c.issues],off_field_discipline=[asdict(d) for d in newp[pid].off_field_discipline]))
        if fixture_updates or any((pid,mid) in changed_keys for pid in newp):
            rebuilt=copy.deepcopy(report);rebuilt['players']=[dict(player=serialize(p),validation=serialize(newr[p.context.player_id])) for p in new.players];rebuilt['boundaries']=serialize(new.boundaries)
            ars=appearance_rows(rebuilt,fixture,lineups);frame=flatten_events(events,fixture,ars);mm,unknown,_=measurements(frame,ars);metric_index={m['player_id']:m for m in mm}
            for c in changes:
                if c['match_id']==mid:
                    ar=next(a for a in ars if a['player_id']==c['player_id']);assert ar['active_appearance']==c['after_active']
                    assert ar['reconstructed_entries'];checks['source_reconstruction_entry_decisions']+=1
                    if not c['after_active']:assert ar['supported_minutes'] is None and ar['validated_elapsed_seconds'] is None
            for pid,(r,oracle,nf) in fixture_updates.items():
                secs=r.elapsed_seconds;nf['seconds']=dict(numerator=secs.numerator,denominator=secs.denominator);tid=newp[pid].team_id
                def within(uid):
                    t=raw.clock(ei[uid]);return t[0] in bounds and bounds[t[0]][0]<=t[1]<=bounds[t[0]][1] and any(a<=t<=b for a,b in oracle['intervals'])
                for attr,m in nf['metrics'].items():
                    m['seconds']=nf['seconds']
                    if attr=='press_resistance':continue
                    pm=metric_index[pid]['components']['progressive_passes' if attr=='progressive_passing' else attr]
                    assert set(pm['event_ids'])==set(m['numerator_ids'])
                    reasons=list(pm['reasons'])
                    if attr=='progressive_passing' and any(not within(e['id']) for e in actors[tid,pid] if raw.typ(e)=='Pass'):reasons.append('PASS_OUTSIDE_SUPPORTED_EXPOSURE')
                    if mid==3879594:reasons.append('PENDING_DELIVERED_FIXTURE_SCOPE')
                    assert (not pm['unaligned_event_ids'])==all(within(uid) for uid in m['numerator_ids'])
                    m['reasons']=sorted(set(reasons));m['supported']=not reasons
        if n%50==0:print(f'Replayed {n}/{len(bymatch)} fixtures; source changes {len(changed_keys)}; recovered {len(pending)}; removed {len(removed)}',flush=True)
    assert seen.execute('select count(*) from seen').fetchone()[0]==checks['original_events']
    seen.close();db.close()
    assert {key for key in changed_keys if key[0] in public}==expected_published and not removed and set(pending)==expected_published
    assert len(allapps)==len({(a['player_id'],a['match_id']) for a in allapps})==14979
    assert checks['batch1_recoveries_preserved']==91 and checks['previously_accepted_unchanged']==14537
    assert checks['priority_conflicts_preserved']==9 and sum(c['published'] for c in cards)==10
    assert checks['batch2a_recovery_preserved']==1
    removed.add((26023,3825670))
    for pid,p in public.items():assert p['name'] in names[pid]
    # Persist source evidence before numerical checks; a failed run cannot be
    # mistaken for a completed release and never overwrites source or old audits.
    raw.write_csv(out/'appearance-comparison.csv',changes);raw.write_csv(out/'entry-evidence.csv',cards);raw.write_csv(out/'all-appearance-comparison.csv',allapps)
    batch1_facts=copy.deepcopy(baseline_facts)
    baseline_facts=[f for f in baseline_facts if (f['player_id'],f['match_id']) not in removed]
    dump('baseline-diagnostic-facts.json',baseline_facts);dump('pending-corrected-facts.json',list(pending.values()));dump('input-hashes.json',receipts)
    corrected_facts=[copy.deepcopy(pending.get((f['player_id'],f['match_id']),f)) for f in baseline_facts if (f['player_id'],f['match_id']) not in removed]
    corrected_canonical=copy.deepcopy(canonical)
    for p in corrected_canonical:p['observed_match_ids']=[mid for mid in p['observed_match_ids'] if (p['player_id'],mid) not in removed]
    original_profiles={p['player_id']:p for p in score_players(aggregate(canonical,original_facts),reference)}
    baseline_profiles={p['player_id']:p for p in score_players(aggregate(corrected_canonical,baseline_facts),reference)}
    batch1_facts=[copy.deepcopy(originals[(f['player_id'],f['match_id'])] if (f['player_id'],f['match_id'])==(3256,3900519) else f) for f in batch1_facts]
    batch1_profiles={p['player_id']:p for p in score_players(aggregate(canonical,batch1_facts),reference)}
    corrected_profiles={p['player_id']:p for p in score_players(aggregate(corrected_canonical,corrected_facts),reference)}
    from scripts.verify_bundesliga_readiness import position_group
    canonical_index={p['player_id']:p for p in canonical};fine_changes=[]
    for pid in public:
        groups=defaultdict(F)
        for position,seconds in canonical_index[pid]['position_seconds'].items():groups[position_group(position)]+=raw.rational(seconds)
        for additions in (positions_b1[pid],positions_new[pid]):
            for position,seconds in additions.items():groups[position_group(position)]+=seconds
        high=max(groups.values());fine=sorted(g for g,s in groups.items() if s==high and high>0)
        group=('MID' if fine[0] in ('CM','DM') else fine[0]) if len(fine)==1 else None
        assert group==canonical_index[pid]['comparison_group']
        if fine!=canonical_index[pid]['dominant_fine_groups']:fine_changes.append(dict(player_id=pid,before=canonical_index[pid]['dominant_fine_groups'],after=fine))
    def calculate(pid,fs,p):
        fs=sorted(fs,key=lambda f:f['match_id']);known=sum((raw.rational(f['seconds']) for f in fs if f['seconds'] is not None),F(0))/60;attrs={};eligible=True
        positive=bool(fs) and all(f['seconds'] is not None and raw.rational(f['seconds'])>0 for f in fs)
        for attr in raw.ATTRS:
            good=[f for f in fs if f['metrics'][attr]['supported']]
            secs=sum((raw.rational(f['metrics'][attr]['seconds']) for f in good if f['metrics'][attr]['seconds'] is not None),F(0))
            num=sum(len(f['metrics'][attr]['numerator_ids']) for f in good)
            attempts=sum(len(f['metrics'][attr]['denominator_ids']) for f in good) if attr=='press_resistance' else None
            value=F(100*num,attempts) if attempts else F(num*5400)/secs if attr!='press_resistance' and secs else None
            pool=reference['pools'][p['comparison_group']][attr]
            rating,pct=raw.score(value,known if attr=='press_resistance' else secs/60,known,p['limited_data'],pool)
            approved=p['attributes'][attr]
            assert raw.rational(approved['exact_value'])==value and approved['experimental_rating']==rating and approved['percentile']==pct
            member=pid in pool['member_ids']
            eligible &= bool(member and rating is not None and positive and known>=900 and secs/60==known and secs>=54000 and len(good)==len(fs) and not p['limited_data'] and (attr!='press_resistance' or attempts>=40) and all(f['match_id']!=3879594 for f in fs))
            attrs[attr]=dict(numerator=num,attempts=attempts,exact_value=str(value) if value is not None else None,supported_seconds=str(secs),supported_minutes=float(secs/60),supported_match_ids=[f['match_id'] for f in good],excluded=[dict(match_id=f['match_id'],reasons=f['metrics'][attr]['reasons']) for f in fs if not f['metrics'][attr]['supported']],rating=rating,percentile=pct,frozen_member=member)
        overall=raw.overall([m['rating'] for m in attrs.values()]);assert overall==formula_b([m['rating'] for m in attrs.values()])
        reasons=exclusion_reasons(p,reference);assert eligible==(not reasons)
        checks['independent_formula_b_comparisons']+=1;checks['independent_attribute_comparisons']+=5;checks['independent_eligibility_comparisons']+=1
        return dict(appearance_ids=[f['match_id'] for f in fs],supported_appearance_ids=[f['match_id'] for f in fs if f['seconds'] is not None],exact_supported_minutes=str(known),supported_minutes=float(known),attributes=attrs,overall=overall,eligible=eligible,exclusion_reasons=reasons)
    facts_by=[]
    for fs in (original_facts,batch1_facts,baseline_facts,corrected_facts):
        index=defaultdict(list)
        for f in fs:index[f['player_id']].append(f)
        facts_by.append(index)
    population=[]
    for pid,pub in sorted(public.items()):
        original=calculate(pid,facts_by[0][pid],original_profiles[pid]);batch1=calculate(pid,facts_by[1][pid],batch1_profiles[pid]);before=calculate(pid,facts_by[2][pid],baseline_profiles[pid]);after=calculate(pid,facts_by[3][pid],corrected_profiles[pid])
        assert batch1==json.loads(cpopulation[pid]['merged_batch1'])
        assert before==json.loads(cpopulation[pid]['corrected_batch2a'])
        for attr,m in original['attributes'].items():assert (m['rating'],m['percentile'])==(pub['attributes'][raw.PUBLIC.get(attr,attr)]['rating'],pub['attributes'][raw.PUBLIC.get(attr,attr)]['percentile'])
        assert (original['overall'],original['eligible'])==(pub['ovr']['value'],pub['ovr']['eligible'])
        if pid not in {p for p,m in expected_published}:assert before==after
        population.append(dict(player_id=pid,name=pub['name'],season='2015/2016',affected_by_batch2b=pid in {p for p,m in expected_published},v1=original,merged_batch1=batch1,corrected_batch2a=before,proposed_batch2b=after,added_supported_minutes=float(F(after['exact_supported_minutes'])-F(before['exact_supported_minutes'])),overall_delta=after['overall']-before['overall'] if after['overall'] is not None and before['overall'] is not None else None,eligibility_changed=before['eligible']!=after['eligible'],publication_authorized=False))
    assert len(population)==691
    for path,r in receipts.items():
        with Path(path).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==r['sha256'],path
    for path,h in preserved.items():
        with Path(path).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==h,path
    for path in (root/'src/statsbomb_participation.py',root/'src/source_reconstruction.py',root/'src/participation_intervals.py',root/'src/identity.py',root/'scripts/decoder_fix_independent.py',root/'scripts/off_field_card_independent.py',root/'tests/test_off_field_cards.py',root/'tests/test_source_backed_entry.py',root/'tests/suite_inventory.json',Path(__file__),baseline_path):bind(path)
    raw.write_csv(out/'full-population-comparison.csv',population);raw.write_csv(out/'player-impact.csv',[p for p in population if p['affected_by_batch2b']])
    summary=dict(additional_verified_minutes=sum(float(p['added_supported_minutes']) for p in population),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),players=691,original_published_contributions=14979,corrected_published_contributions=14978,fixtures=len(bymatch),published_affected_players=10,published_changed_appearances=10,published_recovered_appearances=len(pending),batch2a_removed_nonappearances=len(removed),newly_removed_nonappearances=0,supplemental_changed_nonappearances=len(changed_keys-expected_published),all_source_changes=sorted(changed_keys),unchanged_other_published_players=681,source_checks=checks,raw_red_or_second_yellow_events=len(raw_card_ids),off_field_disciplinary_events_retained=len(retained_card_ids),baseline_supported_appearances=14537,corrected_supported_appearances=14547,batch1_recoveries_preserved=91,genuine_priority_conflicts_preserved=9,unexpected_changes=[],dominant_fine_group_changes=fine_changes,comparison_group_changes=0,players_with_overall_changes=sum(p['overall_delta'] not in (None,0) for p in population),eligibility_changes=sum(p['eligibility_changed'] for p in population),reference_semantic_sha256=reference['sha256'],published_sha256=hashlib.sha256((root/'frontend/public/data/player-ratings-2015-16-v1.json').read_bytes()).hexdigest(),input_receipts_reverified=len(receipts),prior_artifacts_preserved=len(preserved),publication_authorized=False,reference_refitted=False)
    dump('summary.json',summary);dump('input-hashes.json',receipts)
    dump('output-hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
