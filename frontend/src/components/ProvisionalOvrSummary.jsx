// Rendering only; calculation, eligibility and source binding live in the adapter.
import { playerDataStatus } from '../lib/playerDataStatus.js';

export default function ProvisionalOvrSummary({ ovr, presentation }) {
  if (!ovr) return null;
  return <section className="five-ovr" aria-label="Provisional overall rating">
    <p className="mono">OVR · FORMULA B · PROVISIONAL</p>
    <strong className="display">{ovr.value === null ? 'N/A' : ovr.value.toFixed(2)}</strong>
    <p>{playerDataStatus({ presentation, ovr }).label}</p>
    {ovr.value === null && <p>All five valid attributes are required for OVR.</p>}
    <details><summary>Overall methodology and eligibility</summary>
      <p>Overall rating is calculated by ranking the five measured attributes from highest to lowest and weighting them 30%, 25%, 20%, 15%, and 10%.</p>
      <p>This provisional experimental Soccer Impact Index rating recognizes measured strengths. It has not been independently validated as player quality and is not an official EA Sports FC/FIFA rating.</p>
      <p>Ranked players must satisfy all five existing strict reference criteria: at least 900 verified aligned minutes, at least 40 supported pressured actions, complete supported observed exposure and metric scopes, existing position-specific reference membership, four-league-only observations and no pending fixture 3879594. These rules do not guarantee statistical confidence or full-season coverage.</p>
      <p>The Limited Data filter includes coverage warnings and profiles excluded from the strict leaderboard. Coverage flags and ranking exclusion are distinct; Coverage &amp; sources retains the specific reasons.</p>
      <p>Formula: {ovr.version} · Eligibility: {ovr.eligibility_version}</p>
    </details>
  </section>;
}
