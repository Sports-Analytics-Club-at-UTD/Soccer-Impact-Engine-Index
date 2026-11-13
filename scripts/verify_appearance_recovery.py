"""Independent source-edge proof for recovered intervals and conservation.

Does not import the recovery implementation. Physical entry/exit edges are paired
first, then projected onto independently checked half boundaries. Role stints do
not supply time. Every included and omitted selected action is accounted for.
"""
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def point(e):
    h,m,s=e['timestamp'].split(':')
    return e['period'],Fraction(int(h)*3600+int(m)*60)+Fraction(s)


def oracle(events,tid,pid):
    ordered=sorted(events,key=lambda e:e['index']);teams={e['team']['id'] for e in events}
    name=lambda e:e['type']['name']
    bounds={}
    for period in (1,2):
        for label,field in [('Half Start','half_start'),('Half End','half_end')]:
            es=[e for e in ordered if e['period']==period and name(e)==label]
            valid=len(es)==2 and {e['team']['id'] for e in es}==teams and len({point(e) for e in es})==1 and all(not e.get(field,{}) for e in es)
            bounds[period,field]=point(es[0])[1] if valid else None
    starters=[e for e in ordered if e['team']['id']==tid and name(e)=='Starting XI']
    assert len(starters)==1
    xi=starters[0];entered=any(p['player']['id']==pid for p in xi['tactics']['lineup'])
    open_edge=xi if entered else None;temporary=False;permanent=False;ever=entered
    pairs=[];conflict=False;halftime=[]
    for e in ordered:
        if e['team']['id']!=tid:continue
        actor=e.get('player',{}).get('id')==pid
        recipient=e.get('pass',{}).get('recipient',{}).get('id')==pid
        label=name(e)
        incoming=label=='Substitution' and e['substitution']['replacement']['id']==pid
        card=e.get('foul_committed',{}).get('card',{}).get('name') or e.get('bad_behaviour',{}).get('card',{}).get('name')
        if incoming:
            assert not ever and open_edge is None and not permanent
            open_edge=e;ever=True
        elif actor and label=='Player On':
            if not temporary or permanent:
                conflict=True;break
            # Paired halftime boundaries independently prove a return during
            # the break. Anchor the next interval at the genuine second start.
            if e['period']==1 and bounds[1,'half_end'] is not None and point(e)[1]>bounds[1,'half_end']:
                first=[x for x in ordered if x['period']==1 and name(x)=='Half End']
                second=[x for x in ordered if x['period']==2 and name(x)=='Half Start']
                assert bounds[2,'half_start']==0 and max(x['index'] for x in first)<e['index']<min(x['index'] for x in second)
                halftime.append(e['id']);open_edge=second[0]
            else:open_edge=e
            temporary=False
        elif actor and (label in ('Player Off','Substitution') or card in ('Red Card','Second Yellow')):
            assert open_edge is not None
            pairs.append((open_edge,e));open_edge=None
            temporary=label=='Player Off' and not e.get('player_off',{}).get('permanent')
            permanent=not temporary
        elif (actor or recipient) and label!='Bad Behaviour' and open_edge is None:
            conflict=True;break
    if not conflict and open_edge is not None:pairs.append((open_edge,None))
    segments=[];incomplete=conflict or temporary
    for entry,exit_event in pairs:
        start_period,start=point(entry);end_period,end=point(exit_event) if exit_event else (2,None)
        for period in range(start_period,end_period+1):
            lo=start if period==start_period else bounds[period,'half_start']
            hi=end if period==end_period and exit_event else bounds[period,'half_end']
            # A Starting XI clock is not usable when the initial video start is flagged.
            if name(entry)=='Starting XI' and period==start_period and bounds[period,'half_start'] is None:lo=None
            if lo is None or hi is None:incomplete=True;continue
            assert 0<=lo<=hi<=4500
            if lo<hi:segments.append((period,lo,hi))
    return segments,not incomplete,halftime


def verify_recoveries(directory,check):
    receipts=json.loads((directory/'input-hashes.json').read_text());sources={v:Path(p) for p,v in receipts.items()}
    parents=[Path(p) for p in receipts if p.endswith('public-ratings.json') and 'supported-sample-final' in p]
    if len(parents)!=1:raise ValueError('one verified v2 parent required')
    parent=parents[0].parent
    previous={ (p['player_id'],p['match_id']):p for line in (parent/'source-replay.jsonl').open(encoding='utf8') for p in json.loads(line)['appearances'] }
    cached={};counts=defaultdict(int);old_bundes=[];new_bundes=[]
    for line in (directory/'source-replay.jsonl').open(encoding='utf8'):
        for row in json.loads(line)['appearances']:
            key=row['player_id'],row['match_id'];before=previous[key]
            if before['competition']=='1. Bundesliga':
                old_bundes.append(before);new_bundes.append(row)
            recovery=row.get('exposure_recovery')
            if recovery is None:
                check(row==before,'unaffected appearance changed');continue
            check(before['seconds'] is None and row['competition']!='1. Bundesliga','recovered outside authorized scope')
            fingerprint=row['source_sha256']
            if fingerprint not in cached:
                raw=sources[fingerprint].read_bytes()
                check(hashlib.sha256(raw).hexdigest()==fingerprint,'recovery source hash')
                cached[fingerprint]=json.loads(raw)
            events=cached[fingerprint];by_id={e['id']:e for e in events}
            if recovery['seconds'] is None:
                counts['withheld']+=1;check(row['seconds'] is None,'failed recovery adds minutes');continue
            expected,complete,halftime=oracle(events,row['team_id'],row['player_id'])
            actual=[(s['period'],Fraction(s['start']['numerator'],s['start']['denominator']),Fraction(s['end']['numerator'],s['end']['denominator'])) for s in recovery['segments']]
            check(actual==expected,'independent entry/exit interval union')
            check(recovery['complete']==complete,'independent full/partial status')
            seconds=sum((hi-lo for _,lo,hi in expected),Fraction())
            check(seconds==Fraction(row['seconds']['numerator'],row['seconds']['denominator']),'independent interval duration')
            counts['full' if complete else 'partial']+=1
            if halftime:counts['halftime_returns']+=1
            inside=lambda e:any(p==e['period'] and lo<=point(e)[1]<=hi for p,lo,hi in expected)
            for attribute,metric in row['metrics'].items():
                original=before['metrics'][attribute]
                if attribute=='press_resistance':
                    check(metric['numerator_ids']==original['numerator_ids'] and metric['denominator_ids']==original['denominator_ids'],'pressure action sample changed')
                    check(metric['included']==original['included'],'pressure admission changed during minute recovery')
                    continue
                selected={uid for uid in original['numerator_ids'] if complete or inside(by_id[uid])}
                omitted=set(original['numerator_ids'])-selected
                check(set(metric['numerator_ids'])==selected,'recovered metric action scope')
                check(set(metric.get('omitted_numerator_ids',[]))==omitted,'omitted action conservation')
                check(not selected.intersection(omitted),'overlapping included/omitted actions')
                if metric['included']:check(all(inside(by_id[uid]) for uid in selected),'action outside recovered denominator')
    check(old_bundes==new_bundes,'Bundesliga source observations changed')
    check(counts['full']+counts['partial']+counts['withheld']==238,'incomplete recovery population')
    return dict(counts)
