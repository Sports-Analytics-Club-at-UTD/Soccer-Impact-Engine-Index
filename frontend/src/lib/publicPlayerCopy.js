// Visitor-facing explanations only. Original reasons and eligibility stay intact.
export const ATTRIBUTE_NAMES = {
  tackles: 'Tackles', interceptions: 'Interceptions', recoveries: 'Ball recoveries',
  press_resistance: 'Press resistance', progressive_passing: 'Progressive passing',
  line_breaking_passes: 'Progressive passing',
};

export function publicPlayerCopy(player) {
  const reasons = player.ovr.exclusion_reasons;
  const codes = new Set(reasons.map((r) => r.split(':').at(-1)));
  const explanations = [];
  const add = (text) => { if (!explanations.includes(text)) explanations.push(text); };
  if (codes.has('BUNDESLIGA_CONTRIBUTION')) add('Bundesliga match coverage is too limited for inclusion in the rankings.');
  else if (codes.has('NOT_FOUR_LEAGUE_ONLY')) add('This profile includes matches outside the leagues used for rankings.');
  if (codes.has('INCOMPLETE_OBSERVED_EXPOSURE')) add('Some match minutes could not be confirmed.');
  if (codes.has('INVALID_OR_PENDING_FIXTURE_SCOPE')) add('A match in this profile is still awaiting review.');
  if ((codes.has('INCOMPLETE_METRIC_SCOPE') || codes.has('FIXTURE_SCOPE_NOT_FULLY_ALIGNED')) &&
      !codes.has('INCOMPLETE_OBSERVED_EXPOSURE') && !codes.has('INVALID_OR_PENDING_FIXTURE_SCOPE')) {
    const affected = [...new Set(reasons.filter((r) => /:(INCOMPLETE_METRIC_SCOPE|FIXTURE_SCOPE_NOT_FULLY_ALIGNED)$/.test(r))
      .map((r) => ATTRIBUTE_NAMES[r.split(':')[0]]?.toLowerCase()).filter(Boolean))];
    add(`Not every match can be included in ${affected.length ? affected.join(', ') : 'the individual ratings'}. Some actions could not be matched reliably to playing time.`);
  }
  if (codes.has('BELOW_900_VERIFIED_SEASON_MINUTES')) add('Fewer than 900 minutes of playing time could be confirmed.');
  if (codes.has('BELOW_40_SUPPORTED_ATTEMPTS')) add('Fewer than 40 actions under pressure are available for ranking.');
  if (codes.has('UNSUPPORTED_POSITION')) add('This playing position is not included in the rankings.');
  if (codes.has('METRIC_EXPOSURE_NOT_COMPLETE_900_MINUTES') && !explanations.length) add('The individual ratings do not all have the playing time required for ranking.');
  if (!player.ovr.eligible && !explanations.length) add('This profile does not meet all the requirements for a like-for-like ranking.');
  const missing = Object.entries(player.attributes).filter(([, a]) => a.rating === null)
    .map(([key]) => ATTRIBUTE_NAMES[key] ?? 'An individual skill');
  const notice = missing.length
    ? `Overall rating unavailable · ${missing.join(', ')} could not be rated. Not included in rankings.`
    : player.ovr.eligible ? null : `Not ranked · ${explanations[0]}`;
  const attributeNotes = Object.fromEntries(Object.entries(player.attributes).map(([key, a]) => {
    let note = null;
    if (a.rating === null) note = a.missingness.includes('NO_SUPPORTED_ATTEMPTS')
      ? 'No recorded actions under pressure are available to calculate this rating.'
      : 'There is not enough reliable match evidence to calculate this rating.';
    else if (a.warnings.includes('BELOW_40_PRESS_ACTIONS / LIMITED DATA')) note = 'Based on fewer than 40 actions under pressure.';
    return [key, note];
  }));
  const seasonCoverage = player.partial_season
    ? 'Historical season coverage is unverified. Confirmed minutes describe supported observed matches; ranking eligibility does not certify full-season coverage.'
    : null;
  return { notice, explanations, attributeNotes, seasonCoverage };
}
