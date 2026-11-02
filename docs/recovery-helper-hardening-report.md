# Recovery helper hardening — Batch 5

**Preventative hardening is complete locally. Both synthetic hazards reproduced; no published corruption was established.** Batch 5 changes no existing production caller or historical helper body. Complete 691-profile comparison finds zero new player associations, numerators, exposures, ratings, Formula B results or eligibility changes. Published V1 and frozen references remain unchanged. The known private frontend typography failure remains separately reported below.

## Baseline and isolation

Fetched origin/main and verified the Batch 4 PR #13 merge `886d58413ee8777585ae989a2d97744171decb5b`; the new branch is `recovery-helper-hardening`, based exactly on that merge. Worktree: `C:/Users/Ayush/Desktop/Projects/Soccer-Impact-Engine-Index-recovery-helper-hardening`. No commit, push, PR, merge, publication or deployment was performed. Original dirty files and existing research/source-reconciliation worktrees were not edited. Git fetch/worktree metadata changed as explicitly requested. No data junction was created or traversed into a new worktree/private directory; installed node_modules was reused through a dependency junction. Small chronology test evidence was copied individually with hashes. Private suites used retained read-only evidence/harnesses, described below.

Read the roadmap from the integrity-audit sibling and the initial identity audit from the retained coverage-audit checkout (neither document exists in merged main). Read merged Batch 4 and Batch 3B reports, and the Batch 2A, 2B and 3A reports. Their input paths and hashes are retained in the private receipts. Absence of formal GitHub reviews was not treated as a blocker.

## Root causes and exact reproduction

Original signatures in `src/metrics/recovery_coverage.py`:

```python
recovery_counts(rec, group_cols=DEFAULT_GROUP)
add_per90(counts, minutes, on, min_minutes=None)
```

`DEFAULT_GROUP = ('player', 'team', 'competition_name', 'season_name')` has no stable ID. Synthetic IDs 1 and 2 share the name `José D'Angelo` and identical team/competition/season. The original default emits one row with count **2**. The guarded default emits IDs **1, 2**, counts **1, 1**, and preserves disjoint event-ID sets **{uuid-A}, {uuid-B}**. Combined count remains 2, with no duplication or loss. These are deliberately synthetic event labels, not claims about original source UUIDs. `grouping-comparison.csv` retains exact keys and sets.

The historical minute helper performs an unchecked left merge. One numerator row and two identical minute keys emit **two rows**. The guarded API raises `RecoveryInputError: minutes: duplicate join keys; supply one supported denominator per context`, returning no partial table. Explicit unsafe name-only grouping fails with the canonical PLAYER_KEYS requirement. `original-helper-reproduction.json` and `join-cardinality-comparison.csv` retain mechanisms and outputs.

## Provenance, callers and compatibility decision

**The entire historical excerpt remains byte-identical to Batch 4.** AST comparison also confirms `extract_recovery_events`, `recovery_counts` and `add_per90` equal the contributor implementation at `0445f18fa1895320f0679ee84022888793fae6e7`. The retained provenance claim is still accurate; constants and historical defaults were not edited.

The original contributor CLI invokes `recovery_counts(rec)` with its historical default. Silently changing that default would change its output grouping/schema and could break legitimate reproduction. A separate adapter is therefore the narrow compatibility choice. Existing contributor imports, signatures and return shapes are preserved. Migration is optional and explicit; new reuse should choose the guarded API. Untracked external notebooks/workflows cannot be enumerated. There are no current tracked notebooks relying on these functions and no other current module importing DEFAULT_GROUP. The original commit tree has its recovery modules and recovery-per90 tests; its CLI dependency is recorded, not silently migrated.

Existing call sites are unchanged:

| Caller | Grouping / join protection |
| --- | --- |
| `src/recovery.py::integrate_recovery` | Calls recovery_counts with PLAYER_KEYS; `_minutes` validates unique canonical exposure, numeric nonnegative finite known minutes; post-merge row count and player/type uniqueness checked. |
| `scripts/audit_provisional_metrics.py` | Explicit PLAYER_KEYS, diagnostic conservation and exposure checks. |
| `scripts/audit_match_scoped_metrics.py` | PLAYER_KEYS plus match_id for fixture rates; PLAYER_KEYS for pooled rates; pooled exposure and metric conservation checks. |
| Contributor original CLI | Historical name default retained solely at legacy compatibility boundary. |

`helper-callsite-inventory.csv` lists exact paths, lines, imports, definitions and calls. No integrated caller was switched to a second aggregation path. Existing production reconstruction and all 34 prior production modules are byte-identical to the completed replay. Existing frontend source is also unchanged.

## Safe API and boundary

```python
from src.metrics.safe_recovery import recovery_counts, add_per90

totals, by_zone = recovery_counts(selected_verified_events)
rates = add_per90(totals, supported_minutes, on=PLAYER_KEYS,
                  min_minutes=900)  # threshold remains caller policy
```

New signatures are `recovery_counts(rec, group_cols=tuple(PLAYER_KEYS))` and `add_per90(counts, minutes, on, min_minutes=None)`. Canonical PLAYER_KEYS is defined in `src/identity.py`: **player_id, team, competition_name, season_name**. All four are mandatory for grouping and denominator joins. Additional dimensions, such as match_id, may be supplied explicitly. They cannot replace team, competition or season. Names do not determine identity; verified spelling, accented, Unicode and apostrophe variants of one ID combine under the canonical default.

The count wrapper delegates aggregation to the unchanged historical function. It requires unique nonblank event IDs, known recovery event types, non-null valid exact positive player IDs and complete canonical context. Missing IDs are never guessed. Missing required columns/invalid identity use the existing `IdentityError`; unsafe grouping, duplicated/conflicting UUID identity, null additional keys and failed conservation use `RecoveryInputError`. Both are ValueError subclasses. Caller input is not mutated.

The rate wrapper validates unique minute-side keys and uses pandas `validate='many_to_one'`. Separate event types and zones may legitimately share one supported denominator. It checks cardinality, full numerator/identity rows and order after merging. It rejects duplicate minutes even if their values agree, negative/nonfinite known exposure, nonnumeric values, flags, null keys, missing numerators, unsafe thresholds and already attached rate columns. It does not drop or sum duplicate exposure.

Positive supported exposure retains the exact historical vector arithmetic `count / minutes * 90`; zero or missing exposure yields NaN. Missing denominators remain missing. Minimum-minute filtering masks rates strictly below the supplied threshold while retaining counts/exposure; equality at the threshold is allowed. An unmatched minute row adds no count row. Empty schema-correct inputs are supported. No global NaN-to-zero conversion occurs.

**Trust boundary:** these are helpers for already selected, source-verified canonical records, not an identity resolver or exposure-support certifier. They cannot prove that an individually plausible supplied ID belongs to a source actor. Raw callers requiring identity reconciliation must use `integrate_recovery`, which retains its trusted-crosswalk and conflict checks. A shared name with two different IDs is valid; one UUID assigned conflicting identities is rejected. No alias, fuzzy matching, invented stable ID or new source-admission policy was introduced. The old unguarded API remains accessible intentionally; direct historical imports do not acquire the new guards. Discoverability is provided in `docs/m2b-recovery.md` and the adapter module documentation.

## Integrated safety and metric semantics

`src/identity.py::resolve_events` assigns source identities with authoritative supplied IDs, a validated trusted crosswalk, unique event IDs, stable context and many-to-one cardinality/order checks. `src/recovery.py::_extract` rejects duplicate raw UUIDs including excluded actions. `_accounting` conserves selected, outside-population and unresolved events. `integrate_recovery` groups only selected events by PLAYER_KEYS and checks totals and known-zone counts per event type before applying validated exposure. `_minutes` never derives denominators from events. `src/scorecard.py` joins components one-to-one on stable contexts; rating assembly and frozen membership remain independent gates.

Successful tackle/interception definitions and failed-ball-recovery exclusion are unchanged. Every selected unknown-location event contributes to totals but not by_zone. Pressure remains a successful/attempted pressured-action ratio; progressive selection and original geometry are unchanged. Positions, source restrictions, participation, thresholds, player-season/team context, exact rational diagnostic exposure and float scoring precision remain intact.

## Source, population and numerical evidence

Freshly recomputed:

- All **691** current diagnostic profiles: **3,455** independent attribute comparisons, **691** Formula B comparisons and **691** eligibility comparisons; zero discrepancies versus Batch 4/3B.
- All A–G retained stage arithmetic: **24,185** attribute rating/percentile and **4,837** Formula B comparisons. Full CSV preserves V1, Batch 1, 2A, 2B, 3A, 3B, 4 and proposed Batch 5, preserving earlier intended differences. Batch 5 versus Batch 4 has zero deltas. It does not erase historical correction deltas versus V1.
- All **2,514** historical frozen-reference candidates in their original scope: **12,570** attribute-candidate predicates plus exact frozen membership-set equality. These are not the number of unique original roster actors.
- Transfer checks: **103** actor/fixture uniqueness, **1,030** numerator conservation and **103** exact exposure conservation assertions.
- Fresh hash checks: **34** unchanged existing production modules, **31** prior evidence artifacts, **4,732** prior input receipts including **4,682** original data receipts, plus retained inputs already bound while checking artifacts. Exact paths, sizes and hashes are in input-hashes.json.
- The hash-bound read-only UUID database passes SQLite integrity checking and contains exactly **5,436,699** UUID-primary-key records across **1,551** fixtures. No source reassignment can be introduced by this unused adapter; prior bidirectional actor/team/fixture conservation evidence is hash-verified and reused.
- Seven original fixture controls independently select successful UUIDs directly from raw provider fields, without using either count helper as selection oracle. They verify per-source-actor numerator sets, counts, actual retained diagnostic denominators, missing denominators and direct rate arithmetic against integrated/guarded outputs. No real-data difference occurred.

| Original fixture | Successful source recovery UUIDs | Known-zone counts |
| --- | ---: | ---: |
| 3753991 (original Fernando Luiz Rosa context) | 177 | 177 |
| 3754296 (original Fernando Luiz Roza context) | 136 | 136 |
| 3825670 (Juanfran bench fixture) | 138 | 138 |
| 3754048 | 132 | 132 |
| 3900579 | 121 | 121 |
| 3825780 | 145 | 145 |
| 3829454 | 122 | 122 |

These seven controls retain **971** successful UUIDs exactly. Their selected source recoveries all have known locations; unknown-location semantics are separately exercised synthetically. Controls inspect the raw helper/integrated selection contract, not a new claim that all raw fixture events satisfy production interval/metric admission. In particular the four historical boundary examples remain under the unchanged chronology restrictions. Production accepted-event sets and geometry are established by the unchanged-code/hash-bound replay evidence, not by treating these raw fixture controls as a new admission path.

**Reused, not newly replayed:** the completed Batch 4/3B full-source reconstruction, bidirectional UUID assignments, independent metric alignment, original actor/recipient bindings and accepted geometry. Reuse is justified by exact original-data/artifact hashes and byte-identical existing production modules; the new adapter has no existing production imports. The retained replay covers 430,440 raw metric UUID-set checks, 418,280 independent measurement-alignment checks, 74,890 frozen-fact raw UUID sets, 41,828 roster geometries, 14,979 historical decisions and 14,550 accepted published appearances. These figures are historical verification evidence, not new Batch 5 scan counts. No massive source replay was rerun.

One historical diagnostic self-receipt differs: the Batch 4 investigation script's receipt records `a53bbe7789fdfd4c81e1e75bc7740a4d6a4eb11406ae4089bec4be05b46f7db0`, while the retained final script is `4e35dc9e8ad6b989a9fac673cd2cfc427e8e5a0fdc131492ebdc6a0622f86dd1`. It is not a line-ending-only difference. The final retained script equals merged Batch 4 after newline normalization. This stale diagnostic self-receipt is recorded explicitly in historical-diagnostic-receipt-differences.json; it is not claimed to match and is not used to waive any original-data, production-module or consumed-output mismatch. Current diagnostics were independently recomputed. This remains a historical audit-reproducibility caveat, not evidence of a changed source or published metric.

Frozen semantic fingerprint remains `403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd`. Published V1 file SHA256 remains `9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e`. Exact original fixture event/lineup/fixture hashes and every reused source receipt are in input-hashes.json. Published V1 JSON, reference populations, original data and V1 numerical files were not written.

## Prior corrections and eligibility

Batch 1's 91 recoveries, Batch 2A's five off-field corrections including Juanfran's removed phantom, Batch 2B's 10 published/26 nonpublished entries, Batch 3A's 3 published/9 nonpublished exits and all 17 terminal observations retain their decisions. Batch 3B's four Weber pressure successes/attempts remain withheld from corrected diagnostics; that layer is not promoted into general production source reconstruction. Fernandinho's conservative candidate-name/source-admission restriction remains; no frontend/backend aliases were added. Conflicting post-dismissal activity, unsupported exits and invalid chronology remain excluded. Source coverage and pending fixture 3879594 policy remain intact. Ranking consequences: **zero eligibility changes**; clearing a helper reuse risk does not add a frozen-reference member or supported observation.

## Regressions and verification

The new suite has 28 inventoried tests with subcases covering all 35 requested scenario categories. Identity coverage includes homonyms, verified same-ID spellings, Unicode/apostrophes, different IDs/teams, transfers, seasons, missing/null/invalid IDs and contexts, duplicate/conflicting UUID identities, unsafe explicit grouping and missing columns. Existing integrated identity tests also retain conflicting crosswalk/source-ID rejection and duplicate raw UUIDs including excluded events. Join coverage includes duplicate denominators, one-to-one/many-to-one, repeated types/zones, unmatched/empty denominators, empty counts, missing/zero/negative/nonfinite exposure, below/exact thresholds and no row/numerator mutation. Totals/by-zone and type conservation include missing source location. Canonical integrated outputs, exact float rates, fixture-specific keys, input immutability and legacy safe-failure compatibility are checked.

Exact completed results (overlapping suites are not summed):

| Suite | Passed | Failed | Skipped | Blocked | Deselected |
| --- | ---: | ---: | ---: | ---: | ---: |
| targeted | 252 | 0 | 0 | 0 | 0 |
| helper-regressions | 28 | 0 | 0 | 0 | 0 |
| public-backend | 1191 | 0 | 0 | 0 | 0 |
| private-backend | 51 | 0 | 0 | 0 | 125 |
| original-source-regressions | 16 | 0 | 0 | 0 | 0 |
| independent-regressions | 12 | 0 | 0 | 0 | 0 |
| identity-probes | 12 | 0 | 0 | 0 | 0 |
| public-frontend | 211 | 0 | 0 | 0 | 0 |
| private-frontend | 33 | 1 | 0 | 0 | 0 |
| production-build | 1 | 0 | 0 | 0 | 0 |
| full-population-numerics | 1 | 0 | 0 | 0 | 0 |
| source-hash-uuid-frozen-transfer-verification | 1 | 0 | 0 | 0 | 0 |
| original-recovery-controls | 7 | 0 | 0 | 0 | 0 |

Verification rows for population/source controls count completed checks, not pytest cases. The known private frontend failure is exactly `provisionalOvr.test.js:61`, the badge-label typography expectation; its complete assertion and log are retained. No unrelated frontend expectation was edited. Private backend runs the authorized original private test source against the new worktree's production modules, with read-only original evidence; 125 nonselected cases are explicitly deselected. Private frontend runs the retained private-suite checkout without editing it; current frontend production sources were checked unchanged. Public frontend/build run in the new worktree.

Failed attempts are retained: initial helper fixture-name ImportError (27 passed/1 failed), the repeated targeted harness run before the UTF-8 fix (147 passed/1 failed), the Windows cp1252 edit-command error, and the first source verification stopping on the stale historical diagnostic self-receipt. The fixture import and UTF-8 issues were fixed; the final targeted run passed. These are not reclassified as known product failures. Final verification logs, commands, return codes and log hashes are in test-results.json. Failed-attempt explanations/logs are kept rather than deleted.

Reproduction from this worktree, with the retained sibling/private evidence:

```powershell
python -B -m pytest tests/test_safe_recovery.py tests/test_recovery.py tests/test_identity.py tests/test_identity_evidence.py tests/test_match_scoped_metrics.py tests/test_provisional_metrics.py tests/test_event_chronology.py -q -p no:cacheprovider
python -B -m scripts.run_backend_tests public -q
python -B audit-output/recovery-helper-hardening/run-private-backend.py
python -B -m scripts.check_off_field_card_sources
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/test_independent_audit.py
python -B -c "import src,runpy; runpy.run_path('../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/identity_probes.py',run_name='__main__')"
npm.cmd run test:public --prefix frontend
npm.cmd run test:private --prefix ../Soccer-Impact-Engine-Index-identity-source-reconciliation/audit-output/private-suite-checkout/frontend
npm.cmd run build --prefix frontend
python -B -m scripts.verify_batch4_numerics
python -B -m scripts.verify_recovery_helper_hardening
```

`verify_batch4_numerics` deliberately refuses an existing output directory. Preserve completed/failed evidence and use a fresh isolated checkout for a complete rerun, or reuse its hash-bound completed output for the Batch 5 verifier. The final seven-source controls were rerun after adding the Rosa fixture and independent direct-rate assertions; exact supplemental command/log is in test-results.json. Input data is read-only; scripts create only ignored diagnostic artifacts.

## Deliverables and remaining boundary

Modified/added review files, complete inventory:

1. `src/metrics/safe_recovery.py` — guarded reuse API.
2. `tests/test_safe_recovery.py` — 28 synthetic regressions plus integration parity.
3. `tests/suite_inventory.json` — explicit public classification of those 28 cases.
4. `scripts/verify_recovery_helper_hardening.py` — reproducible independent source binding, original controls and A–H/frozen/transfer comparison.
5. `docs/m2b-recovery.md` — safe API discovery and legacy boundary.
6. `docs/recovery-helper-hardening-report.md` — this report.

All requested private deliverables exist under `audit-output/recovery-helper-hardening/`: original-helper-reproduction.json, helper-callsite-inventory.csv, provenance-compatibility-review.json, grouping-comparison.csv, join-cardinality-comparison.csv, raw-count-conservation.json, player-impact.csv, full-population-comparison.csv, unresolved-risks.csv, summary.json, input-hashes.json, test-results.json and artifact-inventory.json. Supplemental original-source controls, historical-stage arithmetic, historical self-receipt differences, suite harnesses, logs and failed-attempt evidence remain ignored. Artifact inventory binds each listed review/generated file, excluding its own recursive hash, without traversing data/dependency junctions.

The seven explicit decisions are: (1) provenance-bound bodies retained; (2) separate guarded adapter introduced; (3) existing production callers unchanged; (4) no forced contributor migration; (5) no real-data numerical/association change; (6) unguarded historical API intentionally remains accessible; (7) external usage cannot be fully inventoried and the historical diagnostic self-receipt discrepancy remains documented, while the helper provenance itself is intact.

For Ratings V2, use the guarded API for new pre-resolved helper reuse and keep the existing integrated resolver for raw events. Review historical source/chronology/coverage and reference decisions separately. This hardening provides no justification for a reference refit, new eligibility, a new public snapshot or V2 deployment. Keep all changes local for review.
