"""Read-only four-league 2015/2016 readiness audit; no scoring or publication.

Explicit paths, projected Arrow batches, bounded summary keys and a temporary
disk-backed event-ID index. All returned/printed results remain provisional.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import dataclass
import json
from numbers import Integral, Real
from pathlib import Path
import sqlite3
import sys
import tempfile

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from scripts.audit_provisional_identity import MAPPING_COLUMNS, audit_provisional, prepare_provisional_lookup
from scripts.audit_match_scoped_metrics import clock_seconds
from src.dri_scoring import LEAGUES, SEASON, MIN_MINUTES, ROLE_GROUPS, _number
from src.identity import (PLAYER_KEYS, NAME_KEYS, _contexts, _ids, normalize_player_names,
                          normalize_team_names, validate_population)
from src.identity_evidence import DELIVERED, validate_match_contexts
from src.metrics.recovery_coverage import EVENT_TYPES
from src.recovery import _extract, _minutes

EVENT_COLUMNS = ["id", "match_id", "player", "team", "competition_name", "season_name", "type",
    "location", "duel_type", "duel_outcome", "interception_outcome", "ball_recovery_recovery_failure",
    "position", "period", "minute", "second"]
ROLE_MINUTES = [f"min_{role}" for role in ("GK", "CB", "DM", "CM", "FB", "WM", "AM", "ATT")]
MINUTE_COLUMNS = [*PLAYER_KEYS, "player_name", "minutes", "matches", "position_group", "tied_groups", *ROLE_MINUTES]
RECOVERY_COLUMNS = [*PLAYER_KEYS, "event_type", "count", "minutes", "per90", "matches", "position_group",
                    "reportable", "full_coverage", "meets_min"]
LINEUP_COLUMNS = ["match_id", "team", "player_id", "player_name", "position", "from_time", "to_time",
                  "from_period", "to_period", "start_reason", "end_reason"]
RECOVERY_KEYS = [*PLAYER_KEYS, "event_type"]


class ReadinessError(ValueError):
    """Unsafe source structure; no arbitrary repair or source attestation."""


@dataclass
class ReadinessResult:
    summary: dict
    candidates: pd.DataFrame
    unmatched: pd.DataFrame
    discrepancies: pd.DataFrame


def target(table):
    return table.loc[table.competition_name.isin(LEAGUES) & table.season_name.eq(SEASON)].copy()


def canonical(table, *, recovery=False, allow_duplicates=False):
    columns = RECOVERY_COLUMNS if recovery else MINUTE_COLUMNS
    if not table.columns.is_unique or any(c not in table for c in columns):
        raise ReadinessError("missing/duplicate delivered columns")
    out = _contexts(table[columns], "delivered table").reset_index(drop=True)
    out["player_id"] = _ids(out.player_id, "delivered player IDs")
    key = RECOVERY_KEYS if recovery else PLAYER_KEYS
    if out.duplicated(key).any() and not allow_duplicates:
        raise ReadinessError("duplicate canonical delivered keys")
    if not recovery:
        if not allow_duplicates:
            _minutes(out)
        else:
            for v in out.minutes:
                _number(v,"minutes")
        for col in ["matches", "tied_groups", *ROLE_MINUTES]:
            for v in out[col]:
                _number(v, col, integer=col in ("matches", "tied_groups"))
    else:
        if not out.event_type.isin(EVENT_TYPES).all():
            raise ReadinessError("unknown delivered recovery category")
        for col in ("count", "minutes", "per90", "matches"):
            for v in out[col]:
                _number(v, col, integer=col in ("count", "matches"))
        for col in ("reportable", "full_coverage", "meets_min"):
            if not all(type(v) is bool for v in out[col]):
                raise ReadinessError("delivered flags require actual booleans")
    return out


def table_integrity(minutes, recovery):
    """Validate keys first; arithmetic is a structural check, not scope proof."""
    minutes, recovery = canonical(minutes), canonical(recovery, recovery=True)
    minute_keys = set(minutes[PLAYER_KEYS].itertuples(index=False, name=None))
    recovery_keys = set(recovery[PLAYER_KEYS].itertuples(index=False, name=None))
    contradictions = recovery.groupby(PLAYER_KEYS)[["minutes", "matches", "position_group", "full_coverage"]].nunique(dropna=False)
    if contradictions.gt(1).any().any():
        raise ReadinessError("conflicting metadata across corrected component records")
    joined = recovery.merge(minutes[[*PLAYER_KEYS, "minutes", "matches", "position_group"]], on=PLAYER_KEYS,
        how="left", suffixes=("", "_population"), validate="many_to_one", indicator=True)
    counts = {"rows": len(recovery), "contexts": len(recovery_keys), "duplicate_keys": 0,
              "contexts_absent_from_minutes": len(recovery_keys-minute_keys)}
    for col in ("minutes", "matches", "position_group"):
        same = joined[col].eq(joined[col+"_population"]) | (joined[col].isna() & joined[col+"_population"].isna())
        counts[col+"_disagreements"] = int((joined._merge.eq("both") & ~same).sum())
    positive = recovery.minutes.gt(0) & recovery["count"].notna() & recovery.per90.notna()
    expected = recovery.loc[positive,"count"] / recovery.loc[positive,"minutes"] * 90
    counts["arithmetic_rows_checked"] = int(positive.sum())
    counts["arithmetic_disagreements"] = int((~np.isclose(recovery.loc[positive,"per90"], expected, rtol=1e-9, atol=1e-9)).sum())
    counts["arithmetic_scope_independently_aligned"] = False
    counts["unsupported_per90_rows"] = int((~recovery.minutes.gt(0) | recovery.per90.isna()).sum())
    counts["meets_min_flag_disagreements"] = int(recovery.meets_min.ne(recovery.minutes.ge(MIN_MINUTES)).sum())
    return minutes, recovery, counts


def candidate_population(minutes, recovery):
    """Every explicit DM/CM/CB context; no scoring, zero filling or transfer collapse."""
    minutes, recovery, integrity = table_integrity(minutes, recovery)
    rows = []
    components = {k: g.set_index("event_type") for k,g in target(recovery).groupby(PLAYER_KEYS, sort=True)}
    for source in target(minutes).sort_values(PLAYER_KEYS).to_dict("records"):
        role = source["position_group"]
        if role not in ("DM", "CM", "CB"):
            continue
        key = tuple(source[c] for c in PLAYER_KEYS)
        component = components.get(key, recovery.iloc[:0].set_index("event_type"))
        complete = set(component.index) == set(EVENT_TYPES)
        numeric = complete and bool(component[["count", "per90", "minutes"]].notna().all().all())
        flags = complete and bool(component.reportable.all())
        coverage = complete and bool(component.full_coverage.all())
        aligned_values = complete and bool(component.minutes.eq(source["minutes"]).all())
        arithmetic = numeric and source["minutes"] > 0 and bool(np.isclose(component.per90,
            component["count"] / component.minutes * 90, rtol=1e-9, atol=1e-9).all())
        metadata_ok = complete and aligned_values and bool(component.position_group.eq(role).all()) and bool(component.matches.eq(source["matches"]).all())
        delivered = (bool(pd.notna(source["minutes"]) and source["minutes"] >= MIN_MINUTES)
                     and numeric and flags and coverage and arithmetic and metadata_ok)
        rows.append({**{c:source[c] for c in PLAYER_KEYS}, "player_name":source["player_name"],
            "position_group":role, "score_group":ROLE_GROUPS[role], "minutes":source["minutes"],
            "delivered_matches":source["matches"], "tied_groups":source["tied_groups"],
            "under_900":bool(pd.notna(source["minutes"]) and source["minutes"] < MIN_MINUTES),
            "zero_minutes":bool(source["minutes"] == 0), "missing_minutes":bool(pd.isna(source["minutes"])),
            "component_rows":len(component), "complete_components":complete, "numeric_complete":numeric,
            "all_reportable":flags, "delivered_full_coverage":coverage, "arithmetic_ok":arithmetic,
            "metadata_consistent":metadata_ok, "delivered_rules_eligible":delivered,
            "independently_verified_identity":False, "independently_verified_coverage":False,
            "independently_aligned_exposure":False, "production_ready":False})
    columns = [*PLAYER_KEYS,"player_name","position_group","score_group","minutes","delivered_matches","tied_groups",
        "under_900","zero_minutes","missing_minutes","component_rows","complete_components","numeric_complete",
        "all_reportable","delivered_full_coverage","arithmetic_ok","metadata_consistent","delivered_rules_eligible",
        "independently_verified_identity","independently_verified_coverage","independently_aligned_exposure","production_ready"]
    return pd.DataFrame(rows,columns=columns), integrity


def compare_tables(left, right, *, recovery=False):
    left, right = canonical(left,recovery=recovery), canonical(right,recovery=recovery)
    keys = RECOVERY_KEYS if recovery else PLAYER_KEYS
    cols = RECOVERY_COLUMNS if recovery else MINUTE_COLUMNS
    joined = left.merge(right,on=keys,how="outer",validate="one_to_one",indicator=True,suffixes=("_a","_b"))
    differences = {}
    for c in cols:
        if c not in keys:
            a,b=joined[c+"_a"],joined[c+"_b"]
            differences[c]=int((joined._merge.eq("both") & ~(a.eq(b) | (a.isna() & b.isna()))).sum())
    return {"left_only_keys":int(joined._merge.eq("left_only").sum()),
            "right_only_keys":int(joined._merge.eq("right_only").sum()),"field_differences":differences}


def _read(path, columns, max_rows=200000):
    if not Path(path).is_file():
        raise FileNotFoundError(f"Required input unavailable: {path}")
    file=pq.ParquetFile(path)
    if file.metadata.num_rows > max_rows:
        raise ReadinessError("small-table row bound exceeded")
    return file.read(columns=columns).to_pandas()


def _keyset(table, columns):
    return set(table[columns].itertuples(index=False,name=None))


def _valid_id(value):
    return (not isinstance(value,(bool,np.bool_)) and isinstance(value,Real) and pd.notna(value)
            and 0 < value <= 2**63-1 and value == int(value)
            and (isinstance(value,Integral) or value <= 2**53-1))


def _label(value):
    return isinstance(value,str) and bool(value.strip())


def lineup_exposure_compatibility(candidates, roster):
    """Explain delivered matches/minutes under the contributor's assumptions only.

    Mirroring missing-start=0, missing-end=90 and 0..90 clipping is a diagnostic
    reconciliation, never adoption of those assumptions as verified exposure.
    No rates, scores or new measurements are exported from this calculation.
    """
    active=roster.loc[roster.position.notna()].copy()
    def clock(value):
        return np.nan if pd.isna(value) else clock_seconds(value)/60
    start=active.from_time.map(clock).fillna(0).clip(0,90)
    end=active.to_time.map(clock).fillna(90).clip(0,90)
    active["assumed_minutes"]=(end-start).clip(lower=0)
    grouped=active.groupby([*PLAYER_KEYS,"match_id"]).assumed_minutes.sum().reset_index()
    minutes=grouped.groupby(PLAYER_KEYS).assumed_minutes.sum().rename("assumed_minutes").reset_index()
    positive=grouped.loc[grouped.assumed_minutes.gt(0)].groupby(PLAYER_KEYS).size().rename("assumed_matches").reset_index()
    played=active.groupby(PLAYER_KEYS).match_id.nunique().rename("active_stint_matches").reset_index()
    compared=candidates.merge(minutes,on=PLAYER_KEYS,how="left",validate="one_to_one").merge(
        positive,on=PLAYER_KEYS,how="left",validate="one_to_one").merge(played,on=PLAYER_KEYS,how="left",validate="one_to_one")
    mismatch=compared.delivered_matches.ne(compared.active_stint_matches)
    open_contexts=_keyset(active.loc[active.to_time.isna()],PLAYER_KEYS)
    qualified=_keyset(candidates.loc[candidates.delivered_rules_eligible],PLAYER_KEYS)
    return {"label":"compatibility with contributor 90-minute/default-end convention ONLY; NOT verified exposure",
        "position_stint_match_count_disagreements":int(mismatch.sum()),
        "qualified_position_stint_match_count_disagreements":int((mismatch&compared.delivered_rules_eligible).sum()),
        "positive_clipped_match_count_disagreements":int(compared.delivered_matches.ne(compared.assumed_matches).sum()),
        "pooled_minutes_disagreements_under_assumptions":int((~np.isclose(compared.minutes,compared.assumed_minutes,rtol=1e-9,atol=1e-9)).sum()),
        "clipped_zero_duration_active_stints":int(active.assumed_minutes.eq(0).sum()),
        "qualified_contexts_with_open_active_stints":len(open_contexts&qualified),
        "independent_exposure_verified":False}


def scan_events(path, crosswalk, candidates, lineups, metadata, *, batch_size=65536,
                scratch_dir=None, max_summary_keys=250000):
    """Full local target-scope scan; event payload memory never exceeds one batch.

    Compact match/actor/count summaries have an explicit key cap. SQLite's
    disposable ID index prevents a multi-million-ID Python set. No real scoring.
    """
    if type(batch_size) is not int or not 0 < batch_size <= 65536:
        raise ReadinessError("batch_size must be in 1..65536")
    if type(max_summary_keys) is not int or max_summary_keys <= 0:
        raise ReadinessError("positive summary-key bound required")
    if not Path(path).is_file():
        raise FileNotFoundError(f"Required input unavailable: {path}")
    lookup=prepare_provisional_lookup(crosswalk)
    population=validate_population(candidates[PLAYER_KEYS])
    contexts=validate_match_contexts(metadata,source="event-derived delivered metadata",evidence_kind=DELIVERED).contexts
    context_map={r.match_id:(r.competition_name,r.season_name) for r in contexts.itertuples()}
    roster=lineups.copy(deep=True)
    roster["match_id"]=_ids(roster.match_id,"lineup match ID")
    roster["player_id"]=_ids(roster.player_id,"lineup player ID")
    roster["team"]=normalize_team_names(roster.team)
    roster["player_name_raw"]=normalize_player_names(roster.player_name)
    if not roster.player_name_raw.map(_label).all():
        raise ReadinessError("lineups contain missing/invalid original names")
    direct=[c in roster for c in ("competition_name","season_name")]
    if any(direct) and not all(direct):
        raise ReadinessError("partial lineup context fields")
    if all(direct):
        validate_match_contexts(pd.concat([contexts,roster]),source="direct lineup agreement",evidence_kind=DELIVERED)
        roster=roster.drop(columns=["competition_name","season_name"])
    roster=roster.merge(contexts,on="match_id",how="left",validate="many_to_one",indicator=True)
    missing_metadata=int(roster._merge.ne("both").sum())
    scoped_roster=target(roster)
    roster_names=_keyset(scoped_roster,["match_id","team","player_id","player_name_raw"])
    roster_ids=_keyset(scoped_roster,["match_id","team","player_id"])
    roster_teams=_keyset(scoped_roster,["match_id","team"])
    seen_matches=defaultdict(set); match_teams=set(); match_contexts=set(); actors=set(); actor_names=set()
    candidate_matches=defaultdict(set); count_rows=Counter(); event_by_context=Counter(); unmatched=Counter()
    metadata_disagreements=set(); actor_absent_ids=set(); actor_absent_names=set()
    totals=Counter({k:0 for k in ("target_rows","invalid_input","selected","outside_population","unresolved",
        "events_affected_by_conflicting_keys","missing_actor_names","duplicate_joins","invalid_global_event_ids",
        "invalid_global_scope_labels","invalid_clock_rows","normalized_name_changes","team_alias_changes")})
    per_league={league:Counter() for league in LEAGUES}; nulls=Counter(); types=Counter(); positions=Counter()
    recovery_accounting=Counter(); source_rows=0
    with tempfile.TemporaryDirectory(dir=scratch_dir) as temporary:
        with closing(sqlite3.connect(str(Path(temporary)/"event_ids.sqlite"))) as db:
            db.execute("PRAGMA journal_mode=OFF"); db.execute("PRAGMA synchronous=OFF")
            db.execute("PRAGMA cache_size=-8192"); db.execute("PRAGMA temp_store=FILE")
            db.execute("CREATE TABLE ids(id TEXT NOT NULL)")
            for batch in pq.ParquetFile(path).iter_batches(batch_size=batch_size,columns=EVENT_COLUMNS):
                data=batch.to_pandas(); source_rows+=len(data)
                valid_ids=data.id.map(_label)
                totals["invalid_global_event_ids"]+=int((~valid_ids).sum())
                db.executemany("INSERT INTO ids VALUES (?)",((v,) for v in data.loc[valid_ids,"id"]))
                totals["invalid_global_scope_labels"]+=int((~data.competition_name.map(_label) | ~data.season_name.map(_label)).sum())
                events=target(data).reset_index(drop=True)
                if events.empty:
                    continue
                totals["target_rows"]+=len(events)
                totals["target_invalid_event_ids"]+=int((~events.id.map(_label)).sum())
                nulls.update({c:int(events[c].isna().sum()) for c in EVENT_COLUMNS})
                types.update({str(k):int(v) for k,v in events.type.value_counts(dropna=False).items()})
                positions.update({str(k):int(v) for k,v in events.position.value_counts(dropna=False).items()})
                identity_valid=events.id.map(_label)&events.match_id.map(_valid_id)&events.team.map(_label)&events.player.map(lambda v:pd.isna(v) or isinstance(v,str))
                totals["invalid_input"]+=int((~identity_valid).sum())
                for league,g in events.groupby("competition_name"):
                    per_league[league]["events"]+=len(g)
                    per_league[league]["invalid_input"]+=int((~identity_valid.loc[g.index]).sum())
                events=events.loc[identity_valid].reset_index(drop=True)
                if events.empty:
                    continue
                normalized_teams=normalize_team_names(events.team)
                totals["team_alias_changes"]+=int(events.team.ne(normalized_teams).sum())
                events["team"]=normalized_teams
                times=events[["period","minute","second"]].apply(pd.to_numeric,errors="coerce")
                good_time=times.notna().all(axis=1)&np.isfinite(times).all(axis=1)&times.ge(0).all(axis=1)&times.mod(1).eq(0).all(axis=1)&times.period.isin([1,2,3,4])&times.second.lt(60)
                totals["invalid_clock_rows"]+=int((~good_time).sum())
                for mid,league,season in events[["match_id","competition_name","season_name"]].drop_duplicates().itertuples(index=False,name=None):
                    match_contexts.add((int(mid),league,season)); seen_matches[league].add(int(mid))
                    if context_map.get(mid)!=(league,season):
                        metadata_disagreements.add((int(mid),league,season))
                match_teams.update((int(mid),team) for mid,team in events[["match_id","team"]].drop_duplicates().itertuples(index=False,name=None))
                audit=audit_provisional(events,crosswalk,population)
                resolved=audit.events
                for name in ("selected","outside_population","unresolved","events_affected_by_conflicting_keys","missing_actor_names","duplicate_joins"):
                    totals[name]+=audit.summary[name]
                totals["normalized_name_changes"]+=int((events.player.notna() & events.player.ne(normalize_player_names(events.player))).sum())
                for league,g in resolved.groupby("competition_name"):
                    per_league[league].update({s:int(g.identity_status.eq(s).sum()) for s in ("selected","outside_population","unresolved")})
                for r in audit.unmatched.to_dict("records"):
                    k=tuple(None if pd.isna(r[c]) else r[c] for c in [*NAME_KEYS,"reason"])
                    unmatched[k]+=int(r["events"])
                known=resolved.loc[resolved.player_id.notna()].copy()
                known["player_name_raw"]=normalize_player_names(known.player)
                for mid,team,pid,name in known[["match_id","team","player_id","player_name_raw"]].drop_duplicates().itertuples(index=False,name=None):
                    actor=(int(mid),team,int(pid)); spelling=(*actor,name)
                    actors.add(actor); actor_names.add(spelling)
                    if actor not in roster_ids: actor_absent_ids.add(actor)
                    if spelling not in roster_names: actor_absent_names.add(spelling)
                selected=resolved.loc[resolved.identity_status.eq("selected")]
                event_by_context.update({tuple(k):int(n) for k,n in selected.groupby(PLAYER_KEYS).size().items()})
                for row in selected[[*PLAYER_KEYS,"match_id"]].drop_duplicates().itertuples(index=False,name=None):
                    candidate_matches[tuple(row[:-1])].add(int(row[-1]))
                # Reuse unchanged M2B extraction; unresolved actions stay explicit.
                rec=_extract(events).merge(resolved[["id","player_id","identity_status"]],on="id",how="left",validate="one_to_one")
                for (kind,status),n in rec.groupby(["event_type","identity_status"]).size().items():
                    recovery_accounting[(kind,status)]+=int(n)
                known_rec=rec.loc[rec.player_id.notna()]
                count_rows.update({tuple(k):int(n) for k,n in known_rec.groupby(RECOVERY_KEYS).size().items()})
                if sum(map(len,(match_contexts,match_teams,actors,actor_names,count_rows,unmatched)))>max_summary_keys:
                    raise ReadinessError("summary-key memory bound exceeded; no partial readiness result")
            try:
                db.execute("CREATE UNIQUE INDEX event_id_unique ON ids(id)")
            except sqlite3.IntegrityError as exc:
                duplicates=db.execute("SELECT count(*) FROM (SELECT id FROM ids GROUP BY id HAVING count(*)>1)").fetchone()[0]
                raise ReadinessError(f"duplicate global event IDs: {duplicates}; no deduplication or partial readiness") from exc
    if totals["target_rows"]!=sum(totals[s] for s in ("selected","outside_population","unresolved","invalid_input")):
        raise ReadinessError("event row conservation failed")
    clashes=len(match_contexts)-len({r[0] for r in match_contexts})
    if clashes:
        raise ReadinessError("contradictory event match/competition/season associations")
    leagues=[]
    for league in LEAGUES:
        mids=seen_matches[league]
        teams=sorted({team for mid,team in match_teams if mid in mids})
        source_roster=scoped_roster.loc[scoped_roster.competition_name.eq(league)]
        leagues.append({"competition_name":league,"events":0,"invalid_input":0,"selected":0,"outside_population":0,"unresolved":0,
            **dict(per_league[league]),"matches":len(mids),"match_ids":sorted(mids),
            "match_team_contexts":sum(mid in mids for mid,team in match_teams),"teams":teams,
            "lineup_rows":len(source_roster),"lineup_matches":int(source_roster.match_id.nunique()),
            "source_matches_missing_lineups":len(mids-set(source_roster.match_id)),
            "lineup_matches_absent_from_events":len(set(source_roster.match_id)-mids)})
    summary={"label":"PROVISIONAL — NOT PRODUCTION VERIFIED", "source_rows_scanned":source_rows,
        "events":dict(sorted(totals.items())),"leagues":leagues,"duplicate_global_event_ids":0,
        "global_unique_valid_event_ids":source_rows-totals["invalid_global_event_ids"],
        "target_unique_valid_event_ids":totals["target_rows"]-totals["target_invalid_event_ids"],
        "lookup":lookup.summary,"null_counts":dict(sorted(nulls.items())),"event_types":dict(sorted(types.items())),
        "event_positions":dict(sorted(positions.items())),"match_context_conflicts":clashes,
        "event_metadata_disagreements":len(metadata_disagreements),"lineup_rows_missing_metadata":missing_metadata,
        "lineups_have_direct_context":all(direct),"target_lineup_rows":len(scoped_roster),
        "target_lineup_match_team_contexts":len(roster_teams),
        "event_match_teams_missing_lineups":len(match_teams-roster_teams),
        "lineup_match_teams_absent_from_events":len(roster_teams-match_teams),
        "known_actor_match_contexts":len(actors),"actor_id_team_match_discrepancies":len(actor_absent_ids),
        "actor_spelling_match_discrepancies":len(actor_absent_names),
        "recovery_accounting":[{"event_type":kind,**{s:recovery_accounting[(kind,s)] for s in ("selected","outside_population","unresolved")}} for kind in EVENT_TYPES],
        "row_count_conserved":True,"source_coverage_independently_verified":False,
        "numerator_scope":"all target rows in supplied local source; full-season completeness not established"}
    unmatched_table=pd.DataFrame([{**dict(zip([*NAME_KEYS,"reason"],k)),"events":n} for k,n in unmatched.items()],columns=[*NAME_KEYS,"reason","events"])
    if not unmatched_table.empty: unmatched_table=unmatched_table.sort_values([*NAME_KEYS,"reason"],na_position="last").reset_index(drop=True)
    reconstructed=pd.DataFrame([{**dict(zip(RECOVERY_KEYS,k)),"observed_count":v} for k,v in count_rows.items()],columns=[*RECOVERY_KEYS,"observed_count"])
    return summary,reconstructed,unmatched_table,scoped_roster,candidate_matches,event_by_context


def audit_files(*, events_path, lineups_path, crosswalk_path, minutes_path, recovery_path,
                refresh_minutes_path, refresh_recovery_path, metadata_path,
                original_minutes_path, original_recovery_path, batch_size=65536, scratch_dir=None):
    for path in (events_path,lineups_path,crosswalk_path,minutes_path,recovery_path,refresh_minutes_path,
                 refresh_recovery_path,metadata_path,original_minutes_path,original_recovery_path):
        if not Path(path).is_file():
            raise FileNotFoundError(f"Required input unavailable: {path}")
    minutes=_read(minutes_path,MINUTE_COLUMNS); recovery=_read(recovery_path,RECOVERY_COLUMNS)
    candidates,integrity=candidate_population(minutes,recovery)
    refreshed_minutes=_read(refresh_minutes_path,MINUTE_COLUMNS)
    refreshed_recovery=_read(refresh_recovery_path,RECOVERY_COLUMNS)
    table_integrity(refreshed_minutes,refreshed_recovery)
    crosswalk=_read(crosswalk_path,MAPPING_COLUMNS)
    lineups=_read(lineups_path,LINEUP_COLUMNS+[c for c in ("competition_name","season_name") if c in pq.ParquetFile(lineups_path).schema_arrow.names])
    metadata=_read(metadata_path,["match_id","competition_name","season_name"])
    scan,observed,unmatched,roster,actor_matches,event_counts=scan_events(events_path,crosswalk,candidates,lineups,metadata,batch_size=batch_size,scratch_dir=scratch_dir)
    original_m=canonical(_read(original_minutes_path,MINUTE_COLUMNS),allow_duplicates=True)
    original_r=canonical(_read(original_recovery_path,RECOVERY_COLUMNS),recovery=True,allow_duplicates=True)
    original_summary={"minute_rows":len(original_m),"recovery_rows":len(original_r),
        "duplicate_minute_keys":int(original_m.duplicated(PLAYER_KEYS).sum()),
        "duplicate_recovery_keys":int(original_r.duplicated(RECOVERY_KEYS).sum()),
        "target_duplicate_recovery_keys":int(target(original_r).duplicated(RECOVERY_KEYS).sum()),
        "conflicting_recovery_contexts":int(original_r.groupby(PLAYER_KEYS)[["position_group","minutes","matches"]].nunique(dropna=False).gt(1).any(axis=1).sum())}
    m=target(canonical(minutes)); r=target(canonical(recovery,recovery=True))
    paired=r.merge(observed,on=RECOVERY_KEYS,how="outer",validate="one_to_one",indicator=True)
    paired["local_count_agrees"]=paired._merge.eq("both") & paired["count"].eq(paired.observed_count)
    discrepancies=paired.loc[~paired.local_count_agrees,[*RECOVERY_KEYS,"count","observed_count","_merge"]].copy()
    roster_groups={k:set(map(int,g.match_id)) for k,g in roster.groupby(PLAYER_KEYS)}
    candidates["observed_actor_matches"]=[len(actor_matches.get(tuple(row),set())) for row in candidates[PLAYER_KEYS].itertuples(index=False,name=None)]
    candidates["local_lineup_matches"]=[len(roster_groups.get(tuple(row),set())) for row in candidates[PLAYER_KEYS].itertuples(index=False,name=None)]
    candidates["observed_events"]=[event_counts.get(tuple(row),0) for row in candidates[PLAYER_KEYS].itertuples(index=False,name=None)]
    candidates["lineup_match_count_agrees"]=candidates.local_lineup_matches.eq(candidates.delivered_matches)
    potential=candidates.loc[candidates.delivered_rules_eligible]
    transfer=potential.loc[potential.duplicated(["player_id","season_name"],keep=False)]
    all_transfer=candidates.loc[candidates.duplicated(["player_id","season_name"],keep=False)]
    ckeys=_keyset(candidates,PLAYER_KEYS)
    candidate_rec=paired.loc[[tuple(row) in ckeys for row in paired[PLAYER_KEYS].itertuples(index=False,name=None)]]
    # Stint shape diagnostics only: no inferred final-whistle timing or minutes.
    roster_candidates=roster.loc[[tuple(row) in ckeys for row in roster[PLAYER_KEYS].itertuples(index=False,name=None)]].copy()
    quality={"candidate_lineup_rows":len(roster_candidates),"missing_to_time_rows":int(roster_candidates.to_time.isna().sum()),
        "missing_from_time_rows":int(roster_candidates.from_time.isna().sum()),
        "missing_position_rows":int(roster_candidates.position.isna().sum()),
        "cross_period_rows":int((roster_candidates.from_period.notna()&roster_candidates["to_period"].notna()&roster_candidates.from_period.ne(roster_candidates["to_period"])).sum()),
        "independent_exposure_alignment":"NOT ESTABLISHED; delivered aggregate match counts do not prove aligned minute ledgers"}
    open_stints=roster_candidates.position.notna()&roster_candidates.to_time.isna()
    quality.update({"open_active_stint_rows":int(open_stints.sum()),
        "open_final_whistle_rows":int((open_stints&roster_candidates.end_reason.eq("Final Whistle")).sum()),
        "candidate_contexts_with_open_active_stints":len(roster_candidates.loc[open_stints,PLAYER_KEYS].drop_duplicates()),
        "bench_positionless_rows":int(roster_candidates.position.isna().sum())})
    quality["contributor_90min_compatibility"]=lineup_exposure_compatibility(candidates,roster_candidates)
    zero_rows=r.loc[r["count"].eq(0)].merge(candidates[[*PLAYER_KEYS,"delivered_rules_eligible"]],on=PLAYER_KEYS,validate="many_to_one")
    by_role=[]
    for (league,group),g in candidates.groupby(["competition_name","score_group"],sort=True):
        by_role.append({"competition_name":league,"score_group":group,"candidates":len(g),
            "under_900":int(g.under_900.sum()),"zero_minutes":int(g.zero_minutes.sum()),"missing_minutes":int(g.missing_minutes.sum()),
            "complete_components":int(g.complete_components.sum()),"unreportable":int((~g.all_reportable).sum()),
            "incomplete_delivered_coverage":int((~g.delivered_full_coverage).sum()),
            "arithmetic_ok":int(g.arithmetic_ok.sum()),"delivered_rules_eligible":int(g.delivered_rules_eligible.sum()),
            "ambiguous_role_ties":int(g.tied_groups.gt(1).sum()),"production_verified":0})
    summary={"scope":{"season_name":SEASON,"competitions":list(LEAGUES),"groups":{"MID":["DM","CM"],"CB":["CB"]},"minimum_minutes":MIN_MINUTES},
        "classification":"STRUCTURALLY VALID checks / PROVISIONAL identity / production BLOCKED — NOT ESTABLISHED",
        "production_scoring_ready":False,"production_verified_contexts":0,
        "scan":scan,"corrected_recovery_integrity":integrity,
        "refresh_minutes_comparison":compare_tables(minutes,refreshed_minutes),
        "refresh_recovery_comparison":compare_tables(recovery,refreshed_recovery,recovery=True),
        "original_comparison_only":original_summary,
        "target_delivery":{"minute_contexts":len(m),"recovery_rows":len(r),"recovery_contexts":len(r[PLAYER_KEYS].drop_duplicates()),
            "positions":{str(k):int(v) for k,v in m.position_group.value_counts().items()},
            "zero_minute_contexts":int(m.minutes.eq(0).sum()),"missing_minutes":int(m.minutes.isna().sum()),
            "role_minute_sum_disagreements":int((~np.isclose(m[ROLE_MINUTES].sum(axis=1),m.minutes,rtol=1e-9,atol=1e-9)).sum())},
        "target_delivery_by_league":[{"competition_name":league,"minute_contexts":int(m.competition_name.eq(league).sum()),
            "recovery_rows":int(r.competition_name.eq(league).sum()),
            "recovery_contexts":len(r.loc[r.competition_name.eq(league),PLAYER_KEYS].drop_duplicates()),
            "zero_minute_contexts":int((m.competition_name.eq(league)&m.minutes.eq(0)).sum())} for league in LEAGUES],
        "candidate_counts":{"total":len(candidates),"MID":int(candidates.score_group.eq("MID").sum()),"CB":int(candidates.score_group.eq("CB").sum()),
            "under_900":int(candidates.under_900.sum()),"complete_components":int(candidates.complete_components.sum()),
            "missing_components":int((~candidates.complete_components).sum()),"unreportable":int((~candidates.all_reportable).sum()),
            "incomplete_delivered_coverage":int((~candidates.delivered_full_coverage).sum()),"delivered_rules_eligible":len(potential),
            "unverified_identity_coverage_exposure":len(candidates),"potential_transfer_contexts":len(transfer),
            "all_candidate_transfer_contexts":len(all_transfer),"all_candidate_transfer_player_ids":sorted(map(int,all_transfer.player_id.unique())),
            "potential_transfer_player_ids":sorted(map(int,transfer.player_id.unique())),
            "lineup_match_count_disagreements":int((~candidates.lineup_match_count_agrees).sum())},
        "by_league_role":by_role,"lineup_exposure_shape":quality,
        "local_count_reconciliation":{"label":"local source versus delivered totals; NOT independent full-season scope verification",
            "all_target_shared_category_rows":int(paired._merge.eq("both").sum()),
            "all_target_delivered_only_rows":int(paired._merge.eq("left_only").sum()),"all_target_source_only_rows":int(paired._merge.eq("right_only").sum()),
            "all_target_count_disagreements":int((paired._merge.eq("both")&~paired.local_count_agrees).sum()),
            "candidate_shared_rows":int(candidate_rec._merge.eq("both").sum()),"candidate_delivered_only_rows":int(candidate_rec._merge.eq("left_only").sum()),
            "candidate_count_disagreements":int((candidate_rec._merge.eq("both")&~candidate_rec.local_count_agrees).sum())},
        "outstanding_requirements":["independently supported expected fixture/context coverage and source acquisition/failure accounting",
            "D1-compliant identity/context evidence beyond delivered consistency and contributor-reported lineage",
            "validated full-season numerator and exposure match ledgers with unresolved/open stint timing addressed",
            "per-component reportability evidence beyond delivered flags", "explicit transfer reference-context decisions where applicable"]}
    summary["local_count_reconciliation"].update({"candidate_delivered_zero_rows":len(zero_rows),
        "candidate_delivered_zero_contexts":len(zero_rows[PLAYER_KEYS].drop_duplicates()),
        "qualified_delivered_zero_rows":int(zero_rows.delivered_rules_eligible.sum())})
    return ReadinessResult(summary,candidates,unmatched,discrepancies)


def main(argv=None):
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("events","lineups","crosswalk","minutes","recovery","refresh-minutes","refresh-recovery","metadata","original-minutes","original-recovery"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument("--batch-size",type=int,default=65536)
    parser.add_argument("--scratch-dir",type=Path)
    parser.add_argument("--list-candidates",action="store_true")
    parser.add_argument("--list-matches",action="store_true")
    args=parser.parse_args(argv)
    kwargs={name+"_path":value for name,value in vars(args).items() if name not in ("batch_size","scratch_dir","list_candidates","list_matches")}
    try:
        result=audit_files(**kwargs,batch_size=args.batch_size,scratch_dir=args.scratch_dir)
    except (ValueError,OSError) as exc:
        parser.exit(1,f"Readiness audit rejected: {exc}\n")
    view=dict(result.summary)
    view["scan"]=dict(view["scan"])
    view["scan"]["leagues"]=[{k:v for k,v in row.items() if args.list_matches or k!="match_ids"} for row in view["scan"]["leagues"]]
    print(json.dumps(view,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False))
    print("Unresolved original name/context keys:")
    print(result.unmatched.to_string(index=False))
    print("Local count discrepancies (no assumption of independent season completeness):")
    print(result.discrepancies.head(20).to_string(index=False))
    print(f"Showing up to 20 of {len(result.discrepancies)} discrepancy rows; full ledger available from audit_files().")
    if args.list_candidates:
        print("Exact provisional candidate ledger — NOT production eligible:")
        print(result.candidates.to_string(index=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
