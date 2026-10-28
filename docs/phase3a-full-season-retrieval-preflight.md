# Phase 3A: full-season evidence and controlled retrieval preflight

October 27, 2026 (America/Chicago). Offline review at `integration-foundation`,
HEAD `96b3989e09d1349ed5313b0d7b1ec6471ae7e21a`. No network authorization was
used. No retrieval command below was executed. No rating was calculated or
exported. This report and its exact ID queue are new review documents.

## 1. Exact inventory and retained evidence

`docs/phase3a-pending-source-inventory.json` contains every provider ID, every
delivered ID, every retained ID, every pending ID grouped by competition/season,
and all 189 ordered batches. Arrays contain exact IDs, not inferred ranges.
All four competitions use season ID 27, `2015/2016`.

| Competition (provider ID) | Provider | Delivered | Retained original pairs | Pending |
|---|---:|---:|---|---:|
| La Liga (11) | 380 | 380 | 265958, 266961 | 378 |
| Premier League (2) | 380 | 380 | 3753983, 3754217 | 378 |
| Serie A (12) | 380 | 379 | 3879549, 3879594 | 378 |
| Ligue 1 (7) | 377 | 377 | 3829416, 3901262 | 375 |
| Total | 1,517 | 1,516 | 8 | 1,509 |

The queue orders leagues as above, IDs ascending within each league, and packs
eight across league boundaries. It has 188 batches of eight and one of five.
Keeping competitions entirely separate instead would require 192 batches.
Batch 1 is La Liga: 265839, 265894, 265944, 266056, 266106, 266149, 266160,
266166. Batch 189 is Ligue 1: 3901258, 3901259, 3901260, 3901261, 3901263.

3879594 (AC Milan vs Chievo) already has both original documents. It is excluded
from every acquisition batch and remains
`pending_team_approval_missing_delivered_fixture` in the original manifest.
Its records may be reviewed offline, but cannot be appended to delivered
aggregates. Inclusion requires a separately approved rebuild and reconciliation.
Ligue 1's three unlisted historical schedule slots have no established provider
IDs; none is invented or added to this queue.

Reused immutable inputs:

- `data/source-evidence/phase1-2026-10-27/`: four `matches-*.json` original fixture
  documents and their request sidecars, revision/selection, eight `events-ID.json`
  and eight `lineups-ID.json` payloads with request sidecars, normalized fixtures,
  fixture comparison, retained specifications, and original artifact inventory.
- `data/source-evidence/phase1b-2026-10-27/analysis/retrieval-manifest.json`:
  SHA256 `756d0cbe3fdcbfb9c753da97f861004dccc44db271f863d035bf58fda324cfa2`;
  pinned provider revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.
- Phase 1B `analysis/offline-store`, `final-replay.json`, contradiction
  investigations, and `season-readiness.json`. Existing store journal accounting
  is zero successes, zero failures, zero interrupted requests: original pairs
  are manifest bindings, not new store downloads. Sixteen retained report
  versions cover eight matches; report versions are not extra source pairs.
- Arpit's reviewed 1,517-row fixture Parquet and separate provenance sidecar.
  Its fixture associations agree with the original provider snapshot; unknown
  retrieval endpoint/revision fields are not filled from another acquisition.
- Read-only delivered match metadata and lineups for observed fixture/appearance
  scope; corrected delivered minute/recovery tables for qualification context.

The two existing artifact inventories were checked: all 91 Phase 1 entries and
30 Phase 1B entries match their declared SHA256. The inventories themselves and
other preserved inputs are also covered by the before/after integrity check.

## 2. Workflow readiness and implementation assessment

**Ready for explicitly authorized, serial, bounded evidence acquisition. No
backend fixes are necessary for that operating mode.** Use
`scripts/source_verification_batch.py`; this preflight adds no retrieval engine,
transport, scoring path, policy relaxation, or source-data replacement.

`load_manifest` validates independently retained, SHA-bound original fixture
documents, unique exact positive int64 match IDs, competition/season membership,
immutable revision, and declared payload endpoint/revision. `bound_document`
checks original bytes, the JSON array shape and timezone-aware retrieval date.
Actor, roster, team, tactical and substitution identities are checked by
`statsbomb_participation.adapt_match`. Exact period clocks and source-supported
transitions feed `participation_intervals.validate_participation`. Supported
stoppage time is included, halftime and supported temporary gaps are excluded;
valid position allocation retains exact rational durations. Contradictions
quarantine aggregate exposure and position minutes; unsupported cases withhold.

Network execution requires explicit match IDs, `--allow-network`, a dedicated
store, and `--batch-limit` 1..8; selected count must fit that limit. Offline
verification allows at most 64 IDs. The manifest default is a read-only dry run.
The store binds its marker to the exact manifest SHA. Original payload objects,
request journals and reports use exclusive/content-addressed writes. Successful
payload bindings are fingerprint checked before reuse. Report keys bind source,
fixture, clock interpretation and adapter/validator/workflow code fingerprints.
No completed data are overwritten. All production/publication flags stay false.

Operating limits to retain:

- One serial process per store; there is no tested multi-writer locking contract.
- No automatic retries, backoff, pacing, Retry-After handling or scheduler.
  Transport timeout is 45 seconds per response, with a 20 MiB response cap.
  The code records exceptions and proceeds through the remainder of that bounded
  batch; a stop is not an immediate cancellation of every request in progress.
- Journal files are rescanned by match binding lookup; a populated store may
  become slower as it grows. Season throughput and live rate limits were not
  benchmarked. Use selected-ID dry runs when resuming a batch; avoid repeatedly
  scanning all 1,517 matches against a large journal. This is a performance
  limitation, not permission to discard audit records or bypass integrity checks.
- Request journal success means valid original JSON bytes were retained; match
  adapter review can subsequently reject the pair. HTTP response headers/status
  are not retained by this newer transport, unlike Phase 1 request sidecars.
  Endpoint, source revision, retrieval date, digest and failures remain recorded.
  Do not claim a recovered HTTP status from a generic failure string.
- CLI exit 1 covers source rejection, incomplete pairs, integrity conflict and
  contradictory appearances; exit 2 covers rejected invocation/store inputs.
  Exit 0 can still include incomplete player exposure. Inspect report warnings
  and every active status before authorizing continuation. Acquisition success
  never means complete season evidence or certified exposure.

## 3. Acquisition cost and failure preflight

1,509 pending pairs imply up to **3,018 new payload requests without retries**.
At batch size eight there are **189 bounded invocations** (16 requests per full
batch, ten for the last). At size one there are 1,509 invocations. A mixed or
smaller-batch schedule lies between those bounds; failed attempts add requests.
Neither eight retained pairs nor 549 qualified contexts reduces the listed
full-provider acquisition scope.

Measured eight-pair payload sample:

| Payload | Retained sample total | Observed per-match range | Rough pending projection |
|---|---:|---:|---:|
| Original events | 24,507,823 bytes | 2,658,952–3,387,058 bytes | about 4.62 GB |
| Original lineups | 158,330 bytes | 16,656–23,985 bytes | about 29.9 MB |

Projections multiply the eight-match mean by 1,509; the pilot was deliberately
selected for special cases, so these are planning estimates, not precise season
download sizes or statistical confidence bounds. Decimal GB/MB are used.
Reports, journal files, filesystem overhead, quarantined/orphan objects and
future validator versions add storage. The 16 existing report versions occupy
6,044,954 bytes; their version mix is not a measured full-season report size.
The response cap implies at most about 63.3 GB of newly accepted payload bytes
for 3,018 unique capped responses, before overhead; it is a defensive ceiling,
not a realistic forecast. Refresh/retries/orphans can increase total storage.
Check free space for payloads plus review output before a future acquisition.

Rate limits, DNS failures, connection resets, timeouts, unavailable pinned URLs,
HTTP errors and oversized/malformed documents remain possible. No live request
or availability probe was performed; no precise rate, ETA or failure percentage
is asserted. On repeated failures stop, review the journal and authorize a later
retry rather than creating a retry storm or changing revisions automatically.

For a provider-listed fixture with unavailable payloads, the missing document
remains missing and the pair is incomplete. The fixture is not dropped from the
denominator inventory. For an unlisted fixture, the manifest refuses an invented
ID. A new verified inventory/revision would need separate review and a new store,
not mutation of this store's manifest. Unknown actors, identity conflicts,
unsupported boundaries and contradictory source timelines remain withheld even
after successful retrieval. Refetching the same revision does not repair them.

## 4. Path to real scoring and remaining dependencies

The current sample has **210 structurally valid and 14 contradictory active
appearances**, 79 unused bench entries and 196 distinct actor/club/league/season
contexts. It touches 64 of 549 delivered-table-qualified contexts: 61 have a valid
sample and six a contradictory sample (overlap allowed). There are **zero
validated season-exposure-eligible or production-certified contexts**.

| Stage | Automatic evidence checks | Review/approval and unresolved requirements |
|---|---|---|
| Identity and full appearance inventory | Exact actor/team/match IDs, roster/event/fixture associations, duplicate/context checks, original fingerprints | Independent canonical identity support, provenance attestation, complete appearance inventory and source completeness; observed lineup presence is insufficient |
| Playing and position minutes | Source transitions, agreeing period boundaries, exact elapsed durations, temporary gaps, overlap/reversal/dismissal quarantine, position allocation | Approve season exposure convention and role allocation; resolve or approve handling of all incomplete/conflicting appearances; preserve delivered minutes |
| Numerators and per90 | Retain unfiltered events, reconcile exact actor/match scopes, raw tackle/interception/recovery counts and press attempts/successes; recompute count / supported minutes * 90 | Independently verify metric semantics, event coverage/reportability and same full-season numerator/denominator scope; retrieval and fixture agreement alone do not certify counts |
| 900-minute eligibility | Apply at least 900 validated minutes after full-scope identity/exposure/reportability gates; reject missing/incompatible exposure | Delivered-table qualification is separate; the 549 can change after a future approved rebuild; press thresholds remain candidate policy |
| MID/CB pools | DM/CM/MID map to MID, CB stays separate; four-league scope, unique player-season reference membership, scope compatibility and usable variance | Approve role/transfer membership, complete cohort coverage and final reference attribution; unknown roles stay unavailable |
| Transfers | Sum compatible raw counts and supported minutes, recalculate rates, reject duplicate match contributions and repeated reference members | Approve within/cross-league aggregation and nominated reference context; current transfer implementation accepts synthetic evidence only and needs a separately reviewed real-evidence path |
| Individual FIFA attributes | Existing candidate defensive component and press transforms and distribution checks can be tested offline | Approve individual defensive formula and final press transform/thresholds/pools; D3A aggregate DRI approval does not approve individual component ratings |
| Archetypes | Use highest unrounded percentile and positional tie order; Gold >=90, Silver >=75 and <90 | Only after approved verified component percentiles; no rating-to-percentile substitution; line breaking still lacks approved metric/evidence/policy |
| Versioned delivery | Strict IDs, context/source lineage, null unavailable fields, deterministic serialization and frontend parsing | Existing `soccer-rating-delivery/v1` numeric path is synthetic-only; design/review a production evidence contract and obtain publication authorization; OVR policy remains unresolved |

The candidate defensive formula is component per90 followed by
`clip(65 + 10 * (x - mean(x)) / sample_std(x, ddof=1), 1, 99)`.
Each component uses its own eligible distribution. Press candidates use
`100 * successes / attempts` with the analogous sample-z FIFA transform;
ratios are weighted by attempts. Ranking uses ascending average rank / n * 100,
independently of FIFA rating. Singleton/constant pools withhold. These are
documented candidate mathematics, not approval to score real players.

Transfer actors 3057 (Newcastle/Swansea) and 13286 (Lorient/Sunderland) retain
separate original contexts until an aggregation policy and real evidence path
are approved. Do not average their club per90s, percentiles or ratings.

`season_readiness` intentionally never asserts complete-season production
trust, even when supplied all match reports; its context coverage/exposure gates
remain conservative. `rating_pipeline.readiness_rating_delivery` deliberately
produces withheld diagnostic records and rejects edited certification flags.
Full acquisition therefore still requires a reviewed season certification and
real rating delivery implementation. Do not flip flags or relax these gates.

Team decisions still needed: provenance review; exposure and position/role
policy; contradictions and unknown transitions; historical Ligue 1 coverage;
3879594 inclusion in a separate rebuild; transfer/reference attribution;
individual defensive/press policies; line-breaking definition; OVR; publication.
Some facts may remain unavailable despite retrieval: original historical fetch
outcomes, missing provider fixtures, contradictory timelines and video coverage.
Scoring policy approval is not needed merely to acquire original evidence if
the team explicitly authorizes that isolated research scope, but it is required
before any real scoring/release.

## 5. Exact first command and controlled continuation

Run from the repository root only **after explicit authorization for these eight
IDs**. The dedicated destination does not currently exist; it preserves the
original Phase 1B offline store and reuses original manifest-bound pilot files.

```powershell
python -B -m scripts.source_verification_batch --manifest data/source-evidence/phase1b-2026-10-27/analysis/retrieval-manifest.json --allow-network --batch-limit 8 --match-ids 265839 265894 265944 266056 266106 266149 266160 266166 --destination data/source-evidence/phase3a-controlled-store
```

The following reusable shell function selects an exact queued batch, verifies
the reviewed queue and manifest fingerprints and delegates all retrieval to the
existing CLI. Without the switch it runs a selected-ID offline dry run. It does
not create a second retrieval framework or issue an unbounded loop. Defining the
function alone grants no network authorization. The switch may be used only
after approval of the exact selected batch, or an explicit bounded sequence.

```powershell
function Invoke-PlannedSourceBatch {
    param(
        [Parameter(Mandatory)][ValidateRange(1,189)][int]$BatchNumber,
        [switch]$ExecuteAuthorized
    )
    $queuePath = 'docs/phase3a-pending-source-inventory.json'
    $expectedQueue = 'b5d0e09c9321752adfbff1a55a8d22ecf7ad637a774e0e8b658a28af220351b8'
    if ((Get-FileHash -LiteralPath $queuePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedQueue) {
        throw 'Reviewed queue changed; stop for review.'
    }
    $queue = Get-Content -LiteralPath $queuePath -Raw | ConvertFrom-Json
    if ((Get-FileHash -LiteralPath $queue.manifest_path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $queue.manifest_sha256) {
        throw 'Manifest changed; stop for review.'
    }
    $batch = $queue.batches[$BatchNumber - 1]
    [int[]]$ids = @($batch.match_ids)
    if ($ids.Count -lt 1 -or $ids.Count -gt 8 -or $ids -contains 3879594) {
        throw 'Invalid or policy-pending batch.'
    }
    $cliArgs = @('-B', '-m', 'scripts.source_verification_batch',
        '--manifest', $queue.manifest_path,
        '--destination', 'data/source-evidence/phase3a-controlled-store',
        '--match-ids') + @($ids | ForEach-Object { [string]$_ })
    if ($ExecuteAuthorized) {
        $cliArgs += @('--allow-network', '--batch-limit', [string]$ids.Count)
    }
    $lines = @(& python @cliArgs)
    $resultCode = $LASTEXITCODE
    $lines | Out-Host
    if ($resultCode -ne 0) { throw "Batch $BatchNumber stopped with exit $resultCode; inspect and resume this batch." }
    if ($ExecuteAuthorized) {
        foreach ($result in (($lines -join "`n") | ConvertFrom-Json)) {
            $report = Get-Content -LiteralPath $result.report_path -Raw | ConvertFrom-Json
            if ($report.artifact_validation -ne 'BYTE_BOUND_SOURCE_SCHEMA_REVIEWED') {
                throw 'Source review did not pass; stop.'
            }
            foreach ($status in $report.active_status_counts.PSObject.Properties) {
                if ($status.Name -ne 'STRUCTURALLY_VALID' -and $status.Value -gt 0) {
                    throw 'Active appearance unresolved; inspect report before continuation.'
                }
            }
            if (@($report.warnings).Count -gt 0) { throw 'Source warnings require review before continuation.' }
        }
        Write-Host "Batch $BatchNumber retained and reviewed. Season/scoring gates remain unresolved."
    }
}

# Read-only preflight, safe without retrieval authorization:
Invoke-PlannedSourceBatch -BatchNumber 1

# Future use only after this exact batch is authorized:
# Invoke-PlannedSourceBatch -BatchNumber 1 -ExecuteAuthorized
# Invoke-PlannedSourceBatch -BatchNumber 2 -ExecuteAuthorized
```

The queue eliminates manual ID composition for hundreds of commands. If a future
authorization explicitly covers a bounded range (for example batches 2–4), a
serial `foreach ($n in 2..4) { Invoke-PlannedSourceBatch -BatchNumber $n
-ExecuteAuthorized }` is possible; an exception stops the loop. Do not infer
range/full-season approval from approval of batch 1. Keep one process per store.
Keep the current batch number as the resume cursor until its results are reviewed.
After unresolved evidence is reviewed, continuation with later batches needs
explicit authorization; never change source evidence to force a clean result.

## 6. Resume and failures

Repeat exactly the same authorized batch command, same manifest and destination,
without `--refresh`. Successful, SHA-checked event/lineup documents are reused;
only missing kinds are fetched. A completed pair with a matching review is
skipped. Interruption during a request leaves an outcome-unknown journal start;
resume does not reinterpret it as failure or success. Only finalized successful
bindings are accepted; orphan/partial objects are not automatically promoted.

Before a retry use the function without its switch for that batch. Dry run
reports pair presence, integrity conflicts and aggregate request accounting;
pair presence does not certify its player intervals. Inspect per-request journal
entries (`match_id`, `kind`, `outcome`, error/binding) and the returned immutable
`report_path` for match/appearance outcomes. A failed request may coexist with
a successful other document. Unchanged rejected pairs will be re-reviewed, not
silently repaired or automatically refetched. Do not delete reports/journals to
clear a failure, use another revision, or enable `--refresh` as a generic retry.

Exit 1/2, source warnings, any nonvalid active appearance or unexpected inventory
change pauses continuation for review. A reviewer can decide to preserve
quarantine and authorize acquisition of another batch; no season totals or
production pool memberships may be inferred from that decision. No automatic
retry loop or implicit production ingest is provided.

Offline report replay can use `--verify` with explicit IDs, no network switch,
and the dedicated future store. Rebuild per-context readiness from independently
reviewed report versions using the existing `season_readiness` accountant,
retaining source bindings and manifest digest; do not count multiple report
versions as different matches. `audit_phase1b.py` remains a pilot replay tool:
it selects the original eight pairs, so rerunning it does not account for a
future full-store acquisition by itself. A later full-season review must pass
the selected full-store reports to the existing accountant without changing its
noncertifying semantics.

## 7. Validation, preservation and recommendation

| Offline check | Result |
|---|---|
| Full Python suite, warnings as errors | 849 tests passed, no skips, 146.225 seconds |
| Frontend JavaScript suite | 154 passed, zero failed or skipped |
| Fresh isolated eight-match replay outside the repository | 210 structurally valid / 14 contradictory active appearances; zero requests |
| Immediate replay/resume | All eight reports reused; zero journal requests |
| Exact queue reconciliation | All 1,509 unique pending IDs equal manifest IDs minus eight retained pairs; every batch has 1..8 IDs; SHA-bound manifest and policy-pending exclusion checked |
| Documented PowerShell helper | Syntax parsed successfully; batch 1 offline dry run reported eight pending pairs, zero conflicts, network disabled; no retrieval store created |
| Existing Phase 1 / Phase 1B inventories | All 91 / 30 declared artifact hashes matched |
| Preservation baseline comparison | All 136 input files byte-identical; no additions/deletions in source-evidence or validation; all 12 local Parquets (11 protected plus Arpit fixture snapshot) unchanged; original untracked M4A checklist unchanged |
| Git and whitespace | `git diff --check` and new-document trailing whitespace checks passed; index empty; no tracked changes |

The before/after integrity baseline and validation summary are local artifacts at
`C:/Users/Ayush/.codex/visualizations/2026/10/28/01a1803f-719e-7233-acbc-c9910b9fdc7b/`
(`phase3a-integrity-before.json`, `phase3a-validation.json`). Fresh replay reports
are isolated there under `phase3a-offline-replay/`; preserved evidence directories
received no writes. The helper check exercised only its offline branch, not a
live transport. Existing synthetic fake-transport tests cover retrieval gates,
partial failure, interruption/resume, changed bytes and quarantine. No frontend
build was needed because no implementation or frontend file changed.

Git remains `integration-foundation` at `96b3989`. The six original untracked
status entries remain: three `data/processed/` Parquets, `data/source-evidence/`,
`data/validation/` and `docs/m4a-team-approval-checklist.md`. Only two additional
untracked documents were created: this report and the exact ID inventory/queue.
No staging, commit, push, branch/worktree operation, merge, reset, rebase, clean,
deployment, delivered-table change, official rating export or network retrieval
was performed.

**Conditional GO for authorizing serial 1–8-match evidence batches using the
reviewed manifest and queue, starting with batch 1.** Review the first bounded
batch before granting a larger explicitly bounded sequence. There is no live
season-scale performance/availability proof. **NO-GO for unattended bulk
retrieval under the current authorization, full-season certification, official
ratings or publication.** This task authorizes none of those actions. Complete
retrieval alone will not resolve the season and policy dependencies above.
