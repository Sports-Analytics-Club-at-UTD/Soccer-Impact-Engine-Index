"""Hash-bound original-source candidates; two reconstructions, no decoder calls."""
import csv
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from scripts import decoder_fix_independent as raw
from scripts import off_field_card_independent as independent


def candidates(root):
    prior = root.parent / 'Soccer-Impact-Engine-Index-source-evidence-reconciliation/audit-output/source-reconciliation'
    return [r for r in csv.DictReader((prior/'disputed-appearances.csv').open(encoding='utf-8-sig')) if r['classification']=='E']


def verify(root, rows=None):
    history = root.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit/appearances.csv'
    leads = {int(r['match_id']): json.loads(r['evidence']) for r in csv.DictReader(history.open(encoding='utf-8-sig'))}
    receipts = {}; results = []
    def read(path, expected=None):
        path = Path(path); data = path.read_bytes(); digest = hashlib.sha256(data).hexdigest()
        if expected: assert digest == expected, str(path)
        receipts[str(path.resolve())] = dict(sha256=digest, bytes=len(data))
        return json.loads(data)
    selected=candidates(root) if rows is None else rows
    for row in selected:
        pid, mid, tid = (int(row[k]) for k in ('player_id','match_id','team_id'))
        lead = leads[mid]; report = read(lead['report_path'], lead['report_sha256'])
        bindings = [report['fixture_document'], report['artifacts']['lineups'], report['artifacts']['events']]
        fixtures, lineups, events = [read(b['path'], b['sha256']) for b in bindings]
        fixture = next(f for f in fixtures if f['match_id']==mid)
        roster = [(t,p) for t in lineups for p in t['lineup'] if p['player_id']==pid]
        assert len(roster)==1 and roster[0][0]['team_id']==tid
        assert tid in (fixture['home_team']['home_team_id'],fixture['away_team']['away_team_id'])
        team, player = roster[0]
        bounds, issues, uuids = raw.boundaries(events, {t['team_id'] for t in lineups})
        result = independent.reconstruct(pid, tid, player, events, bounds, issues)
        assert not result['issues'] and result['seconds']==result['lineup_seconds']>0
        assert independent.union(result['intervals'],bounds)==independent.union(result['lineup_intervals'],bounds)
        exits = [e for e in events if e['team']['id']==tid and e.get('player',{}).get('id')==pid and raw.typ(e)=='Player Off' and e.get('player_off',{}).get('permanent') is True]
        assert len(exits)==1
        terminal = exits[0]
        entries = [e for e in events if e['team']['id']==tid and (raw.typ(e)=='Starting XI' and any(x['player']['id']==pid for x in e.get('tactics',{}).get('lineup',[])) or raw.typ(e)=='Substitution' and e['substitution']['replacement']['id']==pid)]
        assert len(entries)==1 and raw.clock(entries[0])<raw.clock(terminal)
        after = [e for e in events if e['team']['id']==tid and raw.clock(e)>raw.clock(terminal) and (e.get('player',{}).get('id')==pid or e.get('pass',{}).get('recipient',{}).get('id')==pid or any(x['player']['id']==pid for x in e.get('tactics',{}).get('lineup',[])))]
        assert not after
        activity=[e for e in events if e['team']['id']==tid and (e.get('player',{}).get('id')==pid or e.get('pass',{}).get('recipient',{}).get('id')==pid)]
        for e in activity:
            t=raw.clock(e)
            assert bounds[t[0]][0]<=t[1]<=bounds[t[0]][1] and any(lo<=t<=hi for lo,hi in result['intervals'])
            if e['id']!=terminal['id'] and t==raw.clock(terminal):assert e['index']<terminal['index']
        snapshots = []
        for e in events:
            if e['team']['id']!=tid or raw.typ(e) not in ('Starting XI','Tactical Shift'): continue
            members = [x for x in e.get('tactics',{}).get('lineup',[]) if x['player']['id']==pid]
            if not members: continue
            active = [i for i,(lo,hi,_) in enumerate(result['lineup_position_intervals']) if lo<=raw.clock(e)<hi]
            assert len(members)==len(active)==1
            p = player['positions'][active[0]]
            assert members[0]['position']==dict(id=p['position_id'],name=p['position'])
            snapshots.append(e['id'])
        ordered = sorted(events,key=lambda e:e['index'])
        assert [e['index'] for e in ordered]==sorted(set(e['index'] for e in events))
        relevant = [e for e in ordered if e['id'] in result['event_ids']+uuids+snapshots]
        assert [raw.clock(e) for e in relevant]==sorted(raw.clock(e) for e in relevant)
        results.append(dict(player_id=pid,name=player['player_name'],match_id=mid,team_id=tid,
            original_entry={k:v for k,v in entries[0].items() if k!='_audit_clock'},
            permanent_exit={k:v for k,v in terminal.items() if k!='_audit_clock'},
            original_positions=player['positions'],bounds=bounds,boundary_uuids=uuids,snapshot_uuids=snapshots,
            independent=result,additional_seconds=str(result['seconds']),additional_minutes=str(result['seconds']/60),
            prior_issues=json.loads(row.get('production_issues') or row.get('before_issues') or '[]'),source_documents=bindings))
    if rows is None:assert len(results)==3
    return dict(candidates=results,receipts=receipts,total_minutes=str(sum((Fraction(r['additional_minutes']) for r in results),Fraction())))


if __name__=='__main__':
    root=Path.cwd(); out=root/'audit-output/permanent-exit-independent-source-checks.json'
    if out.exists(): raise ValueError('Preserve completed evidence')
    result=verify(root);out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf8')
    for r in result['candidates']: print(r['name'],r['player_id'],r['match_id'],r['permanent_exit']['timestamp'],r['additional_minutes'])
