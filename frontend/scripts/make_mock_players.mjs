// Generates src/data/players.json with FICTIONAL placeholder players.
// Run: node scripts/make_mock_players.mjs   (delete once real data is in)
import { writeFileSync } from "node:fs";

let seed = 20151617;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296);
const pick = (lo, hi) => Math.round(lo + rnd() * (hi - lo));

const roster = [
  ["Marcus Delacroix", "PSG", "CB", 2410, "T"],
  ["Tomas Brandl", "Leverkusen", "CB", 2875, "I"],
  ["Ilyas Benkarim", "Barcelona", "CB", 1980, "LB"],
  ["Jonas Wirtz", "Leverkusen", "CB", 740, "REC"],
  ["Dario Valenzuela", "Barcelona", "CB", 3120, "P"],
  ["Kofi Adjei-Mensah", "PSG", "CB", 2260, "T"],
  ["Henrik Solvang", "Leverkusen", "CB", 1530, null],
  ["Rafael Ouedraogo", "PSG", "CB", 2690, "I"],
  ["Nikolai Petrescu", "Leverkusen", "DM", 2990, "T"],
  ["Mateus Almeida-Reis", "Barcelona", "DM", 3340, "LB"],
  ["Yusuf Demirkan", "PSG", "DM", 2150, "REC"],
  ["Lukas Kreuzer", "Leverkusen", "DM", 860, "I"],
  ["Andre Lemaitre", "PSG", "DM", 2740, "P"],
  ["Sami Haddad", "Barcelona", "DM", 1710, "T"],
  ["Bruno Castellanos", "Barcelona", "DM", 2480, "LB"],
  ["Oscar Lindqvist", "Leverkusen", "DM", 1290, null],
];

const players = roster.map(([name, team, position, minutes, star], i) => {
  const pct = {};
  for (const k of ["T", "I", "C", "P", "LB", "REC"]) pct[k] = pick(28, 86);
  if (star) pct[star] = pick(91, 99);
  return {
    id: i + 1,
    name,
    team,
    position,
    minutes,
    photo: "", // e.g. "/players/marcus-delacroix.png"
    pct,
  };
});

writeFileSync(new URL("../src/data/players.json", import.meta.url), JSON.stringify(players, null, 2));
console.log(`wrote ${players.length} placeholder players`);
