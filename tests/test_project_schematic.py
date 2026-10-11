"""Tests for the parametrised schematic/project writer.

Everything except the last class runs without KiCad; symbol extraction then falls back to generated
symbols and the tests assert that this is reported rather than hidden. The native ERC test skips
when kicad-cli is unavailable; a skip is not a pass and the smoke evidence stays with the run.
"""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.kicad_tools import project_schematic as ps
from automation.kicad_tools.native_schematic import children, parse, pins
from automation.kicad_tools.run_check import run_check
from automation.setup.detect_kicad import find_kicad_cli


def kicad_cli():
    try:
        return find_kicad_cli()
    except FileNotFoundError:
        return None


def pin_defs(text):
    return {n: dict(name=a, type=b) for n, a, b in (s.split(':') for s in text.split())}


TWO = pin_defs('1:1:passive 2:2:passive')


def part(ref, kind, nets, pins=None, page='p1', footprint='Resistor_SMD:R_0805_2012Metric', **extra):
    return dict(ref=ref, value=extra.pop('value', kind), footprint=footprint, kind=kind, page=page, nets=dict(nets),
                pins=copy.deepcopy(pins) if pins else {k: dict(name=k, type='passive') for k in nets}, **extra)


def small_spec(root, **overrides):
    parts = [part('U1', 'IC', {'1': 'A', '2': 'B', '3': 'VCC', '4': 'GND', '5': None},
                  pin_defs('1:IN:input 2:OUT:output 3:VCC:power_in 4:GND:power_in 5:NC:no_connect'),
                  footprint='Package_TO_SOT_SMD:SOT-23-5'),
             part('R1', 'R', {'1': 'A', '2': 'B'}, TWO), part('C1', 'C', {'1': 'VCC', '2': 'GND'}, TWO, page='p2'),
             part('Q1', 'Q', {'1': 'B', '2': 'VCC', '3': 'GND'}, pin_defs('1:G:input 2:D:passive 3:S:passive'), page='p2',
                  footprint='Package_TO_SOT_THT:TO-247-3_Vertical')]
    spec = dict(name='T', title='t', kicad_dir=root / 'kicad', design_dir=root / 'design',
                pages={'p1': 'Page one', 'p2': 'Page two'}, parts=parts, flag_nets=['VCC', 'GND'], flag_page='p2',
                net_classes=[dict(name='PWR', clearance=0.5, track_width=1.0, via_diameter=1.0, via_drill=0.5, nets=['VCC', 'GND'])])
    spec.update(overrides)
    return spec


def sheet_items(path):
    tree = parse(path.read_text(encoding='utf-8'))
    return tree, children(tree, 'symbol'), children(tree, 'global_label'), children(tree, 'no_connect')


class HelperTests(unittest.TestCase):
    def test_grid_and_number_formatting(self):
        self.assertEqual(ps.snap(38.1 + 124.46 / 2), 100.33)
        self.assertEqual(ps.num(114.30000000000001), '114.3')
        self.assertEqual(ps.num(5.0), '5')
        self.assertEqual([ps.pin_key(n) for n in ('10', '2', 'A1')], [(0, 10, ''), (0, 2, ''), (1, 0, 'A1')])

    def test_pin_name_normalisation(self):
        self.assertEqual(ps.normalise_pin_name('1', '1'), '')
        self.assertEqual(ps.normalise_pin_name('~', '2'), '')
        self.assertEqual(ps.normalise_pin_name('Cathode', '1'), 'K')
        self.assertEqual(ps.normalise_pin_name('DS', '2'), 'K')

    def test_default_unit_grouping_partitions_and_chunks(self):
        pins_ = {}
        nets = {}
        for i in range(1, 201):
            name = 'VDD' if i <= 20 else 'ADCIN%d' % i if i <= 40 else 'GPIO%d' % i
            pins_[str(i)] = dict(name=name, type='power_in' if i <= 20 else 'input')
            nets[str(i)] = None if 120 < i <= 200 else 'N%d' % i
        groups = ps.default_unit_grouping(dict(kind='DSP', pins=pins_, nets=nets))
        self.assertEqual(sorted(n for g in groups for n in g), sorted(pins_))
        self.assertTrue(all(len(g) <= ps.MAX_UNIT_PINS for g in groups))
        # supply 20, ADC 20, connected 80 -> 64 + 16, unused 80 -> 64 + 16
        self.assertEqual([len(g) for g in groups], [20, 20, 64, 16, 64, 16])
        self.assertEqual(ps.default_unit_grouping(dict(kind='IC', pins={'1': {}, '2': {}}, nets={})), [['1', '2']])

    def test_fet_roles_and_candidates(self):
        q = part('Q1', 'Q', {'1': 'a', '2': 'b', '3': 'c', '4': 'd'}, pin_defs('1:G:input 2:D:passive 3:S:passive 4:KS:passive'))
        self.assertEqual(ps.fet_roles(q), {'1': 'G', '2': 'D', '3': 'S', '4': 'K'})
        spec = ps.coerce_spec(small_spec(Path('x')))
        self.assertEqual(ps.official_candidates(q, spec), [('Transistor_FET', 'Q_NMOS_GDSK'), ('Transistor_FET', 'Q_NMOS_GDSS')])
        bjt = part('Q2', 'Q', {'1': 'a', '2': 'b', '3': 'c'}, pin_defs('1:B:input 2:E:passive 3:C:passive'))
        self.assertIsNone(ps.fet_roles(bjt))
        self.assertEqual(ps.official_candidates(bjt, spec), [])
        d = part('D1', 'D', {'1': 'x', '2': 'y'}, pin_defs('1:K:passive 2:A:passive'), value='SMCJ400A')
        self.assertEqual(ps.official_candidates(d, spec), [('Device', 'D_Zener')])
        d['value'] = 'C4D20120D SiC'
        self.assertEqual(ps.diode_variant(d), 'D_Schottky')

    def test_generated_symbols_carry_every_pin_with_its_type(self):
        q = part('Q1', 'Q', {'1': 'a', '2': 'b', '3': 'c', '4': 'd'}, pin_defs('1:G:input 2:D:passive 3:S:passive 4:KS:passive'))
        definition, extents, source = ps.fet_symbol(q, ps.fet_roles(q), 'Sym_Q1')
        self.assertEqual(source, 'generated:fet')
        self.assertEqual({(p['number'], p['name'], p['type']) for p in pins(definition)},
                         {('1', 'G', 'input'), ('2', 'D', 'passive'), ('3', 'S', 'passive'), ('4', 'KS', 'passive')})
        ic = part('U1', 'IC', {str(n): 'N' for n in range(1, 17)}, pin_defs(' '.join(f'{n}:P{n}:input' for n in range(1, 17))))
        definition, extents, source = ps.generic_symbol(ic, [[str(n) for n in range(1, 17)]], 'Sym_U1')
        self.assertEqual(len(pins(definition)), 16)
        self.assertEqual(extents, [(38.1, 22.86)])
        d = part('D1', 'D', {'1': 'x', '2': 'y'}, pin_defs('1:A:passive 2:K:passive'))
        self.assertEqual(ps.diode_symbol(d, 'Sym_D1')[2], 'generated:diode')
        self.assertIsNone(ps.diode_symbol(part('D2', 'D', {'1': 'x', '2': 'y'}, TWO), 'Sym_D2'))

    def test_connectivity_pre_check_mirrors_kicad_matrix(self):
        parts = [part('U1', 'IC', {'1': 'OUT', '2': 'VCC', '3': 'X'}, pin_defs('1:O:output 2:VCC:power_in 3:NC:no_connect')),
                 part('U2', 'IC', {'1': 'OUT', '2': 'VCC'}, pin_defs('1:O:output 2:VCC:power_in')),
                 part('R1', 'R', {'1': 'OUT', '2': 'LONE'}, TWO)]
        report = ps.analyse_connectivity(parts)
        self.assertEqual(report['undriven_power_nets'], ['VCC'])
        self.assertEqual(report['single_pin_nets'], ['LONE', 'X'])
        self.assertEqual(report['no_connect_pins_with_nets'], ['U1.3'])
        self.assertIn(dict(net='OUT', a='U1.1', b='U2.1', severity='error'), report['pin_conflicts'])
        flagged = ps.analyse_connectivity(parts, ['VCC'])
        self.assertEqual(flagged['undriven_power_nets'], [])
        self.assertTrue(any(c['net'] == 'OUT' and c['severity'] == 'error' for c in ps.analyse_connectivity(parts, ['OUT'])['pin_conflicts']))

    def test_project_settings_and_dru(self):
        classes = ps.coerce_spec(small_spec(Path('x'))).net_classes
        settings = ps.project_settings('T', classes, {'min_clearance': 0.3})
        names = [c['name'] for c in settings['net_settings']['classes']]
        self.assertEqual(names, ['Default', 'PWR'])
        for c in settings['net_settings']['classes']:
            for key in ('name', 'clearance', 'track_width', 'via_diameter', 'via_drill', 'diff_pair_gap', 'diff_pair_via_gap', 'diff_pair_width'):
                self.assertIn(key, c)
        self.assertEqual(settings['net_settings']['netclass_patterns'],
                         [{'netclass': 'PWR', 'pattern': 'VCC'}, {'netclass': 'PWR', 'pattern': 'GND'}])
        self.assertEqual(settings['board']['design_settings']['rules']['min_clearance'], 0.3)
        self.assertEqual(settings['board']['design_settings']['rules']['min_track_width'], ps.DEFAULT_RULES['min_track_width'])
        self.assertTrue(ps.normalise_dru('(rule "x" (constraint clearance (min 1mm)))').startswith('(version 1)\n(rule'))
        with self.assertRaises(ValueError):
            ps.normalise_dru('(rule "x" (constraint clearance (min 1mm))')

    def test_spec_validation(self):
        with self.assertRaises(ValueError):
            ps.coerce_spec(small_spec(Path('x'), bogus=1))
        with self.assertRaises(ValueError):
            ps.coerce_spec(small_spec(Path('x'), flag_page='nope'))
        bad = small_spec(Path('x'))
        bad['parts'].append(part('R1', 'R', {'1': 'A', '2': 'B'}, TWO))
        with self.assertRaises(ValueError):
            ps.coerce_spec(bad)
        bad = small_spec(Path('x'))
        bad['parts'][1]['pins']['1']['type'] = 'magic'
        with self.assertRaises(ValueError):
            ps.coerce_spec(bad)
        raw = small_spec(Path('x'))
        raw['parts'][0]['nets'] = {1: 'A', 2: 'B', 3: 'VCC', 4: 'GND', 5: None}
        raw['parts'][0]['pins'] = {int(k): v for k, v in raw['parts'][0]['pins'].items()}
        spec = ps.coerce_spec(raw)
        self.assertEqual([c['name'] for c in spec.net_classes], ['Default', 'PWR'])
        self.assertEqual(list(spec.parts[0]['nets']), ['1', '2', '3', '4', '5'])
        self.assertEqual(list(raw['parts'][0]['nets']), [1, 2, 3, 4, 5], 'caller model must not be mutated')


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aipe sch ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_generated_project_parses_and_maps_every_part(self):
        result = ps.generate_project(small_spec(self.root, dru_text='(rule "a" (constraint clearance (min 1mm)))'))
        kicad = self.root / 'kicad'
        for name in ('T.kicad_sch', 'p1.kicad_sch', 'p2.kicad_sch', 'T.kicad_pro', 'T.kicad_dru', 'sym-lib-table', 'libraries/AIPE.kicad_sym'):
            self.assertTrue((kicad / name).is_file(), name)
        self.assertFalse((kicad / 'fp-lib-table').exists())
        for sheet in ('T', 'p1', 'p2'):
            tree = parse((kicad / f'{sheet}.kicad_sch').read_text(encoding='utf-8'))
            self.assertEqual(tree[0], 'kicad_sch')
        parse((kicad / 'libraries/AIPE.kicad_sym').read_text(encoding='utf-8'))
        mapping = json.loads(Path(result['mapping']).read_text(encoding='utf-8'))
        self.assertEqual(set(mapping['paths']), {'U1', 'R1', 'C1', 'Q1'})
        self.assertEqual(set(mapping['placement']), {'U1', 'R1', 'C1', 'Q1'})
        self.assertTrue(all(p.startswith('/' + mapping['root_uuid'] + '/') for p in mapping['paths'].values()))
        self.assertEqual([s['key'] for s in mapping['sheets']], ['p1', 'p2'])
        self.assertEqual(result['parts_placed'], 4)
        self.assertEqual(result['diagnostics']['undriven_power_nets'], [])
        # Every model pin is wired to a global label or marked no-connect; flags sit on the flag page.
        _, symbols, labels, no_connects = sheet_items(kicad / 'p1.kicad_sch')
        self.assertEqual(len(symbols), 2)
        self.assertEqual(sorted(l[1] for l in labels), ['A', 'A', 'B', 'B', 'GND', 'VCC'])
        self.assertEqual(len(no_connects), 1)
        _, symbols, labels, _ = sheet_items(kicad / 'p2.kicad_sch')
        self.assertEqual(len(symbols), 4)
        self.assertEqual(sorted(l[1] for l in labels), ['B', 'GND', 'GND', 'GND', 'VCC', 'VCC', 'VCC'])
        project = json.loads((kicad / 'T.kicad_pro').read_text(encoding='utf-8'))
        self.assertEqual([c['name'] for c in project['net_settings']['classes']], ['Default', 'PWR'])
        self.assertEqual(len(project['net_settings']['netclass_patterns']), 2)
        self.assertTrue((kicad / 'T.kicad_dru').read_text(encoding='utf-8').startswith('(version 1)'))

    def test_outputs_are_deterministic(self):
        first, second = self.root / 'a', self.root / 'b'
        ps.generate_project(small_spec(first))
        ps.generate_project(small_spec(second))
        for path in sorted((first / 'kicad').rglob('*')):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (second / 'kicad' / path.relative_to(first / 'kicad')).read_bytes(), path.name)

    def test_full_page_overflows_onto_continuation_sheets(self):
        parts = [part(f'U{i}', 'IC', {str(n): f'N{n}' for n in range(1, 17)},
                      pin_defs(' '.join(f'{n}:P{n}:passive' for n in range(1, 17))), footprint='Package_SO:SOIC-16_3.9x9.9mm_P1.27mm')
                 for i in range(1, 41)]
        result = ps.generate_project(small_spec(self.root, parts=parts, flag_nets=[], pages={'p1': 'Many'}, flag_page='p1'))
        self.assertTrue(result['continuation_sheets'])
        self.assertEqual(result['continuation_sheets'][0], 'p1_2')
        self.assertEqual(result['parts_placed'], 40)
        mapping = json.loads(Path(result['mapping']).read_text(encoding='utf-8'))
        placed_sheets = {entry['sheet'] for entries in mapping['placement'].values() for entry in entries}
        self.assertEqual(placed_sheets, {s['key'] for s in mapping['sheets']})
        root = parse((self.root / 'kicad/T.kicad_sch').read_text(encoding='utf-8'))
        sheets = children(root, 'sheet')
        self.assertEqual(len(sheets), len(mapping['sheets']))
        names = [next(p[2] for p in children(s, 'property') if p[1] == 'Sheetname') for s in sheets]
        self.assertEqual(len(set(names)), len(names))
        for key in mapping['sheets']:
            parse((self.root / 'kicad' / key['file']).read_text(encoding='utf-8'))

    def test_multi_unit_symbol_and_skipped_parts(self):
        pins_ = {str(i): dict(name='VDD' if i <= 4 else 'ADCIN%d' % i if i <= 8 else 'GPIO%d' % i,
                             type='power_in' if i <= 4 else 'input') for i in range(1, 25)}
        nets = {str(i): '3V3' if i <= 4 else 'GND' if i <= 8 else ('SIG%d' % i if i <= 16 else None) for i in range(1, 25)}
        parts = [part('U9', 'DSP', nets, pins_, footprint='Package_QFP:LQFP-176_24x24mm_P0.5mm'),
                 part('R1', 'R', {'1': 'SIG9', '2': 'SIG10'}, TWO), part('X1', 'IC', {'1': 'Z'}, page='elsewhere'),
                 part('X2', 'IC', {'1': 'Z'}, board='control')]
        result = ps.generate_project(small_spec(self.root, parts=parts, flag_nets=['3V3', 'GND'], flag_page='p1', board='power'))
        self.assertEqual(set(result['skipped']), {'X1', 'X2'})
        mapping = json.loads(Path(result['mapping']).read_text(encoding='utf-8'))
        self.assertEqual(mapping['symbols']['U9']['units'], 4)
        self.assertEqual([e['unit'] for e in mapping['placement']['U9']], [1, 2, 3, 4])
        _, symbols, _, no_connects = sheet_items(self.root / 'kicad/p1.kicad_sch')
        units = sorted(int(children(s, 'unit')[0][1]) for s in symbols if children(s, 'lib_id')[0][1] == 'AIPE:Sym_U9')
        self.assertEqual(units, [1, 2, 3, 4])
        self.assertEqual(len(no_connects), 8)

    def test_without_kicad_everything_is_generated_and_reported(self):
        with patch.object(ps, 'kicad_data_root', return_value=None):
            result = ps.generate_project(small_spec(self.root))
        self.assertIsNone(result['library_root'])
        self.assertEqual(result['symbol_fallbacks'], {'Q1': 'generated:fet'})
        mapping = json.loads(Path(result['mapping']).read_text(encoding='utf-8'))
        self.assertEqual(mapping['symbols']['Q1']['source'], 'generated:fet')
        self.assertEqual(mapping['symbols']['U1']['source'], 'generated:rectangle')

    def test_custom_grouping_must_partition_pins(self):
        with self.assertRaises(ValueError):
            ps.generate_project(small_spec(self.root, unit_grouping=lambda p: [list(p['pins'])[:1]]))


@unittest.skipUnless(kicad_cli(), 'kicad-cli not available; native ERC evidence requires KiCad')
class NativeErcTests(unittest.TestCase):
    def test_demo_project_has_zero_erc_findings(self):
        with tempfile.TemporaryDirectory(prefix='aipe erc ') as folder:
            root = Path(folder)
            result = ps.generate_project(ps.demo_spec(root / 'kicad', root / 'design'))
            self.assertEqual(result['diagnostics']['undriven_power_nets'], [])
            self.assertEqual(result['diagnostics']['pin_conflicts'], [])
            if result['library_root']:
                self.assertEqual(result['symbol_fallbacks'], {'Q1': 'generated:fet'})
            code, manifest = run_check('erc', Path(result['root']), root / 'checks')
            data = json.loads(manifest.read_text(encoding='utf-8'))
            self.assertEqual(data['status'], 'passed', data)
            self.assertEqual(code, 0)
            self.assertEqual(data['finding_count'], 0)
            self.assertEqual(data['tool_exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
