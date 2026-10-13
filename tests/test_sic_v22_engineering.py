"""Regression checks for the two independently identified V2.1 circuit errors."""
import unittest

from automation.kicad_tools import generate_sic_schematics as drawings
from automation.kicad_tools import sic_buck_power_model as power
from automation.scripts import calculate_sic_buck as calculation


class EngineeringCorrections(unittest.TestCase):
    def test_current_zero_reference_is_independent_of_3v3(self):
        parts = {p['ref']: p for p in power.build().parts}
        self.assertEqual(parts['R82']['nets'], {'1': 'REF2V5_PB', '2': 'ISENSE_REF'})
        self.assertEqual(parts['R83']['nets'], {'1': 'ISENSE_REF', '2': 'GND_CTRL'})
        self.assertEqual(parts['R82']['value'], '6.65k')
        self.assertEqual(parts['R83']['value'], '1.01k')
        self.assertLess(abs(2.5*1.01/7.66 - .330), .001)

    def test_explicit_connectivity_allowance_rejects_unrelated_change(self):
        base = {('R82','1'): '3V3', ('Q1','1'): 'VIN'}
        expected, refs = drawings.approved_release_map('power', base, {'R82','Q1'})
        self.assertEqual(base[('R82','1')], '3V3')
        self.assertTrue(drawings.compare_pad_maps(expected, expected)['exact'])
        broken = dict(expected); broken[('Q1','1')] = 'PGND'
        self.assertFalse(drawings.compare_pad_maps(expected, broken)['exact'])
        self.assertEqual(refs, {'R82','Q1'})

    def test_sense_midrail_uses_dual_positive_equation_and_rated_part(self):
        parts = {p['ref']: p for p in power.build().parts}
        self.assertEqual(parts['R57']['value'], '160')
        self.assertEqual(parts['R57']['mpn'], 'ERJP08F1600V')
        self.assertIn('1206', parts['R57']['footprint'])
        load = 2*calculation.I_AMC_VDD1_MAX + calculation.I_SENS_MISC
        self.assertAlmostEqual(load, .0204)
        limit = 5/load - calculation.R_LIM_INT
        self.assertAlmostEqual(calculation.bias_budget()['sensing_RLIM_max_ohm'], limit)
        self.assertLess(160*1.01, limit)
        self.assertGreater(1000, limit)


if __name__ == '__main__':
    unittest.main()
