# M1: read-only delivery validation

This tool checks the **existing delivered schema**, not a new permanent integration
schema. It does not select a metric implementation, approve eligibility thresholds,
calculate an index, edit datasets, or fetch StatsBomb data.

## Run

Requires Python 3.10+, pandas, numpy and a pandas Parquet engine (pyarrow or
fastparquet). No package is installed by the CLI. It reports missing dependencies
or unreadable files instead. Run from this integration worktree:

~~~powershell
Set-Location '<path-to-repository>'
$sourceRoot = 'C:\Users\Ayush\Desktop\Projects\Soccer-Impact-Engine-Index'
$original = Join-Path $sourceRoot 'data\processed'
$revised = Join-Path $sourceRoot 'data\validation\arpit-2026-10-21'

# Original delivery: expected FAIL / exit 1.
python -B scripts/validate_datasets.py --minutes "$original\player_minutes.parquet" --recovery "$original\recovery_per90.parquet"

# Revised delivery: expected PASS with zero-minute warnings / exit 0.
python -B scripts/validate_datasets.py --minutes "$revised\player_minutes.parquet" --recovery "$revised\recovery_per90.parquet"

# Validate revised delivery, then compare it with the original / expected exit 0.
python -B scripts/validate_datasets.py --minutes "$revised\player_minutes.parquet" --recovery "$revised\recovery_per90.parquet" --compare-minutes "$original\player_minutes.parquet" --compare-recovery "$original\recovery_per90.parquet"

# Synthetic tests; no network or source datasets needed.
python -B -m unittest discover -s tests -v
~~~

All four paths are explicit. The CLI has no default dataset location and does
not copy files into the worktree. Console output includes paths, row counts,
per-check affected-row counts, up to three examples, and corrective guidance.

Exit codes: **0** no errors (warnings allowed); **1** validation/comparison
errors; **2** CLI usage, dependency, or input-read failure. Checks can flag the
same row more than once; their counts must not be added as unique bad records.

## Input contracts

Identity uses player_id + team + competition_name + season_name.
Recovery adds event_type. Display names never participate in joins/comparisons.
This deliberately retains the delivered string context columns; it does not
require unprovided team/competition/season IDs.

Required minutes columns:

- Numeric: player_id, minutes, matches, tied_groups, min_GK, min_CB, min_DM,
  min_CM, min_FB, min_WM, min_AM, min_ATT.
- String: player_name, team, competition_name, season_name, position_group.
- Boolean: in_scope.

Required recovery columns:

- Numeric: player_id, minutes, matches, count, per90, pctl, pool_n.
- String: player, team, competition_name, season_name, position_group,
  event_type, pctl_note.
- Boolean: reportable, meets_min, full_coverage.

Extra columns are allowed; duplicate column labels are rejected. Numeric
strings and integer flags are not silently coerced into a different schema.
Nullable numeric/boolean pandas dtypes are accepted, subject to value checks.

## Checks and error meanings

| Check | What it verifies / corrective action |
|---|---|
| Schema/types/nonempty | Required fields, compatible types, unique column labels and nonempty deliveries. Repair the upstream export. |
| Identifiers/labels | Positive integral player IDs; nonmissing/nonblank context and display labels. Resolve using source identity evidence. |
| Unique keys | Every row participating in a duplicate stable key is reported. Do not arbitrarily keep the first row. |
| Finite/nonnegative values | Minutes, all position minutes, recovery count/rate are finite and nonnegative; counts are integral. |
| Matches | Positive-minute rows have positive integral match counts. Missing match counts are allowed for zero-minute records only; infinity is never allowed. |
| Position/flags | Position labels refer to reported minute groups; boolean flags are present; tied_groups is an integer between one and the number of groups. |
| Position sum | Total minutes equals the sum of all reported position minutes, without skipping missing values. |
| Dominant position (`minutes.dominant_position`) | With positive valid position-minute exposure, position_group is the maximum-minute group. Exact ties follow the existing producer order GK, CB, DM, CM, FB, WM, AM, ATT. |
| Position ties (`minutes.position_ties`) | With positive valid position-minute exposure, tied_groups equals the number of groups sharing the exact maximum. Near-equal values are not ties. |
| Scope flag (`minutes.scope_agrees`) | in_scope agrees with the existing GK/CB/DM/CM role list. Other roles may remain in minutes with in_scope=False. |
| Recovery scope (`recovery.in_scope_position`, `join.in_scope_minutes`) | Every recovery row has an in-scope role and an unambiguously matched minutes source with in_scope=True. Marking an out-of-scope recovery row unreportable does not admit it. |
| Recovery reporting (`recovery.reportable_agrees`) | Existing rule: GK Ball Recovery is reportable; GK Tackle/Interception are not. All three event types are reportable for other in-scope groups. This does not choose minimum minutes or coverage thresholds. |
| Zero-minute classification | WARNING for zero-minute records carrying a role. No positive exposure supports that classification; these rows may remain in minutes. |
| Positive denominator | Recovery rates require strictly positive minutes; never replace zero with an epsilon. |
| Rate arithmetic | Independently compute count / recovery.minutes * 90. |
| Percentile compatibility | Availability agrees with delivered reportable/meets_min/full_coverage flags; present percentiles are finite in 0..100 and have a positive integral pool size. |
| Join cardinality | Actual left join must match each recovery source row to one minutes record, without multiplication or unmatched rows. Duplicate recovery keys are separately rejected. |
| Denominator agreement | Each unambiguously matched recovery row uses the source minutes value, even if its own per90 arithmetic is internally correct. |
| Position agreement (`join.position_group_agrees`) | Every unambiguously matched recovery row has the same position_group as its minutes source. |
| Match-count agreement (`join.matches_agree`) | Every unambiguously matched recovery row has exactly the same integral matches value as its minutes source. |

Dominant-role, tie-count, scope and goalkeeper reporting checks mirror the existing
producer rules at origin/arpit-dev commit
0445f18fa1895320f0679ee84022888793fae6e7:
`src/metrics/player_minutes.py` (GROUP_ORDER, IN_SCOPE, assign_position_group)
and `src/metrics/recovery_per90.py` (positive-minute/in-scope base, reportable).
They validate consistency with that delivery, not statistical approval of those rules.
Zero-exposure rows retain the existing warning: no dominant-role or exact-tie
assertion is made without positive position-minute exposure. Invalid/nonfinite
position minutes are reported by the existing numeric checks before dependent
role checks are considered.

Floating comparisons use absolute tolerance 1e-6 and relative tolerance 1e-9.
Conservation of integral event counts is exact. Missing pctl/pool_n is legitimate
for ineligible rows; optional NaN is not treated like infinite values. Zero
recovery counts with positive exposure are legitimate.

Invalid schemas skip dependent checks. Invalid identifiers/labels skip join
checks; already reported errors still make the delivery FAIL. Cross-table minutes,
position-group, match-count and source-scope agreement are checked only for
unambiguous joins. A PASS with zero checked rows does not override a
join-cardinality failure, and no arbitrary duplicate source row is selected.

## Optional old/revised comparison

Both comparison paths must be supplied together. The target delivery still gets
full validation. The old delivery gets comparison-specific schema/value checks,
but is **not required to have unique keys**, because consolidation of old
duplicate identities is the purpose of this comparison. Validate it separately
to see its structural failures.

The comparison reports row counts, unique stable-key counts, duplicate-key
excess, and added/missing stable player contexts. It aggregates old duplicate
records by identity, then checks:

- Minute conservation per player/team/competition/season.
- Event conservation per player/team/competition/season/event type.
- Totals overall and by event type.

Changed display names do not imply changed identity. Changed stable player
contexts or conservation differences fail and need an upstream explanation;
there is no allow-list or automatic approval. New zero-count event rows are
allowed if contexts and aggregate event counts are conserved. Equal grand totals
cannot hide redistribution between players or event types.

Comparison does not approve a new stable key, infer aliases, compare raw events,
or prove that minutes by role were assigned correctly.

## Observed local acceptance results

Baseline main: 179ad5e1905ebefc7e97dc732d550b1c110a1ee4.
Work branch: integration-foundation. These are observations of the supplied
files, **not hardcoded validation rules**.

| Result | Original | Revised |
|---|---:|---:|
| Minutes rows | 5,578 | 5,576 |
| Minutes rows participating in duplicate keys | 4 (2 excess) | 0 |
| Recovery rows | 7,683 | 7,680 |
| Recovery rows participating in duplicate keys | 6 (3 excess) | 0 |
| Rows after recovery-to-minutes left join | 7,689 | 7,680 |
| Recovery rows with ambiguous minutes matches | 6 | 0 |
| Unmatched recovery rows | 0 | 0 |
| Zero-minute classification warnings | 22 | 22 |
| Overall delivery | FAIL / exit 1 | PASS / exit 0 |

Original duplicate minutes identities include player 3054 (Manchester City,
Premier League 2015/2016) and 401453 (Stade de Reims, Ligue 1 2015/2016).
The recovery duplicates involve player 3054 across all three event types.
The revised delivery passes schema, identity, join and arithmetic checks.
All 49 synthetic unittest cases pass, including a warnings-as-errors run
(`python -B -W error -m unittest discover -s tests -q`). The original 33 cases
are retained; 16 regression cases cover role and match-count disagreement,
unambiguous-join gating, dominant role and exact ties, scope flags, all excluded
recovery role groups, goalkeeper reporting, nullable types/nondefault indices,
and the unchanged zero-exposure warning behavior.

All eight added consistency checks pass on the revised delivery: dominant role,
exact tie count, minutes scope, recovery role scope, recovery reporting,
cross-table role, cross-table matches and cross-table source scope. The original
files still fail duplicate-key/cardinality checks. Their otherwise unambiguous
rows pass the new cross-table checks.
No datasets were altered; all four SHA256 fingerprints remained unchanged.

Old-to-revised comparison passes: no new/missing stable player contexts; minutes
are conserved per context, and recovery events are conserved per context/event.
Total minutes: 3,591,430.533333 in both deliveries.
Recovery totals: Ball Recovery 93,715; Interception 15,468; Tackle 22,848;
overall 132,031 in both deliveries.

SHA256 fingerprints before and after validation:

| File relative to original checkout | SHA256 |
|---|---|
| data/processed/player_minutes.parquet | 9701ec4a74b1a75ee6094f08619c40b26f6d6f103d64a23ca2802448351e931b |
| data/processed/recovery_per90.parquet | 056f94b0bd49bc707e5d00181d0b85654cd076e5dc3bc09e1a6c121cd530ee4d |
| data/validation/arpit-2026-10-21/player_minutes.parquet | 01f1bb2650df4f793971465eefad49eefcd41a302789b5c5009cf7355a4b1694 |
| data/validation/arpit-2026-10-21/recovery_per90.parquet | 7a546348b2c391d32221456fab259d639910d13c8e672ba030e6d30b38cab61f |

## Limits and next milestone

Consistency of delivered outputs **does not prove completeness of raw events**.
Conserved counts could preserve omissions shared by both deliveries. Internal
agreement also does not prove that lineup stints, stoppage/extra time, role
assignments, successful-action rules or recovery-event deduplication are correct.

This validator does not recalculate percentiles, validate pool membership,
choose minimum minutes or full-coverage thresholds, approve goalkeeper rules,
choose between contributor implementations, or calculate a
composite index. Its percentile checks reflect the flags in this delivery,
not approval of their policy. Role/scope/reporting checks enforce the existing
delivery rules; they cannot establish that the underlying lineup assignments are
correct.

Next: after identity/minutes decisions and raw evidence are available, validate
the event-to-lineup identity crosswalk and player-match exposure on small fixed
fixtures before connecting additional metrics.
