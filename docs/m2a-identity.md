# M2A: shared player identity

`src.identity` resolves event identity independently of metric formulas, roles,
minimum minutes, coverage thresholds, rankings and scoring. It performs no file
I/O, downloads or dataset writes. Population selection belongs to the caller.

## Contract

Canonical player context is **player_id + team + competition_name + season_name**.
The same player can have multiple clubs, competitions or seasons; these remain
distinct contexts. Display names are labels, not stable keys. Matching a raw name
requires an explicitly trusted spelling lookup in its full context.

| Input | Required columns | Rules |
|---|---|---|
| Events | id, player, team, competition_name, season_name | id is a nonblank string, unique within the supplied batch. Context labels are nonblank strings. player is a string or missing; unknown/blank names remain unresolved without a supplied ID. |
| Trusted crosswalk | player_name_raw, player_id, team, competition_name, season_name | Each normalized name/context key maps to exactly one ID. Distinct verified spellings can map to the same stable context. |
| Population | player_id, team, competition_name, season_name | Explicit selected contexts, unique after club normalization. Extra columns such as role/minutes are ignored, not used to infer selection. |

IDs must be positive exact integers fitting signed int64. Integral float inputs
are accepted only within exact float integer precision; strings, booleans,
fractions, infinity and missing required IDs are rejected. Output player_id uses
pandas nullable Int64, preserving integer values without float join rounding.

Events may already contain a trusted player_id. It is preserved and can resolve
an event without a name lookup. A nonmissing supplied ID conflicting with a
crosswalk match raises IdentityError. Missing supplied IDs use the crosswalk.
The caller remains responsible for the provenance of supplied IDs.

Output `IdentityResult.events` contains all input event columns, in the original
row order and with the original index (including repeated index labels). It:

- Adds or completes player_id.
- Canonicalizes team, retaining its original label in team_raw.
- Adds identity_status: selected, outside_population, or unresolved.
- Adds nullable boolean in_population: True, False, or unknown (pd.NA).
- Preserves event id and player labels, competition/season, metric columns,
  missing metric values and all rows. It does not aggregate counts or fill metrics.

`team_raw`, `identity_status`, `in_population`, and names starting with
`_identity_` are reserved on event input. Collisions and duplicate column labels
fail rather than overwrite caller data.

## Normalization and evidence

`normalize_player_names` collapses doubled apostrophes to single apostrophes and
strips surrounding whitespace; missing names stay missing. There is no fuzzy
matching, case folding, accent stripping, internal-space repair or quote repair.
Rosa/Roza and David N'Gog/David N"Gog require separate, verified crosswalk rows.
Those relationships are exercised with synthetic evidence in tests, not embedded
as production aliases or recovered from the old duplicate-containing delivery.

`normalize_team_names` applies the two existing mappings on every input table:

| Raw club label | Canonical club label |
|---|---|
| Marseille | Olympique de Marseille |
| Caen | Stade Malherbe Caen |

Other team labels and competition/season strings remain exact. No club, position
or identity is inferred from partial names or other contextual guesses.

`prepare_crosswalk` validates the lookup before any event join. A name/context
mapping to multiple IDs fails explicitly as ambiguous. Repeated normalized keys
also fail even when they repeat the same ID, including collisions created by
normalization. Callers must review repeated evidence explicitly; the resolver
does not arbitrarily keep a first row. Joins additionally enforce many-to-one
cardinality and verify event count/order after joining.

Trust is an external evidence requirement, not a claim made by this validator.
Crosswalk rows should come from verified lineup spellings or equivalent identity
evidence, preserve all supported aliases, and include known outside players if
their events are to be distinguished from unresolved names. A crosswalk built
only from selected display names is not complete evidence for exclusion.

## Unresolved versus outside

A known resolved ID/context absent from the supplied population is
outside_population. An unmatched identity has **unknown** membership; absence
from a partial spelling lookup never proves exclusion, even for a different club.

Default `resolve_events(..., strict=True)` raises UnresolvedIdentityError if any
event remains unresolved. Its `.result` retains every row and status counts for
diagnosis. `strict=False` is an explicit diagnostic mode returning those rows;
it does not make an incomplete result safe for metrics. `require_resolved()` and
`selected_events()` still raise until all identities resolve. This conservatively
blocks unknown outsiders too, rather than silently dropping a possible selected
player. There is no unresolved-to-zero conversion or allow-list.

Malformed tables, duplicate event IDs, duplicate population/crosswalk keys,
ambiguous mappings and supplied-ID conflicts raise IdentityError even in
diagnostic mode. Input tables are never modified.

## Future component interface

Requires pandas; existing M1 environments already supply it. No contributor
pipeline is imported or copied into this module.

```python
from src.identity import PLAYER_KEYS, resolve_events

# trusted_crosswalk: explicit verified spellings, including known outsiders.
# selected_minutes: caller's population, checked using M1 beforehand.
result = resolve_events(
    raw_events,
    trusted_crosswalk,
    selected_minutes[PLAYER_KEYS],
)
selected_events = result.selected_events()
# Apply the component's existing metric formula, then group by PLAYER_KEYS.
```

Recovery should resolve individual events before name-based aggregation loses
identity distinctions. Pressure should resolve its event sample before counting
actions, retaining its own pressure rules. Passing should retain event IDs for
360 joins and group player outputs by PLAYER_KEYS. These are future call sites:
no contributor formula or pipeline has been migrated in M2A.

Do not pass aggregated recovery rows as events: they lack event IDs and cannot
establish source-event uniqueness. Duplicate detection is per call; streaming
callers must enforce event-ID uniqueness across batches separately.

## Reused source conventions

Inspected directly from fetched Git objects, without merging branches:

- origin/arpit-dev at 0445f18fa1895320f0679ee84022888793fae6e7:
  `src/metrics/player_names.py` (name cleanup), `team_names.py` (two aliases),
  `player_minutes.py` (stable grouping and multiple spelling crosswalk),
  `recovery_per90.py` (context-preserving ID join).
- origin/Joseph-dev at 013c8edd5196a15ac826558f4b0964cc6f3a3e58:
  `src/metrics/scoring_common.py` (team cleanup; name-only joins and duplicate-first
  behavior are not reused).
- origin/pratyush-dev at 77c1639935fb9e1988dd9112c094277973ca0bcd:
  `src/metrics/press_resistancev2.py` (normalized temporary name lookup, stable
  final keys, ambiguity rejection and many-to-one join validation).

M2A adds fail-closed handling and separates unresolved from known outside events;
it does not reuse silent count loss, arbitrary deduplication or zero filling.

## Tests and bounded real-data check

```sh
python -B -m unittest discover -s tests -v
python -B -W error -m unittest discover -s tests -q
```

The 34 identity cases cover verified spellings, homonyms, both club aliases,
Rosa/Roza, N'Gog quote variants, multiple clubs/seasons/competitions, ambiguity,
unresolved versus outside, duplicate IDs/keys and normalization collisions,
join multiplication prevention, integer precision, input immutability, event
order/index preservation, metric missingness, supplied-ID conflicts and empty
inputs. All original 49 M1 tests remain unchanged and pass (83 tests total).

The bounded check used only these existing files, read-only:

- data/validation/arpit-2026-10-21/player_minutes.parquet
- data/validation/arpit-2026-10-21/recovery_per90.parquet
- data/validation/drive-raw-review/statsbomb_team_events.parquet

M1 passed the revised pair: 5,576 minutes rows and 7,680 recovery rows. Raw schema
inspection confirmed event IDs/names/context but no player_id. Only the first
4,096-row Arrow batch was materialized, projecting eight columns: id, player,
team, competition_name, season_name, type, under_pressure, pass_outcome. No full
raw table was loaded or copied; the 3,626,433-row raw file was streamed only for
SHA256 integrity verification.

The deliberately limited lookup used three explicit current-label mappings in
Bayer Leverkusen / 1. Bundesliga / 2023/2024:

| Name | ID | Selected for this interface check? | Sample events |
|---|---:|---|---:|
| Granit Xhaka | 3500 | Yes | 176 |
| Jonathan Tah | 8221 | Yes | 214 |
| Patrik Schick | 7044 | No | 22 |

Each exact name/ID/context was checked against revised minutes, including
uniqueness of that name in context. The two selected mappings were also checked
against revised Ball Recovery rows. These provide delivered-table consistency
evidence, not independent reconstruction of original event-to-lineup identity.
The selected two-player list is a test fixture, not a new eligibility policy.

Result: **412 events resolved consistently with the supplied mappings** (390
selected, 22 known outside); **3,684 unresolved**, with membership left unknown.
No events were dropped or multiplied; event IDs and pass-outcome missing values
were preserved. Default strict mode rejected all 3,684 unresolved identities.
This bounded sample covers three teams in one league-season and is not a
coverage estimate for the entire dataset. Club aliases and spelling edge cases
are synthetic regression coverage, not claimed as verified raw-source mappings.

## Limits and missing inputs

The original complete lineup-derived spelling crosswalk is unavailable locally.
Current display names do not recover all original spellings and cannot identify
homonyms without contextual evidence. M2A cannot prove lookup provenance,
crosswalk completeness, original actor identity, dataset completeness, role
correctness, or metric validity. It does not reconstruct unknown IDs, infer
aliases, or resolve same-context homonyms by choosing a player.

All six original/revised/review Parquet SHA256 fingerprints were unchanged.
No datasets, M1 implementation, eligibility policies or contributor formulas were
modified. The remaining integration input is trusted original spelling evidence;
future components must provide it explicitly before counting unresolved events.
