"""Explicitly bounded public-source pilot; exclusive writes, never delivered outputs.

Run inventory first, then records with an explicit JSON list of at most eight IDs.
No credentials, season event collection, scoring or trust promotion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

LEAGUES = ("La Liga", "Premier League", "Serie A", "Ligue 1")


def write_new(path, payload):
    with Path(path).open("xb") as stream:
        stream.write(payload)


def save_json(path, value):
    write_new(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def fetch(root, url, name, *, revision=None, context=None):
    """Record current request outcomes, never historical delivery outcomes."""
    path = root / name
    if path.exists() or (root / (name + ".request.json")).exists():
        raise FileExistsError(path)
    record = dict(url=url, retrieved_at=datetime.now(timezone.utc).isoformat(),
                  provider_revision=revision, context=context)
    try:
        with urllib.request.urlopen(url, timeout=45) as response:
            payload = response.read(20 * 1024 * 1024 + 1)
            if len(payload) > 20 * 1024 * 1024:
                raise ValueError("bounded response size exceeded")
            record.update(status=response.status, headers=dict(response.headers))
        write_new(path, payload)
        record.update(outcome="success", size_bytes=len(payload),
                      sha256=hashlib.sha256(payload).hexdigest())
    except Exception as exc:
        record.update(outcome="failure", error=f"{type(exc).__name__}: {exc}")
        save_json(root / (name + ".request.json"), record)
        return None
    save_json(root / (name + ".request.json"), record)
    return payload


def inventory(root):
    root.mkdir(parents=True, exist_ok=False)
    commit = fetch(root, "https://api.github.com/repos/statsbomb/open-data/commits/master", "revision.json")
    if commit is None:
        return
    revision = json.loads(commit)["sha"]
    base = f"https://raw.githubusercontent.com/statsbomb/open-data/{revision}"
    for name in ("README.md", "LICENSE.pdf"):
        fetch(root, base + "/" + name, name, revision=revision)
    listing = fetch(root, f"https://api.github.com/repos/statsbomb/open-data/contents/doc?ref={revision}", "documentation-index.json", revision=revision)
    if listing:
        for item in json.loads(listing):
            if item["type"] == "file" and item["name"].lower().endswith(".pdf"):
                fetch(root, base + "/doc/" + item["name"].replace(" ", "%20"), item["name"], revision=revision)
    pycommit = fetch(root, "https://api.github.com/repos/statsbomb/statsbombpy/commits/master", "client-revision.json")
    if pycommit:
        pyrev = json.loads(pycommit)["sha"]
        for name in ("config.py", "public.py", "sb.py"):
            fetch(root, f"https://raw.githubusercontent.com/statsbomb/statsbombpy/{pyrev}/statsbombpy/{name}", "client-" + name, revision=pyrev)
    competitions = fetch(root, base + "/data/competitions.json", "competitions.json", revision=revision)
    fixtures, scope = [], []
    for league in LEAGUES:
        rows = [c for c in json.loads(competitions or b"[]") if c["competition_name"] == league and c["season_name"] == "2015/2016"]
        if len(rows) != 1:
            raise ValueError(f"ambiguous/missing competition: {league}")
        c = rows[0]
        payload = fetch(root, base + f'/data/matches/{c["competition_id"]}/{c["season_id"]}.json', f'matches-{c["competition_id"]}-{c["season_id"]}.json', revision=revision, context=c)
        if payload is None:
            continue
        for match in json.loads(payload):
            fixtures.append(dict(match_id=match["match_id"], competition_name=c["competition_name"], season_name=c["season_name"], home_team=match["home_team"]["home_team_name"], away_team=match["away_team"]["away_team_name"]))
        scope.append(dict(competition_name=league, season_name="2015/2016", coverage_claim="provider_list"))
    save_json(root / "fixtures-normalized.json", fixtures)
    save_json(root / "fixtures-provenance.json", dict(schema_version="fixture-evidence/v1", artifact_kind="fixture_snapshot", provider="StatsBomb Open Data", source_reference=base + "/data/matches/", origin="provider_fixture_records", match_id_namespace="statsbomb", source_revision=revision, retrieved_on=datetime.now(timezone.utc).date().isoformat(), sha256=hashlib.sha256((root / "fixtures-normalized.json").read_bytes()).hexdigest(), scope=scope))


def records(root, selection):
    ids = json.loads(Path(selection).read_text())
    if not isinstance(ids, list) or len(ids) > 8 or len(set(ids)) != len(ids) or any(type(i) is not int or i <= 0 for i in ids):
        raise ValueError("explicit unique list of at most eight positive match IDs required")
    if list(root.glob("events-*.json")) or list(root.glob("lineups-*.json")):
        raise ValueError("sample already attempted; no automatic expansion")
    revision = json.loads((root / "revision.json").read_text())["sha"]
    fixtures = {r["match_id"]: r for r in json.loads((root / "fixtures-normalized.json").read_text())}
    if not set(ids) <= fixtures.keys():
        raise ValueError("sample outside independently retrieved inventory")
    for mid in ids:
        for kind in ("events", "lineups"):
            fetch(root, f"https://raw.githubusercontent.com/statsbomb/open-data/{revision}/data/{kind}/{mid}.json", f"{kind}-{mid}.json", revision=revision, context=fixtures[mid])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inventory", "records"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selection")
    args = parser.parse_args()
    if args.mode == "inventory":
        inventory(args.root)
    else:
        records(args.root, args.selection)


if __name__ == "__main__":
    main()
