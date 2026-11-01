# M4A team scoring approval checklist

**Status: discussion only — all 14 decisions are PENDING APPROVAL.**
No weights, scoring rules, ratings or rankings are approved by this checklist.
IDs match [M4A section 9](m4a-scoring-design.md); details below also capture
unresolved choices in its other sections. [M4B0](m4b0-scorecard-assembly.md)
assembles existing metrics only; presence flags and declared calibration
completeness are not verified coverage or eligibility.

For each blank decision, record the exact rule (or explicit deferral), scope,
approver/owner, date, rationale and policy version. Approve all applicable
subchoices; a heading-level yes/no is insufficient.

## CB / DM / CM positional scoring

**D1 — Which roles and mixed-role convention define comparisons?**

- **M4A options / consequences:** separate CB, DM and CM gives role fidelity but
  smaller pools; combined DM+CM (`MID`) enlarges pools but mixes responsibilities.
  Dominant-role assignment is simpler; role-specific exposure better represents
  mixed roles but needs matching role-level evidence and a defined method.
- **Proposal, not approval:** separate CB/DM/CM; verified role provenance using
  M1's dominant-minutes rule, including its exact tie order
  GK/CB/DM/CM/FB/WM/AM/ATT. Unknown/conflicting roles block role comparisons.
  FB/WM/AM/ATT remain outside the initial scope unless explicitly admitted (D3).
- **Final team decision:** _______________________________________________

## Metric selection and relative weights

**D11 — Which metrics score, and how are they normalized and grouped?**

- **M4A options / consequences:** scorecard first without a composite keeps
  evidence visible. For a later composite, approve recovery/press/progression
  families and their primary metrics, or equal approved components. Equal
  columns can unintentionally overweight families exporting more metrics.
  Choose a primary progression measure, e.g. `prog_passes_p90` or
  `pass_value_p90`, or justify joint use: progression, crossings, value and
  completion overlap. Combined press and its pass/dribble rates also overlap;
  attempts/completions are denominators/diagnostics, not independent achievements.
- **Normalization options / consequences:** within-pool percentiles describe
  relative order; z-scores retain magnitude but increase outlier sensitivity;
  robust scaling needs approved centre/scale and constant-scale handling.
  Per90 suits activity and percentages suit completion; mixing raw totals/units
  rewards playing time. Approve metric units, direction and mandatory set.
- **Proposal, not approval:** scorecard first; retain raw diagnostics, review
  redundancy, then consider percentile-normalized primary family components.
  Existing definitions below are available inputs, not automatically selected.
- **Final team decision:** _______________________________________________

**D12 — If a composite is adopted, how should components/families be weighted?**

- **M4A options / consequences:** equal approved components/families offer a
  transparent baseline but selection creates implicit weights; position-specific
  weights may reflect CB/DM/CM duties but need football justification and
  sensitivity review. Approve within-family weights before family weights;
  different positional scores need not be comparable.
- **Proposal, not approval:** defer the composite; later compare equal approved
  families with position-specific weights after correlation review. Any adopted
  weights must be finite, nonnegative and sum to one. No numeric weights proposed here.
- **Final team decision:** _______________________________________________

### Available definitions and limits to consider for D11

| Integrated metric family | Existing meaning | Selection/coverage caution |
|---|---|---|
| Recovery ([M2B](m2b-recovery.md)) | Separate successful Tackle, Interception and non-failed Ball Recovery counts and per90; missing recovery-failure flag counts as non-failed. | No recovery composite or possession adjustment. Zone outputs are counts; missing/off-pitch locations reduce zone coverage, not totals. |
| Press resistance ([M3A](m3a-press-resistance.md)) | Under-pressure Pass/Dribble completion percentages; combined rate is total successes / total attempts, not an average of two percentages. | Missing pressure is excluded; null pass outcome completes, missing dribble outcome fails. Pass/dribble mix affects comparisons; optional minutes do not gate existing percentages. |
| Progressive passing Level A ([M3B](m3b-progressive-passing.md)) | Measurable eligible open-play passes: goal distance reduced at least 25% and forward movement at least 10 pitch units; completed passes, third crossings, completion percentage and difficulty-weighted distance per90. | Value is distance weighted by reference failure rate, not goals/impact. Reference uses all eligible measurable passes, including outsiders, by league/season/start-third/length band; missing cells fail, with no fallback. Geometry exclusions need an acceptance rule. |

## Percentile comparison populations

**D2 — Which leagues/seasons and eligible members form each comparison pool?**

- **M4A options / consequences:** league-season, role- and metric-specific pools
  improve local relevance but shrink membership; same-season cross-league pools
  increase size but require evidence of comparable opportunity/measurement.
  Contributor Pratyush's four-league 2015/2016 pool is a convention, not approval.
- **Proposal, not approval:** explicit league-season metric pools; publish scope
  and membership size. Eligibility can differ across metrics. Keep passing's
  full reference cohort separate from player comparison pools; never fit it only
  on eligible players. No automatic league/role merging when pools are small.
- **Final team decision:** _______________________________________________

## Minimum playing-time thresholds

**D5 — What minimum minutes apply, and to which contexts/outputs?**

- **M4A options / consequences:** 450 includes more players but noisier rates;
  900 is the contributor-aligned discussion candidate but excludes substitutes
  and some transfers; 1350 favors more exposure but smaller, starter-heavy pools.
  None guarantees statistical stability. Specify application per metric/context.
- **Proposal, not approval:** review 900; keep raw observations below the chosen
  gate with reasons. Zero/missing minutes cannot produce per90 comparisons.
- **Final team decision:** _______________________________________________

## Under-pressure sample thresholds

**D6 — What attempt minimums make percentage comparisons eligible?**

- **M4A options / consequences:** 30 combined pressured actions includes more
  players; 50 reduces single-outcome sensitivity but excludes more. One outcome
  changes these rates by 3.33 versus 2 percentage points; neither proves precision.
  Other justified minima remain possible. Joseph's 50-action convention belongs
  to a different model and does not validate this one.
- **Proposal, not approval:** review combined 30 versus 50; separately approve
  pass-only, dribble-only and progressive-completion attempt minima if selected.
  M4A supplies no numeric candidates for those separate gates. Combined actions
  cannot certify a dribble sample; zero attempts remain N/A.
- **Final team decision:** _______________________________________________

## Missing-data and metric coverage handling

**D7 — What evidence permits full-season or partial-window comparisons?**

- **M4A options / consequences:** verified metric-specific source, identity,
  exposure and calibration gates strengthen validity but currently block
  production; explicitly separate partial-window comparisons allow bounded use
  but cannot represent a season and require aligned window exposure/labels.
- **Proposal, not approval:** reconcile expected fixtures/teams/matches,
  participation, event types, duplicate IDs, omissions and numerator/denominator
  windows for each metric. Approve a geometry-availability acceptance rule;
  M4A specifies no universal acceptable missing percentage. Preserve partial
  observations but withhold full-season normalized outputs for incomplete or
  unknown required coverage. Recovery flags, 300 matches, a valid file, successful
  joins and `complete=True` alone cannot certify coverage.
- **Missingness choice to record:** preserve absent/unobserved, undefined rates
  and evidenced observed zero separately, with reasons; do not inherit contributor
  zero-fill conventions. Otherwise missing observation can become false poor
  performance. Invalid/duplicate inputs need reconciliation, not ordinary N/A.
- **Final team decision:** _______________________________________________

**D13 — What happens when a mandatory composite component is unavailable?**

- **M4A options / consequences:** require every mandatory component and return
  N/A overall, preserving available metrics; this protects comparability but
  reduces inclusion. An explicitly approved partial score includes more players
  but needs its own component set, pool/version label and cannot be compared
  with the full score. Silent zero-fill, substitution or reweighting is excluded.
- **Proposal, not approval:** require the complete eligible, verified set;
  no overall output initially. Eligibility remains metric-specific.
- **Final team decision:** _______________________________________________

## Transferred players and season context

**D4 — How do multiple team contexts enter reference distributions?**

- **M4A options / consequences:** preserve player/team/competition/season rows
  and explicitly approve whether both transfer contexts enter a pool; this
  retains context but may weight a player twice. A separately approved
  player-level reference avoids duplicate influence but needs a defined
  aggregation, exposure and membership policy.
- **Proposal, not approval:** retain all canonical contexts, never silently
  collapse transfers or seasons; settle membership before ranking (with D2/D5).
- **Final team decision:** _______________________________________________

## Whether to include goalkeepers

**D3 — Should GK or additional roles receive scoring outputs?**

- **M4A options / consequences:** initial CB/DM/CM scope with GK separate and no
  GK overall avoids applying unsuitable metrics but limits reach; a separately
  approved GK component set/additional roles expands scope but needs evidence.
  Arpit reports only GK Ball Recovery; Pratyush V2 excludes GK; Joseph's
  alternative GK pass model does not approve integrated combined press for GK.
- **Proposal, not approval:** keep GK separate, without initial overall;
  explicitly defer other roles while preserving their source records.
- **Final team decision:** _______________________________________________

## Overall rating / OVR conversion

**D9 — Should FIFA-style ratings be published, and with what exact conversion?**

- **M4A options / consequences:** defer to avoid arbitrary calibration; adopt
  Pratyush's convention `round(clip(65 + 10*z, 1, 99))`, with sample SD and
  nearest-even rounding, or explicitly approve alternatives. Its constant-pool
  fallback is 65; N/A avoids implying evidence where variation is absent.
  Population SD gives larger absolute z-scores than sample SD in the same pool;
  outliers shift everyone, and clipping creates ties.
- **Proposal, not approval:** defer. If adopted, approve input metric/composite,
  identical eligible pool for recipients and mean/SD, SD convention, baseline,
  scale, bounds, rounding, degenerate-pool handling and any outlier adjustment
  (including winsorization). M4A supplies no approved composite-to-OVR mapping.
- **Final team decision:** _______________________________________________

## Player tiers and ranking methodology

**D8 — Which rank formula and small/constant-pool rules apply?**

- **M4A options / consequences:** average-tie `100 * rank / N` preserves
  contributor practice, but minimum is `100/N`, singleton is 100, and tied maxima
  may be below 100. Endpoint `100*(rank-1)/(N-1)` changes endpoints and requires
  singleton handling. Z/robust normalization retains different information (D11).
  Minimum pool 20 versus 30 trades inclusion for less coarse comparisons;
  neither is statistically established. Constant pools provide no differentiation.
- **Proposal, not approval:** average ties; exclude missing/ineligible values
  from rank and N; candidate N >= 20, with small/constant pools N/A. Publish
  pool definition/N and retain ties rather than implying unsupported distinctions.
  Composite percentiles need their own approved complete-component pool.
- **Final team decision:** _______________________________________________

**D10 — Should tiers be metric-specific, and where are boundaries?**

- **M4A options / consequences:** candidate Gold >=90, Silver >=70 and <90 is
  simple but sensitive to coarse ranks; alternative cutoffs need justification.
  Overall tiers require separate approval; one Gold metric cannot imply overall
  Gold. Contributor Unranked conflates ineligible and eligible below-Silver cases.
- **Proposal, not approval:** defer overall tiers; if metric tiers are adopted,
  review 90/70 and distinguish eligible below Silver from ineligible/N/A.
- **Final team decision:** _______________________________________________

## Fairness, validation and source limitations

**D14 — What auditable contract and validation evidence must accompany release?**

- **M4A options / consequences:** approve section 3's canonical schema/reasons
  and versioned evidence, or equivalent normalized child tables; both support
  auditability but add metadata work. M4B0's existing flat assembly is not approval
  of this future scoring contract. Resolve verified display-label conflicts
  explicitly; names never become identity keys.
- **Proposal, not approval:** retain stable IDs/context keys, verified role and
  display-name provenance, separate exposure/missingness/coverage states, counts,
  eligibility reasons, pool membership and policy/metric/source/crosswalk/
  exposure/calibration fingerprints. Approve exact schema and reason codes.
  Adopt M4A section 11 acceptance checks: invalid-input rejection, conservation,
  unchanged inputs, threshold/tie/missing/transfer boundaries, deterministic
  results, approved transformations/weights and blocked-data behavior.
- **Fairness review to record:** role/team opportunity (no possession adjustment),
  pass/dribble mix, correlated components, outliers, threshold/pool/weight
  sensitivity and cross-role comparability. Normalization cannot repair
  incomparable cohorts or establish causal player impact. Synthetic passing
  tests establish implementation behavior, not real-data completeness.
- **Final team decision:** _______________________________________________

### Release gates for legitimate rankings or ratings

1. **Before any production metric ranking/normalized rating:** resolve applicable
   D1–D8, D11 (selected metrics/normalization) and D14. These establish scope,
   transfer membership, exposure/actions, coverage and the comparison method.
   D3 may explicitly defer GK. Adopt D9 only for FIFA-style conversion and D10
   only for tiers; otherwise record deferral and keep those outputs disabled.
2. **Before a composite ranking, overall rating or overall tier:** additionally
   approve D12/D13, mandatory components, family structure and normalization in
   D11, complete-component pool in D8, and D9/D10 for requested conversions/tiers.
   A team may approve deferral now; deferral does not authorize that output.
3. **Separate data gate, regardless of approval:** obtain a trusted complete
   spelling crosswalk and reconcile target-population identity, per-metric events
   and matching exposure. Delivered table consistency/M1 validation and bounded
   successful integrations do not establish these. Passing additionally needs
   verified full-cohort calibration, reporting coverage, cells and geometry rules.
4. **Unavailable optional metrics stay out:** current 360 frames cannot support
   reliable complete-season Level B for the primary 2015/2016 pool; Joseph's
   alternative retention model lacks Miscontrol/Dispossessed events; clearance
   has no integrated definition. Selecting any requires its missing evidence and
   separate verified integration. Missing events/frames are never zero activity.

**Meeting outcome:** record all D1–D14 as chosen rules or explicit deferrals;
assign owners for missing evidence. Policy approval permits later implementation
work, not immediate production rankings. This checklist changes no methodology,
code, data or existing report.
