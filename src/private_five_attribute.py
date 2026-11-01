"""Private player-season experiments; no production admission or OVR.

Measurements are supplied from sealed existing ledgers, not reconstructed here.
Joseph's Level A measurement and canonical position policy remain authoritative.
"""
from bisect import bisect_left, bisect_right
import copy
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
import statistics

from src.dri_scoring import fifa_from_zscore
from src.fifth_attribute import FOUR
from src.source_reconstruction import exact, rational

VERSION = 'private-five-attribute-player-season/v2'
NOTICE = 'PRIVATE / EXPERIMENTAL / NOT PRODUCTION / NOT PUBLICATION AUTHORIZED'
ATTRIBUTES = ('tackles','interceptions','recoveries','press_resistance','progressive_passing')
PRESS_COUNTS = ('pressured_pass_attempts','pressured_pass_completed',
                'pressured_dribble_attempts','pressured_dribble_completed')
POLICY = dict(id=VERSION, season='2015/2016', competitions=sorted(FOUR),
    groups=['MID','CB'],minimum_minutes=900,press_reference_minimum_actions=40,
    reference_scope='all observed appearances supported for this metric; all observed exposure supported; no pending fixture 3879594; no Bundesliga contributions',
    normal_recipient_scope='metric-supported minutes >=900 for per90; known season minutes >=900 and positive supported attempts for press; sub-40 press projections retain LIMITED DATA',
    provisional_recipient_scope='Bundesliga contributors: positive metric-supported exposure or positive supported press attempts; no 900/40 recipient cutoff',
    position_policy='reuse Joseph canonical dominant verified fine group, then DM/CM -> MID; CB separate; ties withheld',
    formula='clip(65 + 10 * z, 1, 99)',standard_deviation='sample; ddof=1; no rounding',
    percentile='frozen average ascending rank for an exact reference tie; otherwise 100 * number_strictly_below / n',
    definitions=dict(tackles='Duel/Tackle with Won, Success In Play or Success Out',
        interceptions='Interception with Won, Success In Play or Success Out',
        recoveries='Ball Recovery with recovery_failure != True',
        press_resistance='100 * (completed pressured Pass + Complete pressured Dribble) / all pressured Pass+Dribble attempts; no open-play filter',
        progressive_passing='Joseph Level A completed open-play passes: >=10 yards forward and end distance <=75% of starting goal distance; excludes Unknown/Injury Clearance'))


def require(condition, message):
    if not condition:raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def count(value):
    require(type(value) is int and 0 <= value <= 2**63-1,'exact nonnegative integer count required')
    return value


def aggregate(players, facts):
    """One season identity; each attribute retains its own raw/exposure scope."""
    indexed={}
    for p in players:
        k=(p['player_id'],p['season_name'])
        require(k not in indexed and type(k[0]) is int and k[0]>0 and k[1]=='2015/2016','duplicate/invalid canonical season')
        indexed[k]=p
    grouped=defaultdict(list);seen=set();events={a:set() for a in ATTRIBUTES};press_events=set()
    for r in facts:
        k=(r['player_id'],r['season_name']);mk=(*k,r['match_id'])
        require(k in indexed and mk not in seen,'duplicate or unknown canonical fixture')
        require(r['match_id'] in indexed[k]['observed_match_ids'],'fixture outside canonical scope')
        require(set(r['metrics'])==set(ATTRIBUTES),'all five metric fields required')
        require(r['seconds'] is None or exact(r['seconds'])>=0,'invalid verified season exposure')
        seen.add(mk);grouped[k].append(r)
        for a,m in r['metrics'].items():
            require(type(m['supported']) is bool and isinstance(m['reasons'],list),'explicit metric support required')
            require(m['supported']==(not m['reasons']),'support/reasons contradiction')
            require(m['seconds']==r['seconds'],'metric/appearance exposure mismatch')
            for v in m['counts'].values():count(v)
            ids=m['numerator_ids']
            require(all(isinstance(uid,str) and uid for uid in ids) and len(ids)==len(set(ids)),'invalid/duplicate numerator UUID')
            require(not events[a].intersection(ids),'metric UUID repeated across actors/fixtures')
            events[a].update(ids)
            if a=='press_resistance':
                require(set(m['counts'])==set(PRESS_COUNTS),'exact press component counts required')
                c=m['counts'];attempts=c[PRESS_COUNTS[0]]+c[PRESS_COUNTS[2]]
                successes=c[PRESS_COUNTS[1]]+c[PRESS_COUNTS[3]]
                require(c[PRESS_COUNTS[1]]<=c[PRESS_COUNTS[0]] and c[PRESS_COUNTS[3]]<=c[PRESS_COUNTS[2]],'press successes exceed attempts')
                den=m['denominator_ids']
                require(len(den)==len(set(den))==attempts and len(ids)==successes and set(ids)<=set(den),'press success/attempt UUID alignment failed')
                require(not press_events.intersection(den),'press attempt UUID repeated across actors/fixtures')
                press_events.update(den)
            else:
                require(set(m['counts'])=={'count'} and len(ids)==m['counts']['count'],'numerator count/UUID mismatch')
                if m['supported']:require(m['seconds'] is not None and exact(m['seconds'])>0,'positive verified metric exposure required')
    out=[]
    for k,p in sorted(indexed.items()):
        rows=sorted(grouped[k],key=lambda r:r['match_id'])
        require([r['match_id'] for r in rows]==p['observed_match_ids'],'missing canonical appearance')
        known_seconds=sum((exact(r['seconds']) for r in rows if r['seconds'] is not None),Fraction(0))
        complete_exposure=all(r['seconds'] is not None and exact(r['seconds'])>0 for r in rows)
        require(all(r['competition_name'] in FOUR|{'1. Bundesliga'} for r in rows),'unsupported competition')
        contexts=defaultdict(list)
        for r in rows:contexts[r['team'],r['competition_name']].append(r['match_id'])
        comps=sorted({r['competition_name'] for r in rows});bundes='1. Bundesliga' in comps
        attributes={}
        for a in ATTRIBUTES:
            good=[r for r in rows if r['metrics'][a]['supported']]
            cs={n:sum(r['metrics'][a]['counts'][n] for r in good) for n in (PRESS_COUNTS if a=='press_resistance' else ('count',))}
            seconds=sum((exact(r['metrics'][a]['seconds']) for r in good if r['metrics'][a]['seconds'] is not None),Fraction(0))
            attempts=cs[PRESS_COUNTS[0]]+cs[PRESS_COUNTS[2]] if a=='press_resistance' else None
            numerator=cs[PRESS_COUNTS[1]]+cs[PRESS_COUNTS[3]] if a=='press_resistance' else cs['count']
            value=Fraction(100*numerator,attempts) if a=='press_resistance' and attempts else Fraction(numerator*5400,1)/seconds if a!='press_resistance' and seconds>0 else None
            full=len(good)==len(rows)
            minutes=seconds/60
            candidate=bool(value is not None and full and complete_exposure and known_seconds>=54000 and
                p['comparison_group'] in ('MID','CB') and not bundes and not any(r['match_id']==3879594 for r in rows) and
                (a=='press_resistance' or minutes>=900) and (a!='press_resistance' or attempts>=40))
            warnings=[]
            if not full:warnings.append('EXCLUDED_METRIC_APPEARANCES')
            if not complete_exposure:warnings.append('EXCLUDED_OR_UNKNOWN_SEASON_EXPOSURE')
            if bundes:warnings.extend(['LIMITED DATA','PARTIAL SEASON'])
            if a=='press_resistance' and attempts and attempts<40:warnings.append('BELOW_40_PRESS_ACTIONS / LIMITED DATA')
            attributes[a]=dict(raw_counts=cs if good else None,numerator=numerator if good else None,
                attempts=attempts if good else None,supported_minutes=rational(minutes),
                exact_value=rational(value) if value is not None else None,value=float(value) if value is not None else None,
                unit='percent' if a=='press_resistance' else 'per90',
                numerator_match_ids=[r['match_id'] for r in good],denominator_match_ids=[r['match_id'] for r in good],
                excluded_appearances=[dict(match_id=r['match_id'],reasons=r['metrics'][a]['reasons']) for r in rows if not r['metrics'][a]['supported']],
                all_observed_metric_scope_supported=full,experimental_reference_candidate=candidate,
                measured_pass_sample=p['measured_passes'] if a=='progressive_passing' else None,
                warnings=warnings,measurement_reason=None if value is not None else 'NO_SUPPORTED_ATTEMPTS' if a=='press_resistance' and good else 'NO_SUPPORTED_MEASUREMENT')
        out.append(dict(id=f'{k[0]}:{k[1]}',player_id=k[0],season_name=k[1],name=p['name'],
            comparison_group=p['comparison_group'],dominant_fine_groups=p['dominant_fine_groups'],
            position_seconds=copy.deepcopy(p['position_seconds']),observed_match_ids=p['observed_match_ids'],
            contexts=[dict(team=t,competition_name=c,match_ids=ms) for (t,c),ms in sorted(contexts.items())],
            competitions=comps,limited_data=bundes,partial_season=True,
            known_supported_minutes=rational(known_seconds/60),all_observed_exposure_supported=complete_exposure,
            attributes=attributes,reference_member=False,publication_authorized=False,production_certified=False))
    return out


def freeze_reference(players, *, input_binding):
    require(isinstance(input_binding,str) and len(input_binding)==64,'bound input hash required')
    require(len({p['id'] for p in players})==len(players),'duplicate baseline identities')
    pools={}
    for group in POLICY['groups']:
        pools[group]={}
        for a in ATTRIBUTES:
            members=[]
            for p in sorted(players,key=lambda p:p['player_id']):
                m=p['attributes'][a]
                if p['comparison_group']!=group or not m['experimental_reference_candidate']:continue
                require(not p['limited_data'] and set(p['competitions'])<=FOUR and p['all_observed_exposure_supported'] and
                    exact(p['known_supported_minutes'])>=900 and m['all_observed_metric_scope_supported'] and
                    (a!='press_resistance' or m['attempts']>=40),'invalid reference admission')
                require(m['exact_value'] is not None and math.isfinite(m['value']) and float(exact(m['exact_value']))==m['value'],'invalid reference measurement')
                members.append(dict(player_id=p['player_id'],season_name=p['season_name'],
                    exact_value=m['exact_value'],value=m['value'],numerator=m['numerator'],attempts=m['attempts'],
                    supported_minutes=m['supported_minutes'],match_ids=m['numerator_match_ids'],competitions=p['competitions']))
            xs=[m['value'] for m in members]
            pools[group][a]=dict(n=len(xs),mean=statistics.mean(xs) if xs else None,
                sample_sd=statistics.stdev(xs) if len(xs)>1 else None,
                member_ids=[m['player_id'] for m in members],members=members)
    baseline=dict(schema_version=VERSION+'/frozen-reference',notice=NOTICE,frozen=True,
        policy=copy.deepcopy(POLICY),input_binding=input_binding,pools=pools,publication_authorized=False)
    baseline['sha256']=digest(baseline)
    return baseline


def validate_reference(baseline):
    require(baseline.get('schema_version')==VERSION+'/frozen-reference' and baseline.get('policy')==POLICY and
        baseline.get('frozen') is True and baseline.get('publication_authorized') is False,'private frozen policy required')
    require(baseline.get('sha256')==digest({k:v for k,v in baseline.items() if k!='sha256'}),'frozen reference fingerprint changed')
    require(set(baseline['pools'])==set(POLICY['groups']),'separate position pools required')
    for group,pools in baseline['pools'].items():
        require(set(pools)==set(ATTRIBUTES),'five frozen reference populations required')
        for a,pool in pools.items():
            ms=pool['members'];xs=[m['value'] for m in ms]
            require(pool['n']==len(ms) and pool['member_ids']==sorted(set(m['player_id'] for m in ms)),'duplicate/inconsistent reference membership')
            require(all(m['season_name']=='2015/2016' and set(m['competitions'])<=FOUR and m['competitions'] and 3879594 not in m['match_ids'] and
                exact(m['supported_minutes'])>=900 and float(exact(m['exact_value']))==m['value'] and math.isfinite(m['value']) and
                (a!='press_resistance' or m['attempts']>=40) for m in ms),'invalid frozen member evidence')
            require(pool['mean']==(statistics.mean(xs) if xs else None) and
                pool['sample_sd']==(statistics.stdev(xs) if len(xs)>1 else None),'frozen sample statistics disagree')
    return baseline


def score_players(players, baseline):
    """Apply a frozen reference; never fit/update it using recipients."""
    validate_reference(baseline)
    require(len({p['id'] for p in players})==len(players),'duplicate scoring identity')
    orders={(g,a):sorted(exact(m['exact_value']) for m in baseline['pools'][g][a]['members']) for g in POLICY['groups'] for a in ATTRIBUTES}
    out=[]
    for p in sorted(players,key=lambda p:p['player_id']):
        row=copy.deepcopy(p);group=p['comparison_group']
        for a,m in row['attributes'].items():
            reason=None;score=z=pct=None
            if m['value'] is None:reason=m['measurement_reason']
            elif group not in POLICY['groups']:reason='UNSUPPORTED_POSITION_GROUP'
            elif not p['limited_data'] and (exact(p['known_supported_minutes'])<900 if a=='press_resistance' else exact(m['supported_minutes'])<900):reason='BELOW_900_VERIFIED_MINUTES'
            else:
                pool=baseline['pools'][group][a]
                if pool['n']<2:reason='INSUFFICIENT_REFERENCE_MEMBERS'
                elif pool['sample_sd'] is None or pool['sample_sd']<=0:reason='ZERO_REFERENCE_VARIANCE'
                else:
                    require(m['exact_value'] is not None and float(exact(m['exact_value']))==m['value'] and math.isfinite(m['value']),'invalid scoring input')
                    denominator=m['attempts'] if a=='press_resistance' else exact(m['supported_minutes'])
                    require(denominator is not None and denominator>0,'missing or zero scoring denominator')
                    expected=Fraction(100*count(m['numerator']),count(m['attempts'])) if a=='press_resistance' else Fraction(count(m['numerator'])*90,1)/denominator
                    require(exact(m['exact_value'])==expected,'raw numerator/denominator contradicts scoring value')
                    z=(m['value']-pool['mean'])/pool['sample_sd'];score=fifa_from_zscore(z)
                    xs=orders[group,a];x=exact(m['exact_value']);lo=bisect_left(xs,x);hi=bisect_right(xs,x)
                    pct=100*((lo+1+hi)/2 if hi>lo else lo)/len(xs)
            m.update(experimental_rating=score,zscore=z,percentile=pct,score_reason=reason,
                experimental_reference_member=p['player_id'] in baseline['pools'][group][a]['member_ids'] if group in POLICY['groups'] else False,
                score_status='N/A' if score is None else 'PROVISIONAL_LIMITED_DATA' if p['limited_data'] or a=='press_resistance' and m['attempts']<40 else 'PRIVATE_EXPERIMENTAL')
        row.update(schema_version=VERSION+'/player',notice=NOTICE,baseline_sha256=baseline['sha256'])
        out.append(row)
    return out
