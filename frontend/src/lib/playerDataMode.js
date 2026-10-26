/* Keep demo imports behind an explicit mode boundary, including their scoring. */
export function playerDataMode(value) {
  if (value === undefined) return "demo";
  if (value !== "demo" && value !== "raw") throw new Error(`Unknown VITE_PLAYER_DATA_MODE: ${String(value)}. Use demo or raw.`);
  return value;
}

export function loadPlayerExperience(mode, loaders = {
  demo: () => import("../components/DemoExperience.jsx"),
  raw: () => import("../components/RawExperience.jsx"),
}) {
  return loaders[playerDataMode(mode)]();
}
