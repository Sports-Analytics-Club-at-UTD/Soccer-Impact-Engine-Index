import { useEffect, useState } from "react";
import About from "./About.jsx";
import Archetypes from "./Archetypes.jsx";
import Description from "./Description.jsx";
import Footer from "./Footer.jsx";
import Hero from "./Hero.jsx";
import Nav from "./Nav.jsx";
import Search from "./Search.jsx";
import Teams from "./Teams.jsx";
import { useRevealAll } from "../lib/hooks.js";
import { loadPublicRatings } from "../lib/publicRatingsDelivery.js";
import { foundationPlayers } from "../lib/foundationPlayers.js";

export default function DemoExperience({ theme, onToggle }) {
  const [players, setPlayers] = useState([]), [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false), [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setPlayers([]); setError(""); setLoaded(false);
    loadPublicRatings({ signal: controller.signal }).then((data) => {
      if (!controller.signal.aborted) { setPlayers(foundationPlayers(data)); setLoaded(true); }
    }).catch((e) => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [retry]);
  useRevealAll();
  return <>
    <Nav theme={theme} onToggle={onToggle} />
    <main>
      <Hero /><Description /><Archetypes players={players} loaded={loaded} error={error} onRetry={() => setRetry((n) => n + 1)} /><Search players={players} loaded={loaded} error={error} onRetry={() => setRetry((n) => n + 1)} /><Teams /><About />
    </main>
    <Footer />
  </>;
}
