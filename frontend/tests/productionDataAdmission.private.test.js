// Authorized-private suite: absent evidence must fail, never substitute.
import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, readFile, writeFile, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { basename, join, resolve, relative, isAbsolute } from 'node:path';
import { build, createServer, preview } from 'vite';
import admission, { FRONTEND_ROOT, PUBLIC_ASSETS, verifyProductionDirectory, assertAdmittedOutput } from '../build/productionDataAdmission.js';
import { parseExperimentalDelivery, experimentalModels } from '../src/dev/experimentalDelivery.js';
import { ovrLeaderboard } from '../src/dev/provisionalOvr.js';
import { provisionalPlayers } from '../src/lib/provisionalDelivery.js';

const temporary = await mkdtemp(join(tmpdir(), 'sac-admission-'));
after(async () => {
  const target = await realpath(temporary), parent = await realpath(tmpdir()), rel = relative(parent, target);
  if (isAbsolute(rel) || rel.startsWith('..') || !basename(target).startsWith('sac-admission-')) throw Error('Unsafe test cleanup target');
  await rm(target, { recursive: true, force: true });
});
const source = resolve(FRONTEND_ROOT, 'public/data/bundesliga-observations.json');
const original = await readFile(source);
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const sourceHash = '9b6f0a5dd35782e5f6798e6521c5bab126466ca7b320dd7d54e8a38aad086b86';
let sequence = 0;
async function fixture(code, plugins = []) {
  const root = join(temporary, `fixture-${sequence++}`);
  await mkdir(join(root, 'public'), { recursive: true });
  await writeFile(join(root, 'entry.js'), code);
  const outDir = join(root, 'output');
  return { root, outDir, options: { root, configFile: false, plugins: [...plugins, admission()], logLevel: 'silent',
    build: { outDir, emptyOutDir: false, rollupOptions: { input: join(root, 'entry.js') } } } };
}
const normal = join(temporary, 'normal');
const single = join(temporary, 'single');

test('renamed duplicate and minified JS payloads cannot pass output admission', async () => {
  for (const [fileName, bytes] of [['assets/picture.bin', original], ['assets/records.js', `console.log(${JSON.stringify(JSON.parse(original))});`]]) {
    const f = await fixture('console.log("demo");', [{ name: 'inject-unapproved-copy', generateBundle() { this.emitFile({ type: 'asset', fileName, source: bytes }); } }]);
    await assert.rejects(build(f.options), /Production data admission denied/);
  }
  assert.throws(() => assertAdmittedOutput('assets/font.woff2', Buffer.from('{"players":[]}')), /invalid font payload/);
});

test('final on-disk inspection rejects data copied after bundle generation', async () => {
  const f = await fixture('console.log("demo");', [{ name: 'late-copy', async writeBundle(options) {
    await writeFile(join(options.dir, 'innocent-name.json'), original);
  } }]);
  await assert.rejects(build(f.options), /Production data admission denied/);
});

test('local development retains observations, Formula B, identities, provenance and strict ranks', async () => {
  // This HTTP harness fetches HTML/data, not browser module imports. Avoid
  // leaving speculative module-warmup requests pending during Vite shutdown.
  const server = await createServer({ root: FRONTEND_ROOT, configFile: resolve(FRONTEND_ROOT, 'vite.config.js'), logLevel: 'silent',
    optimizeDeps: { noDiscovery: true }, server: { host: '127.0.0.1', port: 5175, strictPort: false, open: false, preTransformRequests: false } });
  try {
    await server.listen();
    const base = `http://127.0.0.1:${server.httpServer.address().port}`;
    const response = await fetch(base + '/data/bundesliga-observations.json');
    const bytes = Buffer.from(await response.arrayBuffer()); assert.equal(sha(bytes), sourceHash);
    const observations = provisionalPlayers(JSON.parse(bytes.toString()));
    assert.equal(observations.length, 346); assert.equal(observations.filter((p) => p.bundesliga_candidate).length, 138);
    const r = await fetch(base + '/__local_experimental/five-attributes');
    assert.equal(r.status, 200); assert.equal(r.headers.get('cache-control'), 'no-store');
    const data = await parseExperimentalDelivery(await r.text()), players = experimentalModels(data);
    assert.equal(players.length, 691); assert.equal(players.filter((p) => p.ovr.value !== null).length, 686);
    assert.equal(ovrLeaderboard(players, 'MID').length, 124); assert.equal(ovrLeaderboard(players, 'CB').length, 107);
    const frozen = new Map((await readFile(resolve(FRONTEND_ROOT, '../data/derived/private-ovr-comparison-v1/player-comparison.jsonl'), 'utf8')).trim().split('\n').map((s) => { const p = JSON.parse(s); return [p.id, p.private_ovr_comparison.dynamic]; }));
    for (const p of players) { assert.equal(p.ovr.value, frozen.get(p.id)); assert.ok(p.presentation.provenance.length); }
    assert.equal(players.find((p) => p.presentation.player_id === '3103').presentation.clubs.length, 2);
    for (const id of ['34558', '22824', '3500']) assert.equal(players.find((p) => p.presentation.player_id === id).ovr.eligible, false);
    for (const path of ['/', '/?view=limited-data', '/?view=five-attribute-experimental']) {
      const r = await fetch(base + path); assert.equal(r.status, 200); assert.match(await r.text(), /<div id="root">/);
    }
    assert.equal(sha(await readFile(source)), sourceHash);
  } finally { server.httpServer.closeAllConnections(); await server.close(); }
});

test('imports of nonpublication data, including raw/url imports, fail before packaging', async () => {
  for (const suffix of ['', '?raw', '?url']) {
    const f = await fixture(`import data from ${JSON.stringify(source.replaceAll('\\', '/') + suffix)}; console.log(data);`);
    await assert.rejects(build(f.options), /Production data admission denied/);
  }
  const f = await fixture('import data from "./approved-looking.json"; console.log(data);');
  await writeFile(join(f.root, 'approved-looking.json'), '{"publication_authorized":true,"players":[]}');
  await assert.rejects(build(f.options), /unreviewed structured-data import/);
  for (const extension of ['yaml', 'json5', 'txt', 'bin']) {
    const f = await fixture(`import data from './future.${extension}?raw'; console.log(data);`);
    await writeFile(join(f.root, `future.${extension}`), 'unreviewed player observations');
    await assert.rejects(build(f.options), /unreviewed source asset import/);
  }
});
