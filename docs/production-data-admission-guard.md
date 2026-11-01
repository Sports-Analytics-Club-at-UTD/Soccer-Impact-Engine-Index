# Default-deny production data admission

Current update: final 2015/16 ratings publication was explicitly approved in the
2026-10-31 implementation request. The guard now admits one exact public release
in addition to the unchanged heatmaps. See [current delivery and verification](public-ratings-production-delivery.md).
The report below records the preceding demo-only boundary and remains historical evidence.

Both Vite configurations disable automatic public-directory copying and use
`frontend/build/productionDataAdmission.js`. Existing admitted inputs are pinned
by path and SHA256: three original `public/team/` PNGs, fictional demo JSON and
the explicit synthetic five-attribute fixture. This is a build inventory, not a
new dataset/asset redistribution approval. New public assets require review.

Unapproved structured-data imports, public assets, private/development sources,
raw/url variants and unsupported asset formats fail admission. Output checks
reject disallowed extensions, known nonpublication bytes, real canonical data
envelopes and invalid font/static fingerprints, including renamed or late-copied
payloads. The final output directory is inspected after writing. Environment
variables and self-declared approval fields cannot authorize publication.

Local observation JSON and the real-player endpoint remain outside distributable
assets. The endpoint is installed only for loopback development, not production
preview. Route visibility alone is insufficient: inspect actual output files.
No publication flag or guard pin is changed for setup or testing.

From `frontend/`:

```powershell
npm run build
npm run preview:single
npm run test:packaging
```

The first build writes `dist/`; standalone output is HTML plus the three original
PNGs in `preview/`. Packaging tests use temporary outputs and include an HTTP
preview check, requiring permitted loopback access. Where networking is denied,
`node scripts/runTests.mjs packaging --offline` explicitly excludes that check;
report its pending status, never call the subset full HTTP acceptance. Both
filesystem builds and output-admission checks remain independently runnable in a
writable external output directory. Do not change permissions or use a different
transport to evade an execution restriction.

See [test inventory](test-suite-inventory.md) and
[private provisioning](private-local-provisioning.md). Source-only tests contain
invented rejection payloads. Exact real-byte and frozen-score checks require
separate authorized inputs. Nothing here enables real-player production delivery.
