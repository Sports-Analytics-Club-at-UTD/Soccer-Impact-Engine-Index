"""Synthetic local artifacts and fake transports only; never real HTTP requests."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_statsbomb_participation import fixture
from scripts.source_verification_batch import (SCHEMA, EvidenceConflict, EvidenceStore,
    bound_document, digest, dry_run, endpoint, load_manifest, main, payload, write_new, MAX_BYTES)

REV='a'*40


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.match,self.lineups,self.events=fixture()
        self.raw={'events':payload(self.events),'lineups':payload(self.lineups)}
        self.documents={}
        for kind,raw in [('matches',payload(self.match)),*self.raw.items()]:
            file=self.root/(kind+'.json');file.write_bytes(raw)
            self.documents[kind]=dict(path=str(file),sha256=digest(raw),source_reference=endpoint(REV,kind,10),provider_revision=REV,retrieved_at='2026-10-27T00:00:00+00:00')
        self.manifest=dict(schema_version=SCHEMA,provider_revision=REV,created_at='2026-10-27T00:00:00+00:00',
            fixture_documents={'matches':self.documents['matches']},matches=[dict(match_id=10,competition_name='Invented League',season_name='2015/2016',fixture_document='matches',inclusion_policy='pending',artifacts={})])
        self.path=self.root/'manifest.json'

    def store(self, artifacts=False):
        if artifacts:
            self.manifest['matches'][0]['artifacts']={k:self.documents[k] for k in ('events','lineups')}
        write_new(self.path,self.manifest)
        return EvidenceStore(self.root/'isolated-evidence',self.path)

    def transport(self,url):
        return self.raw['events' if '/events/' in url else 'lineups']

    def test_offline_default_never_requests(self):
        store=self.store()
        with patch('scripts.source_verification_batch.public_transport',side_effect=AssertionError('network forbidden')):
            result=store.execute([10])
        self.assertEqual(result[0]['status'],'SOURCE_PAIR_INCOMPLETE')
        self.assertEqual(store.accounting(),dict(successes=0,failures=0,interrupted_outcome_unknown=0))

    def test_dry_run_is_read_only(self):
        self.store(True)
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch('scripts.source_verification_batch.public_transport',side_effect=AssertionError):
            plan=dry_run(self.path)
        self.assertEqual(plan['obtained_match_pair_ids'],[10]);self.assertFalse(plan['network_enabled'])
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_cli_default_no_destination_or_network(self):
        write_new(self.path,self.manifest)
        with contextlib.redirect_stdout(io.StringIO()),patch('scripts.source_verification_batch.public_transport',side_effect=AssertionError):
            self.assertEqual(main(['--manifest',str(self.path)]),0)
        self.assertFalse((self.root/'isolated-evidence').exists())

    def test_offline_verification_stable_resume(self):
        store=self.store(True)
        first=store.execute([10])[0]
        self.assertEqual(first['report']['active_status_counts'],{'STRUCTURALLY_VALID':2})
        self.assertFalse(first['report']['production_certified'])
        before=Path(first['report_path']).read_bytes()
        resumed=EvidenceStore(store.root,self.path).execute([10])[0]
        self.assertEqual(resumed['status'],'SKIPPED_PREVIOUSLY_VALIDATED_ARTIFACTS')
        self.assertEqual(Path(resumed['report_path']).read_bytes(),before)
        self.assertEqual(list((store.root/'journal').iterdir()),[])

    def test_network_gate_and_limits(self):
        store=self.store()
        for limit in [None,0,9,True,1.5]:
            with self.subTest(limit=limit),self.assertRaises(ValueError):
                store.execute([10],allow_network=True,batch_limit=limit,transport=self.transport)
        with self.assertRaises(ValueError):store.execute([10],transport=self.transport)
        with self.assertRaises(ValueError):store.execute([10],refresh=True)
        with self.assertRaises(ValueError):store.execute([10],allow_network='yes')
        self.assertEqual(store.accounting()['successes'],0)

    def test_cli_network_gate_before_destination_creation(self):
        write_new(self.path,self.manifest);destination=self.root/'must-stay-absent'
        with contextlib.redirect_stdout(io.StringIO()),patch('scripts.source_verification_batch.public_transport',side_effect=AssertionError):
            result=main(['--manifest',str(self.path),'--allow-network','--match-ids','10','--destination',str(destination)])
        self.assertEqual(result,2);self.assertFalse(destination.exists())

    def test_success_and_skipping_completed_requests(self):
        store=self.store();calls=[]
        def fetch(url):calls.append(url);return self.transport(url)
        first=store.execute([10],allow_network=True,batch_limit=1,transport=fetch)[0]
        self.assertEqual(first['status'],'BYTE_BOUND_SOURCE_SCHEMA_REVIEWED')
        self.assertEqual(len(calls),2)
        second=store.execute([10],allow_network=True,batch_limit=1,transport=fetch)[0]
        self.assertEqual(second['status'],'SKIPPED_PREVIOUSLY_VALIDATED_ARTIFACTS')
        self.assertEqual(len(calls),2);self.assertEqual(store.accounting()['successes'],2)

    def test_partial_failure_resume_reuses_success(self):
        store=self.store();calls=[]
        def first(url):
            calls.append(url)
            if '/lineups/' in url:raise OSError('synthetic connection failure')
            return self.transport(url)
        self.assertEqual(store.execute([10],allow_network=True,batch_limit=1,transport=first)[0]['status'],'SOURCE_PAIR_INCOMPLETE')
        def resumed(url):calls.append(url);return self.transport(url)
        result=EvidenceStore(store.root,self.path).execute([10],allow_network=True,batch_limit=1,transport=resumed)[0]
        self.assertEqual(result['status'],'BYTE_BOUND_SOURCE_SCHEMA_REVIEWED')
        self.assertEqual(sum('/events/' in u for u in calls),1)
        self.assertEqual(store.accounting(),dict(successes=2,failures=1,interrupted_outcome_unknown=0))

    def test_interruption_retains_unknown_and_resumes(self):
        store=self.store()
        def interrupt(url):
            if '/lineups/' in url:raise KeyboardInterrupt()
            return self.transport(url)
        with self.assertRaises(KeyboardInterrupt):store.execute([10],allow_network=True,batch_limit=1,transport=interrupt)
        self.assertEqual(store.accounting()['interrupted_outcome_unknown'],1)
        calls=[]
        def resume(url):calls.append(url);return self.transport(url)
        result=EvidenceStore(store.root,self.path).execute([10],allow_network=True,batch_limit=1,transport=resume)[0]
        self.assertEqual(result['status'],'BYTE_BOUND_SOURCE_SCHEMA_REVIEWED')
        self.assertEqual(len(calls),1);self.assertIn('/lineups/',calls[0])
        self.assertEqual(store.accounting()['interrupted_outcome_unknown'],1)

    def test_repeat_different_bytes_quarantined_no_overwrite(self):
        store=self.store(True);first=store.execute([10])[0]
        original=Path(self.documents['events']['path']).read_bytes()
        changed=copy.deepcopy(self.events);changed[0]['synthetic_extra']='different bytes'
        def refresh(url):return payload(changed) if '/events/' in url else self.raw['lineups']
        result=store.execute([10],allow_network=True,batch_limit=1,refresh=True,transport=refresh)[0]
        self.assertEqual(result['status'],'SOURCE_EVIDENCE_CONFLICT')
        self.assertTrue(Path(result['report_path']).exists())
        self.assertFalse(result['report']['production_certified'])
        self.assertIn('repeat retrieval bytes conflict',result['error'])
        self.assertEqual(Path(self.documents['events']['path']).read_bytes(),original)
        self.assertTrue(Path(first['report_path']).exists())
        self.assertEqual(len(list((store.root/'objects').iterdir())),2)
        self.assertEqual(store.execute([10])[0]['status'],'SOURCE_EVIDENCE_CONFLICT')

    def test_repeat_same_bytes_skip_immutable_report(self):
        store=self.store(True);first=store.execute([10])[0]
        second=store.execute([10],allow_network=True,batch_limit=1,refresh=True,transport=self.transport)[0]
        self.assertEqual(second['status'],'SKIPPED_PREVIOUSLY_VALIDATED_ARTIFACTS')
        self.assertEqual(first['report_path'],second['report_path'])

    def test_tampered_source_rejects_instead_of_refetch(self):
        store=self.store(True);Path(self.documents['events']['path']).write_bytes(b'[]')
        with patch('scripts.source_verification_batch.public_transport',side_effect=AssertionError):
            result=store.execute([10],allow_network=True,batch_limit=1)
        self.assertEqual(result[0]['status'],'SOURCE_EVIDENCE_CONFLICT')

    def test_tampered_cached_report_rejects(self):
        store=self.store(True);r=store.execute([10])[0];Path(r['report_path']).write_bytes(b'{}')
        self.assertEqual(store.execute([10])[0]['status'],'SOURCE_EVIDENCE_CONFLICT')

    def test_validator_revision_invalidates_cache(self):
        store=self.store(True);a=store.execute([10])[0]
        with patch('scripts.source_verification_batch.code_revision',return_value='new-validated-code'):
            b=store.execute([10])[0]
        self.assertEqual(b['status'],'BYTE_BOUND_SOURCE_SCHEMA_REVIEWED')
        self.assertNotEqual(a['report_path'],b['report_path'])
        self.assertTrue(Path(a['report_path']).exists())

    def test_unrelated_destination_rejects(self):
        store=self.store();unrelated=self.root/'existing';unrelated.mkdir();(unrelated/'keep').write_text('keep')
        with self.assertRaises(EvidenceConflict):EvidenceStore(unrelated,self.path)
        self.assertEqual((unrelated/'keep').read_text(),'keep')

    def test_changed_manifest_cannot_resume_same_store(self):
        store=self.store();changed=copy.deepcopy(self.manifest);changed['scope']='changed declaration'
        other=self.root/'other-manifest.json';write_new(other,changed)
        with self.assertRaises(EvidenceConflict):EvidenceStore(store.root,other)

    def test_explicit_ids_required(self):
        store=self.store()
        for ids in [[],[11],[10,10],[10.0],[True],None]:
            with self.subTest(ids=ids),self.assertRaises(ValueError):store.execute(ids)

    def test_manifest_context_and_duplicates_reject(self):
        for mutate in [lambda d:d['matches'][0].update(competition_name='Wrong'),
                       lambda d:d['matches'].append(copy.deepcopy(d['matches'][0])),
                       lambda d:d.update(provider_revision='master'),
                       lambda d:d['matches'][0].update(match_id=10.0)]:
            data=copy.deepcopy(self.manifest);mutate(data)
            path=self.root/(str(len(list(self.root.iterdir())))+'.json');write_new(path,data)
            with self.assertRaises(ValueError):load_manifest(path)

    def test_endpoint_revision_and_timestamp_binding(self):
        for mutate in [lambda b:b.update(source_reference='https://example.invalid/events.json'),
                       lambda b:b.update(provider_revision='b'*40)]:
            data=copy.deepcopy(self.manifest);b=copy.deepcopy(self.documents['events']);mutate(b)
            data['matches'][0]['artifacts']={'events':b}
            path=self.root/(str(len(list(self.root.iterdir())))+'.json');write_new(path,data)
            with self.assertRaises(EvidenceConflict):load_manifest(path)
        b=copy.deepcopy(self.documents['events']);b['retrieved_at']='2026-10-27'
        with self.assertRaises(ValueError):bound_document(b)

    def test_oversized_and_malformed_response_fail_accounting(self):
        store=self.store()
        result=store.execute([10],allow_network=True,batch_limit=1,transport=lambda _:b'x'*(MAX_BYTES+1))
        self.assertEqual(result[0]['status'],'SOURCE_PAIR_INCOMPLETE')
        self.assertEqual(store.accounting()['failures'],2)
        self.assertEqual(list((store.root/'objects').iterdir()),[])

    def test_schema_rejection_never_certifies(self):
        store=self.store()
        self.raw['events']=payload([{'missing':'required event fields'}])
        result=store.execute([10],allow_network=True,batch_limit=1,transport=self.transport)[0]
        self.assertEqual(result['status'],'SOURCE_REJECTED')
        self.assertFalse(result['report']['production_certified'])
        self.assertEqual(store.execute([10])[0]['status'],'SOURCE_REJECTED')

    def test_conflicting_appearance_report_not_certified(self):
        self.events.append(dict(id='dismissal',period=2,timestamp='00:15:00.000',minute=60,second=0,
            type=dict(name='Bad Behaviour'),team=dict(id=1,name='Home'),player=dict(id=101,name='Home Player'),bad_behaviour=dict(card=dict(name='Red Card'))))
        raw=payload(self.events);Path(self.documents['events']['path']).write_bytes(raw);self.documents['events']['sha256']=digest(raw)
        store=self.store(True);result=store.execute([10])[0]
        self.assertEqual(result['report']['active_status_counts']['CONFLICTING_EVIDENCE'],1)
        actor=result['report']['players'][0]
        self.assertIsNone(actor['validation']['elapsed_seconds']);self.assertTrue(actor['player']['source_checks'])

    def test_resume_dry_run_accounts_completed_downloads_read_only(self):
        store=self.store();store.execute([10],allow_network=True,batch_limit=1,transport=self.transport)
        before={p:p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
        plan=dry_run(self.path,destination=store.root,match_ids=[10])
        self.assertEqual(plan['obtained_match_pair_ids'],[10]);self.assertEqual(plan['additional_match_pairs_required'],0)
        self.assertEqual(plan['request_accounting']['successes'],2)
        self.assertEqual(before,{p:p.read_bytes() for p in store.root.rglob('*') if p.is_file()})

    def test_dry_run_conflict_visible_and_never_filled(self):
        store=self.store(True);Path(self.documents['events']['path']).write_bytes(b'[]')
        plan=dry_run(self.path,destination=store.root)
        self.assertEqual(plan['obtained_match_pair_ids'],[])
        self.assertEqual(plan['integrity_conflicts'][0]['match_id'],10)
        self.assertEqual(store.accounting()['successes'],0)

    def test_existing_report_never_overwritten_or_silently_reused(self):
        store=self.store()
        report=dict(match_id=10,artifact_validation='SOURCE_EVIDENCE_CONFLICT',production_certified=False)
        path=store.root/'reports'/f'10-{digest(payload(report))}.json'
        path.write_bytes(b'synthetic corrupted report')
        with self.assertRaises(EvidenceConflict):store.save_report(10,report)
        self.assertEqual(path.read_bytes(),b'synthetic corrupted report')


if __name__=='__main__':unittest.main()
