// Exact critically damped step: retargeting preserves position and velocity.
export function springStep(position, velocity, target, seconds) {
  const omega = 2 * Math.PI / 0.35;
  const offset = position - target;
  const c = velocity + omega * offset;
  const decay = Math.exp(-omega * seconds);
  return { position: target + (offset + c * seconds) * decay,
    velocity: (velocity - omega * c * seconds) * decay };
}

export function createSpring(initial, update) {
  let position = initial, velocity = 0, frame = 0, last = 0;
  const stop = () => { cancelAnimationFrame(frame); frame = 0; };
  return {
    get position() { return position; },
    stop,
    set(value) { stop(); position = value; velocity = 0; update(position); },
    to(target, releaseVelocity = velocity, settled = () => {}) {
      stop(); velocity = releaseVelocity; last = 0;
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || (Math.abs(position - target) < .1 && Math.abs(velocity) < .5)) {
        position = target; velocity = 0; update(position); settled(); return;
      }
      const tick = (time) => {
        const step = springStep(position, velocity, target, last ? Math.min((time - last) / 1000, .064) : 1 / 60);
        last = time; position = step.position; velocity = step.velocity;
        if (Math.abs(position - target) < .1 && Math.abs(velocity) < .5) {
          position = target; velocity = 0; frame = 0; update(position); settled();
        } else { update(position); frame = requestAnimationFrame(tick); }
      };
      frame = requestAnimationFrame(tick);
    },
  };
}

export function sheetDestination(position, velocity, height) {
  const projected = position + velocity / 1000 * .998 / (1 - .998);
  return projected > height * .4 ? height : 0;
}

export function rubberband(distance, dimension) {
  return distance * dimension * .55 / (dimension + .55 * Math.abs(distance));
}
