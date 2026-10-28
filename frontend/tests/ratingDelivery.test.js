import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createRequire, Module } from "node:module";
import { fileURLToPath } from "node:url";
import { parseRatingDelivery, parseRatingJson, ratingPlayers, readRatingFile, RATING_NOTICE } from "../src/lib/ratingDelivery.js";
import { playerDataMode, loadPlayerExperience } from "../src/lib/playerDataMode.js";
import { ratingCard } from "../src/lib/ratingCard.js";

const fixture = () => JSON.parse(readFileSync(new URL("./fixtures/syntheticRatings.json", import.meta.url), "utf8"));
const require = createRequire(import.meta.url), { buildSync } = require("esbuild");
const React = require("react"), { renderToStaticMarkup } = require("react-dom/server");
function component(name) {
  const filename = fileURLToPath(new URL(`../src/components/${name}.jsx`, import.meta.url));
  const result = buildSync({ entryPoints: [filename], bundle: true, write: false, platform: "node", format: "cjs", jsx: "automatic", loader: { ".css": "empty" }, external: ["react", "react-dom", "react/jsx-runtime"] });
  const mod = new Module(filename); mod.paths = Module._nodeModulePaths(fileURLToPath(new URL("..", import.meta.url)));
  mod._compile(result.outputFiles[0].text, filename); return mod.exports.default;
}
const Card = component("PlayerCard"), Experience = component("RatingExperience");
const render = (p) => renderToStaticMarkup(React.createElement(Card, { player: p }));

test("actual Python raw pipeline -> serializer -> parser -> rendered card", () => {
  const output = execFileSync("python", ["-B", "-c", "from scripts.preview_rating_pipeline import demonstration; from src.rating_delivery import serialize_delivery; print(serialize_delivery(demonstration()),end='')"], { cwd: fileURLToPath(new URL("../..", import.meta.url)), encoding: "utf8" });
  assert.deepEqual(parseRatingDelivery(parseRatingJson(output)), fixture());
  const players = ratingPlayers(parseRatingJson(output)), html = render(players[0]);
  assert.match(html, /Synthetic Actor 1/); assert.match(html, /SYNTHETIC \/ NOT PRODUCTION RATINGS/);
  assert.match(html, /Percentile: 25/); assert.match(html, /53\.381049/);
  assert.match(html, /line_breaking_policy_pending/); assert.doesNotMatch(html, /NaN|Clearances/);
  assert.equal((html.match(/class="dot"/g) || []).length, 4);
  assert.doesNotMatch(html, /class="shape"/);
});

test("synthetic cross-league transfer flows through Python, parser and card", () => {
  const script = [
    "import sys; sys.path.insert(0,'tests')",
    "import pandas as pd",
    "from test_rating_pipeline import transfer_fixture",
    "from scripts.preview_rating_pipeline import fixture",
    "from src.transfer_aggregation import aggregate_transfer",
    "from src.rating_pipeline import transfer_inputs, synthetic_rating_delivery",
    "from src.rating_delivery import serialize_delivery",
    "f=fixture(); rows,policy=transfer_fixture(13286,True); r=aggregate_transfer(rows,policy=policy)",
    "pop,metrics,actions=transfer_inputs(r,evidence=f['pool'].coverage_evidence,press_evidence=f['evidence'])",
    "for key,frame in [('population',pop),('measurements',metrics),('actions',actions)]: f[key]=pd.concat([f[key],frame],ignore_index=True)",
    "f['names'][r['context']]='Synthetic transfer actor'; f['transfers']=[r]",
    "print(serialize_delivery(synthetic_rating_delivery(**f)),end='')",
  ].join("\n");
  const output = execFileSync("python", ["-B", "-c", script], { cwd: fileURLToPath(new URL("../..", import.meta.url)), encoding: "utf8" });
  const p = ratingPlayers(parseRatingJson(output))[0];
  assert.equal(p.player_id, "13286"); assert.equal(p.minutes, 900);
  assert.deepEqual(p.contexts.map((c) => c.competition_name), ["Ligue 1", "Premier League"]);
  assert.deepEqual(p.contexts.map((c) => c.team), ["Lorient", "Sunderland"]);
  assert.match(render(p), /Synthetic transfer actor/); assert.match(render(p), /SYNTHETIC \/ NOT PRODUCTION RATINGS/);
});

test("local mode defaults remain unchanged; new loader is explicit", async () => {
  assert.equal(playerDataMode(undefined), "demo"); assert.equal(playerDataMode("rating-preview"), "rating-preview");
  const calls = [];
  const result = await loadPlayerExperience("rating-preview", { "rating-preview": async () => { calls.push("preview"); return 1; }, demo: () => { throw Error("demo fallback"); } });
  assert.equal(result, 1); assert.deepEqual(calls, ["preview"]);
});

test("preview empty state carries warning and no synthetic scouting results", () => {
  const html = renderToStaticMarkup(React.createElement(Experience, { theme: "dark", onToggle() {} }));
  assert.match(html, /No rating delivery imported/); assert.match(html, /SYNTHETIC \/ NOT PRODUCTION RATINGS/);
  assert.match(html, /type="file"/); assert.doesNotMatch(html, /Synthetic Actor|Demo OVR/);
});

test("missing line-breaking and OVR remain N/A; precise labels round only at display", () => {
  const p = ratingPlayers(fixture())[0], card = ratingCard(p);
  assert.equal(card.attributes[0].value, 53.38104996137775); assert.equal(card.attributes[0].text, "53");
  assert.equal(card.attributes[4].value, null); assert.equal(card.attributes[4].text, "N/A"); assert.equal(card.ovr, null);
});

function withRank(rating, percentile) {
  const d = fixture(), p = d.players[0];
  for (const a of Object.values(p.attributes)) if (a.rating !== null) a.percentile = 0;
  p.attributes.tackles.rating = rating; p.attributes.tackles.percentile = percentile;
  p.archetype = { attribute_id: percentile >= 75 ? "tackles" : null, tier: percentile >= 90 ? "Gold" : percentile >= 75 ? "Silver" : null };
  return d;
}
for (const [rating, percentile, tier] of [[95, 40, null], [60, 96, "+"], [99, 74.999, null], [60, 75, "−"], [60, 89.999, "−"], [60, 90, "+"]]) {
  test(`rating ${rating} / percentile ${percentile}: tier ${tier}`, () => {
    const p = ratingPlayers(withRank(rating, percentile))[0];
    assert.equal(ratingCard(p).archetype.tier, tier);
    assert.equal(ratingCard(p).attributes[0].value, rating);
  });
}

const invalid = {
  "production envelope": (d) => { d.production_ready = true; },
  "publication authorization": (d) => { d.publication_authorized = true; },
  "verified display label": (d) => { d.players[0].classification = "verified"; },
  "diagnostic display label": (d) => { d.players[0].classification = "diagnostic"; },
  "approved scoring label": (d) => { d.players[0].eligibility.scoring_approved = true; },
  "verified exposure on synthetic": (d) => { d.players[0].eligibility.season_exposure_verified = true; },
  "wrong season": (d) => { d.players[0].season_name = "2023/2024"; },
  "wrong role": (d) => { d.players[0].role_group = "GK"; },
  "wrong cohort": (d) => { d.players[0].cohort_id = "other"; },
  "wrong pool": (d) => { d.players[0].attributes.tackles.comparison_pool = "other"; },
  "duplicate identity": (d) => { d.players.push(structuredClone(d.players[0])); },
  "unsafe numeric ID": (d) => { d.players[0].player_id = 900000001; },
  "noncanonical ID": (d) => { d.players[0].player_id = "0900000001"; },
  "missing attribute": (d) => { delete d.players[0].attributes.recoveries; },
  "NaN": (d) => { d.players[0].attributes.tackles.rating = NaN; },
  "boolean rating": (d) => { d.players[0].attributes.tackles.rating = true; },
  "invalid percentile": (d) => { d.players[0].attributes.tackles.percentile = 101; },
  "invented OVR": (d) => { d.players[0].overall.rating = 65; },
  "contradictory appearances": (d) => { d.players[0].eligibility.contradictory_sample_appearance_ids = ["1"]; },
  "missing policy": (d) => { d.players[0].attributes.tackles.policy = null; },
  "missing source": (d) => { d.players[0].provenance = []; },
  "missing match window": (d) => { d.players[0].contexts[0].match_ids = []; },
  "withheld numeric": (d) => { d.players[0].attributes.tackles.status = "withheld"; },
  "invented fifth score": (d) => { d.players[0].attributes.line_breaking_passes = structuredClone(d.players[0].attributes.tackles); },
  "rating inferred from scorecard schema": (d) => { d.schema_version = "soccer-scorecard/v1"; },
  "rating inferred from diagnostic schema": (d) => { d.schema_version = "soccer-provisional-profiles/v1"; },
};
for (const [name, mutate] of Object.entries(invalid)) test(`contract rejects ${name}`, () => {
  const d = fixture(); mutate(d); assert.throws(() => parseRatingDelivery(d), /Invalid rating delivery/);
});

test("exact int64 identity and same names stay separately searchable", () => {
  const d = fixture(); d.players[0].player_id = "9223372036854775807"; d.players[1].name = d.players[0].name;
  const rows = ratingPlayers(d); assert.equal(rows[0].player_id, "9223372036854775807"); assert.notEqual(rows[0].id, rows[1].id);
});

test("returned model is independent and object-key ordering is irrelevant", () => {
  const d = fixture(), before = structuredClone(d), p = ratingPlayers(d);
  p[0].attributes.tackles.rating = 1; assert.deepEqual(d, before);
  const reverse = (x) => Array.isArray(x) ? x.map(reverse) : x && typeof x === "object" ? Object.fromEntries(Object.entries(x).reverse().map(([k, v]) => [k, reverse(v)])) : x;
  assert.doesNotThrow(() => parseRatingDelivery(reverse(d)));
});

test("duplicate JSON keys including escaped keys reject", () => {
  assert.throws(() => parseRatingJson('{"a":1,"a":2}'), /duplicate JSON key/);
  assert.throws(() => parseRatingJson('{"a":1,"\\u0061":2}'), /duplicate JSON key/);
  assert.deepEqual(parseRatingJson('{"a":[{},[],{"b":"}\\\""}]}'), { a: [{}, [], { b: '}"' }] });
});

test("local file reader validates and rejects missing/oversized/malformed imports", async () => {
  assert.equal((await readRatingFile({ size: 100, text: async () => JSON.stringify(fixture()) })).length, 8);
  await assert.rejects(readRatingFile(null));
  await assert.rejects(readRatingFile({ size: 6 * 1024 * 1024, text: async () => "{}" }));
  await assert.rejects(readRatingFile({ size: 100, text: async () => "<html>" }));
});

test("rating import failure cannot load demo data", async () => {
  await assert.rejects(loadPlayerExperience("rating-preview", { "rating-preview": () => Promise.reject(Error("bad import")), demo: () => { throw Error("unexpected fallback"); } }), /bad import/);
});
