// Current development delivery and production isolation smoke test.
import assert from 'node:assert/strict';
import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { preview } from 'vite';
import { parseExperimentalDelivery, experimentalModels } from '../src/dev/experimentalDelivery.js';
import { ovrLeaderboard } from '../src/dev/provisionalOvr.js';
import { verifyProductionDirectory } from '../build/productionDataAdmission.js';

const frontend = fileURLToPath(new URL('..',import.meta.url));
await verifyProductionDirectory(resolve(frontend, 'dist'));
const observationsResponse = await fetch('http://127.0.0.1:5173/data/bundesliga-observations.json');
assert.equal(observationsResponse.status, 200);
const observations = await observationsResponse.json();
assert.equal(observations.players.length, 346); assert.equal(observations.publication_authorized, false);
const response = await fetch('http://127.0.0.1:5173/__local_experimental/five-attributes');
assert.equal(response.status,200); assert.equal(response.headers.get('cache-control'),'no-store');
assert.equal(response.headers.get('access-control-allow-origin'),null);
const d=await parseExperimentalDelivery(await response.text()), players=experimentalModels(d);
assert.equal(players.length,691); assert.equal(players.filter((p)=>p.ovr.value!==null).length,686);
assert.equal(ovrLeaderboard(players,'MID').length,124); assert.equal(ovrLeaderboard(players,'CB').length,107);
for (const [path, options, expected] of [
  ['/__local_experimental/five-attributes',{method:'POST'},405],
  ['/__local_experimental/five-attributes?file=secret',{},400],
  ['/__local_experimental/five-attributes',{headers:{origin:'https://example.invalid'}},403],
]) { const r=await fetch('http://127.0.0.1:5173'+path,options);assert.equal(r.status,expected);await r.text(); }

async function files(folder) {
  const result=[];
  for (const entry of await readdir(folder,{withFileTypes:true})) {
    const path=resolve(folder,entry.name);result.push(...(entry.isDirectory()?await files(path):[path]));
  }
  return result;
}
const assets=(await files(resolve(frontend,'dist'))).filter((p)=>/\.(js|json|html|css|map)$/.test(p));
for (const asset of assets) {
  const content=await readFile(asset,'utf8');
  for (const token of ['five-attribute-experimental','/__local_experimental/five-attributes','soccer-ovr-formula-b/v1',d.reference.fingerprint,d.source_package.scores_sha256]) assert.ok(!content.includes(token),`${token} leaked into ${asset}`);
}
const server=await preview({root:frontend,configFile:resolve(frontend,'vite.config.js'),preview:{host:'127.0.0.1',port:0,strictPort:true,open:false}});
const probes=[];
try {
  const base=`http://127.0.0.1:${server.httpServer.address().port}`;
  for (const path of ['/','/?view=five-attribute-experimental','/__local_experimental/five-attributes','/data/bundesliga-observations.json']) {
    const r=await fetch(base+path),content=await r.text();
    assert.ok(!r.headers.get('content-type')?.includes('application/json'));assert.ok(!content.includes('"ovr_integration"'));
    assert.ok(!content.includes('"players"'), 'Nonpublication observations appeared in preview');
    probes.push({path,status:r.status,content_type:r.headers.get('content-type'),json_available:false});
  }
} finally { await new Promise((resolve,reject)=>server.httpServer.close((error)=>error?reject(error):resolve())); }
const result={status:'PASS',local_observation_profiles:observations.players.length,local_observation_publication_authorized:observations.publication_authorized,served_profiles:players.length,complete_ovrs:686,eligible:{MID:124,CB:107},no_store:true,request_rejections_pass:true,production_assets_scanned:assets.length,production_probes:probes};
if (process.argv[2]) await writeFile(resolve(process.argv[2]),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(result,null,2));
