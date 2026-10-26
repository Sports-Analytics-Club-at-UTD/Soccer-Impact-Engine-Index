"""Pure, explicitly attested identity evidence and diagnostic coverage; no I/O."""
from dataclasses import dataclass

import pandas as pd

from src.identity import (CONTEXT, NAME_KEYS, PLAYER_KEYS, IdentityError, IdentityResult,
                          _ids, normalize_player_names, normalize_team_names,
                          prepare_crosswalk, resolve_events, validate_population)

VERIFIED = "VERIFIED_SOURCE_EVIDENCE"
DELIVERED = "DELIVERED_TABLE_CONSISTENCY_ONLY"
SYNTHETIC = "SYNTHETIC_TEST_EVIDENCE"
STRENGTHS = (VERIFIED, DELIVERED, SYNTHETIC)
MATCH_KEYS = ["match_id", "competition_name", "season_name"]
TEAM_MATCH_KEYS = ["match_id", *CONTEXT]
EVIDENCE_COLUMNS = ["source", "evidence_kind", "match_context_source", "match_context_kind",
                    "match_id", "original_player_name", *NAME_KEYS, "player_id"]


class IdentityEvidenceError(IdentityError):
    """Rejected evidence; details retain the records requiring review."""
    def __init__(self, message, details=None):
        self.details = details.copy(deep=True) if isinstance(details, pd.DataFrame) else details
        super().__init__(message)


@dataclass
class MatchContexts:
    contexts: pd.DataFrame
    source: str
    evidence_kind: str
    summary: dict


@dataclass
class LineupEvidence:
    rows: pd.DataFrame
    summary: dict


@dataclass
class CrosswalkEvidence:
    crosswalk: pd.DataFrame
    evidence: pd.DataFrame
    conflicts: pd.DataFrame
    summary: dict

    def require_unambiguous(self):
        if not self.conflicts.empty:
            raise IdentityEvidenceError("conflicting source evidence; season-level crosswalk is incomplete",
                                        self.conflicts)
        return self


@dataclass
class IdentityCoverage:
    identity: IdentityResult
    summary: dict
    breakdown: pd.DataFrame
    unresolved_names: pd.DataFrame
    conflicting_events: pd.DataFrame
    coverage: dict


def _columns(table, required, label):
    if not isinstance(table, pd.DataFrame) or not table.columns.is_unique:
        raise IdentityEvidenceError(f"{label}: DataFrame with unique columns required")
    missing = [c for c in required if c not in table]
    if missing:
        raise IdentityEvidenceError(f"{label}: missing columns {missing}")


def _labels(values, label):
    if not all(isinstance(v, str) and v.strip() for v in values):
        raise IdentityEvidenceError(f"{label}: nonblank strings required")


def _attestation(source, kind):
    if not isinstance(source, str) or not source.strip() or kind not in STRENGTHS:
        raise IdentityEvidenceError("explicit source label and supported evidence kind required")


def _sort(table, columns):
    return table.sort_values(columns, kind="stable", na_position="last").reset_index(drop=True)


def validate_match_contexts(contexts, *, source, evidence_kind):
    """Collapse identical observations with accounting; reject conflicting match IDs.

    evidence_kind is a caller's provenance attestation, never inferred from shape.
    M2A's exact-ID validator is shared for match IDs; no new ID coercion rules.
    """
    _attestation(source, evidence_kind)
    _columns(contexts, MATCH_KEYS, "match contexts")
    out = contexts[MATCH_KEYS].copy(deep=True).reset_index(drop=True)
    out["match_id"] = _ids(out.match_id, "match_id")
    for c in MATCH_KEYS[1:]:
        _labels(out[c], c)
    unique = out.drop_duplicates(MATCH_KEYS)
    clashes = unique.match_id.duplicated(keep=False)
    if clashes.any():
        raise IdentityEvidenceError("conflicting match-to-competition/season mappings", unique.loc[clashes])
    return MatchContexts(_sort(unique, MATCH_KEYS), source, evidence_kind,
                         {"input_rows": len(out), "matches": len(unique),
                          "consistent_repeat_rows": len(out) - len(unique)})


def validate_lineup_evidence(lineups, *, source, evidence_kind, match_contexts=None,
                             name_column="player_name"):
    """Validate direct lineup identity observations, independently of stint/role policy.

    Contexts may be supplied directly or joined from validated MatchContexts.
    Only independently attested verified sources on both sides can yield trusted
    entries. Bench rows are not filtered and exposure/roles are not reconstructed.
    """
    _attestation(source, evidence_kind)
    if name_column not in ["player_name", "player_name_raw"]:
        raise IdentityEvidenceError("name_column must identify an original player_name/player_name_raw field")
    _columns(lineups, ["match_id", "team", "player_id", name_column], "lineups")
    out = lineups[["match_id", "team", "player_id", name_column]].copy(deep=True).reset_index(drop=True)
    out = out.rename(columns={name_column: "original_player_name"})
    out["match_id"] = _ids(out.match_id, "lineups.match_id")
    out["player_id"] = _ids(out.player_id, "lineups.player_id")
    out["team"] = normalize_team_names(out.team)
    out["player_name_raw"] = normalize_player_names(out.original_player_name)
    _labels(out.player_name_raw, "lineups.player_name")
    direct = [c in lineups for c in MATCH_KEYS[1:]]
    if any(direct) and not all(direct):
        raise IdentityEvidenceError("lineups: partial competition/season context")
    if all(direct):
        for c in MATCH_KEYS[1:]:
            out[c] = lineups[c].reset_index(drop=True)
        # Direct source records must themselves associate each match uniquely.
        validate_match_contexts(out, source=source, evidence_kind=evidence_kind)
    if match_contexts is not None:
        if not isinstance(match_contexts, MatchContexts):
            raise IdentityEvidenceError("supply validated MatchContexts")
        if not all(direct) and match_contexts.evidence_kind != VERIFIED:
            raise IdentityEvidenceError("deriving lineup contexts requires a separately verified match association")
        mapping = validate_match_contexts(match_contexts.contexts, source=match_contexts.source,
                                           evidence_kind=match_contexts.evidence_kind).contexts
        joined = out.merge(mapping, on="match_id", how="left", validate="many_to_one",
                           indicator=True, suffixes=("", "_mapped"), sort=False)
        if len(joined) != len(out) or joined["_merge"].ne("both").any():
            raise IdentityEvidenceError("lineups: matches missing from context mapping", joined)
        if all(direct) and any(joined[c].ne(joined[f"{c}_mapped"]).any() for c in MATCH_KEYS[1:]):
            raise IdentityEvidenceError("lineup and supplied match contexts disagree", joined)
        out = joined[out.columns.tolist() + ([] if all(direct) else MATCH_KEYS[1:])].copy()
        context_source, context_kind = match_contexts.source, match_contexts.evidence_kind
    elif not all(direct):
        if len(out):
            raise IdentityEvidenceError("lineups without direct contexts require a verified match association")
        for c in MATCH_KEYS[1:]:
            out[c] = pd.Series(dtype="string")
        context_source, context_kind = source, evidence_kind
    else:
        context_source, context_kind = source, evidence_kind
    for c in MATCH_KEYS[1:]:
        _labels(out[c], c)
    out["source"], out["evidence_kind"] = source, evidence_kind
    out["match_context_source"], out["match_context_kind"] = context_source, context_kind
    out = _sort(out[EVIDENCE_COLUMNS], EVIDENCE_COLUMNS)
    return LineupEvidence(out, {"input_rows": len(out), "distinct_identity_observations": len(out.drop_duplicates()),
                               "consistent_repeat_rows": int(out.duplicated().sum())})


def build_identity_crosswalk(evidence):
    """Build M2A-compatible VERIFIED-only entries and quarantine all conflicting keys.

    Accept one validated LineupEvidence or a sequence thereof (including []).
    Repetition is explicit audit accounting, not arbitrary first-ID selection.
    Untrusted observations remain labeled in the ledger, never auto-promoted.
    """
    inputs = [evidence] if isinstance(evidence, LineupEvidence) else list(evidence)
    pieces = []
    for item in inputs:
        if not isinstance(item, LineupEvidence):
            raise IdentityEvidenceError("validated LineupEvidence required")
        # Revalidate public mutable result records before trusting them.
        _columns(item.rows, EVIDENCE_COLUMNS, "evidence")
        for (source, kind, context_source, context_kind), part in item.rows.groupby(
                ["source", "evidence_kind", "match_context_source", "match_context_kind"], dropna=False):
            _attestation(context_source, context_kind)
            checked = validate_lineup_evidence(part.rename(columns={"original_player_name": "player_name"}),
                                                source=source, evidence_kind=kind).rows
            if not checked.player_name_raw.equals(part.player_name_raw.reset_index(drop=True)):
                # Compare by original spelling/context rather than incoming row order below.
                expected = _sort(part, EVIDENCE_COLUMNS)
                if checked.player_name_raw.tolist() != expected.player_name_raw.tolist():
                    raise IdentityEvidenceError("evidence normalized spelling changed")
            checked["match_context_source"], checked["match_context_kind"] = context_source, context_kind
            pieces.append(checked)
    rows = (pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(columns=EVIDENCE_COLUMNS))
    rows["player_id"] = _ids(rows.player_id, "evidence.player_id")
    rows["match_id"] = _ids(rows.match_id, "evidence.match_id")
    rows = _sort(rows, EVIDENCE_COLUMNS)
    # Also reject contradictory match context across separately validated sources.
    if len(rows):
        validate_match_contexts(rows, source="combined evidence", evidence_kind=DELIVERED)
    observations = rows.drop_duplicates().reset_index(drop=True)
    ambiguous = observations.groupby(NAME_KEYS, dropna=False).player_id.transform("nunique").gt(1)
    conflicts = observations.loc[ambiguous].copy()
    trusted = observations.loc[~ambiguous & observations.evidence_kind.eq(VERIFIED)
                               & observations.match_context_kind.eq(VERIFIED)]
    crosswalk = prepare_crosswalk(trusted[[*NAME_KEYS, "player_id"]].drop_duplicates())
    crosswalk = _sort(crosswalk, NAME_KEYS + ["player_id"])
    observations["report_label"] = observations.evidence_kind
    observations.loc[observations.evidence_kind.eq(VERIFIED) & ~observations.match_context_kind.eq(VERIFIED),
                     "report_label"] = observations.match_context_kind
    observations.loc[ambiguous, "report_label"] = "CONFLICTING"
    conflicts["report_label"] = "CONFLICTING"
    # Keep original repeated records in the ledger; only the lookup and distinct
    # conflict support are deduplicated. A subsequent audit retains this accounting.
    rows["report_label"] = rows.evidence_kind
    rows.loc[rows.evidence_kind.eq(VERIFIED) & ~rows.match_context_kind.eq(VERIFIED),
             "report_label"] = rows.match_context_kind
    clash_keys = pd.MultiIndex.from_frame(conflicts[NAME_KEYS].drop_duplicates())
    rows.loc[pd.MultiIndex.from_frame(rows[NAME_KEYS]).isin(clash_keys), "report_label"] = "CONFLICTING"
    return CrosswalkEvidence(crosswalk, rows, _sort(conflicts, EVIDENCE_COLUMNS), {
        "input_rows": len(rows), "distinct_observations": len(observations),
        "consistent_repeat_rows": len(rows) - len(observations),
        "season_mapping_repeat_rows": len(trusted) - len(crosswalk),
        "trusted_crosswalk_rows": len(crosswalk), "conflicting_keys": len(conflicts[NAME_KEYS].drop_duplicates()),
        "withheld_untrusted_observations": int((~observations.evidence_kind.eq(VERIFIED)
                                                | ~observations.match_context_kind.eq(VERIFIED)).sum()),
        "evidence_labels": observations.report_label.value_counts().sort_index().to_dict(),
        "source_evidence_available": bool(len(observations)),
        "verified_source_observations": int((observations.evidence_kind.eq(VERIFIED)
                                              & observations.match_context_kind.eq(VERIFIED)).sum()),
    })


def _difference(left, right, keys):
    a, b = left[keys].drop_duplicates(), right[keys].drop_duplicates()
    joined = a.merge(b, on=keys, how="left", indicator=True, validate="one_to_one")
    return _sort(joined.loc[joined["_merge"].eq("left_only"), keys], keys)


def audit_identity_coverage(events, evidence, population, *, population_scope, expected_matches=None):
    """Retain every event through M2A strict=False; diagnostics only, never metrics.

    Source collisions are withheld and flagged. Conflicting supplied event IDs
    versus lookup IDs remain fatal under M2A; error details retain all input rows.
    Optional expected matches must be a verified independently supplied manifest.
    """
    if not isinstance(evidence, CrosswalkEvidence):
        raise IdentityEvidenceError("CrosswalkEvidence required")
    _labels(pd.Series([population_scope]), "population_scope")
    selected = validate_population(population)
    # Rebuild from provenance, rather than allow a mutated standalone lookup.
    checked = build_identity_crosswalk(LineupEvidence(evidence.evidence.drop(columns="report_label"), {}))
    try:
        identity = resolve_events(events, checked.crosswalk, selected, strict=False)
    except IdentityError as exc:
        raise IdentityEvidenceError(f"event audit rejected by M2A: {exc}", events) from exc
    resolved = identity.events.reset_index(drop=True)
    lookup_keys = pd.MultiIndex.from_frame(checked.crosswalk[NAME_KEYS])
    names = resolved[CONTEXT].copy()
    names["player_name_raw"] = normalize_player_names(resolved.player)
    crosswalk_match = pd.MultiIndex.from_frame(names[NAME_KEYS]).isin(lookup_keys)
    conflict_keys = pd.MultiIndex.from_frame(checked.conflicts[NAME_KEYS].drop_duplicates())
    conflicting = pd.MultiIndex.from_frame(names[NAME_KEYS]).isin(conflict_keys)
    supplied = (events.player_id.reset_index(drop=True).notna() if "player_id" in events
                else pd.Series(False, index=resolved.index))
    group_keys = [*CONTEXT, *( ["type"] if "type" in resolved else [])]
    breakdown = resolved.groupby([*group_keys, "identity_status"], dropna=False).size().unstack(fill_value=0)
    breakdown = breakdown.reindex(columns=["selected", "outside_population", "unresolved"], fill_value=0).reset_index()
    breakdown.columns.name = None
    unresolved = names.loc[resolved.identity_status.eq("unresolved")].groupby(NAME_KEYS, dropna=False).size().rename("events").reset_index()
    if sum(identity.counts.values()) != len(events) or breakdown[["selected", "outside_population", "unresolved"]].sum().sum() != len(events):
        raise IdentityEvidenceError("event diagnostic count conservation failed")
    coverage = {"match_coverage_status": "UNVERIFIED", "team_coverage_status": "UNVERIFIED",
                "season_coverage_status": "UNVERIFIED", "exposure_coverage_status": "NOT_ASSESSED",
                "expected_manifest_available": expected_matches is not None}
    if "match_id" in resolved:
        # Match coverage needs valid IDs and noncontradictory event metadata too.
        observed = validate_match_contexts(resolved, source="supplied event metadata", evidence_kind=DELIVERED).contexts
        verified_rows = checked.evidence.loc[checked.evidence.evidence_kind.eq(VERIFIED)
                                              & checked.evidence.match_context_kind.eq(VERIFIED)]
        source_matches = verified_rows[MATCH_KEYS].drop_duplicates()
        validate_match_contexts(pd.concat([observed, source_matches], ignore_index=True),
                                source="event/evidence association", evidence_kind=DELIVERED)
        observed_teams = resolved[TEAM_MATCH_KEYS].drop_duplicates().copy()
        observed_teams["match_id"] = _ids(observed_teams.match_id, "events.match_id")
        source_teams = verified_rows[TEAM_MATCH_KEYS].drop_duplicates()
        coverage.update(observed_matches=_sort(observed, MATCH_KEYS), evidence_matches=_sort(source_matches, MATCH_KEYS),
                        observed_match_teams=_sort(observed_teams, TEAM_MATCH_KEYS),
                        event_matches_without_evidence=_difference(observed, source_matches, MATCH_KEYS),
                        evidence_matches_without_events=_difference(source_matches, observed, MATCH_KEYS),
                        event_match_teams_without_evidence=_difference(observed_teams, source_teams, TEAM_MATCH_KEYS),
                        evidence_match_teams_without_events=_difference(source_teams, observed_teams, TEAM_MATCH_KEYS))
        if expected_matches is not None:
            if not isinstance(expected_matches, MatchContexts) or expected_matches.evidence_kind != VERIFIED:
                raise IdentityEvidenceError("expected matches require a verified manifest")
            manifest = validate_match_contexts(expected_matches.contexts, source=expected_matches.source,
                                               evidence_kind=expected_matches.evidence_kind).contexts
            validate_match_contexts(pd.concat([observed, source_matches, manifest], ignore_index=True),
                                    source="manifest association", evidence_kind=DELIVERED)
            coverage.update(expected_manifest_source=expected_matches.source,
                            expected_matches_missing_events=_difference(manifest, observed, MATCH_KEYS),
                            expected_matches_missing_evidence=_difference(manifest, source_matches, MATCH_KEYS),
                            event_matches_outside_manifest=_difference(observed, manifest, MATCH_KEYS))
    elif expected_matches is not None:
        raise IdentityEvidenceError("event match_id required to compare an expected manifest")
    summary = {"population_scope": population_scope, "population_contexts": len(selected),
               "total_events": len(events), "distinct_event_ids": int(events.id.nunique()),
               "events_missing_player_names": int((names.player_name_raw.isna() | names.player_name_raw.eq("")).sum()),
               "events_with_supplied_ids": int(supplied.sum()), "events_matched_crosswalk": int(crosswalk_match.sum()),
               "events_resolved_by_crosswalk_only": int((crosswalk_match & ~supplied).sum()),
               "events_on_conflicting_source_keys": int(conflicting.sum()), "identity_conflicts": 0,
               **identity.counts, "source_evidence": dict(checked.summary),
               "source_gap_label": ("SOURCE_UNAVAILABLE" if not checked.summary["verified_source_observations"]
                                    else "SEE_EVIDENCE_AND_COVERAGE"),
               "identity_coverage_proves_source_completeness": False}
    return IdentityCoverage(identity, summary, _sort(breakdown, group_keys), _sort(unresolved, NAME_KEYS),
                            identity.events.iloc[conflicting.nonzero()[0]].copy(), coverage)
