# Five-attribute delivery contract design

## Implemented boundary: synthetic presentation v1

`src/five_attribute_presentation.py` and
`frontend/src/lib/fiveAttributePresentation.js` implement
`soccer-five-attribute-presentation/v1`. This is a new, isolated synthetic
presentation contract, not a modification of `soccer-rating-delivery/v1` or
`soccer-provisional-observations/v1`. Both older contracts retain their previous
admission behavior. The scorer, frozen baselines and private score outputs are
untouched.

Exact envelope fields:

| Field | Current enforced value/meaning |
| --- | --- |
| schema_version | `soccer-five-attribute-presentation/v1` |
| classification | `synthetic` only |
| notice | `SYNTHETIC TEST FIXTURE / NOT REAL PLAYER RATINGS / NOT PUBLICATION AUTHORIZED` |
| publication_authorized | false |
| numeric_real_delivery_enabled | false |
| reference | Fingerprinted synthetic frozen reference registry |
| players | Unique canonical synthetic player-seasons |

No authorization flag, real classification or real player ID can activate real
delivery. Current identity/reference/provenance IDs require a `synthetic:` prefix
and player/club names require `SYNTHETIC `. Unknown fields, duplicate player-season
IDs, overlapping club fixtures, out-of-range scores, nonfinite values, mismatched
units, unsupported geometry labels and inconsistent arithmetic are rejected.
Frontend text parsing reuses the existing duplicate-JSON-key rejection.

Player fields: `id`, `player_id`, `name`, `season_name`, `comparison_position`
(MID, CB or null), `positions`, `clubs`, `limited_data`, `partial_season`,
`attributes`, `provenance`. Canonical `id = player_id + ':' + season_name`;
transfers are multiple club contexts within one card, not duplicated identities.
Club contexts contain name, competition and disjoint match IDs.
There is deliberately no OVR, archetype, tier, approval or weighting field.

The five stable presentation attribute IDs match the existing card architecture:
`tackles`, `interceptions`, `recoveries`, `press_resistance`,
`line_breaking_passes`. Each attribute has exactly:

| Field | Validation/presentation |
| --- | --- |
| label | Tackling; Interceptions; Ball Recovery; Press Resistance; **Line Breaking — Progressive Passing Proxy** |
| measurement_kind | `progressive_passing_proxy` for fifth; `observed_metric` otherwise |
| rating | null or finite 1..99; no rounding of input |
| percentile | null or finite 0..100; separate from rating |
| observation | null or measured value, units, raw numerator, denominator, denominator unit, rational supported minutes, action sample size and matched fixture IDs |
| normalization | Comparison position, reference version/fingerprint and position/metric pool fingerprint |
| missingness | Explicit reasons; absent measurement or score stays N/A |
| exclusions | Fixture IDs and reasons; per90 denominators exclude these fixtures |
| limited_data / partial_season | Explicit booleans, inherited from player where applicable |
| provenance_ids | Bound to player's supplied evidence descriptors |

An observation's exact supported minutes are `{numerator, denominator}`; per90
is raw count / supported minutes *90. Press uses successful actions / attempts
*100, with attempt count as denominator and action sample size. Its known
supported minutes may be null; this does not manufacture an exposure denominator.
Sub-40 actions require LIMITED DATA. Bundesliga requires LIMITED DATA and PARTIAL
SEASON even with every observed appearance supported. Missing and low samples
never default to a neutral score.

The synthetic frozen registry has a version and separate MID/CB metric pools,
each containing a population version, group/metric ID, n, mean, positive sample
SD, synthetic member IDs and fingerprint. SHA256 binds each pool and the full
registry. Python/JS canonical JSON uses sorted keys, no whitespace, UTF-8,
integer-valued numbers encoded as integers. SHA256 is an integrity check, **not
approval authentication**. The browser verifies reference/pool hashes before
constructing models. Numeric fixtures must agree with their supplied measured
input and frozen formula. Rendering does not fit populations or infer percentiles.

## Designed boundary: authorized real delivery — NOT IMPLEMENTED OR ENABLED

Reserve `soccer-five-attribute-authorized-delivery/v1` for a separate, reviewed
adapter and validator after actual team approvals. No current runtime accepts
this schema. Do not change the synthetic classification/name checks to make
private files fit. Do not feed the private scorer's JSONL directly to the website.

The proposed real contract reuses the player/attribute presentation fields above
with signed-int64 canonical player IDs encoded as decimal strings, exact rational
measurements and explicit nullable observations, plus this required envelope:

| Proposed field | Required binding before admission |
| --- | --- |
| schema_version / classification | New authorized schema / `authorized_real`; neither accepted by the current implementation |
| cohort / definitions_version | Exact approved season, leagues, position policy, five definitions and recipient/exclusion rules |
| frozen_reference | Accepted existing baseline version/hash; server registry supplies unchanged per-metric n/mean/sample SD and pool/member fingerprints |
| reference_projection_fingerprint | Hash of the delivered registry summary; distinct from the source baseline's full-content hash |
| evidence_manifest_refs | Accepted source, identity, appearance/fixture and measurement package hashes |
| decision_record_refs | Authentic recorded team decisions bound to each individual transform, population, press/proxy policy, evidence scope and release |
| publication_scope | Explicit channel, release/cohort and approved policy/evidence/reference fingerprints |
| players | One record per canonical player-season with per-attribute authorized/withheld state and all underlying measurements/warnings |

The real adapter must validate all six existing admission gates against accepted
evidence and authentic decision records, not payload booleans:
`delivered_table_eligible`, `independent_source_supported`,
`season_exposure_verified`, `metric_numerator_verified`, `scoring_approved`,
`publication_authorized`. Apply the checks to the actual attribute/player/fixture
scope. A global publication approval does not implicitly approve every private
row. Partial-season/provisional exceptions must be explicitly covered by the
accepted policy; missing full-season evidence cannot simply be labelled verified.

Do not mint approvals, invent a signature format or nominate a final approver.
The future authorization verifier must authenticate the real team's chosen
review records; this document and a self-declared `approved: true` are not such
records. Default-deny on missing, stale, scope-incompatible or mismatched records.
New policy/population changes need new accepted versions; adding recipients must
not recompute the frozen reference. Publication enablement is a separate release
action, not a side effect of this readiness task.

### Existing private-output mapping after approval

The adapter may consume accepted existing measurements/frozen statistics without
refitting: private `progressive_passing` maps to presentation
`line_breaking_passes`; the explicit proxy label/kind is mandatory. Its numeric
rating and percentile can be copied only after attribute-scope admission.
`raw_counts`, `numerator`, `attempts`, `exact_value`, `supported_minutes`, matching
fixture IDs, exclusions, position evidence and warnings map to observation and
normalization fields. Source and fixture lineage must remain available; both
unsupported measurements and unauthorized numerical fields remain N/A.

The client then needs a separately gated authorized loader/parser and a
versioned trust check at the card-model boundary. Reuse the card layout, existing
Radar and comparison table; do not route real actors through the synthetic-only
validator or silently relabel private outputs. The current synthetic header and
identity checks intentionally prevent this. A release requires end-to-end tests
of authenticated admission, withheld attributes, baseline hashes, transfers,
Bundesliga exceptions and denial of unapproved private files.

## What is ready now

`?view=five-attribute-synthetic` or
`VITE_PLAYER_DATA_MODE=five-attribute-synthetic` selects only the bundled invented
fixture. No real file upload, fetch or private-data import exists in that path.
The default site remains demo; the existing `?view=limited-data` observation route
is preserved. Existing `PlayerCard` dispatches to the new card; `Radar` stays
unchanged and renders five labelled axes, individual points and no polygon for
an incomplete profile. Comparison preserves each player's own normalization
group; it computes no composite score, archetype or tier.

Synthetic data is in `frontend/src/fixtures/syntheticFiveAttributes.json` and is
generated exclusively by `scripts/make_synthetic_five_attribute_fixture.py`.
Tests validate Python/JS parity, integrity, measurements, bounds, missingness,
warnings, deduplication, comparison and denial of unauthorized real delivery.
Production builds contain those unmistakably synthetic fixtures and the existing
observation asset, never private real rating files. Actual real-rating admission,
loader/exporter and publication are deliberately not implemented.
