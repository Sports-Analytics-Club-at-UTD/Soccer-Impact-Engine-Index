import { parseRatingJson } from "./ratingDelivery.js";

export const FIVE_SCHEMA = "soccer-five-attribute-presentation/v1";
export const FIVE_NOTICE = "SYNTHETIC TEST FIXTURE / NOT REAL PLAYER RATINGS / NOT PUBLICATION AUTHORIZED";
export const FIVE_METRICS = [
  { id: "tackles", key: "TAC", label: "Tackling" },
  { id: "interceptions", key: "INT", label: "Interceptions" },
  { id: "recoveries", key: "REC", label: "Ball Recovery" },
  { id: "press_resistance", key: "PRS", label: "Press Resistance" },
  { id: "line_breaking_passes", key: "PROG", label: "Line Breaking — Progressive Passing Proxy" },
];
const names = FIVE_METRICS.map((m) => m.id);
const check = (v, message) => { if (!v) throw Error(`Invalid five-attribute presentation: ${message}`); };
const object = (v) => v && typeof v === "object" && !Array.isArray(v);
const keys = (v, fields) => check(object(v) && Object.keys(v).length === fields.length && fields.every((k) => Object.hasOwn(v, k)), "unexpected or missing fields");
const text = (v) => typeof v === "string" && !!v.trim();
const synthetic = (v) => typeof v === "string" && v.startsWith("synthetic:") && v.length > 10;
const number = (v, lo = 0, hi = Infinity) => typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi;
const integer = (v) => Number.isSafeInteger(v) && v >= 0;
const fingerprint = (v) => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const near = (a, b) => number(a) && Math.abs(a - b) <= 1e-10 * Math.max(1, Math.abs(b));
const unique = (vs, predicate = text) => check(Array.isArray(vs) && vs.every(predicate) && new Set(vs).size === vs.length, "unique strings required");
export function presentationMinutes(v) {
  keys(v, ["numerator", "denominator"]);
  check(integer(v.numerator) && integer(v.denominator) && v.denominator > 0, "exact supported minutes required");
  return v.numerator / v.denominator;
}
function canonical(v) {
  if (Array.isArray(v)) return v.map(canonical);
  if (object(v)) return Object.fromEntries(Object.keys(v).sort().map((k) => [k, canonical(v[k])]));
  return v;
}
async function digest(v) {
  const bytes = new TextEncoder().encode(JSON.stringify(canonical(v)));
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((b) => b.toString(16).padStart(2, "0")).join("");
}
const withoutFingerprint = ({ fingerprint: ignored, ...body }) => body;

async function validateReference(ref) {
  keys(ref, ["version", "synthetic", "positions", "fingerprint"]);
  check(synthetic(ref.version) && ref.synthetic === true, "synthetic frozen reference required");
  keys(ref.positions, ["MID", "CB"]);
  for (const [group, pools] of Object.entries(ref.positions)) {
    keys(pools, names);
    for (const [a, p] of Object.entries(pools)) {
      keys(p, ["population_version", "comparison_position", "metric_id", "n", "mean", "sample_sd", "member_ids", "fingerprint"]);
      check(synthetic(p.population_version) && p.comparison_position === group && p.metric_id === a, "position-specific reference mismatch");
      unique(p.member_ids, synthetic);
      check(integer(p.n) && p.n === p.member_ids.length && p.n >= 2 && number(p.mean) && number(p.sample_sd) && p.sample_sd > 0, "frozen mean/sample SD required");
      check(fingerprint(p.fingerprint) && p.fingerprint === await digest(withoutFingerprint(p)), "pool fingerprint mismatch");
    }
  }
  check(fingerprint(ref.fingerprint) && ref.fingerprint === await digest(withoutFingerprint(ref)), "reference fingerprint mismatch");
}

export function validateFiveAttributeCard(p, ref) {
  keys(p, ["id", "player_id", "name", "season_name", "comparison_position", "positions", "clubs", "limited_data", "partial_season", "attributes", "provenance"]);
  check(synthetic(p.player_id) && p.id === `${p.player_id}:${p.season_name}` && p.season_name === "2015/2016" && typeof p.name === "string" && p.name.startsWith("SYNTHETIC "), "synthetic canonical player-season required");
  check(["MID", "CB", null].includes(p.comparison_position), "comparison position must be MID/CB or missing");
  unique(p.positions);
  check(typeof p.limited_data === "boolean" && typeof p.partial_season === "boolean", "explicit coverage warnings required");
  check(Array.isArray(p.clubs) && p.clubs.length, "club contexts required");
  const fixtures = new Set(), contexts = new Set(); let bundes = false;
  for (const c of p.clubs) {
    keys(c, ["name", "competition_name", "match_ids"]);
    check(typeof c.name === "string" && c.name.startsWith("SYNTHETIC ") && ["La Liga", "Premier League", "Serie A", "Ligue 1", "1. Bundesliga"].includes(c.competition_name), "synthetic club/league required");
    unique(c.match_ids, synthetic);
    const context = JSON.stringify([c.name, c.competition_name]);
    check(c.match_ids.length && c.match_ids.every((id) => !fixtures.has(id)) && !contexts.has(context), "overlapping or duplicate transfer contexts");
    c.match_ids.forEach((id) => fixtures.add(id)); contexts.add(context); bundes ||= c.competition_name === "1. Bundesliga";
  }
  check(!bundes || p.limited_data && p.partial_season, "Bundesliga requires LIMITED DATA / PARTIAL SEASON");
  check(Array.isArray(p.provenance) && p.provenance.length, "provenance required");
  const sources = new Set();
  for (const s of p.provenance) {
    keys(s, ["id", "label", "source", "fingerprint"]);
    check(synthetic(s.id) && text(s.label) && synthetic(s.source) && fingerprint(s.fingerprint) && !sources.has(s.id), "synthetic provenance required"); sources.add(s.id);
  }
  keys(p.attributes, names);
  for (const { id: a, label } of FIVE_METRICS) {
    const m = p.attributes[a];
    keys(m, ["label", "measurement_kind", "rating", "percentile", "observation", "normalization", "missingness", "exclusions", "limited_data", "partial_season", "provenance_ids"]);
    check(m.label === label && m.measurement_kind === (a === "line_breaking_passes" ? "progressive_passing_proxy" : "observed_metric"), "explicit metric/proxy label required");
    check(m.rating === null || number(m.rating, 1, 99), "rating must be null or 1..99");
    check(m.percentile === null || number(m.percentile, 0, 100), "percentile must be null or 0..100");
    unique(m.missingness); unique(m.provenance_ids, synthetic);
    check(m.provenance_ids.length && m.provenance_ids.every((s) => sources.has(s)), "bound provenance required");
    check(typeof m.limited_data === "boolean" && typeof m.partial_season === "boolean" && (!p.limited_data || m.limited_data) && (!p.partial_season || m.partial_season), "attribute coverage warning mismatch");
    check(Array.isArray(m.exclusions), "explicit exclusions required"); const excluded = new Set();
    for (const e of m.exclusions) {
      keys(e, ["match_id", "reasons"]); unique(e.reasons);
      check(fixtures.has(e.match_id) && !excluded.has(e.match_id) && e.reasons.length, "excluded appearance evidence required"); excluded.add(e.match_id);
    }
    const n = m.normalization, group = p.comparison_position;
    keys(n, ["comparison_position", "reference_version", "reference_fingerprint", "pool_fingerprint"]);
    check(n.comparison_position === group && n.reference_version === ref.version && n.reference_fingerprint === ref.fingerprint, "normalization metadata mismatch");
    check(n.pool_fingerprint === (group ? ref.positions[group][a].fingerprint : null), "position pool fingerprint mismatch");
    const o = m.observation, press = a === "press_resistance";
    if (o === null) { check(m.rating === null && m.percentile === null && m.missingness.length, "absent measurement must stay N/A"); continue; }
    keys(o, ["value", "unit", "numerator", "denominator", "denominator_unit", "supported_minutes", "action_sample_size", "match_ids"]);
    check(number(o.value) && integer(o.numerator) && number(o.denominator) && o.denominator > 0, "supported numerator/denominator required");
    check(o.unit === (press ? "percent" : "per90") && o.denominator_unit === (press ? "actions" : "minutes"), "metric units mismatch");
    unique(o.match_ids, synthetic);
    check(o.match_ids.length && o.match_ids.every((id) => fixtures.has(id) && (press || !excluded.has(id))), "unsupported measurement fixture scope");
    if (o.supported_minutes !== null) presentationMinutes(o.supported_minutes);
    if (press) {
      check(integer(o.action_sample_size) && o.action_sample_size === o.denominator && o.numerator <= o.denominator, "press sample mismatch");
      check(o.denominator >= 40 || m.limited_data, "sub-40 press requires LIMITED DATA");
    } else check(o.action_sample_size === null && o.supported_minutes !== null && near(presentationMinutes(o.supported_minutes), o.denominator), "aligned supported minutes required");
    check(near(o.value, o.numerator / o.denominator * (press ? 100 : 90)), "measurement arithmetic mismatch");
    if (m.rating !== null) {
      check(group !== null && m.percentile !== null, "numeric score needs comparison position and percentile");
      const pool = ref.positions[group][a];
      check(near(m.rating, Math.max(1, Math.min(99, 65 + 10 * (o.value - pool.mean) / pool.sample_sd))), "synthetic rating/reference mismatch");
    } else check(m.percentile === null && m.missingness.length, "withheld score needs an explicit reason");
  }
}

export async function parseFiveAttributeDelivery(value) {
  const d = typeof value === "string" ? parseRatingJson(value) : structuredClone(value);
  keys(d, ["schema_version", "classification", "notice", "publication_authorized", "numeric_real_delivery_enabled", "reference", "players"]);
  check(d.schema_version === FIVE_SCHEMA && d.classification === "synthetic" && d.notice === FIVE_NOTICE && d.publication_authorized === false && d.numeric_real_delivery_enabled === false, "synthetic-only boundary; real numeric delivery disabled");
  await validateReference(d.reference);
  check(Array.isArray(d.players), "player array required"); const seen = new Set();
  for (const p of d.players) { validateFiveAttributeCard(p, d.reference); check(!seen.has(p.id), "duplicate canonical player-season"); seen.add(p.id); }
  return d;
}
export function fiveAttributePlayers(validated) {
  return validated.players.map((presentation) => ({ fiveAttributePresentation: true, id: presentation.id, name: presentation.name, presentation, reference: validated.reference }));
}
