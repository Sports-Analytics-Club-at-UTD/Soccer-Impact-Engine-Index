/* Synthetic bounded contract fixtures. Never copy these to public/data. */
import { CANONICAL_KEYS, FIELD_DEFINITIONS, LIMITATIONS, SCHEMA_VERSION } from "../../src/lib/scorecardAdapter.js";

export function player(changes = {}) {
  const row = Object.fromEntries(Object.keys(FIELD_DEFINITIONS).map((field) => [field, field.endsWith("_present") ? false : null]));
  return { ...row, player_id: "1", team: "Team", competition_name: "League", season_name: "Season",
    player_name: "Synthetic Player", position_group: "CB", ...changes };
}
export function payload(players = [player()]) {
  return { schema_version: SCHEMA_VERSION, measurement_type: "raw_metrics", metadata: {
    canonical_keys: [...CANONICAL_KEYS], integer_encoding: "decimal_string", fields: structuredClone(FIELD_DEFINITIONS),
    coverage_status: "unverified", limitations: [...LIMITATIONS], passing_reference: null }, players };
}
export function passingPayload() {
  const p = payload();
  const row = p.players[0];
  for (const [field, spec] of Object.entries(FIELD_DEFINITIONS)) {
    if (spec.component === "passing" && spec.kind === "integer") row[field] = "0";
  }
  Object.assign(row, { passing_present: true, value_sum: 0, passing_minutes: 0,
    passing_rate_status: "zero_minutes", passing_difficulty_scope: "synthetic bounded reference", passing_difficulty_complete: true });
  p.metadata.passing_reference = { scope: row.passing_difficulty_scope, declared_complete: true, independently_verified: false };
  return p;
}
export const response = (data) => ({ ok: true, status: 200, json: async () => data });
