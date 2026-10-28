"""Consume the sealed Step 2 bundle offline; preserve existing numeric gates."""
import argparse
from dataclasses import asdict,is_dataclass
import json
import math
from pathlib import Path

import numpy as np

from scripts.reconstruct_player_evidence import (file_hash,records,line,recipe,verify_existing)
from scripts.source_verification_batch import load_json,write_new
from src.real_candidate_analysis import analyze,summarize,NOTICE,COHORT
from src.source_reconstruction import key
from src.rating_assembly import PlayerContext
from src.rating_pipeline import readiness_rating_delivery,synthetic_rating_delivery
from src.rating_delivery import serialize_delivery
from src.defensive_candidates import (evaluate_defensive_candidates,DefensivePolicy,POLICY_ID,SOURCE,FORMULA)
from src import press_scoring

DEFAULT_INPUT=Path('data/derived/phase3-step2-source-reconstruction-2026-10-27')
CODE=['src/real_candidate_analysis.py','scripts/analyze_real_candidates.py',
      'scripts/check_real_candidate_handoff.mjs','src/rating_pipeline.py','src/rating_delivery.py',
      'src/rating_assembly.py','src/defensive_candidates.py','src/press_scoring.py',
      'src/dri_scoring.py','src/transfer_aggregation.py','src/identity.py','src/identity_evidence.py',
      'src/source_reconstruction.py','src/metrics/press_actions.py','frontend/src/lib/ratingDelivery.js',
      'frontend/src/lib/ratingCard.js','frontend/src/lib/archetypes.js']


def jsonable(value):
    if is_dataclass(value):return jsonable(asdict(value))
    if isinstance(value,dict):return {k:jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [jsonable(v) for v in value]
    if value is None or isinstance(value,(str,bool,int)):return value
    if isinstance(value,np.integer):return int(value)
    if isinstance(value,(float,np.floating)):return float(value) if math.isfinite(value) else None
    raise TypeError('unsupported artifact value: '+str(type(value)))


def implementation():
    return dict(core_recipe=recipe(),files={p:file_hash(p) for p in CODE})


def verify_source(run):
    sealed=load_json(run/'run-manifest.json')
    summary=verify_existing(run,[Path(p) for p in sealed['input_paths']],recipe())
    if sealed['schema_version']!='source-reconstruction-run/v1' or summary['schema_version']!='source-player-reconstruction/v1':
        raise ValueError('unsupported sealed source reconstruction schema')
    if summary['production_certified_contexts']!=0 or summary['publication_authorized'] is not False:
        raise ValueError('unexpected source certification state')
    coverage=load_json(run/'evidence-coverage-and-missingness.json')
    if coverage['missing_delivered_fixture_ids'] not in ([],[3879594]):raise ValueError('unexpected delivered fixture scope change')
    if load_json(run/'360-coverage.json')['target_rows']!=0:raise ValueError('target 360 evidence changed; review required')
    return sealed,summary,coverage


def rejected(call):
    try:call()
    except ValueError as e:return dict(result='REJECTED_AS_EXPECTED',reason=str(e))
    raise ValueError('existing synthetic-only gate unexpectedly accepted real inputs')


def build(run,output):
    run,output=Path(run),Path(output)
    revision=implementation();sealed,source_summary,coverage=verify_source(run)
    source_ref=dict(path=str(run.resolve()),run_manifest_sha256=file_hash(run/'run-manifest.json'))
    if output.exists():
        old=load_json(output/'run-manifest.json')
        if old['implementation']!=revision or old['source']!=source_ref:raise ValueError('analysis input/code conflict')
        for r in old['artifacts']:
            if file_hash(output/r['path'])!=r['sha256']:raise ValueError('analysis fingerprint conflict: '+r['path'])
        return load_json(output/'summary.json')
    clubs=list(records(run/'player-club-summaries.jsonl'))
    if len(clubs)!=source_summary['player_club_contexts']:raise ValueError('source context cardinality changed')
    source=f'{run.as_posix()}/run-manifest.json#sha256={source_ref["run_manifest_sha256"]}'
    facts,result,pop,metrics,pool=analyze(clubs,source=source,excluded_match_ids=coverage['missing_delivered_fixture_ids'])
    bindings={};actor_matches={}
    for a in records(run/'appearance-ledger.jsonl'):
        k=key(a);mid=a['match_id']
        if mid in actor_matches.setdefault(k,set()):raise ValueError('duplicate source appearance in ledger')
        actor_matches[k].add(mid)
        binding=dict(match_id=mid,competition_name=a['competition_name'],season_name=a['season_name'],
            source_documents=a['source_documents'],fixture_reference=a['fixture_reference'],fixture_sha256=a['fixture_sha256'],
            review_reference=a['review_reference'])
        if mid in bindings and bindings[mid]!=binding:raise ValueError('source provenance disagrees within match')
        bindings[mid]=binding
    if len(bindings)!=source_summary['provider_matches']:raise ValueError('source match coverage changed')
    if set(actor_matches)!={key(c) for c in clubs} or any(actor_matches[key(c)]!=set(c['match_ids']) for c in clubs):
        raise ValueError('summary identity/match association differs from source ledger')
    old_readiness=load_json(run/'existing-season-readiness.json')
    by_key={key(c):c for c in clubs};names={};roles={}
    for r in old_readiness['contexts']:
        c=by_key[key(r)];ctx=PlayerContext(**{k:r[k] for k in ('player_id','team','competition_name','season_name')})
        names[ctx]=' / '.join(c['raw_player_names']);roles[ctx]=c['delivered_role']
    handoff=readiness_rating_delivery(old_readiness,names=names,roles=roles,source=source,cohort_id=COHORT)
    probes=dict(defensive_components=rejected(lambda:evaluate_defensive_candidates(pop,metrics,pool=pool,policy=None)),
        press=rejected(lambda:press_scoring.evaluate_press_candidates(pop,None,pools=None,evidence=pool.coverage_evidence,policy=None)),
        numeric_delivery=rejected(lambda:synthetic_rating_delivery(pop,metrics,None,pool=pool,defensive_policy=None,
            press_policy=None,evidence=pool.coverage_evidence,names={})))
    summary=summarize(facts,result)
    summary.update(source=source_ref,source_matches=source_summary['provider_matches'],source_stable_player_ids=source_summary['stable_player_ids'],
        delivery_fixture_exclusions=coverage['missing_delivered_fixture_ids'],offline_withheld_contract_records=len(handoff['players']),
        existing_numeric_boundaries_held=all(p['result']=='REJECTED_AS_EXPECTED' for p in probes.values()))
    transfers=list(records(run/'transfer-policy-comparison.jsonl'))
    output.mkdir(parents=True,exist_ok=False)
    artifacts=[dict(path=p.name,size_bytes=p.stat().st_size,sha256=file_hash(p)) for p in sorted(run.iterdir()) if p.is_file()]
    write_new(output/'source-receipt.json',dict(**source_ref,notice=NOTICE,source_artifacts=artifacts,
        original_inputs_verified=True,reconstruction_restarted=False))
    with (output/'component-candidates.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for r in facts:
            r['provenance']=dict(appearance_ledger='appearance-ledger.jsonl',measurement_ledger='match-component-measurements.jsonl',
                source_bundle=source_ref,match_bindings='match-source-bindings.jsonl')
            line(f,r)
    with (output/'match-source-bindings.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for mid in sorted(bindings):line(f,bindings[mid])
    with (output/'dri-engine-results.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for r in result.players.to_dict('records'):line(f,jsonable(r))
    write_new(output/'dri-engine-inputs.json',jsonable(dict(population=pop.to_dict('records'),measurements=metrics.to_dict('records'),
        pool=pool,notice=NOTICE,expected_evidence_kind_explained='VERIFIED is the engine requirement; all supplied attestations are UNVERIFIED and incomplete')))
    write_new(output/'dri-reference-pools.json',jsonable(dict(pools=result.pools.to_dict('records'),metadata=result.metadata,
        reference_policy_approved=False,notice=NOTICE)))
    write_new(output/'existing-boundary-checks.json',probes)
    write_new(output/'formula-and-gate-register.json',dict(notice=NOTICE,
        dri=dict(implementation='src.dri_scoring.score_dri',approval_record='docs/d3a-approved-dri-scoring.md',
            formula='Equal mean of three per90 average-rank percentiles; sample-z transform clip(65+10*z,1,99)',
            aggregate_formula_approved=True,source_role_exposure_reference_attestations_approved=False,numeric_result=None),
        individual_defensive=dict(implemented_policy=asdict(DefensivePolicy(POLICY_ID,SOURCE,FORMULA,True)),approved=False,
            real_input_supported=False,reason='Existing scorer is synthetic-only; no relabeling or copied transform'),
        press=dict(implemented_formulas=[press_scoring.FIFA,press_scoring.PERCENTILE],approved=False,
            min_actions_comparisons=[30,50],selected_policy=None,real_input_supported=False),
        progressive=dict(implementation='src.metrics.progressive_passes.flag_progressive',level='A',
            true_line_breaking=False,approved_rating_formula=None,target_360_rows=0),
        archetype=dict(gold_percentile_minimum=90,silver_percentile_minimum=75,silver_percentile_maximum_exclusive=90,
            implementation='src.rating_delivery.archetype',percentiles_available=False),
        overall=dict(formula=None,rating=None,reason='policy_not_finalized')))
    write_new(output/'transfer-policy-readiness.json',dict(notice=NOTICE,source_file='transfer-policy-comparison.jsonl',source_bundle=source_ref,
        source_file_sha256=file_hash(run/'transfer-policy-comparison.jsonl'),multi_club_player_seasons=len(transfers),
        threshold_change_player_ids=[r['player_id'] for r in transfers if r['threshold_changes_if_combination_authorized']],
        policy_selected=None,reference_contexts_nominated=[],ratings_averaged=False))
    with (output/'offline-withheld-contract-fixture.json').open('x',encoding='utf-8',newline='\n') as f:f.write(serialize_delivery(handoff))
    write_new(output/'website-handoff.json',dict(notice=NOTICE,schema='soccer-rating-delivery/v1',
        legacy_fixed_notice=handoff['notice'],legacy_notice_is_not_real_numeric_authorization=True,
        diagnostic_contract_supported=True,real_numeric_contract_supported=False,fixture_records=len(handoff['players']),
        fixture='offline-withheld-contract-fixture.json',deployed_files_modified=False,
        remaining=['independent source/identity/exposure/numerator attestations','approved role and transfer/reference membership',
            'individual defensive and press policy decisions','true line-breaking evidence/definition or continued N/A',
            'OVR decision or continued N/A','reviewed versioned real numeric delivery contract and parser',
            'offline integration validation','explicit website publication authorization']))
    write_new(output/'summary.json',summary)
    if implementation()!=revision:raise ValueError('analysis implementation changed during run; output unsealed')
    write_new(output/'run-manifest.json',dict(schema_version='provisional-real-candidate-run/v1',notice=NOTICE,source=source_ref,
        implementation=revision,artifacts=[dict(path=p.name,size_bytes=p.stat().st_size,sha256=file_hash(p)) for p in sorted(output.iterdir())],
        production_certified=False,publication_authorized=False))
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=DEFAULT_INPUT)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    print(json.dumps(build(args.input,args.output),sort_keys=True,indent=2))


if __name__=='__main__':main()
