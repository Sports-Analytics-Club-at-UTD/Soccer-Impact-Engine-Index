import { parseRatingJson } from "./ratingDelivery.js";

export const PROVISIONAL_SCHEMA = "soccer-provisional-observations/v1";
export const DEFINITIONS = "statsbomb-successful-defense-press-pass-dribble/v1";
const attributes = ["tackles", "interceptions", "recoveries", "press_resistance", "line_breaking_passes"];
const leagues = ["La Liga", "Premier League", "Serie A", "Ligue 1", "1. Bundesliga"];
const check = (okay, message) => { if (!okay) throw Error(`Invalid provisional observations: ${message}`); };
const object = (v) => v && typeof v === "object" && !Array.isArray(v);
const keys = (v, names) => check(object(v) && Object.keys(v).length === names.length && names.every((k) => Object.hasOwn(v, k)), "unexpected or missing fields");
const finite = (v) => typeof v === "number" && Number.isFinite(v) && v >= 0;
const integer = (v) => Number.isSafeInteger(v) && v >= 0;
const text = (v) => typeof v === "string" && !!v.trim();
const id = (v) => typeof v === "string" && /^[1-9]\d*$/.test(v) && BigInt(v) <= 9223372036854775807n;
function ids(v) { check(Array.isArray(v) && v.every(id) && new Set(v).size === v.length && v.every((x, i) => !i || BigInt(v[i - 1]) < BigInt(x)), "unique sorted fixture IDs required"); }
const subset = (a, b) => a.every((v) => b.has(v));
const near = (a, b) => finite(a) && Math.abs(a - b) <= 1e-10 * Math.max(1, Math.abs(b));
export function minutes(v) {
  keys(v, ["numerator", "denominator"]);
  check(integer(v.numerator) && integer(v.denominator) && v.denominator > 0, "exact supported minutes required");
  return v.numerator / v.denominator;
}
export function supportedRole(groups) {
  check(object(groups) && Object.keys(groups).every((g) => ["GK", "CB", "DM", "CM", "FB", "WM", "AM", "ATT", "UNKNOWN"].includes(g)), "position groups required");
  const rows = Object.entries(groups).map(([g, v]) => [g, minutes(v)]), top = Math.max(0, ...rows.map((r) => r[1]));
  const best = rows.filter((r) => r[1] === top && top > 0);
  return best.length !== 1 ? null : ["DM", "CM"].includes(best[0][0]) ? "MID" : best[0][0] === "CB" ? "CB" : null;
}

export function validateProvisionalCard(p, sourceIds) {
  keys(p, ["id", "player_id", "name", "season_name", "contexts", "comparison_group", "position_minutes", "observed_positions", "bundesliga_candidate", "observed_exposure_complete", "supported_minutes", "excluded_match_ids", "reference_member", "limited_data", "partial_season", "provenance_ids", "attributes", "bundesliga_sample"]);
  check(id(p.player_id) && p.id === `${p.player_id}:2015/2016` && p.season_name === "2015/2016" && text(p.name), "canonical player-season identity required");
  check(p.limited_data === true && p.partial_season === true && p.reference_member === false, "limited-data reference exclusion required");
  check(typeof p.bundesliga_candidate === "boolean" && typeof p.observed_exposure_complete === "boolean", "exposure flags required");
  check(supportedRole(p.position_minutes) === p.comparison_group, "dominant supported season group mismatch");
  check(near(minutes(p.supported_minutes), Object.values(p.position_minutes).reduce((s, v) => s + minutes(v), 0)), "position/exposure sum mismatch");
  check(Array.isArray(p.observed_positions) && p.observed_positions.every(text), "observed positions required");
  ids(p.excluded_match_ids);
  check(p.observed_exposure_complete === !p.excluded_match_ids.length, "excluded exposure flag mismatch");
  check(Array.isArray(p.provenance_ids) && p.provenance_ids.length && new Set(p.provenance_ids).size === p.provenance_ids.length && subset(p.provenance_ids, sourceIds), "bound provenance required");
  check(Array.isArray(p.contexts) && p.contexts.length, "contexts required");
  const seen = new Set(), contexts = new Set(); let bundes = false;
  for (const c of p.contexts) {
    keys(c, ["team", "competition_name", "match_ids"]);
    check(text(c.team) && leagues.includes(c.competition_name), "invalid contribution context"); ids(c.match_ids);
    check(c.match_ids.length && c.match_ids.every((m) => !seen.has(m)), "overlapping transfer fixture scope");
    const key = JSON.stringify([c.team, c.competition_name]); check(!contexts.has(key), "duplicate club context"); contexts.add(key);
    c.match_ids.forEach((m) => seen.add(m)); bundes ||= c.competition_name === "1. Bundesliga";
  }
  check(bundes && subset(p.excluded_match_ids, seen), "Bundesliga / excluded fixture mismatch");
  const b = p.bundesliga_sample;
  keys(b, ["comparison_group", "position_minutes", "supported_minutes", "match_ids", "excluded_match_ids", "press_attempts", "press_successes"]);
  check(supportedRole(b.position_minutes) === b.comparison_group && p.bundesliga_candidate === ["MID", "CB"].includes(b.comparison_group), "Bundesliga candidate group mismatch");
  check(near(minutes(b.supported_minutes), Object.values(b.position_minutes).reduce((s, v) => s + minutes(v), 0)) && minutes(b.supported_minutes) <= minutes(p.supported_minutes) + 1e-10, "Bundesliga exposure mismatch");
  ids(b.match_ids); ids(b.excluded_match_ids);
  const bundesIds = new Set(p.contexts.filter((c) => c.competition_name === "1. Bundesliga").flatMap((c) => c.match_ids));
  const bundesExcluded = new Set(p.excluded_match_ids.filter((m) => bundesIds.has(m)));
  check(b.match_ids.length === bundesIds.size && subset(b.match_ids, bundesIds) && b.excluded_match_ids.length === bundesExcluded.size && subset(b.excluded_match_ids, bundesExcluded), "Bundesliga fixture sample mismatch");
  check((b.press_attempts === null && b.press_successes === null) || (integer(b.press_attempts) && integer(b.press_successes) && b.press_successes <= b.press_attempts), "Bundesliga action counts required");
  keys(p.attributes, attributes);
  for (const [name, a] of Object.entries(p.attributes)) {
    keys(a, ["rating", "percentile", "observation", "reason"]);
    check(a.rating === null && a.percentile === null, "numeric ratings and percentiles are forbidden");
    check(typeof a.reason === "string", "availability reason required");
    const o = a.observation;
    if (o === null) { check(text(a.reason), "N/A reason required"); continue; }
    check(name !== "line_breaking_passes", "official line breaking remains N/A");
    let expected;
    if (name === "press_resistance") {
      keys(o, ["value", "unit", "attempts", "successes", "pass_attempts", "pass_successes", "dribble_attempts", "dribble_successes", "match_ids", "at_least_40"]);
      check(["attempts", "successes", "pass_attempts", "pass_successes", "dribble_attempts", "dribble_successes"].every((k) => integer(o[k])), "integer action counts required");
      check(o.attempts > 0 && o.successes <= o.attempts && o.pass_successes <= o.pass_attempts && o.dribble_successes <= o.dribble_attempts && o.attempts === o.pass_attempts + o.dribble_attempts && o.successes === o.pass_successes + o.dribble_successes, "press counts disagree");
      check(o.unit === "percent" && typeof o.at_least_40 === "boolean" && o.at_least_40 === (o.attempts >= 40), "press sample rule mismatch");
      check(Array.isArray(o.match_ids) && o.match_ids.length === seen.size && subset(o.match_ids, seen), "press numerator/denominator scope mismatch");
      expected = 100 * o.successes / o.attempts;
    } else {
      keys(o, ["value", "unit", "count", "minutes", "match_ids"]);
      check(integer(o.count) && minutes(o.minutes) > 0, "supported defensive exposure required");
      check(Array.isArray(o.match_ids) && o.match_ids.length && !o.match_ids.some((m) => p.excluded_match_ids.includes(m)), "unsupported defensive fixture admitted");
      check(minutes(o.minutes) <= minutes(p.supported_minutes) + 1e-10 && o.unit === "per90", "defensive denominator mismatch");
      expected = o.count * 90 / minutes(o.minutes);
    }
    ids(o.match_ids); check(subset(o.match_ids, seen), "component fixture scope mismatch");
    check(near(o.value, expected), "observation arithmetic mismatch");
  }
  const combined = p.attributes.press_resistance.observation;
  if (b.press_attempts !== null && b.press_attempts > 0) check(combined !== null && b.press_attempts <= combined.attempts && b.press_successes <= combined.successes && b.press_attempts - b.press_successes <= combined.attempts - combined.successes, "Bundesliga actions exceed combined evidence");
  if (p.contexts.every((c) => c.competition_name === "1. Bundesliga")) check((combined === null && (b.press_attempts === null || b.press_attempts === 0)) || (combined !== null && b.press_attempts === combined.attempts && b.press_successes === combined.successes), "Bundesliga-only press scope mismatch");
  return p;
}

export function parseProvisionalDelivery(input) {
  const d = structuredClone(input);
  keys(d, ["schema_version", "definitions_id", "numeric_ratings_enabled", "publication_authorized", "baseline", "sources", "players"]);
  check(d.schema_version === PROVISIONAL_SCHEMA && d.definitions_id === DEFINITIONS && d.numeric_ratings_enabled === false && d.publication_authorized === false && d.baseline === null, "observation-only envelope required");
  check(Array.isArray(d.sources) && d.sources.length, "evidence sources required"); const sourceIds = new Set();
  for (const s of d.sources) {
    keys(s, ["id", "path", "sha256", "label"]);
    check(Object.values(s).every(text) && /^[a-f0-9]{64}$/.test(s.sha256) && !sourceIds.has(s.id), "source fingerprint required"); sourceIds.add(s.id);
  }
  check(Array.isArray(d.players), "player array required"); const seen = new Set();
  for (const p of d.players) { validateProvisionalCard(p, sourceIds); check(!seen.has(p.id), "duplicate canonical player-season card"); seen.add(p.id); }
  return d;
}

export function provisionalPlayers(input) {
  const d = parseProvisionalDelivery(input);
  return d.players.map((p) => ({ ...p, provisional: true, source_provenance: d.sources.filter((s) => p.provenance_ids.includes(s.id)) }));
}

export async function loadProvisionalPlayers({ url = "data/bundesliga-observations.json", fetchImpl = globalThis.fetch, signal } = {}) {
  const r = await fetchImpl(url, { signal });
  if (!r.ok) throw Error(`Observation data unavailable (${r.status})`);
  return provisionalPlayers(parseRatingJson(await r.text()));
}
