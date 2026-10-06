# Metric Documentation: Defensive Recovery Coverage and Observed Spatial Dominance

Owner: Person 4 (Spatial + Defensive Recovery)
Version: V1, October 2026
Scope: midfielders, center-backs, goalkeepers (no attackers/wingers)

## 0. How to read this document

Every statement is labelled by what kind of thing it is:

- **RAW**: a field or value that comes directly from StatsBomb Open Data.
- **DERIVED**: something we calculate from raw fields.
- **ASSUMPTION**: a choice we made that the data does not prove.
- **N/A rule**: when the data does not support a result, we output N/A. We never infer or substitute another metric.

---

## 1. Data used

### 1.1 Files

| File | Source script | Contents | Stored in |
|---|---|---|---|
| `statsbomb_team_events.parquet` | `fetch_statsbomb_5leagues.py` | 3,626,433 event rows, 1,814 matches, six event types: Pass, Carry, Ball Recovery, Dribble, Duel, Interception. No `player_id` column. | Shared Drive (not git) |
| `statsbomb_360_frames.parquet` | `fetch_statsbomb_360.py` | 7,562,022 rows, 445,569 frame ids, 127 matches | Shared Drive (not git) |
| 360 event-meta lookup | `src/ingestion/fetch_360_event_meta.py` | `id`, `match_id`, `team`, `possession_team` | Shared Drive (not git) |

The fetch scripts are in git so the data can be rebuilt. The parquet files are too large for git.

### 1.2 Fields used (all RAW)

- Events: `type`, `duel_type`, `duel_outcome`, `interception_outcome`, `ball_recovery_recovery_failure`, `location`, `position`, `team`, `player`, plus match, competition and season identifiers.
- 360 frames: `id`, `visible_area`, `teammate`, `actor`, `keeper`, `location`.
- Event-meta lookup: `id`, `match_id`, `team`, `possession_team`.

### 1.3 Coverage

**Events (Recovery Coverage):** five target leagues. Seasons are uneven: La Liga 2016/17 to 2020/21, Ligue 1 2021/22 and 2022/23, Bundesliga 2023/24. Premier League and Serie A each have only 2015/2016 inside the last-10-years window.

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

This is the individual-player metric.

### 2.1 In plain words

How many times did a player win the ball back, and where on the pitch? Tackles, interceptions and ball recoveries are counted separately and never added together inside the metric.

### 2.2 Input -> calculation -> result

**Input (RAW):** event rows of type Interception, Ball Recovery, and Duel with `duel_type == "Tackle"`, with their outcome fields, `location`, `position`, `player`, `team`, competition, season.

**Calculation (DERIVED):**

1. Keep three event types, each kept distinct:
   - **Tackle**: Duel events where `duel_type == "Tackle"`. Tackles are not their own top-level event type in the data.
   - **Interception**: Interception events.
   - **Ball Recovery**: Ball Recovery events.
2. Keep only successful events:
   - Tackle and Interception: `duel_outcome` / `interception_outcome` in `SUCCESS_OUTCOMES` = {Won, Success In Play, Success Out}. Lost In Play and Lost Out are excluded.
   - Ball Recovery: kept unless `ball_recovery_recovery_failure` is True.
3. Assign each event to a pitch zone from its `location` using `src/metrics/zones.py` (currently a 3x3 placeholder grid).
4. Count events per player, team, competition, season, event type, and (separately) per zone.
5. Per-90 rate = count / minutes played x 90. **Not yet computed:** needs the minutes-played table from a teammate's module (`add_per90` already exists in `src/metrics/recovery_coverage.py`).

**Result:**

- `recovery_coverage_totals.parquet`: one row per player-season-event type.
- `recovery_coverage_by_zone.parquet`: one row per player-season-event type-zone.
- Per-player and per-team zone heatmaps (`src/viz/zone_heatmap.py`, `--player` option).
- Counted events in the current data: Tackle 43,290; Interception 27,449; Ball Recovery 175,654 (total 246,393).

### 2.3 Raw vs derived vs assumption

| Item | Type |
|---|---|
| Event type, outcome fields, location, position, player, team | RAW |
| Counts, per-zone counts, per-90 rates | DERIVED |
| Tackles identified through `duel_type == "Tackle"` | RAW field, our selection rule |
| SUCCESS_OUTCOMES set | ASSUMPTION, checked against real label counts |
| Empty recovery-failure flag means a successful recovery | ASSUMPTION (the flag is only ever True or empty) |
| 3x3 zone grid | ASSUMPTION (placeholder, team decision pending) |
| Players identified by name + team + competition + season | ASSUMPTION (no `player_id` in the file) |

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
5. Divide the pitch into 2x2-yard cells. Assign each cell to the nearest visible player.
6. Per zone, defending-team control rate = share of observed cells in that zone assigned to a defending-team player. The attacking side's share is the complement.
7. Aggregate across frames per defending team and zone.
8. N/A rules: a zone with no observed frames is N/A; a team with fewer than `MIN_MATCHES` (10) matches is N/A; a league with no 360 data is N/A.

**Result:**

- `spatial_dominance_team_zone.parquet`: defending team x zone control rate.
- `spatial_coverage.parquet`: how many frames and matches each result is based on.
- Spatial heatmaps for reportable teams only.

**Frame accounting (verified):** 445,569 frame ids = 431,769 used + 13,761 unmatched to an event (3.1%, all in matches 3895266, 3837706, 3895158, 3895309) + 39 skipped for one side only.

**Reportable teams** (matches as defending team in the spatial run): PSG 57, Barcelona 35, Bayer Leverkusen 31. Every other team has 4 or fewer matches (as opponents) and is N/A.

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
3. Not true pitch control. It ignores the ball, player speed, player direction, and anyone outside the camera view. Frames are event-triggered, so they are not evenly spaced in time. Team-level only.
4. Orientation relies on the actor's-perspective assumption, confirmed by the goalkeeper check.

### Recovery Coverage

5. Failed recoveries are flagged only as True. An empty flag is counted as a successful recovery.
6. SUCCESS_OUTCOMES = Won, Success In Play, Success Out (checked against real label counts).
7. No `player_id` in the events file. Players are identified by name + team + competition + season.
8. `fetch_normal` skipped match 3879594 (connection reset).
9. The zone grid is a 3x3 placeholder (`zones.py`). It needs a team decision and must match any teammate zone logic.
10. Goalkeepers are 99.9% Ball Recovery (17,260 of 17,271 counted events; 5 Interception, 6 Tackle). Handling decision pending.
11. Per-90 needs the minutes-played table. A minimum-minutes rule needs a team decision.
12. Sum a player's events across all positions in the group before applying any threshold. The centre-back group must include Left Center Back, Right Center Back and Center Back.
13. No possession adjustment in V1. Players on teams with more possession will have different opportunity to recover the ball than players on teams that defend more.
14. Premier League and Serie A only have 2015/2016 in the window, so recovery counts are not comparable across leagues by season. Team decision pending.
15. How per-90 recovery rates become a per-player score is the index owner's decision (suggested: percentile within position group, weights agreed by the team). The three event types stay separate inside the metric.

### Sample size

Median events per player-season is 4 to 10 even for CB/DM, and the bottom quarter has 2 to 4. Per-90 rates for low-minute players will be noisy.

---

## 5. Open decisions and dependencies

| Decision | Depends on | Status |
|---|---|---|
| Goalkeeper handling | Team | Open |
| Zone grid (3x3 placeholder) | Team, any teammate zone module | Open |
| Premier League / Serie A season gap | Team | Open |
| Per-90 rates | Minutes-played table (teammate) | Waiting |
| Minimum-minutes rule | Minutes table distribution, team | Waiting |
| Final position groups | Teammate position module | Waiting |
| Rates -> per-player score | Index owner | Open |
| Processed-table format | Dashboard owner | Open |

---

## 6. Reproducing the results

Run from the repo root (Windows PowerShell):

```
python -W ignore -m src.metrics.build_metric_tables
python -W ignore -m src.viz.zone_heatmap
python -W ignore -m src.scripts.inspect_data
python -m pytest tests/test_metrics.py
```

Outputs are written to `data/processed/` and `figures/` (not in git).

---

## 7. Items to confirm against the code before this is final

- Whether cells outside `visible_area` are excluded from the grid.
- Whether control rate is pooled over all observed cells or averaged per frame.
- Whether goalkeepers are included as nearest-player candidates in the spatial grid.
- How ties (equal distance) are broken.
- Why defending-team match counts (Leverkusen 31, PSG 57) are lower than the matches in the free 360 set (34 and 58). This may relate to the four matches with unmatched frames; confirm before stating a reason.
- Whether the 43,290 / 27,449 / 175,654 counts are after the success filter.