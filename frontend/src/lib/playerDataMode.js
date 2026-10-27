/* Keep demo imports behind an explicit mode boundary, including their scoring. */
export function playerDataMode(value) {
  if (value === undefined) return "demo";
  if (!["demo", "raw", "diagnostic"].includes(value)) throw new Error(`Unknown VITE_PLAYER_DATA_MODE: ${String(value)}. Use demo, raw or diagnostic.`);
  return value;
}

export function loadPlayerExperience(mode, loaders = {
  demo: () => import("../components/DemoExperience.jsx"),
  raw: () => import("../components/RawExperience.jsx"),
  diagnostic: () => import("../components/DiagnosticExperience.jsx"),
}) {
  return loaders[playerDataMode(mode)]();
}
