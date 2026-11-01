import { NAV, SITE } from "../content.js";
import { Mark } from "./ui.jsx";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="wrap">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 32, justifyContent: "space-between", alignItems: "flex-start" }}>
          <div className="brand display"><Mark size={34} /><span>SAC <span className="c1">Index</span></span></div>
          <nav className="mono t11 up" style={{ display: "grid", gridTemplateColumns: "repeat(2, auto)", gap: "12px 40px" }} aria-label="Footer">
            {NAV.map((n) => <a key={n.id} href={`#${n.id}`} className="mute">{n.label}</a>)}
          </nav>
        </div>
        <div className="footer-row mono t10 up">
          <span className="mute">{SITE.title} · {SITE.season}</span>
          <span className="dim">{SITE.org}</span>
          <a href="https://sac-utd-website.vercel.app/" target="_blank" rel="noopener noreferrer" className="sac-link">Visit SAC Website <span aria-hidden="true">↗</span><span className="sr-only"> (opens in a new tab)</span></a>
        </div>
      </div>
      <div className="wordmark display" aria-hidden="true">SAC</div>
    </footer>
  );
}
