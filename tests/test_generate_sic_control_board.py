"""Tests for the V2 control-board generator (automation.kicad_tools.generate_sic_control_board).

Pure-Python parts run with the host interpreter: candidate loading and validation (regions, rectilinear
islands, disjoint islands, every model part assigned), the LQFP escape planner (alternation along pin runs,
core-rail pins inward / I/O-rail pins outward where parity allows, grid-snapped vias, via spacing), the
In2.Cu corridor geometry, the routing plan (validated by grid_router.validate_plan), the stackup arithmetic,
the Manhattan MST, the candidate scoring and the In2.Cu signal pass helpers (rectilinear island decomposition for
the keepouts, Z-shaped waypoint choice, inner-layer nets excluded from the F.Cu/B.Cu stages without an F.Cu lane
stub). The pcbnew part runs this file under KiCad's bundled Python
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
        self.assertNotIn('style', plan)  # no style argument = the V2 plan

    def test_default_routing_style_validates_and_the_v2_geometry_is_opt_in(self):
        cand = g.load_candidate(g.candidate_path('B'))
        escapes = g.plan_dsp_escapes(lqfp_side('SG9S3S'), (68.0, 33.0))
        styled = g.routing_plan(cand, escapes, 'x.kicad_pcb', ic_refs=['U5'], style=g.ROUTING_STYLE)
        self.assertEqual(styled['style'], g.ROUTING_STYLE)
        self.assertLessEqual(set(g.ROUTING_STYLE), set(gr.STYLE_DEFAULTS))
        self.assertLessEqual(set(g.ROUTING_STYLE_DIAGONAL), set(gr.STYLE_DEFAULTS))
        gr.validate_plan(styled)  # the style block passes the shared router's validation
        gr.validate_plan(g.routing_plan(cand, escapes, 'x.kicad_pcb', ic_refs=['U5'], style=g.ROUTING_STYLE_DIAGONAL))
        self.assertFalse(g.ROUTING_STYLE['diagonal'])  # 8-direction search stays opt-in on the control board (run time, see ROUTING_STYLE comment)
        self.assertNotIn('style', g.routing_plan(cand, escapes, 'x.kicad_pcb', ic_refs=['U5'], style={}))

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


class InnerLayerPassTests(unittest.TestCase):
    """Pure helpers of the In2.Cu signal pass (inner_layer_route itself needs pcbnew)."""

    @staticmethod
    def shoelace(polygon):
        return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(polygon, polygon[1:] + polygon[:1]))) / 2

    def test_rectilinear_rectangles_cover_every_candidate_island_exactly(self):
        for cid in ('A', 'B'):
            cand = g.load_candidate(g.candidate_path(cid))
            for net, polygon in cand['islands'].items():
                if polygon == 'background':
                    continue
                rects = g.rectilinear_rectangles(polygon)
                self.assertTrue(rects, (cid, net))
                self.assertAlmostEqual(sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in rects), self.shoelace(polygon), places=6, msg=(cid, net))
                for x0, y0, x1, y1 in rects:
                    self.assertLess(x0, x1); self.assertLess(y0, y1)
                    self.assertTrue(g.point_in_polygon(((x0 + x1) / 2, (y0 + y1) / 2), polygon), (cid, net, (x0, y0, x1, y1)))
                for a in rects:  # disjoint interiors
                    for b in rects:
                        if a is not b:
                            self.assertFalse(g.boxes_overlap(a, b), (cid, net, a, b))

    def test_rectilinear_rectangles_of_an_l_shape(self):
        rects = g.rectilinear_rectangles([[0, 0], [4, 0], [4, 2], [2, 2], [2, 4], [0, 4]])
        self.assertEqual(sorted(rects), [(0.0, 0.0, 4.0, 2.0), (0.0, 2.0, 2.0, 4.0)])

    def test_waypoints_form_a_z_that_turns_where_the_fewest_through_items_lie(self):
        items = [dict(xy=[50.0, 48.0]), dict(xy=[55.0, 48.25]), dict(xy=[45.0, 50.0]), dict(xy=[47.0, 53.0]), dict(xy=[70.0, 52.0])]
        points = g.inner_route_waypoints([62.75, 46.5], [38.16, 74.0], items)
        self.assertEqual(len(points), 4)
        self.assertEqual(points[0], [62.75, 46.5])
        self.assertEqual(points[-1], [38.125, 74.0])  # the pad centre snapped to the routing grid
        self.assertEqual(points[0][0], points[1][0]); self.assertEqual(points[1][1], points[2][1]); self.assertEqual(points[2][0], points[3][0])
        turn = points[1][1]
        self.assertGreaterEqual(turn, 46.5 + g.INNER_TURN_SEARCH[0]); self.assertLess(turn, 74.0)
        self.assertTrue(all(abs(it['xy'][1] - turn) >= g.INNER_TURN_RADIUS for it in items if 38 < it['xy'][0] < 63), turn)
        self.assertEqual(turn, 51.0)  # the nearest ordinate a full radius beyond the items at 48.0 / 48.25 / 50.0 and before the one at 53.0
        self.assertEqual(points, [[round(v, 6) for v in p] for p in points])

    def test_waypoints_fall_back_to_the_direct_pair(self):
        self.assertEqual(g.inner_route_waypoints([62.75, 46.5], [62.75, 74.0], []), [[62.75, 46.5], [62.75, 74.0]])  # aligned
        self.assertEqual(g.inner_route_waypoints([10.0, 10.0], [12.0, 11.0], []), [[10.0, 10.0], [12.0, 11.0]])  # closer than the minimum
        upward = g.inner_route_waypoints([38.16, 74.0], [62.75, 46.5], [])
        self.assertEqual(len(upward), 4)
        self.assertLess(upward[1][1], 74.0 - g.INNER_TURN_SEARCH[0] + 1e-9)

    def test_sliver_edge_matching_and_widening(self):
        rect = (60.6, 41.6, 61.9, 44.55)  # a 3V3 corridor notch; LR-15 slivers sat just outside its long edges
        self.assertEqual(g.sliver_edge(rect, [60.576, 42.683, 60.6, 42.925]), 'x0')
        self.assertEqual(g.sliver_edge(rect, [61.9, 42.682, 61.929, 42.924]), 'x1')
        self.assertEqual(g.sliver_edge((78.6, 41.1, 81.55, 42.4), [79.682, 41.071, 79.924, 41.1]), 'y0')
        self.assertEqual(g.sliver_edge((78.6, 41.1, 81.55, 42.4), [79.682, 42.4, 79.924, 42.43]), 'y1')
        self.assertIsNone(g.sliver_edge(rect, [60.0, 42.683, 60.1, 42.925]))  # detached from the edge
        self.assertIsNone(g.sliver_edge(rect, [60.576, 50.0, 60.6, 50.2]))  # beyond the edge's extent
        self.assertEqual(g.widened(rect, 'x0', 0.125), (60.475, 41.6, 61.9, 44.55))
        self.assertEqual(g.widened(rect, 'x1', 0.125), (60.6, 41.6, 62.025, 44.55))
        self.assertEqual(g.widened(rect, 'y0', 0.125), (60.6, 41.475, 61.9, 44.55))
        self.assertEqual(g.widened(rect, 'y1', 0.125), (60.6, 41.6, 61.9, 44.675))
        self.assertLess(g.SLIVER_AREA_MM2, 1.0)  # far below the smallest legitimate corridor fill (about 2 mm2)
        self.assertLessEqual(g.SLIVER_TRIM_STEP * g.SLIVER_TRIM_ROUNDS, g.CORRIDOR_HALF_WIDTH * 2)

    def test_inner_layer_nets_are_excluded_from_the_outer_stages_without_a_lane_stub(self):
        cand = g.load_candidate(g.candidate_path('B'))
        centre = (68.0, 33.0)
        pads = lqfp_side('SSSSSS')
        outward = next(e for e in g.plan_dsp_escapes(pads, centre) if e['direction'] == 'out' and e['net'] != 'GND_CTRL')
        next(p for p in pads if p['number'] == outward['number'])['net'] = 'BIAS_EN'  # an outward signal pin of the run
        escapes = g.plan_dsp_escapes(pads, centre)
        bias = next(e for e in escapes if e['net'] == 'BIAS_EN')
        self.assertEqual(bias['direction'], 'out')
        plan = g.routing_plan(cand, escapes, 'x.kicad_pcb', ic_refs=['U5'], dsp_centre=centre)
        gr.validate_plan(plan)
        self.assertEqual(plan['exclude_nets'], list(g.INNER_SIGNAL_NETS))
        self.assertIn('BIAS_EN', plan['exclude_nets'])
        bias_tracks = [t for t in plan['pre_routed']['tracks'] if t['net'] == 'BIAS_EN']
        self.assertEqual(len(bias_tracks), 1)  # pad -> escape via only; no F.Cu stub towards STUB_RADIUS
        self.assertEqual((bias_tracks[0]['a'], bias_tracks[0]['b']), (list(bias['pad']), list(bias['via'])))
        other_out = next(e for e in escapes if e['direction'] == 'out' and e['net'] != 'BIAS_EN' and e['net'] != 'GND_CTRL')
        self.assertGreater(len([t for t in plan['pre_routed']['tracks'] if t['net'] == other_out['net']]), 1)  # ordinary outward pins keep theirs
        self.assertEqual(plan['layers'], ['F.Cu', 'B.Cu'])  # the inner layer is never a routing layer of the outer stages
        self.assertEqual(plan['signal_layers'], ['F.Cu', 'B.Cu'])


class LadderNegotiationTests(unittest.TestCase):
    """negotiate_with_ladder drives a single-penalty negotiation step through RIPUP_PENALTY_LADDER (pure); LadderRouter binds it."""

    def test_restarts_at_the_first_multiple_after_progress_and_stops_after_a_fruitless_cycle(self):
        state = dict(count=3)
        calls = []

        def step(pen, budget):
            calls.append((pen, budget))
            if pen == 100.0 and state['count'] == 3:  # only the 2.5x step finds a path the re-route can keep
                state['count'] = 2
                return [dict(round=0, net='X', penalty=pen, result='kept (3 -> 2)')]
            return [dict(round=0, net='X', penalty=pen, result='reverted (3 > 3)')] if pen == 40.0 else []
        log = g.negotiate_with_ladder(step, lambda: state['count'], rounds=240, penalty=40.0, ladder=(1.0, 0.4, 2.5))
        self.assertEqual([c[0] for c in calls], [40.0, 16.0, 100.0, 40.0, 16.0, 100.0])  # restart at 1x, then one fruitless cycle
        self.assertEqual([e['round'] for e in log], list(range(len(log))))
        self.assertEqual([e['ladder'] for e in log], [1.0, 2.5, 1.0])
        self.assertEqual(state['count'], 2)
        self.assertEqual(calls[0][1], 240)
        self.assertLess(calls[-1][1], 240)  # the round budget shrinks by at least one per step

    def test_stops_at_zero_and_within_the_round_budget(self):
        state = dict(count=2)

        def step(pen, budget):
            state['count'] -= 1
            return [dict(round=7, net='Y', penalty=pen, result='kept')]
        log = g.negotiate_with_ladder(step, lambda: state['count'], rounds=240, penalty=40.0)
        self.assertEqual(state['count'], 0)
        self.assertEqual([e['ladder'] for e in log], [1.0, 1.0])
        self.assertEqual([e['round'] for e in log], [0, 1])
        budgets = []

        def stubborn(pen, budget):
            budgets.append(budget)
            return [dict(round=0, net='Z', penalty=pen, result='reverted')] * 3
        log = g.negotiate_with_ladder(stubborn, lambda: 5, rounds=5, penalty=40.0)
        self.assertEqual(budgets, [5, 2])  # 3 entries per step: the budget of 5 is spent after the second step
        self.assertEqual(len(log), 6)
        self.assertEqual(g.negotiate_with_ladder(stubborn, lambda: 0, rounds=5, penalty=40.0), [])  # nothing unresolved: no step

    def test_ladder_router_only_overrides_the_negotiation(self):
        self.assertTrue(issubclass(g.LadderRouter, gr.Router))
        self.assertEqual(set(g.LadderRouter.__dict__) & {n for n in dir(gr.Router) if not n.startswith('__')}, {'negotiate'})
        self.assertEqual(g.RIPUP_PENALTY_LADDER[0], 1.0)  # the plan's own penalty is always the first attempt
        self.assertEqual(sorted(g.RIPUP_PENALTY_LADDER), [0.4, 1.0, 2.5])
        self.assertAlmostEqual(g.point_segment_distance(0.0, 1.0, -1.0, 0.0, 1.0, 0.0), 1.0)
        self.assertAlmostEqual(g.point_segment_distance(3.0, 0.0, -1.0, 0.0, 1.0, 0.0), 2.0)


class IslandBandTests(unittest.TestCase):
    """Pure helpers of the In2.Cu edge bands: rectangle subtraction, port exit channels, band keepouts and the directed Z."""

    def test_rect_minus(self):
        self.assertEqual(g.rect_minus((0, 0, 10, 10), [(20, 20, 30, 30)]), [(0.0, 0.0, 10.0, 10.0)])  # disjoint hole: unchanged
        pieces = g.rect_minus((0, 0, 10, 10), [(4, -1, 6, 3)])  # a channel entering from the top edge
        self.assertEqual(sorted(pieces), [(0.0, 0.0, 4.0, 3.0), (0.0, 3.0, 10.0, 10.0), (6.0, 0.0, 10.0, 3.0)])
        self.assertAlmostEqual(sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in pieces), 100 - 2 * 3)
        pieces = g.rect_minus((0, 0, 10, 10), [(4, -1, 6, 3), (-1, 8, 2, 9)])  # two holes: disjoint pieces, area accounted
        self.assertAlmostEqual(sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in pieces), 100 - 6 - 2)
        for a in pieces:
            for b in pieces:
                if a is not b:
                    self.assertFalse(g.boxes_overlap(a, b), (a, b))

    def test_port_channels_leave_the_nearest_island_side_straight(self):
        cand = g.load_candidate(g.candidate_path('B'))
        rects = [r for net, poly in cand['islands'].items() if poly != 'background' for r in g.rectilinear_rectangles(poly)]
        east = g.port_channel((82.0, 33.25), rects)  # 1.0 mm east of the 1V9 island (edge x = 81): horizontal exit towards +x
        self.assertEqual((east[1], east[2]), ('x', 1))
        self.assertEqual(east[0], (82.0 - g.INNER_CHANNEL_HALF_WIDTH, 33.25 - g.INNER_CHANNEL_HALF_WIDTH, 81.0 + g.INNER_EDGE_BAND + g.INNER_CHANNEL_HALF_WIDTH,
                                   33.25 + g.INNER_CHANNEL_HALF_WIDTH))  # starts half a width behind the port so the port cell itself is open
        south = g.port_channel((65.75, 45.0), rects)  # 1.0 mm below the island (edge y = 44): vertical exit towards +y
        self.assertEqual((south[1], south[2]), ('y', 1))
        self.assertEqual(south[0], (65.75 - g.INNER_CHANNEL_HALF_WIDTH, 45.0 - g.INNER_CHANNEL_HALF_WIDTH, 65.75 + g.INNER_CHANNEL_HALF_WIDTH,
                                    44.0 + g.INNER_EDGE_BAND + g.INNER_CHANNEL_HALF_WIDTH))
        self.assertIsNone(g.port_channel((57.75, 68.875), rects))  # logic region: outside every band
        self.assertIsNone(g.port_channel((70.0, 30.0), rects))  # inside the island keepout: no channel (no route can start there)
        self.assertIsNone(g.port_channel((38.16, 74.0), rects))  # J8 pin 9: 2.16 mm beyond the 12V_PROT band
        rects2, channels = g.band_keepouts(rects, [(82.0, 33.25), (65.75, 45.0), (62.75, 46.5), (57.75, 68.875), (82.0, 33.25)])
        self.assertEqual(len(channels), 3)  # duplicates and out-of-band ports add nothing
        holes = [channel[0] for channel in channels.values()]
        for x0, y0, x1, y1 in rects2:
            for hx0, hy0, hx1, hy1 in holes:
                self.assertTrue(hx1 <= x0 or hx0 >= x1 or hy1 <= y0 or hy0 >= y1, 'a band piece overlaps a channel')
        covered = lambda px, py: any(x0 <= px <= x1 and y0 <= py <= y1 for x0, y0, x1, y1 in rects2)
        self.assertTrue(covered(81.0 + 1.5, 20.0))  # band east of the island, away from the channel
        self.assertFalse(covered(81.0 + 1.5, 33.25))  # inside the channel
        self.assertFalse(covered(82.0, 33.25))  # the port cell itself (a channel starting at the port left it inside a band piece: iteration 8)
        self.assertFalse(covered(65.75, 45.0))
        self.assertTrue(covered(81.0 + 1.5, 33.25 + 0.6))  # just beside it
        self.assertFalse(covered(81.0 + g.INNER_EDGE_BAND + 1.0, 33.25))  # beyond the band
        self.assertLess(g.INNER_KEEPOUT_MARGIN, g.INNER_EDGE_BAND)
        self.assertGreaterEqual(g.INNER_CHANNEL_HALF_WIDTH, g.ROUTER_TRACE / 2 + g.INNER_CLEARANCE)

    def test_coincident_copper_groups(self):
        F, B = 0, 31  # layer ids: F.Cu and B.Cu
        records = [dict(id='t1', kind='end', pos=(0.0, 0.0), layer=F), dict(id='t1', kind='end', pos=(5.0, 0.0), layer=F),
                   dict(id='t2', kind='end', pos=(5.0, 0.0), layer=B), dict(id='t2', kind='end', pos=(9.0, 0.0), layer=B),  # other layer: joined only by the via
                   dict(id='v1', kind='via', pos=(5.0, 0.0)),
                   dict(id='t3', kind='end', pos=(20.0, 0.0), layer=F), dict(id='t3', kind='end', pos=(25.0, 0.0), layer=F),  # a separate group
                   dict(id='p1', kind='smd', pos=(0.0, 0.0), layer=F, hits={'t1'}), dict(id='p2', kind='pth', pos=(25.0, 0.0), hits={'t3'})]
        groups = g.group_components(records)
        self.assertEqual(len(groups), 2)
        ids = sorted(sorted({r['id'] for r in grp}) for grp in groups)
        self.assertEqual(ids, [['p1', 't1', 't2', 'v1'], ['p2', 't3']])
        groups_without_via = g.group_components([r for r in records if r['id'] != 'v1'])
        self.assertEqual(len(groups_without_via), 3)  # F.Cu and B.Cu ends at (5, 0) do not meet without the via
        comps = [dict(points={r['pos'] for r in grp}, through=[dict(xy=list(r['pos']), kind=r['kind']) for r in grp if r['kind'] in ('via', 'pth')]) for grp in groups]
        self.assertEqual([it['xy'] for it in g.component_through_items(comps, (9.0, 0.0))], [[5.0, 0.0]])  # the B.Cu track end's group owns the via
        self.assertEqual([it['xy'] for it in g.component_through_items(comps, (20.0, 0.0))], [[25.0, 0.0]])  # ... the other one its plated pad
        self.assertEqual(g.component_through_items(comps, (50.0, 50.0)), [])

    def test_directed_z_for_a_horizontal_exit(self):
        items = [dict(xy=[84.0, 40.0]), dict(xy=[86.0, 50.0])]
        pts = g.inner_route_waypoints([82.0, 33.25], [71.75, 65.875], items, axis='x', direction=1, search=(2.75, 10.0, 0.25))
        self.assertEqual(len(pts), 4)
        self.assertEqual(pts[0], [82.0, 33.25]); self.assertEqual(pts[-1], [71.75, 65.875])
        self.assertEqual(pts[0][1], pts[1][1])  # first leg horizontal ...
        self.assertGreaterEqual(pts[1][0], 82.0 + 2.75)  # ... away from the island although the end lies to the west (a U)
        self.assertEqual(pts[1][0], pts[2][0])  # then vertical
        self.assertEqual(pts[2][1], pts[3][1])  # then horizontal into the end port
        self.assertEqual(g.inner_route_waypoints([82.0, 33.25], [90.0, 33.25], items, axis='x'), [[82.0, 33.25], [90.0, 33.25]])  # aligned
        plain = g.inner_route_waypoints([65.75, 45.0], [57.75, 68.875], items)
        self.assertEqual(plain[0][0], plain[1][0])  # default: vertical first leg towards the end
        self.assertGreater(plain[1][1], 45.0)
        away = g.inner_route_waypoints([65.75, 45.0], [57.75, 30.0], items, direction=1)  # forced south although the end is north
        self.assertGreater(away[1][1], 45.0)


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
    dnp = sorted(fp.GetReference() for fp in board.GetFootprints() if fp.IsDNP())
    return dict(footprints=len(result['placements']), issues=result['placement_issues'], sides=sides, dnp=dnp, copper_layers=board.GetCopperLayerCount(),
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
        self.assertEqual(len(back), 16, back)  # the fifteen 1V9 per-pin capacitors under the package and the mezzanine header J8 (review LR-03)
        self.assertEqual(s['sides']['U5'], 'F')
        self.assertEqual(s['sides']['J8'], 'B')
        self.assertGreater(s['estimates']['analog_pwm_separation_mm'], 0.0)
        self.assertEqual(s['silkscreen'], 16)  # incl. the 'J8 PIN 1 >' and 'MEZZANINE (B.Cu)' labels of the B.Cu header (review LR-03)

    def test_dnp_parts_carry_the_footprint_attribute(self):
        expected = sorted(p['ref'] for p in g.load_parts() if p.get('dnp'))
        self.assertTrue(expected, 'the control model has at least one DNP part (A-C12 UVLO_REF capacitor)')
        self.assertEqual(self.summary['dnp'], expected)  # V2.1: the schematics write (dnp yes); kicad-cli --schematic-parity compares the attribute


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
