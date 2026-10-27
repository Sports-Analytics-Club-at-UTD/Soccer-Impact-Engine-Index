# D3D — line-breaking pass feasibility and candidate metric

**CANDIDATE / DIAGNOSTIC / NOT PRODUCTION APPROVED.**

Review date: October 27, 2026. D3C prerequisite passed: committed at
`a1eb5bd097f6c5557cf808c9988f54cc25b32376`.
No official fifth-attribute definition, rating, OVR, tier or production export is
approved or generated. Existing approval records remain unchanged.

## Definitions and contributor reference

Joseph's locally available reference is `origin/Joseph-dev` at
`013c8edd5196a15ac826558f4b0964cc6f3a3e58`,
`src/metrics/line_breaking.py` and `docs/press_resistance_line_breaking.md`.
These were inspected using Git object reads; no branch switch, fetch, module
execution, acquisition or writer invocation occurred.

**Level A — existing progressive-pass proxy:** the unchanged M3B implementation
uses completed open-play passes, advancing at least 10 pitch units and ending
at most 75% of the starting distance from the attacked goal at (120,40).
Its separate value weights distance gained by an explicitly calibrated
completion-difficulty term. It does not observe opponent locations.

**Level B — Joseph's candidate visible-opponent bypass:** for a completed
open-play pass in normalized positive-x coordinates:

```text
opponents_bypassed = count(visible observations where
    teammate == False AND keeper == False AND x_start < opponent_x < x_end)
candidate_line_break = opponents_bypassed >= 3
```

This counts visible **outfield opponents**, not independently identified
defenders or a modeled defensive line. Lateral distance from the pass path is
ignored; no minimum 10-unit advancement or Level A progress requirement is added.
The three-opponent threshold is Joseph's convention, not a team-approved
football-science definition. Camera omissions make it a visible-sample count;
failure to reach three cannot prove that no actual defensive line was broken.

Joseph's source prints a global median actor-to-start orientation check but does
not enforce per-pass alignment before counting. It also uses match-level any-360
coverage and a provisional 450-minute gate for Level B per90. D3D adopts neither
as production eligibility or exposure verification.

## Actual local schema and feasibility boundary

The local 360 Parquet has **7,562,022 observation rows**, with this actual schema:

| Field | Arrow type | Meaning / limitation |
|---|---|---|
| id | large_string | Associated event UUID; repeats across visible observations |
| visible_area | list<double> | Repeated flat x/y polygon for the event snapshot |
| match_id | int64 | Match association |
| teammate | bool | Same team as the actor; not an independent team ID |
| actor | bool | Actor observation indicator |
| keeper | bool | Keeper indicator; False identifies outfield observations |
| location | list<double> | Visible observation x/y point |
| competition_name | large_string | Delivered context label |
| season_name | large_string | Delivered context label |

There is no visible-player ID/name, observation ID, separate frame timestamp/ID,
explicit usable-frame flag, attacking-direction field or full-camera/team
completeness declaration. Event UUID identifies the associated snapshot, not a
visible person. Repeating UUID or visible_area across different people is normal;
it is not itself duplicate data.

The event source has 3,626,433 rows. Its event/match/team/context, pass locations,
pass type/outcome and recovery failure flag support the read-only coverage audit.
It is a filtered action export, not an independently complete fixture/event feed.

Field semantics support a **pure geometric candidate with explicit validated
inputs**. They do not support guessing defender identities, silently removing
tracking duplicates, inferring attacking direction from a median, or treating
frame presence as complete observation coverage. In particular, the available
file has **no 2015/2016 frames for any of the four target leagues**.

## Measured coverage and quality findings

The full bounded audit found **445,569 distinct frame-event
UUIDs** across **127 observed matches**, not 7.56 million separate frames.

| Local slot | Season | Observation rows | Distinct frame events | Matches with frames |
|---|---|---:|---:|---:|
| 1. Bundesliga | 2023/2024 | 1,953,538 | 118,607 | 34 |
| La Liga | 2020/2021 | 2,181,953 | 128,840 | 35 |
| Ligue 1 | 2021/2022 | 1,475,775 | 86,352 | 26 |
| Ligue 1 | 2022/2023 | 1,950,756 | 111,770 | 32 |

These four slots exhaust the local file. Availability is an observation about
this checkout, not a claim about all StatsBomb products or seasons elsewhere.

### Approved 2015/2016 scope

| League | Observed event matches | Pass events | Completed open-play passes | Matched pass frames | Missing frame rate |
|---|---:|---:|---:|---:|---:|
| La Liga | 380 | 365,288 | 247,613 | 0 | 100% |
| Premier League | 380 | 368,619 | 255,553 | 0 | 100% |
| Serie A | 379 | 372,636 | 257,615 | 0 | 100% |
| Ligue 1 | 377 | 374,239 | 259,725 | 0 | 100% |

Across the four leagues: **1,480,782 pass events**, including **1,020,506 completed
open-play passes**, have **zero matching frames**. No Level B assessment can be
made for them. Two of the completed La Liga passes also fail the strict on-pitch
geometry guard; 1,020,504 completed eligible passes have valid geometry but still
no frames. No frame absence was converted to a zero bypass count.

### Frame-bearing slots: event-level denominators

Here eligible means completed open-play Pass under M3B's source conventions.
All eligible passes in these four slots have finite on-pitch endpoint geometry.
Joins use event UUID plus match, competition and season, never match presence
alone.

| Slot | Passes with frames / all passes | Eligible with frames / all eligible | Missing eligible frames |
|---|---:|---:|---:|
| 1. Bundesliga 2023/2024 | 30,203 / 39,214 | 24,787 / 31,073 | 6,286 (20.23%) |
| La Liga 2020/2021 | 36,912 / 40,337 | 30,446 / 32,225 | 1,779 (5.52%) |
| Ligue 1 2021/2022 | 23,816 / 29,090 | 20,063 / 23,608 | 3,545 (15.02%) |
| Ligue 1 2022/2023 | 29,684 / 36,878 | 25,253 / 30,443 | 5,190 (17.05%) |

Every observed event match in these slots has some 360 rows, yet the eligible
pass frame miss rate ranges **5.52%–20.23%**. Thus Joseph's match-level any-360
criterion cannot establish pass-level completeness. None of these later-season
slots belongs to the approved 2015/2016 comparison population.

### Usability and orientation exclusions

The audit explicitly used a **2 pitch-unit actor alignment tolerance** as a
diagnostic choice, not a team-approved threshold or inference of direction.
Structural usability requires known flags, a single teammate actor, usable
coordinate/polygon structure and no ambiguous duplicate observations.

| Slot | Matched eligible frames | Structurally usable | Native actor-aligned | Native/mirror ambiguous | Mirror only | Neither aligned |
|---|---:|---:|---:|---:|---:|---:|
| 1. Bundesliga 2023/2024 | 24,787 | 22,125 | 22,123 | 5 | 0 | 2 |
| La Liga 2020/2021 | 30,446 | 26,871 | 26,871 | 0 | 0 | 0 |
| Ligue 1 2021/2022 | 20,063 | 16,798 | 16,793 | 3 | 0 | 5 |
| Ligue 1 2022/2023 | 25,253 | 21,257 | 21,252 | 8 | 2 | 3 |

Structural usability is **not** a full source/orientation attestation. Native
actor-aligned includes the native/mirror ambiguous cases. Across these slots,
87,051 matched eligible frames pass structural guards and 87,039 align natively
within the diagnostic tolerance; 16 align with both native and mirrored views,
2 only with the mirrored view, and 10 with neither. No automatic flip occurred.
Median actor-to-start distance is approximately **0.000001573 pitch units** in
each slot's structural sample, supporting coordinate alignment without proving
which goal the team attacks.

The raw schema contains no independent attacking-direction attestation, usable
snapshot declaration or per-visible-person uniqueness evidence. The audit
therefore reports zero passes satisfying *all explicit direction/evidence
prerequisites*, not zero line-breaking passes. No real player Level B numerator
was produced from this structural audit.

Across all 445,569 snapshots:

- **392,157** are structurally usable under the conservative guards;
  **53,412** are excluded.
- All nine parent fields have **zero nulls**. A separate projected-coordinate
  check found every location has exactly two finite, nonmissing coordinates.
- **62,301 observation rows** are finite but outside the 120×80 pitch.
  These are the coordinate-bound exclusions, **not NaN/infinity or automatically
  proven source corruption**. A player can be outside the pitch; this candidate
  conservatively rejects a snapshot containing such a point instead of clipping
  it or silently dropping that person. The team must review this handling.
- **53,267 snapshots** hit that coordinate-bound guard. Additional quality
  reasons include ambiguous duplicate observations (132), ambiguous coincident
  points with different flags (8), and multiple actors (13) among inspected
  otherwise-valid records. Reason counts overlap and may stop at an earlier
  numeric rejection; they must not be summed as exclusive outcomes.
- Independent signature counting across every supplied snapshot found **149
  repeated observation rows in 143 frame events**. These are repeated
  flag/location signatures, not verified duplicate identities: no visible-player
  ID exists to distinguish duplicates from genuinely coincident people.
- Actor flags identify one actor in **445,550** snapshots and two in **19**.
  Some multi-actor cases also fail the coordinate guard.
- Noncontiguous repeated frame-event blocks: **0**; conflicting frame/event
  contexts: **0**; shared event/frame context mismatches: **0**.
- All **3,626,433** source event UUIDs are unique.
  **196,693 frame UUIDs** do not occur in the filtered six-type event source.
  This does not establish lost passes: omitted UUIDs cannot be assigned a type
  from this file, and the event export is not the complete action feed.

The method deliberately distinguishes source observations, structural checks,
attested usability and an assessed metric. None implies complete opponents,
full-season source coverage or validated defensive-line semantics.

### Observable failed Ball Recovery flags

The full event source contains **13,802 failure=True Ball Recovery records** and
**175,654 with a missing failure flag**, with **0 explicit False** records.
Existing M2B treats the latter as non-failed and retains them; D3D changes neither
raw flags nor that definition. The audit makes no link to a preceding pass and
does not reinterpret any failed recovery as a line break.


## Pure implementation and safeguards

`src/line_breaking_candidates.py` is separate from Level A and all scoring/export
contracts. It provides:

- `assess_passes(passes, frames, *, frame_evidence, policy)`
- `JosephCandidatePolicy(policy_id, source, actor_alignment_tolerance)`
- `frame_quality(records)` and explicit `normalize_point(point, direction=...)`
- `aggregate_candidates(assessments, *, crosswalk, population)`

Pass inputs require event/match/context/team, actor name (for existing M2A when
aggregating), optional canonical player ID, x0/y0/x1/y1, explicit completed and
open_play flags, and normalized orientation plus its source. Raw preparation
must retain M3B's open-play convention (missing pass_type, Recovery or
Interception) and completion convention (missing pass_outcome).

Frame observations use the actual nine fields above. A separate one-row-per-event
evidence table requires usable, observations_complete,
one_row_per_visible_player, normalized orientation/source and source/evidence_kind.
These are explicit caller declarations, not invented fields in the raw Parquet.
Observations-complete refers to the supplied snapshot's observations, not all
opponents on the pitch or a full season. Source evidence is preserved and never
promoted to independently verified identities or production metric approval.

Before any candidate count:

- Event IDs are unique; event/match/competition/season associations must agree
  across inputs. Contradictory evidence/event IDs reject rather than choose first.
- Coordinates are finite real values on the 120×80 pitch. Missing coordinates
  withhold; nonnumeric, infinite and off-pitch coordinates reject the pure metric.
  This is a conservative usability guard, not a change to existing Level A's
  finite off-pitch behavior.
- Frame flags are actual booleans or missing; unknown team/keeper flags withhold.
- Visible-area data must be finite, nondegenerate, structurally consistent polygon
  data. This check does not certify complete camera coverage or a football model.
- Exactly one actor must be present and marked teammate. The actor must align
  with the pass start within the caller's explicit tolerance.
- Exact repeated location/flag signatures, or coincident points with conflicting
  flags, make the frame ambiguous. No row is arbitrarily removed and no unique
  visible-person identity is inferred from coordinates.
- Both pass and frame require explicitly sourced positive-x orientation. Actor
  alignment alone cannot establish direction. There is no automatic flip.

`normalize_point` performs a 180-degree rotation `(120-x,80-y)` only for an
explicitly supplied negative_x direction. Callers must consistently transform
pass endpoints, observations and visible-area points and supply orientation
evidence; the helper does not decide direction from data.

The threshold stays exactly three; no corridor-width/defender-spacing rule is
silently added. Additional usability guards and missing-value handling are
deliberate conservative differences from the contributor writer.

Every input pass survives with one of three exclusive statuses:

| Status | Meaning | Count / candidate flag |
|---|---|---|
| assessed | Eligible pass with usable, explicitly supported frame | Observed integer (including 0) / boolean |
| ineligible | Unsuccessful or non-open-play pass | N/A / N/A |
| unassessed | Missing/unknown eligibility, geometry, orientation, frame or ambiguous observations | N/A / N/A |

Reasons remain attached. A missing frame is never zero opponents or a False
performance assessment. A genuine usable frame with no qualifying visible
opponents produces observed0 and False. Backward positive-x passes have no
strictly-between forward opponents under Joseph's exact convention.

## Diagnostic canonical-player aggregation

Aggregation calls unchanged M2A strict identity resolution before returning
player counts. Supplied stable IDs or a caller-trusted contextual crosswalk are
required; no name-only grouping or fuzzy mapping occurs. Unresolved identities
reject player aggregation; known outsiders remain separately accounted in the
full event ledger. This resolver call is not a D1 source-verification attestation.

Canonical contexts preserve player_id/team/competition_name/season_name,
including transfers. Counts retain observed passes, assessed eligible passes,
candidate line breaks, summed visible opponents, unassessed passes and excluded
passes/reasons. Match/event ID sets, policy IDs, source labels and the original
event-level evidence remain available. The count categories conserve every
selected input row; reason counts are nonexclusive diagnostics.

A context with no assessed passes has N/A candidate sums, not invented zeros.
Unobserved population rows are not synthesized. Scope is always labeled the
supplied observed pass window with scope_complete=False. There is no minutes
input or per90 API, so sample counts cannot acquire full-season denominators.
No rankings, 1–100 ratings, OVR or tier logic exists here.

## Synthetic examples and failed recoveries

Controlled fixture: completed open-play pass `(30,40) → (70,40)`; actor at the
start; valid synthetic frame/evidence; outfield opponents at `(40,20)`, `(45,21)`
and optionally `(50,22)`.

| Supplied frame | Level A progressive? | Joseph bypass count | Candidate break |
|---|---|---:|---|
| Two opponents | Yes | 2 | False, assessed |
| Three opponents | Yes | 3 | True, assessed |
| Usable frame with no outfield opponents | Yes | 0 | False, assessed |
| Missing frame | Yes | N/A | N/A, unassessed |
| Duplicate opponent observation | Yes | N/A | N/A, ambiguous |

Level A sees d0=90, d1=50 and forward gain40, so it is progressive regardless of
frame availability. This does not establish multiple opponents bypassed.
The y positions demonstrate that Joseph's candidate is an x strip, not a pass
corridor. These are invented geometric examples, not real player results.

Failed Ball Recovery is separate from successful Ball Recovery: the unchanged
M2B extractor excludes a recovery with failure=True and retains a non-failed
recovery. The tests verify both. D3D does not modify that definition.

An unsuccessful defensive action does not prove that a previous pass broke a
line. Mere event order cannot establish causation, responsibility or linkage.
The pure candidate accepts neither a preceding-recovery-failure shortcut nor a
causal compensation formula. Pass completion/progression and visible opponent
positions answer different questions.

## Alternative definitions and required team decisions

The official fifth attribute is **not currently calculable as Level B for the
approved 2015/2016 population from the local files**. Existing Level A may remain
an observed progressive-pass proxy; it must not silently be relabeled the official
line-breaking attribute or used to fill absent 360 assessments.

Separate candidates worth reviewing, not implemented or approved here:

- Pass-corridor geometry, with an explicitly chosen width and opponent relation
  to start/end; aerial passes and endpoint/camera visibility need policies.
- Defensive-line clustering/spacing, with a defined cohesive opponent line,
  role/spacing assumptions, crossing criterion and temporal validation.
- An explicitly named event-only progressive-pass attribute if the team chooses
  that proxy rather than a defender-bypass definition.

Team decisions are needed on the metric name/meaning; adoption or replacement
of Joseph's x-strip ≥3 convention; direction/actor alignment and duplicate policy;
camera visibility/reportability requirements; eligible roles/open-play convention;
reference scope and exposure requirements; and any future attribute mapping.
Joseph's provisional 450 minutes is not adopted. No scoring weights or overall
formula are decided by D3D.

Next milestone: review the candidate examples and explicitly choose the fifth
attribute definition. If Level B is retained, establish the specific required
frame/direction/visibility evidence for the intended population before planning
an authorized data or scoring step. This audit performs no acquisition and makes
no claim about data availability outside the local checkout.

## Reproducible audit, tests and integrity

New files only:

- `src/line_breaking_candidates.py`
- `scripts/audit_line_breaking_feasibility.py`
- `tests/test_line_breaking_candidates.py`
- `docs/d3d-line-breaking-feasibility.md`

Run the read-only audit from the repository root:

```powershell
python -B -W error -m scripts.audit_line_breaking_feasibility `
  --events data/validation/drive-raw-review/statsbomb_team_events.parquet `
  --frames data/validation/drive-raw-review/statsbomb_360_frames.parquet `
  --actor-tolerance 2 `
  --scratch-dir $env:TEMP
```

The scan projects ten event fields and the nine frame fields. It reads Arrow
batches of 16,384 rows by default (maximum 65,536), carries at most 129 observations
for one frame, and buffers at most 1,000 frame summaries. A cleaned-up temporary
SQLite database, with a 64 MiB cache and file-backed sorting, holds event/frame
indexes. Bulk indexes avoid unnecessary incremental random-UUID writes. No
multi-million-row pandas table or whole-file Python event-ID set is loaded.
Only diagnostic terminal JSON/progress is printed; no production JSON/CSV/Parquet,
ingestion, acquisition or network requests occur.

Conflicting frame contexts are quarantined without choosing a first match;
repeated frame blocks become unusable. Event UUID duplicates reject rather than
deduplicate. Geometry, matching, medians and native/mirror comparisons are
read-only diagnostics. A second Arrow projection independently cross-checked
slot row counts and the finite/off-pitch coordinate classification.

**29 focused tests** cover known 2/3-opponent cases, strict boundaries, no
corridor substitution, keeper/teammate exclusion, real observed zero versus
missing frame, duplicate/coincident observations, flags, missing/nonfinite/
off-pitch geometry, orientation and explicit rotation, completion/open-play
exclusions, context uniqueness, canonical transfers/known outsiders/unresolved
IDs, conservation, source labels, row-order invariance, immutability, failed
recoveries, Level A versus B, and absence of ratings/writers/network operations.
Synthetic audit fixtures also span row groups/batches and test noncontiguous
duplicate blocks, contradictory match contexts, source preservation and
temporary-index cleanup.

Final regression: `python -B -W error -m unittest discover -s tests -q` —
**588 passed** (559 existing + 29 D3D). Recursive frontend JavaScript:
**99 passed**, none skipped. `git diff --check` and new-file whitespace checks pass.

All 11 protected Parquet SHA256 fingerprints match the pre-work and D1B/D2C/D2D
inventories. Both large raw files were opened read-only.

| Preserved input | SHA256 | Result |
|---|---|---|
| `data/processed/player_minutes.parquet` | `9701ec4a74b1a75ee6094f08619c40b26f6d6f103d64a23ca2802448351e931b` | PASS |
| `data/processed/player_name_crosswalk.parquet` | `a250ac8074967aad3b1fdcd35a849584658ac333a4049d1de3845f443d2397e7` | PASS |
| `data/processed/recovery_per90.parquet` | `056f94b0bd49bc707e5d00181d0b85654cd076e5dc3bc09e1a6c121cd530ee4d` | PASS |
| `data/raw/statsbomb_lineups.parquet` | `dfb6e2f0adfb1ec25c879b26feb3616b8683c64e152657f098edc20aa1635be2` | PASS |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | `01f1bb2650df4f793971465eefad49eefcd41a302789b5c5009cf7355a4b1694` | PASS |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | `7a546348b2c391d32221456fab259d639910d13c8e672ba030e6d30b38cab61f` | PASS |
| `data/validation/arpit-match-context-review/match_metadata.parquet` | `1b1de360e0f31c49aabd43d065f95fe0762d29a31ea2bcba21b54571b86f3b47` | PASS |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | `5600f1250a3bd7fcf9d12a9d11ecac4ae9d39cd58898d6e6df1e5d4d1aa1830e` | PASS |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | `5b53d544662826206511e2d2c532297160b781f84958b2acf615195590f82012` | PASS |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | `497fa459e1ee99f758ed37d405d69285af5e6759306851456d03fde8c4025625` | PASS |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | `ec12fdd2340fb125671f4996abdac510c3dc6d81555848792520ce5df2519eb8` | PASS |

All 131 pre-existing fingerprinted files remain unchanged, including M3B Level A,
M2B recovery, M3A press, D3A DRI, D3C candidate scoring, D2 diagnostics, frontend,
identity/trust and the untracked M4A checklist. Branch remains
`integration-foundation`; HEAD remains
`a1eb5bd097f6c5557cf808c9988f54cc25b32376`; main remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`.
Only the four D3D files are new and untracked; the pre-existing untracked datasets
and M4A remain preserved. No tracked changes, staged files, branch/worktree
operations, commits, pushes, deployments, official scores or production outputs.

