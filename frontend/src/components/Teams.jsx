import { useState } from "react";
import { TEAMS, TEAMS_SECTION } from "../content.js";
import { useTilt } from "../lib/hooks.js";
import { IconDown, Photo, SectionHead } from "./ui.jsx";

function Badge({ t, open, onToggle }) {
  const tilt = useTilt({ max: 7, scale: 1.03 });
  return (
    <div className="reveal">
      <button
        type="button" {...tilt} onClick={onToggle} aria-expanded={open} aria-controls={`team-${t.id}`}
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
        <div id={team ? `team-${team.id}` : undefined} className={`team-panel ${team ? "open" : ""}`} aria-live="polite">
          <div>
            {team && (
              <div className="team-inner">
                <h3 className="display" style={{ fontSize: "1.6rem" }}>{team.name}</h3>
                <p className="note" style={{ marginTop: 12 }}>{team.note}</p>
                <div className="slots">
                  {team.images.map((im) => (
                    <figure key={im.label} className="slot" style={{ margin: 0 }}>
                      <Photo src={im.src} label={`${im.label} · image`} />
                      <figcaption className="mono t10 up">
                        <b>{im.label}</b>{im.caption}
                      </figcaption>
                    </figure>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
