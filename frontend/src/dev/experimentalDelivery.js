// This module is reachable only through import.meta.env.DEV in App.jsx.
import { FIVE_METRICS, presentationMinutes } from "../lib/fiveAttributePresentation.js";
import { parseRatingJson } from "../lib/ratingDelivery.js";
import { playerDataStatus } from "../lib/playerDataStatus.js";
import { validateOvrIntegration } from "./provisionalOvr.js";
import { experimentalComponentClassification } from "./componentClassification.js";
export const EXPERIMENTAL_NOTICE = "EXPERIMENTAL PROJECT RATINGS";
export const EA_DISCLAIMER = "NOT OFFICIAL EA FIFA RATINGS";
export const LOCAL_ENDPOINT = "/__local_experimental/five-attributes";
const REFERENCE = "403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd";
const PROJECTION = "af27f0053582b76c26c12e26aa4de55e56bc0b0eafe0cae9cc1fc47c5ad6b663";
const MANIFEST = "5a8030b4a6ca06aeec81538221b07315c5644a9025915eb31c0bf2dab3cc9bc6";
export const EXPERIMENTAL_LEAGUES = ["Premier League", "La Liga", "Serie A", "Ligue 1", "1. Bundesliga"];
const check = (v, message) => { if (!v) throw Error(`Invalid local experimental ratings: ${message}`); };
const object = (v) => v && typeof v === "object" && !Array.isArray(v);
const keys = (v, names) => check(object(v) && Object.keys(v).length === names.length && names.every((k) => Object.hasOwn(v, k)), "unexpected or missing fields");
const text = (v) => typeof v === "string" && !!v.trim();
const numeric = (v, lo = 0, hi = Infinity) => typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi;
const integer = (v) => Number.isSafeInteger(v) && v >= 0;
const fp = (v) => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const id = (v) => typeof v === "string" && /^[1-9]\d*$/.test(v) && BigInt(v) <= 9223372036854775807n;
const near = (a, b) => numeric(a) && Math.abs(a - b) <= 1e-10 * Math.max(1, Math.abs(b));
const unique = (vs, predicate = text) => check(Array.isArray(vs) && vs.every(predicate) && new Set(vs).size === vs.length, "unique evidence values required");
function canonical(v) {
  if (Array.isArray(v)) return v.map(canonical);
  return object(v) ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canonical(v[k])])) : v;
}
async function digest(v) {
  const value = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(canonical(v))));
  return [...new Uint8Array(value)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
const body = ({ fingerprint, ...rest }) => rest;

export function validateExperimentalPlayer(p, reference) {
  keys(p, ["id", "player_id", "name", "season_name", "comparison_position", "positions", "primary_position", "secondary_positions", "position_seconds", "known_supported_minutes", "clubs", "limited_data", "partial_season", "attributes", "provenance"]);
  check(id(p.player_id) && p.id === `${p.player_id}:2015/2016` && p.season_name === "2015/2016" && text(p.name) && !p.name.startsWith("SYNTHETIC "), "canonical real player-season required");
  check(["MID", "CB"].includes(p.comparison_position), "MID/CB comparison required");
  unique(p.positions); unique(p.secondary_positions);
  check(text(p.primary_position) && object(p.position_seconds) && Object.keys(p.position_seconds).length === p.positions.length && p.positions.every((pos) => Object.hasOwn(p.position_seconds, pos)), "verified position evidence required");
  for (const duration of Object.values(p.position_seconds)) presentationMinutes(duration);
  presentationMinutes(p.known_supported_minutes);
  check(typeof p.limited_data === "boolean" && typeof p.partial_season === "boolean", "explicit coverage status required");
  check(Array.isArray(p.clubs) && p.clubs.length, "club contexts required");
  const fixtures = new Set(), contexts = new Set(); let bundes = false;
  for (const c of p.clubs) {
    keys(c, ["name", "competition_name", "match_ids"]); unique(c.match_ids, id);
    const ck = JSON.stringify([c.name, c.competition_name]);
    check(text(c.name) && !c.name.startsWith("SYNTHETIC ") && EXPERIMENTAL_LEAGUES.includes(c.competition_name) && c.match_ids.length && !contexts.has(ck) && c.match_ids.every((mid) => !fixtures.has(mid)), "transfer identity or fixture overlap");
    c.match_ids.forEach((mid) => fixtures.add(mid)); contexts.add(ck); bundes ||= c.competition_name === "1. Bundesliga";
  }
  check(p.limited_data === bundes && (!bundes || p.partial_season), "Bundesliga limited/partial coverage missing");
  check(Array.isArray(p.provenance) && p.provenance.length, "source provenance required"); const sources = new Set();
  for (const s of p.provenance) {
    keys(s, ["id", "label", "source", "fingerprint"]);
    check(text(s.id) && text(s.label) && text(s.source) && fp(s.fingerprint) && !sources.has(s.id), "invalid source binding"); sources.add(s.id);
  }
  keys(p.attributes, FIVE_METRICS.map((m) => m.id));
  for (const { id: a, label } of FIVE_METRICS) {
    const m = p.attributes[a];
    keys(m, ["label", "measurement_kind", "rating", "percentile", "observation", "normalization", "missingness", "exclusions", "limited_data", "partial_season", "provenance_ids", "warnings", "sample_details", "score_status"]);
    check(m.label === label && m.measurement_kind === (a === "line_breaking_passes" ? "progressive_passing_proxy" : "observed_metric"), "metric/proxy definition mismatch");
    check(m.rating === null || numeric(m.rating, 1, 99), "score outside 1..99");
    check(m.percentile === null || numeric(m.percentile, 0, 100), "percentile outside 0..100");
    unique(m.missingness); unique(m.warnings); unique(m.provenance_ids);
    check(m.provenance_ids.length && m.provenance_ids.every((s) => sources.has(s)), "unbound attribute provenance");
    check(typeof m.limited_data === "boolean" && typeof m.partial_season === "boolean" && (!p.limited_data || m.limited_data) && (!p.partial_season || m.partial_season), "attribute coverage warnings lost");
    check(Array.isArray(m.exclusions), "excluded appearances required"); const excluded = new Set();
    for (const e of m.exclusions) {
      keys(e, ["match_id", "reasons"]); unique(e.reasons);
      check(fixtures.has(e.match_id) && !excluded.has(e.match_id) && e.reasons.length, "excluded appearance outside source scope"); excluded.add(e.match_id);
    }
    const n = m.normalization; keys(n, ["comparison_position", "reference_version", "reference_fingerprint", "pool_fingerprint"]);
    check(n.comparison_position === p.comparison_position && n.reference_version === reference.version && n.reference_fingerprint === REFERENCE && n.pool_fingerprint === reference.positions[p.comparison_position][a].fingerprint, "position-specific frozen reference mismatch");
    const sample = m.sample_details; keys(sample, ["raw_counts", "action_sample_size", "measured_pass_sample"]);
    check(sample.action_sample_size === null || integer(sample.action_sample_size), "invalid action sample");
    check(sample.measured_pass_sample === null || integer(sample.measured_pass_sample), "invalid measured pass sample");
    if (sample.raw_counts !== null) check(object(sample.raw_counts) && Object.values(sample.raw_counts).every(integer), "invalid raw counts");
    const o = m.observation, press = a === "press_resistance";
    if (o === null) { check(m.rating === null && m.percentile === null && m.missingness.length, "missing measurement must stay N/A"); continue; }
    keys(o, ["value", "unit", "numerator", "denominator", "denominator_unit", "supported_minutes", "action_sample_size", "match_ids", "exact_value"]);
    check(numeric(o.value) && integer(o.numerator) && numeric(o.denominator) && o.denominator > 0 && o.unit === (press ? "percent" : "per90") && o.denominator_unit === (press ? "actions" : "minutes"), "invalid measured input/units");
    unique(o.match_ids, id);
    check(o.match_ids.length && o.match_ids.every((mid) => fixtures.has(mid) && !excluded.has(mid)), "unaligned measurement fixture scope");
    check(near(presentationMinutes(o.exact_value), o.value) && near(o.value, o.numerator / o.denominator * (press ? 100 : 90)), "exact measured statistic mismatch");
    const duration = presentationMinutes(o.supported_minutes);
    if (press) {
      check(integer(o.action_sample_size) && o.action_sample_size === o.denominator && o.numerator <= o.denominator && sample.action_sample_size === o.denominator, "press attempts/successes mismatch");
      check(o.denominator >= 40 || m.limited_data, "sub-40 press warning missing");
    } else check(duration > 0 && near(duration, o.denominator) && o.action_sample_size === null, "unsupported per90 exposure");
    if (m.rating === null) check(m.percentile === null && m.missingness.length && m.score_status === "N/A", "withheld score reason missing");
    else check(m.percentile !== null && ["PRIVATE_EXPERIMENTAL", "PROVISIONAL_LIMITED_DATA"].includes(m.score_status), "missing experimental score status");
  }
  check(FIVE_METRICS.some((m) => p.attributes[m.id].rating !== null), "no supported experimental scores");
}

export async function parseExperimentalDelivery(value) {
  const d = typeof value === "string" ? parseRatingJson(value) : structuredClone(value);
  const integration = d.ovr_integration;
  delete d.ovr_integration;
  keys(d, ["schema_version", "classification", "notice", "disclaimer", "local_only", "production_ready", "publication_authorized", "reference", "source_package", "counts", "players"]);
  check(d.schema_version === "soccer-local-experimental-five-attributes/v1" && d.classification === "local_experimental" && d.notice === EXPERIMENTAL_NOTICE && d.disclaimer === EA_DISCLAIMER && d.local_only === true && d.production_ready === false && d.publication_authorized === false, "local experimental boundary required");
  keys(d.source_package, ["version", "manifest_sha256", "scores_sha256", "measurements_sha256"]);
  check(d.source_package.manifest_sha256 === MANIFEST && fp(d.source_package.scores_sha256) && fp(d.source_package.measurements_sha256), "frozen source package fingerprint mismatch");
  const ref = d.reference; keys(ref, ["version", "fingerprint", "positions", "projection_fingerprint"]);
  check(ref.version === "private-five-attribute-player-season/v2" && ref.fingerprint === REFERENCE && ref.projection_fingerprint === PROJECTION && d.source_package.version === ref.version, "frozen reference fingerprint mismatch");
  const { projection_fingerprint, ...projection } = ref;
  check(await digest(projection) === projection_fingerprint, "frozen reference projection changed");
  keys(ref.positions, ["MID", "CB"]);
  for (const [group, pools] of Object.entries(ref.positions)) {
    keys(pools, FIVE_METRICS.map((m) => m.id));
    for (const [a, p] of Object.entries(pools)) {
      keys(p, ["population_version", "comparison_position", "metric_id", "n", "mean", "sample_sd", "member_fingerprint", "source_reference_fingerprint", "fingerprint"]);
      check(p.population_version === ref.version && p.comparison_position === group && p.metric_id === a && p.source_reference_fingerprint === REFERENCE && integer(p.n) && p.n >= 2 && numeric(p.mean) && numeric(p.sample_sd) && p.sample_sd > 0 && fp(p.member_fingerprint), "invalid frozen group population");
      check(p.fingerprint === await digest(body(p)), "position pool fingerprint mismatch");
    }
  }
  check(Array.isArray(d.players), "player array required"); const seen = new Set();
  for (const p of d.players) { validateExperimentalPlayer(p, ref); check(!seen.has(p.id), "duplicate player-season"); seen.add(p.id); }
  keys(d.counts, ["examined", "available", "complete", "partial", "bundesliga_complete", "bundesliga_partial"]);
  const complete = d.players.filter((p) => FIVE_METRICS.every((m) => p.attributes[m.id].rating !== null)).length;
  check(d.players.length === d.counts.available && d.counts.available === 691 && complete === d.counts.complete && complete === 686 && d.counts.partial === 5 && d.counts.examined === 2514, "complete/partial coverage mismatch");
  check(d.players.filter((p) => p.limited_data && FIVE_METRICS.every((m) => p.attributes[m.id].rating !== null)).length === d.counts.bundesliga_complete && d.counts.bundesliga_complete === 133 && d.players.filter((p) => p.limited_data && FIVE_METRICS.some((m) => p.attributes[m.id].rating === null)).length === 5 && d.counts.bundesliga_partial === 5, "Bundesliga provisional coverage mismatch");
  if (integration !== undefined) {
    validateOvrIntegration(integration, d);
    d.ovr_integration = integration;
  }
  return d;
}

export const experimentalModels = (validated) => validated.players.map((presentation) => ({ id: presentation.id, name: presentation.name, presentation, reference: validated.reference,
  componentClassification: experimentalComponentClassification({ presentation, ovr: validated.ovr_integration?.players[presentation.id] }),
  ...(validated.ovr_integration ? { ovr: { ...validated.ovr_integration.players[presentation.id], version: validated.ovr_integration.version, eligibility_version: validated.ovr_integration.eligibility_version, source_package: validated.ovr_integration.source_package } } : {}) }));
export async function loadExperimentalRatings({ fetcher = fetch, signal } = {}) {
  const response = await fetcher(LOCAL_ENDPOINT, { cache: "no-store", credentials: "same-origin", signal });
  if (!response.ok) throw Error(`Local experimental adapter failed (${response.status}); no fallback was loaded`);
  if (!response.headers.get("content-type")?.includes("application/json")) throw Error("Local development endpoint unavailable; production/static previews do not serve experimental ratings");
  return parseExperimentalDelivery(await response.text());
}

export { filterExperimentalPlayers } from "../lib/playerDiscovery.js";
