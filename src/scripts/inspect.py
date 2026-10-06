"""STEP 0 - run this before trusting any metric code.

It checks the two parquet files against what recovery_coverage.py and
spatial_dominance.py assume, and prints the facts we still have to confirm
(outcome label values, 360 coordinate orientation, 360 coverage per league/season).

Usage:
    python inspect_data.py --events statsbomb_team_events.parquet --frames statsbomb_360_frames.parquet
"""
import argparse

import numpy as np
import pandas as pd

EVENT_COLS_NEEDED = [
    "id", "match_id", "type", "team", "possession_team", "player", "player_id",
    "location", "duel_type", "duel_outcome", "interception_outcome",
    "ball_recovery_recovery_failure",
]
EVENT_COLS_NICE_TO_HAVE = ["position", "minute", "period", "competition_name", "season_name"]
FRAME_COLS_NEEDED = ["id", "match_id", "visible_area", "teammate", "actor", "keeper", "location"]


def check_columns(df, needed, label):
    missing = [c for c in needed if c not in df.columns]
    print(f"[{label}] missing required columns: {missing if missing else 'none'}")
    return missing


def main(events_path, frames_path):
    ev = pd.read_parquet(events_path)
    fr = pd.read_parquet(frames_path)

    print("=== SHAPES ===")
    print("events:", ev.shape, "| matches:", ev["match_id"].nunique() if "match_id" in ev else "?")
    print("frames:", fr.shape, "| matches:", fr["match_id"].nunique() if "match_id" in fr else "?")

    print("\n=== COLUMN CHECKS ===")
    check_columns(ev, EVENT_COLS_NEEDED, "events needed")
    check_columns(ev, EVENT_COLS_NICE_TO_HAVE, "events nice-to-have")
    check_columns(fr, FRAME_COLS_NEEDED, "frames needed")
    print("\nevents columns:", list(ev.columns))
    print("frames columns:", list(fr.columns))

    print("\n=== EVENT TYPES ===")
    if "type" in ev:
        print(ev["type"].value_counts().to_string())

    print("\n=== OUTCOME LABELS (confirm which count as 'won' / successful) ===")
    for col in ["duel_type", "duel_outcome", "interception_outcome", "ball_recovery_recovery_failure"]:
        if col in ev:
            print(f"\n{col}:")
            print(ev[col].value_counts(dropna=False).to_string())
    if {"type", "duel_type", "duel_outcome"} <= set(ev.columns):
        tk = ev[(ev["type"] == "Duel") & (ev["duel_type"] == "Tackle")]
        print("\nTackle duels by outcome:")
        print(tk["duel_outcome"].value_counts(dropna=False).to_string())

    print("\n=== 360 COVERAGE (events matches vs matches that have frames) ===")
    if "match_id" in ev:
        has360 = set(fr["match_id"].unique())
        tmp = ev[["match_id"]].drop_duplicates().copy()
        for c in ["competition_name", "season_name"]:
            if c in ev:
                tmp = tmp.merge(ev[["match_id", c]].drop_duplicates("match_id"), on="match_id")
        tmp["has_360"] = tmp["match_id"].isin(has360)
        keys = [c for c in ["competition_name", "season_name"] if c in tmp]
        if keys:
            cov = tmp.groupby(keys).agg(n_matches=("match_id", "nunique"), n_with_360=("has_360", "sum"))
            cov["status"] = np.where(cov["n_with_360"] == 0, "N/A (no 360 data)", "partial sample")
            print(cov.to_string())
        else:
            print("No competition/season columns in events; overall:",
                  int(tmp["has_360"].sum()), "of", len(tmp), "matches have 360 frames")

    print("\n=== 360 ORIENTATION CHECK ===")
    print("Mean x of goalkeepers in frames, split by 'teammate' (teammate = same team as the event actor).")
    print("If 360 coordinates use the actor's perspective (as spatial_dominance.py assumes),")
    print("the teammate keeper should sit LOW x (own goal at 0) and the opposing keeper HIGH x.")
    if {"keeper", "teammate", "location"} <= set(fr.columns):
        k = fr[fr["keeper"] == True]  # noqa: E712
        xs = np.array([loc[0] if isinstance(loc, (list, tuple, np.ndarray)) and len(loc) >= 2 else np.nan
                       for loc in k["location"].to_numpy()])
        print(pd.Series(xs, index=k.index).groupby(k["teammate"]).agg(["mean", "count"]).to_string())
    print("\nIf this does NOT match, stop and fix the flip rule in spatial_dominance.py before running anything.")

    print("\n=== TYPES OF NESTED FIELDS (for parsing) ===")
    if "location" in fr:
        print("frames.location example:", repr(fr["location"].iloc[0]), type(fr["location"].iloc[0]))
    if "visible_area" in fr:
        print("frames.visible_area example type:", type(fr["visible_area"].iloc[0]),
              "| length:", len(fr["visible_area"].iloc[0]) if hasattr(fr["visible_area"].iloc[0], "__len__") else "n/a")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--events", default="statsbomb_team_events.parquet")
    p.add_argument("--frames", default="statsbomb_360_frames.parquet")
    a = p.parse_args()
    main(a.events, a.frames)