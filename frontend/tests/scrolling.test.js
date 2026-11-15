import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
import { activeSectionAt, cancelAutoScroll, scrollToElement } from '../src/lib/scrolling.js';

let dom, frames, time, frameId, target, headerHeight;
function advance(count = 180) {
  for (let i = 0; i < count && frames.size; i++) {
    const pending = [...frames.values()]; frames.clear(); time += 16;
    pending.forEach((callback) => callback(time));
  }
}
beforeEach(() => {
  dom = new JSDOM('<div class="nav-in"></div><section id="target"></section>');
  globalThis.window = dom.window; globalThis.document = dom.window.document;
  frames = new Map(); time = 0; frameId = 0; headerHeight = 84;
  globalThis.requestAnimationFrame = (callback) => { frames.set(++frameId, callback); return frameId; };
  globalThis.cancelAnimationFrame = (id) => frames.delete(id);
  Object.defineProperty(document.documentElement, 'scrollHeight', { value: 4000 });
  Object.defineProperty(window, 'innerHeight', { value: 800 });
  window.matchMedia = () => ({ matches: false });
  window.scrollTo = ({ top }) => { window.scrollY = top; };
  document.querySelector('.nav-in').getBoundingClientRect = () => ({ height: headerHeight });
  target = document.getElementById('target');
  target.getBoundingClientRect = () => ({ top: 1100 - window.scrollY, bottom: 1400 - window.scrollY, height: 300 });
});
afterEach(() => {
  cancelAutoScroll(); dom.window.close(); delete globalThis.window; delete globalThis.document;
  delete globalThis.requestAnimationFrame; delete globalThis.cancelAnimationFrame;
});

test('section landing follows the current header height while scrolling', () => {
  scrollToElement(target, 'start'); advance(5);
  assert.ok(window.scrollY > 0 && window.scrollY < 1000);
  headerHeight = 140; advance();
  assert.equal(window.scrollY, 944);
  assert.equal(frames.size, 0);
});

test('wheel, touch and keyboard input immediately relinquish automatic scrolling', () => {
  for (const event of [new window.Event('wheel'), new window.Event('touchstart'), new window.KeyboardEvent('keydown', { key: 'PageDown' }), new window.Event('pointerdown')]) {
    window.scrollY = 0; scrollToElement(target, 'start'); advance(3);
    window.dispatchEvent(event);
    const stoppedAt = window.scrollY; advance();
    assert.equal(window.scrollY, stoppedAt);
    assert.equal(frames.size, 0);
  }
});

test('expansion and scrolling start together and completion waits for the expanding panel', () => {
  const panel = document.createElement('div'); panel.className = 'expanding-panel'; panel.dataset.settled = 'false';
  document.body.append(panel); panel.append(target);
  scrollToElement(target, 'start'); advance(4);
  assert.ok(window.scrollY > 0);
  advance(); assert.equal(frames.size, 1);
  panel.dataset.settled = 'true'; advance();
  assert.equal(frames.size, 0);
});

test('retargeting preserves the on-screen position; reduced motion lands immediately', () => {
  scrollToElement(target, 'start'); advance(5);
  const position = window.scrollY;
  scrollToElement(document.body, 'start');
  assert.equal(window.scrollY, position);
  assert.equal(frames.size, 1);
  cancelAutoScroll();
  window.matchMedia = () => ({ matches: true });
  scrollToElement(target, 'start');
  assert.equal(window.scrollY, 1000);
  assert.equal(frames.size, 0);
});

test('section highlighting has a small stable band around section boundaries', () => {
  const sections = (top) => [{ id: 'home', top: -500 }, { id: 'search', top }];
  assert.equal(activeSectionAt(sections(196), 200, 'home'), 'home');
  assert.equal(activeSectionAt(sections(187), 200, 'home'), 'search');
  assert.equal(activeSectionAt(sections(205), 200, 'search'), 'search');
  assert.equal(activeSectionAt(sections(213), 200, 'search'), 'home');
});
