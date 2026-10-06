"""Defensive Recovery Coverage (no 360 needed).

INPUT   statsbomb_team_events.parquet (raw StatsBomb events)
RULES   Three event types, kept SEPARATE (never summed or blended):
          - Tackle        : type == "Duel" AND duel_type == "Tackle"  (tackles are NOT a top-level type)
          - Interception  : type == "Interception"
          - Ball Recovery : type == "Ball Recovery", excluding recoveries flagged as failed
        Only successful tackles / interceptions are counted (see SUCCESS_OUTCOMES).
CALC    1. Extract the three event types into one long table (one row per event).
        2. Tag each event with a pitch zone from its own location (zones.py).
        3. Count per player (or any grouping) x event type (x zone).
        4. per-90 = count / minutes * 90, ONLY when minutes are supplied.
RESULT  raw counts + per-90 rate per event type, plus zone breakdown.
        No possession adjustment in V1 (documented limitation).

RAW vs ASSUMPTION
  raw data   : type, duel_type, duel_outcome, interception_outcome, ball_recovery_recovery_failure, location
  assumption : SUCCESS_OUTCOMES below (which outcome labels mean "won"). Verify with inspect_data.py.
  derived    : zone, counts, per-90

N/A RULES
  - event with no location  -> still counted in totals, has zone <NA>, excluded from zone breakdown
  - player with no minutes  -> per90 = NaN (N/A). Minutes are never estimated from events.
"""
import numpy as np
import pandas as pd

from zones import assign_zone, split_location

EVENT_TYPES = ("Tackle", "Interception", "Ball Recovery")

# ASSUMPTION - confirm against the value counts printed by inspect_data.py.
SUCCESS_OUTCOMES = {"Won", "Success In Play", "Success Out"}

REQUIRED_COLS = [
    "match_id", "type", "team", "player_id", "player", "location",
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


def recovery_counts(rec, group_cols=("player_id", "player", "team")):
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


if __name__ == "__main__":
    ev = pd.read_parquet("statsbomb_team_events.parquet")
    rec = extract_recovery_events(ev)
    totals, by_zone = recovery_counts(rec)
    print(totals.groupby("event_type")["count"].sum())
    print(totals.sort_values("count", ascending=False).head(10))