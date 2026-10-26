"""Bounded integration of Arpit recovery functions with explicit M2A identity.

No I/O, percentile rankings, population selection, or missing-count imputation.
See docs/m2b-recovery.md for input contracts and exposure limitations.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from src.identity import IdentityResult, PLAYER_KEYS, resolve_events, validate_population
from src.metrics.recovery_coverage import (
    EVENT_TYPES, REQUIRED_COLS, add_per90, extract_recovery_events, recovery_counts,
)


class RecoveryError(ValueError):
    """Unsafe input or failed recovery conservation invariant."""


@dataclass
class RecoveryDiagnostic:
    inspected_events: int
    identity: IdentityResult
    accounting: pd.DataFrame


@dataclass
class RecoveryResult:
    identity: IdentityResult
    accounting: pd.DataFrame
    totals: pd.DataFrame
    by_zone: pd.DataFrame


def _extract(events):
    if not events.columns.is_unique:
        raise RecoveryError("events: duplicate column labels")
    required = ["id", "competition_name", "season_name", *REQUIRED_COLS]
    missing = [c for c in required if c not in events]
    if missing:
        raise RecoveryError(f"events: missing columns {missing}")
    if not all(isinstance(v, str) and v.strip() for v in events.id):
        raise RecoveryError("events: missing/invalid event IDs")
    if events.id.duplicated().any():
        raise RecoveryError("events: duplicate event IDs, including excluded actions")
    # Match the supplied raw export's object/empty flag semantics. Nullable
    # BooleanArray propagates pd.NA through ~eq(True), silently excluding a
    # non-failed recovery. Adapt storage on a copy, leaving the formula intact.
    source = events.copy()
    source["ball_recovery_recovery_failure"] = source.ball_recovery_recovery_failure.astype(object)
    rec = extract_recovery_events(source)
    if rec.id.duplicated().any() or not rec.id.isin(events.id).all():
        raise RecoveryError("extraction changed event identity cardinality")
    return rec


def _accounting(rec, resolved):
    if rec.id.tolist() != resolved.id.tolist() or rec.event_type.tolist() != resolved.event_type.tolist():
        raise RecoveryError("identity resolution changed recovery IDs, order or event types")
    rows = []
    for kind in EVENT_TYPES:
        sub = resolved.loc[resolved.event_type.eq(kind)]
        row = {"event_type": kind, "extracted": int(rec.event_type.eq(kind).sum())}
        row.update({status: int(sub.identity_status.eq(status).sum())
                    for status in ["selected", "outside_population", "unresolved"]})
        if row["extracted"] != sum(row[s] for s in ["selected", "outside_population", "unresolved"]):
            raise RecoveryError("recovery count conservation failed across identity resolution")
        rows.append(row)
    return pd.DataFrame(rows)


def inspect_recovery(events, crosswalk, population):
    """Diagnostic only: retain every extracted identity; produce no partial metrics."""
    rec = _extract(events)
    identity = resolve_events(rec, crosswalk, population, strict=False)
    return RecoveryDiagnostic(len(events), identity, _accounting(rec, identity.events))


def _minutes(minutes):
    # Reuse M2A's stable-key validation/normalization; do not deduplicate minutes.
    keys = validate_population(minutes).reset_index(drop=True)
    if "minutes" not in minutes:
        raise RecoveryError("minutes: missing minutes column")
    values = minutes.minutes.reset_index(drop=True)
    if not is_numeric_dtype(values) or is_bool_dtype(values):
        raise RecoveryError("minutes: exposure must be numeric, not strings or flags")
    numeric = values.astype(float)
    if (numeric.notna() & (~np.isfinite(numeric) | numeric.lt(0))).any():
        raise RecoveryError("minutes: exposure must be nonnegative and finite when known")
    keys["minutes"] = numeric
    return keys


def integrate_recovery(events, crosswalk, minutes, population):
    """Resolve all counted events before stable-ID aggregation; fail closed on unknowns.

    Known outsiders remain in identity/accounting. Only explicitly selected rows
    enter metric tables. Missing/zero minutes retain counts with per90=NaN and
    a rate_status. Omitted event-type rows are not filled with invented zeros.
    """
    exposure = _minutes(minutes)
    rec = _extract(events)
    identity = resolve_events(rec, crosswalk, population)
    accounting = _accounting(rec, identity.events)
    selected = identity.selected_events()
    totals, by_zone = recovery_counts(selected, group_cols=PLAYER_KEYS)
    for kind in EVENT_TYPES:
        expected = int(selected.event_type.eq(kind).sum())
        counted = int(totals.loc[totals.event_type.eq(kind), "count"].sum())
        zoned = int(by_zone.loc[by_zone.event_type.eq(kind), "count"].sum())
        if counted != expected or zoned != int((selected.event_type.eq(kind) & selected.zone.notna()).sum()):
            raise RecoveryError("stable-ID aggregation lost or duplicated recovery counts")
    # Unique exposure keys make the unchanged contributor helper's left join safe.
    out = add_per90(totals, exposure, on=PLAYER_KEYS)
    if len(out) != len(totals) or out.duplicated(PLAYER_KEYS + ["event_type"]).any():
        raise RecoveryError("minutes join multiplied recovery rows")
    out["rate_status"] = "ok"
    out.loc[out.minutes.eq(0), "rate_status"] = "zero_minutes"
    out.loc[out.minutes.isna(), "rate_status"] = "missing_minutes"
    return RecoveryResult(identity, accounting, out, by_zone)
