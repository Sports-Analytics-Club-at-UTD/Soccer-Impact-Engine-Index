import { METRICS, percentileValue } from "../lib/archetypes.js";
import { scoreLabel } from "../lib/ratingCard.js";

/* A missing axis has a label but no point. Incomplete profiles have no polygon. */
const CX = 160, CY = 150, R = 100;
const pt = (i, frac, n) => {
  const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
  return [CX + Math.cos(a) * R * frac, CY + Math.sin(a) * R * frac];
};

export default function Radar({ attributes = METRICS.map((m) => ({ ...m, value: null })), label = "FIFA-style rating profile" }) {
  const n = attributes.length;
  const poly = (fr) => attributes.map((_, i) => pt(i, fr, n).join(",")).join(" ");
  const values = attributes.map((m) => percentileValue(m.value));
  const complete = values.every((v) => v !== null);
  const shape = complete ? values.map((v, i) => pt(i, v / 100, n).join(",")).join(" ") : null;
  const summary = attributes.map((m, i) => `${m.label} ${scoreLabel(values[i])}`).join(", ");

  return (
    <div className="radar">
      <svg viewBox="0 0 320 300" role="img" aria-label={`${label}: ${summary}`}>
        {[0.25, 0.5, 0.75, 1].map((f) => <polygon key={f} className="ring" points={poly(f)} />)}
        {attributes.map((m, i) => {
          const [x, y] = pt(i, 1, n);
          return <line key={m.key} className="axis" x1={CX} y1={CY} x2={x} y2={y} />;
        })}
        {complete && <polygon key={shape} className="shape" points={shape} />}
        {attributes.map((m, i) => {
          if (values[i] === null) return null;
          const [x, y] = pt(i, values[i] / 100, n);
          return <circle key={m.key} className="dot" cx={x} cy={y} r="3.4" />;
        })}
        {attributes.map((m, i) => {
          const [x, y] = pt(i, 1.3, n);
          return (
            <g key={m.key}>
              <text className="lab" x={x} y={y + 4}>{m.key}</text>
              <text className="labv" x={x} y={y + 18}>{scoreLabel(values[i])}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
