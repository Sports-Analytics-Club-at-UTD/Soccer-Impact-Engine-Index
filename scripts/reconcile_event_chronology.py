"""Offline exact chronology reconciliation. Originals are opened read-only.

Run --priority before the single full replay. Existing outputs are never reused.
No source, production, reference, published rating or admission rule is changed.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from fractions import Fraction as F
from functools import lru_cache
import copy
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

from scripts import decoder_fix_independent as raw
from scripts import off_field_card_independent as state
from scripts.source_verification_batch import payload
from src import statsbomb_participation as adapter
from src import independent_source_checks as second
from src.source_reconstruction import appearance_rows, flatten_events, measurements, event_within_exposure, exact

ROOT=Path(__file__).resolve().parents[1]
PRIOR=ROOT.parent/'Soccer-Impact-Engine-Index-permanent-exit-support'
AUDIT=ROOT.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit'
RECON=ROOT.parent/'Soccer-Impact-Engine-Index-source-evidence-reconciliation'
SOURCE=ROOT.parent/'Soccer-Impact-Engine-Index'
PRIORITY={3754048,3900579,3825780,3829454}


def table(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def write_csv(path,rows,fields=None):
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,default=str) if isinstance(v,(dict,list,tuple)) else v for k,v in row.items()})


def serialized(value):return json.loads(payload(value))


def run(priority=False):
    out=ROOT/('audit-output/chronology-priority' if priority else 'audit-output/event-chronology')
    if out.exists():raise ValueError('Preserve prior run: '+str(out))
    out.mkdir(parents=True)
    receipts={};checks=Counter()
    def read(path,expected=None):
        path=Path(path).resolve();b=path.read_bytes();h=hashlib.sha256(b).hexdigest()
        if expected:assert h==expected,str(path)
        receipts[str(path)]={'sha256':h,'bytes':len(b)}
        return b
    def js(path,expected=None):return json.loads(read(path,expected))
    def rows(path):read(path);return table(path)
    def dump(name,value):(out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf8')
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='95b82a6cf7e591fa7a6623d57e1533fabfb6db79'
    # No behavioral change: bind the exact merged production bytes to Batch 3A.
    for p in (ROOT/'src').rglob('*.py'):
        assert read(p)==read(PRIOR/'src'/p.relative_to(ROOT/'src')),p
    for p in (AUDIT/'docs/full-player-data-integrity-audit.md',AUDIT/'docs/data-correction-roadmap.md',RECON/'docs/source-evidence-reconciliation-report.md',PRIOR/'docs/permanent-exit-support-report.md'):
        read(p)
    history=rows(AUDIT/'audit-output/full-player-audit/appearances.csv')
    original=rows(AUDIT/'audit-output/full-player-audit/source-chronology-conflicts.csv')
    reconciled=rows(RECON/'audit-output/source-reconciliation/chronology-events.csv')
    assert len(original)==107 and len({int(r['player_id']) for r in original})==15
    original_ids={r['event_id'] for r in original}
    assert len(original_ids)==107
    old= {(int(r['player_id']),int(r['match_id'])):r for r in rows(PRIOR/'audit-output/permanent-exit-support/all-appearance-comparison.csv')}
    priorhash=js(PRIOR/'audit-output/permanent-exit-support/output-hashes.json')
    for name,h in priorhash.items():
        p=PRIOR/name if (PRIOR/name).exists() else PRIOR/'audit-output/permanent-exit-support'/name
        with p.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        assert digest==h,str(p)
        receipts[str(p.resolve())]={'sha256':digest,'bytes':p.stat().st_size}
    facts={}
    if not priority:
        for f in js(PRIOR/'audit-output/permanent-exit-support/baseline-diagnostic-facts.json'):facts[f['player_id'],f['match_id']]=f
        for f in js(PRIOR/'audit-output/permanent-exit-support/pending-corrected-facts.json'):facts[f['player_id'],f['match_id']]=f
    b1rows=rows(ROOT.parent/'Soccer-Impact-Engine-Index-participation-decoder-fix/audit-output/decoder-fix/all-appearance-comparison.csv')
    b1keys={(int(a['player_id']),int(a['match_id'])) for a in b1rows if a['changed']=='True'}
    assert len(b1keys)==91
    terminal_prior={(int(r['player_id']),int(r['match_id'])):r for r in rows(PRIOR/'audit-output/permanent-exit-support/terminal-source-inventory.csv')}
    leads={int(a['match_id']):json.loads(a['evidence']) for a in history}
    published=js(ROOT/'frontend/public/data/player-ratings-2015-16-v1.json')
    public={int(p['player_id']) for p in published['players']};assert len(public)==691
    # Cache only pure clock conversion and index irrelevant transition rows out
    # exactly as in the validated earlier replay. Full schema/proof reads remain.
    adapter._timestamp=lru_cache(maxsize=8192)(adapter._timestamp)
    original_check=adapter._check_original_transitions
    def indexed(tid,pid,observations,events,reference):
        relevant=[e for e in events if e['team']['id']==tid and (raw.typ(e) in ('Starting XI','Tactical Shift') or e.get('player',{}).get('id')==pid and (raw.typ(e) in ('Player On','Player Off','Substitution') or raw.card(e) in ('Red Card','Second Yellow')) or raw.typ(e)=='Substitution' and e['substitution']['replacement']['id']==pid)]
        return original_check(tid,pid,observations,relevant,reference)
    adapter._check_original_transitions=indexed
    db=sqlite3.connect(out/'source-uuid-index.sqlite')
    db.execute('create table events(uuid text primary key,match_id integer,team_id integer,player_id integer) without rowid')
    exceptions=[];comparisons=[];priority_rows=[];found_original={};coverage=[];raw_sets=Counter();all_geometry=hashlib.sha256()
    selected_mids=sorted(PRIORITY if priority else leads)
    bymatch=defaultdict(list)
    for key,r in old.items():bymatch[key[1]].append(r)
    for n,mid in enumerate(selected_mids,1):
        lead=leads[mid];report=js(lead['report_path'],lead['report_sha256'])
        bindings=[report['fixture_document'],report['artifacts']['lineups'],report['artifacts']['events']]
        bs=[read(b['path'],b['sha256']) for b in bindings]
        fixtures,lineups,events=map(json.loads,bs);fixture=next(f for f in fixtures if f['match_id']==mid)
        frozen_events=hashlib.sha256(bs[2]).hexdigest()
        roster={(t['team_id'],p['player_id']):p for t in lineups for p in t['lineup']}
        assert len(roster)==sum(len(t['lineup']) for t in lineups)
        ids={e['id']:e for e in events};assert len(ids)==len(events)
        db.executemany('insert into events values (?,?,?,?)',((e['id'],mid,e['team']['id'],e.get('player',{}).get('id')) for e in events));db.commit()
        checks['original_events']+=len(events)
        for e in events:
            assert e.get('match_id',mid)==mid
            tid=e['team']['id'];assert tid in {t['team_id'] for t in lineups}
            for actor in ([e['player']] if 'player' in e else [])+([e['pass']['recipient']] if 'recipient' in e.get('pass',{}) else []):
                assert roster[tid,actor['id']]['player_name']==actor['name'];checks['stable_actor_or_recipient_bindings']+=1
        adapted=adapter.adapt_match(mid,*(adapter.SourceDocument(b,c['source_reference'],'pinned-original') for b,c in zip(bs,bindings)),clock_document_reference='Pinned exact period-local clocks; original 0/45 source offsets')
        validations={r.context.player_id:r for r in adapted.validate()}
        for p in adapted.players:
            checks['batch2b_entry_proofs_preserved']+=bool(p.reconstructed_entries)
            checks['batch3a_exit_proofs_preserved']+=bool(p.reconstructed_exits)
            checks['batch2a_offfield_records_preserved']+=len(p.off_field_discipline)
            pid=p.context.player_id
            if (pid,mid) in b1keys:
                assert validations[pid].elapsed_seconds is not None;checks['batch1_recoveries_preserved']+=1
            if (pid,mid) in terminal_prior:
                previous=terminal_prior[pid,mid]
                assert (str(bool(p.reconstructed_exits)),validations[pid].status)==(previous['recovered'],previous['status'])
                checks['terminal_observations_preserved']+=1
        rebuilt=copy.deepcopy(report)
        rebuilt['players']=[dict(player=serialized(asdict(p)),validation=serialized(asdict(validations[p.context.player_id]))) for p in adapted.players]
        rebuilt['boundaries']=serialized([asdict(b) for b in adapted.boundaries])
        ars=appearance_rows(rebuilt,fixture,lineups);ai={(a['team_id'],a['player_id']):a for a in ars}
        bounds,bissues,brefs=raw.boundaries(events,{t['team_id'] for t in lineups})
        sbounds=second.boundaries(events,{t['team_id'] for t in lineups})
        transition_index=defaultdict(list)
        for e in events:transition_index[e['period'],e['minute'],e['second'],e['team']['id'],raw.typ(e)].append(e)
        frame=flatten_events(events,fixture,ars);ms,unknown,_=measurements(frame,ars);mi={(m['team_id'],m['player_id']):m for m in ms}
        scounts,missing,_,_=second.selected(events)
        for k,m in mi.items():
            for attr,c in m['components'].items():
                assert sorted(scounts.get(k,{}).get(attr,[]))==c['event_ids'];checks['raw_metric_uuid_sets']+=1
        for a in ars:
            k=(a['team_id'],a['player_id']);pid=k[1];r=validations[pid]
            active=a['active_appearance'];valid=a['participation_status']=='STRUCTURALLY_VALID'
            if valid:
                oracle=second.exposure(roster[k]['positions'],pid,k[0],transition_index,sbounds)
                assert oracle is not None,(mid,k)
                seconds,positions,intervals=oracle
                supplied=[((o['start']['period'],F(str(o['start']['seconds']))),(o['end']['period'],F(str(o['end']['seconds'])))) for o in a['playing_intervals']]
                assert seconds==exact(a['validated_elapsed_seconds']) and intervals==supplied
                assert positions=={p['position']:exact(p['elapsed_seconds']) for p in a['position_allocation']}
                checks['all_roster_exact_geometries']+=1
                all_geometry.update(payload([mid,k,supplied,positions]))
                for attr,c in mi[k]['components'].items():
                    bad=sorted(uid for uid in c['event_ids'] if not second.within(ids[uid],intervals,sbounds))
                    assert bad==c['unaligned_event_ids'];checks['independent_measurement_alignment']+=1
            if pid in public and (pid,mid) in old:
                previous=old[pid,mid];status=a['participation_status'];secs=str(r.elapsed_seconds) if r.elapsed_seconds is not None else ''
                assert (status,secs)==(previous['corrected_status'],previous['corrected_seconds']),(mid,pid,status,secs,previous)
                assert json.loads(previous['corrected_issues'])==serialized([asdict(i) for i in r.issues])
                comparisons.append(dict(player_id=pid,match_id=mid,team_id=k[0],before_status=status,after_status=status,before_seconds=secs,after_seconds=secs,geometry_unchanged=True,playing_intervals=a['playing_intervals'],position_allocation=a['position_allocation']))
                checks['published_decisions_preserved']+=1
                if valid:checks['published_accepted_preserved']+=1
        if not priority:
            raw_selected=defaultdict(lambda:defaultdict(set))
            for e in events:
                for attr in raw.selected(e):raw_selected[e.get('player',{}).get('id')][attr].add(e['id'])
            for prior_row in bymatch[mid]:
                pid=int(prior_row['player_id'])
                if (pid,mid) not in facts:
                    assert (pid,mid)==(26023,3825670);continue
                fact=facts[pid,mid]
                for attr,m in fact['metrics'].items():
                    assert set(m['numerator_ids'])==raw_selected[pid][attr],(pid,mid,attr)
                    if attr=='press_resistance':assert set(m['denominator_ids'])==raw_selected[pid]['press_attempts']
                    checks['frozen_fact_raw_uuid_sets']+=1
        independent_cache={}
        actor_keys={(e['team']['id'],e['player']['id']) for e in events if 'player' in e}
        transitions=[e for e in events if raw.typ(e) in ('Starting XI','Tactical Shift','Substitution','Player On','Player Off') or raw.card(e) in ('Red Card','Second Yellow')]
        for k in actor_keys:
            a=ai[k]
            if a['participation_status']!='STRUCTURALLY_VALID':
                oracle=state.reconstruct(k[1],k[0],roster[k],events,bounds,bissues,transition_events=transitions)
                independent_cache[k]=oracle
                coverage.append(dict(player_id=k[1],match_id=mid,team_id=k[0],published=k[1] in public,appearance_status=a['participation_status'],production_failure_reasons=a['failure_reasons'],independent=oracle,playing_intervals=a['playing_intervals'],source_documents=bindings))
        for e in events:
            pid=e.get('player',{}).get('id')
            if pid is None:continue
            k=e['team']['id'],pid;a=ai[k];point=raw.clock(e)
            # Inventory actor clocks against available original interval geometry,
            # including unresolved appearances; status still gates admission.
            observed=[]
            for o in a['playing_intervals']:
                if o['start'] and o['end']:observed.append(((o['start']['period'],F(str(o['start']['seconds']))),(o['end']['period'],F(str(o['end']['seconds'])))))
            bp=sbounds.get(point[0],(None,None));period_known=all(v is not None for v in bp)
            outside_period=period_known and not bp[0]<=point[1]<=bp[1]
            outside_nominal=bool(observed) and not any(lo<=point<=hi for lo,hi in observed)
            valid=a['participation_status']=='STRUCTURALLY_VALID'
            oracle=independent_cache.get(k)
            geometry_known=valid or oracle is not None and oracle['seconds'] is not None
            event_intervals=observed if valid else oracle['intervals'] if geometry_known else []
            outside_interval=geometry_known and not any(lo<=point<=hi for lo,hi in event_intervals)
            no_interval=not geometry_known
            exceptional=outside_period or outside_interval
            if not exceptional and e['id'] not in original_ids:continue
            valid=a['participation_status']=='STRUCTURALLY_VALID'
            selected=sorted(raw.selected(e));components=mi.get(k,{}).get('components',{})
            relevance={name:dict(selected=e['id'] in c['event_ids'],status=c['status'],reasons=c['reasons'],count=c['count'],unaligned=e['id'] in c['unaligned_event_ids'],supported_minutes=a['validated_elapsed_minutes']) for name,c in components.items() if e['id'] in c['event_ids']}
            halfends=[{key:x.get(key) for key in ('id','index','period','timestamp','team','half_end')} for x in events if x['period']==e['period'] and raw.typ(x)=='Half End']
            category='SOURCE_PERIOD_CONTRADICTION' if outside_period else 'OUTSIDE_SUPPORTED_PARTICIPATION' if outside_interval and valid else 'UNRESOLVED_PARTICIPATION_GEOMETRY' if outside_interval else 'NO_SUPPORTED_PARTICIPATION' if no_interval else 'RESOLVED_EARLIER_BATCH'
            row=dict(player_id=pid,name=roster[k]['player_name'],match_id=mid,team_id=k[0],published=pid in public,event_id=e['id'],event_type=raw.typ(e),period=e['period'],timestamp=e['timestamp'],event_index=e.get('index'),original_array_offset=events.index(e),exact_period_seconds=str(point[1]),period_boundary=[str(x) if x is not None else None for x in bp],half_end_events=halfends,seconds_after_half_end=str(point[1]-bp[1]) if bp[1] is not None else None,outside_period=outside_period,outside_player_interval=outside_interval,outside_nominal_lineup_interval=outside_nominal,no_interval_evidence=no_interval,event_state_geometry_known=geometry_known,independent_event_intervals=event_intervals,remains_exception=exceptional,original_exception=e['id'] in original_ids,appearance_status=a['participation_status'],accepted_appearance=valid,playing_intervals=a['playing_intervals'],original_positions=roster[k]['positions'],selected_metrics=selected,production_metric_relevance=relevance,successful_measurement=bool(set(selected)-{'press_attempts'}),administrative_or_nonmeasurement=not selected,classification=category,existing_decision='WITHHELD' if not event_within_exposure(e,a) else 'WITHIN_EXPOSURE',proposed_decision='WITHHELD' if not event_within_exposure(e,a) else 'WITHIN_EXPOSURE',reason='Exact source boundary and participation checks; no timing tolerance',production_failure_reasons=a['failure_reasons'],source_documents=bindings,report_path=lead['report_path'],report_sha256=lead['report_sha256'],independent_boundary_agreement=not bissues and bounds==sbounds,independent_period_evidence=brefs,source_index_after_half_end=all(e.get('index',-1)>x.get('index',-1) for x in halfends),outcome={name:e[name] for name in ('ball_recovery','duel','interception','pass','dribble') if name in e})
            if k not in independent_cache:independent_cache[k]=state.reconstruct(pid,k[0],roster[k],events,bounds,bissues)
            row['independent_event_and_lineup_reconstruction']=independent_cache[k]
            row['outside_supported_exposure']=not event_within_exposure(e,a)
            if (pid,mid) in facts:
                row['frozen_fact_metrics']={name:dict(supported=m['supported'],reasons=m['reasons'],in_numerator=e['id'] in m['numerator_ids'],in_denominator=e['id'] in (m['denominator_ids'] or []),seconds=m['seconds']) for name,m in facts[pid,mid]['metrics'].items()}
            if e['id'] in original_ids:found_original[e['id']]=row
            if exceptional:exceptions.append(row)
            if mid in PRIORITY and raw.typ(e)=='Ball Recovery' and selected and outside_period:
                if k not in independent_cache:independent_cache[k]=state.reconstruct(pid,k[0],roster[k],events,bounds,bissues)
                row=copy.deepcopy(row);row['independent_event_and_lineup_reconstruction']=independent_cache[k]
                row['neighboring_source_rows']=[{key:x.get(key) for key in ('id','index','type','period','timestamp','player','team')} for x in events[max(0,events.index(e)-3):events.index(e)+4]]
                priority_rows.append(row)
        # Cached clocks are ephemeral fields only; source bytes were never written.
        assert hashlib.sha256(Path(bindings[2]['path']).read_bytes()).hexdigest()==frozen_events
        if n%25==0 or priority:print(f'{n}/{len(selected_mids)} fixtures; {checks["original_events"]} events; {len(exceptions)} all-roster exceptions',flush=True)
    assert db.execute('select count(*) from events').fetchone()[0]==checks['original_events'];db.close()
    write_csv(out/'coverage-interval-evidence.csv',coverage)
    write_csv(out/'current-exception-inventory.csv',exceptions)
    write_csv(out/'original-exception-inventory.csv',[found_original[r['event_id']] for r in original if r['event_id'] in found_original])
    write_csv(out/'exception-classifications.csv',exceptions+[r for r in found_original.values() if not r['remains_exception']])
    write_csv(out/'unresolved-conflicts.csv',exceptions)
    write_csv(out/'appearance-comparison.csv',comparisons)
    dump('priority-evidence.json',priority_rows)
    if not priority:
        assert len(selected_mids)==1551 and checks['original_events']==5436699
        assert checks['published_decisions_preserved']==14979 and checks['published_accepted_preserved']==14550
        assert set(found_original)==original_ids
        assert checks['batch1_recoveries_preserved']==91
        assert checks['batch2b_entry_proofs_preserved']==36
        assert checks['batch3a_exit_proofs_preserved']==12
        assert checks['terminal_observations_preserved']==len(terminal_prior)
        population=rows(PRIOR/'audit-output/permanent-exit-support/full-population-comparison.csv')
        for p in population:
            p['proposed_batch3b']=p['proposed_batch3a'];p['batch3b_overall_delta']=0;p['batch3b_eligibility_changed']=False
        write_csv(out/'full-population-comparison.csv',population)
        write_csv(out/'player-impact.csv',[dict(player_id=p['player_id'],name=p['name'],before=json.loads(p['proposed_batch3a']),after=json.loads(p['proposed_batch3a']),successful_action_delta=0,supported_seconds_delta=0,attribute_rating_delta=0,percentile_delta=0,formula_b_delta=0,eligibility_changed=False) for p in population])
    write_csv(out/'changed-metric-events.csv',[],['player_id','match_id','event_id','metric','before','after','reason'])
    summary=dict(mode='priority' if priority else 'complete',baseline='95b82a6cf7e591fa7a6623d57e1533fabfb6db79',production_changes=0,confirmed_production_defects=0,valid_chronology_corrections=0,original_exception_count=107,original_players=15,original_reopened=len(found_original),original_remaining=sum(r['remains_exception'] for r in found_original.values()),original_resolved=sum(not r['remains_exception'] for r in found_original.values()),current_published_exceptions=sum(r['published'] for r in exceptions),current_published_players=len({r['player_id'] for r in exceptions if r['published']}),current_all_roster_exceptions=len(exceptions),current_all_roster_players=len({r['player_id'] for r in exceptions}),additional_published_exceptions=sum(r['published'] and not r['original_exception'] for r in exceptions),coverage_actor_observations=len(coverage),classification_counts=dict(Counter(r['classification'] for r in exceptions)),published_classification_counts=dict(Counter(r['classification'] for r in exceptions if r['published'])),successful_selected_exception_counts=dict(Counter(a for r in exceptions if r['published'] for a in r['selected_metrics'])),priority_cases=len(priority_rows),source_checks=dict(checks),geometry_fingerprint=all_geometry.hexdigest(),metric_action_delta=0,exposure_seconds_delta=0,attribute_delta=0,formula_b_delta=0,eligibility_changes=0,publication_authorized=False)
    dump('summary.json',summary);dump('input-hashes.json',receipts)
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--priority',action='store_true');args=parser.parse_args();run(args.priority)

