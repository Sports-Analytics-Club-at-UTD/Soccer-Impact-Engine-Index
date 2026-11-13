"""Versioned ratings from supported samples; no historical artifacts are mutated."""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import statistics

from src.private_five_attribute import ATTRIBUTES, POLICY as METRIC_POLICY

VERSION = 'supported-sample-five-attributes/v1'
FOUR = {'Premier League', 'La Liga', 'Serie A', 'Ligue 1'}
POLICY = dict(id=VERSION, minimum_minutes=900, minimum_pressure_attempts=40,
    competitions=sorted(FOUR), groups=['MID', 'CB'],
    population='the 691 published 2015/2016 player identities; all retained active source appearances',
    sample='each per90 numerator and minute denominator use the same accepted appearances; pressure uses verified action pairs',
    exclusions='unsupported observations excluded and disclosed, without disqualifying other supported observations',
    references='separate MID/CB pools; all five pools use the same eligible player population per position',
    definitions=deepcopy(METRIC_POLICY['definitions']),
    formula=METRIC_POLICY['formula'], standard_deviation=METRIC_POLICY['standard_deviation'],
    percentile=METRIC_POLICY['percentile'],
    minimums_status='retained project cutoffs, not statistically validated certainty thresholds')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def pair(value):
    return None if value is None else dict(numerator=value.numerator, denominator=value.denominator)


def unpack(value):
    return None if value is None else Fraction(value['numerator'], value['denominator'])


def eligibility(player):
    """No all-observed-complete or historical reference-membership requirements."""
    reasons = []
    if player['comparison_group'] not in POLICY['groups']:
        reasons.append('UNSUPPORTED_POSITION')
    if not player['competitions'] or not set(player['competitions']) <= FOUR:
        reasons.append('BUNDESLIGA_CONTRIBUTION' if '1. Bundesliga' in player['competitions'] else 'NOT_FOUR_LEAGUE_ONLY')
    if unpack(player['known_supported_minutes']) < 900:
        reasons.append('BELOW_900_VERIFIED_SEASON_MINUTES')
    for attribute in ATTRIBUTES:
        m = player['attributes'][attribute]
        if m['exact_value'] is None:
            reasons.append(attribute + ':MISSING_MEASUREMENT_DENOMINATOR')
        if attribute != 'press_resistance' and unpack(m['supported_minutes']) < 900:
            reasons.append(attribute + ':BELOW_900_SUPPORTED_METRIC_MINUTES')
        if attribute == 'press_resistance' and m['attempts'] < 40:
            reasons.append(attribute + ':BELOW_40_SUPPORTED_ATTEMPTS')
    return reasons


def aggregate(identities, appearances):
    """Reject duplicate scopes and preserve included/excluded event IDs privately."""
    grouped = defaultdict(list)
    seen = set()
    event_sets = {a: set() for a in (*ATTRIBUTES, 'pressure_attempts')}
    ids = {int(p['player_id']) for p in identities}
    if len(ids) != len(identities):
        raise ValueError('duplicate player identity')
    for row in appearances:
        key = row['player_id'], row['match_id']
        if key in seen or key[0] not in ids:
            raise ValueError('duplicate or unknown player/fixture')
        seen.add(key)
        if row['seconds'] is not None and unpack(row['seconds']) <= 0:
            raise ValueError('positive exact playing time required')
        for a, metric in row['metrics'].items():
            if metric['included'] != (not metric['reasons']):
                raise ValueError('metric support contradicts reasons')
            selected = metric['numerator_ids']
            if len(selected) != len(set(selected)) or event_sets[a].intersection(selected):
                raise ValueError('duplicate numerator event')
            event_sets[a].update(selected)
            if a == 'press_resistance':
                attempts = metric['denominator_ids']
                if len(attempts) != len(set(attempts)) or not set(selected) <= set(attempts) or event_sets['pressure_attempts'].intersection(attempts):
                    raise ValueError('invalid pressure pairs')
                event_sets['pressure_attempts'].update(attempts)
            elif metric['included'] and row['seconds'] is None:
                raise ValueError('per90 lacks a supported denominator')
        grouped[key[0]].append(row)
    result = []
    for old in sorted(identities, key=lambda p: int(p['player_id'])):
        rows = sorted(grouped[int(old['player_id'])], key=lambda r: r['match_id'])
        seconds = sum((unpack(r['seconds']) for r in rows if r['seconds'] is not None), Fraction())
        metrics = {}
        for a in ATTRIBUTES:
            good = [r for r in rows if r['metrics'][a]['included']]
            numerator = sum(len(r['metrics'][a]['numerator_ids']) for r in good)
            duration = sum((unpack(r['seconds']) for r in good if r['seconds'] is not None), Fraction()) / 60
            attempts = sum(len(r['metrics'][a]['denominator_ids']) for r in good) if a == 'press_resistance' else None
            value = (Fraction(100*numerator, attempts) if attempts else None) if a == 'press_resistance' else (Fraction(90*numerator)/duration if duration else None)
            metrics[a] = dict(numerator=numerator, attempts=attempts, supported_minutes=pair(duration),
                exact_value=pair(value), value=None if value is None else float(value),
                numerator_match_ids=[r['match_id'] for r in good], denominator_match_ids=[r['match_id'] for r in good],
                excluded_appearances=[dict(match_id=r['match_id'], reasons=r['metrics'][a]['reasons']) for r in rows if not r['metrics'][a]['included']])
        competitions = sorted({r['competition'] for r in rows})
        player = dict(player_id=int(old['player_id']), id=old['id'], name=old['name'],
            comparison_group=old['comparison_position'], competitions=competitions,
            observed_match_ids=[r['match_id'] for r in rows],
            supported_match_ids=[r['match_id'] for r in rows if r['seconds'] is not None],
            known_supported_minutes=pair(seconds/60), attributes=metrics)
        player['exclusion_reasons'] = eligibility(player)
        player['eligible'] = not player['exclusion_reasons']
        result.append(player)
    return result


def freeze_reference(players, input_binding):
    if len({p['player_id'] for p in players}) != len(players):
        raise ValueError('duplicate reference identity')
    pools = {}
    for group in POLICY['groups']:
        members = sorted((p for p in players if p['comparison_group'] == group and not eligibility(p)), key=lambda p: p['player_id'])
        pools[group] = {}
        for a in ATTRIBUTES:
            xs = [p['attributes'][a]['value'] for p in members]
            if len(xs) < 2 or statistics.stdev(xs) <= 0:
                raise ValueError('insufficient reference members or zero variance: ' + group + '/' + a)
            pools[group][a] = dict(n=len(xs), member_ids=[p['player_id'] for p in members],
                exact_values=[p['attributes'][a]['exact_value'] for p in members],
                mean=statistics.mean(xs), sample_sd=statistics.stdev(xs))
    reference = dict(version=VERSION, policy=deepcopy(POLICY), input_binding=input_binding, pools=pools)
    reference['sha256'] = digest(reference)
    return reference


def score(players, reference):
    if reference['sha256'] != digest({k:v for k,v in reference.items() if k != 'sha256'}) or reference['policy'] != POLICY:
        raise ValueError('changed reference')
    result = deepcopy(players)
    for p in result:
        for a, m in p['attributes'].items():
            m.update(rating=None, percentile=None, score_reason=None)
            # Measurements remain visible even below ranking minimums.
            if m['value'] is None:
                m['score_reason'] = 'NO_SUPPORTED_ATTEMPTS' if a == 'press_resistance' else 'NO_SUPPORTED_MEASUREMENT'
                continue
            pool = reference['pools'][p['comparison_group']][a]
            m['rating'] = min(99., max(1., 65. + 10.*(m['value']-pool['mean'])/pool['sample_sd']))
            xs = sorted(unpack(x) for x in pool['exact_values']); value = unpack(m['exact_value'])
            lo, hi = bisect_left(xs, value), bisect_right(xs, value)
            m['percentile'] = 100*((lo+1+hi)/2 if hi > lo else lo)/len(xs)
        values = [p['attributes'][a]['rating'] for a in ATTRIBUTES]
        p['overall'] = None if None in values else float(sum((Fraction(v)*Fraction(w,100) for v,w in zip(sorted(values,reverse=True), (30,25,20,15,10))), Fraction()))
        if p['overall'] is None and p['eligible']:
            raise ValueError('eligible profile lacks a complete rating')
    return result
