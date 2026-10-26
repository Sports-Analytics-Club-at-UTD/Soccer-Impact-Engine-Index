# D1B: authoritative player identity source validation

Review date: October 26, 2026. **D1B IS NOT READY FOR PRODUCTION PROMOTION; D1B-P PROVISIONAL MATCHING WORKS.** The delivered lineup supplies original spelling/ID observations, but lacks competition/season. The subsequently delivered `match_metadata.parquet` passes structural and association checks. **CONTRIBUTOR-REPORTED PROVENANCE:** Arpit explicitly confirms it was extracted from `statsbomb_team_events.parquet`, not `sb.matches`; it is not an independent authoritative fixture manifest. Independent match-context provenance remains **NOT VERIFIED**. D1's production evidence gate remains unchanged; the separately authorized provisional diagnostic below uses the delivered crosswalk without a production trust attestation. No production crosswalk is reconstructed or promoted.

**VERIFIED FINDING** means a checked local file/code property. **CONTRIBUTOR-REPORTED PROVENANCE** records the supplied origin statement. **NOT VERIFIED** marks authoritative context, acquisition completeness, or source coverage that local consistency checks cannot establish.

## Input inventory and full SHA256 fingerprints

Hashes were captured before analysis. All ten inputs were opened read-only. The six original expected values below are taken directly from `docs/d1-identity-evidence.md`; the four new values establish the delivery fingerprints. Final rehash results appear in the integrity section.

| Input | Rows | Pre-analysis SHA256 |
|---|---:|---|
| `data/raw/statsbomb_lineups.parquet` | 86,743 | `dfb6e2f0adfb1ec25c879b26feb3616b8683c64e152657f098edc20aa1635be2` |
| `data/processed/player_name_crosswalk.parquet` | 5,578 | `a250ac8074967aad3b1fdcd35a849584658ac333a4049d1de3845f443d2397e7` |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | 5,576 | `5600f1250a3bd7fcf9d12a9d11ecac4ae9d39cd58898d6e6df1e5d4d1aa1830e` |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | 7,680 | `5b53d544662826206511e2d2c532297160b781f84958b2acf615195590f82012` |
| `data/processed/player_minutes.parquet` | 5,578 | `9701ec4a74b1a75ee6094f08619c40b26f6d6f103d64a23ca2802448351e931b` |
| `data/processed/recovery_per90.parquet` | 7,683 | `056f94b0bd49bc707e5d00181d0b85654cd076e5dc3bc09e1a6c121cd530ee4d` |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | 5,576 | `01f1bb2650df4f793971465eefad49eefcd41a302789b5c5009cf7355a4b1694` |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | 7,680 | `7a546348b2c391d32221456fab259d639910d13c8e672ba030e6d30b38cab61f` |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | 3,626,433 | `ec12fdd2340fb125671f4996abdac510c3dc6d81555848792520ce5df2519eb8` |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | 7,562,022 | `497fa459e1ee99f758ed37d405d69285af5e6759306851456d03fde8c4025625` |

The first four rows are new deliveries; the remaining six are the original D1 baseline. No Parquet was overwritten, regenerated, or replaced. Metadata and projected columns were used. Large event data was streamed in Arrow batches for match/context distinctness only; only the first 4,096 event rows were converted to pandas. The 360 table was inspected by metadata and fingerprint only.

## Actual schemas and null counts — VERIFIED FINDING

### `data/raw/statsbomb_lineups.parquet` — 86,743 rows

```text
match_id: int64
team: large_string
player_id: int64
player_name: large_string
player_nickname: large_string
jersey_number: int64
position_id: double
position: large_string
from_time: large_string
to_time: large_string
from_period: double
to_period: double
start_reason: large_string
end_reason: large_string
```

| Column | Null rows |
|---|---:|
| `match_id` | 0 |
| `team` | 0 |
| `player_id` | 0 |
| `player_name` | 0 |
| `player_nickname` | 49,598 |
| `jersey_number` | 0 |
| `position_id` | 18,350 |
| `position` | 18,350 |
| `from_time` | 18,350 |
| `to_time` | 58,275 |
| `from_period` | 18,350 |
| `to_period` | 58,275 |
| `start_reason` | 18,350 |
| `end_reason` | 18,350 |

### `data/processed/player_name_crosswalk.parquet` — 5,578 rows

```text
player_id: int64
player_name_raw: large_string
team: large_string
competition_name: large_string
season_name: large_string
```

| Column | Null rows |
|---|---:|
| `player_id` | 0 |
| `player_name_raw` | 0 |
| `team` | 0 |
| `competition_name` | 0 |
| `season_name` | 0 |

### `data/validation/arpit-refresh-review/player_minutes.parquet` — 5,576 rows

```text
player_id: int64
player_name: large_string
team: large_string
competition_name: large_string
season_name: large_string
min_GK: double
min_CB: double
min_DM: double
min_CM: double
min_FB: double
min_WM: double
min_AM: double
min_ATT: double
minutes: double
tied_groups: int64
position_group: large_string
in_scope: bool
matches: double
```

| Column | Null rows |
|---|---:|
| `player_id` | 0 |
| `player_name` | 0 |
| `team` | 0 |
| `competition_name` | 0 |
| `season_name` | 0 |
| `min_GK` | 0 |
| `min_CB` | 0 |
| `min_DM` | 0 |
| `min_CM` | 0 |
| `min_FB` | 0 |
| `min_WM` | 0 |
| `min_AM` | 0 |
| `min_ATT` | 0 |
| `minutes` | 0 |
| `tied_groups` | 0 |
| `position_group` | 0 |
| `in_scope` | 0 |
| `matches` | 22 |

### `data/validation/arpit-refresh-review/recovery_per90.parquet` — 7,680 rows

```text
player_id: int64
player: large_string
team: large_string
competition_name: large_string
season_name: large_string
position_group: large_string
matches: double
minutes: double
event_type: large_string
count: int64
per90: double
reportable: bool
meets_min: bool
full_coverage: bool
pctl: double
pool_n: double
pctl_note: large_string
```

| Column | Null rows |
|---|---:|
| `player_id` | 0 |
| `player` | 0 |
| `team` | 0 |
| `competition_name` | 0 |
| `season_name` | 0 |
| `position_group` | 0 |
| `matches` | 0 |
| `minutes` | 0 |
| `event_type` | 0 |
| `count` | 0 |
| `per90` | 0 |
| `reportable` | 0 |
| `meets_min` | 0 |
| `full_coverage` | 0 |
| `pctl` | 5,935 |
| `pool_n` | 5,935 |
| `pctl_note` | 0 |

Lineup `match_id` and `player_id` pass the existing M2A positive exact signed-int64 validation. Player names have zero null/blank values. Delivered crosswalk identity fields have zero null/blank values; its IDs pass M2A. Refreshed metric identity fields are non-null. All Arrow fields permit nulls at schema level; actual counts above are separate from that declaration.

## Contributor provenance and match-context gate

**CONTRIBUTOR-REPORTED PROVENANCE:** Arpit states that `statsbomb_lineups.parquet` was generated by `fetch_lineups`, the crosswalk by `player_minutes`, and the order was `fetch_lineups -> player_minutes`; refreshed minutes and recovery were uploaded together. This statement does not certify complete source coverage.

**VERIFIED FINDING:** read-only inspection of existing `origin/arpit-dev` at `0445f18fa1895320f0679ee84022888793fae6e7` shows `src/ingestion/fetch_lineups.py` flattening `statsbombpy.sb.lineups` into exactly the delivered 14-column structure, including bench rows and original player names. It obtains requested match IDs from events, omits competition/season, and may record failed fetches separately. Matching shape corroborates the statement but is not an execution/acquisition log.

The same contributor revision of `src/metrics/player_minutes.py` normalizes names/teams, chooses a display spelling, filters positionless rows, obtains match contexts from events, and writes distinct five-field spelling mappings. It warns on conflicting match contexts then keeps the first row; this policy is not accepted here. No contributor script was executed, fetched, merged, or adopted.

**VERIFIED FINDING:** lineup has 86,743 stint/bench rows, 1,814 distinct matches, 3,628 match/team pairs, 69,063 distinct match/team/ID/original-spelling observations, zero exact full-row duplicates, and 18,350 positionless rows. Thus 17,680 rows repeat identity observations through stints; they are not duplicate full source rows. Existing team aliases apply to 501 lineup rows; no new aliases were added.

Streaming all 3,626,433 event rows with only match/team/competition/season projected yields 3,628 distinct contexts. `validate_match_contexts(..., evidence_kind=DELIVERED)` accepts 1,814 unique match associations, with zero conflicting associations (the two teams account for 1,814 repeated match associations). All lineup matches and match/team pairs occur in event metadata, and all observed event matches occur in lineups. No arbitrary first conflicting association was chosen.

**NOT VERIFIED:** that association is event-derived, not an independent authoritative fixture manifest. No separate matches Parquet, fixture manifest, fetch failure log, acquisition record, or expected participation/season manifest is present in the local data inventory. Even perfect observed overlap cannot establish omitted fixtures or source authenticity/completeness.

Calling `validate_lineup_evidence(..., evidence_kind=DELIVERED)` on the actual context-free source rejects it with `lineups without direct contexts require a verified match association`. Passing the event-derived mapping cannot meet that verified-context requirement. No source is attested as `VERIFIED_SOURCE_EVIDENCE`; all 86,743 raw rows and all 5,578 delivered mappings are withheld from trusted use. This is a provenance/context hold, not an ambiguity quarantine.

## Delivered crosswalk audit and comparison

**VERIFIED FINDING:** `prepare_crosswalk` accepts the delivered structure under the unchanged M2A rules; acceptance checks shape and cardinality, not trust. There are 5,578 rows, 5,578 unique normalized spelling/context keys, 5,576 canonical player contexts, zero repeated identical mappings, zero normalized duplicate keys, and zero name/context keys with competing IDs. There are zero crosswalk team-alias rows and zero context-free name/team collisions with competing lineup IDs. Every delivered ID/name/team combination has a local raw lineup observation.

Two canonical contexts have two observed spelling variants, rather than conflicting IDs:

| ID | Team / competition / season | Observed spellings |
|---:|---|---|
| 3054 | Manchester City / Premier League / 2015/2016 | `Fernando Luiz Rosa`; `Fernando Luiz Roza` |
| 401453 | Stade de Reims / Ligue 1 / 2015/2016 | `David N'Gog`; `David N"Gog` |

These remain distinct spellings. No fuzzy lookup, global alias, accent repair, guessed ID, or first-ID selection was used.

**NOT VERIFIED — relational consistency only:** attaching the unique event-derived contexts in memory permits a non-authoritative set comparison, without passing those associations into trusted lineup validation or reconstructing a trusted crosswalk:

| Comparison | Shared exact mappings | Delivered-only mappings | Lineup-only mappings | Ambiguous keys |
|---|---:|---:|---:|---:|
| All lineup observations + event contexts | 5,578 | 0 | 1,259 | 0 |
| Position-present observations + event contexts | 5,578 | 0 | 0 | 0 |

The delivered crosswalk matches the contributor position-present extraction exactly under this unverified association. Its 1,259 missing mappings relative to the all-lineup comparison reflect mappings absent after position filtering; they must not be silently excluded from future bench-aware source evidence. No inconsistent ID mappings or extra delivered mappings were found in this relational comparison. Competition/season consistency is checked only against events, not independently validated.

**Trusted reconstruction:** `build_identity_crosswalk([])` yields zero input/verified observations, zero trusted entries, and zero conflicting keys. Eligible missing/extra/inconsistent source mappings are **not assessable** without validated authoritative context; comparing 5,578 delivered mappings against an empty eligible set would not prove them erroneous. Ambiguity quarantine is zero observed keys; provenance hold is all delivered mappings. The existing functions need no change.

## Refreshed minutes and recovery version comparison

**VERIFIED FINDING:** all compared versions have identical column names/order/types (excluding metadata). All refreshed files differ in SHA256 from both original and October 21 files. Refreshed and October 21 Arrow schema metadata differ, while every value agrees after alignment by the unique table grain, treating null/null as equal. Byte differences are not evidence of changed metric values.

| Table / version | Rows | Distinct canonical contexts | Repeated canonical rows beyond first | Duplicate rows beyond first at table grain |
|---|---:|---:|---:|---:|
| Minutes original | 5,578 | 5,576 | 2 | 2 |
| Minutes October 21 / refresh (each) | 5,576 | 5,576 | 0 | 0 |
| Recovery original | 7,683 | 2,560 | 5,123 | 3 |
| Recovery October 21 / refresh (each) | 7,680 | 2,560 | 5,120 | 0 |

Minutes grain is canonical player context; recovery grain additionally includes `event_type`. Three event types per recovery context account for the expected 5,120 repeated canonical rows; they are not duplicate metric records. Both refreshed versions have zero missing/extra canonical contexts against either baseline. No changed IDs were found on unique display-spelling/context keys (and event type for recovery); ambiguous original canonical records were reviewed separately rather than arbitrarily selected.

All 5,576 minutes rows and 7,680 recovery rows match October 21 exactly: zero changed metric/descriptor values and zero nullable identity differences. Against original files, 5,574 unambiguous minutes rows and 7,677 unambiguous recovery-grain rows agree across every shared non-key column. The remaining original duplicate groups differ as follows:

| Context | Original values | Revised / refreshed values |
|---|---|---|
| 3054, Manchester City, Premier League, 2015/2016 minutes | Rosa 2,640.6833333333334 + Roza 90 minutes; CM 955.8666666666667 + 90; roles DM and CM | Rosa 2,730.6833333333334 minutes; CM 1,045.8666666666666; DM; matches 33 |
| 401453, Stade de Reims, Ligue 1, 2015/2016 minutes | N"Gog 778.1666666666666 + N'Gog 75.38333333333334; ATT minutes 749.0166666666667 + 75.38333333333334 | N"Gog 853.55 minutes; ATT minutes 824.4; ATT; matches 16 |
| 3054 recovery Ball Recovery | Rosa 162, Roza 7; per90 5.5212981488377375 and 7 | count 169; per90 5.570034362583236 |
| 3054 recovery Interception | Rosa 35, Roza 1; per90 1.1928730568476593 and 1 | count 36; per90 1.1865161955798609 |
| 3054 recovery Tackle | Rosa 72, Roza 3; per90 2.453910288372328 and 3 | count 75; per90 2.471908740791377 |

For these three recovery rows, refresh uses Rosa / DM / 2,730.6833333333334 minutes / 33 matches; reportable, meets_min, full_coverage are true. The original Roza / CM / 90-minute rows had meets_min false and null pctl/pool_n with below-minimum note; the original Rosa rows had meets_min true. Revised/refreshed pctl values (41.86046511627907, 74.4186046511628, 86.04651162790698), pool_n 43, and note `ok` match the original Rosa rows. This documents delivered values only; no statistical policy or percentile computation is endorsed or changed.

All identity/descriptor null counts agree across minutes versions: only `matches` has 22 nulls in each; all other columns have zero nulls. Recovery has zero nulls except `pctl` and `pool_n`: 5,938 each in original versus 5,935 each in October 21/refresh. No missing identity is repaired by guessing.

Recommendation: retain October 21 as the diagnostic version because it already has unique canonical/grain records and is value-equivalent to refresh. Refresh is corroboration, with no demonstrated reason to promote it. Original duplicate-key files remain preserved for provenance. Neither aggregate version supplies trusted original spelling/context evidence or approves minute, role, eligibility, or percentile policy.

## Bounded event identity audit — unchanged D1 population

Reused `validate_match_contexts`, `validate_lineup_evidence`, `build_identity_crosswalk`, and `audit_identity_coverage`, plus the existing M2A resolver/normalizers. Population is exactly all 5,576 October 21 minutes contexts, validated without filtering or substitutions. Input is the first Arrow batch of 4,096 rows from the review events, projecting exactly `id, match_id, player, team, competition_name, season_name, type`. No supplied event player IDs exist. Only eligible verified evidence is permitted, so the trusted lookup remains empty.

| Diagnostic | Prior D1 | D1B | Change |
|---|---:|---:|---:|
| Total / distinct event IDs | 4,096 / 4,096 | 4,096 / 4,096 | 0 |
| Selected | 0 | 0 | 0 |
| Known outside | 0 | 0 | 0 |
| Unresolved | 4,096 | 4,096 | 0 |
| Verified crosswalk matches / crosswalk-only resolved | 0 / 0 | 0 / 0 | 0 |
| Missing actor names | 0 | 0 | 0 |
| Distinct unresolved name/context combinations | 51 | 51 | 0 |

D1B duplicate identity joins: **0**, with event IDs/order preserved. Conflicting event IDs versus trusted evidence: **0 comparisons yielding conflict**; there is no trusted lookup to corroborate actor IDs. Events on eligible conflicting source keys: 0. Missing input match/team/competition/season contexts: 0. Unmatched events: 4,096 across 51 keys. Two observed matches and four match/team pairs lack eligible verified source evidence, although they occur in the delivered context-free lineup. No expected verified fixture manifest is available.

Count conservation: **0 + 0 + 4,096 = 4,096**. Event types remain Ball Recovery 101, Carry 1,714, Dribble 29, Duel 76, Interception 20, Pass 2,156. Team totals remain Bayer Leverkusen 2,314, Union Berlin 787, VfB Stuttgart 995. Matches are 3895292 and 3895320, both event-labeled 1. Bundesliga / 2023/2024. These bounded findings do not establish coverage for all events or the 2015/2016 cohort.

All remaining unresolved keys below have the same reason: no eligible authoritative competition/season association for the source spelling/ID evidence. Each is event-labeled 1. Bundesliga / 2023/2024; none is proven outside the population merely because lookup evidence is unavailable.

| Original event name (M2A-normalized) | Team | Events |
|---|---|---:|
| Adam Hložek | Bayer Leverkusen | 26 |
| Alejandro Grimaldo García | Bayer Leverkusen | 237 |
| Alex Král | Union Berlin | 39 |
| Alexander Nübel | VfB Stuttgart | 100 |
| Amine Adli | Bayer Leverkusen | 112 |
| András Schäfer | Union Berlin | 59 |
| Anthony Rouault | VfB Stuttgart | 4 |
| Atakan Karazor | VfB Stuttgart | 133 |
| Aïssa Bilal Laïdouni | Union Berlin | 40 |
| Benedict Hollerbach | Union Berlin | 22 |
| Borja Iglesias Quintas | Bayer Leverkusen | 32 |
| Brenden Aaronson | Union Berlin | 60 |
| Chris Führich | VfB Stuttgart | 57 |
| Christopher Trimmel | Union Berlin | 40 |
| Danilho Doekhi | Union Berlin | 54 |
| Deniz Undav | VfB Stuttgart | 33 |
| Diogo Filipe Monteiro Pinto Leite | Union Berlin | 87 |
| Edmond Fayçal Tapsoba | Bayer Leverkusen | 91 |
| Enzo Millot | VfB Stuttgart | 130 |
| Exequiel Alejandro Palacios | Bayer Leverkusen | 101 |
| Florian Wirtz | Bayer Leverkusen | 165 |
| Frederik Rønnow | Union Berlin | 86 |
| Granit Xhaka | Bayer Leverkusen | 176 |
| Hiroki Ito | VfB Stuttgart | 125 |
| Jamie Leweling | VfB Stuttgart | 61 |
| Jeremie Frimpong | Bayer Leverkusen | 99 |
| Jonas Hofmann | Bayer Leverkusen | 69 |
| Jonathan Tah | Bayer Leverkusen | 214 |
| Josip Juranović | Union Berlin | 43 |
| Josip Stanišić | Bayer Leverkusen | 9 |
| Kevin Vogt | Union Berlin | 81 |
| Leonidas Stergiou | VfB Stuttgart | 58 |
| Lucas Tousart | Union Berlin | 58 |
| Lukáš Hrádecký | Bayer Leverkusen | 82 |
| Mahmoud Dahoud | VfB Stuttgart | 17 |
| Maximilian Mittelstädt | VfB Stuttgart | 75 |
| Mikkel Kaufmann | Union Berlin | 20 |
| Nathan Tella | Bayer Leverkusen | 89 |
| Odilon Kossonou | Bayer Leverkusen | 245 |
| Pascal Stenzel | VfB Stuttgart | 1 |
| Patrik Schick | Bayer Leverkusen | 22 |
| Piero Martín Hincapié Reyna | Bayer Leverkusen | 237 |
| Rani Khedira | Union Berlin | 32 |
| Robert Andrich | Bayer Leverkusen | 276 |
| Robin Gosens | Union Berlin | 51 |
| Serhou Guirassy | VfB Stuttgart | 65 |
| Silas Katompa Mvumpa | VfB Stuttgart | 9 |
| Victor Okoh Boniface | Bayer Leverkusen | 32 |
| Waldemar Anton | VfB Stuttgart | 108 |
| Woo-Yeong Jeong | VfB Stuttgart | 19 |
| Yorbe Vertessen | Union Berlin | 15 |

## Follow-up: delivered match metadata review

The following read-only investigation supplements the original ten-input review above; historical source-absence statements and bounded audit results describe that earlier review. The local inventory now contains **11 Parquets**.

### Structural validation — VERIFIED FINDINGS

New input: `data/validation/arpit-match-context-review/match_metadata.parquet`.

SHA256: `1b1de360e0f31c49aabd43d065f95fe0762d29a31ea2bcba21b54571b86f3b47`.

| Column | Arrow type | Actual nulls |
|---|---|---:|
| `match_id` | int64 | 0 |
| `competition_name` | large_string | 0 |
| `season_name` | large_string | 0 |

The file contains **1,814 rows and 1,814 unique match IDs**, with zero duplicate match IDs and zero conflicting competition/season associations. `validate_match_contexts` accepts it structurally with `DELIVERED_TABLE_CONSISTENCY_ONLY`; no contradictory association was resolved by selecting its first occurrence.

| Association check | Result |
|---|---:|
| Lineup matches missing metadata | 0 |
| Metadata matches absent from lineups | 0 |
| Lineup rows before / after the many-to-one join | 86,743 / 86,743 |
| Matched lineup rows | 86,743 |
| Lineup match/team pairs covered | 3,628 of 3,628 |
| Conflicting associations against observed event contexts | 0 |

Streaming only match/team/competition/season columns from all 3,626,433 review events confirms exact metadata agreement with the event associations, including the row order of distinct match/competition/season records. All 3,628 event match/team pairs agree with lineups. This establishes observed consistency, not independent fixture or full-season completeness.

Using the new metadata only for a non-authoritative relational comparison gives **6,837 distinct all-lineup spelling/context/ID mappings**: all **5,578 delivered mappings** agree exactly, with **1,259 additional lineup-only mappings**, zero delivered-only mappings, zero different IDs on shared keys and **zero conflicting normalized identity keys**. Restricting the diagnostic comparison to position-present lineup observations matches the delivered crosswalk exactly. No fuzzy matching or guessed IDs were used; these counts do not establish trusted source mappings or event-spelling completeness.

### Source provenance — contributor clarification; independent evidence NOT VERIFIED

**CONTRIBUTOR-REPORTED PROVENANCE:** Arpit explicitly confirmed that the match-context information was extracted from `statsbomb_team_events.parquet`, **not from `sb.matches`**. This resolves the previously open question about the reported derivation; it does not establish independent authoritative match-context evidence. Exact agreement with the event associations, including row order, corroborates that statement. The file is an event-derived association table, not an independent authoritative fixture manifest. Existing ingestion code calling `sb.matches` while collecting events does not change the provenance of this delivered artifact. It remains `DELIVERED_TABLE_CONSISTENCY_ONLY`, not `VERIFIED_SOURCE_EVIDENCE`.

**VERIFIED FINDING — original lineup context:** reinspection of `data/raw/statsbomb_lineups.parquet` confirms that none of `competition_name`, `season_name`, `competition_id` or `season_id` is present. The lineup records therefore do not independently supply the missing competition/season association. Rechecked event-to-lineup associations remain consistent: 1,814 unique matches with no conflicting context associations, all 86,743 lineup rows matched without loss, all 3,628 match/team pairs shared, and no missing matches in either direction. These are structural/relational checks only; agreement with the events cannot independently corroborate context extracted from those same events.

With that actual unverified association, `validate_lineup_evidence` rejects context derivation with `deriving lineup contexts requires a separately verified match association`. **At the metadata-review stage, no trusted crosswalk reconstruction was authorized or performed and no new 4,096-event audit was run.** The earlier 0 selected / 0 known outside / 4,096 unresolved partition is the historical verified-evidence baseline. The subsequently authorized D1B-P diagnostic below supplies a provisional crosswalk directly to the pure resolver; it does not promote any mapping to trusted production use.

**Explicit blocker:** no independently verified match-to-competition/season source is available, and the original lineup records cannot supply that context directly. Obtain a separately justified authoritative match-context source with traceable source records/revision, competition/season IDs, acquisition scope and failure records. The generating script/command, revision and input fingerprints would additionally document the event-derived artifact's lineage, but cannot make it independent evidence. No missing metadata is fabricated and D1's verification requirements are unchanged.

All **11 Parquet SHA256 fingerprints** matched before and after the follow-up investigation. Both this uncommitted report and `docs/m4a-team-approval-checklist.md` were unchanged during that investigation. This subsequent documentation update changes only this report; code, frontend, scoring, the checklist and datasets remain unchanged. Historical regression results below were not rerun for the metadata review.

## Provisional Event Identity Integration

### Scope, inputs and provenance

**CONTRIBUTOR-REPORTED PROVENANCE:** lineups were generated by `fetch_lineups`, followed by `player_minutes`, which produced the delivered crosswalk. Match competition/season context came from `statsbomb_team_events.parquet`, not `sb.matches`.

**NOT YET PRODUCTION-VERIFIED:** this lineage supports the explicitly authorized provisional join audit, not authoritative source verification. Missing independent match-context evidence does not block this diagnostic. The lookup is supplied provisionally by the caller; no `VERIFIED_SOURCE_EVIDENCE` label or D1 evidence object is created. Neither `src/identity.py` nor `src/identity_evidence.py` is changed.

All six requested paths were available and inspected read-only, without substitution:

| Input | Rows | Diagnostic use |
|---|---:|---|
| `data/raw/statsbomb_lineups.parquet` | 86,743 | Existing original spelling/ID observations; no independent competition/season fields |
| `data/processed/player_name_crosswalk.parquet` | 5,578 | Exact provisional lookup source |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | 5,576 | Delivery availability/schema check; not substituted for October 21 |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | 7,680 | Delivery availability/schema check; no metric recomputation |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | 5,576 | Original explicit population; project canonical keys, with no role/minute filtering |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | 3,626,433 | Bounded prefixes only; project `id`, `match_id`, `player`, `team`, `competition_name`, `season_name`, `type`, in that order |

### Safe lookup and diagnostic implementation

**VERIFIED STRUCTURAL FINDING:** the delivered crosswalk has 5,578 source rows, 5,578 normalized spelling/context/ID mappings, 5,578 normalized lookup keys and 5,576 canonical player contexts. Identical duplicate mappings: **0**. Conflicting normalized keys/source rows: **0 / 0**. Usable provisional lookup entries: **5,578**. Original spellings are retained in the diagnostic observation ledger.

`scripts/audit_provisional_identity.py` reuses M2A's exact integer-ID validation, name/team normalization, `prepare_crosswalk`, `validate_population` and `resolve_events(strict=False)`. The key is `player_name_raw + team + competition_name + season_name`. It validates all rows before counting/collapsing identical normalized mappings; every key with competing IDs is quarantined, never assigned an arbitrary winner. Invalid fields fail explicitly. Missing actor names survive as unresolved; missing lookup matches do not become known outsiders. Supplied event IDs in a `player_id` column are rejected so this diagnostic measures lookup assignments only.

Every event survives exactly once, in its original order. Duplicate event IDs fail, including across row groups within the chosen prefix. The script accepts explicit input paths and a positive `--limit` (default 4,096), reads projected Arrow batches, and holds only that bounded prefix plus the small lookup/population tables. It prints summaries, conflicting source observations and unmatched normalized names/contexts. It performs no ingestion, network requests, dataset writes, production JSON export or metric/scoring calculations.

```sh
python -B -W error -m scripts.audit_provisional_identity --events data/validation/drive-raw-review/statsbomb_team_events.parquet --crosswalk data/processed/player_name_crosswalk.parquet --population data/validation/arpit-2026-10-21/player_minutes.parquet
```

### Identical 4,096-event comparison

**PROVISIONAL MATCHING RESULT:** the exact original prefix, projection, ordering and all 5,576 October 21 population contexts now produce:

| Diagnostic | Prior D1/D1B empty eligible lookup | D1B-P provisional delivered lookup |
|---|---:|---:|
| Event rows / unique event IDs | 4,096 / 4,096 | 4,096 / 4,096 |
| Events matched to player IDs | 0 | 4,096 |
| Selected player-context events | 0 | 4,096 |
| Known outside-population events | 0 | 0 |
| Unresolved events | 4,096 | 0 |
| Matched percentage | 0% | 100% |

The sample covers 2 matches and 51 matched player contexts, all event-labeled 1. Bundesliga / 2023/2024. Conflicting source keys: **0**; affected events: **0**. Missing actor names, invalid identity fields, duplicate joins and unmatched name/context keys: **0 each**. There are no remaining unmatched names or unresolved causes in this prefix. Count conservation is **4,096 + 0 + 0 = 4,096**; event IDs and ordering are preserved. These assignments are provisional, not authoritatively source-verified identities.

### Larger bounded diagnostic

After the successful original sample, the same diagnostic was run with `--limit 65536` to test additional match/player contexts. It processed **65,536 rows and 65,536 unique event IDs**, covering **29 matches and 346 matched player contexts**, still entirely 1. Bundesliga / 2023/2024. Results: **65,536 matched/selected (100%), 0 known outside, 0 unresolved**. Missing actor names, invalid identity fields, affected conflicting events, unmatched keys and duplicate joins remain zero; all rows and order are conserved. Uniqueness was checked over the entire prefix, not separately per batch.

No full event scan was performed for D1B-P. This prefix does not test all leagues/seasons, all 5,578 lookup keys or full source/spelling completeness. A larger scan is deferred until a specific metric/coverage question justifies its cost.

### D1B-P regression and integrity

**VERIFIED STRUCTURAL FINDING:** `python -B -W error -m unittest discover -s tests -q` passed **366 tests** (340 existing + 26 focused provisional tests). The complete recursive frontend JavaScript suite passed **67 tests, 0 failures** across both discovered test files. Process-local temporary directories for synthetic test files were directed to an allowed artifact workspace; no existing dataset was used as a test output. `git diff --check` passed. No metric/scoring/frontend implementation or M2A/D1 contract changed.

`tests/test_provisional_identity.py` covers duplicate accounting, normalized aliases and original spellings, conflict quarantine/order independence, exact large IDs and invalid IDs, context separation, missing names, no fuzzy/display-name fallback, selected/outside/unresolved separation, 4,096-row conservation, input immutability and original ordering, supplied-ID rejection, empty inputs, duplicate event IDs across row groups, explicit missing paths, bounded projection and CLI behavior. It also checks that D1 still rejects an unverified match association.

All 11 SHA256 values match both the pre-work inventory and the recorded D1/D1B fingerprints:

| Preserved input | SHA256 check |
|---|---|
| `data/processed/player_minutes.parquet` | PASS — unchanged |
| `data/processed/player_name_crosswalk.parquet` | PASS — unchanged |
| `data/processed/recovery_per90.parquet` | PASS — unchanged |
| `data/raw/statsbomb_lineups.parquet` | PASS — unchanged |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | PASS — unchanged |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | PASS — unchanged |
| `data/validation/arpit-match-context-review/match_metadata.parquet` | PASS — unchanged |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | PASS — unchanged |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | PASS — unchanged |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | PASS — unchanged |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | PASS — unchanged |

Only the existing untracked `docs/d1b-identity-source-validation.md` was edited; `scripts/audit_provisional_identity.py` and `tests/test_provisional_identity.py` are new untracked files. The M4A checklist and every other pre-existing fingerprinted file remain unchanged. No tracked or staged changes exist. The pre-existing untracked dataset entries and checklist remain as found; the raw lineup remains ignored by existing Git rules. Branch is still `integration-foundation`, HEAD is `8314439d6cbf549794555aa6e732482482ede0f0`, and `main` remains `179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. No branch/worktree, ingestion, download, commit, push, deployment, production scorecard or rating was created.

### Production boundary and next metric step

**NOT YET PRODUCTION-VERIFIED:** independent match-context provenance, source/acquisition completeness, expected fixtures/teams/participants, full actor spelling coverage, exposure alignment and scoring approvals remain separate requirements. D1's verified-only evidence builder is unchanged and still rejects unverified context association. Provisional matching success does not authorize production scorecards or ratings.

The next real-metrics step is an explicitly provisional, in-memory bounded recovery/press audit using these same resolved events, preserving selected/outside/unresolved accounting and raw component definitions. Start with observed counts and pressured completion percentages; do not divide prefix event counts by full-season minutes or promote these mappings into production integration. Establish matching event-window exposure before any per90 interpretation, and verified evidence before production promotion.

## Integration decision and remaining confirmation

**NOT VERIFIED:** authoritative match association, acquisition coverage/failures, expected fixtures/teams/participants, full actor spelling coverage, and complete season coverage. Source observations are now available; the prior file-absence blocker has narrowed to trusted context/provenance and completeness. A successful relational lookup cannot close those gaps.

For production promotion, obtain a separately justified authoritative match-to-competition/season source; the confirmed event-derived delivery cannot close that independent-context requirement. Also obtain expected fixture scope, acquisition/failure records and expected team/participation coverage. Only after provenance passes, use the existing `validate_match_contexts`, `validate_lineup_evidence` and `build_identity_crosswalk` contracts to reconstruct an in-memory verified candidate including bench observations and review spelling/collision discrepancies. Compare that verified candidate against the D1B-P diagnostic using the same event prefix and population. These production requirements do not prevent the isolated provisional testing above. Team approval of metric/exposure rules remains separate. No source version was promoted.

## Regression and repository integrity

**VERIFIED FINDING:** required Python command `python -B -W error -m unittest discover -s tests -q` passed **340 tests** (156.684 seconds) after directing process-local TEMP/TMP to the permitted artifact workspace. The first run executed 340 tests with one environment PermissionError creating/cleaning a synthetic temporary Parquet; the corrected rerun passed without code changes. Synthetic test files are separate from the ten preserved inputs.

The complete recursive frontend test suite was invoked by enumerating all `frontend/tests/**/*.test.js` paths and passing them to `node --test`: **67 passed, 0 failed**. `git diff --check` passed. No implementation change was required, so no new regression tests were added.

All ten files were rehashed after analysis and after regression testing. The post-test values below equal the pre-analysis fingerprints in the inventory. All six originals also match the full expected values preserved in D1.

| Input | Final SHA256 | Comparison |
|---|---|---|
| `data/raw/statsbomb_lineups.parquet` | `dfb6e2f0adfb1ec25c879b26feb3616b8683c64e152657f098edc20aa1635be2` | PASS: new delivery unchanged |
| `data/processed/player_name_crosswalk.parquet` | `a250ac8074967aad3b1fdcd35a849584658ac333a4049d1de3845f443d2397e7` | PASS: new delivery unchanged |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | `5600f1250a3bd7fcf9d12a9d11ecac4ae9d39cd58898d6e6df1e5d4d1aa1830e` | PASS: new delivery unchanged |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | `5b53d544662826206511e2d2c532297160b781f84958b2acf615195590f82012` | PASS: new delivery unchanged |
| `data/processed/player_minutes.parquet` | `9701ec4a74b1a75ee6094f08619c40b26f6d6f103d64a23ca2802448351e931b` | PASS: unchanged and matches D1 |
| `data/processed/recovery_per90.parquet` | `056f94b0bd49bc707e5d00181d0b85654cd076e5dc3bc09e1a6c121cd530ee4d` | PASS: unchanged and matches D1 |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | `01f1bb2650df4f793971465eefad49eefcd41a302789b5c5009cf7355a4b1694` | PASS: unchanged and matches D1 |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | `7a546348b2c391d32221456fab259d639910d13c8e672ba030e6d30b38cab61f` | PASS: unchanged and matches D1 |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | `ec12fdd2340fb125671f4996abdac510c3dc6d81555848792520ce5df2519eb8` | PASS: unchanged and matches D1 |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | `497fa459e1ee99f758ed37d405d69285af5e6759306851456d03fde8c4025625` | PASS: unchanged and matches D1 |

Branch remains `integration-foundation`. HEAD remains `8314439d6cbf549794555aa6e732482482ede0f0`; `main` remains `179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. Index and worktree inventory match their initial state. No tracked file has changed; the sole new intended repository file is the unstaged, untracked `docs/d1b-identity-source-validation.md`. No backend formula, scoring, identity contract, frontend, baseline report, or Parquet was modified. Nothing was staged, committed, pushed, deployed, or switched.

Final `git status --short`:

```text
?? data/processed/player_minutes.parquet
?? data/processed/player_name_crosswalk.parquet
?? data/processed/recovery_per90.parquet
?? data/validation/
?? docs/d1b-identity-source-validation.md
```

The raw lineup is ignored by the existing Git rules; its omission from short status does not imply it was absent from the fingerprint checks. The four pre-existing untracked dataset entries remain as found.


## Reviewed implementation fingerprints

These SHA256 values fingerprint the local contract/evidence code, baseline report, and relevant regression files read during review. Contributor blobs are fingerprinted from the existing Git revision, without checking them out.

| Reviewed source | SHA256 |
|---|---|
| `docs/d1-identity-evidence.md` | `805e54574c610c80cf1a1f890c4321fa5b5ab43088fc4cd8fd47d0b80daf27ad` |
| `src/identity.py` | `e0600ba49c77c1551679b2bc6a727cba791a4d2adf998c0106184582b9f64976` |
| `src/identity_evidence.py` | `bde82ce97561b92a0c6572796d1e12ff6ace40cec60936d71dff18c5249cae0c` |
| `tests/test_identity.py` | `faaba7d43b9cc6897a6ca6dcdbe790c571f7f31c911d1c476fceee0096a5b687` |
| `tests/test_identity_evidence.py` | `130e40affb2d852fabcc42d5c9963d3f999fb57d0432cf46f015a661146f6acd` |
| `0445f18:src/ingestion/fetch_lineups.py` | `8421f44a070e2e5fc8af5f289fd25fef63f5a6954382f74e02edc7ff76a43777` |
| `0445f18:src/metrics/player_minutes.py` | `92064b46b7559e2077adef4fa51776ad2ae0415f76bdf067c7e5f39f5a837086` |

## Reproduction outline

Read Parquet schemas/counts with `pyarrow.parquet.ParquetFile`; hash file bytes in blocks with SHA256. Sum null counts from Arrow batches for each new delivery. For metric comparison, normalize teams using M2A, retain exact IDs, compare set membership on canonical contexts, and compare values at unique canonical grain (plus event_type for recovery). Exclude every member of duplicate baseline groups from one-to-one comparisons and review those groups explicitly. For fixture consistency, stream only event match/team/competition/season columns, deduplicate observations, then call `validate_match_contexts` with `DELIVERED_TABLE_CONSISTENCY_ONLY`. The resulting association is diagnostic only.

```python
import pyarrow.parquet as pq
from src.identity import PLAYER_KEYS
from src.identity_evidence import (DELIVERED, validate_lineup_evidence,
    build_identity_crosswalk, audit_identity_coverage)

population = pq.read_table(
    "data/validation/arpit-2026-10-21/player_minutes.parquet",
    columns=PLAYER_KEYS,
).to_pandas()
events = next(pq.ParquetFile(
    "data/validation/drive-raw-review/statsbomb_team_events.parquet"
).iter_batches(batch_size=4096, columns=[
    "id", "match_id", "player", "team", "competition_name", "season_name", "type"
])).to_pandas()
# Actual context-free lineup validation fails without an independently verified
# match association. Do not replace that association with event-only metadata.
candidate = build_identity_crosswalk([])
audit = audit_identity_coverage(
    events, candidate, population,
    population_scope="all 5576 revised October 21 delivered minutes contexts, no filtering",
)
assert audit.summary["unresolved"] == 4096
```
