"""Verify the private package, conservation and isolation without source rebuild."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.prepare_fifth_attribute import records, sha
from src.fifth_attribute import combine_observations, private_preview
from src.rating_delivery import validate_delivery


def validate(root, output, tests):
    root,output,tests=Path(root),Path(output),Path(tests)
    if output.exists():raise ValueError('new validation output required')
    manifest=json.loads((root/'manifest.json').read_text())
    for name,expected in manifest['artifacts'].items():
        if sha(root/name)!=expected:raise ValueError('private output changed: '+name)
    for name,expected in manifest['implementation'].items():
        if sha(name)!=expected:raise ValueError('integration implementation changed: '+name)
    for entry in manifest['inputs']:
        seal=Path(entry['path'])
        if sha(seal)!=entry['sha256']:raise ValueError('source seal changed')
        for name,expected in entry['artifacts'].items():
            if sha(seal.parent/name)!=expected:raise ValueError('source artifact changed: '+name)
    observations=list(records(root/'match-observations.jsonl'))
    players=list(records(root/'player-measurements.jsonl'))
    preview=json.loads((root/'PRIVATE-EXPERIMENTAL-preview.json').read_text())
    if combine_observations(list(reversed(observations)))!=players:
        raise ValueError('reversed-input player aggregation is not deterministic')
    if private_preview(list(reversed(players)))!=preview:
        raise ValueError('reversed-input private normalization is not deterministic')
    good=[r for r in observations if not r['reasons']]
    for column in ('prog_attempts','prog_passes','third_cross','measured_passes'):
        if sum(r[column] for r in good)!=sum(p[column] or 0 for p in players):
            raise ValueError('raw count conservation failed: '+column)
    if any(p['rating'] is not None or p['publication_authorized'] or p['reference_member'] or p['production_certified'] for p in players):
        raise ValueError('production privilege or rating leaked')
    try:
        validate_delivery(preview)
    except ValueError:
        pass
    else:
        raise ValueError('private preview admitted by production delivery')
    receipts=json.loads(Path('data/derived/bundesliga-targeted-2026-10-29/input-receipts.json').read_text())
    protected={}
    for r in receipts['local_files']:
        if Path(r['path']).suffix=='.parquet':
            actual=sha(r['path'])
            if actual!=r['sha256']:raise ValueError('protected parquet changed')
            protected[r['path']]=actual
    suites=ET.parse(tests).getroot().findall('.//testsuite')
    if not suites or any(int(s.attrib.get(k,0)) for s in suites for k in ('failures','errors')):
        raise ValueError('complete passing regression record required')
    result=dict(status='PASS',deterministic_reversed_aggregation=True,count_conservation=True,
        official_numeric_ratings=0,production_delivery_rejects_private_preview=True,
        input_and_implementation_fingerprints_unchanged=True,protected_parquets=protected,
        tests=sum(int(s.attrib['tests']) for s in suites),tests_sha256=sha(tests),
        private_package={p.name:sha(p) for p in sorted(root.iterdir()) if p.is_file()},
        validator_sha256=sha(__file__),publication_authorized=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tests',type=Path,required=True)
    args=parser.parse_args();validate(args.input,args.output,args.tests)
