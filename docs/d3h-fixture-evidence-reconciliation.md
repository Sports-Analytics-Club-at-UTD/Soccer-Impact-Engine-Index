# D3H — offline fixture and acquisition evidence reconciliation

October 27, 2026. Offline comparison capability; no real independent snapshot
has been supplied or verified. Production scoring remains blocked.

## Purpose and trust boundary

`scripts/audit_fixture_evidence.py` compares explicitly supplied local fixture,
delivered match metadata, lineup and optional acquisition records. It never
reads the events dataset, downloads data, computes minutes/metrics/ratings,
constructs trusted identity evidence, writes datasets, or selects reference
players. Results are deterministic terminal JSON summaries only.

A provenance sidecar documents the provider, source reference, revision/date,
ID namespace, scope and SHA256 of the supplied artifact. The reader checks the
fingerprint against actual bytes. This binds a declaration to a file; it does
not authenticate its author, upstream origin or independence. A provider label,
an `origin` declaration, a coverage claim or two agreeing tables never grant
`VERIFIED_SOURCE_EVIDENCE`. There is deliberately no CLI trust override.

The status **independently supported fixture record** remains **NOT ESTABLISHED
BY THIS TOOL**. A supplied provider-record snapshot is labeled **DOCUMENTED
FIXTURE SNAPSHOT — INDEPENDENCE REVIEW REQUIRED**. External review must establish
its source independently of the delivered events before its associations can
support D1's existing verified evidence gate. This comparator does not perform
or replace that review. Actor identities, metric coverage, playing-time exposure,
full-season verification and production readiness always remain false here.

## Accepted input formats

All table paths are explicit local `.parquet` files or `.json` record arrays.
Parquet reads project only the columns below. Inputs are capped at 200,000 rows;
JSON files are additionally capped at 16 MiB. Oversized event datasets reject
rather than initiate a full scan. The reader rejects duplicate JSON keys and
nonfinite JSON constants. Metadata tables may include other leagues/seasons;
their contexts are validated, while league summaries select the four target
2015/2016 leagues. Snapshot records must belong to its declared target scope.

| Input | Required columns | Optional columns |
|---|---|---|
| Fixture snapshot | `match_id, competition_name, season_name` | `home_team, away_team` |
| Delivered metadata | `match_id, competition_name, season_name` | `home_team, away_team` |
| Lineups | `match_id, team` | Both `competition_name, season_name` together |
| Acquisition ledger | `match_id, competition_name, season_name, stage, outcome, evidence_reference` | `reason` |

Use StatsBomb match IDs. The existing M2A validator enforces positive exact
signed-int64 IDs; JSON IDs should be integer literals, never strings or unsafe
floating-point approximations. Other provider ID namespaces require a separately
validated mapping upstream; this tool does not infer equivalent fixtures.

Supply both home/away teams or neither (two nulls are also allowed). Available
teams are checked against each other and the lineup's distinct team set. Missing
teams are explicitly unassessed. Only the existing two M2A team aliases apply;
there is no fuzzy matching. Context-free lineups cannot independently validate
competition/season. Repeated player/stint rows are normal, not fixture duplicates.
Lineup presence establishes roster-record presence, not participation or identity.

For example, this is a **synthetic** fixture-array fragment:

```json
[
  {
    "match_id": 3879594,
    "competition_name": "Serie A",
    "season_name": "2015/2016",
    "home_team": null,
    "away_team": null
  }
]
```

This example tests the reported ID; it supplies no real independent fixture
record or team association.

## Provenance sidecars

`--snapshot-provenance` is required with `--snapshot`. Its JSON object has these
exact fields (only the noted alternatives are optional):

```json
{
  "schema_version": "fixture-evidence/v1",
  "artifact_kind": "fixture_snapshot",
  "provider": "Invented provider for synthetic example",
  "source_reference": "invented-fixtures/test-only",
  "origin": "synthetic",
  "match_id_namespace": "statsbomb",
  "source_revision": "invented-v1",
  "sha256": "REPLACE_WITH_ACTUAL_64_CHARACTER_LOWERCASE_SHA256",
  "scope": [
    {
      "competition_name": "Serie A",
      "season_name": "2015/2016",
      "coverage_claim": "partial"
    }
  ]
}
```

Replace the fingerprint placeholder with `(Get-FileHash -Algorithm SHA256
-LiteralPath <snapshot>).Hash.ToLowerInvariant()`. The hash covers the snapshot
file, not the sidecar. At least one of `source_revision` (nonblank text) and
`retrieved_on` (ISO calendar date, such as `2026-10-27`) is required; both can be
supplied. Unknown fields, wrong artifact kinds/versions, conflicting hashes,
duplicate league scope records and rows outside declared scope reject the run.

Allowed snapshot origins: `provider_fixture_records`, `event_derived`,
`synthetic`. Event-derived snapshots are explicitly labeled **NOT INDEPENDENT**;
synthetic inputs remain synthetic demonstrations. Reusing a delivered artifact's
fingerprint as the snapshot rejects the file-based run. A different fingerprint
does not prove independent origin.

Scope is one record for each supplied league; it need not cover all four.
`coverage_claim` is `partial`, `provider_list`, `full_competition_claimed` or
`unknown`. Every value is a caller declaration, never a computed completeness
finding. A complete provider list may cover fewer fixtures than a complete league
season. No universal expected count, including 380, is hardcoded.

`--acquisition-ledger` requires `--acquisition-provenance`. The latter uses the
same provenance structure with `artifact_kind="acquisition_ledger"`, origin
`acquisition_log` or `synthetic`, and no `scope` field. Its fingerprint binds the
ledger file. Each final ledger row has stage `events` or `lineups`, outcome
`success`, `failure` or `unknown`, and a nonblank `evidence_reference` pointing
to the relevant request/run/log record. Failure additionally requires a nonblank
reason. References are retained for review, not fetched or authenticated.

One final outcome per match/stage is required. Duplicate or contradictory
outcomes reject the run; raw retry history must first be explicitly reconciled
outside this tool. A documented failure is a supplied log record, not proof of
the cause of every missing artifact. A successful request does not establish
complete event delivery, a correct filter or verified source identity. Absence
of a log remains **ACQUISITION OUTCOME UNKNOWN**, even when lineups are present.

## Comparison behavior and future commands

Run from the repository root. Current available evidence, without a snapshot:

```powershell
python -B -m scripts.audit_fixture_evidence --metadata data/validation/arpit-match-context-review/match_metadata.parquet --lineups data/raw/statsbomb_lineups.parquet
```

The status is explicitly **NOT VERIFIED — SOURCE SNAPSHOT MISSING**. Missing
expected IDs, unexpected observed IDs and snapshot counts are null (unassessed),
not fabricated empty fixture sets. The contributor claim for `3879594` is
reported separately; it never enters the expected ledger automatically.

Once actual local artifacts and provenance have been supplied:

```powershell
python -B -m scripts.audit_fixture_evidence --snapshot C:/evidence/fixtures.parquet --snapshot-provenance C:/evidence/fixtures-provenance.json --metadata data/validation/arpit-match-context-review/match_metadata.parquet --lineups data/raw/statsbomb_lineups.parquet --acquisition-ledger C:/evidence/acquisition.json --acquisition-provenance C:/evidence/acquisition-provenance.json
```

The `C:/evidence/` paths are placeholders, not supplied evidence. No such files
are created by this task. Omit both acquisition options when logs are unavailable.

The report contains per-league supplied/observed counts, sorted missing and
unexpected IDs, absent lineups, unassessed team associations, duplicate and
conflicting records, cross-table context/team differences, orphan lineup IDs,
provenance, input fingerprints, and documented/unknown acquisition outcomes.
Identical repeated fixture records are explicitly counted and represented once
in set comparisons. Conflicting IDs are quarantined from those sets and retained
with every distinct record; no first-row choice occurs. Counts exclude quarantined
IDs. Out-of-snapshot leagues remain unassessed. Empty supplied snapshots remain
empty supplied sets, never evidence of complete coverage.

Exit codes: 0 = comparison completed (may have missing/unverified evidence),
1 = comparison completed with conflicting records/associations, 2 = rejected
malformed/unavailable input. A successful exit never means production readiness.
Use `python -B -W error -m unittest discover -s tests -p test_fixture_evidence.py -q`
for synthetic regression checks.

## Current evidence and exact gaps

Read-only `git show` inspection used `origin/arpit-dev` at
`9d53c04be0d687ba6f6650deac6ca89784557246`: `fetch_normal.py`,
`fetch_lineups.py` and `docs/metric_documentation.md`. The event collector calls
`sb.matches` but does not save that response; fetch failures are printed and
skipped. Lineup IDs are drawn from the collected events, so overlap cannot
identify fixtures omitted from both. A lineup failure file can be written only
when failures occur; no such file was located in the working data inventory.

Arpit's section 1.3 reports that Serie A fixture **3879594** was listed upstream
but skipped following an events-fetch connection reset. This remains
**CONTRIBUTOR-REPORTED FIXTURE CLAIM**, not a supplied independent fixture or
acquisition log. The synthetic test supplies that ID and correctly reports it
missing from a smaller observed ledger; that is tested capability only.

The document reports an empty Ligue 1 difference against StatsBomb's list,
without printing the list size. **377 observed matches do not prove complete
league coverage.** No three missing IDs are guessed. The tool accepts a supplied
377-record list as a comparison set while leaving full-season verification false.

The actual delivered metadata has 1,814 global matches; the four target counts
are La Liga 380, Premier League 380, Serie A 379 and Ligue 1 377. It was derived
from events, not an independent fixture response. All 86,743 lineup rows are
available. D3B's full event scan and matching findings are reused; no large event
scan is repeated here.

Still missing: independently supported fixture/context snapshots with source
revision/date and team associations; preserved acquisition requests/outcomes and
failure references tied to the delivery; and provenance review establishing
independence. Recover archived contributor records before requesting targeted
new retrieval. The comparator evaluates artifacts when supplied; it does not
claim they were found or generate them from the observed data.

Even validated fixture matching does not resolve D1 actor identity trust,
component extraction/reportability, per-context numerator/exposure alignment,
open final-whistle endpoints, approved playing-time conventions or transferred
player reference membership. D3B's zero production-verified scoring contexts
remain unchanged. See D1B, D3B and D3A for their existing separate gates.

## Validation and preservation

The 41 new synthetic tests pass, covering the reported missing ID, exact and
extra fixture sets, duplicate/conflicting IDs, context/team mismatches, absent
lineups, acquisition outcomes, 377-match uncertainty, missing/empty/partial
snapshots, invalid paths/provenance/hashes, row order, input immutability,
bounded projected reads and CLI error/status behavior. The full Python suite
passes **669 tests** (628 existing + 41 D3H). Frontend JavaScript passes **112
tests**, with no frontend changes.

The initial focused run encountered sandbox temporary-directory permission
errors. Setting process-local `TEMP` and `TMP` to the permitted visualization
directory outside the repository resolved fixture writes and cleanup without
changing existing tests or repository configuration. Tests use disposable
synthetic artifacts only; the audit itself writes no files.

The existing local metadata/lineup comparison was executed with no snapshot or
acquisition ledger. It reports the required missing-snapshot status, target
observed counts 380/380/379/377, no context/team conflicts, no orphan lineup IDs,
unknown acquisition outcomes and false production readiness. No independent
real-source snapshot was available; synthetic success does not change that.

All **141 pre-existing file fingerprints** match the initial snapshot, including
all tracked files, all 11 protected Parquets and the untracked M4A checklist.
Protected SHA256 results also match D3B's documented inventory:

| Preserved input | SHA256 | Result |
|---|---|---|
| `data/processed/player_minutes.parquet` | `9701ec4a74b1a75ee6094f08619c40b26f6d6f103d64a23ca2802448351e931b` | PASS |
| `data/processed/player_name_crosswalk.parquet` | `a250ac8074967aad3b1fdcd35a849584658ac333a4049d1de3845f443d2397e7` | PASS |
| `data/processed/recovery_per90.parquet` | `056f94b0bd49bc707e5d00181d0b85654cd076e5dc3bc09e1a6c121cd530ee4d` | PASS |
| `data/raw/statsbomb_lineups.parquet` | `dfb6e2f0adfb1ec25c879b26feb3616b8683c64e152657f098edc20aa1635be2` | PASS |
| `data/validation/arpit-2026-10-21/player_minutes.parquet` | `01f1bb2650df4f793971465eefad49eefcd41a302789b5c5009cf7355a4b1694` | PASS |
| `data/validation/arpit-2026-10-21/recovery_per90.parquet` | `7a546348b2c391d32221456fab259d639910d13c8e672ba030e6d30b38cab61f` | PASS |
| `data/validation/arpit-match-context-review/match_metadata.parquet` | `1b1de360e0f31c49aabd43d065f95fe0762d29a31ea2bcba21b54571b86f3b47` | PASS |
| `data/validation/arpit-refresh-review/player_minutes.parquet` | `5600f1250a3bd7fcf9d12a9d11ecac4ae9d39cd58898d6e6df1e5d4d1aa1830e` | PASS |
| `data/validation/arpit-refresh-review/recovery_per90.parquet` | `5b53d544662826206511e2d2c532297160b781f84958b2acf615195590f82012` | PASS |
| `data/validation/drive-raw-review/statsbomb_360_frames.parquet` | `497fa459e1ee99f758ed37d405d69285af5e6759306851456d03fde8c4025625` | PASS |
| `data/validation/drive-raw-review/statsbomb_team_events.parquet` | `ec12fdd2340fb125671f4996abdac510c3dc6d81555848792520ce5df2519eb8` | PASS |

`git diff --check`, new-file syntax and whitespace checks pass. No existing
tracked file changed, and the staging area is empty. The only new repository
files are this document, `scripts/audit_fixture_evidence.py`, and
`tests/test_fixture_evidence.py`. All pre-existing untracked data and checklist
entries remain preserved. Branch is `integration-foundation`, HEAD remains
`81a6070e1f63a045ade74d0110c34673996f7d25`, and main remains
`179ad5e1905ebefc7e97dc732d550b1c110a1ee4`. No commit, push or deployment occurred.

Next evidence task: recover the archived four-league provider fixture snapshots
and original acquisition/failure records, starting with the reported `3879594`
failure and Ligue 1 comparison. Independently review provenance, then run this
offline comparison. Seek only specific missing artifacts if archives cannot
supply them; do not initiate blanket event recollection.
