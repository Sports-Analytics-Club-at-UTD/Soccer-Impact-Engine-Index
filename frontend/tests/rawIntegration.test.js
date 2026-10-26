import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadPlayerExperience, playerDataMode } from "../src/lib/playerDataMode.js";
import { loadScorecard, scorecardAssetUrl, ScorecardLoadError } from "../src/lib/scorecardLoader.js";
import { parseScorecard } from "../src/lib/scorecardAdapter.js";
import { adjacentContext, BROWSE_LABEL, browsePlayers, componentAvailability, contextLabel, PASSING_METRICS,
  playerLabel, positionLabel, positionOptions, PRESS_METRICS, rawCardModel, RAW_METRIC_NOTICE,
  RAW_MODE_NOTICE, selectContext } from "../src/lib/rawScorecardView.js";
import { passingPayload, payload, player, response } from "./fixtures/rawScorecards.js";

const model = (p = payload()) => parseScorecard(p);
const load = (p) => loadScorecard({ fetchImpl: async () => response(p) });

test("mode defaults only to demo when unset", () => {
  assert.equal(playerDataMode(undefined), "demo");
  assert.equal(playerDataMode("demo"), "demo");
  assert.equal(playerDataMode("raw"), "raw");
});
test("unknown or blank configured modes fail explicitly", () => {
  for (const value of ["", "RAW", "other", null, 1]) assert.throws(() => playerDataMode(value), /Unknown/);
});
test("demo mode calls only the demo loader", async () => {
  const calls = [];
  assert.equal(await loadPlayerExperience("demo", { demo: () => { calls.push("demo"); return "demo"; }, raw: () => calls.push("raw") }), "demo");
  assert.deepEqual(calls, ["demo"]);
});
test("raw mode failure never calls a fictional fallback", async () => {
  let demoCalls = 0;
  await assert.rejects(() => loadPlayerExperience("raw", { raw: async () => { throw new Error("chunk failed"); }, demo: () => { demoCalls++; } }), /chunk failed/);
  assert.equal(demoCalls, 0);
});
test("unknown mode does not invoke either loader", () => {
  let calls = 0;
  assert.throws(() => loadPlayerExperience("bad", { raw: () => calls++, demo: () => calls++ }), /Unknown/);
  assert.equal(calls, 0);
});
test("raw dependency graph excludes demo records, radar and scoring modules", () => {
  const visited = new Set();
  function walk(path) {
    if (visited.has(path)) return;
    visited.add(path);
    const source = readFileSync(path, "utf8");
    for (const match of source.matchAll(/\bimport\s+(?:[^;]*?\s+from\s+)?["'](\.[^"']+)["']/g)) {
      walk(resolve(dirname(path), match[1]));
    }
  }
  walk(fileURLToPath(new URL("../src/components/RawExperience.jsx", import.meta.url)));
  for (const path of visited) assert.doesNotMatch(path.replaceAll("\\", "/"), /\/(?:data\/players\.json|lib\/(?:data|archetypes)\.js|components\/(?:Radar|PlayerCard|Search|Archetypes|Teams|Hero|Description)\.jsx)$/);
});
test("asset URL respects root, subpath, relative and CDN Vite bases", () => {
  for (const [base, expected] of [["/", "/data/scorecard.json"], ["/soccer/", "/soccer/data/scorecard.json"],
    ["/soccer", "/soccer/data/scorecard.json"], ["./", "./data/scorecard.json"],
    ["https://assets.example/app/", "https://assets.example/app/data/scorecard.json"]]) assert.equal(scorecardAssetUrl(base), expected);
  assert.throws(() => scorecardAssetUrl(""));
});
test("successful load uses injected fetch and existing parser", async () => {
  const signal = new AbortController().signal;
  const result = await loadScorecard({ baseUrl: "/club/", signal, fetchImpl: async (url, options) => {
    assert.equal(url, "/club/data/scorecard.json");
    assert.equal(options.signal, signal);
    assert.equal(options.headers.Accept, "application/json");
    return response(payload());
  } });
  assert.equal(result.players[0].context_key, '["1","Team","League","Season"]');
});
test("404 and server failures are explicit with no fake profiles", async () => {
  for (const status of [404, 500]) await assert.rejects(loadScorecard({ fetchImpl: async () => ({ ok: false, status }) }),
    (e) => e instanceof ScorecardLoadError && e.code === "http" && e.message.includes(String(status)));
});
test("network failure is explicit", async () => {
  await assert.rejects(loadScorecard({ fetchImpl: async () => { throw new TypeError("offline"); } }), (e) => e.code === "network");
});
test("invalid JSON including a SPA HTML fallback is rejected", async () => {
  await assert.rejects(loadScorecard({ fetchImpl: async () => ({ ok: true, json: async () => { throw new SyntaxError("Unexpected <"); } }) }), (e) => e.code === "json");
});
test("unsupported schema is rejected without weakening validation", async () => {
  await assert.rejects(load({ ...payload(), schema_version: "v2" }), (e) => e.code === "contract");
});
test("invalid units, provenance and duplicate contexts remain rejected", async () => {
  const units = payload(); units.metadata.fields.value_sum.unit = "goals";
  const provenance = payload(); provenance.metadata.coverage_status = "complete";
  for (const p of [units, provenance, payload([player(), player()])]) await assert.rejects(load(p), (e) => e.code === "contract");
});
test("missing or sample passing calibration fails at load boundary", async () => {
  const p = passingPayload(); p.metadata.passing_reference = null;
  const q = passingPayload(); q.metadata.passing_reference.declared_complete = false;
  for (const input of [p, q]) await assert.rejects(load(input), (e) => e.code === "contract");
});
test("an empty valid scorecard stays empty", async () => {
  const loaded = await load(payload([]));
  assert.deepEqual(loaded.players, []);
  assert.equal(loaded.metadata.coverage_status, "unverified");
});
test("loading awaits response rather than making observations", async () => {
  let resolveResponse;
  let finished = false;
  const pending = loadScorecard({ fetchImpl: () => new Promise((resolve) => { resolveResponse = resolve; }) });
  pending.then(() => { finished = true; });
  await Promise.resolve();
  assert.equal(finished, false);
  resolveResponse(response(payload([])));
  assert.equal((await pending).players.length, 0);
});
test("cancellation is propagated without fabricating a load error/model", async () => {
  const error = new Error("aborted"); error.name = "AbortError";
  await assert.rejects(loadScorecard({ fetchImpl: async () => { throw error; } }), (e) => e === error);
});
test("same names retain separate contexts and stable-ID selections", () => {
  const players = model(payload([player({ player_id: "2" }), player()])).players;
  assert.equal(browsePlayers(players, { query: "synthetic" }).length, 2);
  assert.equal(selectContext(players, players[1].context_key).player_id, "2");
  assert.equal(selectContext(players, "not a context"), null);
});
test("one player across clubs and seasons remains separately selectable", () => {
  const players = model(payload([player(), player({ team: "Other" }), player({ season_name: "Other" })])).players;
  for (const row of players) assert.equal(selectContext(players, row.context_key), row);
  assert.equal(new Set(players.map((p) => p.context_key)).size, 3);
});
test("large ID remains exact in search, fallback name and selection", () => {
  const id = "9223372036854775807";
  const players = model(payload([player({ player_id: id, player_name: null })])).players;
  assert.equal(browsePlayers(players, { query: id })[0].player_id, id);
  assert.equal(playerLabel(players[0]), `Player ID ${id}`);
  assert.equal(selectContext(players, players[0].context_key).player_id, id);
});
test("name search supports accents and exact ID search", () => {
  const players = model(payload([player({ player_name: "José Synthetic" }), player({ player_id: "10" })])).players;
  assert.equal(browsePlayers(players, { query: "jose" })[0].player_id, "1");
  assert.equal(browsePlayers(players, { query: "10" }).length, 1);
  assert.equal(browsePlayers(players, { query: "no match" }).length, 0);
});
test("context descriptions include team, competition and season", () => {
  assert.equal(contextLabel(player()), "Team · League · Season");
});
test("missing/blank display names do not invent a person", () => {
  for (const name of [null, "", "   "]) assert.equal(playerLabel(player({ player_name: name })), "Player ID 1");
});
test("All plus observed roles retain CM/GK/unknown and do not infer eligibility", () => {
  const rows = [player(), player({ player_id: "2", position_group: "CM" }), player({ player_id: "3", position_group: "GK" }),
    player({ player_id: "4", position_group: null }), player({ player_id: "5", position_group: "Other verified role" })];
  const players = model(payload(rows)).players;
  const options = positionOptions(players);
  assert.equal(options[0].label, "All");
  assert.deepEqual(options.map((o) => o.label).sort(), ["All", "CB", "CM", "GK", "Other verified role", "Unspecified"].sort());
  assert.equal(browsePlayers(players).length, 5);
  assert.equal(browsePlayers(players, { position: "unspecified" })[0].player_id, "4");
  assert.equal(browsePlayers(players, { position: "known:CM" })[0].player_id, "2");
});
test("unknown role and a literal Unspecified role have different filter values", () => {
  const rows = [player({ position_group: null }), player({ player_id: "2", position_group: "Unspecified" })];
  assert.equal(positionOptions(rows).length, 3);
  assert.equal(positionLabel(rows[0]), "Unspecified");
});
test("browse order stays canonical, with no OVR or metric sorting", () => {
  const players = model(payload([player({ player_id: "2", player_name: "Aaron" }), player({ player_name: "Zed" })])).players;
  assert.deepEqual(browsePlayers(players).map((p) => p.player_name), ["Zed", "Aaron"]);
  assert.equal(BROWSE_LABEL, "Available player profiles");
  assert.doesNotMatch(BROWSE_LABEL, /top|rank/i);
});
test("keyboard navigation returns canonical keys and clamps boundaries", () => {
  const rows = model(payload([player(), player({ player_id: "2" })])).players;
  assert.equal(adjacentContext(rows, null, 1), rows[0].context_key);
  assert.equal(adjacentContext(rows, rows[0].context_key, 1), rows[1].context_key);
  assert.equal(adjacentContext(rows, rows[1].context_key, 1), rows[1].context_key);
  assert.equal(adjacentContext(rows, rows[1].context_key, -1), rows[0].context_key);
  assert.equal(adjacentContext([], null, 1), null);
});
test("recovery present zero is distinct from absent component", () => {
  const p = payload([player({ recovery_tackle_present: true, recovery_tackle_count: "0", recovery_tackle_per90: 0,
    recovery_tackle_minutes: 180, recovery_tackle_rate_status: "ok" })]);
  const m = model(p), card = rawCardModel(m.players[0], m.metadata);
  assert.equal(card.recovery[0].metrics[0].value, "0");
  assert.equal(card.recovery[0].metrics[1].value, 0);
  assert.match(card.recovery[0].availability, /Source row present/);
  assert.equal(card.recovery[1].metrics[0].text, "N/A");
  assert.match(card.recovery[1].availability, /no source component row/);
});
test("missing and zero source minutes retain explanations, never computed rates", () => {
  for (const [minutes, status, phrase] of [[null, "missing_minutes", "missing"], [0, "zero_minutes", "zero"]]) {
    const p = payload([player({ recovery_tackle_present: true, recovery_tackle_count: "1", recovery_tackle_minutes: minutes,
      recovery_tackle_rate_status: status })]);
    const m = model(p), card = rawCardModel(m.players[0], m.metadata);
    assert.equal(card.recovery[0].metrics[1].text, "N/A");
    assert.match(card.recovery[0].availability, new RegExp(phrase));
  }
});
test("all nine pressure labels are raw percentages/counts, not percentile scores", () => {
  assert.equal(PRESS_METRICS.length, 9);
  for (const [, label] of PRESS_METRICS) assert.doesNotMatch(label, /percentile|rank|tier/i);
  assert.equal(PRESS_METRICS.find(([field]) => field === "press_resistance_rate")[1], "Combined press resistance percentage");
});
test("passing has all eight fields, Level A label and distance units", () => {
  const m = model(passingPayload()), card = rawCardModel(m.players[0], m.metadata);
  assert.equal(PASSING_METRICS.length, 8);
  assert.match(card.passing.title, /Level A/);
  assert.equal(card.passing.metrics.find((v) => v.field === "value_sum").unit, "difficulty_weighted_yards");
  assert.equal(card.passing.metrics.find((v) => v.field === "pass_value_p90").unit, "difficulty_weighted_yards/90min");
});
test("calibration display is caller-attested, not independently verified", () => {
  const m = model(passingPayload()), card = rawCardModel(m.players[0], m.metadata);
  assert.equal(card.passing.scope, "synthetic bounded reference");
  assert.equal(card.passing.declaration, "Caller-attested complete: Yes. Independently verified: No.");
});
test("absent passing has no invented calibration", () => {
  const m = model(), card = rawCardModel(m.players[0], m.metadata);
  assert.equal(card.passing.scope, "N/A");
  assert.match(card.passing.declaration, /no passing source row/);
});
test("large count display retains exact string with no unsafe chart number", () => {
  const p = passingPayload(); p.players[0].prog_attempts = "9223372036854775807";
  const m = model(p), metric = rawCardModel(m.players[0], m.metadata).passing.metrics[0];
  assert.equal(metric.value, "9223372036854775807");
  assert.equal(metric.text, "9223372036854775807 events");
  assert.equal(metric.chartValue, null);
});
test("raw card contains no fabricated ratings/tiers and no invalid numeric display", () => {
  const m = model(passingPayload()), card = rawCardModel(m.players[0], m.metadata);
  const output = JSON.stringify(card);
  assert.doesNotMatch(output, /NaN|Infinity|"ovr"|"archetype"|"tier"|"pct"/);
  assert.equal(card.coverage, "unverified");
  assert.match(RAW_MODE_NOTICE, /not yet verified/);
  assert.match(RAW_METRIC_NOTICE, /No overall score/);
});
test("view helpers leave canonical model unchanged", () => {
  const m = model(passingPayload()), before = structuredClone(m);
  browsePlayers(m.players); positionOptions(m.players); rawCardModel(m.players[0], m.metadata);
  assert.deepEqual(m, before);
});
