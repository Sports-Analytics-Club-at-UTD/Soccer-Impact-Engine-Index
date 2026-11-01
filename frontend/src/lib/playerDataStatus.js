// Presentation/discovery status only: consume validated coverage and eligibility.
// Never infer or change eligibility, ratings, source flags or exclusion reasons.
export function playerDataStatus({ presentation, ovr } = {}) {
  const coverageLimited = presentation?.limited_data === true ||
    Object.values(presentation?.attributes ?? {}).some((m) => m?.limited_data === true);
  const notRanked = ovr?.eligible === false;
  return {
    coverageLimited,
    notRanked,
    limited: coverageLimited || notRanked,
    label: notRanked ? 'LIMITED DATA · NOT RANKED'
      : coverageLimited ? 'LIMITED DATA'
        : ovr?.eligible === true ? 'Leaderboard eligible' : null,
  };
}
