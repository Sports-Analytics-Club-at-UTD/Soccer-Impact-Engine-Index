/* Raw scorecard contract only. Intentionally independent of demo data/archetypes. */
export const SCHEMA_VERSION = "soccer-scorecard/v1";
export const CANONICAL_KEYS = Object.freeze(["player_id", "team", "competition_name", "season_name"]);
export const LIMITATIONS = Object.freeze([
  "Source-row presence does not establish complete source coverage.",
  "Calibration completeness is caller-attested, not independently verified.",
  "No complete production player population or approved scoring is claimed.",
]);
const RECOVERY = ["recovery_tackle", "recovery_interception", "recovery_ball_recovery"];
const COMPONENTS = [...RECOVERY, "press", "passing"];
const definitions = {};
const add = (name, kind, unit, component = null) => {
  definitions[name] = Object.freeze({ kind, unit, component });
};
CANONICAL_KEYS.forEach((c) => add(c, c === "player_id" ? "id" : "text", "identity"));
add("player_name", "text", "label");
add("position_group", "text", "label");
add("minutes", "number", "minutes");
add("matches", "integer", "matches");
RECOVERY.forEach((prefix) => {
  [["count", "integer", "events"], ["per90", "number", "events/90min"],
    ["rate_status", "status", "status"], ["minutes", "number", "minutes"],
    ["present", "boolean", "presence"]].forEach(([suffix, kind, unit]) => add(`${prefix}_${suffix}`, kind, unit, prefix));
});
const PRESS_COUNTS = ["pressured_pass_attempts", "pressured_pass_completed", "pressured_dribble_attempts",
  "pressured_dribble_completed", "pressured_actions", "successful_pressured_actions"];
PRESS_COUNTS.forEach((c) => add(c, "integer", "events", "press"));
["pressured_pass_completion_rate", "pressured_dribble_completion_rate", "press_resistance_rate"]
  .forEach((c) => add(c, "number", "percent", "press"));
add("press_minutes", "number", "minutes", "press");
add("press_present", "boolean", "presence", "press");
["prog_attempts", "prog_passes", "third_cross"].forEach((c) => add(c, "integer", "events", "passing"));
[["value_sum", "difficulty_weighted_yards"], ["prog_passes_p90", "events/90min"],
  ["prog_completion_pct", "percent"], ["third_cross_p90", "events/90min"],
  ["pass_value_p90", "difficulty_weighted_yards/90min"], ["passing_minutes", "minutes"]]
  .forEach(([c, unit]) => add(c, "number", unit, "passing"));
add("passing_rate_status", "status", "status", "passing");
add("passing_difficulty_scope", "text", "reference_scope", "passing");
add("passing_difficulty_complete", "boolean", "caller_attestation", "passing");
add("passing_present", "boolean", "presence", "passing");
export const FIELD_DEFINITIONS = Object.freeze(definitions);

export class ScorecardPayloadError extends Error {}
const fail = (message) => { throw new ScorecardPayloadError(message); };
const object = (v) => v !== null && typeof v === "object" && !Array.isArray(v)
  && [Object.prototype, null].includes(Object.getPrototypeOf(v));
const exactKeys = (value, keys, label) => {
  if (!object(value) || Object.keys(value).length !== keys.length
    || keys.some((c) => !Object.hasOwn(value, c))) fail(`${label}: missing or unsupported fields`);
};
const equalArray = (a, b) => Array.isArray(a) && a.length === b.length && a.every((v, i) => v === b[i]);
const integer = (v, positive, label) => {
  if (typeof v !== "string" || !/^(0|[1-9][0-9]*)$/.test(v) || v.length > 19
    || BigInt(v) > 9223372036854775807n || (positive && v === "0")) fail(`${label}: exact decimal int64 string required`);
};
function validateValue(value, field) {
  const { kind, unit } = FIELD_DEFINITIONS[field];
  if (value === null && kind !== "id" && !CANONICAL_KEYS.includes(field) && !field.endsWith("_present")) return;
  if (kind === "id" || kind === "integer") integer(value, kind === "id", field);
  else if (kind === "number") {
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0
      || (unit === "percent" && value > 100)) fail(`${field}: invalid finite raw measurement`);
  } else if (kind === "boolean") {
    if (typeof value !== "boolean") fail(`${field}: boolean required`);
  } else if (typeof value !== "string" || (CANONICAL_KEYS.includes(field) && !value.trim())
    || (kind === "status" && !["ok", "zero_minutes", "missing_minutes"].includes(value))) fail(`${field}: invalid label/status`);
}

export function contextKey(record) {
  CANONICAL_KEYS.forEach((c) => validateValue(record[c], c));
  return JSON.stringify(CANONICAL_KEYS.map((c) => record[c]));
}

// Code-point comparison agrees with Python string sorting, without locale rules.
function compareText(a, b) {
  const x = Array.from(a), y = Array.from(b);
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const delta = x[i].codePointAt(0) - y[i].codePointAt(0);
    if (delta) return delta;
  }
  return x.length - y.length;
}

export function parseScorecard(payload) {
  exactKeys(payload, ["schema_version", "measurement_type", "metadata", "players"], "payload");
  if (payload.schema_version !== SCHEMA_VERSION) fail("Unsupported scorecard version");
  if (payload.measurement_type !== "raw_metrics") fail("Only raw measurements are supported");
  const meta = payload.metadata;
  exactKeys(meta, ["canonical_keys", "integer_encoding", "fields", "coverage_status", "limitations", "passing_reference"], "metadata");
  if (!equalArray(meta.canonical_keys, CANONICAL_KEYS) || meta.integer_encoding !== "decimal_string"
    || meta.coverage_status !== "unverified" || !equalArray(meta.limitations, LIMITATIONS)) fail("Unsupported coverage/identity metadata");
  exactKeys(meta.fields, Object.keys(FIELD_DEFINITIONS), "field definitions");
  for (const [c, spec] of Object.entries(FIELD_DEFINITIONS)) {
    exactKeys(meta.fields[c], ["kind", "unit", "component"], c);
    if (Object.keys(spec).some((key) => spec[key] !== meta.fields[c][key])) fail(`${c}: incompatible metric units/meaning`);
  }
  const ref = meta.passing_reference;
  if (ref !== null) {
    exactKeys(ref, ["scope", "declared_complete", "independently_verified"], "passing reference");
    if (typeof ref.scope !== "string" || !ref.scope.trim() || ref.declared_complete !== true
      || ref.independently_verified !== false) fail("Invalid calibration declaration");
  }
  if (!Array.isArray(payload.players)) fail("players must be an array");
  const seen = new Set();
  const aliases = { Marseille: "Olympique de Marseille", Caen: "Stade Malherbe Caen" };
  const players = payload.players.map((source) => {
    exactKeys(source, Object.keys(FIELD_DEFINITIONS), "player context");
    for (const c of Object.keys(FIELD_DEFINITIONS)) validateValue(source[c], c);
    const row = { ...source, team: Object.hasOwn(aliases, source.team) ? aliases[source.team] : source.team };
    const key = contextKey(row);
    if (seen.has(key)) fail(`Duplicate canonical identity: ${key}`);
    seen.add(key);
    for (const component of COMPONENTS) {
      const fields = Object.keys(FIELD_DEFINITIONS).filter((c) => FIELD_DEFINITIONS[c].component === component
        && c !== `${component}_present`);
      if (!row[`${component}_present`] && fields.some((c) => row[c] !== null)) fail(`${component}: absent component has values`);
      if (row[`${component}_present`]) {
        if (fields.some((c) => FIELD_DEFINITIONS[c].kind === "integer" && row[c] === null)) fail(`${component}: missing observed counts`);
        if (component !== "press") {
          const prefix = component === "passing" ? "passing" : component;
          const minutes = row[`${prefix}_minutes`];
          const status = minutes === null ? "missing_minutes" : minutes === 0 ? "zero_minutes" : "ok";
          if (row[`${prefix}_rate_status`] !== status) fail(`${component}: inconsistent exposure/status`);
        }
      }
    }
    if (row.passing_present && (ref === null || row.passing_difficulty_scope !== ref.scope
      || row.passing_difficulty_complete !== true)) fail("Missing/mismatched passing calibration");
    const minutes = ["minutes", ...RECOVERY.map((p) => `${p}_minutes`), "press_minutes", "passing_minutes"]
      .map((c) => row[c]).filter((v) => v !== null);
    if (new Set(minutes).size > 1) fail("Conflicting minutes across components");
    return { ...row, context_key: key };
  });
  players.sort((a, b) => {
    const x = BigInt(a.player_id), y = BigInt(b.player_id);
    if (x !== y) return x < y ? -1 : 1;
    for (const c of CANONICAL_KEYS.slice(1)) {
      const delta = compareText(a[c], b[c]);
      if (delta) return delta;
    }
    return 0;
  });
  return { schema_version: SCHEMA_VERSION, measurement_type: "raw_metrics",
    metadata: JSON.parse(JSON.stringify(meta)), players };
}

export function displayMetric(record, field) {
  if (!Object.hasOwn(FIELD_DEFINITIONS, field) || !["number", "integer"].includes(FIELD_DEFINITIONS[field].kind)) fail("Unsupported numeric metric");
  const { unit, kind } = FIELD_DEFINITIONS[field];
  const value = record[field];
  validateValue(value, field);
  if (value === null) return { value: null, unit, text: "N/A", chartValue: null };
  const chartValue = kind === "integer" ? (BigInt(value) <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(value) : null) : value;
  const text = kind === "integer" ? value : value.toFixed(2).replace(/\.?0+$/, "");
  return { value, unit, text: unit === "percent" ? `${text}%` : `${text} ${unit}`, chartValue };
}
