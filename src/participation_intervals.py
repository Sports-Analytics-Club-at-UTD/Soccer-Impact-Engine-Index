"""Pure participation structure checks; no source authentication, I/O or scoring.

Transition kinds below are internal adapter categories, not provider event names.
Seconds are exact integers, Decimal or Fraction values; no clocks are inferred.
"""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from numbers import Integral

import pandas as pd

from src.identity import _ids

VALID = "STRUCTURALLY_VALID"
INCOMPLETE = "INCOMPLETE_EVIDENCE"
CONFLICT = "CONFLICTING_EVIDENCE"
CONVENTIONS = ("period_local", "period_offset")
ENTRIES = ("starter", "substitution", "return", "position_change", "unknown")
EXITS = ("substitution", "dismissal", "temporary_exit", "match_end", "position_change", "unknown")


class ParticipationError(ValueError):
    """Malformed input declarations, distinct from retained evidence problems."""


@dataclass(frozen=True)
class Context:
    match_id: int
    player_id: int
    team_key: str


@dataclass(frozen=True)
class Clock:
    period: int
    seconds: int | Decimal | Fraction | None
    evidence_refs: tuple = ()


@dataclass(frozen=True)
class Stint:
    observation_id: str
    context: Context
    position: str | None
    start: Clock | None
    end: Clock | None
    entry_kind: str
    exit_kind: str
    evidence_refs: tuple = ()
    provenance_refs: tuple = ()


@dataclass(frozen=True)
class ClockPolicy:
    match_id: int
    convention: str | None
    period_order: tuple
    evidence_refs: tuple = ()
    provenance_refs: tuple = ()


@dataclass(frozen=True)
class PeriodBoundary:
    match_id: int
    period: int
    start_seconds: int | Decimal | Fraction | None
    end_seconds: int | Decimal | Fraction | None
    evidence_refs: tuple = ()
    provenance_refs: tuple = ()


@dataclass(frozen=True, order=True)
class Issue:
    status: str
    code: str
    observation_ids: tuple = ()


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    observation_ids: tuple = ()


@dataclass(frozen=True)
class IntervalResult:
    observation_id: str
    elapsed_seconds: Fraction | None
    boundary_periods: tuple
    # Candidate geometry only. Aggregate acceptance also requires sequence checks.


@dataclass(frozen=True)
class Gap:
    preceding_id: str
    following_id: str
    elapsed_seconds: Fraction | None
    supported_temporary_absence: bool


@dataclass(frozen=True)
class PositionExposure:
    position: str
    elapsed_seconds: Fraction


@dataclass(frozen=True)
class ParticipationResult:
    context: Context
    status: str
    elapsed_seconds: Fraction | None
    position_allocation: tuple | None
    intervals: tuple
    gaps: tuple
    findings: tuple
    issues: tuple
    observations: tuple
    clock_policy: ClockPolicy | None
    period_boundaries: tuple
    source_independently_verified: bool = False
    publication_authorized: bool = False


def _identifier(value, label):
    try:
        return int(_ids(pd.Series([value]), label).iloc[0])
    except ValueError as exc:
        raise ParticipationError(str(exc)) from exc


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ParticipationError(f"{label}: nonblank text required")


def _refs(value):
    if not isinstance(value, tuple):
        raise ParticipationError("evidence/provenance references must be immutable tuples")
    for ref in value:
        _text(ref, "reference")
    if len(set(value)) != len(value):
        raise ParticipationError("duplicate references")


def _seconds(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (Integral, Decimal, Fraction)):
        raise ParticipationError("seconds require exact int, Decimal, Fraction or None; no float/string coercion")
    if isinstance(value, Decimal) and not value.is_finite():
        raise ParticipationError("nonfinite seconds")
    result = Fraction(int(value)) if isinstance(value, Integral) else Fraction(value)
    if result < 0:
        raise ParticipationError("negative seconds")
    return result


def _context(value):
    if not isinstance(value, Context):
        raise ParticipationError("explicit Context required")
    _identifier(value.match_id, "match_id")
    _identifier(value.player_id, "player_id")
    _text(value.team_key, "team_key")


def _clock(value):
    if value is not None:
        if not isinstance(value, Clock):
            raise ParticipationError("Clock or None required")
        _identifier(value.period, "period")
        _seconds(value.seconds)
        _refs(value.evidence_refs)


def validate_participation(context, observations, *, clock_policy=None, period_boundaries=()):
    """Validate ONE supplied player/team/match collection, without completeness inference.

    Missing evidence is retained; contradictions quarantine the aggregate. Exact
    time is conditional arithmetic under caller-documented semantics, never a
    verified real-world measurement. No season, eligibility or rating policy.
    """
    _context(context)
    if not isinstance(observations, (list, tuple)) or not isinstance(period_boundaries, (list, tuple)):
        raise ParticipationError("explicit observation and boundary lists/tuples required")
    for obs in observations:
        if not isinstance(obs, Stint):
            raise ParticipationError("Stint observations required")
        _text(obs.observation_id, "observation_id")
    observations = tuple(sorted(observations, key=lambda obs: obs.observation_id))
    issues, findings = set(), set()

    def issue(status, code, *ids):
        issues.add(Issue(status, code, tuple(sorted(ids))))

    def finding(code, *ids):
        findings.add(Finding(code, tuple(sorted(ids))))

    usable_policy = True
    order = {}
    if clock_policy is None:
        usable_policy = False
        issue(INCOMPLETE, "unknown_period_semantics")
    else:
        if not isinstance(clock_policy, ClockPolicy) or not isinstance(clock_policy.period_order, tuple):
            raise ParticipationError("ClockPolicy with immutable explicit period order required")
        if clock_policy.convention is not None and not isinstance(clock_policy.convention, str):
            raise ParticipationError("clock convention must be text or None")
        _identifier(clock_policy.match_id, "policy.match_id")
        _refs(clock_policy.evidence_refs)
        _refs(clock_policy.provenance_refs)
        periods = [_identifier(p, "period_order") for p in clock_policy.period_order]
        if len(set(periods)) != len(periods):
            raise ParticipationError("duplicate period identifiers in clock policy")
        order = {p: i for i, p in enumerate(periods)}
        if clock_policy.match_id != context.match_id:
            issue(CONFLICT, "policy_match_mismatch")
            usable_policy = False
        if clock_policy.convention not in CONVENTIONS or not periods:
            issue(INCOMPLETE, "unknown_period_semantics")
            usable_policy = False
        if not clock_policy.evidence_refs:
            issue(INCOMPLETE, "missing_clock_policy_evidence")
            usable_policy = False
        if not clock_policy.provenance_refs:
            issue(INCOMPLETE, "missing_clock_policy_provenance")
            usable_policy = False

    boundaries, supplied_boundaries = {}, []
    for boundary in period_boundaries:
        if not isinstance(boundary, PeriodBoundary):
            raise ParticipationError("PeriodBoundary required")
        _identifier(boundary.match_id, "boundary.match_id")
        period = _identifier(boundary.period, "boundary.period")
        start, end = _seconds(boundary.start_seconds), _seconds(boundary.end_seconds)
        _refs(boundary.evidence_refs)
        _refs(boundary.provenance_refs)
        supplied_boundaries.append(boundary)
        if period in boundaries:
            raise ParticipationError("duplicate/conflicting period boundary; reconcile declarations explicitly")
        boundaries[period] = boundary
        if boundary.match_id != context.match_id:
            issue(CONFLICT, "boundary_match_mismatch")
        if start is None or end is None:
            issue(INCOMPLETE, "missing_period_boundary_clock")
        if not boundary.evidence_refs:
            issue(INCOMPLETE, "missing_period_boundary_evidence")
        if not boundary.provenance_refs:
            issue(INCOMPLETE, "missing_period_boundary_provenance")
        if order and period not in order:
            issue(CONFLICT, "boundary_period_outside_policy")
        if start is not None and end is not None and end <= start:
            issue(CONFLICT, "nonpositive_period_boundary")
        if clock_policy and clock_policy.convention == "period_local" and start not in (None, 0):
            issue(CONFLICT, "period_local_origin_not_zero")

    def supported_boundary(period):
        b = boundaries.get(period)
        return (b is not None and b.match_id == context.match_id and b.evidence_refs and b.provenance_refs
                and b.start_seconds is not None and b.end_seconds is not None
                and _seconds(b.end_seconds) > _seconds(b.start_seconds))

    def elapsed(start, end):
        """Return geometry and the periods whose boundaries were required."""
        if not usable_policy or start is None or end is None:
            return None, ()
        if start.period not in order or end.period not in order or start.seconds is None or end.seconds is None:
            return None, ()
        first, last = order[start.period], order[end.period]
        if first > last:
            return None, ()
        s, e = _seconds(start.seconds), _seconds(end.seconds)
        if first == last:
            return (e - s if e >= s else None), ()
        periods = clock_policy.period_order[first:last + 1]
        if not all(supported_boundary(p) for p in periods):
            return None, periods
        total = Fraction(0)
        for p in periods:
            b = boundaries[p]
            lo = s if p == start.period else _seconds(b.start_seconds)
            hi = e if p == end.period else _seconds(b.end_seconds)
            if not _seconds(b.start_seconds) <= lo <= hi <= _seconds(b.end_seconds):
                return None, periods
            total += hi - lo
        return total, periods

    seen_ids, seen_geometry, checked, results = set(), {}, [], []
    for obs in observations:
        if not isinstance(obs, Stint):
            raise ParticipationError("Stint observations required")
        _text(obs.observation_id, "observation_id")
        if obs.observation_id in seen_ids:
            raise ParticipationError("duplicate observation_id; no first-record selection")
        seen_ids.add(obs.observation_id)
        _context(obs.context)
        _clock(obs.start)
        _clock(obs.end)
        _refs(obs.evidence_refs)
        _refs(obs.provenance_refs)
        if obs.position is not None:
            _text(obs.position, "position")
        if obs.entry_kind not in ENTRIES or obs.exit_kind not in EXITS:
            raise ParticipationError("unsupported internal transition category")
        oid = obs.observation_id
        if obs.context != context:
            issue(CONFLICT, "identity_association_mismatch", oid)
        if not obs.evidence_refs:
            issue(INCOMPLETE, "missing_observation_evidence", oid)
        if not obs.provenance_refs:
            issue(INCOMPLETE, "missing_source_provenance", oid)
        if obs.position is None:
            issue(INCOMPLETE, "missing_position_allocation", oid)
        if obs.entry_kind == "unknown" or obs.exit_kind == "unknown":
            issue(INCOMPLETE, "unknown_transition", oid)
        for label, point in (("start", obs.start), ("end", obs.end)):
            if point is None or point.seconds is None:
                issue(INCOMPLETE, "missing_" + label + "_clock", oid)
            if point is None or not point.evidence_refs:
                issue(INCOMPLETE, "missing_" + label + "_evidence", oid)
            if point and order and point.period not in order:
                issue(CONFLICT, "observation_period_outside_policy", oid)
            if point and point.seconds is not None and supported_boundary(point.period):
                b = boundaries[point.period]
                if not _seconds(b.start_seconds) <= _seconds(point.seconds) <= _seconds(b.end_seconds):
                    issue(CONFLICT, "clock_outside_supported_period", oid)
        complete_clock = (obs.start is not None and obs.end is not None
                          and obs.start.seconds is not None and obs.end.seconds is not None
                          and obs.start.period in order and obs.end.period in order)
        if complete_clock:
            start_key = (order[obs.start.period], _seconds(obs.start.seconds))
            end_key = (order[obs.end.period], _seconds(obs.end.seconds))
            if start_key[0] > end_key[0]:
                issue(CONFLICT, "reversed_period_order", oid)
            elif start_key[0] == end_key[0] and start_key[1] > end_key[1]:
                issue(CONFLICT, "reversed_within_period_clock", oid)
            elif start_key == end_key:
                finding("same_clock_entry_exit", oid)
            if start_key <= end_key:
                geometry = (start_key, end_key)
                if geometry in seen_geometry:
                    issue(CONFLICT, "duplicate_participation", seen_geometry[geometry], oid)
                seen_geometry[geometry] = oid
                checked.append((start_key, end_key, obs))
            if obs.entry_kind == "starter":
                if start_key[0] != 0:
                    issue(CONFLICT, "starter_after_first_period", oid)
                if clock_policy.convention == "period_local" and start_key[1] != 0:
                    issue(CONFLICT, "starter_after_period_start", oid)
                if supported_boundary(obs.start.period) and start_key[1] != _seconds(boundaries[obs.start.period].start_seconds):
                    issue(CONFLICT, "starter_after_period_start", oid)
            if obs.exit_kind == "match_end":
                if end_key[0] != len(order) - 1:
                    issue(CONFLICT, "match_end_before_last_period", oid)
                if supported_boundary(obs.end.period) and end_key[1] != _seconds(boundaries[obs.end.period].end_seconds):
                    issue(CONFLICT, "match_end_clock_disagreement", oid)
        if obs.start and obs.start.seconds is not None and clock_policy and clock_policy.convention == "period_offset":
            if _seconds(obs.start.seconds) > 90 * 60:
                finding("recorded_entry_after_minute_90", oid)
        duration, used = elapsed(obs.start, obs.end)
        if complete_clock and order[obs.start.period] < order[obs.end.period] and duration is None:
            issue(INCOMPLETE, "cross_period_boundaries_unavailable", oid)
        results.append(IntervalResult(oid, duration, tuple(used)))

    if not observations:
        issue(INCOMPLETE, "no_participation_observations")
    if len(observations) > 1:
        finding("multiple_active_stints", *sorted(seen_ids))
    checked.sort(key=lambda row: (row[0], row[1], row[2].observation_id))
    gaps = []
    frontier = None
    for start_key, end_key, obs in checked:
        if frontier and start_key < frontier[1] and start_key < end_key:
            issue(CONFLICT, "overlapping_active_intervals", frontier[2].observation_id, obs.observation_id)
        if frontier is None or end_key > frontier[1]:
            frontier = (start_key, end_key, obs)
    sequence_complete = (usable_policy and len(checked) == len(observations)
                         and all(o.entry_kind != "unknown" and o.exit_kind != "unknown" for o in observations))
    if observations and not sequence_complete:
        issue(INCOMPLETE, "sequence_evidence_incomplete")
    for index, (_, _, obs) in enumerate(checked):
        # A missing/unmapped observation may be the preceding exit or return.
        # Do not invent a contradiction by ordering only the surviving subset.
        if not sequence_complete:
            continue
        previous = checked[index - 1][2] if index else None
        following = checked[index + 1][2] if index + 1 < len(checked) else None
        if obs.entry_kind in ("return", "position_change"):
            required = "temporary_exit" if obs.entry_kind == "return" else "position_change"
            if previous is None or previous.exit_kind != required:
                issue(CONFLICT, "unsupported_" + obs.entry_kind, obs.observation_id)
        elif previous is not None:
            issue(CONFLICT, "new_entry_after_prior_participation", previous.observation_id, obs.observation_id)
        if obs.exit_kind in ("temporary_exit", "position_change"):
            required = "return" if obs.exit_kind == "temporary_exit" else "position_change"
            if following is None or following.entry_kind != required:
                issue(INCOMPLETE, "unclosed_" + obs.exit_kind, obs.observation_id)
        if previous:
            gap_seconds, _ = elapsed(previous.end, obs.start)
            supported_absence = bool(usable_policy and previous.exit_kind == "temporary_exit" and obs.entry_kind == "return"
                and previous.end.evidence_refs and obs.start.evidence_refs
                and previous.evidence_refs and obs.evidence_refs and previous.provenance_refs and obs.provenance_refs)
            if (order[previous.end.period], _seconds(previous.end.seconds)) <= (order[obs.start.period], _seconds(obs.start.seconds)):
                gaps.append(Gap(previous.observation_id, obs.observation_id, gap_seconds, supported_absence))
                if gap_seconds is None or gap_seconds > 0:
                    finding("gap_between_active_intervals", previous.observation_id, obs.observation_id)
                if obs.entry_kind == "position_change" and (gap_seconds is None or gap_seconds != 0):
                    issue(INCOMPLETE if gap_seconds is None else CONFLICT, "position_change_not_contiguous", previous.observation_id, obs.observation_id)
                if supported_absence:
                    finding("temporary_exit_and_reentry", previous.observation_id, obs.observation_id)
                if obs.entry_kind == "position_change":
                    finding("position_change", previous.observation_id, obs.observation_id)

    status = CONFLICT if any(i.status == CONFLICT for i in issues) else INCOMPLETE if issues else VALID
    duration_map = {r.observation_id: r.elapsed_seconds for r in results}
    total, allocation = None, None
    if status == VALID:
        # Every accepted observation is bounded and present in the checked sequence.
        total = sum((r.elapsed_seconds for r in results), Fraction(0))
        positions = {}
        for obs in observations:
            positions[obs.position] = positions.get(obs.position, Fraction(0)) + duration_map[obs.observation_id]
        allocation = tuple(PositionExposure(p, value) for p, value in sorted(positions.items()))
    return ParticipationResult(context, status, total, allocation,
        tuple(sorted(results, key=lambda r: r.observation_id)), tuple(gaps), tuple(sorted(findings)), tuple(sorted(issues)),
        tuple(sorted(observations, key=lambda o: o.observation_id)), clock_policy,
        tuple(sorted(supplied_boundaries, key=lambda b: b.period)))
