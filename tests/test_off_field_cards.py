"""Synthetic source-backed off-field proofs and fail-closed negative controls."""
import copy
from dataclasses import asdict
from fractions import Fraction as F
import json
import unittest
from unittest.mock import patch

from test_statsbomb_participation import fixture,run,transition
from src.statsbomb_participation import SourceSchemaError
from src.source_reconstruction import appearance_rows
from scripts.source_verification_batch import payload
from scripts import off_field_card_independent as independent
from scripts import decoder_fix_independent as raw


def complete():
    d=fixture()
    d[0][0]['competition']['competition_id']=1;d[0][0]['season']['season_id']=27
    for team in d[1]:
        tid=team['team_id'];xi=next(e for e in d[2] if e['type']['name']=='Starting XI' and e['team']['id']==tid)
        for n in range(10):
            pid=tid*1000+n;name=f'Actor {pid}'
            p=copy.deepcopy(team['lineup'][0]);p.update(player_id=pid,player_name=name)
            team['lineup'].append(p)
            xi['tactics']['lineup'].append(dict(player=dict(id=pid,name=name),position=dict(id=3,name='Right Center Back')))
    return d


def bench(d):
    d[1][0]['lineup'].append(dict(player_id=999,player_name='Bench',positions=[]))
    return d


def card(d,pid=101,kind='Red Card',stamp='00:40:00.000',minute=85,second=0):
    transition(d[2],'Bad Behaviour',stamp,minute,second,
        player=dict(id=pid,name='Bench' if pid==999 else 'Home Player'),
        bad_behaviour=dict(card=dict(name=kind)),
        position=dict(id=0,name='Substitute') if pid==999 else dict(id=3,name='Right Center Back'))
    return d[2][-1]


def substituted():
    d=bench(complete());d[1][0]['lineup'][0]['positions'][0].update(to='60:00',to_period=2,end_reason='Substitution - Off (Tactical)')
    transition(d[2],'Substitution','00:15:00.125',60,0,substitution=dict(replacement=dict(id=999,name='Bench')))
    return d


def indexed(d,card_first=False):
    order=sorted(d[2],key=lambda e:(e['period'],raw.clock(dict(e))[1],
        0 if e['type']['name']==('Bad Behaviour' if card_first else 'Substitution') else 1))
    for i,e in enumerate(order,1):e['index']=i


class OffFieldCardTests(unittest.TestCase):
    def inspect(self,d,pid=101):
        a=run(d);p=next(p for p in a.players if p.context.player_id==pid)
        r=next(r for r in a.validate() if r.context.player_id==pid)
        es=copy.deepcopy(d[2]);bounds,issues,_=raw.boundaries(es,{1,2})
        player=next(p for t in d[1] for p in t['lineup'] if p['player_id']==pid)
        oracle=independent.reconstruct(pid,p.team_id,player,es,bounds,issues)
        return a,p,r,oracle

    def proves(self,d,state,pid=101):
        a,p,r,o=self.inspect(d,pid)
        self.assertEqual([c.state for c in p.off_field_discipline],[state])
        self.assertEqual([c['state'] for c in o['off_field_discipline']],[state])
        self.assertEqual(o['issues'],[])
        self.assertEqual(r.elapsed_seconds,o['seconds'])
        self.assertTrue(all(c.evidence_refs for c in p.off_field_discipline))
        return a,p,r,o

    def withholds(self,d,pid=101):
        a,p,r,o=self.inspect(d,pid)
        self.assertFalse(p.off_field_discipline)
        self.assertFalse(o['off_field_discipline'])
        self.assertIsNone(r.elapsed_seconds)
        return a,p,r,o

    def test_unused_red_card_is_not_an_appearance(self):
        d=bench(complete());card(d,999)
        _,p,r,o=self.proves(d,'UNUSED_ROSTER',999)
        self.assertFalse(p.observations or p.source_checks)
        self.assertFalse(o['active']);self.assertIsNone(r.elapsed_seconds)

    def test_unused_second_yellow_is_not_an_appearance(self):
        d=bench(complete());card(d,999,'Second Yellow')
        self.proves(d,'UNUSED_ROSTER',999)

    def test_post_substitution_red_card_preserves_exact_interval(self):
        d=substituted();card(d)
        self.assertEqual(self.proves(d,'AFTER_SUBSTITUTION')[2].elapsed_seconds,F('3750.625'))

    def test_post_substitution_second_yellow_preserves_exact_interval(self):
        d=substituted();card(d,kind='Second Yellow')
        self.proves(d,'AFTER_SUBSTITUTION')

    def absence_before_substitution(self,off,on):
        d=substituted();p=d[1][0]['lineup'][0];end=copy.deepcopy(p['positions'][0])
        p['positions'][0].update(to='50:00',to_period=2,end_reason=off)
        end.update(**{'from':'51:00'},from_period=2,start_reason=on);p['positions'].append(end)
        transition(d[2],'Player Off','00:05:00.125',50,0);transition(d[2],'Player On','00:06:00.375',51,0);card(d)
        return d

    def test_post_substitution_card_excludes_temporary_absence(self):
        d=self.absence_before_substitution('Player Off','Player On')
        self.assertEqual(self.proves(d,'AFTER_SUBSTITUTION')[2].elapsed_seconds,F('3690.375'))

    def test_both_off_camera_aliases_survive_off_field_fix(self):
        d=self.absence_before_substitution('Player Off (Off Camera)','Player On (Off Camera)')
        self.assertEqual(self.proves(d,'AFTER_SUBSTITUTION')[2].elapsed_seconds,F('3690.375'))

    def test_active_red_card_continuing_lineup_still_conflicts(self):
        d=complete();card(d)
        r=self.withholds(d)[2]
        self.assertIn('participation_after_permanent_exit',{i.code for i in r.issues})

    def test_active_second_yellow_still_conflicts(self):
        d=complete();card(d,kind='Second Yellow');self.withholds(d)

    def test_foul_committed_card_after_substitution_is_playing_conflict(self):
        d=substituted();e=card(d);e['type']['name']='Foul Committed';e['foul_committed']=e.pop('bad_behaviour')
        self.withholds(d)

    def test_card_before_verified_entry_is_not_unused_roster(self):
        d=substituted();p=d[1][0]['lineup'][-1]
        stint=copy.deepcopy(d[1][0]['lineup'][0]['positions'][0]);stint.update(**{'from':'60:00','to':None},from_period=2,to_period=None,start_reason='Substitution - On (Tactical)',end_reason='Final Whistle')
        p['positions']=[stint];card(d,999,stamp='00:05:00.000',minute=50)
        self.withholds(d,999)

    def test_card_during_temporary_absence_stays_unresolved(self):
        d=complete();p=d[1][0]['lineup'][0];p['positions'][0].update(to='60:00',to_period=2,end_reason='Player Off')
        second=copy.deepcopy(p['positions'][0]);second.update(**{'from':'65:00','to':None},from_period=2,to_period=None,start_reason='Player On',end_reason='Final Whistle');p['positions'].append(second)
        transition(d[2],'Player Off','00:15:00.125',60,0);transition(d[2],'Player On','00:20:00.125',65,0)
        card(d,stamp='00:17:00.000',minute=62);self.withholds(d)

    def test_missing_kickoff_coverage_does_not_prove_unused(self):
        d=bench(complete());card(d,999)
        d[2][:]=[e for e in d[2] if e['id']!='xi-1'];self.withholds(d,999)

    def test_incomplete_xi_does_not_prove_unused(self):
        d=bench(complete());card(d,999)
        next(e for e in d[2] if e['id']=='xi-1')['tactics']['lineup'].pop();self.withholds(d,999)

    def test_duplicate_xi_actor_blocks_unused_proof(self):
        d=bench(complete());card(d,999)
        xi=next(e for e in d[2] if e['id']=='xi-1');xi['tactics']['lineup'].append(copy.deepcopy(xi['tactics']['lineup'][0]))
        self.withholds(d,999)

    def test_unused_card_with_conflicting_index_order_is_unresolved(self):
        d=bench(complete());e=card(d,999);indexed(d)
        xi=next(e for e in d[2] if e['id']=='xi-1');xi['index'],e['index']=e['index'],xi['index']
        self.withholds(d,999)

    def test_flagged_video_boundary_stays_unresolved(self):
        d=bench(complete());card(d,999)
        next(e for e in d[2] if e['type']['name']=='Half End')['half_end']={'early_video_end':True}
        self.withholds(d,999)

    def test_explicit_active_card_position_blocks_unused_proof(self):
        d=bench(complete());e=card(d,999);e['position']={'id':3,'name':'Right Center Back'}
        self.withholds(d,999)

    def test_unused_actor_activity_blocks_off_field_proof(self):
        d=bench(complete());card(d,999)
        transition(d[2],'Pass','00:30:00.000',75,0,player=dict(id=999,name='Bench'),**{'pass':{}})
        self.withholds(d,999)

    def test_unused_pass_recipient_blocks_off_field_proof(self):
        d=bench(complete());card(d,999)
        transition(d[2],'Pass','00:30:00.000',75,0,**{'pass':{'recipient':{'id':999,'name':'Bench'}}})
        self.withholds(d,999)

    def test_equal_clock_card_after_indexed_substitution(self):
        d=substituted();card(d,stamp='00:15:00.125',minute=60);indexed(d)
        self.proves(d,'AFTER_SUBSTITUTION')

    def test_equal_clock_card_before_indexed_substitution_stays_active(self):
        d=substituted();card(d,stamp='00:15:00.125',minute=60);indexed(d,True)
        self.withholds(d)

    def test_equal_clock_without_indices_is_ambiguous(self):
        d=substituted();card(d,stamp='00:15:00.125',minute=60);self.withholds(d)

    def test_one_millisecond_after_substitution(self):
        d=substituted();card(d,stamp='00:15:00.126',minute=60);self.proves(d,'AFTER_SUBSTITUTION')

    def test_one_millisecond_before_substitution(self):
        d=substituted();card(d,stamp='00:15:00.124',minute=60);self.withholds(d)

    def test_conflicting_source_index_clock_order(self):
        d=substituted();card(d);indexed(d)
        e=next(e for e in d[2] if e['type']['name']=='Bad Behaviour');sub=next(e for e in d[2] if e['type']['name']=='Substitution')
        e['index'],sub['index']=sub['index'],e['index'];self.withholds(d)

    def test_missing_substitution_cannot_be_inferred(self):
        d=substituted();card(d);d[2][:]=[e for e in d[2] if e['type']['name']!='Substitution'];self.withholds(d)

    def test_duplicate_source_entry_stays_unresolved(self):
        d=substituted();card(d);xi=copy.deepcopy(next(e for e in d[2] if e['id']=='xi-1'));xi['id']='duplicate-xi';d[2].append(xi)
        self.withholds(d)

    def test_return_after_substitution_stays_conflicting(self):
        d=substituted();card(d);transition(d[2],'Player On','00:45:00.000',90,0);self.withholds(d)

    def test_card_with_conflicting_stable_id_rejects_schema(self):
        d=substituted();e=card(d);e['player']['id']=888888
        with self.assertRaises(SourceSchemaError):run(d)

    def test_card_with_conflicting_source_name_rejects_schema(self):
        d=substituted();e=card(d);e['player']['name']='Other person'
        with self.assertRaises(SourceSchemaError):run(d)

    def test_source_activity_after_claimed_exit_stays_conflicting(self):
        d=substituted();card(d);transition(d[2],'Pass','00:30:00.000',75,0,**{'pass':{}})
        self.withholds(d)

    def test_post_exit_snapshot_blocks_off_field_proof(self):
        d=substituted();card(d);e=copy.deepcopy(next(e for e in d[2] if e['id']=='xi-1'))
        e.update(id='later-snapshot',period=2,timestamp='00:30:00.000',minute=75,second=0);e['type']['name']='Tactical Shift';d[2].append(e)
        self.withholds(d)

    def test_unrepresented_temporary_exit_is_not_cleared(self):
        d=substituted();card(d)
        transition(d[2],'Player Off','00:05:00.000',50,0);transition(d[2],'Player On','00:05:00.000',50,0);indexed(d)
        self.withholds(d)

    def test_disciplinary_uuid_provenance_and_inputs_survive(self):
        d=substituted();e=card(d);before=copy.deepcopy(d);a,p,_,_=self.proves(d,'AFTER_SUBSTITUTION')
        self.assertEqual(d,before);self.assertTrue(p.off_field_discipline[0].event_ref.endswith(e['id']))
        self.assertTrue(all('sha256=' in ref for ref in a.provenance))

    def test_independent_checker_does_not_call_production_decision(self):
        d=substituted();e=card(d);events=copy.deepcopy(d[2]);bounds,issues,_=raw.boundaries(events,{1,2})
        with patch('src.statsbomb_participation._off_field_discipline',side_effect=AssertionError('production decision called')):
            result=independent.reconstruct(101,1,d[1][0]['lineup'][0],events,bounds,issues)
        self.assertEqual(result['issues'],[])
        self.assertEqual(result['seconds'],F('3750.625'))
        self.assertIn(e['id'],result['event_ids'])

    def test_reconstructed_bench_row_has_no_zero_minute_appearance(self):
        d=bench(complete());card(d,999);a,_,_,_=self.proves(d,'UNUSED_ROSTER',999)
        serialize=lambda v:json.loads(payload(asdict(v) if hasattr(v,'__dataclass_fields__') else [asdict(x) for x in v]))
        report=dict(match_id=10,competition_name='Invented League',season_name='2015/2016',artifact_validation='BYTE_BOUND_SOURCE_SCHEMA_REVIEWED',production_certified=False,
            verification_key='synthetic-private',players=[dict(player=serialize(p),validation=serialize(v)) for p,v in zip(a.players,a.validate())],boundaries=serialize(a.boundaries))
        row=next(r for r in appearance_rows(report,d[0][0],d[1]) if r['player_id']==999)
        self.assertFalse(row['active_appearance']);self.assertEqual(row['participation_status'],'BENCH_NO_ASSERTED_APPEARANCE')
        self.assertIsNone(row['validated_elapsed_seconds']);self.assertIsNone(row['supported_minutes'])
        self.assertEqual(len(row['off_field_discipline']),1)


if __name__=='__main__':unittest.main()
