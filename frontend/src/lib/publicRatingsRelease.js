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
  path: 'data/player-ratings-2015-16-v3.json',
  sha256: 'ad2be90730ffd3019a3b8c66385bec2b5c1958a3e34bf476628e1238a65851bf',
  bytes: 1512488,
  approval: 'User authorized source/scope corrections and recovery of verified portions of remaining non-Bundesliga appearances on 2026-11-13. Aggregate ratings and coverage only; no deployment or raw-source publication.',
});
