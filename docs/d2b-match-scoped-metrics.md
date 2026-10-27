# D2B: match-scoped metrics and exposure validation

Review date: October 26, 2026. **Ready for diagnostic review.** Real match-window
counts and percentages work. Explicit local stint evidence permits a small
subset of provisional recovery per90 values; most denominators remain withheld.
No ratings, percentiles, tiers, role eligibility or production publication.

## A. Exact windows, sources and reproduction

Deterministic selection from D2A's 65,536-event prefix: retain its first two
matches (3895292, 3895320), then the matches containing the other two zero-minute
actors (3895107, 3895348). All four have recovery/press observations and matching
lineups; the selection includes D2A example players Granit Xhaka and Jonathan Tah.

Inputs, all read-only and available without substitution:

- `data/validation/drive-raw-review/statsbomb_team_events.parquet`
- `data/raw/statsbomb_lineups.parquet`
- `data/processed/player_name_crosswalk.parquet`
- `data/validation/arpit-2026-10-21/player_minutes.parquet`
- `data/validation/arpit-refresh-review/player_minutes.parquet` (zero-minute comparison)
- `data/validation/arpit-match-context-review/match_metadata.parquet`

```sh
python -B -W error -m scripts.audit_match_scoped_metrics --events data/validation/drive-raw-review/statsbomb_team_events.parquet --lineups data/raw/statsbomb_lineups.parquet --crosswalk data/processed/player_name_crosswalk.parquet --minutes data/validation/arpit-2026-10-21/player_minutes.parquet --metadata data/validation/arpit-match-context-review/match_metadata.parquet --match-ids 3895292 3895320 3895107 3895348 --investigate-player-ids 8934 32253 316245
```

The script streams all source batches, projecting D2A's 15 metric/identity fields
plus `period`, `minute`, `second`. It keeps selected rows in source order, with a
100,000 selected-event safety cap. A temporary disk-backed SQLite unique index
checks IDs globally without retaining millions of strings in RAM; temporary work
files are closed and removed on completion/error. No source or output dataset is
written. `--batch-size`, `--max-events` and optional `--scratch-dir` are explicit
resource controls. Optional watched IDs use the D1B-P nonconflicting lookup to
count their exact spelling/context occurrences across the entire scan.

The scan visited **3,626,433 source rows and unique IDs**, found **zero global
duplicate event IDs**, and retained **9,202 rows**. Every selected match was
collected through end-of-file, not cut at a prefix boundary. These four matches
happen to have all their local rows within D2A's first 65,536 rows; the complete
scan established that no further selected rows occur later. Match 3895320 adds
249 rows beyond the original 4,096-event prefix.

## B. Local event coverage and observed times

**VERIFIED STRUCTURAL CHECKS:** all matches below have exactly one event-derived
competition/season association: **1. Bundesliga / 2023/2024**. Event counts equal
unique event-ID counts in every row. Times are observed clock ranges, not match
start/end evidence or playing-time denominators.

| Match ID | Observed teams | Local events / IDs | Lineup rows | Period 1 observed | Period 2 observed |
|---|---|---:|---:|---|---|
| 3895107 | Bayer Leverkusen; FC Köln | 2,403 / 2,403 | 48 | 00:00–48:54 | 45:01–93:01 |
| 3895292 | Bayer Leverkusen; Union Berlin | 2,211 / 2,211 | 55 | 00:01–48:31 | 45:00–96:41 |
| 3895320 | Bayer Leverkusen; VfB Stuttgart | 2,134 / 2,134 | 55 | 00:00–45:44 | 45:02–97:41 |
| 3895348 | Augsburg; Bayer Leverkusen | 2,454 / 2,454 | 49 | 00:01–47:56 | 45:01–93:22 |

Only periods 1 and 2 occur in these selected local events. Period clocks overlap
around halftime, demonstrating why naive cross-period clock subtraction cannot
recover first-half added time. Nothing assumes a 90-minute final whistle.

## C. Team, lineup and context associations

All **8 match/team pairs** agree between events and lineups. The 207 lineup rows
represent **158 distinct match/team/player records** including bench observations
and repeated position stints. Every event actor's exact provisional player ID,
canonical team and normalized original spelling occurs in that match's lineup.
Actor discrepancies, missing team associations and contradictory contexts: **0**.
The full per-team lineup ID lists are in the appendix and CLI summary.

Delivered metadata passes structural validation and agrees with all observed
contexts. Context-free lineups acquire competition/season by a many-to-one
diagnostic join only. Conflicting associations are rejected, never resolved by
keeping a first row. **CONTRIBUTOR-REPORTED PROVENANCE:** this metadata was
extracted from events, not `sb.matches`; this is consistency checking, not
independent authoritative fixture verification.

**CONTRIBUTOR-REPORTED PROVENANCE:** original lineups came from `fetch_lineups`,
followed by `player_minutes`, which produced the spelling crosswalk. Those origin
statements and local consistency checks are retained without a production trust
attestation.

## D. Provisional identity integration

Reuse D1B-P's lookup preparation and D2A's `audit_metrics`. The same 5,576 October
21 canonical contexts remain the explicit population without role/minute filters.
Lookup: 5,578 usable normalized keys, zero identical duplicates/conflicting keys.

**9,202 / 9,202 events matched and selected (100%)**, with **0 known outside,
0 unresolved, 0 missing actor names, 0 invalid identity fields, 0 duplicate joins**.
The pooled window contains 82 distinct observed canonical player contexts.
Per-match observed context counts are 31, 30, 32 and 31 in table order above.
An unresolved input blocks all player metrics, retaining diagnostic evidence;
unknown actors are never silently dropped or classified outside.

## E. Recovery metrics and zones

**PROVISIONAL OBSERVED METRICS:** unchanged M2B filtering, canonical aggregation,
nullable failure-flag handling and 3-by-3 zones are reused through D2A.

| Match | Successful tackles | Successful interceptions | Ball recoveries | Recovery player contexts |
|---|---:|---:|---:|---:|
| 3895107 | 17 | 16 | 81 | 26 |
| 3895292 | 22 | 9 | 94 | 30 |
| 3895320 | 18 | 10 | 90 | 27 |
| 3895348 | 20 | 13 | 85 | 27 |
| Pooled | **77** | **48** | **350** | **76** |

All 475 qualifying recovery events have usable zones; unknown-zone count is zero
in every match/category. Pooled counts for zones 1–9 are respectively
**58, 52, 31, 93, 31, 38, 62, 72, 38**. The CLI prints full
match/player/category/zone tables. No combined defensive score or absent-action
zero grid is created.

## F. Press-resistance metrics

Unchanged M3A pressure/outcome rules and D2A aggregation apply. All percentages
below are derived from summed attempts/completions, never averaged player rates.

| Match | Pass completed / attempts | Pass % | Dribble completed / attempts | Dribble % | Combined % | Press contexts |
|---|---:|---:|---:|---:|---:|---:|
| 3895107 | 182 / 209 | 87.081340 | 14 / 25 | 56 | 83.760684 | 27 |
| 3895292 | 104 / 132 | 78.787879 | 13 / 29 | 44.827586 | 72.670807 | 29 |
| 3895320 | 134 / 176 | 76.136364 | 12 / 21 | 57.142857 | 74.111675 | 30 |
| 3895348 | 87 / 116 | 75 | 14 / 29 | 48.275862 | 69.655172 | 29 |
| Pooled | **507 / 633** | **80.094787** | **53 / 104** | **50.961538** | **75.983718** | **76** |

The pooled combined numerator/denominator is **560 / 737**. Zero-attempt component
percentages remain N/A; unobserved player/action rows remain absent.

## G. Player examples and conservation

All examples retain team/competition/season context; these are examples, not
rankings. Xhaka (3500) and Tah (8221) are Bayer Leverkusen contexts.

| Scope / player | Tackle | Interception | Ball Recovery | Press pass completed / attempts | Dribble completed / attempts | Combined % |
|---|---:|---:|---:|---:|---:|---:|
| 3895107 / Xhaka | 1 | Absent | 6 | 19 / 21 | 0 / 0 (N/A) | 90.476190 |
| 3895292 / Xhaka | Absent | 1 | 5 | 7 / 9 | 1 / 1 | 80 |
| 3895348 / Tah | Absent | 3 | 3 | 3 / 3 | 1 / 1 | 100 |
| Pooled / Xhaka | 1 | 1 | 16 | 28 / 32 | 1 / 1 | 87.878788 |
| Pooled / Tah | Absent | 4 | 10 | 16 / 17 | 2 / 2 | 94.736842 |

`Absent` denotes no observed category row, not a fabricated zero. All input events
survive once in original order. Counts and completions conserve separately for
selected/outside/unresolved partitions. Per-player/category and zone counts, and
each press count column, conserve between per-match and pooled outputs.
Full disjoint accounting is **475 recovery + 737 press + 7,990 neither = 9,202**.
The six raw event types remain the ingested subset, not the full StatsBomb feed.

## H. Zero-minute investigation

The optional watched-actor scan finds the following counts across the complete
local event source, with no additional event matches for these exact provisional
spellings/contexts. Both October 21 and refreshed tables give each player
**0 minutes**, all eight position-minute fields zero, `tied_groups=8`, role `GK`
and missing `matches`. These delivered labels are not source positional evidence.

| Player / team | Event match | Local events | Original stint evidence, period 2 |
|---|---:|---|---|
| 8934 Pascal Stenzel / VfB Stuttgart | 3895320 | 1 Pass, 1 Carry, 1 Ball Recovery | Right Wing 91:00–91:26; Right Wing Back 91:26–unknown final whistle |
| 32253 Luca Jannis Kilian / FC Köln | 3895107 | 1 Pass, 1 Carry, 1 Ball Recovery | Right Back 90:45–unknown final whistle |
| 316245 Mahmut Küçüksahin / Augsburg | 3895348 | 4 Pass, 4 Carry | Right Center Midfield 90:16–unknown final whistle |

Stenzel also has a bench-only lineup observation in 3895167; Kilian has one in
3895258. Küçüksahin has only the played observation above. Stenzel's played match
has two position rows; each other played match has one. All starts are tactical
substitution-on records; Stenzel's intermediate end/start is a Tactical Shift.
All final ends are labeled Final Whistle but lack end clocks/periods.

Stenzel's Ball Recovery has failure flag true, so no qualifying recovery row is
created; his Pass is not pressured. Kilian has one qualifying Ball Recovery and
no pressured Pass/Dribble. Küçüksahin has one pressured pass, completed, and no
dribble attempts (dribble percentage N/A). His four Carries are outside M3A's
Pass/Dribble definition. No metric rows are manufactured for the other actions.

**VERIFIED STRUCTURAL CHECKS / explanatory mechanism:** existing contributor
`src/metrics/player_minutes.py` at `origin/arpit-dev` clips all stint starts/ends
to 90 minutes and fills an absent end with 90. Each recorded stint here therefore
becomes zero duration under that convention. With all position-minute values
zero, the existing dominant-role tie order selects GK. This exactly explains
the observed zero/tie/role pattern under the contributor-reported pipeline; no
evidence of a missing source ID or fuzzy identity repair is needed. No contributor
pipeline was run and no independent generation log was supplied. The provenance
of this particular execution remains contributor-reported, while the cap's
mathematical consequence and source/delivery values are directly checked.

This is not proof that delivered zero minutes are internally incorrect: they
are consistent with the export's capped convention, which discards these added-
time appearances. Actual uncapped durations remain unknown. No replacement
minutes or roles are assigned and no delivery is overwritten.

## I. Exposure validation and narrow per90 feasibility

Assess all 158 local match/player lineup groups separately from season minutes:
**32 bench-only, 124 withheld, 2 aligned explicit-stint contexts**. Bench-only
records create no metric zeros. Repeated position stints are examined together;
duplicates, overlaps, gaps and ambiguous entry/exit evidence withhold exposure.

A positive denominator first requires explicit attestation of exhaustive local
match collection. The file wrapper supplies it only after the complete scan;
the pure in-memory helper withholds per90 by default, so closed stint fields
cannot silently certify a prefix. A positive denominator also requires every
recorded stint to have an explicit valid
start/end clock and period, positive contiguous nonoverlapping intervals, an
entry (Starting XI at 00:00 in period 1, or substitution on), a terminal exit,
and every actor event inside the intervals. Only within-period intervals are
accepted; crossing or multiple periods requires period-boundary timing not
provided here. No end is filled from an event maximum or assumed 90/120 minutes.
Extra-time periods are structurally supported but not observed in these matches.

Most active players lack a final-whistle end clock or have intervals crossing
halves. Cross-period clock ranges cannot establish added time; their differences
are not used as denominators. All three zero-minute actors remain withheld.
Stenzel's explicit first 26 seconds cannot stand in for his unknown whole stint.

## J. Actual eligible per90 values and withheld outputs

These are **conditional provisional local-source rates**, not production-verified
season rates. Denominators come solely from the exact explicit lineup intervals:

| Match / player / team | Interval and exit | Minutes | Metric count | Per90 |
|---|---|---:|---|---:|
| 3895292 / 28239 Adam Hložek / Bayer Leverkusen | P1 00:00–31:58; injury substitution off | 31.966667 | Ball Recovery 2 | 5.630865 |
| same | same | same | Tackle 1 | 2.815433 |
| 3895348 / 51825 Tim Breithaupt / Augsburg | P1 00:00–40:14; injury substitution off | 40.233333 | Ball Recovery 2 | 4.473902 |
| same | same | same | Interception 1 | 2.236951 |

All 26 Hložek and 42 Breithaupt actor events lie within their respective explicit
intervals; no period boundary is crossed. Existing `add_per90` supplies the
unchanged arithmetic. Hložek's pooled denominator is withheld because his other
selected-match participation includes an open final-whistle stint. Breithaupt's
only selected-match appearance is this closed interval, so his two pooled rates
equal the two match rates. Pooled exposure requires every corresponding local
lineup appearance to be aligned or explicitly bench-only; one unknown appearance
blocks that player's pooled rate. All other rates remain N/A with reasons.

## K. Limitations, regression and integrity

**NOT PRODUCTION-VERIFIED:** collecting all local rows proves the scope of this
file, not completeness of StatsBomb's entire event feed, intended fixtures or
season participation. The export already excludes most event types, including
the boundary/substitution feed needed for broader exposure checks. Metadata is
event-derived and is never labeled an independent fixture manifest. D1 identity
evidence gates, M2A resolver, M2B/M3A formulas and scoring approvals remain unchanged.
Provisional local lineup durations do not promote the mapping to verified source
evidence or authorize website production data.

`python -B -W error -m unittest discover -s tests -q` passed **417 tests**
(391 existing + 26 focused D2B tests). All **67 recursive frontend JavaScript
tests passed**. Tests cover matches spanning batches, global duplicate IDs even
in unselected matches, filtering/caps, context and lineup contradictions,
unresolved rejection, watched actors, multiple/overlapping/duplicated/gapped
stints, missing timing, bench/zero-minute actors, period/extra-time handling,
match/pooled conservation and per90 only with matching explicit exposure.

All 11 SHA256 fingerprints match the pre-work inventory and D1B's full recorded
values (also referenced by D2A):

| Preserved input | Fingerprint check |
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

All 108 pre-existing fingerprinted files remain unchanged, including D1/D1B
contracts, D2A/D1B-P helpers and reports, M2B/M3A formulas, frontend, scoring and
M4A checklist. Only `scripts/audit_match_scoped_metrics.py`,
`tests/test_match_scoped_metrics.py` and this document are new, untracked files.
No tracked or staged changes, branch/worktree creation, dataset writes, download,
ingestion, commit, push or deployment occurred. Branch remains
`integration-foundation`; HEAD is unchanged at
`e444d04010f8e36f4e915a464937ede8b67fb39f`, and `main` remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. `git diff --check` and whitespace/path
checks on the new artifacts pass.

## L. Next milestone toward real website profiles

Prepare a reviewable diagnostic player-profile contract using these real raw
metrics, explicit match scope, provisional identity labels, coverage and per90
withholding reasons. Reconcile the capped-minute convention with the team before
changing any delivered exposure or positional policy. Obtain explicit period/end
and substitution evidence for broader denominators, then separately approve any
website diagnostic-data integration. This milestone changes no frontend and
publishes no production scorecard, ratings, tiers or percentiles.

## Appendix: lineup IDs by selected match and team

These are locally listed IDs, including bench players, not playing-time claims.

- **3895107, Bayer Leverkusen:** 3500, 8221, 8403, 8667, 8804, 9195, 10336, 27133, 28239, 28268, 30606, 32289, 32712, 33401, 38004, 40724, 41411, 46046, 49337, 261630.
- **3895107, FC Köln:** 7095, 8352, 8406, 8623, 8828, 9105, 9125, 10016, 11279, 18405, 29682, 32253, 35637, 38991, 55787, 72768, 134880, 300704, 382352, 405983.
- **3895292, Bayer Leverkusen:** 3500, 7044, 8221, 8667, 8804, 9195, 10336, 11391, 27133, 28239, 28268, 30606, 32289, 32712, 33401, 38004, 40724, 41411, 46046, 49337.
- **3895292, Union Berlin:** 3117, 6985, 8239, 8397, 8933, 9164, 9402, 11175, 12420, 18789, 20606, 23452, 23779, 24243, 24849, 29163, 32537, 42822, 44955, 48543.
- **3895320, Bayer Leverkusen:** 7044, 8221, 8667, 8804, 9195, 10336, 27133, 28268, 30606, 32289, 32712, 33401, 38004, 40724, 41411, 46046, 49337, 114833, 196651, 261630.
- **3895320, VfB Stuttgart:** 5697, 8238, 8538, 8934, 9102, 12407, 12413, 13329, 20662, 20947, 22067, 23614, 28805, 29227, 45115, 47619, 95272, 131243, 396287.
- **3895348, Augsburg:** 3428, 6874, 8245, 8318, 9198, 9221, 9227, 10823, 12411, 24319, 24442, 25118, 40167, 40995, 51825, 85506, 316234, 316237, 316245.
- **3895348, Bayer Leverkusen:** 3500, 7044, 8221, 8667, 8804, 9195, 10336, 27133, 28239, 28268, 30606, 32289, 32712, 33401, 38004, 40724, 41411, 46046, 49337, 261630.
