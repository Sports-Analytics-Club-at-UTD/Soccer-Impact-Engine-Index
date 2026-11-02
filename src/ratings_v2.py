"""Private Ratings V2 integration. Frozen fitting and V1 delivery are untouched."""
import copy
from fractions import Fraction
from src.private_five_attribute import aggregate, score_players, validate_reference
from src.provisional_ovr import formula_b, ELIGIBILITY_VERSION
from src.private_ovr_formula_c import exclusion_reasons

VERSION = 'soccer-ratings-v2/frozen-reference-candidate-1'
ADMISSION_VERSION = 'source-bound-component-chronology/v1'


def reconstruct(canonical, facts, reference, exceptions, *, removed_nonappearances=()):
    # This source-proof layer is deliberately imported only by the V2 path.
    from scripts.event_chronology_diagnostics import correct_diagnostic_facts
    validate_reference(reference)
    reference_before = copy.deepcopy(reference)
    corrected, changed, proofs = correct_diagnostic_facts(facts, exceptions)
    players = copy.deepcopy(canonical)
    # Canonical active contributions, not administrative source activity, define
    # observations. A removed nonappearance is never replaced with zero minutes.
    removed=set(removed_nonappearances)
    if any((f['player_id'], f['match_id']) in removed for f in corrected):
        raise ValueError('removed nonappearance still contributes a fact')
    for p in players:
        p['observed_match_ids'] = [mid for mid in p['observed_match_ids']
                                   if (p['player_id'],mid) not in removed]
    scored = score_players(aggregate(players, corrected), reference)
    for p in scored:
        values = [m['experimental_rating'] for m in p['attributes'].values()]
        reasons = exclusion_reasons(p, reference)
        value = formula_b(values)
        p['ovr'] = dict(value=value, status='calculated' if value is not None else 'unavailable',
                        eligible=value is not None and not reasons, exclusion_reasons=reasons,
                        comparison_position=p['comparison_group'])
        p['ratings_version'] = VERSION
        p['eligibility_version'] = ELIGIBILITY_VERSION
        p['publication_authorized'] = False
    assert reference == reference_before
    return scored, corrected, changed, proofs


def rank_profiles(players, *, eligible_only=True):
    """Separate MID/CB; full precision, provider-ID tie order as in the UI."""
    result = {}
    for group in ('MID', 'CB'):
        selected = [p for p in players if p['comparison_group'] == group
                    and p['ovr']['value'] is not None
                    and (not eligible_only or p['ovr']['eligible'])]
        selected.sort(key=lambda p: (-p['ovr']['value'], p['player_id']))
        for i, p in enumerate(selected, 1):
            result[p['player_id']] = i
    return result


def independent_b(values):
    """Independent exact weighted mean and specialization invariant."""
    if len(values) != 5 or any(type(v) not in (float, int) or not 1 <= v <= 99 for v in values):
        return None
    s = sorted((Fraction(v) for v in values), reverse=True)
    a = sum(s) / 5
    b = sum(s[i] * Fraction(30 - 5*i, 100) for i in range(5))
    assert b >= a
    assert b-a == (s[0]-s[4])/10 + (s[1]-s[3])/20
    return float(b)
