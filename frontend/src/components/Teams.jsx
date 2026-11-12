import { useState } from "react";
import { TEAMS, TEAMS_SECTION } from "../content.js";
import { useTilt } from "../lib/hooks.js";
import { IconDown, SectionHead } from "./ui.jsx";
import SpatialDominancePitch from "./SpatialDominancePitch.jsx";

function Badge({ t, open, onToggle }) {
  const tilt = useTilt({ max: 7, scale: 1.03 });
  return (
    <div className="reveal">
      <button
        type="button" {...tilt} onClick={onToggle} aria-expanded={open} aria-controls="team-spatial-panel"
        className="tilt sheen card-surface angular-sm badge"
      >
        <span className="mk display">{t.short.slice(0, 3).toUpperCase()}</span>
        <span>
          <h3 className="display">{t.short}</h3>
          <div className="nm">{t.name}</div>
        </span>
        <IconDown className="chev" size={20} />
      </button>
    </div>
  );
}

export default function Teams() {
  const [openId, setOpenId] = useState(null);
  const team = TEAMS.find((t) => t.id === openId);

  return (
    <section id="teams" className="section">
      <div className="wrap">
        <SectionHead eyebrow={TEAMS_SECTION.eyebrow} title={TEAMS_SECTION.title} intro={TEAMS_SECTION.intro} />

        <div className="badges">
          {TEAMS.map((t) => (
            <Badge key={t.id} t={t} open={openId === t.id} onToggle={() => setOpenId(openId === t.id ? null : t.id)} />
          ))}
        </div>

        {/* one panel, content swaps with the selected team */}
        <div id="team-spatial-panel" className={`team-panel ${team ? "open" : ""}`}>
          <div>
            {team && (
              <div className="team-inner">
                <h3 className="display" style={{ fontSize: "1.6rem" }}>{team.name}</h3>
                <SpatialDominancePitch key={team.id} team={team} />
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
