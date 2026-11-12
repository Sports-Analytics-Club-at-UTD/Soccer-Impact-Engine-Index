import { useEffect, useId, useRef, useState } from 'react';
import { SPATIAL_DOMINANCE, SPATIAL_ZONES, spatialColor, spatialLabelColor } from '../lib/spatialDominance.js';
import './spatialDominance.css';

export default function SpatialDominancePitch({ team }) {
  const data = SPATIAL_DOMINANCE[team.id];
  const id = useId();
  const pitch = useRef(null);
  const [hovered, setHovered] = useState(null);
  const [focused, setFocused] = useState(null);
  const [selected, setSelected] = useState(null);
  const active = hovered ?? focused ?? selected;
  const zone = active === null ? null : SPATIAL_ZONES[active];

  useEffect(() => {
    const dismiss = (event) => {
      if (!pitch.current?.contains(event.target)) setSelected(null);
    };
    document.addEventListener('pointerdown', dismiss);
    return () => document.removeEventListener('pointerdown', dismiss);
  }, []);

  function onKeyDown(event) {
    if (event.key === 'Escape') {
      setHovered(null); setFocused(null); setSelected(null);
      event.stopPropagation();
    }
    const index = Number(event.target.dataset.zone);
    if (!Number.isInteger(index)) return;
    const offsets = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -3, ArrowDown: 3 };
    if (event.key in offsets) {
      event.preventDefault();
      const next = (index + offsets[event.key] + 9) % 9;
      pitch.current.querySelector(`[data-zone="${next}"]`).focus();
    }
  }

  return <figure className="spatial-figure" aria-labelledby={`${id}-title`}>
    <figcaption className="spatial-heading">
      <h4 id={`${id}-title`} className="mono">Off-ball spatial dominance</h4>
      <span>{data.matches} matches with 360 data</span>
    </figcaption>
    <div ref={pitch} className="spatial-pitch" role="group" aria-label={`${team.name} spatial zones; attack from left to right`} onKeyDown={onKeyDown} onPointerLeave={() => setHovered(null)}>
      <div className="spatial-zones">
        {SPATIAL_ZONES.map((item, index) => <button key={item.id} type="button" data-zone={index}
          className={`spatial-zone${active === index ? ' is-active' : ''}`}
          style={{ backgroundColor: spatialColor(data.percentages[index]), color: spatialLabelColor(data.percentages[index]) }}
          aria-label={`${item.name}: ${data.percentages[index]}%`}
          aria-describedby={active === index ? `${id}-tooltip` : undefined}
          aria-pressed={selected === index}
          onPointerEnter={(event) => { if (event.pointerType !== 'touch') setHovered(index); }}
          onFocus={() => setFocused(index)} onBlur={() => setFocused(null)}
          onClick={() => { setSelected(selected === index ? null : index); setFocused(null); setHovered(null); }}>
          <span>{data.percentages[index]}%</span>
        </button>)}
      </div>
      <svg className="spatial-markings" viewBox="0 0 120 60" aria-hidden="true">
        <rect x="0.3" y="0.3" width="119.4" height="59.4" />
        <path d="M60 0V60 M0 12H18V48H0 M120 12H102V48H120 M0 22H6V38H0 M120 22H114V38H120" />
        <circle cx="60" cy="30" r="8" />
        <circle cx="60" cy="30" r="0.5" />
      </svg>
      {zone && <div id={`${id}-tooltip`} role="tooltip" className={`spatial-tooltip spatial-tooltip-col-${zone.column} spatial-tooltip-row-${zone.row}`}>
        <strong>{zone.name} · {data.percentages[active]}%</strong>
        <p>Share of observed cells in this zone nearest to {team.short}’s defenders during opponent possession. Not pitch control, defensive effectiveness or a possession-win probability.</p>
        <small>Original chart value, rounded to a whole percent.</small>
      </div>}
    </div>
    <div className="spatial-direction mono"><span>Direction of attack</span><svg viewBox="0 0 100 8" aria-hidden="true"><path d="M0 4H98M94 1L98 4L94 7" /></svg></div>
    <div className="spatial-legend" aria-label="Color scale: 0 to 100 percent defender-nearest share">
      <span>0%</span><span className="spatial-ramp" /><span>100%</span><span>Defender-nearest share</span>
    </div>
    <p className="spatial-methodology">Share of observed spatial cells nearest to the team’s defenders during opponent possession, from event-triggered 360 frames. This describes positioning, not true pitch control, defensive effectiveness or the probability of winning possession. Values and match counts are transcribed from the original charts; unrounded data, season and fixture lists are unavailable.</p>
  </figure>;
}
