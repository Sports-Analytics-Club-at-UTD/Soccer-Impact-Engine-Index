"""Press Resistance (owner: Joseph).

In plain words: when an opponent is closing a player down, how often does the player keep
the ball, and how often are they in that situation at all?

INPUT  (RAW)     data/raw/statsbomb_team_events.parquet
                 needs event types Pass, Dribble, Carry, Miscontrol, Dispossessed
                 (Miscontrol and Dispossessed must be added to fetch_normal.py; see main())
                 data/processed/player_minutes.parquet (from src.metrics.player_minutes)
OUTPUT (DERIVED) data/processed/press_resistance_per90.parquet, one row per in-scope player-season

STEP 1: classify each action as retained or lost
  Pass (open play), under_pressure, pass_outcome empty                      -> retained
  Pass (open play), under_pressure, outcome Incomplete / Out / Pass Offside -> lost
  Pass with outcome Unknown / Injury Clearance                              -> excluded
  Dribble Complete -> retained, Dribble Incomplete -> lost (a dribble always faces an opponent)
  Miscontrol under pressure                                                 -> lost
  Dispossessed (any; an opponent took the ball)                             -> lost   ASSUMPTION
  Carry: not in the rate. Carries have no outcome; a carry that ends in a loss is already
         recorded as the next event (Dispossessed / Miscontrol / failed pass).

STEP 2: output columns (never blended into one number)
  pr_retention_rate    retained / (retained + lost)         headline number
  pr_actions_p90       (retained + lost) per 90             how often the player is pressed
  pr_retained_p90      retained per 90
  pr_prog_carries_p90  carries under pressure moving the ball >= 10 yards forward, per 90

STEP 3: N/A rules and percentiles
  - fewer than MIN_PRESSURED_ACTIONS (ASSUMPTION, 50) -> retention rate N/A, per-90s still shown
  - goalkeepers: pass part only; dribble and carry columns N/A          ASSUMPTION
  - percentiles within league-season x position group, full-coverage seasons, >= min minutes

Run from the repo root:
    python -W ignore -m src.metrics.press_resistance
    python -W ignore -m src.metrics.press_resistance --min-minutes 900 --min-actions 50
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.metrics.scoring_common import (
    DEFAULT_MIN_MINUTES, EVENTS, KEYS, MINUTES, add_percentile, attach_counts, clean_keys,
    in_scope_base, is_open_play_pass, is_true, na_reason, per90, season_coverage,
)
from src.metrics.zones import split_location

OUT = "data/processed/press_resistance_per90.parquet"

PASS_LOST = {"Incomplete", "Out", "Pass Offside"}
PASS_EXCLUDED = {"Unknown", "Injury Clearance"}
LOSS_EVENT_TYPES = ["Miscontrol", "Dispossessed"]
MIN_PRESSURED_ACTIONS = 50       # ASSUMPTION, set during calibration
PROG_CARRY_MIN_FORWARD = 10.0    # yards, ASSUMPTION

REQUIRED_COLS = ["type", "team", "player", "competition_name", "season_name",
                 "under_pressure", "pass_outcome", "pass_type", "dribble_outcome",
                 "location", "carry_end_location"]
METRICS = ["pr_retention_rate", "pr_actions_p90", "pr_retained_p90", "pr_prog_carries_p90"]


def _require(df, cols):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"events table is missing required columns: {missing}")


def classify_pressured_actions(events):
    """Long table, one row per counted action: KEYS + action + retained (bool)."""
    _require(events, REQUIRED_COLS)
    t = events["type"]
    pressured = is_true(events["under_pressure"])
    outcome = events["pass_outcome"]

    pressured_pass = is_open_play_pass(events) & pressured & ~outcome.isin(PASS_EXCLUDED)
    pass_ok = pressured_pass & outcome.isna()
    pass_lost = pressured_pass & outcome.isin(PASS_LOST)
    dribble_ok = (t == "Dribble") & (events["dribble_outcome"] == "Complete")
    dribble_lost = (t == "Dribble") & (events["dribble_outcome"] == "Incomplete")
    miscontrol = (t == "Miscontrol") & pressured
    dispossessed = t == "Dispossessed"

    parts = []
    for action, mask, retained in [
        ("Pass", pass_ok, True), ("Pass", pass_lost, False),
        ("Dribble", dribble_ok, True), ("Dribble", dribble_lost, False),
        ("Miscontrol", miscontrol, False), ("Dispossessed", dispossessed, False),
    ]:
        sub = events.loc[mask, KEYS].copy()
        sub["action"] = action
        sub["retained"] = retained
        parts.append(sub)
    return pd.concat(parts, ignore_index=True)


def progressive_pressured_carries(events, min_forward=PROG_CARRY_MIN_FORWARD):
    """Carries under pressure that move the ball at least min_forward yards towards goal."""
    carries = events[(events["type"] == "Carry") & is_true(events["under_pressure"])]
    x0, _ = split_location(carries["location"])
    x1, _ = split_location(carries["carry_end_location"])
    forward = x1 - x0                      # NaN if either location is missing -> not counted
    return carries.loc[forward >= min_forward, KEYS].copy()


def pressure_counts(actions, prog_carries):
    """Per player-season counts: all actions, the pass-only part (for goalkeepers), carries."""
    a = actions.assign(
        retained_n=actions["retained"].astype(int),
        lost_n=(~actions["retained"]).astype(int),
        pass_retained_n=(actions["retained"] & (actions["action"] == "Pass")).astype(int),
        pass_lost_n=(~actions["retained"] & (actions["action"] == "Pass")).astype(int),
    )
    counts = a.groupby(KEYS)[["retained_n", "lost_n", "pass_retained_n", "pass_lost_n"]].sum()
    carries = prog_carries.groupby(KEYS).size().rename("prog_carries_n")
    counts = counts.join(carries, how="outer").fillna(0).astype(int).reset_index()
    return counts.rename(columns=lambda c: c[:-2] if c.endswith("_n") else c)


def build_table(counts, base, coverage, min_minutes=DEFAULT_MIN_MINUTES, min_actions=MIN_PRESSURED_ACTIONS):
    count_cols = ["retained", "lost", "pass_retained", "pass_lost", "prog_carries"]
    df = attach_counts(base, counts, count_cols)
    df = df.merge(coverage, on=["competition_name", "season_name"], how="left")

    gk = df["position_group"] == "GK"
    # Goalkeepers: only the pass part is reported.
    used_ret = np.where(gk, df["pass_retained"], df["retained"])
    used_lost = np.where(gk, df["pass_lost"], df["lost"])
    df["pr_actions"] = used_ret + used_lost
    df["pr_retained"] = used_ret

    enough = df["pr_actions"] >= min_actions
    df["pr_retention_rate"] = (df["pr_retained"] / df["pr_actions"].replace(0, np.nan)).where(enough)
    df["pr_actions_p90"] = per90(df["pr_actions"], df["minutes"])
    df["pr_retained_p90"] = per90(df["pr_retained"], df["minutes"])
    df["pr_prog_carries_p90"] = per90(df["prog_carries"], df["minutes"]).where(~gk)

    df["meets_min"] = df["minutes"] >= min_minutes
    eligible = df["full_coverage"].fillna(False).astype(bool) & df["meets_min"]
    for m in METRICS:
        add_percentile(df, m, eligible)

    df["na_reason"] = na_reason(df, min_minutes)
    df["rate_note"] = np.where(enough, "ok", f"N/A: fewer than {min_actions} pressured actions")
    df.loc[gk, "rate_note"] = np.where(enough[gk], "goalkeeper: passes only", df.loc[gk, "rate_note"])
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-minutes", type=float, default=DEFAULT_MIN_MINUTES, help="PROVISIONAL")
    ap.add_argument("--min-actions", type=int, default=MIN_PRESSURED_ACTIONS, help="ASSUMPTION")
    ap.add_argument("--allow-missing-loss-events", action="store_true",
                    help="run even if Miscontrol/Dispossessed are not in the events file "
                         "(retention rates will be too HIGH; for testing only)")
    args = ap.parse_args()

    cols = ["match_id", "id"] + REQUIRED_COLS
    events = pd.read_parquet(EVENTS)
    events = clean_keys(events[[c for c in cols if c in events.columns]])

    missing = [t for t in LOSS_EVENT_TYPES if t not in set(events["type"].unique())]
    if missing:
        msg = (f"The events file has no {missing} events. Add them to RELEVANT_EVENT_TYPES in "
               f"src/ingestion/fetch_normal.py and re-run the fetch. Without them every ball lost "
               f"while carrying is invisible and retention rates are biased upwards.")
        if not args.allow_missing_loss_events:
            raise SystemExit(msg)
        print(f"WARNING: {msg}")

    actions = classify_pressured_actions(events)
    carries = progressive_pressured_carries(events)
    print("Counted actions (retained / lost):")
    print(actions.groupby(["action", "retained"]).size().to_string())
    print(f"Progressive pressured carries: {len(carries):,}")

    counts = pressure_counts(actions, carries)
    base = in_scope_base(pd.read_parquet(MINUTES))
    cov = season_coverage(events)
    df = build_table(counts, base, cov, args.min_minutes, args.min_actions)

    out_cols = ["player_id", *KEYS, "position_group", "matches", "minutes", "retained", "lost",
                "pass_retained", "pass_lost", "prog_carries", "pr_actions", *METRICS,
                *[f"pctl_{m}" for m in METRICS], "meets_min", "full_coverage", "rate_note", "na_reason"]
    df = df[[c for c in out_cols if c in df.columns]].sort_values(KEYS)
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(f"\nSaved {len(df):,} rows -> {OUT}")

    # Calibration aids: how many players survive the action threshold, and the spread of the rate.
    ok = df[df["meets_min"]]
    print(f"\nPressured actions per player-season (>= {args.min_minutes:.0f} min), by group:")
    print(ok.groupby("position_group")["pr_actions"].describe(percentiles=[.1, .25, .5, .75, .9]).round(0).to_string())
    print("\nRetention rate by group:")
    print(ok.groupby("position_group")["pr_retention_rate"].describe().round(3).to_string())


if __name__ == "__main__":
    main()
