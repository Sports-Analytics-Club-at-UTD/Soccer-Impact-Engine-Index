# Phase 3 Step 3: real scoring input preflight

Prepared October 28, 2026 on `integration-foundation`, checkpoint `53e9b22`.
This work prepares inputs; it produces no real numeric rating, attestation,
reference membership, certification or publication permission.

The existing formulas, independent verification and synthetic delivery pipeline
were sufficient for their documented purposes. `real_candidate_analysis.analyze`
already projected the real defensive measurements into the DRI contract with
truthful withheld evidence. Missing engineering was the sealed-input handoff to
both defensive and press contracts, comparison against the completed independent
context evidence, and a separate validator for future evidence/membership receipts.
No scorer, reconstruction or independent verifier was rebuilt.

## Implementation and exact mapping

New module: [`src/real_scoring_preflight.py`](../src/real_scoring_preflight.py).
Run the read-only console preflight from the repository root:

```powershell
python -B -m src.real_scoring_preflight
```

`load_preflight()` pins the previously reviewed source manifest, independent
verification manifest and unsigned request by their exact SHA256 values. It also
checks the bytes and sizes of the two consumed JSONL artifacts against those
manifests. It consumes the sealed player-club summaries and reference evidence;
it does not reopen all originals or repeat source verification. The manifests
retain the original acquisition and verification provenance chain.

`prepare()` reuses the existing real projection and checks matching context sets,
stable actor/team IDs, exact independently supported rational duration, unresolved
appearance totals, actor findings, role agreement and transfer ambiguity.
Duplicate or conflicting identities, invalid counts, foreign numerator scopes,
inconsistent rates and unexpected trust promotion fail closed. Incomplete rows
remain present with their counts and withheld denominators; they cannot become
approved members. Original fixture 3879594 remains excluded.

| Fact / engine input | Mapping |
| --- | --- |
| Identity | Canonical integer provider player ID plus team, competition and season; team ID retained alongside engine identity columns |
| Exposure | Exact rational minutes retained in context facts; existing engine numeric minutes and `SeasonScope` projected by the existing analyzer |
| Defensive measurements | Three existing DRI measurement rows per context: successful tackles, successful interceptions, recoveries; exact counts, per90 and numerator/exposure match scopes |
| Press measurements | Existing `press_scoring.ACTION_COLUMNS`: four exact pressured pass/dribble attempt/completion counts, identity, matching `PressScope` and coverage reference |
| Comparison | Existing cohort ID plus MID/CB comparison-pool identifier; these identify proposed comparison groups, not approved distributions |
| Provenance | Source seal `2376fe77…`, independent seal `9f697c62…`, unsigned request seal `78fb45d0…`; full hashes in the code and console output |
| Review issues | Independent blockers, unresolved exposure, transfer ambiguity and exact excluded match IDs preserved per context |

The returned `PreparedInputs` contains population, defensive measurements, press
actions, comparison pool and a deterministic report. All evidence remains
`UNVERIFIED`, `full_season=false`, `reference_member=false`; reportability remains
withheld. Press evidence is deliberately not relabeled as synthetic to satisfy
the existing candidate engine. No engine or delivery admission rule was changed.

## Future receipt boundary

`validate_receipt()` accepts only an explicitly hash-pinned
`real-scoring-review-receipt/v1` with decision scope
`evidence_and_club_membership_only`. It requires reviewer, authority, review date,
independent basis, decision version, exact evidence/request/mapping bindings,
accepted exposure/role handling, retained successful interceptions, explicit
private-computation approval and accepted limited provider coverage. The existing
unsigned request and approval matrix cannot satisfy this contract.

Memberships must name exact technical contexts, role groups and team IDs, with
at most one club unit per player-season. A transferred actor requires explicit
`nominate_this_club_only`; aggregation is unsupported by this receipt scope.
Combining clubs still requires the existing contribution validation and an
explicitly reviewed adapter for the selected policy. No partial or incomplete
other-club exposure becomes a complete aggregate through nomination.

The trusted digest is the SHA256 of canonical JSON computed by `canonical_hash`.
The caller must obtain and authenticate that digest and reviewer authority
independently; computing a digest from an arbitrary uploaded JSON is not approval.
This is structural/integrity validation, **not signature authentication**.
An optional `--receipt PATH --trusted-receipt-sha256 HASH` performs these checks
and still returns `scoring_enabled=false`. No actual receipt was created.

Receipt acceptance does not approve individual formulas or populate engine
reference flags. It returns the remaining policy, real-engine admission and
delivery/publication gates explicitly. Real numeric frontend delivery stays
disabled; true line breaking and OVR remain N/A. Existing aggregate DRI mathematics,
four leagues, MID/CB grouping, 900 minutes and 90/75 archetype thresholds are unchanged.

## Verification and present readiness

Two consecutive loads of the actual sealed inputs produced identical reports
and all three identical engine input tables:

- 2,280 contexts; 6,840 defensive measurement rows; 2,280 press action rows.
- 236 technical candidates: 126 MID and 110 CB.
- 12 candidate transfer-review flags; two candidate fixture-exclusion flags.
- Mapping SHA256: `c79116585c57f886c247b511f785a7cdaf88d617ffea69a7ec8865eeee4663a0`.
- Zero approved reference members, real numeric ratings or publication permissions.

The twelve new focused tests cover deterministic/repeated preparation, identity
and exposure conflicts, counts/scopes, incomplete exposure, fixture exclusion,
unsigned/untrusted receipts, stale bindings, membership/role/transfer ambiguity,
sealed-file tampering, and rejection by existing numeric boundaries. Test receipts
use invented identities and authorities only.

Validation completed: 12 focused tests pass; the full backend run passes all
932 tests (`python -B -W error -m unittest discover -s tests`); all 154 frontend
tests pass (`node --test frontend/tests/*.test.js`). Fixture reconstruction in
the test suite is confined to invented temporary inputs; the full real
reconstruction and independent source acquisition were not rerun.

Fingerprint comparison found zero changed/missing files among 15,223 pre-existing
repository files, totaling 7,939,066,419 bytes (Git internals and bytecode caches
excluded). Protected Parquets, source originals, sealed artifacts, prior local
work and the reference PDF remain unchanged. Preservation receipts are outside
the repository in the session visualization directory. Only this report, the new
module and its test file were added. Branch and HEAD remain `integration-foundation`
and `53e9b2218973031e4d6a82d721650a88503e6432`; the index remains empty.

## What remains and the next action

The [Arpit reported-comparison note](phase3-step3-arpit-reported-validation.md)
records 708/708 matching defensive counts, reported minute/scope differences and
the remaining Step 3 decisions. It supplies no authenticated receipt or scoring
authorization. Technical candidates remain 236 (126 MID, 110 CB), all 12 transfer
flags remain, and Arpit's transfer position awaits clarification; admission gates
and the original comparison package are unchanged.

The verified facts can now be supplied in existing engine contract shapes without
rebuilding protected datasets. They cannot yet be supplied as admitted real
scoring inputs. Individual defensive and press candidate engines remain
synthetic-only; this session deliberately adds no real numeric execution mode.

The existing [approval evidence matrix](phase3-step3-approval-evidence-matrix.md)
remains the single decision package. Outstanding human decisions are source and
exposure/role attestation, exact reference membership and transfer treatment,
individual defensive/press policy adoption, and accepted source/release scope.
These are approval/evidence decisions rather than missing formula discovery.

Once reviewers provide an authenticated, versioned receipt, run this preflight
against its exact evidence and mapping bindings. Then implement and review only
the narrowly approved real-engine admission, using the existing mathematical
engines and the nominated units; add policy-specific tests before any authorized
private calculation. A changed numerator or aggregated transfer unit needs its
own justified, versioned adaptation. Public numeric delivery requires separate
authorization and contract work. No settled decision needs reopening.
