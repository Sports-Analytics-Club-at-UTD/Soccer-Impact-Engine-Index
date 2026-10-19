"""
Fetch StatsBomb Open Data for the 5 target leagues and save as one shared parquet file.

Covers RAW events for the whole team's metrics:
  - Interception, Ball Recovery, Tackle      -> Defensive Recovery Coverage (Person 4)
  - Pass                                     -> Progressive Line-Breaking Pass Value (teammate)
  - Pass, Carry, Dribble + under_pressure    -> Press Resistance (teammate)

Does NOT pull 360 data — that's a separate, narrower script for the 3 season-slots
that have free 360 data (Bundesliga 2023/24, La Liga 2020/21, Ligue 1 2021/22 or 2022/23),
needed only for Off-Ball Spatial Dominance (Person 4).

This script pulls RAW events only. It does NOT pre-compute anyone's derived metric
(e.g. it does not filter tackles down to "won" only, or compute pass progressiveness) —
that logic belongs to whoever owns each metric, applied locally after reading this file.
Keeping the shared file raw avoids baking one person's assumptions into everyone's data.

Run once, share the output file (statsbomb_team_events.parquet) via Drive.
Do not re-run this per teammate — one pull, one shared file.
"""

import pandas as pd
from statsbombpy import sb
import time
from pathlib import Path

TARGET_LEAGUES = [
    "La Liga",
    "Premier League",
    "Serie A",
    "1. Bundesliga",  # StatsBomb's exact naming, not just "Bundesliga"
    "Ligue 1",
]

# Keep any season starting in this year or later (last 10 years from today).
# NOTE: StatsBomb's only PL/Serie A season in this range (2015/2016) starts in
# 2015, so a cutoff of 2016 silently excludes it. Set to 2015 if you want it included —
# otherwise PL and Serie A will have ZERO rows in the output, which is what happened
# on the first run at cutoff=2016.
MIN_SEASON_START_YEAR = 2015

# Add an event type here ONLY after checking with whoever needs it — confirm the
# event type name matches StatsBomb's exact taxonomy (case-sensitive) via sb.events()
# on a sample match before trusting a filter on it.
#
# IMPORTANT: StatsBomb's top-level type for tackles is "Duel", NOT "Tackle".
# "Tackle" only appears as a VALUE inside the duel_type column (alongside "Aerial",
# etc.) on Duel-type rows. Filtering on type == "Tackle" silently returns zero rows —
# this was confirmed against real pulled data on 2026-09-28.
RELEVANT_EVENT_TYPES = [
    "Interception",
    "Ball Recovery",
    "Duel",
    "Pass",
    "Carry",
    "Dribble",
]

# Columns we actually need — trim the raw StatsBomb schema down, but keep enough
# for every teammate's known metric. under_pressure applies to ALL event types,
# not just certain ones, so it's kept unconditionally below.
KEEP_COLUMNS = [
    "id", "match_id", "type", "minute", "second", "period",
    "team", "player", "position",
    "location",
    "under_pressure",  # applies across all event types — Press Resistance needs this

    # Defensive Recovery Coverage fields (Person 4)
    "duel_type", "duel_outcome",           # isolates won vs lost tackles
    "interception_outcome",
    "ball_recovery_recovery_failure",      # flags failed recoveries

    # Pass fields (Progressjive Line-Breaking Pass Value)
    "pass_end_location", "pass_length", "pass_height",
    "pass_outcome", "pass_body_part", "pass_type",

    # Carry fields (Press Resistance)
    "carry_end_location",

    # Dribble fields (Press Resistance)
    "dribble_outcome",
]


def get_target_competitions():
    """Pull live competition list, filter to our 5 leagues AND seasons starting
    within the last 10 years. Never hardcode season names/IDs."""
    comps = sb.competitions()
    target = comps[comps["competition_name"].isin(TARGET_LEAGUES)].copy()
    if target.empty:
        raise RuntimeError("No matching competitions found — check league names against sb.competitions() output.")

    # season_name looks like "2015/2016" — take the first 4 chars as the start year.
    target["season_start_year"] = target["season_name"].str[:4].astype(int)
    target = target[target["season_start_year"] >= MIN_SEASON_START_YEAR]

    if target.empty:
        raise RuntimeError(f"No seasons found starting {MIN_SEASON_START_YEAR} or later.")

    return target


def fetch_all_events():
    all_events = []
    comps = get_target_competitions()

    print(f"Found {len(comps)} competition/season combos across target leagues.")

    for _, comp_row in comps.iterrows():
        comp_id = comp_row["competition_id"]
        season_id = comp_row["season_id"]
        comp_name = comp_row["competition_name"]
        season_name = comp_row["season_name"]

        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as e:
            print(f"  [SKIP] {comp_name} {season_name}: could not load matches ({e})")
            continue

        print(f"  {comp_name} {season_name}: {len(matches)} matches")

        for match_id in matches["match_id"]:
            try:
                events = sb.events(match_id=match_id)
            except Exception as e:
                print(f"    [SKIP] match {match_id}: {e}")
                continue

            relevant = events[events["type"].isin(RELEVANT_EVENT_TYPES)].copy()
            if relevant.empty:
                continue

            relevant["competition_name"] = comp_name
            relevant["season_name"] = season_name
            relevant["match_id"] = match_id

            # Keep only columns that actually exist in this slice (schema varies by event type)
            cols_present = [c for c in KEEP_COLUMNS if c in relevant.columns]
            all_events.append(relevant[cols_present + ["competition_name", "season_name"]])

            time.sleep(0.05)  # be polite to the open-data host, avoid hammering requests

    if not all_events:
        raise RuntimeError("No events collected — something went wrong upstream.")

    return pd.concat(all_events, ignore_index=True)


if __name__ == "__main__":
    df = fetch_all_events()

    # NOTE: this file stays RAW — no filtering down to "won tackles only" or any
    # other person's derived logic. Each metric owner applies their own filtering
    # after loading this file. Example (Person 4, Recovery Coverage) — remember
    # tackles live inside type == "Duel" with duel_type == "Tackle", not their own
    # top-level type:
    #
    #   won_tackles = df[(df["type"] == "Duel") &
    #                     (df["duel_type"] == "Tackle") &
    #                     (df["duel_outcome"].astype(str).str.contains("Won|Success", na=False))]
    #
    # Check the actual distinct values in duel_outcome yourself (df["duel_outcome"].unique())
    # before trusting "Won|Success" as the full list of winning outcomes — StatsBomb may use
    # a value you haven't seen yet, and guessing at it would violate the no-invented-data rule.
    #
    # If duel_outcome / pass_outcome / etc. is missing for some rows, don't assume
    # a default outcome — mark that metric N/A for those rows per project rules.

    out_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "statsbomb_team_events.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"\nSaved {len(df)} events to {out_path}")
    print(f"Event types included: {df['type'].unique().tolist()}")
    print(f"Leagues covered: {df['competition_name'].unique().tolist()}")