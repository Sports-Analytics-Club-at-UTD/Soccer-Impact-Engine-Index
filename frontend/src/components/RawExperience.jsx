import { useEffect, useState } from "react";
import { loadScorecard } from "../lib/scorecardLoader.js";
import { useRevealAll } from "../lib/hooks.js";
import { RAW_METRIC_NOTICE, RAW_MODE_NOTICE } from "../lib/rawScorecardView.js";
import Nav from "./Nav.jsx";
import RawSearch from "./RawSearch.jsx";
import { SectionHead } from "./ui.jsx";

const SECTIONS = [{ id: "home", label: "Raw metrics" }, { id: "search", label: "Player profiles" }];

export default function RawExperience({ theme, onToggle }) {
  useRevealAll();
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState({ status: "loading" });
    loadScorecard({ baseUrl: import.meta.env.BASE_URL, signal: controller.signal })
      .then((model) => { if (active) setState({ status: model.players.length ? "ready" : "empty", model }); })
      .catch((error) => { if (active) setState({ status: "error", error }); });
    return () => { active = false; controller.abort(); };
  }, [attempt]);

  return <>
    <Nav theme={theme} onToggle={onToggle} sections={SECTIONS} />
    <main className="raw-experience">
      <section id="home" className="section raw-home"><div className="wrap">
        <SectionHead eyebrow="Raw scorecard mode" title="Raw player metrics" intro={RAW_MODE_NOTICE} />
        <p className="warn mono angular-sm" role="note">{RAW_METRIC_NOTICE}</p>
      </div></section>
      <section id="search" className="section"><div className="wrap">
        <h2 className="display">Player profiles</h2>
        {state.status === "loading" && <p role="status">Loading raw scorecard…</p>}
        {state.status === "error" && <div role="alert" className="warn mono angular-sm">
          <p>{state.error.message}</p>
          <p>No player profiles are available. Supply a verified, versioned scorecard at the configured asset location; this screen does not fall back to demo data.</p>
          <button className="raw-retry angular-sm" type="button" onClick={() => setAttempt((n) => n + 1)}>Retry raw scorecard</button>
        </div>}
        {state.model && <div role="note" className="raw-note">
          <p>Declared coverage: {state.model.metadata.coverage_status}.</p>
          <ul>{state.model.metadata.limitations.map((text) => <li key={text}>{text}</li>)}</ul>
        </div>}
        {state.status === "empty" && <p role="status" className="empty-card angular">The scorecard loaded successfully but contains no player contexts. No demo players have been substituted.</p>}
        {state.status === "ready" && <RawSearch model={state.model} />}
      </div></section>
    </main>
    <footer className="footer"><div className="wrap mono">Raw scorecard foundation · source coverage unverified</div></footer>
  </>;
}
