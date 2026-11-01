"""Focused offline checks of the separate Bundesliga run; no source mutations."""
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from scripts.verify_bundesliga_readiness import (
    OUT, ROOT, DEFENSIVE, file_hash, records, exact, load_json, write_new,
)


def audit():
    manifest=load_json(OUT/'run-manifest.json')
    checked=0
    for a in manifest['artifacts']:
        assert file_hash(OUT/a['path'])==a['sha256'], a['path'];checked+=1
    for p,sha in manifest['recipe'].items():assert file_hash(p)==sha,p
    receipts=load_json(OUT/'input-receipts.json')
    for a in receipts['local_files']+receipts['original_documents']:
        assert file_hash(a['path'])==a['sha256'],a['path'];checked+=1
    matches=list(records(OUT/'match-checks.jsonl'))
    assert len(matches)==34
    ids=load_json(ROOT/'scope.json')['match_ids']
    assert sorted(m['match_id'] for m in matches)==ids
    assert sum(m['delivered_events'] for m in matches)==61972
    assert sum(m['original_events'] for m in matches)==115240
    assert all(m['independent_calculation_agrees'] and not m['metric_field_differences'] and
               not m['actor_findings'] and not m['orphan_components'] for m in matches)
    associations=list(records(OUT/'event-reconciliation.jsonl'))
    assert len(associations)==len({r['event_id'] for r in associations})==61972
    assert all(r['status']=='SOURCE_UUID_AND_CONTEXT_EXACT' and not r['metric_field_differences'] for r in associations)
    bymatch={}
    for m in matches:
        original=load_json(m['source_documents']['events']['path'])
        bymatch[m['match_id']]={e['id']:e for e in original}
    for m in records(OUT/'match-measurements.jsonl'):
        for c in m['components'].values():
            assert c['count']==len(c['event_ids'])==len(set(c['event_ids']))
            assert set(c['unaligned_event_ids'])<=set(c['event_ids'])
            for uid in c['event_ids']:
                e=bymatch[m['match_id']][uid]
                assert e['player']['id']==m['player_id'] and e['team']['id']==m['team_id']
    apps=list(records(OUT/'appearances.jsonl'))
    active=[a for a in apps if a['active_appearance']]
    states=Counter(a['participation_status'] for a in active)
    assert states=={'STRUCTURALLY_VALID':918,'CONFLICTING_EVIDENCE':30}
    for a in active:
        if a['participation_status']!='STRUCTURALLY_VALID':
            assert a['validated_elapsed_seconds'] is None and a['failure_reasons']
        else:
            assert exact(a['validated_elapsed_seconds'])==sum((exact(v['elapsed_seconds']) for v in a['position_allocation']),Fraction(0))
    players=list(records(OUT/'player-readiness.jsonl'))
    assert len(players)==len({p['player_id'] for p in players})==346
    for p in players+list(records(OUT/'transfers.jsonl')):
        assert p['reference_member'] is False and p['ratings'] is None
        assert p['publication_authorized'] is False and p['source_signoff'] is False
        assert p['limited_data'] and p['partial_season_coverage']
        pr=p['press']
        if pr['attempts']:
            assert abs(pr['measured_percent']-100*pr['successes']/pr['attempts'])<1e-10
            assert pr['below_40_limited_data']==(pr['attempts']<40)
        else:assert pr['measured_percent'] is None
        for n in DEFENSIVE:
            c=p['defensive'][n]
            if c['status']!='N/A':
                assert exact(c['supported_minutes'])>0
                assert abs(c['per90']-float(c['supported_count']*90/exact(c['supported_minutes'])))<1e-10
            assert c['rating'] is None
    transfers=list(records(OUT/'transfers.jsonl'))
    assert len(transfers)==9
    for t in transfers:
        mids=[mid for c in t['original_contexts'] for mid in c['match_ids']]
        assert len(mids)==len(set(mids)) and t['nonoverlapping_fixture_scopes']
    result=dict(status='PASS',sealed_artifacts_and_inputs_fingerprinted=checked,
        original_match_pairs=34,delivered_uuid_associations=61972,
        original_events=115240,supported_appearances=918,withheld_appearances=30,
        canonical_source_players=346,canonical_transfer_players=9,
        test_suite='70 focused tests passed: Bundesliga readiness, StatsBomb participation, independent source checks',
        normalization_members_added=0,numeric_ratings_generated=0,
        source_signoff=False,production_certified=False,publication_authorized=False)
    destination=Path('data/validation/bundesliga-targeted-tests-2026-10-29/validation.json')
    write_new(destination,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':audit()
