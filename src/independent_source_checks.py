"""Second calculation path over original JSON; no rating or trust promotion.

Does not call the reconstruction's event projection, metric extractors,
participation adapter or interval validator. Shared identity/alias policy and
component names remain authoritative. Same-provider corroboration is explicitly
distinct from independent external provenance attestation.
"""
from collections import Counter,defaultdict
from decimal import Decimal
from fractions import Fraction
import math
import re

from src.source_reconstruction import COUNT_NAMES,exact,rational,team_name
from src.statsbomb_participation import _team_name_agrees


class CheckMismatch(ValueError):
    """Unexpected source/derived disagreement; never overwrite or repair."""


def clock(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?',value):raise CheckMismatch('invalid original timestamp')
    h,m,s=value.split(':')
    if int(m)>=60 or Decimal(s)>=60:raise CheckMismatch('invalid clock component')
    return Fraction(int(h)*3600+int(m)*60)+Fraction(Decimal(s))


def boundaries(events,teams):
    result={}
    for period in (1,2):
        pair=[]
        for typ,attr in [('Half Start','half_start'),('Half End','half_end')]:
            rows=[e for e in events if e['period']==period and e['type']['name']==typ]
            vals={clock(e['timestamp']) for e in rows}
            usable=(len(vals)==1 and {e['team']['id'] for e in rows}==set(teams)
                    and not any(e.get(attr) or attr in e and not isinstance(e[attr],dict) for e in rows))
            value=next(iter(vals)) if usable else None
            if typ=='Half Start' and value!=0:value=None
            pair.append(value)
        result[period]=tuple(pair)
    return result


def endpoint(stint,side,pid,tid,events,bounds):
    reason=stint.get('start_reason' if side=='from' else 'end_reason')
    if side=='to' and reason=='Final Whistle':
        end=bounds[2][1];raw=stint.get('to')
        if stint.get('to_period') not in (None,2):return None
        if raw is not None:
            m,s=map(int,raw.split(':'))
            if end is None or (m-45)*60+s!=int(end):return None
        return (2,end) if end is not None else None
    period=stint.get(side+'_period');raw=stint.get(side)
    if period not in (1,2) or raw is None:return None
    minute,second=map(int,raw.split(':'))
    types={'Starting XI':'Starting XI','Tactical Shift':'Tactical Shift','Player On':'Player On','Player Off':'Player Off',
           'Player On (Off Camera)':'Player On','Player Off (Off Camera)':'Player Off','Player Off (Permanent)':'Player Off',
           'Foul Committed (Red Card)':'Foul Committed','Foul Committed (Second Yellow)':'Foul Committed'}
    allowed={'from':{'Starting XI','Tactical Shift','Player On','Player On (Off Camera)'},'to':{'Tactical Shift','Player Off','Player Off (Off Camera)','Player Off (Permanent)','Foul Committed (Red Card)','Foul Committed (Second Yellow)'}}
    substitution=isinstance(reason,str) and reason.startswith('Substitution - '+('On' if side=='from' else 'Off')+' (')
    typ='Substitution' if substitution else types.get(reason) if reason in allowed[side] else None
    values=set()
    for e in events.get((period,minute,second,tid,typ),[]):
        actor=e.get('player',{}).get('id')
        if typ=='Substitution' and side=='from':actor=e['substitution']['replacement']['id']
        if typ in ('Starting XI','Tactical Shift'):
            actor=pid if any(p['player']['id']==pid and (side=='to' or (p['position']['id'],p['position']['name'])==(stint.get('position_id'),stint.get('position'))) for p in e.get('tactics',{}).get('lineup',[])) else None
        if typ=='Foul Committed' and e.get('foul_committed',{}).get('card',{}).get('name') not in ('Red Card','Second Yellow'):continue
        # This resolves raw geometry only; check_match compares it with a valid
        # ledger. Permanent evidence must never resolve a temporary endpoint.
        if typ=='Player Off':
            permanent=e.get('player_off',{}).get('permanent')
            if reason=='Player Off (Permanent)' and permanent is not True:continue
            if reason!='Player Off (Permanent)' and permanent:continue
        if actor==pid:values.add(clock(e['timestamp']))
    return (period,next(iter(values))) if len(values)==1 else None


def exposure(positions,pid,tid,events,bounds):
    seconds=Fraction(0);allocation=defaultdict(Fraction);intervals=[]
    for p in positions:
        start=endpoint(p,'from',pid,tid,events,bounds);end=endpoint(p,'to',pid,tid,events,bounds)
        if start is None or end is None or end<start:return None
        duration=Fraction(0)
        for period in range(start[0],end[0]+1):
            lo,hi=bounds[period]
            if lo is None or hi is None or hi<lo:return None
            a=start[1] if period==start[0] else lo;b=end[1] if period==end[0] else hi
            if not lo<=a<=b<=hi:return None
            duration+=b-a
        seconds+=duration;allocation[p['position']]+=duration;intervals.append((start,end))
    ordered=sorted(intervals)
    if any(a[1]>b[0] for a,b in zip(ordered,ordered[1:])):return None
    return seconds,dict(allocation),intervals


def within(event,intervals,bounds):
    period=event['period'];time=clock(event['timestamp']);lo,hi=bounds[period]
    return bool(lo is not None and hi is not None and lo<=time<=hi and any(a<=(period,time)<=b for a,b in intervals))


def selected(events):
    """Independent raw-field transcription of existing count definitions.

    Also inventories total interceptions to expose the PDF definition conflict.
    PDF flags are geometry diagnostics under explicit forward-x interpretation;
    no PDF composite or line-breaking rating is computed.
    """
    by_actor=defaultdict(lambda:{n:[] for n in COUNT_NAMES});missing=Counter();totals=Counter();geometry=Counter()
    success={'Won','Success In Play','Success Out'}
    for e in events:
        typ=e['type']['name'];pid=e.get('player',{}).get('id');tid=e['team']['id'];k=(tid,pid)
        if typ=='Interception':totals['total_interceptions']+=1
        names=[]
        if typ=='Duel' and e.get('duel',{}).get('type',{}).get('name')=='Tackle' and e.get('duel',{}).get('outcome',{}).get('name') in success:names.append('tackles')
        if typ=='Interception' and e.get('interception',{}).get('outcome',{}).get('name') in success:names.append('interceptions')
        if typ=='Ball Recovery' and e.get('ball_recovery',{}).get('recovery_failure')!=True:names.append('recoveries')
        if typ in ('Pass','Dribble') and e.get('under_pressure')==True:
            part='pass' if typ=='Pass' else 'dribble';names.append('pressured_'+part+'_attempts')
            completed=e.get('pass',{}).get('outcome') is None if part=='pass' else e.get('dribble',{}).get('outcome',{}).get('name')=='Complete'
            if completed:names.append('pressured_'+part+'_completed')
        if typ=='Pass':
            p=e.get('pass',{});start=e.get('location');end=p.get('end_location')
            open_play=p.get('type') is None or p.get('type',{}).get('name') in ('Recovery','Interception')
            measurable=open_play and p.get('outcome',{}).get('name') not in ('Unknown','Injury Clearance')
            coords=(start or [])[:2]+(end or [])[:2]
            known=len(coords)==4 and all(type(x) in (int,float) and math.isfinite(x) for x in coords)
            if measurable and not known:missing[k]+=1
            if known:
                x,y,u,v=coords;forward=u-x;cross=min(2,max(0,int(u//40)))>min(2,max(0,int(x//40)))
                complete=p.get('outcome') is None
                prog=forward>=10 and math.hypot(120-u,40-v)<=.75*math.hypot(120-x,40-y)
                if complete:
                    geometry['completed_passes_with_geometry']+=1
                    geometry['pdf_forward_x_P10']+=forward>=10;geometry['pdf_forward_x_D20']+=forward>=20;geometry['pdf_Z_third_crossing']+=cross
                    geometry['P10_without_Joseph_distance_condition']+=forward>=10 and not prog
                if measurable and prog:
                    names.append('progressive_attempts')
                    if complete:
                        names.append('progressive_passes')
                        if cross:names.append('progressive_third_crossings')
        for name in names:by_actor[k][name].append(e['id']);totals[name]+=1
    return dict(by_actor),missing,totals,geometry


def check_match(fixture,lineups,events,appearances,metric_rows):
    teams={fixture[s][s+'_id']:fixture[s][s+'_name'] for s in ('home_team','away_team')}
    roster={};actor_findings=[];actor_refs=0
    if len(lineups)!=2:raise CheckMismatch('source roster must contain two teams')
    for t in lineups:
        if not _team_name_agrees(t['team_id'],teams.get(t['team_id']),t['team_name'],fixture):raise CheckMismatch('fixture/roster team mismatch')
        for p in t['lineup']:
            k=(t['team_id'],p['player_id'])
            if k in roster or any(pid==p['player_id'] for _,pid in roster):raise CheckMismatch('duplicate source actor ID')
            roster[k]=p
    eventmap={e['id']:e for e in events}
    if len(eventmap)!=len(events):raise CheckMismatch('duplicate original event UUID')
    for e in events:
        if 'match_id' in e and e['match_id']!=fixture['match_id']:raise CheckMismatch('original event match disagreement')
        tid=e['team']['id']
        if not _team_name_agrees(tid,teams.get(tid),e['team']['name'],fixture):raise CheckMismatch('original event team disagreement')
        if e['period'] not in (1,2) or int(clock(e['timestamp']))!=(e['minute']-(45 if e['period']==2 else 0))*60+e['second']:raise CheckMismatch('original event clock disagreement')
        actors=[('actor',e['player'])] if 'player' in e else []
        if 'substitution' in e:actors.append(('replacement',e['substitution']['replacement']))
        if 'recipient' in e.get('pass',{}):actors.append(('recipient',e['pass']['recipient']))
        actors += [('tactical',p['player']) for p in e.get('tactics',{}).get('lineup',[])]
        for role,p in actors:
            actor_refs+=1;expected=roster.get((tid,p['id']))
            if expected is None or p['name']!=expected['player_name']:
                actor_findings.append(dict(event_id=e['id'],player_id=p['id'],team_id=tid,actor_role=role,
                    source_actor_id=e.get('player',{}).get('id'),observed_name=p['name'],expected_name=None if expected is None else expected['player_name'],reason='RAW_ACTOR_ROSTER_DISAGREEMENT'))
    bounds=boundaries(events,teams);counts,missing,totals,geometry=selected(events)
    transitions=defaultdict(list)
    for e in events:transitions[e['period'],e['minute'],e['second'],e['team']['id'],e['type']['name']].append(e)
    metrics={(m['team_id'],m['player_id']):m for m in metric_rows};active={(a['team_id'],a['player_id']):a for a in appearances}
    if len(active)!=len(appearances) or len(metrics)!=len(metric_rows) or active.keys()!=metrics.keys():raise CheckMismatch('duplicate/misaligned derived actors')
    unknown=[dict(team_id=k[0],player_id=k[1],component=n,event_ids=ids) for k,cs in counts.items() if k not in active for n,ids in cs.items() if ids]
    rows=[]
    for k,a in sorted(active.items()):
        if a['match_id']!=fixture['match_id'] or k not in roster or a['player_name_raw']!=roster[k]['player_name']:raise CheckMismatch('ledger/source identity mismatch')
        if a['original_positions']!=roster[k]['positions']:raise CheckMismatch('source stints altered in ledger')
        raw=exposure(roster[k]['positions'],k[1],k[0],transitions,bounds)
        valid=a['participation_status']=='STRUCTURALLY_VALID';seconds=None;positions=None;intervals=[]
        if valid:
            if raw is None:raise CheckMismatch('valid ledger exposure lacks independent endpoint support')
            seconds,positions,intervals=raw
            supplied=[((o['start']['period'],Fraction(o['start']['seconds'])),(o['end']['period'],Fraction(o['end']['seconds']))) for o in a['playing_intervals']]
            supplied_positions={p['position']:exact(p['elapsed_seconds']) for p in a['position_allocation']}
            if seconds!=exact(a['validated_elapsed_seconds']) or positions!=supplied_positions or intervals!=supplied:raise CheckMismatch('independent interval/position/elapsed disagreement')
        elif a['validated_elapsed_seconds'] is not None or a['position_allocation'] is not None:raise CheckMismatch('unresolved minutes promoted')
        components={}
        for name in COUNT_NAMES:
            ids=sorted(counts.get(k,{}).get(name,[]));c=metrics[k]['components'][name]
            if ids!=c['event_ids'] or len(ids)!=c['count']:raise CheckMismatch('independent numerator UUID disagreement: '+name)
            bad=[uid for uid in ids if not within(eventmap[uid],intervals,bounds)] if valid else []
            if bad!=c['unaligned_event_ids']:raise CheckMismatch('independent action/exposure disagreement')
            ready=valid and seconds>0 and not bad and not (name.startswith('progressive') and missing[k]) and not any(u['component']==name for u in unknown)
            rate=float(Fraction(len(ids)*5400,1)/seconds) if ready else None
            if (rate is None)!=(c['per90'] is None) or rate is not None and not math.isclose(rate,c['per90'],rel_tol=1e-12,abs_tol=1e-12):raise CheckMismatch('independent rate availability/arithmetic disagreement')
            components[name]=dict(count=len(ids),aligned=ready,per90=rate,unaligned_event_ids=bad)
        rows.append(dict(match_id=fixture['match_id'],team_id=k[0],player_id=k[1],team=a['team'],competition_name=a['competition_name'],season_name=a['season_name'],
            participation_status=a['participation_status'],minute_check='INDEPENDENT_CALCULATION_AGREES' if valid else 'WITHHELD_UNRESOLVED_SOURCE',
            independent_seconds=rational(seconds) if valid else None,independent_position_seconds={n:rational(v) for n,v in sorted((positions or {}).items())},
            components=components,actor_findings=[f for f in actor_findings if k[1] in (f['player_id'],f['source_actor_id'])],
            original_failure_reasons=a['failure_reasons'],independent_external_attestation=False,production_certified=False))
    return dict(rows=rows,actor_findings=actor_findings,actor_references_checked=actor_refs,orphan_component_events=unknown,
        original_events=len(events),roster_actors=len(roster),source_totals=dict(totals),pdf_geometry_diagnostics=dict(geometry),
        pdf_composite_score=None,pdf_geometry_interpretation='FORWARD_X_DIAGNOSTIC_ONLY_NOT_AN_APPROVED_FORMULA')


def reference_readiness(clubs,aggregates):
    """Check exact raw sums and role evidence; never select a transfer policy."""
    players=defaultdict(list)
    for c in clubs:players[c['player_id']].append(c)
    rows=[]
    # Existing contributor's finest role groups, before comparison-pool mapping.
    # Never combine unrelated positions into OTHER before choosing dominance.
    groups={'GK':{'Goalkeeper'},'CB':{'Center Back','Left Center Back','Right Center Back'},
        'DM':{'Center Defensive Midfield','Left Defensive Midfield','Right Defensive Midfield'},
        'CM':{'Center Midfield','Left Center Midfield','Right Center Midfield'},
        'FB':{'Right Back','Left Back','Right Wing Back','Left Wing Back'},'WM':{'Right Midfield','Left Midfield'},
        'AM':{'Right Attacking Midfield','Center Attacking Midfield','Left Attacking Midfield'},
        'ATT':{'Right Wing','Left Wing','Center Forward','Right Center Forward','Left Center Forward','Striker','Secondary Striker'}}
    position_roles={name.lower().replace(' ',''):role for role,names in groups.items() for name in names}
    for c in sorted(clubs,key=lambda c:(c['player_id'],c['team'],c['competition_name'],c['season_name'])):
        k=(c['player_id'],c['team'],c['competition_name'],c['season_name']);g=aggregates[k]
        if exact(c['supported_seconds'])!=g['seconds'] or set(c['match_ids'])!=g['matches']:raise CheckMismatch('club exposure/match sum differs')
        for n in COUNT_NAMES:
            if c['components'][n]['raw_source_count']!=g['counts'][n]:raise CheckMismatch('club raw numerator sum differs')
        mapped=Counter()
        for position,seconds in g['positions'].items():mapped[position_roles.get(position.lower().replace(' ',''),'UNKNOWN')]+=seconds
        top=max(mapped.values(),default=0);fine=sorted(role for role,v in mapped.items() if v==top and top>0)
        dominant=sorted({'MID' if role in ('DM','CM') else role for role in fine})
        delivered='MID' if c['delivered_role'] in ('DM','CM','MID') else 'CB' if c['delivered_role']=='CB' else None
        complete=not g['unresolved'] and not c['identity_reasons']
        expected_candidate=bool(complete and g['seconds']>=54000 and delivered)
        if c['candidate_900_minutes_evidence_met']!=expected_candidate or c['provider_observed_exposure_complete']!=complete:raise CheckMismatch('independent 900-minute/completeness gate disagrees')
        if {p:exact(v)*60 for p,v in c['source_position_minutes'].items()}!=dict(g['positions']):raise CheckMismatch('club source position allocation differs')
        for n,v in c['components'].items():
            expected_rate=float(Fraction(g['counts'][n]*5400,1)/g['seconds']) if complete and g['seconds']>0 and g['aligned_matches'][n]==g['matches'] else None
            if v['aligned_match_ids']!=sorted(g['aligned_matches'][n]) or v['aligned_subset_count']!=g['aligned_counts'][n] or exact(v['aligned_subset_minutes'])*60!=g['aligned_seconds'][n]:raise CheckMismatch('club aligned count/exposure subset differs')
            if (expected_rate is None)!=(v['provider_scope_per90'] is None) or expected_rate is not None and not math.isclose(expected_rate,v['provider_scope_per90'],rel_tol=1e-12,abs_tol=1e-12):raise CheckMismatch('club numerator/denominator scope differs')
        role_supported=dominant==[delivered] if delivered else False
        technical=bool(c['candidate_900_minutes_evidence_met'] and all(c['components'][n]['provider_scope_per90'] is not None for n in COUNT_NAMES[:7])
                       and not g['actor_findings'] and role_supported)
        rows.append(dict(player_id=c['player_id'],team_id=c['team_id'],team=c['team'],competition_name=c['competition_name'],season_name=c['season_name'],
            original_candidate_900=c['candidate_900_minutes_evidence_met'],known_supported_subset_900=g['seconds']>=54000,
            independent_seconds=rational(g['seconds']),unresolved_appearances=g['unresolved'],
            independently_supported_comparison_groups=dominant,delivered_comparison_group=delivered,source_dominant_group_agrees=role_supported,
            source_dominant_role_groups=fine,source_group_seconds={role:rational(v) for role,v in sorted(mapped.items())},multi_club_contexts=len(players[c['player_id']]),
            existing_identity_reasons=c['identity_reasons'],
            transfer_reference_ambiguous=len(players[c['player_id']])>1,technical_candidate_checks_passed=technical,
            actor_findings=g['actor_findings'],reference_member=False,independent_external_attestation=False,fully_evidence_ready=False,
            blockers=['independent_external_or_human_attestation_pending','exposure_and_role_policy_approval_pending','reference_membership_approval_pending','individual_formula_approval_pending']+
                ([] if technical else ['technical_evidence_or_eligibility_not_ready'])+(['transfer_reference_policy_pending'] if len(players[c['player_id']])>1 else [])+
                (['historical_ligue1_scope_pending'] if c['competition_name']=='Ligue 1' else [])+
                (['3879594_scope_pending'] if c['includes_policy_pending_3879594'] else []),
            production_certified=False,publication_authorized=False))
    return rows
