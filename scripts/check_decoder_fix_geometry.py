"""Additional independent geometry and canonical identity checks on pinned bytes."""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from scripts import decoder_fix_independent as oracle
from src.statsbomb_participation import SourceDocument, adapt_match


def normalized(intervals,bounds):
    parts=defaultdict(list)
    for a,b in intervals:
        for p in range(a[0],b[0]+1):
            lo=a[1] if p==a[0] else bounds[p][0]
            hi=b[1] if p==b[0] else bounds[p][1]
            if lo<hi:parts[p].append((lo,hi))
    out=[]
    for p,rows in sorted(parts.items()):
        merged=[]
        for lo,hi in sorted(rows):
            if merged and lo<=merged[-1][1]:merged[-1]=(merged[-1][0],max(hi,merged[-1][1]))
            else:merged.append((lo,hi))
        out += [(p,lo,hi) for lo,hi in merged]
    return out


def main(audit,source,output):
    import csv
    apps=list(csv.DictReader((audit/'audit-output/full-player-audit/appearances.csv').open(encoding='utf-8-sig')))
    public=json.loads(Path('frontend/public/data/player-ratings-2015-16-v1.json').read_text())['players']
    bymatch=defaultdict(list);names=defaultdict(set);checks=0;hashes={};details=[]
    additions=defaultdict(lambda:defaultdict(F))
    for a in apps:bymatch[int(a['match_id'])].append(a)
    def read(binding):
        raw=Path(binding['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==binding['sha256']
        hashes[binding['path']]=binding['sha256'];return raw
    for n,(mid,aa) in enumerate(sorted(bymatch.items()),1):
        ev=json.loads(aa[0]['evidence']);report=json.loads(read({'path':ev['report_path'],'sha256':ev['report_sha256']}))
        eb,lb,fb=report['artifacts']['events'],report['artifacts']['lineups'],report['fixture_document']
        raw=[read(b) for b in (fb,lb,eb)];fixtures,lineups,events=map(json.loads,raw)
        roster={(t['team_id'],p['player_id']):p for t in lineups for p in t['lineup']}
        for (tid,pid),p in roster.items():names[pid].add(p['player_name'])
        bounds,issues,_=oracle.boundaries(events,{t['team_id'] for t in lineups})
        new=adapt_match(mid,*(SourceDocument(r,b['source_reference'],'pinned-original') for r,b in zip(raw,(fb,lb,eb))),clock_document_reference='Pinned original period-local clocks; 0/45 display offsets')
        rr={r.context.player_id:r for r in new.validate()}
        transitions=[e for e in events if oracle.typ(e) in ('Starting XI','Tactical Shift','Substitution','Player On','Player Off') or oracle.card(e) in ('Red Card','Second Yellow')]
        for a in aa:
            pid,tid=int(a['player_id']),int(a['team_id']);r=rr[pid]
            if r.elapsed_seconds is None:continue
            o=oracle.reconstruct(pid,tid,roster[tid,pid],transitions,bounds,issues)
            intervals=[((s.start.period,F(s.start.seconds)),(s.end.period,F(s.end.seconds))) for s in r.observations]
            assert normalized(intervals,bounds)==normalized(o['intervals'],bounds),(pid,mid)
            checks+=1
            if a['current_status']!='STRUCTURALLY_VALID':
                details.append(dict(player_id=pid,match_id=mid,production_intervals=intervals,event_state_intervals=o['intervals'],exact_union=normalized(intervals,bounds)))
                for allocation in r.position_allocation:additions[pid][allocation.position]+=allocation.elapsed_seconds
        if n%100==0:print(f'Geometry verified {n}/{len(bymatch)} fixtures',flush=True)
    assert len({p['player_id'] for p in public})==len(public)==691
    for p in public:assert p['name'] in names[int(p['player_id'])],p['player_id']
    from scripts.verify_bundesliga_readiness import position_group
    canonical_path=source/'data/derived/fifth-attribute-private-v1/player-measurements.jsonl'
    canonical_raw=canonical_path.read_bytes();hashes[str(canonical_path)]=hashlib.sha256(canonical_raw).hexdigest()
    canonical={p['player_id']:p for p in map(json.loads,canonical_raw.decode().splitlines())}
    group_changes=[];fine_changes=[]
    for p in public:
        pid=int(p['player_id']);old=canonical[pid];groups=defaultdict(F)
        for position,seconds in old['position_seconds'].items():groups[position_group(position)]+=oracle.rational(seconds)
        for position,seconds in additions[pid].items():groups[position_group(position)]+=seconds
        high=max(groups.values());dominant=sorted(k for k,v in groups.items() if v==high and high>0)
        group=('MID' if dominant[0] in ('DM','CM') else dominant[0]) if len(dominant)==1 else None
        if dominant!=old['dominant_fine_groups']:fine_changes.append(dict(player_id=pid,before=old['dominant_fine_groups'],after=dominant))
        if group!=old['comparison_group']:group_changes.append(dict(player_id=pid,before=old['comparison_group'],after=group))
    assert not group_changes,group_changes
    result=dict(accepted_exact_interval_unions_checked=checks,canonical_id_name_pairs_verified=len(public),fixture_count=len(bymatch),recovered_interval_details=details,input_hashes=hashes,comparison_group_changes=group_changes,dominant_fine_group_changes=fine_changes)
    output.write_text(json.dumps(result,indent=2,default=str)+'\n',encoding='utf8')
    print(f'{checks} exact interval unions and 691 canonical identities verified',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.audit_root,a.source_root,a.output)
