"""Bounded offline fixture comparisons. No trust promotion, event scan or writes."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sys

import pandas as pd
import pyarrow.parquet as pq

from src.identity import _ids, normalize_team_names

LEAGUES = ("La Liga", "Premier League", "Serie A", "Ligue 1")
SEASON = "2015/2016"
CONTEXT = ("match_id", "competition_name", "season_name")
TEAMS = ("home_team", "away_team")
MAX_ROWS = 200_000
MAX_JSON_BYTES = 16 * 1024 * 1024
MISSING_SNAPSHOT = "NOT VERIFIED — SOURCE SNAPSHOT MISSING"
CLAIM = {
    "match_id": 3879594, "competition_name": "Serie A", "season_name": SEASON,
    "status": "CONTRIBUTOR-REPORTED FIXTURE CLAIM",
    "reported_cause": "events-fetch connection reset",
    "reference": "origin/arpit-dev@9d53c04be0d687ba6f6650deac6ca89784557246:docs/metric_documentation.md section 1.3",
}


class FixtureEvidenceError(ValueError):
    """Malformed or contradictory declarations; never infer source trust."""


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise FixtureEvidenceError(f"{label}: nonblank text required")
    return value


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise FixtureEvidenceError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _path(value):
    path = Path(value)
    if not path.is_file():
        raise FixtureEvidenceError(f"local input file unavailable: {path}")
    return path


def _json(path):
    if path.stat().st_size > MAX_JSON_BYTES:
        raise FixtureEvidenceError("JSON input exceeds bounded read limit")
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream, object_pairs_hook=_object,
                         parse_constant=lambda value: (_ for _ in ()).throw(
                             FixtureEvidenceError(f"nonfinite JSON value: {value}")))


def fingerprint(path):
    with _path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_records(path, required, optional=()):
    """JSON record arrays or projected Parquet only; never read event payloads."""
    path = _path(path)
    if path.suffix.lower() == ".parquet":
        file = pq.ParquetFile(path)
        if file.metadata.num_rows > MAX_ROWS:
            raise FixtureEvidenceError("Parquet row cap exceeded; event scans are unsupported")
        names = file.schema_arrow.names
        if len(names) != len(set(names)) or not set(required).issubset(names):
            raise FixtureEvidenceError("missing or duplicate Parquet columns")
        columns = [c for c in (*required, *optional) if c in names]
        return file.read(columns=columns).to_pylist()
    if path.suffix.lower() != ".json":
        raise FixtureEvidenceError("input must be local .json or .parquet")
    rows = _json(path)
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise FixtureEvidenceError("bounded JSON record array required")
    if any(not isinstance(row, dict) or not set(required).issubset(row) for row in rows):
        raise FixtureEvidenceError("record missing required columns")
    return rows


def provenance(path, artifact, kind):
    """Check declarations and byte binding, not provider identity/independence."""
    value = _json(_path(path))
    required = {"schema_version", "artifact_kind", "provider", "source_reference", "origin", "sha256", "match_id_namespace"}
    allowed = required | {"retrieved_on", "source_revision", "scope"}
    if not isinstance(value, dict) or not required.issubset(value) or set(value) - allowed:
        raise FixtureEvidenceError("incomplete/unsupported provenance fields")
    if value["schema_version"] != "fixture-evidence/v1" or value["artifact_kind"] != kind:
        raise FixtureEvidenceError("conflicting provenance artifact kind/version")
    for field in ("provider", "source_reference"):
        _text(value[field], field)
    if value["match_id_namespace"] != "statsbomb":
        raise FixtureEvidenceError("explicit StatsBomb match IDs required; no cross-provider ID inference")
    origins = {"provider_fixture_records", "event_derived", "synthetic"} if kind == "fixture_snapshot" else {"acquisition_log", "synthetic"}
    if value["origin"] not in origins:
        raise FixtureEvidenceError("unsupported provenance origin; source labels do not establish independence")
    if not value.get("retrieved_on") and not value.get("source_revision"):
        raise FixtureEvidenceError("retrieval date or source revision required")
    if "retrieved_on" in value:
        try:
            date.fromisoformat(_text(value["retrieved_on"], "retrieved_on"))
        except ValueError as exc:
            raise FixtureEvidenceError("retrieved_on must be an ISO date") from exc
    if "source_revision" in value:
        _text(value["source_revision"], "source_revision")
    if not isinstance(value["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", value["sha256"]):
        raise FixtureEvidenceError("lowercase SHA256 fingerprint required")
    if value["sha256"] != fingerprint(artifact):
        raise FixtureEvidenceError("source file fingerprint conflicts with provenance")
    if kind == "fixture_snapshot":
        scope = value.get("scope")
        if not isinstance(scope, list) or not scope:
            raise FixtureEvidenceError("explicit nonempty snapshot scope required")
        keys = []
        for row in scope:
            if not isinstance(row, dict) or set(row) != {"competition_name", "season_name", "coverage_claim"}:
                raise FixtureEvidenceError("invalid snapshot scope record")
            if row["competition_name"] not in LEAGUES or row["season_name"] != SEASON:
                raise FixtureEvidenceError("snapshot scope outside target leagues/season")
            if row["coverage_claim"] not in ("partial", "provider_list", "full_competition_claimed", "unknown"):
                raise FixtureEvidenceError("unsupported snapshot coverage claim")
            keys.append(row["competition_name"])
        if len(keys) != len(set(keys)):
            raise FixtureEvidenceError("duplicate/conflicting provenance scope")
        value = {**value, "scope": sorted(scope, key=lambda r: LEAGUES.index(r["competition_name"]))}
    elif "scope" in value:
        raise FixtureEvidenceError("acquisition provenance must not declare fixture coverage")
    return value


@lru_cache(maxsize=MAX_ROWS, typed=True)
def _id(value):
    try:
        return int(_ids(pd.Series([value]), "match_id").iloc[0])
    except ValueError as exc:
        raise FixtureEvidenceError(str(exc)) from exc


@lru_cache(maxsize=MAX_ROWS, typed=True)
def _team(value):
    try:
        return str(normalize_team_names(pd.Series([_text(value, "team")])).iloc[0])
    except ValueError as exc:
        raise FixtureEvidenceError(str(exc)) from exc


def fixtures(rows, label):
    """Account for duplicate records; quarantine conflicting IDs without selection."""
    grouped = defaultdict(list)
    for row in rows:
        mid = _id(row["match_id"])
        league, season = (_text(row[c], c) for c in CONTEXT[1:])
        teams = [row.get(c) for c in TEAMS]
        if (teams[0] is None) != (teams[1] is None):
            raise FixtureEvidenceError(f"{label}: both fixture teams or two nulls required")
        home, away = (None, None) if teams[0] is None else tuple(_team(v) for v in teams)
        if home is not None and home == away:
            raise FixtureEvidenceError(f"{label}: fixture teams must differ")
        grouped[mid].append((league, season, home, away))
    clean, duplicate, conflicts = {}, [], []
    for mid, records in sorted(grouped.items()):
        distinct = set(records)
        if len(records) > 1:
            duplicate.append({"match_id": mid, "rows": len(records), "distinct_records": len(distinct)})
        if len(distinct) != 1:
            conflicts.append({"match_id": mid, "records": [list(r) for r in sorted(distinct, key=repr)]})
        else:
            league, season, home, away = records[0]
            clean[mid] = dict(match_id=mid, competition_name=league, season_name=season, home_team=home, away_team=away)
    return clean, {"input_rows": len(rows), "duplicate_ids": duplicate, "conflicting_ids": conflicts}


def _target(row):
    return row["competition_name"] in LEAGUES and row["season_name"] == SEASON


def compare_records(observed, lineups, *, snapshot=None, snapshot_info=None, ledger=None, ledger_info=None):
    """Pure deterministic comparison; supplied metadata never grants source trust."""
    obs, obs_quality = fixtures(observed, "observed")
    expected, snapshot_quality = fixtures(snapshot or [], "snapshot")
    if snapshot is not None and snapshot_info is None:
        raise FixtureEvidenceError("snapshot requires documented provenance")
    if snapshot is None and snapshot_info is not None:
        raise FixtureEvidenceError("snapshot provenance without snapshot")
    if (ledger is None) != (ledger_info is None):
        raise FixtureEvidenceError("acquisition ledger and provenance must be supplied together")
    scope = {r["competition_name"]: r["coverage_claim"] for r in snapshot_info["scope"]} if snapshot_info else {}
    if any(not _target(r) or r["competition_name"] not in scope for r in expected.values()):
        raise FixtureEvidenceError("snapshot records conflict with declared target scope")
    roster = defaultdict(set)
    roster_contexts = defaultdict(set)
    for row in lineups:
        mid = _id(row["match_id"])
        roster[mid].add(_team(row["team"]))
        direct = [c in row for c in CONTEXT[1:]]
        if any(direct) and not all(direct):
            raise FixtureEvidenceError("partial direct lineup context")
        if all(direct):
            roster_contexts[mid].add(tuple(_text(row[c], c) for c in CONTEXT[1:]))
    acquisition = {}
    acquisition_contexts = defaultdict(list)
    for row in ledger or []:
        mid = _id(row["match_id"])
        context = tuple(_text(row[c], c) for c in CONTEXT[1:])
        if row["stage"] not in ("events", "lineups") or row["outcome"] not in ("success", "failure", "unknown"):
            raise FixtureEvidenceError("invalid acquisition stage/outcome")
        key = (mid, row["stage"])
        if key in acquisition:
            raise FixtureEvidenceError("duplicate/conflicting acquisition outcome; provide one final outcome per match/stage")
        _text(row["evidence_reference"], "acquisition evidence_reference")
        if row["outcome"] == "failure":
            _text(row.get("reason"), "failure reason")
        acquisition[key] = {"match_id": mid, "competition_name": context[0], "season_name": context[1],
                            "stage": row["stage"], "outcome": row["outcome"],
                            "reason": row.get("reason"), "evidence_reference": row["evidence_reference"]}
        acquisition_contexts[mid].append(("acquisition:" + row["stage"], context))
    disagreements, lineup_context_conflicts, team_disagreements = [], [], []
    for mid in sorted(set(obs) | set(expected) | set(roster) | {k[0] for k in acquisition}):
        references = [(name, table[mid]) for name, table in (("snapshot", expected), ("observed", obs)) if mid in table]
        contexts = [(name, (r["competition_name"], r["season_name"])) for name, r in references]
        contexts += [("lineups", pair) for pair in sorted(roster_contexts[mid])]
        contexts += sorted(acquisition_contexts[mid])
        if len({pair for _, pair in contexts}) > 1:
            disagreements.append({"match_id": mid, "contexts": [[name, *pair] for name, pair in contexts]})
        if len(roster_contexts[mid]) > 1:
            lineup_context_conflicts.append(mid)
        known_teams = [(name, (r["home_team"], r["away_team"])) for name, r in references if r["home_team"] is not None]
        if len({pair for _, pair in known_teams}) > 1:
            team_disagreements.append({"match_id": mid, "kind": "fixture_home_away_disagreement"})
        for name, teams in known_teams:
            if mid in roster and roster[mid] != set(teams):
                team_disagreements.append({"match_id": mid, "kind": "lineup_team_disagreement", "reference": name,
                                           "expected_teams": sorted(teams), "lineup_teams": sorted(roster[mid])})
    leagues = []
    for league in LEAGUES:
        observed_ids = {mid for mid, r in obs.items() if _target(r) and r["competition_name"] == league}
        expected_ids = {mid for mid, r in expected.items() if r["competition_name"] == league}
        assessed = league in scope
        leagues.append({"competition_name": league, "season_name": SEASON,
            "observed_count": len(observed_ids), "snapshot_count": len(expected_ids) if assessed else None,
            "coverage_claim": scope.get(league), "comparison_status": "SUPPLIED SNAPSHOT SET ONLY" if assessed else "SOURCE SNAPSHOT UNAVAILABLE FOR LEAGUE",
            "missing_expected_ids": sorted(expected_ids - observed_ids) if assessed else None,
            "unexpected_observed_ids": sorted(observed_ids - expected_ids) if assessed else None,
            "observed_without_lineups": sorted(observed_ids - set(roster)),
            "expected_without_lineups": sorted(expected_ids - set(roster)) if assessed else None,
            "team_association_unavailable_ids": sorted(mid for mid in expected_ids if expected[mid]["home_team"] is None),
            "full_season_verified": False})
    target_ids = {mid for mid, r in obs.items() if _target(r)} | set(expected)
    outcomes = []
    for mid, stage in sorted(set(acquisition) | {(mid, stage) for mid in target_ids for stage in ("events", "lineups")}):
        row = acquisition.get((mid, stage))
        status = "ACQUISITION OUTCOME UNKNOWN"
        if row and row["outcome"] != "unknown":
            status = "ACQUISITION FAILURE DOCUMENTED" if row["outcome"] == "failure" else "ACQUISITION SUCCESS DOCUMENTED"
        outcomes.append({"match_id": mid, "stage": stage, "status": status, "record": row})
    conflict = bool(disagreements or team_disagreements or lineup_context_conflicts or
                    obs_quality["conflicting_ids"] or snapshot_quality["conflicting_ids"])
    status = MISSING_SNAPSHOT
    if snapshot is not None:
        status = {"provider_fixture_records": "DOCUMENTED FIXTURE SNAPSHOT — INDEPENDENCE REVIEW REQUIRED",
                  "event_derived": "NOT INDEPENDENT — EVENT-DERIVED SNAPSHOT",
                  "synthetic": "SYNTHETIC FIXTURE COMPARISON ONLY"}[snapshot_info["origin"]]
    return {"status": status, "comparison_has_conflicts": conflict,
        "snapshot_provenance": snapshot_info, "acquisition_provenance": ledger_info,
        "source_independence_verified": False, "independently_supported_fixture_record": "NOT ESTABLISHED BY THIS TOOL",
        "event_derived_context_status": "EVENT-DERIVED CONTEXT AGREEMENT ONLY" if not disagreements else "CONTEXT DISAGREEMENT",
        "contributor_claims": [dict(CLAIM)], "observed_quality": obs_quality, "snapshot_quality": snapshot_quality,
        "context_disagreements": disagreements, "team_disagreements": team_disagreements,
        "lineup_context_conflicts": lineup_context_conflicts,
        "lineup_ids_without_delivered_metadata": sorted(set(roster) - set(obs)),
        "leagues": leagues, "acquisition_outcomes": outcomes,
        "identity_verified": False, "exposure_verified": False, "metric_coverage_verified": False,
        "production_scoring_ready": False}


def audit_files(*, metadata_path, lineups_path, snapshot_path=None, snapshot_provenance_path=None,
                acquisition_path=None, acquisition_provenance_path=None):
    if (snapshot_path is None) != (snapshot_provenance_path is None):
        raise FixtureEvidenceError("supply snapshot and snapshot provenance together")
    if (acquisition_path is None) != (acquisition_provenance_path is None):
        raise FixtureEvidenceError("supply acquisition ledger and provenance together")
    observed = read_records(metadata_path, CONTEXT, TEAMS)
    lineups = read_records(lineups_path, ("match_id", "team"), CONTEXT[1:])
    snapshot, info, ledger, log_info = None, None, None, None
    if snapshot_path is not None:
        snapshot = read_records(snapshot_path, CONTEXT, TEAMS)
        info = provenance(snapshot_provenance_path, snapshot_path, "fixture_snapshot")
        if info["sha256"] in {fingerprint(metadata_path), fingerprint(lineups_path)}:
            raise FixtureEvidenceError("snapshot reuses a delivered artifact; independent source record unavailable")
    if acquisition_path is not None:
        ledger = read_records(acquisition_path, (*CONTEXT, "stage", "outcome", "evidence_reference"), ("reason",))
        log_info = provenance(acquisition_provenance_path, acquisition_path, "acquisition_ledger")
    result = compare_records(observed, lineups, snapshot=snapshot, snapshot_info=info, ledger=ledger, ledger_info=log_info)
    result["input_fingerprints"] = {"metadata": fingerprint(metadata_path), "lineups": fingerprint(lineups_path)}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--lineups", required=True)
    parser.add_argument("--snapshot")
    parser.add_argument("--snapshot-provenance")
    parser.add_argument("--acquisition-ledger")
    parser.add_argument("--acquisition-provenance")
    args = parser.parse_args(argv)
    try:
        result = audit_files(metadata_path=args.metadata, lineups_path=args.lineups,
            snapshot_path=args.snapshot, snapshot_provenance_path=args.snapshot_provenance,
            acquisition_path=args.acquisition_ledger, acquisition_provenance_path=args.acquisition_provenance)
    except (FixtureEvidenceError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Fixture evidence rejected: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False))
    return 1 if result["comparison_has_conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
