"""Guarded recovery reuse API; historical recovery_coverage stays unchanged.

Inputs must already carry source-verified stable IDs. For raw events requiring
identity resolution, use src.recovery.integrate_recovery instead. This adapter
neither resolves names nor establishes exposure support. See
docs/recovery-helper-hardening-report.md for the compatibility boundary.
"""
import numpy as np
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from src.identity import PLAYER_KEYS, _columns, _ids, _text
from src.metrics.recovery_coverage import EVENT_TYPES, recovery_counts as _counts


class RecoveryInputError(ValueError):
    """Unsafe grouping, event identity, or exposure join."""


def _keys(keys, label):
    if isinstance(keys, str):
        raise RecoveryInputError(f"{label}: supply a sequence containing PLAYER_KEYS")
    keys = list(keys)
    if len(keys) != len(set(keys)) or not set(PLAYER_KEYS).issubset(keys):
        raise RecoveryInputError(f"{label}: require all canonical PLAYER_KEYS {PLAYER_KEYS}")
    if set(keys) & {"count", "minutes", "per90", "event_type", "zone", "id"}:
        raise RecoveryInputError(f"{label}: keys contain an event or measurement column")
    return keys


def _identity(table, keys, label):
    _columns(table, keys, label)
    _ids(table.player_id, f"{label}.player_id")
    for col in keys:
        if col != "player_id":
            if table[col].isna().any():
                raise RecoveryInputError(f"{label}.{col}: null join/group keys")
            if col in PLAYER_KEYS:
                _text(table[col], f"{label}.{col}")


def _numeric(series, label):
    if series.empty:
        return
    if not is_numeric_dtype(series) or is_bool_dtype(series):
        raise RecoveryInputError(f"{label}: require numeric values, not strings or flags")
    if (series.notna() & (~np.isfinite(series) | series.lt(0))).any():
        raise RecoveryInputError(f"{label}: require finite nonnegative values when known")


def recovery_counts(rec, group_cols=tuple(PLAYER_KEYS)):
    """Count selected, uniquely identified events by stable player/team/season.

    Return the historical (totals, by_zone) shapes, using canonical keys by
    default. Unknown zones count in totals only. No name-based ID inference.
    Additional grouping dimensions are allowed; canonical contexts cannot be
    omitted. Names are descriptive, not required grouping dimensions.
    """
    keys = _keys(group_cols, "group_cols")
    _identity(rec, keys, "recovery events")
    _columns(rec, ["id", "event_type", "zone"], "recovery events")
    _text(rec.id, "recovery events.id")
    if rec.id.duplicated().any():
        raise RecoveryInputError("recovery events: duplicate event UUIDs or conflicting UUID identities")
    if not rec.event_type.isin(EVENT_TYPES).all():
        raise RecoveryInputError("recovery events: unknown/missing event_type")
    totals, zones = _counts(rec, group_cols=keys)
    if totals["count"].sum() != len(rec) or zones["count"].sum() != rec.zone.notna().sum():
        raise RecoveryInputError("recovery events: count conservation failed")
    return totals, zones


def add_per90(counts, minutes, on, min_minutes=None):
    """Attach one denominator per canonical context to any number of count rows.

    Missing/zero denominators yield NaN rates. Negative/nonfinite exposure,
    duplicate denominators, null keys and existing rate columns fail closed.
    Numerators and input row order are preserved; no deduplication or imputation.
    """
    keys = _keys(on, "on")
    _identity(counts, keys, "counts")
    _identity(minutes, keys, "minutes")
    _columns(counts, ["count"], "counts")
    _columns(minutes, ["minutes"], "minutes")
    if {"minutes", "per90"}.intersection(counts.columns):
        raise RecoveryInputError("counts: minutes/per90 already present; supply original numerators")
    _numeric(counts["count"], "counts.count")
    if counts["count"].isna().any():
        raise RecoveryInputError("counts.count: missing numerators")
    _numeric(minutes.minutes, "minutes.minutes")
    if min_minutes is not None:
        if isinstance(min_minutes, (bool, str)) or not np.isscalar(min_minutes):
            raise RecoveryInputError("min_minutes: require a finite nonnegative number")
        if not np.isfinite(min_minutes) or min_minutes < 0:
            raise RecoveryInputError("min_minutes: require a finite nonnegative number")
    if minutes.duplicated(keys).any():
        raise RecoveryInputError("minutes: duplicate join keys; supply one supported denominator per context")
    out = counts.merge(minutes[keys + ["minutes"]], on=keys, how="left",
                       validate="many_to_one", sort=False)
    if len(out) != len(counts) or not out[counts.columns].reset_index(drop=True).equals(counts.reset_index(drop=True)):
        raise RecoveryInputError("minutes join changed count rows, identity, order or numerators")
    out["per90"] = out["count"].div(out["minutes"]).mul(90).where(out["minutes"] > 0)
    if min_minutes is not None:
        out.loc[out["minutes"] < min_minutes, "per90"] = np.nan
    return out
