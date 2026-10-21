"""Convert the SAC parquet file into src/data/players.json for the website.

Usage:
    pip install pandas pyarrow
    python scripts/parquet_to_json.py path/to/players.parquet

Browsers can't read parquet, so run this before each deploy and commit the
resulting JSON. Edit COLUMN_MAP so the right-hand names match YOUR columns.
The site expects PERCENTILES (0-100) vs positional peers, not raw counts.
"""
import json
import sys
from pathlib import Path

import pandas as pd

COLUMN_MAP = {
    # site field   : your parquet column
    "name": "player_name",
    "team": "team",
    "position": "position",      # must be "CB" or "DM"
    "minutes": "minutes_played",
    "T": "tackles_pct",
    "I": "interceptions_pct",
    "C": "clearances_pct",
    "P": "pressure_pct",         # playing under pressure
    "LB": "line_breaking_pct",
    "REC": "recoveries_pct",     # used by Sweeper / Ball-Winning Midfielder
}
PHOTO_COLUMN = None  # e.g. "photo_path" if you have one; otherwise placeholders show

OUT = Path(__file__).resolve().parent.parent / "src" / "data" / "players.json"


def main(path: str) -> None:
    df = pd.read_parquet(path)
    missing = [v for v in COLUMN_MAP.values() if v not in df.columns]
    if missing:
        sys.exit(f"Columns not found in parquet: {missing}\nAvailable: {list(df.columns)}")

    df = df[df[COLUMN_MAP["position"]].isin(["CB", "DM"])]  # GK etc. excluded
    rows = []
    for i, r in enumerate(df.to_dict("records"), start=1):
        rows.append({
            "id": i,
            "name": str(r[COLUMN_MAP["name"]]),
            "team": str(r[COLUMN_MAP["team"]]),
            "position": r[COLUMN_MAP["position"]],
            "minutes": int(r[COLUMN_MAP["minutes"]]),
            "photo": str(r[PHOTO_COLUMN]) if PHOTO_COLUMN else "",
            "pct": {k: round(float(r[COLUMN_MAP[k]]), 1) for k in ["T", "I", "C", "P", "LB", "REC"]},
        })
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"Wrote {len(rows)} players -> {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
