"""Fetch StatsBomb open-data lineups for every match in the events file.

Why: the events file has no substitution information and no player_id, so we
cannot compute minutes played or assign position groups from it. StatsBomb's
lineups data lists every player in each match with the position(s) they played
and when they went on / off.

This script only FETCHES and FLATTENS (raw data). It does not compute minutes.
Minutes are a derived step done afterwards, once we have inspected real output.

Output: one row per player per position stint. A player who never played has a
single row with empty position fields (kept on purpose so we can see them;
drop them later).

Columns written:
    match_id, team, player_id, player_name, player_nickname, jersey_number,
    position_id, position, from_time, to_time, from_period, to_period,
    start_reason, end_reason

Usage (from the repo root, PowerShell):

    # 1) Test on ONE match first and look at the printed output
    python -W ignore -m src.ingestion.fetch_statsbomb_lineups --match-id 3895266

    # 2) Full run over every match in the events file
    python -W ignore -m src.ingestion.fetch_statsbomb_lineups

Requires: pip install statsbombpy pandas pyarrow
"""

import argparse
import time
from pathlib import Path

import pandas as pd
from statsbombpy import sb

# ---- Paths: ADJUST these two defaults to match where your parquet files live.
DEFAULT_EVENTS = "data/raw/statsbomb_team_events.parquet"
DEFAULT_OUT = "data/raw/statsbomb_lineups.parquet"
DEFAULT_FAILED = "data/raw/statsbomb_lineups_failed_matches.txt"

MAX_RETRIES = 3


def fetch_one_match(match_id: int) -> pd.DataFrame:
    """Return the flattened lineup rows for one match (all teams)."""
    lineups = sb.lineups(match_id=match_id)  # dict: team name -> DataFrame
    rows = []
    for team_name, df in lineups.items():
        for _, p in df.iterrows():
            base = {
                "match_id": match_id,
                "team": team_name,
                "player_id": p.get("player_id"),
                "player_name": p.get("player_name"),
                "player_nickname": p.get("player_nickname"),
                "jersey_number": p.get("jersey_number"),
            }
            positions = p.get("positions")
            if isinstance(positions, list) and len(positions) > 0:
                for pos in positions:
                    rows.append({
                        **base,
                        "position_id": pos.get("position_id"),
                        "position": pos.get("position"),
                        "from_time": pos.get("from"),
                        "to_time": pos.get("to"),
                        "from_period": pos.get("from_period"),
                        "to_period": pos.get("to_period"),
                        "start_reason": pos.get("start_reason"),
                        "end_reason": pos.get("end_reason"),
                    })
            else:
                # Player listed but no position stint (did not play).
                rows.append({
                    **base,
                    "position_id": None, "position": None,
                    "from_time": None, "to_time": None,
                    "from_period": None, "to_period": None,
                    "start_reason": None, "end_reason": None,
                })
    return pd.DataFrame(rows)


def fetch_with_retry(match_id: int):
    """Try a match up to MAX_RETRIES times. Return DataFrame or None."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fetch_one_match(match_id)
        except Exception as exc:  # network resets, etc.
            print(f"  match {match_id}: attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            time.sleep(2 * attempt)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--events", default=DEFAULT_EVENTS, help="events parquet (used for the list of match_ids)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--failed", default=DEFAULT_FAILED)
    ap.add_argument("--match-id", type=int, default=None, help="fetch ONE match and print it (test mode, nothing saved)")
    ap.add_argument("--sleep", type=float, default=0.2, help="seconds between matches")
    args = ap.parse_args()

    # ---- Test mode: one match, print, stop.
    if args.match_id is not None:
        df = fetch_with_retry(args.match_id)
        if df is None:
            print("Fetch failed. Check your internet connection and that statsbombpy is installed.")
            return
        pd.set_option("display.width", 200)
        pd.set_option("display.max_columns", 30)
        print(f"Rows: {len(df)}   Columns: {list(df.columns)}")
        print(df.head(25).to_string())
        print("\nSample of from_time / to_time values:")
        print(df[["position", "from_time", "to_time", "from_period", "to_period"]].dropna().head(10).to_string())
        return

    # ---- Full run.
    match_ids = (
        pd.read_parquet(args.events, columns=["match_id"])["match_id"]
        .dropna().astype(int).unique().tolist()
    )
    match_ids.sort()
    print(f"{len(match_ids)} matches to fetch from {args.events}")

    frames, failed = [], []
    for i, mid in enumerate(match_ids, start=1):
        df = fetch_with_retry(mid)
        if df is None:
            failed.append(mid)
        else:
            frames.append(df)
        if i % 50 == 0 or i == len(match_ids):
            print(f"  {i}/{len(match_ids)} done, {len(failed)} failed")
        time.sleep(args.sleep)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = pd.concat(frames, ignore_index=True)
    result.to_parquet(out_path, index=False)
    print(f"Saved {len(result):,} rows from {result['match_id'].nunique()} matches -> {out_path}")

    if failed:
        Path(args.failed).write_text("\n".join(str(m) for m in failed))
        print(f"{len(failed)} matches failed after {MAX_RETRIES} attempts; ids written to {args.failed}")
        print("Re-run later, or document them as skipped (like match 3879594 in the events fetch).")


if __name__ == "__main__":
    main()