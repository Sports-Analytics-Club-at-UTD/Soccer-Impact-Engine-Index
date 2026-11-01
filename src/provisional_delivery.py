"""Observation-only provisional cards. No scoring, pool building or publication.

This is a separate versioned extension of the card input, not a relaxation of
soccer-rating-delivery/v1. Frozen baseline admission returns a plan, never scores.
"""
import copy
from fractions import Fraction
import hashlib
import json
import math

SCHEMA = 'soccer-provisional-observations/v1'
DEFINITIONS = 'statsbomb-successful-defense-press-pass-dribble/v1'
LEAGUES = ['La Liga', 'Premier League', 'Serie A', 'Ligue 1']
ATTRIBUTES = ['tackles', 'interceptions', 'recoveries', 'press_resistance', 'line_breaking_passes']


def require(condition, message):
    if not condition: raise ValueError(message)


def keys(value, fields):
    require(isinstance(value, dict) and set(value) == set(fields), 'unexpected or missing fields')


def number(value, minimum=0):
    return type(value) in (int, float) and math.isfinite(value) and value >= minimum


def identifier(value):
    return isinstance(value, str) and value.isascii() and value.isdecimal() and str(int(value)) == value and 0 < int(value) <= 2**63-1


def ids(values):
    require(isinstance(values, list) and all(identifier(v) for v in values) and
            values == sorted(set(values), key=int), 'unique sorted fixture IDs required')


def duration(value):
    keys(value, ['numerator', 'denominator'])
    require(type(value['numerator']) is int and value['numerator'] >= 0 and
            type(value['denominator']) is int and value['denominator'] > 0, 'exact nonnegative minutes required')
    return Fraction(value['numerator'], value['denominator'])


def rational(value):
    return dict(numerator=value.numerator, denominator=value.denominator)


def role(groups):
    values = {k: duration(v) for k,v in groups.items()}
    high = max(values.values(), default=0)
    top = [k for k,v in values.items() if v == high and high > 0]
    return ('MID' if top[0] in ('DM','CM') else 'CB' if top[0] == 'CB' else None) if len(top) == 1 else None


def validate_card(p, source_ids):
    keys(p, ['id','player_id','name','season_name','contexts','comparison_group','position_minutes',
        'observed_positions','bundesliga_candidate','observed_exposure_complete','supported_minutes',
        'excluded_match_ids','reference_member','limited_data','partial_season','provenance_ids','attributes','bundesliga_sample'])
    require(identifier(p['player_id']) and p['id'] == p['player_id']+':2015/2016' and p['season_name']=='2015/2016', 'canonical player-season identity required')
    require(isinstance(p['name'],str) and p['name'].strip(), 'player name required')
    require(p['limited_data'] is True and p['partial_season'] is True and p['reference_member'] is False, 'separate limited-data reference exclusion required')
    require(type(p['bundesliga_candidate']) is bool and type(p['observed_exposure_complete']) is bool, 'explicit exposure flags required')
    require(isinstance(p['position_minutes'],dict) and set(p['position_minutes']) <= {'GK','CB','DM','CM','FB','WM','AM','ATT','UNKNOWN'}, 'position groups required')
    require(role(p['position_minutes']) == p['comparison_group'], 'dominant supported season group mismatch')
    require(duration(p['supported_minutes']) == sum((duration(v) for v in p['position_minutes'].values()),Fraction(0)), 'position/exposure sum mismatch')
    require(isinstance(p['observed_positions'],list) and all(isinstance(v,str) and v.strip() for v in p['observed_positions']), 'observed positions required')
    ids(p['excluded_match_ids'])
    require(p['observed_exposure_complete'] == (not p['excluded_match_ids']), 'excluded exposure flag mismatch')
    require(isinstance(p['provenance_ids'],list) and bool(p['provenance_ids']) and len(set(p['provenance_ids']))==len(p['provenance_ids']) and set(p['provenance_ids']) <= source_ids, 'bound provenance required')
    require(isinstance(p['contexts'],list) and bool(p['contexts']), 'contexts required')
    seen=set(); context_keys=set(); bundes=False
    for c in p['contexts']:
        keys(c,['team','competition_name','match_ids'])
        require(isinstance(c['team'],str) and c['team'].strip() and c['competition_name'] in LEAGUES+['1. Bundesliga'], 'invalid contribution context')
        ids(c['match_ids']); require(bool(c['match_ids']) and not seen.intersection(c['match_ids']), 'overlapping transfer fixture scope')
        ck=(c['team'],c['competition_name']);require(ck not in context_keys,'duplicate club context')
        context_keys.add(ck);seen.update(c['match_ids']);bundes |= c['competition_name']=='1. Bundesliga'
    require(bundes and set(p['excluded_match_ids']) <= seen, 'Bundesliga scope / excluded fixtures mismatch')
    b=p['bundesliga_sample']
    keys(b,['comparison_group','position_minutes','supported_minutes','match_ids','excluded_match_ids','press_attempts','press_successes'])
    require(isinstance(b['position_minutes'],dict) and set(b['position_minutes']) <= {'GK','CB','DM','CM','FB','WM','AM','ATT','UNKNOWN'}, 'Bundesliga position groups required')
    require(role(b['position_minutes'])==b['comparison_group'] and p['bundesliga_candidate']==(b['comparison_group'] in ('MID','CB')), 'Bundesliga candidate group mismatch')
    require(duration(b['supported_minutes'])==sum((duration(v) for v in b['position_minutes'].values()),Fraction(0)) and duration(b['supported_minutes'])<=duration(p['supported_minutes']), 'Bundesliga exposure mismatch')
    ids(b['match_ids']);ids(b['excluded_match_ids'])
    bundes_ids={m for c in p['contexts'] if c['competition_name']=='1. Bundesliga' for m in c['match_ids']}
    require(set(b['match_ids'])==bundes_ids and set(b['excluded_match_ids'])==set(p['excluded_match_ids']).intersection(bundes_ids), 'Bundesliga fixture sample mismatch')
    require((b['press_attempts'] is None and b['press_successes'] is None) or
        (type(b['press_attempts']) is int and type(b['press_successes']) is int and 0<=b['press_successes']<=b['press_attempts']), 'Bundesliga action counts required')
    keys(p['attributes'],ATTRIBUTES)
    for name,a in p['attributes'].items():
        keys(a,['rating','percentile','observation','reason'])
        require(a['rating'] is None and a['percentile'] is None, 'numeric ratings and percentiles are forbidden')
        require(isinstance(a['reason'],str), 'availability reason required')
        o=a['observation']
        if o is None:
            require(bool(a['reason']), 'N/A reason required');continue
        require(name!='line_breaking_passes', 'official line breaking remains N/A')
        if name=='press_resistance':
            keys(o,['value','unit','attempts','successes','pass_attempts','pass_successes','dribble_attempts','dribble_successes','match_ids','at_least_40'])
            for k in ['attempts','successes','pass_attempts','pass_successes','dribble_attempts','dribble_successes']:
                require(type(o[k]) is int and o[k]>=0, 'integer action counts required')
            require(o['attempts']>0 and o['successes']<=o['attempts'] and o['pass_successes']<=o['pass_attempts'] and o['dribble_successes']<=o['dribble_attempts'] and
                o['attempts']==o['pass_attempts']+o['dribble_attempts'] and o['successes']==o['pass_successes']+o['dribble_successes'], 'press counts disagree')
            expected=100*o['successes']/o['attempts']
            require(o['unit']=='percent' and type(o['at_least_40']) is bool and o['at_least_40']==(o['attempts']>=40), 'press sample rule mismatch')
            require(set(o['match_ids'])==seen,'press numerator/denominator scope mismatch')
        else:
            keys(o,['value','unit','count','minutes','match_ids'])
            require(type(o['count']) is int and o['count']>=0 and duration(o['minutes'])>0, 'supported defensive exposure required')
            require(not set(o['match_ids']).intersection(p['excluded_match_ids']) and bool(o['match_ids']), 'unsupported defensive fixture admitted')
            require(duration(o['minutes'])<=duration(p['supported_minutes']), 'defensive denominator exceeds supported exposure')
            expected=float(o['count']*90/duration(o['minutes']))
            require(o['unit']=='per90','defensive unit mismatch')
        ids(o['match_ids']);require(set(o['match_ids'])<=seen, 'component fixture scope mismatch')
        require(number(o['value']) and math.isclose(o['value'],expected,rel_tol=1e-12,abs_tol=1e-12), 'observation arithmetic mismatch')
    combined=p['attributes']['press_resistance']['observation']
    if b['press_attempts'] is not None and b['press_attempts']>0:
        require(combined is not None and b['press_attempts']<=combined['attempts'] and b['press_successes']<=combined['successes'] and
            b['press_attempts']-b['press_successes']<=combined['attempts']-combined['successes'], 'Bundesliga actions exceed combined evidence')
    if all(c['competition_name']=='1. Bundesliga' for c in p['contexts']):
        require((combined is None and b['press_attempts'] in (None,0)) or combined is not None and
            (b['press_attempts'],b['press_successes'])==(combined['attempts'],combined['successes']), 'Bundesliga-only press scope mismatch')
    return copy.deepcopy(p)


def validate_delivery(data):
    keys(data,['schema_version','definitions_id','numeric_ratings_enabled','publication_authorized','baseline','sources','players'])
    require(data['schema_version']==SCHEMA and data['definitions_id']==DEFINITIONS and data['numeric_ratings_enabled'] is False and
        data['publication_authorized'] is False and data['baseline'] is None, 'observation-only envelope required')
    require(isinstance(data['sources'],list) and bool(data['sources']), 'evidence sources required')
    sources=set()
    for s in data['sources']:
        keys(s,['id','path','sha256','label'])
        require(all(isinstance(s[k],str) and s[k].strip() for k in s), 'source descriptor required')
        require(s['id'] not in sources and len(s['sha256'])==64 and all(c in '0123456789abcdef' for c in s['sha256']), 'source fingerprint required')
        sources.add(s['id'])
    require(isinstance(data['players'],list), 'player array required')
    seen=set()
    for p in data['players']:
        validate_card(p,sources); require(p['id'] not in seen,'duplicate canonical player-season card');seen.add(p['id'])
    return copy.deepcopy(data)


def card_from_readiness(row, *, candidate, provenance_ids, bundesliga_row=None):
    """Project already verified evidence; no acquisition, reconstruction or scores."""
    require(row['ratings'] is None and row['reference_member'] is False and row['source_identity_supported'], 'untrusted or rated readiness input')
    raw_contexts=row.get('original_contexts') or [dict(c,competition_name='1. Bundesliga') for c in row['clubs']]
    if 'original_contexts' in row:
        require(row['matching_metric_definitions'] and row['nonoverlapping_fixture_scopes'] and row['technical_combination']=='SUPPORTED_SUBSETS_ONLY', 'incompatible transfer contributions')
    contexts=[dict(team=c['team'],competition_name=c['competition_name'],match_ids=[str(m) for m in c['match_ids']]) for c in raw_contexts]
    attributes={n:dict(rating=None,percentile=None,observation=None,reason='No supported observation') for n in ATTRIBUTES}
    for n in ATTRIBUTES[:3]:
        c=row['defensive'][n]
        if c['status']=='SUPPORTED_OBSERVED_SUBSET':
            attributes[n].update(observation=dict(value=c['per90'],unit='per90',count=c['supported_count'],
                minutes=c['supported_minutes'],match_ids=[str(m) for m in c['supported_match_ids']]),reason='Verified subset; unresolved exposure excluded' if row['unresolved_match_ids'] else 'Observed sample only')
    pr=row['press']
    if pr['status']=='SUPPORTED_ACTION_RATIO' and pr['attempts']>0:
        attributes['press_resistance'].update(observation=dict(value=pr['measured_percent'],unit='percent',attempts=pr['attempts'],successes=pr['successes'],
            pass_attempts=pr['pressured_pass_attempts'],pass_successes=pr['pressured_pass_completed'],
            dribble_attempts=pr['pressured_dribble_attempts'],dribble_successes=pr['pressured_dribble_completed'],
            match_ids=sorted({m for c in contexts for m in c['match_ids']},key=int),at_least_40=pr['observed_40_actions']),reason='Below 40 actions; retain measured ratio' if pr['attempts']<40 else 'Observed action ratio')
    else:attributes['press_resistance']['reason']='No observed pressured actions' if pr['attempts']==0 else 'Press observations unavailable'
    attributes['line_breaking_passes']['reason']='Official line breaking is unavailable'
    minutes=sum((duration(v) for v in row['group_minutes'].values()),Fraction(0))
    original=bundesliga_row or row
    bundes_minutes=sum((duration(v) for v in original['group_minutes'].values()),Fraction(0))
    sample=dict(comparison_group=role(original['group_minutes']),position_minutes=copy.deepcopy(original['group_minutes']),
        supported_minutes=rational(bundes_minutes),match_ids=sorted({str(m) for c in original['clubs'] for m in c['match_ids']},key=int),
        excluded_match_ids=[str(m) for m in original['unresolved_match_ids']],
        press_attempts=original['press']['attempts'],press_successes=original['press']['successes'])
    return dict(id=f"{row['player_id']}:2015/2016",player_id=str(row['player_id']),name=row['names'][0],season_name='2015/2016',contexts=contexts,
        comparison_group=role(row['group_minutes']),position_minutes=copy.deepcopy(row['group_minutes']),observed_positions=row['observed_positions'],
        bundesliga_candidate=candidate,observed_exposure_complete=row['all_observed_appearance_minutes_supported'],supported_minutes=rational(minutes),
        excluded_match_ids=[str(m) for m in row['unresolved_match_ids']],reference_member=False,limited_data=True,partial_season=True,
        provenance_ids=provenance_ids,attributes=attributes,bundesliga_sample=sample)


def provisional_admission(card, baseline):
    """Read-only admission plan compatible with a frozen external reference.

    Does not compute z-scores, percentiles or FIFA values, even for synthetic
    callers. Publication and numeric-rating gates stay closed.
    """
    validate_card(card,set(card['provenance_ids']))
    keys(baseline,['id','sha256','frozen','competitions','definitions_id','members','statistics'])
    require(baseline['frozen'] is True and baseline['competitions']==LEAGUES and baseline['definitions_id']==DEFINITIONS,'fixed four-league baseline required')
    body={k:v for k,v in baseline.items() if k!='sha256'}
    sha=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    require(sha==baseline['sha256'],'frozen baseline fingerprint mismatch')
    seen=set();counts={'MID':0,'CB':0}
    for m in baseline['members']:
        keys(m,['player_id','competition_name','role_group'])
        require(identifier(m['player_id']) and m['competition_name'] in LEAGUES and m['role_group'] in counts and m['player_id'] not in seen,'invalid or duplicate four-league reference member')
        seen.add(m['player_id']);counts[m['role_group']]+=1
    keys(baseline['statistics'],['MID','CB'])
    for group,stats in baseline['statistics'].items():
        keys(stats,ATTRIBUTES[:4])
        for s in stats.values():
            keys(s,['mean','sample_sd','n','member_ids'])
            members={m['player_id'] for m in baseline['members'] if m['role_group']==group}
            ids(s['member_ids'])
            require(set(s['member_ids'])<=members and type(s['n']) is int and s['n']==len(s['member_ids']) and s['n']>=2 and number(s['mean']) and number(s['sample_sd']) and s['sample_sd']>0,'valid frozen reference statistics required')
    group=card['comparison_group']
    return dict(player_season_id=card['id'],baseline_id=baseline['id'],baseline_sha256=sha,role_group=group,
        admissible_attributes=[n for n in ATTRIBUTES[:4] if group in ('MID','CB') and card['attributes'][n]['observation'] is not None],
        reference_member=False,numeric_rating_authorized=False,publication_authorized=False)
