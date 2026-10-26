"""Synthetic bounded metric audits; no real datasets or source attestations."""
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts.audit_provisional_metrics import (
    EVENT_COLUMNS, MetricsPrerequisiteError, audit_files, audit_metrics, compare_delivery, main,
)
from src.identity import PLAYER_KEYS, IdentityError
from src.recovery import integrate_recovery
from src.press_resistance import integrate_press_resistance


def event(event_id="e1", **changes):
    return dict(id=event_id, match_id=10, player="Player", team="Team",
                competition_name="League", season_name="Season", type="Ball Recovery",
                location=[10, 10], duel_type=None, duel_outcome=None,
                interception_outcome=None, ball_recovery_recovery_failure=None,
                under_pressure=None, pass_outcome=None, dribble_outcome=None) | changes


def mapping(player="Player", player_id=1, **changes):
    return dict(player_name_raw=player, player_id=player_id, team="Team",
                competition_name="League", season_name="Season") | changes


def inputs(rows=None, mappings=None, minutes=900.0):
    e = pd.DataFrame(rows if rows is not None else [event()], columns=EVENT_COLUMNS)
    x = pd.DataFrame(mappings if mappings is not None else [mapping()])
    m = pd.DataFrame([mapping()])[PLAYER_KEYS].assign(minutes=minutes)
    return e, x, m


def run(rows=None, **kwargs):
    return audit_metrics(*inputs(rows, **kwargs))


class ProvisionalMetricTests(unittest.TestCase):
    def test_recovery_definitions_and_category_conservation(self):
        rows = [event("b"), event("f", ball_recovery_recovery_failure=True),
                event("t", type="Duel", duel_type="Tackle", duel_outcome="Won"),
                event("l", type="Duel", duel_type="Tackle", duel_outcome="Lost In Play"),
                event("a", type="Duel", duel_type="Aerial", duel_outcome="Won"),
                event("i", type="Interception", interception_outcome="Success Out"),
                event("u", type="Interception", interception_outcome=None)]
        result = run(rows)
        self.assertEqual(result.recovery.set_index("event_type")["count"].to_dict(),
                         {"Ball Recovery": 1, "Interception": 1, "Tackle": 1})
        self.assertEqual(result.summary["recovery_nonqualifying_events"], 4)
        self.assertEqual(result.recovery_accounting.selected.sum(), 3)

    def test_nullable_recovery_failure_storage_matches_existing_wrapper(self):
        e, x, m = inputs([event(), event("e2"), event("e3")])
        e["ball_recovery_recovery_failure"] = pd.Series([pd.NA, False, True], dtype="boolean")
        result = audit_metrics(e, x, m)
        self.assertEqual(result.recovery["count"].sum(), 2)
        self.assertTrue(pd.isna(e.ball_recovery_recovery_failure.iloc[0]))

    def test_zone_edges_unknown_locations_and_totals(self):
        rows = [event(str(i), location=loc) for i, loc in enumerate(
            ([0, 0], [40, 0], [120, 80], None, [-1, 0], [10, 100]))]
        result = run(rows)
        self.assertEqual(result.by_zone.zone.tolist(), [1, 2, 9])
        self.assertEqual(result.recovery["count"].sum(), 6)
        self.assertEqual(result.zones.unknown_zone.sum(), 3)
        self.assertEqual(result.zones.zoned.sum(), 3)

    def test_press_attempts_outcomes_and_attempt_weighted_combined_rate(self):
        rows = [event(str(i), type="Pass", under_pressure=True,
                      pass_outcome=None if i < 3 else "Incomplete") for i in range(4)]
        rows += [event("d", type="Dribble", under_pressure=True, dribble_outcome="Incomplete")]
        result = run(rows)
        row = result.press.iloc[0]
        self.assertEqual(row.pressured_pass_attempts, 4)
        self.assertEqual(row.pressured_pass_completed, 3)
        self.assertEqual(row.pressured_dribble_attempts, 1)
        self.assertEqual(row.press_resistance_rate, 60)
        self.assertEqual(row.pressured_pass_completion_rate, 75)
        self.assertEqual(row.pressured_dribble_completion_rate, 0)
        self.assertEqual(result.press_accounting.completed.sum(), 3)

    def test_zero_component_attempts_are_na(self):
        result = run([event(type="Pass", under_pressure=True)])
        self.assertEqual(result.press.iloc[0].pressured_pass_completion_rate, 100)
        self.assertTrue(pd.isna(result.press.iloc[0].pressured_dribble_completion_rate))

    def test_missing_pressure_and_dribble_outcome_keep_existing_semantics(self):
        e, x, m = inputs([event("p", type="Pass"), event("d", type="Dribble"),
                          event("u", type="Pass"), event("c", type="Carry")])
        e["under_pressure"] = pd.Series([True, True, pd.NA, True], dtype="boolean")
        e["dribble_outcome"] = pd.Series([pd.NA] * 4, dtype="string")
        result = audit_metrics(e, x, m)
        self.assertEqual(result.summary["aggregate_press"]["pressured_actions"], 2)
        self.assertEqual(result.summary["aggregate_press"]["press_resistance_rate"], 50)
        self.assertEqual(result.summary["press_nonqualifying_events"], 2)

    def test_known_outsiders_accounted_but_not_selected_metrics(self):
        rows = [event(), event("o", player="Out"),
                event("p", player="Out", type="Pass", under_pressure=True)]
        result = run(rows, mappings=[mapping(), mapping("Out", 2)])
        self.assertEqual(result.identity.summary["outside_population"], 2)
        self.assertEqual(result.recovery["count"].sum(), 1)
        self.assertEqual(result.recovery_accounting.outside_population.sum(), 1)
        self.assertEqual(result.press_accounting.outside_population_completed.sum(), 1)
        self.assertTrue(result.press.empty)

    def test_unresolved_action_retains_accounting_and_blocks_metrics(self):
        with self.assertRaises(MetricsPrerequisiteError) as caught:
            run([event(), event("u", player="Unknown", type="Pass", under_pressure=True)])
        self.assertEqual(caught.exception.identity.summary["unresolved"], 1)
        self.assertEqual(caught.exception.press_accounting.unresolved.sum(), 1)
        self.assertEqual(caught.exception.press_accounting.unresolved_completed.sum(), 1)
        self.assertFalse(hasattr(caught.exception, "recovery"))

    def test_unresolved_nonmetric_event_also_blocks_partial_metrics(self):
        with self.assertRaises(MetricsPrerequisiteError):
            run([event(), event("u", player="Unknown", type="Carry")])

    def test_conflicting_source_key_cannot_create_counts(self):
        with self.assertRaises(MetricsPrerequisiteError) as caught:
            run(mappings=[mapping(), mapping(player_id=2)])
        self.assertEqual(caught.exception.identity.summary["events_affected_by_conflicting_keys"], 1)

    def test_duplicate_lookup_rows_never_multiply_metrics(self):
        result = run([event(str(i)) for i in range(4096)], mappings=[mapping(), mapping()])
        self.assertEqual(result.recovery["count"].sum(), 4096)
        self.assertEqual(result.identity.summary["unique_event_ids"], 4096)
        self.assertEqual(result.identity.lookup.summary["duplicate_identical_mapping_rows"], 1)

    def test_duplicate_ids_in_excluded_rows_rejected(self):
        with self.assertRaisesRegex(IdentityError, "duplicate event IDs"):
            run([event(type="Carry"), event(type="Carry")])

    def test_no_zero_grid_or_per90_for_unobserved_actions(self):
        result = run([event(type="Carry")])
        self.assertTrue(result.recovery.empty)
        self.assertTrue(result.press.empty)
        self.assertNotIn("per90", result.recovery.columns)
        self.assertNotIn("minutes", result.press.columns)

    def test_missing_and_zero_exposure_do_not_change_counts(self):
        for minutes in (float("nan"), 0.0, 900.0):
            with self.subTest(minutes=minutes):
                result = run(minutes=minutes)
                self.assertEqual(result.recovery["count"].sum(), 1)
                self.assertNotIn("per90", result.recovery.columns)
                self.assertIn("WITHHELD", result.summary["per90"])

    def test_invalid_exposure_rejected_without_estimation(self):
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            run(minutes=-1.0)

    def test_parity_with_established_integrations_and_immutable_inputs(self):
        e, x, m = inputs([event(), event("p", type="Pass", under_pressure=True)])
        originals = [f.copy(deep=True) for f in (e, x, m)]
        result = audit_metrics(e, x, m)
        rec = integrate_recovery(e, x, m, m[PLAYER_KEYS])
        press = integrate_press_resistance(e, x, m[PLAYER_KEYS])
        pd.testing.assert_frame_equal(result.recovery, rec.totals[result.recovery.columns])
        pd.testing.assert_frame_equal(result.by_zone, rec.by_zone)
        pd.testing.assert_frame_equal(result.press, press.totals)
        for frame, original in zip((e, x, m), originals):
            pd.testing.assert_frame_equal(frame, original)
        self.assertEqual(result.identity.events.id.tolist(), e.id.tolist())
        self.assertEqual(result.identity.events.match_id.tolist(), e.match_id.tolist())

    def test_corrupted_aggregation_rejected_by_conservation(self):
        real = run()
        wrong = real.recovery.copy()
        wrong["count"] += 1
        with patch("scripts.audit_provisional_metrics.recovery_counts", return_value=(wrong, real.by_zone)):
            with self.assertRaisesRegex(IdentityError, "conservation"):
                run()

    def test_delivery_scope_difference_is_not_a_formula_disagreement(self):
        result = run()
        delivery = result.recovery.copy()
        delivery["count"] = 999
        comparison = compare_delivery(result, delivery)
        self.assertEqual(comparison["shared_context_category_rows"], 1)
        self.assertIn("NOT COMPARABLE", comparison["count_comparison"])
        self.assertIn("NOT ESTABLISHED", comparison["formula_disagreement"])

    def test_duplicate_delivered_keys_rejected(self):
        result = run()
        with self.assertRaisesRegex(IdentityError, "duplicate"):
            compare_delivery(result, pd.concat([result.recovery, result.recovery]))

    def test_empty_event_input_preserves_empty_metric_tables(self):
        result = run([])
        self.assertTrue(result.recovery.empty)
        self.assertTrue(result.press.empty)
        self.assertEqual(result.summary["input_events"], 0)
        self.assertTrue(pd.isna(result.summary["aggregate_press"]["press_resistance_rate"]))


class ProvisionalMetricsFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        e, x, m = inputs([event(str(i)) for i in range(5)])
        self.events, self.crosswalk, self.minutes = [self.root / n for n in
                                                    ("events.parquet", "lookup.parquet", "minutes.parquet")]
        for path, frame in zip((self.events, self.crosswalk, self.minutes), (e, x, m)):
            pq.write_table(pa.Table.from_pandas(frame), path, row_group_size=2)

    def audit(self, **kwargs):
        return audit_files(events_path=self.events, crosswalk_path=self.crosswalk,
                           minutes_path=self.minutes, **kwargs)

    def test_projected_prefix_is_read_only_across_row_groups(self):
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        result = self.audit(limit=3, comparison_minutes_path=self.minutes)
        self.assertEqual(result.identity.events.id.tolist(), ["0", "1", "2"])
        self.assertEqual(result.recovery["count"].sum(), 3)
        self.assertEqual(result.summary["minutes_comparison"]["changed_minutes"], 0)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})

    def test_cross_row_group_duplicate_ids_rejected(self):
        e, _, _ = inputs([event(), event()])
        pq.write_table(pa.Table.from_pandas(e), self.events, row_group_size=1)
        with self.assertRaisesRegex(IdentityError, "duplicate event IDs"):
            self.audit()

    def test_missing_optional_path_is_not_silently_ignored(self):
        with self.assertRaisesRegex(FileNotFoundError, "Required input unavailable"):
            self.audit(delivered_recovery_path=self.root / "missing.parquet")

    def test_invalid_limit_rejected(self):
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.audit(limit=limit)

    def test_cli_success_and_unresolved_prerequisite_report(self):
        args = ["--events", str(self.events), "--crosswalk", str(self.crosswalk),
                "--minutes", str(self.minutes)]
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(args), 0)
        self.assertIn("NOT PRODUCTION-VERIFIED", output.getvalue())
        e, _, _ = inputs([event(player="Unknown")])
        pq.write_table(pa.Table.from_pandas(e), self.events)
        errors = io.StringIO()
        with redirect_stderr(errors):
            self.assertEqual(main(args), 1)
        self.assertIn("no player metrics calculated", errors.getvalue())
        self.assertIn("Unknown", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
