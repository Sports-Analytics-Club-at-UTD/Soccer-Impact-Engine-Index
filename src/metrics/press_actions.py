"""Pure action-level adaptation of Pratyush V2, without rankings or file I/O.

Reference: origin/pratyush-dev, 77c1639935fb9e1988dd9112c094277973ca0bcd,
src/metrics/press_resistancev2.py:357-466 (filter/counts), 507-527 (combined rate).
Season/population policy and legacy dropping of unknown names are not imported.
"""
import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from src.identity import PLAYER_KEYS

COUNT_COLS = [
    "pressured_pass_attempts", "pressured_pass_completed",
    "pressured_dribble_attempts", "pressured_dribble_completed",
]
RATE_COLS = ["pressured_pass_completion_rate", "pressured_dribble_completion_rate",
             "press_resistance_rate"]
DERIVED_COLS = ["pressured_actions", "successful_pressured_actions", *RATE_COLS]


class PressResistanceError(ValueError):
    """Invalid action inputs or violated conservation invariants."""


def classify_actions(events):
    """Select pressured Pass/Dribble rows and retain IDs/names for strict identity."""
    if not events.columns.is_unique:
        raise PressResistanceError("events: duplicate column labels")
    required = ["type", "under_pressure", "pass_outcome", "dribble_outcome"]
    missing = [c for c in required if c not in events]
    if missing:
        raise PressResistanceError(f"events: missing action columns {missing}")
    if any(c in events for c in ["successful", *COUNT_COLS, *DERIVED_COLS]):
        raise PressResistanceError("events: reserved action output column collision")
    # Object comparison preserves V2's True/empty flag semantics without pandas'
    # object fillna downcasting warning. Missing pressure never selects an action.
    keep = events.under_pressure.astype(object).eq(True) & events.type.isin(["Pass", "Dribble"])
    mapped = events.loc[keep].copy()
    # Nullable string missing outcomes behave like the original raw object export:
    # a missing dribble outcome is not Complete; a missing pass outcome completes.
    mapped["dribble_outcome"] = mapped.dribble_outcome.astype(object)
    is_pass = mapped["type"].eq("Pass")
    mapped["successful"] = (
        (is_pass & mapped["pass_outcome"].isna())
        | (~is_pass & mapped["dribble_outcome"].eq("Complete"))
    )
    mapped["pressured_pass_attempts"] = is_pass.astype(int)
    mapped["pressured_pass_completed"] = (is_pass & mapped["successful"]).astype(int)
    mapped["pressured_dribble_attempts"] = (~is_pass).astype(int)
    mapped["pressured_dribble_completed"] = (~is_pass & mapped["successful"]).astype(int)
    return mapped


def aggregate_actions(mapped):
    """V2 summation, called only after strict identity validation by the wrapper."""
    return mapped.groupby(PLAYER_KEYS, as_index=False).agg(
        pressured_pass_attempts=("pressured_pass_attempts", "sum"),
        pressured_pass_completed=("pressured_pass_completed", "sum"),
        pressured_dribble_attempts=("pressured_dribble_attempts", "sum"),
        pressured_dribble_completed=("pressured_dribble_completed", "sum"),
    )


def add_completion_rates(counts):
    """Percent rates, never zero-fill unknown counts or synthesize player rows."""
    if not counts.columns.is_unique or any(c not in counts for c in COUNT_COLS):
        raise PressResistanceError("counts: unique columns and all four action counts required")
    if any(c in counts for c in DERIVED_COLS):
        raise PressResistanceError("counts: reserved derived output column collision")
    for c in COUNT_COLS:
        values = counts[c]
        if not is_numeric_dtype(values) or is_bool_dtype(values) or np.iscomplexobj(values):
            raise PressResistanceError("counts: finite nonnegative integers required")
        numeric = values.astype(float)
        if (~np.isfinite(numeric) | numeric.lt(0) | numeric.ne(np.floor(numeric))).any():
            raise PressResistanceError("counts: finite nonnegative integers required")
    for kind in ["pass", "dribble"]:
        if (counts[f"pressured_{kind}_completed"] > counts[f"pressured_{kind}_attempts"]).any():
            raise PressResistanceError("completed count exceeds attempt count")
    result = counts.copy()
    result["pressured_actions"] = result.pressured_pass_attempts + result.pressured_dribble_attempts
    result["successful_pressured_actions"] = (
        result.pressured_pass_completed + result.pressured_dribble_completed
    )
    for kind in ["pass", "dribble"]:
        denominator = result[f"pressured_{kind}_attempts"]
        result[f"pressured_{kind}_completion_rate"] = (
            100 * result[f"pressured_{kind}_completed"] / denominator.where(denominator.gt(0))
        )
    result["press_resistance_rate"] = (
        100 * result["successful_pressured_actions"]
        / result["pressured_actions"].where(result["pressured_actions"].gt(0))
    )
    return result
