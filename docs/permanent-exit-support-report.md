# Permanent player-exit support — Batch 3A

Local implementation on branch `permanent-exit-support`, isolated worktree `C:/Users/Ayush/Desktop/Projects/Soccer-Impact-Engine-Index-permanent-exit-support`. Fetched `origin/main` and verified Batch 2B merge `b024bdb0276394bec8532ffa13105b02c4c15b0a`. No commit, push, merge, PR, deployment, published-rating edit or reference refit was made. Existing worktrees and research remain preserved.

**All three retained candidates are independently corroborated and recovered.** Added supported exposure is `16127227/60000` minutes = **268.7871166667 minutes**. Zero candidates remain excluded for participation. Player/metric exclusions and frozen membership are evaluated separately.

## Root cause and adopted semantics

The provider event is `Player Off` with `player_off.permanent=true`; the original lineup endpoint is labelled `Player Off (Permanent)`. The adapter intentionally excludes permanent records from temporary-exit matching and leaves this lineup label unknown. This was an explicit support-policy limit, not a temporary-exit decoding error.

`statsbomb_participation._source_backed_terminal_exit` binds an explicit `terminal_exit` only after independently established XI/incoming-substitution entry, exact original event and lineup endpoint agreement, stable identity/schema validation, reliable original boundaries, existing source checks, core interval validation, a separate original-event state walk, exact normalized union equality, matching position IDs and labels, and complete actor/recipient activity checks. A temporary absence must have a supported return before the terminal exit. Failed proof leaves original unknown observations, geometry, issues and raw evidence intact. No clipping, timestamp tolerance, inferred entry or player-specific production rule is used.

A terminal exit cannot resume. Later returns, substitutions, dismissals, active snapshots or player/recipient activity block corroboration. Equal-clock activity needs source indices proving it precedes the exit. Conflicting terminal transitions at the same clock are withheld even when indexed; an index does not resolve incompatible terminal assertions. Bad Behaviour after this terminal category is conservatively withheld, including an apparent bench card: the existing independently proved post-substitution/unused-roster exception is not expanded. This leaves dismissal and Batch 2A policy unchanged.

`participation_intervals.EXITS` includes `terminal_exit`, and its sequence validator rejects a following stint. `AdaptedPlayer.reconstructed_exits` contains an immutable `ReconstructedExit` with original UUID and entry/snapshot/lineup/boundary references. `source_reconstruction.appearance_rows` preserves that provenance. Original labels, UUIDs, IDs, exact clocks, positions, lineup bytes and source hashes survive. The exit cannot create an appearance by itself.

`independent_source_checks.endpoint` separately resolves the explicit permanent lineup endpoint only against a true original permanent event. Temporary endpoints continue to reject permanent events. Its raw geometry calculation never admits an appearance; `check_match` compares source geometry and metric sets with the ledger. All three real cases also pass this independent metric path.

## Candidates, source identity and exact geometry

| Player / fixture / team | Original entry UUID | Permanent-exit UUID | Period / exact timestamp | Added seconds | Added minutes |
| --- | --- | --- | --- | ---: | ---: |
| Fernando Francisco Reges (16003) / 3754135 / 36 | `59751881-318b-408f-bc3d-6acc00f52f76` | `f70b3889-61e5-4865-b88d-5b9ca42a95ac` | 2 / 00:27:41.371 | `4572999/1000` | 76.2166500000 |
| José María Giménez de Vargas (5259) / 3825907 / 212 | `c8705881-5855-4f0c-94a6-900c1c5fcefd` | `5d554229-ddef-48db-870c-f83f3611c7d6` | 2 / 00:41:36.449 | `5257361/1000` | 87.6226833333 |
| Nicolas Pallois (3256) / 3829452 / 146 | `d323743d-c7ce-4fb9-baf7-0c5c0cb2dac2` | `5e750259-63ea-4930-8553-44884cd0c9d0` | 2 / 00:50:54.781 | `6296867/1000` | 104.9477833333 |

The prior appearance exposure was unsupported (`null`), not a claimed zero-minute appearance. The reported additions are exposure newly included in the diagnostic aggregates. Both independent methods reconstruct original supported intervals directly; neither calls the production decoder. Original state transitions and lineup geometry are retained separately, with exact normalized union comparison rather than minutes alone.

### Fernando Francisco Reges — 16003/3754135

Original entry: period 1 `00:00:00.000`, source index 2. Terminal index: 2786.
Event intervals: `[[[1, "0"], [2, "1661371/1000"]]]`.
Original lineup intervals: `[[[1, "0"], [2, "1661371/1000"]]]`.
Unsupported baseline observations: `[{"observation_id": "3754135:36:16003:0", "context": {"match_id": 3754135, "player_id": 16003, "team_key": "Manchester City"}, "position": "Right Defensive Midfield", "start": {"period": 1, "seconds": "0.000", "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/events/3754135.json#/event/59751881-318b-408f-bc3d-6acc00f52f76"]}, "end": {"period": 2, "seconds": 1661, "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3754135.json#/team/36/player/16003/positions/0"]}, "entry_kind": "starter", "exit_kind": "unknown", "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3754135.json#/team/36/player/16003/positions/0"], "provenance_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/matches/2/27.json@pinned-original#sha256=e07d6d360b30e0cd17f9aeea0db1502d2a5666d298f1b44b83a2d2f21ba3d21b", "https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3754135.json@pinned-original#sha256=ea7eca3d75a4f151845d32dcd1233f598287671e6e6b0d459b45b6da3ae7d5db", "https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/events/3754135.json@pinned-original#sha256=cdd0ea81c1173630242eb89eb42e4b4473f9b77d1944cd689717d3059eace2f4"]}]`.
Original boundaries: `{"1": ["0", "727907/250"], "2": ["0", "2887221/1000"]}`.
Prior rejection: `[{"status": "INCOMPLETE_EVIDENCE", "code": "sequence_evidence_incomplete", "observation_ids": []}, {"status": "INCOMPLETE_EVIDENCE", "code": "unknown_transition", "observation_ids": ["3754135:36:16003:0"]}]`. Corrected classification: `STRUCTURALLY_VALID`.
Original positions: `[{"position_id": 9, "position": "Right Defensive Midfield", "from": "00:00", "to": "72:41", "from_period": 1, "to_period": 2, "start_reason": "Starting XI", "end_reason": "Player Off (Permanent)"}]`.

| Source document | SHA256 |
| --- | --- |
| Fixture | `e07d6d360b30e0cd17f9aeea0db1502d2a5666d298f1b44b83a2d2f21ba3d21b` |
| Lineup | `ea7eca3d75a4f151845d32dcd1233f598287671e6e6b0d459b45b6da3ae7d5db` |
| Events | `cdd0ea81c1173630242eb89eb42e4b4473f9b77d1944cd689717d3059eace2f4` |

### José María Giménez de Vargas — 5259/3825907

Original entry: period 1 `00:00:00.000`, source index 2. Terminal index: 3397.
Event intervals: `[[[1, "0"], [2, "2496449/1000"]]]`.
Original lineup intervals: `[[[1, "0"], [2, "2492847/1000"]], [[2, "2492847/1000"], [2, "2496449/1000"]]]`.
Unsupported baseline observations: `[{"observation_id": "3825907:212:5259:0", "context": {"match_id": 3825907, "player_id": 5259, "team_key": "Atl\u00e9tico Madrid"}, "position": "Right Center Back", "start": {"period": 1, "seconds": "0.000", "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/events/3825907.json#/event/c8705881-5855-4f0c-94a6-900c1c5fcefd"]}, "end": {"period": 2, "seconds": "2492.847", "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/events/3825907.json#/event/37d03738-5af4-43c4-b4e8-ef95143a2000"]}, "entry_kind": "starter", "exit_kind": "position_change", "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3825907.json#/team/212/player/5259/positions/0"], "provenance_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/matches/11/27.json@pinned-original#sha256=4e2074c633559f3b88e9593a752d8d15d9d9ba0d6c8a25316a68ec6526b4d14b", "https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3825907.json@pinned-original#sha256=1748aaa8d9c08c1e258bb2f12906b3b79346cb22694518e701daf29d844c1906", "https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/events/3825907.json@pinned-original#sha256=7ec889beeefc2e6cfd152ef55bf59d95ed97cc5ea5cc5d6192c58fa204c53462"]}, {"observation_id": "3825907:212:5259:1", "context": {"match_id": 3825907, "player_id": 5259, "team_key": "Atl\u00e9tico Madrid"}, "position": "Right Center Forward", "start": {"period": 2, "seconds": "2492.847", "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/events/3825907.json#/event/37d03738-5af4-43c4-b4e8-ef95143a2000"]}, "end": {"period": 2, "seconds": 2496, "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3825907.json#/team/212/player/5259/positions/1"]}, "entry_kind": "position_change", "exit_kind": "unknown", "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3825907.json#/team/212/player/5259/positions/1"], "provenance_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/matches/11/27.json@pinned-original#sha256=4e2074c633559f3b88e9593a752d8d15d9d9ba0d6c8a25316a68ec6526b4d14b", "https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3825907.json@pinned-original#sha256=1748aaa8d9c08c1e258bb2f12906b3b79346cb22694518e701daf29d844c1906", "https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/events/3825907.json@pinned-original#sha256=7ec889beeefc2e6cfd152ef55bf59d95ed97cc5ea5cc5d6192c58fa204c53462"]}]`.
Original boundaries: `{"1": ["0", "345114/125"], "2": ["0", "1454773/500"]}`.
Prior rejection: `[{"status": "INCOMPLETE_EVIDENCE", "code": "sequence_evidence_incomplete", "observation_ids": []}, {"status": "INCOMPLETE_EVIDENCE", "code": "unknown_transition", "observation_ids": ["3825907:212:5259:1"]}]`. Corrected classification: `STRUCTURALLY_VALID`.
Original positions: `[{"position_id": 3, "position": "Right Center Back", "from": "00:00", "to": "86:32", "from_period": 1, "to_period": 2, "start_reason": "Starting XI", "end_reason": "Tactical Shift"}, {"position_id": 22, "position": "Right Center Forward", "from": "86:32", "to": "86:36", "from_period": 2, "to_period": 2, "start_reason": "Tactical Shift", "end_reason": "Player Off (Permanent)"}]`.

| Source document | SHA256 |
| --- | --- |
| Fixture | `4e2074c633559f3b88e9593a752d8d15d9d9ba0d6c8a25316a68ec6526b4d14b` |
| Lineup | `1748aaa8d9c08c1e258bb2f12906b3b79346cb22694518e701daf29d844c1906` |
| Events | `7ec889beeefc2e6cfd152ef55bf59d95ed97cc5ea5cc5d6192c58fa204c53462` |

### Nicolas Pallois — 3256/3829452

Original entry: period 1 `00:00:00.000`, source index 1. Terminal index: 3387.
Event intervals: `[[[1, "0"], [2, "3054781/1000"]]]`.
Original lineup intervals: `[[[1, "0"], [2, "3054781/1000"]]]`.
Unsupported baseline observations: `[{"observation_id": "3829452:146:3256:0", "context": {"match_id": 3829452, "player_id": 3256, "team_key": "Bordeaux"}, "position": "Left Center Back", "start": {"period": 1, "seconds": "0.000", "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/events/3829452.json#/event/d323743d-c7ce-4fb9-baf7-0c5c0cb2dac2"]}, "end": {"period": 2, "seconds": 3054, "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3829452.json#/team/146/player/3256/positions/0"]}, "entry_kind": "starter", "exit_kind": "unknown", "evidence_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3829452.json#/team/146/player/3256/positions/0"], "provenance_refs": ["https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/matches/7/27.json@pinned-original#sha256=733c7cf47bd7a19d9acae5add722c32b404664d949377057a280bd0b0f0d2464", "https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/lineups/3829452.json@pinned-original#sha256=84ca195a670454253302540f1a02086f70af3324e3d2e02e8a6404538533b0be", "https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/data/events/3829452.json@pinned-original#sha256=57dbeefe5b833f15c70c3ac37c7219a9d1e1d48d7b2f92b3c78cf9d31b6c611a"]}]`.
Original boundaries: `{"1": ["0", "1621043/500"], "2": ["0", "3090963/1000"]}`.
Prior rejection: `[{"status": "INCOMPLETE_EVIDENCE", "code": "sequence_evidence_incomplete", "observation_ids": []}, {"status": "INCOMPLETE_EVIDENCE", "code": "unknown_transition", "observation_ids": ["3829452:146:3256:0"]}]`. Corrected classification: `STRUCTURALLY_VALID`.
Original positions: `[{"position_id": 5, "position": "Left Center Back", "from": "00:00", "to": "95:54", "from_period": 1, "to_period": 2, "start_reason": "Starting XI", "end_reason": "Player Off (Permanent)"}]`.

| Source document | SHA256 |
| --- | --- |
| Fixture | `733c7cf47bd7a19d9acae5add722c32b404664d949377057a280bd0b0f0d2464` |
| Lineup | `84ca195a670454253302540f1a02086f70af3324e3d2e02e8a6404538533b0be` |
| Events | `57dbeefe5b833f15c70c3ac37c7219a9d1e1d48d7b2f92b3c78cf9d31b6c611a` |

## Frozen-reference numerical impact

A = published V1; B = Batch 1; C = Batch 2A; D = Batch 2B; E = terminal-exit support. All 691 profiles are calculated in all five stages. Original inputs reproduce every published rating/percentile, Formula B value or N/A and eligibility result; B/C/D reproduce retained diagnostics. Production aggregation agrees with separately transcribed raw-UUID/rational arithmetic for 17,275 attribute and 3,455 Formula B/eligibility comparisons. Press resistance remains an action ratio.

| Player | D supported minutes | E supported minutes | D Formula B | E Formula B | Delta | Eligibility changed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Nicolas Pallois (3256) | 1355.0337500000 | 1459.9815333333 | 75.5015618859021 | 75.61485549756146 | 0.11329361165935836 | False |
| José María Giménez de Vargas (5259) | 2436.3726833333 | 2523.9953666667 | 64.67022795702388 | 64.6016069857531 | -0.06862097127078925 | False |
| Fernando Francisco Reges (16003) | 1637.8147500000 | 1714.0314000000 | 71.15156958233857 | 71.34014002681702 | 0.18857044447845794 | False |

| Player | Attribute | Numerator / attempts D → E | Supported minutes D → E | Exact value D → E | Rating D → E | Percentile D → E |
| --- | --- | --- | --- | --- | --- | --- |
| 3256 | tackles | 17 → 19 | 1355.0337500000 → 1459.9815333333 | `1224000/1084027` → `1350000/1152617` | 70.01152689080719 → 71.21580637391178 | 69.72477064220183 → 71.55963302752293 |
| 3256 | interceptions | 15 → 15 | 1355.0337500000 → 1459.9815333333 | `1080000/1084027` → `20250000/21899723` | 69.72272854768924 → 67.57298880731234 | 68.80733944954129 → 60.55045871559633 |
| 3256 | recoveries | 79 → 87 | 1355.0337500000 → 1459.9815333333 | `5688000/1084027` → `117450000/21899723` | 84.45308108577532 → 85.63836409746654 | 96.29629629629629 → 97.22222222222223 |
| 3256 | press_resistance | 58/94 → 58/94 | 1355.0337500000 → 1459.9815333333 | `2900/47` → `2900/47` | 61.54165761704783 → 61.54165761704783 | 33.333333333333336 → 33.333333333333336 |
| 3256 | progressive_passing | 68 → 72 | 1355.0337500000 → 1459.9815333333 | `4896000/1084027` → `97200000/21899723` | 78.20302855259958 → 77.56028364295004 | 88.07339449541284 → 87.1559633027523 |
| 5259 | tackles | 34 → 34 | 2436.3726833333 → 2523.9953666667 | `183600000/146182361` → `91800000/75719861` | 73.63776615025131 → 72.39124978027398 | 82.56880733944953 → 76.14678899082568 |
| 5259 | interceptions | 19 → 20 | 2436.3726833333 → 2523.9953666667 | `102600000/146182361` → `54000000/75719861` | 60.8848770139127 → 61.22383506944959 | 40.36697247706422 → 40.36697247706422 |
| 5259 | recoveries | 75 → 79 | 2436.3726833333 → 2523.9953666667 | `405000000/146182361` → `213300000/75719861` | 59.14297681033496 → 59.617686642718404 | 30.555555555555557 → 32.407407407407405 |
| 5259 | press_resistance | 67/118 → 67/118 | 2436.3726833333 → 2523.9953666667 | `3350/59` → `3350/59` | 54.96854863468294 → 54.96854863468294 | 14.814814814814815 → 14.814814814814815 |
| 5259 | progressive_passing | 76 → 81 | 2436.3726833333 → 2523.9953666667 | `410400000/146182361` → `218700000/75719861` | 64.13448529658967 → 64.79982871161972 | 52.293577981651374 → 54.12844036697248 |
| 16003 | tackles | 39 → 43 | 1637.8147500000 → 1714.0314000000 | `360000/167981` → `6450000/2856719` | 74.29905396756953 → 76.22756228228154 | 83.2 → 84.0 |
| 16003 | interceptions | 27 → 28 | 1637.8147500000 → 1714.0314000000 | `3240000/2183753` → `4200000/2856719` | 77.26335179063209 → 76.96834978235367 | 86.4 → 85.6 |
| 16003 | recoveries | 88 → 90 | 1637.8147500000 → 1714.0314000000 | `960000/198523` → `13500000/2856719` | 60.91319975198609 → 59.8990142692511 | 35.483870967741936 → 32.25806451612903 |
| 16003 | press_resistance | 113/141 → 113/141 | 1637.8147500000 → 1714.0314000000 | `11300/141` → `11300/141` | 76.28657530428022 → 76.28657530428022 | 90.4 → 90.4 |
| 16003 | progressive_passing | 18 → 20 | 1637.8147500000 → 1714.0314000000 | `2160000/2183753` → `3000000/2856719` | 49.04129462767069 → 49.47626669196893 | 0.0 → 0.0 |

Ranking eligibility changes: **0**. No leaderboard promotion is performed. No reference population is refitted. Remaining E exclusions:

- Nicolas Pallois (3256): `["tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER"]`.
- José María Giménez de Vargas (5259): `["tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER"]`.
- Fernando Francisco Reges (16003): `["INCOMPLETE_OBSERVED_EXPOSURE", "tackles:NOT_NORMAL_REFERENCE_CANDIDATE", "tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "tackles:INCOMPLETE_METRIC_SCOPE", "tackles:FIXTURE_SCOPE_NOT_FULLY_ALIGNED", "interceptions:NOT_NORMAL_REFERENCE_CANDIDATE", "interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "interceptions:INCOMPLETE_METRIC_SCOPE", "interceptions:FIXTURE_SCOPE_NOT_FULLY_ALIGNED", "recoveries:NOT_NORMAL_REFERENCE_CANDIDATE", "recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "recoveries:INCOMPLETE_METRIC_SCOPE", "recoveries:FIXTURE_SCOPE_NOT_FULLY_ALIGNED", "press_resistance:NOT_NORMAL_REFERENCE_CANDIDATE", "press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "progressive_passing:NOT_NORMAL_REFERENCE_CANDIDATE", "progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER", "progressive_passing:INCOMPLETE_METRIC_SCOPE", "progressive_passing:FIXTURE_SCOPE_NOT_FULLY_ALIGNED"]`.

Per-appearance raw numerator/attempt UUIDs, admission predicates and aligned exact exposure are in `appearance-comparison.csv`. Aggregate supported match IDs, denominators, values, percentiles, ratings and remaining exclusions are retained for all stages in `player-impact.csv` and `full-population-comparison.csv`. Missing evidence is never filled with zero activity.

## Complete-population preservation and remaining conflicts

The replay reopens all **1,551 fixtures / 5,436,699 original events**, verifies byte hashes and checks every source roster actor against the actual merged-baseline adapter. All **14,547 accepted Batch 2B intervals** are identical; **14,550** are supported afterward. All **91 Batch 1 recoveries**, Pallois’s Batch 2A recovery, Juanfran’s removed phantom, **ten published and 26 nonpublished Batch 2B recoveries** remain intact. All 14,979 historical keys are accounted for, with 14,978 current active contributions and no new or lost legitimate appearance. Other published profiles unchanged from D: **688**.

Every permanent source record was inventoried: **17**. Additional nonpublished terminal recoveries: **9**. These initially unanticipated effects of the general rule are individually investigated and independently corroborated. See `terminal-source-inventory.csv`; source-only actors remain separate from recipient scores. Unexplained full-population changes: **0**.

Raw UUID sets remain conserved in 74,895 metric/appearance comparisons and 3,036,652 delivered contexts. A separate original-byte UUID database is reused only after validating its independent fingerprint and every source receipt against the fresh replay. Bidirectional disk-backed set comparison finds zero missing, extra or duplicate UUIDs. Independent Parquet checks cover 3,626,433 projections with zero mismatches and all 2,514 frozen-candidate predicates with zero discrepancies.

Ramos `5201/267533` and `5201/3825879`, Francis `3608/3754058`, Mendy `4506/3829490`, Pajot `3414/3829490`, and Batch 1 residuals `23349/3879602`, `40430/3879772`, `3577/3879863`, `13730/3901259` retain identical rejection decisions and issue arrays. All other previously unresolved appearances remain unchanged except the three candidates. **428 active appearances** remain unresolved/unsupported across source conflicts, coverage and existing policies; these are not 428 newly diagnosed bugs. `unresolved-conflicts.csv` retains exact issues. Name-admission, pending-fixture, progressive-pass geometry and metric-scope restrictions remain unchanged.

Published ratings SHA256: `9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e`. Frozen semantic fingerprint: `403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd`. Prior artifact hashes and consumed source receipts are rechecked unchanged. This is retained same-provider corroboration, not external historical attestation or a complete-season certification.

## Verification

| Check | Passed | Failed | Skipped | Blocked | Deselected |
| --- | ---: | ---: | ---: | ---: | ---: |
| targeted-regressions | 173 | 0 | 0 | 0 | 0 |
| original-source-regressions | 16 | 0 | 0 | 0 | 0 |
| public-backend | 1137 | 0 | 0 | 0 | 0 |
| private-backend | 51 | 0 | 0 | 0 | 125 |
| independent-regressions | 12 | 0 | 0 | 0 | 0 |
| identity-probes | 12 | 0 | 0 | 0 | 0 |
| public-frontend | 211 | 0 | 0 | 0 | 0 |
| private-frontend | 33 | 1 | 0 | 0 | 0 |
| production-build | 1 | 0 | 0 | 0 | 0 |
| independent-candidate-checks | 3 | 0 | 0 | 0 | 0 |
| full-population-replay | 1 | 0 | 0 | 0 | 0 |
| uuid-conservation | 1 | 0 | 0 | 0 | 0 |
| raw-delivery-reference-checks | 1 | 0 | 0 | 0 | 0 |
| nonpublished-independent-checks | 9 | 0 | 0 | 0 | 0 |

The private frontend failure is the existing badge-label typography expectation at `provisionalOvr.test.js:61` (case begins at line 44); unrelated UI and ratings are unchanged. Targeted cases overlap public backend totals; real-candidate subcases are not counted as additional top-level unit tests. Deselections are outside the declared private suite, not skipped verification.

Earlier attempts remain in ignored evidence: a synthetic fixture duplicate UUID was corrected; the first replay compared equal dataclass values across separately loaded module classes and was corrected to structural comparison; initial private provisioning followed a retained data junction, was stopped, and its task-owned accidental copy was removed. The first expanded source-test attempt passed bench roster rows to a checker requiring active appearances, producing three subcase errors; the corrected active-row call passes. Original data and prior checkouts were not modified. The current harness copies only test/application files and uses junctions for source data and locked dependencies. Only completed logs/replay support this report.

Reproduction from the isolated worktree (Python 3.13, retained sibling evidence, locked Node dependencies):

```powershell
python -B -m scripts.check_permanent_exit_sources
python -B -m scripts.run_permanent_exit_checks
python -B -m scripts.verify_permanent_exit_support
python -B -m scripts.check_permanent_exit_uuid_conservation
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/scripts/audit_full_player_additional_checks.py --source-root ../Soccer-Impact-Engine-Index --checkout . --output audit-output/permanent-additional
python -B -m scripts.finalize_permanent_exit_support
```

Use a fresh output directory/worktree or preserve completed output before rerunning; evidence-producing commands refuse completed replay/log outputs. Exact executed suite commands, return codes and log paths are in `test-results.json`. Private harness fixtures and dependency locks are fingerprinted in `audit-output/private-harness-input-hashes.json`.

## Modified files and artifacts

- `docs/permanent-exit-support-report.md`
- `scripts/check_off_field_card_sources.py`
- `scripts/check_permanent_exit_sources.py`
- `scripts/check_permanent_exit_uuid_conservation.py`
- `scripts/finalize_permanent_exit_support.py`
- `scripts/run_permanent_exit_checks.py`
- `scripts/verify_permanent_exit_support.py`
- `src/independent_source_checks.py`
- `src/participation_intervals.py`
- `src/source_reconstruction.py`
- `src/statsbomb_participation.py`
- `tests/suite_inventory.json`
- `tests/test_permanent_exits.py`

Required ignored outputs are under `audit-output/permanent-exit-support/`: `candidate-appearances.csv`, `appearance-comparison.csv`, `player-impact.csv`, `full-population-comparison.csv`, `permanent-exit-evidence.csv`, `unresolved-conflicts.csv`, `summary.json`, `input-hashes.json`, `test-results.json`, `artifact-inventory.json`. Supplemental evidence includes the complete historical ledger, all-source permanent inventory, diagnostic facts, merged adapter snapshot and disk-backed UUID inventory/comparison. Independent source evidence, private harness receipts, suite logs, raw/reference checks and failed-attempt logs remain under `audit-output/`. Large private outputs stay ignored.

No implementation blocker remains for this verified local scope. The known frontend expectation remains a separate test/UI-contract task. Next recommended phase: review the local correction and diagnostic results; investigate the documented exact event-chronology exceptions separately. Any publication, new reference population or versioned ratings release requires explicit approval.

## Nonpublished terminal exits

Each source-only recovery is independently checked again from byte-bound originals. These actors receive no published score, reference admission or ranking promotion.

| Actor / fixture / team | Exact seconds | Added minutes | Exit UUID |
| --- | ---: | ---: | --- |
| Kevin Gameiro (6401) / 3825646 / 213 | `880687/200` | 73.3905833333 | `fa2ab118-0f85-4343-913f-3626bcfa86c5` |
| Daniele Bonera (6827) / 3825667 / 222 | `2005631/1000` | 33.4271833333 | `18dfca94-492d-43fa-9b06-c33f68234db3` |
| Diego Mainz García (26781) / 3825740 / 1049 | `688989/125` | 91.8652000000 | `7e62d46e-7537-4473-8a41-3f49e5df3d48` |
| Jozabed Sánchez Ruiz (6852) / 3825781 / 360 | `5567643/1000` | 92.7940500000 | `29cfcc24-5dd9-40e2-8338-699f0a9e663e` |
| Carlos Arturo Bacca Ahumada (5688) / 3878602 / 243 | `5872087/1000` | 97.8681166667 | `71ca6865-9dbf-42b5-af73-08f9c4160019` |
| Duván Esteban Zapata Banguera (7017) / 3879552 / 230 | `1034651/200` | 86.2209166667 | `36abf001-4ab6-48f2-9da6-6d9fac03f96e` |
| Ismaël Tiémoko Diomandé (3797) / 3900620 / 140 | `1406009/250` | 93.7339333333 | `6f2926a1-5226-4346-8676-a189d6ad49cc` |
| Carlos Eduardo de Castro Lourenço (401472) / 3901226 / 133 | `5508611/1000` | 91.8101833333 | `4d944537-9694-4c2f-9b29-544a35c441c8` |
| Zlatan Ibrahimović (3672) / 3901261 / 131 | `686544/125` | 91.5392000000 | `2f495b65-2118-402c-8500-69de0bbefbf2` |

## Permanent-event records still withheld

Five of the 17 source permanent-event records remain withheld. No source record is accepted solely because its event has a permanent flag.

| Actor / fixture | Preserved rejection reasons |
| --- | --- |
| Alessio Cerci (7702) / 3879796 | active_position_snapshot_disagreement, participation_after_permanent_exit, reversed_within_period_clock, sequence_evidence_incomplete, unknown_transition; original lineup final endpoint is Final Whistle, not a permanent exit |
| Robert Berič (4601) / 3900509 | sequence_evidence_incomplete, unknown_transition; original lineup final endpoint is Player Off (Off Camera), not a permanent exit |
| Anthony Weber (7435) / 3900512 | participation_after_permanent_exit, sequence_evidence_incomplete, unknown_transition; original lineup final endpoint is Final Whistle, not a permanent exit |
| Florent Balmont (3211) / 3901151 | participation_after_permanent_exit, sequence_evidence_incomplete, unknown_transition; original lineup final endpoint is Final Whistle, not a permanent exit |
| Sofiane Boufal (3625) / 3901155 | participation_after_permanent_exit, sequence_evidence_incomplete, unknown_transition; original lineup final endpoint is Final Whistle, not a permanent exit |

Robert Berič `4601/3900509` illustrates the semantic restriction: the raw permanent event ends at period 2 `00:38:11.472`, but the lineup calls that endpoint `Player Off (Off Camera)`. Even agreeing event/lineup geometry does not authorize relabelling a temporary source assertion as permanent. The original labels, event and unsupported decision are preserved.
