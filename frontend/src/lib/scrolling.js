import { springStep } from './motion.js';

let active = null;

export function cancelAutoScroll() {
  active?.stop();
}

export function scrollToElement(element, align = 'nearest') {
  if (!element) return;
  let velocity = active?.velocity ?? 0, last = 0, frame = 0;
  cancelAutoScroll();
  const keys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'PageUp', 'PageDown', 'Home', 'End', ' ', 'Tab', 'Escape'];
  const interruptKey = (event) => { if (keys.includes(event.key)) stop(); };
  const stop = () => {
    cancelAnimationFrame(frame);
    for (const type of ['wheel', 'touchstart', 'pointerdown']) window.removeEventListener(type, stop);
    window.removeEventListener('keydown', interruptKey);
    if (active?.stop === stop) active = null;
  };
  const destination = () => {
    const bounds = element.getBoundingClientRect();
    const edge = (document.querySelector('.nav-in')?.getBoundingClientRect().height ?? 0) + 16;
    let delta = 0;
    if (align === 'start' || bounds.top < edge || bounds.height > window.innerHeight - edge - 16) delta = bounds.top - edge;
    else if (bounds.bottom > window.innerHeight - 16) delta = bounds.bottom - window.innerHeight + 16;
    return Math.max(0, Math.min(window.scrollY + delta, document.documentElement.scrollHeight - window.innerHeight));
  };
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.scrollTo({ top: destination(), behavior: 'instant' });
    return;
  }
  active = { stop, velocity };
  for (const type of ['wheel', 'touchstart', 'pointerdown']) window.addEventListener(type, stop, { passive: true });
  window.addEventListener('keydown', interruptKey);
  const tick = (time) => {
    if (!element.isConnected) { stop(); return; }
    const target = destination(), current = window.scrollY;
    const next = springStep(current, velocity, target, last ? Math.min((time - last) / 1000, .064) : 1 / 60);
    last = time; velocity = next.velocity; active.velocity = velocity;
    window.scrollTo({ top: Math.max(0, next.position), behavior: 'instant' });
    const expanding = element.closest('.expanding-panel')?.dataset.settled === 'false';
    if (!expanding && Math.abs(window.scrollY - target) < 1 && Math.abs(velocity) < 5) {
      window.scrollTo({ top: target, behavior: 'instant' }); stop();
    } else frame = requestAnimationFrame(tick);
  };
  frame = requestAnimationFrame(tick);
}

export function activeSectionAt(sections, edge, currentId) {
  let candidate = 0;
  sections.forEach((section, index) => { if (section.top <= edge) candidate = index; });
  const current = sections.findIndex((section) => section.id === currentId);
  if (current >= 0 && candidate > current && sections[candidate].top > edge - 12) return currentId;
  if (current >= 0 && candidate < current && sections[current].top <= edge + 12) return currentId;
  return sections[candidate]?.id ?? currentId;
}
