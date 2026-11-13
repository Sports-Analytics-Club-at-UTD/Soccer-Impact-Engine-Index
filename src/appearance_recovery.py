"""Recover source-backed playing exposure without treating role stints as minutes.

Physical Starting XI/substitution/off/on/card records establish participation.
Tactical position labels do not establish entry or exit. Flagged boundaries never
become invented kickoffs/final whistles. A verified portion is explicitly partial.
"""
from dataclasses import dataclass
from fractions import Fraction

from scripts.decoder_fix_independent import clock, typ, card


@dataclass(frozen=True)
class Segment:
    period: int
    start: Fraction
    end: Fraction
    start_reference: str
    end_reference: str


@dataclass(frozen=True)
class ExposureRecovery:
    segments: tuple
    complete: bool
    reasons: tuple
    proof_references: tuple

    @property
    def seconds(self):
        return sum((s.end-s.start for s in self.segments), Fraction()) if self.segments else None


def contains(event, segments):
    period, point=clock(event)
    return any(s.period==period and s.start<=point<=s.end for s in segments)


def recover_exposure(events, team_id, player_id, *, off_field_ids=()):
    """Conservative full/partial duration from original physical transitions.

    A contradiction in physical participation withholds the disputed remainder;
    an already closed, verified prefix can survive an incompatible later return.
    Missing boundaries withhold only intervals that actually depend on them.
    A period-local entry/exit pair can be timed without an unrelated final whistle.
    """
    def blocked(reason):return ExposureRecovery((),False,(reason,),())
    if not events or len({e['id'] for e in events})!=len(events):return blocked('DUPLICATE_OR_EMPTY_EVENTS')
    indices=[e.get('index') for e in events]
    if any(type(i) is not int or i<=0 for i in indices) or len(set(indices))!=len(indices):
        return blocked('UNRELIABLE_SOURCE_ORDER')
    ordered=sorted(events,key=lambda e:e['index'])
    teams={e['team']['id'] for e in ordered}
    if len(teams)!=2 or team_id not in teams:return blocked('EXACT_TWO_TEAM_CONTEXT_REQUIRED')
    periods={e['period'] for e in ordered}
    if periods!={1,2}:return blocked('UNSUPPORTED_PERIOD_SCOPE')
    xi=[e for e in ordered if e['team']['id']==team_id and typ(e)=='Starting XI']
    if len(xi)!=1 or clock(xi[0])!=(1,0):return blocked('UNIQUE_ORIGINAL_STARTING_XI_REQUIRED')
    members=xi[0].get('tactics',{}).get('lineup',[])
    if len(members)!=11 or len({m['player']['id'] for m in members})!=11:return blocked('INVALID_STARTING_XI_MEMBERSHIP')
    starter=any(m['player']['id']==player_id for m in members)
    bounds={};proof=[]
    for period in (1,2):
        bounds[period]={}
        for kind,field in [('Half Start','half_start'),('Half End','half_end')]:
            records=[e for e in ordered if e['period']==period and typ(e)==kind]
            times={clock(e)[1] for e in records}
            paired=len(records)==2 and {e['team']['id'] for e in records}==teams and len(times)==1
            time=next(iter(times)) if paired else None
            valid=paired and all(isinstance(e.get(field,{}),dict) and not e.get(field,{}) for e in records)
            valid=valid and (time==0 if kind=='Half Start' else time is not None and 0<time<=4500)
            bounds[period][field]=(time if valid else None,records[0]['id'] if records else '',time)
            proof.extend(e['id'] for e in records)
    transitions=[]
    for e in ordered:
        if e['team']['id']!=team_id:continue
        actor=e.get('player',{}).get('id')==player_id
        incoming=typ(e)=='Substitution' and e['substitution']['replacement']['id']==player_id
        terminal=actor and (typ(e) in ('Substitution','Player Off') or card(e) in ('Red Card','Second Yellow'))
        if incoming or terminal or actor and typ(e)=='Player On':
            if e['id'] not in off_field_ids:transitions.append(e)
    if [clock(e) for e in transitions]!=sorted(clock(e) for e in transitions):return blocked('TRANSITION_CLOCK_INDEX_DISAGREEMENT')
    if len({clock(e) for e in transitions})!=len(transitions):return blocked('AMBIGUOUS_EQUAL_CLOCK_TRANSITIONS')
    state='ACTIVE' if starter else 'UNUSED';ever=starter;segments=[];reasons=set();proof.append(xi[0]['id'])
    transition_ids={e['id'] for e in transitions}
    previous_period=1
    start_time,start_ref,_=bounds[1]['half_start']
    opened=(start_time,start_ref) if state=='ACTIVE' else None

    def close(period,end,ref):
        if opened is None:return
        start,origin=opened
        if start is None or end is None:
            reasons.add('UNVERIFIED_PERIOD_BOUNDARY');return
        if end<start:raise ValueError('reversed physical interval')
        if end>start:segments.append(Segment(period,start,end,origin,ref))

    def prefix(reason):
        if not segments:return blocked(reason)
        return ExposureRecovery(tuple(segments),False,(reason,),tuple(dict.fromkeys(proof)))

    for e in ordered:
        period=e['period'];point=clock(e)[1]
        if period<previous_period:return blocked('INTERLEAVED_SOURCE_PERIODS')
        if period!=previous_period:
            if state=='ACTIVE':
                end,end_ref,_=bounds[previous_period]['half_end'];close(previous_period,end,end_ref)
            previous_period=period
            begin,begin_ref,_=bounds[period]['half_start']
            opened=(begin,begin_ref) if state=='ACTIVE' else None
        if e['team']['id']!=team_id:continue
        actor=e.get('player',{}).get('id')==player_id
        recipient=e.get('pass',{}).get('recipient',{}).get('id')==player_id
        if e['id'] in transition_ids:
            t=typ(e);incoming=t=='Substitution' and e['substitution']['replacement']['id']==player_id
            observed_limit=bounds[period]['half_end'][2]
            # A documented return between paired halftime whistles and second-
            # half starts is an off-pitch break transition, not playing time.
            if t=='Player On' and state=='TEMPORARILY_OFF' and period==1 and bounds[1]['half_end'][0] is not None and point>bounds[1]['half_end'][0]:
                ends=[x for x in ordered if x['period']==1 and typ(x)=='Half End']
                starts=[x for x in ordered if x['period']==2 and typ(x)=='Half Start']
                if bounds[2]['half_start'][0]==0 and ends and starts and max(x['index'] for x in ends)<e['index']<min(x['index'] for x in starts):
                    state='ACTIVE';opened=None;proof.append(e['id']);continue
            if point<0 or observed_limit is not None and point>observed_limit:return blocked('TRANSITION_OUTSIDE_OBSERVED_PERIOD')
            if incoming:
                if state!='UNUSED' or ever:return blocked('CONFLICTING_ENTRY')
                state='ACTIVE';ever=True;opened=(point,e['id'])
            elif t=='Player On':
                if state!='TEMPORARILY_OFF':return prefix('CONFLICTING_RETURN')
                state='ACTIVE';opened=(point,e['id'])
            else:
                if state!='ACTIVE':return blocked('EXIT_WHILE_INACTIVE')
                try:close(period,point,e['id'])
                except ValueError:return blocked('REVERSED_PHYSICAL_INTERVAL')
                opened=None
                state='TEMPORARILY_OFF' if t=='Player Off' and not e.get('player_off',{}).get('permanent') else 'TERMINAL'
            proof.append(e['id'])
        elif (actor or recipient) and typ(e)!='Bad Behaviour' and e['id'] not in off_field_ids:
            if state!='ACTIVE':return prefix('ACTIVITY_OUTSIDE_SUPPORTED_STATE')
        elif typ(e)=='Tactical Shift':
            snapshot=e.get('tactics',{}).get('lineup',[])
            listed=sum(m['player']['id']==player_id for m in snapshot)
            if len(snapshot)!=11 or len({m['player']['id'] for m in snapshot})!=11:return blocked('INVALID_TACTICAL_MEMBERSHIP')
            if listed>1 or state=='ACTIVE' and listed!=1:return blocked('PHYSICAL_TACTICAL_MEMBERSHIP_CONFLICT')
            # Later passive membership cannot undo an explicit permanent exit.
    if state=='ACTIVE':
        end,end_ref,_=bounds[2]['half_end']
        try:close(2,end,end_ref)
        except ValueError:return blocked('REVERSED_PHYSICAL_INTERVAL')
    elif state=='TEMPORARILY_OFF':reasons.add('UNRESOLVED_TEMPORARY_ABSENCE_AT_END')
    if not ever:return blocked('NO_ORIGINAL_ENTRY')
    if not segments:return blocked('NO_SUPPORTED_CLOSED_INTERVAL')
    for s in segments:
        if not 0<=s.start<s.end<=4500:return blocked('IMPLAUSIBLE_PHYSICAL_INTERVAL')
    for a,b in zip(segments,segments[1:]):
        if a.period>b.period or a.period==b.period and a.end>b.start:return blocked('OVERLAPPING_PHYSICAL_INTERVALS')
    return ExposureRecovery(tuple(segments),not reasons,tuple(sorted(reasons)),tuple(dict.fromkeys(proof)))
