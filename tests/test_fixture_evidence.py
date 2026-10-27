"""Synthetic offline evidence tests; no real source authentication or ratings."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from scripts import audit_fixture_evidence as module
from scripts.audit_fixture_evidence import (
    CONTEXT, FixtureEvidenceError, MISSING_SNAPSHOT, audit_files, compare_records,
    fingerprint, main, provenance, read_records,
)


def fixture(mid=10, league="Serie A", **changes):
    return dict(match_id=mid, competition_name=league, season_name="2015/2016",
                home_team="Invented A", away_team="Invented B") | changes


def roster(mid=10):
    return [dict(match_id=mid, team=team) for team in ("Invented A", "Invented B")]


def info(origin="synthetic", leagues=("Serie A",), coverage="partial"):
    return dict(schema_version="fixture-evidence/v1", artifact_kind="fixture_snapshot",
        provider="Invented provider", source_reference="invented-fixtures/test-only",
        match_id_namespace="statsbomb", origin=origin, source_revision="invented-v1", sha256="0" * 64,
        scope=[dict(competition_name=league, season_name="2015/2016", coverage_claim=coverage) for league in leagues])


def compare(observed=None, lineups=None, snapshot=None, **kwargs):
    return compare_records([fixture()] if observed is None else observed,
        roster() if lineups is None else lineups,
        snapshot=[fixture()] if snapshot is None else snapshot,
        snapshot_info=kwargs.pop("snapshot_info", info()), **kwargs)


def league(result, name="Serie A"):
    return next(row for row in result["leagues"] if row["competition_name"] == name)


class FixtureComparisonTests(unittest.TestCase):
    def test_exact_matching_sets(self):
        result = compare()
        self.assertEqual(league(result)["missing_expected_ids"], [])
        self.assertEqual(league(result)["unexpected_observed_ids"], [])
        self.assertFalse(result["comparison_has_conflicts"])

    def test_synthetic_3879594_gap(self):
        result = compare(snapshot=[fixture(), fixture(3879594)])
        self.assertEqual(league(result)["missing_expected_ids"], [3879594])
        self.assertEqual(result["status"], "SYNTHETIC FIXTURE COMPARISON ONLY")
        claim = result["contributor_claims"][0]
        self.assertEqual(claim["status"], "CONTRIBUTOR-REPORTED FIXTURE CLAIM")
        failure = next(r for r in result["acquisition_outcomes"] if r["match_id"] == 3879594)
        self.assertEqual(failure["status"], "ACQUISITION OUTCOME UNKNOWN")

    def test_claim_never_fabricates_expected_fixture(self):
        self.assertEqual(league(compare())["snapshot_count"], 1)
        self.assertNotIn(3879594, league(compare())["missing_expected_ids"])

    def test_extra_observed(self):
        self.assertEqual(league(compare(observed=[fixture(), fixture(11)]))["unexpected_observed_ids"], [11])

    def test_duplicate_ids_accounted_without_silent_drop(self):
        result = compare(observed=[fixture(), fixture()], snapshot=[fixture(), fixture()])
        for key in ("observed_quality", "snapshot_quality"):
            self.assertEqual(result[key]["duplicate_ids"], [dict(match_id=10, rows=2, distinct_records=1)])
        self.assertEqual(league(result)["observed_count"], 1)

    def test_conflicting_match_records_are_quarantined(self):
        for name in ("observed", "snapshot"):
            with self.subTest(name=name):
                result = compare(**{name: [fixture(), fixture(league="La Liga")]},
                                 snapshot_info=info(leagues=("Serie A", "La Liga")))
                self.assertTrue(result["comparison_has_conflicts"])
                self.assertEqual(result[name + "_quality"]["conflicting_ids"][0]["match_id"], 10)

    def test_cross_table_competition_and_season_conflicts(self):
        for change in (dict(competition_name="La Liga"), dict(season_name="2014/2015")):
            result = compare(observed=[fixture(**change)])
            self.assertEqual(result["context_disagreements"][0]["match_id"], 10)
            self.assertTrue(result["comparison_has_conflicts"])

    def test_fixture_home_away_conflict(self):
        result = compare(observed=[fixture(home_team="Invented B", away_team="Invented A")])
        self.assertEqual(result["team_disagreements"][0]["kind"], "fixture_home_away_disagreement")

    def test_lineup_missing_team_and_wrong_team(self):
        for rows in ([roster()[0]], [dict(match_id=10, team="Other")]):
            self.assertTrue(compare(lineups=rows)["team_disagreements"])

    def test_existing_aliases_only(self):
        result = compare(snapshot=[fixture(home_team="Marseille")], observed=[fixture(home_team="Olympique de Marseille")],
                         lineups=[dict(match_id=10, team=t) for t in ("Marseille", "Invented B")])
        self.assertEqual(result["team_disagreements"], [])

    def test_missing_lineups_not_zero_players(self):
        row = league(compare(lineups=[]))
        self.assertEqual(row["expected_without_lineups"], [10])
        self.assertEqual(row["observed_without_lineups"], [10])

    def test_direct_lineup_context_conflicts(self):
        rows = [roster()[0] | dict(competition_name="Serie A", season_name="2015/2016"),
                roster()[1] | dict(competition_name="La Liga", season_name="2015/2016")]
        result = compare(lineups=rows)
        self.assertEqual(result["lineup_context_conflicts"], [10])
        self.assertTrue(result["context_disagreements"])

    def test_partial_lineup_context_rejected(self):
        with self.assertRaises(FixtureEvidenceError):
            compare(lineups=[roster()[0] | dict(competition_name="Serie A")])

    def test_stint_repetitions_are_not_duplicate_fixtures(self):
        result = compare(lineups=roster() * 5)
        self.assertFalse(result["comparison_has_conflicts"])
        self.assertEqual(result["team_disagreements"], [])

    def test_missing_fixture_teams_are_explicitly_unassessed(self):
        result = compare(snapshot=[fixture(home_team=None, away_team=None)])
        self.assertEqual(league(result)["team_association_unavailable_ids"], [10])
        self.assertEqual(result["team_disagreements"], [])

    def test_one_team_and_same_teams_rejected(self):
        for changes in (dict(home_team=None), dict(away_team="Invented A")):
            with self.assertRaises(FixtureEvidenceError):
                compare(snapshot=[fixture(**changes)])

    def test_unknown_success_failure_are_distinct(self):
        rows = [fixture(11), fixture(12)]
        ledger = [fixture(11) | dict(stage="events", outcome="failure", reason="invented connection failure", evidence_reference="invented-log:1"),
                  fixture(12) | dict(stage="events", outcome="success", evidence_reference="invented-log:2")]
        result = compare(snapshot=[fixture(), *rows], ledger=ledger, ledger_info={"origin": "synthetic"})
        states = {(r["match_id"], r["stage"]): r["status"] for r in result["acquisition_outcomes"]}
        self.assertEqual(states[(10, "events")], "ACQUISITION OUTCOME UNKNOWN")
        self.assertEqual(states[(11, "events")], "ACQUISITION FAILURE DOCUMENTED")
        self.assertEqual(states[(12, "events")], "ACQUISITION SUCCESS DOCUMENTED")
        self.assertEqual(states[(12, "lineups")], "ACQUISITION OUTCOME UNKNOWN")

    def test_acquisition_duplicates_bad_outcomes_and_missing_reasons_reject(self):
        row = fixture() | dict(stage="events", outcome="failure", reason="invented", evidence_reference="test")
        for rows in ([row, row], [row | dict(outcome="complete")], [row | dict(stage="anything")], [row | dict(reason=None)]):
            with self.assertRaises(FixtureEvidenceError):
                compare(ledger=rows, ledger_info={"origin": "synthetic"})

    def test_acquisition_context_conflict(self):
        row = fixture(league="La Liga") | dict(stage="events", outcome="unknown", evidence_reference="test")
        self.assertTrue(compare(ledger=[row], ledger_info={})["context_disagreements"])

    def test_ligue1_377_not_a_completeness_finding(self):
        rows = [fixture(mid, "Ligue 1") for mid in range(1, 378)]
        result = compare(observed=rows, snapshot=rows, snapshot_info=info(leagues=("Ligue 1",), coverage="provider_list"))
        self.assertEqual(league(result, "Ligue 1")["observed_count"], 377)
        self.assertEqual(league(result, "Ligue 1")["missing_expected_ids"], [])
        self.assertFalse(league(result, "Ligue 1")["full_season_verified"])
        self.assertFalse(result["production_scoring_ready"])

    def test_absent_snapshot_uses_unknown_not_empty_expected_set(self):
        result = compare_records([fixture()], roster())
        self.assertEqual(result["status"], MISSING_SNAPSHOT)
        self.assertIsNone(league(result)["missing_expected_ids"])
        self.assertIsNone(league(result)["unexpected_observed_ids"])

    def test_empty_snapshot_is_not_complete(self):
        result = compare(snapshot=[])
        self.assertEqual(league(result)["snapshot_count"], 0)
        self.assertEqual(league(result)["unexpected_observed_ids"], [10])
        self.assertFalse(league(result)["full_season_verified"])

    def test_all_empty_inputs(self):
        result = compare_records([], [])
        self.assertEqual(result["acquisition_outcomes"], [])
        self.assertEqual(result["status"], MISSING_SNAPSHOT)

    def test_partial_snapshot_does_not_assess_other_leagues(self):
        result = compare(observed=[fixture(), fixture(11, "Ligue 1")])
        self.assertIsNone(league(result, "Ligue 1")["unexpected_observed_ids"])
        self.assertEqual(league(result)["coverage_claim"], "partial")

    def test_provider_label_and_full_coverage_claim_never_promote_trust(self):
        for origin in ("provider_fixture_records", "event_derived", "synthetic"):
            result = compare(snapshot_info=info(origin=origin, coverage="full_competition_claimed"))
            for flag in ("source_independence_verified", "identity_verified", "exposure_verified", "metric_coverage_verified", "production_scoring_ready"):
                self.assertFalse(result[flag])
            self.assertNotIn("VERIFIED_SOURCE_EVIDENCE", json.dumps(result))

    def test_row_order_invariance_and_input_immutability(self):
        observed = [fixture(11), fixture(), fixture()]
        snapshot = [fixture(12), fixture(), fixture(11)]
        lineups = roster(11) + roster()
        before = copy.deepcopy((observed, snapshot, lineups))
        a = compare(observed, lineups, snapshot)
        b = compare(observed[::-1], lineups[::-1], snapshot[::-1])
        self.assertEqual(a, b)
        self.assertEqual((observed, snapshot, lineups), before)

    def test_invalid_ids_rejected_and_int64_preserved(self):
        for mid in (True, 0, -1, 1.5, "10", 2**63, float(2**53)):
            with self.subTest(mid=mid), self.assertRaises(FixtureEvidenceError):
                compare(snapshot=[fixture(mid)])
        self.assertEqual(league(compare(snapshot=[fixture(2**63 - 1)]))["missing_expected_ids"], [2**63 - 1])

    def test_missing_provenance_not_accepted(self):
        with self.assertRaises(FixtureEvidenceError):
            compare_records([], [], snapshot=[])
        with self.assertRaises(FixtureEvidenceError):
            compare(ledger=[])

    def test_snapshot_outside_scope_rejected(self):
        for row in (fixture(league="Ligue 1"), fixture(season_name="2020/2021")):
            with self.assertRaises(FixtureEvidenceError):
                compare(snapshot=[row])


class OfflineFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metadata = self.write("metadata.json", [fixture()])
        self.lineups = self.write("lineups.json", roster())
        self.snapshot = self.write("snapshot.json", [fixture(), fixture(3879594)])
        self.prov = self.write("snapshot-provenance.json", info() | dict(sha256=fingerprint(self.snapshot)))

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def run_audit(self, **changes):
        return audit_files(**(dict(metadata_path=self.metadata, lineups_path=self.lineups,
            snapshot_path=self.snapshot, snapshot_provenance_path=self.prov) | changes))

    def test_file_fingerprints_and_synthetic_missing_example(self):
        before = {p.name: fingerprint(p) for p in self.root.iterdir()}
        result = self.run_audit()
        self.assertEqual(league(result)["missing_expected_ids"], [3879594])
        self.assertEqual(result["snapshot_provenance"]["sha256"], fingerprint(self.snapshot))
        self.assertEqual(before, {p.name: fingerprint(p) for p in self.root.iterdir()})

    def test_fingerprint_mismatch_rejected(self):
        self.snapshot.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(FixtureEvidenceError, "fingerprint"):
            self.run_audit()

    def test_no_snapshot_cli_explicit_and_terminal_only(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--metadata", str(self.metadata), "--lineups", str(self.lineups)]), 0)
        self.assertEqual(json.loads(out.getvalue())["status"], MISSING_SNAPSHOT)

    def test_bad_paths_and_missing_paired_inputs(self):
        for changes in (dict(metadata_path=self.root / "absent.parquet"), dict(lineups_path=self.root),
                        dict(snapshot_provenance_path=None), dict(acquisition_path=self.snapshot)):
            with self.subTest(changes=changes), self.assertRaises(FixtureEvidenceError):
                self.run_audit(**changes)

    def test_conflicting_and_incomplete_provenance(self):
        original = json.loads(self.prov.read_text())
        variants = [original | dict(artifact_kind="acquisition_ledger"), original | dict(origin="verified"),
                    original | dict(retrieved_on="yesterday"), original | dict(match_id_namespace="other"),
                    original | dict(source_revision=""), original | dict(scope=[]),
                    original | dict(scope=original["scope"] * 2), original | dict(independent=True)]
        variants.append({k: v for k, v in original.items() if k != "provider"})
        for value in variants:
            self.write(self.prov.name, value)
            with self.subTest(value=value), self.assertRaises(FixtureEvidenceError):
                self.run_audit()

    def test_date_can_replace_revision(self):
        value = json.loads(self.prov.read_text())
        del value["source_revision"]
        self.write(self.prov.name, value | dict(retrieved_on="2026-10-27"))
        self.assertEqual(self.run_audit()["snapshot_provenance"]["retrieved_on"], "2026-10-27")

    def test_delivered_artifact_cannot_be_its_own_independent_snapshot(self):
        self.write(self.prov.name, info("provider_fixture_records") | dict(sha256=fingerprint(self.metadata)))
        with self.assertRaisesRegex(FixtureEvidenceError, "delivered artifact"):
            self.run_audit(snapshot_path=self.metadata)

    def test_projected_parquet_reads(self):
        path = self.root / "metadata.parquet"
        pq.write_table(pa.Table.from_pylist([fixture() | dict(unneeded_payload="not read")]), path)
        rows = read_records(path, CONTEXT)
        self.assertNotIn("unneeded_payload", rows[0])
        self.assertEqual(self.run_audit(metadata_path=path)["leagues"][2]["observed_count"], 1)

    def test_row_and_json_byte_caps(self):
        path = self.root / "metadata.parquet"
        pq.write_table(pa.Table.from_pylist([fixture(), fixture(11)]), path)
        with patch.object(module, "MAX_ROWS", 1), self.assertRaises(FixtureEvidenceError):
            read_records(path, CONTEXT)
        with patch.object(module, "MAX_ROWS", 1), self.assertRaises(FixtureEvidenceError):
            read_records(self.snapshot, CONTEXT)
        with patch.object(module, "MAX_JSON_BYTES", 1), self.assertRaises(FixtureEvidenceError):
            read_records(self.metadata, CONTEXT)

    def test_malformed_inputs_cli_errors(self):
        for text in ('{"match_id": 1}', '[{"match_id":1,"match_id":2}]', '[{"match_id":NaN}]', 'not JSON'):
            self.metadata.write_text(text, encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main(["--metadata", str(self.metadata), "--lineups", str(self.lineups)]), 2)
            self.assertEqual(out.getvalue(), "")
            self.assertIn("rejected", err.getvalue())

    def test_ledger_files_require_fingerprint_bound_provenance(self):
        ledger = self.write("ledger.json", [fixture(3879594) | dict(stage="events", outcome="failure",
            reason="invented reset", evidence_reference="invented-log:1")])
        p = info() | dict(artifact_kind="acquisition_ledger", sha256=fingerprint(ledger))
        del p["scope"]
        sidecar = self.write("ledger-provenance.json", p)
        result = self.run_audit(acquisition_path=ledger, acquisition_provenance_path=sidecar)
        row = next(r for r in result["acquisition_outcomes"] if r["match_id"] == 3879594 and r["stage"] == "events")
        self.assertEqual(row["status"], "ACQUISITION FAILURE DOCUMENTED")
        self.assertFalse(result["source_independence_verified"])

    def test_conflict_cli_exit_one(self):
        self.write(self.metadata.name, [fixture(), fixture(league="La Liga")])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--metadata", str(self.metadata), "--lineups", str(self.lineups)]), 1)


if __name__ == "__main__":
    unittest.main()
