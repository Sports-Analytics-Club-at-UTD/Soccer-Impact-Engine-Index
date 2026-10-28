import { useRef, useState } from "react";
import Nav from "./Nav.jsx";
import PlayerCard from "./PlayerCard.jsx";
import { readRatingFile, RATING_NOTICE } from "../lib/ratingDelivery.js";
import "../diagnostic.css";

export default function RatingExperience({ theme, onToggle }) {
  const [players, setPlayers] = useState([]), [error, setError] = useState("");
  const [query, setQuery] = useState(""), [selected, setSelected] = useState(null);
  const generation = useRef(0), input = useRef(null);
  async function importFile(event) {
    const ticket = ++generation.current;
    setPlayers([]); setSelected(null); setError(""); setQuery("");
    try {
      const rows = await readRatingFile(event.target.files?.[0]);
      if (ticket === generation.current) setPlayers(rows);
    } catch (e) { if (ticket === generation.current) setError(e.message); }
  }
  const matches = players.filter((p) => [p.name,p.player_id,p.team,p.competition_name].some((v) => v.toLowerCase().includes(query.toLowerCase())));
  return <><Nav theme={theme} onToggle={onToggle} sections={[{ id: "home", label: "Local rating preview" }]} />
    <main id="home" className="wrap section diagnostic-experience">
      <h1 className="display">Local rating pipeline preview</h1>
      <p className="warn mono" role="note">{RATING_NOTICE}</p>
      <p>Candidate calculations for invented actors. Diagnostic real-player imports retain withheld ratings. Files stay in this browser.</p>
      <label>Choose rating delivery JSON<input ref={input} type="file" accept=".json,application/json" onChange={importFile} /></label>
      <button type="button" onClick={() => { generation.current++; setPlayers([]); setSelected(null); setError(""); setQuery(""); if (input.current) input.current.value = ""; }}>Clear import</button>
      {error && <p role="alert">{error}. No demo fallback was used.</p>}
      {!players.length && !error && <p role="status">No rating delivery imported.</p>}
      {!!players.length && <><label>Search name, canonical ID, team or league<input value={query} onChange={(e) => setQuery(e.target.value)} /></label>
        <p role="status">{matches.length} matching contexts</p>
        <div className="diagnostic-layout"><div className="diagnostic-list">{matches.map((p) =>
          <button key={p.id} type="button" aria-pressed={selected?.id === p.id} onClick={() => setSelected(p)}>
            {p.name} · {p.team} · {p.player_id} · {p.classification}
          </button>)}</div><div>{selected && <PlayerCard player={selected} onClose={() => setSelected(null)} />}</div></div></>}
    </main></>;
}
