"""Provisional Formula B; independent of attribute fitting and presentation."""
from fractions import Fraction
import math

VERSION = 'soccer-ovr-formula-b/v1'
ELIGIBILITY_VERSION = 'existing-strict-five-attribute-reference/v1'


def formula_b(values):
    """Return no score for anything other than five finite ratings in [1, 99]."""
    if not isinstance(values, (list, tuple)) or len(values) != 5 or any(
        type(v) not in (int, float) or not 1 <= v <= 99 or not math.isfinite(v) for v in values
    ):
        return None
    return float(sum(v * Fraction(w, 20) for v, w in
                     zip(sorted(map(Fraction, values), reverse=True), (6, 5, 4, 3, 2))))
