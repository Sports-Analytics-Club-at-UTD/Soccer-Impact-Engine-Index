
"""
SOCCER IMPACT ENGINE
PRESS RESISTANCE V2 — POSITION-SPECIFIC RANKINGS

Season: 2015/2016
Leagues: La Liga, Premier League, Serie A, Ligue 1

Position groups:
    MID = DM + CM
    CB  = Center Backs

Both groups are ranked INDEPENDENTLY.

Metrics:
    - Pressured pass completion
    - Pressured dribble completion
    - Combined press resistance rate
    - Position-specific percentile
    - Position-specific z-score
    - FIFA-style rating (1-99)
    - Gold / Silver / Unranked tiers

Eligibility:
    >= 900 minutes
    >= 30 pressured actions

Gold:   >= 90th percentile
Silver: >= 70th percentile

FIFA-style rating:
    clip(65 + 10 * z_score, 1, 99)

Run:
    python src/metrics/press_resistance_v2.py

Existing V1 outputs are NOT overwritten.
"""

from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

RAW = ROOT / "data/raw/statsbomb_team_events.parquet"
MINUTES = ROOT / "data/processed/player_minutes.parquet"
RECOVERY = ROOT / "data/processed/recovery_per90.parquet"

OUT = ROOT / "data/processed"

SEASON = "2015/2016"

LEAGUES = {
    "La Liga",
    "Premier League",
    "Serie A",
    "Ligue 1",
}

KEY = [
    "player_id",
    "team",
    "competition_name",
    "season_name",
]

NAME_KEY = [
    "player",
    "team",
    "competition_name",
    "season_name",
]

POSITION_MAP = {
    "DM": "MID",
    "CM": "MID",
    "CB": "CB",
}

MIN_MINUTES = 900
MIN_ACTIONS = 30

GOLD_THRESHOLD = 90
SILVER_THRESHOLD = 70

FIFA_BASELINE = 65
FIFA_SCALE = 10

COUNT_COLS = [
    "pressured_pass_attempts",
    "pressured_pass_completed",
    "pressured_dribble_attempts",
    "pressured_dribble_completed",
]


# ============================================================
# VALIDATION HELPERS
# ============================================================

def require(df, columns, label):
    missing = sorted(set(columns) - set(df.columns))

    if missing:
        raise ValueError(
            f"{label} missing columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def normalize_names(series):
    """
    Normalize StatsBomb names with doubled apostrophes.
    Example: N''Diaye -> N'Diaye
    """
    return (
        series.astype("string")
        .str.replace("''", "'", regex=False)
        .str.strip()
    )


def validate_unique(df, columns, label):
    duplicates = df.duplicated(columns).sum()

    if duplicates:
        raise ValueError(
            f"{label} contains {duplicates} duplicate keys."
        )


# ============================================================
# LOAD FULL-COVERAGE FLAGS
# ============================================================

def load_coverage():
    recovery = pd.read_parquet(RECOVERY)

    require(
        recovery,
        KEY + ["full_coverage"],
        "recovery_per90",
    )

    recovery = recovery.loc[
        recovery["season_name"].eq(SEASON)
        & recovery["competition_name"].isin(LEAGUES),
        KEY + ["full_coverage"],
    ].copy()

    recovery["full_coverage"] = (
        recovery["full_coverage"]
        .fillna(False)
        .astype(bool)
    )

    # Recovery data may contain multiple event-type rows.
    # Each player must have one consistent coverage flag.
    inconsistent = (
        recovery.groupby(KEY, dropna=False)["full_coverage"]
        .nunique()
    )

    if (inconsistent > 1).any():
        raise ValueError(
            "Conflicting full_coverage values "
            "for the same player-season."
        )

    coverage = recovery.drop_duplicates(KEY)

    validate_unique(
        coverage,
        KEY,
        "Recovery coverage",
    )

    return coverage


# ============================================================
# LOAD MIDFIELDERS AND CENTER BACKS
# ============================================================

def load_players(coverage):
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

    validate_unique(
        minutes,
        KEY,
        "Player minutes",
    )

    minutes["score_group"] = (
        minutes["position_group"]
        .map(POSITION_MAP)
    )

    players = minutes.merge(
        coverage,
        on=KEY,
        how="left",
        validate="one_to_one",
    )

    # Preserve the original V1 coverage requirement.
    players = players.loc[
        players["full_coverage"].eq(True)
    ].copy()

    if players.empty:
        raise ValueError(
            "No full-coverage MID/CB players found."
        )

    possible_name_cols = [
        "player_name",
        "player",
        "name",
    ]

    name_col = next(
        (
            col for col in possible_name_cols
            if col in players.columns
        ),
        None,
    )

    if name_col is None:
        raise ValueError(
            "No player-name column available "
            "for mapping events to player_id."
        )

    if players[name_col].isna().any():
        raise ValueError(
            "Missing player names in player_minutes."
        )

    players["minutes"] = pd.to_numeric(
        players["minutes"],
        errors="raise",
    )

    if players["minutes"].isna().any():
        raise ValueError(
            "Missing minutes for one or more players."
        )

    if (players["minutes"] < 0).any():
        raise ValueError(
            "Negative player minutes detected."
        )

    print("\nFULL-COVERAGE PLAYER POPULATION")
    print(
        players["score_group"]
        .value_counts()
        .to_string()
    )

    return players, name_col


# ============================================================
# BUILD PLAYER NAME -> ID CROSSWALK
# ============================================================

def build_crosswalk(players, name_col):
    """
    Event data contains player names rather than player IDs.

    Use player name + team + league + season
    to resolve stable player_id.

    All final joins use KEY, not player name.
    """

    crosswalk = (
        players[KEY + [name_col]]
        .rename(columns={name_col: "player"})
        .copy()
    )

    crosswalk["player"] = normalize_names(
        crosswalk["player"]
    )

    ambiguous = (
        crosswalk.groupby(
            NAME_KEY,
            dropna=False,
        )["player_id"]
        .nunique()
    )

    if (ambiguous > 1).any():
        raise ValueError(
            "Ambiguous name-to-ID mappings detected."
        )

    crosswalk = crosswalk.drop_duplicates(
        NAME_KEY
    )

    validate_unique(
        crosswalk,
        NAME_KEY,
        "Player crosswalk",
    )

    return crosswalk


# ============================================================
# CALCULATE PRESSURED ACTIONS
# ============================================================

def calculate_pressured_actions(crosswalk):
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
        "Raw events",
    )

    events = events.loc[
        events["season_name"].eq(SEASON)
        & events["competition_name"].isin(LEAGUES)
        & events["under_pressure"].fillna(False).eq(True)
        & events["type"].isin(["Pass", "Dribble"])
        & events["player"].notna(),
    ].copy()

    events["player"] = normalize_names(
        events["player"]
    )

    mapped = events.merge(
        crosswalk,
        on=NAME_KEY,
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    unmatched = int(
        mapped["_merge"].ne("both").sum()
    )

    print(
        "\nPressured pass/dribble events "
        "without a MID/CB ID mapping:",
        f"{unmatched:,}",
    )

    # These events belong to players outside our
    # validated positional/coverage population,
    # or have unresolved name mappings.
    mapped = mapped.loc[
        mapped["_merge"].eq("both")
    ].copy()

    if mapped.empty:
        raise ValueError(
            "No pressured events mapped to players."
        )

    is_pass = mapped["type"].eq("Pass")

    # StatsBomb pass outcome:
    # Null = completed pass.
    #
    # StatsBomb dribble outcome:
    # "Complete" = completed dribble.

    mapped["successful"] = (
        (
            is_pass
            & mapped["pass_outcome"].isna()
        )
        |
        (
            ~is_pass
            & mapped["dribble_outcome"].eq("Complete")
        )
    )

    mapped["pressured_pass_attempts"] = (
        is_pass.astype(int)
    )

    mapped["pressured_pass_completed"] = (
        is_pass & mapped["successful"]
    ).astype(int)

    mapped["pressured_dribble_attempts"] = (
        (~is_pass).astype(int)
    )

    mapped["pressured_dribble_completed"] = (
        ~is_pass & mapped["successful"]
    ).astype(int)

    stats = (
        mapped.groupby(
            KEY,
            as_index=False,
        )
        .agg(
            pressured_pass_attempts=(
                "pressured_pass_attempts",
                "sum",
            ),
            pressured_pass_completed=(
                "pressured_pass_completed",
                "sum",
            ),
            pressured_dribble_attempts=(
                "pressured_dribble_attempts",
                "sum",
            ),
            pressured_dribble_completed=(
                "pressured_dribble_completed",
                "sum",
            ),
        )
    )

    validate_unique(
        stats,
        KEY,
        "Pressured action statistics",
    )

    return stats


# ============================================================
# POSITION-SPECIFIC SCORING
# ============================================================

def score_position_group(players, stats, group):
    """
    Calculate press resistance for one position group.

    MID and CB are processed separately, ensuring:
      - Separate percentile distributions
      - Separate means
      - Separate standard deviations
      - Separate z-scores
      - Separate FIFA-style ratings
      - Separate Gold/Silver classifications
    """

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
        result[COUNT_COLS]
        .fillna(0)
        .astype(int)
    )

    # ----------------------------------------
    # TOTAL PRESSURED ACTIONS
    # ----------------------------------------

    result["pressured_actions"] = (
        result["pressured_pass_attempts"]
        + result["pressured_dribble_attempts"]
    )

    result["successful_pressured_actions"] = (
        result["pressured_pass_completed"]
        + result["pressured_dribble_completed"]
    )

    # ----------------------------------------
    # PRESS RESISTANCE RATE
    # ----------------------------------------

    result["press_resistance_rate"] = (
        100
        * result["successful_pressured_actions"]
        / result["pressured_actions"].where(
            result["pressured_actions"].gt(0)
        )
    )

    # ----------------------------------------
    # ELIGIBILITY
    # ----------------------------------------

    result["tier_eligible"] = (
        result["minutes"].ge(MIN_MINUTES)
        & result["pressured_actions"].ge(MIN_ACTIONS)
    )

    eligible = result["tier_eligible"]

    eligible_rates = result.loc[
        eligible,
        "press_resistance_rate",
    ]

    # ----------------------------------------
    # POSITION-SPECIFIC PERCENTILE
    # ----------------------------------------

    result["position_percentile"] = float("nan")

    result.loc[
        eligible,
        "position_percentile",
    ] = (
        eligible_rates.rank(
            method="average",
            pct=True,
        )
        * 100
    )

    # ----------------------------------------
    # POSITION-SPECIFIC Z-SCORE
    # ----------------------------------------

    group_mean = eligible_rates.mean()
    group_std = eligible_rates.std(ddof=1)

    result["press_resistance_zscore"] = float("nan")

    if pd.notna(group_std) and group_std > 0:
        zscores = (
            eligible_rates - group_mean
        ) / group_std
    else:
        # Identical rates or insufficient population:
        # Assign the baseline rating.
        zscores = pd.Series(
            0.0,
            index=eligible_rates.index,
        )

    result.loc[
        eligible,
        "press_resistance_zscore",
    ] = zscores

    # ----------------------------------------
    # FIFA-STYLE RATING (1-99)
    # ----------------------------------------

    result["press_resistance_fifa_rating"] = (
        float("nan")
    )

    fifa_ratings = (
        FIFA_BASELINE
        + FIFA_SCALE * zscores
    ).clip(
        lower=1,
        upper=99,
    ).round().astype(int)

    result.loc[
        eligible,
        "press_resistance_fifa_rating",
    ] = fifa_ratings

    # ----------------------------------------
    # GOLD / SILVER TIERS
    # ----------------------------------------

    result["tier"] = "Unranked"

    percentile = result["position_percentile"]

    result.loc[
        eligible
        & percentile.ge(SILVER_THRESHOLD),
        "tier",
    ] = "Silver"

    result.loc[
        eligible
        & percentile.ge(GOLD_THRESHOLD),
        "tier",
    ] = "Gold"

    # ----------------------------------------
    # GROUP SUMMARY STATISTICS
    # ----------------------------------------

    result["position_group_mean"] = group_mean
    result["position_group_std"] = group_std

    return result


# ============================================================
# OUTPUTS AND TERMINAL PREVIEW
# ============================================================

def save_group(result, group):
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    prefix = (
        f"press_resistance_{group.lower()}_v2"
    )

    csv_path = OUT / f"{prefix}.csv"
    parquet_path = OUT / f"{prefix}.parquet"

    sorted_result = result.sort_values(
        [
            "tier_eligible",
            "position_percentile",
        ],
        ascending=[
            False,
            False,
        ],
    )

    sorted_result.to_csv(
        csv_path,
        index=False,
    )

    sorted_result.to_parquet(
        parquet_path,
        index=False,
    )

    print("\n" + "=" * 70)
    print(f"{group} PRESS RESISTANCE RESULTS")
    print("=" * 70)

    print(
        "Leagues:",
        sorted(
            result["competition_name"].unique()
        ),
    )

    print(
        "Total player-season rows:",
        len(result),
    )

    print(
        "Tier eligible:",
        int(result["tier_eligible"].sum()),
    )

    print("\nTier counts:")
    print(
        result["tier"]
        .value_counts()
        .to_string()
    )

    eligible_rates = result.loc[
        result["tier_eligible"],
        "press_resistance_rate",
    ]

    print("\nPosition statistics:")
    print(
        "Mean press resistance:",
        round(eligible_rates.mean(), 2),
    )

    print(
        "Standard deviation:",
        round(eligible_rates.std(ddof=1), 2),
    )

    print("\nTOP 15 ELIGIBLE PLAYERS")

    display_cols = [
        col for col in [
            "player_name",
            "player",
            "name",
            "team",
            "competition_name",
            "minutes",
            "pressured_actions",
            "press_resistance_rate",
            "position_percentile",
            "press_resistance_zscore",
            "press_resistance_fifa_rating",
            "tier",
        ]
        if col in result.columns
    ]

    top = (
        result.loc[
            result["tier_eligible"]
        ]
        .nlargest(
            15,
            "position_percentile",
        )
    )

    print(
        top[display_cols]
        .round(2)
        .to_string(index=False)
    )

    print("\nSaved:")
    print(csv_path)
    print(parquet_path)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("SOCCER IMPACT ENGINE")
    print("PRESS RESISTANCE V2")
    print("MID AND CB — INDEPENDENT RANKINGS")
    print("=" * 70)

    for path in (
        RAW,
        MINUTES,
        RECOVERY,
    ):
        if not path.exists():
            raise FileNotFoundError(
                f"Missing required file: {path}"
            )

    # 1. Load coverage.
    coverage = load_coverage()

    # 2. Load eligible-position population.
    players, name_col = load_players(
        coverage
    )

    # 3. Confirm both positional populations exist.
    for group in ["MID", "CB"]:
        count = int(
            players["score_group"]
            .eq(group)
            .sum()
        )

        if count == 0:
            raise ValueError(
                f"No full-coverage {group} players found. "
                "Check position_group and coverage data."
            )

    # 4. Build name-to-ID mapping.
    crosswalk = build_crosswalk(
        players,
        name_col,
    )

    # 5. Count pressured passes and dribbles.
    stats = calculate_pressured_actions(
        crosswalk
    )

    # 6. Score and export independently.
    for group in ["MID", "CB"]:
        result = score_position_group(
            players,
            stats,
            group,
        )

        if not result["tier_eligible"].any():
            raise ValueError(
                f"No eligible {group} players. "
                "Check minutes and pressured actions."
            )

        save_group(
            result,
            group,
        )

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("MID and CB scored independently.")
    print("Existing V1 files preserved.")
    print("=" * 70)


if __name__ == "__main__":
    main()
