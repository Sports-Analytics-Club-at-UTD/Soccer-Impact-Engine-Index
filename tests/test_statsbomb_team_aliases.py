"""Explicit source-ID/context alias regressions; invented match observations."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from test_statsbomb_participation import fixture, run, source
from src.statsbomb_participation import SourceSchemaError, adapt_match
from scripts.source_verification_batch import code_revision


def alias_fixture(alias='Marseille', canonical='Olympique de Marseille', tid=147):
    data = fixture()
    match, lineups, events = data
    match[0]['competition'] = dict(competition_id=7, competition_name='Ligue 1')
    match[0]['season'] = dict(season_id=27, season_name='2015/2016')
    match[0]['home_team'] = dict(home_team_id=tid, home_team_name=canonical)
    lineups[0].update(team_id=tid, team_name=alias)
    for event in events:
        if event['team']['id'] == 1:
            event['team'] = dict(id=tid, name=alias)
    return data


class SourceTeamAliasTests(unittest.TestCase):
    def test_marseille_requires_supported_id_and_preserves_original_names(self):
        data = alias_fixture()
        before = copy.deepcopy(data)
        docs = [source(value, kind) for value, kind in zip(data, ('matches','lineups','events'))]
        fingerprints = [doc.fingerprint for doc in docs]
        result = adapt_match(10, *docs, clock_document_reference='synthetic clock')
        self.assertEqual(data, before)
        self.assertEqual([doc.fingerprint for doc in docs], fingerprints)
        self.assertEqual([doc.records() for doc in docs], list(before))
        self.assertEqual({n.team_id for n in result.team_name_normalizations}, {147})
        self.assertEqual(len(result.team_name_normalizations), 2)
        for n in result.team_name_normalizations:
            self.assertEqual(n.fixture_name, 'Olympique de Marseille')
            self.assertEqual(n.observed_name, 'Marseille')
            self.assertEqual(n.canonical_name, 'Olympique de Marseille')
            self.assertTrue(n.source_reference.startswith('synthetic/'))
        self.assertEqual({p.team_id for p in result.players}, {147,2})
        self.assertTrue(all(r.status == 'STRUCTURALLY_VALID' for r in result.validate()))
        self.assertTrue(all(not r.source_independently_verified for r in result.validate()))

    def test_caen_requires_supported_id(self):
        data = alias_fixture('Caen', 'Stade Malherbe Caen', 140)
        result = run(data)
        self.assertEqual({n.team_id for n in result.team_name_normalizations}, {140})
        self.assertEqual({n.canonical_name for n in result.team_name_normalizations}, {'Stade Malherbe Caen'})
        data[0][0]['home_team']['home_team_id'] = 147
        with self.assertRaises(SourceSchemaError):
            run(data)

    def test_alias_cannot_transfer_to_different_consistent_id(self):
        for alias, canonical in [('Marseille','Olympique de Marseille'),('Caen','Stade Malherbe Caen')]:
            with self.subTest(alias=alias), self.assertRaises(SourceSchemaError):
                run(alias_fixture(alias, canonical, 999))

    def test_matching_names_do_not_override_different_source_ids(self):
        for kind in ('lineups', 'events'):
            for name in ('Marseille', 'Olympique de Marseille'):
                data = alias_fixture()
                if kind == 'lineups':
                    data[1][0].update(team_id=140, team_name=name)
                else:
                    data[2][0]['team'].update(id=140, name=name)
                with self.subTest(kind=kind,name=name), self.assertRaises(SourceSchemaError):
                    run(data)

    def test_unknown_alias_and_fuzzy_spelling_reject(self):
        for name in ('OM', 'Olympique Marseille', 'Marseille ', 'marseille', 'Caen', 'Unrelated'):
            for kind in ('lineups', 'events'):
                data = alias_fixture()
                if kind == 'lineups': data[1][0]['team_name'] = name
                else: data[2][0]['team']['name'] = name
                with self.subTest(name=name,kind=kind), self.assertRaises(SourceSchemaError):
                    run(data)

    def test_wrong_match_rejects(self):
        for mutate in (lambda d:d[0][0].update(match_id=11),
                       lambda d:d[2][0].update(match_id=11)):
            data = alias_fixture(); mutate(data)
            with self.assertRaises(SourceSchemaError): run(data)

    def test_wrong_competition_or_season_cannot_enable_alias(self):
        for field, key, value in [('competition','competition_id',2),
                                  ('competition','competition_name','Premier League'),
                                  ('season','season_id',28),
                                  ('season','season_name','2016/2017'),
                                  ('competition','competition_id',7.0),
                                  ('season','season_id',27.0)]:
            data = alias_fixture(); data[0][0][field][key] = value
            with self.subTest(field=field,key=key,value=value), self.assertRaises(SourceSchemaError):
                run(data)
        data = alias_fixture(); del data[0][0]['competition']['competition_id']
        with self.assertRaises(SourceSchemaError): run(data)

    def test_player_id_and_name_checks_remain_exact(self):
        for field, value in [('id',777),('name','Different Player')]:
            data = alias_fixture()
            event = next(e for e in data[2] if e['team']['id']==147 and 'tactics' in e)
            event['tactics']['lineup'][0]['player'][field] = value
            with self.subTest(field=field), self.assertRaises(SourceSchemaError): run(data)

    def test_opponent_side_stays_exact(self):
        for kind in ('lineups', 'events'):
            for field, value in [('id',156),('name','Marseille')]:
                data = alias_fixture()
                if kind == 'lineups':
                    data[1][1]['team_id' if field=='id' else 'team_name'] = value
                else:
                    next(e for e in data[2] if e['team']['id']==2)['team'][field] = value
                with self.subTest(kind=kind,field=field), self.assertRaises(SourceSchemaError): run(data)

    def test_exact_names_need_no_alias_record(self):
        data = alias_fixture()
        data[1][0]['team_name'] = 'Olympique de Marseille'
        for event in data[2]:
            if event['team']['id']==147: event['team']['name']='Olympique de Marseille'
        self.assertEqual(run(data).team_name_normalizations, ())

    def test_fixture_short_spelling_is_preserved(self):
        data = alias_fixture()
        data[0][0]['home_team']['home_team_name'] = 'Marseille'
        data[1][0]['team_name'] = 'Olympique de Marseille'
        result = run(data)
        player = next(p for p in result.players if p.team_id==147)
        self.assertEqual(player.context.team_key, 'Marseille')
        self.assertEqual(result.team_name_normalizations[0].canonical_name, 'Olympique de Marseille')

    def test_verification_revision_includes_existing_alias_policy(self):
        before = code_revision()
        original = Path.read_bytes
        def changed(path):
            raw = original(path)
            return raw+b'\n# test policy revision\n' if path.name=='identity.py' else raw
        with patch.object(Path, 'read_bytes', changed):
            self.assertNotEqual(code_revision(), before)


if __name__ == '__main__':
    unittest.main()
