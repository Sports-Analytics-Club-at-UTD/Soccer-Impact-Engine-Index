"""Explicit, cardinality-safe event identity resolution; no metric or scope policy."""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral, Real
import math

import pandas as pd

CONTEXT = ["team", "competition_name", "season_name"]
PLAYER_KEYS = ["player_id", *CONTEXT]
NAME_KEYS = ["player_name_raw", *CONTEXT]
TEAM_ALIASES = {
    "Marseille": "Olympique de Marseille",
    "Caen": "Stade Malherbe Caen",
}
STATUSES = ("selected", "outside_population", "unresolved")


class IdentityError(ValueError):
    """Invalid identity evidence or an unsafe join contract."""


class UnresolvedIdentityError(IdentityError):
    """Resolution failed closed; the complete result remains available for diagnosis."""

    def __init__(self, result):
        self.result = result
        missing = result.events.loc[result.events.identity_status == "unresolved"]
        examples = missing[["id", "player", *CONTEXT]].head(3).to_dict("records")
        super().__init__(f"{len(missing)} unresolved event identities; population membership "
                         f"is unknown. Supply trusted crosswalk evidence. Examples: {examples}")


@dataclass
class IdentityResult:
    events: pd.DataFrame

    @property
    def counts(self):
        """Event counts by status, including zero counts; never metric imputation."""
        return {s: int(self.events.identity_status.eq(s).sum()) for s in STATUSES}

    def require_resolved(self):
        if self.counts["unresolved"]:
            raise UnresolvedIdentityError(self)
        return self

    def selected_events(self):
        """Select only after every input identity is resolved; never silently drop unknowns."""
        self.require_resolved()
        return self.events.loc[self.events.in_population.eq(True)].copy()


def _columns(table, required, label):
    if not table.columns.is_unique:
        raise IdentityError(f"{label}: duplicate column labels")
    missing = [c for c in required if c not in table]
    if missing:
        raise IdentityError(f"{label}: missing columns {missing}")


def _text(series, label, *, allow_missing=False):
    present = series.dropna()
    if not all(isinstance(v, str) for v in present):
        raise IdentityError(f"{label}: labels must be strings")
    if not allow_missing and (series.isna().any() or any(not v.strip() for v in present)):
        raise IdentityError(f"{label}: missing or blank labels")


def normalize_player_names(names):
    """Existing spelling cleanup only: doubled apostrophes and surrounding whitespace."""
    _text(names, "player names", allow_missing=True)
    return names.astype("string").str.replace("''", "'", regex=False).str.strip()


def normalize_team_names(teams):
    """Apply only the two declared club aliases; no fuzzy matching or inferred clubs."""
    _text(teams, "team")
    return teams.replace(TEAM_ALIASES).copy()


def _ids(series, label, *, allow_missing=False):
    def valid(value):
        if not pd.api.types.is_scalar(value):
            return False
        if pd.isna(value):
            return allow_missing
        if isinstance(value, bool):
            return False
        if isinstance(value, Integral):
            return 0 < value <= 2**63 - 1
        # Floats above exact-integer precision are not safe identity evidence.
        return (isinstance(value, Real) and math.isfinite(value)
                and 0 < value <= 2**53 - 1 and value == math.floor(value))

    if not all(valid(v) for v in series):
        raise IdentityError(f"{label}: IDs must be positive exact integers fitting signed int64")
    return series.astype("Int64")


def _contexts(table, label):
    out = table.copy(deep=True)
    for c in CONTEXT:
        _text(out[c], f"{label}.{c}")
    out["team"] = normalize_team_names(out.team)
    return out


def validate_population(population):
    """Validate explicit selected stable contexts; do not derive eligibility from labels."""
    _columns(population, PLAYER_KEYS, "population")
    out = _contexts(population[PLAYER_KEYS], "population")
    out["player_id"] = _ids(out.player_id, "population.player_id")
    if out.duplicated(PLAYER_KEYS).any():
        raise IdentityError("population: duplicate stable keys after team normalization")
    return out


def prepare_crosswalk(crosswalk):
    """Validate a caller-trusted spelling lookup, rejecting normalized duplicate keys."""
    _columns(crosswalk, [*NAME_KEYS, "player_id"], "crosswalk")
    out = _contexts(crosswalk[[*NAME_KEYS, "player_id"]], "crosswalk")
    out["player_id"] = _ids(out.player_id, "crosswalk.player_id")
    out["player_name_raw"] = normalize_player_names(out.player_name_raw)
    _text(out.player_name_raw, "crosswalk.player_name_raw")
    ambiguous = out.groupby(NAME_KEYS, dropna=False).player_id.nunique().gt(1)
    if ambiguous.any():
        raise IdentityError("crosswalk: ambiguous name-to-ID mappings in the same context")
    if out.duplicated(NAME_KEYS).any():
        raise IdentityError("crosswalk: duplicate normalized name/context keys; "
                            "review repeated evidence explicitly before resolution")
    return out


def resolve_events(events, crosswalk, population, *, strict=True):
    """Attach stable IDs without dropping/multiplying rows. See docs/m2a-identity.md.

    Crosswalk scope must include known outsiders if they are to be distinguished
    from unknown identities. A missing crosswalk match never proves exclusion.
    Existing event player IDs are authoritative input, checked against any lookup
    match. Names alone never establish that two players are the same person.
    """
    _columns(events, ["id", "player", *CONTEXT], "events")
    reserved = {"team_raw", "identity_status", "in_population"}
    if any(c in reserved or str(c).startswith("_identity_") for c in events.columns):
        raise IdentityError("events: reserved identity output/internal column collision")
    _text(events.id, "events.id")
    if events.id.duplicated().any():
        raise IdentityError("events: duplicate event IDs; do not deduplicate events implicitly")
    out = _contexts(events.reset_index(drop=True), "events")
    out["team_raw"] = events.team.to_numpy(copy=True)
    out["_identity_name"] = normalize_player_names(out.player)
    supplied = (_ids(out.player_id, "events.player_id", allow_missing=True)
                if "player_id" in out else pd.Series(pd.NA, index=out.index, dtype="Int64"))
    out["player_id"] = supplied
    lookup = prepare_crosswalk(crosswalk).rename(
        columns={"player_name_raw": "_identity_name", "player_id": "_identity_mapped_id"})
    selected = validate_population(population)
    out = out.merge(lookup, on=["_identity_name", *CONTEXT], how="left",
                    validate="many_to_one", sort=False)
    if len(out) != len(events) or out.id.tolist() != events.id.tolist():
        raise IdentityError("event join changed cardinality or event order")
    mapped = out["_identity_mapped_id"]
    conflict = out.player_id.notna() & mapped.notna() & out.player_id.ne(mapped)
    if conflict.any():
        raise IdentityError("events: supplied player_id conflicts with trusted crosswalk")
    out["player_id"] = out.player_id.fillna(mapped).astype("Int64")
    member = pd.MultiIndex.from_frame(out[PLAYER_KEYS]).isin(
        pd.MultiIndex.from_frame(selected[PLAYER_KEYS]))
    out["in_population"] = pd.array(member, dtype="boolean")
    out["identity_status"] = "outside_population"
    out.loc[member, "identity_status"] = "selected"
    unknown = out.player_id.isna()
    out.loc[unknown, "identity_status"] = "unresolved"
    out.loc[unknown, "in_population"] = pd.NA
    out = out.drop(columns=["_identity_name", "_identity_mapped_id"])
    out.index = events.index.copy()
    result = IdentityResult(out)
    return result.require_resolved() if strict else result
