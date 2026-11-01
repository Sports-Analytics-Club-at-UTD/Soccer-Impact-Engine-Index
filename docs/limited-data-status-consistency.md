# Limited Data and ranking status

The shared `playerDataStatus` helper drives discovery filters, cards and
comparisons. Limited Data includes either a measurement/coverage limitation or
an explicit ranking exclusion. The filter therefore includes every profile
carrying the corresponding visible status; it is not restricted to a single
league or one low-sample flag.

Coverage and rank admission remain distinct. A profile can have complete
observed attribute ratings yet be unranked under the existing strict eligibility
rules. Preserve its calculated score and the reason for exclusion. A missing
score stays N/A. Do not drop excluded profiles from discovery, award them badges,
impute missing values or change admission to make a filter count look complete.

An invented fixture with complete observations, calculated OVR 75 and
`eligible=false` remains discoverable with Limited Data / Not Ranked and retains
75. This is a synthetic interface example, not a private player measurement.

Partial Season describes observed scope; it does not by itself prove Limited
Data or ranking exclusion. Even an admitted observed sample does not establish
historical season completeness. Search, league, MID/CB, coverage and Limited
Data controls compose over the same canonical view models. Transfers retain one
canonical player-season and compatible disjoint evidence; unsupported exposure
stays explicit rather than becoming zero.

No status cleanup changes Formula B, source attributes or cohort membership.
See [Formula B](provisional-formula-b-ovr.md),
[badges](local-attribute-badges.md), and
[unified navigation/state](unified-local-website-integration.md).
