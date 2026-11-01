"""Isolated private comparison of frozen attributes; no scoring or delivery API."""
from copy import deepcopy
from fractions import Fraction
import math
from statistics import correlation, mean, median, stdev, pstdev

ATTRIBUTES = ('tackles', 'interceptions', 'recoveries', 'press_resistance', 'progressive_passing')
WEIGHTS = tuple(Fraction(n, 20) for n in (6, 5, 4, 3, 2))
NOTICE = 'PRIVATE / EXPERIMENTAL / NOT AN ADOPTED OVR / NOT PUBLICATION AUTHORIZED'


def exact(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 1 <= value <= 99:
        raise ValueError('Expected a finite frozen attribute rating in 1..99')
    return Fraction(value)


def pair(value):
    return {'numerator': value.numerator, 'denominator': value.denominator}


def unpack(value):
    return Fraction(value['numerator'], value['denominator'])


def calculate(attributes):
    """No intermediate rounding; exact rational operations on stored binary floats."""
    values = {a: None if attributes[a]['experimental_rating'] is None
              else exact(attributes[a]['experimental_rating']) for a in ATTRIBUTES}
    if any(v is None for v in values.values()):
        return {'status': 'N/A', 'reason': 'Five numeric frozen attributes required',
                'equal': None, 'dynamic': None, 'difference': None,
                'exact': None, 'dynamic_assignment': None, 'attribute_range': None,
                'attribute_population_sd': None}
    ordered = sorted(ATTRIBUTES, key=lambda a: (-values[a], ATTRIBUTES.index(a)))
    a = sum(values.values()) / 5
    b = sum(values[key] * weight for key, weight in zip(ordered, WEIGHTS))
    boost = b - a
    assert boost == (values[ordered[0]] - values[ordered[4]]) / 10 + (values[ordered[1]] - values[ordered[3]]) / 20
    return {'status': 'PRIVATE_EXPERIMENTAL_COMPARISON', 'reason': None,
            'equal': float(a), 'dynamic': float(b), 'difference': float(boost),
            'exact': {'equal': pair(a), 'dynamic': pair(b), 'difference': pair(boost)},
            'dynamic_assignment': [{'attribute': key, 'rating': attributes[key]['experimental_rating'],
                                    'weight': float(w), 'exact_weight': pair(w)} for key, w in zip(ordered, WEIGHTS)],
            'attribute_range': float(max(values.values()) - min(values.values())),
            'attribute_population_sd': pstdev(float(v) for v in values.values())}


def ranked(rows, formula):
    return sorted(rows, key=lambda p: (-unpack(p['private_ovr_comparison']['exact'][formula]), p['player_id'], p['id']))


def assign_ranks(rows, context):
    for formula in ('equal', 'dynamic'):
        ordered = ranked(rows, formula)
        i = 0
        while i < len(ordered):
            j = i + 1
            score = unpack(ordered[i]['private_ovr_comparison']['exact'][formula])
            while j < len(ordered) and unpack(ordered[j]['private_ovr_comparison']['exact'][formula]) == score:
                j += 1
            for p in ordered[i:j]:
                p['private_ovr_comparison']['ranks'][context][formula] = i + 1
                p['private_ovr_comparison']['average_ranks'][context][formula] = (i + 1 + j) / 2
            i = j
    for p in rows:
        r = p['private_ovr_comparison']['ranks'][context]
        r['improvement_under_dynamic'] = r['equal'] - r['dynamic']


def compare(profiles):
    out = []
    seen = set()
    for p in profiles:
        if p['id'] in seen:
            raise ValueError('Duplicate canonical player-season')
        seen.add(p['id'])
        result = calculate(p['attributes'])
        if all(p['attributes'][a]['experimental_rating'] is None for a in ATTRIBUTES):
            continue
        if p['comparison_group'] not in ('MID', 'CB'):
            raise ValueError('Unsupported comparison position')
        row = deepcopy(p)
        row['private_ovr_comparison'] = result | {
            'notice': NOTICE, 'official': False, 'adopted': False,
            'ranks': {'position': {'equal': None, 'dynamic': None, 'improvement_under_dynamic': None},
                      'overall_descriptive_only': {'equal': None, 'dynamic': None, 'improvement_under_dynamic': None}},
            'average_ranks': {'position': {'equal': None, 'dynamic': None},
                              'overall_descriptive_only': {'equal': None, 'dynamic': None}}}
        out.append(row)
    complete = [p for p in out if p['private_ovr_comparison']['equal'] is not None]
    for group in ('MID', 'CB'):
        assign_ranks([p for p in complete if p['comparison_group'] == group], 'position')
    assign_ranks(complete, 'overall_descriptive_only')
    return sorted(out, key=lambda p: (p['player_id'], p['id']))


def stats(values):
    values = list(values)
    return {'n': len(values), 'mean': mean(values) if values else None,
            'median': median(values) if values else None,
            'sample_sd': stdev(values) if len(values) > 1 else None,
            'min': min(values) if values else None, 'max': max(values) if values else None}


def rho(x, y):
    return correlation(x, y) if len(x) > 1 and len(set(x)) > 1 and len(set(y)) > 1 else None


def brief(p):
    c = p['private_ovr_comparison']
    return {'id': p['id'], 'player_id': p['player_id'], 'name': p['name'],
            'position': p['comparison_group'], 'clubs': [v['team'] for v in p['contexts']],
            'competitions': p['competitions'], 'limited_data': p['limited_data'], 'partial_season': p['partial_season'],
            'attributes': {a: p['attributes'][a]['experimental_rating'] for a in ATTRIBUTES},
            'known_supported_minutes': p['known_supported_minutes'],
            'metric_supported_minutes': {a: p['attributes'][a]['supported_minutes'] for a in ATTRIBUTES},
            'metric_warnings': {a: p['attributes'][a]['warnings'] for a in ATTRIBUTES},
            'press_attempts': p['attributes']['press_resistance']['attempts'],
            'attribute_range': c['attribute_range'], 'equal': c['equal'], 'dynamic': c['dynamic'],
            'difference': c['difference'], 'position_ranks': c['ranks']['position'],
            'overall_descriptive_ranks': c['ranks']['overall_descriptive_only']}


def describe(rows, context='position'):
    cs = [p['private_ovr_comparison'] for p in rows]
    # Spearman re-ranks within this descriptive subset, including tied averages.
    vectors = {}
    for formula in ('equal', 'dynamic'):
        scores = [unpack(c['exact'][formula]) for c in cs]
        ordered = sorted(scores)
        averages = {}
        for score in set(ordered):
            slots = [i + 1 for i, value in enumerate(ordered) if value == score]
            averages[score] = mean(slots)
        vectors[formula] = [averages[score] for score in scores]
    return {**{key: stats(c[key] for c in cs) for key in ('equal', 'dynamic', 'difference')},
            'spearman': rho(vectors['equal'], vectors['dynamic']),
            'rank_changed': sum(c['ranks'][context]['improvement_under_dynamic'] != 0 for c in cs),
            'max_absolute_rank_change': max((abs(c['ranks'][context]['improvement_under_dynamic']) for c in cs), default=0),
            'limited_data_count': sum(p['limited_data'] for p in rows),
            'below_40_press_actions': sum(0 < (p['attributes']['press_resistance']['attempts'] or 0) < 40 for p in rows),
            'below_900_supported_minutes': sum(Fraction(**p['known_supported_minutes']) < 900 for p in rows),
            'any_metric_below_900_minutes': sum(any(Fraction(**p['attributes'][a]['supported_minutes']) < 900
                                                 for a in ATTRIBUTES if a != 'press_resistance') for p in rows),
            'any_clipped_99': sum(any(p['attributes'][a]['experimental_rating'] == 99 for a in ATTRIBUTES) for p in rows),
            'any_excluded_appearances': sum(any(p['attributes'][a]['excluded_appearances'] for a in ATTRIBUTES) for p in rows)}


def reversal_analysis(rows):
    """Pairwise order reversals within a position; no inference about football truth."""
    ordered = ranked(rows, 'equal')
    scores = [(p, unpack(p['private_ovr_comparison']['exact']['equal']),
               unpack(p['private_ovr_comparison']['exact']['dynamic'])) for p in ordered]
    reversals = comparable = violations = 0
    largest = None
    gap = Fraction(-1)
    for i, (high, ha, hb) in enumerate(scores):
        for low, la, lb in scores[i + 1:]:
            if ha == la:
                continue
            comparable += 1
            if hb < lb:
                reversals += 1
                violations += all(high['attributes'][a]['experimental_rating'] >= low['attributes'][a]['experimental_rating'] for a in ATTRIBUTES)
                if ha - la > gap:
                    gap = ha - la
                    largest = {'higher_under_equal': brief(high), 'higher_under_dynamic': brief(low),
                               'equal_score_gap': float(gap)}
    return {'comparable_pairs': comparable, 'reversed_pairs': reversals,
            'reversed_fraction': reversals / comparable if comparable else None,
            'pareto_dominance_violations': violations, 'largest_equal_gap_reversed': largest}


def summarize(rows):
    complete = [p for p in rows if p['private_ovr_comparison']['equal'] is not None]
    summary = {'notice': NOTICE, 'supported_profiles': len(rows), 'complete': len(complete),
               'partial': len(rows) - len(complete), 'overall_descriptive_only': describe(complete, 'overall_descriptive_only'),
               'positions': {}, 'quality_subsets': {},
               'boost_range_pearson': rho([p['private_ovr_comparison']['difference'] for p in complete],
                                         [p['private_ovr_comparison']['attribute_range'] for p in complete])}
    boards = {}
    for group in ('MID', 'CB'):
        subset = [p for p in complete if p['comparison_group'] == group]
        summary['positions'][group] = describe(subset)
        summary['positions'][group]['reversals'] = reversal_analysis(subset)
        boards[group] = {f: [brief(p) for p in ranked(subset, f)[:20]] for f in ('equal', 'dynamic')}
        summary['positions'][group]['top20_limited_data'] = {f: sum(p['limited_data'] for p in boards[group][f]) for f in ('equal', 'dynamic')}
        for flag in (False, True):
            summary['quality_subsets'][group + ('_LIMITED_DATA' if flag else '_four_league_only')] = describe([p for p in subset if p['limited_data'] == flag])
    boards['overall_descriptive_only'] = {f: [brief(p) for p in ranked(complete, f)] for f in ('equal', 'dynamic')}
    boards['largest_boosts'] = [brief(p) for p in sorted(complete, key=lambda p: (-unpack(p['private_ovr_comparison']['exact']['difference']), p['player_id']))[:20]]
    move = lambda p: p['private_ovr_comparison']['ranks']['position']['improvement_under_dynamic']
    boards['largest_rank_gains'] = [brief(p) for p in sorted(complete, key=lambda p: (-move(p), p['player_id']))[:20]]
    boards['largest_rank_losses'] = [brief(p) for p in sorted(complete, key=lambda p: (move(p), p['player_id']))[:20]]
    boards['smallest_attribute_spreads'] = [brief(p) for p in sorted(complete, key=lambda p: (p['private_ovr_comparison']['attribute_range'], p['player_id']))[:10]]
    boards['largest_attribute_spreads'] = [brief(p) for p in sorted(complete, key=lambda p: (-p['private_ovr_comparison']['attribute_range'], p['player_id']))[:10]]
    wanted = {3961: "N'Golo Kanté", 5574: 'Toni Kroos', 5539: 'Casemiro', 3037: 'Mousa Dembélé',
              7173: 'Leonardo Bonucci', 5675: 'Kalidou Koulibaly', 3500: 'Granit Xhaka',
              4802: 'Florentin Pogba', 3103: 'Milan Biševac'}
    by_id = {p['player_id']: p for p in rows}
    boards['requested_examples'] = [{'requested_name': name, 'result': brief(by_id[pid]) if pid in by_id else None,
                                    'absence_reason': None if pid in by_id else 'Absent from frozen supported-score profiles'} for pid, name in wanted.items()]
    boards['partial_profiles'] = [brief(p) for p in rows if p['private_ovr_comparison']['equal'] is None]
    return summary, boards
