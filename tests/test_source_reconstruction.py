"""Invented local source fixtures; no invented measurement is called real."""
import copy
from contextlib import closing
from dataclasses import asdict
from fractions import Fraction
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from test_statsbomb_participation import fixture,source
from scripts.source_verification_batch import (EvidenceStore,SCHEMA,code_revision,digest,endpoint,payload,write_new)
from scripts.reconstruct_player_evidence import reconstruct,records,build_delivered_index
from src.statsbomb_participation import adapt_match
from src.source_reconstruction import (COUNT_NAMES,appearance_rows,flatten_events,measurements,
    aggregate_context,transfer_comparison,reconcile_event,rational,exact)


def data():
    d=fixture();d[0][0]['competition']=dict(competition_id=11,competition_name='La Liga')
    d[0][0]['season']=dict(season_id=27,season_name='2015/2016')
    def add(uid,typ,minute,**fields):
        e=dict(id=uid,period=1,timestamp=f'00:{minute:02d}:00.000',minute=minute,second=0,
            type=dict(name=typ),team=dict(id=1,name='Home'),player=dict(id=101,name='Home Player'),
            location=[50,40])
        e.update(fields);d[2].append(e)
    add('tackle','Duel',10,duel=dict(type=dict(name='Tackle'),outcome=dict(name='Won')))
    add('intercept','Interception',11,interception=dict(outcome=dict(name='Success In Play')))
    add('recover','Ball Recovery',12)
    add('failed-recover','Ball Recovery',13,ball_recovery=dict(recovery_failure=True))
    add('pass','Pass',20,under_pressure=True,**{'pass':dict(end_location=[90,40],length=40)})
    add('dribble','Dribble',21,under_pressure=True,dribble=dict(outcome=dict(name='Complete')))
    return d


def review(d):
    a=adapt_match(10,*(source(x,k) for x,k in zip(d,['matches','lineups','events'])),clock_document_reference='synthetic documented clock')
    r=dict(match_id=10,competition_name='La Liga',season_name='2015/2016',artifact_validation='BYTE_BOUND_SOURCE_SCHEMA_REVIEWED',
        verification_key='synthetic-key',production_certified=False,boundaries=[asdict(b) for b in a.boundaries],
        players=[dict(player=asdict(p),validation=asdict(v)) for p,v in zip(a.players,a.validate())])
    return json.loads(payload(r))


def project(d=None):
    d=data() if d is None else d
    a=appearance_rows(review(d),d[0][0],d[1]);f=flatten_events(d[2],d[0][0],a);m,u,p=measurements(f,a)
    return a,f,m,u


def contribution(mid,minutes,count=0,status='STRUCTURALLY_VALID',team='Home'):
    a=dict(match_id=mid,player_id=101,team=team,competition_name='La Liga',season_name='2015/2016',
        participation_status=status,validated_elapsed_seconds=rational(Fraction(minutes)*60) if status=='STRUCTURALLY_VALID' else None,
        player_name_raw='Invented Player',player_name_normalized='Invented Player',position_allocation=[])
    m=dict(match_id=mid,components={n:dict(count=count if n=='tackles' else 0,aligned_count=(count if n=='tackles' else 0) if status=='STRUCTURALLY_VALID' else None,
        reasons=[] if status=='STRUCTURALLY_VALID' else ['UNRESOLVED_PARTICIPATION']) for n in COUNT_NAMES})
    return a,m


class ReconstructionFactsTests(unittest.TestCase):
    def test_original_input_and_exact_minutes_preserved(self):
        d=data();before=copy.deepcopy(d);a,frame,m,unknown=project(d)
        self.assertEqual(d,before);self.assertEqual(len(a),2);self.assertEqual(unknown,[])
        self.assertEqual(exact(a[0]['validated_elapsed_seconds']),Fraction(5701))
        self.assertEqual(exact(a[0]['validated_elapsed_minutes']),Fraction(5701,60))
        self.assertFalse(a[0]['production_certified'])

    def test_existing_count_definitions_and_legitimate_zero(self):
        a,f,ms,u=project();m=next(r for r in ms if r['player_id']==101)
        for n in ('tackles','interceptions','recoveries','pressured_pass_attempts','pressured_pass_completed','pressured_dribble_attempts','pressured_dribble_completed','progressive_passes'):
            self.assertEqual(m['components'][n]['count'],1,n)
        other=next(r for r in ms if r['player_id']==102)
        self.assertEqual(other['components']['tackles']['count'],0)
        self.assertEqual(other['components']['tackles']['per90'],0)
        self.assertIsNone(other['line_breaking_count'])

    def test_contradiction_keeps_counts_but_withholds_minutes_and_rates(self):
        d=data();d[2].append(dict(id='red',period=1,timestamp='00:30:00.000',minute=30,second=0,
            type=dict(name='Bad Behaviour'),team=dict(id=1,name='Home'),player=dict(id=101,name='Home Player'),bad_behaviour=dict(card=dict(name='Red Card'))))
        a,_,ms,_=project(d);actor=next(r for r in a if r['player_id']==101)
        self.assertEqual(actor['participation_status'],'CONFLICTING_EVIDENCE');self.assertIsNone(actor['validated_elapsed_minutes'])
        m=next(r for r in ms if r['player_id']==101)['components']['tackles']
        self.assertEqual(m['count'],1);self.assertIsNone(m['per90']);self.assertIsNone(m['aligned_count'])

    def test_incomplete_boundary_not_imputed(self):
        d=data();d[2][:]=[e for e in d[2] if not(e['period']==2 and e['type']['name']=='Half End')]
        a,_,ms,_=project(d)
        self.assertTrue(all(r['participation_status']=='INCOMPLETE_EVIDENCE' for r in a))
        self.assertTrue(all(r['validated_elapsed_minutes'] is None for r in a))

    def test_count_after_whistle_is_denominator_mismatch(self):
        d=data();e=next(e for e in d[2] if e['id']=='tackle')
        e.update(period=2,timestamp='00:50:00.000',minute=95)
        a,_,ms,_=project(d)
        self.assertEqual(a[0]['participation_status'],'STRUCTURALLY_VALID')
        value=ms[0]['components']['tackles']
        self.assertIn('NUMERATOR_DENOMINATOR_MISMATCH',value['reasons']);self.assertIsNone(value['per90'])

    def test_missing_progressive_geometry_only_withholds_that_measurement(self):
        d=data();next(e for e in d[2] if e['id']=='pass')['pass'].pop('end_location')
        _,_,ms,_=project(d);m=ms[0]
        self.assertIn('MISSING_SOURCE_GEOMETRY',m['components']['progressive_passes']['reasons'])
        self.assertIsNotNone(m['components']['recoveries']['per90'])

    def test_duplicate_appearance_and_event_reject(self):
        d=data();r=review(d);r['players'].append(copy.deepcopy(r['players'][0]))
        with self.assertRaises(ValueError):appearance_rows(r,d[0][0],d[1])
        a=project(d)[0];d[2].append(copy.deepcopy(d[2][0]))
        with self.assertRaises(ValueError):flatten_events(d[2],d[0][0],a)

    def test_wrong_match_and_team_fail_closed(self):
        d=data();a=project(d)[0];d[2][0]['match_id']=11
        with self.assertRaises(ValueError):flatten_events(d[2],d[0][0],a)
        d=data();d[2][0]['team']['name']='Other'
        with self.assertRaises(ValueError):flatten_events(d[2],d[0][0],a)

    def test_uuid_reconciliation_never_guesses_identity(self):
        _,f,_,_=project();s=next(r for r in f.to_dict('records') if r['id']=='tackle')
        d={c:s[c] for c in ('id','match_id','team','player','competition_name','season_name','type')}
        self.assertEqual(reconcile_event(s,d)['reconciled_player_id'],101)
        for field,value in [('id','unknown'),('match_id',11),('team','Away'),('player','Different'),('competition_name','Ligue 1'),('season_name','2016/2017'),('player_id',102)]:
            wrong={**d,field:value};result=reconcile_event(s,wrong)
            self.assertIsNone(result['reconciled_player_id'],field)

    def test_bench_is_not_zero_minute_appearance(self):
        d=data();d[1][0]['lineup'].append(dict(player_id=999,player_name='Bench',positions=[]))
        a,_,m,_=project(d);bench=next(r for r in a if r['player_id']==999)
        self.assertFalse(bench['active_appearance']);self.assertIsNone(bench['validated_elapsed_minutes'])
        self.assertFalse(any(r['player_id']==999 for r in m))

    def test_900_boundary_on_exact_supported_exposure(self):
        for minutes,expected in [(Fraction(899999,1000),False),(900,True)]:
            a,m=contribution(10,minutes)
            r=aggregate_context([a],[m],provider_complete=True,role='CB')
            self.assertEqual(r['candidate_900_minutes_evidence_met'],expected)
            self.assertFalse(r['production_certified']);self.assertFalse(r['reference_member'])

    def test_known_900_subset_does_not_mask_unresolved_appearance(self):
        a,m=contribution(10,900,10);b,n=contribution(11,0,5,'CONFLICTING_EVIDENCE')
        r=aggregate_context([a,b],[m,n],provider_complete=True,role='CB')
        self.assertTrue(r['supported_subset_at_least_900']);self.assertFalse(r['candidate_900_minutes_evidence_met'])
        self.assertIsNone(r['provider_scope_complete_minutes']);self.assertIsNone(r['withheld_minutes'])
        self.assertEqual(r['components']['tackles']['raw_source_count'],15)
        self.assertEqual(r['components']['tackles']['aligned_subset_count'],10)
        self.assertIsNone(r['components']['tackles']['provider_scope_per90'])

    def test_missing_fixture_coverage_and_identity_block_complete_scope(self):
        a,m=contribution(10,1000)
        for kwargs in [dict(provider_complete=False),dict(provider_complete=True,identity_reasons=['UNRESOLVED'])]:
            r=aggregate_context([a],[m],role='CB',**kwargs)
            self.assertFalse(r['candidate_900_minutes_evidence_met']);self.assertIsNone(r['provider_scope_complete_minutes'])

    def test_numerator_scope_and_duplicate_transfer_matches_reject(self):
        a,m=contribution(10,900)
        with self.assertRaises(ValueError):aggregate_context([a],[{**m,'match_id':11}],provider_complete=True)
        with self.assertRaises(ValueError):aggregate_context([a,a],[m,m],provider_complete=True)

    def test_transfer_raw_sums_and_alternative_thresholds(self):
        a,m=contribution(10,300,10);b,n=contribution(11,600,30,team='Away')
        ca=aggregate_context([a],[m],provider_complete=True,role='CB');cb=aggregate_context([b],[n],provider_complete=True,role='CB')
        ca.update(team='Home',team_id=1,competition_name='La Liga');cb.update(team='Away',team_id=2,competition_name='Ligue 1')
        # Changing competition is a source-facts experiment, not selecting a pool.
        season=aggregate_context([a,b],[m,n],provider_complete=True)
        r=transfer_comparison([ca,cb],season)
        self.assertEqual(r['combined_raw_counts']['tackles'],40)
        self.assertEqual(exact(r['combined_supported_minutes']),900)
        self.assertEqual(season['components']['tackles']['provider_scope_per90'],4)
        self.assertTrue(r['threshold_changes_if_combination_authorized'])
        self.assertFalse(r['scenarios'][1]['applicable']);self.assertFalse(r['reference_member'])

    def test_deterministic_input_order(self):
        a,m=contribution(10,300,10);b,n=contribution(11,600,30)
        self.assertEqual(aggregate_context([a,b],[m,n],provider_complete=True),aggregate_context([b,a],[n,m],provider_complete=True))


class ReconstructionRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        d=data();rev='a'*40;bindings={}
        for kind,value in [('matches',d[0]),('events',d[2]),('lineups',d[1])]:
            path=self.root/(kind+'.json');path.write_bytes(payload(value))
            bindings[kind]=dict(path=str(path),sha256=digest(path.read_bytes()),provider_revision=rev,
                source_reference=f'https://raw.githubusercontent.com/statsbomb/open-data/{rev}/data/matches/11/27.json' if kind=='matches' else endpoint(rev,kind,10),retrieved_at='2026-10-27T00:00:00+00:00')
        manifest=self.root/'manifest.json';write_new(manifest,dict(schema_version=SCHEMA,provider_revision=rev,fixture_documents={'fixtures':bindings['matches']},
            matches=[dict(match_id=10,competition_name='La Liga',season_name='2015/2016',fixture_document='fixtures',inclusion_policy='synthetic_test_only',artifacts={k:bindings[k] for k in ('events','lineups')})]))
        store=EvidenceStore(self.root/'store',manifest);result=store.execute([10])[0]
        index=self.root/'index.json';write_new(index,dict(validator_revision=code_revision(),manifest_sha256=digest(manifest.read_bytes()),matches=[dict(match_id=10,report_path=result['report_path'],report_sha256=digest(Path(result['report_path']).read_bytes()),verification_key=result['report']['verification_key'])]))
        minutes=[];recovery=[]
        for pid,name,team in [(101,'Home Player','Home'),(102,'Away Player','Away')]:
            k=dict(player_id=pid,player_name=name,team=team,competition_name='La Liga',season_name='2015/2016')
            minutes.append(dict(**k,minutes=900.,matches=1,position_group='CB',tied_groups=1,**{f'min_{role}':900. if role=='CB' else 0. for role in ('GK','CB','DM','CM','FB','WM','AM','ATT')}))
            for event in ('Tackle','Interception','Ball Recovery'):
                recovery.append(dict(**{a:b for a,b in k.items() if a!='player_name'},event_type=event,count=1,per90=.1,minutes=900.,matches=1,position_group='CB',reportable=True,full_coverage=True,meets_min=True))
        for name,rows in [('minutes',minutes),('recovery',recovery),('crosswalk',[dict(player_id=r['player_id'],player_name_raw=r['player_name'],team=r['team'],competition_name='La Liga',season_name='2015/2016') for r in minutes]),
            ('lineups',[dict(match_id=10,team=t['team_name'],player_id=p['player_id'],player_name=p['player_name'],position=p['positions'][0]['position']) for t in d[1] for p in t['lineup']]),
            ('metadata',[dict(match_id=10,competition_name='La Liga',season_name='2015/2016')])]:
            pq.write_table(pa.Table.from_pylist(rows),self.root/(name+'.parquet'))
        flat=flatten_events(d[2],d[0][0],appearance_rows(review(d),d[0][0],d[1]))
        ev=flat[flat.type.isin(['Duel','Interception','Ball Recovery','Pass','Dribble'])][['id','match_id','team','player','competition_name','season_name','type']]
        pq.write_table(pa.Table.from_pandas(ev,preserve_index=False),self.root/'events.parquet')
        pq.write_table(pa.table(dict(match_id=pa.array([],type=pa.int64()),competition_name=pa.array([],type=pa.string()),season_name=pa.array([],type=pa.string()))),self.root/'frames.parquet')
        self.kw=dict(index=index,manifest=manifest,**{k:self.root/(k+'.parquet') for k in ('events','minutes','recovery','crosswalk','lineups','metadata','frames')})

    def test_full_small_rebuild_is_deterministic_and_existing_run_idempotent(self):
        before={p:p.read_bytes() for p in self.root.glob('*') if p.is_file()}
        with patch('scripts.source_verification_batch.public_transport',side_effect=AssertionError('no network')):
            a=reconstruct(output=self.root/'one',**self.kw)
            hashes={p.name:digest(p.read_bytes()) for p in (self.root/'one').iterdir()}
            self.assertEqual(reconstruct(output=self.root/'one',**self.kw),a)
            self.assertEqual(hashes,{p.name:digest(p.read_bytes()) for p in (self.root/'one').iterdir()})
            b=reconstruct(output=self.root/'two',**self.kw)
        self.assertEqual(a,b)
        self.assertEqual(hashes,{p.name:digest(p.read_bytes()) for p in (self.root/'two').iterdir()})
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        self.assertEqual(a['active_appearances'],2);self.assertEqual(a['production_certified_contexts'],0)

    def test_source_fingerprint_change_refuses_idempotent_reuse(self):
        reconstruct(output=self.root/'one',**self.kw)
        (self.root/'events.json').write_bytes(b'[]')
        with self.assertRaises(ValueError):reconstruct(output=self.root/'one',**self.kw)

    def test_independent_audit_checks_sealed_facts_and_rejects_tampering(self):
        from scripts.audit_source_reconstruction import audit
        reconstruct(output=self.root/'one',**self.kw)
        report=audit(self.root/'one',self.root/'audit')
        self.assertTrue(report['invariants_passed'])
        self.assertEqual(report['match_count'],1)
        self.assertEqual(report['appearance_counts'],{'STRUCTURALLY_VALID':2})
        self.assertEqual(report['production_certified_contexts'],0)
        with self.assertRaises(ValueError):audit(self.root/'one',self.root/'audit')
        (self.root/'one'/'appearance-ledger.jsonl').write_bytes(b'{}\n')
        with self.assertRaises(ValueError):audit(self.root/'one',self.root/'tampered-audit')
        self.assertFalse((self.root/'tampered-audit').exists())

    def test_derived_tamper_and_incomplete_output_refuse_overwrite(self):
        reconstruct(output=self.root/'one',**self.kw)
        target=self.root/'one'/'summary.json';target.write_bytes(b'{}')
        with self.assertRaises(ValueError):reconstruct(output=self.root/'one',**self.kw)
        self.assertEqual(target.read_bytes(),b'{}')
        (self.root/'partial').mkdir()
        with self.assertRaises(FileNotFoundError):reconstruct(output=self.root/'partial',**self.kw)

    def test_ambiguous_delivered_mapping_is_reported_not_chosen(self):
        path=self.kw['crosswalk'];rows=pq.read_table(path).to_pylist();rows.append({**rows[0],'player_id':999})
        pq.write_table(pa.Table.from_pylist(rows),path)
        result=reconstruct(output=self.root/'one',**self.kw)
        identity=list(records(self.root/'one'/'identity-reconciliation.jsonl'))
        self.assertIn('AMBIGUOUS_DELIVERED_NAME_MAPPING',identity[0]['identity_reasons'])
        self.assertEqual(result['production_certified_contexts'],0)

    def test_duplicate_delivered_uuid_and_missing_review_coverage_reject(self):
        rows=pq.read_table(self.kw['events']).to_pylist();rows.append(rows[0]);pq.write_table(pa.Table.from_pylist(rows),self.kw['events'])
        with closing(sqlite3.connect(':memory:')) as db:
            with self.assertRaises(ValueError):build_delivered_index(self.kw['events'],db)
        idx=json.loads(self.kw['index'].read_bytes());idx['matches']=[];self.kw['index'].write_bytes(payload(idx))
        with self.assertRaises(ValueError):reconstruct(output=self.root/'one',**self.kw)


if __name__=='__main__':unittest.main()
