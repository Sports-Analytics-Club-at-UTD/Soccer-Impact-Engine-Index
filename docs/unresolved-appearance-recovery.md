# Remaining appearance recovery

This branch follows the verified v2 player-data reconciliation. The user requested
investigation and correction of all 238 unresolved appearances outside Bundesliga.
The 238 appearances affect 174 players and 101 fixtures. Bundesliga source rows,
including its one unresolved appearance, are preserved unchanged.

## Result

| Outcome | Appearances | Meaning |
| --- | ---: | --- |
| Fully recovered elapsed exposure | 116 | Original physical entry/exit events establish the entire appearance. |
| Partially recovered exposure | 122 | Only source-backed closed intervals contribute actions and elapsed minutes; the remaining time is still unverified. |
| No usable interval recovered outside Bundesliga | 0 | Every investigated appearance has at least one verified interval. |

This adds 11,124.456250 supported minutes across 174 players. Eligibility stays
at 551 players: 297 MID and 254 CB. The minimums, competition cohort and Formula B
weights are unchanged. Reference statistics and scores are rebuilt consistently
using the additional measurements, so score changes are expected across the index.

There remain 122 non-Bundesliga appearances with unresolved portions. They are
not presented as fully repaired matches. One entirely unsupported Bundesliga
appearance remains outside this investigation. Source conflicts and original
provider bytes are retained; no final whistle or kickoff is estimated.

## Evidence rules

Physical Starting XI, incoming/outgoing substitution, Player Off/On, and dismissal
records determine playing exposure. Tactical-position labels do not create a
physical entry or exit. This recovers time even where fine-position stints contain
reversed endpoints, overlaps or stale role snapshots. Original canonical season
comparison positions are retained. Recovered elapsed time does not certify the
disputed minute-by-minute position labels.

Paired, unflagged half boundaries supply genuine kickoff/whistle endpoints.
A flagged late start or early video end cannot supply that endpoint. A player
substituted off before an unknown final whistle can still have a fully supported
appearance. Other players may retain only a verified half or an explicit closed
entry/exit interval. Source timestamps keep their milliseconds and first-half
stoppage time; the halftime break contributes no playing time.

Paolo Sammarco (23349), fixture 3879602, returned 78 milliseconds after the paired
first-half whistle and before the paired second-half starts. The return is a
documented halftime transition, not a reason to add break time or move its clock.
His first interval closes at Player Off and the next begins at the genuine second
kickoff. This is a general boundary-order rule, not a player-specific exception.

Anthony Weber (7435), fixture 3900512, retains only the 901.182 seconds before the
permanent-exit assertion. Its incompatible return still withholds the remainder.
The fixture's disputed pressure ratio remains entirely excluded, leaving the
same season pressure sample of 79 successes / 109 attempts.

Busquets (5203), fixture 266557, gains the verified first half of 46:27.825. The
second-half final-whistle timestamp is still unavailable. His supported total is
2,958.924967 minutes, with one explicitly partial match, while pressure retains
the existing 301 successes / 357 attempts. Ramos's 23 appearances and
2,010.556500 supported minutes remain unchanged.

## Metric scope and disclosure

Every per90 numerator is restricted to precisely the recovered interval union
that supplies its duration denominator. Selected actions outside a partial union
are retained in the private omitted-action ledger and excluded from the count.
Pressure ratios retain their separately verified action sample; partial elapsed
recovery does not silently trim a pressure ratio's successes or failures.
Existing metric-specific exclusions and pending fixture restrictions remain.

Public v3 adds explicit partial-fixture counts for each profile and skill. Player
card details explain that only verified portions are included and that actions
outside them are excluded. The removed "matches backing these minutes" footer
text is not restored. About Us, Teams, the spatial pitch, and archetype definitions
are unchanged.

## Verification and reproduction

The source replay reopens all 101 affected fixtures, verifies their document
fingerprints and independent metric-selection agreement, and proves that every
previously supported observation is unchanged. Unaffected fixtures come from the
byte-bound, independently verified v2 snapshot; all 691 profiles are reaggregated.
The old v1/v2 public snapshots remain unchanged and only the pinned v3 aggregate
is admitted to production output. Raw source events and interval evidence stay
in ignored audit-output.

A separate verifier does not import the recovery function. It pairs original
entry/exit edges first, projects them onto independently checked half boundaries,
and compares the exact interval union, duration, full/partial status, and included
versus omitted action sets. It also checks preservation of all Bundesliga rows,
the full investigated population, eligibility, frozen cohort statistics, scores,
percentiles, Formula B, public disclosures and byte bindings.

Completed checks: 427,228 independent checks; all 1,245 public backend cases;
all 244 public frontend tests including production HTTP checks; production build.
Browser checks cover keyboard selection, multiple archetypes, card details and
close controls at 1,440px and 320px with no horizontal overflow. There were no
application runtime errors; the existing favicon request returns 404.

With the original authorized research checkout and private verified v2 package:

```powershell
python -B -m scripts.recover_remaining_appearances --source-root ../.. --parent ../player-data-reconciliation/audit-output/supported-sample-final --output audit-output/new-recovery
python -B -m scripts.verify_supported_ratings audit-output/new-recovery
python -B -m scripts.install_supported_release audit-output/new-recovery
python -B -m scripts.report_supported_ratings audit-output/new-recovery
python -B -m scripts.run_backend_tests public -q
cd frontend
npm run test:public
npm run build
```

Output directories and release destinations must be new; installation never
overwrites a release. In an existing checkout, compare regenerated aggregate
bytes with the committed v3 instead of reinstalling it.

The completed private evidence is in `audit-output/recovered-appearances-final/`:
`RECOVERY-238.md` covers every investigated appearance, `REPORT.md` links to all
691 individual player reports, and source replay, changes CSV, frozen reference,
manifest and independent verification receipt are retained alongside them.

Public snapshot: `frontend/public/data/player-ratings-2015-16-v3.json`,
1,512,488 bytes, SHA-256
`ad2be90730ffd3019a3b8c66385bec2b5c1958a3e34bf476628e1238a65851bf`.
The branch is uncommitted and has not been pushed, merged or deployed.
