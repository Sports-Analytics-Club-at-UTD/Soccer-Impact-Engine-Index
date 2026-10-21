import { METRICS } from "../lib/archetypes.js";
import { MIN_MINUTES } from "../lib/data.js";
import { useCountUp, useTilt } from "../lib/hooks.js";
import Radar from "./Radar.jsx";
import { IconClose, Photo } from "./ui.jsx";

export default function PlayerCard({ player, onClose }) {
  const tilt = useTilt({ max: 4, scale: 1.01 });
  const ovr = useCountUp(player.ovr);
  const a = player.archetype;
  const low = player.minutes < MIN_MINUTES;

  return (
    <article {...tilt} className="tilt sheen card-surface on angular pcard" key={player.id} aria-label={`${player.name} player card`}>
      <span className="ghost-ovr display" aria-hidden="true">{player.ovr}</span>
      <button type="button" className="close" onClick={onClose} aria-label="Close player card"><IconClose size={16} /></button>

      <div className="pcard-top">
        <Photo src={player.photo} label="FIFA 16 photo" className="lg" />
        <div>
          <div className="mono t10 up c2">{player.position === "CB" ? "Centre-back" : "Defensive midfielder"}</div>
          <h3 className="display" style={{ marginTop: 10 }}>{player.name}</h3>
          <div className="team">{player.team}</div>

          <div className="ovr-block">
            <div className="ovr-num display" aria-label={`Overall ${player.ovr}`}>{ovr}</div>
            <div className="mono t10 up mute" style={{ paddingBottom: 6 }}>OVR</div>
          </div>

          <div className={`arch-badge angular-sm ${a.tier ? "" : "std"}`}>
            <span className="tier mono">{a.tier || "·"}</span>
            <span>
              <span className="mono t9 up dim" style={{ display: "block" }}>Archetype</span>
              <span className="display" style={{ fontSize: "1rem", lineHeight: 1.1 }}>{a.name}</span>
            </span>
          </div>
        </div>
      </div>

      <div className="viz">
        <Radar pct={player.pct} />
        <div className="stat-grid">
          {METRICS.map((m) => (
            <div className="stat" key={m.key}>
              <div className="top">
                <span className="k"><b className="mono t11">{m.key}</b><span className="mono t10 up mute">{m.label}</span></span>
                <span className="mono t11">{Math.round(player.pct[m.key])}</span>
              </div>
              <div className="bar"><i style={{ width: `${player.pct[m.key]}%` }} /></div>
            </div>
          ))}
        </div>
      </div>

      <div className="minutes mono">
        Minutes played: <b>{player.minutes.toLocaleString()}</b>
      </div>
      {low && (
        <div className="warn mono angular-sm" role="note">
          (Warning: Under {MIN_MINUTES} mins, data might not be representative)
        </div>
      )}
    </article>
  );
}
