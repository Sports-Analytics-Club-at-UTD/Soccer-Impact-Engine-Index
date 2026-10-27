export const DIAGNOSTIC_NOTICE = "DIAGNOSTIC — PROVISIONAL REAL DATA";
export const profileName = (p) => p.identity.player_name ?? (p.identity.observed_name_variants.join(" / ") || "Unnamed event actor");
export const profileContext = (p) => [p.identity.team, p.identity.competition_name, p.identity.season_name].join(" · ");
const fold = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
export function browseDiagnosticProfiles(model, query = "", match = "") {
  return model.profiles.filter((p) => (!match || p.scope.observed_match_ids.includes(match)) &&
    fold([profileName(p), profileContext(p), p.identity.player_id, ...p.identity.observed_name_variants].join(" ")).includes(fold(query.trim())));
}
export const selectDiagnosticProfile = (rows, key) => rows.find((p) => p.context_key === key) ?? null;
export const diagnosticWindow = (p, match = "") => match ? p.matches.find((m) => m.match_id === match) ?? null : p.pooled;
export const diagnosticValue = (v) => v === null || v === undefined ? "N/A" : typeof v === "number" ? v.toLocaleString("en", { maximumFractionDigits: 3 }) : v;
export const reasonText = (s) => s.replaceAll("_", " ");
export const zeroMinuteWarning = (p) => p.pooled.exposure.source_ambiguities.includes("observed_activity_with_zero_delivered_minutes");
