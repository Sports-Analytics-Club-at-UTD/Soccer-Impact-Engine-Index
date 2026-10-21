import { ABOUT } from "../content.js";
import { useTilt } from "../lib/hooks.js";
import { Photo, SectionHead } from "./ui.jsx";

function Member({ m, i }) {
  const tilt = useTilt({ max: 8, scale: 1.04 });
  return (
    <div className="reveal" style={{ transitionDelay: `${i * 70}ms` }}>
      <div {...tilt} className="tilt sheen card-surface angular member">
        <Photo src={m.photo} label="Team photo" />
        <h3 className="display">{m.name}</h3>
        <div className="role mono t10 up">{m.role}</div>
        <p>{m.does}</p>
      </div>
    </div>
  );
}

export default function About() {
  return (
    <section id="about" className="section">
      <div className="wrap">
        <SectionHead eyebrow={ABOUT.eyebrow} title={ABOUT.title} intro={ABOUT.intro} />
        <div className="members">
          {ABOUT.members.map((m, i) => <Member key={m.name} m={m} i={i} />)}
        </div>
      </div>
    </section>
  );
}
