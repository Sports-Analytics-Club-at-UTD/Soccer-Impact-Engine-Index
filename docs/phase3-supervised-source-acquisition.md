# Phase 3: supervised full-season source acquisition

October 27, 2026, America/Chicago. Existing checkout `integration-foundation`,
HEAD `96b3989e09d1349ed5313b0d7b1ec6471ae7e21a`.

**Stopped during batch 144 on a source team-identity rejection for 3829430.**
No subsequent match was requested. The original documents are retained; the
identity gate was not changed, and no source record was repaired or refreshed.

## Acquisition and verification outcome

The starting inventory reconciled exactly to 1,517 provider fixtures, 16 retained
pairs (eight Phase 1 plus eight Phase 3A), and 1,501 pending pairs. Original
fixture/request inventories and retained fingerprints passed offline checks.
The existing manifest and approved queue remained unchanged:

- Manifest SHA256:
  `756d0cbe3fdcbfb9c753da97f861004dccc44db271f863d035bf58fda324cfa2`.
- Provider revision: `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.
- Queue SHA256:
  `b5d0e09c9321752adfbff1a55a8d22ecf7ad637a774e0e8b658a28af220351b8`.

| Result | Count |
|---|---:|
| New pairs obtained this session | 1,143 |
| Total original pairs retained | 1,159 |
| Total pairs passing source schema/identity review | 1,158 |
| Obtained pair rejected by source identity gate | 1: 3829430 |
| Pairs still unacquired | 358 |
| Successful payload requests this session | 2,286 |
| Failed / interrupted-outcome-unknown requests this session | 0 / 0 |
| Controlled-store successful requests, including initial Phase 3A batch | 2,302 |
| Controlled-store failures / interrupted outcomes | 0 / 0 |
| Full eight-match batches completed this session | 142: batches 2–143 |
| Partial batch | 144: seven pairs obtained; six reviewed, one rejected; eighth unrequested |
| Remaining nonempty acquisition queue groups | 46: remainder of 144, then 145–189 |

All requests were serial and limited to missing events/lineups for approved
four-league 2015/2016 inventory IDs. The existing `EvidenceStore.execute` gate
remained active with limits of at most eight. A local session supervisor invoked
the existing machinery, stopped immediately after an acquisition failure or
match-level rejection, and allowed actor-level quarantine to persist while
continuing other authorized matches. It used a per-process journal read snapshot
for serial lookup efficiency; original exclusive journal writes were retained.
No repository implementation, transport, formula or identity gate was changed.
Progress was reported for each batch, with cumulative reports every 64 newly
obtained pairs and repeated content-hash checkpoints.

No `(match_id, artifact_kind)` was requested twice. The eight original Phase 1
pairs and eight completed Phase 3A pairs were reused without downloads. There
were no refreshes, retries, unrelated data requests or unbounded concurrency.

## Coverage and appearances

All rows below are season `2015/2016`. Obtained pairs and source-reviewed pairs
are separate counts; a rejected pair still occupies retained acquisition scope.

| Competition | Provider | Obtained | Source reviewed | Unacquired | Structurally valid | Contradictory | Incomplete |
|---|---:|---:|---:|---:|---:|---:|---:|
| La Liga | 380 | 380 | 380 | 0 | 10,278 | 243 | 32 |
| Premier League | 380 | 380 | 380 | 0 | 10,254 | 161 | 54 |
| Serie A | 380 | 380 | 380 | 0 | 10,055 | 352 | 192 |
| Ligue 1 | 377 | 19 | 18 | 358 | 458 | 15 | 28 |
| Total | 1,517 | 1,159 | 1,158 | 358 | 31,045 | 771 | 306 |

The final totals are counted directly from one report per match; they supersede
the running arithmetic contradiction tally. This session alone added 30,617
structurally valid, 755 contradictory and 306 incomplete active appearances.
Bench-only roster entries are not fabricated appearances. No appearance count
is asserted for rejected match 3829430. Its entire unassociated match review
remains withheld rather than being counted as zero real-world participation.

For every contradictory or incomplete active appearance, aggregate exposure and
position allocation remain null. Millisecond clocks, original source IDs,
transition evidence and original position records remain in immutable reports.
Some incompleteness concerns flagged period boundaries: for example 266557 has
a flagged final Half End, 3879615/3879619 have flagged second-half starts, and
3829428 has a flagged first-half start. These are retained provider observations
handled by the existing validator, not grounds to invent whistle times.

## Initial Phase 3A contradictions inspected

- **265944 / actor 16332, Ognjen Vranješ:** event
  `843091e6-4678-4515-828b-e20b8a46f76c` is a Foul Committed with a Second Yellow
  card. The lineup retains activity after this permanent exit, including a later
  position stint. Original transition-not-represented and post-exit-activity
  findings remain; minutes and position allocation are withheld.
- **266149 / actor 6576, Gorka Iraizoz Moreno:** event
  `d5df0bdf-430b-4c40-92dd-72b141b4139d` is a Foul Committed with a Red Card.
  The lineup claims subsequent activity, including a later positional stint.
  Both source conflict findings are preserved; minutes and position allocation
  are withheld.

`initial-contradiction-review.json` retains their original events, positions,
validation results and source bindings. No automatic reordering, inferred repair
or source edit was performed.

## Stop condition: 3829430

The independent fixture lists Stade de Reims vs Olympique de Marseille on
2015-08-16. Its away team ID is **147**, named **Olympique de Marseille**.
The original lineup and events use team ID **147**, named **Marseille**.
Home team ID/name 156 / Stade de Reims agrees. The existing adapter requires
exact fixture/lineup team identity associations and returned:

```text
SourceSchemaError: fixture/lineup team identity conflict
```

Both payloads were obtained successfully, with 3,533 original events and two
team lineup objects. This is a source-association rejection, not a download or
fingerprint failure. Matching numeric IDs do not authorize silently replacing
the strict name check. No alias or correction was approved in this session.

| Payload | SHA256 |
|---|---|
| Events | `0d071c549e1030adb5f639e1c91a03fc5e467a2324a4d302d11732f49a6b90b3` |
| Lineups | `1094d1c7fbf56ab364b3cd5080a68f87d8cd3543e67be3737c4eebdd5aadd8e5` |

`source-rejection-review.json` binds the exact original fixture record, source
team labels, immutable payload descriptors and rejected report path. All later
retrieval stopped. The remaining first unacquired ID is **3829431**.

## Evidence, exact remainder and resume

Existing payload store: `data/source-evidence/phase3a-controlled-store/`.
It now contains 2,302 content-addressed objects, 1,151 match reports and 4,604
append-only request journal entries. Phase 1's eight original pairs and Phase 1B
review reports remain in their original locations, referenced without copying
or replacement.

New session review artifacts live exclusively under
`data/source-evidence/phase3-supervised-session-2026-10-27/`:

- `batch-NNN-UUID.json`: every batch's exact IDs, per-match result paths,
  accounting, status counts, quarantine findings, remaining IDs and stop state.
- `final-acquisition-summary.json`: audited counts, coverage, storage, source
  rejection, preservation and exact remaining queue groups.
- `remaining-source-inventory.json`: all **358 exact remaining IDs**, grouped
  by competition/season and original queue group. It separately lists source
  obtained but rejected ID **3829430**; that pair must not be downloaded again.
- `quarantined-appearances.json`: all 1,077 contradictory/incomplete active
  appearances and issue codes, referenced to the immutable match reports.
- `initial-contradiction-review.json` and `source-rejection-review.json`:
  original evidence supporting the initial quarantine and mandatory stop.
- `preservation-input-inventory.json`, `validation-record.json` and
  `artifact-inventory.json`: input fingerprints and final verification records.

All 358 unacquired IDs are in Ligue 1. Their exact array, not an inferred numeric
range, is the resume authority. The first IDs are 3829431, 3829432, 3829433,
3829434, 3829435, 3829436, 3829437, 3829438. Original batch 144 has only
3829431 unacquired; subsequent original batches 145–189 are unacquired.

**Do not continue network retrieval until the source-identity stop has been
reviewed and continuation is explicitly cleared.** The exact reviewed outcome
could preserve match-level quarantine or require a separately reviewed identity
policy implementation. This report does not authorize either policy change.
Refetching the pinned revision is not a repair for the differing source names.

After that review clears continuation, an offline selected-ID inventory check is:

```powershell
python -B -m scripts.source_verification_batch --manifest data/source-evidence/phase1b-2026-10-27/analysis/retrieval-manifest.json --destination data/source-evidence/phase3a-controlled-store --match-ids 3829431
```

The first missing-pair retrieval command, prepared but not executed, is:

```powershell
python -B -m scripts.source_verification_batch --manifest data/source-evidence/phase1b-2026-10-27/analysis/retrieval-manifest.json --destination data/source-evidence/phase3a-controlled-store --allow-network --batch-limit 1 --match-ids 3829431
```

Then continue the remaining exact queued IDs serially, at most eight per batch,
using the same manifest/store, without `--refresh`. Read completed bindings and
their fingerprints before any missing-artifact request. Actor contradictions
remain quarantined; source rejection, integrity conflict, acquisition failure,
rate limiting, unexplained filesystem change or insufficient storage stops
continuation. The session supervisor stopped on the first acquisition failure
if one occurred; none did. Interrupted starts would remain outcome-unknown and
only successfully finalized bindings could be reused; this session ended with
no interrupted requests and no partial pairs.

## Storage, validation and input preservation

Controlled-store files total **3,886,882,003 bytes** (about 3.89 GB decimal),
including initial Phase 3A data. The session added **3,858,902,232 bytes** to
that store. All retained original pair payloads, including Phase 1, occupy
**3,486,693,810 bytes**. Session review documents add a smaller separate amount;
the validation record gives their measured total. At the final acquisition
accounting snapshot, **11,842,162,688 bytes** remained free. A 2 GiB reserve and
next-batch allowance were enforced during acquisition; storage did not trigger
the stop.

| Validation | Result |
|---|---|
| Full offline Python suite, warnings as errors | 849 passed, no skips; 160.121 seconds |
| Pre-session file preservation | All 251 inventoried preexisting input/code files byte-identical |
| Protected Parquets | All 11 unchanged |
| Arpit fixture snapshot | Unchanged |
| Original untracked M4A checklist | Unchanged |
| Existing manifests, approved queue, source artifacts/reports/journals | Unchanged; only exclusive new store/session files added |
| New object and report content hashes | All passed, including repeated acquisition checkpoints |
| Request endpoint/revision/byte bindings and start/finish associations | All 2,302 controlled-store payload requests passed |
| Repeated `(match_id, kind)` requests | Zero |
| Unexpected source/validation additions outside approved store/session | Zero |
| Scoring/identity/participation implementation changes | Zero |
| Git whitespace / index | `git diff --check` passed; no staged changes |

No frontend implementation changed, so frontend builds were not needed for
this acquisition. The source workflow's real retained-evidence checks and fake
transport failure/resume regressions are included in the full Python suite.
Final inventories were checked directly against disk; report versions were not
counted as extra matches. No identity, source or policy gate was relaxed.

## Certification, blockers and Git

**Actual season certification progress: zero certified contexts.** Acquiring all
provider-covered pairs for three leagues supplies more evidence, not an exposure
attestation. The existing 549 delivered-table-qualified contexts are not promoted
to validated exposure eligibility. Delivered player minutes and numerators were
not rebuilt, scoring formulas were unchanged, and no production rating was
calculated or exported.

Remaining work includes source-association review for 3829430; the 358 missing
Ligue 1 pairs; independent identity/provenance review; complete appearance and
metric numerator/denominator scope; handling of 771 contradictory and 306
incomplete appearances plus the wholly rejected match; exposure/role/transfer
and reference membership policy; historical Ligue 1 coverage; individual FIFA,
press, line-breaking and OVR policies; a separately reviewed production delivery
contract and publication authorization. Three provider-unlisted Ligue 1 schedule
slots still have no verified IDs and were not invented or retrieved.

Fixture **3879594** remains retained source evidence only. Its inclusion in a
rebuilt scoring dataset still requires team scope approval; nothing was inserted
into delivered tables. No full historical coverage is inferred from provider
lists alone.

Git remains on `integration-foundation` at `96b3989`, with no tracked changes and
an empty staging area. The original untracked data/checklist entries remain.
The earlier two Phase 3A review documents remain untracked and unchanged; this
session adds this untracked report and new evidence inside the already untracked
`data/source-evidence/` tree. No branch/worktree change, merge, rebase, reset,
clean, staging, commit, push, publication or deployment occurred.
