import { componentTier } from '../lib/archetypes.js';
import { FIVE_METRICS } from '../lib/fiveAttributePresentation.js';
import { playerDataStatus } from '../lib/playerDataStatus.js';

// Explicit user approval, 2026-10-31: individual attribute badges in the local
// experiment only. Consume the validated strict Formula B eligibility decision;
// do not recalculate membership or authorize archetypes/publication.
export const ATTRIBUTE_BADGE_METHODOLOGY = 'Gold indicates an attribute at or above the 90th percentile of its existing position-specific reference population. Silver indicates the 75th to below the 90th percentile. Badges are shown only for strictly eligible real-player profiles. They describe individual component strengths; Formula B remains the overall rating. Local preview only; publication is not authorized.';

export function experimentalComponentClassification(player) {
  const { presentation, ovr } = player;
  // Defensive completeness checks do not add a new eligibility policy. The
  // validated eligible population already satisfies them; absent data fails shut.
  const complete = FIVE_METRICS.every(({ id }) => {
    const rating = presentation?.attributes?.[id]?.rating;
    return typeof rating === 'number' && Number.isFinite(rating) && rating >= 1 && rating <= 99;
  });
  const eligible = ovr?.eligible === true && !playerDataStatus(player).limited && complete;
  return Object.freeze({
    status: eligible ? 'eligible' : 'withheld',
    explanation: ATTRIBUTE_BADGE_METHODOLOGY,
    tiers: Object.freeze(Object.fromEntries(FIVE_METRICS.map(({ id }) =>
      [id, eligible ? componentTier(presentation.attributes[id].percentile) : null]))),
  });
}
