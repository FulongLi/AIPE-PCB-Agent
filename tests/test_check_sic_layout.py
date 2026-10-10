"""Tests for the V2 layout metrics checker (automation.verification.check_sic_layout).

Pure-Python parts (segment/polygon distances, bounding-box pruning, the slot surface-path formula, net-class
matching, spec and model loading, rule-row dispositions, Markdown rendering) run with the host interpreter.
The pcbnew parts run this file under KiCad's bundled Python (``--synthetic <dir>``): a small four-layer board
is built from programmatic footprints with known geometry (two TO-247-like devices, an isolated driver with a
non-plated slot, a heatsink envelope, a control header, zones and a rule area), saved, reloaded and measured,
and the metrics are compared with values computed analytically from the same constants. A second pcbnew test
runs the CLI read-only on the frozen V1 board with a minimal spec. Both skip, never pass, without KiCad.
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.setup.detect_kicad import find_kicad_cli, read_config  # noqa: E402
from automation.verification import check_sic_layout as cl  # noqa: E402

V1_BOARD = ROOT / 'examples/buck-48v-24v-1kw/kicad/AIPE_Buck_1kW.kicad_pcb'
V1_MODEL = ROOT / 'examples/buck-48v-24v-1kw/design/circuit.json'


def kicad_python():
    """Interpreter with pcbnew: AIPE_KICAD_PYTHON, local-tools.json, next to kicad-cli, or None."""
    explicit = os.environ.get('AIPE_KICAD_PYTHON') or read_config().get('kicad_python')
    if explicit and Path(os.path.expandvars(explicit)).is_file():
        return Path(os.path.expandvars(explicit))
    try:
        cli = find_kicad_cli()
    except FileNotFoundError:
        cli = None
    if cli:
        for name in ('python.exe', 'python3', 'python'):
            if (cli.parent / name).is_file():
                return cli.parent / name
    try:
        import pcbnew  # noqa: F401
        return Path(sys.executable)
    except ImportError:
        return None


# ----- pure geometry and spec handling ------------------------------------------------------------------------
class GeometryTests(unittest.TestCase):
    def test_segment_distances(self):
        self.assertAlmostEqual(cl.segment_segment_distance((0, 0), (1, 0), (0, 1), (1, 1)), 1.0)
        self.assertAlmostEqual(cl.segment_segment_distance((0, 0), (2, 2), (0, 2), (2, 0)), 0.0)  # crossing
        self.assertAlmostEqual(cl.segment_segment_distance((0, 0), (1, 0), (2, 0), (3, 0)), 1.0)  # collinear gap
        self.assertAlmostEqual(cl.segment_segment_distance((0, 0), (1, 0), (1, 0), (1, 5)), 0.0)  # touching
        self.assertAlmostEqual(cl.segment_segment_distance((0, 0), (0, 0), (3, 4), (3, 4)), 5.0)  # degenerate points
        matrix = cl.segments_distance_matrix([[0, 0, 1, 0], [0, 3, 1, 3]], [[0, 1, 1, 1]])
        self.assertEqual(matrix.shape, (2, 1))
        np.testing.assert_allclose(matrix[:, 0], [1.0, 2.0])

    def test_edges_min_distance_matches_brute_force_and_chunks(self):
        rng = np.random.default_rng(1)
        E1 = rng.uniform(0, 10, (40, 4))
        E2 = rng.uniform(20, 30, (37, 4))
        brute = cl.segments_distance_matrix(E1, E2).min()
        self.assertAlmostEqual(cl.edges_min_distance(E1, E2), brute, places=9)
        self.assertAlmostEqual(cl.edges_min_distance(E1, E2, budget=50), brute, places=9)
        self.assertEqual(cl.edges_min_distance(np.empty((0, 4)), E2), math.inf)

    def test_point_in_polygon_with_hole_and_area(self):
        outer = [(0, 0), (10, 0), (10, 10), (0, 10)]
        hole = [(4, 4), (6, 4), (6, 6), (4, 6)]
        self.assertTrue(cl.point_in_polygon((1, 1), [outer, hole]))
        self.assertFalse(cl.point_in_polygon((5, 5), [outer, hole]))
        self.assertFalse(cl.point_in_polygon((11, 5), [outer]))
        self.assertAlmostEqual(cl.polygon_area(outer), 100.0)
        poly = cl.make_polygon([outer, hole])
        self.assertAlmostEqual(poly.area(), 96.0)
        self.assertEqual(poly.bbox, (0.0, 0.0, 10.0, 10.0))

    def test_primitive_distances_numpy_backend(self):
        a = cl.make_rect((0, 0, 2, 2), net='A')
        b = cl.make_rect((5, 0, 7, 2), net='B')
        inside = cl.make_rect((0.5, 0.5, 1.0, 1.0), net='C')
        seg = cl.make_segment((3, -5), (3, 5), 0.5, net='S')
        via = cl.make_circle((4.5, 1), 0.3, net='V')
        self.assertAlmostEqual(cl.primitive_distance(a, b), 3.0)
        self.assertAlmostEqual(cl.primitive_distance(a, inside), 0.0)
        self.assertAlmostEqual(cl.primitive_distance(a, seg), 0.75)  # 3 - 2 - 0.25
        self.assertAlmostEqual(cl.primitive_distance(seg, b), 1.75)  # 5 - 3 - 0.25
        self.assertAlmostEqual(cl.primitive_distance(a, via), 2.2)   # 4.5 - 2 - 0.3
        self.assertAlmostEqual(cl.primitive_distance(seg, via), 0.95)  # 1.5 - 0.25 - 0.3
        self.assertAlmostEqual(cl.primitive_distance(via, cl.make_circle((4.5, 3), 0.2)), 1.5)
        hole_poly = cl.make_polygon([[(0, 0), (10, 0), (10, 10), (0, 10)], [(4, 4), (6, 4), (6, 6), (4, 6)]])
        self.assertAlmostEqual(cl.primitive_distance(hole_poly, cl.make_rect((4.5, 4.5, 5.5, 5.5))), 0.5)
        self.assertAlmostEqual(cl.primitive_distance(hole_poly, cl.make_circle((5, 5), 0.25)), 0.75)

    @unittest.skipUnless(cl.shapely_available(), 'shapely not importable in this interpreter')
    def test_shapely_backend_agrees_with_numpy(self):
        rng = np.random.default_rng(7)
        prims = []
        for i in range(12):
            x, y = rng.uniform(0, 50, 2)
            prims.append(cl.make_rect((x, y, x + rng.uniform(0.5, 4), y + rng.uniform(0.5, 4)), net=f'N{i}'))
            prims.append(cl.make_segment((x, y + 6), (x + rng.uniform(1, 8), y + 6 + rng.uniform(-3, 3)), rng.uniform(0.2, 1.0), net=f'S{i}'))
            prims.append(cl.make_circle((x + 2, y + 9), rng.uniform(0.2, 0.6), net=f'V{i}'))
        for p in prims:
            for q in prims:
                # shapely buffers round caps with 16 segments per quarter turn: polygonal error below ~1e-3 mm here
                self.assertAlmostEqual(cl.primitive_distance(p, q, 'numpy'), cl.primitive_distance(p, q, 'shapely'), delta=2e-3, msg=(p.kind, q.kind))
        self.assertEqual(cl.distance_backend('shapely'), 'shapely')
        self.assertEqual(cl.distance_backend('numpy'), 'numpy')

    def test_group_min_distance_prunes_like_brute_force(self):
        rng = np.random.default_rng(3)
        A = [cl.make_rect((x, y, x + 1, y + 1), net='A') for x, y in rng.uniform(0, 30, (25, 2))]
        B = [cl.make_circle((x, y), 0.4, net='B') for x, y in rng.uniform(35, 60, (30, 2))]
        brute = min(cl.primitive_distance(p, q) for p in A for q in B)
        d, pair = cl.group_min_distance(A, B)
        self.assertAlmostEqual(d, brute, places=9)
        self.assertAlmostEqual(cl.primitive_distance(*pair), brute, places=9)
        d2, _ = cl.group_min_distance(A, B, budget=7)
        self.assertAlmostEqual(d2, brute, places=9)
        self.assertEqual(cl.group_min_distance([], B), (None, None))
        touching = cl.group_min_distance(A, [cl.make_rect(A[0].bbox)])
        self.assertEqual(touching[0], 0.0)

    def test_bbox_helpers(self):
        self.assertAlmostEqual(cl.bbox_distance((0, 0, 1, 1), (4, 5, 6, 7)), 5.0)
        self.assertEqual(cl.bbox_distance((0, 0, 2, 2), (1, 1, 3, 3)), 0.0)
        self.assertEqual(cl.bbox_union([(0, 0, 1, 1), (2, -1, 3, 4)]), (0, -1, 3, 4))
        self.assertIsNone(cl.bbox_union([None]))
        self.assertEqual(cl.inflate((0, 0, 1, 1), 0.5), (-0.5, -0.5, 1.5, 1.5))
        self.assertTrue(cl.point_in_bbox((0.5, 0.5), (0, 0, 1, 1)))

    def test_slot_surface_path_formula(self):
        self.assertAlmostEqual(cl.slot_surface_path_mm(6.0, 3.0), 2 * math.sqrt(9 + 9))
        self.assertAlmostEqual(cl.slot_surface_path_mm(5.5, 0.0), 5.5)  # no extension: the gap itself
        self.assertAlmostEqual(cl.slot_surface_path_mm(7.0, -1.0), 7.0)  # a short slot never shortens the path
        e = cl.slot_extension_for_path_mm(5.5, 9.0)
        self.assertAlmostEqual(cl.slot_surface_path_mm(5.5, e), 9.0)
        self.assertEqual(cl.slot_extension_for_path_mm(9.5, 9.0), 0.0)
        # the 'gap + 2 x board thickness' model would claim 5.5 + 4 = 9.5 mm here; the around-the-end path is shorter
        self.assertLess(cl.slot_surface_path_mm(5.5, 2.0), 9.5)

    def test_stackup_parsing(self):
        text = ('(kicad_pcb (setup (stackup\n(layer "F.Cu" (type "copper") (thickness 0.07))\n'
                '(layer "dielectric 1" (type "prepreg") (thickness 0.2) (material "FR4") (epsilon_r 4.3))\n'
                '(layer "In1.Cu" (type "copper") (thickness 0.035))\n(copper_finish "ENIG") (dielectric_constraints no))\n(pad_to_mask_clearance 0)))')
        stack = cl.parse_stackup(text)
        self.assertEqual([s['layer'] for s in stack], ['F.Cu', 'dielectric 1', 'In1.Cu'])
        self.assertEqual(stack[0]['thickness_um'], 70.0)
        self.assertEqual(stack[2]['thickness_um'], 35.0)
        self.assertNotIn('thickness_um', stack[1])
        self.assertEqual(cl.parse_stackup('(kicad_pcb (setup))'), [])


class SpecTests(unittest.TestCase):
    def test_default_specs_load_and_reference_baseline_thresholds(self):
        power = cl.load_spec(cl.DEFAULT_SPECS['power'])
        control = cl.load_spec(cl.DEFAULT_SPECS['control'])
        self.assertEqual((power['board'], control['board']), ('power', 'control'))
        pairs = {p['name']: p for p in power['isolation']['pairs']}
        selv = next(p for n, p in pairs.items() if 'CTRL_SELV' in n)
        self.assertEqual(selv['min_mm'], {'all': 9.0})
        self.assertEqual(next(p for n, p in pairs.items() if n.startswith('HV to PE'))['min_mm'], {'all': 5.0})
        self.assertEqual(power['heatsink']['keepout_mm'], 5.0)
        self.assertEqual(power['gate_loops'][0]['driver_to_gate_mm_max'], 15)
        self.assertEqual(power['commutation']['pin_to_capacitor_mm_max'], [5, 15])
        self.assertEqual(len(power['isolation']['barrier_parts']), 8)
        self.assertTrue(all(b['required_surface_path_mm'] == 9.0 for b in power['isolation']['barrier_parts']))
        self.assertEqual(power['compactness']['board_area_mm2_max'], 43200)
        self.assertEqual(control['isolation']['pairs'], [])
        self.assertEqual(control['control']['model_near_pin_key'], 'near_dsp_pin')
        # the HV/DRV/DESAT/SENSE_ISO vocabulary follows sic_buck_common.NET_CLASS_PATTERNS
        from automation.kicad_tools.sic_buck_common import NET_CLASS_PATTERNS
        for name in ('HV_VIN', 'HV_SW', 'HV_PGND', 'HV_VOUT', 'SENSE_ISO', 'PE'):
            for pattern in NET_CLASS_PATTERNS[name]:
                self.assertEqual(cl.net_class(pattern.replace('*', 'X'), power['net_classes']), name, pattern)

    def test_spec_loading_defaults_and_validation(self):
        with tempfile.TemporaryDirectory(prefix='aipe spec ') as folder:
            path = Path(folder) / 'spec.json'
            path.write_text(json.dumps({'board': 'x', 'net_classes': {'HV': ['VIN']}}), encoding='utf-8')
            spec = cl.load_spec(path)
            self.assertEqual(spec['isolation'], {'pairs': [], 'barrier_keepouts': [], 'barrier_parts': []})
            self.assertEqual(spec['gate_loops'], [])
            self.assertEqual(spec['title'], 'x layout spec')
            path.write_text(json.dumps({'schema_version': 99}), encoding='utf-8')
            with self.assertRaises(ValueError):
                cl.load_spec(path)
            path.write_text(json.dumps([1, 2]), encoding='utf-8')
            with self.assertRaises(ValueError):
                cl.load_spec(path)
            path.write_text(json.dumps({'net_classes': {'HV': 'VIN'}}), encoding='utf-8')
            with self.assertRaises(ValueError):
                cl.load_spec(path)
            model_path = Path(folder) / 'model.json'
            model_path.write_text(json.dumps({'parts': [{'ref': 'C1', 'near_dsp_pin': '4'}, {'nope': 1}]}), encoding='utf-8')
            self.assertEqual([p['ref'] for p in cl.load_model(model_path)], ['C1'])
            model_path.write_text(json.dumps({'parts': 3}), encoding='utf-8')
            with self.assertRaises(ValueError):
                cl.load_model(model_path)

    def test_net_classes_groups_and_thresholds(self):
        spec = cl.load_spec(cl.DEFAULT_SPECS['power'])
        self.assertEqual(cl.net_class('DESAT_H_OC', spec['net_classes']), 'DESAT_HS')  # DESAT precedes DRV_HS
        self.assertEqual(cl.net_class('HS_VDD', spec['net_classes']), 'DRV_HS')
        self.assertEqual(cl.net_class('GND_CTRL', spec['net_classes']), 'CTRL_SELV')
        self.assertIsNone(cl.net_class('unconnected-(U1-Pad7)', spec['net_classes']))
        nets = ['VIN', 'SW', 'PGND', 'KS_H', 'DESAT_H_OC', 'GND_CTRL', 'PE', 'FOO']
        self.assertEqual(cl.nets_of_groups(nets, ['HV'], spec), ['PGND', 'SW', 'VIN'])
        self.assertEqual(cl.nets_of_groups(nets, ['HS_ISLAND'], spec), ['DESAT_H_OC', 'KS_H'])
        self.assertEqual(cl.nets_of_groups(nets, ['PE'], spec), ['PE'])  # a bare class name works as a group
        self.assertEqual(cl.threshold_for({'outer': 3.0, 'inner': 1.0}, 'inner'), 1.0)
        self.assertEqual(cl.threshold_for({'all': 9.0}, 'outer'), 9.0)
        self.assertEqual(cl.threshold_for(5, 'inner'), 5.0)
        self.assertIsNone(cl.threshold_for(None, 'outer'))
        self.assertEqual(cl.layer_kind('In1.Cu', ['F.Cu', 'B.Cu']), 'inner')

    def test_rule_rows_follow_spec_thresholds_only(self):
        self.assertEqual(cl.row('PE-PCB-001', 'm', 12.0)['disposition'], cl.MEASURED)
        self.assertEqual(cl.row('PE-PCB-001', 'm', 12.0, '<= 15 mm', True)['disposition'], cl.WITHIN)
        self.assertEqual(cl.row('PE-PCB-001', 'm', 19.0, '<= 15 mm', False)['disposition'], cl.EXCEEDS)
        self.assertEqual(cl.row('PE-PCB-001', 'm', None, '<= 15 mm', False)['disposition'], cl.NOT_MEASURED)
        self.assertEqual(cl.row('KR-ISO-004', 'm', 1)['requirement'], cl.RULES['KR-ISO-004'][0])
        table = cl.assemble_rule_table({'gate_loops': {'rows': [cl.row('KR-PCB-003', 'm', 1)]}}, [cl.row('PE-PCB-006', 'm', 2)])
        self.assertEqual([r['rule'] for r in table][:2], ['PE-PCB-001', 'PE-PCB-002'])
        self.assertEqual({r['rule'] for r in table}, set(cl.RULES))
        self.assertEqual(sum(r['disposition'] == cl.NOT_MEASURED for r in table), len(cl.RULES) - 2)
        for rule in ('PE-PCB-001', 'PE-PCB-008', 'KR-PCB-003', 'KR-ISO-001', 'KR-ISO-002', 'KR-ISO-004', 'KR-TH-002'):
            self.assertIn(rule, cl.RULES)

    def test_markdown_and_json_helpers(self):
        self.assertEqual(cl.fmt(None), 'n/a')
        self.assertEqual(cl.fmt(True), 'yes')
        self.assertEqual(cl.fmt(1.23456), '1.235')
        self.assertEqual(cl.fmt({'a': 1.5, 'b': [1, 2]}, 1), 'a=1.5; b=1, 2')
        self.assertIsNone(cl.rounded(math.inf))
        lines = cl.md_table(['A', 'B'], [[1, 'x|y']])
        self.assertEqual(lines[0], '| A | B |')
        self.assertIn('x\\|y', lines[2])
        payload = cl.jsonable({'a': (1, 2), 'b': {3}, 'c': np.float64(1.23456789), 'd': math.nan, 'e': cl.make_circle((0, 0), 1, net='N', layer='F.Cu')})
        self.assertEqual(payload['a'], [1, 2])
        self.assertEqual(payload['b'], [3])
        self.assertEqual(payload['c'], 1.2346)
        self.assertIsNone(payload['d'])
        self.assertEqual(payload['e']['net'], 'N')
        json.dumps(payload)


# ----- synthetic pcbnew board ---------------------------------------------------------------------------------
# All coordinates in mm. The expectations in SyntheticBoardTests are derived from these constants.
PAD_SQ = 1.8                   # TO-247-like square pads (rect), 2.54 mm pitch
SOIC_PAD = (1.5, 0.6)          # driver pads: 1.5 mm along x (across the gap), 0.6 mm along y
SOIC_X = (8.0, 15.0)           # SELV row and HV row x positions
SOIC_Y = (28.0, 29.27, 30.54, 31.81)
SLOT = dict(xy=(11.5, 29.905), drill=(1.2, 10.0))
VIA_KS_H = (15.0, 26.0)
VIA_DIA = 0.6
HS_COURTYARD = (20.0, 1.0, 34.0, 4.0)
VIN_ZONE = (30.0, 5.0, 40.0, 11.0)
PGND_ZONE = (18.0, 5.0, 45.0, 25.0)
GND_CTRL_ZONE = (1.0, 20.0, 10.0, 39.0)   # right edge clear of the U1 slot hole (x 10.9..12.1) and its clearance
ISO_BARRIER = (12.25, 24.0, 14.0, 35.0)
VIA_BOX = (14.5, 25.5, 15.5, 26.5)
SYN_PARTS = [
    # ref, courtyard (or None), [(pad, net, x, y, shape, size, drill)]
    ('Q1', (19.0, 9.0, 28.7, 11.0), [('1', 'G_H', 20.0, 10.0), ('2', 'VIN', 22.54, 10.0), ('3', 'SW', 25.08, 10.0), ('4', 'KS_H', 27.62, 10.0)]),
    ('Q2', (19.0, 19.0, 28.7, 21.0), [('1', 'G_L', 20.0, 20.0), ('2', 'SW', 22.54, 20.0), ('3', 'PGND', 25.08, 20.0), ('4', 'KS_L', 27.62, 20.0)]),
]
SYN_SMD = [
    ('C1', None, [('1', 'VIN', 33.0, 9.0, (2.0, 2.0)), ('2', 'PGND', 33.0, 13.0, (2.0, 2.0))]),
    ('U1', (6.5, 26.5, 16.5, 33.3), [('1', 'PWM_H', SOIC_X[0], SOIC_Y[0], SOIC_PAD), ('2', 'GND_CTRL', SOIC_X[0], SOIC_Y[1], SOIC_PAD),
                                     ('3', '3V3', SOIC_X[0], SOIC_Y[2], SOIC_PAD), ('4', 'PWM_L', SOIC_X[0], SOIC_Y[3], SOIC_PAD),
                                     ('5', 'KS_H', SOIC_X[1], SOIC_Y[0], SOIC_PAD), ('6', 'GATE_H', SOIC_X[1], SOIC_Y[1], SOIC_PAD),
                                     ('7', 'VDD_H', SOIC_X[1], SOIC_Y[2], SOIC_PAD), ('8', 'VEE_H', SOIC_X[1], SOIC_Y[3], SOIC_PAD)]),
    ('R1', None, [('1', 'GATE_H', 16.4, 10.0, (1.0, 1.2)), ('2', 'G_H', 18.0, 10.0, (1.0, 1.2))]),
    ('C2', None, [('1', 'VDD_H', 18.0, 30.54, (1.0, 1.0)), ('2', 'VEE_H', 19.6, 30.54, (1.0, 1.0))]),
]
SYN_J1 = [('1', 'PWM_H', 3.0, 36.0), ('2', 'GND_CTRL', 3.0, 38.0)]  # round THT pads 1.7 mm, drill 1.0
SYN_TRACKS = [
    # net, layer, a, b, width
    ('GATE_H', 'F.Cu', (SOIC_X[1], SOIC_Y[1]), (16.4, 10.0), 0.5),
    ('G_H', 'F.Cu', (18.0, 10.0), (20.0, 10.0), 0.5),
    ('KS_H', 'F.Cu', (SOIC_X[1], SOIC_Y[0]), VIA_KS_H, 0.5),
    ('KS_H', 'In1.Cu', VIA_KS_H, (31.0, 26.0), 0.5),
    ('KS_H', 'In1.Cu', (31.0, 26.0), (31.0, 13.0), 0.5),   # x = 31 keeps 2.23 mm from the Q2.4 pad edge (inner HS/LS limit 1.0 mm)
    ('KS_H', 'In1.Cu', (31.0, 13.0), (27.62, 10.0), 0.5),
    ('KS_L', 'B.Cu', (27.62, 20.0), (25.08, 20.0), 0.3),   # deliberate Kelvin-to-source short (KR-PCB-003 violation)
]
SYN_SPEC = {
    'schema_version': 1, 'board': 'synthetic', 'title': 'synthetic layout checker board',
    'expected': {'outline_mm': [60, 40], 'copper_layers': 4},
    'net_classes': {'HV_VIN': ['VIN'], 'HV_SW': ['SW'], 'HV_PGND': ['PGND'], 'DRV_HS': ['G_H', 'GATE_H', 'KS_H', 'VDD_H', 'VEE_H'],
                    'DRV_LS': ['G_L', 'KS_L'], 'CTRL_SELV': ['PWM_*', 'GND_CTRL', '3V3']},
    'class_groups': {'HV': ['HV_VIN', 'HV_SW', 'HV_PGND'], 'DRV': ['DRV_HS', 'DRV_LS'], 'CTRL_SELV': ['CTRL_SELV']},
    'copper': {'groups': ['HV'], 'vias_per_transition_min': None},
    'isolation': {
        'pairs': [{'name': 'HV/DRV to CTRL_SELV', 'a': ['HV', 'DRV'], 'b': ['CTRL_SELV'], 'min_mm': {'all': 9.0}, 'rules': ['KR-ISO-002']},
                  {'name': 'HS to LS', 'a': ['DRV_HS'], 'b': ['DRV_LS'], 'min_mm': {'outer': 3.0, 'inner': 1.0}, 'rules': ['KR-ISO-001']}],
        'barrier_keepouts': [{'name': 'ISO_BARRIER', 'zone_name': 'ISO_BARRIER'}, {'name': 'VIA_BOX', 'rect_mm': list(VIA_BOX)}],
        'barrier_parts': [{'ref': 'U1', 'required_surface_path_mm': 9.0, 'slot_extension_min_mm': 2.0, 'slot_width_min_mm': 1.0}]},
    'commutation': {'vin_net': 'VIN', 'pgnd_net': 'PGND', 'sw_net': 'SW', 'hf_capacitor_refs': ['C1'], 'hf_capacitor_nets': ['VIN', 'PGND'],
                    'pin_to_capacitor_mm_max': [5, 15],
                    'mosfets': [{'ref': 'Q1', 'role': 'HS', 'drain_pad': '2', 'source_pad': '3', 'gate_pad': '1', 'kelvin_pad': '4'},
                                {'ref': 'Q2', 'role': 'LS', 'drain_pad': '2', 'source_pad': '3', 'gate_pad': '1', 'kelvin_pad': '4'}]},
    'gate_loops': [{'mosfet': 'Q1', 'gate_pad': '1', 'kelvin_pad': '4', 'driver_ref': 'U1', 'driver_output_pads': ['6'], 'driver_return_pads': ['5'],
                    'gate_nets': ['GATE_H', 'G_H'], 'kelvin_net': 'KS_H', 'power_source_net': 'SW', 'driver_to_gate_mm_max': 15},
                   {'mosfet': 'Q2', 'gate_pad': '1', 'kelvin_pad': '4', 'driver_ref': 'U1', 'driver_output_pads': [], 'driver_return_pads': [],
                    'gate_nets': ['G_L'], 'kelvin_net': 'KS_L', 'power_source_net': 'PGND', 'driver_to_gate_mm_max': 15}],
    'heatsink': {'ref': 'HS1', 'keepout_mm': 5.0, 'groups': ['HV']},
    'decoupling': [{'ic': 'U1', 'supply_pads': ['7'], 'capacitor_refs': ['C2'], 'max_mm': 5.0}],
    'sensing': {'sw_net': 'SW', 'kelvin_pairs': [], 'parts': []},
    'control': {'section_refs': ['J1'], 'power_groups': ['HV'],
                'ground': {'net': 'GND_CTRL', 'layers': ['In1.Cu'], 'min_area_mm2': 120, 'require_copper_at': [[6.0, 30.0]], 'forbid_copper_at': [[30.0, 30.0]]}},
    'compactness': {'rated_power_W': 100, 'component_heights_mm': {'HS1': 20.0, 'default': 2.0}, 'hv_groups': ['HV']},
}


def build_synthetic_board(path):
    """Create the synthetic four-layer board with pcbnew and save it (needs KiCad Python)."""
    import pcbnew as pcb
    board = pcb.BOARD()
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(pcb.FromMM(1.6))
    names = sorted({p[1] for _, _, pads in SYN_PARTS + SYN_SMD for p in pads} | {p[1] for p in SYN_J1} | {t[0] for t in SYN_TRACKS})
    nets = {}
    for name in names:
        nets[name] = pcb.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    layer_ids = {board.GetLayerName(l): l for l in board.GetEnabledLayers().CuStack()}

    def point(x, y):
        return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))

    def footprint(ref, courtyard, xy):
        fp = pcb.FOOTPRINT(board)
        fp.SetReference(ref)
        fp.SetValue(ref)
        fp.SetFPID(pcb.LIB_ID('AIPE_TEST', ref))
        board.Add(fp)
        fp.SetPosition(point(*xy))  # before adding items: SetPosition translates everything already in the footprint
        if courtyard:
            shape = pcb.PCB_SHAPE(fp)
            shape.SetShape(pcb.SHAPE_T_RECT)
            shape.SetStart(point(courtyard[0], courtyard[1]))
            shape.SetEnd(point(courtyard[2], courtyard[3]))
            shape.SetLayer(pcb.F_CrtYd)
            shape.SetWidth(pcb.FromMM(0.05))
            fp.Add(shape)
        return fp

    def pad(fp, number, net, x, y, size, drill=None, shape=None, npth=False):
        p = pcb.PAD(fp)
        p.SetNumber(number)
        p.SetShape(shape if shape is not None else pcb.PAD_SHAPE_RECT)
        if npth:
            p.SetAttribute(pcb.PAD_ATTRIB_NPTH)
            p.SetLayerSet(pcb.PAD.UnplatedHoleMask())
        elif drill:
            p.SetAttribute(pcb.PAD_ATTRIB_PTH)
            p.SetLayerSet(pcb.PAD.PTHMask())
        else:
            p.SetAttribute(pcb.PAD_ATTRIB_SMD)
            p.SetLayerSet(pcb.PAD.SMDMask())
        p.SetSize(point(*size))
        if drill:
            if drill[0] != drill[1]:
                p.SetDrillShape(pcb.PAD_DRILL_SHAPE_OBLONG)
            p.SetDrillSize(point(*drill))
        p.SetPosition(point(x, y))
        if net:
            p.SetNet(nets[net])
        fp.Add(p)
        return p

    for ref, courtyard, pads in SYN_PARTS:
        fp = footprint(ref, courtyard, (pads[0][2], pads[0][3]))
        for number, net, x, y in pads:
            pad(fp, number, net, x, y, (PAD_SQ, PAD_SQ), drill=(1.0, 1.0))
    for ref, courtyard, pads in SYN_SMD:
        fp = footprint(ref, courtyard, (pads[0][2], pads[0][3]))
        for number, net, x, y, size in pads:
            pad(fp, number, net, x, y, size)
        if ref == 'U1':
            pad(fp, '', None, SLOT['xy'][0], SLOT['xy'][1], SLOT['drill'], drill=SLOT['drill'], shape=pcb.PAD_SHAPE_OVAL, npth=True)
    j1 = footprint('J1', None, (3.0, 37.0))
    for number, net, x, y in SYN_J1:
        pad(j1, number, net, x, y, (1.7, 1.7), drill=(1.0, 1.0), shape=pcb.PAD_SHAPE_CIRCLE)
    hs = footprint('HS1', HS_COURTYARD, (27.0, 2.5))
    pad(hs, '', None, 27.0, 2.5, (3.2, 3.2), drill=(3.2, 3.2), shape=pcb.PAD_SHAPE_CIRCLE, npth=True)
    for a, b in [((0, 0), (60, 0)), ((60, 0), (60, 40)), ((60, 40), (0, 40)), ((0, 40), (0, 0))]:
        edge = pcb.PCB_SHAPE(board)
        edge.SetShape(pcb.SHAPE_T_SEGMENT)
        edge.SetStart(point(*a))
        edge.SetEnd(point(*b))
        edge.SetLayer(pcb.Edge_Cuts)
        edge.SetWidth(pcb.FromMM(0.05))
        board.Add(edge)
    for net, layer, a, b, width in SYN_TRACKS:
        track = pcb.PCB_TRACK(board)
        track.SetStart(point(*a))
        track.SetEnd(point(*b))
        track.SetWidth(pcb.FromMM(width))
        track.SetLayer(layer_ids[layer])
        track.SetNet(nets[net])
        board.Add(track)
    via = pcb.PCB_VIA(board)
    via.SetPosition(point(*VIA_KS_H))
    via.SetWidth(pcb.FromMM(VIA_DIA))
    via.SetDrill(pcb.FromMM(0.3))
    via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
    via.SetNet(nets['KS_H'])
    board.Add(via)
    for net, layer, box in (('VIN', 'F.Cu', VIN_ZONE), ('PGND', 'In2.Cu', PGND_ZONE), ('GND_CTRL', 'In1.Cu', GND_CTRL_ZONE)):
        zone = pcb.ZONE(board)
        zone.SetNet(nets[net])
        zone.SetLayer(layer_ids[layer])
        zone.SetAssignedPriority(1)
        zone.SetLocalClearance(pcb.FromMM(0.5))
        zone.SetMinThickness(pcb.FromMM(0.2))
        zone.SetPadConnection(pcb.ZONE_CONNECTION_FULL)
        zone.SetIslandRemovalMode(pcb.ISLAND_REMOVAL_MODE_ALWAYS)
        outline = zone.Outline()
        outline.NewOutline()
        for x, y in ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])):
            outline.Append(pcb.FromMM(x), pcb.FromMM(y))
        board.Add(zone)
    rule = pcb.ZONE(board)
    rule.SetIsRuleArea(True)
    rule.SetZoneName('ISO_BARRIER')
    rule.SetLayerSet(pcb.LSET.AllCuMask(4))
    if hasattr(rule, 'SetDoNotAllowZoneFills'):
        rule.SetDoNotAllowZoneFills(True)
    outline = rule.Outline()
    outline.NewOutline()
    for x, y in ((ISO_BARRIER[0], ISO_BARRIER[1]), (ISO_BARRIER[2], ISO_BARRIER[1]), (ISO_BARRIER[2], ISO_BARRIER[3]), (ISO_BARRIER[0], ISO_BARRIER[3])):
        outline.Append(pcb.FromMM(x), pcb.FromMM(y))
    board.Add(rule)
    board.BuildConnectivity()
    pcb.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    pcb.SaveBoard(str(path), board)
    return path


def synthetic_scenario(out_dir) -> dict:
    """Build the synthetic board, run the checker (numpy backend) and return the metrics document."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    board = build_synthetic_board(out_dir / 'synthetic.kicad_pcb')
    spec_path = out_dir / 'spec.json'
    spec_path.write_text(json.dumps(SYN_SPEC, indent=1), encoding='utf-8')
    metrics = cl.run_check(board, cl.load_spec(spec_path), backend='numpy', spec_path=spec_path)
    cl.write_outputs(metrics, out_dir, 'synthetic')
    return metrics


def track_length(net):
    return sum(math.dist(a, b) for n, _layer, a, b, _w in SYN_TRACKS if n == net)


class SyntheticBoardTests(unittest.TestCase):
    """Measures a real pcbnew board with known geometry; skipped without KiCad Python."""

    @classmethod
    def setUpClass(cls):
        python = kicad_python()
        if python is None:
            raise unittest.SkipTest('KiCad Python with pcbnew unavailable')
        cls.temp = tempfile.TemporaryDirectory(prefix='aipe layout checker ')
        result = subprocess.run([str(python), str(Path(__file__).resolve()), '--synthetic', cls.temp.name], cwd=str(ROOT),
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
        if result.returncode != 0:
            cls.temp.cleanup()
            raise AssertionError(result.stdout[-4000:] + result.stderr[-4000:])
        cls.metrics = json.loads(result.stdout.strip().splitlines()[-1])

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'temp'):
            cls.temp.cleanup()

    def rows(self, rule):
        return [r for r in self.metrics['rule_table'] if r['rule'] == rule]

    def test_board_summary_and_outputs(self):
        board = self.metrics['board']
        self.assertEqual(board['copper_layers'], 4)
        self.assertEqual(board['layers'], ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'])
        self.assertEqual(board['outline_mm'], [60.0, 40.0])
        self.assertAlmostEqual(board['outline_area_mm2'], 2400.0, places=3)
        self.assertEqual(board['footprints'], 8)
        self.assertEqual(board['thickness_mm'], 1.6)
        self.assertEqual(board['rule_areas'], 1)
        self.assertEqual(board['zones'], 3)
        self.assertTrue((Path(self.temp.name) / 'layout_metrics_synthetic.json').is_file())
        text = (Path(self.temp.name) / 'layout_metrics_synthetic.md').read_text(encoding='utf-8')
        self.assertIn('## Rule table', text)
        self.assertIn('KR-ISO-004', text)
        self.assertEqual(self.metrics['status'], cl.STATUS)
        self.assertEqual(self.metrics['distance_backend'], 'numpy')
        self.assertEqual({r['rule'] for r in self.metrics['rule_table']}, set(cl.RULES))

    def test_net_lengths_vias_and_layers(self):
        nets = self.metrics['nets']
        self.assertAlmostEqual(nets['GATE_H']['track_mm'], track_length('GATE_H'), places=3)
        self.assertAlmostEqual(nets['KS_H']['track_mm'], track_length('KS_H'), places=3)
        self.assertEqual(nets['KS_H']['vias'], 1)
        self.assertEqual(nets['GATE_H']['cls'], 'DRV_HS')
        self.assertIn('F.Cu', nets['VIN']['zone_area_mm2'])
        self.assertGreater(nets['VIN']['zone_area_mm2']['F.Cu'], 50.0)

    def test_commutation_proxies(self):
        com = self.metrics['commutation']
        q1 = next(m for m in com['mosfets'] if m['ref'] == 'Q1')
        drain = q1['pins']['drain']
        self.assertAlmostEqual(drain['nearest_same_net_mm'], math.dist((22.54, 10.0), (33.0, 9.0)), places=3)
        self.assertEqual(drain['nearest_same_net_pad'], 'C1.1')
        self.assertEqual(drain['capacitors_within_row2'], 1)
        self.assertEqual(drain['capacitors_within_row1'], 0)
        self.assertIsNone(q1['pins']['source']['nearest_same_net_mm'])  # SW is not a capacitor net
        self.assertEqual(com['hf_group_bbox_mm'], [32.0, 8.0, 34.0, 14.0])
        self.assertIn('F.Cu', com['sw_copper_mm2'])
        rows = self.rows('PE-PCB-002')
        self.assertTrue(any(r['disposition'] == cl.WITHIN for r in rows))

    def test_gate_loop_and_kelvin_separation(self):
        loops = {g['mosfet']: g for g in self.metrics['gate_loops']['loops']}
        q1 = loops['Q1']
        self.assertAlmostEqual(q1['driver_output_to_gate_pad_mm'], math.dist((SOIC_X[1], SOIC_Y[1]), (20.0, 10.0)), places=3)
        self.assertEqual(q1['gate_layers'], ['F.Cu'])
        self.assertEqual(q1['kelvin_layers'], ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'])  # through via spans every layer
        self.assertTrue(q1['gate_kelvin_on_adjacent_layers'])
        self.assertIn(['F.Cu', 'In1.Cu'], q1['adjacent_layer_pairs'])
        ks = q1['kelvin_separation']
        self.assertTrue(ks['distinct_nets'])
        self.assertFalse(ks['copper_contact'])
        self.assertEqual(ks['bridging_parts'], [])
        self.assertAlmostEqual(ks['min_copper_distance_mm'], 2.54 - PAD_SQ, places=3)  # pin field gap
        q2 = loops['Q2']['kelvin_separation']
        self.assertTrue(q2['copper_contact'])  # the deliberate KS_L-PGND track
        self.assertEqual(q2['min_copper_distance_mm'], 0.0)
        self.assertEqual(q2['bridging_parts'], [])
        dispositions = {r['metric'].split(' ')[0]: r['disposition'] for r in self.rows('KR-PCB-003')}
        self.assertEqual(dispositions['KS_H'], cl.WITHIN)
        self.assertEqual(dispositions['KS_L'], cl.EXCEEDS)
        gate_rows = self.rows('PE-PCB-001')
        self.assertTrue(any(r['disposition'] == cl.EXCEEDS and r['threshold'] == '<= 15 mm' for r in gate_rows))
        self.assertTrue(any(r['disposition'] == cl.NOT_MEASURED for r in gate_rows))  # Q2 has no driver output pad

    def test_isolation_pairs(self):
        pairs = {p['name']: p for p in self.metrics['isolation']['pairs']}
        selv = pairs['HV/DRV to CTRL_SELV']
        self.assertAlmostEqual(selv['per_layer']['F.Cu']['distance_mm'], SOIC_X[1] - SOIC_X[0] - SOIC_PAD[0], places=3)
        self.assertAlmostEqual(selv['per_layer']['In1.Cu']['distance_mm'], VIA_KS_H[0] - VIA_DIA / 2 - GND_CTRL_ZONE[2], delta=0.01)
        via_to_header = math.dist(VIA_KS_H, (3.0, 36.0)) - VIA_DIA / 2 - 0.85
        self.assertAlmostEqual(selv['per_layer']['In2.Cu']['distance_mm'], via_to_header, delta=0.02)
        self.assertAlmostEqual(selv['per_layer']['B.Cu']['distance_mm'], via_to_header, delta=0.02)
        self.assertFalse(selv['within_threshold'])
        self.assertEqual(selv['per_layer']['F.Cu']['threshold_mm'], 9.0)
        self.assertEqual(selv['per_layer']['F.Cu']['between'][0]['ref'], 'U1')
        hs_ls = pairs['HS to LS']
        # nearest HS/LS copper on F.Cu: the slanted GATE_H track passes the upper-left corner of the Q2.1 (G_L) pad
        _net, _layer, a, b, width = SYN_TRACKS[0]
        corner = (20.0 - PAD_SQ / 2, 20.0 - PAD_SQ / 2)
        expected = float(cl._point_segment_distances([corner], [[*a, *b]])[0, 0]) - width / 2
        self.assertAlmostEqual(hs_ls['per_layer']['F.Cu']['distance_mm'], expected, delta=0.02)
        self.assertTrue(hs_ls['within_threshold'])
        self.assertEqual(hs_ls['per_layer']['In1.Cu']['threshold_mm'], 1.0)
        self.assertGreater(hs_ls['per_layer']['In1.Cu']['distance_mm'], 1.0)

    def test_barrier_strips_slot_and_surface_path(self):
        keepouts = {k['name']: k for k in self.metrics['isolation']['barrier_keepouts']}
        self.assertTrue(keepouts['ISO_BARRIER']['copper_free'])
        self.assertEqual(keepouts['ISO_BARRIER']['region'], "rule area 'ISO_BARRIER'")
        self.assertEqual(keepouts['ISO_BARRIER']['bbox_mm'], list(ISO_BARRIER))
        self.assertFalse(keepouts['VIA_BOX']['copper_free'])
        self.assertTrue(all(e['copper_items'] >= 1 for e in keepouts['VIA_BOX']['per_layer'].values()))
        self.assertIn('KS_H', keepouts['VIA_BOX']['per_layer']['In2.Cu']['nets'])
        part = self.metrics['isolation']['barrier_parts'][0]
        self.assertEqual(part['selv_pads'], ['1', '2', '3', '4'])
        self.assertEqual(part['hv_pads'], ['5', '6', '7', '8'])
        gap = SOIC_X[1] - SOIC_X[0] - SOIC_PAD[0]
        self.assertAlmostEqual(part['land_gap_mm'], gap, places=3)
        self.assertEqual(part['row_axis'], 'y')
        row_extent = (SOIC_Y[0] - SOIC_PAD[1] / 2, SOIC_Y[-1] + SOIC_PAD[1] / 2)
        slot_extent = (SLOT['xy'][1] - SLOT['drill'][1] / 2, SLOT['xy'][1] + SLOT['drill'][1] / 2)
        extension = min(row_extent[0] - slot_extent[0], slot_extent[1] - row_extent[1])
        best = part['best_slot']
        self.assertEqual(best['kind'], 'npth pad')
        self.assertAlmostEqual(best['extension_mm'], extension, places=3)
        self.assertAlmostEqual(best['width_mm'], 1.2, places=3)
        self.assertAlmostEqual(part['surface_path_mm'], cl.slot_surface_path_mm(gap, extension), places=3)
        self.assertAlmostEqual(part['required_extension_mm'], cl.slot_extension_for_path_mm(gap, 9.0), places=3)
        self.assertEqual(self.rows('KR-ISO-004')[0]['disposition'], cl.EXCEEDS)  # 7.8 mm < 9 mm
        self.assertEqual(self.rows('KR-ISO-001')[-1]['disposition'], cl.EXCEEDS)  # VIA_BOX contains copper

    def test_heatsink_decoupling_control_and_compactness(self):
        hs = self.metrics['heatsink']['per_layer']
        self.assertAlmostEqual(hs['F.Cu']['min_distance_mm'], VIN_ZONE[1] - HS_COURTYARD[3], delta=0.05)
        self.assertAlmostEqual(hs['B.Cu']['min_distance_mm'], (10.0 - PAD_SQ / 2) - HS_COURTYARD[3], delta=0.01)
        self.assertEqual(self.rows('KR-TH-002')[0]['disposition'], cl.EXCEEDS)
        dec = self.metrics['decoupling']['ics'][0]
        self.assertAlmostEqual(dec['pads'][0]['distance_mm'], 3.0, places=3)
        self.assertEqual(dec['pads'][0]['capacitor'], 'C2.1')
        self.assertEqual(self.rows('PE-PCB-008')[0]['disposition'], cl.WITHIN)
        ctl = self.metrics['control']
        self.assertEqual(ctl['control_refs'], ['J1'])
        self.assertEqual(ctl['power_refs'], ['C1', 'Q1', 'Q2'])
        self.assertGreater(ctl['bbox_separation_mm'], 15.0)
        ground = ctl['ground']['per_layer']['In1.Cu']
        self.assertGreater(ground['area_mm2'], 120.0)
        self.assertEqual(ground['islands'], 1)
        self.assertTrue(ground['probes']['required'][0]['copper'])
        self.assertFalse(ground['probes']['forbidden'][0]['copper'])
        self.assertTrue(any(r['disposition'] == cl.WITHIN and 'zone area' in r['metric'] for r in self.rows('PE-PCB-007')))
        cmp_ = self.metrics['compactness']
        self.assertAlmostEqual(cmp_['board_area_dm2'], 0.24, places=4)
        self.assertAlmostEqual(cmp_['footprints_per_dm2'], 8 / 0.24, places=3)
        self.assertAlmostEqual(cmp_['power_density_W_per_dm2'], 100 / 0.24, places=3)
        self.assertEqual(cmp_['tallest_component'], {'ref': 'HS1', 'height_mm': 20.0})
        self.assertAlmostEqual(cmp_['assembly_height_mm']['used'], 21.6, places=4)
        self.assertAlmostEqual(cmp_['power_density_W_per_L'], 100 / (2400 * 21.6 / 1e6), places=2)
        self.assertGreater(cmp_['courtyard_fraction']['front'], 0.0)


class V1BoardTests(unittest.TestCase):
    """Read-only robustness run on the frozen V1 six-layer board through the CLI; skipped without KiCad Python."""

    def test_cli_measures_v1_board_with_minimal_spec(self):
        python = kicad_python()
        if python is None:
            self.skipTest('KiCad Python with pcbnew unavailable')
        if not V1_BOARD.is_file():
            self.skipTest('V1 board not present')
        spec = {'schema_version': 1, 'board': 'v1', 'net_classes': {'HV_VIN': ['VIN', 'VIN_RAW'], 'HV_SW': ['SW'], 'HV_VOUT': ['VOUT'], 'CTRL_SELV': ['3V3', '1V9', 'ADC_*']},
                'class_groups': {'HV': ['HV_VIN', 'HV_SW', 'HV_VOUT'], 'CTRL_SELV': ['CTRL_SELV']},
                'isolation': {'pairs': [{'name': 'HV to control', 'a': ['HV'], 'b': ['CTRL_SELV'], 'min_mm': None}]},
                'commutation': {'vin_net': 'VIN', 'pgnd_net': 'GND', 'sw_net': 'SW', 'hf_capacitor_refs': ['C15', 'C16'], 'hf_capacitor_nets': ['VIN', 'GND'],
                                'mosfets': [{'ref': 'Q1', 'drain_pad': '2', 'source_pad': '3', 'gate_pad': '1'}]},
                'sensing': {'sw_net': 'SW', 'kelvin_pairs': [{'name': 'ISENSE', 'nets': ['ISENSE_P', 'ISENSE_N']}], 'parts': ['R9']},
                'control': {'section_groups': ['CTRL_SELV'], 'power_groups': ['HV'], 'dsp_ref': 'U16',
                            'ground': {'net': 'GND', 'layers': ['In1.Cu', 'In4.Cu'], 'min_area_mm2': 62000, 'require_copper_at': [[50.0, 100.0]], 'forbid_copper_at': [[145.0, 45.0]]}},
                'compactness': {'rated_power_W': 1000, 'component_heights_mm': {'default': 2.0}}}
        with tempfile.TemporaryDirectory(prefix='aipe v1 layout ') as folder:
            spec_path = Path(folder) / 'spec.json'
            spec_path.write_text(json.dumps(spec), encoding='utf-8')
            before = V1_BOARD.stat().st_mtime_ns
            result = subprocess.run([str(python), str(ROOT / 'automation/verification/check_sic_layout.py'), str(V1_BOARD), '--spec', str(spec_path),
                                     '--model', str(V1_MODEL), '--output', folder, '--backend', 'numpy'],
                                    cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
            self.assertEqual(result.returncode, 0, msg=result.stdout[-3000:] + result.stderr[-3000:])
            self.assertEqual(V1_BOARD.stat().st_mtime_ns, before)  # read-only
            metrics = json.loads((Path(folder) / 'layout_metrics_v1.json').read_text(encoding='utf-8'))
            self.assertTrue((Path(folder) / 'layout_metrics_v1.md').is_file())
        board = metrics['board']
        self.assertEqual((board['footprints'], board['copper_layers'], board['thickness_mm']), (240, 6, 2.0))
        self.assertEqual(board['outline_mm'], [300.0, 220.0])
        self.assertEqual(board['copper_um']['F.Cu'], 70.0)
        self.assertEqual({r['rule'] for r in metrics['rule_table']}, set(cl.RULES))
        ground = metrics['control']['ground']['per_layer']
        self.assertGreater(ground['In1.Cu']['area_mm2'], 62000)
        self.assertTrue(ground['In4.Cu']['probes']['required'][0]['copper'])
        self.assertFalse(ground['In4.Cu']['probes']['forbidden'][0]['copper'])
        self.assertEqual(len(metrics['control']['dsp_bypass']), 26)
        self.assertLess(max(b['distance_mm'] for b in metrics['control']['dsp_bypass']), 10.0)
        pair = metrics['isolation']['pairs'][0]
        self.assertEqual(set(pair['per_layer']), set(board['layers']))
        self.assertTrue(all(e['distance_mm'] is not None and e['distance_mm'] > 0 for e in pair['per_layer'].values()))
        self.assertIsNone(pair['within_threshold'])
        self.assertEqual(metrics['summary']['exceeding_threshold'], 0)
        self.assertGreater(metrics['commutation']['mosfets'][0]['pins']['drain']['nearest_same_net_mm'], 0)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--synthetic':
        print(json.dumps(synthetic_scenario(sys.argv[2])))
    else:
        unittest.main()
