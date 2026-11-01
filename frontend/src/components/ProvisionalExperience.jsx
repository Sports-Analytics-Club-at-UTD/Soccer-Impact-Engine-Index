import { useEffect, useState } from "react";
import Nav from "./Nav.jsx";
import PlayerCard from "./PlayerCard.jsx";
import { loadProvisionalPlayers } from "../lib/provisionalDelivery.js";
import "../diagnostic.css";

const fold = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
export default function ProvisionalExperience({ theme, onToggle }) {
  const [players, setPlayers] = useState(null), [error, setError] = useState("");
  const [query, setQuery] = useState(""), [all, setAll] = useState(false), [selected, setSelected] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    loadProvisionalPlayers({ url: `${import.meta.env.BASE_URL}data/bundesliga-observations.json`, signal: controller.signal })
      .then((rows) => { if (!controller.signal.aborted) setPlayers(rows); })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, []);
  const matches = (players || []).filter((p) => (all || p.bundesliga_candidate) && fold([p.name, p.player_id, ...p.contexts.map((c) => `${c.team} ${c.competition_name}`)].join(" ")).includes(fold(query.trim())));
  return <><Nav theme={theme} onToggle={onToggle} sections={[{ id: "home", label: "Bundesliga observations" }]} />
    <main id="home" className="wrap section diagnostic-experience">
      <h1 className="display">Bundesliga · 2015/16</h1>
      <p className="warn mono" role="note">LIMITED DATA · PARTIAL SEASON</p>
      <p>Verified observed samples, including supported transfers. Numeric ratings are withheld.</p>
      {error ? <p role="alert">{error}. No demo fallback was used.</p> : players === null ? <p role="status">Loading verified observations…</p> : <>
        <div className="diagnostic-controls"><label>Search name, player ID, club or league<input value={query} onChange={(e) => { setQuery(e.target.value); setSelected(null); }} /></label>
          <label><input type="checkbox" checked={all} onChange={(e) => { setAll(e.target.checked); setSelected(null); }} />Include other positions and identity-only profiles</label></div>
        <p role="status">{matches.length} player-season cards · {players.filter((p) => p.bundesliga_candidate).length} supported Bundesliga MID/CB candidates</p>
        <div className="diagnostic-layout"><div className="diagnostic-list">{matches.map((p) => <button key={p.id} type="button" aria-pressed={selected?.id === p.id} onClick={() => setSelected(p)}>
          {p.name}<span>{p.contexts.map((c) => c.team).join(" · ")} · {p.comparison_group ?? "Role unavailable for MID/CB scoring"}</span>
        </button>)}</div><div>{selected ? <PlayerCard player={selected} onClose={() => setSelected(null)} /> : <p>Select a player to inspect supported measurements and sample sizes.</p>}</div></div>
      </>}
    </main></>;
}
