"""Shared helpers for Press Resistance and Line-Breaking Pass Value.

Same conventions as recovery_per90.py (Person 4), so the outputs line up:
  - players are matched on name + team + competition + season (no player_id in the events file)
  - minutes and position groups come from data/processed/player_minutes.parquet
  - a league-season is "full coverage" if the events file has >= FULL_SEASON_MATCHES matches
  - percentiles only within league-season x position group, full-coverage seasons only

Pitch geometry: StatsBomb 120 x 80 yards. Every event is recorded from the acting team's
point of view, attacking towards x = 120, so the goal being attacked is at (120, 40).
"""
import numpy as np
import pandas as pd

from src.metrics.team_names import clean_team

EVENTS = "data/raw/statsbomb_team_events.parquet"
MINUTES = "data/processed/player_minutes.parquet"

KEYS = ["player", "team", "competition_name", "season_name"]
GOAL_X = 120.0
GOAL_Y = 40.0

DEFAULT_MIN_MINUTES = 900.0      # PROVISIONAL, same as recovery_per90
FULL_SEASON_MATCHES = 300        # DERIVED from the match-count gap (377-380 vs <= 36)

# pass_type values that still count as open play. Empty pass_type = a normal open-play pass.
# Corner, Free Kick, Goal Kick, Kick Off and Throw-in are set pieces and are excluded.
OPEN_PLAY_PASS_TYPES = {"Recovery", "Interception"}


def distance_to_goal(x, y):
    """Distance in yards from (x, y) to the centre of the goal being attacked."""
    return np.hypot(GOAL_X - np.asarray(x, dtype=float), GOAL_Y - np.asarray(y, dtype=float))


def is_open_play_pass(events):
    """Boolean mask: Pass events that are not set pieces."""
    pass_type = events["pass_type"] if "pass_type" in events.columns else pd.Series(np.nan, index=events.index)
    return (events["type"] == "Pass") & (pass_type.isna() | pass_type.isin(OPEN_PLAY_PASS_TYPES))


def is_true(series):
    """StatsBomb boolean flags are True or empty. Empty means False."""
    return series.eq(True).fillna(False).astype(bool)


def clean_keys(df):
    """Apply the shared team-name cleaning so keys match player_minutes."""
    df = df.copy()
    df["team"] = clean_team(df["team"])
    return df


def season_coverage(events, full_season_matches=FULL_SEASON_MATCHES):
    """Matches per league-season in the events file, and whether it is a full league season."""
    ms = events[["match_id", "competition_name", "season_name"]].drop_duplicates()
    cov = ms.groupby(["competition_name", "season_name"])["match_id"].nunique().rename("season_matches").reset_index()
    cov["full_coverage"] = cov["season_matches"] >= full_season_matches
    return cov


def in_scope_base(minutes):
    """One row per in-scope player-season with minutes > 0 (GK, CB, DM, CM)."""
    mins = minutes.rename(columns={"player_name": "player"})
    dups = mins.duplicated(KEYS, keep=False)
    if dups.any():
        print(f"WARNING: {dups.sum()} minutes rows share a player/team/competition/season key "
              f"(two players with the same name?). Keeping the first of each.")
        mins = mins.drop_duplicates(KEYS)
    cols = [c for c in ["player_id", *KEYS, "position_group", "matches", "minutes", "in_scope"] if c in mins.columns]
    return mins.loc[mins["in_scope"] & (mins["minutes"] > 0), cols].copy()


def attach_counts(base, counts, count_cols):
    """Left-join per player-season counts onto the minutes base. A player with no row gets 0
    (ASSUMPTION, same as recovery_per90: they played and the data recorded none)."""
    out = base.merge(counts, on=KEYS, how="left")
    out[count_cols] = out[count_cols].fillna(0).astype(int)
    return out


def per90(count, minutes):
    """count / minutes * 90; N/A when minutes is 0 or missing."""
    minutes = pd.Series(minutes, dtype=float)
    return (pd.Series(count, dtype=float) / minutes * 90.0).where(minutes > 0)


def add_percentile(df, value_col, eligible, pool_cols=("competition_name", "season_name", "position_group")):
    """pctl_<value_col>: percentile within the pool, only for eligible rows. Others are NaN.
    Ties get the average rank; the top player is 100."""
    pool_cols = list(pool_cols)
    col = f"pctl_{value_col}"
    df[col] = np.nan
    ok = eligible & df[value_col].notna()
    if ok.any():
        df.loc[ok, col] = df[ok].groupby(pool_cols)[value_col].rank(pct=True) * 100
    return df


def na_reason(df, min_minutes):
    """One reason per row explaining why percentiles are missing ('ok' if they are not)."""
    reason = pd.Series("ok", index=df.index, dtype=object)
    reason[~df["full_coverage"].fillna(False).astype(bool)] = "N/A: single-club season, no comparison group"
    reason[(reason == "ok") & (df["minutes"] < min_minutes)] = "N/A: below minimum minutes"
    return reason
