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
    "Spatial data only exists at team level, so this is where space is measured. Pick a team to open its visualizations.",
};

/* Add / remove teams freely. Each image: { label, src, caption } — leave src ""
   to show a placeholder. */
export const TEAMS = [
  {
    id: "psg",
    short: "PSG",
    name: "Paris Saint-Germain",
    note: "Placeholder: one or two lines on what stands out about this team's spatial profile.",
    images: [
      { label: "Spatial dominance", src: "/team/spatial_Paris_Saint-Germain.png", alt: "Paris Saint-Germain spatial dominance heatmap: defender-nearest share of observed space while opponents have possession.", caption: "Zone control map" },
      { label: "Pressing zones", src: "", caption: "Where possession is won back" },
      { label: "Off-ball dominance", src: "", caption: "Team-level only" },
    ],
  },
  {
    id: "barca",
    short: "Barça",
    name: "FC Barcelona",
    note: "Placeholder: one or two lines on what stands out about this team's spatial profile.",
    images: [
      { label: "Spatial dominance", src: "/team/spatial_Barcelona.png", alt: "Barcelona spatial dominance heatmap: defender-nearest share of observed space while opponents have possession.", caption: "Zone control map" },
      { label: "Pressing zones", src: "", caption: "Where possession is won back" },
      { label: "Off-ball dominance", src: "", caption: "Team-level only" },
    ],
  },
  {
    id: "leverkusen",
    short: "Leverkusen",
    name: "Bayer 04 Leverkusen",
    note: "Placeholder: one or two lines on what stands out about this team's spatial profile.",
    images: [
      { label: "Spatial dominance", src: "/team/spatial_Bayer_Leverkusen.png", alt: "Bayer Leverkusen spatial dominance heatmap: defender-nearest share of observed space while opponents have possession.", caption: "Zone control map" },
      { label: "Pressing zones", src: "", caption: "Where possession is won back" },
      { label: "Off-ball dominance", src: "", caption: "Team-level only" },
    ],
  },
];

export const ABOUT = {
  eyebrow: "The team",
  title: "About us",
  intro: "Five members of the UTD Sports Analytics Club, eight weeks, one index.",
  // photo: "/team/name.jpg" — leave "" for a placeholder
  members: [
    { name: "Vibhor Rajan", role: "Project Manager", does: "Scope, timeline and keeping the five of us shipping.", photo: "" },
    { name: "Pratyush Malaviya", role: "Lead Developer", does: "Architecture, pipeline and the build you're looking at.", photo: "" },
    { name: "Arpit Gupta", role: "Engineer", does: "Placeholder: what Arpit worked on.", photo: "" },
    { name: "Ayush Mendhe", role: "Engineer", does: "Placeholder: what Ayush worked on.", photo: "" },
    { name: "Joseph Olutayo", role: "Engineer", does: "Placeholder: what Joseph worked on.", photo: "" },
  ],
};
