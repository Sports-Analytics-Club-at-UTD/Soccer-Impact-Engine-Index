"""Read-only local preview adapter for the completed frozen v2 experiment.

No scorer, population fit, approval issuer, output-file writer or original event
reader. This module is invoked only by the loopback Vite development middleware.
"""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

from src.five_attribute_presentation import LABELS, digest as projection_digest
from src.private_five_attribute import digest as frozen_digest

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'data/derived/private-five-attribute-v2'
EXPECTED_MANIFEST='5a8030b4a6ca06aeec81538221b07315c5644a9025915eb31c0bf2dab3cc9bc6'
EXPECTED_REFERENCE='403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd'
SCHEMA='soccer-local-experimental-five-attributes/v1'
NOTICE='EXPERIMENTAL PROJECT RATINGS'
DISCLAIMER='NOT OFFICIAL EA FIFA RATINGS'
MAP={a:a for a in ('tackles','interceptions','recoveries','press_resistance')}|{'line_breaking_passes':'progressive_passing'}


def require(v,message):
    if not v:raise ValueError('Local experimental preview: '+message)


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def rational(v):
    require(isinstance(v,dict) and set(v)=={'numerator','denominator'} and
        type(v['numerator']) is int and v['numerator']>=0 and type(v['denominator']) is int and v['denominator']>0,
        'invalid exact measurement')
    return Fraction(v['numerator'],v['denominator'])


def numeric(v,lo=0,hi=float('inf')):
    return type(v) in (int,float) and math.isfinite(v) and lo<=v<=hi


def index(rows):
    out={}
    for p in rows:
        pid=p['player_id'];require(type(pid) is int and 0<pid<=2**63-1 and
            p['id']==f'{pid}:2015/2016' and p['season_name']=='2015/2016' and p['id'] not in out,'invalid/duplicate canonical player-season')
        out[p['id']]=p
    return out


def reference_projection(baseline):
    positions={}
    for group,pools in baseline['pools'].items():
        positions[group]={}
        for out_key,source_key in MAP.items():
            p=pools[source_key]
            require(p['n']==len(p['member_ids'])==len(set(p['member_ids'])) and p['n']>=2 and
                numeric(p['mean']) and numeric(p['sample_sd']) and p['sample_sd']>0,'invalid frozen reference statistics')
            body=dict(population_version=baseline['policy']['id'],comparison_position=group,metric_id=out_key,
                n=p['n'],mean=p['mean'],sample_sd=p['sample_sd'],member_fingerprint=frozen_digest(p['member_ids']),
                source_reference_fingerprint=baseline['sha256'])
            positions[group][out_key]=body|{'fingerprint':projection_digest(body)}
    ref=dict(version=baseline['policy']['id'],fingerprint=baseline['sha256'],positions=positions)
    ref['projection_fingerprint']=projection_digest(ref)
    return ref


def project_player(p,measurement,reference,manifest):
    require(p['baseline_sha256']==EXPECTED_REFERENCE and p['publication_authorized'] is False and
        p['production_certified'] is False and p['reference_member'] is False and 'ovr' not in p and 'overall' not in p,
        'not an isolated experimental record')
    for k,v in measurement.items():
        if k!='attributes':require(p[k]==v,'player identity/context/position differs from frozen measurement')
    group=p['comparison_group'];require(group in ('MID','CB'),'unsupported comparison group')
    require(set(p['attributes'])==set(MAP.values()),'five attributes required')
    contexts=p['contexts'];seen=set();context_keys=set()
    for c in contexts:
        ck=(c['team'],c['competition_name'])
        require(ck not in context_keys and not seen.intersection(c['match_ids']) and len(c['match_ids'])==len(set(c['match_ids'])),
            'duplicate/overlapping transfer fixture scope')
        context_keys.add(ck);seen.update(c['match_ids'])
    require(seen==set(p['observed_match_ids']) and len(seen)==len(p['observed_match_ids']),'canonical fixture scope mismatch')
    bundes=any(c['competition_name']=='1. Bundesliga' for c in contexts)
    require(p['limited_data']==bundes and (not bundes or p['partial_season'] is True),'Bundesliga coverage labels missing')
    attrs={}
    for a,source in MAP.items():
        m=p['attributes'][source];raw=measurement['attributes'][source]
        require(all(m[k]==v for k,v in raw.items()),'score input differs from frozen measured statistic')
        rating,pct=m['experimental_rating'],m['percentile']
        require(rating is None or numeric(rating,1,99),'rating outside 1..99')
        require(pct is None or numeric(pct,0,100),'percentile outside 0..100')
        require(m['numerator_match_ids']==m['denominator_match_ids'] and set(m['numerator_match_ids'])<=seen and
            len(m['numerator_match_ids'])==len(set(m['numerator_match_ids'])),'attribute numerator/denominator fixture mismatch')
        exclusions=m['excluded_appearances'];excluded={e['match_id'] for e in exclusions}
        require(len(excluded)==len(exclusions) and excluded<=seen and all(e['reasons'] for e in exclusions),'invalid excluded appearance evidence')
        require(not excluded.intersection(m['numerator_match_ids']),'excluded metric appearances were included')
        duration=rational(m['supported_minutes']);press=a=='press_resistance';observation=None
        if m['value'] is not None:
            require(numeric(m['value']) and m['exact_value'] is not None and
                float(rational(m['exact_value']))==m['value'],'inexact measured statistic')
            n=m['numerator'];require(type(n) is int and n>=0,'missing raw numerator')
            if press:
                d=m['attempts'];require(type(d) is int and 0<d and n<=d,'invalid press sample')
                expected=Fraction(100*n,d)
            else:
                require(duration>0,'no verified per90 denominator');d=float(duration);expected=Fraction(n*90,1)/duration
            require(rational(m['exact_value'])==expected,'raw measurement denominator inconsistent')
            observation=dict(value=m['value'],unit=m['unit'],numerator=n,denominator=d,
                denominator_unit='actions' if press else 'minutes',supported_minutes=m['supported_minutes'],
                action_sample_size=m['attempts'] if press else None,match_ids=[str(mid) for mid in m['numerator_match_ids']],
                exact_value=m['exact_value'])
        if rating is None:require(pct is None and bool(m['score_reason']),'missing score lacks an explicit reason')
        else:require(observation is not None and pct is not None and m['score_reason'] is None,'score has absent measurement/percentile')
        pool=reference['positions'][group][a]
        attrs[a]=dict(label=LABELS[a],measurement_kind='progressive_passing_proxy' if a=='line_breaking_passes' else 'observed_metric',
            rating=rating,percentile=pct,observation=observation,
            normalization=dict(comparison_position=group,reference_version=reference['version'],reference_fingerprint=EXPECTED_REFERENCE,
                pool_fingerprint=pool['fingerprint']),
            missingness=list(dict.fromkeys(v for v in (m['score_reason'],m['measurement_reason']) if v)),
            exclusions=[dict(match_id=str(e['match_id']),reasons=e['reasons']) for e in exclusions],
            limited_data=p['limited_data'] or any('LIMITED DATA' in w for w in m['warnings']),partial_season=p['partial_season'],
            provenance_ids=['frozen:scores','frozen:measurements','frozen:facts'],warnings=m['warnings'],
            sample_details=dict(raw_counts=m['raw_counts'],action_sample_size=m['attempts'],measured_pass_sample=m['measured_pass_sample']),
            score_status=m['score_status'])
    # These are existing verified role labels, not a new position/score decision.
    from scripts.verify_bundesliga_readiness import position_group
    primary=p['dominant_fine_groups'][0] if len(p['dominant_fine_groups'])==1 else None
    return dict(id=p['id'],player_id=str(p['player_id']),name=p['name'],season_name=p['season_name'],comparison_position=group,
        positions=list(p['position_seconds']),primary_position=primary,
        secondary_positions=[pos for pos in p['position_seconds'] if position_group(pos)!=primary],
        position_seconds=p['position_seconds'],known_supported_minutes=p['known_supported_minutes'],
        clubs=[dict(name=c['team'],competition_name=c['competition_name'],match_ids=[str(mid) for mid in c['match_ids']]) for c in contexts],
        limited_data=p['limited_data'],partial_season=p['partial_season'],attributes=attrs,
        provenance=[dict(id='frozen:'+key,label=label,source='data/derived/private-five-attribute-v2/'+filename,
            fingerprint=manifest['artifacts'][filename]) for key,label,filename in (
            ('scores','Existing frozen experimental scores','PRIVATE-EXPERIMENTAL-scores.jsonl'),
            ('measurements','Existing canonical player-season measurements','player-measurements.jsonl'),
            ('facts','Existing verified actor/fixture numerator and exposure lineage','measurement-facts.jsonl'))])


def build():
    require(sha(PACKAGE/'manifest.json')==EXPECTED_MANIFEST,'frozen package manifest fingerprint changed')
    manifest=json.loads((PACKAGE/'manifest.json').read_text())
    required=['PRIVATE-EXPERIMENTAL-scores.jsonl','player-measurements.jsonl','frozen-reference.json','measurement-facts.jsonl','validation.json','summary.json']
    for filename in required:require(sha(PACKAGE/filename)==manifest['artifacts'][filename],'frozen artifact changed: '+filename)
    validation=json.loads((PACKAGE/'validation.json').read_text())
    require(validation['status']=='PASS' and validation['frozen_reference_unchanged'] and validation['official_numeric_ratings']==0,'completed experimental validation required')
    baseline=json.loads((PACKAGE/'frozen-reference.json').read_text())
    require(baseline['frozen'] is True and baseline['sha256']==EXPECTED_REFERENCE and
        frozen_digest({k:v for k,v in baseline.items() if k!='sha256'})==EXPECTED_REFERENCE,'frozen reference SHA256 mismatch')
    scored=index(json.loads(s) for s in (PACKAGE/'PRIVATE-EXPERIMENTAL-scores.jsonl').open(encoding='utf8'))
    measured=index(json.loads(s) for s in (PACKAGE/'player-measurements.jsonl').open(encoding='utf8'))
    require(scored.keys()==measured.keys() and len(scored)==2514,'canonical dataset scope changed')
    for group,pools in baseline['pools'].items():
        for a,pool in pools.items():
            for pid in pool['member_ids']:
                p=measured[f'{pid}:2015/2016']
                require(not p['limited_data'] and p['comparison_group']==group and
                    p['attributes'][a]['experimental_reference_candidate'],'Bundesliga or invalid player in frozen reference')
    reference=reference_projection(baseline)
    players=[project_player(p,measured[k],reference,manifest) for k,p in scored.items()
        if any(m['experimental_rating'] is not None for m in p['attributes'].values())]
    complete=sum(all(m['rating'] is not None for m in p['attributes'].values()) for p in players)
    require(len(players)==691 and complete==686,'expected complete/partial experimental coverage changed')
    return dict(schema_version=SCHEMA,classification='local_experimental',notice=NOTICE,disclaimer=DISCLAIMER,
        local_only=True,production_ready=False,publication_authorized=False,reference=reference,
        source_package=dict(version=baseline['policy']['id'],manifest_sha256=EXPECTED_MANIFEST,
            scores_sha256=manifest['artifacts']['PRIVATE-EXPERIMENTAL-scores.jsonl'],
            measurements_sha256=manifest['artifacts']['player-measurements.jsonl']),
        counts=dict(examined=2514,available=len(players),complete=complete,partial=len(players)-complete,
            bundesliga_complete=sum(p['limited_data'] and all(m['rating'] is not None for m in p['attributes'].values()) for p in players),
            bundesliga_partial=sum(p['limited_data'] and any(m['rating'] is None for m in p['attributes'].values()) for p in players)),
        players=players)


if __name__=='__main__':
    print(json.dumps(build(),sort_keys=True,separators=(',',':'),allow_nan=False))
