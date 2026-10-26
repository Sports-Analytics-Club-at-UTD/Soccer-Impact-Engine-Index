"""Synthetic diagnostic tests; no production identity attestations or datasets."""
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts.audit_provisional_identity import (
    EVENT_COLUMNS, MAPPING_COLUMNS, audit_files, audit_provisional, main,
    prepare_provisional_lookup,
)
from src.identity import IdentityError, PLAYER_KEYS
from src.identity_evidence import (
    DELIVERED, IdentityEvidenceError, validate_lineup_evidence, validate_match_contexts,
)


def mapping(name="Player", player_id=1, **changes):
    return dict(player_name_raw=name, player_id=player_id, team="Team",
                competition_name="League", season_name="Season") | changes


def event(event_id="e1", name="Player", **changes):
    return dict(id=event_id, player=name, match_id=10, team="Team",
                competition_name="League", season_name="Season", type="Pass") | changes


def run(events=None, mappings=None, population=None):
    return audit_provisional(
        pd.DataFrame(events if events is not None else [event()], columns=EVENT_COLUMNS),
        pd.DataFrame(mappings if mappings is not None else [mapping()], columns=MAPPING_COLUMNS),
        pd.DataFrame(population if population is not None else [mapping()], columns=PLAYER_KEYS),
    )


class ProvisionalIdentityTests(unittest.TestCase):
    def test_selected_outside_and_unknown_are_distinct(self):
        result = run([event(), event("e2", "Outside"), event("e3", "Unknown")],
                     [mapping(), mapping("Outside", 2)])
        self.assertEqual(result.events.identity_status.tolist(),
                         ["selected", "outside_population", "unresolved"])
        self.assertEqual(result.summary["events_matched_to_ids"], 2)
        self.assertEqual(result.summary["unresolved"], 1)
        self.assertTrue(pd.isna(result.events.iloc[2].player_id))
        self.assertTrue(pd.isna(result.events.iloc[2].in_population))

    def test_identical_mappings_counted_before_collapse(self):
        result = run(mappings=[mapping(), mapping(), mapping()])
        self.assertEqual(result.lookup.summary["duplicate_identical_mapping_rows"], 2)
        self.assertEqual(len(result.lookup.observations), 3)
        self.assertEqual(len(result.lookup.lookup), 1)
        self.assertEqual(len(result.events), 1)

    def test_conflicting_key_fully_quarantined_no_first_id(self):
        source = [mapping(), mapping(player_id=2), mapping(), mapping("Safe", 3)]
        result = run([event(), event("e2", "Safe")], source, [mapping("Safe", 3)])
        self.assertEqual(result.lookup.summary["conflicting_source_keys"], 1)
        self.assertEqual(result.lookup.summary["conflicting_source_rows"], 3)
        self.assertEqual(result.summary["events_affected_by_conflicting_keys"], 1)
        self.assertTrue(pd.isna(result.events.iloc[0].player_id))
        self.assertEqual(result.events.iloc[1].player_id, 3)
        self.assertEqual(result.unmatched.reason.tolist(), ["conflicting_source_key"])

    def test_conflict_invariant_to_source_order(self):
        rows = [mapping(), mapping(player_id=2)]
        for source in (rows, rows[::-1]):
            self.assertEqual(run(mappings=source).summary["unresolved"], 1)

    def test_normalized_duplicates_preserve_original_spelling(self):
        source = [mapping(" O''Name ", team="Marseille"),
                  mapping("O'Name", team="Olympique de Marseille")]
        result = run([event(name="O'Name", team="Marseille")], source,
                     [mapping("O'Name", team="Olympique de Marseille")])
        self.assertEqual(result.lookup.summary["duplicate_identical_mapping_rows"], 1)
        self.assertEqual(result.lookup.observations.original_player_name.tolist(),
                         [" O''Name ", "O'Name"])
        self.assertEqual(result.summary["selected"], 1)

    def test_conflicts_after_normalization_are_quarantined(self):
        result = run([event(team="Marseille")],
                     [mapping(team="Marseille"), mapping(player_id=2, team="Olympique de Marseille")])
        self.assertEqual(result.summary["unresolved"], 1)
        self.assertEqual(result.lookup.summary["conflicting_source_keys"], 1)

    def test_exact_large_integer_preserved(self):
        value = 2**63 - 1
        result = run(mappings=[mapping(player_id=value)], population=[mapping(player_id=value)])
        self.assertEqual(result.events.player_id.tolist(), [value])
        self.assertEqual(str(result.events.player_id.dtype), "Int64")

    def test_invalid_ids_fail_even_in_repeated_source(self):
        for value in (True, 0, -1, 1.5, float("inf"), float("nan"),
                      None, "1", 2**63, float(2**53)):
            with self.subTest(value=value), self.assertRaises(IdentityError):
                source = pd.DataFrame([mapping(player_id=value)] * 2, dtype=object)
                prepare_provisional_lookup(source)

    def test_safe_integral_float_uses_existing_m2a_semantics(self):
        self.assertEqual(run(mappings=[mapping(player_id=1.0)]).events.player_id.tolist(), [1])

    def test_invalid_context_and_source_names_rejected(self):
        for column in ("player_name_raw", "team", "competition_name", "season_name"):
            for value in (None, " ", 7):
                with self.subTest(column=column, value=value), self.assertRaises(IdentityError):
                    run(mappings=[mapping(**{column: value})])

    def test_context_is_full_key_not_display_name(self):
        result = run([event(season_name="Other"), event("e2", team="Other"),
                      event("e3", competition_name="Other")])
        self.assertEqual(result.summary["unresolved"], 3)
        self.assertEqual(result.summary["events_matched_to_ids"], 0)

    def test_no_fuzzy_or_display_name_fallback(self):
        result = run([event(name="player"), event("e2", "Pláyer")])
        self.assertEqual(result.summary["events_matched_to_ids"], 0)
        self.assertEqual(result.unmatched.reason.unique().tolist(), ["no_exact_provisional_mapping"])

    def test_missing_names_survive_without_fabricated_ids(self):
        result = run([event(name=None), event("e2", " ")])
        self.assertEqual(result.summary["missing_actor_names"], 2)
        self.assertEqual(result.summary["unresolved"], 2)
        self.assertEqual(result.unmatched.events.sum(), 2)
        self.assertEqual(result.unmatched.reason.unique().tolist(), ["missing_actor_name"])

    def test_4096_event_conservation_no_multiplication(self):
        events = [event(str(i), "Player" if i % 2 else "Unknown") for i in range(4096)]
        result = run(events, [mapping(), mapping()])
        self.assertEqual(len(result.events), 4096)
        self.assertEqual(result.summary["unique_event_ids"], 4096)
        self.assertEqual(result.summary["selected"], 2048)
        self.assertEqual(result.summary["unresolved"], 2048)
        self.assertEqual(result.events.id.tolist(), [str(i) for i in range(4096)])
        self.assertTrue(result.summary["row_count_conserved"])
        self.assertEqual(result.summary["duplicate_joins"], 0)

    def test_input_values_and_repeated_index_unchanged(self):
        events = pd.DataFrame([event(), event("e2", "Unknown")], index=[5, 5])
        source = pd.DataFrame([mapping(), mapping()])
        population = pd.DataFrame([mapping()])[PLAYER_KEYS]
        originals = [frame.copy(deep=True) for frame in (events, source, population)]
        result = audit_provisional(events, source, population)
        for frame, original in zip((events, source, population), originals):
            pd.testing.assert_frame_equal(frame, original)
        self.assertEqual(result.events.index.tolist(), [5, 5])

    def test_duplicate_event_ids_fail(self):
        with self.assertRaisesRegex(IdentityError, "duplicate event IDs"):
            run([event(), event()])

    def test_invalid_event_context_match_id_and_event_id_fail(self):
        for changes in ({"match_id": 1.5}, {"team": ""}, {"competition_name": None}, {"id": ""}):
            with self.subTest(changes=changes), self.assertRaises(IdentityError):
                run([event(**changes)])

    def test_supplied_event_ids_cannot_bypass_lookup_diagnostic(self):
        events = pd.DataFrame([event(player_id=1)])
        with self.assertRaisesRegex(IdentityError, "without supplied player_id"):
            audit_provisional(events, pd.DataFrame([mapping()]), pd.DataFrame([mapping()])[PLAYER_KEYS])

    def test_empty_source_means_unknown_not_outside(self):
        result = run(mappings=[])
        self.assertEqual(result.summary["unresolved"], 1)
        self.assertEqual(result.summary["outside_population"], 0)
        self.assertFalse(result.summary["production_verified"])

    def test_empty_events_preserve_schema_and_counts(self):
        result = run(events=[])
        self.assertEqual(result.summary["total_events"], 0)
        self.assertIsNone(result.summary["matched_percent"])

    def test_production_evidence_gate_still_rejects_event_context(self):
        contexts = validate_match_contexts(pd.DataFrame([event()]), source="synthetic event contexts",
                                           evidence_kind=DELIVERED)
        lineups = pd.DataFrame([dict(match_id=10, team="Team", player_id=1, player_name="Player")])
        with self.assertRaisesRegex(IdentityEvidenceError, "separately verified"):
            validate_lineup_evidence(lineups, source="synthetic lineup", evidence_kind=DELIVERED,
                                     match_contexts=contexts)


class ProvisionalFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.events = root / "events.parquet"
        self.crosswalk = root / "crosswalk.parquet"
        self.population = root / "population.parquet"
        pq.write_table(pa.Table.from_pandas(pd.DataFrame([mapping()])), self.crosswalk)
        pq.write_table(pa.Table.from_pandas(pd.DataFrame([mapping()])[PLAYER_KEYS]), self.population)

    def audit(self, limit=4096):
        return audit_files(events_path=self.events, crosswalk_path=self.crosswalk,
                           population_path=self.population, limit=limit)

    def test_prefix_projection_row_groups_and_read_only_inputs(self):
        rows = pd.DataFrame([event(str(i)) | {"unused": "ignored"} for i in range(4100)])
        pq.write_table(pa.Table.from_pandas(rows), self.events, row_group_size=1000)
        before = {p: p.read_bytes() for p in Path(self.temp.name).iterdir()}
        result = self.audit()
        self.assertEqual(result.summary["selected"], 4096)
        self.assertEqual(result.events.id.tolist(), [str(i) for i in range(4096)])
        self.assertNotIn("unused", result.events)
        self.assertEqual({p: p.read_bytes() for p in Path(self.temp.name).iterdir()}, before)

    def test_duplicate_ids_across_row_groups_rejected(self):
        pq.write_table(pa.Table.from_pandas(pd.DataFrame([event(), event()])), self.events, row_group_size=1)
        with self.assertRaisesRegex(IdentityError, "duplicate event IDs"):
            self.audit()

    def test_missing_file_and_invalid_limits_explicit(self):
        with self.assertRaisesRegex(FileNotFoundError, "Required input unavailable"):
            self.audit()
        for limit in (0, -1, True, 2.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.audit(limit)

    def test_cli_reports_provisional_and_actual_short_input(self):
        pq.write_table(pa.Table.from_pandas(pd.DataFrame([event()])), self.events)
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--events", str(self.events), "--crosswalk", str(self.crosswalk),
                         "--population", str(self.population)])
        self.assertEqual(code, 0)
        self.assertIn("NOT YET PRODUCTION-VERIFIED", output.getvalue())
        self.assertIn("total_events: 1", output.getvalue())

    def test_cli_missing_input_rejects_without_writing(self):
        with redirect_stderr(io.StringIO()):
            code = main(["--events", str(self.events), "--crosswalk", str(self.crosswalk),
                         "--population", str(self.population)])
        self.assertEqual(code, 1)
        self.assertFalse(self.events.exists())


if __name__ == "__main__":
    unittest.main()
