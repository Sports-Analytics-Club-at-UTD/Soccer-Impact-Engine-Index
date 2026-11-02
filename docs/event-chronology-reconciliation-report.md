# Event chronology and measurement boundary reconciliation — Batch 3B

Local branch `event-chronology-reconciliation`; worktree `C:/Users/Ayush/Desktop/Projects/Soccer-Impact-Engine-Index-event-chronology-reconciliation`. Fetched origin/main and verified PR #11 merge `95b82a6cf7e591fa7a6623d57e1533fabfb6db79`. Prior dirty workspaces, evidence and audits are preserved. No commit, push, PR, merge, deployment or publication was made.

**One diagnostic admission defect is corrected; production participation and measurement code are unchanged.** The four recovery boundary cases remain excluded. The correction withholds one ambiguous pressure component, admits no new event and changes no interval.

## Original and current exception inventory

All **107 original exceptions across 15 players remain**; none was resolved by Batches 1–3A. Current published inventory: **115 observations across 21 players**, comprising **107 comparable nonadministrative actor-action exceptions across 15 players** and 8 administrative/participation rows. Full roster: **148 observations across 54 players**, including 33 nonpublished observations.

The prior source-reconciliation register has 114 rows across 20 players: all original 107 plus seven Bad Behaviour / Player On observations, including Pallois’s off-field card. The additional published row here is Paolo Sammarco’s Player On `cfc338f2-7318-452e-bbb3-f03b558ce501`, fixture 3879602, period 1 `00:46:25.854`, index 1949, beyond the recorded first-period boundary. His reversed/overlapping lineup and source contradiction remain withheld. It is a new nonmeasurement observation, not a recovered action. All 114 prior UUIDs are present in the conserved source index; the supplemental comparison distinguishes source presence from exception membership.

The original register has 12 distinct selected action UUIDs: four in accepted appearances and eight in rejected 7435/3900512. The other 95 are not selected metric actions. Three of the eight rejected-appearance actions were nevertheless admitted by the older diagnostic pressure-ratio policy; the per-90 candidates were withheld. Metric memberships overlap. Administrative cards, receipts, Pressure rows, unsuccessful actions and other nonmeasurement rows are separately labelled. Unknown interval geometry is stored in `coverage-interval-evidence.csv` (1,226 actor/fixture observations), rather than counted as definite chronology overruns.

## Four priority recovery cases

| Player / fixture | Exact recovery UUID | Period / timestamp / index | Excess seconds | Half End clocks / indices / UUIDs |
| --- | --- | --- | ---: | --- |
| Scott Dann / 3754048 | `11536d85-b54e-409f-b440-cfda9fdcef43` | 2 / 00:49:25.109 / 3643 | 17/500 | 00:49:25.075 / 3641 (`c8f0f7bf-f15e-47e5-8771-1e297e1cf927`); 00:49:25.075 / 3642 (`e9b5c9e0-4bd5-4687-a41b-ab4c368da78c`) |
| Celso Borges Mora / 3825780 | `4d96feb8-6500-4ddb-bcfc-e3b39f8faa2d` | 1 / 00:46:02.693 / 1803 | 73/1000 | 00:46:02.620 / 1801 (`fbbab93b-2cf8-49f1-8691-90ce17225989`); 00:46:02.620 / 1802 (`6900d50e-45bc-419a-97f4-0fb023426533`) |
| Renato Civelli / 3829454 | `d87a52d1-7654-452c-ad0c-70772eff9215` | 1 / 00:48:08.451 / 1672 | 171/1000 | 00:48:08.280 / 1670 (`b98a4b72-f630-4f8a-98dc-4ff42e009ea5`); 00:48:08.280 / 1671 (`4ffbd369-fb23-43c9-8e96-a4df4acaeaf7`) |
| Guillaume Gillet / 3900579 | `4b05296a-67a1-43e2-8aed-f7aa807e5598` | 1 / 00:46:01.861 / 1363 | 63/500 | 00:46:01.735 / 1361 (`9db4f02f-7543-43b5-a6df-c9e4b045b4c9`); 00:46:01.735 / 1362 (`9ade8527-2c5d-44fe-908e-6a4cc88d66f6`) |

Both team Half End assertions agree exactly for each case; every recovery follows both in original index order and exact clock. Separate event-state and lineup-endpoint reconstructions agree on geometry and duration. Correct identity and successful outcome cannot override the period contradiction. No retained separate boundary assertion supports extending time. Dann is beyond his final period and player endpoint; Gillet, Borges and Civelli overrun their first period while inside a nominal cross-period stint. All four retain `NUMERATOR_DENOMINATOR_MISMATCH` and withheld recovery component rates; raw candidate counts/UUIDs remain intact.

## Confirmed diagnostic admission defect

`scripts/score_private_five_attributes.py:71–77` deliberately drops duration-related rejection reasons when building press resistance, since an action ratio does not require minutes. This also loses known chronology ambiguity. In 7435/3900512 it admits four successes/attempts despite three occurring after an original permanent exit followed by an incompatible return. The ratio policy for unknown duration alone is preserved; it does not establish support for contradictory chronology.

`scripts/event_chronology_diagnostics.py` corrects diagnostic facts using an explicit independently verified exception ledger. It reopens original fixture/event/lineup bytes and checks SHA256, fixture/team/stable player, UUID, index, exact timestamp, outcome, metric definition, separately established boundaries, event-state geometry and independent lineup endpoints. Conflicting interpretations remain contradictory. When a selected action has verified chronology ambiguity, the complete component is withheld with `SOURCE_CHRONOLOGY_CONFLICT`. It preserves raw numerator/denominator UUIDs and counts rather than dropping uncertain denominator actions to improve a ratio. No player or fixture is hardcoded in correction logic.

The existing release builder, sealed facts and source reconstruction are not overwritten. The new finalizer applies this general adjudication layer only to local Batch 3B diagnostics. This is not a V2 release or new production certification. Integration into a future versioned reconstruction requires review.

Affected player: **Anthony Weber (7435)**. Three disputed pressured actions trigger one component withdrawal. All four previously admitted fixture successes/attempts are withheld, including one otherwise supported action because the component must retain a coherent numerator/denominator scope. **Admitted pressure successes: −4; admitted attempts: −4.** Original source and candidate UUIDs/counts remain unchanged. Complete evidence is in `verified-measurement-corrections.json`; all four changed admission UUIDs are in `changed-metric-events.csv`.

## Frozen-reference attribute and Formula B effects

| Attribute | Numerator before → after | Attempts before → after | Exact value before → after | Rating before → after | Percentile before → after |
| --- | --- | --- | --- | --- | --- |
| tackles | 14 → 14 | None → None | `75600000/94611863` → `75600000/94611863` | 60.575328326728595 → 60.575328326728595 | 37.61467889908257 → 37.61467889908257 |
| interceptions | 17 → 17 | None → None | `91800000/94611863` → `91800000/94611863` | 68.94211627962306 → 68.94211627962306 | 67.88990825688073 → 67.88990825688073 |
| recoveries | 45 → 45 | None → None | `243000000/94611863` → `243000000/94611863` | 57.07732377405279 → 57.07732377405279 | 22.22222222222222 → 22.22222222222222 |
| press_resistance | 83 → 79 | 113 → 109 | `8300/113` → `7900/109` | 77.23069650289477 → 75.92973526853555 | 93.51851851851852 → 87.96296296296296 |
| progressive_passing | 67 → 67 | None → None | `361800000/94611863` → `361800000/94611863` | 72.50290983561644 → 72.50290983561644 | 82.56880733944953 → 82.56880733944953 |

Formula B: **69.87739129211172 → 69.48710292180395**, delta **-0.39028837030777197**. Supported minutes: **94611863/60000 → 94611863/60000**, delta **0**. Ranking eligibility: **False → False**. All remaining exclusions are preserved in `player-impact.csv`.

Tackles, interceptions, recoveries and progressive passing have zero numerator, exposure, rating and percentile change. The pressure denominator change is four actions, not minutes. Total supported exposure is unchanged. The other 690 published profiles have no diagnostic difference. Eligibility changes: 0. Frozen membership and fingerprint `403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd` remain fixed. No promotion is performed.

All 691 A–F comparisons are retained: published V1, Batch 1, Batch 2A, Batch 2B, Batch 3A, Batch 3B. Current E/F production aggregation/scoring agrees with separate rational counts/rates, normalization, percentiles, Formula B and eligibility calculations. Historical A–E arithmetic is checked against hash-bound retained diagnostics, without repeating their full original-source scans.

## Chronology semantics and preserved restrictions

`event_within_exposure` requires accepted participation, a supported source period and inclusive exact rational player endpoints. Events exactly at supported starts/ends or Half End pass; unsupported clocks one millisecond outside do not. `measurements` preserves raw selected UUIDs, identifies alignment failures and withholds rates. Its timestamp predicate is not an independent adjudicator of equal-clock transitions; existing indexed transition proof and ambiguity rejection remain in force. No generic epsilon, rounding, snapping, clock correction, assumed 45/90-minute duration or final-whistle extension is introduced. Provider 0/45 minute offsets are coordinates checked against original timestamps; actual boundary lengths determine exposure.

Successful tackle/interception outcomes, nonfailed recoveries and the existing pressured Pass/Dribble definition are unchanged. Press resistance remains successes/attempts. Pressure and receipts are not ratio successes. Progressive passing retains source geometry, open-play, completion, actor/recipient validation, missing-geometry, all-pass exposure and pending fixture restrictions. Fixture 3879594 remains pending. Stable identity/name admission is unchanged.

## Complete source replay and prior corrections

The final complete replay reopens **1,551 fixtures and 5,436,699 original events**. All **14,979 historical published ledger decisions**, including Juanfran’s removed nonappearance, match Batch 3A. All **14,550 accepted published appearances** retain exact original geometry, positions and duration. The entire production `src` tree is byte-identical to Batch 3A. Independent endpoints match **41,828 accepted roster appearances**. The disk-backed global UUID key proves uniqueness/conservation; 430,440 raw metric set comparisons, 418,280 independent alignment checks and 74,890 current fact UUID comparisons pass.

Preserved: all 91 Batch 1 recoveries; Juanfran/Pallois and three supplemental Batch 2A bench cards (five off-field records); all 36 Batch 2B entries (10 published, 26 nonpublished); all 12 Batch 3A exits (3 published, 9 nonpublished). All 17 permanent source observations retain decisions, including the five unresolved records and Robert Beric’s conflicting off-camera label. Ramos, Francis, Mendy and the four unresolved Batch 1 cases remain withheld. The pressure correction affects none of the earlier recovered appearances.

The broader roster search finds 33 additional nonpublished observations, including five selected recovery candidates already withheld by alignment/participation rules. It finds no additional selected pressure chronology exception. Nonpublished diagnostic changes: 0. Unexpected published/nonpublished changes: 0. Because production reconstruction is unchanged, the completed validated source replay is reused. The diagnostic patch receives targeted two-method original-source checks and a complete 691-profile E/F numerical replay.

Source checks: `{"all_roster_exact_geometries": 41828, "batch1_recoveries_preserved": 91, "batch2a_offfield_records_preserved": 5, "batch2b_entry_proofs_preserved": 36, "batch3a_exit_proofs_preserved": 12, "frozen_fact_raw_uuid_sets": 74890, "independent_measurement_alignment": 418280, "original_events": 5436699, "published_accepted_preserved": 14550, "published_decisions_preserved": 14979, "raw_metric_uuid_sets": 430440, "stable_actor_or_recipient_bindings": 6831213, "terminal_observations_preserved": 17}`. Numerical checks: `{"historical_attribute_checks": 17275, "historical_formula_b_checks": 3455, "independent_current_attribute_checks": 6910, "independent_current_eligibility_checks": 1382, "independent_current_formula_b_checks": 1382}`.

## Verification results

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
| chronology-targeted-initial | 205 | 0 | 0 | 0 | 0 |
| chronology-targeted-final | 213 | 0 | 0 | 0 | 0 |
| diagnostic-admission-regressions | 64 | 0 | 0 | 0 | 0 |
| public-backend-final | 1137 | 0 | 0 | 0 | 0 |
| private-backend-final | 51 | 0 | 0 | 0 | 125 |
| full-population-source-replay | 1 | 0 | 0 | 0 | 0 |

Suites overlap; do not sum them as distinct tests. Private frontend reproduces the known `provisionalOvr.test.js:61` badge typography failure. No UI or unrelated numerical behavior is changed for it. Exact commands, exit codes and log paths are in `test-results.json`. Independent original-source, UUID, identity, numerator/exposure and frozen arithmetic evidence supports these conclusions; test passage alone is insufficient.

Regressions cover both sides of exact endpoints/Half End; stoppage; period-local/cross-period clocks; success/failure; administrative rows, Pressure and receipts; missing geometry; pre-entry, temporary absence, substitution, permanent exit and dismissal; contradictory intervals; duplicate UUIDs; conflicting IDs; the four recovery originals; supported measurements; all earlier batches. Existing suites cover indexed equal-clock and ambiguous ordering. New diagnostic tests reject tampered hash/team/index/time, preserve raw counts/UUIDs and ratio semantics, retain unknown-duration policy, reject withholding based on the supported pre-exit action and verify the real permanent-exit contradiction.

## Evidence limitations, failed attempts and next phase

These are independent calculations over retained same-provider records, not external historical attestation. The contradictory exit/return is not repaired. The four boundary overruns remain unresolved without explicit corrected provider or independent boundary evidence. Unknown coverage, lineup and identity evidence is not invented. All original 107 source exceptions remain; the verified correction changes diagnostic admission rather than raw chronology.

Failed/partial attempts remain under `audit-output/*attempt*`. An initial serialization failure, a population diagnostic stopped after 100 fixtures to separate missing geometry from actual chronology, and a pre-scan syntax error are preserved. The corrected scan is the sole completed full source replay. A proposed write was not executed when automatic approval review hit a usage limit; work resumed after the user requested continuation. A later oversized Windows command was rejected before execution and recorded separately.

Reproduce with the retained sibling evidence: priority preflight `python -B -m scripts.reconcile_event_chronology --priority`; targeted/public/private suites; final source replay `python -B -m scripts.reconcile_event_chronology`; final numerical/admission pass `python -B -m scripts.finalize_event_chronology`. Scans refuse existing output directories; preserve completed/failed runs. Finalization changes only in-memory diagnostic facts and ignored outputs.

Recommended next phase: review this pressure-admission correction and its integration contract before any versioned reconstruction, then proceed to Batch 4 stable-ID/source-name and delivered-appearance reconciliation. Keep unresolved chronology in a provider-resolution queue. Do not apply a timing tolerance or generate/publish V2 without explicit approval.

## Full local modified-file inventory

Tracked additions: `scripts/reconcile_event_chronology.py`, `scripts/event_chronology_diagnostics.py`, `scripts/finalize_event_chronology.py`, `tests/test_event_chronology.py`, `docs/event-chronology-reconciliation-report.md`. No existing tracked production source, published JSON, V1 numerical output, original StatsBomb record or frozen reference is modified.

Required private evidence: `audit-output/event-chronology/{original-exception-inventory.csv,current-exception-inventory.csv,exception-classifications.csv,changed-metric-events.csv,appearance-comparison.csv,player-impact.csv,full-population-comparison.csv,unresolved-conflicts.csv,summary.json,input-hashes.json,test-results.json,artifact-inventory.json}`. Supplemental: `verified-measurement-corrections.json`, `source-reconciliation-inventory-comparison.csv`, `coverage-interval-evidence.csv`, `priority-evidence.json`, `source-uuid-index.sqlite`. Priority checks, failed attempts, complete test/build logs and private harnesses stay ignored under `audit-output`. Ignored provisioning/build artifacts include `frontend/node_modules` (junction) and `frontend/dist/`. The artifact inventory enumerates private/review/build files with size and SHA256, excluding its own recursive hash and without traversing data/dependency junctions.
