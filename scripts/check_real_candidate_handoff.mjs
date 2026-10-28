// Offline assertions only. No app import, network, public data write or server.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {parseRatingDelivery, parseRatingJson, ratingPlayers, readRatingFile} from '../frontend/src/lib/ratingDelivery.js';
import {ratingCard} from '../frontend/src/lib/ratingCard.js';

const path=process.argv[2];
assert(path,'Provide the isolated withheld contract fixture path');
const delivery=parseRatingDelivery(parseRatingJson(fs.readFileSync(path,'utf8')));
assert(delivery.players.length>0);
const players=ratingPlayers(delivery);
assert.equal(new Set(players.map(p=>p.id)).size,players.length);
const imported=await readRatingFile({size:fs.statSync(path).size,text:async()=>fs.readFileSync(path,'utf8')});
assert.deepEqual(imported,players);
for (const p of players) {
  assert.equal(p.classification,'diagnostic');
  assert.equal(p.eligibility.synthetic_supported,false);
  assert.equal(p.overall.rating,null);
  assert.equal(p.ratingNotice,'DIAGNOSTIC / RATINGS WITHHELD');
  assert.equal(p.position,p.role_group==='MID'?'DM':p.role_group);
  const card=ratingCard(p);
  assert.equal(card.ovr,null);
  assert(card.attributes.every(a=>a.value===null && a.text==='N/A'));
  for (const a of Object.values(p.attributes)) {
    assert.equal(a.rating,null);assert.equal(a.percentile,null);assert.equal(a.status,'withheld');
  }
}
const edit=(fn)=>{const d=structuredClone(delivery);fn(d);return d;};
assert.throws(()=>parseRatingDelivery(edit(d=>{d.publication_authorized=true;})));
assert.throws(()=>parseRatingDelivery(edit(d=>{d.players[0].eligibility.synthetic_supported=true;})));
assert.throws(()=>parseRatingDelivery(edit(d=>{d.players[0].attributes.tackles.rating=65;})));
assert.throws(()=>parseRatingDelivery(edit(d=>{d.players[0].overall.rating=65;})));
assert.throws(()=>parseRatingDelivery(edit(d=>{d.players.push(structuredClone(d.players[0]));})));
console.log(JSON.stringify({offline_contract_passed:true,diagnostic_records:delivery.players.length,
  numeric_real_scores:0,negative_promotions_rejected:5,production_files_modified:false}));
