"""Tests for automation.kicad_tools.sic_buck_power_model (V2 power board).

Pure-Python checks always run: the model builds deterministically, references are unique,
every mezzanine pin carries the net name of sic_buck_common.mezzanine_net, Kelvin-source nets
stay separate from the power-source nets, the baseline values are present, the ERC pre-check
of project_schematic is clean with the declared PWR_FLAG nets, and the custom footprints parse
with the expected pad numbers.  Checks that need the installed KiCad footprint library or
KiCad's bundled Python (pcbnew) skip when they are unavailable; a skip is never a pass.
"""

import json
import os
import re
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from automation.kicad_tools import project_footprints as pf
from automation.kicad_tools import sic_buck_power_model as model
from automation.kicad_tools.project_schematic import PIN_TYPES, analyse_connectivity
from automation.kicad_tools.sic_buck_common import mezzanine_net
from automation.setup.detect_kicad import find_kicad_cli, read_config

PCBNEW_SCRIPT = '''
import json, sys
try:
    import pcbnew
except ImportError as error:
    print(json.dumps({"skip": str(error)}))
    sys.exit(0)
root, result = sys.argv[1], {}
for name in sys.argv[2:]:
    fp = pcbnew.FootprintLoad(root, name)
    result[name] = None if fp is None else sorted({p.GetNumber() for p in fp.Pads() if p.GetNumber()}, key=lambda s: int(s))
print(json.dumps(result))
'''


def kicad_python():
    """KiCad's bundled interpreter (where pcbnew lives), or None."""
    try:
        cli = find_kicad_cli()
    except FileNotFoundError:
        return None
    if not cli:
        return None
    configured = read_config().get('kicad_python')
    candidates = ([Path(os.path.expandvars(configured)).expanduser()] if configured else []) + [
        cli.parent / 'python.exe', cli.parent / 'python3', cli.parent / 'python']
    return next((p for p in candidates if p.is_file()), None)


def library_installed():
    return pf.footprint_available('Package_TO_SOT_THT', 'TO-247-4_Vertical')


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = model.build().parts
        cls.by_ref = {p['ref']: p for p in cls.parts}

    def test_builds_deterministically_within_the_expected_size(self):
        again = model.build().parts
        self.assertEqual(self.parts, again)
        self.assertTrue(200 <= len(self.parts) <= 260, len(self.parts))
        self.assertEqual(len(self.by_ref), len(self.parts), 'duplicate references')
        for p in self.parts:
            with self.subTest(ref=p['ref']):
                self.assertEqual(p['board'], 'power')
                self.assertIn(p['page'], model.PAGES)
                self.assertEqual(p['footprint'].count(':'), 1)
                self.assertEqual(set(p['nets']), set(p['pins']))
                for pin in p['pins'].values():
                    self.assertIn(pin['type'], PIN_TYPES)
                if p.get('dnp'):
                    self.assertTrue(p['footprint'], 'DNP parts keep their footprint')

    def test_mezzanine_socket_uses_the_shared_pin_assignment(self):
        sockets = [p for p in self.parts if 'PinSocket_2x25' in p['footprint']]
        self.assertEqual(len(sockets), 1)
        nets = sockets[0]['nets']
        self.assertEqual(set(nets), {str(n) for n in range(1, 51)})
        for pin, net in nets.items():
            self.assertEqual(net, mezzanine_net(pin), pin)
        self.assertEqual(sum(1 for n in nets.values() if n == 'GND_CTRL'), 24)

    def test_kelvin_source_nets_are_never_joined_to_power_source_nets(self):
        power = {'SW', 'PGND', 'VIN', 'VIN_RAW', 'VOUT', 'VOUT_L'}
        for p in self.parts:
            nets = set(p['nets'].values())
            if p['kind'] == 'Q':
                continue
            for ks in ('KS_H', 'KS_L'):
                if ks in nets:
                    self.assertFalse(nets & power, (p['ref'], nets))
        q1, q2 = self.by_ref['Q1'], self.by_ref['Q2']
        self.assertEqual(q1['nets'], {'1': 'VIN', '2': 'SW', '3': 'KS_H', '4': 'G_H'})
        self.assertEqual(q2['nets'], {'1': 'SW', '2': 'PGND', '3': 'KS_L', '4': 'G_L'})
        self.assertEqual({p['name'] for p in q1['pins'].values()}, {'D', 'S', 'KS', 'G'})

    def test_baseline_values_are_honoured(self):
        values = Counter((p['kind'], p['value'], p['footprint'].rsplit(':', 1)[1], bool(p.get('dnp'))) for p in self.parts)
        self.assertEqual(values[('R', '10', 'R_1206_3216Metric', False)], 2, 'R_ON 10 ohm per channel')
        self.assertEqual(values[('R', '3.3', 'R_1206_3216Metric', False)], 2, 'R_OFF 3.3 ohm per channel')
        self.assertEqual(values[('R', '2.2k', 'R_1206_3216Metric', False)], 2, 'DESAT R1')
        self.assertEqual(values[('R', '4.99k', 'R_0603_1608Metric', False)], 2, 'DESAT R2')
        self.assertEqual(values[('C', '680p/50V', 'C_0603_1608Metric', False)], 2, 'DESAT blanking')
        self.assertEqual(values[('C', '0.47u/630V', 'C_2220_5750Metric', False)], 10, 'HF ceramic tier')
        self.assertEqual(values[('C', '0.47u/630V', 'C_2220_5750Metric', True)], 2, 'damping leg DNP')
        self.assertEqual(values[('R', '120k', 'R_2512_6332Metric', False)], 3, 'input bleeder')
        self.assertEqual(values[('R', '100k', 'R_2512_6332Metric', False)], 2, 'output bleeder')
        self.assertEqual(values[('R', '150k', 'R_1206_3216Metric', False)], 3, 'input indicator string')
        self.assertEqual(values[('R', '100k', 'R_1206_3216Metric', False)], 2, 'output indicator string')
        self.assertEqual(sum(1 for p in self.parts if p['mpn'] == 'B32776G8206K000'), 2)
        self.assertEqual(sum(1 for p in self.parts if p['mpn'] == 'B32776G4606K000'), 2)
        self.assertEqual(sum(1 for p in self.parts if p['mpn'] == 'UCC21710QDWRQ1'), 2)
        self.assertEqual(sum(1 for p in self.parts if p['mpn'] == 'UCC14141QDWNRQ1'), 3)
        self.assertEqual(sum(1 for p in self.parts if p['mpn'] == 'AMC1311BDWVR'), 2)
        self.assertEqual(sum(1 for p in self.parts if p['mpn'] == 'C4MS025120K'), 2)
        oc_divider = [p for p in self.parts if {'REF2V5_PB', 'VOC_SET'} <= set(p['nets'].values())]
        self.assertEqual([p['value'] for p in oc_divider], ['2.32k'])
        self.assertEqual([p['value'] for p in self.parts if set(p['nets'].values()) == {'VOC_SET', 'GND_CTRL'} and p['kind'] == 'R'], ['1k'])
        bias = self.by_ref['U2']
        self.assertEqual(bias['nets']['28'], 'VDD_H')
        self.assertEqual(bias['nets']['19'], 'VEE_H')
        self.assertEqual(bias['nets']['4'], 'BIAS_EN_F')
        sensor = self.by_ref['U10']
        self.assertEqual((sensor['nets']['1'], sensor['nets']['2'], sensor['nets']['6'], sensor['nets']['7'], sensor['nets']['8']),
                         ('VOUT_L', 'VOUT', 'ISENSE', 'OC_N', 'VOC_SET'))
        driver = self.by_ref['U1']
        self.assertEqual((driver['nets']['10'], driver['nets']['11'], driver['nets']['3'], driver['nets']['1']), ('PWM_H_F', 'PWM_L_F', 'KS_H', 'KS_H'))
        self.assertEqual((self.by_ref['U3']['nets']['10'], self.by_ref['U3']['nets']['11']), ('PWM_L_F', 'PWM_H_F'))
        self.assertGreaterEqual(sum(1 for p in self.parts if p.get('dnp')), 12)

    def test_erc_precheck_is_clean_with_the_declared_flag_nets(self):
        report = analyse_connectivity(self.parts, model.FLAG_NETS)
        self.assertEqual(report['pin_conflicts'], [])
        self.assertEqual(report['undriven_power_nets'], [])
        self.assertEqual(report['single_pin_nets'], [])
        self.assertEqual(report['no_connect_pins_with_nets'], [])
        nets = model.nets_of(self.parts)
        self.assertTrue(set(model.FLAG_NETS) <= nets, set(model.FLAG_NETS) - nets)
        self.assertTrue(set(model.HV_INTERMEDIATE_NETS) <= nets, set(model.HV_INTERMEDIATE_NETS) - nets)
        for net in ('VIN_RAW', 'VIN', 'SW', 'VOUT_L', 'VOUT', 'PGND', 'G_H', 'KS_H', 'VDD_H', 'VEE_H', 'DESAT_H_A', 'DESAT_H_OC',
                    'G_L', 'KS_L', 'VDD_L', 'VEE_L', 'DESAT_L_A', 'DESAT_L_OC', '5V_ISO', 'ISO_15V', 'VIN_DIV', 'VOUT_DIV',
                    '12V_PROT', '3V3', 'GND_CTRL', 'PWM_H_F', 'PWM_L_F', 'RESET_N', 'BIAS_EN', 'RELAY_ON', 'FLT_H_N', 'FLT_L_N',
                    'RDY_H', 'RDY_L', 'OC_N', 'FAN_TACH', 'PG_BIAS_H_N', 'PG_BIAS_L_N', 'PG_BIAS_S_N', 'FAULT_N', 'SPARE_D1',
                    'SPARE_D2', 'ISENSE', 'ISENSE_REF', 'VIN_SENSE', 'VOUT_SENSE', 'VOC_SET', 'REF2V5_PB', 'K1_LOW', 'PE'):
            self.assertIn(net, nets)

    def test_every_ic_and_transistor_has_a_recorded_pinout_source(self):
        for p in self.parts:
            if p['kind'] in ('IC', 'Q'):
                with self.subTest(ref=p['ref']):
                    self.assertIn(p['mpn'], model.PINOUT_SOURCES)

    def test_custom_footprints_parse_with_the_expected_pads(self):
        expected = {
            model.CUSTOM_NAMES['c_in']: ['1', '2'], model.CUSTOM_NAMES['c_out']: ['1', '2'], model.CUSTOM_NAMES['toroid']: ['1', '2'],
            model.CUSTOM_NAMES['heatsink']: [], model.CUSTOM_NAMES['ucc14141']: [str(n) for n in range(1, 37)],
            model.CUSTOM_NAMES['amc1311']: [str(n) for n in range(1, 9)], model.CUSTOM_NAMES['tmcs1133']: [str(n) for n in range(1, 11)],
            model.CUSTOM_NAMES['ptc']: ['1', '2'], model.CUSTOM_NAMES['ucc21710']: [str(n) for n in range(1, 17)]}
        self.assertEqual(set(model.CUSTOM_FOOTPRINTS), set(expected))
        for name, value in model.CUSTOM_FOOTPRINTS.items():
            with self.subTest(name=name):
                self.assertTrue(pf.NAME_PATTERN.fullmatch(name))
                text, boxes = value
                pads = pf.pads_in_text(text)
                self.assertEqual(pf.pad_numbers(pads), expected[name])
                self.assertTrue(boxes)
        film = pf.pads_in_text(model.CUSTOM_FOOTPRINTS[model.CUSTOM_NAMES['c_in']][0])
        self.assertEqual({tuple(p['at']) for p in film}, {(-18.75, -5.1), (-18.75, 5.1), (18.75, -5.1), (18.75, 5.1)})
        toroid = pf.pads_in_text(model.CUSTOM_FOOTPRINTS[model.CUSTOM_NAMES['toroid']][0])
        self.assertEqual([p['type'] for p in toroid], ['thru_hole', 'thru_hole'] + ['np_thru_hole'] * 4)
        self.assertEqual({tuple(p['at']) for p in toroid if p['type'] == 'np_thru_hole'}, {(-30.0, -30.0), (-30.0, 30.0), (30.0, -30.0), (30.0, 30.0)})
        for key, length in (('ucc14141', 17.5), ('amc1311', 10.8), ('tmcs1133', 15.5), ('ucc21710', 16.6)):
            slots = [p for p in pf.pads_in_text(model.CUSTOM_FOOTPRINTS[model.CUSTOM_NAMES[key]][0]) if p['type'] == 'np_thru_hole']
            self.assertEqual([(p['shape'], p['drill']) for p in slots], [('oval', [1.2, length])], key)
        tmcs = {p['number']: p for p in pf.pads_in_text(model.CUSTOM_FOOTPRINTS[model.CUSTOM_NAMES['tmcs1133']][0]) if p['number']}
        self.assertEqual((tmcs['1']['size'], tmcs['1']['at']), ([3.0, 4.41], [-5.375, -2.54]))
        self.assertEqual(tmcs['3']['at'][1], 4.445)
        self.assertEqual(tmcs['10']['at'][1], -4.445)

    def test_written_circuit_json_matches_the_module(self):
        if not model.CIRCUIT_JSON.exists():
            self.skipTest('design/circuit_power.json not written yet')
        written = json.loads(model.CIRCUIT_JSON.read_text(encoding='utf-8'))
        self.assertEqual(written, self.parts)
        self.assertTrue(model.BOM_CSV.exists())
        header = model.BOM_CSV.read_text(encoding='utf-8').splitlines()[0]
        self.assertEqual(header, 'reference,value,manufacturer,mpn,footprint,datasheet,dnp,note')

    @unittest.skipUnless(library_installed(), 'installed KiCad footprint library required')
    def test_pad_mapping_validates_against_the_installed_library(self):
        self.assertEqual(pf.validate_pad_mapping(self.parts, custom_footprints=model.CUSTOM_FOOTPRINTS), [])

    @unittest.skipUnless(kicad_python(), 'KiCad Python (pcbnew) required')
    def test_custom_footprints_load_in_pcbnew(self):
        with tempfile.TemporaryDirectory(prefix='aipe power fp ') as temp:
            lib = Path(temp) / 'AIPE.pretty'
            lib.mkdir()
            for name, value in model.CUSTOM_FOOTPRINTS.items():
                (lib / f'{name}.kicad_mod').write_text(pf.custom_text(value), encoding='utf-8')
            script = Path(temp) / 'load.py'
            script.write_text(PCBNEW_SCRIPT, encoding='utf-8')
            run = subprocess.run([str(kicad_python()), str(script), str(lib), *model.CUSTOM_FOOTPRINTS], capture_output=True, text=True, timeout=300)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout.strip().splitlines()[-1])
            if 'skip' in result:
                self.skipTest(result['skip'])
            for name, pads in result.items():
                with self.subTest(name=name):
                    self.assertIsNotNone(pads, 'FootprintLoad returned None')
                    expected = pf.pad_numbers(pf.pads_in_text(pf.custom_text(model.CUSTOM_FOOTPRINTS[name])))
                    self.assertEqual(sorted(pads, key=int), sorted(expected, key=int))


if __name__ == '__main__':
    unittest.main()
