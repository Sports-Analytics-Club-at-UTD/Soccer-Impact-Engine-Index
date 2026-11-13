import { classify, classifyAll, METRICS } from './archetypes.js';
import { publicPlayerCopy } from './publicPlayerCopy.js';
import { playerName } from './playerNames.js';

// Adapt the approved release to the foundation's existing search and card UI.
// Ratings, eligibility and coverage are supplied by the validated release.
export function foundationPlayers(data) {
  return data.players.map((p) => {
    const position = p.comparison_position === 'CB' ? 'CB' : 'DM';
    const copy = publicPlayerCopy(p);
    return {
      id: p.id, ...playerName(p), team: [...new Set(p.clubs.map((c) => c.name === 'Marseille' ? 'Olympique de Marseille' : c.name))].join(' / '),
      position, primaryPosition: p.primary_position, season: p.season_name,
      minutes: p.coverage.supported_minutes, attributes: p.attributes,
      coverage: p.coverage, eligibilityReasons: p.ovr.exclusion_reasons,
      ratingDetails: copy,
      ovr: p.ovr.value, ranked: p.ovr.eligible, publicRating: true,
      archetype: p.badge_eligible ? classify({ position, attributes: p.attributes })
        : { name: 'Archetype unavailable', tier: null },
      archetypes: p.badge_eligible ? classifyAll({ position, attributes: p.attributes }) : [],
      ratingNotice: copy.notice,
    };
  });
}

export function publicRatingCard(player) {
  return {
    attributes: METRICS.map((m) => {
      const a = player.attributes[m.id];
      return { ...m, label: m.id === 'line_breaking_passes' ? 'Progressive passing' : m.label,
        value: a.rating, text: a.rating === null ? 'N/A' : a.rating.toFixed(2), percentile: a.percentile };
    }),
    profileLabel: '2015/16 player ratings',
    archetype: player.archetype, archetypes: player.archetypes, ovr: player.ovr, ovrLabel: 'Overall rating',
  };
}

export const displayOverall = (value) => value === null ? 'N/A' : value.toFixed(2);
