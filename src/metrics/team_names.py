"""Team-name cleaning shared by the metric scripts.

StatsBomb uses two different names for the same club in some data. In Ligue 1 2015/2016 the
events file lists both 'Marseille' and 'Olympique de Marseille', and both 'Caen' and
'Stade Malherbe Caen'. Left alone, a player's season is split across two team keys, which
splits their minutes and their event counts.

This maps each pair to one name. It is an ASSUMPTION about identity (the two names are the
same club). It was checked by confirming the two names never appear in the same match.

Ligue 1 2022/2023 lists 21 team names; the extra name is the same Marseille pair (one match
each), already covered by the mapping above. The two Marseille names never share a match
anywhere in the events file.

If another duplicate is found, add it here and rerun player_minutes and recovery_per90.
"""

TEAM_ALIASES = {
    "Marseille": "Olympique de Marseille",
    "Caen": "Stade Malherbe Caen",
}


def clean_team(series):
    """Return a pandas Series of team names with duplicates mapped to one name."""
    return series.replace(TEAM_ALIASES)