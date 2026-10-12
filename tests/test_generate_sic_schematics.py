"""Tests for automation.kicad_tools.generate_sic_schematics (V2 KiCad projects of the SiC buck).

Pure-Python checks always run: net-class assignment of both board models, the class-pair clearance
logic, pin-field exceptions from pad geometry (including rotated pads), the design-rule text, the
project specs and the merged BOM.  Generation, parsing of the written KiCad files, the mapping files,
determinism and native kicad-cli ERC need KiCad 10 and its footprint library; they skip cleanly when
KiCad is missing - a skip is never a pass, the recorded evidence lives under
examples/sic-buck-400v-200v-5kw/verification/erc.
"""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from automation.kicad_tools import generate_sic_schematics as g
from automation.kicad_tools import project_footprints as pf
from automation.kicad_tools import project_schematic as ps
from automation.kicad_tools import sic_buck_common as common
from automation.kicad_tools import sic_buck_power_model as power_model
from automation.kicad_tools.native_schematic import children, parse
from automation.setup.detect_kicad import find_kicad_cli


def kicad_cli():
    try:
        return find_kicad_cli()
    except FileNotFoundError:
        return None


def library_installed():
    return pf.footprint_available('Package_TO_SOT_THT', 'TO-247-4_Vertical')


def pad(number, x, y, w, h):
    return dict(number=number, type='smd', shape='rect', at=[x, y], size=[w, h])


# Pad geometry of a few footprints (KiCad 10.0.7 values) so the rule logic is testable without the library.
TO247_4 = [dict(number=str(i + 1), type='thru_hole', shape='oval', at=[x, 0.0], size=[1.905, 4.5]) for i, x in enumerate((0.0, 5.08, 7.62, 10.16))]
R1206 = [pad('1', -1.4, 0, 1.0, 1.75), pad('2', 1.4, 0, 1.0, 1.75)]
R2512 = [pad('1', -2.9625, 0, 1.225, 3.35), pad('2', 2.9625, 0, 1.225, 3.35)]
SOIC16W = [pad(str(i + 1), -4.65, -4.445 + 1.27 * i, 2.05, 0.6) for i in range(8)] + [pad(str(16 - i), 4.65, -4.445 + 1.27 * i, 2.05, 0.6) for i in range(8)]
ROTATED = '''(footprint "Rot" (version 20260206) (generator "test") (layer "F.Cu")
  (pad "1" smd rect (at -1.7 -0.975 270) (size 0.3 1.6) (layers "F.Cu" "F.Paste" "F.Mask"))
  (pad "2" smd rect (at -1.7 -0.325 270) (size 0.3 1.6) (layers "F.Cu" "F.Paste" "F.Mask"))
  (pad "" np_thru_hole circle (at 0 0) (size 1 1) (drill 1) (layers "*.Cu" "*.Mask")))'''


class NetClassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = {board: g.build_parts(board) for board in g.BOARDS}

    def test_wildcard_match_is_anchored_and_case_sensitive(self):
        self.assertTrue(g.wildcard_match('VIN', 'VIN'))
        self.assertFalse(g.wildcard_match('VIN', 'VIN_RAW'))
        self.assertTrue(g.wildcard_match('HS_*', 'HS_OUTH'))
        self.assertFalse(g.wildcard_match('HS_*', 'LS_OUTH'))
        self.assertTrue(g.wildcard_match('DESAT_H_*', 'DESAT_H_OC'))
        self.assertFalse(g.wildcard_match('vin', 'VIN'))
        self.assertTrue(g.wildcard_match('VIN_DIV_T?', 'VIN_DIV_T1'))

    def test_power_board_nets_each_belong_to_exactly_one_baseline_class(self):
        classes, assignment = g.board_net_classes('power', self.parts['power'])
        names = [c['name'] for c in classes]
        self.assertEqual(names, ['Default', 'HV_VIN', 'HV_SW', 'HV_PGND', 'HV_VOUT', 'DRV_HS', 'DRV_LS', 'DESAT_HS', 'DESAT_LS',
                                 'SENSE_ISO', 'PGND_LV', 'PE', 'CTRL_SELV'])
        self.assertEqual(set(assignment), set(g.net_names(self.parts['power'])))
        expected = {'VIN_RAW': 'HV_VIN', 'VIN': 'HV_VIN', 'BLD_IN_1': 'HV_VIN', 'IND_IN_3': 'PGND_LV', 'DAMP_MID': 'HV_VIN', 'VIN_DIV_T1': 'HV_VIN',
                    'SW': 'HV_SW', 'SNUB_MID': 'HV_SW', 'PGND': 'HV_PGND', 'PE_REF_MID': 'HV_PGND', 'VOUT': 'HV_VOUT', 'VOUT_L': 'HV_VOUT',
                    'BLD_OUT_1': 'HV_VOUT', 'VOUT_DIV_T1': 'HV_VOUT', 'G_H': 'DRV_HS', 'KS_H': 'DRV_HS', 'HS_OUTH': 'DRV_HS', 'VEE_L': 'DRV_LS',
                    'DESAT_H_A': 'DESAT_HS', 'DESAT_L_OC': 'DESAT_LS', 'VIN_DIV': 'SENSE_ISO', 'VOUT_DIV': 'SENSE_ISO', '5V_ISO': 'SENSE_ISO',
                    'ISO_15V': 'SENSE_ISO', 'PE': 'PE', '12V_PROT': 'CTRL_SELV', 'GND_CTRL': 'CTRL_SELV', '3V3': 'CTRL_SELV', 'PWM_H_F': 'CTRL_SELV',
                    '12V_BIAS_H': 'CTRL_SELV', 'GNDP_S': 'CTRL_SELV', 'K1_LOW': 'CTRL_SELV'}
        for net, name in expected.items():
            self.assertEqual(assignment[net], name, net)
        for net in power_model.HV_INTERMEDIATE_NETS:
            self.assertIn(assignment[net], g.HV_CLASSES + ('PGND_LV',), net)  # LED anode nodes are the PGND_LV island class
        for pin in range(1, 51):
            self.assertEqual(assignment[common.mezzanine_net(str(pin))], 'CTRL_SELV', pin)
        clearance = g.class_clearances(classes)
        self.assertEqual(clearance['HV_VIN'], 3.0)
        self.assertEqual(clearance['DRV_HS'], 0.3)
        self.assertEqual(clearance['PE'], 5.0)
        self.assertEqual(clearance['CTRL_SELV'], 0.25)
        self.assertEqual(clearance['Default'], 0.25)
        self.assertEqual([c for c in classes if c['name'] == 'Default'][0]['nets'], [])

    def test_control_board_is_entirely_selv(self):
        classes, assignment = g.board_net_classes('control', self.parts['control'])
        names = {c['name'] for c in classes}
        self.assertTrue({'Default', 'CTRL_SELV', 'CTRL_PWR'} <= names)
        self.assertTrue(set(common.NET_CLASS_PATTERNS) <= names)
        self.assertEqual(set(assignment.values()), {'CTRL_SELV', 'CTRL_PWR'})
        for net in ('12V_IN', '12V_PROT', 'EFUSE_RTN', '5V', '3V3', '1V9', 'GND_CTRL'):
            self.assertEqual(assignment[net], 'CTRL_PWR', net)
        for net in ('PWM_H', 'FAULT_N', 'VIN_SENSE', 'EPWM1A', 'XRS_N'):
            self.assertEqual(assignment[net], 'CTRL_SELV', net)
        for c in classes:
            if c['name'] in common.NET_CLASS_PATTERNS:
                self.assertEqual(c['nets'], common.NET_CLASS_PATTERNS[c['name']])
        self.assertEqual(g.class_clearances(classes)['Default'], 0.2)
        with self.assertRaises(ValueError):
            g.board_net_classes('control', self.parts['control'] + [dict(ref='X1', nets={'1': 'VIN', '2': 'GND_CTRL'})])

    def test_required_clearance_follows_the_baseline_rules(self):
        clearance = g.class_clearances(g.board_net_classes('power', self.parts['power'])[0])
        cases = {('HV_VIN', 'CTRL_SELV'): 9.0, ('DRV_HS', 'Default'): 9.0, ('SENSE_ISO', 'CTRL_SELV'): 9.0, ('HV_VIN', 'PE'): 5.0,
                 ('HV_PGND', 'PE'): 5.0, ('HV_SW', 'DRV_HS'): 0.3, ('HV_SW', 'DESAT_HS'): 0.3, ('HV_PGND', 'SENSE_ISO'): 0.3,
                 ('HV_PGND', 'DRV_LS'): 0.3, ('HV_VIN', 'HV_SW'): 3.0, ('DRV_HS', 'DRV_LS'): 3.0, ('HV_VIN', 'DRV_HS'): 3.0,
                 ('SENSE_ISO', 'HV_VIN'): 3.0, ('DRV_HS', 'DESAT_HS'): 0.3, ('HV_VIN', 'HV_VIN'): 3.0, ('CTRL_SELV', 'CTRL_SELV'): 0.25,
                 ('PE', 'CTRL_SELV'): 5.0}
        for (a, b), value in cases.items():
            self.assertEqual(g.required_clearance(a, b, clearance), value, (a, b))
            self.assertEqual(g.required_clearance(b, a, clearance), value, (b, a))

    def test_pin_field_exceptions_come_from_pad_geometry(self):
        classes, assignment = g.board_net_classes('power', self.parts['power'])
        clearance = g.class_clearances(classes)
        parts = [dict(ref='Q1', footprint='Q', nets={'1': 'VIN', '2': 'SW', '3': 'KS_H', '4': 'G_H'}),
                 dict(ref='R4', footprint='R1206', nets={'1': 'VIN', '2': 'IND_IN_1'}),
                 dict(ref='R14', footprint='R2512', nets={'1': 'PGND', '2': 'PE'}),
                 dict(ref='R99', footprint='R2512', nets={'1': 'VIN', '2': 'PGND'}),
                 dict(ref='U1', footprint='SOIC', nets={**{str(n): 'KS_H' for n in range(1, 9)}, **{str(n): 'GND_CTRL' for n in range(9, 17)}})]
        geometry = {'Q': TO247_4, 'R1206': R1206, 'R2512': R2512, 'SOIC': SOIC16W}
        records = g.pin_field_exceptions(parts, geometry, assignment, clearance)
        by_ref = {(r['ref'], tuple(r['classes'])): r for r in records}
        self.assertNotIn('Q1', {r['ref'] for r in records}, 'VIN-SW pads are 3.175 mm apart and SW-KS_H is a same-island pair')
        self.assertNotIn('R99', {r['ref'] for r in records}, '2512 pads at 4.7 mm satisfy the 3.0 mm HV rule')
        r4 = by_ref[('R4', ('HV_VIN', 'HV_VIN'))]
        self.assertEqual((r4['kind'], r4['required_mm'], r4['clearance_mm']), ('hv', 3.0, 1.79))
        self.assertAlmostEqual(r4['min_gap_mm'], 1.8)
        r14 = by_ref[('R14', ('HV_PGND', 'PE'))]
        self.assertEqual((r14['kind'], r14['required_mm'], r14['clearance_mm']), ('hv', 5.0, 4.69))
        u1 = by_ref[('U1', ('CTRL_SELV', 'DRV_HS'))]
        # 8 x 8 cross pairs, of which only those with |row offset| <= 4 are closer than 9 mm: 8 + 2 x (7 + 6 + 5 + 4) = 52
        self.assertEqual((u1['kind'], u1['required_mm'], u1['clearance_mm'], u1['pad_pairs']), ('barrier', 9.0, 7.24, 52))
        self.assertAlmostEqual(g.pad_gap(*R1206), 1.8)
        self.assertAlmostEqual(g.pad_gap(TO247_4[0], TO247_4[1]), 3.175)
        self.assertAlmostEqual(g.pad_gap(TO247_4[1], TO247_4[2]), 0.635)
        self.assertEqual(g.exception_clearance(0.635), 0.62)
        self.assertEqual(g.exception_clearance(0.05), 0.1)
        rule = g.exception_rule(r14)
        self.assertIn("A.memberOfFootprint('R14') && B.intersectsCourtyard('R14')", rule)
        self.assertIn("(min 4.69mm)", rule)

    def test_pad_records_account_for_rotation(self):
        records = g.pad_records(ROTATED)
        self.assertEqual([r['number'] for r in records], ['1', '2'], 'unnumbered holes are not electrical pads')
        self.assertEqual(records[0]['size'], [1.6, 0.3])
        self.assertAlmostEqual(g.pad_gap(*records), 0.35)

    def test_design_rules_text_orders_rules_and_parses(self):
        exceptions = [dict(ref='R4', classes=['HV_VIN', 'HV_VIN'], clearance_mm=1.79, kind='hv'),
                      dict(ref='U1', classes=['CTRL_SELV', 'DRV_HS'], clearance_mm=7.24, kind='barrier')]
        text = g.design_rules_text('power', exceptions, ['basis line', common.BANNER])
        ps.normalise_dru(text)
        self.assertTrue(text.startswith('(version 1)\n# basis line\n# ' + common.BANNER))
        order = [text.index(key) for key in ('HV functional clearance (inner layers)', 'HV functional clearance (outer layers)',
                                              'Same reference island', 'HV side to PE', 'HV side to CTRL_SELV (all layers)',
                                              'HV side to board edge', 'pin field R4', 'pin field U1')]
        self.assertEqual(order, sorted(order))
        self.assertIn('(constraint clearance (min 9mm))', text)
        self.assertIn('(constraint clearance (min 5mm))', text)
        self.assertIn('(layer inner)\n  (condition', text)
        self.assertIn('(constraint edge_clearance (min 1mm))', text)
        self.assertIn("B.NetClass == 'Default'", text, 'unclassed nets are treated as SELV')
        self.assertIn("A.NetClass == 'HV_SW') && (B.NetClass == 'DRV_HS' || B.NetClass == 'DESAT_HS'", text)
        control = g.design_rules_text('control', [], [])
        ps.normalise_dru(control)
        self.assertIn('guards only', control)
        self.assertNotIn('pin field', control)

    def test_specs_coerce_for_both_boards(self):
        for board in g.BOARDS:
            with self.subTest(board=board):
                spec, assignment = g.build_spec(board, self.parts[board], Path('x/kicad'), Path('x/design'), exceptions=[])
                coerced = ps.coerce_spec(spec)
                self.assertEqual(coerced.name, g.project_name(board))
                self.assertEqual(coerced.revision, common.GENERATION)
                self.assertEqual(coerced.comment, common.BANNER)
                self.assertIn(common.BASIS, coerced.title)
                self.assertEqual(coerced.pages, {str(k): str(v) for k, v in g.board_model(board).PAGES.items()})
                self.assertEqual(coerced.flag_nets, list(g.board_model(board).FLAG_NETS))
                self.assertIn(coerced.flag_page, coerced.pages)
                self.assertEqual(coerced.mapping_name, f'schematic_mapping_{board}.json')
                self.assertEqual(coerced.paper, 'A3')
                self.assertTrue(set(coerced.page_notes) <= set(coerced.pages))
                self.assertTrue(any('design_decisions.json' in line for line in coerced.header_lines))
                self.assertEqual(coerced.design_rules['min_clearance'], g.SELV_CLEARANCE[board])
                report = ps.analyse_connectivity(coerced.parts, coerced.flag_nets)
                self.assertEqual(report['pin_conflicts'], [])
                self.assertEqual(report['undriven_power_nets'], [])
        self.assertEqual(g.flag_page('power'), power_model.FLAG_PAGE)
        self.assertEqual(g.flag_page('control'), '01_aux_12v')

    def test_presentation_policy_and_style_switch(self):
        self.assertIsNone(g.presentation_for('control', 'legacy'))
        with self.assertRaises(ValueError):
            g.presentation_for('control', 'fancy')
        circuit = g.build_circuit('control')
        wired = g.presentation_for('control', 'wired', circuit)
        self.assertEqual(wired['style'], 'wired')
        self.assertEqual(wired['supply'], 'auto')
        self.assertIn('5V_SW', wired['exclude_supply'])
        self.assertEqual(wired['groups']['U2'], 'buck_5v')
        self.assertIn('buck_5v', wired['group_titles'])
        self.assertEqual(circuit.parts, g.build_parts('control'), 'blocks are presentation metadata only')
        power = g.build_circuit('power')
        self.assertEqual(power.groups['U1'], 'driver_h')
        self.assertEqual(power.groups['U3'], 'driver_l')
        self.assertTrue(power.groups['U2'].startswith('bias_'))
        legacy, _ = g.build_spec('control', self.parts['control'], Path('x/kicad'), Path('x/design'), exceptions=[], style='legacy')
        self.assertIsNone(ps.coerce_spec(legacy).presentation)
        spec, _ = g.build_spec('control', self.parts['control'], Path('x/kicad'), Path('x/design'), exceptions=[], style='wired', circuit=circuit)
        self.assertEqual(ps.coerce_spec(spec).presentation['groups'], circuit.groups)

    def test_merged_bom_carries_a_board_column(self):
        for path in g.BOM_SOURCES.values():
            if not Path(path).is_file():
                self.skipTest(f'{path} not written')
        with tempfile.TemporaryDirectory(prefix='aipe_bom_') as temp:
            target = Path(temp) / 'bom.csv'
            summary = g.write_merged_bom(target)
            with target.open(encoding='utf-8', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(list(rows[0]), g.BOM_FIELDS)
            self.assertEqual(len(rows), summary['rows'])
            self.assertEqual({r['board'] for r in rows}, set(g.BOARDS))
            self.assertEqual(summary['per_board']['power'], len(self.parts['power']))
            self.assertEqual(summary['per_board']['control'], len(self.parts['control']))
            self.assertEqual(sum(1 for r in rows if r['dnp'] == 'yes'), summary['dnp'])


@unittest.skipUnless(kicad_cli() and library_installed(), 'KiCad 10 with its footprint library is required')
class GenerationLabelTests(unittest.TestCase):
    """One generation label (sic_buck_common.GENERATION) for everything the V2.1 generators write."""

    def test_banner_is_derived_from_the_generation_label(self):
        self.assertEqual(common.GENERATION, "V2.1")
        self.assertEqual(common.BANNER, f"AI-GENERATED ENGINEERING PROTOTYPE - {common.GENERATION} - HUMAN REVIEW REQUIRED")
        self.assertEqual(g.REVISION, common.GENERATION)
        self.assertEqual(power_model.COMMENT, common.BANNER)
        for text in g.NOTICE_TEXT.values():
            self.assertTrue(text.endswith(common.BANNER + "."), text[-90:])
        self.assertTrue(any(common.BANNER in line for line in g.header_lines("power", {}, [])))

    def test_board_generators_share_the_label(self):
        from automation.kicad_tools import generate_sic_control_board as cb
        from automation.kicad_tools import generate_sic_power_board as pb
        for module in (cb, pb):
            self.assertEqual(module.REVISION, common.GENERATION, module.__name__)
            self.assertEqual(module.BANNER, common.BANNER, module.__name__)
        silk = [item[0] for item in pb.SILKSCREEN]
        self.assertIn(common.BANNER, silk)
        self.assertIn(f"AIPE SiC BUCK 400V -> 200V / 5kW - POWER BOARD {common.GENERATION}", silk)
        for cid in ("A", "B"):
            candidate = json.loads(cb.candidate_path(cid).read_text(encoding="utf-8"))
            label = f"AIPE SiC BUCK CONTROL {common.GENERATION}"
            self.assertIn(label, [item["text"] for item in candidate["silkscreen"]], cid)
            # the placer keeps auto-placed parts off cb.text_box(label), which depends on the character count only: the label must
            # keep the 26 characters of the V2 label "AIPE SiC BUCK CONTROL - V2" or C49 moves and the control routing changes
            self.assertEqual(len(label), len("AIPE SiC BUCK CONTROL - V2"))


class GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='aipe_sic_')
        cls.root = Path(cls.temp.name)
        cls.results = {}
        for board in g.BOARDS:
            cls.results[board] = g.generate(board, cls.root / 'kicad' / f'{board}_board', cls.root / 'design')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_generated_files_parse_and_mapping_records_the_generation(self):
        for board, result in self.results.items():
            with self.subTest(board=board):
                kicad = self.root / 'kicad' / f'{board}_board'
                name = g.project_name(board)
                root = parse((kicad / f'{name}.kicad_sch').read_text(encoding='utf-8'))
                self.assertEqual(root[0], 'kicad_sch')
                self.assertEqual(len(children(root, 'sheet')), len(result['sheets']))
                for sheet in result['sheets']:
                    tree = parse((kicad / sheet['file']).read_text(encoding='utf-8'))
                    self.assertEqual(tree[0], 'kicad_sch')
                parse((kicad / 'libraries' / 'AIPE.kicad_sym').read_text(encoding='utf-8'))
                project = json.loads((kicad / f'{name}.kicad_pro').read_text(encoding='utf-8'))
                self.assertIn('CTRL_SELV', [c['name'] for c in project['net_settings']['classes']])
                self.assertTrue(project['net_settings']['netclass_patterns'])
                dru = (kicad / f'{name}.kicad_dru').read_text(encoding='utf-8')
                self.assertTrue(dru.startswith('(version 1)'))
                self.assertIn('HV side to CTRL_SELV (all layers)', dru)
                for file in ('fp-lib-table', 'sym-lib-table'):
                    self.assertTrue((kicad / file).is_file(), file)
                self.assertEqual(result['skipped'], {})
                self.assertEqual(result['parts_placed'], len(g.build_parts(board)))
                mapping_path = self.root / 'design' / f'schematic_mapping_{board}.json'
                self.assertTrue(mapping_path.is_file())
                mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
                self.assertEqual(set(mapping['paths']), {p['ref'] for p in g.build_parts(board)})
                generation = mapping['generation']
                self.assertEqual(generation['board'], board)
                self.assertEqual(generation['banner'], common.BANNER)
                self.assertEqual(generation['parts'], len(g.build_parts(board)))
                self.assertEqual(generation['precheck']['pin_conflicts'], [])
                self.assertTrue(all(r['kind'] in ('barrier', 'hv', 'pitch') for r in generation['pin_field_exceptions']))
        self.assertTrue((self.root / 'kicad/power_board/libraries/AIPE.pretty').is_dir())
        self.assertEqual(self.results['control']['generation']['libraries']['custom'], [])
        power_exceptions = self.results['power']['generation']['pin_field_exceptions']
        self.assertTrue(any(r['ref'] == 'U1' and r['kind'] == 'barrier' for r in power_exceptions))
        self.assertFalse(any(r['ref'] in ('Q1', 'Q2') for r in power_exceptions))

    def test_native_erc_has_zero_findings(self):
        for board in g.BOARDS:
            with self.subTest(board=board):
                manifest = g.run_erc(board, self.root / 'kicad' / f'{board}_board', self.root / 'erc')
                self.assertEqual(manifest['status'], 'passed', manifest.get('details'))
                self.assertEqual(manifest['finding_count'], 0, manifest.get('details'))
                self.assertEqual(manifest['tool_exit_code'], 0)

    def test_wired_gates_pass_and_legacy_style_stays_available(self):
        for board in g.BOARDS:
            with self.subTest(board=board):
                gates = g.verify_wired(board, self.root / 'kicad' / f'{board}_board', self.root / 'gates' / board)
                self.assertTrue(gates['gates']['dru_identical']['passed'], gates['gates']['dru_identical'])
                self.assertTrue(gates['gates']['net_settings_equal']['passed'])
                self.assertTrue(gates['gates']['erc_zero']['passed'], gates['gates']['erc_zero'].get('details'))
                self.assertTrue(gates['gates']['netlist_vs_model']['passed'], gates['gates']['netlist_vs_model'])
                self.assertTrue(gates['gates']['netlist_vs_v2']['passed'], gates['gates']['netlist_vs_v2'])
                self.assertEqual(gates['gates']['erc_zero']['finding_types'], {})
                fill = gates['gates']['paper_fill']
                self.assertTrue(fill['passed'], fill)
                self.assertTrue(all(e['fill'] >= fill['min_fill'] for e in fill['escalated']), fill['escalated'])
                self.assertTrue(gates['passed'])
                mapping = json.loads((self.root / 'design' / f'schematic_mapping_{board}.json').read_text(encoding='utf-8'))
                self.assertEqual(mapping['generation']['style'], 'wired')
                exceptions = mapping['presentation']['exceptions']      # label fallbacks: budgeted and every one listed
                self.assertLessEqual(len(exceptions), 4, exceptions)
                self.assertTrue(all(e['reason'] == 'no_wire_path' and e['net'] and e['sheet'] for e in exceptions), exceptions)
                self.assertTrue(mapping['presentation']['guard']['identical'])
                self.assertEqual(self.results[board]['continuation_sheets'], [])
        legacy = self.root / 'legacy'
        result = g.generate('control', legacy / 'kicad', legacy / 'design', style='legacy')
        self.assertIn('06_pwm_fault_logic_2', result['continuation_sheets'])
        self.assertNotIn('presentation', result)

    def test_generation_is_deterministic(self):
        again = self.root / 'again'
        g.generate('power', again / 'kicad', again / 'design')
        first = self.root / 'kicad/power_board'
        for path in sorted(first.rglob('*')):
            if path.is_file():
                other = again / 'kicad' / path.relative_to(first)
                self.assertEqual(path.read_bytes(), other.read_bytes(), path.name)


if __name__ == '__main__':
    unittest.main()
