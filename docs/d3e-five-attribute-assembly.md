# D3E — policy-gated five-attribute assembly

October 27, 2026. Pure backend framework and controlled synthetic demonstration.
No production player ratings, final OVR, player tiers, frontend integration or
publication. D3D is committed at `cf73ae1` on `integration-foundation`.

## Interface and exact schema

```python
players = assemble_ratings(contexts, slots, candidate_policy=None)
```

`src/rating_assembly.py` accepts explicit lists/tuples and returns a tuple of
immutable `PlayerAssembly` records sorted by canonical context. It performs no
file/network I/O and imports no scoring engine, ingestion script or exporter.
It neither calculates individual ratings nor selects a scoring cohort.

The five slots, in fixed order, are:

| Identifier | Intended attribute |
|---|---|
| `tackles` | Tackles |
| `interceptions` | Interceptions |
| `recoveries` | Ball Recoveries |
| `press_resistance` | Press Resistance |
| `line_breaking_passes` | Line-Breaking Passes, final definition pending |

Each `AttributeSlot` has exactly these fields:

| Field | Contract |
|---|---|
| `attribute_id` | One of the five identifiers above |
| `context` | `PlayerContext(player_id, team, competition_name, season_name)` |
| `score` | Finite real rating in [1,100] when available; exactly `None` when withheld |
| `status` | `available` or `withheld` |
| `reasons` | Immutable tuple of unique nonblank withholding reasons; empty only when available |
| `policy` | `AttributePolicy(attribute_id, policy_id, version, unit, synthetic_only)` or explicit `None` when withheld |
| `evidence` | `RatingEvidence(kind, sources, fixture_id, complete)` or explicit `None` when withheld |
| `scope` | `RatingScope(competition_name, season_name, match_ids, full_season, cohort_id)` or explicit `None` when withheld |
| `comparison_pool_ref` | Nonblank versioned pool reference or explicit `None` when withheld |

`PlayerAssembly` contains `context`, the five `attributes`, `overall`, `notice`,
`production_verified=False` and `publication_authorized=False`. `OverallCandidate`
contains `score`, `status`, `reasons`, `policy` and `tier=None`. This is a separate
in-memory backend contract with no frontend schema/export adapter.

Canonical identity follows the existing identity validator. This boundary accepts
exact integral positive signed-int64 player IDs and already normalized teams;
aliases must be normalized upstream. No identity is guessed or repaired. Duplicate
population contexts and duplicate context/attribute pairs reject the complete call.
Slots outside the explicit population also reject it. Transfers retain separate
team contexts, and different league/season contexts are never joined together.

Scope match IDs must be a nonempty sorted unique tuple of positive exact
signed-int64 integers. Source competition and season must match the slot's
canonical context. `full_season` is a boolean declaration, not a coverage finding.
The caller supplies the cohort and comparison-pool references; this module does
not derive either from labels, minutes or delivered eligibility.

## Approved decisions versus candidate policies

Confirmed project direction is five attributes plus OVR. Gold >=90 and Silver
>=75 and <90 are confirmed boundaries; application to a player score is unresolved.
No tier is assigned here.

For **DRI only**, four 2015/2016 leagues are pooled (La Liga, Premier League,
Serie A, Ligue 1), MID and CB are separate, at least 900 minutes is required,
the three defensive component percentiles have equal weights, and the approved
transform is `clip(65 + 10*z, 1, 99)`. D3E leaves those formulas untouched.

DRI is an aggregate Defensive Recovery Index. Its component percentiles and its
aggregate transformed rating are not approved separate tackles, interceptions
or recoveries 1–100 attributes. DRI is neither a sixth attribute nor an OVR.
No DRI fallback or raw count/per90/percentage conversion exists in this module.

`AttributePolicy` identifies an externally supplied candidate rating. D3E accepts
only `unit="rating_1_100"` and `synthetic_only=True`; it performs no transform.
These labels do not approve or authenticate a transformation. A raw percentage
can numerically resemble a rating, so callers must declare units and policy
honestly; the assembler cannot infer provenance from the number itself.

The following safeguards are conservative implementation boundaries for this
synthetic demonstration, not new team-approved scoring/eligibility decisions:
numeric ratings must be synthetic; OVR requires exact equal scope/cohort and
pool references and one fixture ID across the five slots; expected component
policies must be explicitly pinned. No role, minutes or action threshold is
implicitly inherited from DRI.

## OVR gate, compatibility and missingness

By default, OVR is `None`, status **N/A — POLICY NOT FINALIZED**, with reason
`policy_not_finalized`. Complete individual synthetic scores do not enable OVR.

An explicit `SyntheticOVRPolicy(policy_id, version, component_policies)` enables
only the candidate `equal_weight_mean_of_five`, with `synthetic_only=True`.
The policy must pin one `AttributePolicy` for each of the five distinct attributes,
including its identifier, version and rating unit. Different attributes may have
different versions only if those precise versions are explicitly selected.
Reordering the pinned policies does not affect arithmetic or matching.

All five available scores are required. The candidate is `math.fsum(scores)/5`;
there is no component dropping, weight redistribution, fallback, clipping,
rounding or display formatting. The result is labeled `synthetic_candidate` and
retains its candidate policy object. This is **not a confirmed team decision**.

An omitted slot becomes a retained `withheld` slot with `score=None`, reason
`missing_attribute`, and explicit `None` for unavailable metadata. Explicit
withheld inputs retain all supplied reasons, policy, scope and evidence. Missing
or withheld attributes block candidate OVR. Valid but mutually incompatible
scopes/cohorts, comparison pools, fixture provenance or expected policy versions
also block OVR while retaining the original slots. Reasons identify each failure.

Malformed/contradictory declarations reject the call with `RatingAssemblyError`:
identity conflicts, source-scope season/league conflicts, duplicate contexts,
unsupported attributes, invalid scores (including zero, NaN, infinity, booleans,
strings), withheld numeric values, absent reasons, wrong units or mixed lineage.
Only `None` encodes N/A; NaN is not an alternative missingness representation.
Available attributes cannot carry withholding reasons or omit required metadata.

## Reproducible synthetic example

All actors, matches, policies and numbers below are invented fixture inputs.
They are not derived from counts, per90 rates, percentages or real players.

```python
from src.identity_evidence import SYNTHETIC
from src.rating_assembly import (
    ATTRIBUTES, AttributePolicy, AttributeSlot, EvidenceSource, PlayerContext,
    RatingEvidence, RatingScope, SyntheticOVRPolicy, assemble_ratings,
)

context = PlayerContext(1, "Invented Club", "La Liga", "2015/2016")
scope = RatingScope("La Liga", "2015/2016", (101, 102), True,
                    "invented-cohort-v1")
evidence = RatingEvidence(
    SYNTHETIC, (EvidenceSource(SYNTHETIC, "invented fixture ledger"),),
    "invented-five-ratings-v1", True,
)
policies = tuple(AttributePolicy(a, f"invented-{a}", "v1",
                                "rating_1_100", True) for a in ATTRIBUTES)
scores = (61, 72, 83, 94, 55)
slots = [AttributeSlot(a, context, score, "available", (), policy,
                       evidence, scope, "invented-pool-v1")
         for a, score, policy in zip(ATTRIBUTES, scores, policies)]

default = assemble_ratings([context], slots)[0]  # OVR None
candidate_policy = SyntheticOVRPolicy("invented-equal-five", "v1", policies)
demo = assemble_ratings([context], slots, candidate_policy=candidate_policy)[0]
assert demo.overall.score == (61 + 72 + 83 + 94 + 55) / 5 == 73.0
assert demo.overall.tier is None
```

Removing any slot, including tackles, press resistance or line-breaking passes,
withholds OVR; there is no four-component mean. Even a synthetic OVR >=90
receives no Gold tier.

## Provenance and production limitations

`RatingEvidence` contains an explicit evidence kind, a nonempty immutable tuple
of `EvidenceSource(kind, source)` records, fixture ID and boolean completeness.
Every source kind must equal the declared result kind. Synthetic provenance
requires a nonblank fixture ID; real-data declarations cannot claim fixture
provenance. Relabeling declared synthetic lineage as verified or delivered is
rejected. Mixed source kinds are rejected rather than promoted.

Numeric available slots require complete `SYNTHETIC_TEST_EVIDENCE`. Verified,
delivered, provisional and unverified real-data declarations may be retained on
withheld slots only. These declarations are caller attestations, not independent
authentication. Dishonestly replacing an entire lineage cannot be detected by a
pure assembler; upstream trust and coverage verification remain necessary.

D3B found **840 MID/CB candidate contexts**, **549** passing delivered-table
eligibility checks, and **0 production-ready DRI ratings**. D3E neither consumes
those tables nor upgrades their status. Delivered consistency is not verified
identity, exposure, event completeness or production scoring readiness.

D3D found **0 locally available 2015/2016 360 matches** for the four target
leagues. Missing frames are not zero bypasses or zero line breaks. Later-season
360 observations cannot supply the target-season fifth attribute. Level A
progressive passes do not prove defensive-line-breaking passes. The D3D visible
opponent-bypass diagnostic is not an approved final fifth-attribute definition
or 1–100 transformation. No Level B target-season scores are created here.

## Team decisions and next milestone

Still required: separate tackles/interceptions/recoveries rating transformations;
press transformation and minimum-action threshold; metric-specific role/minutes,
eligibility, cohort and transfer/reference membership policies; final fifth-
attribute definition and transform; OVR formula/weights and its compatibility
rules; player-level tier application; rounding and display precision.

Recommended next milestone: record those decisions in a separately approved
attribute/OVR policy specification, then implement approved transforms with
synthetic regressions. Independently verify target-season source identity,
aligned exposure, metric coverage and comparison populations. Resolve the fifth
attribute's missing evidence before any real-data rating or production export.
Approval alone does not supply data coverage.

## Validation and preservation

Full Python regression: `python -B -W error -m unittest discover -s tests -q`
passed **628 tests** (588 existing + 40 D3E) in 300.638 seconds. The initial run
encountered 52 existing-test errors because the sandbox default temporary
directory denied fixture writes/cleanup. Setting process-local `TEMP` and `TMP`
to a writable temporary directory outside the repository resolved the issue;
the complete rerun passed without test or existing-source modifications.

Frontend regression: `node --test frontend/tests/*.test.js` passed **99 tests**,
zero failures or skips. The documented synthetic example executes successfully.
`git diff --check` and explicit whitespace checks on all three new files pass.
The 40 D3E tests cover five-slot completeness, every missing attribute, default
and explicit OVR gates, exact arithmetic, policy versions, scope/cohort/pool and
fixture compatibility, identity conflicts, duplicates, numeric/missingness
validation, provenance promotion rejection, transfers, ordering, immutability,
no tiers, no production publication, and no file/network operations.

Existing scoring, frontend, identity trust, D2/D3 interfaces and prior approval
documents are unchanged. No staging, commit, push, deployment, dataset download,
ingestion or production output writer is part of D3E.

All existing tracked files match their pre-work SHA256 fingerprints byte for
byte. Branch remains `integration-foundation`, HEAD remains `cf73ae1`, and
`main` remains `179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. The only new files
are `src/rating_assembly.py`, `tests/test_rating_assembly.py` and this document;
all are untracked/unstaged. Pre-existing untracked processed/validation data and
`docs/m4a-team-approval-checklist.md` remain preserved.

Protected Parquets were SHA256-checked before and after implementation against
the D3D inventory. Every result matches.

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
