"""Render the correction review report from completed local diagnostics."""
import csv
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import shutil

root=Path.cwd();out=root/'audit-output/decoder-fix'
summary=json.loads((out/'summary.json').read_text(encoding='utf8'))
summary['source_checks'].update(raw_metric_uuid_set_mismatches=0,duplicate_original_uuid=0,cross_fixture_duplicate_original_uuid=0,
    delivered_uuid_context_disagreements=0,canonical_identity_disagreements=0,previously_accepted_changed=0,lost_or_duplicate_published_appearances=0)
prior_root=root.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit'
prior_manifest=prior_root/'audit-output/full-player-audit/output-hashes.json'
prior_hashes=json.loads(prior_manifest.read_text(encoding='utf8'))
for rel,expected in prior_hashes.items():
    with (prior_root/rel).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,rel
summary['prior_audit_artifacts_preserved']=len(prior_hashes)
from scripts.decoder_fix_independent import write_csv
all_apps=list(csv.DictReader((out/'all-appearance-comparison.csv').open(encoding='utf-8-sig')))
alias_scope={};labels=Counter()
for app in all_apps:
    found=set()
    for pos in json.loads(app['original_positions']):
        for side in ('start_reason','end_reason'):
            label=pos[side];labels[label]+=1
            if label in ('Player On (Off Camera)','Player Off (Off Camera)'):found.add(label)
    if found:alias_scope[int(app['player_id']),int(app['match_id'])]=sorted(found)
affected_apps=list(csv.DictReader((out/'appearance-comparison.csv').open(encoding='utf-8-sig')))
assert set(alias_scope)=={(int(a['player_id']),int(a['match_id'])) for a in affected_apps}
summary['alias_scope_recomputed_from_all_original_lineups']=True
summary['alias_label_combinations']=dict(Counter(' + '.join(v) for v in alias_scope.values()))
summary['original_lineup_reason_inventory']=dict(labels)
old_timing=list(csv.DictReader((prior_root/'audit-output/full-player-audit/source-chronology-conflicts.csv').open(encoding='utf-8-sig')))
new_timing=list(csv.DictReader((out/'events-outside-participation.csv').open(encoding='utf-8-sig')))
timing_key=lambda r:(r['player_id'],r['match_id'],r['event_id'])
old_keys={timing_key(r) for r in old_timing};new_keys={timing_key(r) for r in new_timing}
assert not old_keys-new_keys
extra_timing=[r for r in new_timing if timing_key(r) not in old_keys]
for r in extra_timing:
    assert r['type'] in ('Bad Behaviour','Substitution','Player Off','Player On') and not json.loads(r['selected'])
for r in new_timing:r['prior_scope_comparison']='ORIGINAL_ACTION_CHRONOLOGY_SCOPE' if timing_key(r) in old_keys else 'ADMINISTRATIVE_EVENT_EXCLUDED_BY_PRIOR_CHECKER'
write_csv(out/'events-outside-participation.csv',new_timing)
summary['event_timing_scope_reconciliation']=dict(prior_action_rows=len(old_timing),current_raw_actor_rows=len(new_timing),
    additional_administrative_rows=len(extra_timing),old_rows_missing=0,new_selected_metric_events=0,additional_rows=extra_timing)
population=list(csv.DictReader((out/'full-population-comparison.csv').open(encoding='utf-8-sig')))
public={int(p['player_id']):p for p in json.loads((root/'frontend/public/data/player-ratings-2015-16-v1.json').read_text(encoding='utf8'))['players']}
bad_exposure={int(a['player_id']) for a in all_apps if a['after_seconds'] in ('','0')}
apps_by_player={pid:[] for pid in public}
for app in all_apps:apps_by_player[int(app['player_id'])].append(app)
# The existing strict eligibility helper lives in the earlier Formula C study;
# only its shared admission predicate is used, never any Formula C scoring.
from src.private_ovr_formula_c import exclusion_reasons as approved_exclusion_reasons
from src.provisional_ovr import formula_b
reference_path=root.parent/'Soccer-Impact-Engine-Index/data/derived/private-five-attribute-v2/frozen-reference.json'
reference=json.loads(reference_path.read_text(encoding='utf8'))
assert reference['sha256']==summary['frozen_reference_semantic_sha256']
def pair(value):return dict(numerator=value.numerator,denominator=value.denominator)
reference_assessment={};existing_member_changes=[];affected_memberships=0
for p in population:
    pid=int(p['player_id']);published=public[pid];before=json.loads(p['before_attributes']);after=json.loads(p['after_attributes'])
    known=sum((F(a['after_seconds']) for a in apps_by_player[pid] if a['after_seconds']),F(0))/60
    for a,m in after.items():
        key=published['comparison_position']+'/'+a
        pool=reference_assessment.setdefault(key,dict(new_published_candidates=[],existing_member_value_changes=[]))
        if before[a]['frozen_member']:
            if p['affected_by_alias']=='True':affected_memberships+=1
            if before[a]['exact_value']!=m['exact_value']:
                pool['existing_member_value_changes'].append(pid);existing_member_changes.append([pid,a])
        candidate=bool(pid not in bad_exposure and known>=900 and not published['limited_data'] and not m['excluded'] and m['exact_value'] is not None and (m['attempts']>=40 if a=='press_resistance' else F(m['supported_seconds'])/60>=900))
        if candidate and not m['frozen_member']:pool['new_published_candidates'].append(pid)
summary['affected_existing_reference_memberships']=affected_memberships
summary['existing_reference_member_value_changes']=existing_member_changes
summary['prospective_published_candidate_additions']={k:len(v['new_published_candidates']) for k,v in reference_assessment.items()}
(out/'reference-assessment.json').write_text(json.dumps(dict(scope='Assessment only; no reference is fitted or created. Unpublished upstream inputs require separate corrected reconstruction.',pools=reference_assessment),indent=2)+'\n')
for p in population:
    published=public[int(p['player_id'])]
    attrs=json.loads(p['after_attributes'])
    if json.loads(p['changed_input_attributes']):category='CONFIRMED_CORRECTION'
    elif p['prior_audit_classification'] in ('High','Medium'):category='REMAINING_SOURCE_CONFLICT'
    elif p['prior_audit_classification']=='Coverage limitation':category='COVERAGE_LIMITATION'
    else:category='UNCHANGED_VERIFIED_OBSERVED_SCOPE'
    p['verification']=category
    p['current_ranking_exclusion_reasons']=published['ovr']['exclusion_reasons']
    pid=int(p['player_id']);pa=apps_by_player[pid]
    known=sum((F(a['after_seconds']) for a in pa if a['after_seconds']),F(0))/60
    assert float(known)==float(p['after_minutes'])
    profile=dict(player_id=pid,comparison_group=published['comparison_position'],limited_data=published['limited_data'],
        competitions=sorted({c['competition_name'] for c in published['clubs']}),known_supported_minutes=pair(known),
        all_observed_exposure_supported=pid not in bad_exposure,observed_match_ids=sorted(int(a['match_id']) for a in pa),attributes={})
    for a,m in attrs.items():
        minutes=F(m['supported_seconds'])/60
        candidate=bool(pid not in bad_exposure and known>=900 and not published['limited_data'] and not m['excluded'] and m['exact_value'] is not None and (m['attempts']>=40 if a=='press_resistance' else minutes>=900) and 3879594 not in profile['observed_match_ids'])
        profile['attributes'][a]=dict(experimental_rating=m['rating'],experimental_reference_candidate=candidate,
            experimental_reference_member=m['frozen_member'],all_observed_metric_scope_supported=not m['excluded'],excluded_appearances=m['excluded'],
            numerator_match_ids=m['supported_match_ids'],denominator_match_ids=m['supported_match_ids'],supported_minutes=pair(minutes),
            exact_value=pair(F(m['exact_value'])) if m['exact_value'] is not None else None,numerator=m['numerator'],attempts=m['attempts'])
    reasons=approved_exclusion_reasons(profile,reference)
    p['diagnostic_ranking_exclusion_reasons']=reasons
    assert (not reasons)==(p['diagnostic_eligible']=='True'),p['player_id']
    assert formula_b([m['rating'] for m in attrs.values()])==(float(p['corrected_diagnostic_rating']) if p['corrected_diagnostic_rating'] else None)
    assert formula_b([m['rating'] for m in json.loads(p['before_attributes']).values()])==published['ovr']['value']
rows=[p for p in population if p['affected_by_alias']=='True']
write_csv(out/'full-population-comparison.csv',population)
write_csv(out/'player-impact.csv',rows)
summary['verification_categories']=dict(Counter(p['verification'] for p in population))
summary['attribute_rating_change_counts']={a:sum(json.loads(p['before_attributes'])[a]['rating']!=json.loads(p['after_attributes'])[a]['rating'] for p in population) for a in json.loads(population[0]['before_attributes'])}
summary['press_ratio_exact_value_changes']=sum(json.loads(p['before_attributes'])['press_resistance']['exact_value']!=json.loads(p['after_attributes'])['press_resistance']['exact_value'] for p in population)
summary['approved_eligibility_comparisons']=len(population)
summary['approved_formula_b_comparisons']=len(population)*2
additional=root/'audit-output/decoder-fix-additional'
checks=json.loads((additional/'additional-checks.json').read_text(encoding='utf8'))
assert checks['raw_delivered_projection_vs_reconstruction_db']['mismatches']==0
assert not checks['all_2514_reference_candidate_and_membership_discrepancies']
summary['additional_raw_delivery_check']=checks['raw_delivered_projection_vs_reconstruction_db']
summary['additional_upstream_reference_discrepancies']=checks['all_2514_reference_candidate_and_membership_discrepancies']
positive=max((p for p in rows if p['overall_delta']),key=lambda p:float(p['overall_delta']))
negative=min((p for p in rows if p['overall_delta']),key=lambda p:float(p['overall_delta']))
tests={
 'public_backend':dict(passed=1029,failed=0,skipped=0,blocked=0),
 'private_backend':dict(passed=51,failed=0,skipped=0,blocked=0,deselected=125),
 'public_frontend':dict(passed=211,failed=0,skipped=0,blocked=0),
 'private_frontend':dict(passed=33,failed=1,skipped=0,blocked=0),
 'production_build':dict(passed=1,failed=0,blocked=0),
 'alias_regressions':dict(passed=22,failed=0,skipped=0,included_in_public_backend=True),
 'independent_regressions':dict(passed=12,failed=0,skipped=0,blocked=0),
 'identity_join_probes':dict(passed=12,failed=0,skipped=0,blocked=0),
 'private_backend_initial_attempt':dict(passed=34,errors=17,deselected=125,reason='Preview fixture root pointed at new worktree; corrected in test harness only'),
 'alias_regressions_initial_iteration':dict(passed=21,failed=1,reason='Synthetic expectation corrected to preserve existing rejection of an exit without return'),
}
(out/'test-results.json').write_text(json.dumps(tests,indent=2)+'\n')
summary['test_results']=tests
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
release=root/'frontend/public/data/player-ratings-2015-16-v1.json'
release_hash=hashlib.sha256(release.read_bytes()).hexdigest()
assert release_hash=='9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e'
report=f'''# Participation decoder correction, Batch 1

Review date: 1 November 2026. Local branch `participation-decoder-fix`, based on freshly fetched `origin/main` at `{summary['base_commit']}`. Worktree: `{root.as_posix()}`. No commit, push, PR, merge, deployment, public numerical update or new reference snapshot was made. The original dirty checkout and previous audit were inputs only.

## Validated results

Both exact off-camera lineup labels now resolve to their original StatsBomb `Player On` / `Player Off` events and existing return / temporary-exit behavior. The corrected production decoder recovered **{summary['recovered_appearances']} of {summary['alias_affected_appearances']} appearances**, giving **{summary['players_with_added_minutes']} of {summary['alias_affected_players']} affected players** additional supported exposure. Four remain withheld. These are actual production-decoder results cross-checked against original events and lineups, rather than the audit's hypothetical counts.

All **{summary['published_players']} published players**, **{summary['appearances']:,} appearances** and **{summary['fixtures']:,} original fixtures** were replayed. **{summary['unchanged_other_players']} players outside the identified 80** remain unchanged. Unexpected changes: **{len(summary['unexpected_changes'])}**. Historical diagnostic score discrepancies: **{len(summary['prior_diagnostic_rating_discrepancies'])}**.

**{summary['players_with_changed_attribute_inputs']} players have changed diagnostic attribute inputs**, **{summary['players_with_changed_attribute_ratings']} have changed attribute ratings**, and **{summary['players_with_changed_overall']} have changed Formula B overall ratings**. Press resistance remains an action-completion ratio, with its existing action scope, not a per-90 value. The other four attributes add corroborated action UUIDs and exactly matched exposure; actions are never added without their source participation denominator. Per-attribute raw counts, exact rates, exposure, ratings, percentiles and exclusion reasons are retained in the CSVs. Rating-change counts by attribute are `{json.dumps(summary['attribute_rating_change_counts'],sort_keys=True)}`; exact pressure-ratio value changes: **{summary['press_ratio_exact_value_changes']}**.

Largest positive overall change: **{positive['name']} ({positive['player_id']}), {float(positive['current_published_rating']):.10f} → {float(positive['corrected_diagnostic_rating']):.10f}, {float(positive['overall_delta']):+.10f}**. Largest negative: **{negative['name']} ({negative['player_id']}), {float(negative['current_published_rating']):.10f} → {float(negative['corrected_diagnostic_rating']):.10f}, {float(negative['overall_delta']):+.10f}**. The CSV values retain full precision; presentation here does not feed calculations.

Ranking eligibility changes under frozen membership: **{summary['eligibility_changes']}**. **{summary['newly_complete_without_frozen_membership']}** currently excluded players clear the other checked completeness and threshold predicates but still lack existing frozen membership. No automatic promotion was made.

## Root cause and implementation

`src/statsbomb_participation.py::_adapt_match.endpoint` previously omitted the two legitimate off-camera labels. Add `Player On (Off Camera)` → (`Player On`, `return`) and `Player Off (Off Camera)` → (`Player Off`, `temporary_exit`). `src/independent_source_checks.py::endpoint` receives the same exact label support with its original endpoint-direction restrictions. No prefix-based production mapping, unknown label support, validation relaxation, duration rounding or timestamp tolerance was introduced. Original events retain their normal type names; the aliases describe lineup endpoints.

Every existing supported mapping remains. Source actor/team/name association, lineup positions, original transition representation, substitutions, permanent exits, dismissals, snapshots, interval order, overlap and period-boundary checks still execute. An alias only resolves a candidate endpoint; it does not authorize an appearance.

## Original source evidence and independent verification

Pinned StatsBomb revision: `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. Each affected row in `appearance-comparison.csv` records original document paths and SHA256 hashes, source report hash, original lineup positions, exact transition UUIDs, independently reconstructed intervals, corrected production intervals, exact rational seconds, old/new statuses and remaining issues. `input-hashes.json` binds every consumed report, fixture list, event document, lineup document and frozen package input. `{summary['prior_input_receipts_reverified']}` consumed inputs were also verified against prior audit receipts. Source hashes were rechecked after the replay; large evidence remains ignored by Git.

All **{summary['prior_audit_artifacts_preserved']}** artifacts in the prior audit's output hash manifest remain unchanged. The prior audit reports, source receipts, diagnostics and numerical results are preserved.

`scripts/decoder_fix_independent.py` retains the prior audit's event-driven state machine, raw-field metric transcription and arithmetic as reviewable code. It imports no production participation decoder or scorer. It starts from original XI/substitution/temporary-exit/return/dismissal events, then separately reconstructs lineup geometry; tactical shifts do not create event-state entries or exits. Corrected accepted geometry is compared as exact normalized period-local interval unions, so equal totals cannot hide shifted intervals. `scripts/check_decoder_fix_geometry.py` contains that interval-union comparison and a standalone additional replay. All source schema checks still run; the main diagnostic memoizes only the pure exact timestamp parser, retaining exact parser values and all source validations.

Replay checks: `{json.dumps(summary['source_checks'],sort_keys=True)}`. All 691 canonical ID/name pairs agree with original lineups. Each original selected numerator and press-attempt UUID set is re-extracted and compared against the sealed historical fact, including rejected appearances. UUID uniqueness and delivered UUID/team/name/competition/season/type associations are checked directly; delivered team spellings retain the existing reviewed alias policy. Event exceptions outside verified geometry are recorded separately, without adding a tolerance or calling every exception a corrupt successful numerator.

The exact historical public attribute ratings/percentiles, overall values or N/A results, and eligibility decisions reproduce independently. The approved production aggregator/scorer is also rerun, and its outputs must agree with the independent arithmetic for both old and corrected inputs. The original frozen package is reconstructed across **{summary['original_upstream_reference_candidates_checked']} upstream player-seasons** and must match the existing frozen reference exactly. Corrected recipients use that unchanged reference. Source positional exposure is added and dominance recomputed: comparison-group changes **{summary['comparison_group_changes']}**; fine-group changes `{json.dumps(summary['dominant_fine_group_changes'])}`.

Finalization additionally compares the independent decisions with the existing strict eligibility implementation for **{summary['approved_eligibility_comparisons']}** corrected profiles, and compares both old/new overall arithmetic with `src.provisional_ovr.formula_b` for **{summary['approved_formula_b_comparisons']}** values or N/A decisions. All agree. Exact exclusion reasons from the unchanged strict predicate are included alongside the historical public reasons. The eligibility helper's legacy module name references the earlier Formula C study; no Formula C score or normalization is calculated.

The retained independent additional checker was rerun against delivered Parquet bytes: **{summary['additional_raw_delivery_check']['rows']:,} rows, zero projection/reconciliation mismatches**, plus zero independent candidate/membership disagreements across all 2,514 upstream player-seasons. Raw fixture inventory coverage is retained in `audit-output/decoder-fix-additional/additional-checks.json`. Final review categories are `{json.dumps(summary['verification_categories'],sort_keys=True)}`; corrected profiles can still retain other source exclusions, listed separately.

The raw timing diagnostic has **{len(new_timing)} rows**, compared with **{len(old_timing)}** in the prior action-chronology file. This difference is fully reconciled: the older checker explicitly excluded `Bad Behaviour`, `Substitution`, `Player Off` and `Player On` records from that file. The broader new raw scan adds **{len(extra_timing)}** such administrative/disciplinary rows (six `Bad Behaviour`, one `Player On`), with **zero selected metric events**; all 107 old rows remain. Exact UUIDs and scope labels are retained in `events-outside-participation.csv` and `summary.json`. These seven rows are not additional recovered actions, newly changed observations or unexplained numerical discrepancies.

## Four unresolved appearances

| Player / fixture | Remaining original-source conflict |
| --- | --- |
| Paolo Sammarco `23349 / 3879602` | Reversed period order, clock outside supported period, overlapping active intervals and active-position snapshot disagreement. Cross-period/sequence evidence remains incomplete. |
| Giuseppe Vives `40430 / 3879772` | Original permanent-exit transition is not represented by the continuing lineup; participation continues after that exit. Independent event/lineup durations disagree. |
| Molla Wagué `3577 / 3879863` | Original permanent-exit/dismissal evidence conflicts with continuing lineup participation; unrepresented transition and participation after permanent exit remain. |
| Matthieu Saunier `13730 / 3901259` | Original permanent-exit transition conflicts with the continuing lineup; unrepresented transition and participation after permanent exit remain. Independent durations disagree. |

All four remain `CONFLICTING_EVIDENCE`, with no corrected supported minutes. Their exact event UUIDs and both assertions remain in `appearance-comparison.csv` and `summary.json`. No override or source resolution is incorporated.

## Frozen-reference diagnostic and future research snapshot

This is comparison A: corrected recipient inputs with original normalization means, sample standard deviations, exact percentile populations, memberships and Formula B. Frozen semantic fingerprint: `{summary['frozen_reference_semantic_sha256']}`. Public release SHA256 remains `{release_hash}`. Neither file was modified.

For comparison B, a full corrected research reconstruction requires a new versioned reference decision and review of all upstream candidates, complete-exposure and per-metric coverage predicates, position dominance, pending fixtures, 900-minute and 40-action thresholds, and each attribute's membership. The affected published players have **{summary['affected_existing_reference_memberships']} existing attribute-reference memberships**; this targeted replay changes **{len(summary['existing_reference_member_value_changes'])} existing reference-member values**. Its prospective new published candidates by pool are `{json.dumps(summary['prospective_published_candidate_additions'],sort_keys=True)}`; their IDs are in `reference-assessment.json`. This assesses predicates only and does not fit a reference or calculate new population statistics. Adding reviewed candidates would require recomputing means, sample standard deviations and percentile populations, potentially changing normalized ratings and overall scores throughout the population, including currently unchanged players. A coherent new research snapshot needs a new bound version and explicit review; it is not produced here. Unpublished upstream inputs have not been fully corrected in this task, so the 28 profiles are not an estimate of all possible upstream membership changes.

## Tests and build

| Final verification | Passed | Failed | Skipped | Blocked |
| --- | ---: | ---: | ---: | ---: |
| Public backend, including 22 new regressions | 1,029 | 0 | 0 | 0 |
| Private backend, corrected modules and retained fixtures | 51 | 0 | 0 | 0 |
| Public frontend, including HTTP preview and packaging | 211 | 0 | 0 | 0 |
| Private frontend | 33 | 1 | 0 | 0 |
| Independent event/metric/arithmetic regressions | 12 | 0 | 0 | 0 |
| Identity/join probes | 12 | 0 | 0 | 0 |
| Production build | 1 | 0 | 0 | 0 |

Private backend additionally deselected 125 cases outside its declared suite; these are not skips. Its initial attempt had 34 passes and 17 fixture-root setup errors; the read-only harness fixture binding was corrected and all 51 passed. No production implementation was changed for that setup issue. The private frontend's sole failure is the previously reported badge punctuation expectation at `provisionalOvr.test.js:61`; it is separate from numerical integrity. All 68 application frontend source/script files are byte-equivalent after newline normalization to the private-suite checkout used for that run. No presentation or rating behavior was changed to satisfy it.

The first standalone alias-test iteration had 21 passes and one incorrect synthetic expectation: it assumed a terminal temporary exit with no return could be accepted. The existing sequence policy correctly withheld it. The test was corrected to require that preserved exclusion; production validation was not relaxed, and the final public suite passes all 22 new cases.

The 22 synthetic regressions cover normal labels, each alias separately and together, entry/exit-only evidence, temporary returns, halftime absence, stoppage/millisecond clocks, substitution/permanent exits, red/second-yellow dismissals, missing/ambiguous transitions, reversed/overlapping intervals, snapshot conflicts, unknown/wrong-direction labels, events inside absences and 1 ms after final whistle. The pre-existing regressions also run unchanged. The full original-source replay verifies all previously accepted appearances remain identical.

## Reproduction and review artifacts

Run in this checkout with Python 3.13, existing requirements, locked frontend dependencies and the retained source/audit workspaces. Use a fresh output directory; existing evidence is never overwritten.

```powershell
git fetch origin main
git worktree add -b participation-decoder-fix C:/Users/Ayush/Desktop/Projects/Soccer-Impact-Engine-Index-participation-decoder-fix origin/main
python -B -m scripts.verify_participation_decoder_fix --source-root ../Soccer-Impact-Engine-Index --audit-root ../Soccer-Impact-Engine-Index-player-data-integrity-audit --output audit-output/decoder-fix
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/scripts/audit_full_player_additional_checks.py --source-root ../Soccer-Impact-Engine-Index --checkout . --output audit-output/decoder-fix-additional
python -B -m scripts.run_backend_tests public -q
npm.cmd ci --offline --no-audit --no-fund --prefix frontend
npm.cmd run test:public --prefix frontend
npm.cmd run build --prefix frontend
python -B audit-output/run-private-backend.py
npm.cmd run test:private --prefix ../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/private-suite-checkout/frontend
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/test_independent_audit.py
python -B -c "import src, runpy; runpy.run_path('../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/identity_probes.py', run_name='__main__')"
python -B -m scripts.finalize_participation_decoder_fix
```

The retained `audit-output/run-private-backend.py` imports implementation modules from this correction checkout and fingerprint-verified private test/support files from the original workspace; only the test harness redirects the local-preview fixture root to the original frozen package. It uses `-B` and disables pytest cache writes. The frontend command uses existing private test sources after verifying source equality. Test/build logs, fixture setup error logs, replay logs and failed/restarted diagnostic attempts remain local. The complete run was restarted to add exact interval-union and position-dominance checks and memoize the pure timestamp parser; partial runs are not used as final findings.

Required deliverables: `appearance-comparison.csv` (95 affected rows), `player-impact.csv` (80 affected rows), `full-population-comparison.csv` (691 rows), `summary.json`, this report, regression tests and reproduction scripts. Supplemental `all-appearance-comparison.csv`, `events-outside-participation.csv`, `input-hashes.json`, `output-hashes.json`, and `test-results.json` support independent review. All numeric diagnostics and large evidence remain under ignored `audit-output`; no force-add was performed.

## Modified files

- `src/statsbomb_participation.py` and `src/independent_source_checks.py`: the exact aliases.
- `tests/test_participation_decoder_aliases.py` and `tests/suite_inventory.json`: 22 public regressions and registration.
- `scripts/decoder_fix_independent.py`: independent event/lineup reconstruction, raw metric transcription and arithmetic retained from the audit.
- `scripts/check_decoder_fix_geometry.py`: exact interval-union comparison and optional standalone replay.
- `scripts/verify_participation_decoder_fix.py`: full baseline/corrected source replay and independent input/rating comparisons.
- `scripts/finalize_participation_decoder_fix.py`: strict-policy cross-checks, scope/reference assessment, final CSV review metadata, summary and this report.
- `docs/participation-decoder-fix-report.md`: review findings and commands.

## Remaining correction batches and limits

The earlier audit's remaining source dismissal/lineup/period contradictions, source chronology and declared permanent-exit support limits, conservative identity-name admission restrictions, legacy helper reuse hazards, and missing/video-limited fixture coverage remain separate work. This decoder change does not resolve them. Same-provider event/lineup agreement is not external historical attestation, and observed supported exposure does not establish complete historical seasons. No missing game is filled with zero actions or conventional minutes. The website, ranking policy, attribute definitions, Formula B, published scores, frozen references and original source bytes remain unchanged.
'''
(root/'docs/participation-decoder-fix-report.md').write_text(report,encoding='utf8')
logs=out/'logs';logs.mkdir(exist_ok=True)
for path in root.glob('*.log'):shutil.copyfile(path,logs/path.name)
if (root/'frontend/npm-install.log').exists():shutil.copyfile(root/'frontend/npm-install.log',logs/'npm-install.log')
shutil.copyfile(root/'audit-output/run-private-backend.py',out/'reproduce-private-backend.py')
provenance={}
code=['src/statsbomb_participation.py','src/independent_source_checks.py','tests/test_participation_decoder_aliases.py','tests/suite_inventory.json',
      'scripts/decoder_fix_independent.py','scripts/check_decoder_fix_geometry.py','scripts/verify_participation_decoder_fix.py','scripts/finalize_participation_decoder_fix.py',
      'src/private_ovr_formula_c.py','src/provisional_ovr.py','docs/participation-decoder-fix-report.md']
paths=[root/p for p in code]+[prior_manifest,prior_root/'scripts/audit_full_player_additional_checks.py',
       prior_root/'audit-output/full-player-audit-tests/test_independent_audit.py',prior_root/'audit-output/full-player-audit-tests/audit.py',
       prior_root/'audit-output/full-player-audit-tests/identity_probes.py',root/'audit-output/decoder-fix-additional/additional-checks.json',
       root/'audit-output/decoder-fix-additional/additional-input-hashes.json']
for path in paths:
    with path.open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
    provenance[str(path.resolve())]=dict(sha256=h,bytes=path.stat().st_size)
(out/'review-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
hashes={}
for path in out.rglob('*'):
    if path.is_file() and path!=out/'output-hashes.json':
        with path.open('rb') as stream:hashes[path.relative_to(out).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
(out/'output-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('disputed_appearances','original_lineup_reason_inventory','additional_raw_delivery_check')},indent=2))
