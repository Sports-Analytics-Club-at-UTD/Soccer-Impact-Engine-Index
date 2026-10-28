# Metric Documentation: Defensive Recovery Coverage and Observed Spatial Dominance

Owner: Person 4 (Spatial + Defensive Recovery)
Version: V1, updated 27 October 2026
Scope: midfielders, center-backs, goalkeepers (no attackers/wingers). Team V1 scope: 2015/16 only.

## 0. How to read this document

Every statement is labelled by what kind of thing it is:

- **RAW**: a field or value that comes directly from StatsBomb Open Data.
- **DERIVED**: something we calculate from raw fields.
- **ASSUMPTION**: a choice we made that the data does not prove.
- **N/A rule**: when the data does not support a result, we output N/A. We never infer or substitute another metric.
- **Person 4 decision (not yet agreed with the team)**: a rule chosen by Person 4 in this document's version. It has not been discussed with the rest of the team.

---

## 1. Data used

### 1.1 Files

| File | Source script | Contents | Stored in |
|---|---|---|---|
| `statsbomb_team_events.parquet` | `src/ingestion/fetch_normal.py` | 3,626,433 event rows, 1,814 matches, six event types: Pass, Carry, Ball Recovery, Dribble, Duel, Interception. No `player_id` column. | Shared Drive (not git) |
| `statsbomb_360_frames.parquet` | `src/ingestion/fetch_360.py` (confirmed: the script writes this file) | 7,562,022 rows, 445,569 frame ids, 127 matches | Shared Drive (not git) |
| `statsbomb_360_event_meta.parquet` | `src/ingestion/fetch_360_event_meta.py` | `id`, `match_id`, `team`, `possession_team` | Shared Drive (not git) |
| `statsbomb_lineups.parquet` | `src/ingestion/fetch_lineups.py` | 86,743 rows, all 1,814 matches fetched. One row per player per position stint (a player with no stint has one row with empty position fields). | Shared Drive (not git) |
| `statsbomb_fixtures_2015_16.parquet` | `src/ingestion/fetch_fixtures.py` | StatsBomb's match list (`sb.matches`) for the four full 2015/16 leagues: 1,517 matches (La Liga 380, Ligue 1 377, Premier League 380, Serie A 380), with a `fetched_on` date column. Fresh fetch on 27 Oct 2026. Some manager columns held two IDs in one cell and are saved as text. | Shared Drive (not git) |

Derived tables (in `data/processed/`, not in git): `recovery_coverage_totals`, `recovery_coverage_by_zone`, `spatial_dominance_team_zone`, `spatial_coverage`, `player_minutes`, `player_name_crosswalk`, `recovery_per90`, `recovery_scores`, `match_metadata`.

`match_metadata.parquet`: one row per match (1,814 rows) with `match_id`, `competition_name` and `season_name`, taken from the events file with `drop_duplicates`. Each match has exactly one competition and season. It was extracted from `statsbomb_team_events.parquet`, not from `sb.matches`, so it is derived, not original StatsBomb match data. It has no teams, dates, scores or StatsBomb competition/season IDs. It was created with a one-line pandas command that is not in git yet. It does not include match 3879594, because that match is not in the events file.

Name-cleaning helpers (in git): `src/metrics/team_names.py` (clubs listed under two names, see limitation 17) and `src/metrics/player_names.py` (players listed under two spellings, see limitations 20 and 23).

The fetch scripts are in git so the data can be rebuilt. The parquet files are too large for git.

### 1.2 Fields used (all RAW)

- Events: `match_id`, `type`, `minute`, `second`, `period`, `team`, `player`, `position`, `location`, `duel_type`, `duel_outcome`, `interception_outcome`, `ball_recovery_recovery_failure`, `competition_name`, `season_name`.
- 360 frames: `id`, `visible_area`, `teammate`, `actor`, `keeper`, `location`.
- Event-meta lookup: `id`, `match_id`, `team`, `possession_team`.
- Lineups: `match_id`, `team`, `player_id`, `player_name`, `player_nickname`, `position`, `from_time`, `to_time`, `from_period`, `to_period`, `start_reason`, `end_reason`.
- Fixtures: `match_id`, `competition_name`, `season_name` (used for the coverage comparison).

### 1.3 Coverage

**Events (Recovery Coverage).** Verified match counts per league-season in the events file:

| Coverage | League-seasons (matches) |
|---|---|
| **Full league season** | La Liga 2015/16 (380), Ligue 1 2015/16 (377), Premier League 2015/16 (380), Serie A 2015/16 (379) |
| **Partial (one club's season)** | Bundesliga 2015/16 (34), Bundesliga 2023/24 (34), La Liga 2016/17 (34), 2017/18 (36), 2018/19 (34), 2019/20 (33), 2020/21 (35), Ligue 1 2021/22 (26), Ligue 1 2022/23 (32) |

Nothing falls between 36 and 377 matches. Each partial season was checked from the per-90 match counts (the team whose players appear in the most matches): Bayer Leverkusen for Bundesliga 2015/16 and 2023/24 (33 matches each), Barcelona for La Liga 2016/17 to 2020/21 (32, 35, 33, 31 and 35 matches) and Paris Saint-Germain for Ligue 1 2021/22 and 2022/23 (24 and 32 matches). These counts are the highest per-player match count for the club, so they can sit slightly below the season's match total. For Bundesliga 2015/16, players of every other team appear in at most 2 matches (they are opponents). In the full league-seasons the top team has 38 matches, as expected. The four full league-seasons are all 2015/2016. The partial seasons were not checked against StatsBomb's match list (only the four 2015/16 leagues were fetched).

**Full seasons checked against StatsBomb's match list.** First checked on 26 Oct 2026 (in memory, nothing saved), then re-checked on 27 Oct 2026 against a fresh fetch saved as `statsbomb_fixtures_2015_16.parquet` (competition_id / season_id: La Liga 11/27, Ligue 1 7/27, Premier League 2/27, Serie A 12/27).

| League 2015/16 | Listed by StatsBomb | In events file | Listed but not in events file | In events file but not listed | Listed but not in lineups |
|---|---|---|---|---|---|
| La Liga | 380 | 380 | none | none | none |
| Ligue 1 | 377 | 377 | none | none | none |
| Premier League | 380 | 380 | none | none | none |
| Serie A | 380 | 379 | 3879594 | none | 3879594 |

- Serie A 2015/16 has 379 of 380 matches. The one gap is 3879594, the match the events fetch skipped (connection reset). It is also absent from the lineups.
- Ligue 1 2015/16 has 377 matches because StatsBomb lists 377. It is complete, not a fetch failure.
- The 27 Oct list is a fresh fetch, not the list used on 26 Oct. Both checks gave the same result.

**360 frames (Spatial Dominance):** free only for four league-seasons, each covering one club.

| League-season | Matches with 360 | Matches in season slot | Club covered |
|---|---|---|---|
| Bundesliga 2023/24 | 34 | 34 | Bayer Leverkusen |
| La Liga 2020/21 | 35 | 35 | Barcelona |
| Ligue 1 2021/22 | 26 | 26 | Paris Saint-Germain |
| Ligue 1 2022/23 | 32 | 32 | Paris Saint-Germain |
| **Total** | **127** | **127** | |

Premier League and Serie A: zero free 360 data in any season. **N/A rule applies.**

Within these four league-seasons every match has 360 data. The sample is small because only four league-seasons are free, not because matches are missing.

---

## 2. Metric 1: Defensive Recovery Coverage

This is the individual-player metric. It is built in four steps: counts (2.2), minutes and position groups (2.3), per-90 rates and a provisional within-league percentile (2.4), and pooled scores per event type (2.6).

### 2.1 In plain words

How many times did a player win the ball back, and where on the pitch? Tackles, interceptions and ball recoveries are counted separately and never added together inside the metric.

### 2.2 Counts

**Input (RAW):** event rows of type Interception, Ball Recovery, and Duel with `duel_type == "Tackle"`, with their outcome fields, `location`, `position`, `player`, `team`, competition, season.

**Calculation (DERIVED):**

1. Keep three event types, each kept distinct:
   - **Tackle**: Duel events where `duel_type == "Tackle"`. Tackles are not their own top-level event type in the data.
   - **Interception**: Interception events.
   - **Ball Recovery**: Ball Recovery events.
2. Keep only successful events (the filter runs before anything is counted, confirmed against `src/metrics/recovery_coverage.py`):
   - Tackle and Interception: outcome in `SUCCESS_OUTCOMES` = {Won, Success In Play, Success Out}. Lost In Play and Lost Out are excluded.
   - Ball Recovery: kept unless `ball_recovery_recovery_failure` is True.
3. Assign each event to a pitch zone from its `location` using `src/metrics/zones.py` (currently a 3x3 placeholder grid).
4. Count events per player name, team, competition, season, event type, and (separately) per zone. These counts are name-based because the events file has no `player_id`; `player_id` is attached later in `recovery_per90` (see limitation 23).

**Result:**

- `recovery_coverage_totals.parquet`: one row per player-season-event type (columns: player, team, competition_name, season_name, event_type, count). Name-based.
- `recovery_coverage_by_zone.parquet`: one row per player-season-event type-zone. Name-based.
- Per-player and per-team zone heatmaps (`src/viz/zone_heatmap.py`, `--player` option). Name-based.
- Counted events (after the success filter): Tackle 43,290; Interception 27,449; Ball Recovery 175,654 (total 246,393). Of these, 132,036 come from in-scope players (GK, CB, DM, CM) and 114,357 from out-of-scope players, which are dropped when per-90 is built.

### 2.3 Minutes and position groups

Script: `src/metrics/player_minutes.py`. Output: `player_minutes.parquet`, one row per player_id + team + competition + season (5,576 rows). The script also writes `player_name_crosswalk.parquet` (see limitation 23).

**Input (RAW):** lineups (position stints with start and end times). Competition and season for each match come from the events file.

**Calculation (DERIVED), all Person 4 decisions, not yet agreed with the team:**

1. Drop lineup rows with no position stint (players who never played): 18,350 of 86,743 rows.
2. Stint minutes = end time minus start time on the match clock. A stint with no end time runs to 90:00. Start and end are capped at 90:00, so every match counts as at most 90 minutes and extra time is ignored. A player who plays 60 minutes gets 60.
3. Map each position label to a group:
   - **GK**: Goalkeeper
   - **CB**: Center Back, Left Center Back, Right Center Back
   - **DM**: Center, Left and Right Defensive Midfield
   - **CM**: Center, Left Center and Right Center Midfield
   - **Out of scope**: fullbacks and wing backs (FB), Left/Right Midfield (WM), attacking midfielders (AM), wingers and forwards (ATT)
4. A player's position group for a season = the group where they played the most minutes. Ties (71 rows) are broken by the fixed order GK, CB, DM, CM, then the others.
5. A player's minutes are **all** their minutes in that season, in any position. Their events are likewise counted from any position, so numerator and denominator match.
6. Club names are cleaned before grouping (`clean_team`). Players are grouped by `player_id` + team + competition + season, not by name. The display name (`player_name`) is the most frequent spelling of that `player_id` in the lineups (after `clean_player`); it is a label only.

**Result (verified):** player-seasons per group: GK 422, CB 957, DM 704, CM 499 in scope; FB 958, WM 376, AM 238, ATT 1,422 out of scope (5,576 total). Maximum player-match minutes 90.00. 0 duplicate player_id + team + competition + season keys.

**Join check:** all 304,876 recovery-type events (Ball Recovery, Interception, Tackle, before the success filter) found their player in the lineups on match + team + player name (100.00%).

**Minutes per player-season, in-scope groups:**

| Group | Player-seasons | Median | 75th percentile | 90th percentile |
|---|---|---|---|---|
| CB | 957 | 180 | 1,260 | 2,462 |
| DM | 704 | 177 | 1,196 | 2,345 |
| CM | 499 | 113 | 865 | 2,245 |
| GK | 422 | 180 | 902 | 2,970 |

### 2.4 Per-90 rates and provisional within-league percentile

Script: `src/metrics/recovery_per90.py`. Output: `recovery_per90.parquet`, one row per in-scope player-season x event type (7,680 rows).

**Calculation (DERIVED):**

1. Attach `player_id` to the recovery totals through the crosswalk (player name + team + competition + season), add up counts per `player_id`, then match to the minutes table on player_id + team + competition + season. All 246,393 events received a player_id and matched (0 lost).
2. Keep players in scope with minutes above 0. A player with no totals row for an event type gets a count of 0 (1,869 rows). This is an ASSUMPTION: the player was on the pitch and the events data records none.
3. Per-90 = count / minutes x 90.
4. **Goalkeepers:** only Ball Recovery is reportable. Goalkeeper Tackle and Interception rows stay in the table with `reportable = False`. Person 4 decision, not yet agreed with the team. Reason: goalkeepers are 99.9% Ball Recovery (17,260 of 17,271 counted events; 5 Interception, 6 Tackle).
5. **Minimum minutes:** `meets_min` flags players at or above a threshold, **provisionally 900 minutes** (about ten full matches). The final rule is not decided.
6. **Full-coverage rule:** a league-season counts as full coverage if the events file has at least 300 matches for it (default). The events file shows 377 to 380 or 36 or fewer, so any cutoff in between gives the same result.
7. **Within-league percentile (`pctl`, a provisional helper, not used by the team's pipeline):** the percentile of per-90 within league-season x position group x event type (rank as a share of the pool, ties get the average rank, top player = 100). The lowest-ranked player in a pool gets 100/N, not 0. Computed only for rows that are reportable, meet the minimum minutes, and are in a full-coverage season. Every other row gets N/A, with the reason in `pctl_note`:
   - "N/A: goalkeeper, Ball Recovery only"
   - "N/A: single-club season, no comparison group"
   - "N/A: below minimum minutes"
8. The three event types are never blended. Each has its own per-90 and its own percentile.

**Player-seasons meeting each minimum-minutes threshold (all seasons):**

| Group | >= 450 | >= 900 | >= 1,350 |
|---|---|---|---|
| GK | 134 | 108 | 93 |
| CB | 335 | 285 | 229 |
| DM | 247 | 203 | 165 |
| CM | 156 | 124 | 94 |

**Within-league `pctl` pool sizes at 900 minutes (full-coverage seasons only):**

| League (2015/16) | CB | DM | CM | GK |
|---|---|---|---|---|
| La Liga | 62 | 54 | 13 | 23 |
| Ligue 1 | 67 | 49 | 25 | 26 |
| Premier League | 59 | 43 | 26 | 27 |
| Serie A | 67 | 42 | 42 | 22 |

16 pools, smallest 13, median 42. 73 players meet the minimum minutes but have no `pctl` because their season is single-club. They keep their per-90 rates.

### 2.5 Raw vs derived vs assumption

| Item | Type |
|---|---|
| Event type, outcome fields, location, position, player, team | RAW |
| Lineup positions, start and end times, player_id | RAW |
| StatsBomb match list (fixtures file) | RAW |
| Counts, per-zone counts, minutes, per-90 rates, percentiles | DERIVED |
| `match_metadata` (match_id -> competition, season, from the events file) | DERIVED |
| Tackles identified through `duel_type == "Tackle"` | RAW field, our selection rule |
| SUCCESS_OUTCOMES set | ASSUMPTION, checked against real label counts |
| Empty recovery-failure flag means a successful recovery | ASSUMPTION (the flag is only ever True or empty) |
| 3x3 zone grid | ASSUMPTION (placeholder, team decision pending) |
| Event counts are attached to a player_id through the lineups crosswalk (name + team + competition + season) | DERIVED, supported by the 100% join check and 0 crosswalk clashes |
| Display name = most frequent spelling per player_id | DERIVED (label only, not used in any key) |
| Player names cleaned with `clean_player` (`''` to `'`, strip whitespace) | DERIVED, applied to lineups and recovery totals only |
| 90-minute cap, no extra time | Person 4 decision, not yet agreed with the team |
| Position group = most minutes; all minutes and events count | Person 4 decision, not yet agreed with the team |
| Wide midfielders and fullbacks out of scope | Person 4 decision; the press resistance owner agreed to align V1 with DM and CM only |
| Goalkeepers: Ball Recovery only | Person 4 decision, not yet agreed with the team |
| Missing totals row = 0 events | ASSUMPTION |
| 900-minute threshold | PROVISIONAL, not decided |
| Full-coverage cutoff of 300 matches | DERIVED from the match-count gap |
| Marseille / Olympique de Marseille and Caen / Stade Malherbe Caen are the same clubs | ASSUMPTION (see limitation 17) |
| Percentile in `recovery_scores` (rank / pool size x 100) | DERIVED |
| Rating in `recovery_scores` (65 + 10z, clipped to 1-99) | DERIVED; the constants 65 and 10 and the clip are ASSUMPTIONS (display layer only) |
| Gold at percentile 90 or higher, Silver 75 up to 90 | PROVISIONAL, not final until the team agrees |
| DM and CM ranked together as one Midfielders group | Team working decision (V1) |
| A recovery rate means the same thing across the four leagues | ASSUMPTION, not testable with this data |
| mu and sigma are computed from the eligible pool | ASSUMPTION about the team's formula document (see section 7) |

### 2.6 Recovery scores (percentile, rating, tier per event type)

Script: `src/metrics/recovery_scores.py`. Output: `recovery_scores.parquet`, one row per player-season x event type (7,680 rows, same rows as `recovery_per90`). It reads `recovery_per90.parquet` and changes nothing in it.

**In plain words:** for each player and each event type, how does his per-90 rate compare with other eligible players of the same kind across the four full leagues? Tackles, interceptions and ball recoveries each get their own percentile, rating and tier. They are never blended.

**Input (DERIVED):** `per90`, `reportable`, `meets_min`, `full_coverage` and `position_group` from `recovery_per90.parquet`.

**Calculation (DERIVED), provisional until the team agrees:**

1. **Position group for scoring:** DM and CM are combined into one Midfielders group (`MID`). CB and GK keep their own groups.
2. **Eligible rows:** `reportable` and `meets_min` (900 minutes, provisional) and `full_coverage`. Every other row gets no percentile, rating or tier, with the reason in `score_note`:
   - "N/A: goalkeeper, Ball Recovery only"
   - "N/A: single-club season, not in reference pool"
   - "N/A: below minimum minutes"
3. **Pool:** eligible players in the same season, scoring group and event type, with all four full leagues together (no per-league ranking). Single-club seasons (Bundesliga 2015/16, which covers only Leverkusen, and the other partial seasons) are not in the pool.
4. **Percentile** = rank of the player's per-90 in the pool / pool size x 100. Ties share the average rank. The best player in a pool gets 100; the lowest gets 100/N.
5. **Rating** = 65 + 10 x z, where z = (per-90 - pool mean) / pool standard deviation, clipped to 1-99. The mean and standard deviation are calculated per pool. Display layer only; tiers do not use it.
6. **Tier** (on the percentile, not the rating): Gold = 90 or higher, Silver = 75 up to (not including) 90, otherwise none. N/A rows get tier N/A.

**Result (verified from the run on 23 Oct 2026, re-run on 26 Oct 2026 with the same pool sizes and tier counts):**

- `recovery_scores.parquet` columns: player_id, player, team, competition_name, season_name, position_group, score_group, minutes, event_type, count, per90, percentile, rating, pool_n, tier, score_note.
- Pool sizes (all 2015/16, four leagues together): MID 294 for each event type, CB 255 for each event type, GK 98 (Ball Recovery only). 1,745 scored rows in total (sum of the printed pool sizes).
- Tier counts: Ball Recovery 66 Gold, 97 Silver, 484 none; Interception and Tackle 56 Gold, 82 Silver, 411 none each. Gold is about 10% and Silver about 15% of each pool.
- Rating distribution: mean 65.0 and standard deviation about 10 in every pool. Highest ratings reach 99.0 (the cap) in the CB Interception, GK Ball Recovery and MID Ball Recovery pools. 28 of the 1,745 scored rows are 90 or higher. The lowest rating is 38.5, so the floor of 1 did not apply.
- Goalkeepers appear only under Ball Recovery.

`pool_n` is the number of players the row was ranked against.

### 2.7 Raw vs derived vs assumption for scores

See the last rows of the table in 2.5.

---

## 3. Metric 2: Observed Spatial Dominance

This is a **team-level** metric. It cannot rank individual players.

### 3.1 In plain words

When the opposition has the ball, how much of each pitch zone is physically closer to the defending team's visible players than to the attackers? It is called *Observed* Spatial Dominance because it is not true pitch control.

### 3.2 Why team-level, not player-level

The free 360 table has no identity for off-ball players. Its columns are `id`, `visible_area`, `match_id`, `teammate`, `actor`, `keeper`, `location`. Only the actor (the player performing the ball event) can be identified, by joining `id` back to the events table. A per-player control rate would require inventing identities, which the project rules forbid. This is a locked data limitation.

### 3.3 Input -> calculation -> result

**Input (RAW):** 360 frames (player positions per event-triggered frame) and the event-meta lookup (`team`, `possession_team`).

**Calculation (DERIVED):**

1. Join each frame to its event on `id`. Frames with no matching event are excluded and counted (`skipped_no_event_match`).
2. Keep frames where the defending team is not the possession team.
3. Normalise orientation so the defending team's goal is at x = 0. Coordinates are from the actor's perspective, confirmed by a goalkeeper check (mean x of actor-side goalkeeper 10.1, opposing goalkeeper 112.6).
4. Skip frames that show players from only one side (counted separately).
5. Divide the pitch into 2x2-yard cells. Assign each cell to the nearest visible player. Cells outside `visible_area` are not counted (N/A). Both goalkeepers are included as players. Exact distance ties go to the first point in the array (`argmin`).
6. Per zone, defending-team control rate = share of observed cells in that zone assigned to a defending-team player. The attacking side's share is the complement.
7. Aggregate across frames and matches per defending team and zone. This is pooled (cell-weighted): observed and defender cell counts are summed and then divided, not averaged as per-frame ratios.
8. N/A rules: a zone with no observed frames is N/A; a team with fewer than `MIN_MATCHES` (10) matches is N/A; a league with no 360 data is N/A.

**Result:**

- `spatial_dominance_team_zone.parquet`: defending team x zone control rate.
- `spatial_coverage.parquet`: how many frames and matches each result is based on.
- Spatial heatmaps for reportable teams only.

**Frame accounting (verified):** 445,569 frame ids = 431,769 used + 13,761 unmatched to an event (3.1%, all in matches 3895266, 3837706, 3895158, 3895309) + 39 skipped for one side only.

**Reportable teams** (matches as defending team in the spatial run): PSG 57, Barcelona 35, Bayer Leverkusen 31. Every other team has 4 or fewer matches (as opponents) and is N/A.

The reportable counts are below the matches in the free 360 set (Leverkusen 31 of 34, PSG 57 of 58, Barcelona 35 of 35). The four matches with unmatched frames are 3895158 (Dortmund vs Leverkusen), 3895266 (Leverkusen vs Wolfsburg), 3895309 (Dortmund vs Leverkusen) and 3837706 (PSG vs Brest): three Leverkusen matches and one PSG match, which matches the gaps exactly. This is explained by the numbers lining up; it was not checked that those matches contribute no used frames.

### 3.4 Raw vs derived vs assumption

| Item | Type |
|---|---|
| Frame player locations, teammate/actor/keeper flags, visible_area | RAW |
| possession_team, team (event-meta) | RAW |
| Cell assignments, zone control rates, coverage counts | DERIVED |
| Nearest-player = control | ASSUMPTION (simplification) |
| 2x2-yard cell size | ASSUMPTION |
| Actor's-perspective orientation | ASSUMPTION, supported by the goalkeeper check |
| MIN_MATCHES = 10 | ASSUMPTION |
| 3x3 zone grid | ASSUMPTION (placeholder) |

---

## 4. Limitations

### Spatial Dominance

1. Only four league-seasons have free 360 data, one club each. Teams below `MIN_MATCHES` (10) are N/A. Premier League and Serie A are N/A (zero free 360 data). They are never filled with other event types.
2. 13,761 frames (3.1%) in four matches could not be matched to an event and were excluded.
3. Not true pitch control. It ignores the ball, player speed, player direction, and anyone outside the camera view. Frames are event-triggered, so they are not evenly spaced in time. Team-level only. Control rate is pooled (cell-weighted) across frames and matches, not an average of per-frame ratios.
4. Orientation relies on the actor's-perspective assumption, confirmed by the goalkeeper check.

### Recovery Coverage

5. Failed recoveries are flagged only as True. An empty flag is counted as a successful recovery.
6. SUCCESS_OUTCOMES = Won, Success In Play, Success Out (checked against real label counts). Interception outcome counts in the events file: Won 17,673; Success In Play 9,508; Success Out 268 (total 27,449, the counted interceptions); Lost In Play 10,456 and Lost Out 6,675 are excluded. No interception has an empty outcome. Success Out is about 1% of counted interceptions, so including or excluding it barely moves any rate.
7. The events file has no `player_id`. Players are matched to the lineups on match + team + player name. In `recovery_per90`, `recovery_scores` and `player_minutes`, records are keyed on `player_id` (see limitation 23). In the events file, `recovery_coverage_totals`, `recovery_coverage_by_zone` and the heatmaps, players are still identified by name + team + competition + season (events file and by-zone table only; see 23). The match check found no failures (100.00%). On the name-based side, two different players with the same name and team in a season would be merged; no such case is known.
8. `fetch_normal` skipped match 3879594 (connection reset). Confirmed against StatsBomb's match list on 26 Oct and again against a fresh fetch on 27 Oct: this match is absent from the events file and from the lineups, and it is the only Serie A 2015/16 match missing, so Serie A has 379 of 380 matches. Retrying it would add one match but would change row counts and scores. Nobody has asked for the retry; it needs a team decision.
9. The zone grid is a 3x3 placeholder (`zones.py`). It needs a team decision and must match any teammate zone logic. An 18-zone grid (6x3) was considered and left out because per-player cells would be mostly empty (median 4 to 10 recovery events per player-season).
10. Goalkeepers are 99.9% Ball Recovery. Only Ball Recovery is reported for goalkeepers; Tackle and Interception are kept but marked not reportable. Person 4 decision, not yet agreed with the team. Goalkeeper Ball Recovery counts depend heavily on team style.
11. Per-90 is built from the lineups-based minutes table. The 900-minute threshold is provisional and not agreed with the team.
12. A player's position group is where they played the most minutes. All of their minutes and all of their events count, in any position. The centre-back group is Center Back, Left Center Back and Right Center Back. Players who move between groups are assigned to one group only.
13. No possession adjustment in V1. Players on teams with more possession will have different opportunity to recover the ball than players on teams that defend more. This also affects the percentiles, ratings and tiers.
14. Only La Liga, Ligue 1, Premier League and Serie A 2015/2016 are full league-seasons, so every percentile, rating and tier comes from 2015/2016 data. That is a decade old for scouting use. The team's V1 scope is 2015/16 only. Scores are not comparable across seasons. Single-club seasons have per-90 rates but no percentile, rating or tier (73 qualifying players). Bundesliga has no full league-season: Bundesliga 2015/16 covers only Leverkusen (players in up to 33 of 34 matches; every other team's players in at most 2). At 900 minutes it has 7 Leverkusen players (CB 4, DM 2, GK 1, CM 0).
15. `pctl` in `recovery_per90` (within league-season) is a provisional helper and is not used by the team's pipeline. The pooled percentile, rating and tier per event type are in `recovery_scores` (section 2.6). How the three event types become one per-player score is still the index owner's decision. The three event types stay separate inside the metric.
16. Every match is counted as at most 90 minutes and extra time is ignored. A player on the pitch to the final whistle gets 90. Stoppage-time events still count, which slightly raises every per-90 rate equally. Person 4 decision, not yet agreed with the team.
17. StatsBomb lists some clubs under two names. Marseille / Olympique de Marseille and Caen / Stade Malherbe Caen are mapped to one name in `src/metrics/team_names.py` for minutes and per-90. Without this, a player's season was split across two team names. This assumes they are the same clubs. The recovery by-zone table and the team heatmaps are not yet cleaned this way, and the original events file keeps both names. Check done: the paired names never appear in the same match. For Marseille this was checked across the whole events file (0 matches share both names). Caen's combined count is 38 matches (9 + 29), a full Ligue 1 season. Marseille's combined count is 42 matches (12 + 30): by season and name it is Ligue 1 2015/16: 11 as "Marseille" + 27 as "Olympique de Marseille" = 38 (a full season); Ligue 1 2021/22: 2 as "Olympique de Marseille"; Ligue 1 2022/23: 1 under each name = 2. The 4 matches outside 2015/16 fall in the two PSG-only seasons, where other clubs appear only as PSG's opponents. Ligue 1 2022/23 lists 21 team names; the extra name is the same Marseille / Olympique de Marseille pair (one match each), already covered by the mapping.
18. Fullbacks, wing backs, wide midfielders (Left/Right Midfield), attacking midfielders, wingers and forwards are out of scope. The press resistance owner agreed to align V1 with DM and CM only, keeping AM and WM for future expansion.
19. A missing event row is counted as 0 for a player who played. This affects 1,869 of 7,680 rows.
20. **Some players are listed under two spellings that differ only in a doubled vs single apostrophe (plus one trailing tab).** The lineups show 9 such player_ids: M'Bengue (3424), N'Golo Kanté (3961), M'Vila (4429), N'Gosso Massouma (4469), N'Doye (5676), D'Ambrosio (6984), O'Kane (13248), O'Shea (16890), N'Diaye (40700). The first fix, found in the processed tables, covered seven of them on one team each: Cheikh M'Bengue (Rennes), Cheikh N'Doye (Angers), Eunan O'Kane (AFC Bournemouth), John O'Shea (Sunderland), Mamadou N'Diaye (Montpellier), N'Golo Kanté (Leicester City), Yann Gérard M'Vila (Sunderland). N'Gosso Massouma and D'Ambrosio were not in that seven. In the events file they appear only with the doubled apostrophe (Danilo D''Ambrosio, Inter Milan, 1,769 events; Guy Adolphe N''Gosso Massouma, Angers, 119 events). The single-apostrophe spelling appears only in the lineups, in 3 rows (1 for D'Ambrosio, 2 for N'Gosso Massouma) that have no position or times, so they are non-playing rows dropped before minutes are grouped, and they never split a record. The cause of the doubled apostrophes is unknown. `clean_player` (`src/metrics/player_names.py`) collapses `''` to `'` and strips whitespace. It is still used to line up spellings between the recovery totals and the lineups crosswalk, but player records themselves are now keyed on `player_id` (limitation 23), so a spelling difference no longer splits a player's minutes. The raw files, `recovery_coverage_by_zone` and the per-player heatmaps keep the raw spellings, so per-player zone data for these players must be looked up under the doubled spelling (for example `--player "N''Golo Kanté"`). The same check found a trailing tab in one name (Daniel Arnaud N''Di), which `clean_player` strips. No other name was altered; for example "DaniloD''Ambrosio" keeps its missing space, as in the source. Row-count history: this fix first changed player-season rows from 5,585 to 5,578 and per-90 rows from 7,695 to 7,683; limitation 23 later changed them to 5,576 and 7,680.
21. 422 goalkeeper player-seasons are in `player_minutes`, but 400 are in `recovery_per90`, because per-90 keeps only players with minutes above 0.
22. The in-scope event count moved from 132,035 to 132,036 (out-of-scope 114,358 to 114,357) after the name fix. One event changed side of 246,393; the cause has not been checked and the earlier state is not available to recompute. No practical effect.
23. **Player records are keyed on player_id, not name.** `player_minutes` and `recovery_per90` have one row per player_id + team + competition + season. The display name is the most frequent spelling of that player_id in the lineups, and it is only a label. This replaced name-based keys after the same player appeared under different spellings (for example Fernando Luiz Rosa and Fernando Luiz Roza, player_id 3054), which had split one player's minutes into separate records. 11 player_ids in the lineups have more than one spelling: 9 differ only by a doubled apostrophe, one is Rosa/Roza (3054), and one differs by a double quote (David N'Gog, 401453). The events file has no player_id, so IDs are attached to event counts through a crosswalk built from the lineups (`player_name_crosswalk.parquet`: spelling + team + competition + season -> player_id). Checks: the match-level join of recovery events to lineup players is 100% (304,876 of 304,876), no spelling maps to two player_ids within a team and season (0 clashes; 0 clashes also within a match and team in the lineups), and 0 counted events were lost in the crosswalk. Effect: player-season rows 5,578 -> 5,576, per-90 rows 7,683 -> 7,680, in-scope CM 500 -> 499. The two player-seasons that merged are Fernando Luiz Rosa (Manchester City, Premier League 2015/16, in scope) and David N'Gog (Stade de Reims, Ligue 1 2015/16, out of scope); this is consistent with CM 500 -> 499 and 3 fewer per-90 rows (one player-season x three event types). Limitations: the by-zone table and the heatmaps are still name-based; a player who changes club mid-season remains two records, because team is part of the key. One display name keeps a double quote as in the source (David N"Gog; out of scope, label only).
24. **Scores pool four leagues and assume a recovery rate means the same thing in each.** The data cannot test this. All four leagues are 2015/16, so no cross-season assumption is needed. Percentiles, ratings and tiers also partly reflect team style (limitation 13).
25. **The rating is a display layer.** It is a z-score of per-90, which is right-skewed, so a few top players sit far ahead of the rest. The constants 65 and 10 and the 1-99 clip are choices, not facts. In the V1 run, three pools reach the 99.0 cap and 28 of 1,745 scored rows are 90 or higher.
26. **Tier follows the percentile, not the rating.** In the printed rows, Gold players have ratings from 83.4 to 99.0 and Silver players about 76 to 79. A rating cannot be used to infer a tier.
27. **Ties can sit on a tier boundary.** Tied players share the average rank. In the V1 run the Gold and Silver counts are the ones a tie-free pool would give (checked by arithmetic), so no tie moved a boundary in this run.
28. **DM and CM are ranked together (team working decision).** A DM may rank higher than a CM on recoveries because of the role. This has not been checked.
29. **Goalkeepers are scored on Ball Recovery only** (pool of 98). Tackle and Interception rows for goalkeepers get no score.
30. **Bundesliga and other single-club seasons get no percentile, rating or tier.** The team plans to display Bundesliga statistics with coverage limitations flagged; any comparison against the four-league pool is provisional and is built on the team's side, not in these files.
31. **Playing time comes from the lineups, not from substitution events.** The events file keeps only six event types, so it has no substitutions or Starting XI events, and no other events file exists. Minutes are built from the lineups' start and end times (see 2.3). No fixture lists or fetch logs from the original downloads were saved; the 27 Oct fixtures file is a fresh fetch made to verify coverage.

### Sample size

Median events per player-season is 4 to 10 even for CB/DM, and the bottom quarter has 2 to 4. The median in-scope player-season has only 113 to 180 minutes, so per-90 rates for low-minute players are noisy. Scores use only players with 900 or more minutes.

---

## 5. Open decisions and dependencies

| Decision | Status |
|---|---|
| Minutes table | Done: built from StatsBomb lineups by Person 4 |
| Position groups | Done: GK, CB, DM, CM from lineups; DM and CM combined as Midfielders for scores |
| Goalkeeper handling | Person 4 decision: Ball Recovery only; needs team agreement |
| Minimum minutes | Provisional 900 (press resistance also needs 30 pressured actions); open |
| Tier cutoffs (Gold 90, Silver 75) | Provisional; needs team agreement |
| Rating constants (65, 10) and 1-99 clip | Display choice; needs team agreement |
| Zone grid | 3x3 placeholder; open, must match any teammate zone logic |
| Season scope | Team V1 scope is 2015/16 only |
| Pooling across the four 2015/16 leagues | Done for `recovery_scores` (all four pooled) |
| Rates -> one per-player score | Open (index owner) |
| Wide midfielders and fullbacks out of scope | Agreed for V1 with the press resistance owner |
| Retry of match 3879594 (Serie A) | Open; would change row counts and scores, needs a team yes |
| Processed-table format | Done: `player_minutes.parquet`, `recovery_per90.parquet`, `player_name_crosswalk.parquet`, `statsbomb_lineups.parquet` and `match_metadata.parquet` (derived from the events file) uploaded to the shared Drive by Person 4 on 26 Oct (player_id-keyed, rebuilt in one run); `statsbomb_fixtures_2015_16.parquet` uploaded on 27 Oct. `recovery_scores.parquet` to be shared |

---

## 6. Reproducing the results

Run from the repo root (Windows PowerShell):

```
python -W ignore -m src.metrics.build_metric_tables
python -W ignore -m src.ingestion.fetch_lineups
python -W ignore -m src.ingestion.fetch_fixtures
python -W ignore -m src.metrics.player_minutes
python -W ignore -m src.metrics.recovery_per90
python -W ignore -m src.metrics.recovery_scores
python -W ignore -m src.viz.zone_heatmap
python -m pytest -q
```

`player_minutes` must run before `recovery_per90`: it writes both `player_minutes.parquet` and `player_name_crosswalk.parquet`, which `recovery_per90` reads. `recovery_scores` reads `recovery_per90.parquet`. `recovery_per90` takes `--min-minutes` (default 900) and `--full-season-matches` (default 300). `zone_heatmap` needs `--kind {recovery,spatial}`; see `--help` for the other options. Outputs are written to `data/processed/` and `figures/` (not in git).

`fetch_fixtures` needs no other script to run first. It fetches StatsBomb's match list for the four 2015/16 leagues, saves it to `data/raw/statsbomb_fixtures_2015_16.parquet`, and prints a comparison against the events and lineups files. It changes no other file and stops with an error if a fetch fails (no silent skipping). It is not used by any metric; it only verifies coverage.

The test suite currently has 44 passing tests (run 26 Oct 2026), including `tests/test_player_id_keys.py` (display names and the crosswalk) and `tests/test_recovery_scores.py` (9 tests for `recovery_scores.py`). The `recovery_scores` tests use small made-up tables, not real football data, and check: DM and CM share one pool while CB stays separate; a goalkeeper Tackle gets N/A while a goalkeeper Ball Recovery is scored; a player below the minimum minutes gets N/A; ineligible rows do not change the pool; the Gold (90) and Silver (75) boundaries; the three event types are scored separately; and the rating (a constant pool gives 65, the 99 clip, mean 65 and spread 10 when not clipped). Not covered by a test: ties sitting on a tier boundary (limitation 27), and `fetch_fixtures.py`.

---

## 7. Items to confirm before this is final

Open items that remain (everything else listed earlier was checked and is recorded in the sections above):

- Spatial: the array order of points when two distances tie exactly (the code uses `argmin`, so the first point wins). Low impact.
- Why one event moved from out-of-scope to in-scope after the name fix (limitation 22). One event of 246,393; the earlier state is not available to recompute.
- Double-counting check (proxy), done with a one-line command, not yet a tested script: of 70,739 counted Tackles and Interceptions, 0.5% (3 s), 0.8% (5 s) and 1.3% (10 s) are followed by a Ball Recovery from the same player in the same match and period. This is not proof of the same underlying action; the reverse order (Recovery then Tackle) and other players were not checked. Possession is not available in the events file.
- Team formula document (Metric Formulas.docx) versus these files: it says "Total Interceptions" while the data counts successful interceptions only, so the wording should change to "Successful". It calls mu and sigma "constants for each category"; here they are computed from the eligible pool (same season, group and event type, four leagues pooled, 900+ minutes), which is assumed to be what the team means. It has no 1-99 clip and no percentile or tiers.
- The partial seasons (single-club) were not compared against StatsBomb's match list; only the four 2015/16 leagues were.