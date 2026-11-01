"""Source-only checks with invented inputs; copied assertions retain independent expectations."""
from copy import deepcopy
from fractions import Fraction
import unittest
from src.private_ovr_comparison import ATTRIBUTES, WEIGHTS, calculate, compare, summarize, unpack

def attributes(values):
    return {a: {'experimental_rating': v} for a, v in zip(ATTRIBUTES, values)}


def profile(pid, values):
    return {'id': f'{pid}:2015/2016', 'player_id': pid, 'comparison_group': 'MID', 'attributes': attributes(values)}


class ArithmeticTests(unittest.TestCase):
    def test_known_mean_and_dynamic(self):
        c = calculate(attributes([90, 80, 70, 60, 50]))
        self.assertEqual((c['equal'], c['dynamic'], c['difference']), (70, 75, 5))
        self.assertEqual(sum(WEIGHTS), 1)


    def test_dynamic_not_fixed_to_attribute(self):
        a = calculate(attributes([90, 80, 70, 60, 50]))
        b = calculate(attributes([50, 60, 70, 80, 90]))
        self.assertEqual(a['exact'], b['exact'])
        self.assertEqual(b['dynamic_assignment'][0]['attribute'], 'progressive_passing')


    def test_equal_scores_and_deterministic_ties(self):
        for value in (1, 65.123456789, 99):
            c = calculate(attributes([value] * 5))
            self.assertEqual(c['exact']['equal'], c['exact']['dynamic'])
            self.assertEqual([a['attribute'] for a in c['dynamic_assignment']], list(ATTRIBUTES))


    def test_no_intermediate_rounding(self):
        values = [90.123456789123, 80.000000000003, 70.001, 60.232, 50.7]
        c = calculate(attributes(values))
        self.assertEqual(unpack(c['exact']['equal']), sum(map(Fraction, values)) / 5)
        self.assertEqual(unpack(c['exact']['dynamic']), sum(Fraction(v) * w for v, w in zip(values, WEIGHTS)))


    def test_missing_no_imputation_and_invalid_fail_closed(self):
        self.assertIsNone(calculate(attributes([10, None, 40, 50, 60]))['equal'])
        for bad in (True, float('nan'), float('inf'), 0, 100, '65'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                calculate(attributes([bad, 10, 20, 30, 40]))


    def test_competition_ties_average_ranks_and_order(self):
        inputs = [profile(3, [50]*5), profile(2, [70]*5), profile(1, [70]*5)]
        before = deepcopy(inputs)
        rows = compare(inputs)
        self.assertEqual(rows, compare(reversed(inputs)))
        self.assertEqual(inputs, before)
        self.assertEqual([p['private_ovr_comparison']['ranks']['position']['equal'] for p in rows], [1, 1, 3])
        self.assertEqual(rows[0]['private_ovr_comparison']['average_ranks']['position']['equal'], 1.5)


    def test_duplicate_and_unsupported_fail_closed(self):
        p = profile(1, [50]*5)
        with self.assertRaises(ValueError):
            compare([p, p])
        p['comparison_group'] = 'ATT'
        with self.assertRaises(ValueError):
            compare([p])


    def test_spread_premium_and_component_monotonicity(self):
        balanced = calculate(attributes([70]*5))
        uneven = calculate(attributes([90, 80, 70, 60, 50]))
        self.assertEqual(balanced['equal'], uneven['equal'])
        self.assertGreater(uneven['dynamic'], balanced['dynamic'])
        baseline = [90, 80, 70, 60, 50]
        for i in range(5):
            raised = baseline.copy()
            raised[i] += 1
            c = calculate(attributes(raised))
            self.assertGreater(c['equal'], uneven['equal'])
            self.assertGreater(c['dynamic'], uneven['dynamic'])
