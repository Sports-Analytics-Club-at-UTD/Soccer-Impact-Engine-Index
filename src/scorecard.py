"""Pure assembly of existing metric results; no scoring or coverage policy."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from src.identity import IdentityError, PLAYER_KEYS, validate_population
from src.metrics.press_actions import COUNT_COLS, DERIVED_COLS
from src.metrics.recovery_coverage import EVENT_TYPES
from src.passing import PassingResult
from src.press_resistance import PressResult
from src.recovery import RecoveryResult


class ScorecardError(ValueError):
    """An unsafe schema, exposure, context or cardinality mismatch."""


@dataclass
class ScorecardResult:
    scorecard: pd.DataFrame
    diagnostics: dict


DESCRIPTORS = ["player_name", "position_group", "minutes", "matches"]
RECOVERY_PREFIXES = dict(zip(EVENT_TYPES, ["recovery_tackle", "recovery_interception",
                                         "recovery_ball_recovery"]))
PRESS_FIELDS = [*COUNT_COLS, *DERIVED_COLS]
PRESS_COUNTS = [*COUNT_COLS, "pressured_actions", "successful_pressured_actions"]
PASS_COUNTS = ["prog_attempts", "prog_passes", "third_cross"]
PASS_FIELDS = [*PASS_COUNTS, "value_sum", "prog_passes_p90", "prog_completion_pct",
               "third_cross_p90", "pass_value_p90"]


def _columns(table, required, optional, label):
    if not isinstance(table, pd.DataFrame) or not table.columns.is_unique:
        raise ScorecardError(f"{label}: DataFrame with unique column labels required")
    missing = [c for c in required if c not in table]
    extra = [c for c in table if c not in [*required, *optional]]
    if missing or extra:
        raise ScorecardError(f"{label}: missing columns {missing}; unsupported columns {extra}")


def _canonical(table, label):
    try:
        keys = validate_population(table).reset_index(drop=True)
    except IdentityError as exc:
        raise ScorecardError(f"{label}: {exc}") from exc
    out = table.copy(deep=True).reset_index(drop=True)
    for c in PLAYER_KEYS:
        out[c] = keys[c]
    return out


def _numeric(table, columns, label, *, integers=False, allow_missing=True):
    for c in columns:
        values = table[c]
        if (not is_numeric_dtype(values) or is_bool_dtype(values)
                or np.iscomplexobj(values)):
            raise ScorecardError(f"{label}.{c}: real numeric values required")
        known = values.dropna()
        if (not np.isfinite(known.to_numpy(dtype=float)).all() or known.lt(0).any()
                or (not allow_missing and values.isna().any())):
            raise ScorecardError(f"{label}.{c}: finite nonnegative values required")
        if integers:
            if any(v != int(v) or int(v) > 2**63 - 1 for v in known):
                raise ScorecardError(f"{label}.{c}: signed int64 counts required")
            table[c] = values.astype("Int64")
        else:
            table[c] = values.astype("Float64")


def _status(table, label):
    if not table.rate_status.isin(["ok", "missing_minutes", "zero_minutes"]).all():
        raise ScorecardError(f"{label}: invalid rate_status")
    # Validate the status contract, without recalculating any metric rates.
    expected = pd.Series("ok", index=table.index)
    expected.loc[table.minutes.isna()] = "missing_minutes"
    expected.loc[table.minutes.eq(0).fillna(False)] = "zero_minutes"
    if not table.rate_status.eq(expected).all():
        raise ScorecardError(f"{label}: rate_status conflicts with minutes")
    table["rate_status"] = table.rate_status.astype("string")


def assemble_scorecard(base, *, recovery=None, press=None, passing=None):
    """Attach optional RecoveryResult/PressResult/PassingResult to verified base.

    Only totals are assembled; upstream event validation is the caller's contract.
    Presence describes supplied rows, never complete source coverage. Unknown
    contexts fail; missing exposure is preserved, and known exposures must agree.
    See docs/m4b0-scorecard-assembly.md for the fixed output schema.
    """
    _columns(base, PLAYER_KEYS, DESCRIPTORS, "base")
    out = _canonical(base, "base")
    descriptors = [c for c in DESCRIPTORS if c in out]
    out = out[[*PLAYER_KEYS, *descriptors]]
    if "minutes" in out:
        _numeric(out, ["minutes"], "base")
    if "matches" in out:
        _numeric(out, ["matches"], "base", integers=True)
    for c in ["player_name", "position_group"]:
        if c in out and not all(isinstance(v, str) for v in out[c].dropna()):
            raise ScorecardError(f"base.{c}: descriptive strings or missing values required")
    out = out.sort_values(PLAYER_KEYS, kind="stable").reset_index(drop=True)
    exposures = ([out.loc[out.minutes.notna(), [*PLAYER_KEYS, "minutes"]]]
                 if "minutes" in out and out.minutes.notna().any() else [])
    diagnostics = {"base_rows": len(out), "components": {},
                   "coverage_statement": "Row presence only; source completeness is not verified.",
                   "passing_reference": None}

    def attach(source, label, rename, counts):
        nonlocal out
        if source is None:
            source = pd.DataFrame({c: pd.Series(dtype="Int64" if c == "player_id" else "object")
                                   for c in [*PLAYER_KEYS, *rename]})
        membership = source[PLAYER_KEYS].merge(out[PLAYER_KEYS], on=PLAYER_KEYS,
                                              how="left", indicator=True, validate="one_to_one")
        unknown = membership.loc[membership["_merge"].eq("left_only"), PLAYER_KEYS]
        if not unknown.empty:
            raise ScorecardError(f"{label}: {len(unknown)} metric contexts absent from base; "
                                 f"examples: {unknown.head(3).to_dict('records')}")
        if "minutes" in source and source.minutes.notna().any():
            exposures.append(source.loc[source.minutes.notna(), [*PLAYER_KEYS, "minutes"]])
        selected = source[[*PLAYER_KEYS, *rename]].rename(columns=rename)
        present = f"{label}_present"
        selected[present] = pd.Series(True, index=selected.index, dtype="boolean")
        if set(selected.columns).difference(PLAYER_KEYS).intersection(out.columns):
            raise ScorecardError(f"{label}: output column collision")
        out = out.merge(selected, on=PLAYER_KEYS, how="left", validate="one_to_one", sort=False)
        out[present] = out[present].fillna(False).astype(bool)
        if len(out) != len(base) or int(out[present].sum()) != len(source):
            raise ScorecardError(f"{label}: assembly changed row cardinality")
        totals = {}
        for c in counts:
            before = sum(int(v) for v in source[c].dropna())
            after = sum(int(v) for v in out[rename[c]].dropna())
            if before != after:
                raise ScorecardError(f"{label}.{c}: count conservation failed")
            totals[c] = before
        diagnostics["components"][label] = {
            "source_rows": len(source), "present_rows": int(out[present].sum()),
            "absent_base_rows": int((~out[present]).sum()), "count_totals": totals,
            "present_na_values": {rename[c]: int(source[c].isna().sum()) for c in rename},
        }

    if recovery is not None:
        if not isinstance(recovery, RecoveryResult):
            raise ScorecardError("recovery: supply RecoveryResult, not a diagnostic or delivery table")
        _columns(recovery.totals, [*PLAYER_KEYS, "event_type", "count", "minutes", "per90",
                                   "rate_status"], [], "recovery")
        if not recovery.totals.event_type.isin(EVENT_TYPES).all():
            raise ScorecardError("recovery: unknown or missing event_type")
    for kind, prefix in RECOVERY_PREFIXES.items():
        part = None
        if recovery is not None:
            part = _canonical(recovery.totals.loc[recovery.totals.event_type.eq(kind)], prefix)
            _numeric(part, ["count"], prefix, integers=True, allow_missing=False)
            _numeric(part, ["minutes", "per90"], prefix)
            _status(part, prefix)
        attach(part, prefix, {c: f"{prefix}_{c}" for c in
                             ["count", "per90", "rate_status", "minutes"]}, ["count"])

    if press is not None:
        if not isinstance(press, PressResult):
            raise ScorecardError("press: supply PressResult, not a diagnostic or delivery table")
        _columns(press.totals, [*PLAYER_KEYS, *PRESS_FIELDS], ["minutes"], "press")
        part = _canonical(press.totals, "press")
        _numeric(part, PRESS_COUNTS, "press", integers=True, allow_missing=False)
        _numeric(part, [c for c in PRESS_FIELDS if c not in PRESS_COUNTS], "press")
        if "minutes" not in part:
            part["minutes"] = pd.Series(pd.NA, index=part.index, dtype="Float64")
        _numeric(part, ["minutes"], "press")
    else:
        part = None
    attach(part, "press", {**{c: c for c in PRESS_FIELDS}, "minutes": "press_minutes"}, PRESS_COUNTS)

    if passing is not None:
        if not isinstance(passing, PassingResult):
            raise ScorecardError("passing: supply PassingResult, not a sample diagnostic")
        if (not isinstance(passing.difficulty_scope, str) or not passing.difficulty_scope.strip()
                or passing.difficulty_complete is not True):
            raise ScorecardError("passing: labeled, declared-complete reference required; "
                                 "assembly does not verify season completeness")
        _columns(passing.totals, [*PLAYER_KEYS, *PASS_FIELDS, "minutes", "rate_status"], [], "passing")
        part = _canonical(passing.totals, "passing")
        _numeric(part, PASS_COUNTS, "passing", integers=True, allow_missing=False)
        _numeric(part, [c for c in PASS_FIELDS if c not in PASS_COUNTS] + ["minutes"], "passing")
        _status(part, "passing")
        part["difficulty_scope"] = passing.difficulty_scope
        part["difficulty_complete"] = passing.difficulty_complete
        diagnostics["passing_reference"] = {"scope": passing.difficulty_scope,
                                              "declared_complete": passing.difficulty_complete,
                                              "independently_verified": False}
    else:
        part = None
    attach(part, "passing", {**{c: c for c in PASS_FIELDS}, "minutes": "passing_minutes",
                             "rate_status": "passing_rate_status",
                             "difficulty_scope": "passing_difficulty_scope",
                             "difficulty_complete": "passing_difficulty_complete"}, PASS_COUNTS)

    # Missing exposure is not disagreement; never fill it from another source.
    if exposures:
        known = pd.concat(exposures, ignore_index=True).dropna(subset=["minutes"])
        conflicts = known.groupby(PLAYER_KEYS, dropna=False).minutes.nunique().gt(1)
        if conflicts.any():
            examples = conflicts[conflicts].index.tolist()[:3]
            raise ScorecardError(f"conflicting minutes across inputs; contexts: {examples}")

    # Stable nullable storage prevents absent rows from turning large counts into floats.
    count_columns = [f"{p}_count" for p in RECOVERY_PREFIXES.values()] + PRESS_COUNTS + PASS_COUNTS
    string_columns = [f"{p}_rate_status" for p in RECOVERY_PREFIXES.values()] + [
        "passing_rate_status", "passing_difficulty_scope"]
    for c in out.columns.difference([*PLAYER_KEYS, *descriptors]):
        if c.endswith("_present"):
            continue
        dtype = ("Int64" if c in count_columns else "string" if c in string_columns
                 else "boolean" if c == "passing_difficulty_complete" else "Float64")
        out[c] = out[c].astype(dtype)
    return ScorecardResult(out.reset_index(drop=True), diagnostics)
