// Read-only production asset audit and temporary loopback production-preview probes.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, readdir, open, writeFile } from "node:fs/promises";
import { resolve, extname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { preview } from "vite";
import { verifyProductionDirectory } from "../build/productionDataAdmission.js";

const frontend = fileURLToPath(new URL("../", import.meta.url));
const repo = resolve(frontend, "..");
const validation = resolve(repo, "data/validation/local-experimental-website-v1");
const build = resolve(frontend, process.argv[2] ?? 'dist');
await verifyProductionDirectory(build);
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const before = JSON.parse(await readFile(resolve(validation, "preservation-before.json"), "utf8"));
for (const item of before) assert.equal(digest(await readFile(item.path)), item.sha256, `Preserved input changed: ${item.path}`);
async function files(path) {
  const result = [];
  for (const item of await readdir(path, { withFileTypes: true })) {
    const name = resolve(path, item.name);
    result.push(...(item.isDirectory() ? await files(name) : [name]));
  }
  return result;
}
const all = await files(build), text = all.filter((p) => [".js", ".json", ".html", ".css", ".map", ".jsonl"].includes(extname(p)));
const forbidden = ["five-attribute-experimental", "/__local_experimental/five-attributes", "FiveAttributeExperimentalExperience", "EXPERIMENTAL PROJECT RATINGS", "NOT OFFICIAL EA FIFA RATINGS", "private-five-attribute-player-season/v2", "PRIVATE-EXPERIMENTAL-scores.jsonl", "403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd", "af27f0053582b76c26c12e26aa4de55e56bc0b0eafe0cae9cc1fc47c5ad6b663"];
const scored = (await readFile(resolve(repo, "data/derived/private-five-attribute-v2/PRIVATE-EXPERIMENTAL-scores.jsonl"), "utf8")).trim().split("\n").map(JSON.parse);
for (const p of scored.filter((p) => [3961, 5574].includes(p.player_id))) {
  for (const m of Object.values(p.attributes)) if (m.experimental_rating !== null && !Number.isInteger(m.experimental_rating)) forbidden.push(String(m.experimental_rating));
}
for (const path of all) assert.doesNotMatch(basename(path), /PRIVATE-EXPERIMENTAL|frozen-reference|measurement-facts|player-measurements/);
for (const path of text) {
  const content = await readFile(path, "utf8");
  for (const token of forbidden) assert.ok(!content.includes(token), `Development/private token in production asset ${path}: ${token}`);
}
const server = await preview({ root: frontend, configFile: resolve(frontend, "vite.config.js"),
  build: { outDir: build }, preview: { host: "127.0.0.1", port: 0, strictPort: true, open: false } });
const address = server.httpServer.address(), base = `http://127.0.0.1:${address.port}`;
const probes = [];
try {
  for (const path of ["/", "/?view=five-attribute-experimental", "/__local_experimental/five-attributes", "/data/bundesliga-observations.json"]) {
    const r = await fetch(base + path), content = await r.text(), type = r.headers.get("content-type") ?? "";
    assert.ok(!type.includes("application/json"), "Production preview served the experimental API");
    assert.ok(!content.includes('"classification":"local_experimental"') && !content.includes("EXPERIMENTAL PROJECT RATINGS"));
    probes.push({ path, status: r.status, content_type: type, experimental_api_available: false });
  }
} finally { await new Promise((resolve, reject) => server.httpServer.close((error) => error ? reject(error) : resolve())); }
const result = { status: "PASS", production_text_assets_scanned: text.length, forbidden_tokens_and_score_canaries: forbidden.length,
  private_scores_in_production_assets: false, experimental_route_in_production_bundle: false,
  experimental_endpoint_in_production: false, unchanged_preserved_files: before.length, production_http_probes: probes,
  source_reconstruction_runs: 0, scoring_runs: 0, official_delivery_enabled: false };
if (process.argv[3]) await writeFile(resolve(process.argv[3]), JSON.stringify(result, null, 2) + "\n", { flag: "wx" });
console.log(JSON.stringify(result, null, 2));
