"""Independently identify the ten proposed entries from retained original bytes.

No production adapter/decision imports. Event state and raw lineup endpoints
remain separate reconstructions, with exact rational clocks and stable IDs.
"""
import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from scripts import decoder_fix_independent as raw
from scripts import off_field_card_independent as independent


def main():
    root=Path.cwd();prior=root.parent/'Soccer-Impact-Engine-Index-source-evidence-reconciliation/audit-output/source-reconciliation'
    out=root/'audit-output/entry-independent-source-checks.json'
    if out.exists():raise ValueError('Preserve completed independent evidence')
    receipts={}
    def read(path,expected=None):
        p=Path(path);b=p.read_bytes();h=hashlib.sha256(b).hexdigest()
        if expected:assert h==expected,str(p)
        receipts[str(p.resolve())]=dict(sha256=h,bytes=len(b));return b
    proposals=list(csv.DictReader(read(prior/'recoverable-appearances.csv').decode('utf-8-sig').splitlines()))
    history=list(csv.DictReader(read(root.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit/appearances.csv').decode('utf-8-sig').splitlines()))
    leads={int(a['match_id']):json.loads(a['evidence']) for a in history}
    results=[]
    for row in proposals:
        if row['classification']!='B':continue
        pid,mid=int(row['player_id']),int(row['match_id']);lead=leads[mid]
        report=json.loads(read(lead['report_path'],lead['report_sha256']))
        fb,lb,eb=report['fixture_document'],report['artifacts']['lineups'],report['artifacts']['events']
        fixtures,lineups,events=[json.loads(read(b['path'],b['sha256'])) for b in (fb,lb,eb)]
        fixture=next(f for f in fixtures if f['match_id']==mid)
        roster=[(t,p) for t in lineups for p in t['lineup'] if p['player_id']==pid]
        assert len(roster)==1
        team,player=roster[0];tid=team['team_id']
        assert tid in (fixture['home_team']['home_team_id'],fixture['away_team']['away_team_id'])
        positions=player['positions'];first=positions[0]
        assert first['start_reason']=='Tactical Shift'
        member=lambda e:[x for x in e.get('tactics',{}).get('lineup',[]) if x['player']['id']==pid]
        team_events=[e for e in events if e['team']['id']==tid]
        entries=[];shifts=[]
        for e in team_events:
            if raw.typ(e)=='Starting XI' and member(e):entries.append(e)
            if raw.typ(e)=='Substitution' and e['substitution']['replacement']['id']==pid:entries.append(e)
            if raw.typ(e)=='Tactical Shift' and member(e) and e['period']==first['from_period']:
                m,s=map(int,first['from'].split(':'))
                if (e['minute'],e['second'])==(m,s):shifts.append(e)
        assert len(entries)==len(shifts)==1
        entry,shift=entries[0],shifts[0]
        assert raw.clock(entry)==raw.clock(shift)
        expected={'id':first['position_id'],'name':first['position']}
        assert member(shift)[0]['position']==expected
        if raw.typ(entry)=='Starting XI':
            assert raw.clock(entry)==(1,Fraction(0)) and member(entry)[0]['position']==expected
        else:assert entry['substitution']['replacement']=={'id':pid,'name':player['player_name']}
        bounds,issues,boundary_ids=raw.boundaries(events,{t['team_id'] for t in lineups})
        oracle=independent.reconstruct(pid,tid,player,events,bounds,issues)
        assert not oracle['issues'] and oracle['seconds']==oracle['lineup_seconds']>0
        assert independent.union(oracle['intervals'],bounds)==independent.union(oracle['lineup_intervals'],bounds)
        snapshots=[]
        for e in team_events:
            if raw.typ(e) not in ('Starting XI','Tactical Shift') or not member(e):continue
            active=[i for i,(lo,hi,_) in enumerate(oracle['lineup_position_intervals']) if lo<=raw.clock(e)<hi]
            assert len(active)==1
            pos=positions[active[0]]
            assert member(e)[0]['position']=={'id':pos['position_id'],'name':pos['position']}
            snapshots.append(e['id'])
        results.append(dict(player_id=pid,name=player['player_name'],match_id=mid,team_id=tid,team_name=team['team_name'],
            entry_uuid=entry['id'],shift_uuid=shift['id'],entry_type=raw.typ(entry),period=entry['period'],timestamp=entry['timestamp'],
            seconds=str(oracle['seconds']),minutes=str(oracle['seconds']/60),original_positions=positions,
            intervals=oracle['intervals'],lineup_intervals=oracle['lineup_intervals'],transition_uuids=oracle['event_ids'],
            snapshot_uuids=snapshots,boundary_uuids=boundary_ids,events_sha256=eb['sha256'],lineups_sha256=lb['sha256'],fixture_sha256=fb['sha256']))
    assert len(results)==10 and len({(r['player_id'],r['match_id']) for r in results})==10
    total=sum((Fraction(r['minutes']) for r in results),Fraction(0))
    out.write_text(json.dumps(dict(candidates=results,total_minutes=str(total),receipts=receipts),indent=2,default=str)+'\n',encoding='utf8')
    print(f'Independently corroborated {len(results)} entries; additional minutes {total} ({float(total):.10f})')


if __name__=='__main__':main()
