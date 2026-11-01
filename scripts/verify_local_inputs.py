"""Read-only checksum receipt for separately authorized local runtime inputs.

This verifies bytes, never recipient permission, publication approval or scores.
The runtime adapter independently enforces its existing frozen pins.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(root, inventory):
    result = []
    for item in inventory:
        path = root / item["path"]
        status = "missing"
        if path.is_file():
            with path.open("rb") as stream:
                sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
            status = "match" if path.stat().st_size == item["bytes"] and sha256 == item["sha256"] else "MISMATCH"
        result.append({"path": item["path"], "status": status})
    return result


def main():
    inventory = json.loads((ROOT / "docs/private-runtime-checksums.json").read_text(encoding="utf-8"))
    results = verify(ROOT, inventory)
    print(json.dumps({"inputs": results, "all_match": all(r["status"] == "match" for r in results),
                      "publication_authorized_by_this_check": False}, indent=2))
    return 0 if all(r["status"] == "match" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
