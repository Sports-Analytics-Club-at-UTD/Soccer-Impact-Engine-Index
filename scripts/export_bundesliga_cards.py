"""Export observation-only cards from existing sealed readiness, never sources."""
import argparse
import hashlib
import json
from pathlib import Path

from src.provisional_delivery import SCHEMA, DEFINITIONS, card_from_readiness, validate_delivery

EVIDENCE=Path('data/derived/bundesliga-targeted-2026-10-29')
VALIDATION=Path('data/validation/bundesliga-targeted-tests-2026-10-29')
PROVIDER=Path('data/source-evidence/bundesliga-targeted-2026-10-29/manifest.json')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def build():
    seal=json.loads((EVIDENCE/'run-manifest.json').read_text())
    # Only fingerprint the selected sealed inputs; do not rerun the broad audit.
    names=['player-readiness.jsonl','transfers.jsonl']
    for name in names:
        expected=next(a['sha256'] for a in seal['artifacts'] if a['path']==name)
        if sha(EVIDENCE/name)!=expected:raise ValueError('sealed readiness input changed: '+name)
    validation=json.loads((VALIDATION/'validation.json').read_text())
    package=json.loads((VALIDATION/'package-manifest.json').read_text())
    for path in [VALIDATION/'validation.json',EVIDENCE/'run-manifest.json']:
        expected=next(a['sha256'] for a in package['artifacts'] if Path(a['path']).name==path.name)
        if sha(path)!=expected:raise ValueError('validation binding changed')
    if validation['status']!='PASS':raise ValueError('targeted verification must pass')
    with (EVIDENCE/'player-readiness.jsonl').open(encoding='utf8') as f:rows=[json.loads(s) for s in f]
    with (EVIDENCE/'transfers.jsonl').open(encoding='utf8') as f:transfers={r['player_id']:r for r in map(json.loads,f)}
    sources=[dict(id=name,path=str(path).replace('\\','/'),sha256=sha(path),label=label) for name,path,label in [
        ('readiness',EVIDENCE/'player-readiness.jsonl','StatsBomb original-source player measurements'),
        ('transfers',EVIDENCE/'transfers.jsonl','Verified transfer scope and combined measurements'),
        ('provider',PROVIDER,'StatsBomb provider revision '+json.loads(PROVIDER.read_text())['provider_revision']),
        ('seal',EVIDENCE/'run-manifest.json','Byte-bound source verification manifest'),
        ('validation',VALIDATION/'validation.json','Independent calculation and lineage checks')]]
    cards=[card_from_readiness(transfers.get(r['player_id'],r),candidate=r['comparison_group'] in ('MID','CB'),bundesliga_row=r,
        provenance_ids=['transfers' if r['player_id'] in transfers else 'readiness','provider','seal','validation']) for r in rows]
    data=dict(schema_version=SCHEMA,definitions_id=DEFINITIONS,numeric_ratings_enabled=False,publication_authorized=False,
        baseline=None,sources=sources,players=cards)
    return validate_delivery(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();data=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    # The exporter never overwrites an existing artifact.
    with args.output.open('x',encoding='utf8',newline='\n') as f:json.dump(data,f,ensure_ascii=True,allow_nan=False,sort_keys=True,indent=2);f.write('\n')
    print(f"Exported {len(data['players'])} canonical player-season cards; ratings withheld")


if __name__=='__main__':main()
