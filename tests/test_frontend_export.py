"""Strict JSON regressions on bounded synthetic M4B0 results, never production data."""
import copy
import json
import unittest

import numpy as np
import pandas as pd

from src.frontend_export import (FIELD_DEFINITIONS, SCHEMA_VERSION,
                                 FrontendExportError, export_scorecard)
from src.scorecard import ScorecardResult, assemble_scorecard
from test_scorecard import assemble, context, fixtures


class FrontendExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = assemble(fixtures())

    def setUp(self):
        self.result = copy.deepcopy(self.fixture)

    def test_actual_m4b0_contract_and_strict_json(self):
        payload = export_scorecard(self.result)
        self.assertEqual(json.loads(json.dumps(payload, allow_nan=False)), payload)
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["measurement_type"], "raw_metrics")

    def test_exact_identity(self):
        row = export_scorecard(self.result)["players"][0]
        self.assertEqual([row[c] for c in ["player_id", "team", "competition_name", "season_name"]],
                         ["1", "Team", "League", "Season"])

    def test_transfers_seasons_and_same_names(self):
        result = assemble(fixtures([context(), context(team="Other"), context(season_name="Other"), context(2)]))
        players = export_scorecard(result)["players"]
        self.assertEqual(len(players), 4)
        self.assertEqual(len({(r["player_id"], r["team"], r["season_name"]) for r in players}), 4)
        self.assertEqual(len({r["player_name"] for r in players}), 1)

    def test_large_player_id_exact_decimal_string(self):
        value = 2**63 - 1
        row = export_scorecard(assemble(fixtures([context(value)])))["players"][0]
        self.assertEqual(row["player_id"], str(value))

    def test_deterministic_rows_and_fields(self):
        result = assemble(fixtures([context(10), context(2)]))
        before = export_scorecard(result)
        result.scorecard = result.scorecard.iloc[::-1, ::-1]
        self.assertEqual(json.dumps(export_scorecard(result)), json.dumps(before))
        self.assertEqual([r["player_id"] for r in before["players"]], ["2", "10"])

    def test_recovery_values_and_units(self):
        row = export_scorecard(self.result)["players"][0]
        for prefix in ["recovery_tackle", "recovery_interception", "recovery_ball_recovery"]:
            self.assertEqual(row[f"{prefix}_count"], "1")
            self.assertEqual(row[f"{prefix}_per90"], .5)
            self.assertTrue(row[f"{prefix}_present"])
            self.assertEqual(FIELD_DEFINITIONS[f"{prefix}_per90"]["unit"], "events/90min")

    def test_press_exact_rate_names_and_units(self):
        row = export_scorecard(self.result)["players"][0]
        self.assertEqual(row["pressured_actions"], "2")
        self.assertEqual(row["pressured_pass_completion_rate"], 100)
        self.assertEqual(FIELD_DEFINITIONS["press_resistance_rate"]["unit"], "percent")
        self.assertNotIn("pressured_pass_completion_pct", row)

    def test_passing_values_units_and_provenance(self):
        payload = export_scorecard(self.result)
        row = payload["players"][0]
        self.assertEqual(row["prog_passes"], "1")
        self.assertEqual(row["passing_difficulty_scope"], "explicit synthetic cohort")
        self.assertIs(row["passing_difficulty_complete"], True)
        self.assertEqual(FIELD_DEFINITIONS["value_sum"]["unit"], "difficulty_weighted_yards")
        self.assertEqual(FIELD_DEFINITIONS["pass_value_p90"]["unit"], "difficulty_weighted_yards/90min")
        self.assertIs(payload["metadata"]["passing_reference"]["independently_verified"], False)

    def test_missing_components_all_null_and_false(self):
        result = assemble_scorecard(self.result.scorecard[["player_id", "team", "competition_name", "season_name"]])
        payload = export_scorecard(result)
        row = payload["players"][0]
        self.assertFalse(row["press_present"])
        self.assertFalse(row["passing_present"])
        self.assertIsNone(row["pressured_actions"])
        self.assertIsNone(row["passing_difficulty_scope"])
        self.assertIsNone(row["recovery_tackle_count"])
        self.assertIsNone(payload["metadata"]["passing_reference"])

    def test_missing_descriptors_become_null(self):
        self.result.scorecard = self.result.scorecard.drop(columns=["minutes", "player_name", "position_group", "matches"])
        row = export_scorecard(self.result)["players"][0]
        self.assertTrue(all(row[c] is None for c in ["minutes", "player_name", "position_group", "matches"]))

    def test_observed_zero_preserved(self):
        row = export_scorecard(self.result)["players"][0]
        self.assertTrue(row["passing_present"])
        self.assertEqual(row["value_sum"], 0)

    def test_present_unavailable_rate_and_nan_to_null(self):
        self.result.scorecard["press_resistance_rate"] = np.nan
        row = export_scorecard(self.result)["players"][0]
        self.assertTrue(row["press_present"])
        self.assertIsNone(row["press_resistance_rate"])
        json.dumps(export_scorecard(self.result), allow_nan=False)

    def test_missing_and_zero_minutes(self):
        for value, status in [(np.nan, "missing_minutes"), (0.0, "zero_minutes")]:
            with self.subTest(value=value):
                payload = export_scorecard(assemble(fixtures([context(minutes=value)])))
                row = payload["players"][0]
                self.assertEqual(row["passing_rate_status"], status)
                self.assertIsNone(row["pass_value_p90"])

    def test_infinity_rejected(self):
        for value in [np.inf, -np.inf]:
            with self.subTest(value=value):
                self.result.scorecard["press_resistance_rate"] = value
                with self.assertRaisesRegex(FrontendExportError, "finite"):
                    export_scorecard(self.result)

    def test_duplicates_rejected(self):
        self.result.scorecard = pd.concat([self.result.scorecard] * 2)
        with self.assertRaisesRegex(FrontendExportError, "duplicate"):
            export_scorecard(self.result)

    def test_alias_normalization_and_collision(self):
        result = assemble(fixtures([context(team="Caen")]))
        result.scorecard["team"] = "Caen"
        self.assertEqual(export_scorecard(result)["players"][0]["team"], "Stade Malherbe Caen")
        result.scorecard = pd.concat([result.scorecard, result.scorecard.assign(team="Stade Malherbe Caen")])
        with self.assertRaises(FrontendExportError):
            export_scorecard(result)

    def test_unknown_scoring_fields_rejected(self):
        for field in ["pct", "ovr", "tier", "archetype", "unexpected"]:
            with self.subTest(field=field):
                result = copy.deepcopy(self.result)
                result.scorecard[field] = 90
                with self.assertRaisesRegex(FrontendExportError, "unsupported fields"):
                    export_scorecard(result)

    def test_missing_required_field_and_duplicate_columns(self):
        bad = self.result.scorecard.drop(columns="passing_present")
        with self.assertRaisesRegex(FrontendExportError, "missing fields"):
            export_scorecard(ScorecardResult(bad, self.result.diagnostics))
        bad = pd.concat([self.result.scorecard, self.result.scorecard[["minutes"]]], axis=1)
        with self.assertRaisesRegex(FrontendExportError, "duplicate column"):
            export_scorecard(ScorecardResult(bad, self.result.diagnostics))

    def test_missing_calibration_rejected(self):
        self.result.diagnostics["passing_reference"] = None
        with self.assertRaisesRegex(FrontendExportError, "calibration"):
            export_scorecard(self.result)

    def test_mismatched_calibration_rejected(self):
        self.result.scorecard["passing_difficulty_scope"] = "other cohort"
        with self.assertRaisesRegex(FrontendExportError, "calibration"):
            export_scorecard(self.result)

    def test_sample_or_overclaimed_calibration_rejected(self):
        for key, value in [("declared_complete", False), ("independently_verified", True)]:
            result = copy.deepcopy(self.result)
            result.diagnostics["passing_reference"][key] = value
            with self.assertRaisesRegex(FrontendExportError, "provenance"):
                export_scorecard(result)

    def test_input_and_returned_metadata_independence(self):
        before = copy.deepcopy(self.result)
        payload = export_scorecard(self.result)
        payload["metadata"]["fields"]["value_sum"]["unit"] = "changed"
        payload["metadata"]["passing_reference"]["scope"] = "changed"
        pd.testing.assert_frame_equal(self.result.scorecard, before.scorecard)
        self.assertEqual(self.result.diagnostics, before.diagnostics)
        self.assertEqual(FIELD_DEFINITIONS["value_sum"]["unit"], "difficulty_weighted_yards")

    def test_invalid_scalars_rejected(self):
        for value in [True, "75", complex(1, 2), [1], {"value": 1}]:
            with self.subTest(value=value):
                result = copy.deepcopy(self.result)
                result.scorecard["press_resistance_rate"] = pd.Series([value], dtype=object)
                with self.assertRaises(FrontendExportError):
                    export_scorecard(result)

    def test_out_of_range_percentage_rejected(self):
        self.result.scorecard["press_resistance_rate"] = 101.0
        with self.assertRaisesRegex(FrontendExportError, "percentage"):
            export_scorecard(self.result)

    def test_absence_with_values_and_missing_presence_rejected(self):
        for value in [False, pd.NA]:
            result = copy.deepcopy(self.result)
            result.scorecard["press_present"] = value
            with self.assertRaises(FrontendExportError):
                export_scorecard(result)

    def test_large_count_string_preserved(self):
        self.result.scorecard["prog_attempts"] = pd.Series([2**63 - 1], dtype="Int64")
        self.assertEqual(export_scorecard(self.result)["players"][0]["prog_attempts"], str(2**63 - 1))

    def test_unsafe_float_count_rejected(self):
        self.result.scorecard["prog_attempts"] = float(2**53 + 2)
        with self.assertRaisesRegex(FrontendExportError, "exact signed"):
            export_scorecard(self.result)

    def test_empty_scorecard(self):
        self.result.scorecard = self.result.scorecard.iloc[:0]
        self.assertEqual(export_scorecard(self.result)["players"], [])

    def test_wrong_input_type(self):
        with self.assertRaisesRegex(FrontendExportError, "ScorecardResult"):
            export_scorecard(self.result.scorecard)

    def test_no_percentiles_ratings_or_demo_fields_generated(self):
        row = export_scorecard(self.result)["players"][0]
        self.assertFalse(set(["pct", "ovr", "tier", "archetype", "photo", "overall_score", "rank"]) & set(row))


if __name__ == "__main__":
    unittest.main()
