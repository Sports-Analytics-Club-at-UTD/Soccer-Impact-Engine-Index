# Local individual-attribute Gold/Silver badges

The existing local policy classifies each of the five supplied component
percentiles independently, after frozen delivery and Formula B validation.
Only a profile admitted by the existing strict eligibility predicate can receive
badges. No badge calculation changes minutes, cohorts, scope, reference
membership, measurements, ratings or eligibility.

- Gold: unrounded component percentile **>=90**.
- Silver: **>=75 and <90**.
- Below 75 or unavailable: no displayed badge.

For an explicitly invented eligible fixture, percentiles 90, 75 and 74.9 give
Gold, Silver and no badge respectively. A value just below 90 remains Silver
even if its display rounds to 90. An ineligible fixture gets no badges regardless
of its observed percentiles. These examples reproduce no private measurements.

The shared badge component is used in detail cards and comparison cells, with
text labels and methodology disclosures. Qualifying ties can each receive a
badge. Component classifications do not create an OVR tier, positional archetype
or inferred DM/CM specialization. MID and CB references remain separate.

The rendered metric labels use colon typography. The frozen label
`Line Breaking \u2014 Progressive Passing Proxy` is displayed as
`Line Breaking : Progressive Passing Proxy`; its badge accessible name is
`Line Breaking : Progressive Passing Proxy: Gold attribute badge` (or Silver).
The frozen label is not changed. Public rendering tests already require this
colon substitution. The authorized private assertion formerly used the raw
frozen em-dash label at `provisionalOvr.test.js:61`; that expectation was stale.
The minimal correction is supplied in
`frontend/tests/corrections/provisionalOvr-label.patch`, with a corresponding
reviewed private-source fingerprint in `frontend/tests/suiteInventory.json`.
Apply it with `git apply --unidiff-zero` after the authorized private test source
is provisioned. All badge counts, tiers, eligibility checks and numeric tests
remain intact. The retained historical private harness is not edited.

Missing attributes stay unavailable and retain incomplete radar behavior.
[Limited Data](limited-data-status-consistency.md) and ranking exclusions remain
visible; a high observed score cannot override admission. This local permission
does not authorize real-player production publication or certify complete-season
coverage. See [Formula B](provisional-formula-b-ovr.md),
[public synthetic checks](../frontend/tests/componentClassification.test.js) and
[private verification prerequisites](test-suite-inventory.md).
