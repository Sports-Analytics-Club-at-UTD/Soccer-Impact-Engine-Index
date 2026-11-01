import { FIVE_METRICS, validateFiveAttributeCard } from "../lib/fiveAttributePresentation.js";
import Radar from "./Radar.jsx";
import { playerDataStatus } from '../lib/playerDataStatus.js';
import AttributeBadge from './AttributeBadge.jsx';

export default function FiveAttributeComparison({ players }) {
  if (players.length !== 2 || players[0].id === players[1].id) return <p>Choose two different player-seasons to compare.</p>;
  for (const p of players) validateFiveAttributeCard(p.presentation, p.reference);
  return <FiveAttributeComparisonView players={players} />;
}

export function FiveAttributeComparisonView({ players, label = "Synthetic five-attribute comparison", heading = "Compare synthetic player-seasons", showRadars = false, showDifferences = false, notice = null, compactCoverage = false }) {
  if (players.length !== 2 || players[0].id === players[1].id) return <p>Choose two different player-seasons to compare.</p>;
  const compatible = players[0].presentation.comparison_position === players[1].presentation.comparison_position && players[0].reference.fingerprint === players[1].reference.fingerprint;
  return <section className="five-comparison" aria-label={label}>
    <h2 className="display">{heading}</h2>
    {players.some((p) => p.componentClassification) && <details><summary>Attribute badge methodology</summary><p>{players.find((p) => p.componentClassification).componentClassification.explanation}</p></details>}
    {!compactCoverage && notice && <p className="warn mono" role="note">{notice}</p>}
    {!compatible && <p role="note">Different comparison positions: MID and CB percentiles use separate reference populations. Score differences are N/A.</p>}
    {showRadars && <div className="five-comparison-radars">{players.map((p) => <div key={p.id}>
      <h3>{p.name} · {p.presentation.comparison_position}</h3>
      <Radar attributes={FIVE_METRICS.map((m) => ({ ...m, label: m.label.replaceAll("\u2014", ":"), value: p.presentation.attributes[m.id].rating }))} label={`${p.name} five-axis experimental ratings`} />
    </div>)}</div>}
    <div className="five-table-scroll"><table><caption>Ratings and position-specific percentiles; each player uses their own comparison position.</caption>
      <thead><tr><th scope="col">Attribute</th>{players.map((p) => <th scope="col" key={p.id}>{p.name}<br />{p.presentation.comparison_position ?? "N/A"}{!compactCoverage && p.presentation.limited_data && <><br />LIMITED DATA</>}{!compactCoverage && p.presentation.partial_season && <><br />PARTIAL SEASON</>}</th>)}{showDifferences && <th scope="col">Difference (first − second)</th>}</tr></thead>
      <tbody>{players.every((p) => p.ovr) && <tr><th scope="row">OVR · Formula B (provisional)</th>{players.map((p) => <td key={p.id}>{p.ovr.value === null ? 'N/A' : p.ovr.value.toFixed(2)}<br />{playerDataStatus(p).label}</td>)}{showDifferences && <td>{compatible && players.every((p) => p.ovr.value !== null) ? (players[0].ovr.value - players[1].ovr.value).toFixed(2) : 'N/A'}</td>}</tr>}{FIVE_METRICS.map((m) => <tr key={m.id}><th scope="row">{m.label.replaceAll("\u2014", ":")}</th>{players.map((p) => {
        const a = p.presentation.attributes[m.id];
        return <td key={p.id}><span className="attribute-rating">{a.rating === null ? "N/A" : a.rating.toFixed(2)}<AttributeBadge tier={p.componentClassification?.tiers[m.id]} label={m.label.replaceAll("\u2014", ":")} /></span><br />Percentile: {a.percentile === null ? "N/A" : a.percentile.toFixed(2)}</td>;
      })}{showDifferences && <td>{compatible && players.every((p) => p.presentation.attributes[m.id].rating !== null) ? (players[0].presentation.attributes[m.id].rating - players[1].presentation.attributes[m.id].rating).toFixed(2) : "N/A"}</td>}</tr>)}</tbody>
    </table></div>
  </section>;
}
