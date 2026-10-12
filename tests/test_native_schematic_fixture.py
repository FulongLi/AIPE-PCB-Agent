"""Native KiCad fixture for the emitter semantics the V2.1 presentation layer relies on.

A tiny two-sheet project is written with native_schematic.Schematic (rotations 0/90/180/270 of an official
Device:R and of a generated glyph, a T-join with a junction, a hierarchical label with its root sheet pin and
one global anchor, Value-named power symbols with PWR_FLAGs, a single-occurrence global label on a local
net, (dnp yes) and a no_connect) and then checked with kicad-cli: ERC with --severity-all must report zero
findings and the exported netlist must carry the bare net names the drawing implies.  Skips without KiCad;
a skip is not a pass.
"""
import json
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from automation.kicad_tools import native_schematic as ns
from automation.kicad_tools import project_schematic as ps
from automation.kicad_tools.run_check import run_check
from automation.setup.detect_kicad import find_kicad_cli


def kicad_cli():
    try:
        return find_kicad_cli()
    except FileNotFoundError:
        return None


def pin_defs(text):
    return {n: dict(name=a, type=b) for n, a, b in (s.split(':') for s in text.split())}


def build_fixture(root: Path) -> dict:
    """Write the project; returns the expected {(ref, pad): net name}."""
    library = ps._Library(ps.kicad_data_root())
    r_official = library.extract('Device', 'R').replace('"R', '"Sym_R')  # top symbol and its _0_1 / _1_1 units
    generic_part = dict(ref='RG', value='1k', footprint='Resistor_SMD:R_0603_1608Metric', kind='R', nets={'1': 'x', '2': 'y'},
                        pins=pin_defs('1:1:passive 2:2:passive'))
    r_generic, _, _ = ps.generic_symbol(generic_part, [['1', '2']], 'Sym_RG')
    nc_part = dict(ref='U9', value='3pin', footprint='Package_TO_SOT_SMD:SOT-23', kind='IC', nets={'1': 'a', '2': None, '3': 'b'},
                   pins=pin_defs('1:A:passive 2:NC:no_connect 3:B:passive'))
    ic_def, _, _ = ps.generic_symbol(nc_part, [['1', '2', '3']], 'Sym_U9')
    rail = ns.power_symbol_definition('PWR_VRAIL', 'VRAIL')
    gnd = ns.power_symbol_definition('PWR_GND', 'GND', down=True)
    flag = ps.FLAG_DEFINITION

    kicad = root / 'kicad'
    kicad.mkdir(parents=True)
    rootsch = ns.Schematic('F', 'fixture root', 'A4', revision='fixture')
    sheet_id = ns.uid('F/sub/sheet')
    sub = ns.Schematic('F/sub', 'fixture sub', 'A3', project_name='F', instance_path='/' + rootsch.root_uuid + '/' + sheet_id,
                       revision='fixture')
    expected = {}

    def place(sch, lib_id, definition, ref, x, y, angle, nets, **kw):
        points = sch.add_symbol(lib_id, definition, ref, ref, 'Resistor_SMD:R_0603_1608Metric', x, y, 1, angle=angle, **kw)
        for pad, net in nets.items():
            if net is not None:
                expected[(ref, pad)] = net
        return points

    # chain net A: R1 (0 deg, vertical: pin 1 up) ... each rotation of the official R, pins joined by wires
    # R1 at 0: pin1 (x, y-3.81) top, pin2 bottom.  R2 at 90: pin1 (x-3.81, y) left.  R3 at 180: pin1 bottom.  R4 at 270: pin1 right.
    p1 = place(sub, 'AIPE:Sym_R', r_official, 'R1', 50.8, 50.8, 0, {'1': 'VRAIL', '2': 'A'})
    p2 = place(sub, 'AIPE:Sym_R', r_official, 'R2', 76.2, 63.5, 90, {'1': 'A', '2': 'HP'})
    p3 = place(sub, 'AIPE:Sym_R', r_official, 'R3', 101.6, 76.2, 180, {'1': 'HP', '2': 'GTAG'})
    p4 = place(sub, 'AIPE:Sym_R', r_official, 'R4', 127.0, 63.5, 270, {'1': 'GTAG', '2': 'GND'})
    assert p1['1'] == (50.8, 46.99) and p2['1'] == (72.39, 63.5) and p3['1'] == (101.6, 80.01) and p4['1'] == (130.81, 63.5), (p1, p2, p3, p4)
    # VRAIL: power symbol on R1 pin 1 through a stub, PWR_FLAG beside it
    sub.wire((50.8, 46.99), (50.8, 44.45))
    sub.add_symbol('AIPE:PWR_VRAIL', rail, '#PWR01', 'VRAIL', '', 50.8, 44.45, 1, in_bom=False, on_board=False, hide_reference=True)
    sub.wire((50.8, 44.45), (55.88, 44.45))
    sub.add_symbol('AIPE:PWR_FLAG', flag, '#FLG01', 'PWR_FLAG', '', 55.88, 44.45, 1, in_bom=False, on_board=False, hide_reference=True)
    # net A: R1 pin 2 down to the row of R2, across to R2 pin 1, with a generated R (RG, 90 deg) tapped in at a T
    sub.wire((50.8, 54.61), (50.8, 63.5))
    sub.wire((50.8, 63.5), (72.39, 63.5))
    sub.wire((60.96, 63.5), (60.96, 71.12))
    sub.junction((60.96, 63.5))
    pg = place(sub, 'AIPE:Sym_RG', r_generic, 'RG', 60.96, 78.74, 90, {'1': 'GTAG', '2': 'A'}, dnp=True)
    assert pg['2'] == (60.96, 71.12) and pg['1'] == (60.96, 86.36), pg
    sub.global_label('A', (50.8, 58.42), 180)       # single global anchor of the local net A on a wire interior (P8)
    # net HP: R2 pin 2 -> R3 pin 1 through a corner, hierarchical label at the end of a stub
    sub.wire((80.01, 63.5), (101.6, 63.5))
    sub.wire((101.6, 63.5), (101.6, 80.01))
    sub.wire((101.6, 63.5), (101.6, 55.88))
    sub.junction((101.6, 63.5))
    sub.hierarchical_label('HP', (101.6, 55.88), 'passive', 90)
    # net GTAG: R3 pin 2 (top at 180) -> R4 pin 1, RG pin 1 joins through a wire ending on a junction
    sub.wire((101.6, 72.39), (101.6, 68.58))
    sub.wire((101.6, 68.58), (130.81, 68.58))
    sub.wire((130.81, 68.58), (130.81, 63.5))
    sub.wire((60.96, 86.36), (60.96, 91.44))
    sub.wire((60.96, 91.44), (115.57, 91.44))
    sub.wire((115.57, 91.44), (115.57, 68.58))
    sub.junction((115.57, 68.58))
    sub.global_label('GTAG', (115.57, 91.44), 0)
    # GND: R4 pin 2 (left at 270) -> ground symbol + flag
    sub.wire((123.19, 63.5), (118.11, 63.5))
    sub.wire((118.11, 63.5), (118.11, 58.42))
    sub.add_symbol('AIPE:PWR_GND', gnd, '#PWR02', 'GND', '', 118.11, 58.42, 1, angle=180, in_bom=False, on_board=False, hide_reference=True)
    sub.wire((118.11, 58.42), (113.03, 58.42))
    sub.add_symbol('AIPE:PWR_FLAG', flag, '#FLG02', 'PWR_FLAG', '', 113.03, 58.42, 1, in_bom=False, on_board=False, hide_reference=True)
    # U9: pin 1 on GTAG, pin 2 no-connect, pin 3 on A (through a label-free wire pair)
    pu = place(sub, 'AIPE:Sym_U9', ic_def, 'U9', 152.4, 91.44, 0, {'1': 'GTAG', '2': None, '3': 'A'})
    sub.wire(pu['1'], (115.57, pu['1'][1]))
    sub.wire((115.57, pu['1'][1]), (115.57, 91.44))
    sub.no_connect(pu['2'])
    sub.wire(pu['3'], (pu['3'][0] + 5.08, pu['3'][1]))
    sub.global_label('A', (pu['3'][0] + 5.08, pu['3'][1]), 0)   # second occurrence of the anchor name joins by name
    sub.write(kicad / 'sub.kicad_sch')
    # root: sheet symbol with the HP pin, a stub and the global anchor (one global label fixes the bare name)
    rootsch.items.append(f'''(sheet (at 50.8 50.8) (size 50.8 25.4) (stroke (width 0.254) (type default))
            (fill (color 0 0 0 0)) (uuid "{sheet_id}")
            (property "Sheetname" "sub" (at 50.8 49.53 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
            (property "Sheetfile" "sub.kicad_sch" (at 50.8 77.47 0) (effects (font (size 1.0 1.0)) (justify left top)))
            (pin "HP" passive (at 101.6 58.42 0) (effects (font (size 1.0 1.0)) (justify right)) (uuid "{ns.uid('F/sub/pin/HP')}"))
            (instances (project "F" (path "/{rootsch.root_uuid}" (page "2")))))''')
    rootsch.wire((101.6, 58.42), (106.68, 58.42))
    rootsch.global_label('HP', (106.68, 58.42), 0)
    rootsch.write(kicad / 'F.kicad_sch')
    definitions = [r_official, r_generic, ic_def, rail, gnd, flag]
    text = '(kicad_symbol_lib (version 20250114) (generator "aipe")\n' + '\n'.join(
        d.replace('(symbol "' + name, '(symbol "AIPE:' + name, 1) for d, name in zip(definitions, ('Sym_R', 'Sym_RG', 'Sym_U9', 'PWR_VRAIL', 'PWR_GND', 'PWR_FLAG'))) + ')\n'
    (kicad / 'libraries').mkdir()
    (kicad / 'libraries/AIPE.kicad_sym').write_text(text, encoding='utf-8')
    (kicad / 'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "AIPE") (type "KiCad") (uri "${KIPRJMOD}/libraries/AIPE.kicad_sym") (options "") (descr "fixture")))\n', encoding='utf-8')
    (kicad / 'fp-lib-table').write_text('(fp_lib_table (version 7)\n  (lib (name "Resistor_SMD") (type "KiCad") (uri "${KICAD10_FOOTPRINT_DIR}/Resistor_SMD.pretty") (options "") (descr "")))\n', encoding='utf-8')
    (kicad / 'F.kicad_pro').write_text(json.dumps(ps.project_settings('F', [dict(ps.DEFAULT_CLASS)]), indent=2), encoding='utf-8')
    return expected


def build_adversarial(root: Path) -> None:
    """Case B: a global label Q on the interior of net P's wire (KiCad merges the nets); the guard must refuse the plan."""
    library = ps._Library(ps.kicad_data_root())
    r_official = library.extract('Device', 'R').replace('"R', '"Sym_R')
    kicad = root / 'kicad'
    kicad.mkdir(parents=True)
    sch = ns.Schematic('B', 'adversarial', 'A4', revision='fixture')
    # RP1 (90 deg: pin 2 at x+3.81) ... RP2 (90 deg: pin 1 at x-3.81) joined by one P wire with a P label on a stub
    p1 = sch.add_symbol('AIPE:Sym_R', r_official, 'RP1', '1k', 'Resistor_SMD:R_0603_1608Metric', 40.0, 100.0, 1, angle=90)
    p2 = sch.add_symbol('AIPE:Sym_R', r_official, 'RP2', '1k', 'Resistor_SMD:R_0603_1608Metric', 100.0, 100.0, 1, angle=90)
    pq = sch.add_symbol('AIPE:Sym_R', r_official, 'RQ', '1k', 'Resistor_SMD:R_0603_1608Metric', 70.0, 120.0, 1, angle=90)
    sch.wire(p1['2'], p2['1'])
    sch.wire((50.0, 100.0), (50.0, 95.0))
    sch.global_label('P', (50.0, 95.0), 0)
    sch.wire(p1['1'], (p1['1'][0] - 5.0, 100.0))
    sch.global_label('P1', (p1['1'][0] - 5.0, 100.0), 180)
    sch.wire(p2['2'], (p2['2'][0] + 5.0, 100.0))
    sch.global_label('P2', (p2['2'][0] + 5.0, 100.0), 0)
    sch.wire(pq['1'], (60.0, 120.0))
    sch.global_label('Q', (60.0, 120.0), 180)
    sch.wire(pq['2'], (80.0, 120.0))
    sch.global_label('Q', (80.0, 120.0), 0)
    sch.global_label('Q', (70.0, 100.0), 0)          # the stray label: on the interior of the P wire
    sch.write(kicad / 'B.kicad_sch')
    text = '(kicad_symbol_lib (version 20250114) (generator "aipe")\n' + r_official.replace('(symbol "Sym_R', '(symbol "AIPE:Sym_R', 1) + ')\n'
    (kicad / 'libraries').mkdir()
    (kicad / 'libraries/AIPE.kicad_sym').write_text(text, encoding='utf-8')
    (kicad / 'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "AIPE") (type "KiCad") (uri "${KIPRJMOD}/libraries/AIPE.kicad_sym") (options "") (descr "fixture")))\n', encoding='utf-8')
    (kicad / 'fp-lib-table').write_text('(fp_lib_table (version 7)\n  (lib (name "Resistor_SMD") (type "KiCad") (uri "${KICAD10_FOOTPRINT_DIR}/Resistor_SMD.pretty") (options "") (descr "")))\n', encoding='utf-8')
    (kicad / 'B.kicad_pro').write_text(json.dumps(ps.project_settings('B', [dict(ps.DEFAULT_CLASS)]), indent=2), encoding='utf-8')
    return dict(p1=p1, p2=p2, pq=pq)


@unittest.skipUnless(kicad_cli() and ps.kicad_data_root(), 'kicad-cli and the KiCad symbol library are required')
class AdversarialLabelTests(unittest.TestCase):
    def test_label_of_another_net_on_a_wire_interior_merges_in_kicad_and_fails_the_guard(self):
        from automation.kicad_tools import schematic_wiring as sw
        with tempfile.TemporaryDirectory(prefix='aipe_adv_') as temp:
            root = Path(temp)
            points = build_adversarial(root)
            xml = root / 'netlist.xml'
            run = subprocess.run([str(kicad_cli()), 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', str(xml),
                                  str(root / 'kicad/B.kicad_sch')], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
            self.assertEqual(run.returncode, 0, run.stderr)
            tree = ET.parse(xml).getroot()
            drawn = {}
            for net in tree.findall('nets/net'):
                for node in net.findall('node'):
                    drawn[(node.attrib['ref'], node.attrib['pin'])] = net.attrib['name']
            # KiCad connects the Q label to the P wire: the P pins and the Q pins end up on one net
            self.assertEqual(len({drawn[('RP1', '2')], drawn[('RP2', '1')], drawn[('RQ', '1')], drawn[('RQ', '2')]}), 1, drawn)
            # the guard sees the same geometry and refuses it
            w = sw.SheetWiring()
            p1, p2, pq = points['p1'], points['p2'], points['pq']
            w.pins = {('RP1', '2'): dict(point=p1['2'], net='P'), ('RP2', '1'): dict(point=p2['1'], net='P'),
                      ('RP1', '1'): dict(point=p1['1'], net='P1'), ('RP2', '2'): dict(point=p2['2'], net='P2'),
                      ('RQ', '1'): dict(point=pq['1'], net='Q'), ('RQ', '2'): dict(point=pq['2'], net='Q')}
            w.segments = [sw.Segment('P', p1['2'], p2['1']), sw.Segment('P', (50.0, 100.0), (50.0, 95.0)),
                          sw.Segment('P1', p1['1'], (p1['1'][0] - 5.0, 100.0)), sw.Segment('P2', p2['2'], (p2['2'][0] + 5.0, 100.0)),
                          sw.Segment('Q', pq['1'], (60.0, 120.0)), sw.Segment('Q', pq['2'], (80.0, 120.0))]
            w.labels = [dict(kind='global', name='P', point=(50.0, 95.0)), dict(kind='global', name='P1', point=(p1['1'][0] - 5.0, 100.0)),
                        dict(kind='global', name='P2', point=(p2['2'][0] + 5.0, 100.0)), dict(kind='global', name='Q', point=(60.0, 120.0)),
                        dict(kind='global', name='Q', point=(80.0, 120.0)), dict(kind='global', name='Q', point=(70.0, 100.0))]
            sw.normalise(w)
            parts = [dict(ref='RP1', nets={'1': 'P1', '2': 'P'}), dict(ref='RP2', nets={'1': 'P', '2': 'P2'}), dict(ref='RQ', nets={'1': 'Q', '2': 'Q'})]
            report = sw.compare_with_model(sw.connectivity({'s': w}, [], []), parts)
            self.assertFalse(report['identical'])
            self.assertTrue(any(p['kind'] == 'label_on_other_net' for p in report['problems']), report)
            self.assertTrue(report['multi_named'], report)


@unittest.skipUnless(kicad_cli() and ps.kicad_data_root(), 'kicad-cli and the KiCad symbol library are required')
class NativeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='aipe_fixture_')
        cls.root = Path(cls.temp.name)
        cls.expected = build_fixture(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_erc_with_severity_all_is_clean(self):
        code, manifest = run_check('erc', self.root / 'kicad/F.kicad_sch', self.root / 'erc')
        data = json.loads(manifest.read_text(encoding='utf-8'))
        details = []
        if data.get('finding_count'):
            report = json.loads(Path(data['report']).read_text(encoding='utf-8-sig'))
            details = [(s.get('path'), v['type'], v['description'], [i['description'] for i in v.get('items', [])])
                       for s in report['sheets'] for v in s['violations']]
        self.assertEqual(data['finding_count'], 0, details)
        self.assertEqual(code, 0)

    def test_netlist_names_follow_the_drawing(self):
        xml = self.root / 'netlist.xml'
        run = subprocess.run([str(kicad_cli()), 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', str(xml),
                              str(self.root / 'kicad/F.kicad_sch')], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
        self.assertEqual(run.returncode, 0, run.stderr)
        tree = ET.parse(xml).getroot()
        drawn = {}
        for net in tree.findall('nets/net'):
            for node in net.findall('node'):
                drawn[(node.attrib['ref'], node.attrib['pin'])] = net.attrib['name']
        for key, name in self.expected.items():
            self.assertEqual(drawn.get(key), name, key)
        self.assertNotIn(('U9', '2'), {k for k, v in drawn.items() if not v.startswith('unconnected-')})
        # rotated pins connected, DNP pins still in the netlist, hierarchical-only net named by the root anchor
        self.assertEqual(drawn[('RG', '2')], 'A')
        self.assertEqual(drawn[('R2', '2')], 'HP')
        self.assertEqual(drawn[('R4', '2')], 'GND')
        dnp = [c for c in tree.findall('components/comp') if c.attrib['ref'] == 'RG'][0]
        self.assertIsNotNone(dnp.find("property[@name='dnp']"))


if __name__ == '__main__':
    unittest.main()
