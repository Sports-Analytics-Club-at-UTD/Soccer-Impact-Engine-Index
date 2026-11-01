# Public and authorized-private test inventory

The inventories describe required source and actual case identities, not a target
pass count. A missing/unknown module or missing case is an error. Updating a test
requires review of its catalog entry; do not change catalogs to hide lost checks.

## Source-only verification

From the root with the declared Python environment active:

```powershell
python -B -m scripts.run_backend_tests public -q
cd frontend
npm run test:public
npm run test:packaging
```

`tests/suite_inventory.json` names each required public Python case. The runner
collects only required modules, rejects missing/unknown cases and requires every
selected case to run. `frontend/tests/suiteInventory.json` lists required modules
and reviewed LF-normalized source hashes. Public/packaging selection does not
require separately provisioned private test modules. No private data is needed.

Where loopback access is not permitted, use these explicitly partial profiles:

```powershell
node scripts/runTests.mjs public --offline
node scripts/runTests.mjs packaging --offline
```

They positively exclude the named HTTP preview check, report the exclusion, and
never constitute full HTTP acceptance. Do not use a negative name filter that
can match a file/ancestor and accidentally run every child. A temporary-output
filesystem failure must also be reported; use ordinary writable paths without
changing permissions or evading execution restrictions.

## Coverage migration

42 synthetic methods were copied with unchanged assertion ASTs into the five
`tests/test_source_only_*.py` modules: 8 A/B arithmetic, 7 Formula C arithmetic,
3 Formula B, 7 observation-contract and 17 independent original-array checks.
The catalog maps each copy to its unchanged legacy original, avoiding duplicate
execution while preserving the legacy source. Nothing recalculates expectations
from the function under test. Public verification has 1,007 actual cases.

Five earlier public cases require private code/reference context: one reviewed
PDF receipt, three verifier-run checks and one legacy CLI output-refusal check.
They are explicitly private, not deleted or claimed as passing without inputs.
Private verification has 51 actual cases. Together the catalogs retain all
1,058 original assertions by case identity/equivalence, not a fabricated count.
Frontend source is catalogued as 192 public and 34 private cases in the reviewed
versions; offline profiles report their HTTP exclusions separately.

## Private source and fixture interface

Repository access alone does not authorize receipt of test source or data.
Authorized custodians must separately provide the original private verification
source and existing evidence through an approved channel. Never place these in
public Git or regenerate them for a test. The source-only candidate intentionally
does not contain the private measurement examples or research/reference code.

Backend `private_source_sha256` records reviewed LF source fingerprints for the
required private verification modules and helpers; the frontend inventory records
its four private modules. These are metadata, not expected score payloads.
Private/full runners fail explicitly if source is missing or differs.
Public copies of six mixed/private modules omit private bodies; the authorized
private workspace must retain the full reviewed originals, including mixed-module
versions. Public markers cannot substitute for those source fingerprints. The
checksum-bound legacy implementation/test originals remain byte-identical;
retained artifact validators still enforce their independent raw-byte hashes.

After source preflight, original private regressions compare against existing
independent frozen references and expectations. Runtime inputs are the seven
files described in [provisioning](private-local-provisioning.md). Private tests
also need retained OVR v1/v2 comparison/eligibility artifacts, observation JSON,
source/processed/phase-3 evidence, the contributor review package and the reviewed
Joseph Git object. Hash validation, exact numerical comparisons, transfer checks,
strict eligibility and missingness assertions are unchanged. Missing evidence
fails or makes acceptance incomplete; it is never replaced by synthetic data.

Run from the authorized original/private workspace:

```powershell
python -B -m scripts.run_backend_tests private -q
cd frontend
npm run test:private
```

`all` / `npm test` requires both source and evidence. The public candidate is
not expected to pass private/all suites without separate provisioning. The
optional private offline profile explicitly excludes its local HTTP workflow;
all other real-data assertions still run. Source preflight and data validation
are separate from recipient permission and production publication authority.
