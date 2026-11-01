"""Produce the local Batch 2A review from completed source replay and test logs."""
import ast
import csv
import hashlib
import json
import os
from pathlib import Path


def main():
    root=Path.cwd();out=root/'audit-output/off-field-card-fix';source=root.parent/'Soccer-Impact-Engine-Index'
    read=lambda p:json.loads(p.read_text(encoding='utf8'))
    table=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig')))
    def dump(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    s=read(out/'summary.json');population=table(out/'full-population-comparison.csv');apps=table(out/'all-appearance-comparison.csv');evidence=table(out/'off-field-card-evidence.csv')
    impact={int(p['player_id']):p for p in table(out/'player-impact.csv')}
    assert len(population)==691 and len(apps)==14979 and len(evidence)==5 and set(impact)=={3256,26023}
    assert s['unexpected_changes']==[] and s['unchanged_other_published_players']==689
    assert s['comparison_group_changes']==0 and s['dominant_fine_group_changes']==[]
    historical_keys={(int(a['player_id']),int(a['match_id'])) for a in apps}
    original_keys={(int(p['player_id']),mid) for p in population for mid in json.loads(p['v1'])['appearance_ids']}
    baseline_keys={(int(p['player_id']),mid) for p in population for mid in json.loads(p['merged_batch1'])['appearance_ids']}
    corrected_keys={(int(p['player_id']),mid) for p in population for mid in json.loads(p['corrected_batch2a'])['appearance_ids']}
    assert original_keys==baseline_keys==historical_keys and len(historical_keys)==14979
    assert corrected_keys==historical_keys-{(26023,3825670)} and len(corrected_keys)==14978
    s['explicit_appearance_key_conservation']=dict(original=len(original_keys),baseline=len(baseline_keys),corrected=len(corrected_keys),explained_removed_key=[26023,3825670],lost_legitimate_keys=0,unexpected_keys=0)
    additional=read(root/'audit-output/off-field-additional/additional-checks.json')
    assert additional['raw_delivered_projection_vs_reconstruction_db']['mismatches']==0
    assert not additional['all_2514_reference_candidate_and_membership_discrepancies']
    s['raw_delivery_projection_check']=additional['raw_delivered_projection_vs_reconstruction_db']
    s['original_reference_candidate_membership_discrepancies']=[]
    # Every reported disciplinary record is exactly the original JSON event;
    # a participation correction is not deletion of a disciplinary observation.
    for e in evidence:
        raw=Path(e['events_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==e['events_sha256']
        event=next(x for x in json.loads(raw) if x['id']==e['event_id'])
        assert event==json.loads(e['original_event']) and event['player']['id']==int(e['player_id'])
    tree=ast.parse((root/'tests/test_off_field_cards.py').read_text(encoding='utf8'))
    new_cases=sum(isinstance(m,ast.FunctionDef) and m.name.startswith('test_') for c in tree.body if isinstance(c,ast.ClassDef) for m in c.body)
    public_count=len(read(root/'tests/suite_inventory.json')['public'])
    tests={
        'public_backend':dict(passed=public_count,failed=0,skipped=0,blocked=0,deselected=0,log='backend-public.log'),
        'private_backend':dict(passed=51,failed=0,skipped=0,blocked=0,deselected=125,log='backend-private.log'),
        'original_source_regressions':dict(passed=15,failed=0,skipped=0,blocked=0,deselected=0,log='original-source-regressions.log'),
        'retained_independent_regressions':dict(passed=12,failed=0,skipped=0,blocked=0,deselected=0,log='independent-regressions.log'),
        'identity_join_probes':dict(passed=12,failed=0,skipped=0,blocked=0,deselected=0,log='identity-probes.log'),
        'public_frontend':dict(passed=211,failed=0,skipped=0,blocked=0,deselected=0,log='frontend-public.log'),
        'private_frontend':dict(passed=33,failed=1,skipped=0,blocked=0,deselected=0,log='frontend-private.log',known_failure='provisionalOvr.test.js:61 obsolete badge typography expectation; enclosing test starts at line 44'),
        'production_build':dict(passed=1,failed=0,skipped=0,blocked=0,deselected=0,log='frontend-build.log')}
    for name,t in tests.items():
        log=(root/'audit-output'/t['log']).read_text(encoding='utf8')
        if name in ('public_backend','private_backend'):
            assert f"{t['passed']} passed" in log
            assert f"{t['deselected']} outside this selection" in log
        elif name in ('original_source_regressions','retained_independent_regressions'):assert f"Ran {t['passed']} tests" in log and 'OK' in log
        elif name=='identity_join_probes':assert len(json.loads(log)['results'])==12
        elif name in ('public_frontend','private_frontend'):assert f"pass {t['passed']}" in log and f"fail {t['failed']}" in log and 'skipped 0' in log
        else:assert 'built in' in log
    s['new_synthetic_regressions_included_in_public']=new_cases;assert new_cases==36
    s['test_results']=tests;dump(out/'test-results.json',tests)
    # Source/research restrictions retained by the full replay and explicit tests.
    prior=root.parent/'Soccer-Impact-Engine-Index-source-evidence-reconciliation/audit-output/source-reconciliation'
    aindex={(a['player_id'],a['match_id']):a for a in apps}
    b2b=[a for a in table(prior/'recoverable-appearances.csv') if a['classification']=='B']
    permanent=[a for a in table(prior/'disputed-appearances.csv') if a['classification']=='E']
    for a in b2b+permanent:
        now=aindex[a['player_id'],a['match_id']];assert not now['corrected_seconds'] and now['baseline_status']==now['corrected_status']
    s['deferred_batch2b_entries_still_excluded']=len(b2b);s['permanent_exit_policy_cases_still_excluded']=len(permanent)
    assert len(b2b)==10 and len(permanent)==3
    jp=impact[26023];pp=impact[3256]
    jv,jb,ja=(json.loads(jp[k]) for k in ('v1','merged_batch1','corrected_batch2a'))
    pv,pb,pa=(json.loads(pp[k]) for k in ('v1','merged_batch1','corrected_batch2a'))
    s['affected_player_results']={str(pid):dict(name=p['name'],v1=json.loads(p['v1']),merged_batch1=json.loads(p['merged_batch1']),corrected_batch2a=json.loads(p['corrected_batch2a']),added_supported_minutes=float(p['added_supported_minutes']),overall_delta=float(p['overall_delta'])) for pid,p in impact.items()}
    s['newly_complete_except_frozen_membership']=[int(p['player_id']) for p in impact.values()
        if all(':NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER' in reason for reason in json.loads(p['corrected_batch2a'])['exclusion_reasons'])]
    s['current_unresolved_active_appearances']=sum(not a['corrected_seconds'] and a['removed_nonappearance']!='True' for a in apps)
    assert s['current_unresolved_active_appearances']==441
    modified=['src/statsbomb_participation.py','src/source_reconstruction.py','scripts/decoder_fix_independent.py','scripts/off_field_card_independent.py','scripts/verify_off_field_card_fix.py','scripts/check_off_field_card_sources.py','scripts/finalize_off_field_card_fix.py','tests/test_off_field_cards.py','tests/suite_inventory.json','docs/off-field-card-fix-report.md']
    s['modified_file_inventory']=modified
    cols=['tackles','interceptions','recoveries','press_resistance','progressive_passing']
    def f(v):return 'N/A' if v is None else f'{v:.12f}'
    def count_display(a):return str(a['numerator']) if a['attempts'] is None else f"{a['numerator']}/{a['attempts']}"
    report=[
        '# Off-field disciplinary-card correction — Batch 2A',
        '',
        f"Review date: 1 November 2026. Branch `off-field-card-fix`, freshly fetched merged Batch 1 baseline `{s['base_commit']}`. Isolated worktree `{root.as_posix()}`. Original dirty workspaces and earlier audits were preserved read-only. No commit, push, merge, PR, deployment or ratings release was made.",
        '',
        '**The confirmed defect is corrected and source-replayed.** Juanfran’s unused-roster disciplinary record no longer creates an asserted playing appearance. Pallois’s already-supported event/lineup intervals are recovered, with his subsequent disciplinary card retained separately. The three supplemental unused-roster cases are also corrected. No other source appearance decision changes.',
        '',
        f"Published scope: **691 players and all 14,979 historical contribution keys**, across **1,551 fixtures and {s['source_checks']['original_events']:,} original events**. Corrected diagnostics contain **14,978 active contribution keys**: one proved phantom is removed, rather than replaced with a fictitious zero-minute appearance. Supported interval count changes **14,536 → 14,537**. Exactly **two published players / two historical contributions** are affected. Three other source cases are nonpublished and receive no published-score claim. The other **689 published players are unchanged relative to merged Batch 1**.",
        '',
        '## Root cause and exact correction',
        '',
        '`_check_original_transitions` previously required a represented participation endpoint for every red/second-yellow event, regardless of whether the actor was playing. `appearance_rows` uses observations or blocking source checks to identify asserted appearances. This converted a bench disciplinary record into a phantom appearance, and rejected a legitimately substituted player for a later off-field card.',
        '',
        'The original checker still runs unchanged. A separate `_off_field_discipline` proof in `src/statsbomb_participation.py` may remove only the `original_transition_not_represented` check whose exact UUID reference belongs to a proved off-field Bad Behaviour card. All other source checks remain. Frozen `OffFieldDiscipline` records carry the original event reference, classification and corroborating lineup/XI/boundary/transition references. `AdaptedPlayer.off_field_discipline` and `source_reconstruction.appearance_rows` preserve that nonblocking provenance; it does not make `active_appearance` true.',
        '',
        'Unused-roster proof requires a complete, unique 11-actor original XI, reliable original period boundaries, no playing-position stint, XI/tactical membership, incoming substitution, return/exit or playing activity for that stable team/player ID. An explicit non-substitute position on the disciplinary actor also blocks the proof. Post-substitution proof requires existing valid stints, an independently walked original entry/temporary-exit/return/substitution sequence, exact event/lineup interval-union equality, no other source inconsistency, and no subsequent playing activity or lineup snapshot. All original source identity and schema checks execute before this classification.',
        '',
        'Precise period-local clocks are retained. A same-time substitution/card needs original indices establishing their order; missing or conflicting ordering makes the proof abstain. One-millisecond differences remain exact. A card before entry, during a temporary absence, after an unsupported permanent exit, or with unreliable coverage is not automatically off-field. Foul Committed remains playing evidence, including its red/second-yellow events. No blanket Bad Behaviour/card suppression, timing tolerance, endpoint inference, final-whistle clipping or name-based merge was introduced. Provider strings and stable IDs are unchanged.',
        '',
        '## Original source corrections',
        '',
        '| Player / fixture | Original decision | Corrected decision | Supported exposure added |',
        '| --- | --- | --- | ---: |',
        '| Juanfran 26023 / 3825670 | Phantom rejected appearance | Bench roster only; no asserted appearance | 0; no playing time invented |',
        '| Nicolas Pallois 3256 / 3900519 | Conflicting evidence | Existing intervals supported | 1573.137 s / 26.21895 min |',
        '| 6672 / 3825869 | Phantom upstream appearance | Bench roster only | None; nonpublished |',
        '| 10612 / 3825885 | Phantom upstream appearance | Bench roster only | None; nonpublished |',
        '| 40458 / 3878555 | Phantom upstream appearance | Bench roster only | None; nonpublished |',
        '',
        'Juanfran’s original Bad Behaviour / Red Card UUID is `e8bbbe1d-37fb-4ffb-92dd-ee93a07c6481`, period 2 `00:35:16.470`, with original position `Substitute` and no independently supported entry or playing-position stint. The original roster row, fixture ID, card and byte-bound provenance survive. The original V1 and merged-baseline canonical fixture sets are immutable inputs; only a copied corrected diagnostic scope removes the false contribution.',
        '',
        'Pallois: original XI → temporary exit UUID `57e0aba7-b4e4-4c32-913a-fb4070a4f71b` at period 1 `00:06:29.128` → return UUID `8dfec95b-f3aa-4c8d-a732-ab754bfd7653` at `00:09:26.133` → injury substitution UUID `97e31f4a-5b3f-42d1-904c-e50b384d219d` at `00:29:10.142`. The original supported intervals are exactly `[0,389.128]` and `[566.133,1750.142]` seconds in period 1. Their sum is **1573137/1000 seconds**. The absence is **177.005 seconds**, explicitly excluded. The later red card UUID `7524424d-4b7b-482d-93eb-0611dde9d8b1`, period 2 `00:49:09.389`, occurs after the proved substitution in both exact clock and original index order.',
        '',
        'All five exact event documents and lineup SHA256 values are listed below; provider references and original fixture/report hashes are also retained per row in `appearance-comparison.csv` and `input-hashes.json`.',
        '',
        '| Player / fixture | Original events SHA256 | Original lineups SHA256 |',
        '| --- | --- | --- |',
        *[f"| {e['player_id']} / {e['match_id']} | `{e['events_sha256']}` | `{e['lineups_sha256']}` |" for e in evidence],
        '',
        'Supplemental disciplinary UUIDs: `64a577f6-1bd2-4ca5-bc3d-f6c8c61c157b` (6672), `12abeefa-7d37-4b1d-b674-1487b0eebc9b` (10612), and `66115c24-7ba3-4208-a1d4-a4f92e2103c3` (40458). They are source-adapter corrections outside the 691-published-recipient calculation. Their upstream sealed measurements and reference membership are not rewritten or rescored in this task.',
        '',
        '## Independent verification and complete replay',
        '',
        '`scripts/off_field_card_independent.py` uses its own raw-event state walk and raw lineup endpoint reconstruction. It never imports the production off-field decision, adapter Stints or source-check result. The retained decoder oracle now exposes its separately resolved lineup interval union, position intervals and endpoint UUIDs as evidence, without changing its legacy interpretation. The new checker retains original disciplinary UUIDs while separating proved off-field discipline from its state transitions. A regression replaces the production decision with an exception and confirms the independent calculation still succeeds.',
        '',
        'The replay executes the actual merged-baseline module obtained from Git and the corrected adapter for every original fixture, then compares all 14,979 published ledger rows and all source roster actors. A diagnostic-only timestamp cache and relevance index optimize the unchanged original-transition check; the complete source schema pass and new off-field proof still see all source records and actor activity. Independent event arithmetic consumes a transition index but its playing-activity/recipient proof sees the full raw events. No optimization is installed in production.',
        '',
        f"Fresh assertion counts: `{json.dumps(s['source_checks'],sort_keys=True)}`. All **91 Batch 1 recoveries** and both off-camera labels remain intact. All **14,536 previously accepted intervals are identical**, with exact normalized geometry checks on **14,537 corrected accepted intervals**. Raw numerator/pressure-attempt UUID sets are conserved in 74,895 attribute/appearance checks. All canonical names and stable IDs agree with original same-fixture rosters; duplicate source UUIDs, lost legitimate ledger keys and unexpected decisions: **0**.",
        '',
        f"All {s['raw_red_or_second_yellow_events']} original red/second-yellow events remain in the unchanged source universe. The five reclassified disciplinary records are compared field-for-field against the original JSON; no UUID or disciplinary observation is deleted. Juanfran has no selected metric numerator or pressure-attempt UUID in the removed contribution, so removing that nonappearance drops no legitimate measured action. Original versus corrected observation keys and reasons are explicit in `all-appearance-comparison.csv`.",
        '',
        f"The additional independent check covers **{s['raw_delivery_projection_check']['rows']:,} delivered Parquet projections**, with **0** reconstruction-index mismatches, and all **2,514 original frozen-reference candidate/membership predicates**, with **0** discrepancies. The reference is validated against its sealed fingerprint and existing members; no new reference population is fitted. {s['prior_artifacts_preserved']} bound previous audit artifacts are reverified unchanged.",
        '',
        '## Private diagnostic measurements and Formula B',
        '',
        'Three distinct input sets are retained in every population row: original V1 observations, merged Batch 1 diagnostics and corrected Batch 2A diagnostics. Original inputs reproduce every public attribute rating/percentile, overall value or N/A outcome, and eligibility decision. The merged baseline also reproduces the previous exact attribute values, numerators, exposure, percentiles, scores and exclusion sets. Production aggregation/scoring and separately transcribed raw-set/rational arithmetic agree. Original definitions and the fixed reference are used throughout.',
        '',
        f"Frozen semantic fingerprint: `{s['reference_semantic_sha256']}`. Public ratings SHA256: `{s['published_sha256']}`. Neither file is modified. Press resistance remains successful pressured actions / attempted pressured actions; supported elapsed exposure affects its completeness predicates but never changes its action-ratio definition.",
        '',
        '| Player | V1 minutes | Batch 1 minutes | Batch 2A minutes | Batch 1 OVR | Batch 2A OVR | Delta |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
        *[f"| {p['name']} ({pid}) | {json.loads(p['v1'])['supported_minutes']:.8f} | {json.loads(p['merged_batch1'])['supported_minutes']:.8f} | {json.loads(p['corrected_batch2a'])['supported_minutes']:.8f} | {f(json.loads(p['merged_batch1'])['overall'])} | {f(json.loads(p['corrected_batch2a'])['overall'])} | {float(p['overall_delta']):+.12f} |" for pid,p in sorted(impact.items())],
        '',
        '**Pallois, merged Batch 1 → corrected Batch 2A:**',
        '',
        '| Attribute | Numerator / attempts before → after | Exact value before → after | Rating before → after | Percentile before → after |',
        '| --- | --- | --- | --- | --- |',
        *[f"| {a} | {count_display(pb['attributes'][a])} → {count_display(pa['attributes'][a])} | `{pb['attributes'][a]['exact_value']}` → `{pa['attributes'][a]['exact_value']}` | {f(pb['attributes'][a]['rating'])} → {f(pa['attributes'][a]['rating'])} | {f(pb['attributes'][a]['percentile'])} → {f(pa['attributes'][a]['percentile'])} |" for a in cols],
        '',
        'Pallois gains no tackles, one interception, two recoveries and one progressive pass from the corroborated appearance. Those actions are admitted only with the same supported elapsed denominator. His total pressured successes/attempts remain 58/94 and his press-resistance value/rating are unchanged. Extra exposure reduces some per-90 rates, so neither individual ratings nor the overall change are presumed to increase. The independently recomputed overall change agrees with the prior hypothesis; that earlier value is an asserted comparison, not the input to the new calculation.',
        '',
        '**Juanfran:** no minute, action count, exact attribute value, rating, percentile or Formula B value changes. His original and corrected values are retained for all five attributes in `player-impact.csv`. The change is removal of one unsupported nonappearance from metric/exposure completeness, not invented time or a score increase.',
        '',
        f"**Ranking eligibility changes: {s['eligibility_changes']}.** Juanfran clears the other checked completeness conditions after the false contribution is removed, but still lacks existing frozen attribute membership. Pallois remains excluded; his separate `3256/3829452` permanent-exit support-policy case is still withheld. All original and corrected exclusion reasons are retained, without automatic promotion. Comparison groups and dominant fine-position groups remain unchanged. No Batch 2B entry exposure is included.",
        '',
        '## Conflicts and deferred work',
        '',
        'Both Ramos cases (`5201/267533`, `5201/3825879`), Francis `3608/3754058`, Mendy `4506/3829490`, and all four unresolved Batch 1 cases (`23349/3879602`, `40430/3879772`, `3577/3879863`, `13730/3901259`) remain excluded with their previous source contradictions. Every other previously rejected published appearance remains rejected, except the single supported Pallois recovery and Juanfran’s explicit nonappearance removal. In total **441 active appearances retain unresolved/unsupported exposure** after this correction; this count includes genuine coverage and policy exclusions, not 441 demonstrated implementation bugs.',
        '',
        'All ten corroborated Tactical Shift entry proposals remain deferred to Batch 2B. The three clean permanent-exit support-policy cases remain excluded for later review. Other conflicting lineups, missing source evidence, exact chronology exceptions and conservative name-admission restrictions remain intact. This same-provider reconstruction corroborates retained source geometry; it does not certify complete historical seasons or replace missing games with zero observations.',
        '',
        '## Tests and build',
        '',
        '| Verification | Passed | Failed | Skipped | Blocked | Deselected |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
        *[f"| {name} | {t['passed']} | {t['failed']} | {t['skipped']} | {t['blocked']} | {t['deselected']} |" for name,t in tests.items()],
        '',
        f"The public suite includes **{new_cases} new regressions**, not an additional {new_cases} tests to add to the public total. They cover both disciplinary card types, unused and substituted states, genuine active dismissals, continuing lineups, pre-entry cards, temporary absences, ambiguous coverage/state, equal-time source order, millisecond separation, missing/duplicate entries or substitutions, conflicting IDs/names, after-exit actor/recipient activity, retained UUIDs, aliases and checker independence. The 15 source regressions include ten Batch 2B subcases and three permanent-policy subcases; these subcases are not extra top-level test counts. The 125 private deselections are outside that suite and are not skips.",
        '',
        'The private frontend retains the known obsolete badge em-dash/typography expectation failure at `provisionalOvr.test.js:61` (test begins at line 44). No ratings or frontend behavior was changed to make it pass. Its current application files and reviewed private test fingerprints are bound in `audit-output/private-frontend-provenance.json`.',
        '',
        'Unsuccessful setup/diagnostic attempts are retained: the first synthetic run had four fixture-serialization errors because its index helper cached Fraction clocks into test JSON; copying before parsing fixed the fixture helper. A private frontend provisioning attempt lacked its static toy-data directory and was rerun after restoring the exact fixture. Two source-replay harness attempts compared module-local dataclass types and tuple-valued issue IDs directly to separately loaded/JSON records; their structural comparison was corrected without changing production decisions. Only the completed final replay supplies these results. A final full public suite was rerun after the independent transition-index change and passed.',
        '',
        '## Reproduction',
        '',
        'Use Python 3.13 with the project requirements, locked frontend dependencies and the authorized retained sibling evidence workspaces. All new large outputs are ignored. The replay refuses an existing output directory; preserve or rename a previous run before repeating it.',
        '',
        '```powershell',
        'python -B -m scripts.verify_off_field_card_fix',
        'python -B -m scripts.run_backend_tests public -q',
        'python -B audit-output/run-private-backend.py',
        'python -B -m scripts.check_off_field_card_sources',
        'python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/test_independent_audit.py',
        'python -B -c "import src, runpy; runpy.run_path(\'../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/identity_probes.py\', run_name=\'__main__\')"',
        'python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/scripts/audit_full_player_additional_checks.py --source-root ../Soccer-Impact-Engine-Index --checkout . --output audit-output/off-field-additional',
        'npm.cmd run test:public --prefix frontend',
        'npm.cmd run test:private --prefix audit-output/private-suite-checkout/frontend',
        'npm.cmd run build --prefix frontend',
        'python -B -m scripts.finalize_off_field_card_fix',
        '```',
        '',
        'The ignored private backend harness fingerprint-checks the authorized private sources and imports corrected modules before read-only support modules. The ignored frontend harness contains unchanged current application files, the reviewed private tests/fixture, and read-only data/dependency junctions; it does not modify a previous audit checkout. Test/log hashes and original source receipts are in the final manifest.',
        '',
        '## Complete modified-file and output inventory',
        '',
        *['- `'+p+'`' for p in modified],
        '',
        'Required private files under `audit-output/off-field-card-fix/`: `appearance-comparison.csv` (five published/supplemental source cases), `player-impact.csv` (two published players), `full-population-comparison.csv` (691 players), `off-field-card-evidence.csv` (five original disciplinary records), `summary.json`, `input-hashes.json`, `test-results.json`.',
        '',
        'Supplemental outputs there: `all-appearance-comparison.csv` (14,979 retained historical keys, with the explicit nonappearance removal), `baseline-diagnostic-facts.json`, `pending-corrected-facts.json`, `merged_baseline_statsbomb_participation.py`, `output-hashes.json`, `artifact-inventory.json`. `audit-output/off-field-additional/` contains independent delivery/reference/coverage results and receipts. Private harnesses, provenance, source-test receipts, all final logs and unsuccessful attempt logs remain under `audit-output/`; the artifact inventory gives every retained private file path, size and SHA256, without following read-only junctions.',
        '',
        'All corrections and numerical comparisons remain local and uncommitted. Published player JSON, V1 scores, frozen reference files, original provider files, Formula B, attribute definitions, identity-admission rules, permanent-exit policy and frontend are unchanged. No team photos or unrelated site changes are included.'
    ]
    report_path=root/'docs/off-field-card-fix-report.md';report_path.write_text('\n'.join(report)+'\n',encoding='utf8')
    receipts=read(out/'input-hashes.json')
    for extra in (root/'audit-output/off-field-additional/additional-input-hashes.json',root/'audit-output/off-field-source-test-input-hashes.json'):
        receipts.update(read(extra))
    paths=[root/p for p in modified if p!=str(report_path.relative_to(root)).replace('\\','/')]+[root/'audit-output'/t['log'] for t in tests.values()]+[root/'audit-output/private-frontend-provenance.json']
    for path in paths:
        with path.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
        receipts[str(path.resolve())]=dict(sha256=h,bytes=path.stat().st_size)
    for path,r in receipts.items():
        with Path(path).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==r['sha256'],path
    s['final_input_receipts_reverified']=len(receipts);dump(out/'input-hashes.json',receipts);dump(out/'summary.json',s)
    inventory=[]
    for folder,dirs,files in os.walk(root/'audit-output',followlinks=False):
        dirs[:]=[name for name in dirs if name!='node_modules' and not (Path(folder)/name).is_junction() and not (Path(folder)/name).is_symlink()]
        for name in files:
            p=Path(folder)/name
            if p.name in ('artifact-inventory.json','output-hashes.json'):continue
            with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
            inventory.append(dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=h))
    dump(out/'artifact-inventory.json',inventory)
    outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='output-hashes.json'}
    outputs['../../docs/off-field-card-fix-report.md']=hashlib.sha256(report_path.read_bytes()).hexdigest();dump(out/'output-hashes.json',outputs)
    print(json.dumps(dict(published_players=s['published_affected_players'],recovered=s['published_recovered_appearances'],removed=s['published_removed_nonappearances'],supplemental=s['supplemental_changed_nonappearances'],pallois_before=pb['overall'],pallois_after=pa['overall'],juanfran_unchanged=ja['overall'],eligibility_changes=s['eligibility_changes'],test_results=tests),indent=2))


if __name__=='__main__':main()
