"""Synthetic assembly regressions using the existing milestone event fixtures."""
import copy
from dataclasses import replace
import unittest

import numpy as np
import pandas as pd

from src.identity import NAME_KEYS, PLAYER_KEYS
from src.passing import integrate_progressive_passing
from src.press_resistance import integrate_press_resistance
from src.recovery import integrate_recovery
from src.scorecard import (PASS_FIELDS, PRESS_FIELDS, RECOVERY_PREFIXES,
                           ScorecardError, assemble_scorecard)
from test_passing import event as passing_event, reference
from test_press_resistance import event as press_event
from test_recovery import event as recovery_event


def context(player_id=1, **changes):
    return dict(player_id=player_id, team="Team", competition_name="League",
                season_name="Season", player_name="Same label", position_group="CB",
                minutes=180.0, matches=2) | changes


def fixtures(contexts=None):
    """Tiny, fully supplied synthetic scope, never a real season coverage claim."""
    base = pd.DataFrame(contexts or [context()])
    rows = []
    for i, row in base.iterrows():
        keys = {c: row[c] for c in PLAYER_KEYS}
        rows += [recovery_event(f"r{i}", player=row.player_name, **keys),
                 recovery_event(f"t{i}", player=row.player_name, **keys,
                                type="Duel", duel_type="Tackle", duel_outcome="Won"),
                 recovery_event(f"i{i}", player=row.player_name, **keys,
                                type="Interception", interception_outcome="Won"),
                 passing_event(f"p{i}", player=row.player_name, **keys,
                               under_pressure=True, dribble_outcome=None),
                 press_event(f"d{i}", player=row.player_name, **keys,
                             type="Dribble", dribble_outcome="Complete")]
    events = pd.DataFrame(rows)
    events["player_id"] = events.player_id.astype("Int64")
    lookup = pd.DataFrame(columns=[*NAME_KEYS, "player_id"])
    population = base[PLAYER_KEYS]
    minutes = base[[*PLAYER_KEYS, "minutes"]]
    recovery = integrate_recovery(events, lookup, minutes, population)
    press = integrate_press_resistance(events, lookup, population, minutes=minutes)
    passing = integrate_progressive_passing(events, lookup, population, minutes,
                                            reference=reference(events))
    return base, recovery, press, passing


def assemble(data):
    base, recovery, press, passing = data
    return assemble_scorecard(base, recovery=recovery, press=press, passing=passing)


class ScorecardTests(unittest.TestCase):
    def setUp(self):
        self.data = fixtures()

    def test_actual_three_result_contracts(self):
        row = assemble(self.data).scorecard.iloc[0]
        self.assertEqual(row.player_id, 1)
        self.assertTrue(row.press_present and row.passing_present)
        self.assertEqual(row.pressured_actions, 2)
        self.assertEqual(row.prog_passes, 1)

    def test_recovery_long_to_wide(self):
        row = assemble(self.data).scorecard.iloc[0]
        for prefix in RECOVERY_PREFIXES.values():
            self.assertEqual(row[f"{prefix}_count"], 1)
            self.assertEqual(row[f"{prefix}_per90"], .5)
            self.assertEqual(row[f"{prefix}_rate_status"], "ok")
            self.assertTrue(row[f"{prefix}_present"])

    def test_recovery_components_never_blended(self):
        self.assertEqual(len([c for c in assemble(self.data).scorecard if c.endswith("_count")]), 3)

    def test_press_exact_implemented_names_and_values(self):
        row = assemble(self.data).scorecard.iloc[0]
        source = self.data[2].totals.iloc[0]
        for c in PRESS_FIELDS:
            self.assertEqual(row[c], source[c])
        self.assertNotIn("pressured_pass_completion_pct", row.index)
        self.assertNotIn("pressured_dribble_completion_pct", row.index)

    def test_passing_values_preserved(self):
        row = assemble(self.data).scorecard.iloc[0]
        for c in PASS_FIELDS:
            self.assertEqual(row[c], self.data[3].totals.iloc[0][c])
        self.assertEqual(row.passing_rate_status, "ok")

    def test_matching_by_id_not_row_order(self):
        data = fixtures([context(2), context(1)])
        data[2].totals.loc[data[2].totals.player_id.eq(2), "press_resistance_rate"] = 71.0
        table = assemble(data).scorecard
        self.assertEqual(table.player_id.tolist(), [1, 2])
        self.assertEqual(table.press_resistance_rate.tolist(), [100, 71])

    def test_seasons_remain_separate(self):
        table = assemble(fixtures([context(), context(season_name="Other")])).scorecard
        self.assertEqual(len(table), 2)
        self.assertEqual(set(table.season_name), {"Other", "Season"})

    def test_transfer_teams_remain_separate(self):
        table = assemble(fixtures([context(), context(team="Other")])).scorecard
        self.assertEqual(len(table), 2)
        self.assertEqual(set(table.team), {"Other", "Team"})

    def test_competitions_remain_separate(self):
        table = assemble(fixtures([context(), context(competition_name="Other")])).scorecard
        self.assertEqual(len(table), 2)

    def test_two_players_same_name(self):
        table = assemble(fixtures([context(1), context(2)])).scorecard
        self.assertEqual(table.player_name.nunique(), 1)
        self.assertEqual(table.player_id.tolist(), [1, 2])

    def test_both_club_aliases_across_inputs(self):
        for alias, canonical in [("Marseille", "Olympique de Marseille"),
                                 ("Caen", "Stade Malherbe Caen")]:
            with self.subTest(alias=alias):
                data = fixtures([context(team=canonical)])
                data[0]["team"] = alias
                data[2].totals["team"] = alias
                data[3].totals["team"] = alias
                self.assertEqual(assemble(data).scorecard.team.tolist(), [canonical])

    def test_duplicate_base_rejected(self):
        base = pd.concat([self.data[0]] * 2, ignore_index=True)
        with self.assertRaisesRegex(ScorecardError, "base.*duplicate"):
            assemble_scorecard(base)

    def test_normalization_collision_rejected(self):
        base = pd.DataFrame([context(team="Caen"), context(team="Stade Malherbe Caen")])
        with self.assertRaisesRegex(ScorecardError, "duplicate"):
            assemble_scorecard(base)

    def test_duplicate_recovery_component_rejected(self):
        r = self.data[1]
        r.totals = pd.concat([r.totals, r.totals.iloc[:1]])
        with self.assertRaisesRegex(ScorecardError, "recovery_.*duplicate"):
            assemble(self.data)

    def test_duplicate_press_rejected(self):
        p = self.data[2]
        p.totals = pd.concat([p.totals] * 2)
        with self.assertRaisesRegex(ScorecardError, "press.*duplicate"):
            assemble(self.data)

    def test_duplicate_passing_rejected(self):
        p = self.data[3]
        p.totals = pd.concat([p.totals] * 2)
        with self.assertRaisesRegex(ScorecardError, "passing.*duplicate"):
            assemble(self.data)

    def test_unknown_or_missing_recovery_type(self):
        for kind in ["Clearance", None]:
            with self.subTest(kind=kind):
                data = fixtures()
                data[1].totals.loc[0, "event_type"] = kind
                with self.assertRaisesRegex(ScorecardError, "event_type"):
                    assemble(data)

    def test_counts_conserved_in_each_family(self):
        result = assemble(fixtures([context(1), context(2)]))
        components = result.diagnostics["components"]
        for prefix in RECOVERY_PREFIXES.values():
            self.assertEqual(components[prefix]["count_totals"], {"count": 2})
        self.assertEqual(components["press"]["count_totals"]["pressured_actions"], 4)
        self.assertEqual(components["passing"]["count_totals"]["prog_passes"], 2)

    def test_no_row_multiplication(self):
        table = assemble(fixtures([context(1), context(2)])).scorecard
        self.assertEqual(len(table), 2)
        self.assertFalse(table.duplicated(PLAYER_KEYS).any())

    def test_missing_recovery_component_is_not_zero(self):
        self.data[1].totals = self.data[1].totals.query("event_type != 'Tackle'")
        row = assemble(self.data).scorecard.iloc[0]
        self.assertFalse(row.recovery_tackle_present)
        self.assertTrue(pd.isna(row.recovery_tackle_count))
        self.assertTrue(row.recovery_interception_present)

    def test_missing_press_row_preserves_missingness(self):
        self.data[2].totals = self.data[2].totals.iloc[:0]
        row = assemble(self.data).scorecard.iloc[0]
        self.assertFalse(row.press_present)
        self.assertTrue(pd.isna(row.pressured_actions))
        self.assertTrue(pd.isna(row.press_resistance_rate))

    def test_missing_passing_row_preserves_missingness(self):
        self.data[3].totals = self.data[3].totals.iloc[:0]
        row = assemble(self.data).scorecard.iloc[0]
        self.assertFalse(row.passing_present)
        self.assertTrue(pd.isna(row.prog_passes))
        self.assertTrue(pd.isna(row.passing_difficulty_complete))

    def test_observed_zero_distinct_from_absent(self):
        self.data[1].totals.loc[0, ["count", "per90"]] = 0
        self.data[1].totals = self.data[1].totals.query("event_type != 'Tackle'")
        table = assemble(self.data).scorecard
        row = table.iloc[0]
        self.assertTrue(row.recovery_ball_recovery_present)
        self.assertEqual(row.recovery_ball_recovery_count, 0)
        self.assertFalse(row.recovery_tackle_present)
        self.assertTrue(pd.isna(row.recovery_tackle_count))

    def test_zero_and_missing_minutes_preserve_source_rates(self):
        for minutes, status in [(0.0, "zero_minutes"), (np.nan, "missing_minutes")]:
            with self.subTest(minutes=minutes):
                row = assemble(fixtures([context(minutes=minutes)])).scorecard.iloc[0]
                self.assertEqual(row.recovery_tackle_rate_status, status)
                self.assertEqual(row.passing_rate_status, status)
                self.assertTrue(pd.isna(row.recovery_tackle_per90))
                self.assertTrue(pd.isna(row.prog_passes_p90))
                self.assertEqual(row.press_resistance_rate, 100)

    def test_conflicting_base_exposure_rejected(self):
        self.data[0]["minutes"] = 181.0
        with self.assertRaisesRegex(ScorecardError, "conflicting minutes.*1"):
            assemble(self.data)

    def test_conflicting_metric_exposure_without_base_minutes(self):
        base = self.data[0].drop(columns="minutes")
        self.data[2].totals["minutes"] = 181.0
        with self.assertRaisesRegex(ScorecardError, "conflicting minutes"):
            assemble_scorecard(base, recovery=self.data[1], press=self.data[2])

    def test_conflicting_minutes_between_recovery_components(self):
        self.data[1].totals.loc[0, "minutes"] = 181.0
        with self.assertRaisesRegex(ScorecardError, "conflicting minutes"):
            assemble_scorecard(self.data[0][PLAYER_KEYS], recovery=self.data[1])

    def test_missing_minutes_not_filled_from_other_inputs(self):
        self.data[2].totals["minutes"] = np.nan
        row = assemble(self.data).scorecard.iloc[0]
        self.assertEqual(row.minutes, 180)
        self.assertTrue(pd.isna(row.press_minutes))

    def test_optional_press_exposure_absent(self):
        self.data[2].totals = self.data[2].totals.drop(columns="minutes")
        row = assemble(self.data).scorecard.iloc[0]
        self.assertTrue(row.press_present)
        self.assertTrue(pd.isna(row.press_minutes))

    def test_calibration_metadata_preserved_without_verification_claim(self):
        result = assemble(self.data)
        self.assertEqual(result.scorecard.passing_difficulty_scope.tolist(), ["explicit synthetic cohort"])
        self.assertTrue(result.scorecard.passing_difficulty_complete.all())
        self.assertEqual(result.diagnostics["passing_reference"],
                         {"scope": "explicit synthetic cohort", "declared_complete": True,
                          "independently_verified": False})

    def test_sample_reference_and_diagnostic_rejected(self):
        with self.assertRaisesRegex(ScorecardError, "declared-complete"):
            assemble_scorecard(self.data[0], passing=replace(self.data[3], difficulty_complete=False))
        with self.assertRaisesRegex(ScorecardError, "PassingResult"):
            assemble_scorecard(self.data[0], passing=self.data[3].totals)

    def test_no_ranking_rating_eligibility_or_index_columns(self):
        table = assemble(self.data).scorecard
        forbidden = ["percentile", "rating", "tier", "eligible", "overall", "score", "weight", "rank"]
        self.assertFalse([c for c in table if any(word in c for word in forbidden)])

    def test_no_threshold_filter(self):
        table = assemble(fixtures([context(minutes=1.0)])).scorecard
        self.assertEqual(len(table), 1)
        self.assertEqual(table.pressured_actions.tolist(), [2])

    def test_input_immutability(self):
        originals = copy.deepcopy(self.data)
        assemble(self.data)
        pd.testing.assert_frame_equal(self.data[0], originals[0])
        for result, original in zip(self.data[1:], originals[1:]):
            for field, value in vars(result).items():
                previous = getattr(original, field)
                if isinstance(value, pd.DataFrame):
                    pd.testing.assert_frame_equal(value, previous)
                elif field == "identity":
                    pd.testing.assert_frame_equal(value.events, previous.events)
                else:
                    self.assertEqual(value, previous)

    def test_determinism_with_reordered_rows_and_columns(self):
        data = fixtures([context(2), context(1)])
        expected = assemble(data)
        shuffled = copy.deepcopy(data)
        shuffled = (shuffled[0].iloc[::-1, ::-1], *shuffled[1:])
        for result in shuffled[1:]:
            result.totals = result.totals.iloc[::-1, ::-1]
        actual = assemble(shuffled)
        pd.testing.assert_frame_equal(actual.scorecard, expected.scorecard)
        self.assertEqual(actual.diagnostics, expected.diagnostics)

    def test_base_only_and_empty_base(self):
        for base in [self.data[0], self.data[0].iloc[:0]]:
            with self.subTest(rows=len(base)):
                result = assemble_scorecard(base)
                self.assertEqual(len(result.scorecard), len(base))
                self.assertFalse(result.scorecard.press_present.any())
                self.assertTrue(result.scorecard.prog_passes.isna().all())

    def test_all_empty_actual_metric_contracts(self):
        base, r, p, a = self.data
        empty = base.iloc[:0]
        r = replace(r, totals=r.totals.iloc[:0])
        p = replace(p, totals=p.totals.iloc[:0])
        a = replace(a, totals=a.totals.iloc[:0])
        result = assemble_scorecard(empty, recovery=r, press=p, passing=a)
        self.assertTrue(result.scorecard.empty)
        self.assertEqual(list(result.scorecard), list(assemble(self.data).scorecard))

    def test_metric_contexts_absent_from_base_rejected_all_families(self):
        for name, result in zip(["recovery", "press", "passing"], self.data[1:]):
            with self.subTest(family=name):
                with self.assertRaisesRegex(ScorecardError, "absent from base.*player_id"):
                    assemble_scorecard(self.data[0].iloc[:0], **{name: result})

    def test_only_keys_base_allowed_without_descriptive_inference(self):
        table = assemble_scorecard(self.data[0][PLAYER_KEYS], press=self.data[2]).scorecard
        self.assertNotIn("position_group", table)
        self.assertNotIn("minutes", table)

    def test_base_column_collision_rejected(self):
        with self.assertRaisesRegex(ScorecardError, "unsupported columns.*prog_passes"):
            assemble_scorecard(self.data[0].assign(prog_passes=99))

    def test_duplicate_column_labels_rejected(self):
        base = pd.concat([self.data[0], self.data[0][["minutes"]]], axis=1)
        with self.assertRaisesRegex(ScorecardError, "unique column"):
            assemble_scorecard(base)

    def test_missing_metric_column_rejected(self):
        self.data[2].totals = self.data[2].totals.drop(columns="press_resistance_rate")
        with self.assertRaisesRegex(ScorecardError, "missing columns.*press_resistance_rate"):
            assemble(self.data)

    def test_large_ids_and_counts_remain_exact_with_missing_rows(self):
        large = 2**53 + 1
        data = fixtures([context(large), context(2)])
        data[1].totals = data[1].totals.loc[data[1].totals.player_id.eq(large)].copy()
        data[1].totals["count"] = large
        table = assemble(data).scorecard
        self.assertEqual(table.player_id.tolist(), [2, large])
        self.assertEqual(table.recovery_tackle_count.iloc[1], large)
        self.assertTrue(pd.isna(table.recovery_tackle_count.iloc[0]))

    def test_invalid_ids_and_exposure_rejected(self):
        for column, value in [("player_id", True), ("player_id", 1.5), ("minutes", -1),
                              ("minutes", np.inf), ("minutes", "180"), ("minutes", True)]:
            with self.subTest(column=column, value=value):
                base = self.data[0].copy()
                base[column] = value
                with self.assertRaises(ScorecardError):
                    assemble_scorecard(base)

    def test_present_na_value_diagnostic_distinct_from_absence(self):
        self.data[2].totals["pressured_dribble_completion_rate"] = np.nan
        result = assemble(self.data)
        diag = result.diagnostics["components"]["press"]
        self.assertEqual(diag["present_na_values"]["pressured_dribble_completion_rate"], 1)
        self.assertEqual(diag["present_rows"], 1)
        self.assertEqual(diag["absent_base_rows"], 0)
        self.assertTrue(pd.isna(result.scorecard.pressured_dribble_completion_rate.iloc[0]))

    def test_nonzero_passing_value_and_observed_zero_from_real_interface(self):
        base = self.data[0]
        lookup = pd.DataFrame(columns=[*NAME_KEYS, "player_id"])
        events = pd.DataFrame([passing_event(player_id=1),
                               passing_event("short", player_id=1, pass_end_location=[35, 40])])
        failed = pd.DataFrame([passing_event("ref-failure", player_id=1, pass_outcome="Incomplete")])
        cohort = pd.concat([events, failed], ignore_index=True)
        result = integrate_progressive_passing(events, lookup, base[PLAYER_KEYS],
                                              base[[*PLAYER_KEYS, "minutes"]], reference=reference(cohort))
        table = assemble_scorecard(base, passing=result).scorecard
        self.assertEqual(table.value_sum.iloc[0], 20)
        self.assertEqual(table.pass_value_p90.iloc[0], 10)
        zero = integrate_progressive_passing(events.iloc[1:], lookup, base[PLAYER_KEYS],
                                            base[[*PLAYER_KEYS, "minutes"]], reference=reference(cohort))
        row = assemble_scorecard(base, passing=zero).scorecard.iloc[0]
        self.assertTrue(row.passing_present)
        self.assertEqual(row.prog_passes, 0)
        self.assertTrue(pd.isna(row.prog_completion_pct))
        self.assertFalse(row.press_present)
        self.assertTrue(pd.isna(row.pressured_actions))

    def test_empty_outputs_directly_from_upstream_integrators(self):
        base = self.data[0]
        e = pd.DataFrame([recovery_event(), passing_event("p", under_pressure=False,
                                                        dribble_outcome=None)])
        empty = e.iloc[:0]
        lookup = pd.DataFrame(columns=[*NAME_KEYS, "player_id"])
        r = integrate_recovery(empty, lookup, base, base[PLAYER_KEYS])
        p = integrate_press_resistance(empty, lookup, base[PLAYER_KEYS])
        a = integrate_progressive_passing(empty, lookup, base[PLAYER_KEYS], base,
                                          reference=reference(e))
        row = assemble_scorecard(base, recovery=r, press=p, passing=a).scorecard.iloc[0]
        self.assertFalse(row.press_present or row.passing_present or row.recovery_tackle_present)

    def test_normalized_duplicate_components_rejected(self):
        for name, index in [("recovery", 1), ("press", 2), ("passing", 3)]:
            with self.subTest(name=name):
                data = fixtures([context(team="Caen")])
                table = data[index].totals
                duplicate = table.iloc[:1].copy()
                duplicate["team"] = "Caen"
                data[index].totals = pd.concat([table, duplicate], ignore_index=True)
                with self.assertRaisesRegex(ScorecardError, "duplicate"):
                    assemble(data)

    def test_invalid_status_and_unsupported_source_fields_rejected(self):
        data = fixtures()
        data[3].totals["rate_status"] = "missing_minutes"
        with self.assertRaisesRegex(ScorecardError, "rate_status conflicts"):
            assemble(data)
        self.data[2].totals["prog_passes"] = 1
        with self.assertRaisesRegex(ScorecardError, "unsupported columns"):
            assemble(self.data)

    def test_failed_assembly_does_not_mutate_inputs(self):
        self.data[0]["minutes"] = 12.0
        before = copy.deepcopy(self.data)
        with self.assertRaises(ScorecardError):
            assemble(self.data)
        pd.testing.assert_frame_equal(self.data[0], before[0])
        for actual, original in zip(self.data[1:], before[1:]):
            pd.testing.assert_frame_equal(actual.totals, original.totals)


if __name__ == "__main__":
    unittest.main()
