"""Invented fixtures exercise the real-input boundary; no source attestation."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import unittest

import test_source_reconstruction as reconstruction_tests
from src.source_reconstruction import aggregate_context
from src.real_candidate_analysis import analyze,summarize
from scripts.analyze_real_candidates import build
from scripts.reconstruct_player_evidence import reconstruct,file_hash


def club(minutes=900,*,mid=10,team='Home',role='CB',status='STRUCTURALLY_VALID',pid=101,identities=()):
    a,m=reconstruction_tests.contribution(mid,minutes,10,status,team);a['player_id']=pid
    c=aggregate_context([a],[m],provider_complete=True,identity_reasons=identities,role=role)
    c.update(team=team,team_id=1 if team=='Home' else 2,competition_name='La Liga')
    c['delivered_scope_comparison']=copy.deepcopy(c) if mid!=3879594 else None
    return c


class RealCandidateFactsTests(unittest.TestCase):
    def test_real_counts_enter_existing_engine_but_never_attest_themselves(self):
        c=club();before=copy.deepcopy(c)
        facts,result,pop,metrics,pool=analyze([c],source='fixture/hash')
        self.assertEqual(c,before);self.assertTrue(facts[0]['candidate_900_evidence_met'])
        self.assertEqual(facts[0]['components']['tackles']['candidate_per90'],1)
        self.assertFalse(pop.iloc[0].reference_member)
        self.assertEqual(pop.iloc[0].identity_evidence.kind,'UNVERIFIED')
        self.assertFalse(pop.iloc[0].exposure_scope.full_season)
        self.assertFalse(result.players.iloc[0].eligible)
        self.assertIn('unverified_identity_evidence',result.players.iloc[0].reasons)
        self.assertTrue(result.players.dri_fifa.isna().all())
        self.assertTrue(all(r['numeric_ratings']==0 for r in summarize(facts,result)['groups']))

    def test_exact_900_boundary_and_separate_role_groups(self):
        for role,group in [('CB','CB'),('DM','MID'),('CM','MID'),(None,None)]:
            for mins,eligible in [(Fraction(899999,1000),False),(Fraction(900*10**18-1,10**18),False),(900,role is not None)]:
                f,*_=analyze([club(mins,role=role)],source='fixture')
                self.assertEqual(f[0]['comparison_group'],group)
                self.assertEqual(f[0]['candidate_900_evidence_met'],eligible)

    def test_unresolved_minutes_never_become_subset_season_rates(self):
        for status in ('CONFLICTING_EVIDENCE','INCOMPLETE_EVIDENCE'):
            f,r,p,m,_=analyze([club(status=status)],source='fixture')
            self.assertIsNone(f[0]['complete_delivered_scope_minutes'])
            self.assertIsNone(f[0]['components']['tackles']['candidate_per90'])
            self.assertEqual(f[0]['components']['tackles']['delivered_scope_count'],10)
            self.assertTrue(m.per90.isna().all());self.assertFalse(f[0]['candidate_900_evidence_met'])

    def test_missing_delivered_fixture_is_excluded_and_does_not_get_zero_facts(self):
        f,r,p,m,_=analyze([club(mid=3879594)],source='fixture')
        self.assertEqual(f[0]['analysis_match_ids'],[])
        self.assertEqual(f[0]['excluded_match_ids'],[3879594])
        self.assertIsNone(f[0]['components']['tackles']['delivered_scope_count'])
        self.assertEqual(f[0]['components']['tackles']['original_provider_count'],10)
        self.assertIsNone(p.iloc[0].exposure_scope)

    def test_identity_flags_withhold_complete_exposure(self):
        f,*_=analyze([club(identities=['CANDIDATE_SOURCE_NAME_DISAGREEMENT'])],source='fixture')
        self.assertFalse(f[0]['candidate_900_evidence_met']);self.assertIsNone(f[0]['complete_delivered_scope_minutes'])

    def test_duplicate_context_and_different_club_ids_reject(self):
        c=club()
        with self.assertRaises(ValueError):analyze([c,c],source='fixture')
        d=club(pid=102);d['team_id']=2
        with self.assertRaises(ValueError):analyze([c,d],source='fixture')

    def test_foreign_component_scope_and_inconsistent_per90_reject(self):
        for change in ('scope','rate','count'):
            c=club();v=c['delivered_scope_comparison']['components']['tackles']
            if change=='scope':v['aligned_match_ids']=[11]
            elif change=='rate':v['provider_scope_per90']=50
            else:v['raw_source_count']=True
            with self.assertRaises(ValueError):analyze([c],source='fixture')

    def test_transfer_contexts_stay_separate_and_have_no_reference_admission(self):
        f,r,*_=analyze([club(400),club(600,mid=11,team='Away')],source='fixture')
        self.assertEqual(len(f),2);self.assertFalse(any(x['candidate_900_evidence_met'] for x in f))
        self.assertFalse(any(x['reference_member'] for x in f));self.assertFalse(r.players.eligible.any())

    def test_existing_press_percentage_is_measurement_not_rating(self):
        c=club();ds=c['delivered_scope_comparison']
        for name,count in [('pressured_pass_attempts',40),('pressured_pass_completed',30),('pressured_dribble_attempts',10),('pressured_dribble_completed',5)]:
            v=ds['components'][name];v.update(raw_source_count=count,aligned_subset_count=count,provider_scope_per90=count/10)
        f,*_=analyze([c],source='fixture');p=f[0]['press_measurement']
        self.assertEqual(p['completion_percentage'],70);self.assertIsNone(p['rating']);self.assertIsNone(p['percentile'])
        self.assertTrue(all(r['measurement_and_900_gate_met'] for r in p['action_threshold_comparisons']))
        self.assertFalse(any(r['approved'] for r in p['action_threshold_comparisons']))

    def test_zero_press_attempts_and_line_breaking_and_ovr_are_missing(self):
        f,*_=analyze([club()],source='fixture');p=f[0]
        self.assertIsNone(p['press_measurement']['completion_percentage'])
        self.assertIsNone(p['line_breaking_rating']);self.assertIsNone(p['overall_rating']);self.assertIsNone(p['archetype'])

    def test_recovery_interval_failure_does_not_discard_count_or_exposure(self):
        c=club();v=c['delivered_scope_comparison']['components']['recoveries']
        v.update(provider_scope_per90=None,provider_scope_status='NUMERATOR_DENOMINATOR_SCOPE_UNRESOLVED',aligned_match_ids=[],reasons=['NUMERATOR_DENOMINATOR_MISMATCH'])
        f,r,*_=analyze([c],source='fixture')
        self.assertEqual(f[0]['complete_delivered_scope_minutes'],900)
        self.assertTrue(f[0]['candidate_900_evidence_met'])
        self.assertFalse(f[0]['components']['recoveries']['candidate_900_measurement_ready'])

    def test_candidate_gate_and_source_trust_tampering_reject(self):
        for field in ('reference_member','production_certified'):
            c=club();c[field]=True
            with self.assertRaises(ValueError):analyze([c],source='fixture')
        c=club();c['delivered_scope_comparison']['candidate_900_minutes_evidence_met']=False
        with self.assertRaises(ValueError):analyze([c],source='fixture')

    def test_order_does_not_change_facts_or_engine_results(self):
        c,d=club(),club(1200,mid=11,pid=102)
        a,b,*_=analyze([c,d],source='fixture');x,y,*_=analyze([d,c],source='fixture')
        self.assertEqual(a,x);self.assertTrue(b.players.equals(y.players))


class RealCandidateRunTests(unittest.TestCase):
    def setUp(self):
        self.fixture=reconstruction_tests.ReconstructionRunTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.run=self.root/'source';reconstruct(output=self.run,**self.fixture.kw)

    def test_deterministic_read_only_run_and_offline_frontend_contract(self):
        before={p.name:(file_hash(p),p.stat().st_mtime_ns) for p in self.run.iterdir()}
        a=build(self.run,self.root/'one');hashes={p.name:file_hash(p) for p in (self.root/'one').iterdir()}
        self.assertEqual(build(self.run,self.root/'one'),a)
        self.assertEqual(a,build(self.run,self.root/'two'))
        self.assertEqual(hashes,{p.name:file_hash(p) for p in (self.root/'two').iterdir()})
        self.assertEqual(before,{p.name:(file_hash(p),p.stat().st_mtime_ns) for p in self.run.iterdir()})
        check=subprocess.run(['node','scripts/check_real_candidate_handoff.mjs',str(self.root/'one'/'offline-withheld-contract-fixture.json')],capture_output=True,text=True)
        self.assertEqual(check.returncode,0,check.stderr)
        self.assertEqual(json.loads(check.stdout)['diagnostic_records'],2)
        self.assertEqual(a['candidate_scores_generated'],0);self.assertTrue(a['existing_numeric_boundaries_held'])

    def test_source_tamper_and_partial_output_refuse_without_rebuild(self):
        (self.run/'summary.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):build(self.run,self.root/'one')
        self.assertFalse((self.root/'one').exists())

    def test_analysis_tamper_refuses_overwrite(self):
        build(self.run,self.root/'one');p=self.root/'one'/'summary.json';p.write_bytes(b'{}')
        with self.assertRaises(ValueError):build(self.run,self.root/'one')
        self.assertEqual(p.read_bytes(),b'{}')
        (self.root/'partial').mkdir()
        with self.assertRaises(FileNotFoundError):build(self.run,self.root/'partial')


if __name__=='__main__':unittest.main()
