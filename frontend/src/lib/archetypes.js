/* Archetype definitions + classification. Edit wording here.
   Rule: a player gets ONE primary archetype — the one whose metric is their
   highest percentile for their position. Tier by that percentile:
     ≥ 90  → "+"      75–90 → "−"      < 75 → "Standard"                      */

export const TIER = { plus: 90, minus: 75 };

/* Future rating attributes: canonical IDs match D3E; short keys are display labels. */
export const METRICS = [
  { id: "tackles", key: "T", label: "Tackles" },
  { id: "interceptions", key: "I", label: "Interceptions" },
  { id: "recoveries", key: "REC", label: "Recoveries" },
  { id: "press_resistance", key: "P", label: "Press Resistance" },
  { id: "line_breaking_passes", key: "LB", label: "Line-Breaking Passes" },
];

/* Historical fictional percentile chart only. Never migrate C values into REC. */
export const DEMO_METRICS = [
  { key: "T", label: "Tackles" },
  { key: "I", label: "Interceptions" },
  { key: "C", label: "Clearances" },
  { key: "P", label: "Playing under pressure" },
  { key: "LB", label: "Line-breaking passes" },
];

/* Archetype metric keys retain their existing tie order and demo mapping. */
export const GROUPS = ["Defensive Recovery", "Press Resistance", "Line-breaking passes"];

export const ARCHETYPES = {
  CB: [
    { id: "stopper", name: "Stopper", group: "Defensive Recovery", metric: "T", blurb: "Specializes in tackles." },
    { id: "sweeper", name: "Sweeper", group: "Defensive Recovery", metric: "REC", blurb: "Leads in ball recoveries." },
    { id: "reader", name: "Tactician / Reader", group: "Defensive Recovery", metric: "I", blurb: "Leads in interceptions." },
    { id: "libero", name: "Libero", group: "Press Resistance", metric: "P", blurb: "Stays composed with the ball under pressure." },
    { id: "ballplaying", name: "Ball-Playing CB", group: "Line-breaking passes", metric: "LB", blurb: "Breaks lines with passes from the back." },
  ],
  DM: [
    { id: "destroyer", name: "Destroyer", group: "Defensive Recovery", metric: "T", blurb: "Specializes in tackles." },
    { id: "anchor", name: "Anchor", group: "Defensive Recovery", metric: "I", blurb: "Leads in interceptions." },
    { id: "bwm", name: "Ball-Winning Midfielder", group: "Defensive Recovery", metric: "REC", blurb: "Leads in recoveries." },
    { id: "volante", name: "Volante", group: "Press Resistance", metric: "P", blurb: "Stays composed with the ball under pressure." },
    { id: "dlp", name: "Deep-Lying Playmaker", group: "Line-breaking passes", metric: "LB", blurb: "Breaks lines with passes from deep." },
  ],
};

export function percentileValue(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100 ? value : null;
}

function selectArchetype(position, percentile) {
  const list = ARCHETYPES[position] || [];
  let best = null;
  for (const a of list) {
    const v = percentileValue(percentile(a.metric));
    if (v === null) continue;
    if (!best || v > best.value) best = { a, value: v }; // ties keep the first listed
  }
  if (!best || best.value < TIER.minus) return { name: "Standard", tier: null, metric: null, value: best ? best.value : null };
  return { name: best.a.name, tier: best.value >= TIER.plus ? "+" : "−", metric: best.a.metric, value: best.value };
}

/* Only explicitly supplied rank percentiles classify future rating cards. */
export function classify(player) {
  return selectArchetype(player.position, (key) =>
    player.attributes?.[METRICS.find((m) => m.key === key).id]?.percentile);
}

export function classifyDemo(player) {
  return selectArchetype(player.position, (key) => player.pct?.[key]);
}

/* Historical demo OVR only; never called for real rating cards. */
export function demoOverall(player) {
  const vals = DEMO_METRICS.map((m) => percentileValue(player.pct?.[m.key])).filter((v) => v !== null);
  return vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : null;
}
