"""Synthetic Level A integration tests; explicit cohorts are fixtures, not season claims."""
import unittest
from dataclasses import replace
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.identity import IdentityError, PLAYER_KEYS, UnresolvedIdentityError
from src.metrics.progressive_passes import distance_to_goal, flag_progressive, prepare_passes
from src.passing import (
    PassingError, calibrate_difficulty, inspect_progressive_passing, integrate_progressive_passing,
)


def event(event_id="e1", player="Player", **overrides):
    return dict(id=event_id, match_id=1, player=player, team="Team", competition_name="League",
                season_name="Season", type="Pass", location=[30, 40], pass_end_location=[70, 40],
                pass_type=None, pass_outcome=None, pass_length=None) | overrides


def spelling(player_id=1, name="Player", **context):
    return dict(player_id=player_id, player_name_raw=name, team="Team",
                competition_name="League", season_name="Season") | context


def setup(rows=None, aliases=None):
    e = pd.DataFrame(rows or [event()])
    x = pd.DataFrame(aliases or [spelling()])
    p = x[PLAYER_KEYS].drop_duplicates().reset_index(drop=True)
    return e, x, p, p.assign(minutes=180.0)


def reference(e, complete=True):
    return calibrate_difficulty(e, scope="explicit synthetic cohort", complete=complete)


def run(rows=None, aliases=None):
    e, x, p, m = setup(rows, aliases)
    return integrate_progressive_passing(e, x, p, m, reference=reference(e))


class PassingTests(unittest.TestCase):
    def test_open_play_missing_recovery_interception_types(self):
        e, x, p, m = setup([event(str(i), pass_type=t) for i, t in enumerate([None, "Recovery", "Interception"])])
        out = integrate_progressive_passing(e, x, p, m, reference=reference(e))
        self.assertEqual(out.preparation["measurable"], 3)
        self.assertEqual(out.totals.prog_passes.tolist(), [3])

    def test_set_pieces_and_nonpasses_accounted_separately(self):
        rows = [event(), *[event(str(i), pass_type=t) for i, t in enumerate(
            ["Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in"])], event("carry", type="Carry")]
        out = run(rows)
        self.assertEqual(out.preparation["non_open_play"], 5)
        self.assertEqual(out.preparation["non_pass"], 1)
        self.assertEqual(len(out.event_accounting), 7)

    def test_unknown_and_injury_clearance_are_excluded(self):
        out = run([event(), event("u", pass_outcome="Unknown"), event("i", pass_outcome="Injury Clearance")])
        self.assertEqual(out.preparation["excluded_outcome"], 2)
        self.assertEqual(out.totals.prog_attempts.tolist(), [1])

    def test_incomplete_pass_attempts_not_successes(self):
        out = run([event(), event("fail", pass_outcome="Incomplete")])
        row = out.totals.iloc[0]
        self.assertEqual((row.prog_attempts, row.prog_passes, row.third_cross), (2, 1, 1))
        self.assertEqual(row.prog_completion_pct, 50)

    def test_distance_to_attacking_goal(self):
        np.testing.assert_allclose(distance_to_goal([120, 60, 120], [40, 40, 30]), [0, 60, 10])

    def test_progression_exact_ratio_and_forward_boundaries(self):
        out = run([event(location=[80, 40], pass_end_location=[90, 40]),
                   event("ratio", location=[80, 40], pass_end_location=[89.999, 40]),
                   event("forward", location=[110, 40], pass_end_location=[119, 40])])
        self.assertEqual(out.identity.events.prog_attempt.tolist(), [True, False, False])

    def test_third_crossings_and_boundary_placement(self):
        out = run([event(location=[30, 40], pass_end_location=[40, 40]),
                   event("cross", location=[60, 40], pass_end_location=[80, 40]),
                   event("same", location=[45, 40], pass_end_location=[75, 40])])
        self.assertEqual(out.identity.events.start_third.tolist(), [0, 1, 1])
        self.assertEqual(out.identity.events.end_third.tolist(), [1, 2, 1])
        self.assertEqual(out.identity.events.third_cross.tolist(), [False, True, False])

    def test_length_bands_are_left_closed(self):
        e, x, p, m = setup([event(str(i), pass_length=v) for i, v in enumerate([0, 14.999, 15, 29.999, 30])])
        out = integrate_progressive_passing(e, x, p, m, reference=reference(e))
        self.assertEqual(out.identity.events.length_band.tolist(), ["0-15", "0-15", "15-30", "15-30", "30+"])

    def test_missing_pass_length_uses_euclidean_distance(self):
        out = run([event(location=[30, 20], pass_end_location=[60, 60])])
        self.assertEqual(out.identity.events.length.iloc[0], 50)

    def test_difficulty_includes_outsiders_and_nonprogressive_passes(self):
        e, x, p, m = setup([event(), event("outside", player="Outside", pass_outcome="Incomplete",
                                         location=[30, 40], pass_end_location=[10, 40], pass_length=40)],
                            [spelling(), spelling(2, "Outside")])
        ref = reference(e)
        a = integrate_progressive_passing(e, x, p[p.player_id.eq(1)], m, reference=ref)
        b = integrate_progressive_passing(e, x, p, m, reference=ref)
        self.assertEqual(a.identity.events.p_hat.tolist(), [.5, .5])
        pd.testing.assert_series_equal(a.identity.events.p_hat, b.identity.events.p_hat)
        self.assertEqual(a.totals.value_sum.iloc[0], 20)

    def test_difficulty_is_separate_by_competition_season_third_band(self):
        rows = [event(), event("failure", pass_outcome="Incomplete"),
                event("otherseason", season_name="Other"), event("otherleague", competition_name="Other"),
                event("third", location=[50, 40], pass_end_location=[90, 40]), event("short", pass_length=10)]
        e, x, p, m = setup(rows)
        diagnostic = inspect_progressive_passing(e, x, p, reference=reference(e, complete=False))
        self.assertEqual(diagnostic.identity.events.p_hat.tolist(), [.5, .5, 1, 1, 1, 1])

    def test_streaming_cell_fit_matches_whole_reference(self):
        e, _, _, _ = setup([event(), event("two", pass_outcome="Incomplete"), event("three")])
        a = reference(e)
        b = calibrate_difficulty([e.iloc[:1], e.iloc[1:]], scope="same cohort", complete=True)
        pd.testing.assert_frame_equal(a.cells, b.cells)
        self.assertEqual(b.accounting["raw_events"], 3)

    def test_sample_reference_blocked_in_production_but_labeled_in_diagnostic(self):
        e, x, p, m = setup()
        ref = reference(e, complete=False)
        with self.assertRaisesRegex(PassingError, "declared complete"):
            integrate_progressive_passing(e, x, p, m, reference=ref)
        diagnostic = inspect_progressive_passing(e, x, p, reference=ref)
        self.assertFalse(diagnostic.difficulty_complete)
        self.assertFalse(hasattr(diagnostic, "totals"))

    def test_reference_scope_and_completeness_are_explicit(self):
        e, _, _, _ = setup()
        for scope, complete in [("", True), ("sample", "yes"), (None, True)]:
            with self.subTest(scope=scope), self.assertRaises(PassingError):
                calibrate_difficulty(e, scope=scope, complete=complete)

    def test_duplicate_reference_batches_rejected(self):
        e, _, _, _ = setup()
        with self.assertRaisesRegex(PassingError, "across batches"):
            calibrate_difficulty([e, e], scope="duplicate", complete=True)

    def test_missing_calibration_cell_cannot_fall_back_to_reporting_batch(self):
        e, x, p, m = setup()
        ref = reference(e.assign(season_name="Other"))
        with self.assertRaisesRegex(PassingError, "no fallback"):
            integrate_progressive_passing(e, x, p, m, reference=ref)

    def test_mutated_reference_statistics_or_duplicate_cells_fail(self):
        e, x, p, m = setup()
        ref = reference(e)
        for bad in [ref.cells.assign(p_hat=.25), pd.concat([ref.cells, ref.cells], ignore_index=True)]:
            with self.assertRaises(PassingError):
                integrate_progressive_passing(e, x, p, m, reference=replace(ref, cells=bad))

    def test_missing_start_and_end_geometry_accounted(self):
        rows = [event(), event("start", location=None), event("end", pass_end_location=None),
                event("partial", location=[30]), event("nan", pass_end_location=[np.nan, 40])]
        out = run(rows)
        self.assertEqual(out.preparation["missing_geometry"], 4)
        self.assertEqual(out.preparation["measurable"], 1)
        self.assertEqual(out.event_accounting.category.tolist().count("missing_geometry"), 4)

    def test_exclusion_categories_are_exclusive_and_exhaustive(self):
        out = run([event(), event("non", type="Carry"), event("set", pass_type="Corner"),
                   event("unknown", pass_outcome="Unknown", location=None), event("missing", location=None)])
        self.assertEqual(out.event_accounting.category.tolist(),
                         ["measurable", "non_pass", "non_open_play", "excluded_outcome", "missing_geometry"])
        self.assertEqual(out.preparation["pass_events"], 4)
        self.assertEqual(out.preparation["open_play"], 3)

    def test_nonfinite_geometry_rejected_not_published(self):
        for row in [event(location=[np.inf, 40]), event(pass_length=-1), event(pass_length=np.inf)]:
            with self.subTest(row=row), self.assertRaises(PassingError):
                run([row])

    def test_verified_spellings_aggregate_stable_id(self):
        out = run([event(player="Rosa"), event("two", player="Roza")], [spelling(3054, "Rosa"), spelling(3054, "Roza")])
        self.assertEqual(out.totals.player_id.tolist(), [3054])
        self.assertEqual(out.totals.prog_passes.tolist(), [2])

    def test_marseille_and_caen_aliases_with_unique_minutes(self):
        for raw, canonical in [("Marseille", "Olympique de Marseille"), ("Caen", "Stade Malherbe Caen")]:
            e, x, p, m = setup([event(team=raw)], [spelling(team=canonical)])
            out = integrate_progressive_passing(e, x, p, m.assign(team=raw), reference=reference(e))
            self.assertEqual(out.totals.team.tolist(), [canonical])
            self.assertEqual(out.totals.prog_passes_p90.tolist(), [.5])

    def test_homonyms_transfers_and_seasons_stay_separate(self):
        contexts = [dict(team="A"), dict(team="B"), dict(team="B", season_name="Next")]
        out = run([event(str(i), **c) for i, c in enumerate(contexts)],
                  [spelling(1 if i != 1 else 2, **c) for i, c in enumerate(contexts)])
        self.assertEqual(len(out.totals), 3)
        self.assertEqual(out.totals.prog_passes.sum(), 3)

    def test_same_context_homonyms_with_trusted_ids(self):
        e, x, p, m = setup([event(player_id=1), event("two", player_id=2)], [spelling(), spelling(2)])
        out = integrate_progressive_passing(e, x.iloc[:0], p, m, reference=reference(e))
        self.assertEqual(out.totals.player_id.tolist(), [1, 2])

    def test_existing_player_id_restored_before_identity_and_conflicts_rejected(self):
        e, x, p, m = setup([event(player_id=1)])
        out = integrate_progressive_passing(e, x, p, m, reference=reference(e))
        self.assertEqual(out.identity.events.player_id.tolist(), [1])
        self.assertNotIn("player_id_x", out.identity.events)
        e["player_id"] = 2
        with self.assertRaisesRegex(IdentityError, "conflicts"):
            integrate_progressive_passing(e, x, p, m, reference=reference(e))

    def test_duplicate_raw_ids_even_when_excluded_rejected(self):
        for row in [event(), event(type="Carry"), event(pass_type="Corner")]:
            with self.assertRaisesRegex(PassingError, "duplicate event IDs"):
                run([event(), row])

    def test_ambiguous_or_duplicate_spelling_keys_rejected(self):
        for aliases in [[spelling(), spelling(2)], [spelling(), spelling()]]:
            with self.assertRaises(IdentityError):
                run(aliases=aliases)

    def test_unknown_identity_fails_closed_and_diagnostic_retains_it(self):
        e, x, p, m = setup([event(), event("unknown", player="Unknown")])
        ref = reference(e)
        with self.assertRaises(UnresolvedIdentityError):
            integrate_progressive_passing(e, x, p, m, reference=ref)
        diagnostic = inspect_progressive_passing(e, x, p, reference=ref)
        self.assertEqual(diagnostic.identity.counts["unresolved"], 1)
        self.assertEqual(diagnostic.accounting.measurable.sum(), 2)
        self.assertTrue(pd.isna(diagnostic.identity.events.loc[1, "in_population"]))

    def test_known_outside_counts_and_values_conserved(self):
        e, x, p, m = setup([event(), event("outside", player="Outside", pass_outcome="Incomplete")],
                            [spelling(), spelling(2, "Outside")])
        out = integrate_progressive_passing(e, x, p[p.player_id.eq(1)], m, reference=reference(e))
        self.assertEqual(out.accounting.measurable.tolist(), [1, 1, 0])
        self.assertEqual(out.accounting.prog_attempts.sum(), 2)
        self.assertEqual(out.totals.value_sum.sum(), 20)

    def test_identity_and_aggregation_loss_guards(self):
        from src.identity import resolve_events
        def broken(*args, **kwargs):
            result = resolve_events(*args, **kwargs)
            result.events = result.events.iloc[:0]
            return result
        with patch("src.passing.resolve_events", side_effect=broken):
            with self.assertRaisesRegex(PassingError, "identity join changed"):
                run()
        from src.metrics.progressive_passes import level_a_counts
        def doubled(passes):
            out = level_a_counts(passes)
            out["prog_attempts"] *= 2
            return out
        with patch("src.passing.level_a_counts", side_effect=doubled):
            with self.assertRaisesRegex(PassingError, "lost or multiplied"):
                run()

    def test_lost_nonprogressive_player_context_is_rejected_even_with_zero_sums(self):
        from src.metrics.progressive_passes import level_a_counts
        def dropping(passes):
            return level_a_counts(passes).iloc[:0]
        with patch("src.passing.level_a_counts", side_effect=dropping):
            with self.assertRaisesRegex(PassingError, "lost or invented observed player contexts"):
                run([event(location=[50, 40], pass_end_location=[30, 40])])

    def test_duplicate_normalized_minutes_rejected(self):
        e, x, p, m = setup([event(team="Caen")], [spelling(team="Caen")])
        m = pd.concat([m, m.assign(team="Stade Malherbe Caen")], ignore_index=True)
        with self.assertRaisesRegex(IdentityError, "duplicate stable"):
            integrate_progressive_passing(e, x, p, m, reference=reference(e))

    def test_per90_formulas_and_completion_percentage(self):
        out = run([event(), event("two", pass_outcome="Incomplete")])
        row = out.totals.iloc[0]
        self.assertEqual(row.prog_passes_p90, .5)
        self.assertEqual(row.third_cross_p90, .5)
        self.assertEqual(row.pass_value_p90, 10)
        self.assertEqual(row.prog_completion_pct, 50)

    def test_zero_and_missing_minutes_retain_counts(self):
        e, x, p, m = setup()
        ref = reference(e)
        for exposure, status in [(m.assign(minutes=0), "zero_minutes"),
                                 (m.assign(minutes=np.nan), "missing_minutes"),
                                 (m.iloc[:0], "missing_minutes")]:
            out = integrate_progressive_passing(e, x, p, exposure, reference=ref).totals
            self.assertEqual(out.prog_passes.tolist(), [1])
            self.assertTrue(out[["prog_passes_p90", "third_cross_p90", "pass_value_p90"]].isna().all().all())
            self.assertEqual(out.rate_status.tolist(), [status])

    def test_invalid_minutes_rejected(self):
        e, x, p, m = setup()
        for value in [-1, np.inf, True, "90"]:
            with self.assertRaises(PassingError):
                integrate_progressive_passing(e, x, p, m.assign(minutes=value), reference=reference(e))

    def test_zero_progressive_attempts_have_na_completion(self):
        row = run([event(location=[50, 40], pass_end_location=[30, 40])]).totals.iloc[0]
        self.assertEqual((row.prog_attempts, row.prog_passes, row.value_sum), (0, 0, 0))
        self.assertTrue(pd.isna(row.prog_completion_pct))

    def test_no_unobserved_player_rows_or_rankings_or_level_b_outputs(self):
        e, x, p, m = setup(aliases=[spelling(), spelling(2, "Absent")])
        out = integrate_progressive_passing(e, x, p, m, reference=reference(e))
        self.assertEqual(out.totals.player_id.tolist(), [1])
        for name in ["line_breaks_p90", "opponents_bypassed_p90", "pctl_pass_value_p90", "tier", "fifa_rating"]:
            self.assertNotIn(name, out.totals)

    def test_empty_reporting_sample_and_no_selected_players(self):
        e, x, p, m = setup()
        for reporting, selected in [(e.iloc[:0], p), (e, p.iloc[:0])]:
            out = integrate_progressive_passing(reporting, x, selected, m, reference=reference(e))
            self.assertTrue(out.totals.empty)

    def test_inputs_and_reference_unchanged(self):
        e, x, p, m = setup([event(), event("two", pass_outcome="Incomplete")])
        e.index, m.index = [9, 9], [20]
        saved = [d.copy(deep=True) for d in [e, x, p, m]]
        ref = reference(e)
        before = ref.cells.copy(deep=True)
        integrate_progressive_passing(e, x, p, m, reference=ref)
        inspect_progressive_passing(e, x, p, reference=ref)
        for actual, expected in zip([e, x, p, m], saved):
            pd.testing.assert_frame_equal(actual, expected)
        pd.testing.assert_frame_equal(ref.cells, before)


if __name__ == "__main__":
    unittest.main()
