# Phase 3 Step 2: source player reconstruction

Completed offline October 28, 2026, on `integration-foundation`, HEAD
`96b3989e09d1349ed5313b0d7b1ec6471ae7e21a`. This report recovers the interrupted
reporting step. The existing reconstruction was verified and reused, not rebuilt.
**SOURCE-SUPPORTED CANDIDATES / NOT PRODUCTION CERTIFIED.**

## Reconstructed evidence

The sealed directory is
`data/derived/phase3-step2-source-reconstruction-2026-10-27/`. Its date records
the session start. Its 21 artifacts occupy 1,725,028,333 bytes. Manifest SHA256:
`2376fe773b709cf620a5cbf29c9a150ad2b32acd88291ff2f696deef1f2b94de`.

| Fact | Result |
| --- | ---: |
| Provider matches reconstructed | 1,517 |
| Original events processed | 5,321,459 |
| Roster actor/match records | 57,665 |
| Active appearances | 42,100 |
| Structurally valid / contradictory / incomplete | 40,640 / 1,095 / 365 |
| Roster records without asserted appearances | 15,565 |
| Stable player IDs / player-season summaries | 2,177 |
| Player-club contexts | 2,280 |
| Known supported elapsed minutes | 3,072,230.645066667 |
| Complete observed provider exposure contexts without review flags | 1,322 |
| Source-complete 900-minute CB/DM/CM candidates | 238 |
| Candidates with aligned core component scopes | 236 |
| Certified season contexts / real ratings generated in Step 2 | 0 / 0 |

Exact supported minutes are `11520864919 / 3750`. Rational durations preserve
source clock precision, supported stoppage time, exclusion of halftime and gaps,
and position allocation. The exposure convention still requires team approval.
The 1,460 unresolved appearances retain null minutes and position allocations;
their withheld total is unknown, not zero or an estimated residual. Their
observations, conflicts and raw metric counts remain intact.

| League, 2015/16 | Provider / delivered fixtures | Valid / contradictory / incomplete | Club contexts | 900-minute candidates | Known supported minutes |
| --- | --- | --- | ---: | ---: | ---: |
| La Liga | 380 / 380 | 10,278 / 243 / 32 | 546 | 60 | 767,022.182700 |
| Premier League | 380 / 380 | 10,254 / 161 / 54 | 561 | 79 | 790,325.423533 |
| Serie A | 380 / 379 | 10,055 / 352 / 192 | 585 | 51 | 757,594.266050 |
| Ligue 1 | 377 / 377 | 10,053 / 339 / 87 | 588 | 48 | 757,288.772783 |

Provider inventory coverage does not certify historical season completeness.
Ligue 1's 377 matches do not establish 380 historical fixtures. The three
unlisted schedule slots have no independently verified IDs here. Serie A
`3879594` remains source evidence only, with separate provider/delivered-scope
comparisons. No delivered scoring dataset includes it through this work; team
scope approval remains necessary. Its source inclusion changes none of the 238
candidate threshold decisions.

## Identity reconciliation

All 3,626,433 delivered UUIDs were indexed uniquely. The four target contexts
contain 2,974,680 delivered events, all matched by original UUID, match,
competition, season, normalized team/player name and event type. Zero target
delivered events are unmatched. Source UUIDs are also globally unique. Original
IDs supply the identity missing from delivered events through the UUID/context
association; no name-only ID assignment is invented. SQLite `seen` means UUID
presence, not independent identity attestation.

Of 2,280 active source club contexts, 2,279 have exact source-ID/delivered-name
crosswalk mappings; one lacks a matching name mapping. No ambiguous delivered
mapping or source normalized-name collision key was observed.

Ten contexts retain identity/activity review flags, which are not ten proven
incorrect identities:

- Player `3054`, Manchester City: source names include Fernando Luiz Rosa and
  Fernando Luiz Roza; candidate/source name disagreement remains unresolved.
- `6672` Sevilla, `10612` Rayo Vallecano, `26023` Levante UD, `40458` Juventus:
  source versus delivered appearance classifications disagree.
- Five active club contexts retain conservative no-stint source-activity flags.
  Six events across players `27348`, `158769`, `7105`, `25859`, `27457`, `10448`
  were inspected. All are Bad Behaviour / Yellow Card records, position
  Substitute, with empty roster positions for those matches. One actor has no
  active club context. These events imply no playing time and no minutes were
  imputed. The review flags remain; no automatic correction was applied.

The unresolved source inventory has 1,466 records: 1,460 participation records
and six activity records. Numerator scope issues have a separate inventory.

## Minutes, eligibility and numerators

The 900-minute gate uses complete observed provider exposure, no unresolved
appearance or identity/review flag, exact supported minutes and existing
delivered role labels. Source position minutes remain separate from those role
labels; no season role policy is inferred. The 238 contexts comprise 111 CB,
86 DM and 41 CM (127 MID). They are not approved reference members.

Across all roles, 1,338 contexts have known subsets above 900; that weaker fact
does not establish full observed exposure. Of the earlier 549 table-qualified
contexts, 234 pass the stronger source gate and 315 do not. Four new conditional
candidates cross 900 using supported elapsed time: `9461` Norwich City
(910.586467), `17520` Empoli (939.975267), `31572` Hellas Verona (914.072283),
`386509` Frosinone (932.498633). Their role/exposure policies remain pending.

| Existing candidate measurement | Raw source count | Complete aligned club-rate contexts |
| --- | ---: | ---: |
| Tackles | 36,493 | 1,322 |
| Interceptions | 22,898 | 1,322 |
| Recoveries | 150,721 | 1,318 |
| Pressured pass attempts / completions | 231,678 / 158,191 | 1,322 |
| Pressured dribble attempts / completions | 52,321 / 29,079 | 1,322 |
| Progressive attempts / completed passes | 217,248 / 94,777 | 1,322 |
| Progressive third crossings | 60,664 | 1,322 |

Raw counts include unresolved appearances; they are not automatically usable
season numerators. Each selected event retains its original UUID. Legitimate
zeros follow a full original-array scan for the identified actor. Missing
delivered component rows remain missing, not zero.

Existing recovery extraction, press-action counts/completion helpers, passing
preparation and progressive flags are reused unchanged. No individual rating
formula is approved by reconstructing a count. Full-source counts, aligned subset
counts/minutes/rates, and complete provider-scope rates remain separate. Per90
requires positive valid elapsed exposure and all selected event times within
validated intervals and boundaries. A whole-source numerator never uses a
partial supported denominator.

Nine valid appearances contain recovery events outside validated exposure;
their rates remain withheld without clipping or moving events. Four otherwise
complete contexts lose full recovery rates. Two of the 238 candidates are
affected: `3407` Crystal Palace and `4380` Nantes. The remaining 236 have aligned
tackle/interception/recovery/press scopes. Detailed event IDs, source clocks,
intervals and boundaries are in the supplementary numerator-scope review.

For delivered fixture scope, 3,081 comparable defensive component rows agree
exactly; 3,759 delivered component rows are absent. No comparable count
disagreement was found. Complete source minutes differ from delivered minutes
in 448 comparable contexts. These are convention/coverage comparisons requiring
review, not automatically errors. Partial source totals are not compared as
complete exposure.

Passing preparation found 1,481,813 pass events, 1,310,016 measurable passes after
existing filters, and zero missing-geometry classifications. Progressive passes
remain Level A candidate counts. They are not true line-breaking passes.
Difficulty is unknown; no calibrated pass value is exported. The flat 360 table
contains zero rows for the four target 2015/16 contexts; unrelated-season frames
are not substituted. True line breaking stays null pending definition/evidence.

## Transfer and production decisions

There are 103 multi-club player-seasons, 38 spanning target leagues. Separate
clubs, combine-within-league, and combine-across-target-leagues are explicitly
unapproved alternatives. Raw counts/minutes are summed without duplicate match
contributions. No reference context is nominated and no scored ratings averaged.

Four all-role player-season threshold comparisons change if pooling is approved:

| ID | Club minutes | Combined minutes |
| --- | --- | ---: |
| 3951 | Juventus 772.594967; Marseille 349.029767 | 1,121.624733 |
| 9593 | Bournemouth 632.388933; Norwich 270.000917 | 902.389850 |
| 23329 | Palermo 670.393150; Reims 680.430417 | 1,350.823567 |
| 23488 | Fiorentina 489.375750; Watford 809.579033 | 1,298.954783 |

These are not automatic MID/CB admissions. A second club's unresolved appearance
can also prevent a complete pooled denominator despite a large known subset.

Production blockers: independent actor/provenance attestation; approved handling
of 1,460 unresolved appearances, identity/appearance discrepancies, substitute
activity flags and nine recovery scope mismatches; exposure/role approval;
historical Ligue 1 coverage; `3879594` rebuild scope; metric reportability;
transfer/reference membership; individual defensive FIFA and press policies;
true line-breaking definition/evidence; OVR; and the production evidence and
publication contract. Zero production-certified contexts were declared.

## Artifacts, validation and preservation

Implementation: `src/source_reconstruction.py`,
`scripts/reconstruct_player_evidence.py`, `scripts/audit_source_reconstruction.py`,
`tests/test_source_reconstruction.py`. Existing identity, participation, season
readiness and metric implementations were reused. Scoring and delivery modules
were not changed. Existing alias corrections remain intact.

The sealed core contains appearance/roster ledgers, match coverage, club/season
summaries, eligibility matrix, raw measurements, numerator/denominator and
delivered-component reconciliation, identities/collisions, unresolved inventory,
transfer comparisons, coverage/360/readiness reports, summary, SQLite UUID index,
input receipts and run manifest. The manifest enumerates every artifact, code
hash and runtime version. Input receipts bind all source/review and delivered
inputs. Supplementary review is separate in
`data/derived/phase3-step2-review-2026-10-28/`.

The provider revision is `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`; source
manifest SHA256 is
`756d0cbe3fdcbfb9c753da97f861004dccc44db271f863d035bf58fda324cfa2`;
current review-index SHA256 is
`28702f87e0acbb9465b98eee25dfaf5868e277fd63f63191d49412166596a8f2`.

Recorded regression results: 883 Python tests (all 861 original plus 22 new),
warnings treated as errors; 154 frontend tests; no failures or skips. Focused
22-test rerun passed. Small deterministic rebuilds match every artifact byte,
including SQLite. The real bundle passed idempotent reuse with all inputs and
artifacts rehashed, all 21 file sizes/mtimes unchanged. No second full real-data
rebuild is claimed or needed to continue.

Independent checks passed for uniqueness, position/exposure conservation, count
cardinality, rate/scope arithmetic, aggregate count/minute conservation, transfer
joins and trust gates. Tests cover ambiguous IDs, duplicates, missing coverage,
contradictions/incomplete exposure, bench/orphan actors, 900-minute boundaries,
numerator alignment, transfer alternatives, fingerprints, tampering and partial
output refusal. No safety test was weakened.

All 12,250 files present before Step 2 (5,954,175,171 bytes) matched starting
SHA256/size, with zero changed or missing files. This includes 11 protected
Parquets, Arpit's fixture snapshot, original sources/reports, M4A documents,
frontend files and prior alias code/tests. No network retrieval, staging,
commit, push, publication or deployment occurred. Branch/HEAD stayed unchanged;
the two tracked modifications were the pre-existing alias files only.

Reusing the existing reconstruction path verifies receipts/code/artifacts and
returns the summary without writes. Partial/conflicting directories refuse
overwrite. The current continuation must not rebuild the SQLite index or ledgers.
Step 3's separate report records the maximum permitted candidate analysis and
remaining website handoff work. Reconstructed facts alone do not bypass engine
evidence or production gates.
