"""Tests of the requirement-file-driven DAB-V1 generation (automation.dab_v1).

Host interpreter only: YAML subset loader against PyYAML, requirement validation, model connectivity pre-checks,
insulation-table rules, harness pin-map agreement between the three boards, custom footprint land gaps, routing-plan
assembly against grid_router.validate_plan and the run_plan extensions.  Nothing here runs KiCad; the native ERC/DRC
evidence lives under examples/dab-10kw/verification and is produced by the pipeline, not by this file.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from automation.dab_v1 import footprints as fpt, model, parts, requirements as rq, rules
from automation.kicad_tools import grid_router as gr, project_footprints as pf, project_schematic as ps

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - the host environment has PyYAML
    yaml = None

REQ = rq.load()


class YamlLoaderTests(unittest.TestCase):
    @unittest.skipIf(yaml is None, 'PyYAML unavailable')
    def test_fallback_loader_matches_pyyaml_on_every_requirement_file(self):
        for path in rq.requirement_files().values():
            text = path.read_text(encoding='utf-8-sig')
            self.assertEqual(json.dumps(yaml.safe_load(text), sort_keys=True, default=str),
                             json.dumps(rq.load_yaml_text(text), sort_keys=True, default=str), path.name)

    def test_subset_parser_scalars_flow_and_blocks(self):
        data = rq.load_yaml_text('a: 1\nb: 2.5\nc: [1, "x, y", {k: null}]\nd:\n  - e: true\n    f: "https://x/y?z=1"\n  - 3\nurl: https://a/b\n2.5: 1.5\n')
        self.assertEqual(data['a'], 1)
        self.assertEqual(data['c'], [1, 'x, y', {'k': None}])
        self.assertEqual(data['d'][0]['f'], 'https://x/y?z=1')
        self.assertEqual(data['d'][1], 3)
        self.assertEqual(data['url'], 'https://a/b')
        self.assertEqual(data[2.5], 1.5)
        with self.assertRaises(rq.YamlError):
            rq.load_yaml_text('a: [1, 2\n')


class RequirementTests(unittest.TestCase):
    def test_boards_and_stackups_are_consistent(self):
        for board in rq.BOARDS:
            cfg = REQ.board(board)
            self.assertEqual(sum(1 for row in cfg['stackup'] if row[1] == 'copper'), cfg['layers'])
            self.assertAlmostEqual(sum(float(row[2]) for row in cfg['stackup']), cfg['thickness_mm'], places=2)
            self.assertEqual(REQ.floorplans[board]['outline_mm'], cfg['size_mm'])

    def test_functional_gap_interpolates_the_reference_table(self):
        self.assertEqual(REQ.functional_gap_mm(20), 0.25)
        self.assertEqual(REQ.functional_gap_mm(800), 4.0)
        self.assertEqual(REQ.functional_gap_mm(1000), 5.0)
        self.assertGreater(REQ.functional_gap_mm(825), 4.0)
        self.assertLess(REQ.functional_gap_mm(825), 5.0)
        self.assertGreaterEqual(REQ.reinforced_gap_mm(), REQ.functional_gap_mm(1000))

    def test_validation_rejects_a_broken_harness_map(self):
        import copy
        broken = copy.deepcopy(REQ)
        broken.interfaces = copy.deepcopy(REQ.interfaces)
        del broken.interfaces['control_harness']['pins'][40]
        with self.assertRaises(ValueError):
            broken.validate()


class ModelTests(unittest.TestCase):
    def test_every_board_passes_the_connectivity_precheck(self):
        for board in rq.BOARDS:
            circuit = model.build(REQ, board)
            report = ps.analyse_connectivity(circuit.parts, model.flag_nets(circuit))
            for key in ('undriven_power_nets', 'pin_conflicts', 'single_pin_nets', 'no_connect_pins_with_nets'):
                self.assertFalse(report[key], (board, key, report[key][:5]))
            refs = [p['ref'] for p in circuit.parts]
            self.assertEqual(len(refs), len(set(refs)))

    def test_pad_maps_match_the_footprints(self):
        custom = fpt.custom(REQ.components)
        root = pf.footprints_root()
        for board in rq.BOARDS:
            circuit = model.build(REQ, board)
            if root is None or not root.is_dir():
                issues = [i for i in pf.validate_pad_mapping(circuit.parts, custom) if 'AIPE:' in i]
            else:
                issues = pf.validate_pad_mapping(circuit.parts, custom)
            self.assertEqual(issues, [], board)

    def test_harness_pin_map_agrees_between_power_and_control_boards(self):
        harness = REQ.interfaces['control_harness']
        control = model.build(REQ, 'control').parts
        shared = set(harness['shared_nets'])
        for board, ctrl_ref, prefix in (('primary-power', 'J2', 'P'), ('secondary-power', 'J3', 'S')):
            power_j5 = next(p for p in model.build(REQ, board).parts if p['ref'] == 'J5')['nets']
            ctrl = next(p for p in control if p['ref'] == ctrl_ref)['nets']
            for pin, net in harness['pins'].items():
                self.assertEqual(power_j5[str(pin)], net, (board, pin))
                self.assertEqual(ctrl[str(pin)], net if net in shared else f'{prefix}_{net}', (board, pin))

    def test_switch_roles_and_kelvin_returns(self):
        circuit = model.build(REQ, 'primary-power')
        for q in (p for p in circuit.parts if p['kind'] == 'Q'):
            drain, source = model.ROLE_NETS[q['role']]
            self.assertEqual((q['nets']['1'], q['nets']['2']), (drain, source))
            self.assertEqual(q['nets']['3'], f'KS_{q["role"]}')
            driver = next(p for p in circuit.parts if p.get('island') == q['role'] and p['mpn'] == REQ.components['gate_driver']['mpn'])
            self.assertEqual(driver['nets']['3'], f'KS_{q["role"]}')  # COM on the Kelvin source only
            self.assertEqual(driver['nets']['7'], f'G_{q["role"]}')   # Miller clamp straight at the gate
            self.assertEqual(driver['nets']['11'], f'PWMF_{model.COMPLEMENT[q["role"]]}')  # shoot-through interlock

    def test_secondary_carries_modulator_and_amplifier_and_primary_the_dc_block(self):
        primary = model.build(REQ, 'primary-power').parts
        secondary = model.build(REQ, 'secondary-power').parts
        self.assertTrue(any(p.get('barrier') == 'vmod' for p in secondary))
        self.assertFalse(any(p.get('barrier') == 'vmod' for p in primary))
        self.assertTrue(any('CBLK' in p['footprint'] for p in primary))
        self.assertFalse(any('CBLK' in p['footprint'] for p in secondary))


class RuleTests(unittest.TestCase):
    def test_pair_voltage_over_switch_states(self):
        bus_p, sw_a, island_ah = ('bus_p', (1, 0, 0), 0), ('sw_a', (0, 1, 0), 0), ('island_ah', (0, 1, 0), 25)
        self.assertEqual(rules.pair_voltage(bus_p, sw_a, 800), 800)
        self.assertEqual(rules.pair_voltage(sw_a, island_ah, 800), 25)
        self.assertEqual(rules.pair_voltage(bus_p, island_ah, 800), 825)

    def test_power_board_rules_have_reinforced_barrier_and_documented_relaxations(self):
        parts_ = model.build(REQ, 'primary-power').parts
        built = rules.build_rules(REQ, 'primary-power', parts_)
        self.assertIn(f'(min {REQ.reinforced_gap_mm()}mm)', built['dru'])
        self.assertIn("A.NetClass == 'CTRL'", built['dru'])
        self.assertNotIn("B.NetClass != 'CTRL'", built['dru'])  # unconnected pads must not count as hazardous
        refs = {r['ref'] for r in built['evidence']['relaxations']}
        self.assertTrue({'Q1', 'Q2', 'Q3', 'Q4'} <= refs)
        for r in built['evidence']['relaxations']:
            self.assertGreater(r['table_mm'], r['package_mm'])
        self.assertTrue(all(c['nets'] for c in built['classes'] if c['name'] != 'Default'))
        domains = rules.power_domains(parts_)
        for net in ('BUS_P', 'PGND', 'SW_A', 'SW_B', 'G_AH', 'KS_BL', 'VDIV1', 'BLD1', 'S_5V'):
            self.assertIn(net, domains)
        for net in ('GND_CTRL', '3V3', 'PWM_AH', 'ISNS', 'VSNS_P'):
            self.assertNotIn(net, domains)
        gap = rules.make_pair_gap(REQ, 'primary-power', domains)
        self.assertEqual(gap('GND_CTRL', 'BUS_P'), (REQ.reinforced_gap_mm(), True))
        self.assertEqual(gap('G_AH', 'KS_AH'), (REQ.board('primary-power')['min_clearance_mm'], False))
        self.assertEqual(gap('BUS_P', 'PGND'), (4.0, False))

    def test_secondary_board_needs_no_package_relaxation(self):
        parts_ = model.build(REQ, 'secondary-power').parts
        built = rules.build_rules(REQ, 'secondary-power', parts_)
        self.assertEqual(built['evidence']['relaxations'], [])

    def test_control_board_is_a_single_selv_domain(self):
        built = rules.build_rules(REQ, 'control', model.build(REQ, 'control').parts)
        self.assertEqual([c['name'] for c in built['classes']], ['Default', 'CTRL_POWER', 'CTRL_SIGNAL'])


class FootprintTests(unittest.TestCase):
    def test_isolation_footprints_keep_the_reinforced_land_gap(self):
        custom = fpt.custom(REQ.components)
        for name in fpt.barrier_footprints():
            self.assertGreaterEqual(fpt.land_gap(custom[name][0]), REQ.reinforced_gap_mm(), name)
            pads = pf.pads_in_text(custom[name][0])
            numbers = [p['number'] for p in pads if p['number']]
            self.assertEqual(len(numbers), len(set(numbers)))

    def test_part_codes(self):
        self.assertEqual(parts.erjp_code('2'), '2R00')
        self.assertEqual(parts.erjp_code('180'), '1800')
        self.assertEqual(parts.erjp_code('1k'), '1001')
        self.assertEqual(parts.tnpw_code('634k', '1206'), 'TNPW1206634KBEEA')
        self.assertEqual(parts.tnpw_code('10k', '0603'), 'TNPW060310K0BEEA')


class RoutingPlanTests(unittest.TestCase):
    def test_run_plan_accepts_several_pours_per_layer(self):
        self.assertEqual(gr.polygons_of([(0, 0), (1, 0), (1, 1)]), [[(0, 0), (1, 0), (1, 1)]])
        self.assertEqual(len(gr.polygons_of([[(0, 0), (1, 0), (1, 1)], [(2, 2), (3, 2), (3, 3)]])), 2)
        plan = dict(board=dict(width=10, height=10), layers=['F.Cu'], power={'N': dict(zones={'F.Cu': [[(0, 0), (1, 0), (1, 1)], [(2, 2), (3, 2), (3, 3)]]})})
        gr.validate_plan(plan)
        with self.assertRaises(ValueError):
            gr.validate_plan(dict(board=dict(width=10, height=10), layers=['F.Cu'], power={'N': dict(zones={'F.Cu': [[(0, 0), (1, 0)]]})}))

    def test_floorplan_record_builds_a_valid_plan_when_present(self):
        from automation.dab_v1 import routing
        for board in rq.BOARDS:
            record = rq.EXAMPLE / 'pcb' / f'floorplan_{board}.json'
            if not record.exists():
                self.skipTest(f'{record.name} not generated')
            data = json.loads(record.read_text(encoding='utf-8'))
            nets = sorted({n for p in model.build(REQ, board).parts for n in p['nets'].values() if n})
            plan = routing.build_plan(REQ, board, data, nets, None)
            self.assertEqual(plan['layers'], REQ.routing[board]['layers'])
            if REQ.board(board)['side'] != 'control':
                self.assertIn('BUS_P', plan['power'])
                self.assertTrue(all('region' in plan['net_rules'][n] for n in nets if n.startswith('G_')))
                for keepout in plan['keepouts']:
                    self.assertEqual(len(keepout['rect']), 4)

    def test_pour_rectangles_merge_into_disjoint_polygons(self):
        try:
            import shapely  # noqa: F401
        except ImportError:
            self.skipTest('shapely unavailable')
        from automation.dab_v1.copper import merge_zones
        merged = merge_zones({'N': {'F.Cu': [[(0, 0), (10, 0), (10, 10), (0, 10)], [(5, 5), (15, 5), (15, 15), (5, 15)], [(30, 30), (31, 30), (31, 31), (30, 31)]]}})
        self.assertEqual(len(merged['N']['F.Cu']), 2)
        self.assertEqual(len(merged['N']['F.Cu'][0]), 8)
        with self.assertRaises(ValueError):  # a frame leaves a hole
            merge_zones({'N': {'F.Cu': [[(0, 0), (10, 0), (10, 1), (0, 1)], [(0, 9), (10, 9), (10, 10), (0, 10)], [(0, 0), (1, 0), (1, 10), (0, 10)], [(9, 0), (10, 0), (10, 10), (9, 10)]]}})

    def test_rect_subtraction(self):
        from automation.dab_v1.floorplan import subtract_rects
        pieces = subtract_rects([0, 0, 10, 10], [[4, 4, 6, 6]])
        self.assertEqual(len(pieces), 4)
        self.assertAlmostEqual(sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in pieces), 100 - 4)
        self.assertEqual(subtract_rects([0, 0, 10, 10], [[-1, -1, 11, 11]]), [])


if __name__ == '__main__':
    unittest.main()
