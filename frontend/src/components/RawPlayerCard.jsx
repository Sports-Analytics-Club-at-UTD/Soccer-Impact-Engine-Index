import { rawCardModel } from "../lib/rawScorecardView.js";
import { IconClose } from "./ui.jsx";

function Measurements({ rows }) {
  return <dl className="raw-measurements">
    {rows.map((metric) => <div className="stat" key={metric.field}>
      <dt>{metric.label}</dt><dd className="mono">{metric.text}</dd>
    </div>)}
  </dl>;
}

export default function RawPlayerCard({ player, metadata, onClose }) {
  const card = rawCardModel(player, metadata);
  return <article className="card-surface on angular pcard raw-player-card" aria-label={`${card.name} raw metric profile`}>
    <button className="close" type="button" onClick={onClose} aria-label="Close player profile"><IconClose size={16} /></button>
    <div className="mono t10 up c2">{card.position} · Raw measurements</div>
    <h3 className="display">{card.name}</h3>
    <p className="team">{card.context}</p>
    <p className="mono">Player ID: {card.player_id}</p>
    <Measurements rows={card.descriptors} />

    <section className="raw-metric-group" aria-label="Defensive recovery">
      <h4 className="display">Defensive recovery</h4>
      {card.recovery.map((component) => <section key={component.prefix} className="raw-component" aria-label={component.label}>
        <h5>{component.label}</h5>
        <p className="raw-note">{component.availability}</p>
        <Measurements rows={component.metrics} />
        <p className="raw-note">Rate status: {component.status} · Source minutes: {component.exposure}</p>
      </section>)}
    </section>

    <section className="raw-metric-group" aria-label="Press resistance">
      <h4 className="display">Press resistance</h4>
      <p className="raw-note">{card.press.availability}</p>
      <Measurements rows={card.press.metrics} />
      <p className="raw-note">Source minutes: {card.press.exposure}. These are completion percentages, not percentile ranks. N/A percentages have no available rate; no value is inferred.</p>
    </section>

    <section className="raw-metric-group" aria-label={card.passing.title}>
      <h4 className="display">{card.passing.title}</h4>
      <p className="raw-note">{card.passing.availability}</p>
      <Measurements rows={card.passing.metrics} />
      <p className="raw-note">Rate status: {card.passing.status} · Source minutes: {card.passing.exposure}. An unavailable attempt denominator leaves completion percentage N/A.</p>
      <p className="raw-note">Pass value uses difficulty-weighted distance in the source yards convention; per90 value retains those units. It is not expected goals or a player rating. Level A does not measure verified 360-based opponents bypassed.</p>
      <p className="raw-note">Calibration scope: {card.passing.scope}</p>
      <p className="raw-note">{card.passing.declaration}</p>
    </section>

    <div className="warn mono angular-sm" role="note">
      Coverage: {card.coverage}.
      <ul>{card.limitations.map((text) => <li key={text}>{text}</li>)}</ul>
    </div>
  </article>;
}
