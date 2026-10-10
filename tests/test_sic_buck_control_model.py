"""Tests for automation.kicad_tools.sic_buck_control_model.

Pure-Python checks (build, references, mezzanine contract, baseline DSP pin map, fault-logic
values, ERC pre-check, BOM rows) always run. The pad/net mapping check against the installed
KiCad 10 footprint library skips when no KiCad library is reachable; a skip is never a pass.
"""
import unittest
from collections import Counter

from automation.kicad_tools import project_footprints as pf
from automation.kicad_tools import sic_buck_common as common
from automation.kicad_tools import sic_buck_control_model as model
from automation.kicad_tools.project_schematic import PIN_TYPES, analyse_connectivity

REQUIRED_KEYS = ('ref', 'value', 'footprint', 'nets', 'page', 'kind', 'mpn', 'maker', 'source', 'pins', 'note', 'board', 'dnp')


def library_installed():
    return pf.footprint_available('Package_QFP', 'LQFP-176_24x24mm_P0.5mm')


class ControlModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuit = model.build()
        cls.parts = cls.circuit.parts

    def test_builds_a_control_board_of_the_expected_size(self):
        self.assertTrue(180 <= len(self.parts) <= 300, len(self.parts))
        self.assertTrue(all(p['board'] == 'control' for p in self.parts))
        self.assertTrue(all(p['page'] in model.PAGES for p in self.parts))
        for key in REQUIRED_KEYS:
            self.assertTrue(all(key in p for p in self.parts), key)
        self.assertTrue(all(p['footprint'].count(':') == 1 for p in self.parts))
        self.assertEqual(model.CUSTOM_FOOTPRINTS, {})

    def test_references_are_unique_and_pins_match_nets(self):
        refs = [p['ref'] for p in self.parts]
        self.assertEqual(len(refs), len(set(refs)), Counter(refs).most_common(3))
        for p in self.parts:
            self.assertEqual(set(p['pins']), set(p['nets']), p['ref'])
            for n, pin in p['pins'].items():
                self.assertIn(pin['type'], PIN_TYPES, (p['ref'], n))
                if pin['type'] == 'no_connect':
                    self.assertIsNone(p['nets'][n], (p['ref'], n))

    def test_mezzanine_header_uses_the_shared_pin_assignment(self):
        headers = [p for p in self.parts if p['footprint'].endswith('PinHeader_2x25_P2.54mm_Vertical')]
        self.assertEqual(len(headers), 1)
        nets = headers[0]['nets']
        self.assertEqual(set(nets), {str(i) for i in range(1, 51)})
        for pin, net in nets.items():
            self.assertEqual(net, common.mezzanine_net(pin), pin)
        self.assertEqual(sum(1 for n in nets.values() if n == 'GND_CTRL'), 24)
        used = Counter(n for p in self.parts for n in p['nets'].values() if n)
        for pin in range(1, 51):
            self.assertGreaterEqual(used[common.mezzanine_net(str(pin))], 2, pin)  # every mezzanine net is used on the board

    def test_dsp_follows_the_baseline_pin_map(self):
        dsp = next(p for p in self.parts if p['kind'] == 'DSP')
        self.assertEqual(len(dsp['pins']), 176)
        for label, pin, _function in common.decisions()['controller']['dsp_pin_map']:
            token = label.split()[0]
            self.assertEqual(dsp['nets'][str(pin)], model.BASELINE_SIGNAL_NET.get(token, token), label)
        self.assertEqual(len([p for p in self.parts if p.get('near_dsp_pin')]), 26)
        self.assertEqual(dsp['nets']['104'], 'GND_CTRL')  # X1 grounded with the 3.3 V oscillator on XCLKIN
        self.assertIsNone(dsp['nets']['102'])  # X2 open
        self.assertEqual(dsp['nets']['105'], 'CLK30')

    def test_fault_logic_values_and_polarities_follow_the_baseline(self):
        resistors = Counter((p['value'], p['nets']['1'], p['nets']['2']) for p in self.parts if p['kind'] == 'R')
        for expected in (('953', 'REF2V5', 'OVP_OUT_REF'), ('10k', 'OVP_OUT_REF', 'GND_CTRL'), ('1k', 'REF2V5', 'OVP_IN_REF'), ('11k', 'OVP_IN_REF', 'GND_CTRL'),
                         ('1k', 'REF2V5', 'UVLO_REF'), ('1.91k', 'UVLO_REF', 'GND_CTRL'), ('21.5k', 'UVLO', 'UVLO_REF'), ('32.4k', 'REF3V0', 'OTP_REF'),
                         ('6.04k', 'EFUSE_ILIM', 'EFUSE_RTN'), ('14.7k', 'I12V_MON', 'EFUSE_RTN'), ('107k', '12V_IN', 'EFUSE_UVLO'),
                         ('4.42k', 'EFUSE_UVLO', 'EFUSE_OVP'), ('101k', '5V', 'MON5'), ('18.2k', '1V9', 'FB19'), ('30.1k', 'FB19', 'GND_CTRL'),
                         ('150k', '12V_PROT', 'V12V_MON'), ('33.2k', 'V12V_MON', 'GND_CTRL'), ('2.2k', 'REF3V0', 'TEMP_HS_NTC'), ('10k', 'ESTOP_N', 'GND_CTRL')):
            self.assertEqual(resistors[expected], 1, expected)
        self.assertEqual(resistors[('22k', 'ADCRESEXT', 'GND_CTRL')], 1)
        inverter = next(p for p in self.parts if p['mpn'] == 'SN74LV04APWR')
        self.assertEqual((inverter['nets']['1'], inverter['nets']['2']), ('UVLO', 'UVLO_N'))
        self.assertEqual((inverter['nets']['3'], inverter['nets']['4']), ('PG_BIAS_H_N', 'PG_BIAS_H_OK'))
        latch = next(p for p in self.parts if p['mpn'] == 'SN74LVC1G74DCTR')
        self.assertEqual((latch['nets']['1'], latch['nets']['5'], latch['nets']['6']), ('ARM', 'FAULT_N', 'FAULT_LATCH_N'))
        self.assertEqual(len([p for p in self.parts if p['mpn'] == 'SN74LV21APWR']), 3)
        self.assertEqual(len([p for p in self.parts if p['mpn'] == 'TLV1702AIDGKR']), 2)
        self.assertEqual([p['nets']['1'] for p in self.parts if p['dnp']], ['UVLO_REF'])

    def test_connectivity_precheck_is_clean(self):
        report = analyse_connectivity(self.parts, model.FLAG_NETS)
        self.assertEqual(report['undriven_power_nets'], [])
        self.assertEqual(report['pin_conflicts'], [])
        self.assertEqual(report['no_connect_pins_with_nets'], [])
        self.assertEqual(report['single_pin_nets'], [])
        for p in self.parts:  # the eFuse RTN reference must never be bridged to the system ground
            if len(p['nets']) == 2:
                self.assertNotEqual(set(p['nets'].values()), {'EFUSE_RTN', 'GND_CTRL'}, p['ref'])

    def test_bom_rows_have_the_required_columns(self):
        rows = model.bom_rows(self.circuit)
        self.assertEqual(len(rows), len(self.parts))
        self.assertEqual(list(rows[0]), ['reference', 'value', 'manufacturer', 'mpn', 'footprint', 'datasheet', 'dnp', 'note'])
        for row in rows:
            if not row['reference'].startswith(('TP', 'H')):
                self.assertTrue(row['mpn'], row['reference'])
        self.assertEqual(sum(1 for r in rows if r['dnp'] == 'yes'), 1)
        ics = {p['mpn'] for p in self.parts if p['kind'] in ('IC', 'DSP')}
        self.assertTrue(ics <= set(model.PINOUT_SOURCES), ics - set(model.PINOUT_SOURCES))

    @unittest.skipUnless(library_installed(), 'installed KiCad footprint library not available')
    def test_pad_mapping_validates_against_installed_footprints(self):
        self.assertEqual(pf.validate_pad_mapping(self.parts, custom_footprints=model.CUSTOM_FOOTPRINTS), [])


if __name__ == '__main__':
    unittest.main()
