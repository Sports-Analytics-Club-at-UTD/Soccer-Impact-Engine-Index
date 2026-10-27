# D2D — diagnostic real-player frontend

Status: local diagnostic integration; NOT YET PRODUCTION-VERIFIED.

## Mode and boundaries

Set `VITE_PLAYER_DATA_MODE=diagnostic` explicitly. The existing default demo and
explicit raw modes retain their loaders and contracts. Diagnostic mode has its
own lazy React experience and strict `soccer-provisional-profiles/v1` adapter.
It reuses the existing navigation, fonts, theme tokens, section heading and
angular panels, with scoped responsive CSS.

The opening notice reads **DIAGNOSTIC — PROVISIONAL REAL DATA**. No OVR,
percentile, tier, archetype, rating conversion or radar is displayed for these
profiles. Progression / line-breaking reads **Not yet assessed**. Demo's five
rating axes, including Clearances, are unchanged; the diagnostic recovery counts
are a separate measurement family.

## Explicit local import

Use **Choose diagnostic JSON** to select a local D2C export. File reading,
schema validation, search and rendering run entirely client-side. No fetch,
upload, browser persistence, automatic scorecard loading or demo fallback is
used. Invalid/replacement imports remove the previous model before validation;
a generation token prevents a stale read from restoring cleared data.
The file must be nonempty and at most 16 MiB. Reloading clears the import.

The separate adapter rejects incompatible versions, fields, units and
provenance; duplicate canonical identities (including the two existing team
aliases); noncanonical signed-int64 decimal-string IDs/counts; contradictory
match windows, exposure states or per90 denominators; inconsistent zones,
counts, percentages and pooled totals; fabricated rating fields; and unsupported
completeness claims. BigInt arithmetic preserves exact IDs and count totals.
Object property order is immaterial.

These checks establish structural consistency, not authenticity of an arbitrary
local file. The contract retains contributor-reported identity lineage,
event-derived match context and `authoritative_feed_complete=false`.
Production identity/evidence gates and metric formulas are unchanged.

## Browsing and measurements

Search names, observed variants, team, competition, season or ID. Search folds
accents for discovery only; it never creates identity mappings. Browse order is
canonical numeric player ID followed by context labels, not performance rank.
Player selection uses the complete player/team/competition/season key.

Choose pooled observations or an individual match. Match search includes only
players with observed actor events in that match; bench-only exposure does not
fabricate a metric profile. No missing match falls back to pooled values.
Pooled membership includes the player's associated lineup exposure matches.

Profiles display successful tackles, interceptions, ball recoveries, raw
3 × 3 zone counts and unknown zones; pressured pass/dribble attempts and
completions; combined successful actions and press-resistance percentages.
N/A distinguishes missing measurements and zero-attempt undefined rates from
observed zero counts. An absent zone entry is shown as —, not an invented count.

Per90 appears only when D2C supplies aligned, positive match-window exposure.
Withholding reasons remain visible. Wider-scope delivered minutes are identified
separately and never used as a denominator. Observed activity with zero delivered
minutes receives an explicit warning. Percentages/per90 display up to three
decimal places; exact count/ID strings are never rounded.

## Reproduce the local preview

From the repository root, choose an existing writable directory **outside this
repository** for `$previewDirectory`, then generate a new JSON file:

```powershell
$previewDirectory = Read-Host 'Existing external preview directory'
python -B scripts/export_diagnostic_profiles.py `
  --output (Join-Path $previewDirectory 'd2d-provisional-profiles.json') `
  --events data/validation/drive-raw-review/statsbomb_team_events.parquet `
  --crosswalk data/processed/player_name_crosswalk.parquet `
  --minutes data/validation/arpit-2026-10-21/player_minutes.parquet `
  --lineups data/raw/statsbomb_lineups.parquet `
  --metadata data/validation/arpit-match-context-review/match_metadata.parquet `
  --scratch-dir $previewDirectory
```

The helper requires all five explicit input paths and an explicit new external
JSON output. It rejects outputs anywhere inside the repository (including public
assets/data), missing parents, other extensions and existing files. It uses the
existing D2B projected Arrow streaming collector with bounded event retention
and temporary on-disk uniqueness tracking, then the unchanged D2C builder.
The default four windows are 3895107, 3895292, 3895320 and 3895348; explicit
`--match-ids` can select other diagnostic windows. The source scan establishes
local collection membership, never independent authoritative completeness.
No ingestion, download, Parquet output or production JSON is performed.

Start the website:

```powershell
Set-Location frontend
$env:VITE_PLAYER_DATA_MODE = 'diagnostic'
npm run dev -- --host 127.0.0.1 --port 5173
```

Open the printed localhost URL and import the generated file. Set the environment
value to `raw` for existing raw mode; remove it or set `demo` for the existing
demo. No environment file is committed. Stop the server with Ctrl+C.

## Verification

- Python: `python -B -W error -m unittest discover -s tests -q` —
  **447 passed**, versus 443 previously; four new output-safety tests.
- JavaScript: recursively enumerate every `*.test.js` under `frontend/tests`
  and pass the file list to `node --test` — **99 passed**, versus 67 previously.
  The 32 new tests include actual Python-generated synthetic D2C payloads,
  int64 IDs, counts, schema/provenance rejection, duplicate identity, scope and
  zone conservation, weighted pooled rates, missing/unsupported per90,
  observed zero versus undefined rates, zero-minute warning, local file rejection,
  search/selection, and no demo/network/rating imports.
- Local builds: default demo, raw and diagnostic `npm run build` passed;
  diagnostic `npm run preview:single` passed. Real profiles were never placed in
  public assets or either generated build.
- The helper generated **82 profiles**, **four matches**, **9,202 observed events**
  in an external 986,910-byte JSON. The JavaScript adapter accepted all 82.
- Browser: actual external file imported; Xhaka pooled counts were 1 tackle,
  1 interception, 16 ball recoveries and 29/33 successful pressured actions
  (87.879%). Hložek match 3895292 showed 2 recoveries, 5.631 per90 and 31.967
  aligned minutes; his pooled 3 recoveries retained withheld per90.
  Kücüksahin's zero-minute warning, invalid-schema alert, empty search and
  clear-import/no-fallback state were checked.
- Desktop dark/light and mobile light screens were inspected; 390px and 320px
  viewports had no horizontal document overflow. Shared navigation and headings
  rendered. No captured console warnings/errors.
- `git diff --check` passed. Nothing staged.

Repeat manually when reviewing: opening notice/import; Xhaka pooled profile;
Hložek pooled versus match 3895292; zero-minute/missing profile; nonexistent
search/match; invalid replacement import and clear; keyboard navigation;
dark/light and narrow-screen navigation. Cross-browser and screen-reader review
beyond these local checks remains useful.

## Integrity and Git scope

All 11 existing Parquets match both the pre-work SHA256 inventory and D1B records:

| Input | SHA256 | Result |
|---|---|---|
| `data/processed/player_minutes.parquet` | `9701ec4a74b1a75ee6094f08619c40b26f6d6f103d64a23ca2802448351e931b` | PASS |
| `data/processed/player_name_crosswalk.parquet` | `a250ac8074967aad3b1fdcd35a849584658ac333a4049d1de3845f443d2397e7` | PASS |
| `data/processed/recovery_per90.parquet` | `056f94b0bd49bc707e5d00181d0b85654cd076e5dc3bc09e1a6c121cd530ee4d` | PASS |
| `data/raw/statsbomb_lineups.parquet` | `dfb6e2f0adfb1ec25c879b26feb3616b8683c64e152657f098edc20aa1635be2` | PASS |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | `01f1bb2650df4f793971465eefad49eefcd41a302789b5c5009cf7355a4b1694` | PASS |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | `7a546348b2c391d32221456fab259d639910d13c8e672ba030e6d30b38cab61f` | PASS |
| `data/validation/arpit-match-context-review/match_metadata.parquet` | `1b1de360e0f31c49aabd43d065f95fe0762d29a31ea2bcba21b54571b86f3b47` | PASS |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | `5600f1250a3bd7fcf9d12a9d11ecac4ae9d39cd58898d6e6df1e5d4d1aa1830e` | PASS |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | `5b53d544662826206511e2d2c532297160b781f84958b2acf615195590f82012` | PASS |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | `497fa459e1ee99f758ed37d405d69285af5e6759306851456d03fde8c4025625` | PASS |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | `ec12fdd2340fb125671f4996abdac510c3dc6d81555848792520ce5df2519eb8` | PASS |

Of the 114 pre-existing fingerprinted files, only
`frontend/src/lib/playerDataMode.js` changed. Backend formulas, provenance gates,
raw/demo adapters and components, existing documents and the M4A checklist remain
byte-for-byte unchanged. No real diagnostic JSON exists in the repository.

New files:

- `frontend/src/components/DiagnosticExperience.jsx`
- `frontend/src/diagnostic.css`
- `frontend/src/lib/diagnosticAdapter.js`
- `frontend/src/lib/diagnosticView.js`
- `frontend/tests/diagnosticIntegration.test.js`
- `scripts/export_diagnostic_profiles.py`
- `tests/test_diagnostic_export.py`
- `docs/d2d-diagnostic-frontend.md`

Pre-existing untracked inputs remain:
`data/processed/player_minutes.parquet`,
`data/processed/player_name_crosswalk.parquet`,
`data/processed/recovery_per90.parquet`, `data/validation/`, and
`docs/m4a-team-approval-checklist.md`.

Branch remains `integration-foundation`, HEAD
`60afffadafb482505f94eb94f8bafd905697bf4d`; main remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. No staged files, branch/worktree
creation, merge, reset, commit, push or deployment.

## Remaining limitations

This is a local preview of a limited provisional event collection. It does not
establish full-season coverage, independently verified match/identity provenance,
complete exposure, statistical comparisons or production-ready scoring.
Unsupported per90 stays withheld. Production promotion still needs the existing
evidence requirements, appropriate coverage/exposure validation, and separately
approved scoring methodology. No scoring decision is made by D2D.

