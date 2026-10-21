import pandas as pd

from src.metrics.player_names import clean_player


def test_doubled_apostrophe_collapsed():
    out = clean_player(pd.Series(["N''Golo Kanté", "N'Golo Kanté"]))
    assert out.tolist() == ["N'Golo Kanté", "N'Golo Kanté"]


def test_trailing_tab_stripped():
    assert clean_player(pd.Series(["Daniel Arnaud N''Di\t"])).iloc[0] == "Daniel Arnaud N'Di"


def test_missing_stays_missing():
    out = clean_player(pd.Series(["Eunan O''Kane", None]))
    assert out.isna().tolist() == [False, True]


def test_no_space_is_not_invented():
    assert clean_player(pd.Series(["DaniloD''Ambrosio"])).iloc[0] == "DaniloD'Ambrosio"