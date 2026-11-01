/* ═══════════════════════════════════════════════════════════════════════════
   EVERYTHING YOU'LL WANT TO EDIT LIVES HERE (plus src/lib/archetypes.js for
   archetype wording, and src/data/players.json for player data).
   Images: put files in /public and point to them like "/teams/psg-1.png".
   ═══════════════════════════════════════════════════════════════════════════ */

export const SITE = {
  title: "SAC Midfielder/Defender Index",
  org: "UTD Sports Analytics Club",
  season: "2015/16",
};

export const NAV = [
  { id: "home", label: "Home" },
  { id: "description", label: "Description" },
  { id: "archetypes", label: "Archetypes" },
  { id: "search", label: "Search" },
  { id: "teams", label: "Teams" },
  { id: "about", label: "About us" },
];

export const HERO = {
  subtitle: "(football clips)",
  tagline: "Centre-backs and defensive midfielders, ranked by what they actually do.",
  cta: "Search a player",
  // Drop your clips in /public and set the path, e.g. "/clips/hero.mp4".
  // Leave empty to show the animated pitch placeholder.
  videoSrc: "",
  poster: "",
};

export const DESCRIPTION = {
  eyebrow: "(Project)",
  title: "Description",
  intro:
    "The SAC Midfielder/Defender Index scores centre-backs and defensive midfielders on five measures — tackles, interceptions, clearances, playing under pressure and line-breaking passes — as percentiles against their positional peers. Each player is then assigned one primary archetype.",
  points: [
    {
      label: "One season of data",
      body:
        "We could only use 2015/16 data. It was the only season available to us because of financial constraints, so every number on this site comes from that single season.",
    },
    {
      label: "Spatial data is team-level",
      body:
        "The spatial data we had is provided on a team basis only. We have no player-level spatial data, so spatial work is done per team, not per player.",
    },
    {
      label: "Pivoting to teams",
      body:
        "Because of that, the project pivots to teams: player cards show individual percentile profiles, and the Teams section shows how each side controls space. Off-ball dominance is measured for teams only.",
    },
  ],
};

export const TEAMS_SECTION = {
  eyebrow: "Spatial data",
  title: "Teams",
  intro:
    "Pick a team to view its off-ball spatial dominance in one team-level heat map.",
};

/* Each team shows one heat map: { label, src, alt, caption }. */
export const TEAMS = [
  {
    id: "psg",
    short: "PSG",
    name: "Paris Saint-Germain",
    note: "Team-level zone control while opponents have possession, showing the defender-nearest share of observed space.",
    images: [
      { label: "OFF-BALL SPATIAL DOMINANCE", src: "/team/spatial_Paris_Saint-Germain.png", alt: "Paris Saint-Germain team-level off-ball spatial dominance heat map: defender-nearest share of observed space while opponents have possession.", caption: "TEAM-LEVEL HEAT MAP" },
    ],
  },
  {
    id: "barca",
    short: "Barça",
    name: "FC Barcelona",
    note: "Team-level zone control while opponents have possession, showing the defender-nearest share of observed space.",
    images: [
      { label: "OFF-BALL SPATIAL DOMINANCE", src: "/team/spatial_Barcelona.png", alt: "Barcelona team-level off-ball spatial dominance heat map: defender-nearest share of observed space while opponents have possession.", caption: "TEAM-LEVEL HEAT MAP" },
    ],
  },
  {
    id: "leverkusen",
    short: "Leverkusen",
    name: "Bayer 04 Leverkusen",
    note: "Team-level zone control while opponents have possession, showing the defender-nearest share of observed space.",
    images: [
      { label: "OFF-BALL SPATIAL DOMINANCE", src: "/team/spatial_Bayer_Leverkusen.png", alt: "Bayer Leverkusen team-level off-ball spatial dominance heat map: defender-nearest share of observed space while opponents have possession.", caption: "TEAM-LEVEL HEAT MAP" },
    ],
  },
];

export const ABOUT = {
  eyebrow: "The team",
  title: "About us",
  intro: "Five members of the UTD Sports Analytics Club, eight weeks, one index.",
  // photo: "/team/name.jpg" — leave "" for a placeholder
  members: [
    { name: "Vibhor Rajan", role: "Project Manager", does: "Scope, timeline, and website frontend development.", photo: "" },
    { name: "Pratyush Malaviya", role: "Lead Developer", does: "Backend architecture, bringing the metric modules into one consistent codebase, and the press resistance rebuild.", photo: "" },
    { name: "Arpit Gupta", role: "Engineer", does: "Built the StatsBomb data pipeline and the Defensive Recovery and Observed Spatial Dominance metrics.", photo: "" },
    { name: "Ayush", role: "Integration Engineer", does: "Combined the team's metrics, matched player data across sources, validated the ratings, and integrated the results into the website.", photo: "" },
    { name: "Joseph Olutayo", role: "Engineer", does: "Developed the Progressive Line-Breaking Pass metric.", photo: "" },
  ],
};
