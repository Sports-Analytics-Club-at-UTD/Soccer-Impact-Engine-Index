
"""Press Resistance V2: 2015/16, MID and CB ranked separately.

MID = DM + CM
CB = center backs only

Run:
    python src/metrics/press_resistance_v2.py

Inputs:
    data/raw/statsbomb_team_events.parquet
    data/processed/player_minutes.parquet
    data/processed/recovery_per90.parquet

Outputs:
    data/processed/press_resistance_mid_v2.csv
    data/processed/press_resistance_mid_v2.parquet
    data/processed/press_resistance_cb_v2.csv
    data/processed/press_resistance_cb_v2.parquet

Requires pandas and pyarrow (or another Parquet engine).
"""

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

RAW = ROOT / "data" / "raw" / "statsbomb_team_events.parquet"
MINUTES = ROOT / "data" / "processed" / "player_minutes.parquet"
RECOVERY = ROOT / "data" / "processed" / "recovery_per90.parquet"
OUT = ROOT / "data" / "processed"

SEASON = "2015/2016"
LEAGUES = {"La Liga", "Premier League", "Serie A", "Ligue 1"}

KEY = ["player_id", "team", "competition_name", "season_name"]
NAME_KEY = ["player", "team", "competition_name", "season_name"]

POSITION_MAP = {
    "DM": "MID",
    "CM": "MID",
    "CB": "CB",
}

MIN_MINUTES = 900
MIN_ACTIONS = 30
GOLD_THRESHOLD = 90
SILVER_THRESHOLD = 70

COUNT_COLS = [
    "pressured_pass_attempts",
    "pressured_pass_completed",
    "pressured_dribble_attempts",
    "pressured_dribble_completed",
]


def require(df, cols, label):
    missing = sorted(set(cols) - set(df.columns))
    if missing:
        raise ValueError(
            f"{label} missing columns: {missing}. "
            f"Available: {list(df.columns)}"
        )


def normalize_names(series):
    return (
        series.astype("string")
        .str.replace("''", "'", regex=False)
    )


def load_coverage():
    """Reduce recovery coverage to one flag per player-season key."""
    recovery = pd.read_parquet(RECOVERY)

    require(recovery, KEY + ["full_coverage"], "recovery_per90")

    recovery = recovery.loc[
        recovery["season_name"].eq(SEASON)
        & recovery["competition_name"].isin(LEAGUES),
        KEY + ["full_coverage"],
    ].copy()

    recovery["full_coverage"] = (
        recovery["full_coverage"].fillna(False).astype(bool)
    )

    inconsistent = (
        recovery.groupby(KEY, dropna=False)["full_coverage"].nunique()
    )

    if (inconsistent > 1).any():
        raise ValueError(
            "Conflicting full_coverage values for the same player-season."
        )

    return recovery.drop_duplicates(KEY)


def load_players(coverage):
    """Load MID and CB players, preserving the original coverage rules."""
    minutes = pd.read_parquet(MINUTES)

    require(
        minutes,
        KEY + ["minutes", "position_group"],
        "player_minutes",
    )

    minutes = minutes.loc[
        minutes["season_name"].eq(SEASON)
        & minutes["competition_name"].isin(LEAGUES)
        & minutes["position_group"].isin(POSITION_MAP),
    ].copy()

    if minutes.duplicated(KEY).any():
        raise ValueError(
            "player_minutes has duplicate player-season keys."
        )

    minutes["score_group"] = (
        minutes["position_group"].map(POSITION_MAP)
    )

    players = minutes.merge(
        coverage,
        on=KEY,
        how="left",
        validate="one_to_one",
    )

    players = players.loc[
        players["full_coverage"].eq(True)
    ].copy()

    if players.empty:
        raise ValueError(
            "No full-coverage MID or CB players found."
        )

    possible_name_cols = ["player_name", "player", "name"]
    name_col = next(
        (c for c in possible_name_cols if c in players.columns),
        None,
    )

    if name_col is None:
        raise ValueError(
            "player_minutes lacks a player-name field "
            "for mapping events to player_id."
        )

    if players[name_col].isna().any():
        raise ValueError(
            "Missing player names in player_minutes."
        )

    return players, name_col


def build_crosswalk(players, name_col):
    """Resolve event player names to stable player IDs."""
    crosswalk = (
        players[KEY + [name_col]]
        .rename(columns={name_col: "player"})
        .copy()
    )

    crosswalk["player"] = normalize_names(crosswalk["player"])

    ambiguous = (
        crosswalk.groupby(NAME_KEY, dropna=False)["player_id"].nunique()
    )

    if (ambiguous > 1).any():
        raise ValueError(
            "Ambiguous name-to-ID mappings found."
        )

    return crosswalk.drop_duplicates(NAME_KEY)


def calculate_pressured_actions(crosswalk):
    """Count pressured pass/dribble attempts and completions."""
    events = pd.read_parquet(RAW)

    require(
        events,
        [
            "match_id",
            "type",
            "player",
            "team",
            "competition_name",
            "season_name",
            "under_pressure",
            "pass_outcome",
            "dribble_outcome",
        ],
        "events",
    )

    events = events.loc[
        events["season_name"].eq(SEASON)
        & events["competition_name"].isin(LEAGUES)
        & events["under_pressure"].fillna(False).eq(True)
        & events["type"].isin(["Pass", "Dribble"])
        & events["player"].notna(),
    ].copy()

    events["player"] = normalize_names(events["player"])

    mapped = events.merge(
        crosswalk,
        on=NAME_KEY,
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    unmatched = mapped["_merge"].ne("both").sum()

    print(
        "Pressured pass/dribble events without "
        f"a MID/CB ID mapping: {unmatched:,}"
    )

    mapped = mapped.loc[
        mapped["_merge"].eq("both")
    ].copy()

    if mapped.empty:
        raise ValueError(
            "No events mapped to eligible-position players."
        )

    is_pass = mapped["type"].eq("Pass")

    mapped["successful"] = (
        (is_pass & mapped["pass_outcome"].isna())
        | (~is_pass & mapped["dribble_outcome"].eq("Complete"))
    )

    mapped["pressured_pass_attempts"] = is_pass.astype(int)
    mapped["pressured_pass_completed"] = (
        is_pass & mapped["successful"]
    ).astype(int)

    mapped["pressured_dribble_attempts"] = (~is_pass).astype(int)
    mapped["pressured_dribble_completed"] = (
        ~is_pass & mapped["successful"]
    ).astype(int)

    stats = mapped.groupby(KEY, as_index=False).agg(
        pressured_pass_attempts=("pressured_pass_attempts", "sum"),
        pressured_pass_completed=("pressured_pass_completed", "sum"),
        pressured_dribble_attempts=("pressured_dribble_attempts", "sum"),
        pressured_dribble_completed=("pressured_dribble_completed", "sum"),
    )

    return stats


def score_position_group(players, stats, group):
    """Calculate Press Resistance and rank only within this group."""
    group_players = players.loc[
        players["score_group"].eq(group)
    ].copy()

    result = group_players.merge(
        stats,
        on=KEY,
        how="left",
        validate="one_to_one",
    )

    result[COUNT_COLS] = (
        result[COUNT_COLS].fillna(0).astype(int)
    )

    result["pressured_actions"] = (
        result["pressured_pass_attempts"]
        + result["pressured_dribble_attempts"]
    )

    result["successful_pressured_actions"] = (
        result["pressured_pass_completed"]
        + result["pressured_dribble_completed"]
    )

    result["press_resistance_rate"] = (
        100 * result["successful_pressured_actions"]
        / result["pressured_actions"].where(
            result["pressured_actions"].gt(0)
        )
    )

    result["tier_eligible"] = (
        result["minutes"].ge(MIN_MINUTES)
        & result["pressured_actions"].ge(MIN_ACTIONS)
    )

    # CRITICAL: Each group gets its own independent percentile pool.
    # This function receives only MID or only CB rows.
    result["position_percentile"] = float("nan")

    eligible = result["tier_eligible"]

    result.loc[eligible, "position_percentile"] = (
        result.loc[eligible, "press_resistance_rate"]
        .rank(method="average", pct=True)
        * 100
    )

    percentile = result["position_percentile"]

    result["tier"] = "Unranked"

    result.loc[
        eligible & percentile.ge(SILVER_THRESHOLD),
        "tier",
    ] = "Silver"

    result.loc[
        eligible & percentile.ge(GOLD_THRESHOLD),
        "tier",
    ] = "Gold"

    return result


def save_group(result, group):
    """Save independent MID and CB outputs."""
    OUT.mkdir(parents=True, exist_ok=True)

    prefix = f"press_resistance_{group.lower()}_v2"

    csv_path = OUT / f"{prefix}.csv"
    parquet_path = OUT / f"{prefix}.parquet"

    sorted_result = result.sort_values(
        ["tier_eligible", "position_percentile"],
        ascending=False,
    )

    sorted_result.to_csv(csv_path, index=False)
    sorted_result.to_parquet(parquet_path, index=False)

    print(f"\n{'=' * 65}")
    print(f"{group} PRESS RESISTANCE")
    print("=" * 65)

    print("Leagues:", sorted(result["competition_name"].unique()))
    print("Player-season rows:", len(result))
    print("Tier eligible:", int(result["tier_eligible"].sum()))
    print("Tier counts:")
    print(result["tier"].value_counts().to_string())

    display_cols = [
        c for c in [
            "player_name",
            "player",
            "name",
            "team",
            "competition_name",
            "minutes",
            "pressured_actions",
            "press_resistance_rate",
            "position_percentile",
            "tier",
        ]
        if c in result.columns
    ]

    top = (
        result.loc[result["tier_eligible"]]
        .nlargest(15, "position_percentile")
    )

    print(
        "\nTop 15 eligible players:\n"
        + top[display_cols].to_string(index=False)
    )

    print(f"\nSaved:\n{csv_path}\n{parquet_path}")


def main():
    for path in (RAW, MINUTES, RECOVERY):
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Check the file location before running."
            )

    coverage = load_coverage()
    players, name_col = load_players(coverage)

    print("\nFull-coverage player population:")
    print(players["score_group"].value_counts().to_string())

    if not players["score_group"].eq("MID").any():
        raise ValueError("No MID players found.")

    if not players["score_group"].eq("CB").any():
        raise ValueError(
            "No CB players found. Check position_group in player_minutes."
        )

    crosswalk = build_crosswalk(players, name_col)
    stats = calculate_pressured_actions(crosswalk)

    for group in ["MID", "CB"]:
        result = score_position_group(players, stats, group)
        save_group(result, group)

    print("\nDONE: MID and CB ranked independently.")


if __name__ == "__main__":
    main()
