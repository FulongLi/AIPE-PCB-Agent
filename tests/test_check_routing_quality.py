"""Tests for automation.verification.check_routing_quality.

The measurement core takes the plain-dict document ``extract_board`` produces, so these tests build such documents by
hand and run with the host interpreter (no pcbnew). The pcbnew extraction itself is exercised by the V2.1 synthetic
scenario of tests/test_grid_router.py and by the recorded V2 baselines.
"""

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.kicad_tools import path_geometry as pg
from automation.verification import check_routing_quality as cq

NM = cq.NM_PER_MM


def nm(x, y):
    return [int(round(x * NM)), int(round(y * NM))]


def seg(net, layer, a, b, width=0.2, uuid=None):
    return dict(net=net, layer=layer, a=nm(*a), b=nm(*b), width_mm=width, length_mm=math.dist(a, b), uuid=uuid or f'{net}-{a}-{b}', kind='seg')


def arc(net, layer, a, m, b, width=0.2):
    return dict(net=net, layer=layer, a=nm(*a), b=nm(*b), mid=nm(*m), width_mm=width, length_mm=pg.arc_length(a, m, b), uuid=f'arc-{a}', kind='arc',
                radius_mm=pg.arc_from_points(a, m, b)[1])


def polyline(net, layer, points, width=0.2):
    return [seg(net, layer, p, q, width) for p, q in zip(points, points[1:])]


def document(items, vias=(), pad_hits=None, zone_nets=()):
    return dict(board=dict(file='x.kicad_pcb', sha256='0' * 64, pcbnew_version='test', layers=['F.Cu', 'B.Cu']), items=items,
                vias=[dict(net=n, xy=nm(*xy), diameter_mm=0.6, layers=['F.Cu', 'B.Cu'], uuid=f'via-{xy}') for n, xy in vias],
                pad_hits={net: [nm(*p) for p in pts] for net, pts in (pad_hits or {}).items()}, zone_nets=list(zone_nets))


class MeasureTests(unittest.TestCase):
    def test_staircase_is_counted_as_90_degree_bends_and_a_stair_run(self):
        stairs = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3), (10, 3)]
        doc = document(polyline('A', 'F.Cu', [(p[0] * 0.25, p[1] * 0.25) for p in stairs]))
        m = cq.measure(doc)
        t = m['totals']
        self.assertEqual((t['segments'], t['arcs'], t['vias'], t['chains']), (7, 0, 0, 1))
        self.assertEqual(t['bends_90'], 6)
        self.assertEqual(t['direction_changes'], 6)
        self.assertEqual(t['stair_runs'], 1)
        self.assertEqual(t['zigzag_runs'], 0)
        self.assertEqual(t['short_segments'], 6)  # 0.25 mm steps are short; the 1.75 mm tail is not
        self.assertGreaterEqual(t['short_segment_runs'], 1)
        self.assertAlmostEqual(t['length_mm'], 6 * 0.25 + 1.75, places=6)
        self.assertEqual(m['nets']['A']['bends_90'], 6)
        self.assertEqual(m['by_layer']['F.Cu']['segments'], 7)
        self.assertEqual(m['by_attribution']['router']['bends_90'], 6)
        self.assertEqual(m['sharp_corners']['by_reason'], {'unexplained': 6})
        self.assertAlmostEqual(m['totals']['efficiency'], math.dist((0, 0), (2.5, 0.75)) / t['length_mm'], places=4)

    def test_meander_is_a_zigzag_run_and_efficiency_drops(self):
        meander = [(0, 0), (0.4, 0), (0.4, 0.4), (0.8, 0.4), (0.8, 0), (1.2, 0), (1.2, 0.4), (1.6, 0.4), (6.0, 0.4)]
        m = cq.measure(document(polyline('B', 'B.Cu', meander)))
        t = m['totals']
        self.assertEqual(t['zigzag_runs'], 1)
        self.assertEqual(t['stair_runs'], 0)
        self.assertEqual(t['bends_90'], 6)  # the last joint continues straight
        self.assertLess(t['efficiency'], 0.9)
        self.assertEqual(m['worst_cases']['short_runs'][0]['kind'], 'zigzag')

    def test_diagonals_and_tangent_arcs_are_not_bends(self):
        a, mid, b, _, _ = pg.fillet_corner((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), 1.0)
        items = [seg('C', 'F.Cu', (0.0, 0.0), a), arc('C', 'F.Cu', a, mid, b), seg('C', 'F.Cu', b, (10.0, 10.0)),
                 seg('D', 'F.Cu', (20.0, 0.0), (25.0, 0.0)), seg('D', 'F.Cu', (25.0, 0.0), (30.0, 5.0))]
        m = cq.measure(document(items))
        t = m['totals']
        self.assertEqual((t['segments'], t['arcs']), (4, 1))
        self.assertEqual(t['bends_90'], 0)
        self.assertEqual(t['bends_45'], 1)
        self.assertEqual(t['arc_joints'], 2)
        self.assertEqual(t['arc_joints_discontinuous'], 0)
        self.assertEqual(m['arcs']['count'], 1)
        self.assertAlmostEqual(m['arcs']['radius_mm']['min'], 1.0, places=3)
        self.assertAlmostEqual(m['nets']['C']['arc_length_mm'], math.pi / 2, places=2)
        self.assertEqual(m['nets']['C']['chains'], 1)  # seg-arc-seg is one chain
        # a non-tangent arc joint is reported
        bad = [seg('E', 'F.Cu', (0.0, 0.0), a), arc('E', 'F.Cu', a, mid, b), seg('E', 'F.Cu', b, (12.0, 1.0))]
        m2 = cq.measure(document(bad))
        self.assertEqual(m2['totals']['arc_joints_discontinuous'], 1)
        self.assertEqual(len(m2['arcs']['tangency_failures']), 1)
        self.assertGreater(m2['arcs']['tangency_failures'][0]['error_deg'], 10)

    def test_vias_pads_and_junctions_split_chains_and_zone_nets_are_flagged(self):
        items = polyline('F', 'F.Cu', [(0, 0), (5, 0), (5, 5)]) + polyline('F', 'B.Cu', [(5, 5), (9, 5)]) + polyline('F', 'F.Cu', [(5, 0), (5, -3)])
        doc = document(items, vias=[('F', (5, 5))], pad_hits={'F': [(0, 0)]}, zone_nets=['F'])
        m = cq.measure(doc)
        self.assertEqual(m['totals']['vias'], 1)
        self.assertEqual(m['nets']['F']['vias'], 1)
        self.assertTrue(m['nets']['F']['zone_connected'])
        self.assertEqual(m['zone_connected_nets'], ['F'])
        self.assertEqual(m['totals']['chains'], 4)  # pad->T, T->via, T->stub, via->end on B.Cu
        self.assertEqual(m['totals']['bends_90'], 0)  # the T is a junction, not a bend
        self.assertEqual(m['by_attribution']['pad_link']['segments'], 1)
        # a via in the middle of a straight run on one layer is an anchor too
        doc2 = document(polyline('G', 'F.Cu', [(0, 0), (2, 0), (2, 2)]), vias=[('G', (2, 0))])
        self.assertEqual(cq.measure(doc2)['totals']['bends_90'], 0)
        self.assertEqual(cq.measure(doc2)['totals']['chains'], 2)

    def test_pre_routed_attribution_and_report_reasons(self):
        items = polyline('H', 'F.Cu', [(0, 0), (3, 0), (3, 3), (6, 3)])
        plan = {'stage1_run_plan': {'pre_routed': {'tracks': [dict(net='H', layer='F.Cu', a=[0, 0], b=[3, 0], width=0.2)]}}}
        m = cq.measure(document(items), plan=plan)
        self.assertEqual(m['by_attribution']['pre_routed']['segments'], 1)
        self.assertEqual(m['by_attribution']['router']['segments'], 2)
        self.assertEqual(m['sharp_corners']['by_reason'], {'pre_routed': 1, 'unexplained': 1})
        report = {'beautify': {'exceptions': [dict(net='H', layer='F.Cu', xy=[3.0, 3.0], reason='clearance')]}}
        m2 = cq.measure(document(items), plan=plan, report=report)
        self.assertEqual(m2['sharp_corners']['by_reason'], {'pre_routed': 1, 'clearance': 1})
        self.assertEqual(cq.pre_routed_keys(None), set())
        self.assertEqual(len(cq.pre_routed_keys({'tracks': [dict(net='H', layers=['F.Cu', 'B.Cu'], a=[0, 0], b=[1, 0])]})), 4)

    def test_anchors_are_per_net_and_degree2_probe_is_reported(self):
        items = polyline('A', 'F.Cu', [(0, 0), (2, 0), (2, 2)]) + polyline('B', 'F.Cu', [(0, 1), (2, 1), (2, 3)])
        m = cq.measure(document(items, vias=[('B', (2, 0))]))        # B's via at A's corner must not split A's chain
        self.assertEqual(m['totals']['bends_90'], 2)
        self.assertEqual(m['totals']['chains'], 2)
        m = cq.measure(document(items, vias=[('A', (2, 0))]))        # A's own via does
        self.assertEqual(m['totals']['bends_90'], 1)
        self.assertEqual(m['totals']['chains'], 3)
        self.assertEqual(m['totals']['degree2_joints'], 2)           # the probe figure counts the anchored corner too
        self.assertEqual(m['totals']['degree2_bends_90'], 2)

    def test_compare_and_writers(self):
        before = cq.measure(document(polyline('K', 'F.Cu', [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3), (9, 3)])))
        after = cq.measure(document(polyline('K', 'F.Cu', [(0, 0), (3, 3), (9, 3)])))
        cmp_doc = cq.compare(before, after)
        self.assertLess(cmp_doc['totals']['bends_90']['delta'], 0)
        self.assertLess(cmp_doc['totals']['length_mm']['delta'], 0)
        self.assertEqual(cmp_doc['nets_longer_after'], [])
        self.assertEqual(cmp_doc['nets_with_more_vias'], [])
        self.assertTrue(cmp_doc['nets']['K']['min_width_mm']['same'])
        text = cq.markdown(cmp_doc)
        self.assertIn('Routing quality comparison', text)
        with tempfile.TemporaryDirectory(prefix='aipe rq ') as folder:
            json_path, md_path = cq.write_outputs(before, folder, 'unit')
            loaded = json.loads(json_path.read_text(encoding='utf-8'))
            self.assertEqual(loaded['totals']['segments'], 7)
            self.assertEqual(loaded['status'], cq.STATUS)
            self.assertIn('| board |', md_path.read_text(encoding='utf-8'))
            run = Path(folder) / 'run.json'
            run.write_text(json.dumps(dict(status='passed', finding_counts=dict(violations=0, unconnected_items=0, schematic_parity=0), finding_count=0,
                                           tool_exit_code=0, source_sha256='0' * 64)), encoding='utf-8')
            link = cq.link_drc(document([]), run)
            self.assertTrue(link['board_sha256_matches_drc_source'])
            self.assertEqual(link['finding_counts']['violations'], 0)

    def test_degenerate_documents(self):
        empty = cq.measure(document([]))
        self.assertEqual(empty['totals']['segments'], 0)
        self.assertIsNone(empty['totals']['efficiency'])
        self.assertIsNone(empty['arcs']['radius_mm'])
        zero = cq.measure(document([seg('Z', 'F.Cu', (1, 1), (1, 1))]))  # zero-length items are ignored
        self.assertEqual(zero['totals']['segments'], 0)


if __name__ == '__main__':
    unittest.main()
