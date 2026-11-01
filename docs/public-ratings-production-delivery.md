# Approved 2015/16 public ratings delivery

Implemented in an isolated managed worktree from refreshed `origin/main`, commit
`01a36ae` (2026-10-31 client date). No commit, push or deployment was performed.
The original checkout's private files, untracked files and research artifacts
were read without modification.

## Approval and release scope

The implementation request explicitly states: “Our team has explicitly approved
publishing the real-player ratings on the Soccer Impact Index website.” This
release implements that final-ratings scope only. It does not change approval
flags in historical research packages or grant permission to publish them.

The only newly admitted asset is
`frontend/public/data/player-ratings-2015-16-v1.json`:

| Property | Value |
|---|---|
| Schema / release | `soccer-public-ratings/v1` / `2015-16-v1` |
| Profiles | 691 |
| Complete Formula B OVRs / incomplete | 686 / 5 |
| Strict leaderboard members | 124 MID / 107 CB |
| Uncompressed size | 1,431,543 bytes |
| gzip size, Node default compression | 119,605 bytes |
| SHA256 | `9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e` |

The minified JSON includes canonical player identity, retained full name,
2015/2016 season, clubs/leagues, primary/secondary and comparison positions,
five full-precision ratings and percentiles, Formula B OVR/status, badge
eligibility, authoritative leaderboard eligibility/exclusion reasons, attribute
coverage/missingness warnings, supported-minute and observed-fixture counts,
and general methodology/coverage disclosures. Public reference version
`frozen-mid-cb-2015-16/v1` names the unchanged existing MID/CB references; no new
population is fitted. Counts and formula/eligibility versions are included.

It excludes raw events and datasets, per-match observations and fixture lists,
measurement numerators/denominators, exact measurements, raw action counts,
reference members and statistics, private package manifests/fingerprints, file
paths, research receipts and diagnostic outputs. This is a separate projection,
not a renamed private package.

## Implementation

- `scripts/export_public_ratings.py` reads the existing validated local Formula B
  adapter and selects public fields. It writes with exclusive creation and never
  overwrites a release. It does not fit a reference, rescore attributes or change
  the authoritative strict eligibility decision.
- `src/lib/publicRatingsRelease.js` pins the reviewed path, size, hash and scoped
  approval record. The production admission plugin adds exactly this asset to
  its inventory. Automatic public-directory copying, private import denial,
  embedded-payload scans and final on-disk inspection remain enabled. A flag or
  environment variable cannot admit another dataset.
- `src/lib/publicRatingsDelivery.js` fetches the same-origin static JSON, rejects
  HTTP/MIME failures or changed bytes, and validates the field allowlist, counts,
  Formula B arithmetic, eligibility and badge consistency. Failures display an
  error and Retry, without a fictional fallback.
- `App.jsx` always selects the real-player interface in production. Development
  loaders and fictional/synthetic tools are behind a development-only import,
  so their player modules are absent from the production bundle. Stale demo
  environment/query settings cannot select fictional production players.
- `RealPlayerExperience.jsx` is the existing unified local experience moved into
  shared components with injectable delivery. Its local wrapper still uses the
  private adapter and validator. Navigation, OVR, discovery and badge helpers
  move to shared libraries, with compatibility re-exports for local callers.
  Formula B and its eligibility predicate remain unchanged.
- The shared five-attribute card retains its ratings, radar, OVR and badges. For
  the public projection it renders coverage disclosures instead of unavailable
  private measurement details. The existing comparison and navigation components
  are reused. Arpit's Teams component, descriptions and all three PNG bytes are
  unchanged. The existing experimental stylesheet moves to `src/realPlayers.css`.
- `.gitignore` admits exactly the approved public JSON; other local public data
  stays excluded. Tests and their reviewed inventory are extended for this
  release. Historical guard documentation is retained with a current-status note.

## Vercel and HTTP delivery

The baseline has no tracked `vercel.json` or local linked-project metadata.
Its existing Vercel-compatible configuration is the normal frontend Vite build;
`vite.single.config.js` explicitly identifies itself as a separate sharing build.
The new `frontend/vercel.json` records the same Vite framework, `npm run build`
and `dist` output, plus `nosniff` and immutable caching for the versioned JSON.
It adds no API, function or rewrite. The Vercel project root should remain
`frontend`. These properties follow the [Vercel configuration reference](https://vercel.com/docs/project-configuration).

Production requires Node/npm and the committed reviewed package; Python and
private research files are unnecessary. The guard emits the JSON to
`dist/data/player-ratings-2015-16-v1.json`, which Vercel serves as a static asset.
Hash routes preserve player/comparison links without a server-side player API.
Future releases must use a new filename/version and reviewed fingerprint;
immutable release URLs must not be repurposed.

Both normal and sharing builds emit the same approved JSON. The sharing output
contains HTML plus `data/` and `team/` assets and must be served over HTTP; copying
only its HTML is insufficient.

## Verification

- `npm run test:public`: **197 passed, zero failures/skips**, including both
  actual guarded builds, HTTP preview checks, admission attack cases and public
  contract tests. The reviewed test inventory is updated, not bypassed.
- `npm run build`: passed. Output: 23 files, 2,106,065 bytes.
- `npm run preview:single`: passed. Output: 5 files, 2,172,682 bytes.
- The clean worktree builds successfully without private research inputs.
- Exact projection comparison against the validated original adapter preserved
  all 3,455 attribute ratings/percentiles and all 691 OVR/eligibility records.
  All 691 identities, transfers and coverage warnings are retained by projection.
- Real production-preview browser checks confirmed:

| Player | Display OVR | Badge/status checks |
|---|---:|---|
| N'Golo Kanté | 83.08 | Three Gold attribute badges; eligible |
| Toni Kroos | 77.00 | One Silver and two Gold attribute badges; eligible |
| Kalidou Koulibaly | 82.42 | Three Gold and one Silver attribute badges; eligible |
| Sereso Geoffroy Gonzaroua Dié | 92.00 | Limited Data, not ranked, no badges |

- Every exported badge decision was tested against the existing unrounded
  percentile thresholds and strict eligibility. MID/CB leaderboards have 124/107
  members in OVR order. The five incomplete profiles retain OVR N/A.
- Accent-insensitive player search, player cards, paired Kanté/Kroos comparisons,
  mobile menu navigation/closure and absence of horizontal overflow at 390px
  passed. All three Teams heatmaps decoded successfully in the browser.
- A deliberately tampered HTTP response triggered the fingerprint error; Retry
  recovered after restoring the approved response. No demo fallback appeared.
- Actual HTTP preview returned JSON 200 with the exact approved hash. HTML,
  fonts and pinned heatmaps loaded. Observation/private endpoint requests did
  not return JSON; Vite preview's HTML SPA fallback is not a data API.
- Guard regressions still reject unknown data imports/raw/url variants, renamed
  payloads, embedded private envelopes, fake approval flags and late output
  copies. New checks reject changed release bytes and renamed public packages.
- No browser JavaScript runtime errors occurred. The existing missing favicon
  produced an unrelated 404 during the initial preview visit.
- `git diff --check` passed. No scoring implementation, reference population,
  eligibility policy, Teams description or heatmap was edited.

Logs, exact parity receipt and desktop/mobile screenshots are retained outside
the source tree at
`C:/Users/Ayush/.codex/visualizations/2026/11/01/01a194a0-639e-7691-a923-bdb089972b38/`.

The full private research suite was not run in this source-only worktree: its
separately provisioned inputs/test sources are intentionally absent. Exact
release parity was instead checked against the authorized original adapter.
No deployment was made, so live Vercel project settings, CDN headers and the
eventual deployed domain remain post-deployment checks. There is no implementation
blocker; the production-ready artifacts are verified locally.

## Reproduction and next pull request

From `frontend/`: `npm ci --no-audit --no-fund`, `npm run test:public`,
`npm run build`, `npm run preview:single`, and `npm run preview`.

For an authorized custodian reproducing the release to a **new** temporary path:

```powershell
python -B scripts/export_public_ratings.py --source-root <authorized-research-checkout> --output <new-output-path>
```

Compare its exact bytes/hash with the committed package; do not overwrite frozen
research or the immutable release to resolve a mismatch.

Recommended PR branch/title: `codex/public-real-ratings` /
“Serve approved 2015/16 player ratings in production”. Include the public JSON,
exporter, shared UI/library changes, guard/release pins, Vercel configuration,
ignore exception, updated tests/inventory and current documentation. Exclude
private inputs, observations, `dist`, `preview`, dependencies and external
verification artifacts. Review the scoped JSON and hash together before merge.
No Git staging, commit, push or deployment has been performed.
