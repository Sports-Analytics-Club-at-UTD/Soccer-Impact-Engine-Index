"""Source-only checks with invented inputs; copied assertions retain independent expectations."""
from decimal import Decimal
from fractions import Fraction
import unittest
from src.private_ovr_formula_c import parameters, normalize, evaluate, digest, pair, unpack, value

def synthetic_reference():
    params = parameters([Fraction(64), Fraction(65), Fraction(66)])
    r = {'pools': {g: params | {'member_ids': []} for g in ('MID', 'CB')}}
    return r | {'sha256': digest(r)}


def synthetic_row(pid, average):
    a = Fraction(average)
    return {'id': str(pid), 'player_id': pid, 'comparison_group': 'MID',
            'private_ovr_comparison': {'equal': float(a), 'dynamic': float(a),
                'exact': {'equal': pair(a), 'dynamic': pair(a)}}}


class FormulaCArithmeticTests(unittest.TestCase):
    def test_exact_mean_sample_variance_and_sample_sd(self):
        p = parameters([Fraction(61), Fraction(65), Fraction(69)])
        self.assertEqual(unpack(p['exact_mean']), 65)
        self.assertEqual(unpack(p['exact_sample_variance']), 16)
        self.assertEqual(Decimal(p['sample_sd_decimal']), 4)
        self.assertEqual(normalize(Fraction(69), p)['rating'], 75)


    def test_clipping_both_boundaries(self):
        p = synthetic_reference()['pools']['MID']
        for average, expected in [(1, 1), (99, 99), (65, 65)]:
            c = normalize(Fraction(average), p)
            self.assertEqual(c['rating'], expected)
            self.assertEqual(c['clipped'], average != 65)


    def test_insufficient_and_zero_variance_fail_closed(self):
        for values in ([], [Fraction(65)], [Fraction(65)] * 2):
            with self.assertRaises(ValueError):
                parameters(values)
        with self.assertRaises(ValueError):
            normalize(Fraction(65), None)
        p = synthetic_reference()['pools']['MID'] | {'sample_sd_decimal': '0'}
        with self.assertRaises(ValueError):
            normalize(Fraction(65), p)


    def test_clipping_creates_competition_ties_without_reversals(self):
        rows = evaluate([synthetic_row(1, '68.5'), synthetic_row(2, 70), synthetic_row(3, 65)], synthetic_reference())
        self.assertEqual([p['formula_c_evaluation']['position_ranks']['C'] for p in rows], [1, 1, 3])
        self.assertGreater(value(rows[1], 'A'), value(rows[0], 'A'))
        self.assertEqual(value(rows[0], 'C'), value(rows[1], 'C'))


    def test_affine_slope_and_intercept(self):
        p = parameters([Fraction(61), Fraction(65), Fraction(69)])
        self.assertEqual(Decimal(p['slope_decimal']), Decimal('2.5'))
        self.assertEqual(Decimal(p['intercept_decimal']), Decimal('-97.5'))
        for a in (61, 65, 69):
            self.assertEqual(Decimal(normalize(Fraction(a), p)['unclipped_decimal']), Decimal('2.5') * a - Decimal('97.5'))


    def test_reference_hash_tamper_rejected(self):
        r = synthetic_reference()
        r['pools']['MID']['mean'] += 1
        with self.assertRaisesRegex(ValueError, 'changed'):
            evaluate([], r)


    def test_rounded_display_tie_never_controls_rank(self):
        rows = evaluate([synthetic_row(1, '65.00001'), synthetic_row(2, '65.00002')], synthetic_reference())
        self.assertEqual(f"{rows[0]['formula_c_evaluation']['rating']:.2f}", f"{rows[1]['formula_c_evaluation']['rating']:.2f}")
        self.assertEqual([p['formula_c_evaluation']['position_ranks']['C'] for p in rows], [2, 1])
