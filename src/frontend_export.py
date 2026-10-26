"""Strict, pure JSON contract for M4B0 raw measurements; no scoring policy."""
import math
from numbers import Integral, Real

import numpy as np
import pandas as pd

from src.identity import IdentityError, PLAYER_KEYS, validate_population
from src.scorecard import (DESCRIPTORS, PASS_COUNTS, PASS_FIELDS, PRESS_COUNTS,
                           PRESS_FIELDS, RECOVERY_PREFIXES, ScorecardResult)

SCHEMA_VERSION = "soccer-scorecard/v1"
LIMITATIONS = ["Source-row presence does not establish complete source coverage.",
               "Calibration completeness is caller-attested, not independently verified.",
               "No complete production player population or approved scoring is claimed."]


class FrontendExportError(ValueError):
    """Unsupported scorecard schema or unsafe JSON value/provenance."""


def _definitions():
    definitions = {}

    def add(name, kind, unit, component=None):
        definitions[name] = dict(kind=kind, unit=unit, component=component)

    for c in PLAYER_KEYS:
        add(c, "id" if c == "player_id" else "text", "identity")
    for c in DESCRIPTORS:
        add(c, "integer" if c == "matches" else "number" if c == "minutes" else "text",
            "matches" if c == "matches" else "minutes" if c == "minutes" else "label")
    for prefix in RECOVERY_PREFIXES.values():
        for suffix, kind, unit in [("count", "integer", "events"), ("per90", "number", "events/90min"),
                                   ("rate_status", "status", "status"), ("minutes", "number", "minutes"),
                                   ("present", "boolean", "presence")]:
            add(f"{prefix}_{suffix}", kind, unit, prefix)
    for c in PRESS_FIELDS:
        add(c, "integer" if c in PRESS_COUNTS else "number",
            "events" if c in PRESS_COUNTS else "percent", "press")
    add("press_minutes", "number", "minutes", "press")
    add("press_present", "boolean", "presence", "press")
    for c in PASS_FIELDS:
        unit = ("events" if c in PASS_COUNTS else "difficulty_weighted_yards" if c == "value_sum"
                else "percent" if c == "prog_completion_pct" else
                "difficulty_weighted_yards/90min" if c == "pass_value_p90" else "events/90min")
        add(c, "integer" if c in PASS_COUNTS else "number", unit, "passing")
    for c, kind, unit in [("passing_minutes", "number", "minutes"),
                           ("passing_rate_status", "status", "status"),
                           ("passing_difficulty_scope", "text", "reference_scope"),
                           ("passing_difficulty_complete", "boolean", "caller_attestation"),
                           ("passing_present", "boolean", "presence")]:
        add(c, kind, unit, "passing")
    return definitions


FIELD_DEFINITIONS = _definitions()
COMPONENTS = [*RECOVERY_PREFIXES.values(), "press", "passing"]


def _scalar(value, name, definition):
    if not pd.api.types.is_scalar(value):
        raise FrontendExportError(f"{name}: scalar required")
    if pd.isna(value):
        return None
    kind = definition["kind"]
    if kind in ["text", "status"]:
        if not isinstance(value, str):
            raise FrontendExportError(f"{name}: string required")
        if kind == "status" and value not in ["ok", "zero_minutes", "missing_minutes"]:
            raise FrontendExportError(f"{name}: unknown rate status")
        return value
    if kind == "boolean":
        if not isinstance(value, (bool, np.bool_)):
            raise FrontendExportError(f"{name}: boolean required")
        return bool(value)
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise FrontendExportError(f"{name}: real numeric value required")
    if not math.isfinite(value) or value < 0:
        raise FrontendExportError(f"{name}: finite nonnegative value required")
    if kind == "integer":
        if value != int(value) or value > 2**63 - 1 or (not isinstance(value, Integral) and value > 2**53 - 1):
            raise FrontendExportError(f"{name}: exact signed int64 count required")
        return str(int(value))  # Decimal strings survive JavaScript's numeric boundary.
    if definition["unit"] == "percent" and value > 100:
        raise FrontendExportError(f"{name}: percentage exceeds 100")
    return float(value)


def export_scorecard(result):
    """Return a fresh versioned JSON-compatible object, without I/O or mutation.

    Accept only an assembled ScorecardResult. Structural validation protects
    against unsafe changes since assembly; it cannot certify source coverage.
    """
    if not isinstance(result, ScorecardResult) or not isinstance(result.scorecard, pd.DataFrame):
        raise FrontendExportError("ScorecardResult required")
    table = result.scorecard
    required = set(FIELD_DEFINITIONS).difference(DESCRIPTORS)
    if not table.columns.is_unique:
        raise FrontendExportError("scorecard: duplicate column labels")
    missing, extra = required.difference(table), set(table).difference(FIELD_DEFINITIONS)
    if missing or extra:
        raise FrontendExportError(f"scorecard: missing fields {sorted(missing)}; unsupported fields {sorted(extra)}")
    try:
        keys = validate_population(table).reset_index(drop=True)
    except IdentityError as exc:
        raise FrontendExportError(str(exc)) from exc
    rows = table.copy(deep=True).reset_index(drop=True)
    for c in PLAYER_KEYS:
        rows[c] = keys[c]
    rows = rows.sort_values(PLAYER_KEYS, kind="stable")
    # Copy only available reference metadata, never opaque caller diagnostics.
    if not isinstance(result.diagnostics, dict):
        raise FrontendExportError("assembly diagnostics required")
    reference = result.diagnostics.get("passing_reference")
    if reference is not None:
        expected = {"scope", "declared_complete", "independently_verified"}
        if (not isinstance(reference, dict) or set(reference) != expected
                or not isinstance(reference["scope"], str) or not reference["scope"].strip()
                or reference["declared_complete"] is not True
                or reference["independently_verified"] is not False):
            raise FrontendExportError("invalid passing calibration provenance")
        reference = dict(reference)
    players = []
    for source in rows.to_dict("records"):
        row = {c: (str(int(source[c])) if c == "player_id" else
                   _scalar(source.get(c), c, definition)) for c, definition in FIELD_DEFINITIONS.items()}
        for component in COMPONENTS:
            present = row[f"{component}_present"]
            if present is None:
                raise FrontendExportError(f"{component}: presence flag cannot be missing")
            fields = [c for c, spec in FIELD_DEFINITIONS.items()
                      if spec["component"] == component and c != f"{component}_present"]
            if not present and any(row[c] is not None for c in fields):
                raise FrontendExportError(f"{component}: absent row has metric values")
            if present and any(row[c] is None for c in fields if FIELD_DEFINITIONS[c]["kind"] == "integer"):
                raise FrontendExportError(f"{component}: present row missing counts")
            if present and component != "press":
                minute_field = "passing_minutes" if component == "passing" else f"{component}_minutes"
                status_field = "passing_rate_status" if component == "passing" else f"{component}_rate_status"
                minutes = row[minute_field]
                status = "missing_minutes" if minutes is None else "zero_minutes" if minutes == 0 else "ok"
                if row[status_field] != status:
                    raise FrontendExportError(f"{component}: inconsistent exposure/status")
        if row["passing_present"] and (reference is None
                or row["passing_difficulty_scope"] != reference["scope"]
                or row["passing_difficulty_complete"] is not True):
            raise FrontendExportError("present passing row requires matching calibration provenance")
        minute_fields = ["minutes", *[f"{p}_minutes" for p in RECOVERY_PREFIXES.values()],
                         "press_minutes", "passing_minutes"]
        if len({row[c] for c in minute_fields if row[c] is not None}) > 1:
            raise FrontendExportError("conflicting minutes across components")
        players.append(row)
    return {"schema_version": SCHEMA_VERSION, "measurement_type": "raw_metrics",
            "metadata": {"canonical_keys": list(PLAYER_KEYS), "integer_encoding": "decimal_string",
                         "fields": _definitions(), "coverage_status": "unverified",
                         "limitations": list(LIMITATIONS), "passing_reference": reference},
            "players": players}
