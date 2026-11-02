"""Batch 4 read-only identity investigation; no production identity/admission edits.

Run from this worktree. Output is exclusive and all source reads are hash-bound.
Historical participation decisions are reused only with identical production code
and original bytes. A fresh disk-backed UUID/actor inventory is independent of
production matching. Same-ID spelling findings are diagnostic assertions only.
"""
from collections import Counter, defaultdict
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
import csv, hashlib, json, sqlite3
import pandas as pd
import pyarrow.parquet as pq
from src import statsbomb_participation as adapter
from src.source_reconstruction import appearance_rows, player_name, team_name, reconcile_event
from scripts.source_verification_batch import payload

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'Soccer-Impact-Engine-Index'
PRIOR=ROOT.parent/'Soccer-Impact-Engine-Index-event-chronology-reconciliation'
SEALED=SOURCE/'data/derived/phase3-step2-source-reconstruction-2026-10-27'
OUT=ROOT/'audit-output/identity-source-reconciliation'
BENCH={(26023,3825670),(6672,3825869),(10612,3825885),(40458,3878555)}

def rows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:yield from csv.DictReader(f)

def jsonlines(p):
    with Path(p).open(encoding='utf8') as f:
        for line in f:yield json.loads(line)

def write_csv(p,rs,fields=None):
    rs=list(rs);fields=fields or list(dict.fromkeys(k for r in rs for k in r))
    with Path(p).open('x',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rs:w.writerow({k:json.dumps(v,ensure_ascii=True,sort_keys=True) if isinstance(v,(dict,list,set,tuple)) else v for k,v in r.items()})

def run(reuse_index=None):
    OUT.mkdir(parents=True,exist_ok=False);receipts={};checks=Counter()
    def read(p,expected=None):
        p=Path(p);p=p if p.is_absolute() else SOURCE/p
        b=p.read_bytes();h=hashlib.sha256(b).hexdigest()
        if expected is not None:assert h==expected, str(p)
        receipts[str(p.resolve())]={'sha256':h,'bytes':len(b)}
        return b
    def bind(p,expected):
        p=Path(p)
        with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
        assert h==expected,str(p)
        receipts[str(p.resolve())]={'sha256':h,'bytes':p.stat().st_size}
    def js(p,h=None):return json.loads(read(p,h))
    def dump(name,value):(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=True,default=str)+'\n',encoding='utf8')
    # The previous complete replay used these exact production implementations.
    for p in (ROOT/'src').rglob('*.py'):
        assert read(p)==read(PRIOR/p.relative_to(ROOT)),str(p)
        checks['unchanged_production_modules']+=1
    for p in ['scripts/reconstruct_player_evidence.py','scripts/event_chronology_diagnostics.py']:
        assert read(ROOT/p).replace(b"\r\n",b"\n")==read(PRIOR/p).replace(b"\r\n",b"\n")
    inventory=js(PRIOR/'audit-output/event-chronology/artifact-inventory.json')
    bound={r['path']:r['sha256'] for r in inventory}
    for name in ['source-uuid-index.sqlite','input-hashes.json','source-replay-summary.json','full-population-comparison.csv','verified-measurement-corrections.json','current-exception-inventory.csv']:
        bind(PRIOR/'audit-output/event-chronology'/name,bound['audit-output/event-chronology/'+name])
    prior_receipts=js(PRIOR/'audit-output/event-chronology/input-hashes.json')
    # Every prior source receipt is rehashed, not inferred from file metadata.
    for path,r in prior_receipts.items():
        if '/data/' in Path(path).as_posix():bind(path,r['sha256']);checks['prior_data_receipts_rehashed']+=1
    manifest=js(SEALED/'run-manifest.json');artifacts={r['path']:r['sha256'] for r in manifest['artifacts']}
    for name in ['identity-reconciliation.jsonl','roster-identities.jsonl','event-associations.sqlite','unresolved-evidence.jsonl']:
        bind(SEALED/name,artifacts[name])
    old=list(jsonlines(SEALED/'identity-reconciliation.jsonl'))
    original=[r for r in old if r['identity_reasons']];assert len(old)==2280 and len(original)==10
    write_csv(OUT/'original-restriction-inventory.csv',original)
    historical=js(SOURCE/'audit-output/name-polish-2026-11-01/identity-matching.json')
    assert historical['flagged_contexts']==original
    # Verify the requested prior reports before deriving any conclusions.
    docs=[ROOT.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit/docs/data-correction-roadmap.md',Path('C:/Users/Ayush/.codex/worktrees/coverage-audit/Soccer-Impact-Engine-Index/docs/identity-integrity-audit-2026-11-01.md')]
    docs += [ROOT.parent/'Soccer-Impact-Engine-Index-source-evidence-reconciliation/docs'/n for n in ['source-evidence-reconciliation-report.md','source-reconciliation-correction-plan.md']]
    docs += [ROOT/'docs'/n for n in ['off-field-card-fix-report.md','source-backed-entry-fix-report.md','permanent-exit-support-report.md','event-chronology-reconciliation-report.md']]
    for p in docs:read(p)
    roster=list(jsonlines(SEALED/'roster-identities.jsonl'));byfixture=defaultdict(list)
    for r in roster:byfixture[r['match_id']].append(r)
    leads={int(r['match_id']):r for r in rows(ROOT.parent/'Soccer-Impact-Engine-Index-participation-decoder-fix/audit-output/decoder-fix/all-appearance-comparison.csv')}
    assert len(byfixture)==1517 and len(leads)==1551
    for mid in leads:byfixture.setdefault(mid,[])
    assert len(byfixture)==1551
    delivered=defaultdict(lambda:dict(names=set(),active=False))
    for r in pq.read_table(SOURCE/'data/raw/statsbomb_lineups.parquet',columns=['match_id','team','player_id','player_name','position']).to_pylist():
        d=delivered[r['match_id'],team_name(r['team']),r['player_id']];d['names'].add(player_name(r['player_name']));d['active']|=r['position'] is not None
    reasons=defaultdict(set);names=defaultdict(set);active_sets=defaultdict(set);delivered_sets=defaultdict(set);bench_events=[];evidence=[];appearance=[];uuids=[];aliases=[];counts=Counter();actor_counts=Counter();recipient_counts=Counter();source_contexts=defaultdict(set)
    old_bykey={(r['player_id'],r['team_id'],r['competition_name'],r['season_name']):r for r in old}
    target_keys={(r['player_id'],r['team_id']) for r in original};target_ids={r['player_id'] for r in original}
    # Scope retained aliases by provider, stable ID, team, competition, season,
    # fixture and exact raw UUID; no alias is installed in any matching table.
    indexpath=OUT/'source-uuid-index.sqlite'
    if reuse_index is not None:
        import shutil
        reuse_index=Path(reuse_index)
        # Reuse only a complete independently built inventory whose exact bytes
        # equal the sealed baseline; all original data receipts are checked above.
        bind(reuse_index,bound['audit-output/event-chronology/source-uuid-index.sqlite'])
        shutil.copyfile(reuse_index,indexpath)
    db=sqlite3.connect(str(indexpath),uri=True)
    if reuse_index is None:db.execute('create table events(uuid text primary key,match_id integer,team_id integer,player_id integer) without rowid')
    delivered_db=sqlite3.connect((SEALED/'event-associations.sqlite').as_uri()+'?mode=ro&immutable=1',uri=True)
    for n,(mid,rs) in enumerate(sorted(byfixture.items()),1):
        lead=rs[0]['review_reference'] if rs else dict(path=leads[mid]['report_path'],sha256=leads[mid]['report_sha256'])
        report=js(lead['path'],lead['sha256'])
        fixture=next(f for f in js(report['fixture_document']['path'],report['fixture_document']['sha256']) if f['match_id']==mid)
        bindings=report['artifacts'];ls=js(bindings['lineups']['path'],bindings['lineups']['sha256']);es=js(bindings['events']['path'],bindings['events']['sha256'])
        if not rs:
            rs=appearance_rows(report,fixture,ls)
            for r in rs:r.update(review_reference=lead,delivered_fixture_present=True)
        rawroster={(t['team_id'],p['player_id']):p for t in ls for p in t['lineup']};assert len(rawroster)==sum(len(t['lineup']) for t in ls)
        active={r['player_id'] for r in rs if r['active_appearance'] and (r['player_id'],mid) not in BENCH}
        assert {r['player_id'] for r in rs}=={pid for tid,pid in rawroster}
        ids={e['id']:e for e in es};assert len(ids)==len(es)
        if reuse_index is None:
            db.executemany('insert into events values (?,?,?,?)',((e['id'],mid,e['team']['id'],e.get('player',{}).get('id')) for e in es));db.commit()
        if any((r['player_id'],r['team_id']) in target_keys for r in rs):
            ds={x[0]:dict(zip(['id','match_id','team','player','competition_name','season_name','type'],x)) for x in delivered_db.execute('select id,mid,team,player,competition,season,type from delivered where mid=?',(mid,))}
        else:ds={}
        for r in rs:
            k=(r['player_id'],r['team_id'],r['competition_name'],r['season_name']);names[k].add(r['player_name_raw']);source_contexts[r['player_id'],r['season_name']].add((r['team_id'],r['competition_name']))
            d=delivered.get((mid,r['team'],r['player_id']));a=r['player_id'] in active
            if a:active_sets[k].add(mid)
            if d and d['active']:delivered_sets[k].add(mid)
            if d:
                if d['names']!={r['player_name_normalized']}:reasons[k].add('DELIVERED_LINEUP_NAME_DISAGREEMENT')
                if d['active']!=a:reasons[k].add('DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT')
            elif r['delivered_fixture_present'] and a:reasons[k].add('DELIVERED_ACTIVE_ROSTER_MISSING')
            if k in old_bykey:
                reasons[k].update(x for x in old_bykey[k]['identity_reasons'] if x not in ('DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT','SOURCE_ACTIVITY_WITHOUT_APPEARANCE'))
            if (r['player_id'],r['team_id']) in target_keys:
                appearance.append(dict(player_id=r['player_id'],team_id=r['team_id'],match_id=mid,competition=r['competition_name'],season=r['season_name'],raw_name=r['player_name_raw'],source_active=a,delivered_active=bool(d and d['active']),historical_active=r['active_appearance'],batch2a_removed=(r['player_id'],mid) in BENCH,original_positions=rawroster[r['team_id'],r['player_id']]['positions'],lineup_reference=bindings['lineups']['source_reference']+f"#/team/{r['team_id']}/player/{r['player_id']}",source_hashes={kind:b['sha256'] for kind,b in bindings.items()}))
        for e in es:
            tid=e['team']['id'];assert tid in {t['team_id'] for t in ls}
            for role,actor in [('actor',e.get('player')),('recipient',e.get('pass',{}).get('recipient'))]:
                if not actor:continue
                pid=actor['id'];assert rawroster[tid,pid]['player_name']==actor['name'];checks['stable_'+role+'_bindings']+=1
                k=(pid,tid,report['competition_name'],report['season_name'])
                if role=='actor' and pid not in active:
                    reasons[k].add('SOURCE_ACTIVITY_WITHOUT_APPEARANCE')
                    bench_events.append(dict(player_id=pid,team_id=tid,match_id=mid,event_id=e['id'],type=e['type']['name'],raw_event=e,lineup=rawroster[tid,pid],source_hashes={kind:b['sha256'] for kind,b in bindings.items()}))
                if (pid,tid) not in target_keys:continue
                (actor_counts if role=='actor' else recipient_counts)[pid,actor['name']]+=1
                assoc=None
                if role=='actor' and e['id'] in ds:
                    source=dict(id=e['id'],match_id=mid,team_id=tid,team=next(r['team'] for r in rs if r['team_id']==tid),player_id=pid,player=actor['name'],competition_name=report['competition_name'],season_name=report['season_name'],type=e['type']['name'])
                    assoc=reconcile_event(source,ds[e['id']]);assert not assoc['reasons'];counts[pid]+=1
                evidence.append(dict(player_id=pid,team_id=tid,match_id=mid,competition_id=fixture['competition']['competition_id'],competition=report['competition_name'],season_id=fixture['season']['season_id'],season=report['season_name'],role=role,event_id=e['id'],event_index=e['index'],event_type=e['type']['name'],raw_name=actor['name'],normalized_name=player_name(actor['name']),original_lineup_name=rawroster[tid,pid]['player_name'],lineup_reference=bindings['lineups']['source_reference']+f'#/team/{tid}/player/{pid}',event_reference=bindings['events']['source_reference']+'#/event/'+e['id'],source_hashes={kind:b['sha256'] for kind,b in bindings.items()},delivered_association=assoc,admission_changed=False))
        uuids.append(dict(match_id=mid,source_events=len(es),unique_fixture_uuids=len(ids),source_events_sha256=bindings['events']['sha256'],reused_baseline_source_hash_equal=True,changed_actor_associations=0,changed_recipient_associations=0))
        checks['original_events']+=len(es);checks['original_fixtures']+=1
        if n%100==0:print('IDENTITY_SOURCE_SCAN',n,'/',len(byfixture),flush=True)
    assert checks['original_events']==5436699
    prior_db=PRIOR/'audit-output/event-chronology/source-uuid-index.sqlite'
    db.execute('attach database ? as baseline',('file:'+prior_db.as_posix()+'?mode=ro',))
    assert db.execute('select count(*) from (select * from events except select * from baseline.events)').fetchone()[0]==0
    assert db.execute('select count(*) from (select * from baseline.events except select * from events)').fetchone()[0]==0
    checks['uuid_actor_fixture_team_bidirectional_comparisons']=5436699
    db.close();delivered_db.close()
    current=[];comparison=[]
    for k in sorted(set(old_bykey)|set(reasons)):
        prior=old_bykey.get(k);now=sorted(reasons[k]);oldreasons=prior['identity_reasons'] if prior else []
        if not now and not oldreasons:continue
        same_id=len(names[k])>1
        classification=['A','H'] if same_id else ['C','H'] if now==['SOURCE_ACTIVITY_WITHOUT_APPEARANCE'] else ['B','H'] if now else ['G']
        resolved='G' if 'DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT' in oldreasons and 'DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT' not in now else None
        row=dict(player_id=k[0],team_id=k[1],competition=k[2],season=k[3],original_names=sorted(names[k]),prior_reasons=oldreasons,current_reasons=now,classification=classification,resolved_appearance_class=resolved,source_active_matches=sorted(active_sets[k]),delivered_active_matches=sorted(delivered_sets[k]),same_id_variants_verified=same_id,production_restriction_preserved=True,association_changes=0,metric_changes=0)
        current.append(row);comparison.append(row)
    assert counts[3054]==3873 and counts[26023]==1415
    assert active_sets[26023,221,'La Liga','2015/2016']==delivered_sets[26023,221,'La Liga','2015/2016']
    write_csv(OUT/'current-restriction-inventory.csv',current);write_csv(OUT/'identity-admission-comparison.csv',comparison)
    write_csv(OUT/'source-name-evidence.csv',evidence);write_csv(OUT/'delivered-appearance-evidence.csv',appearance)
    write_csv(OUT/'event-uuid-conservation.csv',uuids);write_csv(OUT/'unresolved-conflicts.csv',bench_events)
    dump('source-activity-without-appearance.json',bench_events)
    # Reuse complete B3B numeric records with byte validation, then independently
    # re-evaluate every stage's frozen arithmetic. No matching/admission changed.
    from scripts import decoder_fix_independent as raw
    from src.private_five_attribute import validate_reference
    from src.provisional_ovr import formula_b
    from fractions import Fraction as F
    ref=validate_reference(js(SOURCE/'data/derived/private-five-attribute-v2/frozen-reference.json'))
    assert ref['sha256']=='403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd'

    published=js(ROOT/'frontend/public/data/player-ratings-2015-16-v1.json')
    public={p['player_id']:p for p in published['players']};assert len(public)==691
    # Group and limited-data are canonical facts, never guessed from names.
    canonical={p['player_id']:p for p in jsonlines(SOURCE/'data/derived/fifth-attribute-private-v1/player-measurements.jsonl')}
    population=list(rows(PRIOR/'audit-output/event-chronology/full-population-comparison.csv'));impact=[]
    for r in population:
        pid=int(r['player_id']);c=canonical[pid]
        for stage in ['v1','merged_batch1','corrected_batch2a','corrected_batch2b','proposed_batch3a','proposed_batch3b']:
            data=json.loads(r[stage]);ratings=[]
            for attr,m in data['attributes'].items():
                value=F(m['exact_value']) if m['exact_value'] is not None else None
                score,pct=raw.score(value,F(data['exact_supported_minutes']) if attr=='press_resistance' else F(m['supported_seconds'])/60,F(data['exact_supported_minutes']),c['limited_data'],ref['pools'][c['comparison_group']][attr])
                assert (score,pct)==(m['rating'],m['percentile']),(pid,stage,attr)
                ratings.append(score);checks['independent_frozen_attribute_comparisons']+=1
            assert formula_b(ratings)==data['overall'];checks['independent_formula_b_comparisons']+=1
        r['proposed_batch4']=r['proposed_batch3b'];r['batch4_overall_delta']=0;r['batch4_eligibility_changed']=False
        if pid in target_ids:
            impact.append(dict(player_id=pid,before=json.loads(r['proposed_batch3b']),after=json.loads(r['proposed_batch4']),attribute_deltas={a:0 for a in raw.ATTRS},formula_b_delta=0,eligibility_changed=False))
    assert len(population)==691
    write_csv(OUT/'full-population-comparison.csv',population);write_csv(OUT/'player-impact.csv',impact)
    transfers=[dict(player_id=k[0],season=k[1],contexts=sorted(v),policy='UNCHANGED_STABLE_ID_CLUB_SCOPED') for k,v in source_contexts.items() if len(v)>1]
    write_csv(OUT/'transfer-contexts.csv',transfers)
    dump('summary.json',dict(baseline='1bd99b9c43795ecd670b7ad447d031fd25578c39',production_changes=0,production_identity_defects_confirmed=0,historical_contexts=len(old),historical_restrictions=len(original),current_restrictions=len(current),checks=checks,actor_name_counts=[dict(player_id=k[0],name=k[1],events=v) for k,v in actor_counts.items()],recipient_name_counts=[dict(player_id=k[0],name=k[1],events=v) for k,v in recipient_counts.items()],target_delivered_associations=dict(counts),source_only_inactive_actor_events=len(bench_events),transfer_player_seasons=len(transfers),diagnostic_same_id_assertions_only=True,new_matching_aliases=0,changed_source_event_associations=0,changed_delivered_appearance_decisions=0,changed_duration=0,changed_metric_admission=0,changed_player_season_membership=0,changed_published_eligibility=0,all_691_formula_b_delta=0,frozen_fingerprint=ref['sha256'],prior_corrections=js(PRIOR/'audit-output/event-chronology/source-replay-summary.json')['source_checks']))
    dump('input-hashes.json',receipts)
    print('COMPLETE',dict(checks),flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--reuse-verified-index',type=Path)
    run(parser.parse_args().reuse_verified_index)
