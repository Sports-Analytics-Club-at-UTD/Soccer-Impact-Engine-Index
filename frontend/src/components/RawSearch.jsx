import { useEffect, useMemo, useRef, useState } from "react";
import { adjacentContext, BROWSE_LABEL, browsePlayers, contextLabel, playerLabel,
  positionLabel, positionOptions, selectContext } from "../lib/rawScorecardView.js";
import RawPlayerCard from "./RawPlayerCard.jsx";
import { IconSearch } from "./ui.jsx";

export default function RawSearch({ model }) {
  const [query, setQuery] = useState("");
  const [position, setPosition] = useState("");
  const [selectedKey, setSelectedKey] = useState(null);
  const input = useRef(null), card = useRef(null), buttons = useRef(new Map());
  const options = useMemo(() => positionOptions(model.players), [model.players]);
  const visible = useMemo(() => browsePlayers(model.players, { query, position }), [model.players, query, position]);
  const selected = selectContext(model.players, selectedKey);

  useEffect(() => { if (selectedKey) card.current?.focus(); }, [selectedKey]);
  const close = () => {
    const previous = selectedKey;
    setSelectedKey(null);
    (buttons.current.get(previous) ?? input.current)?.focus();
  };
  const move = (event, key = null) => {
    if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
    event.preventDefault();
    const next = adjacentContext(visible, key, event.key === "ArrowDown" ? 1 : -1);
    buttons.current.get(next)?.focus();
  };

  return <div className="search-grid raw-search-grid">
    <div>
      <label className="mono raw-control-label" htmlFor="raw-position">Position group</label>
      <select id="raw-position" className="raw-position angular-sm" value={position} onChange={(e) => setPosition(e.target.value)}>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      <label className="mono raw-control-label" htmlFor="raw-query">Search by name or exact player ID</label>
      <div className="search-input angular-sm">
        <IconSearch />
        <input id="raw-query" ref={input} type="search" value={query} autoComplete="off" spellCheck={false}
          aria-controls="raw-profiles" onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => move(e)} />
      </div>
      <h3 className="sub-label mono">{BROWSE_LABEL}</h3>
      <p className="raw-note">Canonical browse order, not a ranking. Arrow keys move between profile buttons; Enter selects a context.</p>
      <p role="status" className="raw-note">{visible.length} available context{visible.length === 1 ? "" : "s"} matching the current filters.</p>
      {!visible.length && <p className="empty-card angular">No player contexts match this search and position group.</p>}
      <ul id="raw-profiles" className="browse raw-browse" aria-label={BROWSE_LABEL}>
        {visible.map((player) => <li key={player.context_key}>
          <button type="button" className={`browse-row raw-browse-row ${selectedKey === player.context_key ? "on" : ""}`}
            ref={(el) => { if (el) buttons.current.set(player.context_key, el); else buttons.current.delete(player.context_key); }}
            aria-pressed={selectedKey === player.context_key} onKeyDown={(e) => move(e, player.context_key)}
            onClick={() => setSelectedKey(player.context_key)}>
            <span className="nm">{playerLabel(player)}</span>
            <span className="raw-note">{contextLabel(player)}</span>
            <span className="mono raw-note">{positionLabel(player)} · Player ID: {player.player_id}</span>
          </button>
        </li>)}
      </ul>
    </div>
    <aside className="raw-card-column" aria-label="Selected player context" tabIndex={-1} ref={card}
      onKeyDown={(e) => { if (e.key === "Escape" && selected) { e.preventDefault(); close(); } }}>
      {selected ? <RawPlayerCard key={selected.context_key} player={selected} metadata={model.metadata} onClose={close} />
        : <div className="empty-card angular">Select an available player context to view raw measurements and source limitations.</div>}
    </aside>
  </div>;
}
