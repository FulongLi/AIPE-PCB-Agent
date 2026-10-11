"""Tests for the reusable grid router.

Pure-Python parts (grid sizing, occupancy merging, dilation, path compression,
A* on a tiny numpy grid, plan validation) run with the host interpreter. The
synthetic-board part needs KiCad: it runs this file with KiCad's bundled Python
(``--synthetic <dir>``), builds a 60 x 40 mm four-layer board from official
footprints, routes it with ``run_plan``, saves and reloads it and runs
``kicad-cli pcb drc`` (without schematic parity, there is no schematic). It is
skipped, never passed, when pcbnew or kicad-cli is unavailable.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.kicad_tools import grid_router as gr
from automation.setup.detect_kicad import find_kicad_cli, read_config

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is a repository requirement
    np = None


class ShapeTests(unittest.TestCase):
    def test_grid_shape_matches_v1_board_and_scales(self):
        self.assertEqual(gr.grid_shape(300, 220, 0.25), (1201, 881))
        self.assertEqual(gr.grid_shape(60, 40, 0.25), (241, 161))
        self.assertEqual(gr.grid_shape(60, 40, 0.5), (121, 81))
        with self.assertRaises(ValueError):
            gr.grid_shape(0, 40, 0.25)

    def test_default_directions_alternate_on_inner_layers(self):
        self.assertEqual(gr.default_directions(4), [None, 'h', 'v', None])
        self.assertEqual(gr.default_directions(6), [None, 'h', 'v', 'h', 'v', None])
        self.assertEqual(gr.default_directions(2), [None, None])

    def test_sort_keys(self):
        self.assertLess(gr.pad_sort_key('2'), gr.pad_sort_key('10'))
        self.assertLess(gr.pad_sort_key('10'), gr.pad_sort_key('A1'))
        self.assertLess(gr.natural_ref_key('C2'), gr.natural_ref_key('C10'))

    def test_compress_path_merges_runs_and_places_vias(self):
        path = [(0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0), (2, 2, 0), (2, 2, 1), (3, 2, 1)]
        self.assertEqual(gr.compress_path(path), ([(0, 0, 2, 0, 0), (2, 0, 2, 2, 0), (2, 2, 3, 2, 1)], [(2, 2)]))
        self.assertEqual(gr.compress_path([(1, 1, 0)]), ([], []))


@unittest.skipIf(np is None, 'numpy unavailable')
class GridTests(unittest.TestCase):
    def grid(self):
        return gr.Grid(21, 11, 2, grid=0.25, margin_cells=1)

    def test_arrays_are_sized_from_the_board_and_framed(self):
        g = gr.Grid(*gr.grid_shape(60, 40, 0.25), 4, grid=0.25, margin_cells=4)
        self.assertEqual(g.occ.shape, (4, 161, 241))
        self.assertEqual(g.vocc.shape, (161, 241))
        self.assertTrue((g.occ[:, :4, :] == -1).all() and (g.occ[:, :, -4:] == -1).all())
        self.assertEqual(int(g.occ[0, 80, 120]), 0)
        self.assertTrue(g.inside(4, 4) and not g.inside(3, 4) and not g.inside(237, 80))
        self.assertEqual(g.to_grid(30.0, 20.0), (120, 80))
        self.assertEqual(g.to_mm(120, 80), (30.0, 20.0))

    def test_merge_marks_conflicts_as_blocked(self):
        g = self.grid()
        g.box(g.occ[0], (1.0, 1.0, 2.0, 2.0), 0, 5)
        g.box(g.occ[0], (1.5, 1.5, 3.0, 3.0), 0, 6)
        g.box(g.occ[0], (1.0, 1.0, 2.0, 2.0), 0, 5)
        self.assertEqual(int(g.occ[0, 4, 4]), 5)
        self.assertEqual(int(g.occ[0, 7, 7]), -1)
        self.assertEqual(int(g.occ[0, 9, 9]), 6)
        self.assertEqual(int(g.occ[0, 10, 10]), -1)
        g.segment(g.vocc, (1.0, 1.0), (3.0, 1.0), 0.3, 9)
        self.assertEqual(int(g.vocc[4, 8]), 9)
        self.assertEqual(int(g.vocc[6, 8]), 0)

    def test_dilate_is_conservative(self):
        mask = np.zeros((7, 7), dtype=bool)
        mask[3, 3] = True
        self.assertEqual(int(gr.dilate(mask, 0).sum()), 1)
        self.assertEqual(int(gr.dilate(mask, 1).sum()), 5)
        self.assertEqual(int(gr.dilate(mask, 0.2).sum()), 5)
        self.assertEqual(int(gr.dilate(mask, 2).sum()), 13)
        self.assertEqual(int(gr.dilate(np.zeros((3, 3), dtype=bool), 2).sum()), 0)

    def test_astar_detours_around_a_wall(self):
        g = self.grid()
        g.occ[0, 2:9, 10] = -1
        path = g.astar((2, 5, 0), (18, 5, 0), 7, (0,))
        self.assertEqual((path[0], path[-1]), ((2, 5, 0), (18, 5, 0)))
        self.assertEqual(len(path), 25)
        self.assertTrue(all(n[2] == 0 for n in path))
        self.assertTrue(all(n[0] != 10 or n[1] in (1, 9) for n in path))

    def test_astar_changes_layer_only_when_allowed(self):
        g = self.grid()
        g.occ[0, :, 10] = -1
        self.assertIsNone(g.astar((2, 5, 0), (18, 5, 0), 7, (0,)))
        path = g.astar((2, 5, 0), (18, 5, 0), 7, (0, 1))
        segments, vias = gr.compress_path(path)
        self.assertEqual({n[2] for n in path}, {0, 1})
        self.assertEqual(len(vias), 2)
        g.vocc[:, :] = -1
        self.assertIsNone(g.astar((2, 5, 0), (18, 5, 0), 7, (0, 1)))
        g.transitions[5, 9] = 7
        g.transitions[5, 18] = 7
        self.assertIsNotNone(g.astar((2, 5, 0), (18, 5, 0), 7, (0, 1)))

    def test_astar_own_code_is_passable_and_limits_apply(self):
        g = self.grid()
        g.occ[0, :, 10] = 7
        path = g.astar((2, 5, 0), (18, 5, 0), 7, (0,))
        self.assertEqual(len(path), 17)
        self.assertIsNone(g.astar((2, 5, 0), (18, 5, 0), 3, (0,)))
        self.assertIsNone(g.astar((2, 5, 0), (18, 5, 0), 7, (0,), max_nodes=3))
        g.occ[0, :, 10] = -1
        g.occ[0, 5, 10] = 0
        self.assertIsNone(g.astar((2, 3, 0), (18, 3, 0), 7, (0,), margin=1))
        self.assertIsNotNone(g.astar((2, 3, 0), (18, 3, 0), 7, (0,), margin=3))

    def test_astar_dilation_closes_narrow_gaps(self):
        g = self.grid()
        g.occ[0, :, 10] = 3
        g.occ[0, 4:7, 10] = 0
        self.assertIsNotNone(g.astar((2, 5, 0), (18, 5, 0), 7, (0,)))
        self.assertIsNone(g.astar((2, 5, 0), (18, 5, 0), 7, (0,), extra=2))

    def test_astar_any_layer_endpoints(self):
        g = self.grid()
        g.occ[0, :, 10] = -1
        path = g.astar((2, 5, None), (18, 5, None), 7, (0, 1))
        self.assertEqual(path[0][2], 1)
        self.assertTrue(all(n[2] == 1 for n in path))
        self.assertEqual(gr.compress_path(path)[1], [])


class PlanTests(unittest.TestCase):
    def plan(self):
        return {'board': {'width': 60, 'height': 40}, 'layers': ['F.Cu', 'B.Cu']}

    def test_valid_plan_is_copied(self):
        plan = self.plan()
        self.assertEqual(gr.validate_plan(plan), plan)
        self.assertIsNot(gr.validate_plan(plan), plan)

    def test_invalid_plans_are_rejected(self):
        cases = {
            'unknown key': dict(self.plan(), routes=[]),
            'missing board': {'layers': ['F.Cu']},
            'negative size': {'board': {'width': -1, 'height': 40}, 'layers': ['F.Cu']},
            'no layers': {'board': {'width': 60, 'height': 40}, 'layers': []},
            'via drill': dict(self.plan(), via=[0.3, 0.6]),
            'keepout rect': dict(self.plan(), keepouts=[{'rect': [0, 0, 1]}]),
            'ground without layers': dict(self.plan(), ground={'net': 'GND'}),
            'power zone points': dict(self.plan(), power={'VIN': {'zones': {'F.Cu': [[0, 0], [1, 1]]}}}),
        }
        for label, plan in cases.items():
            with self.subTest(label):
                with self.assertRaises(ValueError):
                    gr.validate_plan(plan)


# ----- synthetic KiCad board ------------------------------------------------------------------
def kicad_python():
    """Interpreter with pcbnew: AIPE_KICAD_PYTHON, local-tools.json, next to kicad-cli, or this one."""
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


def native_drc(cli, board_path, report_path):
    """Run kicad-cli pcb drc (no schematic parity: the synthetic board has no schematic)."""
    command = [str(cli), 'pcb', 'drc', '--format', 'json', '--severity-all', '--exit-code-violations',
               '--refill-zones', '--output', str(report_path), str(board_path)]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
    data = json.loads(Path(report_path).read_text(encoding='utf-8-sig'))
    describe = lambda group: [f"{v.get('type')}: {v.get('description')}" for v in group]
    return dict(exit_code=result.returncode, violations=len(data['violations']), unconnected=len(data['unconnected_items']),
                parity=len(data.get('schematic_parity', [])), details=describe(data['violations']) + describe(data['unconnected_items']),
                command=command)


SYNTHETIC_PARTS = [
    # ref, library, footprint, (x, y), angle, {pad: net}, side
    ('U1', 'Package_SO', 'SOIC-16_3.9x9.9mm_P1.27mm', (17, 20), 0,
     {'1': 'VDD', '2': 'IN_A', '3': 'IN_B', '4': 'GND', '5': 'FAULT', '8': 'GND', '9': 'KS', '13': 'GND', '14': 'VDD', '16': 'GATE_DRV'}, 'F'),
    ('J1', 'Connector_PinHeader_2.54mm', 'PinHeader_2x05_P2.54mm_Vertical', (6, 8), 0,
     {'1': 'VDD', '2': 'GND', '3': 'IN_A', '4': 'GND', '5': 'IN_B', '6': 'GND', '7': 'KS', '8': 'GND', '9': 'FAULT', '10': 'GND'}, 'F'),
    ('Q1', 'Package_TO_SOT_THT', 'TO-247-4_Vertical', (38, 12), 0, {'1': 'GATE', '2': 'VBUS', '3': 'SW', '4': 'KS'}, 'F'),
    ('C1', 'Capacitor_SMD', 'C_0805_2012Metric', (17, 27.5), 0, {'1': 'VDD', '2': 'GND'}, 'F'),
    ('C2', 'Capacitor_SMD', 'C_0805_2012Metric', (17, 20), 90, {'1': 'VDD', '2': 'GND'}, 'B'),
    ('R1', 'Resistor_SMD', 'R_0805_2012Metric', (26, 16), 0, {'1': 'GATE_DRV', '2': 'GATE'}, 'F'),
    ('R2', 'Resistor_SMD', 'R_0805_2012Metric', (26, 20), 0, {'1': 'GATE', '2': 'KS'}, 'F'),
    ('R3', 'Resistor_SMD', 'R_0805_2012Metric', (44, 24), 0, {'1': 'VBUS', '2': 'SW'}, 'F'),
    ('H1', 'MountingHole', 'MountingHole_3.2mm_M3_Pad', (54, 34), 0, {}, 'F'),
]

SYNTHETIC_PLAN = {
    'board': {'width': 60, 'height': 40},
    'layers': ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'],
    'net_rules': {'VBUS': {'width': 1.0, 'clearance': 0.5}, 'SW': {'width': 1.0}, 'GATE': {'width': 0.3}, 'GATE_DRV': {'width': 0.3}},
    'keepouts': [{'layer': None, 'rect': [50, 28, 58, 38], 'net': None}],
    'pre_routed': {'via_arrays': [{'net': 'GND', 'origin': [30, 32], 'pitch': [1.5, 1.5], 'count': [3, 2]}],
                   'vias': [{'net': 'GND', 'xy': [36, 32], 'if_allowed': True}],
                   'tracks': [{'net': 'GND', 'layer': 'B.Cu', 'a': [30, 32], 'b': [33, 32]}]},
    'fanout': {'order': ['U1']},
    'critical': ['GATE_DRV', 'GATE', 'KS'],
    'critical_layers': ['F.Cu', 'B.Cu'],
    'power': {'VDD': {'anchors': ['C1'], 'zones': {'In2.Cu': [[2, 2], [58, 2], [58, 38], [2, 38]]}},
              'VBUS': {'anchors': ['Q1']}},
    'signal_order': ['IN_', 'FAULT', 'SW'],
    'ground': {'net': 'GND', 'layers': ['In1.Cu', 'B.Cu']},
}

RULES = {'min_clearance': 0.15, 'min_track_width': 0.15, 'min_via_diameter': 0.55, 'min_through_hole_diameter': 0.25,
         'min_hole_clearance': 0.25, 'min_hole_to_hole': 0.25, 'min_copper_edge_clearance': 0.5, 'min_via_annular_width': 0.1}


def synthetic_scenario(out_dir):
    """Build, route, save, reload and DRC the synthetic board; returns a JSON-serialisable summary."""
    import pcbnew as pcb
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    cli = find_kicad_cli()
    data = Path(os.environ.get('AIPE_KICAD_DATA', str(cli.parent.parent / 'share/kicad'))) if cli else None
    if data is None or not (data / 'footprints').is_dir():
        raise FileNotFoundError('KiCad footprint library not found')
    board = pcb.BOARD(); board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(pcb.FromMM(1.6))
    net_names = sorted({net for *_, pins, _side in SYNTHETIC_PARTS for net in pins.values()})
    nets = {}
    for name in net_names:
        nets[name] = pcb.NETINFO_ITEM(board, name); board.Add(nets[name])
    point = lambda x, y: pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))
    libraries = set()
    for ref, lib, name, (x, y), angle, pins, side in SYNTHETIC_PARTS:
        fp = pcb.FootprintLoad(str(data / 'footprints' / f'{lib}.pretty'), name)
        if fp is None:
            raise FileNotFoundError(f'{lib}:{name}')
        libraries.add(lib)
        fp.SetFPID(pcb.LIB_ID(lib, name)); fp.SetReference(ref); fp.SetValue(name)
        board.Add(fp)
        if side == 'B':
            fp.Flip(point(0, 0), False)
        fp.Reference().SetLayer(pcb.B_Fab if side == 'B' else pcb.F_Fab); fp.Value().SetVisible(False)
        fp.SetOrientationDegrees(angle); fp.SetPosition(point(x, y))
        for pad in fp.Pads():
            if pad.GetNumber() in pins:
                pad.SetNet(nets[pins[pad.GetNumber()]])
    for a, b in [((0, 0), (60, 0)), ((60, 0), (60, 40)), ((60, 40), (0, 40)), ((0, 40), (0, 0))]:
        edge = pcb.PCB_SHAPE(board); edge.SetShape(pcb.SHAPE_T_SEGMENT); edge.SetStart(point(*a)); edge.SetEnd(point(*b))
        edge.SetLayer(pcb.Edge_Cuts); edge.SetWidth(pcb.FromMM(0.05)); board.Add(edge)
    name = 'grid_router_synthetic'
    table = ['(fp_lib_table (version 7)'] + [
        f'(lib (name "{lib}") (type "KiCad") (uri "{(data / "footprints" / (lib + ".pretty")).as_posix()}") (options "") (descr "KiCad library"))'
        for lib in sorted(libraries)] + [')']
    (out_dir / 'fp-lib-table').write_text('\n'.join(table) + '\n', encoding='utf-8')
    (out_dir / f'{name}.kicad_pro').write_text(json.dumps({
        'meta': {'filename': f'{name}.kicad_pro', 'version': 1},
        'net_settings': {'classes': [
            {'name': 'Default', 'clearance': 0.2, 'track_width': 0.2, 'via_diameter': 0.6, 'via_drill': 0.3},
            {'name': 'HV', 'clearance': 0.5, 'track_width': 1.0, 'via_diameter': 0.6, 'via_drill': 0.3}],
            'netclass_patterns': [{'netclass': 'HV', 'pattern': 'VBUS'}], 'version': 4},
        'board': {'design_settings': {'rules': RULES}},
    }, indent=2) + '\n', encoding='utf-8')
    plan = dict(SYNTHETIC_PLAN, save=str(out_dir / f'{name}.kicad_pcb'))
    report = gr.run_plan(board, plan)
    loaded = pcb.LoadBoard(plan['save'])
    widths = {}
    for item in loaded.GetTracks():
        if not isinstance(item, pcb.PCB_VIA):
            widths.setdefault(item.GetNetname(), set()).add(round(pcb.ToMM(item.GetWidth()), 3))
    by_layer = {loaded.GetLayerName(l): sum(1 for t in loaded.GetTracks() if not isinstance(t, pcb.PCB_VIA) and t.GetLayer() == l)
                for l in loaded.GetEnabledLayers().CuStack()}
    back_pads = sum(1 for fp in loaded.GetFootprints() for pad in fp.Pads() if pad.IsOnLayer(pcb.B_Cu) and not pad.IsOnLayer(pcb.F_Cu))
    # A second router on the reloaded board must register every existing track and via as occupancy.
    again = gr.Router(loaded, 60, 40, SYNTHETIC_PLAN['layers'], net_rules=SYNTHETIC_PLAN['net_rules'])
    reregistered = dict(vias=len(again.vias), net_length_mm={k: round(v, 3) for k, v in sorted(again.length.items())},
                        ports=len(again.ports), blocked_cells=int((again.grid.occ != 0).sum()))
    summary = dict(report=report, track_widths={k: sorted(v) for k, v in sorted(widths.items())}, tracks_by_layer=by_layer,
                   back_side_pads=back_pads, reregistered=reregistered, out_dir=str(out_dir))
    if cli:
        summary['drc'] = native_drc(cli, plan['save'], out_dir / 'drc.json')
    return summary


class SyntheticBoardTests(unittest.TestCase):
    """End-to-end routing of a real pcbnew board; skipped without KiCad."""

    def test_synthetic_board_routes_cleanly_and_passes_native_drc(self):
        python = kicad_python()
        if python is None:
            self.skipTest('KiCad Python with pcbnew unavailable')
        with tempfile.TemporaryDirectory(prefix='aipe grid router ') as folder:
            result = subprocess.run([str(python), str(Path(__file__).resolve()), '--synthetic', folder], cwd=str(ROOT),
                                    capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
            self.assertEqual(result.returncode, 0, msg=result.stdout[-4000:] + result.stderr[-4000:])
            summary = json.loads(result.stdout.strip().splitlines()[-1])
        report = summary['report']
        self.assertEqual(report['unresolved'], [])
        self.assertGreater(report['tracks'], 0)
        self.assertGreater(report['vias'], 0)
        self.assertEqual(report['zones'], 3)
        self.assertEqual(report['saved']['footprints'], len(SYNTHETIC_PARTS))
        self.assertEqual(report['saved']['zones'], 3)
        self.assertEqual(report['grid']['layers'], SYNTHETIC_PLAN['layers'])
        self.assertEqual(summary['track_widths']['VBUS'], [1.0])
        self.assertEqual(summary['track_widths']['GATE'], [0.3])
        self.assertIn('GND', summary['track_widths'])
        self.assertIn('KS', report['net_length_mm'])
        self.assertEqual(summary['back_side_pads'], 2)
        self.assertGreaterEqual(summary['tracks_by_layer']['B.Cu'], 1)
        self.assertEqual(summary['reregistered']['vias'], report['vias'])
        self.assertEqual(summary['reregistered']['net_length_mm'], report['net_length_mm'])
        if 'drc' not in summary:
            self.skipTest('kicad-cli unavailable; routing checked without native DRC')
        self.assertEqual((summary['drc']['violations'], summary['drc']['unconnected']), (0, 0), msg=summary['drc']['details'])
        self.assertEqual(summary['drc']['exit_code'], 0)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--synthetic':
        print(json.dumps(synthetic_scenario(sys.argv[2])))
    else:
        unittest.main()
