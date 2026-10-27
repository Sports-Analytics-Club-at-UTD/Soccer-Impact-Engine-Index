# D3F — frontend rating and archetype alignment

October 27, 2026. Frontend presentation preparation only, on `integration-foundation`.

## Ready contract

The future card consumes `player.attributes[attribute_id] = { rating, percentile }`.
Both fields are independent, explicit numbers or null; omission is unavailable.
This is an internal presentation contract, not a production export schema or an
adapter for D3E `AttributeSlot.score`. It does not certify evidence or eligibility.
Existing identity, provenance, raw and diagnostic validators remain authoritative
and unchanged. A future approved integration must provide validated inputs.

| Canonical identifier | Card label | Short key |
|---|---|---|
| `tackles` | Tackles | T |
| `interceptions` | Interceptions | I |
| `recoveries` | Recoveries | REC |
| `press_resistance` | Press Resistance | P |
| `line_breaking_passes` | Line-Breaking Passes | LB |

`ratingCard.js` retains supplied finite ratings in [1,100] at full JavaScript
number precision. Radar geometry and bar widths use that value; final labels use
`Math.round` to integers. Null, omitted, nonnumeric, nonfinite and out-of-range
values display N/A. Missing axes have no dots or bars; an incomplete radar omits
the filled polygon entirely, while retaining the grid and available points.
No minimum-radius floor creates artificial scores. Defensive N/A presentation
is not backend input validation or authorization to publish.

Percentiles must be finite numbers in [0,100]. Only `percentile` determines the
primary archetype. Highest available eligible positional archetype wins; equal
values retain the existing list order: CB T, REC, I, P, LB; DM T, I, REC, P, LB.
Existing supported roles stay CB/DM; this change adds no role or eligibility
policy. Gold is >=90 (+); Silver is >=75 and <90 (−); below 75 or no eligible
percentile retains Standard. Classification uses unrounded precision. Missing
rating does not erase a separately supplied percentile, and a high rating cannot
create Gold. Future cards display Gold/Silver names; demo symbols remain unchanged.

For example, this is an invented unit-test input, not a real-player score:

```js
const player = {
  position: "CB",
  attributes: { tackles: { rating: 61.23456789, percentile: 95.1 } }
};
// Tackles label 61, bar 61.23456789%, Stopper Gold; other ratings N/A.
// OVR is always null / N/A — POLICY NOT FINALIZED.
```

`PlayerCard` defaults to this explicit rating contract. Search passes `demo`
explicitly. `Radar` receives the prepared attribute values and never reads `pct`.
No real-rating import or new mode is enabled. Real cards do not inherit the
fictional demo's 1000-minute warning as a new eligibility policy.

## Compatibility and deliberate demo exception

The existing fictional JSON is untouched. `DEMO_METRICS`, `classifyDemo` and
`demoOverall` retain historical chart values, archetypes and illustrative OVR.
Its chart still uses Clearances (C) and its existing five percentiles; REC remains
a separate archetype input. Migrating this chart to ratings or changing its OVR
would require new sample assumptions, so D3F implements the correct five-rating
contract separately. No C-to-REC copying and no percentile-to-rating relabeling
occurs. The demo now identifies its profile as fictional percentiles and its
OVR as Demo OVR. All raw and diagnostic loading, search, measurements and trust
boundaries remain unchanged; neither mode starts consuming the rating contract.

## Blocked by policy and source verification

OVR is unconditionally withheld for future rating cards, even with five complete
ratings or caller-supplied `ovr`/`overall`. No equal, weighted or highest-rating
formula is selected. The historical demo mean is explicitly demo-only.

The frontend can display a future explicitly supplied line-breaking rating but
creates no real score or conversion. Progressive passes, raw counts/per90,
percentages, DRI aggregate ratings and backend candidate outputs are never used
as substitutes. Missing fifth-attribute evidence stays missing. D3D's missing
target-season 360 evidence and final line-breaking definition remain blockers.

Separate defensive attribute transforms, final press transform/action threshold,
metric-specific populations/eligibility and source/scope verification remain
required upstream. DRI component percentiles are not approved separate FIFA
ratings. D3E remains synthetic-only and has no direct frontend export adapter.
Its older discussion of unresolved player tier application is superseded only
for this frontend archetype contract by the D3F instruction: archetype tiers use
percentiles. Backend scoring formulas and tier helpers are untouched.

## Validation

Run `node --test frontend/tests/*.test.js` from the repository root. The new
rating regressions include server-rendered card/radar output using the existing
Vite esbuild dependency, independence, exact attribute order, Gold/Silver
boundaries and ties, missing/invalid scores, precision, no OVR or passing fallback,
and every existing fictional row. Existing raw/diagnostic regressions include
Python exporter contract checks. No backend changes require a separate full
Python run.

Build both regular and single-file configurations for demo, raw and diagnostic
with `VITE_PLAYER_DATA_MODE` explicitly set. These checks generate ignored local
build output only. No deployment, staging, commit, push or branch changes.

### Results and preserved state

- JavaScript: **112 passed**, zero failures/skips (99 existing + 13 D3F).
- Regular and single-file Vite builds: all **six** demo/raw/diagnostic builds pass.
- `git diff --check` and new-file whitespace checks pass.
- All **11 protected Parquet SHA256 fingerprints** match the inventory recorded
  in D3E. Tracked datasets, backend source/tests, fictional JSON, mode loader,
  diagnostic experience and approval checklist have no Git diff. Pre-existing
  untracked data and checklist remain present and untouched.
- Branch stays `integration-foundation`; HEAD stays
  `4288930481736de4d2254912245a8968029fad63`; main stays
  `179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. Nothing staged or committed.

Exact modified files:

- `frontend/README.md`
- `frontend/src/components/PlayerCard.jsx`
- `frontend/src/components/Radar.jsx`
- `frontend/src/components/Search.jsx`
- `frontend/src/lib/archetypes.js`
- `frontend/src/lib/data.js`

Exact new D3F files:

- `frontend/src/lib/ratingCard.js`
- `frontend/tests/ratingCard.test.js`
- `docs/d3f-frontend-rating-alignment.md`
