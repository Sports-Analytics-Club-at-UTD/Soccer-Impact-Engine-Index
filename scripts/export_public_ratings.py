"""Project the validated local adapter into the approved public ratings scope.

Run manually with the authorized research checkout as --source-root. Production
builds never run Python or read research files. Existing outputs are not replaced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def project(data):
    players = []
    metrics = ('tackles', 'interceptions', 'recoveries', 'press_resistance', 'line_breaking_passes')
    for p in data['players']:
        ovr = data['ovr_integration']['players'][p['id']]
        attrs = {key: {field: p['attributes'][key][field] for field in
                 ('rating', 'percentile', 'limited_data', 'missingness', 'warnings')} for key in metrics}
        badge_eligible = (ovr['eligible'] and not p['limited_data'] and
                          not any(a['limited_data'] for a in attrs.values()) and
                          all(a['rating'] is not None for a in attrs.values()))
        players.append({**{key: p[key] for key in ('id', 'player_id', 'name', 'season_name',
                        'comparison_position', 'positions', 'primary_position', 'secondary_positions',
                        'limited_data', 'partial_season')},
                        'clubs': [{k: c[k] for k in ('name', 'competition_name')} for c in p['clubs']],
                        'coverage': {'supported_minutes': p['known_supported_minutes']['numerator'] /
                                     p['known_supported_minutes']['denominator'],
                                     'observed_fixtures': sum(len(c['match_ids']) for c in p['clubs'])},
                        'attributes': attrs, 'ovr': ovr, 'badge_eligible': badge_eligible})
    return {'schema_version': 'soccer-public-ratings/v1', 'release': '2015-16-v1',
            'season': '2015/2016', 'formula_version': data['ovr_integration']['version'],
            'eligibility_version': data['ovr_integration']['eligibility_version'],
            'reference_version': 'frozen-mid-cb-2015-16/v1',
            'disclosures': [
                'Experimental project ratings, not official EA Sports FC/FIFA ratings or validated player quality.',
                'Available observations do not establish complete seasons. Missing matches are not zero-action performances.',
                'MID and CB use separate unchanged frozen references; Bundesliga observations do not contribute to the baseline.',
                'Bundesliga coverage is uneven. Limited Data also includes profiles excluded from strict rankings.',
                'Progressive passing is a proxy and does not verify opponent defensive lines.'
            ], 'counts': data['counts'], 'players': players}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source_root.resolve()))
    from scripts.provisional_ovr import build
    data = project(build())
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as target:
        target.write(payload)
    print(json.dumps({'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'players': len(data['players'])}))
