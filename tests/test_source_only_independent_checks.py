"""Source-only checks with invented inputs; copied assertions retain independent expectations."""
from collections import Counter, defaultdict
import copy
from fractions import Fraction
import unittest
from unittest.mock import patch
import test_source_reconstruction as fixtures
from src.independent_source_checks import check_match, selected, clock, reference_readiness, CheckMismatch
from src.source_reconstruction import exact, rational, COUNT_NAMES, aggregate_context

def checked(d=None):
    d=fixtures.data() if d is None else d
    appearances,_,metrics,_=fixtures.project(d)
    return d,appearances,metrics,check_match(d[0][0],d[1],d[2],appearances,metrics)


def club_fixture(minutes=900,status='STRUCTURALLY_VALID',role='CB',team='Home',mid=10):
    a,m=fixtures.contribution(mid,minutes,10,status,team)
    if status=='STRUCTURALLY_VALID':a['position_allocation']=[dict(position='Center Back',elapsed_seconds=rational(Fraction(minutes)*60))]
    c=aggregate_context([a],[m],provider_complete=True,role=role)
    c.update(team=team,team_id=1,competition_name='La Liga',includes_policy_pending_3879594=False)
    g=dict(seconds=exact(a['validated_elapsed_seconds']) if a['validated_elapsed_seconds'] else Fraction(0),
        counts=Counter({n:v['count'] for n,v in m['components'].items()}),positions={'Center Back':Fraction(minutes)*60} if a['validated_elapsed_seconds'] else {},
        matches={mid},unresolved=0 if status=='STRUCTURALLY_VALID' else 1,actor_findings=0,
        aligned_matches=defaultdict(set,{n:{mid} if status=='STRUCTURALLY_VALID' else set() for n in COUNT_NAMES}),
        aligned_counts=Counter({n:v['count'] if status=='STRUCTURALLY_VALID' else 0 for n,v in m['components'].items()}),
        aligned_seconds=defaultdict(Fraction,{n:Fraction(minutes)*60 if status=='STRUCTURALLY_VALID' else Fraction(0) for n in COUNT_NAMES}))
    return c,g


class IndependentChecksTests(unittest.TestCase):
    def test_original_facts_preserved_and_independent_intervals_agree(self):
        d=fixtures.data();before=copy.deepcopy(d);_,a,m,r=checked(d)
        self.assertEqual(d,before);self.assertEqual(len(r['rows']),2)
        for old,new in zip(a,r['rows']):self.assertEqual(new['independent_seconds'],old['validated_elapsed_seconds'])
        self.assertTrue(all(not r['independent_external_attestation'] for r in r['rows']))


    def test_does_not_call_original_reconstruction_extractors_or_validator(self):
        d,a,m,_=checked()
        with patch('src.source_reconstruction.measurements',side_effect=AssertionError('not independent')),patch('src.statsbomb_participation.adapt_match',side_effect=AssertionError('not independent')):
            self.assertEqual(len(check_match(d[0][0],d[1],d[2],a,m)['rows']),2)


    def test_secondary_recipient_identity_conflict_is_quarantined_without_guessing(self):
        d=fixtures.data();e=next(e for e in d[2] if e['id']=='pass');e['pass']['recipient']=dict(id=102,name='Away Player')
        _,a,m,r=checked(d)
        self.assertEqual(r['actor_findings'][0]['actor_role'],'recipient')
        self.assertTrue(next(r for r in r['rows'] if r['player_id']==101)['actor_findings'])
        self.assertFalse(any(r['production_certified'] for r in r['rows']))


    def test_total_interceptions_are_diagnostic_and_do_not_replace_successful(self):
        d=fixtures.data();e=copy.deepcopy(next(e for e in d[2] if e['id']=='intercept'));e['id']='failed-interception';e['interception']['outcome']['name']='Lost In Play';d[2].append(e)
        r=checked(d)[3]
        self.assertEqual(r['source_totals']['total_interceptions'],2);self.assertEqual(r['source_totals']['interceptions'],1)


    def test_pdf_forward_flag_is_not_joseph_progression_or_a_rating(self):
        d=fixtures.data();e=next(e for e in d[2] if e['id']=='pass');e['location']=[30,40];e['pass']['end_location']=[41,40]
        r=checked(d)[3];g=r['pdf_geometry_diagnostics']
        self.assertEqual(g['pdf_forward_x_P10'],1);self.assertEqual(g['pdf_Z_third_crossing'],1)
        self.assertEqual(g['P10_without_Joseph_distance_condition'],1)
        self.assertEqual(r['source_totals'].get('progressive_passes',0),0);self.assertIsNone(r['pdf_composite_score'])


    def test_clock_precision_and_halftime_exclusion(self):
        self.assertEqual(clock('00:00:00.123'),Fraction(123,1000))
        _,a,_,r=checked();self.assertEqual(exact(r['rows'][0]['independent_seconds']),exact(a[0]['validated_elapsed_seconds']))
        for invalid in ['00:60:00','00:00:60','45:00']:
            with self.assertRaises(CheckMismatch):clock(invalid)


    def test_missing_original_endpoint_cannot_support_valid_ledger(self):
        d,a,m,_=checked();d[2][:]=[e for e in d[2] if e['type']['name']!='Starting XI']
        with self.assertRaises(CheckMismatch):check_match(d[0][0],d[1],d[2],a,m)


    def test_missing_boundary_is_preserved_without_inferred_exposure(self):
        d=fixtures.data();d[2][:]=[e for e in d[2] if not(e['period']==2 and e['type']['name']=='Half End')]
        r=checked(d)[3];self.assertTrue(all(row['independent_seconds'] is None for row in r['rows']))


    def test_contradictory_actor_is_withheld_even_if_raw_stint_geometry_exists(self):
        d=fixtures.data();d[2].append(dict(id='red',period=1,timestamp='00:30:00.000',minute=30,second=0,
            type=dict(name='Bad Behaviour'),team=dict(id=1,name='Home'),player=dict(id=101,name='Home Player'),bad_behaviour=dict(card=dict(name='Red Card'))))
        r=checked(d)[3];row=next(r for r in r['rows'] if r['player_id']==101)
        self.assertEqual(row['participation_status'],'CONFLICTING_EVIDENCE');self.assertIsNone(row['independent_seconds'])
        self.assertEqual(row['components']['tackles']['count'],1);self.assertIsNone(row['components']['tackles']['per90'])


    def test_outside_recovery_clock_retains_uuid_and_withholds_rate(self):
        d=fixtures.data();e=next(e for e in d[2] if e['id']=='recover');e.update(period=2,timestamp='00:50:00.000',minute=95)
        r=checked(d)[3];c=next(r for r in r['rows'] if r['player_id']==101)['components']['recoveries']
        self.assertEqual(c['unaligned_event_ids'],['recover']);self.assertEqual(c['count'],1);self.assertIsNone(c['per90'])


    def test_original_duplicate_uuid_and_derived_duplicate_actor_reject(self):
        d,a,m,_=checked();d[2].append(copy.deepcopy(d[2][0]))
        with self.assertRaises(CheckMismatch):check_match(d[0][0],d[1],d[2],a,m)
        d,a,m,_=checked();a.append(copy.deepcopy(a[0]));m.append(copy.deepcopy(m[0]))
        with self.assertRaises(CheckMismatch):check_match(d[0][0],d[1],d[2],a,m)


    def test_derived_minutes_positions_count_and_rate_tampering_reject(self):
        for field in ('minutes','positions','count','rate'):
            d,a,m,_=checked()
            if field=='minutes':a[0]['validated_elapsed_seconds']=rational(Fraction(1))
            elif field=='positions':a[0]['original_positions'][0]['position']='Invented'
            elif field=='count':m[0]['components']['tackles']['count']=99
            else:m[0]['components']['tackles']['per90']=99
            with self.assertRaises(CheckMismatch):check_match(d[0][0],d[1],d[2],a,m)


    def test_exact_900_and_source_role_do_not_admit_reference_members(self):
        for minutes,expected in [(Fraction(900*10**18-1,10**18),False),(900,True)]:
            c,g=club_fixture(minutes);r=reference_readiness([c],{(101,'Home','La Liga','2015/2016'):g})[0]
            self.assertEqual(r['technical_candidate_checks_passed'],expected)
            self.assertFalse(r['reference_member']);self.assertFalse(r['fully_evidence_ready'])


    def test_source_dominant_role_disagreement_blocks_technical_readiness(self):
        c,g=club_fixture(role='DM');r=reference_readiness([c],{(101,'Home','La Liga','2015/2016'):g})[0]
        self.assertTrue(r['original_candidate_900']);self.assertFalse(r['source_dominant_group_agrees']);self.assertFalse(r['technical_candidate_checks_passed'])


    def test_role_dominance_is_computed_before_mid_comparison_mapping(self):
        c,g=club_fixture(1300,role='CM')
        positions={'Center Attacking Midfield':400,'Center Midfield':500,'Left Midfield':400}
        c['source_position_minutes']={p:rational(Fraction(v)) for p,v in positions.items()}
        g['positions']={p:Fraction(v)*60 for p,v in positions.items()}
        r=reference_readiness([c],{(101,'Home','La Liga','2015/2016'):g})[0]
        self.assertEqual(r['source_dominant_role_groups'],['CM'])
        self.assertEqual(r['independently_supported_comparison_groups'],['MID'])
        self.assertTrue(r['technical_candidate_checks_passed'])


    def test_unknown_appearance_does_not_turn_known_subset_into_complete_season(self):
        c,g=club_fixture(status='INCOMPLETE_EVIDENCE');r=reference_readiness([c],{(101,'Home','La Liga','2015/2016'):g})[0]
        self.assertFalse(r['original_candidate_900']);self.assertEqual(r['unresolved_appearances'],1)


    def test_candidate_or_aligned_subset_tamper_is_rejected(self):
        for field in ('candidate','scope'):
            c,g=club_fixture()
            if field=='candidate':c['candidate_900_minutes_evidence_met']=False
            else:c['components']['tackles']['aligned_match_ids']=[]
            with self.assertRaises(CheckMismatch):reference_readiness([c],{(101,'Home','La Liga','2015/2016'):g})
