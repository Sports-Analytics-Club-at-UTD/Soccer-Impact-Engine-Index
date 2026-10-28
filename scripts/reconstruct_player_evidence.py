"""Offline, deterministic source-statistics reconstruction; exclusive derived output.

No retrieval, scoring, source edits or evidence/certification promotion. Existing
sealed output is verified and reused; an incomplete/conflicting output refuses.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts.source_verification_batch import (load_json,load_manifest,digest,payload,write_new,
    bound_document,code_revision,CLOCK_REFERENCE)
from scripts.audit_dri_readiness import candidate_population, target
from scripts.audit_provisional_identity import prepare_provisional_lookup
from src.dri_scoring import LEAGUES,SEASON,ROLE_GROUPS
from src.season_verification import season_readiness
from src.source_reconstruction import (NOTICE,COUNT_NAMES,appearance_rows,flatten_events,measurements,
    reconcile_event,aggregate_context,transfer_comparison,key,team_name,player_name,exact,rational)

DEFAULT_INDEX=Path('data/source-evidence/phase3-alias-continuation-2026-10-27/current-review-index.json')
DEFAULT_MANIFEST=Path('data/source-evidence/phase1b-2026-10-27/analysis/retrieval-manifest.json')
DEFAULT_EVENTS=Path('data/validation/drive-raw-review/statsbomb_team_events.parquet')
DEFAULT_MINUTES=Path('data/validation/arpit-refresh-review/player_minutes.parquet')
DEFAULT_RECOVERY=Path('data/validation/arpit-refresh-review/recovery_per90.parquet')
DEFAULT_CROSSWALK=Path('data/processed/player_name_crosswalk.parquet')
DEFAULT_LINEUPS=Path('data/raw/statsbomb_lineups.parquet')
DEFAULT_METADATA=Path('data/validation/arpit-match-context-review/match_metadata.parquet')
DEFAULT_FRAMES=Path('data/validation/drive-raw-review/statsbomb_360_frames.parquet')
RECIPE_FILES=['scripts/reconstruct_player_evidence.py','src/source_reconstruction.py',
    'scripts/source_verification_batch.py','scripts/audit_dri_readiness.py','scripts/audit_provisional_identity.py',
    'src/statsbomb_participation.py','src/participation_intervals.py','src/identity.py','src/identity_evidence.py',
    'src/recovery.py','src/metrics/recovery_coverage.py','src/metrics/zones.py','src/metrics/press_actions.py',
    'src/metrics/progressive_passes.py','src/passing.py','src/dri_scoring.py','src/transfer_aggregation.py']
RECIPE_FILES.append('src/season_verification.py')


def file_hash(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def recipe():
    return dict(files={p:file_hash(p) for p in RECIPE_FILES},python=sys.version.split()[0],
        pandas=pd.__version__,numpy=np.__version__,pyarrow=pa.__version__,sqlite=sqlite3.sqlite_version)


def line(stream,row):
    stream.write(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n')


def records(path):
    with Path(path).open(encoding='utf-8') as f:
        for text in f:yield json.loads(text)


def build_delivered_index(path,db):
    """One bounded scan, disk-backed unique UUID index, no name-based ID fill."""
    db.execute('CREATE TABLE delivered (id TEXT,mid INTEGER,team TEXT,player TEXT,competition TEXT,season TEXT,type TEXT,seen INTEGER DEFAULT 0)')
    totals=Counter();rows=0
    cols=['id','match_id','team','player','competition_name','season_name','type']
    for batch in pq.ParquetFile(path).iter_batches(batch_size=65536,columns=cols):
        data=batch.to_pylist();values=[]
        for r in data:
            if not isinstance(r['id'],str) or not r['id']:raise ValueError('invalid delivered UUID')
            if type(r['match_id']) is not int or r['match_id']<=0:raise ValueError('invalid delivered match ID')
            values.append(tuple(r[c] for c in cols))
            totals[r['competition_name'],r['season_name']]+=1
        db.executemany('INSERT INTO delivered(id,mid,team,player,competition,season,type) VALUES (?,?,?,?,?,?,?)',values)
        rows+=len(data)
    try:db.execute('CREATE UNIQUE INDEX delivered_uuid ON delivered(id)')
    except sqlite3.IntegrityError as exc:raise ValueError('duplicate delivered event UUIDs; reconstruction refused') from exc
    db.execute('CREATE INDEX delivered_match ON delivered(mid)')
    db.execute('CREATE TABLE original_ids(id TEXT,mid INTEGER,player_id INTEGER)')
    db.commit()
    return dict(rows=rows,by_context=[dict(competition_name=k[0],season_name=k[1],rows=v) for k,v in sorted(totals.items())])


def inspect_frame_contexts(path):
    counts=Counter();matches=defaultdict(set)
    for b in pq.ParquetFile(path).iter_batches(batch_size=131072,columns=['match_id','competition_name','season_name']):
        table=b.to_pandas()
        for (comp,season),g in table.groupby(['competition_name','season_name'],sort=True):
            counts[comp,season]+=len(g);matches[comp,season].update(map(int,g.match_id.unique()))
    return dict(source_path=str(path),provenance_status='DELIVERED_FLAT_FRAMES_NOT_ORIGINAL_FRAME_ATTESTATION',
        target_rows=sum(v for (c,s),v in counts.items() if c in LEAGUES and s==SEASON),
        contexts=[dict(competition_name=k[0],season_name=k[1],rows=v,match_ids=sorted(matches[k])) for k,v in sorted(counts.items())],
        line_breaking_definition='UNRESOLVED',line_breaking_candidate_measurement=None)


def verify_existing(output,inputs,revision):
    manifest=load_json(output/'run-manifest.json')
    if manifest['recipe']!=revision or manifest['input_paths']!=[str(p.resolve()) for p in inputs]:
        raise ValueError('existing output belongs to different inputs/code')
    for r in load_json(output/'input-receipts.json'):
        if file_hash(r['path'])!=r['sha256']:raise ValueError('input fingerprint changed: '+r['path'])
    for r in manifest['artifacts']:
        p=output/r['path']
        if not p.is_file() or file_hash(p)!=r['sha256']:raise ValueError('derived artifact fingerprint conflict: '+str(p))
    return load_json(output/'summary.json')


def reconstruct(*,output,index=DEFAULT_INDEX,manifest=DEFAULT_MANIFEST,events=DEFAULT_EVENTS,
                minutes=DEFAULT_MINUTES,recovery=DEFAULT_RECOVERY,crosswalk=DEFAULT_CROSSWALK,
                lineups=DEFAULT_LINEUPS,metadata=DEFAULT_METADATA,frames=DEFAULT_FRAMES):
    output=Path(output);inputs=list(map(Path,[index,manifest,events,minutes,recovery,crosswalk,lineups,metadata,frames]))
    revision=recipe()
    if output.exists():return verify_existing(output,inputs,revision)
    # Validate explicit source inventory/current implementation before any output.
    source_manifest=load_manifest(manifest);idx=load_json(index)
    if idx['validator_revision']!=code_revision() or idx['manifest_sha256']!=file_hash(manifest):
        raise ValueError('stale source review index or manifest mismatch')
    reviews={r['match_id']:r for r in idx['matches']}
    if len(reviews)!=len(idx['matches']) or set(reviews)!={r['match_id'] for r in source_manifest['matches']}:
        raise ValueError('duplicate or incomplete approved review inventory')
    fixture_docs={name:bound_document(b).records() for name,b in source_manifest['fixture_documents'].items()}
    fixtures={f['match_id']:f for rs in fixture_docs.values() for f in rs}
    if len(fixtures)!=len(reviews):raise ValueError('fixture cardinality mismatch')
    delivered_metadata={}
    for r in pq.read_table(metadata).to_pylist():
        if r['match_id'] in delivered_metadata and r!=delivered_metadata[r['match_id']]:raise ValueError('conflicting delivered match contexts')
        delivered_metadata[r['match_id']]=r
    minute_frame=pq.read_table(minutes).to_pandas();recovery_frame=pq.read_table(recovery).to_pandas()
    population,table_checks=candidate_population(minute_frame,recovery_frame)
    candidates={key(r):r for r in population.astype(object).where(pd.notna(population),None).to_dict('records')}
    delivered_components={}
    for r in target(recovery_frame).to_dict('records'):
        k=(int(r['player_id']),team_name(r['team']),r['competition_name'],r['season_name'],r['event_type'])
        if k in delivered_components:raise ValueError('duplicate delivered component context')
        delivered_components[k]=r
    lookup=prepare_provisional_lookup(pq.read_table(crosswalk).to_pandas())
    mappings=defaultdict(set)
    for r in lookup.observations.to_dict('records'):
        mappings[(r['player_name_raw'],r['team'],r['competition_name'],r['season_name'])].add(int(r['player_id']))
    delivered_lineups=defaultdict(lambda:dict(names=set(),active=False,rows=0))
    for r in pq.read_table(lineups,columns=['match_id','team','player_id','player_name','position']).to_pylist():
        k=(r['match_id'],team_name(r['team']),r['player_id'])
        value=delivered_lineups[k];value['names'].add(player_name(r['player_name']));value['active']|=r['position'] is not None;value['rows']+=1
    output.mkdir(parents=True,exist_ok=False)
    receipts={str(p.resolve()):dict(path=str(p.resolve()),size_bytes=p.stat().st_size,sha256=file_hash(p)) for p in inputs}
    for b in source_manifest['fixture_documents'].values():receipts[str(Path(b['path']).resolve())]=dict(path=str(Path(b['path']).resolve()),size_bytes=Path(b['path']).stat().st_size,sha256=b['sha256'])
    db=sqlite3.connect(str(output/'event-associations.sqlite'))
    db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA temp_store=FILE')
    db.execute('PRAGMA cache_size=-32768')
    try:delivered_scan=build_delivered_index(events,db)
    except BaseException:
        db.close()
        raise
    print('DELIVERED_INDEX_READY',delivered_scan['rows'],flush=True)
    all_appearances=defaultdict(list);all_metrics=defaultdict(list);identity_reasons=defaultdict(set)
    context_reconciliation=defaultdict(Counter);source_names=defaultdict(set)
    unassociated_delivered_names=set();source_name_ids=defaultdict(set)
    source_counts=Counter();association_counts=Counter();event_types=Counter();passing_counts=Counter();roster_count=0
    league_statuses=defaultdict(Counter);lineup_seen=set();unresolved_count=0
    try:
        with ExitStack() as stack:
            streams={name:stack.enter_context((output/(name+'.jsonl')).open('x',encoding='utf-8',newline='\n')) for name in
                ['appearance-ledger','roster-identities','match-component-measurements','unresolved-evidence','match-coverage']}
            for number,mid in enumerate(sorted(reviews),1):
                entry=reviews[mid];rp=Path(entry['report_path']);raw=rp.read_bytes()
                if digest(raw)!=entry['report_sha256']:raise ValueError('source report fingerprint mismatch')
                report=load_json(rp);f=fixtures[mid]
                if report['verification_key']!=entry['verification_key'] or report['verification_key']!=digest(payload(dict(match_id=mid,fixture=report['fixture_document'],artifacts=report['artifacts'],validator_revision=idx['validator_revision'],clock_reference=CLOCK_REFERENCE))):
                    raise ValueError('source verification revision/binding conflict')
                if report['production_certified'] is not False or report['source_independently_verified'] is not False:raise ValueError('unexpected source certification')
                receipts[str(rp.resolve())]=dict(path=str(rp.resolve()),size_bytes=len(raw),sha256=entry['report_sha256'])
                docs={kind:bound_document(b) for kind,b in report['artifacts'].items()}
                for b in report['artifacts'].values():receipts[str(Path(b['path']).resolve())]=dict(path=str(Path(b['path']).resolve()),size_bytes=Path(b['path']).stat().st_size,sha256=b['sha256'])
                roster=appearance_rows(report,f,docs['lineups'].records())
                frame=flatten_events(docs['events'].records(),f,roster)
                metric_rows,unknown,preparation=measurements(frame,roster)
                measured={r['player_id']:r for r in metric_rows}
                passing_counts.update({k:v for k,v in preparation.items() if isinstance(v,int)})
                event_types.update(frame.type.value_counts().to_dict());source_counts['original_events']+=len(frame)
                db.executemany('INSERT INTO original_ids VALUES (?,?,?)',[(r['id'],mid,None if pd.isna(r['player_id']) else int(r['player_id'])) for r in frame[['id','player_id']].to_dict('records')])
                delivered={r[0]:dict(zip(['id','match_id','team','player','competition_name','season_name','type'],r)) for r in db.execute('SELECT id,mid,team,player,competition,season,type FROM delivered WHERE mid=?',(mid,))}
                matched_ids=[];seen_original=set();match_associations=Counter()
                for e in frame.to_dict('records'):
                    uid=e['id'];seen_original.add(uid)
                    if uid not in delivered:
                        match_associations['source_only_events']+=1;continue
                    result=reconcile_event(e,delivered[uid]);matched_ids.append((uid,));association_counts[result['status']]+=1;match_associations[result['status']]+=1
                    if result['reasons']:
                        unresolved_count+=1
                        line(streams['unresolved-evidence'],dict(kind='DELIVERED_EVENT_ASSOCIATION',match_id=mid,event_id=uid,source=e['player'],delivered=delivered[uid],**result))
                        if result['source_player_id'] is not None:
                            identity_reasons[(result['source_player_id'],e['team'],e['competition_name'],e['season_name'])].update(result['reasons'])
                    if result['source_player_id'] is not None:
                        context_reconciliation[result['source_player_id'],e['team'],e['competition_name'],e['season_name']][result['status']]+=1
                db.executemany('UPDATE delivered SET seen=1 WHERE id=?',matched_ids)
                meta=delivered_metadata.get(mid)
                context_ok=bool(meta and (meta['competition_name'],meta['season_name'])==(report['competition_name'],report['season_name']))
                if meta and not context_ok:raise ValueError('delivered/source match context disagreement')
                for a in roster:
                    roster_count+=1;k=key(a);lk=(mid,a['team'],a['player_id']);dl=delivered_lineups.get(lk)
                    if dl:
                        lineup_seen.add(lk)
                        if dl['names']!={a['player_name_normalized']}:identity_reasons[k].add('DELIVERED_LINEUP_NAME_DISAGREEMENT')
                        if dl['active']!=a['active_appearance']:identity_reasons[k].add('DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT')
                    elif context_ok and a['active_appearance']:identity_reasons[k].add('DELIVERED_ACTIVE_ROSTER_MISSING')
                    ids=mappings.get((a['player_name_normalized'],a['team'],a['competition_name'],a['season_name']),set())
                    mapping_status='EXACT_SOURCE_ID_AND_DELIVERED_MAPPING' if ids=={a['player_id']} else 'AMBIGUOUS_MAPPING' if len(ids)>1 else 'NO_MATCHING_DELIVERED_MAPPING'
                    if ids and a['player_id'] not in ids:identity_reasons[k].add('DELIVERED_CROSSWALK_ID_DISAGREEMENT')
                    if len(ids)>1:identity_reasons[k].add('AMBIGUOUS_DELIVERED_NAME_MAPPING')
                    if k in candidates and player_name(candidates[k]['player_name'])!=a['player_name_normalized']:
                        identity_reasons[k].add('CANDIDATE_SOURCE_NAME_DISAGREEMENT')
                    source_name_ids[a['player_name_normalized'],a['team'],a['competition_name'],a['season_name']].add(a['player_id'])
                    a.update(delivered_fixture_present=context_ok,delivered_lineup_present=dl is not None,
                        delivered_mapping_status=mapping_status,candidate_population_context_present=k in candidates,
                        review_reference=dict(path=str(rp),sha256=entry['report_sha256']),
                        source_documents={kind:dict(source_reference=b['source_reference'],sha256=b['sha256'],provider_revision=b['provider_revision'],retrieved_at=b['retrieved_at']) for kind,b in report['artifacts'].items()},
                        fixture_reference=report['fixture_document']['source_reference'],fixture_sha256=report['fixture_document']['sha256'])
                    line(streams['roster-identities'],{k:v for k,v in a.items() if k not in ('playing_intervals','original_positions','period_boundaries','source_checks','position_allocation')})
                    if not a['active_appearance']:continue
                    source_counts[a['participation_status']]+=1;league_statuses[a['competition_name']][a['participation_status']]+=1
                    all_appearances[k].append(a);all_metrics[k].append(measured[a['player_id']])
                    source_names[a['player_id'],a['season_name']].add(a['player_name_normalized'])
                    line(streams['appearance-ledger'],a);line(streams['match-component-measurements'],measured[a['player_id']])
                    if a['participation_status']!='STRUCTURALLY_VALID':
                        unresolved_count+=1;line(streams['unresolved-evidence'],dict(kind='PARTICIPATION',match_id=mid,player_id=a['player_id'],team=a['team'],status=a['participation_status'],reasons=a['failure_reasons'],review_reference=a['review_reference']))
                for issue in unknown:
                    unresolved_count+=1;line(streams['unresolved-evidence'],dict(kind='SOURCE_COMPONENT_WITHOUT_APPEARANCE',match_id=mid,**issue))
                for uid,row in delivered.items():
                    if uid not in seen_original:
                        unresolved_count+=1;association_counts['DELIVERED_UUID_NOT_IN_ORIGINAL_MATCH']+=1
                        line(streams['unresolved-evidence'],dict(kind='DELIVERED_UUID_NOT_IN_ORIGINAL_MATCH',delivered=row))
                        if isinstance(row['player'],str):unassociated_delivered_names.add((player_name(row['player']),team_name(row['team']),row['competition_name'],row['season_name']))
                active_ids={a['player_id'] for a in roster if a['active_appearance']}
                for e in frame[['id','player_id','team','competition_name','season_name']].to_dict('records'):
                    if not pd.isna(e['player_id']) and int(e['player_id']) not in active_ids:
                        pid=int(e['player_id']);identity_reasons[pid,e['team'],e['competition_name'],e['season_name']].add('SOURCE_ACTIVITY_WITHOUT_APPEARANCE')
                        unresolved_count+=1;source_counts['actor_events_without_active_appearance']+=1
                        line(streams['unresolved-evidence'],dict(kind='SOURCE_ACTIVITY_WITHOUT_APPEARANCE',match_id=mid,event_id=e['id'],player_id=pid,team=e['team']))
                line(streams['match-coverage'],dict(match_id=mid,competition_name=report['competition_name'],season_name=report['season_name'],source_pair_obtained=True,
                    original_event_count=len(frame),delivered_event_count=len(delivered),delivered_fixture_present=context_ok,
                    active_status_counts=report['active_status_counts'],event_associations=dict(match_associations),unknown_component_actors=len(unknown),
                    production_scope_policy='PENDING_TEAM_APPROVAL' if mid==3879594 else 'NO_PRODUCTION_SCOPE_AUTHORIZED'))
                if number%64==0 or number==len(reviews):
                    db.commit();print('SOURCE_RECONSTRUCTION',number,'/',len(reviews),dict(source_counts),flush=True)
            try:db.execute('CREATE UNIQUE INDEX original_uuid ON original_ids(id)')
            except sqlite3.IntegrityError as exc:raise ValueError('duplicate original UUID across match scopes') from exc
            target_unseen=db.execute('SELECT id,mid,team,player,competition,season,type FROM delivered WHERE seen=0 AND season=? AND competition IN (?,?,?,?)',(SEASON,*LEAGUES)).fetchall()
            source_counts['unreconciled_target_delivered_events']=len(target_unseen)
            # Detailed rows already emitted for observed target matches. Retain any
            # entirely unexpected target fixture as a separate unresolved fact.
            for raw in target_unseen:
                if raw[1] not in reviews:
                    unresolved_count+=1;line(streams['unresolved-evidence'],dict(kind='DELIVERED_TARGET_MATCH_OUTSIDE_PROVIDER_INVENTORY',event_id=raw[0],match_id=raw[1],team=raw[2],player_name_raw=raw[3]))
            db.commit()
    finally:
        db.close()
    for name,team,comp,season in sorted(unassociated_delivered_names):
        for pid in source_name_ids.get((name,team,comp,season),set()):
            identity_reasons[pid,team,comp,season].add('UNRECONCILED_DELIVERED_EVENT_UUID')
    # Reconcile every delivered active lineup observation, not just known joins.
    for (mid,team,pid),dl in sorted(delivered_lineups.items()):
        if mid in fixtures and dl['active'] and (mid,team,pid) not in lineup_seen:
            f=fixtures[mid];identity_reasons[pid,team,f['competition']['competition_name'],f['season']['season_name']].add('DELIVERED_APPEARANCE_ABSENT_FROM_SOURCE_ROSTER')
    active_by_club=defaultdict(list);metric_by_club=all_metrics;clubs=[];seasons=[];transfers=[]
    for k,rows in sorted(all_appearances.items()):
        delivered=candidates.get(k);role=delivered['position_group'] if delivered else None
        summary=aggregate_context(rows,metric_by_club[k],provider_complete=len(reviews)==len(fixtures),identity_reasons=identity_reasons[k],role=role)
        summary.update(player_id=k[0],team=k[1],team_id=rows[0]['team_id'],competition_name=k[2],season_name=k[3],
            delivered_table_qualified=bool(delivered and delivered['delivered_rules_eligible']),
            delivered_minutes=delivered['minutes'] if delivered else None,delivered_event_reconciliation=dict(context_reconciliation[k]),
            delivered_mapping_statuses=sorted({r['delivered_mapping_status'] for r in rows}),
            includes_policy_pending_3879594=any(r['match_id']==3879594 for r in rows))
        dr=[r for r in rows if r['delivered_fixture_present']]
        dm=[r for r in all_metrics[k] if r['match_id'] in {a['match_id'] for a in dr}]
        ds=aggregate_context(dr,dm,provider_complete=True,identity_reasons=identity_reasons[k],role=role) if dr else None
        summary['delivered_scope_comparison']=None if ds is None else {c:ds[c] for c in ('supported_minutes','provider_scope_complete_minutes','complete_provider_scope_at_least_900','candidate_900_minutes_evidence_met','components')}
        clubs.append(summary);active_by_club[k[0],k[3]].append(summary)
    for (pid,season),contexts in sorted(active_by_club.items()):
        keys=[(c['player_id'],c['team'],c['competition_name'],c['season_name']) for c in contexts]
        rows=[r for k in keys for r in all_appearances[k]];ms=[r for k in keys for r in all_metrics[k]]
        reasons=sorted({r for k in keys for r in identity_reasons[k]})
        combined=aggregate_context(rows,ms,provider_complete=True,identity_reasons=reasons)
        combined.update(original_contexts=[dict(team=c['team'],team_id=c['team_id'],competition_name=c['competition_name'],season_name=c['season_name']) for c in contexts],
            aggregation_status='SOURCE_FACTS_COMPARISON_ONLY_NO_REFERENCE_POLICY',roles_observed=sorted({c['delivered_role'] for c in contexts if c['delivered_role']}))
        seasons.append(combined)
        if len(contexts)>1:transfers.append(transfer_comparison(contexts,combined))
    for name,rows in [('player-club-summaries',clubs),('player-season-summaries',seasons),('transfer-policy-comparison',transfers)]:
        with (output/(name+'.jsonl')).open('x',encoding='utf-8',newline='\n') as f:
            for row in rows:line(f,row)
    with (output/'numerator-denominator-reconciliation.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for c in clubs:
            for name,value in c['components'].items():
                line(f,dict(player_id=c['player_id'],team=c['team'],competition_name=c['competition_name'],season_name=c['season_name'],component=name,
                    raw_source_match_ids=c['match_ids'],supported_exposure_match_ids=c['supported_match_ids'],unresolved_match_ids=c['unresolved_match_ids'],
                    supported_minutes=c['supported_minutes'],complete_provider_scope_minutes=c['provider_scope_complete_minutes'],
                    aligned_subset_is_full_provider_scope=c['provider_observed_exposure_complete'] and value['aligned_match_ids']==c['match_ids'],**value))
    with (output/'delivered-component-comparison.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for c in clubs:
            for name,event_type in [('tackles','Tackle'),('interceptions','Interception'),('recoveries','Ball Recovery')]:
                d=delivered_components.get((*key(c),event_type))
                source=c['delivered_scope_comparison']
                source_count=None if source is None else source['components'][name]['raw_source_count']
                delivered_count=None if d is None or pd.isna(d['count']) else int(d['count'])
                complete_minutes=None if source is None else source['provider_scope_complete_minutes']
                line(f,dict(player_id=c['player_id'],team=c['team'],competition_name=c['competition_name'],season_name=c['season_name'],component=name,
                    delivered_count=delivered_count,original_source_count_for_delivered_fixture_scope=source_count,
                    count_difference=None if delivered_count is None or source_count is None else delivered_count-source_count,
                    delivered_minutes=c['delivered_minutes'],source_complete_delivered_scope_minutes=complete_minutes,
                    minutes_difference=None if c['delivered_minutes'] is None or complete_minutes is None else c['delivered_minutes']-complete_minutes,
                    status='MISSING_DELIVERED_COMPONENT_ROW' if d is None else 'SOURCE_OR_DELIVERED_SCOPE_UNAVAILABLE' if source_count is None else
                        'COUNTS_AGREE_ON_DELIVERED_FIXTURE_SCOPE' if delivered_count==source_count else 'COUNT_DISAGREEMENT_REVIEW',
                    note='Count and arithmetic comparisons only; no source trust, full historical coverage or scoring approval inferred'))
    with (output/'identity-reconciliation.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for c in clubs:
            line(f,{name:c[name] for name in ('player_id','team_id','team','competition_name','season_name','raw_player_names','normalized_player_names',
                'delivered_event_reconciliation','delivered_mapping_statuses','identity_reasons')})
    write_new(output/'source-name-collisions.json',[
        dict(player_name_normalized=k[0],team=k[1],competition_name=k[2],season_name=k[3],distinct_source_player_ids=sorted(ids),
             status='NAME_COLLISION_IDS_RETAINED_SEPARATELY_NO_NAME_ONLY_ID_JOIN') for k,ids in sorted(source_name_ids.items()) if len(ids)>1])
    clubmap={key(c):c for c in clubs};matrix=[]
    for k in sorted(set(candidates)|set(clubmap)):
        c=clubmap.get(k);d=candidates.get(k)
        matrix.append(dict(player_id=k[0],team=k[1],competition_name=k[2],season_name=k[3],
            delivered_role=None if d is None else d['position_group'],delivered_table_qualified=bool(d and d['delivered_rules_eligible']),
            source_appearance_context_present=c is not None,known_supported_minutes=None if c is None else c['known_supported_minutes'],
            unresolved_appearances=None if c is None else c['withheld_appearance_count'],
            candidate_900_minutes_evidence_met=bool(c and c['candidate_900_minutes_evidence_met']),
            delivered_scope_candidate_900_met=bool(c and c['delivered_scope_comparison'] and c['delivered_scope_comparison']['candidate_900_minutes_evidence_met']),
            component_scopes_ready=False if c is None else all(c['components'][n]['provider_scope_status']=='SOURCE_VERIFIED_CANDIDATE_MEASUREMENT' for n in ('tackles','interceptions','recoveries',*COUNT_NAMES[3:7])),
            identity_reasons=[] if c is None else c['identity_reasons'],
            blockers=sorted(set(['independent_identity_attestation_pending','exposure_and_role_policy_pending','reference_membership_policy_pending','individual_scoring_policies_pending','production_contract_pending','publication_not_authorized']+
                (['missing_source_appearance_context'] if c is None else (['unresolved_participation_or_scope'] if not c['provider_observed_exposure_complete'] else [])+
                (['serie_a_3879594_scope_pending'] if c['includes_policy_pending_3879594'] else [])+
                (['historical_ligue1_coverage_unresolved'] if k[2]=='Ligue 1' else [])))),production_certified=False,reference_member=False))
    with (output/'eligibility-readiness-matrix.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for row in matrix:line(f,row)
    active_count=sum(len(r) for r in all_appearances.values())
    # Keep the established season accountant and its noncertifying gates. The
    # new evidence matrix adds scope facts, never edits its certification flags.
    all_appearances.clear();all_metrics.clear()
    flat_fixtures=[dict(match_id=f['match_id'],competition_name=f['competition']['competition_name'],season_name=f['season']['season_name']) for f in fixtures.values()]
    qualified=[r for r in candidates.values() if r['delivered_rules_eligible']]
    old_accounting=season_readiness(flat_fixtures,list(delivered_metadata.values()),
        pq.read_table(lineups,columns=['match_id','team','player_id','position']).to_pylist(),qualified,
        (load_json(reviews[mid]['report_path']) for mid in sorted(reviews)))
    write_new(output/'existing-season-readiness.json',old_accounting)
    del old_accounting
    frame_coverage=inspect_frame_contexts(frames);write_new(output/'360-coverage.json',frame_coverage)
    total_seconds=sum((exact(c['supported_seconds']) for c in clubs),Fraction(0))
    coverage=dict(provider_fixture_count=len(fixtures),delivered_target_fixture_count=sum(mid in delivered_metadata for mid in fixtures),
        missing_delivered_fixture_ids=sorted(set(fixtures)-set(delivered_metadata)),
        leagues=[dict(competition_name=league,season_name=SEASON,provider_fixture_count=sum(f['competition']['competition_name']==league for f in fixtures.values()),
            delivered_fixture_count=sum(f['competition']['competition_name']==league and mid in delivered_metadata for mid,f in fixtures.items()),active_status_counts=dict(league_statuses[league]),
            historical_full_season_completeness='NOT_CERTIFIED_BY_PROVIDER_LIST') for league in LEAGUES])
    write_new(output/'evidence-coverage-and-missingness.json',coverage)
    summary=dict(schema_version='source-player-reconstruction/v1',notice=NOTICE,provider_matches=len(fixtures),roster_actor_match_records=roster_count,
        active_appearances=active_count,participation_counts={s:source_counts[s] for s in ('STRUCTURALLY_VALID','CONFLICTING_EVIDENCE','INCOMPLETE_EVIDENCE')},
        player_club_contexts=len(clubs),player_season_contexts=len(seasons),stable_player_ids=len({c['player_id'] for c in clubs}),
        known_supported_minutes=rational(total_seconds/60),known_supported_minutes_display=float(total_seconds/60),
        withheld_appearance_count=source_counts['CONFLICTING_EVIDENCE']+source_counts['INCOMPLETE_EVIDENCE'],withheld_minutes=None,
        source_events=source_counts['original_events'],delivered_scan=delivered_scan,event_associations=dict(association_counts),
        unreconciled_target_delivered_events=source_counts['unreconciled_target_delivered_events'],
        actor_events_without_active_appearance=source_counts['actor_events_without_active_appearance'],
        source_name_collision_keys=sum(len(ids)>1 for ids in source_name_ids.values()),
        contexts_with_identity_disagreements=sum(bool(c['identity_reasons']) for c in clubs),
        delivered_candidate_contexts=len(candidates),delivered_table_qualified_contexts=sum(bool(r['delivered_rules_eligible']) for r in candidates.values()),
        source_complete_candidate_900_contexts=sum(r['candidate_900_minutes_evidence_met'] for r in matrix),
        source_complete_candidate_900_delivered_scope_contexts=sum(r['delivered_scope_candidate_900_met'] for r in matrix),
        source_complete_candidate_900_with_core_component_scope=sum(r['candidate_900_minutes_evidence_met'] and r['component_scopes_ready'] for r in matrix),
        multi_club_player_seasons=len(transfers),transfer_combination_changes_threshold=sum(r['threshold_changes_if_combination_authorized'] for r in transfers),
        unresolved_evidence_records=unresolved_count,progressive_preparation=dict(passing_counts),target_360_rows=frame_coverage['target_rows'],
        production_certified_contexts=0,publication_authorized=False,policy_pending_fixture_ids=[3879594],
        source_review_index_sha256=file_hash(index),source_verification_revision=idx['validator_revision'],table_integrity=table_checks)
    write_new(output/'summary.json',summary)
    write_new(output/'next-step-readiness.json',dict(notice=NOTICE,source_statistics_reconstruction_complete=True,production_scoring_ready=False,
        blockers=['independent_actor_identity_and_provenance_attestation','contradictory_and_incomplete_appearance_resolution','approved_exposure_and_role_convention',
            'metric_definition_and_reportability_review','Ligue_1_historical_coverage','3879594_rebuild_scope','transfer_and_reference_membership_policy',
            'individual_FIFA_and_press_policy','true_line_breaking_definition_and_target_360_evidence','OVR_policy','production_evidence_contract','publication_authorization'],
        production_certified_contexts=0,delivered_dataset_writes=0,ratings_generated=0))
    write_new(output/'input-receipts.json',[receipts[k] for k in sorted(receipts)])
    if recipe()!=revision:raise ValueError('implementation changed during reconstruction; output left unsealed')
    for r in receipts.values():
        if Path(r['path']).stat().st_size!=r['size_bytes']:raise ValueError('input size changed during reconstruction')
    artifacts=[dict(path=p.name,size_bytes=p.stat().st_size,sha256=file_hash(p)) for p in sorted(output.iterdir()) if p.is_file()]
    write_new(output/'run-manifest.json',dict(schema_version='source-reconstruction-run/v1',recipe=revision,input_paths=[str(p.resolve()) for p in inputs],
        source_manifest_sha256=file_hash(manifest),artifacts=artifacts,production_certified=False,publication_authorized=False))
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();print(json.dumps(reconstruct(output=args.output),sort_keys=True,indent=2))


if __name__=='__main__':main()
