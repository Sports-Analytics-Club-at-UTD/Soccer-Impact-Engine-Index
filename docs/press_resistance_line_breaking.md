# Metric Documentation: Press Resistance and Progressive Line-Breaking Pass Value

Owner: Joseph (Press Resistance + Line-Breaking)
Version: V1 draft, 12 October 2026
Scope: midfielders, center-backs, goalkeepers (GK, CB, DM, CM, from `player_minutes.py`)

Labels follow `metric_documentation.md`: **RAW**, **DERIVED**, **ASSUMPTION**, **N/A rule**.

## Shared conventions

- Pitch is 120 x 80 yards; every event is from the acting team's view, attacking x = 120. Distance to goal = distance to (120, 40). **RAW convention**
- Open-play pass = `type == "Pass"` and `pass_type` empty, `Recovery` or `Interception`. **ASSUMPTION**
- Minutes, position groups, team-name cleaning, full-coverage rule (>= 300 matches), the provisional 900-minute minimum and percentiles within league-season x position group are reused from Person 4's work so outputs line up.
- Players are matched on name + team + competition + season. A player with no events gets 0. **ASSUMPTION** (same as `recovery_per90`)

## Metric 1: Press Resistance

Code: `src/metrics/press_resistance.py`. Output: `data/processed/press_resistance_per90.parquet`.

| Event | Condition | Result |
|---|---|---|
| Pass (open play) | `under_pressure` and `pass_outcome` empty | Retained |
| Pass (open play) | `under_pressure` and outcome `Incomplete`, `Out`, `Pass Offside` | Lost |
| Pass | outcome `Unknown`, `Injury Clearance` | Excluded |
| Dribble | `Complete` / `Incomplete` | Retained / Lost |
| Miscontrol | `under_pressure` | Lost |
| Dispossessed | any (**ASSUMPTION**) | Lost |
| Carry | any | Not in the rate |

Columns: `pr_retention_rate` (headline), `pr_actions_p90`, `pr_retained_p90`, `pr_prog_carries_p90` (pressured carries >= 10 yards forward, **ASSUMPTION**).

N/A rules: fewer than 50 pressured actions -> rate N/A (**ASSUMPTION**); goalkeepers pass part only (**ASSUMPTION**); single-club seasons and players below the minimum minutes get no percentile.

**Data dependency:** `Miscontrol` and `Dispossessed` must be added to `RELEVANT_EVENT_TYPES` in `src/ingestion/fetch_normal.py` and the fetch re-run. The script refuses to run without them, because rates would be biased upwards.

## Metric 2: Progressive Line-Breaking Pass Value

Code: `src/metrics/line_breaking.py`. Output: `data/processed/line_breaking_per90.parquet`.

### Level A: all matches, events only

- Progressive = open play, complete, `d_end <= 0.75 * d_start`, and `end_x - start_x >= 10`. **ASSUMPTION**
- Attempt = same geometry, complete or not. For incomplete passes `pass_end_location` is where the pass ended, not where it was aimed. **ASSUMPTION**
- Third-crossing = progressive and ends in a higher third (x = 40, 80).
- Pass value = `(d_start - d_end) * (1 - p_hat)`, `p_hat` = completion rate in league-season x start third x length band (0-15, 15-30, 30+). **DERIVED**
- Columns: `prog_passes_p90`, `prog_completion_pct`, `third_cross_p90`, `pass_value_p90` (headline), plus percentiles.

### Level B: 360 matches only

- `opponents_bypassed` = visible outfield opponents with x strictly between pass start and end x. Line break if >= 3. **ASSUMPTION**
- Reported only when every match of the league-season has 360 frames and the player has >= 450 minutes. No percentiles (one club per season, no fair pool).
- Lower bound: opponents outside the camera view are not counted.
- The script prints an orientation check (actor position vs pass start) and a Level A vs Level B crosstab to show how good a stand-in Level A is.

## Reproducing

```
python -W ignore -m src.metrics.player_minutes        # Person 4, needed first
python -W ignore -m src.metrics.press_resistance
python -W ignore -m src.metrics.line_breaking          # add --no-360 to skip Level B
python -m pytest tests/test_press_line_breaking.py
```

## Open decisions

| Decision | Status |
|---|---|
| Add Miscontrol and Dispossessed to the fetch | Needed before Press Resistance can run |
| Thresholds: 50 actions, 25% / 10 yards, 3 opponents, 450 minutes (360) | ASSUMPTION, calibrate week of 10/12 |
| Show Level B in the dashboard, or only use it to validate Level A | Open (Vibhor / Ayush) |
