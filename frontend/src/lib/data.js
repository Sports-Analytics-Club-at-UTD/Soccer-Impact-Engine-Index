/* Single place the site reads player data from.
   Swap src/data/players.json for the real file (see scripts/parquet_to_json.py)
   and nothing else needs to change.

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
