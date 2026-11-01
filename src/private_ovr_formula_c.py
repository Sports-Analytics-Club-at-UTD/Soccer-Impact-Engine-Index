"""Private Formula C evaluation; consumes frozen A/B, never fits attributes."""
from collections import Counter
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from statistics import correlation

from src.private_ovr_comparison import ATTRIBUTES, pair, unpack, stats

VERSION = 'private-ovr-comparison-v2'
NOTICE = 'PRIVATE / EXPERIMENTAL / NO OVR ADOPTED / NOT PUBLICATION AUTHORIZED'
FOUR = {'Premier League', 'La Liga', 'Serie A', 'Ligue 1'}
PRECISION = 80


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def decimal(value):
    return Decimal(value.numerator) / Decimal(value.denominator)


def exclusion_reasons(p, attribute_reference):
    """Intersect the existing normal attribute policies, checking explicit scope evidence."""
    reasons = []
    group = p['comparison_group']
    if group not in ('MID', 'CB'):
        reasons.append('UNSUPPORTED_POSITION')
    if p['limited_data'] or '1. Bundesliga' in p['competitions']:
        reasons.append('BUNDESLIGA_CONTRIBUTION')
    if not p['competitions'] or not set(p['competitions']) <= FOUR:
        reasons.append('NOT_FOUR_LEAGUE_ONLY')
    if unpack(p['known_supported_minutes']) < 900:
        reasons.append('BELOW_900_VERIFIED_SEASON_MINUTES')
    if not p['all_observed_exposure_supported']:
        reasons.append('INCOMPLETE_OBSERVED_EXPOSURE')
    observed = p['observed_match_ids']
    if not observed or len(observed) != len(set(observed)) or 3879594 in observed:
        reasons.append('INVALID_OR_PENDING_FIXTURE_SCOPE')
    for a in ATTRIBUTES:
        m = p['attributes'][a]
        if m['experimental_rating'] is None:
            reasons.append(a + ':ABSENT_RATING')
        if not m['experimental_reference_candidate']:
            reasons.append(a + ':NOT_NORMAL_REFERENCE_CANDIDATE')
        if not m['experimental_reference_member'] or group not in attribute_reference['pools'] or p['player_id'] not in attribute_reference['pools'].get(group, {}).get(a, {}).get('member_ids', []):
            reasons.append(a + ':NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER')
        if not m['all_observed_metric_scope_supported'] or m['excluded_appearances']:
            reasons.append(a + ':INCOMPLETE_METRIC_SCOPE')
        if (m['numerator_match_ids'] != m['denominator_match_ids'] or
                len(m['numerator_match_ids']) != len(set(m['numerator_match_ids'])) or
                set(m['numerator_match_ids']) != set(observed)):
            reasons.append(a + ':FIXTURE_SCOPE_NOT_FULLY_ALIGNED')
        if unpack(m['supported_minutes']) != unpack(p['known_supported_minutes']) or unpack(m['supported_minutes']) < 900:
            reasons.append(a + ':METRIC_EXPOSURE_NOT_COMPLETE_900_MINUTES')
        if m['exact_value'] is None or m['numerator'] is None:
            reasons.append(a + ':MISSING_MEASUREMENT_DENOMINATOR')
        if a == 'press_resistance' and (type(m['attempts']) is not int or m['attempts'] < 40):
            reasons.append(a + ':BELOW_40_SUPPORTED_ATTEMPTS')
    return reasons


def parameters(averages):
    if len(averages) < 2:
        raise ValueError('Formula C requires at least two eligible members')
    mu = sum(averages) / len(averages)
    variance = sum((a - mu) ** 2 for a in averages) / (len(averages) - 1)
    if variance <= 0:
        raise ValueError('Formula C zero variance; normalization withheld')
    with localcontext() as ctx:
        ctx.prec = PRECISION
        sd = decimal(variance).sqrt()
        slope = Decimal(10) / sd
        intercept = Decimal(65) - slope * decimal(mu)
        return {'n': len(averages), 'exact_mean': pair(mu), 'exact_sample_variance': pair(variance),
                'sample_sd_expression': 'sqrt(exact_sample_variance)',
                'mean': float(mu), 'sample_sd': float(sd), 'sample_sd_decimal': str(sd),
                'slope_decimal': str(slope), 'intercept_decimal': str(intercept),
                'unclipped_1_threshold_decimal': str(decimal(mu) - Decimal('6.4') * sd),
                'unclipped_99_threshold_decimal': str(decimal(mu) + Decimal('3.4') * sd)}


def freeze_reference(profiles, previous_rows, attribute_reference):
    profiles, previous_rows = list(profiles), list(previous_rows)
    by_id = {p['id']: p for p in previous_rows}
    if len(by_id) != len(previous_rows) or len({p['id'] for p in profiles}) != len(profiles):
        raise ValueError('Duplicate canonical player-season')
    audit = []
    pools = {g: [] for g in ('MID', 'CB')}
    for p in sorted(profiles, key=lambda p: (p['player_id'], p['id'])):
        reasons = exclusion_reasons(p, attribute_reference)
        audit.append({'id': p['id'], 'player_id': p['player_id'], 'comparison_group': p['comparison_group'],
                      'eligible': not reasons, 'exclusion_reasons': reasons})
        if not reasons:
            old = by_id.get(p['id'])
            if old is None or old['private_ovr_comparison']['exact'] is None:
                raise ValueError('Eligible member missing from frozen complete A/B results')
            pools[p['comparison_group']].append({'id': p['id'], 'player_id': p['player_id'],
                'average_exact': old['private_ovr_comparison']['exact']['equal'],
                'average': old['private_ovr_comparison']['equal'],
                'known_supported_minutes': p['known_supported_minutes'],
                'observed_match_ids': p['observed_match_ids'],
                'press_attempts': p['attributes']['press_resistance']['attempts']})
    frozen = {'version': VERSION + '/formula-c-reference', 'notice': NOTICE, 'frozen': True,
              'publication_authorized': False, 'pools': {}}
    for group, members in pools.items():
        frozen['pools'][group] = parameters([unpack(m['average_exact']) for m in members]) | {
            'member_ids': [m['id'] for m in members], 'player_ids': [m['player_id'] for m in members], 'members': members}
    frozen['sha256'] = digest(frozen)
    return frozen, audit


def normalize(average, params):
    if params is None:
        raise ValueError('Unsupported comparison group')
    with localcontext() as ctx:
        ctx.prec = PRECISION
        sd = Decimal(params['sample_sd_decimal'])
        if not sd.is_finite() or sd <= 0:
            raise ValueError('Invalid Formula C sample SD')
        z = (decimal(average) - decimal(unpack(params['exact_mean']))) / sd
        raw = Decimal(65) + Decimal(10) * z
        clipped = min(Decimal(99), max(Decimal(1), raw))
        return {'rating': float(clipped), 'rating_decimal': str(clipped), 'z_decimal': str(z),
                'unclipped_decimal': str(raw), 'clipped': raw < 1 or raw > 99,
                'clipping_boundary': 1 if raw < 1 else 99 if raw > 99 else None}


def value(p, method, unclipped=False):
    if method in ('A', 'B'):
        return unpack(p['private_ovr_comparison']['exact'][{'A': 'equal', 'B': 'dynamic'}[method]])
    key = 'unclipped_decimal' if unclipped else 'rating_decimal'
    return Fraction(Decimal(p['formula_c_evaluation'][key]))


def order(rows, method):
    return sorted(rows, key=lambda p: (-value(p, method), p['player_id'], p['id']))


def rank_maps(rows, method):
    ordered = order(rows, method)
    slots = {}
    for i, p in enumerate(ordered, 1):
        slots.setdefault(value(p, method), []).append(i)
    return {p['id']: {'competition': min(slots[value(p, method)]),
                      'average': sum(slots[value(p, method)]) / len(slots[value(p, method)])} for p in rows}


def evaluate(previous_rows, reference):
    if reference['sha256'] != digest({k: v for k, v in reference.items() if k != 'sha256'}):
        raise ValueError('Frozen Formula C reference changed')
    out = []
    for old in sorted(previous_rows, key=lambda p: (p['player_id'], p['id'])):
        p = deepcopy(old)
        group = p['comparison_group']
        if old['private_ovr_comparison']['equal'] is None:
            c = {'rating': None, 'rating_decimal': None, 'z_decimal': None, 'unclipped_decimal': None,
                 'clipped': False, 'clipping_boundary': None, 'reason': 'FIVE_NUMERIC_ATTRIBUTES_REQUIRED'}
        else:
            c = normalize(unpack(old['private_ovr_comparison']['exact']['equal']), reference['pools'].get(group)) | {'reason': None}
        p['formula_c_evaluation'] = c | {'notice': NOTICE, 'reference_sha256': reference['sha256'],
            'reference_member': p['id'] in reference['pools'].get(group, {}).get('member_ids', []),
            'position_ranks': {m: None for m in ('A', 'B', 'C')},
            'overall_descriptive_ranks': {m: None for m in ('A', 'B', 'C')},
            'adopted': False, 'publication_authorized': False}
        out.append(p)
    complete = [p for p in out if p['formula_c_evaluation']['rating'] is not None]
    for group in ('MID', 'CB', 'overall_descriptive'):
        subset = complete if group == 'overall_descriptive' else [p for p in complete if p['comparison_group'] == group]
        context = 'overall_descriptive_ranks' if group == 'overall_descriptive' else 'position_ranks'
        for method in ('A', 'B', 'C'):
            ranks = rank_maps(subset, method)
            for p in subset:
                p['formula_c_evaluation'][context][method] = ranks[p['id']]['competition']
    return out


def brief(p):
    old, c = p['private_ovr_comparison'], p['formula_c_evaluation']
    return {'id': p['id'], 'name': p['name'], 'comparison_group': p['comparison_group'],
            'A': old['equal'], 'B': old['dynamic'], 'C': c['rating'],
            'C_unclipped': c['unclipped_decimal'], 'C_clipped': c['clipped'],
            'C_reference_member': c['reference_member'], 'position_ranks': c['position_ranks'],
            'overall_descriptive_ranks': c['overall_descriptive_ranks'],
            'known_supported_minutes': p['known_supported_minutes'],
            'press_attempts': p['attributes']['press_resistance']['attempts'],
            'metric_sample_sizes': {a: {'numerator': p['attributes'][a]['numerator'],
                                      'attempts': p['attributes'][a]['attempts'],
                                      'supported_minutes': p['attributes'][a]['supported_minutes']} for a in ATTRIBUTES},
            'attributes': {a: p['attributes'][a]['experimental_rating'] for a in ATTRIBUTES},
            'limited_data': p['limited_data'], 'partial_season': p['partial_season'],
            'metric_warnings': {a: p['attributes'][a]['warnings'] for a in ATTRIBUTES},
            'clubs': [v['team'] for v in p['contexts']], 'competitions': p['competitions']}


def pair_analysis(rows, left, right):
    left_rank, right_rank = rank_maps(rows, left), rank_maps(rows, right)
    lvec = [left_rank[p['id']]['average'] for p in rows]
    rvec = [right_rank[p['id']]['average'] for p in rows]
    n = len(rows)
    rho = correlation(lvec, rvec) if n > 1 and len(set(lvec)) > 1 and len(set(rvec)) > 1 else None
    scores = [(value(p, left), value(p, right)) for p in rows]
    reversals = new_ties = broken_ties = 0
    for i, (a, b) in enumerate(scores):
        for c, d in scores[i + 1:]:
            reversals += (a - c) * (b - d) < 0
            new_ties += a != c and b == d
            broken_ties += a == c and b != d
    shifts = [{**brief(p), 'rank_change': left_rank[p['id']]['competition'] - right_rank[p['id']]['competition']}
              for p in rows]
    return {'n': n, 'spearman': rho, 'pairwise_reversals': reversals, 'new_tied_pairs': new_ties,
            'broken_tied_pairs': broken_ties,
            'players_with_rank_change': sum(v['rank_change'] != 0 for v in shifts),
            'largest_rank_changes': sorted(shifts, key=lambda p: (-abs(p['rank_change']), p['id']))[:10],
            'difference_right_minus_left': stats(float(value(p, right) - value(p, left)) for p in rows),
            'largest_numeric_differences': [brief(p) | {'right_minus_left': float(value(p, right) - value(p, left))}
                                            for p in sorted(rows, key=lambda p: (-abs(value(p, right) - value(p, left)), p['id']))[:10]]}


def describe(rows):
    return {'n': len(rows), 'distributions': {m: stats(float(value(p, m)) for p in rows) for m in ('A', 'B', 'C')},
            'clipped_1': sum(p['formula_c_evaluation']['clipping_boundary'] == 1 for p in rows),
            'clipped_99': sum(p['formula_c_evaluation']['clipping_boundary'] == 99 for p in rows),
            'below_40_press_actions': sum((p['attributes']['press_resistance']['attempts'] or 0) < 40 for p in rows),
            'below_900_minutes': sum(unpack(p['known_supported_minutes']) < 900 for p in rows),
            'top20': {m: [brief(p) for p in order(rows, m)[:20]] for m in ('A', 'B', 'C')},
            'display_ties': {m: {'groups': sum(n > 1 for n in counts.values()),
                                 'pairs': sum(n * (n - 1) // 2 for n in counts.values()),
                                 'rule': 'two-decimal display only; never used for rank'}
                             for m in ('A', 'B', 'C')
                             for counts in [Counter(f'{float(value(p, m)):.2f}' for p in rows)]}}


def cross_quality_pairs(normal, bundesliga):
    result = {'pairs': len(normal) * len(bundesliga)}
    for left, right in (('A', 'B'), ('A', 'C'), ('B', 'C')):
        reversed_pairs = ties = 0
        for a in normal:
            for b in bundesliga:
                x = value(a, left) - value(b, left)
                y = value(a, right) - value(b, right)
                reversed_pairs += x * y < 0
                ties += x != 0 and y == 0
        result[left + '_vs_' + right] = {'reversals': reversed_pairs, 'new_tied_pairs': ties}
    return result


def summarize(rows, reference, audit):
    complete = [p for p in rows if p['formula_c_evaluation']['rating'] is not None]
    result = {'notice': NOTICE, 'complete': len(complete), 'partial': len(rows) - len(complete),
              'canonical_examined': len(audit), 'positions': {}, 'overall_descriptive_only': describe(complete),
              'exclusion_reason_counts': dict(sorted(Counter(r for p in audit for r in p['exclusion_reasons']).items()))}
    for group in ('MID', 'CB'):
        subset = [p for p in complete if p['comparison_group'] == group]
        subsets = {'normal_four_league_reference_members': [p for p in subset if p['formula_c_evaluation']['reference_member']],
                   'four_league_reference_excluded_recipients': [p for p in subset if not p['limited_data'] and not p['formula_c_evaluation']['reference_member']],
                   'bundesliga_limited_data': [p for p in subset if p['limited_data']]}
        result['positions'][group] = describe(subset) | {
            'comparisons': {a + '_vs_' + b: pair_analysis(subset, a, b) for a, b in (('A', 'B'), ('A', 'C'), ('B', 'C'))},
            'quality_subsets': {name: describe(ps) | {'A_vs_C': pair_analysis(ps, 'A', 'C')} for name, ps in subsets.items()},
            'normal_vs_bundesliga_pair_behavior': cross_quality_pairs(subsets['normal_four_league_reference_members'], subsets['bundesliga_limited_data']),
            'top20_bundesliga_counts': {m: sum(p['limited_data'] for p in order(subset, m)[:20]) for m in ('A', 'B', 'C')},
            'affine_proof': {'formula': 'C_unclipped = slope * A + intercept', 'positive_slope': Decimal(reference['pools'][group]['slope_decimal']) > 0,
                'unclipped_order_matches_A': [p['id'] for p in order(subset, 'A')] == [p['id'] for p in sorted(subset, key=lambda p: (-value(p, 'C', True), p['player_id'], p['id']))]}}
    result['overall_descriptive_only']['A_vs_C'] = pair_analysis(complete, 'A', 'C')
    wanted = {3961: "N'Golo Kanté", 5574: 'Toni Kroos', 5539: 'Casemiro', 3037: 'Mousa Dembélé',
              7173: 'Leonardo Bonucci', 5675: 'Kalidou Koulibaly', 3500: 'Granit Xhaka',
              34558: 'Sereso Dié', 22824: 'Sebastian Rode', 4802: 'Florentin Pogba'}
    by_id = {p['player_id']: p for p in rows}
    result['requested_examples'] = [{'requested_name': name, 'result': brief(by_id[pid]) if pid in by_id else None,
                                    'absence_reason': None if pid in by_id else 'Absent from frozen supported profiles'} for pid, name in wanted.items()]
    result['partial_profiles'] = [brief(p) for p in rows if p['formula_c_evaluation']['rating'] is None]
    return result
