"""Synthetic source fixtures exercise attestations, never establish real source truth."""
import copy
import unittest

import numpy as np
import pandas as pd

from src.identity import (IdentityError, NAME_KEYS, PLAYER_KEYS, UnresolvedIdentityError,
                          prepare_crosswalk, resolve_events)
from src.identity_evidence import (
    DELIVERED, SYNTHETIC, VERIFIED, IdentityEvidenceError, LineupEvidence,
    audit_identity_coverage, build_identity_crosswalk, validate_lineup_evidence, validate_match_contexts,
)


def lineup(player_id=1, name="Player", match_id=10, **changes):
    return dict(match_id=match_id, team="Team", player_id=player_id, player_name=name,
                competition_name="League", season_name="Season") | changes


def event(name="Player", event_id="e1", **changes):
    return dict(id=event_id, match_id=10, player=name, team="Team", competition_name="League",
                season_name="Season", type="Pass") | changes


def validated(rows=None, kind=VERIFIED, source="synthetic fixture emulating verified lineups", **kwargs):
    # VERIFIED here emulates an external attestation for a positive-path unit test.
    # It is not a claim that this fixture verifies any real StatsBomb actor.
    table = pd.DataFrame(rows if rows is not None else [lineup()])
    return validate_lineup_evidence(table, source=source, evidence_kind=kind, **kwargs)


def built(rows=None, **kwargs):
    return build_identity_crosswalk(validated(rows, **kwargs))


def population(rows=None):
    return pd.DataFrame(rows if rows is not None else [lineup()])[PLAYER_KEYS]


def audit(rows=None, evidence=None, selected=None, **kwargs):
    return audit_identity_coverage(pd.DataFrame(rows if rows is not None else [event()]),
                                   evidence if evidence is not None else built(),
                                   selected if selected is not None else population(),
                                   population_scope="explicit synthetic diagnostic population", **kwargs)


class IdentityEvidenceTests(unittest.TestCase):
    def test_valid_direct_lineup_crosswalk(self):
        result = built()
        self.assertEqual(result.crosswalk.player_id.tolist(), [1])
        self.assertEqual(result.summary["trusted_crosswalk_rows"], 1)

    def test_int64_id_precision(self):
        value = 2**63 - 1
        result = built([lineup(player_id=value)])
        self.assertEqual(result.crosswalk.player_id.tolist(), [value])
        self.assertEqual(str(result.crosswalk.player_id.dtype), "Int64")

    def test_full_canonical_context(self):
        row = built().crosswalk.iloc[0]
        self.assertEqual(row[NAME_KEYS].tolist(), ["Player", "Team", "League", "Season"])

    def test_verified_match_context_association(self):
        table = pd.DataFrame([lineup()]).drop(columns=["competition_name", "season_name"])
        mapping = validate_match_contexts(pd.DataFrame([lineup()]), source="synthetic match manifest", evidence_kind=VERIFIED)
        evidence = validate_lineup_evidence(table, source="synthetic lineup fixture", evidence_kind=VERIFIED, match_contexts=mapping)
        self.assertEqual(build_identity_crosswalk(evidence).crosswalk.season_name.tolist(), ["Season"])
        self.assertEqual(evidence.rows.match_context_source.tolist(), ["synthetic match manifest"])

    def test_match_repetition_is_explicitly_accounted(self):
        result = validate_match_contexts(pd.DataFrame([lineup(), lineup()]), source="fixture", evidence_kind=VERIFIED)
        self.assertEqual(result.summary, {"input_rows": 2, "matches": 1, "consistent_repeat_rows": 1})

    def test_repeated_lineup_rows_accounted_without_multiplication(self):
        validated_rows = validated([lineup(), lineup(), lineup(match_id=11)])
        result = build_identity_crosswalk(validated_rows)
        self.assertEqual(validated_rows.summary["consistent_repeat_rows"], 1)
        self.assertEqual(result.summary["consistent_repeat_rows"], 1)
        self.assertEqual(result.summary["season_mapping_repeat_rows"], 1)
        self.assertEqual(len(result.crosswalk), 1)
        self.assertEqual(len(result.evidence), 3)
        self.assertEqual(audit(evidence=result).summary["source_evidence"]["consistent_repeat_rows"], 1)

    def test_multiple_sources_preserve_provenance(self):
        result = build_identity_crosswalk([validated(source="fixture A"), validated(source="fixture B")])
        self.assertEqual(len(result.crosswalk), 1)
        self.assertEqual(set(result.evidence.source), {"fixture A", "fixture B"})

    def test_conflicting_match_mapping_rejected(self):
        with self.assertRaisesRegex(IdentityEvidenceError, "conflicting match") as caught:
            validate_match_contexts(pd.DataFrame([lineup(), lineup(season_name="Other")]), source="fixture", evidence_kind=VERIFIED)
        self.assertEqual(len(caught.exception.details), 2)

    def test_missing_match_association_rejected(self):
        table = pd.DataFrame([lineup()]).drop(columns=["competition_name", "season_name"])
        with self.assertRaisesRegex(IdentityEvidenceError, "association"):
            validate_lineup_evidence(table, source="fixture", evidence_kind=VERIFIED)

    def test_missing_mapped_match_rejected(self):
        mapping = validate_match_contexts(pd.DataFrame([lineup(match_id=11)]), source="fixture", evidence_kind=VERIFIED)
        with self.assertRaisesRegex(IdentityEvidenceError, "missing from context"):
            validated(match_contexts=mapping)

    def test_direct_context_disagrees_with_mapping(self):
        mapping = validate_match_contexts(pd.DataFrame([lineup(season_name="Other")]), source="fixture", evidence_kind=VERIFIED)
        with self.assertRaisesRegex(IdentityEvidenceError, "disagree"):
            validated(match_contexts=mapping)

    def test_conflicting_ids_quarantine_entire_name_key(self):
        result = built([lineup(), lineup(2, match_id=11)])
        self.assertTrue(result.crosswalk.empty)
        self.assertEqual(result.summary["conflicting_keys"], 1)
        self.assertEqual(set(result.conflicts.match_id), {10, 11})
        self.assertEqual(set(result.conflicts.player_id), {1, 2})
        self.assertEqual(set(result.conflicts.report_label), {"CONFLICTING"})

    def test_same_match_homonym_not_chosen(self):
        result = built([lineup(), lineup(2)])
        self.assertTrue(result.crosswalk.empty)
        with self.assertRaisesRegex(IdentityEvidenceError, "conflicting"):
            result.require_unambiguous()

    def test_conflict_does_not_remove_unrelated_verified_key(self):
        result = built([lineup(), lineup(2), lineup(3, "Other")])
        self.assertEqual(result.crosswalk.player_id.tolist(), [3])

    def test_normalized_spelling_duplicates_with_consistent_id_are_accounted(self):
        result = built([lineup(name=" O''Name "), lineup(name="O'Name", match_id=11)])
        self.assertEqual(result.crosswalk.player_name_raw.tolist(), ["O'Name"])
        self.assertEqual(result.summary["season_mapping_repeat_rows"], 1)
        self.assertEqual(set(result.evidence.original_player_name), {" O''Name ", "O'Name"})

    def test_normalized_spelling_conflict_is_quarantined(self):
        result = built([lineup(name=" O''Name "), lineup(2, "O'Name", match_id=11)])
        self.assertTrue(result.crosswalk.empty)
        self.assertEqual(result.summary["conflicting_keys"], 1)

    def test_multiple_verified_spellings_same_id(self):
        result = built([lineup(name="Rosa"), lineup(name="Roza", match_id=11)])
        self.assertEqual(len(result.crosswalk), 2)
        self.assertEqual(result.crosswalk.player_id.tolist(), [1, 1])

    def test_rosa_roza_not_global_alias(self):
        result = audit([event("Roza")], built([lineup(name="Rosa")]))
        self.assertEqual(result.summary["unresolved"], 1)

    def test_apostrophe_quote_distinct_without_verified_alias(self):
        result = audit([event('David N"Gog')], built([lineup(name="David N'Gog")]))
        self.assertEqual(result.summary["unresolved"], 1)

    def test_both_verified_quote_spellings_compatible_with_m2a(self):
        result = built([lineup(name="David N'Gog"), lineup(name='David N"Gog')])
        resolved = resolve_events(pd.DataFrame([event("David N'Gog"), event('David N"Gog', "e2")]), result.crosswalk, population())
        self.assertEqual(resolved.counts["selected"], 2)

    def test_existing_club_aliases_only(self):
        for alias, canonical in [("Marseille", "Olympique de Marseille"), ("Caen", "Stade Malherbe Caen")]:
            with self.subTest(alias=alias):
                result = built([lineup(team=alias)])
                self.assertEqual(result.crosswalk.team.tolist(), [canonical])
                self.assertEqual(audit([event(team=canonical)], result, population([lineup(team=alias)])).summary["selected"], 1)

    def test_transfers_and_seasons_distinct(self):
        result = built([lineup(), lineup(team="Other", match_id=11), lineup(season_name="Other", match_id=12)])
        self.assertEqual(len(result.crosswalk), 3)

    def test_same_name_in_different_teams_different_people(self):
        result = built([lineup(), lineup(2, team="Other")])
        self.assertEqual(set(result.crosswalk.player_id), {1, 2})
        self.assertTrue(result.conflicts.empty)

    def test_missing_or_invalid_player_ids_rejected(self):
        for value in [None, True, "1", 1.5, 0, -1, np.inf, float(2**53), 2**63]:
            with self.subTest(value=value), self.assertRaises(IdentityError):
                built([lineup(player_id=value)])

    def test_missing_or_invalid_names_rejected(self):
        for value in [None, "", "  ", 12]:
            with self.subTest(value=value), self.assertRaises(IdentityError):
                built([lineup(name=value)])

    def test_missing_team_and_context_rejected(self):
        for field in ["team", "competition_name", "season_name"]:
            with self.subTest(field=field), self.assertRaises(IdentityError):
                built([lineup(**{field: None})])

    def test_invalid_match_ids_rejected(self):
        for value in [None, True, "10", 0, -1, 1.25, np.inf]:
            with self.subTest(value=value), self.assertRaises(IdentityError):
                built([lineup(match_id=value)])

    def test_partial_direct_context_rejected(self):
        table = pd.DataFrame([lineup()]).drop(columns="season_name")
        with self.assertRaisesRegex(IdentityEvidenceError, "partial"):
            validate_lineup_evidence(table, source="fixture", evidence_kind=VERIFIED)

    def test_duplicate_event_ids_rejected(self):
        with self.assertRaisesRegex(IdentityEvidenceError, "duplicate event"):
            audit([event(), event()])

    def test_unknown_name_membership_unknown_not_outside(self):
        result = audit([event("Unknown")])
        self.assertEqual(result.summary["outside_population"], 0)
        self.assertEqual(result.summary["unresolved"], 1)
        self.assertTrue(pd.isna(result.identity.events.in_population.iloc[0]))

    def test_selected_and_verified_outside_partition(self):
        result = audit([event(), event("Other", "e2"), event("Unknown", "e3")], built([lineup(), lineup(2, "Other")]))
        self.assertEqual(result.identity.counts, {"selected": 1, "outside_population": 1, "unresolved": 1})
        self.assertEqual(result.summary["events_matched_crosswalk"], 2)
        self.assertEqual(result.summary["total_events"], 3)

    def test_strict_unresolved_still_rejected_by_m2a(self):
        result = audit([event("Unknown")])
        with self.assertRaises(UnresolvedIdentityError):
            result.identity.require_resolved()

    def test_event_count_conservation_no_multiplication(self):
        evidence = built([lineup(), lineup(match_id=11), lineup(match_id=12)])
        result = audit([event(), event(event_id="e2")], evidence)
        self.assertEqual(len(result.identity.events), 2)
        self.assertEqual(sum(result.identity.counts.values()), 2)
        self.assertEqual(result.summary["distinct_event_ids"], 2)

    def test_event_conflict_is_fatal_and_all_rows_retained_in_error(self):
        with self.assertRaisesRegex(IdentityEvidenceError, "conflicts with trusted") as caught:
            audit([event(player_id=2), event(event_id="e2", player_id=1)])
        self.assertEqual(len(caught.exception.details), 2)

    def test_source_conflicts_remain_visible_unresolved(self):
        result = audit(evidence=built([lineup(), lineup(2)]))
        self.assertEqual(result.summary["events_on_conflicting_source_keys"], 1)
        self.assertEqual(result.summary["unresolved"], 1)
        self.assertEqual(len(result.conflicting_events), 1)

    def test_supplied_stable_id_preserved_on_source_homonym(self):
        result = audit([event(player_id=1)], built([lineup(), lineup(2)]))
        self.assertEqual(result.summary["selected"], 1)
        self.assertEqual(result.summary["events_on_conflicting_source_keys"], 1)

    def test_provenance_records_raw_original_and_match(self):
        row = built([lineup(name=" O''Name ")]).evidence.iloc[0]
        self.assertEqual(row.original_player_name, " O''Name ")
        self.assertEqual(row.player_name_raw, "O'Name")
        self.assertEqual(row.match_id, 10)
        self.assertIn("synthetic", row.source)

    def test_delivered_evidence_not_auto_trusted(self):
        evidence = built(kind=DELIVERED)
        self.assertTrue(evidence.crosswalk.empty)
        result = audit(evidence=evidence)
        self.assertEqual(result.summary["unresolved"], 1)
        self.assertEqual(evidence.summary["evidence_labels"], {DELIVERED: 1})
        self.assertEqual(len(result.coverage["event_matches_without_evidence"]), 1)

    def test_synthetic_evidence_stays_synthetic(self):
        evidence = built(kind=SYNTHETIC)
        self.assertTrue(evidence.crosswalk.empty)
        self.assertEqual(evidence.evidence.report_label.tolist(), [SYNTHETIC])

    def test_unverified_match_mapping_never_upgrades_lineups(self):
        mapping = validate_match_contexts(pd.DataFrame([lineup()]), source="unverified metadata", evidence_kind=DELIVERED)
        evidence = build_identity_crosswalk(validated(match_contexts=mapping))
        self.assertTrue(evidence.crosswalk.empty)
        self.assertEqual(evidence.evidence.report_label.tolist(), [DELIVERED])

    def test_weak_conflict_does_not_silently_win(self):
        evidence = build_identity_crosswalk([validated(), validated([lineup(2)], kind=DELIVERED)])
        self.assertTrue(evidence.crosswalk.empty)
        self.assertEqual(evidence.summary["conflicting_keys"], 1)

    def test_mutated_lookup_not_trusted_over_provenance(self):
        evidence = built()
        evidence.crosswalk["player_id"] = 99
        self.assertEqual(audit(evidence=evidence).identity.events.player_id.tolist(), [1])

    def test_missing_player_name_with_supplied_id(self):
        result = audit([event(None, player_id=1)])
        self.assertEqual(result.summary["events_missing_player_names"], 1)
        self.assertEqual(result.summary["events_with_supplied_ids"], 1)
        self.assertEqual(result.summary["selected"], 1)
        self.assertEqual(result.summary["events_matched_crosswalk"], 0)

    def test_breakdown_by_team_season_competition_and_type(self):
        result = audit([event(), event("Unknown", "e2", type="Dribble")])
        self.assertEqual(set(result.breakdown.type), {"Pass", "Dribble"})
        self.assertEqual(result.breakdown[["selected", "outside_population", "unresolved"]].sum().sum(), 2)

    def test_expected_match_and_team_gaps_reported(self):
        manifest = validate_match_contexts(pd.DataFrame([lineup(), lineup(match_id=11)]), source="synthetic expected fixtures", evidence_kind=VERIFIED)
        result = audit([event(), event("Unknown", "e2", team="Other")], expected_matches=manifest)
        self.assertEqual(result.coverage["expected_matches_missing_events"].match_id.tolist(), [11])
        self.assertEqual(result.coverage["expected_matches_missing_evidence"].match_id.tolist(), [11])
        self.assertEqual(result.coverage["event_match_teams_without_evidence"].team.tolist(), ["Other"])
        self.assertEqual(result.coverage["match_coverage_status"], "UNVERIFIED")

    def test_ambiguous_event_match_context_rejected(self):
        with self.assertRaisesRegex(IdentityEvidenceError, "conflicting match"):
            audit([event(), event(event_id="e2", season_name="Other")])

    def test_unverified_expected_manifest_rejected(self):
        manifest = validate_match_contexts(pd.DataFrame([lineup()]), source="unverified fixture", evidence_kind=DELIVERED)
        with self.assertRaisesRegex(IdentityEvidenceError, "verified manifest"):
            audit(expected_matches=manifest)

    def test_input_immutability(self):
        source = pd.DataFrame([lineup(), lineup()])
        original = source.copy(deep=True)
        e = pd.DataFrame([event()]); e_original = e.copy(deep=True)
        p = population(); p_original = p.copy(deep=True)
        evidence = build_identity_crosswalk(validate_lineup_evidence(source, source="fixture", evidence_kind=VERIFIED))
        evidence_before = copy.deepcopy(evidence)
        audit_identity_coverage(e, evidence, p, population_scope="explicit fixture")
        pd.testing.assert_frame_equal(source, original)
        pd.testing.assert_frame_equal(e, e_original)
        pd.testing.assert_frame_equal(p, p_original)
        pd.testing.assert_frame_equal(evidence.evidence, evidence_before.evidence)
        pd.testing.assert_frame_equal(evidence.crosswalk, evidence_before.crosswalk)

    def test_deterministic_evidence_and_crosswalk(self):
        rows = [lineup(2, "Z"), lineup(name="A", match_id=11), lineup(name="Other spelling", match_id=12)]
        a, b = built(rows), built(rows[::-1])
        pd.testing.assert_frame_equal(a.crosswalk, b.crosswalk)
        pd.testing.assert_frame_equal(a.evidence, b.evidence)
        self.assertEqual(a.summary, b.summary)

    def test_empty_source_and_event_input(self):
        evidence = build_identity_crosswalk([])
        self.assertTrue(evidence.crosswalk.empty)
        result = audit_identity_coverage(pd.DataFrame([event()]).iloc[:0], evidence, population(),
                                         population_scope="empty synthetic event batch")
        self.assertEqual(result.summary["total_events"], 0)

    def test_missing_source_never_establishes_outside_population(self):
        result = audit(evidence=build_identity_crosswalk([]))
        self.assertEqual(result.summary["source_gap_label"], "SOURCE_UNAVAILABLE")
        self.assertEqual(result.summary["unresolved"], 1)
        self.assertEqual(result.summary["outside_population"], 0)

    def test_unverified_association_cannot_supply_missing_lineup_context(self):
        source = pd.DataFrame([lineup()]).drop(columns=["competition_name", "season_name"])
        mapping = validate_match_contexts(pd.DataFrame([lineup()]), source="unverified metadata", evidence_kind=DELIVERED)
        with self.assertRaisesRegex(IdentityEvidenceError, "separately verified"):
            validate_lineup_evidence(source, source="fixture", evidence_kind=VERIFIED, match_contexts=mapping)

    def test_empty_declared_lineup_source(self):
        table = pd.DataFrame(columns=["match_id", "team", "player_id", "player_name"])
        result = build_identity_crosswalk(validate_lineup_evidence(table, source="empty fixture", evidence_kind=SYNTHETIC))
        self.assertTrue(result.crosswalk.empty)

    def test_m2a_crosswalk_shape_and_uniqueness(self):
        result = built([lineup(), lineup(name="Other spelling", match_id=11)])
        self.assertFalse(result.crosswalk.duplicated(NAME_KEYS).any())
        pd.testing.assert_frame_equal(prepare_crosswalk(result.crosswalk), result.crosswalk)

    def test_raw_name_column_supported_explicitly(self):
        source = pd.DataFrame([lineup()]).rename(columns={"player_name": "player_name_raw"})
        result = build_identity_crosswalk(validate_lineup_evidence(source, source="fixture", evidence_kind=VERIFIED,
                                                                 name_column="player_name_raw"))
        self.assertEqual(result.crosswalk.player_name_raw.tolist(), ["Player"])

    def test_population_scope_required(self):
        with self.assertRaises(IdentityEvidenceError):
            audit_identity_coverage(pd.DataFrame([event()]), built(), population(), population_scope="")

    def test_invalid_evidence_kind_or_duplicate_columns_rejected(self):
        with self.assertRaises(IdentityEvidenceError):
            validated(kind="looks verified")
        table = pd.DataFrame([lineup()])
        table = pd.concat([table, table[["player_id"]]], axis=1)
        with self.assertRaises(IdentityEvidenceError):
            validate_lineup_evidence(table, source="fixture", evidence_kind=VERIFIED)

    def test_conflicting_match_across_separate_sources_rejected(self):
        with self.assertRaisesRegex(IdentityEvidenceError, "conflicting match"):
            build_identity_crosswalk([validated(), validated([lineup(season_name="Other")], source="fixture B")])

    def test_event_source_association_disagreement_rejected(self):
        with self.assertRaisesRegex(IdentityEvidenceError, "conflicting match"):
            audit([event(season_name="Other")])

    def test_empty_population_known_ids_are_outside_not_unresolved(self):
        result = audit(selected=population().iloc[:0])
        self.assertEqual(result.summary["outside_population"], 1)
        self.assertEqual(result.summary["unresolved"], 0)

    def test_missing_name_without_id_retained_unknown(self):
        result = audit([event(name=None)])
        self.assertEqual(result.summary["events_missing_player_names"], 1)
        self.assertEqual(result.summary["unresolved"], 1)

    def test_original_event_index_order_and_values_preserved(self):
        source = pd.DataFrame([event(), event("Unknown", "e2")], index=[9, 9]).assign(metric=np.nan)
        result = audit_identity_coverage(source, built(), population(), population_scope="explicit fixture")
        self.assertEqual(result.identity.events.index.tolist(), [9, 9])
        self.assertEqual(result.identity.events.id.tolist(), ["e1", "e2"])
        self.assertTrue(result.identity.events.metric.isna().all())

    def test_no_position_minutes_or_exposure_policy(self):
        evidence = built([lineup(position=None, minutes=0, in_scope=False)])
        self.assertEqual(len(evidence.crosswalk), 1)
        self.assertNotIn("minutes", evidence.crosswalk)
        self.assertNotIn("position", evidence.crosswalk)

    def test_audit_without_match_ids_cannot_claim_match_coverage(self):
        source = pd.DataFrame([event()]).drop(columns="match_id")
        result = audit_identity_coverage(source, built(), population(), population_scope="explicit fixture")
        self.assertEqual(result.summary["selected"], 1)
        self.assertEqual(result.coverage["match_coverage_status"], "UNVERIFIED")
        self.assertNotIn("observed_matches", result.coverage)


if __name__ == "__main__":
    unittest.main()
