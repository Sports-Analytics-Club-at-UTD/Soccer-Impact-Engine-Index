import { DESCRIPTION, SITE } from "../content.js";
import { useTilt } from "../lib/hooks.js";
import { SectionHead } from "./ui.jsx";

function Point({ p, i }) {
  const tilt = useTilt({ max: 6, scale: 1.02 });
  return (
    <div className="reveal" style={{ transitionDelay: `${i * 80}ms` }}>
      <div {...tilt} className="tilt sheen panel angular point">
        <div className="tag mono t10 up">0{i + 1}</div>
        <h3 className="display">{p.label}</h3>
        <p>{p.body}</p>
      </div>
    </div>
  );
}

export default function Description() {
  return (
    <section id="description" className="section">
      <div className="ghost display" aria-hidden="true">{SITE.season}</div>
      <div className="wrap" style={{ position: "relative" }}>
        <SectionHead eyebrow={DESCRIPTION.eyebrow} title={DESCRIPTION.title} intro={DESCRIPTION.intro} />
        <div className="points">
          {DESCRIPTION.points.map((p, i) => <Point key={p.label} p={p} i={i} />)}
        </div>
      </div>
    </section>
  );
}
