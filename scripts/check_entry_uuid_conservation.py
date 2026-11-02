"""Second raw-byte UUID inventory; no production imports or decision functions.

Build independently while the replay runs; compare inventories only after both
finish. The new disk database bounds memory and refuses an existing output.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--compare-only',action='store_true')
    args=parser.parse_args()
    root=Path.cwd();out=root/'audit-output/entry-uuid-independent'
    dbpath=out/'original-uuids.sqlite'
    if not args.compare_only:
        if out.exists():raise ValueError('Preserve prior inventory; use a fresh output directory')
        out.mkdir(parents=True)
        conn=sqlite3.connect(dbpath)
        conn.execute('create table originals(uuid text primary key, fixture integer, team integer, player integer) without rowid')
        receipts={};rows=0
        def read(path,expected):
            p=Path(path);b=p.read_bytes();h=hashlib.sha256(b).hexdigest()
            assert h==expected,str(p)
            receipts[str(p.resolve())]=dict(sha256=h,bytes=len(b));return json.loads(b)
        prior=root.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit/appearances.csv'
        matches={}
        with prior.open(encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):matches.setdefault(int(row['match_id']),json.loads(row['evidence']))
        assert len(matches)==1551
        for n,(mid,lead) in enumerate(sorted(matches.items()),1):
            report=read(lead['report_path'],lead['report_sha256'])
            binding=report['artifacts']['events'];events=read(binding['path'],binding['sha256'])
            ids={e['id'] for e in events};assert len(ids)==len(events)
            conn.executemany('insert into originals values (?,?,?,?)',
                ((e['id'],mid,e['team']['id'],e.get('player',{}).get('id')) for e in events))
            conn.commit();rows+=len(events)
            if n%250==0:print(f'Independent UUID inventory: {n}/1551 fixtures',flush=True)
        assert conn.execute('select count(*) from originals').fetchone()[0]==rows==5436699
        conn.close()
        (out/'input-hashes.json').write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf8')
        (out/'inventory.json').write_text(json.dumps(dict(fixtures=1551,original_events=rows,duplicate_uuids=0),indent=2)+'\n')
        print('Original-byte inventory complete; run --compare-only after full replay.',flush=True)
    else:
        conn=sqlite3.connect(dbpath.as_uri()+'?mode=ro&immutable=1',uri=True)
        replay=root/'audit-output/source-backed-entry-fix'
        summary=json.loads((replay/'summary.json').read_text())
        assert summary['source_checks']['original_events']==5436699
        conn.execute('attach database ? as replay',((replay/'uuid-conservation.sqlite').as_uri()+'?mode=ro&immutable=1',))
        missing=conn.execute('select count(*) from originals o left join replay.seen r on o.uuid=r.uuid where r.uuid is null').fetchone()[0]
        extra=conn.execute('select count(*) from replay.seen r left join originals o on o.uuid=r.uuid where o.uuid is null').fetchone()[0]
        assert missing==extra==0
        result=dict(fixtures=1551,original_events=5436699,missing_uuids=missing,extra_uuids=extra,duplicate_uuids=0,
            independent_database_sha256=hashlib.file_digest(dbpath.open('rb'),'sha256').hexdigest(),
            replay_database_sha256=hashlib.file_digest((replay/'uuid-conservation.sqlite').open('rb'),'sha256').hexdigest())
        target=out/'comparison.json'
        if target.exists():raise ValueError('Preserve previous comparison')
        target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
        conn.close()


if __name__=='__main__':main()
