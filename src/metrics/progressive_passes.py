"""Level A excerpts from Joseph-dev, 013c8edd5196a15ac826558f4b0964cc6f3a3e58.

Source: src/metrics/line_breaking.py and src/metrics/scoring_common.py.
Selected functions/constants are unchanged; only KEYS uses shared stable IDs.
No CLI, writers, percentile helpers, Level B or press-retention code is included.
Difficulty fitting is adapted for explicit whole-cohort calibration in src.passing.
"""
import numpy as np
import pandas as pd

from src.identity import PLAYER_KEYS as KEYS
from src.metrics.zones import X_EDGES, split_location

GOAL_X = 120.0


GOAL_Y = 40.0


OPEN_PLAY_PASS_TYPES = {"Recovery", "Interception"}


def distance_to_goal(x, y):
    """Distance in yards from (x, y) to the centre of the goal being attacked."""
    return np.hypot(GOAL_X - np.asarray(x, dtype=float), GOAL_Y - np.asarray(y, dtype=float))


def is_open_play_pass(events):
    """Boolean mask: Pass events that are not set pieces."""
    pass_type = events["pass_type"] if "pass_type" in events.columns else pd.Series(np.nan, index=events.index)
    return (events["type"] == "Pass") & (pass_type.isna() | pass_type.isin(OPEN_PLAY_PASS_TYPES))


def per90(count, minutes):
    """count / minutes * 90; N/A when minutes is 0 or missing."""
    minutes = pd.Series(minutes, dtype=float)
    return (pd.Series(count, dtype=float) / minutes * 90.0).where(minutes > 0)


PASS_EXCLUDED = {"Unknown", "Injury Clearance"}


PROGRESS_RATIO = 0.75


MIN_FORWARD = 10.0


LENGTH_BANDS = [0, 15, 30, np.inf]


REQUIRED_COLS = ["id", "match_id", "type", "team", "player", "competition_name", "season_name",
                 "location", "pass_end_location", "pass_outcome", "pass_type", "pass_length"]


def _third(x):
    """0 = own third, 1 = middle third, 2 = attacking third. NaN stays NaN."""
    x = np.asarray(x, dtype=float)
    third = np.clip(np.searchsorted(X_EDGES, x, side="right") - 1, 0, 2).astype(float)
    third[~np.isfinite(x)] = np.nan
    return third


def prepare_passes(events):
    """Open-play passes (excluding Unknown / Injury Clearance outcomes) with geometry columns."""
    missing = [c for c in REQUIRED_COLS if c not in events.columns]
    if missing:
        raise KeyError(f"events table is missing required columns: {missing}")
    keep = is_open_play_pass(events) & ~events["pass_outcome"].isin(PASS_EXCLUDED)
    p = events.loc[keep, REQUIRED_COLS].copy()
    p["x0"], p["y0"] = split_location(p["location"])
    p["x1"], p["y1"] = split_location(p["pass_end_location"])
    p = p.dropna(subset=["x0", "y0", "x1", "y1"])   # no location -> cannot be measured, not guessed
    p["completed"] = p["pass_outcome"].isna()
    p["d0"] = distance_to_goal(p["x0"], p["y0"])
    p["d1"] = distance_to_goal(p["x1"], p["y1"])
    p["forward"] = p["x1"] - p["x0"]
    length = p["pass_length"].astype(float)
    p["length"] = length.fillna(pd.Series(np.hypot(p["x1"] - p["x0"], p["y1"] - p["y0"]), index=p.index))
    p["start_third"] = _third(p["x0"])
    p["end_third"] = _third(p["x1"])
    return p.drop(columns=["location", "pass_end_location"])


def flag_progressive(passes, ratio=PROGRESS_RATIO, min_forward=MIN_FORWARD):
    p = passes.copy()
    p["prog_attempt"] = (p["d1"] <= ratio * p["d0"]) & (p["forward"] >= min_forward)
    p["progressive"] = p["prog_attempt"] & p["completed"]
    p["third_cross"] = p["progressive"] & (p["end_third"] > p["start_third"])
    p["pass_value"] = np.where(p["progressive"], (p["d0"] - p["d1"]) * p["difficulty"], 0.0)
    return p


def level_a_counts(passes):
    g = passes.groupby(KEYS)
    return pd.DataFrame({
        "prog_attempts": g["prog_attempt"].sum(),
        "prog_passes": g["progressive"].sum(),
        "third_cross": g["third_cross"].sum(),
        "value_sum": g["pass_value"].sum(),
    }).reset_index()
