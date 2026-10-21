"""Tests of the requirement-file-driven DAB-V1 generation (automation.dab_v1).

Host interpreter only: YAML subset loader against PyYAML, requirement validation, model connectivity pre-checks,
insulation-table rules, harness pin-map agreement between the three boards, custom footprint land gaps, routing-plan
assembly against grid_router.validate_plan and the run_plan extensions.  Nothing here runs KiCad; the native ERC/DRC
evidence lives under examples/dab-10kw/verification and is produced by the pipeline, not by this file.
"""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from automation.dab_v1 import fanout_rows as fr, footprints as fpt, model, parts, requirements as rq, rules
from automation.kicad_tools import grid_router as gr, project_footprints as pf, project_schematic as ps

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is a repository requirement
    np = None

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

    def test_plan_carries_the_remediation_fields(self):
        """The routing plan built from a regenerated floorplan record switches on the 2026-10-21 remediation: no via-in-pad,
        stranded-ground fallback and routing, same-net row bridges as pre-routed tracks, and the optional time box."""
        from automation.dab_v1 import routing
        record = rq.EXAMPLE / 'pcb' / 'floorplan_primary-power.json'
        if not record.exists():
            self.skipTest(f'{record.name} not generated')
        data = json.loads(record.read_text(encoding='utf-8'))
        if 'no_via_in_pad' not in data['plan']:
            self.skipTest('floorplan record predates the remediation')
        nets = sorted({n for p in model.build(REQ, 'primary-power').parts for n in p['nets'].values() if n})
        plan = routing.build_plan(REQ, 'primary-power', data, nets, None, time_budget_s=120, checkpoint=Path('x.kicad_pcb'))
        self.assertFalse(plan['fanout']['no_via_in_pad'])  # available in the router, deliberately off for the DAB plans (remediation 2.2)
        self.assertGreaterEqual(len(plan['fanout']['exact_lane_pads']), 100)  # exit lanes for the IC pads (remediation 2.10)
        self.assertTrue(all(len(lane) == 3 and lane[2] > 0 for lane in plan['fanout']['exact_lane_pads']))
        self.assertEqual(plan['fanout']['fallback_direct_nets'], ['GND_CTRL'])
        self.assertTrue(plan['ground']['route_stranded'])
        self.assertEqual(plan['time_budget_s'], 120.0)
        self.assertEqual(plan['checkpoint'], 'x.kicad_pcb')
        bridges = [t for t in plan['pre_routed']['tracks'] if 'note' in t]
        self.assertGreaterEqual(len(bridges), 20)  # five DWN-36 modules x six same-net runs
        self.assertTrue(all(t['width'] <= fr.BRIDGE_WIDTH_MAX for t in bridges))
        skipped = {tuple(p) for p in plan['fanout']['skip_pads']}
        stubbed = {(s[0], s[1]) for s in plan['fanout']['exact_stub_pads']}
        self.assertFalse(skipped & stubbed)  # a pad is either bridged-and-skipped or stubbed, never both
        self.assertNotIn('time_budget_s', routing.build_plan(REQ, 'primary-power', data, nets, None))


def dwn_row(net_of, *, y=78.975, x0=92.475, pitch=0.65, pad=(0.4, 1.85)):
    """Synthetic ProjectBoard.pads() records of one 0.65 mm pitch row (the UCC14141 DWN-36 SELV row of the DAB-V1 boards)."""
    out = []
    for i, net in enumerate(net_of):
        x = x0 + i * pitch
        out.append(dict(ref='U3', pin=str(i + 1), net=net, xy=[x, y], box=[x - pad[0] / 2, y - pad[1] / 2, x + pad[0] / 2, y + pad[1] / 2],
                        layers=['F.Cu'], thru=False))
    return out


class FinePitchRowTests(unittest.TestCase):
    """automation.dab_v1.fanout_rows: the geometric escape plan of fine-pitch rows (root cause of the 2026-10-21 fan-out and
    route failures on the DAB-V1 boards; see docs/dab-10kw/routing-remediation.md)."""

    WIDTHS = {'GNDP_AH': 0.6, '12V_BIAS_AH': 0.8, 'PG_BIAS_N': 0.3, 'BIAS_ENF': 0.3, 'PGND': 0.3}
    FANOUT = {'GNDP_AH': 0.25, '12V_BIAS_AH': 0.25}
    ROUTER = dict(trace=0.3, clearance=0.25, grid=0.125, eps=0.02, base_stub=0.45)

    def plan(self, nets, bbox=(91.29, 67.81, 104.71, 80.19), **kw):
        params = dict(self.ROUTER, **kw)
        return fr.plan_rows('U3', dwn_row(nets), list(bbox), width_of=lambda n: self.WIDTHS.get(n, 0.3),
                            fanout_width_of=lambda n: self.FANOUT.get(n, self.WIDTHS.get(n, 0.3)), **params)

    def test_end_pads_of_a_long_row_escape_across_the_row(self):
        pads = dwn_row(['A'] * 18)
        # the courtyard of the DWN-36 is nearly square: the raw |dx| vs |dy| rule sent pins 1 and 18 sideways along the row
        self.assertEqual(fr.pad_direction(pads[0], pads, [91.29, 67.81, 104.71, 80.19]), (0, 1))
        self.assertEqual(fr.pad_direction(pads[-1], pads, [91.29, 67.81, 104.71, 80.19]), (0, 1))
        self.assertEqual(fr.outward_direction((10.0, 3.0), [0, 0, 20, 4]), (0, 1))
        self.assertEqual(fr.outward_direction((19.0, 2.0), [0, 0, 20, 4]), (1, 0))

    def test_same_net_runs_are_bridged_and_get_one_stub_each(self):
        nets = ['GNDP_AH', 'GNDP_AH', 'PG_BIAS_N', 'BIAS_ENF', 'GNDP_AH', '12V_BIAS_AH', '12V_BIAS_AH'] + ['GNDP_AH'] * 11
        out = self.plan(nets)
        self.assertEqual(out['warnings'], [])
        self.assertEqual(len(out['bridges']), 3)  # pins 1-2, 6-7, 8-18
        for bridge in out['bridges']:
            self.assertLessEqual(bridge['width'], 0.3)
            self.assertLess(bridge['a'][1], 79.9)  # inside the lands, in their outer half
            self.assertGreater(bridge['a'][1], 78.975)
        stubs = {s[1]: s for s in out['stubs']}
        self.assertEqual(len(stubs), 6)  # six runs: GND 1-2, PG, ENF, GND 5, 12V 6-7, GND 8-18
        self.assertEqual(len(out['skip_pads']), 18 - 6)
        self.assertEqual(stubs['1'][4], 0.325)   # even run: the stub sits on the bridge between the two lands
        self.assertEqual(stubs['6'][4], 0.325)
        self.assertEqual(stubs['13'][4], 0.0)    # odd run: the middle land
        self.assertTrue(all(s[3] == [0, 1] for s in out['stubs']))

    def test_stub_lengths_follow_the_occupancy_model(self):
        nets = ['GNDP_AH', 'GNDP_AH', 'PG_BIAS_N', 'BIAS_ENF', 'GNDP_AH', '12V_BIAS_AH', '12V_BIAS_AH'] + ['GNDP_AH'] * 11
        stubs = {s[1]: s for s in self.plan(nets)['stubs']}
        # narrow nets: the port just clears the neighbouring lands' halo band (clearance + trace/2 = 0.4 mm)
        self.assertEqual(stubs['3'][2], 0.5)
        self.assertEqual(stubs['4'][2], 0.5)
        # a 0.6 mm net escaping alone between a 0.3 mm stub and the 12V stub has to pass the neighbour's stub end before it widens
        self.assertGreater(stubs['5'][2], stubs['4'][2] + 0.5)
        # a stub on a bridge between two same-net lands sees its nearest foreign stub 1.5 pitches away: no extra length
        self.assertLess(stubs['6'][2], stubs['5'][2])
        self.assertGreaterEqual(stubs['6'][2], 0.25 + 0.15 + fr.dilation_mm(0.8, 0.3, 0.125) + 0.1 - 1e-9)
        # the comb geometry is consistent: a wide net's port is outside the dilated halo of every foreign stub
        for s in self.plan(nets)['stubs']:
            net = nets[int(s[1]) - 1]
            if self.WIDTHS[net] <= 0.3:
                continue
            port = (92.475 + (int(s[1]) - 1) * 0.65 + s[4], 79.9 + s[2])
            for t in self.plan(nets)['stubs']:
                other = nets[int(t[1]) - 1]
                if other == net:
                    continue
                end = (92.475 + (int(t[1]) - 1) * 0.65 + t[4], 79.9 + t[2] + self.FANOUT.get(other, self.WIDTHS[other]) / 2)
                need = fr.halo_mm(self.FANOUT.get(other, self.WIDTHS[other]), 0.3, 0.25, 0.02) + fr.dilation_mm(self.WIDTHS[net], 0.3, 0.125)
                lateral = abs(port[0] - end[0])
                if lateral < need:
                    self.assertGreaterEqual(math.hypot(lateral, port[1] - end[1]), need - 1e-6, (s, t))

    def test_exit_lanes_reach_the_fan_out_band_and_wide_stubs_end_beyond_them(self):
        nets = ['GNDP_AH', 'GNDP_AH', 'PG_BIAS_N', 'BIAS_ENF', 'GNDP_AH', '12V_BIAS_AH', '12V_BIAS_AH'] + ['GNDP_AH'] * 11
        widths = dict(self.WIDTHS, GNDP_AH=0.5, **{'12V_BIAS_AH': 0.5})
        out = fr.plan_rows('U3', dwn_row(nets), [91.29, 67.81, 104.71, 80.19], width_of=lambda n: widths.get(n, 0.3),
                           fanout_width_of=lambda n: self.FANOUT.get(n, widths.get(n, 0.3)), band_mm=3.0, **self.ROUTER)
        stubs = {s[1]: s for s in out['stubs']}
        lanes = {l[1]: l[2] for l in out['lanes']}
        self.assertEqual(out['rows'][0]['lane_end'], 2.0)
        for pin in ('3', '4'):  # narrow nets: 0.5 mm stub plus a lane to the end of the band
            self.assertAlmostEqual(stubs[pin][2] + lanes[pin], 2.0, places=6)
        # the lone wide GND pin ends beyond the neighbouring lane end, so its 0.5 mm track starts where no lane is alongside
        self.assertGreater(stubs['5'][2], 2.0)
        self.assertNotIn('5', lanes)
        # critical nets keep the pad port and get a lane from the land to the band end
        crit = fr.plan_rows('U2', dwn_row(['G_AH', 'OUTL_AH', 'VDD_AH'], pitch=1.27, pad=(0.6, 1.65)), [0, 0, 20, 20], width_of=lambda n: 0.6,
                            fanout_width_of=lambda n: 0.25, critical_nets={'G_AH', 'OUTL_AH'}, band_mm=3.0, **self.ROUTER)
        self.assertEqual([s[1] for s in crit['stubs']], ['3'])
        self.assertEqual({l[1]: l[2] for l in crit['lanes']}['1'], 2.0)
        self.assertAlmostEqual({l[1]: l[2] for l in crit['lanes']}['3'] + crit['stubs'][0][2], 2.0, places=6)

    def test_pour_nets_are_bridged_but_not_stubbed_and_coarse_rows_keep_plain_stubs(self):
        out = self.plan(['PGND', 'PGND', 'PGND', 'BIAS_ENF'] + ['PGND'] * 14, pour_nets={'PGND'})
        self.assertEqual(len(out['bridges']), 2)
        self.assertEqual([s[1] for s in out['stubs']], ['4'])
        self.assertEqual(out['skip_pads'], [])  # pour-net pads are bridged and keep the fan-out's via escape (no enclosed pour pockets)
        coarse = fr.plan_rows('U2', dwn_row(['A', 'B', 'C', 'D'], pitch=1.27, pad=(0.6, 1.65)), [0, 0, 20, 20], width_of=lambda n: 0.3,
                              fanout_width_of=lambda n: 0.3, **self.ROUTER)
        self.assertEqual(coarse['bridges'], [])
        self.assertEqual([s[2] for s in coarse['stubs']], [0.45] * 4)
        ground = fr.plan_rows('U9', dwn_row(['GND_CTRL', 'X', 'GND_CTRL', 'GND_CTRL']), [0, 0, 20, 20], width_of=lambda n: 0.3,
                              fanout_width_of=lambda n: 0.25, exact_via_nets={'GND_CTRL'}, **self.ROUTER)
        self.assertEqual(ground['exact_via_pads'], [['U9', '1'], ['U9', '3']])


@unittest.skipIf(np is None, 'numpy unavailable')
class ExactStubEndTests(unittest.TestCase):
    """Router._exact_end_ok / _claim_port_cell without pcbnew: a bare Router around a Grid with hand-made pad records."""

    def router(self):
        r = gr.Router.__new__(gr.Router)
        r.grid = gr.Grid(81, 41, 1, grid=0.125, margin_cells=2)
        r.trace, r.clearance = 0.3, 0.25
        r.pad_records = []
        return r

    def pad(self, r, code, box, layers=(0,), thru=False):
        rec = dict(code=code, box=list(box), layers=list(layers), thru=thru, net=f'N{code}')
        r.pad_records.append(rec)
        for layer in layers:
            r.grid.box(r.grid.occ[layer], box, r.clearance + r.trace / 2, code, alt=r.grid.alt[layer])
        return rec

    def test_soft_conflict_cell_is_accepted_only_with_real_clearance(self):
        r = self.router()
        # two 0.40 mm lands at 0.65 mm pitch: their 0.4 mm halos overlap in the gap and beyond the land ends
        a = self.pad(r, 1, [4.0, 1.0, 4.4, 2.85])
        b = self.pad(r, 2, [4.65, 1.0, 5.05, 2.85])
        end = (4.2, 2.85 + 0.35)  # the 0.35 mm stub end of land a, below the row
        cell = r.grid.to_grid(*end)
        self.assertEqual(int(r.grid.occ[0, cell[1], cell[0]]), -2)
        self.assertTrue(r._exact_end_ok(a, 0, end, cell, 0.25))   # 0.25 mm stub: 0.45 mm from land b >= clearance + width/2 = 0.375
        r._claim_port_cell(0, cell[0], cell[1], 1)
        self.assertEqual(int(r.grid.occ[0, cell[1], cell[0]]), 1)
        # a stub too wide for the row is refused: the end point is 0.57 mm from land b, a 0.7 mm stub needs 0.25 + 0.35
        r.grid.occ[0, cell[1], cell[0]] = -2
        self.assertFalse(r._exact_end_ok(a, 0, end, cell, 0.7))
        # hard blocks and foreign copper always refuse
        r.grid.occ[0, cell[1], cell[0]] = -1
        self.assertFalse(r._exact_end_ok(a, 0, end, cell, 0.25))
        r.grid.occ[0, cell[1], cell[0]] = 2
        self.assertFalse(r._exact_end_ok(a, 0, end, cell, 0.25))
        self.assertFalse(r._exact_end_ok(a, 0, (0.0, 0.0), (0, 0), 0.25))  # outside the routable area


class PlanValidationTests(unittest.TestCase):
    def test_time_budget_and_checkpoint_keys(self):
        base = dict(board=dict(width=10, height=10), layers=['F.Cu'])
        self.assertEqual(gr.validate_plan(dict(base, time_budget_s=60, checkpoint='x.kicad_pcb'))['time_budget_s'], 60)
        with self.assertRaises(ValueError):
            gr.validate_plan(dict(base, time_budget_s=-1))
        with self.assertRaises(ValueError):
            gr.validate_plan(dict(base, checkpoint=7))
        with self.assertRaises(ValueError):
            gr.validate_plan(dict(base, unknown_key=1))


if __name__ == '__main__':
    unittest.main()
