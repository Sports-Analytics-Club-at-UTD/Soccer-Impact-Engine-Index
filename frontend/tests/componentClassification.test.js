import test from 'node:test';
import assert from 'node:assert/strict';
import { componentTier, classify, METRICS } from '../src/lib/archetypes.js';
import { experimentalComponentClassification } from '../src/dev/componentClassification.js';

const eligiblePlayer = () => ({
  presentation: { comparison_position: 'MID', limited_data: false, attributes: Object.fromEntries(METRICS.map(({ id }, i) =>
    [id, { rating: 60 + i, percentile: [90, 75, 74.99999999999999, 89.99999999999999, 100][i] }])) },
  ovr: { eligible: true, value: 65 },
});

test('five independent tiers use precise percentiles; changing OVR and ratings cannot promote a component', () => {
  const p = eligiblePlayer(), before = structuredClone(p);
  assert.deepEqual(experimentalComponentClassification(p).tiers, {
    tackles: 'Gold', interceptions: 'Silver', recoveries: 'Standard', press_resistance: 'Silver', line_breaking_passes: 'Gold',
  });
  assert.deepEqual(p, before);
  const expected = experimentalComponentClassification(p);
  p.ovr.value = 99;
  for (const a of Object.values(p.presentation.attributes)) a.rating = 99;
  assert.deepEqual(experimentalComponentClassification(p), expected);
});

test('absent eligibility, Limited Data and incomplete input withhold all badges', () => {
  for (const mutate of [
    (p) => { p.ovr.eligible = false; }, (p) => { delete p.ovr; },
    (p) => { p.presentation.limited_data = true; },
    (p) => { p.presentation.attributes.press_resistance.limited_data = true; },
    (p) => { p.presentation.attributes.recoveries.rating = null; },
    (p) => { delete p.presentation.attributes.tackles; },
  ]) {
    const p = eligiblePlayer(); mutate(p);
    const c = experimentalComponentClassification(p);
    assert.equal(c.status, 'withheld');
    assert.deepEqual(Object.values(c.tiers), [null, null, null, null, null]);
  }
});

test('invalid or absent percentile stays unavailable without erasing other component tiers', () => {
  for (const value of [null, undefined, NaN, Infinity, -1, 101, '99', true]) {
    const p = eligiblePlayer(); p.presentation.attributes.tackles.percentile = value;
    const c = experimentalComponentClassification(p);
    assert.equal(c.tiers.tackles, null);
    assert.equal(c.tiers.interceptions, 'Silver');
  }
});

test('component tiers retain exact Gold/Silver boundaries and unavailable values', () => {
  for (const [value, tier] of [[0, 'Standard'], [74.99999999999999, 'Standard'],
    [75, 'Silver'], [89.99999999999999, 'Silver'], [90, 'Gold'], [100, 'Gold']]) {
    assert.equal(componentTier(value), tier);
  }
  for (const value of [undefined, null, NaN, Infinity, -1, 101, '90', true]) {
    assert.equal(componentTier(value), null);
  }
});

test('existing positional priorities stay deterministic; CM and MID gain no DM taxonomy', () => {
  for (const position of ['CB', 'DM']) {
    const attributes = Object.fromEntries(METRICS.map(({ id }) => [id, { rating: 1, percentile: 90 }]));
    const player = { position, attributes, ovr: { value: 99 } };
    assert.equal(classify(player).name, position === 'CB' ? 'Stopper' : 'Destroyer');
    delete attributes.tackles;
    assert.equal(classify(player).name, position === 'CB' ? 'Sweeper' : 'Anchor');
    assert.deepEqual(classify(player), classify({ ...player, ovr: { value: 1 } }));
    for (const unsupported of ['CM', 'MID', null]) {
      assert.equal(classify({ ...player, position: unsupported }).metric, null);
    }
  }
});

test('component classification consumes percentiles and never rating or Formula B', () => {
  const player = { position: 'CB', ovr: { value: 99 }, attributes: { tackles: { rating: 99, percentile: 74.99999999999999 } } };
  assert.equal(classify(player).tier, null);
  player.attributes.tackles = { rating: 1, percentile: 90 };
  assert.equal(classify(player).tier, '+');
  player.attributes.tackles = { rating: 99, percentile: null };
  assert.equal(classify(player).value, null);
});
