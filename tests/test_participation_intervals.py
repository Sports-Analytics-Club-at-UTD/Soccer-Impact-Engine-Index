"""Synthetic interval structure only; no delivered players or source promotion."""
import ast
import copy
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from fractions import Fraction
import inspect
import itertools
import unittest

from src import participation_intervals as module
from src.participation_intervals import (
    Clock, ClockPolicy, Context, CONFLICT, INCOMPLETE, ParticipationError,
    PeriodBoundary, Stint, VALID, validate_participation,
)

CTX = Context(101, 202, "invented-team-key")
REFS = ("invented-fixture:boundary",)
PROVENANCE = ("invented-synthetic-source:v1",)


def clock(seconds, period=1, refs=REFS):
    return Clock(period, seconds, refs)


def policy(periods=(1,), convention="period_offset", **changes):
    return replace(ClockPolicy(101, convention, periods, REFS, PROVENANCE), **changes)


def boundary(period=1, start=0, end=2880, **changes):
    return replace(PeriodBoundary(101, period, start, end, REFS, PROVENANCE), **changes)


def stint(oid="a", start=0, end=2880, **changes):
    start = start if isinstance(start, Clock) or start is None else clock(start)
    end = end if isinstance(end, Clock) or end is None else clock(end)
    return replace(Stint(oid, CTX, "invented-CB", start, end,
        "starter", "match_end", REFS, PROVENANCE), **changes)


def validate(rows=None, **changes):
    return validate_participation(CTX, [stint()] if rows is None else rows,
        **(dict(clock_policy=policy()) | changes))


def codes(result):
    return {issue.code for issue in result.issues}


def findings(result):
    return {finding.code for finding in result.findings}


class ValidIntervalTests(unittest.TestCase):
    def test_ordinary_starter(self):
        r = validate()
        self.assertEqual(r.status, VALID)
        self.assertEqual(r.elapsed_seconds, 2880)
        self.assertEqual(r.position_allocation[0].elapsed_seconds, 2880)

    def test_ordinary_substitute(self):
        r = validate([stint(start=1800, entry_kind="substitution")])
        self.assertEqual(r.elapsed_seconds, 1080)

    def test_substitution_after_minute_90_is_not_clipped(self):
        r = validate([stint(start=5460, end=5760, entry_kind="substitution")])
        self.assertEqual(r.status, VALID)
        self.assertEqual(r.elapsed_seconds, 300)
        self.assertIn("recorded_entry_after_minute_90", findings(r))

    def test_starter_through_recorded_stoppage(self):
        r = validate([stint(end=5760)])
        self.assertEqual(r.elapsed_seconds, 5760)

    def test_explicit_cross_period_offsets_preserve_both_added_times(self):
        r = validate([stint(end=clock(5580, 2))],
            clock_policy=policy((1, 2)), period_boundaries=[boundary(), boundary(2, 2700, 5580)])
        self.assertEqual(r.status, VALID)
        self.assertEqual(r.elapsed_seconds, 5760)  # 48 + 48, not clock-label 93 or assumed 90
        self.assertEqual(r.intervals[0].boundary_periods, (1, 2))

    def test_period_local_cross_period(self):
        r = validate([stint(end=clock(2880, 2))],
            clock_policy=policy((1, 2), "period_local"), period_boundaries=[boundary(), boundary(2, 0, 2880)])
        self.assertEqual(r.elapsed_seconds, 5760)

    def test_three_explicit_periods_without_hardcoded_lengths(self):
        rows = [stint(start=clock(0, 10), end=clock(300, 30), exit_kind="substitution")]
        r = validate(rows, clock_policy=policy((10, 20, 30), "period_local"),
            period_boundaries=[boundary(10, 0, 1000), boundary(20, 0, 1200), boundary(30, 0, 400)])
        self.assertEqual(r.elapsed_seconds, 2500)

    def test_temporary_exit_and_reentry_exclude_gap(self):
        rows = [stint(end=1200, exit_kind="temporary_exit"),
                stint("b", 1260, 2880, entry_kind="return")]
        r = validate(rows)
        self.assertEqual(r.status, VALID)
        self.assertEqual(r.elapsed_seconds, 2820)
        self.assertEqual(r.gaps[0].elapsed_seconds, 60)
        self.assertTrue(r.gaps[0].supported_temporary_absence)
        self.assertIn("multiple_active_stints", findings(r))
        self.assertIn("temporary_exit_and_reentry", findings(r))

    def test_dismissal_is_terminal_supported_exit(self):
        self.assertEqual(validate([stint(end=2000, exit_kind="dismissal")]).elapsed_seconds, 2000)

    def test_position_change_does_not_double_count(self):
        rows = [stint(end=1200, exit_kind="position_change"),
                stint("b", 1200, 2880, entry_kind="position_change", position="invented-DM")]
        r = validate(rows)
        self.assertEqual(r.elapsed_seconds, 2880)
        self.assertEqual(sum(p.elapsed_seconds for p in r.position_allocation), r.elapsed_seconds)
        self.assertEqual({p.position: p.elapsed_seconds for p in r.position_allocation},
                         {"invented-CB": 1200, "invented-DM": 1680})
        self.assertIn("position_change", findings(r))

    def test_position_change_across_explicit_period_boundary(self):
        rows = [stint(end=2880, exit_kind="position_change"),
                stint("b", start=clock(2700, 2), end=clock(5580, 2), entry_kind="position_change")]
        r = validate(rows, clock_policy=policy((1, 2)), period_boundaries=[boundary(), boundary(2, 2700, 5580)])
        self.assertEqual(r.elapsed_seconds, 5760)
        self.assertEqual(r.gaps[0].elapsed_seconds, 0)

    def test_exact_decimal_precision_no_early_rounding(self):
        r = validate([stint(start=Decimal("1.000000000000000000000000000001"),
                            end=Decimal("1.000000000000000000000000000003"), entry_kind="substitution")])
        self.assertEqual(r.elapsed_seconds, Fraction(2, 10**30))

    def test_fraction_input_is_exact(self):
        r = validate([stint(start=Fraction(1, 3), end=Fraction(2, 3), entry_kind="substitution")])
        self.assertEqual(r.elapsed_seconds, Fraction(1, 3))

    def test_equal_start_end_explicit_zero_is_not_missing(self):
        r = validate([stint(start=300, end=300, entry_kind="substitution")])
        self.assertEqual(r.status, VALID)
        self.assertEqual(r.elapsed_seconds, 0)
        self.assertIn("same_clock_entry_exit", findings(r))

    def test_temporary_absence_across_periods_does_not_require_gap_duration(self):
        rows = [stint(end=1000, exit_kind="temporary_exit"),
                stint("b", clock(3000, 2), clock(4000, 2), entry_kind="return", exit_kind="substitution")]
        r = validate(rows, clock_policy=policy((1, 2)))
        self.assertEqual(r.elapsed_seconds, 2000)
        self.assertIsNone(r.gaps[0].elapsed_seconds)
        self.assertIn("gap_between_active_intervals", findings(r))


class IncompleteEvidenceTests(unittest.TestCase):
    def assertIncomplete(self, result, code):
        self.assertEqual(result.status, INCOMPLETE)
        self.assertIsNone(result.elapsed_seconds)
        self.assertIsNone(result.position_allocation)
        self.assertIn(code, codes(result))

    def test_unknown_period_semantics(self):
        for p in (None, policy(convention="unknown"), policy(convention=None), policy(periods=())):
            with self.subTest(policy=p):
                self.assertIncomplete(validate(clock_policy=p), "unknown_period_semantics")

    def test_missing_policy_documentation(self):
        for field, code in (("evidence_refs", "missing_clock_policy_evidence"), ("provenance_refs", "missing_clock_policy_provenance")):
            self.assertIncomplete(validate(clock_policy=policy(**{field: ()})), code)

    def test_cross_period_missing_boundaries(self):
        r = validate([replace(stint(), end=clock(5580, 2))], clock_policy=policy((1, 2)))
        self.assertIncomplete(r, "cross_period_boundaries_unavailable")
        self.assertIsNone(r.intervals[0].elapsed_seconds)

    def test_cross_period_missing_one_boundary(self):
        r = validate([replace(stint(), end=clock(5580, 2))], clock_policy=policy((1, 2)), period_boundaries=[boundary()])
        self.assertIncomplete(r, "cross_period_boundaries_unavailable")

    def test_boundary_without_support_not_used(self):
        for changes in (dict(evidence_refs=()), dict(provenance_refs=()), dict(end_seconds=None)):
            r = validate([replace(stint(), end=clock(5580, 2))], clock_policy=policy((1, 2)),
                period_boundaries=[boundary(), boundary(2, 2700, 5580, **changes)])
            self.assertIncomplete(r, "cross_period_boundaries_unavailable")

    def test_missing_final_whistle_end_no_90_fallback(self):
        for end in (None, clock(None)):
            self.assertIncomplete(validate([replace(stint(), end=end)]), "missing_end_clock")

    def test_missing_entry_clock(self):
        self.assertIncomplete(validate([replace(stint(), start=None)]), "missing_start_clock")

    def test_missing_boundary_reference(self):
        self.assertIncomplete(validate([replace(stint(), end=clock(2880, refs=()))]), "missing_end_evidence")

    def test_missing_observation_evidence(self):
        self.assertIncomplete(validate([replace(stint(), evidence_refs=())]), "missing_observation_evidence")

    def test_missing_source_provenance_visible(self):
        r = validate([replace(stint(), provenance_refs=())])
        self.assertIncomplete(r, "missing_source_provenance")
        self.assertFalse(r.source_independently_verified)

    def test_temporary_exit_without_recorded_return(self):
        self.assertIncomplete(validate([stint(end=1200, exit_kind="temporary_exit")]), "unclosed_temporary_exit")

    def test_unpaired_position_change(self):
        self.assertIncomplete(validate([stint(end=1200, exit_kind="position_change")]), "unclosed_position_change")

    def test_position_unknown_blocks_allocation_and_accepted_total(self):
        self.assertIncomplete(validate([replace(stint(), position=None)]), "missing_position_allocation")

    def test_unknown_transition(self):
        self.assertIncomplete(validate([replace(stint(), exit_kind="unknown")]), "unknown_transition")

    def test_empty_observations_not_zero_participation(self):
        self.assertIncomplete(validate([]), "no_participation_observations")

    def test_cross_period_position_change_missing_boundary(self):
        rows = [stint(end=2880, exit_kind="position_change"),
                replace(stint("b"), start=clock(2700, 2), end=clock(5580, 2), entry_kind="position_change")]
        self.assertIncomplete(validate(rows, clock_policy=policy((1, 2))), "position_change_not_contiguous")

    def test_supplied_boundary_missing_provenance_stays_visible(self):
        self.assertIncomplete(validate(period_boundaries=[boundary(provenance_refs=())]), "missing_period_boundary_provenance")

    def test_other_intervals_never_close_an_open_endpoint(self):
        rows = [replace(stint(), end=clock(None), exit_kind="temporary_exit"),
                stint("b", 1200, 2880, entry_kind="return")]
        r = validate(rows)
        self.assertIncomplete(r, "sequence_evidence_incomplete")
        self.assertIsNone(r.intervals[0].elapsed_seconds)
        self.assertIn("missing_end_clock", codes(r))

    def test_unknown_preceding_exit_is_incomplete_not_a_fabricated_conflict(self):
        rows = [stint(end=1200, exit_kind="unknown"), stint("b", 1260, 2880, entry_kind="return")]
        self.assertIncomplete(validate(rows), "sequence_evidence_incomplete")

    def test_incomplete_exit_support_not_labeled_supported_absence(self):
        rows = [replace(stint(end=1200, exit_kind="temporary_exit"), end=clock(1200, refs=())),
                stint("b", 1260, 2880, entry_kind="return")]
        r = validate(rows)
        self.assertIncomplete(r, "missing_end_evidence")
        self.assertFalse(r.gaps[0].supported_temporary_absence)


class ConflictingEvidenceTests(unittest.TestCase):
    def assertConflict(self, result, code):
        self.assertEqual(result.status, CONFLICT)
        self.assertIsNone(result.elapsed_seconds)
        self.assertIsNone(result.position_allocation)
        self.assertIn(code, codes(result))

    def test_reversed_period_order_d3i_pattern(self):
        row = replace(stint(), start=clock(2712, 2), end=clock(2860, 1), entry_kind="substitution", exit_kind="substitution")
        self.assertConflict(validate([row], clock_policy=policy((1, 2))), "reversed_period_order")

    def test_reversed_within_period_clock(self):
        self.assertConflict(validate([stint(start=1000, end=900, entry_kind="substitution")]), "reversed_within_period_clock")

    def test_overlapping_duplicate_participation(self):
        self.assertConflict(validate([stint(), stint("b")]), "duplicate_participation")

    def test_partial_overlap(self):
        rows = [stint(end=1800, exit_kind="temporary_exit"), stint("b", 1700, 2880, entry_kind="return")]
        self.assertConflict(validate(rows), "overlapping_active_intervals")

    def test_nested_overlap_cannot_hide_behind_shorter_stint(self):
        rows = [stint(end=2800, exit_kind="position_change"),
                stint("b", 100, 200, entry_kind="position_change", exit_kind="position_change"),
                stint("c", 300, 400, entry_kind="position_change", exit_kind="substitution")]
        r = validate(rows)
        self.assertConflict(r, "overlapping_active_intervals")
        self.assertTrue(any(set(i.observation_ids) == {"a", "c"} for i in r.issues if i.code == "overlapping_active_intervals"))

    def test_return_without_preceding_exit(self):
        self.assertConflict(validate([stint(start=1200, entry_kind="return")]), "unsupported_return")

    def test_return_after_permanent_exit(self):
        rows = [stint(end=1200, exit_kind="dismissal"), stint("b", 1300, 2880, entry_kind="return")]
        self.assertConflict(validate(rows), "unsupported_return")

    def test_gap_cannot_be_disguised_as_position_change(self):
        rows = [stint(end=1200, exit_kind="position_change"), stint("b", 1260, 2880, entry_kind="position_change")]
        self.assertConflict(validate(rows), "position_change_not_contiguous")

    def test_repeated_substitution_entry(self):
        rows = [stint(end=1200, exit_kind="substitution"), stint("b", 1260, 2880, entry_kind="substitution")]
        self.assertConflict(validate(rows), "new_entry_after_prior_participation")

    def test_identity_mismatch_quarantined_for_each_key(self):
        for context in (replace(CTX, match_id=102), replace(CTX, player_id=203), replace(CTX, team_key="other")):
            self.assertConflict(validate([replace(stint(), context=context)]), "identity_association_mismatch")

    def test_policy_and_boundary_match_mismatch(self):
        self.assertConflict(validate(clock_policy=policy(match_id=102)), "policy_match_mismatch")
        self.assertConflict(validate(period_boundaries=[boundary(match_id=102)]), "boundary_match_mismatch")

    def test_endpoint_outside_supported_period(self):
        self.assertConflict(validate([stint(end=3000)], period_boundaries=[boundary()]), "clock_outside_supported_period")

    def test_invalid_period_boundaries(self):
        for b in (boundary(end=0), boundary(start=100, end=99)):
            self.assertConflict(validate(period_boundaries=[b]), "nonpositive_period_boundary")

    def test_period_local_origin_must_match_explicit_semantics(self):
        self.assertConflict(validate(clock_policy=policy(convention="period_local"),
            period_boundaries=[boundary(start=10)]), "period_local_origin_not_zero")

    def test_period_outside_policy(self):
        self.assertConflict(validate([replace(stint(), start=clock(0, 2))]), "observation_period_outside_policy")

    def test_match_end_disagrees_with_supported_boundary(self):
        self.assertConflict(validate([stint(end=2700)], period_boundaries=[boundary()]), "match_end_clock_disagreement")

    def test_starter_cannot_begin_later_period_or_after_known_start(self):
        self.assertConflict(validate([replace(stint(), start=clock(2700, 2), end=clock(5580, 2))],
            clock_policy=policy((1, 2))), "starter_after_first_period")
        self.assertConflict(validate([stint(start=10)], period_boundaries=[boundary()]), "starter_after_period_start")


class ContractTests(unittest.TestCase):
    def test_row_order_invariance_including_conflicting_duplicates(self):
        rows = [stint(), stint("b"), stint("c")]
        expected = validate(rows)
        for perm in itertools.permutations(rows):
            self.assertEqual(validate(list(perm)), expected)

    def test_immutability_and_evidence_audit_trail(self):
        rows = [stint()]
        bounds = [boundary()]
        before = copy.deepcopy((rows, bounds))
        r = validate(rows, period_boundaries=bounds)
        self.assertEqual((rows, bounds), before)
        self.assertEqual(r.observations[0].provenance_refs, PROVENANCE)
        self.assertEqual(r.clock_policy.evidence_refs, REFS)
        self.assertEqual(r.period_boundaries[0].evidence_refs, REFS)
        with self.assertRaises(FrozenInstanceError):
            r.status = "changed"

    def test_boundary_order_invariance(self):
        row = replace(stint(), end=clock(5580, 2))
        b = [boundary(), boundary(2, 2700, 5580)]
        self.assertEqual(validate([row], clock_policy=policy((1, 2)), period_boundaries=b),
                         validate([row], clock_policy=policy((1, 2)), period_boundaries=b[::-1]))

    def test_invalid_numeric_clocks_do_not_coerce(self):
        for value in (True, -1, 1.5, "90:00", Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(value=value), self.assertRaises(ParticipationError):
                validate([replace(stint(), start=clock(value))])

    def test_invalid_identity_and_int64_exactness(self):
        for value in (True, 0, -1, "1", 1.5, 2**63):
            with self.subTest(value=value), self.assertRaises(ParticipationError):
                validate_participation(replace(CTX, player_id=value), [], clock_policy=policy())
        ctx = replace(CTX, player_id=2**63 - 1)
        r = validate_participation(ctx, [replace(stint(), context=ctx)], clock_policy=policy())
        self.assertEqual(r.context.player_id, 2**63 - 1)

    def test_duplicate_observation_ids_reject(self):
        with self.assertRaises(ParticipationError):
            validate([stint(), stint()])

    def test_duplicate_boundaries_and_policy_periods_reject(self):
        with self.assertRaises(ParticipationError):
            validate(period_boundaries=[boundary(), boundary()])
        with self.assertRaises(ParticipationError):
            validate(clock_policy=policy((1, 1)))

    def test_mutable_or_bad_evidence_declarations_reject(self):
        for refs in (["test"], ("",), ("test", "test")):
            with self.assertRaises(ParticipationError):
                validate([replace(stint(), evidence_refs=refs)])

    def test_invalid_contract_objects_reject(self):
        for rows in ({}, [None], [dict(match_id=101)]):
            with self.assertRaises(ParticipationError):
                validate(rows)
        with self.assertRaises(ParticipationError):
            validate([replace(stint(), entry_kind="invented-provider-event")])
        with self.assertRaises(ParticipationError):
            validate(clock_policy=policy(convention=[]))

    def test_no_trust_or_eligibility_promotion(self):
        r = validate()
        self.assertFalse(r.source_independently_verified)
        self.assertFalse(r.publication_authorized)
        for name in ("minutes", "season_total", "eligible", "percentile", "rating", "ovr"):
            self.assertFalse(hasattr(r, name))

    def test_module_has_no_io_network_or_scoring_import(self):
        tree = ast.parse(inspect.getsource(module))
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertNotIn("src.dri_scoring", imports)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, ("open", "print", "input", "eval", "exec"))


if __name__ == "__main__":
    unittest.main()
