import math
import unittest
from automation.kicad_tools.copper_review import arc_points,reference_coverage,barrier


class CopperReviewTests(unittest.TestCase):
    def test_arc_follows_middle_point_and_length(self):
        from shapely.geometry import LineString
        pts=arc_points([1,0],[0,-1],[-1,0])
        self.assertLess(min(p[1] for p in pts),-.999)
        self.assertAlmostEqual(LineString(pts).length,math.pi,places=3)

    def test_reference_hole_is_a_real_return_discontinuity(self):
        plane=dict(net='GND',layer='In1.Cu',kind='zone',polygons=[dict(shell=[[0,0],[10,0],[10,10],[0,10]],holes=[[[4,4],[6,4],[6,6],[4,6]]])])
        trace=dict(net='CLK',layer='F.Cu',kind='track',uuid='clock',start=[1,5],end=[9,5],mid=None,polygons=[])
        result=reference_coverage([plane,trace],['CLK'],reference='GND')[0]
        self.assertAlmostEqual(result['uncovered_projection_mm'],2)
        self.assertAlmostEqual(result['projected_coverage'],.75)

    def test_barrier_checks_opposite_layers(self):
        records=[dict(net=n,layer=l,polygons=[dict(shell=[[x,0],[x+1,0],[x+1,1],[x,1]],holes=[])]) for n,l,x in [('HV','F.Cu',0),('CTRL','B.Cu',8.5)]]
        result=barrier(records,{'HV'})
        self.assertEqual(result['projected_all_layer_minimum_mm'],7.5)
        self.assertFalse(result['passed'])
