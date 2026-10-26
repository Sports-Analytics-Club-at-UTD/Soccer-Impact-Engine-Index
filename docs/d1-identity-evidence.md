# D1: player identity evidence and crosswalk reconstruction

## 1. Purpose and current blocker

**AUTHORITATIVE LINEUP SOURCE NOT AVAILABLE.** D1 provides a pure evidence builder
and diagnostic coverage contract, not a reconstructed production population.
The inspected integration HEAD is `94e75ea` (M5B), following `8f1e77a` (M5A).
No existing backend, M2A resolver, adapters, React code or statistical policy is
changed. New files are `src/identity_evidence.py`,
`tests/test_identity_evidence.py` and this document.

**VERIFIED FINDINGS** below describe checked local files/code and bounded
observations. They do not mean that original real-player identities have been
verified. There are **zero new real source-verified name-to-ID mappings** in D1.

## 2. Existing M2A identity contract

Canonical player context is `player_id`, `team`, `competition_name`, `season_name`.
The spelling lookup uses `player_name_raw` plus team/competition/season. Stable
IDs are exact positive signed-int64 integers, preserved as nullable Int64; integral
floats are accepted only within M2A's safe exact-integer range. Display names are
not identity keys. Team aliases remain only Marseille -> Olympique de Marseille
and Caen -> Stade Malherbe Caen. Name normalization only strips surrounding
whitespace and collapses doubled apostrophes.

`prepare_crosswalk`, `validate_population` and `resolve_events` are reused.
M2A's internal exact-ID validator is also reused for player and match IDs, without
changing the resolver or defining a competing ID conversion. `strict=False`
retains selected, known outside and unresolved events. Unknown membership remains
nullable, never outside by default. `require_resolved()`/default strict resolution
still reject unknowns. Supplied trusted IDs remain authoritative, with conflicts
against lookup evidence rejected. Input ID provenance remains the caller's duty.

## 3. Source files actually found — VERIFIED FINDINGS

All six existing Parquets were inspected read-only with Arrow metadata. Their
schemas were readable. Only projected columns and one bounded event batch were
materialized; no multi-million-row event or 360 table was loaded into pandas.

| Existing file | Rows | Identity relevance / evidence limit |
|---|---:|---|
| `data/processed/player_minutes.parquet` | 5,578 | player_id, display name, canonical context, role/minute descriptors; original duplicate-key delivery, not original spelling evidence |
| `data/processed/recovery_per90.parquet` | 7,683 | aggregated player/context/event counts, minutes and flags; not original event-to-ID evidence |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | 5,576 | distinct delivered canonical contexts; supporting population/descriptor evidence only |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | 7,680 | revised aggregate context/count consistency; cannot supply missing original spellings |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | 3,626,433 | id, match_id, player, team, competition_name, season_name, type and event attributes; **no player_id column** |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | 7,562,022 | event id/match/context, actor/teammate/keeper flags and geometry; no player ID/name evidence |

Lineup source `data/raw/statsbomb_lineups.parquet`, original event path
`data/raw/statsbomb_team_events.parquet`, historical
`data/processed/player_name_crosswalk.parquet`, and candidate match manifest
`data/raw/statsbomb_matches.parquet` were not found. The review event file exists
at the path above; its match metadata is not an independent fixture manifest.
No replacement data was searched online, downloaded, guessed or fabricated.

## 4. Required lineup schema and explicit attestations

`validate_lineup_evidence(lineups, source=..., evidence_kind=...,
match_contexts=None, name_column="player_name")` accepts direct records containing:

- `match_id`: positive exact integer identifying the source match.
- `team`: nonblank string; only existing M2A club aliases apply.
- `player_id`: valid M2A stable ID.
- Original spelling in `player_name`, or explicitly select
  `name_column="player_name_raw"`. Missing/blank names fail.
- Either both `competition_name` and `season_name` directly in the source, or a
  separately verified match-context association. Partial direct context fails.

The caller must explicitly name the source/category and its evidence kind:

| Label | Meaning / lookup treatment |
|---|---|
| `VERIFIED_SOURCE_EVIDENCE` | Caller attests direct authoritative identity evidence; eligible for trusted lookup only with verified direct/associated context and no collision |
| `DELIVERED_TABLE_CONSISTENCY_ONLY` | Supporting aggregate evidence; retained but never promoted to trusted spelling mappings |
| `SYNTHETIC_TEST_EVIDENCE` | Fixture observations, retained and labeled; no trusted production entries |
| `CONFLICTING` | Derived report label for a normalized name/context with competing IDs; quarantined |
| `UNRESOLVED` | No trusted event identity established; M2A's machine status is lowercase `unresolved` |
| `SOURCE_UNAVAILABLE` | No supplied usable authoritative evidence; local file absence is established separately by the inventory |

These are evidence labels, not scoring confidence ratings. File readability,
matching aggregate names or a caller's string label cannot independently prove
authenticity. Verification of source provenance is an external prerequisite;
the module validates structure/consistency and enforces the explicit trust gate.
An empty supplied table alone cannot distinguish a missing file from an empty
file. No function performs file I/O, downloads or data writes.

## 5. Match-context association rules

`validate_match_contexts(table, source=..., evidence_kind=...)` requires
`match_id`, `competition_name`, `season_name`. It validates IDs/labels, accounts
for identical repeated observations and returns a unique mapping with one
competition/season per match. Competing associations raise
`IdentityEvidenceError` with conflicting records in `.details`; there is no
first-row selection.

Context-free lineups can derive competition/season only through a validated
`MatchContexts` explicitly attested as VERIFIED. Unknown match IDs fail.
Direct lineup context is checked against any supplied mapping; disagreement
fails. If direct source context is supplied alongside an unverified association,
the observation is conservatively withheld from the trusted crosswalk. Source
labels for both sides are retained. Event metadata and independently supplied
expected manifests are checked for association conflicts during coverage audits.

## 6. Crosswalk reconstruction approach

```python
from src.identity_evidence import (
    VERIFIED, validate_match_contexts, validate_lineup_evidence,
    build_identity_crosswalk, audit_identity_coverage,
)

# These inputs must already have authoritative, independently reviewed provenance.
matches = validate_match_contexts(
    verified_match_records, source="reviewed match manifest", evidence_kind=VERIFIED,
)
lineups = validate_lineup_evidence(
    verified_original_lineups, source="reviewed original lineup records",
    evidence_kind=VERIFIED, match_contexts=matches,
)
candidate = build_identity_crosswalk(lineups)
candidate.require_unambiguous()  # optional strict gate: fails on source collisions
lookup = candidate.crosswalk    # only verified, nonconflicting M2A entries
audit = audit_identity_coverage(
    bounded_event_batch, candidate, explicitly_selected_contexts,
    population_scope="caller-described bounded diagnostic population",
    expected_matches=matches,
)
```

`build_identity_crosswalk` accepts one validated `LineupEvidence` or a sequence,
including `[]` when no evidence is supplied. It revalidates provenance records,
normalization and combined match associations before building an M2A-compatible
unique lookup. No role/minute/scope filtering is inferred. A validated lineup
bench identity may be useful evidence without implying playing exposure.

The result contains `crosswalk`, `evidence`, `conflicts` and `summary`. `evidence`
retains all original observations, including repeats, with source label/kind,
match-context source/kind, match ID, original spelling, normalized spelling,
stable ID, canonical context and report label. Crosswalk construction explicitly
deduplicates consistent mappings; the source ledger remains available for review.

## 7. Repeated and conflicting evidence

Summary accounting separates input rows, distinct observations, exact repeated
observations and repeated season-level mappings across matches/spellings.
Evidence-label counts describe distinct observations; verified-observation counts
also describe distinct observations. Diagnostic counts are not player metrics.
Repeated identical evidence cannot multiply event joins.

All evidence for a normalized name/team/competition/season with multiple IDs is
quarantined from the trusted lookup, including collisions seen across matches or
sources. The conflicts table retains distinct supporting match/source records;
the full ledger retains repetitions. Unrelated verified keys can still be
reviewed separately. Even a contradictory weaker observation triggers review
rather than an arbitrary winning ID. `require_unambiguous()` prevents treating
such a partial lookup as a complete unambiguous reconstruction.

## 8. Same-name and alias limitations

M2A's lookup key has no match_id. Two genuinely distinct same-name players inside
one team/competition/season cannot be encoded as an unambiguous season spelling
mapping. D1 reports both IDs and their matches and excludes that key. A future
verified match-scoped resolver extension may be necessary; D1 does not implement
one. A trusted supplied event ID can still resolve an actor under unchanged M2A,
while the audit flags the colliding season name key.

Rosa/Roza and apostrophe/quote variants such as David N'Gog/David N"Gog only map
together when each spelling has its own verified source record. No global
football-name alias, fuzzy matching, accent/case repair or convenient homonym
selection is added. Transfers, competitions and seasons remain separate contexts.

## 9. Population, exposure and coverage separation

`audit_identity_coverage(events, candidate, population, population_scope=...,
expected_matches=None)` revalidates the evidence ledger and calls M2A with
`strict=False`. Every input event/index and metric value is retained. It reports
selected, known outside and unresolved counts, missing names, supplied IDs,
verified crosswalk matches, crosswalk-only resolutions and events on conflicting
source keys. Supplied-ID and lookup-match counts overlap by design; only the
three M2A status categories form an exclusive event partition.

`IdentityCoverage` returns `identity`, `summary`, `breakdown`, `unresolved_names`,
`conflicting_events` and `coverage`. Breakdown uses canonical team, competition,
season and event type when present. Unresolved names are grouped by normalized
spelling/full context, including missing names. Input IDs must be unique;
duplicate IDs and cardinality errors fail rather than deduplicate events.
Conflicting supplied event IDs versus trusted lookup IDs remain fatal M2A errors;
the wrapped exception retains all original input rows in `.details`. Successful
audit `identity_conflicts=0` does not assert absence of source homonyms: those
have separate key/event counts and conflict records.

With match IDs, coverage compares observed event matches/match-team contexts
against verified source observations. Weak/synthetic evidence does not close
these source gaps. It reports event matches/teams without verified evidence and
evidence matches/teams absent from the supplied event batch. An optional verified
expected manifest adds missing expected event/evidence matches and event matches
outside the manifest. Missing expected matches are attributable to the supplied
scope only; a prefix batch intentionally omits later events.

Match/team/season completeness stays UNVERIFIED; exposure is NOT_ASSESSED.
Without independent expected fixtures and team/participation expectations, neither
the intended season denominator nor all missing teams/players can be known.
Without event match IDs, no observed-match tables are claimed. An explicitly
named population is validated with M2A but never treated as the complete project
population. No 450/900/1350-minute rules or role eligibility are applied.

## 10. Bounded real-data results — VERIFIED FINDINGS

Only the first Arrow batch of **4,096 events**, projecting id, match_id, player,
team, competition_name, season_name and type, was audited. The population was
**all 5,576 revised delivered minute contexts**, with no role/minute filtering.
This is an explicit diagnostic population, not a complete source population
claim. Its IDs/context/display/role/minute descriptors are
DELIVERED_TABLE_CONSISTENCY_ONLY; no display names were promoted into a lookup.
With no authoritative source, the supplied evidence set and trusted lookup were
empty, rather than fabricated from aggregate names.

| Diagnostic | Result |
|---|---:|
| Input events / distinct event IDs | 4,096 / 4,096 |
| Missing actor names / supplied player IDs | 0 / 0 |
| Verified crosswalk matches | 0 |
| Selected / known outside / unresolved | 0 / 0 / 4,096 |
| Distinct unresolved normalized name/context keys | 51 |
| Observed matches / match-team contexts | 2 / 4 |
| Observed matches lacking verified source evidence | 2 |
| Observed match-team contexts lacking verified source evidence | 4 |
| Source-identity conflicts detected | 0 comparisons possible; not proof of conflict-free actors |

Both observed matches, `3895292` and `3895320`, are in 1. Bundesliga / 2023/2024.
The sample has Bayer Leverkusen 2,314 events, Union Berlin 787 and VfB Stuttgart
995. Unresolved events by supplied source type are:

| Ball Recovery | Carry | Dribble | Duel | Interception | Pass |
|---:|---:|---:|---:|---:|---:|
| 101 | 1,714 | 29 | 76 | 20 | 2,156 |

All event counts are conserved. No events are classified outside merely because
their names fail an empty lookup. No original name-to-ID pair is verified by
this experiment. No full event scan is useful until authoritative evidence is
available; the bounded result is not a coverage estimate for 3.6M events or the
primary 2015/2016 cohort. All other matches/seasons and intended fixture/team
coverage remain unassessed, not implicitly complete.

## 11. Source evidence missing locally — REMAINING INPUTS REQUIRED

Obtain the original `statsbomb_lineups.parquet` or equivalent authoritative
lineup records with exact match IDs, source team names, stable player IDs and
every original actor spelling, plus provenance identifying their origin/scope.
If competition/season is absent, also obtain an independently verified unique
match-to-competition/season association. Raw event metadata must be checked for
conflicts before association and cannot be trusted solely because a first row
can be selected.

For completeness, obtain the intended competition/season fixture manifest,
expected participating teams and lineup/player participation coverage. Preserve
file fingerprints and source acquisition provenance. If available, obtain the
original historical `player_name_crosswalk.parquet` with its source lineage for
corroboration; an aggregate-only lookup without original provenance is not a
substitute for lineup evidence. Resolve same-context homonyms and verify each
additional spelling. No guessed numeric IDs, roster guesses or online name pages
are acceptable workarounds.

## 12. Tests, provenance review and integrity checks

Arpit source was inspected directly from fetched `origin/arpit-dev` at `0445f18`:
`player_minutes.py`, `player_names.py`, `team_names.py`, `recovery_per90.py`.
Historically, his minutes code cleaned original lineup spellings, chose display
names by frequency, filtered to position stints and extracted distinct spelling
maps. It warned about conflicting match associations then kept the first match
row; D1 rejects that unsafe association instead. Its 90-minute cap, dominant
roles, tie-breaking, scope and recovery thresholds are not adopted or approved.
The contributor pipeline was not executed or merged.

```sh
python -B -m unittest discover -s tests -v
python -B -W error -m unittest discover -s tests -q
node --test frontend/tests/*.test.js
```

Synthetic tests exercise valid lineup-shaped records, explicit positive-path
source attestations, untrusted/synthetic withholding, exact IDs, repeated and
conflicting observations, homonyms, spelling distinctions, aliases, context
association, manifests, selected/outside/unresolved partitions, fatal event
conflicts, deterministic construction, empty inputs and immutability. A fixture
emulating a VERIFIED attestation does not verify any real actor. The real-data
evaluation above does not reuse such synthetic mappings.

All six baseline Parquet hashes are recorded here for input-integrity comparison:

| File (as listed in section 3) | SHA256 |
|---|---|
| Original minutes | `9701ec4a74b1a75ee6094f08619c40b26f6d6f103d64a23ca2802448351e931b` |
| Original recovery | `056f94b0bd49bc707e5d00181d0b85654cd076e5dc3bc09e1a6c121cd530ee4d` |
| Revised minutes | `01f1bb2650df4f793971465eefad49eefcd41a302789b5c5009cf7355a4b1694` |
| Revised recovery | `7a546348b2c391d32221456fab259d639910d13c8e672ba030e6d30b38cab61f` |
| Review events | `ec12fdd2340fb125671f4996abdac510c3dc6d81555848792520ce5df2519eb8` |
| Review 360 | `497fa459e1ee99f758ed37d405d69285af5e6759306851456d03fde8c4025625` |

No audit CLI is added: the pure interfaces plus projected Arrow batch check are
sufficient for this missing-source milestone. No generated data, temporary
player tables, JSON, Parquet, scoring table or frontend export is written.

Both required Python commands passed **340 tests**: all 276 existing tests plus
64 new evidence tests, including warnings-as-errors. All **67 existing Node
tests** passed. Post-work hashes match all six values above. Git checks confirm
that only the three new D1 files appear beyond the six pre-existing untracked
datasets; tracked files, staging, HEAD, main refs and worktree inventory are
unchanged. No branch/worktree was created and nothing was staged or published.

## 13. Requirements for D1B

With verified original sources, validate the schema/associations and source
fingerprints, build an in-memory candidate, review every conflicting key and
compare canonical IDs/contexts against the revised minutes delivery without
deriving original spellings from it. Run bounded event audits first, then
projected streaming audits with cross-batch event-ID uniqueness if affordable.
D1 currently enforces uniqueness per call, not across independently audited
batches; a streaming orchestrator must keep global uniqueness/accounting.

Reconcile expected fixtures, teams, actors and missing seasons separately from
the name-match rate. Review actor spellings and same-context homonyms using
source evidence; propose a match-scoped resolver extension only if required.
Exposure reconstruction and role/minute/scoring policy are separate milestones.
Do not declare complete reconstruction merely because a bounded lookup joins.

## 14. Is complete reconstruction possible with current inputs?

**No.** The technical evidence/coverage layer is implementable and testable now,
but complete real identity reconstruction remains blocked by missing original
lineup/spelling evidence and independently verified scope/participation coverage.
The delivered tables can corroborate IDs/contexts; they cannot recover every
original actor spelling or prove complete source coverage. D1B requires the
additional inputs in section 11 before a production reconstruction is defensible.
