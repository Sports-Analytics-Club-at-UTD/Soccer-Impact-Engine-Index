import { useEffect, useMemo, useRef, useState } from "react";
import { PLAYERS } from "../lib/data.js";
import { useMediaQuery, useTilt } from "../lib/hooks.js";
import { search } from "../lib/search.js";
import PlayerCard from "./PlayerCard.jsx";
import { IconClose, IconSearch, Photo, SectionHead } from "./ui.jsx";

const POSITIONS = ["CB", "DM"]; // GK intentionally excluded

function Highlight({ text, q }) {
  const i = q ? text.toLowerCase().indexOf(q.toLowerCase()) : -1;
  if (i < 0) return text;
  return (<>{text.slice(0, i)}<mark>{text.slice(i, i + q.length)}</mark>{text.slice(i + q.length)}</>);
}

function TopCard({ p, rank, onPick, on }) {
  const tilt = useTilt({ max: 9, scale: 1.04 });
  return (
    <button type="button" {...tilt} onClick={() => onPick(p)}
            className={`tilt sheen card-surface angular-sm top-card ${on ? "on" : ""}`}>
      <span className="rank display" aria-hidden="true">{rank}</span>
      <div className="row">
        <Photo src={p.photo} label="FIFA 16" className="sm" />
        <div className="mono t10 up c2">#{rank} · {p.position}</div>
      </div>
      <div className="name display">{p.name}</div>
      <div className="meta">{p.team} · {p.archetype.name}{p.archetype.tier ? ` ${p.archetype.tier}` : ""}</div>
      <div className="ovr">
        <div className="ovr-num display">{p.ovr}</div>
        <div className="mono t9 up dim">Demo OVR</div>
      </div>
    </button>
  );
}

export default function Search() {
  const [pos, setPos] = useState("CB");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(-1);
  const [selected, setSelected] = useState(null);
  const isMobile = useMediaQuery("(max-width: 959px)");
  const inputRef = useRef(null);

  const ranked = useMemo(
    () => PLAYERS.filter((p) => p.position === pos).sort((a, b) => b.ovr - a.ovr),
    [pos]
  );
  const top3 = ranked.slice(0, 3);
  const { matches, didYouMean } = useMemo(() => search(q, PLAYERS), [q]);

  const pick = (p) => {
    setSelected(p);
    setPos(p.position);
    setQ(p.name);
    setOpen(false);
    setHi(-1);
  };

  useEffect(() => {
    if (!(isMobile && selected)) return;
    const on = (e) => e.key === "Escape" && setSelected(null);
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, [isMobile, selected]);

  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setOpen(true); setHi((h) => Math.min(h + 1, matches.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
    else if (e.key === "Enter") {
      e.preventDefault();
      if (hi >= 0 && matches[hi]) pick(matches[hi]);
      else if (matches[0]) pick(matches[0]);
      else if (didYouMean) pick(didYouMean);
    } else if (e.key === "Escape") setOpen(false);
  };

  const showList = open && q.trim().length > 0 && matches.length > 0;
  const cardOpen = !!selected;

  return (
    <section id="search" className="section">
      <div className="wrap">
        <SectionHead
          eyebrow="Player index"
          title="Search"
          intro="Browse the three highest-rated players per position, or search anyone in the index. Every player has a card."
        />

        <div className="tabs mono reveal" role="tablist" aria-label="Position">
          {POSITIONS.map((p) => (
            <button key={p} type="button" role="tab" aria-selected={pos === p} onClick={() => setPos(p)}>{p}</button>
          ))}
        </div>

        <div className="sub-label mono t10 up reveal">Top 3 overall · {pos === "CB" ? "Centre-backs" : "Defensive midfielders"}</div>
        <div className="top3">
          {top3.map((p, i) => (
            <TopCard key={p.id} p={p} rank={i + 1} onPick={pick} on={selected?.id === p.id} />
          ))}
        </div>

        <div className="search-grid">
          <div>
            <div className="sub-label mono t10 up" style={{ marginTop: 0, marginBottom: 14 }}>Find a player</div>
            <div className="search-box">
              <div className="search-input angular-sm">
                <IconSearch />
                <input
                  ref={inputRef} type="text" value={q} placeholder="Search a player…" autoComplete="off" spellCheck={false}
                  role="combobox" aria-expanded={showList} aria-controls="player-list" aria-autocomplete="list"
                  aria-activedescendant={hi >= 0 ? `opt-${matches[hi]?.id}` : undefined}
                  onChange={(e) => { setQ(e.target.value); setOpen(true); setHi(-1); }}
                  onFocus={() => setOpen(true)}
                  onBlur={() => setTimeout(() => setOpen(false), 120)}
                  onKeyDown={onKey}
                />
                {q && (
                  <button type="button" className="clear" aria-label="Clear search"
                          onClick={() => { setQ(""); inputRef.current?.focus(); }}><IconClose size={14} /></button>
                )}
              </div>

              {showList && (
                <ul id="player-list" role="listbox" className="listbox angular-sm">
                  {matches.map((p, i) => (
                    <li key={p.id} id={`opt-${p.id}`} role="option" aria-selected={hi === i}
                        onMouseDown={(e) => { e.preventDefault(); pick(p); }} onMouseEnter={() => setHi(i)}>
                      <span><Highlight text={p.name} q={q.trim()} /></span>
                      <span className="sm mono">{p.position} · {p.team}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="suggest" aria-live="polite">
              {didYouMean && q.trim() && (
                <>Did you mean <button type="button" onClick={() => pick(didYouMean)}>{didYouMean.name}</button>?</>
              )}
              {!didYouMean && q.trim().length >= 3 && matches.length === 0 && <>No player found for “{q.trim()}”.</>}
            </div>

            <div className="browse">
              <div className="mono t10 up dim" style={{ marginBottom: 6 }}>All {pos} in the index</div>
              {ranked.map((p, i) => (
                <button key={p.id} type="button" className={`browse-row ${selected?.id === p.id ? "on" : ""}`} onClick={() => pick(p)}>
                  <span className="n mono t11">{i + 1}</span>
                  <span className="nm">{p.name}</span>
                  <span className="tm mono">{p.team}</span>
                  <span className="ov mono t11">{p.ovr}</span>
                </button>
              ))}
            </div>

            <div className="placeholder-banner mono angular-sm">
              Demo data: fictional players, percentile profiles and illustrative demo OVR. Raw scorecards use a separate mode (see README).
            </div>
          </div>

          {isMobile && cardOpen && <div className="backdrop" onClick={() => setSelected(null)} />}
          <aside className={`card-col ${cardOpen ? "open" : ""}`} aria-live="polite">
            {selected ? (
              <PlayerCard demo player={selected} onClose={() => setSelected(null)} />
            ) : (
              <div className="empty-card angular">
                <Photo label="FIFA 16 photo" />
                <div className="display" style={{ fontSize: "1.3rem", color: "var(--text)" }}>Player card</div>
                <p style={{ marginTop: 10, lineHeight: 1.6, fontSize: 14 }}>
                  Search a player or pick one from the list to see their archetype, percentile profile and minutes played.
                </p>
              </div>
            )}
          </aside>
        </div>
      </div>
    </section>
  );
}
