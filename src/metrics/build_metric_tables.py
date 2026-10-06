"""Build the refined metric tables the dashboard reads, and save them to data/processed/.

Run from the repo root:
    python -W ignore -m src.metrics.build_metric_tables              # both metrics
    python -W ignore -m src.metrics.build_metric_tables --only recovery
    python -W ignore -m src.metrics.build_metric_tables --only spatial   # slow (~10 min)

OUTPUT FILES (data/processed/)
  recovery_coverage_totals.parquet
      player, team, competition_name, season_name, event_type, count
      One row per player-season-event type. event_type is Tackle / Interception / Ball Recovery
      and is never blended. Includes events with no location.
      per90 is NOT here yet: it needs the minutes-played table from the minutes module
      (see add_per90 in recovery_coverage.py). Without minutes it would be N/A, never estimated.
  recovery_coverage_by_zone.parquet
      same columns + zone (1..9, see zones.py). Events with no usable location are excluded,
      so zone counts can sum to less than the totals.
  spatial_dominance_team_zone.parquet
      defending_team, zone, observed_cells, defender_cells, n_frames, n_matches,
      control_rate, reportable
      control_rate is NaN (N/A) and reportable is False when n_matches < MIN_MATCHES.
      Those rows are kept (not dropped) so the dashboard can show "N/A".
"""
import argparse
from pathlib import Path

import pandas as pd

from src.metrics.recovery_coverage import extract_recovery_events, recovery_counts
from src.metrics.spatial_dominance import MIN_MATCHES, observed_spatial_dominance, team_control

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"


def build_recovery(raw=RAW, out=OUT):
    ev = pd.read_parquet(raw / "statsbomb_team_events.parquet")
    rec = extract_recovery_events(ev)
    totals, by_zone = recovery_counts(rec)
    out.mkdir(parents=True, exist_ok=True)
    totals.to_parquet(out / "recovery_coverage_totals.parquet", index=False)
    by_zone.to_parquet(out / "recovery_coverage_by_zone.parquet", index=False)
    print(f"recovery_coverage_totals:   {len(totals):>8} rows")
    print(f"recovery_coverage_by_zone:  {len(by_zone):>8} rows")
    print("counts per event type:", totals.groupby("event_type")["count"].sum().to_dict())
    return totals, by_zone


def build_spatial(raw=RAW, out=OUT, min_matches=MIN_MATCHES):
    meta = pd.read_parquet(raw / "statsbomb_360_event_meta.parquet")
    frames = pd.read_parquet(raw / "statsbomb_360_frames.parquet")
    res, stats = observed_spatial_dominance(frames, meta)
    tc = team_control(res, min_matches=min_matches)
    out.mkdir(parents=True, exist_ok=True)
    tc.to_parquet(out / "spatial_dominance_team_zone.parquet", index=False)
    print(f"spatial_dominance_team_zone: {len(tc):>7} rows "
          f"({tc.loc[tc['reportable'], 'defending_team'].nunique()} reportable teams, "
          f"{tc.loc[~tc['reportable'], 'defending_team'].nunique()} N/A)")
    print("frame stats:", dict(stats))
    return tc


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=["recovery", "spatial"], help="build just one metric")
    a = p.parse_args()
    if a.only in (None, "recovery"):
        build_recovery()
    if a.only in (None, "spatial"):
        build_spatial()
    print(f"\nSaved to {OUT}")