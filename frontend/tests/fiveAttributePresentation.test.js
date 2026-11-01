import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createRequire, Module } from "node:module";
import { fileURLToPath } from "node:url";
import { FIVE_METRICS, parseFiveAttributeDelivery, fiveAttributePlayers } from "../src/lib/fiveAttributePresentation.js";
import { playerDataMode, loadPlayerExperience } from "../src/lib/playerDataMode.js";

const require = createRequire(import.meta.url), { buildSync } = require("esbuild");
const React = require("react"), { renderToStaticMarkup } = require("react-dom/server");
const fixture = () => JSON.parse(readFileSync(new URL("../src/fixtures/syntheticFiveAttributes.json", import.meta.url), "utf8"));
function component(name) {
  const filename = fileURLToPath(new URL(`../src/components/${name}.jsx`, import.meta.url));
  const r = buildSync({ entryPoints: [filename], bundle: true, write: false, platform: "node", format: "cjs", jsx: "automatic", loader: { ".css": "empty" }, logLevel: "silent", external: ["react", "react-dom", "react/jsx-runtime"] });
  const mod = new Module(filename); mod.paths = Module._nodeModulePaths(fileURLToPath(new URL("..", import.meta.url))); mod._compile(r.outputFiles[0].text, filename); return mod.exports.default;
}
const Card = component("PlayerCard"), Comparison = component("FiveAttributeComparison"), Experience = component("FiveAttributeExperience");
const models = async () => fiveAttributePlayers(await parseFiveAttributeDelivery(fixture()));
const render = (p) => renderToStaticMarkup(React.createElement(Card, { player: p }));

test("Python fixture -> fingerprint validation -> existing PlayerCard dispatch", async () => {
  const data = execFileSync("python", ["-B", "-c", "import json; from scripts.make_synthetic_five_attribute_fixture import fixture; print(json.dumps(fixture()))"], { cwd: fileURLToPath(new URL("../..", import.meta.url)), encoding: "utf8" });
  assert.deepEqual(await parseFiveAttributeDelivery(data), fixture());
  assert.match(render((await models())[0]), /SYNTHETIC TEST FIXTURE/);
});

test("five correct labels, measured units, positions and no invented overall", async () => {
  const html = render((await models())[0]);
  for (const m of FIVE_METRICS) assert.ok(html.includes(m.label));
  assert.match(html, /per 90/); assert.match(html, /75%/); assert.match(html, /30 successful pressured actions \/ 40 pressured attempts/);
  assert.match(html, /Comparison: MID/); assert.match(html, /synthetic:mid-transfer:2015\/2016/);
  assert.doesNotMatch(html, /Archetype|OVR|Overall|Gold|Silver|ghost-ovr/);
  assert.match(html, /does not verify defensive line-breaking events/);
});

test("five axes reuse Radar; ratings remain separate from percentiles", async () => {
  const html = render((await models())[0]);
  assert.equal((html.match(/class="axis"/g) || []).length, 5);
  assert.equal((html.match(/class="dot"/g) || []).length, 5);
  assert.equal((html.match(/class="shape"/g) || []).length, 1);
  assert.match(html, /Tackling 65/); assert.match(html, /Percentile: 75/);
});

test("missing attribute remains N/A with four points and no polygon", async () => {
  const html = render((await models())[3]);
  assert.match(html, /N\/A/); assert.match(html, /missing geometry example/);
  assert.equal((html.match(/class="axis"/g) || []).length, 5);
  assert.equal((html.match(/class="dot"/g) || []).length, 4);
  assert.doesNotMatch(html, /class="shape"/);
  assert.match(html, /Excluded appearances:/);
});

test("Bundesliga uses same card and retains sub40/partial-season samples", async () => {
  const html = render((await models())[2]);
  assert.match(html, /five-attribute player card/); assert.match(html, /LIMITED DATA/); assert.match(html, /PARTIAL SEASON/);
  assert.match(html, /5 successful pressured actions \/ 12 pressured attempts/); assert.match(html, /Fewer than 40 pressured actions \(12\)/);
  assert.equal((html.match(/class="axis"/g) || []).length, 5);
});

test("one transferred player-season, two clubs; duplicate identity rejected", async () => {
  const d = fixture(), p = (await models())[0];
  assert.equal(d.players.filter((x) => x.id === p.id).length, 1);
  const html = render(p); assert.match(html, /SYNTHETIC North Club/); assert.match(html, /SYNTHETIC South Club/);
  d.players.push(structuredClone(d.players[0])); await assert.rejects(parseFiveAttributeDelivery(d), /duplicate canonical/);
});

test("comparison retains each position and missing/limited labels; no aggregate score", async () => {
  const ps = await models();
  const html = renderToStaticMarkup(React.createElement(Comparison, { players: [ps[0], ps[2]] }));
  assert.match(html, /MID/); assert.match(html, /CB/); assert.match(html, /PARTIAL SEASON/);
  for (const m of FIVE_METRICS) assert.ok(html.includes(m.label));
  assert.doesNotMatch(html, /OVR|Archetype|Gold|Silver/);
  assert.match(renderToStaticMarkup(React.createElement(Comparison, { players: [ps[0], ps[3]] })), /N\/A/);
  assert.match(renderToStaticMarkup(React.createElement(Comparison, { players: [ps[0], ps[0]] })), /two different player-seasons/);
});

for (const [key, values] of [["rating", [0, 100, -1, true, NaN, Infinity]], ["percentile", [-1, 101, true, Infinity]]]) {
  test(`${key} numeric bounds reject rather than coerce`, async () => {
    for (const v of values) { const d = fixture(); d.players[0].attributes.tackles[key] = v; await assert.rejects(parseFiveAttributeDelivery(d)); }
  });
}
test("fingerprint corruption and MID/CB metadata mismatch reject", async () => {
  const a = fixture(); a.reference.positions.MID.tackles.mean = 999; await assert.rejects(parseFiveAttributeDelivery(a), /fingerprint/);
  const b = fixture(); b.players[0].attributes.tackles.normalization.comparison_position = "CB"; await assert.rejects(parseFiveAttributeDelivery(b), /normalization/);
  const c = fixture(); c.reference.fingerprint = "0".repeat(64); await assert.rejects(parseFiveAttributeDelivery(c), /fingerprint/);
});
test("unauthorized real numeric delivery cannot select this path", async () => {
  for (const [k,v] of [["classification","verified"],["publication_authorized",true],["numeric_real_delivery_enabled",true]]) {
    const d = fixture(); d[k] = v; await assert.rejects(parseFiveAttributeDelivery(d), /synthetic-only boundary/);
  }
  const d = fixture(); Object.assign(d.players[0], { player_id: "5574", id: "5574:2015/2016", name: "Toni Kroos" });
  await assert.rejects(parseFiveAttributeDelivery(d), /synthetic canonical/);
  await assert.rejects(parseFiveAttributeDelivery({ schema_version: "private-five-attribute-player-season/v2", players: [] }));
});
test("unknown fields, OVR and duplicate JSON keys reject", async () => {
  const d = fixture(); d.players[0].ovr = 75; await assert.rejects(parseFiveAttributeDelivery(d), /unexpected/);
  const source = JSON.stringify(fixture()).replace('"classification":"synthetic"', '"classification":"synthetic","classification":"synthetic"');
  await assert.rejects(parseFiveAttributeDelivery(source), /duplicate/i);
});
test("mode is explicit; existing default and limited-data routes remain unchanged", async () => {
  assert.equal(playerDataMode(undefined), "demo"); assert.equal(playerDataMode("limited-data"), "limited-data");
  assert.equal(playerDataMode("five-attribute-synthetic"), "five-attribute-synthetic");
  assert.equal(await loadPlayerExperience("five-attribute-synthetic", { "five-attribute-synthetic": () => 7, demo: () => assert.fail() }), 7);
  assert.match(renderToStaticMarkup(React.createElement(Experience, {})), /SYNTHETIC TEST FIXTURE/);
});
test("readiness client has no real-file loader or private score imports", () => {
  const files = ["../src/components/FiveAttributeExperience.jsx", "../src/lib/fiveAttributePresentation.js"];
  for (const f of files) {
    const source = readFileSync(new URL(f, import.meta.url), "utf8");
    assert.doesNotMatch(source, /fetch\(|type="file"|data\/derived|PRIVATE-EXPERIMENTAL-scores|private-five-attribute-v2/);
  }
  const d = fixture(); assert.ok(d.players.every((p) => p.player_id.startsWith("synthetic:") && p.name.startsWith("SYNTHETIC ")));
});
