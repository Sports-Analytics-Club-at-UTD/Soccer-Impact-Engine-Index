"""Recovery scores: percentile and FIFA-style rating per event type, per 90, pooled across the four full leagues.

Input  (DERIVED): data/processed/recovery_per90.parquet
Output (DERIVED): data/processed/recovery_scores.parquet (one row per player-season x event type)

Rules (provisional, not final until the team agrees):
  - Group: DM and CM are one "MID" group. CB and GK keep their own groups.
  - Eligible: reportable, meets_min (900 by default) and full_coverage. Others get N/A.
  - Pool: season x group x event type, all full-coverage leagues together (no per-league ranking).
  - percentile = share of the pool at or below the player's per90 x 100 (0-100). Tiers use this.
  - rating = RATING_MEAN + RATING_SPREAD x z, where z = (per90 - pool mean) / pool std.
    Clipped to 1-99. Display layer only: the tiers do not use it.
  - Tiers: Gold >= 90, Silver >= 75 and < 90, else none (on the percentile).
  - The three event types are never blended: each has its own percentile, rating and tier.

Run from the repo root (PowerShell):
    python -W ignore -m src.metrics.recovery_scores
"""

from pathlib import Path

import numpy as np
import pandas as pd

SRC = "data/processed/recovery_per90.parquet"
OUT = "data/processed/recovery_scores.parquet"
GOLD, SILVER = 90.0, 75.0
RATING_MEAN, RATING_SPREAD = 65.0, 10.0
GROUP_MAP = {"DM": "MID", "CM": "MID", "CB": "CB", "GK": "GK"}
EVENT_TYPES = ["Tackle", "Interception", "Ball Recovery"]


def score_recovery(df):
    """Add score_group, percentile, rating, pool_n, tier and score_note to the per90 table."""
    df = df.copy()
    df["score_group"] = df["position_group"].map(GROUP_MAP)
    eligible = df["reportable"] & df["meets_min"] & df["full_coverage"]
    pool = ["season_name", "score_group", "event_type"]
    df["percentile"] = np.nan
    df["rating"] = np.nan
    df["pool_n"] = np.nan
    e = df[eligible]
    g = e.groupby(pool)["per90"]
    df.loc[eligible, "percentile"] = g.rank(pct=True) * 100
    df.loc[eligible, "pool_n"] = g.transform("size")
    mean = g.transform("mean")
    std = g.transform("std").replace(0, np.nan)
    z = ((e["per90"] - mean) / std).fillna(0.0)
    df.loc[eligible, "rating"] = (RATING_MEAN + RATING_SPREAD * z).clip(1, 99)
    df["tier"] = "none"
    df.loc[df["percentile"] >= SILVER, "tier"] = "Silver"
    df.loc[df["percentile"] >= GOLD, "tier"] = "Gold"
    df.loc[df["percentile"].isna(), "tier"] = "N/A"
    df["score_note"] = "ok"
    df.loc[~df["reportable"], "score_note"] = "N/A: goalkeeper, Ball Recovery only"
    df.loc[df["reportable"] & ~df["full_coverage"], "score_note"] = "N/A: single-club season, not in reference pool"
    df.loc[df["reportable"] & df["full_coverage"] & ~df["meets_min"], "score_note"] = "N/A: below minimum minutes"
    return df


def main():
    per90 = pd.read_parquet(SRC)
    out = score_recovery(per90)
    cols = ["player_id", "player", "team", "competition_name", "season_name", "position_group",
            "score_group", "minutes", "event_type", "count", "per90", "percentile", "rating",
            "pool_n", "tier", "score_note"]
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    out[cols].to_parquet(OUT, index=False)
    print(f"Saved {len(out):,} rows -> {OUT}")

    ok = out[out["score_note"] == "ok"]
    show = ["player", "team", "competition_name", "score_group", "minutes", "per90",
            "percentile", "rating", "tier", "pool_n"]

    print("\nPool sizes (eligible players per season x group x event type, all leagues together):")
    print(ok.groupby(["season_name", "score_group", "event_type"]).size().to_string())

    print("\nTier counts per event type:")
    print(ok.groupby(["event_type", "tier"]).size().unstack(fill_value=0).to_string())

    print("\nRating distribution per pool (mean, std, min, max, count of ratings >= 90):")
    d = ok.groupby(["score_group", "event_type"])["rating"].agg(["mean", "std", "min", "max"]).round(1)
    d["rating>=90"] = ok[ok["rating"] >= 90].groupby(["score_group", "event_type"]).size()
    print(d.fillna(0).to_string())

    print("\nTop 10 per event type (by percentile):")
    for et in EVENT_TYPES:
        t = ok[ok["event_type"] == et].sort_values(["percentile", "rating"], ascending=False).head(10)
        print(f"\n{et}")
        print(t[show].round(2).to_string(index=False))

    print("\nA few Silver players per event type (percentile 75 up to 90, highest first):")
    for et in EVENT_TYPES:
        s = ok[(ok["event_type"] == et) & (ok["tier"] == "Silver")].sort_values("percentile", ascending=False).head(8)
        print(f"\n{et}")
        print(s[show].round(2).to_string(index=False))


if __name__ == "__main__":
    main()