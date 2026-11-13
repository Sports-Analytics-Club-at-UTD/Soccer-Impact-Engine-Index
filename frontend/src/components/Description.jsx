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
        <details className="card-detail panel angular-sm" style={{ marginTop: 28, padding: 20 }}>
          <summary>More about the ratings</summary>
          <p>The five skills are tackles, interceptions, ball recoveries, press resistance and progressive passing. Ratings use fixed 2015/16 comparison groups, separately for centre-backs (CB) and midfielders (MID), so new profiles do not change existing ratings. Ball-winning actions and progressive passes are measured per 90 confirmed minutes, including stoppage time. Press resistance measures pass and dribble completion under pressure. Progressive passing measures forward progress; it does not establish how many opponents a pass bypassed.</p>
          <p>A skill rating is 65 at the group average, with 10 points added or subtracted for each step equal to the group's typical spread. Ratings range from 1 to 99; a 90th percentile performance is in the group's top 10%. The overall score requires all five ratings and weights them from strongest to weakest at 30%, 25%, 20%, 15% and 10%.</p>
          <p>Rankings require at least 900 confirmed minutes for each skill measured per 90 minutes and at least 40 supported actions under pressure. Unsupported observations are excluded from the affected skill, while a player’s other verified matches remain usable. Pressure resistance uses an action ratio, so it can include verified actions when a match’s final duration is unknown. These minimums are project rules and do not establish statistical certainty. Midfielders and centre-backs use separate rebuilt comparison groups; ratings are not directly comparable with the earlier release. Confirmed minutes and rankings do not guarantee a complete season record. Bundesliga coverage remains too uneven for ranking, though available ratings remain visible.</p>
        </details>
      </div>
    </section>
  );
}
