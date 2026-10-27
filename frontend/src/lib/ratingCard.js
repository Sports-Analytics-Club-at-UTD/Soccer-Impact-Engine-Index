import { METRICS, DEMO_METRICS, classify, classifyDemo, demoOverall, percentileValue } from "./archetypes.js";

export const OVR_PENDING = "N/A — POLICY NOT FINALIZED";
export const ratingValue = (value) => percentileValue(value) !== null && value >= 1 ? value : null;
export const scoreLabel = (value) => value === null ? "N/A" : String(Math.round(value));

/* Presentation contract only, not an exporter, scoring transform or trust gate.
   attributes[id] = { rating: number|null, percentile: number|null }.
   The caller must independently establish eligibility and verified source lineage.
   No fallback from pct, score, raw percentages, DRI or progressive passing. */
export function ratingCard(player, { demo = false } = {}) {
  const metrics = demo ? DEMO_METRICS : METRICS;
  const attributes = metrics.map((m) => {
    const value = demo ? percentileValue(player.pct?.[m.key]) : ratingValue(player.attributes?.[m.id]?.rating);
    return { ...m, value, text: scoreLabel(value),
      percentile: demo ? value : percentileValue(player.attributes?.[m.id]?.percentile) };
  });
  return {
    attributes,
    profileLabel: demo ? "Fictional percentile profile" : "FIFA-style rating profile",
    archetype: demo ? classifyDemo(player) : classify(player),
    ovr: demo ? demoOverall(player) : null,
    ovrLabel: demo ? "Demo OVR" : OVR_PENDING,
  };
}
