"""Synthetic realistic open-data schema regression tests; no real certification."""
import copy
from dataclasses import replace
from decimal import Decimal
import json
import unittest

from src.statsbomb_participation import SourceDocument, SourceSchemaError, adapt_match
from src.participation_intervals import VALID, INCOMPLETE, CONFLICT


def source(value, name):
    return SourceDocument(json.dumps(value, sort_keys=True).encode(), "synthetic/" + name, "test-v1")


def fixture():
    match = [{"match_id": 10, "competition": {"competition_name": "Invented League"},
              "season": {"season_name": "2015/2016"},
              "home_team": {"home_team_id": 1, "home_team_name": "Home"},
              "away_team": {"away_team_id": 2, "away_team_name": "Away"}}]
    stint = dict(position_id=3, position="Right Center Back", **{"from": "00:00", "to": None},
                 from_period=1, to_period=None, start_reason="Starting XI", end_reason="Final Whistle")
    lineups = [dict(team_id=i, team_name=n, lineup=[dict(player_id=i+100, player_name=n+" Player", positions=[copy.deepcopy(stint)])]) for i,n in [(1,"Home"),(2,"Away")]]
    events = []
    for period in (1, 2):
        for i, name in [(1,"Home"),(2,"Away")]:
            for typ, timestamp, minute, second in [("Half Start","00:00:00.000",0 if period==1 else 45,0),
                                                    ("Half End","00:47:30.500",47 if period==1 else 92,30)]:
                events.append(dict(id=f"{period}-{i}-{typ}",period=period,timestamp=timestamp,minute=minute,second=second,
                                   type=dict(name=typ),team=dict(id=i,name=name)))
            if period == 1:
                e=dict(id=f"xi-{i}", period=1,timestamp="00:00:00.000",minute=0,second=0,
                       type=dict(name="Starting XI"),team=dict(id=i,name=name),
                       tactics=dict(lineup=[dict(player=dict(id=i+100,name=name+" Player"),position=dict(id=3,name="Right Center Back"))]))
                events.append(e)
    return match, lineups, events


def run(data):
    return adapt_match(10,*(source(d,n) for d,n in zip(data,["matches","lineups","events"])),
                       clock_document_reference="synthetic documented clock convention")


def transition(events, typ, stamp, minute, second, **extra):
    e=dict(id=f"transition-{len(events)}",period=2,timestamp=stamp,minute=minute,second=second,
           type=dict(name=typ),team=dict(id=1,name="Home"),player=dict(id=101,name="Home Player"))
    e.update(extra); events.append(e)


class AdapterTests(unittest.TestCase):
    def test_cross_period_stoppage_exact(self):
        a=run(fixture()); r=a.validate()[0]
        self.assertEqual(r.status,VALID)
        self.assertEqual(r.elapsed_seconds,Decimal('5701.000'))
        self.assertFalse(r.source_independently_verified)
        self.assertFalse(r.publication_authorized)

    def test_input_immutability_and_determinism(self):
        data=fixture(); before=copy.deepcopy(data)
        self.assertEqual(run(data),run(data)); self.assertEqual(data,before)

    def test_provenance_byte_binding(self):
        d=source([],"a"); changed=replace(d,raw=b'[ ]')
        self.assertNotEqual(d.fingerprint,changed.fingerprint)
        a=run(fixture()); self.assertTrue(all('sha256=' in p for p in a.provenance))
        self.assertIn('from_period',a.players[0].raw_positions[0])

    def test_bench_is_not_an_appearance(self):
        d=fixture();d[1][0]['lineup'].append(dict(player_id=999,player_name='Bench',positions=[]))
        a=run(d);r=next(r for r in a.validate() if r.context.player_id==999)
        self.assertEqual(r.status,INCOMPLETE);self.assertIsNone(r.elapsed_seconds)

    def test_missing_final_whistle(self):
        d=fixture();d[2][:]=[e for e in d[2] if not(e['period']==2 and e['type']['name']=='Half End')]
        r=run(d).validate()[0];self.assertEqual(r.status,INCOMPLETE);self.assertIsNone(r.elapsed_seconds)

    def test_missing_first_period_end(self):
        d=fixture();d[2][:]=[e for e in d[2] if not(e['period']==1 and e['type']['name']=='Half End')]
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_disagreeing_team_whistles(self):
        d=fixture();e=next(e for e in d[2] if e['period']==2 and e['type']['name']=='Half End')
        e.update(timestamp='00:47:31.000',second=31)
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_one_team_whistle_is_withheld(self):
        d=fixture();d[2][:]=[e for e in d[2] if e['id']!='2-1-Half End']
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_temporary_absence_and_post90(self):
        d=fixture();s=d[1][0]['lineup'][0]['positions'][0]
        s.update(to='91:00',to_period=2,end_reason='Player Off')
        t=copy.deepcopy(s);t.update(**{'from':'92:00','to':None},from_period=2,to_period=None,start_reason='Player On',end_reason='Final Whistle')
        d[1][0]['lineup'][0]['positions'].append(t)
        transition(d[2],'Player Off','00:46:00.000',91,0)
        transition(d[2],'Player On','00:47:00.000',92,0)
        r=run(d).validate()[0]
        self.assertEqual(r.status,VALID);self.assertEqual(r.elapsed_seconds,Decimal('5641'))
        self.assertTrue(r.gaps[0].supported_temporary_absence)
        self.assertEqual(r.gaps[0].elapsed_seconds,60)

    def test_missing_return_event(self):
        d=fixture();s=d[1][0]['lineup'][0]['positions'][0]
        s.update(**{'from':'92:00'},from_period=2,start_reason='Player On')
        self.assertEqual(run(d).validate()[0].status,INCOMPLETE)

    def test_unknown_reason(self):
        d=fixture();d[1][0]['lineup'][0]['positions'][0]['start_reason']='Undocumented'
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_identity_conflicts(self):
        for mutate in [lambda d:d[1][0].update(team_name='Wrong'),
                       lambda d:next(e for e in d[2] if 'tactics' in e)['tactics']['lineup'][0]['player'].update(id=777),
                       lambda d:next(e for e in d[2] if 'tactics' in e)['tactics']['lineup'][0]['player'].update(name='Wrong'),
                       lambda d:d[1][1]['lineup'][0].update(player_id=101)]:
            with self.subTest(mutate=mutate):
                d=fixture();mutate(d)
                with self.assertRaises(SourceSchemaError):run(d)

    def test_exact_ids(self):
        for value in [True,101.0,'101',0,2**63]:
            d=fixture();d[1][0]['lineup'][0]['player_id']=value
            with self.subTest(value=value),self.assertRaises(SourceSchemaError):run(d)

    def test_duplicate_event(self):
        d=fixture();d[2].append(copy.deepcopy(d[2][0]))
        with self.assertRaises(SourceSchemaError):run(d)

    def test_missing_schema_fields(self):
        for key in ['positions','player_id','player_name']:
            d=fixture();del d[1][0]['lineup'][0][key]
            with self.subTest(key=key),self.assertRaises(SourceSchemaError):run(d)

    def test_malformed_clocks(self):
        for value in ['bad','00:60:00.000','00:00:60.000',None]:
            d=fixture();d[2][0]['timestamp']=value
            with self.subTest(value=value),self.assertRaises(SourceSchemaError):run(d)

    def test_clock_disagreement(self):
        d=fixture();d[2][0]['minute']=1
        with self.assertRaises(SourceSchemaError):run(d)

    def test_extra_period_rejected(self):
        d=fixture();d[2][0]['period']=3
        with self.assertRaises(SourceSchemaError):run(d)

    def test_malformed_lineup_clock(self):
        d=fixture();d[1][0]['lineup'][0]['positions'][0]['from']='0:99'
        with self.assertRaises(SourceSchemaError):run(d)

    def test_explicit_final_whistle_conflict(self):
        d=fixture();d[1][0]['lineup'][0]['positions'][0].update(to='90:00',to_period=2)
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_source_json_validation(self):
        for raw in [b'{}',b'[{"a":1,"a":2}]',b'[NaN]']:
            with self.subTest(raw=raw),self.assertRaises(SourceSchemaError):
                SourceDocument(raw,'synthetic','v1').records()

    def test_match_not_in_inventory(self):
        d=fixture();d[0][0]['match_id']=11
        with self.assertRaises(SourceSchemaError):run(d)

    def test_position_change_and_overlap(self):
        d=fixture();s=d[1][0]['lineup'][0]['positions'][0]
        s.update(to='60:00',to_period=2,end_reason='Tactical Shift')
        t=copy.deepcopy(s);t.update(**{'from':'60:00','to':None},from_period=2,to_period=None,start_reason='Tactical Shift',end_reason='Final Whistle')
        d[1][0]['lineup'][0]['positions'].append(t)
        transition(d[2],'Tactical Shift','00:15:00.125',60,0,tactics=dict(lineup=[dict(player=dict(id=101,name='Home Player'),position=dict(id=3,name='Right Center Back'))]))
        self.assertEqual(run(d).validate()[0].status,VALID)
        d[1][0]['lineup'][0]['positions'].append(copy.deepcopy(t))
        self.assertEqual(run(d).validate()[0].status,CONFLICT)

    def test_substitution_identity(self):
        d=fixture();s=d[1][0]['lineup'][0]['positions'][0]
        s.update(to='60:00',to_period=2,end_reason='Substitution - Off (Tactical)')
        replacement=copy.deepcopy(s);replacement.update(**{'from':'60:00','to':None},from_period=2,to_period=None,start_reason='Substitution - On (Tactical)',end_reason='Final Whistle')
        d[1][0]['lineup'].append(dict(player_id=999,player_name='Replacement',positions=[replacement]))
        transition(d[2],'Substitution','00:15:00.125',60,0,substitution=dict(replacement=dict(id=999,name='Replacement')))
        a=run(d);r=next(r for r in a.validate() if r.context.player_id==999)
        self.assertEqual(r.status,VALID);self.assertEqual(r.elapsed_seconds,Decimal('1950.375'))

    def test_reversed_periods_preserved(self):
        d=fixture();s=d[1][0]['lineup'][0]['positions'][0]
        s.update(**{'from':'45:00','to':'46:00'},from_period=2,to_period=1,start_reason='Player On',end_reason='Player Off')
        r=run(d).validate()[0]
        self.assertEqual(r.status,CONFLICT)
        self.assertIn('reversed_period_order',{i.code for i in r.issues})

    def test_permanent_exit_not_a_temporary_absence(self):
        d=fixture();s=d[1][0]['lineup'][0]['positions'][0]
        s.update(to='60:00',to_period=2,end_reason='Player Off')
        transition(d[2],'Player Off','00:15:00.000',60,0,player_off=dict(permanent=True))
        self.assertEqual(run(d).validate()[0].status,INCOMPLETE)

    def test_ambiguous_transition_withheld(self):
        d=fixture();s=d[1][0]['lineup'][0]['positions'][0]
        s.update(to='60:00',to_period=2,end_reason='Player Off')
        transition(d[2],'Player Off','00:15:00.100',60,0)
        transition(d[2],'Player Off','00:15:00.200',60,0)
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_missing_position_withheld(self):
        d=fixture();d[1][0]['lineup'][0]['positions'][0].pop('position')
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_record_order_not_used_as_clock(self):
        d=fixture();a=run(d);d[2].reverse()
        b=run(d)
        self.assertEqual([r.elapsed_seconds for r in a.validate()], [r.elapsed_seconds for r in b.validate()])
        self.assertNotEqual(a.provenance,b.provenance)

    def test_incomplete_video_boundaries_withheld(self):
        # Documented provider boundary conditions, synthetic failure records.
        for kind, field, flag in [('Half End','half_end','early_video_end'),
                                  ('Half End','half_end','match_suspended'),
                                  ('Half Start','half_start','late_video_start')]:
            d=fixture();e=next(e for e in d[2] if e['period']==2 and e['type']['name']==kind)
            e[field]={flag:True}
            with self.subTest(flag=flag):self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_unknown_boundary_attributes_withheld(self):
        d=fixture();d[2][0]['half_start']={'undocumented':True}
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_malformed_tactics_rejected(self):
        d=fixture();e=next(e for e in d[2] if 'tactics' in e)
        e['tactics']['lineup'][0].pop('position')
        with self.assertRaises(SourceSchemaError):run(d)

    def test_omitted_temporary_events_quarantine_total(self):
        d=fixture()
        transition(d[2],'Player Off','00:15:00.100',60,0)
        transition(d[2],'Player On','00:16:00.200',61,0)
        a=run(d);r=a.validate()[0]
        self.assertEqual(r.status,CONFLICT)
        self.assertIsNone(r.elapsed_seconds)
        self.assertEqual(len(a.players[0].source_checks),2)
        self.assertTrue(all(c.evidence_refs for c in a.players[0].source_checks))

    def test_bad_behaviour_red_card_cannot_leave_player_active(self):
        d=fixture()
        transition(d[2],'Bad Behaviour','00:15:00.100',60,0,bad_behaviour=dict(card=dict(name='Red Card')))
        r=run(d).validate()[0]
        self.assertEqual(r.status,CONFLICT)
        self.assertIn('participation_after_permanent_exit',{i.code for i in r.issues})

    def test_second_yellow_cannot_leave_player_active(self):
        d=fixture()
        transition(d[2],'Foul Committed','00:15:00.100',60,0,foul_committed=dict(card=dict(name='Second Yellow')))
        self.assertIsNone(run(d).validate()[0].elapsed_seconds)

    def test_interior_position_change_not_hidden_by_matching_endpoints(self):
        d=fixture()
        transition(d[2],'Tactical Shift','00:15:00.100',60,0,tactics=dict(lineup=[dict(player=dict(id=101,name='Home Player'),position=dict(id=5,name='Left Center Back'))]))
        r=run(d).validate()[0]
        self.assertEqual(r.status,CONFLICT)
        self.assertIn('active_position_snapshot_disagreement',{i.code for i in r.issues})
        self.assertIsNone(r.position_allocation)

    def test_event_indices_exact_unique_if_present(self):
        d=fixture()
        for i,e in enumerate(d[2],1):e['index']=i
        self.assertEqual(run(d).validate()[0].status,VALID)
        d[2][1]['index']=d[2][0]['index']
        with self.assertRaises(SourceSchemaError):run(d)

    def test_partial_event_indices_reject(self):
        d=fixture();d[2][0]['index']=1
        with self.assertRaises(SourceSchemaError):run(d)

    def test_final_period_requires_exact_integer(self):
        for value in [2.0,True,'2']:
            d=fixture();d[1][0]['lineup'][0]['positions'][0]['to_period']=value
            with self.subTest(value=value),self.assertRaises(SourceSchemaError):run(d)

    def test_explicit_match_id_requires_exact_integer(self):
        d=fixture();d[2][0]['match_id']=10.0
        with self.assertRaises(SourceSchemaError):run(d)

    def test_source_check_order_is_deterministic(self):
        d=fixture()
        transition(d[2],'Player Off','00:15:00.100',60,0)
        transition(d[2],'Player On','00:16:00.200',61,0)
        a=run(d);d[2].reverse();b=run(d)
        self.assertEqual(a.players[0].source_checks,b.players[0].source_checks)

    def test_malformed_nested_event_field_rejects_cleanly(self):
        d=fixture();d[2][0]['team']=None
        with self.assertRaises(SourceSchemaError):run(d)

    def test_malformed_boundary_attributes_withheld(self):
        for value in [None,False,[],0]:
            d=fixture();d[2][0]['half_start']=value
            with self.subTest(value=value):self.assertIsNone(run(d).validate()[0].elapsed_seconds)


if __name__ == '__main__':
    unittest.main()
