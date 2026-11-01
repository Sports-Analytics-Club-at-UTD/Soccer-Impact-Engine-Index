import { useEffect, useRef, useState } from "react";
import { NAV } from "../content.js";
import { IconClose, IconMenu, IconMoon, IconSun, Mark } from "./ui.jsx";

export default function Nav({ theme, onToggle, sections = NAV, activeSection, onNavigate }) {
  const [open, setOpen] = useState(false);
  const [solid, setSolid] = useState(false);
  const [active, setActive] = useState("home");
  const menuButton = useRef(null);

  useEffect(() => {
    const on = () => setSolid(window.scrollY > 40);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);

  useEffect(() => {
    if (activeSection !== undefined || !("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: "-45% 0px -50% 0px" }
    );
    sections.forEach((n) => {
      const el = document.getElementById(n.id);
      if (el) io.observe(el);
    });
    return () => io.disconnect();
  }, [sections, activeSection]);

  const light = theme === "light";
  const current = activeSection ?? active;
  function follow(id, event) { onNavigate?.(id, event); setOpen(false); }

  return (
    <header className={`nav ${solid || open ? "solid" : ""}`} onKeyDown={(e) => { if (e.key === 'Escape' && open) { setOpen(false); menuButton.current?.focus(); } }}>
      <div className="nav-in">
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

      {open && (
        <nav id="site-mobile-menu" aria-label="Mobile navigation" className="mobile-menu mono">
          {sections.map((n) => (
            <a key={n.id} href={n.href ?? `#${n.id}`} aria-current={current === n.id ? 'page' : undefined} onClick={(e) => follow(n.id, e)}>{n.label}</a>
          ))}
        </nav>
      )}
    </header>
  );
}
