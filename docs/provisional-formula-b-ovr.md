# Provisional Formula B overall rating

The authorized local experiment uses the existing full-precision five attribute
ratings: tackles, interceptions, recoveries, press resistance and the
progressive-passing proxy. Sort their numeric values from highest to lowest and
apply weights **30%, 25%, 20%, 15%, 10%** in that order. The weights attach to
sorted values, not fixed attributes or positions. Only display rounds.

An explicitly invented example `[90, 80, 70, 60, 50]` yields **75**. It is a math
example, not a measured player or a renamed private record. All five finite
ratings must be in [1,99]; an absent/invalid component produces OVR **N/A**,
never an imputed zero. Ties do not change the result. The backend preserves
exact arithmetic over supplied binary floats; the client independently validates
the delivery and formula result before presenting it.

OVR is provisional project analysis, not an official EA rating, a football
outcome validation or a publication approval. Its value does not confer ranking
eligibility. The adapter reuses the existing strict reference-intersection and
scope rules; MID and CB leaderboards stay separate. Ineligible profiles retain
their calculated observed OVR without being ranked. There is no overall
Gold/Silver tier and no Formula B percentile borrowed from another model.

The loopback development homepage uses one validated adapter load. Missing or
mismatched frozen inputs fail explicitly with no demo fallback. Production
remains fictional. See [provisioning](private-local-provisioning.md),
[Limited Data](limited-data-status-consistency.md), and
[the test inventory](test-suite-inventory.md). Source-only arithmetic checks are
in [Formula B tests](../tests/test_source_only_formula_b.py); independent exact
real-score parity remains an authorized private workflow with unchanged refs.
