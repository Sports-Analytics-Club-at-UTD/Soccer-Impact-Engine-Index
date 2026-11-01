# Authorized private/local provisioning

Source access alone does not authorize receipt of data. The team must approve
the recipient and transfer channel separately. No private payload belongs in
the source handoff, public Git, build output or this document. Do not regenerate,
replace, normalize line endings or edit the frozen files to resolve setup errors.

## Required runtime layout

An authorized custodian provisions these existing files unchanged, relative to
the repository root:

```text
data/derived/private-five-attribute-v2/
  manifest.json
  PRIVATE-EXPERIMENTAL-scores.jsonl
  player-measurements.jsonl
  frozen-reference.json
  measurement-facts.jsonl
  validation.json
  summary.json
```

The seven files total **128,625,033 bytes**. Exact individual sizes and SHA256
checksums are in [private-runtime-checksums.json](private-runtime-checksums.json),
which contains metadata only. From the root, run:

```powershell
python -B -m scripts.verify_local_inputs
```

All seven must report `match` and the command must exit zero. A missing or
mismatched file fails; obtain the correct approved original from its custodian.
For an independent one-file check, use
`Get-FileHash -Algorithm SHA256 data/derived/private-five-attribute-v2/manifest.json`.
The runtime adapter still independently validates its unchanged manifest pin,
artifact fingerprints and measurements. This receipt does not approve publication.

Activate the declared Python environment before starting Vite. Open the loopback
homepage as described in the root README. Missing/invalid inputs cause the fixed
development endpoint to return HTTP 500 and the UI to show a data-validation
error. There is no fictional or synthetic fallback. `?view=demo` explicitly opens
the separate fictional demonstration.

## Additional test evidence

The seven runtime files are **not** a complete research-test fixture package.
Full/private suites also read the retained OVR v1/v2 comparison and eligibility
packages under `data/derived/private-ovr-comparison-v1/` and `private-ovr-comparison-v2/`,
the optional legacy `frontend/public/data/bundesliga-observations.json`, sealed
source/phase-3/Bundesliga/progressive-passing evidence under `data/source-evidence/`,
`data/derived/` and `data/validation/`, original/processed Parquets under `data/raw/`
and `data/processed/`, and compiled contributor evidence under
`docs/review/arpit-comparison-2026-10-28/`. The private verification methods retain
their exact file/hash requirements; missing evidence must fail or be reported
incomplete, never replaced with invented inputs. Ask the custodian for the
specific packages required by the selected checks, not a blanket data download.

The separate immutable Joseph contributor Git reference is documented in
[source-handoff.md](source-handoff.md). No data fixture should be fetched,
copied or regenerated automatically by a setup/test command.

Public/synthetic commands need none of these payloads. Production demo builds
also need no private data. `.gitignore` protects the current data/evidence stores;
it does not grant access or guarantee safe publication. The production admission
guard is a separate default-deny boundary and remains unchanged.
