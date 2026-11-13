"""Reopen the 101 affected fixtures and rebuild the complete 691-player snapshot.

The independently verified v2 snapshot supplies unchanged fixtures. Bundesliga
rows are preserved byte-for-byte at the parsed-record level, including its one
unresolved appearance. All parent artifacts and original input bytes are checked.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

from scripts.rebuild_supported_ratings import ROOT, sha, jsonl, finish
from src.reconciled_source import replay


def run(source,parent,output,workers=4):
    source,parent,output=source.resolve(),parent.resolve(),output.resolve()
    if not output.is_relative_to(ROOT/'audit-output') or output.exists():raise ValueError('new local output directory required')
    manifest=json.loads((parent/'manifest.json').read_text());verification=json.loads((parent/'verification.json').read_text())
    if verification['status']!='PASS' or verification['manifest_sha256']!=sha(parent/'manifest.json'):raise ValueError('verified parent required')
    for name,expected in manifest['artifacts'].items():
        if sha(parent/name)!=expected:raise ValueError('parent artifact changed: '+name)
    receipts=json.loads((parent/'input-hashes.json').read_text())
    for path,expected in receipts.items():
        if sha(path)!=expected:raise ValueError('original source changed: '+path)
    for name in ('manifest.json','source-replay.jsonl','public-ratings.json','verification.json'):
        receipts[str(parent/name)]=sha(parent/name)
    previous={r['match_id']:r for r in jsonl(parent/'source-replay.jsonl')}
    target={mid for mid,row in previous.items() if any(p['seconds'] is None and p['competition']!='1. Bundesliga' for p in row['appearances'])}
    bindings={}
    for relative in ('data/derived/phase3-step2-source-reconstruction-2026-10-27/appearance-ledger.jsonl','data/derived/bundesliga-targeted-2026-10-29/appearances.jsonl'):
        for row in jsonl(source/relative):
            binding=row.get('review_reference',row.get('report_reference'))
            if binding:bindings[row['match_id']]=binding
    old=json.loads((parent/'public-ratings.json').read_bytes());identities={int(p['player_id']):p['name'] for p in old['players']}
    print(f'Replaying {len(target)} affected fixtures; Bundesliga is unchanged.',flush=True)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        pending={executor.submit(replay,(str(source),mid,bindings[mid],identities)):mid for mid in sorted(target)}
        for index,future in enumerate(as_completed(pending),1):
            mid=pending[future];result=future.result();result.pop('event_ids');receipts.update(result.pop('receipts'))
            by_id={p['player_id']:p for p in previous[mid]['appearances']}
            if result['nonappearances']!=previous[mid]['nonappearances']:raise ValueError('recovery changed appearance admission')
            for p in result['appearances']:
                before=by_id[p['player_id']]
                if before['seconds'] is not None and p!=before:raise ValueError('previously supported row changed')
                if p['competition']=='1. Bundesliga' and p!=before:raise ValueError('Bundesliga changed')
            previous[mid]=result
            if index%20==0 or index==len(target):print(f'Checked {index}/{len(target)} affected fixtures',flush=True)
    output.mkdir(parents=True);appearances=[];benches=[]
    with (output/'source-replay.jsonl').open('x',encoding='utf8') as handle:
        for mid,row in sorted(previous.items()):
            handle.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n');appearances.extend(row['appearances']);benches.extend(row['nonappearances'])
    summary=json.loads((parent/'summary.json').read_text())
    return finish(output,old,appearances,benches,receipts,sorted(previous),summary['original_events'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--parent',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.source_root,args.parent,args.output)
