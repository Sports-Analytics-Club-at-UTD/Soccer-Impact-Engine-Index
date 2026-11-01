import Radar from "./Radar.jsx";
import ProvisionalOvrSummary from "./ProvisionalOvrSummary.jsx";
import AttributeBadge from "./AttributeBadge.jsx";
import { FIVE_METRICS, presentationMinutes, validateFiveAttributeCard } from "../lib/fiveAttributePresentation.js";

const format = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 2 });
export default function FiveAttributePlayerCard({ player, onClose }) {
  const { presentation: p, reference } = player;
  validateFiveAttributeCard(p, reference);
  return <FiveAttributeCardView presentation={p} reference={reference} onClose={onClose} />;
}

// Shared rendering only. Each caller keeps its own data-validation boundary.
export function FiveAttributeCardView({ presentation: p, reference, onClose, ovr, componentClassification, compactCoverage = false, notice = "SYNTHETIC TEST FIXTURE", radarLabel = "Synthetic five-axis FIFA-style ratings" }) {
  const axes = FIVE_METRICS.map((m) => ({ ...m, value: p.attributes[m.id].rating }));
  return <article className="five-card card-surface" aria-label={`${p.name} five-attribute player card`}>
    <header className="five-card-header">
      <div>{!compactCoverage && notice && <p className="mono">{notice}</p>}<h2 className="display">{p.name}</h2>
        <p>{p.clubs.map((c) => c.name).join(" · ")} · {p.season_name}</p>
        <p>Positions: {p.positions.join("; ") || "N/A"} · Comparison: {p.comparison_position ?? "N/A"}</p>
        {p.primary_position && <p>Primary position group: {p.primary_position} · Secondary positions: {p.secondary_positions?.join("; ") || "None observed"}</p>}
        {p.known_supported_minutes && <p>{format(presentationMinutes(p.known_supported_minutes))} known supported minutes · {p.clubs.reduce((n, c) => n + c.match_ids.length, 0)} observed fixtures</p>}
        <p className="mono five-identity">Player-season: {p.id}</p></div>
      <button type="button" onClick={onClose} aria-label="Close player card">Close</button>
    </header>
    {p.coverage && <p>{format(p.coverage.supported_minutes)} known supported minutes · {p.coverage.observed_fixtures} observed fixtures · Partial season</p>}
    {!compactCoverage && (p.limited_data || p.partial_season) && <p className="warn mono" role="note">
      {p.limited_data && <strong>LIMITED DATA </strong>}{p.partial_season && <strong>PARTIAL SEASON</strong>}
    </p>}
    <ProvisionalOvrSummary ovr={ovr} presentation={p} />
    <div className="five-card-viz"><Radar attributes={axes} label={radarLabel} />
      <div className="five-score-summary">{FIVE_METRICS.map((m) => <div key={m.id}>
        <span>{m.label}</span><span className="attribute-rating"><strong className="display">{p.attributes[m.id].rating === null ? "N/A" : format(p.attributes[m.id].rating)}</strong><AttributeBadge tier={componentClassification?.tiers[m.id]} label={m.label} /></span>
        <span>Percentile: {p.attributes[m.id].percentile === null ? "N/A" : format(p.attributes[m.id].percentile)} · {p.comparison_position ?? "N/A"}</span>
      </div>)}</div>
    </div>
    <p>Progressive passing is a proxy. It does not verify defensive line-breaking events.</p>
    {axes.some((a) => a.value === null) && <p role="note">Incomplete profile: missing attributes stay N/A; the visualization has no filled polygon.</p>}
    {!p.coverage && <div className="five-metric-grid">{FIVE_METRICS.map(({ id, label }) => {
      const m = p.attributes[id], o = m.observation;
      const pool = p.comparison_position ? reference.positions[p.comparison_position][id] : null;
      const warnings = compactCoverage ? m.warnings?.filter((w) => !['LIMITED DATA', 'PARTIAL SEASON', 'BELOW_40_PRESS_ACTIONS / LIMITED DATA'].includes(w)) : m.warnings;
      const evidenceNotes = <>
        {!compactCoverage && (m.limited_data || m.partial_season) && <p className="warn" role="note">{m.limited_data ? "LIMITED DATA" : ""} {m.partial_season ? "PARTIAL SEASON" : ""}</p>}
        {o?.action_sample_size < 40 && o?.action_sample_size !== null && <p className={compactCoverage ? undefined : 'warn'}>Fewer than 40 pressured actions ({o.action_sample_size}); measured sample retained.</p>}
        {!!warnings?.length && <p className={compactCoverage ? undefined : 'warn'}>{warnings.join(" · ")}</p>}
        {m.exclusions.length > 0 && <p className={compactCoverage ? undefined : 'warn'}>Excluded appearances: {m.exclusions.map((e) => `${e.match_id} — ${e.reasons.join("; ")}`).join(" · ")}</p>}
      </>;
      return <section key={id} aria-label={label}>
        <h3>{label}</h3>
        <p>Measured: <strong>{o ? `${format(o.value)}${o.unit === "percent" ? "%" : " per 90"}` : "N/A"}</strong></p>
        {o && <>
          <p>{o.numerator} {o.denominator_unit === "actions" ? "successful pressured actions" : "events"} / {format(o.denominator)} {o.denominator_unit === "actions" ? "pressured attempts" : "supported minutes"}</p>
          {o.denominator_unit === "actions" && <p>Known supported minutes: {o.supported_minutes === null ? "N/A — duration unresolved; the ratio uses attempts" : format(presentationMinutes(o.supported_minutes))}</p>}
        </>}
        {!compactCoverage && evidenceNotes}
        {m.missingness.length > 0 && <p>Unavailable: {m.missingness.join("; ")}</p>}
        {m.sample_details?.measured_pass_sample !== null && m.sample_details?.measured_pass_sample !== undefined && <p>Measured open-play pass sample: {m.sample_details.measured_pass_sample}</p>}
        {id === "press_resistance" && m.sample_details?.raw_counts && <p>Passes: {m.sample_details.raw_counts.pressured_pass_completed}/{m.sample_details.raw_counts.pressured_pass_attempts}; dribbles: {m.sample_details.raw_counts.pressured_dribble_completed}/{m.sample_details.raw_counts.pressured_dribble_attempts}</p>}
        {id === "press_resistance" && o === null && m.sample_details?.action_sample_size === 0 && <p>No pressured attempts observed (sample size 0).</p>}
        <details><summary>Measurement scope and frozen reference</summary>
          {compactCoverage && evidenceNotes}
          <p>Fixtures: {o?.match_ids.join(", ") || "N/A"}</p>
          {o?.exact_value && <p>Exact measured value: {o.exact_value.numerator}/{o.exact_value.denominator} {o.unit}</p>}
          {o?.supported_minutes && o?.exact_value && <p>Exact supported minutes: {o.supported_minutes.numerator}/{o.supported_minutes.denominator}</p>}
          <p>Comparison position: {m.normalization.comparison_position ?? "N/A"}</p>
          <p>Population: {pool?.population_version ?? "N/A"}; n={pool?.n ?? "N/A"}; mean={pool?.mean ?? "N/A"}; sample SD={pool?.sample_sd ?? "N/A"}</p>
          <p>Reference version: {m.normalization.reference_version}</p>
          <p>Reference fingerprint: <code>{m.normalization.reference_fingerprint}</code></p>
          <p>Position/metric pool fingerprint: <code>{m.normalization.pool_fingerprint ?? "N/A"}</code></p>
        </details>
      </section>;
    })}</div>}
    {p.coverage ? <details><summary>Coverage &amp; sources</summary>
      <p>Final 2015/16 project ratings, approved for publication. Available observations do not establish complete seasons. Missing matches are not zero-action performances.</p>
      <p>MID and CB use separate unchanged frozen references; Bundesliga observations do not contribute to the baseline. Bundesliga coverage is uneven.</p>
      <p>Raw observations, private research and reference memberships are not included in the public release.</p>
      <p>{componentClassification?.explanation}</p>
      {!!ovr?.exclusion_reasons.length && <p>Ranking exclusions: {ovr.exclusion_reasons.join("; ")}</p>}
      {FIVE_METRICS.map(({id,label}) => <p key={id}>{label}: {[...p.attributes[id].warnings, ...p.attributes[id].missingness].join(" · ") || "Available"}</p>)}
    </details> : <details><summary>{compactCoverage ? 'Coverage & sources' : 'Clubs and evidence provenance'}</summary>
      {componentClassification && <p>{componentClassification.explanation}</p>}
      {compactCoverage && <>
        <p>{p.partial_season ? 'Partial-season observation. This frozen dataset marks all profiles as partial season, including leaderboard-eligible players; eligibility does not establish full-season coverage.' : 'Available observed fixtures do not establish full-season coverage.'}</p>
        {p.limited_data && <p>Bundesliga coverage is uneven and incomplete. Supported observations are retained; missing matches are not zero-action performances or proof of low season playing time.</p>}
        <p>MID and CB use separate frozen references. Bundesliga observations do not contribute to the reference baseline.</p>
        <p>Source evidence is frozen and loaded unchanged. Real-player data is served only in the local development preview; production delivery remains disabled. This preview grants no publication authority.</p>
        <p>Reference SHA256: <code>{reference.fingerprint}</code></p>
        {ovr && <>
          <p>Source version: {ovr.source_package.version} · Manifest SHA256: <code>{ovr.source_package.manifest_sha256}</code></p>
          {!!ovr.exclusion_reasons.length && <p>Ranking exclusions: {ovr.exclusion_reasons.join('; ')}</p>}
        </>}
      </>}
      {p.clubs.map((c) => <p key={`${c.name}:${c.competition_name}`}>{c.name} · {c.competition_name} · {c.match_ids.join(", ")}</p>)}
      {p.provenance.map((s) => <p key={s.id}>{s.label} · {s.source}<br /><code>{s.fingerprint}</code></p>)}
    </details>}
  </article>;
}
