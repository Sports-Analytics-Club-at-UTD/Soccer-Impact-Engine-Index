"""
Fetch a fresh StatsBomb match (fixture) list for the four full 2015/16 leagues and
compare it with the events and lineups files.

Input  (RAW):     StatsBomb open data, sb.competitions() and sb.matches()
Output (RAW):     data/raw/statsbomb_fixtures_2015_16.parquet (one row per match, with fetched_on date)
Also reads:       data/raw/statsbomb_team_events.parquet, data/raw/statsbomb_lineups.parquet
Changes nothing:  it does not modify the events file, lineups or any processed table.

This is a fresh fetch, not the list used for earlier checks, so it carries today's date.
A failed fetch stops the script (no silent skipping).

Run from the repo root (PowerShell):
    python -W ignore -m src.ingestion.fetch_fixtures
"""

from datetime import date
from pathlib import Path

import pandas as pd
from statsbombpy import sb

LEAGUES = ["La Liga", "Ligue 1", "Premier League", "Serie A"]
SEASON = "2015/2016"

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "data" / "raw" / "statsbomb_team_events.parquet"
LINEUPS = ROOT / "data" / "raw" / "statsbomb_lineups.parquet"
OUT = ROOT / "data" / "raw" / "statsbomb_fixtures_2015_16.parquet"


def find_competitions():
    comps = sb.competitions()
    pick = comps[comps["competition_name"].isin(LEAGUES) & (comps["season_name"] == SEASON)]
    print("Competitions found:")
    print(pick[["competition_id", "season_id", "competition_name", "season_name"]].to_string(index=False))
    if len(pick) != len(LEAGUES) or pick["competition_name"].nunique() != len(LEAGUES):
        raise SystemExit(f"Expected exactly {len(LEAGUES)} competitions (one per league), found {len(pick)}. Stopping.")
    return pick


def fetch_fixtures(pick):
    frames = []
    for _, row in pick.iterrows():
        m = sb.matches(competition_id=row["competition_id"], season_id=row["season_id"])
        m["competition_name"] = row["competition_name"]
        m["season_name"] = row["season_name"]
        print(f"  {row['competition_name']} {row['season_name']}: {len(m)} matches listed")
        frames.append(m)
    fix = pd.concat(frames, ignore_index=True)
    fix["fetched_on"] = date.today().isoformat()
    for col in fix.select_dtypes(include="object").columns:
        fix[col] = fix[col].map(lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else str(v))
    return fix


def compare(fix):
    ev = pd.read_parquet(EVENTS, columns=["match_id", "competition_name", "season_name"]).drop_duplicates()
    ev = ev[(ev["season_name"] == SEASON) & ev["competition_name"].isin(LEAGUES)]
    lineup_ids = set(int(x) for x in pd.read_parquet(LINEUPS, columns=["match_id"])["match_id"].unique())

    print("\nComparison (StatsBomb list vs files):")
    for name in LEAGUES:
        listed = set(int(x) for x in fix.loc[fix["competition_name"] == name, "match_id"])
        in_events = set(int(x) for x in ev.loc[ev["competition_name"] == name, "match_id"])
        print(f"\n{name} {SEASON}")
        print(f"  listed by StatsBomb:            {len(listed)}")
        print(f"  in events file:                 {len(in_events)}")
        print(f"  listed but NOT in events file:  {sorted(listed - in_events)}")
        print(f"  in events file but NOT listed:  {sorted(in_events - listed)}")
        print(f"  listed but NOT in lineups file: {sorted(listed - lineup_ids)}")


def main():
    pick = find_competitions()
    fix = fetch_fixtures(pick)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fix.to_parquet(OUT, index=False)
    print(f"\nSaved {len(fix):,} matches -> {OUT}")
    compare(fix)


if __name__ == "__main__":
    main()