"""Offline investigation/readiness over the retained real Phase 1 pilot.

No retrieval. All outputs are exclusive review artifacts in a new directory.
No changes to delivered data, source records, scoring, or production attestations.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from scripts.audit_dri_readiness import candidate_population
from scripts.source_verification_batch import (EvidenceStore, manifest_from_phase1,
                                              load_json, write_new, dry_run, digest)
from src.season_verification import season_readiness

ORIGINAL_CONFLICTS = {3754217:(3437,3496,3517,6746),3829416:(3230,16462),3879549:(6636,7026,7147)}


def investigate(report, events, original_ids):
    """Retain evidence views, not corrected intervals or guessed transitions."""
    cases=[]
    event_binding=report['artifacts']['events']
    for row in report['players']:
        p,v=row['player'],row['validation']
        pid=p['context']['player_id']
        if pid not in original_ids and v['status']!='CONFLICTING_EVIDENCE':
            continue
        tid=p['team_id']
        relevant=[]
        for event in events:
            if event['team']['id']!=tid:
                continue
            typ=event['type']['name']
            snapshot=next((x for x in event.get('tactics',{}).get('lineup',[]) if x['player']['id']==pid),None)
            actor=event.get('player',{}).get('id')==pid
            incoming=event.get('substitution',{}).get('replacement',{}).get('id')==pid
            boundary=typ in ('Half Start','Half End')
            if boundary or snapshot or incoming or actor and typ in ('Player Off','Player On','Substitution','Foul Committed','Bad Behaviour'):
                if actor and typ in ('Foul Committed','Bad Behaviour') and not event.get('foul_committed',{}).get('card') and not event.get('bad_behaviour',{}).get('card'):
                    continue
                relevant.append(dict(source_reference=event_binding['source_reference']+'#/event/'+event['id'],
                                     original_event=event,actor_position_snapshot=snapshot))
        # Explicit order views show why sorting displayed minute across halves is
        # not a chronology. Neither view edits the retained source observations.
        by_index=sorted(relevant,key=lambda x:x['original_event']['index'])
        by_period=sorted(relevant,key=lambda x:(x['original_event']['period'],x['original_event']['timestamp'],x['original_event']['index']))
        reverse=[]
        for i,raw in enumerate(p['raw_positions']):
            stint=json.loads(raw)
            if stint.get('from_period') is not None and stint.get('to_period') is not None and stint['from_period']>stint['to_period']:
                reverse.append(i)
        cases.append(dict(match_id=report['match_id'],player_id=pid,team_id=tid,team=p['context']['team_key'],
                          player_name=p['player_name'],was_phase1_conflict=pid in original_ids,
                          classification='D_CONTRADICTORY_UPSTREAM_SOURCE_OBSERVATIONS',
                          adapter_interpretation_caused_original_conflict=False,
                          clock_convention_supported=True,period_boundaries_available=all(b['start_seconds'] is not None and b['end_seconds'] is not None for b in report['boundaries']),
                          identity_context_conflict=False,reversed_stint_indices=reverse,
                          raw_positions=p['raw_positions'],adapted_observations=p['observations'],
                          source_checks=p['source_checks'],validator_issues=v['issues'],
                          original_event_index_order=by_index,period_clock_order=by_period,
                          source_provenance=p['observations'][0]['provenance_refs'] if p['observations'] else [],
                          outcome='CONFLICT_PRESERVED_MINUTES_WITHHELD',elapsed_seconds=None,
                          scope_note='Implementation previously missed some cross-event contradictions; no upstream record was repaired.'))
    return cases


def audit(phase1, output):
    phase1,output=Path(phase1),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    manifest_path=output/'retrieval-manifest.json'
    write_new(manifest_path,manifest_from_phase1(phase1))
    plan=dry_run(manifest_path)
    write_new(output/'offline-plan.json',plan)
    store=EvidenceStore(output/'offline-store',manifest_path)
    selected=sorted(load_json(phase1/'selection.json'))
    results=store.execute(selected)  # OFFLINE: transport and network flag omitted.
    if any('report' not in r for r in results):
        raise ValueError('Retained pilot failed offline artifact verification')
    reports=[r['report'] for r in results]
    cases=[]
    for report in reports:
        events=load_json(report['artifacts']['events']['path'])
        cases.extend(investigate(report,events,ORIGINAL_CONFLICTS.get(report['match_id'],())))
    write_new(output/'contradiction-investigations.json',cases)
    # Resume must reuse immutable validated artifacts/reports and make no request.
    resumed=store.execute(selected)
    if any(r['status']!='SKIPPED_PREVIOUSLY_VALIDATED_ARTIFACTS' for r in resumed):
        raise ValueError('Offline resume unexpectedly reprocessed retained pilot')
    write_new(output/'offline-resume.json',[{k:v for k,v in r.items() if k!='report'} for r in resumed])
    minutes=pd.read_parquet('data/validation/arpit-refresh-review/player_minutes.parquet')
    recovery=pd.read_parquet('data/validation/arpit-refresh-review/recovery_per90.parquet')
    candidates,_=candidate_population(minutes,recovery)
    qualified=candidates[candidates.delivered_rules_eligible].to_dict('records')
    metadata=pd.read_parquet('data/validation/arpit-match-context-review/match_metadata.parquet').to_dict('records')
    lineups=pd.read_parquet('data/raw/statsbomb_lineups.parquet').where(pd.notna, None).to_dict('records')
    readiness=season_readiness(load_json(phase1/'fixtures-normalized.json'),metadata,lineups,qualified,reports)
    write_new(output/'season-readiness.json',readiness)
    summary=dict(mode='OFFLINE_ONLY',network_requests=0,readiness=readiness['summary'],
                 original_conflicts_investigated=sum(c['was_phase1_conflict'] for c in cases),
                 additional_conflicts_found=sum(not c['was_phase1_conflict'] for c in cases),
                 contradictions_repaired=0,transferred_actors=readiness['transferred_actors'],
                 missing_serie_a_inclusion='PENDING_TEAM_APPROVAL; no delivered data modification',
                 input_manifest_sha256=digest(manifest_path.read_bytes()),
                 results=[{k:v for k,v in r.items() if k!='report'} for r in results])
    write_new(output/'phase1b-summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase1',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.phase1,args.output),indent=2))


if __name__=='__main__':
    main()
