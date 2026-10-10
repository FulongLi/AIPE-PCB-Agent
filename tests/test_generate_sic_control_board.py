"""Tests for the V2 control-board generator (automation.kicad_tools.generate_sic_control_board).

Pure-Python parts run with the host interpreter: candidate loading and validation (regions, rectilinear
islands, disjoint islands, every model part assigned), the LQFP escape planner (alternation along pin runs,
core-rail pins inward / I/O-rail pins outward where parity allows, grid-snapped vias, via spacing), the
In2.Cu corridor geometry, the routing plan (validated by grid_router.validate_plan), the stackup arithmetic,
the Manhattan MST and the candidate scoring. The pcbnew part runs this file under KiCad's bundled Python
(``--place <dir>``): it places candidate B unrouted into a temporary directory without touching the
repository outputs and checks the placement summary. A further test reads the recorded routing evidence of
the repository board when present and checks that the DRC manifest it names exists, matches the board's
hash and reports zero findings; it skips, never passes, when the evidence is absent. Skips are never passes.
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

from automation.kicad_tools import generate_sic_control_board as g  # noqa: E402
from automation.kicad_tools import grid_router as gr  # noqa: E402
from automation.setup.detect_kicad import find_kicad_cli, read_config  # noqa: E402


def kicad_python():
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
    return None


def lqfp_side(net_pattern, x=55.325, y0=22.25, size=(1.5, 0.3), start=1):
    """Synthetic west-side LQFP pad list: one pad per character of ``net_pattern`` (S signal, G ground, 9 core, 3 I/O, . none)."""
    names = {'S': 'SIG', 'G': 'GND_CTRL', '9': '1V9', '3': '3V3'}
    pads = []
    for i, ch in enumerate(net_pattern):
        if ch == '.':
            continue
        net = names[ch] if ch != 'S' else f'SIG{i}'
        pads.append(dict(number=str(start + i), net=net, xy=(x, y0 + 0.5 * i), size=size))
    return pads


class CandidateTests(unittest.TestCase):
    def test_candidates_load_validate_and_cover_the_model(self):
        parts = g.load_parts()
        self.assertEqual(len(parts), 207)
        for cid in ('A', 'B'):
            cand = g.load_candidate(g.candidate_path(cid))
            self.assertEqual(cand['id'], cid)
            self.assertEqual(g.islands_overlap(cand), [], cid)
            report = g.assignment_report(parts, cand)
            self.assertEqual(report['unassigned'], [], cid)
            self.assertEqual(len(report['bypass']), 26, cid)
            self.assertIn('U5', report['fixed'])
            placed = set(report['fixed']) | set(report['bypass']) | {r for refs in report['regions'].values() for r in refs}
            self.assertEqual(placed, {p['ref'] for p in parts}, cid)
            for net in g.RAILS:
                self.assertIn(net, cand['islands'])
            self.assertEqual(cand['islands']['3V3'], 'background')
        a, b = g.load_candidate(g.candidate_path('A')), g.load_candidate(g.candidate_path('B'))
        self.assertNotEqual(a['dsp']['angle'], b['dsp']['angle'])

    def test_candidate_validation_rejects_bad_geometry(self):
        cand = g.load_candidate(g.candidate_path('B'))
        with tempfile.TemporaryDirectory() as tmp:
            bad = dict(cand)
            bad['islands'] = dict(cand['islands'], **{'5V': [[24.0, 15.0], [43.5, 16.0], [43.5, 34.0], [24.0, 34.0]]})  # not rectilinear
            path = Path(tmp) / 'bad.json'
            path.write_text(json.dumps(bad), encoding='utf-8')
            with self.assertRaises(ValueError):
                g.load_candidate(path)
            bad = dict(cand)
            bad['regions'] = dict(cand['regions'], **{'logic': [[0.5, 55.0, 86.5, 70.8]]})  # inside the edge margin
            path.write_text(json.dumps(bad), encoding='utf-8')
            with self.assertRaises(ValueError):
                g.load_candidate(path)
        overlapping = dict(cand, islands=dict(cand['islands'], **{'5V': [[20.0, 10.0], [60.0, 10.0], [60.0, 30.0], [20.0, 30.0]]}))
        self.assertTrue(g.islands_overlap(overlapping))


class EscapePlanTests(unittest.TestCase):
    def test_alternation_and_rail_preferences(self):
        centre = (68.0, 33.0)
        pads = lqfp_side('SG9SSSG3SSSS')  # one run of 12 connected pins at 0.5 mm pitch
        records = g.plan_dsp_escapes(pads, centre)
        self.assertEqual(len(records), 12)
        directions = [r['direction'] for r in sorted(records, key=lambda r: r['lateral'])]
        for a, b in zip(directions, directions[1:]):
            self.assertNotEqual(a, b, 'adjacent pins must alternate inward/outward')
        by_net = {r['net']: r for r in records}
        self.assertEqual(by_net['1V9']['direction'], 'in')
        self.assertEqual(by_net['3V3']['direction'], 'out')
        self.assertFalse(any(r['exception'] for r in records))
        for r in records:
            self.assertAlmostEqual(r['via'][0] / g.ESCAPE_GRID, round(r['via'][0] / g.ESCAPE_GRID), places=6)
            self.assertAlmostEqual(r['via'][1], r['lateral'])
            if r['direction'] == 'in':
                self.assertGreater(r['via'][0], r['pad'][0])  # west side: inward is +x
            else:
                self.assertLess(r['via'][0], r['pad'][0])
        outward = sorted((r for r in records if r['direction'] == 'out'), key=lambda r: r['lateral'])
        distances = [r['distance'] for r in outward]
        self.assertEqual(distances, [g.ESCAPE_OUT[i % 2] for i in range(len(outward))])
        for i, a in enumerate(records):
            for b in records[i + 1:]:
                self.assertGreaterEqual(((a['via'][0] - b['via'][0]) ** 2 + (a['via'][1] - b['via'][1]) ** 2) ** 0.5, g.VIA[0] + g.CLEARANCE - 1e-6)

    def test_parity_conflict_is_flagged_and_runs_split_at_unconnected_pins(self):
        centre = (68.0, 33.0)
        records = g.plan_dsp_escapes(lqfp_side('9S3'), centre)  # core and I/O pins two apart: same parity
        self.assertEqual(sum(r['exception'] for r in records), 1)
        core = next(r for r in records if r['net'] == '1V9')
        self.assertEqual(core['direction'], 'in')  # the core pin wins (weight 2)
        records = g.plan_dsp_escapes(lqfp_side('9S.9S'), centre)  # two runs: both core pins can go inward
        self.assertEqual([r['direction'] for r in sorted(records, key=lambda r: r['lateral'])], ['in', 'out', 'in', 'out'])

    def test_off_grid_lateral_is_rejected(self):
        pads = lqfp_side('SS', y0=22.3)
        with self.assertRaises(ValueError):
            g.plan_dsp_escapes(pads, (68.0, 33.0))


class CorridorTests(unittest.TestCase):
    ISLANDS = {'1V9': [[10.0, 10.0], [20.0, 10.0], [20.0, 20.0], [10.0, 20.0]], '3V3': 'background'}

    def test_items_in_their_own_territory_need_nothing(self):
        result = g.island_corridors([dict(net='1V9', xy=[15.0, 15.0], kind='via'), dict(net='3V3', xy=[30.0, 30.0], kind='via')], self.ISLANDS)
        self.assertEqual(result, dict(corridors=[], issues=[]))

    def test_notch_and_finger_corridors(self):
        items = [dict(net='3V3', xy=[18.5, 15.0], kind='via'),   # I/O via inside the core island: notch to the east edge
                 dict(net='1V9', xy=[22.0, 12.0], kind='via')]   # core via outside: finger to the island
        result = g.island_corridors(items, self.ISLANDS)
        self.assertEqual(result['issues'], [])
        self.assertEqual([c['net'] for c in result['corridors']], ['3V3', '1V9'])
        notch, finger = result['corridors']
        self.assertEqual(notch['direction'], [1, 0])
        box = g.polygon_bbox(notch['polygon'])
        self.assertTrue(box[0] <= 18.5 <= box[2] and box[1] <= 15.0 <= box[3])
        self.assertGreater(box[2], 20.0)  # reaches beyond the island edge into the background
        self.assertAlmostEqual(box[3] - box[1], 2 * g.CORRIDOR_HALF_WIDTH)
        self.assertEqual(finger['direction'], [-1, 0])
        fbox = g.polygon_bbox(finger['polygon'])
        self.assertLess(fbox[0], 20.0)  # enters the island
        self.assertTrue(fbox[0] <= 22.0 <= fbox[2])

    def test_blocked_corridor_is_reported(self):
        items = [dict(net='3V3', xy=[15.0, 15.0], kind='via')]
        items += [dict(net='1V9', xy=[15.0 + dx, 15.0 + dy], kind='via') for dx, dy in ((0.7, 0), (-0.7, 0), (0, 0.7), (0, -0.7))]
        result = g.island_corridors(items, self.ISLANDS)
        self.assertEqual(result['corridors'], [])
        self.assertEqual(len(result['issues']), 1)
        self.assertIn('severed', result['issues'][0]['reason'])
        far = [dict(net='3V3', xy=[15.0, 15.0], kind='via'), dict(net='1V9', xy=[15.0, 16.0], kind='via')]  # 1.0 mm beside: allowed
        self.assertEqual(len(g.island_corridors(far, self.ISLANDS)['corridors']), 1)

    def test_l_shaped_corridor_around_a_foreign_via(self):
        # 1V9 via 2 mm east of the core island; a signal via sits on the straight path to the island edge
        items = [dict(net='1V9', xy=[22.0, 12.0], kind='via')]
        obstacles = [dict(net='SIG', xy=[21.0, 12.0], r=0.3)]
        result = g.island_corridors(items, self.ISLANDS, obstacles=obstacles)
        self.assertEqual(result['issues'], [])
        self.assertEqual([c.get('leg') for c in result['corridors']], [1, 2])
        leg1, leg2 = result['corridors']
        self.assertNotEqual(leg1['priority'], leg2['priority'])  # overlapping same-net zones need distinct priorities
        self.assertTrue(min(leg1['priority'], leg2['priority']) >= g.CORRIDOR_PRIORITY)
        self.assertEqual(leg1['direction'][0], 0)  # lateral first leg
        self.assertEqual(leg2['direction'], [-1, 0])  # then west into the island
        b1, b2 = g.polygon_bbox(leg1['polygon']), g.polygon_bbox(leg2['polygon'])
        self.assertTrue(b1[0] <= 22.0 <= b1[2] and b1[1] <= 12.0 <= b1[3])  # covers the via
        self.assertLess(b2[0], 20.0)  # enters the island
        self.assertGreaterEqual(min(abs(b2[1] - 12.0), abs(b2[3] - 12.0)), 0.55)  # second leg clears the signal via ring
        self.assertEqual(g.uncovered_rail_items(items, self.ISLANDS, result['corridors']), [])
        self.assertEqual(len(g.uncovered_rail_items(items, self.ISLANDS, [])), 1)
        # foreign vias on both lateral legs: no corridor, one issue
        wider = g.island_corridors(items, self.ISLANDS, obstacles=obstacles + [dict(net='SIG', xy=[22.0, 13.5], r=0.3), dict(net='SIG', xy=[22.0, 10.5], r=0.3)])
        self.assertEqual(wider['corridors'], [])
        self.assertEqual(len(wider['issues']), 1)


class PlanAndHelperTests(unittest.TestCase):
    def test_routing_plan_validates_and_carries_the_escapes(self):
        cand = g.load_candidate(g.candidate_path('B'))
        pads = lqfp_side('SG9S3S')
        escapes = g.plan_dsp_escapes(pads, (68.0, 33.0))
        plan = g.routing_plan(cand, escapes, 'x.kicad_pcb', ic_refs=['U5', 'U1', 'U2'])
        checked = gr.validate_plan(plan)
        self.assertEqual(checked['layers'], ['F.Cu', 'B.Cu'])
        self.assertEqual(len(plan['pre_routed']['tracks']), len(escapes))
        self.assertTrue(all(v['port'] for v in plan['pre_routed']['vias']))
        self.assertEqual(plan['fanout']['skip_refs'], ['U5'])
        self.assertEqual(plan['fanout']['order'][0], 'U5')
        self.assertEqual(set(plan['power']), set(g.RAILS))
        self.assertEqual(plan['ground']['layers'], ['In1.Cu'])
        self.assertEqual(plan['power']['1V9']['zones']['In2.Cu'], cand['islands']['1V9'])
        self.assertEqual(plan['power']['3V3']['zones']['In2.Cu'], g.background_polygon())
        self.assertGreaterEqual(plan['grid'], 0.1)
        self.assertEqual(plan['via'], [0.6, 0.3])

    def test_stackup_text_and_geometry_helpers(self):
        self.assertAlmostEqual(g.stackup_thickness_mm(), 1.6)
        text = g.stackup_text()
        self.assertIn('(layer "In1.Cu" (type "copper") (thickness 0.035))', text)
        self.assertIn('(copper_finish "ENIG")', text)
        self.assertEqual(g.manhattan_mst([(0, 0), (3, 0), (3, 4)]), 7.0)
        self.assertEqual(g.manhattan_mst([(1, 1)]), 0.0)
        self.assertTrue(g.point_in_polygon((5, 5), [[0, 0], [10, 0], [10, 10], [0, 10]]))
        self.assertFalse(g.point_in_polygon((15, 5), [[0, 0], [10, 0], [10, 10], [0, 10]]))
        box = g.text_box('BOOT', (45.0, 39.0), 0.8)
        self.assertLess(box[0], 45.0 - 1.5)
        self.assertAlmostEqual(g.snap(82.075, 0.25), 82.0)
        self.assertEqual(g.box_distance((0, 0, 1, 1), (3, 0, 4, 1)), 2.0)

    def test_candidate_scoring(self):
        criteria = {'A': dict(dsp_bypass_max_mm=5.0, pwm_path_mm=200.0, tz_path_mm=180.0, analog_pwm_separation_mm=2.0, analog_path_mm=1200.0, courtyard_fraction_front=0.3),
                    'B': dict(dsp_bypass_max_mm=5.0, pwm_path_mm=100.0, tz_path_mm=160.0, analog_pwm_separation_mm=20.0, analog_path_mm=1100.0, courtyard_fraction_front=0.3)}
        scoring = g.score_candidates(criteria)
        self.assertEqual(scoring['selected'], 'B')
        self.assertEqual(scoring['scores']['B'], 0.0)
        self.assertGreater(scoring['scores']['A'], 0.0)
        tie = {'A': dict(criteria['B']), 'B': dict(criteria['B'])}
        self.assertEqual(g.score_candidates(tie)['selected'], 'A')

    def test_read_manifest_adds_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / 'drc.json'
            report.write_text(json.dumps({'$schema': 'https://schemas.kicad.org/drc.v1.json', 'violations': [{'type': 'clearance', 'description': 'x', 'items': [{'pos': {'x': 1, 'y': 2}}]}],
                                          'unconnected_items': [], 'schematic_parity': []}), encoding='utf-8')
            manifest = Path(tmp) / 'run.json'
            manifest.write_text(json.dumps({'status': 'failed', 'report': str(report), 'finding_count': 1}), encoding='utf-8')
            data = g.read_manifest(manifest)
            self.assertEqual((data['violations'], data['unconnected_items'], data['schematic_parity']), (1, 0, 0))
            self.assertTrue(data['details'][0].startswith('clearance: x'))


def place_scenario(out_dir) -> dict:
    """Place candidate B unrouted into ``out_dir`` (KiCad Python) and return a JSON-ready summary."""
    out_dir = Path(out_dir)
    result = g.build_control(g.candidate_path('B'), out_dir / f'{g.NAME}.kicad_pcb', route=False, drc=False, metrics=False, write_outputs=False)
    import pcbnew as pcb
    board = pcb.LoadBoard(str(out_dir / f'{g.NAME}.kicad_pcb'))
    sides = {}
    for fp in board.GetFootprints():
        sides[fp.GetReference()] = 'B' if fp.IsFlipped() else 'F'
    text = (out_dir / f'{g.NAME}.kicad_pcb').read_text(encoding='utf-8')
    return dict(footprints=len(result['placements']), issues=result['placement_issues'], sides=sides, copper_layers=board.GetCopperLayerCount(),
                stackup='(stackup' in text, nets=result['nets'], estimates={k: v for k, v in result['estimates'].items() if k.endswith('_mm') or k.endswith('fraction')},
                silkscreen=len(result['silkscreen']))


@unittest.skipUnless(kicad_python() is not None and find_kicad_cli(), 'KiCad (pcbnew + kicad-cli) not available')
class PlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        completed = subprocess.run([str(kicad_python()), str(Path(__file__).resolve()), '--place', cls.temp.name], cwd=str(ROOT),
                                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
        if completed.returncode != 0:
            raise RuntimeError(f'placement scenario failed: {completed.stdout[-2000:]}\n{completed.stderr[-4000:]}')
        cls.summary = json.loads(completed.stdout.strip().splitlines()[-1])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_part_is_placed_with_the_expected_sides_and_stack(self):
        s = self.summary
        self.assertEqual(s['footprints'], 207)
        self.assertEqual(s['copper_layers'], 4)
        self.assertTrue(s['stackup'])
        back = sorted(ref for ref, side in s['sides'].items() if side == 'B')
        self.assertEqual(len(back), 15, back)  # the fifteen 1V9 per-pin capacitors sit under the package
        self.assertEqual(s['sides']['U5'], 'F')
        self.assertGreater(s['estimates']['analog_pwm_separation_mm'], 0.0)
        self.assertEqual(s['silkscreen'], 15)


class EvidenceTests(unittest.TestCase):
    """The recorded routing evidence must be internally consistent and honest: the DRC manifest it names must exist,
    match the board's hash, carry the parity/severity flags, and its finding count must agree with the recorded
    counts; a board recorded as fully routed must have a clean manifest, a board recorded with unresolved
    connections must not be recorded as passed."""
    PROGRESS = g.VERIFICATION_DIR / 'routing_progress_control.json'

    @unittest.skipUnless(PROGRESS.is_file(), 'no recorded routing evidence')
    def test_recorded_drc_manifest_matches_the_board_and_the_recorded_state(self):
        progress = json.loads(self.PROGRESS.read_text(encoding='utf-8'))
        board = Path(progress['board'])
        self.assertTrue(board.is_file(), board)
        import hashlib
        self.assertEqual(progress['board_sha256'], hashlib.sha256(board.read_bytes()).hexdigest(), 'board changed after the recorded run')
        drc = progress.get('drc') or {}
        manifest = Path(drc.get('manifest', ''))
        self.assertTrue(manifest.is_file(), 'DRC manifest missing')
        recorded = json.loads(manifest.read_text(encoding='utf-8'))
        self.assertEqual(recorded['source_sha256'], progress['board_sha256'])
        self.assertIn('--schematic-parity', recorded['command'])
        self.assertIn('--severity-all', recorded['command'])
        self.assertEqual(recorded['finding_count'], drc['finding_count'])
        self.assertEqual(recorded['status'], drc['status'])
        if progress['unresolved_count'] == 0 and progress['stage'] == 'routed':
            self.assertEqual(recorded['status'], 'passed')
            self.assertEqual(recorded['finding_count'], 0)
        else:
            self.assertEqual(progress['stage'], 'routed_with_unresolved_connections')
            self.assertEqual(recorded['status'], 'failed')
            self.assertGreaterEqual(drc['unconnected_items'], 1)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--place':
        print(json.dumps(place_scenario(sys.argv[2])))
    else:
        unittest.main()
