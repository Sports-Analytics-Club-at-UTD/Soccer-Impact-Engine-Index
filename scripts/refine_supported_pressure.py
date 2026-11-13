"""Replay only fixtures affected by the initial overbroad pressure clock check.

The parent snapshot's complete source replay is byte-bound and retained. A subset
of an already monotonic sequence cannot introduce a new ordering conflict; only
fixtures with the old clock-order reason need fresh decoding. All other fields
must remain identical. No source events or historical outputs are changed.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path

from scripts.rebuild_supported_ratings import ROOT, sha, jsonl, finish
from src.reconciled_source import replay


def refine(source, parent, output, workers=4):
    source,parent,output=source.resolve(),parent.resolve(),output.resolve()
    if not output.is_relative_to(ROOT/'audit-output') or output.exists():raise ValueError('new local output directory required')
    manifest=json.loads((parent/'manifest.json').read_text())
    for name,expected in manifest['artifacts'].items():
        if sha(parent/name)!=expected:raise ValueError('parent snapshot changed: '+name)
    receipts=json.loads((parent/'input-hashes.json').read_text())
    for path,expected in receipts.items():
        if sha(path)!=expected:raise ValueError('original input changed: '+path)
    receipts[str(parent/'manifest.json')]=sha(parent/'manifest.json')
    receipts[str(parent/'source-replay.jsonl')]=sha(parent/'source-replay.jsonl')
    previous={r['match_id']:r for r in jsonl(parent/'source-replay.jsonl')}
    target={mid for mid,row in previous.items() if any('SOURCE_CLOCK_INDEX_DISAGREEMENT' in p['chronology_reasons'] for p in row['appearances'])}
    bindings={}
    for relative in ('data/derived/phase3-step2-source-reconstruction-2026-10-27/appearance-ledger.jsonl','data/derived/bundesliga-targeted-2026-10-29/appearances.jsonl'):
        for row in jsonl(source/relative):
            binding=row.get('review_reference',row.get('report_reference'))
            if binding:bindings[row['match_id']]=binding
    old_path=ROOT/'frontend/public/data/player-ratings-2015-16-v1.json';old=json.loads(old_path.read_bytes())
    identities={int(p['player_id']):p['name'] for p in old['players']}
    print(f'Rechecking {len(target)} affected fixtures; preserving all other verified replay rows.',flush=True)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        pending={executor.submit(replay,(str(source),mid,bindings[mid],identities)):mid for mid in sorted(target)}
        for future in as_completed(pending):
            mid=pending[future];result=future.result();result.pop('event_ids');receipts.update(result.pop('receipts'))
            before=deepcopy(previous[mid]);after=deepcopy(result)
            for fixture in (before,after):
                for player in fixture['appearances']:
                    player.pop('chronology_reasons');player['metrics']['press_resistance'].pop('included');player['metrics']['press_resistance'].pop('reasons')
            if before!=after:raise ValueError('pressure refinement changed unrelated evidence')
            previous[mid]=result
    output.mkdir(parents=True);appearances=[];benches=[]
    with (output/'source-replay.jsonl').open('x',encoding='utf8') as handle:
        for mid,row in sorted(previous.items()):
            handle.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n');appearances.extend(row['appearances']);benches.extend(row['nonappearances'])
    summary=json.loads((parent/'summary.json').read_text())
    return finish(output,old,appearances,benches,receipts,sorted(previous),summary['original_events'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--parent',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();refine(args.source_root,args.parent,args.output)
