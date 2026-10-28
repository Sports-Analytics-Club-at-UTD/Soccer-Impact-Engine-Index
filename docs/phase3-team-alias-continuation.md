# Phase 3 continuation: supported team aliases and completed acquisition

October 27, 2026, America/Chicago. Branch `integration-foundation`, baseline and
final HEAD `96b3989e09d1349ed5313b0d7b1ec6471ae7e21a`.

**All 1,517 approved provider-listed pairs are retained and pass source review
under the updated verification revision. Zero pairs remain unacquired.**
The 358 authorized missing pairs were obtained serially without refreshes.
This completes acquisition against the approved provider inventory, not full
historical league completeness or production certification.

## Alias investigation and narrow correction

The retained fixture for **3829430** is Stade de Reims vs Olympique de Marseille,
Ligue 1, 2015/2016, dated 2015-08-16. The fixture, original events and lineup all
identify Marseille as team **147**, and the opponent as team **156**, Stade de
Reims. The fixture uses `Olympique de Marseille`; events and lineup use
`Marseille`. All original bytes and fingerprints agree with their descriptors.

| Original document | SHA256 |
|---|---|
| Ligue 1 fixture response | `733c7cf47bd7a19d9acae5add722c32b404664d949377057a280bd0b0f0d2464` |
| 3829430 events | `0d071c549e1030adb5f639e1c91a03fc5e467a2324a4d302d11732f49a6b90b3` |
| 3829430 lineups | `1094d1c7fbf56ab364b3cd5080a68f87d8cd3543e67be3737c4eebdd5aadd8e5` |

`src/identity.py` already declares exactly the two spelling aliases used here.
That file and its mapping were not changed. Original fixture records identify
Stade Malherbe Caen as team **140**; retained match **3829414** corroborates
ID 140 and its canonical name in both lineup and events, alongside team 147.
The later retrieved short-name Caen records also agree on ID 140.

`src/statsbomb_participation.py` now permits only:

| Exact team ID | Established spellings | Required fixture context |
|---|---|---|
| 147 | Marseille / Olympique de Marseille | competition ID 7 / Ligue 1; season ID 27 / 2015/2016 |
| 140 | Caen / Stade Malherbe Caen | competition ID 7 / Ligue 1; season ID 27 / 2015/2016 |

The numeric source team ID must first associate with the selected fixture team.
Neither a similar name nor an alias can repair a wrong ID, opponent, match or
context. Context IDs must be exact integers. Unknown names, whitespace/case
variants and arbitrary discrepancies still reject. Existing exact-name behavior
for other teams is unchanged. Player IDs/names, roster associations, substitutions,
tactical identities, source clocks, boundaries and quarantine checks remain exact.

Original names, numeric IDs and bytes are never rewritten. New immutable
`TeamNameNormalization` audit records retain fixture and observed names,
canonical spelling, team ID and an original source example reference. Every
unmodified occurrence remains in the original SHA-bound JSON. Player contexts
retain the fixture's original team label; there is no delivered-data rename.

`scripts/source_verification_batch.py` adds those records to new match reports
and includes `src/identity.py` in the verification implementation fingerprint,
alongside the workflow, adapter and interval validator. Future alias-map changes
therefore invalidate cached reviews. Original report files are preserved.

Final verification implementation revision:

```text
b3ce0be37343fde8076f3b872f97c6e5aecee78ab45859269984cfe1877bc0d6
```

## Offline regression and retained-source replay

The new `tests/test_statsbomb_team_aliases.py` contains 12 regressions covering
supported Marseille/Caen IDs and contexts; matching names with differing IDs;
consistent but unsupported IDs; unknown/fuzzy spellings; wrong match,
competition or season; player ID/name disagreements; opponent-side mismatch;
raw-input/fingerprint immutability; original fixture labels; and alias-policy
verification revision changes.

First, **3829430 was revalidated offline from retained bytes**. It now has 27
structurally valid appearances and one contradictory appearance. Jacques-Alaixys
Romao, actor **10036**, retains original-transition-not-represented and
post-permanent-exit activity findings. His aggregate minutes and position
allocation remain null. Fixing the team spelling did not repair participation.
The earlier rejected report remains untouched next to the new accepted-schema
report and its quarantined appearance.

Then all **1,159 retained pairs** were revalidated offline. The **1,158 previously
accepted results compare exactly**, excluding only their changed verification
key and the added normalization audit field. There were zero unexpected result
changes. All 1,159 immediate resume checks reused current-revision reports.
No requests or object/journal writes occurred during this replay.

Replay totals were 31,072 structurally valid, 772 contradictory and 306
incomplete active appearances. The additional 27 valid and one contradictory
appearance came from the previously rejected match, not corrections to older
accepted appearances. Network acquisition resumed only after the tests, complete
offline replay and preexisting-file preservation checks passed.

## Acquisition and final source inventory

The manifest remains byte-identical:

```text
data/source-evidence/phase1b-2026-10-27/analysis/retrieval-manifest.json
SHA256 756d0cbe3fdcbfb9c753da97f861004dccc44db271f863d035bf58fda324cfa2
Provider revision 4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
```

The original approved queue and historical remaining-ID snapshot also remain
unchanged. Their prior pending counts are historical states. The new final
inventory records the current complete state and exact original provider IDs.

Acquisition reused `EvidenceStore.execute`, its original transport, pinned
endpoints, request journal, source bindings and immutable report writer in
`data/source-evidence/phase3a-controlled-store/`. A session supervisor selected
the exact still-absent IDs from the actual 358-ID remainder, invoked serial
groups of 1–8 and stopped on source/integrity/acquisition failures. Each group
used the existing network authorization and size gate. Actor-level quarantine
did not cause source repairs or exposure promotion. No additional failure or
unknown alias required stopping this continuation.

| Acquisition result | Count |
|---|---:|
| Retained at start | 1,159 |
| Additional pairs obtained | 358 |
| Total original pairs retained and source reviewed | 1,517 |
| Remaining pairs / current source rejections | 0 / 0 |
| Successful requests this continuation | 716 |
| Failed / interrupted-outcome-unknown requests | 0 / 0 |
| Controlled-store successes across Phase 3A and subsequent sessions | 3,018 |
| Controlled-store failures / interrupted outcomes | 0 / 0 |
| Repeated `(match_id, artifact_kind)` requests across the controlled store | 0 |
| Serial continuation groups | 46: one match, 44 groups of eight, final five |

Completed pairs, including 3829430 and the original eight Phase 1 pairs, were
never downloaded again. No refresh, unrelated source request, unlimited
concurrency, manifest replacement or source-artifact overwrite occurred.

| League, 2015/2016 | Provider pairs | Reviewed pairs | Pending | Structurally valid appearances | Contradictory | Incomplete |
|---|---:|---:|---:|---:|---:|---:|
| La Liga | 380 | 380 | 0 | 10,278 | 243 | 32 |
| Premier League | 380 | 380 | 0 | 10,254 | 161 | 54 |
| Serie A | 380 | 380 | 0 | 10,055 | 352 | 192 |
| Ligue 1 | 377 | 377 | 0 | 10,053 | 339 | 87 |
| Total | 1,517 | 1,517 | 0 | **40,640** | **1,095** | **365** |

The newly obtained 358 pairs contribute 9,568 valid, 323 contradictory and 59
incomplete active appearances. Final counts use exactly one current-revision
review per match, never every historical report version. Bench-only roster
entries are not asserted appearances. All 1,460 contradictory/incomplete active
appearances retain null aggregate exposure and position allocation.

Known normalization was applied in 11 Marseille matches and nine Caen matches;
the exact match IDs, original labels and example references are retained in the
normalization ledger. There are no unresolved aliases encountered in this run.
No fuzzy or additional alias rule was introduced to finish the inventory.

## Evidence artifacts, integrity and storage

New review records are under
`data/source-evidence/phase3-alias-continuation-2026-10-27/`:

- `alias-source-evidence-review.json`: original fixture/event/lineup associations
  supporting IDs 147 and 140 and the established spellings.
- `3829430-offline-revalidation.json`, `3829430-participation-quarantine.json`:
  the initial offline result, original conflict evidence and withheld exposure.
- `retained-pair-revalidation.json`: every retained match's old/new report paths,
  current keys, expected resolution, unchanged accepted results and cache checks.
- `pre-acquisition-validation.json`: passing tests, full replay and preservation
  conditions checked before retrieval.
- `batch-NNN-UUID.json`: exact selected IDs, report paths, request accounting,
  appearance outcomes, accepted normalizations and cumulative pending state.
- `final-acquisition-summary.json`, `final-source-inventory.json`: final counts,
  coverage, exact provider IDs and empty pending list.
- `current-review-index.json`: one source-reviewed report per match, pinned to
  the current implementation revision. Use this instead of globbing all report
  versions into a season accountant.
- `accepted-team-name-normalizations.json`, `quarantined-appearances.json`:
  exact accepted spellings and all unresolved appearance findings.
- `preservation-input-inventory.json`, `validation-record.json`,
  `artifact-inventory.json`: preservation baseline and final verification records.

The controlled store occupies **5,558,839,120 bytes** (about 5.56 GB decimal).
This continuation added **1,671,957,117 bytes**, including fresh reviews of the
retained pairs. Original event/lineup payloads across all 1,517 matches total
**4,597,809,021 bytes**; historical and current review versions add overhead.
At final accounting, **9,711,370,240 bytes** remained free. Acquisition enforced
a 2 GiB reserve plus next-operation allowances.

Validation on the final implementation:

| Check | Result |
|---|---|
| Focused adapter and batch workflow tests | 80 passed |
| Strengthened alias regressions | 12 passed, also included in full suite |
| Full Python suite, warnings as errors | **861 passed**, zero skipped; final run 198.555 seconds |
| Frontend JavaScript suite | **154 passed**, zero failed or skipped |
| Full retained replay and immediate reuse | 1,159 passed each; no requests |
| Prior accepted report result comparison | 1,158 unchanged; only expected 3829430 resolution |
| Current report revision, hash and source association checks | All 1,517 passed |
| All old/new object and report content hashes | Passed, including repeated acquisition checkpoints |
| Controlled-store endpoint, revision, retrieval-time and request binding checks | All 3,018 successful requests passed |
| Preexisting file preservation | 8,436 checked: 8,434 unchanged; only two authorized implementation files changed |
| Protected inputs | All 11 protected Parquets, Arpit fixture Parquet and original M4A checklist unchanged |
| Existing source evidence, validation data, manifest and old queues | Byte-identical; only append-only additions |
| Git whitespace and index | Passed; no staged changes |

The source normalizer changes no scoring formula, policy, dataset, player name
or numeric ID. All provenance/trust/publication restrictions remain in force.
The implementation changes are limited to the participation adapter and source
verification report/revision handling, plus the new regression file. No frontend
implementation changed; no deployment or production rating export was performed.

## Step 2: real-player season statistics and playing minutes

**Production-certified season contexts remain zero.** Acquisition and source
schema review do not establish independent season-level identity, complete
usable exposure, verified numerators or approved scoring eligibility. The 549
delivered-table-qualified contexts were not promoted to certified exposure.

Step 2 still requires the following work and decisions:

1. Establish a reviewed canonical actor/club/competition/season appearance
   inventory using the current review index and original source bindings. Keep
   transfers, unknown identities, bench entries and absent contributions distinct.
   Source-roster agreement cannot alone attest an entire season crosswalk.
2. Resolve, independently substantiate or explicitly approve handling of the
   1,095 contradictory and 365 incomplete appearances. Preserve original
   observations and competing evidence. Unsupported actor totals cannot be
   quietly replaced with zero, clipped-90 time or partial-season denominators.
3. Approve the exposure/position convention: supported regulation clocks and
   stoppage time, exclusion of halftime and temporary gaps, boundary flags,
   position-minute/role allocation and unsupported exits. Then build a separate
   reconciled match ledger and sum only supported exposure under that policy.
4. Reconstruct the required raw metric numerators from original unfiltered
   events, with reviewed metric semantics and reportability. Prove exact actor,
   match and appearance coverage aligned to the same exposure scope. Only then
   compute per90 from total counts and supported minutes and reevaluate the
   900-minute eligibility gate; delivered minute totals are not a fallback.
5. Approve missing-delivery and coverage scope. Serie A fixture **3879594** is
   retained but still cannot enter a rebuilt scoring dataset without team scope
   approval and full roster/exposure/numerator reconciliation. Ligue 1's 377
   provider records do not establish 380 historical fixtures; three unlisted
   schedule slots still have no independently established provider IDs.
6. Approve transfer/role and reference-pool rules. Aggregate compatible raw
   counts and supported minutes without duplicate match contributions, retain
   original clubs/leagues and nominate reference membership explicitly. Do not
   average club rates, percentiles or ratings. MID/CB pools remain separate.
7. Establish a reviewed season-certification evidence path and explicit source,
   identity, exposure and numerator attestations. Existing `season_readiness`
   reports remain noncertifying. Any later individual FIFA, press, line-breaking,
   archetype or OVR delivery needs its own approved policy, production contract
   and publication authorization. None was calculated or enabled here.

Delivered event/minute tables were not rebuilt. No recovered match was inserted
into production scoring. This session completes source acquisition and the narrow
alias correction; it does not perform Step 2 or produce official player ratings.

## Git and final state

Branch remains `integration-foundation`; HEAD remains `96b3989`. The two tracked
modifications are `src/statsbomb_participation.py` and
`scripts/source_verification_batch.py`. The regression file
`tests/test_statsbomb_team_aliases.py` and this report are new and untracked.
Existing untracked data/checklist/review documents remain untracked. New source
objects, journals and review artifacts stay inside the already untracked evidence
tree. The staging area is empty.

No branch/worktree change, merge, rebase, reset, clean, staging, commit, push,
publication or deployment occurred. No additional retrieval is needed for the
approved 1,517-entry provider inventory. Future source expansion, dataset rebuild
or production scoring requires its own reviewed scope.
