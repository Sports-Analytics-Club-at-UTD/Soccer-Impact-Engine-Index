"""Private integration contracts; synthetic fixtures never promote source trust."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.private_five_attribute import (ATTRIBUTES,PRESS_COUNTS,aggregate,digest,
    freeze_reference,score_players,validate_reference)
from src.source_reconstruction import rational
from src.rating_delivery import validate_delivery
from scripts.score_private_five_attributes import prepare_facts,build


def case(pid=1, mid=1, minutes=900, successes=10, group='MID', comp='La Liga', pressure=40, retained=20):
    seconds=rational(Fraction(minutes*60))
    metrics={}
    for a in ATTRIBUTES:
        ids=[f'{pid}:{mid}:{a}:{i}' for i in range(successes)]
        if a=='press_resistance':
            den=[f'{pid}:{mid}:press:{i}' for i in range(pressure)]
            metrics[a]=dict(counts=dict(zip(PRESS_COUNTS,[pressure,retained,0,0])),numerator_ids=den[:retained],
                denominator_ids=den,seconds=seconds,supported=True,reasons=[])
        else:metrics[a]=dict(counts={'count':successes},numerator_ids=ids,denominator_ids=None,
            seconds=seconds,supported=True,reasons=[])
    p=dict(player_id=pid,season_name='2015/2016',name=f'Player {pid}',comparison_group=group,
        dominant_fine_groups=['CM' if group=='MID' else group],position_seconds={},observed_match_ids=[mid],measured_passes=100)
    r=dict(player_id=pid,season_name='2015/2016',match_id=mid,team='Club',competition_name=comp,seconds=seconds,metrics=metrics)
    return p,r


def population():
    pairs=[case(pid=i,successes=i*10,retained=i*10) for i in (1,2,3)]
    return aggregate([p for p,r in pairs],[r for p,r in pairs])


class PrivateFiveAttributeTests(unittest.TestCase):
    def baseline(self,ps=None):return freeze_reference(ps or population(),input_binding='a'*64)

    def test_five_distinct_reference_memberships(self):
        p1,r1=case();p2,r2=case(pid=2,successes=20);p3,r3=case(pid=3,pressure=39,retained=10)
        r3['metrics']['recoveries'].update(supported=False,reasons=['UNALIGNED'])
        ps=aggregate([p1,p2,p3],[r1,r2,r3]);b=self.baseline(ps)
        self.assertEqual(b['pools']['MID']['tackles']['member_ids'],[1,2,3])
        self.assertEqual(b['pools']['MID']['recoveries']['member_ids'],[1,2])
        self.assertEqual(b['pools']['MID']['press_resistance']['member_ids'],[1,2])

    def test_transfer_sums_counts_seconds_and_weighted_press(self):
        p,r=case(minutes=450,pressure=10,retained=10)
        _,r2=case(mid=2,minutes=450,successes=30,pressure=30,retained=0)
        p['observed_match_ids']=[1,2];r2['team']='Second Club'
        result=aggregate([p],[r2,r])[0]
        self.assertEqual(result['attributes']['tackles']['value'],4)
        self.assertEqual(result['attributes']['press_resistance']['value'],25)
        self.assertEqual(len(result['contexts']),2)
        self.assertEqual(result['attributes']['press_resistance']['attempts'],40)

    def test_sample_sd_formula_separate_mid_cb(self):
        pairs=[case(pid=i,successes=i*10,retained=i*10,group='MID' if i<3 else 'CB') for i in (1,2,3,4)]
        ps=aggregate([p for p,r in pairs],[r for p,r in pairs]);b=self.baseline(ps)
        self.assertAlmostEqual(b['pools']['MID']['tackles']['sample_sd'],2**-.5)
        self.assertEqual(b['pools']['CB']['tackles']['member_ids'],[3,4])
        scores=score_players(ps,b)
        self.assertAlmostEqual(scores[0]['attributes']['tackles']['experimental_rating'],65-10/2**.5)
        self.assertAlmostEqual(scores[2]['attributes']['tackles']['experimental_rating'],65-10/2**.5)

    def test_reference_900_and_press_40_boundaries(self):
        pairs=[case(pid=1,minutes=899),case(pid=2,pressure=39),case(pid=3,pressure=40)]
        ps=aggregate([p for p,r in pairs],[r for p,r in pairs]);b=self.baseline(ps)
        self.assertEqual(b['pools']['MID']['tackles']['member_ids'],[2,3])
        self.assertEqual(b['pools']['MID']['press_resistance']['member_ids'],[3])
        scored=score_players(ps,b)
        self.assertEqual(scored[0]['attributes']['tackles']['score_reason'],'BELOW_900_VERIFIED_MINUTES')
        self.assertEqual(scored[1]['attributes']['press_resistance']['score_reason'],'INSUFFICIENT_REFERENCE_MEMBERS')

    def test_bundesliga_provisional_sub40_and_no_reference_contamination(self):
        base=population();p,r=case(pid=4,minutes=30,comp='1. Bundesliga',pressure=1,retained=1)
        ps=base+aggregate([p],[r]);b=self.baseline(ps)
        self.assertEqual(b,self.baseline(base))
        s=score_players(ps,b)[-1]
        self.assertTrue(s['limited_data'] and s['partial_season'])
        self.assertIsNotNone(s['attributes']['press_resistance']['experimental_rating'])
        self.assertIn('BELOW_40_PRESS_ACTIONS / LIMITED DATA',s['attributes']['press_resistance']['warnings'])
        self.assertEqual(s['attributes']['tackles']['score_status'],'PROVISIONAL_LIMITED_DATA')

    def test_cross_league_bundesliga_transfer_excluded_from_all_baselines(self):
        p,r=case();_,r2=case(mid=2,comp='1. Bundesliga');p['observed_match_ids']=[1,2]
        ps=aggregate([p],[r,r2]);b=self.baseline(ps)
        self.assertTrue(all(b['pools']['MID'][a]['n']==0 for a in ATTRIBUTES))

    def test_zero_and_missing_counts_not_conflated(self):
        p,r=case(successes=0,pressure=0,retained=0)
        r['metrics']['recoveries'].update(supported=False,reasons=['UNKNOWN_EXPOSURE'])
        ps=aggregate([p],[r])[0]
        self.assertEqual(ps['attributes']['tackles']['value'],0)
        self.assertIsNone(ps['attributes']['recoveries']['value'])
        self.assertIsNone(ps['attributes']['recoveries']['raw_counts'])
        self.assertIsNone(ps['attributes']['press_resistance']['value'])

    def test_press_ratio_without_minutes_retained_but_never_reference(self):
        p,r=case(comp='1. Bundesliga');r['seconds']=None
        for a,m in r['metrics'].items():
            m['seconds']=None
            if a!='press_resistance':m.update(supported=False,reasons=['UNKNOWN_EXPOSURE'])
        ps=aggregate([p],[r]);self.assertEqual(ps[0]['attributes']['press_resistance']['value'],50)
        self.assertFalse(ps[0]['attributes']['press_resistance']['experimental_reference_candidate'])
        self.assertIsNone(ps[0]['attributes']['tackles']['value'])

    def test_subset_denominators_and_reference_failure(self):
        p,r=case();_,r2=case(mid=2);p['observed_match_ids']=[1,2]
        r2['metrics']['tackles'].update(supported=False,reasons=['EVENT_OUTSIDE_EXPOSURE'])
        ps=aggregate([p],[r,r2])[0]
        self.assertEqual(ps['attributes']['tackles']['supported_minutes'],rational(Fraction(900)))
        self.assertEqual(ps['attributes']['tackles']['numerator_match_ids'],[1])
        self.assertFalse(ps['attributes']['tackles']['experimental_reference_candidate'])
        self.assertTrue(ps['attributes']['interceptions']['experimental_reference_candidate'])

    def test_zero_variance_singleton_and_no_reference_fail_closed(self):
        p,r=case();ps=aggregate([p],[r])
        self.assertEqual(score_players(ps,self.baseline(ps))[0]['attributes']['tackles']['score_reason'],'INSUFFICIENT_REFERENCE_MEMBERS')
        p2,r2=case(pid=2);ps+=aggregate([p2],[r2])
        self.assertEqual(score_players(ps,self.baseline(ps))[0]['attributes']['tackles']['score_reason'],'ZERO_REFERENCE_VARIANCE')

    def test_unsupported_position_never_scores(self):
        p,r=case(pid=4,group='FB',comp='1. Bundesliga')
        s=score_players(aggregate([p],[r]),self.baseline())[0]
        self.assertTrue(all(m['score_reason']=='UNSUPPORTED_POSITION_GROUP' for m in s['attributes'].values()))

    def test_exact_ties_and_external_frozen_percentiles(self):
        pairs=[case(pid=i,successes=x,retained=10) for i,x in enumerate([10,10,30,40],1)]
        ps=aggregate([p for p,r in pairs],[r for p,r in pairs]);b=self.baseline(ps)
        s=score_players(ps,b)
        self.assertEqual(s[0]['attributes']['tackles']['percentile'],37.5)
        p,r=case(pid=5,successes=20)
        self.assertEqual(score_players(aggregate([p],[r]),b)[0]['attributes']['tackles']['percentile'],50)

    def test_frozen_reference_not_refit_for_recipients_and_clipping(self):
        b=self.baseline();before=copy.deepcopy(b)
        p,r=case(pid=5,successes=1000)
        s=score_players(aggregate([p],[r]),b)[0]
        self.assertEqual(s['attributes']['tackles']['experimental_rating'],99)
        self.assertEqual(b,before)

    def test_frozen_hash_and_statistics_tamper_rejected(self):
        b=self.baseline();b['pools']['MID']['tackles']['mean']+=1
        with self.assertRaises(ValueError):validate_reference(b)
        b['sha256']=digest({k:v for k,v in b.items() if k!='sha256'})
        with self.assertRaises(ValueError):validate_reference(b)

    def test_duplicate_player_and_transfer_fixture_rejected(self):
        p,r=case()
        with self.assertRaises(ValueError):aggregate([p,p],[r])
        with self.assertRaises(ValueError):aggregate([p],[r,r|{'team':'Other'}])

    def test_unknown_fixture_or_missing_appearance_rejected(self):
        p,r=case();p['observed_match_ids']=[1,2]
        with self.assertRaises(ValueError):aggregate([p],[r])
        r['match_id']=3
        with self.assertRaises(ValueError):aggregate([p],[r])

    def test_uuid_success_subset_and_duplicate_attempt_rejected(self):
        p,r=case();r['metrics']['press_resistance']['numerator_ids'][0]='foreign'
        with self.assertRaises(ValueError):aggregate([p],[r])
        p,r=case();_,r2=case(mid=2);p['observed_match_ids']=[1,2]
        r2['metrics']['press_resistance']=copy.deepcopy(r['metrics']['press_resistance'])
        with self.assertRaises(ValueError):aggregate([p],[r,r2])

    def test_determinism_conservation_and_no_ovr_or_delivery_admission(self):
        pairs=[case(pid=i,successes=i*10,retained=i*10) for i in (1,2,3)]
        ps=aggregate([p for p,r in pairs],[r for p,r in pairs])
        self.assertEqual(ps,aggregate([p for p,r in reversed(pairs)],[r for p,r in reversed(pairs)]))
        self.assertEqual(sum(p['attributes']['tackles']['numerator'] for p in ps),60)
        b=self.baseline(ps);s=score_players(ps,b)
        self.assertEqual(s,score_players(list(reversed(ps)),b))
        self.assertTrue(all('ovr' not in p and not p['publication_authorized'] and not p['reference_member'] for p in s))
        with self.assertRaises(ValueError):validate_delivery({'schema_version':'private-five-attribute-player-season/v1','players':s})

    def test_existing_output_refuses_before_input_access(self):
        with patch('scripts.score_private_five_attributes.Path.exists',return_value=True),patch('scripts.score_private_five_attributes.inputs') as source:
            with self.assertRaises(ValueError):build('existing')
            source.assert_not_called()

    def test_mismatched_metric_minutes_and_zero_denominator_fail_closed(self):
        p,r=case();r['metrics']['tackles']['seconds']=rational(Fraction(1))
        with self.assertRaisesRegex(ValueError,'exposure mismatch'):aggregate([p],[r])
        p,r=case();r['seconds']=rational(Fraction(0))
        for m in r['metrics'].values():m['seconds']=r['seconds']
        with self.assertRaisesRegex(ValueError,'positive verified'):aggregate([p],[r])

    def test_scoring_rejects_raw_value_denominator_contradiction(self):
        ps=population();b=self.baseline(ps)
        ps[0]['attributes']['tackles']['numerator']=1
        with self.assertRaisesRegex(ValueError,'contradicts scoring value'):score_players(ps,b)
        ps=population();ps[0]['limited_data']=True
        ps[0]['attributes']['tackles']['supported_minutes']=rational(Fraction(0))
        with self.assertRaisesRegex(ValueError,'zero scoring denominator'):score_players(ps,b)

    def test_source_adapter_preserves_ratio_but_excludes_pending_fixture(self):
        def source(mid=1):
            p,r=case(mid=mid)
            obs=dict(player_id=1,match_id=mid,name='Player',season_name='2015/2016',team='Club',
                competition_name='La Liga',seconds=r['seconds'],prog_passes=10,reasons=[])
            components={}
            for a in ('tackles','interceptions','recoveries'):
                components[a]=dict(count=10,event_ids=r['metrics'][a]['numerator_ids'],status='SOURCE_VERIFIED_CANDIDATE_MEASUREMENT',reasons=[])
            for n in PRESS_COUNTS:
                is_attempt=n.endswith('attempts');ids=r['metrics']['press_resistance']['denominator_ids' if is_attempt else 'numerator_ids'] if 'pass' in n else []
                components[n]=dict(count=len(ids),event_ids=ids,reasons=['UNRESOLVED_PARTICIPATION'])
            components['progressive_passes']=dict(count=10,event_ids=r['metrics']['progressive_passing']['numerator_ids'])
            raw=dict(player_id=1,team_id=7,match_id=mid,season_name='2015/2016',team='Club',competition_name='La Liga',components=components)
            return obs,raw
        obs,m=source();f=prepare_facts([obs],[m])[0]
        self.assertTrue(f['metrics']['press_resistance']['supported'])
        self.assertEqual(f['metrics']['press_resistance']['counts'][PRESS_COUNTS[0]],40)
        obs,m=source(3879594);obs['reasons']=['PENDING_DELIVERED_FIXTURE_SCOPE']
        f=prepare_facts([obs],[m])[0]
        self.assertTrue(all(not metric['supported'] for metric in f['metrics'].values()))

    def test_source_adapter_fixture_and_team_disagreements_fail_closed(self):
        obs=dict(player_id=1,match_id=1,season_name='2015/2016',team='Club',competition_name='La Liga')
        m=dict(player_id=1,match_id=2)
        with self.assertRaisesRegex(ValueError,'fixture mismatch'):prepare_facts([obs],[m])
        m=dict(player_id=1,match_id=1,season_name='2015/2016',team='Other',competition_name='La Liga')
        with self.assertRaisesRegex(ValueError,'disagreement'):prepare_facts([obs],[m])

    def test_four_league_sub40_recipient_keeps_private_projection(self):
        p,r=case(pid=5,pressure=39,retained=10)
        ps=aggregate([p],[r]);b=self.baseline()
        self.assertFalse(ps[0]['attributes']['press_resistance']['experimental_reference_candidate'])
        scored=score_players(ps,b)[0]['attributes']['press_resistance']
        self.assertIsNotNone(scored['experimental_rating'])
        self.assertEqual(scored['score_status'],'PROVISIONAL_LIMITED_DATA')
        self.assertEqual(scored['attempts'],39)


if __name__=='__main__':unittest.main()
