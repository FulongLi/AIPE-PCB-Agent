"""Tests for automation.kicad_tools.path_geometry (pure Python, host interpreter)."""

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.kicad_tools import path_geometry as pg


def always_clear(_polyline):
    return True


class SearchSupportTests(unittest.TestCase):
    def test_octants_and_turn_classes(self):
        self.assertEqual(len(pg.MOVES8), 8)
        self.assertEqual(pg.OCTANT[(1, 0)], 0)
        self.assertEqual(pg.OCTANT[(1, 1)], 1)
        self.assertEqual(pg.OCTANT[(0, -1)], 6)
        self.assertEqual(pg.turn_class(0, 0), 0)
        self.assertEqual(pg.turn_class(0, 1), 1)
        self.assertEqual(pg.turn_class(0, 2), 2)
        self.assertEqual(pg.turn_class(0, 7), 1)
        self.assertEqual(pg.turn_class(1, 6), 3)
        self.assertEqual(pg.turn_class(0, 4), 4)
        self.assertEqual(pg.turn_class(pg.NO_DIR, 3), 0)

    def test_octile_is_the_8_direction_distance(self):
        self.assertEqual(pg.octile(5, 0), 5)
        self.assertAlmostEqual(pg.octile(3, 3), 3 * pg.SQRT2)
        self.assertAlmostEqual(pg.octile(-7, 2), 7 + (pg.SQRT2 - 1) * 2)
        self.assertLessEqual(pg.octile(7, 2), 9)  # never above Manhattan


class PolylineTests(unittest.TestCase):
    def test_turn_angle_and_classification(self):
        self.assertAlmostEqual(pg.turn_angle((0, 0), (1, 0), (2, 0)), 0.0)
        self.assertAlmostEqual(abs(pg.turn_angle((0, 0), (1, 0), (1, 1))), 90.0)
        self.assertAlmostEqual(abs(pg.turn_angle((0, 0), (1, 0), (2, 1))), 45.0)
        left = pg.turn_angle((0, 0), (1, 0), (1, 1)); right = pg.turn_angle((0, 0), (1, 0), (1, -1))
        self.assertEqual((left > 0), (right < 0))
        self.assertEqual(pg.classify_bend(2.0), 'straight')
        self.assertEqual(pg.classify_bend(-45.0), '45')
        self.assertEqual(pg.classify_bend(90.0), '90')
        self.assertEqual(pg.classify_bend(60.0), 'other')

    def test_merge_collinear(self):
        pts = [(0, 0), (1, 0), (2, 0), (2, 0), (2, 1), (2, 2), (3, 3)]
        self.assertEqual(pg.merge_collinear(pts), [(0, 0), (2, 0), (2, 2), (3, 3)])
        self.assertEqual(pg.merge_collinear([(0, 0), (1, 0), (0, 0)]), [(0, 0), (1, 0), (0, 0)])  # a reversal is kept

    def test_octilinear_candidates(self):
        self.assertEqual(pg.octilinear_candidates((1, 1), (1, 1)), [])
        self.assertEqual(pg.octilinear_candidates((0, 0), (5, 0)), [[(0, 0), (5, 0)]])
        self.assertEqual(pg.octilinear_candidates((0, 0), (3, 3)), [[(0, 0), (3, 3)]])
        cands = pg.octilinear_candidates((0, 0), (6, 2))
        self.assertEqual(cands, [[(0, 0), (2, 2), (6, 2)], [(0, 0), (4, 0), (6, 2)]])
        for cand in cands:
            self.assertAlmostEqual(pg.polyline_length(cand), 4 + 2 * pg.SQRT2)
            self.assertLess(pg.polyline_length(cand), 8)
        self.assertEqual(pg.octilinear_candidates((0, 0), (-2, 5))[0], [(0, 0), (-2, -2 + 4), (-2, 5)])

    def test_shortcut_replaces_a_staircase_and_respects_the_clearance_test(self):
        stairs = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3), (4, 3), (4, 4), (8, 4)]
        pulled = pg.shortcut(stairs, always_clear)
        self.assertEqual(pulled, [(0, 0), (4, 4), (8, 4)])
        self.assertLess(pg.polyline_length(pulled), pg.polyline_length(stairs))
        blocked = pg.shortcut(stairs, lambda poly: False)
        self.assertEqual(blocked, pg.merge_collinear(stairs))
        # a clearance test that rejects anything touching x == 2.5 keeps the stair in that column only
        def clear(poly):
            return all(not (min(p[0], q[0]) < 2.5 < max(p[0], q[0])) or p[1] == q[1] for p, q in zip(poly, poly[1:]))
        partial = pg.shortcut(stairs, clear)
        self.assertEqual((partial[0], partial[-1]), ((0, 0), (8, 4)))
        self.assertLessEqual(pg.polyline_length(partial), pg.polyline_length(stairs) + 1e-9)

    def test_short_runs_find_zigzags_and_stairs(self):
        zig = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 0), (3, 0), (3, 1), (10, 1)]
        runs = pg.short_runs(zig, l_short=2.0)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['kind'], 'zigzag')
        self.assertEqual(runs[0]['segments'], 6)
        stair = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3), (10, 3)]
        self.assertEqual(pg.short_runs(stair, 2.0)[0]['kind'], 'stair')
        self.assertEqual(pg.short_runs([(0, 0), (10, 0), (10, 10)], 2.0), [])
        self.assertEqual(pg.short_runs([(0, 0), (1, 0), (2, 0), (3, 0)], 2.0), [])  # straight joints are not a run

    def test_collapse_short_runs(self):
        zig = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 0), (3, 0), (3, 1), (10, 1)]
        out = pg.collapse_short_runs(zig, l_short=2.0, is_clear=always_clear)
        self.assertEqual((out[0], out[-1]), ((0, 0), (10, 1)))
        self.assertLess(len(out), len(zig))
        self.assertLess(pg.polyline_length(out), pg.polyline_length(zig))
        self.assertEqual(pg.collapse_short_runs(zig, 2.0, lambda poly: False), pg.merge_collinear(zig))

    def test_chamfer_cuts_sharp_corners_on_grid(self):
        corner = [(0, 0), (10, 0), (10, 10)]
        out = pg.chamfer(corner, always_clear)
        self.assertEqual(out, [(0, 0), (10, 10)])  # full room on both legs: the largest chamfer is the diagonal itself
        kept = pg.chamfer(corner, always_clear, keep_start=8, keep_end=8)
        self.assertEqual(kept, [(0, 0), (8, 0), (10, 2), (10, 10)])
        self.assertEqual(pg.chamfer(corner, lambda poly: False), corner)
        self.assertEqual(pg.chamfer([(0, 0), (10, 0), (13, 3)], always_clear), [(0, 0), (10, 0), (13, 3)])  # 45 deg corners are left alone
        two = pg.chamfer([(0, 0), (10, 0), (10, 10), (20, 10)], always_clear)
        self.assertEqual(two[0], (0, 0)); self.assertEqual(two[-1], (20, 10))
        self.assertTrue(all(abs(abs(pg.turn_angle(*two[i - 1:i + 2])) - 45) < 1e-9 for i in range(1, len(two) - 1)))
        self.assertTrue(all(pg._unit_steps(p, q) is not None for p, q in zip(two, two[1:])))  # stays on the grid


class ArcTests(unittest.TestCase):
    def test_fillet_corner_matches_the_verified_construction(self):
        a, m, b, d, theta = pg.fillet_corner((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), 1.0)
        self.assertAlmostEqual(theta, 90.0)
        self.assertAlmostEqual(d, 1.0)
        self.assertAlmostEqual(a[0], 9.0); self.assertAlmostEqual(a[1], 0.0)
        self.assertAlmostEqual(b[0], 10.0); self.assertAlmostEqual(b[1], 1.0)
        (cx, cy), r, _, sweep = pg.arc_from_points(a, m, b)
        self.assertAlmostEqual(r, 1.0)
        self.assertAlmostEqual(cx, 9.0); self.assertAlmostEqual(cy, 1.0)
        self.assertAlmostEqual(abs(math.degrees(sweep)), 90.0)
        self.assertAlmostEqual(pg.arc_length(a, m, b), math.pi / 2)
        # tangents continue the legs
        tx, ty = pg.tangent_at(a, m, b, at_start=True)
        self.assertAlmostEqual(tx, 1.0); self.assertAlmostEqual(ty, 0.0)
        tx, ty = pg.tangent_at(a, m, b, at_start=False)
        self.assertAlmostEqual(tx, 0.0); self.assertAlmostEqual(ty, 1.0)
        # 45 degree corner, radius 1: trim tan(22.5 deg)
        a, m, b, d, theta = pg.fillet_corner((0.0, 0.0), (10.0, 0.0), (15.0, 5.0), 1.0)
        self.assertAlmostEqual(theta, 45.0)
        self.assertAlmostEqual(d, math.tan(math.radians(22.5)))
        self.assertAlmostEqual(pg.arc_from_points(a, m, b)[1], 1.0)
        self.assertIsNone(pg.fillet_corner((0, 0), (1, 0), (2, 0), 1.0))
        self.assertIsNone(pg.fillet_corner((0, 0), (1, 0), (0, 0), 1.0))
        self.assertIsNone(pg.fillet_corner((0, 0), (1, 0), (1, 1), 0.0))

    def test_fillet_on_the_other_side_and_sampling(self):
        a, m, b, d, _ = pg.fillet_corner((0.0, 0.0), (10.0, 0.0), (10.0, -10.0), 2.0)
        (cx, cy), r, _, _ = pg.arc_from_points(a, m, b)
        self.assertAlmostEqual(r, 2.0); self.assertAlmostEqual(cx, 8.0); self.assertAlmostEqual(cy, -2.0)
        pts = pg.sample_arc(a, m, b, 0.1)
        self.assertEqual(pts[0], a); self.assertEqual(pts[-1], b)
        self.assertTrue(all(abs(math.dist(p, (cx, cy)) - 2.0) < 1e-9 for p in pts))
        self.assertTrue(all(math.dist(p, q) <= 0.1 + 1e-9 for p, q in zip(pts, pts[1:])))
        self.assertGreater(len(pts), 30)
        with self.assertRaises(ValueError):
            pg.arc_from_points((0, 0), (1, 0), (2, 0))


class ChainTests(unittest.TestCase):
    def items(self):
        # net A on F.Cu: pad(0,0) -> (10,0) -> (10,10) -> via (10,10) continues on B.Cu; a T at (10,0) towards (10,-5)
        return [
            dict(id='t1', net='A', layer='F.Cu', a=(0, 0), b=(10, 0), width=0.2),
            dict(id='t2', net='A', layer='F.Cu', a=(10, 0), b=(10, 10), width=0.2),
            dict(id='t3', net='A', layer='F.Cu', a=(10, 0), b=(10, -5), width=0.2),
            dict(id='t4', net='A', layer='B.Cu', a=(10, 10), b=(20, 10), width=0.2),
            dict(id='t5', net='A', layer='B.Cu', a=(20, 10), b=(20, 15), width=0.2),
            dict(id='t6', net='B', layer='F.Cu', a=(30, 0), b=(31, 0), width=0.3),
            dict(id='t7', net='B', layer='F.Cu', a=(31, 0), b=(32, 0), width=0.5),
        ]

    def test_chains_split_at_junctions_layers_fixed_points_and_width_changes(self):
        chains = pg.chains_from_items(self.items())
        by = {(c['net'], c['layer'], c['points'][0], c['points'][-1]): c for c in chains}
        self.assertEqual(len(chains), 6)
        self.assertIn(('A', 'F.Cu', (0, 0), (10, 0)), by)  # the T at (10, 0) is a junction (degree 3)
        self.assertIn(('A', 'B.Cu', (10, 10), (20, 15)), by)  # degree-2 node (20, 10) is interior
        self.assertEqual(len(by[('A', 'B.Cu', (10, 10), (20, 15))]['edges']), 2)
        self.assertIn(('B', 'F.Cu', (30, 0), (31, 0)), by)  # width change splits
        split = pg.chains_from_items(self.items(), fixed={(20, 10)})
        self.assertEqual(len(split), 7)
        for chain in chains:
            self.assertEqual(chain['points'][0], chain['edges'][0]['a'])
            self.assertEqual(chain['points'][-1], chain['edges'][-1]['b'])
            for e, f in zip(chain['edges'], chain['edges'][1:]):
                self.assertEqual(e['b'], f['a'])

    def test_arcs_are_ordinary_edges(self):
        items = [dict(id='s', net='A', layer='F.Cu', a=(0, 0), b=(9, 0), width=0.2),
                 dict(id='arc', net='A', layer='F.Cu', a=(9, 0), b=(10, 1), mid=(9.7, 0.3), kind='arc', width=0.2),
                 dict(id='s2', net='A', layer='F.Cu', a=(10, 1), b=(10, 9), width=0.2)]
        chains = pg.chains_from_items(items)
        self.assertEqual(len(chains), 1)
        self.assertEqual([e['kind'] for e in chains[0]['edges']], ['seg', 'arc', 'seg'])
        self.assertEqual(chains[0]['edges'][1]['mid'], (9.7, 0.3))
        self.assertEqual(len(pg.chains_from_items(items, fixed={(9, 0)})), 2)
        self.assertEqual(pg.chains_from_items([]), [])

    def test_diagonals_clear_of_via_guards(self):
        via = (0, 0)
        self.assertTrue(pg.diagonals_clear_of([(0, 0), (0, 4), (3, 7)], [(via, 4)]))      # 4 straight cells, then the diagonal
        self.assertFalse(pg.diagonals_clear_of([(0, 0), (0, 2), (3, 5)], [(via, 4)]))     # diagonal starts 2 cells from the via
        self.assertFalse(pg.diagonals_clear_of([(0, 0), (3, 3)], [(via, 1)]))             # diagonal leaving the via centre
        self.assertTrue(pg.diagonals_clear_of([(0, 0), (0, 2), (5, 2)], [(via, 4)]))      # orthogonal only: always clear
        self.assertTrue(pg.diagonals_clear_of([(0, 0), (3, 3)], []))
        self.assertAlmostEqual(pg.point_segment_distance((0, 1), (-1, 0), (1, 0)), 1.0)
        self.assertAlmostEqual(pg.point_segment_distance((3, 0), (-1, 0), (1, 0)), 2.0)

    def test_interior_first_item_does_not_split_the_chain(self):
        # sorted order starts at the interior item (2,3)-(2,6): the chain must still be walked whole from an anchor end
        poly = [(5, 0), (5, 3), (2, 3), (2, 6), (9, 6)]
        items = [dict(id=f't{i}', net='A', layer='F.Cu', a=a, b=b, width=0.2) for i, (a, b) in enumerate(zip(poly, poly[1:]))]
        chains = pg.chains_from_items(items)
        self.assertEqual(len(chains), 1)
        self.assertEqual(len(chains[0]['edges']), 4)
        self.assertEqual(sum(1 for i in range(1, 4) if abs(pg.turn_angle(*chains[0]['points'][i - 1:i + 2])) > 85), 3)
        self.assertTrue(chains[0]['fixed_start'] and chains[0]['fixed_end'])
        self.assertIn(chains[0]['points'][0], [(5, 0), (9, 6)])
        loop = [(0, 0), (1, 0), (1, 1), (0, 1)]
        ring = [dict(id=f'r{i}', net='A', layer='F.Cu', a=a, b=b, width=0.2) for i, (a, b) in enumerate(zip(loop, loop[1:] + loop[:1]))]
        self.assertEqual(len(pg.chains_from_items(ring)), 1)   # a closed loop without anchors is one chain

    def test_fixed_accepts_net_point_pairs(self):
        items = [dict(id='a', net='A', layer='F.Cu', a=(0, 0), b=(5, 0), width=0.2), dict(id='b', net='A', layer='F.Cu', a=(5, 0), b=(5, 5), width=0.2),
                 dict(id='c', net='B', layer='F.Cu', a=(0, 1), b=(5, 1), width=0.2), dict(id='d', net='B', layer='F.Cu', a=(5, 1), b=(5, 6), width=0.2)]
        self.assertEqual(len(pg.chains_from_items(items, fixed={('A', (5, 0))})), 3)   # only net A is split at (5, 0)
        self.assertEqual(len(pg.chains_from_items(items, fixed={('B', (5, 0))})), 2)   # another net's via at (5, 0) is no anchor for A
        self.assertEqual(len(pg.chains_from_items(items, fixed={(5, 0), (5, 1)})), 4)  # bare points still anchor every net


if __name__ == '__main__':
    unittest.main()
