"""Synthetic regression cases for support decisions, denominator scope and policy."""
from copy import deepcopy
from fractions import Fraction
import unittest

from src.reconciled_source import identity_agrees, pressure_chronology
from src.supported_sample_ratings import ATTRIBUTES, aggregate, eligibility, freeze_reference, pair, score


def identity(pid=1, group='MID'):
    return dict(player_id=str(pid), id=f'{pid}:2015/2016', name=f'Example {pid}', comparison_position=group)


def appearance(pid=1, mid=10, minutes=900, count=2, attempts=40, excluded=()):
    metrics={}
    for a in ATTRIBUTES:
        prefix=f'{pid}-{mid}-{a}'
        metrics[a]=dict(included=a not in excluded,reasons=['UNRESOLVED_PARTICIPATION'] if a in excluded else [],
            numerator_ids=[f'{prefix}-{i}' for i in range(count)],
            denominator_ids=[f'{prefix}-{i}' for i in range(attempts)] if a=='press_resistance' else None)
    return dict(player_id=pid,match_id=mid,seconds=None if minutes is None else pair(Fraction(minutes)*60),
        competition='La Liga',metrics=metrics)


def event(index, name, *, player=1, **extra):
    return dict(id=str(index),index=index,period=1,timestamp=f'00:{index:02}:00.000',
        team={'id':10},player={'id':player},type={'name':name},**extra)


class SupportedSampleTests(unittest.TestCase):
    def test_unresolved_match_does_not_disqualify_verified_sample(self):
        good=appearance(); unknown=appearance(mid=11,minutes=None,excluded=set(ATTRIBUTES)-{'press_resistance'})
        p=aggregate([identity()],[good,unknown])[0]
        self.assertTrue(p['eligible'])
        self.assertEqual(p['supported_match_ids'],[10])
        self.assertEqual(p['attributes']['tackles']['numerator_match_ids'],[10])
        self.assertEqual(p['attributes']['press_resistance']['numerator_match_ids'],[10,11])
        self.assertEqual(p['attributes']['press_resistance']['attempts'],80)

    def test_per90_exclusion_removes_both_count_and_minutes(self):
        p=aggregate([identity()],[appearance(),appearance(mid=11,minutes=100,count=20,excluded=['recoveries'])])[0]
        m=p['attributes']['recoveries']
        self.assertEqual(m['numerator'],2)
        self.assertEqual(m['supported_minutes'],pair(Fraction(900)))
        self.assertEqual(m['exact_value'],pair(Fraction(1,5)))
        self.assertEqual(m['numerator_match_ids'],m['denominator_match_ids'])

    def test_each_per90_metric_needs_900_minutes(self):
        p=aggregate([identity()],[appearance(minutes=899),appearance(mid=11,minutes=1,excluded=['recoveries'])])[0]
        self.assertFalse(p['eligible'])
        self.assertIn('recoveries:BELOW_900_SUPPORTED_METRIC_MINUTES',p['exclusion_reasons'])

    def test_pressure_40_boundary(self):
        self.assertTrue(aggregate([identity()],[appearance(attempts=40)])[0]['eligible'])
        self.assertFalse(aggregate([identity()],[appearance(attempts=39)])[0]['eligible'])

    def test_pressure_conflict_excludes_whole_ratio(self):
        p=aggregate([identity()],[appearance(),appearance(mid=11,count=4,attempts=4,excluded=['press_resistance'])])[0]
        m=p['attributes']['press_resistance']
        self.assertEqual((m['numerator'],m['attempts']),(2,40))
        self.assertEqual(m['excluded_appearances'][0]['match_id'],11)

    def test_duplicate_fixture_and_duplicate_event_fail(self):
        row=appearance()
        with self.assertRaisesRegex(ValueError,'duplicate'):aggregate([identity()],[row,row])
        second=appearance(mid=11);second['metrics']['tackles']['numerator_ids']=row['metrics']['tackles']['numerator_ids']
        with self.assertRaisesRegex(ValueError,'duplicate'):aggregate([identity()],[row,second])

    def test_pressure_success_must_belong_to_attempts(self):
        row=appearance();row['metrics']['press_resistance']['denominator_ids']=[]
        with self.assertRaisesRegex(ValueError,'pressure'):aggregate([identity()],[row])

    def test_bundesliga_remains_outside_ranking_cohort(self):
        row=appearance();row['competition']='1. Bundesliga'
        self.assertIn('BUNDESLIGA_CONTRIBUTION',aggregate([identity()],[row])[0]['exclusion_reasons'])

    def test_alias_is_bound_to_exact_provider_identity(self):
        self.assertTrue(identity_agrees(3054,'Fernando Luiz Rosa','Fernando Luiz Roza'))
        self.assertFalse(identity_agrees(3055,'Fernando Luiz Rosa','Fernando Luiz Roza'))
        self.assertFalse(identity_agrees(3054,'Fernando Luiz Rosa','Another Person'))

    def test_permanent_exit_and_return_withhold_pressure(self):
        events=[event(1,'Starting XI',tactics={'lineup':[{'player':{'id':1}}]}),
            event(2,'Player Off',player_off={'permanent':True}),event(3,'Player On'),event(4,'Pass')]
        self.assertIn('CONFLICTING_RETURN',pressure_chronology(1,10,events))

    def test_second_yellow_ends_active_state(self):
        events=[event(1,'Starting XI',tactics={'lineup':[{'player':{'id':1}}]}),
            event(2,'Foul Committed',foul_committed={'card':{'name':'Second Yellow'}}),event(3,'Pass')]
        self.assertIn('ACTIVITY_OUTSIDE_SUPPORTED_STATE',pressure_chronology(1,10,events))
        self.assertEqual(pressure_chronology(1,10,events[:2]),[])

    def test_pressure_does_not_require_final_video_clock(self):
        self.assertEqual(pressure_chronology(1,10,[event(1,'Starting XI',tactics={'lineup':[{'player':{'id':1}}]}),event(2,'Pass')]),[])

    def test_unrelated_receipt_clock_does_not_discard_supported_pressure(self):
        events=[event(1,'Starting XI',tactics={'lineup':[{'player':{'id':1}}]}),
            event(2,'Pass',under_pressure=True),event(3,'Ball Receipt*')]
        events[-1]['timestamp']='00:00:02.094'
        self.assertEqual(pressure_chronology(1,10,events),[])

    def test_pressure_attempt_clock_disagreement_still_withholds(self):
        events=[event(1,'Starting XI',tactics={'lineup':[{'player':{'id':1}}]}),
            event(2,'Pass',under_pressure=True),event(3,'Pass',under_pressure=True)]
        events[-1]['timestamp']='00:00:02.094'
        self.assertIn('SOURCE_CLOCK_INDEX_DISAGREEMENT',pressure_chronology(1,10,events))

    def test_unverified_off_field_card_is_not_ignored(self):
        events=[event(1,'Starting XI',tactics={'lineup':[{'player':{'id':1}}]}),event(2,'Substitution',substitution={'replacement':{'id':2}}),
            event(3,'Bad Behaviour',bad_behaviour={'card':{'name':'Red Card'}})]
        self.assertIn('EXIT_WHILE_INACTIVE',pressure_chronology(1,10,events))
        self.assertEqual(pressure_chronology(1,10,events,{'3'}),[])

    def test_same_eligible_cohort_for_all_attributes_and_frozen_scoring(self):
        identities=[identity(i,g) for g,base in [('MID',0),('CB',10)] for i in range(base+1,base+4)]
        rows=[appearance(int(p['player_id']),count=i+1) for i,p in enumerate(identities)]
        measured=aggregate(identities,rows);reference=freeze_reference(measured,'a'*64)
        for group,pools in reference['pools'].items():
            self.assertEqual(len({tuple(p['member_ids']) for p in pools.values()}),1)
        frozen=deepcopy(reference);scored=score(measured,reference)
        self.assertEqual(reference,frozen)
        self.assertTrue(all(1<=p['overall']<=99 for p in scored))
        reference['pools']['MID']['tackles']['mean']+=1
        with self.assertRaisesRegex(ValueError,'changed reference'):score(measured,reference)

    def test_low_sample_does_not_fit_reference(self):
        identities=[identity(i,g) for g,base in [('MID',0),('CB',10)] for i in range(base+1,base+4)]
        rows=[appearance(int(p['player_id']),count=i+1) for i,p in enumerate(identities)]
        measured=aggregate(identities,rows);baseline=freeze_reference(measured,'a'*64)
        low=aggregate([identity(99)],[appearance(99,minutes=899,count=30)])[0]
        self.assertEqual(freeze_reference(measured+[low],'a'*64),baseline)
        scored=score(measured+[low],baseline)
        self.assertFalse(scored[-1]['eligible'])
        self.assertIsNotNone(scored[-1]['overall'])


if __name__=='__main__':unittest.main()
