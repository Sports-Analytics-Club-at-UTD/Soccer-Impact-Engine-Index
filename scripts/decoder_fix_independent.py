"""Independent original-byte audit. Does not import production decoders/scorers.

Run with Python -B; source is read-only, output must be a new directory.
All hypothetical measurements retain the existing frozen reference and position.
"""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import statistics
import subprocess
import unicodedata

ATTRS = ('tackles', 'interceptions', 'recoveries', 'press_resistance', 'progressive_passing')
PUBLIC = {'progressive_passing': 'line_breaking_passes'}
FOUR = {'Premier League', 'La Liga', 'Serie A', 'Ligue 1'}


def rational(x):
    return None if x is None else F(x['numerator'], x['denominator'])


def clock(e):
    if '_audit_clock' in e:return e['_audit_clock']
    h, m, s = e['timestamp'].split(':')
    value=e['period'], F(int(h)*3600+int(m)*60) + F(Decimal(s))
    e['_audit_clock']=value
    return value


def typ(e):
    return e.get('type', {}).get('name')


def card(e):
    return e.get('bad_behaviour', {}).get('card', {}).get('name',
        e.get('foul_committed', {}).get('card', {}).get('name'))


def selected(e):
    """Five definitions implemented directly against original nested JSON."""
    out = set(); t = typ(e)
    won = {'Won', 'Success In Play', 'Success Out'}
    if t == 'Duel' and e.get('duel', {}).get('type', {}).get('name') == 'Tackle' and e['duel'].get('outcome', {}).get('name') in won:
        out.add('tackles')
    if t == 'Interception' and e.get('interception', {}).get('outcome', {}).get('name') in won:
        out.add('interceptions')
    if t == 'Ball Recovery' and e.get('ball_recovery', {}).get('recovery_failure') is not True:
        out.add('recoveries')
    if e.get('under_pressure') is True and t in ('Pass', 'Dribble'):
        out.add('press_attempts')
        if t == 'Pass' and e.get('pass', {}).get('outcome') is None or t == 'Dribble' and e.get('dribble', {}).get('outcome', {}).get('name') == 'Complete':
            out.add('press_resistance')
    p = e.get('pass', {})
    if t == 'Pass' and p.get('type', {}).get('name') in (None, 'Recovery', 'Interception') and p.get('outcome') is None:
        a, b = e.get('location'), p.get('end_location')
        if a and b and len(a) >= 2 and len(b) >= 2 and b[0]-a[0] >= 10 and math.hypot(120-b[0], 40-b[1]) <= .75*math.hypot(120-a[0], 40-a[1]):
            out.add('progressive_passing')
    return out


def boundaries(events, tids):
    out = {}; issues = []; refs = []
    for p in (1, 2):
        vals = []
        for name, field in [('Half Start', 'half_start'), ('Half End', 'half_end')]:
            es = [e for e in events if e['period'] == p and typ(e) == name]
            times = {clock(e)[1] for e in es}; refs += [e['id'] for e in es]
            if len(times) != 1 or {e['team']['id'] for e in es} != tids:
                issues.append('MISSING_OR_DISAGREEING_BOUNDARY'); vals.append(None)
            elif any(e.get(field) or field in e and not isinstance(e[field], dict) for e in es):
                issues.append('FLAGGED_VIDEO_BOUNDARY'); vals.append(None)
            else:
                value = next(iter(times)); vals.append(value)
                if name == 'Half Start' and value != 0: issues.append('NONZERO_VIDEO_ORIGIN')
        if None not in vals:
            out[p] = tuple(vals)
            if vals[1] <= vals[0] or vals[1] > 4500: issues.append('IMPLAUSIBLE_PERIOD_DURATION')
    return out, sorted(set(issues)), refs


def elapsed(a, b, bounds):
    if a > b or a[0] not in bounds or b[0] not in bounds: return None
    total = F(0)
    for p in range(a[0], b[0]+1):
        if p not in bounds: return None
        lo = a[1] if p == a[0] else bounds[p][0]
        hi = b[1] if p == b[0] else bounds[p][1]
        if not bounds[p][0] <= lo <= hi <= bounds[p][1]: return None
        total += hi-lo
    return total


def reconstruct(pid, tid, player, events, bounds, boundary_issues):
    """Event state machine, cross-checked against independently resolved lineup geometry.

    Tactical shifts do not create entry/exit events in this state machine. This
    deliberately differs from the production position-stint sequence decoder.
    """
    issues = list(boundary_issues); used = []; intervals = []; opened = None
    ever = False; permanent = False
    for e in sorted(events, key=lambda e: (*clock(e), e.get('index', 0))):
        if e['team']['id'] != tid: continue
        actor = e.get('player', {}).get('id'); t = typ(e); point = clock(e)
        start = (t == 'Starting XI' and any(x['player']['id'] == pid for x in e.get('tactics', {}).get('lineup', [])))
        incoming = t == 'Substitution' and e['substitution']['replacement']['id'] == pid
        returning = t == 'Player On' and actor == pid
        exiting = actor == pid and (t in ('Player Off', 'Substitution') or card(e) in ('Red Card', 'Second Yellow'))
        if start or incoming or returning:
            used.append(e['id'])
            if opened is not None: issues.append('DUPLICATE_ENTRY')
            elif permanent: issues.append('ENTRY_AFTER_PERMANENT_EXIT')
            else: opened = point; ever = True
        if exiting:
            used.append(e['id'])
            if opened is None:
                # Cards to unused substitutes do not establish an appearance.
                if ever or player.get('positions'): issues.append('EXIT_WHILE_INACTIVE')
            else:
                intervals.append((opened, point)); opened = None
            if t == 'Substitution' or card(e) in ('Red Card', 'Second Yellow') or e.get('player_off', {}).get('permanent') is True:
                permanent = True
    if opened is not None:
        if 2 in bounds: intervals.append((opened, (2, bounds[2][1])))
        else: issues.append('NO_FINAL_BOUNDARY')
    if not ever and player.get('positions'): issues.append('LINEUP_WITHOUT_EVENT_ENTRY')
    raw_intervals = []; lineup_event_ids = []; position_intervals = []
    for pos in player.get('positions', []):
        endpoints = []
        for side in ('from', 'to'):
            reason = pos.get('start_reason' if side == 'from' else 'end_reason', '')
            if side == 'to' and reason == 'Final Whistle':
                point = (2, bounds[2][1]) if 2 in bounds else None
            else:
                raw = pos.get(side); period = pos.get(side+'_period')
                candidates = []
                if raw is not None and period in (1, 2):
                    m, s = map(int, raw.split(':'))
                    for e in events:
                        if e['period'] != period or (e['minute'], e['second']) != (m, s) or e['team']['id'] != tid: continue
                        t = typ(e); actor = e.get('player', {}).get('id')
                        ok = False
                        if reason in ('Starting XI', 'Tactical Shift') and t == reason:
                            ok = any(x['player']['id'] == pid and (side == 'to' or x['position']['id'] == pos.get('position_id')) for x in e.get('tactics', {}).get('lineup', []))
                        elif reason.startswith('Substitution - ') and t == 'Substitution':
                            ok = (e['substitution']['replacement']['id'] if side == 'from' else actor) == pid
                        elif reason.startswith('Player On') and t == 'Player On': ok = actor == pid
                        elif reason.startswith('Player Off') and t == 'Player Off': ok = actor == pid
                        elif ('Red Card' in reason or 'Second Yellow' in reason) and card(e) in ('Red Card','Second Yellow'): ok = actor == pid
                        if ok: candidates.append(e)
                clocks = {clock(e) for e in candidates}
                point = next(iter(clocks)) if len(clocks) == 1 else None
                used += [e['id'] for e in candidates]
                lineup_event_ids += [e['id'] for e in candidates]
            if point is None: issues.append('UNRESOLVED_LINEUP_ENDPOINT:'+reason)
            endpoints.append(point)
        if all(x is not None for x in endpoints):
            raw_intervals.append(tuple(endpoints))
            position_intervals.append((*endpoints, pos.get('position')))
    raw_intervals.sort()
    for i, (a, b) in enumerate(raw_intervals):
        if elapsed(a, b, bounds) is None: issues.append('INVALID_LINEUP_DURATION')
        if i and a < raw_intervals[i-1][1] and a < b: issues.append('OVERLAPPING_LINEUP_INTERVALS')
    event_seconds = [elapsed(a,b,bounds) for a,b in intervals]
    raw_seconds = [elapsed(a,b,bounds) for a,b in raw_intervals]
    total = sum(event_seconds, F(0)) if event_seconds and None not in event_seconds else None
    lineup_total = sum(raw_seconds, F(0)) if raw_seconds and None not in raw_seconds else None
    if total is not None and lineup_total is not None and total != lineup_total:
        issues.append('EVENT_LINEUP_DURATION_CONFLICT')
    if total is not None and total <= 0: issues.append('NONPOSITIVE_DURATION')
    return dict(seconds=total, lineup_seconds=lineup_total, intervals=intervals,
        issues=sorted(set(issues)), event_ids=sorted(set(used)), active=ever,
        lineup_intervals=raw_intervals, lineup_event_ids=sorted(set(lineup_event_ids)),
        lineup_position_intervals=position_intervals)


def score(value, minutes, known_minutes, limited, pool):
    if value is None or not limited and minutes < 900: return None, None
    x = float(value); z = (x-pool['mean'])/pool['sample_sd']
    result = min(99., max(1., 65.+10.*z))
    xs = [rational(m['exact_value']) for m in pool['members']]
    lo = sum(v < value for v in xs); eq = sum(v == value for v in xs)
    pct = 100*((lo+1+lo+eq)/2 if eq else lo)/len(xs)
    return result, pct


def overall(values):
    if any(v is None for v in values): return None
    # Preserve exact binary-input arithmetic before final float conversion.
    return float(sum((F(v)*F(w,100) for v,w in zip(sorted(values, reverse=True), (30,25,20,15,10))), F(0)))


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        for r in rows:
            w.writerow({k:json.dumps(v,ensure_ascii=False,default=str) if isinstance(v,(list,dict,tuple)) else v for k,v in r.items()})
