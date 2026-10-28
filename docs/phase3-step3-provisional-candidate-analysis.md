# Phase 3 continuation: completed evidence analysis and Step 3 gates

October 28, 2026. Branch `integration-foundation`, HEAD
`96b3989e09d1349ed5313b0d7b1ec6471ae7e21a`.

**PROVISIONAL REAL-DATA ANALYSIS / NOT PRODUCTION-CERTIFIED /
NOT PUBLICATION-AUTHORIZED.**

The interrupted Step 2 report is recovered in
`docs/phase3-step2-player-reconstruction.md`. The existing sealed reconstruction
and its original input receipts were verified without rebuilding any source,
SQLite index or large ledger. All 1,517 matches, 5,321,459 original events,
2,974,680 exact target delivered-event associations, 2,177 player IDs and 2,280
club contexts remain intact. The source-supported 900-minute gate yields 238
contexts; 236 have aligned core measurement scopes. None is production certified.

Step 3 now has a deterministic real-data input adapter, existing-engine gate
results, per-component readiness, formula provenance, transfer-policy references
and an isolated frontend contract test. **Zero numeric real-player rating
candidates can pass the current engine/evidence gates.** Numeric Step 3 is not
complete. No evidence flags, synthetic privileges, formulas or policies were
changed to manufacture a result.

## Actual engine audit and reuse

`src.real_candidate_analysis.analyze` projects real source-backed measurements
into the exact existing `score_dri` population and measurement contracts. It
supplies `Evidence('UNVERIFIED', bound_source_reference, False)` for identity,
context, exposure and component/pool coverage. The comparison pool's expected
kind is VERIFIED, which describes the engine requirement, not an attestation
that these inputs satisfy it. Reference membership is false for every context.
`SeasonScope.full_season` remains false because complete provider inventory
observation is not independently certified full-season exposure.

The existing `src.dri_scoring.score_dri` was executed on all 2,280 real contexts.
It retained every row and returned N/A for every DRI, component percentile,
DRI percentile, z-score and FIFA result. All required independent-evidence,
reportability, reference membership, pool completeness and full-season gates
remain explicit in `dri-engine-results.jsonl`. There are no fitted comparison
distributions and no approved reference members.

Existing real-data boundaries were exercised and held:

- `defensive_candidates.evaluate_defensive_candidates` rejects a verified-kind
  real pool: individual component experiments are synthetic-only.
- `press_scoring.evaluate_press_candidates` rejects real evidence: its evidence
  contract and numeric candidate policies are synthetic-only.
- `rating_pipeline.synthetic_rating_delivery` rejects real input before numeric
  orchestration. `transfer_aggregation` likewise does not certify real exposure.
- `rating_pipeline.readiness_rating_delivery` accepts the existing noncertifying
  season-readiness report and produces diagnostic cards with all ratings withheld.

The adapter adds no rating mathematics. It reuses existing DRI validation,
candidate count/per90 facts, and the existing pressured-action completion helper.
It does not relabel real inputs as synthetic, create independent attestations,
select reference contexts, pool transfers, clone a z-score transform or extend
the public contract. Existing engine and frontend implementation files are
unchanged.

## Candidate measurement coverage

Analysis scope excludes `3879594`. Its original provider facts remain separately
visible, and its source-only context receives missing delivered-scope counts,
not fabricated zero counts. Original and analysis match lists, raw provider
counts, delivered-scope numerators, exact supported denominators, aligned subsets,
role labels, eligibility, source references and null rating fields are retained.
Every summary identity/match set was checked against the appearance ledger;
match source/review/fixture bindings are preserved separately.

| Group | Contexts examined | Complete observed 900-minute candidates | All core scopes aligned |
| --- | ---: | ---: | ---: |
| MID (delivered DM + CM labels) | 478 | 127 | 126 |
| CB | 362 | 111 | 110 |
| No supported comparison label in delivered candidate population | 1,440 | 0 | 0 |
| Total | 2,280 | 238 | 236 |

The last group is not a new inferred role: source position minutes remain
available in the sealed reconstruction, but no dominant-role classification is
invented. Delivered DM/CM/CB labels still require role policy approval.

| Measurement at complete observed 900-minute scope | MID candidates | CB candidates | Numeric ratings generated |
| --- | ---: | ---: | ---: |
| Tackles | 127 | 111 | 0 |
| Interceptions | 127 | 111 | 0 |
| Recoveries | 126 | 110 | 0 |
| Pressure pass/dribble counts and combined completion percentage | 127 | 111 | 0 |
| Level A progressive attempts/completions/third crossings | 127 | 111 | 0 |
| True line breaking | 0 | 0 | 0 |
| OVR | 0 | 0 | 0 |

Across all roles and minute levels, complete aligned source rates are available
for 1,322 contexts for tackles, interceptions, press counts and progressive
counts; recoveries have 1,318. This is measurement availability, not scoring
eligibility. In MID, those figures are 260 and 259 respectively; CB, 188 and
187. All rating/percentile fields remain null in all 2,280 analysis contexts.

The existing press measurement is `100 * successes / attempts`, with null when
attempts are zero. It is not a FIFA score or a percentile. The existing 30-action
and 50-action candidate alternatives were compared without choosing a policy:
all 127 MID candidates meet both; 111 CB meet 30 and 105 CB meet 50. These
counts do not approve a minimum, reference size, pooling or transform.

## Formula and evidence decisions

The aggregate DRI methodology has D3A approval: equal mean of the three
component per90 average-rank percentiles, followed by its sample-z
`clip(65 + 10*z, 1, 99)` transform. That approval does not certify the real
input population. Individual defensive transforms are separately unapproved
synthetic candidates (`arpit-component-per90-sample-z/v1`, pinned to contributor
source `68c5802:src/metrics/recovery_scores.py`). Their implementation operates
on per90 distributions, not a substituted DRI or a displayed percentile.

Press's implemented sample-z FIFA and percentile experiments remain unapproved
for real data. No policy is selected. Displayed future attributes follow the
FIFA-style direction; percentiles remain separate archetype inputs. The existing
archetype rules use Gold >=90th percentile and Silver >=75th and <90th. No real
archetype can be assigned while all required score percentiles are missing.

Progressive passes retain their existing geometry-based Level A meaning. There
is no implemented approved mapping from these counts to a real fifth attribute.
They do not become true line-breaking passes. Target 2015/16 StatsBomb 360 rows
remain zero, true line-breaking scores remain null, and no difficulty/pass-value
calibration is fabricated. No OVR formula exists here; overall ratings remain N/A.

The 1,095 contradictory and 365 incomplete appearances remain unresolved. Ten
contexts retain the existing identity/activity flags: five name/appearance
disagreements and five conservative activity review contexts. The six no-stint
events are substitute Bad Behaviour cards, not evidence of playing time. Nine
recovery events outside validated exposure remain in raw counts with affected
rates withheld. No unresolved minutes are imputed, discarded into a false
complete season, or combined with wider numerators.

Transfer alternatives remain bound to the unchanged 103-player-season source
comparison, including 38 cross-league cases. Raw-count/minute threshold changes
for IDs `3951`, `9593`, `23329`, `23488` are retained; no club/reference context is
selected and no rating is averaged. Ligue 1 remains 377 provider-listed matches,
not a certified 380-match historical season. `3879594` stays outside the analysis
scoring population pending separate scope approval.

## Website handoff

`offline-withheld-contract-fixture.json` contains 549 diagnostic records produced
by the existing readiness delivery path, matching the earlier table-qualified
population. It is an isolated contract fixture, not a real rating feed. All five
attribute ratings and percentiles, archetype slots and OVR remain unavailable.
The fixture is accepted by the existing Python validator, JavaScript parser,
`ratingPlayers`, local-file reader and `ratingCard`; all displayed values are N/A.
Five attempted promotions (publication, synthetic privileges, numeric attribute,
numeric OVR, duplicate identity) are rejected.

The legacy v1 envelope retains its required fixed synthetic notice. This is a
contract limitation, not a real scoring authorization; the frontend assigns
these records `DIAGNOSTIC / RATINGS WITHHELD`. The analysis artifacts carry the
explicit provisional real-data notice above. Raw analysis files are not directly
compatible with v1's exact fields and cannot be relabeled into numeric ratings.
No frontend mode, preview, public feed, deployed demo or website file was changed.

Before Step 4: review source/identity/exposure/numerator attestations; approve
role/transfer/reference membership and individual policies; support permitted
real numeric inputs in the existing engine under a reviewed evidence path;
design a versioned real-data delivery contract/parser with explicit trust,
approval and publication gates; map exact actor/context/provenance and separately
missing values; rerun offline integration, precision and security checks; then
obtain explicit website/publication authorization. Preserve v1's current tests.
Missing line breaking and OVR may remain N/A; they must not be invented.

## Deliverables and reproduction

New continuation files:

- `docs/phase3-step2-player-reconstruction.md`
- `docs/phase3-step3-provisional-candidate-analysis.md`
- `src/real_candidate_analysis.py`
- `scripts/analyze_real_candidates.py`
- `scripts/check_real_candidate_handoff.mjs`
- `tests/test_real_candidate_analysis.py`

New sealed analysis directory:
`data/derived/phase3-step3-provisional-analysis-2026-10-28/`:

- `component-candidates.jsonl`, `match-source-bindings.jsonl`
- `dri-engine-inputs.json`, `dri-engine-results.jsonl`, `dri-reference-pools.json`
- `existing-boundary-checks.json`, `formula-and-gate-register.json`
- `transfer-policy-readiness.json`, `offline-withheld-contract-fixture.json`
- `website-handoff.json`, `source-receipt.json`, `summary.json`, `run-manifest.json`

The source receipt binds the unchanged 21-file core; the analysis manifest binds
all new artifacts, code/runtime recipe, existing engines and frontend contract.
The separate continuation verification directory records tests, preservation,
idempotence, Git status and fingerprints of these deliverables. Existing Step 2
core and review artifacts are not edited to add continuation metadata.
Its exact path is `data/derived/phase3-continuation-verification-2026-10-28/`;
`final-review-manifest.json` enumerates and fingerprints the new deliverables.

```powershell
python -B -W error -m scripts.analyze_real_candidates --output data/derived/phase3-step3-provisional-analysis-2026-10-28
python -B -W error -m unittest discover -s tests -p test_real_candidate_analysis.py -q
python -B -W error -m unittest discover -s tests -q
node --test frontend/tests/*.test.js
node scripts/check_real_candidate_handoff.mjs data/derived/phase3-step3-provisional-analysis-2026-10-28/offline-withheld-contract-fixture.json
```

Existing output is rehashed and reused without writes. Partial, stale,
corrupt or conflicting output refuses overwrite. Reconstruction/source failures
stop consumption; no rebuild or repair is attempted.

## Validation, preservation and remaining decisions

The 16 focused continuation tests pass. They cover exact 900-minute rational
boundaries, unchanged source facts, ID and scope associations, separate groups,
missing/contradictory exposure, denominator arithmetic, transfer nonadmission,
press measurements and action alternatives, missing line breaking/OVR,
determinism, idempotence, source/output tampering, partial output refusal and
actual Python-to-JavaScript contract integration. Regression and preservation
results are recorded in the continuation verification artifacts. The full Python
suite passes **899 tests** with warnings as errors (883 prior plus 16 new), with
zero failures. The frontend suite passes **154 tests**, with zero failures or
skips. The actual offline real-data fixture passes the existing frontend contract
and N/A presentation checks for all **549** records, with five promotion attempts
rejected. The 13-file real-analysis bundle passes idempotent reuse with all
source/output fingerprints checked and every size/mtime unchanged.

All **12,282 pre-existing files (7,685,926,710 bytes)** match their starting
SHA256/size with no missing files. This extends the previous 12,250-file Step 2
preservation result to the completed reconstruction, supplementary review and
prior new implementation/tests. All original source evidence, protected
Parquets, Arpit fixture snapshot, M4A checklist, prior alias edits and deployed
frontend files remain unchanged. No reconstruction was restarted.

Specific teammate decisions remain: identity/exposure reviewers must attest
source actors and approve conflict handling, clocks and roles; the integration
lead must resolve historical Ligue 1 and `3879594` scope and nominate an explicit
transfer/reference policy; scoring owners must approve individual defensive,
press, line-breaking and OVR policies or their continued N/A states; delivery
owners must approve the versioned real-data contract and publication boundary.
The 238/236 readiness counts cannot substitute for these decisions.

Step 2 reporting and the maximum currently permitted Step 3 technical analysis
are complete. Numeric Step 3 and real website integration remain blocked by
the documented evidence, membership and policy gaps. Branch/HEAD and the empty
index are preserved; the only tracked modifications remain the pre-existing
two alias files. No protected input, prior implementation/test/report,
reconstruction artifact or deployed frontend file was changed. No network
acquisition, staging, commit, push, upload, publication or deployment occurred.
