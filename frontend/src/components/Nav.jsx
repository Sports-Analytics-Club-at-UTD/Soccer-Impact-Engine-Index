import { useEffect, useRef, useState } from "react";
import { activeSectionAt } from "../lib/scrolling.js";
import { NAV } from "../content.js";
import { IconClose, IconMenu, IconMoon, IconSun, Mark } from "./ui.jsx";

export default function Nav({ theme, onToggle, sections = NAV, activeSection, onNavigate }) {
  const [open, setOpen] = useState(false);
  const [solid, setSolid] = useState(false);
  const [active, setActive] = useState("home");
  const menuButton = useRef(null), headerContent = useRef(null), currentSection = useRef("home");

  useEffect(() => {
    const on = () => setSolid(window.scrollY > 40);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);

  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const height = headerContent.current.getBoundingClientRect().height;
      if (document.documentElement.style.getPropertyValue('--nav-height') !== `${height}px`) document.documentElement.style.setProperty('--nav-height', `${height}px`);
      if (activeSection !== undefined) return;
      const positions = sections.map((section) => {
        const element = document.getElementById(section.id);
        return element ? { id: section.id, top: element.getBoundingClientRect().top } : null;
      }).filter(Boolean);
      const next = activeSectionAt(positions, height + Math.min(120, window.innerHeight * .2), currentSection.current);
      if (next !== currentSection.current) { currentSection.current = next; setActive(next); }
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(schedule);
    observer?.observe(headerContent.current);
    return () => {
      cancelAnimationFrame(frame); observer?.disconnect();
      window.removeEventListener('scroll', schedule); window.removeEventListener('resize', schedule);
      document.documentElement.style.removeProperty('--nav-height');
    };
  }, [sections, activeSection]);

  const light = theme === "light";
  const current = activeSection ?? active;
  function follow(id, event) { onNavigate?.(id, event); setOpen(false); }

  return (
    <header className={`nav ${solid || open ? "solid" : ""}`} onKeyDown={(e) => { if (e.key === 'Escape' && open) { setOpen(false); menuButton.current?.focus(); } }}>
      <div ref={headerContent} className="nav-in">
        <a href={sections.find((s) => s.id === 'home')?.href ?? '#home'} onClick={(e) => follow('home', e)} className="brand display" aria-label="Home">
          <Mark />
          <span>SAC <span className="c1">Index</span></span>
        </a>

        <nav className="nav-links mono" aria-label={activeSection === undefined ? 'Sections' : 'Main navigation'}>
          {sections.map((n) => (
            <a key={n.id} href={n.href ?? `#${n.id}`} onClick={(e) => follow(n.id, e)} aria-current={current === n.id ? 'page' : undefined} className={current === n.id ? "active" : ""}>{n.label}</a>
          ))}
        </nav>

        <div className="nav-right">
          <button
            type="button" role="switch" aria-checked={light} aria-label="Light mode"
            className="switch" onClick={onToggle}
          >
            <IconMoon className="moon" />
            <IconSun className="sun" />
            <span className="knob" />
          </button>
          <button ref={menuButton} type="button" className="burger" aria-label="Menu" aria-controls="site-mobile-menu" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? <IconClose size={22} /> : <IconMenu size={22} />}
          </button>
        </div>
      </div>

      <div className={`mobile-menu-wrap ${open ? "open" : ""}`} inert={open ? undefined : ""} aria-hidden={!open}>
        <nav id="site-mobile-menu" aria-label="Mobile navigation" className="mobile-menu mono">
          {sections.map((n) => (
            <a key={n.id} href={n.href ?? `#${n.id}`} aria-current={current === n.id ? 'page' : undefined} onClick={(e) => follow(n.id, e)}>{n.label}</a>
          ))}
        </nav>
      </div>
    </header>
  );
}
