"""Missing player-season integration contracts, using synthetic facts only."""
import ast
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.fifth_attribute import combine_observations, private_preview
from src.metrics import progressive_passes as joseph
from src.passing import calibrate_difficulty, _prepare, _apply_reference
from src.rating_delivery import validate_delivery
from scripts.prepare_fifth_attribute import project, build, read_bound


def row(pid=1, mid=1, **kw):
    return dict(player_id=pid,season_name='2015/2016',name='Player',team='Club',
        competition_name='La Liga',match_id=mid,seconds={'numerator':54000,'denominator':1},
        position_seconds={'Center Midfield':{'numerator':54000,'denominator':1}},
        reasons=[],prog_attempts=20,prog_passes=10,third_cross=5,measured_passes=100,value_sum=100.0)|kw


def event(uid='a', **kw):
    return dict(id=uid,match_id=1,competition_name='La Liga',season_name='2015/2016',
        type='Pass',player='Player',team='Club',player_id=1,location=[30,40],
        pass_end_location=[60,40],pass_outcome=None,pass_type=None,pass_length=30)|kw


class FifthAttributeTests(unittest.TestCase):

    def test_transfer_sums_raw_counts_not_rates(self):
        p=combine_observations([row(),row(mid=2,team='Second',prog_passes=20)])[0]
        self.assertEqual(p['prog_passes'],30)
        self.assertEqual(p['minutes'],1800)
        self.assertEqual(p['prog_passes_p90'],1.5)
        self.assertEqual(len(p['clubs']),2)
        self.assertTrue(p['experimental_reference_candidate'])

    def test_duplicate_fixture_across_clubs_rejected(self):
        with self.assertRaises(ValueError):combine_observations([row(),row(team='Other')])

    def test_missing_not_zero_supported_zero_and_no_attempt_percentage(self):
        p=combine_observations([row(reasons=['MISSING_GEOMETRY'])])[0]
        self.assertIsNone(p['prog_passes'])
        self.assertIsNone(p['prog_passes_p90'])
        p=combine_observations([row(prog_attempts=0,prog_passes=0,third_cross=0,measured_passes=0,value_sum=0.0)])[0]
        self.assertEqual(p['prog_passes_p90'],0)
        self.assertIsNone(p['prog_completion_pct'])

    def test_subset_exposure_retains_missing_fixture(self):
        p=combine_observations([row(),row(mid=2,reasons=['UNSUPPORTED_EXPOSURE'])])[0]
        self.assertEqual(p['minutes'],900)
        self.assertEqual(p['prog_passes'],10)
        self.assertEqual(p['supported_match_ids'],[1])
        self.assertFalse(p['experimental_reference_candidate'])
        self.assertEqual(p['measurement_status'],'SUPPORTED_SUBSET')

    def test_position_dominance_before_mid_mapping_and_ties(self):
        pos={p:{'numerator':s,'denominator':1} for p,s in [('Center Midfield',15000),('Center Defensive Midfield',15000),('Center Back',24000)]}
        p=combine_observations([row(position_seconds=pos)])[0]
        self.assertEqual(p['comparison_group'],'CB')
        pos['Center Back']['numerator']=15000
        self.assertIsNone(combine_observations([row(position_seconds=pos)])[0]['comparison_group'])

    def test_bundesliga_and_cross_league_transfers_never_reference(self):
        ps=combine_observations([row(),row(mid=2,competition_name='1. Bundesliga',value_sum=None)])
        self.assertFalse(ps[0]['experimental_reference_candidate'])
        self.assertTrue(ps[0]['limited_data'])
        self.assertIsNone(ps[0]['pass_value_p90'])

    def test_pending_fixture_and_under_900_never_reference(self):
        self.assertFalse(combine_observations([row(mid=3879594)])[0]['experimental_reference_candidate'])
        self.assertFalse(combine_observations([row(seconds={'numerator':53999,'denominator':1})])[0]['experimental_reference_candidate'])

    def test_separate_mid_cb_sample_sd_and_exact_existing_formula(self):
        cb={'Center Back':{'numerator':54000,'denominator':1}}
        ps=combine_observations([row(),row(pid=2,prog_passes=20),row(pid=3,position_seconds=cb),row(pid=4,position_seconds=cb,prog_passes=20)])
        p=private_preview(ps)
        self.assertAlmostEqual(p['pools']['MID']['sample_std_dev'],2**-.5)
        self.assertEqual(p['pools']['MID']['n'],2)
        self.assertEqual(p['pools']['CB']['n'],2)
        self.assertAlmostEqual(p['players'][0]['private_experimental_rating'],65-10/2**.5)
        self.assertEqual(p,private_preview(list(reversed(ps))))
        with self.assertRaises(ValueError):validate_delivery(p)
        self.assertTrue(all(r['rating'] is None for r in ps))

    def test_zero_variance_withheld(self):
        ps=combine_observations([row(),row(pid=2)])
        self.assertTrue(all(r['private_experimental_rating'] is None for r in private_preview(ps)['players']))

    def test_determinism_and_conservation(self):
        rows=[row(),row(mid=2,prog_passes=20),row(pid=2)]
        self.assertEqual(combine_observations(rows),combine_observations(list(reversed(rows))))
        ps=combine_observations(rows)
        self.assertEqual(sum(p['prog_passes'] for p in ps),40)
        self.assertEqual(sum(p['measured_passes'] for p in ps),300)

    def test_full_cohort_calibration_not_reporting_subset(self):
        e=pd.DataFrame([event(),event('b',player_id=2,pass_outcome='Incomplete')])
        ref=calibrate_difficulty(e,scope='explicit synthetic eligible cohort',complete=True)
        self.assertEqual(ref.cells.iloc[0].p_hat,.5)
        reporting,_,_=_prepare(e.iloc[:1])
        valued=_apply_reference(reporting,ref)
        self.assertEqual(valued.pass_value.iloc[0],15)

    def test_joseph_geometry_and_outcomes(self):
        e=pd.DataFrame([event('exact',location=[80,40],pass_end_location=[90,40]),
            event('short',location=[80,40],pass_end_location=[89.999,40]),
            event('ratio',location=[0,40],pass_end_location=[10,40]),
            event('fail',pass_outcome='Incomplete'),event('corner',pass_type='Corner'),
            event('missing',location=None),event('boundary',location=[40,40],pass_end_location=[80,40])])
        p,_,summary=_prepare(e)
        p=joseph.flag_progressive(p.assign(difficulty=0))
        self.assertEqual(set(p.loc[p.progressive,'id']),{'exact','boundary'})
        self.assertTrue(p.set_index('id').loc['fail','prog_attempt'])
        self.assertEqual(summary['missing_geometry'],1)
        self.assertTrue(p.set_index('id').loc['boundary','third_cross'])

    def test_projection_preserves_original_identity_and_failure_outcome(self):
        raw=[dict(id='verified-uuid',type={'name':'Pass'},team={'id':7,'name':'Club'},
            player={'id':23,'name':'Original'},location=[40,40],
            **{'pass':dict(end_location=[80,40],outcome={'name':'Incomplete'})})]
        p=project(raw,42,'La Liga').iloc[0]
        self.assertEqual((p.id,p.match_id,p.player_id,p.team_id),('verified-uuid',42,23,7))
        self.assertEqual(p.pass_outcome,'Incomplete')
        self.assertEqual(raw[0]['pass']['outcome']['name'],'Incomplete')

    def test_existing_output_and_changed_evidence_fail_closed(self):
        with patch('scripts.prepare_fifth_attribute.Path.exists',return_value=True):
            with self.assertRaisesRegex(ValueError,'exclusive'):build('existing')
        with patch('scripts.prepare_fifth_attribute.sha',return_value='changed'):
            with self.assertRaisesRegex(ValueError,'binding changed'):
                read_bound({'path':'sealed.json','sha256':'original'})

    def test_offline_assembly_with_null_unsupported_position_allocation(self):
        from scripts import prepare_fifth_attribute as runner
        e=dict(id='original',type={'name':'Pass'},team={'id':7,'name':'Club'},
            player={'id':1,'name':'Player'},location=[30,40],
            **{'pass':dict(end_location=[60,40],length=30)})
        report=dict(competition_name='La Liga',artifacts={'events':{'path':'original.json','sha256':'bound'}})
        app=dict(player_id=1,team_id=7,active_appearance=True,player_name_raw='Player',
            season_name='2015/2016',team='Club',competition_name='La Liga',
            participation_status='STRUCTURALLY_VALID',validated_elapsed_seconds={'numerator':54000,'denominator':1},
            position_allocation=[{'position':'Center Midfield','elapsed_seconds':{'numerator':54000,'denominator':1}}])
        apps=[app,app|dict(player_id=2,player_name_raw='Missing',participation_status='INCOMPLETE_EVIDENCE',
            validated_elapsed_seconds=None,position_allocation=None)]
        def components(pid, independent=False):
            return {n:dict(count=int(pid==1),event_ids=['original'] if pid==1 else []) for n in
                ('progressive_attempts','progressive_passes','progressive_third_crossings')}
        metrics=[dict(team_id=7,player_id=a['player_id'],progressive_missing_geometry=0,
            components=components(a['player_id'])) for a in apps]
        checks=[dict(team_id=7,player_id=a['player_id'],actor_findings=[],
            independent_seconds=a['validated_elapsed_seconds'],components=components(a['player_id'])) for a in apps]
        def groups(path):
            if path.parent==runner.BUNDES:return iter([])
            rows=checks if path.parent==runner.CHECKS else apps if path.name=='appearance-ledger.jsonl' else metrics
            return iter([(1,rows)])
        with tempfile.TemporaryDirectory() as d, \
                patch.object(runner,'seal',return_value={}), \
                patch.object(runner,'match_sources',side_effect=lambda:iter([(1,report,False)])), \
                patch.object(runner,'read_bound',return_value=[e]), \
                patch.object(runner,'grouped',side_effect=groups), \
                patch.object(runner,'event_within_exposure',return_value=True):
            output=Path(d)/'private'
            runner.build(output)
            players=list(runner.records(output/'player-measurements.jsonl'))
            self.assertEqual(players[0]['prog_passes'],1)
            self.assertEqual(players[0]['measured_passes'],1)
            self.assertIsNone(players[1]['prog_passes'])
            self.assertEqual(players[1]['position_seconds'],{})
            self.assertTrue((output/'manifest.json').is_file())
            self.assertFalse(json.loads((output/'summary.json').read_text())['publication_authorized'])


if __name__=='__main__':unittest.main()
