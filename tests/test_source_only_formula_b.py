"""Source-only checks with invented inputs; copied assertions retain independent expectations."""
import itertools
import math
import unittest
from src.provisional_ovr import formula_b

class FormulaBTests(unittest.TestCase):
    def test_independent_examples_and_permutations(self):
        for values, expected in [([75]*5, 75), ([90,90,85,55,55],80.25), ([99]*5,99), ([1]*5,1)]:
            for perm in set(itertools.permutations(values)):
                self.assertEqual(formula_b(perm), expected)


    def test_invalid_inputs(self):
        for values in (None, [], [75]*4, [75]*6, [75,75,75,75,None], [75,75,75,75,'75'],
                       [75,75,75,75,True], [75,75,75,75,math.nan], [75,75,75,75,math.inf],
                       [75,75,75,75,0], [75,75,75,75,100], [10**1000]*5):
            self.assertIsNone(formula_b(values))


    def test_precision_reproducibility_and_continuity(self):
        values = [75.123456789, 80.987654321, 65.111111111, 90.999999999, 44.444444444]
        self.assertEqual(formula_b(values), formula_b(values))
        self.assertNotEqual(formula_b(values), formula_b([round(v,2) for v in values]))
        for epsilon in [1e-5,1e-8]:
            self.assertLessEqual(abs(formula_b([75+epsilon,75-epsilon,80,90,60])-formula_b([75]*2+[80,90,60])), epsilon)
