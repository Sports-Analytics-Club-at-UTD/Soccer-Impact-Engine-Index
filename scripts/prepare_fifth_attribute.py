"""Offline Joseph Level A integration over sealed evidence; no reconstruction.

Writes exclusively to a new private directory. Never writes Parquets or frontend.
Run: python -B -m scripts.prepare_fifth_attribute --output data/derived/fifth-attribute-private-v1
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
from itertools import groupby
import json
from pathlib import Path

import pandas as pd

from src.fifth_attribute import VERSION, NOTICE, combine_observations, private_preview
from src.passing import _prepare, _apply_reference, calibrate_difficulty
from src.metrics.progressive_passes import flag_progressive
from src.source_reconstruction import event_within_exposure, rational

FOUR = Path('data/derived/phase3-step2-source-reconstruction-2026-10-27')
CHECKS = Path('data/derived/phase3-step3-independent-verified-2026-10-28')
BUNDES = Path('data/derived/bundesliga-targeted-2026-10-29')
PENDING = {3879594}


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def records(path):
    with Path(path).open(encoding='utf8') as f:
        for s in f:
            yield json.loads(s)


def read_bound(ref):
    if sha(ref['path']) != ref['sha256']:
        raise ValueError('source binding changed: '+ref['path'])
    return json.loads(Path(ref['path']).read_text(encoding='utf8'))


def seal(root, names):
    m = json.loads((root/'run-manifest.json').read_text())
    for name in names:
        expected = next(a['sha256'] for a in m['artifacts'] if a['path'] == name)
        if sha(root/name) != expected:
            raise ValueError('sealed input changed: '+name)
    return dict(path=str(root/'run-manifest.json'),sha256=sha(root/'run-manifest.json'),
        artifacts={n:sha(root/n) for n in names})


def project(events, mid, comp):
    """Original pass fields for Joseph's existing helpers; no inferred outcomes."""
    rows=[]
    for e in events:
        if e['type']['name'] != 'Pass':
            continue
        p=e['pass'];actor=e.get('player',{})
        rows.append(dict(id=e['id'],match_id=mid,competition_name=comp,season_name='2015/2016',
            type='Pass',team=e['team']['name'],team_id=e['team']['id'],player=actor.get('name'),player_id=actor.get('id'),
            location=e.get('location'),pass_end_location=p.get('end_location'),
            pass_outcome=p.get('outcome',{}).get('name'),pass_type=p.get('type',{}).get('name'),pass_length=p.get('length')))
    return pd.DataFrame(rows)


def match_sources():
    for root, name, refkey in [(CHECKS,'match-independent-checks.jsonl','review_reference'),
                                (BUNDES,'match-checks.jsonl','report_reference')]:
        for c in records(root/name):
            report=read_bound(c[refkey])
            yield c['match_id'], report, root == BUNDES


def batches():
    n=0
    for mid,report,bundes in match_sources():
        if bundes or mid in PENDING:
            continue
        # These exact bytes already passed the sealed independent schema checks.
        # Verify their hash and parse once; do not rerun source reconstruction.
        events=read_bound(report['artifacts']['events'])
        n+=1
        if n%200==0:print('Calibration fixtures:',n,flush=True)
        yield project(events,mid,report['competition_name'])


def grouped(path):
    return iter((mid,list(rs)) for mid,rs in groupby(records(path),lambda r:r['match_id']))


def build(output):
    output=Path(output)
    if output.exists():
        raise ValueError('new exclusive private output directory required')
    inputs=[seal(FOUR,['appearance-ledger.jsonl','match-component-measurements.jsonl']),
            seal(CHECKS,['appearance-independent-checks.jsonl','match-independent-checks.jsonl']),
            seal(BUNDES,['appearances.jsonl','match-measurements.jsonl','match-checks.jsonl'])]
    print('Calibrating all measurable open-play passes in eligible four-league observed fixtures',flush=True)
    reference=calibrate_difficulty(batches(),scope=VERSION+': all original four-league 2015/16 observed provider fixtures except pending 3879594; all players and roles',complete=True)
    # complete means all passes in this exact named observed cohort, never a
    # claim of a complete league season or production certification.
    print('Calibration measured passes:',reference.accounting['measurable'],flush=True)
    ag=grouped(FOUR/'appearance-ledger.jsonl'); mg=grouped(FOUR/'match-component-measurements.jsonl')
    ig=grouped(CHECKS/'appearance-independent-checks.jsonl')
    bg=grouped(BUNDES/'appearances.jsonl'); bm=grouped(BUNDES/'match-measurements.jsonl')
    observations=[];ledger=[];fixtures=Counter();seen_events=set();accounting=Counter()
    for number,(mid,report,bundes) in enumerate(match_sources(),1):
        am,apps=next(bg if bundes else ag);mm,metrics=next(bm if bundes else mg)
        if am != mid or mm != mid:
            raise ValueError('exact fixture ledger alignment failed')
        independent={}
        if not bundes:
            im,checks=next(ig)
            if im != mid:raise ValueError('independent fixture mismatch')
            independent={(r['team_id'],r['player_id']):r for r in checks}
        if mid in PENDING:
            # Retain pending appearances as explicit missingness, never silently
            # add the undelivered fixture to reference scope.
            events=[];passes=pd.DataFrame();summary={}
        else:
            events=read_bound(report['artifacts']['events'])
            ids=[e['id'] for e in events]
            if len(set(ids))!=len(ids) or seen_events.intersection(ids):
                raise ValueError('duplicate original event UUID across fixtures')
            seen_events.update(ids)
            projected=project(events,mid,report['competition_name'])
            passes,_,summary=_prepare(projected)
            passes['team_id']=passes.id.map(projected.set_index('id').team_id)
            passes=flag_progressive(passes.assign(difficulty=0.0)) if bundes else _apply_reference(passes,reference)
        fixtures[report['competition_name']]+=1
        accounting.update(summary)
        raw={e['id']:e for e in events};by_actor={}
        if not passes.empty:
            by_actor={k:g for k,g in passes.groupby(['team_id','player_id'])}
        metricmap={(r['team_id'],r['player_id']):r for r in metrics}
        active={(a['team_id'],a['player_id']):a for a in apps if a['active_appearance']}
        if set(by_actor)-set(active):raise ValueError('original passes lack active canonical identity')
        for k,a in sorted(active.items()):
            reasons=[];p=by_actor.get(k);m=metricmap[k]
            if mid in PENDING:reasons.append('PENDING_DELIVERED_FIXTURE_SCOPE')
            if a['participation_status']!='STRUCTURALLY_VALID':reasons.append('UNSUPPORTED_EXPOSURE')
            if m['progressive_missing_geometry']:reasons.append('MISSING_GEOMETRY')
            if p is not None:
                if not p.player.eq(a['player_name_raw']).all():raise ValueError('canonical ID/name disagreement')
                if any(not event_within_exposure(raw[uid],a) for uid in p.id):reasons.append('PASS_OUTSIDE_SUPPORTED_EXPOSURE')
                # Invalid bounds cannot quietly become measurable zeroes.
                if not (p.x0.between(0,120)&p.x1.between(0,120)&p.y0.between(0,80)&p.y1.between(0,80)).all():
                    reasons.append('OUT_OF_PITCH_GEOMETRY')
            counts={}
            for name,col in [('progressive_attempts','prog_attempt'),('progressive_passes','progressive'),('progressive_third_crossings','third_cross')]:
                uids=sorted(p.loc[p[col],'id'].tolist()) if p is not None else []
                c=m['components'][name]
                if mid not in PENDING and (uids!=sorted(c['event_ids']) or len(uids)!=c['count']):
                    raise ValueError('Joseph/sealed UUID count parity failed')
                if not bundes:
                    ic=independent[k]
                    if ic['actor_findings']:reasons.append('ACTOR_EVIDENCE_CONFLICT')
                    if ic['independent_seconds']!=a['validated_elapsed_seconds']:
                        raise ValueError('independent minute disagreement')
                    if mid not in PENDING and ic['components'][name]['count']!=len(uids):
                        raise ValueError('independent progressive count disagreement')
                counts[{'prog_attempt':'prog_attempts','progressive':'prog_passes','third_cross':'third_cross'}[col]]=c['count'] if mid in PENDING else len(uids)
            measured=None if mid in PENDING else 0 if p is None else len(p)
            seconds=a['validated_elapsed_seconds']
            if seconds is None or seconds['numerator']<=0:reasons.append('MISSING_OR_ZERO_EXPOSURE')
            observation=dict(player_id=a['player_id'],season_name=a['season_name'],name=a['player_name_raw'],
                team=a['team'],competition_name=a['competition_name'],match_id=mid,
                seconds=seconds,position_seconds={v['position']:v['elapsed_seconds'] for v in (a['position_allocation'] or [])},
                reasons=sorted(set(reasons)),**counts,measured_passes=measured,
                value_sum=None if bundes or mid in PENDING else float(p.pass_value.sum()) if p is not None else 0.0)
            observations.append(observation)
        ledger.append(dict(match_id=mid,competition_name=report['competition_name'],
            events_sha256=report['artifacts']['events']['sha256'],
            original_events=None if mid in PENDING else len(events),measured_passes=None if mid in PENDING else 0 if passes.empty else len(passes),
            progressive_passes=None if mid in PENDING else 0 if passes.empty else int(passes.progressive.sum()),
            pending_scope=mid in PENDING,uuid_and_count_parity=True))
        if number%200==0:print('Integrated fixtures:',number,flush=True)
    if any(next(g,None) is not None for g in (ag,mg,ig,bg,bm)):
        raise ValueError('unexpected extra sealed fixture')
    players=combine_observations(observations);preview=private_preview(players)
    summary=dict(schema_version=VERSION,notice=NOTICE,method_contributor='Joseph',
        headline='Successful progressive passes per 90',fixtures=dict(fixtures),
        calibration=dict(scope=reference.scope,observed_cohort_complete=True,full_league_season_certified=False,
            accounting=reference.accounting,fixture_counts={c:n for (c,s),n in reference.matches.items()},
            bundesliga='NOT CALIBRATED: incomplete league-season observation pool'),
        unique_players=len(players),supported_players=sum(p['prog_passes_p90'] is not None for p in players),
        fully_supported_observed_players=sum(p['all_observed_exposure_supported'] for p in players),
        groups={g:dict(observed=sum(p['comparison_group']==g for p in players),
            supported=sum(p['comparison_group']==g and p['prog_passes_p90'] is not None for p in players),
            four_league_supported=sum(p['comparison_group']==g and not p['limited_data'] and p['prog_passes_p90'] is not None for p in players),
            private_reference_candidates=preview['pools'][g]['n'],
            bundesliga_supported=sum(p['comparison_group']==g and p['limited_data'] and p['prog_passes_p90'] is not None for p in players)) for g in ('MID','CB')},
        bundesliga_players=sum(p['limited_data'] for p in players),
        bundesliga_supported=sum(p['limited_data'] and p['prog_passes_p90'] is not None for p in players),
        supported_appearances=sum(not r['reasons'] for r in observations),
        missing_appearance_reasons=dict(Counter(v for r in observations for v in r['reasons'])),
        production_ratings_generated=0,publication_authorized=False)
    output.mkdir(parents=True,exist_ok=False)
    def write(name,value):
        with (output/name).open('x',encoding='utf8',newline='\n') as f:
            json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    for name,rows in [('player-measurements.jsonl',players),('match-observations.jsonl',observations),('fixture-audit.jsonl',ledger)]:
        with (output/name).open('x',encoding='utf8',newline='\n') as f:
            for r in rows:f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n')
    write('summary.json',summary);write('PRIVATE-EXPERIMENTAL-preview.json',preview)
    reference.cells.to_csv(output/'difficulty-calibration.csv',index=False,mode='x')
    write('manifest.json',dict(schema_version=VERSION,notice=NOTICE,inputs=inputs,
        implementation={p:sha(p) for p in ['src/fifth_attribute.py','scripts/prepare_fifth_attribute.py','src/passing.py','src/metrics/progressive_passes.py']},
        artifacts={p.name:sha(p) for p in sorted(output.iterdir())},publication_authorized=False))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    build(parser.parse_args().output)
