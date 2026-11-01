# Off-field disciplinary-card correction — Batch 2A

Review date: 1 November 2026. Branch `off-field-card-fix`, freshly fetched merged Batch 1 baseline `90acc62f467e807462a753cf03f3f352b90e4314`. Isolated worktree `C:/Users/Ayush/Desktop/Projects/Soccer-Impact-Engine-Index-off-field-card-fix`. Original dirty workspaces and earlier audits were preserved read-only. No commit, push, merge, PR, deployment or ratings release was made.

**The confirmed defect is corrected and source-replayed.** Juanfran’s unused-roster disciplinary record no longer creates an asserted playing appearance. Pallois’s already-supported event/lineup intervals are recovered, with his subsequent disciplinary card retained separately. The three supplemental unused-roster cases are also corrected. No other source appearance decision changes.

Published scope: **691 players and all 14,979 historical contribution keys**, across **1,551 fixtures and 5,436,699 original events**. Corrected diagnostics contain **14,978 active contribution keys**: one proved phantom is removed, rather than replaced with a fictitious zero-minute appearance. Supported interval count changes **14,536 → 14,537**. Exactly **two published players / two historical contributions** are affected. Three other source cases are nonpublished and receive no published-score claim. The other **689 published players are unchanged relative to merged Batch 1**.

## Root cause and exact correction

`_check_original_transitions` previously required a represented participation endpoint for every red/second-yellow event, regardless of whether the actor was playing. `appearance_rows` uses observations or blocking source checks to identify asserted appearances. This converted a bench disciplinary record into a phantom appearance, and rejected a legitimately substituted player for a later off-field card.

The original checker still runs unchanged. A separate `_off_field_discipline` proof in `src/statsbomb_participation.py` may remove only the `original_transition_not_represented` check whose exact UUID reference belongs to a proved off-field Bad Behaviour card. All other source checks remain. Frozen `OffFieldDiscipline` records carry the original event reference, classification and corroborating lineup/XI/boundary/transition references. `AdaptedPlayer.off_field_discipline` and `source_reconstruction.appearance_rows` preserve that nonblocking provenance; it does not make `active_appearance` true.

Unused-roster proof requires a complete, unique 11-actor original XI, reliable original period boundaries, no playing-position stint, XI/tactical membership, incoming substitution, return/exit or playing activity for that stable team/player ID. An explicit non-substitute position on the disciplinary actor also blocks the proof. Post-substitution proof requires existing valid stints, an independently walked original entry/temporary-exit/return/substitution sequence, exact event/lineup interval-union equality, no other source inconsistency, and no subsequent playing activity or lineup snapshot. All original source identity and schema checks execute before this classification.

Precise period-local clocks are retained. A same-time substitution/card needs original indices establishing their order; missing or conflicting ordering makes the proof abstain. One-millisecond differences remain exact. A card before entry, during a temporary absence, after an unsupported permanent exit, or with unreliable coverage is not automatically off-field. Foul Committed remains playing evidence, including its red/second-yellow events. No blanket Bad Behaviour/card suppression, timing tolerance, endpoint inference, final-whistle clipping or name-based merge was introduced. Provider strings and stable IDs are unchanged.

## Original source corrections

| Player / fixture | Original decision | Corrected decision | Supported exposure added |
| --- | --- | --- | ---: |
| Juanfran 26023 / 3825670 | Phantom rejected appearance | Bench roster only; no asserted appearance | 0; no playing time invented |
| Nicolas Pallois 3256 / 3900519 | Conflicting evidence | Existing intervals supported | 1573.137 s / 26.21895 min |
| 6672 / 3825869 | Phantom upstream appearance | Bench roster only | None; nonpublished |
| 10612 / 3825885 | Phantom upstream appearance | Bench roster only | None; nonpublished |
| 40458 / 3878555 | Phantom upstream appearance | Bench roster only | None; nonpublished |

Juanfran’s original Bad Behaviour / Red Card UUID is `e8bbbe1d-37fb-4ffb-92dd-ee93a07c6481`, period 2 `00:35:16.470`, with original position `Substitute` and no independently supported entry or playing-position stint. The original roster row, fixture ID, card and byte-bound provenance survive. The original V1 and merged-baseline canonical fixture sets are immutable inputs; only a copied corrected diagnostic scope removes the false contribution.

Pallois: original XI → temporary exit UUID `57e0aba7-b4e4-4c32-913a-fb4070a4f71b` at period 1 `00:06:29.128` → return UUID `8dfec95b-f3aa-4c8d-a732-ab754bfd7653` at `00:09:26.133` → injury substitution UUID `97e31f4a-5b3f-42d1-904c-e50b384d219d` at `00:29:10.142`. The original supported intervals are exactly `[0,389.128]` and `[566.133,1750.142]` seconds in period 1. Their sum is **1573137/1000 seconds**. The absence is **177.005 seconds**, explicitly excluded. The later red card UUID `7524424d-4b7b-482d-93eb-0611dde9d8b1`, period 2 `00:49:09.389`, occurs after the proved substitution in both exact clock and original index order.

All five exact event documents and lineup SHA256 values are listed below; provider references and original fixture/report hashes are also retained per row in `appearance-comparison.csv` and `input-hashes.json`.

| Player / fixture | Original events SHA256 | Original lineups SHA256 |
| --- | --- | --- |
| 26023 / 3825670 | `6c90b8df7e4b3405b9f0f5ac03af9b4f7c3ed81273ac5bc011ee8fac42e03be7` | `ddc98bfbb8c8cd0c90cf275067dec05d3f5cead82e1c740d09f2b12ec0d62021` |
| 6672 / 3825869 | `a2bd37559434e28b04f56821d10399451a5c39cb9536a7395293a7809b2c0e0e` | `7208c11e225c767782a701f4f150c1f51846b70235f1fd9d230e84aa3da3176c` |
| 10612 / 3825885 | `98ca87e125703e4ad91883d1f816df9fe0516fdb0da6be2bad33c7aacde7441c` | `ea9def0cbd8d7054912eb8e95a6910960b6678ea2a17f4cd0f87a28b01937154` |
| 40458 / 3878555 | `d5d0a50c4660802328389d1f6f983755c66849752ecae2415c8e074065e5a823` | `5465ae381041d61d8505c2db0d656be671ddea0d8c33cf0d342c5716745f68d8` |
| 3256 / 3900519 | `49e0e7fe5ea0c69c297519f2b81c9dd67c388d489782fbb5f03959fcd9a85c3b` | `159c52763629ed5cbc8c7a0da458aad26d1816d3ab07218686a73098c841520a` |

Supplemental disciplinary UUIDs: `64a577f6-1bd2-4ca5-bc3d-f6c8c61c157b` (6672), `12abeefa-7d37-4b1d-b674-1487b0eebc9b` (10612), and `66115c24-7ba3-4208-a1d4-a4f92e2103c3` (40458). They are source-adapter corrections outside the 691-published-recipient calculation. Their upstream sealed measurements and reference membership are not rewritten or rescored in this task.

## Independent verification and complete replay

`scripts/off_field_card_independent.py` uses its own raw-event state walk and raw lineup endpoint reconstruction. It never imports the production off-field decision, adapter Stints or source-check result. The retained decoder oracle now exposes its separately resolved lineup interval union, position intervals and endpoint UUIDs as evidence, without changing its legacy interpretation. The new checker retains original disciplinary UUIDs while separating proved off-field discipline from its state transitions. A regression replaces the production decision with an exception and confirms the independent calculation still succeeds.

The replay executes the actual merged-baseline module obtained from Git and the corrected adapter for every original fixture, then compares all 14,979 published ledger rows and all source roster actors. A diagnostic-only timestamp cache and relevance index optimize the unchanged original-transition check; the complete source schema pass and new off-field proof still see all source records and actor activity. Independent event arithmetic consumes a transition index but its playing-activity/recipient proof sees the full raw events. No optimization is installed in production.

Fresh assertion counts: `{"batch1_recoveries_preserved": 91, "corrected_exact_interval_unions": 14537, "delivered_uuid_contexts": 3036652, "independent_attribute_comparisons": 10365, "independent_eligibility_comparisons": 2073, "independent_formula_b_comparisons": 2073, "merged_baseline_decisions_reproduced": 14979, "original_events": 5436699, "previously_accepted_unchanged": 14536, "priority_conflicts_preserved": 8, "raw_metric_uuid_sets": 74895, "source_reconstruction_card_decisions": 5}`. All **91 Batch 1 recoveries** and both off-camera labels remain intact. All **14,536 previously accepted intervals are identical**, with exact normalized geometry checks on **14,537 corrected accepted intervals**. Raw numerator/pressure-attempt UUID sets are conserved in 74,895 attribute/appearance checks. All canonical names and stable IDs agree with original same-fixture rosters; duplicate source UUIDs, lost legitimate ledger keys and unexpected decisions: **0**.

All 420 original red/second-yellow events remain in the unchanged source universe. The five reclassified disciplinary records are compared field-for-field against the original JSON; no UUID or disciplinary observation is deleted. Juanfran has no selected metric numerator or pressure-attempt UUID in the removed contribution, so removing that nonappearance drops no legitimate measured action. Original versus corrected observation keys and reasons are explicit in `all-appearance-comparison.csv`.

The additional independent check covers **3,626,433 delivered Parquet projections**, with **0** reconstruction-index mismatches, and all **2,514 original frozen-reference candidate/membership predicates**, with **0** discrepancies. The reference is validated against its sealed fingerprint and existing members; no new reference population is fitted. 80 bound previous audit artifacts are reverified unchanged.

## Private diagnostic measurements and Formula B

Three distinct input sets are retained in every population row: original V1 observations, merged Batch 1 diagnostics and corrected Batch 2A diagnostics. Original inputs reproduce every public attribute rating/percentile, overall value or N/A outcome, and eligibility decision. The merged baseline also reproduces the previous exact attribute values, numerators, exposure, percentiles, scores and exclusion sets. Production aggregation/scoring and separately transcribed raw-set/rational arithmetic agree. Original definitions and the fixed reference are used throughout.

Frozen semantic fingerprint: `403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd`. Public ratings SHA256: `9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e`. Neither file is modified. Press resistance remains successful pressured actions / attempted pressured actions; supported elapsed exposure affects its completeness predicates but never changes its action-ratio definition.

| Player | V1 minutes | Batch 1 minutes | Batch 2A minutes | Batch 1 OVR | Batch 2A OVR | Delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Nicolas Pallois (3256) | 1328.81480000 | 1328.81480000 | 1355.03375000 | 75.358617803582 | 75.501561885902 | +0.142944082320 |
| Juan Francisco García García (26023) | 1577.02060000 | 1577.02060000 | 1577.02060000 | 75.188449605939 | 75.188449605939 | +0.000000000000 |

**Pallois, merged Batch 1 → corrected Batch 2A:**

| Attribute | Numerator / attempts before → after | Exact value before → after | Rating before → after | Percentile before → after |
| --- | --- | --- | --- | --- |
| tackles | 17 → 17 | `3825000/3322037` → `1224000/1084027` | 70.648446240741 → 70.011526890807 | 70.642201834862 → 69.724770642202 |
| interceptions | 14 → 15 | `3150000/3322037` → `1080000/1084027` | 68.279728879698 → 69.722728547689 | 64.220183486239 → 68.807339449541 |
| recoveries | 77 → 79 | `17325000/3322037` → `5688000/1084027` | 84.126784421915 → 84.453081085775 | 96.296296296296 → 96.296296296296 |
| press_resistance | 58/94 → 58/94 | `2900/47` → `2900/47` | 61.541657617048 → 61.541657617048 | 33.333333333333 → 33.333333333333 |
| progressive_passing | 67 → 68 | `15075000/3322037` → `4896000/1084027` | 78.379072540801 → 78.203028552600 | 88.073394495413 → 88.073394495413 |

Pallois gains no tackles, one interception, two recoveries and one progressive pass from the corroborated appearance. Those actions are admitted only with the same supported elapsed denominator. His total pressured successes/attempts remain 58/94 and his press-resistance value/rating are unchanged. Extra exposure reduces some per-90 rates, so neither individual ratings nor the overall change are presumed to increase. The independently recomputed overall change agrees with the prior hypothesis; that earlier value is an asserted comparison, not the input to the new calculation.

**Juanfran:** no minute, action count, exact attribute value, rating, percentile or Formula B value changes. His original and corrected values are retained for all five attributes in `player-impact.csv`. The change is removal of one unsupported nonappearance from metric/exposure completeness, not invented time or a score increase.

**Ranking eligibility changes: 0.** Juanfran clears the other checked completeness conditions after the false contribution is removed, but still lacks existing frozen attribute membership. Pallois remains excluded; his separate `3256/3829452` permanent-exit support-policy case is still withheld. All original and corrected exclusion reasons are retained, without automatic promotion. Comparison groups and dominant fine-position groups remain unchanged. No Batch 2B entry exposure is included.

## Conflicts and deferred work

Both Ramos cases (`5201/267533`, `5201/3825879`), Francis `3608/3754058`, Mendy `4506/3829490`, and all four unresolved Batch 1 cases (`23349/3879602`, `40430/3879772`, `3577/3879863`, `13730/3901259`) remain excluded with their previous source contradictions. Every other previously rejected published appearance remains rejected, except the single supported Pallois recovery and Juanfran’s explicit nonappearance removal. In total **441 active appearances retain unresolved/unsupported exposure** after this correction; this count includes genuine coverage and policy exclusions, not 441 demonstrated implementation bugs.

All ten corroborated Tactical Shift entry proposals remain deferred to Batch 2B. The three clean permanent-exit support-policy cases remain excluded for later review. Other conflicting lineups, missing source evidence, exact chronology exceptions and conservative name-admission restrictions remain intact. This same-provider reconstruction corroborates retained source geometry; it does not certify complete historical seasons or replace missing games with zero observations.

## Tests and build

| Verification | Passed | Failed | Skipped | Blocked | Deselected |
| --- | ---: | ---: | ---: | ---: | ---: |
| public_backend | 1065 | 0 | 0 | 0 | 0 |
| private_backend | 51 | 0 | 0 | 0 | 125 |
| original_source_regressions | 15 | 0 | 0 | 0 | 0 |
| retained_independent_regressions | 12 | 0 | 0 | 0 | 0 |
| identity_join_probes | 12 | 0 | 0 | 0 | 0 |
| public_frontend | 211 | 0 | 0 | 0 | 0 |
| private_frontend | 33 | 1 | 0 | 0 | 0 |
| production_build | 1 | 0 | 0 | 0 | 0 |

The public suite includes **36 new regressions**, not an additional 36 tests to add to the public total. They cover both disciplinary card types, unused and substituted states, genuine active dismissals, continuing lineups, pre-entry cards, temporary absences, ambiguous coverage/state, equal-time source order, millisecond separation, missing/duplicate entries or substitutions, conflicting IDs/names, after-exit actor/recipient activity, retained UUIDs, aliases and checker independence. The 15 source regressions include ten Batch 2B subcases and three permanent-policy subcases; these subcases are not extra top-level test counts. The 125 private deselections are outside that suite and are not skips.

The private frontend retains the known obsolete badge em-dash/typography expectation failure at `provisionalOvr.test.js:61` (test begins at line 44). No ratings or frontend behavior was changed to make it pass. Its current application files and reviewed private test fingerprints are bound in `audit-output/private-frontend-provenance.json`.

Unsuccessful setup/diagnostic attempts are retained: the first synthetic run had four fixture-serialization errors because its index helper cached Fraction clocks into test JSON; copying before parsing fixed the fixture helper. A private frontend provisioning attempt lacked its static toy-data directory and was rerun after restoring the exact fixture. Two source-replay harness attempts compared module-local dataclass types and tuple-valued issue IDs directly to separately loaded/JSON records; their structural comparison was corrected without changing production decisions. Only the completed final replay supplies these results. A final full public suite was rerun after the independent transition-index change and passed.

## Reproduction

Use Python 3.13 with the project requirements, locked frontend dependencies and the authorized retained sibling evidence workspaces. All new large outputs are ignored. The replay refuses an existing output directory; preserve or rename a previous run before repeating it.

```powershell
python -B -m scripts.verify_off_field_card_fix
python -B -m scripts.run_backend_tests public -q
python -B audit-output/run-private-backend.py
python -B -m scripts.check_off_field_card_sources
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/test_independent_audit.py
python -B -c "import src, runpy; runpy.run_path('../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/identity_probes.py', run_name='__main__')"
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/scripts/audit_full_player_additional_checks.py --source-root ../Soccer-Impact-Engine-Index --checkout . --output audit-output/off-field-additional
npm.cmd run test:public --prefix frontend
npm.cmd run test:private --prefix audit-output/private-suite-checkout/frontend
npm.cmd run build --prefix frontend
python -B -m scripts.finalize_off_field_card_fix
```

The ignored private backend harness fingerprint-checks the authorized private sources and imports corrected modules before read-only support modules. The ignored frontend harness contains unchanged current application files, the reviewed private tests/fixture, and read-only data/dependency junctions; it does not modify a previous audit checkout. Test/log hashes and original source receipts are in the final manifest.

## Complete modified-file and output inventory

- `src/statsbomb_participation.py`
- `src/source_reconstruction.py`
- `scripts/decoder_fix_independent.py`
- `scripts/off_field_card_independent.py`
- `scripts/verify_off_field_card_fix.py`
- `scripts/check_off_field_card_sources.py`
- `scripts/finalize_off_field_card_fix.py`
- `tests/test_off_field_cards.py`
- `tests/suite_inventory.json`
- `docs/off-field-card-fix-report.md`

Required private files under `audit-output/off-field-card-fix/`: `appearance-comparison.csv` (five published/supplemental source cases), `player-impact.csv` (two published players), `full-population-comparison.csv` (691 players), `off-field-card-evidence.csv` (five original disciplinary records), `summary.json`, `input-hashes.json`, `test-results.json`.

Supplemental outputs there: `all-appearance-comparison.csv` (14,979 retained historical keys, with the explicit nonappearance removal), `baseline-diagnostic-facts.json`, `pending-corrected-facts.json`, `merged_baseline_statsbomb_participation.py`, `output-hashes.json`, `artifact-inventory.json`. `audit-output/off-field-additional/` contains independent delivery/reference/coverage results and receipts. Private harnesses, provenance, source-test receipts, all final logs and unsuccessful attempt logs remain under `audit-output/`; the artifact inventory gives every retained private file path, size and SHA256, without following read-only junctions.

All corrections and numerical comparisons remain local and uncommitted. Published player JSON, V1 scores, frozen reference files, original provider files, Formula B, attribute definitions, identity-admission rules, permanent-exit policy and frontend are unchanged. No team photos or unrelated site changes are included.
