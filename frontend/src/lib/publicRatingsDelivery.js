import { FIVE_METRICS } from './fiveAttributePresentation.js';
import { formulaB, OVR_VERSION, ELIGIBILITY_VERSION } from './provisionalOvr.js';
import { experimentalComponentClassification } from './componentClassification.js';
import { PUBLIC_RATINGS_RELEASE } from './publicRatingsRelease.js';

const check = (v, message) => { if (!v) throw Error(`Invalid public ratings: ${message}`); };
const keys = (v, names) => check(v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === names.length && names.every((k) => Object.hasOwn(v, k)), 'unexpected fields');
const strings = (v) => Array.isArray(v) && v.every((s) => typeof s === 'string' && s.length);
const number = (v, min = 0, max = Infinity) => typeof v === 'number' && Number.isFinite(v) && v >= min && v <= max;
export function validatePublicPlayer(p, supportedSample = false, partialSamples = false) {
  keys(p, ['id','player_id','name','season_name','comparison_position','positions','primary_position','secondary_positions','limited_data','partial_season','clubs','coverage','attributes','ovr','badge_eligible']);
  check(/^[1-9]\d*$/.test(p.player_id) && p.id === `${p.player_id}:2015/2016` && p.season_name === '2015/2016' && typeof p.name === 'string' && p.name.length, 'identity');
  check(['MID', 'CB'].includes(p.comparison_position) && ['DM','CM','CB'].includes(p.primary_position) && strings(p.positions) && strings(p.secondary_positions), 'position');
  check(typeof p.limited_data === 'boolean' && p.partial_season === true && typeof p.badge_eligible === 'boolean', 'coverage flags');
  check(Array.isArray(p.clubs) && p.clubs.length, 'clubs');
  for (const c of p.clubs) { keys(c, ['name','competition_name']); check(typeof c.name === 'string' && c.name.length && ['Premier League','La Liga','Serie A','Ligue 1','1. Bundesliga'].includes(c.competition_name), 'club'); }
  keys(p.coverage, partialSamples ? ['supported_minutes','observed_fixtures','supported_fixtures','unresolved_fixtures','partial_fixtures'] : supportedSample ? ['supported_minutes','observed_fixtures','supported_fixtures','unresolved_fixtures'] : ['supported_minutes','observed_fixtures']);
  check(number(p.coverage.supported_minutes) && Number.isSafeInteger(p.coverage.observed_fixtures) && p.coverage.observed_fixtures > 0, 'coverage');
  if (supportedSample) check(Number.isSafeInteger(p.coverage.supported_fixtures) && p.coverage.supported_fixtures >= 0 &&
    Number.isSafeInteger(p.coverage.unresolved_fixtures) && p.coverage.unresolved_fixtures >= 0 &&
    p.coverage.supported_fixtures + p.coverage.unresolved_fixtures === p.coverage.observed_fixtures, 'supported coverage');
  if (partialSamples) check(Number.isSafeInteger(p.coverage.partial_fixtures) && p.coverage.partial_fixtures >= 0 && p.coverage.partial_fixtures <= p.coverage.supported_fixtures, 'partial coverage');
  keys(p.attributes, FIVE_METRICS.map((m) => m.id));
  for (const [id, a] of Object.entries(p.attributes)) {
    keys(a, supportedSample ? ['rating','percentile','limited_data','missingness','warnings','coverage'] : ['rating','percentile','limited_data','missingness','warnings']);
    check((a.rating === null ? a.percentile === null && a.missingness.length > 0 : number(a.rating,1,99) && number(a.percentile,0,100)) && typeof a.limited_data === 'boolean' && strings(a.missingness) && strings(a.warnings), 'attribute');
    if (supportedSample) {
      keys(a.coverage, partialSamples ? ['supported_fixtures','excluded_fixtures','supported_minutes','pressure_attempts','partial_fixtures'] : ['supported_fixtures','excluded_fixtures','supported_minutes','pressure_attempts']);
      const c = a.coverage;
      check(Number.isSafeInteger(c.supported_fixtures) && c.supported_fixtures >= 0 && Number.isSafeInteger(c.excluded_fixtures) && c.excluded_fixtures >= 0 &&
        c.supported_fixtures + c.excluded_fixtures === p.coverage.observed_fixtures && number(c.supported_minutes) &&
        c.supported_minutes <= p.coverage.supported_minutes + 1e-9 &&
        (id === 'press_resistance' ? Number.isSafeInteger(c.pressure_attempts) && c.pressure_attempts >= 0 : c.pressure_attempts === null), 'metric coverage');
      if (partialSamples) check(Number.isSafeInteger(c.partial_fixtures) && c.partial_fixtures >= 0 && c.partial_fixtures <= c.supported_fixtures && (id !== 'press_resistance' || c.partial_fixtures === 0), 'partial metric coverage');
    }
  }
  const o = p.ovr, calculated = formulaB(FIVE_METRICS.map(({ id }) => p.attributes[id].rating));
  keys(o, ['value','status','eligible','exclusion_reasons','comparison_position']);
  check(o.comparison_position === p.comparison_position && typeof o.eligible === 'boolean' && strings(o.exclusion_reasons), 'eligibility');
  check(calculated === null ? o.value === null && o.status === 'unavailable' : number(o.value,1,99) && Math.abs(o.value-calculated) < 1e-12 && o.status === 'calculated', 'Formula B');
  check(o.eligible === (calculated !== null && o.exclusion_reasons.length === 0), 'ranking decision');
  if (supportedSample) {
    const expected = [];
    const comps = [...new Set(p.clubs.map((c) => c.competition_name))];
    if (comps.includes('1. Bundesliga')) expected.push('BUNDESLIGA_CONTRIBUTION');
    if (p.coverage.supported_minutes < 900) expected.push('BELOW_900_VERIFIED_SEASON_MINUTES');
    for (const { id } of FIVE_METRICS) {
      const a = p.attributes[id], key = id === 'line_breaking_passes' ? 'progressive_passing' : id;
      if (a.rating === null) expected.push(`${key}:MISSING_MEASUREMENT_DENOMINATOR`);
      if (id !== 'press_resistance' && a.coverage.supported_minutes < 900) expected.push(`${key}:BELOW_900_SUPPORTED_METRIC_MINUTES`);
      if (id === 'press_resistance' && a.coverage.pressure_attempts < 40) expected.push(`${key}:BELOW_40_SUPPORTED_ATTEMPTS`);
    }
    check(JSON.stringify(o.exclusion_reasons) === JSON.stringify(expected), 'supported-sample policy');
  }
  const classification = experimentalComponentClassification({ presentation: p, ovr: o });
  check(p.badge_eligible === (classification.status === 'eligible'), 'badge decision');
  if (o.eligible) check(!p.limited_data && p.coverage.supported_minutes >= 900 && !p.clubs.some((c) => c.competition_name === '1. Bundesliga'), 'strict eligibility');
}

export function parsePublicRatings(text) {
  const d = JSON.parse(text);
  keys(d, ['schema_version','release','season','formula_version','eligibility_version','reference_version','disclosures','counts','players']);
  const partialSamples = d.schema_version === 'soccer-public-ratings/v3';
  const supportedSample = partialSamples || d.schema_version === 'soccer-public-ratings/v2';
  const version = partialSamples ? 'v3' : 'v2';
  check((supportedSample ? d.release === `2015-16-${version}` && d.eligibility_version === 'supported-sample-five-attributes/v1' && d.reference_version === `supported-mid-cb-2015-16/${version}`
    : d.schema_version === 'soccer-public-ratings/v1' && d.release === '2015-16-v1' && d.eligibility_version === ELIGIBILITY_VERSION && d.reference_version === 'frozen-mid-cb-2015-16/v1') &&
    d.season === '2015/2016' && d.formula_version === OVR_VERSION && strings(d.disclosures) && d.disclosures.length === 5, 'release');
  keys(d.counts, ['examined','available','complete','partial','bundesliga_complete','bundesliga_partial']);
  check(Array.isArray(d.players) && d.players.length === 691 && new Set(d.players.map((p) => p.id)).size === 691, 'player population');
  d.players.forEach((p) => validatePublicPlayer(p, supportedSample, partialSamples));
  const complete = d.players.filter((p) => p.ovr.value !== null).length;
  if (supportedSample) {
    check(d.counts.complete === complete && d.counts.available === 691 && d.counts.partial === 691 - complete && d.counts.examined === 691 &&
      d.counts.bundesliga_complete === d.players.filter((p) => p.limited_data && p.ovr.value !== null).length &&
      d.counts.bundesliga_partial === d.players.filter((p) => p.limited_data && p.ovr.value === null).length, 'counts');
  } else {
    check(complete === 686 && d.counts.complete === complete && d.counts.available === 691 && d.counts.partial === 5 && d.counts.examined === 2514 && d.counts.bundesliga_complete === 133 && d.counts.bundesliga_partial === 5, 'counts');
    for (const [group, count] of [['MID',124],['CB',107]]) check(d.players.filter((p) => p.ovr.eligible && p.comparison_position === group).length === count, 'ranked population');
  }
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
