# Phase 1: recovered source evidence and bounded real-data verification

October 27, 2026. Four independent provider fixture lists and eight original
match event/lineup pairs were retrieved. This establishes that independent
source records are obtainable. It does **not** certify any season context for
production: the existing identity, exposure, component and policy gates remain.

## Source preflight and provenance

Contributor code inspected read-only: `origin/arpit-dev:src/ingestion/fetch_normal.py`
and `src/ingestion/fetch_lineups.py`. The former uses `statsbombpy.sb.competitions`,
`matches`, and `events`, retains only six action types, and does not archive the
fixture response. The latter flattens original lineup position stints, obtaining
match IDs from delivered events. Neither script supplies credentials explicitly.
Historical installed client versions, environment configuration and request logs
remain unavailable; current client behavior does not reconstruct those facts.

The public client interface was verified from pinned `statsbombpy` source:
`dc4a2461b7406df451e1bbb549e56d8d963cb5d7` (October 20, 2026).
`client-config.py`, `client-public.py`, and `client-sb.py` are retained in the
evidence directory. Public paths are:

- `data/competitions.json`: competition/season ID pairs and coverage metadata.
- `data/matches/{competition_id}/{season_id}.json`: provider-listed match objects,
  team IDs/names, competition/season, dates and available version metadata.
- `data/events/{match_id}.json`: original, unfiltered event arrays.
- `data/lineups/{match_id}.json`: original team sheets, actor IDs/names, cards and
  observed position stint objects.

The base for this retrieval is
`https://raw.githubusercontent.com/statsbomb/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/`.
The commit is dated September 7, 2026. The old repository URL redirects to
`hudl/open-data`; pinned raw paths under `statsbomb` worked. Retrieval started
October 27, 2026 at 22:49:32 UTC. Every remote request has an adjacent
`.request.json` containing URL, timestamp, revision, response headers/status,
context, byte size and SHA256. These are **new request records**, never old fetch
logs. All 35 current requests succeeded; 29,395,823 original response bytes were
retained, including documentation and client source.
The initial sandbox-only preflight failed DNS resolution; the authorized network
preflight and subsequent bounded retrieval succeeded. `preflight-access.json`
records that distinction without inventing an HTTP response for a DNS failure.

Target competition IDs are La Liga **11**, Premier League **2**, Serie A **12**,
Ligue 1 **7**; season ID **27**, name `2015/2016`, for all four. Match metadata
usually reports data version `1.1.0`, shot and XY fidelity versions `2`.
One Ligue 1 and one Serie A record have empty version metadata; no version is
invented for these. Client API fallback version constants describe a separate
service interface and are not asserted as versions of these public JSON files.

Retained provider documentation includes Events v4.0.0, Lineups v2.0.0,
Competitions v2.0.0, Matches v3.0.0, Data Specification v1.1, 360 v1.0.0,
README and LICENSE. The old lineup specification documents roster identity but
does **not** document the position-stint extension seen in the actual sample.
Stint fields and reasons here are observed original values, corroborated where
possible by documented event types; they are not inferred from another calculator.

Public access required no credentials. README describes research use and asks
for StatsBomb attribution/logo for shared analysis. The retained user agreement
also sets restrictions on redistribution and commercial exploitation, disclaims
completeness, and discusses registration. It must be consulted before any later
sharing or commercial use. This session performs local analysis only, with no
publication or redistribution. Provider ownership attribution is retained.

## D3H: actual fixture comparison

`scripts/audit_fixture_evidence.py` was run against the fresh normalized snapshot,
its byte-bound provenance, existing event-derived metadata and delivered lineups.
The JSON report is `fixture-comparison.json`. `phase1-findings.json` separately
contains the exact sorted provider and observed ID arrays for every league.

| League | Provider IDs | Observed IDs | Missing expected IDs | Unexpected IDs |
|---|---:|---:|---|---|
| La Liga | 380 | 380 | none | none |
| Premier League | 380 | 380 | none | none |
| Serie A | 380 | 379 | 3879594 | none |
| Ligue 1 | 377 | 377 | none against provider list | none |

There are no fixture context, team, or lineup context disagreements. The missing
Serie A fixture has no local lineup records either. All historical events/lineups
acquisition outcomes remain unknown: 1,517 expected fixtures per stage. No new
request ledger was passed as a historical acquisition ledger. The reported
connection reset remains a contributor claim, not an independently recovered log.

**3879594 is AC Milan versus Chievo**, explicitly listed in the fresh provider
snapshot. Both its events (3,664 records) and original lineups were retrieved
successfully. The local omission is independently corroborated; its historical
cause is not. None of these recovered records was inserted into delivered data.

**Ligue 1 public coverage is 377, not 380.** A double-round-robin comparison of
the provider's 20 club names implies unlisted home/away schedule slots Bastia–
Gazelec Ajaccio, Saint-Etienne–Paris Saint-Germain, and Troyes–Bordeaux (exact
provider spellings retained in JSON). These are schedule-slot inferences, not
independent fixture records: no provider IDs, dates, cancellations or failure
causes are fabricated. The four-list retrieval cannot identify missing provider
IDs that the provider never lists.

D3H intentionally retains `INDEPENDENCE REVIEW REQUIRED` and false trust flags.
Direct versioned retrieval supplies independently obtained records for review;
it does not silently grant a D1 `VERIFIED_SOURCE_EVIDENCE` attestation.

## Adapter and explicit clock interpretation

`src/statsbomb_participation.py` is pure and separate from scoring and delivered
minutes. `SourceDocument` retains original bytes, source URL, revision and SHA256.
The adapter checks unique fixture membership, exact positive actor/team IDs,
fixture/roster/event team names, actor names and roster associations, including
substitution replacements and tactical lineups. Duplicate events/actors,
cross-team identities and unsupported periods reject. It does not reconstruct
or promote a season-level identity crosswalk.

Provider documentation identifies periods 1/2 as the regulation halves, event
timestamps at millisecond precision, and minute resets to 45 at halftime.
In every sampled event, the timestamp equals the period-local clock and its
integer part agrees with `minute/second` using offsets 0 and 45. Original
paired Half Start events are at zero. The adapter checks this relationship for
every event; disagreement rejects instead of choosing one clock.

Lineup `MM:SS` plus period is used to locate an actor/team-specific original
transition; elapsed time uses that event's original millisecond timestamp.
Starting XI, Tactical Shift, Substitution (including replacement ID), Player
Off/On, and documented red/second-yellow foul events map to D3J categories.
Position changes require the new tactical position to agree. Unsupported
reasons or ambiguous/missing matching transitions remain unknown, preventing
an aggregate duration. Raw position JSON retains original clocks, periods,
position IDs/names and reason text alongside immutable provenance references.

An open Final Whistle endpoint is supported only by agreeing team Half End
timestamps in the final regulation period. Duplicate agreeing team records are
normal; disagreements are never resolved by taking a maximum. Half Start/End
attributes are conservatively withheld because documented early video end,
late video start and match suspension can invalidate a whistle interpretation.
No such flags occurred in the pilot. Unknown boundary attributes also withhold.
No event maximum, arbitrary minute 90 or filtered action establishes a whistle.

Cross-period exposure sums active portions of both halves, includes observed
stoppage time and excludes the halftime break. Player Off/On gaps are retained
and excluded. Overlapping or reversed intervals quarantine the entire supplied
player-match total. Extra time/shootouts, permanent non-substitution exits and
off-camera reasons without corroborating transitions are not silently mapped.
This arithmetic convention is a documented pilot interpretation; choosing the
season scoring exposure policy remains a team decision.

## D3J: real bounded reconstruction

All eight selected match pairs are real evidence; failure-case tests are synthetic.
There was no season event download or repeated delivered event scan.

| Match | Evidence selection | Original events | Valid active appearances | Contradictory |
|---|---|---:|---:|---:|
| 3879594 | missing Serie A fixture | 3,664 | 28 | 0 |
| 3753983 | ordinary structure and post-90 substitute | 3,715 | 28 | 0 |
| 3754217 | local reversed periods, dismissal, temporary absence | 3,732 | 24 | 4 |
| 3829416 | Ligue 1 reversed periods | 3,366 | 26 | 2 |
| 3879549 | Serie A reversed periods and anomalous exit reason | 3,087 | 25 | 3 |
| 265958 | temporary absence/return | 3,359 | 28 | 0 |
| 266961 | return after minute 90 | 3,915 | 28 | 0 |
| 3901262 | complex eight-position-stint players | 3,800 | 28 | 0 |
| Total | eight original event/lineup pairs | 28,638 | 215 | 9 |

There are also 79 bench roster entries with no position stints: these are not
asserted appearances or fabricated zero-minute players. Among active appearances,
215 are source-supported and structurally valid conditional on the recorded
semantics; nine have other contradictory evidence. None is a source-unverified
synthetic success presented as real evidence. Missing boundary, missing transition,
identity conflict and structurally-consistent-only paths are separately retained
by the validator/adapter and covered by synthetic regressions. The pilot has no
standalone incomplete active appearance, but one contradictory appearance also
has an unsupported transition reason. All trust/publication flags remain false.

All local active position stints for the seven already-delivered samples match
fresh original source fields exactly, including the problematic rows. Original
actor IDs and names agree in those local records. The eighth match has 28 active
players absent from local match lineups. The sample touches 64 of the 549
table-qualified contexts; 62 have at least one valid sampled appearance. Neither
number establishes complete appearances, actor resolution, numerators or season
exposure for any of those contexts.

Seven temporary gaps occur in fully valid player collections; an eighth is
present in a contradictory collection whose total remains withheld. For match
265958/player 6867, the original off/on gap is 71.987 seconds; valid active
exposure is 5,488.285 seconds. For 3753983/player 3647, entry at 92:08 yields
116.639 supported seconds, whereas the contributor's clipped-90 arithmetic
would yield zero. Complex position changes in 3901262 validate without overlapping
time. All 215 valid pilot totals differ from the old integer-second clipped-90
arithmetic (differences 0.011 to 556.530 seconds); this is a comparison, never an
instruction to replace approved minutes.

Existing delivered minutes are season aggregates, so the review retains them
as context and compares the known contributor arithmetic on local-equivalent
stints at match level. It does not subtract a partial pilot from a season total
or claim an independently delivered per-match minutes artifact exists.

The nine quarantined appearances are 3754217: 3437, 3496, 3517, 6746;
3829416: 3230, 16462; 3879549: 6636, 7026, 7147. Eight have reversed-period
stints; overlap and transition issues coexist. In 3754217, the source puts a
Tactical Shift at first-half 47:40 before a second-half 45:12 Tactical Shift
in event index/period order, while lineup stints order these by displayed clock,
creating period reversals. Coquelin's lineup additionally claims participation
after his halftime substitution. This is upstream lineup evidence in conflict
with original event chronology, not an error fixed by refetching the same data.
`contradiction-review.json` retains raw stints and relevant original event
sequences for all nine. No automatic reordering, repair or identity reassignment
was applied. A separate event-sequence reconstruction can be reviewed next.

## Full-season feasibility and remaining blockers

The existing 549 table-qualified contexts have observed active roster records
across **all 1,516 locally observed target fixtures**. Seven are now sampled;
the eighth sample recovers the missing Serie A fixture. Thus the observed
appearance inventory still requires **1,509 additional original match pairs**
to use this same source-backed pilot workflow, not a few conveniently selected
matches. Exact IDs are retained in `participation-summary.json` and must be
reconciled against necessary actor/boundary records before any future retrieval.
No claim is made that all these pairs have been fetched or will be available.

That would mean up to 3,018 further payload requests if both events and lineups
were reobtained. Existing lineups already provide stable IDs and stint observations;
the larger necessity is original transition and whistle evidence. A narrower
future acquisition could retain only required original boundary/tactical/identity
records after reviewing complete per-match responses, subject to explicit scope
authorization and retained source integrity. The sampled mean projects about
4.62 GB of additional event JSON and 29.9 MB of lineup JSON; these are rough
sample-based byte estimates, not measured season totals or a retrieval commitment.

- **Technical:** the adapter currently supports only observed regulation clocks,
  exact corroborated transitions and unflagged agreeing boundaries. It fails
  closed for unknown cases; broader event-sequence reconstruction needs separate
  implementation and regression review.
- **Provider data:** the lineup contradictions persist in the original source.
  Three Ligue 1 schedule slots are absent from this provider inventory. Public
  records alone cannot establish player participation and metric numerators for
  fixtures whose original records are unavailable, or certify video completeness
  beyond recorded provider evidence.
- **Missing archives:** the delivery's historical success/failure/filter history
  cannot be reconstructed from a fresh snapshot. Current success does not prove
  the cause of an old omission.
- **Team policy:** explicit provenance review, exposure convention, treatment of
  provider contradictions/missing fixtures, transferred reference contexts and
  other approved scoring gates remain unresolved. No scoring formulas change.

Verification of **all 549 full-season contexts is not presently established**.
Source-backed verification of provider-covered records is technically feasible,
but even complete retrieval does not solve provider omissions, contradictory
lineup stints, the historical audit trail or policy decisions. The exact next
action with the highest immediate evidence value is to reconstruct a separate
candidate timeline from the already-retained original event indices/periods for
3754217's four quarantined actors, then review it against substitutions, tactical
positions and whistles. This tests whether the provider-lineup blocker can be
removed without further retrieval or modifying delivered data. Resolve that
method and the coverage/exposure decisions before authorizing a larger request.

## Files, replay, validation and preservation

New implementation files are `scripts/recover_source_sample.py`,
`scripts/validate_source_sample.py`, `src/statsbomb_participation.py`,
`tests/test_statsbomb_participation.py`, and this report. No tracked file was edited.

All new source and review artifacts are under
`data/source-evidence/phase1-2026-10-27/`. `artifact-inventory.json` enumerates
every evidence artifact with exact relative path, size, SHA256 and schema/category.
It includes original competitions, four match lists, eight event arrays, eight
lineup arrays, all request sidecars, provider documents/client source, normalized
fixtures/provenance, selection/rationale, D3H comparison, eight participation
reviews, participation summary, findings, contradiction extracts and validation
record. The inventory excludes itself by definition.

The retrieval utility has explicit inventory/records modes, a maximum eight-ID
sample, response byte caps and exclusive creation. It refuses an existing root
or sample and never retries into existing paths. The review utility checks source
bytes against their request fingerprints before adapting; review writes are also
exclusive. Re-running against the same output directory intentionally fails.
To inspect without any new files, call the pure adapter using retained bytes.
D3H remains read-only and can be replayed using the arguments in its report.

Regression tests cover realistic source schema, missing/malformed fields, exact
stable identities, substituted actors, bench records, duplicate events, periods,
missing/flagged/disagreeing whistles, post-90 activity, temporary/permanent exits,
cross-period sums, position changes, overlaps/reversals, deterministic provenance
and input immutability. All failure fixtures are synthetic and explicitly labeled.
Final commands/results and protected fingerprints are in `validation-record.json`:
**32 focused Python tests, 764 full Python tests, and 112 frontend JavaScript
tests pass**. Final adapter replay reproduces 215 valid/nine contradictory active
appearances. `git diff --check` and new Python syntax/whitespace checks pass.
All **11 protected Parquets plus the M4A checklist** match their pre-session
SHA256 fingerprints. The tracked diff and staging area are empty; only the five
new implementation/report files, isolated evidence and pre-existing untracked
inputs appear in status.

Branch remains `integration-foundation`; HEAD remains
`20d690ee6d017fc689cec09fff088d8d7f524c07`. All 11 protected Parquets and the M4A
checklist must match the pre-session SHA256 manifest. The pre-existing untracked
dataset/checklist entries remain untracked. No delivered dataset, scoring formula,
gate, frontend, branch or worktree was modified. No staging, commits, pushes,
merges, rebases, resets, clean operations or deployments were performed.
