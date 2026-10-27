# D3A — team-approved Defensive Recovery Index

Decision record: October 27, 2026. Implementation scope: pure backend DRI
mathematics and synthetic regression tests. No official real-player scoring,
rankings, output datasets, frontend integration or publication.

## Attribution and decisions

Methodology adapted from Pratyush's
`src/metrics/defensive_recoveriesv2.py`, inspected read-only via
`git show origin/pratyush-dev:src/metrics/defensive_recoveriesv2.py`.
The local remote-tracking ref resolves to
`f024cbf6e952c7353bdd8c8be3973112c6f92113`. The writer script was neither
imported nor executed; no contributor branch was merged.

The integration lead communicated the following **team decisions** in the D3A
request on October 27, 2026; no individual approver names were supplied:

- Final attribute set: Tackles, Interceptions, Ball Recoveries, Press Resistance,
  Line-Breaking Passes. The intended player experience has five 1–100 attributes
  and an overall rating. D3A implements only the DRI component.
- Equal weights for the three defensive component percentiles.
- At least 900 minutes; MID combines DM and CM, CB is separate.
- Joint four-league **2015/2016** population: La Liga, Premier League, Serie A,
  Ligue 1. MID and CB never share a normalization distribution.
- DRI FIFA transform: clip(65 + 10 × z, 1, 99).
- Gold at score ≥90; Silver at 75≤score<90. Which player-level score receives a
  tier remains undecided.

These confirmations supersede the corresponding pending proposals in M4A for
this DRI scope. Existing M4A documents/checklist are preserved unchanged; no
other proposal is implicitly approved.

Still open: exact overall OVR formula and attribute aggregation; the fifth
attribute's line-breaking definition; application of final player tiers.
The 30-pressure-action minimum remains tentative and is not enforced here.

## Pure interface and explicit evidence

`src/dri_scoring.py` exports:

- `score_dri(population, measurements, *, pool=ComparisonPool(...))`
- immutable `ComparisonPool`, `SeasonScope` and `Evidence` declarations
- `DRIResult(players, pools, metadata)`, `DRIError`
- `fifa_from_zscore(z)` and separate `classify_tier(score)` helpers

There is no file/network I/O, CLI, writer, frontend import or production export.
Caller must validate upstream identity, role, measurements, exposure and evidence
before constructing these inputs; this module also validates their explicit
structure and consistency. Evidence declarations are caller attestations, not
source authentication performed by D3A.

Canonical key K is `player_id, team, competition_name, season_name`, using existing
M2A normalization and exact integer-ID validation. Team contexts remain distinct.

Input DataFrames use exactly these columns:

| Input | Columns after K |
|---|---|
| Population: one row per canonical context | `position_group, reference_member, minutes, exposure_scope, identity_evidence, context_evidence, exposure_evidence` |
| Measurements: up to one row per K/event type | `event_type, count, minutes, per90, rate_status, numerator_scope, reportable, reportability_source, coverage_evidence` |

Measurement fields match the integrated recovery totals' meanings: event type
is exactly Tackle, Interception or Ball Recovery; count is a known exact
nonnegative signed-int64 integer; per90 is events/90min. The existing successful
event filters and rate formula are not modified. An upstream assembler can
project those fields from `RecoveryResult.totals`; it must supply the remaining
evidence from independently validated sources. Row presence is insufficient.

`SeasonScope(competition_name, season_name, match_ids, full_season)` requires a
nonempty, sorted unique tuple of exact positive match IDs. Each component's
numerator scope must equal the population exposure scope, including all match
IDs and the full-season declaration. Scope must match that row's competition and
season. A partial match window cannot use wider full-season minutes.

`Evidence(kind, source, complete)` requires a nonblank reference and a real boolean.
The pool declares either existing `VERIFIED_SOURCE_EVIDENCE` or
`SYNTHETIC_TEST_EVIDENCE`. Every identity/context/exposure attestation and every
component coverage attestation must match that kind and be complete. The pool
also needs complete coverage evidence for its declared four-league population.
Delivered consistency, unverified, incomplete or provisional evidence withholds
scoring. Synthetic evidence cannot satisfy a verified pool.

Each component additionally needs `reportable=True` and a nonblank
`reportability_source`. Truthy strings and numeric flags are rejected.
`None` explicitly records absent structured evidence; it never establishes trust.
Existing D1 evidence gates remain unchanged and are not bypassed or recreated.

## Eligibility and population policy

The caller explicitly supplies the candidate population and boolean
`reference_member` for every row. DM and CM map to MID; explicitly declared MID
is also accepted; CB stays CB. Missing, AMBIGUOUS and unsupported roles retain N/A
with different reasons. No dominant role, playing position or club is guessed.

A selected context needs positive minutes ≥900, all three complete reportable
components, supported per90, full-season matching scopes, and all required
coverage/identity/exposure evidence. Verified observed zero is a valid
measurement; a missing component/value is not zero. Missing numeric values
(`None`, pandas NA/NaN) remain missing. Strings, booleans, complex values,
negative values, infinity, fractional/inexact counts and contradictory supplied
per90/exposure arithmetic reject the call without coercion.

All population rows survive. Out-of-policy seasons/competitions retain
`invalid_pool_membership` and no scores; they cannot affect approved pools.
A pool declaration for another season or league set rejects the call.
Measurements outside the explicit population, unresolved IDs, duplicate
canonical identities/components and normalized alias collisions reject the call.
Component and population minutes must agree exactly; rate/count/minute arithmetic
is checked with relative and absolute tolerance 1e-9.

All applicable withholding reasons are retained in a deterministic tuple,
including below-minutes, missing component/measurement, missing/zero minutes,
unsupported per90, reportability, provenance/coverage, role, scope and membership.
No missing-score imputation, weight redistribution or hidden row filtering occurs.

**Conservative transfer safeguard, not an approved final transfer policy:**
at most one explicitly selected reference context per player/season across both
position pools and all four leagues. Multiple selected contexts reject the call
even if roles/leagues differ. Caller must explicitly designate a reference
context or mark all transferred contexts non-reference pending policy approval.
Non-reference contexts remain visible with N/A; they are neither collapsed nor
scored against the cohort. No automatic club choice or cross-team aggregation is
implemented. A future aggregate-transfer model needs separate approval/evidence.

## Exact mathematics

For an eligible group of n members, with each component's supplied per90 x:

```text
P_component = 100 × rank(x, ascending=True, method="average") / n
DRI = (P_tackle + P_interception + P_ball_recovery) / 3
DRI_percentile = 100 × rank(DRI, ascending=True, method="average") / n
DRI_zscore = (DRI - mean(DRI)) / std(DRI, ddof=1)
DRI_FIFA = clip(65 + 10 × DRI_zscore, 1, 99)
```

Component weights are exactly equal. DRI z-scores use DRI values, not DRI
percentiles. DRI is not final OVR. Decimal precision is retained, not rounded.
Half-integer average ranks are summed before conversion to DRI percentages to
avoid false differences from floating-point summation of tied rank fractions.
Inputs and outputs are canonically ordered before statistical reductions.

**Conservative statistical safeguards, not a new approved sample-size threshold:**
fewer than two eligible reference contexts cannot support sample standard
deviation; a constant DRI distribution cannot support differentiated z-scores.
All derived score columns remain NaN with N/A in either case. Identical DRI
values are checked directly to avoid a tiny floating-point standard deviation
creating artificial ratings. Empty pools are reported instead of omitted.
Component-constant pools can still score if the combined DRI varies.

`players` exposes all contexts, roles/groups, pool ID, membership flag, minutes,
component rates, eligibility, status/reasons, three component percentiles, DRI,
DRI percentile, z-score and DRI FIFA rating. Data eligibility can be true while
statistical status is N/A. `pools` exposes exact eligible canonical keys/counts,
all four declared leagues, per-league member counts, mean/sample deviation and
withholding reason for each separate MID/CB pool. A league with no eligible
members has an explicit zero membership count, not assumed source completeness.
`metadata` records policy/evidence mode and always
`publication_authorized=False`.

## Synthetic worked examples

These are controlled mathematical fixtures, not real-player records or genuine
season manifests.

Four eligible MID contexts (one in each declared league), with component per90s
(1,1,1), (2,2,2), (3,3,3), (4,4,4):

| Synthetic context | Each component percentile / DRI | DRI percentile | DRI z | DRI FIFA (shown to 6 decimals only) |
|---|---:|---:|---:|---:|
| 1 | 25 | 25 | -1.161895 | 53.381050 |
| 2 | 50 | 50 | -0.387298 | 61.127017 |
| 3 | 75 | 75 | 0.387298 | 68.872983 |
| 4 | 100 | 100 | 1.161895 | 76.618950 |

Mean =62.5; sample variance =3125/3; sample deviation =32.27486121839514.
Implementation retains full float precision. With component vectors
(1,1,1), (1,1,1), (3,3,3), (4,4,4), the first two contexts each receive
37.5 for component percentiles, DRI and DRI percentile (average tie ranks).

With MID vectors (1,1,1), (2,2,2) and CB vectors (100,100,100),
(200,200,200), each pool independently has DRI values 50 and 100 and
z=±1/√2. Neither pool changes the other's normalization. Clipping is also
tested on synthetic 100-member distributions and the standalone transform.

## Tier helper and differences from V2

`classify_tier` accepts finite scores in [1,100], returns Gold at ≥90, Silver
at ≥75 and <90, otherwise None. Missing values return None; out-of-domain inputs
reject. The helper is never called automatically by `score_dri`. No tier column
or final player-tier publication is produced.

Compared with Pratyush V2:

- Preserve per90 components, ascending average ties, equal-weight DRI, independent
  MID/CB distributions, ≥900 minutes, sample z-score and unrounded 1–99 transform.
- Replace the source's Silver ≥70 with the newly confirmed ≥75 helper.
- Withhold singleton/constant ratings instead of manufacturing z=0/rating65.
- Use explicit caller evidence, scopes, population and transfer decisions rather
  than loader flags and implicit filtering. Retain N/A reasons/contexts.
- Reject invalid numbers without numeric/string flag coercion; enforce existing
  canonical identity contracts, unique keys and exact count validation.
- Omit source file loaders/writers, automatic per-component FIFA ratings,
  archetypes and automatic component/DRI tiers. No final OVR is implemented.
- Do not execute the contributor writer on the duplicate-key original recovery
  delivery. Corrected deliveries may be structurally compatible, but their row
  presence/flags do not establish required source completeness or provenance.

## Real-data boundary and next milestone

The existing 82 D2C/D2D Bundesliga 2023/2024 contexts cover four local match
windows. They are neither the approved four-league 2015/2016 population nor
production-verified full-season measurements. No real dataset was scored in D3A.
No partial counts were paired with full-season minutes; no dataset output file
or public JSON was generated. The synthetic tests use explicit synthetic
evidence; a mock verified-evidence test exercises caller attestations only.

Next milestone: validate an explicit, independently supported four-league
2015/2016 population with full-season recovery/exposure and per-component
reportability evidence; settle transfer/role ambiguity policy; then exercise a
private in-memory scoring review. Production publication and overall OVR need
separate decisions. Continue investigation of line-breaking and the tentative
pressure minimum separately; do not substitute existing progression for an
unapproved fifth attribute.

## Regression, integrity and Git

Focused tests cover all formulas/boundaries and validation rules above, including
constant pools of different sizes, opposing-rank cancellation, verified observed
zero versus missing data, cross-pool transfer duplication, deterministic order,
immutability, no I/O and no OVR output.

Full Python: `python -B -W error -m unittest discover -s tests -q` —
**491 tests passed** (447 existing +44 D3A).
Recursive frontend JavaScript: **99 passed**, none skipped.
`git diff --check` and new-file whitespace checks pass.
All existing interfaces and source files remain unchanged.

All 11 Parquet SHA256 values match the pre-work inventory and D1B/D2C/D2D records:

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

D2D prerequisite passed: committed at
`b848613287a449971f0638248c8fbec28a688b29`. That remains HEAD.
Branch remains `integration-foundation`; main remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`.
Only three new files: this report, `src/dri_scoring.py` and
`tests/test_dri_scoring.py`. No pre-existing tracked file changes; the untracked
M4A approval checklist and dataset files remain unchanged.
No staged files, commits, pushes, merges, branch/worktree operations, resets,
ingestion, score outputs or deployments.

