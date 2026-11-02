"""Private, exclusive-output V2 reconstruction using authorized retained evidence.

python -B -m scripts.reconstruct_ratings_v2 --output audit-output/ratings-v2
Run the full source replay first; see the reconstruction report.
"""
import argparse
from collections import Counter, defaultdict
import copy
import csv
from fractions import Fraction as F
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import statistics
import subprocess
import sys

from scripts import decoder_fix_independent as oracle
from src.private_five_attribute import ATTRIBUTES, validate_reference
from src.ratings_v2 import reconstruct, rank_profiles, independent_b, VERSION, ADMISSION_VERSION

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'Soccer-Impact-Engine-Index'
B3A = ROOT.parent / 'Soccer-Impact-Engine-Index-permanent-exit-support'
B3B = ROOT.parent / 'Soccer-Impact-Engine-Index-event-chronology-reconciliation'
B5 = ROOT.parent / 'Soccer-Impact-Engine-Index-recovery-helper-hardening'
BASELINE = '1686a4f82d22f2e31935fe9cdacbc93a9ffac849'
PUBLIC_SHA = '9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e'
REF_SHA = '403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd'
STAGES = ['v1', 'merged_batch1', 'corrected_batch2a', 'corrected_batch2b',
          'proposed_batch3a', 'proposed_batch3b', 'proposed_batch4', 'proposed_batch5']


def fraction(v):
    return None if v is None else F(v['numerator'], v['denominator'])


def file_sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def write_csv(path, rows, fields=None):
    rows = list(rows)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row)) or ['player_id', 'reason']
    f=io.StringIO(newline='')
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for row in rows:
        w.writerow({k: json.dumps(v, sort_keys=True, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    write_verified(path,f.getvalue().encode('utf8'))


def write_verified(path,data):
    """Resume only byte-identical artifacts; never overwrite different evidence."""
    if path.exists():
        if path.read_bytes()!=data:raise ValueError('Preserve differing previous evidence: '+str(path))
        return
    with path.open('xb') as f:f.write(data)


def split_half_review(players, facts, reference):
    """Descriptive fixture-cluster split; no confidence intervals or refitting.

    Alternate sorted provider fixture IDs. This is not a chronological holdout.
    Each half requires eight supported fixtures and forty pressure attempts.
    The 900-minute full-profile rule remains unchanged in the product candidate.
    """
    observations=[]
    for p in players:
        if not p['ovr']['eligible']:continue
        rows=sorted(facts[p['player_id']],key=lambda r:r['match_id'])
        halves=[]
        for part in (rows[::2],rows[1::2]):
            samples=sum(len(r['metrics']['press_resistance']['denominator_ids']) for r in part)
            if len(part)<8 or samples<40:
                halves.append(dict(available=False,fixtures=len(part),press_attempts=samples,reason='FEWER_THAN_8_FIXTURES_OR_40_PRESS_ATTEMPTS'))
                continue
            secs=sum((fraction(r['seconds']) for r in part),F())
            ratings=[]
            for a in ATTRIBUTES:
                n=sum(len(r['metrics'][a]['numerator_ids']) for r in part)
                value=F(n*100,samples) if a=='press_resistance' else F(n*5400)/secs
                pool=reference['pools'][p['comparison_group']][a]
                ratings.append(min(99.,max(1.,65.+10.*(float(value)-pool['mean'])/pool['sample_sd'])))
            halves.append(dict(available=True,match_ids=[r['match_id'] for r in part],press_attempts=samples,supported_minutes=str(secs/60),formula_b=independent_b(ratings)))
        observations.append(dict(player_id=p['player_id'],position_group=p['comparison_group'],full_formula_b=p['ovr']['value'],halves=halves))
    summary={}
    for g in ('MID','CB'):
        paired=[r for r in observations if r['position_group']==g and all(h['available'] for h in r['halves'])]
        def ranks(side):
            values={r['player_id']:r['halves'][side]['formula_b'] for r in paired}
            return {pid:1+sum(v>x for v in values.values())+(sum(v==x for v in values.values())-1)/2 for pid,x in values.items()}
        a,b=ranks(0),ranks(1)
        summary[g]=dict(paired_profiles=len(paired),withheld_profiles=sum(r['position_group']==g for r in observations)-len(paired),spearman=statistics.correlation([a[k] for k in a],[b[k] for k in a]) if len(a)>1 else None,top10_common=len(set(sorted(a,key=lambda k:(a[k],k))[:10])&set(sorted(b,key=lambda k:(b[k],k))[:10])),top20_common=len(set(sorted(a,key=lambda k:(a[k],k))[:20])&set(sorted(b,key=lambda k:(b[k],k))[:20])))
    return dict(method='Alternating sorted provider fixture IDs; fixed full-profile eligible cohort; minimum 8 fixtures and 40 attempts in each half; same frozen parameters and Formula B; descriptive within observed coverage only',groups=summary,observations=observations,confidence_intervals='NOT ESTIMATED; incomplete coverage and provider dependence remain')


def build(output, *, numerical_only=False):
    out = Path(output).resolve()
    if not out.is_relative_to(ROOT / 'audit-output'):
        raise ValueError('candidate must remain in ignored audit-output')
    out.mkdir(parents=True, exist_ok=True)
    receipts = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        with path.open('rb') as f:
            h = hashlib.file_digest(f, 'sha256').hexdigest()
        if expected is not None:
            assert h == expected, (str(path), h, expected)
        receipts[str(path)] = dict(sha256=h, bytes=path.stat().st_size)
        return path

    def js(path, expected=None):
        return json.loads(bind(path, expected).read_bytes())

    def table(path):
        with bind(path).open(encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))

    def dump(name, data):
        write_verified(out/name,(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf8'))

    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert sha == BASELINE
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASELINE, 'origin/main'], cwd=ROOT, check=True)
    public = js(ROOT / 'frontend/public/data/player-ratings-2015-16-v1.json', PUBLIC_SHA)
    recipient_ids = {int(p['player_id']) for p in public['players']}
    assert len(recipient_ids) == 691
    pkg = SOURCE / 'data/derived/private-five-attribute-v2'
    manifest = js(pkg / 'manifest.json', '5a8030b4a6ca06aeec81538221b07315c5644a9025915eb31c0bf2dab3cc9bc6')
    for name, h in manifest['artifacts'].items():
        bind(pkg / name, h)
    for folder in ('private-ovr-comparison-v1','private-ovr-comparison-v2'):
        research=SOURCE/'data/derived'/folder
        for name in ('manifest.json','policy.json','summary.json','statistical-analysis.json','independent-numeric-validation.json','validation.json','player-comparison.jsonl','three-formula-player-comparison.jsonl'):
            path=research/name
            if path.exists():bind(path)
    reference = validate_reference(js(pkg / 'frozen-reference.json'))
    assert reference['sha256'] == REF_SHA
    canonical_path = SOURCE / 'data/derived/fifth-attribute-private-v1/player-measurements.jsonl'
    fifth = js(canonical_path.parent / 'manifest.json')
    canonical = [json.loads(s) for s in bind(canonical_path, fifth['artifacts'][canonical_path.name]).read_text(encoding='utf8').splitlines()]
    # Verify retained corrections against their sealed output receipts before use.
    seals = js(B3A / 'audit-output/permanent-exit-support/output-hashes.json')
    for path, h in seals.items():
        bind(B3A / path, h)
    for root, folder in [(B3B, 'event-chronology'), (B5, 'recovery-helper-hardening')]:
        inventory = js(root / 'audit-output' / folder / 'artifact-inventory.json')
        for item in inventory:
            path = root / item['path']
            if path.name in ('full-population-comparison.csv', 'current-exception-inventory.csv', 'verified-measurement-corrections.json','historical-diagnostic-receipt-differences.json'):
                bind(path, item['sha256'])
    base = B3A / 'audit-output/permanent-exit-support'
    facts = {(f['player_id'], f['match_id']): f for f in js(base / 'baseline-diagnostic-facts.json')}
    pending = js(base / 'pending-corrected-facts.json')
    for f in pending:
        facts[f['player_id'], f['match_id']] = f
    appearance_decisions=table(base/'all-appearance-comparison.csv')
    removed=set()
    for row in appearance_decisions:
        if row['removed_nonappearance']=='True':
            assert row['corrected_status']=='BENCH_NO_ASSERTED_APPEARANCE' and not row['corrected_seconds'] and json.loads(row['off_field_discipline'])
            removed.add((int(row['player_id']),int(row['match_id'])))
    exceptions = table(B3B / 'audit-output/event-chronology/current-exception-inventory.csv')
    prior = table(B5 / 'audit-output/recovery-helper-hardening/full-population-comparison.csv')
    historical = {int(r['player_id']): r for r in prior}
    assert set(historical) == recipient_ids
    scored, corrected, changed, proofs = reconstruct(canonical, list(facts.values()), reference, exceptions, removed_nonappearances=removed)
    # Second reconstruction reverses all input order, reopens the chronology
    # proofs, and must produce identical bytes/values, including all N/A states.
    repeated = reconstruct(list(reversed(canonical)), list(reversed(list(facts.values()))), reference, list(reversed(exceptions)), removed_nonappearances=removed)
    assert repeated[0] == scored and sorted(repeated[1], key=lambda r:(r['player_id'],r['match_id'])) == sorted(corrected, key=lambda r:(r['player_id'],r['match_id']))
    players = [p for p in scored if p['player_id'] in recipient_ids]
    assert len(players) == 691
    byid = {p['player_id']:p for p in players}
    fs = defaultdict(list)
    for f in corrected:
        fs[f['player_id']].append(f)
    checks = Counter()
    snapshots = {}
    for p in players:
        pid = p['player_id']; rows = sorted(fs[pid], key=lambda f:f['match_id'])
        known = sum((fraction(f['seconds']) for f in rows if f['seconds'] is not None), F()) / 60
        assert fraction(p['known_supported_minutes']) == known
        independent_attrs = {}; ratings = []; eligible = bool(rows) and all(f['seconds'] is not None and fraction(f['seconds']) > 0 for f in rows)
        for attr in ATTRIBUTES:
            good = [f for f in rows if f['metrics'][attr]['supported']]
            ids = [u for f in good for u in f['metrics'][attr]['numerator_ids']]
            denids = [u for f in good for u in (f['metrics'][attr]['denominator_ids'] or [])]
            assert len(ids) == len(set(ids)) and len(denids) == len(set(denids))
            n = len(ids); attempts = len(denids) if attr == 'press_resistance' else None
            secs = sum((fraction(f['metrics'][attr]['seconds']) for f in good if f['metrics'][attr]['seconds'] is not None), F())
            value = F(100*n, attempts) if attempts else F(n*5400)/secs if attr != 'press_resistance' and secs else None
            pool = reference['pools'][p['comparison_group']][attr]
            rating, pct = oracle.score(value, known if attr == 'press_resistance' else secs/60, known, p['limited_data'], pool)
            obs = p['attributes'][attr]
            assert (fraction(obs['exact_value']), obs['experimental_rating'], obs['percentile']) == (value, rating, pct)
            assert obs['numerator_match_ids'] == [f['match_id'] for f in good]
            eligible &= bool(pid in pool['member_ids'] and rating is not None and known >= 900 and secs/60 == known and secs >= 54000 and len(good) == len(rows) and not p['limited_data'] and (attr != 'press_resistance' or attempts >= 40) and all(f['match_id'] != 3879594 for f in rows))
            independent_attrs[attr] = dict(numerator=n, attempts=attempts, exact_value=str(value) if value is not None else None, supported_seconds=str(secs), supported_minutes=float(secs/60), supported_match_ids=[f['match_id'] for f in good], excluded=[dict(match_id=f['match_id'], reasons=f['metrics'][attr]['reasons']) for f in rows if not f['metrics'][attr]['supported']], rating=rating, percentile=pct, frozen_member=pid in pool['member_ids'])
            ratings.append(rating); checks['independent_attribute_checks'] += 1
        assert independent_b(ratings) == p['ovr']['value']
        assert eligible == p['ovr']['eligible']
        snap = dict(appearance_ids=[f['match_id'] for f in rows], supported_appearance_ids=[f['match_id'] for f in rows if f['seconds'] is not None], exact_supported_minutes=str(known), supported_minutes=float(known), attributes=independent_attrs, overall=p['ovr']['value'], eligible=eligible, exclusion_reasons=p['ovr']['exclusion_reasons'])
        assert snap == json.loads(historical[pid]['proposed_batch5']), pid
        snapshots[pid] = snap
        checks['independent_formula_b_checks'] += 1; checks['independent_eligibility_checks'] += 1
        for stage in STAGES:
            s = json.loads(historical[pid][stage]); rs = []
            for attr, m in s['attributes'].items():
                v = F(m['exact_value']) if m['exact_value'] is not None else None
                rating, pct = oracle.score(v, F(s['exact_supported_minutes']) if attr == 'press_resistance' else F(m['supported_seconds'])/60, F(s['exact_supported_minutes']), p['limited_data'], reference['pools'][p['comparison_group']][attr])
                assert (rating,pct) == (m['rating'],m['percentile']); rs.append(rating)
                checks['historical_attribute_checks'] += 1
            assert independent_b(rs) == s['overall']; checks['historical_formula_b_checks'] += 1
        assert json.loads(historical[pid]['proposed_batch4']) == json.loads(historical[pid]['proposed_batch5'])
        assert json.loads(historical[pid]['proposed_batch3b']) == json.loads(historical[pid]['proposed_batch4'])
    from scripts import verify_recovery_helper_hardening as guarded_checks
    frozen_transfer_checks = guarded_checks.frozen_and_transfers()
    receipts.update(guarded_checks.RECEIPTS)
    # Verify conservation again over the corrected current transfer contexts.
    for p in players:
        contexts=p['contexts']
        mids=[mid for c in contexts for mid in c['match_ids']]
        assert len(mids)==len(set(mids))==len(fs[p['player_id']])
        if len(contexts)>1:
            context_seconds=[]
            for c in contexts:
                parts=[f for f in fs[p['player_id']] if f['match_id'] in c['match_ids']]
                assert all((f['team'],f['competition_name'])==(c['team'],c['competition_name']) for f in parts)
                context_seconds.append(sum((fraction(f['seconds']) for f in parts if f['seconds'] is not None),F()))
            assert sum(context_seconds,F())/60==fraction(p['known_supported_minutes'])
            checks['corrected_transfer_exposure_checks']+=1
            for a in ATTRIBUTES:
                total=sum(len(f['metrics'][a]['numerator_ids']) for f in fs[p['player_id']] if f['metrics'][a]['supported'])
                assert total==p['attributes'][a]['numerator']
                checks['corrected_transfer_numerator_checks']+=1
            checks['corrected_transfer_fixture_checks']+=1
    checkpoint=dict(checks=checks,profiles=len(players),complete=sum(p['ovr']['value'] is not None for p in players),snapshots=snapshots,frozen_and_transfer_checks=frozen_transfer_checks)
    checkpoint_path=out/'numerical-checkpoint.json'
    if checkpoint_path.exists():
        previous=json.loads(checkpoint_path.read_bytes())
        assert previous['snapshots']==json.loads(json.dumps(snapshots))
        assert all(checkpoint['checks'][k]==v for k,v in previous['checks'].items())
    else:dump('numerical-checkpoint.json',checkpoint)
    if numerical_only:
        print(json.dumps(dict(checks=checks,profiles=len(players),complete=checkpoint['complete'])),flush=True)
        return
    replay_dir = out / 'source-replay'
    replay = js(replay_dir / 'summary.json')
    assert replay['mode'] == 'complete' and replay['source_checks']['original_events'] == 5436699
    fresh_exceptions=table(replay_dir/'current-exception-inventory.csv')
    def exception_key(r):
        return (r['event_id'],int(r['player_id']),int(r['match_id']),int(r['team_id']),int(r['period']),r['timestamp'],int(r['event_index']),tuple(json.loads(r['selected_metrics'])))
    assert {exception_key(r) for r in fresh_exceptions}=={exception_key(r) for r in exceptions}
    checks['fresh_chronology_ledger_bindings']=len(fresh_exceptions)
    for path, receipt in js(replay_dir / 'input-hashes.json').items():
        bind(path, receipt['sha256'])
    from scripts.verify_bundesliga_readiness import position_group
    appearance_index={(int(r['player_id']),int(r['match_id'])):r for r in table(replay_dir/'appearance-comparison.csv')}
    position_review=[]
    for p in players:
        pid=p['player_id'];v1=json.loads(historical[pid]['v1'])
        positions={name:fraction(seconds) for name,seconds in p['position_seconds'].items()}
        added=set(snapshots[pid]['supported_appearance_ids'])-set(v1['supported_appearance_ids'])
        for mid in sorted(added):
            for allocation in json.loads(appearance_index[pid,mid]['position_allocation']):
                name=allocation['position'];positions[name]=positions.get(name,F())+fraction(allocation['elapsed_seconds'])
        groups=defaultdict(F)
        for name,seconds in positions.items():groups[position_group(name)]+=seconds
        high=max(groups.values());fine=sorted(g for g,s in groups.items() if s==high and high>0)
        group=('MID' if fine[0] in ('CM','DM') else fine[0]) if len(fine)==1 else None
        assert group==p['comparison_group']
        position_review.append(dict(player_id=pid,comparison_group=group,canonical_fine_groups=p['dominant_fine_groups'],corrected_dominant_fine_groups=fine,fine_group_changed=fine!=p['dominant_fine_groups'],corrected_position_seconds={k:str(v) for k,v in positions.items()},added_supported_fixtures=sorted(added),display_policy='Retain canonical product fine labels; corrected fine dominance remains diagnostic metadata under existing batch contract'))
    write_csv(out/'position-exposure-comparison.csv',position_review)
    # Bidirectional actor/fixture/UUID membership uses a fresh replay database.
    dbpath = bind(replay_dir / 'source-uuid-index.sqlite')
    db = sqlite3.connect(dbpath.as_uri()+'?mode=ro&immutable=1', uri=True)
    assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
    assert db.execute('select count(*),count(distinct match_id) from events').fetchone() == (5436699,1551)
    for p in players:
        for f in fs[p['player_id']]:
            for a, m in f['metrics'].items():
                for uid in set(m['numerator_ids']) | set(m['denominator_ids'] or []):
                    assert db.execute('select match_id,team_id,player_id from events where uuid=?',(uid,)).fetchone() == (f['match_id'], f['evidence']['component_team_id'],p['player_id'])
                    checks['uuid_actor_fixture_checks'] += 1
    db.close()
    # Original successful recovery categories are disjoint. Preserve totals
    # independently of known-zone counts; missing locations never erase actions.
    leads={int(r['match_id']):json.loads(r['evidence']) for r in table(ROOT.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit/appearances.csv')}
    per_match=defaultdict(list)
    for f in corrected:
        if f['player_id'] in recipient_ids:per_match[f['match_id']].append(f)
    zones=defaultdict(lambda:dict(total=0,known_zone=0,unknown_zone=0,by_zone=Counter()))
    fixture_inventory=[]
    assert set(per_match)<=set(leads)
    for mid in sorted(leads):
        rows=per_match.get(mid,[])
        lead=leads[mid];report=js(lead['report_path'],lead['report_sha256']);doc=report['artifacts']['events']
        fixture_inventory.append(dict(match_id=mid,competition=report['competition_name'],season=report['season_name'],report_path=lead['report_path'],report_sha256=lead['report_sha256'],events_path=doc['path'],events_sha256=doc['sha256'],lineups_path=report['artifacts']['lineups']['path'],lineups_sha256=report['artifacts']['lineups']['sha256']))
        fixture_inventory[-1]['fixture_document']=report['fixture_document']
        events={e['id']:e for e in js(doc['path'],doc['sha256'])}
        for f in rows:
            categories=[set(f['metrics'][a]['numerator_ids']) for a in ('tackles','interceptions','recoveries')]
            assert len(set.union(*categories))==sum(map(len,categories))
            for a in ('tackles','interceptions','recoveries'):
                m=f['metrics'][a]
                if not m['supported']:continue
                z=zones[f['player_id'],a]
                for uid in m['numerator_ids']:
                    e=events[uid];assert e['player']['id']==f['player_id'] and a in oracle.selected(e)
                    loc=e.get('location');z['total']+=1
                    if loc and len(loc)>=2 and all(type(v) in (int,float) and math.isfinite(v) for v in loc[:2]) and 0<=loc[0]<=120 and 0<=loc[1]<=80:
                        xb=0 if loc[0]<40 else 1 if loc[0]<80 else 2
                        yb=0 if loc[1]<80/3 else 1 if loc[1]<160/3 else 2
                        z['known_zone']+=1;z['by_zone'][str(1+xb+3*yb)]+=1
                    else:z['unknown_zone']+=1
    zone_rows=[]
    for p in players:
        for a in ('tackles','interceptions','recoveries'):
            z=zones[p['player_id'],a]
            assert z['total']==(p['attributes'][a]['numerator'] or 0)==z['known_zone']+z['unknown_zone']
            assert sum(z['by_zone'].values())==z['known_zone']
            zone_rows.append(dict(player_id=p['player_id'],attribute=a,**z))
    write_csv(out/'recovery-zone-accounting.csv',zone_rows)
    assert len(fixture_inventory)==1551
    write_csv(out/'original-fixture-inventory.csv',fixture_inventory)
    oldplayers = [dict(player_id=int(p['player_id']), comparison_group=p['comparison_position'], ovr=p['ovr']) for p in public['players']]
    oldrank = rank_profiles(oldplayers); newrank = rank_profiles(players)
    oldall = rank_profiles(oldplayers,eligible_only=False); newall = rank_profiles(players,eligible_only=False)
    for population, ranks, eligible_only in [(oldplayers,oldrank,True),(players,newrank,True),(oldplayers,oldall,False),(players,newall,False)]:
        for p in population:
            value=p['ovr']['value']
            if value is None or eligible_only and not p['ovr']['eligible']:
                assert p['player_id'] not in ranks
                continue
            expected=1+sum(q['comparison_group']==p['comparison_group'] and q['ovr']['value'] is not None and (not eligible_only or q['ovr']['eligible']) and (q['ovr']['value']>value or q['ovr']['value']==value and q['player_id']<p['player_id']) for q in population)
            assert ranks[p['player_id']]==expected
            checks['independent_rank_checks']+=1
    bind(ROOT/'frontend/src/lib/playerNames.js')
    display_names=json.loads(subprocess.check_output(['node','--input-type=module','-e',"import {playerName} from './frontend/src/lib/playerNames.js';let b='';for await(const c of process.stdin)b+=c;console.log(JSON.stringify(Object.fromEntries(JSON.parse(b).map(p=>[p.player_id,playerName(p).name]))));"],input=json.dumps(public['players']).encode('utf8'),cwd=ROOT))
    comparisons=[]; attrs=[]; lineage=[]; admissions=[]
    for old in public['players']:
        pid=int(old['player_id']); p=byid[pid]; before=json.loads(historical[pid]['v1']); after=snapshots[pid]
        assert old['ovr']['value']==before['overall'] and old['ovr']['eligible']==before['eligible']
        batches=[]; previous=before
        for label, stage in zip(['1','2A','2B','3A','3B','4','5'],STAGES[1:]):
            nxt=json.loads(historical[pid][stage])
            if nxt != previous:batches.append(label)
            previous=nxt
        changed_uuids=set(); changed_fixtures=set()
        for a in ATTRIBUTES:
            b=before['attributes'][a]; n=after['attributes'][a]
            public_key='line_breaking_passes' if a=='progressive_passing' else a
            assert old['attributes'][public_key]['rating']==b['rating'] and old['attributes'][public_key]['percentile']==b['percentile']
            bs=set(b['supported_match_ids']); ns=set(n['supported_match_ids'])
            oldids={u for f in fs[pid] if f['match_id'] in bs for u in f['metrics'][a]['numerator_ids']}
            newids={u for f in fs[pid] if f['match_id'] in ns for u in f['metrics'][a]['numerator_ids']}
            oldden={u for f in fs[pid] if f['match_id'] in bs for u in (f['metrics'][a]['denominator_ids'] or [])}
            newden={u for f in fs[pid] if f['match_id'] in ns for u in (f['metrics'][a]['denominator_ids'] or [])}
            changed_uuids.update(oldids^newids);changed_uuids.update(oldden^newden);changed_fixtures.update(bs^ns)
            attrs.append(dict(player_id=pid,attribute=a,v1=b,v2=n,rating_changed=b['rating']!=n['rating'],numerator_uuids_added=sorted(newids-oldids),numerator_uuids_removed=sorted(oldids-newids),pressure_denominator_uuids_added=sorted(newden-oldden),pressure_denominator_uuids_removed=sorted(oldden-newden),reference_mean=reference['pools'][p['comparison_group']][a]['mean'],reference_sample_sd=reference['pools'][p['comparison_group']][a]['sample_sd'],correction_batches=batches))
        row=dict(player_id=pid,canonical_name=p['name'],display_name=display_names[str(pid)],season=p['season_name'],position_group=p['comparison_group'],v1_formula_b=before['overall'],v2_formula_b=after['overall'],delta_formula_b=after['overall']-before['overall'] if after['overall'] is not None and before['overall'] is not None else None,v1_rank=oldrank.get(pid),v2_rank=newrank.get(pid),rank_delta=oldrank[pid]-newrank[pid] if pid in oldrank and pid in newrank else None,v1_all_complete_rank=oldall.get(pid),v2_all_complete_rank=newall.get(pid),all_complete_rank_delta=oldall[pid]-newall[pid] if pid in oldall and pid in newall else None,v1_eligibility=before['eligible'],v2_eligibility=after['eligible'],eligibility_change_reason=p['ovr']['exclusion_reasons'],verified_minutes_v1=before['exact_supported_minutes'],verified_minutes_v2=after['exact_supported_minutes'],source_fixtures_added=sorted(set(after['appearance_ids'])-set(before['appearance_ids'])),source_fixtures_removed=sorted(set(before['appearance_ids'])-set(after['appearance_ids'])),metric_scope_changed_fixtures=sorted(changed_fixtures),changed_event_uuid_count=len(changed_uuids),correction_batch_ids=batches,source_limitations=dict(limited_data=p['limited_data'],partial_season=p['partial_season'],exclusions=p['ovr']['exclusion_reasons']),verification_status='FRESHLY RECOMPUTED; retained corrected facts source-verified by fresh replay')
        for a in ATTRIBUTES:
            row[a+'_v1']=before['attributes'][a]['rating'];row[a+'_v2']=after['attributes'][a]['rating']
        row.update(five_attribute_complete=all(m['experimental_rating'] is not None for m in p['attributes'].values()),supported_pressure_actions=p['attributes']['press_resistance']['attempts'],all_observed_exposure_supported=p['all_observed_exposure_supported'],unsupported_exposure_fixtures=[f['match_id'] for f in fs[pid] if f['seconds'] is None],valid_position_classification=p['comparison_group'] in ('MID','CB'),transfer_contexts=p['contexts'],competitions=p['competitions'],limited_data=p['limited_data'],partial_season=p['partial_season'],pending_fixture_exclusions=[mid for mid in p['observed_match_ids'] if mid==3879594],withheld_metric_components=[dict(match_id=f['match_id'],attribute=a,reasons=m['reasons']) for f in fs[pid] for a,m in f['metrics'].items() if not m['supported']])
        comparisons.append(row)
        for f in fs[pid]:
            for a,m in f['metrics'].items():
                lineage.append(dict(player_id=pid,season=p['season_name'],position_group=p['comparison_group'],team=f['team'],competition=f['competition_name'],match_id=f['match_id'],attribute=a,**m))
        admissions.append(dict(player_id=pid,stages={k:json.loads(historical[pid][k]) for k in STAGES},ratings_v2=after))
    # Preserve public field shapes in an explicitly private, differently versioned
    # envelope; attach exact lineage separately rather than publishing it.
    candidate=copy.deepcopy(public)
    candidate.update(schema_version=VERSION,release='2015-16-v2-private-candidate-1',publication_authorized=False,production_ready=False,reference_fingerprint=REF_SHA,admission_version=ADMISSION_VERSION,baseline_sha=sha)
    for target in candidate['players']:
        pid=int(target['player_id']);p=byid[pid]
        target['ovr']=p['ovr'];target['coverage']=dict(supported_minutes=float(fraction(p['known_supported_minutes'])),observed_fixtures=len(p['observed_match_ids']))
        target['clubs']=[dict(name=c['team'],competition_name=c['competition_name']) for c in p['contexts']]
        for key in target['attributes']:
            a='progressive_passing' if key=='line_breaking_passes' else key;m=p['attributes'][a]
            target['attributes'][key]=dict(rating=m['experimental_rating'],percentile=m['percentile'],limited_data=p['limited_data'] or any('LIMITED DATA' in w for w in m['warnings']),missingness=list(dict.fromkeys(x for x in (m['score_reason'],m['measurement_reason']) if x)),warnings=m['warnings'])
        target['badge_eligible']=p['ovr']['eligible'] and not p['limited_data'] and all(not a['limited_data'] and a['rating'] is not None for a in target['attributes'].values())
    candidate['counts']['complete']=sum(p['ovr']['value'] is not None for p in players)
    candidate['counts']['partial']=691-candidate['counts']['complete']
    for rel in ['src/ratings_v2.py','scripts/reconstruct_ratings_v2.py','scripts/event_chronology_diagnostics.py','scripts/reconcile_event_chronology.py']:
        bind(ROOT/rel)
    candidate['source_fingerprint']=hashlib.sha256(json.dumps(receipts,sort_keys=True).encode()).hexdigest()
    candidate['policy_fingerprint']=hashlib.sha256(json.dumps(dict(reference=REF_SHA,formula='30/25/20/15/10 sorted clipped attributes',eligibility=public['eligibility_version'],admission=ADMISSION_VERSION),sort_keys=True).encode()).hexdigest()
    # Refit feasibility: corrected recipient candidates are evidence, not a
    # corrected full 2,514-candidate upstream cohort. Do not fit a mixed snapshot.
    membership=[]
    for group,pools in reference['pools'].items():
        for a,pool in pools.items():
            prospective={p['player_id'] for p in players if p['comparison_group']==group and p['attributes'][a]['experimental_reference_candidate']}
            for pid in sorted(set(pool['member_ids'])|prospective):
                membership.append(dict(position_group=group,attribute=a,player_id=pid,frozen_member=pid in pool['member_ids'],v2_frozen_member=pid in pool['member_ids'],corrected_published_candidate=pid in prospective,proposed_entering=pid not in pool['member_ids'] and pid in prospective,proposed_departing=pid in pool['member_ids'] and pid in byid and pid not in prospective,scenario_b='NOT FITTED: complete corrected upstream cohort and transfer membership decision required',frozen_n=pool['n'],frozen_mean=pool['mean'],frozen_sd=pool['sample_sd']))
    sensitivity={}
    for group in ('MID','CB'):
        selected=[p for p in players if p['comparison_group']==group and p['ovr']['eligible']]
        baseline_order=sorted(selected,key=lambda p:(-p['ovr']['value'],p['player_id']))
        base_rank={p['player_id']:i for i,p in enumerate(baseline_order,1)}
        scenarios={}
        for weights in [(25,25,20,15,15),(35,25,20,15,5),(20,20,20,20,20)]:
            vals={p['player_id']:float(sum(F(v)*F(w,100) for v,w in zip(sorted([m['experimental_rating'] for m in p['attributes'].values()],reverse=True),weights))) for p in selected}
            ordered=sorted(vals,key=lambda pid:(-vals[pid],pid));ranks={pid:i for i,pid in enumerate(ordered,1)}
            # Spearman uses average ranks in case alternative weights tie.
            def average_ranks(values):
                groups=defaultdict(list)
                for i,pid in enumerate(sorted(values,key=lambda k:(-values[k],k)),1):groups[values[pid]].append((pid,i))
                return {pid:statistics.mean(i for _,i in rows) for rows in groups.values() for pid,_ in rows}
            ar=average_ranks({p['player_id']:p['ovr']['value'] for p in selected});br=average_ranks(vals)
            reversals=sum((selected[i]['ovr']['value']-selected[j]['ovr']['value'])*(vals[selected[i]['player_id']]-vals[selected[j]['player_id']])<0 for i in range(len(selected)) for j in range(i))
            scenarios['/'.join(map(str,weights))]=dict(spearman=statistics.correlation([ar[k] for k in ar],[br[k] for k in ar]),pairwise_reversals=reversals,top10_retained=len(set(ordered[:10])&{p['player_id'] for p in baseline_order[:10]}),top20_retained=len(set(ordered[:20])&{p['player_id'] for p in baseline_order[:20]}),largest_movements=sorted([dict(player_id=pid,rank_delta=base_rank[pid]-ranks[pid]) for pid in ranks],key=lambda r:-abs(r['rank_delta']))[:10])
        sensitivity[group]=dict(eligible=len(selected),scenarios=scenarios,small_sample_exposure=[dict(player_id=p['player_id'],press_attempts=p['attributes']['press_resistance']['attempts'],supported_minutes=p['known_supported_minutes']) for p in selected if p['attributes']['press_resistance']['attempts']<80],bootstrap='NOT PERFORMED: match-cluster model and original coverage uncertainty remain; no narrow confidence interval inferred')
    summaries=dict(profiles=691,complete=candidate['counts']['complete'],missing_ovr=candidate['counts']['partial'],changed_attributes=sum(r['rating_changed'] for r in attrs),changed_ovrs=sum(r['v1_formula_b']!=r['v2_formula_b'] for r in comparisons),unchanged_ovrs=sum(r['v1_formula_b']==r['v2_formula_b'] for r in comparisons),newly_eligible=sum(not r['v1_eligibility'] and r['v2_eligibility'] for r in comparisons),newly_ineligible=sum(r['v1_eligibility'] and not r['v2_eligibility'] for r in comparisons),eligible={g:sum(p['comparison_group']==g and p['ovr']['eligible'] for p in players) for g in ('MID','CB')})
    dump('summary.json',summaries)
    dump('ratings-v2-candidate.private.json',candidate)
    dump('independent-verification.json',dict(status='PASS',checks=checks,frozen_and_historical_transfer_checks=frozen_transfer_checks,deterministic_repeat=True,reference_unchanged=True,external_outcome_validation=False,source_fact_status='HASH-VERIFIED REUSED, independently checked against freshly replayed originals'))
    dump('original-source-replay-summary.json',dict(status='FRESHLY RECOMPUTED',execution_baseline=sha,replay=replay,historical_comparison_baseline=replay['baseline'],retained_facts='HASH-VERIFIED REUSED; fresh UUID/admission/exposure comparison',scenario_b='BLOCKED: corrected full upstream reference cohort not available'))
    dump('source-uuid-conservation.json',dict(status='PASS',events=5436699,fixtures=1551,duplicate_uuids=0,checks=checks['uuid_actor_fixture_checks'],raw_uuid_retained=True))
    dump('formula-b-sensitivity.json',dict(private_research=True,adopted=False,selected_weights=[30,25,20,15,10],groups=sensitivity,split_half=split_half_review(players,fs,reference)))
    # The established proof contract represents exact Fraction clocks as
    # rational strings; original source clocks and UUIDs remain unchanged.
    dump('verified-measurement-corrections.json',json.loads(json.dumps(proofs,default=str)))
    dump('historical-diagnostic-receipt-differences.json',js(B5/'audit-output/recovery-helper-hardening/historical-diagnostic-receipt-differences.json'))
    for name,rows in [('correction-admission-ledger.jsonl',admissions),('attribute-source-lineage.jsonl',lineage)]:
        write_verified(out/name,(''.join(json.dumps(row,sort_keys=True,ensure_ascii=False)+'\n' for row in rows)).encode('utf8'))
    write_csv(out/'changed-metric-events.csv',changed)
    write_csv(out/'attribute-comparison.csv',attrs)
    for name in ['player-691-comparison.csv','formula-b-comparison.csv','ranking-comparison.csv','eligibility-comparison.csv','participation-and-exposure-comparison.csv']:
        write_csv(out/name,comparisons)
    write_csv(out/'reference-membership-comparison.csv',membership)
    write_csv(out/'unresolved-source-conflicts.csv',exceptions)
    write_csv(out/'outlier-review.csv',[dict(**r,review_reason='large score delta or sparse sample or retained exclusion',press_attempts=byid[r['player_id']]['attributes']['press_resistance']['attempts']) for r in comparisons if abs(r['delta_formula_b'] or 0)>=1 or byid[r['player_id']]['attributes']['press_resistance']['attempts'] is None or (byid[r['player_id']]['attributes']['press_resistance']['attempts'] or 0)<40])
    focused={
        'largest-positive-ovr':sorted([r for r in comparisons if (r['delta_formula_b'] or 0)>0],key=lambda r:-r['delta_formula_b'])[:20],
        'largest-negative-ovr':sorted([r for r in comparisons if (r['delta_formula_b'] or 0)<0],key=lambda r:r['delta_formula_b'])[:20],
        'largest-positive-rank':sorted([r for r in comparisons if (r['all_complete_rank_delta'] or 0)>0],key=lambda r:-r['all_complete_rank_delta'])[:20],
        'largest-negative-rank':sorted([r for r in comparisons if (r['all_complete_rank_delta'] or 0)<0],key=lambda r:r['all_complete_rank_delta'])[:20],
        'largest-positive-eligible-rank':sorted([r for r in comparisons if (r['rank_delta'] or 0)>0],key=lambda r:-r['rank_delta'])[:20],
        'largest-negative-eligible-rank':sorted([r for r in comparisons if (r['rank_delta'] or 0)<0],key=lambda r:r['rank_delta'])[:20],
        'newly-eligible':[r for r in comparisons if not r['v1_eligibility'] and r['v2_eligibility']],
        'newly-ineligible':[r for r in comparisons if r['v1_eligibility'] and not r['v2_eligibility']],
        'remaining-limited-data':[r for r in comparisons if byid[r['player_id']]['limited_data']],
        'withheld-components':[dict(player_id=p['player_id'],attribute=a,excluded=m['excluded_appearances']) for p in players for a,m in p['attributes'].items() if m['excluded_appearances']],
        'top10-top20':[r for r in comparisons if any(rank is not None and rank<=20 for rank in (r['v1_rank'],r['v2_rank'],r['v1_all_complete_rank'],r['v2_all_complete_rank']))]}
    for name,rows in focused.items():write_csv(out/(name+'.csv'),rows)
    policies=[('Frozen reference reuse','APPROVED / ALREADY IMPLEMENTED','frozen-reference.json','Reuse exact membership, means, SDs and semantic fingerprint','No decision required for A; refit remains separate'),('Reference refit','UNRESOLVED SOURCE OR POLICY ISSUE','reference-membership-comparison.csv','No mixed corrected/uncorrected upstream cohort fit','Review full corrected upstream cohort, transfer membership and proposed rules'),('Source coverage / incomplete seasons','APPROVED / ALREADY IMPLEMENTED','docs/data-correction-roadmap.md; original fixture inventories','Observed scope only; Bundesliga limited-data exclusion','Additional source acquisition requires its own scope'),('Chronology component admission','APPROVED / ALREADY IMPLEMENTED','docs/event-chronology-reconciliation-report.md; verified-measurement-corrections.json','Withhold full affected component; preserve raw actions','Remaining source contradictions need provider resolution'),('Source-name consistency','APPROVED / ALREADY IMPLEMENTED','docs/identity-source-reconciliation-report.md; 3054/3754296','Keep conservative restriction and authoritative ID','Any alias admission requires independent review'),('Pending fixture','UNRESOLVED SOURCE OR POLICY ISSUE','3879594; docs/data-correction-roadmap.md','Exclude pending contribution','Approve source-scope admission only after evidence review'),('Transfers','APPROVED / ALREADY IMPLEMENTED','src/private_five_attribute.py; transfer-policy-comparison.jsonl','Pool verified season facts once; frozen membership retained','No new reference-context choice'),('Limited-data rankings','APPROVED / ALREADY IMPLEMENTED','src/private_ovr_formula_c.py::exclusion_reasons','Computable score does not confer rank','No promotion authorized'),('Pressure sample','APPROVED / ALREADY IMPLEMENTED','src/private_five_attribute.py::POLICY','40 for reference/strict eligibility; retain sparse observed projections','No threshold change'),('Publication','SUPPORTED BY EVIDENCE BUT NOT YET AUTHORIZED','user reconstruction request; candidate envelope','Publication explicitly false','Team numerical review and separate release approval')]
    write_csv(out/'policy-decision-register.csv',[dict(item=a,classification=b,evidence=c,preserved_rule=d,smallest_decision=e) for a,b,c,d,e in policies])
    for folder in ['src','scripts','tests','docs']:
        for path in (ROOT/folder).glob('*.py' if folder!='docs' else '*report.md'):bind(path)
    for path in [ROOT/'README.md',ROOT/'.gitignore',ROOT.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit/docs/data-correction-roadmap.md',Path('C:/Users/Ayush/.codex/worktrees/coverage-audit/Soccer-Impact-Engine-Index/docs/identity-integrity-audit-2026-11-01.md')]:bind(path)
    worktrees=subprocess.check_output(['git','worktree','list','--porcelain'],cwd=ROOT,text=True)
    import numpy as np
    import pandas as pd
    runtime=dict(python=sys.version,pandas=pd.__version__,numpy=np.__version__,sqlite=sqlite3.sqlite_version,node=subprocess.check_output(['node','--version'],text=True).strip(),npm=subprocess.check_output(['npm.cmd','--version'],text=True).strip())
    dump('baseline-and-input-hashes.json',dict(baseline=sha,origin_main=sha,branch='ratings-v2-reconstruction',worktree=str(ROOT),runtime=runtime,retained_worktree_git_baselines=worktrees,public_v1_sha256=PUBLIC_SHA,reference_semantic_sha256=REF_SHA,inputs=receipts))
    inventory=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=file_sha(p)) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='artifact-inventory.json']
    dump('artifact-inventory.json',inventory)
    print(json.dumps(summaries,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',default='audit-output/ratings-v2')
    parser.add_argument('--numerical-only',action='store_true',help='retain an independently verified numerical checkpoint before full-source finalization')
    args=parser.parse_args()
    build(args.output,numerical_only=args.numerical_only)
