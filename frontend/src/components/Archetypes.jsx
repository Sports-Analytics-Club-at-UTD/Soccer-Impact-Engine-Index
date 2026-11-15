import { useEffect, useRef, useState } from "react";
import { ARCHETYPES, GROUPS, METRICS, TIER, archetypeLeaders } from "../lib/archetypes.js";
import ExpandingPanel from "./ExpandingPanel.jsx";
import { useTilt } from "../lib/hooks.js";
import { IconArrow, IconClose, IconDown, Photo, SectionHead } from "./ui.jsx";
import PlayerCard from "./PlayerCard.jsx";

const METRIC_LABEL = { ...Object.fromEntries(METRICS.map((m) => [m.key, m.label])), REC: "Ball recoveries", LB: "Progressive passing" };

function Arch({ a, position, onPick, expanded }) {
  const tilt = useTilt({ max: 3, scale: 1.01 });
  return (
    <button type="button" {...tilt} className="tilt sheen card-surface angular-sm arch" onClick={onPick}
            aria-label={`View ${a.name} top 5 · ${position === 'DM' ? 'MID' : position}`}
            aria-expanded={expanded} aria-controls={`leaders-${a.group.replaceAll(' ', '-').toLowerCase()}`}>
      <span className="pos mono t9 up">{position === 'DM' ? 'MID' : position}</span>
      <h4 className="display">{a.name}</h4>
      <div className="metric mono t10 up">Judged on · {METRIC_LABEL[a.metric]}</div>
      <p>{a.blurb}</p>
      <span className="arch-expand mono t10">Top 5 <IconDown /></span>
    </button>
  );
}


export default function Archetypes({ players = [], loaded = false, error = "", onRetry }) {
  const [selected, setSelected] = useState(null), [closing, setClosing] = useState(null), [player, setPlayer] = useState(null);
  const dialog = useRef(null);
  const archetypeTrigger = useRef(null);
  const leadersRegion = useRef(null);
  const previousGroup = useRef(null);
  const scrollTo = (element) => element?.scrollIntoView?.({ block: 'nearest',
    behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  const select = (next) => { setClosing(selected); setSelected(next); };
  useEffect(() => {
    if (selected && (previousGroup.current === selected.a.group || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)) scrollTo(leadersRegion.current);
    previousGroup.current = selected?.a.group;
  }, [selected]);
  useEffect(() => {
    if (!player) return;
    dialog.current.showModal();
    dialog.current.querySelector('.pcard .close')?.focus();
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, [player]);
  return (
    <section id="archetypes" className="section">
      <div className="wrap">
        <SectionHead
          eyebrow="Player styles"
          title="Archetypes"
          intro="Players included in the rankings can earn up to five archetypes, one for each skill at or above the 75th percentile. Each archetype is Gold or Silver, with the strongest shown first. Eligible players with no qualifying skills remain Standard."
        />

        <div className="legend reveal">
          <span className="chip angular-sm mono"><b>Gold</b> {TIER.plus}th percentile and up</span>
          <span className="chip angular-sm mono"><b>Silver</b> {TIER.minus}th to below {TIER.plus}th</span>
          <span className="chip angular-sm mono"><b>Standard</b> below the {TIER.minus}th</span>
        </div>

        <p className="directory-note">Select an archetype to explore its top 5 ranked players.</p>
        <div className="arch-groups">
          {GROUPS.map((g) => {
            const open = selected?.a.group === g;
            const current = open ? selected : closing?.a.group === g ? closing : null;
            const leaders = current ? archetypeLeaders(players, current.position, current.a) : [];
            return (
            <div key={g} className="arch-group reveal">
              <h3>{g === 'Line-breaking passes' ? 'Progressive passing' : g}</h3>
              <div className="arch-grid">
                {["CB", "DM"].flatMap((pos) =>
                  ARCHETYPES[pos].filter((a) => a.group === g).map((a) => <Arch key={a.id} a={a} position={pos}
                    expanded={selected?.a.id === a.id} onPick={(e) => { archetypeTrigger.current = e.currentTarget; select(selected?.a.id === a.id ? null : { a, position: pos }); }} />)
                )}
              </div>
              <ExpandingPanel className="archetype-panel" id={`leaders-${g.replaceAll(' ', '-').toLowerCase()}`} open={open}
                onSettled={(expanded) => {
                  if (expanded) scrollTo(leadersRegion.current);
                  else setClosing((previous) => previous?.a.group === g ? null : previous);
                }}>
                {current && <div ref={open ? leadersRegion : undefined} className="archetype-dropdown" role={open ? 'region' : undefined} aria-labelledby={`archetype-leaders-${g.replaceAll(' ', '-').toLowerCase()}`}>
                  <div className="archetype-dropdown-heading">
                    <div>
                      <div className="leader-context mono">Top 5 · {current.position === 'DM' ? 'Midfielders' : 'Centre-backs'}</div>
                      <h4 key={current.a.id} id={`archetype-leaders-${g.replaceAll(' ', '-').toLowerCase()}`} className="display">{current.a.name}</h4>
                    </div>
                    <button type="button" className="archetype-collapse" aria-label="Close archetype list"
                            onClick={() => { select(null); archetypeTrigger.current?.focus({ preventScroll: true }); scrollTo(archetypeTrigger.current); }}><IconClose size={18} /></button>
                  </div>
                  <p className="directory-note">Ordered by {METRIC_LABEL[current.a.metric].toLowerCase()} within this position. Select a player to open their card.</p>
                  {error ? <div role="alert"><p>We couldn’t load the player ratings.</p><button type="button" className="btn btn-ghost" onClick={onRetry}>Try again</button></div>
                    : !loaded ? <p role="status">Loading player ratings…</p>
                    : !leaders.length ? <p role="status">No ranked players have earned this archetype.</p>
                    : <>
                      <ol key={current.a.id} className="archetype-leaders">{leaders.map((p, i) => {
                        const badge = p.archetypes.find((a) => a.metric === current.a.metric);
                        return <li key={p.id}><button type="button" className={`browse-row leader-card angular-sm ${i === 0 ? 'leader-card-first' : ''}`} data-rank={i + 1}
                          onClick={() => setPlayer(p)} aria-haspopup="dialog">
                          <span className="leader-rank mono" aria-label={`Rank ${i + 1}`}>{String(i + 1).padStart(2, '0')}</span>
                          <Photo src={p.photo} label="" className="leader-portrait" />
                          <span className="leader-info">
                            <span className="nm">{p.name}</span>
                            <span className="leader-clubs">{p.crests?.map((crest) => <img key={crest} src={crest} alt="" width="20" height="20" loading="lazy" />)}{p.team}</span>
                            <span className={`leader-tier mono ${badge.tier === '+' ? 'gold' : 'silver'}`}>{badge.tier === '+' ? 'Gold' : 'Silver'}</span>
                          </span>
                          <span className="leader-action mono">View profile <IconArrow /></span>
                        </button></li>;
                      })}</ol>
                    </>}
                </div>}
              </ExpandingPanel>
            </div>
            );
          })}
        </div>

        <dialog ref={dialog} className="archetype-dialog" aria-label={player ? `${player.name} player profile` : 'Player profile'}
                onClose={() => setPlayer(null)}>
          {player && <PlayerCard player={player} onClose={() => dialog.current.close()} />}
        </dialog>

        <div className="teams-only panel angular-sm reveal">
          <div className="mono t11 up c2" style={{ paddingTop: 3 }}>Teams only</div>
          <div>
            <h4 className="display">Off-ball dominance</h4>
            <p>
              Explore how teams defend space when the opposition has the ball in the Teams section below.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
