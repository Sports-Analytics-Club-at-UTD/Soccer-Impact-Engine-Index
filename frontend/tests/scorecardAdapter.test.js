import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { CANONICAL_KEYS, FIELD_DEFINITIONS, LIMITATIONS, SCHEMA_VERSION,
  ScorecardPayloadError, contextKey, displayMetric, parseScorecard } from "../src/lib/scorecardAdapter.js";

// Synthetic contract fixtures only; no real complete-season population or ratings.
function player(changes = {}) {
  const row = Object.fromEntries(Object.keys(FIELD_DEFINITIONS).map((c) => [c, c.endsWith("_present") ? false : null]));
  return { ...row, player_id: "1", team: "Team", competition_name: "League", season_name: "Season",
    player_name: "Same label", position_group: "CB", ...changes };
}
function payload(players = [player()]) {
  return { schema_version: SCHEMA_VERSION, measurement_type: "raw_metrics", metadata: {
    canonical_keys: [...CANONICAL_KEYS], integer_encoding: "decimal_string",
    fields: structuredClone(FIELD_DEFINITIONS), coverage_status: "unverified",
    limitations: [...LIMITATIONS], passing_reference: null }, players };
}
function passing(p = payload()) {
  const row = p.players[0];
  for (const [c, spec] of Object.entries(FIELD_DEFINITIONS)) {
    if (spec.component === "passing" && spec.kind === "integer") row[c] = "0";
  }
  Object.assign(row, { passing_present: true, passing_rate_status: "missing_minutes", value_sum: 0,
    passing_difficulty_scope: "synthetic cohort", passing_difficulty_complete: true });
  p.metadata.passing_reference = { scope: "synthetic cohort", declared_complete: true, independently_verified: false };
  return p;
}
function press(p = payload()) {
  const row = p.players[0];
  for (const [c, spec] of Object.entries(FIELD_DEFINITIONS)) {
    if (spec.component === "press" && spec.kind === "integer") row[c] = "0";
  }
  row.press_present = true;
  return p;
}
const rejects = (p) => assert.throws(() => parseScorecard(p), ScorecardPayloadError);

test("canonical identity and derived context key", () => {
  const row = parseScorecard(payload()).players[0];
  assert.equal(row.context_key, '["1","Team","League","Season"]');
  assert.equal(row.player_id, "1");
});
test("transfers, seasons, leagues and same-name players remain distinct", () => {
  const rows = [player(), player({ team: "Other" }), player({ season_name: "Other" }),
    player({ competition_name: "Other" }), player({ player_id: "2" })];
  const parsed = parseScorecard(payload(rows));
  assert.equal(new Set(parsed.players.map((r) => r.context_key)).size, 5);
  assert.equal(new Set(parsed.players.map((r) => r.player_name)).size, 1);
});
test("deterministic numeric-ID order, independent of incoming order", () => {
  const rows = [player({ player_id: "10" }), player({ player_id: "2" })];
  assert.deepEqual(parseScorecard(payload(rows)), parseScorecard(payload([...rows].reverse())));
  assert.deepEqual(parseScorecard(payload(rows)).players.map((p) => p.player_id), ["2", "10"]);
});
test("full signed int64 identity survives strict JSON roundtrip", () => {
  const p = JSON.parse(JSON.stringify(payload([player({ player_id: "9223372036854775807" })])));
  assert.equal(parseScorecard(p).players[0].player_id, "9223372036854775807");
});
test("numeric, rounded, zero and unsupported IDs are rejected", () => {
  for (const id of [1, 9007199254740993, "0", "01", "-1", "1.0", "9223372036854775808", null]) {
    rejects(payload([player({ player_id: id })]));
  }
});
test("duplicate canonical identity is rejected", () => rejects(payload([player(), player()])));
test("known aliases normalize and collide safely", () => {
  for (const [alias, team] of [["Caen", "Stade Malherbe Caen"], ["Marseille", "Olympique de Marseille"]]) {
    assert.equal(parseScorecard(payload([player({ team: alias })])).players[0].team, team);
    rejects(payload([player({ team: alias }), player({ team })]));
  }
});
test("context key escapes delimiter-like labels", () => {
  assert.notEqual(contextKey(player({ team: "a|b", season_name: "c" })), contextKey(player({ team: "a", season_name: "b|c" })));
});
test("unsupported versions and missing versions fail", () => {
  for (const version of ["v2", 1, null, undefined]) rejects({ ...payload(), schema_version: version });
});
test("unexpected payload and player fields fail", () => {
  rejects({ ...payload(), demo: true });
  for (const field of ["unexpected", "pct", "ovr", "tier", "archetype", "rank", "photo"]) {
    rejects(payload([player({ [field]: 99 })]));
  }
});
test("missing fields and undefined values fail", () => {
  const p = payload();
  delete p.players[0].press_present;
  rejects(p);
  rejects(payload([player({ minutes: undefined })]));
});
test("unit or meaning substitution is rejected", () => {
  const p = payload();
  p.metadata.fields.press_resistance_rate.unit = "percentile";
  rejects(p);
  rejects({ ...payload(), measurement_type: "rankings" });
});
test("recovery zero, per90, status and presence stay separate", () => {
  const p = payload([player({ recovery_tackle_present: true, recovery_tackle_count: "0",
    recovery_tackle_per90: 0, recovery_tackle_minutes: 180, recovery_tackle_rate_status: "ok" })]);
  const row = parseScorecard(p).players[0];
  assert.equal(row.recovery_tackle_count, "0");
  assert.equal(row.recovery_tackle_per90, 0);
  assert.equal(row.recovery_interception_present, false);
  assert.equal(row.recovery_interception_count, null);
});
test("press raw percentages and underlying counts are preserved", () => {
  const p = press();
  Object.assign(p.players[0], { pressured_pass_attempts: "4", pressured_pass_completed: "3",
    pressured_actions: "4", successful_pressured_actions: "3", pressured_pass_completion_rate: 75, press_resistance_rate: 75 });
  const row = parseScorecard(p).players[0];
  assert.equal(row.press_resistance_rate, 75);
  assert.equal(row.pressured_dribble_completion_rate, null);
  assert.equal(displayMetric(row, "press_resistance_rate").unit, "percent");
});
test("passing raw values and calibration declaration are preserved", () => {
  const parsed = parseScorecard(passing());
  assert.equal(parsed.players[0].value_sum, 0);
  assert.equal(parsed.players[0].passing_difficulty_scope, "synthetic cohort");
  assert.equal(parsed.metadata.passing_reference.independently_verified, false);
  assert.equal(FIELD_DEFINITIONS.pass_value_p90.unit, "difficulty_weighted_yards/90min");
});
test("missing component and present N/A rate remain distinguishable", () => {
  const row = parseScorecard(press()).players[0];
  assert.equal(row.press_present, true);
  assert.equal(row.press_resistance_rate, null);
  assert.equal(row.passing_present, false);
  assert.equal(row.prog_passes, null);
  assert.equal(displayMetric(row, "press_resistance_rate").text, "N/A");
});
test("null minutes and zero minutes retained with source status", () => {
  const p = passing();
  const row = parseScorecard(p).players[0];
  assert.equal(row.passing_minutes, null);
  assert.equal(row.passing_rate_status, "missing_minutes");
  Object.assign(p.players[0], { passing_minutes: 0, passing_rate_status: "zero_minutes" });
  assert.equal(parseScorecard(p).players[0].passing_minutes, 0);
});
test("NaN, infinities, negative numbers and booleans cannot reach chart values", () => {
  for (const value of [NaN, Infinity, -Infinity, -1, true, "75"]) {
    const p = press();
    p.players[0].press_resistance_rate = value;
    rejects(p);
    assert.throws(() => displayMetric({ press_resistance_rate: value }, "press_resistance_rate"), ScorecardPayloadError);
  }
});
test("percentage greater than 100 is invalid", () => {
  const p = press();
  p.players[0].press_resistance_rate = 101;
  rejects(p);
});
test("presence cannot be null and absent component cannot have values", () => {
  rejects(payload([player({ press_present: null })]));
  rejects(payload([player({ pressured_actions: "0" })]));
  const p = passing();
  p.players[0].prog_attempts = null;
  rejects(p);
});
test("passing presence requires matching calibration", () => {
  const p = passing();
  p.metadata.passing_reference = null;
  rejects(p);
  const q = passing();
  q.players[0].passing_difficulty_scope = "other";
  rejects(q);
});
test("sample or overclaimed provenance rejected", () => {
  for (const [key, value] of [["declared_complete", false], ["independently_verified", true]]) {
    const p = passing();
    p.metadata.passing_reference[key] = value;
    rejects(p);
  }
  const p = payload();
  p.metadata.coverage_status = "complete";
  rejects(p);
});
test("large count displayed exactly, not rounded into a chart number", () => {
  const p = passing();
  p.players[0].prog_attempts = "9223372036854775807";
  const metric = displayMetric(parseScorecard(p).players[0], "prog_attempts");
  assert.equal(metric.value, "9223372036854775807");
  assert.equal(metric.text, "9223372036854775807 events");
  assert.equal(metric.chartValue, null);
});
test("zero display and available chart value are finite", () => {
  const row = parseScorecard(passing()).players[0];
  assert.deepEqual(displayMetric(row, "value_sum"), { value: 0, unit: "difficulty_weighted_yards", text: "0 difficulty_weighted_yards", chartValue: 0 });
});
test("invalid numeric count strings rejected", () => {
  for (const value of [0, "1.5", "-1", "00", "9223372036854775808"]) {
    const p = passing();
    p.players[0].prog_attempts = value;
    rejects(p);
  }
});
test("input immutability and returned metadata independence", () => {
  const p = passing(), before = structuredClone(p);
  const parsed = parseScorecard(p);
  parsed.players[0].team = "changed";
  parsed.metadata.fields.value_sum.unit = "changed";
  parsed.metadata.passing_reference.scope = "changed";
  assert.deepEqual(p, before);
});
test("empty payload stays empty without fictional fallback", () => {
  assert.deepEqual(parseScorecard(payload([])).players, []);
  rejects(null);
  rejects([]);
});
test("no OVR, percentiles, tiers or archetypes are calculated", () => {
  const row = parseScorecard(passing()).players[0];
  assert.deepEqual(Object.keys(row), [...Object.keys(FIELD_DEFINITIONS), "context_key"]);
  for (const field of ["ovr", "pct", "tier", "archetype"]) assert.equal(Object.hasOwn(row, field), false);
});
test("exposure disagreement and wrong source status rejected", () => {
  const p = passing();
  p.players[0].passing_rate_status = "ok";
  rejects(p);
  const q = press();
  Object.assign(q.players[0], { minutes: 180, press_minutes: 90 });
  rejects(q);
});
test("code-point string ordering is deterministic across languages", () => {
  const p = payload([player({ team: "\u{10000}" }), player({ team: "\ue000" })]);
  assert.equal(parseScorecard(p).players[0].team, "\ue000");
});

test("actual Python M4B0 export parses without schema or unit drift", () => {
  const script = `
import json, sys
sys.path.insert(0, 'tests')
from test_scorecard import assemble, fixtures, context
from src.frontend_export import export_scorecard
result = assemble(fixtures([context(), context(team='Other'), context(season_name='Other'),
                           context(2), context(2**63-1)]))
print(json.dumps(export_scorecard(result), allow_nan=False))
`;
  const run = spawnSync(process.env.PYTHON || "python", ["-B", "-W", "error", "-c", script], {
    cwd: fileURLToPath(new URL("../../", import.meta.url)), encoding: "utf8",
  });
  assert.equal(run.error, undefined);
  assert.equal(run.status, 0, run.stderr);
  const model = parseScorecard(JSON.parse(run.stdout));
  assert.equal(model.players.length, 5);
  assert.equal(new Set(model.players.map((p) => p.context_key)).size, 5);
  assert.equal(model.players.at(-1).player_id, "9223372036854775807");
  assert.equal(model.players[0].recovery_tackle_per90, .5);
  assert.equal(model.players[0].press_resistance_rate, 100);
  assert.equal(model.players[0].prog_passes, "1");
  assert.equal(model.metadata.coverage_status, "unverified");
});
