# D2A: provisional real-player metrics audit

Review date: October 26, 2026. **PROVISIONAL OBSERVED METRICS work for both
bounded prefixes.** This is an in-memory development diagnostic, not a production
scorecard or full-season reconstruction. No roles, eligibility thresholds,
percentiles, rankings, tiers, weights or ratings are applied.

## A. Inputs and repeatable sample selection

All requested inputs were available and read-only, with no path substitution:

| Input | Rows | Use |
|---|---:|---|
| `data/processed/player_name_crosswalk.parquet` | 5,578 | Caller-supplied provisional spelling/context lookup |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | 5,576 | Same explicit population as D1B-P; exposure availability only |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | 5,576 | Canonical context/minute-value consistency comparison |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | 7,680 | Category and canonical-key coverage comparison |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | 3,626,433 | First 4,096 and first 65,536 events, in stored order |

`scripts/audit_provisional_metrics.py` reads projected PyArrow batches and retains
only the requested prefix, the small lookup and population tables. Event columns,
in order: `id`, `match_id`, `player`, `team`, `competition_name`, `season_name`,
`type`, `location`, `duel_type`, `duel_outcome`, `interception_outcome`,
`ball_recovery_recovery_failure`, `under_pressure`, `pass_outcome`, `dribble_outcome`.
No full event scan was performed. Prefixes are nested, not disjoint samples.

Run from the repository root:

```sh
python -B -W error -m scripts.audit_provisional_metrics --events data/validation/drive-raw-review/statsbomb_team_events.parquet --crosswalk data/processed/player_name_crosswalk.parquet --minutes data/validation/arpit-2026-10-21/player_minutes.parquet --delivered-recovery data/validation/arpit-refresh-review/recovery_per90.parquet --comparison-minutes data/validation/arpit-refresh-review/player_minutes.parquet --limit 4096
```

Repeat with `--limit 65536`. The script prints identity/lookup summaries, exclusion
and conservation accounting, all observed player-context counts/percentages and
by-zone counts. Player tables use canonical grouping order, not metric ranking.
It writes no files, performs no ingestion/network requests and produces no
production JSON. Missing supplied paths fail explicitly.

## B. Identity resolution with the metric projection

**VERIFIED STRUCTURAL CHECKS:** reuse D1B-P's `audit_provisional`, including exact
ID validation, existing name/team normalization, duplicate counting, conflict
quarantine and M2A `resolve_events(strict=False)`. All 5,576 October 21 contexts
are retained without role or minute filtering. The provisional lookup contains
5,578 normalized keys, zero identical duplicates and zero conflicting keys.

| Diagnostic | 4,096 prefix | 65,536 prefix |
|---|---:|---:|
| Input rows / unique event IDs | 4,096 / 4,096 | 65,536 / 65,536 |
| Matched IDs / selected events | 4,096 / 4,096 | 65,536 / 65,536 |
| Known outside / unresolved | 0 / 0 | 0 / 0 |
| Match percentage | 100% | 100% |
| Observed matches / player contexts | 2 / 51 | 29 / 346 |
| Conflicting-key-affected events | 0 | 0 |
| Missing actor names / invalid identity fields | 0 / 0 | 0 / 0 |
| Duplicate joins | 0 | 0 |

Both samples are entirely event-labeled **1. Bundesliga / 2023/2024**. Original
event IDs, order, match IDs and canonical context survive identity attachment.
No unknown actor is converted to a known outsider or a zero metric. Any unresolved
input, including a nonmetric event, blocks player metrics while retaining
unmatched keys and recovery/press accounting in the diagnostic error.

## C. Recovery event counts and coverage

**PROVISIONAL OBSERVED METRICS:** use unchanged `inspect_recovery` and
`recovery_counts(..., group_cols=PLAYER_KEYS)`. This preserves successful Tackle
and Interception outcomes (`Won`, `Success In Play`, `Success Out`) and Ball
Recovery unless its failure flag equals true. The existing wrapper's nullable
failure-flag storage adaptation is retained; missing flags count as non-failed.

| Category | 4,096 count | Observed contexts | 65,536 count | Observed contexts |
|---|---:|---:|---:|---:|
| Tackle | 22 | 15 | 604 | 196 |
| Interception | 9 | 7 | 368 | 151 |
| Ball Recovery | 94 | 27 | 2,442 | 287 |

The recovery family has observations for **30** and **307** distinct player
contexts respectively (49 and 634 context/category rows). Category counts sum to
125 and 3,414 qualifying events for conservation only; no combined defensive
score is created. Missing player/category rows remain absent, not zero-filled.

## D. Pressured attempts, completions and percentages

Reuse unchanged `inspect_press_resistance`, `aggregate_actions` and
`add_completion_rates`. Pressure must equal true. All pass types are included;
null pass outcome completes. Dribble completion requires exact `Complete`;
missing dribble outcome is unsuccessful. Missing pressure excludes the action.

| Metric | 4,096 prefix | 65,536 prefix |
|---|---:|---:|
| Pass completed / attempts | 238 / 308 | 3,776 / 4,863 |
| Pass completion rate | 77.272727% | 77.647543% |
| Dribble completed / attempts | 13 / 29 | 402 / 756 |
| Dribble completion rate | 44.827586% | 53.174603% |
| Combined successful / attempts | 251 / 337 | 4,178 / 5,619 |
| Combined press-resistance rate | 74.480712% | 74.354867% |
| Observed press player contexts | 47 | 318 |

Aggregate percentages above pool attempts/completions; they are not averages of
player percentages or pass/dribble rates. Each player's zero-attempt component
percentage remains N/A, not zero. Raw attempts/completions remain integer counts.

## E. Actual player-context examples

All examples share 1. Bundesliga / 2023/2024. Names are observed event labels;
IDs come from the provisional delivered lookup. These are illustrative contexts,
not a ranked selection. `Absent` means no observed category row, not a certified
zero or missing-data imputation.

| Prefix | ID / event name | Team | Tackle | Interception | Ball Recovery |
|---|---|---|---:|---:|---:|
| 4,096 | 3117 / Lucas Tousart | Union Berlin | 1 | 3 | 5 |
| 4,096 | 3500 / Granit Xhaka | Bayer Leverkusen | Absent | 1 | 5 |
| 4,096 | 8221 / Jonathan Tah | Bayer Leverkusen | Absent | Absent | 3 |
| 65,536 | 3117 / Lucas Tousart | Union Berlin | 1 | 3 | 5 |
| 65,536 | 3500 / Granit Xhaka | Bayer Leverkusen | 17 | 11 | 158 |
| 65,536 | 8221 / Jonathan Tah | Bayer Leverkusen | 10 | 14 | 87 |

| Prefix / player ID | Pass completed / attempts | Pass % | Dribble completed / attempts | Dribble % | Combined % |
|---|---:|---:|---:|---:|---:|
| 4,096 / 3117 | 4 / 5 | 80 | 2 / 3 | 66.666667 | 75 |
| 4,096 / 3500 | 7 / 9 | 77.777778 | 1 / 1 | 100 | 80 |
| 4,096 / 8221 | 6 / 7 | 85.714286 | 0 / 0 | N/A | 85.714286 |
| 65,536 / 3117 | 4 / 5 | 80 | 2 / 3 | 66.666667 | 75 |
| 65,536 / 3500 | 396 / 446 | 88.789238 | 9 / 18 | 50 | 87.284483 |
| 65,536 / 8221 | 165 / 191 | 86.387435 | 4 / 7 | 57.142857 | 85.353535 |

## F. Zone accounting

Existing 120-by-80 pitch and 3-by-3 zones are unchanged: x boundaries 40/80 and y
boundaries 80/3 and 160/3; zone is `1 + x_band + 3*y_band`. Missing/off-pitch
locations stay in recovery totals but not zone counts. In both real prefixes,
all qualifying selected locations have valid zones: **0 unknown-zone events**.

| Zone | 4,096 qualifying recovery events | 65,536 qualifying recovery events |
|---|---:|---:|
| 1 | 19 | 434 |
| 2 | 12 | 410 |
| 3 | 8 | 226 |
| 4 | 21 | 567 |
| 5 | 6 | 349 |
| 6 | 9 | 274 |
| 7 | 21 | 413 |
| 8 | 19 | 482 |
| 9 | 10 | 259 |

Per-category zoned sums equal 22/9/94 and 604/368/2,442 respectively. The script
also prints player/context/category/zone tables. No zone per90 is computed.

## G. Unresolved and excluded event accounting

| Event type | 4,096 input | Recovery qualifies | Press qualifies | 65,536 input | Recovery qualifies | Press qualifies |
|---|---:|---:|---:|---:|---:|---:|
| Ball Recovery | 101 | 94 | 0 | 2,640 | 2,442 | 0 |
| Duel | 76 | 22 | 0 | 1,704 | 604 | 0 |
| Interception | 20 | 9 | 0 | 584 | 368 | 0 |
| Pass | 2,156 | 0 | 308 | 33,303 | 0 | 4,863 |
| Dribble | 29 | 0 | 29 | 756 | 0 | 756 |
| Carry | 1,714 | 0 | 0 | 26,549 | 0 | 0 |

Recovery excludes 3,971 / 62,122 input events: other types, nonqualifying Duel or
Interception outcomes, and failed recoveries under existing definitions. Press
excludes 3,759 / 59,917 events: other types and Pass/Dribble without true pressure.
Neither metric qualifies 3,634 / 56,503 events. Metric exclusions are not identity
failures or missing player scores. All filtered actions are selected; outside and
unresolved counts, including press completions, are zero in both samples.

## H. Count and cardinality conservation

**VERIFIED STRUCTURAL CHECKS:** unique IDs are checked over each complete bounded
prefix, including row-group boundaries and events later excluded by metrics.
Identity partitions sum to the input size; every original event survives once
in order. Recovery extracted = selected + outside + unresolved by category;
aggregated counts = qualifying selected events. Zoned + unknown = total selected
recovery events. Press attempts and completions conserve separately by action
type and identity status; player sums match selected filtered actions. Aggregated
canonical keys are unique; percentages are within 0–100 or N/A.

Full-input disjoint accounting: **125 + 337 + 3,634 = 4,096** and
**3,414 + 5,619 + 56,503 = 65,536**. No absent player/action grid is manufactured.

## I. Delivered recovery comparison

The refreshed delivery has 7,680 category rows across 2,560 canonical contexts,
using the same three category labels and documented recovery definitions. This
audit uses their established implementation; no formula disagreement was found
in definition review. Different-scope count differences cannot establish one.

| Canonical context/category comparison | 4,096 prefix | 65,536 prefix |
|---|---:|---:|
| Shared observed/delivered rows | 24 | 340 |
| Observed rows absent from delivery | 25 | 294 |
| Delivered rows absent from observed prefix | 7,656 | 7,340 |

The 25 observed-only rows have delivered minute roles AM (7), ATT (6), FB (12).
For the larger prefix: AM (48), ATT (107), FB (125), GK (1), WM (13). These are
descriptive coverage findings, not a role filter applied here or approval of the
delivery's reporting policy. **NOT COMPARABLE:** partial-prefix counts and wider
delivered totals have different numerator scope, and the delivery covers a
narrower context set. No equality with season totals or delivered per90 is tested.

## J. Exposure and per90 limits

October 21 and refreshed minutes share all 5,576 canonical contexts and identical
minute values, with no missing/extra contexts. All observed contexts have known
minutes: 50 positive / 1 zero in the first prefix; 343 positive / 3 zero in the
larger prefix. Zero-minute contexts with observed events are IDs 8934 (VfB
Stuttgart), 32253 (FC Köln) and 316245 (Augsburg), all 2023/2024; only 8934 occurs
in the 4,096 prefix. These discrepancies require source/exposure reconciliation,
not guessed minutes or dropping actors from the raw-count diagnostic.

The supplied minutes tables have player/team/competition/season exposure, not
matching match-level/prefix exposure. Existing lineup stints do not by themselves
establish complete, validated exposure for these exact event windows; none was
reconstructed. Matching table values also cannot prove window alignment. Prefix
boundaries may truncate matches. **Per90 is withheld entirely from metric tables**;
counts and observed completion percentages need no invented minute denominator.

## K. Provenance, regression and data integrity

**NOT PRODUCTION-VERIFIED:** Arpit reports `fetch_lineups` then `player_minutes`
as the lineage of the lineup/crosswalk deliveries. Competition/season context is
event-derived, not an independent fixture manifest. D1B-P mappings remain
provisional; no `VERIFIED_SOURCE_EVIDENCE` label is used and no production trust
gate is bypassed or changed. Successful joins do not prove source completeness,
full-season identity reconstruction, exposure validity or scoring approval.

Focused regressions are in `tests/test_provisional_metrics.py`: exact recovery
selection, nullable flags/outcomes, zone boundaries/unknowns, attempt-weighted
percentages and N/A, outsider accounting, unresolved/conflicting-key failure,
duplicate mappings and cross-row-group event IDs, no fabricated zero grid/per90,
input immutability and parity with unchanged integrations, bounded read-only
projection, explicit missing paths, CLI behavior and conservation failure tests.

`python -B -W error -m unittest discover -s tests -q` passed **391 tests**:
366 existing plus 25 focused D2A regressions. The full frontend JavaScript suite
was enumerated recursively and passed **67 tests, 0 failures** across both test
files. Synthetic temporary test inputs used a permitted artifact workspace;
existing datasets were never outputs. `git diff --check` and whitespace checks
on all three new files passed.

All 11 SHA256 values matched both the pre-work inventory and D1/D1B records:

| Preserved Parquet | Fingerprint check |
|---|---|
| `data/processed/player_minutes.parquet` | PASS — unchanged |
| `data/processed/player_name_crosswalk.parquet` | PASS — unchanged |
| `data/processed/recovery_per90.parquet` | PASS — unchanged |
| `data/raw/statsbomb_lineups.parquet` | PASS — unchanged |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | PASS — unchanged |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | PASS — unchanged |
| `data/validation/arpit-match-context-review/match_metadata.parquet` | PASS — unchanged |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | PASS — unchanged |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | PASS — unchanged |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | PASS — unchanged |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | PASS — unchanged |

All 105 pre-existing fingerprinted files are unchanged, including the frontend,
recovery/press formulas, M2A/D1 production trust contracts, D1B-P diagnostic,
existing reports and M4A checklist. The only additions are
`scripts/audit_provisional_metrics.py`, `tests/test_provisional_metrics.py` and
this document, all untracked. Pre-existing untracked dataset/checklist entries
remain as found. No file was staged, committed or pushed; no branch/worktree was
created and no deployment occurred. Branch remains `integration-foundation`;
HEAD remains `9c4199ca8b357928ad0c1bae8f15a48f15990a19` and `main` remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. No production scorecard, per90 output,
scoring weights or ratings were generated.

## L. Next integration steps

1. Reconcile observed zero-minute contexts against source participation and
   exposure evidence. Do not estimate substitute minutes or alter raw data.
2. Select explicit complete-match event windows, validate matching match-level
   exposure and cross-batch event-ID accounting, then extend this provisional
   raw-metric audit to a justified cohort. No full scan is required by D2A.
3. Obtain independent source/context and fixture/team/participation evidence for
   production promotion. Keep statistical policy approval separate. Preserve
   current raw metrics and diagnostic provenance; do not publish a production
   scorecard, ratings or percentiles from these prefixes.
