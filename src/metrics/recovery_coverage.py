"""Recovery dependency excerpt from origin/arpit-dev (0445f18fa1895320f0679ee84022888793fae6e7).

Original: src/metrics/recovery_coverage.py. Selected function bodies/constants are unchanged.
Only imports, this provenance header, and omission of unrelated CLI/helpers differ.
The integrated caller supplies stable player-ID grouping and validates joins.
"""
import numpy as np
import pandas as pd

from src.metrics.zones import assign_zone, split_location


EVENT_TYPES = ("Tackle", "Interception", "Ball Recovery")


SUCCESS_OUTCOMES = {"Won", "Success In Play", "Success Out"}


DEFAULT_GROUP = ("player", "team", "competition_name", "season_name")


REQUIRED_COLS = [
    "match_id", "type", "team", "player", "location",
    "duel_type", "duel_outcome", "interception_outcome", "ball_recovery_recovery_failure",
]


CARRY_COLS = [
    "id", "match_id", "competition_id", "season_id", "competition_name", "season_name",
    "team", "player_id", "player", "position", "minute", "period",
]


def _require(df, cols):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"events table is missing required columns: {missing}")


def extract_recovery_events(events, tackle_outcomes=SUCCESS_OUTCOMES,
                            interception_outcomes=SUCCESS_OUTCOMES):
    """Long table: one row per counted event, with event_type, x, y, zone."""
    _require(events, REQUIRED_COLS)
    t = events["type"]

    tackle = (
        (t == "Duel") & (events["duel_type"] == "Tackle")
        & events["duel_outcome"].isin(tackle_outcomes)
    )
    interception = (t == "Interception") & events["interception_outcome"].isin(interception_outcomes)
    failed = events["ball_recovery_recovery_failure"].eq(True)
    recovery = (t == "Ball Recovery") & ~failed

    keep = [c for c in CARRY_COLS if c in events.columns] + ["location"]
    parts = []
    for name, mask in [("Tackle", tackle), ("Interception", interception), ("Ball Recovery", recovery)]:
        sub = events.loc[mask, keep].copy()
        sub["event_type"] = name
        parts.append(sub)
    out = pd.concat(parts, ignore_index=True)

    x, y = split_location(out["location"])
    out["x"], out["y"] = x, y
    out["zone"] = assign_zone(x, y)
    return out.drop(columns="location")


def recovery_counts(rec, group_cols=DEFAULT_GROUP):
    """Return (totals, by_zone). Event types stay separate in both.

    totals  : every counted event, including those with no location
    by_zone : only events with a known zone (so zone counts can sum to < totals)
    """
    g = list(group_cols)
    totals = rec.groupby(g + ["event_type"], dropna=False).size().rename("count").reset_index()
    by_zone = (
        rec.dropna(subset=["zone"])
        .groupby(g + ["event_type", "zone"]).size().rename("count").reset_index()
    )
    return totals, by_zone


def add_per90(counts, minutes, on, min_minutes=None):
    """Attach minutes and compute per-90.

    minutes: DataFrame with the columns in `on` plus a 'minutes' column.
             (Comes from the minutes-played module - not derived here.)
    No minutes row -> per90 is NaN. min_minutes (optional) sets per90 to NaN below that
    threshold; the threshold itself is a team decision, so there is no default.
    """
    on = list(on)
    out = counts.merge(minutes[on + ["minutes"]], on=on, how="left")
    out["per90"] = out["count"].div(out["minutes"]).mul(90).where(out["minutes"] > 0)
    if min_minutes is not None:
        out.loc[out["minutes"] < min_minutes, "per90"] = np.nan
    return out
