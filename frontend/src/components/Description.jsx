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
          <p>The five skills are tackles, interceptions, ball recoveries, press resistance and progressive passing. Each compares recorded performances with a fixed 2015/16 comparison group, separately for centre-backs and midfielders. These original groups remain fixed, so adding a profile does not move everyone else’s rating.</p>
          <p>A skill rating starts at 65 for the comparison group’s average. A step equal to the group’s typical spread of performances (its standard deviation) adds or subtracts 10 points. Ratings stay between 1 and 99. A percentile of 90 places that performance among the top 10% of its comparison group.</p>
          <p>Ball-winning actions and progressive passes are measured per 90 confirmed minutes, including recorded stoppage time. Press resistance is the share of passes and dribbles completed under pressure. Progressive passing describes forward progress towards goal; it does not establish how many opponents a pass bypassed.</p>
          <p>The overall rating weights the strongest skill at 30%, followed by 25%, 20%, 15% and 10%. All five skills must have a rating for an overall score to be shown.</p>
          <p>Rankings require at least 900 confirmed minutes and complete evidence across the recorded matches for all five skills. The press resistance comparison group also requires at least 40 supported actions under pressure. Players must belong to all five original comparison groups; reaching the minute and action thresholds alone does not guarantee eligibility. Bundesliga coverage is too uneven for ranking, although available ratings can still be viewed.</p>
          <p>Recorded matches may include appearances whose duration could not be confirmed. Each skill uses only the matches with enough reliable evidence. Confirmed minutes describe supported observed appearances, rather than a complete historical season total. Neither a rating nor inclusion in the rankings guarantees a complete season record.</p>
        </details>
      </div>
    </section>
  );
}
