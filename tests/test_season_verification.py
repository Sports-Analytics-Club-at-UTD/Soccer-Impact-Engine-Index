"""Synthetic season accounting, including separate transferred club contexts."""
import copy
from dataclasses import asdict
import json
import unittest

from test_statsbomb_participation import fixture,run,transition
from scripts.source_verification_batch import payload
from src.season_verification import season_readiness


def inputs():
    a=run(fixture())
    report=json.loads(payload(dict(match_id=10,competition_name='Invented League',season_name='2015/2016',
        artifact_validation='BYTE_BOUND_SOURCE_SCHEMA_REVIEWED',production_certified=False,
        players=[dict(player=asdict(p),validation=asdict(r)) for p,r in zip(a.players,a.validate())])))
    fixtures=[dict(match_id=i,competition_name='Invented League',season_name='2015/2016',home_team=h,away_team='Away') for i,h in [(10,'Home'),(20,'Other')]]
    metadata=[dict(match_id=i,competition_name='Invented League',season_name='2015/2016') for i in [10,20]]
    contexts=[dict(player_id=101,team=team,competition_name='Invented League',season_name='2015/2016',minutes=1000) for team in ['Home','Other']]
    lineups=[dict(match_id=i,player_id=101,team=team,position='Right Center Back') for i,team in [(10,'Home'),(20,'Other')]]
    return fixtures,metadata,lineups,contexts,[report]


class ReadinessTests(unittest.TestCase):
    def test_sample_counts_not_season_certification(self):
        r=season_readiness(*inputs());s=r['summary']
        self.assertEqual(s['source_match_pairs_obtained'],1)
        self.assertEqual(s['additional_provider_match_pairs_required'],1)
        self.assertEqual(s['qualified_contexts_touched'],1)
        self.assertEqual(s['qualified_contexts_with_valid_sample'],1)
        self.assertEqual(s['production_certified_contexts'],0)
        self.assertEqual(s['validated_season_exposure_eligible_contexts'],0)
        self.assertFalse(r['publication_authorized'])

    def test_transferred_player_club_contexts_stay_distinct(self):
        r=season_readiness(*inputs())
        self.assertEqual(len(r['contexts']),2);self.assertEqual(len(r['transferred_actors']),1)
        actor=r['transferred_actors'][0];self.assertEqual(actor['player_id'],101)
        self.assertEqual({c['team'] for c in actor['contexts']},{'Home','Other'})
        self.assertFalse(actor['scores_aggregated'])
        first=next(c for c in r['contexts'] if c['team']=='Home')
        other=next(c for c in r['contexts'] if c['team']=='Other')
        self.assertEqual(first['valid_sample_appearance_ids'],[10]);self.assertEqual(other['valid_sample_appearance_ids'],[])

    def test_eligibility_and_exposure_are_separate(self):
        r=season_readiness(*inputs())
        for c in r['contexts']:
            self.assertTrue(c['delivered_table_eligible']);self.assertFalse(c['validated_exposure_eligible'])
            self.assertEqual(c['identity_gate'],'UNRESOLVED');self.assertEqual(c['reportability_gate'],'UNRESOLVED')
            self.assertFalse(c['season_exposure_verified'])

    def test_missing_delivered_fixture_with_source_pair(self):
        d=list(inputs());d[1]=[d[1][1]]
        r=season_readiness(*d)
        self.assertEqual(r['leagues'][0]['missing_from_delivered_ids'],[10])
        self.assertEqual(r['summary']['source_match_pairs_obtained'],1)
        self.assertEqual(r['summary']['observed_match_pairs_obtained'],0)
        self.assertEqual(r['missing_delivered_fixture_inclusion'],'PENDING_TEAM_APPROVAL')

    def test_provider_list_match_does_not_prove_full_league(self):
        r=season_readiness(*inputs())
        self.assertTrue(r['leagues'][0]['provider_ids_match_delivered'])
        self.assertFalse(r['leagues'][0]['source_coverage_complete'])
        self.assertEqual(r['leagues'][0]['full_historical_league_completeness'],'NOT_ESTABLISHED_BY_PROVIDER_LIST')

    def test_all_pairs_still_not_automatic_exposure_approval(self):
        d=list(inputs());d[0]=d[0][:1];d[1]=d[1][:1];d[2]=d[2][:1];d[3]=d[3][:1]
        r=season_readiness(*d)
        self.assertTrue(r['leagues'][0]['source_coverage_complete'])
        self.assertFalse(r['leagues'][0]['season_exposure_verified'])
        self.assertFalse(r['contexts'][0]['validated_exposure_eligible'])

    def test_conflicts_count_without_minutes(self):
        d=list(inputs());a=fixture();transition(a[2],'Bad Behaviour','00:15:00.000',60,0,bad_behaviour=dict(card=dict(name='Red Card')))
        adapted=run(a)
        d[4][0]['players']=json.loads(payload([dict(player=asdict(p),validation=asdict(r)) for p,r in zip(adapted.players,adapted.validate())]))
        r=season_readiness(*d)
        self.assertEqual(r['summary']['active_appearance_status_counts']['CONFLICTING_EVIDENCE'],1)
        self.assertEqual(r['contexts'][0]['contradictory_sample_appearance_ids'],[10])
        self.assertFalse(r['contexts'][0]['validated_exposure_eligible'])

    def test_input_immutability_and_determinism(self):
        d=inputs();before=copy.deepcopy(d)
        self.assertEqual(season_readiness(*d),season_readiness(*d));self.assertEqual(d,before)

    def test_duplicate_context_rejects(self):
        d=list(inputs());d[3].append(copy.deepcopy(d[3][0]))
        with self.assertRaises(ValueError):season_readiness(*d)

    def test_duplicate_fixture_and_report_reject(self):
        for index in [0,4]:
            d=list(inputs());d[index].append(copy.deepcopy(d[index][0]))
            with self.subTest(index=index),self.assertRaises(ValueError):season_readiness(*d)

    def test_actor_context_conflict_reject(self):
        d=list(inputs());d[4][0]['players'][0]['validation']['context']['player_id']=999
        with self.assertRaises(ValueError):season_readiness(*d)

    def test_report_context_and_certification_reject(self):
        for changes in [dict(competition_name='Wrong'),dict(production_certified=True)]:
            d=list(inputs());d[4][0].update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):season_readiness(*d)

    def test_rejected_source_not_counted_as_obtained(self):
        d=list(inputs());d[4][0]['artifact_validation']='SOURCE_REJECTED'
        self.assertEqual(season_readiness(*d)['summary']['source_match_pairs_obtained'],0)

    def test_bench_roster_not_counted_as_appearance(self):
        d=list(inputs());a=fixture();a[1][0]['lineup'].append(dict(player_id=999,player_name='Synthetic Bench',positions=[]));adapted=run(a)
        d[4][0]['players']=json.loads(payload([dict(player=asdict(p),validation=asdict(r)) for p,r in zip(adapted.players,adapted.validate())]))
        self.assertEqual(season_readiness(*d)['summary']['sample_active_player_contexts'],2)


if __name__=='__main__':unittest.main()
