# D2C: provisional real-player profile contract

**DIAGNOSTIC / PROVISIONAL / NOT PRODUCTION VERIFIED.**

Review date: October 26, 2026. The separate contract version is
`soccer-provisional-profiles/v1`. It prepares D2B observations for a future
diagnostic UI; it is not publication approval and is not `soccer-scorecard/v1`.
No public JSON, website data substitution, ratings or scoring is introduced.

## Pure builder and validated inputs

```python
from src.provisional_profiles import build_profiles

# audit is an existing validated D2B MatchAudit, not a delivery/production scorecard.
# october21_minutes is optional supporting metadata, never a denominator here.
payload = build_profiles(audit, delivered_minutes=october21_minutes)
```

The builder returns fresh JSON-compatible dictionaries/lists and performs no file
or network I/O. It reuses the existing D2B, D2A and M3A pure functions to recheck
the supplied mutable results: exact identities, event and match membership,
duplicate keys, per-match/pooled counts, zones, percentages, exposure and per90.
Contradictory or modified tables raise `ProfileContractError`, not a partial
profile output. No production identity-evidence label is created or relaxed.

Revalidation uses the input's already-established selected membership for these
events only; it does not reconstruct or replace the project-wide population.
Profiles are emitted only for selected canonical contexts with observed events,
not for every lookup/roster row. Known outsiders do not become profiles. No
unresolved event may enter the contract. The real D2B input retains the original
5,576-context diagnostic population before profile construction.

## Versioned schema and field definitions

| Object / field | Definition |
|---|---|
| `schema_version` | Exact `soccer-provisional-profiles/v1` |
| `verification_status` | Exact `DIAGNOSTIC / PROVISIONAL / NOT PRODUCTION VERIFIED`, also on each profile |
| `production_schema_compatible` | Always `false` |
| `integer_encoding` | `decimal_string`: player/match IDs and event/action counts retain exact signed-int64 precision |
| `units` | Counts: events; percentages: 0–100; aligned exposure: minutes; recovery per90: events/90min; zones: existing 3x3, 120x80 pitch |
| `canonical_keys` | `player_id`, `team`, `competition_name`, `season_name` |
| Top-level `scope` | Sorted exact diagnostic match IDs, observed match/event counts, explicit local-collection attestation, coverage statement and `authoritative_feed_complete=false` |
| `identity_provenance` | Caller-supplied D1B-P provisional lookup and contributor-reported lineup/crosswalk lineage |
| `match_context_provenance` | Event-derived; explicitly not an independent authoritative fixture manifest |
| `profiles[]` | One unique canonical context, sorted by numeric player ID then context labels |
| Profile `identity` | Decimal-string player ID, canonical labels, supported `player_name`, observed name variants and name source |
| Profile `scope.included_match_ids` | Local lineup appearances for this player/context inside the diagnostic window, including explicitly recorded bench appearances |
| Profile `scope.observed_match_ids` | Subset with actual actor events; `observed_match_count` counts only this subset; `observed_event_count` is an exact decimal string |
| Profile `matches[]` | One record for each observed actor match, with `match_id`, `scope_match_ids`, observed event count, recovery, press and exposure |
| Profile `pooled` | Counts and derived percentages for that player's included window, with explicit `scope_match_ids`; not an average of match percentages |
| `not_assessed_metric_families` | `['progression']`: no progression measurements were supplied by D2B; no placeholder progression values |

Identity names are descriptive observed event labels, never join keys. Existing
M2A whitespace/doubled-apostrophe normalization and the two team aliases apply.
If multiple observed spellings remain, `player_name=null` and the exact normalized
variants remain available; the builder does not arbitrarily pick an identity.
Transfers, teams, competitions and seasons remain separate canonical contexts.

### Recovery blocks

Each match/pooled `recovery` object has separate `Tackle`, `Interception` and
`Ball Recovery` entries:

- `status`: `observed` or `missing`; `count`: decimal string or null.
- `match_ids`: the entry's explicit numerator window.
- `zone_counts`: observed `{zone, count}` entries sorted by zone, or null for a
  missing measurement. An observed empty zone list means no usable zone observations,
  not zero total activity; `unknown_zone_count` retains the count difference.
- `per90`: `status` (`available`/`unsupported`), `available`, numeric `value` or
  null, reasons, numerator/denominator match IDs and the aligned minute denominator.
  Unsupported denominator IDs/minutes are null, rather than a false alignment claim.

### Press blocks

`press.status` distinguishes an observed aggregate from an absent aggregate.
`press.counts` contains the four M3A pass/dribble attempt/completion counts plus
`pressured_actions` and `successful_pressured_actions`, as exact decimal strings.
If the entire measurement is absent, all these values remain null.

`press.percentages` has `pressured_pass_completion_rate`,
`pressured_dribble_completion_rate` and `press_resistance_rate`, each with a
`status` and numeric `value` or null. Rates use unchanged `add_completion_rates`:
pooled successes divided by pooled attempts. No match/player percentages are
summed or arithmetically averaged. Component zero-attempt percentages have status
`undefined_zero_attempts`; a missing whole aggregate has status `missing`.

### Exposure blocks

`exposure.match_ids` and `match_records[]` retain the exact lineup window and
D2B statuses: `aligned_explicit_stints`, `bench_no_stint`, or `withheld`, with
aligned minutes or null and reason codes. Aggregate exposure has `status=aligned`
only if every corresponding appearance is measured/explicitly bench-only and
the all-local-rows attestation is present. Otherwise aggregate minutes remain null.

Optional pooled exposure metadata separately carries `delivered_minutes`,
`delivered_minutes_status` (`known_wider_scope`, `zero`, `missing`, `not_supplied`),
its wider scope statement, and `source_ambiguities`. The three D2B zero-minute
actors retain `observed_activity_with_zero_delivered_minutes`; their original
zero values are not changed or substituted into per90 denominators.

## Missingness and scope rules

| Situation | Representation |
|---|---|
| No observed recovery category or whole press aggregate | `missing`, null values; no invented zero grid |
| Observed pressured attempt with no completions | Observed completion count `"0"` and numeric percentage `0.0` |
| Zero component attempts in an observed press aggregate | Count `"0"`; percentage null with `undefined_zero_attempts` |
| Metric family not assessed by D2B | Explicit `not_assessed_metric_families`; no fabricated measurements |
| Observed count but unsupported exposure | Count retained; per90 null, `unsupported`, with reasons |
| Explicit bench-only appearance | Exposure record may retain D2B's 0 minutes; no fabricated actor match or metric row |
| No supplied wider-scope minutes / missing delivered value | `not_supplied` / `missing`; neither becomes zero |

All profile match IDs must belong to the diagnostic window, and every observed
match must have corresponding lineup context. Metric/exposure keys are unique.
Numerator and available denominator windows must coincide. One unknown appearance
blocks that player's pooled per90, even when one match rate is supported.
Input and returned-output mutations cannot change each other. JSON serializes
with `allow_nan=False`; missing values are null, not NaN/Infinity.

## Real D2B output and conservation

Reconstructed the same D2B result from the unchanged event source, exact match IDs
3895107, 3895292, 3895320 and 3895348, and October 21 population. Reuse of the
bounded source slice is justified by its full recorded SHA256 and D2B's exhaustive
scan/count evidence: the first 65,536 rows contain exactly all 2,403 / 2,211 /
2,134 / 2,454 selected match rows. A prefix alone is not a completeness attestation.
No new full decoded-event scan or download was needed to reproduce these
immutable inputs; SHA256 checking still reads the source bytes.

The resulting contract contains **82 unique real canonical profiles**, **9,202
selected events**, four diagnostic matches and no fabricated roster-only players.
Recovery sums remain **77 Tackles, 48 Interceptions, 350 Ball Recoveries**, with
475 usable zone observations. Press remains **633 pass attempts / 507 completions**,
**104 dribble attempts / 53 completions**, and **737 total actions / 560 successes**.
The pooled all-player diagnostic rate is 75.98371777476255%; individual profiles
retain their own pooled numerators/denominators, not this global percentage.

### Real selected-field excerpts

These are selected fields from actual builder output, not standalone complete
payloads or production fixtures. The full structure is defined above and returned
by the builder; no public JSON artifact is written.

Granit Xhaka, ID 3500, Bayer Leverkusen / 1. Bundesliga / 2023/2024:

```json
{
  "scope": {
    "included_match_ids": ["3895107", "3895292", "3895348"],
    "observed_match_ids": ["3895107", "3895292", "3895348"],
    "observed_match_count": 3,
    "observed_event_count": "459"
  },
  "counts": {
    "pressured_pass_attempts": "32",
    "pressured_pass_completed": "28",
    "pressured_dribble_attempts": "1",
    "pressured_dribble_completed": "1",
    "pressured_actions": "33",
    "successful_pressured_actions": "29"
  },
  "press_resistance_rate": {"status": "observed", "value": 87.87878787878788}
}
```

His pooled recovery counts remain Tackle `"1"`, Interception `"1"`, Ball Recovery
`"16"`. All his per90 values remain unsupported with explicit exposure reasons.

Tim Breithaupt, ID 51825, Augsburg / 1. Bundesliga / 2023/2024; actual pooled
`recovery['Ball Recovery']` entry:

```json
{
  "status": "observed",
  "count": "2",
  "match_ids": ["3895348"],
  "zone_counts": [{"zone": 1, "count": "1"}, {"zone": 4, "count": "1"}],
  "unknown_zone_count": "0",
  "per90": {
    "status": "available",
    "available": true,
    "value": 4.473902236951118,
    "reasons": [],
    "numerator_match_ids": ["3895348"],
    "denominator_match_ids": ["3895348"],
    "aligned_minutes": 40.233333333333334
  }
}
```

Breithaupt's 42 actor events belong to that one match. His Interception count is
`"1"` with per90 2.236951118475559; Tackle remains missing, not zero. Press is
3 completions / 4 passes (75%), no dribble attempts (dribble percentage null).

Adam Hložek, ID 28239, has included matches 3895107, 3895292 and 3895348 but actor
events only in the first two; the third is an explicit bench exposure record.
Match 3895292 retains 31.966666666666665 aligned minutes, Ball Recovery count
`"2"` / per90 **5.630865484880084**, and Tackle count `"1"` / per90
**2.815432742440042**. His pooled rates remain null because 3895107 has an open
final-whistle stint. No match measurement is fabricated for the bench appearance.

Mahmut Küçüksahin (316245) has 8 observed events in 3895348, one pressured pass
completed (100%), no dribble attempts, missing recovery entries and unsupported
aligned minutes. Wider delivered minutes remain 0.0 with the zero-minute/source
ambiguity flag. Stenzel (8934) and Kilian (32253) retain the same zero-minute warning.

Across all profiles, **exactly four match/category per90 values and two pooled
category per90 values** remain available, preserving D2B's conditional cases.
Every other unsupported value stays null. No minute denominator comes from
season aggregates, event-first/last timestamps, assumed match lengths or corrections.

## Relationship to the existing frontend contract

| Existing `soccer-scorecard/v1` | D2C diagnostic contract |
|---|---|
| Exporter accepts assembled `ScorecardResult` | Builder accepts validated D2B `MatchAudit` |
| Top-level `players` with fixed flat per-context fields | Nested `profiles`, match records, pooled windows and exposure evidence |
| Per-component presence and source minute/status fields | Explicit observed/missing/undefined/unsupported states and reason lists |
| No source match-ID windows or zone arrays | Exact profile/match numerator and denominator IDs, by-zone observations |
| Known component minutes must agree | Wider delivered minutes and aligned match minutes are deliberately separate |
| Fixed passing block and calibration declarations | Progression explicitly not assessed; no implied calibration claim |
| Strict Python/JS version, field and unit checks | Different version and `production_schema_compatible=false`; existing validator rejects it |

Both preserve canonical identity and exact decimal-string IDs/counts. This shared
encoding does not make the schemas interchangeable. `export_scorecard`,
`scorecardAdapter.js` and `rawScorecardView.js` are unchanged. No diagnostic result
is cast into v1, no validator is loosened, and no production data file is written.

Future React work needs a separate version-specific validator/loader and an
explicitly selected diagnostic mode; canonical browsing; visible provisional and
scope labels; match-versus-pooled views; zone rendering; and clear N/A reasons,
zero-minute warnings and conditional per90 descriptions. It must not silently
fall back to demo or production data or flatten incompatible windows together.

## Regression, integrity and publication boundary

Focused Python tests include exact int64 identity, duplicate/scope rejection,
per-match/pooled counts, attempt-weighted percentages, observed-zero/missing/N/A
states, exposure safety, provenance, immutability, deterministic output and no
production compatibility claims. Actual D2B input tests check Xhaka, Hložek,
Breithaupt, the zero-minute actors and conservation across all 82 profiles.

`python -B -W error -m unittest discover -s tests -q` passed **443 tests**:
417 existing plus 26 focused D2C tests, including all four real-data checks.
The recursively enumerated frontend JavaScript suite passed **67 tests, 0 failures**.
No real-data tests were skipped in this checkout. `git diff --check` and new-file
whitespace/path checks pass.

All 11 Parquet SHA256 values match both the pre-work inventory and the D1B values
referenced by D2A/D2B:

| Preserved input | SHA256 check |
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

All 111 pre-existing fingerprinted files remain unchanged, including the frontend,
existing scorecard/v1 exporter/validator, backend formulas, identity contracts,
D2B/D2A diagnostics and M4A checklist. Only `src/provisional_profiles.py`,
`tests/test_provisional_profiles.py` and this report are new, untracked files.
Branch remains `integration-foundation`; HEAD remains
`cdb3d9c4c73073ef9481b278aa7170d3acbf33f5` and `main` remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. No tracked or staged changes, public
JSON, branch/worktree creation, commit, push or deployment.

Before any React publication, review this diagnostic contract, implement and test
its separate consumer, and explicitly authorize the data integration. Source
completeness, independent identity/context evidence, broader exposure alignment
and any statistical policy remain separate production requirements. They do not
invalidate the scoped provisional diagnostic. D2C changes no deployed website,
existing production exporter, identity gate, metric formula or scoring policy.
