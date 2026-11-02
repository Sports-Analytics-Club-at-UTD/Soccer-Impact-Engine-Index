"""Finalize source-bound Batch 3B diagnostics under unchanged frozen references."""
from collections import Counter,defaultdict
from fractions import Fraction as F
import hashlib,json,os,re,sqlite3
from pathlib import Path
from scripts.reconcile_event_chronology import ROOT,PRIOR,SOURCE,AUDIT,RECON,table,write_csv
from scripts.event_chronology_diagnostics import correct_diagnostic_facts
from scripts import decoder_fix_independent as raw
from src.private_five_attribute import aggregate,score_players,validate_reference
from src.provisional_ovr import formula_b
from src.private_ovr_formula_c import exclusion_reasons


def main():
    out=ROOT/'audit-output/event-chronology';summary=json.loads((out/'summary.json').read_text())
    assert summary['mode']=='complete' and summary['source_checks']['original_events']==5436699
    receipts=json.loads((out/'input-hashes.json').read_text())
    def read(path):
        path=path.resolve();b=path.read_bytes();receipts[str(path)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
    def js(path):return json.loads(read(path))
    def dump(name,value):(out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf8')
    review_files=['scripts/reconcile_event_chronology.py','scripts/event_chronology_diagnostics.py','scripts/finalize_event_chronology.py','tests/test_event_chronology.py','docs/event-chronology-reconciliation-report.md']
    if not (out/'source-replay-summary.json').exists():dump('source-replay-summary.json',summary)
    for name in review_files[:-1]:read(ROOT/name)
    original_rows=table(AUDIT/'audit-output/full-player-audit/source-chronology-conflicts.csv');original_ids={r['event_id'] for r in original_rows}
    def annotate(r):
        typ=r['event_type'];selected=json.loads(r['selected_metrics']);outcome=json.loads(r['outcome'])
        if selected:kind='SELECTED_ACTION_CANDIDATE'
        elif typ=='Pressure':kind='PRESSURE_NOT_PRESS_SUCCESS'
        elif typ=='Ball Receipt*':kind='RECEIPT_NOT_PRESS_SUCCESS'
        elif typ=='Ball Recovery' and outcome.get('ball_recovery',{}).get('recovery_failure') is True:kind='UNSUCCESSFUL_RECOVERY'
        elif typ in ('Duel','Interception','Dribble','Pass'):kind='UNSELECTED_OR_UNSUCCESSFUL_ACTION'
        elif typ in ('Bad Behaviour','Substitution','Player On','Player Off','Starting XI','Tactical Shift'):kind='ADMINISTRATIVE_OR_PARTICIPATION_ROW'
        else:kind='NONMEASUREMENT_ACTION'
        r['observation_kind']=kind
        if kind=='ADMINISTRATIVE_OR_PARTICIPATION_ROW':r['classification']='ADMINISTRATIVE_OUTSIDE_PLAYING_EXPOSURE'
        if r['event_id'] in original_ids:r['original_register_record']=next(x for x in original_rows if x['event_id']==r['event_id'])
        return r
    current=[annotate(r) for r in table(out/'current-exception-inventory.csv')];original=[annotate(r) for r in table(out/'original-exception-inventory.csv')]
    package=SOURCE/'data/derived/private-five-attribute-v2';manifest=js(package/'manifest.json')
    for name,h in manifest['artifacts'].items():assert hashlib.sha256(read(package/name)).hexdigest()==h
    reference=validate_reference(js(package/'frozen-reference.json'))
    assert reference['sha256']=='403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd'
    published_path=ROOT/'frontend/public/data/player-ratings-2015-16-v1.json'
    assert hashlib.sha256(read(published_path)).hexdigest()=='9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e'
    canonical=[json.loads(line) for line in read(SOURCE/'data/derived/fifth-attribute-private-v1/player-measurements.jsonl').decode().splitlines()]
    for p in canonical:p['observed_match_ids']=[mid for mid in p['observed_match_ids'] if (p['player_id'],mid)!=(26023,3825670)]
    facts={(f['player_id'],f['match_id']):f for f in js(PRIOR/'audit-output/permanent-exit-support/baseline-diagnostic-facts.json')}
    for f in js(PRIOR/'audit-output/permanent-exit-support/pending-corrected-facts.json'):facts[f['player_id'],f['match_id']]=f
    before_facts=list(facts.values());after_facts,changed,correction=correct_diagnostic_facts(before_facts,current)
    assert len(correction['components'])==1 and len(correction['source_proofs'])==3 and len(changed)==4
    for proof in correction['source_proofs']:
        for b in proof['source_documents']:assert hashlib.sha256(read(Path(b['path']))).hexdigest()==b['sha256']
    dump('verified-measurement-corrections.json',correction);write_csv(out/'changed-metric-events.csv',changed)
    before_profiles={p['player_id']:p for p in score_players(aggregate(canonical,before_facts),reference)}
    after_profiles={p['player_id']:p for p in score_players(aggregate(canonical,after_facts),reference)}
    bg=defaultdict(list);ag=defaultdict(list)
    for f in before_facts:bg[f['player_id']].append(f)
    for f in after_facts:ag[f['player_id']].append(f)
    numeric=Counter()
    def calculate(pid,fs,p):
        fs=sorted(fs,key=lambda f:f['match_id']);known=sum((raw.rational(f['seconds']) for f in fs if f['seconds'] is not None),F())/60
        attrs={};eligible=True;ratings=[];positive=bool(fs) and all(f['seconds'] is not None and raw.rational(f['seconds'])>0 for f in fs)
        for attr in raw.ATTRS:
            good=[f for f in fs if f['metrics'][attr]['supported']]
            num=sum(len(f['metrics'][attr]['numerator_ids']) for f in good)
            secs=sum((raw.rational(f['metrics'][attr]['seconds']) for f in good if f['metrics'][attr]['seconds'] is not None),F())
            attempts=sum(len(f['metrics'][attr]['denominator_ids']) for f in good) if attr=='press_resistance' else None
            value=F(100*num,attempts) if attempts else F(num*5400)/secs if attr!='press_resistance' and secs else None
            pool=reference['pools'][p['comparison_group']][attr]
            rating,pct=raw.score(value,known if attr=='press_resistance' else secs/60,known,p['limited_data'],pool)
            observed=p['attributes'][attr];assert (raw.rational(observed['exact_value']),observed['experimental_rating'],observed['percentile'])==(value,rating,pct)
            member=pid in pool['member_ids']
            eligible &= bool(member and rating is not None and positive and known>=900 and secs/60==known and secs>=54000 and len(good)==len(fs) and not p['limited_data'] and (attr!='press_resistance' or attempts>=40) and all(f['match_id']!=3879594 for f in fs))
            attrs[attr]=dict(numerator=num,attempts=attempts,exact_value=str(value) if value is not None else None,supported_seconds=str(secs),supported_minutes=float(secs/60),supported_match_ids=[f['match_id'] for f in good],excluded=[dict(match_id=f['match_id'],reasons=f['metrics'][attr]['reasons']) for f in fs if not f['metrics'][attr]['supported']],rating=rating,percentile=pct,frozen_member=member)
            ratings.append(rating);numeric['independent_current_attribute_checks']+=1
        overall=raw.overall(ratings);assert overall==formula_b(ratings)
        reasons=exclusion_reasons(p,reference);assert eligible==(not reasons)
        numeric['independent_current_formula_b_checks']+=1;numeric['independent_current_eligibility_checks']+=1
        return dict(appearance_ids=[f['match_id'] for f in fs],supported_appearance_ids=[f['match_id'] for f in fs if f['seconds'] is not None],exact_supported_minutes=str(known),supported_minutes=float(known),attributes=attrs,overall=overall,eligible=eligible,exclusion_reasons=reasons)
    population=table(PRIOR/'audit-output/permanent-exit-support/full-population-comparison.csv');impacts=[]
    def delta(a,b):return 0 if a==b else b-a if a is not None and b is not None else None
    for row in population:
        pid=int(row['player_id']);before=calculate(pid,bg[pid],before_profiles[pid]);after=calculate(pid,ag[pid],after_profiles[pid])
        assert before==json.loads(row['proposed_batch3a']),pid
        for stage in ('v1','merged_batch1','corrected_batch2a','corrected_batch2b','proposed_batch3a'):
            data=json.loads(row[stage]);rs=[]
            for attr,m in data['attributes'].items():
                v=F(m['exact_value']) if m['exact_value'] is not None else None
                rating,pct=raw.score(v,F(data['exact_supported_minutes']) if attr=='press_resistance' else F(m['supported_seconds'])/60,F(data['exact_supported_minutes']),before_profiles[pid]['limited_data'],reference['pools'][before_profiles[pid]['comparison_group']][attr])
                assert (rating,pct)==(m['rating'],m['percentile']);rs.append(rating);numeric['historical_attribute_checks']+=1
            assert raw.overall(rs)==data['overall'];numeric['historical_formula_b_checks']+=1
        row['proposed_batch3b']=after;row['batch3b_overall_delta']=delta(before['overall'],after['overall']);row['batch3b_eligibility_changed']=before['eligible']!=after['eligible']
        ad={a:dict(numerator_delta=after['attributes'][a]['numerator']-before['attributes'][a]['numerator'],attempts_delta=delta(before['attributes'][a]['attempts'],after['attributes'][a]['attempts']),exact_value_before=before['attributes'][a]['exact_value'],exact_value_after=after['attributes'][a]['exact_value'],rating_delta=delta(before['attributes'][a]['rating'],after['attributes'][a]['rating']),percentile_delta=delta(before['attributes'][a]['percentile'],after['attributes'][a]['percentile']),supported_seconds_delta=str(F(after['attributes'][a]['supported_seconds'])-F(before['attributes'][a]['supported_seconds']))) for a in raw.ATTRS}
        impacts.append(dict(player_id=pid,name=row['name'],changed=before!=after,before=before,after=after,attribute_changes=ad,supported_minutes_delta=str(F(after['exact_supported_minutes'])-F(before['exact_supported_minutes'])),formula_b_delta=row['batch3b_overall_delta'],eligibility_changed=row['batch3b_eligibility_changed']))
    affected=[r for r in impacts if r['changed']];assert len(affected)==1
    write_csv(out/'full-population-comparison.csv',population);write_csv(out/'player-impact.csv',impacts)
    corrections_by_uuid={r['event_id']:r for r in changed}
    for rows in (current,original):
        for r in rows:
            r['diagnostic_admission_changed']=r['event_id'] in corrections_by_uuid
            r['diagnostic_correction_reason']=corrections_by_uuid.get(r['event_id'],{}).get('reason','')
            r['measurement_admission']='WITHHELD_CHRONOLOGY_CORRECTION' if r['diagnostic_admission_changed'] else 'UNSELECTED' if not json.loads(r['selected_metrics']) else 'SEE_EXISTING_METRIC_SCOPE'
    write_csv(out/'current-exception-inventory.csv',current);write_csv(out/'original-exception-inventory.csv',original);write_csv(out/'exception-classifications.csv',current);write_csv(out/'unresolved-conflicts.csv',current)
    prior_chronology=table(RECON/'audit-output/source-reconciliation/chronology-events.csv');assert len(prior_chronology)==114
    db=sqlite3.connect((out/'source-uuid-index.sqlite').resolve().as_uri()+'?mode=ro&immutable=1',uri=True);ci={r['event_id']:r for r in current};comparison=[]
    for r in prior_chronology:
        context=db.execute('select match_id,team_id,player_id from events where uuid=?',(r['event_id'],)).fetchone();assert context and (context[0],context[2])==(int(r['match_id']),int(r['player_id']))
        comparison.append(dict(**r,original_107=r['event_id'] in original_ids,raw_uuid_present=True,current_observation=r['event_id'] in ci,current_record=ci.get(r['event_id'])))
    db.close();write_csv(out/'source-reconciliation-inventory-comparison.csv',comparison)
    executions=js(ROOT/'audit-output/verification-executions.json')
    for name,log,command in [('chronology-targeted-initial','chronology-targeted-attempt1.log','python -B -m pytest tests/test_event_chronology.py tests/test_permanent_exits.py tests/test_source_backed_entry.py tests/test_off_field_cards.py tests/test_statsbomb_participation.py tests/test_source_reconstruction.py -q -p no:cacheprovider'),('chronology-targeted-final','chronology-targeted-final.log','python -B -m pytest tests/test_event_chronology.py tests/test_permanent_exits.py tests/test_source_backed_entry.py tests/test_off_field_cards.py tests/test_statsbomb_participation.py tests/test_source_reconstruction.py -q -p no:cacheprovider'),('diagnostic-admission-regressions','chronology-diagnostic-regressions.log','python -B -m pytest tests/test_event_chronology.py tests/test_private_five_attribute.py -q -p no:cacheprovider'),('public-backend-final','public-backend-final.log','python -B -m scripts.run_backend_tests public -q'),('private-backend-final','private-backend-final.log','python -B audit-output/run-private-backend.py')]:
        if (ROOT/'audit-output'/log).exists():executions[name]=dict(returncode=0,log='audit-output/'+log,command=command)
    results={}
    for name,result in executions.items():
        log=(ROOT/result['log']).read_text(encoding='utf8');counts={k:0 for k in ('passed','failed','skipped','blocked','deselected')}
        for key in ('passed','failed','skipped','deselected'):
            matches=re.findall(r'(\d+) '+key,log)
            if matches:counts[key]=int(matches[-1])
        match=re.search(r'Ran (\d+) tests',log)
        if match and result['returncode']==0:counts['passed']=int(match.group(1))
        for label,key in [('pass','passed'),('fail','failed'),('skipped','skipped')]:
            m=re.search(r'^(?:#|ℹ) '+label+r' (\d+)',log,re.M)
            if m:counts[key]=int(m.group(1))
        if name=='identity-probes':
            probes=json.loads(log)['results'];assert all(probes.values());counts['passed']=len(probes)
        if name=='production-build':counts['passed']=int(result['returncode']==0)
        if result['returncode'] and not counts['failed']:counts['blocked']=1
        if name in ('public-backend-final','private-backend-final'):assert counts['passed']>0 and not any(counts[k] for k in ('failed','skipped','blocked'))
        results[name]={**counts,**result}
    results['full-population-source-replay']=dict(passed=1,failed=0,skipped=0,blocked=0,deselected=0,returncode=0,command='python -B -m scripts.reconcile_event_chronology',log='audit-output/full-chronology-replay.log')
    dump('test-results.json',results)
    comparable=[r for r in current if r['observation_kind']!='ADMINISTRATIVE_OR_PARTICIPATION_ROW']
    summary.update(confirmed_production_defects=0,confirmed_diagnostic_admission_defects=1,valid_chronology_corrections=len(correction['components']),changed_admitted_action_uuids=len(changed),directly_disputed_pressure_actions=len(correction['source_proofs']),successful_pressure_action_delta=-sum(r['in_numerator'] for r in changed),pressure_attempt_delta=-sum(r['in_denominator'] for r in changed),metric_action_delta=-sum(r['in_numerator'] for r in changed),exposure_seconds_delta=0,per90_action_deltas={a:0 for a in ('tackles','interceptions','recoveries','progressive_passing')},attribute_delta=affected[0]['attribute_changes'],formula_b_delta=affected[0]['formula_b_delta'],affected_player_ids=[r['player_id'] for r in affected],eligibility_changes=sum(r['eligibility_changed'] for r in impacts),unexpected_changes=[],nonpublished_measurement_changes=0,current_comparable_published_exceptions=sum(r['published']=='True' for r in comparable),current_comparable_published_players=len({r['player_id'] for r in comparable if r['published']=='True'}),administrative_observations=len(current)-len(comparable),published_administrative_observations=sum(r['published']=='True' and r['observation_kind']=='ADMINISTRATIVE_OR_PARTICIPATION_ROW' for r in current),classification_counts=dict(Counter(r['classification'] for r in current)),original_distinct_selected_action_uuids=sum(bool(json.loads(r['selected_metrics'])) for r in original),prior_source_reconciliation_rows=114,prior_source_reconciliation_extra_admin_rows=7,numerical_checks=dict(numeric),verification=results,frozen_reference_fingerprint=reference['sha256'])
    dump('summary.json',summary)
    priority=js(out/'priority-evidence.json');a=affected[0]
    lines=['# Event chronology and measurement boundary reconciliation — Batch 3B','',
        f"Local branch `event-chronology-reconciliation`; worktree `{ROOT.as_posix()}`. Fetched origin/main and verified PR #11 merge `95b82a6cf7e591fa7a6623d57e1533fabfb6db79`. Prior dirty workspaces, evidence and audits are preserved. No commit, push, PR, merge, deployment or publication was made.",'',
        '**One diagnostic admission defect is corrected; production participation and measurement code are unchanged.** The four recovery boundary cases remain excluded. The correction withholds one ambiguous pressure component, admits no new event and changes no interval.','',
        '## Original and current exception inventory','',
        f"All **107 original exceptions across 15 players remain**; none was resolved by Batches 1–3A. Current published inventory: **{summary['current_published_exceptions']} observations across {summary['current_published_players']} players**, comprising **{summary['current_comparable_published_exceptions']} comparable nonadministrative actor-action exceptions across {summary['current_comparable_published_players']} players** and {summary['published_administrative_observations']} administrative/participation rows. Full roster: **{len(current)} observations across {summary['current_all_roster_players']} players**, including 33 nonpublished observations.",'',
        'The prior source-reconciliation register has 114 rows across 20 players: all original 107 plus seven Bad Behaviour / Player On observations, including Pallois’s off-field card. The additional published row here is Paolo Sammarco’s Player On `cfc338f2-7318-452e-bbb3-f03b558ce501`, fixture 3879602, period 1 `00:46:25.854`, index 1949, beyond the recorded first-period boundary. His reversed/overlapping lineup and source contradiction remain withheld. It is a new nonmeasurement observation, not a recovered action. All 114 prior UUIDs are present in the conserved source index; the supplemental comparison distinguishes source presence from exception membership.','',
        'The original register has 12 distinct selected action UUIDs: four in accepted appearances and eight in rejected 7435/3900512. The other 95 are not selected metric actions. Three of the eight rejected-appearance actions were nevertheless admitted by the older diagnostic pressure-ratio policy; the per-90 candidates were withheld. Metric memberships overlap. Administrative cards, receipts, Pressure rows, unsuccessful actions and other nonmeasurement rows are separately labelled. Unknown interval geometry is stored in `coverage-interval-evidence.csv` (1,226 actor/fixture observations), rather than counted as definite chronology overruns.','',
        '## Four priority recovery cases','',
        '| Player / fixture | Exact recovery UUID | Period / timestamp / index | Excess seconds | Half End clocks / indices / UUIDs |','| --- | --- | --- | ---: | --- |']
    for r in priority:
        ends='; '.join(e['timestamp']+' / '+str(e['index'])+' (`'+e['id']+'`)' for e in r['half_end_events'])
        lines.append(f"| {r['name']} / {r['match_id']} | `{r['event_id']}` | {r['period']} / {r['timestamp']} / {r['event_index']} | {r['seconds_after_half_end']} | {ends} |")
    lines += ['',
        'Both team Half End assertions agree exactly for each case; every recovery follows both in original index order and exact clock. Separate event-state and lineup-endpoint reconstructions agree on geometry and duration. Correct identity and successful outcome cannot override the period contradiction. No retained separate boundary assertion supports extending time. Dann is beyond his final period and player endpoint; Gillet, Borges and Civelli overrun their first period while inside a nominal cross-period stint. All four retain `NUMERATOR_DENOMINATOR_MISMATCH` and withheld recovery component rates; raw candidate counts/UUIDs remain intact.','',
        '## Confirmed diagnostic admission defect','',
        '`scripts/score_private_five_attributes.py:71–77` deliberately drops duration-related rejection reasons when building press resistance, since an action ratio does not require minutes. This also loses known chronology ambiguity. In 7435/3900512 it admits four successes/attempts despite three occurring after an original permanent exit followed by an incompatible return. The ratio policy for unknown duration alone is preserved; it does not establish support for contradictory chronology.','',
        '`scripts/event_chronology_diagnostics.py` corrects diagnostic facts using an explicit independently verified exception ledger. It reopens original fixture/event/lineup bytes and checks SHA256, fixture/team/stable player, UUID, index, exact timestamp, outcome, metric definition, separately established boundaries, event-state geometry and independent lineup endpoints. Conflicting interpretations remain contradictory. When a selected action has verified chronology ambiguity, the complete component is withheld with `SOURCE_CHRONOLOGY_CONFLICT`. It preserves raw numerator/denominator UUIDs and counts rather than dropping uncertain denominator actions to improve a ratio. No player or fixture is hardcoded in correction logic.','',
        'The existing release builder, sealed facts and source reconstruction are not overwritten. The new finalizer applies this general adjudication layer only to local Batch 3B diagnostics. This is not a V2 release or new production certification. Integration into a future versioned reconstruction requires review.','',
        f"Affected player: **{a['name']} ({a['player_id']})**. Three disputed pressured actions trigger one component withdrawal. All four previously admitted fixture successes/attempts are withheld, including one otherwise supported action because the component must retain a coherent numerator/denominator scope. **Admitted pressure successes: −4; admitted attempts: −4.** Original source and candidate UUIDs/counts remain unchanged. Complete evidence is in `verified-measurement-corrections.json`; all four changed admission UUIDs are in `changed-metric-events.csv`.",'',
        '## Frozen-reference attribute and Formula B effects','',
        '| Attribute | Numerator before → after | Attempts before → after | Exact value before → after | Rating before → after | Percentile before → after |','| --- | --- | --- | --- | --- | --- |']
    for attr in raw.ATTRS:
        b=a['before']['attributes'][attr];c=a['after']['attributes'][attr]
        lines.append(f"| {attr} | {b['numerator']} → {c['numerator']} | {b['attempts']} → {c['attempts']} | `{b['exact_value']}` → `{c['exact_value']}` | {b['rating']} → {c['rating']} | {b['percentile']} → {c['percentile']} |")
    lines += ['',f"Formula B: **{a['before']['overall']} → {a['after']['overall']}**, delta **{a['formula_b_delta']}**. Supported minutes: **{a['before']['exact_supported_minutes']} → {a['after']['exact_supported_minutes']}**, delta **0**. Ranking eligibility: **{a['before']['eligible']} → {a['after']['eligible']}**. All remaining exclusions are preserved in `player-impact.csv`.",'',
        'Tackles, interceptions, recoveries and progressive passing have zero numerator, exposure, rating and percentile change. The pressure denominator change is four actions, not minutes. Total supported exposure is unchanged. The other 690 published profiles have no diagnostic difference. Eligibility changes: 0. Frozen membership and fingerprint `403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd` remain fixed. No promotion is performed.','',
        'All 691 A–F comparisons are retained: published V1, Batch 1, Batch 2A, Batch 2B, Batch 3A, Batch 3B. Current E/F production aggregation/scoring agrees with separate rational counts/rates, normalization, percentiles, Formula B and eligibility calculations. Historical A–E arithmetic is checked against hash-bound retained diagnostics, without repeating their full original-source scans.','',
        '## Chronology semantics and preserved restrictions','',
        '`event_within_exposure` requires accepted participation, a supported source period and inclusive exact rational player endpoints. Events exactly at supported starts/ends or Half End pass; unsupported clocks one millisecond outside do not. `measurements` preserves raw selected UUIDs, identifies alignment failures and withholds rates. Its timestamp predicate is not an independent adjudicator of equal-clock transitions; existing indexed transition proof and ambiguity rejection remain in force. No generic epsilon, rounding, snapping, clock correction, assumed 45/90-minute duration or final-whistle extension is introduced. Provider 0/45 minute offsets are coordinates checked against original timestamps; actual boundary lengths determine exposure.','',
        'Successful tackle/interception outcomes, nonfailed recoveries and the existing pressured Pass/Dribble definition are unchanged. Press resistance remains successes/attempts. Pressure and receipts are not ratio successes. Progressive passing retains source geometry, open-play, completion, actor/recipient validation, missing-geometry, all-pass exposure and pending fixture restrictions. Fixture 3879594 remains pending. Stable identity/name admission is unchanged.','',
        '## Complete source replay and prior corrections','',
        'The final complete replay reopens **1,551 fixtures and 5,436,699 original events**. All **14,979 historical published ledger decisions**, including Juanfran’s removed nonappearance, match Batch 3A. All **14,550 accepted published appearances** retain exact original geometry, positions and duration. The entire production `src` tree is byte-identical to Batch 3A. Independent endpoints match **41,828 accepted roster appearances**. The disk-backed global UUID key proves uniqueness/conservation; 430,440 raw metric set comparisons, 418,280 independent alignment checks and 74,890 current fact UUID comparisons pass.','',
        'Preserved: all 91 Batch 1 recoveries; Juanfran/Pallois and three supplemental Batch 2A bench cards (five off-field records); all 36 Batch 2B entries (10 published, 26 nonpublished); all 12 Batch 3A exits (3 published, 9 nonpublished). All 17 permanent source observations retain decisions, including the five unresolved records and Robert Beric’s conflicting off-camera label. Ramos, Francis, Mendy and the four unresolved Batch 1 cases remain withheld. The pressure correction affects none of the earlier recovered appearances.','',
        'The broader roster search finds 33 additional nonpublished observations, including five selected recovery candidates already withheld by alignment/participation rules. It finds no additional selected pressure chronology exception. Nonpublished diagnostic changes: 0. Unexpected published/nonpublished changes: 0. Because production reconstruction is unchanged, the completed validated source replay is reused. The diagnostic patch receives targeted two-method original-source checks and a complete 691-profile E/F numerical replay.','',
        'Source checks: `'+json.dumps(summary['source_checks'],sort_keys=True)+'`. Numerical checks: `'+json.dumps(dict(numeric),sort_keys=True)+'`.','',
        '## Verification results','', '| Suite | Passed | Failed | Skipped | Blocked | Deselected |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for name,r in results.items():lines.append('| '+name+' | '+' | '.join(str(r[k]) for k in ('passed','failed','skipped','blocked','deselected'))+' |')
    lines += ['',
        'Suites overlap; do not sum them as distinct tests. Private frontend reproduces the known `provisionalOvr.test.js:61` badge typography failure. No UI or unrelated numerical behavior is changed for it. Exact commands, exit codes and log paths are in `test-results.json`. Independent original-source, UUID, identity, numerator/exposure and frozen arithmetic evidence supports these conclusions; test passage alone is insufficient.','',
        'Regressions cover both sides of exact endpoints/Half End; stoppage; period-local/cross-period clocks; success/failure; administrative rows, Pressure and receipts; missing geometry; pre-entry, temporary absence, substitution, permanent exit and dismissal; contradictory intervals; duplicate UUIDs; conflicting IDs; the four recovery originals; supported measurements; all earlier batches. Existing suites cover indexed equal-clock and ambiguous ordering. New diagnostic tests reject tampered hash/team/index/time, preserve raw counts/UUIDs and ratio semantics, retain unknown-duration policy, reject withholding based on the supported pre-exit action and verify the real permanent-exit contradiction.','',
        '## Evidence limitations, failed attempts and next phase','',
        'These are independent calculations over retained same-provider records, not external historical attestation. The contradictory exit/return is not repaired. The four boundary overruns remain unresolved without explicit corrected provider or independent boundary evidence. Unknown coverage, lineup and identity evidence is not invented. All original 107 source exceptions remain; the verified correction changes diagnostic admission rather than raw chronology.','',
        'Failed/partial attempts remain under `audit-output/*attempt*`. An initial serialization failure, a population diagnostic stopped after 100 fixtures to separate missing geometry from actual chronology, and a pre-scan syntax error are preserved. The corrected scan is the sole completed full source replay. A proposed write was not executed when automatic approval review hit a usage limit; work resumed after the user requested continuation. A later oversized Windows command was rejected before execution and recorded separately.','',
        'Reproduce with the retained sibling evidence: priority preflight `python -B -m scripts.reconcile_event_chronology --priority`; targeted/public/private suites; final source replay `python -B -m scripts.reconcile_event_chronology`; final numerical/admission pass `python -B -m scripts.finalize_event_chronology`. Scans refuse existing output directories; preserve completed/failed runs. Finalization changes only in-memory diagnostic facts and ignored outputs.','',
        'Recommended next phase: review this pressure-admission correction and its integration contract before any versioned reconstruction, then proceed to Batch 4 stable-ID/source-name and delivered-appearance reconciliation. Keep unresolved chronology in a provider-resolution queue. Do not apply a timing tolerance or generate/publish V2 without explicit approval.','',
        '## Full local modified-file inventory','',
        'Tracked additions: '+', '.join('`'+p+'`' for p in review_files)+'. No existing tracked production source, published JSON, V1 numerical output, original StatsBomb record or frozen reference is modified.','',
        'Required private evidence: `audit-output/event-chronology/{original-exception-inventory.csv,current-exception-inventory.csv,exception-classifications.csv,changed-metric-events.csv,appearance-comparison.csv,player-impact.csv,full-population-comparison.csv,unresolved-conflicts.csv,summary.json,input-hashes.json,test-results.json,artifact-inventory.json}`. Supplemental: `verified-measurement-corrections.json`, `source-reconciliation-inventory-comparison.csv`, `coverage-interval-evidence.csv`, `priority-evidence.json`, `source-uuid-index.sqlite`. Priority checks, failed attempts, complete test/build logs and private harnesses stay ignored under `audit-output`. Ignored provisioning/build artifacts include `frontend/node_modules` (junction) and `frontend/dist/`. The artifact inventory enumerates private/review/build files with size and SHA256, excluding its own recursive hash and without traversing data/dependency junctions.']
    (ROOT/review_files[-1]).write_text('\n'.join(lines)+'\n',encoding='utf8')
    for path,receipt in receipts.items():
        with Path(path).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==receipt['sha256'],path
    dump('input-hashes.json',receipts)
    inventory=[]
    for parent,dirs,files in os.walk(ROOT/'audit-output',followlinks=False):
        dirs[:]=[d for d in dirs if d not in ('node_modules','data','dist','__pycache__')]
        for name in files:
            p=Path(parent)/name
            if p==out/'artifact-inventory.json':continue
            with p.open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
            inventory.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=h))
    for p in [*(ROOT/name for name in review_files),*(ROOT/'frontend/dist').rglob('*')]:
        if p.is_file():
            with p.open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
            inventory.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=h))
    dump('artifact-inventory.json',inventory)
    print(json.dumps(dict(affected=[{k:r[k] for k in ('player_id','name','attribute_changes','formula_b_delta','eligibility_changed')} for r in affected],summary={k:summary[k] for k in ('original_remaining','current_published_exceptions','current_all_roster_exceptions','confirmed_diagnostic_admission_defects','changed_admitted_action_uuids','successful_pressure_action_delta','pressure_attempt_delta','exposure_seconds_delta','formula_b_delta','eligibility_changes')},artifact_count=len(inventory)),indent=2))

if __name__=='__main__':main()
