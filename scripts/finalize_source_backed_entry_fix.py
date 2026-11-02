"""Finalize a completed local Batch 2B replay; assert results before reporting."""
import csv
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    root=Path.cwd();out=root/'audit-output/source-backed-entry-fix'
    read=lambda p:json.loads(p.read_text(encoding='utf8'))
    table=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig')))
    def dump(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf8')
    def sha(p):
        with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
    s=read(out/'summary.json');population=table(out/'full-population-comparison.csv')
    # Retain the completed replay's original evidence before enriching reports.
    for name in ('summary.json','appearance-comparison.csv','all-appearance-comparison.csv','input-hashes.json','output-hashes.json'):
        snapshot=out/('replay-'+name)
        if not snapshot.exists():snapshot.write_bytes((out/name).read_bytes())
    apps=table(out/'all-appearance-comparison.csv');entries=table(out/'entry-evidence.csv')
    changed=table(out/'appearance-comparison.csv');impact=table(out/'player-impact.csv')
    original=read(root/'audit-output/entry-independent-source-checks.json')
    uuid=read(root/'audit-output/entry-uuid-independent/comparison.json')
    assert len(population)==691 and len(apps)==14979 and len(impact)==10
    assert s['published_recovered_appearances']==10 and s['unchanged_other_published_players']==681
    assert s['unexpected_changes']==[] and s['source_checks']['previously_accepted_unchanged']==14537
    assert s['reference_semantic_sha256']=='403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd'
    assert s['published_sha256']=='9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e'
    published=root/'frontend/public/data/player-ratings-2015-16-v1.json'
    assert sha(published)==hashlib.sha256(subprocess.check_output(['git','show','HEAD:frontend/public/data/player-ratings-2015-16-v1.json'])).hexdigest()
    assert s['source_checks']['batch1_recoveries_preserved']==91 and s['source_checks']['batch2a_recovery_preserved']==1
    assert s['source_checks']['independent_attribute_comparisons']==13820
    assert s['source_checks']['independent_formula_b_comparisons']==2764
    assert s['source_checks']['independent_eligibility_comparisons']==2764
    assert uuid['missing_uuids']==uuid['extra_uuids']==uuid['duplicate_uuids']==0
    ie={(r['player_id'],r['match_id']):r for r in original['candidates']}
    published_entries=[e for e in entries if e['published']=='True']
    assert len(published_entries)==10
    for e in published_entries:
        r=ie[int(e['player_id']),int(e['match_id'])]
        assert (e['entry_id'],e['shift_id'],e['entry_timestamp'],e['entry_period'])==(r['entry_uuid'],r['shift_uuid'],r['timestamp'],str(r['period']))
        assert e['events_sha256']==r['events_sha256'] and e['lineups_sha256']==r['lineups_sha256']
    keys=lambda state:{(int(p['player_id']),mid) for p in population for mid in json.loads(p[state])['appearance_ids']}
    assert keys('v1')==keys('merged_batch1')=={(int(a['player_id']),int(a['match_id'])) for a in apps}
    assert keys('corrected_batch2a')==keys('proposed_batch2b')==keys('v1')-{(26023,3825670)}
    aindex={(int(a['player_id']),int(a['match_id'])):a for a in apps}
    # Expose per-appearance raw UUID counts and admission alongside the aggregate
    # impact, without changing immutable source facts or diagnostic decisions.
    pending={(p['player_id'],p['match_id']):p for p in read(out/'pending-corrected-facts.json')}
    source=root.parent/'Soccer-Impact-Engine-Index/data/derived/private-five-attribute-v2/measurement-facts.jsonl'
    prior_facts={}
    with source.open(encoding='utf8') as stream:
        for line in stream:
            f=json.loads(line);key=f['player_id'],f['match_id']
            if key in pending:prior_facts[key]=f
    for c in changed:
        key=int(c['player_id']),int(c['match_id'])
        c['before_participation_issues']=json.loads(aindex[key]['baseline_issues']) if key in aindex else None
        c['after_interval_geometry']=json.loads(c['independent'])['intervals']
        details={}
        if key in pending:
            for attr,new in pending[key]['metrics'].items():
                old=prior_facts[key]['metrics'][attr]
                details[attr]=dict(raw_numerator_count=len(new['numerator_ids']),raw_attempt_count=len(new['denominator_ids']) if new['denominator_ids'] is not None else None,
                    raw_numerator_uuids=new['numerator_ids'],raw_attempt_uuids=new['denominator_ids'],
                    before_supported=old['supported'],after_supported=new['supported'],before_seconds=old['seconds'],after_seconds=new['seconds'],
                    before_admitted_numerator=len(old['numerator_ids']) if old['supported'] else 0,
                    after_admitted_numerator=len(new['numerator_ids']) if new['supported'] else 0,
                    before_reasons=old['reasons'],after_reasons=new['reasons'])
        c['per_appearance_metric_admission']=details
    from scripts.decoder_fix_independent import write_csv
    write_csv(out/'appearance-comparison.csv',changed)
    for a in apps:
        prior_removal=(int(a['player_id']),int(a['match_id']))==(26023,3825670)
        a['original_v1_ledger_key']=True
        a['active_batch2a_ledger_key']=not prior_removal
        a['active_batch2b_ledger_key']=not prior_removal
        a['approved_removal_batch']='2A' if prior_removal else None
    write_csv(out/'all-appearance-comparison.csv',apps)
    recon=root.parent/'Soccer-Impact-Engine-Index-source-evidence-reconciliation/audit-output/source-reconciliation'
    policy=[a for a in table(recon/'disputed-appearances.csv') if a['classification']=='E']
    assert len(policy)==3
    for r in policy:
        a=aindex[int(r['player_id']),int(r['match_id'])]
        assert not a['corrected_seconds'] and a['baseline_issues']==a['corrected_issues']
    # Recheck the name-admission policy through every player's unchanged metric
    # exclusions, not a source-nickname shortcut or reference-membership change.
    additional=read(root/'audit-output/entry-additional/additional-checks.json')
    assert additional['raw_delivered_projection_vs_reconstruction_db']['mismatches']==0
    assert not additional['all_2514_reference_candidate_and_membership_discrepancies']
    tests={}
    def result(name,passed,log,failed=0,deselected=0):
        t=dict(passed=passed,failed=failed,skipped=0,blocked=0,deselected=deselected,log=log)
        text=(root/'audit-output'/log).read_text(encoding='utf8')
        if name in ('public_backend','private_backend','targeted_regressions'):
            assert f'{passed} passed' in text
            if deselected:assert f'{deselected} deselected' in text
        elif name in ('original_source_regressions','retained_independent_regressions'):
            assert f'Ran {passed} tests' in text and '\nOK' in text
        elif name in ('public_frontend','private_frontend'):
            assert f'pass {passed}' in text and f'fail {failed}' in text and 'skipped 0' in text
        elif name=='identity_join_probes':assert len(json.loads(text)['results'])==passed
        elif name=='production_build':assert 'built in' in text
        tests[name]=t
    result('public_backend',len(read(root/'tests/suite_inventory.json')['public']),'backend-public.log')
    result('private_backend',51,'backend-private-resumed.log',deselected=125)
    result('targeted_regressions',109,'entry-targeted-resumed.log')
    result('original_source_regressions',16,'original-source-regressions.log')
    result('retained_independent_regressions',12,'independent-regressions.log')
    result('identity_join_probes',12,'identity-probes.log')
    result('public_frontend',211,'frontend-public-resumed.log')
    result('private_frontend',33,'frontend-private-resumed.log',failed=1)
    tests['private_frontend']['known_failure']='provisionalOvr.test.js:61 badge label punctuation; test starts at line 44'
    result('production_build',1,'frontend-build.log')
    tests['independent_candidate_checks']=dict(passed=10,failed=0,skipped=0,blocked=0,deselected=0,artifact='audit-output/entry-independent-source-checks.json')
    tests['full_population_replay']=dict(passed=1,failed=0,skipped=0,blocked=0,deselected=0,players=691,fixtures=1551,log='full-replay-roster-scope.log')
    tests['independent_uuid_conservation']=dict(passed=1,failed=0,skipped=0,blocked=0,deselected=0,events=5436699,artifact='audit-output/entry-uuid-independent/comparison.json')
    tests['raw_delivery_and_reference_checks']=dict(passed=1,failed=0,skipped=0,blocked=0,deselected=0,projections=3626433,frozen_candidates=2514,log='additional-checks.log')
    dump(out/'test-results.json',tests)
    s['test_results']=tests;s['independent_uuid_conservation']=uuid
    s['raw_delivery_projection_check']=additional['raw_delivered_projection_vs_reconstruction_db']
    s['original_reference_candidate_membership_discrepancies']=[]
    s['explicit_appearance_key_conservation']=dict(v1=14979,batch1=14979,batch2a=14978,batch2b=14978,approved_batch2a_removal=[26023,3825670],unexplained_keys=0)
    s['permanent_exit_policy_cases_still_excluded']=len(policy)
    s['remaining_unresolved_active_appearances']=sum(not a['corrected_seconds'] and (int(a['player_id']),int(a['match_id']))!=(26023,3825670) for a in apps)
    assert s['remaining_unresolved_active_appearances']==431
    total=sum((F(json.loads(p['proposed_batch2b'])['exact_supported_minutes'])-F(json.loads(p['corrected_batch2a'])['exact_supported_minutes']) for p in impact),F(0))
    assert total==F(original['total_minutes'])==F(6517279,12000)
    s['exact_additional_verified_minutes']=str(total)
    largest=sorted(impact,key=lambda p:abs(float(p['overall_delta'])) if p['overall_delta'] else 0,reverse=True)
    s['largest_score_changes']=[dict(player_id=int(p['player_id']),name=p['name'],delta=float(p['overall_delta'])) for p in largest]
    s['supplemental_source_recoveries']=[dict(player_id=int(c['player_id']),match_id=int(c['match_id']),name=c['name'],independent=json.loads(c['independent']),after_seconds=c['after_seconds']) for c in changed if c['published']=='False']
    s.pop('supplemental_changed_nonappearances',None)
    s['off_field_discipline_preserved']=True
    s.pop('off_field_disciplinary_events_retained',None)
    s['newly_complete_except_frozen_membership']=[int(p['player_id']) for p in impact if all(':NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER' in x for x in json.loads(p['proposed_batch2b'])['exclusion_reasons'])]
    modified=subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()
    modified+=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
    report='docs/source-backed-entry-fix-report.md'
    s['modified_file_inventory']=sorted(set(modified+[report]))
    dump(out/'summary.json',s)
    byid={int(p['player_id']):p for p in impact}
    lines=['# Source-backed player-entry correction — Batch 2B','',
        'Local diagnostic correction on branch `source-backed-entry-fix`, based on merged Batch 2A `81a23aeb4c5e64c4aebba188aca602254a8ad3b3`. The prerequisite is the validated, documented implementation merged through PR #9; no formal GitHub review is claimed. Original worktrees, uncommitted work, source bytes, published ratings and frozen populations are preserved. No commit, push, merge, PR, release or deployment was made.','',
        f'**All ten proposed published appearances are independently supported and recovered.** Zero of the ten remain excluded for participation. Added elapsed exposure: `{total}` minutes = **{float(total):.10f} minutes**. This does not clear separate player/metric exclusions or grant ranking membership.','',
        '## Root cause and implementation','',
        'The adapter resolved the original first Tactical Shift endpoint correctly but classified it as `position_change`. The participation validator requires a prior position-change exit, so a first shift was rejected as `unsupported_position_change`; incoming substitutions also produced an unrepresented original-entry check. Original XI/substitution evidence already existed at the exact same period-local clock.','',
        '`statsbomb_participation._source_backed_entry` constructs one frozen `ReconstructedEntry` only after unique stable-ID original entry support, exact entry/shift clock equality, agreeing initial XI position for starters, unique compatible shift, all positional snapshots, complete boundaries, existing source checks, normal participation validation, and a separate original-event entry/exit walk with exact interval-union equality. Reversed chronology, missing/duplicate transitions, permanent-exit conflicts, overlaps, dismissals continuing through lineup intervals and snapshot contradictions remain blocking. Unknown source categories are unchanged.','',
        'Only the first internal Stint entry category and its original evidence references change. Provider lineup labels, raw positions, UUIDs, fixture/team/player identities, exact endpoint geometry and provenance remain intact. `AdaptedPlayer.reconstructed_entries` and `source_reconstruction.appearance_rows` retain the explicit entry/shift binding. No player list, tolerance, fuzzy-name rule or permanent-exit policy is added to production. Metric-specific admission runs unchanged after participation recovery.','',
        '## Original source evidence','',
        'The independent checker identifies entries directly from pinned original bytes without importing the production adapter or decision helper. Its event state machine and lineup endpoint reconstruction agree on exact unions. The full replay compares the actually loaded merged Batch 2A module against proposed production code; source schema validation remains complete.','',
        '| Player / fixture | Original entry UUID | First shift UUID | Exact period / clock | Exact seconds | Minutes |','| --- | --- | --- | --- | ---: | ---: |']
    for e in published_entries:
        pid=int(e['player_id']);r=ie[pid,int(e['match_id'])]
        lines.append(f"| {r['name']} ({pid}) / {r['match_id']} | `{r['entry_uuid']}` ({r['entry_type']}) | `{r['shift_uuid']}` | {r['period']} / {r['timestamp']} | {r['seconds']} | {float(F(r['minutes'])):.10f} |")
    lines+=['','| Player / fixture | Original events SHA256 | Original lineups SHA256 |','| --- | --- | --- |']
    for r in original['candidates']:lines.append(f"| {r['player_id']} / {r['match_id']} | `{r['events_sha256']}` | `{r['lineups_sha256']}` |")
    lines+=['','`entry-evidence.csv` retains full original entry and shift records, indices, team IDs, positions, source document paths/hashes and proof references. `appearance-comparison.csv` retains every changed source appearance, prior issue arrays and exact before/after exposure. `entry-independent-source-checks.json` independently retains full event/lineup interval geometry, snapshot/boundary UUIDs and original positions. No original observation is rewritten.','',
        '## Four-state population and rating comparisons','',
        'A = original published V1; B = corrected Batch 1; C = merged Batch 2A; D = proposed Batch 2B. All 691 players are recalculated in all four states, using independently transcribed raw UUID counts, rational exposure/rates, frozen percentiles, ratings, eligibility and Formula B. Original inputs reproduce published values; B and C reproduce sealed prior diagnostics. All 14,979 historical contribution keys remain accounted for; C and D both contain 14,978 active keys after Batch 2A’s proved Juanfran nonappearance removal.','',
        '| Player | A minutes | B minutes | C minutes | D minutes | C Formula B | D Formula B | D − C |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    fmt=lambda v:'N/A' if v is None else f'{v:.12f}'
    for p in impact:
        a,b,c,d=[json.loads(p[k]) for k in ('v1','merged_batch1','corrected_batch2a','proposed_batch2b')]
        lines.append(f"| {p['name']} ({p['player_id']}) | {a['supported_minutes']:.8f} | {b['supported_minutes']:.8f} | {c['supported_minutes']:.8f} | {d['supported_minutes']:.8f} | {fmt(c['overall'])} | {fmt(d['overall'])} | {fmt(None if d['overall'] is None or c['overall'] is None else d['overall']-c['overall'])} |")
    lines+=['','Largest absolute Formula B changes: '+ '; '.join(f"{p['name']} ({float(p['overall_delta']):+.12f})" for p in largest[:3])+'. Ratings are not assumed to increase.']
    lines+=['','### Attribute, numerator and denominator alignment','',
        'The following compares C → D. Rates use only accepted action UUIDs and their matching supported exposure. Press resistance remains successful pressured actions / attempted pressured actions, independently of elapsed minutes. CSV population records retain all four states, exact rates, per-attribute supported/excluded match IDs, attempts, counts, exposure, ratings and percentiles.','',
        '| Player | Attribute | Numerator (press attempts) | Supported minutes | Exact value | Rating | Percentile |','| --- | --- | --- | --- | --- | --- | --- |']
    for p in impact:
        c,d=[json.loads(p[k]) for k in ('corrected_batch2a','proposed_batch2b')]
        for attr in c['attributes']:
            x,y=c['attributes'][attr],d['attributes'][attr]
            num=lambda z:str(z['numerator'])+(f"/{z['attempts']}" if z['attempts'] is not None else '')
            lines.append(f"| {p['player_id']} | {attr} | {num(x)} → {num(y)} | {x['supported_minutes']:.8f} → {y['supported_minutes']:.8f} | `{x['exact_value']}` → `{y['exact_value']}` | {fmt(x['rating'])} → {fmt(y['rating'])} | {fmt(x['percentile'])} → {fmt(y['percentile'])} |")
    lines+=['','### Ranking and position implications','',
        f"Ranking eligibility changes under frozen membership: **{s['eligibility_changes']}**. Comparison-group changes: **0**. Dominant fine-position changes after both batches’ recovered exposure: `{json.dumps(s['dominant_fine_group_changes'],ensure_ascii=False)}`. These remain diagnostic metadata; frozen CB/MID groups are unchanged.",
        '',f"Players clearing other checked conditions while still lacking existing frozen membership: `{s['newly_complete_except_frozen_membership']}`. This is a future reference-membership question, not admission to current rankings. No comparison population is refitted.",'',
        '| Player | Remaining D exclusions |','| --- | --- |']
    for p in impact:lines.append(f"| {p['name']} ({p['player_id']}) | {'; '.join(json.loads(p['proposed_batch2b'])['exclusion_reasons']) or 'None'} |")
    lines+=['','## Whole-population preservation and investigated effects','',
        f"All **14,537 Batch 2A accepted appearances** retain identical validation results and exact intervals; the **91 Batch 1 recoveries** and Pallois’s Batch 2A recovery remain intact. Juanfran and the three supplemental unused-roster bench cards remain nonappearances with retained disciplinary provenance. D has **14,547 supported published appearances** and **431 active appearances with unresolved/unsupported exposure**. All other **681 published players** are exactly unchanged from C across metrics, scores, identity, eligibility and exclusions. Unexpected published changes: **0**.",
        '',f"A general source rule also corroborates **{len(s['supplemental_source_recoveries'])} nonpublished roster appearances**. The first was Łukasz Fabiański `3262/3754047`, sharing the original zero-clock XI/shift with Ki and Williams. The initial all-roster assertion stopped on this case; independent event/lineup geometry and source positions established why it changed. Every supplemental row is checked by the same independent raw-source reconstruction and recorded below; none enters the 691-player score calculation, reference membership or published JSON.",'',
        '| Nonpublished actor | Fixture | Exact seconds |','| --- | --- | ---: |']
    for c in s['supplemental_source_recoveries']:lines.append(f"| {c['name']} ({c['player_id']}) | {c['match_id']} | {c['after_seconds']} |")
    lines+=['','These source-only recoveries are retained leads for a separate future upstream admission assessment. No future reference-membership claim or new score is made for those actors.']
    lines+=['',
        'Ramos (both cases), Francis, Mendy, Pajot and all four Batch 1 residual cases retain their previous rejection issues. All three clean permanent-exit policy cases remain withheld. Fernandinho’s source-name restriction and metric-specific scope/geometry restrictions remain unchanged. No unsupported Tactical Shift alone becomes an entry. No contradictory source is clipped, guessed or silently replaced.','',
        f"Independent raw UUID inventory: **{uuid['original_events']:,} original events / 1,551 fixtures**, duplicate/missing/extra UUIDs **0/0/0**. A second disk-backed inventory built directly from hash-bound original bytes agrees bidirectionally with the replay UUID inventory. All **74,895 raw metric UUID sets** and **3,036,652 delivered event contexts** are checked in the replay. The additional checker verifies **3,626,433 Parquet projections** and all **2,514 frozen-reference candidate/membership predicates**, with zero discrepancies.",
        '',f"Frozen semantic fingerprint remains `{s['reference_semantic_sha256']}`. Public ratings SHA256 remains `{s['published_sha256']}`. Original source receipts and prior artifact hashes are rechecked before finalization; no data source/reference/population is rewritten.",'',
        '## Tests and execution limits','',
        '| Verification | Passed | Failed | Skipped | Blocked | Deselected |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for name,t in tests.items():lines.append(f"| {name} | {t['passed']} | {t['failed']} | {t['skipped']} | {t['blocked']} | {t['deselected']} |")
    lines+=['',
        'The 30 new synthetic regressions are included in the public total; the 109 targeted cases overlap that total. The 16 retained-original tests include ten entry-candidate subcases, the Batch 2A cases and specific exclusions; subcases are not extra top-level unit tests. Private deselections are outside the declared suite and are not skips. The single private frontend failure is the previously reported badge-label expectation at `provisionalOvr.test.js:61` (case begins at line 44); no UI or numerical change was made to satisfy it.','',
        'Prior incomplete attempts remain preserved: initial source checks passed but receipt writing lacked its output directory; one synthetic chronology control failed before the proof included XI/boundary chronology; the original full replay exhausted memory; initial private backend import and public frontend esbuild failed during resource contention; private frontend initially lacked its ignored fixture/support modules. The large memory/setup command was declined at the prior usage limit and did not execute. Resumed edits were small and separately reviewed. The bounded replay uses fixture-scoped indexed reads from the immutable source DB plus a new disk-backed UUID primary key. The first bounded attempt then stopped on the investigated nonpublished goalkeeper scope assertion. The completed replay and final logs alone support the final numerical results. Earlier reports and attempts are not overwritten.','',
        'The independent path does not call the production entry proof. It retains its own original-event state machine and separately resolved lineup geometry. Same-provider source reconciliation does not resolve genuine contradictions or certify historically complete seasons.','',
        '## Reproduction','',
        'Use Python 3.13, retained sibling evidence workspaces and existing locked frontend dependencies. Output-generating commands refuse existing completed directories/files; use a fresh worktree or preserve each old output under a distinct attempt name before repeating. Private harness inputs are individually fingerprint-bound in the ignored provenance manifests.','',
        '```powershell',
        'python -B -m pytest tests/test_source_backed_entry.py tests/test_off_field_cards.py tests/test_statsbomb_participation.py -q -p no:cacheprovider',
        'python -B -m scripts.check_off_field_card_sources',
        'python -B -m scripts.check_source_backed_entries',
        'python -B -m scripts.verify_source_backed_entry_fix',
        'python -B -m scripts.check_entry_uuid_conservation',
        'python -B -m scripts.check_entry_uuid_conservation --compare-only',
        'python -B -m scripts.run_backend_tests public -q',
        'python -B audit-output/run-private-backend.py',
        'python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/test_independent_audit.py',
        'python -B -c "import src, runpy; runpy.run_path(\'../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/identity_probes.py\', run_name=\'__main__\')"',
        'python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/scripts/audit_full_player_additional_checks.py --source-root ../Soccer-Impact-Engine-Index --checkout . --output audit-output/entry-additional',
        'npm.cmd run test:public --prefix frontend',
        'npm.cmd run test:private --prefix audit-output/private-suite-checkout/frontend',
        'npm.cmd run build --prefix frontend',
        'python -B -m scripts.finalize_source_backed_entry_fix','```','',
        '## Modified files and artifact inventory','']
    lines += [f'- `{p}`' for p in s['modified_file_inventory']]
    lines += ['','Required ignored outputs under `audit-output/source-backed-entry-fix/`: `appearance-comparison.csv`, `player-impact.csv`, `full-population-comparison.csv`, `entry-evidence.csv`, `summary.json`, `input-hashes.json`, `test-results.json`. Supplemental files include `all-appearance-comparison.csv`, baseline/pending diagnostic facts, the merged adapter snapshot, `uuid-conservation.sqlite`, `output-hashes.json` and `artifact-inventory.json`. Independent source/UUID evidence, additional raw/reference checks, private harness provenance, logs and failed attempts remain under `audit-output/`. Large files and source evidence remain ignored.','',
        'Recommended next correction batch: separately review the three source-corroborated permanent-exit support-policy cases, with explicit terminal-exit semantics and conflict regressions. Keep genuine source contradictions and nickname policy outside that batch. Published numerical changes and any new reference population require separate approval.','']
    (root/report).write_text('\n'.join(lines),encoding='utf8')
    # Bind all consumed independent/test receipts and implementation/report files.
    receipts=read(out/'input-hashes.json')
    extra=[root/p for p in s['modified_file_inventory']]+[root/'audit-output'/t['log'] for t in tests.values() if 'log' in t]
    extra += [root/'audit-output/entry-independent-source-checks.json',root/'audit-output/entry-uuid-independent/input-hashes.json',root/'audit-output/entry-uuid-independent/comparison.json',root/'audit-output/private-harness-resumed-input-hashes.json',root/'audit-output/private-frontend-provenance.json',root/'audit-output/entry-additional/additional-checks.json']
    for p in extra:receipts[str(p.resolve())]=dict(sha256=sha(p),bytes=p.stat().st_size)
    dump(out/'input-hashes.json',receipts)
    for path,r in receipts.items():assert sha(Path(path))==r['sha256'],path
    dump(out/'output-hashes.json',{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in ('output-hashes.json','artifact-inventory.json')})
    # Flush the completion receipt before hashing redirected stdout as an artifact.
    print(json.dumps(dict(recovered=10,additional_minutes=float(total),eligibility_changes=s['eligibility_changes'],supplemental_source_recoveries=len(s['supplemental_source_recoveries']),report=report,modified=s['modified_file_inventory']),indent=2),flush=True)
    inventory={}
    def walk(directory):
        for p in directory.iterdir():
            if p.is_symlink() or p.is_junction():continue
            if p.is_dir():walk(p)
            elif p.is_file() and p!=out/'artifact-inventory.json':inventory[str(p.relative_to(root))]=dict(bytes=p.stat().st_size,sha256=sha(p))
    walk(root/'audit-output')
    dump(out/'artifact-inventory.json',inventory)


if __name__=='__main__':main()
