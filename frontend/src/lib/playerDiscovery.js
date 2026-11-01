import { FIVE_METRICS } from "./fiveAttributePresentation.js";
import { playerDataStatus } from "./playerDataStatus.js";
export const EXPERIMENTAL_LEAGUES = ["Premier League", "La Liga", "Serie A", "Ligue 1", "1. Bundesliga"];
const normalize = (v) => String(v).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim();
export function filterExperimentalPlayers(players, { query = "", league = "", position = "", coverage = "", limited = false } = {}) {
  const terms = normalize(query).split(/\s+/).filter(Boolean);
  return players.filter((player) => {
    const p = player.presentation;
    const haystack = normalize([p.name, p.player_id, p.comparison_position, p.primary_position, ...p.positions, ...p.secondary_positions, ...p.clubs.flatMap((c) => [c.name, c.competition_name])].join(" "));
    const count = FIVE_METRICS.filter((m) => p.attributes[m.id].rating !== null).length;
    return terms.every((term) => haystack.includes(term)) && (!league || p.clubs.some((c) => c.competition_name === league)) && (!position || p.comparison_position === position) && (!coverage || (coverage === "complete" ? count === 5 : count > 0 && count < 5)) && (!limited || playerDataStatus(player).limited);
  }).sort((a, b) => a.name.localeCompare(b.name) || Number(BigInt(a.presentation.player_id) - BigInt(b.presentation.player_id)));
}
