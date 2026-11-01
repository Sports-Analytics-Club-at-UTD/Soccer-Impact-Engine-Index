# Source-only handoff and test contract

This handoff covers the existing unified local MID/CB experiment and the guarded
fictional production demo. It does not authorize real-player publication or
distribution of provider evidence. Keep all retained research inputs unchanged.

## Environment and commands

The tested baseline is Python 3.13.0, Node 24.21.0 and npm 11.19.0. Python must be
at least 3.11. Activate the Python environment in the terminal running Vite:
the middleware and frontend contract tests invoke `python`. Direct runtime
versions are NumPy 2.1.3, pandas 2.2.3 and PyArrow 26.0.0; pytest 8.4.2 is a
separate test dependency. Use `requirements-test.txt` for verification and
`requirements.txt` for runtime. Optional historical visualization/network
packages are in `requirements-research.txt`; they are not website prerequisites.
The latter is not an acceptance claim for those historical research workflows.

The frontend lockfile is unchanged: run `npm ci --no-audit --no-fund` from
`frontend/`. Python files pin direct dependencies, not every transitive/platform
wheel. Record `python -m pip freeze` for a new validated environment before
claiming an equivalent install. Never upgrade packages to repair frozen scores.

| Scope | Root command | Frontend command |
| --- | --- | --- |
| Source-only / synthetic | `python -B -m scripts.run_backend_tests public -q` | `npm run test:public` |
| Production packaging without private data | Both frontend builds below | `npm run test:packaging` |
| Authorized evidence | `python -B -m scripts.run_backend_tests private -q` | `npm run test:private` |
| Complete assertions | `python -B -m scripts.run_backend_tests all -q` | `npm test` |

From `frontend/`, build with `npm run build` and `npm run preview:single`.
Source-only checks explicitly deselect private checks; this is not a skipped
or passing private acceptance. Private commands must be run separately after
authorized provisioning. A missing evidence file is an error; the backend runner
also returns nonzero if a selected private/full check skips. Direct `pytest tests` bypasses the reviewed inventory and must not be labelled
complete acceptance; use the inventoried runner for handoff verification.
All existing numerical/eligibility assertions remain in the full suite.

The current exact case/source catalogs, migration and fail-closed private fixture
interface are documented in [test-suite-inventory.md](test-suite-inventory.md).
The 42 unchanged synthetic copies replace legacy aliases; five reference-bound
checks now belong to private verification.

Frontend private files are `localExperimentalRatings.test.js`,
`provisionalOvr.test.js`, `productionDataAdmission.private.test.js` and
`provisionalDelivery.private.test.js`. Public production tests use explicit
invented denial payloads; private tests additionally check the original
nonpublication bytes and all real-profile parity. Python class/method boundaries
are explicit in `scripts/run_backend_tests.py`. New tests that read private
inputs must be assigned to that boundary. Public checks must pass from a
source-only tree with no data directories.

Use `PYTHONDONTWRITEBYTECODE=1`, `-B`, an external `TEMP`/`TMP`, and external pytest
`--basetemp` / `--junitxml` paths for preservation-sensitive acceptance runs.
The runner disables pytest's repository cache. Do not run a recursive cleanup.

## Joseph contributor parity prerequisite

The private AST parity check uses the reviewed immutable revision
`013c8edd5196a15ac826558f4b0964cc6f3a3e58`, path
`src/metrics/line_breaking.py`, rather than a mutable machine-local `Joseph-dev`
branch. Before private/full checks, verify the object exists:

```powershell
git cat-file -e 013c8edd5196a15ac826558f4b0964cc6f3a3e58:src/metrics/line_breaking.py
```

If absent, ask the contributor/team for the approved history/reference transfer;
do not silently compare against another branch or skip the assertion. Repository
access or a successful parity test does not authorize transfer of private data.

## Byte-preserving checkout

`.gitattributes` sets LF for JSON, Python and other text source and disables text
conversion for images/binary assets. This overrides `core.autocrlf=true` for the
checksum-sensitive source. Existing production guard pins and frozen evidence
hashes must remain unchanged. Adding the policy does not rewrite the current
working files or normalize the index.

Before a later approved staging/commit operation, inspect `git ls-files --eol`
and `git check-attr text eol -- <exact paths>`. Review proposed text blobs against
the intended LF hashes, particularly demo/synthetic JSON and the frozen v1 files
`scripts/compare_private_ovr.py`, `src/private_ovr_comparison.py` and
`tests/test_private_ovr_comparison.py`. If an index blob requires normalization,
request explicit approval for that exact path and inspect its diff; never use
blanket `git add --renormalize .`. No normalization or staging is performed by
the policy itself. Never normalize ignored frozen data artifacts.

After the eventual approved commit, validate a fresh Windows checkout with
`core.autocrlf=true`, both builds, both source-only suites and, where authorized,
private acceptance. The hardening verification report outside the repository
records Git's actual checkout-filter bytes without staging or creating a commit.

## Reviewed file boundaries

Use the external hardening report's exact proposed-staging and handoff manifests,
not `git add .`, directory-wide staging or a recursive workspace archive.
The 87 earlier proposals were a review pool, not blanket approval. The three
`docs/review/*-2026-10-29.md` proposals remain withheld for disclosure review;
compiled review evidence and `docs/references/` are excluded entirely.
Required runtime source must remain visible to Git; `frontend/build/` contains
guard source and must not be confused with generated `frontend/dist/`.

Exclude `data/` payloads, `frontend/public/data/`, source evidence, frozen numeric
packages, formula PDF, compiled contributor reports, dependencies, build outputs,
caches, browser logs and local virtual environments. Existing tracked empty data
placeholders are harmless, but confer no payload exception. Ignore rules do not
remove files from disk or untrack existing files. Existing tracked heatmaps stay
byte-identical; build admission does not resolve separate redistribution rights.

The next team decisions are the source/documentation audience, authorization and
channel for private recipients, contributor evidence/reference handoff, and any
future public asset/data licensing. Staging, committing, pushing and distribution
each remain subject to explicit approval. Public release decisions do not block
continuing the authorized local experiment.
