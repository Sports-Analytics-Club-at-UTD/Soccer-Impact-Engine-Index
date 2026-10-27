"""Bounded StatsBomb open-data adapter for D3J; no I/O or trust promotion.

Observed lineup stints are corroborated with original transition events. Period
local timestamps retain milliseconds. Lineup MM:SS is only a transition lookup,
never an assumed final whistle. Unsupported/ambiguous transitions stay unknown.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
import hashlib
import json
import re

from src.participation_intervals import (Clock, ClockPolicy, Context, PeriodBoundary,
                                         Stint, Issue, CONFLICT, INCOMPLETE,
                                         validate_participation)


class SourceSchemaError(ValueError):
    """Source schema/identity cannot safely be associated."""


def _id(value):
    if type(value) is not int or not 0 < value < 2**63:
        raise SourceSchemaError("positive exact signed-int64 source ID required")
    return value


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise SourceSchemaError("nonblank source text required")
    return value


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise SourceSchemaError("duplicate source JSON key")
        out[key] = value
    return out


@dataclass(frozen=True)
class SourceDocument:
    raw: bytes
    reference: str
    revision: str

    @property
    def fingerprint(self):
        return hashlib.sha256(self.raw).hexdigest()

    @property
    def provenance(self):
        return f"{self.reference}@{self.revision}#sha256={self.fingerprint}"

    def records(self):
        if not isinstance(self.raw, bytes) or len(self.raw) > 20 * 1024 * 1024:
            raise SourceSchemaError("bounded original source bytes required")
        _text(self.reference)
        _text(self.revision)
        data = json.loads(self.raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(SourceSchemaError("nonfinite JSON")))
        if not isinstance(data, list) or any(not isinstance(r, dict) for r in data):
            raise SourceSchemaError("original JSON record array required")
        return data


@dataclass(frozen=True)
class SourceCheck:
    status: str
    code: str
    evidence_refs: tuple
    observation_ids: tuple = ()


@dataclass(frozen=True)
class AdaptedPlayer:
    context: Context
    player_name: str
    team_id: int
    observations: tuple
    raw_positions: tuple
    source_checks: tuple = ()


@dataclass(frozen=True)
class AdaptedMatch:
    match_id: int
    competition_name: str
    season_name: str
    players: tuple
    policy: ClockPolicy
    boundaries: tuple
    warnings: tuple
    provenance: tuple

    def validate(self):
        results = []
        for player in self.players:
            result = validate_participation(player.context, player.observations,
                       clock_policy=self.policy, period_boundaries=self.boundaries)
            if player.source_checks:
                issues = set(result.issues) | {Issue(c.status, c.code, c.observation_ids)
                                              for c in player.source_checks}
                status = CONFLICT if any(i.status == CONFLICT for i in issues) else INCOMPLETE
                result = replace(result, status=status, elapsed_seconds=None,
                                 position_allocation=None, issues=tuple(sorted(issues)))
            results.append(result)
        return tuple(results)


def _timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?", value):
        raise SourceSchemaError("malformed period-local timestamp")
    h, m, s = value.split(":")
    if int(m) >= 60 or Decimal(s) >= 60:
        raise SourceSchemaError("malformed timestamp components")
    return Decimal(h) * 3600 + Decimal(m) * 60 + Decimal(s)


def _lineup_clock(value):
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{2,3}:[0-5]\d", value):
        raise SourceSchemaError("malformed lineup MM:SS")
    m, s = value.split(":")
    return int(m), int(s)


def _adapt_match(match_id, matches, lineups, events, *, clock_document_reference):
    """Adapt ONE roster; zero-position bench players remain nonparticipants.

    Caller supplies byte-bound original documents and reviewed clock reference.
    This is identified provider evidence, not a D1 verified trust attestation.
    Only regulation periods 1/2 are currently supported. Other cases reject.
    """
    _id(match_id)
    _text(clock_document_reference)
    ms, ls, es = matches.records(), lineups.records(), events.records()
    selected = [r for r in ms if r.get("match_id") == match_id]
    if len(selected) != 1:
        raise SourceSchemaError("match must occur exactly once in provider inventory")
    match = selected[0]
    try:
        _id(match["match_id"])
        competition = _text(match["competition"]["competition_name"])
        season = _text(match["season"]["season_name"])
        expected = {_id(match[k][k + "_id"]): _text(match[k][k + "_name"]) for k in ("home_team", "away_team")}
        if len(expected) != 2 or len(ls) != 2:
            raise SourceSchemaError("exactly two distinct source teams required")
        roster = {}
        for team in ls:
            tid = _id(team["team_id"])
            if tid in roster or expected.get(tid) != team["team_name"]:
                raise SourceSchemaError("fixture/lineup team identity conflict")
            roster[tid] = {}
            for player in team["lineup"]:
                pid = _id(player["player_id"])
                if pid in roster[tid] or any(pid in r for r in roster.values()):
                    raise SourceSchemaError("duplicate/cross-team player identity")
                _text(player["player_name"])
                if not isinstance(player["positions"], list):
                    raise SourceSchemaError("explicit original positions array required")
                roster[tid][pid] = player
        if set(roster) != set(expected):
            raise SourceSchemaError("source teams disagree")
        seen, indices = set(), set()
        indexed = ["index" in e for e in es]
        if any(indexed) and not all(indexed):
            raise SourceSchemaError("partially missing original event index")
        for e in es:
            eid = _text(e["id"])
            if eid in seen:
                raise SourceSchemaError("duplicate original event ID")
            seen.add(eid)
            if "index" in e:
                index = _id(e["index"])
                if index in indices:
                    raise SourceSchemaError("duplicate original event index")
                indices.add(index)
            if "match_id" in e and _id(e["match_id"]) != match_id:
                raise SourceSchemaError("event match identity conflict")
            if type(e["period"]) is not int or e["period"] not in (1, 2):
                raise SourceSchemaError("unsupported period; no extra-time/shootout inference")
            _timestamp(e["timestamp"])
            if type(e["minute"]) is not int or type(e["second"]) is not int or not 0 <= e["second"] < 60:
                raise SourceSchemaError("malformed original event clock")
            offset = 0 if e["period"] == 1 else 45
            if int(_timestamp(e["timestamp"])) != (e["minute"] - offset) * 60 + e["second"]:
                raise SourceSchemaError("event timestamp/offset clock disagreement")
            _text(e["type"]["name"])
            tid = _id(e["team"]["id"])
            if expected.get(tid) != e["team"]["name"]:
                raise SourceSchemaError("event/fixture team identity conflict")
            actors = ([e["player"]] if "player" in e else [])
            if e["type"]["name"] == "Substitution":
                actors += [e["substitution"]["replacement"]]
            actors += [x["player"] for x in e.get("tactics", {}).get("lineup", [])]
            for tactical_player in e.get("tactics", {}).get("lineup", []):
                _id(tactical_player["position"]["id"])
                _text(tactical_player["position"]["name"])
            for actor in actors:
                pid = _id(actor["id"])
                if pid not in roster[tid] or actor["name"] != roster[tid][pid]["player_name"]:
                    raise SourceSchemaError("event/roster player identity conflict")
    except (KeyError, TypeError) as exc:
        raise SourceSchemaError(f"missing/malformed source field: {exc}") from exc

    provenance = (matches.provenance, lineups.provenance, events.provenance)
    warnings, boundaries = [], []

    def ref(e):
        return events.reference + "#/event/" + e["id"]

    def boundary(period, kind):
        candidates = [e for e in es if e["period"] == period and e["type"]["name"] == kind]
        attribute = "half_start" if kind == "Half Start" else "half_end"
        # Provider documents late video start, early video end and suspension.
        # No flagged boundary is usable without a separately reviewed mapping.
        # Withhold unknown boundary attributes too; never infer a real whistle.
        if any(e.get(attribute) or attribute in e and not isinstance(e[attribute],dict) for e in candidates):
            warnings.append(f"{kind}: period {period}: flagged/unsupported boundary attributes")
            return None, ()
        values = {_timestamp(e["timestamp"]) for e in candidates}
        # Two team records are normal. Never choose the latest of disagreements.
        if len(values) != 1 or {e["team"]["id"] for e in candidates} != set(expected):
            warnings.append(f"{kind}: period {period}: missing or disagreeing team whistle evidence")
            return None, ()
        value = next(iter(values))
        if kind == "Half Start" and value != 0:
            warnings.append(f"Half Start: period {period}: unsupported nonzero origin")
            return None, ()
        return value, tuple(sorted(ref(e) for e in candidates))

    for period in (1, 2):
        start, sr = boundary(period, "Half Start")
        end, er = boundary(period, "Half End")
        boundaries.append(PeriodBoundary(match_id, period, start, end, sr + er, (events.provenance,)))
    policy = ClockPolicy(match_id, "period_local", (1, 2),
                         (clock_document_reference, "observed timestamp=minute-offset+second; offsets 0/45"),
                         (events.provenance,))

    def endpoint(stint, side, tid, pid, raw_ref):
        reason = stint.get("start_reason" if side == "from" else "end_reason")
        if side == "to" and reason == "Final Whistle":
            b = boundaries[-1]
            supplied_period = stint.get("to_period")
            if supplied_period is not None and (type(supplied_period) is not int or supplied_period not in (1, 2)):
                raise SourceSchemaError("malformed final-whistle period")
            supplied_clock = _lineup_clock(stint.get("to"))
            if supplied_period not in (None, 2) or (supplied_clock is not None and b.end_seconds is not None and (supplied_clock[0]-45)*60+supplied_clock[1] != int(b.end_seconds)):
                warnings.append(raw_ref + ": final-whistle lineup disagreement")
                return None, "unknown"
            if b.end_seconds is None:
                return None, "unknown"
            return Clock(2, b.end_seconds, b.evidence_refs), "match_end"
        period = stint.get(side + "_period")
        pair = _lineup_clock(stint.get(side))
        if period is not None and (type(period) is not int or period not in (1, 2)):
            raise SourceSchemaError("malformed/unsupported lineup period")
        if pair is None or period is None:
            return None, "unknown"
        mapping = {"Starting XI": ("Starting XI", "starter"),
                   "Tactical Shift": ("Tactical Shift", "position_change"),
                   "Player On": ("Player On", "return"),
                   "Player Off": ("Player Off", "temporary_exit"),
                   "Foul Committed (Red Card)": ("Foul Committed", "dismissal"),
                   "Foul Committed (Second Yellow)": ("Foul Committed", "dismissal")}
        if isinstance(reason, str) and reason.startswith("Substitution - " + ("On" if side == "from" else "Off") + " ("):
            typ, kind = "Substitution", "substitution"
        else:
            typ, kind = mapping.get(reason, (None, "unknown"))
        allowed = {"from": {"starter", "position_change", "return", "substitution"},
                   "to": {"position_change", "temporary_exit", "substitution", "dismissal"}}
        if kind not in allowed[side]:
            typ, kind = None, "unknown"
        candidates = []
        for e in es:
            if e["period"] != period or (e["minute"], e["second"]) != pair or e["team"]["id"] != tid or e["type"]["name"] != typ:
                continue
            actor = e.get("player", {}).get("id")
            if typ == "Substitution" and side == "from":
                actor = e["substitution"]["replacement"]["id"]
            if typ in ("Starting XI", "Tactical Shift"):
                positions = e.get("tactics", {}).get("lineup", [])
                actor = pid if any(x["player"]["id"] == pid and (side == "to" or (x["position"]["id"] == stint.get("position_id") and x["position"]["name"] == stint.get("position"))) for x in positions) else None
            if typ == "Foul Committed" and e.get("foul_committed", {}).get("card", {}).get("name") not in ("Red Card", "Second Yellow"):
                continue
            if typ == "Player Off" and e.get("player_off", {}).get("permanent"):
                continue
            if actor == pid:
                candidates.append(e)
        clocks = {_timestamp(e["timestamp"]) for e in candidates}
        if len(clocks) == 1:
            return Clock(period, next(iter(clocks)), tuple(sorted(ref(e) for e in candidates))), kind
        warnings.append(raw_ref + ": missing/ambiguous original transition: " + str(reason))
        # Preserve original geometry for contradiction detection, without claiming
        # transition support. Unknown category prevents an aggregate duration.
        seconds = (pair[0] - (45 if period == 2 else 0)) * 60 + pair[1]
        return Clock(period, seconds, (raw_ref,)) if seconds >= 0 else None, "unknown"

    players = []
    for tid in sorted(roster):
        for pid, player in sorted(roster[tid].items()):
            context = Context(match_id, pid, expected[tid])
            observations, raw_positions = [], []
            for i, stint in enumerate(player["positions"]):
                if not isinstance(stint, dict):
                    raise SourceSchemaError("position must be an original object")
                raw_ref = f"{lineups.reference}#/team/{tid}/player/{pid}/positions/{i}"
                start, entry = endpoint(stint, "from", tid, pid, raw_ref)
                end, exit_kind = endpoint(stint, "to", tid, pid, raw_ref)
                position = stint.get("position")
                if position is not None:
                    _text(position)
                    _id(stint.get("position_id"))
                observations.append(Stint(f"{match_id}:{tid}:{pid}:{i}", context, position,
                                         start, end, entry, exit_kind, (raw_ref,), provenance))
                raw_positions.append(json.dumps(stint, sort_keys=True, ensure_ascii=True))
            checks = _check_original_transitions(tid, pid, observations, es, ref)
            players.append(AdaptedPlayer(context, player["player_name"], tid, tuple(observations), tuple(raw_positions), checks))
    return AdaptedMatch(match_id, competition, season, tuple(players), policy,
                        tuple(boundaries), tuple(sorted(warnings)), provenance)


def _check_original_transitions(tid, pid, observations, events, reference):
    """One-way consistency checks, never replacement/repair of source stints.

    Endpoint matching alone cannot detect omitted exits or an event snapshot
    that contradicts the claimed active position. Preserve both observations.
    """
    checks = set()
    represented = {r for o in observations for point in (o.start, o.end) if point
                   for r in point.evidence_refs}

    def key(point):
        return (point.period, point.seconds) if point and point.seconds is not None else None

    for event in events:
        if event["team"]["id"] != tid:
            continue
        typ = event["type"]["name"]
        actor = event.get("player", {}).get("id")
        incoming = event.get("substitution", {}).get("replacement", {}).get("id")
        eref = reference(event)
        clock = (event["period"], _timestamp(event["timestamp"]))
        card = event.get("foul_committed", {}).get("card", {}).get("name")
        card = event.get("bad_behaviour", {}).get("card", {}).get("name", card)
        dismissed = actor == pid and card in ("Red Card", "Second Yellow")
        permanent = actor == pid and (dismissed or typ == "Substitution" or
                     typ == "Player Off" and event.get("player_off", {}).get("permanent") is True)
        required = actor == pid and typ in ("Player Off", "Player On", "Substitution")
        if typ == "Player Off" and event.get("player_off", {}).get("permanent") is True:
            required = False  # unsupported exit category remains incomplete
        required = required or typ == "Substitution" and incoming == pid or dismissed
        if required and eref not in represented:
            checks.add(SourceCheck(CONFLICT, "original_transition_not_represented", (eref,)))
        if permanent:
            later = tuple(sorted(o.observation_id for o in observations
                                 if key(o.end) is not None and key(o.end) > clock
                                 and key(o.start) is not None and key(o.start) < key(o.end)))
            if later:
                checks.add(SourceCheck(CONFLICT, "participation_after_permanent_exit", (eref,), later))
        if typ in ("Starting XI", "Tactical Shift"):
            snapshot = next((p for p in event.get("tactics", {}).get("lineup", [])
                             if p["player"]["id"] == pid), None)
            if snapshot is None:
                continue
            active = [o for o in observations if key(o.start) is not None and key(o.end) is not None
                      and key(o.start) <= clock < key(o.end)]
            if not observations and typ == "Starting XI":
                checks.add(SourceCheck(CONFLICT, "starting_actor_has_no_lineup_stints", (eref,)))
            if len(active) == 1 and active[0].position != snapshot["position"]["name"]:
                checks.add(SourceCheck(CONFLICT, "active_position_snapshot_disagreement", (eref,),
                                       (active[0].observation_id,)))
    return tuple(sorted(checks, key=lambda c: (c.status, c.code, c.evidence_refs, c.observation_ids)))


def adapt_match(match_id, matches, lineups, events, *, clock_document_reference):
    """Validate original schemas and preserve every source contradiction."""
    try:
        if any(not isinstance(d,SourceDocument) for d in (matches,lineups,events)):
            raise SourceSchemaError("explicit original SourceDocument inputs required")
        return _adapt_match(match_id,matches,lineups,events,
                            clock_document_reference=clock_document_reference)
    except (KeyError,TypeError,AttributeError,UnicodeError) as exc:
        raise SourceSchemaError(f"missing/malformed original source schema: {exc}") from exc
