import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from scripts.validate_datasets import GROUPS, compare, main, validate


def minutes_row(player_id=1, name="Player", minutes=90.0):
    return dict(player_id=player_id, player_name=name, team="Team",
                competition_name="League", season_name="Season", minutes=minutes,
                matches=1.0 if minutes else np.nan, tied_groups=1,
                position_group="DM", in_scope=True,
                **{f"min_{g}": minutes if g == "DM" else 0.0 for g in GROUPS})


def recovery_row(player_id=1, name="Player", count=3, minutes=90.0):
    return dict(player_id=player_id, player=name, team="Team",
                competition_name="League", season_name="Season", minutes=minutes,
                matches=1.0, position_group="DM", event_type="Ball Recovery", count=count,
                per90=count / minutes * 90 if minutes else 0.0,
                reportable=True, meets_min=False, full_coverage=True,
                pctl=np.nan, pool_n=np.nan, pctl_note="below delivered minimum")


def delivery():
    return pd.DataFrame([minutes_row()]), pd.DataFrame([recovery_row()])


def failures(report):
    return {c["name"]: c["count"] for c in report.checks if c["count"] and c["severity"] == "ERROR"}


class ValidatorTests(unittest.TestCase):
    def test_valid_identity_and_no_mutation(self):
        m, r = delivery()
        before_m, before_r = m.copy(deep=True), r.copy(deep=True)
        self.assertTrue(validate(m, r).ok)
        pd.testing.assert_frame_equal(m, before_m)
        pd.testing.assert_frame_equal(r, before_r)

    def test_duplicate_minutes_multiply_join(self):
        m, r = delivery()
        result = validate(pd.concat([m, m], ignore_index=True), r)
        self.assertEqual(failures(result)["minutes.unique_keys"], 2)
        self.assertEqual(failures(result)["join.exactly_one_minutes_record"], 1)

    def test_duplicate_recovery_records(self):
        m, r = delivery()
        self.assertEqual(failures(validate(m, pd.concat([r, r], ignore_index=True)))[
            "recovery.unique_keys"], 2)

    def test_spelling_variant_same_id_joins(self):
        m, r = delivery()
        r.loc[0, "player"] = "Different spelling"
        self.assertTrue(validate(m, r).ok)

    def test_same_name_different_ids_remain_distinct(self):
        m = pd.DataFrame([minutes_row(1), minutes_row(2)])
        r = pd.DataFrame([recovery_row(1), recovery_row(2)])
        self.assertTrue(validate(m, r).ok)

    def test_missing_minutes_record(self):
        m, r = delivery()
        r.loc[0, "player_id"] = 2
        self.assertEqual(failures(validate(m, r))["join.missing_minutes"], 1)

    def test_zero_minute_player_is_warning(self):
        m, r = delivery()
        m = pd.concat([m, pd.DataFrame([minutes_row(2, minutes=0)])], ignore_index=True)
        result = validate(m, r)
        self.assertTrue(result.ok)
        warning = next(c for c in result.checks if c["name"] == "minutes.zero_minute_classification")
        self.assertEqual((warning["severity"], warning["count"]), ("WARNING", 1))

    def test_zero_rate_denominator_fails(self):
        m, r = delivery()
        r.loc[0, "minutes"] = 0
        self.assertIn("recovery.positive_denominator", failures(validate(m, r)))

    def test_wrong_rate(self):
        m, r = delivery()
        r.loc[0, "per90"] = 99
        self.assertIn("recovery.per90_arithmetic", failures(validate(m, r)))

    def test_rate_correct_for_wrong_source_denominator_still_fails(self):
        m, r = delivery()
        r.loc[0, ["minutes", "per90"]] = [45, 6]
        f = failures(validate(m, r))
        self.assertIn("join.minutes_agree", f)
        self.assertNotIn("recovery.per90_arithmetic", f)

    def test_position_minutes_sum(self):
        m, r = delivery()
        m.loc[0, "min_DM"] = 80
        self.assertIn("minutes.position_sum", failures(validate(m, r)))

    def test_missing_and_nonfinite_required_numbers(self):
        for col in ["count", "minutes", "per90"]:
            for value in [np.nan, np.inf, -np.inf]:
                with self.subTest(col=col, value=value):
                    m, r = delivery()
                    r[col] = float(value)
                    self.assertFalse(validate(m, r).ok)

    def test_nonfinite_position_minutes(self):
        m, r = delivery()
        m.loc[0, "min_CB"] = np.inf
        self.assertFalse(validate(m, r).ok)

    def test_optional_percentiles_can_be_missing(self):
        m, r = delivery()
        self.assertTrue(validate(m, r).ok)
        r.loc[0, "meets_min"] = True
        self.assertIn("recovery.percentile_availability", failures(validate(m, r)))

    def test_nonfinite_percentile_and_pool(self):
        for col in ["pctl", "pool_n"]:
            m, r = delivery()
            r.loc[0, col] = np.inf
            self.assertFalse(validate(m, r).ok)

    def test_missing_and_invalid_identifiers(self):
        for col, value in [("team", ""), ("season_name", None), ("player_id", np.nan),
                           ("player_id", 1.5), ("player_id", -1)]:
            m, r = delivery()
            m[col] = value
            self.assertFalse(validate(m, r).ok)

    def test_missing_column_and_incompatible_type(self):
        m, r = delivery()
        self.assertFalse(validate(m.drop(columns="min_DM"), r).ok)
        m["minutes"] = "90"
        self.assertFalse(validate(m, r).ok)

    def test_negative_or_fractional_count(self):
        for value in [-1, 0.5]:
            m, r = delivery()
            r["count"] = value
            self.assertFalse(validate(m, r).ok)

    def test_nullable_numeric_and_boolean_types(self):
        m, r = delivery()
        m["player_id"] = m.player_id.astype("Int64")
        m["in_scope"] = m.in_scope.astype("boolean")
        self.assertTrue(validate(m, r).ok)
        m.loc[0, "in_scope"] = pd.NA
        self.assertFalse(validate(m, r).ok)

    def test_empty_deliveries_fail(self):
        m, r = delivery()
        self.assertFalse(validate(m.iloc[:0], r.iloc[:0]).ok)


class ConsistencyTests(unittest.TestCase):
    def test_cross_table_position_disagreement(self):
        m, r = delivery()
        r.loc[0, "position_group"] = "CB"
        self.assertEqual(failures(validate(m, r))["join.position_group_agrees"], 1)

    def test_cross_table_match_count_disagreement(self):
        m, r = delivery()
        r.loc[0, "matches"] = 2
        self.assertEqual(failures(validate(m, r))["join.matches_agree"], 1)

    def test_cross_table_agreement_nondefault_indices_and_nullable_types(self):
        m, r = delivery()
        m.index, r.index = [10], [20]
        m["matches"], r["matches"] = m.matches.astype("Int64"), r.matches.astype("Int64")
        m["in_scope"] = m.in_scope.astype("boolean")
        self.assertTrue(validate(m, r).ok)

    def test_ambiguous_source_skips_attribute_checks(self):
        m, r = delivery()
        other = m.copy()
        other.loc[0, ["position_group", "matches"]] = ["CB", 2]
        result = validate(pd.concat([m, other], ignore_index=True), r)
        self.assertIn("join.exactly_one_minutes_record", failures(result))
        for name in ["join.position_group_agrees", "join.matches_agree", "join.in_scope_minutes"]:
            check = next(c for c in result.checks if c["name"] == name)
            self.assertEqual(check["checked"], 0)

    def test_missing_source_skips_attribute_checks(self):
        m, r = delivery()
        r.loc[0, "player_id"] = 2
        result = validate(m, r)
        self.assertIn("join.missing_minutes", failures(result))
        self.assertNotIn("join.position_group_agrees", failures(result))
        self.assertNotIn("join.matches_agree", failures(result))

    def test_dominant_label_must_follow_position_minutes(self):
        m, r = delivery()
        m.loc[0, ["min_DM", "min_CB"]] = [30, 60]
        self.assertIn("minutes.dominant_position", failures(validate(m, r)))
        m.loc[0, "position_group"] = r.loc[0, "position_group"] = "CB"
        self.assertTrue(validate(m, r).ok)

    def test_exact_tie_uses_declared_order(self):
        m, r = delivery()
        m.loc[0, ["min_DM", "min_CB", "tied_groups", "position_group"]] = [45, 45, 2, "CB"]
        r.loc[0, "position_group"] = "CB"
        self.assertTrue(validate(m, r).ok)
        m.loc[0, "position_group"] = "DM"
        self.assertIn("minutes.dominant_position", failures(validate(m, r)))

    def test_tie_count_must_match_position_minutes(self):
        m, r = delivery()
        m.loc[0, "tied_groups"] = 2
        self.assertIn("minutes.position_ties", failures(validate(m, r)))
        m.loc[0, ["min_DM", "min_CM", "tied_groups"]] = [45, 45, 1]
        self.assertIn("minutes.position_ties", failures(validate(m, r)))

    def test_near_tie_is_not_an_exact_tie(self):
        m, r = delivery()
        m.loc[0, ["min_DM", "min_CM"]] = [45.0000001, 44.9999999]
        self.assertTrue(validate(m, r).ok)
        m.loc[0, "tied_groups"] = 2
        self.assertIn("minutes.position_ties", failures(validate(m, r)))

    def test_scope_flag_must_follow_role(self):
        for role, flag in [("DM", False), ("FB", True)]:
            with self.subTest(role=role):
                m, r = delivery()
                m.loc[0, ["position_group", "in_scope"]] = [role, flag]
                self.assertIn("minutes.scope_agrees", failures(validate(m, r)))

    def test_out_of_scope_minutes_without_recovery_are_allowed(self):
        m, r = delivery()
        other = minutes_row(player_id=2)
        other.update(position_group="FB", in_scope=False, min_DM=0, min_FB=90)
        self.assertTrue(validate(pd.concat([m, pd.DataFrame([other])], ignore_index=True), r).ok)

    def test_recovery_out_of_scope_role_is_rejected_even_if_unreportable(self):
        for role in ["FB", "WM", "AM", "ATT"]:
            for reportable in [True, False]:
                with self.subTest(role=role, reportable=reportable):
                    m, r = delivery()
                    r.loc[0, ["position_group", "reportable"]] = [role, reportable]
                    self.assertIn("recovery.in_scope_position", failures(validate(m, r)))

    def test_recovery_requires_in_scope_source_flag(self):
        m, r = delivery()
        m.loc[0, "in_scope"] = False
        self.assertIn("join.in_scope_minutes", failures(validate(m, r)))

    def test_goalkeeper_reporting_rules(self):
        for event in ["Tackle", "Interception", "Ball Recovery"]:
            with self.subTest(event=event):
                m, r = delivery()
                m.loc[0, ["position_group", "min_DM", "min_GK"]] = ["GK", 0, 90]
                r.loc[0, ["position_group", "event_type", "reportable"]] = ["GK", event, event == "Ball Recovery"]
                self.assertTrue(validate(m, r).ok)
                r.loc[0, "reportable"] = event != "Ball Recovery"
                self.assertIn("recovery.reportable_agrees", failures(validate(m, r)))

    def test_outfield_recovery_rows_are_reportable(self):
        m, r = delivery()
        r.loc[0, "reportable"] = False
        self.assertIn("recovery.reportable_agrees", failures(validate(m, r)))

    def test_zero_exposure_does_not_invent_dominant_role(self):
        m, r = delivery()
        m = pd.concat([m, pd.DataFrame([minutes_row(2, minutes=0)])], ignore_index=True)
        result = validate(m, r)
        self.assertTrue(result.ok)
        self.assertNotIn("minutes.dominant_position", failures(result))
        self.assertNotIn("minutes.position_ties", failures(result))


class ComparisonTests(unittest.TestCase):
    def test_identity_consolidation_conserves_minutes_and_events(self):
        old_m = pd.DataFrame([minutes_row(minutes=60), minutes_row(name="Variant", minutes=30)])
        old_r = pd.DataFrame([recovery_row(count=1, minutes=60),
                              recovery_row(name="Variant", count=2, minutes=30)])
        m, r = delivery()
        before = old_m.copy(deep=True)
        result = compare(old_m, old_r, m, r)
        self.assertTrue(result.ok)
        self.assertIn("rows 2 -> 1", result.render())
        pd.testing.assert_frame_equal(old_m, before)

    def test_event_count_change(self):
        m, r = delivery()
        revised = r.copy()
        revised.loc[0, "count"] = 4
        self.assertIn("comparison.recovery.conservation", failures(compare(m, r, m, revised)))

    def test_equal_grand_total_does_not_hide_player_redistribution(self):
        m = pd.DataFrame([minutes_row(1), minutes_row(2)])
        r = pd.DataFrame([recovery_row(1, count=1), recovery_row(2, count=5)])
        revised = r.copy()
        revised["count"] = [2, 4]
        self.assertFalse(compare(m, r, m, revised).ok)

    def test_event_type_redistribution_fails(self):
        m, r = delivery()
        revised = r.copy()
        revised["event_type"] = "Interception"
        self.assertFalse(compare(m, r, m, revised).ok)

    def test_minutes_change(self):
        m, r = delivery()
        revised = m.copy()
        revised.loc[0, "minutes"] = 91
        self.assertIn("comparison.minutes.conservation", failures(compare(m, r, revised, r)))

    def test_new_and_missing_contexts(self):
        m, r = delivery()
        revised = m.copy()
        revised["player_id"] = 2
        f = failures(compare(m, r, revised, r))
        self.assertEqual(f["comparison.minutes.context_changes"], 2)

    def test_missing_numeric_not_hidden_by_aggregation(self):
        m, r = delivery()
        old = m.copy()
        old["minutes"] = np.nan
        self.assertFalse(compare(old, r, m, r).ok)


class CliTests(unittest.TestCase):
    def test_cli_exit_codes_and_read_only_files(self):
        with tempfile.TemporaryDirectory() as temp:
            m, r = delivery()
            mp, rp = Path(temp) / "minutes.parquet", Path(temp) / "recovery.parquet"
            m.to_parquet(mp, index=False)
            r.to_parquet(rp, index=False)
            before = (mp.read_bytes(), rp.read_bytes())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--minutes", str(mp), "--recovery", str(rp),
                                       "--compare-minutes", str(mp), "--compare-recovery", str(rp)]), 0)
            self.assertEqual((mp.read_bytes(), rp.read_bytes()), before)
            r["per90"] = 99
            r.to_parquet(rp, index=False)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--minutes", str(mp), "--recovery", str(rp)]), 1)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--minutes", str(mp), "--recovery", str(rp) + ".missing"]), 2)

    def test_comparison_requires_both_paths(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--minutes", "m", "--recovery", "r", "--compare-minutes", "old"])
        self.assertEqual(cm.exception.code, 2)



class BoundaryTests(unittest.TestCase):
    def test_duplicate_column_labels(self):
        m, r = delivery()
        m = pd.concat([m, m[["minutes"]]], axis=1)
        self.assertIn("minutes.duplicate_columns", failures(validate(m, r)))

    def test_invalid_event_type(self):
        m, r = delivery()
        r.loc[0, "event_type"] = "Unknown"
        self.assertIn("recovery.event_types", failures(validate(m, r)))

    def test_zero_count_and_nondefault_indices(self):
        m, r = delivery()
        m.index, r.index = [10], [20]
        r.loc[20, ["count", "per90"]] = [0, 0]
        self.assertTrue(validate(m, r).ok)

    def test_missing_matches_only_allowed_without_exposure(self):
        m, r = delivery()
        m.loc[0, "matches"] = np.nan
        self.assertIn("minutes.matches", failures(validate(m, r)))
        m, r = delivery()
        m = pd.concat([m, pd.DataFrame([minutes_row(2, minutes=0)])], ignore_index=True)
        m.loc[1, "matches"] = np.inf
        self.assertIn("minutes.matches", failures(validate(m, r)))


if __name__ == "__main__":
    unittest.main()
