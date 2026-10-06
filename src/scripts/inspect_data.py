"""STEP 0 - run this before trusting any metric code.

Checks the parquet files against what src/metrics/* assumes and prints the facts we still
have to confirm (outcome label values, 360 coordinate orientation, 360 coverage, how many
360 frames can be matched to an event).

Usage (from the repo root):
    python scripts/inspect_data.py
Optional: --events / --frames / --meta to point at other files.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

EVENT_COLS_NEEDED = [
    "id", "match_id", "type", "team", "player", "location",
    "duel_type", "duel_outcome", "interception_outcome", "ball_recovery_recovery_failure",
]
EVENT_COLS_NICE = ["position", "minute", "period", "competition_name", "season_name", "player_id"]
FRAME_COLS_NEEDED = ["id", "match_id", "visible_area", "teammate", "actor", "keeper", "location"]
META_COLS_NEEDED = ["id", "match_id", "team", "possession_team"]


def check_columns(df, needed, label):
    missing = [c for c in needed if c not in df.columns]
    print(f"[{label}] missing: {missing if missing else 'none'}")
    return missing


def main(events_path, frames_path, meta_path):
    ev = pd.read_parquet(events_path)
    fr = pd.read_parquet(frames_path)

    print("=== SHAPES ===")
    print("events:", ev.shape, "| matches:", ev["match_id"].nunique())
    print("frames:", fr.shape, "| matches:", fr["match_id"].nunique())

    print("\n=== COLUMN CHECKS ===")
    check_columns(ev, EVENT_COLS_NEEDED, "events needed")
    check_columns(ev, EVENT_COLS_NICE, "events nice-to-have (player_id is expected to be absent)")
    check_columns(fr, FRAME_COLS_NEEDED, "frames needed")
    print("events columns:", list(ev.columns))
    print("frames columns:", list(fr.columns))

    print("\n=== EVENT TYPES ===")
    print(ev["type"].value_counts().to_string())

    print("\n=== OUTCOME LABELS (confirm which count as 'won' / successful) ===")
    for col in ["duel_type", "duel_outcome", "interception_outcome", "ball_recovery_recovery_failure"]:
        if col in ev:
            print(f"\n{col}:")
            print(ev[col].value_counts(dropna=False).to_string())
    if {"type", "duel_type", "duel_outcome"} <= set(ev.columns):
        tk = ev[(ev["type"] == "Duel") & (ev["duel_type"] == "Tackle")]
        print("\nTackle duels by outcome (compare with SUCCESS_OUTCOMES in recovery_coverage.py):")
        print(tk["duel_outcome"].value_counts(dropna=False).to_string())
    if "interception_outcome" in ev:
        print("\nInterception outcomes:")
        print(ev[ev["type"] == "Interception"]["interception_outcome"].value_counts(dropna=False).to_string())

    print("\n=== 360 COVERAGE (matches in events vs matches with frames) ===")
    has360 = set(fr["match_id"].unique())
    tmp = ev[["match_id"] + [c for c in ["competition_name", "season_name"] if c in ev]].drop_duplicates("match_id")
    tmp = tmp.assign(has_360=tmp["match_id"].isin(has360))
    keys = [c for c in ["competition_name", "season_name"] if c in tmp]
    if keys:
        cov = tmp.groupby(keys).agg(n_matches=("match_id", "nunique"), n_with_360=("has_360", "sum"))
        cov["status"] = np.where(cov["n_with_360"] == 0, "N/A (no 360 data)", "partial sample")
        print(cov.to_string())

    print("\n=== CAN 360 FRAMES BE MATCHED TO EVENTS? ===")
    frame_ids = set(fr["id"].unique())
    in_shared = len(frame_ids & set(ev["id"].unique()))
    print(f"frame ids found in the shared events file: {in_shared} of {len(frame_ids)} "
          f"({100 * in_shared / len(frame_ids):.1f}%)  <- low is expected: that file keeps only 6 event types")
    if Path(meta_path).exists():
        meta = pd.read_parquet(meta_path)
        check_columns(meta, META_COLS_NEEDED, "event-meta needed")
        in_meta = len(frame_ids & set(meta["id"].unique()))
        print(f"frame ids found in the event-meta file:   {in_meta} of {len(frame_ids)} "
              f"({100 * in_meta / len(frame_ids):.1f}%)  <- should be ~100%")
        print("possession_team missing in meta:", int(meta["possession_team"].isna().sum()))
    else:
        print(f"event-meta file not found at {meta_path}")
        print("-> run src/ingestion/fetch_360_event_meta.py first (needed for Off-Ball Spatial Dominance).")

    print("\n=== 360 ORIENTATION CHECK ===")
    print("Mean x of goalkeepers by 'teammate' (teammate = same team as the event actor).")
    print("If 360 uses the actor's perspective (as spatial_dominance.py assumes), the teammate")
    print("keeper should sit at LOW x (own goal at 0) and the opposing keeper at HIGH x.")
    if {"keeper", "teammate", "location"} <= set(fr.columns):
        k = fr[fr["keeper"] == True]  # noqa: E712
        xs = np.array([loc[0] if isinstance(loc, (list, tuple, np.ndarray)) and len(loc) >= 2 else np.nan
                       for loc in k["location"].to_numpy()])
        print(pd.Series(xs, index=k.index).groupby(k["teammate"]).agg(["mean", "count"]).to_string())
    print("If this does NOT match, stop and fix the flip rule in spatial_dominance.py.")

    print("\n=== NESTED FIELD TYPES (for parsing) ===")
    print("frames.location example:", repr(fr["location"].iloc[0]))
    va = fr["visible_area"].iloc[0]
    print("frames.visible_area example type:", type(va), "| length:", len(va) if hasattr(va, "__len__") else "n/a")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--events", default=str(RAW / "statsbomb_team_events.parquet"))
    p.add_argument("--frames", default=str(RAW / "statsbomb_360_frames.parquet"))
    p.add_argument("--meta", default=str(RAW / "statsbomb_360_event_meta.parquet"))
    a = p.parse_args()
    main(a.events, a.frames, a.meta)