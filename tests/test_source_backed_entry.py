"""First-shift entry proof: exact source assertions, never inferred playing time."""
import copy
import json
import unittest
from unittest.mock import patch

from test_statsbomb_participation import run, transition
from test_off_field_cards import complete, indexed
from src.statsbomb_participation import SourceSchemaError
from scripts import decoder_fix_independent as raw
from scripts import off_field_card_independent as independent


def starter():
    d=complete();d[1][0]['lineup'][0]['positions'][0]['start_reason']='Tactical Shift'
    xi=next(e for e in d[2] if e['id']=='xi-1')
    shift=copy.deepcopy(xi);shift['id']='initial-shift';shift['type']['name']='Tactical Shift'
    d[2].append(shift)
    return d


def substitute(stamp='00:00:00.000',minute=45,second=0):
    d=starter();p=d[1][0]['lineup'][0]
    xi=next(e for e in d[2] if e['id']=='xi-1')
    xi['tactics']['lineup'][0]=copy.deepcopy(xi['tactics']['lineup'][1])
    xi['tactics']['lineup'][0]['player']=dict(id=999,name='Outgoing')
    s=copy.deepcopy(p['positions'][0]);s['start_reason']='Starting XI'
    s.update(to=f'{minute:02}:{second:02}',to_period=2,end_reason='Substitution - Off (Tactical)')
    d[1][0]['lineup'].append(dict(player_id=999,player_name='Outgoing',positions=[s]))
    p['positions'][0].update(**{'from':f'{minute:02}:{second:02}'},from_period=2)
    shift=next(e for e in d[2] if e['id']=='initial-shift')
    shift.update(period=2,timestamp=stamp,minute=minute,second=second)
    # Only the incoming actor is a positional assertion at this later clock.
    shift['tactics']['lineup']=shift['tactics']['lineup'][:1]
    transition(d[2],'Substitution',stamp,minute,second,player=dict(id=999,name='Outgoing'),
               substitution=dict(replacement=dict(id=101,name='Home Player')))
    return d


class SourceBackedEntryTests(unittest.TestCase):
    def inspect(self,d):
        a=run(d);p=next(p for p in a.players if p.context.player_id==101)
        v=next(v for v in a.validate() if v.context.player_id==101)
        return p,v

    def accepts(self,d,kind):
        original=copy.deepcopy(d);p,v=self.inspect(d)
        self.assertIsNotNone(v.elapsed_seconds);self.assertEqual(len(p.reconstructed_entries),1)
        proof=p.reconstructed_entries[0];self.assertEqual(proof.entry_kind,kind)
        self.assertIn(proof.entry_ref,p.observations[0].start.evidence_refs)
        self.assertIn(proof.shift_ref,p.observations[0].start.evidence_refs)
        self.assertEqual(json.loads(p.raw_positions[0])['start_reason'],'Tactical Shift')
        es=copy.deepcopy(d[2]);bounds,issues,_=raw.boundaries(es,{1,2})
        o=independent.reconstruct(101,1,d[1][0]['lineup'][0],es,bounds,issues)
        self.assertEqual(o['issues'],[]);self.assertEqual(o['seconds'],v.elapsed_seconds)
        self.assertEqual(independent.union(o['intervals'],bounds),independent.union(o['lineup_intervals'],bounds))
        self.assertEqual(d,original)
        return p,v

    def rejects(self,d):
        try:p,v=self.inspect(d)
        except SourceSchemaError:return
        self.assertFalse(p.reconstructed_entries);self.assertIsNone(v.elapsed_seconds)

    def test_original_xi_and_exact_shift(self):self.accepts(starter(),'starter')
    def test_incoming_substitution(self):self.accepts(substitute('00:15:00.125',60),'substitution')
    def test_halftime_substitution(self):self.accepts(substitute(),'substitution')
    def test_equal_clock_indexed_transition(self):
        d=substitute();indexed(d);self.accepts(d,'substitution')
    def test_production_proof_does_not_drive_independent_oracle(self):
        d=starter();es=copy.deepcopy(d[2]);b,i,_=raw.boundaries(es,{1,2})
        with patch('src.statsbomb_participation._source_backed_entry',side_effect=AssertionError('production called')):
            o=independent.reconstruct(101,1,d[1][0]['lineup'][0],es,b,i)
        self.assertEqual(o['issues'],[]);self.assertIsNotNone(o['seconds'])
    def test_one_millisecond_mismatch(self):
        d=starter();next(e for e in d[2] if e['id']=='initial-shift')['timestamp']='00:00:00.001';self.rejects(d)
    def test_substitution_one_millisecond_mismatch(self):
        d=substitute();next(e for e in d[2] if e['type']['name']=='Substitution')['timestamp']='00:00:00.001';self.rejects(d)
    def test_no_original_entry(self):
        d=substitute();d[2][:]=[e for e in d[2] if e['type']['name']!='Substitution'];self.rejects(d)
    def test_wrong_incoming_player(self):
        d=substitute();next(e for e in d[2] if e['type']['name']=='Substitution')['substitution']['replacement']=dict(id=1000,name='Actor 1000');self.rejects(d)
    def test_wrong_team(self):
        d=starter();next(e for e in d[2] if e['id']=='initial-shift')['team']=dict(id=2,name='Away');self.rejects(d)
    def test_wrong_original_position_name(self):
        d=starter();next(e for e in d[2] if e['id']=='xi-1')['tactics']['lineup'][0]['position']['name']='Left Back';self.rejects(d)
    def test_wrong_original_position_id(self):
        d=starter();next(e for e in d[2] if e['id']=='xi-1')['tactics']['lineup'][0]['position']['id']=9;self.rejects(d)
    def test_wrong_shift_position(self):
        d=starter();next(e for e in d[2] if e['id']=='initial-shift')['tactics']['lineup'][0]['position']['id']=9;self.rejects(d)
    def test_duplicate_xi(self):
        d=starter();e=copy.deepcopy(next(e for e in d[2] if e['id']=='xi-1'));e['id']='duplicate-xi';d[2].append(e);self.rejects(d)
    def test_duplicate_substitution(self):
        d=substitute();e=copy.deepcopy(d[2][-1]);e['id']='duplicate-sub';d[2].append(e);self.rejects(d)
    def test_conflicting_entry_times(self):
        d=substitute();e=copy.deepcopy(d[2][-1]);e.update(id='later-sub',timestamp='00:00:01.000',second=1);d[2].append(e);self.rejects(d)
    def test_duplicate_shift(self):
        d=starter();e=copy.deepcopy(d[2][-1]);e['id']='duplicate-shift';d[2].append(e);self.rejects(d)
    def test_duplicate_snapshot_actor(self):
        d=starter();e=next(e for e in d[2] if e['id']=='initial-shift');e['tactics']['lineup'].append(copy.deepcopy(e['tactics']['lineup'][0]));self.rejects(d)
    def test_overlap(self):
        d=starter();d[1][0]['lineup'][0]['positions'].append(copy.deepcopy(d[1][0]['lineup'][0]['positions'][0]));self.rejects(d)
    def test_reversed_period(self):
        d=substitute();d[1][0]['lineup'][0]['positions'][0].update(to='47:30',to_period=1);self.rejects(d)
    def test_flagged_boundary(self):
        d=starter();next(e for e in d[2] if e['id']=='2-1-Half End')['half_end']={'early_video_end':True};self.rejects(d)
    def test_conflicting_boundary(self):
        d=starter();next(e for e in d[2] if e['id']=='2-1-Half End').update(timestamp='00:47:31.000',second=31);self.rejects(d)
    def test_later_contradictory_snapshot(self):
        d=starter();e=copy.deepcopy(d[2][-1]);e.update(id='later-shift',period=2,timestamp='00:10:00.000',minute=55);e['tactics']['lineup'][0]['position']['name']='Left Back';d[2].append(e);self.rejects(d)
    def test_later_contradictory_snapshot_id(self):
        d=starter();e=copy.deepcopy(d[2][-1]);e.update(id='later-shift',period=2,timestamp='00:10:00.000',minute=55);e['tactics']['lineup'][0]['position']['id']=9;d[2].append(e);self.rejects(d)
    def test_active_dismissal_continuing_lineup(self):
        d=starter();transition(d[2],'Bad Behaviour','00:10:00.000',55,0,bad_behaviour=dict(card=dict(name='Red Card')));self.rejects(d)
    def test_substitution_continuing_lineup(self):
        d=starter();transition(d[2],'Substitution','00:10:00.000',55,0,substitution=dict(replacement=dict(id=1000,name='Actor 1000')));self.rejects(d)
    def test_permanent_exit_continuing_lineup(self):
        d=starter();transition(d[2],'Player Off','00:10:00.000',55,0,player_off=dict(permanent=True));self.rejects(d)
    def test_backwards_original_indices(self):
        d=substitute();indexed(d)
        # Unique indices but the later actor snapshot precedes original XI.
        for i,e in enumerate(sorted(d[2],key=lambda e:(e['id']!='initial-shift',e.get('index',0))),1):e['index']=i
        self.rejects(d)
    def test_previously_accepted_unchanged(self):
        d=complete();p,v=self.inspect(d);self.assertFalse(p.reconstructed_entries);self.assertIsNotNone(v.elapsed_seconds)
    def test_missing_entry_identity(self):
        d=substitute();del d[2][-1]['substitution']['replacement']['id'];self.rejects(d)
