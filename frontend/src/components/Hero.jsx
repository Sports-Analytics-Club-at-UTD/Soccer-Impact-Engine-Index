import { useEffect, useState } from "react";
import { HERO, SITE } from "../content.js";
import { IconArrow } from "./ui.jsx";

/* Title lines are split here so they stack nicely; edit freely. */
const LINES = [
  { text: "SAC", accent: true },
  { text: "Midfielder/" },
  { text: "Defender Index" },
];

const TICKER = [
  `${SITE.season} season`,
  "Centre-backs · Defensive midfielders",
  "Percentiles vs positional peers",
  "5 metrics · 1 primary archetype",
  "Spatial data: team level only",
  SITE.org,
];

function PitchLoop() {
  return (
    <svg className="pitch-svg" viewBox="0 0 1200 700" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect className="ln" x="60" y="60" width="1080" height="580" />
      <path className="ln" d="M600 60v580" />
      <circle className="ln" cx="600" cy="350" r="90" />
      <rect className="ln" x="60" y="190" width="170" height="320" />
      <rect className="ln" x="970" y="190" width="170" height="320" />
      <rect className="ln" x="60" y="268" width="62" height="164" />
      <rect className="ln" x="1078" y="268" width="62" height="164" />
      <circle className="press" cx="520" cy="250" r="90" />
      <circle className="press b" cx="520" cy="250" r="90" />
      <circle className="ball" cx="0" cy="0" r="7" />
    </svg>
  );
}

export default function Hero() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setReady(true), 60);
    return () => clearTimeout(t);
  }, []);

  return (
    <section id="home" className="hero">
      {/* ── BACKGROUND: your football clips ───────────────────────────────
          Set HERO.videoSrc in content.js (file in /public, e.g. "/clips/hero.mp4").
          Until then the animated pitch below shows.                       */}
      <div className="hero-bg">
        {HERO.videoSrc ? (
          <video autoPlay muted loop playsInline poster={HERO.poster || undefined}>
            <source src={HERO.videoSrc} type="video/mp4" />
          </video>
        ) : (
          <>
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(150deg,var(--bg-2),var(--bg))" }} />
            <PitchLoop />
          </>
        )}
      </div>
      <div className="hero-glow" />
      <div className="grain" />
      <div className="hero-fade" />
      {!HERO.videoSrc && <div className="video-note mono t10 up">Hero clip placeholder · 1920×1080 · MP4</div>}

      <div className="wrap hero-in">
        <div className={`fade-in ${ready ? "" : "pre"}`}>
          <div className="eyebrow">{SITE.season} · CB · DM</div>
        </div>

        <h1 className="display hero-title">
          {LINES.map((l, i) => (
            <span key={i} className="line">
              <span
                className={ready ? "" : "pre"}
                style={{ transitionDelay: `${0.12 + i * 0.11}s`, color: l.accent ? "var(--a1)" : undefined }}
              >
                {l.text}
              </span>
            </span>
          ))}
        </h1>

        <div className={`hero-sub mono fade-in ${ready ? "" : "pre"}`}>{HERO.subtitle}</div>

        <div className={`hero-foot fade-in ${ready ? "" : "pre"}`}>
          <p>{HERO.tagline}</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            <a href="#search" className="btn btn-solid">{HERO.cta} <IconArrow /></a>
            <a href="#description" className="btn btn-ghost">How it works</a>
          </div>
        </div>
      </div>

      <div className="ticker">
        <div className="ticker-row">
          <div className="ticker-live">
            <span className="pulse-dot" />
            <span className="mono t10 up dim">Index</span>
          </div>
          <div className="ticker-view">
            <div className="ticker-track">
              {[...TICKER, ...TICKER].map((t, i) => (
                <span key={i} className="mono t10 up dim">
                  {t}<span className="c2" style={{ marginLeft: 56 }}>/</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
