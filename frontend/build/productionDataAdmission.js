// Build-time admission only. This module is never imported by browser code.
// Only the explicitly reviewed public final-ratings release is admitted.
// Environment flags and self-declared payload booleans cannot add authority.
import { PUBLIC_RATINGS_RELEASE } from '../src/lib/publicRatingsRelease.js';
import { createHash } from 'node:crypto';
import { lstat, readFile, readdir, realpath } from 'node:fs/promises';
import { basename, dirname, extname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const FRONTEND_ROOT = fileURLToPath(new URL('../', import.meta.url));
const REPOSITORY_ROOT = resolve(FRONTEND_ROOT, '..');
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const denied = (reason) => { throw Error(`Production data admission denied: ${reason}`); };

// Existing aggregate team pictures are retained unchanged; this is an asset
// inventory, not certification of their statistical provenance. New static/demo
// assets require explicit path/content review here. Never add private data here.
export const PUBLIC_ASSETS = Object.freeze([
  PUBLIC_RATINGS_RELEASE,
  // About Us portraits supplied for public display.
  { path: 'team/vibhor-rajan.webp', sha256: '332f351b2fbec6b8ef4abfdde62df0efde17e61d4c66e1bd0e18f9b6b7e6e08a' },
  { path: 'team/pratyush-malaviya.webp', sha256: '9e1c95d5b3627f899f22391c0cb3dc02a13d4aee1d2ffd203993011e0095b195' },
  { path: 'team/arpit-gupta.webp', sha256: '4a0c8cfa0dd51589cc728794047cb71d91eaf94749cac62ed3741ff3e1cc5e8c' },
  { path: 'team/ayush-mendhe.webp', sha256: 'c1bfa7c5f2c1661500691c2d35ae1db1357a2f1fa99528a213e835021ba07dfc' },
  { path: 'team/joseph-olutayo.webp', sha256: '628624e750f9c4e916d130235339f8378945f516ed543876fe21864868035fd2' },
  { path: 'team/spatial_Barcelona.png', sha256: '0421ca9ceb2bef7f8b360813a5f36c0c725b34e15bd1da5400fe08e67a6f217b' },
  { path: 'team/spatial_Bayer_Leverkusen.png', sha256: '30bff5b12ab5cd763c651909bf28d7fb5d21b123fb5a9cc9dbe8aa408abeb602' },
  { path: 'team/spatial_Paris_Saint-Germain.png', sha256: '10914ca2b386cc3071af6668f3424577ed10649595ba0c05d73a3538d1bc480e' },
]);
const DEMO_DATA = new Map([
  [resolve(FRONTEND_ROOT, 'src/data/players.json'), '058c8885a893ebd80c92b47e4ae95a4484ad97e82bbe22738591b80be5d5c503'],
  [resolve(FRONTEND_ROOT, 'src/fixtures/syntheticFiveAttributes.json'), '9924967f2441f80524489d96f29058fa2f654dcb842b1d99854876d7e7540e14'],
]);
const FORBIDDEN_HASHES = new Set([
  // Exact original observations, including a renamed/binary copy.
  '9b6f0a5dd35782e5f6798e6521c5bab126466ca7b320dd7d54e8a38aad086b86',
]);
const DATA_EXTENSION = /\.(?:jsonl?|csv|tsv|parquet|arrow|feather|xlsx?|sqlite3?|db|ndjson)$/i;
const CODE_EXTENSION = new Set(['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.css', '.scss', '.sass', '.less', '.styl', '.html']);
const GENERATED_EXTENSION = new Set(['.html', '.js', '.mjs', '.css', '.map', '.woff', '.woff2']);
const within = (parent, path) => {
  const r = relative(parent, path);
  return r === '' || (!r.startsWith('..') && !isAbsolute(r));
};

async function checkedBytes(path, expected) {
  if ((await lstat(path)).isSymbolicLink() || await realpath(path) !== resolve(path)) denied(`symlink asset: ${path}`);
  const bytes = await readFile(path);
  if (digest(bytes) !== expected) denied(`reviewed public asset fingerprint changed: ${path}`);
  return bytes;
}

export async function validateDataImport(id) {
  const path = id.split('?')[0];
  if (!isAbsolute(path)) return; // Rollup virtual modules are not source files.
  const file = resolve(path);
  if (within(resolve(REPOSITORY_ROOT, 'data'), file) || within(resolve(FRONTEND_ROOT, 'src/dev'), file) || within(resolve(FRONTEND_ROOT, 'dev'), file)) {
    denied(`private/development source imported into production: ${file}`);
  }
  if (within(resolve(FRONTEND_ROOT, 'public'), file)) {
    const asset = PUBLIC_ASSETS.find((a) => resolve(FRONTEND_ROOT, 'public', a.path) === file);
    if (!asset) denied(`unreviewed public asset import: ${file}`);
    await checkedBytes(file, asset.sha256);
    return;
  }
  if (DATA_EXTENSION.test(file)) {
    // Dependency package manifests are code metadata, not a data admission path.
    if (file.split(/[\\/]/).includes('node_modules') && basename(file) === 'package.json') return;
    const expected = DEMO_DATA.get(file);
    if (!expected) denied(`unreviewed structured-data import: ${file}`);
    await checkedBytes(file, expected);
    return;
  }
  if (!CODE_EXTENSION.has(extname(file).toLowerCase()) && !['.woff', '.woff2'].includes(extname(file).toLowerCase())) {
    denied(`unreviewed source asset import: ${file}`);
  }
}

export function assertAdmittedOutput(name, input) {
  const bytes = typeof input === 'string' ? Buffer.from(input) : Buffer.from(input);
  const hash = digest(bytes);
  if (FORBIDDEN_HASHES.has(hash)) denied(`unauthorized observations payload in ${name}`);
  const publicAsset = PUBLIC_ASSETS.find((a) => a.path === name.replaceAll('\\', '/'));
  if (publicAsset) {
    if (hash !== publicAsset.sha256) denied(`changed static asset in ${name}`);
    return;
  }
  if (!GENERATED_EXTENSION.has(extname(name).toLowerCase())) denied(`unreviewed distributable file: ${name}`);
  if (['.woff', '.woff2'].includes(extname(name).toLowerCase())) {
    if (!['wOFF', 'wOF2'].includes(bytes.subarray(0, 4).toString('ascii'))) denied(`invalid font payload: ${name}`);
    return;
  }
  // These checks also cover JSON literals/strings in generated JS, renamed text
  // assets and source maps. Generic validator code is allowed; actual payloads
  // with real canonical season IDs or private envelope fields are not.
  const text = bytes.toString('utf8').replace(/\\u([a-f\d]{4})/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/\\([/"'])/g, '$1');
  if (/["'`][1-9]\d*:20\d\d\/20\d\d["'`]/.test(text) ||
      /["']?schema_version["']?\s*:\s*["'](?:soccer-provisional-observations\/|soccer-local-experimental-|private-five-attribute-)/.test(text) ||
      text.includes('403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd')) {
    denied(`real-player/private payload embedded in ${name}`);
  }
}

export async function verifyProductionDirectory(folder) {
  const files = [];
  async function visit(path) {
    for (const item of await readdir(path, { withFileTypes: true })) {
      const entry = resolve(path, item.name);
      if (item.isSymbolicLink()) denied(`symlink in production output: ${entry}`);
      if (item.isDirectory()) await visit(entry);
      else {
        const name = relative(folder, entry).replaceAll('\\', '/');
        assertAdmittedOutput(name, await readFile(entry));
        files.push(name);
      }
    }
  }
  await visit(resolve(folder));
  for (const asset of PUBLIC_ASSETS) if (!files.includes(asset.path)) denied(`missing reviewed static asset: ${asset.path}`);
  return files.sort();
}

export default function productionDataAdmission() {
  let config;
  const written = new Set();
  return {
    name: 'production-data-admission', apply: 'build', enforce: 'pre',
    config() { return { publicDir: false, build: { copyPublicDir: false } }; },
    configResolved(value) {
      config = value;
      if (config.publicDir || config.build.copyPublicDir !== false) denied('automatic public copying must remain disabled');
      config.logger.info('Production data admission: automatic public copying disabled; only the approved pinned final-ratings release, 3 pinned heatmaps, 5 pinned About Us portraits and 2 pinned demo/synthetic imports admitted. All other data remains denied.');
    },
    async load(id) { await validateDataImport(id); return null; },
    generateBundle: {
      order: 'post', sequential: true,
      async handler(_, bundle) {
        for (const asset of PUBLIC_ASSETS) this.emitFile({ type: 'asset', fileName: asset.path,
          source: await checkedBytes(resolve(FRONTEND_ROOT, 'public', asset.path), asset.sha256) });
        for (const [name, entry] of Object.entries(bundle)) assertAdmittedOutput(name, entry.type === 'chunk' ? entry.code : entry.source);
      },
    },
    writeBundle(options) { if (config.build.write !== false) written.add(resolve(options.dir ?? dirname(options.file))); },
    closeBundle: {
      order: 'post', sequential: true,
      async handler() { for (const folder of written) await verifyProductionDirectory(folder); },
    },
  };
}
