"""Source-only checks with invented inputs; copied assertions retain independent expectations."""
import copy
import hashlib
import json
import unittest
from synthetic_provisional import synthetic
from src.provisional_delivery import ATTRIBUTES, DEFINITIONS, LEAGUES, SCHEMA, provisional_admission, validate_delivery

def baseline():
    members=[dict(player_id=str(pid),competition_name=LEAGUES[i%4],role_group='MID' if pid<204 else 'CB') for i,pid in enumerate(range(201,207))]
    b=dict(id='invented-frozen-reference',frozen=True,competitions=LEAGUES,definitions_id=DEFINITIONS,members=members,
        statistics={g:{n:dict(mean=2,sample_sd=1,n=3,member_ids=[m['player_id'] for m in members if m['role_group']==g]) for n in ATTRIBUTES[:4]} for g in ['MID','CB']})
    return sign(b)


def sign(b):
    b.pop('sha256',None)
    b['sha256']=hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return b


class ProvisionalDeliveryTests(unittest.TestCase):
    def test_synthetic_contract_sub40_zero_observation_and_na(self):
        d=synthetic();self.assertEqual(validate_delivery(d),d)
        p=d['players'][0]
        self.assertEqual(p['attributes']['tackles']['observation']['value'],0)
        self.assertEqual(p['attributes']['press_resistance']['observation']['value'],50)
        self.assertIsNone(p['attributes']['line_breaking_passes']['observation'])


    def test_rating_percentile_and_line_breaking_leakage_rejected(self):
        for field in ['rating','percentile']:
            d=synthetic();d['players'][0]['attributes']['tackles'][field]=80
            with self.assertRaisesRegex(ValueError,'forbidden'):validate_delivery(d)
        d=synthetic();d['players'][0]['attributes']['line_breaking_passes']['observation']=d['players'][0]['attributes']['tackles']['observation']
        with self.assertRaisesRegex(ValueError,'line breaking'):validate_delivery(d)
        d=synthetic();d['numeric_ratings_enabled']=True
        with self.assertRaises(ValueError):validate_delivery(d)


    def test_bad_scope_capped_denominator_and_duplicate_card_reject(self):
        for mutate in [lambda p:p['attributes']['tackles']['observation'].update(match_ids=['12']),
            lambda p:p['attributes']['tackles']['observation'].update(minutes=dict(numerator=90,denominator=1)),
            lambda p:p['attributes']['press_resistance']['observation'].update(match_ids=['11'])]:
            d=synthetic();mutate(d['players'][0])
            with self.assertRaises(ValueError):validate_delivery(d)
        d=synthetic();d['players'].append(copy.deepcopy(d['players'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate canonical'):validate_delivery(d)


    def test_40_boundary_zero_attempts_and_wrong_group_reject(self):
        for attempts in [1,39,40]:
            d=synthetic();o=d['players'][0]['attributes']['press_resistance']['observation']
            o.update(attempts=attempts,pass_attempts=attempts,successes=0,pass_successes=0,value=0,at_least_40=attempts>=40)
            d['players'][0]['bundesliga_sample'].update(press_attempts=attempts,press_successes=0)
            validate_delivery(d)
        d=synthetic();d['players'][0]['attributes']['press_resistance']['observation']['attempts']=0
        with self.assertRaises(ValueError):validate_delivery(d)
        d=synthetic();d['players'][0]['comparison_group']='MID'
        with self.assertRaisesRegex(ValueError,'group mismatch'):validate_delivery(d)


    def test_frozen_admission_does_not_score_or_mutate_reference(self):
        d=synthetic();p=d['players'][0];b=baseline();before=copy.deepcopy(b)
        admission=provisional_admission(p,b)
        self.assertEqual(b,before);self.assertEqual(len(admission['admissible_attributes']),4)
        self.assertFalse(admission['reference_member']);self.assertFalse(admission['numeric_rating_authorized'])
        self.assertNotIn('rating',admission)
        for positions in [{'FB':dict(numerator=10,denominator=1)},{}]:
            p=synthetic()['players'][0];p.update(position_minutes=positions,comparison_group=None,supported_minutes=dict(numerator=10 if positions else 0,denominator=1))
            p.update(bundesliga_candidate=False)
            p['bundesliga_sample'].update(position_minutes=positions,comparison_group=None,supported_minutes=copy.deepcopy(p['supported_minutes']))
            if not positions:
                for n in ATTRIBUTES[:3]:p['attributes'][n]['observation']=None
            self.assertEqual(provisional_admission(p,b)['admissible_attributes'],[])


    def test_baseline_bundesliga_tampering_and_duplicate_influence_reject(self):
        for change in [lambda b:b['members'][0].update(competition_name='1. Bundesliga'),
                       lambda b:b['members'].append(copy.deepcopy(b['members'][0]))]:
            b=baseline();change(b);sign(b)
            with self.assertRaises(ValueError):provisional_admission(synthetic()['players'][0],b)
        b=baseline();b['statistics']['CB']['tackles']['mean']=42
        with self.assertRaisesRegex(ValueError,'fingerprint'):provisional_admission(synthetic()['players'][0],b)


    def test_per_attribute_frozen_reference_subsets(self):
        b=baseline();s=b['statistics']['CB']['press_resistance'];s.update(n=2,member_ids=s['member_ids'][:2]);sign(b)
        self.assertEqual(len(provisional_admission(synthetic()['players'][0],b)['admissible_attributes']),4)
