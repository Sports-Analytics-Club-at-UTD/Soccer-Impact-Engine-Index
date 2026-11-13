import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire, Module } from 'node:module';
import { fileURLToPath } from 'node:url';
import { ARCHETYPES, METRICS, classify, classifyAll, classifyAllDemo, archetypeLeaders } from '../src/lib/archetypes.js';
import { foundationPlayers, publicRatingCard } from '../src/lib/foundationPlayers.js';
import { parsePublicRatings } from '../src/lib/publicRatingsDelivery.js';
import { ratingCard } from '../src/lib/ratingCard.js';

const require = createRequire(import.meta.url), React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
function component(name) {
  const filename = fileURLToPath(new URL(`../src/components/${name}.jsx`, import.meta.url));
  const result = require('esbuild').buildSync({ entryPoints: [filename], bundle: true, write: false,
    platform: 'node', format: 'cjs', jsx: 'automatic', logLevel: 'silent',
    external: ['react', 'react/jsx-runtime'], loader: { '.css': 'empty' },
    define: { 'import.meta.env.DEV': 'false', 'import.meta.env.BASE_URL': '"/"' } });
  const mod = new Module(filename); mod.paths = Module._nodeModulePaths(fileURLToPath(new URL('..', import.meta.url)));
  mod._compile(result.outputFiles[0].text, filename); return mod.exports.default;
}
const PlayerCard = component('PlayerCard'), Search = component('Search');
const fixture = (position, values) => ({ id: 'fixture', name: 'Test player', team: 'Test club', position, minutes: 1500,
  attributes: Object.fromEntries(METRICS.map((metric, i) => [metric.id, { rating: 60, percentile: values[i] }])) });
const data = parsePublicRatings(readFileSync(new URL('../public/data/player-ratings-2015-16-v1.json', import.meta.url), 'utf8'));
const players = foundationPlayers(data);

test('archetype leaders use earned secondary badges, position and eligibility, rather than overall', () => {
  const make = (id, value, extras = {}) => ({ id, position: 'CB', ranked: true, ovr: 100 - value,
    archetypes: [{ metric: 'LB', value: 100, tier: '+' }, { metric: 'T', value, tier: value >= 90 ? '+' : '−' }], ...extras });
  const sample = [make('silver', 80), make('gold', 99), make('tie', 99),
    make('unranked', 100, { ranked: false }), make('midfielder', 100, { position: 'DM' }),
    make('missing', 100, { archetypes: [] })];
  const before = structuredClone(sample);
  assert.deepEqual(archetypeLeaders(sample, 'CB', ARCHETYPES.CB[0]).map((p) => p.id), ['gold', 'tie', 'silver']);
  assert.deepEqual(sample, before);
  assert.deepEqual(archetypeLeaders([], 'CB', ARCHETYPES.CB[0]), []);
});

test('all ten live archetype lists contain the correct top five without altering the release', () => {
  const live = foundationPlayers(parsePublicRatings(readFileSync(new URL('../public/data/player-ratings-2015-16-v3.json', import.meta.url), 'utf8')));
  const before = structuredClone(live);
  for (const position of ['CB', 'DM']) for (const a of ARCHETYPES[position]) {
    const metric = METRICS.find((m) => m.key === a.metric).id;
    const expected = live.filter((p) => p.ranked && p.position === position && p.attributes[metric].percentile >= 75)
      .sort((p, q) => q.attributes[metric].percentile - p.attributes[metric].percentile).slice(0, 5);
    const actual = archetypeLeaders(live, position, a);
    assert.equal(actual.length, 5);
    assert.deepEqual(actual.map((p) => p.id), expected.map((p) => p.id));
  }
  assert.deepEqual(live, before);
});

test('archetype dropdown expands inline, switches lists, collapses and handles loading or errors', async () => {
  const { JSDOM } = await import('jsdom');
  const dom = new JSDOM('<div id="root"></div>');
  globalThis.window = dom.window; globalThis.document = dom.window.document;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.cancelAnimationFrame = () => {};
  const { createRoot } = require('react-dom/client');
  const root = createRoot(document.getElementById('root')), Archetypes = component('Archetypes');
  const { act } = React;
  const render = (props) => act(() => root.render(React.createElement(Archetypes, props)));
  const trigger = (name) => document.querySelector(`[aria-label="View ${name} top 5 · CB"]`);
  try {
    render({ players, loaded: true });
    act(() => trigger('Stopper').click());
    assert.equal(trigger('Stopper').getAttribute('aria-expanded'), 'true');
    assert.equal(document.querySelector('dialog[open]'), null);
    assert.equal(document.querySelectorAll('.archetype-leaders li').length, 5);
    assert.doesNotMatch(document.querySelector('[role=region]').textContent, /percentile/i);
    assert.equal(document.querySelector('.archetype-leaders .ov'), null);
    act(() => trigger('Libero').click());
    assert.equal(trigger('Stopper').getAttribute('aria-expanded'), 'false');
    assert.equal(document.querySelectorAll('[role=region]').length, 1);
    assert.match(document.querySelector('[role=region]').textContent, /Libero/);
    act(() => trigger('Libero').click());
    assert.equal(document.querySelector('[role=region]'), null);
    act(() => trigger('Stopper').click());
    const close = document.querySelector('[aria-label="Close archetype list"]');
    assert.equal(close.tagName, 'BUTTON');
    assert.equal(close.tabIndex, 0);
    act(() => close.click());
    assert.equal(document.querySelector('[role=region]'), null);
    assert.equal(trigger('Stopper').getAttribute('aria-expanded'), 'false');
    assert.equal(document.activeElement, trigger('Stopper'));
    act(() => trigger('Stopper').click());
    render({ loaded: false });
    assert.match(document.querySelector('[role=status]').textContent, /Loading/);
    let retries = 0;
    render({ error: 'internal detail', onRetry: () => retries++ });
    assert.doesNotMatch(document.querySelector('[role=alert]').textContent, /internal detail/);
    act(() => document.querySelector('[role=alert] button').click());
    assert.equal(retries, 1);
    render({ players: [], loaded: true });
    assert.match(document.querySelector('[role=status]').textContent, /No ranked players/);
  } finally {
    act(() => root.unmount()); dom.window.close();
    delete globalThis.window; delete globalThis.document; delete globalThis.IS_REACT_ACT_ENVIRONMENT; delete globalThis.cancelAnimationFrame;
  }
});

test('all qualifying skills earn their own tier, ordered by exact percentile', () => {
  const p = fixture('CB', [90, 89.999, 75, 74.999, 100]);
  const before = structuredClone(p);
  assert.deepEqual(classifyAll(p), [
    { name: 'Ball-Playing CB', metric: 'LB', tier: '+', value: 100 },
    { name: 'Stopper', metric: 'T', tier: '+', value: 90 },
    { name: 'Tactician / Reader', metric: 'I', tier: '−', value: 89.999 },
    { name: 'Sweeper', metric: 'REC', tier: '−', value: 75 },
  ]);
  assert.deepEqual(ratingCard(p).archetypes, classifyAll(p));
  assert.deepEqual(classifyAll(p)[0], classify(p));
  assert.deepEqual(p, before);
  p.attributes.tackles.rating = 1;
  assert.deepEqual(classifyAll(p), classifyAll(before), 'rating changes cannot create or remove percentile badges');
});

test('up to five styles are retained, including stable position-specific ties', () => {
  for (const [position, names] of [
    ['CB', ['Stopper', 'Sweeper', 'Tactician / Reader', 'Libero', 'Ball-Playing CB']],
    ['DM', ['Destroyer', 'Anchor', 'Ball-Winning Midfielder', 'Volante', 'Deep-Lying Playmaker']],
  ]) {
    const p = fixture(position, [90,90,90,90,90]);
    assert.deepEqual(classifyAll(p).map((a) => a.name), names);
    const html = renderToStaticMarkup(React.createElement(PlayerCard, { player: p }));
    assert.equal((html.match(/class="arch-badge /g) ?? []).length, 5);
    for (const name of names) assert.ok(html.includes(name));
    assert.match(html, /aria-label="Player archetypes"/);
  }
});

test('missing, invalid and subthreshold percentiles never produce archetypes', () => {
  for (const value of [null, undefined, NaN, Infinity, -1, 101, '95', 74.999]) {
    assert.deepEqual(classifyAll(fixture('CB', [value,value,value,value,value])), []);
  }
  assert.deepEqual(classifyAll(fixture('GK', [100,100,100,100,100])), []);
  assert.deepEqual(classifyAll({ position: 'CB' }), []);
  const html = renderToStaticMarkup(React.createElement(PlayerCard, { player: fixture('CB', [74,10,20,30,40]) }));
  assert.match(html, /Standard/);
  assert.equal((html.match(/class="arch-badge /g) ?? []).length, 1);
  assert.deepEqual(classifyAllDemo({ position: 'CB', pct: { T: 90, I: 80, C: 100 } }).map((a) => a.name), ['Stopper', 'Tactician / Reader']);
});

test('all public profiles retain existing eligibility, primary style, scores and coverage', () => {
  for (const [i, p] of players.entries()) {
    const source = data.players[i];
    const expected = source.badge_eligible ? classifyAll({ position: p.position, attributes: source.attributes }) : [];
    assert.deepEqual(p.archetypes, expected, p.name);
    assert.deepEqual(publicRatingCard(p).archetypes, expected, p.name);
    assert.equal(p.ovr, source.ovr.value);
    assert.equal(p.ranked, source.ovr.eligible);
    assert.deepEqual(p.attributes, source.attributes);
    assert.deepEqual(p.coverage, source.coverage);
    if (expected.length) assert.deepEqual(p.archetype, expected[0]);
    if (!source.badge_eligible) {
      const html = renderToStaticMarkup(React.createElement(PlayerCard, { player: p }));
      assert.match(html, /Archetype unavailable/);
      assert.equal((html.match(/class="arch-badge /g) ?? []).length, 1);
    }
  }
});

test('real player cards show the full collection and compact previews disclose additional styles', () => {
  const multiple = players.find((p) => p.archetypes.length >= 3);
  assert.ok(multiple);
  const html = renderToStaticMarkup(React.createElement(PlayerCard, { player: multiple }));
  assert.equal((html.match(/class="arch-badge /g) ?? []).length, multiple.archetypes.length);
  for (const a of multiple.archetypes) assert.ok(html.includes(a.name));
  const previews = renderToStaticMarkup(React.createElement(Search, { players, loaded: true }));
  const top = players.filter((p) => p.ranked && p.position === 'CB').sort((a, b) => b.ovr - a.ovr).slice(0, 3);
  for (const p of top.filter((p) => p.archetypes.length > 1)) assert.ok(previews.includes(`+${p.archetypes.length - 1} more`));
});
