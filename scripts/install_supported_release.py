"""Install an independently verified aggregate snapshot in this branch only."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def install(directory):
    verification=json.loads((directory/'verification.json').read_text())
    manifest_bytes=(directory/'manifest.json').read_bytes()
    manifest=json.loads(manifest_bytes)
    raw=(directory/'public-ratings.json').read_bytes()
    if (verification['status']!='PASS' or verification['players']!=691 or
        verification.get('manifest_sha256')!=hashlib.sha256(manifest_bytes).hexdigest() or
        verification.get('public_sha256')!=hashlib.sha256(raw).hexdigest() or
        verification.get('verifier_sha256')!=hashlib.sha256((ROOT/'scripts/verify_supported_ratings.py').read_bytes()).hexdigest() or
        hashlib.sha256(raw).hexdigest()!=manifest['artifacts']['public-ratings.json']):
        raise ValueError('verified complete aggregate release required')
    data=json.loads(raw)
    if data['schema_version']!='soccer-public-ratings/v2' or data['release']!='2015-16-v2':
        raise ValueError('unexpected release')
    # Hash the source measurements and reference again before using the receipt.
    for name in ('players.json','measurements.json','frozen-reference.json','source-replay.jsonl'):
        with (directory/name).open('rb') as handle:actual=hashlib.file_digest(handle,'sha256').hexdigest()
        if actual!=manifest['artifacts'][name]:raise ValueError('verified artifact changed: '+name)
    encoded=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
    destination=ROOT/'frontend/public/data/player-ratings-2015-16-v2.json'
    with destination.open('xb') as handle:handle.write(encoded)
    fingerprint=hashlib.sha256(encoded).hexdigest()
    descriptor=ROOT/'frontend/src/lib/publicRatingsRelease.js'
    descriptor.write_text("""// Historical aggregate release retained for explicit compatibility checks.
export const LEGACY_PUBLIC_RATINGS_RELEASE = Object.freeze({
  path: 'data/player-ratings-2015-16-v1.json',
  sha256: '9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e',
  bytes: 1431543,
  approval: 'Team approval for final aggregate 2015/16 ratings supplied on 2026-10-31; raw research excluded.',
});

// Supported samples and rebuilt cohorts authorized in the player-audit review.
// Exact path and bytes remain mandatory; payload flags cannot admit other data.
export const PUBLIC_RATINGS_RELEASE = Object.freeze({
  path: 'data/player-ratings-2015-16-v2.json',
  sha256: '"""+fingerprint+"""',
  bytes: """+str(len(encoded))+""",
  approval: 'User authorized source/scope corrections, measurement and reference rebuild, and a uniform eligibility rule on 2026-11-13. Aggregate ratings and coverage only; no deployment or raw-source publication.',
});
""",encoding='utf8',newline='\n')
    print(json.dumps(dict(path=str(destination),bytes=len(encoded),sha256=fingerprint)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    install(parser.parse_args().directory)
