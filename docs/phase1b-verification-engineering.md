# Phase 1B: verification engineering and retained-source investigation

October 27, 2026. This session used only existing local source evidence. **Zero
network requests, zero production-certified season contexts, and zero ratings.**
The verification workflow is implemented for bounded offline review and optional
explicitly authorized future acquisition; the source records for season coverage
remain incomplete. No provider contradiction was guessed away or repaired.

## Outcomes of all nine original contradictions

All nine are **D: contradictory upstream source observations**. None was caused
by an adapter clock interpretation error. Original event IDs, indices, period
identifiers, timestamps, team/player IDs, positions, entry/exit reasons and paired
whistles are retained in `analysis/contradiction-investigations.json`. Each case
includes both original event-index order and period/clock order, unmodified raw
position objects, adapter observations and validator issues. Every disputed
aggregate duration and position allocation remains withheld.

| Match / player ID | Actor | Exact retained-source contradiction |
|---|---|---|
| 3754217 / 3437 | Francis Coquelin | Temporary exit 1/21:41.335 and return 1/22:04.886 are supported. A first-half tactical shift at 1/47:40.432 precedes substitution off at 2/00:00.217. The lineup also starts a stint at first-half 47:40 continuing to final whistle, overlapping the prior stint and extending past that substitution. |
| 3754217 / 3496 | Mesut Ozil | The lineup orders second-half displayed 45:12 before first-half 47:40. Original tactical events are 1/47:40.432 then 2/00:12.953; the intermediate stint reverses periods and active positions disagree with the event snapshot. |
| 3754217 / 3517 | Aaron Ramsey | The same 2/45:12 to 1/47:40 reversed-period stint and overlapping position allocations occur. Original tactical snapshots disagree with the claimed interior position. |
| 3754217 / 6746 | Gabriel | Reversed-period stints coexist with an original `Bad Behaviour` red card at 1/45:44.427 (`9323e138-e109-4571-aabd-6554caed0b11`). The lineup and subsequent tactical snapshots continue to list him active after dismissal. Event snapshots themselves therefore do not provide an uncontested corrected position timeline. |
| 3829416 / 3230 | Alassane Plea | The lineup places second-half displayed 45:03 before first-half 46:05. Actual tactical events are 1/46:05.280 (`e2ccbf18-ed6b-47b3-b0b0-925284952dc1`) then 2/00:03.571 (`55be218b-62a0-41f1-98d5-0164bfea7bc4`). Reverse periods, overlaps and snapshot disagreement remain. |
| 3829416 / 16462 | Hatem Ben Arfa | The same reversal occurs. At substitution off 2/17:46.685 the event position is Right Wing Back, while the lineup's final active stint claims Center Forward. |
| 3879549 / 6636 | Rodrigo Ely | A stint starts at 2/45:00 and ends at 1/45:51, with `Substitution - On (Tactical)` as its exit reason. The original incoming substitution is retained; treating an incoming reason as an outgoing transition would be unsupported. The source also puts this positional stint before his first-half entry. |
| 3879549 / 7026 | Giacomo Bonaventura | A stint runs from second-half displayed 45:00 back to first-half 46:06. Original tactical events are 1/46:06.763 then 2/00:00.000. Their positions conflict with the claimed overlapping stint allocation. |
| 3879549 / 7147 | Andrea Bertolacci | The same period reversal occurs after a supported first-half temporary exit/return. Its real absence does not resolve the reversed tactical position stints. |

Period notation `1/47:40.432` means period 1, original period-local event
timestamp. Values labeled **displayed** are original lineup MM:SS clocks.
All nine retain complete unflagged paired period boundaries. The adapter checks
every event's period-local timestamp against minute/second with offsets 0 and 45;
no clock disagreement was found. There are no identity/context conflicts in
these cases. Thus categories A (adapter-caused conflict), B (unsupported clock),
C (incomplete boundary) and E (identity/context conflict) do not explain them.
Sorting displayed MM:SS across halves would erase recorded stoppage time and is
not a supported repair. The observed pattern does not prove the provider's
internal lineup-generation algorithm or establish the real-world correct lineup.

## Implementation gap found and corrected

The original nine were legitimate failures. However, Phase 1 checked only the
supplied stints and their endpoints. It did not independently cross-check all
original exit events and interior tactical position snapshots. This was a
verification coverage defect: five additional appearances formerly labeled
structurally valid now correctly remain contradictory.

| Match / actor ID | Newly detected source conflict |
|---|---|
| 3829416 / 3210, Valere Germain | First-half 46:05.280 already assigns Left Wing Back; the lineup retains Right Center Forward until second-half 45:03. |
| 3829416 / 4443, Paul Baysse | That first-half snapshot already assigns Center Back; the lineup retains Right Center Back until second-half 45:03. |
| 3829416 / 401474, Kevin Gomis | That first-half snapshot already assigns Right Center Back; the lineup retains Right Back until second-half 45:03. |
| 3829416 / 7323, Olivier Boscagli | Second-yellow dismissal at 1/43:23.579 (`31952b30-fb18-4706-babf-66a7e35e9097`) is absent from the lineup interval endpoints; the lineup continues to final whistle. |
| 3879549 / 7458, Alessio Romagnoli | Second-yellow dismissal at 1/41:48.147 (`cf134a63-5936-479b-8b82-3a7bffa44e06`) is absent from the lineup interval endpoints; the lineup continues to final whistle. |

The hardened `src/statsbomb_participation.py` now:

- Retains immutable, source-referenced consistency checks alongside each actor's
  raw position records and D3J observations.
- Detects omitted Player Off/On, substitution and dismissal evidence, including
  `Bad Behaviour` red cards; detects claimed activity after a permanent exit.
- Compares interior Starting XI/Tactical Shift position snapshots against a
  uniquely claimed active stint. It never chooses one of overlapping stints.
- Withholds the aggregate duration and position allocation for any additional
  source conflict, while preserving D3J's original issues and candidate geometry.
- Validates exact final-whistle period and explicit match IDs, unique original
  event indices when supplied, and malformed nested schema failures.
- Withholds malformed/unknown boundary attributes as well as documented early
  video end, late video start and suspension flags.

It still preserves millisecond precision, period origins, stoppage time,
temporary gaps, actor IDs/names, positions, original reasons and source
fingerprints. Missing final whistles remain unresolved. Permanent exits whose
internal transition category is unsupported remain incomplete unless contradictory
activity is independently observed. No exit, entry, position or duration is
invented. `src/participation_intervals.py` and approved scoring formulas are
unchanged. These are stricter evidence checks, not a production trust attestation.

## Real sample and season readiness

The source match set remains exactly the eight Phase 1 matches. No source pair
was downloaded again. Immutable match/actor reports are under
`analysis/offline-store/reports/`; `analysis/final-replay.json` identifies the
reports for the final workflow implementation and verifies resume behavior.

| Match | Structurally valid active appearances | Contradictory active appearances |
|---|---:|---:|
| 265958 | 28 | 0 |
| 266961 | 28 | 0 |
| 3753983 | 28 | 0 |
| 3754217 | 24 | 4 |
| 3829416 | 22 | 6 |
| 3879549 | 24 | 4 |
| 3879594 | 28 | 0 |
| 3901262 | 28 | 0 |
| Total | **210** | **14** |

There are 224 active player-match observations across 196 distinct player/club/
league/season contexts, plus 79 bench roster entries that are not asserted active
appearances. The sample covers **eight provider matches, seven delivered
matches, and 64 of the 549 table-qualified contexts**. Of those contexts, 61 have
at least one valid sample appearance and six have a contradictory sample
appearance; these sets overlap. None has independently verified full-season
exposure. Delivered-table eligibility stays separate from validated exposure
eligibility: **549 table-qualified; zero validated season exposure eligible;
zero production-certified**. Actor identity and component reportability gates
remain unresolved rather than inferred from structural interval validity.

`src/season_verification.py` provides deterministic, pure accounting;
`analysis/season-readiness.json` records every qualified context separately,
its observed appearances, source pair coverage, valid/conflicting samples and
unresolved gates. The two transferred actors retain four separate contexts:

- **3057:** Newcastle United and Swansea City, Premier League 2015/2016.
- **13286:** Lorient, Ligue 1, and Sunderland, Premier League, 2015/2016.

No club exposures or scores are pooled. No real ratings, score distributions,
production exports or changes to delivered minutes are introduced.

## Arpit's actual October 27 fixture file

Read-only input:
`data/source-evidence/arpit-fixtures-2026-10-27/statsbomb_fixtures_2015_16.parquet`.
It has **1,517 rows and 57 columns**, including exact int64 match/competition/
season/team IDs, string league/season/home/away fields, fixture metadata and
`fetched_on`. Its SHA256 is:

`0272328e14e1e0363fa4368e834958fb24ff547f518f9eecfbb83447bff90488`.

Its schema is retained in `arpit-snapshot-review.json`. D3H reads this actual
Parquet directly: all required columns already exist, so no conversion or
rewriting was necessary. Its normalized fixture associations agree exactly with
Phase 1: no duplicate IDs, no IDs exclusive to either snapshot, and no match-ID,
league, season or home/away name disagreements. A second comparison also found
zero differences across 14 fixture metadata fields, including competition/
season/team IDs, dates, scores, status, match week and version fields.

| League | Delivered observed / provider-listed | Result |
|---|---:|---|
| La Liga | 380 / 380 | exact provider ID match |
| Premier League | 380 / 380 | exact provider ID match |
| Ligue 1 | 377 / 377 | exact provider match, not proof of 380 historical fixtures |
| Serie A | 379 / 380 | missing delivered ID **3879594**, AC Milan vs Chievo |

D3H also finds no context/team disagreements. Fresh October 27 fixture snapshots
do not establish historical event/lineup acquisition outcomes. Arpit's provenance
is recorded **separately**: the user supplied retriever/date and every
`fetched_on` value says `2026-10-27`; no original endpoint, request timestamp or
provider Git revision accompanies this Parquet. Those fields remain unknown;
agreement does not justify assigning Phase 1's revision to Arpit's retrieval.
The D3H sidecar binds its actual bytes and declared date, keeping the independent
review gate unresolved. See `arpit-fixtures-provenance.json`,
`arpit-d3h-comparison.json` and `arpit-full-context-comparison.json`.

Recovered source records for 3879594 remain isolated. Inclusion in a future
complete-season rebuild is **pending team approval**. Such a rebuild must
explicitly reconcile its roster/identity, original events, exposure and component
numerators, and then rerun eligibility checks; it cannot append recovered minutes
to current season aggregates or silently extend the present denominator.
The three Ligue 1 provider-unlisted schedule slots remain a separate coverage
limitation; no missing provider IDs or acquisition causes are invented.

## Manifest-driven future retrieval and verification

`scripts/source_verification_batch.py` implements:

- An explicit 1,517-fixture manifest at the retained immutable provider revision,
  bound original fixture documents, per-match context and inclusion policy, and
  references to the eight retained event/lineup pairs.
- Source URLs, timezone-aware retrieval timestamps, SHA256 fingerprints and
  original byte/schema checks. Fixture, endpoint, revision or content conflicts
  reject instead of selecting a winner.
- An **offline read-only dry run by default**. Its optional existing-store view
  includes completed retrievals, failures, interrupted outcomes and integrity
  conflicts without writing files or making a request.
- Explicit offline verification batches of up to 64 selected IDs; immutable
  match/actor reports include input bindings and a verification key tied to
  adapter/validator/workflow implementation fingerprints.
- Safe resume: unchanged completed artifacts and matching validated reports are
  skipped; only missing payloads can be requested in an authorized retrieval run.
  Interrupted request starts remain outcome-unknown. Unfinalized/orphan payloads
  never become accepted evidence merely because bytes exist on disk.
- Optional retrieval only with `--allow-network`, explicit `--match-ids`, explicit
  `--batch-limit` from **1 to 8**, and `--destination` pointing to a dedicated new
  store (or the same manifest's registered store on resume). No credentials or
  private endpoints are used. The gate is checked before retrieval.
- Append-only request journals, exclusive/content-addressed object and report
  writes, success/failure accounting, rejected-schema reports, cache tamper/stale
  detection and optional repeat-fetch comparison via `--refresh`. Different
  bytes remain isolated and produce a persistent integrity-conflict report.
  Prior source files, reports and delivered tables are never overwritten.

The implementation is operated as a single batch writer per store; no concurrent
multi-process acquisition was exercised. Its tested resume contract concerns
interrupted requests, partial failures and subsequent serial runs. There is no
automatic retry loop, scheduler, missing-fixture fetch or production ingest.

Safe local commands, with **no network access**:

```powershell
python -B -m scripts.source_verification_batch --manifest data/source-evidence/phase1b-2026-10-27/analysis/retrieval-manifest.json
python -B -m scripts.source_verification_batch --manifest data/source-evidence/phase1b-2026-10-27/analysis/retrieval-manifest.json --verify --match-ids 3754217 --destination data/source-evidence/phase1b-2026-10-27/analysis/offline-store
```

The second command returns a conflict-bearing review and a nonzero outcome for
this disputed match, while skipping unchanged validated source artifacts on
resume. A successful artifact/schema review is not a successful player interval
or season certification. The optional network mode was **not invoked** in this
session; synthetic fake transports test its authorization and failure behavior.

`scripts/audit_phase1b.py` orchestrates the offline pilot investigation, manifest
plan, immutable reports, resume check and readiness report into a new exclusive
output directory. It cannot retrieve data or overwrite an existing output root.

## Feasibility and next major integration phase

The provider inventory is 1,517 fixtures; the retained source inventory is eight
pairs. **1,509 additional original match pairs remain** for this complete-pair
workflow: up to 3,018 payload requests if both documents are retrieved. Existing
lineups may reduce necessary retrieval after their provenance and required
actor/boundary coverage are reviewed; the new tooling does not assume that a
few verified matches establish season identity or exposure. Phase 1's rough
sample-based scope estimate remains about 4.62 GB of event JSON plus 29.9 MB of
lineup JSON. No season-scale acquisition occurred here.

Engineering can now proceed through explicit bounded manifests and resume with
auditable reports. **Full-season verification cannot complete with current
provider evidence locally available.** It still needs original source records
for remaining appearances, resolution or explicit policy handling of provider
contradictions, historical coverage decisions for Ligue 1, approval of 3879594's
inclusion, provenance review, exposure convention and component numerator/
reportability alignment. Historical acquisition logs cannot be recovered by a
fresh fetch. Even a completed download cannot by itself resolve these issues.

The recommended next major phase is **controlled evidence expansion and
rebuild-policy integration**: first obtain team decisions/provider clarification
for disputed timelines, Ligue 1 coverage and 3879594; then authorize only explicit
small retrieval batches needed by the manifest. A later rebuild must be a new,
isolated dataset with reconciled actor identities, appearances, exposure and
component scope. Production scoring remains a separate gated action.

## Exact implementation changes and validation

Modified relative to Phase 1 (both were already untracked):

- `src/statsbomb_participation.py`
- `tests/test_statsbomb_participation.py`

New code/tests/documentation:

- `src/season_verification.py`
- `scripts/source_verification_batch.py`
- `scripts/audit_phase1b.py`
- `tests/test_source_verification_batch.py`
- `tests/test_season_verification.py`
- `tests/test_phase1b_real_evidence.py`
- `docs/phase1b-verification-engineering.md`

All new review artifacts are separate under
`data/source-evidence/phase1b-2026-10-27/`; `artifact-inventory.json` records every
new review artifact and its fingerprint. The manifest references the original
Phase 1 files rather than copying or replacing them. Raw source data and generated
review JSON remain separate from code that could later be reviewed for a commit.
Neither source-data directories nor implementation files were staged here.

Focused tests cover 43 adapter, 25 batch workflow, 14 season accounting and two
explicitly labeled real retained-evidence checks (**84 focused tests**). Full
Python/JavaScript results and final preservation checks are recorded in
`validation-record.json`. Synthetic failure fixtures exercise missing/flagged
whistles, temporary absences, post-90/cross-period clocks, omitted exits/cards,
position conflicts, malformed schemas/IDs, deterministic provenance, immutability,
offline defaults, bounded authorization, interruption/resume, fingerprint changes,
repeat conflicts, stale/tampered reports and separate transfer contexts.

The branch remains `integration-foundation`, HEAD
`20d690ee6d017fc689cec09fff088d8d7f524c07`. No tracked file, staging area, delivered
dataset, scoring formula or gate was changed. No branches/worktrees, merges,
rebases, resets, cleans, commits, pushes, deployments or production exports were
performed. The original 11 protected Parquets, M4A checklist, Arpit snapshot and
all 92 Phase 1 evidence artifacts are subject to final byte-for-byte verification.
