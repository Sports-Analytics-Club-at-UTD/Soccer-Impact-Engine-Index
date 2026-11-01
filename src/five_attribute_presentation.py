"""Approval-ready presentation boundary; currently SYNTHETIC ONLY.

This is not a production exporter or an extension of numeric real admission.
No file reader, scoring pipeline, approval receipt issuer or baseline fitter.
"""
import copy
import hashlib
import json
import math

from src.rating_assembly import ATTRIBUTES

SCHEMA='soccer-five-attribute-presentation/v1'
NOTICE='SYNTHETIC TEST FIXTURE / NOT REAL PLAYER RATINGS / NOT PUBLICATION AUTHORIZED'
LABELS=dict(tackles='Tackling',interceptions='Interceptions',recoveries='Ball Recovery',
    press_resistance='Press Resistance',line_breaking_passes='Line Breaking — Progressive Passing Proxy')
UNITS={a:'percent' if a=='press_resistance' else 'per90' for a in ATTRIBUTES}


def check(condition,message):
    if not condition:raise ValueError('Invalid five-attribute presentation: '+message)


def keys(value,names):
    check(isinstance(value,dict) and set(value)==set(names),'unexpected or missing fields')


def number(v,lo=0,hi=float('inf')):
    return type(v) in (int,float) and math.isfinite(v) and lo<=v<=hi


def text(v):return isinstance(v,str) and bool(v.strip())
def synthetic(v):return isinstance(v,str) and v.startswith('synthetic:') and len(v)>10
def fingerprint(v):return isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)


def digest(value):
    # Shared JS/Python canonical encoding for synthetic reference fingerprints.
    def normalize(v):
        if isinstance(v,dict):return {k:normalize(x) for k,x in v.items()}
        if isinstance(v,list):return [normalize(x) for x in v]
        if type(v) is float and math.isfinite(v) and v.is_integer():return int(v)
        return v
    return hashlib.sha256(json.dumps(normalize(value),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def unique_strings(values,predicate=text):
    check(isinstance(values,list) and all(predicate(v) for v in values) and len(set(values))==len(values),'unique strings required')


def minutes(value):
    keys(value,['numerator','denominator'])
    check(type(value['numerator']) is int and value['numerator']>=0 and type(value['denominator']) is int and value['denominator']>0,'exact supported minutes required')
    return value['numerator']/value['denominator']


def validate_reference(ref):
    keys(ref,['version','synthetic','positions','fingerprint'])
    check(synthetic(ref['version']) and ref['synthetic'] is True,'synthetic frozen reference required')
    keys(ref['positions'],['MID','CB'])
    for group,pools in ref['positions'].items():
        keys(pools,ATTRIBUTES)
        for a,p in pools.items():
            keys(p,['population_version','comparison_position','metric_id','n','mean','sample_sd','member_ids','fingerprint'])
            check(synthetic(p['population_version']) and p['comparison_position']==group and p['metric_id']==a,'position-specific reference mismatch')
            unique_strings(p['member_ids'],synthetic)
            check(type(p['n']) is int and p['n']==len(p['member_ids']) and p['n']>=2 and number(p['mean']) and number(p['sample_sd']) and p['sample_sd']>0,'frozen mean/sample SD required')
            check(fingerprint(p['fingerprint']) and p['fingerprint']==digest({k:v for k,v in p.items() if k!='fingerprint'}),'pool fingerprint mismatch')
    check(fingerprint(ref['fingerprint']) and ref['fingerprint']==digest({k:v for k,v in ref.items() if k!='fingerprint'}),'reference fingerprint mismatch')


def validate_card(p,ref):
    keys(p,['id','player_id','name','season_name','comparison_position','positions','clubs','limited_data','partial_season','attributes','provenance'])
    check(synthetic(p['player_id']) and p['id']==p['player_id']+':'+p['season_name'] and p['season_name']=='2015/2016' and p['name'].startswith('SYNTHETIC '),'synthetic canonical player-season required')
    check(p['comparison_position'] in ('MID','CB',None),'comparison position must be MID/CB or missing')
    unique_strings(p['positions'])
    check(type(p['limited_data']) is bool and type(p['partial_season']) is bool,'explicit coverage warnings required')
    check(isinstance(p['clubs'],list) and bool(p['clubs']),'club contexts required')
    fixtures=set();contexts=set();bundes=False
    for c in p['clubs']:
        keys(c,['name','competition_name','match_ids'])
        check(c['name'].startswith('SYNTHETIC ') and c['competition_name'] in ('La Liga','Premier League','Serie A','Ligue 1','1. Bundesliga'),'synthetic club/league required')
        unique_strings(c['match_ids'],synthetic)
        check(c['match_ids'] and not fixtures.intersection(c['match_ids']) and (c['name'],c['competition_name']) not in contexts,'overlapping or duplicate transfer contexts')
        fixtures.update(c['match_ids']);contexts.add((c['name'],c['competition_name']));bundes |= c['competition_name']=='1. Bundesliga'
    check(not bundes or p['limited_data'] and p['partial_season'],'Bundesliga requires LIMITED DATA / PARTIAL SEASON')
    check(isinstance(p['provenance'],list) and bool(p['provenance']),'provenance required')
    sources=set()
    for s in p['provenance']:
        keys(s,['id','label','source','fingerprint'])
        check(synthetic(s['id']) and text(s['label']) and synthetic(s['source']) and fingerprint(s['fingerprint']) and s['id'] not in sources,'synthetic provenance required')
        sources.add(s['id'])
    keys(p['attributes'],ATTRIBUTES)
    for a,m in p['attributes'].items():
        keys(m,['label','measurement_kind','rating','percentile','observation','normalization','missingness','exclusions','limited_data','partial_season','provenance_ids'])
        check(m['label']==LABELS[a] and m['measurement_kind']==('progressive_passing_proxy' if a=='line_breaking_passes' else 'observed_metric'),'explicit metric/proxy label required')
        check(m['rating'] is None or number(m['rating'],1,99),'rating must be null or 1..99')
        check(m['percentile'] is None or number(m['percentile'],0,100),'percentile must be null or 0..100')
        unique_strings(m['missingness']);unique_strings(m['provenance_ids'],synthetic)
        check(m['provenance_ids'] and set(m['provenance_ids'])<=sources,'bound provenance required')
        check(type(m['limited_data']) is bool and type(m['partial_season']) is bool and
            (not p['limited_data'] or m['limited_data']) and (not p['partial_season'] or m['partial_season']),'attribute coverage warning mismatch')
        check(isinstance(m['exclusions'],list),'explicit exclusions required')
        excluded=set()
        for e in m['exclusions']:
            keys(e,['match_id','reasons']);unique_strings(e['reasons'])
            check(e['match_id'] in fixtures and e['match_id'] not in excluded and e['reasons'],'excluded appearance evidence required')
            excluded.add(e['match_id'])
        n=m['normalization'];keys(n,['comparison_position','reference_version','reference_fingerprint','pool_fingerprint'])
        group=p['comparison_position']
        check(n['comparison_position']==group and n['reference_version']==ref['version'] and n['reference_fingerprint']==ref['fingerprint'],'normalization metadata mismatch')
        check(n['pool_fingerprint']==(ref['positions'][group][a]['fingerprint'] if group else None),'position pool fingerprint mismatch')
        o=m['observation']
        if o is None:
            check(m['rating'] is None and m['percentile'] is None and m['missingness'],'absent measurement must stay N/A');continue
        keys(o,['value','unit','numerator','denominator','denominator_unit','supported_minutes','action_sample_size','match_ids'])
        check(number(o['value']) and type(o['numerator']) is int and o['numerator']>=0 and number(o['denominator']) and o['denominator']>0,'supported numerator/denominator required')
        check(o['unit']==UNITS[a] and o['denominator_unit']==('actions' if a=='press_resistance' else 'minutes'),'metric units mismatch')
        unique_strings(o['match_ids'],synthetic)
        check(o['match_ids'] and set(o['match_ids'])<=fixtures and (a=='press_resistance' or not excluded.intersection(o['match_ids'])),'unsupported measurement fixture scope')
        if o['supported_minutes'] is not None:minutes(o['supported_minutes'])
        if a=='press_resistance':
            check(type(o['action_sample_size']) is int and o['action_sample_size']==o['denominator'] and o['numerator']<=o['denominator'],'press sample mismatch')
            check(o['denominator']>=40 or m['limited_data'],'sub-40 press requires LIMITED DATA')
        else:
            check(o['action_sample_size'] is None and o['supported_minutes'] is not None and math.isclose(minutes(o['supported_minutes']),o['denominator'],rel_tol=1e-12),'aligned supported minutes required')
        check(math.isclose(o['value'],o['numerator']/o['denominator']*(100 if a=='press_resistance' else 90),rel_tol=1e-10,abs_tol=1e-10),'measurement arithmetic mismatch')
        if m['rating'] is not None:
            check(group is not None and m['percentile'] is not None,'numeric score needs comparison position and percentile')
            pool=ref['positions'][group][a]
            expected=max(1,min(99,65+10*(o['value']-pool['mean'])/pool['sample_sd']))
            check(math.isclose(m['rating'],expected,rel_tol=1e-10,abs_tol=1e-10),'synthetic rating/reference mismatch')
        else:check(m['percentile'] is None and m['missingness'],'withheld score needs an explicit reason')


def validate_delivery(payload):
    keys(payload,['schema_version','classification','notice','publication_authorized','numeric_real_delivery_enabled','reference','players'])
    check(payload['schema_version']==SCHEMA and payload['classification']=='synthetic' and payload['notice']==NOTICE and
        payload['publication_authorized'] is False and payload['numeric_real_delivery_enabled'] is False,'synthetic-only boundary; real numeric delivery disabled')
    validate_reference(payload['reference'])
    check(isinstance(payload['players'],list),'player array required')
    seen=set()
    for p in payload['players']:
        validate_card(p,payload['reference']);check(p['id'] not in seen,'duplicate canonical player-season');seen.add(p['id'])
    return copy.deepcopy(payload)
