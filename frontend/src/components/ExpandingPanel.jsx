import { useEffect, useRef } from "react";
import { createSpring } from "../lib/motion.js";

export default function ExpandingPanel({ id, className, open, onSettled, children }) {
  const panel = useRef(null), content = useRef(null), motion = useRef(null);
  const target = useRef(-1), naturalHeight = useRef(1), notify = useRef(onSettled);
  notify.current = onSettled;
  useEffect(() => {
    const spring = createSpring(0, (height) => {
      panel.current.style.height = `${Math.max(0, height)}px`;
      panel.current.style.opacity = String(Math.min(1, Math.max(0, height / naturalHeight.current)));
    });
    motion.current = spring;
    return () => spring.stop();
  }, []);
  useEffect(() => {
    const resize = () => {
      naturalHeight.current = Math.max(1, content.current.getBoundingClientRect().height);
      const next = open ? naturalHeight.current : 0;
      if (target.current === next) return;
      target.current = next;
      panel.current.dataset.settled = 'false';
      motion.current.to(next, undefined, () => {
        panel.current.dataset.settled = String(open);
        notify.current(open);
      });
    };
    resize();
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize);
    observer?.observe(content.current);
    return () => observer?.disconnect();
  }, [open, children]);
  return <div ref={panel} id={id} className={`expanding-panel ${className} ${open ? 'open' : ''}`}
    inert={open ? undefined : ''} aria-hidden={!open}>
    <div ref={content} className="expanding-panel-content">{children}</div>
  </div>;
}
