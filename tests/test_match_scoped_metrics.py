"""Synthetic match-window and explicit-stint tests; no real evidence promotion."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts.audit_match_scoped_metrics import (
    EVENT_COLUMNS, MATCH_PLAYER, assess_exposure, collect_matches, match_metrics,
)
from scripts.audit_provisional_identity import prepare_provisional_lookup
from scripts.audit_provisional_metrics import MetricsPrerequisiteError
from src.identity import IdentityError, PLAYER_KEYS


def event(event_id="e1", match_id=10, **changes):
    return dict(id=event_id, match_id=match_id, player="Player", team="Team",
                competition_name="League", season_name="Season", type="Ball Recovery",
                location=[10, 10], duel_type=None, duel_outcome=None, interception_outcome=None,
                ball_recovery_recovery_failure=None, under_pressure=None, pass_outcome=None,
                dribble_outcome=None, period=1, minute=1, second=0) | changes


def lineup(match_id=10, **changes):
    return dict(match_id=match_id, team="Team", player_id=1, player_name="Player",
                position="Center Back", from_time="00:00", to_time="10:00", from_period=1,
                to_period=1, start_reason="Starting XI", end_reason="Substitution - Off (Tactical)") | changes


def fixture(events=None, lineups=None, metadata=None):
    e = pd.DataFrame(events if events is not None else [event()])
    x = pd.DataFrame([dict(player_id=1, player_name_raw="Player", team="Team",
                           competition_name="League", season_name="Season")])
    minutes = x[PLAYER_KEYS].assign(minutes=900.0)
    l = pd.DataFrame(lineups if lineups is not None else [lineup()])
    context = (pd.DataFrame(metadata) if metadata is not None else
               e[["match_id", "competition_name", "season_name"]].drop_duplicates())
    return e, x, minutes, l, context


def audit(events=None, lineups=None, metadata=None):
    # Emulate an exhaustive local synthetic fixture, not authoritative source truth.
    return match_metrics(*fixture(events, lineups, metadata), local_collection_complete=True)


class MatchMetricsTests(unittest.TestCase):
    def test_per_match_and_pooled_count_conservation(self):
        result = audit([event("a"), event("b", 20)], [lineup(), lineup(20)])
        self.assertEqual(result.pooled.recovery["count"].sum(), 2)
        self.assertEqual([r.recovery["count"].sum() for r in result.per_match.values()], [1, 1])
        self.assertEqual(result.events.id.tolist(), ["a", "b"])
        self.assertEqual(result.pooled.identity.summary["selected"], 2)

    def test_context_contradiction_rejected_not_first_selected(self):
        with self.assertRaisesRegex(IdentityError, "conflicting match"):
            audit(metadata=[dict(match_id=10, competition_name="Other", season_name="Season")])

    def test_missing_metadata_rejected(self):
        with self.assertRaisesRegex(IdentityError, "absent.*metadata"):
            audit(metadata=[dict(match_id=20, competition_name="League", season_name="Season")])

    def test_unresolved_identity_refuses_partial_player_metrics(self):
        with self.assertRaises(MetricsPrerequisiteError) as caught:
            audit([event(), event("u", player="Unknown")])
        self.assertEqual(caught.exception.identity.summary["unresolved"], 1)

    def test_actor_must_have_exact_match_team_id_and_spelling_evidence(self):
        for change in ({"player_id": 2}, {"player_name": "Other"}, {"team": "Other"}):
            with self.subTest(change=change), self.assertRaisesRegex(IdentityError, "absent.*lineup"):
                audit(lineups=[lineup(**change)])

    def test_extra_lineup_team_discrepancy_rejected(self):
        with self.assertRaisesRegex(IdentityError, "match-team"):
            audit(lineups=[lineup(), lineup(team="Other", player_id=2)])

    def test_explicit_matching_stint_supports_only_provisional_per90(self):
        result = audit()
        self.assertEqual(result.exposure.minutes.tolist(), [10])
        self.assertEqual(result.recovery_per90.per90.tolist(), [9])
        self.assertFalse(result.summary["authoritative_feed_complete"])

    def test_multiple_contiguous_stints_not_double_counted(self):
        result = audit(lineups=[lineup(to_time="05:00", end_reason="Tactical Shift"),
                               lineup(from_time="05:00", start_reason="Tactical Shift")])
        self.assertEqual(result.exposure.minutes.tolist(), [10])
        self.assertEqual(result.recovery_per90.per90.tolist(), [9])

    def test_missing_end_withholds_not_90_or_last_event_estimate(self):
        result = audit(lineups=[lineup(to_time=None, to_period=None, end_reason="Final Whistle")])
        self.assertTrue(result.recovery_per90.per90.isna().all())
        self.assertIn("missing_or_invalid", result.exposure.reasons.iloc[0])

    def test_missing_start_withholds(self):
        result = audit(lineups=[lineup(from_time=None)])
        self.assertTrue(result.recovery_per90.per90.isna().all())

    def test_overlapping_or_duplicate_stints_withhold(self):
        for rows in ([lineup(), lineup()],
                     [lineup(to_time="06:00", end_reason="Tactical Shift"),
                      lineup(from_time="05:00", start_reason="Tactical Shift")]):
            with self.subTest(rows=rows):
                result = audit(lineups=rows)
                self.assertTrue(result.recovery_per90.per90.isna().all())
                self.assertIn("overlapping", result.exposure.reasons.iloc[0])

    def test_gapped_stints_withhold(self):
        result = audit(lineups=[lineup(to_time="04:00", end_reason="Tactical Shift"),
                               lineup(from_time="05:00", start_reason="Tactical Shift")])
        self.assertIn("gapped", result.exposure.reasons.iloc[0])
        self.assertTrue(result.recovery_per90.per90.isna().all())

    def test_cross_period_duration_withheld(self):
        result = audit(lineups=[lineup(to_period=2, to_time="60:00")])
        self.assertIn("cross_period", result.exposure.reasons.iloc[0])
        self.assertTrue(result.recovery_per90.per90.isna().all())

    def test_actor_outside_stint_withheld_not_dropped(self):
        result = audit([event(minute=20)])
        self.assertEqual(result.pooled.recovery["count"].sum(), 1)
        self.assertIn("outside_stints", result.exposure.reasons.iloc[0])
        self.assertTrue(result.recovery_per90.per90.isna().all())

    def test_zero_season_minutes_do_not_override_explicit_match_stints(self):
        e, x, m, l, c = fixture()
        m["minutes"] = 0.0
        result = match_metrics(e, x, m, l, c, local_collection_complete=True)
        self.assertEqual(result.pooled.summary["selected_contexts_zero_minutes"], 1)
        self.assertEqual(result.recovery_per90.minutes.tolist(), [10])

    def test_stoppage_time_not_capped_at_90(self):
        result = audit([event(period=2, minute=91)],
                       [lineup(from_time="90:45", to_time="94:45", from_period=2, to_period=2,
                               start_reason="Substitution - On (Tactical)")])
        self.assertEqual(result.exposure.minutes.tolist(), [4])
        self.assertEqual(result.recovery_per90.per90.tolist(), [22.5])

    def test_extra_time_closed_interval_does_not_assume_90_minute_match(self):
        result = audit([event(period=3, minute=95)],
                       [lineup(from_time="92:00", to_time="102:00", from_period=3, to_period=3,
                               start_reason="Substitution - On (Tactical)")])
        self.assertEqual(result.exposure.minutes.tolist(), [10])

    def test_bench_actor_is_ambiguous_not_invented_zero_exposure(self):
        row = lineup(**{k: None for k in ["position", "from_time", "to_time", "from_period",
                                          "to_period", "start_reason", "end_reason"]})
        result = audit(lineups=[row])
        self.assertIn("actor_without_position_stint", result.exposure.reasons.iloc[0])
        self.assertTrue(result.recovery_per90.per90.isna().all())

    def test_unobserved_bench_players_do_not_get_metric_zero_rows(self):
        row = lineup(player_id=2, player_name="Bench", **{k: None for k in [
            "position", "from_time", "to_time", "from_period", "to_period", "start_reason", "end_reason"]})
        result = audit(lineups=[lineup(), row])
        self.assertEqual(result.exposure.exposure_status.tolist(), ["aligned_explicit_stints", "bench_no_stint"])
        self.assertEqual(result.pooled.recovery.player_id.tolist(), [1])

    def test_unaligned_match_blocks_pooled_per90_for_that_context(self):
        result = audit([event("a"), event("b", 20)],
                       [lineup(), lineup(20, to_time=None, to_period=None)])
        self.assertEqual(result.recovery_per90.per90.notna().sum(), 1)
        self.assertTrue(result.pooled_recovery_per90.per90.isna().all())

    def test_closed_stints_alone_cannot_certify_a_prefix_as_complete(self):
        result = match_metrics(*fixture())
        self.assertFalse(result.summary["local_collection_complete"])
        self.assertTrue(result.recovery_per90.per90.isna().all())
        self.assertEqual(result.exposure.reasons.tolist(), ["local_match_collection_not_established"])


class MatchCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "events.parquet"

    def write(self, rows):
        pq.write_table(pa.Table.from_pandas(pd.DataFrame(rows)), self.path, row_group_size=2)

    def collect(self, **kwargs):
        return collect_matches(self.path, [10], batch_size=2, scratch_dir=self.root, **kwargs)

    def test_entire_match_after_batch_and_unrelated_match_boundaries(self):
        self.write([event("a"), event("other", 20), event("b"), event("c"), event("last", 30)])
        before = self.path.read_bytes()
        events, summary = self.collect()
        self.assertEqual(events.id.tolist(), ["a", "b", "c"])
        self.assertEqual(summary["source_rows_scanned"], 5)
        self.assertEqual(summary["global_unique_event_ids"], 5)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_duplicate_ids_across_batches_even_nonselected_matches_fail(self):
        self.write([event("a"), event("duplicate", 20), event("duplicate", 30)])
        with self.assertRaisesRegex(IdentityError, "global source"):
            self.collect()
        self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_selected_event_cap_refuses_partial_match(self):
        self.write([event("a"), event("b"), event("c")])
        with self.assertRaisesRegex(IdentityError, "no partial match"):
            self.collect(max_events=2)

    def test_absent_requested_match_fails(self):
        self.write([event(match_id=20)])
        with self.assertRaisesRegex(IdentityError, "absent"):
            self.collect()

    def test_watched_actor_accounting_includes_unselected_matches(self):
        self.write([event("a"), event("b", 20), event("c", 30, player="Unknown")])
        _, crosswalk, _, _, _ = fixture()
        events, summary = self.collect(watch_lookup=prepare_provisional_lookup(crosswalk).lookup)
        self.assertEqual(events.id.tolist(), ["a"])
        self.assertEqual(sum(row["events"] for row in summary["watched_actor_counts"]), 2)
        self.assertEqual([row["match_id"] for row in summary["watched_actor_counts"]], [10, 20])


if __name__ == "__main__":
    unittest.main()
