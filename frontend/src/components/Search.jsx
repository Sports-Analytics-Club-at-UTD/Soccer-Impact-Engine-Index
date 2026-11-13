import { useEffect, useMemo, useRef, useState } from "react";
import { displayOverall } from "../lib/foundationPlayers.js";
import { useMediaQuery, useTilt } from "../lib/hooks.js";
import { search } from "../lib/search.js";
import { directoryPage } from "../lib/directoryPage.js";
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
        <Photo src={p.photo} label="Player photo" className="sm" />
        <div className="mono t10 up c2">#{rank} · {p.position === 'DM' ? 'MID' : p.position}</div>
      </div>
      <div className="name display">{p.name}</div>
      <div className="meta">{p.team} · {p.archetype.name}{p.archetype.tier ? ` · ${p.archetype.tier === '+' ? 'Gold' : 'Silver'}` : ""}{p.archetypes?.length > 1 ? ` · +${p.archetypes.length - 1} more` : ''}</div>
      <div className="ovr">
        <div className="ovr-num display">{displayOverall(p.ovr)}</div>
        <div className="mono t9 up dim">Overall rating</div>
      </div>
    </button>
  );
}

export default function Search({ players = [], loaded = false, error = "", onRetry }) {
  const [pos, setPos] = useState("CB");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(-1);
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState(1);
  const isMobile = useMediaQuery("(max-width: 959px)");
  const inputRef = useRef(null);

  const ranked = useMemo(
    () => players.filter((p) => p.position === pos).sort((a, b) => Number(b.ranked === true) - Number(a.ranked === true) || (b.ovr ?? -1) - (a.ovr ?? -1)),
    [pos, players]
  );
  const top3 = ranked.filter((p) => p.ranked).slice(0, 3);
  const { pageCount, currentPage, pageStart, directory } = directoryPage(ranked, page);
  useEffect(() => { setPage(1); }, [pos, players]);
  const { matches, didYouMean } = useMemo(() => search(q, players), [q, players]);

  const switchPosition = (position) => {
    setPos(position);
    setPage(1);
    setQ("");
    setSelected(null);
    setOpen(false);
    setHi(-1);
  };

  const pick = (p) => {
    setSelected(p);
    setPos(p.position);
    setQ(p.name);
    setOpen(false);
    setHi(-1);
  };

  useEffect(() => {
    if (!selected) return;
    const on = (e) => e.key === "Escape" && setSelected(null);
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, [isMobile, selected]);

  useEffect(() => {
    if (!(isMobile && selected)) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previous; };
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

        {error && <div role="alert"><p>We couldn’t load the player ratings.</p><button type="button" className="btn btn-ghost" style={{ marginTop: 12 }} onClick={onRetry}>Try again</button></div>}
        {!loaded && !error && <p role="status">Loading player ratings…</p>}
        {loaded && !error && <>
        <div className="sub-label mono t10 up reveal">Top 3 · {pos === "CB" ? "Centre-backs" : "Midfielders"}</div>
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
                  role="combobox" aria-label="Search players" aria-expanded={showList} aria-controls="player-list" aria-autocomplete="list"
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
                      <span className="sm mono">{p.position === 'DM' ? 'MID' : p.position} · {p.team}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="suggest" aria-live="polite">
              {didYouMean && q.trim() && (
                <>Did you mean <button type="button" onClick={() => pick(didYouMean)}>{didYouMean.name}</button>?</>
              )}
              {!didYouMean && q.trim().length >= 3 && matches.length === 0 && <>No player found for “{q.trim().replaceAll("\u2014", ",")}”.</>}
            </div>

            <div className="browse">
              <div className="directory-heading">
                <div>
                  <h3 className="mono t11 up">All Players</h3>
                  <p className="mono t10 mute">{pos === "CB" ? "Centre-backs" : "Defensive midfielders"}</p>
                </div>
                <div className="position-toggle mono" role="group" aria-label="Player directory position">
                  {POSITIONS.map((position) => (
                    <button key={position} type="button" aria-pressed={pos === position}
                            onClick={() => switchPosition(position)}>{position}</button>
                  ))}
                </div>
              </div>
              {directory.map((p, i) => (
                <button key={p.id} type="button" className={`browse-row ${selected?.id === p.id ? "on" : ""}`} onClick={() => pick(p)}>
                  <span className="n mono t11" aria-label={`Browse position ${pageStart + i + 1}`}>{pageStart + i + 1}</span>
                  <span className="nm">{p.name}{!p.ranked && <span className="directory-status mono">Not ranked</span>}</span>
                  <span className="tm mono">{p.team}</span>
                  <span className="ov mono t11">{displayOverall(p.ovr)}</span>
                </button>
              ))}
              <nav className="directory-pages mono t11" aria-label="Player directory pages">
                <button type="button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>Previous</button>
                <span role="status">Page {currentPage} of {pageCount} · {ranked.length} players</span>
                <button type="button" disabled={currentPage === pageCount} onClick={() => setPage(currentPage + 1)}>Next</button>
              </nav>
            </div>

            <div className="placeholder-banner mono angular-sm">
              Top 3 includes ranked players only. The directory shows ranked players first, then unranked players, each ordered by overall rating. Directory numbers show browsing order. Search covers everyone.
            </div>
          </div>

          {isMobile && cardOpen && <div className="backdrop" onClick={() => setSelected(null)} />}
          <aside className={`card-col ${cardOpen ? "open" : ""}`} aria-live="polite">
            {selected ? (
              <PlayerCard player={selected} onClose={() => setSelected(null)} />
            ) : (
              <div className="empty-card angular">
                <Photo label="Player profile" />
                <div className="display" style={{ fontSize: "1.3rem", color: "var(--text)" }}>Player card</div>
                <p style={{ marginTop: 10, lineHeight: 1.6, fontSize: 14 }}>
                  Search a player or pick one from the list to see their archetype, percentile profile and minutes played.
                </p>
              </div>
            )}
          </aside>
        </div>
        </>}
      </div>
    </section>
  );
}
