/* ═══════════════════════════════════════════════════════════════════════════
   EVERYTHING YOU'LL WANT TO EDIT LIVES HERE (plus src/lib/archetypes.js for
   archetype wording; approved player data is pinned in lib/publicRatingsRelease.js).
   Images: put files in /public and point to them like "/teams/psg-1.png".
   ═══════════════════════════════════════════════════════════════════════════ */

export const SITE = {
  title: "SAC Midfielder/Defender Index",
  org: "UTD Sports Analytics Club",
  season: "2015/16",
};

export const NAV = [
  { id: "home", label: "Home" },
  { id: "description", label: "How it works" },
  { id: "archetypes", label: "Archetypes" },
  { id: "search", label: "Search" },
  { id: "teams", label: "Teams" },
  { id: "about", label: "About us" },
];

export const HERO = {
  subtitle: "The game behind the numbers",
  tagline: "Discover the strengths of centre-backs and midfielders through their performances in 2015/16.",
  cta: "Search a player",
  // Drop your clips in /public and set the path, e.g. "/clips/hero.mp4".
  // Leave empty to show the animated pitch placeholder.
  videoSrc: "",
  poster: "",
};

export const DESCRIPTION = {
  eyebrow: "Understanding the index",
  title: "How our ratings work",
  intro:
    "Real match performances from 2015/16, rated across five football skills. These are independent SAC project ratings, not official FIFA or EA ratings.",
  points: [
    {
      label: "Five football skills",
      body:
        "Tackling, interceptions, recoveries, press resistance and progressive passing: explore how players win the ball, keep it and move play forward.",
    },
    {
      label: "Compare by position",
      body:
        "Centre-backs and midfielders are compared separately. The overall rating combines all five skills, giving greater weight to a player’s strongest abilities.",
    },
    {
      label: "Know the coverage",
      body:
        "Available matches may not cover a full season. Some players have individual ratings but lack enough verified evidence for rankings. Their available ratings are still shown; missing scores display N/A.",
    },
  ],
};

export const TEAMS_SECTION = {
  eyebrow: "Defending as a team",
  title: "Teams",
  intro:
    "Explore the space nearest to each team’s defenders while the opposition had possession. These maps describe the team, rather than individual player ratings.",
};

/* Each team shows one heat map: { label, src, alt, caption }. */
export const TEAMS = [
  {
    id: "psg",
    short: "PSG",
    name: "Paris Saint-Germain",
    note: "The heat map shows the share of recorded space nearest to this team’s defenders when opponents have the ball. It describes defensive positioning, rather than the chance of winning possession.",
    images: [
      { label: "OFF-BALL SPATIAL DOMINANCE", src: "/team/spatial_Paris_Saint-Germain.png", alt: "Paris Saint-Germain team-level off-ball spatial dominance heat map: defender-nearest share of observed space while opponents have possession.", caption: "TEAM-LEVEL HEAT MAP" },
    ],
  },
  {
    id: "barca",
    short: "Barça",
    name: "FC Barcelona",
    note: "The heat map shows the share of recorded space nearest to this team’s defenders when opponents have the ball. It describes defensive positioning, rather than the chance of winning possession.",
    images: [
      { label: "OFF-BALL SPATIAL DOMINANCE", src: "/team/spatial_Barcelona.png", alt: "Barcelona team-level off-ball spatial dominance heat map: defender-nearest share of observed space while opponents have possession.", caption: "TEAM-LEVEL HEAT MAP" },
    ],
  },
  {
    id: "leverkusen",
    short: "Leverkusen",
    name: "Bayer 04 Leverkusen",
    note: "The heat map shows the share of recorded space nearest to this team’s defenders when opponents have the ball. It describes defensive positioning, rather than the chance of winning possession.",
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
    { name: "Vibhor Rajan", role: "Project Manager", does: "Led the project and shaped the website experience.", photo: "" },
    { name: "Pratyush Malaviya", role: "Lead Developer", does: "Brought the five skills together and developed the press resistance analysis.", photo: "" },
    { name: "Arpit Gupta", role: "Engineer", does: "Developed the ball-winning analysis and team defensive maps using StatsBomb match data.", photo: "" },
    { name: "Ayush Mendhe", role: "Integration Engineer", does: "Connected the match evidence, checked the ratings and brought the player profiles to the website.", photo: "" },
    { name: "Joseph Olutayo", role: "Engineer", does: "Developed the progressive passing analysis to explore how players move the ball forward.", photo: "" },
  ],
};
