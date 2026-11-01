import { FIVE_METRICS } from '../lib/fiveAttributePresentation.js';

export const OVR_VERSION = 'soccer-ovr-formula-b/v1';
export const ELIGIBILITY_VERSION = 'existing-strict-five-attribute-reference/v1';
export const OVR_EXPLANATION = 'Overall rating is calculated by ranking the five measured attributes from highest to lowest and weighting them 30%, 25%, 20%, 15%, and 10%.';

export function formulaB(values) {
  if (!Array.isArray(values) || values.length !== 5 || [...values].some((v) => typeof v !== 'number' || !Number.isFinite(v) || v < 1 || v > 99)) return null;
  return [...values].sort((a, b) => b - a).reduce((sum, v, i) => sum + v * [6, 5, 4, 3, 2][i], 0) / 20;
}

export function validateOvrIntegration(integration, data) {
  const check = (v) => { if (!v) throw Error('Invalid provisional Formula B integration'); };
  check(integration && integration.version === OVR_VERSION && integration.eligibility_version === ELIGIBILITY_VERSION);
  check(integration.reference_fingerprint === data.reference.fingerprint && integration.source_package && Object.keys(integration.source_package).length === Object.keys(data.source_package).length && Object.entries(data.source_package).every(([key, value]) => integration.source_package[key] === value));
  check(integration.players && Object.keys(integration.players).length === data.players.length);
  for (const p of data.players) {
    const ovr = integration.players[p.id];
    const value = formulaB(FIVE_METRICS.map((m) => p.attributes[m.id].rating));
    check(ovr && ovr.comparison_position === p.comparison_position && typeof ovr.eligible === 'boolean' && Array.isArray(ovr.exclusion_reasons) && ovr.exclusion_reasons.every((r) => typeof r === 'string' && r.length));
    check(value === null ? ovr.value === null && ovr.status === 'unavailable' : typeof ovr.value === 'number' && Number.isFinite(ovr.value) && Math.abs(ovr.value - value) < 1e-12 && ovr.status === 'calculated');
    check(ovr.eligible === (value !== null && ovr.exclusion_reasons.length === 0));
    // Defense in depth; authoritative membership and complete exposure come from
    // the hash-validated backend's existing strict-reference predicate.
    if (ovr.eligible) check(!p.limited_data && p.known_supported_minutes.numerator / p.known_supported_minutes.denominator >= 900 && p.attributes.press_resistance.observation?.action_sample_size >= 40 && Object.values(p.attributes).every((m) => !m.limited_data && !m.exclusions.length && m.normalization.comparison_position === p.comparison_position));
  }
}

export const formatOvr = (ovr) => ovr?.value == null ? 'N/A' : ovr.value.toFixed(2);
export function ovrLeaderboard(players, position) {
  if (!['MID', 'CB'].includes(position)) throw Error('Select MID or CB for the OVR leaderboard');
  return players.filter((p) => p.ovr?.eligible === true && p.ovr.status === 'calculated' && p.ovr.comparison_position === position && p.presentation.comparison_position === position && typeof p.ovr.value === 'number' && Number.isFinite(p.ovr.value) && p.ovr.value >= 1 && p.ovr.value <= 99)
    .sort((a, b) => b.ovr.value - a.ovr.value || (BigInt(a.presentation.player_id) < BigInt(b.presentation.player_id) ? -1 : BigInt(a.presentation.player_id) > BigInt(b.presentation.player_id) ? 1 : 0));
}
