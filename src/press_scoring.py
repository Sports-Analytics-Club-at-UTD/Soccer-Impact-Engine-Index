"""CANDIDATE SCORING — NOT PRODUCTION APPROVED.

Pure synthetic-only experiments over unchanged M3A counts/rates. No defaults
for candidate policy, no real-data mode, publication, OVR, tiers or I/O.
Contributor reference: Pratyush press V2 at f024cbf6e952c7353bdd8c8be3973112c6f92113.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction
import math
from numbers import Integral, Real

import numpy as np
import pandas as pd

from src.identity import PLAYER_KEYS, validate_population
from src.identity_evidence import SYNTHETIC
from src.metrics.press_actions import COUNT_COLS, DERIVED_COLS, RATE_COLS, add_completion_rates

NOTICE = "CANDIDATE SCORING — NOT PRODUCTION APPROVED"
LEAGUES = ("La Liga", "Premier League", "Serie A", "Ligue 1")
SEASON = "2015/2016"
PERCENTILE = "average_rank_percentile_clipped_1_100"
FIFA = "sample_z_65_10_unrounded_clipped_1_99"
POPULATION_COLUMNS = [*PLAYER_KEYS, "position_group", "minutes", "exposure_scope",
                      "identity_evidence", "context_evidence", "exposure_evidence"]
ACTION_COLUMNS = [*PLAYER_KEYS, *COUNT_COLS, "numerator_scope", "coverage_evidence"]
TOTAL_COLUMNS = ["pressured_actions", "successful_pressured_actions"]
MAX_COUNT = 2**63 - 1


class PressScoringError(ValueError):
    """An unsafe or non-synthetic experiment; no repaired/partial score table."""


@dataclass(frozen=True)
class SyntheticEvidence:
    kind: str
    fixture_id: str
    source: str
    complete: bool


@dataclass(frozen=True)
class PressScope:
    competition_name: str
    season_name: str
    match_ids: tuple
    full_season: bool


@dataclass(frozen=True)
class CandidatePolicy:
    policy_id: str
    source: str
    formula: str
    min_actions: int
    min_minutes: float
    pooling: str
    min_pool_size: int
    reference_unit: str


@dataclass(frozen=True)
class ComparisonPools:
    population_id: str
    season_name: str
    competitions: tuple
    members: pd.DataFrame
    coverage_evidence: SyntheticEvidence | None


@dataclass(frozen=True)
class CandidatePressResult:
    players: pd.DataFrame
    pools: pd.DataFrame
    metadata: dict


def _missing(value):
    return pd.api.types.is_scalar(value) and bool(pd.isna(value))


def _label(value, name):
    if not isinstance(value, str) or not value.strip():
        raise PressScoringError(f"{name}: explicit nonblank text required")


def _numeric(value, name, *, count=False):
    if _missing(value):
        return None
    try:
        valid = (not isinstance(value, (bool, np.bool_)) and isinstance(value, Real)
                 and math.isfinite(value) and value >= 0)
    except OverflowError:
        valid = False
    if not valid:
        raise PressScoringError(f"{name}: finite nonnegative real number required")
    if count and (int(value) != value or value > MAX_COUNT or
                  (not isinstance(value, Integral) and value > 2**53-1)):
        raise PressScoringError(f"{name}: exact nonnegative signed-int64 count required")
    return int(value) if count else float(value)


def _evidence(value, fixture_id, *, optional=True):
    if value is None and optional:
        return False
    if not isinstance(value, SyntheticEvidence) or value.kind != SYNTHETIC:
        raise PressScoringError("synthetic-only gate: delivered, provisional and verified real-data evidence forbidden")
    _label(value.fixture_id, "fixture_id"); _label(value.source, "evidence source")
    if value.fixture_id != fixture_id or type(value.complete) is not bool:
        raise PressScoringError("mixed synthetic fixture provenance or invalid completeness flag")
    return value.complete


def _scope(value, context, associations):
    if value is None:
        return
    if not isinstance(value, PressScope):
        raise PressScoringError("PressScope or explicit None required")
    if (value.competition_name != context[2] or value.season_name != context[3]
            or value.full_season is not True or not isinstance(value.match_ids, tuple)
            or not value.match_ids or any(isinstance(v, (bool,np.bool_)) or not isinstance(v, Integral)
                or not 0 < v <= MAX_COUNT for v in value.match_ids)
            or tuple(sorted(set(value.match_ids))) != value.match_ids):
        raise PressScoringError("inconsistent, partial-season or invalid numerator/exposure scope")
    for mid in value.match_ids:
        association=(value.competition_name,value.season_name)
        if mid in associations and associations[mid]!=association:
            raise PressScoringError("match ID has contradictory competition/season associations")
        associations[mid]=association


def _canonical(table, required, label, optional=()):
    if (not isinstance(table, pd.DataFrame) or not table.columns.is_unique
            or not set(required).issubset(table.columns) or set(table.columns)-set(required)-set(optional)):
        raise PressScoringError(f"{label}: incompatible structured columns")
    try:
        keys = validate_population(table).reset_index(drop=True)
    except ValueError as exc:
        raise PressScoringError(f"{label}: {exc}") from exc
    out = table.copy(deep=True).reset_index(drop=True)
    for key in PLAYER_KEYS:
        out[key] = keys[key]
    if not out.competition_name.isin(LEAGUES).all() or not out.season_name.eq(SEASON).all():
        raise PressScoringError(f"{label}: outside explicit four-league 2015/2016 scope")
    return out


def _policy(policy):
    if policy is None:
        return
    if not isinstance(policy, CandidatePolicy):
        raise PressScoringError("explicit CandidatePolicy or None required")
    _label(policy.policy_id, "policy_id"); _label(policy.source, "policy source")
    if (policy.formula not in (PERCENTILE,FIFA) or policy.pooling not in ("separate_mid_cb","combined_mid_cb")
            or policy.reference_unit not in ("one_context_per_player","canonical_context")):
        raise PressScoringError("unsupported explicit candidate formula/pooling/reference unit")
    if (isinstance(policy.min_actions,(bool,np.bool_)) or not isinstance(policy.min_actions,Integral)
            or not 0 <= policy.min_actions <= MAX_COUNT
            or isinstance(policy.min_pool_size,(bool,np.bool_)) or not isinstance(policy.min_pool_size,Integral)
            or policy.min_pool_size < 2):
        raise PressScoringError("explicit integer action minimum and pool minimum >=2 required")
    if _numeric(policy.min_minutes,"candidate min_minutes") is None:
        raise PressScoringError("explicit candidate minute minimum required")


def _measurements(row):
    values = {c: _numeric(row[c],c,count=True) for c in COUNT_COLS}
    complete = all(v is not None for v in values.values())
    expected = dict.fromkeys(DERIVED_COLS, None)
    for kind in ("pass","dribble"):
        attempted,completed = values[f"pressured_{kind}_attempts"],values[f"pressured_{kind}_completed"]
        if attempted is not None and completed is not None and completed > attempted:
            raise PressScoringError("completed actions exceed attempted actions")
    if complete:
        attempts = values[COUNT_COLS[0]] + values[COUNT_COLS[2]]
        successful = values[COUNT_COLS[1]] + values[COUNT_COLS[3]]
        if max(attempts,successful) > MAX_COUNT:
            raise PressScoringError("combined action count overflows signed int64")
        # M3A accepts floating numeric storage. A float shadow for percentages
        # avoids int64 overflow in its 100*count multiplication. Exact original
        # counts/totals remain Python ints/nullable Int64, never this shadow.
        calculated = add_completion_rates(pd.DataFrame([values],dtype=float)).iloc[0]
        expected.update({"pressured_actions":attempts,"successful_pressured_actions":successful,
                         **{c:None if pd.isna(calculated[c]) else float(calculated[c]) for c in RATE_COLS}})
    for c in DERIVED_COLS:
        if c not in row:
            continue
        supplied = _numeric(row[c],c,count=c in TOTAL_COLUMNS)
        actual = expected[c]
        if ((supplied is None) != (actual is None) or (supplied is not None and
                (supplied != actual if c in TOTAL_COLUMNS else not math.isclose(supplied,actual,rel_tol=1e-12,abs_tol=1e-12)))):
            raise PressScoringError(f"contradictory supplied M3A total/percentage: {c}")
    return values | expected, complete


def _percentiles(ratios):
    """Average ascending ranks on exact successful/attempt fractions."""
    ranks = {}
    ordered = sorted(ratios,key=lambda key:ratios[key])
    start = 0
    while start < len(ordered):
        end = start+1
        while end < len(ordered) and ratios[ordered[start]] == ratios[ordered[end]]:
            end += 1
        for key in ordered[start:end]:
            ranks[key] = 100 * ((start+1+end)/2) / len(ordered)
        start = end
    return ranks


def evaluate_press_candidates(population, actions, *, pools, evidence, policy):
    """Synthetic-only candidate scores, with every explicit population row retained.

    policy=None returns raw measurements and N/A scores, never a default policy.
    Real/verified evidence is rejected even if structurally valid. Selecting an
    experimental policy never approves it or authorizes publication.
    """
    if not isinstance(evidence,SyntheticEvidence):
        raise PressScoringError("explicit synthetic dataset evidence required")
    dataset_complete = _evidence(evidence,evidence.fixture_id,optional=False)
    _policy(policy)
    if not isinstance(pools,ComparisonPools):
        raise PressScoringError("explicit comparison-pool definition required")
    _label(pools.population_id,"population_id")
    if (pools.season_name != SEASON or not isinstance(pools.competitions,tuple)
            or len(pools.competitions) != 4 or not all(isinstance(v,str) for v in pools.competitions)
            or set(pools.competitions) != set(LEAGUES)):
        raise PressScoringError("comparison scope must explicitly declare all four 2015/2016 leagues")
    pool_complete = _evidence(pools.coverage_evidence,evidence.fixture_id)
    pop = _canonical(population,POPULATION_COLUMNS,"population").sort_values(PLAYER_KEYS).reset_index(drop=True)
    counts = _canonical(actions,ACTION_COLUMNS,"actions",DERIVED_COLS)
    members = _canonical(pools.members,[*PLAYER_KEYS,"pool_group"],"pool members").sort_values(PLAYER_KEYS)
    keys = set(pop[PLAYER_KEYS].itertuples(index=False,name=None))
    if (set(counts[PLAYER_KEYS].itertuples(index=False,name=None))-keys
            or set(members[PLAYER_KEYS].itertuples(index=False,name=None))-keys):
        raise PressScoringError("action or pool identity absent from explicit population")
    if not members.pool_group.isin(["MID","CB","COMBINED"]).all():
        raise PressScoringError("invalid comparison pool group")
    groups = set(members.pool_group)
    if "COMBINED" in groups and len(groups)>1:
        raise PressScoringError("combined and separate pools cannot coexist")
    if policy and ((policy.pooling=="separate_mid_cb" and "COMBINED" in groups)
                   or (policy.pooling=="combined_mid_cb" and groups-set(["COMBINED"]))):
        raise PressScoringError("pool membership contradicts selected candidate pooling")
    if policy and policy.reference_unit=="one_context_per_player" and members.duplicated(["player_id","season_name"]).any():
        raise PressScoringError("multiple reference contexts for a player-season; caller must choose explicitly")
    membership = {tuple(r[c] for c in PLAYER_KEYS):r["pool_group"] for r in members.to_dict("records")}
    action_map = {tuple(r[c] for c in PLAYER_KEYS):r for r in counts.to_dict("records")}
    rows = []; ratios = {}; associations = {}
    for source in pop.to_dict("records"):
        key = tuple(source[c] for c in PLAYER_KEYS)
        role = None if _missing(source["position_group"]) else source["position_group"]
        if role is not None and role not in ("DM","CM","MID","CB","AMBIGUOUS"):
            raise PressScoringError("invalid or unsupported role")
        group = membership.get(key)
        expected_group = "MID" if role in ("DM","CM","MID") else "CB" if role=="CB" else None
        if expected_group and group in ("MID","CB") and group!=expected_group:
            raise PressScoringError("cross-position comparison-pool contamination")
        reasons = []
        if role in (None,"AMBIGUOUS"): reasons.append("missing_role" if role is None else "ambiguous_role")
        if group is None: reasons.append("not_pool_member")
        if policy is None: reasons.append("candidate_policy_not_selected")
        if not dataset_complete: reasons.append("incomplete_synthetic_dataset")
        if not pool_complete: reasons.append("incomplete_pool_coverage")
        for name in ("identity_evidence","context_evidence","exposure_evidence"):
            if not _evidence(source[name],evidence.fixture_id): reasons.append("missing_or_incomplete_"+name)
        minutes = _numeric(source["minutes"],"minutes")
        if minutes is None: reasons.append("missing_exposure")
        elif minutes <= 0: reasons.append("nonpositive_exposure")
        elif policy and minutes < policy.min_minutes: reasons.append("below_candidate_min_minutes")
        scope = source["exposure_scope"]; _scope(scope,key,associations)
        if scope is None: reasons.append("missing_exposure_scope")
        action = action_map.get(key)
        measured = dict.fromkeys([*COUNT_COLS,*DERIVED_COLS],None)
        if action is None:
            reasons.append("missing_actions")
        else:
            measured, complete = _measurements(action)
            numerator = action["numerator_scope"]; _scope(numerator,key,associations)
            if numerator is not None and scope is not None and numerator!=scope:
                raise PressScoringError("numerator and exposure match windows disagree")
            if numerator is None: reasons.append("missing_numerator_scope")
            if not _evidence(action["coverage_evidence"],evidence.fixture_id): reasons.append("incomplete_press_coverage")
            if not complete: reasons.append("incomplete_action_counts")
            else:
                attempts=measured["pressured_actions"]
                if attempts==0: reasons.append("zero_attempts")
                else: ratios[key]=Fraction(measured["successful_pressured_actions"],attempts)
                if policy and attempts < policy.min_actions: reasons.append("below_candidate_min_actions")
        rows.append({**{c:source[c] for c in PLAYER_KEYS},"position_group":role,"pool_group":group,
            "pool_id":f"{pools.population_id}:{group}" if group else None,"minutes":minutes,**measured,
            "eligible":not reasons,"status":"N/A","reasons":tuple(sorted(reasons)),
            "candidate_percentile":np.nan,"candidate_zscore":np.nan,"candidate_score":np.nan,
            "policy_id":policy.policy_id if policy else None,"policy_status":"NOT_FINALIZED",
            "candidate_formula":policy.formula if policy else None,"notice":NOTICE,
            "policy_provenance":asdict(policy) if policy else None,
            "exposure_scope":asdict(scope) if scope else None,
            "numerator_scope":asdict(action["numerator_scope"]) if action and action["numerator_scope"] else None,
            "source_provenance":{"dataset":asdict(evidence),"identity":asdict(source["identity_evidence"]) if source["identity_evidence"] else None,
                "context":asdict(source["context_evidence"]) if source["context_evidence"] else None,
                "exposure":asdict(source["exposure_evidence"]) if source["exposure_evidence"] else None,
                "press":asdict(action["coverage_evidence"]) if action and action["coverage_evidence"] else None}})
    count_names=[*COUNT_COLS,*TOTAL_COLUMNS]
    columns=[*PLAYER_KEYS,"position_group","pool_group","pool_id","minutes",*COUNT_COLS,*DERIVED_COLS,
        "eligible","status","reasons","candidate_percentile","candidate_zscore","candidate_score",
        "policy_id","policy_status","candidate_formula","notice","policy_provenance",
        "exposure_scope","numerator_scope","source_provenance"]
    players=pd.DataFrame([{k:v for k,v in row.items() if k not in count_names} for row in rows],columns=[c for c in columns if c not in count_names])
    for c in count_names: players[c]=pd.array([row[c] for row in rows],dtype="Int64")
    players=players[columns]
    summaries=[]
    pool_groups=("COMBINED",) if (policy and policy.pooling=="combined_mid_cb") or "COMBINED" in groups else ("MID","CB")
    for group in pool_groups:
        indexes=[i for i,row in enumerate(rows) if row["eligible"] and row["pool_group"]==group]
        selected={i:ratios[tuple(rows[i][c] for c in PLAYER_KEYS)] for i in indexes}
        reason=None; mean=None; std=None
        if policy is None: reason="candidate_policy_not_selected"
        elif len(indexes)<policy.min_pool_size: reason="insufficient_candidate_pool"
        elif len(set(selected.values()))==1: reason="constant_candidate_pool"
        else:
            percentiles=_percentiles(selected)
            average=sum(selected.values(),Fraction(0))/len(selected)
            deviations={i:float(100*(q-average)) for i,q in selected.items()}
            std=math.sqrt(math.fsum(d*d for d in deviations.values())/(len(indexes)-1))
            mean=float(100*average)
            for i in indexes:
                players.at[i,"candidate_percentile"]=percentiles[i]
                if policy.formula==PERCENTILE:
                    score=max(1.,min(100.,percentiles[i]))
                else:
                    z=deviations[i]/std
                    players.at[i,"candidate_zscore"]=z
                    score=max(1.,min(99.,65+10*z))
                players.at[i,"candidate_score"]=score
                players.at[i,"status"]="candidate_scored"
        if reason:
            for i in indexes: players.at[i,"reasons"]=(reason,)
        declared=members.loc[members.pool_group.eq(group),PLAYER_KEYS]
        summaries.append({"pool_id":f"{pools.population_id}:{group}","pool_group":group,
            "declared_members":tuple(declared.itertuples(index=False,name=None)),
            "eligible_members":tuple(tuple(rows[i][c] for c in PLAYER_KEYS) for i in indexes),
            "eligible_count":len(indexes),"reason":reason,"mean_press_percentage":mean,"sample_std":std,
            "notice":NOTICE,"evidence_kind":SYNTHETIC,"policy_id":policy.policy_id if policy else None,
            "policy_provenance":asdict(policy) if policy else None,"dataset_evidence":asdict(evidence),
            "coverage_evidence":asdict(pools.coverage_evidence) if pools.coverage_evidence else None,
            "season_name":SEASON,"competitions":LEAGUES})
    return CandidatePressResult(players,pd.DataFrame(summaries),{"notice":NOTICE,"synthetic_only":True,
        "production_scoring_supported":False,"publication_authorized":False,"policy_finalized":False,
        "policy":asdict(policy) if policy else None,"dataset_evidence":asdict(evidence),
        "pool_coverage_evidence":asdict(pools.coverage_evidence) if pools.coverage_evidence else None,
        "population_id":pools.population_id,"season_name":SEASON,"competitions":LEAGUES,
        "role_mapping":{"DM":"MID","CM":"MID","MID":"MID","CB":"CB"}})
