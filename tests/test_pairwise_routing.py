"""Pure geometry regressions for routing proposals, independent of pcbnew."""
import unittest
import numpy as np
from automation.kicad_tools.grid_router import Grid
from automation.kicad_tools.pairwise_router import exclude_box,exclude_segment
from automation.kicad_tools.qfp_escape import plan_dsp_escapes
from automation.kicad_tools.project_board import segment_box_distance


class PairwiseMasks(unittest.TestCase):
    def test_placement_does_not_treat_diagonal_bbox_as_copper(self):
        # A rectangle in the empty corner of a long diagonal's bounding box
        # is clear; a rectangle crossed by its centreline is not.
        d=segment_box_distance((0,0),(10,10),np.array([0,4,12]),np.array([8,4,10]),np.array([1,6,13]),np.array([9,6,11]))
        self.assertAlmostEqual(d[0],7/np.sqrt(2))
        self.assertEqual(d[1],0)
        self.assertEqual(d[2],2)

    def test_zero_length_segment_and_parallel_projection(self):
        self.assertAlmostEqual(float(segment_box_distance((0,0),(0,0),3.,4.,5.,6.)),5.)
        self.assertAlmostEqual(float(segment_box_distance((0,0),(10,0),3.,4.,5.,6.)),4.)

    def test_box_keeps_rounded_corner_clearance(self):
        grid=Grid(101,101,2,.1,1)
        mask=np.ones((101,101),dtype=bool)
        exclude_box(mask,grid,(4,4,6,6),1.)
        self.assertFalse(mask[50,30])
        self.assertFalse(mask[35,35])
        self.assertTrue(mask[30,30])
        self.assertTrue(mask[50,29])

    def test_diagonal_track_includes_both_end_caps(self):
        grid=Grid(101,101,2,.1,1)
        mask=np.ones((101,101),dtype=bool)
        exclude_segment(mask,grid,(2,2),(8,8),.5)
        self.assertFalse(mask[20,15])
        self.assertFalse(mask[85,80])
        self.assertFalse(mask[50,50])
        self.assertTrue(mask[60,50])

    def test_qfp_alternation_respects_real_via_spacing(self):
        pads=[dict(number=str(i+1),net=['1V9','GND_CTRL','3V3','SIGNAL'][i%4],xy=[12.675,.25+i*.5],size=[1.35,.25]) for i in range(12)]
        es=plan_dsp_escapes(pads,(0,0))
        self.assertEqual(len(es),len(pads))
        self.assertEqual({e['direction'] for e in es},{'in','out'})
        for a in es:
            for b in es:
                if a is b:continue
                self.assertGreaterEqual(np.linalg.norm(np.array(a['via'])-b['via']),.8)

if __name__=='__main__':unittest.main()
