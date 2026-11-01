"""Run reviewed public/private cases; missing sources or cases fail explicitly.

Use: python -B -m scripts.run_backend_tests public|private|all [pytest options]
The inventory preserves private checks and maps 42 unchanged synthetic copies.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


class SuiteBoundary:
    def __init__(self, suite, inventory):
        self.suite = suite
        self.expected = set(inventory["public"] if suite == "public" else inventory["private"] if suite == "private" else inventory["public"] + inventory["private"])
        self.known = set(inventory["public"] + inventory["private"]) | {r["legacy"] for r in inventory["legacy_equivalents"]}

    def pytest_collection_modifyitems(self, config, items):
        import pytest
        collected = {item.nodeid for item in items}
        unknown, missing = collected - self.known, self.expected - collected
        if unknown or missing:
            raise pytest.UsageError("Test inventory mismatch; review source/catalog, never silently reduce coverage. "
                                    + "Missing: " + repr(sorted(missing)) + "; unknown: " + repr(sorted(unknown)))
        selected = [item for item in items if item.nodeid in self.expected]
        deselected = [item for item in items if item.nodeid not in self.expected]
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
        print(f"\nBackend suite {self.suite}: {len(selected)} inventoried cases; {len(deselected)} outside this selection.")

    def pytest_sessionfinish(self, session, exitstatus):
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter and reporter.stats.get("skipped"):
            print("Inventoried verification skipped required cases; acceptance is incomplete.")
            session.exitstatus = 1


def main():
    import pytest
    suite = sys.argv[1] if len(sys.argv) > 1 else "all"
    if suite not in ("all", "public", "private"):
        raise SystemExit("Expected all, public or private")
    if Path.cwd() != ROOT:
        raise SystemExit("Run from the repository root; relative private fixture paths are intentional.")
    inventory = json.loads((ROOT / "tests/suite_inventory.json").read_text(encoding="utf-8"))
    if inventory.get("schema_version") != 1:
        raise SystemExit("Unsupported test inventory")
    boundary = SuiteBoundary(suite, inventory)
    paths = sorted({nodeid.split("::", 1)[0] for nodeid in boundary.expected})
    missing = [path for path in paths if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit("Missing required " + suite + " test source: " + ", ".join(missing)
                         + ". Private source/evidence must be separately authorized; no substitution or skip.")
    if suite in ("all", "private"):
        for name, expected in inventory["private_source_sha256"].items():
            path = ROOT / name
            if not path.is_file():
                raise SystemExit("Missing authorized private verification source: " + name)
            actual = hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
            if actual != expected:
                raise SystemExit("Private verification source differs from reviewed fingerprint: " + name)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    return pytest.main([*paths, "-p", "no:cacheprovider", *sys.argv[2:]], plugins=[boundary])


if __name__ == "__main__":
    raise SystemExit(main())
