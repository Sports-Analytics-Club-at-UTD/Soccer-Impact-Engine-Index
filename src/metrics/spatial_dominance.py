"""Off-Ball Spatial Dominance - TEAM-LEVEL "Observed Spatial Dominance" (needs StatsBomb 360).

DRAFT DEFINITION (replaces the player-level one)
  Input   : 360 freeze frames (one row per visible player per event) + an EVENT-META table
            (id, match_id, team, possession_team) covering EVERY event type of the 360 matches.
            NOTE: the shared statsbomb_team_events.parquet is NOT enough - it keeps only 6 event
            types and has no possession_team, so most frame ids would not match. Use
            src/ingestion/fetch_360_event_meta.py to build data/raw/statsbomb_360_event_meta.parquet.
  Calc    : for every 360 frame where the OPPONENT has possession:
              1. keep only the part of the pitch the camera actually saw (visible_area)
              2. split that area into small grid cells (default 2 x 2 yards)
              3. give each cell to the nearest visible player
              4. count the cells that went to the defending team vs the attacking team
            Pool counts over frames and group by pitch zone.
  Result  : per team and zone:  control_rate = defender cells / observed cells
            ("the defending team was nearest to X% of the observed space in this zone").
  Name    : "Observed Spatial Dominance", NOT true pitch control. It ignores the ball,
            player speed and direction, and any player outside the camera view.

WHY TEAM-LEVEL: free 360 freeze frames carry no identity for off-ball players, so a
per-player rate cannot be built without inventing identities. We don't.

RULES / ASSUMPTIONS (all explicit)
  - Frames are EVENT-TRIGGERED, not uniform in time. Results describe space control at
    moments when something happened, not average control over a match.
  - Cells outside visible_area are not counted at all (N/A), never assumed.
  - A frame must contain >=1 player from each side, otherwise it is skipped
    (one-sided frames would mechanically give 100% control).
  - Orientation: the 360 coordinates are assumed to use the event ACTOR's perspective
    (actor's team attacks toward x = 120), same as events. VERIFY with inspect_data.py.
    We normalise every frame so the DEFENDING team's own goal is at x = 0:
        actor on the defending side -> no change
        actor on the possessing side -> mirror (x -> 120 - x, y -> 80 - y)
  - teammate == True means "same team as the actor".
  - Both goalkeepers are included as players.
  - No 360 data -> no output. Never substitute tackles / interceptions.
"""
from collections import Counter

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath

from src.metrics.zones import N_ZONES, PITCH_X, PITCH_Y, assign_zone, split_location

FLIP = np.array([PITCH_X, PITCH_Y])

# Minimum matches a team needs in a zone before its control_rate is reported.
# Below it, control_rate is NaN (N/A) - never a guess. Only 4 league-seasons have free 360 data
# and they cover one club each (PSG 57, Barcelona 35, Leverkusen 31 matches; every other team
# has <= 4, as opponents). Any value from 5 to 31 gives the same three teams; 10 is the
# documented choice. A team decision - change here if the team agrees on another value.
MIN_MATCHES = 10


def _require(df, cols, label):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"{label} is missing required columns: {missing}")


def make_grid(cell=2.0):
    """Cell centres over the whole pitch and the zone id of each cell."""
    xs = np.arange(cell / 2, PITCH_X, cell)
    ys = np.arange(cell / 2, PITCH_Y, cell)
    gx, gy = np.meshgrid(xs, ys)
    centers = np.column_stack([gx.ravel(), gy.ravel()])
    zones = assign_zone(centers[:, 0], centers[:, 1]).to_numpy(dtype=int)
    return centers, zones


def _parse_poly(va):
    try:
        arr = np.asarray(va, dtype=float).ravel()
    except (TypeError, ValueError):
        return None
    if arr.size < 6 or arr.size % 2 or not np.isfinite(arr).all():
        return None
    return arr.reshape(-1, 2)


def frame_control(points, is_attacker, poly, centers, cell_zone):
    """One frame (already in normalised coordinates).

    Returns (observed_cells_per_zone, defender_cells_per_zone), arrays of length N_ZONES + 1
    (index 0 unused), or None if no grid cell lies inside the visible area.
    """
    observed = MplPath(poly).contains_points(centers)
    if not observed.any():
        return None
    c = centers[observed]
    d2 = ((c[:, None, :] - points[None, :, :]) ** 2).sum(axis=2)
    nearest = d2.argmin(axis=1)
    defender = ~is_attacker[nearest]
    z = cell_zone[observed]
    return (np.bincount(z, minlength=N_ZONES + 1),
            np.bincount(z[defender], minlength=N_ZONES + 1))


def observed_spatial_dominance(frames, events, cell=2.0):
    """Match-level table + skip statistics.

    Returns (result, stats)
      result columns: match_id, defending_team, zone, observed_cells, defender_cells, n_frames
      stats: Counter of frames used / skipped by reason (put these numbers in the documentation)
    """
    _require(frames, ["id", "match_id", "visible_area", "teammate", "location"], "frames")
    _require(events, ["id", "match_id", "team", "possession_team"], "events")

    centers, cell_zone = make_grid(cell)
    meta = events.drop_duplicates("id")[["id", "team", "possession_team"]]
    match_teams = events.groupby("match_id")["team"].unique().to_dict()

    stats = Counter()
    acc = {}  # (match_id, defending_team) -> [observed(10), defender(10), frames(10)]

    for match_id, mf in frames.groupby("match_id", sort=False):
        mf = mf.merge(meta, on="id", how="left").reset_index(drop=True)
        teams = list(match_teams.get(match_id, []))
        x, y = split_location(mf["location"])
        teammate = mf["teammate"].to_numpy(dtype=bool)
        team_arr = mf["team"].to_numpy()
        poss_arr = mf["possession_team"].to_numpy()

        for _, idx in mf.groupby("id", sort=False).indices.items():
            r = idx[0]
            if len(teams) != 2:
                stats["skipped_match_teams_not_two"] += 1
                continue
            team, poss = team_arr[r], poss_arr[r]
            if pd.isna(team) or pd.isna(poss):
                stats["skipped_no_event_match"] += 1
                continue
            if poss not in teams:
                stats["skipped_possession_team_not_in_match"] += 1
                continue
            poly = _parse_poly(mf["visible_area"].iat[r])
            if poly is None:
                stats["skipped_no_visible_area"] += 1
                continue
            px, py = x[idx], y[idx]
            if np.isnan(px).any() or np.isnan(py).any():
                stats["skipped_missing_player_location"] += 1
                continue

            actor_is_attacker = team == poss
            is_att = teammate[idx] == actor_is_attacker
            if is_att.all() or (~is_att).all():
                stats["skipped_one_side_only"] += 1
                continue

            pts = np.column_stack([px, py])
            if actor_is_attacker:
                pts = FLIP - pts
                poly = FLIP - poly

            out = frame_control(pts, is_att, poly, centers, cell_zone)
            if out is None:
                stats["skipped_no_observed_cells"] += 1
                continue

            defending = [t for t in teams if t != poss][0]
            a = acc.setdefault((match_id, defending),
                               [np.zeros(N_ZONES + 1), np.zeros(N_ZONES + 1), np.zeros(N_ZONES + 1)])
            a[0] += out[0]
            a[1] += out[1]
            a[2] += (out[0] > 0)
            stats["frames_used"] += 1

    rows = []
    for (match_id, defending), (obs, dfn, nfr) in acc.items():
        for z in range(1, N_ZONES + 1):
            if obs[z] > 0:  # zone never observed -> no row = N/A
                rows.append((match_id, defending, z, int(obs[z]), int(dfn[z]), int(nfr[z])))
    result = pd.DataFrame(rows, columns=["match_id", "defending_team", "zone",
                                         "observed_cells", "defender_cells", "n_frames"])
    return result, stats


def team_control(result, min_matches=None):
    """Roll match-level rows up to team x zone. Cell-weighted (pooled), not an average of ratios.

    min_matches: if given, rows with fewer matches than this get control_rate = NaN (N/A) and
    reportable = False. The raw cell counts stay visible so the N/A is explainable.
    """
    g = result.groupby(["defending_team", "zone"]).agg(
        observed_cells=("observed_cells", "sum"),
        defender_cells=("defender_cells", "sum"),
        n_frames=("n_frames", "sum"),
        n_matches=("match_id", "nunique"),
    ).reset_index()
    g["control_rate"] = g["defender_cells"] / g["observed_cells"]
    if min_matches is not None:
        g["reportable"] = g["n_matches"] >= min_matches
        g.loc[~g["reportable"], "control_rate"] = np.nan
    return g


if __name__ == "__main__":
    from pathlib import Path

    raw = Path(__file__).resolve().parents[2] / "data" / "raw"
    meta = pd.read_parquet(raw / "statsbomb_360_event_meta.parquet")
    fr = pd.read_parquet(raw / "statsbomb_360_frames.parquet")
    res, st = observed_spatial_dominance(fr, meta)
    total = sum(st.values())
    print("Frames used / skipped by reason:")
    for k, v in sorted(st.items()):
        print(f"  {k}: {v}")
    print(f"  total frames seen: {total}")
    tc = team_control(res, min_matches=MIN_MATCHES)
    print("\ncontrol_rate range (must be within 0..1):", tc["control_rate"].min(), tc["control_rate"].max())
    shown = tc[tc["reportable"]]
    print(f"\nReportable (>= {MIN_MATCHES} matches): {shown['defending_team'].nunique()} teams; "
          f"N/A for {tc.loc[~tc['reportable'], 'defending_team'].nunique()} teams")
    print(shown.sort_values(["defending_team", "zone"]).to_string(index=False))

    # --- diagnostics ---
    per_team = tc.groupby("defending_team")["n_matches"].max().sort_values(ascending=False)
    print(f"\nTeams with results: {len(per_team)}")
    print("Matches per team (top 10):")
    print(per_team.head(10).to_string())
    print("Teams with only 1-2 matches:", int((per_team <= 2).sum()), "of", len(per_team))

    unmatched = fr[~fr["id"].isin(meta["id"])]
    print(f"\nFrames with no event match: {unmatched['id'].nunique()} frame ids in "
          f"{unmatched['match_id'].nunique()} matches. Top matches:")
    print(unmatched.groupby("match_id")["id"].nunique().sort_values(ascending=False).head(10).to_string())