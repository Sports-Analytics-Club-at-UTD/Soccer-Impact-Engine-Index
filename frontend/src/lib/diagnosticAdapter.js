/* Diagnostic-only D2C contract. No demo data, ratings or production-schema coercion. */
export const SCHEMA_VERSION = "soccer-provisional-profiles/v1";
export const VERIFICATION_STATUS = "DIAGNOSTIC / PROVISIONAL / NOT PRODUCTION VERIFIED";
export const CANONICAL_KEYS = ["player_id", "team", "competition_name", "season_name"];
export const RECOVERY_TYPES = ["Tackle", "Interception", "Ball Recovery"];
export const PRESS_COUNTS = ["pressured_pass_attempts", "pressured_pass_completed", "pressured_dribble_attempts",
  "pressured_dribble_completed", "pressured_actions", "successful_pressured_actions"];
export const PRESS_RATES = ["pressured_pass_completion_rate", "pressured_dribble_completion_rate", "press_resistance_rate"];
const UNITS = { counts: "events", percentages: "percent_0_100", aligned_minutes: "minutes", per90: "events/90min", zones: "existing_3x3_120x80" };
const IDENTITY_PROVENANCE = "D1B-P caller-supplied provisional lookup; contributor-reported lineup/crosswalk lineage";
const CONTEXT_PROVENANCE = "event-derived; not an independent authoritative fixture manifest";
const COVERAGE = "supplied D2B match window; all-local-rows attestation is not authoritative completeness";
const MINUTES_SCOPE = "wider player/team/competition/season; never a denominator here";
const REASONS = new Set(["actor_without_position_stint", "duplicate_stints", "cross_period_duration_unverified",
  "invalid_position_or_nonpositive_interval", "clock_period_disagreement", "missing_or_invalid_interval_or_period",
  "initial_stint_not_entry", "starting_xi_clock_mismatch", "terminal_stint_not_exit", "multiple_period_timing_unverified",
  "overlapping_stints", "gapped_stints", "actor_event_outside_stints", "no_measurable_interval",
  "local_match_collection_not_established", "no_matching_lineup_exposure", "missing_metric",
  "nonpositive_or_unavailable_aligned_minutes"]);
const fail = (message) => { throw new Error(`Invalid diagnostic profile: ${message}`); };
const equal = (a, b) => {
  if (a === b) return true;
  if (!a || !b || typeof a !== "object" || typeof b !== "object") return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const x = Object.keys(a), y = Object.keys(b);
  return x.length === y.length && x.every((k) => Object.hasOwn(b, k) && equal(a[k], b[k]));
};
const teamAlias = (s) => s === "Marseille" ? "Olympique de Marseille" : s === "Caen" ? "Stade Malherbe Caen" : s;
const keys = (o, list, label) => {
  if (!o || typeof o !== "object" || Array.isArray(o) || !equal(Object.keys(o).sort(), [...list].sort())) fail(`${label}: unexpected/missing fields`);
};
const text = (s, label) => { if (typeof s !== "string" || !s.trim()) fail(`${label}: nonblank text required`); };
const numeric = (n, label, nullable = false) => {
  if (nullable && n === null) return;
  if (typeof n !== "number" || !Number.isFinite(n) || n < 0) fail(`${label}: finite nonnegative number required`);
};
const integer = (s, positive = false) => {
  if (typeof s !== "string" || !/^(0|[1-9]\d*)$/.test(s) || BigInt(s) > 9223372036854775807n || (positive && s === "0")) fail("exact decimal-string signed-int64 identity/count required");
  return BigInt(s);
};
const compareId = (a, b) => BigInt(a) < BigInt(b) ? -1 : BigInt(a) > BigInt(b) ? 1 : 0;
const compareText = (a, b) => {
  const x = Array.from(a), y = Array.from(b);
  for (let i = 0; i < Math.min(x.length, y.length); i++) if (x[i] !== y[i]) return x[i].codePointAt(0) - y[i].codePointAt(0);
  return x.length - y.length;
};
const ids = (a, label) => {
  if (!Array.isArray(a)) fail(`${label}: match-ID array required`);
  a.forEach((s) => integer(s, true));
  if (new Set(a).size !== a.length || !equal([...a].sort(compareId), a)) fail(`${label}: duplicate or noncanonical match IDs`);
};
const subset = (a, b, label) => { if (a.some((s) => !b.includes(s))) fail(`${label}: incompatible match window`); };
const strings = (a, label) => {
  if (!Array.isArray(a) || new Set(a).size !== a.length) fail(`${label}: unique string array required`);
  a.forEach((s) => text(s, label));
};
const reasons = (a) => { strings(a, "reasons"); if (a.some((s) => !REASONS.has(s))) fail("unsupported withholding reason"); };
const close = (a, b, label) => { if (Math.abs(a - b) > 1e-9 * Math.max(1, Math.abs(b))) fail(`${label}: inconsistent arithmetic`); };
const safeLength = (n, a, label) => { if (!Number.isSafeInteger(n) || n !== a.length) fail(`${label}: count/window mismatch`); };

function exposure(e, scope, complete, pooled) {
  keys(e, ["match_ids", "match_records", "status", "aligned_minutes", "reasons", ...(pooled ?
    ["delivered_minutes", "delivered_minutes_status", "source_ambiguities", "delivered_minutes_scope"] : [])], "exposure");
  ids(e.match_ids, "exposure");
  if (!equal(e.match_ids, scope) || !Array.isArray(e.match_records)) fail("exposure window mismatch");
  const seen = [], union = new Set();
  let aligned = complete && e.match_records.length > 0, sum = 0;
  e.match_records.forEach((r) => {
    keys(r, ["match_id", "status", "aligned_minutes", "reasons"], "exposure record");
    integer(r.match_id, true); seen.push(r.match_id); reasons(r.reasons);
    r.reasons.forEach((s) => union.add(s));
    if (!["aligned_explicit_stints", "bench_no_stint", "withheld"].includes(r.status)) fail("unsupported exposure status");
    if (r.status === "withheld") {
      aligned = false;
      if (r.aligned_minutes !== null || !r.reasons.length) fail("withheld exposure needs null minutes and reasons");
    } else if (!complete) {
      if (r.status !== "bench_no_stint" || r.aligned_minutes !== null) fail("unaligned local collection cannot supply minutes");
    } else {
      numeric(r.aligned_minutes, "aligned minutes");
      if (r.reasons.length || (r.status === "bench_no_stint" ? r.aligned_minutes !== 0 : r.aligned_minutes <= 0)) fail("invalid aligned stint exposure");
      sum += r.aligned_minutes;
    }
  });
  if (!equal(seen, scope)) fail("exposure records do not cover the exact match window");
  if (!complete) union.add("local_match_collection_not_established");
  if (!scope.length) union.add("no_matching_lineup_exposure");
  reasons(e.reasons);
  if (!equal([...union].sort(), [...e.reasons].sort())) fail("aggregate exposure reasons disagree");
  if (e.status !== (aligned ? "aligned" : "unsupported")) fail("contradictory aggregate exposure");
  if (aligned) { numeric(e.aligned_minutes, "aggregate minutes"); close(e.aligned_minutes, sum, "aggregate minutes"); }
  else if (e.aligned_minutes !== null) fail("unsupported exposure cannot supply minutes");
  if (pooled) {
    if (e.delivered_minutes_scope !== MINUTES_SCOPE) fail("unsupported delivered-minute scope");
    numeric(e.delivered_minutes, "delivered minutes", true);
    if (!["known_wider_scope", "zero", "missing", "not_supplied"].includes(e.delivered_minutes_status)) fail("unsupported delivered-minute status");
    const status = e.delivered_minutes_status;
    if ((["missing", "not_supplied"].includes(status) && e.delivered_minutes !== null) ||
        (status === "zero" && e.delivered_minutes !== 0) ||
        (status === "known_wider_scope" && !(e.delivered_minutes > 0))) fail("delivered minutes/status disagree");
    if (!equal(e.source_ambiguities, status === "zero" ? ["observed_activity_with_zero_delivered_minutes"] : [])) fail("source ambiguity flags disagree");
  }
}

function recovery(block, scope, e) {
  keys(block, RECOVERY_TYPES, "recovery");
  RECOVERY_TYPES.forEach((category) => {
    const r = block[category];
    keys(r, ["status", "count", "match_ids", "zone_counts", "unknown_zone_count", "per90"], category);
    if (!equal(r.match_ids, scope)) fail("recovery numerator window mismatch");
    if (!["observed", "missing"].includes(r.status)) fail("unsupported recovery state");
    const present = r.status === "observed";
    if (!present) {
      if (r.count !== null || r.zone_counts !== null || r.unknown_zone_count !== null) fail("missing measurement has invented values");
    } else {
      const count = integer(r.count), seen = new Set();
      let total = integer(r.unknown_zone_count);
      if (!Array.isArray(r.zone_counts)) fail("zone array required");
      r.zone_counts.forEach((z) => {
        keys(z, ["zone", "count"], "zone");
        if (!Number.isInteger(z.zone) || z.zone < 1 || z.zone > 9 || seen.has(z.zone)) fail("invalid/duplicate zone");
        seen.add(z.zone); total += integer(z.count);
      });
      if (total !== count) fail("zone/count conservation failed");
    }
    const p = r.per90;
    keys(p, ["status", "available", "value", "reasons", "numerator_match_ids", "denominator_match_ids", "aligned_minutes"], "per90");
    if (!equal(p.numerator_match_ids, scope)) fail("per90 numerator scope mismatch");
    reasons(p.reasons);
    const available = present && e.status === "aligned" && e.aligned_minutes > 0;
    if (p.available !== available || p.status !== (available ? "available" : "unsupported")) fail("unsupported per90 availability claim");
    if (available) {
      numeric(p.value, "per90"); numeric(p.aligned_minutes, "per90 minutes");
      if (!equal(p.denominator_match_ids, scope) || p.reasons.length) fail("per90 denominator window mismatch");
      close(p.aligned_minutes, e.aligned_minutes, "per90 exposure");
      close(p.value, Number(integer(r.count)) / e.aligned_minutes * 90, "per90");
    } else {
      if (p.value !== null || p.denominator_match_ids !== null || p.aligned_minutes !== null) fail("withheld per90 has values");
      const expected = !present ? ["missing_metric"] : e.reasons.length ? e.reasons : ["nonpositive_or_unavailable_aligned_minutes"];
      if (!equal([...p.reasons].sort(), [...expected].sort())) fail("per90 withholding reasons disagree");
    }
  });
}

function press(p) {
  keys(p, ["status", "counts", "percentages"], "press");
  keys(p.counts, PRESS_COUNTS, "press counts"); keys(p.percentages, PRESS_RATES, "press percentages");
  if (!["observed", "missing"].includes(p.status)) fail("unsupported press status");
  if (p.status === "missing") {
    if (PRESS_COUNTS.some((k) => p.counts[k] !== null)) fail("missing press has invented counts");
  } else {
    PRESS_COUNTS.forEach((k) => integer(p.counts[k]));
    const c = p.counts, n = (k) => integer(c[k]);
    if (n("pressured_pass_completed") > n("pressured_pass_attempts") || n("pressured_dribble_completed") > n("pressured_dribble_attempts") ||
        n("pressured_actions") !== n("pressured_pass_attempts") + n("pressured_dribble_attempts") ||
        n("successful_pressured_actions") !== n("pressured_pass_completed") + n("pressured_dribble_completed")) fail("press count conservation failed");
  }
  PRESS_RATES.forEach((k, i) => {
    const r = p.percentages[k]; keys(r, ["status", "value"], "percentage");
    const numerator = p.counts[["pressured_pass_completed", "pressured_dribble_completed", "successful_pressured_actions"][i]];
    const denominator = p.counts[["pressured_pass_attempts", "pressured_dribble_attempts", "pressured_actions"][i]];
    const missing = p.status === "missing", zero = !missing && denominator === "0";
    if (r.status !== (missing ? "missing" : zero ? "undefined_zero_attempts" : "observed")) fail("percentage/attempt status mismatch");
    if (missing || zero) { if (r.value !== null) fail("undefined percentage must be null"); }
    else { numeric(r.value, "percentage"); if (r.value > 100) fail("percentage exceeds 100"); close(r.value, 100 * Number(integer(numerator)) / Number(integer(denominator)), "percentage"); }
  });
}

function measurements(v, scope, complete, pooled) {
  if (!equal(v.scope_match_ids, scope)) fail("measurement window mismatch");
  exposure(v.exposure, scope, complete, pooled); recovery(v.recovery, scope, v.exposure); press(v.press);
}

function conserve(p) {
  const pooled = p.pooled;
  RECOVERY_TYPES.forEach((k) => {
    const rows = p.matches.map((m) => m.recovery[k]).filter((r) => r.status === "observed"), target = pooled.recovery[k];
    if (target.status !== (rows.length ? "observed" : "missing")) fail("pooled recovery fabricates/loses observations");
    if (rows.length) {
      if (rows.reduce((s, r) => s + integer(r.count), 0n) !== integer(target.count) ||
          rows.reduce((s, r) => s + integer(r.unknown_zone_count), 0n) !== integer(target.unknown_zone_count)) fail("pooled recovery count mismatch");
      const zones = new Map();
      rows.forEach((r) => r.zone_counts.forEach((z) => zones.set(z.zone, (zones.get(z.zone) ?? 0n) + integer(z.count))));
      if (zones.size !== target.zone_counts.length || target.zone_counts.some((z) => zones.get(z.zone) !== integer(z.count))) fail("pooled zone mismatch");
    }
  });
  const rows = p.matches.filter((m) => m.press.status === "observed");
  if (pooled.press.status !== (rows.length ? "observed" : "missing")) fail("pooled press fabricates/loses observations");
  if (rows.length) PRESS_COUNTS.forEach((k) => {
    if (rows.reduce((s, m) => s + integer(m.press.counts[k]), 0n) !== integer(pooled.press.counts[k])) fail("pooled press counts mismatch");
  });
}

export function parseDiagnosticProfiles(payload) {
  keys(payload, ["schema_version", "verification_status", "production_schema_compatible", "integer_encoding", "units", "canonical_keys",
    "scope", "identity_provenance", "match_context_provenance", "profiles"], "payload");
  if (payload.schema_version !== SCHEMA_VERSION || payload.verification_status !== VERIFICATION_STATUS ||
      payload.production_schema_compatible !== false || payload.integer_encoding !== "decimal_string" ||
      !equal(payload.canonical_keys, CANONICAL_KEYS) || payload.identity_provenance !== IDENTITY_PROVENANCE ||
      payload.match_context_provenance !== CONTEXT_PROVENANCE) fail("unsupported schema/provenance");
  keys(payload.units, Object.keys(UNITS), "units");
  if (Object.keys(UNITS).some((k) => payload.units[k] !== UNITS[k])) fail("incompatible metric units");
  keys(payload.scope, ["match_ids", "local_collection_complete", "observed_match_count", "observed_event_count", "local_event_coverage", "authoritative_feed_complete"], "dataset scope");
  const window = payload.scope.match_ids, complete = payload.scope.local_collection_complete;
  ids(window, "dataset"); safeLength(payload.scope.observed_match_count, window, "dataset");
  integer(payload.scope.observed_event_count);
  if (typeof complete !== "boolean" || payload.scope.authoritative_feed_complete !== false || payload.scope.local_event_coverage !== COVERAGE) fail("unsupported coverage provenance");
  if (!Array.isArray(payload.profiles)) fail("profiles must be an array");
  const seen = new Set(); let eventSum = 0n;
  payload.profiles.forEach((p) => {
    keys(p, ["identity", "verification_status", "scope", "pooled", "matches", "not_assessed_metric_families"], "profile");
    if (p.verification_status !== VERIFICATION_STATUS || !equal(p.not_assessed_metric_families, ["progression"])) fail("unsupported profile provenance/assessment");
    keys(p.identity, [...CANONICAL_KEYS, "player_name", "observed_name_variants", "name_source"], "identity");
    integer(p.identity.player_id, true); CANONICAL_KEYS.slice(1).forEach((k) => text(p.identity[k], k));
    strings(p.identity.observed_name_variants, "names");
    if (!p.identity.observed_name_variants.length || p.identity.observed_name_variants.some((s) => s !== s.replaceAll("''", "'").trim()) ||
        !equal([...p.identity.observed_name_variants].sort(compareText), p.identity.observed_name_variants)) fail("noncanonical observed names");
    if (p.identity.name_source !== "observed_event_actor_label" || p.identity.player_name !==
        (p.identity.observed_name_variants.length === 1 ? p.identity.observed_name_variants[0] : null)) fail("unsupported name provenance");
    const context = CANONICAL_KEYS.map((k) => k === "team" ? teamAlias(p.identity[k]) : p.identity[k]);
    const key = JSON.stringify(context);
    if (seen.has(key)) fail("duplicate canonical identity"); seen.add(key);
    keys(p.scope, ["included_match_ids", "observed_match_ids", "observed_match_count", "observed_event_count"], "player scope");
    const included = p.scope.included_match_ids, observed = p.scope.observed_match_ids;
    ids(included, "included"); ids(observed, "observed"); subset(included, window, "included"); subset(observed, included, "observed");
    safeLength(p.scope.observed_match_count, observed, "player"); eventSum += integer(p.scope.observed_event_count, true);
    keys(p.pooled, ["scope_match_ids", "recovery", "press", "exposure"], "pooled");
    measurements(p.pooled, included, complete, true);
    if (!Array.isArray(p.matches) || !equal(p.matches.map((m) => m.match_id), observed)) fail("observed match membership mismatch");
    let count = 0n;
    p.matches.forEach((m) => {
      keys(m, ["match_id", "scope_match_ids", "observed_event_count", "recovery", "press", "exposure"], "match");
      measurements(m, [m.match_id], complete, false);
      const n = integer(m.observed_event_count, true); count += n;
      if (m.exposure.match_records.some((r) => r.status === "bench_no_stint")) fail("actor events cannot have bench-only exposure");
      const record = p.pooled.exposure.match_records.find((r) => r.match_id === m.match_id);
      if (!equal(record, m.exposure.match_records[0])) fail("pooled/match exposure disagreement");
      const actions = RECOVERY_TYPES.reduce((s, k) => s + (m.recovery[k].status === "observed" ? integer(m.recovery[k].count) : 0n), 0n)
        + (m.press.status === "observed" ? integer(m.press.counts.pressured_actions) : 0n);
      if (actions > n) fail("metric actions exceed observed events");
    });
    if (count !== integer(p.scope.observed_event_count)) fail("player event conservation failed");
    conserve(p);
  });
  if (eventSum > integer(payload.scope.observed_event_count)) fail("profile events exceed dataset events");
  const model = JSON.parse(JSON.stringify(payload));
  model.profiles.forEach((p) => {
    p.identity.team = teamAlias(p.identity.team);
    p.context_key = JSON.stringify(CANONICAL_KEYS.map((k) => p.identity[k]));
  });
  model.profiles.sort((a, b) => compareId(a.identity.player_id, b.identity.player_id) ||
    CANONICAL_KEYS.slice(1).map((k) => compareText(a.identity[k], b.identity[k])).find((v) => v !== 0) || 0);
  return model;
}

export async function readDiagnosticFile(file) {
  if (!file || typeof file.text !== "function" || !Number.isSafeInteger(file.size) || file.size <= 0 || file.size > 16 * 1024 * 1024) throw new Error("Choose a nonempty diagnostic JSON file under 16 MiB.");
  let payload;
  try { payload = JSON.parse(await file.text()); } catch { throw new Error("The local file is not readable JSON."); }
  return parseDiagnosticProfiles(payload);
}
