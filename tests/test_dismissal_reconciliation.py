"""Synthetic dismissal-precedence candidates; original source assertions stay intact."""
import copy
from fractions import Fraction
import unittest

from src.dismissal_reconciliation import reconcile_dismissal
from src.participation_intervals import CONFLICT, VALID
from src.statsbomb_participation import SourceDocument, _timestamp
from test_statsbomb_participation import fixture, run, source, transition


def prepared(kind='Second Yellow', typ='Foul Committed'):
    data = fixture()
    teammate = copy.deepcopy(data[1][0]['lineup'][0])
    teammate.update(player_id=103, player_name='Teammate')
    data[1][0]['lineup'].append(teammate)
    xi = next(e for e in data[2] if e['type']['name'] == 'Starting XI' and e['team']['id'] == 1)
    xi['tactics']['lineup'].append(dict(player=dict(id=103, name='Teammate'), position=dict(id=3, name='Right Center Back')))
    field = 'foul_committed' if typ == 'Foul Committed' else 'bad_behaviour'
    transition(data[2], typ, '00:35:00.125', 80, 0, **{field: {'card': {'name': kind}}})
    return data


def indexed(data):
    for index, event in enumerate(sorted(data[2], key=lambda e: (e['period'], _timestamp(e['timestamp']))), 1):
        event['index'] = index


def review(data, assign_indices=True, pid=101):
    if assign_indices:
        indexed(data)
    adapted = run(data)
    return adapted, reconcile_dismissal(adapted, source(data[2], 'events'), pid)


class DismissalReconciliationTests(unittest.TestCase):
    def test_second_yellow_recovers_exact_source_elapsed_time(self):
        adapted, result = review(prepared())
        self.assertEqual(result.original.status, CONFLICT)
        self.assertEqual(result.candidate.status, VALID)
        self.assertEqual(result.candidate.elapsed_seconds, Fraction('4950.625'))
        self.assertEqual(result.observations[-1].exit_kind, 'dismissal')
        self.assertTrue(result.dismissal_reference)
        self.assertFalse(result.reasons or result.publication_authorized)
        self.assertEqual(adapted.validate()[0].status, CONFLICT)

    def test_direct_red_foul_uses_same_policy(self):
        self.assertEqual(review(prepared('Red Card'))[1].candidate.elapsed_seconds, Fraction('4950.625'))

    def test_active_bad_behaviour_card_uses_same_policy(self):
        self.assertIsNotNone(review(prepared('Second Yellow', 'Bad Behaviour'))[1].candidate)

    def test_later_passive_tactical_snapshot_is_retained_as_stale(self):
        data = prepared()
        original = data[1][0]['lineup'][0]['positions'][0]
        later = copy.deepcopy(original)
        original.update(to='85:00', to_period=2, end_reason='Tactical Shift')
        later.update(**{'from': '85:00'}, from_period=2, start_reason='Tactical Shift', position_id=4, position='Center Back')
        data[1][0]['lineup'][0]['positions'].append(later)
        transition(data[2], 'Tactical Shift', '00:40:00.250', 85, 0,
                   tactics={'lineup': [{'player': {'id': 101, 'name': 'Home Player'}, 'position': {'id': 4, 'name': 'Center Back'}}]})
        data[2][-1].pop('player')
        adapted, result = review(data)
        self.assertEqual(result.candidate.elapsed_seconds, Fraction('4950.625'))
        self.assertEqual(len(result.stale_snapshot_references), 1)
        self.assertEqual(len(result.observations), 1)
        self.assertEqual(len(adapted.players[0].raw_positions), 2)

    def test_actual_later_player_action_blocks_reconciliation(self):
        data = prepared()
        transition(data[2], 'Ball Recovery', '00:36:00.000', 81, 0)
        result = review(data)[1]
        self.assertIsNone(result.candidate)
        self.assertIn('PLAYER_ACTIVITY_AFTER_DISMISSAL', result.reasons)

    def test_later_pass_received_blocks_reconciliation(self):
        data = prepared()
        transition(data[2], 'Pass', '00:36:00.000', 81, 0,
                   player={'id': 103, 'name': 'Teammate'}, **{'pass': {'recipient': {'id': 101, 'name': 'Home Player'}}})
        self.assertIn('PLAYER_ACTIVITY_AFTER_DISMISSAL', review(data)[1].reasons)

    def test_equal_clock_activity_after_card_is_not_admitted(self):
        data = prepared()
        transition(data[2], 'Ball Recovery', '00:35:00.125', 80, 0)
        self.assertIn('PLAYER_ACTIVITY_AFTER_DISMISSAL', review(data)[1].reasons)

    def test_equal_clock_activity_before_card_remains_usable(self):
        data = prepared()
        transition(data[2], 'Ball Recovery', '00:35:00.125', 80, 0)
        card, action = data[2][-2:]
        data[2][-2:] = [action, card]
        self.assertIsNotNone(review(data)[1].candidate)

    def test_multiple_dismissals_are_not_silently_deduplicated(self):
        data = prepared()
        transition(data[2], 'Bad Behaviour', '00:36:00.000', 81, 0, bad_behaviour={'card': {'name': 'Red Card'}})
        self.assertIn('UNIQUE_DISMISSAL_REQUIRED', review(data)[1].reasons)

    def test_yellow_card_does_not_end_participation(self):
        self.assertIsNone(review(prepared('Yellow Card'))[1].candidate)

    def test_existing_supported_dismissal_is_unchanged(self):
        data = prepared()
        data[1][0]['lineup'][0]['positions'][0].update(to='80:00', to_period=2, end_reason='Foul Committed (Second Yellow)')
        result = review(data)[1]
        self.assertEqual(result.original.status, VALID)
        self.assertIsNone(result.candidate)

    def test_incomplete_half_boundary_is_not_replaced_with_ninety_minutes(self):
        data = prepared()
        for event in data[2]:
            if event['type']['name'] == 'Half End' and event['period'] == 2:
                event['half_end'] = {'early_video_end': True}
        self.assertIn('UNRELATED_OR_INCOMPLETE_SOURCE_EVIDENCE', review(data)[1].reasons)

    def test_unrelated_position_conflict_is_not_removed(self):
        data = prepared()
        transition(data[2], 'Tactical Shift', '00:30:00.000', 75, 0,
                   tactics={'lineup': [{'player': {'id': 101, 'name': 'Home Player'}, 'position': {'id': 4, 'name': 'Center Back'}}]})
        data[2][-1].pop('player')
        self.assertIn('UNRELATED_OR_INCOMPLETE_SOURCE_EVIDENCE', review(data)[1].reasons)

    def test_missing_source_indices_withhold_candidate(self):
        self.assertIn('UNIQUE_SOURCE_INDICES_REQUIRED', review(prepared(), False)[1].reasons)

    def test_source_index_clock_disagreement_withholds_candidate(self):
        data = prepared(); indexed(data)
        data[2][-1]['index'] = 1000
        self.assertIn('SOURCE_CLOCK_INDEX_DISAGREEMENT', review(data, False)[1].reasons)

    def test_different_event_bytes_cannot_be_used(self):
        data = prepared(); indexed(data)
        adapted = run(data)
        document = SourceDocument(b'[]', 'synthetic/events', 'test-v1')
        with self.assertRaises(ValueError):
            reconcile_dismissal(adapted, document, 101)

    def test_input_immutability_and_event_array_order_independence(self):
        data = prepared(); indexed(data); before = copy.deepcopy(data)
        adapted, result = review(data, False)
        self.assertEqual(data, before)
        self.assertEqual(result, reconcile_dismissal(adapted, source(data[2], 'events'), 101))
        data[2].reverse()
        other = review(data, False)[1]
        self.assertEqual(result.candidate.elapsed_seconds, other.candidate.elapsed_seconds)
