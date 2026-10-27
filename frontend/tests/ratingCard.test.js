import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire, Module } from "node:module";
import { fileURLToPath } from "node:url";
import { METRICS, classify, classifyDemo, demoOverall } from "../src/lib/archetypes.js";
import { ratingCard, OVR_PENDING } from "../src/lib/ratingCard.js";

const require = createRequire(import.meta.url);
const { buildSync } = require("esbuild");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
function component(name) {
  const filename = fileURLToPath(new URL(`../src/components/${name}.jsx`, import.meta.url));
  const result = buildSync({ entryPoints: [filename], bundle: true, write: false, platform: "node", format: "cjs",
    jsx: "automatic", external: ["react", "react-dom", "react/jsx-runtime"] });
  const mod = new Module(filename);
  mod.paths = Module._nodeModulePaths(fileURLToPath(new URL("..", import.meta.url)));
  mod._compile(result.outputFiles[0].text, filename);
  return mod.exports.default;
}
const PlayerCard = component("PlayerCard"), Radar = component("Radar");
const renderCard = (player, demo = false) => renderToStaticMarkup(React.createElement(PlayerCard, { player, demo }));
const base = { id: "fixture", name: "Invented fixture", team: "Invented club", position: "CB", minutes: 1200 };
const fixture = () => ({ ...base, attributes: Object.fromEntries(METRICS.map((m) => [m.id, { rating: 61.23456789, percentile: 20 }])) });
const demoRows = JSON.parse(readFileSync(new URL("../src/data/players.json", import.meta.url), "utf8"));

test("exact five canonical IDs and labels replace Clearances with Recoveries", () => {
  assert.deepEqual(METRICS.map((m) => m.id), ["tackles", "interceptions", "recoveries", "press_resistance", "line_breaking_passes"]);
  assert.deepEqual(METRICS.map((m) => m.label), ["Tackles", "Interceptions", "Recoveries", "Press Resistance", "Line-Breaking Passes"]);
  assert.equal(METRICS[2].key, "REC");
  assert.doesNotMatch(renderCard(fixture()), /Clearances/);
});

test("rating and percentile remain independent, precision retained, integer labels only", () => {
  const p = fixture(); p.attributes.tackles = { rating: 61.23456789, percentile: 95.1 };
  const before = structuredClone(p), card = ratingCard(p);
  assert.equal(card.attributes[0].value, 61.23456789);
  assert.equal(card.attributes[0].text, "61");
  assert.equal(card.attributes[0].percentile, 95.1);
  assert.equal(card.archetype.tier, "+");
  assert.equal(card.archetype.value, 95.1);
  const html = renderCard(p);
  assert.match(html, /width:61.23456789%/);
  assert.match(html, /Tackles 61/);
  assert.deepEqual(p, before);
  p.attributes.tackles.rating = 99;
  assert.deepEqual(classify(p), card.archetype);
  p.attributes.tackles.percentile = 80;
  assert.equal(ratingCard(p).attributes[0].value, 99);
  assert.equal(classify(p).tier, "−");
});

for (const [pct, tier] of [[0, null], [74.999, null], [75, "−"], [89.999, "−"], [90, "+"], [100, "+"]]) {
  test(`Gold/Silver use unrounded percentile ${pct}, independent of rating 99`, () => {
    const p = fixture(); p.attributes.tackles = { rating: 99, percentile: pct };
    assert.equal(classify(p).tier, tier);
  });
}

test("highest eligible archetype and existing position-specific tie orders are stable", () => {
  for (const [position, expected] of [["CB", ["Stopper", "Sweeper", "Tactician / Reader", "Libero", "Ball-Playing CB"]],
    ["DM", ["Destroyer", "Anchor", "Ball-Winning Midfielder", "Volante", "Deep-Lying Playmaker"]]]) {
    const keys = position === "CB" ? ["tackles", "recoveries", "interceptions", "press_resistance", "line_breaking_passes"] : METRICS.map((m) => m.id);
    const p = { ...base, position, attributes: Object.fromEntries(keys.map((k) => [k, { rating: 1, percentile: 91 }])) };
    for (let i = 0; i < keys.length; i++) {
      assert.equal(classify(p).name, expected[i]);
      delete p.attributes[keys[i]];
    }
    assert.equal(classify(p).name, "Standard");
  }
  const p = fixture(); p.attributes.recoveries.percentile = 99;
  assert.equal(classify(p).name, "Sweeper");
  p.position = "GK";
  assert.equal(classify(p).metric, null);
});

test("missing/invalid ratings render N/A without bars, points or a fabricated polygon", () => {
  for (const value of [undefined, null, NaN, Infinity, -1, 0, 101, "90", true]) {
    const p = fixture(); p.attributes.recoveries.rating = value;
    const card = ratingCard(p), html = renderCard(p);
    assert.equal(card.attributes[2].value, null);
    assert.equal(card.attributes[2].text, "N/A");
    assert.equal((html.match(/class="dot"/g) || []).length, 4);
    assert.equal((html.match(/style="width:/g) || []).length, 4);
    assert.doesNotMatch(html, /class="shape"|NaN|Infinity|undefined/);
    assert.match(html, /Recoveries N\/A/);
  }
  const html = renderCard(base);
  assert.doesNotMatch(html, /class="dot"|class="shape"|style="width:/);
  assert.match(renderToStaticMarkup(React.createElement(Radar)), /Recoveries N\/A/);
});

test("missing rating can retain ranking percentile; invalid percentiles never classify", () => {
  const p = { ...base, attributes: { recoveries: { rating: null, percentile: 95 } } };
  assert.equal(ratingCard(p).archetype.name, "Sweeper");
  assert.equal(ratingCard(p).attributes[2].text, "N/A");
  for (const percentile of [null, undefined, NaN, Infinity, -1, 101, "95", true]) {
    p.attributes.recoveries.percentile = percentile;
    assert.equal(classify(p).value, null);
  }
});

test("no invented OVR, no legacy/raw/DRI/progressive passing fallback", () => {
  const p = { ...fixture(), ovr: 99, overall: { score: 99 }, pct: { LB: 99 }, dri_fifa: 99, prog_passes_p90: 99 };
  delete p.attributes.line_breaking_passes;
  assert.equal(ratingCard(p).attributes[4].value, null);
  assert.equal(ratingCard(p).ovr, null);
  assert.equal(ratingCard(fixture()).ovr, null);
  assert.match(renderCard(p), /N\/A — POLICY NOT FINALIZED/);
  assert.equal(ratingCard({ ...base, pct: { T: 99 } }).attributes[0].value, null);
  assert.equal(classify({ ...base, pct: { T: 99 } }).value, null);
});

test("every existing demo retains original percentiles, archetype and illustrative OVR", () => {
  for (const p of demoRows) {
    const values = ["T", "I", "C", "P", "LB"].map((k) => p.pct[k]);
    const card = ratingCard(p, { demo: true });
    assert.deepEqual(card.attributes.map((m) => m.value), values);
    assert.equal(demoOverall(p), Math.round(values.reduce((a, b) => a + b) / 5));
    const order = p.position === "CB" ? ["T", "REC", "I", "P", "LB"] : ["T", "I", "REC", "P", "LB"];
    const best = order.reduce((a, b) => p.pct[b] > p.pct[a] ? b : a);
    assert.equal(classifyDemo(p).value, p.pct[best]);
    assert.equal(classifyDemo(p).metric, p.pct[best] >= 75 ? best : null);
    assert.equal(card.archetype.tier, p.pct[best] >= 90 ? "+" : p.pct[best] >= 75 ? "−" : null);
    const html = renderCard(p, true);
    assert.match(html, /Fictional percentile profile/);
    assert.match(html, /Clearances/);
    assert.match(html, /Demo OVR/);
    assert.doesNotMatch(html, /FIFA-style rating profile/);
  }
});
