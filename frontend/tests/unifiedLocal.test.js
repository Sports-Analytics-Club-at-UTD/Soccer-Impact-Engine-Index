import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire, Module } from 'node:module';
import { fileURLToPath } from 'node:url';
import { LOCAL_SECTIONS, readLocalRoute, localHref, isPlainNavigation } from '../src/dev/localNavigation.js';

test('six unified destinations round-trip canonical identities and independent comparison state', () => {
  assert.deepEqual(LOCAL_SECTIONS.map((s) => s.label), ['Home', 'Players', 'Leaderboards', 'Compare', 'Teams', 'About']);
  for (const { id: view } of LOCAL_SECTIONS) {
    const route = { view, playerId: '3961:2015/2016', firstId: '5574:2015/2016', secondId: '3500:2015/2016', group: 'CB' };
    assert.deepEqual(readLocalRoute(localHref(route)), route);
  }
});

test('empty, invalid and old fragment destinations fail safely without admitting a player', () => {
  assert.equal(readLocalRoute('').view, 'home');
  assert.equal(readLocalRoute('#not-a-view?group=GK').view, 'home');
  assert.equal(readLocalRoute('#leaderboards?group=GK').group, 'MID');
  assert.equal(readLocalRoute('#experimental-discovery').view, 'players');
  assert.equal(readLocalRoute('#experimental-comparison').view, 'compare');
  assert.equal(readLocalRoute('#players?player=unknown').playerId, 'unknown'); // Lookup failure, never fallback identity.
  assert.equal(readLocalRoute(localHref({ view: 'players' })).playerId, null);
});

test('modified link clicks retain browser-native new-tab behavior', () => {
  const plain = { button: 0, defaultPrevented: false };
  assert.equal(isPlainNavigation(plain), true);
  for (const patch of [{button:1}, {metaKey:true}, {ctrlKey:true}, {shiftKey:true}, {altKey:true}, {defaultPrevented:true}]) {
    assert.equal(isPlainNavigation({ ...plain, ...patch }), false);
  }
});

const require = createRequire(import.meta.url), React = require('react'), { renderToStaticMarkup } = require('react-dom/server');
function component(name) {
  const filename = fileURLToPath(new URL(name, import.meta.url));
  const result = require('esbuild').buildSync({entryPoints:[filename],bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',logLevel:'silent',external:['react','react/jsx-runtime'],loader:{'.css':'empty'}});
  const mod = new Module(filename); mod.paths = Module._nodeModulePaths(fileURLToPath(new URL('..',import.meta.url))); mod._compile(result.outputFiles[0].text,filename); return mod.exports.default;
}

test('unified home reuses the shared navigation and retained Teams without embedding real player data', () => {
  const Experience = component('../src/dev/FiveAttributeExperimentalExperience.jsx');
  const html = renderToStaticMarkup(React.createElement(Experience, { theme: 'dark' }));
  assert.match(html, /Main navigation/);
  for (const { id, label } of LOCAL_SECTIONS) assert.ok(html.includes(`href="#${id}"`), label);
  assert.match(html, /Soccer Impact Index/);
  assert.match(html, /uneven match coverage/);
  assert.match(html, /Loading and validating player observations/);
  assert.match(html, /class="unified-teams" hidden/);
  assert.match(html, /Paris Saint-Germain/);
  assert.doesNotMatch(html, /3961:2015|N&#x27;&#x27;Golo|classification scope pending/);
});

test('shared navigation retains the existing default demo destinations', () => {
  const Nav = component('../src/components/Nav.jsx');
  const html = renderToStaticMarkup(React.createElement(Nav, { theme: 'dark' }));
  assert.match(html, /aria-label="Sections"/);
  assert.match(html, /href="#archetypes"/);
  assert.match(html, /href="#search"/);
  assert.doesNotMatch(html, /five-attribute-experimental/);
});
