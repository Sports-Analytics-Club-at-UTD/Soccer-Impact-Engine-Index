import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { parsePublicRatings, publicModels, loadPublicRatings } from '../src/lib/publicRatingsDelivery.js';
import { PUBLIC_RATINGS_RELEASE as release } from '../src/lib/publicRatingsRelease.js';
import { ovrLeaderboard } from '../src/lib/provisionalOvr.js';
import { filterExperimentalPlayers } from '../src/lib/playerDiscovery.js';
import { assertAdmittedOutput, validateDataImport } from '../build/productionDataAdmission.js';
const bytes = await readFile(new URL(`../public/${release.path}`, import.meta.url));
const data = parsePublicRatings(bytes.toString('utf8')), models = publicModels(data);

test('reviewed release retains all final values, badge decisions and strict leaderboards', () => {
  assert.equal(bytes.length, release.bytes);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), release.sha256);
  for (const [name, value] of [['Kanté','83.08'],['Toni Kroos','77.00'],['Kalidou Koulibaly','82.42'],['Sereso Geoffroy Gonzaroua Dié','92.00']]) {
    const p = models.find((p) => p.name.includes(name)); assert.ok(p, name); assert.equal(p.ovr.value.toFixed(2), value);
  }
  assert.equal(models.length, 691); assert.equal(models.filter((p) => p.ovr.value === null).length, 5);
  for (const [group, count] of [['MID',124],['CB',107]]) {
    const rows = ovrLeaderboard(models, group); assert.equal(rows.length, count);
    assert.ok(rows.every((p,i) => !i || rows[i-1].ovr.value >= p.ovr.value));
  }
  const die = models.find((p) => p.name.includes('Sereso Geoffroy Gonzaroua Dié'));
  assert.equal(die.ovr.eligible,false); assert.equal(die.componentClassification.status,'withheld');
  assert.ok(!ovrLeaderboard(models,'MID').includes(die));
  const kante = filterExperimentalPlayers(models, {query:'kante'})[0];
  assert.ok(kante.name.includes('Kanté'));
  assert.equal(filterExperimentalPlayers(models,{query:'Marcus Delacroix'}).length,0);
  for (const p of models) for (const [id, a] of Object.entries(p.presentation.attributes)) {
    assert.equal(p.componentClassification.tiers[id], !p.presentation.badge_eligible ? null : a.percentile >= 90 ? 'Gold' : a.percentile >= 75 ? 'Silver' : 'Standard');
  }
});

test('public contract excludes research and rejects changed ratings or eligibility', () => {
  assert.doesNotMatch(bytes.toString(), /raw_counts|match_ids|member_ids|manifest_sha256|source_package|reference_fingerprint|position_seconds|exact_value|403c1d9ab93def/);
  for (const mutate of [
    (d) => { d.players[0].attributes.tackles.rating += 1; },
    (d) => { d.players[0].raw_counts = {}; },
    (d) => { d.players.find((p) => !p.ovr.eligible).ovr.eligible = true; },
    (d) => { d.players[0].badge_eligible = !d.players[0].badge_eligible; },
  ]) { const changed = structuredClone(data); mutate(changed); assert.throws(() => parsePublicRatings(JSON.stringify(changed)), /Invalid public ratings/); }
});

test('public HTTP loader validates MIME and exact bytes without demo fallback', async () => {
  assert.equal((await loadPublicRatings({fetcher: async () => new Response(bytes,{headers:{'content-type':'application/json'}})})).players.length,691);
  for (const response of [new Response('<html>fallback</html>',{headers:{'content-type':'text/html'}}), new Response('{}',{headers:{'content-type':'application/json'}}), new Response('missing',{status:404})]) {
    await assert.rejects(loadPublicRatings({fetcher: async () => response}), /Invalid public ratings/);
  }
});

test('release admission is restricted to exact reviewed path and content', async () => {
  assert.doesNotThrow(() => assertAdmittedOutput(release.path,bytes));
  assert.throws(() => assertAdmittedOutput('data/renamed-ratings.json',bytes), /admission denied/);
  assert.throws(() => assertAdmittedOutput(release.path, Buffer.concat([bytes,Buffer.from(' ')])), /admission denied/);
  for (const suffix of ['', '?raw','?url']) await validateDataImport(new URL(`../public/${release.path}`, import.meta.url).pathname.replace(/^\/([A-Z]:)/,'$1') + suffix);
});


test('Vercel uses the guarded Vite build and version-specific static cache policy', async () => {
  const config = JSON.parse(await readFile(new URL('../vercel.json', import.meta.url), 'utf8'));
  assert.equal(config.framework,'vite'); assert.equal(config.buildCommand,'npm run build'); assert.equal(config.outputDirectory,'dist');
  assert.deepEqual(config.headers, [{source: '/' + release.path, headers: [
    {key:'Cache-Control',value:'public, max-age=31536000, immutable'}, {key:'X-Content-Type-Options',value:'nosniff'},
  ]}]);
  assert.equal(config.rewrites,undefined);
});
