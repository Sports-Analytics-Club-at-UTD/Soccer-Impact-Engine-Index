import { useEffect, useRef } from 'react';
import { createSpring, rubberband, sheetDestination } from '../lib/motion.js';
import PlayerCard from './PlayerCard.jsx';

export default function PlayerSheet({ player, onClose, trigger }) {
  const dialog = useRef(null), spring = useRef(null), gesture = useRef(null);
  const dismiss = useRef(onClose);
  dismiss.current = onClose;
  const visible = !!player;

  useEffect(() => {
    if (!visible) return;
    const surface = dialog.current;
    const previous = document.body.style.overflow;
    surface.dataset.closing = "false";
    surface.showModal();
    surface.querySelector('.pcard .close')?.focus();
    document.body.style.overflow = 'hidden';
    const motion = createSpring(surface.getBoundingClientRect().height, (y) => {
      surface.style.transform = `translateY(${y}px)`;
    });
    spring.current = motion;
    motion.set(motion.position);
    motion.to(0);
    return () => {
      motion.stop(); spring.current = null;
      surface.close(); surface.style.transform = '';
      document.body.style.overflow = previous;
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    };
  }, [visible, trigger]);

  const close = () => {
    const motion = spring.current;
    if (motion) { dialog.current.dataset.closing = "true"; motion.to(dialog.current.getBoundingClientRect().height, undefined, () => dismiss.current()); }
  };
  const endDrag = (e, cancelled = false) => {
    const drag = gesture.current;
    if (!drag || drag.id !== e.pointerId) return;
    gesture.current = null;
    const motion = spring.current;
    if (!motion) return;
    const history = drag.history.filter((point) => e.timeStamp - point.time <= 100);
    const first = history[0], last = history.at(-1);
    const velocity = first && last.time > first.time ? (last.y - first.y) / (last.time - first.time) * 1000 : 0;
    const height = dialog.current.getBoundingClientRect().height;
    const target = cancelled || !drag.moved ? 0 : sheetDestination(motion.position, velocity, height);
    dialog.current.dataset.closing = String(!!target);
    motion.to(target, cancelled ? 0 : velocity, target ? () => dismiss.current() : undefined);
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  };

  return <dialog ref={dialog} className="player-dialog" aria-label={player ? `${player.name} player profile` : 'Player profile'}
    onCancel={(e) => { e.preventDefault(); close(); }}
    onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
    <div className="sheet-handle" role="separator" aria-label="Drag down to dismiss player profile"
      onPointerDown={(e) => {
        if (e.button !== 0 || !spring.current) return;
        dialog.current.dataset.closing = "false";
        spring.current.stop();
        e.currentTarget.setPointerCapture(e.pointerId);
        gesture.current = { id: e.pointerId, offset: e.clientY - spring.current.position,
          startY: e.clientY, moved: false, history: [{ y: e.clientY, time: e.timeStamp }] };
      }}
      onPointerMove={(e) => {
        const drag = gesture.current;
        if (!drag || drag.id !== e.pointerId || !spring.current) return;
        drag.history = [...drag.history.filter((point) => e.timeStamp - point.time <= 100), { y: e.clientY, time: e.timeStamp }];
        if (!drag.moved && Math.abs(e.clientY - drag.startY) < 10) return;
        drag.moved = true;
        const y = e.clientY - drag.offset;
        spring.current.set(y < 0 ? rubberband(y, dialog.current.getBoundingClientRect().height) : y);
      }}
      onPointerUp={endDrag} onPointerCancel={(e) => endDrag(e, true)} onLostPointerCapture={(e) => endDrag(e, true)}>
      <span />
    </div>
    {player && <PlayerCard player={player} onClose={close} />}
  </dialog>;
}
