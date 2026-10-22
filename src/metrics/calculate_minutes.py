
import json
import time
from pathlib import Path

import pandas as pd
import requests

# STEP 1: File paths
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "raw" / "statsbomb_team_events.parquet"

OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = OUTPUT_DIR / "player_minutes_2015_16.csv"
MATCH_OUTPUT = OUTPUT_DIR / "player_match_minutes_2015_16.csv"
FAILED_OUTPUT = OUTPUT_DIR / "failed_match_downloads.csv"

# STEP 2: Load match IDs
df = pd.read_parquet(
    DATA_PATH,
    columns=["match_id", "season_name"]
)

match_ids = (
    df.loc[df["season_name"] == "2015/2016", "match_id"]
    .dropna()
    .astype(int)
    .unique()
)

print(f"Found {len(match_ids)} matches.")

session = requests.Session()
session.headers.update({
    "User-Agent": "SoccerImpactEngine/1.0"
})

records = []
failed_matches = []


def download_events(match_id):
    url = (
        "https://raw.githubusercontent.com/"
        "statsbomb/open-data/master/data/events/"
        f"{match_id}.json"
    )

    for attempt in range(3):
        try:
            response = session.get(url, timeout=30)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except (requests.RequestException, ValueError):
            if attempt == 2:
                return None
            time.sleep(2 * (attempt + 1))

    return None


def event_seconds(event):
    minute = event.get("minute", 0)
    second = event.get("second", 0)
    return float(minute) * 60 + float(second)


def calculate_match_minutes(events, match_id):
    """
    Calculate player appearances using Starting XI,
    Substitution, and match-period information.

    Stoppage time is included.
    """

    if not events:
        raise ValueError("Empty event file")

    starters = [
        e for e in events
        if e.get("type", {}).get("name") == "Starting XI"
    ]

    if len(starters) != 2:
        raise ValueError(
            f"Expected 2 Starting XI records, got {len(starters)}"
        )

    # Match duration from the final event timestamp.
    # For ordinary regulation matches, this includes
    # recorded stoppage time.
    match_end = max(event_seconds(e) for e in events)

    appearances = {}

    for lineup_event in starters:
        team = lineup_event["team"]["name"]

        for entry in lineup_event.get("tactics", {}).get("lineup", []):
            player = entry["player"]["name"]
            key = (team, player)

            appearances[key] = {
                "match_id": match_id,
                "team": team,
                "player": player,
                "start_seconds": 0.0,
                "end_seconds": match_end
            }

    substitutions = sorted(
        [
            e for e in events
            if e.get("type", {}).get("name") == "Substitution"
        ],
        key=event_seconds
    )

    for event in substitutions:
        team = event["team"]["name"]
        outgoing = event["player"]["name"]
        incoming = event["substitution"]["replacement"]["name"]

        substitution_time = event_seconds(event)

        outgoing_key = (team, outgoing)
        incoming_key = (team, incoming)

        if outgoing_key not in appearances:
            raise ValueError(
                f"Outgoing player not found: {outgoing}"
            )

        appearances[outgoing_key]["end_seconds"] = substitution_time

        if incoming_key in appearances:
            raise ValueError(
                f"Duplicate appearance: {incoming}"
            )

        appearances[incoming_key] = {
            "match_id": match_id,
            "team": team,
            "player": incoming,
            "start_seconds": substitution_time,
            "end_seconds": match_end
        }

    result = []

    for appearance in appearances.values():
        minutes = (
            appearance["end_seconds"]
            - appearance["start_seconds"]
        ) / 60

        if minutes < 0:
            raise ValueError("Negative minutes calculated")

        result.append({
            "match_id": appearance["match_id"],
            "team": appearance["team"],
            "player": appearance["player"],
            "minutes_played": round(minutes, 2)
        })

    return result


# STEP 3: Process matches
for index, match_id in enumerate(match_ids, start=1):

    events = download_events(match_id)

    if events is None:
        failed_matches.append({
            "match_id": match_id,
            "reason": "Download failed or file unavailable"
        })
        print(f"[{index}/{len(match_ids)}] Failed: {match_id}")
        continue

    try:
        match_records = calculate_match_minutes(
            events, match_id
        )

        records.extend(match_records)

        print(
            f"[{index}/{len(match_ids)}] "
            f"Processed {match_id}"
        )

    except (ValueError, KeyError, TypeError) as error:
        failed_matches.append({
            "match_id": match_id,
            "reason": str(error)
        })
        print(f"[{index}/{len(match_ids)}] Error: {error}")

    # Avoid sending too many requests at once
    time.sleep(0.1)


# STEP 4: Save match-level minutes
if not records:
    raise RuntimeError("No valid player minutes calculated.")

match_minutes = pd.DataFrame(records)

match_minutes.to_csv(
    MATCH_OUTPUT,
    index=False
)

# STEP 5: Aggregate seasonal minutes
season_minutes = (
    match_minutes.groupby(
        ["player", "team"],
        as_index=False
    )
    .agg(
        minutes_played=("minutes_played", "sum"),
        matches_played=("match_id", "nunique")
    )
)

season_minutes["minutes_played"] = (
    season_minutes["minutes_played"].round(2)
)

season_minutes = season_minutes.sort_values(
    "minutes_played",
    ascending=False
)

season_minutes.to_csv(
    OUTPUT_PATH,
    index=False
)

# STEP 6: Save failures
pd.DataFrame(
    failed_matches,
    columns=["match_id", "reason"]
).to_csv(FAILED_OUTPUT, index=False)

# STEP 7: Summary
print("\nPLAYING TIME CALCULATION COMPLETE")
print(f"Matches requested: {len(match_ids)}")
print(f"Matches processed: {len(match_ids) - len(failed_matches)}")
print(f"Failed matches: {len(failed_matches)}")
print(f"Player-team records: {len(season_minutes)}")

print("\nTOP 10 BY MINUTES PLAYED")
print(season_minutes.head(10).to_string(index=False))

print(f"\nSaved: {OUTPUT_PATH}")
print(f"Match-level data: {MATCH_OUTPUT}")
print(f"Failure report: {FAILED_OUTPUT}")

if failed_matches:
    print(
        "\nWARNING: Some matches failed. "
        "Do not finalize tiers until the failures are resolved."
    )
