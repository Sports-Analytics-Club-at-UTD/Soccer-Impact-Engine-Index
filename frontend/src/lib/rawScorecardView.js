import { displayMetric } from "./scorecardAdapter.js";

export const RAW_MODE_NOTICE = "Raw player metrics — source completeness and scoring eligibility not yet verified.";
export const RAW_METRIC_NOTICE = "Statistics are raw measurements. No overall score is available; no percentile ranking has been approved. Source coverage may be incomplete. Missing measurements show N/A.";
export const BROWSE_LABEL = "Available player profiles";
export const playerLabel = (p) => p.player_name?.trim() ? p.player_name : `Player ID ${p.player_id}`;
export const positionLabel = (p) => p.position_group?.trim() ? p.position_group : "Unspecified";
export const contextLabel = (p) => `${p.team} · ${p.competition_name} · ${p.season_name}`;
const positionKey = (p) => p.position_group?.trim() ? `known:${p.position_group}` : "unspecified";
const fold = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

export function positionOptions(players) {
  const observed = new Map(players.map((p) => [positionKey(p), positionLabel(p)]));
  return [{ value: "", label: "All" }, ...[...observed].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)
    .map(([value, label]) => ({ value, label }))];
}

export function browsePlayers(players, { query = "", position = "" } = {}) {
  const q = query.trim();
  // Preserve adapter canonical order: filtering is browsing, never metric ranking.
  return players.filter((p) => (!position || positionKey(p) === position)
    && (!q || p.player_id === q || (p.player_name?.trim() && fold(p.player_name).includes(fold(q)))));
}

export const selectContext = (players, key) => players.find((p) => p.context_key === key) ?? null;
export function adjacentContext(players, key, direction) {
  if (!players.length) return null;
  const current = players.findIndex((p) => p.context_key === key);
  const next = current < 0 ? (direction > 0 ? 0 : players.length - 1)
    : Math.min(players.length - 1, Math.max(0, current + direction));
  return players[next].context_key;
}

export const RECOVERY_COMPONENTS = [
  ["recovery_tackle", "Successful tackles"],
  ["recovery_interception", "Successful interceptions"],
  ["recovery_ball_recovery", "Ball recoveries"],
];
export const PRESS_METRICS = [
  ["pressured_pass_attempts", "Pressured pass attempts"],
  ["pressured_pass_completed", "Pressured pass completions"],
  ["pressured_dribble_attempts", "Pressured dribble attempts"],
  ["pressured_dribble_completed", "Pressured dribble completions"],
  ["pressured_actions", "Combined pressured actions"],
  ["successful_pressured_actions", "Combined successful actions"],
  ["pressured_pass_completion_rate", "Pressured pass completion percentage"],
  ["pressured_dribble_completion_rate", "Pressured dribble completion percentage"],
  ["press_resistance_rate", "Combined press resistance percentage"],
];
export const PASSING_METRICS = [
  ["prog_attempts", "Progressive attempts"], ["prog_passes", "Completed progressive passes"],
  ["third_cross", "Third-crossing progressive passes"], ["value_sum", "Total pass value"],
  ["prog_passes_p90", "Progressive passes per90"], ["prog_completion_pct", "Progressive completion percentage"],
  ["third_cross_p90", "Third crossings per90"], ["pass_value_p90", "Pass value per90"],
];

export function componentAvailability(player, prefix) {
  if (!player[`${prefix}_present`]) return "Not available — no source component row.";
  const status = player[`${prefix}_rate_status`];
  if (status === "missing_minutes") return "Source row present; per90 rates unavailable because source minutes are missing.";
  if (status === "zero_minutes") return "Source row present; per90 rates unavailable because source minutes are zero.";
  return "Source row present; presence does not verify source coverage.";
}

export function rawCardModel(player, metadata) {
  const metrics = (pairs) => pairs.map(([field, label]) => ({ field, label, ...displayMetric(player, field) }));
  return {
    name: playerLabel(player), context: contextLabel(player), position: positionLabel(player),
    player_id: player.player_id, context_key: player.context_key,
    descriptors: metrics([["minutes", "Minutes"], ["matches", "Matches"]]),
    recovery: RECOVERY_COMPONENTS.map(([prefix, label]) => ({ prefix, label,
      availability: componentAvailability(player, prefix), status: player[`${prefix}_rate_status`] ?? "N/A",
      exposure: displayMetric(player, `${prefix}_minutes`).text,
      metrics: metrics([[`${prefix}_count`, "Observed count"], [`${prefix}_per90`, "Per90 rate"]]) })),
    press: { availability: componentAvailability(player, "press"), metrics: metrics(PRESS_METRICS),
      exposure: displayMetric(player, "press_minutes").text },
    passing: { title: "Progressive passing — Level A", availability: componentAvailability(player, "passing"),
      status: player.passing_rate_status ?? "N/A", metrics: metrics(PASSING_METRICS),
      exposure: displayMetric(player, "passing_minutes").text,
      scope: player.passing_difficulty_scope ?? "N/A",
      declaration: player.passing_present
        ? "Caller-attested complete: Yes. Independently verified: No."
        : "Calibration: N/A — no passing source row.",
    },
    coverage: metadata.coverage_status, limitations: [...metadata.limitations],
  };
}
