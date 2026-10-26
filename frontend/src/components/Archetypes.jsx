import { ARCHETYPES, GROUPS, METRICS, TIER } from "../lib/archetypes.js";
import { useTilt } from "../lib/hooks.js";
import { SectionHead } from "./ui.jsx";

const METRIC_LABEL = { ...Object.fromEntries(METRICS.map((m) => [m.key, m.label])), REC: "Ball recoveries" };

function Arch({ a, position }) {
  const tilt = useTilt({ max: 6, scale: 1.03 });
  return (
    <div {...tilt} className="tilt sheen card-surface angular-sm arch">
      <span className="pos mono t9 up">{position}</span>
      <h4 className="display">{a.name}</h4>
      <div className="metric mono t10 up">Judged on · {METRIC_LABEL[a.metric]}</div>
      <p>{a.blurb}</p>
    </div>
  );
}

export default function Archetypes() {
  return (
    <section id="archetypes" className="section">
      <div className="wrap">
        <SectionHead
          eyebrow="Player styles"
          title="Archetypes"
          intro="Every player gets one primary archetype: the style where their percentile is highest for their position. The tier shows how far ahead of their peers they are."
        />

        <div className="legend reveal">
          <span className="chip angular-sm mono"><b>+</b> {TIER.plus}th percentile and up</span>
          <span className="chip angular-sm mono"><b>−</b> {TIER.minus}th to {TIER.plus}th</span>
          <span className="chip angular-sm mono"><b>Standard</b> below the {TIER.minus}th</span>
        </div>

        <div className="arch-groups">
          {GROUPS.map((g) => (
            <div key={g} className="arch-group reveal">
              <h3>{g}</h3>
              <div className="arch-grid">
                {["CB", "DM"].flatMap((pos) =>
                  ARCHETYPES[pos].filter((a) => a.group === g).map((a) => <Arch key={a.id} a={a} position={pos} />)
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="teams-only panel angular-sm reveal">
          <div className="mono t11 up c2" style={{ paddingTop: 3 }}>Teams only</div>
          <div>
            <h4 className="display">Off-ball dominance</h4>
            <p>
              Measured for teams, not players, because our spatial data is only available at team level. You'll find it
              in the Teams section below.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
