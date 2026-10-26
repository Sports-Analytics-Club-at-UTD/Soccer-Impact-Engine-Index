# M4B0: unified metric scorecard assembly

`src.scorecard.assemble_scorecard` combines existing in-memory metric results
into a canonical player-context table. This is a metric assembly layer, not a
team-approved scoring model. It does not calculate metrics, select players,
infer roles, apply eligibility thresholds, rank players, assign tiers/ratings,
weight components or create an overall Index. It performs no file or network I/O
and does not modify input DataFrames. The M4A design was committed before this
implementation; its policy recommendations remain pending approval.

## Interface and input contracts

```python
from src.scorecard import assemble_scorecard

# Inputs are explicitly supplied and verified by the caller.
# recovery_result, press_result and passing_result come from the existing
# integrate_recovery, integrate_press_resistance and
# integrate_progressive_passing interfaces, respectively.
result = assemble_scorecard(
    verified_context_base,
    recovery=recovery_result,
    press=press_result,
    passing=passing_result,
)
table = result.scorecard
diagnostics = result.diagnostics
```

Each metric argument is optional (`None` means not supplied). Supply actual
`RecoveryResult`, `PressResult` and `PassingResult` objects, not raw events,
delivered Parquets, generic tables or diagnostic-only results. Assembly reads
their `totals` tables and passing calibration labels; it does not rerun source
extraction, identity resolution, calibration or calculations. The caller must
provide already-validated, unaltered integration results and trusted base data.
Dataclass type checks are not independent proof of their provenance.

Canonical keys, in order, are `player_id`, `team`, `competition_name`,
`season_name`. M2A's `validate_population` applies its existing ID/label rules
and Marseille/Caen aliases. IDs remain nullable Int64 without float rounding.
No name-based join, new alias, role inference or team/season collapse occurs.
Different teams, competitions and seasons remain separate contexts even for
the same player. Different players may share a display name.

The base requires these four keys. Supported optional descriptive columns,
in fixed order, are `player_name`, `position_group`, `minutes`, `matches`.
Names/roles are strings or missing labels and are copied, not used to select or
match players. No position enum or dominant-role policy is introduced. Known
minutes must be finite, numeric and nonnegative; known matches must additionally
be integers fitting signed int64. Missing exposure is allowed. Without these
optional columns, the assembler does not manufacture them from another input.
Other base columns are rejected explicitly, including metric/output collisions;
extensions need an explicit contract rather than silent passthrough.

## Output columns and original units

Output is one row for every base context, sorted ascending by the four canonical
keys with a fresh RangeIndex. Column order is keys, supplied descriptors in the
order above, then the following fixed component blocks. Metric blocks exist
even when their inputs are omitted or empty. Reordering input rows/columns does
not change output values or column order.

### Recovery long to wide

| Source `event_type` | Output prefix |
|---|---|
| Tackle | `recovery_tackle` |
| Interception | `recovery_interception` |
| Ball Recovery | `recovery_ball_recovery` |

Each prefix has columns in this order: `_count`, `_per90`, `_rate_status`,
`_minutes`, `_present`. For example, `recovery_tackle_count` is the unchanged
observed tackle count, `recovery_tackle_per90` is the existing event rate per
90 minutes, and `recovery_tackle_present` identifies a supplied tackle row.
Counts, rates, statuses and source minutes stay separate for all three types.
No recovery composite or zone score is created. `by_zone` stays in the original
RecoveryResult and is not silently blended into the scorecard.

Required recovery totals columns are keys plus `event_type`, `count`, `minutes`,
`per90`, `rate_status`. Uniqueness is per canonical context **and event type**;
not every base context is required to have all three types. Unknown/missing event
types and duplicate component rows, including alias collisions, are errors.

### Press resistance

These exact M3A field names are preserved, in order:

1. `pressured_pass_attempts`, `pressured_pass_completed`
2. `pressured_dribble_attempts`, `pressured_dribble_completed`
3. `pressured_actions`, `successful_pressured_actions`
4. `pressured_pass_completion_rate`, `pressured_dribble_completion_rate`,
   `press_resistance_rate`
5. `press_minutes`, `press_present`

The first six are event counts; all three rates are percentages on a 0-100
scale, not fractions or per90 rates. The implemented pass/dribble names end in
`_rate`, not `_pct`. Required totals are keys and the nine metric fields.
Optional source `minutes` becomes `press_minutes`; if not supplied, this column
remains N/A even for a present press row. There is no upstream press rate-status
field and none is invented. No 30-action or 900-minute rule is applied.

### Progressive passing, Level A

The passing block, in order, is `prog_attempts`, `prog_passes`, `third_cross`,
`value_sum`, `prog_passes_p90`, `prog_completion_pct`, `third_cross_p90`,
`pass_value_p90`, `passing_minutes`, `passing_rate_status`,
`passing_difficulty_scope`, `passing_difficulty_complete`, `passing_present`.
Required totals are keys, the first eight fields, `minutes` and `rate_status`.

Counts, completion percentage, event per90 rates and difficulty-weighted distance
values retain their M3B units. `value_sum` and `pass_value_p90` are not goals,
ratings or probabilities. Passing `minutes` and `rate_status` receive prefixes
to avoid overwriting base/recovery exposure or status. No Level B or 360 metrics
are attached.

`difficulty_scope` and `difficulty_complete` from PassingResult become
`passing_difficulty_scope` and `passing_difficulty_complete` on present passing
rows only. Missing passing rows do not inherit calibration metadata. The
diagnostics retain these labels even for an empty supplied PassingResult.
Sample/diagnostic passing inputs and `difficulty_complete != True` are rejected,
as in the production integration contract. A declared-complete synthetic or
bounded reference is not certified as a production season cohort by assembly.

## Missing values, storage and exposure

Presence flags are non-null booleans. Counts use nullable Int64; metric values
and minutes use nullable Float64; component statuses/scope use nullable strings;
passing declared completeness uses a nullable boolean. Input frames are not
changed by these output storage adaptations. Known nonnegative finite numeric
values are required, with nonmissing integer counts. Invalid values, unsupported
source columns and duplicate column labels fail explicitly.

| Situation | Output |
|---|---|
| Component row present with observed zero | `_present=True`, value `0` |
| Component row present with undefined/missing rate | `_present=True`, rate N/A; source status retained where available |
| Component row absent or input omitted | `_present=False`, all that component's values/status/metadata N/A |

No absent observation is zero-filled. A missing tackle does not become zero
because an interception exists. Present N/A press/passing percentages remain
N/A. Source missingness is preserved as nullable output missingness, not as a
new valid metric. With no base rows and no metric observations, the result is
an empty table with the same component schema. Nonempty metric observations
against an empty base fail as unmatched contexts.

Known minutes must agree exactly across the base and every supplied component,
including the three recovery types. Zero versus positive known minutes is a
conflict. Missing versus known is not a conflict: both source values are retained,
with no imputation or preference for one input. This check also works without
base minutes. Existing recovery/passing `rate_status` must agree with their own
missing/zero/positive minutes. The assembler preserves rates and does not
recalculate them. Source-window alignment still requires external evidence:
equal numerical minutes alone cannot prove matching event coverage.

## Cardinality, conservation and diagnostics

Unsafe inputs raise `ScorecardError` with a component/schema or context
diagnostic. Base and press/passing totals require unique canonical keys;
recovery requires unique keys within each event type. Every join uses explicit
keys and one-to-one validation. Output columns cannot overwrite existing ones.
Metric contexts absent from the base fail with their count and up to three
example keys; there is no silently dropping join or permissive exclusion mode.

After each attachment, row count must equal base size, present rows must equal
source rows, and sums of source counts must exactly equal attached counts.
Integer preservation is tested above float's exact-integer range. Passing values
and rates are copied, not normalized, combined or recomputed. No upstream event
accounting or metric validation is replaced by these assembly checks.

`result.diagnostics` contains:

- `base_rows` and a `coverage_statement` explicitly limited to row presence.
- `components`, keyed by the three recovery prefixes, `press`, and `passing`.
  Each records `source_rows`, `present_rows`, `absent_base_rows`, `count_totals`,
  and `present_na_values` by output field. Missing-value counts count only source
  rows, separately from absent base rows. Zero diagnostic counts for absent
  sources describe assembly, not observed zero player activity.
- `passing_reference`: `None` when omitted; otherwise `scope`,
  `declared_complete` and `independently_verified=False`. Upstream result objects
  retain richer preparation/identity accounting for caller inspection.

These diagnostics make no full-season, calibration-authenticity, crosswalk or
identity-coverage claim. They do not create coverage/eligibility flags for use
as statistical scoring gates. Serialization can convert pandas nullable values
to the frontend's null representation later; no serializer or frontend changes
are introduced here.

## Verification and bounded examples

`tests/test_scorecard.py` uses the existing recovery, press and passing event
fixture builders to produce actual integrated result objects. The fixtures
combine tackles, interceptions, recoveries, pressured passes/dribbles and Level A
passes under explicit synthetic identities/exposure. Tests include a nonzero
difficulty-weighted passing value, an observed non-progressive zero, missing
components and rates, low/zero/missing minutes, aliases, homonyms, transfers,
seasons, large integers, rejected duplicates/unmatched contexts, immutable inputs,
empty upstream outputs and deterministic assembly. None is a reconstructed real
complete-season population or a player ranking.

```sh
python -B -m unittest discover -s tests -v
python -B -W error -m unittest discover -s tests -q
```

Both commands passed: 246 tests total, including all 196 existing milestone
tests and 50 new assembly tests. Earlier milestone files and M4A remain
unchanged, and all six existing Parquet SHA256 fingerprints match the pre-work
baseline. Only this document, the assembly module and its test module are new.

No raw-data extraction is needed for this assembly milestone. Existing real
recovery deliveries are not substitutes for M2B/M3A/M3B result objects. All
Parquets remain read-only; this module never reads or writes them.

## Data limitations and future scoring integration

A complete trusted lineup-derived spelling crosswalk and verified aligned
per-metric source/exposure coverage are still missing for a full real scorecard.
M1-validated deliveries establish internal consistency, not complete actor
identity or source coverage. Passing also requires verified correctly scoped
calibration; declared completeness alone is insufficient. Available 360 frames
do not support complete primary-pool Level B. Joseph's alternative press model
lacks required Miscontrol/Dispossessed events, and no clearance metric is
integrated. None of these missing inputs is fabricated by assembly.

M4A comparison groups, minimum minutes/actions, coverage gates, small-pool rules,
normalizations, FIFA-style transformations, tiers, component sets and weights
remain **PENDING APPROVAL**. This technical assembly milestone approves none of
them and does not change M4A. Future scoring functions can consume this table
after schema/policy approval, with separately verified coverage evidence and
explicit missing-value reasons. Row-presence flags and a declared calibration
label cannot stand in for those approvals or evidence.
