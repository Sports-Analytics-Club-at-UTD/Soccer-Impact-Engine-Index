# M3B: Level A progressive passing

In-memory integration of Joseph's provisional Level A method with M2A identity
and unique verified minutes. No writers, rankings, Level B metrics or second
press-resistance model are included. Earlier milestones are unchanged.

## Source and formulas

Source: origin/Joseph-dev at `013c8edd5196a15ac826558f4b0964cc6f3a3e58`,
`src/metrics/line_breaking.py` and `src/metrics/scoring_common.py`.
The local `src/metrics/progressive_passes.py` excerpts reuse unchanged bodies for
distance_to_goal, is_open_play_pass, per90, _third, prepare_passes,
flag_progressive and level_a_counts. KEYS points to shared stable player keys.
Difficulty fitting is adapted to combine whole-cohort cell statistics across
batches rather than inadvertently calibrating each reporting batch separately.

- Open play: Pass with pass_type missing, Recovery or Interception.
- Unknown and Injury Clearance outcomes are excluded; null outcome completes.
- Geometry: StatsBomb 120 by 80, attacking goal (120, 40). Distance is Euclidean.
  Use reported pass length, falling back to geometric length when missing.
- Progressive attempt: d1 <= 0.75*d0 **and** end_x-start_x >= 10.
- Progressive pass: progressive attempt and completed.
- Third crossing: progressive pass ending in a higher third (boundaries 40/80).
- p_hat: completed / attempts among **all** eligible measurable open-play passes
  in competition_name + season_name + start_third + length_band. Bands are
  left-closed [0,15), [15,30), [30,infinity).
- Completed progressive value: (d0-d1)*(1-p_hat); other measured passes have zero.

Thresholds and difficulty weighting remain existing provisional assumptions,
not approval of a statistical or product policy.

## Interface and reference contract

```python
from src.passing import calibrate_difficulty, integrate_progressive_passing

# raw_reference_batches must represent the entire named calibration cohort,
# including outsiders and nonprogressive passes. No population input is accepted.
reference = calibrate_difficulty(
    raw_reference_batches,
    scope="Explicitly defined delivered league-season cohort",
    complete=True,
)
result = integrate_progressive_passing(
    reporting_events, trusted_crosswalk, selected_population, verified_minutes,
    reference=reference,
)
```

Calibration accepts one raw DataFrame or an iterable of disjoint batches. It
fits one shared table by summing completion/attempt counts before dividing.
Changing the reporting population cannot change difficulty. Duplicate IDs within
or across reference batches fail. Reference counts and probabilities are checked
again when applied; uncovered cells fail without a reporting-batch fallback.

`scope` and boolean `complete` are mandatory. Completeness is a caller attestation
about the named supplied cohort, **not** an inference or independent certification
of source coverage. `complete=False` labels illustrative calibration and is
rejected by production; it can only be used by the diagnostic interface. Do not
mark a selected-player subset or partial season complete. Keep input provenance
and any known season/match gaps with the reference scope.

| Input | Required fields |
|---|---|
| Raw reporting/reference events | id, match_id, type, team, player, competition_name, season_name, location, pass_end_location, pass_outcome, pass_type, pass_length |
| Trusted crosswalk | player_name_raw, player_id, team, competition_name, season_name |
| Selected population | player_id, team, competition_name, season_name |
| Verified minutes | Same canonical keys plus numeric minutes |

Existing trusted event player_id is optional. The original preparation projects
it away; the wrapper restores it by unique event ID before M2A, preserving values
and conflict detection without suffixed player-ID joins. Spelling evidence and
club aliases follow unchanged M2A rules. Names never group resolved metrics.

Required columns/unique event IDs are checked before filtering, including excluded
events. Geometry with missing coordinates is excluded exactly as in the source;
nonfinite derived geometry or negative lengths raise input errors rather than
publish invalid values. Finite off-pitch coordinates retain the original method's
behavior. Generated geometry/difficulty column names are reserved on raw inputs.

## Outputs, missingness and conservation

`result.preparation` reports raw/pass/open-play counts and exclusive counts for
non_pass, non_open_play, excluded_outcome, missing_geometry and measurable.
`result.event_accounting` retains every supplied event ID/context and exactly one
category. Thus excluded outcomes and missing geometry are visible, not silent.

Every measurable event survives through identity validation. Production raises
on unresolved identities before returning player metrics. Known outsiders remain
in identity/accounting, not the selected aggregates. The accounting table splits
measurable passes, progressive attempts, progressive completions, third crossings
and values across selected, outside_population and unresolved. Integer counts
must conserve exactly; floating values use tolerance 1e-6 absolute / 1e-9 relative.
Ambiguous/duplicate spelling mappings, conflicting IDs, duplicate normalized
minutes keys and multiplying joins are rejected.

`result.totals` contains canonical keys and:

| Field | Calculation |
|---|---|
| prog_attempts, prog_passes, third_cross | Separate sums of observed flags |
| value_sum | Sum of observed pass values |
| prog_passes_p90 | prog_passes / minutes * 90 |
| prog_completion_pct | 100 * prog_passes / prog_attempts; N/A at zero attempts |
| third_cross_p90 | third_cross / minutes * 90 |
| pass_value_p90 | value_sum / minutes * 90 |

Zero/missing minutes retain counts and values with N/A per90 fields, flagged
zero_minutes/missing_minutes in rate_status. Positive known minutes get status
ok. Negative/nonfinite known exposure fails. No unobserved player row is created.
Zero progressive counts for a player with measured nonprogressive passes are
observed zeros; unknown identities or missing geometry do not become zeros.

```python
from src.passing import inspect_progressive_passing
diagnostic = inspect_progressive_passing(
    sample_events, limited_crosswalk, population, reference=reference,
)
```

Diagnostics retain unresolved rows and calibration scope/completeness labels,
but have no player totals. Inputs and reference cells are not mutated. Reporting
event uniqueness is per call; streaming reporters must check across batches.
Reference completeness does not establish reporting coverage: sample counts over
season minutes are illustrative arithmetic, not full-season player rates.

## Tests and observed checks

```sh
python -B -m unittest discover -s tests -v
python -B -W error -m unittest discover -s tests -q
```

39 new cases cover filters, geometry boundaries, thirds/bands, outsider-inclusive
and population-independent difficulty, streamed calibration, partial-reference
rejection, missing cells, pass values, geometry exclusions, aliases, identities,
transfers/seasons, supplied IDs, duplicates, conservation, minutes and immutability.
Existing 157 tests remain unchanged: 196 total.

Read-only verification used the existing raw review events and revised minutes /
recovery Parquets under data/validation. M1 passed 5,576 minutes and 7,680 recovery
rows, retaining 22 existing zero-minute warnings. All six existing Parquet
fingerprints remained unchanged.

Calibration projected the 12 required columns and streamed the entire delivered
Premier League 2015/2016 cohort in 65,536-row batches. No full raw table was loaded;
only a compact six-column measurable cohort was retained for direct comparison
with the original add_difficulty transform. No dataset was written.

| Calibration accounting | Count |
|---|---:|
| Delivered raw events / observed matches | 741,442 / 380 |
| Pass / open-play events | 368,619 / 329,685 |
| Non-open-play / excluded outcomes | 38,934 / 1,757 |
| Missing geometry / measurable passes | 0 / 327,928 |
| Difficulty cells | 9 |

This is full **delivered-cohort** calibration, not independent proof that every
real-world pass is present. Other leagues/seasons are outside this reference.

The first 8,192 delivered Premier League 2015/2016 records were the reporting
sample: 4,297 passes, 3,940 open-play, 357 non-open-play, 17 excluded outcomes,
zero missing geometry, and 3,923 measurable passes. Progressive attempts totaled
472, completed progressive passes 230, and third crossings 142.

Four exact current-label mappings were checked against revised minutes, including
contextual name uniqueness, and corroborated in revised Ball Recovery rows:
Yaya Toure (3087, exact accented source spelling), Otamendi (3090, exact accented
source spelling), Fernando Luiz Rosa (3054), Joe Hart (3291), all Manchester City /
Premier League / 2015/2016. Hart was an explicit known outsider for this fixture.
This supports delivered-table consistency, not independent lineup reconstruction.

| Sample identity partition | Measurable | Attempts | Progressive | Third crossings | Value sum |
|---|---:|---:|---:|---:|---:|
| Selected | 153 | 11 | 6 | 4 | 17.539727 |
| Known outside | 13 | 4 | 2 | 2 | 37.236678 |
| Unresolved | 3,757 | 457 | 222 | 136 | 1849.724056 |

Strict production rejected 3,757 unresolved identities. The bounded production
check retained only the 166 IDs resolved by explicit evidence: selected 153,
known outside 13, unresolved zero. All counts/values conserved. No row was
invented for Rosa, whose verified label had no measurable pass in this sample.

| Player | Attempts / progressive / third crossings | Value sum | Progressive p90 | Completion % | Third-cross p90 | Value p90 |
|---|---|---:|---:|---:|---:|---:|
| Yaya Toure | 8 / 4 / 2 | 12.941195 | 0.154737 | 50 | 0.077368 | 0.500619 |
| Otamendi | 3 / 2 / 2 | 4.598531 | 0.067390 | 66.666667 | 0.067390 | 0.154947 |

These use verified season minutes 2326.533333 and 2671.033333 against bounded
sample counts; the per90 values are illustrative, not season measurements.
Example: one Toure pass reduced goal distance from 69.053964 to 48.931789;
full-cohort p_hat was 0.865404732, giving value 2.708349566.

Only original pure function ASTs were executed for comparison, without importing
the CLI or ranking code. All nine full-cohort p_hat cells, 3,923 sample geometries /
flags / values, two player aggregates, and all requested rates matched Joseph's
Level A logic. Reused function/constant ASTs were also checked unchanged.

## Deferred Level B and press model

Joseph's Level B counts visible outfield opponents strictly between the start
and end x of a completed open-play pass with a frame; at least three is a break.
Its orientation check compares actor/start positions. Its match-level coverage
flag does not establish usable frames for every pass. Original frame-row counting
can overcount duplicate visible-player observations; absent frames are not zero
opponents. No Level B implementation or output is exposed here.

A later task needs event-level frame coverage, deduplication evidence/semantics,
orientation validation, visibility/missingness accounting and matching exposure.
Current later-season selected-match 360 data cannot support a complete 2015/2016
four-league season metric. No bypass per90, Level B percentile or index use is
approved by this milestone.

Joseph's separate retention model includes Miscontrol/Dispossessed losses and
progressive pressured carries. The current export lacks those loss types. Its
full retention rate cannot be calculated by treating them as zero or combining
it with M3A. Additional source events and a team decision on the two definitions
are required. M3A remains unchanged.

The full trusted lineup spelling crosswalk is still missing. Complete player
reconstruction, source completeness, role/exposure correctness, statistical
approval and final scoring remain outside M3B.
