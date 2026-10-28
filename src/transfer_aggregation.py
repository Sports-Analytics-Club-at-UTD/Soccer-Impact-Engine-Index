"""Pure match-ledger transfer experiments; no delivered exposure certification."""
from dataclasses import dataclass
import math

from src.dri_scoring import LEAGUES, SEASON, ROLE_GROUPS
from src.rating_assembly import PlayerContext, _context

COUNTS = ("tackles", "interceptions", "recoveries", "pressured_pass_attempts",
          "pressured_pass_completed", "pressured_dribble_attempts", "pressured_dribble_completed")


@dataclass(frozen=True)
class TransferPolicy:
    policy_id: str
    combine_clubs: bool
    allow_cross_league: bool
    reference_context: PlayerContext
    pool_id: str
    admit_reference: bool
    source: str


def aggregate_transfer(contributions, *, policy):
    """Combine synthetic match numerators/minutes only under explicit policy.

    One row per match/actor is required. Duplicate match IDs are rejected, even
    across clubs. Real evidence is retained but never gets an aggregate exposure.
    Result preserves every contribution and exactly one nominated context.
    """
    if not isinstance(contributions, (list, tuple)) or not contributions:
        raise ValueError("nonempty contribution ledger required")
    seen = set(); contexts = set(); roles = set(); lineage = []; reasons = []
    minute_values = []; totals = dict.fromkeys(COUNTS, 0)
    for row in contributions:
        if set(row) != {"context", "role", "match_id", "minutes", "counts", "source", "synthetic"}:
            raise ValueError("exact contribution fields required")
        context = row["context"]; _context(context); contexts.add(context)
        if row["role"] not in ROLE_GROUPS:
            raise ValueError("unsupported transfer role")
        roles.add(ROLE_GROUPS[row["role"]])
        mid = row["match_id"]
        if type(mid) is not int or not 0 < mid <= 2**63-1 or mid in seen:
            raise ValueError("invalid or duplicate actor match contribution")
        seen.add(mid)
        if type(row["synthetic"]) is not bool or not isinstance(row["source"], str) or not row["source"].strip():
            raise ValueError("explicit evidence lineage required")
        if row["synthetic"] is not True:
            reasons.append("source_exposure_not_certified")
        minutes = row["minutes"]
        if minutes is None:
            reasons.append("missing_minutes")
        elif type(minutes) not in (int, float) or not math.isfinite(minutes) or minutes <= 0:
            raise ValueError("positive supported minutes required")
        else:
            minute_values.append(minutes)
        if set(row["counts"]) != set(COUNTS):
            raise ValueError("raw numerator contract required; no ratings or percentiles")
        for key, value in row["counts"].items():
            if type(value) is not int or not 0 <= value <= 2**63-1:
                raise ValueError("exact nonnegative numerator required")
            totals[key] += value
        for action in ("pass", "dribble"):
            if row["counts"][f"pressured_{action}_completed"] > row["counts"][f"pressured_{action}_attempts"]:
                raise ValueError("completed actions exceed attempts")
        lineage.append({**row, "counts": dict(row["counts"])})
    if len({c.player_id for c in contexts}) != 1 or len({c.season_name for c in contexts}) != 1 or len(roles) != 1:
        reasons.append("incompatible_identity_season_or_role")
    if any(c.season_name != SEASON or c.competition_name not in LEAGUES for c in contexts):
        reasons.append("outside_reference_scope")
    if policy is None:
        reasons.append("transfer_policy_missing")
    elif not isinstance(policy, TransferPolicy):
        raise ValueError("explicit TransferPolicy required")
    else:
        _context(policy.reference_context)
        if any(type(v) is not bool for v in (policy.combine_clubs, policy.allow_cross_league, policy.admit_reference)):
            raise ValueError("explicit transfer policy booleans required")
        if any(not isinstance(v,str) or not v.strip() for v in (policy.policy_id,policy.pool_id,policy.source)):
            raise ValueError("transfer policy provenance required")
        if not policy.combine_clubs or policy.reference_context not in contexts:
            reasons.append("transfer_policy_inapplicable")
        if len({c.competition_name for c in contexts}) > 1 and not policy.allow_cross_league:
            reasons.append("cross_league_transfer_not_permitted")
    try:
        total_minutes = math.fsum(minute_values)
    except OverflowError as exc:
        raise ValueError("aggregate exposure overflow") from exc
    if not math.isfinite(total_minutes) or any(v > 2**63-1 for v in totals.values()):
        raise ValueError("aggregate overflow")
    reasons = tuple(sorted(set(reasons)))
    return dict(status="withheld" if reasons else "synthetic_combined", reasons=reasons,
        context=policy.reference_context if policy else None, role=next(iter(roles)) if len(roles)==1 else None,
        minutes=None if reasons else total_minutes, counts=None if reasons else totals,
        per90=None if reasons else {k: totals[k]/total_minutes*90 for k in COUNTS[:3]},
        contributions=tuple(sorted(lineage,key=lambda r:r["match_id"])), policy=policy,
        reference_member=bool(not reasons and policy.admit_reference), publication_authorized=False)


def require_unique_memberships(results):
    """At most one reference member per canonical actor/season/pool."""
    seen = set()
    for result in results:
        if not result["reference_member"]:
            continue
        c = result["context"]
        key = (c.player_id, c.season_name, result["policy"].pool_id)
        if key in seen:
            raise ValueError("duplicate reference membership")
        seen.add(key)
    return tuple(results)
