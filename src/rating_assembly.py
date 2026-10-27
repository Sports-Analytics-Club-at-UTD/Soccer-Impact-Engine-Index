"""D3E pure candidate slots; no attribute transforms or production publication.

Evidence is caller-declared lineage, never source authentication. Numeric inputs
are synthetic ratings only. Existing scoring/identity/export contracts are untouched.
"""
from dataclasses import dataclass
import math
from numbers import Integral, Real

import pandas as pd

from src.identity import PLAYER_KEYS, validate_population
from src.identity_evidence import SYNTHETIC, VERIFIED, DELIVERED

ATTRIBUTES = ("tackles", "interceptions", "recoveries", "press_resistance",
              "line_breaking_passes")
NOTICE = "SYNTHETIC-ONLY CANDIDATE / NOT PRODUCTION APPROVED"
POLICY_NOT_FINALIZED = "N/A — POLICY NOT FINALIZED"


class RatingAssemblyError(ValueError):
    """Contradictory or malformed input; no coercion or silent repair."""


@dataclass(frozen=True, order=True)
class PlayerContext:
    player_id: int
    team: str
    competition_name: str
    season_name: str


@dataclass(frozen=True)
class RatingScope:
    competition_name: str
    season_name: str
    match_ids: tuple
    full_season: bool
    cohort_id: str


@dataclass(frozen=True)
class EvidenceSource:
    kind: str
    source: str


@dataclass(frozen=True)
class RatingEvidence:
    kind: str
    sources: tuple
    fixture_id: str | None
    complete: bool


@dataclass(frozen=True)
class AttributePolicy:
    attribute_id: str
    policy_id: str
    version: str
    unit: str
    synthetic_only: bool


@dataclass(frozen=True)
class AttributeSlot:
    attribute_id: str
    context: PlayerContext
    score: float | None
    status: str
    reasons: tuple
    policy: AttributePolicy | None
    evidence: RatingEvidence | None
    scope: RatingScope | None
    comparison_pool_ref: str | None


@dataclass(frozen=True)
class SyntheticOVRPolicy:
    policy_id: str
    version: str
    component_policies: tuple
    formula: str = "equal_weight_mean_of_five"
    synthetic_only: bool = True


@dataclass(frozen=True)
class OverallCandidate:
    score: float | None
    status: str
    reasons: tuple
    policy: SyntheticOVRPolicy | None
    tier: None = None


@dataclass(frozen=True)
class PlayerAssembly:
    context: PlayerContext
    attributes: tuple
    overall: OverallCandidate
    notice: str = NOTICE
    production_verified: bool = False
    publication_authorized: bool = False


def _label(value, name):
    if not isinstance(value, str) or not value.strip():
        raise RatingAssemblyError(f"{name}: explicit nonblank string required")


def _context(value):
    if not isinstance(value, PlayerContext):
        raise RatingAssemblyError("explicit PlayerContext required")
    if isinstance(value.player_id, bool) or not isinstance(value.player_id, Integral):
        raise RatingAssemblyError("canonical player_id must be an exact integer")
    raw = {k: getattr(value, k) for k in PLAYER_KEYS}
    try:
        canonical = validate_population(pd.DataFrame([raw])).iloc[0].to_dict()
    except ValueError as exc:
        raise RatingAssemblyError(str(exc)) from exc
    if canonical != raw:
        raise RatingAssemblyError("exact canonical context required; normalize upstream")


def _policy(value):
    if not isinstance(value, AttributePolicy) or value.attribute_id not in ATTRIBUTES:
        raise RatingAssemblyError("explicit supported AttributePolicy required")
    _label(value.policy_id, "scoring policy identifier")
    _label(value.version, "scoring policy version")
    if value.unit != "rating_1_100" or value.synthetic_only is not True:
        raise RatingAssemblyError("only synthetic candidate rating_1_100 policies supported")


def _evidence(value):
    if not isinstance(value, RatingEvidence) or value.kind not in (SYNTHETIC, VERIFIED, DELIVERED, "UNVERIFIED", "PROVISIONAL"):
        raise RatingAssemblyError("explicit supported evidence kind required")
    if type(value.complete) is not bool or not isinstance(value.sources, tuple) or not value.sources:
        raise RatingAssemblyError("immutable nonempty source lineage and boolean completeness required")
    for source in value.sources:
        if not isinstance(source, EvidenceSource) or source.kind != value.kind:
            raise RatingAssemblyError("evidence lineage mismatch; no evidence promotion or mixing")
        _label(source.source, "evidence source")
    if value.kind == SYNTHETIC:
        _label(value.fixture_id, "synthetic fixture identifier")
    elif value.fixture_id is not None:
        raise RatingAssemblyError("real evidence cannot claim synthetic fixture provenance")


def _scope(value, context):
    if not isinstance(value, RatingScope):
        raise RatingAssemblyError("explicit RatingScope required")
    _label(value.cohort_id, "cohort identifier")
    if (value.competition_name != context.competition_name or value.season_name != context.season_name):
        raise RatingAssemblyError("source scope competition/season conflicts with canonical context")
    ids = value.match_ids
    if (type(value.full_season) is not bool or not isinstance(ids, tuple) or not ids
            or any(isinstance(v, bool) or not isinstance(v, Integral) or not 0 < v <= 2**63 - 1 for v in ids)
            or tuple(sorted(set(ids))) != ids):
        raise RatingAssemblyError("scope requires sorted unique exact positive match IDs and boolean full_season")


def _slot(value):
    if not isinstance(value, AttributeSlot) or value.attribute_id not in ATTRIBUTES:
        raise RatingAssemblyError("one of the exact five attribute slots required")
    _context(value.context)
    if not isinstance(value.reasons, tuple):
        raise RatingAssemblyError("immutable unique reasons required")
    for reason in value.reasons:
        _label(reason, "missing/withholding reason")
    if len(set(value.reasons)) != len(value.reasons):
        raise RatingAssemblyError("immutable unique reasons required")
    if value.policy is not None:
        _policy(value.policy)
        if value.policy.attribute_id != value.attribute_id:
            raise RatingAssemblyError("scoring policy belongs to a different attribute")
    if value.evidence is not None:
        _evidence(value.evidence)
    if value.scope is not None:
        _scope(value.scope, value.context)
    if value.comparison_pool_ref is not None:
        _label(value.comparison_pool_ref, "comparison pool reference")
    if value.status == "withheld":
        if value.score is not None or not value.reasons:
            raise RatingAssemblyError("withheld slot needs None score and explicit reasons")
    elif value.status == "available":
        score = value.score
        if (isinstance(score, bool) or not isinstance(score, Real)
                or not 1 <= score <= 100 or not math.isfinite(score)):
            raise RatingAssemblyError("available score must be a finite real rating in [1, 100]")
        if value.reasons or any(v is None for v in (value.policy, value.evidence, value.scope, value.comparison_pool_ref)):
            raise RatingAssemblyError("available slot needs complete policy, evidence, scope and pool, without withholding reasons")
        if value.evidence.kind != SYNTHETIC or not value.evidence.complete:
            raise RatingAssemblyError("numeric ratings are synthetic-only; no real-data score assembly")
    else:
        raise RatingAssemblyError("status must be available or withheld")


def _ovr_policy(value):
    if not isinstance(value, SyntheticOVRPolicy):
        raise RatingAssemblyError("explicit SyntheticOVRPolicy required")
    _label(value.policy_id, "candidate OVR policy identifier")
    _label(value.version, "candidate OVR policy version")
    if value.synthetic_only is not True or value.formula != "equal_weight_mean_of_five":
        raise RatingAssemblyError("only synthetic equal-weight five-attribute demonstration supported")
    if not isinstance(value.component_policies, tuple) or len(value.component_policies) != 5:
        raise RatingAssemblyError("candidate OVR policy must pin all five component policies")
    for policy in value.component_policies:
        _policy(policy)
    if set(p.attribute_id for p in value.component_policies) != set(ATTRIBUTES):
        raise RatingAssemblyError("candidate OVR policy needs five distinct component policies")


def assemble_ratings(contexts, slots, *, candidate_policy=None):
    """Return immutable PlayerAssembly tuples in canonical order, without I/O.

    Contexts and slots are explicit finite lists/tuples. Omitted slots become
    withheld with missing_attribute. Incompatible well-formed slots are retained,
    but withhold the optional OVR; contradictory identities/values reject the call.
    No raw count/rate transforms, inferred eligibility, tiers, or production output.
    """
    if not isinstance(contexts, (list, tuple)) or not isinstance(slots, (list, tuple)):
        raise RatingAssemblyError("explicit context and slot lists/tuples required")
    for context in contexts:
        _context(context)
    if len(set(contexts)) != len(contexts):
        raise RatingAssemblyError("duplicate canonical contexts")
    if candidate_policy is not None:
        _ovr_policy(candidate_policy)
    ledger = {}
    known = set(contexts)
    for slot in slots:
        _slot(slot)
        key = (slot.context, slot.attribute_id)
        if slot.context not in known:
            raise RatingAssemblyError("attribute identity absent from canonical population")
        if key in ledger:
            raise RatingAssemblyError("duplicate canonical context/attribute")
        ledger[key] = slot
    players = []
    for context in sorted(contexts):
        attributes = tuple(ledger.get((context, attribute), AttributeSlot(
            attribute, context, None, "withheld", ("missing_attribute",), None, None, None, None))
            for attribute in ATTRIBUTES)
        reasons = []
        if candidate_policy is None:
            reasons.append("policy_not_finalized")
        else:
            expected = {p.attribute_id: p for p in candidate_policy.component_policies}
            for slot in attributes:
                if slot.status != "available":
                    reasons.append(f"{slot.attribute_id}:unavailable")
                if slot.policy != expected[slot.attribute_id]:
                    reasons.append(f"{slot.attribute_id}:policy_version_mismatch")
            if len({s.scope for s in attributes}) != 1:
                reasons.append("incompatible_scopes_or_cohorts")
            if len({s.comparison_pool_ref for s in attributes}) != 1:
                reasons.append("incompatible_comparison_pools")
            if len({s.evidence.fixture_id if s.evidence else None for s in attributes}) != 1:
                reasons.append("incompatible_fixture_provenance")
        score = None if reasons else math.fsum(s.score for s in attributes) / 5
        overall = OverallCandidate(score, POLICY_NOT_FINALIZED if candidate_policy is None else
            "withheld" if reasons else "synthetic_candidate", tuple(reasons), candidate_policy)
        players.append(PlayerAssembly(context, attributes, overall))
    return tuple(players)
