"""Synthetic action and identity regressions against Pratyush V2 definitions."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.identity import IdentityError, PLAYER_KEYS, UnresolvedIdentityError
from src.metrics.press_actions import COUNT_COLS, PressResistanceError, add_completion_rates, classify_actions
from src.press_resistance import inspect_press_resistance, integrate_press_resistance


def event(event_id="e1", player="Player", **overrides):
    return dict(id=event_id, player=player, team="Team", competition_name="League",
                season_name="Season", type="Pass", under_pressure=True,
                pass_outcome=None, dribble_outcome=None) | overrides


def spelling(player_id=1, name="Player", **context):
    return dict(player_id=player_id, player_name_raw=name, team="Team",
                competition_name="League", season_name="Season") | context


def setup(rows=None, aliases=None):
    e = pd.DataFrame(rows or [event()])
    x = pd.DataFrame(aliases or [spelling()])
    p = x[PLAYER_KEYS].drop_duplicates().reset_index(drop=True)
    return e, x, p


def run(rows=None, aliases=None, **kwargs):
    return integrate_press_resistance(*setup(rows, aliases), **kwargs)


class PressResistanceTests(unittest.TestCase):
    def test_completed_pressured_pass(self):
        row = run().totals.iloc[0]
        self.assertEqual(row[COUNT_COLS].tolist(), [1, 1, 0, 0])
        self.assertEqual(row.pressured_pass_completion_rate, 100)
        self.assertTrue(pd.isna(row.pressured_dribble_completion_rate))
        self.assertEqual(row.press_resistance_rate, 100)

    def test_incomplete_pressured_pass(self):
        row = run([event(pass_outcome="Incomplete")]).totals.iloc[0]
        self.assertEqual(row[COUNT_COLS].tolist(), [1, 0, 0, 0])
        self.assertEqual(row.press_resistance_rate, 0)

    def test_completed_pressured_dribble(self):
        row = run([event(type="Dribble", dribble_outcome="Complete")]).totals.iloc[0]
        self.assertEqual(row[COUNT_COLS].tolist(), [0, 0, 1, 1])
        self.assertTrue(pd.isna(row.pressured_pass_completion_rate))
        self.assertEqual(row.pressured_dribble_completion_rate, 100)

    def test_incomplete_pressured_dribble(self):
        row = run([event(type="Dribble", dribble_outcome="Incomplete")]).totals.iloc[0]
        self.assertEqual(row[COUNT_COLS].tolist(), [0, 0, 1, 0])
        self.assertEqual(row.press_resistance_rate, 0)

    def test_missing_dribble_outcome_is_attempt_not_success(self):
        row = run([event(type="Dribble")]).totals.iloc[0]
        self.assertEqual(row[COUNT_COLS].tolist(), [0, 0, 1, 0])

    def test_unpressured_and_other_actions_excluded(self):
        for row in [event(under_pressure=False), event(type="Carry"), event(type="Dispossessed")]:
            with self.subTest(row=row):
                result = run([row])
                self.assertTrue(result.totals.empty)
                self.assertEqual(result.accounting.filtered.sum(), 0)

    def test_missing_pressure_excluded_for_object_and_nullable_flags(self):
        for flag in [None, np.nan, pd.NA]:
            e, x, p = setup([event(under_pressure=flag)])
            self.assertTrue(integrate_press_resistance(e, x, p).totals.empty)
        e, x, p = setup([event(), event("two"), event("three")])
        e["under_pressure"] = pd.Series([True, pd.NA, False], dtype="boolean")
        self.assertEqual(integrate_press_resistance(e, x, p).totals.pressured_actions.tolist(), [1])

    def test_nullable_outcome_storage_matches_original_object_definitions(self):
        e, x, p = setup([event(), event("two", type="Dribble"), event("three", type="Dribble")])
        e["pass_outcome"] = pd.Series([pd.NA, pd.NA, pd.NA], dtype="string")
        e["dribble_outcome"] = pd.Series([pd.NA, pd.NA, "Complete"], dtype="string")
        result = integrate_press_resistance(e, x, p)
        self.assertEqual(result.totals[COUNT_COLS].iloc[0].tolist(), [1, 1, 2, 1])

    def test_zero_action_rates_are_na_without_creating_population_metrics(self):
        counts = pd.DataFrame([{c: 0 for c in COUNT_COLS}])
        result = add_completion_rates(counts)
        self.assertTrue(result[["pressured_pass_completion_rate", "pressured_dribble_completion_rate",
                                "press_resistance_rate"]].isna().all().all())
        self.assertTrue(run([event(under_pressure=False)]).totals.empty)

    def test_combined_formula_is_action_weighted(self):
        row = run([event(), event("two", pass_outcome="Out"),
                   event("three", type="Dribble", dribble_outcome="Complete")]).totals.iloc[0]
        self.assertEqual(row.pressured_actions, 3)
        self.assertEqual(row.successful_pressured_actions, 2)
        self.assertAlmostEqual(row.press_resistance_rate, 100 * 2 / 3)
        self.assertEqual(row.pressured_pass_completion_rate, 50)
        self.assertEqual(row.pressured_dribble_completion_rate, 100)

    def test_v2_outcome_definition_matrix(self):
        # V2: all non-null pass outcomes fail, only exact Complete dribbles succeed.
        pass_outcomes = [None, "Incomplete", "Out", "Pass Offside", "Unknown", "Injury Clearance", ""]
        dribble_outcomes = [None, "Complete", "Incomplete", "complete", "Unknown"]
        rows = [event(f"p{i}", pass_outcome=v) for i, v in enumerate(pass_outcomes)]
        rows += [event(f"d{i}", type="Dribble", dribble_outcome=v) for i, v in enumerate(dribble_outcomes)]
        row = run(rows).totals.iloc[0]
        self.assertEqual(row[COUNT_COLS].tolist(), [7, 1, 5, 1])
        self.assertAlmostEqual(row.press_resistance_rate, 100 * 2 / 12)

    def test_set_piece_pass_not_excluded(self):
        self.assertEqual(run([event(pass_type="Corner")]).totals.pressured_actions.tolist(), [1])

    def test_explicit_population_not_hardcoded_to_v2_season_or_leagues(self):
        row = run().totals.iloc[0]
        self.assertEqual((row.competition_name, row.season_name), ("League", "Season"))
        self.assertNotIn("tier_eligible", row.index)
        self.assertNotIn("position_percentile", row.index)

    def test_verified_alternate_spellings_aggregate_by_id(self):
        result = run([event(player="Fernando Luiz Rosa"), event("two", player="Fernando Luiz Roza")],
                     [spelling(3054, "Fernando Luiz Rosa"), spelling(3054, "Fernando Luiz Roza")])
        self.assertEqual(result.totals.player_id.tolist(), [3054])
        self.assertEqual(result.totals.pressured_actions.tolist(), [2])

    def test_marseille_and_caen_aliases_in_all_joins(self):
        for raw, canonical in [("Marseille", "Olympique de Marseille"), ("Caen", "Stade Malherbe Caen")]:
            with self.subTest(raw=raw):
                e, x, p = setup([event(team=raw), event("two", team=canonical)], [spelling(team=canonical)])
                m = p.assign(team=raw, minutes=45)
                result = integrate_press_resistance(e, x, p, minutes=m)
                self.assertEqual(result.totals.team.tolist(), [canonical])
                self.assertEqual(result.totals.pressured_actions.tolist(), [2])
                self.assertEqual(result.totals.minutes.tolist(), [45])

    def test_same_name_different_ids_in_different_teams(self):
        result = run([event(team="A"), event("two", team="B")],
                     [spelling(team="A"), spelling(2, team="B")])
        self.assertEqual(result.totals.player_id.tolist(), [1, 2])

    def test_same_context_homonyms_with_trusted_supplied_ids(self):
        e, x, p = setup([event(player_id=1), event("two", player_id=2)], [spelling(), spelling(2)])
        result = integrate_press_resistance(e, x.iloc[:0], p)
        self.assertEqual(result.totals.player_id.tolist(), [1, 2])

    def test_transfers_seasons_and_competitions_stay_separate(self):
        contexts = [dict(team="A"), dict(team="B"), dict(team="B", season_name="Next"),
                    dict(team="B", competition_name="Other")]
        result = run([event(str(i), **c) for i, c in enumerate(contexts)],
                     [spelling(**c) for c in contexts])
        self.assertEqual(len(result.totals), 4)
        self.assertEqual(result.totals.pressured_actions.sum(), 4)

    def test_existing_player_id_is_preserved_without_suffixes(self):
        e, x, p = setup([event(player_id=1)])
        result = integrate_press_resistance(e, x, p)
        self.assertEqual(result.identity.events.player_id.tolist(), [1])
        self.assertNotIn("player_id_x", result.identity.events)
        self.assertNotIn("player_id_y", result.identity.events)

    def test_missing_supplied_id_uses_crosswalk(self):
        e, x, p = setup()
        e["player_id"] = pd.Series([pd.NA], dtype="Int64")
        self.assertEqual(integrate_press_resistance(e, x, p).totals.player_id.tolist(), [1])

    def test_supplied_id_conflict_rejected(self):
        with self.assertRaisesRegex(IdentityError, "conflicts"):
            run([event(player_id=2)])

    def test_missing_name_does_not_drop_selected_action(self):
        with self.assertRaises(UnresolvedIdentityError):
            run([event(player=None)])
        e, x, p = setup([event(player=None, player_id=1)])
        self.assertEqual(integrate_press_resistance(e, x, p).totals.pressured_actions.tolist(), [1])

    def test_duplicate_event_ids_even_if_excluded(self):
        for row in [event(), event(type="Carry"), event(under_pressure=False)]:
            with self.subTest(row=row), self.assertRaisesRegex(PressResistanceError, "duplicate event IDs"):
                run([event(), row])

    def test_ambiguous_and_duplicate_crosswalk_rejected(self):
        for aliases in [[spelling(), spelling(2)], [spelling(), spelling()]]:
            with self.subTest(aliases=aliases), self.assertRaises(IdentityError):
                run(aliases=aliases)

    def test_unresolved_fails_closed_in_production(self):
        with self.assertRaises(UnresolvedIdentityError) as caught:
            run([event(player="Unknown")])
        self.assertEqual(caught.exception.result.counts["unresolved"], 1)

    def test_diagnostic_accounts_for_attempts_and_completions_by_status(self):
        e, x, p = setup([event(), event("two", player="Outside", pass_outcome="Out"),
                         event("three", player="Unknown", type="Dribble", dribble_outcome="Complete")],
                        [spelling(), spelling(2, "Outside")])
        result = inspect_press_resistance(e, x, p[p.player_id.eq(1)])
        self.assertEqual(result.accounting.filtered.sum(), 3)
        self.assertEqual(result.accounting.completed.sum(), 2)
        self.assertEqual(result.identity.counts, dict(selected=1, outside_population=1, unresolved=1))
        self.assertEqual(result.accounting.unresolved_completed.sum(), 1)
        self.assertFalse(hasattr(result, "totals"))
        self.assertTrue(pd.isna(result.identity.events.loc[2, "in_population"]))

    def test_known_outside_events_are_not_unknown_or_player_metrics(self):
        e, x, p = setup([event(), event("two", player="Outside")], [spelling(), spelling(2, "Outside")])
        result = integrate_press_resistance(e, x, p[p.player_id.eq(1)])
        self.assertEqual(result.totals.player_id.tolist(), [1])
        self.assertEqual(result.accounting.outside_population.sum(), 1)

    def test_count_and_success_conservation(self):
        result = run([event(), event("two", type="Dribble", dribble_outcome="Complete"),
                      event("three", pass_outcome="Incomplete")])
        self.assertEqual(result.totals.pressured_actions.sum(), len(result.identity.events))
        self.assertEqual(result.totals.successful_pressured_actions.sum(), result.accounting.selected_completed.sum())
        self.assertTrue(result.totals.pressured_pass_completed.le(result.totals.pressured_pass_attempts).all())
        self.assertTrue(result.totals.pressured_dribble_completed.le(result.totals.pressured_dribble_attempts).all())

    def test_guard_detects_identity_row_loss(self):
        from src.identity import resolve_events
        def broken(*args, **kwargs):
            result = resolve_events(*args, **kwargs)
            result.events = result.events.iloc[:0]
            return result
        with patch("src.press_resistance.resolve_events", side_effect=broken):
            with self.assertRaisesRegex(PressResistanceError, "changed action IDs"):
                run()

    def test_guard_detects_aggregate_count_multiplication(self):
        from src.metrics.press_actions import aggregate_actions
        def broken(rows):
            out = aggregate_actions(rows)
            out["pressured_pass_attempts"] *= 2
            return out
        with patch("src.press_resistance.aggregate_actions", side_effect=broken):
            with self.assertRaisesRegex(PressResistanceError, "lost or multiplied"):
                run()

    def test_duplicate_normalized_minutes_keys_rejected(self):
        e, x, p = setup([event(team="Caen")], [spelling(team="Caen")])
        m = pd.concat([p.assign(minutes=90), p.assign(team="Stade Malherbe Caen", minutes=45)], ignore_index=True)
        with self.assertRaisesRegex(IdentityError, "duplicate stable"):
            integrate_press_resistance(e, x, p, minutes=m)

    def test_optional_unique_minutes_do_not_qualify_or_change_rates(self):
        e, x, p = setup()
        for value in [0, 1, 899, 900, 1000, np.nan]:
            with self.subTest(value=value):
                out = integrate_press_resistance(e, x, p, minutes=p.assign(minutes=value)).totals
                self.assertEqual(out.press_resistance_rate.tolist(), [100])
                self.assertEqual(out.pressured_actions.tolist(), [1])
        self.assertNotIn("minutes", integrate_press_resistance(e, x, p).totals)

    def test_missing_minutes_record_and_nullable_value_remain_missing(self):
        e, x, p = setup()
        for m in [p.assign(minutes=90).iloc[:0], p.assign(minutes=pd.Series([pd.NA], dtype="Float64"))]:
            out = integrate_press_resistance(e, x, p, minutes=m).totals
            self.assertTrue(out.minutes.isna().all())
            self.assertEqual(out.press_resistance_rate.tolist(), [100])

    def test_invalid_minutes_rejected(self):
        e, x, p = setup()
        for v in [-1, np.inf, True, "90"]:
            with self.subTest(v=v), self.assertRaises(PressResistanceError):
                integrate_press_resistance(e, x, p, minutes=p.assign(minutes=v))

    def test_unknown_counts_never_become_zero_and_invalid_counts_rejected(self):
        for v in [np.nan, np.inf, -1, .5, True, "1"]:
            counts = pd.DataFrame([{c: 0 for c in COUNT_COLS}])
            counts["pressured_pass_attempts"] = v
            with self.subTest(v=v), self.assertRaises(PressResistanceError):
                add_completion_rates(counts)

    def test_completed_cannot_exceed_attempts(self):
        counts = pd.DataFrame([dict(zip(COUNT_COLS, [1, 2, 0, 0]))])
        with self.assertRaisesRegex(PressResistanceError, "exceeds"):
            add_completion_rates(counts)

    def test_no_metrics_created_for_unobserved_population(self):
        e, x, p = setup(aliases=[spelling(), spelling(2, "Absent")])
        result = integrate_press_resistance(e, x, p)
        self.assertEqual(result.totals.player_id.tolist(), [1])
        self.assertTrue(integrate_press_resistance(e, x, p.iloc[:0]).totals.empty)

    def test_inputs_unchanged_nondefault_duplicate_indices(self):
        e, x, p = setup([event(), event("two", type="Dribble", dribble_outcome="Complete")])
        e.index = pd.Index([8, 8], name="source")
        m = p.assign(minutes=90)
        m.index = [20]
        before = [d.copy(deep=True) for d in [e, x, p, m]]
        result = integrate_press_resistance(e, x, p, minutes=m)
        inspect_press_resistance(e, x, p)
        self.assertEqual(result.identity.events.id.tolist(), ["e1", "two"])
        for actual, saved in zip([e, x, p, m], before):
            pd.testing.assert_frame_equal(actual, saved)

    def test_missing_duplicate_and_reserved_columns_fail(self):
        e, x, p = setup()
        for bad in [e.drop(columns="pass_outcome"), e.drop(columns="id"),
                    pd.concat([e, e[["id"]]], axis=1), e.assign(pressured_actions=1)]:
            with self.assertRaises(PressResistanceError):
                integrate_press_resistance(bad, x, p)


if __name__ == "__main__":
    unittest.main()
