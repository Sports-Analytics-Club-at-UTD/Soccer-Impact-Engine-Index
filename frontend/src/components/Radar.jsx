import { METRICS } from "../lib/archetypes.js";

/* Hand-drawn SVG spider chart for T · I · C · P · LB (percentiles, 0–100). */
const CX = 160, CY = 150, R = 100;
const pt = (i, frac, n) => {
  const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
  return [CX + Math.cos(a) * R * frac, CY + Math.sin(a) * R * frac];
};

export default function Radar({ pct }) {
  const n = METRICS.length;
  const poly = (fr) => METRICS.map((_, i) => pt(i, fr, n).join(",")).join(" ");
  const shape = METRICS.map((m, i) => pt(i, Math.max(0.04, (pct[m.key] || 0) / 100), n).join(",")).join(" ");
  const summary = METRICS.map((m) => `${m.label} ${Math.round(pct[m.key] || 0)}`).join(", ");

  return (
    <div className="radar">
      <svg viewBox="0 0 320 300" role="img" aria-label={`Percentile profile: ${summary}`}>
        {[0.25, 0.5, 0.75, 1].map((f) => <polygon key={f} className="ring" points={poly(f)} />)}
        {METRICS.map((_, i) => {
          const [x, y] = pt(i, 1, n);
          return <line key={i} className="axis" x1={CX} y1={CY} x2={x} y2={y} />;
        })}
        <polygon key={shape} className="shape" points={shape} />
        {METRICS.map((m, i) => {
          const [x, y] = pt(i, Math.max(0.04, (pct[m.key] || 0) / 100), n);
          return <circle key={m.key} className="dot" cx={x} cy={y} r="3.4" />;
        })}
        {METRICS.map((m, i) => {
          const [x, y] = pt(i, 1.3, n);
          return (
            <g key={m.key}>
              <text className="lab" x={x} y={y + 4}>{m.key}</text>
              <text className="labv" x={x} y={y + 18}>{Math.round(pct[m.key] || 0)}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
