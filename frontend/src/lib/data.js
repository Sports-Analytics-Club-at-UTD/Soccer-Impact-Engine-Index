/* DEMO ONLY: fictional data and illustrative scoring remain isolated here.
   Do not replace this file with raw scorecard values. The versioned real-metric
   adapter is scorecardAdapter.js; React integration is a future milestone.

   Expected row shape:
   { id, name, team, position: "CB" | "DM", minutes, photo?,
     pct: { T, I, C, P, LB, REC }   // percentiles 0–100 vs positional peers }   */
import raw from "../data/players.json";
import { classify, overall } from "./archetypes.js";

export const MIN_MINUTES = 1000;

export const PLAYERS = raw.map((p) => ({
  ...p,
  ovr: overall(p),
  archetype: classify(p),
}));
