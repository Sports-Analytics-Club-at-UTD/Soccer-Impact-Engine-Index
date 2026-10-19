"""STEP 3 - how much recovery data does each position actually have?

Run from the repo root:
    python -W ignore src/scripts/check_position_samples.py

Reads data/raw/statsbomb_team_events.parquet, applies the Recovery Coverage rules
(src/metrics/recovery_coverage.py) and summarises by the RAW StatsBomb `position` label
(position at the moment of the event). It does NOT group positions into "centre-backs",
"midfielders" etc. - that mapping belongs to the position module/teammate. Use this output to
see which raw labels exist and how thin the samples are.

No thresholds are applied. Spread is shown as quartiles so you can judge for yourself.
"""
import sys
from pathlib import Path    

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.metrics.recovery_coverage import extract_recovery_events  # noqa: E402

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"


def position_summary(rec):
    """Return (events_by_position, player_spread).

    events_by_position : rows = position, columns = event type, plus Total and share of all events
    player_spread      : per position, how many player-seasons and how many events each has
                         (min / quartiles / max of events per player-season)
    """
    rec = rec.copy()
    rec["position"] = rec["position"].fillna("(missing)")

    by_pos = rec.pivot_table(index="position", columns="event_type", values="match_id",
                             aggfunc="size", fill_value=0)
    by_pos["Total"] = by_pos.sum(axis=1)
    by_pos["share_of_all"] = (by_pos["Total"] / by_pos["Total"].sum()).round(4)
    by_pos = by_pos.sort_values("Total", ascending=False)

    per_player = (rec.groupby(["position", "player", "team", "competition_name", "season_name"])
                  .size().rename("events").reset_index())
    spread = per_player.groupby("position")["events"].describe(percentiles=[0.25, 0.5, 0.75])
    spread = spread.rename(columns={"count": "player_seasons"})[
        ["player_seasons", "min", "25%", "50%", "75%", "max"]]
    spread = spread.loc[by_pos.index]
    return by_pos, spread


def main():
    ev = pd.read_parquet(RAW / "statsbomb_team_events.parquet")
    rec = extract_recovery_events(ev)
    if "position" not in rec.columns:
        raise SystemExit("No 'position' column in the events file.")

    by_pos, spread = position_summary(rec)
    pd.set_option("display.width", 200)
    print("=== COUNTED EVENTS BY RAW POSITION (event types kept separate) ===")
    print(by_pos.to_string())
    print("\n=== SAMPLE SPREAD: events per player-season, by position ===")
    print("(player_seasons = number of player-season rows; min/25%/50%/75%/max = events each)")
    print(spread.round(1).to_string())
    print(f"\nTotal counted events: {int(by_pos['Total'].sum())}")
    print("Events with missing position:", int(by_pos.loc["(missing)", "Total"]) if "(missing)" in by_pos.index else 0)


if __name__ == "__main__":
    main()