"""Synthetic recovery integration regressions; no production identity evidence."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.identity import IdentityError, PLAYER_KEYS, UnresolvedIdentityError
from src.metrics.zones import assign_zone
from src.recovery import RecoveryError, inspect_recovery, integrate_recovery


def event(event_id="e1", player="Player", **overrides):
    row = dict(id=event_id, match_id=1, player=player, team="Team", competition_name="League",
               season_name="Season", type="Ball Recovery", location=[10, 10], duel_type=None,
               duel_outcome=None, interception_outcome=None, ball_recovery_recovery_failure=None)
    row.update(overrides)
    return row


def crosswalk(name="Player", player_id=1, **context):
    return dict(player_name_raw=name, player_id=player_id, team="Team", competition_name="League",
                season_name="Season") | context


def setup(rows=None, aliases=None, exposure=180.0):
    e = pd.DataFrame(rows or [event()])
    x = pd.DataFrame(aliases or [crosswalk()])
    p = x[PLAYER_KEYS].drop_duplicates().reset_index(drop=True)
    m = p.assign(minutes=exposure)
    return e, x, m, p


def run(rows=None, aliases=None, exposure=180.0):
    return integrate_recovery(*setup(rows, aliases, exposure))


class RecoveryTests(unittest.TestCase):
    def test_successful_tackles_only(self):
        rows = [event(str(i), type="Duel", duel_type="Tackle", duel_outcome=outcome)
                for i, outcome in enumerate(["Won", "Success In Play", "Success Out", "Lost In Play", None])]
        rows.append(event("aerial", type="Duel", duel_type="Aerial", duel_outcome="Won"))
        result = run(rows)
        self.assertEqual(result.totals.event_type.tolist(), ["Tackle"])
        self.assertEqual(result.totals["count"].tolist(), [3])

    def test_successful_interceptions_only(self):
        rows = [event(str(i), type="Interception", interception_outcome=outcome)
                for i, outcome in enumerate(["Won", "Success In Play", "Success Out", "Lost Out", None])]
        self.assertEqual(run(rows).totals["count"].tolist(), [3])

    def test_nonfailed_recoveries_only(self):
        rows = [event(str(i), ball_recovery_recovery_failure=flag)
                for i, flag in enumerate([None, False, True, np.nan])]
        self.assertEqual(run(rows).totals["count"].tolist(), [3])

    def test_nullable_recovery_failure_flags_keep_nonfailed_actions(self):
        e, x, m, p = setup([event(), event("two"), event("three")])
        e["ball_recovery_recovery_failure"] = pd.Series([pd.NA, False, True], dtype="boolean")
        result = integrate_recovery(e, x, m, p)
        self.assertEqual(result.totals["count"].tolist(), [2])
        self.assertTrue(pd.isna(e.ball_recovery_recovery_failure.iloc[0]))

    def test_all_three_components_separate(self):
        result = run([event(), event("t", type="Duel", duel_type="Tackle", duel_outcome="Won"),
                      event("i", type="Interception", interception_outcome="Success Out"),
                      event("pass", type="Pass")])
        self.assertEqual(result.totals.set_index("event_type")["count"].to_dict(),
                         {"Tackle": 1, "Interception": 1, "Ball Recovery": 1})
        self.assertEqual(result.accounting.extracted.sum(), 3)
        self.assertEqual(result.accounting.selected.sum(), 3)

    def test_missing_and_offpitch_locations_remain_in_totals(self):
        result = run([event(location=None), event("off", location=[-1, 10]), event("known")])
        self.assertEqual(result.totals["count"].sum(), 3)
        self.assertEqual(result.by_zone["count"].sum(), 1)
        self.assertEqual(result.identity.events.zone.isna().sum(), 2)

    def test_original_zone_edges_and_invalid_coordinates(self):
        z = assign_zone([0, 119, 120, 40, 0], [0, 79, 80, 0, 79])
        self.assertEqual(list(z), [1, 9, 9, 2, 7])
        self.assertTrue(assign_zone([np.nan, -1, 10], [5, 5, 100]).isna().all())
        self.assertEqual(run().by_zone.zone.tolist(), [1])

    def test_verified_spellings_aggregate_on_id(self):
        result = run([event(player="Fernando Luiz Rosa"), event("two", player="Fernando Luiz Roza")],
                     [crosswalk("Fernando Luiz Rosa", 3054), crosswalk("Fernando Luiz Roza", 3054)])
        self.assertEqual(result.totals.player_id.tolist(), [3054])
        self.assertEqual(result.totals["count"].tolist(), [2])
        self.assertEqual(result.identity.events.id.tolist(), ["e1", "two"])

    def test_known_club_aliases_share_counts_and_minutes(self):
        for alias, canonical in [("Marseille", "Olympique de Marseille"), ("Caen", "Stade Malherbe Caen")]:
            with self.subTest(alias=alias):
                e, x, m, p = setup([event(team=alias), event("two", team=canonical)],
                                    [crosswalk(team=canonical)])
                m["team"] = alias
                result = integrate_recovery(e, x, m, p)
                self.assertEqual(result.totals.team.tolist(), [canonical])
                self.assertEqual(result.totals["count"].tolist(), [2])
                self.assertEqual(result.totals.per90.tolist(), [1.0])

    def test_same_name_different_ids_in_different_teams(self):
        result = run([event(team="A"), event("two", team="B")],
                     [crosswalk(team="A"), crosswalk(player_id=2, team="B")])
        self.assertEqual(result.totals.player_id.tolist(), [1, 2])
        self.assertEqual(result.totals["count"].tolist(), [1, 1])

    def test_same_context_homonyms_remain_distinct_with_trusted_supplied_ids(self):
        e, x, m, p = setup([event(player_id=1), event("two", player_id=2)],
                            [crosswalk(), crosswalk(player_id=2)])
        # Names alone are ambiguous; pre-supplied trusted IDs need no spelling guess.
        result = integrate_recovery(e, x.iloc[:0], m, p)
        self.assertEqual(result.totals.player_id.tolist(), [1, 2])
        self.assertEqual(result.totals["count"].tolist(), [1, 1])

    def test_transfers_and_seasons_remain_separate(self):
        result = run([event(team="A"), event("two", team="B"), event("three", team="B", season_name="Next")],
                     [crosswalk(team="A"), crosswalk(team="B"), crosswalk(team="B", season_name="Next")])
        self.assertEqual(len(result.totals), 3)
        self.assertEqual(result.totals["count"].tolist(), [1, 1, 1])
        self.assertEqual(result.totals.player_id.tolist(), [1, 1, 1])

    def test_duplicate_raw_ids_rejected_even_for_excluded_actions(self):
        for kind in ["Ball Recovery", "Pass"]:
            with self.subTest(kind=kind), self.assertRaisesRegex(RecoveryError, "duplicate event IDs"):
                run([event(), event(type=kind)])

    def test_ambiguous_crosswalk_rejected(self):
        with self.assertRaisesRegex(IdentityError, "ambiguous"):
            run(aliases=[crosswalk(), crosswalk(player_id=2)])

    def test_duplicate_crosswalk_cannot_multiply_counts(self):
        with self.assertRaisesRegex(IdentityError, "duplicate normalized"):
            run(aliases=[crosswalk(), crosswalk()])

    def test_conflicting_supplied_player_id_rejected(self):
        with self.assertRaisesRegex(IdentityError, "conflicts"):
            run([event(player_id=2)])

    def test_duplicate_minutes_rejected(self):
        e, x, m, p = setup()
        with self.assertRaisesRegex(IdentityError, "duplicate stable"):
            integrate_recovery(e, x, pd.concat([m, m], ignore_index=True), p)

    def test_alias_collision_in_minutes_rejected(self):
        e, x, m, p = setup([event(team="Caen")], [crosswalk(team="Caen")])
        other = m.assign(team="Stade Malherbe Caen")
        with self.assertRaisesRegex(IdentityError, "duplicate stable"):
            integrate_recovery(e, x, pd.concat([m, other], ignore_index=True), p)

    def test_unresolved_recovery_blocks_production(self):
        e, x, m, p = setup([event(), event("two", player="Unknown")])
        with self.assertRaises(UnresolvedIdentityError) as caught:
            integrate_recovery(e, x, m, p)
        self.assertEqual(caught.exception.result.counts["unresolved"], 1)
        self.assertEqual(len(caught.exception.result.events), 2)

    def test_diagnostic_conserves_unresolved_and_outside_counts(self):
        e, x, m, p = setup([event(), event("two", player="Outside"), event("three", player="Unknown")],
                            [crosswalk(), crosswalk("Outside", 2)])
        p = p[p.player_id.eq(1)]
        diagnostic = inspect_recovery(e, x, p)
        row = diagnostic.accounting.set_index("event_type").loc["Ball Recovery"]
        self.assertEqual(row.to_dict(), dict(extracted=3, selected=1, outside_population=1, unresolved=1))
        self.assertFalse(hasattr(diagnostic, "totals"))
        self.assertEqual(len(diagnostic.identity.events), 3)
        self.assertTrue(pd.isna(diagnostic.identity.events.loc[2, "in_population"]))

    def test_known_outside_is_explicitly_accounted_for(self):
        e, x, m, p = setup([event(), event("two", player="Outside")],
                            [crosswalk(), crosswalk("Outside", 2)])
        result = integrate_recovery(e, x, m, p[p.player_id.eq(1)])
        self.assertEqual(result.totals["count"].sum(), 1)
        self.assertEqual(result.accounting.outside_population.sum(), 1)
        self.assertEqual(result.accounting.extracted.sum(), 2)

    def test_count_conservation_per_type_across_aliases(self):
        rows = [event(str(i), player=name, **kind) for i, (name, kind) in enumerate([
            ("A", {}), ("B", {}), ("A", dict(type="Duel", duel_type="Tackle", duel_outcome="Won")),
            ("B", dict(type="Interception", interception_outcome="Won"))])]
        result = run(rows, [crosswalk("A"), crosswalk("B")])
        self.assertEqual(result.totals["count"].sum(), 4)
        for row in result.accounting.to_dict("records"):
            actual = result.totals.loc[result.totals.event_type.eq(row["event_type"]), "count"].sum()
            self.assertEqual(actual, row["extracted"])

    def test_guard_detects_loss_from_identity_join(self):
        from src.identity import resolve_events
        e, x, m, p = setup([event(), event("two")])
        def losing_join(*args, **kwargs):
            result = resolve_events(*args, **kwargs)
            result.events = result.events.iloc[:1]
            return result
        with patch("src.recovery.resolve_events", side_effect=losing_join):
            with self.assertRaisesRegex(RecoveryError, "changed recovery IDs"):
                integrate_recovery(e, x, m, p)

    def test_per90_formula(self):
        result = run([event(), event("two"), event("three")], exposure=270)
        self.assertEqual(result.totals.per90.tolist(), [1.0])
        self.assertEqual(result.totals.rate_status.tolist(), ["ok"])

    def test_zero_minutes_preserves_count_without_rate(self):
        result = run(exposure=0)
        self.assertEqual(result.totals["count"].tolist(), [1])
        self.assertTrue(result.totals.per90.isna().all())
        self.assertEqual(result.totals.rate_status.tolist(), ["zero_minutes"])

    def test_missing_minutes_record_preserves_count_without_rate(self):
        e, x, m, p = setup()
        result = integrate_recovery(e, x, m.iloc[:0], p)
        self.assertTrue(result.totals.per90.isna().all())
        self.assertEqual(result.totals["count"].tolist(), [1])
        self.assertEqual(result.totals.rate_status.tolist(), ["missing_minutes"])

    def test_missing_minutes_value_preserves_count_without_rate(self):
        result = run(exposure=np.nan)
        self.assertTrue(result.totals.per90.isna().all())
        self.assertEqual(result.totals.rate_status.tolist(), ["missing_minutes"])

    def test_invalid_minutes_fail(self):
        for value in [-1, np.inf, -np.inf, True, "90"]:
            with self.subTest(value=value), self.assertRaises(RecoveryError):
                run(exposure=value)

    def test_missing_and_duplicate_schema_fail(self):
        e, x, m, p = setup()
        with self.assertRaises(RecoveryError):
            integrate_recovery(e.drop(columns="id"), x, m, p)
        with self.assertRaises(RecoveryError):
            integrate_recovery(pd.concat([e, e[["id"]]], axis=1), x, m, p)
        with self.assertRaises(RecoveryError):
            integrate_recovery(e, x, m.drop(columns="minutes"), p)

    def test_no_zero_filling_unobserved_components_or_players(self):
        e, x, m, p = setup(aliases=[crosswalk(), crosswalk("No events", 2)])
        result = integrate_recovery(e, x, m, p)
        self.assertEqual(result.totals.event_type.tolist(), ["Ball Recovery"])
        self.assertEqual(result.totals.player_id.tolist(), [1])

    def test_unknown_unsuccessful_actions_are_excluded_before_identity(self):
        result = run([event(), event("excluded", player="Unknown", type="Duel", duel_type="Tackle", duel_outcome="Lost Out")])
        self.assertEqual(result.totals["count"].sum(), 1)

    def test_empty_extraction_is_not_zero_grid(self):
        result = run([event(type="Pass")])
        self.assertTrue(result.totals.empty)
        self.assertTrue(result.by_zone.empty)
        self.assertEqual(result.accounting.extracted.sum(), 0)

    def test_all_known_outside_events_produce_no_selected_metrics(self):
        e, x, m, p = setup()
        result = integrate_recovery(e, x, m, p.iloc[:0])
        self.assertTrue(result.totals.empty)
        self.assertEqual(result.accounting.outside_population.sum(), 1)

    def test_nullable_missing_minutes_stay_unknown(self):
        e, x, m, p = setup()
        m["minutes"] = pd.Series([pd.NA], dtype="Float64")
        result = integrate_recovery(e, x, m, p)
        self.assertTrue(result.totals.per90.isna().all())
        self.assertEqual(result.totals["count"].tolist(), [1])

    def test_inputs_unchanged_with_nondefault_indices(self):
        e, x, m, p = setup([event(), event("two")])
        e.index, m.index = [9, 9], [20]
        before = [d.copy(deep=True) for d in [e, x, m, p]]
        integrate_recovery(e, x, m, p)
        inspect_recovery(e, x, p)
        for actual, saved in zip([e, x, m, p], before):
            pd.testing.assert_frame_equal(actual, saved)


if __name__ == "__main__":
    unittest.main()
