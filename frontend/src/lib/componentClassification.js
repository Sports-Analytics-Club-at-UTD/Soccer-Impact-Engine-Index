import { componentTier } from './archetypes.js';
import { FIVE_METRICS } from './fiveAttributePresentation.js';
import { playerDataStatus } from './playerDataStatus.js';

// Reuse the existing individual-attribute badge rules and strict eligibility.
// Publication scope is controlled separately by the pinned public release.
export const ATTRIBUTE_BADGE_METHODOLOGY = 'Gold indicates an attribute at or above the 90th percentile of its existing position-specific reference population. Silver indicates the 75th to below the 90th percentile. Badges are shown only for strictly eligible real-player profiles. They describe individual component strengths; Formula B remains the overall rating. Final 2015/16 ratings are approved for public display; raw research evidence is not distributed.';

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
