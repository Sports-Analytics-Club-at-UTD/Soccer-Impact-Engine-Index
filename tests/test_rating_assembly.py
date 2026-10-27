"""Controlled invented ratings only; no production data, writers or network."""
import ast
import copy
from dataclasses import FrozenInstanceError, replace
import inspect
import math
import unittest
from unittest.mock import patch

from src import rating_assembly as module
from src.identity_evidence import SYNTHETIC, VERIFIED, DELIVERED
from src.rating_assembly import (ATTRIBUTES, POLICY_NOT_FINALIZED, AttributePolicy,
    AttributeSlot, EvidenceSource, PlayerContext, RatingAssemblyError, RatingEvidence,
    RatingScope, SyntheticOVRPolicy, assemble_ratings)


def fixture(scores=(61, 72, 83, 94, 55)):
    context = PlayerContext(1, "Invented Club", "La Liga", "2015/2016")
    scope = RatingScope("La Liga", "2015/2016", (101, 102), True, "invented-cohort-v1")
    evidence = RatingEvidence(SYNTHETIC, (EvidenceSource(SYNTHETIC, "invented fixture ledger"),),
                              "invented-five-ratings-v1", True)
    policies = tuple(AttributePolicy(a, f"invented-{a}", "v1", "rating_1_100", True) for a in ATTRIBUTES)
    slots = [AttributeSlot(a, context, score, "available", (), policy, evidence, scope,
                          "invented-pool-v1") for a, score, policy in zip(ATTRIBUTES, scores, policies)]
    candidate = SyntheticOVRPolicy("invented-equal-five", "v1", policies)
    return [context], slots, candidate


def run(f, *, enabled=True):
    return assemble_ratings(f[0], f[1], candidate_policy=f[2] if enabled else None)


class RatingAssemblyTests(unittest.TestCase):
    def test_five_distinct_slots_and_retained_metadata(self):
        f = fixture(); player = run(f)[0]
        self.assertEqual(tuple(s.attribute_id for s in player.attributes), ATTRIBUTES)
        self.assertEqual(player.attributes, tuple(f[1]))
        self.assertEqual(player.context, f[0][0])

    def test_default_ovr_policy_not_finalized(self):
        player = run(fixture(), enabled=False)[0]
        self.assertIsNone(player.overall.score)
        self.assertEqual(player.overall.status, POLICY_NOT_FINALIZED)
        self.assertEqual(player.overall.reasons, ("policy_not_finalized",))

    def test_explicit_candidate_exact_five_component_arithmetic(self):
        player = run(fixture())[0]
        self.assertEqual(player.overall.score, (61 + 72 + 83 + 94 + 55) / 5)
        self.assertEqual(player.overall.status, "synthetic_candidate")
        self.assertEqual(player.overall.policy.policy_id, "invented-equal-five")

    def test_fractional_scores_unrounded(self):
        scores = (1.1, 2.2, 3.3, 99.9, 100.)
        self.assertEqual(run(fixture(scores))[0].overall.score, math.fsum(scores) / 5)

    def test_each_missing_attribute_withholds_without_zero_fill(self):
        for attr in ATTRIBUTES:
            with self.subTest(attribute=attr):
                f = fixture(); f[1][:] = [s for s in f[1] if s.attribute_id != attr]
                player = run(f)[0]
                missing = next(s for s in player.attributes if s.attribute_id == attr)
                self.assertIsNone(missing.score)
                self.assertEqual(missing.status, "withheld")
                self.assertEqual(missing.reasons, ("missing_attribute",))
                self.assertIsNone(player.overall.score)
                self.assertIn(f"{attr}:unavailable", player.overall.reasons)

    def test_explicit_withheld_preserves_all_reasons_and_provenance(self):
        f = fixture(); f[1][4] = replace(f[1][4], score=None, status="withheld",
            reasons=("definition_not_approved", "no_target_season_360"))
        player = run(f)[0]
        self.assertEqual(player.attributes[4], f[1][4])
        self.assertIsNone(player.overall.score)

    def test_empty_slots_still_yield_exact_five(self):
        f = fixture(); f[1].clear()
        player = run(f)[0]
        self.assertEqual(len(player.attributes), 5)
        self.assertTrue(all(s.score is None for s in player.attributes))
        self.assertIsNone(player.overall.score)

    def test_no_automatic_tiers_even_at_gold_and_silver_boundaries(self):
        for score in (74, 75, 89.9, 90, 100):
            player = run(fixture((score,) * 5))[0]
            self.assertIsNone(player.overall.tier)
            self.assertFalse(any(hasattr(s, "tier") for s in player.attributes))

    def test_incompatible_scope_match_window_cohort_and_full_season(self):
        for change in (dict(match_ids=(101,)), dict(cohort_id="other-cohort"), dict(full_season=False)):
            f = fixture(); f[1][2] = replace(f[1][2], scope=replace(f[1][2].scope, **change))
            player = run(f)[0]
            self.assertIsNone(player.overall.score)
            self.assertIn("incompatible_scopes_or_cohorts", player.overall.reasons)
            self.assertEqual(player.attributes[2], f[1][2])

    def test_incompatible_pool_withholds_ovr(self):
        f = fixture(); f[1][3] = replace(f[1][3], comparison_pool_ref="different-pool")
        self.assertIn("incompatible_comparison_pools", run(f)[0].overall.reasons)

    def test_mismatched_scoring_policy_versions_and_identifiers(self):
        for change in (dict(version="v2"), dict(policy_id="other-policy")):
            f = fixture(); f[1][0] = replace(f[1][0], policy=replace(f[1][0].policy, **change))
            player = run(f)[0]
            self.assertIsNone(player.overall.score)
            self.assertIn("tackles:policy_version_mismatch", player.overall.reasons)

    def test_distinct_component_versions_allowed_only_when_explicitly_pinned(self):
        f = fixture(); policy = replace(f[1][0].policy, version="v2")
        f[1][0] = replace(f[1][0], policy=policy)
        candidate = replace(f[2], component_policies=(policy, *f[2].component_policies[1:]))
        self.assertEqual(assemble_ratings(f[0], f[1], candidate_policy=candidate)[0].overall.score, 73.)

    def test_conflicting_player_id_team_league_and_season_rejected(self):
        for change in (dict(player_id=2), dict(team="Other Club"),
                       dict(competition_name="Serie A"), dict(season_name="2020/2021")):
            f = fixture(); f[1][0] = replace(f[1][0], context=replace(f[0][0], **change))
            with self.subTest(change=change), self.assertRaises(RatingAssemblyError): run(f)

    def test_duplicate_canonical_population_rejected(self):
        f = fixture(); f[0].append(f[0][0])
        with self.assertRaisesRegex(RatingAssemblyError, "duplicate canonical contexts"): run(f)

    def test_duplicate_context_attribute_rejected(self):
        f = fixture(); f[1].append(f[1][0])
        with self.assertRaisesRegex(RatingAssemblyError, "duplicate canonical context/attribute"): run(f)

    def test_noncanonical_team_alias_rejected_without_repair(self):
        context = replace(fixture()[0][0], team="Marseille")
        with self.assertRaisesRegex(RatingAssemblyError, "exact canonical"): assemble_ratings([context], [])

    def test_invalid_canonical_ids_and_labels(self):
        for change in (dict(player_id=True), dict(player_id=1.), dict(player_id=0),
                       dict(player_id=2**63), dict(team=""), dict(season_name=None)):
            with self.subTest(change=change), self.assertRaises(RatingAssemblyError):
                assemble_ratings([replace(fixture()[0][0], **change)], [])

    def test_invalid_scores_nan_infinity_and_no_coercion(self):
        for score in (0, -1, 100.01, float("nan"), float("inf"), -float("inf"),
                      True, "75", 75j, None, 10**400):
            f = fixture(); f[1][0] = replace(f[1][0], score=score)
            with self.subTest(score=score), self.assertRaises(RatingAssemblyError): run(f)

    def test_inclusive_rating_boundaries(self):
        self.assertEqual(run(fixture((1, 100, 1, 100, 1)))[0].overall.score, 40.6)

    def test_withheld_cannot_carry_any_score_including_nan_or_zero(self):
        for score in (0, 75, float("nan")):
            f = fixture(); f[1][0] = replace(f[1][0], status="withheld", score=score, reasons=("missing",))
            with self.subTest(score=score), self.assertRaises(RatingAssemblyError): run(f)

    def test_explicit_missingness_and_available_consistency(self):
        for change in (dict(status="N/A"), dict(status="withheld", score=None),
                       dict(reasons=("withheld",)), dict(policy=None), dict(evidence=None),
                       dict(scope=None), dict(comparison_pool_ref=None), dict(reasons=["missing"])):
            f = fixture(); f[1][0] = replace(f[1][0], **change)
            with self.subTest(change=change), self.assertRaises(RatingAssemblyError): run(f)

    def test_no_raw_counts_rates_percentages_or_dri_substitution_policy(self):
        for unit in ("count", "per90", "percent", "dri_fifa"):
            f = fixture(); f[1][0] = replace(f[1][0], policy=replace(f[1][0].policy, unit=unit))
            with self.subTest(unit=unit), self.assertRaises(RatingAssemblyError): run(f)
        f = fixture(); f[1][0] = replace(f[1][0], attribute_id="dri")
        with self.assertRaises(RatingAssemblyError): run(f)

    def test_wrong_attribute_policy_rejected(self):
        f = fixture(); f[1][0] = replace(f[1][0], policy=f[1][1].policy)
        with self.assertRaises(RatingAssemblyError): run(f)

    def test_no_numeric_real_delivered_or_provisional_ratings(self):
        for kind in (VERIFIED, DELIVERED, "PROVISIONAL", "UNVERIFIED"):
            f = fixture(); evidence = RatingEvidence(kind, (EvidenceSource(kind, "invented claim"),), None, True)
            f[1][0] = replace(f[1][0], evidence=evidence)
            with self.subTest(kind=kind), self.assertRaises(RatingAssemblyError): run(f)

    def test_real_evidence_can_be_retained_only_in_withheld_slots(self):
        f = fixture(); evidence = RatingEvidence(DELIVERED, (EvidenceSource(DELIVERED, "invented delivered ledger"),), None, False)
        f[1][0] = replace(f[1][0], score=None, status="withheld", reasons=("not_production_verified",), evidence=evidence)
        self.assertEqual(run(f)[0].attributes[0].evidence, evidence)
        self.assertIsNone(run(f)[0].overall.score)

    def test_no_synthetic_lineage_promotion_to_verified_or_delivered(self):
        for kind in (VERIFIED, DELIVERED):
            f = fixture(); f[1][0] = replace(f[1][0], score=None, status="withheld", reasons=("blocked",),
                evidence=replace(f[1][0].evidence, kind=kind, fixture_id=None))
            with self.assertRaisesRegex(RatingAssemblyError, "lineage mismatch"): run(f)

    def test_mixed_lineage_not_accepted_as_synthetic(self):
        f = fixture(); f[1][0] = replace(f[1][0], evidence=replace(f[1][0].evidence,
            sources=(EvidenceSource(SYNTHETIC, "invented"), EvidenceSource(VERIFIED, "invented claim"))))
        with self.assertRaises(RatingAssemblyError): run(f)

    def test_incomplete_or_missing_fixture_evidence_rejected(self):
        for change in (dict(complete=False), dict(complete=1), dict(fixture_id=None), dict(sources=())):
            f = fixture(); f[1][0] = replace(f[1][0], evidence=replace(f[1][0].evidence, **change))
            with self.subTest(change=change), self.assertRaises(RatingAssemblyError): run(f)

    def test_different_synthetic_fixture_withholds_ovr(self):
        f = fixture(); f[1][0] = replace(f[1][0], evidence=replace(f[1][0].evidence, fixture_id="other-fixture"))
        self.assertIn("incompatible_fixture_provenance", run(f)[0].overall.reasons)

    def test_target_scope_cannot_borrow_later_season_frames(self):
        f = fixture(); f[1][4] = replace(f[1][4], scope=replace(f[1][4].scope, season_name="2020/2021"))
        with self.assertRaisesRegex(RatingAssemblyError, "scope competition/season"): run(f)

    def test_scope_validation(self):
        for change in (dict(match_ids=()), dict(match_ids=(102, 101)), dict(match_ids=(101, 101)),
                       dict(match_ids=(True,)), dict(match_ids=(101.,)), dict(full_season=1), dict(cohort_id="")):
            f = fixture(); f[1][0] = replace(f[1][0], scope=replace(f[1][0].scope, **change))
            with self.subTest(change=change), self.assertRaises(RatingAssemblyError): run(f)

    def test_candidate_policy_must_be_explicit_complete_and_synthetic(self):
        f = fixture()
        for policy in (True, {}, replace(f[2], synthetic_only=False), replace(f[2], formula="drop_missing"),
                       replace(f[2], component_policies=f[2].component_policies[:4]),
                       replace(f[2], component_policies=(f[2].component_policies[0],) * 5)):
            with self.subTest(policy=policy), self.assertRaises(RatingAssemblyError):
                assemble_ratings(f[0], f[1], candidate_policy=policy)

    def test_transfer_teams_are_separate_contexts(self):
        f = fixture(); other = replace(f[0][0], team="Invented Transfer Club")
        f[0].append(other); f[1].extend(replace(s, context=other, score=20) for s in tuple(f[1]))
        players = run(f)
        self.assertEqual(len(players), 2)
        self.assertEqual([p.overall.score for p in players], [73., 20.])

    def test_different_player_seasons_are_separate(self):
        f = fixture(); other = replace(f[0][0], season_name="2020/2021")
        f[0].append(other)
        players = run(f)
        self.assertEqual(len(players), 2)
        self.assertIsNone(players[1].overall.score)

    def test_row_order_invariance(self):
        f = fixture(); other = replace(f[0][0], player_id=2)
        f[0].append(other); f[1].extend(replace(s, context=other) for s in tuple(f[1]))
        expected = run(f); f[0].reverse(); f[1].reverse()
        self.assertEqual(run(f), expected)

    def test_input_immutability_and_immutable_output(self):
        f = fixture(); before = copy.deepcopy(f); player = run(f)[0]
        self.assertEqual(f, before)
        with self.assertRaises(FrozenInstanceError): player.publication_authorized = True
        with self.assertRaises(FrozenInstanceError): player.attributes[0].score = 99

    def test_empty_population_and_unknown_attribute_context(self):
        self.assertEqual(assemble_ratings([], []), ())
        with self.assertRaises(RatingAssemblyError): assemble_ratings([], fixture()[1])

    def test_no_production_publication_or_frontend_contract(self):
        player = run(fixture())[0]
        self.assertFalse(player.production_verified)
        self.assertFalse(player.publication_authorized)
        self.assertIn("SYNTHETIC-ONLY", player.notice)
        self.assertFalse(hasattr(player, "schema_version"))

    def test_no_io_or_network_during_assembly(self):
        f = fixture()
        with patch("builtins.open", side_effect=AssertionError("file access forbidden")), \
             patch("socket.socket", side_effect=AssertionError("network forbidden")), \
             patch("pandas.DataFrame.to_parquet", side_effect=AssertionError("writer forbidden")), \
             patch("pandas.DataFrame.to_json", side_effect=AssertionError("writer forbidden")):
            self.assertEqual(run(f)[0].overall.score, 73.)

    def test_module_imports_no_writers_network_or_existing_scoring_engines(self):
        tree = ast.parse(inspect.getsource(module))
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        self.assertEqual(set(imports), {"dataclasses", "math", "numbers", "pandas", "src.identity", "src.identity_evidence"})
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        forbidden = {"open", "write", "write_text", "write_bytes", "to_parquet", "to_json", "to_csv", "urlopen", "request"}
        self.assertFalse(any((isinstance(c.func, ast.Name) and c.func.id in forbidden)
            or (isinstance(c.func, ast.Attribute) and c.func.attr in forbidden) for c in calls))


if __name__ == "__main__":
    unittest.main()
