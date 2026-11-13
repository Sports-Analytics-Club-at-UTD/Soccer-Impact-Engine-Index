// Historical aggregate release retained for explicit compatibility checks.
export const LEGACY_PUBLIC_RATINGS_RELEASE = Object.freeze({
  path: 'data/player-ratings-2015-16-v1.json',
  sha256: '9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e',
  bytes: 1431543,
  approval: 'Team approval for final aggregate 2015/16 ratings supplied on 2026-10-31; raw research excluded.',
});

// Supported samples and rebuilt cohorts authorized in the player-audit review.
// Exact path and bytes remain mandatory; payload flags cannot admit other data.
export const PUBLIC_RATINGS_RELEASE = Object.freeze({
  path: 'data/player-ratings-2015-16-v2.json',
  sha256: 'e9fe1b6f3ca825eb8c961fea484ba08eed95d87c2cf8958f23303683d627e39d',
  bytes: 1448401,
  approval: 'User authorized source/scope corrections, measurement and reference rebuild, and a uniform eligibility rule on 2026-11-13. Aggregate ratings and coverage only; no deployment or raw-source publication.',
});
