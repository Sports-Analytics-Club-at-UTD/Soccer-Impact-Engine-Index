import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createRequire,Module} from 'node:module';
import {fileURLToPath} from 'node:url';
import {parsePublicRatings} from '../src/lib/publicRatingsDelivery.js';
import {PUBLIC_RATINGS_RELEASE as release} from '../src/lib/publicRatingsRelease.js';
import {foundationPlayers} from '../src/lib/foundationPlayers.js';
import {publicPlayerCopy} from '../src/lib/publicPlayerCopy.js';

const bytes=readFileSync(new URL(`../public/${release.path}`,import.meta.url));
const data=parsePublicRatings(bytes.toString('utf8'));
const before=parsePublicRatings(readFileSync(new URL('../public/data/player-ratings-2015-16-v2.json',import.meta.url),'utf8'));
const byId=(id)=>data.players.find((p)=>p.player_id===String(id));

test('recovery release is pinned and retains every identity and ranking decision',()=>{
  assert.equal(data.schema_version,'soccer-public-ratings/v3');
  assert.equal(createHash('sha256').update(bytes).digest('hex'),release.sha256);
  assert.equal(bytes.length,release.bytes);
  assert.equal(data.players.length,691);
  const old=new Map(before.players.map((p)=>[p.id,p]));
  for(const p of data.players){assert.equal(p.ovr.eligible,old.get(p.id).ovr.eligible);assert.equal(p.badge_eligible,old.get(p.id).badge_eligible);}
  assert.equal(data.players.filter((p)=>p.ovr.eligible).length,551);
});

test('all partial fixture counts are bounded and explicit',()=>{
  assert.equal(data.players.reduce((n,p)=>n+p.coverage.partial_fixtures,0),122);
  assert.equal(data.players.reduce((n,p)=>n+p.coverage.unresolved_fixtures,0),1);
  for(const p of data.players){
    assert.ok(p.coverage.partial_fixtures<=p.coverage.supported_fixtures);
    for(const [id,a] of Object.entries(p.attributes)){
      assert.ok(a.coverage.partial_fixtures<=p.coverage.partial_fixtures);
      if(id==='press_resistance')assert.equal(a.coverage.partial_fixtures,0);
    }
  }
});

test('Busquets adds only the confirmed first half and retains the same pressure sample',()=>{
  const p=byId(5203);
  assert.equal(p.coverage.partial_fixtures,1);assert.equal(p.coverage.observed_fixtures,35);
  assert.ok(Math.abs(p.coverage.supported_minutes-2958.9249666666665)<1e-9);
  assert.equal(p.attributes.press_resistance.coverage.pressure_attempts,357);
  assert.equal(p.attributes.tackles.coverage.partial_fixtures,1);
  assert.match(publicPlayerCopy(p).attributeNotes.tackles,/only verified portions of 1 match/);
});

test('Weber keeps verified prefix time while the disputed pressure ratio stays excluded',()=>{
  const p=byId(7435),old=before.players.find((p)=>p.player_id==='7435');
  assert.equal(p.coverage.partial_fixtures,1);
  assert.ok(Math.abs(p.coverage.supported_minutes-old.coverage.supported_minutes-901.182/60)<1e-9);
  assert.equal(p.attributes.press_resistance.coverage.pressure_attempts,109);
  assert.equal(p.attributes.press_resistance.coverage.excluded_fixtures,1);
});

test('Sammarco halftime return is fully recovered without adding break time',()=>{
  const p=byId(23349);
  assert.equal(p.coverage.partial_fixtures,0);assert.equal(p.coverage.unresolved_fixtures,0);
  assert.equal(p.coverage.supported_fixtures,p.coverage.observed_fixtures);
});

test('invalid partial coverage is rejected rather than silently converted to full support',()=>{
  const changed=structuredClone(data),p=changed.players.find((p)=>p.player_id==='5203');
  p.coverage.partial_fixtures=p.coverage.supported_fixtures+1;
  assert.throws(()=>parsePublicRatings(JSON.stringify(changed)),/partial coverage/);
  const other=structuredClone(data),q=other.players.find((p)=>p.player_id==='5203');
  q.attributes.press_resistance.coverage.partial_fixtures=1;
  assert.throws(()=>parsePublicRatings(JSON.stringify(other)),/partial metric coverage/);
});

test('cards disclose partial samples in rating details without restoring removed footer text',()=>{
  const require=createRequire(import.meta.url),React=require('react');
  const {renderToStaticMarkup}=require('react-dom/server');
  const filename=fileURLToPath(new URL('../src/components/PlayerCard.jsx',import.meta.url));
  const bundled=require('esbuild').buildSync({entryPoints:[filename],bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',logLevel:'silent',external:['react','react/jsx-runtime']});
  const mod=new Module(filename);mod.filename=filename;mod.paths=Module._nodeModulePaths(fileURLToPath(new URL('../',import.meta.url)));mod._compile(bundled.outputFiles[0].text,filename);
  const player=foundationPlayers(data).find((p)=>p.id==='5203:2015/2016');
  const html=renderToStaticMarkup(React.createElement(mod.exports.default,{player}));
  assert.match(html,/only verified portions of 1 match/);
  assert.match(html,/actions outside those portions are excluded/);
  assert.doesNotMatch(html,/backing these minutes/);
  assert.match(html,/Included in the position rankings/);
});

test('aggregate projection contains no raw event or interval evidence',()=>{
  assert.doesNotMatch(bytes.toString(),/omitted_numerator_ids|numerator_ids|denominator_ids|proof_references|source_sha256|start_reference|end_reference|member_ids|exposure_recovery/);
});
