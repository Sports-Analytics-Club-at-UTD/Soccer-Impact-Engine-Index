"""Private original-source regressions for Batch 4; missing evidence fails."""
from collections import defaultdict
from pathlib import Path
import csv,hashlib,json,unittest
import pandas as pd
from src.identity import resolve_events,PLAYER_KEYS
from scripts.check_off_field_card_sources import load

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'audit-output/identity-source-reconciliation'


def table(name):
    with (OUT/name).open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))


class OriginalIdentityRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=json.loads((OUT/'summary.json').read_text());cls.current=table('current-restriction-inventory.csv');cls.evidence=table('source-name-evidence.csv');cls.apps=table('delivered-appearance-evidence.csv')

    def test_complete_source_universe_and_no_reassignment(self):
        s=self.summary;self.assertEqual(s['checks']['original_events'],5436699);self.assertEqual(s['checks']['original_fixtures'],1551)
        self.assertEqual(s['checks']['uuid_actor_fixture_team_bidirectional_comparisons'],5436699)
        self.assertEqual(s['changed_source_event_associations'],0)

    def test_fernandinho_all_original_fixture_names_and_ids(self):
        rs=[r for r in self.evidence if r['player_id']=='3054'];self.assertEqual({r['raw_name'] for r in rs},{'Fernando Luiz Rosa','Fernando Luiz Roza'})
        self.assertEqual({r['team_id'] for r in rs},{'36'});self.assertEqual({r['competition_id'] for r in rs},{'2'});self.assertEqual({r['season_id'] for r in rs},{'27'})
        self.assertTrue(all(r['raw_name']==r['original_lineup_name'] for r in rs))
        self.assertEqual({r['match_id'] for r in rs if r['raw_name']=='Fernando Luiz Roza'},{'3754296'})
        self.assertEqual(sum(r['role']=='actor' and r['raw_name']=='Fernando Luiz Roza' for r in rs),294)
        self.assertEqual(sum(r['role']=='recipient' and r['raw_name']=='Fernando Luiz Roza' for r in rs),73)
        self.assertEqual(self.summary['target_delivered_associations']['3054'],3873)

    def test_existing_resolver_handles_original_supplied_ids_without_alias_install(self):
        rs=[r for r in self.evidence if r['player_id']=='3054' and r['role']=='actor']
        # Original actor UUIDs are unique; fixture context stays in each record.
        es=pd.DataFrame([dict(id=r['event_id'],player=r['raw_name'],player_id=3054,team='Manchester City',competition_name=r['competition'],season_name=r['season'],match_id=int(r['match_id'])) for r in rs])
        x=pd.DataFrame([dict(player_name_raw='Fernando Luiz Rosa',player_id=3054,team='Manchester City',competition_name='Premier League',season_name='2015/2016')])
        resolved=resolve_events(es,x,x[PLAYER_KEYS]);self.assertEqual(resolved.events.id.tolist(),es.id.tolist());self.assertTrue(resolved.events.player_id.eq(3054).all());self.assertEqual(resolved.events.player.tolist(),es.player.tolist())

    def test_juanfran_active_sets_and_phantom_absence(self):
        rs=[r for r in self.apps if r['player_id']=='26023']
        self.assertEqual({r['match_id'] for r in rs if r['source_active']=='True'},{r['match_id'] for r in rs if r['delivered_active']=='True'})
        removed=next(r for r in rs if r['match_id']=='3825670');self.assertEqual((removed['source_active'],removed['delivered_active'],removed['batch2a_removed']),('False','False','True'))
        _,_,_,es,_,p,v,oracle,_=load(26023,3825670)
        self.assertFalse(p.observations or p.source_checks);self.assertFalse(oracle['active']);self.assertEqual(oracle['issues'],[]);self.assertIsNone(v.elapsed_seconds)
        self.assertEqual([d.state for d in p.off_field_discipline],['UNUSED_ROSTER'])
        self.assertEqual(sum(e['id']=='e8bbbe1d-37fb-4ffb-92dd-ee93a07c6481' for e in es),1)

    def test_other_three_corrected_bench_appearances(self):
        for pid,mid in [(6672,3825869),(10612,3825885),(40458,3878555)]:
            with self.subTest(player=pid):
                _,_,_,_,_,p,v,o,_=load(pid,mid);self.assertFalse(p.observations or p.source_checks);self.assertFalse(o['active']);self.assertIsNone(v.elapsed_seconds);self.assertEqual([d.state for d in p.off_field_discipline],['UNUSED_ROSTER'])

    def test_every_historical_and_additional_restriction_has_exact_evidence(self):
        old={int(r['player_id']) for r in table('original-restriction-inventory.csv')};self.assertEqual(len(old),10)
        current={int(r['player_id']):r for r in self.current};self.assertTrue(old<=current.keys())
        for pid,r in current.items():
            with self.subTest(player=pid):
                self.assertEqual(json.loads(r['current_reasons']),['CANDIDATE_SOURCE_NAME_DISAGREEMENT'] if pid==3054 else ['SOURCE_ACTIVITY_WITHOUT_APPEARANCE'])
                self.assertEqual(r['association_changes'],'0');self.assertEqual(r['metric_changes'],'0')
                self.assertTrue(any(int(e['player_id'])==pid for e in self.evidence) or any(int(e['player_id'])==pid for e in table('unresolved-conflicts.csv')))

    def test_remaining_activity_is_discipline_not_an_active_appearance(self):
        bench=json.loads((OUT/'source-activity-without-appearance.json').read_text())
        for r in bench:
            with self.subTest(uuid=r['event_id']):
                self.assertEqual(r['raw_event']['type']['name'],'Bad Behaviour');self.assertEqual(r['lineup']['positions'],[])
                if r['player_id'] not in (26023,6672,10612,40458):
                    _,_,_,_,_,p,v,o,_=load(r['player_id'],r['match_id']);self.assertFalse(p.observations or p.source_checks);self.assertFalse(o['active']);self.assertIsNone(v.elapsed_seconds)

    def test_all_691_profiles_and_batch3b_correction_preserved(self):
        p=ROOT/'audit-output/batch4-numerics/summary.json';r=json.loads(p.read_text());self.assertEqual(r['players'],691);self.assertEqual(r['changed_profiles'],0);self.assertEqual(r['changed_eligibility'],0);self.assertEqual(r['pressure_correction_actions'],4)
        self.assertEqual(self.summary['prior_corrections']['published_accepted_preserved'],14550)


if __name__=='__main__':unittest.main(verbosity=2)
