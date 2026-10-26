import numpy as np
import pandas as pd
import pytest

from src.metrics.recovery_scores import score_recovery


def make_row(player_id, position_group="CB", event_type="Tackle", per90=1.0,
             reportable=True, meets_min=True, full_coverage=True,
             season_name="2015/2016"):
    return {
        "player_id": player_id,
        "position_group": position_group,
        "event_type": event_type,
        "per90": per90,
        "reportable": reportable,
        "meets_min": meets_min,
        "full_coverage": full_coverage,
        "season_name": season_name,
    }


def run(rows):
    return score_recovery(pd.DataFrame(rows))


def test_dm_and_cm_share_one_pool_and_cb_is_separate():
    rows = [
        make_row(1, "DM", per90=1), make_row(2, "CM", per90=2),
        make_row(3, "DM", per90=3), make_row(4, "CM", per90=4),
        make_row(5, "CB", per90=1), make_row(6, "CB", per90=2), make_row(7, "CB", per90=3),
    ]
    out = run(rows).set_index("player_id")
    assert (out.loc[[1, 2, 3, 4], "score_group"] == "MID").all()
    assert (out.loc[[1, 2, 3, 4], "pool_n"] == 4).all()
    assert (out.loc[[5, 6, 7], "pool_n"] == 3).all()
    assert out.loc[1, "percentile"] == 25.0
    assert out.loc[4, "percentile"] == 100.0


def test_goalkeeper_tackle_is_na_but_goalkeeper_ball_recovery_is_scored():
    rows = [
        make_row(1, "GK", "Tackle", per90=0.1, reportable=False),
        make_row(2, "GK", "Ball Recovery", per90=1.0),
        make_row(3, "GK", "Ball Recovery", per90=2.0),
    ]
    out = run(rows).set_index("player_id")
    assert np.isnan(out.loc[1, "percentile"])
    assert out.loc[1, "tier"] == "N/A"
    assert out.loc[1, "score_note"].startswith("N/A: goalkeeper")
    assert out.loc[2, "score_group"] == "GK"
    assert out.loc[2, "score_note"] == "ok"
    assert out.loc[3, "percentile"] == 100.0


def test_below_minimum_minutes_is_na():
    rows = [make_row(1, per90=1), make_row(2, per90=2),
            make_row(3, per90=9, meets_min=False)]
    out = run(rows).set_index("player_id")
    assert np.isnan(out.loc[3, "percentile"])
    assert out.loc[3, "tier"] == "N/A"
    assert out.loc[3, "score_note"] == "N/A: below minimum minutes"


def test_ineligible_rows_do_not_change_the_pool():
    eligible = [make_row(i, per90=float(i)) for i in range(1, 21)]
    extras = [
        make_row(100, per90=1000.0, full_coverage=False),
        make_row(101, per90=500.0, meets_min=False),
    ]
    out = run(eligible + extras).set_index("player_id")
    assert (out.loc[list(range(1, 21)), "pool_n"] == 20).all()
    assert out.loc[20, "percentile"] == 100.0
    assert out.loc[100, "score_note"] == "N/A: single-club season, not in reference pool"
    assert out.loc[100, "tier"] == "N/A"
    assert out.loc[101, "score_note"] == "N/A: below minimum minutes"


def test_tier_boundaries_gold_90_silver_75():
    # 20 players, per90 = id, so percentile = id x 5 (5, 10, ..., 100)
    out = run([make_row(i, per90=float(i)) for i in range(1, 21)]).set_index("player_id")
    assert out.loc[14, "tier"] == "none"    # 70
    assert out.loc[15, "tier"] == "Silver"  # exactly 75
    assert out.loc[17, "tier"] == "Silver"  # 85
    assert out.loc[18, "tier"] == "Gold"    # exactly 90
    assert out.loc[20, "tier"] == "Gold"    # 100


def test_three_event_types_are_scored_separately():
    rows = []
    for i in range(1, 21):
        rows.append(make_row(i, event_type="Tackle", per90=float(i)))
        rows.append(make_row(i, event_type="Interception", per90=float(21 - i)))
    out = run(rows).set_index(["player_id", "event_type"])
    assert len(out) == 40  # no rows merged or blended
    assert out.loc[(20, "Tackle"), "tier"] == "Gold"
    assert out.loc[(20, "Interception"), "tier"] == "none"
    assert out.loc[(1, "Tackle"), "tier"] == "none"
    assert out.loc[(1, "Interception"), "tier"] == "Gold"


def test_rating_constant_pool_is_65():
    out = run([make_row(i, per90=2.0) for i in range(1, 6)])
    assert (out["rating"] == 65.0).all()


def test_rating_is_clipped_to_99():
    rows = [make_row(i, per90=1.0) for i in range(1, 20)] + [make_row(20, per90=100.0)]
    out = run(rows).set_index("player_id")
    assert out.loc[20, "rating"] == 99.0
    assert out["rating"].min() >= 1.0


def test_rating_mean_65_and_spread_10_when_not_clipped():
    out = run([make_row(i, per90=float(i)) for i in range(1, 21)])
    assert out["rating"].mean() == pytest.approx(65.0)
    assert out["rating"].std() == pytest.approx(10.0)