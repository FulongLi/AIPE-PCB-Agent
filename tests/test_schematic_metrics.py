"""Tests for automation.kicad_tools.schematic_metrics (one readability definition for V2 and V2.1 sheets)."""
import tempfile
import unittest
from pathlib import Path

from automation.kicad_tools import project_schematic as ps
from automation.kicad_tools import schematic_metrics as sm
from tests.test_schematic_presentation import wired_spec


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aipe_metrics_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_legacy_sheets_are_all_stub_labels_and_wired_sheets_are_not(self):
        ps.generate_project(wired_spec(self.root / 'legacy', presentation=None))
        legacy = sm.measure_project(self.root / 'legacy/kicad')
        totals = legacy['totals']
        self.assertEqual(totals['junctions'], 0)
        self.assertEqual(totals['hierarchical_labels'], 0)
        self.assertEqual(totals['global_labels_on_pin_stubs'], totals['connected_pins'])
        self.assertEqual(totals['wired_pins'], 0)
        self.assertEqual(totals['wired_pin_share'], 0.0)
        self.assertEqual(totals['dangling_wire_ends'], 0)
        self.assertEqual(totals['off_grid_points'], 0)
        ps.generate_project(wired_spec(self.root / 'wired'))
        wired = sm.measure_project(self.root / 'wired/kicad')
        totals = wired['totals']
        self.assertEqual(totals['global_labels_on_pin_stubs'], 0)
        self.assertGreater(totals['junctions'], 0)
        self.assertGreater(totals['hierarchical_labels'], 0)
        self.assertEqual(totals['sheet_pins'], 6)
        self.assertGreaterEqual(totals['wired_pin_share'], 0.6)
        self.assertEqual(totals['continuation_sheets'], 0)
        self.assertEqual(totals['dangling_wire_ends'], 0)
        self.assertEqual(totals['isolated_symbols'], 0)
        self.assertEqual(totals['off_grid_points'], 0)
        self.assertEqual(totals['symbols'], 14)
        root = next(s for s in wired['sheets'] if s['root'])
        self.assertEqual(root['global_labels'], 6)

    def test_sheet_pin_names_count_as_text_and_fill_is_reported(self):
        root = self.root / 'kicad'
        root.mkdir(parents=True)
        sheet = ps.Schematic('T', 'root', 'A4')
        # a sheet with one left and one right pin, a stub wire and the global anchor at each stub end (V2.1 root pattern)
        sheet.items.append('''(sheet (at 50.8 50.8) (size 50.8 25.4) (stroke (width 0.254) (type default))
            (fill (color 0 0 0 0)) (uuid "00000000-0000-0000-0000-000000000001")
            (property "Sheetname" "sub" (at 50.8 49.53 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
            (property "Sheetfile" "sub.kicad_sch" (at 50.8 77.47 0) (effects (font (size 1.0 1.0)) (justify left top)))
            (pin "LEFT_PORT_NAME" input (at 50.8 55.88 180) (effects (font (size 1.27 1.27)) (justify left)) (uuid "00000000-0000-0000-0000-000000000002"))
            (pin "RIGHT_PORT_NAME" output (at 101.6 55.88 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid "00000000-0000-0000-0000-000000000003"))
            (instances (project "T" (path "/00000000-0000-0000-0000-000000000000" (page "2")))))''')
        sheet.wire((50.8, 55.88), (45.72, 55.88))
        sheet.global_label('LEFT_PORT_NAME', (45.72, 55.88), 180, size=1.27)
        sheet.wire((101.6, 55.88), (106.68, 55.88))
        sheet.global_label('RIGHT_PORT_NAME', (106.68, 55.88), 0, size=1.27)
        sheet.write(root / 'T.kicad_sch')
        good = sm.measure_sheet(root / 'T.kicad_sch')
        self.assertEqual(good['sheet_pins'], 2)
        self.assertEqual(good['text_overlaps'], 0, 'names inside the sheet, anchors outside')
        self.assertIsNotNone(good['paper_fill'])
        self.assertGreater(good['paper_fill'], 0.0)
        # the inverted justify (text drawn outward, over the anchor) is counted
        text = (root / 'T.kicad_sch').read_text(encoding='utf-8')
        text = text.replace('(at 50.8 55.88 180) (effects (font (size 1.27 1.27)) (justify left))', '(at 50.8 55.88 180) (effects (font (size 1.27 1.27)) (justify right))')
        text = text.replace('(at 101.6 55.88 0) (effects (font (size 1.27 1.27)) (justify right))', '(at 101.6 55.88 0) (effects (font (size 1.27 1.27)) (justify left))')
        (root / 'bad.kicad_sch').write_text(text, encoding='utf-8')
        self.assertEqual(sm.measure_sheet(root / 'bad.kicad_sch')['text_overlaps'], 2)

    def test_text_boxes_and_crossings(self):
        a = sm.text_box(0, 0, 'ABCD', 1.0, 'left')
        b = sm.text_box(1.0, 0, 'XY', 1.0, 'left')
        self.assertTrue(sm.boxes_overlap(a, b))
        self.assertFalse(sm.boxes_overlap(a, sm.text_box(20, 0, 'XY', 1.0, 'left')))
        self.assertTrue(sm.on_grid(1.27 * 7))
        self.assertFalse(sm.on_grid(1.0))

    def test_compare_projects_folds_continuation_sheets_and_writes_markdown(self):
        ps.generate_project(wired_spec(self.root / 'legacy', presentation=None))
        ps.generate_project(wired_spec(self.root / 'wired'))
        result = sm.compare_projects(self.root / 'legacy/kicad', self.root / 'wired/kicad', before_root='W', after_root='W',
                                     mapping=self.root / 'wired/design/schematic_mapping.json')
        self.assertEqual(result['labels'], ['V2', 'V2.1'])
        self.assertEqual(set(result['pages']), {'p1', 'p2', 'root'})
        self.assertGreater(result['totals']['V2']['global_labels_on_pin_stubs'], 0)
        self.assertEqual(result['totals']['V2.1']['global_labels_on_pin_stubs'], 0)
        self.assertLess(result['delta']['global_labels_on_pin_stubs'], 0)
        self.assertIsNotNone(result['planner'])
        self.assertIn('p1', result['planner']['sheets'])
        self.assertIn('label_fallbacks', result['planner']['totals'])
        self.assertEqual(sm.page_key('06_pwm_fault_logic_2.kicad_sch'), '06_pwm_fault_logic')
        md = sm.comparison_markdown(result, 'test')
        self.assertIn('| wired_pin_share |', md)
        self.assertIn('| p1 |', md)
        self.assertIn('single_global_label', md)


if __name__ == '__main__':
    unittest.main()
