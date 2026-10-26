import { useEffect, useState } from "react";
import About from "./components/About.jsx";
import Archetypes from "./components/Archetypes.jsx";
import Description from "./components/Description.jsx";
import Footer from "./components/Footer.jsx";
import Hero from "./components/Hero.jsx";
import Nav from "./components/Nav.jsx";
import Search from "./components/Search.jsx";
import Teams from "./components/Teams.jsx";
import { useRevealAll } from "./lib/hooks.js";

export default function App() {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute("data-theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("sac-theme", theme); } catch (e) { /* private mode: fine */ }
  }, [theme]);

  useRevealAll();

  return (
    <>
      <Nav theme={theme} onToggle={() => setTheme(theme === "dark" ? "light" : "dark")} />
      <main>
        <p className="wrap mono" role="note">Demo mode: fictional players with illustrative percentiles, OVR and archetypes. No production scorecard is connected.</p>
        <Hero />
        <Description />
        <Archetypes />
        <Search />
        <Teams />
        <About />
      </main>
      <Footer />
    </>
  );
}
