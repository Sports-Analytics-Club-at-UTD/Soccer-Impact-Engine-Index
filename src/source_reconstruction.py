"""Source-backed candidate facts and reconciliation; no scoring or certification.

Participation comes from byte-bound existing source reviews. Action definitions
are the existing recovery, press and Level A progressive-pass implementations.
Known subset measurements never become complete-season denominators implicitly.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from functools import lru_cache
import json

import pandas as pd

from src.identity import normalize_player_names, normalize_team_names
from src.statsbomb_participation import _id, _timestamp, _team_name_agrees
from src.participation_intervals import VALID, CONFLICT, INCOMPLETE
from src.dri_scoring import MIN_MINUTES, ROLE_GROUPS
from src.recovery import _extract
from src.metrics.press_actions import classify_actions, COUNT_COLS, add_completion_rates
from src.passing import _prepare
from src.metrics.progressive_passes import flag_progressive
from src.transfer_aggregation import COUNTS as TRANSFER_COUNTS

NOTICE = 'SOURCE-SUPPORTED CANDIDATE FACTS / NOT PRODUCTION CERTIFIED'
COUNT_NAMES = (*TRANSFER_COUNTS, 'progressive_attempts', 'progressive_passes',
               'progressive_third_crossings')
RECOVERY_MAP = {'Tackle':'tackles', 'Interception':'interceptions', 'Ball Recovery':'recoveries'}


@lru_cache(maxsize=20000)
def player_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('original player name required')
    return str(normalize_player_names(pd.Series([value])).iloc[0])


@lru_cache(maxsize=1000)
def team_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('original team name required')
    return str(normalize_team_names(pd.Series([value])).iloc[0])


def exact(value):
    if isinstance(value, dict) and set(value)=={'numerator','denominator'}:
        if type(value['numerator']) is not int or type(value['denominator']) is not int or value['denominator']<=0:
            raise ValueError('exact rational required')
        return Fraction(value['numerator'],value['denominator'])
    if isinstance(value, Fraction): return value
    raise ValueError('byte-bound rational duration required')


def rational(value):
    return dict(numerator=value.numerator, denominator=value.denominator)


def key(row):
    return (_id(row['player_id']), row['team'], row['competition_name'], row['season_name'])


def appearance_rows(report, fixture, lineups):
    """One row per supplied roster actor; bench entries are not appearances."""
    mid=_id(report['match_id'])
    if (report.get('artifact_validation')!='BYTE_BOUND_SOURCE_SCHEMA_REVIEWED'
            or mid!=fixture['match_id'] or report['competition_name']!=fixture['competition']['competition_name']
            or report['season_name']!=fixture['season']['season_name']
            or report.get('production_certified') is not False):
        raise ValueError('source review/fixture context disagreement')
    teams={_id(fixture[s][s+'_id']):fixture[s][s+'_name'] for s in ('home_team','away_team')}
    roster={}
    rawteams={}
    for t in lineups:
        tid=_id(t['team_id'])
        if tid in rawteams or not _team_name_agrees(tid,teams.get(tid),t['team_name'],fixture):
            raise ValueError('lineup/fixture identity disagreement')
        rawteams[tid]=t['team_name']
        for p in t['lineup']:
            pid=_id(p['player_id'])
            if (tid,pid) in roster or any(i==pid for _,i in roster):
                raise ValueError('duplicate/cross-team source actor')
            roster[tid,pid]=p['player_name']
    seen=set();rows=[]
    for item in report['players']:
        p,v=item['player'],item['validation'];c=p['context'];tid=_id(p['team_id']);pid=_id(c['player_id'])
        if ((tid,pid) in seen or c!=v['context'] or c['match_id']!=mid
                or roster.get((tid,pid))!=p['player_name'] or c['team_key']!=teams.get(tid)):
            raise ValueError('duplicate or inconsistent source appearance identity')
        seen.add((tid,pid))
        active=bool(p['observations'] or p.get('source_checks'))
        status=v['status'] if active else 'BENCH_NO_ASSERTED_APPEARANCE'
        if active and status not in (VALID,CONFLICT,INCOMPLETE):raise ValueError('unsupported participation status')
        seconds=exact(v['elapsed_seconds']) if active and status==VALID else None
        if seconds is not None and seconds<0:raise ValueError('negative source exposure')
        if seconds is None and (v['elapsed_seconds'] is not None or v['position_allocation'] is not None):
            raise ValueError('unresolved/bench exposure must remain withheld')
        rows.append(dict(match_id=mid,competition_id=_id(fixture['competition']['competition_id']),
            competition_name=report['competition_name'],season_id=_id(fixture['season']['season_id']),season_name=report['season_name'],
            team_id=tid,team=team_name(teams[tid]),fixture_team_name_raw=teams[tid],lineup_team_name_raw=rawteams[tid],
            player_id=pid,player_name_raw=p['player_name'],player_name_normalized=player_name(p['player_name']),
            active_appearance=active,participation_status=status,
            validated_elapsed_seconds=rational(seconds) if seconds is not None else None,
            validated_elapsed_minutes=rational(seconds/60) if seconds is not None else None,
            supported_minutes=float(seconds/60) if seconds is not None else None,
            position_allocation=v['position_allocation'],original_positions=[json.loads(s) for s in p['raw_positions']],
            playing_intervals=[dict(observation_id=o['observation_id'],position=o['position'],start=o['start'],end=o['end'],
                entry_kind=o['entry_kind'],exit_kind=o['exit_kind'],evidence_refs=o['evidence_refs'],
                status='SOURCE_SUPPORTED' if status==VALID else 'UNRESOLVED_CANDIDATE') for o in p['observations']],
            period_boundaries=report['boundaries'],failure_reasons=sorted({i['code'] for i in v['issues']}),
            source_checks=p.get('source_checks',[]),source_verification_key=report['verification_key'],
            scope_policy='PENDING_TEAM_APPROVAL_MISSING_DELIVERED_FIXTURE' if mid==3879594 else 'NO_PRODUCTION_SCOPE_AUTHORIZED',
            source_independently_verified=False,production_certified=False))
    if seen!=set(roster):raise ValueError('report omitted source roster actors')
    return sorted(rows,key=lambda r:(r['team_id'],r['player_id']))


def flatten_events(events, fixture, roster_rows):
    """Project original fields for existing metric helpers; never name-match IDs."""
    roster={(r['team_id'],r['player_id']):r for r in roster_rows}
    teams={fixture[s][s+'_id']:fixture[s][s+'_name'] for s in ('home_team','away_team')}
    records=[];seen=set()
    for e in events:
        uid=e['id'];tid=_id(e['team']['id']);actor=e.get('player');pid=_id(actor['id']) if actor else None
        if not isinstance(uid,str) or not uid or uid in seen:raise ValueError('duplicate/invalid original event ID')
        seen.add(uid)
        if 'match_id' in e and _id(e['match_id'])!=fixture['match_id']:raise ValueError('event match conflict')
        if not _team_name_agrees(tid,teams.get(tid),e['team']['name'],fixture):raise ValueError('event team conflict')
        if actor and (roster.get((tid,pid),{}).get('player_name_raw')!=actor['name']):raise ValueError('event actor conflict')
        p=e.get('pass',{});d=e.get('duel',{});i=e.get('interception',{});dr=e.get('dribble',{})
        records.append(dict(id=uid,match_id=fixture['match_id'],type=e['type']['name'],team_id=tid,
            team=team_name(teams[tid]),team_raw=e['team']['name'],player_id=pid,player=actor['name'] if actor else None,
            competition_name=fixture['competition']['competition_name'],season_name=fixture['season']['season_name'],
            timestamp=e['timestamp'],period=e['period'],minute=e['minute'],second=e['second'],location=e.get('location'),
            position=e.get('position',{}).get('name'),under_pressure=e.get('under_pressure'),
            duel_type=d.get('type',{}).get('name'),duel_outcome=d.get('outcome',{}).get('name'),
            interception_outcome=i.get('outcome',{}).get('name'),ball_recovery_recovery_failure=e.get('ball_recovery',{}).get('recovery_failure'),
            pass_end_location=p.get('end_location'),pass_length=p.get('length'),pass_outcome=p.get('outcome',{}).get('name'),
            pass_type=p.get('type',{}).get('name'),dribble_outcome=dr.get('outcome',{}).get('name')))
    frame=pd.DataFrame(records)
    if not len(frame):raise ValueError('original event array cannot be empty')
    frame['player_id']=pd.array([r['player_id'] for r in records],dtype='Int64')
    return frame


def measure_events(frame):
    """Return source UUIDs for unchanged existing candidate count definitions."""
    selected={name:[] for name in COUNT_NAMES}
    rec=_extract(frame)
    for r in rec[['id','event_type']].to_dict('records'):selected[RECOVERY_MAP[r['event_type']]].append(r['id'])
    actions=classify_actions(frame)
    for name in COUNT_COLS:selected[name]=actions.loc[actions[name].eq(1),'id'].tolist()
    passes,pass_ledger,preparation=_prepare(frame)
    # Difficulty is deliberately unknown. Only geometry/count outputs are used;
    # no fabricated calibration or pass-value score is exported.
    passes['difficulty']=float('nan')
    progressive=flag_progressive(passes)
    for name,col in [('progressive_attempts','prog_attempt'),('progressive_passes','progressive'),('progressive_third_crossings','third_cross')]:
        selected[name]=progressive.loc[progressive[col],'id'].tolist()
    missing=pass_ledger.loc[pass_ledger.category.eq('missing_geometry'),'id'].tolist()
    return selected,missing,preparation


def event_within_exposure(event, appearance):
    if appearance['participation_status']!=VALID:return False
    t=(event['period'],_timestamp(event['timestamp']))
    bounds={b['period']:b for b in appearance['period_boundaries']}
    b=bounds.get(t[0])
    if b is None or b['start_seconds'] is None or b['end_seconds'] is None:return False
    if not Fraction(str(b['start_seconds']))<=Fraction(t[1])<=Fraction(str(b['end_seconds'])):return False
    for o in appearance['playing_intervals']:
        if o['start'] and o['end']:
            start=(o['start']['period'],Fraction(str(o['start']['seconds'])))
            end=(o['end']['period'],Fraction(str(o['end']['seconds'])))
            if start<=t<=end:return True
    return False


def measurements(frame, appearances):
    """Retain all counts; per90 uses only exactly aligned supported appearance scope."""
    selected,missing,preparation=measure_events(frame)
    events={r['id']:r for r in frame.to_dict('records')}
    actors={(r['team_id'],r['player_id']):r for r in appearances if r['active_appearance']}
    by_actor=defaultdict(lambda:{name:[] for name in COUNT_NAMES});unknown=[]
    for name,ids in selected.items():
        for uid in ids:
            e=events[uid];pid=e['player_id']
            k=(e['team_id'],int(pid)) if not pd.isna(pid) else None
            if k not in actors:
                unknown.append(dict(event_id=uid,component=name,reason='NO_ACTIVE_SOURCE_APPEARANCE',player_id=None if k is None else k[1]))
            else:by_actor[k][name].append(uid)
    missing_by_actor=Counter()
    for uid in missing:
        e=events[uid]
        if not pd.isna(e['player_id']):missing_by_actor[e['team_id'],int(e['player_id'])]+=1
    rows=[]
    for k,a in sorted(actors.items()):
        components={}
        for name in COUNT_NAMES:
            ids=sorted(by_actor[k][name]);bad=[uid for uid in ids if not event_within_exposure(events[uid],a)] if a['participation_status']==VALID else []
            reasons=[]
            if a['participation_status']!=VALID:reasons.append('UNRESOLVED_PARTICIPATION')
            if bad:reasons.append('NUMERATOR_DENOMINATOR_MISMATCH')
            if name.startswith('progressive') and missing_by_actor[k]:reasons.append('MISSING_SOURCE_GEOMETRY')
            if any(u['component']==name for u in unknown):reasons.append('UNRESOLVED_COMPONENT_ACTOR_IN_MATCH')
            minutes=exact(a['validated_elapsed_minutes']) if a['validated_elapsed_minutes'] is not None else None
            if minutes==0:reasons.append('ZERO_SUPPORTED_MINUTES')
            components[name]=dict(count=len(ids),event_ids=ids,unaligned_event_ids=bad,
                status='SOURCE_VERIFIED_CANDIDATE_MEASUREMENT' if not reasons else 'WITHHELD_RATE',reasons=reasons,
                aligned_count=len(ids) if not reasons else None,
                per90=float(Fraction(len(ids)*90,1)/minutes) if not reasons and minutes else None,
                publication_authorized=False)
        rows.append(dict(match_id=a['match_id'],player_id=a['player_id'],team_id=a['team_id'],team=a['team'],
            competition_name=a['competition_name'],season_name=a['season_name'],components=components,
            progressive_missing_geometry=missing_by_actor[k],line_breaking_count=None,
            line_breaking_status='UNRESOLVED_DEFINITION_AND_TARGET_360_EVIDENCE',scoring_policy_status='PENDING_TEAM_APPROVAL'))
    return rows,unknown,preparation


def reconcile_event(source, delivered):
    """A UUID plus exact source context supplies IDs absent from delivered data."""
    reasons=[]
    if source['id']!=delivered['id']:reasons.append('EVENT_UUID_MISMATCH')
    if _id(source['match_id'])!=_id(delivered['match_id']):reasons.append('MATCH_ID_MISMATCH')
    for c in ('competition_name','season_name','type'):
        if source[c]!=delivered[c]:reasons.append(c.upper()+'_MISMATCH')
    if team_name(source['team'])!=team_name(delivered['team']):reasons.append('TEAM_ASSOCIATION_MISMATCH')
    if source['player'] is None or not isinstance(delivered['player'],str) or player_name(source['player'])!=player_name(delivered['player']):
        reasons.append('PLAYER_NAME_MISMATCH_OR_MISSING')
    if 'player_id' in delivered and delivered['player_id'] is not None:
        if pd.isna(source['player_id']) or _id(delivered['player_id'])!=_id(int(source['player_id'])):reasons.append('PLAYER_ID_MISMATCH')
    if 'team_id' in delivered and delivered['team_id'] is not None and _id(delivered['team_id'])!=_id(source['team_id']):
        reasons.append('TEAM_ID_MISMATCH')
    return dict(status='SOURCE_UUID_AND_CONTEXT_EXACT' if not reasons else 'UNRESOLVED_DELIVERED_ASSOCIATION',
                reasons=reasons,source_player_id=None if pd.isna(source['player_id']) else int(source['player_id']),
                reconciled_player_id=None if reasons or pd.isna(source['player_id']) else int(source['player_id']))


def aggregate_context(rows, metric_rows, *, provider_complete, identity_reasons=(), role=None):
    """One club context or explicit source-facts season comparison; never a pool."""
    rows=sorted(rows,key=lambda r:r['match_id'])
    if len({r['match_id'] for r in rows})!=len(rows):raise ValueError('duplicate actor match contribution')
    if not rows:raise ValueError('nonempty appearance ledger required')
    if len({r['player_id'] for r in rows})!=1 or len({r['season_name'] for r in rows})!=1:raise ValueError('incompatible player/season')
    metrics={r['match_id']:r for r in metric_rows}
    if len(metrics)!=len(metric_rows) or set(metrics)!={r['match_id'] for r in rows}:raise ValueError('numerator/appearance scope mismatch')
    valid=[r for r in rows if r['participation_status']==VALID]
    unresolved=[r for r in rows if r['participation_status']!=VALID]
    seconds=sum((exact(r['validated_elapsed_seconds']) for r in valid),Fraction(0))
    complete=bool(provider_complete and not unresolved and not identity_reasons)
    counts={name:sum(metrics[r['match_id']]['components'][name]['count'] for r in rows) for name in COUNT_NAMES}
    components={}
    for name in COUNT_NAMES:
        aligned=[r for r in rows if metrics[r['match_id']]['components'][name]['aligned_count'] is not None]
        matched_seconds=sum((exact(r['validated_elapsed_seconds']) for r in aligned),Fraction(0))
        matched_count=sum(metrics[r['match_id']]['components'][name]['count'] for r in aligned)
        all_aligned=complete and len(aligned)==len(rows)
        components[name]=dict(raw_source_count=counts[name],aligned_appearance_count=len(aligned),aligned_match_ids=[r['match_id'] for r in aligned],
            aligned_subset_count=matched_count,aligned_subset_minutes=rational(matched_seconds/60),
            aligned_subset_per90=float(Fraction(matched_count*5400,1)/matched_seconds) if matched_seconds else None,
            provider_scope_per90=float(Fraction(counts[name]*5400,1)/seconds) if all_aligned and seconds else None,
            provider_scope_status='SOURCE_VERIFIED_CANDIDATE_MEASUREMENT' if all_aligned and seconds else 'NUMERATOR_DENOMINATOR_SCOPE_UNRESOLVED',
            reasons=sorted({reason for r in rows for reason in metrics[r['match_id']]['components'][name]['reasons']}),
            scoring_policy_status='PENDING_TEAM_APPROVAL')
    positions=defaultdict(Fraction)
    for r in valid:
        for p in r['position_allocation']:positions[p['position']]+=exact(p['elapsed_seconds'])
    pressure=add_completion_rates(pd.DataFrame([{n:counts[n] for n in COUNT_COLS}])).iloc[0]
    return dict(player_id=rows[0]['player_id'],season_name=rows[0]['season_name'],match_ids=[r['match_id'] for r in rows],
        supported_match_ids=[r['match_id'] for r in valid],unresolved_match_ids=[r['match_id'] for r in unresolved],
        raw_player_names=sorted({r['player_name_raw'] for r in rows}),normalized_player_names=sorted({r['player_name_normalized'] for r in rows}),
        supported_seconds=rational(seconds),supported_minutes=rational(seconds/60),known_supported_minutes=float(seconds/60),
        withheld_appearance_count=len(unresolved),withheld_minutes=None if unresolved else 0,
        provider_observed_exposure_complete=complete,provider_scope_complete_minutes=float(seconds/60) if complete else None,
        source_position_minutes={p:rational(v/60) for p,v in sorted(positions.items())},
        supported_subset_at_least_900=seconds>=MIN_MINUTES*60,
        complete_provider_scope_at_least_900=bool(complete and seconds>=MIN_MINUTES*60),
        delivered_role=role,role_group=ROLE_GROUPS.get(role),identity_reasons=sorted(set(identity_reasons)),
        candidate_900_minutes_evidence_met=bool(complete and seconds>=MIN_MINUTES*60 and role in ROLE_GROUPS),
        components=components,provider_historical_season_completeness='NOT_CERTIFIED_BY_PROVIDER_LIST',
        raw_source_press_attempts=int(pressure.pressured_actions),raw_source_press_successes=int(pressure.successful_pressured_actions),
        raw_source_press_completion_rate=None if pd.isna(pressure.press_resistance_rate) else float(pressure.press_resistance_rate),
        line_breaking_status='UNRESOLVED_DEFINITION_AND_TARGET_360_EVIDENCE',reference_member=False,
        independent_identity_attested=False,exposure_policy_approved=False,production_certified=False,publication_authorized=False)


def transfer_comparison(clubs, season):
    """Explicit alternative admission comparisons, with no chosen reference key."""
    leagues={c['competition_name'] for c in clubs}
    separate=any(c['complete_provider_scope_at_least_900'] for c in clubs)
    combined=season['complete_provider_scope_at_least_900']
    return dict(player_id=season['player_id'],season_name=season['season_name'],
        original_contexts=[dict(team=c['team'],team_id=c['team_id'],competition_name=c['competition_name'],
            match_ids=c['match_ids'],raw_counts={n:c['components'][n]['raw_source_count'] for n in COUNT_NAMES},
            supported_minutes=c['supported_minutes'],complete_provider_scope_minutes=c['provider_scope_complete_minutes'],
            separate_club_threshold_met=c['complete_provider_scope_at_least_900']) for c in clubs],
        scenarios=[dict(policy='CLUB_CONTEXTS_SEPARATE',evidence_threshold_met=separate,applicable=True,approved=False),
            dict(policy='COMBINE_WITHIN_LEAGUE',evidence_threshold_met=combined if len(leagues)==1 else None,applicable=len(leagues)==1,approved=False),
            dict(policy='COMBINE_ACROSS_TARGET_LEAGUES',evidence_threshold_met=combined,applicable=True,approved=False)],
        combined_raw_counts={n:season['components'][n]['raw_source_count'] for n in COUNT_NAMES},
        combined_supported_minutes=season['supported_minutes'],combined_complete_minutes=season['provider_scope_complete_minutes'],
        threshold_changes_if_combination_authorized=bool(combined and not separate),
        role_membership_policy='PENDING_TEAM_APPROVAL',nominated_reference_context=None,reference_member=False,
        production_certified=False,publication_authorized=False)
