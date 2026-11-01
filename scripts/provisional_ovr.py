"""Read-only versioned integration of approved B into the existing local delivery.

No frozen outputs are written. Reuses the historical strict eligibility predicate,
without invoking Formula C fitting or standardization.
"""
import json

from scripts.local_experimental_ratings import build as attributes, PACKAGE
from src.private_ovr_comparison import ATTRIBUTES
from src.private_ovr_formula_c import exclusion_reasons
from src.provisional_ovr import VERSION, ELIGIBILITY_VERSION, formula_b


def build():
    data = attributes()  # Pins and validates source hashes before any OVR use.
    baseline = json.loads((PACKAGE / 'frozen-reference.json').read_text())
    supported = {p['id'] for p in data['players']}
    rows = {}
    for line in (PACKAGE / 'PRIVATE-EXPERIMENTAL-scores.jsonl').open(encoding='utf8'):
        p = json.loads(line)
        if p['id'] not in supported:
            continue
        value = formula_b([p['attributes'][a]['experimental_rating'] for a in ATTRIBUTES])
        reasons = exclusion_reasons(p, baseline)
        rows[p['id']] = dict(value=value, status='calculated' if value is not None else 'unavailable',
                             eligible=value is not None and not reasons, exclusion_reasons=reasons,
                             comparison_position=p['comparison_group'])
    data['ovr_integration'] = dict(version=VERSION, eligibility_version=ELIGIBILITY_VERSION,
        source_package=dict(data['source_package']), reference_fingerprint=data['reference']['fingerprint'],
        players=rows)
    return data


if __name__ == '__main__':
    print(json.dumps(build(), sort_keys=True, separators=(',', ':'), allow_nan=False))
