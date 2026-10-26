# M2B: defensive recovery integration

This milestone connects the existing recovery calculation to shared identity.
It provides in-memory interfaces and a bounded verification, not a complete
player-level reconstruction or final percentile table. It performs no file I/O.

## Reused source and definitions

The necessary excerpts come from origin/arpit-dev at
`0445f18fa1895320f0679ee84022888793fae6e7`:

| Local source | Reused contents |
|---|---|
| src/metrics/recovery_coverage.py | EVENT_TYPES, SUCCESS_OUTCOMES, DEFAULT_GROUP, REQUIRED_COLS, CARRY_COLS; _require, extract_recovery_events, recovery_counts, add_per90 |
| src/metrics/zones.py | Pitch/grid constants; split_location and assign_zone |

Selected function bodies and constants are unchanged. Source-level provenance
headers identify the original paths and commit. The excerpts omit executable
CLI blocks and unrelated zone helpers. No ingestion, spatial, ranking or plotting
implementation is imported. Team/name normalization comes from unchanged M2A.

Preserved definitions:

- Tackle: type Duel, duel_type Tackle, outcome Won, Success In Play or Success Out.
- Interception: type Interception with one of the same successful outcomes.
- Ball Recovery: type Ball Recovery unless the failure flag equals True.
  An empty failure flag is non-failed, matching the supplied raw export.
- Components stay separate; no combined recovery score or possession adjustment.
- Zones use the existing 120 by 80, 3 by 3 grid. Missing/off-pitch locations
  remain in totals and are excluded only from the zone breakdown.
- per90 = count / minutes * 90, only with positive known minutes.

The integration passes PLAYER_KEYS explicitly to recovery_counts, replacing its
legacy default name grouping without changing its counting algorithm. The
unchanged add_per90 helper is called only after unique minute keys are checked.
The excerpt helpers themselves retain their original interfaces; use the wrapper
below for the identity/cardinality guarantees.

## Production interface

```python
from src.identity import PLAYER_KEYS
from src.recovery import integrate_recovery

# Use M1 to validate the revised delivery first.
# Crosswalk and population must be explicit, supported inputs, as in M2A.
result = integrate_recovery(
    raw_events,
    trusted_crosswalk,
    verified_minutes,
    selected_population[PLAYER_KEYS],
)
counts_and_rates = result.totals
zone_counts = result.by_zone
accounting = result.accounting
```

Flow: raw event-ID preflight -> existing recovery extraction -> strict M2A
identity resolution -> selected stable-ID aggregation -> unique minutes join ->
separate counts and per90. Event IDs survive through identity validation.

| Input | Contract |
|---|---|
| raw_events | Unique nonblank string id; match_id, type, player, team, competition_name, season_name, location, duel_type, duel_outcome, interception_outcome, ball_recovery_recovery_failure. Optional supplied player_id follows M2A conflict rules. Extra columns are not used to infer identity. |
| trusted_crosswalk | M2A player_name_raw, player_id, team, competition_name, season_name; includes verified spellings and any known outsiders. |
| verified_minutes | Unique player_id/team/competition_name/season_name plus numeric minutes. Known values must be finite and nonnegative. M1 should validate the complete delivered schema upstream. |
| selected_population | Explicit unique canonical stable contexts; no role, exposure or coverage selection is inferred. |

Canonical keys remain player_id + team + competition_name + season_name. Both
known club aliases are normalized consistently in events, crosswalk, population
and minutes. Display names never group counts. No M2A identity rules changed.

Outputs:

- `identity.events`: every extracted event, including known outside events,
  event ID, canonical identity, event_type, x/y/zone and M2A status/diagnostics.
  Extraction uses the contributor's event-type ordering; identity preserves that
  order. Raw rows not selected by the recovery definitions are intentionally absent.
- `accounting`: one row per event type with extracted, selected,
  outside_population and unresolved counts. The latter three must sum exactly
  to extracted. Accounting zeros describe observed partitions, not player metrics.
- `totals`: canonical keys, event_type, count, minutes, per90, rate_status.
  One observed selected player/component per row. No percentiles or final index.
- `by_zone`: canonical keys, event_type, zone, count for usable locations.

Missing minute rows or missing minute values preserve counts, minutes/per90 N/A
and rate_status=missing_minutes. Zero minutes preserve counts, per90 N/A and
rate_status=zero_minutes. Positive finite exposure gets rate_status=ok. Negative,
infinite, nonnumeric or boolean exposure fails. No exposure is estimated.

The interface does not generate a player-by-component zero grid: an unobserved
component or a population member with no supplied event has no metric row.
Missing statistics are not replaced with zero. Sample counts divided by season
minutes are not complete-season rates unless the caller establishes coverage.
No new minimum-minute, role, goalkeeper, coverage or eligibility policy is added.
Existing M1 scope/reporting checks still apply to the delivered recovery table;
M2B does not manufacture a replacement for that ranked/reportable export.

## Failure and diagnostic behavior

Duplicate raw event IDs are rejected even if one duplicate would be filtered
out. Ambiguous/duplicate normalized lookup keys, conflicting IDs, duplicate
canonical minutes keys and alias collisions fail before aggregation. Missing
required columns and duplicate column labels fail explicitly.

Every extracted recovery identity must resolve before production metrics exist.
Unresolved identities raise UnresolvedIdentityError, retaining the M2A result for
diagnosis. No unknown name is assumed to be outside the selected population.
Known outsiders remain explicitly counted in identity/accounting but are not
selected metrics. Per-type selected counts must equal aggregate totals, and zone
counts must equal the number of selected events with usable zones. Cardinality
checks also guard the minutes join.

```python
from src.recovery import inspect_recovery

diagnostic = inspect_recovery(raw_sample, limited_crosswalk, population)
print(diagnostic.accounting)
unresolved = diagnostic.identity.events.query("identity_status == 'unresolved'")
```

This diagnostic path never returns totals or rates, so an incomplete crosswalk
cannot accidentally become a partial production metric table. The production
path has no permissive skip-unresolved option.

Uniqueness is enforced within each call. A streaming caller must enforce event-ID
uniqueness across batches; concatenating overlapping batches is unsafe. Inputs
are not mutated. The wrapper does not verify that trusted evidence is authentic
or infer completeness from conservation alone.

## Confirmed integration defect and storage adaptation

The contributor expression `~failure_flag.eq(True)` works for the supplied
object/empty flag export. On pandas nullable boolean data, a missing pd.NA
propagates through that expression and excludes a non-failed recovery. A
regression fixture [missing, False, True] demonstrated one count instead of two.

The wrapper converts only the failure-flag column to object storage on a copy
before calling the unchanged extractor. This preserves the original empty-flag
semantics across both representations; it does not change the recovery formula
or the caller's data. The fixture now yields two, and all real extraction totals
match. No identity-rule changes were needed.

## Verification

```sh
python -B -m unittest discover -s tests -v
python -B -W error -m unittest discover -s tests -q
```

35 M2B tests cover the three classifications and unsuccessful exclusions, zone
edges and missing locations, alias aggregation, alternate spellings, homonyms,
transfers/seasons, supplied-ID conflicts, duplicate events/lookups/minutes,
identity conservation including a deliberately broken resolver, explicit outside
accounting, unresolved diagnostic behavior, per90 and missing/zero minutes,
input immutability, nullable flags, empty outputs and absence of zero filling.
The existing 83 M1/M2A tests are retained: 118 tests total.

The read-only verification used:

- data/validation/drive-raw-review/statsbomb_team_events.parquet
- data/validation/arpit-2026-10-21/player_minutes.parquet
- data/validation/arpit-2026-10-21/recovery_per90.parquet

M1 passed the revised 5,576-row minutes / 7,680-row recovery delivery, with the
existing 22 zero-minute warnings. All six existing Parquet fingerprints remained
unchanged. No processed output was written.

### Global source-filter check

Projected only the 12 event/context/location/outcome fields required by extraction
and streamed 65,536-row Arrow batches. All 3,626,433 source rows were inspected;
the complete raw table was never materialized. Extracted recovery IDs were
checked across batches: zero duplicates among 246,393 extracted events.

| Component | Independently extracted | Previously reported |
|---|---:|---:|
| Tackle | 43,290 | 43,290 |
| Interception | 27,449 | 27,449 |
| Ball Recovery | 175,654 | 175,654 |
| Total | 246,393 | 246,393 |

This verifies raw filters, not a full player-ID reconstruction. Global source
counts include players outside the delivered recovery population.

### Incomplete sample diagnosis

Using just three explicit mappings, the first 4,096 raw rows yielded 125 recovery
events: 22 tackles, 9 interceptions, 94 ball recoveries. Nine identities resolved
selected (1 interception, 8 recoveries), none resolved outside, and 116 remained
unresolved (22 tackles, 8 interceptions, 86 recoveries). All 125 remained accounted
for; this is diagnostic output, not a population-complete metric table.

### Bounded player check across the available source

Mappings were explicitly limited to Granit Xhaka (3500), Jonathan Tah (8221) and
Patrik Schick (7044), all Bayer Leverkusen / 1. Bundesliga / 2023/2024. Exact
name/ID/context and contextual name uniqueness were checked in revised minutes;
the two selected player mappings were corroborated in revised recovery. Schick
was a known outside player for this interface check. This selection is a test
fixture, not a new eligibility rule. Only their 380 counted source events were
retained from the stream for production-interface verification.

| Component | Before identity | Selected | Known outside | Unresolved |
|---|---:|---:|---:|---:|
| Tackle | 40 | 37 | 3 | 0 |
| Interception | 32 | 30 | 2 | 0 |
| Ball Recovery | 308 | 290 | 18 | 0 |
| Total | 380 | 357 | 23 | 0 |

All counts were conserved; no multiplying join occurred.

| Player | Minutes | Component | Count | Per90 |
|---|---:|---|---:|---:|
| Granit Xhaka | 2823.283333 | Tackle | 24 | 0.765067 |
| Granit Xhaka | 2823.283333 | Interception | 14 | 0.446289 |
| Granit Xhaka | 2823.283333 | Ball Recovery | 184 | 5.865511 |
| Jonathan Tah | 2631.45 | Tackle | 13 | 0.444622 |
| Jonathan Tah | 2631.45 | Interception | 16 | 0.547227 |
| Jonathan Tah | 2631.45 | Ball Recovery | 106 | 3.625378 |

All six counts and rates matched the delivered recovery rows (absolute tolerance
1e-6, relative tolerance 1e-9 for rates): zero mismatches, no comparison of final
percentile rankings. Current-label evidence supports this bounded consistency
check; it does not recreate missing original lineup spelling evidence.

## Remaining inputs and limits

The complete lineup-derived spelling crosswalk is still missing. Full source-to-ID
reconstruction remains blocked; unknown names cannot be dropped or resolved from
similarity. Raw-event completeness, lineup/minute correctness, alias evidence
and population policy are upstream responsibilities. Conservation can preserve
an omission shared by both deliveries, and this bounded check cannot establish
coverage or validity for every player, season or competition.
