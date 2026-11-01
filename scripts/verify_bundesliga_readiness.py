"""Separate, bounded Bundesliga source verification; no scoring or population writes.

Run with python -B -m scripts.verify_bundesliga_readiness prepare|acquire|analyze.
Acquisition is explicit, at most eight matches per invocation, and pinned to the
same provider revision as the existing four-league evidence. All outputs use
exclusive creation. Existing sealed evidence is only read.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from scripts.source_verification_batch import (
    EvidenceStore, SCHEMA, bound_document, digest, load_json, now, payload,
    public_transport, write_new,
)
from src.source_reconstruction import (
    COUNT_NAMES, aggregate_context, appearance_rows, exact, flatten_events,
    measurements, rational, reconcile_event,
)
from src.independent_source_checks import check_match
from src.participation_intervals import VALID

ROOT = Path('data/source-evidence/bundesliga-targeted-2026-10-29')
OUT = Path('data/derived/bundesliga-targeted-2026-10-29')
EVENTS = Path('data/validation/drive-raw-review/statsbomb_team_events.parquet')
MINUTES = Path('data/processed/player_minutes.parquet')
RECOVERY = Path('data/processed/recovery_per90.parquet')
FILTER = [('competition_name', '=', '1. Bundesliga'), ('season_name', '=', '2015/2016')]
FOUR = Path('data/derived/phase3-step2-source-reconstruction-2026-10-27')
TRANSFERS = {3058, 3083, 5460, 6330, 7852, 8217, 9461, 20027, 27341}
DEFENSIVE = ('tackles', 'interceptions', 'recoveries')
PRESS = ('pressured_pass_attempts', 'pressured_pass_completed',
         'pressured_dribble_attempts', 'pressured_dribble_completed')


def file_hash(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def records(path):
    with Path(path).open(encoding='utf8') as f:
        for row in f:
            yield json.loads(row)


def line(stream, row):
    stream.write(json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n')


def prepare():
    """Get one original fixture list; require exact delivered/provider scope equality."""
    if ROOT.exists():
        raise ValueError('dedicated source root already exists; do not overwrite')
    revision = load_json('data/source-evidence/phase1-2026-10-27/revision.json')['sha']
    url = f'https://raw.githubusercontent.com/statsbomb/open-data/{revision}/data/matches/9/27.json'
    # Retrieve and check before creating the exclusive source directory.
    raw = public_transport(url)
    fixtures = json.loads(raw)
    delivered = pq.read_table(EVENTS, columns=['match_id'], filters=FILTER)
    ids = sorted(set(delivered.column('match_id').to_pylist()))
    provider_ids = sorted(f['match_id'] for f in fixtures)
    if len(ids) != 34 or ids != provider_ids:
        raise ValueError('provider fixture inventory differs from explicit 34-match delivered scope')
    if any((f['competition']['competition_id'], f['season']['season_id']) != (9, 27) for f in fixtures):
        raise ValueError('provider competition/season disagreement')
    ROOT.mkdir(parents=True, exist_ok=False)
    path = ROOT / 'matches-9-27.json'
    path.write_bytes(raw)
    binding = dict(path=str(path.resolve()), sha256=digest(raw), source_reference=url,
                   provider_revision=revision, retrieved_at=now())
    write_new(ROOT / 'matches-9-27.request.json', dict(outcome='success', **binding))
    manifest = dict(schema_version=SCHEMA, provider_revision=revision, created_at=now(),
        scope='Bundesliga 2015/2016 observed provider list only; no full-season or scoring certification',
        fixture_documents={'matches-9-27.json': binding},
        matches=[dict(match_id=mid, competition_name='1. Bundesliga', season_name='2015/2016',
                      fixture_document='matches-9-27.json', inclusion_policy='VERIFICATION_ONLY_NO_REFERENCE_ADMISSION',
                      artifacts={}) for mid in ids])
    write_new(ROOT / 'manifest.json', manifest)
    write_new(ROOT / 'scope.json', dict(match_ids=ids, delivered_events=delivered.num_rows,
        provider_fixture_count=len(fixtures), fixture_sha256=digest(raw),
        retained_original_bundesliga_pairs_in_existing_four_league_review=0,
        production_certified=False, publication_authorized=False))
    print('PREPARED', len(ids), 'fixtures', ids, flush=True)


def acquire(ids):
    store = EvidenceStore(ROOT / 'store', ROOT / 'manifest.json')
    results = store.execute(ids, allow_network=True, batch_limit=8)
    print(json.dumps([dict(match_id=r['match_id'], status=r['status'],
        active_status_counts=r.get('report', {}).get('active_status_counts'),
        error=r.get('report', {}).get('error')) for r in results]), flush=True)


def position_group(position):
    """Display grouping only; preserves raw positions and ties in outputs."""
    if position == 'Goalkeeper': return 'GK'
    if position in ('Center Back', 'Left Center Back', 'Right Center Back'): return 'CB'
    if position in ('Defensive Midfield', 'Center Defensive Midfield', 'Left Defensive Midfield', 'Right Defensive Midfield'): return 'DM'
    if position in ('Center Midfield', 'Left Center Midfield', 'Right Center Midfield'): return 'CM'
    if position in ('Left Back', 'Right Back', 'Left Wing Back', 'Right Wing Back'): return 'FB'
    if position in ('Left Midfield', 'Right Midfield'): return 'WM'
    if position in ('Center Attacking Midfield', 'Left Attacking Midfield', 'Right Attacking Midfield'): return 'AM'
    if position in ('Center Forward', 'Left Center Forward', 'Right Center Forward', 'Left Wing', 'Right Wing', 'Secondary Striker'): return 'ATT'
    return 'UNKNOWN'


def position_summary(positions):
    groups = defaultdict(Fraction)
    for p, value in positions.items(): groups[position_group(p)] += exact(value)
    top = max(groups.values(), default=Fraction(0))
    dominant = sorted(k for k, v in groups.items() if v == top) if top else []
    return dict(group_minutes={k: rational(v) for k, v in sorted(groups.items())},
                most_played_supported_groups=dominant,
                comparison_group=('MID' if dominant[0] in ('DM', 'CM') else 'CB' if dominant[0] == 'CB' else None) if len(dominant) == 1 else None,
                observed_positions=sorted(positions))


def press_evidence(metric_rows, bad_actor_ids=()):
    """Press is an action ratio; retain sub-40 values even without full minutes.

    Source identity and component actors must agree. Unresolved participation is
    separately disclosed and never converted to verified exposure.
    """
    if not metric_rows or any(r['player_id'] in bad_actor_ids for r in metric_rows):
        return dict(status='N/A', attempts=None, successes=None, measured_percent=None,
                    observed_40_actions=False, below_40_limited_data=False)
    counts = {n: sum(r['components'][n]['count'] for r in metric_rows) for n in PRESS}
    attempts = counts[PRESS[0]] + counts[PRESS[2]]
    successes = counts[PRESS[1]] + counts[PRESS[3]]
    return dict(status='SUPPORTED_ACTION_RATIO' if attempts else 'N/A_NO_ATTEMPTS', **counts,
                attempts=attempts, successes=successes,
                measured_percent=100 * successes / attempts if attempts else None,
                observed_40_actions=attempts >= 40, below_40_limited_data=0 < attempts < 40)


def player_readiness(clubs, metric_rows, bad_actor_ids=()):
    """No ratings. Aligned subsets carry their own numerator and denominator."""
    pid = clubs[0]['player_id']
    positions = defaultdict(Fraction)
    for c in clubs:
        for p, v in c['source_position_minutes'].items(): positions[p] += exact(v)
    pos = position_summary({p: rational(v) for p, v in positions.items()})
    components = {}
    for n in DEFENSIVE:
        supported = [c['components'][n] for c in clubs if c['components'][n]['aligned_appearance_count']]
        ids = [mid for c in supported for mid in c['aligned_match_ids']]
        if len(ids) != len(set(ids)): raise ValueError('overlapping actor fixture contributions')
        minutes = sum((exact(c['aligned_subset_minutes']) for c in supported), Fraction(0))
        count = sum(c['aligned_subset_count'] for c in supported)
        okay = bool(minutes > 0 and pid not in bad_actor_ids)
        components[n] = dict(status='SUPPORTED_OBSERVED_SUBSET' if okay else 'N/A',
            supported_count=count if okay else None, supported_minutes=rational(minutes) if okay else None,
            supported_match_ids=sorted(ids) if okay else [],
            per90=float(Fraction(count * 90, 1) / minutes) if okay else None,
            unresolved_appearance_count=sum(c['withheld_appearance_count'] for c in clubs), rating=None)
    press = press_evidence(metric_rows, bad_actor_ids)
    okay_role = pos['comparison_group'] in ('MID', 'CB')
    return dict(player_id=pid, season_name='2015/2016', names=sorted({n for c in clubs for n in c['raw_player_names']}),
        clubs=[dict(team=c['team'], team_id=c['team_id'], match_ids=c['match_ids']) for c in clubs],
        source_identity_supported=pid not in bad_actor_ids,
        known_supported_minutes=sum(c['known_supported_minutes'] for c in clubs),
        all_observed_appearance_minutes_supported=all(c['provider_observed_exposure_complete'] for c in clubs),
        unresolved_match_ids=sorted({m for c in clubs for m in c['unresolved_match_ids']}),
        source_position_minutes={p:rational(v) for p,v in sorted(positions.items())}, **pos,
        defensive=components, press=press, line_breaking=None,
        partial_season_coverage=True, season_completeness='NOT_ESTABLISHED_BY_OBSERVED_PROVIDER_LIST',
        limited_data=True, minimum_900_normal_population_met=sum(c['known_supported_minutes'] for c in clubs)>=900,
        provisional_rating_technically_possible=okay_role and pid not in bad_actor_ids and (
            any(c['status']!='N/A' for c in components.values()) or press['attempts'] is not None and press['attempts']>0),
        rating_policy_authorized=False, reference_member=False, ratings=None,
        source_signoff=False, production_certified=False, publication_authorized=False)


def analyze():
    if OUT.exists(): raise ValueError('exclusive analysis output already exists')
    store = EvidenceStore(ROOT/'store', ROOT/'manifest.json', create=False)
    fixtures = {f['match_id']: f for f in bound_document(store.manifest['fixture_documents']['matches-9-27.json']).records()}
    delivered = pq.read_table(EVENTS, filters=FILTER).to_pandas()
    if delivered.id.duplicated().any(): raise ValueError('duplicate delivered UUIDs')
    minute_frame = pq.read_table(MINUTES).to_pandas()
    minutes = minute_frame[minute_frame.competition_name.eq('1. Bundesliga') & minute_frame.season_name.eq('2015/2016')]
    recovery = pq.read_table(RECOVERY, filters=FILTER).to_pandas()
    delivered_keys = {(int(r.player_id),r.team):r for r in minutes.itertuples()}
    OUT.mkdir(parents=True, exist_ok=False)
    artifacts = ['appearances', 'match-measurements', 'match-checks', 'event-reconciliation', 'unresolved', 'club-summaries', 'player-readiness', 'transfers']
    by_club = defaultdict(list); metrics_by_club = defaultdict(list); statuses=Counter(); totals=Counter()
    bad_actors=set(); source_ids=set(); failed_matches=[]; input_bindings={}
    with ExitStack() as stack:
        streams={n: stack.enter_context((OUT/(n+'.jsonl')).open('x', encoding='utf8')) for n in artifacts}
        for mid in sorted(fixtures):
            result=store.verify(mid)
            report=result.get('report',{})
            if report.get('artifact_validation')!='BYTE_BOUND_SOURCE_SCHEMA_REVIEWED':
                failed_matches.append(mid);line(streams['unresolved'],dict(match_id=mid,kind='SOURCE_PAIR_OR_SCHEMA_UNAVAILABLE',detail=report or result));continue
            bindings=report['artifacts']; docs={k:bound_document(v).records() for k,v in bindings.items()}
            for b in [*bindings.values(),report['fixture_document']]:input_bindings[b['path']]=b
            roster=appearance_rows(report,fixtures[mid],docs['lineups']); active=[a for a in roster if a['active_appearance']]
            frame=flatten_events(docs['events'],fixtures[mid],roster)
            if source_ids.intersection(frame.id):raise ValueError('duplicate source UUID across fixtures')
            source_ids.update(frame.id)
            ms,unknown,_=measurements(frame,roster)
            independent=check_match(fixtures[mid],docs['lineups'],docs['events'],active,ms)
            for f in independent['actor_findings']:
                bad_actors.update(p for p in [f.get('player_id'),f.get('source_actor_id')] if p is not None)
                line(streams['unresolved'],dict(match_id=mid,kind='ACTOR_DISAGREEMENT',detail=f))
            for f in unknown:line(streams['unresolved'],dict(match_id=mid,kind='UNRESOLVED_COMPONENT_ACTOR',detail=f))
            fmap={r['id']:r for r in frame.to_dict('records')}; d=delivered[delivered.match_id.eq(mid)]; associations=Counter(); field_differences=Counter()
            compare=['type','under_pressure','duel_type','duel_outcome','interception_outcome',
                'ball_recovery_recovery_failure','pass_outcome','dribble_outcome']
            for dr in d.to_dict('records'):
                sr=fmap.get(dr['id'])
                check=reconcile_event(sr,dr) if sr else dict(status='UUID_MISSING_FROM_ORIGINAL',reasons=['UUID_MISSING_FROM_ORIGINAL'])
                differences=[k for k in compare if sr and not ((pd.isna(dr[k]) and pd.isna(sr[k])) or dr[k]==sr[k])]
                associations[check['status']]+=1;field_differences.update(differences)
                line(streams['event-reconciliation'],dict(event_id=dr['id'],match_id=mid,**check,metric_field_differences=differences))
            for a in roster:
                a['source_documents']=bindings;a['review_reference']=dict(path=result['report_path'],sha256=file_hash(result['report_path']))
                line(streams['appearances'],a)
                if a['active_appearance']:
                    statuses[a['participation_status']]+=1;by_club[a['player_id'],a['team']].append(a)
                    if a['participation_status']!=VALID:line(streams['unresolved'],dict(kind='UNSUPPORTED_INTERVAL',**a))
            for m in ms:
                line(streams['match-measurements'],m);metrics_by_club[m['player_id'],m['team']].append(m)
                for n,c in m['components'].items():
                    if c['unaligned_event_ids']:line(streams['unresolved'],dict(kind='EVENT_OUTSIDE_SUPPORTED_EXPOSURE',match_id=mid,player_id=m['player_id'],component=n,event_ids=c['unaligned_event_ids']))
            line(streams['match-checks'],dict(match_id=mid,source_pair_verified=True,independent_calculation_agrees=True,
                original_events=len(frame),delivered_events=len(d),event_associations=dict(associations),metric_field_differences=dict(field_differences),
                actor_findings=independent['actor_findings'],orphan_components=independent['orphan_component_events'],
                boundaries=report['boundaries'],source_totals=independent['source_totals'],source_documents=bindings,
                report_reference=dict(path=result['report_path'],sha256=file_hash(result['report_path'])),production_certified=False))
            totals.update(associations);totals['original_events']+=len(frame);totals['metric_field_differences']+=sum(field_differences.values())
            print('VERIFIED_BUNDESLIGA',mid,dict(statuses),flush=True)
        clubs=[]
        for k,apps in sorted(by_club.items()):
            delivered_row=delivered_keys.get(k)
            c=aggregate_context(apps,metrics_by_club[k],provider_complete=True,role=delivered_row.position_group if delivered_row else None)
            c.update(team=apps[0]['team'],team_id=apps[0]['team_id'],competition_name='1. Bundesliga',
                scope='OBSERVED_34_MATCH_INVENTORY_ONLY',season_coverage_partial=True,
                delivered_capped_minutes=float(delivered_row.minutes) if delivered_row else None,
                supported_minus_capped_minutes=c['known_supported_minutes']-float(delivered_row.minutes) if delivered_row and not c['withheld_appearance_count'] else None,
                identity_supported=c['player_id'] not in bad_actors)
            c.update(position_summary(c['source_position_minutes']))
            discrepancies=[]
            for n,ev in [('tackles','Tackle'),('interceptions','Interception'),('recoveries','Ball Recovery')]:
                old=recovery[recovery.player_id.eq(k[0])&recovery.team.eq(k[1])&recovery.event_type.eq(ev)]
                if len(old)>1:raise ValueError('duplicate aggregate component')
                if len(old)==1 and int(old.iloc[0]['count'])!=c['components'][n]['raw_source_count']:discrepancies.append(n)
            c['delivered_defensive_count_disagreements']=discrepancies
            line(streams['club-summaries'],c);clubs.append(c)
        by_player=defaultdict(list)
        for c in clubs:by_player[c['player_id']].append(c)
        players=[]
        for pid, cs in sorted(by_player.items()):
            metric_rows=[m for c in cs for m in metrics_by_club[pid,c['team']]]
            p=player_readiness(cs,metric_rows,bad_actors)
            p['delivered_mid_cb_candidate']=bool(minutes[minutes.player_id.eq(pid)].position_group.isin(['CB','DM','CM']).any())
            line(streams['player-readiness'],p);players.append(p)
        transfer_rows=transfer_review(clubs,metrics_by_club,bad_actors)
        for t in transfer_rows:line(streams['transfers'],t)
    midcb=[p for p in players if p['comparison_group'] in ('MID','CB')]
    summary=dict(notice='SAME-PROVIDER ORIGINAL-SOURCE VERIFICATION; NO SOURCE SIGNOFF OR RATINGS',
        exact_match_ids=sorted(fixtures),matches_verified=len(fixtures)-len(failed_matches),failed_match_ids=failed_matches,
        original_event_totals=dict(totals),participation_status_counts=dict(statuses),active_source_players=len(players),
        source_dominant_mid_cb_players=len(midcb),delivered_mid_cb_players=int(minutes[minutes.position_group.isin(['CB','DM','CM'])].player_id.nunique()),
        mid_cb_with_any_supported_minutes=sum(p['known_supported_minutes']>0 for p in midcb),
        mid_cb_all_observed_minutes_supported=sum(p['all_observed_appearance_minutes_supported'] for p in midcb),
        mid_cb_verified_defensive_subsets={n:sum(p['defensive'][n]['status']!='N/A' for p in midcb) for n in DEFENSIVE},
        mid_cb_supported_press=sum(p['press']['status']=='SUPPORTED_ACTION_RATIO' for p in midcb),
        mid_cb_press_at_least_40=sum(p['press']['observed_40_actions'] for p in midcb),
        mid_cb_press_below_40=sum(p['press']['below_40_limited_data'] for p in midcb),
        potential_provisional_mid_cb_players=sum(p['provisional_rating_technically_possible'] for p in midcb),
        bad_actor_player_ids=sorted(bad_actors),transfers_reviewed=len(transfer_rows),
        partial_season_coverage=True,reference_members_added=0,ratings_generated=0,source_signoff=False,
        production_certified=False,publication_authorized=False)
    write_new(OUT/'summary.json',summary)
    receipt_paths=[EVENTS,MINUTES,RECOVERY,ROOT/'manifest.json',ROOT/'scope.json',
        FOUR/'player-club-summaries.jsonl',FOUR/'appearance-ledger.jsonl',FOUR/'match-component-measurements.jsonl',FOUR/'run-manifest.json']
    receipts=[dict(path=str(p.resolve()),sha256=file_hash(p),size_bytes=p.stat().st_size) for p in receipt_paths]
    write_new(OUT/'input-receipts.json',dict(local_files=receipts,original_documents=list(input_bindings.values())))
    write_new(OUT/'run-manifest.json',dict(schema_version='bundesliga-readiness/v1',created_at=now(),
        recipe={str(p):file_hash(p) for p in [Path(__file__),Path('src/source_reconstruction.py'),Path('src/independent_source_checks.py'),Path('src/statsbomb_participation.py'),Path('src/participation_intervals.py')]},
        artifacts=[dict(path=p.name,sha256=file_hash(p),size_bytes=p.stat().st_size) for p in sorted(OUT.iterdir()) if p.is_file()],
        production_certified=False,publication_authorized=False))
    print(json.dumps(summary,indent=2),flush=True)


def transfer_review(clubs, metrics_by_club, bad_actors):
    """Reuse only nine existing source ledgers; never reconstruct four leagues."""
    seal=load_json(FOUR/'run-manifest.json')
    for name in ['player-club-summaries.jsonl','appearance-ledger.jsonl','match-component-measurements.jsonl']:
        expected=next(a['sha256'] for a in seal['artifacts'] if a['path']==name)
        if file_hash(FOUR/name)!=expected:raise ValueError('existing sealed transfer input changed: '+name)
    existing=[c for c in records(FOUR/'player-club-summaries.jsonl') if c['player_id'] in TRANSFERS]
    apps=defaultdict(list);ms=defaultdict(list)
    for a in records(FOUR/'appearance-ledger.jsonl'):
        if a['player_id'] in TRANSFERS and a['active_appearance']:apps[a['player_id'],a['team']].append(a)
    for m in records(FOUR/'match-component-measurements.jsonl'):
        if m['player_id'] in TRANSFERS:ms[m['player_id'],m['team']].append(m)
    result=[]
    for pid in sorted(TRANSFERS):
        bs=[c for c in clubs if c['player_id']==pid];fs=[c for c in existing if c['player_id']==pid]
        # Original source reconstruction uses the same aggregate shape; all
        # combined outputs remain explicitly subset measurements.
        ids=[mid for c in bs+fs for mid in c['match_ids']]
        disjoint=len(ids)==len(set(ids))
        if not disjoint:raise ValueError('cross-league actor-match duplication')
        metric_rows=[m for c in bs for m in metrics_by_club[pid,c['team']]]+[m for c in fs for m in ms[pid,c['team']]]
        p=player_readiness(bs+fs,metric_rows,bad_actors)
        original_roles=sorted({position for c in bs+fs for position in c['source_position_minutes']})
        reasons=[]
        if not bs or not fs:reasons.append('MISSING_CONTRIBUTION')
        if pid in bad_actors or any(c.get('identity_reasons') for c in fs):reasons.append('IDENTITY_REVIEW_REQUIRED')
        p.update(original_contexts=[dict(player_id=pid,team=c['team'],competition_name=c['competition_name'],
            match_ids=c['match_ids'],known_supported_minutes=c['known_supported_minutes'],
            unresolved_match_ids=c['unresolved_match_ids']) for c in bs+fs],
            canonical_player_season_id=f'{pid}:2015/2016',nonoverlapping_fixture_scopes=disjoint,
            matching_metric_definitions=True,all_observed_positions=original_roles,
            technical_combination='SUPPORTED_SUBSETS_ONLY' if not reasons else 'WITHHELD',combination_reasons=reasons,
            policy_admission=False,unobserved_bundesliga_exposure='UNKNOWN_NOT_ZERO')
        result.append(p)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['prepare','acquire','analyze'])
    parser.add_argument('--match-ids',type=int,nargs='+')
    args=parser.parse_args()
    if args.mode=='prepare':prepare()
    elif args.mode=='acquire':acquire(args.match_ids)
    else:analyze()


if __name__=='__main__':main()
