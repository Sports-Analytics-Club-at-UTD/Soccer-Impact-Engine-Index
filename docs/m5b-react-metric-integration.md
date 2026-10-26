# M5B: real-metric React integration

## 1. What M5B implements

M5B connects the existing `soccer-scorecard/v1` contract to React loading,
canonical-context browsing and raw metric cards. It works on the committed M5A
baseline `8f1e77a`. It introduces no scoring, statistical eligibility, metric
calculation, new JSON schema, data export or production-season dataset.
Backend modules, Python export, M5A validation and metric definitions are
unchanged. The existing visual language, theme control and demo experience stay.

File inventory (relative to the repository root):

| Status | Files |
|---|---|
| Created: mode/page components | `frontend/src/components/DemoExperience.jsx`, `frontend/src/components/RawExperience.jsx`, `frontend/src/components/RawSearch.jsx`, `frontend/src/components/RawPlayerCard.jsx` |
| Created: pure helpers/loader | `frontend/src/lib/playerDataMode.js`, `frontend/src/lib/scorecardLoader.js`, `frontend/src/lib/rawScorecardView.js` |
| Created: tests/fixtures | `frontend/tests/rawIntegration.test.js`, `frontend/tests/fixtures/rawScorecards.js` |
| Created: documentation | `docs/m5b-react-metric-integration.md` |
| Modified | `frontend/src/App.jsx`, `frontend/src/components/Nav.jsx`, `frontend/src/components/Search.jsx` (demo banner only), `frontend/src/styles.css`, `frontend/README.md` |

## 2. Demo versus raw-data mode

`App.jsx` resolves the explicit mode and lazy-loads `DemoExperience.jsx` or
`RawExperience.jsx` through `playerDataMode.js`. Unknown modes display an explicit
configuration error; failed module loads display an error boundary, never a
fictional-data fallback. Raw mode's dependency graph excludes demo player data,
demo ranking/archetype calculations, the old player card and percentile radar.

Demo mode mounts the previous Hero/Description/Archetypes/Search/Teams/About and
Footer, preserving their fictional OVR, rankings, archetypes and radar behavior.
Its notice reads: **Demo data — fictional players and illustrative ratings.**

Raw mode mounts a raw-metrics introduction, loader/search/cards and limited raw
navigation/footer. It excludes the demo hero/model claims, archetype section,
top-three rankings, radar and static team spatial views. The notice reads:
**Raw player metrics — source completeness and scoring eligibility not yet
verified.** A further visible explanation states that these are raw measurements,
no overall score is available, no percentile ranking is approved, coverage may be
incomplete and missing measurements show N/A. This is not a finalized Index.

## 3. Environment configuration

Vite's `VITE_PLAYER_DATA_MODE` accepts exactly `demo` or `raw`. An unset value
defaults to demo; blank, differently cased or unknown values fail explicitly.
No repository configuration enables raw/production mode by default. This is a
Vite startup/build-time selection, not a runtime mode inferred from data quality.
Restart the dev server or rebuild after changing environment configuration.

## 4. Raw JSON loading location

`scorecardLoader.js` requests `<BASE_URL>data/scorecard.json`; a future deployment
can supply this as `frontend/public/data/scorecard.json`. Root, relative, nested
and CDN Vite bases retain their prefix. No production/public JSON or directory of
fictional scorecards is created by M5B. The loader accepts injected `fetchImpl`,
base URL and AbortSignal for offline tests.

Every successful HTTP/JSON response passes through the unchanged
`parseScorecard`. HTTP 404/server failure, network failure, invalid JSON (including
an HTML SPA fallback), unsupported schema, duplicate contexts, invalid units and
invalid provenance all fail explicitly. Errors retain their cause/code and are
rendered as an alert with a retry button. Failed loads do not return demo rows.

React starts in `loading`, then displays `ready`, `empty` or `error`. A valid empty
player array gets a distinct successful-empty message and retains its coverage
declaration. Effect cleanup aborts stale requests and guards state updates, so
responses from an unmounted/replaced request cannot populate the screen. There
is no extraction, converter invocation or data write during loading.

## 5. Canonical player context selection

All four fields remain available: `player_id`, `team`, `competition_name`,
`season_name`. Raw React list/card keys, selection state and focus-target maps
use the adapter's full `context_key`. IDs remain exact decimal strings; no
Number conversion, sequential identity or name-based selection is introduced.
Transfers, multiple seasons and same-name distinct players stay selectable.
No photo is invented. Missing/blank `player_name` displays `Player ID <actual ID>`.

## 6. Search and position filtering

`RawSearch.jsx` uses pure helpers from `rawScorecardView.js`. Search matches
available names with case/diacritic-insensitive substring matching or an exact
player ID. Name search does not resolve actor identity or infer spelling aliases.
Every result displays name/ID fallback, team, competition, season, position and
stable ID. Search/position filters preserve adapter canonical order; this is
explicitly a browse list, not a quality ranking. There is no top-three substitute.

The default position option is All. Other options are derived from observed
descriptor labels, including CM/GK/other groups. Null/blank labels are accessible
as Unspecified. Unknown roles are not inferred or excluded, and no eligibility
rule is applied. A literal verified `Unspecified` role remains distinct from a
missing descriptor through separate filter values.

Controls have visible labels; results are ordinary focusable profile buttons.
Arrow keys from search enter the browse list and move between contexts. Enter
or Space selects a focused button, moving focus to the selected card region.
Escape or Close returns focus to the triggering profile button, or search if
that button is no longer visible. Mobile cards remain in document flow rather
than introducing an untested modal/focus trap. Empty filters show a clear message.

## 7. Raw metric display mapping

`RawPlayerCard.jsx` renders the pure `rawCardModel` as labeled definition lists,
using existing surfaces, typography and grid styles. All numeric text comes from
the unchanged M5A `displayMetric`, preserving raw values and units. No rates are
calculated in React. The header shows full context, stable ID, known position,
minutes and matches, retaining N/A where unavailable.

| Category | Fields/labels |
|---|---|
| Successful tackles | `recovery_tackle_count`, `recovery_tackle_per90`, presence, source minutes and rate status |
| Successful interceptions | `recovery_interception_count`, `recovery_interception_per90`, presence, source minutes and rate status |
| Ball recoveries | `recovery_ball_recovery_count`, `recovery_ball_recovery_per90`, presence, source minutes and rate status |
| Press attempts/completions | `pressured_pass_attempts`, `pressured_pass_completed`, `pressured_dribble_attempts`, `pressured_dribble_completed` |
| Combined press counts | `pressured_actions`, `successful_pressured_actions` |
| Press completion percentages | `pressured_pass_completion_rate`, `pressured_dribble_completion_rate`, `press_resistance_rate` (percent, not percentile rank) |
| Progressive passing — Level A | `prog_attempts`, `prog_passes`, `third_cross`, `value_sum`, `prog_passes_p90`, `prog_completion_pct`, `third_cross_p90`, `pass_value_p90` |

The press/passing categories additionally show their source-row presence and
source minutes. Passing shows `passing_rate_status`, `passing_difficulty_scope`
and its declared completeness. Recovery event types are never blended.

Counts display exact decimal strings, per90 values retain events/90min and
completion percentages retain percent. Pass value displays difficulty-weighted
yards and difficulty-weighted yards/90min, with a plain-language distance
explanation. The card explicitly rejects interpretations as expected goals,
universal quality ratings or verified 360-based opponents bypassed. No clearance
field, normalized radar axis, Gold/Silver tier or overall score is supplied.

## 8. Null/zero/source-row distinction

- Absent component: Not available, with no source component row; metrics/status
  remain N/A. Presence of another component never fills it.
- Present component with observed zero: display 0, preserving integer text.
- Present component with a null per90: display N/A and use source rate status
  to explain missing or zero source minutes. Completion percentages can be
  unavailable independently of minutes when an attempt denominator is absent.
- Base/optional source minutes and matches retain missing values; no exposure
  is inferred. Large counts are displayed exactly without Number coercion.

Raw components never use `value || 0`, round null, divide counts by minutes or
recompute percentages. The v1 validator rejects NaN/Infinity in payloads; the
display helper supplies N/A for null. No chart is rendered for raw measurements.

## 9. Calibration and coverage limitations

The screen and card visibly retain `metadata.coverage_status=unverified` and the
contract's limitations. Source-row presence and schema validation do not prove
complete event coverage, identity/exposure alignment or full-season eligibility.
Passing's scope is shown verbatim as text, with **Caller-attested complete: Yes.
Independently verified: No.** for a present validated passing row. An absent
passing row shows N/A calibration, even if envelope reference metadata exists.
No completeness flag is promoted to independent verification.

## 10. Demo-only charts/archetypes/rankings

The demo stays in its own lazy module and continues to use `Search.jsx`,
`PlayerCard.jsx`, `Radar.jsx`, `lib/data.js` and `lib/archetypes.js`. Their existing
illustrative calculations apply only to fictional demo records. The raw path
does not import those modules and has no fallback to them after an error.
Static Teams visuals are demo-only and are not represented as derived from
the new raw scorecard. Demo JSON and assets are unchanged; its outdated
conversion banner now points to the separate mode rather than replacement data.

## 11. Example local development workflow

Use existing installed dependencies; do not automatically install/download them.
With the frontend as the current directory, PowerShell can select demo mode:

```powershell
$env:VITE_PLAYER_DATA_MODE = "demo"
npm run dev
```

To exercise raw loading/error states, stop the server and use:

```powershell
$env:VITE_PLAYER_DATA_MODE = "raw"
npm run dev
```

No raw file is supplied by this milestone, so an absent asset intentionally
produces an error (404 or invalid JSON for an HTML fallback). Only provide an
explicitly verified/scoped v1 export through the existing Python adapter when
the necessary inputs are available. Do not publish test fixtures or run the
legacy percentile converter, and never overwrite `src/data/players.json`.
Subpath deployment assets are resolved through Vite's configured base.

## 12. Frontend test and build status

From the repository root:

```sh
node --test frontend/tests/*.test.js
python -B -m unittest discover -s tests -v
python -B -W error -m unittest discover -s tests -q
```

New Node tests cover mode boundaries and raw dependency isolation, injected
loading/cancellation/failures, v1 validation, canonical selection/navigation,
names/IDs, dynamic positions, all metric labels/units, missingness, exact large
integers, calibration wording and immutable view models. Synthetic builders live
only under `frontend/tests/fixtures/`; they are not shipped as public player data.
Existing M5A contract and Python-to-JS compatibility tests remain in the suite.

Verification results: all **67 Node tests** pass (31 existing plus 36 new), and
both required Python commands pass all **276 existing tests**, including the
warnings-as-errors run. All six Parquet SHA256 hashes, demo JSON and package
manifests/lockfile match the baseline. Backend/adapter formulas, prior policy
documents, staging, main refs and HEAD remain unchanged. No data export or
public scorecard was created.

**BUILD NOT RUN — DEPENDENCIES UNAVAILABLE.** `frontend/node_modules` is absent;
no package installation/download or manifest/lockfile change is made. Node tests
verify helpers/contracts and import isolation, not React rendering or browser
behavior. JSX rendering, responsive layout and browser accessibility still need
production build and browser verification once dependencies are authorized and
available. No browser-tested claim is made.

## 13. Missing production inputs

The full trusted lineup spelling crosswalk and verified per-metric source and
exposure coverage still block a full real-season scorecard. Valid M1 deliveries
do not establish complete identity/coverage or supply integrated press/passing
results. Passing calibration additionally needs a verified complete, correctly
defined cohort. Complete primary-pool Level B/360 inputs, Joseph's alternative
press-model loss events and an integrated clearance metric remain absent. M5B
does not reconstruct a population, regenerate datasets or fabricate any inputs.

## 14. Requirements for M5C and approved scoring

M5C needs authorized dependency availability, production builds in both modes,
and browser checks for loading/error/empty/ready states, keyboard/focus behavior,
mobile layout and transfers/homonyms. Verified bounded inputs must retain their
scope limitations; a production-season release needs independently verified
population, source coverage, exposure and calibration evidence.

Any later scoring UI needs explicit M4A policy approval for pools, eligibility,
normalization, percentile/rating definitions, component sets, weights, tiers and
missing-component rules. Demo formulas and raw completion percentages cannot
substitute for approval. M5B is a raw-measurement integration ready for review,
not a complete Index or a scored production dataset.
