/* Shared primitives + inline icons (no icon library needed). */

const I = ({ children, size = 16, ...rest }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
       strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}>{children}</svg>
);

export const IconSearch = (p) => <I {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></I>;
export const IconSun = (p) => <I {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></I>;
export const IconMoon = (p) => <I {...p}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" /></I>;
export const IconMenu = (p) => <I {...p}><path d="M4 7h16M4 12h16M4 17h16" /></I>;
export const IconClose = (p) => <I {...p}><path d="M6 6l12 12M18 6 6 18" /></I>;
export const IconArrow = (p) => <I {...p}><path d="M5 12h14M13 6l6 6-6 6" /></I>;
export const IconDown = (p) => <I {...p}><path d="m6 9 6 6 6-6" /></I>;

/* Club-neutral mark: a pitch half-circle + press ring. Swap for your logo. */
export function Mark({ size = 28 }) {
  return (
    <svg className="brand-mark" width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="28" height="28" rx="3" stroke="var(--a1)" strokeWidth="1.6" />
      <path d="M2 16h8M22 16h8" stroke="var(--a1)" strokeWidth="1.2" opacity=".7" />
      <circle cx="16" cy="16" r="5" stroke="var(--a2)" strokeWidth="1.4" />
      <circle cx="16" cy="16" r="1.6" fill="var(--a2)" />
    </svg>
  );
}

export function SectionHead({ eyebrow, title, intro }) {
  return (
    <div className="section-head reveal">
      <div className="eyebrow">{eyebrow}</div>
      <h2 className="display">{title}</h2>
      {intro && <p>{intro}</p>}
    </div>
  );
}

/* Image slot: shows the image when `src` is set, otherwise a labelled placeholder. */
export function Photo({ src, label, className = "" }) {
  return (
    <div className={`photo ${className}`}>
      {src ? <img src={src} alt={label} loading="lazy" /> : <span className="mono t10 up">{label}</span>}
    </div>
  );
}
