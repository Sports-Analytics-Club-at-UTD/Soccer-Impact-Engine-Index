import { classify, METRICS } from './archetypes.js';
import { playerDataStatus } from './playerDataStatus.js';

// Adapt the approved release to the foundation's existing search and card UI.
// Ratings, eligibility and coverage are supplied by the validated release.
export function foundationPlayers(data) {
  return data.players.map((p) => {
    const position = p.comparison_position === 'CB' ? 'CB' : 'DM';
    return {
      id: p.id, name: p.name, team: p.clubs.map((c) => c.name).join(' / '),
      position, primaryPosition: p.primary_position, season: p.season_name,
      minutes: p.coverage.supported_minutes, attributes: p.attributes,
      ovr: p.ovr.value, ranked: p.ovr.eligible, publicRating: true,
      archetype: p.badge_eligible ? classify({ position, attributes: p.attributes })
        : { name: 'Withheld — limited data', tier: null },
      ratingNotice: [playerDataStatus({ presentation: p, ovr: p.ovr }).label,
        'Partial-season observations; supported minutes only.',
        'Progressive passing is a proxy for line breaking.',
        ...p.ovr.exclusion_reasons].filter(Boolean).join(' · '),
    };
  });
}

export function publicRatingCard(player) {
  return {
    attributes: METRICS.map((m) => {
      const a = player.attributes[m.id];
      return { ...m, label: m.id === 'line_breaking_passes' ? 'Progressive passing proxy' : m.label,
        value: a.rating, text: a.rating === null ? 'N/A' : a.rating.toFixed(2), percentile: a.percentile };
    }),
    profileLabel: 'Approved 2015/16 rating profile',
    archetype: player.archetype, ovr: player.ovr, ovrLabel: 'Formula B OVR',
  };
}

export const displayOverall = (value) => value === null ? 'N/A' : value.toFixed(2);
