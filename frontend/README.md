# SAC Midfielder/Defender Index

## Integration status: explicit demo and raw modes

The default demo UI uses fictional players and illustrative percentiles, OVR and
archetypes. Raw mode loads the existing M5A contract into a separate search and
measurement-card experience, without demo scoring or charts. Do not replace demo
JSON with backend measurements or run the legacy converter for production.
See [the frontend contract](../docs/m5a-frontend-contract.md) and
[M5B integration](../docs/m5b-react-metric-integration.md). No production player
JSON is supplied; structural validation does not certify source coverage.

Single-page site for the UTD Sports Analytics Club scouting model.
Vite + React. Deploys to Vercel with no configuration.

## Run it

```bash
npm install
npm run dev            # local site at http://localhost:5173
npm run build          # production build into /dist (what Vercel runs)
npm run preview:single # one self-contained file at preview/index.html
```

## Deploy to Vercel

1. Push this folder to a GitHub repo.
2. In Vercel, choose **Add New → Project** and import the repo.
3. Vercel detects Vite automatically (build command `npm run build`, output `dist`). Click **Deploy**.

Every push to `main` redeploys.

## Where to edit things

| What | File |
|---|---|
| All page text, nav labels, team panels, About Us members | `src/content.js` |
| Archetype names, descriptions, tier cut-offs (90 / 75) | `src/lib/archetypes.js` |
| **OVR formula** (placeholder: mean of the 5 percentiles) | `overall()` in `src/lib/archetypes.js` |
| Minutes warning threshold (1000) | `MIN_MINUTES` in `src/lib/data.js` |
| Hero title lines | `LINES` at the top of `src/components/Hero.jsx` |
| Colors for dark and light mode | the top of `src/styles.css` |

### Images and clips

Put files in `/public` and reference them from `src/content.js` with a leading slash.

| What | Folder | Set it in |
|---|---|---|
| Hero football clip (MP4) | `public/clips/` | `HERO.videoSrc` |
| Team spatial visualizations | `public/teams/` | each team's `images[].src` |
| Team member photos | `public/team/` | `ABOUT.members[].photo` |
| FIFA 16 player photos | `public/players/` | the `photo` field per player (see below) |

Any slot left as `""` shows a labelled placeholder.

## Loading raw scorecards without replacing the demo

With dependencies already available, choose the mode explicitly in PowerShell
before starting Vite (restart after configuration changes):

```powershell
$env:VITE_PLAYER_DATA_MODE = "raw"
npm run dev
```

Unset mode defaults to `demo`; `VITE_PLAYER_DATA_MODE=demo` explicitly selects
the original demo. Other values, including a blank configured value, fail.

Raw mode requests `data/scorecard.json` relative to Vite's `BASE_URL`, corresponding
to `public/data/scorecard.json` in a future deployment. Only supply an explicitly
verified, appropriately scoped `soccer-scorecard/v1` export through the M5A
adapter. No file is created there by the application. Missing/invalid data shows
an error or empty state, never fictional players. Keep synthetic fixtures under
tests, and do not publish them at this asset path.

Do not run `parquet_to_json.py` against the project datasets: it expects approved
percentiles, uses sequential IDs and overwrites the demo. Preserve
`src/data/players.json`. Raw mode retains all canonical contexts, observed role
groups and N/A values; it does not fill the legacy T/I/C/P/LB/REC radar axes.

## How archetypes are assigned (demo only)

Each player gets **one primary archetype**: whichever of their position's archetypes has the
highest percentile. Tier by that percentile: **+** ≥ 90, **−** 75–90, **Standard** below 75.
Ties go to whichever archetype is listed first in `ARCHETYPES`.
Off-ball dominance is team-level only and appears in the Teams section.
