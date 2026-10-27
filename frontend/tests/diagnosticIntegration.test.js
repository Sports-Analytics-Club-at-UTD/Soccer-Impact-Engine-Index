import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { parseDiagnosticProfiles, readDiagnosticFile } from "../src/lib/diagnosticAdapter.js";
import { browseDiagnosticProfiles, selectDiagnosticProfile, diagnosticWindow, diagnosticValue, zeroMinuteWarning } from "../src/lib/diagnosticView.js";
import { playerDataMode, loadPlayerExperience } from "../src/lib/playerDataMode.js";

// Generate a small test-only contract through the real Python exporter primitives.
// No real-player JSON is checked in or bundled.
const python = spawnSync("python", ["-B", "-c", `
import sys,json
sys.path.insert(0,'tests')
from test_provisional_profiles import fixture
from src.provisional_profiles import build_profiles
a,m=fixture([{},dict(id='e2',match_id=20)],player_id=2**63-1)
b,n=fixture(complete=False)
c,o=fixture([dict(type='Pass',under_pressure=True)]+[dict(id='p'+str(i),match_id=20,type='Pass',under_pressure=True,pass_outcome='Incomplete') for i in range(3)])
print(json.dumps(dict(basic=build_profiles(a,delivered_minutes=m),incomplete=build_profiles(b,delivered_minutes=n),press=build_profiles(c,delivered_minutes=o)),allow_nan=False))
`], { cwd: fileURLToPath(new URL("../../", import.meta.url)), encoding: "utf8" });
assert.equal(python.status, 0, python.stderr);
const generated = JSON.parse(python.stdout);
const fixture = generated.basic;
const fresh = () => structuredClone(fixture);
const change = (fn) => { const p = fresh(); fn(p); return p; };
test("diagnostic mode is explicit and isolated", async () => {
  assert.equal(playerDataMode("diagnostic"), "diagnostic");
  assert.equal(await loadPlayerExperience("diagnostic", { diagnostic: () => "diagnostic", demo: () => assert.fail() }), "diagnostic");
});
test("diagnostic loader failure has no demo fallback", async () => {
  await assert.rejects(() => loadPlayerExperience("diagnostic", { diagnostic: async () => { throw Error("failed"); }, demo: () => assert.fail() }), /failed/);
});
test("real D2C primitives produce accepted exact int64 IDs and counts", () => {
  const model = parseDiagnosticProfiles(fresh());
  assert.equal(model.profiles[0].identity.player_id, "9223372036854775807");
  assert.equal(model.profiles[0].pooled.recovery["Ball Recovery"].count, "2");
});
for (const value of [1, 1.5, "01", "1.0", "-1", "9223372036854775808"]) {
  test(`rejects noncanonical identity ${value}`, () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.profiles[0].identity.player_id = value; }))));
}
test("counts require exact decimal strings", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.profiles[0].pooled.recovery["Ball Recovery"].count = 2; }))));
test("incompatible schema rejected", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.schema_version = "soccer-scorecard/v1"; }))));
test("unsupported provenance rejected", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.match_context_provenance = "VERIFIED_SOURCE_EVIDENCE"; }))));
test("authoritative completeness promotion rejected", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.scope.authoritative_feed_complete = true; }))));
test("duplicate identities rejected", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.profiles.push(structuredClone(p.profiles[0])); }))));
test("duplicate matches rejected", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.scope.match_ids.push("20"); }))));
test("contradictory player match windows rejected", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.profiles[0].scope.included_match_ids = ["10"]; }))));
test("contradictory per90 denominator rejected", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.profiles[0].matches[0].recovery["Ball Recovery"].per90.denominator_match_ids = ["20"]; }))));
test("pooled count conservation enforced", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { const r = p.profiles[0].pooled.recovery["Ball Recovery"]; r.count = "3"; r.zone_counts[0].count = "3"; r.per90.value = 13.5; }))));
test("zone conservation enforced", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.profiles[0].matches[0].recovery["Ball Recovery"].unknown_zone_count = "1"; }))));
test("fabricated overall ratings rejected as unknown fields", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.profiles[0].ovr = 90; }))));
test("pooled and match-specific values remain distinct", () => {
  const p = parseDiagnosticProfiles(fresh()).profiles[0];
  assert.equal(diagnosticWindow(p).recovery["Ball Recovery"].count, "2");
  assert.equal(diagnosticWindow(p, "10").recovery["Ball Recovery"].count, "1");
  assert.equal(diagnosticWindow(p, "999"), null);
});
test("missing metrics are N/A with unsupported per90", () => {
  const r = parseDiagnosticProfiles(fresh()).profiles[0].pooled.recovery.Tackle;
  assert.equal(diagnosticValue(r.count), "N/A");
  assert.equal(r.per90.available, false);
  assert.deepEqual(r.per90.reasons, ["missing_metric"]);
});
test("search, match filtering and selection never substitute a player", () => {
  const m = parseDiagnosticProfiles(fresh());
  assert.equal(browseDiagnosticProfiles(m, "fixture").length, 1);
  assert.equal(browseDiagnosticProfiles(m, "Team", "10").length, 1);
  assert.equal(browseDiagnosticProfiles(m, "absent").length, 0);
  assert.equal(browseDiagnosticProfiles(m, "", "999").length, 0);
  assert.equal(selectDiagnosticProfile(m.profiles, "absent"), null);
  assert.equal(selectDiagnosticProfile(m.profiles, m.profiles[0].context_key), m.profiles[0]);
});
test("zero-minute ambiguity is preserved and warned", () => {
  const m = parseDiagnosticProfiles(change((p) => { const e = p.profiles[0].pooled.exposure; e.delivered_minutes = 0; e.delivered_minutes_status = "zero"; e.source_ambiguities = ["observed_activity_with_zero_delivered_minutes"]; }));
  assert.equal(zeroMinuteWarning(m.profiles[0]), true);
});
test("JSON object property order does not change validation", () => {
  const reverse = (v) => Array.isArray(v) ? v.map(reverse) : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).reverse().map(([k, x]) => [k, reverse(x)])) : v;
  assert.equal(parseDiagnosticProfiles(reverse(fresh())).profiles.length, 1);
});
test("local file validates entirely through explicit input", async () => {
  const content = JSON.stringify(fresh());
  assert.equal((await readDiagnosticFile({ size: content.length, text: async () => content })).profiles.length, 1);
  await assert.rejects(() => readDiagnosticFile({ size: 1, text: async () => "{" }), /JSON/);
  await assert.rejects(() => readDiagnosticFile({ size: 17 * 1024 * 1024, text: () => assert.fail() }), /16 MiB/);
});
test("diagnostic dependency graph contains no demo ratings or network loader", () => {
  const files = ["components/DiagnosticExperience.jsx", "lib/diagnosticAdapter.js", "lib/diagnosticView.js"];
  const source = files.map((f) => readFileSync(new URL(`../src/${f}`, import.meta.url), "utf8")).join("\n");
  assert.doesNotMatch(source, /import .*?(?:archetypes|players|Radar|PlayerCard|scorecardLoader)/);
  assert.doesNotMatch(source, /\bfetch\s*\(|localStorage|sessionStorage/);
  assert.match(source, /Not yet assessed/);
  assert.match(source, /DIAGNOSTIC — PROVISIONAL REAL DATA/);
});
test("incomplete collection withholds per90 even with observed recovery", () => {
  const p = parseDiagnosticProfiles(generated.incomplete).profiles[0];
  assert.equal(p.pooled.recovery["Ball Recovery"].count, "1");
  assert.equal(p.pooled.recovery["Ball Recovery"].per90.value, null);
  assert.ok(p.pooled.recovery["Ball Recovery"].per90.reasons.includes("local_match_collection_not_established"));
});
test("pooled percentage uses total attempts and preserves observed zero", () => {
  const p = parseDiagnosticProfiles(generated.press).profiles[0];
  assert.equal(p.pooled.press.percentages.press_resistance_rate.value, 25);
  assert.equal(p.matches[1].press.percentages.press_resistance_rate.value, 0);
  assert.equal(p.matches[1].press.percentages.pressured_dribble_completion_rate.value, null);
});
test("a fabricated mean of match percentages is rejected", () => {
  const p = structuredClone(generated.press);
  p.profiles[0].pooled.press.percentages.press_resistance_rate.value = 50;
  assert.throws(() => parseDiagnosticProfiles(p));
});
test("ambiguous observed names retain their source variants", () => {
  const m = parseDiagnosticProfiles(change((p) => { p.profiles[0].identity.player_name = null; p.profiles[0].identity.observed_name_variants = ["Actor A", "Actor B"]; }));
  assert.equal(browseDiagnosticProfiles(m, "Actor B").length, 1);
});
test("noncanonical observed name spelling is rejected", () => assert.throws(() => parseDiagnosticProfiles(change((p) => { p.profiles[0].identity.player_name = " Actor"; p.profiles[0].identity.observed_name_variants = [" Actor"]; }))));
