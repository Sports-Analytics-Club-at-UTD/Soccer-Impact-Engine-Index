"""Per-90 recovery rates for in-scope players (GK, CB, DM, CM).

Input  (DERIVED earlier): data/processed/recovery_coverage_totals.parquet
                          columns: player, team, competition_name, season_name, event_type, count
                          data/processed/player_minutes.parquet (from src.metrics.player_minutes)
Output (DERIVED):         data/processed/recovery_per90.parquet
                          one row per in-scope player-season x event type

Rules:
  - A league-season is "full coverage" if the events file has at least --full-season-matches
    matches for it (default 300). This is a data rule, not an outside assumption about league
    size: the events file shows either 377-380 matches or 36 or fewer, nothing in between.
  - pctl (PROVISIONAL helper, not the index): percentile of per90 within
    league-season x position group x event type, only for full-coverage seasons, players who
    meet the minimum minutes, and reportable rows. Everything else is N/A, with the reason in
    pctl_note. Event types are never blended.
  - Rows are matched on player name + team + competition + season (no player_id in the events file).
  - Only players with minutes > 0 and an in-scope position group are kept.
  - If a player has no row for an event type in the totals table, their count is 0
    (they played, and the events data recorded none). This is an ASSUMPTION; it is
    documented in docs/metric_documentation.md.
  - per90 = count / minutes * 90. Minutes of 0 would give N/A (never invented).
  - Goalkeepers: only Ball Recovery is reportable (reportable = False for GK Tackle and
    Interception). Rows are kept so the choice is visible, not hidden.
  - meets_min is only a convenience flag (default threshold is PROVISIONAL, set with
    --min-minutes). The final minimum-minutes rule is still to be decided.

Run from the repo root (PowerShell):
    python -W ignore -m src.metrics.recovery_per90
    python -W ignore -m src.metrics.recovery_per90 --min-minutes 900
"""

import argparse
from pathlib import Path

import pandas as pd

from src.metrics.team_names import clean_team
from src.metrics.player_names import clean_player

TOTALS ="data/processed/recovery_coverage_totals.parquet"
MINUTES = "data/processed/player_minutes.parquet"
EVENTS = "data/raw/statsbomb_team_events.parquet"
OUT = "data/processed/recovery_per90.parquet"

EVENT_TYPES = ["Tackle", "Interception", "Ball Recovery"]
KEYS = ["player", "team", "competition_name", "season_name"]
THRESHOLDS = [450, 900, 1350]

def season_coverage(ev, full_season_matches):
    """Matches per league-season, and whether it counts as full coverage."""
    cov = (
        ev.drop_duplicates()
        .groupby(["competition_name", "season_name"])["match_id"].nunique()
        .rename("season_matches").reset_index()
    )
    cov["full_coverage"] = cov["season_matches"] >= full_season_matches
    return cov


def finish_grid(grid, cov, min_minutes):
    """Missing counts -> 0, then per90, reportable, meets_min, and full_coverage."""
    grid = grid.copy()
    grid["count"] = grid["count"].fillna(0).astype(int)
    grid["per90"] = grid["count"] / grid["minutes"] * 90.0
    grid["reportable"] = ~((grid["position_group"] == "GK") & (grid["event_type"] != "Ball Recovery"))
    grid["meets_min"] = grid["minutes"] >= min_minutes
    return grid.merge(cov, on=["competition_name", "season_name"], how="left")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-minutes", type=float, default=900.0, help="PROVISIONAL threshold for the meets_min flag")
    ap.add_argument("--full-season-matches", type=int, default=300,
                    help="league-seasons with at least this many matches count as full coverage")
    args = ap.parse_args()

    totals = pd.read_parquet(TOTALS)
    # Same club under two names -> one name, then add up the counts that were split.
    totals["team"] = clean_team(totals["team"])
    totals["player"] = clean_player(totals["player"])
    totals = totals.groupby(KEYS + ["event_type"], as_index=False)["count"].sum()
    mins = pd.read_parquet(MINUTES).rename(columns={"player_name": "player"})

    # ---- Checks before merging.
    dups = mins.duplicated(KEYS, keep=False)
    if dups.any():
        print(f"WARNING: {dups.sum()} minutes rows share the same player/team/competition/season key "
              f"(two players with the same name?). Examples:")
        print(mins[dups][KEYS + ["player_id", "minutes"]].head(10).to_string(index=False))

    chk = totals.merge(mins[KEYS + ["in_scope"]].drop_duplicates(KEYS), on=KEYS, how="left")
    n_all = chk["count"].sum()
    n_unmatched = chk.loc[chk["in_scope"].isna(), "count"].sum()
    n_out = chk.loc[chk["in_scope"] == False, "count"].sum()  # noqa: E712
    n_in = chk.loc[chk["in_scope"] == True, "count"].sum()  # noqa: E712
    print(f"Events in totals table: {n_all:,}")
    print(f"  from in-scope players:     {n_in:,}")
    print(f"  from out-of-scope players: {n_out:,} (fullbacks, wingers, forwards, etc. - dropped here)")
    print(f"  not found in minutes:      {n_unmatched:,}")
    if n_unmatched:
        print("  Top unmatched (player, team, season):")
        un = chk[chk["in_scope"].isna()].groupby(KEYS)["count"].sum().sort_values(ascending=False)
        print(un.head(10).to_string())

    # ---- Season coverage, from the events file: how many matches does each league-season have?
    ev = pd.read_parquet(EVENTS, columns=["match_id", "competition_name", "season_name"]).drop_duplicates()
    cov = season_coverage(ev, args.full_season_matches)
    print(f"\nMatches per league-season in the events file (full_coverage = at least {args.full_season_matches}):")
    print(cov.to_string(index=False))

    # ---- Build the full player-season x event-type grid, then attach counts.
    base = mins[mins["in_scope"] & (mins["minutes"] > 0)].copy()
    grid = base.merge(pd.DataFrame({"event_type": EVENT_TYPES}), how="cross")
    grid = grid.merge(totals[KEYS + ["event_type", "count"]], on=KEYS + ["event_type"], how="left")
    n_zero = grid["count"].isna().sum()
    print(f"\nPlayer-season x event-type rows: {len(grid):,} ({n_zero:,} had no events row and are counted as 0)")
    grid = finish_grid(grid, cov, args.min_minutes)

    # ---- Provisional percentile, only where there is a real comparison group.
    pool_cols = ["competition_name", "season_name", "position_group", "event_type"]
    eligible = grid["reportable"] & grid["meets_min"] & grid["full_coverage"]
    elig = grid[eligible]
    grid["pctl"] = float("nan")
    grid["pool_n"] = float("nan")
    grid.loc[eligible, "pctl"] = elig.groupby(pool_cols)["per90"].rank(pct=True) * 100
    grid.loc[eligible, "pool_n"] = elig.groupby(pool_cols)["per90"].transform("size")
    grid["pctl_note"] = "ok"
    grid.loc[~grid["reportable"], "pctl_note"] = "N/A: goalkeeper, Ball Recovery only"
    grid.loc[grid["reportable"] & ~grid["full_coverage"], "pctl_note"] = "N/A: single-club season, no comparison group"
    grid.loc[grid["reportable"] & grid["full_coverage"] & ~grid["meets_min"], "pctl_note"] = "N/A: below minimum minutes"

    out_cols = ["player_id", "player", "team", "competition_name", "season_name", "position_group",
                "matches", "minutes", "event_type", "count", "per90", "reportable", "meets_min",
                "full_coverage", "pctl", "pool_n", "pctl_note"]
    out = grid[out_cols].sort_values(["competition_name", "season_name", "position_group", "player", "event_type"])
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    print(f"Saved {len(out):,} rows -> {OUT}")

    # ---- Help choose the minimum-minutes rule: how many players survive each threshold?
    players = out[["player_id", "player", "team", "competition_name", "season_name",
                   "position_group", "minutes"]].drop_duplicates()
    print("\nPlayer-seasons that would qualify at each minimum-minutes threshold:")
    rows = []
    for t in [0] + THRESHOLDS:
        s = players[players["minutes"] >= t].groupby("position_group").size()
        rows.append(s.rename(f">= {t}"))
    print(pd.concat(rows, axis=1).fillna(0).astype(int).reindex(["GK", "CB", "DM", "CM"]).to_string())

    # ---- Pool sizes for percentiles (league-season x position group) at the provisional threshold.
    ok = out[(out["pctl_note"] == "ok") & (out["event_type"] == "Ball Recovery")]
    pools = ok.groupby(["competition_name", "season_name", "position_group"]).size().rename("players").reset_index()
    print(f"\nPercentile pool sizes (full-coverage league-seasons only, >= {args.min_minutes:.0f} minutes):")
    print(pools.sort_values(["competition_name", "season_name", "position_group"]).to_string(index=False))
    print(f"  pools: {len(pools)}   smallest: {pools['players'].min()}   median: {pools['players'].median():.0f}")
    n_single = out[(out["event_type"] == "Ball Recovery") & out["meets_min"] & ~out["full_coverage"]]
    print(f"  Players meeting minimum minutes but with percentile N/A (single-club seasons): {len(n_single)}")


if __name__ == "__main__":
    main()