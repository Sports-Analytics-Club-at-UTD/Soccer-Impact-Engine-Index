"""Exact physical-transition and partial-exposure regressions on synthetic events."""
from copy import deepcopy
from fractions import Fraction
import unittest

from src.appearance_recovery import recover_exposure, contains


def fixture(*,starter=True,late_first=False,early_end=False,late_second=False):
    events=[]
    def add(period,time,name,team=10,**fields):
        i=len(events)+1
        h=int(time)//3600;m=int(time)%3600//60;s=Fraction(time)%60
        e=dict(id=str(i),index=i,period=period,timestamp=f'{h:02}:{m:02}:{float(s):06.3f}',
            team={'id':team},type={'name':name},**fields)
        events.append(e);return e
    members=[{'player':{'id':i},'position':{'id':i,'name':'Example role'}} for i in range(1 if starter else 2,12 if starter else 13)]
    add(1,0,'Starting XI',tactics={'lineup':members})
    add(1,0,'Starting XI',20,tactics={'lineup':[{'player':{'id':i}} for i in range(21,32)]})
    for t in (10,20):add(1,0,'Half Start',t,**({'half_start':{'late_video_start':True}} if late_first else {}))
    for t in (10,20):add(1,2800,'Half End',t)
    for t in (10,20):add(2,0,'Half Start',t,**({'half_start':{'late_video_start':True}} if late_second else {}))
    for t in (10,20):add(2,2900,'Half End',t,**({'half_end':{'early_video_end':True}} if early_end else {}))
    return events


def insert(events,period,time,name,**fields):
    h=int(time)//3600;m=int(time)%3600//60;s=Fraction(time)%60
    e=dict(id='extra-'+str(len(events)),period=period,timestamp=f'{h:02}:{m:02}:{float(s):06.3f}',team={'id':10},type={'name':name},**fields)
    # Boundaries stay paired; explicit source indices establish within-clock order.
    events.append(e)
    events.sort(key=lambda e:(e['period'],e['timestamp'],0 if e['type']['name']=='Starting XI' else 1))
    for index,event in enumerate(events,1):event['index']=index
    return e


class AppearanceRecoveryTests(unittest.TestCase):
    def test_complete_two_halves_have_exact_duration(self):
        r=recover_exposure(fixture(),10,1)
        self.assertTrue(r.complete);self.assertEqual(r.seconds,5700)

    def test_early_video_end_retains_only_confirmed_first_half(self):
        r=recover_exposure(fixture(early_end=True),10,1)
        self.assertFalse(r.complete);self.assertEqual(r.seconds,2800)
        self.assertEqual([s.period for s in r.segments],[1])

    def test_substitution_before_missing_final_whistle_is_complete(self):
        events=fixture(early_end=True)
        insert(events,2,Fraction('1234.567'),'Substitution',player={'id':1},substitution={'replacement':{'id':99}})
        r=recover_exposure(events,10,1)
        self.assertTrue(r.complete);self.assertEqual(r.seconds,Fraction('4034.567'))

    def test_late_first_half_does_not_invent_first_half_minutes(self):
        r=recover_exposure(fixture(late_first=True),10,1)
        self.assertFalse(r.complete);self.assertEqual(r.seconds,2900)

    def test_late_second_half_retains_first_half_only(self):
        r=recover_exposure(fixture(late_second=True),10,1)
        self.assertFalse(r.complete);self.assertEqual(r.seconds,2800)

    def test_known_incoming_and_outgoing_pair_in_flagged_period(self):
        es=fixture(starter=False,late_first=True)
        insert(es,1,100,'Substitution',player={'id':2},substitution={'replacement':{'id':1}})
        insert(es,1,300,'Substitution',player={'id':1},substitution={'replacement':{'id':99}})
        r=recover_exposure(es,10,1)
        self.assertTrue(r.complete);self.assertEqual(r.seconds,200)

    def test_temporarily_off_time_is_removed_exactly(self):
        es=fixture();insert(es,1,300,'Player Off',player={'id':1});insert(es,1,Fraction('320.125'),'Player On',player={'id':1})
        r=recover_exposure(es,10,1)
        self.assertTrue(r.complete);self.assertEqual(r.seconds,Fraction('5679.875'))

    def test_permanent_exit_followed_by_return_is_withheld(self):
        es=fixture();insert(es,1,300,'Player Off',player={'id':1},player_off={'permanent':True});insert(es,1,320,'Player On',player={'id':1})
        r=recover_exposure(es,10,1)
        self.assertEqual(r.reasons,('CONFLICTING_RETURN',));self.assertFalse(r.complete)
        self.assertEqual(r.seconds,300)

    def test_actual_activity_after_permanent_exit_is_withheld(self):
        es=fixture();insert(es,1,300,'Substitution',player={'id':1},substitution={'replacement':{'id':99}});insert(es,1,320,'Pass',player={'id':1})
        r=recover_exposure(es,10,1)
        self.assertFalse(r.complete);self.assertEqual(r.seconds,300)

    def test_second_yellow_cuts_elapsed_time(self):
        es=fixture();insert(es,2,1200,'Foul Committed',player={'id':1},foul_committed={'card':{'name':'Second Yellow'}})
        r=recover_exposure(es,10,1)
        self.assertTrue(r.complete);self.assertEqual(r.seconds,4000)

    def test_role_disagreement_does_not_invent_physical_exit(self):
        es=fixture();members=deepcopy(es[0]['tactics']['lineup']);members[0]['position']={'id':25,'name':'Other role'}
        insert(es,2,100,'Tactical Shift',tactics={'lineup':members})
        self.assertEqual(recover_exposure(es,10,1).seconds,5700)

    def test_missing_physical_member_is_not_ignored(self):
        es=fixture();members=deepcopy(es[0]['tactics']['lineup']);members[0]['player']['id']=99
        insert(es,2,100,'Tactical Shift',tactics={'lineup':members})
        self.assertIsNone(recover_exposure(es,10,1).seconds)

    def test_duplicate_indices_are_rejected(self):
        es=fixture();es[-1]['index']=es[-2]['index']
        self.assertIsNone(recover_exposure(es,10,1).seconds)

    def test_disagreeing_half_clocks_are_not_averaged(self):
        es=fixture();es[5]['timestamp']='00:46:39.000'
        r=recover_exposure(es,10,1)
        self.assertFalse(r.complete);self.assertEqual(r.seconds,2900)

    def test_unused_substitute_does_not_get_minutes(self):
        self.assertIsNone(recover_exposure(fixture(starter=False),10,1).seconds)

    def test_actual_actions_are_scoped_to_recovered_half(self):
        es=fixture(early_end=True);before=insert(es,1,100,'Pass',player={'id':1});after=insert(es,2,100,'Pass',player={'id':1})
        r=recover_exposure(es,10,1)
        self.assertTrue(contains(before,r.segments));self.assertFalse(contains(after,r.segments))

    def test_transition_after_observed_video_limit_is_rejected(self):
        es=fixture(early_end=True);insert(es,2,3000,'Substitution',player={'id':1},substitution={'replacement':{'id':99}})
        self.assertIsNone(recover_exposure(es,10,1).seconds)

    def test_equal_clock_transitions_are_not_guessed(self):
        es=fixture();insert(es,1,300,'Player Off',player={'id':1});insert(es,1,300,'Player On',player={'id':1})
        self.assertIsNone(recover_exposure(es,10,1).seconds)

    def test_verified_halftime_return_does_not_count_break_time(self):
        es=fixture();insert(es,1,2700,'Player Off',player={'id':1});insert(es,1,Fraction('2800.078'),'Player On',player={'id':1})
        r=recover_exposure(es,10,1)
        self.assertTrue(r.complete);self.assertEqual(r.seconds,5600)

    def test_halftime_return_needs_verified_second_half_start(self):
        es=fixture(late_second=True);insert(es,1,2700,'Player Off',player={'id':1});insert(es,1,Fraction('2800.078'),'Player On',player={'id':1})
        self.assertIsNone(recover_exposure(es,10,1).seconds)


if __name__=='__main__':unittest.main()
