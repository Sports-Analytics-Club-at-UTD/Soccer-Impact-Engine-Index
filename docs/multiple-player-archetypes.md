# Multiple player archetypes

Eligible player cards show every qualifying position-specific archetype, up to five (one per skill). Gold starts at the exact 90th percentile; Silver starts at 75 and stays below 90. Styles are ordered by descending percentile, with existing position-specific definition order retained for ties. The strongest remains the primary style used in compact previews; those previews also show how many additional styles the full card contains.

The public release's existing `badge_eligible` decision still gates every archetype. Ineligible players keep “Archetype unavailable” and no earned styles. Eligible players without a qualifying skill remain “Standard.” Missing or invalid percentiles never earn styles. Names and tiers are text, so the display does not rely on color.

The release payload, rating calculations, reference populations, rankings, coverage and eligibility rules are unchanged. The additional styles are derived in the presentation adapter from the existing percentiles. The singular primary-style helper remains available to existing validators and consumers. Diagnostic and experimental views keep their existing per-attribute badge handling.

The change lives on `multiple-player-archetypes`, based on `origin/main` at `e388e16`, independently of the spatial-visualization branch.

Verification: all 229 public tests and the production build pass. The additional tests check exact percentile boundaries, both position mappings, stable ties, invalid or missing values, all 691 public profiles' existing eligibility and rating values, and full-card and preview rendering. Browser checks confirm five badges fit at 320, 375, 768 and 1440 pixels, alongside Standard and unavailable states. A touch-enabled 320px preview of Augusto Fernández shows all five badges, retains the close button after scrolling, and reports no page errors.
