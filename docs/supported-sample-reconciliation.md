# Supported-sample player ratings

This branch implements the user-authorized follow-up to the 691-player audit.
It uses the audited website base (e388e16), retains the historical v1 aggregate
release unchanged, and creates a separate v2 snapshot. No deployment or merge
is performed. Raw provider records, original conflicts and previous research
snapshots remain unchanged.

## One policy for every player

Rank eligibility requires a supported MID/CB identity, observations exclusively
from the existing four-league cohort, at least 900 supported minutes for each
of the four per-90 metrics, and at least 40 supported pressure attempts. Each
metric must have a measured denominator. These are retained project cutoffs;
they are not statistically validated guarantees of precision. Bundesliga
measurements remain visible outside rankings and reference fitting.

Unresolved appearances do not automatically exclude a whole player. Per-90
numerators and durations use exactly the same accepted fixture set. A disputed
selected action withholds that fixture's whole component, rather than removing
an inconvenient event while retaining its exposure. A pressure chronology
conflict withholds the whole fixture ratio, including successes and failures.
Supported action ratios can include a fixture without a verified final duration.
Early video endpoints never become assumed final whistles or 90-minute matches.

All five attribute reference pools share the same eligible cohort within each
position. They are rebuilt once from the reconciled measurements and then frozen
with input and content fingerprints. Attribute definitions, sample-SD scoring,
clipping, percentile tie handling and Formula B weights stay unchanged. Reference
rebuilding changes ratings and percentiles even when a player's raw measurement
does not change; v1 and v2 scores are not directly comparable.

## Source handling

The command reopens all 1,551 retained audited fixtures and reconciles the 691
published provider identities. It includes active retained source appearances,
including those absent from the old published scope; unused bench disciplinary
records do not create appearances. This is the complete retained sample, not a
claim of complete historical season coverage or a new external-data acquisition.
Existing canonical comparison-position labels are retained.

The dismissal reconciler accepts a unique verified active Red Card/Second Yellow
cutoff only after an independent entry/exit state walk agrees with the clipped
lineup interval union and exact elapsed duration. Later passive tactical snapshots
are retained as conflicting assertions. Actual later activity, incompatible
re-entry, unrelated evidence gaps and ambiguous transitions withhold recovery.
It does not modify the default historical adapter.

Pressure clock-order checks use selected pressure actions and participation
transitions. A miscoded timestamp on an unrelated ball receipt cannot by itself
exclude a valid pressure sample. Actual activity after a permanent exit or an
incompatible return still withholds the entire fixture ratio. The first replay
used a broader clock check; its retained snapshot is followed by a byte-bound
replay of the 94 affected fixtures. That refinement proves that all other source
fields remain identical. A fresh full rebuild uses the refined check directly.

Fernandinho's Rosa/Roza alias is restricted to provider ID 3054. Other substantive
name disagreements remain excluded. Juanfran's unused-roster disciplinary
observation is removed from appearance counting. Original source roster IDs,
team context, event IDs and source document fingerprints must agree.

## Reproduction

From this branch, with the original authorized research checkout and completed
audit still available:

```powershell
python -B -m scripts.rebuild_supported_ratings --source-root ../.. --audit ../player-data-eligibility-audit/audit-output/full-audit --output audit-output/rebuild --workers 4
python -B -m scripts.verify_supported_ratings audit-output/rebuild
python -B -m scripts.install_supported_release audit-output/rebuild
python -B -m scripts.run_backend_tests public -q
cd frontend
npm run test:public
npm run build
```

All output directories and aggregate destinations must be new. Source bytes,
measurement scopes, exact denominators, eligibility reasons, reference cohorts,
sample statistics, percentiles, Formula B and named-player regressions are
checked before installation. `changes.csv` and `changes.json` cover every player;
the source replay retains each excluded fixture and its reasons. Research outputs
stay in ignored `audit-output`; only aggregate ratings and sample coverage enter
the frontend. The HTTP loader and production build require the new exact path,
byte count and SHA-256. Payload flags and environment variables cannot admit
unreviewed data.

## Verified result

All 691 profiles were rebuilt from 1,551 fixtures and 5,436,699 original events.
The new policy admits 551 ranked players (297 MID, 254 CB), up from 231. There
are 320 newly eligible players and no previously eligible player loses admission.
The 138 Bundesliga contributors remain outside rankings; Guglielmo Stendardo
and Adriano Russo remain excluded because they have fewer than 40 supported
pressure attempts. Some exclusions overlap with minute minimums.

Busquets is eligible with 34 duration-supported appearances and 2,912.461217
minutes; pressure retains 301 successes / 357 attempts across 35 matches. Ramos
is eligible with all 23 appearances and 2,010.556500 minutes. His two verified
dismissal cutoffs are included. Across the population, 189 dismissal appearances
are recovered and 239 appearances retain unresolved duration. Weber's disputed
fixture is withheld from pressure entirely, leaving 79 successes / 109 attempts.
Fernandinho's provider-bound spelling alias is accepted; Juanfran's unused bench
discipline record no longer counts as an appearance.

Independent verification passes 402,045 checks over all profiles and source
bindings. All 1,225 public backend cases and all 231 public frontend tests pass,
including production HTTP/admission checks; the production build passes. Browser
checks confirm keyboard player search, rank inclusion, expanded metric coverage,
accessible close controls and no horizontal overflow at 1,440px, 375px and 320px.
No application runtime errors were observed; the existing missing favicon returns
404. About Us and the team spatial visualization source remain unchanged.

The complete private review is in `audit-output/supported-sample-final/REPORT.md`,
with individual reports for every player, `changes.csv`, the source replay and
the final verification receipt. The website aggregate is separately pinned to
`frontend/public/data/player-ratings-2015-16-v2.json` (SHA-256
`e9fe1b6f3ca825eb8c961fea484ba08eed95d87c2cf8958f23303683d627e39d`).
