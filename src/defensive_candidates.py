"""Synthetic Arpit component experiment; D3A approves aggregate DRI only."""
from dataclasses import asdict, dataclass

from src.dri_scoring import score_dri, PREFIXES
from src.identity_evidence import SYNTHETIC

POLICY_ID = "arpit-component-per90-sample-z/v1"
SOURCE = "68c5802:src/metrics/recovery_scores.py"
FORMULA = "clip(65+10*(per90-mean)/sample_std,1,99)"
ATTRIBUTES = dict(zip(PREFIXES.values(), ("tackles", "interceptions", "recoveries")))


@dataclass(frozen=True)
class DefensivePolicy:
    policy_id: str
    source: str
    formula: str
    synthetic_only: bool


def evaluate_defensive_candidates(population, measurements, *, pool, policy):
    """Reuse DRI input/identity/scope gates; transform each component's per90.

    Constant/singleton pools withhold rather than copying the contributor's
    neutral-65 fallback. Never transform DRI or a component percentile to FIFA.
    """
    if pool.evidence_kind != SYNTHETIC:
        raise ValueError("defensive candidates require synthetic evidence")
    if policy is not None and policy != DefensivePolicy(POLICY_ID, SOURCE, FORMULA, True):
        raise ValueError("unsupported explicit defensive candidate policy")
    checked = score_dri(population, measurements, pool=pool)
    rows = checked.players.copy(deep=True)
    for prefix, attribute in ATTRIBUTES.items():
        rows[f"{attribute}_rating"] = float("nan")
        rows[f"{attribute}_rank"] = float("nan")
        rows[f"{attribute}_reasons"] = [tuple(r) if not eligible else
            ("candidate_policy_not_selected",) if policy is None else ()
            for r, eligible in zip(rows.reasons, rows.eligible)]
        if policy is None:
            continue
        for group in ("MID", "CB"):
            selected = rows.index[rows.eligible & rows.score_group.eq(group)]
            values = rows.loc[selected, f"{prefix}_per90"]
            reason = "insufficient_component_pool" if len(values) < 2 else (
                "constant_component_pool" if values.nunique() == 1 else None)
            if reason:
                for i in selected:
                    rows.at[i, f"{attribute}_reasons"] = (reason,)
                continue
            rows.loc[selected, f"{attribute}_rank"] = values.rank(method="average", pct=True) * 100
            rows.loc[selected, f"{attribute}_rating"] = (
                65 + 10 * (values - values.mean()) / values.std(ddof=1)).clip(1, 99)
    return rows, {"policy": asdict(policy) if policy else None,
                  "policy_approved": False, "publication_authorized": False}
