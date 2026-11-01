import { minutes, validateProvisionalCard } from "../lib/provisionalDelivery.js";

const labels = { tackles: "Successful tackles", interceptions: "Successful interceptions", recoveries: "Ball recoveries", press_resistance: "Press resistance", line_breaking_passes: "Line breaking" };
const format = (n) => n.toLocaleString(undefined, { maximumFractionDigits: 2 });

export default function ProvisionalPlayerCard({ player, onClose }) {
  const { provisional, source_provenance, ...p } = player;
  validateProvisionalCard(p, new Set((source_provenance || []).map((s) => s.id)));
  return <article className="diagnostic-profile provisional-card" aria-label={`${p.name} player card`}>
    <button type="button" onClick={onClose} aria-label="Close player card">Close</button>
    <h2 className="display">{p.name}</h2>
    <p>{p.contexts.map((c) => c.team).join(" · ")} · {p.season_name}</p>
    <p className="warn mono" role="note"><strong>LIMITED DATA</strong> · <strong>PARTIAL SEASON</strong></p>
    <p>Observed measurements. Ratings, percentiles and overall score: N/A.</p>
    <p>Scoring group: <b>{p.comparison_group ?? "N/A: no supported MID/CB assignment"}</b>.
      {p.comparison_group === null && " MID/CB ratings are withheld."}</p>
    <p>Supported positions: {Object.entries(p.position_minutes).map(([g, v]) => `${g} (${format(minutes(v))} minutes)`).join("; ") || "N/A"}.</p>
    <details><summary>All supported position labels</summary><p>{p.observed_positions.join("; ") || "N/A"}</p></details>
    <p>{format(minutes(p.supported_minutes))} supported minutes · {p.contexts.reduce((s, c) => s + c.match_ids.length, 0)} observed matches.</p>
    {p.contexts.some((c) => c.competition_name !== "1. Bundesliga") && <p>Bundesliga portion: {format(minutes(p.bundesliga_sample.supported_minutes))} supported minutes · {p.bundesliga_sample.match_ids.length} observed matches · {p.bundesliga_sample.press_successes ?? "N/A"}/{p.bundesliga_sample.press_attempts ?? "N/A"} pressured actions. Measurements below combine compatible supported season evidence.</p>}
    <p>{p.observed_exposure_complete ? "Exposure supported across all observed matches. Season coverage remains partial." : "Verified subsets only. Additional exposure is excluded; its duration is unknown."}</p>
    {!!p.excluded_match_ids.length && <p className="warn" role="note">Excluded appearances: {p.excluded_match_ids.join(", ")}. Defensive counts and minutes omit these appearances. Press ratios retain verified actions and do not require a minute denominator.</p>}
    <div className="diagnostic-metrics">{Object.entries(p.attributes).map(([key, a]) => {
      const o = a.observation;
      return <section key={key} aria-label={labels[key]}>
        <h3>{labels[key]}</h3><p>Rating: <b>N/A</b></p>
        <p>Observed: <strong>{o === null ? "N/A" : `${format(o.value)}${o.unit === "percent" ? "%" : " per90"}`}</strong></p>
        {o && (o.unit === "percent" ? <>
          <p>{o.successes} successful / {o.attempts} pressured actions · {o.match_ids.length} observed matches</p>
          <p>Passes: {o.pass_successes}/{o.pass_attempts}; dribbles: {o.dribble_successes}/{o.dribble_attempts}</p>
          <p className={o.at_least_40 ? "" : "warn"}>{o.at_least_40 ? "At least 40 actions observed" : "LIMITED DATA: fewer than 40 actions; measured value retained"}</p>
        </> : <p>{o.count} events / {format(minutes(o.minutes))} supported minutes · {o.match_ids.length} matched matches</p>)}
        <p>{a.reason}</p>
        {o && <details><summary>Measurement fixture scope</summary><p>{o.match_ids.join(", ")}</p></details>}
      </section>;
    })}</div>
    <p className="warn" role="note">Unobserved Bundesliga exposure is unknown. These samples do not establish full-season performance.</p>
    <details><summary>Clubs, sources and verification provenance</summary>
      {p.contexts.map((c) => <p key={`${c.team}:${c.competition_name}`}>{c.team} · {c.competition_name} · matches {c.match_ids.join(", ")}</p>)}
      <p>StatsBomb original-source observations; independent calculation checks. Source signoff and rating publication remain withheld.</p>
      {source_provenance.map((s) => <p key={s.id}>{s.label}<br /><code>{s.path}</code><br />SHA256: <code>{s.sha256}</code></p>)}
    </details>
  </article>;
}
