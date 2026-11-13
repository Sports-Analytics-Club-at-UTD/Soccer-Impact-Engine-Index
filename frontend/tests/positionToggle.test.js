import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire, Module } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { foundationPlayers } from '../src/lib/foundationPlayers.js';
import { parsePublicRatings } from '../src/lib/publicRatingsDelivery.js';

const require = createRequire(import.meta.url), React = require('react');
const initialDom = new JSDOM('<!doctype html>');
globalThis.window = initialDom.window; globalThis.document = initialDom.window.document;
const { createRoot } = require('react-dom/client');
initialDom.window.close();
const { act } = React;
const filename = fileURLToPath(new URL('../src/components/Search.jsx', import.meta.url));
const result = require('esbuild').buildSync({ entryPoints: [filename], bundle: true, write: false,
  platform: 'node', format: 'cjs', jsx: 'automatic', logLevel: 'silent',
  external: ['react', 'react/jsx-runtime'], loader: { '.css': 'empty' } });
const mod = new Module(filename); mod.paths = Module._nodeModulePaths(fileURLToPath(new URL('..', import.meta.url)));
mod._compile(result.outputFiles[0].text, filename);
const Search = mod.exports.default;
const players = foundationPlayers(parsePublicRatings(readFileSync(new URL('../public/data/player-ratings-2015-16-v1.json', import.meta.url), 'utf8')));
let dom, root, container;
const button = (name) => [...container.querySelectorAll('button')].find((el) => el.textContent === name);
const click = (el) => act(() => el.click());
const rows = () => [...container.querySelectorAll('.browse-row .nm')].map((el) => el.firstChild.textContent);
const ranked = (pos) => {
  const ordered = players.filter((p) => p.position === pos).sort((a, b) => (b.ovr ?? -1) - (a.ovr ?? -1));
  return [...ordered.filter((p) => p.ranked), ...ordered.filter((p) => !p.ranked)];
};
const status = () => container.querySelector('.directory-pages [role=status]').textContent;
function query(value) {
  const input = container.querySelector('input');
  act(() => {
    Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, 'value').set.call(input, value);
    require('react-dom/test-utils').Simulate.change(input, { target: { value } });
  });
  return input;
}
function pickFirst() {
  act(() => require('react-dom/test-utils').Simulate.keyDown(container.querySelector('input'), { key: 'Enter', preventDefault() {} }));
}
beforeEach(() => {
  dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost' });
  globalThis.window = dom.window; globalThis.document = dom.window.document;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.cancelAnimationFrame = () => {};
  window.matchMedia = (query) => ({ matches: query.includes('prefers-reduced-motion'), addEventListener() {}, removeEventListener() {} });
  container = document.getElementById('root'); root = createRoot(container);
  act(() => root.render(React.createElement(Search, { players, loaded: true })));
});
afterEach(() => { act(() => root.unmount()); dom.window.close(); delete globalThis.window; delete globalThis.document; delete globalThis.IS_REACT_ACT_ENVIRONMENT; delete globalThis.cancelAnimationFrame; });

test('CB is selected by default with correctly sorted first-page players', () => {
  assert.equal(button('CB').getAttribute('aria-pressed'), 'true');
  assert.equal(button('DM').getAttribute('aria-pressed'), 'false');
  assert.deepEqual(rows(), ranked('CB').slice(0, 6).map((p) => p.name));
});

test('ranked players precede higher-rated unranked players while ties, missing ratings and search remain intact', () => {
  const base = players.find((p) => p.position === 'CB' && p.ranked);
  const sample = [
    { ...base, id: 'unranked-high', name: 'Unranked High', ranked: false, ovr: 99 },
    { ...base, id: 'ranked-low', name: 'Ranked Low', ranked: true, ovr: 60 },
    { ...base, id: 'ranked-high', name: 'Ranked High', ranked: true, ovr: 80 },
    { ...base, id: 'unranked-missing', name: 'Unranked Missing', ranked: false, ovr: null },
    { ...base, id: 'ranked-tie', name: 'Ranked Tie', ranked: true, ovr: 80 },
  ];
  act(() => root.render(React.createElement(Search, { players: sample, loaded: true })));
  assert.deepEqual(rows(), ['Ranked High', 'Ranked Tie', 'Ranked Low', 'Unranked High', 'Unranked Missing']);
  assert.deepEqual([...container.querySelectorAll('.top-card .name')].map((el) => el.textContent), ['Ranked High', 'Ranked Tie', 'Ranked Low']);
  query('Unranked High');
  assert.match(container.querySelector('[role=listbox]').textContent, /Unranked High/);
});
test('CB to DM to CB updates selection, lists, counts and eligible top three', () => {
  for (const pos of ['DM', 'CB']) {
    click(button(pos));
    assert.equal(button(pos).getAttribute('aria-pressed'), 'true');
    assert.deepEqual(rows(), ranked(pos).slice(0, 6).map((p) => p.name));
    assert.ok(status().endsWith(`${ranked(pos).length} players`));
    const names = [...container.querySelectorAll('.top-card .name')].map((el) => el.textContent);
    assert.deepEqual(names, ranked(pos).filter((p) => p.ranked).slice(0, 3).map((p) => p.name));
  }
});
test('all pages preserve ordering and unique membership with no cross-position leakage', () => {
  for (const pos of ['CB', 'DM']) {
    click(button(pos)); const seen = [];
    do { seen.push(...rows()); if (button('Next').disabled) break; click(button('Next')); } while (true);
    assert.deepEqual(seen, ranked(pos).map((p) => p.name));
    assert.equal(new Set(seen).size, seen.length);
    assert.equal(button('Next').disabled, true);
    click(button(pos === 'CB' ? 'DM' : 'CB'));
    assert.match(status(), /^Page 1 of/);
    assert.equal(button('Previous').disabled, true);
  }
});
test('global accented player search selects DM from CB and synchronizes toggle', () => {
  query('kante'); assert.match(container.querySelector('[role=listbox]').textContent, /Kant/);
  pickFirst(); assert.equal(button('DM').getAttribute('aria-pressed'), 'true');
  assert.match(container.querySelector('input').value, /Kant/);
  assert.deepEqual(rows(), ranked('DM').slice(0, 6).map((p) => p.name));
});
test('search selects CB from DM and resets pagination', () => {
  click(button('DM')); click(button('Next')); query('Sergio Ramos'); pickFirst();
  assert.equal(button('CB').getAttribute('aria-pressed'), 'true'); assert.match(status(), /^Page 1 of/);
});
test('explicit position switch clears query, suggestions and selected card', () => {
  query('kante'); pickFirst(); click(button('CB'));
  assert.equal(container.querySelector('input').value, '');
  assert.equal(container.querySelector('[role=listbox]'), null);
  assert.ok(container.querySelector('.empty-card')); assert.match(status(), /^Page 1 of/);
});
test('clearing search preserves current position and full directory', () => {
  query('kante'); pickFirst(); click(container.querySelector('[aria-label="Clear search"]'));
  assert.equal(container.querySelector('input').value, ''); assert.equal(button('DM').getAttribute('aria-pressed'), 'true');
  assert.deepEqual(rows(), ranked('DM').slice(0, 6).map((p) => p.name));
});
test('empty search results preserve directory and position; toggle clears no-result message', () => {
  query('zzzzzzzzzzzzzzzzzz'); assert.match(container.querySelector('.suggest').textContent, /No player found/);
  assert.equal(button('CB').getAttribute('aria-pressed'), 'true');
  assert.deepEqual(rows(), ranked('CB').slice(0, 6).map((p) => p.name));
  click(button('DM')); assert.equal(container.querySelector('.suggest').textContent, '');
});
test('position control exposes named group, pressed states and focusable native buttons', () => {
  const group = container.querySelector('[role=group][aria-label="Player directory position"]');
  assert.ok(group); assert.deepEqual([...group.children].map((el) => el.textContent), ['CB', 'DM']);
  for (const pos of ['DM', 'CB']) {
    const el = button(pos); assert.equal(el.tagName, 'BUTTON'); assert.equal(el.type, 'button');
    assert.equal(el.tabIndex, 0); el.focus(); assert.equal(document.activeElement, el);
    click(el); assert.equal(el.getAttribute('aria-pressed'), 'true');
  }
});
