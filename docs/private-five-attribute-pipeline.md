# Private consolidated five-attribute pipeline

The authoritative completed experiment is
`data/derived/private-five-attribute-v2/`. Its schema/policy is
`private-five-attribute-player-season/v2`. It is **PRIVATE / EXPERIMENTAL**, with
no production delivery, publication authority, OVR, tiers or attribute weights.
Earlier local v1 directories are development snapshots; v2 distinguishes the
press reference minimum from recipient eligibility.

## Reused evidence and definitions

`scripts/score_private_five_attributes.py` consumes the already verified four-league
and Bundesliga match-component ledgers and the completed Joseph fifth-attribute
package. It checks input fingerprints and joins exact canonical player/fixture/
club/league/season contexts. It does not open original event documents or
Parquets, fetch data, reconstruct minutes, rerun original evidence verification,
or import a contributor's writer.

- Tackles: Duel/Tackle with Won, Success In Play or Success Out.
- Interceptions: Interception with those same successful outcomes. Total
  interceptions from the PDF are a different definition and are not substituted.
- Recoveries: Ball Recovery with recovery_failure not True.
- Press resistance: 100 * successful pressured Pass/Dribble actions / all such
  attempts. Pass succeeds with missing outcome; Dribble succeeds only with
  Complete. There is no open-play filter. This is the existing Pratyush-derived
  action ratio, distinct from Joseph's broader press retention metric.
- Progressive Passing Proxy: Joseph's unchanged Level A completed open-play
  passes moving >=10 yards forward and reducing distance to goal by >=25%.
  Unknown and Injury Clearance outcomes are excluded. This is not a verified
  opponent-line-break measurement. No 360 data is used.

## Identity, exposure and missingness

`src/private_five_attribute.py` aggregates disjoint raw actor-match contributions
into one player-season. It reuses Joseph's canonical dominant verified fine
position group, then maps DM/CM to MID, keeping CB separate. Other positions and
ties remain explicit and cannot gain scoring admission. Club scores and
percentages are never averaged.

Each per90 attribute sums only its own aligned numerator and supported elapsed
minutes. Each metric retains its own supporting fixture IDs and excluded
appearances. Known zeros over positive verified exposure remain zeros; absent
measurements remain null. Counts and UUID lineage remain in the fact ledger.
Pending fixture 3879594 is excluded with an explicit reason.

Press's denominator is attempts, not minutes. Its verified action ratio can
remain supported when appearance duration is unresolved, matching the existing
Bundesliga policy. Unknown exposure is disclosed separately and cannot confer
reference eligibility. Success UUIDs must be contained in the same actor/fixture
attempt UUIDs. Per90 support never inherits this press-specific exception.

## Per-attribute frozen references and scores

Each attribute computes its own MID and CB member lists from unique four-league
player-seasons. Members require >=900 combined verified minutes, complete
observed exposure, complete metric-specific aligned scope, and no pending
fixture. Press references additionally require >=40 pressured actions.
Every Bundesliga contributor is excluded, including cross-league transfers.
Joseph's fifth-attribute membership is not copied to the other attributes.

Normal four-league score recipients require >=900 metric-supported minutes for
per90 attributes, or >=900 known season minutes plus positive supported attempts
for press. The 40-action threshold applies to reference membership; a supported
sub-40 recipient may receive a private projection with LIMITED DATA and its
sample size. Bundesliga contributors may receive provisional per90 scores over
positive supported exposure or a positive supported press ratio, retaining
LIMITED DATA, PARTIAL SEASON and excluded-appearance warnings.

`freeze_reference` creates a versioned, fingerprinted snapshot of input binding,
policy, exact member inputs, IDs, counts, fixture scopes, means and sample SDs.
`score_players` applies that supplied snapshot without changing it. CLI replay
also verifies that its frozen membership belongs to the same eligible input
snapshot; it does not admit recipients as new reference members.

All five transforms use `clip(65 + 10 * ((x-mean)/sample_sd), 1, 99)` via the
existing pure FIFA helper. Exact rational metric inputs and unrounded float
scores/z values are retained. Zero variance, insufficient members, missing or
zero denominators, absent measurements and unsupported groups fail closed.
Reference ties use average ascending rank percentiles. Unseen values use the
frozen proportion strictly below the value. The percentile policy is explicit
and does not affect the FIFA transform.

## Reproduction and artifacts

Each output directory must be new. Existing results and evidence are never
overwritten. The main outputs are raw facts, canonical measurements, private
scores, frozen references, coverage summary, validation and hash manifest.

```powershell
python -B -m scripts.score_private_five_attributes --output data/derived/private-five-attribute-v2
python -B -m scripts.score_private_five_attributes --output data/derived/private-five-attribute-v2-replay --baseline data/derived/private-five-attribute-v2/frozen-reference.json
python -B -m scripts.validate_private_five_attributes --input data/derived/private-five-attribute-v2 --replay data/derived/private-five-attribute-v2-replay --tests data/validation/private-five-attribute-v2/tests.xml --output data/validation/private-five-attribute-v2/package-validation.json
```

The final validator compares full artifact/manifest hashes between original and
frozen replay, checks the existing measurement helper formulas, position and
reference exclusions, source/code bindings and regression results, then writes
the private report with real-player examples. It does not rerun event filtering
or source verification. The main run separately checks raw-count conservation,
reversed-input determinism, Joseph aggregate parity and rejection by both existing
delivery contracts.

Official integration remains separate: record individual-formula, population,
source/exposure/scope and proxy-label approvals, then add an approved adapter
through existing admission gates and a versioned delivery contract. Website card
wiring must carry sample, missingness and Bundesliga labels. OVR, tiers and
archetypes remain separate decisions. No existing gate or frontend file changes
are part of this experiment.
