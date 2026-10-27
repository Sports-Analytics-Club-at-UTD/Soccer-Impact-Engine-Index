import { useRef, useState } from "react";
import Nav from "./Nav.jsx";
import { useRevealAll } from "../lib/hooks.js";
import { SectionHead } from "./ui.jsx";
import { readDiagnosticFile, RECOVERY_TYPES, PRESS_COUNTS, PRESS_RATES } from "../lib/diagnosticAdapter.js";
import { DIAGNOSTIC_NOTICE, profileName, profileContext, browseDiagnosticProfiles, selectDiagnosticProfile,
  diagnosticWindow, diagnosticValue as value, reasonText, zeroMinuteWarning } from "../lib/diagnosticView.js";
import "../diagnostic.css";

const SECTIONS = [{ id: "home", label: "Diagnostic import" }, { id: "search", label: "Player profiles" }];
const LABELS = { Tackle: "Successful tackles", Interception: "Interceptions", "Ball Recovery": "Ball recoveries" };
function Reasons({ items }) { return items?.length ? <p className="diagnostic-reasons">{items.map(reasonText).join("; ")}</p> : null; }
function Profile({ player, match }) {
  const window = diagnosticWindow(player, match);
  if (!window) return <p role="status">No observed metrics for this player in the selected match.</p>;
  return <article className="diagnostic-profile angular">
    <h2 className="display">{profileName(player)}</h2><p>{profileContext(player)}</p>
    <p className="mono">Player ID {player.identity.player_id} · {match ? `Match ${match}` : "Pooled observed window"}</p>
    <p>Included matches: {window.scope_match_ids.join(", ")}</p>
    {zeroMinuteWarning(player) && <p role="note" className="warn">Observed activity with zero delivered minutes. Wider-scope minutes cannot support a per90 denominator.</p>}
    <h3>Recovery events</h3><div className="diagnostic-metrics">
      {RECOVERY_TYPES.map((k) => { const r = window.recovery[k]; return <section key={k}>
        <h4>{LABELS[k]}</h4><strong>{value(r.count)}</strong><p>events · {r.status === "missing" ? "No measurement available" : "Observed"}</p>
        <p>Per90: {value(r.per90.value)}</p><Reasons items={r.per90.reasons} />
        <h5>Recovery zones · 3 × 3</h5>{r.zone_counts === null ? <p>N/A — no zone measurement</p> : <>
          <div className="diagnostic-zones" aria-label={`${LABELS[k]} zone counts`}>{Array.from({ length: 9 }, (_, i) =>
            <div key={i}>Zone {i + 1}<b>{r.zone_counts.find((z) => z.zone === i + 1)?.count ?? "—"}</b></div>)}</div>
          <p>Unknown zone: {r.unknown_zone_count}. — = no recorded zone entry.</p></>}
      </section>; })}</div>
    <h3>Playing under pressure</h3><div className="diagnostic-metrics">
      {PRESS_COUNTS.map((k) => <section key={k}><h4>{reasonText(k)}</h4><strong>{value(window.press.counts[k])}</strong><p>{window.press.status === "missing" ? "No measurement available" : "events"}</p></section>)}
      {PRESS_RATES.map((k) => { const r = window.press.percentages[k]; return <section key={k}><h4>{reasonText(k)}</h4><strong>{value(r.value)}{r.value !== null ? "%" : ""}</strong><p>{reasonText(r.status)}</p></section>; })}</div>
    <h3>Progression / line-breaking</h3><p>Not yet assessed</p>
    <h3>Exposure and limitations</h3><p>Aligned minutes: {value(window.exposure.aligned_minutes)} · {window.exposure.status}</p>
    <Reasons items={window.exposure.reasons} />
    <p>Wider-scope delivered minutes: {value(player.pooled.exposure.delivered_minutes)} — never used as the match-window denominator.</p>
    <p>NOT YET PRODUCTION-VERIFIED. Identity lineage is contributor-reported; match context is event-derived, not an independent fixture manifest.</p>
  </article>;
}
export default function DiagnosticExperience({ theme, onToggle }) {
  useRevealAll();
  const [state, setState] = useState({ status: "idle" });
  const [query, setQuery] = useState(""), [match, setMatch] = useState(""), [selected, setSelected] = useState("");
  const generation = useRef(0), input = useRef(null);
  async function importFile(event) {
    const file = event.target.files?.[0], ticket = ++generation.current;
    setState({ status: "loading" }); setQuery(""); setMatch(""); setSelected("");
    try { const model = await readDiagnosticFile(file); if (ticket === generation.current) setState({ status: "ready", model }); }
    catch (error) { if (ticket === generation.current) setState({ status: "error", error }); }
  }
  const rows = state.model ? browseDiagnosticProfiles(state.model, query, match) : [];
  const player = selectDiagnosticProfile(rows, selected);
  return <><Nav theme={theme} onToggle={onToggle} sections={SECTIONS} />
    <main className="raw-experience diagnostic-experience"><section id="home" className="section raw-home"><div className="wrap">
      <SectionHead eyebrow="Local diagnostic preview" title="Real-player observations" intro="Import a D2C provisional profile file to explore observed match windows." />
      <p className="warn mono angular-sm diagnostic-notice" role="note">{DIAGNOSTIC_NOTICE}</p>
      <p>Explicit local import only. Validation and display happen in this browser; the file is not uploaded or persisted. No production verification is implied.</p>
      <label className="diagnostic-import">Choose diagnostic JSON<input ref={input} type="file" accept=".json,application/json" onChange={importFile} /></label>
      <button type="button" className="raw-retry angular-sm" onClick={() => { generation.current++; setState({ status: "idle" }); setSelected(""); if (input.current) input.current.value = ""; }}>Clear imported data</button>
      {state.status === "idle" && <p role="status">No diagnostic data imported. No demo players are substituted.</p>}
      {state.status === "loading" && <p role="status">Validating local file…</p>}
      {state.status === "error" && <p role="alert" className="warn">{state.error.message}</p>}
    </div></section><section id="search" className="section"><div className="wrap">
      <h2 className="display">Player profiles</h2>{state.model && <>
        <p>{state.model.profiles.length} player contexts · {state.model.scope.observed_match_count} matches · {state.model.scope.observed_event_count} observed events</p>
        <div className="diagnostic-controls"><label>Search players, IDs or teams<input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Player name or context" /></label>
          <label>Match window<select value={match} onChange={(e) => { setMatch(e.target.value); setSelected(""); }}><option value="">Pooled observed window</option>{state.model.scope.match_ids.map((id) => <option key={id} value={id}>Match {id}</option>)}</select></label></div>
        <p role="status">{rows.length} matching player contexts</p><div className="diagnostic-layout">
          <div className="diagnostic-list" aria-label="Player selection">{rows.map((p) => <button type="button" aria-pressed={player?.context_key === p.context_key} key={p.context_key} onClick={() => setSelected(p.context_key)}><b>{profileName(p)}</b><span>{profileContext(p)}</span></button>)}{!rows.length && <p>No matching players.</p>}</div>
          <div>{player ? <Profile player={player} match={match} /> : <p>Select a player to inspect observations.</p>}</div>
        </div></>}
    </div></section></main><footer className="footer"><div className="wrap mono">Provisional observations · source coverage unverified</div></footer></>;
}
