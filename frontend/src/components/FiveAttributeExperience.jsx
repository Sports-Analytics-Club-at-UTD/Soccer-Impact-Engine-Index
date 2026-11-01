import { useEffect, useState } from "react";
import Nav from "./Nav.jsx";
import PlayerCard from "./PlayerCard.jsx";
import FiveAttributeComparison from "./FiveAttributeComparison.jsx";
import fixture from "../fixtures/syntheticFiveAttributes.json";
import { FIVE_NOTICE, fiveAttributePlayers, parseFiveAttributeDelivery } from "../lib/fiveAttributePresentation.js";
import "../fiveAttribute.css";

export default function FiveAttributeExperience({ theme, onToggle }) {
  const [players, setPlayers] = useState([]), [selected, setSelected] = useState(null), [other, setOther] = useState(null), [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    parseFiveAttributeDelivery(fixture).then((d) => {
      if (!active) return; const rows = fiveAttributePlayers(d);
      setPlayers(rows); setSelected(rows[0]); setOther(rows[1]);
    }).catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  return <><Nav theme={theme} onToggle={onToggle} sections={[{ id: "home", label: "Synthetic readiness" }]} />
    <main id="home" className="wrap section five-experience">
      <h1 className="display">Five-attribute card readiness</h1>
      <p className="warn mono" role="note">{FIVE_NOTICE}</p>
      <p>Invented players and frozen test references. Explore a transfer, a centre-back, limited Bundesliga coverage and missing measurements.</p>
      {error && <p role="alert">These example profiles are unavailable. Please refresh the page.</p>}
      {!players.length && !error && <p role="status">Validating synthetic fixtures…</p>}
      {!!players.length && <>
        <label>Player-season <select value={selected?.id ?? ""} onChange={(e) => setSelected(players.find((p) => p.id === e.target.value) ?? null)}>
          <option value="">Choose a synthetic player</option>{players.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select></label>
        <p role="status">{players.length} distinct synthetic player-seasons. Transfers share one card.</p>
        {selected && <PlayerCard player={selected} onClose={() => setSelected(null)} />}
        <label>Compare with <select value={other?.id ?? ""} onChange={(e) => setOther(players.find((p) => p.id === e.target.value) ?? null)}>
          <option value="">Choose a second synthetic player</option>{players.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select></label>
        {selected && other && <FiveAttributeComparison players={[selected, other]} />}
      </>}
    </main>
  </>;
}
