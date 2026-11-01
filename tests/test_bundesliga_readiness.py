"""Focused safeguards for separate Bundesliga verification, using invented data."""
import copy
from fractions import Fraction
import unittest

from scripts.verify_bundesliga_readiness import (
    DEFENSIVE, PRESS, player_readiness, position_summary, press_evidence,
)
from src.source_reconstruction import rational


def metric(attempts=2, successes=1):
    counts = dict(zip(PRESS, [attempts, successes, 0, 0]))
    return dict(player_id=101, components={n: dict(count=c) for n,c in counts.items()})


def club(mid=10, minutes=95, unresolved=False):
    return dict(player_id=101, team='Invented Club', team_id=1, match_ids=[mid],
        raw_player_names=['Invented Player'], source_position_minutes={'Center Back':rational(Fraction(minutes))},
        known_supported_minutes=minutes, provider_observed_exposure_complete=not unresolved,
        unresolved_match_ids=[mid+1] if unresolved else [], withheld_appearance_count=int(unresolved),
        components={n:dict(aligned_appearance_count=1,aligned_match_ids=[mid],
            aligned_subset_minutes=rational(Fraction(minutes)),aligned_subset_count=2) for n in DEFENSIVE})


class BundesligaReadinessTests(unittest.TestCase):
    def test_sub40_press_retains_measurement_and_never_zero_fills(self):
        result=press_evidence([metric()])
        self.assertEqual(result['measured_percent'],50)
        self.assertTrue(result['below_40_limited_data'])
        self.assertFalse(result['observed_40_actions'])
        self.assertIsNone(press_evidence([metric(0,0)])['measured_percent'])

    def test_press40_boundary_and_identity_conflict(self):
        self.assertTrue(press_evidence([metric(40,30)])['observed_40_actions'])
        self.assertEqual(press_evidence([metric()],{101})['status'],'N/A')

    def test_unsupported_appearances_do_not_inflate_denominator(self):
        c=club(unresolved=True); before=copy.deepcopy(c)
        p=player_readiness([c],[metric()])
        self.assertEqual(p['defensive']['tackles']['supported_minutes'],rational(Fraction(95)))
        self.assertFalse(p['all_observed_appearance_minutes_supported'])
        self.assertEqual(p['unresolved_match_ids'],[11]);self.assertEqual(c,before)
        self.assertTrue(p['partial_season_coverage'])
        self.assertIsNone(p['ratings']);self.assertFalse(p['reference_member'])

    def test_transfer_same_fixture_rejected(self):
        with self.assertRaisesRegex(ValueError,'overlapping'):
            player_readiness([club(),club()],[metric()])

    def test_transfer_adds_counts_and_minutes_without_club_ratings(self):
        p=player_readiness([club(10,95),club(20,5)],[metric(),metric(3,2)])
        self.assertEqual(p['defensive']['tackles']['supported_count'],4)
        self.assertEqual(p['defensive']['tackles']['supported_minutes'],rational(Fraction(100)))
        self.assertEqual(p['press']['attempts'],5);self.assertEqual(p['press']['successes'],3)
        self.assertFalse(p['minimum_900_normal_population_met'])
        self.assertFalse(p['publication_authorized'])

    def test_position_tie_withholds_comparison_assignment(self):
        p=position_summary({'Center Back':rational(Fraction(5)), 'Center Midfield':rational(Fraction(5))})
        self.assertEqual(p['most_played_supported_groups'],['CB','CM'])
        self.assertIsNone(p['comparison_group'])


if __name__=='__main__':unittest.main()
