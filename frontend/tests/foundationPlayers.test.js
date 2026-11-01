import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire, Module } from 'node:module';
import { fileURLToPath } from 'node:url';
import { parsePublicRatings } from '../src/lib/publicRatingsDelivery.js';
import { foundationPlayers, publicRatingCard, displayOverall } from '../src/lib/foundationPlayers.js';
import { search } from '../src/lib/search.js';

const data = parsePublicRatings(readFileSync(new URL('../public/data/player-ratings-2015-16-v1.json', import.meta.url), 'utf8'));
const players = foundationPlayers(data);
const require = createRequire(import.meta.url), React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
function component(path) {
  const filename = fileURLToPath(new URL(path, import.meta.url));
  const result = require('esbuild').buildSync({ entryPoints: [filename], bundle: true, write: false,
    platform: 'node', format: 'cjs', jsx: 'automatic', logLevel: 'silent',
    external: ['react', 'react/jsx-runtime'], loader: { '.css': 'empty' },
    define: { 'import.meta.env.DEV': 'false', 'import.meta.env.BASE_URL': '"/"' } });
  const mod = new Module(filename); mod.paths = Module._nodeModulePaths(fileURLToPath(new URL('..', import.meta.url)));
  mod._compile(result.outputFiles[0].text, filename); return mod.exports.default;
}

test('foundation adapter preserves every approved identity, score, club, position and eligibility decision', () => {
  assert.equal(players.length, 691);
  for (let i = 0; i < players.length; i++) {
    const p = players[i], approved = data.players[i], card = publicRatingCard(p);
    assert.equal(p.id, approved.id); assert.equal(p.name, approved.name);
    assert.equal(p.team, approved.clubs.map((c) => c.name).join(' / '));
    assert.equal(p.primaryPosition, approved.primary_position);
    assert.equal(p.minutes, approved.coverage.supported_minutes);
    assert.deepEqual(p.attributes, approved.attributes);
    assert.equal(p.ovr, approved.ovr.value); assert.equal(p.ranked, approved.ovr.eligible);
    assert.equal(card.ovr, approved.ovr.value);
    for (const a of card.attributes) {
      assert.equal(a.value, approved.attributes[a.id].rating);
      assert.equal(a.percentile, approved.attributes[a.id].percentile);
    }
    if (!approved.badge_eligible) assert.equal(card.archetype.tier, null);
  }
  assert.equal(players.filter((p) => p.ranked && p.position === 'CB').length, 107);
  assert.equal(players.filter((p) => p.ranked && p.position === 'DM').length, 124);
  assert.equal(players.filter((p) => p.ovr === null).length, 5);
});

test('existing search finds real names with accents and retains excluded and incomplete profiles', () => {
  assert.ok(search('kante', players).matches.some((p) => p.name.includes('Kanté')));
  assert.equal(search('Marcus Delacroix', players).matches.length, 0);
  const die = players.find((p) => p.name.includes('Sereso Geoffroy Gonzaroua Dié'));
  assert.equal(die.ranked, false); assert.equal(displayOverall(die.ovr), '92.00');
  assert.ok(search(die.name, players).matches.includes(die));
  assert.match(die.ratingNotice, /NOT RANKED/);
  for (const p of players.filter((p) => p.ovr === null)) {
    assert.equal(displayOverall(p.ovr), 'N/A');
    assert.ok(search(p.name, players).matches.includes(p));
  }
});

test('foundation page keeps every original section and its shared navigation and footer', () => {
  const Experience = component('../src/components/DemoExperience.jsx');
  const html = renderToStaticMarkup(React.createElement(Experience, { theme: 'dark' }));
  for (const id of ['home', 'description', 'archetypes', 'search', 'teams', 'about']) assert.ok(html.includes(`id="${id}"`), id);
  assert.match(html, /aria-label="Sections"/);
  assert.match(html, /class="footer/);
  assert.match(html, /Paris Saint-Germain/);
  assert.doesNotMatch(html, /fictional players|unified-destinations/);
});

test('foundation search shows only eligible top-three cards and displays load and retry states', () => {
  const Search = component('../src/components/Search.jsx');
  const html = renderToStaticMarkup(React.createElement(Search, { players, loaded: true }));
  const top = [...players.filter((p) => p.position === 'CB' && p.ranked)].sort((a, b) => b.ovr - a.ovr).slice(0, 3);
  const cards = html.slice(html.indexOf('class="top3"'), html.indexOf('class="search-grid"'));
  for (const p of top) assert.ok(cards.includes(displayOverall(p.ovr)), p.name);
  assert.equal((cards.match(/top-card/g) ?? []).length, 3);
  assert.doesNotMatch(html, /Demo OVR|fictional players|Marcus Delacroix/);
  const failed = renderToStaticMarkup(React.createElement(Search, { error: 'Release unavailable' }));
  assert.match(failed, /role="alert"/); assert.match(failed, /Retry player data/);
  assert.doesNotMatch(failed, /top-card/);
});

test('original card presents exact approved OVR, missing scores and coverage without inventing values', () => {
  const PlayerCard = component('../src/components/PlayerCard.jsx');
  const kante = players.find((p) => p.name.includes('Kanté'));
  const html = renderToStaticMarkup(React.createElement(PlayerCard, { player: kante }));
  assert.match(html, /83\.08/); assert.match(html, /Formula B OVR/);
  assert.match(html, /Partial-season observations/);
  assert.match(html, /Progressive passing is a proxy/);
  const partial = players.find((p) => p.ovr === null);
  const missing = renderToStaticMarkup(React.createElement(PlayerCard, { player: partial }));
  assert.match(missing, /N\/A/); assert.match(missing, /NOT RANKED/);
  assert.doesNotMatch(missing, /class="shape"/);
});
