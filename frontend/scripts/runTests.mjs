// Required modules and reviewed source hashes prevent silent coverage loss.
import { readdirSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const suite = process.argv[2] ?? 'all';
const offline = process.argv.slice(3).includes('--offline');
if (!['all', 'public', 'private', 'packaging'].includes(suite) || process.argv.slice(3).some((v) => v !== '--offline')) throw Error('Expected all, public, private or packaging; optional --offline');
const inventory = JSON.parse(readFileSync(new URL('../tests/suiteInventory.json', import.meta.url), 'utf8'));
if (inventory.schema_version !== 1) throw Error('Unsupported frontend test inventory');
const allFiles = [...inventory.public_files, ...inventory.private_files];
const present = readdirSync(new URL('../tests/', import.meta.url)).filter((p) => p.endsWith('.test.js')).sort();
const unknown = present.filter((p) => !allFiles.includes(p));
if (unknown.length) throw Error(`Uncatalogued tests require review: ${unknown.join(', ')}`);
const selected = suite === 'all' ? allFiles : suite === 'private' ? inventory.private_files
  : suite === 'packaging' ? ['productionDataAdmission.test.js'] : inventory.public_files;
// Only complete/private runs require private test source. Public runs never do.
for (const name of selected) {
  if (!present.includes(name)) throw Error(`Missing required ${suite} test source: ${name}; no substitution or skip`);
  const source = readFileSync(new URL(`../tests/${name}`, import.meta.url), 'utf8').replaceAll(String.fromCharCode(13, 10), String.fromCharCode(10));
  const hash = createHash('sha256').update(source).digest('hex');
  if (hash !== inventory.source_sha256[name]) throw Error(`Test source differs from reviewed inventory: ${name}`);
}
const args = ['--test'];
if (offline) {
  // Positive literal skip names: never use a negative name filter matching ancestors.
  const names = [...(suite !== 'private' ? inventory.network_tests.public : []), ...(suite === 'all' || suite === 'private' ? inventory.network_tests.private : [])];
  if (names.some((name) => !/^[A-Za-z0-9 ,]+$/.test(name))) throw Error('Review offline test-name literals before use');
  args.push('--test-skip-pattern', names.join('|'));
  console.log(`OFFLINE SUBSET: ${names.length} HTTP case(s) explicitly excluded; full HTTP acceptance remains pending.`);
}
console.log(`Frontend ${suite}: ${selected.length} required source modules; private evidence is separately provisioned.`);
const result = spawnSync(process.execPath, [...args, ...selected.map((p) => `tests/${p}`)], { cwd: root, stdio: 'inherit' });
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
