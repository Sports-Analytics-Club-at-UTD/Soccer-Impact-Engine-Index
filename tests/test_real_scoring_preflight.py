"""Invented fixtures test preparation only; test receipts grant no real approval."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_real_candidate_analysis as fixtures
from src import real_scoring_preflight as preflight
from src.source_reconstruction import rational, exact
from src.rating_pipeline import synthetic_rating_delivery
from src.defensive_candidates import evaluate_defensive_candidates
from src import press_scoring


def check(c):
    return dict(player_id=c['player_id'], team_id=c['team_id'], team=c['team'],
        competition_name=c['competition_name'], season_name=c['season_name'],
        independent_seconds=rational(exact(c['supported_minutes'])*60),
        unresolved_appearances=c['withheld_appearance_count'], actor_findings=0,
        reference_member=False, fully_evidence_ready=False, production_certified=False,
        publication_authorized=False, technical_candidate_checks_passed=True,
        source_dominant_group_agrees=True, delivered_comparison_group='CB',
        transfer_reference_ambiguous=False, blockers=['approval_pending'])


def prepared():
    c = fixtures.club()
    return preflight.prepare([c], [check(c)], provenance='INVENTED_TEST_ONLY')


def receipt(report):
    c = report['contexts'][0]
    return dict(schema_version='real-scoring-review-receipt/v1',
        decision_scope='evidence_and_club_membership_only', reviewer='INVENTED TEST REVIEWER',
        authority='INVENTED TEST AUTHORITY', reviewed_at='2026-10-28',
        independent_basis='INVENTED TEST BASIS', decision_version='test-only/v1',
        bindings=dict(source_manifest_sha256=preflight.SOURCE_SEAL,
            verification_manifest_sha256=preflight.CHECK_SEAL,
            review_request_sha256=preflight.REQUEST_SEAL, mapping_sha256=report['mapping_sha256']),
        fixture_policy='delivered_scope_excluding_3879594',
        source_scope='four_provider_inventories_2015_16_ligue1_377',
        exposure_role_attested=True, successful_interceptions_retained=True,
        private_computation_approved=True, publication_authorized=False,
        memberships=[{k:c[k] for k in ('player_id','team_id','team','competition_name','season_name','comparison_group')} |
                     dict(reference_unit='club_context')])


def validate(report, r):
    return preflight.validate_receipt(report, r, trusted_receipt_sha256=preflight.canonical_hash(r))


class RealScoringPreflightTests(unittest.TestCase):
    def test_exact_contract_mapping_preserves_inputs(self):
        c=fixtures.club(); before=copy.deepcopy(c)
        p=preflight.prepare([c],[check(c)],provenance='fixture')
        self.assertEqual(c,before)
        self.assertEqual(p.report['technical_candidates'],1)
        self.assertEqual(exact(p.report['contexts'][0]['exact_minutes']),900)
        self.assertEqual(p.measurements.iloc[0]['count'],10)
        self.assertEqual(list(p.actions.columns),press_scoring.ACTION_COLUMNS)
        self.assertFalse(p.population.reference_member.any())
        self.assertEqual(p.pool.coverage_evidence.kind,'UNVERIFIED')
        self.assertFalse(p.report['scoring_enabled'])

    def test_order_determinism_and_repeated_preparation(self):
        a,b=fixtures.club(),fixtures.club(pid=102,mid=11)
        x=preflight.prepare([a,b],[check(a),check(b)],provenance='fixture')
        y=preflight.prepare([b,a],[check(b),check(a)],provenance='fixture')
        self.assertEqual(x.report,y.report)
        self.assertTrue(x.actions.equals(y.actions))

    def test_conflicting_identity_exposure_and_actor_rejected(self):
        c=fixtures.club()
        for field,value in [('team_id',99),('independent_seconds',rational(1)),('actor_findings',1),
                            ('unresolved_appearances',1),('reference_member',True)]:
            v=check(c);v[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                preflight.prepare([c],[v],provenance='fixture')
        with self.assertRaises(ValueError):preflight.prepare([c],[],provenance='fixture')
        with self.assertRaises(ValueError):preflight.prepare([c,c],[check(c)],provenance='fixture')

    def test_missing_counts_and_foreign_scope_rejected(self):
        for mode in ('missing','conflict','scope'):
            c=fixtures.club();v=c['delivered_scope_comparison']['components']['interceptions']
            if mode=='missing':v['raw_source_count']=None
            elif mode=='conflict':v['provider_scope_per90']=999
            else:v['aligned_match_ids']=[100]
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                preflight.prepare([c],[check(c)],provenance='fixture')

    def test_incomplete_exposure_retains_count_withholds_denominator(self):
        c=fixtures.club(status='INCOMPLETE_EVIDENCE')
        p=preflight.prepare([c],[check(c)],provenance='fixture')
        r=p.report['contexts'][0]
        self.assertFalse(r['technically_mappable']);self.assertIsNone(r['exact_minutes'])
        self.assertEqual(r['components']['tackles']['delivered_scope_count'],10)
        with self.assertRaises(ValueError):validate(p.report,receipt(p.report))

    def test_excluded_fixture_is_not_added_to_scoring_scope(self):
        c=fixtures.club(mid=3879594)
        p=preflight.prepare([c],[check(c)],provenance='fixture')
        self.assertEqual(p.report['contexts'][0]['excluded_match_ids'],[3879594])
        self.assertEqual(p.report['contexts'][0]['analysis_match_ids'],[])
        self.assertIsNone(p.actions.iloc[0].numerator_scope)
        r=receipt(prepared().report);r['fixture_policy']='include_3879594'
        with self.assertRaises(ValueError):validate(prepared().report,r)

    def test_unsigned_and_untrusted_receipts_rejected(self):
        p=prepared()
        with self.assertRaises(ValueError):validate(p.report,{'document_kind':'UNSIGNED_REVIEW_REQUEST_NOT_AN_ATTESTATION'})
        r=receipt(p.report)
        for trust in (None,'0'*64):
            with self.assertRaises(ValueError):preflight.validate_receipt(p.report,r,trusted_receipt_sha256=trust)
        for field in ('reviewer','authority','reviewed_at','independent_basis','decision_version'):
            bad=copy.deepcopy(r);bad[field]=None
            with self.subTest(field=field),self.assertRaises(ValueError):validate(p.report,bad)

    def test_stale_bindings_and_unapproved_membership_rejected(self):
        p=prepared();r=receipt(p.report)
        for field in r['bindings']:
            bad=copy.deepcopy(r);bad['bindings'][field]='0'*64
            with self.subTest(field=field),self.assertRaises(ValueError):validate(p.report,bad)
        for members in ([],[r['memberships'][0],r['memberships'][0]],
                        [r['memberships'][0]|{'player_id':999}],
                        [r['memberships'][0]|{'comparison_group':'MID'}]):
            bad=copy.deepcopy(r);bad['memberships']=members
            with self.assertRaises(ValueError):validate(p.report,bad)

    def test_transfer_nomination_explicit_and_never_aggregated(self):
        a,b=fixtures.club(),fixtures.club(team='Away',mid=11)
        ca,cb=check(a),check(b);ca['transfer_reference_ambiguous']=cb['transfer_reference_ambiguous']=True
        p=preflight.prepare([a,b],[ca,cb],provenance='fixture');r=receipt(p.report)
        with self.assertRaises(ValueError):validate(p.report,r)
        r['memberships'][0]['transfer_decision']='nominate_this_club_only'
        self.assertEqual(validate(p.report,r)['nominated_members'],1)
        second={k:p.report['contexts'][1][k] for k in ('player_id','team_id','team','competition_name','season_name','comparison_group')}
        r['memberships'].append(second|dict(reference_unit='club_context',transfer_decision='nominate_this_club_only'))
        with self.assertRaises(ValueError):validate(p.report,r)

    def test_receipt_acceptance_never_promotes_or_scores(self):
        p=prepared();before=copy.deepcopy(p.report)
        result=validate(p.report,receipt(p.report))
        self.assertFalse(result['scoring_enabled']);self.assertFalse(result['publication_authorized'])
        self.assertEqual(p.report,before);self.assertFalse(p.population.reference_member.any())
        with self.assertRaises(ValueError):evaluate_defensive_candidates(p.population,p.measurements,pool=p.pool,policy=None)
        with self.assertRaises(ValueError):synthetic_rating_delivery(p.population,p.measurements,p.actions,
            pool=p.pool,defensive_policy=None,press_policy=None,evidence=p.pool.coverage_evidence,names={})

    def test_loader_rejects_changed_seal_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'run-manifest.json').write_text('{}',encoding='utf-8')
            before=(root/'run-manifest.json').read_bytes()
            with self.assertRaises(ValueError):preflight.load_preflight(root,root,root/'run-manifest.json')
            self.assertEqual(before,(root/'run-manifest.json').read_bytes())

    def test_selected_artifact_requires_exact_hash_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'facts';p.write_text('facts',encoding='utf-8')
            manifest={'artifacts':[dict(path='facts',size_bytes=5,sha256=preflight.digest(p))]}
            self.assertEqual(preflight._artifact(root,manifest,'facts'),p)
            p.write_text('other',encoding='utf-8')
            with self.assertRaises(ValueError):preflight._artifact(root,manifest,'facts')


if __name__=='__main__':unittest.main()
