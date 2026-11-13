"""Explicit candidate reconciliation of a verified dismissal with stale lineup endpoints.

This opt-in review never changes the default adapter, original documents, frozen
measurements, ratings or ranking eligibility. Raw assertions and the original
conflict remain available beside the proposed supported interval.
"""
from dataclasses import dataclass, replace
from fractions import Fraction

from src.participation_intervals import Clock, ParticipationResult, Stint, VALID, validate_participation
from src.statsbomb_participation import SourceDocument, _check_original_transitions, _timestamp


@dataclass(frozen=True)
class DismissalReview:
    match_id: int
    player_id: int
    original: ParticipationResult
    candidate: ParticipationResult | None
    observations: tuple[Stint, ...]
    dismissal_reference: str | None
    stale_snapshot_references: tuple
    reasons: tuple
    publication_authorized: bool = False


def reconcile_dismissal(adapted, events_document, player_id):
    """Propose exact pre-dismissal exposure, retaining the original source conflict.

    Precedence is explicit: an active player's unique Red Card/Second Yellow
    event ends participation. Later passive tactical roster snapshots are retained
    as stale assertions, but actual later player activity or re-entry blocks proof.
    """
    if not isinstance(events_document, SourceDocument) or events_document.provenance not in adapted.provenance:
        raise ValueError('events must be the same byte-bound document used by the adapter')
    pairs = [(p, r) for p, r in zip(adapted.players, adapted.validate()) if p.context.player_id == player_id]
    if len(pairs) != 1:
        raise ValueError('one exact roster player required')
    player, original = pairs[0]

    def withheld(reason, reference=None):
        return DismissalReview(adapted.match_id, player_id, original, None,
                              player.observations, reference, (), (reason,))

    if not player.observations or original.status == VALID:
        return withheld('NO_UNRESOLVED_ACTIVE_APPEARANCE')
    if {issue.code for issue in original.issues} - {'original_transition_not_represented', 'participation_after_permanent_exit'}:
        return withheld('UNRELATED_OR_INCOMPLETE_SOURCE_EVIDENCE')
    events = events_document.records()
    team = [e for e in events if e['team']['id'] == player.team_id]
    actor = lambda e: e.get('player', {}).get('id') == player_id
    recipient = lambda e: e.get('pass', {}).get('recipient', {}).get('id') == player_id
    members = lambda e: [p for p in e.get('tactics', {}).get('lineup', []) if p['player']['id'] == player_id]
    card = lambda e: (e.get('foul_committed', {}).get('card', {}).get('name')
                      or e.get('bad_behaviour', {}).get('card', {}).get('name'))
    point = lambda e: (e['period'], _timestamp(e['timestamp']))
    ref = lambda e: events_document.reference + '#/event/' + e['id']
    dismissals = [e for e in team if actor(e) and e['type']['name'] in ('Foul Committed', 'Bad Behaviour')
                  and card(e) in ('Red Card', 'Second Yellow')]
    if len(dismissals) != 1:
        return withheld('UNIQUE_DISMISSAL_REQUIRED')
    terminal = dismissals[0]; end = point(terminal); terminal_ref = ref(terminal)
    related = [e for e in team if actor(e) or recipient(e) or members(e)
               or e['type']['name'] == 'Substitution' and e['substitution']['replacement']['id'] == player_id
               or e['type']['name'] in ('Half Start', 'Half End')]
    if (any(type(e.get('index')) is not int or e['index'] <= 0 for e in related)
            or len({e['index'] for e in related}) != len(related)):
        return withheld('UNIQUE_SOURCE_INDICES_REQUIRED', terminal_ref)
    ordered = sorted(related, key=lambda e: e['index'])
    if [point(e) for e in ordered] != sorted(point(e) for e in ordered):
        return withheld('SOURCE_CLOCK_INDEX_DISAGREEMENT', terminal_ref)
    if any((actor(e) or recipient(e)) and e is not terminal
           and (point(e) > end or point(e) == end and e['index'] > terminal['index']) for e in related):
        return withheld('PLAYER_ACTIVITY_AFTER_DISMISSAL', terminal_ref)

    # First prove the unmodified lineup geometry; only its terminal overrun may change.
    core = validate_participation(player.context, player.observations,
                                 clock_policy=adapted.policy, period_boundaries=adapted.boundaries)
    if core.status != VALID:
        return withheld('LINEUP_GEOMETRY_NOT_INDEPENDENTLY_VALID', terminal_ref)
    candidate = []; clipped = 0
    for stint in player.observations:
        start = (stint.start.period, stint.start.seconds)
        stop = (stint.end.period, stint.end.seconds)
        if start >= end:
            if stint.entry_kind != 'position_change':
                return withheld('POST_DISMISSAL_REENTRY', terminal_ref)
            continue
        if stop > end:
            candidate.append(replace(stint, end=Clock(*end, (terminal_ref,)), exit_kind='dismissal'))
            clipped += 1
        else:
            candidate.append(stint)
    if clipped != 1:
        return withheld('DISMISSAL_MUST_CUT_ONE_ACTIVE_INTERVAL', terminal_ref)
    if _check_original_transitions(player.team_id, player_id, candidate, events, ref):
        return withheld('OTHER_SOURCE_TRANSITION_CONFLICT', terminal_ref)
    proposed = validate_participation(player.context, tuple(candidate), clock_policy=adapted.policy,
                                      period_boundaries=adapted.boundaries)
    if proposed.status != VALID or proposed.elapsed_seconds is None or proposed.elapsed_seconds <= 0:
        return withheld('INVALID_PROPOSED_GEOMETRY', terminal_ref)

    # Independently walk original entry/off/on/dismissal events, without lineup endpoints.
    state = 'UNUSED'; opened = None; intervals = []; transition_clocks = set()
    for e in ordered:
        t = point(e); typ = e['type']['name']
        if t > end or t == end and e['index'] > terminal['index']:
            continue
        entry = typ == 'Starting XI' and bool(members(e)) or typ == 'Substitution' and e.get('substitution', {}).get('replacement', {}).get('id') == player_id
        is_actor = actor(e)
        transition = entry or is_actor and typ in ('Player Off', 'Player On', 'Substitution') or e is terminal
        if transition:
            if t in transition_clocks:
                return withheld('AMBIGUOUS_EQUAL_CLOCK_TRANSITIONS', terminal_ref)
            transition_clocks.add(t)
            if entry or typ == 'Player On':
                if state != ('UNUSED' if entry else 'TEMPORARILY_OFF'):
                    return withheld('INCONSISTENT_SOURCE_ENTRY', terminal_ref)
                state = 'ACTIVE'; opened = t
            else:
                if state != 'ACTIVE':
                    return withheld('DISMISSAL_OR_EXIT_WHILE_INACTIVE', terminal_ref)
                intervals.append((opened, t)); opened = None
                state = 'TEMPORARILY_OFF' if typ == 'Player Off' and not e.get('player_off', {}).get('permanent') else 'TERMINAL'
        elif (is_actor or recipient(e)) and state != 'ACTIVE':
            return withheld('PLAYER_ACTIVITY_OUTSIDE_ACTIVE_INTERVAL', terminal_ref)
        if typ in ('Starting XI', 'Tactical Shift') and members(e):
            active = [s for s in candidate if (s.start.period, s.start.seconds) <= t < (s.end.period, s.end.seconds)]
            if state != 'ACTIVE' or len(active) != 1 or len(members(e)) != 1 or active[0].position != members(e)[0]['position']['name']:
                return withheld('PRE_DISMISSAL_POSITION_CONFLICT', terminal_ref)
    if state != 'TERMINAL' or not intervals or intervals[-1][1] != end:
        return withheld('INDEPENDENT_DISMISSAL_WALK_FAILED', terminal_ref)
    bounds = {b.period: (b.start_seconds, b.end_seconds) for b in adapted.boundaries}

    def union(rows):
        parts = []
        for start, stop in rows:
            for period in adapted.policy.period_order:
                if start[0] <= period <= stop[0]:
                    lo = start[1] if period == start[0] else bounds[period][0]
                    hi = stop[1] if period == stop[0] else bounds[period][1]
                    if lo < hi:
                        parts.append((period, Fraction(lo), Fraction(hi)))
        merged = []
        for period, lo, hi in sorted(parts):
            if merged and merged[-1][0] == period and merged[-1][2] == lo:
                merged[-1] = (period, merged[-1][1], hi)
            else:
                merged.append((period, lo, hi))
        return merged

    pieces = union(intervals)
    if pieces != union([((s.start.period, s.start.seconds), (s.end.period, s.end.seconds)) for s in candidate]):
        return withheld('INDEPENDENT_INTERVAL_UNION_DISAGREEMENT', terminal_ref)
    if sum((hi - lo for _, lo, hi in pieces), Fraction()) != proposed.elapsed_seconds:
        return withheld('INDEPENDENT_DURATION_DISAGREEMENT', terminal_ref)
    stale = tuple(sorted(ref(e) for e in related if e['type']['name'] == 'Tactical Shift' and members(e)
                         and (point(e) > end or point(e) == end and e['index'] > terminal['index'])))
    return DismissalReview(adapted.match_id, player_id, original, proposed, tuple(candidate), terminal_ref, stale, ())
