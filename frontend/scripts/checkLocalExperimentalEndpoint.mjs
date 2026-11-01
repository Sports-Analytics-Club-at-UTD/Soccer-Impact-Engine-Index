// End-to-end read-only development endpoint checks. No scoring or export.
import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseExperimentalDelivery } from "../src/dev/experimentalDelivery.js";

const repo = fileURLToPath(new URL("../../", import.meta.url));
const base = "http://127.0.0.1:5173", endpoint = "/__local_experimental/five-attributes";
const response = await fetch(base + endpoint);
assert.equal(response.status, 200); assert.equal(response.headers.get("cache-control"), "no-store");
assert.equal(response.headers.get("access-control-allow-origin"), null);
const data = await parseExperimentalDelivery(await response.text());
const frozen = new Map((await readFile(resolve(repo, "data/derived/private-five-attribute-v2/PRIVATE-EXPERIMENTAL-scores.jsonl"), "utf8")).trim().split("\n").map((s) => { const p=JSON.parse(s); return [String(p.player_id),p]; }));
const sourceKeys = { tackles: "tackles", interceptions: "interceptions", recoveries: "recoveries", press_resistance: "press_resistance", line_breaking_passes: "progressive_passing" };
for (const p of data.players) {
  const source = frozen.get(p.player_id); assert.ok(source); assert.equal(p.name, source.name);
  for (const [a, sourceKey] of Object.entries(sourceKeys)) {
    assert.equal(p.attributes[a].rating, source.attributes[sourceKey].experimental_rating);
    assert.equal(p.attributes[a].percentile, source.attributes[sourceKey].percentile);
  }
}
const probes=[];
for (const [path,options,status] of [
  [endpoint,{method:"POST"},405], [endpoint+"?file=secret",{},400],
  [endpoint,{headers:{origin:"https://example.invalid"}},403],
  ["/@fs/"+repo.replaceAll("\\","/")+"data/derived/private-five-attribute-v2/PRIVATE-EXPERIMENTAL-scores.jsonl",{},403],
]) {
  const r=await fetch(base+path,options); assert.equal(r.status,status,path); probes.push({path, status:r.status}); await r.text();
}
const result={status:"PASS", counts:data.counts, actual_http_scores_and_percentiles_match_frozen_files:true,
  required_player_ids:["3961","5574","7173","3500","3103","4802"],
  cache_control:response.headers.get("cache-control"),cross_origin_access_enabled:false,probes,
  source_reconstructions:0,scoring_runs:0,publication_authorized:false};
assert.ok(result.required_player_ids.every((id)=>data.players.some((p)=>p.player_id===id)));
await writeFile(resolve(repo,"data/validation/local-experimental-website-v1/development-http.json"),JSON.stringify(result,null,2)+"\n",{flag:"wx"});
console.log(JSON.stringify(result,null,2));
