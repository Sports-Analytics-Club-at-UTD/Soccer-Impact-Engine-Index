"""Export D2C diagnostic JSON to an explicit new file outside this repository."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_match_scoped_metrics import audit_files
from src.provisional_profiles import build_profiles
import pyarrow.parquet as pq
from src.identity import PLAYER_KEYS


def validate_output(path):
    destination = Path(path).resolve()
    if destination.is_relative_to(ROOT) or destination.suffix.lower() != ".json":
        raise ValueError("Output must be a JSON path outside the repository")
    if not destination.parent.is_dir() or destination.exists():
        raise ValueError("Output parent must exist and output must be a new file")
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    for name in ("events", "crosswalk", "minutes", "lineups", "metadata"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--match-ids", nargs="+", type=int,
                        default=[3895107, 3895292, 3895320, 3895348])
    parser.add_argument("--scratch-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        output = validate_output(args.output)
        audit = audit_files(events_path=args.events, crosswalk_path=args.crosswalk,
            minutes_path=args.minutes, lineups_path=args.lineups, metadata_path=args.metadata,
            match_ids=args.match_ids, scratch_dir=args.scratch_dir)
        minutes = pq.read_table(args.minutes, columns=[*PLAYER_KEYS, "minutes"]).to_pandas()
        payload = build_profiles(audit, delivered_minutes=minutes)
        serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        # Exclusive creation also protects against an output appearing during the audit.
        validate_output(output)
        with output.open("x", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
    except (ValueError, OSError) as exc:
        print(f"Diagnostic export rejected: {exc}", file=sys.stderr)
        return 1
    print(f"Exported {len(payload['profiles'])} provisional profiles; no production attestation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
