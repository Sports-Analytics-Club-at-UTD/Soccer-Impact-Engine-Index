"""Replay byte-bound source documents into auditable supported observations."""
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import unicodedata

from scripts.decoder_fix_independent import clock, selected, card, typ
from src.dismissal_reconciliation import reconcile_dismissal
from src.participation_intervals import VALID
from src.statsbomb_participation import SourceDocument, adapt_match
from src.source_reconstruction import flatten_events, measure_events
from src.supported_sample_ratings import ATTRIBUTES, pair

DOCUMENT_CACHE = {}
ALIASES = {3054: {'Fernando Luiz Rosa', 'Fernando Luiz Roza'}}


def normalized(name):
    return ''.join(c for c in unicodedata.normalize('NFKD', name).casefold() if c.isalnum())


def identity_agrees(pid, canonical, observed):
    return normalized(canonical) == normalized(observed) or canonical in ALIASES.get(pid, set()) and observed in ALIASES[pid]


def within(event, intervals, boundaries):
    point = clock(event)
    bound = next((b for b in boundaries if b.period == point[0]), None)
    if bound is None or bound.start_seconds is None or bound.end_seconds is None:
        return False
    if not Fraction(bound.start_seconds) <= point[1] <= Fraction(bound.end_seconds):
        return False
    return any((s.start.period, s.start.seconds) <= point <= (s.end.period, s.end.seconds) for s in intervals)


def pressure_chronology(pid, tid, events, off_field_ids=()):
    """Verify action membership without substituting video length for elapsed time.

    Any incompatible re-entry or actual activity after a permanent exit withholds
    the whole fixture ratio, including its successes and failures.
    """
    relevant = [e for e in events if e['team']['id'] == tid and (
        e.get('player', {}).get('id') == pid or
        e.get('pass', {}).get('recipient', {}).get('id') == pid or
        typ(e) == 'Starting XI' and any(p['player']['id'] == pid for p in e.get('tactics', {}).get('lineup', [])) or
        typ(e) == 'Substitution' and e['substitution']['replacement']['id'] == pid)]
    indices = [e.get('index') for e in relevant]
    if any(type(i) is not int or i <= 0 for i in indices) or len(indices) != len(set(indices)):
        return ['UNRELIABLE_SOURCE_ORDER']
    ordered = sorted(relevant, key=lambda e:e['index'])
    # Receipt/other action clocks can be miscoded without changing whether a
    # pressure attempt occurred during an evidenced active stint. Only pressure
    # actions and entry/exit clocks establish the ratio's clock-order proof.
    timed = [e for e in ordered if 'press_attempts' in selected(e) or typ(e) in
        ('Starting XI','Substitution','Player On','Player Off') or card(e) in ('Red Card','Second Yellow')]
    if [clock(e) for e in timed] != sorted(clock(e) for e in timed):
        return ['SOURCE_CLOCK_INDEX_DISAGREEMENT']
    state = 'UNUSED'; reasons = set()
    for e in ordered:
        t = typ(e); actor = e.get('player', {}).get('id') == pid
        entry = t == 'Starting XI' or t == 'Substitution' and e['substitution']['replacement']['id'] == pid
        if entry:
            if state != 'UNUSED': reasons.add('CONFLICTING_ENTRY')
            state = 'ACTIVE' if state == 'UNUSED' else 'CONFLICT'
        elif actor and t == 'Player On':
            if state != 'TEMPORARILY_OFF': reasons.add('CONFLICTING_RETURN')
            state = 'ACTIVE' if state == 'TEMPORARILY_OFF' else 'CONFLICT'
        elif actor and (t in ('Player Off', 'Substitution') or card(e) in ('Red Card', 'Second Yellow')):
            if e['id'] in off_field_ids:
                continue
            if state != 'ACTIVE': reasons.add('EXIT_WHILE_INACTIVE')
            state = 'TEMPORARILY_OFF' if t == 'Player Off' and not e.get('player_off', {}).get('permanent') else 'TERMINAL'
        elif t != 'Bad Behaviour' and state != 'ACTIVE':
            reasons.add('ACTIVITY_OUTSIDE_SUPPORTED_STATE')
    return sorted(reasons)


def replay(task):
    root, mid, binding, identities = task
    root = Path(root).resolve()
    receipts = {}

    def bound_file(path, expected):
        path = Path(path)
        path = path if path.is_absolute() else root/path
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ValueError('source outside selected research checkout')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('source fingerprint changed: ' + str(path))
        receipts[str(path)] = expected
        return raw

    report = json.loads(bound_file(binding['path'], binding['sha256']))

    def document(binding, cache=False):
        if cache and binding['sha256'] in DOCUMENT_CACHE:
            doc = DOCUMENT_CACHE[binding['sha256']]
            path = Path(binding['path']); path = path if path.is_absolute() else root/path
            receipts[str(path.resolve())] = binding['sha256']
            return doc
        raw = bound_file(binding['path'], binding['sha256'])
        doc = SourceDocument(raw, binding['source_reference'], binding['provider_revision'])
        if cache: DOCUMENT_CACHE[binding['sha256']] = doc
        return doc

    fixtures = document(report['fixture_document'], True)
    lineups = document(report['artifacts']['lineups']); source = document(report['artifacts']['events'])
    fixture = next(f for f in fixtures.records() if f['match_id'] == mid)
    adapted = adapt_match(mid, fixtures, lineups, source, clock_document_reference=report['clock_policy']['evidence_refs'][0])
    events = source.records(); by_id = {e['id']:e for e in events}
    if len(by_id) != len(events): raise ValueError('duplicate original event UUID')
    rosters = {(t['team_id'], p['player_id']):p for t in lineups.records() for p in t['lineup']}
    raw_sets = defaultdict(lambda:defaultdict(set))
    for e in events:
        if not e.get('player'): continue
        key = e['team']['id'], e['player']['id']
        if key not in rosters: raise ValueError('actor lacks exact source roster ID')
        for a in selected(e): raw_sets[key][a].add(e['id'])
    # A separate existing implementation must agree on each selected UUID.
    roster_rows = [dict(team_id=t, player_id=p, player_name_raw=r['player_name']) for (t,p),r in rosters.items()]
    helper, missing, _ = measure_events(flatten_events(events, fixture, roster_rows))
    helper_sets = defaultdict(lambda:defaultdict(set))
    for a in ATTRIBUTES:
        names = ('pressured_pass_completed','pressured_dribble_completed') if a == 'press_resistance' else ('progressive_passes',) if a == 'progressive_passing' else (a,)
        for name in names:
            for uid in helper[name]:
                e=by_id[uid]; helper_sets[e['team']['id'], e['player']['id']][a].add(uid)
    missing_by_actor = defaultdict(list)
    for uid in missing:
        e = by_id[uid]
        if e.get('player'): missing_by_actor[e['team']['id'], e['player']['id']].append(uid)
    rows = []; benches = []; seen = set()
    for actor, validation in zip(adapted.players, adapted.validate()):
        pid, tid = actor.context.player_id, actor.team_id
        if pid not in identities: continue
        if pid in seen: raise ValueError('same player appears for both teams')
        seen.add(pid)
        active = bool(actor.observations or actor.source_checks)
        if not active:
            benches.append(dict(player_id=pid, match_id=mid, reason='NO_SUPPORTED_APPEARANCE_ASSERTION'))
            continue
        intervals = actor.observations
        seconds = validation.elapsed_seconds if validation.status == VALID else None
        dismissal = None
        if seconds is None:
            review = reconcile_dismissal(adapted, source, pid)
            dismissal = dict(accepted=review.candidate is not None, reasons=list(review.reasons),
                dismissal_reference=review.dismissal_reference, stale_snapshots=list(review.stale_snapshot_references))
            if review.candidate is not None:
                seconds = review.candidate.elapsed_seconds; intervals = review.observations
        names = {rosters[tid,pid]['player_name']} | {e['player']['name'] for e in events if e['team']['id']==tid and e.get('player',{}).get('id')==pid}
        identity_reasons = [] if all(identity_agrees(pid, identities[pid], name) for name in names) else ['UNRESOLVED_IDENTITY_NAME_CONFLICT']
        off_field = {d.event_ref.rsplit('/',1)[-1] for d in actor.off_field_discipline}
        chronology = pressure_chronology(pid, tid, events, off_field)
        metrics = {}
        for a in ATTRIBUTES:
            numerator = sorted(raw_sets[tid,pid][a])
            if set(numerator) != helper_sets[tid,pid][a]:
                raise ValueError('independent metric selection disagrees: ' + str((mid,pid,a)))
            denominator = sorted(raw_sets[tid,pid]['press_attempts']) if a == 'press_resistance' else None
            reasons = list(identity_reasons)
            if mid == 3879594: reasons.append('PENDING_DELIVERED_FIXTURE_SCOPE')
            if a == 'press_resistance':
                reasons.extend(chronology)
                if seconds is not None and any(not within(by_id[uid], intervals, adapted.boundaries) for uid in denominator):
                    reasons.append('PRESSURE_ACTION_OUTSIDE_EXPOSURE')
            else:
                if seconds is None: reasons.append('UNRESOLVED_PARTICIPATION')
                elif any(not within(by_id[uid], intervals, adapted.boundaries) for uid in numerator):
                    reasons.append('NUMERATOR_DENOMINATOR_MISMATCH')
                if a == 'progressive_passing':
                    # Missing geometry and eligible pass scope outside exposure
                    # withhold the fixture, including zero selected passes.
                    if missing_by_actor[tid,pid]: reasons.append('MISSING_PASS_GEOMETRY')
                    if seconds is not None and any(e['team']['id']==tid and e.get('player',{}).get('id')==pid
                        and typ(e)=='Pass' and e.get('pass',{}).get('type',{}).get('name') in (None,'Recovery','Interception')
                        and e.get('pass',{}).get('outcome',{}).get('name') not in ('Unknown','Injury Clearance')
                        and not within(e, intervals, adapted.boundaries) for e in events):
                        reasons.append('PASS_SCOPE_OUTSIDE_EXPOSURE')
            metrics[a] = dict(included=not reasons, reasons=sorted(set(reasons)), numerator_ids=numerator, denominator_ids=denominator)
        if identity_reasons: seconds = None
        rows.append(dict(player_id=pid, match_id=mid, team_id=tid, team=next(t['team_name'] for t in lineups.records() if t['team_id']==tid),
            competition=adapted.competition_name, season=adapted.season_name,
            seconds=pair(seconds), original_issues=[i.code for i in validation.issues], dismissal=dismissal,
            identity_names=sorted(names), identity_reasons=identity_reasons, chronology_reasons=chronology,
            source_sha256=source.fingerprint, source=source.reference, metrics=metrics))
    return dict(match_id=mid, appearances=rows, nonappearances=benches, event_ids=list(by_id), receipts=receipts)
