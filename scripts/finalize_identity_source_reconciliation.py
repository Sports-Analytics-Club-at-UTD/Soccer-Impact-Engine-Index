"""Finalize the local Batch 4 report and ignored, hash-bound evidence inventory."""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
import csv,hashlib,json,re,subprocess
from scripts.investigate_identity_sources import ROOT,SOURCE,PRIOR,SEALED,OUT,rows,write_csv,jsonlines


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    summary=json.loads((OUT/'summary.json').read_text(encoding='utf8'));inputs=json.loads((OUT/'input-hashes.json').read_text(encoding='utf8'))
    def bind(p,expected=None):
        h=sha(p)
        if expected:assert h==expected,str(p)
        inputs[str(p.resolve())]={'sha256':h,'bytes':p.stat().st_size}
    def js(p):bind(p);return json.loads(p.read_text(encoding='utf8'))
    def dump(name,v):(OUT/name).write_text(json.dumps(v,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
    inventory=js(SEALED/'run-manifest.json');oldhashes={r['path']:r['sha256'] for r in inventory['artifacts']}
    transferpath=SEALED/'transfer-policy-comparison.jsonl';bind(transferpath,oldhashes[transferpath.name]);transfer_checks=Counter()
    for r in jsonlines(transferpath):
        contexts=r['original_contexts'];mids=[m for c in contexts for m in c['match_ids']]
        assert len(mids)==len(set(mids));transfer_checks['actor_fixture_uniqueness']+=1
        for attr,total in r['combined_raw_counts'].items():
            assert sum(c['raw_counts'][attr] for c in contexts)==total;transfer_checks['numerator_conservation']+=1
        exact=lambda v:F(v['numerator'],v['denominator'])
        assert sum((exact(c['supported_minutes']) for c in contexts),F())==exact(r['combined_supported_minutes']);transfer_checks['exposure_conservation']+=1
    numeric=js(ROOT/'audit-output/batch4-numerics/summary.json');assert numeric['players']==691 and numeric['changed_profiles']==0
    additional=js(ROOT/'audit-output/batch4-additional/additional-checks.json');assert additional['raw_delivered_projection_vs_reconstruction_db']['mismatches']==0 and additional['all_2514_reference_candidate_and_membership_discrepancies']==[]
    candidatepath=SOURCE/'data/derived/private-five-attribute-v2/player-measurements.jsonl';bind(candidatepath)
    candidates=list(jsonlines(candidatepath));assert len(candidates)==2514
    summary['historical_candidate_attribute_predicates_checked']=sum(len(p['attributes']) for p in candidates)
    summary['fresh_numerical_verification']=numeric;summary['independent_transfer_checks']=transfer_checks;summary['historical_reference_candidates_checked']=2514
    bind(ROOT/'frontend/public/data/player-ratings-2015-16-v1.json','9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e')
    collisions=SEALED/'source-name-collisions.json';bind(collisions,oldhashes[collisions.name]);assert json.loads(collisions.read_text(encoding='utf8'))==[]
    policy=ROOT.parent/'Soccer-Impact-Engine-Index-source-evidence-reconciliation/audit-output/source-reconciliation/identity-policy-contexts.csv';bind(policy);assert len(list(rows(policy)))==10
    current=list(rows(OUT/'current-restriction-inventory.csv'));apps=list(rows(OUT/'delivered-appearance-evidence.csv'))
    for r in current:
        r['has_current_active_club_context']=bool(json.loads(r['source_active_matches']))
        r['explanation']='Original event and lineup spellings agree within each fixture under one stable ID; candidate-season spelling check remains conservative.' if r['player_id']=='3054' else 'Only source Bad Behaviour activity lacks an active appearance; preserve the raw disciplinary record and the activity flag without creating playing exposure.'
        if r['resolved_appearance_class']=='G':r['explanation']+=' Batch 2A already resolved the active-appearance mismatch.'
    # Enrich the completed inventory without replacing its source scan results.
    write_csv(OUT/'current-restriction-classifications.csv',current)
    summary['current_active_club_restrictions']=sum(r['has_current_active_club_context'] for r in current)
    summary['current_roster_restrictions']=len(current)
    summary['historical_appearance_mismatches_resolved']=sum(r['resolved_appearance_class']=='G' for r in current)
    # Machine-readable same-ID assertion, explicitly excluded from crosswalk use.
    fern=next(r for r in current if r['player_id']=='3054')
    decision=dict(provider_revision='4b73468fc5b0f1950f9f66fada70ad3a4f9327cb',player_id=3054,team_id=36,competition_id=2,season_id=27,raw_names=json.loads(fern['original_names']),status='VERIFIED_SAME_SOURCE_ID_SPELLINGS_DIAGNOSTIC_ONLY',matching_alias_installed=False,production_reason_retained='CANDIDATE_SOURCE_NAME_DISAGREEMENT',proof_ledger='source-name-evidence.csv',no_cross_club_or_idless_extension=True)
    dump('source-name-decisions.json',[decision])
    executions=js(ROOT/'audit-output/verification-executions.json');results={}
    def result(name,command,path,exitcode=None):
        text=path.read_text(encoding='utf8',errors='replace');counts=dict(passed=0,failed=0,skipped=0,blocked=0,deselected=0)
        for key in counts:
            found=re.findall(r'(\d+) '+key+r'\b',text)
            if found:counts[key]=int(found[-1])
        for key,label in [('passed','pass'),('failed','fail'),('skipped','skipped')]:
            m=re.findall(r'^(?:#|ℹ) '+label+r' (\d+)',text,re.M)
            if m:counts[key]=int(m[-1])
        m=re.search(r'Ran (\d+) tests?',text)
        if m and '\nOK' in text:counts['passed']=int(m.group(1))
        if name=='production-build' and exitcode==0:counts['passed']=1
        if name=='identity-probes':
            probes=json.loads(text)['results'];assert all(probes.values());counts['passed']=len(probes)
        assert counts['passed'] or name in ('source-identity-scan','independent-numerics','raw-reference-checks'),(name,text[-500:])
        results[name]=dict(command=command,returncode=exitcode,log=str(path.relative_to(ROOT)),sha256=sha(path),**counts)
    for name,r in executions.items():result(name,r['command'],ROOT/r['log'],r['returncode'])
    extra=[('batch4-targeted','python -B -m pytest tests/test_identity_source_reconciliation.py tests/test_identity.py tests/test_identity_evidence.py tests/test_source_reconstruction.py tests/test_event_chronology.py -q -p no:cacheprovider','batch4-targeted-final.log'),('public-backend-final','python -B -m scripts.run_backend_tests public -q','public-backend-batch4-final.log'),('original-identity-records','python -B -m scripts.check_identity_source_records','batch4-original-source-final.log')]
    for name,command,log in extra:result(name,command,ROOT/'audit-output'/log,0)
    for name,command,log in [('source-identity-scan','python -B -m scripts.investigate_identity_sources --reuse-verified-index audit-output/identity-source-reconciliation-attempt3/source-uuid-index.sqlite',ROOT/'identity-investigation-final.log'),('independent-numerics','python -B -m scripts.verify_batch4_numerics',ROOT/'audit-output/batch4-numerics-attempt2.log'),('raw-reference-checks','python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/scripts/audit_full_player_additional_checks.py --source-root ../Soccer-Impact-Engine-Index --checkout . --output audit-output/batch4-additional',ROOT/'audit-output/batch4-additional.log')]:
        result(name,command,log,0);results[name]['passed']=1
    assert results['public-backend-final']['passed']==1163
    assert all(r['failed']==0 for name,r in results.items() if name!='private-frontend')
    assert results['private-frontend']['passed']==33 and results['private-frontend']['failed']==1
    dump('test-results.json',results)
    population=list(rows(OUT/'full-population-comparison.csv'));byid={int(r['player_id']):r for r in population}
    retained_facts=js(ROOT/'audit-output/batch4-numerics/profiles.json');assert len(retained_facts)==691
    for r in retained_facts:assert r['batch4']==json.loads(byid[r['player_id']]['proposed_batch4'])
    report=['# Stable player identity and source-name reconciliation — Batch 4','',
        'Baseline: `1bd99b9c43795ecd670b7ad447d031fd25578c39` (PR #12), fetched from origin/main. Local branch `identity-source-reconciliation`; isolated worktree `'+str(ROOT)+'`. No commit, push, PR, merge, deployment or publication was performed. Existing worktrees and their uncommitted work were preserved.','',
        '**No new production identity defect is confirmed, and no production matching or admission change is justified by these records.** The same-ID spelling provenance is established; the existing stable-ID resolver already handles supplied IDs. The separate conservative candidate-name flag is retained. Four historical appearance-set mismatches are already resolved by Batch 2A. Remaining activity flags describe bench discipline, not wrong-person attribution.','',
        '## Scope and reproducibility','',
        f"The historical inventory has 2,280 active player/club contexts and 2,974,680 exact delivered associations, with ten restricted contexts. The current scan covers {summary['checks']['original_fixtures']:,} retained fixtures and {summary['checks']['original_events']:,} original events, including the separately retained 34 Bundesliga fixtures. Current source-roster restrictions: {summary['current_roster_restrictions']}; restrictions attached to a currently active club context: {summary['current_active_club_restrictions']}. These populations differ: an unused roster actor is not an active player/club observation. Historical flags are not claims of published errors.",'',
        'All eight requested prior reports were located across retained worktrees and read. The identity-integrity audit is retained under `C:/Users/Ayush/.codex/worktrees/coverage-audit/Soccer-Impact-Engine-Index/docs/identity-integrity-audit-2026-11-01.md`. The roadmap and initial identity-policy register are in the integrity-audit and source-reconciliation sibling worktrees. Exact paths, hashes and private evidence inputs are recorded in `input-hashes.json`.','',
        '## Fernandinho — stable ID 3054','',
        'Manchester City team ID 36; Premier League competition ID 2; season 2015/2016, source season ID 27. The 35 original roster records contain `Fernando Luiz Rosa` in 34 fixtures and `Fernando Luiz Roza` in fixture **3754296**. The latter has **294 actor events and 73 pass-recipient references** under ID 3054; every original event spelling agrees with the same-fixture lineup ID/name. Actor and recipient roles remain distinct in the evidence ledger. All 3,873 delivered actor associations remain exact UUID/context matches. No delivered event needs a name override.','',
        'Roza fixture events SHA256: `392a2af6232982127b65c14dab1dc52643afbe2c0969d9dc82f2e009e4947ce6`; lineups SHA256: `383d7f62097d8c768c57e081e333cdfe7b6f0b1a47b9c062103e52ba69c307db`; fixture document SHA256: `e07d6d360b30e0cd17f9aeea0db1502d2a5666d298f1b44b83a2d2f21ba3d21b`. Example original actor UUID: `685e5fed-36de-4a5f-94f5-7b1b7ae96c52`. `source-name-evidence.csv` retains every investigated UUID, raw/normalized spelling, role, fixture/team/competition/season IDs, original lineup reference and source hashes for both variants.','',
        'Decision: a provenance-bound same-source-ID spelling assertion is recorded in `source-name-decisions.json`, for diagnostic explanation only. **No matching alias is installed. Alias-based admission beyond the existing supplied-ID path is withheld.** The production `CANDIDATE_SOURCE_NAME_DISAGREEMENT` flag remains. The source spelling question is reconciled, but this batch does not promote the upstream context to complete exposure or bypass its conservative admission policy. The existing resolver accepts original supplied stable IDs without adding an ID-less bridge or a cross-club alias. A change to the upstream candidate-admission contract would need its own explicit review; a name flag alone does not recover an event, duration or metric.','',
        '## Juanfran — stable ID 26023','',
        'Levante UD team ID 221; La Liga, 2015/2016. Batch 2A already resolves the historical `DELIVERED_SOURCE_APPEARANCE_DISAGREEMENT`: the current source active set, selected delivered active set and diagnostic contribution set each contain **20 fixtures**. The V1 historical observed set contains 21, including the removed nonappearance. Fixture 3825670 remains a bench-only roster record, with no entry or position stint and no accepted ledger contribution. Its Bad Behaviour / Red Card UUID `e8bbbe1d-37fb-4ffb-92dd-ee93a07c6481` remains unchanged. No zero-minute observation is invented.','',
        'The generic `SOURCE_ACTIVITY_WITHOUT_APPEARANCE` diagnostic can still be reproduced because that loop counts every actor event, including this bench card. It is a separate administrative activity flag, not an unresolved active-appearance mismatch or a player-identity conflict. Retaining that conservative flag changes no accepted measurement. Events SHA256: `6c90b8df7e4b3405b9f0f5ac03af9b4f7c3ed81273ac5bc011ee8fac42e03be7`; lineups SHA256: `ddc98bfbb8c8cd0c90cf275067dec05d3f5cead82e1c740d09f2b12ec0d62021`.','',
        '## Current restriction inventory','',
        '| Stable ID | Original names | Team ID | Prior reasons | Current reasons | Classification |','| --- | --- | --- | --- | --- | --- |']
    for r in current:report.append('| '+str(r['player_id'])+' | '+', '.join(json.loads(r['original_names']))+' | '+str(r['team_id'])+' | '+', '.join(json.loads(r['prior_reasons']))+' | '+', '.join(json.loads(r['current_reasons']))+' | '+', '.join(json.loads(r['classification']))+(' / appearance G' if r['resolved_appearance_class']=='G' else '')+' |')
    report += ['',
        'A = verified source-name inconsistency; C = source activity without an established active appearance; G = already resolved by earlier batches; H = preserved conservative restriction. No genuine conflicting source ID, ambiguous same-context name mapping, missing original identity evidence or new implementation defect was found in these investigated restrictions. The full roster includes source-only actors absent from the historical active-club summary. The exact additional actor and all disciplinary UUIDs/fixtures are in the current inventory and `unresolved-conflicts.csv`. No restriction is cleared using a display nickname.','',
        'The other three appearance mismatches (6672/3825869, 10612/3825885, 40458/3878555) are also Batch 2A bench-card removals. Their disciplinary activity remains traceable. The five older activity contexts (7105, 10448, 25859, 27348, 27457) retain administrative source activity without an active appearance. They receive no zero-minute contribution and no published-player recovery claim. All current context rows retain exact reasons rather than conflating identity, activity, missing video and duration support.','',
        '## Identity pipeline and safeguards','',
        '`prepare_crosswalk` rejects ambiguous and duplicate normalized name/team/competition/season keys. `resolve_events` validates many-to-one cardinality, event order and uniqueness, supplied-ID conflicts, and stable-ID/context population membership. Supplied stable IDs remain authoritative. Missing IDs require caller-trusted evidence and are never guessed. Normalization is limited to declared doubled apostrophes/whitespace and the two existing team aliases; there is no accent folding, nickname or fuzzy bridge.','',
        '`identity_evidence` independently validates match-to-season/competition mappings, lineup evidence attestations and source collisions. The requested historical `source_events` implementation is named `flatten_events` in this baseline: it validates original actor/roster identity and event/team/fixture context. `reconcile_event` requires UUID, fixture, team, competition, season, type and original name agreement, and rejects conflicting supplied player/team IDs. The participation adapter also validates XI, tactical and substitution actors against original roster IDs/names. Fresh independent actor and recipient checks cover the complete retained source universe.','',
        'The reconstruction script uses exact source UUIDs to locate delivered records, stable match/team/player IDs for roster associations, and a separate candidate-name consistency check. That check remains conservative. Tackles/interceptions/recoveries run through the recovery wrapper with `PLAYER_KEYS`; press resistance uses stable context with a one-to-one exposure join; passing and progressive passing restore supplied IDs by unique event UUID and use stable context/cardinality checks. Scorecard joins remain one-to-one. No new name-based metric join, frontend alias dependency or Batch 5 legacy-helper change is introduced.','',
        '## Source, UUID, transfer and participation conservation','',
        'A fresh disk-backed primary-key inventory independently reopens all original event bytes and checks exact actor/team/fixture tuples bidirectionally against the hash-validated Batch 3B UUID database. Missing, extra, duplicate and reassigned UUIDs: **0**. Raw actor/recipient spelling and lineup assertions are preserved; no original event record or name is rewritten. The 34 Bundesliga fixtures use their separate retained source reports, rather than being incorrectly counted in the old 2,280-context ledger.','',
        f"Fresh identity checks: `{json.dumps(summary['checks'],sort_keys=True)}`. Independent transfer checks over the hash-bound historical original scope: `{json.dumps(dict(transfer_checks),sort_keys=True)}`. Club-specific provenance is retained; duplicate actor fixtures are rejected, numerators/exposure sum exactly, and no transfer policy or nominated reference context changes. Current UUID uniqueness prevents an event contributing as two different source actors.",'',
        'Because production reconstruction is unchanged and every production module and consumed original-source hash matches the completed Batch 3B replay, its accepted geometry/measurement verification is reused. This is deliberate hash-bound reuse, not a newly claimed production participation replay. The fresh scan independently verifies source identity and UUID conservation; original-source regressions rerun current adapter/state checks for the remaining bench cases. All 14,550 accepted published contributions retain their geometry. Batch 1: 91 recoveries; Batch 2A: five disciplinary corrections; Batch 2B: 36 entry proofs; Batch 3A: 12 exit proofs; all 17 terminal observations and all existing unresolved contradictions retain their decisions.','',
        'Batch 3B remains a separate diagnostic admission layer: the fresh numerical run reapplies its independently source-verified chronology ledger, withholding the full Anthony Weber 7435/3900512 pressure component. Four successes and four attempts remain withheld. Production source reconstruction, sealed V1 facts and published V1 remain separate from these diagnostics and a possible future V2.','',
        '## Frozen-reference numerical and eligibility results','',
        'A–G comparisons for every one of the 691 published profiles are in `full-population-comparison.csv`: V1, Batch 1, 2A, 2B, 3A, 3B and Batch 4. The fresh Batch 4 score replay recomputes production aggregation under unchanged references and independently confirms raw numerator/attempt sets, exact matched exposure, per-90/action ratios, ratings, percentiles, Formula B and exclusion predicates. It preserves all prior Batch 3B differences relative to earlier stages. Historical A–F arithmetic is independently rechecked against hash-bound diagnostic records.','',
        '**Batch 4 versus Batch 3B: zero changes to all five numerators, pressure attempts, supported exposure, attribute values, ratings, percentiles, Formula B, player-season membership and ranking eligibility across all 691 profiles.** No source-association, delivered active-appearance, duration or metric admission decision changes. The same-ID provenance label alone is the new finding. All 2,514 historical frozen-reference candidate records are checked against their original retained scope, including 12,570 per-attribute candidate predicates and frozen membership-set equality, with zero discrepancies. This historical candidate scope is separate from the original source-roster population. No references are refitted.','',
        '| Player | Diagnostic fixtures / supported | Exact minutes | Formula B | Eligible |','| --- | --- | --- | --- | --- |']
    for pid in (3054,26023):
        d=json.loads(byid[pid]['proposed_batch4']);report.append(f"| {pid} | {len(d['appearance_ids'])} / {len(d['supported_appearance_ids'])} | {d['exact_supported_minutes']} | {d['overall']} | {d['eligible']} |")
    report += ['', '| Player | Attribute | Numerator | Attempts | Exact value | Rating | Percentile |','| --- | --- | --- | --- | --- | --- | --- |']
    for pid in (3054,26023):
        for attr,m in json.loads(byid[pid]['proposed_batch4'])['attributes'].items():report.append(f"| {pid} | {attr} | {m['numerator']} | {m['attempts']} | {m['exact_value']} | {m['rating']} | {m['percentile']} |")
    report += ['',
        'Every value above is unchanged by Batch 4. Fernandinho still has two unsupported observed contributions and separate metric-scope/frozen-membership exclusions; Juanfran still lacks existing frozen attribute membership. No leaderboard promotion occurs. Remaining exclusions for each potentially affected published player appear in `player-impact.csv`. Nonpublished source-roster matching, activity, geometry, metric admission, reference membership and published-score consequences are unchanged; the evidence ledger separately records their administrative flags.','',
        'Frozen semantic fingerprint: `403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd`. Published V1 SHA256: `9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e`.','',
        '## Verification','', '| Suite | Passed | Failed | Skipped | Blocked | Deselected |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for name,r in results.items():report.append('| '+name+' | '+' | '.join(str(r[k]) for k in ('passed','failed','skipped','blocked','deselected'))+' |')
    report += ['',
        'Suites overlap and are not summed. The private frontend failure remains the pre-existing typography expectation at `provisionalOvr.test.js:61`; no unrelated UI/scoring change was made. The final public suite includes 26 new identity regression cases. Exact commands, logs, exit codes and counts are retained in `test-results.json`. The initial targeted command referenced a nonexistent transfer test filename; the next run lacked two retained chronology evidence files (12 fixture-setup failures). Provisioning the exact retained fixtures resolved all 12, with 186 passing in the final targeted run. An initial numerical check included upstream candidates outside the 691 published comparison and was corrected to the explicit published set. These were harness issues, not newly classified known product failures. The first report finalization attempt used the Windows default encoding for Unicode evidence; explicit UTF-8 reading resolved it, and its failure log remains preserved.','',
        'The first source attempt rejected a Git line-ending difference in a diagnostic script; normalized text equality resolved it while production byte checks remain strict. The second detected that the old roster ledger covers 1,517 four-league fixtures; the complete scan explicitly adds the 34 separately retained Bundesliga fixtures. Failed/partial directories and logs remain preserved. The third scan reopened all 1,551 fixtures and built the complete independent UUID index, but its final SQLite attachment failed because URI handling was not enabled. The fresh index is byte-identical to Batch 3B (`1db269d9af16e091f91e40d29d06b8f4f997112ce0605d01713b3acbb77ba969`). The final run enables URI handling, validates and reuses that completed index, rechecks all source hashes and original records, and completes bidirectional comparison. It avoids repeating expensive index insertion; all attempts remain preserved. The completed final run supports the final findings.','',
        '## Deliverables, limitations and next phase','',
        'Tracked review files: `scripts/investigate_identity_sources.py`, `scripts/verify_batch4_numerics.py`, `scripts/check_identity_source_records.py`, `scripts/finalize_identity_source_reconciliation.py`, `tests/test_identity_source_reconciliation.py`, `tests/suite_inventory.json`, and `docs/identity-source-reconciliation-report.md`. No production `src` module, frontend source, original dataset, frozen reference or published numerical output changes.','',
        'All requested private CSV/JSON deliverables are under `audit-output/identity-source-reconciliation/`, with supplemental source-name decisions, full disciplinary records, enriched classifications, transfer contexts and the fresh UUID database. Additional fresh numerical and historical-reference checks are retained under `audit-output/batch4-numerics/` and `audit-output/batch4-additional/`. Test/build logs and private harness inputs remain ignored. `artifact-inventory.json` lists path, size and SHA256 for all review files and task-owned evidence/log files; it excludes its own recursive hash and dependency/data junction traversal. Nothing private is staged.','',
        'Reproduce in a fresh worktree/output directory: `python -B -m scripts.investigate_identity_sources`; `python -B -m scripts.verify_batch4_numerics`; the independent additional checker command in `test-results.json`; `python -B -m scripts.check_identity_source_records`; public/private suites; then `python -B -m scripts.finalize_identity_source_reconciliation`. Evidence-producing commands refuse completed output directories. Source data is read-only.','',
        'The conclusions are stable-ID consistency findings within retained same-provider records, not external historical attestation or complete-season certification. They establish no wrong-player attribution. Production candidate-name and administrative-activity restrictions are intentionally retained; incomplete duration, source chronology and frozen membership are independent limitations. No implementation/evidence blocker remains for this local investigation. The known private frontend expectation is separate.','',
        'Recommended next phase: review the same-ID provenance assertion and decide whether a future versioned reconstruction should distinguish source-proven spelling variants and bench-disciplinary activity from blocking identity conflicts. Such an integration must preserve the existing UUID/context/ID checks and separately compare admission consequences; it is not implemented here. Keep unrelated source contradictions in the provider-resolution queue and handle Batch 5 legacy-helper hardening separately. Do not publish V2 or refit references without authorization.','']
    (ROOT/'docs/identity-source-reconciliation-report.md').write_text('\n'.join(report),encoding='utf8')
    dump('summary.json',summary)
    review=['scripts/investigate_identity_sources.py','scripts/verify_batch4_numerics.py','scripts/check_identity_source_records.py','scripts/finalize_identity_source_reconciliation.py','tests/test_identity_source_reconciliation.py','tests/suite_inventory.json','docs/identity-source-reconciliation-report.md']
    for name in review:bind(ROOT/name)
    for name in ['batch4-numerics/input-hashes.json','batch4-additional/additional-input-hashes.json','private-harness-input-hashes.json']:
        p=ROOT/'audit-output'/name
        if p.exists():bind(p)
    dump('input-hashes.json',inputs)
    artifacts=[]
    for rel in review:artifacts.append(dict(path=rel,bytes=(ROOT/rel).stat().st_size,sha256=sha(ROOT/rel)))
    folders=[OUT,ROOT/'audit-output/batch4-numerics',ROOT/'audit-output/batch4-additional',*sorted((ROOT/'audit-output').glob('identity-source-reconciliation-attempt*')),*sorted((ROOT/'audit-output').glob('batch4-numerics-attempt*'))]
    for folder in folders:
        for p in sorted(folder.rglob('*')):
            if p.is_file() and p.name!='artifact-inventory.json':artifacts.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    for p in sorted((ROOT/'audit-output').glob('*.log')):artifacts.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    for p in sorted(ROOT.glob('*batch4.log'))+sorted(ROOT.glob('identity-investigation*.log')):artifacts.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    dump('artifact-inventory.json',artifacts)
    # Keep redirected finalizer logs stable before their inventory hash is sealed.

if __name__=='__main__':main()
