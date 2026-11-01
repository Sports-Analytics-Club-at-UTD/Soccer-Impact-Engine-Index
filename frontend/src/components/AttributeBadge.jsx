// Rendering only. The local validated model determines admission and tiers.
export default function AttributeBadge({ tier, label }) {
  if (tier !== 'Gold' && tier !== 'Silver') return null;
  return <span className={`attribute-badge attribute-badge-${tier.toLowerCase()}`} aria-label={`${label}: ${tier} attribute badge`}>{tier}</span>;
}
