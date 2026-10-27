
"""
SOCCER IMPACT ENGINE
DEFENSIVE RECOVERY V2

Season: 2015/2016
Leagues: La Liga, Premier League, Serie A, Ligue 1

POSITION GROUPS
---------------
MID = DM + CM
CB  = Center Backs

MID and CB are ALWAYS ranked independently.

DEFENSIVE COMPONENTS
--------------------
1. Interceptions per 90
2. Successful Tackles per 90
3. Successful Ball Recoveries per 90

DEFENSIVE RECOVERY INDEX
------------------------
DRI = (
    interception_percentile
    + tackle_percentile
    + ball_recovery_percentile
) / 3

ELIGIBILITY
-----------
- At least 900 minutes
- Full league coverage
- Reportable data for all three components

TIERS
-----
Gold:   >= 90th percentile
Silver: >= 70th percentile
Other eligible players: Unranked
Ineligible players: N/A

FIFA-STYLE RATING
-----------------
rating = clip(65 + 10 * z_score, 1, 99)

Uses separate means and standard deviations for MID and CB.

INPUT
-----
data/processed/recovery_per90.parquet

OUTPUTS
-------
data/processed/defensive_recovery_mid_v2.csv
data/processed/defensive_recovery_mid_v2.parquet
data/processed/defensive_recovery_cb_v2.csv
data/processed/defensive_recovery_cb_v2.parquet

Run from repository root:
python -m src.metrics.defensive_recovery_v2

Existing V1 files are not overwritten.
"""

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT = ROOT / "data/processed/recovery_per90.parquet"
OUT = ROOT / "data/processed"

SEASON = "2015/2016"

LEAGUES = [
    "La Liga",
    "Premier League",
    "Serie A",
    "Ligue 1",
]

POSITION_MAP = {
    "DM": "MID",
    "CM": "MID",
    "CB": "CB",
}

EVENT_TYPES = [
    "Interception",
    "Tackle",
    "Ball Recovery",
]

EVENT_PREFIX = {
    "Interception": "interception",
    "Tackle": "tackle",
    "Ball Recovery": "ball_recovery",
}

ARCHETYPES = {
    "Interception": "Interceptor",
    "Tackle": "Ball-Winner",
    "Ball Recovery": "Recovery Specialist",
}

KEY = [
    "player_id",
    "team",
    "competition_name",
    "season_name",
]

MIN_MINUTES = 900

GOLD_THRESHOLD = 90.0
SILVER_THRESHOLD = 70.0

FIFA_BASELINE = 65.0
FIFA_SCALE = 10.0


# ============================================================
# HELPERS
# ============================================================

def require(df, columns, label):
    missing = sorted(set(columns) - set(df.columns))

    if missing:
        raise ValueError(
            f"{label} missing columns: {missing}. "
            f"Available: {list(df.columns)}"
        )


def validate_unique(df, columns, label):
    duplicates = int(df.duplicated(columns).sum())

    if duplicates:
        raise ValueError(
            f"{label}: {duplicates} duplicate keys found."
        )


def normalize_flag(series, label):
    """
    Safely normalize boolean flags.

    Does not interpret the string "False" as True.
    """
    normalized = (
        series.astype("string")
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
            "1": True,
            "0": False,
        })
    )

    if normalized.isna().any():
        raise ValueError(
            f"{label} contains missing or invalid values."
        )

    return normalized.astype(bool)


def assign_tiers(percentiles, eligible):
    tiers = pd.Series(
        "N/A",
        index=percentiles.index,
        dtype="object",
    )

    tiers.loc[eligible] = "Unranked"

    tiers.loc[
        eligible & percentiles.ge(SILVER_THRESHOLD)
    ] = "Silver"

    tiers.loc[
        eligible & percentiles.ge(GOLD_THRESHOLD)
    ] = "Gold"

    return tiers


def score_metric(df, value_col, prefix):
    """
    Score one metric using eligible players only.

    Called separately for MID and CB, so:
    - Percentiles are position-specific.
    - Means are position-specific.
    - Standard deviations are position-specific.
    - FIFA-style ratings are position-specific.
    """

    df = df.copy()

    eligible = df["tier_eligible"]

    percentile_col = f"{prefix}_percentile"
    zscore_col = f"{prefix}_zscore"
    rating_col = f"{prefix}_fifa_rating"
    tier_col = f"{prefix}_tier"

    df[percentile_col] = np.nan
    df[zscore_col] = np.nan
    df[rating_col] = np.nan

    values = df.loc[eligible, value_col]

    if values.empty:
        raise ValueError(
            f"No eligible players for {prefix}."
        )

    if values.isna().any():
        raise ValueError(
            f"Eligible players have missing {value_col}."
        )

    # Average ascending percentile rank.
    percentiles = (
        values.rank(method="average", pct=True) * 100
    )

    mean = values.mean()
    std = values.std(ddof=1)

    if pd.notna(std) and std > 0:
        zscores = (values - mean) / std
    else:
        # Identical values receive the neutral rating.
        zscores = pd.Series(
            0.0,
            index=values.index,
        )

    ratings = (
        FIFA_BASELINE + FIFA_SCALE * zscores
    ).clip(lower=1, upper=99)

    # Preserve decimal ratings, matching recovery_scores.py.
    df.loc[eligible, percentile_col] = percentiles
    df.loc[eligible, zscore_col] = zscores
    df.loc[eligible, rating_col] = ratings

    df[tier_col] = assign_tiers(
        df[percentile_col],
        eligible,
    )

    return df


# ============================================================
# LOAD AND VALIDATE RECOVERY DATA
# ============================================================

def load_data():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Cannot find input file: {INPUT}"
        )

    df = pd.read_parquet(INPUT)

    required = KEY + [
        "position_group",
        "minutes",
        "event_type",
        "count",
        "per90",
        "full_coverage",
        "reportable",
    ]

    require(df, required, "recovery_per90")

    df = df.loc[
        df["season_name"].eq(SEASON)
        & df["competition_name"].isin(LEAGUES)
        & df["position_group"].isin(POSITION_MAP)
        & df["event_type"].isin(EVENT_TYPES)
    ].copy()

    if df.empty:
        raise ValueError(
            "No matching MID/CB recovery records found."
        )

    df["score_group"] = (
        df["position_group"].map(POSITION_MAP)
    )

    for flag in ["full_coverage", "reportable"]:
        df[flag] = normalize_flag(df[flag], flag)

    for col in ["minutes", "count", "per90"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    if df[["minutes", "count", "per90"]].isna().any().any():
        raise ValueError(
            "Missing or nonnumeric minutes, count or per90."
        )

    if (df[["minutes", "count", "per90"]] < 0).any().any():
        raise ValueError(
            "Negative minutes, count or per90 found."
        )

    if df[KEY + ["event_type"]].isna().any().any():
        raise ValueError(
            "Null player keys or event types found."
        )

    validate_unique(
        df,
        KEY + ["event_type"],
        "Recovery source",
    )

    # All event rows for a player must agree on
    # position, minutes, and coverage.
    consistency_cols = [
        "position_group",
        "score_group",
        "minutes",
        "full_coverage",
    ]

    inconsistent = (
        df.groupby(KEY, dropna=False)[consistency_cols]
        .nunique(dropna=False)
    )

    if (inconsistent > 1).any().any():
        raise ValueError(
            "Conflicting position, minutes, or coverage "
            "for the same player-season."
        )

    print("\nSOURCE POSITION COUNTS")
    print(
        df.groupby("score_group")[KEY[0]]
        .nunique()
        .to_string()
    )

    return df


# ============================================================
# BUILD PLAYER-LEVEL TABLE
# ============================================================

def build_player_table(df):
    """
    Convert three event rows per player into one player row.

    Eligibility is checked at player level, requiring
    all three event types.
    """

    metadata_cols = KEY + [
        "position_group",
        "score_group",
        "minutes",
        "full_coverage",
    ]

    for optional in ["player", "player_name"]:
        if optional in df.columns:
            metadata_cols.append(optional)

    metadata = df[metadata_cols].drop_duplicates(KEY)

    validate_unique(
        metadata,
        KEY,
        "Player metadata",
    )

    # Individual action reportability must be preserved.
    reportability = df.pivot(
        index=KEY,
        columns="event_type",
        values="reportable",
    )

    rates = df.pivot(
        index=KEY,
        columns="event_type",
        values="per90",
    )

    counts = df.pivot(
        index=KEY,
        columns="event_type",
        values="count",
    )

    # Ensure all expected event columns exist.
    for event in EVENT_TYPES:
        if event not in rates.columns:
            rates[event] = np.nan

        if event not in counts.columns:
            counts[event] = np.nan

        if event not in reportability.columns:
            reportability[event] = False

    rates = rates.rename(
        columns={
            event: f"{prefix}_per90"
            for event, prefix in EVENT_PREFIX.items()
        }
    )

    counts = counts.rename(
        columns={
            event: f"{prefix}_count"
            for event, prefix in EVENT_PREFIX.items()
        }
    )

    reportability = reportability.rename(
        columns={
            event: f"{prefix}_reportable"
            for event, prefix in EVENT_PREFIX.items()
        }
    )

    rates = rates.reset_index()
    counts = counts.reset_index()
    reportability = reportability.reset_index()

    players = metadata.merge(
        rates,
        on=KEY,
        how="left",
        validate="one_to_one",
    )

    players = players.merge(
        counts,
        on=KEY,
        how="left",
        validate="one_to_one",
    )

    players = players.merge(
        reportability,
        on=KEY,
        how="left",
        validate="one_to_one",
    )

    rate_cols = [
        f"{prefix}_per90"
        for prefix in EVENT_PREFIX.values()
    ]

    report_cols = [
        f"{prefix}_reportable"
        for prefix in EVENT_PREFIX.values()
    ]

    # Missing reportability is treated as False.
    for col in report_cols:
        players[col] = (
            players[col].fillna(False).astype(bool)
        )

    players["tier_eligible"] = (
        players["minutes"].ge(MIN_MINUTES)
        & players["full_coverage"]
        & players[report_cols].all(axis=1)
        & players[rate_cols].notna().all(axis=1)
    )

    players["score_note"] = "ok"

    players.loc[
        ~players["full_coverage"],
        "score_note",
    ] = "N/A: incomplete league coverage"

    players.loc[
        players["full_coverage"]
        & players["minutes"].lt(MIN_MINUTES),
        "score_note",
    ] = "N/A: below 900 minutes"

    players.loc[
        players["full_coverage"]
        & players["minutes"].ge(MIN_MINUTES)
        & ~players[report_cols].all(axis=1),
        "score_note",
    ] = "N/A: incomplete or unreportable components"

    players.loc[
        players["full_coverage"]
        & players["minutes"].ge(MIN_MINUTES)
        & players[report_cols].all(axis=1)
        & ~players[rate_cols].notna().all(axis=1),
        "score_note",
    ] = "N/A: missing component rate"

    validate_unique(
        players,
        KEY,
        "Player-level recovery table",
    )

    return players


# ============================================================
# SCORE EACH POSITION GROUP
# ============================================================

def score_position_group(players, group):
    """
    Score MID or CB independently.

    The input is filtered BEFORE any ranking,
    mean, standard deviation, or tier calculation.
    """

    result = players.loc[
        players["score_group"].eq(group)
    ].copy()

    if result.empty:
        raise ValueError(
            f"No {group} players found."
        )

    if not result["tier_eligible"].any():
        raise ValueError(
            f"No eligible {group} players found."
        )

    # --------------------------------------------------------
    # INDIVIDUAL DEFENSIVE SPECIALIZATIONS
    # --------------------------------------------------------

    for event, prefix in EVENT_PREFIX.items():
        result = score_metric(
            result,
            f"{prefix}_per90",
            prefix,
        )

        result[f"{prefix}_archetype"] = ARCHETYPES[event]

    # --------------------------------------------------------
    # OVERALL DEFENSIVE RECOVERY INDEX
    # --------------------------------------------------------

    component_percentiles = [
        "interception_percentile",
        "tackle_percentile",
        "ball_recovery_percentile",
    ]

    result["defensive_recovery_score"] = (
        result[component_percentiles].mean(
            axis=1,
            skipna=False,
        )
    )

    # Ineligible players receive no DRI.
    result.loc[
        ~result["tier_eligible"],
        "defensive_recovery_score",
    ] = np.nan

    # The overall DRI gets its own percentile,
    # z-score, rating, and tier.
    result = score_metric(
        result,
        "defensive_recovery_score",
        "defensive_recovery",
    )

    return result


# ============================================================
# VALIDATION
# ============================================================

def validate_results(result, group):
    eligible = result.loc[
        result["tier_eligible"]
    ].copy()

    if eligible.empty:
        raise ValueError(
            f"No eligible {group} players."
        )

    if not result["score_group"].eq(group).all():
        raise ValueError(
            f"{group} contains players from another group."
        )

    validate_unique(
        result,
        KEY,
        f"{group} output",
    )

    metric_prefixes = [
        "interception",
        "tackle",
        "ball_recovery",
        "defensive_recovery",
    ]

    for prefix in metric_prefixes:
        percentile_col = f"{prefix}_percentile"
        rating_col = f"{prefix}_fifa_rating"

        if eligible[
            [percentile_col, rating_col]
        ].isna().any().any():
            raise ValueError(
                f"Missing eligible {prefix} scores."
            )

        if not eligible[
            percentile_col
        ].between(0, 100).all():
            raise ValueError(
                f"{prefix} percentiles outside 0-100."
            )

        if not eligible[
            rating_col
        ].between(1, 99).all():
            raise ValueError(
                f"{prefix} ratings outside 1-99."
            )

    # Recalculate DRI to verify equal weighting.
    expected_dri = eligible[
        [
            "interception_percentile",
            "tackle_percentile",
            "ball_recovery_percentile",
        ]
    ].mean(axis=1)

    if not np.allclose(
        eligible["defensive_recovery_score"],
        expected_dri,
        rtol=1e-10,
        atol=1e-10,
    ):
        raise ValueError(
            "DRI does not match equal-weighted components."
        )

    # Confirm source per90 rates match count/minutes.
    for prefix in EVENT_PREFIX.values():
        expected_rate = (
            eligible[f"{prefix}_count"]
            / eligible["minutes"]
            * 90
        )

        if not np.allclose(
            eligible[f"{prefix}_per90"],
            expected_rate,
            rtol=1e-5,
            atol=1e-7,
        ):
            raise ValueError(
                f"{prefix} per90 does not match count/minutes."
            )

    # Ineligible players must have no numerical rankings.
    ineligible = result.loc[
        ~result["tier_eligible"]
    ]

    for prefix in metric_prefixes:
        for suffix in [
            "percentile",
            "zscore",
            "fifa_rating",
        ]:
            col = f"{prefix}_{suffix}"

            if ineligible[col].notna().any():
                raise ValueError(
                    f"Ineligible {group} players have {col}."
                )

    print(f"\n{group} VALIDATION PASSED")
    print("Eligible players:", len(eligible))
    print("Duplicate keys: 0")
    print("All component rates validated.")
    print("All percentile/rating ranges validated.")
    print("Overall DRI equal weighting validated.")


# ============================================================
# SAVE AND PRINT RESULTS
# ============================================================

def save_group(result, group):
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    prefix = (
        f"defensive_recovery_{group.lower()}_v2"
    )

    csv_path = OUT / f"{prefix}.csv"
    parquet_path = OUT / f"{prefix}.parquet"

    sorted_result = result.sort_values(
        [
            "tier_eligible",
            "defensive_recovery_percentile",
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
    print(f"{group} DEFENSIVE RECOVERY RESULTS")
    print("=" * 70)

    print("Player-season rows:", len(result))
    print(
        "Eligible players:",
        int(result["tier_eligible"].sum()),
    )

    print("\nOVERALL DRI TIERS")
    print(
        result["defensive_recovery_tier"]
        .value_counts()
        .to_string()
    )

    print("\nTOP 15 DEFENSIVE RECOVERY PLAYERS")

    display_cols = [
        col for col in [
            "player",
            "player_name",
            "team",
            "competition_name",
            "minutes",
            "interception_per90",
            "tackle_per90",
            "ball_recovery_per90",
            "defensive_recovery_score",
            "defensive_recovery_percentile",
            "defensive_recovery_fifa_rating",
            "defensive_recovery_tier",
        ]
        if col in result.columns
    ]

    top = (
        result.loc[
            result["tier_eligible"]
        ]
        .nlargest(
            15,
            "defensive_recovery_percentile",
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
    print("DEFENSIVE RECOVERY V2")
    print("MID AND CB RANKED INDEPENDENTLY")
    print("=" * 70)

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing required file: {INPUT}"
        )

    # Step 1: Load and validate teammate's recovery data.
    source = load_data()

    # Step 2: Convert three event rows into one player row.
    players = build_player_table(source)

    print("\nPOSITION POPULATION")
    print(
        players["score_group"]
        .value_counts()
        .to_string()
    )

    # Step 3: Score and validate each position independently.
    results = {}

    for group in ["MID", "CB"]:
        result = score_position_group(
            players,
            group,
        )

        validate_results(
            result,
            group,
        )

        results[group] = result

    # Step 4: Save only after both groups pass validation.
    for group, result in results.items():
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
