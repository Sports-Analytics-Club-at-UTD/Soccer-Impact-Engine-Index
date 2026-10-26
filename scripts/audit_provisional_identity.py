"""Read-only, bounded provisional matching; never a production trust attestation.

Run from the repository root with python -B -m scripts.audit_provisional_identity.
No ingestion, metric calculations, evidence promotion or output files.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import pandas as pd
import pyarrow.parquet as pq

from src.identity import (
    CONTEXT, NAME_KEYS, PLAYER_KEYS, IdentityError, _columns, _ids, _text,
    normalize_player_names, normalize_team_names, prepare_crosswalk,
    resolve_events, validate_population,
)

EVENT_COLUMNS = ["id", "match_id", "player", *CONTEXT, "type"]
MAPPING_COLUMNS = [*NAME_KEYS, "player_id"]


@dataclass
class ProvisionalLookup:
    lookup: pd.DataFrame
    observations: pd.DataFrame
    conflicts: pd.DataFrame
    summary: dict


@dataclass
class ProvisionalAudit:
    events: pd.DataFrame
    lookup: ProvisionalLookup
    unmatched: pd.DataFrame
    summary: dict


def prepare_provisional_lookup(source):
    """Count repeats, quarantine every conflicting key, retain original spellings.

    Invalid fields fail before deduplication. Reuse M2A's exact ID/text semantics;
    no name aliases beyond its existing normalization are introduced.
    """
    _columns(source, MAPPING_COLUMNS, "provisional crosswalk")
    rows = source[MAPPING_COLUMNS].copy(deep=True).reset_index(drop=True)
    rows["original_player_name"] = rows.player_name_raw.copy()
    rows["player_id"] = _ids(rows.player_id, "provisional crosswalk.player_id")
    rows["team"] = normalize_team_names(rows.team)
    rows["player_name_raw"] = normalize_player_names(rows.player_name_raw)
    for column in NAME_KEYS:
        _text(rows[column], f"provisional crosswalk.{column}")
    mappings = rows[MAPPING_COLUMNS].drop_duplicates()
    ambiguous = mappings.groupby(NAME_KEYS, dropna=False).player_id.transform("nunique").gt(1)
    conflict_keys = mappings.loc[ambiguous, NAME_KEYS].drop_duplicates()
    affected = pd.MultiIndex.from_frame(rows[NAME_KEYS]).isin(
        pd.MultiIndex.from_frame(conflict_keys))
    rows["provisional_status"] = "usable"
    rows.loc[affected, "provisional_status"] = "conflicting"
    lookup = prepare_crosswalk(mappings.loc[~ambiguous]).sort_values(NAME_KEYS).reset_index(drop=True)
    return ProvisionalLookup(lookup, rows, rows.loc[affected].copy(), {
        "source_rows": len(rows),
        "normalized_mapping_rows": len(mappings),
        "normalized_key_count": len(mappings[NAME_KEYS].drop_duplicates()),
        "duplicate_identical_mapping_rows": len(rows) - len(mappings),
        "conflicting_source_keys": len(conflict_keys),
        "conflicting_source_rows": int(affected.sum()),
        "usable_lookup_rows": len(lookup),
        "production_verified": False,
    })


def audit_provisional(events, crosswalk, population):
    """Caller-authorized provisional lookup through unchanged M2A strict=False.

    No D1 evidence objects or VERIFIED attestations are created. Supplied event
    player IDs are rejected: this diagnostic measures delivered lookup matches.
    Missing actor names survive as unresolved; invalid keys/IDs fail explicitly.
    """
    _columns(events, EVENT_COLUMNS, "events")
    if "player_id" in events:
        raise IdentityError("provisional audit requires events without supplied player_id")
    _ids(events.match_id, "events.match_id")
    lookup = prepare_provisional_lookup(crosswalk)
    selected = validate_population(population)
    result = resolve_events(events, lookup.lookup, selected, strict=False)
    out = result.events
    names = out[CONTEXT].copy()
    names["player_name_raw"] = normalize_player_names(out.player)
    conflict_keys = lookup.conflicts[NAME_KEYS].drop_duplicates()
    conflicts = pd.MultiIndex.from_frame(names[NAME_KEYS]).isin(
        pd.MultiIndex.from_frame(conflict_keys))
    missing_names = names.player_name_raw.isna() | names.player_name_raw.eq("")
    unresolved = out.identity_status.eq("unresolved")
    details = names.loc[unresolved].copy()
    details["reason"] = "no_exact_provisional_mapping"
    details.loc[conflicts[unresolved.to_numpy()], "reason"] = "conflicting_source_key"
    details.loc[missing_names.loc[unresolved], "reason"] = "missing_actor_name"
    unmatched = details.groupby([*NAME_KEYS, "reason"], dropna=False).size().rename("events").reset_index()
    same_order = out.id.tolist() == events.id.tolist() and out.index.equals(events.index)
    conserved = len(out) == len(events) == sum(result.counts.values())
    if not conserved or not same_order or out.id.duplicated().any():
        raise IdentityError("provisional audit changed event count, uniqueness or order")
    return ProvisionalAudit(out, lookup, unmatched, {
        "label": "PROVISIONAL MATCHING RESULT",
        "production_verified": False,
        "population_contexts": len(selected),
        "total_events": len(events),
        "unique_event_ids": int(out.id.nunique()),
        "events_matched_to_ids": int(out.player_id.notna().sum()),
        "matched_percent": 100 * int(out.player_id.notna().sum()) / len(out) if len(out) else None,
        **result.counts,
        "events_affected_by_conflicting_keys": int(conflicts.sum()),
        "missing_actor_names": int(missing_names.sum()),
        "invalid_identity_fields": 0,  # Invalid input fails; no rows are dropped/repaired.
        "duplicate_joins": 0,
        "unmatched_name_context_keys": len(unmatched),
        "row_count_conserved": conserved,
        "original_order_preserved": same_order,
    })


def audit_files(*, events_path, crosswalk_path, population_path, limit=4096):
    """Read a single bounded Arrow prefix with explicit paths; no file writes.

    A single prefix frame validates event-ID uniqueness across any row groups
    traversed. No streaming mode or unbounded/full-table option is provided.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    for path in (events_path, crosswalk_path, population_path):
        if not Path(path).is_file():
            raise FileNotFoundError(f"Required input unavailable: {path}")
    crosswalk = pq.read_table(crosswalk_path, columns=MAPPING_COLUMNS).to_pandas()
    population = pq.read_table(population_path, columns=PLAYER_KEYS).to_pandas()
    pieces, remaining = [], limit
    for batch in pq.ParquetFile(events_path).iter_batches(
            batch_size=min(limit, 65536), columns=EVENT_COLUMNS):
        piece = batch.slice(0, remaining).to_pandas()
        pieces.append(piece)
        remaining -= len(piece)
        if remaining == 0:
            break
    events = (pd.concat(pieces, ignore_index=True) if pieces
              else pd.DataFrame(columns=EVENT_COLUMNS))
    return audit_provisional(events, crosswalk, population)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--population", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=4096)
    args = parser.parse_args(argv)
    try:
        result = audit_files(events_path=args.events, crosswalk_path=args.crosswalk,
                             population_path=args.population, limit=args.limit)
    except (IdentityError, ValueError, OSError) as exc:
        print(f"Diagnostic rejected: {exc}", file=sys.stderr)
        return 1
    print("PROVISIONAL MATCHING RESULT — NOT YET PRODUCTION-VERIFIED")
    print("Crosswalk:", args.crosswalk)
    print("Events:", args.events, "Population:", args.population)
    for label, summary in [("Lookup", result.lookup.summary), ("Events", result.summary)]:
        print(label)
        for key, value in summary.items():
            print(f"  {key}: {value}")
    print("Conflicting source observations:")
    print(result.lookup.conflicts.to_string(index=False))
    print("Unmatched names/contexts:")
    print(result.unmatched.to_string(index=False))
    print("No evidence promotion, metric calculations or output files. Sample coverage only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
