"""Tests for the V2 pipeline smoke driver (automation.kicad_tools.v2_pipeline_smoke).

The model, design-rule generation, zone coverage, routing plan and evidence layout are checked with the
host interpreter alone. The end-to-end class needs kicad-cli, the installed KiCad footprint library and
KiCad's bundled Python with pcbnew; it skips cleanly when any of them is missing. A skip is never a pass
and does not replace the recorded smoke run under examples/.../verification/environment.
"""

import json
import tempfile
import unittest
from pathlib import Path

from automation.kicad_tools import grid_router as gr
from automation.kicad_tools import project_footprints as pf
from automation.kicad_tools import project_schematic as ps
from automation.kicad_tools import v2_pipeline_smoke as sm
from automation.setup.detect_kicad import find_kicad_cli


def kicad_cli():
    try:
        return find_kicad_cli()
    except FileNotFoundError:
        return None


def library_installed():
    return pf.footprint_available('Package_TO_SOT_THT', 'TO-247-4_Vertical')


# Pad geometry of the two official footprints that matter for the design rules (KiCad 10.0.7 values).
FAKE_GEOMETRY = {
    'Package_TO_SOT_THT:TO-247-4_Vertical': [dict(number=str(i + 1), at=[x, 0.0], size=[1.905, 4.5]) for i, x in enumerate((0.0, 5.08, 7.62, 10.16))],
    'Capacitor_SMD:C_2220_5750Metric': [dict(number='1', at=[-2.55, 0.0], size=[1.8, 5.4]), dict(number='2', at=[2.55, 0.0], size=[1.8, 5.4])],
}
# Placed pad centres the zone polygons must reach (from the deterministic PLACEMENT table).
SAMPLE_PADS = {('Q1', '4'): [(56.16, 36.0)], ('Q1', '2'): [(51.08, 36.0)], ('Q1', '3'): [(53.62, 36.0)], ('Q2', '2'): [(27.08, 36.0)],
               ('C1', '1'): [(50.0, 42.45)], ('C2', '1'): [(57.0, 42.45)], ('L1', '1'): [(75.0, 26.0)], ('L1', '2'): [(105.0, 26.0)],
               ('C4', '1'): [(110.75, 56.9), (110.75, 67.1)]}


class ModelTests(unittest.TestCase):
    def test_parts_follow_the_shared_format_and_split_by_board(self):
        parts = sm.build_parts()
        refs = [p['ref'] for p in parts]
        self.assertEqual(len(refs), len(set(refs)))
        for part in parts:
            for key in ('ref', 'value', 'footprint', 'nets', 'page', 'kind', 'mpn', 'maker', 'source', 'pins', 'note', 'board'):
                self.assertIn(key, part, part['ref'])
            self.assertEqual(set(part['pins']), set(part['nets']), part['ref'])
            self.assertEqual(part['footprint'].count(':'), 1, part['ref'])
            self.assertIn(part['board'], ('power', 'control'))
        self.assertEqual([p['ref'] for p in parts if p['board'] == 'control'], ['J2'])
        self.assertEqual(len(sm.power_parts(parts)), len(parts) - 1)
        custom = sm.custom_footprints()
        for part in parts:
            lib, name = pf.split_footprint(part)
            if lib == pf.CUSTOM_LIB:
                self.assertIn(name, custom)
        for ref, (x, y, angle) in sm.PLACEMENT.items():
            self.assertIn(ref, {p['ref'] for p in sm.power_parts(parts)})
            self.assertTrue(0 < x < sm.WIDTH and 0 < y < sm.HEIGHT, ref)
        self.assertEqual(set(sm.PLACEMENT), {p['ref'] for p in sm.power_parts(parts)})

    def test_schematic_spec_validates_and_is_erc_consistent_before_kicad(self):
        parts = sm.build_parts()
        spec = ps.coerce_spec(sm.schematic_spec(Path('x/kicad'), Path('x/design'), parts, sm.design_rules_text([])))
        self.assertEqual([c['name'] for c in spec.net_classes], ['Default', 'HV', 'GATE'])
        self.assertEqual(spec.board, 'power')
        self.assertEqual(spec.flag_nets, sm.FLAG_NETS)
        power = [p for p in spec.parts if p.get('board') == 'power']
        report = ps.analyse_connectivity(power, spec.flag_nets)
        self.assertEqual(report['undriven_power_nets'], [])
        self.assertEqual(report['pin_conflicts'], [])
        self.assertEqual(report['single_pin_nets'], [])
        self.assertEqual(report['no_connect_pins_with_nets'], [])

    def test_pin_field_rules_come_from_pad_geometry(self):
        parts = [p for p in sm.power_parts() if p['footprint'] in FAKE_GEOMETRY]
        rules = sm.pin_field_rules(parts, FAKE_GEOMETRY)
        self.assertEqual([(r['ref'], r['pads'], r['required_mm']) for r in rules], [('Q1', ['2', '3'], 2.5), ('Q2', ['2', '3'], 3.0)])
        self.assertAlmostEqual(rules[0]['gap_mm'], 0.635)
        self.assertAlmostEqual(sm.pad_gap(*FAKE_GEOMETRY['Capacitor_SMD:C_2220_5750Metric']), 3.3)
        text = sm.design_rules_text(rules)
        self.assertTrue(text.startswith('(version 1)\n(rule "HV to PGND"'))
        self.assertLess(text.index('HV to PGND'), text.index('pin field Q1'))
        self.assertIn("A.memberOfFootprint('Q2') && B.intersectsCourtyard('Q2') && (A.NetClass == 'HV' || B.NetClass == 'HV')", text)
        self.assertEqual(text.count('(rule '), 3)
        ps.normalise_dru(text)

    def test_zone_polygons_cover_the_placed_pads(self):
        self.assertEqual(sm.zone_coverage(SAMPLE_PADS), [])
        moved = {**SAMPLE_PADS, ('C1', '1'): [(50.0, 47.55)]}
        self.assertEqual(len(sm.zone_coverage(moved)), 1)
        self.assertTrue(sm.point_in_polygon((105, 30), sm.VOUT_POLYGON))
        self.assertFalse(sm.point_in_polygon((60, 30), sm.VOUT_POLYGON))

    def test_routing_plan_is_valid_and_keeps_hv_on_zones(self):
        plan = sm.routing_plan(SAMPLE_PADS, 'x.kicad_pcb')
        self.assertEqual(gr.validate_plan(plan), plan)
        self.assertNotIn('style', plan)  # the V2 plan byte for byte
        styled = sm.routing_plan(SAMPLE_PADS, 'x.kicad_pcb', style=sm.V21_STYLE)
        self.assertEqual(gr.validate_plan(styled), styled)
        self.assertEqual(styled['style'], sm.V21_STYLE)
        self.assertEqual({k: v for k, v in styled.items() if k != 'style'}, plan)
        self.assertEqual(plan['layers'], sm.LAYERS)
        for net in sm.HV_NETS:
            self.assertFalse(plan['power'][net]['stubs'])
            self.assertEqual(set(plan['power'][net]['zones']), {'F.Cu', 'B.Cu'})
            self.assertEqual(plan['net_rules'][net]['clearance'], sm.HV_TO_PGND)
            self.assertIn(net, plan['fanout']['skip_nets'])
        self.assertEqual(plan['critical'], sm.CRITICAL)
        self.assertEqual(plan['critical_layers'], ['F.Cu', 'B.Cu'])
        self.assertEqual(plan['ground']['layers'], ['In1.Cu', 'In2.Cu'])
        self.assertIn(['Q1', '4'], plan['fanout']['skip_pads'])
        self.assertEqual(plan['pre_routed']['vias'], [dict(net='KS_H', xy=[58.0, 33.0], port=True)])
        self.assertEqual(plan['pre_routed']['tracks'][0]['a'], [56.16, 36.0])
        self.assertEqual(plan['keepouts'][0]['rect'], list(sm.HEATSINK_BASE))
        self.assertEqual(len(plan['keepouts']), 1 + 2 * len(sm.ZONE_KEEPOUTS))
        self.assertFalse(plan['strict'])

    def test_stackup_text_and_injection(self):
        text = sm.stackup_text()
        self.assertEqual(text.count('(type "copper")'), 4)
        self.assertEqual(text.count('(layer '), 7)
        with tempfile.TemporaryDirectory(prefix='aipe smoke ') as folder:
            path = Path(folder) / 'b.kicad_pcb'
            path.write_text('(kicad_pcb (version 20241229)\n\t(paper "A4")\n\t(setup\n\t\t(pad_to_mask_clearance 0)\n\t)\n)\n', encoding='utf-8')
            self.assertTrue(sm.inject_stackup(path))
            written = path.read_text(encoding='utf-8')
            self.assertEqual(written.count('(stackup'), 1)
            self.assertIn('(paper "A3")', written)
            self.assertFalse(sm.inject_stackup(path))
            path.write_text('(kicad_pcb)', encoding='utf-8')
            with self.assertRaises(ValueError):
                sm.inject_stackup(path)

    def test_module_versions_and_evidence_layout(self):
        versions = sm.module_versions()
        self.assertEqual(set(versions), set(sm.MODULES))
        for record in versions.values():
            self.assertEqual(len(record['sha256']), 64)
            self.assertGreater(record['lines'], 10)
        summary = dict(generated_utc='now', host='h', python='3', status='passed', seconds=1.0, tools=dict(kicad_cli='x', kicad_cli_version='10.0.7'),
                       modules=versions, notes=['n'], steps=dict(
                           model=dict(parts=16, power_parts=15, control_parts=['J2'], nets=18, custom_footprints=['a']),
                           schematic=dict(sheets=['p'], parts_placed=15, skipped={}, symbol_fallbacks={}, flags=['VIN'], net_classes=['Default'], pin_field_rules=[]),
                           erc=dict(status='passed', finding_count=0, tool_exit_code=0, seconds=0.2),
                           board=dict(status='passed', copper_layers=4, stackup_present=True, footprints=15, pcbnew_version='10.0.7',
                                      report=dict(tracks=1, vias=2, zones=8, pruned=0, unresolved=[], seconds=0.3, saved={'footprints': 15})),
                           drc=dict(status='passed', finding_count=0, violations=0, unconnected_items=0, schematic_parity=0, tool_exit_code=0),
                           exports=dict(status='passed', commands=11, exit_codes=[0] * 11, files=30),
                           simulation=dict(status='passed', name='s', points=10, ngspice_runtime_s=1.0, vout_mean_V=200.0, il_pkpk_A=7.4, efficiency=0.99, warnings=0, ngspice_version='46')))
        evidence = sm.evidence_summary(summary)
        self.assertEqual(evidence['status'], 'passed')
        self.assertEqual(evidence['erc']['finding_count'], 0)
        self.assertEqual((evidence['drc']['violations'], evidence['drc']['unconnected_items'], evidence['drc']['schematic_parity']), (0, 0, 0))
        self.assertEqual(evidence['exports']['commands'], 11)
        self.assertEqual(evidence['board']['unresolved'], 0)
        self.assertEqual(evidence['tools']['ngspice_version'], '46')
        self.assertEqual(set(evidence['module_versions']), set(sm.MODULES))
        json.dumps(evidence)


@unittest.skipUnless(kicad_cli() and library_installed() and sm.kicad_python(), 'kicad-cli, the KiCad footprint library and KiCad Python are required')
class EndToEndTests(unittest.TestCase):
    """Runs the whole pipeline (without the ngspice step) into a temporary directory."""

    def test_smoke_passes_with_zero_erc_and_drc_findings(self):
        with tempfile.TemporaryDirectory(prefix='aipe v2 smoke ') as folder:
            summary = sm.run(folder, skip_simulation=True)
            steps = summary['steps']
            self.assertEqual(steps['model']['pad_mapping_issues'], [])
            self.assertEqual(steps['schematic']['skipped'], {'J2': "board 'control'"})
            self.assertEqual(steps['erc']['status'], 'passed', steps['erc'])
            self.assertEqual((steps['erc']['finding_count'], steps['erc']['tool_exit_code']), (0, 0))
            board = steps['board']
            self.assertEqual(board['status'], 'passed', board.get('error'))
            self.assertEqual((board['copper_layers'], board['stackup_present'], board['footprints']), (4, True, 15))
            self.assertEqual(board['report']['unresolved'], [])
            self.assertEqual(board['report']['zones'], 8)
            self.assertGreater(board['report']['tracks'], 0)
            drc = steps['drc']
            self.assertEqual(drc['status'], 'passed', drc.get('details'))
            self.assertEqual((drc['violations'], drc['unconnected_items'], drc['schematic_parity'], drc['tool_exit_code']), (0, 0, 0, 0))
            exports = steps['exports']
            self.assertEqual((exports['status'], exports['commands'], exports['exit_codes']), ('passed', 11, [0] * 11))
            self.assertEqual(steps['simulation']['status'], 'skipped')
            self.assertEqual(summary['status'], 'passed')
            root = Path(folder)
            for name in ('kicad/AIPE_V2_Smoke.kicad_pcb', 'kicad/AIPE_V2_Smoke.kicad_sch', 'kicad/AIPE_V2_Smoke.kicad_dru', 'kicad/fp-lib-table',
                         'design/schematic_mapping.json', 'design/routing_report.json', 'exports/export-manifest.json', 'smoke-summary.json'):
                self.assertTrue((root / name).is_file(), name)

    def test_smoke_passes_with_the_v21_router_style(self):
        """The same pipeline with the V2.1 geometry enabled (8-direction search, octilinear simplification, arcs): the board routes
        with zero unresolved connections, the beautify stage runs, and native DRC with schematic parity stays at zero findings."""
        with tempfile.TemporaryDirectory(prefix='aipe v2 smoke styled ') as folder:
            summary = sm.run(folder, skip_simulation=True, style=sm.V21_STYLE)
            steps = summary['steps']
            board = steps['board']
            self.assertEqual(board['status'], 'passed', board.get('error'))
            report = board['report']
            self.assertEqual(report['unresolved'], [])
            self.assertEqual(report['zones'], 8)
            self.assertTrue(report['style']['diagonal'])
            self.assertTrue(report['beautify']['enabled'])
            self.assertGreater(report['beautify']['chains'], 0)
            self.assertLessEqual(report['beautify']['length_after_mm'], report['beautify']['length_before_mm'] + 1e-6)
            drc = steps['drc']
            self.assertEqual(drc['status'], 'passed', drc.get('details'))
            self.assertEqual((drc['violations'], drc['unconnected_items'], drc['schematic_parity'], drc['tool_exit_code']), (0, 0, 0, 0))
            self.assertEqual(steps['exports']['status'], 'passed')
            self.assertEqual(summary['status'], 'passed')
            plan = json.loads((Path(folder) / 'design/routing_plan.json').read_text(encoding='utf-8'))
            self.assertEqual(plan['style'], sm.V21_STYLE)


if __name__ == '__main__':
    unittest.main()
