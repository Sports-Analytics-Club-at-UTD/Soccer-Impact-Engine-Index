import { FIVE_METRICS } from './fiveAttributePresentation.js';
import { formulaB, OVR_VERSION, ELIGIBILITY_VERSION } from './provisionalOvr.js';
import { experimentalComponentClassification } from './componentClassification.js';
import { PUBLIC_RATINGS_RELEASE } from './publicRatingsRelease.js';

const check = (v, message) => { if (!v) throw Error(`Invalid public ratings: ${message}`); };
const keys = (v, names) => check(v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === names.length && names.every((k) => Object.hasOwn(v, k)), 'unexpected fields');
const strings = (v) => Array.isArray(v) && v.every((s) => typeof s === 'string' && s.length);
const number = (v, min = 0, max = Infinity) => typeof v === 'number' && Number.isFinite(v) && v >= min && v <= max;
export function validatePublicPlayer(p) {
  keys(p, ['id','player_id','name','season_name','comparison_position','positions','primary_position','secondary_positions','limited_data','partial_season','clubs','coverage','attributes','ovr','badge_eligible']);
  check(/^[1-9]\d*$/.test(p.player_id) && p.id === `${p.player_id}:2015/2016` && p.season_name === '2015/2016' && typeof p.name === 'string' && p.name.length, 'identity');
  check(['MID', 'CB'].includes(p.comparison_position) && ['DM','CM','CB'].includes(p.primary_position) && strings(p.positions) && strings(p.secondary_positions), 'position');
  check(typeof p.limited_data === 'boolean' && p.partial_season === true && typeof p.badge_eligible === 'boolean', 'coverage flags');
  check(Array.isArray(p.clubs) && p.clubs.length, 'clubs');
  for (const c of p.clubs) { keys(c, ['name','competition_name']); check(typeof c.name === 'string' && c.name.length && ['Premier League','La Liga','Serie A','Ligue 1','1. Bundesliga'].includes(c.competition_name), 'club'); }
  keys(p.coverage, ['supported_minutes','observed_fixtures']);
  check(number(p.coverage.supported_minutes) && Number.isSafeInteger(p.coverage.observed_fixtures) && p.coverage.observed_fixtures > 0, 'coverage');
  keys(p.attributes, FIVE_METRICS.map((m) => m.id));
  for (const a of Object.values(p.attributes)) {
    keys(a, ['rating','percentile','limited_data','missingness','warnings']);
    check((a.rating === null ? a.percentile === null && a.missingness.length > 0 : number(a.rating,1,99) && number(a.percentile,0,100)) && typeof a.limited_data === 'boolean' && strings(a.missingness) && strings(a.warnings), 'attribute');
  }
  const o = p.ovr, calculated = formulaB(FIVE_METRICS.map(({ id }) => p.attributes[id].rating));
  keys(o, ['value','status','eligible','exclusion_reasons','comparison_position']);
  check(o.comparison_position === p.comparison_position && typeof o.eligible === 'boolean' && strings(o.exclusion_reasons), 'eligibility');
  check(calculated === null ? o.value === null && o.status === 'unavailable' : number(o.value,1,99) && Math.abs(o.value-calculated) < 1e-12 && o.status === 'calculated', 'Formula B');
  check(o.eligible === (calculated !== null && o.exclusion_reasons.length === 0), 'ranking decision');
  const classification = experimentalComponentClassification({ presentation: p, ovr: o });
  check(p.badge_eligible === (classification.status === 'eligible'), 'badge decision');
  if (o.eligible) check(!p.limited_data && p.coverage.supported_minutes >= 900 && !p.clubs.some((c) => c.competition_name === '1. Bundesliga'), 'strict eligibility');
}

export function parsePublicRatings(text) {
  const d = JSON.parse(text);
  keys(d, ['schema_version','release','season','formula_version','eligibility_version','reference_version','disclosures','counts','players']);
  check(d.schema_version === 'soccer-public-ratings/v1' && d.release === '2015-16-v1' && d.season === '2015/2016' && d.formula_version === OVR_VERSION && d.eligibility_version === ELIGIBILITY_VERSION && d.reference_version === 'frozen-mid-cb-2015-16/v1' && strings(d.disclosures) && d.disclosures.length === 5, 'release');
  keys(d.counts, ['examined','available','complete','partial','bundesliga_complete','bundesliga_partial']);
  check(Array.isArray(d.players) && d.players.length === 691 && new Set(d.players.map((p) => p.id)).size === 691, 'player population');
  d.players.forEach(validatePublicPlayer);
  const complete = d.players.filter((p) => p.ovr.value !== null).length;
  check(complete === 686 && d.counts.complete === complete && d.counts.available === 691 && d.counts.partial === 5 && d.counts.examined === 2514 && d.counts.bundesliga_complete === 133 && d.counts.bundesliga_partial === 5, 'counts');
  for (const [group, count] of [['MID',124],['CB',107]]) check(d.players.filter((p) => p.ovr.eligible && p.comparison_position === group).length === count, 'ranked population');
  return d;
}

export const publicModels = (d) => d.players.map((p) => ({
  id: p.id, name: p.name, presentation: p,
  reference: { fingerprint: d.reference_version },
  ovr: { ...p.ovr, version: d.formula_version, eligibility_version: d.eligibility_version },
  componentClassification: experimentalComponentClassification({ presentation: p, ovr: p.ovr }),
}));

export async function loadPublicRatings({ fetcher = fetch, signal } = {}) {
  const response = await fetcher(`${import.meta.env?.BASE_URL ?? '/'}${PUBLIC_RATINGS_RELEASE.path}`, { credentials: 'same-origin', signal });
  check(response.ok && response.headers.get('content-type')?.includes('application/json'), 'release unavailable; no demo fallback was loaded');
  const bytes = await response.arrayBuffer();
  const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map((b) => b.toString(16).padStart(2,'0')).join('');
  check(bytes.byteLength === PUBLIC_RATINGS_RELEASE.bytes && hash === PUBLIC_RATINGS_RELEASE.sha256, 'release fingerprint');
  return parsePublicRatings(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
}
