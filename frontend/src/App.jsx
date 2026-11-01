import { Component, lazy, Suspense, useEffect, useState } from "react";
import { loadPlayerExperience, playerDataMode } from "./lib/playerDataMode.js";

let Experience, configurationError;
try {
  const configuredMode = playerDataMode(import.meta.env.VITE_PLAYER_DATA_MODE);
  const requestedView = new URLSearchParams(window.location.search).get("view");
  const mode = ["limited-data", "five-attribute-synthetic"].includes(requestedView) ? requestedView : configuredMode;
  if (import.meta.env.DEV && requestedView === "five-attribute-experimental") {
    Experience = lazy(() => import("./dev/FiveAttributeExperimentalExperience.jsx"));
  } else {
    Experience = lazy(() => loadPlayerExperience(mode));
  }
} catch (error) {
  configurationError = error;
}

class ExperienceBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    return this.state.error
      ? <main className="wrap mode-notice" role="alert">Unable to load the selected interface: {String(this.state.error.message)}. No demo fallback was used.</main>
      : this.props.children;
  }
}

export default function App() {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute("data-theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("sac-theme", theme); } catch (e) { /* private mode: fine */ }
  }, [theme]);

  if (configurationError) return <main className="wrap mode-notice" role="alert">{configurationError.message}</main>;
  return <ExperienceBoundary><Suspense fallback={<main className="wrap mode-notice" role="status">Loading selected interface…</main>}>
    <Experience theme={theme} onToggle={() => setTheme(theme === "dark" ? "light" : "dark")} />
  </Suspense></ExperienceBoundary>;
}
