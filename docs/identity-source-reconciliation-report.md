# Stable player identity and source-name reconciliation — Batch 4

Baseline: `1bd99b9c43795ecd670b7ad447d031fd25578c39` (PR #12), fetched from origin/main. Local branch `identity-source-reconciliation`; isolated worktree `C:\Users\Ayush\Desktop\Projects\Soccer-Impact-Engine-Index-identity-source-reconciliation`. No commit, push, PR, merge, deployment or publication was performed. Existing worktrees and their uncommitted work were preserved.

**No new production identity defect is confirmed, and no production matching or admission change is justified by these records.** The same-ID spelling provenance is established; the existing stable-ID resolver already handles supplied IDs. The separate conservative candidate-name flag is retained. Four historical appearance-set mismatches are already resolved by Batch 2A. Remaining activity flags describe bench discipline, not wrong-person attribution.

## Scope and reproducibility

The historical inventory has 2,280 active player/club contexts and 2,974,680 exact delivered associations, with ten restricted contexts. The current scan covers 1,551 retained fixtures and 5,436,699 original events, including the separately retained 34 Bundesliga fixtures. Current source-roster restrictions: 11; restrictions attached to a currently active club context: 9. These populations differ: an unused roster actor is not an active player/club observation. Historical flags are not claims of published errors.

All eight requested prior reports were located across retained worktrees and read. The identity-integrity audit is retained under `C:/Users/Ayush/.codex/worktrees/coverage-audit/Soccer-Impact-Engine-Index/docs/identity-integrity-audit-2026-11-01.md`. The roadmap and initial identity-policy register are in the integrity-audit and source-reconciliation sibling worktrees. Exact paths, hashes and private evidence inputs are recorded in `input-hashes.json`.

## Fernandinho — stable ID 3054

Manchester City team ID 36; Premier League competition ID 2; season 2015/2016, source season ID 27. The 35 original roster records contain `Fernando Luiz Rosa` in 34 fixtures and `Fernando Luiz Roza` in fixture **3754296**. The latter has **294 actor events and 73 pass-recipient references** under ID 3054; every original event spelling agrees with the same-fixture lineup ID/name. Actor and recipient roles remain distinct in the evidence ledger. All 3,873 delivered actor associations remain exact UUID/context matches. No delivered event needs a name override.

Roza fixture events SHA256: `392a2af6232982127b65c14dab1dc52643afbe2c0969d9dc82f2e009e4947ce6`; lineups SHA256: `383d7f62097d8c768c57e081e333cdfe7b6f0b1a47b9c062103e52ba69c307db`; fixture document SHA256: `e07d6d360b30e0cd17f9aeea0db1502d2a5666d298f1b44b83a2d2f21ba3d21b`. Example original actor UUID: `685e5fed-36de-4a5f-94f5-7b1b7ae96c52`. `source-name-evidence.csv` retains every investigated UUID, raw/normalized spelling, role, fixture/team/competition/season IDs, original lineup reference and source hashes for both variants.

Decision: a provenance-bound same-source-ID spelling assertion is recorded in `source-name-decisions.json`, for diagnostic explanation only. **No matching alias is installed. Alias-based admission beyond the existing supplied-ID path is withheld.** The production `CANDIDATE_SOURCE_NAME_DISAGREEMENT` flag remains. The source spelling question is reconciled, but this batch does not promote the upstream context to complete exposure or bypass its conservative admission policy. The existing resolver accepts original supplied stable IDs without adding an ID-less bridge or a cross-club alias. A change to the upstream candidate-admission contract would need its own explicit review; a name flag alone does not recover an event, duration or metric.

## Juanfran — stable ID 26023

Levante UD team ID 221; La Liga, 2015/2016. Batch 2A already resolves the historical `DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT`: the current source active set, selected delivered active set and diagnostic contribution set each contain **20 fixtures**. The V1 historical observed set contains 21, including the removed nonappearance. Fixture 3825670 remains a bench-only roster record, with no entry or position stint and no accepted ledger contribution. Its Bad Behaviour / Red Card UUID `e8bbbe1d-37fb-4ffb-92dd-ee93a07c6481` remains unchanged. No zero-minute observation is invented.

The generic `SOURCE_ACTIVITY_WITHOUT_APPEARANCE` diagnostic can still be reproduced because that loop counts every actor event, including this bench card. It is a separate administrative activity flag, not an unresolved active-appearance mismatch or a player-identity conflict. Retaining that conservative flag changes no accepted measurement. Events SHA256: `6c90b8df7e4b3405b9f0f5ac03af9b4f7c3ed81273ac5bc011ee8fac42e03be7`; lineups SHA256: `ddc98bfbb8c8cd0c90cf275067dec05d3f5cead82e1c740d09f2b12ec0d62021`.

## Current restriction inventory

| Stable ID | Original names | Team ID | Prior reasons | Current reasons | Classification |
| --- | --- | --- | --- | --- | --- |
| 3054 | Fernando Luiz Rosa, Fernando Luiz Roza | 36 | CANDIDATE_SOURCE_NAME_DISAGREEMENT | CANDIDATE_SOURCE_NAME_DISAGREEMENT | A, H |
| 6672 | Jorge Andújar Moreno | 213 | DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H / appearance G |
| 7105 | Fabián Ariel Orellana Valenzuela | 209 | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H |
| 10448 | Adam Ounas | 146 | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H |
| 10612 | Yoel Rodríguez Oterino | 360 | DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H / appearance G |
| 25859 | Sérgio Paulo Barbosa Valente | 223 | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H |
| 26023 | Juan Francisco García García | 221 | DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H / appearance G |
| 27348 | Ricky van Wolfswinkel | 218 | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H |
| 27457 | Manuel Fernández Muñíz | 219 | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H |
| 40458 | Rubens Fernando Moedim | 224 | DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H / appearance G |
| 158769 | Ivan Kelava | 1049 |  | SOURCE_ACTIVITY_WITHOUT_APPEARANCE | C, H |

A = verified source-name inconsistency; C = source activity without an established active appearance; G = already resolved by earlier batches; H = preserved conservative restriction. No genuine conflicting source ID, ambiguous same-context name mapping, missing original identity evidence or new implementation defect was found in these investigated restrictions. The full roster includes source-only actors absent from the historical active-club summary. The exact additional actor and all disciplinary UUIDs/fixtures are in the current inventory and `unresolved-conflicts.csv`. No restriction is cleared using a display nickname.

The other three appearance mismatches (6672/3825869, 10612/3825885, 40458/3878555) are also Batch 2A bench-card removals. Their disciplinary activity remains traceable. The five older activity contexts (7105, 10448, 25859, 27348, 27457) retain administrative source activity without an active appearance. They receive no zero-minute contribution and no published-player recovery claim. All current context rows retain exact reasons rather than conflating identity, activity, missing video and duration support.

## Identity pipeline and safeguards

`prepare_crosswalk` rejects ambiguous and duplicate normalized name/team/competition/season keys. `resolve_events` validates many-to-one cardinality, event order and uniqueness, supplied-ID conflicts, and stable-ID/context population membership. Supplied stable IDs remain authoritative. Missing IDs require caller-trusted evidence and are never guessed. Normalization is limited to declared doubled apostrophes/whitespace and the two existing team aliases; there is no accent folding, nickname or fuzzy bridge.

`identity_evidence` independently validates match-to-season/competition mappings, lineup evidence attestations and source collisions. The requested historical `source_events` implementation is named `flatten_events` in this baseline: it validates original actor/roster identity and event/team/fixture context. `reconcile_event` requires UUID, fixture, team, competition, season, type and original name agreement, and rejects conflicting supplied player/team IDs. The participation adapter also validates XI, tactical and substitution actors against original roster IDs/names. Fresh independent actor and recipient checks cover the complete retained source universe.

The reconstruction script uses exact source UUIDs to locate delivered records, stable match/team/player IDs for roster associations, and a separate candidate-name consistency check. That check remains conservative. Tackles/interceptions/recoveries run through the recovery wrapper with `PLAYER_KEYS`; press resistance uses stable context with a one-to-one exposure join; passing and progressive passing restore supplied IDs by unique event UUID and use stable context/cardinality checks. Scorecard joins remain one-to-one. No new name-based metric join, frontend alias dependency or Batch 5 legacy-helper change is introduced.

## Source, UUID, transfer and participation conservation

A fresh disk-backed primary-key inventory independently reopens all original event bytes and checks exact actor/team/fixture tuples bidirectionally against the hash-validated Batch 3B UUID database. Missing, extra, duplicate and reassigned UUIDs: **0**. Raw actor/recipient spelling and lineup assertions are preserved; no original event record or name is rewritten. The 34 Bundesliga fixtures use their separate retained source reports, rather than being incorrectly counted in the old 2,280-context ledger.

Fresh identity checks: `{"independent_formula_b_comparisons": 4146, "independent_frozen_attribute_comparisons": 20730, "original_events": 5436699, "original_fixtures": 1551, "prior_data_receipts_rehashed": 4667, "stable_actor_bindings": 5415829, "stable_recipient_bindings": 1415384, "unchanged_production_modules": 34, "uuid_actor_fixture_team_bidirectional_comparisons": 5436699}`. Independent transfer checks over the hash-bound historical original scope: `{"actor_fixture_uniqueness": 103, "exposure_conservation": 103, "numerator_conservation": 1030}`. Club-specific provenance is retained; duplicate actor fixtures are rejected, numerators/exposure sum exactly, and no transfer policy or nominated reference context changes. Current UUID uniqueness prevents an event contributing as two different source actors.

Because production reconstruction is unchanged and every production module and consumed original-source hash matches the completed Batch 3B replay, its accepted geometry/measurement verification is reused. This is deliberate hash-bound reuse, not a newly claimed production participation replay. The fresh scan independently verifies source identity and UUID conservation; original-source regressions rerun current adapter/state checks for the remaining bench cases. All 14,550 accepted published contributions retain their geometry. Batch 1: 91 recoveries; Batch 2A: five disciplinary corrections; Batch 2B: 36 entry proofs; Batch 3A: 12 exit proofs; all 17 terminal observations and all existing unresolved contradictions retain their decisions.

Batch 3B remains a separate diagnostic admission layer: the fresh numerical run reapplies its independently source-verified chronology ledger, withholding the full Anthony Weber 7435/3900512 pressure component. Four successes and four attempts remain withheld. Production source reconstruction, sealed V1 facts and published V1 remain separate from these diagnostics and a possible future V2.

## Frozen-reference numerical and eligibility results

A–G comparisons for every one of the 691 published profiles are in `full-population-comparison.csv`: V1, Batch 1, 2A, 2B, 3A, 3B and Batch 4. The fresh Batch 4 score replay recomputes production aggregation under unchanged references and independently confirms raw numerator/attempt sets, exact matched exposure, per-90/action ratios, ratings, percentiles, Formula B and exclusion predicates. It preserves all prior Batch 3B differences relative to earlier stages. Historical A–F arithmetic is independently rechecked against hash-bound diagnostic records.

**Batch 4 versus Batch 3B: zero changes to all five numerators, pressure attempts, supported exposure, attribute values, ratings, percentiles, Formula B, player-season membership and ranking eligibility across all 691 profiles.** No source-association, delivered active-appearance, duration or metric admission decision changes. The same-ID provenance label alone is the new finding. All 2,514 historical frozen-reference candidate records are checked against their original retained scope, including 12,570 per-attribute candidate predicates and frozen membership-set equality, with zero discrepancies. This historical candidate scope is separate from the original source-roster population. No references are refitted.

| Player | Diagnostic fixtures / supported | Exact minutes | Formula B | Eligible |
| --- | --- | --- | --- | --- |
| 3054 | 33 / 31 | 20788177/7500 | 71.4159779782039 | False |
| 26023 | 20 / 20 | 7885103/5000 | 75.18844960593903 | False |

| Player | Attribute | Numerator | Attempts | Exact value | Rating | Percentile |
| --- | --- | --- | --- | --- | --- | --- |
| 3054 | tackles | 73 | None | 49275000/20788177 | 78.11854326361151 | 86.4 |
| 3054 | interceptions | 32 | None | 21600000/20788177 | 67.52284428459328 | 66.4 |
| 3054 | recoveries | 155 | None | 104625000/20788177 | 62.731154765862826 | 41.12903225806452 |
| 3054 | press_resistance | 224 | 306 | 11200/153 | 65.57836658353287 | 51.2 |
| 3054 | progressive_passing | 136 | None | 91800000/20788177 | 73.46390271234233 | 82.4 |
| 26023 | tackles | 23 | None | 10350000/7885103 | 75.25691542875781 | 87.1559633027523 |
| 26023 | interceptions | 25 | None | 11250000/7885103 | 82.64399169863796 | 94.4954128440367 |
| 26023 | recoveries | 72 | None | 32400000/7885103 | 72.82212091024626 | 78.70370370370371 |
| 26023 | press_resistance | 43 | 81 | 4300/81 | 50.036859079832126 | 8.333333333333334 |
| 26023 | progressive_passing | 78 | None | 35100000/7885103 | 77.66745986430371 | 88.07339449541284 |

Every value above is unchanged by Batch 4. Fernandinho still has two unsupported observed contributions and separate metric-scope/frozen-membership exclusions; Juanfran still lacks existing frozen attribute membership. No leaderboard promotion occurs. Remaining exclusions for each potentially affected published player appear in `player-impact.csv`. Nonpublished source-roster matching, activity, geometry, metric admission, reference membership and published-score consequences are unchanged; the evidence ledger separately records their administrative flags.

Frozen semantic fingerprint: `403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd`. Published V1 SHA256: `9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e`.

## Verification

| Suite | Passed | Failed | Skipped | Blocked | Deselected |
| --- | ---: | ---: | ---: | ---: | ---: |
| targeted-regressions | 151 | 0 | 0 | 0 | 0 |
| original-source-regressions | 16 | 0 | 0 | 0 | 0 |
| public-backend | 1137 | 0 | 0 | 0 | 0 |
| private-backend | 51 | 0 | 0 | 0 | 125 |
| independent-regressions | 12 | 0 | 0 | 0 | 0 |
| identity-probes | 12 | 0 | 0 | 0 | 0 |
| public-frontend | 211 | 0 | 0 | 0 | 0 |
| private-frontend | 33 | 1 | 0 | 0 | 0 |
| production-build | 1 | 0 | 0 | 0 | 0 |
| batch4-targeted | 186 | 0 | 0 | 0 | 0 |
| public-backend-final | 1163 | 0 | 0 | 0 | 0 |
| original-identity-records | 8 | 0 | 0 | 0 | 0 |
| source-identity-scan | 1 | 0 | 0 | 0 | 0 |
| independent-numerics | 1 | 0 | 0 | 0 | 0 |
| raw-reference-checks | 1 | 0 | 0 | 0 | 0 |

Suites overlap and are not summed. The private frontend failure remains the pre-existing typography expectation at `provisionalOvr.test.js:61`; no unrelated UI/scoring change was made. The final public suite includes 26 new identity regression cases. Exact commands, logs, exit codes and counts are retained in `test-results.json`. The initial targeted command referenced a nonexistent transfer test filename; the next run lacked two retained chronology evidence files (12 fixture-setup failures). Provisioning the exact retained fixtures resolved all 12, with 186 passing in the final targeted run. An initial numerical check included upstream candidates outside the 691 published comparison and was corrected to the explicit published set. These were harness issues, not newly classified known product failures. The first report finalization attempt used the Windows default encoding for Unicode evidence; explicit UTF-8 reading resolved it, and its failure log remains preserved.

The first source attempt rejected a Git line-ending difference in a diagnostic script; normalized text equality resolved it while production byte checks remain strict. The second detected that the old roster ledger covers 1,517 four-league fixtures; the complete scan explicitly adds the 34 separately retained Bundesliga fixtures. Failed/partial directories and logs remain preserved. The third scan reopened all 1,551 fixtures and built the complete independent UUID index, but its final SQLite attachment failed because URI handling was not enabled. The fresh index is byte-identical to Batch 3B (`1db269d9af16e091f91e40d29d06b8f4f997112ce0605d01713b3acbb77ba969`). The final run enables URI handling, validates and reuses that completed index, rechecks all source hashes and original records, and completes bidirectional comparison. It avoids repeating expensive index insertion; all attempts remain preserved. The completed final run supports the final findings.

## Deliverables, limitations and next phase

Tracked review files: `scripts/investigate_identity_sources.py`, `scripts/verify_batch4_numerics.py`, `scripts/check_identity_source_records.py`, `scripts/finalize_identity_source_reconciliation.py`, `tests/test_identity_source_reconciliation.py`, `tests/suite_inventory.json`, and `docs/identity-source-reconciliation-report.md`. No production `src` module, frontend source, original dataset, frozen reference or published numerical output changes.

All requested private CSV/JSON deliverables are under `audit-output/identity-source-reconciliation/`, with supplemental source-name decisions, full disciplinary records, enriched classifications, transfer contexts and the fresh UUID database. Additional fresh numerical and historical-reference checks are retained under `audit-output/batch4-numerics/` and `audit-output/batch4-additional/`. Test/build logs and private harness inputs remain ignored. `artifact-inventory.json` lists path, size and SHA256 for all review files and task-owned evidence/log files; it excludes its own recursive hash and dependency/data junction traversal. Nothing private is staged.

Reproduce in a fresh worktree/output directory: `python -B -m scripts.investigate_identity_sources`; `python -B -m scripts.verify_batch4_numerics`; the independent additional checker command in `test-results.json`; `python -B -m scripts.check_identity_source_records`; public/private suites; then `python -B -m scripts.finalize_identity_source_reconciliation`. Evidence-producing commands refuse completed output directories. Source data is read-only.

The conclusions are stable-ID consistency findings within retained same-provider records, not external historical attestation or complete-season certification. They establish no wrong-player attribution. Production candidate-name and administrative-activity restrictions are intentionally retained; incomplete duration, source chronology and frozen membership are independent limitations. No implementation/evidence blocker remains for this local investigation. The known private frontend expectation is separate.

Recommended next phase: review the same-ID provenance assertion and decide whether a future versioned reconstruction should distinguish source-proven spelling variants and bench-disciplinary activity from blocking identity conflicts. Such an integration must preserve the existing UUID/context/ID checks and separately compare admission consequences; it is not implemented here. Keep unrelated source contradictions in the provider-resolution queue and handle Batch 5 legacy-helper hardening separately. Do not publish V2 or refit references without authorization.
