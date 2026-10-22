
import pandas as pd
from pathlib import Path

# ============================================================
# STEP 1: Locate datasets
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_PATH = (
    BASE_DIR / "data" / "raw"
    / "statsbomb_team_events.parquet"
)

MINUTES_PATH = (
    BASE_DIR / "data" / "processed"
    / "player_minutes_2015_16.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = OUTPUT_DIR / "press_resistance_2015_16.csv"


# ============================================================
# STEP 2: Load datasets
# ============================================================

df = pd.read_parquet(
    DATA_PATH,
    columns=[
        "player",
        "team",
        "position",
        "season_name",
        "type",
        "under_pressure",
        "pass_outcome",
        "dribble_outcome"
    ]
)

minutes = pd.read_csv(MINUTES_PATH)

print("\nDatasets loaded successfully.")


# ============================================================
# STEP 3: Filter to 2015/16 season
# ============================================================

season = df[
    df["season_name"] == "2015/2016"
].copy()


# ============================================================
# STEP 4: Define midfielder positions
# ============================================================

midfield_positions = [
    "Center Defensive Midfield",
    "Left Defensive Midfield",
    "Right Defensive Midfield",
    "Center Midfield",
    "Left Center Midfield",
    "Right Center Midfield",
    "Center Attacking Midfield",
    "Left Attacking Midfield",
    "Right Attacking Midfield",
    "Left Midfield",
    "Right Midfield"
]

# Determine each player-team's primary recorded position
primary_positions = (
    season.dropna(subset=["player", "position"])
    .groupby(["player", "team"])["position"]
    .agg(lambda x: x.value_counts().idxmax())
    .reset_index()
)

# Keep midfielders only
midfielders = primary_positions[
    primary_positions["position"].isin(midfield_positions)
].copy()


# ============================================================
# STEP 5: Select pressured passes and dribbles
# ============================================================

actions = season[
    (season["under_pressure"] == True)
    & (season["type"].isin(["Pass", "Dribble"]))
].copy()


# ============================================================
# STEP 6: Identify successful actions
# ============================================================

# Completed passes have a missing pass_outcome.
# Successful dribbles have dribble_outcome == "Complete".

actions["successful"] = (
    (
        (actions["type"] == "Pass")
        & (actions["pass_outcome"].isna())
    )
    |
    (
        (actions["type"] == "Dribble")
        & (actions["dribble_outcome"] == "Complete")
    )
)


# ============================================================
# STEP 7: Aggregate player statistics
# ============================================================

scores = (
    actions.groupby(
        ["player", "team"],
        as_index=False
    )
    .agg(
        pressured_actions=("successful", "size"),
        successful_actions=("successful", "sum")
    )
)


# ============================================================
# STEP 8: Attach midfielder positions
# ============================================================

scores = scores.merge(
    midfielders,
    on=["player", "team"],
    how="inner",
    validate="one_to_one"
)


# ============================================================
# STEP 9: Attach seasonal minutes played
# ============================================================

scores = scores.merge(
    minutes[["player", "team", "minutes_played"]],
    on=["player", "team"],
    how="left",
    validate="one_to_one"
)

# Check for missing minutes
missing_minutes = scores["minutes_played"].isna().sum()

if missing_minutes > 0:
    raise ValueError(
        f"{missing_minutes} players have missing minutes. "
        "Check player/team names in both datasets."
    )


# ============================================================
# STEP 10: Apply eligibility requirements
# ============================================================

# Must play at least 1,000 minutes
# Must attempt at least 30 pressured actions

scores = scores[
    (scores["minutes_played"] >= 1000)
    & (scores["pressured_actions"] >= 30)
].copy()

if scores.empty:
    raise ValueError(
        "No midfielders meet the eligibility requirements."
    )


# ============================================================
# STEP 11: Calculate press resistance score
# ============================================================

scores["press_resistance_score"] = (
    100
    * scores["successful_actions"]
    / scores["pressured_actions"]
)


# ============================================================
# STEP 12: Calculate midfielder percentile
# ============================================================

# Compare only eligible midfielders.
# Keep full precision until output.

scores["midfielder_percentile"] = (
    scores["press_resistance_score"]
    .rank(pct=True, method="average")
    .mul(100)
)


# ============================================================
# STEP 13: Assign Gold / Silver tiers
# ============================================================

def assign_tier(percentile):
    if percentile >= 90:
        return "Gold"
    elif percentile >= 70:
        return "Silver"
    else:
        return "Unranked"


scores["tier"] = (
    scores["midfielder_percentile"]
    .apply(assign_tier)
)


# ============================================================
# STEP 14: Sort rankings
# ============================================================

scores = scores.sort_values(
    [
        "midfielder_percentile",
        "pressured_actions"
    ],
    ascending=[False, False]
)


# ============================================================
# STEP 15: Select output columns
# ============================================================

columns = [
    "player",
    "team",
    "position",
    "minutes_played",
    "pressured_actions",
    "successful_actions",
    "press_resistance_score",
    "midfielder_percentile",
    "tier"
]

output = scores[columns].copy()

# Round only for presentation and export
output[
    ["press_resistance_score", "midfielder_percentile"]
] = output[
    ["press_resistance_score", "midfielder_percentile"]
].round(2)


# ============================================================
# STEP 16: Preview top 15 midfielders
# ============================================================

print(
    "\nTOP 15 MIDFIELDERS - "
    "PRESS RESISTANCE (2015/16)\n"
)

print(
    output.head(15).to_string(index=False)
)


# ============================================================
# STEP 17: Summary
# ============================================================

print(
    f"\nTotal qualifying midfielders: {len(output)}"
)

print("\nTier Distribution:")
print(output["tier"].value_counts())


# ============================================================
# STEP 18: Export CSV
# ============================================================

output.to_csv(
    OUTPUT_PATH,
    index=False
)

print(f"\nResults saved to: {OUTPUT_PATH}")

print("\nPRESS RESISTANCE ANALYSIS COMPLETE")
