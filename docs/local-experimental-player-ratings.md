# Local real-player experimental website

Formula B is now the provisional project OVR in this route. See
[the Formula B integration report](provisional-formula-b-ovr.md) for current
behavior, eligibility, validation and release limitations. The no-OVR statements
and completed checks below describe the earlier five-attribute-only delivery.

Implemented on `integration-foundation`; completed by continuing the existing
adapter and UI work. This is an isolated development preview, not official
rating delivery or publication. No team approval is required for this explicitly
authorized local preview. No approval records or production privileges are
created.

## Open the preview

From `frontend/`, run:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open <http://127.0.0.1:5173/?view=five-attribute-experimental>.
The local server is running at that address after validation. Python on PATH
reads the existing package; missing or changed artifacts cause a clear error,
never fallback scores. Production/static preview deliberately cannot load this
route's real data.

## Available data and features

- **691 real canonical player-seasons:** all **686 complete** and **5 partial**
  scored profiles from the existing frozen v2 experiment. The other 1,823
  examined player-seasons have no supported scores under that experiment's
  recipient/position rules and are not shown as invented rating profiles.
- All **138 Bundesliga contributors** are included: 133 complete and 5 partial,
  including supported sub-900-minute observations. Sub-40 press projections
  retain their action samples and LIMITED DATA. PARTIAL SEASON and metric-specific
  excluded-appearance warnings remain visible.
- Search by name (accent/apostrophe insensitive), ID, club, league, primary or
  observed positions. Filter by any of the five leagues, MID/CB, full/partial
  ratings, or any LIMITED DATA warning. Lists are alphabetical, not rankings.
- A shared player-card layout displays five exact supplied ratings (rounded for
  display only), separate position percentiles, actual measurements/units,
  rational-minute evidence, primary/secondary positions, clubs, action/pass
  samples, missingness, fixtures and source fingerprints.
- The existing five-axis Radar is reused. Missing values leave labelled axes
  and points unfilled; an incomplete profile has no filled polygon.
- Two-player comparison supplies side-by-side ratings/percentiles and radars.
  Differences use first minus second only within compatible position/reference
  groups and supported attributes. Cross-MID/CB differences are N/A, with an
  explicit separate-population warning.
- Transfers have one canonical player-season card with all supported clubs.
  Milan Bisevac (3103), for example, has one Lazio/Lyon card. No club-level
  ratings or percentages are averaged.

Every real numerical page/card/comparison displays **EXPERIMENTAL PROJECT
RATINGS** and **NOT OFFICIAL EA FIFA RATINGS**. The fifth label is **Line Breaking
— Progressive Passing Proxy**, with an explicit warning that it does not verify
defensive line-breaking events. No overall rating, archetype, tier, badge or
ranking is generated for these real profiles.

## Implementation reused and extended

| File | Responsibility |
| --- | --- |
| `scripts/local_experimental_ratings.py` | Fixed-path read-only adapter; verifies existing manifest/reference/artifact hashes and exact measurement/score correspondence, then projects supported rows. Does not call a scorer or fit populations |
| `frontend/dev/experimentalRatingsPlugin.js` | Node-only Vite `serve` middleware for `/__local_experimental/five-attributes`; invokes the adapter without shell interpolation |
| `frontend/vite.config.js` | Adds development plugin, loopback binding and private-evidence filesystem denial |
| `frontend/src/App.jsx` | Adds the query route only inside `import.meta.env.DEV`; existing default and other routes remain unchanged |
| `frontend/src/dev/experimentalDelivery.js` | Separate local-only parser, pinned frozen-reference/projection checks, numeric/scope/identity validation, search and filtering |
| `frontend/src/dev/FiveAttributeExperimentalExperience.jsx` | Local fetch, discovery, pagination, selection, comparisons, loading/failure handling and required notices |
| `frontend/src/dev/experimental.css` | Existing SAC theme-token styling and responsive discovery/comparison layout |
| `frontend/src/components/FiveAttributePlayerCard.jsx` | Extracts the existing card body as `FiveAttributeCardView`; synthetic wrapper retains its original strict validator. Adds optional exact/sample/position metadata |
| `frontend/src/components/FiveAttributeComparison.jsx` | Reuses the comparison body, with optional two radars and compatible per-attribute differences. Existing synthetic wrapper remains strict |
| `frontend/scripts/checkExperimentalIsolation.mjs` | Static build/private-score scan and temporary loopback production-preview HTTP checks |
| `frontend/scripts/checkLocalExperimentalEndpoint.mjs` | Live development HTTP parity and rejection tests |

`Radar`, the existing default demo, synthetic preview, Bundesliga observations
components/asset, official delivery contracts, frozen baselines and measurement
outputs remain unchanged. The real path is separate from the synthetic contract;
real actors are not relabelled synthetic or passed through official admission.

## Frozen source and validation boundary

Source: `data/derived/private-five-attribute-v2/`.
Baseline SHA256:
`403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd`.
Manifest SHA256:
`5a8030b4a6ca06aeec81538221b07315c5644a9025915eb31c0bf2dab3cc9bc6`.

Scores and percentiles are copied from `PRIVATE-EXPERIMENTAL-scores.jsonl`, not
recalculated. Exact inputs and scopes must agree with the separately frozen
`player-measurements.jsonl`. The existing validation record must pass; hashes
also bind the frozen reference and actor/fixture fact ledger. Metadata projection
fingerprints do not create new reference populations. A future experiment needs
an explicit version/pin update; this adapter does not silently refresh baselines.

The endpoint accepts only a fixed GET with no query/path parameters. Socket
address and Host must be loopback; cross-origin and cross-site requests are
rejected. Responses are `no-store`, have no permissive CORS header and do not
publish a static asset. The development server denies direct private artifact
and Parquet paths. The plugin has no production-preview hook. The client route
and dev-only module import are compiled out of production; this is more than
hiding a navigation link.

## Completed checks

**1,016 backend tests and 190 frontend tests passed. Production build passed.**
These completed runs were preserved and inspected on resumption; no unnecessary
reconstruction or real scoring was restarted.

The live HTTP adapter served all 691 profiles with every score and percentile
equal to the frozen files. All six requested players were checked: N'Golo Kante
(3961), Toni Kroos (5574), Leonardo Bonucci (7173), Granit Xhaka (3500), Milan
Bisevac (3103) and Florentin Pogba (4802). Their source names, including source
punctuation, are preserved. Browser checks confirmed real search, transfers,
five-axis cards, partial N/A, same-role differences and cross-role warnings.

Desktop (1280×900 target) and mobile (390×844 target) were checked. At mobile,
the document and scroll width both measured 375 CSS pixels (excluding the
scrollbar), and the visualization used a single column without horizontal
overflow. The temporary viewport override was reset.

Production isolation scanned 14 text assets for 19 route, endpoint, fingerprint,
private-file and exact-score canaries, finding none. A temporary production
preview confirmed the experimental URL/endpoint do not return rating JSON. SPA
fallback may return HTTP 200 HTML; that is not an experimental API. Direct
development access to the private score file returned 403; POST, parameterized
file requests and cross-origin access were also rejected. The default browser
page still displays the original fictional-demo notice.

Evidence is under `data/validation/local-experimental-website-v1/`:
`backend.xml`, `backend.txt`, `frontend.txt`, `build.txt`, `production-isolation.json`,
`development-http.json`, `browser-verification.json`, preservation receipts and
real-card screenshots. Existing frozen artifacts and official contracts match
their pre-work hashes.

## Remaining work

**No technical blocker remains for this local preview.** Keep the loopback Vite
development server running while browsing it. No acquisition, source
reconstruction or regeneration of frozen real scores was performed.

Official website delivery remains a separate, disabled release path. It still
needs the previously documented team decisions, accepted policy/evidence scope,
an authorized production adapter/loader and explicit publication authorization.
None of those gates is required or forged for this isolated local experiment.
No official OVR, commit, push, branch switch, merge or deployment was performed.
