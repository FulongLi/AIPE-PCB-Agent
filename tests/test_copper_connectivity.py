import contextlib,io,json,tempfile,unittest
from pathlib import Path
from automation.kicad_tools.copper_connectivity import analyse


class FilledIslandTests(unittest.TestCase):
    def test_zone_identity_does_not_bridge_separate_islands(self):
        def rect(x0,y0,x1,y1):return dict(shell=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],holes=[])
        records=[dict(net='N',layer='F.Cu',kind='zone',through=False,polygons=[rect(0,0,2,2),rect(8,0,10,2)]),
                 dict(net='N',layer='B.Cu',kind='zone',through=False,polygons=[rect(0,0,10,2)])]
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.json';output=Path(td)/'result.json'
            for expected,x in [(3,None),(2,1),(1,9)]:
                if x is not None:
                    for layer in ['F.Cu','B.Cu']:records.append(dict(net='N',layer=layer,kind='via',through=True,xy=[x,1],polygons=[rect(x-.3,.7,x+.3,1.3)]))
                source.write_text(json.dumps(dict(sha256='fixture',records=records)))
                with contextlib.redirect_stdout(io.StringIO()):analyse(source,output)
                self.assertEqual(json.loads(output.read_text())['nets'][0]['component_count'],expected)

    def test_zone_hole_does_not_connect_an_inner_island(self):
        shell=[[0,0],[10,0],[10,10],[0,10]];hole=[[2,2],[8,2],[8,8],[2,8]]
        records=[dict(net='N',layer='F.Cu',kind='zone',through=False,polygons=[dict(shell=shell,holes=[hole]),dict(shell=[[4,4],[6,4],[6,6],[4,6]],holes=[])])]
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source.json';output=Path(td)/'result.json';source.write_text(json.dumps(dict(sha256='fixture',records=records)))
            with contextlib.redirect_stdout(io.StringIO()):analyse(source,output)
            self.assertEqual(json.loads(output.read_text())['nets'][0]['component_count'],2)
