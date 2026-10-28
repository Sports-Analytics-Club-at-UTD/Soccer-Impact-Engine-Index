"""Read-only real measurements projected into existing gates; no new scorer."""
from collections import Counter
import math

import pandas as pd

from src.dri_scoring import (Evidence, SeasonScope, ComparisonPool, score_dri,
    POPULATION_COLUMNS, MEASUREMENT_COLUMNS, ROLE_GROUPS, MIN_MINUTES, LEAGUES, SEASON)
from src.identity import PLAYER_KEYS
from src.identity_evidence import VERIFIED
from src.metrics.press_actions import COUNT_COLS, add_completion_rates
from src.source_reconstruction import COUNT_NAMES, exact, key
from src.statsbomb_participation import _id

NOTICE = 'PROVISIONAL REAL-DATA ANALYSIS / NOT PRODUCTION-CERTIFIED / NOT PUBLICATION-AUTHORIZED'
COHORT = 'phase3-real-source-readiness-2015-16/v1'
EVENTS = {'tackles':'Tackle','interceptions':'Interception','recoveries':'Ball Recovery'}


def _count(value):
    if type(value) is not int or not 0 <= value <= 2**63-1:
        raise ValueError('exact nonnegative source count required')
    return value


def analyze(clubs, *, source, excluded_match_ids=(3879594,)):
    """Observe existing real DRI gates with truthful unverified attestations.

    Complete observed exposure is not an independently attested full season.
    No reference membership or synthetic privilege is manufactured. Missing
    scope and rates remain null; original raw facts stay separately visible.
    """
    if not isinstance(source,str) or not source.strip():raise ValueError('bound source reference required')
    excluded=set(excluded_match_ids)
    if any(type(m) is not int or m<=0 for m in excluded):raise ValueError('exact excluded match IDs required')
    evidence=Evidence('UNVERIFIED',source,False)
    population=[];measurements=[];facts=[];seen=set();team_ids={}
    for c in sorted(clubs,key=key):
        k=key(c)
        if k in seen:raise ValueError('duplicate source player-club context')
        seen.add(k);_id(c['team_id'])
        tk=(c['team'],c['competition_name'],c['season_name'])
        if tk in team_ids and team_ids[tk]!=c['team_id']:raise ValueError('club ID/context disagreement')
        team_ids[tk]=c['team_id']
        if c['competition_name'] not in LEAGUES or c['season_name']!=SEASON:raise ValueError('outside approved source scope')
        if c['production_certified'] is not False or c['reference_member'] is not False:raise ValueError('unexpected source trust promotion')
        mids=c['match_ids']
        if not mids or mids!=sorted(set(mids)) or any(type(m) is not int or m<=0 for m in mids):raise ValueError('canonical source match IDs required')
        scope_ids=tuple(m for m in mids if m not in excluded)
        ds=c['delivered_scope_comparison']
        if bool(scope_ids)!=(ds is not None):raise ValueError('delivered scope/fixture exclusion disagreement')
        complete=ds is not None and ds['provider_scope_complete_minutes'] is not None
        exact_minutes=exact(ds['supported_minutes']) if complete else None
        minutes=float(exact_minutes) if complete else None
        if complete and (minutes<0 or not math.isfinite(minutes) or minutes!=ds['provider_scope_complete_minutes']):raise ValueError('complete source denominator disagreement')
        role=c['delivered_role'];group=ROLE_GROUPS.get(role)
        candidate=bool(complete and exact_minutes>=MIN_MINUTES and group and not c['identity_reasons'])
        if ds is not None and candidate!=ds['candidate_900_minutes_evidence_met']:raise ValueError('candidate exposure/role declaration disagreement')
        scope=SeasonScope(c['competition_name'],c['season_name'],scope_ids,False) if scope_ids else None
        identity=dict(zip(PLAYER_KEYS,k))
        population.append(dict(**identity,position_group=role,reference_member=False,minutes=minutes,
            exposure_scope=scope,identity_evidence=evidence,context_evidence=evidence,exposure_evidence=evidence))
        components={}
        for name in COUNT_NAMES:
            original=c['components'][name];_count(original['raw_source_count'])
            v=None if ds is None else ds['components'][name]
            count=None if v is None else _count(v['raw_source_count'])
            rate=None if v is None else v['provider_scope_per90']
            aligned=bool(complete and v is not None and v['aligned_match_ids']==list(scope_ids)
                         and v['provider_scope_status']=='SOURCE_VERIFIED_CANDIDATE_MEASUREMENT')
            if v is not None and (v['aligned_match_ids']!=sorted(set(v['aligned_match_ids'])) or not set(v['aligned_match_ids'])<=set(scope_ids)):
                raise ValueError('component match scope outside exposure')
            if rate is not None:
                if not aligned or minutes<=0 or v['reasons'] or not math.isclose(rate,count/minutes*90,rel_tol=1e-9,abs_tol=1e-9):
                    raise ValueError('source numerator/denominator mismatch')
            elif aligned and minutes>0:raise ValueError('aligned positive source scope missing rate')
            usable=bool(candidate and aligned and rate is not None)
            components[name]=dict(original_provider_count=original['raw_source_count'],delivered_scope_count=count,
                denominator_minutes=ds['supported_minutes'] if complete else None,
                aligned_subset_count=None if v is None else v['aligned_subset_count'],
                aligned_subset_minutes=None if v is None else v['aligned_subset_minutes'],
                aligned_match_ids=[] if v is None else v['aligned_match_ids'],
                candidate_per90=rate,measurement_status='SOURCE_SUPPORTED_CANDIDATE' if rate is not None else 'WITHHELD_SCOPE',
                candidate_900_measurement_ready=usable,formula='count / validated elapsed minutes * 90',
                formula_approval='EXISTING_MEASUREMENT_ONLY_SCORING_APPROVAL_NOT_INFERRED',
                reasons=['MISSING_DELIVERED_SOURCE_SCOPE'] if v is None else v['reasons'],
                rating=None,percentile=None,production_certified=False,publication_authorized=False)
            if name in EVENTS:
                measurements.append(dict(**identity,event_type=EVENTS[name],count=count,minutes=minutes,per90=rate,
                    rate_status='missing_minutes' if minutes is None else 'zero_minutes' if minutes==0 else 'ok' if rate is not None else 'unsupported',
                    numerator_scope=scope if aligned else None,reportable=False,reportability_source=None,coverage_evidence=evidence))
        press_counts={n:components[n]['delivered_scope_count'] for n in COUNT_COLS}
        press_rate=None;attempts=None;successes=None
        if all(v is not None for v in press_counts.values()):
            for typ in ('pass','dribble'):
                if press_counts[f'pressured_{typ}_completed']>press_counts[f'pressured_{typ}_attempts']:raise ValueError('press completions exceed attempts')
            attempts=sum(press_counts[n] for n in ('pressured_pass_attempts','pressured_dribble_attempts'))
            successes=sum(press_counts[n] for n in ('pressured_pass_completed','pressured_dribble_completed'))
            if all(components[n]['candidate_per90'] is not None for n in COUNT_COLS):
                value=add_completion_rates(pd.DataFrame([press_counts])).iloc[0].press_resistance_rate
                press_rate=None if pd.isna(value) else float(value)
        facts.append(dict(**identity,team_id=c['team_id'],raw_player_names=c['raw_player_names'],
            notice=NOTICE,source=source,role_label=role,comparison_group=group,role_policy_approved=False,
            original_match_ids=mids,analysis_match_ids=list(scope_ids),excluded_match_ids=sorted(set(mids)&excluded),
            known_supported_provider_minutes=c['supported_minutes'],complete_delivered_scope_minutes=minutes,
            unresolved_appearance_count=c['withheld_appearance_count'],identity_reasons=c['identity_reasons'],
            candidate_900_evidence_met=candidate,reference_member=False,components=components,
            press_measurement=dict(attempts=attempts,successes=successes,completion_percentage=press_rate,
                formula='100 * successful pressured actions / pressured attempts',rating=None,percentile=None,
                action_threshold_comparisons=[dict(min_actions=n,measurement_and_900_gate_met=bool(candidate and press_rate is not None and attempts>=n),approved=False) for n in (30,50)]),
            line_breaking_rating=None,line_breaking_reason='UNRESOLVED_DEFINITION_AND_NO_TARGET_360',
            overall_rating=None,overall_reason='POLICY_NOT_FINALIZED',archetype=None,
            scoring_approved=False,production_certified=False,publication_authorized=False))
    pop=pd.DataFrame(population,columns=POPULATION_COLUMNS)
    metrics=pd.DataFrame(measurements,columns=MEASUREMENT_COLUMNS)
    expected_pool=ComparisonPool(COHORT,VERIFIED,evidence)
    result=score_dri(pop,metrics,pool=expected_pool)
    if result.players.eligible.any() or result.players.status.ne('N/A').any():raise ValueError('unexpected real scoring admission')
    return facts,result,pop,metrics,expected_pool


def summarize(facts,result):
    groups=[]
    for group in ('MID','CB',None):
        rows=[r for r in facts if r['comparison_group']==group]
        groups.append(dict(comparison_group=group,contexts=len(rows),candidate_900_contexts=sum(r['candidate_900_evidence_met'] for r in rows),
            core_aligned_candidates=sum(r['candidate_900_evidence_met'] and all(r['components'][n]['candidate_900_measurement_ready'] for n in (*EVENTS,*COUNT_COLS)) for r in rows),
            components={n:dict(candidate_900_measurement_ready=sum(r['components'][n]['candidate_900_measurement_ready'] for r in rows),
                measured_scope_rates=sum(r['components'][n]['candidate_per90'] is not None for r in rows),numeric_ratings=0,
                withheld_ratings=len(rows)) for n in COUNT_NAMES},
            press_action_sensitivity={str(n):sum(r['press_measurement']['action_threshold_comparisons'][i]['measurement_and_900_gate_met'] for r in rows) for i,n in enumerate((30,50))},
            actual_reference_members=0,numeric_ratings=0))
    return dict(schema_version='provisional-real-candidate-analysis/v1',notice=NOTICE,contexts=len(facts),groups=groups,
        dri_gate_reasons=dict(Counter(reason for reasons in result.players.reasons for reason in reasons)),
        candidate_scores_generated=0,production_certified_contexts=0,production_ratings=0,publication_authorized=False,
        technical_analysis_complete=True,numeric_step3_complete=False,reference_membership_selected=False)
