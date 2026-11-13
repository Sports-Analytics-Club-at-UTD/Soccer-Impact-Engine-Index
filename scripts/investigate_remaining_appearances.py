"""Inspect every remaining non-Bundesliga appearance against original source bytes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from src.appearance_recovery import recover_exposure, contains
from src.supported_sample_ratings import pair


def run(parent,output):
    if output.exists():raise ValueError('new output required')
    receipts=json.loads((parent/'input-hashes.json').read_text())
    sources={value:Path(path) for path,value in receipts.items()}
    rows=[p for line in (parent/'source-replay.jsonl').open(encoding='utf8') for p in json.loads(line)['appearances'] if p['seconds'] is None and p['competition']!='1. Bundesliga']
    cached={};results=[]
    for row in rows:
        fingerprint=row['source_sha256']
        if fingerprint not in cached:
            raw=sources[fingerprint].read_bytes()
            if hashlib.sha256(raw).hexdigest()!=fingerprint:raise ValueError('original source changed')
            cached[fingerprint]=json.loads(raw)
        events=cached[fingerprint];candidate=recover_exposure(events,row['team_id'],row['player_id'])
        result={key:row[key] for key in ('player_id','match_id','team','competition','original_issues','source_sha256')}
        result.update(status='full' if candidate.complete else 'partial' if candidate.seconds else 'withheld',
            seconds=pair(candidate.seconds),reasons=candidate.reasons,
            segments=[dict(period=s.period,start=pair(s.start),end=pair(s.end),start_reference=s.start_reference,end_reference=s.end_reference) for s in candidate.segments],
            proof_references=candidate.proof_references)
        by_id={e['id']:e for e in events}
        result['selected_actions_outside_recovery']={a:[uid for uid in m['numerator_ids'] if not contains(by_id[uid],candidate.segments)] for a,m in row['metrics'].items()}
        results.append(result)
    summary=dict(appearances=len(results),fixtures=len(cached),outcomes=dict(Counter(r['status'] for r in results)),
        withholding_reasons=dict(Counter(reason for r in results if r['status']=='withheld' for reason in r['reasons'])),
        partial_reasons=dict(Counter(reason for r in results if r['status']=='partial' for reason in r['reasons'])))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(dict(summary=summary,appearances=results),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parent',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.parent,args.output)
