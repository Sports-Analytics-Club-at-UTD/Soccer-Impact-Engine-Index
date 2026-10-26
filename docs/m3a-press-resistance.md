# M3A: pressured actions and completion rates

This in-memory interface integrates Pratyush's action definitions with shared
identity. It performs no file I/O and creates no rankings, tiers or final index.

## Source and preserved definitions

Reference: origin/pratyush-dev at
`77c1639935fb9e1988dd9112c094277973ca0bcd`,
`src/metrics/press_resistancev2.py`: action filtering/classification/aggregation
(357-466), action totals and combined rate (507-527). V1 was inspected as well;
neither branch version has substantive tests. `src/metrics/press_actions.py`
adapts only those action calculations into pure functions, without importing the
original scripts or executing their writers/scoring code.

An attempt is a Pass or Dribble with under_pressure equal to True. Missing
pressure does not select an action. A Pass completes only when pass_outcome is
null. A Dribble completes only when dribble_outcome equals the exact string
Complete. Missing dribble outcome is an attempt without a completion. Set pieces
remain included; this is not Joseph's broader retention/loss metric.

The four independent integer counts are:

- pressured_pass_attempts / pressured_pass_completed
- pressured_dribble_attempts / pressured_dribble_completed

Derived columns:

| Column | Calculation |
|---|---|
| pressured_actions | pass attempts + dribble attempts |
| successful_pressured_actions | completed passes + completed dribbles |
| pressured_pass_completion_rate | 100 * completed passes / pass attempts |
| pressured_dribble_completion_rate | 100 * completed dribbles / dribble attempts |
| press_resistance_rate | 100 * successful_pressured_actions / pressured_actions |

All rates are percentages, not 0-1 fractions. A zero denominator yields N/A.
The combined rate is action-weighted, not the mean of the two component rates.
Unknown counts are rejected, not zero-filled. A genuinely observed pass-only
player has zero observed dribble attempts and N/A dribble rate; this does not
manufacture metrics for players with no observed action.

Pressure/outcome storage is adapted on copies to reproduce raw V2 object/empty
semantics for pandas nullable columns. Missing pressure remains excluded;
missing pass outcome remains complete; missing dribble outcome remains
incomplete. Object fillna downcasting warnings and nullable outcome conversion
errors are avoided without changing action definitions or source inputs.

## Reusable interface

```python
from src.press_resistance import integrate_press_resistance

result = integrate_press_resistance(
    raw_events,
    trusted_crosswalk,
    selected_population,
    minutes=verified_minutes,  # optional metadata; does not qualify players
)
actions = result.identity.events
counts_and_rates = result.totals
accounting = result.accounting
```

Flow: raw-ID preflight -> pressured Pass/Dribble selection and classification ->
strict M2A resolution -> explicit selected population -> stable-ID sums -> rates
-> optional unique minutes join. IDs remain present until after validation.

| Input | Required fields |
|---|---|
| raw_events | id, player, team, competition_name, season_name, type, under_pressure, pass_outcome, dribble_outcome |
| trusted_crosswalk | player_name_raw, player_id, team, competition_name, season_name |
| selected_population | player_id, team, competition_name, season_name |
| optional minutes | player_id, team, competition_name, season_name, minutes |

Raw IDs must be unique nonblank strings, including events later excluded by the
action filter. Missing names are retained as identity problems rather than
dropped. A trusted existing player_id can resolve a missing/different display
label; conflicting supplied IDs fail under unchanged M2A rules. No player_id_x/y
merge is used. Malformed or duplicate column labels fail explicitly. Action
output names (successful, the four counts, the totals and rates) are reserved on
raw input, alongside M2A's identity output/internal names.

Canonical grouping remains player_id + team + competition_name + season_name.
Known Marseille and Caen aliases normalize consistently across every table.
Crosswalks must include verified spellings and known outsiders; they are never
constructed automatically from selected display names. No team, role or player
identity is inferred. Unknowns remain unknown even if their club is unselected.

Results:

- `identity.events`: every filtered action, with event ID, original context and
  canonical team/ID, action counts and selected/outside/unresolved status.
- `accounting`: Pass and Dribble rows containing filtered/completed counts and
  attempt/completion partitions for selected, outside_population and unresolved.
- `totals`: one row per observed selected stable context, the four counts,
  action/success totals, three rates, and optional minutes. No population grid
  or row for an unobserved player is created.

The minutes join normalizes keys, rejects duplicates/alias collisions and uses
one-to-one validation. Missing rows/values remain missing; known values must be
finite and nonnegative. Zero minutes are allowed metadata and do not change a
completion rate. No exposure, zero counts or complete coverage is inferred.
Use M1 to check the complete delivered minute/recovery contract upstream.

## Strict production versus diagnostics

Unresolved filtered actions raise UnresolvedIdentityError before aggregation,
including actions with missing player labels. The exception retains all M2A
diagnostic rows. Known resolved outsiders remain in accounting but not metrics.
Ambiguous or duplicate normalized crosswalk keys, supplied-ID conflicts and
duplicate event IDs fail explicitly.

```python
from src.press_resistance import inspect_press_resistance

diagnostic = inspect_press_resistance(raw_sample, limited_crosswalk, population)
print(diagnostic.accounting)
```

Diagnostics retain unresolved attempts and successes and return no partial
player metric table. There is no permissive production switch that drops them.
For each action type, selected + known outside + unresolved equals filtered;
the same equality is checked separately for completions. Every filtered event
has exactly one attempt indicator. Completed counts cannot exceed attempts.
Stable-ID sums and optional minutes joins must conserve all four selected counts.

Inputs, including nondefault/repeated index labels, are not mutated. Uniqueness
checks apply per call; streaming callers must enforce cross-batch event-ID
uniqueness. Conservation does not establish source completeness or crosswalk
authenticity. Completion rates from a bounded sample are sample rates.

## Existing V2 policy versus M3A scope

Original V2 selects 2015/2016 and La Liga, Premier League, Serie A and Ligue 1;
MID combines DM+CM, while CB is a separate scoring population. Full-coverage
flags are read from the recovery delivery. Its scoring script also applies
900-minute/30-action qualification, positional ranks, z-scores, ratings and tiers.

M3A documents these conventions but imports none of those population/coverage
or scoring policies. It accepts explicit contexts from any season/competition.
MID and CB action results stay distinct by player context; callers can supply
separate verified MID and CB populations to separate calls. The interface does
not infer role membership, pool leagues, assign a scoring group or rank anyone.

## Tests

```sh
python -B -m unittest discover -s tests -v
python -B -W error -m unittest discover -s tests -q
```

39 new cases cover action/outcome definitions, missing pressure and nullable
outcomes, zero denominators, combined arithmetic, explicit spelling aliases,
clubs, homonyms, transfers/seasons/competitions, existing IDs/conflicts, duplicate
events/crosswalks/minutes, unresolved diagnostics, conservation with deliberately
broken joins/aggregation, missing minutes, immutability and unobserved populations.
All 118 existing M1/M2A/M2B tests remain unchanged: 157 tests total.

## Bounded real-data verification

Read-only sources:

- data/validation/drive-raw-review/statsbomb_team_events.parquet
- data/validation/arpit-2026-10-21/player_minutes.parquet
- data/validation/arpit-2026-10-21/recovery_per90.parquet

M1 passes the revised delivery (5,576 minutes and 7,680 recovery rows), retaining
its 22 zero-minute warnings. All six original/revised/review Parquet fingerprints
remain unchanged. No dataset or metric output is written.

The sample consists of the first 8,192 rows of Parquet row group 2 (Ligue 1
2015/2016), plus the first 8,192 Premier League 2015/2016 rows encountered in that
row group. Reading 16,384-row batches projected ten columns (id, match_id, player,
team, competition_name, season_name, type, under_pressure, pass_outcome,
dribble_outcome) visited only 65,536 source rows. The 16,384-row retained sample
is not a full season, league or dataset reconstruction.

Six explicit mappings were checked for exact ID/name/context and contextual name
uniqueness in revised minutes, and corroborated in revised Ball Recovery rows:
Lassana Diarra (3181), Nicolas Alexis Julio N'Koulou Ndoubena (7472), Gnegneri Yaya
Toure (3087; exact accented source spelling used), Nicolas Hernan Otamendi (3090;
exact accented spelling used), Fernando Luiz Rosa (3054), and Joe Hart (3291).
The first two use Olympique de Marseille / Ligue 1; the remaining four use
Manchester City / Premier League; all are 2015/2016 contexts. Joe Hart is an
explicit known outsider for this check. Selection is a fixture, not eligibility.

| Action | Attempts | Completed | Selected attempts / completed | Known outside attempts / completed | Unresolved attempts / completed |
|---|---:|---:|---:|---:|---:|
| Pass | 1,031 | 702 | 21 / 17 | 2 / 1 | 1,008 / 684 |
| Dribble | 243 | 131 | 6 / 2 | 0 / 0 | 237 / 129 |
| Total | 1,274 | 833 | 27 / 19 | 2 / 1 | 1,245 / 813 |

Strict production rejected the 1,245 unresolved actions. The bounded production
test then used only the 29 event IDs resolved by the explicit mappings: 27
selected + 2 known outside, with zero unresolved. All 29 attempts and 20 successes
remained accounted for. No metric row was created for Fernando Luiz Rosa because
that exact verified spelling had no action in this sample.

| Player | Pass completed / attempts | Dribble completed / attempts | Pass rate | Dribble rate | Combined rate |
|---|---:|---:|---:|---:|---:|
| Yaya Toure (3087) | 10 / 12 | 1 / 5 | 83.333333 | 20 | 64.705882 |
| Otamendi (3090) | 0 / 1 | 0 / 0 | 0 | N/A | 0 |
| Diarra (3181) | 3 / 4 | 0 / 0 | 75 | N/A | 75 |
| N'Koulou (7472) | 4 / 4 | 1 / 1 | 100 | 100 | 100 |

Verified season minutes were attached unchanged: 2326.533333, 2671.033333, 2086
and 2968.7 respectively. They did not determine sample eligibility or rates.

### Comparison with original V2

Selected AST statements/functions were executed directly from the fetched V2
source with an in-memory read stub; no original module, writer, ranking, rating
or tier calculation was imported or run. Original selection/classification
matched all 1,274 sample actions. Original aggregation and combined-rate formulas
also matched all selected rows after aligning shared team normalization.

The original unnormalized name/team join retained only 18 selected actions; nine
Marseille actions (Diarra four, N'Koulou five) were lost despite supported names.
Shared normalization recovered those nine, yielding 27 with identical formulas.

Five raw actions named Fernando Luiz Roza did not match the verified Rosa label.
They remain unresolved; M3A does not assert their ID from spelling similarity or
the old duplicate-containing minutes delivery. The missing original spelling
crosswalk is required before resolving them. Likewise, current-label evidence
and agreement between delivered tables are not independent lineup verification.

Intentional safety differences from V2: unresolved names are retained/rejected,
not dropped; existing IDs do not acquire merge suffixes; team aliases are shared;
and absent players are not zero-filled. Missing names are routed to identity
resolution rather than removed by V2's player.notna prefilter. Action eligibility
remains pressured Pass/Dribble; trusted existing IDs can resolve nameless actors.

## Remaining limitations

The complete trusted lineup-derived spelling crosswalk remains unavailable.
Full player-level reconstruction, coverage, population qualification and scoring
remain outside M3A. Source completeness, authentic mapping evidence, role labels
and final comparison-pool policy are not established by these sample checks.
