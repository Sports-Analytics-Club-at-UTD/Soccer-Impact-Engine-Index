"""Offline invariants and review inventory over a sealed candidate reconstruction."""
import argparse
from collections import Counter,defaultdict
from fractions import Fraction
from itertools import zip_longest
import math
from pathlib import Path

from scripts.source_verification_batch import load_json,write_new,bound_document
from scripts.reconstruct_player_evidence import records,file_hash,line
from src.source_reconstruction import COUNT_NAMES,exact,key,rational


def audit(run,output):
    run,output=Path(run),Path(output)
    if output.exists():raise ValueError('new exclusive review output required')
    sealed=load_json(run/'run-manifest.json')
    for r in sealed['artifacts']:
        if file_hash(run/r['path'])!=r['sha256']:raise ValueError('derived fingerprint mismatch: '+r['path'])
    output.mkdir(parents=True,exist_ok=False)
    summary=load_json(run/'summary.json');statuses=Counter();durations=defaultdict(Fraction)
    source_counts=defaultdict(Counter);component_issues=defaultdict(Counter);metric_totals=Counter();team_ids=defaultdict(set)
    seen=set();row_count=0;per_match=Counter();review_refs={}
    with (output/'unresolved-measurement-inventory.jsonl').open('x',encoding='utf-8',newline='\n') as out:
        for a,m in zip_longest(records(run/'appearance-ledger.jsonl'),records(run/'match-component-measurements.jsonl')):
            if a is None or m is None:raise ValueError('appearance/numerator row count mismatch')
            identity=(a['match_id'],a['team_id'],a['player_id'])
            if identity!=(m['match_id'],m['team_id'],m['player_id']) or identity in seen:raise ValueError('duplicate/misaligned appearance identity')
            seen.add(identity);row_count+=1;per_match[a['match_id']]+=1;statuses[a['participation_status']]+=1;k=key(a)
            review_refs[a['match_id']]=a['review_reference']
            team_ids[a['team'],a['competition_name'],a['season_name']].add(a['team_id'])
            seconds=None if a['validated_elapsed_seconds'] is None else exact(a['validated_elapsed_seconds'])
            if a['participation_status']=='STRUCTURALLY_VALID':
                if seconds is None or sum((exact(p['elapsed_seconds']) for p in a['position_allocation']),Fraction(0))!=seconds:raise ValueError('position/exposure conservation failed')
                durations[k]+=seconds
            elif seconds is not None or a['position_allocation'] is not None:raise ValueError('unresolved exposure promoted')
            if a['production_certified'] is not False or m['line_breaking_count'] is not None:raise ValueError('unsupported trust/line-breaking output')
            for name,c in m['components'].items():
                if len(c['event_ids'])!=len(set(c['event_ids'])) or len(c['event_ids'])!=c['count']:raise ValueError('numerator event cardinality failed')
                source_counts[k][name]+=c['count'];metric_totals[name]+=c['count']
                if c['per90'] is not None:
                    if seconds is None or seconds<=0 or c['aligned_count']!=c['count'] or c['reasons']:raise ValueError('unsupported appearance rate')
                    if not math.isclose(c['per90'],float(Fraction(c['count']*5400,1)/seconds),rel_tol=1e-12,abs_tol=1e-12):raise ValueError('rate arithmetic failed')
                for reason in c['reasons']:component_issues[name][reason]+=1
                if c['reasons']:
                    line(out,dict(match_id=a['match_id'],player_id=a['player_id'],team=a['team'],component=name,reasons=c['reasons'],
                        unaligned_event_ids=c['unaligned_event_ids'],raw_count=c['count'],supported_minutes=a['validated_elapsed_minutes'],
                        rate=c['per90'],review_reference=a['review_reference']))
    if any(len(ids)!=1 for ids in team_ids.values()):raise ValueError('same club context has different numeric source team IDs')
    if row_count!=summary['active_appearances'] or statuses!=Counter(summary['participation_counts']):raise ValueError('appearance count mismatch')
    if len(per_match)!=summary['provider_matches']:raise ValueError('missing match/player ledger coverage')
    clubs=list(records(run/'player-club-summaries.jsonl'));club_lookup={key(c):c for c in clubs}
    if len(club_lookup)!=len(clubs):raise ValueError('duplicate player-club context')
    component_ready=Counter();identity_flags=Counter();role_candidates=Counter();full_minutes=0
    for c in clubs:
        k=key(c)
        if exact(c['supported_seconds'])!=durations[k]:raise ValueError('club exposure does not equal match sum')
        if c['withheld_appearance_count'] and (c['provider_scope_complete_minutes'] is not None or c['withheld_minutes'] is not None):raise ValueError('partial exposure was promoted')
        if c['candidate_900_minutes_evidence_met']:
            if not c['provider_observed_exposure_complete'] or durations[k]<54000:raise ValueError('unsafe 900-minute candidate')
            role_candidates[c['role_group']]+=1
        full_minutes+=c['provider_scope_complete_minutes'] is not None
        identity_flags.update(c['identity_reasons'])
        for name,v in c['components'].items():
            if v['raw_source_count']!=source_counts[k][name]:raise ValueError('club numerator does not equal match sum')
            if v['provider_scope_per90'] is not None:
                if not c['provider_observed_exposure_complete'] or v['aligned_match_ids']!=c['match_ids']:raise ValueError('numerator/denominator scope mismatch')
                if not math.isclose(v['provider_scope_per90'],float(Fraction(v['raw_source_count']*5400,1)/durations[k]),rel_tol=1e-12,abs_tol=1e-12):raise ValueError('club rate arithmetic failed')
                component_ready[name]+=1
        if c['reference_member'] or c['production_certified']:raise ValueError('unapproved reference admission')
    if rational(sum(durations.values(),Fraction(0))/60)!=summary['known_supported_minutes']:raise ValueError('global minutes not conserved')
    transfers=list(records(run/'transfer-policy-comparison.jsonl'))
    for t in transfers:
        if t['reference_member'] or t['nominated_reference_context'] is not None or any(s['approved'] for s in t['scenarios']):raise ValueError('unapproved transfer membership')
        keys=[(t['player_id'],c['team'],c['competition_name'],t['season_name']) for c in t['original_contexts']]
        matches=[mid for k in keys for mid in club_lookup[k]['match_ids']]
        if len(matches)!=len(set(matches)):raise ValueError('duplicate transferred-player match contribution')
        if exact(t['combined_supported_minutes'])!=sum((exact(club_lookup[k]['supported_minutes']) for k in keys),Fraction(0)):raise ValueError('transfer minutes not conserved')
        for name in COUNT_NAMES:
            if t['combined_raw_counts'][name]!=sum(club_lookup[k]['components'][name]['raw_source_count'] for k in keys):raise ValueError('transfer raw counts not conserved')
    comparison=Counter(r['status'] for r in records(run/'delivered-component-comparison.jsonl'))
    activity_types=Counter()
    with (output/'source-activity-review.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for issue in records(run/'unresolved-evidence.jsonl'):
            if issue['kind']!='SOURCE_ACTIVITY_WITHOUT_APPEARANCE':continue
            ref=review_refs[issue['match_id']]
            if file_hash(ref['path'])!=ref['sha256']:raise ValueError('activity review source fingerprint changed')
            review=load_json(ref['path'])
            events=bound_document(review['artifacts']['events']).records()
            event=next(e for e in events if e['id']==issue['event_id'])
            lineups=bound_document(review['artifacts']['lineups']).records()
            actor=next(p for t in lineups for p in t['lineup'] if p['player_id']==issue['player_id'])
            activity_types[event['type']['name']]+=1
            line(f,dict(**issue,original_event_type=event['type'],original_player=event['player'],
                original_position=event.get('position'),original_card=event.get('bad_behaviour',{}).get('card'),
                original_period=event['period'],original_timestamp=event['timestamp'],original_roster_positions=actor['positions'],
                interpretation='ACTIVITY_RECORD_ONLY_NO_PLAYING_TIME_IMPLIED',review_reference=ref,
                production_certified=False))
    with (output/'identity-context-review.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for c in clubs:
            if c['identity_reasons']:
                line(f,{k:c[k] for k in ('player_id','team_id','team','competition_name','season_name','raw_player_names','identity_reasons','match_ids')})
    complete_minute_differences=sum(r['minutes_difference'] is not None and abs(r['minutes_difference'])>1e-9 for r in records(run/'delivered-component-comparison.jsonl') if r['component']=='tackles')
    report=dict(schema_version='source-reconstruction-audit/v1',input_run_manifest_sha256=file_hash(run/'run-manifest.json'),
        audit_implementation_sha256=file_hash(__file__),invariants_passed=True,appearance_counts=dict(statuses),match_count=len(per_match),
        player_club_contexts=len(clubs),complete_provider_observed_exposure_contexts=full_minutes,known_supported_minutes=summary['known_supported_minutes'],
        candidate_900_contexts_by_role=dict(role_candidates),identity_and_activity_review_flags=dict(identity_flags),
        source_activity_event_types=dict(activity_types),
        component_source_totals=dict(metric_totals),component_complete_rate_contexts=dict(component_ready),component_appearance_failure_reasons={k:dict(v) for k,v in sorted(component_issues.items())},
        delivered_component_comparison=dict(comparison),contexts_with_complete_minutes_different_from_delivered=complete_minute_differences,
        multi_club_player_seasons=len(transfers),transfer_threshold_change_player_ids=[t['player_id'] for t in transfers if t['threshold_changes_if_combination_authorized']],
        provider_scope_vs_delivered_scope_900_change_contexts=[dict(player_id=c['player_id'],team=c['team'],competition_name=c['competition_name'],provider_scope=c['candidate_900_minutes_evidence_met'],
            delivered_scope=c['delivered_scope_comparison']['candidate_900_minutes_evidence_met']) for c in clubs if c['delivered_scope_comparison'] and c['candidate_900_minutes_evidence_met']!=c['delivered_scope_comparison']['candidate_900_minutes_evidence_met']],
        production_certified_contexts=0,ratings_generated=0,publication_authorized=False)
    write_new(output/'review-summary.json',report)
    write_new(output/'artifact-inventory.json',dict(input_run_manifest_sha256=report['input_run_manifest_sha256'],audit_implementation_sha256=report['audit_implementation_sha256'],
        artifacts=[dict(path=p.name,sha256=file_hash(p),size_bytes=p.stat().st_size) for p in sorted(output.iterdir()) if p.is_file()]))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();print(audit(args.input,args.output))


if __name__=='__main__':main()
