import { ratingCard } from "../lib/ratingCard.js";
import { publicRatingCard, displayOverall } from "../lib/foundationPlayers.js";
import { useCountUp, useTilt } from "../lib/hooks.js";
import Radar from "./Radar.jsx";
import { IconClose, Photo } from "./ui.jsx";
import ProvisionalPlayerCard from "./ProvisionalPlayerCard.jsx";
import FiveAttributePlayerCard from "./FiveAttributePlayerCard.jsx";

export default function PlayerCard({ player, onClose, demo = false }) {
  if (player.fiveAttributePresentation) return <FiveAttributePlayerCard player={player} onClose={onClose} />;
  return player.provisional
    ? <ProvisionalPlayerCard player={player} onClose={onClose} />
    : <StandardPlayerCard player={player} onClose={onClose} demo={demo} />;
}

function StandardPlayerCard({ player, onClose, demo = false }) {
  const tilt = useTilt({ max: 4, scale: 1.01 });
  const card = player.publicRating ? publicRatingCard(player) : ratingCard(player, { demo });
  const animatedOvr = useCountUp(card.ovr ?? 0);
  const ovr = player.publicRating ? displayOverall(card.ovr) : card.ovr === null ? "N/A" : animatedOvr;
  const a = card.archetype;
  const low = demo && player.minutes < 1000;

  return (
    <article {...tilt} className="tilt sheen card-surface on angular pcard" key={player.id} aria-label={`${player.name} player card`}>
      <span className="ghost-ovr display" aria-hidden="true">{player.publicRating ? displayOverall(card.ovr) : card.ovr ?? ""}</span>
      <button type="button" className="close" onClick={onClose} aria-label="Close player card"><IconClose size={16} /></button>

      <div className="pcard-top">
        <Photo src={player.photo} label={player.publicRating ? "Player photo" : "FIFA 16 photo"} className="lg" />
        <div>
          <div className="mono t10 up c2">{player.publicRating ? `${player.primaryPosition} · ${player.season}` : player.position === "CB" ? "Centre-back" : player.position === "DM" ? "Defensive midfielder" : "Role unavailable"}</div>
          <h3 className="display" style={{ marginTop: 10 }}>{player.name}</h3>
          <div className="team">{player.team}</div>

          <div className="ovr-block">
            <div className="ovr-num display" aria-label={card.ovrLabel}>{ovr}</div>
            <div className="mono t10 up mute" style={{ paddingBottom: 6 }}>{card.ovrLabel}</div>
          </div>

          <div className={`arch-badge angular-sm ${a.tier ? "" : "std"}`}>
            <span className="tier mono">{demo ? a.tier || "·" : a.tier === "+" ? "Gold" : a.tier === "−" ? "Silver" : "·"}</span>
            <span>
              <span className="mono t9 up dim" style={{ display: "block" }}>Archetype</span>
              <span className="display" style={{ fontSize: "1rem", lineHeight: 1.1 }}>{a.name}</span>
            </span>
          </div>
        </div>
      </div>

      <p className="mono t10">{card.profileLabel}</p>
      {player.ratingNotice && <p className="warn mono" role="note">{player.ratingNotice}</p>}
      <div className="viz">
        <Radar attributes={card.attributes} label={card.profileLabel} />
        <div className="stat-grid">
          {card.attributes.map((m) => (
            <div className="stat" key={m.key}>
              <div className="top">
                <span className="k"><b className="mono t11">{m.key}</b><span className="mono t10 up mute">{m.label}</span></span>
                <span className="mono t11">{m.text}</span>
              </div>
              <div className="bar">{m.value !== null && <i style={{ width: `${m.value}%` }} />}</div>
              {player.ratingNotice && <p className="mono t10">Percentile: {m.percentile === null ? "N/A" : String(Math.round(m.percentile))}
                {player.attributes[m.id]?.reasons?.length ? ` · ${player.attributes[m.id].reasons.join("; ")}` : ""}</p>}
              {player.publicRating && [...player.attributes[m.id].missingness, ...player.attributes[m.id].warnings].length > 0 && <p className="mono t10">{[...player.attributes[m.id].missingness, ...player.attributes[m.id].warnings].join(" · ")}</p>}
            </div>
          ))}
        </div>
      </div>

      <div className="minutes mono">
        Minutes played: <b>{Number.isFinite(player.minutes) ? player.minutes.toLocaleString() : "N/A"}</b>
      </div>
      {low && (
        <div className="warn mono angular-sm" role="note">
          (Warning: Under 1000 mins, data might not be representative)
        </div>
      )}
    </article>
  );
}
