import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire, Module } from 'node:module';
import { fileURLToPath } from 'node:url';
import { parsePublicRatings } from '../src/lib/publicRatingsDelivery.js';
import { foundationPlayers, publicRatingCard, displayOverall } from '../src/lib/foundationPlayers.js';
import { search } from '../src/lib/search.js';
import { publicPlayerCopy } from '../src/lib/publicPlayerCopy.js';
import { playerName } from '../src/lib/playerNames.js';
import { directoryPage } from '../src/lib/directoryPage.js';

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
    assert.equal(p.id, approved.id); assert.equal(p.canonicalName, approved.name);
    const clubNames = approved.clubs.map((c) => c.name === 'Marseille' ? 'Olympique de Marseille' : c.name);
    assert.equal(p.team, clubNames.filter((name, i) => clubNames.indexOf(name) === i).join(' / '));
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

test('club display collapses the verified Marseille alias while preserving transfers and source records', () => {
  const source = data.players[0];
  const clubs = [
    { competition_name: 'Serie A', name: 'Juventus' },
    { competition_name: 'Ligue 1', name: 'Marseille' },
    { competition_name: 'Ligue 1', name: 'Olympique de Marseille' },
  ];
  const before = structuredClone(clubs);
  assert.equal(foundationPlayers({ players: [{ ...source, clubs }] })[0].team, 'Juventus / Olympique de Marseille');
  assert.deepEqual(clubs, before);
});

test('existing search finds real names with accents and retains excluded and incomplete profiles', () => {
  assert.ok(search('kante', players).matches.some((p) => p.name.includes('Kanté')));
  assert.equal(search('Marcus Delacroix', players).matches.length, 0);
  const die = players.find((p) => p.canonicalName.includes('Sereso Geoffroy Gonzaroua Dié'));
  assert.equal(die.ranked, false); assert.equal(displayOverall(die.ovr), '92.00');
  assert.ok(search(die.name, players).matches.includes(die));
  assert.match(die.ratingNotice, /Not ranked/);
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
  assert.match(failed, /role="alert"/); assert.match(failed, /Try again/);
  assert.doesNotMatch(failed, /top-card/);
});

test('original card presents exact approved OVR, missing scores and coverage without inventing values', () => {
  const PlayerCard = component('../src/components/PlayerCard.jsx');
  const kante = players.find((p) => p.name.includes('Kanté'));
  const html = renderToStaticMarkup(React.createElement(PlayerCard, { player: kante }));
  assert.match(html, /83\.08/); assert.match(html, /Overall rating/);
  assert.match(html, /Confirmed minutes/);
  assert.match(html, /Included in the position rankings/);
  assert.match(html, /Historical season coverage is unverified/);
  assert.match(html, /ranking eligibility does not certify full-season coverage/);
  const partial = players.find((p) => p.ovr === null);
  const missing = renderToStaticMarkup(React.createElement(PlayerCard, { player: partial }));
  assert.match(missing, /N\/A/); assert.match(missing, /Not included in rankings/);
  assert.doesNotMatch(missing, /class="shape"/);
});

test('all 691 cards explain ranking and missingness without leaking internal codes, including disclosure contents', () => {
  const PlayerCard = component('../src/components/PlayerCard.jsx');
  const technical = /[A-Z]{2,}_[A-Z_]+|Formula B|SHA256|fingerprint|normalization|reference candidate|experimental|production|publication|fixture scope/i;
  for (const p of players) {
    const html = renderToStaticMarkup(React.createElement(PlayerCard, { player: p }));
    assert.equal(data.players.find((source) => source.id === p.id).partial_season, true);
    assert.match(html, /Historical season coverage is unverified/, p.name);
    assert.match(html, /Confirmed minutes describe supported observed matches/, p.name);
    assert.doesNotMatch(html, technical, p.name);
    assert.doesNotMatch(html, /\u2014/, p.name);
    assert.match(html, /Rating details/);
    if (p.ranked) {
      assert.equal(p.ratingNotice, null);
      assert.doesNotMatch(html, /class="warn/);
    } else {
      assert.ok(p.ratingNotice);
      assert.ok(p.ratingDetails.explanations.length > 0);
    }
    for (const a of Object.values(p.attributes)) {
      for (const code of [...a.missingness, ...a.warnings]) assert.ok(!html.includes(code), `${p.name}: ${code}`);
    }
  }
});

test('verified names preserve canonical identity, search aliases and never merge similar names', () => {
  assert.equal(players.filter((p) => p.name !== p.canonicalName).length, 250);
  assert.equal(new Set(players.map((p) => p.id)).size, 691);
  assert.equal(new Set(players.map((p) => p.name.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase())).size, 691);
  for (const p of players) {
    for (const name of [p.name, p.canonicalName, ...p.aliases]) {
      assert.ok(search(name, players, 691).matches.includes(p), `${p.id}: ${name}`);
    }
  }
  const ramos = players.find((p) => p.canonicalName === 'Sergio Ramos García');
  assert.equal(ramos.name, 'Sergio Ramos');
  assert.equal(search('Sergio Ramos Garcia', players).matches[0].id, ramos.id);
  const matip = players.find((p) => p.canonicalName === 'Joël Andre Job Matip');
  assert.equal(search('Joel Matip', players).matches[0].id, matip.id);
  assert.equal(search('Frederik Sorensen', players).matches[0].name, 'Frederik Sørensen');
  assert.equal(search('Emil Hallfredsson', players).matches[0].name, 'Emil Hallfreðsson');
  assert.equal(playerName({player_id: 5201, season_name: 'unknown', name: 'Canonical'}).name, 'Canonical');
  const similar = [{id:'one',name:'Alex',canonicalName:'First Alex',aliases:['Shared'],ovr:70},
    {id:'two',name:'Alex',canonicalName:'Second Alex',aliases:['Shared'],ovr:70}];
  assert.deepEqual(search('Shared', similar).matches.map((p) => p.id), ['one','two']);
  assert.deepEqual(search('Second Alex', similar).matches.map((p) => p.id), ['two']);
});

test('player card retains keyboard access, a persistent close rail and bounded responsive scrolling', () => {
  const PlayerCard = component('../src/components/PlayerCard.jsx');
  const p = players.find((p) => p.name === 'Sergio Ramos');
  const html = renderToStaticMarkup(React.createElement(PlayerCard, { player: p }));
  assert.match(html, /tabindex="0" aria-label="Sergio Ramos player card"/);
  assert.match(html, /class="card-close-rail"><button type="button" class="close"/);
  assert.match(html, /Full name: Sergio Ramos García/);
  assert.match(html, /Archetype unavailable/);
  const css = readFileSync(new URL('../src/styles.css', import.meta.url), 'utf8');
  const cardRule = css.match(/\.pcard \{([^}]+)\}/)[1];
  assert.match(cardRule, /max-height: 90dvh/);
  assert.match(cardRule, /overflow-y: auto/);
  assert.match(cardRule, /overscroll-behavior-y: contain/);
  assert.match(css, /@media \(min-width: 960px\) \{ \.pcard \{ max-height: calc\(100dvh - 100px\)/);
  assert.match(css, /\.card-close-rail \{ position: sticky; top: 0/);
});

test('every six-row directory page covers all profiles once, with no placeholder rows', () => {
  for (const pos of ['CB','DM']) {
    const group = players.filter((p) => p.position === pos).sort((a,b) => (b.ovr ?? -1)-(a.ovr ?? -1));
    const {pageCount} = directoryPage(group, 1); const seen = [];
    for (let page=1; page<=pageCount; page++) {
      const result = directoryPage(group, page);
      assert.equal(result.currentPage, page);
      assert.equal(result.directory.length, Math.min(6, group.length-(page-1)*6));
      seen.push(...result.directory.map((p) => p.id));
    }
    assert.deepEqual(seen, group.map((p) => p.id));
    assert.equal(new Set(seen).size, group.length);
    assert.equal(directoryPage(group, pageCount+1).currentPage, pageCount);
  }
});

test('all public sections, dynamic directory names and error states are free of em dashes', () => {
  for (const path of ['Hero','Description','Archetypes','Teams','About','Footer']) {
    const C = component(`../src/components/${path}.jsx`);
    assert.doesNotMatch(renderToStaticMarkup(React.createElement(C)), /\u2014/, path);
  }
  const Search = component('../src/components/Search.jsx');
  for (const props of [{players,loaded:true}, {}, {error:'INTERNAL_FAILURE — private details'}]) {
    const html = renderToStaticMarkup(React.createElement(Search,props));
    assert.doesNotMatch(html, /\u2014|INTERNAL_FAILURE/);
  }
  const Footer = component('../src/components/Footer.jsx');
  const html = renderToStaticMarkup(React.createElement(Footer));
  assert.match(html, /href="https:\/\/sac-utd-website.vercel.app\/" target="_blank" rel="noopener noreferrer"/);
  assert.match(html, /Visit SAC Website/);
});

test('specific restrictions stay truthful and unknown future reasons use a safe general explanation', () => {
  for (const [name, words] of [['Sergio Ramos', /minutes could not be confirmed/],
    ['Scott Dann', /actions could not be matched reliably/], ['Adriano Russo', /40 actions/],
    ['Georg Niedermeier', /Bundesliga match coverage/]]) {
    const p = players.find((p) => p.name.includes(name));
    assert.match(p.ratingDetails.explanations.join(' '), words);
  }
  const raw = structuredClone(data.players[0]);
  raw.ovr.eligible = false; raw.ovr.exclusion_reasons = ['FUTURE_PRIVATE_REASON'];
  const copy = publicPlayerCopy(raw);
  assert.match(copy.notice, /Not ranked/);
  assert.doesNotMatch(JSON.stringify(copy), /FUTURE_PRIVATE_REASON/);
});

test('directory remains limited to six rows while search finds profiles outside that page', () => {
  const Search = component('../src/components/Search.jsx');
  const html = renderToStaticMarkup(React.createElement(Search, { players, loaded: true }));
  assert.equal((html.match(/class="browse-row/g) ?? []).length, 6);
  const outside = players.find((p) => p.name.includes('Ramos'));
  assert.equal(outside.ranked, false);
  assert.ok(search(outside.name, players).matches.includes(outside));
  assert.match(html, /Player directory pages/);
  assert.doesNotMatch(html, /class="directory-status/);
});

test('loading and errors use visitor copy and never echo technical exceptions', () => {
  const Search = component('../src/components/Search.jsx');
  const raw = 'Invalid public ratings: release fingerprint SHA256 SECRET_DIAGNOSTIC';
  const failed = renderToStaticMarkup(React.createElement(Search, { error: raw }));
  assert.match(failed, /We couldn’t load the player ratings/);
  assert.doesNotMatch(failed, /fingerprint|SHA256|SECRET_DIAGNOSTIC/);
  assert.doesNotMatch(failed, /Page 1 of 1|Player directory pages/);
  const loading = renderToStaticMarkup(React.createElement(Search));
  assert.match(loading, /Loading player ratings/);
  assert.doesNotMatch(loading, /approved|validating|fallback/i);
  assert.doesNotMatch(loading, /Player directory pages/);
});

test('page-level failure copy does not disclose configuration or exception details', () => {
  const App = component('../src/App.jsx');
  const previous = globalThis.document;
  globalThis.document = { documentElement: { getAttribute: () => 'dark' } };
  let html;
  try { html = renderToStaticMarkup(React.createElement(App)); }
  finally { if (previous === undefined) delete globalThis.document; else globalThis.document = previous; }
  assert.match(html, /This page is unavailable/);
  assert.match(html, /Refresh page/);
  assert.doesNotMatch(html, /window is not defined|VITE_|fallback|ReferenceError|configuration|interface/);
});

test('shared methodology and homepage copy keep limitations clear without implementation language', () => {
  const Description = component('../src/components/Description.jsx');
  const Hero = component('../src/components/Hero.jsx');
  const Archetypes = component('../src/components/Archetypes.jsx');
  const description = renderToStaticMarkup(React.createElement(Description));
  assert.match(description, /not official FIFA or EA ratings/);
  assert.match(description, /900 confirmed minutes/);
  assert.match(description, /40 supported actions under pressure/);
  assert.match(description, /does not establish how many opponents a pass bypassed/);
  assert.match(description, /may not cover a full season|complete season record/);
  assert.doesNotMatch(renderToStaticMarkup(React.createElement(Hero)), /placeholder|MP4|1920|football clips/);
  assert.doesNotMatch(renderToStaticMarkup(React.createElement(Archetypes)), /Every player gets|Breaks lines with/);
});
