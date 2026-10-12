"""Tests for automation.kicad_tools.schematic_wiring (sheet-grid wire router, normalisation, connectivity guard)."""
import unittest

from automation.kicad_tools import schematic_wiring as sw


def seg(net, a, b):
    return sw.Segment(net, a, b)


class GridRouterTests(unittest.TestCase):
    def test_straight_and_l_candidates_come_first(self):
        grid = sw.WireGrid(0, 0, 100, 100)
        path = grid.route('A', {sw.cell((10.16, 20.32)): None}, {sw.cell((50.8, 20.32))})
        self.assertEqual(path, [(10.16, 20.32), (50.8, 20.32)])
        path = grid.route('A', {sw.cell((10.16, 20.32)): None}, {sw.cell((50.8, 40.64))})
        self.assertEqual(len(path), 3)
        self.assertEqual((path[0], path[-1]), ((10.16, 20.32), (50.8, 40.64)))

    def test_detours_around_blocked_bodies_and_respects_pin_direction(self):
        grid = sw.WireGrid(0, 0, 100, 100)
        grid.block_rect(20.32, 10.16, 30.48, 40.64)
        path = grid.route('A', {sw.cell((10.16, 25.4)): [(-1, 0)]}, {sw.cell((40.64, 25.4))})
        self.assertIsNotNone(path)
        self.assertEqual(path[0], (10.16, 25.4))
        self.assertEqual(path[-1], (40.64, 25.4))
        self.assertLess(path[1][0], 10.16, 'first move must leave the pin to the left')
        for c in [sw.cell(p) for p in path]:
            self.assertNotIn(c, grid.blocked)

    def test_other_nets_are_crossed_straight_but_never_overlapped_or_touched(self):
        grid = sw.WireGrid(0, 0, 100, 100)
        grid.add_segment(seg('B', (30.48, 0), (30.48, 60.96)))      # vertical wall of net B
        grid.add_pin((30.48, 0), 'B')
        path = grid.route('A', {sw.cell((10.16, 20.32)): None}, {sw.cell((50.8, 20.32))})
        self.assertEqual(path, [(10.16, 20.32), (50.8, 20.32)], 'perpendicular crossing is allowed')
        # a wire end of B lies in the way at the same row: the router must not run through it
        grid2 = sw.WireGrid(0, 0, 100, 100)
        grid2.add_segment(seg('B', (30.48, 20.32), (30.48, 40.64)))
        path = grid2.route('A', {sw.cell((10.16, 20.32)): None}, {sw.cell((50.8, 20.32))})
        self.assertIsNotNone(path)
        self.assertNotIn(sw.cell((30.48, 20.32)), [sw.cell(p) for p in path])
        cells = set()
        for i in range(len(path) - 1):
            cells.update(sw.cells_between(path[i], path[i + 1]))
        self.assertNotIn(sw.cell((30.48, 20.32)), cells)
        # overlapping a parallel wire of another net is impossible
        grid3 = sw.WireGrid(0, 0, 40, 10)
        grid3.add_segment(seg('B', (0, 5.08), (38.1, 5.08)))
        for y in (0, 1.27, 2.54, 3.81, 6.35, 7.62, 8.89, 10.16):
            grid3.add_segment(seg('C', (0, y), (38.1, y)))
        self.assertIsNone(grid3.route('A', {sw.cell((2.54, 5.08)): None}, {sw.cell((35.56, 5.08))}))


class NormaliseTests(unittest.TestCase):
    def test_t_join_splits_the_spine_and_adds_one_junction(self):
        w = sw.SheetWiring()
        w.segments = [seg('N', (0, 0), (25.4, 0)), seg('N', (12.7, 0), (12.7, 12.7))]
        w.pins = {('R1', '1'): dict(point=(0, 0), net='N'), ('R2', '1'): dict(point=(12.7, 12.7), net='N'), ('R3', '1'): dict(point=(25.4, 0), net='N')}
        sw.normalise(w)
        self.assertEqual(sorted((s.a, s.b) for s in w.segments), [((0, 0), (12.7, 0)), ((12.7, 0), (12.7, 12.7)), ((12.7, 0), (25.4, 0))])
        self.assertEqual(w.junctions, [(12.7, 0)])
        self.assertEqual(w.problems, [])

    def test_collinear_corners_merge_and_other_net_contacts_are_problems(self):
        w = sw.SheetWiring()
        w.segments = [seg('N', (0, 0), (12.7, 0)), seg('N', (12.7, 0), (25.4, 0)), seg('M', (6.35, -5.08), (6.35, 0))]
        w.pins = {('R1', '1'): dict(point=(0, 0), net='N'), ('R2', '1'): dict(point=(25.4, 0), net='N'), ('R3', '1'): dict(point=(6.35, -5.08), net='M')}
        sw.normalise(w)
        self.assertEqual(len([s for s in w.segments if s.net == 'N']), 1, 'collinear N segments merge')
        self.assertTrue(any(p['kind'] == 'end_on_other_net' for p in w.problems))

    def test_trim_dangling_removes_only_free_stubs(self):
        w = sw.SheetWiring()
        w.segments = [seg('N', (0, 0), (12.7, 0)), seg('N', (12.7, 0), (12.7, 5.08)), seg('N', (12.7, 0), (20.32, 0))]
        w.pins = {('R1', '1'): dict(point=(0, 0), net='N'), ('R2', '1'): dict(point=(12.7, 5.08), net='N')}
        sw.normalise(w)
        removed = sw.trim_dangling(w)
        self.assertEqual(removed, 1)
        self.assertEqual(sorted((s.a, s.b) for s in w.segments), [((0, 0), (12.7, 0)), ((12.7, 0), (12.7, 5.08))])

    def test_crossings_count_perpendicular_pairs_of_different_nets(self):
        segments = [seg('A', (0, 5), (10, 5)), seg('B', (5, 0), (5, 10)), seg('A', (5, 0), (5, 10))]
        self.assertEqual(sw.crossings(segments), 1)


class ConnectivityTests(unittest.TestCase):
    def make(self):
        parts = [dict(ref='R1', nets={'1': 'A', '2': 'VCC'}), dict(ref='R2', nets={'1': 'A', '2': 'X'}),
                 dict(ref='R3', nets={'1': 'X', '2': 'GND'}), dict(ref='R4', nets={'1': 'X', '2': None})]
        sub = sw.SheetWiring()
        sub.segments = [seg('A', (0, 0), (10.16, 0)), seg('X', (20.32, 0), (30.48, 0)), seg('X', (25.4, 0), (25.4, 10.16)),
                        seg('X', (30.48, 0), (35.56, 0)), seg('VCC', (-5.08, 0), (-5.08, -5.08)), seg('GND', (40.64, 0), (40.64, 5.08))]
        sub.pins = {('R1', '1'): dict(point=(0, 0), net='A'), ('R1', '2'): dict(point=(-5.08, 0), net='VCC'),
                    ('R2', '1'): dict(point=(10.16, 0), net='A'), ('R2', '2'): dict(point=(20.32, 0), net='X'),
                    ('R3', '1'): dict(point=(30.48, 0), net='X'), ('R3', '2'): dict(point=(40.64, 0), net='GND'),
                    ('R4', '1'): dict(point=(25.4, 10.16), net='X'), ('R4', '2'): dict(point=(50.8, 0), net=None)}
        sub.labels = [dict(kind='global', name='A', point=(5.08, 0)), dict(kind='power', name='VCC', point=(-5.08, -5.08)),
                      dict(kind='power', name='GND', point=(40.64, 5.08)), dict(kind='hier', name='X', point=(35.56, 0))]
        sub.no_connects = [(50.8, 0)]
        sw.normalise(sub)
        root_pins = [dict(sheet='s1', name='X', point=(100, 100))]
        root_labels = [dict(name='X', point=(105.08, 100))]
        root = sw.SheetWiring()
        root.segments = [seg('X', (100, 100), (105.08, 100))]
        root.labels = [dict(kind='global', name='X', point=(105.08, 100)), dict(kind='sheetpin', name='X', point=(100, 100))]
        return parts, sub, root, root_pins, root_labels

    def test_geometry_reproduces_the_model_through_labels_power_values_and_sheet_pins(self):
        parts, sub, root, root_pins, root_labels = self.make()
        derived = sw.connectivity({'s1': sub, '_root': root}, root_pins, root_labels)
        report = sw.compare_with_model(derived, parts)
        self.assertTrue(report['identical'], report)
        self.assertEqual(derived['pads'][('R4', '1')], 'X')

    def test_missing_anchor_and_missing_junction_are_detected(self):
        parts, sub, root, root_pins, root_labels = self.make()
        sub.labels = [l for l in sub.labels if l['name'] != 'A']
        derived = sw.connectivity({'s1': sub, '_root': root}, root_pins, root_labels)
        report = sw.compare_with_model(derived, parts)
        self.assertFalse(report['identical'])
        self.assertTrue(any(u['expected'] == 'A' for u in report['unnamed']))
        parts, sub, root, root_pins, root_labels = self.make()
        sub.junctions = []        # the R4 stub ends on the interior of the X spine: not connected without a junction
        sub.segments = [seg('A', (0, 0), (10.16, 0)), seg('X', (20.32, 0), (35.56, 0)), seg('X', (25.4, 0), (25.4, 10.16)),
                        seg('VCC', (-5.08, 0), (-5.08, -5.08)), seg('GND', (40.64, 0), (40.64, 5.08))]
        derived = sw.connectivity({'s1': sub, '_root': root}, root_pins, root_labels)
        self.assertNotIn(('R4', '1'), derived['pads'])

    def test_label_of_another_net_on_a_wire_interior_is_a_problem_and_merges_the_nets(self):
        # KiCad 10 connects a label anywhere on a wire (adversarial case B): a Q label on the P wire merges P and Q
        parts = [dict(ref='RP1', nets={'2': 'P'}), dict(ref='RP2', nets={'1': 'P'}), dict(ref='RQ', nets={'1': 'Q', '2': 'Q'})]
        w = sw.SheetWiring()
        w.pins = {('RP1', '2'): dict(point=(43.81, 100.0), net='P'), ('RP2', '1'): dict(point=(96.19, 100.0), net='P'),
                  ('RQ', '1'): dict(point=(66.19, 120.0), net='Q'), ('RQ', '2'): dict(point=(73.81, 120.0), net='Q')}
        w.segments = [seg('P', (43.81, 100.0), (96.19, 100.0)), seg('P', (50.0, 100.0), (50.0, 95.0)),
                      seg('Q', (66.19, 120.0), (60.0, 120.0)), seg('Q', (73.81, 120.0), (80.0, 120.0))]
        w.labels = [dict(kind='global', name='P', point=(50.0, 95.0)), dict(kind='global', name='Q', point=(60.0, 120.0)),
                    dict(kind='global', name='Q', point=(80.0, 120.0)), dict(kind='global', name='Q', point=(70.0, 100.0))]
        sw.normalise(w)
        self.assertIn(dict(kind='label_on_other_net', net='Q', other='P', at=(70.0, 100.0)), w.problems)
        self.assertIn((70.0, 100.0), {s.a for s in w.segments} | {s.b for s in w.segments}, 'the P wire is split at the label')
        report = sw.compare_with_model(sw.connectivity({'s': w}, [], []), parts)
        self.assertFalse(report['identical'])
        self.assertTrue(report['multi_named'] and all(m['names'] == ['P', 'Q'] for m in report['multi_named']), report)
        self.assertTrue(any(p['kind'] == 'label_on_other_net' for p in report['problems']))
        # the same geometry without the stray label is sound (text labels also connect on an interior of their own net)
        w2 = sw.SheetWiring()
        w2.pins, w2.segments = dict(w.pins), [seg('P', (43.81, 100.0), (96.19, 100.0)), seg('P', (50.0, 100.0), (50.0, 95.0)),
                                             seg('Q', (66.19, 120.0), (60.0, 120.0)), seg('Q', (73.81, 120.0), (80.0, 120.0))]
        w2.labels = [dict(kind='global', name='P', point=(50.0, 95.0)), dict(kind='global', name='Q', point=(60.0, 120.0)),
                     dict(kind='global', name='Q', point=(80.0, 120.0)), dict(kind='global', name='P', point=(70.0, 100.0))]
        sw.normalise(w2)
        self.assertTrue(sw.compare_with_model(sw.connectivity({'s': w2}, [], []), parts)['identical'])

    def test_power_pin_on_a_wire_interior_does_not_connect(self):
        parts = [dict(ref='R1', nets={'1': 'S', '2': 'S'})]
        w = sw.SheetWiring()
        w.pins = {('R1', '1'): dict(point=(0.0, 0.0), net='S'), ('R1', '2'): dict(point=(20.0, 0.0), net='S')}
        w.segments = [seg('S', (0.0, 0.0), (20.0, 0.0))]
        w.labels = [dict(kind='power', name='VRAIL', point=(10.0, 0.0)), dict(kind='global', name='S', point=(20.0, 0.0))]
        sw.normalise(w)
        derived = sw.connectivity({'s': w}, [], [])
        self.assertEqual(derived['pads'][('R1', '1')], 'S', 'the power Value does not reach the wire')
        self.assertTrue(any(p['kind'] == 'label_dangling' and p['name'] == 'VRAIL' for p in derived['problems']))
        # on a wire end (same net) the power pin connects and the wire is a junction-free end
        w = sw.SheetWiring()
        w.pins = {('R1', '1'): dict(point=(0.0, 0.0), net='VRAIL'), ('R1', '2'): dict(point=(20.0, 0.0), net='VRAIL')}
        w.segments = [seg('VRAIL', (0.0, 0.0), (20.0, 0.0)), seg('VRAIL', (10.0, 0.0), (10.0, -5.0))]
        w.labels = [dict(kind='power', name='VRAIL', point=(10.0, -5.0))]
        sw.normalise(w)
        self.assertEqual(w.junctions, [(10.0, 0.0)])
        self.assertTrue(sw.compare_with_model(sw.connectivity({'s': w}, [], []), [dict(ref='R1', nets={'1': 'VRAIL', '2': 'VRAIL'})])['identical'])

    def test_unconnected_pins_need_a_no_connect_marker_and_nothing_else(self):
        parts, sub, root, root_pins, root_labels = self.make()
        sub.no_connects = []
        report = sw.compare_with_model(sw.connectivity({'s1': sub, '_root': root}, root_pins, root_labels), parts)
        self.assertFalse(report['identical'])
        self.assertEqual([d['kind'] for d in report['dangling']], ['nc_missing'])
        self.assertEqual(report['no_connects'], dict(expected=1, drawn=0))
        parts, sub, root, root_pins, root_labels = self.make()
        sub.segments.append(seg('X', (50.8, 0), (50.8, 5.08)))      # a wire reaches the no-connect pin
        sw.normalise(sub)
        report = sw.compare_with_model(sw.connectivity({'s1': sub, '_root': root}, root_pins, root_labels), parts)
        self.assertIn('nc_pin_connected', [d['kind'] for d in report['dangling']])

    def test_two_global_names_on_one_net_are_reported(self):
        parts, sub, root, root_pins, root_labels = self.make()
        sub.labels.append(dict(kind='global', name='OTHER', point=(0, 0)))
        derived = sw.connectivity({'s1': sub, '_root': root}, root_pins, root_labels)
        report = sw.compare_with_model(derived, parts)
        self.assertFalse(report['identical'])
        self.assertTrue(report['multi_named'])


if __name__ == '__main__':
    unittest.main()
