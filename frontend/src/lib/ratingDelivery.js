import { METRICS, classify } from "./archetypes.js";

export const RATING_SCHEMA = "soccer-rating-delivery/v1";
export const RATING_NOTICE = "SYNTHETIC / NOT PRODUCTION RATINGS";
const LEAGUES = ["La Liga", "Premier League", "Serie A", "Ligue 1"];
const SEASON = "2015/2016";
const SYNTHETIC = "SYNTHETIC_TEST_EVIDENCE";
const canonicalTeam = (s) => { text(s); if (["Marseille", "Caen"].includes(s)) fail("canonical team context required"); };
const GATES = ["delivered_table_eligible", "independent_source_supported", "season_exposure_verified", "metric_numerator_verified", "scoring_approved", "publication_authorized"];
const fail = (message) => { throw new Error(`Invalid rating delivery: ${message}`); };
const keys = (o, names) => {
  if (!o || typeof o !== "object" || Array.isArray(o) || Object.keys(o).length !== names.length || names.some((k) => !Object.hasOwn(o, k))) fail("unexpected or missing fields");
};
const text = (s) => { if (typeof s !== "string" || !s.trim()) fail("nonblank text required"); };
const id = (s) => { if (typeof s !== "string" || !/^[1-9]\d*$/.test(s) || BigInt(s) > 9223372036854775807n) fail("exact positive signed-int64 decimal ID required"); };
const strings = (a, nonempty = false, ids = false) => {
  if (!Array.isArray(a) || (nonempty && !a.length)) fail("array required");
  a.forEach(ids ? id : text);
  if (new Set(a).size !== a.length || (ids && a.some((v, i) => i && BigInt(a[i - 1]) >= BigInt(v)))) fail("duplicate or unordered values");
};
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const number = (n, low = 0, high = Infinity) => typeof n === "number" && Number.isFinite(n) && n >= low && n <= high;

/* JSON.parse discards duplicate keys. Scan the grammar first so text imports
   cannot silently replace an identity, evidence gate or rating. */
export function parseRatingJson(source) {
  if (typeof source !== "string") fail("JSON text required");
  JSON.parse(source); // Validate the complete JSON grammar before scanning.
  const tokens = source.match(/"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"|[{}\[\],:]|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null/g) || [];
  let i = 0;
  function value() {
    const t = tokens[i++];
    if (t === "{") {
      const seen = new Set();
      while (tokens[i] !== "}") {
        const k = JSON.parse(tokens[i++]);
        if (seen.has(k)) fail("duplicate JSON key");
        seen.add(k); i++; value();
        if (tokens[i] !== ",") break;
        i++;
      }
      i++;
    } else if (t === "[") {
      while (tokens[i] !== "]") { value(); if (tokens[i] !== ",") break; i++; }
      i++;
    }
  }
  value();
  return JSON.parse(source);
}

export function parseRatingDelivery(payload) {
  const d = structuredClone(payload);
  keys(d, ["schema_version", "notice", "publication_authorized", "production_ready", "scope", "players"]);
  if (d.schema_version !== RATING_SCHEMA || d.notice !== RATING_NOTICE || d.publication_authorized !== false || d.production_ready !== false) fail("nonpublication v1 envelope required");
  keys(d.scope, ["season_name", "competitions", "role_groups", "cohort_id"]);
  if (d.scope.season_name !== SEASON || !equal(d.scope.competitions, LEAGUES) || !equal(d.scope.role_groups, ["MID", "CB"])) fail("comparison scope mismatch");
  text(d.scope.cohort_id);
  if (!Array.isArray(d.players)) fail("player array required");
  const seen = new Set();
  for (const p of d.players) {
    keys(p, ["player_id", "name", "team", "competition_name", "season_name", "role_group", "classification", "minutes", "provenance", "contexts", "eligibility", "cohort_id", "attributes", "archetype", "overall"]);
    id(p.player_id);
    [p.name, p.team, p.competition_name, p.season_name, p.cohort_id].forEach(text);
    canonicalTeam(p.team);
    const key = JSON.stringify([p.player_id, p.team, p.competition_name, p.season_name]);
    if (seen.has(key)) fail("duplicate canonical context");
    seen.add(key);
    if (p.season_name !== SEASON || !LEAGUES.includes(p.competition_name) || !["MID", "CB", null].includes(p.role_group) || p.cohort_id !== d.scope.cohort_id) fail("player scope mismatch");
    if (!["synthetic", "diagnostic", "verified"].includes(p.classification) || (p.minutes !== null && !number(p.minutes))) fail("invalid classification or minutes");
    strings(p.provenance, true);
    if (!Array.isArray(p.contexts) || !p.contexts.length) fail("source contexts required");
    const contextKeys = new Set(), matchIds = new Set();
    for (const c of p.contexts) {
      keys(c, ["team", "competition_name", "season_name", "match_ids", "source", "full_season", "evidence_kind"]);
      text(c.team); text(c.source); strings(c.match_ids, false, true);
      canonicalTeam(c.team);
      if (c.season_name !== SEASON || !LEAGUES.includes(c.competition_name)) fail("contribution scope mismatch");
      const expectedKind = { synthetic: SYNTHETIC, diagnostic: "UNVERIFIED", verified: "VERIFIED_SOURCE_EVIDENCE" }[p.classification];
      if (typeof c.full_season !== "boolean" || c.evidence_kind !== expectedKind) fail("context evidence classification mismatch");
      for (const mid of c.match_ids) { if (matchIds.has(mid)) fail("duplicate transfer match"); matchIds.add(mid); }
      const ck = JSON.stringify([c.team, c.competition_name, c.season_name]);
      if (contextKeys.has(ck)) fail("duplicate contribution context");
      contextKeys.add(ck);
    }
    if (!contextKeys.has(JSON.stringify([p.team, p.competition_name, p.season_name]))) fail("nominated context missing from lineage");
    const e = p.eligibility;
    keys(e, [...GATES, "synthetic_supported", "valid_sample_appearance_ids", "contradictory_sample_appearance_ids", "reasons"]);
    if ([...GATES, "synthetic_supported"].some((g) => typeof e[g] !== "boolean") || e.scoring_approved || e.publication_authorized) fail("separate nonpublication evidence gates required");
    strings(e.valid_sample_appearance_ids, false, true); strings(e.contradictory_sample_appearance_ids, false, true); strings(e.reasons);
    if (e.valid_sample_appearance_ids.some((v) => e.contradictory_sample_appearance_ids.includes(v))) fail("contradictory appearance status");
    const synthetic = p.classification === "synthetic";
    if (synthetic ? GATES.slice(1).some((g) => e[g]) : e.synthetic_supported) fail("classification cannot promote evidence");
    if (p.classification === "verified" && (!GATES.slice(1, 4).every((g) => e[g]) || e.reasons.length || e.contradictory_sample_appearance_ids.length || p.contexts.some((c) => !c.full_season || !c.match_ids.length))) fail("verified classification contradicts evidence gates");
    keys(p.attributes, METRICS.map((m) => m.id));
    for (const [aid, a] of Object.entries(p.attributes)) {
      keys(a, ["rating", "percentile", "status", "reasons", "policy", "comparison_pool"]);
      strings(a.reasons);
      if (a.policy !== null) {
        keys(a.policy, ["policy_id", "source", "formula", "min_minutes", "min_actions", "status"]);
        [a.policy.policy_id, a.policy.source, a.policy.formula].forEach(text);
        if (a.policy.status !== "candidate" || [a.policy.min_minutes, a.policy.min_actions].some((v) => v !== null && !number(v))) fail("candidate policy required");
      }
      if (a.status === "withheld") {
        if (a.rating !== null || a.percentile !== null || !a.reasons.length) fail("withheld values require nulls and reasons");
      } else if (a.status === "synthetic_candidate") {
        if (!synthetic || !e.synthetic_supported || e.reasons.length || e.contradictory_sample_appearance_ids.length || a.reasons.length || !a.policy || !p.role_group || p.contexts.some((c) => !c.match_ids.length || !c.full_season) || !number(a.rating, 1, 100) || !number(a.percentile, 0, 100) || aid === "line_breaking_passes") fail("invalid synthetic candidate");
      } else fail("unsupported attribute status");
      if (a.comparison_pool !== (p.role_group ? `${p.cohort_id}:${p.role_group}` : null)) fail("attribute pool mismatch");
    }
    keys(p.archetype, ["attribute_id", "tier"]);
    const chosen = classify({ position: p.role_group === "MID" ? "DM" : p.role_group, attributes: p.attributes });
    const expectedId = METRICS.find((m) => m.key === chosen.metric)?.id ?? null;
    const expectedTier = chosen.tier === "+" ? "Gold" : chosen.tier === "−" ? "Silver" : null;
    if (p.archetype.attribute_id !== expectedId || p.archetype.tier !== expectedTier) fail("archetype must follow percentile");
    keys(p.overall, ["rating", "status", "reasons"]);
    if (p.overall.rating !== null || p.overall.status !== "withheld" || !equal(p.overall.reasons, ["policy_not_finalized"])) fail("OVR policy pending");
  }
  return d;
}

export function ratingPlayers(delivery) {
  return parseRatingDelivery(delivery).players.map((p) => ({ ...p,
    id: JSON.stringify([p.player_id, p.team, p.competition_name, p.season_name]),
    position: p.role_group === "MID" ? "DM" : p.role_group,
    ratingNotice: p.classification === "synthetic" ? RATING_NOTICE : "DIAGNOSTIC / RATINGS WITHHELD",
  }));
}

export async function readRatingFile(file) {
  if (!file || typeof file.text !== "function" || file.size > 5 * 1024 * 1024) fail("local JSON file up to 5 MiB required");
  return ratingPlayers(parseRatingJson(await file.text()));
}
