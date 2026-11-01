"""Exact alias regressions with an event-driven independent oracle."""
import copy
from collections import defaultdict
from fractions import Fraction as F
import unittest

from test_statsbomb_participation import fixture, run, transition
from scripts import decoder_fix_independent as oracle
from src.independent_source_checks import boundaries, exposure, within


def absence(entry='Player On (Off Camera)', exit='Player Off (Off Camera)', halftime=False):
    d=fixture();p=d[1][0]['lineup'][0];s=p['positions'][0]
    s.update(to='46:00' if halftime else '91:00',to_period=1 if halftime else 2,end_reason=exit)
    t=copy.deepcopy(s);t.update(**{'from':'47:00' if halftime else '92:00','to':None},from_period=2,to_period=None,start_reason=entry,end_reason='Final Whistle')
    p['positions'].append(t)
    transition(d[2],'Player Off','00:46:00.125',46 if halftime else 91,0)
    d[2][-1]['period']=1 if halftime else 2
    transition(d[2],'Player On','00:02:00.875' if halftime else '00:47:00.875',47 if halftime else 92,0)
    return d


class DecoderAliasTests(unittest.TestCase):
    def verify(self,d,expected):
        before=copy.deepcopy(d);a=run(d);r=a.validate()[0]
        self.assertEqual(d,before)
        self.assertEqual(r.status,'STRUCTURALLY_VALID')
        self.assertEqual(r.elapsed_seconds,expected)
        bounds,issues,_=oracle.boundaries(d[2],{1,2})
        independent=oracle.reconstruct(101,1,d[1][0]['lineup'][0],d[2],bounds,issues)
        self.assertEqual(independent['issues'],[])
        self.assertEqual(independent['seconds'],expected)
        self.assertEqual(independent['lineup_seconds'],expected)
        index=defaultdict(list)
        for e in d[2]:index[e['period'],e['minute'],e['second'],e['team']['id'],e['type']['name']].append(e)
        check=exposure(d[1][0]['lineup'][0]['positions'],101,1,index,boundaries(d[2],{1,2}))
        self.assertEqual(check[0],expected)
        return r

    def test_normal_labels(self):self.verify(absence('Player On','Player Off'),F('5640.25'))
    def test_entry_alias_only(self):self.verify(absence(exit='Player Off'),F('5640.25'))
    def test_exit_alias_only(self):self.verify(absence(entry='Player On'),F('5640.25'))
    def test_both_aliases(self):self.verify(absence(),F('5640.25'))
    def test_halftime_spanning_absence(self):self.verify(absence(halftime=True),F('5489.75'))

    def test_exit_without_return_remains_incomplete(self):
        d=absence();d[1][0]['lineup'][0]['positions'].pop();d[2][:]=[e for e in d[2] if e['type']['name']!='Player On']
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_entry_without_prior_exit_is_conflict(self):
        d=absence();d[1][0]['lineup'][0]['positions'].pop(0)
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_missing_entry(self):
        d=absence();d[2][:]=[e for e in d[2] if e['type']['name']!='Player On']
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_missing_exit(self):
        d=absence();d[2][:]=[e for e in d[2] if e['type']['name']!='Player Off']
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_duplicate_transition_different_milliseconds(self):
        d=absence();e=copy.deepcopy(d[2][-1]);e.update(id='ambiguous',timestamp='00:47:00.876');d[2].append(e)
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_permanent_exit_cannot_be_temporary(self):
        d=absence();next(e for e in d[2] if e['type']['name']=='Player Off')['player_off']={'permanent':True}
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_substitution_before_return_remains_conflicting(self):
        d=absence();transition(d[2],'Substitution','00:46:30.000',91,30,substitution={'replacement':{'id':999,'name':'Other'}})
        d[1][0]['lineup'].append(dict(player_id=999,player_name='Other',positions=[]))
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_red_card_before_return(self):
        d=absence();transition(d[2],'Foul Committed','00:46:30.000',91,30,foul_committed={'card':{'name':'Red Card'}})
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_second_yellow_before_return(self):
        d=absence();transition(d[2],'Bad Behaviour','00:46:30.000',91,30,bad_behaviour={'card':{'name':'Second Yellow'}})
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_reversed_periods(self):
        d=absence();d[1][0]['lineup'][0]['positions'][1]['to_period']=1
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_overlap(self):
        d=absence();d[1][0]['lineup'][0]['positions'].append(copy.deepcopy(d[1][0]['lineup'][0]['positions'][1]))
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_contradictory_position_snapshot(self):
        d=absence();transition(d[2],'Tactical Shift','00:47:15.000',92,15,tactics={'lineup':[{'player':{'id':101,'name':'Home Player'},'position':{'id':5,'name':'Left Center Back'}}]})
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_unknown_similar_label_still_withheld(self):
        d=absence(entry='Player On (Unknown)')
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_alias_on_wrong_endpoint_withheld(self):
        d=absence(entry='Player Off (Off Camera)')
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_event_during_absence_is_outside_exact_geometry(self):
        d=absence();r=self.verify(d,F('5640.25'))
        bounds,issues,_=oracle.boundaries(d[2],{1,2})
        intervals=oracle.reconstruct(101,1,d[1][0]['lineup'][0],d[2],bounds,issues)['intervals']
        event={'period':2,'timestamp':'00:46:30.000'}
        self.assertFalse(within(event,intervals,boundaries(d[2],{1,2})))

    def test_no_tolerance_for_event_after_final_whistle(self):
        d=absence();self.verify(d,F('5640.25'))
        bounds,issues,_=oracle.boundaries(d[2],{1,2})
        intervals=oracle.reconstruct(101,1,d[1][0]['lineup'][0],d[2],bounds,issues)['intervals']
        self.assertFalse(within({'period':2,'timestamp':'00:47:30.501'},intervals,boundaries(d[2],{1,2})))

    def test_independent_oracle_does_not_import_production(self):
        from pathlib import Path
        text=Path(oracle.__file__).read_text()
        self.assertNotIn('from src.',text)
        self.assertNotIn('import src.',text)
