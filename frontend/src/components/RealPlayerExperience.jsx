import { useEffect, useMemo, useRef, useState } from "react";
import Nav from "./Nav.jsx";
import Teams from "./Teams.jsx";
import { useRevealAll } from "../lib/hooks.js";
import { FiveAttributeCardView } from "./FiveAttributePlayerCard.jsx";
import { FiveAttributeComparisonView } from "./FiveAttributeComparison.jsx";
import { EXPERIMENTAL_LEAGUES, filterExperimentalPlayers } from "../lib/playerDiscovery.js";
import { loadPublicRatings, publicModels, validatePublicPlayer } from "../lib/publicRatingsDelivery.js";
import { formatOvr, ovrLeaderboard, OVR_EXPLANATION } from '../lib/provisionalOvr.js';
import { ATTRIBUTE_BADGE_METHODOLOGY } from '../lib/componentClassification.js';
import { playerDataStatus } from '../lib/playerDataStatus.js';
import { LOCAL_SECTIONS, readLocalRoute, localHref, isPlainNavigation } from '../lib/localNavigation.js';
import "../fiveAttribute.css";
import "../realPlayers.css";

const PAGE_SIZE = 30;
function PlayerSeasonSelect({ label, players, value, onChange }) {
  return <label>{label}<select value={value ?? ''} onChange={(e) => onChange(e.target.value || null)}>
    <option value="">Choose a player-season</option>
    {players.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.presentation.comparison_position} · {p.presentation.player_id}</option>)}
  </select></label>;
}

export default function RealPlayerExperience({ theme, onToggle, loadRatings = loadPublicRatings, models = publicModels, validatePlayer = validatePublicPlayer, local = false }) {
  const [route, setRoute] = useState(() => readLocalRoute(typeof window === 'undefined' ? '' : window.location.hash));
  const [data, setData] = useState(null), [players, setPlayers] = useState([]), [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [focusRequest, setFocusRequest] = useState(0);
  const [query, setQuery] = useState(''), [league, setLeague] = useState(''), [position, setPosition] = useState(''), [coverage, setCoverage] = useState(''), [limited, setLimited] = useState(false), [page, setPage] = useState(0);
  const heading = useRef(null), detail = useRef(null);
  useRevealAll();
  useEffect(() => {
    const restore = () => setRoute(readLocalRoute(window.location.hash));
    window.addEventListener('popstate', restore); window.addEventListener('hashchange', restore);
    return () => { window.removeEventListener('popstate', restore); window.removeEventListener('hashchange', restore); };
  }, []);
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    setData(null); setPlayers([]); setError('');
    loadRatings({ signal: controller.signal }).then((d) => {
      if (!active) return;
      if (local && !d.ovr_integration) throw Error('Versioned Formula B data unavailable; restart the local adapter. No fallback was loaded.');
      setData(d); setPlayers(models(d));
    }).catch((e) => { if (active && e.name !== 'AbortError') setError(e.message); });
    return () => { active = false; controller.abort(); };
  }, [retry, loadRatings, models, local]);
  const byId = (id) => players.find((p) => p.id === id) ?? null;
  const selected = byId(route.playerId), first = byId(route.firstId), second = byId(route.secondId);
  const leaderboard = useMemo(() => ovrLeaderboard(players, route.group), [players, route.group]);
  const matches = useMemo(() => filterExperimentalPlayers(players, { query, league, position, coverage, limited }), [players, query, league, position, coverage, limited]);
  const pickerPlayers = useMemo(() => filterExperimentalPlayers(players), [players]);
  const visiblePage = Math.min(page, Math.max(0, Math.ceil(matches.length / PAGE_SIZE) - 1));
  const shown = matches.slice(visiblePage * PAGE_SIZE, (visiblePage + 1) * PAGE_SIZE);
  const sections = useMemo(() => LOCAL_SECTIONS.map((s) => ({ ...s, href: localHref({ ...route, view: s.id }) })), [route]);
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const target = route.view === 'players' && selected ? detail.current?.querySelector('h2') : heading.current;
      if (target) { target.tabIndex = -1; target.focus({ preventScroll: true }); target.scrollIntoView({ block: 'start', behavior: 'instant' }); }
    });
    return () => cancelAnimationFrame(frame);
  }, [route.view, route.playerId, Boolean(data), focusRequest]);
  function navigate(view, patch = {}, event) {
    if (event && !isPlainNavigation(event)) return;
    event?.preventDefault();
    const next = { ...route, ...patch, view }, href = localHref(next);
    if (window.location.hash !== href) window.history.pushState(null, '', href);
    setRoute(next);
  }
  function openPlayer(p, preservePair = false) {
    setFocusRequest((n) => n + 1);
    navigate('players', { playerId: p.id, ...(preservePair ? {} : { firstId: p.id }) });
  }
  function update(setter, value) { setter(value); setPage(0); }
  for (const p of [selected, first, second]) if (p) validatePlayer(p.presentation, p.reference);
  const needsData = ['players', 'leaderboards', 'compare'].includes(route.view);
  const title = route.view === 'home' ? 'Soccer Impact Index' : LOCAL_SECTIONS.find((s) => s.id === route.view).label;
  return <><Nav theme={theme} onToggle={onToggle} sections={sections} activeSection={route.view} onNavigate={(view, event) => navigate(view, {}, event)} />
    <main className="wrap section five-experience experimental-experience unified-local">
      <header className="experimental-intro"><p className="mono experimental-kicker">SAC INDEX · {local ? 'LOCAL DEVELOPMENT PREVIEW' : '2015/16 PLAYER RATINGS'}</p>
        <h1 ref={heading} tabIndex={-1} className={`display${route.view === 'teams' ? ' unified-visually-hidden' : ''}`}>{title}</h1>
      </header>
      {route.view === 'home' && <>
        <p className="unified-intro">Explore measured player strengths and team space. Five attributes, one provisional Formula B overall rating, and separate midfield and centre-back rankings.</p>
        <p>2015/16 observations have uneven match coverage. These experimental ratings describe the available evidence; they do not establish complete seasons or validated player quality.</p>
        <div className="unified-destinations">{LOCAL_SECTIONS.filter((s) => !['home', 'about'].includes(s.id)).map((s) => <a key={s.id} href={localHref({ ...route, view: s.id })} onClick={(e) => navigate(s.id, {}, e)}><strong className="display">{s.label}</strong><span>{{ players: 'Find a player and explore their attributes.', leaderboards: 'Compare strictly eligible MID and CB profiles.', compare: 'Place two player-seasons side by side.', teams: "Explore Arpit’s team-level spatial heatmaps." }[s.id]}</span></a>)}</div>
        {data && <div className="experimental-summary" aria-label="Experimental dataset coverage"><span><strong>{data.counts.available}</strong> player-seasons with supported scores</span><span><strong>{data.counts.complete}</strong> complete five-score profiles</span><span><strong>{data.counts.partial}</strong> incomplete profiles</span><span><strong>{data.counts.bundesliga_complete + data.counts.bundesliga_partial}</strong> Bundesliga contributors · Limited Data</span></div>}
        <a href={localHref({ ...route, view: 'about' })} onClick={(e) => navigate('about', {}, e)}>How the index works</a>
      </>}
      {(needsData || route.view === 'home') && error && <section role="alert" className="experimental-error"><h2>Player data unavailable</h2><p>{error}</p><button type="button" onClick={() => setRetry((n) => n + 1)}>Retry player data</button><p>Team heatmaps and methodology remain available.</p></section>}
      {(needsData || route.view === 'home') && !data && !error && <p role="status">Loading and validating player observations…</p>}
      {route.view === 'players' && data && <>
        <section id="experimental-discovery" aria-label="Find real experimental players" className="experimental-discovery">
          <h2 className="display">Find a player-season</h2>
          <label className="experimental-search">Search name, ID, club, league or position<input type="search" value={query} placeholder="Kanté, 5574, Juventus, Bundesliga, CB…" onChange={(e) => update(setQuery, e.target.value)} /></label>
          <div className="experimental-filters">
            <label>League<select value={league} onChange={(e) => update(setLeague, e.target.value)}><option value="">All five leagues</option>{EXPERIMENTAL_LEAGUES.map((l) => <option key={l} value={l}>{l === '1. Bundesliga' ? 'Bundesliga' : l}</option>)}</select></label>
            <label>Comparison position<select value={position} onChange={(e) => update(setPosition, e.target.value)}><option value="">MID and CB</option><option>MID</option><option>CB</option></select></label>
            <label>Rating coverage<select value={coverage} onChange={(e) => update(setCoverage, e.target.value)}><option value="">Complete and partial</option><option value="complete">All five ratings</option><option value="partial">Partial ratings</option></select></label>
            <label className="experimental-checkbox"><input type="checkbox" checked={limited} onChange={(e) => update(setLimited, e.target.checked)} />Any LIMITED DATA warning</label>
          </div>
          <p role="status">{matches.length} matching player-seasons · Showing {matches.length ? visiblePage * PAGE_SIZE + 1 : 0}–{Math.min((visiblePage + 1) * PAGE_SIZE, matches.length)}. Alphabetical order; no ranking.</p>
          <ul className="experimental-results">{shown.map((p) => { const status = playerDataStatus(p); return <li key={p.id}>
            <div><strong>{p.name}</strong><span>{p.presentation.clubs.map((c) => c.name).join(' · ')}</span><span className="mono">{p.presentation.player_id} · {p.presentation.comparison_position}</span><span>OVR {formatOvr(p.ovr)} · Formula B{status.limited ? ` · ${status.label}` : ''}</span></div>
            <div className="experimental-result-actions"><button type="button" aria-pressed={selected?.id === p.id} aria-label={`View ${p.name}`} onClick={() => openPlayer(p)}>View card</button><button type="button" aria-label={`Compare ${p.name}`} onClick={() => navigate('compare', { firstId: route.firstId ?? p.id, secondId: route.firstId ? p.id : route.secondId })}>Compare</button></div>
          </li>; })}</ul>
          {!matches.length && <p>No matching players. Try another name or clear the filters.</p>}
          <div className="experimental-pagination"><button type="button" disabled={visiblePage === 0} onClick={() => setPage(visiblePage - 1)}>Previous</button><button type="button" disabled={(visiblePage + 1) * PAGE_SIZE >= matches.length} onClick={() => setPage(visiblePage + 1)}>Next</button><button type="button" onClick={() => { setQuery(''); setLeague(''); setPosition(''); setCoverage(''); setLimited(false); setPage(0); }}>Clear filters</button></div>
        </section>
        {selected ? <section ref={detail} id="experimental-selected-card" aria-label="Selected experimental player">
          <button type="button" onClick={() => navigate('compare', { firstId: selected.id })}>Compare this player</button>
          <FiveAttributeCardView presentation={selected.presentation} reference={selected.reference} ovr={selected.ovr} componentClassification={selected.componentClassification} compactCoverage onClose={() => navigate('players', { playerId: null })} radarLabel={`${selected.name} five-axis experimental ratings`} />
        </section> : <p>{route.playerId ? 'Requested player-season is unavailable in this dataset.' : 'Select a player to view their ratings, badges and measurements.'}</p>}
      </>}
      {route.view === 'leaderboards' && data && <section aria-label="Formula B leaderboard" className="experimental-discovery">
        <h2 className="display">Provisional Formula B leaderboard</h2><p>Only strictly eligible profiles are ranked. Coverage is observational; ranking does not establish a complete season.</p>
        <label>Leaderboard position<select value={route.group} onChange={(e) => navigate('leaderboards', { group: e.target.value })}><option>MID</option><option>CB</option></select></label>
        <p>{leaderboard.length} eligible {route.group} player-seasons · OVR descending · exact ties ordered by player ID.</p>
        <ol className="experimental-results">{leaderboard.map((p, i) => <li key={p.id}><div><strong>{i + 1}. {p.name}</strong><span>{p.presentation.comparison_position} · OVR {formatOvr(p.ovr)}</span></div><button type="button" onClick={() => openPlayer(p)}>View {p.name}</button></li>)}</ol>
      </section>}
      {route.view === 'compare' && data && <>
        <div className="unified-pickers"><PlayerSeasonSelect label="First player-season" players={pickerPlayers} value={route.firstId} onChange={(firstId) => navigate('compare', { firstId })} /><PlayerSeasonSelect label="Second player-season" players={pickerPlayers} value={route.secondId} onChange={(secondId) => navigate('compare', { secondId })} /></div>
        {first && second ? <>
          <div className="unified-detail-links"><button type="button" onClick={() => openPlayer(first, true)}>View {first.name} details</button><button type="button" onClick={() => openPlayer(second, true)}>View {second.name} details</button></div>
          <div id="experimental-comparison"><FiveAttributeComparisonView players={[first, second]} label="Real experimental player comparison" heading="Compare player-seasons" showRadars showDifferences compactCoverage /></div>
        </> : <p>{[route.firstId, route.secondId].some((id) => id && !byId(id)) ? 'A requested player-season is unavailable. Choose from the available dataset.' : 'Choose two different player-seasons to compare.'}</p>}
      </>}
      <div className="unified-teams" hidden={route.view !== 'teams'}><Teams /><p>Off-Ball Spatial Dominance by Arpit Gupta. These retained team heatmaps do not establish player-level spatial ratings or a verified match, season or frame-selection scope.</p></div>
      {route.view === 'about' && <section className="unified-methodology" aria-label="About and methodology">
        <p>Soccer Impact Index is a UTD Sports Analytics Club experiment in measured player strengths and team space. Player observations come from the available 2015/16 dataset.</p>
        <details><summary>Five measured attributes</summary><p>Tackling, successful interceptions and ball recovery use observed events per 90 supported minutes. Press Resistance measures successful pressured passes and dribbles as a share of attempts. Progressive Passing Proxy measures successful open-play progressive passes per 90; it does not verify opponent defensive lines.</p><p>Ratings and percentiles use the existing separate MID (DM + CM) and CB references. An unavailable measurement remains N/A.</p></details>
        <details><summary>Formula B overall rating</summary><p>{OVR_EXPLANATION}</p><p>All five attributes are required. This provisional project rating has not been independently validated as player quality and is not an official EA Sports FC/FIFA rating.</p></details>
        <details><summary>Rankings and Limited Data</summary><p>The existing strict leaderboard criteria require complete aligned observed exposure and metric scopes, at least 900 verified minutes, at least 40 supported pressured actions, membership in all five position-specific references, four-league-only observations and no pending excluded fixture. MID and CB rank separately.</p><p>Limited Data includes coverage warnings and exclusion from the strict leaderboard. Available measurements remain visible; incomplete profiles have OVR N/A. Missing matches are not zero-action performances.</p></details>
        <details><summary>Gold and Silver attribute badges</summary><p>{ATTRIBUTE_BADGE_METHODOLOGY}</p><p>Badges apply to each attribute independently. They are not overall player tiers or positional archetypes.</p></details>
        <details><summary>Coverage, team analytics and delivery</summary><p>Available fixtures do not certify complete seasons. Bundesliga coverage is uneven and does not contribute to the frozen reference baseline. Player details retain coverage warnings and ranking exclusion reasons. The public package contains final ratings, not raw research evidence.</p><p>Arpit Gupta’s Off-Ball Spatial Dominance heatmaps are team-level visualizations. Their source season, matches and selected frames are not established here.</p><p>The team has approved publication of the final 2015/16 ratings. Production uses a versioned, fingerprint-verified static package. Research datasets and reference membership are not distributed.</p></details>
      </section>}
    </main>
  </>;
}
