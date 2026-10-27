"""Pure DRI mathematics adapted from Pratyush V2, f024cbf6e952c7353bdd8c8be3973112c6f92113.

Caller supplies validated measurements AND explicit provenance/scope attestations.
This module authenticates no source, performs no I/O and authorizes no publication.
See docs/d3a-approved-dri-scoring.md for team policy versus conservative safeguards.
"""
from dataclasses import dataclass
import math
from numbers import Integral, Real

import numpy as np
import pandas as pd

from src.identity import PLAYER_KEYS, _contexts, _ids, validate_population
from src.identity_evidence import VERIFIED, SYNTHETIC, DELIVERED
from src.metrics.recovery_coverage import EVENT_TYPES

LEAGUES = ("La Liga", "Premier League", "Serie A", "Ligue 1")
SEASON = "2015/2016"
MIN_MINUTES = 900
PREFIXES = dict(zip(EVENT_TYPES, ("tackle", "interception", "ball_recovery")))
ROLE_GROUPS = {"DM": "MID", "CM": "MID", "MID": "MID", "CB": "CB"}
SCORE_COLUMNS = [*[f"{p}_percentile" for p in PREFIXES.values()],
                 "dri", "dri_percentile", "dri_zscore", "dri_fifa"]
POPULATION_COLUMNS = [*PLAYER_KEYS, "position_group", "reference_member", "minutes",
                      "exposure_scope", "identity_evidence", "context_evidence", "exposure_evidence"]
MEASUREMENT_COLUMNS = [*PLAYER_KEYS, "event_type", "count", "minutes", "per90", "rate_status",
                       "numerator_scope", "reportable", "reportability_source", "coverage_evidence"]


class DRIError(ValueError):
    """Malformed/contradictory input; no silently repaired or partial scoring table."""


@dataclass(frozen=True)
class Evidence:
    kind: str
    source: str
    complete: bool


@dataclass(frozen=True)
class SeasonScope:
    competition_name: str
    season_name: str
    match_ids: tuple
    full_season: bool


@dataclass(frozen=True)
class ComparisonPool:
    population_id: str
    evidence_kind: str
    coverage_evidence: Evidence
    season_name: str = SEASON
    competitions: tuple = LEAGUES


@dataclass(frozen=True)
class DRIResult:
    players: pd.DataFrame
    pools: pd.DataFrame
    metadata: dict


def _label(value, name):
    if not isinstance(value, str) or not value.strip():
        raise DRIError(f"{name}: explicit nonblank label required")


def _missing(value):
    return pd.api.types.is_scalar(value) and bool(pd.isna(value))


def _number(value, name, *, integer=False):
    if _missing(value):
        return None
    try:
        valid = (not isinstance(value, (bool, np.bool_)) and isinstance(value, Real)
                 and math.isfinite(value) and value >= 0)
    except OverflowError:
        valid = False
    if not valid:
        raise DRIError(f"{name}: finite nonnegative real number required; no coercion")
    if integer and (int(value) != value or value > 2**63 - 1
                    or (not isinstance(value, Integral) and value > 2**53 - 1)):
        raise DRIError(f"{name}: exact nonnegative signed-int64 count required")
    return int(value) if integer else float(value)


def _evidence(value):
    if value is None:
        return
    if not isinstance(value, Evidence) or value.kind not in (VERIFIED, SYNTHETIC, DELIVERED, "UNVERIFIED", "PROVISIONAL"):
        raise DRIError("unsupported evidence declaration")
    _label(value.source, "evidence source")
    if type(value.complete) is not bool:
        raise DRIError("evidence completeness must be a boolean")


def _trusted(value, kind):
    return value is not None and value.kind == kind and value.complete


def _scope(value):
    if value is None:
        return
    if not isinstance(value, SeasonScope):
        raise DRIError("SeasonScope or explicit None required")
    _label(value.competition_name, "scope competition")
    _label(value.season_name, "scope season")
    if (type(value.full_season) is not bool or not isinstance(value.match_ids, tuple)
            or not value.match_ids or any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Integral)
                or not 0 < v <= 2**63 - 1 for v in value.match_ids)
            or len(set(value.match_ids)) != len(value.match_ids)
            or tuple(sorted(value.match_ids)) != value.match_ids):
        raise DRIError("scope needs canonical unique exact match IDs and boolean full_season")


def _table(table, columns, label):
    if (not isinstance(table, pd.DataFrame) or not table.columns.is_unique
            or set(table.columns) != set(columns)):
        raise DRIError(f"{label}: exact structured column contract required: {columns}")
    try:
        out = _contexts(table, label).reset_index(drop=True)
        out["player_id"] = _ids(out.player_id, label)
    except ValueError as exc:
        raise DRIError(f"{label}: {exc}") from exc
    return out


def fifa_from_zscore(value):
    """Approved DRI transform, separately testable; no rounding or OVR meaning."""
    if (isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
            or (not isinstance(value, Integral) and not math.isfinite(value))):
        raise DRIError("z-score must be a finite real number")
    # Compare before multiplication to avoid overflow on finite extreme inputs.
    if value >= 3.4:
        return 99.0
    if value <= -6.4:
        return 1.0
    return 65.0 + 10.0 * value


def classify_tier(score):
    """Approved boundaries only; caller must separately decide which score to tier."""
    if score is None or _missing(score):
        return None
    value = _number(score, "tier score")
    if not 1 <= value <= 100:
        raise DRIError("tier helper requires a 1–100 score")
    return "Gold" if value >= 90 else "Silver" if value >= 75 else None


def score_dri(population, measurements, *, pool):
    """Score explicit unique reference contexts only, retaining every population row.

    Missing evidence/measurements/roles yield N/A with all applicable reasons.
    Invalid numeric values, unknown measurement identities, duplicate keys and
    multiple reference contexts per player/season reject the entire call.
    Synthetic and verified evidence cannot be mixed. Attestations are not proof.
    """
    if not isinstance(pool, ComparisonPool):
        raise DRIError("explicit ComparisonPool required")
    _label(pool.population_id, "population ID")
    if (pool.evidence_kind not in (VERIFIED, SYNTHETIC) or pool.season_name != SEASON
            or not isinstance(pool.competitions, tuple) or len(pool.competitions) != 4
            or not all(isinstance(v, str) for v in pool.competitions)
            or set(pool.competitions) != set(LEAGUES)):
        raise DRIError("only explicit MID/CB four-league 2015/2016 verified or synthetic policy supported")
    _evidence(pool.coverage_evidence)
    pop = _table(population, POPULATION_COLUMNS, "population")
    try:
        validate_population(pop)
    except ValueError as exc:
        raise DRIError(str(exc)) from exc
    metrics = _table(measurements, MEASUREMENT_COLUMNS, "measurements")
    if (not metrics.event_type.isin(EVENT_TYPES).all()
            or metrics.duplicated([*PLAYER_KEYS, "event_type"]).any()):
        raise DRIError("duplicate canonical recovery keys or unsupported event type")
    keys = set(pop[PLAYER_KEYS].itertuples(index=False, name=None))
    ledger = {}
    for row in metrics.to_dict("records"):
        key = tuple(row[k] for k in PLAYER_KEYS)
        if key not in keys:
            raise DRIError("measurement identity absent from explicit scoring population")
        for field in ("count", "minutes", "per90"):
            row[field] = _number(row[field], field, integer=field == "count")
        if row["rate_status"] not in ("ok", "missing_minutes", "zero_minutes", "unsupported"):
            raise DRIError("unsupported rate status")
        if row["reportable"] is not None and type(row["reportable"]) is not bool:
            raise DRIError("reportable must be bool or explicit None")
        if row["reportability_source"] is not None:
            _label(row["reportability_source"], "reportability source")
        _evidence(row["coverage_evidence"])
        _scope(row["numerator_scope"])
        minutes, rate, count = row["minutes"], row["per90"], row["count"]
        if ((row["rate_status"] == "ok" and (minutes is None or minutes <= 0))
                or (row["rate_status"] == "missing_minutes" and minutes is not None)
                or (row["rate_status"] == "zero_minutes" and minutes != 0)
                or (row["rate_status"] != "ok" and rate is not None)):
            raise DRIError("contradictory per90/exposure status")
        if minutes is not None and minutes > 0 and rate is not None and count is not None:
            expected = count / minutes * 90
            if not math.isfinite(expected) or not math.isclose(rate, expected, rel_tol=1e-9, abs_tol=1e-9):
                raise DRIError("per90 disagrees with integrated count/exposure arithmetic")
        ledger[key + (row["event_type"],)] = row
    if not all(type(v) is bool for v in pop.reference_member):
        raise DRIError("explicit boolean reference_member required")
    references = pop.loc[pop.reference_member]
    if references.duplicated(["player_id", "season_name"]).any():
        raise DRIError("transfer/role policy unresolved: multiple reference contexts for one player-season")
    rows = []
    for source in pop.sort_values(PLAYER_KEYS).to_dict("records"):
        key = tuple(source[k] for k in PLAYER_KEYS)
        reasons = []
        minutes = _number(source["minutes"], "population minutes")
        scope = source["exposure_scope"]
        _scope(scope)
        role = None if _missing(source["position_group"]) else source["position_group"]
        if role is not None and not isinstance(role, str):
            raise DRIError("position_group must be an explicit label or None")
        group = ROLE_GROUPS.get(role)
        if role is None or role == "":
            reasons.append("missing_role")
        elif role == "AMBIGUOUS":
            reasons.append("ambiguous_role")
        elif group is None:
            reasons.append("unsupported_role")
        if source["competition_name"] not in LEAGUES or source["season_name"] != SEASON:
            reasons.append("invalid_pool_membership")
        if not source["reference_member"]:
            reasons.append("not_reference_member")
        if minutes is None:
            reasons.append("missing_minutes")
        elif minutes == 0:
            reasons.append("zero_minutes")
        elif minutes < MIN_MINUTES:
            reasons.append("below_900_minutes")
        for name in ("identity_evidence", "context_evidence", "exposure_evidence"):
            _evidence(source[name])
            if not _trusted(source[name], pool.evidence_kind):
                reasons.append(f"unverified_{name}")
        if not _trusted(pool.coverage_evidence, pool.evidence_kind):
            reasons.append("unverified_or_incomplete_pool_coverage")
        if scope is None or not scope.full_season:
            reasons.append("unsupported_full_season_exposure")
        if scope is not None and (scope.competition_name != source["competition_name"] or scope.season_name != source["season_name"]):
            reasons.append("exposure_context_mismatch")
        values = {}
        for event, prefix in PREFIXES.items():
            metric = ledger.get(key + (event,))
            values[f"{prefix}_per90"] = np.nan if metric is None or metric["per90"] is None else metric["per90"]
            if metric is None:
                reasons.append(f"{prefix}:missing_component")
                continue
            if metric["count"] is None or metric["per90"] is None:
                reasons.append(f"{prefix}:missing_measurement")
            if metric["rate_status"] != "ok":
                reasons.append(f"{prefix}:unsupported_per90")
            if metric["minutes"] != minutes:
                raise DRIError("component and population exposure minutes disagree")
            if metric["reportable"] is not True or metric["reportability_source"] is None:
                reasons.append(f"{prefix}:unreportable_or_unverified")
            if not _trusted(metric["coverage_evidence"], pool.evidence_kind):
                reasons.append(f"{prefix}:unverified_or_incomplete_coverage")
            if metric["numerator_scope"] is None or metric["numerator_scope"] != scope:
                reasons.append(f"{prefix}:numerator_exposure_scope_mismatch")
        rows.append({**{k: source[k] for k in PLAYER_KEYS}, "position_group": role,
            "score_group": group, "pool_id": f"{pool.population_id}:{group}" if group else None,
            "reference_member": source["reference_member"], "minutes": minutes,
            **values, "eligible": not reasons, "status": "N/A", "reasons": tuple(sorted(reasons)),
            **dict.fromkeys(SCORE_COLUMNS, np.nan)})
    columns = [*PLAYER_KEYS, "position_group", "score_group", "pool_id", "reference_member", "minutes",
               *[f"{p}_per90" for p in PREFIXES.values()], "eligible", "status", "reasons", *SCORE_COLUMNS]
    players = pd.DataFrame(rows, columns=columns)
    summaries = []
    for group in ("MID", "CB"):
        selected = players.index[players.eligible.eq(True) & players.score_group.eq(group)]
        members = tuple(tuple(players.loc[i, PLAYER_KEYS]) for i in selected)
        n = len(selected)
        reason, mean, std = "insufficient_reference_pool" if n < 2 else None, None, None
        if n >= 2:
            ranks = pd.DataFrame({prefix: players.loc[selected, f"{prefix}_per90"].rank(method="average")
                                 for prefix in PREFIXES.values()})
            percentiles = ranks.div(n).mul(100)
            # Half-integer rank sums avoid false distinctions from adding three
            # rounded percentile fractions in different orders. Same formula.
            dri = ranks.sum(axis=1).div(3 * n).mul(100)
            mean, std = float(dri.mean()), float(dri.std(ddof=1))
            if dri.nunique() == 1:
                std = 0.0
                reason = "constant_dri_reference_pool"
            else:
                for prefix in PREFIXES.values():
                    players.loc[selected, f"{prefix}_percentile"] = percentiles[prefix]
                players.loc[selected, "dri"] = dri
                players.loc[selected, "dri_percentile"] = dri.rank(method="average", pct=True) * 100
                zscore = (dri - mean) / std
                players.loc[selected, "dri_zscore"] = zscore
                players.loc[selected, "dri_fifa"] = zscore.map(fifa_from_zscore)
                players.loc[selected, "status"] = "scored"
        if reason:
            for i in selected:
                players.at[i, "reasons"] = (reason,)
        summaries.append({"pool_id": f"{pool.population_id}:{group}", "score_group": group,
            "season_name": SEASON, "competitions": LEAGUES, "eligible_members": members,
            "eligible_count": n, "status": "N/A" if reason else "scored", "reason": reason,
            "dri_mean": mean, "dri_sample_std": std,
            "league_member_counts": tuple((league, sum(key[2] == league for key in members)) for league in LEAGUES)})
    return DRIResult(players, pd.DataFrame(summaries), {"population_id": pool.population_id,
        "evidence_kind": pool.evidence_kind, "synthetic_only": pool.evidence_kind == SYNTHETIC,
        "publication_authorized": False, "component_weights": (1/3, 1/3, 1/3),
        "minimum_minutes": MIN_MINUTES, "ddof": 1, "transfer_policy": "one explicit reference context per player-season"})
