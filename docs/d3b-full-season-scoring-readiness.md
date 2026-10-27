# D3B — full-season scoring population readiness

Audit date: October 27, 2026. **Production scoring: BLOCKED / NOT ESTABLISHED.**
All requested local files are available. The audit completed; no additional
download is assumed necessary. No real percentiles, DRI scores, FIFA ratings,
tiers, final OVR or public score outputs were generated.

## Scope, prerequisite and labels

D3A is committed at `c64534a5f9781bf7e2786bcc2e71398224558144`.
Approved scope remains 2015/2016, jointly La Liga / Premier League / Serie A /
Ligue 1, with separate MID (DM+CM) and CB pools and ≥900 minutes.
Equal defensive component weights, DRI mathematics and approved tier boundaries
are unchanged. This audit never calls `score_dri` or a rating/tier helper.

- **STRUCTURALLY VALID:** exact-key, numeric, join and conservation findings.
- **PROVISIONAL:** caller-supplied name-to-ID matching, delivered role/minute
  conventions and event-derived match associations.
- **PRODUCTION VERIFIED:** not established for any candidate.
- **BLOCKED / NOT ESTABLISHED:** independent complete-source, identity/context,
  exposure and per-component reportability evidence needed by D3A.

Source presence, arithmetic consistency and delivered eligibility flags are
different claims. Passing the first two does not establish the last.

## Inputs and fingerprints

All inputs were read-only. The authoritative audit pair is the October 21
corrected minutes/recovery delivery; the refresh pair is a comparison. Original
processed minutes/recovery are comparison-only, never replacements.
The 360 file is integrity-checked only; it is not used to infer fixture coverage.

| Preserved local file | SHA256 | Integrity |
|---|---|---|
| `data/processed/player_minutes.parquet` | `9701ec4a74b1a75ee6094f08619c40b26f6d6f103d64a23ca2802448351e931b` | PASS |
| `data/processed/player_name_crosswalk.parquet` | `a250ac8074967aad3b1fdcd35a849584658ac333a4049d1de3845f443d2397e7` | PASS |
| `data/processed/recovery_per90.parquet` | `056f94b0bd49bc707e5d00181d0b85654cd076e5dc3bc09e1a6c121cd530ee4d` | PASS |
| `data/raw/statsbomb_lineups.parquet` | `dfb6e2f0adfb1ec25c879b26feb3616b8683c64e152657f098edc20aa1635be2` | PASS |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | `01f1bb2650df4f793971465eefad49eefcd41a302789b5c5009cf7355a4b1694` | PASS |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | `7a546348b2c391d32221456fab259d639910d13c8e672ba030e6d30b38cab61f` | PASS |
| `data/validation/arpit-match-context-review/match_metadata.parquet` | `1b1de360e0f31c49aabd43d065f95fe0762d29a31ea2bcba21b54571b86f3b47` | PASS |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | `5600f1250a3bd7fcf9d12a9d11ecac4ae9d39cd58898d6e6df1e5d4d1aa1830e` | PASS |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | `5b53d544662826206511e2d2c532297160b781f84958b2acf615195590f82012` | PASS |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | `497fa459e1ee99f758ed37d405d69285af5e6759306851456d03fde8c4025625` | PASS |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | `ec12fdd2340fb125671f4996abdac510c3dc6d81555848792520ce5df2519eb8` | PASS |

The primary audit reads ten explicit paths: events, lineups, crosswalk, October
21 minutes/recovery, refresh minutes/recovery, metadata and original processed
minutes/recovery. It projects needed fields only; delivered pctl/pool_n fields
are not consumed as scoring evidence.

## Actual local event and lineup coverage

The scan traversed all **3,626,433** raw rows in Arrow batches of at most 65,536,
retaining only compact summaries. **2,974,680** rows fall in the approved scope;
651,753 other-season/competition rows do not enter the target identity audit.
Global valid event IDs: 3,626,433 unique, zero duplicates (checked across batches
with a temporary disk index). Target valid IDs: 2,974,680 unique.

| League | Target event rows | Observed matches | Match/team contexts | Teams | Lineup rows | Lineup matches |
|---|---:|---:|---:|---:|---:|---:|
| La Liga | 738,475 | 380 | 760 | 20 | 16,734 | 380 |
| Premier League | 741,442 | 380 | 760 | 20 | 15,926 | 380 |
| Serie A | 742,064 | 379 | 758 | 20 | 21,440 | 379 |
| Ligue 1 | 752,699 | 377 | 754 | 20 | 18,307 | 377 |
| Total | 2,974,680 | 1,516 | 3,032 | 80 league/team contexts | 72,407 | 1,516 |

Every observed target match and match/team pair has lineup records. Missing
lineup matches, lineup matches absent from the target source, and match/team
association differences are all zero. All 86,743 global lineup rows map without
loss to the delivered metadata; target subset is 72,407 rows.

Match counts alone do **not** establish complete seasons. This audit has no
independently supported expected-fixture ledger identifying which fixtures must
exist, nor source acquisition/failure accounting demonstrating their coverage.
It does not infer that specific fixtures are missing merely from 377/379 counts.

Observed normalized teams:

- La Liga: Athletic Club; Atlético Madrid; Barcelona; Celta Vigo; Eibar;
  Espanyol; Getafe; Granada; Las Palmas; Levante UD; Málaga;
  RC Deportivo La Coruña; Rayo Vallecano; Real Betis; Real Madrid;
  Real Sociedad; Sevilla; Sporting Gijón; Valencia; Villarreal.
- Premier League: AFC Bournemouth; Arsenal; Aston Villa; Chelsea; Crystal Palace;
  Everton; Leicester City; Liverpool; Manchester City; Manchester United;
  Newcastle United; Norwich City; Southampton; Stoke City; Sunderland;
  Swansea City; Tottenham Hotspur; Watford; West Bromwich Albion; West Ham United.
- Serie A: AC Milan; AS Roma; Atalanta; Bologna; Carpi; Chievo; Empoli;
  Fiorentina; Frosinone; Genoa; Hellas Verona; Inter Milan; Juventus; Lazio;
  Napoli; Palermo; Sampdoria; Sassuolo; Torino; Udinese.
- Ligue 1: AS Monaco; Angers; Bastia; Bordeaux; Gazélec Ajaccio; Guingamp; Lille;
  Lorient; Lyon; Montpellier; Nantes; OGC Nice; Olympique de Marseille;
  Paris Saint-Germain; Rennes; Saint-Étienne; Stade Malherbe Caen;
  Stade de Reims; Toulouse; Troyes.

Target source types: 1,480,782 Pass; 1,116,448 Carry; 162,555 Ball Recovery;
125,042 Duel; 52,294 Dribble; 37,559 Interception. This is a filtered action
collection, not the full boundary/substitution event feed needed to independently
reconstruct every participation endpoint.

Target null counts are zero for event ID, match ID, player, team, competition,
season, type, position, location and clock fields. Invalid identity rows and
invalid clock rows: zero. Optional outcome/failure fields are often inapplicable:
duel_type null 2,849,638; duel_outcome null 2,914,524; interception_outcome null
2,937,121; ball-recovery failure flag null 2,962,730. Those nulls retain existing
M2B semantics; they are not silently treated as invalid actors.

## Provisional identity and source associations

Explicit selected population: all **840** delivered DM/CM/CB target contexts,
including under-900 contexts. Known outsiders are successfully mapped contexts
outside that selection, not unresolved names.

| League | Selected candidate events | Known outside population | Unresolved | Invalid identity |
|---|---:|---:|---:|---:|
| La Liga | 305,637 | 432,838 | 0 | 0 |
| Premier League | 315,165 | 426,277 | 0 | 0 |
| Serie A | 379,311 | 362,753 | 0 | 0 |
| Ligue 1 | 348,733 | 403,966 | 0 | 0 |
| Total | 1,348,846 | 1,625,834 | 0 | 0 |

Every target row is conserved exactly once; duplicate joins: zero.
Missing actors, unknown normalized name/context keys, conflicting source keys
and events affected by conflicts: zero.

D1B-P's lookup validation and M2A resolver/normalization are reused unchanged.
The global crosswalk has 5,578 source/normalized/usable mappings, zero identical
duplicate mappings and zero conflicting normalized keys; 2,281 mappings are
within target scope, for the 2,279 corrected canonical minute contexts.
Alternative spellings remain observations, not extra players.
M2A name cleanup changes 29,220 target event labels, and its two declared team
aliases change 18,721 event team labels. No fuzzy matching or new aliases occur.

All **41,923** known actor/match/team keys and their normalized original spelling
observations match lineups. ID/team/match and spelling discrepancies: zero.
Match-to-competition/season conflicts and event/metadata disagreements: zero.

**CONTRIBUTOR-REPORTED PROVENANCE:** Arpit reported fetch_lineups followed by
player_minutes, with the crosswalk produced by player_minutes.
Match metadata was extracted from events, **not sb.matches**. Original lineup
records do not contain independent competition/season fields.
The cardinality-safe metadata join here is explicitly provisional; no D1
VERIFIED_SOURCE_EVIDENCE object or trusted crosswalk is constructed.
Matching event-derived associations cannot independently validate themselves.

## Delivered recovery integrity and reconciliation

| League | Corrected minute contexts, all roles | Recovery contexts | Recovery rows | Zero-minute contexts, all roles |
|---|---:|---:|---:|---:|
| La Liga | 546 | 233 | 699 | 2 |
| Premier League | 561 | 234 | 702 | 2 |
| Serie A | 584 | 295 | 885 | 2 |
| Ligue 1 | 588 | 265 | 795 | 4 |
| Total | 2,279 | 1,027 | 3,081 | 10 |

Target minute-role distribution: CB 362, DM 294, CM 184, GK 197, FB 408, WM 111,
AM 105, ATT 618. No missing target minutes; role-minute sums equal delivered
total minutes. The ten zero-minute contexts are outside the candidate roles.

Across the complete corrected recovery file: **7,680 rows / 2,560 contexts**,
zero duplicate canonical component keys, absent minute identities, contradictory
component metadata, minute/match/role disagreements with corrected minutes, or
meets_min discrepancies. All 7,680 supplied positive-minute arithmetic checks
satisfy `per90=count/minutes*90` at relative/absolute tolerance 1e-9.
This checks internally paired **delivered** values; independent numerator/exposure
alignment remains unestablished. No raw-source rates were manufactured.

October 21 and refresh tables agree exactly on every projected key and core
field, including minutes, position-minute fields, role, matches, counts, per90
and coverage/reportability flags. No refresh substitution was necessary.
Original processed minutes have **two duplicate canonical keys**; original
recovery has **three duplicate component keys** and one conflicting canonical
context's role/minute/match metadata. These original rows were counted, never
resolved by choosing a first occurrence or used as corrected replacements.

The local count reconstruction uses the **unchanged M2B successful-event
extractor**, including nullable failure-flag handling:

| Component | Candidate events | Known-outsider events | Unresolved |
|---|---:|---:|---:|
| Successful tackles | 18,989 | 17,479 | 0 |
| Interceptions | 12,731 | 10,154 | 0 |
| Ball recoveries | 65,182 | 85,423 | 0 |

Candidate counts match delivered totals on **2,382 shared canonical component
rows**, with zero count discrepancies. All 549 table-qualified contexts have
three observed positive component rows: **1,647 shared rows**, none zero-filled.

The other **138 candidate delivered component rows** have count=0 and per90=0, across
87 under-900 contexts: 48 Tackle, 72 Interception, 18 Ball Recovery.
M2B has no observed component row for those keys. They remain classified
delivered-only; the audit does not create observed zero measurements.
The contributor grid explicitly fills absent counts with zero. This is a source
assumption, not independent reportability evidence.

Across all target delivery roles: 2,576 shared rows with zero count differences;
505 delivered-only zero rows; 3,341 source-only rows largely outside the delivered
GK/CB/DM/CM recovery reporting selection. These population/category differences
are not evidence of a changed extraction formula.

All counts above cover **every local target row**. Their agreement supports
local-source reconciliation, not equality to an independently established
complete-season numerator. A common omission in events, derived metadata and
deliveries could pass all these checks.

## Exact candidate and 900-minute accounting

| League | MID candidates | MID below900 | MID table-qualified | CB candidates | CB below900 | CB table-qualified |
|---|---:|---:|---:|---:|---:|---:|
| La Liga | 101 | 34 | 67 | 89 | 27 | 62 |
| Premier League | 106 | 37 | 69 | 81 | 22 | 59 |
| Serie A | 142 | 58 | 84 | 104 | 37 | 67 |
| Ligue 1 | 129 | 55 | 74 | 88 | 21 | 67 |
| Total | **478** | **184** | **294** | **362** | **107** | **255** |

Candidate total **840 contexts** (DM 294 + CM 184 + CB 362), matching the historical
count independently. All 840 have three delivered component records, complete
numeric values, and all component reportable/full_coverage flags true.
Missing component records, flagged incomplete coverage and flagged
unreportability: zero. Missing/zero candidate minutes: zero.
**291** fail the 900-minute check; **549** pass all delivered-table checks.
No candidate is independently source/identity/exposure verified; production-ready
count remains **0**, not 549.

One delivered role tie occurs below threshold: Joleon Lescott (20285),
West Bromwich Albion / Premier League, CB, 180 minutes, tied_groups=2.
No table-qualified context has a delivered tie. Delivered dominant-role labels
remain inherited conventions, not independently approved role/exposure evidence.

The exact ordered candidate ledger is returned as
`ReadinessResult.candidates`; `--list-candidates` prints all 840 canonical keys,
source names/roles/minutes, structural flags and explicit false production
verification fields. It does not write a candidate dataset.
`--list-matches` includes exact observed match-ID ledgers in terminal output.
Inputs, fingerprints and selection predicates make this population reproducible.

### Transfers: contexts are not distinct reference players

All candidates include **54 contexts for 27 transferred player IDs**
(813 distinct candidate IDs). The table-qualified subset contains **549 contexts
but 547 distinct IDs**. Four qualified contexts belong to two players:

| ID | Player | Team | League | Delivered role | Minutes |
|---|---|---|---|---|---:|
| 3057 | Jonjo Shelvey | Newcastle United | Premier League | DM | 1048.433333 |
| 3057 | Jonjo Shelvey | Swansea City | Premier League | CM | 1217.150000 |
| 13286 | Lamine Koné | Lorient | Ligue 1 | CB | 1574.250000 |
| 13286 | Lamine Koné | Sunderland | Premier League | CB | 1314.550000 |

No reference contexts are automatically selected or collapsed. Under D3A's
conservative one-reference-context safeguard, using all 549 would double-weight
two players. Deferring all four ambiguous contexts leaves 545 contexts
(MID 292 / CB 253); explicit single-context choices could yield at most 547
(MID 293 / CB 254). These are **potential structural pool sizes only**, not
approved reference selections or production eligibility.

## Exposure findings: explain differences before claiming contradictions

Candidate lineup subset: **26,496 rows**. Positionless/bench rows: 4,696.
Active stints with missing end times: **13,707**, all labeled Final Whistle;
832 of 840 contexts are affected, including **every one of the 549 table-qualified
contexts**. Cross-period stint rows: **5,020**.

Roster-inclusive distinct match counts differ from delivered matches for 694
candidate contexts, because roster membership includes bench appearances.
Even counting position-stint matches differs for 72 contexts (41 table-qualified);
these differences must not be called unexplained source corruption.

Read-only contributor-code inspection at local `origin/arpit-dev`
`9d53c04be0d687ba6f6650deac6ca89784557246` shows
`src/metrics/player_minutes.py` defaults missing starts to 0, missing ends to 90,
clips clocks to 0..90, and counts only positive-duration player/match totals.
Re-evaluating that convention on local lineup records yields:

- **0** candidate pooled-minute differences.
- **0** candidate positive-duration match-count differences.
- 326 active stint rows have zero duration under clipping.
- All 549 table-qualified contexts still rely on open active stint endpoints.

This explains the delivered aggregates and match counts without importing or
executing the writer. It **does not** validate those defaults as actual exposure,
resolve stoppage time/period boundaries, or approve a new minute convention.
The reusable audit labels this calculation contributor-compatibility only and
keeps independent exposure verification false.

The same contributor revision's `src/metrics/recovery_per90.py` defines delivered
full_coverage by a match-count threshold (default 300), reportability by role
(GK Ball Recovery only), and fills absent grid counts with 0. Inspection describes
the code convention; execution parameters for delivered generation are not
independently logged. Flags cannot substitute for expected-fixture coverage,
D1 identity/context evidence or component-specific acquisition/reportability
evidence. Its existing helper percentiles were neither consumed nor recomputed.

## Production-readiness conclusion and concrete requirements

**Calling D3A for a production cohort is not supported by the established
evidence.** Structural consistency and positive provisional identity matching
are useful and complete; they are not D3A evidence attestations.

What remains genuinely unestablished:

1. Independently supported expected-fixture/context coverage and acquisition /
   failure accounting for the approved four-league seasons. Event-derived
   metadata agrees structurally but is not an independent fixture manifest.
2. D1-compliant identity and match-context provenance, beyond delivered mapping
   consistency and contributor-reported acquisition lineage.
3. Per-context numerator/exposure match ledgers and validated participation
   endpoints/minute conventions, addressing the observed open final-whistle
   and cross-period records. Matching a default-to-90 calculation is insufficient.
4. Component reportability/coverage evidence beyond role flags and the
   documented absent-count zero-fill assumption.
5. Explicit reference-context decisions for the two qualified transferred IDs,
   with role handling consistent with the approved separate MID/CB policy.

No existing file is missing, and no blanket demand for more downloads follows.
First review existing contributor acquisition records, expected fixture lists,
source provenance and participation evidence. Obtain only the specific evidence
found unavailable through that review.

Recommended next milestone: establish those source/exposure records and explicit
reference membership in a private, validated population contract. Re-run this
readiness audit and D3A evidence checks before authorizing any in-memory real
scoring review. Do not bypass D3A or substitute the Bundesliga 2023/2024 diagnostic
profiles. Final OVR, line-breaking definition and the tentative pressure threshold
remain outside D3B.

## Reusable audit and verification

New files only:

- `scripts/audit_dri_readiness.py`
- `tests/test_dri_readiness.py`
- `docs/d3b-full-season-scoring-readiness.md`

The audit accepts ten explicit input paths; the event scan uses projected Arrow
batches, a maximum of 250,000 compact summary keys and a disposable disk-backed
global ID index (8 MiB SQLite cache). Small input tables are capped at 200,000
rows. No whole raw-event table is materialized. Temporary index files are cleaned
on success/failure; no scoring CSV/Parquet/JSON or other dataset output is written.
There are no network/ingestion operations. Terminal output is deterministic.
The primary full scan and the added small-table exposure compatibility check
were both executed against local inputs.

Run from the repository root:

```powershell
python -B -W error -m scripts.audit_dri_readiness `
  --events data/validation/drive-raw-review/statsbomb_team_events.parquet `
  --lineups data/raw/statsbomb_lineups.parquet `
  --crosswalk data/processed/player_name_crosswalk.parquet `
  --minutes data/validation/arpit-2026-10-21/player_minutes.parquet `
  --recovery data/validation/arpit-2026-10-21/recovery_per90.parquet `
  --refresh-minutes data/validation/arpit-refresh-review/player_minutes.parquet `
  --refresh-recovery data/validation/arpit-refresh-review/recovery_per90.parquet `
  --metadata data/validation/arpit-match-context-review/match_metadata.parquet `
  --original-minutes data/processed/player_minutes.parquet `
  --original-recovery data/processed/recovery_per90.parquet `
  --scratch-dir $env:TEMP
```

Append `--list-candidates` / `--list-matches` for exact terminal ledgers.
Missing paths, invalid numeric/flag/identity fields, corrected duplicate keys,
contradictory metadata and duplicate event IDs fail explicitly; conflicting
normalized lookup keys are quarantined and their unresolved events retained.
Invalid selected input is accounted separately, not silently discarded.
The audit returns full discrepancy and unmatched-name ledgers in memory; default
terminal discrepancy output is limited to 20 rows. The CLI uses UTF-8 so that
exact player-name ledgers remain printable on Windows.

Focused synthetic tests cover cohort/role isolation, 900-minute boundary,
duplicates/conflicts, missing components, unsupported fields, zero/missing
minutes, provisional flags, scope mismatches, selected/outside/unresolved/invalid
accounting, cross-batch duplicate IDs, bounded scanning, transfer preservation,
contributor-compatibility withholding, immutability, deterministic populations,
explicit paths, no source writes and no scoring/network/writer calls.

Final Python: `python -B -W error -m unittest discover -s tests -q` —
**520 passed** (491 existing +29 D3B). Recursive frontend JavaScript:
**99 passed**, none skipped. `git diff --check` and new-file whitespace checks pass.
All 11 Parquet hashes match the pre-work and D1B/D2C/D2D inventories.

All 125 pre-existing fingerprinted files are unchanged, including D3A scoring,
identity trust contracts, recovery/press/passing formulas, D2 interfaces, frontend
modes and the untracked M4A checklist. Branch remains `integration-foundation`;
HEAD remains `c64534a5f9781bf7e2786bcc2e71398224558144`; main remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. Existing untracked delivered data and
M4A remain preserved. No tracked modifications or staged files; no branch/worktree
operations, commits, pushes, deployments or production score outputs.

