"""Player minutes and position groups, from StatsBomb lineups.

Input  (RAW):     data/raw/statsbomb_lineups.parquet   (one row per player position stint)
                  data/raw/statsbomb_team_events.parquet (only used for competition/season
                  per match, and for the join check)
Output (DERIVED): data/processed/player_minutes.parquet (one row per player-team-competition-season)

Rules (Person 4 decisions, NOT yet agreed with the team):
  1. Every match is treated as exactly 90 minutes. A stint with no end time runs to 90:00.
     All stint start/end times are capped at 90:00 (extra time is ignored).
  2. A player's position group = the group where they played the most minutes in that
     player-team-competition-season. Ties are reported (not hidden) and broken by the
     fixed order GK, CB, DM, CM, then others.
  3. Minutes are ALL minutes the player played, in any position. (Events are likewise
     counted from any position, so numerator and denominator match.)
  4. In scope = GK, CB, DM, CM. Everyone else (fullbacks, wide midfielders, attacking
     midfielders, forwards) is kept in the table but flagged in_scope = False.
  5. Players who never played (no position stint) are dropped.

Run from the repo root (PowerShell):
    python -W ignore -m src.metrics.player_minutes
"""

from pathlib import Path

import pandas as pd

from src.metrics.team_names import clean_team

LINEUPS ="data/raw/statsbomb_lineups.parquet"
EVENTS = "data/raw/statsbomb_team_events.parquet"
OUT = "data/processed/player_minutes.parquet"

MATCH_MINUTES = 90.0
IN_SCOPE = ["GK", "CB", "DM", "CM"]
GROUP_ORDER = ["GK", "CB", "DM", "CM", "FB", "WM", "AM", "ATT"]  # also the tie-break order

# Position labels are normalised (lower case, spaces removed) before lookup, because the
# labels showed up both with and without spaces in the test output.
GROUP_MAP = {
    "goalkeeper": "GK",
    "centerback": "CB", "leftcenterback": "CB", "rightcenterback": "CB",
    "centerdefensivemidfield": "DM", "leftdefensivemidfield": "DM", "rightdefensivemidfield": "DM",
    "centermidfield": "CM", "leftcentermidfield": "CM", "rightcentermidfield": "CM",
    "rightback": "FB", "leftback": "FB", "rightwingback": "FB", "leftwingback": "FB",
    "rightmidfield": "WM", "leftmidfield": "WM",
    "rightattackingmidfield": "AM", "centerattackingmidfield": "AM", "leftattackingmidfield": "AM",
    "rightwing": "ATT", "leftwing": "ATT", "centerforward": "ATT", "rightcenterforward": "ATT",
    "leftcenterforward": "ATT", "striker": "ATT", "secondarystriker": "ATT",
}


def norm(label) -> str:
    return str(label).lower().replace(" ", "")


def parse_clock(value) -> float:
    """'45:00' -> 45.0 minutes. Missing -> NaN."""
    if pd.isna(value):
        return float("nan")
    parts = str(value).split(":")
    return int(parts[0]) + int(parts[1]) / 60.0


def main():
    lineups = pd.read_parquet(LINEUPS)
    lineups["team"] = clean_team(lineups["team"])  # same club under two names -> one name
    print(f"Lineup rows: {len(lineups):,}   matches: {lineups['match_id'].nunique()}")

    # ---- 1. Drop players who never played (no position stint).
    played = lineups[lineups["position"].notna()].copy()
    print(f"Rows with a position stint: {len(played):,} (dropped {len(lineups) - len(played):,} non-playing rows)")

    # ---- 2. Stint minutes, everything capped at 90:00.
    start = played["from_time"].map(parse_clock).fillna(0.0).clip(0, MATCH_MINUTES)
    end = played["to_time"].map(parse_clock).fillna(MATCH_MINUTES).clip(0, MATCH_MINUTES)
    played["minutes"] = (end - start).clip(lower=0.0)

    # ---- 3. Position group per stint. Unmapped labels are shown, never guessed.
    played["position_norm"] = played["position"].map(norm)
    played["group"] = played["position_norm"].map(GROUP_MAP)
    label_table = (
        played.groupby(["position", "group"], dropna=False)["minutes"].sum().round(0)
        .reset_index().sort_values(["group", "position"], na_position="first")
    )
    print("\nPosition labels found and the group each maps to (check this list!):")
    print(label_table.to_string(index=False))
    unmapped = played[played["group"].isna()]["position"].unique().tolist()
    if unmapped:
        print(f"\nWARNING: unmapped position labels (their minutes are excluded from groups): {unmapped}")
        played = played[played["group"].notna()]

    # ---- 4. Competition and season per match, from the events file.
    ms = pd.read_parquet(EVENTS, columns=["match_id", "competition_name", "season_name"]).drop_duplicates()
    dup = ms["match_id"].duplicated().sum()
    if dup:
        print(f"WARNING: {dup} match_ids have more than one competition/season pair. Check the events file.")
    ms = ms.drop_duplicates("match_id")
    played = played.merge(ms, on="match_id", how="left")
    if played["competition_name"].isna().any():
        print(f"WARNING: {played['competition_name'].isna().sum()} stints have no competition/season.")

    # ---- 5. Per player-match totals (check nobody exceeds 90 minutes).
    pm = played.groupby(["match_id", "team", "player_id"])["minutes"].sum()
    print(f"\nPlayer-match minutes: max {pm.max():.2f}, min {pm.min():.2f}")
    if (pm > MATCH_MINUTES + 0.01).any():
        print("WARNING: some player-match totals exceed 90 minutes (overlapping stints?).")

    # ---- 6. Season table: minutes per group, then the group with most minutes.
    keys = ["player_id", "player_name", "team", "competition_name", "season_name"]
    wide = (
        played.groupby(keys + ["group"])["minutes"].sum().unstack("group", fill_value=0.0)
        .reindex(columns=GROUP_ORDER, fill_value=0.0)
    )
    wide.columns = [f"min_{g}" for g in GROUP_ORDER]
    wide = wide.reset_index()
    min_cols = [f"min_{g}" for g in GROUP_ORDER]

    wide["minutes"] = wide[min_cols].sum(axis=1)
    top = wide[min_cols].max(axis=1)
    wide["tied_groups"] = (wide[min_cols].eq(top, axis=0)).sum(axis=1)
    wide["position_group"] = wide[min_cols].idxmax(axis=1).str.replace("min_", "", regex=False)  # first max = GROUP_ORDER
    wide["in_scope"] = wide["position_group"].isin(IN_SCOPE)

    matches = (
        pm[pm > 0].reset_index().merge(ms, on="match_id", how="left")
        .groupby(["player_id", "team", "competition_name", "season_name"]).size().rename("matches").reset_index()
    )
    wide = wide.merge(matches, on=["player_id", "team", "competition_name", "season_name"], how="left")

    out = Path(OUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    wide.to_parquet(out, index=False)
    print(f"\nSaved {len(wide):,} player-season rows -> {out}")

    # ---- 7. Diagnostics.
    print(f"Rows with tied top groups: {(wide['tied_groups'] > 1).sum()} (tie broken by GROUP_ORDER)")
    print("\nPlayer-seasons per position group:")
    print(wide["position_group"].value_counts().reindex(GROUP_ORDER).to_string())

    scope = wide[wide["in_scope"]]
    print("\nMinutes per player-season, in-scope groups (use this to pick the minimum-minutes rule):")
    print(scope.groupby("position_group")["minutes"].describe(percentiles=[.1, .25, .5, .75, .9]).round(0).to_string())

    # ---- 8. Join check: do recovery events find their player in the lineups?
    ev = pd.read_parquet(EVENTS, columns=["match_id", "type", "team", "player", "duel_type"])
    ev = ev[(ev["type"].isin(["Ball Recovery", "Interception"])) | ((ev["type"] == "Duel") & (ev["duel_type"] == "Tackle"))]
    n_total = len(ev)
    ev = ev[ev["player"].notna()].copy()
    ev["team"] = clean_team(ev["team"])
    print(f"\nJoin check on recovery-type events (Ball Recovery, Interception, Tackle; before any success filter):")
    print(f"  events: {n_total:,}   with no player name: {n_total - len(ev):,}")
    keyset = played[["match_id", "team", "player_name"]].drop_duplicates().rename(columns={"player_name": "player"})
    chk = ev.groupby(["match_id", "team", "player"]).size().rename("n").reset_index().merge(
        keyset, on=["match_id", "team", "player"], how="left", indicator=True)
    matched = chk.loc[chk["_merge"] == "both", "n"].sum()
    print(f"  matched to a lineup player: {matched:,} of {len(ev):,} ({100 * matched / max(len(ev), 1):.2f}%)")
    miss = chk[chk["_merge"] == "left_only"].groupby(["team", "player"])["n"].sum().sort_values(ascending=False)
    if len(miss):
        print("  Top unmatched (team, player) -> events:")
        print(miss.head(15).to_string())

if __name__ == "__main__":
    main()