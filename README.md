# Soccer Impact Index

Experimental scouting website for supported midfielder (MID) and centre-back
(CB) player-seasons. The React/Vite website integrates **Home, Players,
Leaderboards, Compare, Teams and About**. Goalkeeper ratings and individual
spatial-control ratings are research ambitions, not current supported features.

## Setup (PowerShell)

Use Python **3.11 or newer** (`hashlib.file_digest` is required); the accepted
reproducibility environment is **Python 3.13.0, Node 24.21.0, npm 11.19.0**.
`.python-version` and `.node-version` record those tested versions. Other versions
have not received equivalent acceptance testing. Git must honor `.gitattributes`.

```powershell
git clone https://github.com/Sports-Analytics-Club-at-UTD/Soccer-Impact-Engine-Index.git
cd Soccer-Impact-Engine-Index
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test.txt
cd frontend
npm ci --no-audit --no-fund
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open <http://127.0.0.1:5173/>. Activate the Python environment in the same shell
that launches Vite: its local adapter invokes `python`. Runtime-only installation
uses `requirements.txt`; `requirements-test.txt` adds pytest.
`requirements-research.txt` contains optional historical research libraries.
Direct runtime/test versions are pinned to the accepted environment; transitive
Python dependencies are resolved by pip, so these files are not a universal
platform lock. The existing npm lockfile is authoritative; use `npm ci`.

**Repository access does not authorize private data access.** A source-only
checkout builds the team-approved public 2015/16 real-player experience and runs
the public/synthetic checks. Production builds need no private research files. The development homepage needs seven separately authorized frozen
inputs; without them it shows an explicit data error and never substitutes demo
players. See [private provisioning](docs/private-local-provisioning.md).
Use <http://127.0.0.1:5173/?view=demo> for the fictional development demo.

## Current model and limitations

- Five independent attributes: TAC (tackles), INT (interceptions), REC (ball
  recoveries), PRS (press resistance) and LB (progressive-passing proxy).
  LB measures supported progressive passes; it does not establish actual
  defenders or tactical lines bypassed. See [method](docs/fifth-attribute-progressive-passing.md).
- Provisional **Formula B OVR** sorts the five full-precision ratings descending
  and weights them 30/25/20/15/10%. Only presentation rounds. All five valid
  ratings are required. This is experimental, not an official EA rating.
- Individual-attribute Gold badges use unrounded percentiles >=90; Silver uses
  >=75 and <90, for existing strict-eligible profiles only. There is no Gold/
  Silver overall OVR tier or inferred DM/CM positional archetype.
- Authorized frozen inputs yield 691 profiles, 686 complete OVRs and five N/A
  profiles. Strict leaderboards contain 124 MID and 107 CB players. Limited Data
  includes coverage limitations and ranking exclusions; excluded players retain
  their observed scores. Observed fixtures do not certify full-season coverage.
- Teams preserves Arpit's three team-level Off-Ball Spatial Dominance heatmaps.
  They describe defender-nearest observed space during opponent possession,
  not true pitch control or player ratings. Image-specific source/run provenance
  and redistribution rights remain a contributor/team handoff.

[Formula B](docs/provisional-formula-b-ovr.md),
[badges](docs/local-attribute-badges.md),
[Limited Data](docs/limited-data-status-consistency.md) and
[unified integration](docs/unified-local-website-integration.md) give the details.
Historical methodology reports describe their dated approval scope.

## Verify

From the repository root, with the environment active:

```powershell
python -B -m scripts.run_backend_tests public -q
cd frontend
npm run test:public
npm run build
npm run preview:single
```

Outputs are `frontend/dist/` and `frontend/preview/` (HTML plus the versioned
ratings JSON and three team PNGs for the standalone build). Both configurations
enforce default-deny packaging. Only the explicitly approved final-ratings
package is admitted by exact path and SHA256; environment variables cannot
authorize additional data. See [production delivery and verification](docs/public-ratings-production-delivery.md).

After separate private provisioning, run `python -B -m scripts.verify_local_inputs`
from the root, `python -B -m scripts.run_backend_tests private -q`, and, from
`frontend/`, `npm run test:private`. `npm test` and
`python -B -m scripts.run_backend_tests all -q` retain the complete suites.
Private checks require more research fixtures than the seven runtime files and
an immutable Joseph contributor Git object; see [test prerequisites](docs/source-handoff.md).
Missing inputs are incomplete verification, never a passing private acceptance.

## Handoff and contribution boundaries

See [source handoff and test contract](docs/source-handoff.md) for file review,
checkout verification and the staging-approval boundary. Private/processed/
derived evidence, local observations, caches and builds stay excluded from Git.
Never use a blanket staging operation. Do not regenerate frozen data to repair
setup or checksum errors. The historical `streamlit run app/main.py` instruction
is obsolete: that entry point does not exist; Vite is the current website.

No project-wide redistribution license has been selected. The team explicitly
approved publication of the final 2015/16 ratings for this release. That approval
does not authorize publication of raw datasets or private research packages.
