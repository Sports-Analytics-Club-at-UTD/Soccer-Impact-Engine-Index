"""Strict pressured-action integration with separate non-metric diagnostics.

Uses explicit M2A identity and Pratyush V2 action definitions. No scoring policy
or file I/O. See docs/m3a-press-resistance.md for contracts and limitations.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from src.identity import IdentityResult, PLAYER_KEYS, resolve_events, validate_population
from src.metrics.press_actions import (
    COUNT_COLS, PressResistanceError, add_completion_rates, aggregate_actions, classify_actions,
)


@dataclass
class PressDiagnostic:
    inspected_events: int
    identity: IdentityResult
    accounting: pd.DataFrame


@dataclass
class PressResult:
    identity: IdentityResult
    accounting: pd.DataFrame
    totals: pd.DataFrame


def _select(events):
    if not events.columns.is_unique:
        raise PressResistanceError("events: duplicate column labels")
    missing = [c for c in ["id", "player", "team", "competition_name", "season_name"] if c not in events]
    if missing:
        raise PressResistanceError(f"events: missing identity columns {missing}")
    if not all(isinstance(v, str) and v.strip() for v in events.id):
        raise PressResistanceError("events: missing/invalid event IDs")
    if events.id.duplicated().any():
        raise PressResistanceError("events: duplicate event IDs, including excluded actions")
    return classify_actions(events)


def _accounting(actions, resolved):
    if actions.id.tolist() != resolved.id.tolist() or actions.type.tolist() != resolved.type.tolist():
        raise PressResistanceError("identity resolution changed action IDs, types or order")
    if not actions[COUNT_COLS].equals(resolved[COUNT_COLS]):
        raise PressResistanceError("identity resolution changed action counts")
    attempts = resolved.pressured_pass_attempts + resolved.pressured_dribble_attempts
    if not attempts.eq(1).all():
        raise PressResistanceError("every pressured event must contribute exactly one attempt")
    for kind in ["pass", "dribble"]:
        if not resolved[f"pressured_{kind}_completed"].le(resolved[f"pressured_{kind}_attempts"]).all():
            raise PressResistanceError("completed count exceeds attempt count")
    rows = []
    for kind in ["Pass", "Dribble"]:
        sub = resolved.loc[resolved.type.eq(kind)]
        completed = f"pressured_{kind.lower()}_completed"
        row = dict(type=kind, filtered=int(actions.type.eq(kind).sum()),
                   completed=int(actions.loc[actions.type.eq(kind), completed].sum()))
        for status in ["selected", "outside_population", "unresolved"]:
            group = sub.loc[sub.identity_status.eq(status)]
            row[status] = len(group)
            row[f"{status}_completed"] = int(group[completed].sum())
        if (row["filtered"] != sum(row[s] for s in ["selected", "outside_population", "unresolved"])
                or row["completed"] != sum(row[f"{s}_completed"] for s in
                                           ["selected", "outside_population", "unresolved"])):
            raise PressResistanceError("identity attempt/completion conservation failed")
        rows.append(row)
    return pd.DataFrame(rows)


def inspect_press_resistance(events, crosswalk, population):
    """Retain unresolved actions and accounting, without partial player metrics."""
    actions = _select(events)
    identity = resolve_events(actions, crosswalk, population, strict=False)
    return PressDiagnostic(len(events), identity, _accounting(actions, identity.events))


def _attach_minutes(totals, minutes):
    exposure = validate_population(minutes).reset_index(drop=True)
    if "minutes" not in minutes:
        raise PressResistanceError("minutes: missing minutes column")
    values = minutes.minutes.reset_index(drop=True)
    if not is_numeric_dtype(values) or is_bool_dtype(values) or np.iscomplexobj(values):
        raise PressResistanceError("minutes: numeric nonnegative exposure required")
    numeric = values.astype(float)
    if (numeric.notna() & (~np.isfinite(numeric) | numeric.lt(0))).any():
        raise PressResistanceError("minutes: finite nonnegative exposure required when known")
    exposure["minutes"] = numeric
    out = totals.merge(exposure, on=PLAYER_KEYS, how="left", validate="one_to_one", sort=False)
    if len(out) != len(totals) or not out[COUNT_COLS].equals(totals[COUNT_COLS].reset_index(drop=True)):
        raise PressResistanceError("minutes join lost or multiplied action counts")
    return out


def integrate_press_resistance(events, crosswalk, population, *, minutes=None):
    """Strict identity -> observed selected player counts/rates; optional minutes only.

    No population expansion, unknown-to-zero conversion, ranking or qualification.
    Existing event player IDs follow unchanged M2A conflict/missing-ID rules.
    """
    actions = _select(events)
    identity = resolve_events(actions, crosswalk, population)
    accounting = _accounting(actions, identity.events)
    selected = identity.selected_events()
    totals = aggregate_actions(selected)
    if totals.duplicated(PLAYER_KEYS).any():
        raise PressResistanceError("stable-ID grouping produced duplicate contexts")
    for c in COUNT_COLS:
        if int(totals[c].sum()) != int(selected[c].sum()):
            raise PressResistanceError("stable-ID grouping lost or multiplied action counts")
    out = add_completion_rates(totals)
    if int(out.pressured_actions.sum()) != len(selected):
        raise PressResistanceError("selected attempts do not equal selected event count")
    if minutes is not None:
        out = _attach_minutes(out, minutes)
    return PressResult(identity, accounting, out)
