"""Terminal-exit proof and exact negative controls; source bytes stay immutable."""
import copy
from dataclasses import replace
from fractions import Fraction as F
import unittest
from unittest.mock import patch

from test_statsbomb_participation import run, transition
from test_off_field_cards import complete, indexed, card
from test_source_backed_entry import substitute
from src.statsbomb_participation import SourceSchemaError
from src.participation_intervals import Clock, validate_participation


def terminal(data=None, stamp='00:15:00.125', minute=60, second=0):
    d=data or complete()
    d[1][0]['lineup'][0]['positions'][-1].update(to=f'{minute:02}:{second:02}',to_period=2,end_reason='Player Off (Permanent)')
    transition(d[2],'Player Off',stamp,minute,second,player_off=dict(permanent=True))
    return d


class PermanentExitTests(unittest.TestCase):
    def inspect(self,d):
        a=run(d);p=next(p for p in a.players if p.context.player_id==101)
        return a,p,next(v for v in a.validate() if v.context.player_id==101)

    def accepts(self,d):
        original=copy.deepcopy(d);a,p,v=self.inspect(d)
        self.assertIsNotNone(v.elapsed_seconds);self.assertEqual(len(p.reconstructed_exits),1)
        self.assertEqual(p.observations[-1].exit_kind,'terminal_exit')
        self.assertTrue(p.reconstructed_exits[0].event_ref.endswith(d[2][-1]['id']))
        self.assertIn('Player Off (Permanent)',p.raw_positions[-1]);self.assertEqual(d,original)
        return a,p,v

    def rejects(self,d):
        try:a,p,v=self.inspect(d)
        except SourceSchemaError:return
        self.assertIsNone(v.elapsed_seconds);self.assertFalse(p.reconstructed_exits)

    def test_starter_without_return(self):self.assertEqual(self.accepts(terminal())[2].elapsed_seconds,F('3750.625'))
    def test_substitute_without_return(self):
        d=substitute();d[1][0]['lineup'][0]['positions'][0]['start_reason']='Substitution - On (Tactical)'
        self.assertEqual(self.accepts(terminal(d))[2].elapsed_seconds,F('900.125'))
    def test_temporary_absence_return_then_terminal(self):
        d=terminal();p=d[1][0]['lineup'][0]['positions'];later=copy.deepcopy(p[0])
        p[0].update(to='50:00',to_period=2,end_reason='Player Off (Off Camera)')
        later.update(**{'from':'51:00'},from_period=2,start_reason='Player On (Off Camera)');p.append(later)
        # Keep terminal last only to simplify the immutable UUID assertion.
        end=d[2].pop();end['id']='original-terminal';transition(d[2],'Player Off','00:05:00.125',50,0)
        transition(d[2],'Player On','00:06:00.375',51,0);d[2].append(end)
        self.assertEqual(self.accepts(d)[2].elapsed_seconds,F('3690.375'))
    def test_unsupported_return(self):
        d=terminal();transition(d[2],'Player On','00:16:00.000',61,0);self.rejects(d)
    def test_after_exit_activity(self):
        d=terminal();transition(d[2],'Ball Recovery','00:15:00.126',60,0);self.rejects(d)
    def test_before_entry_activity(self):
        d=terminal(substitute());transition(d[2],'Ball Recovery','00:00:00.000',45,0)
        # Substitute enters at halftime, so use period 1 for the contradiction.
        d[2][-1].update(period=1,minute=0);self.rejects(d)
    def test_after_exit_recipient(self):
        d=terminal();transition(d[2],'Pass','00:16:00.000',61,0,player=dict(id=1000,name='Actor 1000'),
            **{'pass':dict(recipient=dict(id=101,name='Home Player'))});self.rejects(d)
    def test_later_tactical_membership(self):
        d=terminal();e=copy.deepcopy(next(e for e in d[2] if e['id']=='xi-1'))
        e.update(id='later-shift',type=dict(name='Tactical Shift'),period=2,timestamp='00:16:00.000',minute=61);d[2].append(e);self.rejects(d)
    def test_continuing_lineup(self):
        d=terminal();d[1][0]['lineup'][0]['positions'][0].update(to=None,to_period=None,end_reason='Final Whistle');self.rejects(d)
    def test_duplicate_terminal(self):
        d=terminal();e=copy.deepcopy(d[2][-1]);e['id']='duplicate';d[2].append(e);self.rejects(d)
    def test_exit_before_entry(self):
        d=terminal(substitute('00:20:00.000',65));self.rejects(d)
    def test_missing_entry(self):
        d=terminal();next(e for e in d[2] if e['id']=='xi-1')['tactics']['lineup']=[];self.rejects(d)
    def test_missing_lineup(self):
        d=terminal();d[1][0]['lineup'][0]['positions']=[];self.rejects(d)
    def test_wrong_actor(self):
        d=terminal();d[2][-1]['player']=dict(id=1000,name='Actor 1000');self.rejects(d)
    def test_wrong_team(self):
        d=terminal();d[2][-1]['team']=dict(id=2,name='Away');self.rejects(d)
    def test_snapshot_name_conflict(self):
        d=terminal();next(e for e in d[2] if e['id']=='xi-1')['tactics']['lineup'][0]['position']['name']='Left Back';self.rejects(d)
    def test_snapshot_id_conflict(self):
        d=terminal();next(e for e in d[2] if e['id']=='xi-1')['tactics']['lineup'][0]['position']['id']=9;self.rejects(d)
    def test_conflicting_substitution(self):
        d=terminal();transition(d[2],'Substitution','00:16:00.000',61,0,substitution=dict(replacement=dict(id=1000,name='Actor 1000')));self.rejects(d)
    def test_equal_clock_substitution_no_order(self):
        d=terminal();transition(d[2],'Substitution','00:15:00.125',60,0,substitution=dict(replacement=dict(id=1000,name='Actor 1000')));self.rejects(d)
    def test_equal_clock_substitution_indexed(self):
        d=terminal();transition(d[2],'Substitution','00:15:00.125',60,0,substitution=dict(replacement=dict(id=1000,name='Actor 1000')));indexed(d);self.rejects(d)
    def test_one_millisecond_before_exit(self):
        d=terminal();transition(d[2],'Ball Recovery','00:15:00.124',60,0);end=d[2].pop(-2);d[2].append(end);self.accepts(d)
    def test_equal_clock_activity_requires_order(self):
        d=terminal();transition(d[2],'Ball Recovery','00:15:00.125',60,0);self.rejects(d)
    def test_equal_clock_activity_before_exit(self):
        d=terminal();transition(d[2],'Ball Recovery','00:15:00.125',60,0);end=d[2].pop(-2);d[2].append(end);indexed(d);self.accepts(d)
    def test_equal_clock_activity_after_exit(self):
        d=terminal();transition(d[2],'Ball Recovery','00:15:00.125',60,0);indexed(d);self.rejects(d)
    def test_missing_period_boundary(self):
        d=terminal();d[2][:]=[e for e in d[2] if e['id']!='1-1-Half End'];self.rejects(d)
    def test_conflicting_period_boundary(self):
        d=terminal();next(e for e in d[2] if e['id']=='2-1-Half End')['timestamp']='00:47:30.501';self.rejects(d)
    def test_flagged_boundary(self):
        d=terminal();next(e for e in d[2] if e['id']=='2-1-Half End')['half_end']=dict(early_video_end=True);self.rejects(d)
    def test_exact_stoppage_boundary(self):self.accepts(terminal(stamp='00:47:30.500',minute=92,second=30))
    def test_first_period_boundary(self):
        d=terminal(stamp='00:47:30.500',minute=47,second=30)
        d[2][-1]['period']=1;d[1][0]['lineup'][0]['positions'][0]['to_period']=1
        self.assertEqual(self.accepts(d)[2].elapsed_seconds,F('2850.5'))
    def test_one_millisecond_after_boundary(self):self.rejects(terminal(stamp='00:47:30.501',minute=92,second=30))
    def test_dismissal_before_exit(self):
        d=terminal();card(d,stamp='00:14:00.000',minute=59);self.rejects(d)
    def test_dismissal_after_exit(self):
        d=terminal();card(d,stamp='00:16:00.000',minute=61);self.rejects(d)
    def test_dismissal_equal_clock(self):
        d=terminal();card(d,stamp='00:15:00.125',minute=60);self.rejects(d)
    def test_bench_card_not_automatically_waived(self):
        d=terminal();card(d,stamp='00:16:00.000',minute=61)['position']=dict(id=0,name='Substitute');self.rejects(d)
    def test_temporary_absence_without_return(self):
        d=terminal();transition(d[2],'Player Off','00:05:00.000',50,0);self.rejects(d)
    def test_overlap(self):
        d=terminal();d[1][0]['lineup'][0]['positions'].append(copy.deepcopy(d[1][0]['lineup'][0]['positions'][0]));self.rejects(d)
    def test_reversed_interval(self):
        d=terminal();d[1][0]['lineup'][0]['positions'][0].update(**{'from':'70:00'},from_period=2);self.rejects(d)
    def test_backwards_indices(self):
        d=terminal();indexed(d);d[2][-1]['index']=0;self.rejects(d)
    def test_terminal_cannot_resume_at_core_layer(self):
        a,p,v=self.inspect(terminal());s=p.observations[-1]
        later=replace(s,observation_id='later',start=Clock(2,1000,('later',)),end=Clock(2,1100,('end',)),entry_kind='substitution',exit_kind='substitution')
        result=validate_participation(p.context,[s,later],clock_policy=a.policy,period_boundaries=a.boundaries)
        self.assertIsNone(result.elapsed_seconds)
    def test_no_proof_for_ordinary_accepted_appearance(self):
        a,p,v=self.inspect(complete());self.assertIsNotNone(v.elapsed_seconds);self.assertFalse(p.reconstructed_exits)
    def test_independent_terminal_geometry_without_decoder(self):
        from collections import defaultdict
        from src.independent_source_checks import exposure, boundaries
        from scripts import decoder_fix_independent as raw
        from scripts import off_field_card_independent as oracle
        d=terminal();index=defaultdict(list)
        for e in d[2]:index[e['period'],e['minute'],e['second'],e['team']['id'],e['type']['name']].append(e)
        with patch('src.statsbomb_participation._source_backed_terminal_exit',side_effect=AssertionError('decoder called')):
            bounds,issues,_=raw.boundaries(d[2],{1,2})
            event=oracle.reconstruct(101,1,d[1][0]['lineup'][0],d[2],bounds,issues)
            lineup=exposure(d[1][0]['lineup'][0]['positions'],101,1,index,boundaries(d[2],{1,2}))
        self.assertEqual(event['issues'],[]);self.assertEqual(lineup[0],event['seconds'])
        self.assertEqual(oracle.union(lineup[2],bounds),oracle.union(event['intervals'],bounds))
    def test_permanent_geometry_cannot_use_temporary_event(self):
        from collections import defaultdict
        from src.independent_source_checks import exposure, boundaries
        d=terminal();d[2][-1]['player_off']['permanent']=False;index=defaultdict(list)
        for e in d[2]:index[e['period'],e['minute'],e['second'],e['team']['id'],e['type']['name']].append(e)
        self.assertIsNone(exposure(d[1][0]['lineup'][0]['positions'],101,1,index,boundaries(d[2],{1,2})))
