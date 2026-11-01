"""Joseph Level A player-season observations; private experiments only.

No production admission, card exporter, file I/O or opponent-line claim.
"""
from collections import defaultdict
from fractions import Fraction
import math
import statistics

from src.source_reconstruction import exact, rational

VERSION = 'joseph-level-a-player-season/v1'
NOTICE = 'PRIVATE / EXPERIMENTAL / NOT PRODUCTION / NOT PUBLICATION AUTHORIZED'
FOUR = {'Premier League', 'La Liga', 'Serie A', 'Ligue 1'}


def combine_observations(rows):
    """Sum disjoint supported raw facts, never club rates or ratings.

    An unsupported appearance is retained as missing, not a zero. Rates describe
    the explicitly enumerated supported subset. Reference candidates require all
    observed appearances, >=900 minutes, and only the four named leagues.
    """
    players = defaultdict(list)
    seen = set()
    for r in rows:
        k = (r['player_id'], r['season_name'], r['match_id'])
        if k in seen:
            raise ValueError('duplicate canonical player/fixture contribution')
        seen.add(k)
        if r['season_name'] != '2015/2016' or r['competition_name'] not in FOUR | {'1. Bundesliga'}:
            raise ValueError('outside explicit league-season scope')
        players[k[:2]].append(r)
    out = []
    for (pid, season), contributions in sorted(players.items()):
        cs = sorted(contributions, key=lambda r: r['match_id'])
        good = [r for r in cs if not r['reasons']]
        seconds = sum((exact(r['seconds']) for r in good), Fraction(0))
        positions = defaultdict(Fraction)
        for r in cs:
            for p, v in r['position_seconds'].items():
                positions[p] += exact(v)
        groups = defaultdict(Fraction)
        # Choose the most-played fine group first, then map DM/CM to MID.
        from scripts.verify_bundesliga_readiness import position_group
        for p, value in positions.items():
            groups[position_group(p)] += value
        high = max(groups.values(), default=0)
        dominant = sorted(k for k,v in groups.items() if v == high and high > 0)
        group = ('MID' if dominant[0] in ('DM','CM') else dominant[0]) if len(dominant) == 1 else None
        comps = sorted({r['competition_name'] for r in cs})
        supported = bool(good and seconds > 0)
        totals = {k: sum(r[k] for r in good) if supported else None for k in
                  ('prog_attempts','prog_passes','third_cross','measured_passes')}
        for r in good:
            if (any(type(r[k]) is not int or r[k] < 0 for k in totals)
                    or not 0 <= r['third_cross'] <= r['prog_passes'] <= r['prog_attempts'] <= r['measured_passes']
                    or exact(r['seconds']) <= 0):
                raise ValueError('invalid supported count/exposure')
        minutes = seconds / 60
        full = len(good) == len(cs)
        bundes = '1. Bundesliga' in comps
        pending = any(r['match_id'] == 3879594 for r in cs)
        value_supported = supported and all(r['value_sum'] is not None for r in good)
        value = math.fsum(r['value_sum'] for r in good) if value_supported else None
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError('invalid difficulty-adjusted value')
        candidate = bool(supported and full and minutes >= 900 and group in ('MID','CB') and not bundes and not pending)
        out.append(dict(player_id=pid, season_name=season, name=cs[0]['name'],
            clubs=sorted({r['team'] for r in cs}), competitions=comps,
            comparison_group=group, dominant_fine_groups=dominant,
            position_seconds={p:rational(v) for p,v in sorted(positions.items())},
            observed_match_ids=[r['match_id'] for r in cs],
            supported_match_ids=[r['match_id'] for r in good],
            excluded_appearances=[dict(match_id=r['match_id'],reasons=r['reasons']) for r in cs if r['reasons']],
            supported_minutes=rational(minutes), minutes=float(minutes) if supported else None,
            all_observed_exposure_supported=full, limited_data=bundes,
            partial_season=True, coverage_status='LIMITED DATA' if bundes else 'OBSERVED PROVIDER FIXTURES; NOT FULL-SEASON CERTIFIED',
            experimental_reference_candidate=candidate, reference_member=False,
            evidence_status='INDEPENDENT SAME-PROVIDER CALCULATIONS; EXTERNAL ATTESTATION PENDING',
            measurement_status='SUPPORTED_OBSERVED_SCOPE' if full and supported else 'SUPPORTED_SUBSET' if supported else 'MISSING',
            **totals, prog_passes_p90=totals['prog_passes']/float(minutes)*90 if supported else None,
            prog_completion_pct=100*totals['prog_passes']/totals['prog_attempts'] if supported and totals['prog_attempts'] else None,
            third_cross_p90=totals['third_cross']/float(minutes)*90 if supported else None,
            value_sum=value, pass_value_p90=value/float(minutes)*90 if value is not None else None,
            value_status='FULL_ELIGIBLE_COHORT_CALIBRATION' if value is not None else 'UNAVAILABLE_INCOMPLETE_CALIBRATION_OR_EXPOSURE',
            rating=None, publication_authorized=False, production_certified=False))
    return out


def private_preview(players):
    """Versioned private sample-SD formula; no production delivery shape."""
    if len({(p['player_id'],p['season_name']) for p in players}) != len(players):
        raise ValueError('duplicate reference player-season')
    players = sorted(players,key=lambda p:(p['player_id'],p['season_name']))
    pools = {}
    scores = []
    for group in ('MID','CB'):
        members = [p for p in players if p['experimental_reference_candidate'] and p['comparison_group'] == group]
        if any(p['limited_data'] or not set(p['competitions']) <= FOUR or not p['all_observed_exposure_supported']
               or p['minutes'] < 900 for p in members):
            raise ValueError('invalid experimental reference member')
        xs = [p['prog_passes_p90'] for p in members]
        mean = statistics.mean(xs) if xs else None
        sd = statistics.stdev(xs) if len(xs)>1 else None
        pools[group] = dict(n=len(xs),mean=mean,sample_std_dev=sd,player_ids=[p['player_id'] for p in members])
        for p in players:
            if p['comparison_group'] != group or p['prog_passes_p90'] is None:
                continue
            rating = min(99,max(1,65+10*(p['prog_passes_p90']-mean)/sd)) if sd and sd>0 else None
            scores.append(dict(player_id=p['player_id'],season_name=p['season_name'],group=group,
                private_experimental_rating=rating,limited_data=p['limited_data'],
                minutes=p['minutes'],measurement_status=p['measurement_status'],
                low_minutes=p['minutes'] < 900,
                experimental_reference_candidate=p['experimental_reference_candidate']))
    return dict(schema_version=VERSION+'/private-preview',notice=NOTICE,
        metric='prog_passes_p90',formula='clip(65 + 10 * ((x - mean) / sample_std_dev), 1, 99)',
        population='unique four-league observed player-seasons; all observed appearances supported; >=900 combined minutes; dominant fine position then MID/CB; excludes Bundesliga contributors and pending fixture 3879594',
        pools=pools,players=scores,publication_authorized=False,numeric_ratings_enabled=False)
