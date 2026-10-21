"""Player-name cleaning (same idea as team_names.py)."""


def clean_player(names):
    """Collapse doubled apostrophes ('' -> ') and strip surrounding whitespace.
    Missing names stay missing."""
    out = names.astype(str).str.replace("''", "'", regex=False).str.strip()
    return out.where(names.notna())