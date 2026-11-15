import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire, Module } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { foundationPlayers } from '../src/lib/foundationPlayers.js';
import { parsePublicRatings } from '../src/lib/publicRatingsDelivery.js';

const require = createRequire(import.meta.url), React = require('react');
const { act } = React, { createRoot } = require('react-dom/client');
const directory = fileURLToPath(new URL('..', import.meta.url));
const compiled = require('esbuild').buildSync({ stdin: { resolveDir: directory, loader: 'jsx', contents: `
  import React from 'react';
  import Nav from './src/components/Nav.jsx';
  import Archetypes from './src/components/Archetypes.jsx';
  import Search from './src/components/Search.jsx';
  import { useRevealAll, useSectionScrolling } from './src/lib/hooks.js';
  export { Archetypes, Search };
  export function Page({ late = false }) {
    useRevealAll(); useSectionScrolling();
    return <><a href="#main-content">Skip to main content</a>
      <Nav theme="dark" onToggle={() => {}} sections={[{id:'home',label:'Home'},{id:'search',label:'Search'},{id:'teams',label:'Teams'}]} />
      <main id="main-content" tabIndex={-1}><section id="home" /><section id="search" /><section id="teams" />
      {late && <div className="reveal" data-testid="late">Late content</div>}</main></>;
  }`, }, bundle: true, write: false, platform: 'node', format: 'cjs', jsx: 'automatic',
  external: ['react', 'react/jsx-runtime', 'react-dom'], loader: { '.css': 'empty' } });
const mod = new Module(directory); mod.paths = Module._nodeModulePaths(directory);
mod._compile(compiled.outputFiles[0].text, directory + '/navigation-tests.cjs');
const { Page, Archetypes, Search } = mod.exports;
const players = foundationPlayers(parsePublicRatings(readFileSync(new URL('../public/data/player-ratings-2015-16-v1.json', import.meta.url), 'utf8')));
let dom, root, frames, time, id, headerHeight, observed, revealCallback;
const click = (element) => act(() => element.click());
const advance = () => act(() => {
  for (let i = 0; i < 200 && frames.size; i++) {
    const pending = [...frames.values()]; frames.clear(); time += 16;
    pending.forEach((callback) => callback(time));
  }
});
beforeEach(() => {
  dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost/' });
  globalThis.window = dom.window; globalThis.document = dom.window.document;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.MutationObserver = window.MutationObserver;
  frames = new Map(); time = 0; id = 0; headerHeight = 84; observed = new Set();
  globalThis.requestAnimationFrame = (callback) => { frames.set(++id, callback); return id; };
  globalThis.cancelAnimationFrame = (frame) => frames.delete(frame);
  globalThis.IntersectionObserver = window.IntersectionObserver = class {
    constructor(callback) { revealCallback = callback; }
    observe(element) { observed.add(element); }
    unobserve(element) { observed.delete(element); }
    disconnect() { observed.clear(); }
  };
  window.matchMedia = (query) => ({ matches: query.includes('prefers-reduced-motion'), addEventListener() {}, removeEventListener() {} });
  window.scrollTo = ({ top }) => { window.scrollY = top; window.dispatchEvent(new window.Event('scroll')); };
  Object.defineProperty(document.documentElement, 'scrollHeight', { value: 4000 });
  window.HTMLElement.prototype.getBoundingClientRect = function () {
    const height = this.classList.contains('nav-in') ? headerHeight : 300;
    const top = ({ search: 1600, teams: 2400 }[this.id] ?? 0) - window.scrollY;
    return { top, bottom: top + height, height };
  };
  window.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  window.HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
  root = createRoot(document.getElementById('root'));
});
afterEach(() => {
  act(() => root.unmount()); dom.window.close();
  for (const key of ['window', 'document', 'MutationObserver', 'IntersectionObserver', 'requestAnimationFrame', 'cancelAnimationFrame', 'IS_REACT_ACT_ENVIRONMENT']) delete globalThis[key];
});

test('skip link focuses main; navigation lands below the measured header and tracks the section', () => {
  act(() => root.render(React.createElement(Page)));
  assert.equal(document.documentElement.style.getPropertyValue('--nav-height'), '84px');
  click(document.querySelector('a[href="#main-content"]'));
  assert.equal(document.activeElement.id, 'main-content');
  headerHeight = 140; act(() => window.dispatchEvent(new window.Event('resize'))); advance();
  assert.equal(document.documentElement.style.getPropertyValue('--nav-height'), '140px');
  click(document.querySelector('.nav-links a[href="#search"]')); advance();
  assert.equal(window.scrollY, 1444);
  assert.equal(window.location.hash, '#search');
  assert.equal(document.querySelector('.nav-links a[aria-current="page"]').textContent, 'Search');
});

test('content inserted after ratings load is registered for scroll reveal', async () => {
  act(() => root.render(React.createElement(Page)));
  await act(async () => root.render(React.createElement(Page, { late: true })));
  const late = document.querySelector('[data-testid="late"]');
  assert.ok(observed.has(late));
  revealCallback([{ target: late, isIntersecting: true }]);
  assert.ok(late.classList.contains('in'));
  assert.equal(observed.has(late), false);
});

test('archetype profiles use the mobile sheet and return focus to the chosen player', () => {
  window.matchMedia = () => ({ matches: true, addEventListener() {}, removeEventListener() {} });
  act(() => root.render(React.createElement(Archetypes, { players, loaded: true })));
  click(document.querySelector('[aria-label="View Stopper top 5 · CB"]'));
  const trigger = document.querySelector('.archetype-panel.open .leader-card');
  trigger.focus(); click(trigger);
  assert.equal(document.querySelector('.archetype-dialog'), null);
  const sheet = document.querySelector('.player-dialog[open]');
  assert.ok(sheet); assert.ok(sheet.querySelector('.sheet-handle'));
  assert.equal(document.activeElement.getAttribute('aria-label'), 'Close player card');
  click(sheet.querySelector('[aria-label="Close player card"]'));
  assert.equal(document.querySelector('.player-dialog[open]'), null);
  assert.equal(document.activeElement, trigger);
});

test('public cards schedule no invisible rating count-up frames', () => {
  window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
  act(() => root.render(React.createElement(Search, { players, loaded: true })));
  click(document.querySelector('.browse-row'));
  assert.ok(document.querySelector('.pcard'));
  assert.equal(frames.size, 0);
});

test('loading reserves three player slots and six directory rows without focusable placeholders', () => {
  act(() => root.render(React.createElement(Search)));
  assert.equal(document.querySelectorAll('.loading-player-card').length, 3);
  assert.equal(document.querySelectorAll('.loading-directory-row').length, 6);
  assert.match(document.querySelector('[role="status"]').textContent, /Loading player ratings/);
  assert.equal(document.querySelectorAll('.search-loading button,.search-loading input,.search-loading a').length, 0);
});
