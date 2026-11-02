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

## Season coverage, observation support and eligibility

`partial_season` is a conservative legacy coverage flag: historical full-season
coverage has not been certified. It is deliberately true for all 691 published
profiles and the private V2 candidate, including the 231 strictly eligible
profiles. It does not assert that every player is known to be missing a match.
The original source policy in `src/fifth_attribute.py` labels supported records
as observed provider fixtures, not full-season certified. The five-attribute
aggregator preserves that flag; V1 export, V2 export and comparison CSVs retain
it without deriving it from eligibility.

Three separate questions must stay separate:

- Historical season coverage: is the full historical season certified?
- Supported observed exposure: are the retained observed appearances and each
  metric's numerator/exposure scope supported? Unknown or excluded appearances
  remain explicit.
- Leaderboard eligibility: does the observed profile satisfy the existing
  complete-scope, frozen-membership, position, competition, 900-minute and
  40-pressure-action requirements?

The five profiles without OVR are incomplete five-attribute profiles. They are
not the count of profiles with unverified historical season coverage. All 691
can retain `partial_season=true` while only five lack OVR. Complete supported
observations and ranking admission do not establish a complete historical season.

Player-card details now describe the flag as historical season coverage being
unverified. Existing Partial Season warnings explain the same distinction.
This wording does not add Limited Data status, remove badges or exclude eligible
players. The flag, CSV serialization, source restrictions and eligibility rules
remain unchanged.

See [Formula B](provisional-formula-b-ovr.md),
[badges](local-attribute-badges.md), and
[unified navigation/state](unified-local-website-integration.md).
