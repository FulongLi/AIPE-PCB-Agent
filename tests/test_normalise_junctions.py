import unittest
from automation.kicad_tools.normalise_junctions import projection,intersection


class JunctionGeometryTests(unittest.TestCase):
    def test_interior_crossing_is_retained_when_tail_is_removed(self):
        t,q=intersection((0,0),(10,0),(4,-2),(4,2))
        self.assertEqual(q,(4,0));self.assertEqual(t,.4)

    def test_disjoint_lines_are_not_junctions(self):
        self.assertIsNone(intersection((0,0),(2,0),(4,-2),(4,2)))
        self.assertIsNone(intersection((0,0),(2,0),(0,1),(2,1)))

    def test_via_annulus_contact_projects_to_the_real_segment(self):
        t,q=projection((1,.3),(0,0),(2,0))
        self.assertEqual(q,(1,0));self.assertEqual(t,.5)
        self.assertEqual(projection((3,.3),(0,0),(2,0)),(1.,(2.,0.)))
