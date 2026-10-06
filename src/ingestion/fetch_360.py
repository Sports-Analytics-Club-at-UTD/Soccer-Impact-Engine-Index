"""
Fetch StatsBomb 360 data for Off-Ball Spatial Dominance.

360 data is ONLY free for these specific season-slots — nowhere else:
  - 1. Bundesliga, 2023/2024
  - La Liga, 2020/2021
  - Ligue 1, 2021/2022  OR  2022/2023

There is NO free 360 data for Premier League or Serie A, in any season.
This is a hard limitation of the open dataset, not a filtering choice —
if your team wants Spatial Dominance for those two leagues, output N/A
for them per project rules. Do not substitute tackles/interceptions/any
other event type as a stand-in for missing 360 data.

This pulls 360 frames only, matched to their corresponding match_id.
It does NOT merge in the regular event data — join by match_id locally
if you need both together (e.g. to know which events occurred during
a given 360 frame's window).
"""

import pandas as pd
from statsbombpy import sb
import time
from pathlib import Path

# Confirmed free 360-data season-slots only. Do not add other seasons here
# without verifying via sb.competitions() + checking the match actually has
# 360 data (not every match in a "360-enabled" season necessarily has it).
SIX_THREE_SIXTY_SLOTS = [
    {"competition_name": "1. Bundesliga", "season_name": "2023/2024"},
    {"competition_name": "La Liga", "season_name": "2020/2021"},
    {"competition_name": "Ligue 1", "season_name": "2021/2022"},
    {"competition_name": "Ligue 1", "season_name": "2022/2023"},
]


def get_slot_competitions():
    comps = sb.competitions()
    rows = []
    for slot in SIX_THREE_SIXTY_SLOTS:
        match = comps[
            (comps["competition_name"] == slot["competition_name"]) &
            (comps["season_name"] == slot["season_name"])
        ]
        if match.empty:
            print(f"  [WARNING] {slot['competition_name']} {slot['season_name']} "
                  f"not found in current competitions list — skipping, do not assume it exists.")
            continue
        rows.append(match.iloc[0])
    if not rows:
        raise RuntimeError("None of the expected 360 season-slots were found. "
                            "Check sb.competitions() output manually before proceeding.")
    return pd.DataFrame(rows)


def fetch_all_360():
    all_frames = []
    comps = get_slot_competitions()

    for _, comp_row in comps.iterrows():
        comp_id = comp_row["competition_id"]
        season_id = comp_row["season_id"]
        comp_name = comp_row["competition_name"]
        season_name = comp_row["season_name"]

        matches = sb.matches(competition_id=comp_id, season_id=season_id)
        print(f"{comp_name} {season_name}: {len(matches)} matches — checking for 360 data")

        matches_with_360 = 0
        for match_id in matches["match_id"]:
            try:
                frames = sb.frames(match_id=match_id, fmt="dataframe")
            except Exception as e:
                # Not every match in a 360-enabled season necessarily has 360 data.
                # Skip silently-but-counted rather than assuming or erroring out.
                continue

            if frames is None or frames.empty:
                continue

            frames = frames.copy()
            frames["match_id"] = match_id
            frames["competition_name"] = comp_name
            frames["season_name"] = season_name
            all_frames.append(frames)
            matches_with_360 += 1

            time.sleep(0.05)

        print(f"  -> {matches_with_360} of {len(matches)} matches had 360 data")

    if not all_frames:
        raise RuntimeError("No 360 frames collected — check statsbombpy version supports sb.frames().")

    return pd.concat(all_frames, ignore_index=True)


if __name__ == "__main__":
    df = fetch_all_360()

    out_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "statsbomb_360_frames.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"\nSaved {len(df)} 360 frame-rows to {out_path}")
    print(f"Slots covered: {df[['competition_name', 'season_name']].drop_duplicates().values.tolist()}")
    print("\nReminder: Premier League and Serie A have NO free 360 data in any season. "
          "Spatial Dominance output for those leagues should be marked N/A, not estimated.")