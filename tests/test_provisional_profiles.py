"""Diagnostic contract regressions: synthetic edge cases plus actual D2B records.

No public JSON, fictional production dataset or production attestation is created.
"""
import copy
import hashlib
import json
from pathlib import Path
import unittest

import pandas as pd
import pyarrow.parquet as pq

from scripts.audit_match_scoped_metrics import EVENT_COLUMNS, match_metrics
from src.frontend_export import FrontendExportError, export_scorecard
from src.identity import PLAYER_KEYS
from src.provisional_profiles import SCHEMA_VERSION, STATUS, ProfileContractError, build_profiles


def fixture(rows=None, *, player_id=1, complete=True):
    # Small synthetic source ledger; not a real-player or production fixture.
    base = dict(id="e1", match_id=10, player="Fixture Actor", team="Team",
        competition_name="League", season_name="Season", type="Ball Recovery", location=[10, 10],
        duel_type=None, duel_outcome=None, interception_outcome=None,
        ball_recovery_recovery_failure=None, under_pressure=None, pass_outcome=None,
        dribble_outcome=None, period=1, minute=1, second=0)
    events = pd.DataFrame([base | changes for changes in (rows if rows is not None else [{}])])
    crosswalk = pd.DataFrame([dict(player_id=player_id, player_name_raw="Fixture Actor", team="Team",
                                   competition_name="League", season_name="Season")])
    minutes = crosswalk[PLAYER_KEYS].assign(minutes=900.0)
    lineups = pd.DataFrame([dict(match_id=int(mid), team="Team", player_id=player_id,
        player_name="Fixture Actor", position="Center Back", from_time="00:00", to_time="10:00",
        from_period=1, to_period=1, start_reason="Starting XI", end_reason="Substitution - Off (Tactical)")
        for mid in sorted(events.match_id.unique())])
    metadata = events[["match_id", "competition_name", "season_name"]].drop_duplicates()
    return match_metrics(events, crosswalk, minutes, lineups, metadata,
                         local_collection_complete=complete), minutes


def profile(audit=None, minutes=None):
    if audit is None:
        audit, minutes = fixture()
    return build_profiles(audit, delivered_minutes=minutes)["profiles"][0]


class ProvisionalProfileTests(unittest.TestCase):
    def test_exact_canonical_identity_and_decimal_ids(self):
        row = profile()
        self.assertEqual({k: row["identity"][k] for k in PLAYER_KEYS},
                         dict(player_id="1", team="Team", competition_name="League", season_name="Season"))
        self.assertEqual(row["identity"]["player_name"], "Fixture Actor")

    def test_int64_identity_survives_json_without_float_rounding(self):
        audit, minutes = fixture(player_id=2**63 - 1)
        result = json.loads(json.dumps(build_profiles(audit, delivered_minutes=minutes), allow_nan=False))
        self.assertEqual(result["profiles"][0]["identity"]["player_id"], str(2**63 - 1))

    def test_mutated_unsafe_float_metric_identity_is_rejected(self):
        audit, _ = fixture(player_id=2**53)
        audit.pooled.recovery["player_id"] = float(2**53)
        with self.assertRaisesRegex(ProfileContractError, "invalid exact identity"):
            build_profiles(audit)

    def test_per_match_counts_and_pooled_counts(self):
        audit, minutes = fixture([{}, {"id": "e2", "match_id": 20}])
        row = profile(audit, minutes)
        self.assertEqual(row["scope"]["observed_match_ids"], ["10", "20"])
        self.assertEqual([m["recovery"]["Ball Recovery"]["count"] for m in row["matches"]], ["1", "1"])
        self.assertEqual(row["pooled"]["recovery"]["Ball Recovery"]["count"], "2")

    def test_pooled_completion_uses_attempts_not_mean_match_percentages(self):
        rows = [{"id": "p0", "type": "Pass", "under_pressure": True}]
        rows += [{"id": f"p{i}", "match_id": 20, "type": "Pass", "under_pressure": True,
                  "pass_outcome": "Incomplete"} for i in range(1, 4)]
        audit, minutes = fixture(rows)
        row = profile(audit, minutes)
        self.assertEqual(row["pooled"]["press"]["percentages"]["press_resistance_rate"]["value"], 25)
        self.assertEqual(row["pooled"]["press"]["counts"]["pressured_actions"], "4")

    def test_missing_observed_zero_and_undefined_are_distinct(self):
        audit, minutes = fixture([{"type": "Pass", "under_pressure": True, "pass_outcome": "Incomplete"}])
        row = profile(audit, minutes)["pooled"]
        self.assertEqual(row["recovery"]["Tackle"]["status"], "missing")
        self.assertIsNone(row["recovery"]["Tackle"]["count"])
        self.assertIsNone(row["recovery"]["Tackle"]["zone_counts"])
        self.assertEqual(row["press"]["counts"]["pressured_pass_completed"], "0")
        self.assertEqual(row["press"]["percentages"]["pressured_pass_completion_rate"],
                         {"status": "observed", "value": 0.0})
        self.assertEqual(row["press"]["percentages"]["pressured_dribble_completion_rate"],
                         {"status": "undefined_zero_attempts", "value": None})

    def test_missing_whole_press_block_is_not_zero_counts(self):
        press = profile()["pooled"]["press"]
        self.assertEqual(press["status"], "missing")
        self.assertTrue(all(v is None for v in press["counts"].values()))

    def test_not_assessed_progression_is_explicit(self):
        self.assertEqual(profile()["not_assessed_metric_families"], ["progression"])

    def test_aligned_minutes_match_count_scope(self):
        row = profile()["matches"][0]
        per90 = row["recovery"]["Ball Recovery"]["per90"]
        self.assertEqual(per90["value"], 9)
        self.assertEqual(per90["aligned_minutes"], 10)
        self.assertEqual(per90["numerator_match_ids"], per90["denominator_match_ids"])

    def test_unproven_collection_withholds_per90(self):
        audit, minutes = fixture(complete=False)
        rate = profile(audit, minutes)["pooled"]["recovery"]["Ball Recovery"]["per90"]
        self.assertFalse(rate["available"])
        self.assertIsNone(rate["value"])
        self.assertIsNone(rate["denominator_match_ids"])
        self.assertIn("local_match_collection_not_established", rate["reasons"])

    def test_wider_scope_minutes_are_metadata_not_denominators(self):
        audit, minutes = fixture()
        minutes["minutes"] = 0.0
        row = profile(audit, minutes)
        self.assertEqual(row["pooled"]["exposure"]["delivered_minutes_status"], "zero")
        self.assertEqual(row["pooled"]["exposure"]["aligned_minutes"], 10)
        self.assertEqual(row["pooled"]["recovery"]["Ball Recovery"]["per90"]["value"], 9)
        self.assertIn("observed_activity_with_zero_delivered_minutes", row["pooled"]["exposure"]["source_ambiguities"])

    def test_missing_delivered_minutes_not_replaced_by_zero(self):
        audit, minutes = fixture()
        minutes["minutes"] = float("nan")
        exposure = profile(audit, minutes)["pooled"]["exposure"]
        self.assertIsNone(exposure["delivered_minutes"])
        self.assertEqual(exposure["delivered_minutes_status"], "missing")
        self.assertEqual(build_profiles(audit)["profiles"][0]["pooled"]["exposure"]["delivered_minutes_status"],
                         "not_supplied")

    def test_input_immutability_and_fresh_return_values(self):
        audit, minutes = fixture()
        original = copy.deepcopy(audit)
        original_minutes = minutes.copy(deep=True)
        output = build_profiles(audit, delivered_minutes=minutes)
        output["profiles"][0]["identity"]["player_name"] = "changed returned label"
        pd.testing.assert_frame_equal(audit.events, original.events)
        pd.testing.assert_frame_equal(audit.exposure, original.exposure)
        pd.testing.assert_frame_equal(audit.pooled.recovery, original.pooled.recovery)
        pd.testing.assert_frame_equal(minutes, original_minutes)
        self.assertEqual(profile(audit, minutes)["identity"]["player_name"], "Fixture Actor")

    def test_duplicate_metric_keys_rejected(self):
        audit, _ = fixture()
        audit.pooled.recovery = pd.concat([audit.pooled.recovery, audit.pooled.recovery])
        with self.assertRaisesRegex(ProfileContractError, "duplicate"):
            build_profiles(audit)

    def test_missing_or_extra_match_window_rejected(self):
        audit, _ = fixture()
        audit.per_match[99] = copy.deepcopy(audit.per_match[10])
        with self.assertRaisesRegex(ProfileContractError, "exactly.*window"):
            build_profiles(audit)

    def test_changed_count_or_averaged_percentage_rejected(self):
        for field in ("count", "rate"):
            with self.subTest(field=field):
                audit, _ = fixture([{"type": "Pass", "under_pressure": True}])
                if field == "count":
                    audit.pooled.press.loc[:, "pressured_pass_attempts"] = 99
                else:
                    audit.pooled.press.loc[:, "press_resistance_rate"] = 50.0
                with self.assertRaises(ProfileContractError):
                    build_profiles(audit)

    def test_mismatched_minutes_or_per90_rejected(self):
        for column in ("minutes", "per90"):
            with self.subTest(column=column):
                audit, _ = fixture()
                audit.recovery_per90.loc[:, column] = 999.0
                with self.assertRaisesRegex(ProfileContractError, "scope/count/value"):
                    build_profiles(audit)

    def test_provenance_cannot_be_promoted(self):
        audit, _ = fixture()
        audit.summary["authoritative_feed_complete"] = True
        with self.assertRaisesRegex(ProfileContractError, "promoted"):
            build_profiles(audit)

    def test_deterministic_despite_table_and_dictionary_order(self):
        audit, minutes = fixture([{}, {"id": "e2", "match_id": 20}])
        expected = build_profiles(audit, delivered_minutes=minutes)
        audit.per_match = dict(reversed(list(audit.per_match.items())))
        audit.exposure = audit.exposure.iloc[::-1].reset_index(drop=True)
        self.assertEqual(build_profiles(audit, delivered_minutes=minutes), expected)
        json.dumps(expected, allow_nan=False)

    def test_no_production_schema_compatibility_or_export(self):
        audit, _ = fixture()
        result = build_profiles(audit)
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertNotEqual(SCHEMA_VERSION, "soccer-scorecard/v1")
        self.assertFalse(result["production_schema_compatible"])
        self.assertEqual(result["verification_status"], STATUS)
        with self.assertRaises(FrontendExportError):
            export_scorecard(result)

    def test_unobserved_bench_player_does_not_become_profile(self):
        audit, _ = fixture()
        # Existing D2B validation rejects a fabricated table row, rather than
        # using it to manufacture a profile from a source lookup or roster.
        extra = audit.pooled.recovery.copy()
        extra["player_id"] = 2
        audit.pooled.recovery = pd.concat([audit.pooled.recovery, extra])
        with self.assertRaises(ProfileContractError):
            build_profiles(audit)

    def test_valid_bench_record_does_not_expand_profile_population(self):
        audit, minutes = fixture()
        bench = audit.lineups.iloc[0].copy()
        bench["player_id"], bench["player_name"], bench["player_name_raw"] = 2, "Synthetic Bench", "Synthetic Bench"
        for column in ("position", "from_time", "to_time", "from_period", "to_period", "start_reason", "end_reason"):
            bench[column] = None
        lineups = pd.concat([audit.lineups, bench.to_frame().T], ignore_index=True)
        checked = match_metrics(audit.events, audit.pooled.identity.lookup.observations,
            minutes, lineups, audit.lineups[["match_id", "competition_name", "season_name"]],
            local_collection_complete=True)
        self.assertEqual([p["identity"]["player_id"] for p in build_profiles(checked)["profiles"]], ["1"])


class RealD2BProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = {"events": Path('data/validation/drive-raw-review/statsbomb_team_events.parquet'),
                     "crosswalk": Path('data/processed/player_name_crosswalk.parquet'),
                     "minutes": Path('data/validation/arpit-2026-10-21/player_minutes.parquet'),
                     "lineups": Path('data/raw/statsbomb_lineups.parquet'),
                     "metadata": Path('data/validation/arpit-match-context-review/match_metadata.parquet')}
        if not all(p.is_file() for p in cls.paths.values()):
            raise unittest.SkipTest("real D2B local inputs unavailable; no substitutions")
        # Reuse D2B's exhaustive scan evidence only for the EXACT unchanged file.
        # The fingerprint and four complete local counts are recorded in D1B/D2B.
        with cls.paths["events"].open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        assert digest == 'ec12fdd2340fb125671f4996abdac510c3dc6d81555848792520ce5df2519eb8'
        prefix = next(pq.ParquetFile(cls.paths["events"]).iter_batches(
            batch_size=65536, columns=EVENT_COLUMNS)).to_pandas()
        events = prefix.loc[prefix.match_id.isin([3895107,3895292,3895320,3895348])].reset_index(drop=True)
        assert events.groupby('match_id').size().to_dict() == {3895107:2403,3895292:2211,3895320:2134,3895348:2454}
        cls.minutes = pq.read_table(cls.paths["minutes"]).to_pandas()
        cls.audit = match_metrics(events, pq.read_table(cls.paths["crosswalk"]).to_pandas(), cls.minutes,
            pq.read_table(cls.paths["lineups"]).to_pandas(), pq.read_table(cls.paths["metadata"]).to_pandas(),
            local_collection_complete=True)
        cls.output = build_profiles(cls.audit, delivered_minutes=cls.minutes)
        cls.players = {p['identity']['player_id']: p for p in cls.output['profiles']}

    def test_real_contexts_and_conservation(self):
        self.assertEqual(len(self.output['profiles']), 82)
        self.assertEqual(len({tuple(p['identity'][k] for k in PLAYER_KEYS) for p in self.output['profiles']}), 82)
        self.assertEqual(sum(int(p['scope']['observed_event_count']) for p in self.output['profiles']), 9202)
        for category, count in [('Tackle',77),('Interception',48),('Ball Recovery',350)]:
            self.assertEqual(sum(int(p['pooled']['recovery'][category]['count'] or 0) for p in self.output['profiles']),count)
        self.assertEqual(sum(int(p['pooled']['press']['counts']['pressured_actions'] or 0) for p in self.output['profiles']),737)

    def test_real_xhaka_pooled_counts_and_rate(self):
        row = self.players['3500']
        self.assertEqual(row['identity']['player_name'], 'Granit Xhaka')
        self.assertEqual(row['pooled']['recovery']['Ball Recovery']['count'], '16')
        self.assertEqual(row['pooled']['press']['counts']['pressured_pass_attempts'], '32')
        self.assertAlmostEqual(row['pooled']['press']['percentages']['press_resistance_rate']['value'],87.87878787878788)

    def test_real_hlozek_match_rate_retained_but_pool_withheld(self):
        row = self.players['28239']
        match = next(m for m in row['matches'] if m['match_id']=='3895292')
        self.assertAlmostEqual(match['recovery']['Ball Recovery']['per90']['value'],5.630865484880083)
        self.assertFalse(row['pooled']['recovery']['Ball Recovery']['per90']['available'])
        self.assertIn('3895348',row['scope']['included_match_ids'])  # Explicit bench record, no fake action row.
        self.assertNotIn('3895348',row['scope']['observed_match_ids'])

    def test_real_breithaupt_supported_pool_and_zero_minute_actors(self):
        row = self.players['51825']
        self.assertAlmostEqual(row['pooled']['recovery']['Ball Recovery']['per90']['value'],4.473902236951118)
        for player_id in ('8934','32253','316245'):
            exposure = self.players[player_id]['pooled']['exposure']
            self.assertEqual(exposure['delivered_minutes'],0)
            self.assertIsNone(exposure['aligned_minutes'])
            self.assertIn('observed_activity_with_zero_delivered_minutes',exposure['source_ambiguities'])
        json.dumps(self.output,allow_nan=False)


if __name__ == '__main__':
    unittest.main()
