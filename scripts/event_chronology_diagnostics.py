"""Source-bound diagnostic admission corrections; no production/source writes.

Unknown duration alone does not invalidate an action ratio. Verified conflicting
chronology does. Withhold the complete component, preserving raw UUIDs and counts.
"""
import copy
import hashlib
import json
from pathlib import Path
from collections import defaultdict
from scripts import decoder_fix_independent as raw
from scripts import off_field_card_independent as state
from src import independent_source_checks as second


def decoded(row,key):
    v=row[key]
    return json.loads(v) if isinstance(v,str) and v[:1] in ('[','{') else v


def verify_exception(row):
    """Reopen originals; establish contradiction without choosing a new clock."""
    documents=decoded(row,'source_documents');parsed=[]
    for b in documents:
        data=Path(b['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=b['sha256']:raise ValueError('source hash disagreement')
        parsed.append(json.loads(data))
    fixtures,lineups,events=parsed
    pid,mid,tid=(int(row[k]) for k in ('player_id','match_id','team_id'))
    fixture=next(f for f in fixtures if f['match_id']==mid)
    if tid not in (fixture['home_team']['home_team_id'],fixture['away_team']['away_team_id']):raise ValueError('fixture team mismatch')
    roster={(t['team_id'],p['player_id']):p for t in lineups for p in t['lineup']}
    if (tid,pid) not in roster:raise ValueError('actor not in fixture roster')
    event=next(e for e in events if e['id']==row['event_id'])
    if (event['team']['id'],event['player']['id'],event['player']['name'])!=(tid,pid,roster[tid,pid]['player_name']):raise ValueError('event stable actor disagreement')
    if (event['period'],event['timestamp'],event['index'])!=(int(row['period']),row['timestamp'],int(row['event_index'])):raise ValueError('event binding disagreement')
    bounds,issues,refs=raw.boundaries(events,{t['team_id'] for t in lineups})
    separate=second.boundaries(events,{t['team_id'] for t in lineups})
    point=raw.clock(event)
    if point[0] not in bounds or bounds[point[0]]!=separate[point[0]]:raise ValueError('boundary interpretation unresolved')
    outside_period=not bounds[point[0]][0]<=point[1]<=bounds[point[0]][1]
    oracle=state.reconstruct(pid,tid,roster[tid,pid],events,bounds,issues)
    transition_index=defaultdict(list)
    for e in events:transition_index[e['period'],e['minute'],e['second'],e['team']['id'],raw.typ(e)].append(e)
    lineup=second.exposure(roster[tid,pid]['positions'],pid,tid,transition_index,separate)
    if lineup is not None and (lineup[0]!=oracle['lineup_seconds'] or lineup[2]!=oracle['lineup_intervals']):raise ValueError('independent lineup resolution disagreement')
    outside_state=oracle['seconds'] is not None and not any(lo<=point<=hi for lo,hi in oracle['intervals'])
    if not (outside_period or outside_state):raise ValueError('no independently established chronology conflict')
    return dict(player_id=pid,match_id=mid,team_id=tid,event_id=event['id'],period=event['period'],timestamp=event['timestamp'],event_index=event['index'],selected=sorted(raw.selected(event)),outside_period=outside_period,outside_event_state=outside_state,independent=oracle,separate_lineup=lineup,boundaries=bounds,boundary_uuids=refs,original_lineup_positions=roster[tid,pid]['positions'],source_documents=documents)


def correct_diagnostic_facts(facts,exceptions):
    """Return new in-memory facts and exact before/after admission evidence."""
    indexed={(f['player_id'],f['match_id']):f for f in facts}
    if len(indexed)!=len(facts):raise ValueError('duplicate diagnostic fact identity')
    conflicts={};proofs=[]
    for row in exceptions:
        key=int(row['player_id']),int(row['match_id'])
        if key not in indexed:continue
        fact=indexed[key];uid=row['event_id']
        affected=[a for a,m in fact['metrics'].items() if m['supported'] and (uid in m['numerator_ids'] or uid in (m['denominator_ids'] or []))]
        if not affected:continue
        proof=verify_exception(row)
        evidence=fact['evidence']
        if (int(evidence['component_player_id']),int(evidence['component_match_id']),int(evidence['component_team_id']))!=(key[0],key[1],proof['team_id']):raise ValueError('fact/source identity disagreement')
        proofs.append(proof)
        for attr in affected:
            expected='press_attempts' if attr=='press_resistance' and uid in (fact['metrics'][attr]['denominator_ids'] or []) else attr
            if expected not in proof['selected'] or uid in fact['metrics'][attr]['numerator_ids'] and attr not in proof['selected']:raise ValueError('metric definition disagreement')
            conflicts.setdefault((key,attr),set()).add(uid)
    corrected=copy.deepcopy(facts);changed=[];components=[]
    for fact in corrected:
        key=fact['player_id'],fact['match_id']
        for attr,metric in fact['metrics'].items():
            triggers=conflicts.get((key,attr))
            if not triggers:continue
            before=copy.deepcopy(metric)
            metric['supported']=False
            metric['reasons']=sorted(set(metric['reasons'])|{'SOURCE_CHRONOLOGY_CONFLICT'})
            components.append(dict(player_id=key[0],match_id=key[1],metric=attr,trigger_uuids=sorted(triggers),before=before,after=copy.deepcopy(metric)))
            for uid in sorted(set(metric['numerator_ids'])|set(metric['denominator_ids'] or [])):
                changed.append(dict(player_id=key[0],match_id=key[1],metric=attr,event_id=uid,in_numerator=uid in metric['numerator_ids'],in_denominator=uid in (metric['denominator_ids'] or []),trigger_conflict=uid in triggers,before_admitted=True,after_admitted=False,raw_uuid_retained=True,reason='SOURCE_CHRONOLOGY_CONFLICT: complete component withheld to preserve numerator/denominator scope'))
    return corrected,changed,dict(components=components,source_proofs=proofs)
