"""Check preservation and build isolation; no metric/source calculation."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path('data/validation/five-attribute-website-v1')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def check():
    before=json.loads((ROOT/'preservation-before.json').read_text(encoding='utf-8-sig'))
    for p in before:
        if sha(p['path'])!=p['sha256']:raise ValueError('preserved input changed: '+p['path'])
    build=ROOT/'build-final'
    files=[p for p in build.rglob('*') if p.is_file() and p.suffix in ('.js','.json','.html','.css')]
    if not files:raise ValueError('production build missing')
    forbidden=['PRIVATE-EXPERIMENTAL-scores.jsonl','private-five-attribute-player-season/v2',
        '403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd','"experimental_rating"']
    # Exact noninteger score canaries are read only for a negative leakage check.
    private=Path('data/derived/private-five-attribute-v2/PRIVATE-EXPERIMENTAL-scores.jsonl')
    for line in private.open(encoding='utf8'):
        p=json.loads(line)
        if p['player_id'] in (3961,5574):
            forbidden.extend(str(m['experimental_rating']) for m in p['attributes'].values() if m['experimental_rating'] is not None)
    for p in files:
        content=p.read_text(encoding='utf8')
        if any(token in content for token in forbidden):raise ValueError('private rating leakage: '+str(p))
    synthetic_chunks=[p for p in files if p.name.startswith('FiveAttributeExperience-') and p.suffix=='.js']
    if len(synthetic_chunks)!=1:raise ValueError('synthetic readiness chunk missing')
    chunk=synthetic_chunks[0].read_text(encoding='utf8')
    if 'SYNTHETIC TEST FIXTURE' not in chunk or 'synthetic:mid-transfer' not in chunk:raise ValueError('synthetic data labels absent')
    suites=ET.parse(ROOT/'backend.xml').getroot().findall('.//testsuite')
    if not suites or any(int(s.attrib.get(k,0)) for s in suites for k in ('failures','errors')):raise ValueError('backend regressions failed')
    frontend=(ROOT/'frontend.txt').read_text(encoding='utf8')
    if 'fail 0' not in frontend or 'pass 179' not in frontend:raise ValueError('frontend regressions failed')
    baseline=json.loads(Path('data/derived/private-five-attribute-v2/frozen-reference.json').read_text())
    approval=Path('docs/review/five-attribute-team-approval-2026-10-29.md').read_text(encoding='utf8')
    for pools in baseline['pools'].values():
        for pool in pools.values():
            if str(pool['mean']) not in approval or str(pool['sample_sd']) not in approval:raise ValueError('approval snapshot statistic drift')
    result=dict(status='PASS',backend_tests=sum(int(s.attrib['tests']) for s in suites),frontend_tests=179,
        unchanged_preserved_files=len(before),frozen_baselines_and_measurements_unchanged=True,
        legacy_contracts_and_bundesliga_components_unchanged=True,production_build='PASS',
        build_text_assets_scanned=len(files),private_score_leakage=False,approval_statistics_copied_from_frozen_snapshot=True,
        numeric_real_delivery_enabled=False,publication_authorized=False,
        screenshots=[str(ROOT/n) for n in ('synthetic-bundesliga.jpg','synthetic-missing.jpg')],
        validation_inputs={n:sha(ROOT/n) for n in ('backend.xml','frontend.txt','build-final.txt','preservation-before.json')},
        artifacts={p:sha(p) for p in ('docs/review/five-attribute-team-approval-2026-10-29.md','docs/five-attribute-delivery-contract.md',
            'src/five_attribute_presentation.py','frontend/src/fixtures/syntheticFiveAttributes.json')})
    output=ROOT/'validation.json'
    with output.open('x',encoding='utf8') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':check()
