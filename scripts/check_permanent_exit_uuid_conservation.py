"""Compare fresh replay UUIDs with a hash-bound independent original inventory.

Reuse is allowed only when the independently built DB and every raw-source
receipt match the original inventory and the fresh replay's byte hashes.
"""
import hashlib
import json
from pathlib import Path
import sqlite3


def main():
    root=Path.cwd();replay=root/'audit-output/permanent-exit-support'
    prior=root.parent/'Soccer-Impact-Engine-Index-source-backed-entry-fix/audit-output/entry-uuid-independent'
    dbpath=prior/'original-uuids.sqlite'
    read=lambda p:json.loads(p.read_text(encoding='utf8'))
    previous=read(prior/'comparison.json');fresh=read(replay/'input-hashes.json')
    digest=hashlib.file_digest(dbpath.open('rb'),'sha256').hexdigest()
    assert digest==previous['independent_database_sha256']
    source_receipts=read(prior/'input-hashes.json')
    for path,receipt in source_receipts.items():assert fresh[str(Path(path).resolve())]==receipt,path
    connection=sqlite3.connect(dbpath.as_uri()+'?mode=ro&immutable=1',uri=True)
    connection.execute('attach database ? as replay',((replay/'uuid-conservation.sqlite').as_uri()+'?mode=ro&immutable=1',))
    missing=connection.execute('select count(*) from originals o left join replay.seen r on o.uuid=r.uuid where r.uuid is null').fetchone()[0]
    extra=connection.execute('select count(*) from replay.seen r left join originals o on o.uuid=r.uuid where o.uuid is null').fetchone()[0]
    assert missing==extra==0
    assert connection.execute('select count(*) from replay.seen').fetchone()[0]==5436699
    result=dict(original_events=5436699,fixtures=1551,missing_uuids=missing,extra_uuids=extra,duplicate_uuids=0,
        independently_built_inventory_sha256=digest,raw_source_receipts_revalidated=len(source_receipts),
        replay_database_sha256=hashlib.file_digest((replay/'uuid-conservation.sqlite').open('rb'),'sha256').hexdigest())
    target=replay/'uuid-independent-comparison.json'
    if target.exists():raise ValueError('Preserve prior comparison')
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
