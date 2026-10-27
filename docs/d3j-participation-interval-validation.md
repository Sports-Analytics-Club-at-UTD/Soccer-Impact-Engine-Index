# D3J — pure participation-interval validation

October 27, 2026. Validation machinery and synthetic fixtures only. No existing
player context is promoted, no delivered minutes are reconstructed, and no
production player minutes, ratings or dataset outputs are generated.

## Scope and interface

`src/participation_intervals.py` exports frozen input/output dataclasses and:

```python
result = validate_participation(
    context, observations,
    clock_policy=explicit_policy,
    period_boundaries=explicit_boundaries,
)
```

This operates on one explicitly supplied player/team/match collection. It is
pure: no filesystem, network, ingestion, exporter or scoring operations. It
neither discovers records nor certifies that the supplied collection includes
every appearance or boundary. A structurally valid sum covers supplied active
intervals only; it is not independently verified full-match participation.

| Input | Fields |
|---|---|
| `Context` | `match_id, player_id, team_key` |
| `Clock` | `period, seconds, evidence_refs` |
| `Stint` | `observation_id, context, position, start, end, entry_kind, exit_kind, evidence_refs, provenance_refs` |
| `ClockPolicy` | `match_id, convention, period_order, evidence_refs, provenance_refs` |
| `PeriodBoundary` | `match_id, period, start_seconds, end_seconds, evidence_refs, provenance_refs` |

Observations and boundaries are finite lists/tuples. Nested evidence references
and period order must be immutable tuples. IDs reuse M2A's positive exact
signed-int64 validator. `team_key` is an explicit nonblank unambiguous string;
the future adapter must supply the same canonical team key everywhere. No name,
team, match or ID is guessed or repaired. Different associations quarantine the
aggregate. Existing normalization and verified identity gates are unchanged.

Clocks use exact nonnegative seconds as integers, `Decimal` or `Fraction`, or
explicit `None` for missing clocks. Float/string coercion is rejected. A future
adapter must parse original clock representations using validated source-format
rules and retain the original records through evidence references. The engine
does not claim an original event schema or parse guessed provider clock fields.

`position` is an original supplied position key, or `None` when unknown. No
CB/MID assignment, dominant-role choice or position mapping is performed.
Each observation has a unique nonblank ID. Duplicate IDs, malformed values,
duplicate period declarations or invalid reference structures raise
`ParticipationError`; these are input-contract errors rather than repaired data.

## Explicit clock policy

Supported conventions are internal arithmetic contracts, **not authenticated
StatsBomb semantics**:

- `period_local`: clock seconds are measured from that period's zero origin.
  Any supplied period start must therefore be zero.
- `period_offset`: clock seconds use a caller-documented origin/offset for each
  period. Each supplied period boundary explicitly identifies its start/end
  labels. No offsets of 45, 90 or 120 minutes are inferred.

`period_order` declares chronology explicitly; numeric period IDs are not used
to invent their order. The policy needs evidence and provenance references.
Unknown/missing conventions or documentation withhold all computed exposure.
These references are declarations, not independent authentication of the policy.

Within a period, exposure is the exact end/start difference. Supported supplied
boundaries also constrain endpoint containment. Across periods, **every spanned
period** requires explicit start/end clocks, evidence and provenance. The
calculation adds the active portion in each period, excluding breaks between
periods and including recorded added time. A missing required boundary yields
N/A for that cross-period interval. This strict boundary requirement is an
implementation safeguard, not approval of a new team playing-time policy.

There is no 90-minute filling or clipping. The only minute-90 comparison is an
informational `recorded_entry_after_minute_90` finding for `period_offset`
entry labels above 5400 seconds; it is never an end boundary or eligibility rule.
For `period_local`, a global minute-90 entry is not inferred from period IDs.

## Internal transition categories

Entry categories: `starter`, `substitution`, `return`, `position_change`,
`unknown`. Exit categories: `substitution`, `dismissal`, `temporary_exit`,
`match_end`, `position_change`, `unknown`.

These are adapter classifications, not assertions that any provider emits those
literal event types or guarantees. Unknown mappings remain incomplete. A future
adapter must justify each classification from source records and references.

- An initial starter must be in the first declared period and agree with a
  supported start boundary (or zero for `period_local`). A match-end exit must
  be in the last declared period and agree with any supported end boundary.
- A temporary exit requires a following return. A return without a supported
  preceding temporary-exit category conflicts; a missing return is incomplete.
- A position change requires paired exit/entry categories and zero elapsed gap.
  Positions split the same participation timeline; they do not create extra time.
- A permanent exit followed by another initial entry conflicts. Dismissal is a
  terminal exit; ordinary substitution off is also terminal for this collection.
- Overlaps, including nested overlaps and duplicate participation with different
  observation IDs, block the aggregate. No union, deduplication or first-record
  selection silently repairs them.
- Gaps are retained separately. Supported temporary absence is excluded from
  active exposure, not filled. A gap across periods can have unknown duration
  while its two within-period active intervals remain measurable; no cross-period
  active duration is inferred in that case.
- Explicit equal start/end clocks produce a zero-duration diagnostic and zero
  conditional exposure when all other structure/evidence is valid. Missing
  clocks never become zero. This does not authenticate D3I's real zero-duration
  rows or justify mapping their unusual boundary reasons into supported categories.

## Output and fail-closed statuses

`ParticipationResult` separates:

- `status`: `STRUCTURALLY_VALID`, `INCOMPLETE_EVIDENCE` or `CONFLICTING_EVIDENCE`.
- `elapsed_seconds`: accepted conditional total as an exact `Fraction`, otherwise
  `None` (N/A). No season aggregation or minutes-output writer exists.
- `position_allocation`: immutable position/exact-seconds records, otherwise
  `None`. A valid allocation sums exactly to accepted elapsed exposure.
- `intervals`: per-observation candidate geometry and the boundary periods used
  or required. These diagnostics are **not accepted aggregate exposure** when
  any collection-level evidence/sequence check fails.
- `gaps`: preceding/following observation IDs, conditional gap duration or N/A,
  and whether supplied evidence supports a temporary-absence sequence.
- `findings`: informational multiple-stint, zero-duration, late-entry, gap,
  temporary-absence and position-change observations.
- `issues`: deterministic codes and affected observation IDs. Missing evidence,
  missing provenance, unknown transitions and unresolved boundaries remain visible.
- `observations`, `clock_policy`, `period_boundaries`: original immutable
  declarations, preserving evidence/provenance references for every interval.

Any conflict takes precedence over incompleteness; either withholds the accepted
total and position allocation. Missing active ends never inherit another
interval's end or the largest event clock. Empty observations mean incomplete
evidence, not a bench appearance or zero participation. There is no automatic
source/evidence promotion: `source_independently_verified=False` and
`publication_authorized=False` for every returned result, including valid ones.

When missing clocks or unmapped transitions prevent a complete sequence check,
the sequence is explicitly incomplete. The engine does not delete those records
and manufacture an unsupported-return conflict from the remaining subset.
Explicit contradictions among bounded observations, such as overlaps, can still
be reported while other evidence is incomplete.

## Reproducible synthetic examples

All identifiers, evidence and clock policies below are invented test inputs.
They are not records for an existing player or an approved real clock convention.

```python
from src.participation_intervals import (
    Clock, ClockPolicy, Context, PeriodBoundary, Stint, validate_participation,
)

context = Context(101, 202, "invented-team-key")
refs = ("invented-fixture:boundary",)
provenance = ("invented-synthetic-source:v1",)
policy = ClockPolicy(101, "period_offset", (1, 2), refs, provenance)
bounds = (
    PeriodBoundary(101, 1, 0, 2880, refs, provenance),
    PeriodBoundary(101, 2, 2700, 5580, refs, provenance),
)
row = Stint("a", context, "invented-CB",
            Clock(1, 0, refs), Clock(2, 5580, refs),
            "starter", "match_end", refs, provenance)
result = validate_participation(context, [row], clock_policy=policy,
                                period_boundaries=bounds)
assert result.status == "STRUCTURALLY_VALID"
assert result.elapsed_seconds == 5760  # 48 + 48 elapsed minutes; neither 93 nor 90
assert not result.source_independently_verified

missing = validate_participation(context, [row], clock_policy=policy)
assert missing.status == "INCOMPLETE_EVIDENCE"
assert missing.elapsed_seconds is None
```

Additional synthetic regressions demonstrate a 91-to-96 recorded-minute
substitute (300 seconds, unclipped), a 60-second temporary absence excluded from
exposure, paired position changes allocating one continuous timeline, an open
final-whistle interval remaining N/A, and a D3I-shaped period reversal despite
numerically increasing clocks. No observed real-player record is passed through
this module in D3J.

## Evidence still required and future adapter

D3I's supplied findings are reused: 56,854 active stints; 33,369 open
final-whistle endpoints; 23,485 explicit endpoints; nine reversed-period records;
eight overlapping adjacent comparisons and 1,489 gap comparisons. All 549
table-qualified contexts still depend on open endpoints. Those findings are
not recomputed here and none becomes verified by this synthetic validator.

The integration lead now reports that Arpit did **not** retain original fixture
snapshots, fetch logs or untrimmed events. This supersedes D3H's suggestion to
first recover those particular archives. They must not be represented as available.
Authoritative original event schema and period-clock semantics remain unverified.

A future authorized retrieval task should first obtain versioned authoritative
source-format/clock documentation and a small pilot of original fixture, lineup
and untrimmed match records. Select cases covering ordinary participation,
late entry, temporary absence, dismissal and contradictory/cross-period stints;
verify actual source fields and boundary representations before coding their
mapping. Preserve source revision, retrieval record, fingerprints, failures and
expected fixture membership. Expand only to demonstrated missing evidence;
do not assume blanket reacquisition is required.

The future evidence-aware adapter must validate match/competition/season and
canonical actor/team identity through existing D1/M2A gates, retain raw source
records, establish clock semantics and map supported boundaries into these
internal categories. Missing original boundaries or contradictory records must
stay unresolved, not be filled from filtered actions, event maxima or minute 90.
Source field names for starts, replacements, dismissals and temporary exits are
not invented by this module. Completeness and provenance authentication remain
separate upstream work, including the independent fixture evidence missing in D3H.

No real lineup adapter, production reconstruction, match/season exporter, role
assignment, 900-minute eligibility, press-action gate, reference membership,
percentile, FIFA attribute, OVR or frontend integration is introduced. Existing
minutes, metric/scoring formulas and ratings therefore remain unchanged.

## Validation and preserved state

- Focused synthetic participation regressions: **63 passed**.
- Full Python regression: `python -B -W error -m unittest discover -s tests -q`:
  **732 passed** (669 existing + 63 D3J), zero failures, in 97.470 seconds.
- Frontend: `node --test frontend/tests/*.test.js`: **112 passed**, zero failures
  or skips. No frontend file changed.
- The documented cross-period synthetic example executes successfully.
- `git diff --check` and explicit whitespace checks on all three new files pass.

The full Python suite used process-local `TEMP`/`TMP` pointing to the permitted
visualization directory outside the repository for disposable existing-test
fixtures. No existing tests or repository configuration were changed. The new
participation tests and documented example perform no file/network operations
and use no delivered player observations.

Before/after checks cover **144 pre-existing files**. Tracked files, the nine
small protected Parquets and the untracked M4A checklist have matching SHA256
fingerprints and unchanged file metadata. The two large event/360 Parquets have
unchanged sizes and modification timestamps; they were not rehashed or scanned.
This deliberately avoids claiming a fresh byte-level hash check for those two
large inputs. No source-data writes or ingestion occurred, and all 11 protected
Parquets and existing validation datasets remain preserved.

Only these files are new:

- `src/participation_intervals.py`
- `tests/test_participation_intervals.py`
- `docs/d3j-participation-interval-validation.md`

No existing tracked file changed. The staging area is empty. Branch remains
`integration-foundation`, HEAD remains
`32e9a5a3d802b85abbd0ab4e0264ff6c8a8a26fc`, and main remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. Existing untracked processed data,
validation datasets and `docs/m4a-team-approval-checklist.md` remain untouched.
No branch/worktree change, staging, commit, push or deployment occurred.
