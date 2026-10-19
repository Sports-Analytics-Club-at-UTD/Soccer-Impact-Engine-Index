"""Unit tests for Press Resistance and Line-Breaking Pass Value.
Tiny synthetic tables (made-up rows to test the CODE, not football facts)."""
import numpy as np
import pandas as pd

from src.metrics.line_breaking import (
    add_difficulty, build_table as lb_table, coverage_360, flag_progressive, level_a_counts,
    level_b_counts, opponents_bypassed, orientation_check, prepare_passes,
)
from src.metrics.press_resistance import (
    build_table as pr_table, classify_pressured_actions, pressure_counts, progressive_pressured_carries,
)
from src.metrics.scoring_common import distance_to_goal

BASE = dict(match_id=1, team="A", player="P1", competition_name="L", season_name="S",
            under_pressure=None, pass_outcome=None, pass_type=None, dribble_outcome=None,
            location=[50, 40], carry_end_location=None, pass_end_location=None, pass_length=None)


def _ev(rows):
    return pd.DataFrame([{**BASE, "id": f"e{i}", **r} for i, r in enumerate(rows)])


def _minutes(rows):
    return pd.DataFrame(rows, columns=["player", "team", "competition_name", "season_name",
                                       "position_group", "matches", "minutes"])


def _cov(full=True):
    return pd.DataFrame({"competition_name": ["L"], "season_name": ["S"],
                         "season_matches": [380], "full_coverage": [full]})


# ---------- geometry ----------
def test_distance_to_goal():
    assert distance_to_goal([120], [40])[0] == 0
    assert distance_to_goal([60], [40])[0] == 60


# ---------- press resistance ----------
def _pressure_events():
    return _ev([
        dict(type="Pass", under_pressure=True),                                    # retained
        dict(type="Pass", under_pressure=True, pass_outcome="Incomplete"),         # lost
        dict(type="Pass", under_pressure=True, pass_outcome="Unknown"),            # excluded
        dict(type="Pass", under_pressure=None),                                    # not pressured
        dict(type="Pass", under_pressure=True, pass_type="Corner"),                # set piece
        dict(type="Dribble", dribble_outcome="Complete"),                          # retained
        dict(type="Dribble", dribble_outcome="Incomplete"),                        # lost
        dict(type="Miscontrol", under_pressure=True),                              # lost
        dict(type="Miscontrol"),                                                   # not pressured
        dict(type="Dispossessed"),                                                 # lost
        dict(type="Carry", under_pressure=True, carry_end_location=[65, 40]),      # prog carry
        dict(type="Carry", under_pressure=True, carry_end_location=[55, 40]),      # too short
        dict(type="Carry", carry_end_location=[90, 40]),                           # not pressured
    ])


def test_classify_pressured_actions():
    a = classify_pressured_actions(_pressure_events())
    got = a.groupby(["action", "retained"]).size().to_dict()
    assert got == {("Pass", True): 1, ("Pass", False): 1, ("Dribble", True): 1,
                   ("Dribble", False): 1, ("Miscontrol", False): 1, ("Dispossessed", False): 1}


def test_progressive_pressured_carries():
    assert len(progressive_pressured_carries(_pressure_events())) == 1


def test_press_table_rates_and_rules():
    ev = _pressure_events()
    counts = pressure_counts(classify_pressured_actions(ev), progressive_pressured_carries(ev))
    base = _minutes([("P1", "A", "L", "S", "DM", 10, 900.0),
                     ("P2", "A", "L", "S", "CB", 10, 900.0)])        # P2 has no events -> zeros
    df = pr_table(counts, base, _cov(), min_minutes=900, min_actions=2).set_index("player")
    assert df.loc["P1", "pr_actions"] == 6
    assert np.isclose(df.loc["P1", "pr_retention_rate"], 2 / 6)
    assert np.isclose(df.loc["P1", "pr_actions_p90"], 6 * 90 / 900)
    assert np.isclose(df.loc["P1", "pr_prog_carries_p90"], 90 / 900)
    assert df.loc["P2", "pr_actions"] == 0 and np.isnan(df.loc["P2", "pr_retention_rate"])
    assert df.loc["P2", "rate_note"].startswith("N/A")


def test_press_goalkeeper_passes_only():
    ev = _pressure_events().assign(player="G1")
    counts = pressure_counts(classify_pressured_actions(ev), progressive_pressured_carries(ev))
    base = _minutes([("G1", "A", "L", "S", "GK", 10, 900.0)])
    df = pr_table(counts, base, _cov(), min_minutes=900, min_actions=1).iloc[0]
    assert df["pr_actions"] == 2 and np.isclose(df["pr_retention_rate"], 0.5)
    assert np.isnan(df["pr_prog_carries_p90"])


def test_press_single_club_season_has_no_percentile():
    ev = _pressure_events()
    counts = pressure_counts(classify_pressured_actions(ev), progressive_pressured_carries(ev))
    base = _minutes([("P1", "A", "L", "S", "DM", 10, 900.0)])
    df = pr_table(counts, base, _cov(full=False), min_minutes=900, min_actions=1).iloc[0]
    assert np.isnan(df["pctl_pr_retention_rate"]) and df["na_reason"].startswith("N/A: single-club")


# ---------- line breaking, level A ----------
def _pass_events():
    return _ev([
        dict(type="Pass", location=[30, 40], pass_end_location=[70, 40]),                  # progressive, crosses third
        dict(type="Pass", location=[30, 40], pass_end_location=[70, 40], pass_outcome="Incomplete"),  # attempt only
        dict(type="Pass", location=[100, 40], pass_end_location=[105, 40]),                # < 10 yards forward
        dict(type="Pass", location=[50, 40], pass_end_location=[30, 40]),                  # backwards
        dict(type="Pass", location=[40, 40], pass_end_location=[70, 40], pass_type="Free Kick"),  # set piece
        dict(type="Pass", location=[45, 40], pass_end_location=[75, 40], pass_type="Recovery"),   # open play, same third
        dict(type="Pass", location=None, pass_end_location=[70, 40]),                      # no location -> dropped
    ])


def test_progressive_flags():
    p = flag_progressive(add_difficulty(prepare_passes(_pass_events())))
    assert len(p) == 5
    assert p["prog_attempt"].sum() == 3
    assert p["progressive"].sum() == 2
    assert p["third_cross"].sum() == 1          # 30->70 crosses x = 40; 45->75 stays in the middle third
    assert (p.loc[~p["progressive"], "pass_value"] == 0).all()


def test_pass_value_uses_distance_and_difficulty():
    p = flag_progressive(add_difficulty(prepare_passes(_pass_events())))
    row = p[p["progressive"]].iloc[0]
    assert np.isclose(row["pass_value"], (row["d0"] - row["d1"]) * (1 - row["p_hat"]))


def test_level_a_table():
    p = flag_progressive(add_difficulty(prepare_passes(_pass_events())))
    base = _minutes([("P1", "A", "L", "S", "CB", 10, 900.0)])
    df = lb_table(level_a_counts(p), base, _cov(), min_minutes=900).iloc[0]
    assert np.isclose(df["prog_passes_p90"], 2 * 90 / 900)
    assert np.isclose(df["prog_completion_pct"], 100 * 2 / 3)
    assert df["lb_note"] == "N/A: 360 data not loaded"


# ---------- line breaking, level B ----------
def _frames():
    rows = [
        # pass e0 (x 30 -> 70): opponents at 50, 60, 65 between; 80 beyond; keeper and teammate ignored
        ("e0", False, False, False, [50, 30]), ("e0", False, False, False, [60, 30]),
        ("e0", False, False, False, [65, 30]), ("e0", False, False, False, [80, 30]),
        ("e0", False, True, False, [55, 40]), ("e0", True, False, False, [55, 20]),
        ("e0", True, False, True, [30, 40]),
        # pass e5 (x 45 -> 75): one opponent between
        ("e5", False, False, False, [60, 30]), ("e5", True, False, True, [45, 40]),
    ]
    f = pd.DataFrame(rows, columns=["id", "teammate", "keeper", "actor", "location"])
    f["match_id"] = 1
    return f


def test_opponents_bypassed_and_line_break():
    p = flag_progressive(add_difficulty(prepare_passes(_pass_events())))
    b = opponents_bypassed(p, _frames(), min_bypassed=3).set_index("id")
    assert b.loc["e0", "opponents_bypassed"] == 3 and b.loc["e0", "line_break"]
    assert b.loc["e5", "opponents_bypassed"] == 1 and not b.loc["e5", "line_break"]
    assert not b.loc["e2", "has_frame"] and np.isnan(b.loc["e2", "opponents_bypassed"])


def test_orientation_check_zero_when_aligned():
    p = prepare_passes(_pass_events())
    assert orientation_check(p, _frames()) == 0


def test_level_b_table_requires_full_360_season():
    ev = _pass_events()
    p = flag_progressive(add_difficulty(prepare_passes(ev)))
    frames = _frames()
    b = level_b_counts(opponents_bypassed(p, frames))
    base = _minutes([("P1", "A", "L", "S", "CB", 10, 900.0)])
    df = lb_table(level_a_counts(p), base, _cov(), b, coverage_360(ev, frames)).iloc[0]
    assert df["lb_note"] == "ok" and np.isclose(df["line_breaks_p90"], 90 / 900)

    cov_partial = coverage_360(ev, frames).assign(share_360=0.5, full_360=False)
    df = lb_table(level_a_counts(p), base, _cov(), b, cov_partial).iloc[0]
    assert np.isnan(df["line_breaks_p90"]) and df["lb_note"].startswith("N/A")
