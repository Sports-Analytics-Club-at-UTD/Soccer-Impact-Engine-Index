import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire, Module } from 'node:module';
import { fileURLToPath } from 'node:url';
import { parsePublicRatings, publicModels, loadPublicRatings } from '../src/lib/publicRatingsDelivery.js';
// Historical v2 sample regressions remain fixed when the current release advances.
const release = {path:'data/player-ratings-2015-16-v2.json',bytes:1448401,
  sha256:'e9fe1b6f3ca825eb8c961fea484ba08eed95d87c2cf8958f23303683d627e39d'};
import { foundationPlayers } from '../src/lib/foundationPlayers.js';
import { ovrLeaderboard } from '../src/lib/provisionalOvr.js';

const bytes = readFileSync(new URL(`../public/${release.path}`, import.meta.url));
const data = parsePublicRatings(bytes.toString('utf8'));
const byId = (id) => data.players.find((p) => p.player_id === String(id));

test('rebuilt release has exact pinned bytes, uniform supported-sample eligibility and complete population', () => {
  assert.equal(data.schema_version, 'soccer-public-ratings/v2');
  assert.equal(data.eligibility_version, 'supported-sample-five-attributes/v1');
  assert.equal(bytes.length, release.bytes);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), release.sha256);
  assert.equal(data.players.length, 691);
  for (const p of data.players) {
    assert.equal(p.coverage.supported_fixtures + p.coverage.unresolved_fixtures, p.coverage.observed_fixtures);
    assert.equal(p.ovr.eligible, p.badge_eligible);
    if (p.ovr.eligible) {
      assert.ok(p.coverage.supported_minutes >= 900);
      assert.ok(p.attributes.press_resistance.coverage.pressure_attempts >= 40);
      for (const [id, a] of Object.entries(p.attributes)) {
        assert.ok(a.rating !== null);
        if (id !== 'press_resistance') assert.ok(a.coverage.supported_minutes >= 900);
      }
    }
  }
  const models = publicModels(data);
  for (const group of ['MID', 'CB']) {
    const rows = ovrLeaderboard(models, group);
    assert.ok(rows.length > (group === 'MID' ? 124 : 107));
    assert.ok(rows.every((p, i) => !i || rows[i - 1].ovr.value >= p.ovr.value));
  }
});

test('Busquets retains 34 verified minute samples and pressure actions from all 35 matches', () => {
  const p = byId(5203);
  assert.equal(p.ovr.eligible, true); assert.equal(p.badge_eligible, true);
  assert.equal(p.coverage.observed_fixtures, 35); assert.equal(p.coverage.supported_fixtures, 34);
  assert.ok(Math.abs(p.coverage.supported_minutes - 2912.4612166666666) < 1e-9);
  assert.equal(p.attributes.tackles.coverage.supported_fixtures, 34);
  assert.equal(p.attributes.tackles.coverage.excluded_fixtures, 1);
  assert.equal(p.attributes.press_resistance.coverage.supported_fixtures, 35);
  assert.equal(p.attributes.press_resistance.coverage.pressure_attempts, 357);
});

test('Ramos is accepted after verified dismissals without inventing minutes', () => {
  const p = byId(5201);
  assert.equal(p.ovr.eligible, true); assert.equal(p.badge_eligible, true);
  assert.equal(p.coverage.observed_fixtures, 23); assert.equal(p.coverage.supported_fixtures, 23);
  assert.ok(Math.abs(p.coverage.supported_minutes - 2010.5565) < 1e-9);
});

test('disputed observations remain disclosed and cannot grant eligibility below metric minimums', () => {
  assert.ok(byId(7435).attributes.press_resistance.coverage.excluded_fixtures >= 1);
  const d = structuredClone(data), p = d.players.find((p) => p.ovr.eligible);
  p.attributes.recoveries.coverage.supported_minutes = 899;
  assert.throws(() => parsePublicRatings(JSON.stringify(d)), /supported-sample policy/);
  const changed = structuredClone(data), q = changed.players.find((p) => p.ovr.eligible);
  q.attributes.press_resistance.coverage.pressure_attempts = 39;
  assert.throws(() => parsePublicRatings(JSON.stringify(changed)), /supported-sample policy/);
});

test('public projection contains aggregate coverage, with no original event or research payloads', () => {
  assert.doesNotMatch(bytes.toString(), /numerator_ids|denominator_ids|match_ids|member_ids|raw_counts|source_sha256|identity_names|position_seconds|exact_value|source_package/);
});

test('rebuilt player cards explain supported coverage and retain keyboard access', () => {
  const require = createRequire(import.meta.url), React = require('react');
  const { renderToStaticMarkup } = require('react-dom/server');
  const filename = fileURLToPath(new URL('../src/components/PlayerCard.jsx', import.meta.url));
  const bundled = require('esbuild').buildSync({entryPoints:[filename], bundle:true, write:false,
    platform:'node', format:'cjs', jsx:'automatic', logLevel:'silent', external:['react','react/jsx-runtime']});
  const mod = new Module(filename); mod.filename = filename; mod.paths = Module._nodeModulePaths(fileURLToPath(new URL('../', import.meta.url)));
  mod._compile(bundled.outputFiles[0].text, filename);
  const player = foundationPlayers(data).find((p) => p.id === '5203:2015/2016');
  const html = renderToStaticMarkup(React.createElement(mod.exports.default,{player}));
  assert.doesNotMatch(html, /matches backing these minutes/);
  assert.match(html, /35 recorded matches/);
  assert.match(html, /34 of 35 recorded matches included/);
  assert.match(html, /357 supported actions under pressure/);
  assert.match(html, /Included in the position rankings/);
  assert.match(html, /tabindex="0"/);
});

test('HTTP loading rejects a changed supported-sample release', async () => {
  const changed = Buffer.concat([bytes, Buffer.from(' ')]);
  await assert.rejects(loadPublicRatings({fetcher:async () => new Response(changed,{headers:{'content-type':'application/json'}})}), /release fingerprint/);
});
