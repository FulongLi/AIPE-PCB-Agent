"""Tests for automation.kicad_tools.project_footprints.

Pure-Python checks always run against a fake library root in a temporary
directory. Checks that need the installed KiCad footprint library or KiCad's
bundled Python (pcbnew) skip when they are unavailable; a skip is never a pass
and does not replace a real KiCad DRC of a generated board.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.kicad_tools import project_footprints as pf
from automation.setup.detect_kicad import find_kicad_cli, read_config

TO247 = ('Package_TO_SOT_THT', 'TO-247-4_Vertical')


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
    """True when the installed KiCad footprint library is reachable."""
    return pf.footprint_available(*TO247)


PCBNEW_SCRIPT = '''
import json, sys
try:
    import pcbnew
except ImportError as error:
    print(json.dumps({"skip": str(error)}))
    sys.exit(0)
root, result = sys.argv[1], {}
for footprint in sys.argv[2:]:
    lib, name = footprint.split(":", 1)
    fp = pcbnew.FootprintLoad(root + "/" + lib + ".pretty", name)
    result[footprint] = None if fp is None else {"pads": [p.GetNumber() for p in fp.Pads()],
                                                 "zones": len(list(fp.Zones())), "attr": fp.GetAttributes()}
print(json.dumps(result))
'''


def fake_source(root: Path) -> Path:
    """Fake installed library: an SMD resistor, a TO-247-4 with a model line, and a mounting hole."""
    resistor = pf.make_footprint('R_0805_2012Metric', '\n'.join(
        pf.smd_pad(n, x, 0, 1.0, 1.45) for n, x in (('1', -0.9375), ('2', 0.9375))), 2.0, 1.25, 'fake 0805')
    to247 = pf.make_footprint('TO-247-4_Vertical', '\n'.join(
        pf.tht_pad(str(i + 1), i * 2.54, 0, (1.9, 4.5), 1.5, 'oval') for i in range(4)), 16, 5.2, 'fake TO-247-4',
        model_name='TO247_ENVELOPE')
    hole = pf.make_footprint('MountingHole_3.2mm_M3', pf.npth_pad(0, 0, 3.2), 6.4, 6.4, 'fake hole', shape='circle')
    for lib, name, text in (('Resistor_SMD', 'R_0805_2012Metric', resistor), ('Package_TO_SOT_THT', 'TO-247-4_Vertical', to247),
                            ('MountingHole', 'MountingHole_3.2mm_M3', hole)):
        folder = root / f'{lib}.pretty'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{name}.kicad_mod').write_text(text, encoding='utf-8')
    return root


def sample_parts():
    """Parts in the shared electrical-model format, split across two boards."""
    return [
        dict(ref='R1', footprint='Resistor_SMD:R_0805_2012Metric', nets={'1': 'A', '2': 'B'}, kind='R', board='control'),
        dict(ref='R2', footprint='Resistor_SMD:R_0805_2012Metric', nets={'1': 'B', '2': 'GND'}, kind='R', board='control'),
        dict(ref='Q1', footprint='Package_TO_SOT_THT:TO-247-4_Vertical', nets={'1': 'G', '2': 'D', '3': 'KS', '4': 'S'}, kind='Q', board='power'),
        dict(ref='L1', footprint='AIPE:TOROID', nets={'1': 'SW', '2': 'VOUT'}, kind='L', board='power'),
        dict(ref='H1', footprint='MountingHole:MountingHole_3.2mm_M3', nets={}, kind='H', board='power'),
    ]


class GeneratorTests(unittest.TestCase):
    def test_toroid_has_two_leads_and_optional_centre_hole(self):
        text, boxes = pf.toroid_inductor_footprint('TOROID', 30, 2.4, 4.6, 47.6, 19, 6.5)
        pads = pf.pads_in_text(text)
        self.assertEqual(pf.pad_numbers(pads), ['1', '2'])
        self.assertEqual([p['type'] for p in pads], ['thru_hole', 'thru_hole', 'np_thru_hole'])
        self.assertEqual([p['at'] for p in pads], [[-15.0, 0.0], [15.0, 0.0], [0.0, 0.0]])
        self.assertIn('(fp_circle (center 0 0) (end 23.8 0)', text)
        self.assertIn('(attr through_hole)', text)
        self.assertEqual(boxes, [(0, 0, 9.5, 47.6, 47.6, 19, (0.25, 0.27, 0.3))])
        without_hole, _ = pf.toroid_inductor_footprint('TOROID', 30, 2.4, 4.6, 47.6, 19)
        self.assertNotIn('np_thru_hole', without_hole)
        upright, boxes = pf.toroid_inductor_footprint('TOROID', 20, 2.4, 4.6, 47.6, 19, upright=True)
        self.assertIn('(fp_rect (start -23.8 -9.5) (end 23.8 9.5)', upright)
        self.assertEqual(boxes[0][3:6], (47.6, 19, 47.6))
        with self.assertRaises(ValueError):
            pf.toroid_inductor_footprint('TOROID', 8, 2.4, 4.6, 47.6, 19, 6.5)

    def test_film_capacitor_two_and_four_pins(self):
        two, _ = pf.film_capacitor_footprint('FILM2', 27.5, 31.5, 13, 22, 1.0)
        pads = pf.pads_in_text(two)
        self.assertEqual([(p['number'], p['at'], p['size'][0], p['drill']) for p in pads],
                         [('1', [-13.75, 0.0], 2.0, 1.0), ('2', [13.75, 0.0], 2.0, 1.0)])
        four, boxes = pf.film_capacitor_footprint('FILM4', 37.5, 41.5, 20, 39.5, 1.2, pins=4, second_pitch_mm=10.2)
        pads = pf.pads_in_text(four)
        self.assertEqual([p['number'] for p in pads], ['1', '1', '2', '2'])
        self.assertEqual(pf.pad_numbers(pads), ['1', '2'])
        self.assertEqual({tuple(p['at']) for p in pads}, {(-18.75, -5.1), (-18.75, 5.1), (18.75, -5.1), (18.75, 5.1)})
        self.assertEqual(boxes, [(0, 0, 19.75, 41.5, 20, 39.5, (0.2, 0.3, 0.6))])
        separate, _ = pf.film_capacitor_footprint('FILM4', 37.5, 41.5, 20, 39.5, 1.2, 4, 10.2, pad_numbers=('1', '2', '3', '4'))
        self.assertEqual(pf.pad_numbers(pf.pads_in_text(separate)), ['1', '2', '3', '4'])
        for kwargs in (dict(pins=3), dict(pins=4), dict(pitch_mm=40), dict(pins=4, second_pitch_mm=19)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                args = dict(name='FILM', pitch_mm=37.5, length_mm=41.5, width_mm=20, height_mm=39.5, lead_drill_mm=1.2)
                args.update(kwargs)
                pf.film_capacitor_footprint(**args)

    def test_heatsink_envelope_has_only_mounting_holes_and_a_rule_area(self):
        text, boxes = pf.heatsink_envelope_footprint('HS', 100, 40, 50, [(-40, 0, 3.2), (40, 0, 3.2)])
        pads = pf.pads_in_text(text)
        self.assertEqual([p['type'] for p in pads], ['np_thru_hole', 'np_thru_hole'])
        self.assertEqual(pf.pad_numbers(pads), [])
        self.assertIn('(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour allowed) (footprints not_allowed))', text)
        self.assertIn('(polygon (pts (xy -50 -20) (xy 50 -20) (xy 50 20) (xy -50 20)))', text)
        self.assertIn('(attr through_hole exclude_from_pos_files)', text)
        self.assertIn('HEATSINK H=50mm', text)
        self.assertEqual(boxes, [(0, 0, 25, 100, 40, 50, (0.55, 0.57, 0.6))])
        plated, _ = pf.heatsink_envelope_footprint('HS', 60, 30, 25, [(-25, 0, 3.2)], plated_number='1', keepout=('vias',),
                                                   keepout_layers=('F.Cu', 'B.Cu'))
        self.assertEqual(pf.pad_numbers(pf.pads_in_text(plated)), ['1'])
        self.assertIn('(layers "F.Cu" "B.Cu")', plated)
        self.assertIn('(tracks allowed) (vias not_allowed)', plated)
        bare, _ = pf.heatsink_envelope_footprint('HS', 60, 30, 25, keepout=None)
        self.assertNotIn('(zone', bare)
        self.assertEqual(pf.pads_in_text(bare), [])
        with self.assertRaises(ValueError):
            pf.heatsink_envelope_footprint('HS', 60, 30, 25, [(31, 0, 3.2)])
        with self.assertRaises(ValueError):
            pf.heatsink_envelope_footprint('HS', 60, 30, 25, keepout=('lasers',))

    def test_pad_helpers(self):
        self.assertEqual(pf.tht_pad('1', -16.255, 0, (12, 7), (8.5, 3.0), 'oval'),
                         '(pad "1" thru_hole oval (at -16.255 0) (size 12 7) (drill oval 8.5 3) (layers "*.Cu" "*.Mask") (remove_unused_layers no))')
        self.assertIn('(roundrect_rratio 0.25)', pf.tht_pad('2', 0, 0, 2.4, 1.2, 'roundrect'))
        self.assertEqual(pf.smd_pad('3', -4.025, 0.85, 2.55, 5.6),
                         '(pad "3" smd rect (at -4.025 0.85) (size 2.55 5.6) (layers "F.Cu" "F.Paste" "F.Mask"))')
        self.assertEqual(pf.npth_pad(0, 0, 3.2),
                         '(pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask"))')
        with self.assertRaises(ValueError):
            pf.tht_pad('1', 0, 0, 1.0, 1.2)
        with self.assertRaises(ValueError):
            pf.tht_pad('1', 0, 0, 2.0, 1.2, 'hexagon')
        with self.assertRaises(ValueError):
            pf.smd_pad('1', 0, 0, 1, 1, 'star')
        self.assertEqual([pf.num(v) for v in (0, -0.0, 1.5, 2.54, 1 / 3, 10.0)], ['0', '0', '1.5', '2.54', '0.3333', '10'])

    def test_make_footprint_is_deterministic_and_infers_type(self):
        pads = pf.smd_pad('1', -1, 0, 1, 1.2) + '\n' + pf.smd_pad('2', 1, 0, 1, 1.2)
        first = pf.make_footprint('TEST_FP', pads, 3, 2, 'test "quoted" description', 'ENV')
        self.assertEqual(first, pf.make_footprint('TEST_FP', pads, 3, 2, 'test "quoted" description', 'ENV'))
        self.assertIn('(attr smd)', first)
        self.assertIn('(descr "test \\"quoted\\" description")', first)
        self.assertIn('(model "${KIPRJMOD}/libraries/AIPE.3dshapes/ENV.wrl"', first)
        self.assertIn('(fp_rect (start -2 -1.5) (end 2 1.5)', first)  # courtyard
        self.assertEqual(pf.footprint_attr(pf.tht_pad('1', 0, 0, 2, 1)), 'through_hole')
        self.assertEqual(pf.footprint_attr(pf.npth_pad(0, 0, 3)), 'through_hole exclude_from_pos_files')
        self.assertEqual(pf.footprint_attr(''), '')
        no_model = pf.make_footprint('TEST_FP', pads, 3, 2, 'd', silkscreen=False, attr='')
        self.assertNotIn('(model', no_model)
        self.assertNotIn('F.SilkS")', no_model.split('(property "Value"')[1])
        self.assertNotIn('(attr', no_model)
        for name in ('bad:name', 'bad/name', 'bad name', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                pf.make_footprint(name, pads, 3, 2, 'd')
        with self.assertRaises(ValueError):
            pf.make_footprint('X', pads, 0, 2, 'd')


class LibraryParsingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aipe fp ')
        self.addCleanup(self.temp.cleanup)
        self.source = fake_source(Path(self.temp.name) / 'footprints')

    def test_footprint_lookup_and_pads_from_a_library_root(self):
        self.assertTrue(pf.footprint_available('Resistor_SMD', 'R_0805_2012Metric', self.source))
        self.assertFalse(pf.footprint_available('Resistor_SMD', 'R_0603_1608Metric', self.source))
        self.assertFalse(pf.footprint_available('Nope', 'R_0805_2012Metric', self.source))
        self.assertEqual(pf.footprint_pads('Resistor_SMD', 'R_0805_2012Metric', self.source), ['1', '2'])
        self.assertEqual(pf.footprint_pads('Package_TO_SOT_THT', 'TO-247-4_Vertical', self.source), ['1', '2', '3', '4'])
        self.assertEqual(pf.footprint_pads('MountingHole', 'MountingHole_3.2mm_M3', self.source), [])
        details = pf.footprint_pad_details('Package_TO_SOT_THT', 'TO-247-4_Vertical', self.source)
        self.assertEqual(details[1], dict(number='2', type='thru_hole', shape='oval', at=[2.54, 0.0], size=[1.9, 4.5],
                                          drill=1.5, layers=['*.Cu', '*.Mask']))
        with self.assertRaises(FileNotFoundError):
            pf.footprint_pads('Resistor_SMD', 'missing', self.source)

    def test_pads_in_text_handles_slots_and_rejects_non_footprints(self):
        text = pf.make_footprint('SLOT', pf.tht_pad('1', 0, 0, (12, 7), (8.5, 3.0), 'oval'), 20, 10, 'd')
        self.assertEqual(pf.pads_in_text(text)[0]['drill'], [8.5, 3.0])
        with self.assertRaises(ValueError):
            pf.pads_in_text('(kicad_pcb (version 1))')

    def test_root_discovery_honours_environment_and_absence(self):
        with patch.dict(os.environ, {'AIPE_KICAD_DATA': self.temp.name}):
            self.assertEqual(pf.footprints_root(), Path(self.temp.name) / 'footprints')
            self.assertTrue(pf.footprint_available('Resistor_SMD', 'R_0805_2012Metric'))
        with patch.dict(os.environ, {'AIPE_KICAD_CLI': str(Path(self.temp.name) / 'absent.exe')}):
            os.environ.pop('AIPE_KICAD_DATA', None)
            self.assertIsNone(pf.footprints_root())
            self.assertFalse(pf.footprint_available('Resistor_SMD', 'R_0805_2012Metric'))

    def test_validate_pad_mapping_reports_each_kind_of_mismatch(self):
        toroid = pf.toroid_inductor_footprint('TOROID', 30, 2.4, 4.6, 47.6, 19, 6.5)
        parts = sample_parts()
        self.assertEqual(pf.validate_pad_mapping(parts, {'TOROID': toroid}, self.source), [])
        parts[0]['nets'] = {'1': 'A', '3': 'B'}
        parts[2]['nets'] = {'1': 'G', '2': 'D', '3': 'S'}
        parts.append(dict(ref='U9', footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', nets={'1': 'X'}))
        issues = pf.validate_pad_mapping(parts, {}, self.source)
        self.assertEqual(len(issues), 4)
        self.assertIn("R1 Resistor_SMD:R_0805_2012Metric: pads without net ['2'], nets without pad ['3']", issues)
        self.assertIn("Q1 Package_TO_SOT_THT:TO-247-4_Vertical: pads without net ['4'], nets without pad []", issues)
        self.assertIn('L1: footprint AIPE:TOROID not found', issues)
        self.assertIn('U9: footprint Package_SO:SOIC-8_3.9x4.9mm_P1.27mm not found', issues)
        self.assertEqual(pf.validate_pad_mapping(parts, {}, self.source, board='control'),
                         ["R1 Resistor_SMD:R_0805_2012Metric: pads without net ['2'], nets without pad ['3']"])
        with self.assertRaises(ValueError):
            pf.validate_pad_mapping([dict(ref='Z1', footprint='NoColon', nets={})], {}, self.source)


class PrepareLibrariesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aipe fp ')
        self.addCleanup(self.temp.cleanup)
        self.source = fake_source(Path(self.temp.name) / 'footprints')
        self.project = Path(self.temp.name) / 'project'
        self.toroid = pf.toroid_inductor_footprint('TOROID', 30, 2.4, 4.6, 47.6, 19, 6.5)

    def prepare(self, parts=None, **kwargs):
        options = dict(custom_footprints={'TOROID': self.toroid}, model_overrides={'Q1': 'TO247_ENV'},
                       models={'TO247_ENV': [(5, 0, 10, 16, 5, 20, (0.2, 0.2, 0.2))]}, source=self.source)
        options.update(kwargs)
        return pf.prepare_libraries(parts or sample_parts(), self.project, **options)

    def test_builds_a_complete_reproducible_project_library(self):
        summary = self.prepare(notice_text='Project note.')
        libraries = self.project / 'libraries'
        self.assertEqual(summary['libraries'], ['AIPE', 'MountingHole', 'Package_TO_SOT_THT', 'Resistor_SMD'])
        self.assertEqual(summary['copied'], ['MountingHole:MountingHole_3.2mm_M3', 'Package_TO_SOT_THT:TO-247-4_Vertical',
                                             'Resistor_SMD:R_0805_2012Metric'])
        self.assertEqual(summary['overrides'], {'Package_TO_SOT_THT:TO-247-4_Vertical': 'TO247_ENV'})
        self.assertEqual(summary['models'], ['TO247_ENV', 'TOROID'])
        self.assertEqual((summary['parts'], summary['issues'], summary['warnings']), (5, [], []))
        self.assertEqual((libraries / 'Resistor_SMD.pretty/R_0805_2012Metric.kicad_mod').read_text(encoding='utf-8'),
                         (self.source / 'Resistor_SMD.pretty/R_0805_2012Metric.kicad_mod').read_text(encoding='utf-8'))
        rewritten = (libraries / 'Package_TO_SOT_THT.pretty/TO-247-4_Vertical.kicad_mod').read_text(encoding='utf-8')
        self.assertIn('(model "${KIPRJMOD}/libraries/AIPE.3dshapes/TO247_ENV.wrl"', rewritten)
        self.assertNotIn('TO247_ENVELOPE.wrl', rewritten)
        self.assertEqual(pf.footprint_pads('Package_TO_SOT_THT', 'TO-247-4_Vertical', libraries), ['1', '2', '3', '4'])
        self.assertEqual((libraries / 'AIPE.pretty/TOROID.kicad_mod').read_text(encoding='utf-8'), self.toroid[0])
        for name in ('TOROID.step', 'TOROID.wrl', 'TO247_ENV.step', 'TO247_ENV.wrl'):
            self.assertTrue((libraries / 'AIPE.3dshapes' / name).is_file(), name)
        for name in ('LICENSE.md', 'CC-BY-SA-4.0.txt', 'NOTICE.md'):
            self.assertTrue((libraries / name).is_file(), name)
        notice = (libraries / 'NOTICE.md').read_text(encoding='utf-8')
        self.assertIn('Project note.', notice)
        self.assertIn('- Resistor_SMD:R_0805_2012Metric', notice)
        self.assertIn('- Package_TO_SOT_THT:TO-247-4_Vertical -> TO247_ENV', notice)
        self.assertIn('- AIPE:TOROID', notice)
        table = (self.project / 'fp-lib-table').read_text(encoding='utf-8')
        self.assertTrue(table.startswith('(fp_lib_table (version 7)\n'))
        self.assertEqual(table.count('(lib (name'), 4)
        self.assertIn('(lib (name "AIPE") (type "KiCad") (uri "${KIPRJMOD}/libraries/AIPE.pretty") (options "") (descr "AIPE project library"))', table)
        self.assertEqual(pf.validate_pad_mapping(sample_parts(), source=libraries), [])
        snapshot = {p.relative_to(self.project): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        self.prepare(notice_text='Project note.')
        self.assertEqual(snapshot, {p.relative_to(self.project): p.read_bytes() for p in self.project.rglob('*') if p.is_file()})

    def test_strict_mode_rejects_mismatches_before_writing(self):
        parts = sample_parts()
        parts[2]['nets'] = {'1': 'G', '2': 'D', '3': 'S'}
        with self.assertRaises(ValueError):
            self.prepare(parts)
        self.assertFalse(self.project.exists())
        summary = self.prepare(parts, strict=False)
        self.assertEqual(len(summary['issues']), 1)
        self.assertTrue((self.project / 'fp-lib-table').is_file())

    def test_board_filter_and_custom_requirements(self):
        summary = self.prepare(board='control', custom_footprints=None, model_overrides=None, models=None)
        self.assertEqual(summary['libraries'], ['Resistor_SMD'])
        self.assertEqual(summary['parts'], 2)
        self.assertFalse((self.project / 'libraries/AIPE.pretty').exists())
        with self.assertRaises(ValueError):  # the AIPE part has no custom footprint
            self.prepare(custom_footprints=None)
        with self.assertRaises(KeyError):
            self.prepare(custom_footprints=None, strict=False)
        with self.assertRaises(KeyError):
            self.prepare(model_overrides={'Q99': 'X'})
        with self.assertRaises(KeyError):  # stale files from an earlier run must not satisfy an override target
            self.prepare(parts=[sample_parts()[0], sample_parts()[3]], model_overrides={'Package_TO_SOT_THT:TO-247-4_Vertical': 'X'})
        with self.assertRaises(KeyError):
            self.prepare(model_overrides={'L1': 'X'})
        parts = sample_parts()
        parts.append(dict(ref='Q2', footprint='Package_TO_SOT_THT:TO-247-4_Vertical', nets={'1': 'G', '2': 'D', '3': 'KS', '4': 'S'}))
        with self.assertRaises(ValueError):
            self.prepare(parts, model_overrides={'Q1': 'A', 'Q2': 'B'}, models={'A': [], 'B': []})
        summary = self.prepare(model_overrides={'Q1': 'UNWRITTEN'})
        self.assertEqual(len(summary['warnings']), 1)
        with self.assertRaises(FileNotFoundError):  # official footprint absent from the library root
            self.prepare(parts=[dict(ref='X1', footprint='Resistor_SMD:R_0603_1608Metric', nets={'1': 'A', '2': 'B'})],
                         strict=False, model_overrides=None, models=None)

    def test_replace_model_appends_when_the_footprint_has_none(self):
        text = pf.make_footprint('PLAIN', pf.smd_pad('1', 0, 0, 1, 1), 2, 2, 'd')
        rewritten = pf.replace_model(text, 'ENV')
        self.assertEqual(rewritten.count('(model '), 1)
        self.assertIn('AIPE.3dshapes/ENV.wrl', rewritten)
        self.assertEqual(pf.pad_numbers(pf.pads_in_text(rewritten)), ['1'])
        twice = pf.replace_model(pf.replace_model(text, 'ENV'), 'OTHER')
        self.assertEqual(twice.count('(model '), 1)
        self.assertIn('OTHER.wrl', twice)


@unittest.skipUnless(library_installed(), 'installed KiCad footprint library not available')
class InstalledLibraryTests(unittest.TestCase):
    def test_footprints_the_v2_design_relies_on_exist_with_expected_pad_counts(self):
        expected = {
            'Package_TO_SOT_THT:TO-247-4_Vertical': 4, 'Package_TO_SOT_THT:TO-247-4_Horizontal_TabDown': 4,
            'Package_TO_SOT_THT:TO-247-4_Horizontal_TabUp': 4, 'Package_TO_SOT_THT:TO-247-3_Vertical': 3,
            'Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm': 16, 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm': 16,
            'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm': 8, 'Package_SO:SOIC-8_7.5x5.85mm_P1.27mm': 8,
            'Package_QFP:LQFP-176_24x24mm_P0.5mm': 176, 'Package_TO_SOT_SMD:SOT-23': 3, 'Package_TO_SOT_SMD:SOT-23-5': 5,
            'Package_TO_SOT_SMD:SOT-23-6': 6, 'Resistor_SMD:R_1206_3216Metric': 2, 'Resistor_SMD:R_0805_2012Metric': 2,
            'Resistor_SMD:R_2512_6332Metric': 2, 'Capacitor_SMD:C_2220_5750Metric': 2, 'Capacitor_SMD:C_1812_4532Metric': 2,
            'Capacitor_SMD:C_1210_3225Metric': 2, 'Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical': 40,
            'Connector_PinHeader_2.54mm:PinHeader_2x13_P2.54mm_Vertical': 26, 'Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical': 10,
            'Connector_IDC:IDC-Header_2x20_P2.54mm_Vertical': 40, 'Connector_IDC:IDC-Header_2x13_P2.54mm_Vertical': 26,
            'MountingHole:MountingHole_3.2mm_M3': 0, 'MountingHole:MountingHole_4.3mm_M4': 0,
            'Heatsink:Heatsink_AAVID_TV5G_TO220_Horizontal': 0, 'Heatsink:Heatsink_125x35x50mm_3xFixationM3': 0,
            'Connector_Phoenix_MSTB:PhoenixContact_MSTBVA_2,5_2-G-5,08_1x02_P5.08mm_Vertical': 2,
            'Connector_Phoenix_GMSTB:PhoenixContact_GMSTBVA_2,5_2-G-7,62_1x02_P7.62mm_Vertical': 2,
            'TerminalBlock_Wuerth:Wuerth_REDCUBE-THR_WP-THRSH_74651195_THR': 1,
        }
        for footprint, count in expected.items():
            with self.subTest(footprint=footprint):
                lib, name = footprint.split(':')
                self.assertTrue(pf.footprint_available(lib, name), footprint)
                self.assertEqual(len(pf.footprint_pads(lib, name)), count)
        self.assertFalse(pf.footprint_available('Package_SO', 'SOIC-8W_7.5x5.85mm_P1.27mm'))


@unittest.skipUnless(library_installed() and kicad_python(), 'KiCad bundled Python with pcbnew not available')
class PcbnewTests(unittest.TestCase):
    def test_prepared_official_and_custom_footprints_load_in_pcbnew(self):
        custom = {'TOROID': pf.toroid_inductor_footprint('TOROID', 30, 2.4, 4.6, 47.6, 19, 6.5),
                  'HEATSINK': pf.heatsink_envelope_footprint('HEATSINK', 100, 40, 50, [(-40, 0, 3.2), (40, 0, 3.2)]),
                  'FILM4': pf.film_capacitor_footprint('FILM4', 37.5, 41.5, 20, 39.5, 1.2, pins=4, second_pitch_mm=10.2)}
        parts = [
            dict(ref='Q1', footprint='Package_TO_SOT_THT:TO-247-4_Vertical', nets={'1': 'G', '2': 'D', '3': 'KS', '4': 'S'}),
            dict(ref='U1', footprint='Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm', nets={str(i): f'N{i}' for i in range(1, 17)}),
            dict(ref='C1', footprint='Capacitor_SMD:C_2220_5750Metric', nets={'1': 'VIN', '2': 'GND'}),
            dict(ref='J1', footprint='Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical', nets={str(i): f'P{i}' for i in range(1, 11)}),
            dict(ref='L1', footprint='AIPE:TOROID', nets={'1': 'SW', '2': 'VOUT'}),
            dict(ref='HS1', footprint='AIPE:HEATSINK', nets={}),
            dict(ref='C2', footprint='AIPE:FILM4', nets={'1': 'VIN', '2': 'GND'}),
        ]
        with tempfile.TemporaryDirectory(prefix='aipe fp ') as folder:
            project = Path(folder) / 'project'
            summary = pf.prepare_libraries(parts, project, custom_footprints=custom, model_overrides={'U1': 'SOIC16W_ENV'},
                                           models={'SOIC16W_ENV': [(0, 0, 1.3, 7.5, 10.3, 2.4, (0.2, 0.2, 0.2))]})
            self.assertEqual(summary['warnings'], [])
            ids = [p['footprint'] for p in parts]
            run = subprocess.run([str(kicad_python()), '-c', PCBNEW_SCRIPT, str(project / 'libraries').replace('\\', '/'), *ids],
                                 capture_output=True, text=True, timeout=300, cwd=folder)
            self.assertEqual(run.returncode, 0, run.stderr[-2000:])
            result = json.loads(run.stdout.strip().splitlines()[-1])
            if 'skip' in result:
                self.skipTest(f"pcbnew not importable: {result['skip']}")
            for part in parts:
                with self.subTest(footprint=part['footprint']):
                    loaded = result[part['footprint']]
                    self.assertIsNotNone(loaded, 'pcbnew.FootprintLoad returned None')
                    lib, name = part['footprint'].split(':')
                    numbered = sorted({n for n in loaded['pads'] if n})
                    self.assertEqual(numbered, sorted(pf.footprint_pads(lib, name, project / 'libraries')))
                    self.assertEqual(set(numbered), set(part['nets']))
            self.assertEqual(result['AIPE:HEATSINK']['zones'], 1)
            self.assertEqual(len(result['AIPE:HEATSINK']['pads']), 2)
            self.assertEqual(len(result['AIPE:FILM4']['pads']), 4)
            self.assertEqual(len(result['AIPE:TOROID']['pads']), 3)


if __name__ == '__main__':
    unittest.main()
