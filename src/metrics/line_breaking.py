"""Progressive Line-Breaking Pass Value (owner: Joseph).

Two levels, because true line-breaking needs opponent positions and those only exist in 360 data.

INPUT  (RAW)     data/raw/statsbomb_team_events.parquet
                 data/raw/statsbomb_360_frames.parquet          (Level B only, optional)
                 data/processed/player_minutes.parquet
OUTPUT (DERIVED) data/processed/line_breaking_per90.parquet, one row per in-scope player-season

LEVEL A: Progressive Pass Value (all matches, events only)
  A pass is PROGRESSIVE if it is an open-play pass, complete (pass_outcome empty), and
    d_end <= 0.75 * d_start        at least 25% closer to goal              ASSUMPTION
    end_x - start_x >= 10          at least 10 yards forward                ASSUMPTION
  An ATTEMPT is any open-play pass meeting the two geometry rules, complete or not.
  THIRD-CROSSING: progressive and ends in a higher third (x = 40 / 80, same as zones.py).
  Pass value = (d_start - d_end) * (1 - p_hat), where p_hat is the completion rate of all
    open-play passes in the same league-season, starting third and length band
    (0-15, 15-30, 30+ yards). Harder passes earn more credit.
  Columns: prog_passes_p90, prog_completion_pct, third_cross_p90, pass_value_p90 (headline)

LEVEL B: True Line-Breaking (360 matches only)
  For each complete open-play pass with a 360 frame, opponents_bypassed = number of visible
  outfield opponents (teammate == False, keeper == False) whose x is strictly between the
  pass start x and end x. LINE BREAK if opponents_bypassed >= 3 (ASSUMPTION).
  360 coordinates are from the actor's (passer's) point of view, confirmed by Person 4's
  goalkeeper check, so they line up with the pass coordinates. orientation_check() re-checks.
  Columns: line_breaks_p90, opponents_bypassed_p90.
  N/A unless the player's league-season has 360 data for every match AND minutes >= 450.
  No percentiles: in practice the sample is one club per season, so there is no fair pool.
  Opponents outside the camera view are not counted, so opponents_bypassed is a lower bound.

Run from the repo root:
    python -W ignore -m src.metrics.line_breaking
    python -W ignore -m src.metrics.line_breaking --no-360
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.metrics.scoring_common import (
    DEFAULT_MIN_MINUTES, EVENTS, KEYS, MINUTES, add_percentile, attach_counts, clean_keys,
    distance_to_goal, in_scope_base, is_open_play_pass, na_reason, per90, season_coverage,
)
from src.metrics.zones import X_EDGES, split_location

FRAMES = "data/raw/statsbomb_360_frames.parquet"
OUT = "data/processed/line_breaking_per90.parquet"

PASS_EXCLUDED = {"Unknown", "Injury Clearance"}
PROGRESS_RATIO = 0.75            # end must be <= 75% of the start distance to goal   ASSUMPTION
MIN_FORWARD = 10.0               # yards                                              ASSUMPTION
LENGTH_BANDS = [0, 15, 30, np.inf]
MIN_BYPASSED = 3                 # opponents, roughly one defensive line              ASSUMPTION
MIN_MINUTES_360 = 450.0          # ASSUMPTION

REQUIRED_COLS = ["id", "match_id", "type", "team", "player", "competition_name", "season_name",
                 "location", "pass_end_location", "pass_outcome", "pass_type", "pass_length"]
METRICS_A = ["prog_passes_p90", "prog_completion_pct", "third_cross_p90", "pass_value_p90"]
METRICS_B = ["line_breaks_p90", "opponents_bypassed_p90"]


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


def add_difficulty(passes):
    """p_hat = completion rate in the same league-season x start third x length band."""
    p = passes.copy()
    p["length_band"] = pd.cut(p["length"], LENGTH_BANDS, right=False, labels=["0-15", "15-30", "30+"])
    cell = ["competition_name", "season_name", "start_third", "length_band"]
    p["p_hat"] = p.groupby(cell, observed=True)["completed"].transform("mean")
    p["difficulty"] = 1.0 - p["p_hat"]
    return p


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


# ---------------- Level B (360) ----------------
def opponents_bypassed(passes, frames, min_bypassed=MIN_BYPASSED):
    """Per complete pass: has_frame, opponents_bypassed (NaN without a frame), line_break."""
    p = passes.loc[passes["completed"], ["id", *KEYS, "x0", "x1"]].copy()
    p["has_frame"] = p["id"].isin(set(frames["id"]))
    opp = frames[(frames["teammate"] == False) & (frames["keeper"] == False)]  # noqa: E712
    ox, _ = split_location(opp["location"])
    opp = pd.DataFrame({"id": opp["id"].to_numpy(), "ox": ox})
    m = p[p["has_frame"]][["id", "x0", "x1"]].merge(opp, on="id", how="inner")
    between = (m["ox"] > m["x0"]) & (m["ox"] < m["x1"])
    bypassed = between.groupby(m["id"]).sum()
    p["opponents_bypassed"] = p["id"].map(bypassed)
    p.loc[p["has_frame"], "opponents_bypassed"] = p.loc[p["has_frame"], "opponents_bypassed"].fillna(0)
    p["line_break"] = p["opponents_bypassed"] >= min_bypassed
    return p


def orientation_check(passes, frames):
    """Median distance between the 360 actor position and the pass start location.
    Small (a couple of yards) means both use the same orientation."""
    actor = frames[frames["actor"] == True]  # noqa: E712
    ax, ay = split_location(actor["location"])
    a = pd.DataFrame({"id": actor["id"].to_numpy(), "ax": ax, "ay": ay}).merge(passes[["id", "x0", "y0"]], on="id")
    return float(np.median(np.hypot(a["ax"] - a["x0"], a["ay"] - a["y0"]))) if len(a) else float("nan")


def level_b_counts(bypass):
    f = bypass[bypass["has_frame"]]
    g = f.groupby(KEYS)
    return pd.DataFrame({
        "passes_360": g.size(),
        "line_breaks": g["line_break"].sum(),
        "opp_bypassed_sum": g["opponents_bypassed"].sum(),
    }).reset_index()


def coverage_360(events, frames):
    """full_360 = every match the events file has for that league-season also has 360 frames."""
    ev = events[["match_id", "competition_name", "season_name"]].drop_duplicates()
    ev["has_360"] = ev["match_id"].isin(set(frames["match_id"]))
    cov = ev.groupby(["competition_name", "season_name"])["has_360"].mean().rename("share_360").reset_index()
    cov["full_360"] = cov["share_360"] == 1.0
    return cov


# ---------------- table ----------------
def build_table(a_counts, base, coverage, b_counts=None, cov360=None, min_minutes=DEFAULT_MIN_MINUTES):
    df = attach_counts(base, a_counts, ["prog_attempts", "prog_passes", "third_cross"])
    df["value_sum"] = df["value_sum"].fillna(0.0)
    df = df.merge(coverage, on=["competition_name", "season_name"], how="left")

    df["prog_passes_p90"] = per90(df["prog_passes"], df["minutes"])
    df["prog_completion_pct"] = (100 * df["prog_passes"] / df["prog_attempts"].replace(0, np.nan))
    df["third_cross_p90"] = per90(df["third_cross"], df["minutes"])
    df["pass_value_p90"] = per90(df["value_sum"], df["minutes"])

    df["meets_min"] = df["minutes"] >= min_minutes
    eligible = df["full_coverage"].fillna(False).astype(bool) & df["meets_min"]
    for m in METRICS_A:
        add_percentile(df, m, eligible)
    df["na_reason"] = na_reason(df, min_minutes)

    if b_counts is None or cov360 is None:
        for m in METRICS_B:
            df[m] = np.nan
        df["lb_note"] = "N/A: 360 data not loaded"
        return df

    df = attach_counts(df, b_counts, ["passes_360", "line_breaks"])
    df["opp_bypassed_sum"] = df["opp_bypassed_sum"].fillna(0)
    df = df.merge(cov360, on=["competition_name", "season_name"], how="left")
    full = df["full_360"].fillna(False).astype(bool)
    ok_b = full & (df["minutes"] >= MIN_MINUTES_360)
    df["line_breaks_p90"] = per90(df["line_breaks"], df["minutes"]).where(ok_b)
    df["opponents_bypassed_p90"] = per90(df["opp_bypassed_sum"], df["minutes"]).where(ok_b)
    df["lb_note"] = "ok"
    df.loc[~full, "lb_note"] = "N/A: no 360 data for every match of this season"
    df.loc[full & ~ok_b, "lb_note"] = f"N/A: below {MIN_MINUTES_360:.0f} minutes"
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-minutes", type=float, default=DEFAULT_MIN_MINUTES, help="PROVISIONAL")
    ap.add_argument("--no-360", action="store_true", help="skip Level B")
    args = ap.parse_args()

    events = pd.read_parquet(EVENTS)
    events = clean_keys(events[[c for c in REQUIRED_COLS if c in events.columns]])
    passes = flag_progressive(add_difficulty(prepare_passes(events)))
    print(f"Open-play passes measured: {len(passes):,}")
    print(f"  progressive attempts: {passes['prog_attempt'].sum():,}   completed: {passes['progressive'].sum():,}"
          f"   third-crossing: {passes['third_cross'].sum():,}")

    base = in_scope_base(pd.read_parquet(MINUTES))
    cov = season_coverage(events)

    b_counts = cov360 = None
    if not args.no_360 and Path(FRAMES).exists():
        frames = pd.read_parquet(FRAMES, columns=["id", "match_id", "teammate", "actor", "keeper", "location"])
        print(f"\nOrientation check: median actor-to-pass-start distance = "
              f"{orientation_check(passes, frames):.2f} yards (should be small)")
        bypass = opponents_bypassed(passes, frames)
        f = bypass[bypass["has_frame"]]
        print(f"Complete passes with a 360 frame: {len(f):,}   line breaks: {int(f['line_break'].sum()):,}")
        print("opponents_bypassed distribution (use this to calibrate MIN_BYPASSED):")
        print(f["opponents_bypassed"].value_counts().sort_index().to_string())
        # How well does Level A stand in for Level B?
        both = f.merge(passes[["id", "progressive"]], on="id")
        print("\nLevel A progressive vs Level B line break (360 passes only):")
        print(pd.crosstab(both["progressive"], both["line_break"]).to_string())
        b_counts, cov360 = level_b_counts(bypass), coverage_360(events, frames)
    elif not args.no_360:
        print(f"\n{FRAMES} not found: Level B columns will be N/A.")

    df = build_table(level_a_counts(passes), base, cov, b_counts, cov360, args.min_minutes)
    out_cols = ["player_id", *KEYS, "position_group", "matches", "minutes", "prog_attempts", "prog_passes",
                "third_cross", "value_sum", *METRICS_A, *[f"pctl_{m}" for m in METRICS_A], "meets_min",
                "full_coverage", "na_reason", "passes_360", "line_breaks", *METRICS_B, "lb_note"]
    df = df[[c for c in out_cols if c in df.columns]].sort_values(KEYS)
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(f"\nSaved {len(df):,} rows -> {OUT}")

    ok = df[df["meets_min"]]
    print(f"\nLevel A by group (>= {args.min_minutes:.0f} min):")
    print(ok.groupby("position_group")[METRICS_A].median().round(2).to_string())


if __name__ == "__main__":
    main()
