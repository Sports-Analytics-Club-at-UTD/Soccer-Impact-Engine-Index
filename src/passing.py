"""Explicit-cohort Level A passing integration; no rankings, Level B or file I/O."""
from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from src.identity import IdentityResult, PLAYER_KEYS, resolve_events, validate_population
from src.metrics.progressive_passes import (
    LENGTH_BANDS, PASS_EXCLUDED, REQUIRED_COLS, flag_progressive, is_open_play_pass,
    level_a_counts, per90, prepare_passes,
)

CELL = ["competition_name", "season_name", "start_third", "length_band"]
COUNTS = ["prog_attempts", "prog_passes", "third_cross", "value_sum"]
CATEGORIES = ["non_pass", "non_open_play", "excluded_outcome", "missing_geometry", "measurable"]


class PassingError(ValueError):
    """Invalid passing contract, unsafe calibration or failed conservation."""


@dataclass(frozen=True)
class DifficultyReference:
    cells: pd.DataFrame
    scope: str
    complete: bool
    accounting: dict
    matches: dict


@dataclass
class PassingDiagnostic:
    preparation: dict
    event_accounting: pd.DataFrame
    identity: IdentityResult
    accounting: pd.DataFrame
    difficulty_scope: str
    difficulty_complete: bool


@dataclass
class PassingResult(PassingDiagnostic):
    totals: pd.DataFrame


def _prepare(events):
    if not events.columns.is_unique:
        raise PassingError("events: duplicate column labels")
    missing = [c for c in REQUIRED_COLS if c not in events]
    if missing:
        raise PassingError(f"events: missing columns {missing}")
    reserved = {"x0", "y0", "x1", "y1", "completed", "d0", "d1", "forward", "length",
                "start_third", "end_third", "length_band", "p_hat", "difficulty",
                "prog_attempt", "progressive", "third_cross", "pass_value"}
    if reserved.intersection(events.columns):
        raise PassingError("events: reserved passing output column collision")
    if not all(isinstance(v, str) and v.strip() for v in events.id):
        raise PassingError("events: missing/invalid event IDs")
    if events.id.duplicated().any():
        raise PassingError("events: duplicate event IDs, including excluded events")
    raw = events.reset_index(drop=True)
    passes = prepare_passes(raw)
    # The original preparation projection omits player_id. Restore it by unique
    # event ID before M2A, rather than creating player_id_x/player_id_y joins.
    if "player_id" in raw:
        passes["player_id"] = passes.id.map(raw.set_index("id").player_id)
    for c in ["competition_name", "season_name"]:
        if not all(isinstance(v, str) and v.strip() for v in passes[c]):
            raise PassingError(f"measurable passes: invalid {c}")
    numeric = passes[["x0", "y0", "x1", "y1", "d0", "d1", "forward", "length"]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all() or passes.length.lt(0).any():
        raise PassingError("measurable passes: nonfinite geometry or negative length")
    ledger = raw[["id", "player", "team", "competition_name", "season_name"]].copy()
    is_pass = raw.type.eq("Pass").fillna(False)
    open_play = is_open_play_pass(raw).fillna(False)
    excluded = open_play & raw.pass_outcome.isin(PASS_EXCLUDED)
    ledger["category"] = "non_pass"
    ledger.loc[is_pass & ~open_play, "category"] = "non_open_play"
    ledger.loc[excluded, "category"] = "excluded_outcome"
    ledger.loc[open_play & ~excluded, "category"] = "missing_geometry"
    ledger.loc[raw.id.isin(passes.id), "category"] = "measurable"
    summary = {c: int(ledger.category.eq(c).sum()) for c in CATEGORIES}
    summary.update(raw_events=len(raw), pass_events=int(is_pass.sum()), open_play=int(open_play.sum()))
    if sum(summary[c] for c in CATEGORIES) != len(raw) or summary["measurable"] != len(passes):
        raise PassingError("preparation accounting lost or multiplied events")
    return passes, ledger, summary


def _bands(passes):
    out = passes.copy()
    out["length_band"] = pd.cut(out.length, LENGTH_BANDS, right=False,
                                labels=["0-15", "15-30", "30+"]).astype("string")
    return out


def calibrate_difficulty(reference_events, *, scope, complete):
    """Fit all measurable supplied passes, never a reporting-population subset.

    Accept a DataFrame or iterable of disjoint raw batches. `complete` is an
    explicit caller attestation about the named cohort, not proof of coverage.
    False marks an illustrative sample and cannot feed production metrics.
    """
    if not isinstance(scope, str) or not scope.strip() or type(complete) is not bool:
        raise PassingError("reference requires a scope label and explicit boolean completeness")
    batches = [reference_events] if isinstance(reference_events, pd.DataFrame) else reference_events
    pieces, seen, summary, matches = [], set(), Counter(), {}
    for raw in batches:
        passes, _, counts = _prepare(raw)
        if seen.intersection(raw.id):
            raise PassingError("reference: duplicate event IDs across batches")
        seen.update(raw.id)
        summary.update(counts)
        for (comp, season), group in raw.groupby(["competition_name", "season_name"]):
            matches.setdefault((comp, season), set()).update(group.match_id.dropna().tolist())
        p = _bands(passes)
        cell = p.groupby(CELL, observed=True).completed.agg(attempts="size", completions="sum").reset_index()
        pieces.append(cell)
    if not pieces:
        raise PassingError("reference: no supplied batches")
    cells = pd.concat(pieces, ignore_index=True).groupby(CELL, observed=True)[["attempts", "completions"]].sum().reset_index()
    if cells.empty:
        raise PassingError("reference: no measurable open-play passes")
    cells["p_hat"] = cells.completions / cells.attempts
    return DifficultyReference(cells, scope, complete, dict(summary), {k: len(v) for k, v in matches.items()})


def _apply_reference(passes, reference):
    if not isinstance(reference, DifficultyReference):
        raise PassingError("supply an explicit calibrated DifficultyReference")
    if (not isinstance(reference.scope, str) or not reference.scope.strip()
            or type(reference.complete) is not bool):
        raise PassingError("reference: invalid scope/completeness metadata")
    cells = reference.cells
    required = [*CELL, "attempts", "completions", "p_hat"]
    if cells.empty or not cells.columns.is_unique or any(c not in cells for c in required) or cells.duplicated(CELL).any():
        raise PassingError("reference: invalid or duplicate calibration cells")
    for c in ["attempts", "completions", "p_hat"]:
        if not is_numeric_dtype(cells[c]) or is_bool_dtype(cells[c]) or not np.isfinite(cells[c].astype(float)).all():
            raise PassingError("reference: invalid cell counts/probabilities")
    if (cells.attempts.le(0).any() or cells.completions.lt(0).any()
            or cells.completions.gt(cells.attempts).any()
            or cells.attempts.ne(np.floor(cells.attempts)).any()
            or cells.completions.ne(np.floor(cells.completions)).any()
            or not np.allclose(cells.p_hat, cells.completions / cells.attempts, atol=1e-12, rtol=1e-12)):
        raise PassingError("reference: inconsistent calibration statistics")
    out = _bands(passes).merge(cells[[*CELL, "p_hat"]], on=CELL, how="left",
                               validate="many_to_one", sort=False)
    if len(out) != len(passes) or out.id.tolist() != passes.id.tolist():
        raise PassingError("difficulty join changed event cardinality/order")
    if out.p_hat.isna().any():
        raise PassingError("reference does not cover every reporting pass cell; no fallback estimates")
    out["difficulty"] = 1.0 - out.p_hat
    return flag_progressive(out)


def _identity_accounting(passes, resolved):
    columns = ["id", "prog_attempt", "progressive", "third_cross", "pass_value"]
    if not passes[columns].reset_index(drop=True).equals(resolved[columns].reset_index(drop=True)):
        raise PassingError("identity join changed measurable passes or values")
    if (resolved.progressive.gt(resolved.prog_attempt).any()
            or resolved.third_cross.gt(resolved.progressive).any()):
        raise PassingError("invalid progressive/third-crossing subset")
    rows = []
    for status in ["selected", "outside_population", "unresolved"]:
        group = resolved.loc[resolved.identity_status.eq(status)]
        rows.append(dict(status=status, measurable=len(group), prog_attempts=int(group.prog_attempt.sum()),
                         prog_passes=int(group.progressive.sum()), third_cross=int(group.third_cross.sum()),
                         value_sum=float(group.pass_value.sum())))
    out = pd.DataFrame(rows)
    if (out.measurable.sum() != len(passes) or out.prog_attempts.sum() != passes.prog_attempt.sum()
            or out.prog_passes.sum() != passes.progressive.sum() or out.third_cross.sum() != passes.third_cross.sum()
            or not np.isclose(out.value_sum.sum(), passes.pass_value.sum(), atol=1e-6, rtol=1e-9)):
        raise PassingError("identity count/value conservation failed")
    return out


def inspect_progressive_passing(events, crosswalk, population, *, reference):
    """Diagnostic only, including sample-reference labels; never partial player metrics."""
    passes, ledger, summary = _prepare(events)
    valued = _apply_reference(passes, reference)
    identity = resolve_events(valued, crosswalk, population, strict=False)
    accounting = _identity_accounting(valued, identity.events)
    return PassingDiagnostic(summary, ledger, identity, accounting, reference.scope, reference.complete)


def _rates(counts, minutes):
    exposure = validate_population(minutes).reset_index(drop=True)
    if "minutes" not in minutes:
        raise PassingError("minutes: missing minutes column")
    values = minutes.minutes.reset_index(drop=True)
    if not is_numeric_dtype(values) or is_bool_dtype(values) or np.iscomplexobj(values):
        raise PassingError("minutes: numeric exposure required")
    numeric = values.astype(float)
    if (numeric.notna() & (~np.isfinite(numeric) | numeric.lt(0))).any():
        raise PassingError("minutes: exposure must be finite and nonnegative when known")
    exposure["minutes"] = numeric
    out = counts.merge(exposure, on=PLAYER_KEYS, how="left", validate="one_to_one", sort=False)
    if len(out) != len(counts) or not out[COUNTS].equals(counts[COUNTS].reset_index(drop=True)):
        raise PassingError("minutes join changed observed counts/values")
    out["prog_passes_p90"] = per90(out.prog_passes, out.minutes)
    out["prog_completion_pct"] = 100 * out.prog_passes / out.prog_attempts.replace(0, np.nan)
    out["third_cross_p90"] = per90(out.third_cross, out.minutes)
    out["pass_value_p90"] = per90(out.value_sum, out.minutes)
    out["rate_status"] = "ok"
    out.loc[out.minutes.eq(0), "rate_status"] = "zero_minutes"
    out.loc[out.minutes.isna(), "rate_status"] = "missing_minutes"
    return out


def integrate_progressive_passing(events, crosswalk, population, minutes, *, reference):
    """Strict Level A metrics using a declared complete, independently supplied cohort."""
    if not isinstance(reference, DifficultyReference) or reference.complete is not True:
        raise PassingError("production requires a declared complete reference cohort; samples are diagnostic only")
    passes, ledger, summary = _prepare(events)
    valued = _apply_reference(passes, reference)
    identity = resolve_events(valued, crosswalk, population)
    accounting = _identity_accounting(valued, identity.events)
    selected = identity.selected_events()
    counts = level_a_counts(selected)
    contexts = selected[PLAYER_KEYS].drop_duplicates().merge(
        counts[PLAYER_KEYS], on=PLAYER_KEYS, how="outer", validate="one_to_one", indicator=True)
    if contexts["_merge"].ne("both").any():
        raise PassingError("stable-ID aggregation lost or invented observed player contexts")
    expected = [selected.prog_attempt.sum(), selected.progressive.sum(), selected.third_cross.sum(), selected.pass_value.sum()]
    observed = counts[COUNTS].sum()
    if (counts.duplicated(PLAYER_KEYS).any() or observed.iloc[:3].tolist() != expected[:3]
            or not np.isclose(observed.iloc[3], expected[3], atol=1e-6, rtol=1e-9)):
        raise PassingError("stable-ID aggregation lost or multiplied counts/values")
    return PassingResult(summary, ledger, identity, accounting, reference.scope, reference.complete,
                         _rates(counts, minutes))
