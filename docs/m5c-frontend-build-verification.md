# M5C: frontend final review and verification

## Scope and result

Final review performed on `integration-foundation`, baseline HEAD
`713c0ce`. Both explicit production modes compile, all 340 Python tests and
67 JavaScript tests pass, and protected dataset fingerprints match D1.
Compilation and Node tests do **not** establish successful browser rendering.
Limited manual Brave checks are now recorded below as user-reported observations
from the Integration Lead, separately from automated results. No deployment has
been performed. No further UI modifications were made during this final review.

**INDEPENDENT BROWSER AUTOMATION BLOCKED / NOT RUN.** The previous computer-use attempt
stopped because it could not reliably determine the Windows browser URL for
policy enforcement. This review respects that restriction: no computer-use,
browser-control, alternative browser automation or workaround was attempted.
The Integration Lead's manual desktop/mobile/404-and-retry checks do not imply
complete responsive or accessibility acceptance. Unverified items remain explicit.

Evidence categories in this report are **AUTOMATED TESTED**, **MANUALLY OBSERVED
(USER-REPORTED)** and **NOT VERIFIED**. Source-code review is identified as such;
it is not substituted for browser execution.

## Dependencies

The preceding M5C attempt successfully ran the authorized
`npm ci --no-audit --no-fund` inside `frontend/`, adding 73 locked packages.
The existing `frontend/node_modules` installation was present and usable in this
continuation. No reinstall, additional dependency or automation package was needed.
`package.json` and `package-lock.json` remain unchanged. Vite reported version
5.4.21 for both builds.

## Authorized team-member correction

The existing `ABOUT.members` entry in `frontend/src/content.js` now displays
**Ayush Mendhe** instead of Ayush. Its Engineer role, description and blank photo
are unchanged. All other members are unchanged, and the list still contains
exactly five members with exactly one Ayush Mendhe entry. The obsolete
`add last name` comment was removed. No authorship or history was modified.

`About.jsx` renders `m.name` from this data source; no duplicate display entry was
added. A Node import/assertion checked the corrected entry, and comparison with
the Git baseline confirmed that all other member entries/fields are unchanged.
The only other content changes are the three intended spatial image mappings.
Both production builds below ran after all intended frontend edits.

## Navigation readability: reviewed and preserved

Current desktop navigation links are **15px** with **0.12em** letter spacing;
SAC INDEX brand text is **18px**. Existing fonts, colors, active underline, hover
effects, container spacing and the 960px menu breakpoint are preserved. Mobile
menu links retain their existing 13px size. No further size/spacing changes were
made in this review. Earlier loaded-font advance estimates indicated room at
320px through desktop widths; those estimates are not browser measurements.
The lead's manual navigation and approximately 400px mobile observations are
recorded separately below, without claiming a comprehensive device matrix.

## Team spatial image integration and asset inventory

**AUTOMATED TESTED / SOURCE REVIEWED:** each team has exactly one populated image
slot, the first Spatial dominance slot. Paths, nonempty team-specific alt text,
asset existence and unchanged binary content were checked. Pressing zones and
Off-ball dominance slots are identical to the baseline, with empty sources;
existing descriptions and captions are also unchanged.

| Team | Public asset / URL | Git inventory |
|---|---|---|
| Paris Saint-Germain | `frontend/public/team/spatial_Paris_Saint-Germain.png` / `/team/spatial_Paris_Saint-Germain.png` | Already tracked, unchanged |
| Barcelona (FC Barcelona) | `frontend/public/team/spatial_Barcelona.png` / `/team/spatial_Barcelona.png` | Already tracked, unchanged |
| Bayer Leverkusen (Bayer 04 Leverkusen) | `frontend/public/team/spatial_Bayer_Leverkusen.png` / `/team/spatial_Bayer_Leverkusen.png` | Already tracked, unchanged |

All three assets were committed with M5A (`8f1e77a`); **there are no new PNG
assets to stage**. They are retained in the intended asset inventory, and binary
comparison against HEAD confirms the data inside them was not altered. They
also matched the previously supplied image attachments. Built copies match the
tracked assets.

`TeamImage` resolves the configured public path through Vite's base URL. Its
team/source-specific key resets error state when selecting another team. A
missing source or `onError` returns the original `Photo` placeholder. CSS scoped
to Teams uses `object-fit: contain`, retaining the full image's proportions inside
the existing 16/10 box; the placeholder overlay is removed only for the real image.
No source-image crop or shared Photo change was made. The lead reports all three
images loading; missing-image fallback execution and exhaustive crop/layout checks
are not independently browser-verified.

Placeholder team notes and generic caption accuracy remain future polish items;
they were deliberately left unchanged rather than duplicating these images into
other metric categories or changing the underlying analysis.

## Demo and raw production builds

From `frontend/`, verification used PowerShell:

```powershell
$env:VITE_PLAYER_DATA_MODE = 'demo'
npm run build
$env:VITE_PLAYER_DATA_MODE = 'raw'
npm run build
```

The actual verification wrapped these temporary settings in `try/finally`, saving
and restoring any prior value. The variable was initially absent and was removed
after both builds; no default-production configuration was written to the repo.

| Mode | Result | Evidence |
|---|---|---|
| Explicit `demo` | PASS | Vite transformed 64 modules; generated HTML, JS, CSS, fonts and existing assets; 27 output files |
| Explicit `raw` | PASS | Vite transformed 64 modules, including RawExperience and its dependencies; generated 27 output files |

The second build replaces the generated `frontend/dist` output, so the final
local output is **raw mode**. Inspection of its generated entry confirms the
literal raw-mode selection passed to the mode validator and lazy loader.
Both lazy experience chunks are emitted by the current shared loader, including
the existing demo chunk. This is **not** an exclusive raw-bundle claim. Existing
Node tests verify raw dependency isolation and no fictional fallback. Limited raw
404/retry behavior has been manually reported by the lead; populated raw
rendering remains unverified. No bundle refactor was made merely to change this
output layout.

## Generated output inspection

Read-only checks of the final raw output confirmed:

- `dist/index.html` exists with a module-script entry and stylesheet reference;
  both referenced files exist.
- Four JavaScript bundles exist, including raw and demo lazy experience chunks;
  inspected relative JS imports resolve to generated files.
- All 14 external CSS/font references resolve; inline SVG data-URI filter
  references were correctly treated as embedded content, not missing disk files.
- No JSON file, test module or fixture file is present in the output.
  In particular, no production `scorecard.json` was generated and
  `frontend/public/data/scorecard.json` does not exist.
- Existing fictional demo player JSON remains unchanged. No new fictional raw
  player profiles or real production player exports were created.
- `frontend/dist` and `frontend/node_modules` are ignored, and nothing is staged.

Output existence/link checks cannot establish layout, visual quality, HTTP
behavior, successful React mounting or accessibility. No screenshots were taken
by this automated review. The lead reports screenshot-supported manual checks;
these are not independent browser-automation results.

## Regression tests

From the repository root:

```powershell
python -B -W error -m unittest discover -s tests -q

$jsTests = @(
  Get-ChildItem frontend/tests -Recurse -Filter '*.test.js' |
  ForEach-Object { $_.FullName }
)
node --test $jsTests
```

| Suite | Result |
|---|---|
| Python, warnings as errors | **340 tests passed** |
| Existing/new frontend Node suites, explicit PowerShell discovery | **67 tests passed** |

These suites cover identity/evidence, metric assembly/export, v1 validation,
mode boundaries, loading failures, canonical-context selection, raw display
models and the Python-to-JavaScript contract. No expectations were weakened.
No additional test framework was installed. The small name-label change was
verified directly rather than adding an implementation-mirroring unit test.

## Parquet and Git integrity

Expected fingerprints were parsed directly from the six labeled SHA256 rows in
`docs/d1-identity-evidence.md`; they were not replaced with newly computed values.
Every protected file matched its exact recorded fingerprint:

| Protected input | Result |
|---|---|
| `data/processed/player_minutes.parquet` | MATCH |
| `data/processed/recovery_per90.parquet` | MATCH |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | MATCH |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | MATCH |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | MATCH |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | MATCH |

No Parquet was regenerated or overwritten. Existing backend formulas, D1 identity
contract, scorecard adapters, dependency manifests and demo player data are
unchanged. The active branch and HEAD remain `integration-foundation` / `713c0ce`;
`main` and `origin/main` retain `179ad5e`. No branch/worktree was created, no merge,
reset or clean operation was performed, and nothing was staged, committed or
pushed. Generated dependencies/output remain local and ignored.

## MANUALLY OBSERVED — USER-REPORTED Brave verification

The following were reported by the Integration Lead as actually observed,
supported by screenshots and manual observations. They were **not independently
performed by browser automation** in this review.

### Demo desktop

- Homepage and navigation rendered correctly.
- Player search/selection worked; the player card, radar and illustrative metrics
  displayed, and the fictional-data disclaimer was visible.
- The Teams section rendered and the PSG, Barcelona and Leverkusen spatial PNGs
  each loaded for the corresponding team.
- About Us displayed Ayush Mendhe.
- Light and dark themes both rendered correctly.

### Mobile, approximately 400px viewport

- Homepage rendered without obvious overflow.
- Hamburger menu and navigation links worked.
- A player profile opened with its radar and metrics.
- The profile closed correctly, the overlay disappeared, and Search remained
  usable. This is not a comprehensive keyboard/focus or device-matrix result.

### Raw missing-data path

- The raw-metric interface loaded with its data limitations visible.
- Missing `scorecard.json` returned HTTP **404**, as expected.
- No fictional demo players, demo rankings, OVR or radar appeared.
- Retry was clicked. Brave's Network panel confirmed a **new** scorecard request,
  which again returned HTTP **404**. Retry is therefore supported by a reported
  network observation, not merely by the presence of a button.

The missing scorecard is an expected data limitation, not a reason to add a
fictional JSON file. No such file was generated or published.

## NOT VERIFIED — remaining acceptance checklist

| Area | Still required |
|---|---|
| Real raw data | Rendering of a real verified scorecard and populated raw search/selection have not been browser-tested |
| Raw alternatives | Empty and malformed responses are not fully browser-tested; network and validation variants need browser acceptance beyond their automated helper tests |
| Raw context/measurements | Verify transfers, same-name actors, multiple seasons, dynamic roles, exact IDs/counts, null/zero distinctions, units and calibration text with an appropriately scoped valid response |
| Accessibility | Screen-reader behavior is not tested; comprehensive keyboard/focus behavior has not been independently verified; formal contrast audit is not complete |
| Responsive coverage | Comprehensive device/browser/zoom matrix, intermediate widths, long labels and extreme IDs remain outside the limited approximately 400px check |
| Image fallback | Confirm the coded placeholder path with a missing/failed image response; do not modify tracked source images to test this |
| Release/data | Public hosting is not deployed, full production player coverage is unavailable and the scoring framework still awaits team approval |

Any future bounded fixture response must remain in a separately authorized test
mechanism; never publish synthetic scorecards under public/production data.

## Exact working-tree inventory and recommended staging set

No unrelated tracked changes were found. The intended commit preparation set is:

```text
frontend/README.md
frontend/src/components/Teams.jsx
frontend/src/content.js
frontend/src/styles.css
docs/m5c-frontend-build-verification.md
```

The first four paths are modified tracked files; this report is a new untracked
document. The three PNGs listed above are already tracked and unchanged, so they
need no new staging action. All six pre-existing local Parquets remain untracked
and must be excluded. `dist/` and `node_modules/` remain ignored. This is a
recommendation only: no files have been staged, committed or pushed.

## Release limitations and readiness

The reviewed frontend changes, documentation and automated regressions are ready
for an M5C integration commit; no commit was made. Limited demo/mobile and raw
404/retry behavior are supported by the lead's manual observations. This does not
constitute complete accessibility acceptance, populated raw-data acceptance or
production readiness. Static hosting has not been deployed or verified.

Before any hosting release, choose the intended build mode, configure the hosting
root/build/output and Vite base path for that destination, then complete the
remaining acceptance checklist. A raw production dataset additionally requires authoritative
identity crosswalk evidence, verified source/exposure/calibration coverage and
the appropriate release review. Scoring policies remain unapproved; compilation
does not create ratings, rankings or a completed Soccer Impact Index.
