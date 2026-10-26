import About from "./About.jsx";
import Archetypes from "./Archetypes.jsx";
import Description from "./Description.jsx";
import Footer from "./Footer.jsx";
import Hero from "./Hero.jsx";
import Nav from "./Nav.jsx";
import Search from "./Search.jsx";
import Teams from "./Teams.jsx";
import { useRevealAll } from "../lib/hooks.js";

export default function DemoExperience({ theme, onToggle }) {
  useRevealAll();
  return <>
    <Nav theme={theme} onToggle={onToggle} />
    <main>
      <p className="wrap mono mode-notice" role="note">Demo data — fictional players and illustrative ratings.</p>
      <Hero /><Description /><Archetypes /><Search /><Teams /><About />
    </main>
    <Footer />
  </>;
}
