# D3C — press resistance scoring candidates

**CANDIDATE SCORING — NOT PRODUCTION APPROVED.**

Review date: October 27, 2026. Scope: pure backend experiments with synthetic
fixtures only. No real-player ratings, public score outputs, player tiers or
overall OVR are produced.

D3B prerequisite passed: committed at
`aa7864cb3da7a07ec43f0d04f2923435e6ef84bf`.
Contributor reference inspected read-only:
`origin/pratyush-dev:src/metrics/press_resistancev2.py` at
`f024cbf6e952c7353bdd8c8be3973112c6f92113`.
The contributor module and writers were not imported or executed.

## Confirmed direction versus candidate policy

The integration lead's D3C request confirms five future 1–100 attributes,
joint consideration of the four 2015/2016 leagues, Gold ≥90 and Silver ≥75 and
<90. D3C neither assigns tiers nor decides which eventual score receives them.

D3A's 900-minute minimum, DM+CM grouping, separate CB population and FIFA
transform are approved **for DRI**. They are not inherited as approved press
policy. For press, minimum minutes, 30 versus 50 actions, role pooling,
minimum reference size, reference unit, transformation and precision policy
remain candidates. The 30-action statement was tentative, not final approval.
Exact overall OVR and line-breaking remain outside this milestone.

## Existing integrated M3A metric

The unchanged `src/metrics/press_actions.py` and `src/press_resistance.py`:

- Select Pass/Dribble events with under_pressure=True; missing pressure is
  excluded. No new pressure definition is introduced.
- Count all selected pass/dribble attempts. A pass completes when pass_outcome
  is missing; a dribble completes only when dribble_outcome is Complete.
- Resolve canonical identity before selected-player aggregation.
- Compute combined actions A=pass_attempts+dribble_attempts and successful actions
  S=pass_completed+dribble_completed.
- Compute press resistance **100 × S/A**, N/A when A=0.
  Pass/dribble completion percentages remain separate diagnostics.

The combined percentage is attempt-weighted, never the mean of pass and dribble
percentages. Minutes are an eligibility input, not a divisor for this metric.
D3C calls the existing M3A rate helper after stronger exact-count validation.
Its tests also feed actual synthetic event output from integrate_press_resistance
through the candidate consumer and check parity.

## Pure interface: no implicit policy defaults

New `src/press_scoring.py` exports immutable `SyntheticEvidence`, `PressScope`,
`CandidatePolicy`, `ComparisonPools`, plus `CandidatePressResult`,
`PressScoringError` and:

```python
result = evaluate_press_candidates(
    population, actions,
    pools=comparison_pools,
    evidence=synthetic_dataset_evidence,
    policy=explicit_candidate_policy,
)
```

All keywords are required. Passing policy=None returns raw synthetic
measurements and withheld scores with candidate_policy_not_selected; omitting
policy raises a call error. There is no automatic 30-action, 900-minute or score
formula selection.

CandidatePolicy requires every field, without defaults:

| Field | Explicit meaning |
|---|---|
| policy_id, source | Stable experiment identifier and policy provenance |
| formula | One of the two precise candidate mappings below |
| min_actions | Nonnegative exact integer threshold; 30 and 50 tested |
| min_minutes | Finite nonnegative candidate threshold; 900 boundary tested |
| pooling | separate_mid_cb or combined_mid_cb |
| min_pool_size | Explicit integer ≥2; no hidden 20/30-player rule |
| reference_unit | one_context_per_player or canonical_context |

Example of an **experimental**, not approved, policy:

```python
policy = CandidatePolicy(
    policy_id="synthetic-press-30-fifa-v1",
    source="controlled synthetic comparison; pending team decision",
    formula=FIFA,
    min_actions=30,
    min_minutes=900,
    pooling="separate_mid_cb",
    min_pool_size=2,
    reference_unit="one_context_per_player",
)
```

Constructor names do not imply publication approval. All outputs carry the
candidate notice, policy provenance and synthetic source provenance.
Metadata always states policy_finalized=False,
production_scoring_supported=False and publication_authorized=False.

## Inputs, identity and scope

Canonical key K remains player_id, team, competition_name, season_name.
Existing M2A ID validation and the two declared team aliases are reused unchanged.
Duplicate canonical contexts, alias collisions and duplicate pool membership
reject the entire call; no first occurrence is chosen.

| Input | Required fields after K |
|---|---|
| population | position_group, minutes, exposure_scope, identity_evidence, context_evidence, exposure_evidence |
| actions | Four M3A COUNT_COLS, numerator_scope, coverage_evidence |
| ComparisonPools.members | pool_group |

Optional action fields are M3A's pressured_actions,
successful_pressured_actions and three percentage columns. When supplied, each
must agree with the unchanged M3A formulas. Unknown extra fields reject.
An action/member key absent from the population rejects; a population context
not selected into membership remains present with not_pool_member.

ComparisonPools explicitly declares population_id, season_name=2015/2016,
the exact four-league tuple (La Liga, Premier League, Serie A, Ligue 1),
members and coverage_evidence. Other seasons/competitions reject rather than
being silently filtered. Numerical fixtures are invented ledgers, not assertions
that a toy match list represents a real football season.

PressScope declares competition, season, sorted unique exact positive match IDs,
and full_season=True. Known numerator and exposure scopes must agree exactly.
Conflicting match-ID-to-competition/season associations across contexts reject.
Missing scopes withhold; malformed, mismatched or explicitly partial-season
scopes reject. D2B's Bundesliga four-match window is incompatible with this scope.

For separate_mid_cb, DM/CM or explicitly supplied MID contexts must be members of
MID; CB contexts must be members of CB. Cross-position membership rejects.
The optional combined_mid_cb experiment requires all selected members explicitly
in COMBINED; separate and combined membership cannot coexist.
This is an explicit comparison alternative, not endorsement of pooling roles.
Missing/ambiguous roles retain N/A; unrelated/invalid roles reject.

Reference unit is explicit: one_context_per_player rejects multiple selected
team contexts for the same player-season. canonical_context permits distinct
team contexts only as a deliberately selected synthetic experiment, with its
possible player double-weighting visible in declared membership. Neither option
silently collapses contexts or chooses a transfer club. Final press transfer
reference policy remains unanswered.

## Strict synthetic boundary and numerical validation

SyntheticEvidence requires kind=SYNTHETIC_TEST_EVIDENCE, a nonblank fixture_id,
source and a real boolean complete flag. Dataset, pool, identity, context,
exposure and press-coverage records must name the same fixture. Missing/incomplete
row/pool evidence withholds scores.

Verified, delivered-consistency and provisional evidence kinds **reject the
call**, including in the dataset declaration, pool and row evidence. There is
no production mode, verified-input override, data loader or promotion function.
Real delivered observations must never be relabeled synthetic. Like any pure
caller-attestation API, this cannot independently authenticate a falsely labeled
fixture; D3C supplies only controlled synthetic examples and tests.

Counts must be finite, nonnegative, exact signed-int64 integers; booleans,
strings, complex/fractional/inexact floats and overflowing individual/combined
totals reject. Completions cannot exceed attempts, even if another count is
missing. Original counts and totals are retained as nullable Int64 without
float coercion.

To safely reuse M3A on the full permitted count range, percentages use a float
shadow passed to its existing helper; this avoids int64 overflow in 100*count.
The shadow never replaces exact counts/totals. Ranking uses exact successful /
attempt Fraction values, so adjacent large count ratios do not become false ties.
Sample deviation is computed from exact centered ratios converted to floating
deviations; exposed raw M3A percentages remain measurement diagnostics.
Ordinary synthetic fixtures match M3A output exactly; no M3A code was changed.

## Alternative candidate transformations

The caller selects **one** formula:

### A — average_rank_percentile_clipped_1_100

```text
candidate_percentile = 100 × ascending average-tie rank(press success rate) / N
candidate_score = clip(candidate_percentile, 1, 100)
```

The lower clip makes the requested 1–100 range explicit for N>100; the raw
percentile is preserved separately. This exact mapping is a candidate choice,
not a final approved press mapping. It is not endpoint rank scaling.
No FIFA z-score score is simultaneously published by this selection.

### B — sample_z_65_10_unrounded_clipped_1_99

```text
z = (press success percentage - cohort mean percentage) / sample_std(ddof=1)
candidate_score = clip(65 + 10 × z, 1, 99)
```

The distribution is the selected eligible **press percentage**, not DRI or its
percentile. Decimal precision is retained without rounding. Percentile remains a
labeled diagnostic; there is only one selected candidate_score column.
This explicit unrounded candidate differs from V2's rounded integer output.

A raw percentage describes observed success/attempts. A percentile describes
relative order in a declared reference group. A FIFA-style score describes
standardized distance from its mean with selected baseline/scale/clipping.
These values are not interchangeable and are not football ability truth.

## Eligibility and withheld states

All population contexts survive. Raw observed counts/rates remain available
when only scoring eligibility fails. Reasons distinguish:

- missing_actions: no supplied action record; no zero counts created.
- incomplete_action_counts: known counts retained, aggregate rate unavailable.
- zero_attempts: rate/score N/A; zero is not a failed success percentage.
- Observed zero completions with positive attempts: rate 0, potentially eligible.
- below_candidate_min_actions / below_candidate_min_minutes.
- missing/nonpositive exposure, missing scopes or incomplete identity/context/
  exposure/press/pool evidence.
- missing/ambiguous role, not_pool_member and candidate_policy_not_selected.

Invalid numerical exposure rejects. Known scope contradictions reject instead
of being masked by another ineligibility reason. Even a zero minute threshold
does not make absent, zero or unreliable exposure eligible.

Rows may be eligibility-qualified but statistically withheld:
insufficient_candidate_pool or constant_candidate_pool. Singleton and constant
pools receive no normalized score for either formula; there is no neutral65
fallback or singleton 100. The explicit minimum ≥2 is a conservative mathematical
safeguard, not an approved football/statistical sample-size threshold.

Every result is labeled NOT_FINALIZED even when status=candidate_scored.
That status means a synthetic experimental calculation succeeded, not approval.
No tier helper is invoked and no final player-tier/OVR field is emitted.

## Synthetic worked examples

Invented contexts with 40 pressured pass attempts, 10/20/30/40 completions,
zero dribble attempts, 900 minutes and complete synthetic evidence:

| Fixture context | Raw success % | Candidate A | Candidate B (shown to 6 decimals only) |
|---|---:|---:|---:|
| 1 | 25 | 25 | 53.381050 |
| 2 | 50 | 50 | 61.127017 |
| 3 | 75 | 75 | 68.872983 |
| 4 | 100 | 100 | 76.618950 |

These are separate runs selecting A or B. B mean=62.5, sample deviation=
sqrt(3125/3), with z values -1.161895, -0.387298, 0.387298, 1.161895.
Implementation retains full float precision.

For rates 25,25,75,100, average-tie percentiles are 37.5,37.5,75,100.
For 10/10 passes and 0/30 dribbles, the combined rate is **25%**, not the
50% average of component percentages.
For MID rates 25/50 and CB rates 75/100, separate candidate pools each produce
percentiles 50/100. An explicit combined experiment gives 25/50/75/100.

Threshold fixtures with 29/30/49/50 attempts retain respectively three contexts
at minimum 30, and one at minimum 50; the latter's score remains withheld because
the explicit minimum pool size is 2. At 899 minutes the candidate 900 policy
withholds; an explicitly selected 450 policy changes that eligibility result.
No candidate threshold proves precision or removes pass/dribble mix effects.

## Differences from contributor V2 and open questions

V2 hardcodes 900/30, separate MID/CB, average ranks, sample z, rounded FIFA
ratings, a constant-pool neutral 65 and automatic percentile tiers with Silver 70.
It inherits recovery full_coverage flags, drops unresolved names in its legacy
join and writes output files.

D3C retains only M3A's already integrated raw action mathematics. It adds:

- Explicit, identified candidate policy and four-league comparison membership.
- Alternatives A/B, with documented clipping and unrounded B.
- Exact-count, canonical-key, scope and synthetic-only validation.
- Explicit missing/withheld records; no imputation, silent filtering, ratings
  from partial scopes or automatic role/population choice.
- No inherited recovery-coverage approval, real-data mode, archetype, tier,
  OVR, writer or network operation.

Team decisions still needed: press-specific minute/action minimums; whether MID
combines DM/CM and CB normalizes separately; final mapping A/B or another
approved calibration; rounding and endpoints; sufficient reference size and
constant-pool behavior; transfer/reference unit; metric-specific coverage and
reportability requirements; eventual tier application. Gold90/Silver75 global
boundaries are not changed, but no press tier is assigned here.
OVR and the line-breaking definition remain separate open work.

Real 2015/2016 ratings remain blocked by both unfinished press policy and D3B's
source/identity/exposure/reportability findings. D3C rejects even verified
evidence by design; satisfying source verification later does not turn this
experimental implementation into an approved production scorer.
Recommended next scoring milestone: review the synthetic 30/50-action and A/B
comparisons, explicitly approve a press policy and its reference population
requirements, then design a separately authorized production boundary once
metric-specific evidence is established.

## Regression, integrity and Git

New files only:

- `src/press_scoring.py`
- `tests/test_press_scoring.py`
- `docs/d3c-press-scoring-candidates.md`

39 focused synthetic tests cover M3A event/helper parity, weighted rates, exact
worked mathematics, ties, explicit policies, pool/role/season/league isolation,
30/50 actions, candidate900 minutes, missing/zero/incomplete values, exact counts
and IDs, overflow/conservation, supplied-value contradictions, synthetic-only
gates, provenance, immutability, row-order invariance, clipping, reference units,
singleton/constant pools and absence of writers/network/tier/OVR output.

Full Python: `python -B -W error -m unittest discover -s tests -q` —
**559 passed** (520 existing +39 D3C). Recursive frontend JavaScript:
**99 passed**, none skipped. `git diff --check` and new-file whitespace checks pass.

All 11 Parquet SHA256 fingerprints match pre-work and D1B/D2C/D2D inventories:

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

All 128 pre-existing fingerprinted files remain unchanged, including M3A, D3A,
D3B, identity/trust, D2A–D2D, frontend/demo/raw/diagnostic modes, existing approval
records and the untracked M4A checklist. No real data was scored; no datasets
were written by D3C.
Branch remains `integration-foundation`, HEAD
`aa7864cb3da7a07ec43f0d04f2923435e6ef84bf`; main remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`.
Only the three D3C files are new; existing untracked data/checklist remain.
No tracked modifications, staged files, commits, pushes, branch/worktree changes
or deployment.

