import unittest
from automation.kicad_tools.sheet_resistance import solve


class SheetResistanceTest(unittest.TestCase):
    def test_rectangle_agrees_with_number_of_squares(self):
        poly=lambda x0,x1:dict(shell=[[x0,0],[x1,0],[x1,5],[x0,5]],holes=[])
        records=[dict(net='P',layer='F.Cu',kind='zone',polygons=[poly(0,10)])]
        for ref,x0,x1 in [('IN',0,1),('OUT',9,10)]:records.append(dict(net='P',layer='F.Cu',kind='pad',ref=ref,pin='1',polygons=[poly(x0,x1)]))
        r=solve(records,'P',{('IN','1')},{('OUT','1')},grid=.25,layers=('F.Cu',),z=(0.,),temperature=20.)
        self.assertEqual(r['status'],'mesh_solved')
        # Equipotential strips occupy the outer 1 mm. Their nearest cell
        #centres are 8.25 mm apart on this grid, with 5 mm sheet width.
        self.assertAlmostEqual(r['resistance_mOhm'],1.724e-5*8.25/(5*.07)*1000,places=8)
