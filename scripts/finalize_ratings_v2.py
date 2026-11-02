"""Seal the local review report after reconstruction and verification finish."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'audit-output/ratings-v2'


def main():
    def js(name):return json.loads((OUT/name).read_bytes())
    def table(name):
        with (OUT/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    def digest(path):
        with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
    summary=js('summary.json');candidate=js('ratings-v2-candidate.private.json')
    verification=js('independent-verification.json');replay=js('original-source-replay-summary.json')
    tests=js('test-results.json');sensitivity=js('formula-b-sensitivity.json');binding=js('baseline-and-input-hashes.json')
    assert candidate['publication_authorized'] is False and candidate['production_ready'] is False
    public=ROOT/'frontend/public/data/player-ratings-2015-16-v1.json'
    assert digest(public)==binding['public_v1_sha256']
    assert verification['status']=='PASS'
    for name,row in tests.items():
        if name=='private-frontend':
            text=Path(row['log']).read_text(encoding='utf8')
            assert row['failed']==1 and 'provisionalOvr.test.js:61' in text
        else:assert row['returncode']==0 and not any(row[k] for k in ('failed','skipped','blocked')),(name,row)
    changes=table('player-691-comparison.csv');members=table('reference-membership-comparison.csv')
    ledger=[json.loads(s) for s in (OUT/'correction-admission-ledger.jsonl').read_text(encoding='utf8').splitlines()]
    stage_names=['v1','merged_batch1','corrected_batch2a','corrected_batch2b','proposed_batch3a','proposed_batch3b','proposed_batch4','proposed_batch5']
    batch_stats=[]
    for label,a,b in zip(['1','2A','2B','3A','3B','4','5'],stage_names,stage_names[1:]):
        ovrs=sum(r['stages'][a]['overall']!=r['stages'][b]['overall'] for r in ledger)
        attrs=sum(r['stages'][a]['attributes'][k]['rating']!=r['stages'][b]['attributes'][k]['rating'] for r in ledger for k in r['stages'][a]['attributes'])
        batch_stats.append(dict(batch=label,changed_ovrs=ovrs,changed_attribute_ratings=attrs))
    rankings={}
    for group in ['MID','CB']:
        rows=[r for r in changes if r['position_group']==group]
        rankings[group]={}
        for scope,oldkey,newkey in [('eligible','v1_rank','v2_rank'),('all_complete','v1_all_complete_rank','v2_all_complete_rank')]:
            rankings[group][scope]={}
            for n in [10,20]:
                old={r['player_id'] for r in rows if r[oldkey] and int(r[oldkey])<=n};new={r['player_id'] for r in rows if r[newkey] and int(r[newkey])<=n}
                rankings[group][scope][str(n)]=dict(entering=sorted(new-old,key=int),departing=sorted(old-new,key=int),retained=len(old&new))
    stats=replay['replay']['source_checks']
    fixture_counts=dict(Counter(r['competition'] for r in table('original-fixture-inventory.csv')))
    rows=['# Ratings V2 reconstruction — private numerical review candidate','',
          '**READY FOR TEAM NUMERICAL REVIEW. Publication is not authorized.**','',
          'This candidate retains Formula B, frozen attribute references and the existing strict eligibility rules. It is a local versioned reconstruction, not a replacement for the published V1 payload. External football-outcome validation has not been performed.','',
          '## Baseline and evidence contract','',
          f"Fetched `origin/main`: `{binding['baseline']}`. This is PR #14’s Batch 5 merge and is reachable from origin/main. Branch `ratings-v2-reconstruction`; worktree `{ROOT.as_posix()}`. The original dirty checkout and all retained correction/research worktrees were read-only inputs. No commit, push, PR, merge, deployment or publication was performed.",'',
          'No AGENTS.md was found in the repository inventory. README, production delivery, scorecard, source reconstruction, original metric modules, eligibility, previous methodology, all seven correction reports, the retained roadmap and identity audit, frozen packages and public/private harnesses were inspected. The roadmap is in the player-data-integrity-audit sibling; the initial identity audit is in the retained coverage-audit checkout. Exact paths, sizes, hashes and baselines are in baseline-and-input-hashes.json and source-input-inventory.csv.','',
          f"Published V1 SHA256: `{binding['public_v1_sha256']}`. Frozen semantic fingerprint: `{candidate['reference_fingerprint']}`. Candidate source fingerprint: `{candidate['source_fingerprint']}`; policy fingerprint: `{candidate['policy_fingerprint']}`.",'',
          '## Original scope and fresh replay','',
          f"**FRESHLY RECOMPUTED:** all {stats['original_events']:,} original UUIDs across 1,551 fixtures; original lineup/actor/recipient context; period and player intervals; successful metric UUID sets and independent alignment. All {stats['published_decisions_preserved']:,} historical published decisions and {stats['published_accepted_preserved']:,} accepted appearances reproduce. The historical roster contains 2,514 candidate player-season records, not 2,514 distinct real-world people. Candidate recipients remain the 691 published player-season identities.",'',
          f"Source checks: `{json.dumps(stats,sort_keys=True)}`. The source-replay database enforces a global UUID primary key and passes SQLite integrity checking. Current candidate attribution is independently checked for {verification['checks']['uuid_actor_fixture_checks']:,} metric UUID memberships against its fixture/team/player tuples. Overlap across different attributes is legitimate; duplication within a metric or actor fixture is rejected.",'',
          f"Original fixture inventories by competition: `{json.dumps(fixture_counts,sort_keys=True)}`. Original-fixture-inventory.csv gives every fixture, season, original fixture-document binding, report, events and lineup path/hash.",'',
          '**HASH-VERIFIED REUSED:** retained corrected metric facts, historical A–H diagnostic snapshots, original package seals and their lineage. Those facts were independently checked against fresh original-source geometry and UUID membership; they are not described as newly authored source facts. The source-replay summary’s historical baseline identifies the Batch 3A comparison ledger; execution_baseline records the actual Batch 5 checkout.','',
          'The Batch 5 historical caveat is retained in historical-diagnostic-receipt-differences.json: one old investigation-script self-receipt differs from the finalized diagnostic script. It is not represented as matching or as a line-ending-only change. No original source, frozen reference, production-module or consumed-output hash mismatch is waived; current source and numerical validation are fresh.','',
          '**NOT VERIFIED:** external outcomes, independent provider attestation and complete historical season performance. **BLOCKED:** a coherent full corrected upstream reference-refit scenario. No incomplete scan substitutes for the completed original-source replay.','',
          '## Included correction findings','',
          '| Batch | Changed attribute ratings at this stage | Changed OVRs at this stage |','| --- | ---: | ---: |']
    rows += [f"| {r['batch']} | {r['changed_attribute_ratings']} | {r['changed_ovrs']} |" for r in batch_stats]
    rows += ['',
       '**VERIFIED SOURCE CORRECTION:** Batch 1 retains all 91 supported off-camera recoveries and the four conflicting exclusions. Batch 2A preserves Juanfran’s removed bench-only nonappearance, Pallois’s supported interval, the supplemental bench records and genuine dismissal restrictions. Batch 2B retains all 36 source-backed entries (10 published, 26 source-only). Batch 3A retains 12 corroborated permanent exits (3 published, 9 source-only), all 17 terminal observations and their contradictions. Raw evidence, UUIDs and exact rational clocks remain intact.','',
       '**IMPLEMENTED MODEL POLICY:** the versioned V2 path explicitly invokes the existing source-bound Batch 3B component adjudicator. It reopens hash-bound original fixture/event/lineup bytes, independently verifies the chronology conflict, and withholds the whole affected numerator/denominator component. It introduces no player-specific exception and no timing tolerance. Unknown duration alone still does not invalidate an action ratio.','',
       'Anthony Weber 7435 / fixture 3900512: the whole pressure component is withheld; all four successes/attempts remain in raw lineage. Three disputed actions trigger withdrawal of all four admitted actions, preserving coherent ratio scope. Season pressure counts are 83/113 → 79/109, rating 77.23069650289477 → 75.92973526853555, Formula B 69.87739129211172 → 69.48710292180395. Supported exposure is unchanged; he remains ineligible. Exact UUIDs, trigger proofs and reasons are in changed-metric-events.csv and verified-measurement-corrections.json.','',
       'Scott Dann 3754048, Guillaume Gillet 3900579, Celso Borges 3825780 and Renato Civelli 3829454 retain their exact post-Half-End recovery exclusions and NUMERATOR_DENOMINATOR_MISMATCH reasons. The source-priority fixtures and full replay preserve these decisions. Batch 4 retains stable-ID authority, the conservative Fernando Luiz Rosa/Roza restriction and administrative bench activity without adding an alias or active appearance. Batch 5 retains provenance-bound helper bodies; existing integrated aggregation is unchanged. No new helper aggregation path was introduced. Batches 4 and 5 add zero numerical changes.','',
       '## Five attributes, arithmetic and independent checks','',
       'Successful tackling/interception definitions, unsuccessful-recovery exclusion, exact per-90 exposure and Joseph Level A forward/goal-distance geometry remain unchanged. Press resistance is the supported successful pressured Pass/Dribble ratio, not per 90. Progressive passing remains a proxy; it does not prove opponent defensive lines were broken. Raw numerator UUIDs, pressure denominator UUIDs, source identities, contexts, missingness, excluded fixture reasons and exact supported seconds are retained in attribute-source-lineage.jsonl. Attribute comparisons retain all source-scope changes and frozen means/SDs.','',
       'For the five clipped 1–99 ratings sorted descending, B = .30 S1 + .25 S2 + .20 S3 + .15 S4 + .10 S5. Exact rational arithmetic over the existing binary float values precedes the final float conversion; only presentation rounds. No imputation, dropped attribute or second normalization occurs. Independently B−A = .10(S1−S5)+.05(S2−S4), and B≥A. Formula A is used only for this arithmetic diagnostic; C is not calculated as the candidate OVR.','',
       f"Independent results: `{json.dumps(verification,sort_keys=True)}`. The verifier sums retained UUID sets and rational exposure directly, uses a separate raw arithmetic implementation for normalization and exact empirical percentiles, checks full-precision rank by pairwise order, and independently transcribes the strict predicates. The production scorer is not its own oracle. Repeat reconstruction reverses input order and reopens original chronology evidence; scored profiles and corrected facts agree exactly. Missing fixtures fail rather than disappearing from canonical scope.",'',
       '## Frozen references and eligibility','',
       'Scenario A reuses exact frozen membership, sample means/SDs, empirical percentile populations and semantic fingerprint. The actual individual attribute pools differ from combined leaderboard counts:','',
       '| Group | Tackles | Interceptions | Recoveries | Press resistance | Progressive passing |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for group in ['MID','CB']:
        ns={r['attribute']:r['frozen_n'] for r in members if r['position_group']==group}
        rows.append('| '+group+' | '+' | '.join(ns[a] for a in ['tackles','interceptions','recoveries','press_resistance','progressive_passing'])+' |')
    proposed=[r for r in members if r['proposed_entering']=='True'];departing=[r for r in members if r['proposed_departing']=='True']
    rows += ['',
       'Normal per-90 recipient scoring requires 900 supported metric minutes; normal pressure recipients require 900 known supported season minutes and positive supported attempts. Bundesliga projections preserve their positive-observation exception and limited-data status. Forty pressure attempts is the reference/strict-eligibility threshold, not a replacement denominator or an automatic rating gate. Strict eligibility additionally requires all observed exposure and all five metric scopes complete and aligned, valid MID/CB classification, the existing frozen attribute-membership intersection, no pending 3879594 contribution, and no Bundesliga contribution. Transfer contexts sum raw verified contributions once; they never average club ratings or duplicate actor fixtures.','',
       f"**UNAPPROVED POLICY PROPOSAL / INCOMPLETE SOURCE EVIDENCE:** Scenario B was assessed but not fitted. {len(proposed)} published attribute-membership pairs satisfy corrected candidacy while outside the frozen pool; {len(departing)} existing published membership pairs fail corrected candidacy. Exact IDs, groups, attributes and reasons are in reference-membership-comparison.csv. These are proposals, not adopted reference entries/departures. A complete corrected 2,514-candidate reference cohort and explicit transfer/membership rules are needed before fitting a coherent replacement. No mixed corrected-recipient/uncorrected-upstream refit was manufactured. Primary reference changes: none.",'',
       '## Population and numerical comparison','',
       f"{summary['profiles']} recipients; {summary['complete']} complete five-attribute OVRs; {summary['missing_ovr']} unavailable OVRs. Compared with V1: {summary['changed_attributes']} changed attribute ratings, {summary['changed_ovrs']} changed OVRs and {summary['unchanged_ovrs']} unchanged OVR/N/A results. Newly eligible: {summary['newly_eligible']}; newly ineligible: {summary['newly_ineligible']}. Every zero-change profile is retained. Partial profiles retain metric-specific N/A reasons. Historical intermediate states are preserved in the admission ledger rather than invented or collapsed into the latest comparison.",'',
       'Largest positive and negative OVR changes:','',
       '| Player | Position | V1 B | V2 B | Delta |','| --- | --- | ---: | ---: | ---: |']
    positive=sorted([r for r in changes if r['delta_formula_b'] and float(r['delta_formula_b'])>0],key=lambda r:-float(r['delta_formula_b']))[:5]
    negative=sorted([r for r in changes if r['delta_formula_b'] and float(r['delta_formula_b'])<0],key=lambda r:float(r['delta_formula_b']))[:5]
    rows += [f"| {r['display_name']} ({r['player_id']}) | {r['position_group']} | {float(r['v1_formula_b']):.8f} | {float(r['v2_formula_b']):.8f} | {float(r['delta_formula_b']):+.8f} |" for r in positive+negative]
    rows += ['',
       'Changes arise from exact supported action/exposure or component-admission changes; Formula B’s weights did not change. Attribute-comparison.csv lists numerator/pressure-denominator UUID additions/removals, metric-supported fixture sets, exposure, exact raw values, frozen parameters and resulting attribute deltas. Correction-admission-ledger.jsonl binds all intermediate batch changes. Single-appearance and sparse-sample cases remain reviewable in outlier-review.csv and withheld-components.csv. A larger observed rating is not evidence of improved ability.','',
       '## Rankings and research stability','',
       f"Strict leaderboard population: {summary['eligible']['MID']} MID and {summary['eligible']['CB']} CB. Ranks use unrounded B, then stable numeric provider ID for exact ties, matching the existing UI order. Ineligible complete profiles have a separate all-complete rank and never acquire an eligible rank. No cross-position ranking is inferred.",'',
       'Top membership comparison (IDs; empty entering/departing lists mean no change):','',
       '```json',json.dumps(rankings,indent=2),'```','',
       'Largest individual all-complete movements are in largest-positive-rank.csv and largest-negative-rank.csv; eligible movements have separately named CSVs. Rank changes can affect unchanged players when other observed profiles move. Limited-data and incomplete-season flags remain visible; the candidate does not certify season completeness.','',
       '**PRIVATE RESEARCH RESULT:** weights 25/25/20/15/15, 35/25/20/15/5 and equal weights are compared only on the existing eligible population. Formula-b-sensitivity.json contains Spearman correlations with average tied ranks, strict pairwise reversals, top-10/top-20 overlap, largest movements and low-pressure-sample observations. Selected V2 weights remain 30/25/20/15/10.','',
       '```json',json.dumps({g:v['scenarios'] for g,v in sensitivity['groups'].items()},indent=2),'```','',
       'A deterministic fixture-cluster split additionally compares alternating sorted provider fixture IDs, requiring eight supported fixtures and forty pressure attempts in each half. This is a private descriptive split, not a temporal holdout or season certification. Half-scope scores use unchanged frozen parameters; they do not acquire product eligibility. No confidence intervals are invented for sparse or incomplete observations.','',
       '```json',json.dumps(sensitivity['split_half']['groups'],indent=2),'```','',
       '## Verification suites','',
       '| Suite | Passed | Failed | Skipped | Deselected | Blocked |','| --- | ---: | ---: | ---: | ---: | ---: |']
    rows += ['| '+name+' | '+' | '.join(str(r[k]) for k in ['passed','failed','skipped','deselected','blocked'])+' |' for name,r in tests.items()]
    rows += ['',
       'Suites overlap and are not summed into a unique test total. Exact commands, logs and exit codes are in test-results.json. Public/private frontend and production build run against unchanged application source; the private frontend source equivalence receipt is in test-provisioning-hashes.json. The sole private frontend failure reproduces the separately known provisionalOvr.test.js:61 badge typography expectation. Typography and test expectations were not altered. No new product failure is dismissed as that known failure.','',
       'The initial dependency-junction command required an absolute Windows target; it was corrected before frontend execution. An initial read-only command used a relative Path parent and failed before reading private facts; no evidence changed. The new summary parser initially mishandled the Unicode Node summary marker; reparsing the unchanged complete logs corrected the recorded frontend counts without rerunning or altering tests. The preliminary summary is preserved as test-results-before-summary-parser-fix.json. Unfinished/failed command logs remain retained. The numerical checkpoint preceded the final explicit nonappearance-boundary tightening; the final numerical pass and V2 tests cover the final implementation.','',
       '## Reproduce and review artifacts','',
       'Use this baseline, Python 3.13 and the existing authorized source/audit siblings. Preserve completed outputs and choose a new isolated worktree/output directory for a full repeat. Never overwrite frozen evidence.','',
       '```powershell',
       'git fetch origin main',
       "python -B -c \"from scripts.reconcile_event_chronology import run; run(output='audit-output/ratings-v2/source-replay', baseline='1686a4f82d22f2e31935fe9cdacbc93a9ffac849')\"",
       'python -B -m scripts.verify_ratings_v2',
       'python -B -m scripts.reconstruct_ratings_v2',
       'python -B -m scripts.finalize_ratings_v2',
       '```','',
       'For an intermediate arithmetic checkpoint use `python -B -m scripts.reconstruct_ratings_v2 --numerical-only`. It is explicitly not a completed source replay or final candidate. Locked frontend dependencies must already be installed or linked; the verifier copies only two small hash-bound chronology test fixtures and uses retained authorized private harness inputs. It never copies raw data into frontend assets.','',
       'All required private artifacts are under audit-output/ratings-v2/. Artifact-inventory.json records every task-owned artifact and review source/report with bytes and SHA256, excluding itself. Source-input-inventory.csv categorizes consumed source, frozen, diagnostic and code receipts. The private candidate preserves the documented public player-field shapes within a new private envelope and attaches version/source/policy fingerprints; source lineage remains a separately ignored artifact. Display labels in the comparison come from the existing frontend ID/season map for reporting only; matching and scoring use canonical IDs.','',
       'Modified/added review files: src/ratings_v2.py; scripts/reconstruct_ratings_v2.py; scripts/verify_ratings_v2.py; scripts/finalize_ratings_v2.py; scripts/reconcile_event_chronology.py (parameterized isolated output/baseline and comparison of historical production modules); tests/test_ratings_v2.py; docs/ratings-v2-reconstruction-report.md. No published payload, V1 reference, original dataset, contributor helper, frontend source, badge policy, player-name map, team photo or deployment changed.','',
       'Recovery-zone-accounting.csv independently reopens original event bytes and conserves successful tackle/interception/recovery totals separately from known-zone totals. Missing or off-pitch locations retain their total contribution without inventing a zone. Overlapping category UUIDs are rejected. Position-exposure-comparison.csv reassesses dominant fine groups using newly supported source allocations; the frozen MID/CB comparison groups remain unchanged. Canonical product fine labels are retained under the existing correction-batch contract, with diagnostic fine-group differences visible.','',
       '## Decisions and release readiness','',
       'Policy-decision-register.csv distinguishes APPROVED / ALREADY IMPLEMENTED, SUPPORTED BY EVIDENCE BUT NOT YET AUTHORIZED and UNRESOLVED SOURCE OR POLICY ISSUE. Source chronology, pending coverage, conservative identity restrictions and incomplete seasons are retained limitations, not permission to infer minutes, add aliases or promote rankings. A refit requires separately reviewed upstream membership and statistics. Publication requires a separate explicit numerical release decision.','',
       '- [x] Baseline and Batch 5 merge verified.',
       '- [x] All approved source corrections retained; Weber component policy explicitly integrated.',
       '- [x] Complete available original-source replay and UUID/exposure verification finished.',
       '- [x] All 691 recipients, five attributes, Formula B, references and eligibility compared independently.',
       '- [x] Primary references, eligibility and public V1 preserved.',
       '- [x] Local candidate and complete review artifacts generated; publication explicitly false.',
       '- [x] Known private frontend typography failure reported separately.',
       '- [ ] Team numerical review and acceptance of the V2 values.',
       '- [ ] Any separately desired reference/coverage/eligibility policy changes approved and validated.',
       '- [ ] Publication and all release prerequisites separately authorized.','',
       '**Final verdict: READY FOR TEAM NUMERICAL REVIEW.** No claim of external football validation or readiness for publication is made.','']
    report=ROOT/'docs/ratings-v2-reconstruction-report.md'
    report.write_text('\n'.join(rows),encoding='utf8')
    # Machine-readable ranking and per-batch review receipts accompany the prose.
    for name,value in [('ranking-review.json',rankings),('cross-batch-summary.json',batch_stats)]:
        (OUT/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
    inventory_rows=[]
    for path,receipt in binding['inputs'].items():
        p=Path(path)
        kind='ORIGINAL_SOURCE' if any(x in p.parts for x in ['source-evidence','raw']) else 'FROZEN_REFERENCE_OR_PACKAGE' if 'data' in p.parts else 'HISTORICAL_DIAGNOSTIC' if 'audit-output' in p.parts else 'CODE_OR_DOCUMENTATION'
        inventory_rows.append(dict(path=path,kind=kind,**receipt))
    with (OUT/'source-input-inventory.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','kind','sha256','bytes']);w.writeheader();w.writerows(inventory_rows)
    status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    (OUT/'final-git-status.txt').write_text(status,encoding='utf8')
    modified=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('frontend/','data/')) for p in modified)
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='artifact-inventory.json']
    files += [ROOT/p for p in ['src/ratings_v2.py','scripts/reconstruct_ratings_v2.py','scripts/verify_ratings_v2.py','scripts/finalize_ratings_v2.py','scripts/reconcile_event_chronology.py','tests/test_ratings_v2.py','docs/ratings-v2-reconstruction-report.md','ratings-v2-replay.log']]
    inventory=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(files)]
    (OUT/'artifact-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(verdict='READY FOR TEAM NUMERICAL REVIEW',summary=summary,report=str(report),candidate_sha256=digest(OUT/'ratings-v2-candidate.private.json')),indent=2))


if __name__=='__main__':main()
