import { lazy } from "react";
import { loadPlayerExperience, playerDataMode } from "../lib/playerDataMode.js";
let Experience;
  const configuredMode = playerDataMode(import.meta.env.VITE_PLAYER_DATA_MODE);
  const requestedView = new URLSearchParams(window.location.search).get("view");
  const mode = ["limited-data", "five-attribute-synthetic"].includes(requestedView) ? requestedView : configuredMode;
  if (import.meta.env.DEV && (requestedView === "five-attribute-experimental" || (!requestedView && configuredMode === "demo"))) {
    Experience = lazy(() => import("./FiveAttributeExperimentalExperience.jsx"));
  } else {
    Experience = lazy(() => loadPlayerExperience(mode));
  }
export default function DevelopmentExperience(props) { return <Experience {...props} />; }
