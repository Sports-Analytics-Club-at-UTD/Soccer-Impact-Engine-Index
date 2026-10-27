"""Local match-window diagnostic; no production identity attestation or data outputs.

Run with python -B -m scripts.audit_match_scoped_metrics. A temporary disk-backed
ID index checks the full source across batches; only requested matches are kept.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
import sys
import tempfile

import pandas as pd
import pyarrow.parquet as pq

from scripts.audit_provisional_identity import MAPPING_COLUMNS, prepare_provisional_lookup
from scripts.audit_provisional_metrics import EVENT_COLUMNS as METRIC_COLUMNS, audit_metrics
from src.identity import (PLAYER_KEYS, NAME_KEYS, IdentityError, _columns, _ids, _text,
                          normalize_player_names, normalize_team_names)
from src.identity_evidence import DELIVERED, validate_match_contexts
from src.metrics.press_actions import COUNT_COLS
from src.metrics.recovery_coverage import add_per90

EVENT_COLUMNS = [*METRIC_COLUMNS, "period", "minute", "second"]
MATCH_PLAYER = ["match_id", *PLAYER_KEYS]
STINT_FIELDS = ["position", "from_time", "to_time", "from_period", "to_period",
                "start_reason", "end_reason"]


@dataclass
class MatchAudit:
    events: pd.DataFrame
    pooled: object
    per_match: dict
    lineups: pd.DataFrame
    actors: pd.DataFrame
    exposure: pd.DataFrame
    recovery_per90: pd.DataFrame
    pooled_recovery_per90: pd.DataFrame
    summary: dict


def collect_matches(path, match_ids, *, batch_size=65536, max_events=100000, scratch_dir=None,
                    watch_lookup=None):
    """Scan ALL source batches. Global uniqueness includes nonselected matches.

    SQLite's temporary unique index bounds RAM without a 3.6M-ID Python set.
    It is deleted on success/failure; input Parquets are never opened for writing.
    A selected-row cap bounds retained event payloads independently of file size.
    """
    ids = _ids(pd.Series(match_ids), "requested match IDs")
    if not len(ids) or ids.duplicated().any():
        raise IdentityError("supply distinct explicit match IDs")
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (batch_size, max_events)):
        raise ValueError("batch_size and max_events must be positive integers")
    wanted, pieces, scanned, retained, watched = set(ids), [], 0, 0, []
    with tempfile.TemporaryDirectory(dir=scratch_dir) as temp:
        with closing(sqlite3.connect(str(Path(temp) / "event_ids.sqlite"))) as db:
            db.execute("PRAGMA journal_mode=OFF")
            db.execute("PRAGMA synchronous=OFF")
            db.execute("PRAGMA cache_size=-8192")
            db.execute("PRAGMA temp_store=FILE")
            db.execute("CREATE TABLE ids (id TEXT NOT NULL)")
            for batch in pq.ParquetFile(path).iter_batches(batch_size=batch_size, columns=EVENT_COLUMNS):
                table = batch.to_pandas()
                _text(table.id, "source event IDs")
                _ids(table.match_id, "source match IDs")
                db.executemany("INSERT INTO ids VALUES (?)", ((value,) for value in table.id))
                selected = table.loc[table.match_id.isin(wanted)].copy()
                retained += len(selected)
                if retained > max_events:
                    raise IdentityError("selected event cap exceeded; no partial match audit")
                if len(selected):
                    pieces.append(selected)
                if watch_lookup is not None and len(watch_lookup):
                    names = normalize_player_names(table.player)
                    candidates = table.loc[names.isin(watch_lookup.player_name_raw)].copy()
                    candidates["player_name_raw"] = names.loc[candidates.index]
                    candidates["team"] = normalize_team_names(candidates.team)
                    candidates = candidates.merge(watch_lookup, on=NAME_KEYS, how="inner",
                                                    validate="many_to_one")
                    watched.append(candidates.groupby([*PLAYER_KEYS, "match_id", "type"]).size()
                                   .rename("events").reset_index())
                scanned += len(table)
            try:
                db.execute("CREATE UNIQUE INDEX unique_ids ON ids (id)")
            except sqlite3.IntegrityError as exc:
                raise IdentityError("duplicate event IDs in global source, including across batches") from exc
    events = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(columns=EVENT_COLUMNS)
    missing = wanted - set(events.match_id)
    if missing:
        raise IdentityError(f"requested matches absent from source: {sorted(missing)}")
    watch_counts = (pd.concat(watched, ignore_index=True).groupby([*PLAYER_KEYS, "match_id", "type"])
                    .events.sum().reset_index().to_dict("records") if watched else [])
    return events, {"source_rows_scanned": scanned, "selected_rows": retained,
                    "global_unique_event_ids": scanned, "global_duplicates": 0,
                    "watched_actor_counts": watch_counts,
                    "local_match_collection": "all source batches scanned; source completeness unverified"}


def clock_seconds(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+:\d{2}(?:\.\d+)?", value):
        raise ValueError("missing/invalid stint clock")
    minute, second = value.split(":")
    if float(second) >= 60:
        raise ValueError("invalid stint seconds")
    return int(minute) * 60 + float(second)


def assess_exposure(lineups, actor_events):
    """Conservative local-stint denominators, independent of delivered season minutes.

    Only explicit positive, contiguous, nonoverlapping intervals within a single
    period qualify. Every actor event must lie in those exact intervals. Missing
    final-whistle clocks and intervals crossing periods stay unmeasured: no 90
    minute cap, event-first/last estimate or inferred half/extra-time duration.
    """
    _columns(lineups, [*MATCH_PLAYER, *STINT_FIELDS], "lineup exposure")
    rows = []
    for key, group in lineups.groupby(MATCH_PLAYER, sort=True):
        keys = dict(zip(MATCH_PLAYER, key))
        actor = actor_events
        for column, value in keys.items():
            actor = actor.loc[actor[column].eq(value)]
        reasons, intervals = [], []
        bench = group.position.isna().all() and group[STINT_FIELDS[1:]].isna().all().all()
        if bench:
            reasons = ["actor_without_position_stint"] if len(actor) else []
            status, minutes = ("withheld", None) if reasons else ("bench_no_stint", 0.0)
        else:
            if group.duplicated(STINT_FIELDS).any():
                reasons.append("duplicate_stints")
            for row in group.itertuples(index=False):
                try:
                    start, end = clock_seconds(row.from_time), clock_seconds(row.to_time)
                    periods = _ids(pd.Series([row.from_period, row.to_period]), "stint periods").tolist()
                    if periods[0] not in (1, 2, 3, 4) or periods[1] not in (1, 2, 3, 4):
                        raise ValueError("unsupported period")
                    if periods[0] != periods[1]:
                        reasons.append("cross_period_duration_unverified")
                    if pd.isna(row.position) or end <= start:
                        reasons.append("invalid_position_or_nonpositive_interval")
                    if start < {1: 0, 2: 2700, 3: 5400, 4: 6300}[periods[0]]:
                        reasons.append("clock_period_disagreement")
                    intervals.append((periods[0], start, end, row.start_reason, row.end_reason))
                except (ValueError, TypeError):
                    reasons.append("missing_or_invalid_interval_or_period")
            intervals.sort(key=lambda x: (x[0], x[1], x[2]))
            if intervals:
                first, last = intervals[0], intervals[-1]
                if not (str(first[3]) == "Starting XI" or str(first[3]).startswith("Substitution - On")):
                    reasons.append("initial_stint_not_entry")
                if str(first[3]) == "Starting XI" and (first[0] != 1 or first[1] != 0):
                    reasons.append("starting_xi_clock_mismatch")
                if not (str(last[4]).startswith("Substitution - Off") or str(last[4]) in
                        ("Final Whistle", "Red Card", "Player Off")):
                    reasons.append("terminal_stint_not_exit")
                for previous, current in zip(intervals, intervals[1:]):
                    if previous[0] != current[0]:
                        reasons.append("multiple_period_timing_unverified")
                    elif current[1] < previous[2]:
                        reasons.append("overlapping_stints")
                    elif current[1] != previous[2]:
                        reasons.append("gapped_stints")
                for event in actor.itertuples(index=False):
                    seconds = event.minute * 60 + event.second
                    if not any(event.period == p and start <= seconds <= end
                               for p, start, end, _, _ in intervals):
                        reasons.append("actor_event_outside_stints")
            else:
                reasons.append("no_measurable_interval")
            status = "withheld" if reasons else "aligned_explicit_stints"
            minutes = None if reasons else sum(end - start for _, start, end, _, _ in intervals) / 60
        rows.append(keys | {"lineup_rows": len(group), "actor_events": len(actor),
                            "exposure_status": status, "minutes": minutes,
                            "reasons": ";".join(sorted(set(reasons)))})
    result = pd.DataFrame(rows, columns=[*MATCH_PLAYER, "lineup_rows", "actor_events",
                                        "exposure_status", "minutes", "reasons"])
    result["minutes"] = pd.to_numeric(result.minutes).astype(float)
    return result


def match_metrics(events, crosswalk, minutes, lineups, metadata, *, local_collection_complete=False):
    """Validate context/lineup associations before D2A metrics.

    The pure caller must explicitly attest exhaustive local match collection to
    enable exposure-based rates. Shape, context agreement and closed stints alone
    cannot establish that the input contains all locally available match rows.
    The file wrapper supplies this flag only after collect_matches reaches EOF.
    """
    if not isinstance(local_collection_complete, bool):
        raise ValueError("local collection attestation must be an explicit boolean")
    contexts = validate_match_contexts(metadata, source="event-derived delivered metadata",
                                       evidence_kind=DELIVERED).contexts
    observed = validate_match_contexts(events, source="local observed events", evidence_kind=DELIVERED).contexts
    validate_match_contexts(pd.concat([contexts, observed]), source="metadata/event agreement",
                            evidence_kind=DELIVERED)
    if set(observed.match_id) - set(contexts.match_id):
        raise IdentityError("observed matches absent from delivered context metadata")
    source = lineups.loc[lineups.match_id.isin(observed.match_id)].copy()
    _columns(source, ["match_id", "team", "player_id", "player_name", *STINT_FIELDS], "lineups")
    source["match_id"] = _ids(source.match_id, "lineup match IDs")
    source["player_id"] = _ids(source.player_id, "lineup player IDs")
    source["team"] = normalize_team_names(source.team)
    source["player_name_raw"] = normalize_player_names(source.player_name)
    _text(source.player_name_raw, "lineup actor names")
    if "competition_name" in source or "season_name" in source:
        validate_match_contexts(pd.concat([source, contexts]), source="direct lineup agreement",
                                evidence_kind=DELIVERED)
        source = source.drop(columns=["competition_name", "season_name"])
    source = source.merge(contexts, on="match_id", how="left", validate="many_to_one")
    # D2A resolves the entire selected input, so no per-match partial result can
    # escape when any actor is unresolved. This does not attest source trust.
    pooled = audit_metrics(events, crosswalk, minutes)
    resolved = pooled.identity.events
    keys = ["match_id", "team", "player_id"]
    spelling_keys = [*keys, "player_name_raw"]
    actor_keys = resolved.copy()
    actor_keys["player_name_raw"] = normalize_player_names(actor_keys.player)
    actors = actor_keys[spelling_keys].drop_duplicates().merge(
        source[spelling_keys].drop_duplicates(), on=spelling_keys, how="left",
        indicator=True, validate="one_to_one")
    if actors._merge.ne("both").any():
        raise IdentityError("event actor ID/team/original spelling absent from that match lineup: "
                            + str(actors.loc[actors._merge.ne("both"), spelling_keys].to_dict("records")))
    team_keys = ["match_id", "team"]
    teams = resolved[team_keys].drop_duplicates().merge(source[team_keys].drop_duplicates(),
                 on=team_keys, how="outer", indicator=True, validate="one_to_one")
    if teams._merge.ne("both").any():
        raise IdentityError("event/lineup match-team association discrepancy: " + str(teams.to_dict("records")))
    for column in ("period", "minute", "second"):
        values = events[column]
        if not pd.api.types.is_numeric_dtype(values) or values.isna().any():
            raise IdentityError("missing/nonnumeric event time fields")
        if ((values % 1 != 0) | (values < 0) | (values == float("inf"))).any():
            raise IdentityError("invalid event time fields")
    if not events.period.isin([1, 2, 3, 4]).all() or not events.second.lt(60).all():
        raise IdentityError("unsupported period or second fields")
    by_match = {int(mid): audit_metrics(group, crosswalk, minutes)
                for mid, group in events.groupby("match_id", sort=True)}
    for category in ("Tackle", "Interception", "Ball Recovery"):
        count = sum(int(r.recovery.loc[r.recovery.event_type.eq(category), "count"].sum())
                    for r in by_match.values())
        if count != int(pooled.recovery.loc[pooled.recovery.event_type.eq(category), "count"].sum()):
            raise IdentityError("recovery conservation across match boundary failed")
    for column in COUNT_COLS:
        if sum(int(r.press[column].sum()) for r in by_match.values()) != int(pooled.press[column].sum()):
            raise IdentityError("press conservation across match boundary failed")
    for attribute, keys, columns in [
            ("recovery", [*PLAYER_KEYS, "event_type"], ["count"]),
            ("by_zone", [*PLAYER_KEYS, "event_type", "zone"], ["count"]),
            ("press", PLAYER_KEYS, COUNT_COLS)]:
        combined = pd.concat([getattr(r, attribute) for r in by_match.values()], ignore_index=True)
        combined = combined.groupby(keys)[columns].sum().sort_index().reset_index()
        expected = getattr(pooled, attribute)[[*keys, *columns]].sort_values(keys).reset_index(drop=True)
        if combined.to_dict("records") != expected.to_dict("records"):
            raise IdentityError(f"{attribute} player-key conservation across match boundary failed")
    exposure = assess_exposure(source, resolved)
    if not local_collection_complete:
        eligible = exposure.exposure_status.eq("aligned_explicit_stints")
        exposure.loc[eligible, "minutes"] = float("nan")
        exposure.loc[eligible, "exposure_status"] = "withheld"
        exposure.loc[eligible, "reasons"] = "local_match_collection_not_established"
    rec = pd.concat([r.recovery.assign(match_id=mid) for mid, r in by_match.items()], ignore_index=True)
    match_rates = add_per90(rec, exposure[[*MATCH_PLAYER, "minutes"]], on=MATCH_PLAYER)
    match_rates = match_rates.merge(exposure[[*MATCH_PLAYER, "exposure_status", "reasons"]],
                                    on=MATCH_PLAYER, validate="many_to_one")
    pooled_exposure = []
    for key, group in exposure.groupby(PLAYER_KEYS, sort=True):
        valid = group.exposure_status.isin(["aligned_explicit_stints", "bench_no_stint"]).all()
        pooled_exposure.append(dict(zip(PLAYER_KEYS, key)) | {
            "minutes": float(group.minutes.sum()) if valid else None})
    pool_exposure = pd.DataFrame(pooled_exposure)
    pool_exposure["minutes"] = pd.to_numeric(pool_exposure.minutes).astype(float)
    pool_rates = add_per90(pooled.recovery, pool_exposure, on=PLAYER_KEYS)
    details = []
    for mid, group in resolved.groupby("match_id", sort=True):
        roster = source.loc[source.match_id.eq(mid)]
        details.append({"match_id": int(mid), "competition_name": group.competition_name.iloc[0],
            "season_name": group.season_name.iloc[0], "teams": sorted(group.team.unique()),
            "events": len(group), "unique_ids": int(group.id.nunique()),
            "lineup_rows": len(roster), "lineup_player_ids": {
                team: sorted(map(int, g.player_id.unique())) for team, g in roster.groupby("team")},
            "period_ranges": {int(p): [int((g.minute*60+g.second).min()),
                                        int((g.minute*60+g.second).max())]
                              for p, g in group.groupby("period")}})
    return MatchAudit(events, pooled, by_match, source, actors, exposure, match_rates, pool_rates, {
        "label": "PROVISIONAL OBSERVED METRICS - NOT PRODUCTION-VERIFIED",
        "matches": details, "context_contradictions": 0, "actor_lineup_discrepancies": 0,
        "local_collection_complete": local_collection_complete, "authoritative_feed_complete": False,
        "exposure_status_counts": exposure.exposure_status.value_counts().to_dict(),
        "recovery_rows_with_per90": int(match_rates.per90.notna().sum()),
        "pooled_recovery_rows_with_per90": int(pool_rates.per90.notna().sum())})


def audit_files(*, events_path, crosswalk_path, minutes_path, lineups_path, metadata_path,
                match_ids, batch_size=65536, max_events=100000, scratch_dir=None,
                investigate_player_ids=()):
    for path in (events_path, crosswalk_path, minutes_path, lineups_path, metadata_path):
        if not Path(path).is_file():
            raise FileNotFoundError(f"Required input unavailable: {path}")
    crosswalk = pq.read_table(crosswalk_path, columns=MAPPING_COLUMNS).to_pandas()
    lookup = prepare_provisional_lookup(crosswalk).lookup
    watch_ids = _ids(pd.Series(list(investigate_player_ids), dtype=object), "investigation player IDs")
    if set(watch_ids) - set(lookup.player_id):
        raise IdentityError("investigation IDs absent from nonconflicting provisional lookup")
    watch = lookup.loc[lookup.player_id.isin(watch_ids)] if len(watch_ids) else None
    events, scan = collect_matches(events_path, match_ids, batch_size=batch_size,
                                   max_events=max_events, scratch_dir=scratch_dir, watch_lookup=watch)
    result = match_metrics(events,
        crosswalk,
        pq.read_table(minutes_path, columns=[*PLAYER_KEYS, "minutes"]).to_pandas(),
        pq.read_table(lineups_path).to_pandas(), pq.read_table(metadata_path).to_pandas(),
        local_collection_complete=True)
    result.summary["source_scan"] = scan
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("events", "crosswalk", "minutes", "lineups", "metadata"):
        parser.add_argument("--" + option, required=True, type=Path)
    parser.add_argument("--match-ids", required=True, nargs="+", type=int)
    parser.add_argument("--batch-size", type=int, default=65536)
    parser.add_argument("--max-events", type=int, default=100000)
    parser.add_argument("--scratch-dir", type=Path)
    parser.add_argument("--investigate-player-ids", nargs="*", type=int, default=[])
    args = parser.parse_args(argv)
    try:
        result = audit_files(events_path=args.events, crosswalk_path=args.crosswalk,
            minutes_path=args.minutes, lineups_path=args.lineups, metadata_path=args.metadata,
            match_ids=args.match_ids, batch_size=args.batch_size, max_events=args.max_events,
            scratch_dir=args.scratch_dir, investigate_player_ids=args.investigate_player_ids)
    except (ValueError, OSError) as exc:
        print(f"Diagnostic rejected: {exc}", file=sys.stderr)
        if hasattr(exc, "identity"):
            print(exc.identity.unmatched.to_string(index=False), file=sys.stderr)
        if hasattr(exc, "details"):
            print(exc.details, file=sys.stderr)
        return 1
    print(result.summary)
    print("Pooled identity", result.pooled.identity.summary)
    print("Pooled raw metrics", result.pooled.summary)
    for mid, audit in result.per_match.items():
        print("Match", mid, audit.summary)
        for table in (audit.recovery, audit.by_zone, audit.press):
            print(table.to_string(index=False))
    for name, table in [("Lineup stints", result.lineups), ("Exposure", result.exposure),
                        ("Match recovery/per90", result.recovery_per90),
                        ("Pooled recovery/per90", result.pooled_recovery_per90)]:
        print(name, table.to_string(index=False))
    print("Only explicit aligned local stints can yield provisional per90; no production outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
