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

// Explicit invented nonpublication-shaped bytes; no real observations.
const original = Buffer.from('{"schema_version":"soccer-local-experimental-synthetic-denial/v0","players":[{"id":"synthetic:denied"}],"publication_authorized":false}');
test('normal production build admits demo/static assets and no nonpublication data', async () => {
  await build({ root: FRONTEND_ROOT, configFile: resolve(FRONTEND_ROOT, 'vite.config.js'), logLevel: 'silent', build: { outDir: normal, emptyOutDir: false } });
  const files = await verifyProductionDirectory(normal);
  assert.ok(files.includes('index.html'));
  assert.ok(!files.some((p) => /bundesliga|\.jsonl?$|\.parquet$|\.gitkeep$/.test(p)));
  const javascript = (await Promise.all(files.filter((p) => p.endsWith('.js')).map((p) => readFile(join(normal, p), 'utf8')))).join('\n');
  assert.match(javascript, /Marcus Delacroix/); // Real demo contents, not merely an empty build.
  assert.doesNotMatch(javascript, /Browse verified 2015\/16 Bundesliga observations/);
  assert.doesNotMatch(javascript, /five-attribute-experimental|\/__local_experimental\/five-attributes|soccer-ovr-formula-b\/v1/);
  assert.doesNotMatch(javascript, /classification scope pending|Component classifications are withheld pending team|Badges are shown only for strictly eligible real-player profiles/);
  assert.doesNotMatch(javascript, /unified-destinations|First player-season|Player data unavailable/);
  for (const p of PUBLIC_ASSETS) assert.equal(sha(await readFile(join(normal, p.path))), p.sha256);
});

test('single-file sharing build has the same admission boundary', async () => {
  await build({ root: FRONTEND_ROOT, configFile: resolve(FRONTEND_ROOT, 'vite.single.config.js'), logLevel: 'silent', build: { outDir: single, emptyOutDir: false } });
  const files = await verifyProductionDirectory(single);
  assert.ok(!files.some((p) => p.endsWith('.json')));
  const html = await readFile(join(single, 'index.html'), 'utf8');
  assert.match(html, /Marcus Delacroix/);
  assert.doesNotMatch(html, /soccer-ovr-formula-b\/v1|\/__local_experimental\/five-attributes/);
  assert.doesNotMatch(html, /classification scope pending|Component classifications are withheld pending team|Badges are shown only for strictly eligible real-player profiles/);
  assert.doesNotMatch(html, /unified-destinations|First player-season|Player data unavailable/);
});

test('actual production preview serves demo assets but no observation or private score JSON', async () => {
  const server = await preview({ root: FRONTEND_ROOT, configFile: resolve(FRONTEND_ROOT, 'vite.config.js'), build: { outDir: normal },
    logLevel: 'silent', preview: { host: '127.0.0.1', port: 0, strictPort: true, open: false } });
  try {
    const base = `http://127.0.0.1:${server.httpServer.address().port}`;
    for (const path of ['/data/bundesliga-observations.json', '/__local_experimental/five-attributes', '/?view=five-attribute-experimental']) {
      const response = await fetch(base + path), text = await response.text();
      assert.ok(!response.headers.get('content-type')?.includes('application/json'));
      assert.notEqual(sha(text), sourceHash);
      assert.doesNotMatch(text, /"players"|"ovr_integration"|soccer-provisional-observations/);
    }
    assert.equal((await fetch(base + '/')).status, 200);
    for (const p of PUBLIC_ASSETS) {
      const response = await fetch(base + '/' + p.path);
      assert.equal(response.status, 200); assert.equal(sha(Buffer.from(await response.arrayBuffer())), p.sha256);
    }
    const font = (await verifyProductionDirectory(normal)).find((p) => p.endsWith('.woff2'));
    const response = await fetch(base + '/' + font); assert.equal(response.status, 200); await response.arrayBuffer();
  } finally { await new Promise((resolve, reject) => server.httpServer.close((e) => e ? reject(e) : resolve())); }
});

test('future public data is excluded even with self-declared approval and environment flags', async () => {
  const f = await fixture('console.log("demo fixture");');
  await writeFile(join(f.root, 'public/future-player-data.json'), JSON.stringify({ publication_authorized: true, players: [{ name: 'Unreviewed real player' }] }));
  const old = process.env.VITE_ALLOW_REAL_PLAYER_DATA;
  process.env.VITE_ALLOW_REAL_PLAYER_DATA = 'true';
  try { await build(f.options); } finally {
    if (old === undefined) delete process.env.VITE_ALLOW_REAL_PLAYER_DATA; else process.env.VITE_ALLOW_REAL_PLAYER_DATA = old;
  }
  assert.ok(!(await verifyProductionDirectory(f.outDir)).some((p) => p.endsWith('.json')));
});

test('synthetic unreviewed imports, including raw/url imports, fail before packaging', async () => {
  for (const suffix of ['', '?raw', '?url']) {
    const f = await fixture(`import data from ${JSON.stringify('./unreviewed.json' + suffix)}; console.log(data);`);
    await writeFile(join(f.root, 'unreviewed.json'), original);
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

test('synthetic renamed duplicate and minified JS payloads cannot pass output admission', async () => {
  for (const [fileName, bytes] of [['assets/picture.bin', original], ['assets/records.js', `console.log(${JSON.stringify(JSON.parse(original))});`]]) {
    const f = await fixture('console.log("demo");', [{ name: 'inject-unapproved-copy', generateBundle() { this.emitFile({ type: 'asset', fileName, source: bytes }); } }]);
    await assert.rejects(build(f.options), /Production data admission denied/);
  }
  assert.throws(() => assertAdmittedOutput('assets/font.woff2', Buffer.from('{"players":[]}')), /invalid font payload/);
});

test('synthetic final on-disk inspection rejects data copied after bundle generation', async () => {
  const f = await fixture('console.log("demo");', [{ name: 'late-copy', async writeBundle(options) {
    await writeFile(join(options.dir, 'innocent-name.json'), original);
  } }]);
  await assert.rejects(build(f.options), /Production data admission denied/);
});
