"""Unit tests on tiny synthetic tables (made-up rows to test the CODE, not football facts)."""
import numpy as np
import pandas as pd

from recovery_coverage import add_per90, extract_recovery_events, recovery_counts
from spatial_dominance import observed_spatial_dominance, team_control
from zones import assign_zone, zone_xband

FULL_PITCH = [0, 0, 120, 0, 120, 80, 0, 80]
LEFT_HALF = [0, 0, 60, 0, 60, 80, 0, 80]


# ---------- zones ----------
def test_zone_ids_and_edges():
    z = assign_zone([0, 119, 120, 40, 0], [0, 79, 80, 0, 79])
    assert list(z) == [1, 9, 9, 2, 7]


def test_zone_missing_or_off_pitch_is_na():
    z = assign_zone([np.nan, -1, 10], [5, 5, 100])
    assert z.isna().all()


# ---------- recovery coverage ----------
def _events():
    base = dict(match_id=1, team="A", player_id=1, player="P1", location=None, duel_type=None,
                duel_outcome=None, interception_outcome=None, ball_recovery_recovery_failure=None)
    rows = [
        dict(type="Duel", duel_type="Tackle", duel_outcome="Won", location=[10, 10]),            # counted
        dict(type="Duel", duel_type="Tackle", duel_outcome="Lost In Play", location=[10, 10]),   # lost -> no
        dict(type="Duel", duel_type="Aerial Lost", duel_outcome="Lost", location=[10, 10]),      # not a tackle
        dict(type="Interception", interception_outcome="Won", location=[60, 40]),                # counted
        dict(type="Ball Recovery", ball_recovery_recovery_failure=False, location=[30, 70]),     # counted
        dict(type="Ball Recovery", ball_recovery_recovery_failure=True, location=[30, 70]),      # failed -> no
        dict(type="Pass", location=[50, 40]),                                                    # ignored
        dict(type="Duel", duel_type="Tackle", duel_outcome="Won", location=None),                # counted, no zone
    ]
    return pd.DataFrame([{**base, **r} for r in rows])


def test_three_event_types_stay_separate_and_correct():
    rec = extract_recovery_events(_events())
    assert set(rec["event_type"]) == {"Tackle", "Interception", "Ball Recovery"}
    totals, by_zone = recovery_counts(rec)
    c = totals.set_index("event_type")["count"].to_dict()
    assert c == {"Tackle": 2, "Interception": 1, "Ball Recovery": 1}
    # event with no location is in totals but not in the zone breakdown
    z = by_zone.groupby("event_type")["count"].sum().to_dict()
    assert z["Tackle"] == 1


def test_per90_and_na_without_minutes():
    rec = extract_recovery_events(_events())
    totals, _ = recovery_counts(rec)
    on = ["player_id", "player", "team"]
    minutes = pd.DataFrame([dict(player_id=1, player="P1", team="A", minutes=180.0)])
    out = add_per90(totals, minutes, on).set_index("event_type")
    assert out.loc["Tackle", "per90"] == 1.0
    # player with no minutes row -> NaN, not a guess
    other = totals.assign(player_id=2)
    out2 = add_per90(other, minutes, on)
    assert out2["per90"].isna().all()


# ---------- spatial dominance ----------
def _frame(fid, players):
    """players: list of (teammate, x, y)"""
    return [dict(id=fid, match_id=1, visible_area=VA[fid], teammate=t, actor=False, keeper=False,
                 location=[x, y]) for t, x, y in players]


VA = {"e1": FULL_PITCH, "e2": FULL_PITCH, "e3": FULL_PITCH, "e4": LEFT_HALF}


def _events_for_spatial():
    return pd.DataFrame([
        dict(id="e1", match_id=1, team="A", possession_team="A"),  # actor attacks
        dict(id="e2", match_id=1, team="B", possession_team="A"),  # actor defends
        dict(id="e3", match_id=1, team="A", possession_team="A"),
        dict(id="e4", match_id=1, team="B", possession_team="A"),
        dict(id="x", match_id=1, team="B", possession_team="B"),   # makes sure both teams are in the match
    ])


def _rate_by_xband(res):
    tc = team_control(res)
    tc["xband"] = zone_xband(tc["zone"])
    g = tc.groupby("xband")[["defender_cells", "observed_cells"]].sum()
    return (g["defender_cells"] / g["observed_cells"]).to_dict()


def test_orientation_flip_gives_same_answer_for_either_actor_side():
    # e1: actor is the ATTACKER (A) -> frame must be mirrored. B (defender) sits at raw x=110.
    f1 = pd.DataFrame(_frame("e1", [(True, 50, 40), (False, 110, 40)]))
    # e2: actor is the DEFENDER (B) -> no mirror. B at x=10, A at x=70. Same situation.
    f2 = pd.DataFrame(_frame("e2", [(True, 10, 40), (False, 70, 40)]))
    ev = _events_for_spatial()

    r1, s1 = observed_spatial_dominance(f1, ev)
    r2, s2 = observed_spatial_dominance(f2, ev)
    assert s1["frames_used"] == 1 and s2["frames_used"] == 1
    assert set(r1["defending_team"]) == {"B"} and set(r2["defending_team"]) == {"B"}

    expected = {0: 1.0, 1: 0.0, 2: 0.0}  # defender owns its own third, nothing beyond the bisector at x=40
    assert _rate_by_xband(r1) == expected
    assert _rate_by_xband(r2) == expected


def test_unobserved_zones_are_na_not_zero():
    # only the left half of the pitch is visible -> attacking third (x band 2) must have NO rows
    f = pd.DataFrame(_frame("e4", [(True, 10, 40), (False, 70, 40)]))
    res, _ = observed_spatial_dominance(f, _events_for_spatial())
    assert 2 not in set(zone_xband(res["zone"]))
    assert _rate_by_xband(res) == {0: 1.0, 1: 0.0}


def test_one_sided_frame_is_skipped():
    f = pd.DataFrame(_frame("e3", [(True, 50, 40), (True, 60, 20)]))  # only the actor's team visible
    res, stats = observed_spatial_dominance(f, _events_for_spatial())
    assert res.empty
    assert stats["skipped_one_side_only"] == 1