"""
Fetch a small RAW lookup for the 360 matches: id, match_id, type, team, possession_team
for EVERY event (not just the six types in statsbomb_team_events.parquet).

Why this exists
---------------
Off-Ball Spatial Dominance (Person 4) needs to know, for each 360 freeze frame, which team
had possession at that event. 360 frames exist for all event types (shots, ball receipts,
pressures, ...), but statsbomb_team_events.parquet keeps only Pass/Carry/Dribble/Duel/
Ball Recovery/Interception and has no possession_team column. Without this lookup most
frames cannot be matched to an event and would be skipped.

Input : data/raw/statsbomb_360_frames.parquet  (only its match_id column is read)
Output: data/raw/statsbomb_360_event_meta.parquet  (small; share via Drive, not git)

Raw only - no filtering, no derived values.
"""

import time
from pathlib import Path

import pandas as pd
from statsbombpy import sb

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
FRAMES_PATH = RAW / "statsbomb_360_frames.parquet"
OUT_PATH = RAW / "statsbomb_360_event_meta.parquet"
KEEP = ["id", "type", "team", "possession_team"]


def main():
    match_ids = pd.read_parquet(FRAMES_PATH, columns=["match_id"])["match_id"].unique()
    print(f"{len(match_ids)} matches with 360 frames")

    parts, skipped = [], []
    for mid in match_ids:
        ev = None
        for attempt in range(1, 4):  # retry: connection resets happen on long pulls
            try:
                ev = sb.events(match_id=int(mid))
                break
            except Exception as e:
                print(f"  [retry {attempt}/3] match {mid}: {e}")
                time.sleep(2 * attempt)
        if ev is None:
            print(f"  [SKIP] match {mid}: failed after 3 attempts")
            skipped.append(mid)
            continue
        missing = [c for c in KEEP if c not in ev.columns]
        if missing:
            raise RuntimeError(f"match {mid}: events missing columns {missing}")
        sub = ev[KEEP].copy()
        sub["match_id"] = mid
        parts.append(sub)
        time.sleep(0.05)

    if not parts:
        raise RuntimeError("No events collected.")

    meta = pd.concat(parts, ignore_index=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    meta.to_parquet(OUT_PATH, index=False)
    print(f"\nSaved {len(meta)} events for {meta['match_id'].nunique()} matches to {OUT_PATH}")
    if skipped:
        print(f"WARNING: {len(skipped)} matches skipped, re-run to retry them: {skipped}")


if __name__ == "__main__":
    main()