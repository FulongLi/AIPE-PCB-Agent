"""Tests for the V2.1 schematic presentation layer (schematic_presentation + the wired path of project_schematic).

Everything here runs without KiCad (generated symbols); the native checks of the same drawing are in
test_native_schematic_fixture.py and test_generate_sic_schematics.py.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from automation.kicad_tools import project_schematic as ps
from automation.kicad_tools import schematic_presentation as sp
from automation.kicad_tools import schematic_metrics as sm
from automation.kicad_tools.native_schematic import children, parse


def pin_defs(text):
    return {n: dict(name=a, type=b) for n, a, b in (s.split(':') for s in text.split())}


TWO = pin_defs('1:1:passive 2:2:passive')


def part(ref, kind, nets, pins=None, page='p1', footprint='Resistor_SMD:R_0805_2012Metric', **extra):
    return dict(ref=ref, value=extra.pop('value', kind), footprint=footprint, kind=kind, page=page, nets=dict(nets),
                pins=copy.deepcopy(pins) if pins else {k: dict(name=k, type='passive') for k in nets}, **extra)


def wired_spec(root, **overrides):
    """Two pages: a regulator with its satellites, a connector page sharing cross nets; rails by supply:auto."""
    parts = [
        part('U1', 'IC', {'1': 'IN', '2': 'OUT', '3': 'VCC', '4': 'GND', '5': None, '6': 'EN'},
             pin_defs('1:IN:input 2:OUT:output 3:VCC:power_in 4:GND:power_in 5:NC:no_connect 6:EN:input'),
             footprint='Package_TO_SOT_SMD:SOT-23-6'),
        part('R1', 'R', {'1': 'IN', '2': 'MID'}, TWO), part('R2', 'R', {'1': 'MID', '2': 'GND'}, TWO),
        part('C1', 'C', {'1': 'VCC', '2': 'GND'}, TWO), part('C2', 'C', {'1': 'VCC', '2': 'GND'}, TWO),
        part('R3', 'R', {'1': 'VCC', '2': 'EN'}, TWO), part('C3', 'C', {'1': 'OUT', '2': 'GND'}, TWO),
        part('R4', 'R', {'1': 'OUT', '2': 'FB'}, TWO), part('R5', 'R', {'1': 'FB', '2': 'GND'}, TWO),
        part('U2', 'IC', {'1': 'VREG', '2': 'GND', '3': 'VCC'}, pin_defs('1:VOUT:power_out 2:GND:power_in 3:VIN:power_in'),
             footprint='Package_TO_SOT_SMD:SOT-23', page='p2'),
        part('C4', 'C', {'1': 'VREG', '2': 'GND'}, TWO, page='p2'),
        part('J1', 'J', {'1': 'IN', '2': 'GND', '3': 'FB', '4': 'VREG'}, page='p2',
             footprint='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical'),
        part('TP1', 'TP', {'1': 'OUT'}, footprint='TestPoint:TestPoint_Pad_D2.0mm', page='p2'),
        part('H1', 'H', {}, pins={}, footprint='MountingHole:MountingHole_3.2mm_M3', page='p2'),
    ]
    spec = dict(name='W', title='wired test', kicad_dir=root / 'kicad', design_dir=root / 'design',
                pages={'p1': 'Regulator', 'p2': 'Connector'}, parts=parts, flag_nets=['VCC', 'GND'], flag_page='p1',
                presentation=dict(supply='auto'))
    spec.update(overrides)
    return spec


class PolicyTests(unittest.TestCase):
    def test_coerce_presentation(self):
        self.assertIsNone(sp.coerce_presentation(None))
        self.assertIsNone(sp.coerce_presentation('legacy'))
        self.assertIsNone(sp.coerce_presentation(dict(style='legacy')))
        wired = sp.coerce_presentation('wired')
        self.assertEqual(wired['supply'], 'auto')
        with self.assertRaises(ValueError):
            sp.coerce_presentation(dict(bogus=1))
        with self.assertRaises(ValueError):
            sp.coerce_presentation(dict(style='fancy'))

    def test_rails_are_flag_nets_plus_power_out_minus_excluded(self):
        spec = ps.coerce_spec(wired_spec(Path('x')))
        nets = sp.classify_nets(spec.parts, spec.flag_nets, spec.presentation)
        self.assertEqual({n for n, i in nets.items() if i['role'] == 'rail'}, {'VCC', 'GND', 'VREG'})
        self.assertEqual(nets['IN']['role'], 'cross')
        self.assertEqual(nets['MID']['role'], 'local')
        self.assertTrue(nets['GND']['down'])
        self.assertFalse(nets['VCC']['down'])
        spec = ps.coerce_spec(wired_spec(Path('x'), presentation=dict(supply='auto', exclude_supply=['VREG'])))
        nets = sp.classify_nets(spec.parts, spec.flag_nets, spec.presentation)
        self.assertEqual(nets['VREG']['role'], 'local')
        spec = ps.coerce_spec(wired_spec(Path('x'), presentation=dict(supply=['GND'])))
        nets = sp.classify_nets(spec.parts, spec.flag_nets, spec.presentation)
        self.assertEqual({n for n, i in nets.items() if i['role'] == 'rail'}, {'GND'})

    def test_port_shapes_follow_the_driving_pins(self):
        spec = ps.coerce_spec(wired_spec(Path('x')))
        nets = sp.classify_nets(spec.parts, spec.flag_nets, spec.presentation)
        self.assertEqual(sp.port_shape('IN', 'p1', nets['IN']), 'passive')
        self.assertEqual(sp.port_shape('OUT', 'p1', nets['OUT']), 'output')
        self.assertEqual(sp.port_shape('OUT', 'p2', nets['OUT']), 'input')

    def test_auto_groups_attach_satellites_to_their_anchor(self):
        spec = ps.coerce_spec(wired_spec(Path('x')))
        nets = sp.classify_nets(spec.parts, spec.flag_nets, spec.presentation)
        page1 = [p for p in spec.parts if p['page'] == 'p1']
        groups = sp.auto_groups(page1, nets)
        self.assertEqual(set(groups.values()), {'p1/U1'})
        page2 = [p for p in spec.parts if p['page'] == 'p2']
        groups = sp.auto_groups(page2, nets)
        self.assertEqual(groups['H1'], 'p2/mechanical')
        self.assertEqual(groups['C4'], 'p2/U2')
        self.assertEqual(groups['J1'], 'p2/J1')

    def test_angle_for_orients_two_pin_symbols(self):
        p = part('R9', 'R', {'1': 'A', '2': 'B'}, TWO)
        definition, _, _ = ps.generic_symbol(p, [['1', '2']], 'Sym_R9')
        self.assertEqual(sp.angle_for(definition, 1, '1', (0, -1)), 270)
        self.assertEqual(sp.angle_for(definition, 1, '1', (0, 1)), 90)
        self.assertEqual(sp.angle_for(definition, 1, '1', (-1, 0)), 0)
        self.assertEqual(sp.angle_for(definition, 1, '2', (-1, 0)), 180)


class WiredGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aipe_wired_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_wired_project_is_connected_named_and_free_of_pin_stub_labels(self):
        result = ps.generate_project(wired_spec(self.root))
        self.assertEqual(result['continuation_sheets'], [])
        self.assertEqual(result['parts_placed'], 14)
        summary = result['presentation']
        self.assertTrue(summary['guard']['identical'])
        self.assertEqual(summary['guard']['pads_checked'], 31)
        self.assertEqual(summary['exceptions'], [])
        self.assertEqual(summary['nets']['VREG']['role'], 'rail')
        mapping = json.loads(Path(result['mapping']).read_text(encoding='utf-8'))
        self.assertEqual(set(mapping['paths']), {p['ref'] for p in wired_spec(self.root)['parts']})
        self.assertIn('angle', mapping['placement']['R1'][0])
        kicad = self.root / 'kicad'
        root = parse((kicad / 'W.kicad_sch').read_text(encoding='utf-8'))
        sheets = children(root, 'sheet')
        self.assertEqual(len(sheets), 2)
        # every cross net is a sheet pin on both sheets plus a global anchor on the root; rails are not ports
        pins_by_sheet = {}
        for sheet in sheets:
            name = next(p[2] for p in children(sheet, 'property') if p[1] == 'Sheetfile')
            pins_by_sheet[name] = sorted(pin[1] for pin in children(sheet, 'pin'))
        self.assertEqual(pins_by_sheet['p1.kicad_sch'], ['FB', 'IN', 'OUT'])
        self.assertEqual(pins_by_sheet['p2.kicad_sch'], ['FB', 'IN', 'OUT'])
        anchors = sorted(l[1] for l in children(root, 'global_label'))
        self.assertEqual(anchors, ['FB', 'FB', 'IN', 'IN', 'OUT', 'OUT'])
        for key, expected_hier in (('p1', ['FB', 'IN', 'OUT']), ('p2', ['FB', 'IN', 'OUT'])):
            tree = parse((kicad / f'{key}.kicad_sch').read_text(encoding='utf-8'))
            self.assertEqual(sorted(l[1] for l in children(tree, 'hierarchical_label')), expected_hier)
            self.assertFalse(children(tree, 'label'), 'no local labels (they would rename nets)')
        self.assertTrue(children(parse((kicad / 'p1.kicad_sch').read_text(encoding='utf-8')), 'junction'))
        p1 = sm.measure_sheet(kicad / 'p1.kicad_sch')
        self.assertEqual(p1['global_labels_on_pin_stubs'], 0)
        self.assertEqual(p1['off_grid_points'], 0)
        self.assertEqual(p1['dangling_wire_ends'], 0)
        self.assertEqual(p1['isolated_symbols'], 0)
        self.assertGreater(p1['power_symbols'], 3)
        self.assertGreaterEqual(p1['wired_pin_share'], 0.6)
        # name tags: exactly one global label per local net on the project
        tags = []
        for key in ('p1', 'p2'):
            tree = parse((kicad / f'{key}.kicad_sch').read_text(encoding='utf-8'))
            tags += [l[1] for l in children(tree, 'global_label')]
        self.assertEqual(sorted(tags), ['EN', 'MID'], 'exactly one name tag per local net')
        # DNP and rotation are written
        lib = (kicad / 'libraries/AIPE.kicad_sym').read_text(encoding='utf-8')
        self.assertIn('(power)', lib)
        text = (kicad / 'p1.kicad_sch').read_text(encoding='utf-8')
        self.assertIn('(at ', text)
        self.assertRegex(text, r'\(symbol \(lib_id "AIPE:Sym_R\d"\) \(at [\d.]+ [\d.]+ (90|270)\)')

    def test_every_unconnected_pin_gets_a_no_connect_marker_whatever_its_placement(self):
        # D (3 pins, one NC) is drawn as a free-lane terminal, J (header) as an anchor, U1 pin 5 through a lane: all marked
        spec = wired_spec(self.root)
        spec['parts'].append(part('D1', 'D', {'1': 'OUT', '2': None, '3': 'GND'}, pin_defs('1:A:passive 2:NC:no_connect 3:K:passive'),
                                  footprint='Package_TO_SOT_SMD:SOT-23'))
        spec['parts'].append(part('J3', 'J', {'1': 'FB', '2': None, '3': None, '4': 'GND'}, page='p2',
                                  footprint='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical'))
        result = ps.generate_project(spec)
        expected = sum(1 for p in spec['parts'] for n in p['nets'].values() if n is None)
        drawn = 0
        for page in ('p1', 'p2'):
            tree = parse((self.root / f'kicad/{page}.kicad_sch').read_text(encoding='utf-8'))
            drawn += len(children(tree, 'no_connect'))
        self.assertEqual(drawn, expected)
        self.assertEqual(result['presentation']['no_connects'], dict(expected=expected, drawn=expected))
        self.assertEqual(sum(s['counts']['no_connects'] for s in result['presentation']['sheets']), expected)

    def test_rail_pins_are_grouped_per_side_so_alternating_supplies_share_one_bus(self):
        # VSS / VDD alternate on every side of the generic symbol: the wired drawing reorders them per side into two buses
        nets = {}
        pins = []
        for i in range(1, 17):
            net = 'VSS' if i % 2 else 'VCC'
            nets[str(i)] = net
            pins.append(f'{i}:{net}{i}:power_in')
        nets['17'], nets['18'] = 'IN', 'OUT'
        pins += ['17:IN:input', '18:OUT:output']
        big = part('U5', 'DSP', nets, pin_defs(' '.join(pins)), footprint='Package_QFP:LQFP-176_24x24mm_P0.5mm')
        spec = wired_spec(self.root)
        spec['parts'].append(big)
        spec['parts'].append(part('C9', 'C', {'1': 'VCC', '2': 'VSS'}, TWO))
        spec['flag_nets'] = ['VCC', 'GND', 'VSS']
        result = ps.generate_project(spec)
        text = (self.root / 'kicad/p1.kicad_sch').read_text(encoding='utf-8')
        tree = parse(text)
        import re
        lib = (self.root / 'kicad/libraries/AIPE.kicad_sym').read_text(encoding='utf-8')
        start = lib.index('(symbol "Sym_U5"')
        end = re.search(r'\(symbol "Sym_(?!U5)', lib[start + 1:])
        sym = lib[start:start + 1 + end.start()] if end else lib[start:]
        # per side the rail pins are contiguous: pin names in y order on the left side read VSS* then VCC* (or the reverse)
        left = sorted([(float(m.group(2)), m.group(3)) for m in re.finditer(r'\(pin power_in line \(at (-[\d.]+) ([-\d.]+) 0\)[^\n]*?\(name "(\w+)"', sym)], reverse=True)
        names = [n for _, n in left]
        runs = [k for k, _ in __import__('itertools').groupby(n.rstrip('0123456789') for n in names)]
        self.assertLessEqual(len(runs), 2, names)
        self.assertEqual(result['presentation']['guard']['identical'], True)
        # legacy symbols keep pin-number order
        legacy_root = self.root / 'legacy'
        ps.generate_project(wired_spec(legacy_root, presentation=None, parts=spec['parts']))
        lib2 = (legacy_root / 'kicad/libraries/AIPE.kicad_sym').read_text(encoding='utf-8')
        start2 = lib2.index('(symbol "Sym_U5"')
        end2 = re.search(r'\(symbol "Sym_(?!U5)', lib2[start2 + 1:])
        sym2 = lib2[start2:start2 + 1 + end2.start()] if end2 else lib2[start2:]
        left2 = sorted([(float(m.group(2)), m.group(3)) for m in re.finditer(r'\(pin power_in line \(at (-[\d.]+) ([-\d.]+) 0\)[^\n]*?\(name "(\w+)"', sym2)], reverse=True)
        self.assertEqual([n for _, n in left2], ['VSS1', 'VCC2', 'VSS3', 'VCC4', 'VSS5', 'VCC6', 'VSS7', 'VCC8', 'VSS9'][:len(left2)])

    def test_packing_fill_and_free_lane_columns(self):
        # bottom-left packing puts a short wide group beside two stacked narrow ones where column packing cannot
        class L:
            def __init__(self, w, h, title):
                self.bbox, self.title = (0.0, 0.0, w, h), title
        PAPER = {'A3': (420.0, 297.0), 'A2': (594.0, 420.0)}
        layouts = [L(280.0, 100.0, 'a'), L(70.0, 100.0, 'b'), L(280.0, 90.0, 'c')]
        paper, positions = sp.pack_sheet(layouts, ['A3', 'A2'], PAPER, 10.0)
        self.assertEqual(paper, 'A3')
        self.assertEqual(len(positions), 3)
        rects = []
        for layout, x, y in positions:
            rects.append((x, y, x + layout.bbox[2], y + layout.bbox[3]))
        left, top, right, bottom = sp.paper_area(paper, PAPER)
        for x0, y0, x1, y1 in rects:
            self.assertGreaterEqual(x0, left)
            self.assertGreaterEqual(y0, top)
            self.assertLessEqual(x1, right)
            self.assertLessEqual(y1, bottom)
        for i in range(3):
            for j in range(i + 1, 3):
                a, b = rects[i], rects[j]
                self.assertFalse(a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3], (a, b))
        self.assertGreater(sp.paper_fill(layouts, 'A3', PAPER), 0.5)
        # free lanes wrap into columns: 20 lone test points stay within max_col_mm instead of a 250 mm column
        spec = wired_spec(self.root)
        for i in range(20):
            spec['parts'].append(part(f'TP{i + 10}', 'TP', {'1': 'OUT'}, footprint='TestPoint:TestPoint_Pad_D2.0mm', page='p2'))
        result = ps.generate_project(spec)
        p2 = next(s for s in result['presentation']['sheets'] if s['key'] == 'p2')
        self.assertEqual(p2['paper'], 'A3')
        self.assertIn('paper_fill', p2['counts'])
        self.assertTrue(result['presentation']['guard']['identical'])

    def test_long_detour_becomes_a_name_tag_pair(self):
        # a route whose only path is far longer than the pin distance is replaced by a pair of global name tags
        spec = wired_spec(self.root)
        # distance rule off and the second IC inside U1's group (close to the MID chain): the planner leaves the join to
        # the router, whose (patched) long detour must then be replaced by a tag pair
        spec['presentation'] = dict(supply='auto', loop_slack_mm=0.0, max_wire_mm=1000.0, groups={'U6': 'U1'})
        # a second IC on MID: the lanes draw two MID components, the router must join them
        spec['parts'].append(part('U6', 'IC', {'1': 'MID', '2': 'GND', '3': 'VCC'}, pin_defs('1:IN:input 2:GND:power_in 3:VCC:power_in'),
                                  footprint='Package_TO_SOT_SMD:SOT-23'))
        original = sp.sw.WireGrid.route

        def long_route(self_, net, sources, targets, margin=24):
            path = original(self_, net, sources, targets, margin)
            if path and net == 'MID':
                a, b = path[0], path[-1]
                far = round(max(p[1] for p in path) + 50.8, 2)
                return [a, (a[0], far), (b[0], far), b]
            return path
        sp.sw.WireGrid.route = long_route
        try:
            result = ps.generate_project(spec)
        finally:
            sp.sw.WireGrid.route = original
        p1 = next(s for s in result['presentation']['sheets'] if s['key'] == 'p1')
        tree = parse((self.root / 'kicad/p1.kicad_sch').read_text(encoding='utf-8'))
        mid_tags = [l for l in children(tree, 'global_label') if l[1] == 'MID']
        self.assertTrue(result['presentation']['guard']['identical'])
        self.assertGreaterEqual(p1['counts']['loop_tags'], 1, p1['counts'])
        self.assertGreaterEqual(len(mid_tags), 2)

    def test_include_supply_promotes_a_passive_net_to_a_rail(self):
        spec = wired_spec(self.root)
        nets = sp.classify_nets(spec['parts'], spec['flag_nets'], sp.coerce_presentation(dict(supply='auto')))
        self.assertEqual(nets['FB']['role'], 'cross')
        nets = sp.classify_nets(spec['parts'], spec['flag_nets'], sp.coerce_presentation(dict(supply='auto', include_supply=['FB'])))
        self.assertEqual(nets['FB']['role'], 'rail')
        self.assertEqual(sp.coerce_presentation(dict(label_size=1))['label_size'], 1.0)

    def test_dnp_flag_and_no_connect_are_emitted(self):
        spec = wired_spec(self.root)
        spec['parts'][1]['dnp'] = True
        result = ps.generate_project(spec)
        text = (self.root / 'kicad/p1.kicad_sch').read_text(encoding='utf-8')
        self.assertIn('(dnp yes)', text)
        tree = parse(text)
        self.assertEqual(len(children(tree, 'no_connect')), 1)
        self.assertTrue(result['presentation']['guard']['identical'])

    def test_guard_rejects_a_plan_that_does_not_reproduce_the_model(self):
        spec = wired_spec(self.root)
        original = sp.Planner.plan_page

        def broken(self_, page, page_parts, flag_nets, is_flag_page, *args, **kwargs):
            planned = original(self_, page, page_parts, flag_nets, is_flag_page, *args, **kwargs)
            if page == 'p1':
                layout = planned['layouts'][0]
                layout.labels = [l for l in layout.labels if l['name'] != 'MID']   # drop the MID name tag
                self_.tags_placed.discard('MID')
            return planned
        sp.Planner.plan_page = broken
        try:
            with self.assertRaises(ValueError) as ctx:
                ps.generate_project(spec)
        finally:
            sp.Planner.plan_page = original
        self.assertIn('connectivity guard', str(ctx.exception))
        self.assertFalse((self.root / 'kicad/W.kicad_sch').exists(), 'nothing is written when the guard fails')

    def test_wired_output_is_deterministic_and_legacy_path_is_untouched(self):
        a, b = self.root / 'a', self.root / 'b'
        ps.generate_project(wired_spec(a))
        ps.generate_project(wired_spec(b))
        for path in sorted((a / 'kicad').rglob('*')):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (b / 'kicad' / path.relative_to(a / 'kicad')).read_bytes(), path.name)
        legacy = ps.generate_project(wired_spec(self.root / 'legacy', presentation=None))
        self.assertNotIn('presentation', legacy)
        tree = parse((self.root / 'legacy/kicad/p1.kicad_sch').read_text(encoding='utf-8'))
        self.assertFalse(children(tree, 'junction'))
        self.assertFalse(children(tree, 'hierarchical_label'))

    def test_explicit_groups_and_titles_drive_the_headings(self):
        spec = wired_spec(self.root, presentation=dict(supply='auto', groups={'R4': 'feedback', 'R5': 'feedback'},
                                                          group_titles={'feedback': 'Feedback divider'}))
        result = ps.generate_project(spec)
        groups = result['presentation']['groups']['p1']
        self.assertIn('Feedback divider', [g['title'] for g in groups])
        feedback = next(g for g in groups if g['title'] == 'Feedback divider')
        self.assertEqual(sorted(feedback['parts']), ['R4', 'R5'])
        text = (self.root / 'kicad/p1.kicad_sch').read_text(encoding='utf-8')
        self.assertIn('"Feedback divider"', text)


class V21ReviewFixesTests(unittest.TestCase):
    """Generator defects found in the V2.1 visual review and their fixes (all generic, no project-specific code)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aipe_wired_fix_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _labels(self, page):
        tree = parse((self.root / f'kicad/{page}.kicad_sch').read_text(encoding='utf-8'))
        out = []
        for kind in ('hierarchical_label', 'global_label'):
            for l in children(tree, kind):
                at = children(l, 'at')[0]
                just = children(children(l, 'effects')[0], 'justify')
                out.append(dict(kind=kind, name=l[1], x=float(at[1]), y=float(at[2]), angle=float(at[3]) if len(at) > 3 else 0.0,
                                justify=just[0][1] if just else '', shape=children(l, 'shape')[0][1] if children(l, 'shape') else None))
        return out

    def test_labels_keep_their_angle_shape_and_justification(self):
        # a free-lane port at a left-running wire end is emitted at 180 / justify right (text away from the wire); lane-end
        # ports keep the shape of the net's driving pins instead of the generic 'bidirectional'
        ps.generate_project(wired_spec(self.root))
        labels = self._labels('p1')
        hier = [l for l in labels if l['kind'] == 'hierarchical_label']
        self.assertTrue(hier)
        for l in hier:
            self.assertEqual(l['justify'], 'right' if l['angle'] in (180.0, 270.0) else 'left', l)
        out = next(l for l in hier if l['name'] == 'OUT')
        self.assertEqual(out['shape'], 'output')
        p2 = [l for l in self._labels('p2') if l['kind'] == 'hierarchical_label']
        left = [l for l in p2 if l['angle'] == 180.0]
        self.assertTrue(left, 'the connector page has ports on left-running lanes')
        # a label's text never lies on its own wire: for a 180 label the wire continues to the right of the anchor
        tree = parse((self.root / 'kicad/p2.kicad_sch').read_text(encoding='utf-8'))
        wires = [tuple((float(xy[1]), float(xy[2])) for xy in children(children(w, 'pts')[0], 'xy')) for w in children(tree, 'wire')]
        for l in left:
            touching = [w for w in wires if (l['x'], l['y']) in w and w[0][1] == w[1][1]]
            for w in touching:
                other = w[1] if w[0] == (l['x'], l['y']) else w[0]
                self.assertGreater(other[0], l['x'], (l, w))

    def test_power_glyphs_point_away_from_the_wire_and_rails_are_ordered(self):
        import re
        ps.generate_project(wired_spec(self.root))
        text = (self.root / 'kicad/p1.kicad_sch').read_text(encoding='utf-8')
        gnd = re.findall(r'\(lib_id "AIPE:PWR_GND"\) \(at [\d.]+ [\d.]+ (\d+)\)', text)
        vcc = re.findall(r'\(lib_id "AIPE:PWR_VCC"\) \(at [\d.]+ [\d.]+ (\d+)\)', text)
        self.assertTrue(gnd and vcc)
        # a ground-style body hangs below its point unrotated (angle 0); the 180 rotation that used to turn every ground
        # glyph upside down into its wire is gone
        self.assertIn('0', gnd)
        self.assertNotIn('180', gnd)
        self.assertIn('0', vcc)
        # generated symbols put supply pins first and ground pins last on each side
        lib = (self.root / 'kicad/libraries/AIPE.kicad_sym').read_text(encoding='utf-8')
        start = lib.index('(symbol "Sym_U1"')
        end = re.search(r'\(symbol "Sym_(?!U1)', lib[start + 1:])
        sym = lib[start:start + 1 + end.start()] if end else lib[start:]
        left = sorted([(float(m.group(1)), m.group(2)) for m in re.finditer(r'\(pin \w+ line \(at -[\d.]+ ([-\d.]+) 0\)[^\n]*?\(name "(\w+)"', sym)],
                      reverse=True)
        names = [n for _, n in left]
        if 'VCC' in names and 'GND' in names:
            self.assertLess(names.index('VCC'), names.index('GND'))

    def test_item_less_lanes_stay_on_their_pin_rows(self):
        # a connector whose signal pins carry no satellites: every port sits on its pin row (no jog staircase)
        spec = wired_spec(self.root)
        pins = {str(i): f'SIG{i}' for i in range(1, 9)}
        spec['parts'].append(part('J9', 'J', pins, footprint='Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical', page='p2'))
        spec['parts'].append(part('J10', 'J', pins, footprint='Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical', page='p1'))
        ps.generate_project(spec)
        for page in ('p1', 'p2'):
            labels = [l for l in self._labels(page) if l['name'].startswith('SIG')]
            self.assertEqual(len(labels), 8, page)
            for angle in (0.0, 180.0):          # the generic header has four pins per side: one port per pin row on each side
                ys = sorted(round(l['y'], 2) for l in labels if l['angle'] == angle)
                self.assertEqual(len(ys), 4, (page, angle))
                gaps = {round(b - a, 2) for a, b in zip(ys, ys[1:])}
                self.assertEqual(gaps, {2.54}, (page, angle, ys))

    def test_hanging_parts_with_long_values_do_not_overlap(self):
        spec = wired_spec(self.root)
        for i in range(4):
            spec['parts'].append(part(f'C{20 + i}', 'C', {'1': 'EN', '2': 'GND'}, TWO, value='0.47u/630V film'))
        ps.generate_project(spec)
        p1 = sm.measure_sheet(self.root / 'kicad/p1.kicad_sch')
        self.assertEqual(p1['text_overlaps'], 0)
        self.assertEqual(p1['isolated_symbols'], 0)

    def test_stale_continuation_sheets_are_removed_but_foreign_files_kept(self):
        kicad = self.root / 'kicad'
        kicad.mkdir(parents=True)
        (kicad / 'p1_2.kicad_sch').write_text('(kicad_sch (version 20250114) (generator "old"))\n', encoding='utf-8')
        (kicad / 'p1.kicad_sch').write_text('(kicad_sch (version 20250114) (generator "old"))\n', encoding='utf-8')
        (kicad / 'notes.kicad_sch').write_text('(kicad_sch (version 20250114) (generator "foreign"))\n', encoding='utf-8')
        result = ps.generate_project(wired_spec(self.root))
        self.assertEqual(result['removed_sheets'], ['p1_2.kicad_sch'])
        self.assertFalse((kicad / 'p1_2.kicad_sch').exists())
        self.assertTrue((kicad / 'notes.kicad_sch').exists())
        self.assertIn('(generator "aipe")', (kicad / 'p1.kicad_sch').read_text(encoding='utf-8'))
        legacy = ps.generate_project(wired_spec(self.root / 'legacy', presentation=None))
        self.assertEqual(legacy['removed_sheets'], [])

    def test_lone_test_points_form_a_grid_with_their_own_labels(self):
        # test points on a net that an anchor lane carries hang off that lane; test points on a net of their own (PROBE,
        # twelve pads) and on a ground rail have no lane and are drawn as a grid, each with its own marker
        spec = wired_spec(self.root)
        for i in range(12):
            spec['parts'].append(part(f'TP{i + 10}', 'TP', {'1': 'OUT' if i % 2 else 'PROBE'}, footprint='TestPoint:TestPoint_Pad_D2.0mm', page='p1'))
        spec['parts'].append(part('TP30', 'TP', {'1': 'GND'}, footprint='TestPoint:TestPoint_Pad_D2.0mm', page='p1'))
        result = ps.generate_project(spec)
        self.assertTrue(result['presentation']['guard']['identical'])
        labels = self._labels('p1')
        self.assertEqual(sum(1 for l in labels if l['name'] == 'PROBE'), 6, 'every PROBE test point carries its own tag')
        tree = parse((self.root / 'kicad/p1.kicad_sch').read_text(encoding='utf-8'))
        tps = [s for s in children(tree, 'symbol') if any(p[1] == 'Reference' and p[2].startswith('TP') for p in children(s, 'property'))]
        rows = {round(float(children(s, 'at')[0][2]), 1) for s in tps}
        self.assertGreaterEqual(len(rows), 2, 'test points wrap into rows (8 per row) and the ground one hangs from its own row')
        p1 = sm.measure_sheet(self.root / 'kicad/p1.kicad_sch')
        self.assertEqual(p1['isolated_symbols'], 0)

    def test_far_apart_cross_net_components_repeat_the_hierarchical_label(self):
        # OUT appears on p1 at U1 and, far away, at a second anchor in another group: the sheet carries two OUT ports
        spec = wired_spec(self.root, presentation=dict(supply='auto', max_cross_wire_mm=20.0,
                                                          groups={'U7': 'far', 'R8': 'far'}, group_titles={'far': 'Far group'}))
        spec['parts'].append(part('U7', 'IC', {'1': 'OUT', '2': 'GND', '3': 'VCC', '4': 'EN'},
                                  pin_defs('1:IN:input 2:GND:power_in 3:VCC:power_in 4:EN2:input'), footprint='Package_TO_SOT_SMD:SOT-23'))
        spec['parts'].append(part('R8', 'R', {'1': 'OUT', '2': 'GND'}, TWO))
        result = ps.generate_project(spec)
        self.assertTrue(result['presentation']['guard']['identical'])
        outs = [l for l in self._labels('p1') if l['name'] == 'OUT' and l['kind'] == 'hierarchical_label']
        self.assertGreaterEqual(len(outs), 2)
        self.assertEqual({l['shape'] for l in outs}, {'output'})
        root = parse((self.root / 'kicad/W.kicad_sch').read_text(encoding='utf-8'))
        p1_sheet = next(s for s in children(root, 'sheet') if any(p[2] == 'p1.kicad_sch' for p in children(s, 'property')))
        self.assertEqual(sum(1 for pin in children(p1_sheet, 'pin') if pin[1] == 'OUT'), 1, 'one sheet pin per net')

    def test_first_fit_columns_never_grow_under_a_neighbour(self):
        class L:
            def __init__(self, w, h, title):
                self.bbox, self.title = (0.0, 0.0, w, h), title
        # tall-narrow, tall-narrow, short-narrow, short-wide: FFD must not append the wide one into column 1 under column 2
        layouts = [L(60.0, 150.0, 'a'), L(60.0, 150.0, 'b'), L(60.0, 60.0, 'c'), L(250.0, 40.0, 'd')]
        positions = sp._pack_columns(layouts, 6.35, 45.0, 407.0, 267.0, True)
        self.assertIsNotNone(positions)
        rects = [(x, y, x + l.bbox[2], y + l.bbox[3]) for l, x, y in positions]
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                self.assertFalse(a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3], (a, b))

    def test_page_planner_tries_the_extras_variants_and_records_the_choice(self):
        result = ps.generate_project(wired_spec(self.root))
        for sheet in result['presentation']['sheets']:
            self.assertIn(sheet['counts']['layout_variant'], ('auto', 'below', 'beside'))


if __name__ == '__main__':
    unittest.main()
