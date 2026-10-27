"""Pure diagnostic profiles from validated D2B results; no production export/I/O.

Integer IDs/counts use decimal strings. This separate contract is deliberately
incompatible with soccer-scorecard/v1 and makes no production trust attestation.
"""
from __future__ import annotations

import math
from numbers import Integral, Real

import pandas as pd

from src.identity import PLAYER_KEYS, _ids, normalize_player_names, validate_population
from src.metrics.press_actions import COUNT_COLS, RATE_COLS, add_completion_rates
from src.metrics.recovery_coverage import EVENT_TYPES

SCHEMA_VERSION = "soccer-provisional-profiles/v1"
STATUS = "DIAGNOSTIC / PROVISIONAL / NOT PRODUCTION VERIFIED"


class ProfileContractError(ValueError):
    """An input no longer satisfies D2B scope, count, identity or exposure checks."""


def _integer(value):
    if (isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)
            or value < 0 or int(value) != value or value > 2**63 - 1
            or (not isinstance(value, Integral) and value > 2**53 - 1)):
        raise ProfileContractError("exact nonnegative signed-int64 count required")
    return str(int(value))


def _number(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0:
        raise ProfileContractError("finite nonnegative number or missing value required")
    return float(value)


def _part(table, key):
    selected = table
    for column, value in zip(PLAYER_KEYS, key):
        selected = selected.loc[selected[column].eq(value)]
    return selected


def _compare(actual, expected, keys, label):
    if (not isinstance(actual, pd.DataFrame) or not actual.columns.is_unique
            or set(actual.columns) != set(expected.columns) or actual.duplicated(keys).any()):
        raise ProfileContractError(f"{label}: duplicate keys or incompatible columns")
    try:
        for column in ("player_id", "match_id"):
            if column in actual:
                _ids(actual[column], f"{label}.{column}")
        for column in ("count", *COUNT_COLS, "pressured_actions", "successful_pressured_actions"):
            if column in actual:
                for value in actual[column]:
                    _integer(value)
    except ValueError as exc:
        raise ProfileContractError(f"{label}: invalid exact identity/count") from exc
    try:
        pd.testing.assert_frame_equal(actual[expected.columns].sort_values(keys).reset_index(drop=True),
                                      expected.sort_values(keys).reset_index(drop=True),
                                      check_dtype=False, check_exact=True)
    except AssertionError as exc:
        raise ProfileContractError(f"{label}: scope/count/value disagreement with D2B evidence") from exc


def _validate(audit):
    # Local import keeps this diagnostic dependency out of existing production
    # assembly/export paths. Revalidation below performs no file/network I/O.
    from scripts.audit_match_scoped_metrics import MatchAudit, MATCH_PLAYER, match_metrics
    from scripts.audit_provisional_identity import MAPPING_COLUMNS

    if not isinstance(audit, MatchAudit):
        raise ProfileContractError("validated D2B MatchAudit required")
    if (audit.summary.get("authoritative_feed_complete") is not False
            or audit.pooled.identity.summary.get("production_verified") is not False
            or audit.pooled.identity.lookup.summary.get("production_verified") is not False
            or audit.pooled.summary.get("production_verified") is not False):
        raise ProfileContractError("provisional evidence cannot be promoted to verified")
    resolved = audit.pooled.identity.events
    if (resolved.identity_status.eq("unresolved").any()
            or resolved.id.tolist() != audit.events.id.tolist()):
        raise ProfileContractError("unresolved identities or changed event order")
    selected = resolved.loc[resolved.identity_status.eq("selected"), PLAYER_KEYS].drop_duplicates()
    # The selected identities already established by D2B define membership only
    # for revalidating these supplied events, not a new project-wide population.
    population = validate_population(selected).assign(minutes=float("nan"))
    contexts = audit.lineups[["match_id", "competition_name", "season_name"]].drop_duplicates()
    try:
        expected = match_metrics(audit.events,
            audit.pooled.identity.lookup.observations[MAPPING_COLUMNS], population,
            audit.lineups, contexts,
            local_collection_complete=audit.summary.get("local_collection_complete"))
    except ValueError as exc:
        raise ProfileContractError(f"D2B evidence rejected: {exc}") from exc
    if set(audit.per_match) != set(expected.per_match):
        raise ProfileContractError("per-match inputs do not cover exactly the event window")
    if not resolved[PLAYER_KEYS + ["identity_status"]].reset_index(drop=True).equals(
            expected.pooled.identity.events[PLAYER_KEYS + ["identity_status"]].reset_index(drop=True)):
        raise ProfileContractError("canonical identity or population membership changed")
    for supplied, fresh in [(audit.pooled, expected.pooled),
                            *[(audit.per_match[mid], expected.per_match[mid]) for mid in sorted(expected.per_match)]]:
        if supplied.summary.get("production_verified") is not False:
            raise ProfileContractError("metric provenance cannot be promoted to verified")
        for attribute, keys in [("recovery", [*PLAYER_KEYS, "event_type"]),
                                ("by_zone", [*PLAYER_KEYS, "event_type", "zone"]),
                                ("press", PLAYER_KEYS)]:
            _compare(getattr(supplied, attribute), getattr(fresh, attribute), keys, attribute)
        if supplied.identity.events.id.tolist() != fresh.identity.events.id.tolist():
            raise ProfileContractError("per-match event membership/order changed")
    for attribute, keys in [("exposure", MATCH_PLAYER),
                            ("recovery_per90", [*MATCH_PLAYER, "event_type"]),
                            ("pooled_recovery_per90", [*PLAYER_KEYS, "event_type"])]:
        _compare(getattr(audit, attribute), getattr(expected, attribute), keys, attribute)
    return expected, selected.sort_values(PLAYER_KEYS).reset_index(drop=True)


def _exposure(rows, complete):
    records, reasons = [], set()
    aligned = complete and len(rows) > 0
    for row in rows.sort_values("match_id").to_dict("records"):
        valid = row["exposure_status"] in ("aligned_explicit_stints", "bench_no_stint")
        aligned = aligned and valid
        row_reasons = row["reasons"].split(";") if row["reasons"] else []
        reasons.update(row_reasons)
        records.append({"match_id": str(int(row["match_id"])), "status": row["exposure_status"],
                        "aligned_minutes": _number(row["minutes"]) if valid and complete else None,
                        "reasons": row_reasons})
    if not complete:
        reasons.add("local_match_collection_not_established")
    if not len(rows):
        reasons.add("no_matching_lineup_exposure")
    return {"match_ids": [r["match_id"] for r in records], "match_records": records,
            "status": "aligned" if aligned else "unsupported",
            "aligned_minutes": float(rows.minutes.sum()) if aligned else None,
            "reasons": sorted(reasons)}


def _recovery(counts, zones, rates, scope, exposure):
    result = {}
    for category in EVENT_TYPES:
        row = counts.loc[counts.event_type.eq(category)]
        rate = rates.loc[rates.event_type.eq(category)]
        zone = zones.loc[zones.event_type.eq(category)].sort_values("zone")
        present = len(row) == 1
        count = row.iloc[0]["count"] if present else None
        value = _number(rate.iloc[0].per90) if len(rate) else None
        available = present and value is not None
        reasons = ([] if available else ["missing_metric"] if not present else
                   exposure["reasons"] or ["nonpositive_or_unavailable_aligned_minutes"])
        result[category] = {
            "status": "observed" if present else "missing", "count": _integer(count) if present else None,
            "match_ids": list(scope),
            "zone_counts": [{"zone": int(r.zone), "count": _integer(r.count)}
                            for r in zone.itertuples(index=False)] if present else None,
            "unknown_zone_count": _integer(int(count) - int(zone["count"].sum())) if present else None,
            "per90": {"status": "available" if available else "unsupported",
                      "available": available, "value": value, "reasons": list(reasons),
                      "numerator_match_ids": list(scope),
                      "denominator_match_ids": list(scope) if available else None,
                      "aligned_minutes": exposure["aligned_minutes"] if available else None},
        }
    return result


def _press(table):
    if table.empty:
        return {"status": "missing", "counts": {c: None for c in
                [*COUNT_COLS, "pressured_actions", "successful_pressured_actions"]},
                "percentages": {c: {"status": "missing", "value": None} for c in RATE_COLS}}
    # Always derive from completions/attempts using the existing M3A helper.
    counts = table[COUNT_COLS].copy()
    row = add_completion_rates(counts).to_dict("records")[0]
    return {"status": "observed", "counts": {c: _integer(row[c]) for c in
            [*COUNT_COLS, "pressured_actions", "successful_pressured_actions"]},
            "percentages": {c: {"status": "undefined_zero_attempts" if pd.isna(row[c]) else "observed",
                                 "value": _number(row[c])} for c in RATE_COLS}}


def build_profiles(audit, *, delivered_minutes=None):
    """Return fresh JSON-compatible diagnostic records; no mutation or output writes.

    Revalidate mutable D2B evidence and conservation. Optional delivered minutes
    supply wider-scope ambiguity metadata only, NEVER per90 denominators.
    """
    from src.recovery import _minutes

    valid, contexts = _validate(audit)
    exposure_source = _minutes(delivered_minutes) if delivered_minutes is not None else None
    complete = valid.summary["local_collection_complete"]
    window = [str(mid) for mid in sorted(valid.per_match)]
    profiles = []
    for values in contexts.itertuples(index=False, name=None):
        identity = dict(zip(PLAYER_KEYS, values))
        identity["player_id"] = str(int(identity["player_id"]))
        events = _part(valid.pooled.identity.events, values)
        names = sorted(normalize_player_names(events.player).dropna().unique().tolist())
        identity["player_name"] = names[0] if len(names) == 1 else None
        identity["observed_name_variants"] = names
        identity["name_source"] = "observed_event_actor_label"
        exposure_rows = _part(valid.exposure, values)
        exposure = _exposure(exposure_rows, complete)
        scope = exposure["match_ids"]
        observed = [str(int(mid)) for mid in sorted(events.match_id.unique())]
        if not set(observed).issubset(scope) or not set(scope).issubset(window):
            raise ProfileContractError("profile match scope lacks lineup or diagnostic membership")
        source = _part(exposure_source, values) if exposure_source is not None else None
        delivered = _number(source.iloc[0].minutes) if source is not None and len(source) else None
        source_status = ("not_supplied" if exposure_source is None else "missing" if delivered is None
                         else "zero" if delivered == 0 else "known_wider_scope")
        exposure["delivered_minutes"] = delivered
        exposure["delivered_minutes_status"] = source_status
        exposure["source_ambiguities"] = (["observed_activity_with_zero_delivered_minutes"]
                                         if source_status == "zero" else [])
        exposure["delivered_minutes_scope"] = "wider player/team/competition/season; never a denominator here"
        matches = []
        for mid in sorted(events.match_id.unique()):
            metric = valid.per_match[int(mid)]
            match_scope = [str(int(mid))]
            match_exposure = _exposure(exposure_rows.loc[exposure_rows.match_id.eq(mid)], complete)
            matches.append({"match_id": str(int(mid)), "scope_match_ids": match_scope,
                "observed_event_count": _integer(events.match_id.eq(mid).sum()),
                "recovery": _recovery(_part(metric.recovery, values), _part(metric.by_zone, values),
                    _part(valid.recovery_per90.loc[valid.recovery_per90.match_id.eq(mid)], values),
                    match_scope, match_exposure),
                "press": _press(_part(metric.press, values)), "exposure": match_exposure})
        profiles.append({"identity": identity, "verification_status": STATUS,
            "scope": {"included_match_ids": list(scope), "observed_match_ids": observed,
                      "observed_match_count": len(observed),
                      "observed_event_count": _integer(len(events))},
            "pooled": {"scope_match_ids": list(scope),
                "recovery": _recovery(_part(valid.pooled.recovery, values), _part(valid.pooled.by_zone, values),
                                       _part(valid.pooled_recovery_per90, values), scope, exposure),
                "press": _press(_part(valid.pooled.press, values)), "exposure": exposure},
            "matches": matches, "not_assessed_metric_families": ["progression"]})
    return {"schema_version": SCHEMA_VERSION, "verification_status": STATUS,
        "production_schema_compatible": False, "integer_encoding": "decimal_string",
        "units": {"counts": "events", "percentages": "percent_0_100", "aligned_minutes": "minutes",
                  "per90": "events/90min", "zones": "existing_3x3_120x80"},
        "canonical_keys": list(PLAYER_KEYS),
        "scope": {"match_ids": window, "local_collection_complete": complete,
                  "observed_match_count": len(window), "observed_event_count": _integer(len(valid.events)),
                  "local_event_coverage": "supplied D2B match window; all-local-rows attestation is not authoritative completeness",
                  "authoritative_feed_complete": False},
        "identity_provenance": "D1B-P caller-supplied provisional lookup; contributor-reported lineup/crosswalk lineage",
        "match_context_provenance": "event-derived; not an independent authoritative fixture manifest",
        "profiles": profiles}
