"""Synthetic-only readiness contract; does not grant real score admission."""
import copy
import json
from pathlib import Path
import unittest

from scripts.make_synthetic_five_attribute_fixture import fixture
from src.five_attribute_presentation import validate_delivery
from src.rating_delivery import validate_delivery as original_delivery
from src.provisional_delivery import validate_delivery as provisional_delivery


class FiveAttributePresentationTests(unittest.TestCase):
    def reject(self,change):
        data=fixture();change(data)
        with self.assertRaises(ValueError):validate_delivery(data)

    def test_fixture_contract_and_no_mutation(self):
        data=fixture();before=copy.deepcopy(data)
        self.assertEqual(validate_delivery(data),data);self.assertEqual(data,before)
        self.assertEqual(len(data['players']),4)

    def test_generated_frontend_fixture_matches(self):
        self.assertEqual(fixture(),json.loads(Path('frontend/src/fixtures/syntheticFiveAttributes.json').read_text(encoding='utf8')))

    def test_non_synthetic_and_authorization_flags_rejected(self):
        for key,value in [('classification','verified'),('publication_authorized',True),('numeric_real_delivery_enabled',True)]:
            self.reject(lambda d:d.update({key:value}))

    def test_real_identity_cannot_claim_synthetic_classification(self):
        self.reject(lambda d:d['players'][0].update(player_id='5574',id='5574:2015/2016',name='Toni Kroos'))

    def test_numeric_bounds_and_nonfinite_fail_closed(self):
        for key,values in [('rating',[0,100,-1,True,float('nan'),float('inf')]),('percentile',[-1,101,True,float('inf')])]:
            for v in values:self.reject(lambda d:d['players'][0]['attributes']['tackles'].update({key:v}))

    def test_reference_content_fingerprint_and_position_binding(self):
        self.reject(lambda d:d['reference']['positions']['MID']['tackles'].update(mean=999))
        self.reject(lambda d:d['reference'].update(fingerprint='0'*64))
        self.reject(lambda d:d['players'][0]['attributes']['tackles']['normalization'].update(comparison_position='CB'))
        self.reject(lambda d:d['players'][0]['attributes']['tackles']['normalization'].update(pool_fingerprint='0'*64))

    def test_proxy_label_cannot_be_true_line_breaks(self):
        self.reject(lambda d:d['players'][0]['attributes']['line_breaking_passes'].update(label='Verified line breaks'))
        self.reject(lambda d:d['players'][0]['attributes']['line_breaking_passes'].update(measurement_kind='true_line_break'))

    def test_units_raw_arithmetic_and_denominator_alignment(self):
        self.reject(lambda d:d['players'][0]['attributes']['tackles']['observation'].update(unit='percent'))
        self.reject(lambda d:d['players'][0]['attributes']['tackles']['observation'].update(denominator=0))
        self.reject(lambda d:d['players'][0]['attributes']['press_resistance']['observation'].update(value=99))
        self.reject(lambda d:d['players'][0]['attributes']['recoveries']['observation'].update(supported_minutes={'numerator':999,'denominator':1}))

    def test_sub40_press_retained_with_sample_and_warning(self):
        d=fixture();m=d['players'][2]['attributes']['press_resistance']
        self.assertEqual(m['observation']['action_sample_size'],12);self.assertTrue(m['limited_data']);self.assertIsNotNone(m['rating'])
        self.reject(lambda d:d['players'][2]['attributes']['press_resistance'].update(limited_data=False))

    def test_bundesliga_partial_flags_required(self):
        self.reject(lambda d:d['players'][2].update(limited_data=False,partial_season=False))
        self.reject(lambda d:d['players'][2]['attributes']['tackles'].update(partial_season=False))

    def test_transfer_one_identity_nonoverlap_and_dedup(self):
        d=fixture();self.assertEqual(len(d['players'][0]['clubs']),2)
        self.reject(lambda d:d['players'].append(copy.deepcopy(d['players'][0])))
        self.reject(lambda d:d['players'][0]['clubs'][1]['match_ids'].append(d['players'][0]['clubs'][0]['match_ids'][0]))

    def test_missing_attribute_never_imputed(self):
        d=fixture();m=d['players'][3]['attributes']['line_breaking_passes']
        self.assertIsNone(m['observation']);self.assertIsNone(m['rating']);self.assertTrue(m['missingness'])
        self.reject(lambda d:d['players'][3]['attributes']['line_breaking_passes'].update(rating=65))
        self.reject(lambda d:d['players'][3]['attributes']['line_breaking_passes'].update(missingness=[]))

    def test_provenance_and_fixture_exclusions(self):
        self.reject(lambda d:d['players'][0]['attributes']['tackles'].update(provenance_ids=['synthetic:unbound']))
        self.reject(lambda d:d['players'][0]['attributes']['tackles']['observation'].update(match_ids=['synthetic:unknown-fixture']))
        self.reject(lambda d:d['players'][0]['attributes']['tackles'].update(exclusions=[{'match_id':d['players'][0]['clubs'][0]['match_ids'][0],'reasons':['Unsupported']}]))

    def test_no_ovr_archetype_or_signoff_and_legacy_contracts_unchanged(self):
        for key in ('overall','ovr','archetype','tier','approval'):
            self.reject(lambda d:d['players'][0].update({key:99}))
        for validator in (original_delivery,provisional_delivery):
            with self.assertRaises(ValueError):validator(fixture())



if __name__=='__main__':unittest.main()
