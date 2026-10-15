import unittest
from shapely.geometry import Polygon,LineString
from automation.kicad_tools.copper_paths import CopperPaths


class CopperPathTests(unittest.TestCase):
    def test_path_goes_around_real_hole(self):
        outer=[(0,0),(10,0),(10,6),(0,6)];hole=[(4,1),(6,1),(6,5),(4,5)]
        r=dict(net='N',layer='F.Cu',kind='zone',uuid='z',polygons=[dict(shell=outer,holes=[hole])])
        g=CopperPaths([r],'N',(0,0,10,6),grid=.25,layers=('F.Cu',),z=(0.,))
        p=g.path([1,3,0.],[9,3,0.]);line=LineString([v[:2] for v in p['points']])
        self.assertTrue(Polygon(outer,[hole]).buffer(1e-5).covers(line))
        self.assertGreater(line.length,8)

    def test_separate_layers_do_not_join_without_via(self):
        r=[dict(net='N',layer=l,kind='zone',uuid=l,polygons=[dict(shell=[(0,0),(4,0),(4,4),(0,4)],holes=[])]) for l in ['F.Cu','B.Cu']]
        g=CopperPaths(r,'N',(0,0,4,4),layers=('F.Cu','B.Cu'),z=(0.,-1.6))
        with self.assertRaises(ValueError):g.path([1,1,0.],[3,3,-1.6])
