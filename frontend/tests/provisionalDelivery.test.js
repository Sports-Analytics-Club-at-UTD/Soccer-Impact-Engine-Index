import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createRequire, Module } from "node:module";
import { fileURLToPath } from "node:url";
import { parseProvisionalDelivery, provisionalPlayers, loadProvisionalPlayers, minutes } from "../src/lib/provisionalDelivery.js";
import { parseRatingDelivery } from "../src/lib/ratingDelivery.js";
import { playerDataMode, loadPlayerExperience } from "../src/lib/playerDataMode.js";

const fixture = () => JSON.parse(readFileSync(new URL("./fixtures/syntheticProvisional.json", import.meta.url), "utf8"));
const require = createRequire(import.meta.url), { buildSync } = require("esbuild");
const React = require("react"), { renderToStaticMarkup } = require("react-dom/server");
function component(name) {
  const filename = fileURLToPath(new URL(`../src/components/${name}.jsx`, import.meta.url));
  const result = buildSync({ entryPoints: [filename], bundle: true, write: false, platform: "node", format: "cjs", jsx: "automatic", loader: { ".css": "empty" }, logLevel: "silent", external: ["react", "react-dom", "react/jsx-runtime"] });
  const mod = new Module(filename); mod.paths = Module._nodeModulePaths(fileURLToPath(new URL("..", import.meta.url)));
  mod._compile(result.outputFiles[0].text, filename); return mod.exports.default;
}
const Card = component("PlayerCard"), Experience = component("ProvisionalExperience");
const render = (p) => renderToStaticMarkup(React.createElement(Card, { player: p }));

test("Python synthetic contract -> parser -> existing PlayerCard extension", () => {
  const output = execFileSync("python", ["-B", "-c", "import sys,json; sys.path.insert(0,'tests'); from synthetic_provisional import synthetic; from src.provisional_delivery import validate_delivery; print(json.dumps(validate_delivery(synthetic())))"], { cwd: fileURLToPath(new URL("../..", import.meta.url)), encoding: "utf8" });
  const d = JSON.parse(output); assert.deepEqual(parseProvisionalDelivery(d), fixture());
  const html = render(provisionalPlayers(d)[0]);
  assert.match(html, /LIMITED DATA/); assert.match(html, /PARTIAL SEASON/);
  assert.match(html, /50%/); assert.match(html, /1 successful \/ 2 pressured actions/);
  assert.match(html, /fewer than 40 actions; measured value retained/);
  assert.match(html, /0 per90/); assert.match(html, /Rating: <b>N\/A<\/b>/);
  assert.match(html, /Excluded appearances: 12/); assert.match(html, /SHA256/);
  assert.doesNotMatch(html, /class="shape"|Demo OVR|Fictional percentile|Gold|Silver/);
});

test("zero attempts is N/A; successful zero over positive attempts stays zero", () => {
  const d = fixture(); d.players[0].attributes.press_resistance.observation = null;
  d.players[0].bundesliga_sample.press_attempts = null; d.players[0].bundesliga_sample.press_successes = null;
  assert.match(render(provisionalPlayers(d)[0]), /Observed: <strong>N\/A<\/strong>/);
  const zero = fixture(), o = zero.players[0].attributes.press_resistance.observation;
  Object.assign(o, { successes: 0, pass_successes: 0, value: 0 });
  zero.players[0].bundesliga_sample.press_successes = 0;
  assert.match(render(provisionalPlayers(zero)[0]), /0%/);
  o.attempts = 0; assert.throws(() => parseProvisionalDelivery(zero), /press counts/);
});

test("40-action boundary is explicit and no observations are imputed", () => {
  for (const count of [1,39,40]) {
    const d = fixture(), o = d.players[0].attributes.press_resistance.observation;
    Object.assign(o, { attempts: count, pass_attempts: count, successes: 0, pass_successes: 0, value: 0, at_least_40: count >= 40 });
    Object.assign(d.players[0].bundesliga_sample, { press_attempts: count, press_successes: 0 });
    const html = render(provisionalPlayers(d)[0]);
    assert.match(html, count >= 40 ? /At least 40 actions observed/ : /fewer than 40 actions/);
  }
  const d = fixture(); d.players[0].attributes.tackles.observation = null;
  assert.equal(provisionalPlayers(d)[0].attributes.tackles.observation, null);
});

test("duplicate identities and overlapping transfer fixture scopes fail closed", () => {
  const d = fixture(); d.players.push(structuredClone(d.players[0]));
  assert.throws(() => parseProvisionalDelivery(d), /duplicate canonical/);
  const overlap = fixture(); overlap.players[0].contexts.push({ team: "Invented Other Club", competition_name: "La Liga", match_ids: ["11"] });
  assert.throws(() => parseProvisionalDelivery(overlap), /overlapping transfer fixture/);
});

test("loader handles success, bad response and duplicate JSON without demo fallback", async () => {
  const players = await loadProvisionalPlayers({ fetchImpl: async () => ({ ok: true, text: async () => JSON.stringify(fixture()) }) });
  assert.equal(players.length, 1);
  await assert.rejects(loadProvisionalPlayers({ fetchImpl: async () => ({ ok: false, status: 404 }) }), /unavailable/);
  await assert.rejects(loadProvisionalPlayers({ fetchImpl: async () => ({ ok: true, text: async () => '{"schema_version":1,"schema_version":2}' }) }), /duplicate JSON key/);
  assert.match(renderToStaticMarkup(React.createElement(Experience)), /Loading match observations/);
});

test("new mode is opt-in; existing defaults remain stable", async () => {
  assert.equal(playerDataMode(undefined), "demo"); assert.equal(playerDataMode("limited-data"), "limited-data");
  assert.equal(await loadPlayerExperience("limited-data", { "limited-data": () => "provisional", demo: () => assert.fail() }), "provisional");
});
