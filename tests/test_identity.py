"""Synthetic identity evidence only; these fixtures are not a production crosswalk."""
import unittest

import numpy as np
import pandas as pd

from src.identity import (
    CONTEXT, NAME_KEYS, PLAYER_KEYS, IdentityError, UnresolvedIdentityError,
    normalize_player_names, normalize_team_names, prepare_crosswalk,
    resolve_events, validate_population,
)


def alias(name="Player", player_id=1, team="Team", season="Season", competition="League"):
    return dict(player_name_raw=name, player_id=player_id, team=team,
                competition_name=competition, season_name=season)


def event(name="Player", event_id="e1", team="Team", season="Season", competition="League"):
    return dict(id=event_id, player=name, team=team, competition_name=competition,
                season_name=season, metric=np.nan)


def population(*rows):
    return pd.DataFrame(rows or [alias()])[PLAYER_KEYS]


def lookup(*rows):
    return pd.DataFrame(rows or [alias()])


def events(*rows):
    return pd.DataFrame(rows or [event()])


class IdentityTests(unittest.TestCase):
    def test_two_verified_spellings_share_stable_id(self):
        result = resolve_events(events(event("Name One"), event("Name Two", "e2")),
                                lookup(alias("Name One"), alias("Name Two")), population())
        self.assertEqual(result.events.player_id.tolist(), [1, 1])
        self.assertEqual(result.events.id.tolist(), ["e1", "e2"])
        self.assertEqual(result.counts, dict(selected=2, outside_population=0, unresolved=0))

    def test_same_name_different_players_in_different_teams(self):
        x = lookup(alias(player_id=1, team="A"), alias(player_id=2, team="B"))
        e = events(event(team="A"), event(team="B", event_id="e2"))
        result = resolve_events(e, x, x[PLAYER_KEYS])
        self.assertEqual(result.events.player_id.tolist(), [1, 2])

    def test_marseille_alias_both_sides(self):
        for raw, trusted in [("Marseille", "Olympique de Marseille"),
                             ("Olympique de Marseille", "Marseille")]:
            with self.subTest(raw=raw):
                result = resolve_events(events(event(team=raw)), lookup(alias(team=trusted)),
                                        population(alias(team="Marseille")))
                self.assertEqual(result.events.team.iloc[0], "Olympique de Marseille")
                self.assertEqual(result.events.team_raw.iloc[0], raw)
                self.assertEqual(result.counts["selected"], 1)

    def test_caen_alias_both_sides(self):
        for raw, trusted in [("Caen", "Stade Malherbe Caen"), ("Stade Malherbe Caen", "Caen")]:
            with self.subTest(raw=raw):
                result = resolve_events(events(event(team=raw)), lookup(alias(team=trusted)),
                                        population(alias(team="Caen")))
                self.assertEqual(result.events.team.iloc[0], "Stade Malherbe Caen")
                self.assertEqual(result.counts["selected"], 1)

    def test_fernando_rosa_roza_requires_explicit_alias(self):
        x = lookup(alias("Fernando Luiz Rosa", 3054))
        e = events(event("Fernando Luiz Roza"))
        with self.assertRaises(UnresolvedIdentityError):
            resolve_events(e, x, population(alias(player_id=3054)))
        x = pd.concat([x, lookup(alias("Fernando Luiz Roza", 3054))], ignore_index=True)
        self.assertEqual(resolve_events(e, x, population(alias(player_id=3054)))
                         .events.player_id.iloc[0], 3054)

    def test_david_ngog_quote_variants_require_evidence(self):
        e = events(event("David N'Gog"), event('David N"Gog', "e2"))
        x = lookup(alias('David N"Gog', 401453))
        with self.assertRaises(UnresolvedIdentityError):
            resolve_events(e, x, population(alias(player_id=401453)))
        x = pd.concat([x, lookup(alias("David N'Gog", 401453))], ignore_index=True)
        self.assertEqual(resolve_events(e, x, population(alias(player_id=401453)))
                         .events.player_id.tolist(), [401453, 401453])

    def test_same_player_multiple_teams_keeps_context(self):
        x = lookup(alias(team="A"), alias(team="B"))
        e = events(event(team="A"), event(team="B", event_id="e2"))
        result = resolve_events(e, x, population(alias(team="A")))
        self.assertEqual(result.events.player_id.tolist(), [1, 1])
        self.assertEqual(result.events.identity_status.tolist(), ["selected", "outside_population"])
        self.assertEqual(result.selected_events().id.tolist(), ["e1"])

    def test_same_player_multiple_seasons_keeps_context(self):
        x = lookup(alias(season="S1"), alias(season="S2"))
        result = resolve_events(events(event(season="S1"), event(season="S2", event_id="e2")),
                                x, population(alias(season="S1")))
        self.assertEqual(result.events.season_name.tolist(), ["S1", "S2"])
        self.assertEqual(result.events.in_population.tolist(), [True, False])

    def test_competition_context_does_not_leak(self):
        with self.assertRaises(UnresolvedIdentityError):
            resolve_events(events(event(competition="Other")), lookup(), population())

    def test_ambiguous_same_name_same_context_fails(self):
        with self.assertRaisesRegex(IdentityError, "ambiguous"):
            resolve_events(events(), lookup(alias(), alias(player_id=2)), population())

    def test_unmatched_selected_context_fails_closed(self):
        with self.assertRaises(UnresolvedIdentityError) as caught:
            resolve_events(events(event("Unverified spelling")), lookup(), population())
        self.assertEqual(caught.exception.result.counts["unresolved"], 1)
        self.assertEqual(caught.exception.result.events.id.tolist(), ["e1"])

    def test_known_outside_player_is_not_unresolved(self):
        result = resolve_events(events(event("Other")), lookup(alias("Other", 2)), population())
        self.assertEqual(result.events.player_id.iloc[0], 2)
        self.assertEqual(result.counts, dict(selected=0, outside_population=1, unresolved=0))

    def test_unknown_player_is_not_assumed_outside_even_in_other_team(self):
        result = resolve_events(events(event(team="Other")), lookup(), population(), strict=False)
        self.assertEqual(result.counts["unresolved"], 1)
        self.assertTrue(pd.isna(result.events.in_population.iloc[0]))
        self.assertTrue(pd.isna(result.events.player_id.iloc[0]))
        with self.assertRaises(UnresolvedIdentityError):
            result.selected_events()

    def test_duplicate_event_ids_fail(self):
        with self.assertRaisesRegex(IdentityError, "duplicate event IDs"):
            resolve_events(events(event(), event()), lookup(), population())

    def test_duplicate_crosswalk_rows_fail_instead_of_multiplying_events(self):
        with self.assertRaisesRegex(IdentityError, "duplicate normalized"):
            resolve_events(events(), lookup(alias(), alias()), population())

    def test_normalization_collision_in_crosswalk_is_rejected(self):
        x = lookup(alias("N''Golo"), alias(" N'Golo "))
        with self.assertRaisesRegex(IdentityError, "duplicate normalized"):
            prepare_crosswalk(x)

    def test_team_alias_collision_is_rejected(self):
        with self.assertRaisesRegex(IdentityError, "duplicate normalized"):
            prepare_crosswalk(lookup(alias(team="Marseille"), alias(team="Olympique de Marseille")))

    def test_ambiguous_normalized_crosswalk_is_rejected(self):
        with self.assertRaisesRegex(IdentityError, "ambiguous"):
            prepare_crosswalk(lookup(alias("N''Golo"), alias("N'Golo", 2)))

    def test_population_duplicate_keys_and_alias_collisions_fail(self):
        for rows in [(alias(), alias()),
                     (alias(team="Caen"), alias(team="Stade Malherbe Caen"))]:
            with self.subTest(rows=rows), self.assertRaisesRegex(IdentityError, "duplicate stable"):
                validate_population(population(*rows))

    def test_inputs_unchanged_on_success_and_failure(self):
        e, x, p = events(), lookup(), population()
        before = [d.copy(deep=True) for d in [e, x, p]]
        resolve_events(e, x, p)
        for actual, saved in zip([e, x, p], before):
            pd.testing.assert_frame_equal(actual, saved)
        e.loc[0, "player"] = "Unknown"
        saved = e.copy(deep=True)
        with self.assertRaises(UnresolvedIdentityError):
            resolve_events(e, x, p)
        pd.testing.assert_frame_equal(e, saved)
        pd.testing.assert_frame_equal(x, before[1])
        pd.testing.assert_frame_equal(p, before[2])

    def test_names_normalize_only_declared_apostrophe_and_whitespace(self):
        raw = pd.Series([" N''Golo\t", None, 'David N"Gog', "DaniloD'Ambrosio"])
        out = normalize_player_names(raw)
        self.assertEqual(out.iloc[0], "N'Golo")
        self.assertTrue(pd.isna(out.iloc[1]))
        self.assertEqual(out.iloc[2:].tolist(), ['David N"Gog', "DaniloD'Ambrosio"])

    def test_no_fuzzy_or_casefolded_identity(self):
        for name in ["player", "Playr"]:
            with self.subTest(name=name), self.assertRaises(UnresolvedIdentityError):
                resolve_events(events(event(name)), lookup(), population())
        self.assertEqual(normalize_team_names(pd.Series([" Marseille ", "marseille"])).tolist(),
                         [" Marseille ", "marseille"])

    def test_metric_missingness_event_order_and_duplicate_indices_preserved(self):
        e = events(event(event_id="b"), event(event_id="a"))
        e.index = pd.Index([9, 9], name="source")
        result = resolve_events(e, lookup(), population())
        self.assertEqual(result.events.id.tolist(), ["b", "a"])
        pd.testing.assert_index_equal(result.events.index, e.index)
        self.assertTrue(result.events.metric.isna().all())

    def test_supplied_event_ids_preserved_without_name_lookup(self):
        e = events(event("Unknown"))
        e["player_id"] = pd.Series([2**53 + 1], dtype="int64")
        result = resolve_events(e, lookup(), population(alias(player_id=2**53 + 1)))
        self.assertEqual(result.events.player_id.iloc[0], 2**53 + 1)
        self.assertEqual(result.counts["selected"], 1)

    def test_conflicting_supplied_player_id_fails(self):
        e = events()
        e["player_id"] = 2
        with self.assertRaisesRegex(IdentityError, "conflicts"):
            resolve_events(e, lookup(), population())

    def test_nullable_supplied_id_falls_back_to_crosswalk(self):
        e = events()
        e["player_id"] = pd.Series([pd.NA], dtype="Int64")
        self.assertEqual(resolve_events(e, lookup(), population()).events.player_id.iloc[0], 1)

    def test_invalid_ids_rejected(self):
        for value in [True, 0, -1, 1.5, np.inf, "1", float(2**53), 2**63, None]:
            with self.subTest(value=value), self.assertRaises(IdentityError):
                prepare_crosswalk(lookup(alias(player_id=value)))

    def test_missing_names_stay_unresolved(self):
        for name in [None, "", "  "]:
            with self.subTest(name=name), self.assertRaises(UnresolvedIdentityError):
                resolve_events(events(event(name)), lookup(), population())

    def test_blank_or_invalid_crosswalk_names_fail(self):
        for name in [None, "", " ", 123]:
            with self.subTest(name=name), self.assertRaises(IdentityError):
                prepare_crosswalk(lookup(alias(name)))

    def test_missing_event_ids_and_context_fail(self):
        for column in ["id", *CONTEXT]:
            for value in [None, "", 123]:
                with self.subTest(column=column, value=value), self.assertRaises(IdentityError):
                    e = events()
                    e[column] = value
                    resolve_events(e, lookup(), population())

    def test_missing_or_duplicate_columns_fail(self):
        e = events()
        for bad in [e.drop(columns="player"), pd.concat([e, e[["id"]]], axis=1)]:
            with self.assertRaises(IdentityError):
                resolve_events(bad, lookup(), population())

    def test_reserved_columns_fail_instead_of_overwriting(self):
        for column in ["team_raw", "identity_status", "in_population", "_identity_name"]:
            with self.subTest(column=column), self.assertRaisesRegex(IdentityError, "collision"):
                e = events()
                e[column] = "do not overwrite"
                resolve_events(e, lookup(), population())

    def test_empty_event_sample_and_population_supported(self):
        result = resolve_events(events().iloc[:0], lookup(), population().iloc[:0])
        self.assertEqual(result.counts, dict(selected=0, outside_population=0, unresolved=0))
        result = resolve_events(events(), lookup(), population().iloc[:0])
        self.assertEqual(result.counts["outside_population"], 1)

    def test_empty_crosswalk_does_not_create_ids(self):
        with self.assertRaises(UnresolvedIdentityError):
            resolve_events(events(), lookup().iloc[:0], population())


if __name__ == "__main__":
    unittest.main()
