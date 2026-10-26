import { useEffect, useState } from "react";
import { NAV } from "../content.js";
import { IconClose, IconMenu, IconMoon, IconSun, Mark } from "./ui.jsx";

export default function Nav({ theme, onToggle, sections = NAV }) {
  const [open, setOpen] = useState(false);
  const [solid, setSolid] = useState(false);
  const [active, setActive] = useState("home");

  useEffect(() => {
    const on = () => setSolid(window.scrollY > 40);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);

  useEffect(() => {
    if (!("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: "-45% 0px -50% 0px" }
    );
    sections.forEach((n) => {
      const el = document.getElementById(n.id);
      if (el) io.observe(el);
    });
    return () => io.disconnect();
  }, [sections]);

  const light = theme === "light";

  return (
    <header className={`nav ${solid || open ? "solid" : ""}`}>
      <div className="nav-in">
        <a href="#home" className="brand display" aria-label="Home">
          <Mark />
          <span>SAC <span className="c1">Index</span></span>
        </a>

        <nav className="nav-links mono" aria-label="Sections">
          {sections.map((n) => (
            <a key={n.id} href={`#${n.id}`} className={active === n.id ? "active" : ""}>{n.label}</a>
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
          <button type="button" className="burger" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? <IconClose size={22} /> : <IconMenu size={22} />}
          </button>
        </div>
      </div>

      {open && (
        <div className="mobile-menu mono">
          {sections.map((n) => (
            <a key={n.id} href={`#${n.id}`} onClick={() => setOpen(false)}>{n.label}</a>
          ))}
        </div>
      )}
    </header>
  );
}
