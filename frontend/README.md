# SAC Midfielder/Defender Index

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

## Swapping in the real data

Browsers can't read parquet, so convert it to JSON before deploying:

```bash
pip install pandas pyarrow
python scripts/parquet_to_json.py path/to/players.parquet
```

1. Open `scripts/parquet_to_json.py` and edit `COLUMN_MAP` so the right-hand names match your parquet columns.
2. Run it. It overwrites `src/data/players.json`. Commit that file.
3. Delete `scripts/make_mock_players.mjs` (it only generates the fictional placeholder players).
4. Remove the "Placeholder data" banner at the bottom of `src/components/Search.jsx`.

The site expects **percentiles (0–100) vs positional peers**, not raw counts, for:
`T` tackles, `I` interceptions, `C` clearances, `P` playing under pressure, `LB` line-breaking passes,
and `REC` ball recoveries (used by Sweeper and Ball-Winning Midfielder; not shown on the card).

Positions must be `CB` or `DM`; anything else is dropped.

## How archetypes are assigned

Each player gets **one primary archetype**: whichever of their position's archetypes has the
highest percentile. Tier by that percentile: **+** ≥ 90, **−** 75–90, **Standard** below 75.
Ties go to whichever archetype is listed first in `ARCHETYPES`.
Off-ball dominance is team-level only and appears in the Teams section.
