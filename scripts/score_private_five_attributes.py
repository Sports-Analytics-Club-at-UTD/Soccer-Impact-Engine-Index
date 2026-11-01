"""Offline five-attribute experiments over existing sealed measurements only.

No original event files, Parquets, acquisition, reconstruction or production
delivery are used. A new private output directory is always required.
"""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path

from scripts.prepare_fifth_attribute import records, sha
from src.private_five_attribute import (VERSION,NOTICE,ATTRIBUTES,PRESS_COUNTS,POLICY,
    aggregate,digest,freeze_reference,score_players,validate_reference,require)
from src.source_reconstruction import exact
from src.rating_delivery import validate_delivery as production_delivery
from src.provisional_delivery import validate_delivery as observation_delivery

FIFTH=Path('data/derived/fifth-attribute-private-v1')
VALIDATED=Path('data/validation/fifth-attribute-tests-v1/package-validation.json')
FOUR=Path('data/derived/phase3-step2-source-reconstruction-2026-10-27')
BUNDES=Path('data/derived/bundesliga-targeted-2026-10-29')
CODE=['src/private_five_attribute.py','scripts/score_private_five_attributes.py',
    'src/fifth_attribute.py','src/dri_scoring.py','src/metrics/recovery_coverage.py','src/metrics/press_actions.py']


def inputs():
    """Reuse verification results and their byte bindings, not their audit jobs."""
    validation=json.loads(VALIDATED.read_text())
    require(validation['status']=='PASS' and sha(FIFTH/'manifest.json')==validation['private_package']['manifest.json'],
        'completed fifth-attribute package validation binding required')
    manifest=json.loads((FIFTH/'manifest.json').read_text())
    for name in ('player-measurements.jsonl','match-observations.jsonl'):
        require(sha(FIFTH/name)==manifest['artifacts'][name],'fifth measurement changed: '+name)
    for source in manifest['inputs']:
        seal=Path(source['path'])
        require(sha(seal)==source['sha256'],'existing source seal changed')
        # Only the component ledgers used by this integration are loaded.
        for name in ('match-component-measurements.jsonl','match-measurements.jsonl'):
            if name in source['artifacts']:
                require(sha(seal.parent/name)==source['artifacts'][name],'existing component ledger changed')
    return dict(fifth_manifest_sha256=sha(FIFTH/'manifest.json'),
        completed_validation_sha256=sha(VALIDATED),source_seals=manifest['inputs'],
        measurement_files={str(FIFTH/n):sha(FIFTH/n) for n in ('player-measurements.jsonl','match-observations.jsonl')})


def prepare_facts(observations, metric_rows):
    """Adapt already verified actor/fixture components; do not re-read events."""
    index={}
    for r in observations:
        k=(r['player_id'],r['match_id'])
        require(k not in index,'duplicate Joseph canonical appearance')
        index[k]=r
    seen=set();facts=[]
    for m in metric_rows:
        k=(m['player_id'],m['match_id']);require(k in index and k not in seen,'component/canonical fixture mismatch')
        seen.add(k);r=index[k]
        require((m['season_name'],m['competition_name'],m['team'])==(r['season_name'],r['competition_name'],r['team']),
            'canonical player/club/league/season disagreement')
        pending=r['match_id']==3879594
        metrics={}
        for a in ('tackles','interceptions','recoveries'):
            c=m['components'][a]
            reasons=sorted(set(c['reasons']+(['PENDING_DELIVERED_FIXTURE_SCOPE'] if pending else [])))
            require((c['status']=='SOURCE_VERIFIED_CANDIDATE_MEASUREMENT')==(not c['reasons']), 'sealed support status contradicts reasons')
            metrics[a]=dict(counts={'count':c['count']},numerator_ids=c['event_ids'],denominator_ids=None,
                seconds=r['seconds'],supported=not reasons,reasons=reasons)
        cs={n:m['components'][n]['count'] for n in PRESS_COUNTS}
        attempts=m['components'][PRESS_COUNTS[0]]['event_ids']+m['components'][PRESS_COUNTS[2]]['event_ids']
        successes=m['components'][PRESS_COUNTS[1]]['event_ids']+m['components'][PRESS_COUNTS[3]]['event_ids']
        # Duration is not the denominator of this action ratio. Retain the
        # existing Bundesliga policy even where participation duration is unknown.
        reasons=sorted({v for n in PRESS_COUNTS for v in m['components'][n]['reasons']
                        if v in ('UNRESOLVED_COMPONENT_ACTOR_IN_MATCH',)} |
                       ({'PENDING_DELIVERED_FIXTURE_SCOPE'} if pending else set()))
        metrics['press_resistance']=dict(counts=cs,numerator_ids=sorted(successes),
            denominator_ids=sorted(attempts),seconds=r['seconds'],supported=not reasons,reasons=reasons)
        c=m['components']['progressive_passes']
        if not r['reasons']:require(c['count']==r['prog_passes'],'Joseph measurement count disagreement')
        metrics['progressive_passing']=dict(counts={'count':c['count']},numerator_ids=c['event_ids'],
            denominator_ids=None,seconds=r['seconds'],supported=not r['reasons'],reasons=r['reasons'])
        facts.append(dict(player_id=r['player_id'],season_name=r['season_name'],match_id=r['match_id'],
            competition_name=r['competition_name'],team=r['team'],seconds=r['seconds'],metrics=metrics,
            evidence=dict(component_ledger=str(BUNDES/'match-measurements.jsonl' if r['competition_name']=='1. Bundesliga' else FOUR/'match-component-measurements.jsonl'),
                component_player_id=m['player_id'],component_team_id=m['team_id'],component_match_id=m['match_id'],
                joseph_ledger=str(FIFTH/'match-observations.jsonl'))))
    require(seen==set(index),'component ledger omitted canonical appearances')
    return sorted(facts,key=lambda r:(r['player_id'],r['match_id']))


def summary(players, scored, baseline):
    def tally(rows):
        totals=Counter(sum(m['experimental_rating'] is not None for m in p['attributes'].values()) for p in rows)
        return dict(examined=len(rows),all_five=totals[5],partial=sum(totals[n] for n in range(1,5)),no_scores=totals[0],
            groups={g:{a:dict(measured=sum(p['comparison_group']==g and p['attributes'][a]['value'] is not None for p in rows),
                scored=sum(p['comparison_group']==g and p['attributes'][a]['experimental_rating'] is not None for p in rows))
                for a in ATTRIBUTES} for g in ('MID','CB')})
    return dict(schema_version=VERSION,notice=NOTICE,canonical_player_seasons=len(players),
        combined=tally(scored),four_league_only=tally([p for p in scored if not p['limited_data']]),
        bundesliga_contributors=tally([p for p in scored if p['limited_data']]),
        references={g:{a:{k:v for k,v in pool.items() if k not in ('members','member_ids')} for a,pool in pools.items()} for g,pools in baseline['pools'].items()},
        baseline_sha256=baseline['sha256'],policy=POLICY,
        score_na_reasons=dict(Counter(m['score_reason'] for p in scored for m in p['attributes'].values() if m['score_reason'])),
        conflicts=['Successful interceptions retained, not PDF total interceptions.',
            'Press uses existing pressured Pass/Dribble ratio, not Joseph broader retention; no open-play filter or progressive weighting.',
            '40-action rule is this authorized private experiment, not retroactive official adoption of D3C candidate thresholds.',
            'Progressive Passing Proxy is Joseph Level A, not verified opponent-line breaks.',
            'Observed fixtures and supported elapsed minutes do not establish full-season completeness; pending 3879594 excluded.',
            'Attribute fixture scopes and reference memberships differ; no common-scope OVR or weights are inferred.'],
        official_numeric_ratings=0,ovr_calculated=False,publication_authorized=False)


def build(output, baseline_path=None):
    output=Path(output)
    require(not output.exists(),'new private output directory required')
    bound=inputs();binding=digest(bound)
    players=list(records(FIFTH/'player-measurements.jsonl'))
    observations=list(records(FIFTH/'match-observations.jsonl'))
    def components():
        yield from records(FOUR/'match-component-measurements.jsonl')
        yield from records(BUNDES/'match-measurements.jsonl')
    facts=prepare_facts(observations,components())
    measured=aggregate(players,facts)
    if baseline_path is None:baseline=freeze_reference(measured,input_binding=binding)
    else:
        baseline=validate_reference(json.loads(Path(baseline_path).read_text()))
        require(baseline['input_binding']==binding,'frozen reference belongs to different bound measurement inputs')
        require(baseline['sha256']==freeze_reference(measured,input_binding=binding)['sha256'],
            'frozen membership/statistics disagree with this versioned eligible input snapshot')
    scored=score_players(measured,baseline)
    # Determinism of the aggregation and scoring, not reconstruction or another
    # pass over original evidence. Recipients never alter the frozen reference.
    require(aggregate(list(reversed(players)),list(reversed(facts)))==measured,'non-deterministic aggregation')
    frozen_before=copy.deepcopy(baseline)
    require(score_players(list(reversed(measured)),baseline)==scored and baseline==frozen_before,'non-deterministic scoring/reference mutation')
    conservation={}
    for a in ATTRIBUTES:
        supported=[r['metrics'][a] for r in facts if r['metrics'][a]['supported']]
        names=PRESS_COUNTS if a=='press_resistance' else ('count',)
        sums={n:sum(m['counts'][n] for m in supported) for n in names}
        for n,total in sums.items():
            require(total==sum(p['attributes'][a]['raw_counts'][n] for p in measured if p['attributes'][a]['raw_counts'] is not None),'raw count conservation failed')
        conservation[a]=sums
    # Preserve Joseph's completed metric without recalculating his method.
    for old,new in zip(sorted(players,key=lambda p:p['player_id']),measured):
        m=new['attributes']['progressive_passing']
        require(old['prog_passes']==m['numerator'] and old['supported_match_ids']==m['numerator_match_ids'] and
            old['supported_minutes']==m['supported_minutes'],'Joseph player-season parity failed')
    envelope=dict(schema_version=VERSION+'/scores',notice=NOTICE,players=scored,publication_authorized=False)
    for validator in (production_delivery,observation_delivery):
        try:validator(envelope)
        except ValueError:pass
        else:raise ValueError('experimental scores admitted to existing delivery')
    result=summary(measured,scored,baseline)
    validation=dict(status='PASS',determinism=True,frozen_reference_unchanged=True,conservation=conservation,
        joseph_level_a_aggregate_parity=True,both_existing_delivery_contracts_reject=True,
        original_event_files_opened=0,source_reconstructions=0,official_numeric_ratings=0,ovr_calculated=False)
    output.mkdir(parents=True,exist_ok=False)
    def write(name,value):
        with (output/name).open('x',encoding='utf8',newline='\n') as f:
            json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    for name,rows in [('measurement-facts.jsonl',facts),('player-measurements.jsonl',measured),('PRIVATE-EXPERIMENTAL-scores.jsonl',scored)]:
        with (output/name).open('x',encoding='utf8',newline='\n') as f:
            for r in rows:f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n')
    write('frozen-reference.json',baseline);write('summary.json',result);write('validation.json',validation)
    write('manifest.json',dict(schema_version=VERSION,notice=NOTICE,inputs=bound,input_binding=binding,
        implementation={p:sha(p) for p in CODE},artifacts={p.name:sha(p) for p in sorted(output.iterdir())},
        baseline_sha256=baseline['sha256'],publication_authorized=False))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,help='Replay an existing frozen private reference; never refit on recipients')
    args=parser.parse_args();build(args.output,args.baseline)
