# Phase 2 — consolidated rating pipeline

October 27, 2026. Original checkout, branch `integration-foundation`, baseline
`475cc77`. This implementation completes a local synthetic pipeline and a
withheld real-data delivery path. It does not certify or publish player ratings.

## Implemented architecture

```text
Explicit synthetic population + recovery numerators/minutes + press counts
  -> optional explicit transfer policy and match-ledger aggregation
  -> existing identity, population, scope and source declarations
  -> score_dri input/eligibility validation + component candidate transforms
  -> evaluate_press_candidates (explicit FIFA policy)
  -> assemble_ratings (five slots; no OVR policy)
  -> soccer-rating-delivery/v1 validation and deterministic serialization
  -> frontend parser and stable context identity
  -> explicit rating-preview file import -> PlayerCard -> ratingCard -> Radar

Original source/participation reports
  -> season_readiness -> readiness_rating_delivery
  -> all real attributes withheld, separate evidence gates retained
```

`src/rating_pipeline.py` provides the orchestration, with no filesystem or network
I/O. `synthetic_rating_delivery` consumes the existing DRI population and recovery
measurement DataFrames and the existing press action contract. `names` maps exact
`PlayerContext` values to display names. `None` candidate policies withhold scores.
The wrapper supports only separate MID/CB press pools and FIFA transforms; the
older percentile experiment remains available in its original module but cannot
be relabeled as a displayed FIFA rating through this pipeline.

`source_readiness_delivery` calls the existing `season_readiness` accountant.
`readiness_rating_delivery` also accepts its current noncertifying report in
memory. Neither path invokes real scoring, even if a caller edits a certification
flag: such reports are rejected. Delivered minutes are not exposed as a supported
rating denominator. Source match presence and structurally valid appearances do
not assert independent source support, verified season exposure or numerator
coverage. All current source gates remain unresolved.

Existing modules reused: `identity`, `identity_evidence`, `dri_scoring`,
`press_scoring`, `rating_assembly`, `season_verification`. The existing
`statsbomb_participation` and `participation_intervals` reports feed the readiness
accounting and retain their independent validation responsibilities. The
line-breaking candidate is deliberately not turned into a rating. Existing raw,
diagnostic, metric extraction and source-verification implementations are intact.

## Versioned delivery and trust boundary

`src/rating_delivery.py` and `frontend/src/lib/ratingDelivery.js` implement
`soccer-rating-delivery/v1`, separate from `soccer-scorecard/v1` and
`soccer-provisional-profiles/v1`. Those two schemas are rejected by the new parser.

The envelope has a fixed notice, scope, players, `production_ready=false` and
`publication_authorized=false`. Scope explicitly names 2015/2016, all four
leagues in established order, separate MID/CB groups and a comparison cohort ID.
Every player preserves:

- Exact positive signed-int64 canonical ID as a decimal string, display name,
  nominated team/competition context, season, role group and cohort identity.
- Original source club contexts, their match-ID lists, full-season declarations,
  evidence kinds and source references; a distinct provenance-reference list.
- `synthetic`, `diagnostic` or `verified` classification. Classification is a
  description, never an authorization mechanism. This pipeline only constructs
  synthetic candidates or diagnostic withheld records.
- Separate gates for delivered-table eligibility, independent source support,
  season exposure, metric numerator verification, scoring approval and
  publication authorization. Valid and contradictory sample appearance IDs are
  separate arrays. `synthetic_supported` grants no source verification.
- Exactly five attribute IDs, each containing `rating`, `percentile`, status,
  reasons, explicit candidate policy metadata and comparison pool reference.
- Archetype attribute/tier derived from percentiles, and an explicitly withheld
  OVR with `policy_not_finalized`.

There is no production mode in v1. Numeric attributes require synthetic
classification, synthetic source contexts, declared full-season match scopes,
synthetic eligibility and candidate policy metadata. A display-label edit cannot
promote them to verified or production ratings. Real records cannot enable
synthetic privileges. Independent gates cannot be asserted from synthetic data.
Every withheld attribute has null rating/percentile and a nonempty reason list.
This conservative delivery version withholds both together; the existing
presentation helper can still represent independently missing values.

Both parsers reject unknown fields, missing/duplicate attributes, duplicate
canonical identities, unsafe IDs, nonfinite/boolean/out-of-range numbers,
scope/pool mismatches, conflicting appearance status, duplicate transfer match
contributions, unavailable values with numbers, invented line-breaking scores,
incorrect archetypes and numeric OVR. JSON text readers also reject duplicate
object keys, including escaped spellings. Object-key order is irrelevant.
Serialization sorts players by numeric ID and canonical context, and uses sorted
JSON keys without NaN, timestamps or rounding. Parsing returns independent data.

These checks are structural and policy restrictions, not cryptographic source
authentication. A fully fabricated synthetic document can describe a synthetic
experiment; it cannot authorize real publication. A future production contract
must connect independently reviewed, byte-bound evidence and publication
authorization rather than relax these restrictions or change a display label.

## Numerical formulas and policy provenance

Contributor code was inspected with read-only Git object reads; no branch was
switched and no contributor writer was executed:

- Arpit: `68c5802:src/metrics/recovery_scores.py`.
- Pratyush: `f024cbf:src/metrics/defensive_recoveriesv2.py` and
  `f024cbf:src/metrics/press_resistancev2.py`.

For each defensive component and each eligible pooled four-league role group:

```text
x = component_count / supported_minutes * 90
percentile = 100 * ascending_average_rank(x) / n
rating = clip(65 + 10 * (x - mean(x)) / sample_std(x, ddof=1), 1, 99)
```

`src/defensive_candidates.py` accepts only the explicit
`arpit-component-per90-sample-z/v1` policy, pinned to the source/formula and
synthetic restriction. Each component gets its own distribution. It never copies
aggregate DRI FIFA and never converts its percentile into a rating. It reuses
DRI's conservative three-component eligibility gates, including at least 900
minutes, explicit reference membership, reportability and aligned full-season
numerator/exposure scope. Missing one defensive component conservatively prevents
all three candidate components from entering this reference calculation.

D3A approves aggregate DRI mathematics; it does not approve these individual
FIFA transforms. Arpit's prose describes share-at-or-below, but the inspected code
actually uses pandas average rank; this experiment reproduces the code. Unlike
the contributor neutral-65 fallback, constant and singleton component pools are
withheld. A component can score when DRI itself is constant, provided that
component's own distribution varies: component rating is mathematically separate
from aggregate DRI. The approved `dri_scoring.py` is unchanged.

Press uses the existing `evaluate_press_candidates` and existing count/rate
helpers. For A attempted pressured passes plus dribbles and S successful actions:

```text
x = 100 * S / A
percentile = 100 * ascending_average_rank(S/A) / n
rating = clip(65 + 10 * (x - mean(x)) / sample_std(x, ddof=1), 1, 99)
```

The demonstration explicitly selects 900 minutes, 30 actions, a minimum of two
eligible reference members, separate MID/CB pooling and one reference context per
player-season. These remain candidate conventions. The policy carries source,
formula and thresholds into delivery and can explicitly select another action or
minute threshold. Ratios are attempt-weighted, not the mean of separate pass and
dribble percentages. Constant/singleton press pools withhold. The contributor's
rounding and old Silver-70 convention are not inherited.

Internally, all ratings and percentiles retain float precision. Final display
uses `Math.round`; bars/radar use the unrounded rating. Archetype selection uses
the highest unrounded percentile with existing positional tie order. Gold is
percentile >=90; Silver is >=75 and <90. Rating 95 / percentile 40 has no tier;
rating 60 / percentile 96 is Gold. MID is presented using the existing DM
archetype vocabulary; CB stays separate.

## Transfer representation

`src/transfer_aggregation.py` accepts a raw match ledger and an explicit
`TransferPolicy`. Each contribution retains canonical actor/club/competition/
season, role, match ID, raw counts, supported synthetic minutes and provenance.
The policy must identify combining permission, cross-league permission, nominated
source context, cohort, reference admission and policy provenance.

Counts sum exactly; minutes use `math.fsum`; per90 is recalculated from totals.
Percentiles and FIFA ratings are never accepted as aggregation inputs. Duplicate
match IDs reject rather than silently deduplicate. Identity, role-group, season,
league and count constraints are checked. Missing/inapplicable policy, missing
minutes, real uncertified exposure or incompatible contexts withhold the combined
result. Combining does not automatically admit a reference member.

`require_unique_memberships` prevents repeated actor/season/pool membership.
`transfer_inputs` rechecks the complete original ledger before projecting a
permitted aggregate into the existing scoring inputs. The orchestrator checks
the nominated population context, counts, exposure, role and membership against
that projection. A modified aggregate cannot override the original ledger.

For cross-league experiments, the explicitly nominated existing club context is
the mathematical reference key; it is not an assertion that all matches occurred
in that league. Delivery retains the actual original contexts and match lists.
No synthetic combined club or competition is invented. Actual cross-league
reference attribution still needs team approval.

Synthetic tests model 3057 Jonjo Shelvey (two Premier League clubs) and 13286
Lamine Kone (Ligue 1 and Premier League). Their numbers are invented test inputs,
not measurements or published ratings for those real actors. A 300-minute,
10-tackle contribution plus a 600-minute, 30-tackle contribution gives 900 minutes,
40 tackles and 4 tackles/90, rather than averaging club rates or scores.

## Local end-to-end demonstration

Eight invented actors cover both role groups and all four reference leagues.
Their invented match IDs/full-season declarations have no real-evidence status.
The first actor has tackles rating `53.38104996137775`, percentile `25`, displayed
rating `53`; four attributes are available and line-breaking/OVR remain N/A.
The fourth actor's percentile 100 drives Gold despite its rating around 76.62.

From the repository root:

```powershell
python -B -m scripts.preview_rating_pipeline --output phase2-synthetic.json
cd frontend
$env:VITE_PLAYER_DATA_MODE = 'rating-preview'
npm run dev
```

Import the new local JSON, or the committed
`frontend/tests/fixtures/syntheticRatings.json`. The generator creates its output
exclusively and refuses to overwrite existing files. It has no real input path.
The preview imports files locally without fetching rating assets, uploading or
persisting them. It starts empty and prominently says
`SYNTHETIC / NOT PRODUCTION RATINGS`. Diagnostic real imports carry a separate
withholding notice. Stable full-context keys prevent name/transfer collisions.
Import errors clear the prior model and have no demo fallback; generation tokens
prevent stale asynchronous imports from replacing current state.

The existing default remains demo. Demo/raw/diagnostic loaders, demo JSON,
fictional Clearances behavior, illustrative demo OVR and deployed configuration
are preserved. Preview adds Recoveries through the future rating semantics; it
does not reuse fictional Clearances. Missing axes have no zero bars or radar
points and incomplete profiles have no filled polygon. Unknown role labels show
`Role unavailable`. No site was deployed.

## Verification and preservation

Validation results are recorded below after the final run. Core regressions use
only synthetic inputs and the committed synthetic JSON. The optional real check
reads the retained readiness report and corrected minutes, constructs all 549
withheld records in memory and writes no real-player JSON. Source reports remain
at 210 structurally valid and 14 contradictory active sample appearances, eight
original match pairs and zero season-production-certified contexts.

The full suite was also exercised in a code-only mirror with no `data` directory:
optional real checks skip explicitly. Frontend tests use fresh Python output,
the strict parser and server-rendered React cards; no browser interaction or
network-based visual inspection is claimed.

The sandbox default temporary directory caused initial permission failures;
successful runs use a writable TEMP/TMP directory. One interim full run overlapped
a synthetic fixture schema update and failed the fixture comparison; final runs
use the settled schema. No assertions were disabled to resolve either issue.

Final validation on the settled implementation:

| Check | Result |
|---|---|
| Focused new backend tests | 33 passed; all also included in the full run |
| Full Python suite, warnings treated as errors | **849 passed**, zero skipped; 219.750 seconds |
| Evidence-free code-only full Python suite | **845 run, 4 optional skips**, no failures; 192.783 seconds |
| Recursive frontend JavaScript suite | **154 passed**, zero skipped (112 existing + 42 new) |
| Standard and single-file frontend builds | **8 passed**: both configurations in all four modes |
| Python syntax | **61 files passed**, no bytecode written |
| Git diff and new-file whitespace | Passed; all 13 changed/new files checked |
| Protected input integrity | **136 files byte-identical**, including all original 11 protected Parquets and the additional fixture snapshot (12 local Parquets total) |
| Source evidence / validation directories | Zero additions, deletions or changed bytes |
| Original untracked M4A checklist | Byte-identical |
| Git branch / HEAD / index | `integration-foundation` / `475cc77` / no staged changes |

There are 11 new implementation/test/documentation files and two modified tracked
frontend files. Original untracked data and the checklist remain untracked and
unchanged. No original backend module, raw/diagnostic parser, demo dataset,
hosting configuration or protected input was modified. All 549 real contexts
retain null attribute ratings and percentiles; all real rating denominators,
line-breaking and OVR remain unavailable. No real-player delivery file was made.

Reproduction commands (from the repository root, installed Python/frontend
dependencies required):

```powershell
python -B -W error -m unittest discover -s tests -p test_rating_pipeline.py -q
python -B -W error -m unittest discover -s tests -q
node --test frontend/tests/*.test.js
git diff --check
```

Both `npm run build` and `npm run preview:single` were checked for `demo`, `raw`,
`diagnostic` and `rating-preview`, with outputs in temporary artifact directories.
These are local build checks, not deployments. Python syntax checks compile all
source, script and test files in memory without writing bytecode. The preservation
inventory/result and full test/build logs are local validation artifacts outside
the repository; no source evidence was copied into repository code or fixtures.

## Changed files

| Files | Purpose |
|---|---|
| `src/defensive_candidates.py` | Explicit synthetic component transforms |
| `src/transfer_aggregation.py` | Match-ledger aggregation and membership checks |
| `src/rating_delivery.py` | Versioned delivery validator, serializer and archetype metadata |
| `src/rating_pipeline.py` | Candidate orchestration, readiness withholding and transfer projection |
| `scripts/preview_rating_pipeline.py` | Offline invented fixture and exclusive JSON generator |
| `frontend/src/lib/ratingDelivery.js` | Matching strict parser, local reader and card mapping |
| `frontend/src/components/RatingExperience.jsx` | Explicit local file import and stable context search |
| `frontend/src/lib/playerDataMode.js` | Additional opt-in preview loader |
| `frontend/src/components/PlayerCard.jsx` | Preview notice, separate percentile/reasons and unknown-role label |
| `tests/test_rating_pipeline.py` | Synthetic backend flow, transfer, contract and optional real withholding checks |
| `frontend/tests/ratingDelivery.test.js` | Live Python-to-React contract/render and rejection regressions |
| `frontend/tests/fixtures/syntheticRatings.json` | Reproducible eight-actor synthetic delivery; no real data |
| `docs/phase2-consolidated-rating-pipeline.md` | This consolidated implementation and release record |

## Release blockers and remaining work

Independent implementation, synthetic end-to-end demonstration, transfer
experiments, withholding delivery and local preview are complete. Further
synthetic policies or UX refinements can be developed without source acquisition,
but they cannot advance current real records to production status.

Actual real-player release still requires all of the following:

1. Independently supported canonical actor identities, roles, original source
   provenance and a reviewed complete appearance inventory.
2. Supported full-season participation/exposure for every contributing actor,
   with the 14 observed contradictions resolved or handled by an approved policy.
3. Verified complete metric numerators and reportability, aligned to exactly the
   same appearance/denominator scope. A matching fixture list cannot replace this.
4. Evidence expansion beyond eight pairs: the existing manifest lists 1,509
   additional provider match pairs, subject to authorized acquisition and review.
   Existing local lineups may reduce retrieval only after provenance review.
5. A historical Ligue 1 coverage decision; the 377-entry provider list alone does
   not establish complete historical coverage.
6. Team approval for inclusion of Serie A fixture 3879594 in a separate rebuilt
   dataset, followed by identity, events, exposure and numerator reconciliation.
   Its recovered original records remain isolated from delivered datasets.
7. Explicit individual defensive FIFA policy approval; final press transform,
   thresholds and reference population approval; transfer/cross-league/role
   aggregation and reference-membership decisions.
8. An agreed actual line-breaking metric, suitable target-season evidence and
   rating policy. Progressive passing is not a substitute.
9. An approved OVR formula. Four available attributes cannot select one.
10. A separately reviewed production evidence/contract path and publication
    authorization. v1 cannot be enabled for production by editing its flags;
    the synthetic restrictions in `rating_assembly.py` must remain intact.

After a team decision, pin its approved formula, version, thresholds, role and
transfer/reference rules in a reviewed policy implementation. Independently
validated exposure, identity and numerator inputs must then establish eligibility
for that policy. A separate production delivery path can consume those reviewed
results only after publication authorization. Approving a formula alone cannot
enable current unverified data, and selecting another display label or the
existing synthetic equal-average OVR must never enable a field.

No source retrieval, delivered metric/minute changes, dataset replacement,
production rating exports, staging, commits, pushes or deployments were performed.
