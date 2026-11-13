"""Independent arithmetic, scope, cohort and byte-integrity checks for a rebuild.

Does not import the rebuilt aggregator, eligibility predicate or scorer.
"""
import argparse
from bisect import bisect_left, bisect_right
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

ATTRIBUTES=('tackles','interceptions','recoveries','press_resistance','progressive_passing')
FOUR={'Premier League','La Liga','Serie A','Ligue 1'}


def exact(value):
    return None if value is None else Fraction(value['numerator'],value['denominator'])


def sha(path):
    with Path(path).open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()


def verify(directory):
    checks=0
    def check(condition,message):
        nonlocal checks
        checks+=1
        if not condition: raise ValueError(message)
    def near(left,right,message):
        check(math.isclose(left,right,rel_tol=1e-12,abs_tol=1e-12),message)
    def read(name):return json.loads((directory/name).read_text(encoding='utf8'))
    manifest=read('manifest.json');root=Path(__file__).resolve().parents[1]
    for name,expected in manifest['artifacts'].items():check(sha(directory/name)==expected,'artifact changed: '+name)
    for name,expected in manifest['implementation'].items():check(sha(root/name)==expected,'implementation changed: '+name)
    receipts=read('input-hashes.json')
    for path,expected in receipts.items():check(sha(path)==expected,'source changed: '+path)
    payload=json.dumps(receipts,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    check(hashlib.sha256(payload).hexdigest()==manifest['input_binding'],'input binding')
    reference=read('frozen-reference.json');body={k:v for k,v in reference.items() if k!='sha256'}
    check(hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==reference['sha256'],'reference binding')
    by_player=defaultdict(list);nonappearances=set();matches=set();metric_ids={a:set() for a in ATTRIBUTES};attempt_ids=set()
    with (directory/'source-replay.jsonl').open(encoding='utf8') as handle:
        for line in handle:
            fixture=json.loads(line);mid=fixture['match_id'];check(mid not in matches,'duplicate fixture');matches.add(mid)
            for bench in fixture['nonappearances']:nonappearances.add((bench['player_id'],mid))
            for row in fixture['appearances']:
                check(row['season']=='2015/2016','wrong source season')
                check((row['player_id'],mid) not in nonappearances,'bench counted as appearance')
                check(mid not in {r['match_id'] for r in by_player[row['player_id']]},'duplicate actor/fixture')
                by_player[row['player_id']].append(row)
                for a,m in row['metrics'].items():
                    check(m['included']==(not m['reasons']),'inclusion reasons')
                    check(not metric_ids[a].intersection(m['numerator_ids']),'duplicate metric UUID')
                    check(len(set(m['numerator_ids']))==len(m['numerator_ids']),'repeated numerator UUID')
                    metric_ids[a].update(m['numerator_ids'])
                    if a=='press_resistance':
                        check(set(m['numerator_ids'])<=set(m['denominator_ids']),'successes outside attempts')
                        check(not attempt_ids.intersection(m['denominator_ids']),'duplicate attempt UUID')
                        attempt_ids.update(m['denominator_ids'])
                        if row['chronology_reasons']:check(not m['included'],'chronology conflict retained')
                    elif m['included']:check(row['seconds'] is not None,'per90 included without minutes')
    players=read('players.json');public=read('public-ratings.json');public_by_id={int(p['player_id']):p for p in public['players']}
    recovery_release=public['schema_version']=='soccer-public-ratings/v3'
    recovery_counts=None
    if recovery_release:
        from scripts.verify_appearance_recovery import verify_recoveries
        recovery_counts=verify_recoveries(directory,check)
    check(len(players)==len(public_by_id)==691,'player population')
    expected_eligible={g:[] for g in ('MID','CB')}
    for p in players:
        pid=p['player_id'];rows=sorted(by_player[pid],key=lambda r:r['match_id']);pub=public_by_id[pid]
        check(p['observed_match_ids']==[r['match_id'] for r in rows],'observed scope')
        minutes=sum((exact(r['seconds']) for r in rows if r['seconds'] is not None),Fraction())/60
        check(minutes==exact(p['known_supported_minutes']),'supported-minute subtotal')
        near(float(minutes),pub['coverage']['supported_minutes'],'public minutes')
        check(pub['coverage']['supported_fixtures']==sum(r['seconds'] is not None for r in rows),'supported match display')
        check(pub['coverage']['unresolved_fixtures']+pub['coverage']['supported_fixtures']==pub['coverage']['observed_fixtures']==len(rows),'coverage totals')
        if recovery_release:
            check(pub['coverage']['partial_fixtures']==sum(bool(r.get('exposure_recovery',{}).get('seconds')) and not r['exposure_recovery']['complete'] for r in rows),'partial-match disclosure')
        reasons=[];competitions={r['competition'] for r in rows}
        if p['comparison_group'] not in ('MID','CB'):reasons.append('UNSUPPORTED_POSITION')
        if not competitions or not competitions<=FOUR:reasons.append('BUNDESLIGA_CONTRIBUTION' if '1. Bundesliga' in competitions else 'NOT_FOUR_LEAGUE_ONLY')
        if minutes<900:reasons.append('BELOW_900_VERIFIED_SEASON_MINUTES')
        for a in ATTRIBUTES:
            m=p['attributes'][a];good=[r for r in rows if r['metrics'][a]['included']]
            numerator=sum(len(r['metrics'][a]['numerator_ids']) for r in good)
            duration=sum((exact(r['seconds']) for r in good if r['seconds'] is not None),Fraction())/60
            attempts=sum(len(r['metrics'][a]['denominator_ids']) for r in good) if a=='press_resistance' else None
            value=(Fraction(100*numerator,attempts) if attempts else None) if a=='press_resistance' else (Fraction(90*numerator)/duration if duration else None)
            check((m['numerator'],m['attempts'],exact(m['supported_minutes']),exact(m['exact_value']))==(numerator,attempts,duration,value),'exact measurement mismatch')
            check(m['numerator_match_ids']==m['denominator_match_ids']==[r['match_id'] for r in good],'numerator/denominator scope')
            check(m['excluded_appearances']==[dict(match_id=r['match_id'],reasons=r['metrics'][a]['reasons']) for r in rows if not r['metrics'][a]['included']],'excluded scope')
            if value is None:reasons.append(a+':MISSING_MEASUREMENT_DENOMINATOR')
            if a!='press_resistance' and duration<900:reasons.append(a+':BELOW_900_SUPPORTED_METRIC_MINUTES')
            if a=='press_resistance' and attempts<40:reasons.append(a+':BELOW_40_SUPPORTED_ATTEMPTS')
            c=pub['attributes']['line_breaking_passes' if a=='progressive_passing' else a]['coverage']
            check(c['supported_fixtures']==len(good) and c['excluded_fixtures']==len(rows)-len(good) and c['pressure_attempts']==attempts,'public metric coverage')
            near(c['supported_minutes'],float(duration),'public metric minutes')
            if recovery_release:
                check(c['partial_fixtures']==(sum(bool(r.get('exposure_recovery',{}).get('seconds')) and not r['exposure_recovery']['complete'] for r in good) if a!='press_resistance' else 0),'partial metric scope')
        check(reasons==p['exclusion_reasons']==pub['ovr']['exclusion_reasons'],'independent eligibility reasons')
        check(p['eligible']==pub['ovr']['eligible']==pub['badge_eligible']==(not reasons),'eligibility/badge decision')
        if not reasons:expected_eligible[p['comparison_group']].append(pid)
    for group in ('MID','CB'):
        members=sorted((p for p in players if p['player_id'] in expected_eligible[group]),key=lambda p:p['player_id'])
        for a,pool in reference['pools'][group].items():
            check(pool['member_ids']==sorted(expected_eligible[group]),'common eligible reference cohort')
            xs=[exact(p['attributes'][a]['exact_value']) for p in members]
            check(pool['exact_values']==[p['attributes'][a]['exact_value'] for p in members] and pool['n']==len(xs),'reference measurements')
            mean=sum(xs,Fraction())/len(xs);variance=sum(((x-mean)**2 for x in xs),Fraction())/(len(xs)-1)
            near(pool['mean'],float(mean),'independent reference mean');near(pool['sample_sd'],math.sqrt(float(variance)),'independent sample SD')
    for p in players:
        pub=public_by_id[p['player_id']];values=[]
        for a,m in p['attributes'].items():
            output=pub['attributes']['line_breaking_passes' if a=='progressive_passing' else a]
            if m['exact_value'] is None:
                check(m['rating'] is output['rating'] is None and m['percentile'] is None,'missing measurement scored')
                values.append(None);continue
            pool=reference['pools'][p['comparison_group']][a];x=exact(m['exact_value'])
            rating=min(99.,max(1.,65+10*(float(x)-pool['mean'])/pool['sample_sd']))
            xs=sorted(exact(v) for v in pool['exact_values']);lo,hi=bisect_left(xs,x),bisect_right(xs,x)
            pct=100*((lo+1+hi)/2 if lo!=hi else lo)/len(xs)
            near(m['rating'],rating,'rating');near(output['rating'],rating,'public rating')
            near(m['percentile'],pct,'percentile');near(output['percentile'],pct,'public percentile');values.append(rating)
        overall=None if None in values else sum(v*w for v,w in zip(sorted(values,reverse=True),(6,5,4,3,2)))/20
        if overall is None:check(pub['ovr']['value'] is p['overall'] is None,'missing overall')
        else:near(pub['ovr']['value'],overall,'Formula B');near(p['overall'],overall,'private Formula B')
    # Explicit regression receipts for the originally investigated cases.
    busquets=public_by_id[5203];ramos=public_by_id[5201]
    check(busquets['ovr']['eligible'] and ramos['ovr']['eligible'],'Busquets/Ramos not accepted')
    check(busquets['coverage']['supported_fixtures']==(35 if recovery_release else 34) and busquets['coverage']['observed_fixtures']==35,'Busquets scope changed unexpectedly')
    if recovery_release:
        check(busquets['coverage']['partial_fixtures']==1 and busquets['attributes']['press_resistance']['coverage']['pressure_attempts']==357,'Busquets partial half or pressure changed')
    check(ramos['coverage']['supported_fixtures']==23,'Ramos dismissal coverage')
    weber=next(r for r in by_player[7435] if r['match_id']==3900512)
    check(not weber['metrics']['press_resistance']['included'] and len(weber['metrics']['press_resistance']['denominator_ids'])==4,'Weber fixture ratio not wholly excluded')
    check((26023,3825670) in nonappearances and all(r['match_id']!=3825670 for r in by_player[26023]),'Juanfran bench appearance retained')
    check(all(not r['identity_reasons'] for r in by_player[3054]),'Fernandinho alias not resolved')
    result=dict(status='PASS',checks=checks,players=len(players),fixtures=len(matches),input_files=len(receipts),
        manifest_sha256=sha(directory/'manifest.json'),public_sha256=sha(directory/'public-ratings.json'),
        verifier_sha256=sha(Path(__file__)),
        eligible=sum(p['eligible'] for p in players),reference_sha256=reference['sha256'],recovery_counts=recovery_counts,
        assertions=['byte integrity','source UUID conservation','exact metric denominators','common eligible reference cohorts',
            'independent reference statistics','normalization and percentiles','Formula B','public coverage and eligibility','named-player regressions'])
    with (directory/'verification.json').open('x',encoding='utf8') as handle:json.dump(result,handle,indent=2)
    print(json.dumps(result,indent=2));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    verify(parser.parse_args().directory.resolve())
