"""Independent raw-source off-field-card verification; no production decisions.

Uses a separate event state walk, original lineup endpoints and exact interval
unions. All original disciplinary UUIDs remain in the returned evidence ledger.
"""
from collections import defaultdict

from scripts import decoder_fix_independent as raw


def union(intervals, bounds):
    pieces=defaultdict(list)
    for lo,hi in intervals:
        if lo>hi:return None
        for period in range(lo[0],hi[0]+1):
            if period not in bounds:return None
            start=lo[1] if period==lo[0] else bounds[period][0]
            end=hi[1] if period==hi[0] else bounds[period][1]
            if not bounds[period][0]<=start<=end<=bounds[period][1]:return None
            if start<end:pieces[period].append((start,end))
    answer=[]
    for period,rows in sorted(pieces.items()):
        compact=[]
        for lo,hi in sorted(rows):
            if compact and lo<=compact[-1][1]:compact[-1]=(compact[-1][0],max(hi,compact[-1][1]))
            else:compact.append((lo,hi))
        answer.extend((period,lo,hi) for lo,hi in compact)
    return answer


def reconstruct(pid,tid,player,events,bounds,boundary_issues,*,transition_events=None):
    # Index only the records the legacy endpoint/state arithmetic consumes.
    # Full raw events remain available below for activity/recipient proofs.
    if transition_events is None:
        transition_events=[e for e in events if raw.typ(e) in ('Starting XI','Tactical Shift','Substitution','Player On','Player Off') or raw.card(e) in ('Red Card','Second Yellow')]
    initial=raw.reconstruct(pid,tid,player,transition_events,bounds,boundary_issues)
    cards=[e for e in transition_events if e['team']['id']==tid and e.get('player',{}).get('id')==pid
           and raw.typ(e)=='Bad Behaviour' and raw.card(e) in ('Red Card','Second Yellow')]
    if not cards:
        initial['off_field_discipline']=[]
        return initial
    team=[e for e in events if e['team']['id']==tid]
    unused=[e for e in team if raw.typ(e)=='Starting XI']
    safe=bool(cards and not boundary_issues and set(bounds)=={1,2}
        and all(lo==0 and hi>lo for lo,hi in bounds.values()) and len(unused)==1
        and raw.clock(unused[0])==(1,0)
        and len(unused[0].get('tactics',{}).get('lineup',[]))==11
        and len({p['player']['id'] for p in unused[0].get('tactics',{}).get('lineup',[])})==11
        and all(bounds[e['period']][0]<=raw.clock(e)[1]<=bounds[e['period']][1] for e in cards)
        and player.get('player_id',pid)==pid)
    identified=[]
    if safe:
        cardids={e['id'] for e in cards}
        xs=[e for e in team if raw.typ(e) in ('Starting XI','Tactical Shift')
            and any(p['player']['id']==pid for p in e.get('tactics',{}).get('lineup',[]))]
        activity=[e for e in team if e.get('player',{}).get('id')==pid or e.get('pass',{}).get('recipient',{}).get('id')==pid]
        incoming=[e for e in team if raw.typ(e)=='Substitution' and e['substitution']['replacement']['id']==pid]
        proof_events={e['id']:e for e in unused+xs+activity+incoming+[e for e in team if raw.typ(e) in ('Half Start','Half End')]}
        if all('index' in e for e in proof_events.values()):
            sequence=[raw.clock(e) for e in sorted(proof_events.values(),key=lambda e:e['index'])]
            if sequence!=sorted(sequence):
                initial['off_field_discipline']=[]
                initial['issues']=sorted(set(initial['issues'])|{'UNRESOLVED_DISCIPLINARY_STATE'})
                return initial
        if not player.get('positions'):
            if not xs and not incoming and all(raw.typ(e)=='Bad Behaviour' and (not e.get('position') or e['position']=={'id':0,'name':'Substitute'}) for e in activity):
                identified=[dict(event_id=e['id'],state='UNUSED_ROSTER',proof_event_ids=[unused[0]['id']]) for e in cards]
        else:
            # Build our own state in provider sequence. No production Stint,
            # SourceCheck, active-state helper or decision is consulted.
            relevant=[]
            for e in team:
                actor=e.get('player',{}).get('id')
                if (raw.typ(e)=='Starting XI' and e in xs or e in incoming
                    or actor==pid and (raw.typ(e) in ('Player On','Player Off','Substitution') or raw.card(e) in ('Red Card','Second Yellow'))):relevant.append(e)
            clocks=defaultdict(list)
            for e in relevant:clocks[raw.clock(e)].append(e)
            reliable=all(len(es)==1 or all('index' in e for e in es) for es in clocks.values())
            if all('index' in e for e in relevant):
                source_clocks=[raw.clock(e) for e in sorted(relevant,key=lambda e:e['index'])]
                reliable &= source_clocks==sorted(source_clocks)
            playing=False;ever_entered=False;temporary=False;sub=None;proof=[]
            for e in sorted(relevant,key=lambda e:(*raw.clock(e),e.get('index',0))):
                t=raw.typ(e)
                if e['id'] in cardids:
                    if sub is None or playing or temporary:reliable=False
                    else:identified.append(dict(event_id=e['id'],state='AFTER_SUBSTITUTION',proof_event_ids=list(proof)))
                elif t=='Starting XI' or e in incoming:
                    if ever_entered or playing or sub is not None:reliable=False
                    playing=True;ever_entered=True;proof.append(e['id'])
                elif t=='Player On':
                    if not temporary or playing or sub is not None:reliable=False
                    playing=True;temporary=False;proof.append(e['id'])
                elif t=='Player Off' and not e.get('player_off',{}).get('permanent'):
                    if not playing:reliable=False
                    playing=False;temporary=True;proof.append(e['id'])
                elif t=='Substitution':
                    if not playing or sub is not None:reliable=False
                    playing=False;temporary=False;sub=e;proof.append(e['id'])
                else:reliable=False
            candidate=raw.reconstruct(pid,tid,player,[e for e in transition_events if e['id'] not in cardids],bounds,boundary_issues)
            reliable &= bool(sub and not playing and len(identified)==len(cards) and not candidate['issues']
                and candidate['seconds'] is not None and candidate['seconds']>0
                and union(candidate['intervals'],bounds)==union(candidate['lineup_intervals'],bounds))
            if any(e['id'] not in candidate['lineup_event_ids'] for e in relevant if e['id'] not in cardids):reliable=False
            for e in xs:
                point=raw.clock(e)
                active=[position for lo,hi,position in candidate['lineup_position_intervals'] if lo<=point<hi]
                supplied=next(p['position']['name'] for p in e['tactics']['lineup'] if p['player']['id']==pid)
                if len(active)==1 and active[0]!=supplied:reliable=False
            if sub is not None:
                terminal=raw.clock(sub)
                if any(raw.clock(e)>=terminal for e in xs):reliable=False
                for e in activity:
                    if raw.typ(e) in ('Bad Behaviour','Player On','Player Off','Substitution'):continue
                    point=raw.clock(e)
                    if (point[0] not in bounds or not bounds[point[0]][0]<=point[1]<=bounds[point[0]][1]
                        or not any(lo<=point<=hi for lo,hi in candidate['intervals'])
                        or point==terminal and ('index' not in e or 'index' not in sub or e['index']>sub['index'])):reliable=False
            if not reliable:identified=[]
    if identified:
        removed={d['event_id'] for d in identified}
        result=raw.reconstruct(pid,tid,player,[e for e in transition_events if e['id'] not in removed],bounds,boundary_issues)
        result['event_ids']=sorted(set(result['event_ids'])|removed)
    else:
        result=initial
        if cards and not initial['active']:
            result['issues']=sorted(set(result['issues'])|{'UNRESOLVED_DISCIPLINARY_STATE'})
    result['off_field_discipline']=identified
    return result
