# Soccer Impact Index frontend

React/Vite local scouting website: **Home | Players | Leaderboards | Compare |
Teams | About**. Production serves the fictional demo. The loopback development
homepage serves the existing authorized real-player experiment.

## Start

Use Node 24.21.0 / npm 11.19.0 (tested) and Python 3.13.0 (tested; minimum 3.11).
Follow the [root setup](../README.md) to install and activate Python first.
The Vite adapter runs `python` from this shell.

```powershell
cd frontend
npm ci --no-audit --no-fund
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open <http://127.0.0.1:5173/>. Seven separately authorized frozen files are needed
for real-player data: [provisioning](../docs/private-local-provisioning.md).
Absent/invalid inputs yield an explicit error, no demo fallback. Use `?view=demo`
for the fictional development demo. `?view=five-attribute-experimental` retains
the legacy explicit entry into the same unified interface.

Player/comparison selections and leaderboard tabs use shareable hash links and
browser Back/Forward. Search filters, comparison selections and team choices
survive session navigation; reload restores URL identities, not all memory-only
filters. Five attributes, provisional Formula B, individual-attribute Gold/Silver
badges, strict MID/CB eligibility and Limited Data behavior are described in the
[root README](../README.md). Teams reuses Arpit's three unchanged heatmaps.

## Tests and builds

```powershell
npm run test:public    # source-only/synthetic; no private fixture required
npm run test:packaging # source-only build, negative admission and preview checks
npm run test:private   # authorized evidence; missing inputs fail
npm test              # both suites, preserving all assertions
npm run build         # dist/
npm run preview:single # preview/index.html plus three team PNGs
npm run preview -- --host 127.0.0.1
```

The test inventory rejects missing or altered required modules. See
[test source and fixture interface](../docs/test-suite-inventory.md). Where loopback
is not permitted, `node scripts/runTests.mjs public --offline` reports its HTTP
exclusion explicitly; it is not full HTTP acceptance.

The public frontend suite also invokes Python for synthetic contract validation.
Use the declared backend environment even for source-only frontend tests.
Private suites require the seven runtime inputs, local observation JSON and frozen
OVR v1/v2 parity evidence; [full prerequisites](../docs/source-handoff.md).
Legacy manual scripts `checkExperimentalIsolation.mjs`,
`checkLocalExperimentalEndpoint.mjs` and `checkProvisionalOvr.mjs` are private
acceptance utilities, not source-only checks: they need their retained historical
receipts/local paths and a running loopback server (some assume port 5173).
The portable test commands above are the contributor entry point.

Both production configurations disable automatic public-directory copying and
use the same default-deny admission guard. Only three fingerprint-pinned images
in `public/team/` are copied; fictional `src/data/players.json` and explicit
synthetic fixtures are separately pinned. `public/data/` observations, local
endpoints and real numeric payloads are excluded. No environment flag approves
publication. Actual build outputs are checked by `test:packaging`.

New files placed in `public/` are not automatically production-admitted. Any new
asset needs explicit scope/rights and guard review; image paths are
`public/team/`, not `public/teams/`. Preserve existing admitted bytes. Demo
archetypes in `src/lib/archetypes.js` are fictional, distinct from real local
attribute badges. Do not run `parquet_to_json.py` against project evidence.

## Legacy contracts and hosting

Raw, diagnostic, limited-data and synthetic-rating-preview views retain their
separate historical contracts. Their earlier no-ratings/withheld statements do
not override later local Formula B/badge approval. `VITE_PLAYER_DATA_MODE` selects
an existing contract, never publication permission; unset mode is unified in
development and fictional demo in production. Raw delivery is not provisioned
or authorized by this handoff. See [M5A](../docs/m5a-frontend-contract.md) and
[production admission](../docs/production-data-admission-guard.md).

For an eventual approved static host: project root `frontend`, build `npm run
build`, output `dist`. Configure the intended base path for a subpath host.
No deployment or real-player production delivery is enabled by these instructions.
