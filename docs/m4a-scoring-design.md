# M4A: scoring design and approval contract

## 1. Purpose and current implementation status

This is a documentation-only design at integration baseline `882c1ee`. M1 validates delivered datasets; M2A provides shared identity; M2B, M3A and M3B expose recovery, Pratyush press resistance and Joseph Level A progressive passing. The integration produces no scoring table, percentiles, FIFA-style ratings, tiers or overall index. An available calculation does not establish production-ready population coverage.

**Approval status:** every recommendation and future contract below is **PROPOSED — PENDING APPROVAL**. None is an approved statistical or football policy. Existing behavior is explicitly identified. M4B must use a recorded team-approved policy, not interpret this document as approval.

Evidence: [identity](../src/identity.py), [recovery](../src/recovery.py), [press resistance](../src/press_resistance.py), [passing](../src/passing.py), their dependencies in `src/metrics/`, and milestone documents [M1](m1-validation.md), [M2A](m2a-identity.md), [M2B](m2b-recovery.md), [M3A](m3a-press-resistance.md), [M3B](m3b-progressive-passing.md). Contributor conventions were checked directly in fetched objects, without merging:

| Ref / commit | Relevant source |
|---|---|
| `origin/arpit-dev` / `0445f18` | `src/metrics/recovery_per90.py` |
| `origin/pratyush-dev` / `77c1639` | `src/metrics/press_resistancev2.py` |
| `origin/Joseph-dev` / `013c8ed` | `src/metrics/scoring_common.py`, `press_resistance.py`, `line_breaking.py` |

## 2. Available metrics and exact formulas

**Existing common behavior:** context key `K = (player_id, team, competition_name, season_name)`. Strict identity resolution precedes selected-population aggregation; unresolved identities reject production aggregation. Selected, outside-population and unresolved diagnostics remain distinguishable. Stable IDs are not name-derived guesses. Observed contexts only are aggregated; an absent output row is not evidence of zero activity.

### Defensive recovery — existing

`integrate_recovery(events, crosswalk, minutes, population)` returns identity diagnostics, accounting, `totals` and `by_zone`. Events qualify as follows:

- Tackle: `type == Duel`, `duel_type == Tackle`, and `duel_outcome` in `Won`, `Success In Play`, `Success Out`.
- Interception: `type == Interception` with `interception_outcome` in the same success set.
- Ball Recovery: `type == Ball Recovery` unless its failure flag equals `True`; a missing failure flag is treated as non-failed by the existing adapter.

| Exact output | Formula / unit |
|---|---|
| `totals`: `K`, `event_type`, `count` | Separate qualifying event counts; no combined recovery count/score |
| `minutes`, `per90`, `rate_status` | `per90 = 90 * count / minutes`, events per 90 minutes; missing/zero minutes yield N/A with `missing_minutes` / `zero_minutes`; otherwise `ok` |
| `by_zone`: `K`, `event_type`, `zone`, `count` | Separate counts in a 3-by-3 grid on a 120-by-80 pitch; x boundaries 40/80, y boundaries 80/3 and 160/3; zone `1 + x_band + 3*y_band` |

Missing/off-pitch locations retain total counts but have no zone count; zone sums can be below totals. Zones are counts, not zone per90 rates. Counts survive missing exposure. The integrated wrapper does not apply a minimum-minutes threshold or output `position_group`, `reportable`, `full_coverage` or percentiles. Those fields in the delivered M1 export belong to that export's convention. No possession adjustment is integrated.

### Pratyush press resistance — existing

`integrate_press_resistance(events, crosswalk, population, minutes=None)` returns identity, accounting and `totals`. It selects Pass/Dribble events whose `under_pressure` equals `True`; missing pressure is excluded. All pass types are included. A pass completes when `pass_outcome` is null; a dribble completes only for `dribble_outcome == Complete`. Missing dribble outcome remains an unsuccessful attempt.

| Exact `totals` fields after `K` | Formula / unit |
|---|---|
| `pressured_pass_attempts`, `pressured_pass_completed` | Pressured pass events, completed subset; integer counts |
| `pressured_dribble_attempts`, `pressured_dribble_completed` | Pressured dribble events, completed subset; integer counts |
| `pressured_actions` | Sum of pass and dribble attempts; count |
| `successful_pressured_actions` | Sum of pass and dribble completions; count |
| `pressured_pass_completion_rate` | `100 * pressured_pass_completed / pressured_pass_attempts`; percentage |
| `pressured_dribble_completion_rate` | `100 * pressured_dribble_completed / pressured_dribble_attempts`; percentage |
| `press_resistance_rate` | `100 * successful_pressured_actions / pressured_actions`; percentage |
| `minutes` | Present only when exposure is supplied; no integrated `rate_status` field here |

Each zero denominator produces N/A for its percentage. Optional minutes do not gate these percentages. No action-count eligibility is enforced by M3A. This combined percentage is action-weighted, not the arithmetic average of pass and dribble percentages. Joseph's alternative possession-retention model is not integrated and is not interchangeable with it.

### Joseph progressive passing, Level A — existing

`calibrate_difficulty(reference_events_or_batches, scope=..., complete=...)` builds the independently supplied reference; `integrate_progressive_passing(events, crosswalk, population, minutes, reference=...)` returns preparation diagnostics, raw-event accounting, identity/accounting, reference metadata and `totals`.

Eligible passes have `type == Pass`, `pass_type` null, `Recovery` or `Interception`, excluding outcomes `Unknown` and `Injury Clearance`. Missing geometry is excluded and accounted for; invalid nonfinite geometry/negative length is rejected. Completion means null `pass_outcome`. Geometry uses the attacked goal centre `(120, 40)`:

| Symbol / existing rule | Definition |
|---|---|
| `d0`, `d1` | Euclidean start/end distance to the goal centre, pitch distance units (source convention: yards) |
| Progressive attempt | `d1 <= 0.75*d0` **and** `end_x - start_x >= 10` |
| Completed progressive pass | Progressive attempt and completed |
| Third crossing | Completed progressive pass with end third greater than start third; x thirds bounded at 40 and 80; one event, even if two boundaries crossed |
| Reference cell | Competition, season, start third and length band `[0,15)`, `[15,30)`, `[30,infinity)`; reported pass length, Euclidean fallback when missing |
| `p_hat` / difficulty | Reference completed / attempted measurable eligible passes in cell; difficulty `1 - p_hat` |
| Event `pass_value` | `(d0-d1)*(1-p_hat)` for completed progressive passes, otherwise observed zero |

Reference counts are accumulated before division across batches. They include eligible passes outside the selected reporting population. Missing reference cells reject integration; there is no fallback. `complete=True` is a required caller attestation, not independent proof of cohort completeness.

| Exact `totals` fields after `K` | Formula / unit |
|---|---|
| `prog_attempts`, `prog_passes`, `third_cross` | Counts of progressive attempts, completed progressive passes, and third-crossing completed progressive passes |
| `value_sum` | Sum of event pass values; difficulty-weighted distance, not goals or completion probability |
| `minutes` | Supplied context exposure |
| `prog_passes_p90` | `90 * prog_passes / minutes`; events per90 |
| `prog_completion_pct` | `100 * prog_passes / prog_attempts`; percentage, N/A at zero attempts |
| `third_cross_p90` | `90 * third_cross / minutes`; events per90 |
| `pass_value_p90` | `90 * value_sum / minutes`; difficulty-weighted distance per90 |
| `rate_status` | `ok`, `zero_minutes`, `missing_minutes`; per90 values N/A for zero/missing exposure |

An observed measurable non-progressive pass can establish zero progressive counts; an absent context cannot. Completion percentage depends on attempts, independently of exposure. No Level B, eligibility, percentile or rating fields are integrated.

## 3. Canonical scoring data contract

**PROPOSED — PENDING APPROVAL:** future schema below; no scoring table or these additional metadata fields exist today. Keep one record per explicit context `K`; metrics may be nested or represented in a normalized child table unique on `K + metric_id`.

| Future fields | Proposed contract |
|---|---|
| `player_id`, `team`, `competition_name`, `season_name` | Required stable integer ID and canonical nonempty context labels; preserve integer precision and approved team aliases. Reject duplicate context records. No transfer-team collapse. |
| `display_name`, `display_name_source` | Verified label selected from trusted identity evidence; never a join key. Missing label remains N/A; conflicting verified labels require an explicit display rule, not a new identity. |
| `position_group`, `position_source` | Verified context role from minutes/position evidence; join and dominant-role agreement required. Unknown/conflicting role blocks role-based comparisons. Reuse the documented M1 role derivation unless an approved policy changes it. |
| `minutes`, `exposure_scope`, `exposure_status` | Numeric, finite, nonnegative when known; match event window/team/season. Separate missing record, missing value and zero. Disagreement across tables is an error, not an average. |
| `metrics[metric_id].value`, `unit`, `status`, `reasons[]` | Exact available values from section 2, no silent recalculation or zero-fill. Unit distinguishes counts, percentages, event per90 and weighted distance per90. Status distinguishes valid observed zero from unavailable/undefined. |
| Per-metric `source_coverage`, `identity_coverage`, `exposure_coverage`, `calibration_coverage` | Independent complete/incomplete/unknown/not-applicable statuses, scope and evidence references; also record excluded events and geometry availability. Coverage must not be copied from recovery to press/passing. |
| `observed_event_count`, denominator fields | Preserve relevant attempts/counts and input accounting for sample-size checks; do not mistake overall pressured actions for dribble attempts. |
| `eligible`, `eligibility_reasons[]`, `pool_id`, `pool_n` | Per metric, after approved eligibility/pool validation. A future separate overall eligibility flag checks mandatory components. |
| Optional `percentile`, `zscore`, `rating`, `tier`, `overall_score` | Only for explicitly approved outputs; otherwise omitted or null with `policy_unapproved`. No implied implementation in M4A. |
| Provenance | Metric/version, policy/version, source/crosswalk/exposure fingerprints, reference scope/fingerprint, pool definition and membership fingerprint. |

**PROPOSED — PENDING APPROVAL:** future reason codes include `missing_metric`, `unobserved_context`, `unresolved_identity`, `missing_role`, `missing_minutes`, `zero_minutes`, `zero_attempts`, `insufficient_minutes`, `insufficient_actions`, `incomplete_source`, `unknown_coverage`, `unverified_calibration`, `pool_too_small`, `constant_pool`, `missing_required_component`, `policy_unapproved`. Preserve upstream reason/status distinctions; multiple reasons may coexist. Invalid duplicate keys, conflicting identities/exposure and nonfinite numeric values are validation errors, not ordinary N/A values.

## 4. Proposed comparison groups

**PROPOSED — PENDING APPROVAL:** start with separate CB, DM and CM league-season pools for each approved metric; publish pool sizes. Combined DM+CM (`MID`) and pooled leagues remain alternatives needing evidence of comparable opportunity and measurement. Separate DM/CM reduces role confounding but can produce very small pools. Transfers remain separate team contexts; the team must approve whether such contexts can both contribute to a reference distribution or whether a separate player-level reference is needed. Never silently collapse or double-weight transferred players.

**PROPOSED — PENDING APPROVAL:** keep GK separate, initially without an overall score. Arpit reports only GK Ball Recovery; Pratyush V2 excludes GK; Joseph's alternative press model uses GK passes only. None establishes approval for the integrated Pratyush combined rate on GK. FB/WM/AM/ATT are outside the initial proposed scoring scope, not deleted from source data. Mixed-role handling requires approval of the dominant-role convention or an alternative role-specific exposure model.

**PROPOSED — PENDING APPROVAL:** pools are metric-specific, even when role/league labels coincide. Press attempts, recovery reporting scope and passing calibration/geometry can yield different eligible members. A full-season passing reference cohort is distinct from the eligible player comparison pool; it must not be recalibrated only on qualifying players. Pool identifiers include policy, metric, role, competitions, season and eligibility version.

## 5. Proposed eligibility requirements

**PROPOSED — PENDING APPROVAL:** compare these candidates, retaining raw metrics and explicit ineligibility reasons:

| Candidate | Benefit | Cost |
|---|---|---|
| 450 minutes | Wider inclusion and larger pools | More exposure-related rate instability |
| 900 minutes | Contributor-aligned starting candidate | Excludes substitutes and some transfers; not a guarantee of stability |
| 1350 minutes | More exposure per included context | Smaller pools and stronger selection toward regular starters |

**PROPOSED — PENDING APPROVAL:** use 900 as the discussion baseline, not an enforced threshold. For combined press resistance, review Pratyush's 30-action minimum against 50 actions as an alternative. One outcome changes a 30-action percentage by 3.33 percentage points versus 2 at 50; neither threshold proves precision or removes pass/dribble mix bias. Higher thresholds reduce instability and inclusion. Joseph's 50-action convention is for a different model and cannot automatically validate either threshold here. Pass-only/dribble-only scores need their own approved attempt minimums; 30 combined actions does not establish an adequate dribble sample. A passing completion minimum also remains unresolved; no new numerical threshold is implied.

**PROPOSED — PENDING APPROVAL:** require verified metric-specific event coverage, identity coverage and matching exposure for a full-season production comparison. Coverage evidence should reconcile expected fixtures/teams/matches, duplicate event IDs, event-type availability, omissions and player participation against the declared scope. Calibration additionally needs the complete, correctly defined pass cohort. Geometry exclusions require a disclosed coverage assessment and an approved acceptance rule; no universal acceptable missing-geometry percentage is asserted here. A match-count heuristic of 300, a valid Parquet, a successful join or `complete=True` alone cannot certify these conditions.

## 6. Percentiles and FIFA-style rating options

**Existing contributor convention:** Arpit and Joseph use average-tie rank within competition/season/role (Arpit also event type). Pratyush V2 ranks eligible combined rates within CB or MID across its selected four-league 2015/2016 population. All use `100 * average_rank / N` with ascending ranks for these higher-is-better metrics. This is an empirical rank, not the fraction strictly below a value: the minimum is `100/N`; tied maxima need not be 100; a singleton gets 100 and an all-equal pool gets `50 + 50/N`.

**PROPOSED — PENDING APPROVAL:** retain average-tie ranks for approved metric scorecards, exclude missing/ineligible values from both rank and N, and display pool definition/N. Withhold normalized outputs for constant pools and pools below a candidate minimum of 20 eligible contexts (alternative: 30). These numbers are review candidates, not statistically established cutoffs. Small pools produce coarse ranks and unstable tier boundaries; do not automatically merge pools to reach a cutoff. Zero-attempt percentages and zero/missing-exposure per90 values remain N/A, never bottom-ranked zero.

**PROPOSED — PENDING APPROVAL, alternatives:** endpoint ranks `100*(rank-1)/(N-1)` require special handling for N=1 and change tie endpoints; z-scores retain magnitude but are sensitive to distribution/outliers; robust scaling requires approved centre/scale and constant-scale rules. No method estimates causal impact or makes incomparable source cohorts comparable.

**Existing Pratyush convention:** for eligible combined rates in the same CB or MID pool, `z = (rate - mean)/s`, using sample standard deviation `s` (`ddof=1`), then `round(clip(65 + 10*z, 1, 99))` as integer. Null/zero standard deviation falls back to z=0 and rating 65. Its rounding follows pandas nearest-even behavior. Ineligible ratings remain N/A.

**PROPOSED — PENDING APPROVAL:** defer FIFA-style output initially. If adopted, approve the exact input metric, same eligible pool for mean/SD and recipients, sample (`N-1`) versus population (`N`) SD, baseline/scale/bounds and rounding. Population SD produces larger absolute z-scores for the same finite pool. Recommend N/A for too-small/constant pools instead of a misleading baseline 65. Outliers shift mean/SD for everyone; clipping creates tied extremes. Percentiles describe relative order, whereas this formula preserves deviations measured in SD units before clipping; neither is an official football rating. Winsorization or other outlier adjustment requires separate approval.

**Existing Pratyush tiers:** Gold at percentile >=90, Silver >=70 and below90, otherwise Unranked; Unranked also covers ineligible contexts. **PROPOSED — PENDING APPROVAL:** if tiers are adopted, initially make them metric-specific using these candidate thresholds, but distinguish `ineligible/N/A` from eligible `below Silver`. Alternative thresholds or overall-index tiers require separate approval; never infer overall Gold from one metric Gold.

## 7. Composite-index weighting options

**PROPOSED — PENDING APPROVAL:** no overall score initially. Two later viable designs are:

| Option | Illustrative proposed formula | Tradeoffs |
|---|---|---|
| A: equal approved components | `S = sum(Z_j)/J` for the approved mandatory component set | Transparent baseline; component selection determines implicit family weights and can reward redundancy |
| B: position-specific weights | `S_r = sum(w_rj * Z_j)`, `w_rj >= 0`, `sum(w_rj)=1` | Can reflect CB/DM/CM responsibilities; requires football justification, sensitivity review and more policy choices; different role scores need not be comparable |

All `Z`, weights and formulas above are **PROPOSED — PENDING APPROVAL**. No numerical position weights are approved. GK needs a separately approved component set before either option applies.

**PROPOSED — PENDING APPROVAL:** only scoring components require normalization; keep raw counts/attempts as diagnostics and eligibility denominators. Use per90 for exposure-dependent activity, percentages for completion, then approved within-pool normalization before combining different units. Raw totals should not enter the index because they reward playing time and mix units. Percentile-normalized components yield an interpretable average relative rank, not cardinal impact; z-normalized components retain magnitude but amplify outlier/calibration sensitivity. A composite percentile would require its own approved complete-component pool.

**PROPOSED — PENDING APPROVAL:** consider a hierarchy of recovery, press resistance and progression families to prevent the family with more exported columns receiving more weight. First approve within-family components/weights, then compare equal family weights with position-specific family weights. Do not count pressured attempts and completions as independent achievements alongside their percentage. Combined press resistance and pass/dribble component rates overlap. Progressive passes, crossings and value share events; including all plus completion percentage can multiply the same signal. Choose a primary progression measure (e.g. `prog_passes_p90` or `pass_value_p90`) with the rest diagnostic, or justify their joint weights through correlation and sensitivity review. Three recovery event types are distinct but can still correlate and depend on team opportunity. No current metric is possession-adjusted.

**PROPOSED — PENDING APPROVAL:** an overall score requires every component in its approved mandatory set, each eligible with verified coverage. Missing one yields N/A overall while preserving available metrics. An explicitly approved partial score with its own component/pool/version label is an alternative, but is not comparable to the full score. No silent zero-fill, weight redistribution or substitution of unapproved/unavailable metrics.

## 8. Missing-data and incomplete-coverage policy

**Existing:** integrated counts are observed aggregates, not a complete player-by-metric grid. Arpit's delivered export and Pratyush's contributor script have grid/left-join zero-fill conventions; these were not imported into the integrated wrappers. Delivered M1 coverage/reportability flags are internally validated but do not prove source completeness.

**PROPOSED — PENDING APPROVAL:** preserve known partial observations with explicit scope; withhold full-season normalized/overall outputs when required coverage is incomplete or unknown. A partial-window per90 is not a full-season per90 if its numerator covers fewer matches than its minutes denominator. A complete calibration does not repair incomplete reporting events; complete reporting events do not repair incomplete identity or exposure. Missing 360 frames are not zero defenders or zero line breaks. Missing source types are not zero losses/clearances. Invalid/duplicate source records require reconciliation rather than scoring around them.

**PROPOSED — PENDING APPROVAL:** certify observed zero only from adequate evidence of observation for that context/metric. Otherwise preserve absence and a reason; do not import contributor zero-fill assumptions. A player may be eligible for one metric and blocked for another. Publish metric coverage and eligibility together, retaining diagnostics for excluded events/contexts and never labeling a successful bounded run a complete reconstructed population.

## 9. Explicit unresolved team decisions

Every row is a **PROPOSED** choice with status **PENDING APPROVAL**, including alternatives. Approval must record decision ID, chosen rule, scope, owner/approver, date, rationale and policy version before M4B enables it.

| DECISION | EXISTING CONTRIBUTOR CONVENTION | PROPOSED OPTION | ALTERNATIVE OPTION | TRADEOFFS | APPROVAL REQUIRED |
|---|---|---|---|---|---|
| D1 Roles | Arpit/Joseph separate roles; Pratyush CB/MID | Separate CB/DM/CM; dominant-role provenance | Pool DM+CM; role-specific exposure | Role fidelity versus pool size; mixed-role bias | PENDING APPROVAL |
| D2 Geography/season | Arpit/Joseph league-season; Pratyush four leagues pooled in 2015/2016 | League-season, metric-specific | Cross-league same-season pools | Local relevance versus comparability/size | PENDING APPROVAL |
| D3 Scope/GK | Arpit GK Ball Recovery only; Pratyush CB/MID | Separate GK, no initial overall; CB/DM/CM initial scope | Approve GK-specific set and additional roles | Sparse/role-inappropriate metrics versus broader coverage | PENDING APPROVAL |
| D4 Transfers | Stable context includes team | Preserve records; approve reference membership treatment | Separate approved player-level reference | Independence versus weighting players twice | PENDING APPROVAL |
| D5 Minutes | Provisional 900 | Review 900 | 450 or 1350 | Inclusion versus stability and pool size | PENDING APPROVAL |
| D6 Attempts | Pratyush 30; Joseph alternative model 50 | Review combined 30; separately approve component/passing minima | Combined 50 or other justified minima | Precision versus excluded players; different definitions | PENDING APPROVAL |
| D7 Coverage | Arpit/Joseph >=300-match heuristic; Pratyush inherited flags | Evidence-backed metric/source/identity/exposure/calibration gates | Explicit partial-window comparisons with separate labels | Stronger validity versus blocked production | PENDING APPROVAL |
| D8 Percentile/pool | Average rank/N; contributor small-pool behavior | Average ties; candidate N>=20, constant pools N/A | N>=30; endpoint ranks or robust normalization | Continuity versus coarse ranks/selection; no universal fair pool | PENDING APPROVAL |
| D9 FIFA-style | Pratyush 65+10 sample-z, clipped/rounded; constant65 | Defer; if approved, explicit parameters and N/A degenerate pools | Adopt source fallback or population SD | Familiar scale versus arbitrary calibration/outliers | PENDING APPROVAL |
| D10 Tiers | Pratyush Gold90/Silver70/Unranked | Candidate metric tiers90/70, ineligible separate | Different thresholds or separate overall tiers | Simplicity versus coarse boundaries and label ambiguity | PENDING APPROVAL |
| D11 Components/normalization | No shared integrated composite | Scorecard first; approve family structure, primary metrics and percentile units | Equal components or z-normalized components | Transparency versus redundancy/magnitude sensitivity | PENDING APPROVAL |
| D12 Weights | No project-wide approved weights | Later equal approved families | Position-specific symbolic weights | Simplicity versus role specificity; validate correlations | PENDING APPROVAL |
| D13 Missing components | No integrated overall | All mandatory components required | Separately labeled partial score | Comparability versus inclusion; never silent reweighting | PENDING APPROVAL |
| D14 Contract/provenance | Existing module-specific outputs | Section 3 schema, reasons and versioned evidence | Equivalent approved normalized tables | Auditability versus metadata burden | PENDING APPROVAL |

## 10. Recommended approach with rationale

**PROPOSED — PENDING APPROVAL:** deliver a transparent metric scorecard before an overall index. Begin review with league-season CB/DM/CM separation, 900 minutes and 30 combined pressured actions as candidate gates, average-tie percentiles with a candidate minimum pool of 20 and constant-pool withholding. Keep GK separate. These are discussion defaults only; data readiness and component-specific action minima remain unresolved. Where a pool fails its approved rule, show N/A and its reason instead of automatically pooling leagues/roles.

**PROPOSED — PENDING APPROVAL:** defer FIFA-style ratings and overall tiers. After component selection and redundancy review, use equal approved family weights as a transparent composite baseline for comparison with position-specific weights; require the full mandatory set. This sequence makes eligibility and coverage failures visible before discretionary weights obscure them. The project can review and approve a design now without asserting that final full-season scoring data exists.

## 11. M4B implementation acceptance criteria

All requirements in this section are **PROPOSED — PENDING APPROVAL**; M4B is not implemented here.

### IMPLEMENTABLE AFTER POLICY APPROVAL

- Record approved decisions D1-D14, exact input/output schema, metric directions/units, parameters, mandatory set, reason codes and policy version; unapproved outputs remain disabled. No recommendation silently becomes a default.
- Implement pure, non-mutating scoring functions accepting canonical metric records plus explicit policy and coverage evidence. Separate metric validation, eligibility, pool construction, normalization, optional rating/tiering and optional aggregation. No file writes/network or hidden cohort selection in the scoring functions.
- Reject duplicate keys, lossy IDs, conflicting role/exposure, invalid numerics, wrong units and incompatible scopes. Validate one-to-one joins and preserve canonical context and count/value conservation; prove source tables are unchanged. Test transferred contexts and trusted name aliases.
- Use synthetic fixtures to test threshold boundaries at 450/900/1350 and approved actions, missing role/minutes, zero exposure/attempts, valid observed zero, absent metric and each coverage state. Verify no zero-fill or silent eligibility inheritance.
- Test approved pool membership, role/league/season separation, transfer treatment, ties, missing exclusion, N below/at minimum, singleton and constant pools. Verify raw counts remain unchanged when eligibility changes.
- If approved, test exact percentile formula; sample/population SD, outliers, clipping and rounding for ratings; tier boundaries and separate ineligible status. No implementation of unapproved outputs.
- If approved, test equal/position-specific weights, nonnegative finite weights summing to one, required-component failure, normalization units, and prevention of implicit reweighting. Verify optional partial scores cannot masquerade as full scores.
- Require deterministic ordering and results under row/batch reordering; pin policy, metric and calibration versions and source/pool fingerprints. Explain every N/A with reasons. Tests distinguish a complete fixture from real-data completeness.
- Assert blocked-data behavior: incomplete/unknown required coverage withholds production comparisons and overall scores with actionable reasons; reference attestation without verification cannot certify final scoring. Preserve bounded diagnostic metrics without presenting final ratings.

### BLOCKED UNTIL ADDITIONAL VERIFIED DATA EXISTS

- Production full-season scorecards/ratings/index release requires a verified target population, trusted crosswalk and aligned source identity/exposure coverage, with match/team/event-type reconciliation for every included metric.
- Production difficulty-weighted passing requires verified complete, correctly scoped calibration and reporting events, reference-cell coverage and an approved geometry-availability rule; a bounded success is insufficient.
- Level B and Joseph's alternative press model require their specific missing inputs in section 12 before entering any approved component set. Clearance requires a separate verified metric definition/integration if selected. Policy approval alone does not supply these data.

## 12. Missing inputs and blockers

Each issue below **DOES NOT BLOCK DESIGN WORK**. The primary classification indicates its scoring impact; unavailable optional metrics do not prevent a scorecard limited to other approved, verified metrics.

| Missing input / limitation | Primary classification | Required resolution / practical effect |
|---|---|---|
| Complete trusted lineup-derived spelling crosswalk unavailable | BLOCKS FINAL SCORING | Obtain verified spellings/IDs and reconcile the declared target population. M2A/M2B/M3A/M3B resolve bounded inputs safely, not complete reconstructed player-season populations. |
| Delivered minutes/recovery pass M1 but source identity/exposure completeness is unestablished | BLOCKS FINAL SCORING | Independently reconcile source matches, participation and identity; internal table/role/count/per90 consistency does not establish complete source coverage. |
| Metric-specific full-season event windows/coverage and aligned exposure unverified | BLOCKS FINAL SCORING | Verify each source numerator and denominator against the same declared scope; recovery flags do not certify press or passing. |
| Complete correctly defined M3B reference cohort and production reporting coverage need verification | BLOCKS A PARTICULAR METRIC | Blocks final difficulty-weighted passing and any mandatory composite containing it. `complete=True` attests, not proves, completeness; retain full-cohort rather than eligible-player-only calibration. |
| Available 360 frames cannot support reliable complete-season Level B for primary 2015/2016 pool | BLOCKS A PARTICULAR METRIC | Obtain verified match/frame coverage and reconcile duplicate frames/events. Missing frames cannot establish zero line breaks. Level B remains unintegrated. |
| Miscontrol and Dispossessed absent from current raw export | BLOCKS A PARTICULAR METRIC | Joseph's alternative press-retention model requires these loss events. Do not omit losses or substitute it for integrated Pratyush M3A. |
| No clearance metric integrated | BLOCKS A PARTICULAR METRIC | Define, verify and integrate separately if the team selects it; do not invent zeros or include it implicitly in recovery. |
| Scoring policy/schema/normalization/weights approvals outstanding | BLOCKS FINAL SCORING | Record approvals before M4B enables scoring; synthetic implementation can then proceed while production data remains blocked. |

**PROPOSED — PENDING APPROVAL:** treat approval records and verified data evidence as separate release gates. No fabricated crosswalk, inferred missing losses, guessed frames, automatic pool expansion or placeholder ratings are acceptable substitutes in the proposed contract.
