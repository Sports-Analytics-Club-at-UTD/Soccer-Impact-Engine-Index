import test from 'node:test';
import assert from 'node:assert/strict';
import { createSpring, springStep, rubberband, sheetDestination } from '../src/lib/motion.js';

test('sheet release projects velocity, allows reversal, and resists upper-bound overshoot', () => {
  assert.equal(sheetDestination(30, 1000, 600), 600);
  assert.equal(sheetDestination(300, -1000, 600), 0);
  assert.equal(sheetDestination(50, 0, 600), 0);
  assert.equal(sheetDestination(300, 0, 600), 600);
  assert.ok(rubberband(-100, 600) < 0);
  assert.ok(Math.abs(rubberband(-100, 600)) < 100);
  assert.ok(Math.abs(rubberband(-1000, 600)) < 600);
});

test('critically damped motion settles without overshoot and carries incoming velocity', () => {
  let position = 600, velocity = 0;
  for (let i = 0; i < 120; i++) {
    const next = springStep(position, velocity, 0, 1 / 60);
    assert.ok(next.position >= 0 && next.position <= position);
    ({ position, velocity } = next);
  }
  assert.ok(position < .001);
  assert.ok(springStep(100, 500, 600, 1 / 60).position > springStep(100, 0, 600, 1 / 60).position);
});

test('spring retargeting starts at its current presentation and cancels obsolete completion', () => {
  let id = 0, time = 0, completed = 0;
  const frames = new Map(), samples = [];
  globalThis.window = { matchMedia: () => ({ matches: false }) };
  globalThis.requestAnimationFrame = (callback) => { frames.set(++id, callback); return id; };
  globalThis.cancelAnimationFrame = (frame) => frames.delete(frame);
  const tick = () => {
    const pending = [...frames.values()]; frames.clear(); time += 16;
    pending.forEach((callback) => callback(time));
  };
  try {
    const spring = createSpring(0, (value) => samples.push(value));
    spring.to(600, 0, () => completed++);
    for (let i = 0; i < 5; i++) tick();
    const presentation = spring.position;
    spring.to(0);
    assert.equal(spring.position, presentation);
    assert.equal(frames.size, 1);
    for (let i = 0; i < 150 && frames.size; i++) tick();
    assert.equal(spring.position, 0);
    assert.equal(completed, 0);
    assert.equal(frames.size, 0);
    assert.ok(samples.length > 5);
    window.matchMedia = () => ({ matches: true });
    spring.to(600, 0, () => completed++);
    assert.equal(spring.position, 600);
    assert.equal(completed, 1);
    assert.equal(frames.size, 0);
  } finally {
    delete globalThis.window; delete globalThis.requestAnimationFrame; delete globalThis.cancelAnimationFrame;
  }
});
