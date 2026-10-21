import pandas as pd

from src.metrics.recovery_per90 import finish_grid, season_coverage

COV = pd.DataFrame({
    "competition_name": ["La Liga", "Ligue 1"],
    "season_name": ["2015/2016", "2021/2022"],
    "season_matches": [380, 26],
    "full_coverage": [True, False],
})


def _grid(rows):
    return pd.DataFrame(rows, columns=["position_group", "event_type", "count", "minutes",
                                       "competition_name", "season_name"])


def test_per90_arithmetic():
    g = finish_grid(_grid([["CB", "Tackle", 3, 270.0, "La Liga", "2015/2016"]]), COV, 900)
    assert g["per90"].iloc[0] == 1.0


def test_missing_count_becomes_zero():
    g = finish_grid(_grid([["CB", "Tackle", None, 900.0, "La Liga", "2015/2016"]]), COV, 900)
    assert g["count"].iloc[0] == 0 and g["per90"].iloc[0] == 0.0


def test_goalkeeper_only_ball_recovery_reportable():
    rows = [["GK", e, 1, 900.0, "La Liga", "2015/2016"] for e in ["Tackle", "Interception", "Ball Recovery"]]
    rows.append(["CB", "Tackle", 1, 900.0, "La Liga", "2015/2016"])
    g = finish_grid(_grid(rows), COV, 900)
    assert g["reportable"].tolist() == [False, False, True, True]


def test_meets_min_threshold():
    rows = [["CB", "Tackle", 1, 899.0, "La Liga", "2015/2016"],
            ["CB", "Tackle", 1, 900.0, "La Liga", "2015/2016"]]
    assert finish_grid(_grid(rows), COV, 900)["meets_min"].tolist() == [False, True]


def test_full_coverage_attached():
    rows = [["CB", "Tackle", 1, 900.0, "La Liga", "2015/2016"],
            ["CB", "Tackle", 1, 900.0, "Ligue 1", "2021/2022"]]
    assert finish_grid(_grid(rows), COV, 900)["full_coverage"].tolist() == [True, False]


def test_season_coverage_threshold():
    ev = pd.DataFrame({
        "match_id": [1, 2, 3, 9],
        "competition_name": ["A", "A", "A", "B"],
        "season_name": ["s"] * 4,
    })
    cov = season_coverage(ev, 3).set_index("competition_name")
    assert cov.loc["A", "season_matches"] == 3 and bool(cov.loc["A", "full_coverage"])
    assert not bool(cov.loc["B", "full_coverage"])