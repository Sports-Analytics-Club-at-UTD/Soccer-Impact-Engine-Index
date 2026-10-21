"""Tests for the player_id keying in player_minutes.py (display names and crosswalk).
All rows below are made-up TEST FIXTURES. They never enter any metric or table."""

import pandas as pd

from src.metrics.player_minutes import build_crosswalk, display_names


def _lineups(rows):
    return pd.DataFrame(rows, columns=["player_id", "player_name_raw"])


def test_display_name_is_most_frequent_spelling():
    df = _lineups([(1, "Fernando Luiz Rosa")] * 3 + [(1, "Fernando Luiz Roza")])
    assert display_names(df).loc[1] == "Fernando Luiz Rosa"


def test_display_name_tie_goes_to_alphabetically_first():
    df = _lineups([(1, "Fernando Luiz Roza"), (1, "Fernando Luiz Rosa")])
    assert display_names(df).loc[1] == "Fernando Luiz Rosa"


def test_one_display_name_per_player_id():
    df = _lineups([(1, "A One"), (1, "A One"), (2, "B Two")])
    names = display_names(df)
    assert len(names) == 2
    assert names.loc[2] == "B Two"


def _played(rows):
    return pd.DataFrame(
        rows,
        columns=["player_id", "player_name_raw", "team", "competition_name", "season_name"],
    )


def test_crosswalk_keeps_every_spelling_with_same_id_and_no_clash():
    p = _played([
        (1, "Fernando Luiz Rosa", "T1", "L", "2015/2016"),
        (1, "Fernando Luiz Roza", "T1", "L", "2015/2016"),
        (1, "Fernando Luiz Rosa", "T1", "L", "2015/2016"),  # duplicate stint row
    ])
    xw, n_clash = build_crosswalk(p)
    assert len(xw) == 2
    assert set(xw["player_id"]) == {1}
    assert n_clash == 0


def test_crosswalk_counts_clash_when_one_spelling_maps_to_two_ids():
    p = _played([
        (1, "Same Name", "T1", "L", "2015/2016"),
        (2, "Same Name", "T1", "L", "2015/2016"),
    ])
    xw, n_clash = build_crosswalk(p)
    assert n_clash == 2


def test_same_name_on_different_teams_is_not_a_clash():
    p = _played([
        (1, "Same Name", "T1", "L", "2015/2016"),
        (2, "Same Name", "T2", "L", "2015/2016"),
    ])
    _, n_clash = build_crosswalk(p)
    assert n_clash == 0