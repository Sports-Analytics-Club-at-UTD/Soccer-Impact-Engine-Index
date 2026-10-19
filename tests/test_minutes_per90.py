import math

import pandas as pd

from src.metrics.player_minutes import (
    GROUP_MAP, GROUP_ORDER, IN_SCOPE, norm, parse_clock,
    stint_minutes, assign_position_group,
)
from src.metrics.team_names import clean_team


def test_parse_clock_minutes_and_seconds():
    assert parse_clock("45:00") == 45.0
    assert parse_clock("60:30") == 60.5


def test_parse_clock_missing_is_nan():
    assert math.isnan(parse_clock(None))
    assert math.isnan(parse_clock(float("nan")))


def test_norm_ignores_case_and_spaces():
    assert norm("Left Center Back") == "leftcenterback"
    assert norm("LeftCenterBack") == "leftcenterback"


def test_all_three_centre_back_labels_map_to_cb():
    for label in ["Center Back", "Left Center Back", "Right Center Back"]:
        assert GROUP_MAP[norm(label)] == "CB"


def test_wide_midfielders_are_out_of_scope():
    assert GROUP_MAP["leftmidfield"] == "WM"
    assert GROUP_MAP["rightmidfield"] == "WM"
    assert "WM" not in IN_SCOPE


def test_every_mapped_group_is_in_group_order():
    assert set(GROUP_MAP.values()) <= set(GROUP_ORDER)


def test_clean_team_merges_duplicate_names():
    s = pd.Series(["Marseille", "Olympique de Marseille", "Caen", "Stade Malherbe Caen"])
    out = clean_team(s).tolist()
    assert out == ["Olympique de Marseille", "Olympique de Marseille",
                   "Stade Malherbe Caen", "Stade Malherbe Caen"]


def test_clean_team_leaves_other_names_alone():
    assert clean_team(pd.Series(["Paris Saint-Germain"])).tolist() == ["Paris Saint-Germain"]

def test_stint_minutes_cap_and_missing_end():
    # full match with no end time -> 90; stint running past 90 is capped; 60 min stays 60
    out = stint_minutes(
        pd.Series(["0:00", "0:00", "30:00"]),
        pd.Series([None, "120:00", "90:00"]),
    )
    assert out.tolist() == [90.0, 90.0, 60.0]


def test_position_group_most_minutes_wins_and_scope_flag():
    row = {f"min_{g}": 0.0 for g in GROUP_ORDER}
    row["min_CB"] = 600.0
    row["min_FB"] = 100.0
    out = assign_position_group(pd.DataFrame([row]))
    assert out["position_group"].iloc[0] == "CB"
    assert out["minutes"].iloc[0] == 700.0
    assert out["tied_groups"].iloc[0] == 1
    assert bool(out["in_scope"].iloc[0]) is True


def test_position_group_tie_goes_to_group_order_and_is_flagged():
    row = {f"min_{g}": 0.0 for g in GROUP_ORDER}
    row["min_DM"] = 450.0
    row["min_CM"] = 450.0
    out = assign_position_group(pd.DataFrame([row]))
    assert out["position_group"].iloc[0] == "DM"   # DM comes before CM in GROUP_ORDER
    assert out["tied_groups"].iloc[0] == 2