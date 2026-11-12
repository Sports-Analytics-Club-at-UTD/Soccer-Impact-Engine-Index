import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire, Module } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { SPATIAL_DOMINANCE, SPATIAL_ZONES, spatialColor, spatialLabelColor } from '../src/lib/spatialDominance.js';

const require = createRequire(import.meta.url), React = require('react');
const { createRoot } = require('react-dom/client');
const { act } = React;
const filename = fileURLToPath(new URL('../src/components/Teams.jsx', import.meta.url));
const result = require('esbuild').buildSync({ entryPoints: [filename], bundle: true, write: false,
  platform: 'node', format: 'cjs', jsx: 'automatic', logLevel: 'silent',
  external: ['react', 'react/jsx-runtime'], loader: { '.css': 'empty' } });
const mod = new Module(filename); mod.paths = Module._nodeModulePaths(fileURLToPath(new URL('..', import.meta.url)));
mod._compile(result.outputFiles[0].text, filename);
const Teams = mod.exports.default;

test('public chart labels and match counts retain all three original row-major layouts', () => {
  assert.deepEqual(Object.values(SPATIAL_DOMINANCE).map(({ matches, percentages }) => [matches, percentages]), [
    [57, [58,44,31,75,56,33,58,44,29]],
    [35, [62,44,29,74,55,31,61,46,33]],
    [31, [59,42,25,71,52,30,58,44,30]],
  ]);
  assert.deepEqual(SPATIAL_ZONES.map(({ row, column }) => [row, column]), [[0,0],[0,1],[0,2],[1,0],[1,1],[1,2],[2,0],[2,1],[2,2]]);
  assert.equal(SPATIAL_ZONES[3].name, 'Defensive center');
});

test('percentage labels meet WCAG AA contrast across the entire shared scale', () => {
  const luminance = (rgb) => rgb.map((v) => { const c = v / 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; })
    .reduce((sum, v, i) => sum + v * [.2126,.7152,.0722][i], 0);
  for (let value = 0; value <= 100; value++) {
    const bg = luminance(spatialColor(value).match(/\d+/g).map(Number));
    const fg = luminance(spatialLabelColor(value) === '#ffffff' ? [255,255,255] : [0,0,0]);
    assert.ok((Math.max(bg, fg) + .05) / (Math.min(bg, fg) + .05) >= 4.5, `contrast at ${value}%`);
  }
});

test('team selection, focus, arrow keys, Escape, hover and tap use the pitch zones', () => {
  const dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost' });
  globalThis.window = dom.window; globalThis.document = dom.window.document;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.cancelAnimationFrame = () => {};
  window.matchMedia = () => ({ matches: true });
  const container = document.getElementById('root'), root = createRoot(container);
  const click = (el) => act(() => el.click());
  const zones = () => [...container.querySelectorAll('.spatial-zone')];
  const tip = () => container.querySelector('[role="tooltip"]');
  try {
    act(() => root.render(React.createElement(Teams)));
    assert.equal(zones().length, 0);
    const badges = [...container.querySelectorAll('.badge')];
    for (const [i, data] of Object.values(SPATIAL_DOMINANCE).entries()) {
      click(badges[i]);
      assert.equal(badges[i].getAttribute('aria-controls'), 'team-spatial-panel');
      assert.deepEqual(zones().map((el) => Number(el.textContent.replace('%', ''))), data.percentages);
      assert.match(container.querySelector('.spatial-heading').textContent, new RegExp(`${data.matches} matches`));
      assert.equal(tip(), null, 'team changes clear the previous selection');
      act(() => zones()[3].focus());
      assert.match(tip().textContent, /Defensive center/);
      assert.match(tip().textContent, /observed cells/);
      assert.equal(document.activeElement.getAttribute('aria-describedby'), tip().id);
      act(() => document.activeElement.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })));
      assert.equal(document.activeElement.dataset.zone, '4');
      act(() => document.activeElement.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })));
      assert.equal(tip(), null);
      click(zones()[8]);
      assert.match(tip().textContent, /Attacking lower channel/);
      assert.equal(zones()[8].getAttribute('aria-pressed'), 'true');
      act(() => document.body.dispatchEvent(new window.Event('pointerdown', { bubbles: true })));
      assert.equal(tip(), null);
      act(() => require('react-dom/test-utils').Simulate.pointerEnter(zones()[0], { pointerType: 'mouse' }));
      assert.match(tip().textContent, /Defensive upper channel/);
      act(() => require('react-dom/test-utils').Simulate.pointerLeave(container.querySelector('.spatial-pitch')));
      assert.equal(tip(), null);
    }
    assert.equal(container.querySelectorAll('.spatial-zone').length, 9);
    assert.equal(container.querySelectorAll('#teams img').length, 0);
    assert.match(container.querySelector('.spatial-methodology').textContent, /unrounded data, season and fixture lists are unavailable/);
    click(badges[2]);
    assert.equal(zones().length, 0);
  } finally {
    act(() => root.unmount()); dom.window.close();
    delete globalThis.window; delete globalThis.document; delete globalThis.IS_REACT_ACT_ENVIRONMENT; delete globalThis.cancelAnimationFrame;
  }
});
