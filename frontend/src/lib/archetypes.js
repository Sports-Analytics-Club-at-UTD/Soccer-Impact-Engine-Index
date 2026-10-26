/* Archetype definitions + classification. Edit wording here.
   Rule: a player gets ONE primary archetype — the one whose metric is their
   highest percentile for their position. Tier by that percentile:
     ≥ 90  → "+"      75–90 → "−"      < 75 → "Standard"                      */

export const TIER = { plus: 90, minus: 75 };

/* The five card metrics (radar axes). */
export const METRICS = [
  { key: "T", label: "Tackles" },
  { key: "I", label: "Interceptions" },
  { key: "C", label: "Clearances" },
  { key: "P", label: "Playing under pressure" },
  { key: "LB", label: "Line-breaking passes" },
];

/* `metric` is the percentile column the archetype is judged on.
   NOTE: "REC" (ball recoveries) is NOT one of the five card metrics, but the
   Sweeper and Ball-Winning Midfielder archetypes are defined on it — so the
   data needs a REC percentile column too. */
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

export function classify(player) {
  const list = ARCHETYPES[player.position] || [];
  let best = null;
  for (const a of list) {
    const v = player.pct[a.metric];
    if (typeof v !== "number") continue;
    if (!best || v > best.value) best = { a, value: v }; // ties keep the first listed
  }
  if (!best || best.value < TIER.minus) return { name: "Standard", tier: null, metric: null, value: best ? best.value : null };
  return { name: best.a.name, tier: best.value >= TIER.plus ? "+" : "−", metric: best.a.metric, value: best.value };
}

/* PLACEHOLDER overall rating: mean of the five card percentiles.
   Swap this one function when the real formula is ready. */
export function overall(player) {
  const vals = METRICS.map((m) => player.pct[m.key]).filter((v) => typeof v === "number");
  return vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : 0;
}
