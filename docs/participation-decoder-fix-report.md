# Participation decoder correction, Batch 1

Review date: 1 November 2026. Local branch `participation-decoder-fix`, based on freshly fetched `origin/main` at `f2104e396fe89c52637cf0ca7bd1208197ffc1f4`. Worktree: `C:/Users/Ayush/Desktop/Projects/Soccer-Impact-Engine-Index-participation-decoder-fix`. No commit, push, PR, merge, deployment, public numerical update or new reference snapshot was made. The original dirty checkout and previous audit were inputs only.

## Validated results

Both exact off-camera lineup labels now resolve to their original StatsBomb `Player On` / `Player Off` events and existing return / temporary-exit behavior. The corrected production decoder recovered **91 of 95 appearances**, giving **77 of 80 affected players** additional supported exposure. Four remain withheld. These are actual production-decoder results cross-checked against original events and lineups, rather than the audit's hypothetical counts.

All **691 published players**, **14,979 appearances** and **1,551 original fixtures** were replayed. **611 players outside the identified 80** remain unchanged. Unexpected changes: **0**. Historical diagnostic score discrepancies: **0**.

**77 players have changed diagnostic attribute inputs**, **77 have changed attribute ratings**, and **77 have changed Formula B overall ratings**. Press resistance remains an action-completion ratio, with its existing action scope, not a per-90 value. The other four attributes add corroborated action UUIDs and exactly matched exposure; actions are never added without their source participation denominator. Per-attribute raw counts, exact rates, exposure, ratings, percentiles and exclusion reasons are retained in the CSVs. Rating-change counts by attribute are `{"interceptions": 77, "press_resistance": 0, "progressive_passing": 77, "recoveries": 77, "tackles": 77}`; exact pressure-ratio value changes: **0**.

Largest positive overall change: **Yussif Raman Chibsah (9903), 66.2331514551 → 67.4022822059, +1.1691307508**. Largest negative: **Vladlen Yurchenko (24428), 74.6445075244 → 71.9316100592, -2.7128974653**. The CSV values retain full precision; presentation here does not feed calculations.

Ranking eligibility changes under frozen membership: **0**. **28** currently excluded players clear the other checked completeness and threshold predicates but still lack existing frozen membership. No automatic promotion was made.

## Root cause and implementation

`src/statsbomb_participation.py::_adapt_match.endpoint` previously omitted the two legitimate off-camera labels. Add `Player On (Off Camera)` → (`Player On`, `return`) and `Player Off (Off Camera)` → (`Player Off`, `temporary_exit`). `src/independent_source_checks.py::endpoint` receives the same exact label support with its original endpoint-direction restrictions. No prefix-based production mapping, unknown label support, validation relaxation, duration rounding or timestamp tolerance was introduced. Original events retain their normal type names; the aliases describe lineup endpoints.

Every existing supported mapping remains. Source actor/team/name association, lineup positions, original transition representation, substitutions, permanent exits, dismissals, snapshots, interval order, overlap and period-boundary checks still execute. An alias only resolves a candidate endpoint; it does not authorize an appearance.

## Original source evidence and independent verification

Pinned StatsBomb revision: `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. Each affected row in `appearance-comparison.csv` records original document paths and SHA256 hashes, source report hash, original lineup positions, exact transition UUIDs, independently reconstructed intervals, corrected production intervals, exact rational seconds, old/new statuses and remaining issues. `input-hashes.json` binds every consumed report, fixture list, event document, lineup document and frozen package input. `4678` consumed inputs were also verified against prior audit receipts. Source hashes were rechecked after the replay; large evidence remains ignored by Git.

All **36** artifacts in the prior audit's output hash manifest remain unchanged. The prior audit reports, source receipts, diagnostics and numerical results are preserved.

`scripts/decoder_fix_independent.py` retains the prior audit's event-driven state machine, raw-field metric transcription and arithmetic as reviewable code. It imports no production participation decoder or scorer. It starts from original XI/substitution/temporary-exit/return/dismissal events, then separately reconstructs lineup geometry; tactical shifts do not create event-state entries or exits. Corrected accepted geometry is compared as exact normalized period-local interval unions, so equal totals cannot hide shifted intervals. `scripts/check_decoder_fix_geometry.py` contains that interval-union comparison and a standalone additional replay. All source schema checks still run; the main diagnostic memoizes only the pure exact timestamp parser, retaining exact parser values and all source validations.

Replay checks: `{"accepted_geometry_checks": 14536, "canonical_identity_disagreements": 0, "cross_fixture_duplicate_original_uuid": 0, "delivered_uuid_context_checks": 3036652, "delivered_uuid_context_disagreements": 0, "duplicate_original_uuid": 0, "lost_or_duplicate_published_appearances": 0, "original_events": 5436699, "previously_accepted_changed": 0, "previously_accepted_unchanged": 14445, "raw_metric_uuid_set_checks": 74895, "raw_metric_uuid_set_mismatches": 0}`. All 691 canonical ID/name pairs agree with original lineups. Each original selected numerator and press-attempt UUID set is re-extracted and compared against the sealed historical fact, including rejected appearances. UUID uniqueness and delivered UUID/team/name/competition/season/type associations are checked directly; delivered team spellings retain the existing reviewed alias policy. Event exceptions outside verified geometry are recorded separately, without adding a tolerance or calling every exception a corrupt successful numerator.

The exact historical public attribute ratings/percentiles, overall values or N/A results, and eligibility decisions reproduce independently. The approved production aggregator/scorer is also rerun, and its outputs must agree with the independent arithmetic for both old and corrected inputs. The original frozen package is reconstructed across **2514 upstream player-seasons** and must match the existing frozen reference exactly. Corrected recipients use that unchanged reference. Source positional exposure is added and dominance recomputed: comparison-group changes **0**; fine-group changes `[]`.

Finalization additionally compares the independent decisions with the existing strict eligibility implementation for **691** corrected profiles, and compares both old/new overall arithmetic with `src.provisional_ovr.formula_b` for **1382** values or N/A decisions. All agree. Exact exclusion reasons from the unchanged strict predicate are included alongside the historical public reasons. The eligibility helper's legacy module name references the earlier Formula C study; no Formula C score or normalization is calculated.

The retained independent additional checker was rerun against delivered Parquet bytes: **3,626,433 rows, zero projection/reconciliation mismatches**, plus zero independent candidate/membership disagreements across all 2,514 upstream player-seasons. Raw fixture inventory coverage is retained in `audit-output/decoder-fix-additional/additional-checks.json`. Final review categories are `{"CONFIRMED_CORRECTION": 77, "COVERAGE_LIMITATION": 227, "REMAINING_SOURCE_CONFLICT": 209, "UNCHANGED_VERIFIED_OBSERVED_SCOPE": 178}`; corrected profiles can still retain other source exclusions, listed separately.

The raw timing diagnostic has **114 rows**, compared with **107** in the prior action-chronology file. This difference is fully reconciled: the older checker explicitly excluded `Bad Behaviour`, `Substitution`, `Player Off` and `Player On` records from that file. The broader new raw scan adds **7** such administrative/disciplinary rows (six `Bad Behaviour`, one `Player On`), with **zero selected metric events**; all 107 old rows remain. Exact UUIDs and scope labels are retained in `events-outside-participation.csv` and `summary.json`. These seven rows are not additional recovered actions, newly changed observations or unexplained numerical discrepancies.

## Four unresolved appearances

| Player / fixture | Remaining original-source conflict |
| --- | --- |
| Paolo Sammarco `23349 / 3879602` | Reversed period order, clock outside supported period, overlapping active intervals and active-position snapshot disagreement. Cross-period/sequence evidence remains incomplete. |
| Giuseppe Vives `40430 / 3879772` | Original permanent-exit transition is not represented by the continuing lineup; participation continues after that exit. Independent event/lineup durations disagree. |
| Molla Wagué `3577 / 3879863` | Original permanent-exit/dismissal evidence conflicts with continuing lineup participation; unrepresented transition and participation after permanent exit remain. |
| Matthieu Saunier `13730 / 3901259` | Original permanent-exit transition conflicts with the continuing lineup; unrepresented transition and participation after permanent exit remain. Independent durations disagree. |

All four remain `CONFLICTING_EVIDENCE`, with no corrected supported minutes. Their exact event UUIDs and both assertions remain in `appearance-comparison.csv` and `summary.json`. No override or source resolution is incorporated.

## Frozen-reference diagnostic and future research snapshot

This is comparison A: corrected recipient inputs with original normalization means, sample standard deviations, exact percentile populations, memberships and Formula B. Frozen semantic fingerprint: `403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd`. Public release SHA256 remains `9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e`. Neither file was modified.

For comparison B, a full corrected research reconstruction requires a new versioned reference decision and review of all upstream candidates, complete-exposure and per-metric coverage predicates, position dominance, pending fixtures, 900-minute and 40-action thresholds, and each attribute's membership. The affected published players have **0 existing attribute-reference memberships**; this targeted replay changes **0 existing reference-member values**. Its prospective new published candidates by pool are `{"CB/interceptions": 17, "CB/press_resistance": 17, "CB/progressive_passing": 16, "CB/recoveries": 17, "CB/tackles": 17, "MID/interceptions": 12, "MID/press_resistance": 12, "MID/progressive_passing": 12, "MID/recoveries": 12, "MID/tackles": 12}`; their IDs are in `reference-assessment.json`. This assesses predicates only and does not fit a reference or calculate new population statistics. Adding reviewed candidates would require recomputing means, sample standard deviations and percentile populations, potentially changing normalized ratings and overall scores throughout the population, including currently unchanged players. A coherent new research snapshot needs a new bound version and explicit review; it is not produced here. Unpublished upstream inputs have not been fully corrected in this task, so the 28 profiles are not an estimate of all possible upstream membership changes.

## Tests and build

| Final verification | Passed | Failed | Skipped | Blocked |
| --- | ---: | ---: | ---: | ---: |
| Public backend, including 22 new regressions | 1,029 | 0 | 0 | 0 |
| Private backend, corrected modules and retained fixtures | 51 | 0 | 0 | 0 |
| Public frontend, including HTTP preview and packaging | 211 | 0 | 0 | 0 |
| Private frontend | 33 | 1 | 0 | 0 |
| Independent event/metric/arithmetic regressions | 12 | 0 | 0 | 0 |
| Identity/join probes | 12 | 0 | 0 | 0 |
| Production build | 1 | 0 | 0 | 0 |

Private backend additionally deselected 125 cases outside its declared suite; these are not skips. Its initial attempt had 34 passes and 17 fixture-root setup errors; the read-only harness fixture binding was corrected and all 51 passed. No production implementation was changed for that setup issue. The private frontend's sole failure is the previously reported badge punctuation expectation at `provisionalOvr.test.js:61`; it is separate from numerical integrity. All 68 application frontend source/script files are byte-equivalent after newline normalization to the private-suite checkout used for that run. No presentation or rating behavior was changed to satisfy it.

The first standalone alias-test iteration had 21 passes and one incorrect synthetic expectation: it assumed a terminal temporary exit with no return could be accepted. The existing sequence policy correctly withheld it. The test was corrected to require that preserved exclusion; production validation was not relaxed, and the final public suite passes all 22 new cases.

The 22 synthetic regressions cover normal labels, each alias separately and together, entry/exit-only evidence, temporary returns, halftime absence, stoppage/millisecond clocks, substitution/permanent exits, red/second-yellow dismissals, missing/ambiguous transitions, reversed/overlapping intervals, snapshot conflicts, unknown/wrong-direction labels, events inside absences and 1 ms after final whistle. The pre-existing regressions also run unchanged. The full original-source replay verifies all previously accepted appearances remain identical.

## Reproduction and review artifacts

Run in this checkout with Python 3.13, existing requirements, locked frontend dependencies and the retained source/audit workspaces. Use a fresh output directory; existing evidence is never overwritten.

```powershell
git fetch origin main
git worktree add -b participation-decoder-fix C:/Users/Ayush/Desktop/Projects/Soccer-Impact-Engine-Index-participation-decoder-fix origin/main
python -B -m scripts.verify_participation_decoder_fix --source-root ../Soccer-Impact-Engine-Index --audit-root ../Soccer-Impact-Engine-Index-player-data-integrity-audit --output audit-output/decoder-fix
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/scripts/audit_full_player_additional_checks.py --source-root ../Soccer-Impact-Engine-Index --checkout . --output audit-output/decoder-fix-additional
python -B -m scripts.run_backend_tests public -q
npm.cmd ci --offline --no-audit --no-fund --prefix frontend
npm.cmd run test:public --prefix frontend
npm.cmd run build --prefix frontend
python -B audit-output/run-private-backend.py
npm.cmd run test:private --prefix ../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/private-suite-checkout/frontend
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/test_independent_audit.py
python -B -c "import src, runpy; runpy.run_path('../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/identity_probes.py', run_name='__main__')"
python -B -m scripts.finalize_participation_decoder_fix
```

The retained `audit-output/run-private-backend.py` imports implementation modules from this correction checkout and fingerprint-verified private test/support files from the original workspace; only the test harness redirects the local-preview fixture root to the original frozen package. It uses `-B` and disables pytest cache writes. The frontend command uses existing private test sources after verifying source equality. Test/build logs, fixture setup error logs, replay logs and failed/restarted diagnostic attempts remain local. The complete run was restarted to add exact interval-union and position-dominance checks and memoize the pure timestamp parser; partial runs are not used as final findings.

Required deliverables: `appearance-comparison.csv` (95 affected rows), `player-impact.csv` (80 affected rows), `full-population-comparison.csv` (691 rows), `summary.json`, this report, regression tests and reproduction scripts. Supplemental `all-appearance-comparison.csv`, `events-outside-participation.csv`, `input-hashes.json`, `output-hashes.json`, and `test-results.json` support independent review. All numeric diagnostics and large evidence remain under ignored `audit-output`; no force-add was performed.

## Modified files

- `src/statsbomb_participation.py` and `src/independent_source_checks.py`: the exact aliases.
- `tests/test_participation_decoder_aliases.py` and `tests/suite_inventory.json`: 22 public regressions and registration.
- `scripts/decoder_fix_independent.py`: independent event/lineup reconstruction, raw metric transcription and arithmetic retained from the audit.
- `scripts/check_decoder_fix_geometry.py`: exact interval-union comparison and optional standalone replay.
- `scripts/verify_participation_decoder_fix.py`: full baseline/corrected source replay and independent input/rating comparisons.
- `scripts/finalize_participation_decoder_fix.py`: strict-policy cross-checks, scope/reference assessment, final CSV review metadata, summary and this report.
- `docs/participation-decoder-fix-report.md`: review findings and commands.

## Remaining correction batches and limits

The earlier audit's remaining source dismissal/lineup/period contradictions, source chronology and declared permanent-exit support limits, conservative identity-name admission restrictions, legacy helper reuse hazards, and missing/video-limited fixture coverage remain separate work. This decoder change does not resolve them. Same-provider event/lineup agreement is not external historical attestation, and observed supported exposure does not establish complete historical seasons. No missing game is filled with zero actions or conventional minutes. The website, ranking policy, attribute definitions, Formula B, published scores, frozen references and original source bytes remain unchanged.
