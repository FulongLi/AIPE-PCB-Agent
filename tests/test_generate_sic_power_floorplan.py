"""Tests for the V2 power-board floorplan generator (automation.kicad_tools.generate_sic_power_floorplan).

Pure-Python parts run with the host interpreter: candidate loading and validation (bands, fixed poses, regions, zones,
heatsink spec), net-class assignment from the project patterns, zone-band membership of every model part, the
assignment of every model part to a fixed pose or a region in all three candidates, the net-aware spacing gaps, the
barrier slot geometry (around-the-end surface path), the ISO_BARRIER segment cutting, the heatsink corridor geometry,
the routing-plan skeleton (validated by grid_router.validate_plan), the stackup arithmetic and the candidate scoring.
The pcbnew part runs this file under KiCad's bundled Python (``--place <dir>``): it places candidate B unrouted into a
temporary directory without touching the repository outputs and checks the placement summary. A further test reads the
recorded floorplan evidence of the repository when present and checks that the board file it names exists and matches
the recorded hash; it skips, never passes, when the evidence is absent. Skips are never passes.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.kicad_tools import generate_sic_power_floorplan as g  # noqa: E402
from automation.kicad_tools import grid_router as gr  # noqa: E402
from automation.setup.detect_kicad import find_kicad_cli, read_config  # noqa: E402

CANDIDATES = ('A', 'B', 'C')


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


class NetClassTests(unittest.TestCase):
    def test_project_patterns_in_order(self):
        self.assertEqual(g.net_class('VIN_DIV_T1'), 'HV_VIN')
        self.assertEqual(g.net_class('VIN_DIV'), 'SENSE_ISO')
        self.assertEqual(g.net_class('KS_H'), 'DRV_HS')
        self.assertEqual(g.net_class('DESAT_L_OC'), 'DESAT_LS')
        self.assertEqual(g.net_class('GNDP_H'), 'CTRL_SELV')
        self.assertEqual(g.net_class('PE'), 'PE')
        self.assertIsNone(g.net_class(None))

    def test_zone_of_every_model_part(self):
        parts = g.load_parts()
        self.assertEqual(len(parts), 237)
        zones = {p['ref']: g.zone_of_part(p) for p in parts}
        self.assertEqual({r for r, z in zones.items() if z == 'BARRIER'}, set(g.BARRIER_REFS))
        self.assertEqual(zones['J7'], 'SELV')
        self.assertEqual(zones['Q1'], 'HV')
        self.assertEqual(zones['H1'], 'HV')  # PE stud belongs to the HV side of the barrier
        self.assertEqual(zones['HS1'], 'MECH')
        self.assertEqual(sum(z == 'HV' for z in zones.values()), 132)
        self.assertEqual(sum(z == 'SELV' for z in zones.values()), 86)

    def test_spacing_gaps(self):
        by_ref = {p['ref']: p for p in g.load_parts()}
        self.assertEqual(g.gap_between_parts(by_ref['R59'], by_ref['R60']), g.GAPS['HV'])  # HV divider neighbours: 3 mm rule + margin
        self.assertEqual(g.gap_between_parts(by_ref['R19'], by_ref['C22']), g.GAPS['DRV'])  # same HS island
        self.assertEqual(g.gap_between_parts(by_ref['R19'], by_ref['R37']), g.GAPS['HV'])  # HS versus LS island: 3 mm barrier
        self.assertEqual(g.gap_between_parts(by_ref['D3'], by_ref['R24']), g.GAPS['HV'])  # DESAT diode carries VIN
        self.assertEqual(g.gap_between_parts(by_ref['C18'], by_ref['R1']), g.GAPS['PE'])  # PE pad versus HV part: 5 mm rule
        self.assertEqual(g.gap_between_parts(by_ref['R17'], by_ref['C20']), g.GAPS['SELV'])
        self.assertEqual(g.gap_between_parts(by_ref['R17'], by_ref['R19']), 9.2)  # SELV versus HV: never in one band
        self.assertEqual(g.gap_between_parts(by_ref['C64'], by_ref['C66']), g.GAPS['DRV'])  # SENSE_ISO / PGND same-reference island
        self.assertEqual(g.gap_between_parts(by_ref['C22'], by_ref['U1']), g.GAPS['DRV'])  # barrier part: only its HV pins count
        self.assertEqual(g.class_pair_clearance('HV_VIN', 'HV_VIN'), 3.0)
        self.assertEqual(g.class_pair_clearance('HV_PGND', 'SENSE_ISO'), 0.3)
        self.assertEqual(g.class_pair_clearance('DRV_HS', 'DRV_LS'), 3.0)
        self.assertEqual(g.class_pair_clearance('PE', 'HV_PGND'), 5.0)


class CandidateTests(unittest.TestCase):
    def test_candidates_load_and_cover_the_model(self):
        parts = g.load_parts()
        titles = set()
        for cid in CANDIDATES:
            cand = g.load_candidate(g.candidate_path(cid))
            self.assertEqual(cand['id'], cid)
            titles.add(cand['title'])
            report = g.assignment_report(parts, cand)
            self.assertEqual(report['unassigned'], [], cid)
            self.assertEqual(report['unknown_fixed'], [], cid)
            placed = set(report['fixed']) | {r for refs in report['regions'].values() for r in refs}
            self.assertEqual(placed, {p['ref'] for p in parts}, cid)
            for ref in g.BARRIER_REFS + ('HS1', 'Q1', 'Q2', 'L1', 'C11', 'C12', 'C13', 'C14', 'J7'):
                self.assertIn(ref, cand['fixed'], f'{cid}: {ref} must be a fixed pose')
            for ref in g.BARRIER_REFS:
                self.assertAlmostEqual(cand['fixed'][ref][1], cand['bands']['barrier_line_y'], msg=f'{cid}: {ref} on the barrier line')
            self.assertAlmostEqual(cand['fixed']['Q2'][0] - cand['fixed']['Q1'][0], 28.0, msg=f'{cid}: 28 mm device pitch')
            self.assertEqual(cand['fixed']['Q1'][1], cand['fixed']['Q2'][1])
            layers = {(z['layer'], z['priority']) for z in cand['zones']}
            self.assertEqual(len(layers), len(cand['zones']), f'{cid}: zone priorities distinct per layer')
        self.assertEqual(len(titles), 3)
        a, b, c = (g.load_candidate(g.candidate_path(i)) for i in CANDIDATES)
        self.assertNotEqual(a['fixed']['HS1'][:2], b['fixed']['HS1'][:2])
        self.assertEqual(c['board_mm'], [220.0, 170.0])
        self.assertEqual(b['board_mm'], [240.0, 180.0])

    def test_candidate_validation_rejects_bad_geometry(self):
        cand = g.load_candidate(g.candidate_path('B'))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            bad = json.loads(json.dumps(cand))
            bad['bands']['selv_y_min'] = 155.0  # 25 mm SELV strip
            path.write_text(json.dumps(bad), encoding='utf-8')
            with self.assertRaises(ValueError):
                g.load_candidate(path)
            bad = json.loads(json.dumps(cand))
            bad['zones'][0]['polygon'] = [[64.0, 126.6], [92.5, 126.6], [92.5, 145.0], [64.0, 145.0]]  # HV zone into the barrier band
            path.write_text(json.dumps(bad), encoding='utf-8')
            with self.assertRaises(ValueError):
                g.load_candidate(path)
            bad = json.loads(json.dumps(cand))
            bad['fixed']['Q1'] = [62.0, 129.0, 45, 'F']  # angle not a multiple of 90
            path.write_text(json.dumps(bad), encoding='utf-8')
            with self.assertRaises(ValueError):
                g.load_candidate(path)
            bad = json.loads(json.dumps(cand))
            bad['regions']['pe_group']['side'] = 'X'
            path.write_text(json.dumps(bad), encoding='utf-8')
            with self.assertRaises(ValueError):
                g.load_candidate(path)

    def test_band_violation_logic(self):
        bands = dict(hv_y_max=140.0, barrier=[140.0, 150.0], barrier_line_y=145.0, selv_y_min=150.0)
        self.assertIsNone(g.band_violation('HV', [10, 120, 20, 139.9], bands))
        self.assertIsNotNone(g.band_violation('HV', [10, 120, 20, 141.0], bands))
        self.assertIsNotNone(g.band_violation('SELV', [10, 149.0, 20, 160.0], bands))
        self.assertIsNone(g.band_violation('BARRIER', [10, 139.0, 20, 151.0], bands))
        self.assertIsNotNone(g.band_violation('BARRIER', [10, 146.0, 20, 158.0], bands))
        self.assertIsNone(g.band_violation('MECH', [10, 140.0, 20, 150.0], bands))


class GeometryTests(unittest.TestCase):
    def test_slot_geometry_and_surface_path(self):
        hv = [[60.0, 139.75, 70.0, 140.95]]
        selv = [[60.0, 149.05, 70.0, 150.25]]
        slot = g.slot_for_pads(hv, selv)
        self.assertEqual(slot['row_axis'], 'x')
        self.assertAlmostEqual(slot['land_gap_mm'], 8.1)
        x0, y0, x1, y1 = slot['rect']
        self.assertAlmostEqual(y1 - y0, g.SLOT_WIDTH)
        self.assertAlmostEqual(x0, 60.0 - g.SLOT_EXTENSION)
        self.assertAlmostEqual(x1, 70.0 + g.SLOT_EXTENSION)
        self.assertAlmostEqual(slot['surface_path_mm'], 2 * ((8.1 / 2) ** 2 + 9.0) ** 0.5, places=3)
        self.assertGreaterEqual(slot['surface_path_mm'], 9.0)
        rotated = g.slot_for_pads([[139.75, 60.0, 140.95, 70.0]], [[149.05, 60.0, 150.25, 70.0]])
        self.assertEqual(rotated['row_axis'], 'y')

    def test_barrier_segments(self):
        segments = g.barrier_segments((1.0, 140.0, 239.0, 150.0), [(44.2, 62.8), (66.6, 77.4), (236.0, 250.0)])
        self.assertEqual(segments, [[1.0, 140.0, 43.9, 150.0], [63.1, 140.0, 66.3, 150.0], [77.7, 140.0, 235.7, 150.0]])
        self.assertEqual(g.barrier_segments((1.0, 140.0, 239.0, 150.0), []), [[1.0, 140.0, 239.0, 150.0]])

    def test_heatsink_corridors(self):
        spec = dict(intake_side='left', corridor_mm=30.0, fan_mm=15.0)
        corr = g.heatsink_corridors([1.0, 20.455, 102.6, 121.545], spec, (240.0, 180.0))
        self.assertEqual(corr['intake'][2], 1.0)
        self.assertEqual(corr['intake_on_board_mm'], 1.0)
        self.assertEqual(corr['exhaust'], [102.6, 20.455, 132.6, 121.545])
        spec_right = dict(intake_side='right', corridor_mm=30.0, fan_mm=15.0)
        corr = g.heatsink_corridors([137.4, 20.0, 239.0, 121.0], spec_right, (240.0, 180.0))
        self.assertEqual(corr['intake'], [239.0, 20.0, 240.0, 121.0])
        self.assertEqual(corr['exhaust'], [107.4, 20.0, 137.4, 121.0])

    def test_circle_box_distance(self):
        self.assertAlmostEqual(g.circle_box_distance((158.0, 92.0), 35.05, [102.6 - 10, 20.0, 102.6, 121.0]), 158.0 - 35.05 - 102.6)
        self.assertEqual(g.circle_box_distance((0.0, 0.0), 5.0, [-1.0, -1.0, 1.0, 1.0]), 0.0)

    def test_stackup(self):
        self.assertAlmostEqual(g.stackup_thickness_mm(), 2.0)
        text = g.stackup_text()
        self.assertEqual(text.count('(type "copper")'), 4)
        self.assertIn('(thickness 0.07)', text)
        self.assertIn('(thickness 1.32)', text)


class PlanAndScoringTests(unittest.TestCase):
    def test_routing_plan_skeleton_validates(self):
        for cid in CANDIDATES:
            cand = g.load_candidate(g.candidate_path(cid))
            plan = g.routing_plan_skeleton(cand, 'x.kicad_pcb')
            gr.validate_plan({k: v for k, v in plan.items() if k != 'keepout_notes'})
            self.assertEqual(plan['layers'], g.COPPER_LAYERS)
            self.assertIn('SW', plan['power'])
            self.assertIn('PGND', plan['power'])
            self.assertEqual(plan['critical_layers'], ['B.Cu'])
            self.assertTrue(all(net in plan['critical'] for net in ('G_H', 'G_L')))
            self.assertEqual(plan['ground']['net'], 'GND_CTRL')
            self.assertGreaterEqual(plan['ground']['polygon'][0][1], cand['bands']['selv_y_min'])

    def test_scoring(self):
        criteria = {
            'A': dict(power_path_mm=500.0, power_path_layer_transitions=3, hf_cap_row1_max_mm=6.0, hf_pads_within_row2_min=4, driver_to_gate_max_mm=11.4,
                      sw_copper_mm2=3000.0, hv_to_selv_min_mm=9.5, heatsink_hv_min_mm=5.2, film_to_heatsink_min_mm=16.7, inductor_to_heatsink_mm=20.0,
                      film_to_inductor_min_mm=0.4, tall_parts_in_corridors=3, drc_lite_findings=10, board_area_mm2=43200.0, placement_issues=6),
            'B': dict(power_path_mm=520.0, power_path_layer_transitions=3, hf_cap_row1_max_mm=6.0, hf_pads_within_row2_min=4, driver_to_gate_max_mm=11.4,
                      sw_copper_mm2=2800.0, hv_to_selv_min_mm=9.6, heatsink_hv_min_mm=5.2, film_to_heatsink_min_mm=34.0, inductor_to_heatsink_mm=20.4,
                      film_to_inductor_min_mm=16.0, tall_parts_in_corridors=0, drc_lite_findings=4, board_area_mm2=43200.0, placement_issues=1),
        }
        scoring = g.score_candidates(criteria)
        self.assertEqual(scoring['selected'], 'B')
        self.assertEqual(scoring['scores']['B'], round(g.COMPARISON_WEIGHTS['power_path_mm'] * 1.0, 4))  # the only criterion where B is worse
        skipped = g.score_candidates({'A': dict(criteria['A'], drc_lite_findings=None), 'B': criteria['B']})
        self.assertIn('skipped', skipped['detail']['drc_lite_findings'])


class EvidenceTests(unittest.TestCase):
    def test_recorded_floorplan_evidence_matches_the_board(self):
        progress = g.VERIFICATION_DIR / 'routing_progress_power.json'
        if not progress.is_file():
            self.skipTest('no routing_progress_power.json recorded yet')
        data = json.loads(progress.read_text(encoding='utf-8'))
        if not data.get('board'):
            self.skipTest('routing_progress_power.json names no board yet')
        board = Path(data['board'])
        if not board.is_file():
            self.skipTest(f'recorded board {board} is absent')
        self.assertEqual(hashlib.sha256(board.read_bytes()).hexdigest(), data['board_sha256'], 'routing_progress_power.json is stale')
        self.assertIn(data['stage'], ('floorplan-selected', 'floorplan-in-progress', 'routed', 'routed_with_unresolved_connections'))
        self.assertEqual(data['footprints'], 237)
        if data.get('drc') and data['drc'].get('manifest'):
            manifest = Path(data['drc']['manifest'])
            self.assertTrue(manifest.is_file(), f'DRC manifest {manifest} missing')
            run = json.loads(manifest.read_text(encoding='utf-8'))
            self.assertEqual(run['source_sha256'], data['board_sha256'], 'DRC manifest does not belong to the recorded board')


class PcbnewPlacementTests(unittest.TestCase):
    """Runs this file under KiCad's Python with --place; the host-interpreter test only launches it."""

    def test_place_candidate_b_in_a_temporary_directory(self):
        try:
            import pcbnew  # noqa: F401
            in_kicad = True
        except ImportError:
            in_kicad = False
        if in_kicad:
            self.skipTest('in-process placement is exercised through --place')
        python = kicad_python()
        if python is None or not find_kicad_cli():
            self.skipTest('KiCad Python / kicad-cli not available')
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run([str(python), str(Path(__file__).resolve()), '--place', tmp], capture_output=True, text=True,
                                       encoding='utf-8', errors='replace', timeout=1200, cwd=str(ROOT))
            self.assertEqual(completed.returncode, 0, completed.stdout[-4000:] + completed.stderr[-4000:])
            summary = json.loads((Path(tmp) / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['footprints'], 237)
        self.assertEqual(summary['candidate'], 'B')
        self.assertGreaterEqual(summary['zones'], len(g.load_candidate(g.candidate_path('B'))['zones']))
        self.assertEqual(summary['barrier_parts'], 8)
        # U1/U3 use the slotted AIPE UCC21710 footprint since 2026-10-11, so every barrier part brings its own NPTH slot
        self.assertEqual(summary['slots_added'], 0)
        self.assertTrue(all(summary['hv_toward_hv_area']))
        self.assertEqual(summary['band_violations'], [])


def place_for_test(directory: str) -> int:
    board = Path(directory) / f'{g.NAME}.kicad_pcb'
    result = g.build_power(g.candidate_path('B'), board, metrics=False, write_outputs=False)
    summary = dict(footprints=result['footprints'], candidate=result['candidate'], zones=result['board_counts']['zones'],
                   barrier_parts=len(result['barrier']), slots_added=len(result['slots_added']),
                   hv_toward_hv_area=[b.get('hv_toward_hv_area') for b in result['barrier']], issues=result['checks']['issues'],
                   band_violations=result['checks']['band_violations'])
    (Path(directory) / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--place':
        raise SystemExit(place_for_test(sys.argv[2]))
    unittest.main()
