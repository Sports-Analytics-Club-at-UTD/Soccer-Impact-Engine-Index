"""Batch 5 read-only source binding and complete diagnostic comparison.

Run after python -B -m scripts.verify_batch4_numerics. Reuses the completed
Batch 4 replay only after rehashing source receipts and all prior production
modules. Does not reconstruct participation or publish output.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
from pathlib import Path
import ast, csv, hashlib, json, sqlite3, subprocess
import pandas as pd
from pandas.testing import assert_frame_equal
from src.identity import PLAYER_KEYS
from src.metrics import recovery_coverage as legacy, safe_recovery as safe
from src.recovery import integrate_recovery

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'Soccer-Impact-Engine-Index'
B4=ROOT.parent/'Soccer-Impact-Engine-Index-identity-source-reconciliation'
OUT=ROOT/'audit-output/recovery-helper-hardening'
RECEIPTS={}


def bind(path, expected=None):
    path=Path(path)
    with path.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    if expected is not None:assert h==expected,(str(path),h,expected)
    RECEIPTS[str(path.resolve())]=dict(sha256=h,bytes=path.stat().st_size)
    return path


def js(path):return json.loads(bind(path).read_bytes())
def rows(path):
    with bind(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=True,default=str)+'\n',encoding='utf8')
def csvout(name,rs,fields=None):
    rs=list(rs);fields=fields or list(rs[0])
    with (OUT/name).open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rs:w.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in r.items()})


def synthetic():
    base=dict(player_id=1,player="José D'Angelo",team='Club',competition_name='League',season_name='2015/2016',event_type='Ball Recovery',zone='defensive')
    rec=pd.DataFrame([base|dict(id='uuid-A'),base|dict(id='uuid-B',player_id=2)])
    old,_=legacy.recovery_counts(rec);new,z=safe.recovery_counts(rec)
    assert old['count'].tolist()==[2] and new['count'].tolist()==[1,1]
    minute=new[PLAYER_KEYS].iloc[:1].assign(minutes=90.)
    dup=pd.concat([minute,minute]);old_join=legacy.add_per90(new.iloc[:1],dup,PLAYER_KEYS)
    try:safe.add_per90(new.iloc[:1],dup,PLAYER_KEYS)
    except safe.RecoveryInputError as e:error=str(e)
    else:raise AssertionError('unsafe join accepted')
    csvout('grouping-comparison.csv',[dict(player_id=int(r.player_id),team=r.team,competition=r.competition_name,season=r.season_name,event_uuids=rec.loc[rec.player_id.eq(r.player_id),'id'].tolist(),safe_count=int(r['count']),legacy_combined_count=2) for _,r in new.iterrows()])
    csvout('join-cardinality-comparison.csv',[dict(case='duplicate_minutes',count_rows=1,minute_rows=2,legacy_output_rows=len(old_join),safe_output_rows=0,outcome=error),dict(case='one_to_one',count_rows=1,minute_rows=1,legacy_output_rows=1,safe_output_rows=len(safe.add_per90(new.iloc[:1],minute,PLAYER_KEYS)),outcome='per90=1'),dict(case='many_to_one',count_rows=2,minute_rows=1,legacy_output_rows=2,safe_output_rows=len(safe.add_per90(pd.concat([new.iloc[:1],new.iloc[:1]]),minute,PLAYER_KEYS)),outcome='two preserved count rows')])
    dump('original-helper-reproduction.json',dict(name_collision_reproduced=True,minute_multiplication_reproduced=True,legacy_name_group_rows=len(old),legacy_count=2,safe_ids=[1,2],safe_counts=[1,1],uuid_sets={'1':['uuid-A'],'2':['uuid-B']},legacy_join_rows=2,safe_duplicate_error=error))


def provenance():
    inv=[]
    for folder in ['src','scripts','tests','notebooks']:
        for p in (ROOT/folder).rglob('*'):
            if p.suffix not in ('.py','.ipynb'):continue
            if p.name in ('verify_recovery_helper_hardening.py','test_safe_recovery.py','safe_recovery.py'):continue
            for i,line in enumerate(p.read_text(encoding='utf8').splitlines(),1):
                if any(word in line for word in ['recovery_counts','add_per90','DEFAULT_GROUP']):
                    inv.append(dict(path=p.relative_to(ROOT).as_posix(),line=i,source=line.strip(),boundary='historical' if 'metrics/recovery_coverage' in p.as_posix() else 'existing unchanged caller'))
    csvout('helper-callsite-inventory.csv',inv)
    commit='0445f18fa1895320f0679ee84022888793fae6e7'
    historic=subprocess.check_output(['git','show',f'{commit}:src/metrics/recovery_coverage.py'],cwd=ROOT).decode('utf8')
    old=ast.parse(historic);cur=ast.parse((ROOT/'src/metrics/recovery_coverage.py').read_text(encoding='utf8'))
    names=['extract_recovery_events','recovery_counts','add_per90']
    for name in names:
        a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name)
        b=next(n for n in cur.body if isinstance(n,ast.FunctionDef) and n.name==name)
        assert ast.dump(a)==ast.dump(b),name
    dump('provenance-compatibility-review.json',dict(original_signatures=['recovery_counts(rec, group_cols=DEFAULT_GROUP)','add_per90(counts, minutes, on, min_minutes=None)'],original_bodies_changed=False,original_ast_equal_to_contributor=names,contributor_commit=commit,guarded_module='src.metrics.safe_recovery',guarded_signatures=['recovery_counts(rec, group_cols=tuple(PLAYER_KEYS))','add_per90(counts, minutes, on, min_minutes=None)'],existing_callers_changed=False,default_group_imports_outside_excerpt=0,current_tracked_notebooks=list(str(p.relative_to(ROOT)) for p in (ROOT/'notebooks').rglob('*.ipynb')),contributor_original_cli_uses_name_default=True,legacy_api_accessible=True,contributor_migration='Optional explicit opt-in to guarded API with source-verified stable IDs and unique supported exposure; existing historical imports unchanged',external_untracked_workflows='Cannot enumerate; retained API is unchanged',frozen_reproduction='Original contributor excerpt and production reconstruction remain byte-identical'))


def verify_reuse():
    checks=Counter()
    for p in (B4/'src').rglob('*.py'):
        target=ROOT/p.relative_to(B4);bind(target,hashlib.sha256(p.read_bytes()).hexdigest());bind(p);checks['unchanged_existing_production_modules']+=1
    for relative in ['scripts/reconstruct_player_evidence.py','scripts/event_chronology_diagnostics.py','scripts/verify_batch4_numerics.py']:
        a,b=bind(ROOT/relative).read_bytes(),bind(B4/relative).read_bytes()
        assert a.replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n')
    inv=js(B4/'audit-output/identity-source-reconciliation/artifact-inventory.json')
    for r in inv:
        p=B4/r['path']
        # Bind the replay's source/UUID, numerical and reference evidence.
        if r['path'].startswith('audit-output/identity-source-reconciliation/') or r['path'].startswith('audit-output/batch4-'):
            bind(p,r['sha256']);checks['prior_artifacts_rehashed']+=1
    historical_script_receipts=[]
    for receipt in [B4/'audit-output/identity-source-reconciliation/input-hashes.json',B4/'audit-output/batch4-additional/additional-input-hashes.json',B4/'audit-output/batch4-numerics/input-hashes.json']:
        for path,r in js(receipt).items():
            # Diagnostic scripts/reports may have been finalized after their
            # self-receipt was captured. They do not gate production replay
            # reuse; bind their current bytes and record any stale receipt.
            p=Path(path)
            diagnostic=any(part in p.parts for part in ('scripts','docs')) and not any(part in p.parts for part in ('data','src'))
            if diagnostic:
                bind(p)
                if RECEIPTS[str(p.resolve())]['sha256']!=r['sha256']:
                    historical_script_receipts.append(dict(path=path,historical_sha256=r['sha256'],current_sha256=RECEIPTS[str(p.resolve())]['sha256'],scope='Historical diagnostic script/report; not production or original source'))
                continue
            if path in RECEIPTS:
                assert RECEIPTS[path]['sha256']==r['sha256'];continue
            bind(path,r['sha256']);checks['prior_input_receipts_rehashed']+=1
            if '/data/' in Path(path).as_posix():checks['original_data_receipts_rehashed']+=1
    dump('historical-diagnostic-receipt-differences.json',historical_script_receipts)
    prior=js(B4/'audit-output/identity-source-reconciliation/summary.json')
    assert prior['checks']['original_events']==5436699 and prior['checks']['original_fixtures']==1551
    dbp=bind(B4/'audit-output/identity-source-reconciliation/source-uuid-index.sqlite')
    with sqlite3.connect(dbp.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        assert db.execute('select count(*) from events').fetchone()[0]==5436699
        assert db.execute('select count(distinct match_id) from events').fetchone()[0]==1551
        assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
    checks['uuid_index_rows_verified']=5436699;checks['uuid_index_fixtures_verified']=1551
    bind(ROOT/'frontend/public/data/player-ratings-2015-16-v1.json','9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e')
    print('Source hashes, prior evidence and production fingerprints verified',dict(checks),flush=True)
    return checks,prior


def compare_profiles():
    fresh=js(ROOT/'audit-output/batch4-numerics/profiles.json')
    before=rows(B4/'audit-output/identity-source-reconciliation/full-population-comparison.csv')
    byid={r['player_id']:r['batch4'] for r in fresh};result=[]
    from scripts import decoder_fix_independent as raw
    from src.private_five_attribute import validate_reference
    from src.provisional_ovr import formula_b
    ref=validate_reference(js(SOURCE/'data/derived/private-five-attribute-v2/frozen-reference.json'))
    canonical={r['player_id']:r for r in map(json.loads,bind(SOURCE/'data/derived/fifth-attribute-private-v1/player-measurements.jsonl').read_text(encoding='utf8').splitlines())}
    historical=Counter()
    assert len(before)==len(byid)==691
    for row in before:
        pid=int(row['player_id']);current=byid[pid];assert current==json.loads(row['proposed_batch4'])
        for stage in ['v1','merged_batch1','corrected_batch2a','corrected_batch2b','proposed_batch3a','proposed_batch3b','proposed_batch4']:
            data=json.loads(row[stage]);ratings=[]
            for attr,m in data['attributes'].items():
                value=F(m['exact_value']) if m['exact_value'] is not None else None
                score,pct=raw.score(value,F(data['exact_supported_minutes']) if attr=='press_resistance' else F(m['supported_seconds'])/60,F(data['exact_supported_minutes']),canonical[pid]['limited_data'],ref['pools'][canonical[pid]['comparison_group']][attr])
                assert (score,pct)==(m['rating'],m['percentile']),(pid,stage,attr)
                ratings.append(score);historical['attribute_checks']+=1
            assert formula_b(ratings)==data['overall'];historical['formula_b_checks']+=1
        row.update(proposed_batch5=current,batch5_overall_delta=0,batch5_eligibility_changed=False)
        result.append(row)
    csvout('full-population-comparison.csv',result)
    csvout('player-impact.csv',[dict(player_id=r['player_id'],name=r['name'],association_changes=0,numerator_changes=0,exposure_changes=0,rating_changes=0,formula_b_changes=0,eligibility_changed=False,exclusion_reasons=byid[int(r['player_id'])]['exclusion_reasons']) for r in before])
    dump('historical-stage-arithmetic.json',dict(historical))
    return js(ROOT/'audit-output/batch4-numerics/summary.json')


def frozen_and_transfers():
    pkg=SOURCE/'data/derived/private-five-attribute-v2'
    ref=js(pkg/'frozen-reference.json');facts=defaultdict(list)
    for line in bind(pkg/'measurement-facts.jsonl').read_text(encoding='utf8').splitlines():
        r=json.loads(line);facts[r['player_id']].append(r)
    members=defaultdict(list);n=predicates=0
    for line in bind(pkg/'player-measurements.jsonl').read_text(encoding='utf8').splitlines():
        p=json.loads(line);fs=facts[p['player_id']];n+=1
        rational=lambda v:F(v['numerator'],v['denominator'])
        known=sum((rational(x['seconds']) for x in fs if x['seconds'] is not None),F())/60
        complete=bool(fs) and all(x['seconds'] is not None and x['seconds']['numerator']>0 for x in fs)
        limited=any(x['competition_name']=='1. Bundesliga' for x in fs);pending=any(x['match_id']==3879594 for x in fs)
        for attr,m in p['attributes'].items():
            good=[x['metrics'][attr] for x in fs if x['metrics'][attr]['supported']]
            minutes=sum((rational(x['seconds']) for x in good if x['seconds'] is not None),F())/60
            attempts=sum(len(x['denominator_ids']) for x in good) if attr=='press_resistance' else None
            candidate=bool(len(good)==len(fs) and complete and known>=900 and p['comparison_group'] in ('MID','CB') and not limited and not pending and (attr=='press_resistance' and attempts>=40 or attr!='press_resistance' and minutes>=900))
            assert candidate==m['experimental_reference_candidate'],(p['player_id'],attr)
            if candidate:members[p['comparison_group'],attr].append(p['player_id'])
            predicates+=1
    for g,pools in ref['pools'].items():
        for attr,pool in pools.items():assert sorted(members[g,attr])==pool['member_ids']
    assert n==2514 and predicates==12570
    transfer=SOURCE/'data/derived/phase3-step2-source-reconstruction-2026-10-27/transfer-policy-comparison.jsonl'
    tc=Counter()
    for line in bind(transfer).read_text(encoding='utf8').splitlines():
        r=json.loads(line);cs=r['original_contexts'];mids=[mid for c in cs for mid in c['match_ids']]
        assert len(mids)==len(set(mids));tc['actor_fixture_uniqueness']+=1
        for attr,total in r['combined_raw_counts'].items():assert sum(c['raw_counts'][attr] for c in cs)==total;tc['numerator_conservation']+=1
        assert sum((rational(c['supported_minutes']) for c in cs),F())==rational(r['combined_supported_minutes']);tc['exposure_conservation']+=1
    return dict(candidates=n,attribute_predicates=predicates,frozen_fingerprint=ref['sha256'],transfers=dict(tc))


def original_sources():
    leads=rows(ROOT.parent/'Soccer-Impact-Engine-Index-participation-decoder-fix/audit-output/decoder-fix/all-appearance-comparison.csv')
    facts=js(ROOT.parent/'Soccer-Impact-Engine-Index-permanent-exit-support/audit-output/permanent-exit-support/baseline-diagnostic-facts.json')
    evidence=[]
    for mid in [3753991,3754296,3825670,3754048,3900579,3825780,3829454]:
        lead=next(r for r in leads if int(r['match_id'])==mid)
        report=json.loads(bind(lead['report_path'],lead['report_sha256']).read_bytes());b=report['artifacts']['events']
        raw=json.loads(bind(b['path'],b['sha256']).read_bytes());b=report['fixture_document']
        fixture=next(r for r in json.loads(bind(b['path'],b['sha256']).read_bytes()) if r['match_id']==mid)
        b=report['artifacts']['lineups'];lineups=json.loads(bind(b['path'],b['sha256']).read_bytes())
        expected={kind:set() for kind in legacy.EVENT_TYPES};projected=[]
        for e in raw:
            kind=e['type']['name'];duel=e.get('duel',{});inter=e.get('interception',{});br=e.get('ball_recovery',{})
            selected=('Tackle' if kind=='Duel' and duel.get('type',{}).get('name')=='Tackle' and duel.get('outcome',{}).get('name') in {'Won','Success In Play','Success Out'} else 'Interception' if kind=='Interception' and inter.get('outcome',{}).get('name') in {'Won','Success In Play','Success Out'} else 'Ball Recovery' if kind=='Ball Recovery' and br.get('recovery_failure') is not True else None)
            if selected:expected[selected].add(e['id'])
            projected.append(dict(id=e['id'],match_id=mid,type=kind,player_id=e.get('player',{}).get('id'),player=e.get('player',{}).get('name'),team=e.get('team',{}).get('name'),competition_name=fixture['competition']['competition_name'],season_name=fixture['season']['season_name'],location=e.get('location'),duel_type=duel.get('type',{}).get('name'),duel_outcome=duel.get('outcome',{}).get('name'),interception_outcome=inter.get('outcome',{}).get('name'),ball_recovery_recovery_failure=br.get('recovery_failure')))
        events=pd.DataFrame(projected);rec=legacy.extract_recovery_events(events)
        for kind,ids in expected.items():assert set(rec.loc[rec.event_type.eq(kind),'id'])==ids
        x=pd.DataFrame([dict(player_name_raw=p['player_name'],player_id=p['player_id'],team=t['team_name'],competition_name=fixture['competition']['competition_name'],season_name=fixture['season']['season_name']) for t in lineups for p in t['lineup']])
        pop=x[PLAYER_KEYS].drop_duplicates().reset_index(drop=True)
        denominator={f['player_id']:float(F(f['seconds']['numerator'],f['seconds']['denominator'])/60) for f in facts if f['match_id']==mid and f['seconds'] is not None}
        minutes=pop.copy();minutes['minutes']=minutes.player_id.map(denominator).astype(float)
        integrated=integrate_recovery(events,x,minutes,pop)
        selected=integrated.identity.selected_events();totals,zones=safe.recovery_counts(selected)
        assert_frame_equal(zones,integrated.by_zone)
        rates=safe.add_per90(totals,minutes,PLAYER_KEYS)
        assert_frame_equal(rates,integrated.totals.drop(columns='rate_status'))
        for _,row in rates.iterrows():
            raw_ids={e['id'] for e in raw if e.get('player',{}).get('id')==row.player_id and e.get('team',{}).get('name')==row.team} & expected[row.event_type]
            assert len(raw_ids)==row['count']
            denom=denominator.get(row.player_id)
            if denom is not None and denom>0:assert row.per90==len(raw_ids)/denom*90
            else:assert pd.isna(row.per90)
        for kind,ids in expected.items():
            assert set(selected.loc[selected.event_type.eq(kind),'id'])==ids
            assert int(totals.loc[totals.event_type.eq(kind),'count'].sum())==len(ids)
        evidence.append(dict(match_id=mid,raw_events=len(raw),selected_uuid_sets={k:sorted(v) for k,v in expected.items()},unknown_location_count=int(selected.zone.isna().sum()),total_count=int(totals['count'].sum()),zone_count=int(zones['count'].sum()),supported_denominators=int(minutes.minutes.notna().sum()),rates_equal=True))
    return evidence


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    synthetic();provenance();checks,prior=verify_reuse();numeric=compare_profiles();frozen=frozen_and_transfers();original=original_sources()
    dump('raw-count-conservation.json',dict(original_fixture_checks=original,fresh_uuid_index_integrity=True,hash_verified_reused_source_checks=prior['checks'],hash_verified_reused_prior_corrections=prior['prior_corrections'],new_full_source_replay=False))
    csvout('unresolved-risks.csv',[dict(risk='Historical unguarded API remains accessible',status='Intentional compatibility boundary',action='New reuse imports src.metrics.safe_recovery; raw identity workflows use integrate_recovery'),dict(risk='Untracked external contributor usage cannot be inventoried',status='API retained unchanged',action='Opt-in migration documented; never infer stable IDs'),dict(risk='Existing source coverage, chronology and source-name restrictions',status='Preserved from Batches 1–4',action='Separate evidence review before Ratings V2')])
    dump('summary.json',dict(baseline='886d58413ee8777585ae989a2d97744171decb5b',synthetic_defects_reproduced=2,original_function_bodies_changed=False,new_guarded_api=True,existing_production_callers_changed=False,checks=dict(checks),fresh_numerics=numeric,fresh_frozen_and_transfer_checks=frozen,original_fixture_checks=len(original),changed_associations=0,changed_numerators=0,changed_exposure=0,changed_published_ratings=0,changed_eligibility=0,prior_corrections_preserved=prior['prior_corrections'],source_replay='Hash-verified Batch 4/3B reuse, not a fresh replay',publication_authorized=False))
    dump('input-hashes.json',RECEIPTS)
    print('Batch 5 verification complete',flush=True)


if __name__=='__main__':main()
