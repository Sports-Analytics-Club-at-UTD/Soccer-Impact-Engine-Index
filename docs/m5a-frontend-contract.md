# M5A: frontend foundation and raw scorecard contract

## Scope and import provenance

M5A imports the existing React frontend from the already-fetched
`origin/vibhor-dev` at `e7bf65868cd5f9b05aca52122577cff881a4f35d`.
The integration baseline is `c1cacae`, which includes M4B0 and committed M4A.
No contributor branch was merged. All 36 source blobs under `frontend/` were
copied without staging; manifests, lockfile, demo JSON, styles and binary assets
are preserved. Four imported text files have intentional integration changes:

- `src/App.jsx`: a visible global demo-only notice; existing component flow stays.
- `src/lib/data.js`: its comment now forbids treating raw measurements as the
  demo percentile shape; runtime loading/calculations are unchanged.
- `scripts/parquet_to_json.py`: a warning marks its old converter as unsuitable
  for M4B0/production; its executable behavior is preserved and was not run.
- `README.md`: a leading demo/integration-status note.

Imported file inventory (paths relative to `frontend/`):

| Area | Imported files |
|---|---|
| Root | `.gitignore`, `README.md`, `index.html`, `package.json`, `package-lock.json`, `vite.config.js`, `vite.single.config.js` |
| Scripts | `scripts/make_mock_players.mjs`, `scripts/parquet_to_json.py` |
| React root | `src/App.jsx`, `src/main.jsx`, `src/styles.css`, `src/content.js` |
| Components | `src/components/About.jsx`, `Archetypes.jsx`, `Description.jsx`, `Footer.jsx`, `Hero.jsx`, `Nav.jsx`, `PlayerCard.jsx`, `Radar.jsx`, `Search.jsx`, `Teams.jsx`, `ui.jsx` (all under `src/components/`) |
| Libraries/data | `src/lib/archetypes.js`, `src/lib/data.js`, `src/lib/hooks.js`, `src/lib/search.js`, `src/data/players.json` |
| Public assets | `public/clips/.gitkeep`, `public/players/.gitkeep`, `public/team/.gitkeep`, `public/team/spatial_Barcelona.png`, `public/team/spatial_Bayer_Leverkusen.png`, `public/team/spatial_Paris_Saint-Germain.png`, `public/teams/.gitkeep` |

New files are `src/frontend_export.py`, `tests/test_frontend_export.py`,
`frontend/src/lib/scorecardAdapter.js`, `frontend/tests/scorecardAdapter.test.js`
and this document. No existing M1-M4B0 source, tests or policy document changes.

## Existing frontend assumptions: demo only

`App.jsx` mounts Nav, Hero, Description, Archetypes, Search, Teams, About and
Footer, with theme/local-storage and reveal behavior. It does not load a backend
API. `lib/data.js` imports 16 fictional records from `src/data/players.json`.
The mock generator uses seeded fictional names and percentile values; it is not
run by M5A. Demo row shape is `{id, name, team, position, minutes, photo, pct}`;
`position` is CB/DM, `photo` is currently blank and `pct` has T/I/C/P/LB/REC axes.
The old converter creates sequential `id` values and loses competition/season;
it cannot export the new canonical contract.

| Consumer | Existing behavior/assumption | Real-data implication |
|---|---|---|
| `lib/archetypes.js` | `overall` rounds the arithmetic mean of available T/I/C/P/LB percentiles (empty ->0). `classify` chooses the highest positional archetype axis including REC; ties keep first; >=90 gives `+`, >=75 gives minus, otherwise Standard. | These remain fictional demo calculations, not approved Index/tiers/archetypes. |
| `lib/search.js` | Searches `name` using normalized tokens/typo distance, with OVR as a match tie-breaker. | Name searching can be adapted, but selection needs full context and OVR tie-breaking cannot carry over. |
| `Search.jsx` | CB/DM tabs only; ranks by descending OVR, shows top three and numbered lists; selects by demo `id`. Existing placeholder banner identifies fictional data. | Do not use raw metrics to manufacture this ranking or collapse transfers. |
| `PlayerCard.jsx` | Reads `name/team/position/photo/minutes/ovr/archetype/pct`; non-CB label assumes DM. Rounds axes and uses values as bar widths; `minutes.toLocaleString()` assumes a number. Warns below demo `MIN_MINUTES=1000`. | Requires explicit missing-value and role support; OVR/archetypes/bars need approved scoring. The demo warning is not backend eligibility. |
| `Radar.jsx` | Five percentile axes, divides by100; missing/falsy values become zero with a 0.04 minimum radius. Labels use rounded values. | Missing raw measurements must not go through this path or be plotted as zero/percentiles. |
| `Archetypes.jsx` / content | CB/DM archetype lists and percentile descriptions. | Broader roles and real claims need deliberate future changes. |
| `Teams.jsx` | Uses static `content.js` team notes/image slots, not player scorecards. | Imported PNGs and placeholders do not establish verified spatial metrics/360 coverage. |

The demo loader does not import the scorecard adapter. The scorecard adapter
does not import demo JSON, OVR or archetype helpers. There is no fallback from a
failed/empty real payload to fictional players. No real data is connected to
React in this milestone. No photos, player ratings or rankings were generated.

## Versioned JSON schema: `soccer-scorecard/v1`

The pure Python interface is `export_scorecard(assembled_result)`. It accepts an
already-assembled `ScorecardResult`, not a Parquet, raw event frame or an
unversioned frontend demo object. It returns this JSON-compatible envelope:

```text
{
  schema_version: "soccer-scorecard/v1",
  measurement_type: "raw_metrics",
  metadata: {
    canonical_keys: ["player_id", "team", "competition_name", "season_name"],
    integer_encoding: "decimal_string",
    fields: { <each field>: {kind, unit, component} },
    coverage_status: "unverified",
    limitations: [<the three explicit contract limitation statements>],
    passing_reference: null | {
      scope: <nonblank string>, declared_complete: true,
      independently_verified: false
    }
  },
  players: [<flat canonical raw-scorecard records>]
}
```

This diagram describes a schema, not a real player JSON artifact. All record
fields listed below are required on the wire; optional absent M4B0 descriptors
are emitted as null. Payload/metadata/record/definition fields are allowlisted;
unsupported additions require a deliberate version/contract change. The
JavaScript parser rejects unsupported versions and substituted units/semantics.
`fields` is the complete field-definition map exported by both adapters, not a
caller-controlled metric interpretation.

### Identity and numeric encoding

`player_id`, `team`, `competition_name`, `season_name` are the canonical identity.
IDs are positive signed-int64 **decimal strings**, including small IDs. This
avoids JavaScript Number rounding above 2^53-1. Counts and `matches` also use
nonnegative signed-int64 decimal strings uniformly; they retain numeric meaning
through `kind="integer"` and their units. There are no leading zeros or inferred
row-number identities. Minutes, per90 values, percentages and weighted passing
values are finite JSON numbers or null. The name/role descriptors are strings or
null; `matches` is a decimal string or null. No photo field is introduced.

Both adapters use M2A's declared Marseille/Caen normalization; other context
labels remain exact. Duplicate normalized keys are rejected. Python sorts by
numeric ID and then team/competition/season; JavaScript uses BigInt and
locale-independent code-point comparison to retain that order. Transferred
players and multiple seasons remain separate records. Same-name players remain
distinct IDs. The JS result adds `context_key = JSON.stringify([player_id, team,
competition_name, season_name])` for future React keys/selection; this derived
full-context key does not replace the stable player ID.

### Exact field/unit mapping

In addition to identity and `player_name`, `position_group`, `minutes`, `matches`,
records contain all M4B0 component columns. Original meanings are unchanged.

| Fields | Kind / unit |
|---|---|
| For each `recovery_tackle`, `recovery_interception`, `recovery_ball_recovery` prefix: `_count` | Integer string / events, separate event types |
| Each recovery prefix: `_per90`, `_minutes` | Number / events/90min and minutes |
| Each recovery prefix: `_rate_status`, `_present` | Status string / status; boolean / source-row presence |
| `pressured_pass_attempts`, `pressured_pass_completed`, `pressured_dribble_attempts`, `pressured_dribble_completed`, `pressured_actions`, `successful_pressured_actions` | Integer strings / events |
| `pressured_pass_completion_rate`, `pressured_dribble_completion_rate`, `press_resistance_rate` | Numbers / percent (0-100), not percentile ranks |
| `press_minutes`, `press_present` | Number / minutes; boolean / presence |
| `prog_attempts`, `prog_passes`, `third_cross` | Integer strings / events |
| `value_sum` | Number / difficulty_weighted_yards (source pitch-distance convention) |
| `prog_passes_p90`, `third_cross_p90` | Numbers / events/90min |
| `prog_completion_pct` | Number / percent (0-100) |
| `pass_value_p90` | Number / difficulty_weighted_yards/90min |
| `passing_minutes`, `passing_rate_status`, `passing_present` | Number / minutes; status string; boolean / presence |
| `passing_difficulty_scope`, `passing_difficulty_complete` | String / reference_scope; boolean / caller_attestation |

Passing values are not goals/probabilities. No unit conversion, rescaling,
normalization, metric calculation or statistical scoring occurs in either
adapter. Raw recovery counts/per90 are not T/I/REC percentiles. Clearances are
unavailable; press percentages are not P percentile ranks; Level A progression
is not full Level B/360 line breaking; Ball Recovery is not an overall recovery
rating. No raw measurement is mapped to the legacy radar axes.

## Missingness, validation and provenance

- Pandas missing values, including valid NaN rate values, become JSON null.
  Infinity, complex/container values, invalid counts/IDs, nonnumeric quantities
  and percentages outside 0-100 fail. Strict `json.dumps(..., allow_nan=False)`
  is exercised in tests. Callers must also use strict JSON serialization.
- An absent component has `_present=false` and all its values/status/provenance
  null. A present row may have N/A rates; its nonmissing observed counts remain
  decimal strings. Observed zero is `"0"` for counts or `0` for numeric metrics.
- Presence flags cannot be null. Recovery/passing status is retained and checked
  against source missing/zero/positive minutes. Known minutes must agree across
  sources; missing exposure is not filled from another source. No minimum-minute
  or action threshold is applied.
- Passing rows require a nonblank matching reference scope and a true declared
  completeness flag. Sample/diagnostic or missing/mismatched calibration fails.
  A declaration does not independently verify calibration, reporting coverage,
  identity completeness or exposure alignment. Empty passing input may retain
  reference metadata at envelope level without inventing player observations.
- Envelope limitations state: source-row presence does not establish complete
  source coverage; calibration completeness is caller-attested, not independently
  verified; no complete production population or approved scoring is claimed.
  Coverage stays `unverified`; opaque assembly diagnostics are not exported as
  verified facts. No scope, fingerprint or completeness evidence is invented.
- Structural validation does not replace upstream identity, metric and source
  validation. Inputs and returned nested metadata do not share mutable state.

## Adapter usage and safe display

```python
import json
from src.frontend_export import export_scorecard

payload = export_scorecard(assembled_result)
json_text = json.dumps(payload, allow_nan=False, ensure_ascii=False)
# No automatic file write or production dataset generation.
```

```javascript
import { parseScorecard, displayMetric } from "./lib/scorecardAdapter.js";

const model = parseScorecard(receivedPayload); // explicit input, no demo fallback
const player = model.players[0];
if (player) {
  const metric = displayMetric(player, "press_resistance_rate");
  // metric: {value, unit, text, chartValue}; missing -> text "N/A", chartValue null
}
```

`parseScorecard` returns a fresh model, preserves exact metrics/metadata, and
raises `ScorecardPayloadError` for invalid/unsupported payloads. `displayMetric`
keeps raw values/units, renders finite numbers to at most two decimals, and never
turns null into zero. A large integer count remains exact display text; its
`chartValue` is null above Number.MAX_SAFE_INTEGER instead of a rounded number.
Other chart values are finite raw values, not scaled percentile axes. There is
no plotting, overall rating, archetype, tier or UI wiring in this module.

## Verification

```sh
python -B -m unittest discover -s tests -v
python -B -W error -m unittest discover -s tests -q
node --test frontend/tests/scorecardAdapter.test.js
```

The new Python/JS tests cover actual M4B0 synthetic outputs, exact identity,
transfers/seasons/homonyms, deterministic order, full int64 IDs/counts, all metric
families, presence, zero/null, malformed schemas/scalars, provenance, immutable
inputs and the absence of invented scores. A bounded direct Python-export to
JS-parse check also validates shared field definitions/units and an int64 ID.
No real production player JSON is generated and no raw extraction is rerun.

Both required backend commands passed all 276 tests (246 existing plus 30 new
export tests). Offline Node tests passed 31 cases, including an automated
Python-export-to-JavaScript regression using the existing Python environment.
All six Parquet SHA256 fingerprints match the pre-work baseline; earlier
milestone tracked files, main refs and staging are unchanged. Import comparison
confirms 32 of 36 frontend blobs remain byte-identical, with only the four
documented edits above.

The imported production build is **NOT RUN**: local Vite/React dependencies are
not installed. Offline Node adapter tests do not validate the React build or
browser rendering. No dependencies were installed/downloaded; manifests and
lockfile remain identical to the fetched source. A future approved dependency
installation is needed to run `npm run build` and browser checks.

## Remaining blockers and M5B requirements

The complete trusted lineup spelling crosswalk and verified metric-specific
event/exposure coverage are still missing for a complete real player dataset.
M1-valid recovery/minutes deliveries are not M3A/M3B outputs and do not establish
source identity completeness. Passing needs verified complete calibration and
aligned reporting coverage. Primary-pool complete 360 Level B data, Joseph's
alternative model's Miscontrol/Dispossessed losses and an integrated clearance
metric remain unavailable. No fabricated data supplies those gaps.

M4A comparison groups, eligibility thresholds, percentiles, FIFA-style ratings,
tiers, components, weights and missing-component scoring policy remain pending
team approval. The demo's OVR/archetype calculations and 1000-minute warning
provide no approval for real scoring.

M5B can consume verified bounded raw measurements through this contract without
scoring: explicitly choose demo versus real mode, never silently fall back;
display name, full context, role, minutes, matches, raw metric values/units,
presence and coverage limitations. Replace demo-ID selection and OVR search
tie-breaking with canonical context selection and a documented non-scoring
ordering. Support CB/DM/CM/GK/unknown roles without relabeling them as DM, provide
N/A states and unit-aware measurements, and keep unverified samples labeled.

M5B must not reuse the current percentile radar, top-three ranking, OVR, archetype
or tier UI for raw metrics. Those sections require either explicit removal from
real mode or later approved scoring inputs. Team spatial views need their own
verified contract. Run production build/browser checks once dependencies are
available, including null/empty/error modes and context selection for transfers.
The adapters are ready for future real-metric integration; complete production
data and approved scoring are not supplied by M5A.
