import { useCallback, useEffect, useRef, useState } from "react";
import { cancelAutoScroll, scrollToElement } from "./scrolling.js";

/* 3D tilt — pure CSS transforms (same hook as the Abdullah City FC site). */
export function useTilt({ max = 9, scale = 1.03 } = {}) {
  const ref = useRef(null);
  const raf = useRef(0);

  const onMouseMove = useCallback(
    (e) => {
      const el = ref.current;
      if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width;
      const py = (e.clientY - r.top) / r.height;
      cancelAnimationFrame(raf.current);
      raf.current = requestAnimationFrame(() => {
        el.style.transition = "box-shadow .2s ease";
        el.style.transform = `perspective(1100px) rotateX(${(0.5 - py) * 2 * max}deg) rotateY(${(px - 0.5) * 2 * max}deg) scale(${scale})`;
        el.style.setProperty("--mx", `${px * 100}%`);
        el.style.setProperty("--my", `${py * 100}%`);
      });
    },
    [max, scale]
  );

  const onMouseLeave = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    cancelAnimationFrame(raf.current);
    el.style.transition = "transform .2s ease-out, box-shadow .2s ease";
    el.style.transform = "perspective(1100px) rotateX(0deg) rotateY(0deg) scale(1)";
  }, []);

  useEffect(() => () => cancelAnimationFrame(raf.current), []);
  return { ref, onMouseMove, onMouseLeave };
}

/* Fade-up on scroll for every .reveal element on the page. */
export function useRevealAll() {
  useEffect(() => {
    const reveal = (root) => {
      const elements = [...(root.matches?.('.reveal:not(.in)') ? [root] : []), ...root.querySelectorAll('.reveal:not(.in)')];
      elements.forEach((element) => observer ? observer.observe(element) : element.classList.add('in'));
    };
    const observer = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { entry.target.classList.add('in'); observer.unobserve(entry.target); }
      });
    }, { threshold: .05, rootMargin: '0px 0px 24px 0px' }) : null;
    const root = document.querySelector('main') ?? document.body;
    reveal(root);
    const mutations = new MutationObserver((entries) => entries.forEach((entry) => {
      entry.addedNodes.forEach((node) => { if (node.nodeType === 1) reveal(node); });
    }));
    mutations.observe(root, { childList: true, subtree: true });
    return () => { observer?.disconnect(); mutations.disconnect(); };
  }, []);
}

export function useMediaQuery(query) {
  const get = () => (typeof window !== "undefined" && window.matchMedia ? window.matchMedia(query).matches : false);
  const [match, setMatch] = useState(get);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setMatch(mq.matches);
    on();
    mq.addEventListener ? mq.addEventListener("change", on) : mq.addListener(on);
    return () => (mq.removeEventListener ? mq.removeEventListener("change", on) : mq.removeListener(on));
  }, [query]);
  return match;
}

/* Count a number up when `key` changes (used for OVR). */
export function useCountUp(target, { duration = 700 } = {}) {
  const [n, setN] = useState(target);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setN(target);
      return;
    }
    let id, start;
    const step = (t) => {
      if (!start) start = t;
      const p = Math.min((t - start) / duration, 1);
      setN(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) id = requestAnimationFrame(step);
    };
    setN(0);
    id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [target, duration]);
  return n;
}


export function useSectionScrolling() {
  useEffect(() => {
    const follow = (event) => {
      const link = event.target.closest?.('a[href^="#"]');
      if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target === '_blank' || link.hasAttribute('download')) return;
      let id;
      try { id = decodeURIComponent(link.hash.slice(1)); } catch { return; }
      const target = document.getElementById(id);
      if (!target) return;
      event.preventDefault();
      if (window.location.hash !== link.hash) window.history.pushState(null, '', link.hash);
      if (target.hasAttribute('tabindex')) target.focus({ preventScroll: true });
      scrollToElement(target, 'start');
    };
    document.addEventListener('click', follow);
    return () => { document.removeEventListener('click', follow); cancelAutoScroll(); };
  }, []);
}
