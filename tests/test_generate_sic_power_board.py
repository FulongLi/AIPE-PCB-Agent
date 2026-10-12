"""Tests for the V2 power-board generator (automation.kicad_tools.generate_sic_power_board).

Pure parts only (host interpreter, no pcbnew): floorplan tables cover the model, the pour / via-group / rule-area
geometry, the barrier polygon, the routing regions (every routed net confined to an island or the SELV strip, no island
region touching a foreign HV group), the fine-pitch escape plan on a synthetic DWN-36 row, the routing plan validated by
grid_router.validate_plan, the PE pre-route and the chain stubs. The end-to-end build (placement, routing, kicad-cli
DRC) is the generator's own run, recorded under examples/.../verification; it is not repeated here.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.kicad_tools import generate_sic_power_board as g  # noqa: E402
from automation.kicad_tools import grid_router as gr  # noqa: E402


def synthetic_row(ref, x0, y, nets, pitch=0.65, size=(1.85, 0.45), layer='F', centre_y=145.0):
    """Pad records of one along-x fine-pitch row (pads 1..n west -> east), as pad_boxes() would return them."""
    boxes = {}
    for i, net in enumerate(nets, 1):
        x = x0 + (i - 1) * pitch
        w, h = size[1], size[0]  # rotated package: the long pad side runs along y
        boxes[(ref, str(i))] = dict(ref_pad=f'{ref}.{i}', bbox=[x - w / 2, y - h / 2, x + w / 2, y + h / 2], net=net, smd=True, xy=(x, y),
                                    size=(w, h), layer=layer, centre=(x0 + pitch * (len(nets) - 1) / 2, centre_y))
    return boxes


class FloorplanTests(unittest.TestCase):
    def test_every_model_part_has_exactly_one_placement_source(self):
        parts = g.load_parts()
        refs = {p['ref'] for p in parts}
        fixed, assigned = set(g.FIXED), set(g.ASSIGN_BY_REF)
        self.assertEqual(refs - fixed - assigned, set())
        self.assertEqual((fixed | assigned) - refs, set())
        self.assertEqual(fixed & assigned, set())
        for region in g.ASSIGN_BY_REF.values():
            self.assertIn(region, g.REGIONS)

    def test_barrier_parts_sit_on_the_barrier_line_with_separated_courtyards(self):
        half = {'U1': 8.9, 'U3': 8.9, 'U2': 9.3, 'U4': 9.3, 'U5': 9.3, 'U6': 6.0, 'U7': 6.0, 'U10': 8.3}
        spans = sorted((g.FIXED[r][0] - half[r], g.FIXED[r][0] + half[r], r) for r in g.BARRIER_REFS)
        for (a0, a1, ra), (b0, b1, rb) in zip(spans, spans[1:]):
            self.assertLessEqual(a1, b0, (ra, rb))
        for r in g.BARRIER_REFS:
            self.assertEqual(g.FIXED[r][1], g.BARRIER_Y)

    def test_hv_zone_polygons_stay_in_the_hv_area_and_selv_pours_in_the_strip(self):
        for z in g.zone_plan():
            ys = [p[1] for p in z['polygon']]
            if z['net'] in g.HV_ZONE_NETS or z['net'] in g.KELVIN_NETS or z['net'] in ('G_H', 'G_L'):
                self.assertLessEqual(max(ys), g.HV_LIMIT_Y, z['net'])
            else:
                self.assertGreaterEqual(min(ys), g.SELV_START_Y, z['net'])
        nets = {z['net'] for z in g.zone_plan()}
        self.assertTrue({'VIN', 'PGND', 'SW', 'VOUT', 'VOUT_L', 'KS_H', 'KS_L', 'GND_CTRL', '3V3'} <= nets)
        self.assertNotIn('12V_PROT', nets)  # routed, not poured

    def test_via_groups_and_rule_areas(self):
        total = {}
        for grp in g.via_groups():
            total[grp['net']] = total.get(grp['net'], 0) + grp['count'][0] * grp['count'][1]
        self.assertGreaterEqual(total['SW'], 24)
        self.assertGreaterEqual(total['VIN'], 24)
        self.assertGreaterEqual(total['VOUT'], 24)
        names = [a['name'] for a in g.rule_areas()]
        self.assertIn('HEATSINK_HV_KEEPOUT', names)
        self.assertEqual(sum(n.startswith('M4_STANDOFF') for n in names), 6)
        self.assertEqual(sum(n.startswith('L1_STANDOFF') for n in names), 4)
        self.assertTrue(g.l1_circle_clear([171.7, 130.8, 176.3, 133.2]))
        self.assertFalse(g.l1_circle_clear([199.0, 128.8, 201.5, 131.2]))

    def test_iso_barrier_polygon_notches_round_the_pad_rows(self):
        rows = [(90.0, 139.3, 100.0, 141.4), (90.0, 148.6, 100.0, 150.7)]
        poly = g.iso_barrier_polygon(rows)
        ys = [p[1] for p in poly]
        self.assertAlmostEqual(max(ys), 150.0)
        self.assertAlmostEqual(min(ys), 140.0)
        def has(x, y):
            return any(abs(px - x) < 1e-6 and abs(py - y) < 1e-6 for px, py in poly)
        self.assertTrue(has(89.7, 141.7))  # HV notch dips 0.3 mm below the HV pad row
        self.assertTrue(has(100.3, 148.3))  # SELV notch rises 0.3 mm above the SELV pad row


class RoutingRegionTests(unittest.TestCase):
    def boxes(self):
        boxes = {}
        boxes.update(synthetic_row('U2', 72.0, 140.025, ['VEE_H'] * 9 + ['VDD_H'] * 2 + ['VEE_H'] * 2 + ['HS_RLIM', 'HS_FB_VEE', 'HS_FB_VDD', 'VEE_H', 'VEE_H']))
        boxes.update(synthetic_row('U2', 72.0, 149.975, ['GNDP_H', 'GNDP_H', 'PG_BIAS_H_N', 'BIAS_EN_F', 'GNDP_H', '12V_BIAS_H', '12V_BIAS_H'] + ['GNDP_H'] * 11))
        boxes[('R19', '1')] = dict(ref_pad='R19.1', bbox=[95, 131, 96, 132], net='HS_OUTH', smd=True, xy=(95.5, 131.5), size=(1, 1), layer='B', centre=(96, 131.5))
        boxes[('R71', '1')] = dict(ref_pad='R71.1', bbox=[150, 170, 151, 171], net='VIN_OUTP', smd=True, xy=(150.5, 170.5), size=(1, 1), layer='F', centre=(151, 170.5))
        boxes[('TP12', '1')] = dict(ref_pad='TP12.1', bbox=[175, 153, 177, 155], net='SPARE_D1', smd=True, xy=(176.0, 154.0), size=(2, 2), layer='F', centre=(176.0, 154.0))
        return boxes

    def test_regions_cover_islands_and_strip_and_keep_the_wall(self):
        regions = g.route_regions(self.boxes())
        self.assertEqual(set(g.HS_NETS) - set(regions), set())
        self.assertEqual(set(g.LS_NETS) - set(regions), set())
        for net in g.HS_NETS:
            self.assertIs(regions[net], regions['G_H'])
        self.assertIn('SPARE_D1', regions)  # a SELV net gets the strip region
        for net in g.AMC_PAIR_NETS:  # r20 (LR-26) mechanism: a listed AMC1311 output pair runs on F.Cu only (the list is empty: attempt not kept)
            self.assertEqual(set(regions[net]), {'F.Cu'})
        for net in g.LS_GATE_LOOP_NETS:  # r20 (LR-24) mechanism: a listed LS gate-loop net runs on B.Cu only (the list is empty: attempt not kept)
            self.assertEqual(set(regions[net]), {'B.Cu'})
        self.assertEqual(regions['G_L']['B.Cu'], regions['LS_GK']['B.Cu'])
        self.assertNotIn('VIN', regions)  # HV pour nets are never routed
        self.assertNotIn('PE', regions)
        hs, ls = regions['G_H'], regions['G_L']
        wall_w, wall_e = g.ISLAND_WALL_X
        for layer, rects in hs.items():
            for r in rects:
                self.assertLessEqual(r[2], wall_w + 1e-9, (layer, r))  # HS copper west of the wall
        for layer, rects in ls.items():
            for r in rects:
                self.assertGreaterEqual(r[0], wall_e - 1e-9, (layer, r))  # LS copper east of the wall
        for layer, rects in regions['SPARE_D1'].items():
            for r in rects:
                self.assertGreaterEqual(r[1], 148.7 - 1e-9, (layer, r))  # SELV copper never north of the SELV pad rows (notch 0.3 mm above them)
        self.assertEqual(regions['SPARE_D1']['In2.Cu'], [[0.5, g.SELV_COPPER_MIN_Y, g.WIDTH - 0.5, g.HEIGHT - 0.5]])  # In2 under the strip carries SELV tracks (the 3V3 pour is a post-route zone)
        self.assertTrue(hs['In2.Cu'])  # In2 is routable inside the islands only

    def test_region_rects_keep_three_millimetres_from_the_foreign_through_pads(self):
        regions = g.route_regions(self.boxes())
        q1_vin = (87.0 - 0.955, 123.75, 87.0 + 0.955, 128.25)
        q2_pgnd = (120.08 - 0.955, 123.75, 120.08 + 0.955, 128.25)

        def distance(rect, pad):
            dx = max(pad[0] - rect[2], rect[0] - pad[2], 0.0)
            dy = max(pad[1] - rect[3], rect[1] - pad[3], 0.0)
            return (dx * dx + dy * dy) ** 0.5
        for layer in ('F.Cu', 'B.Cu'):
            for r in regions['G_H'][layer]:
                if r[1] >= g.HV_COPPER_MAX_Y - 1e-9:
                    continue  # barrier pad-row notch
                self.assertGreaterEqual(distance(r, q1_vin), 3.0 + 0.5, (layer, r))
                self.assertGreaterEqual(distance(r, q2_pgnd), 3.0 + 0.5, (layer, r))


class EscapePlanTests(unittest.TestCase):
    def test_fine_pitch_rows_get_bars_with_one_via_and_fans_for_singles(self):
        boxes = synthetic_row('U2', 72.0, 140.025, ['VEE_H'] * 9 + ['VDD_H'] * 2 + ['VEE_H'] * 2 + ['HS_RLIM', 'HS_FB_VEE', 'HS_FB_VDD', 'VEE_H', 'VEE_H'])
        plan = g.fine_pitch_escapes(boxes, {'U2': object()}, power_nets={'PGND'})
        bars = [t for t in plan['tracks'] if t['width'] > 0.3]
        self.assertEqual(len(bars), 4)  # VEE x9, VDD x2, VEE x2, VEE x2
        bar_vias = [v for v in plan['vias'] if v['net'] in ('VEE_H', 'VDD_H')]
        self.assertEqual(len(bar_vias), 4)
        for via in bar_vias:
            self.assertTrue(via['port'])
            self.assertAlmostEqual(via['xy'][1], 140.025 - 0.925 - g.BAR_VIA_DEPTH_MM, places=3)  # HV side escapes north
        # the three singles between the bars (pads 14, 15, 16) escape through a fan: the outer ones run a leg sideways at FAN_DEPTH_MM,
        # the middle one continues FAN_STEP_MM deeper; every pad ends in its own via and none is left to the router's stub escape
        self.assertEqual(plan['exact'], [])
        self.assertEqual(plan['exact_vias'], [])
        fan = {v['net']: v for v in plan['vias'] if v['net'] not in ('VEE_H', 'VDD_H')}
        self.assertEqual(set(fan), {'HS_RLIM', 'HS_FB_VEE', 'HS_FB_VDD'})
        x14, x15, x16 = (72.0 + 13 * 0.65, 72.0 + 14 * 0.65, 72.0 + 15 * 0.65)
        d1 = 140.025 - 0.925 - g.FAN_DEPTH_MM
        self.assertAlmostEqual(fan['HS_RLIM']['xy'][0], x14 - g.FAN_LEG_MM, places=3); self.assertAlmostEqual(fan['HS_RLIM']['xy'][1], d1, places=3)
        self.assertAlmostEqual(fan['HS_FB_VEE']['xy'][0], x15, places=3); self.assertAlmostEqual(fan['HS_FB_VEE']['xy'][1], d1 - g.FAN_STEP_MM, places=3)
        self.assertAlmostEqual(fan['HS_FB_VDD']['xy'][0], x16 + g.FAN_LEG_MM, places=3); self.assertAlmostEqual(fan['HS_FB_VDD']['xy'][1], d1, places=3)
        legs = [t for t in plan['tracks'] if t['net'] in fan and t['a'][1] == t['b'][1]]
        self.assertEqual(len(legs), 2)  # the two outer pads' legs
        skipped = {tuple(p) for p in plan['skip']}
        self.assertEqual(len(skipped), 18)  # every pad of the row has pre-routed escape copper
        self.assertEqual(plan['widths']['VEE_H'], 0.25)
        pair = next(v for v in plan['vias'] if v['net'] == 'VDD_H')
        self.assertAlmostEqual(pair['xy'][0], 72.0 + 9.5 * 0.65, places=3)
        long = next(v for v in plan['vias'] if v['net'] == 'VEE_H')
        self.assertAlmostEqual(long['xy'][0], 72.0 + 4 * 0.65, places=3)

    def test_selv_side_fine_rows_fan_out_including_the_plane_pads(self):
        boxes = synthetic_row('U5', 150.0, 165.0, ['VIN_SENSE', 'VIN_AMP_N', 'VIN_AMP_P', 'GND_CTRL'], pitch=0.65, size=(1.62, 0.5), centre_y=160.0)  # a barrier package's SELV row
        plan = g.fine_pitch_escapes(boxes, {'U5': object()}, power_nets={'GND_CTRL'})
        self.assertEqual(plan['exact'], [])  # a group of four singles: the fan serves every pad, the plane pad's via reaches its pour
        vias = {v['net']: v for v in plan['vias']}
        self.assertEqual(set(vias), {'VIN_SENSE', 'VIN_AMP_N', 'VIN_AMP_P', 'GND_CTRL'})
        d1 = 165.0 + 0.81 + g.FAN_DEPTH_MM
        self.assertAlmostEqual(vias['VIN_SENSE']['xy'][1], d1, places=3); self.assertAlmostEqual(vias['VIN_SENSE']['xy'][0], 150.0 - g.FAN_LEG_MM, places=3)
        self.assertAlmostEqual(vias['GND_CTRL']['xy'][1], d1, places=3); self.assertAlmostEqual(vias['GND_CTRL']['xy'][0], 150.0 + 3 * 0.65 + g.FAN_LEG_MM, places=3)
        self.assertAlmostEqual(vias['VIN_AMP_N']['xy'][1], d1 + g.FAN_LEG_MM, places=3); self.assertAlmostEqual(vias['VIN_AMP_N']['xy'][0], 150.65 - g.FAN_LEG_MM, places=3)
        self.assertAlmostEqual(vias['VIN_AMP_P']['xy'][1], d1 + g.FAN_LEG_MM, places=3); self.assertAlmostEqual(vias['VIN_AMP_P']['xy'][0], 151.3 + g.FAN_LEG_MM, places=3)
        self.assertEqual(plan['issues'], [])

    def test_vssop_columns_fan_out_along_the_pad_axis(self):
        boxes = {}
        for i, net in enumerate(['VIN_SENSE', 'VIN_AMP_N', 'VIN_AMP_P', 'GND_CTRL'], 1):  # U8's west column: pads along y, escaping west
            x, y = 163.387, 168.025 + (i - 1) * 0.65
            boxes[('U8', str(i))] = dict(ref_pad=f'U8.{i}', bbox=[x - 0.8125, y - 0.25, x + 0.8125, y + 0.25], net=net, smd=True, xy=(x, y), size=(1.625, 0.5),
                                         layer='F', centre=(165.5, 169.0))
        plan = g.fine_pitch_escapes(boxes, {'U8': object()}, power_nets={'GND_CTRL'})
        vias = {v['net']: v for v in plan['vias']}
        d1 = 163.387 - 0.8125 - g.FAN_DEPTH_STRIP_MM
        self.assertAlmostEqual(vias['VIN_SENSE']['xy'][0], d1, places=3); self.assertAlmostEqual(vias['VIN_SENSE']['xy'][1], 168.025 - g.FAN_LEG_MM, places=3)
        self.assertAlmostEqual(vias['VIN_AMP_N']['xy'][0], d1 - g.FAN_LEG_MM, places=3); self.assertAlmostEqual(vias['VIN_AMP_N']['xy'][1], 168.675 - g.FAN_LEG_MM, places=3)
        self.assertAlmostEqual(vias['VIN_AMP_P']['xy'][0], d1 - g.FAN_LEG_MM, places=3); self.assertAlmostEqual(vias['VIN_AMP_P']['xy'][1], 169.325 + g.FAN_LEG_MM, places=3)
        self.assertAlmostEqual(vias['GND_CTRL']['xy'][0], d1, places=3); self.assertAlmostEqual(vias['GND_CTRL']['xy'][1], 169.975 + g.FAN_LEG_MM, places=3)
        self.assertEqual({tuple(p) for p in plan['skip']}, {('U8', '1'), ('U8', '2'), ('U8', '3'), ('U8', '4')})
        for t in plan['tracks']:
            self.assertEqual(t['layer'], 'F.Cu'); self.assertEqual(t['width'], 0.25)
        self.assertIn('U8', g.FAN_OBSTACLE_REFS)  # the fan copper becomes placer obstacles once U8 is placed
        obstacles = g.escape_obstacles(boxes, refs=('U8',))
        self.assertEqual(len([o for o in obstacles if o[0].startswith('ESCVIA')]), 4)
        self.assertTrue(all(o[1][2] <= 163.387 + 0.13 for o in obstacles))  # nothing east of the pad centres: the fan stubs start inside the pads and run west

    def test_connector_pins_all_escape_south_with_links_for_same_net_columns(self):
        boxes = {}
        for i, (x, y, net) in enumerate([(211.0, 160.0, '12V_PROT'), (211.0, 157.46, '12V_PROT'), (208.46, 160.0, 'RELAY_ON'), (208.46, 157.46, 'GND_CTRL'),
                                         (205.92, 160.0, '3V3'), (205.92, 157.46, 'FLT_H_N')], 1):
            boxes[('J7', str(i))] = dict(ref_pad=f'J7.{i}', bbox=[x - 0.85, y - 0.85, x + 0.85, y + 0.85], net=net, smd=False, xy=(x, y), size=(1.7, 1.7),
                                         layer='F', centre=(180.0, 158.73))
        boxes[('U1', '13')] = dict(ref_pad='U1.13', bbox=[96, 149, 97, 150], net='FLT_H_N', smd=True, xy=(96.5, 149.6), size=(1, 1), layer='F', centre=(96, 145))
        specs, links, skip = g.connector_stubs(boxes, power_nets={'GND_CTRL', '3V3'})
        by_pad = {(ref, num): (length, tuple(direction), offset, layer) for ref, num, length, direction, offset, layer in specs}
        # every pin leaves southwards on B.Cu: outer-row pins straight, inner-row pins jogging west between the outer pins; the two
        # 12V_PROT pins of one column are linked and the outer one carries the stub; plane pins (GND_CTRL) escape like the others
        self.assertEqual(set(by_pad), {('J7', '1'), ('J7', '3'), ('J7', '4'), ('J7', '5'), ('J7', '6')})
        self.assertEqual(g.CONNECTOR_NORTH_PINS['J7'], ('30', '32', '36'))  # the three north-bound inner pins (not in this synthetic socket) escape north
        for num in ('1', '3', '5'):
            self.assertEqual(by_pad[('J7', num)][1:], ((0, 1), 0.0, 'B.Cu'))
            self.assertAlmostEqual(by_pad[('J7', num)][0], g.CONNECTOR_STUB_END_Y['outer'] - 160.0 - 0.85)
        self.assertEqual(by_pad[('J7', '6')][1:], ((0, 1), -g.CONNECTOR_JOG_MM, 'B.Cu'))  # inner signal pin: jog west, deeper via
        self.assertAlmostEqual(by_pad[('J7', '6')][0], g.CONNECTOR_STUB_END_Y['inner'] - 157.46 - 0.85)
        self.assertEqual(by_pad[('J7', '4')][1:], ((0, 1), -g.CONNECTOR_JOG_MM, 'B.Cu'))  # inner plane pin: jog west, shallow plane via
        self.assertAlmostEqual(by_pad[('J7', '4')][0], g.CONNECTOR_STUB_END_Y['inner_plane'] - 157.46 - 0.85)
        self.assertGreaterEqual(g.CONNECTOR_STUB_END_Y['inner_plane'] - 0.3 - (160.0 + 0.85), 0.3)  # plane via ring clears the outer pads by the class clearance
        self.assertEqual(skip, [['J7', '2']])
        self.assertEqual(len(links), 1)
        self.assertEqual((links[0]['net'], links[0]['layer'], links[0]['a'], links[0]['b']), ('12V_PROT', 'B.Cu', [211.0, 157.46], [211.0, 160.0]))
        self.assertGreater(g.CONNECTOR_STUB_END_Y['outer'], 160.0 + 0.85 + 0.3 + 0.3)  # the stub-end via ring clears the pad row by the class clearance
        self.assertGreaterEqual(g.CONNECTOR_STUB_END_Y['inner'] - g.CONNECTOR_STUB_END_Y['outer'], 1.2)  # the two via rows are >= 1.75 mm apart centre to centre
        self.assertGreaterEqual(g.SELV_SOCKET_PARTS_Y, g.CONNECTOR_STUB_END_Y['inner'] + 0.3 + 0.3 + 0.25)  # parts start below the inner via row

    def test_barrier_coarse_rows_escape_through_stubs_with_vias_other_coarse_rows_are_left_to_the_fanout(self):
        boxes = synthetic_row('U1', 90.0, 140.35, ['KS_H', 'DESAT_H_OC', 'KS_H', 'HS_OUTH'], pitch=1.27, size=(2.05, 0.6))
        plan = g.fine_pitch_escapes(boxes, {'U1': object()}, power_nets=set())
        self.assertEqual(plan['tracks'], [])  # no adjacent same-net pads: no bars
        short, long = g.EXACT_STUB_HV_MM
        self.assertEqual(plan['exact'], [['U1', '1', short], ['U1', '2', long], ['U1', '3', short], ['U1', '4', long]])  # 1.27 mm barrier row: alternating HV stubs
        self.assertEqual(plan['exact_vias'], [['U1', '1'], ['U1', '2'], ['U1', '3'], ['U1', '4']])  # with a via at every stub end
        self.assertEqual(plan['vias'], [])
        boxes = synthetic_row('U6', 179.095, 139.55, ['5V_ISO', 'VIN_DIV', 'PGND', 'PGND'], pitch=1.27, size=(1.8, 0.6))
        plan = g.fine_pitch_escapes(boxes, {'U6': object()}, power_nets={'PGND'})
        self.assertEqual(plan['exact'], [['U6', '1', 0.3], ['U6', '2', 0.3]])  # AMC1311 HV row: short stubs, the via just beyond the pad end
        self.assertAlmostEqual(plan['vias'][0]['xy'][1], 139.55 - 0.9 - g.BAR_VIA_DEPTH_BY_REF['U6'], places=3)
        boxes = synthetic_row('U8', 150.0, 165.0, ['VIN_SENSE', 'VIN_AMP_N', 'VIN_AMP_P', 'GND_CTRL'], pitch=1.27, size=(1.5, 0.6), centre_y=160.0)
        plan = g.fine_pitch_escapes(boxes, {'U8': object()}, power_nets={'GND_CTRL'})
        self.assertEqual(plan['exact'], [])  # a 1.27 mm row of a strip part keeps the via fanout
        self.assertEqual(plan['vias'], [])
        self.assertEqual(g.inward_escape_pads(boxes), [])  # no part escapes inward by default

    def test_connector_port_boxes_follow_the_stubs(self):
        boxes = {}
        for i, (x, y, net) in enumerate([(211.0, 160.0, '12V_PROT'), (211.0, 157.46, '12V_PROT'), (208.46, 160.0, 'RELAY_ON'), (208.46, 157.46, 'FLT_H_N')], 1):
            boxes[('J7', str(i))] = dict(ref_pad=f'J7.{i}', bbox=[x - 0.85, y - 0.85, x + 0.85, y + 0.85], net=net, smd=False, xy=(x, y), size=(1.7, 1.7), layer='F', centre=(205.0, 158.73))
        stubs, links, skip = g.connector_stubs(boxes, power_nets=set())
        keepouts = g.connector_port_keepouts(boxes, stubs)
        self.assertEqual(len(keepouts), len(stubs))
        by_net = {k['net']: k for k in keepouts}
        half, depth = g.CONNECTOR_PORT_BOX
        south = by_net['RELAY_ON']  # outer-row pin going south
        self.assertAlmostEqual(south['rect'][1], g.CONNECTOR_STUB_END_Y['outer'] - 0.3, places=3)
        self.assertAlmostEqual(south['rect'][3], g.CONNECTOR_STUB_END_Y['outer'] + depth, places=3)
        flt = by_net['FLT_H_N']  # inner-row pin: jogs west, port half a pitch deeper
        self.assertAlmostEqual((flt['rect'][0] + flt['rect'][2]) / 2, 208.46 - g.CONNECTOR_JOG_MM, places=3)
        self.assertAlmostEqual(flt['rect'][1], g.CONNECTOR_STUB_END_Y['inner'] - 0.3, places=3)

    def test_escape_obstacles_cover_the_barrier_fans(self):
        boxes = synthetic_row('U2', 72.0, 140.025, ['VEE_H'] * 2 + ['HS_FB_VDD', 'HS_FB_VEE', 'HS_RLIM'] + ['VEE_H'] * 2)
        obstacles = g.escape_obstacles(boxes)
        names = {name.split(':')[0] for name, _, _ in obstacles}
        self.assertEqual(names, {'ESC', 'ESCVIA'})  # no corridor here: VEE_H owns both bar vias of this row
        vias = [box for name, box, gap in obstacles if name.startswith('ESCVIA')]
        self.assertEqual(len(vias), 5)  # two bar vias and three fan vias
        corridors = [box for name, box, gap in obstacles if name.startswith('ESCCOL')]
        self.assertEqual(len(corridors), 0)  # VEE_H has two bar vias in this row: no exit corridor (only a net's single bar via gets one)
        boxes2 = synthetic_row('U2', 72.0, 140.025, ['VEE_H'] * 2 + ['VDD_H'] * 2 + ['HS_RLIM'] + ['VEE_H'] * 2)
        obstacles2 = g.escape_obstacles(boxes2)
        self.assertEqual({name.split(':')[0] for name, _, _ in obstacles2}, {'ESC', 'ESCVIA', 'ESCCOL'})
        corridors = [box for name, box, gap in obstacles2 if name.startswith('ESCCOL')]
        self.assertEqual(len(corridors), 1)  # the single VDD_H bar via
        for box in corridors:
            self.assertAlmostEqual(box[3] - box[1], g.BAR_EXIT_CORRIDOR_MM, places=3)
        for name, box, gap in obstacles:
            self.assertLess(box[3], g.ISLAND_TOP_Y + 20)
            self.assertGreaterEqual(gap[0], g.ESC_GAP)

    def test_grid_soft_conflicts_record_the_newer_owner_for_the_rip_up(self):
        grid = gr.Grid(40, 40, 2, grid=0.25, margin_cells=1)
        grid.box(grid.occ[0], [2.0, 2.0, 3.0, 3.0], 0.0, 5, alt=grid.alt[0])  # pad halo of net 5
        grid.segment(grid.occ[0], (0.0, 2.5), (10.0, 2.5), 0.3, 7, alt=grid.alt[0])  # a net-7 track across the board, through the halo
        self.assertEqual(int(grid.occ[0][10, 10]), -2); self.assertEqual(int(grid.alt[0][10, 10]), 7)  # overlap: soft block, newer owner recorded
        self.assertEqual(int(grid.occ[0][10, 30]), 7); self.assertEqual(int(grid.occ[0][20, 10]), 0)
        grid.box(grid.occ[0], [2.0, 2.0, 2.3, 2.3], 0.0, -1, alt=grid.alt[0])  # a hard keep-out wins over the soft block
        self.assertEqual(int(grid.occ[0][9, 9]), -1); self.assertEqual(int(grid.alt[0][9, 9]), -1)
        grid.box(grid.occ[1], [2.0, 2.0, 3.0, 3.0], 0.0, 5)
        grid.segment(grid.occ[1], (0.0, 2.5), (10.0, 2.5), 0.3, 7)
        self.assertEqual(int(grid.occ[1][10, 10]), -1)  # without an alt view the classic hard conflict
        crossing = grid.astar_soft((10, 2, 0), (10, 30, 0), 9, layers=(0,), rippable={7})
        self.assertIsNotNone(crossing)  # the soft search crosses the wall where net 7 (rippable) owns or co-owns the cells
        self.assertIsNone(grid.astar_soft((10, 2, 0), (10, 30, 0), 9, layers=(0,), rippable={5}))  # net 7 not rippable: the wall stands

    def test_plan_pins_the_kelvin_gate_and_rail_nets_first_in_every_trial(self):
        self.assertIn('signal_pinned', gr.PLAN_KEYS)
        self.assertEqual(g.SIGNAL_PINNED[:4], ['KS_H', 'KS_L', 'G_H', 'G_L'])
        self.assertNotIn('3V3', g.SIGNAL_PINNED)  # 3V3 first made the strip worse (r13): it keeps its early place in the plan order only
        self.assertLess(g.SIGNAL_ORDER.index('3V3'), g.SIGNAL_ORDER.index('PWM_'))
        self.assertAlmostEqual(gr.point_segment_distance(0.0, 1.0, -1.0, 0.0, 1.0, 0.0), 1.0)
        self.assertAlmostEqual(gr.point_segment_distance(3.0, 0.0, -1.0, 0.0, 1.0, 0.0), 2.0)

    def test_3v3_is_routed_and_its_in2_pour_is_a_post_route_zone(self):
        z = [z for z in g.zone_plan() if z['net'] == '3V3']
        self.assertEqual(len(z), 1)
        self.assertTrue(z[0].get('post_route')); self.assertEqual(z[0]['layer'], 'In2.Cu')
        self.assertEqual(g.NET_RULES['3V3']['width'], 0.25)  # stitching tracks; the In2 pour carries the distribution
        self.assertIn('3V3', g.SIGNAL_ORDER)


class PlanTests(unittest.TestCase):
    def test_routing_plan_validates_and_confines_every_net(self):
        rules = {k: dict(v) for k, v in g.NET_RULES.items()}
        boxes = RoutingRegionTests().boxes()
        for net, region in g.route_regions(boxes).items():
            rules.setdefault(net, {})['region'] = region
        keepouts = g.router_keepouts(boxes, g.rule_areas() + [dict(name='ISO_BARRIER', layers=g.COPPER_LAYERS, polygon=g.iso_barrier_polygon(g.barrier_pad_rows(boxes)),
                                                                   tracks=True, vias=True, pours=True)])
        plan = g.routing_plan(Path('x.kicad_pcb'), [], [], [], keepouts, net_rules=rules, exact_stub_pads=[['R62', '2', 3.6, [0, 1], 0.25]], direct_nets=['G_H'])
        self.assertEqual(gr.validate_plan(plan), plan)
        self.assertEqual(plan['layers'], ['F.Cu', 'In2.Cu', 'B.Cu'])
        self.assertEqual(len(plan['directions']), 3)
        for net in g.HV_ZONE_NETS:
            self.assertFalse(plan['power'][net]['stubs'])
        self.assertLessEqual(set(g.SKIP_ESCAPE_NETS), set(plan['fanout']['skip_nets']))
        self.assertNotIn('PGND', plan['fanout']['skip_nets'])  # PGND pads get in-pad vias / bar vias and are skipped per pad
        self.assertNotIn('KS_H', plan['power'])  # Kelvin pours are added after the signal stage
        self.assertEqual(plan['fanout']['escape_layer'], 'B.Cu')
        self.assertEqual(plan['fanout']['direct_nets'], ['G_H'])
        self.assertEqual(plan['net_rules']['G_H']['region'], g.route_regions(boxes)['G_H'])
        self.assertEqual(plan['net_rules']['PE']['clearance'], 5.3)
        self.assertEqual(plan['net_rules']['VIN']['clearance'], 3.0)
        in2_zone = [k for k in keepouts if k.get('zone')]
        self.assertTrue(in2_zone and all(k['layer'] == 'In2.Cu' for k in in2_zone))
        self.assertTrue(any(k['layer'] == 'F.Cu' and k['net'] == 'VIN' and k['vias'] for k in keepouts))

    def test_pe_pre_route_and_chain_stubs(self):
        boxes = {
            ('H1', '1'): dict(ref_pad='H1.1', bbox=[39.5, 23.2, 48.1, 31.8], net='PE', smd=False, xy=(43.8, 27.5), size=(8.6, 8.6), layer='F', centre=(43.8, 27.5)),
            ('C18', '2'): dict(ref_pad='C18.2', bbox=[41.0, 17.5, 44.0, 20.5], net='PE', smd=False, xy=(42.5, 19.0), size=(3.0, 3.0), layer='F', centre=(37.5, 19.0)),
            ('R14', '2'): dict(ref_pad='R14.2', bbox=[47.8, 62.4, 49.4, 65.6], net='PE', smd=True, xy=(48.6, 64.0), size=(1.6, 3.2), layer='B', centre=(45.65, 64.0)),
            ('R16', '2'): dict(ref_pad='R16.2', bbox=[48.1, 55.16, 49.7, 56.76], net='PE', smd=True, xy=(48.9, 55.96), size=(3.2, 1.6), layer='B', centre=(48.9, 53.0)),
            ('R1', '2'): dict(ref_pad='R1.2', bbox=[49.2, 4.9, 50.8, 8.1], net='BLD_IN_1', smd=True, xy=(50.0, 6.5), size=(1.6, 3.2), layer='F', centre=(47.0, 6.5)),
            ('R2', '1'): dict(ref_pad='R2.1', bbox=[51.0, 4.9, 52.6, 8.1], net='BLD_IN_1', smd=True, xy=(51.8, 6.5), size=(1.6, 3.2), layer='F', centre=(54.8, 6.5)),
        }
        tracks, skip = g.pe_pre_route(boxes)
        self.assertEqual(len(skip), 4)
        self.assertTrue(all(t['layer'] == 'B.Cu' and t['net'] == 'PE' for t in tracks))
        self.assertTrue(any(abs(t['a'][0] - g.PE_SPINE_X) < 1e-6 and abs(t['b'][0] - g.PE_SPINE_X) < 1e-6 for t in tracks))  # the spine
        self.assertTrue(any(t['a'][1] == 55.96 and t['b'][1] == 64.0 for t in tracks))  # R16 pad straight down to R14's row
        stub = next(t for t in tracks if t['a'] == [42.5, 19.0])  # C18's PE pad: vertical stub ending inside the stud pad
        self.assertEqual(stub['b'][0], 42.5)
        self.assertLess(((stub['b'][0] - 43.8) ** 2 + (stub['b'][1] - 27.5) ** 2) ** 0.5, 4.3)
        chain, issues = g.hv_chain_tracks(boxes)
        self.assertEqual(issues, [])
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]['net'], 'BLD_IN_1')
        self.assertAlmostEqual(chain[0]['a'][0], 50.0 + 0.8 - g.CHAIN_TRACK_INSET)
        self.assertAlmostEqual(chain[0]['b'][0], 51.8 - 0.8 + g.CHAIN_TRACK_INSET)

    def test_v21_style_blocks_validate_and_keep_the_v2_search(self):
        # V2.1: both style blocks validate; the default block is one of them (the generator default is what build_power() routes with);
        # eps stays at the V2 0.01 on this 0.125 mm grid (eps 0.02 changed the V2 search: KS_L 88 -> 131 mm in the 2026-10-12 attempt B)
        for block in (g.ROUTING_STYLE_V21, g.ROUTING_STYLE_OCTILINEAR):
            cfg = gr.normalise_style(block)
            self.assertEqual(cfg['eps'], gr.EPS)
            self.assertEqual(cfg['simplify'], 'octilinear')
            self.assertTrue(cfg['arcs'])
            self.assertIn('PE', cfg['straight_nets'])
        self.assertTrue(gr.normalise_style(g.ROUTING_STYLE_V21)['diagonal'])
        self.assertFalse(gr.normalise_style(g.ROUTING_STYLE_OCTILINEAR)['diagonal'])
        self.assertIn(g.ROUTING_STYLE, (g.ROUTING_STYLE_V21, g.ROUTING_STYLE_OCTILINEAR))
        plan = g.routing_plan(Path('x.kicad_pcb'), [], [], [], [], style=g.ROUTING_STYLE)
        self.assertEqual(plan['style'], g.ROUTING_STYLE)
        self.assertNotIn('style', g.routing_plan(Path('x.kicad_pcb'), [], [], [], [], style={}))  # {} = the V2 plan

    def test_write_outputs_scratch_directory_keeps_the_example_folders_untouched(self):
        import tempfile
        result = dict(board=str(Path(__file__)), placements={}, silkscreen=[], slots=[], rule_areas=[], placement_issues=[], seconds=1.0,
                      routing_plan={'grid': g.GRID}, report=dict(unresolved=[], status='x', tracks=0, vias=0, zones=0), board_counts={})
        before = {path: path.stat().st_mtime_ns for path in (g.DESIGN_DIR / 'placement_power.json', g.DESIGN_DIR / 'routing_plan_power.json',
                                                              g.VERIFICATION_DIR / 'routing_progress_power.json') if path.exists()}
        with tempfile.TemporaryDirectory() as tmp:
            g.write_outputs(result, Path(tmp))
            names = sorted(p.name for p in Path(tmp).iterdir())
            self.assertEqual(names, ['placement_power.json', 'routing_plan_power.json', 'routing_progress_power.json'])
            progress = json.loads((Path(tmp) / 'routing_progress_power.json').read_text(encoding='utf-8'))
            self.assertEqual(progress['stage'], 'routed')
            self.assertEqual(progress['status'], g.BANNER)
        for path, stamp in before.items():
            self.assertEqual(path.stat().st_mtime_ns, stamp, path)

    def test_stackup_and_manifest_helpers(self):
        self.assertEqual(g.stackup_text().count('(type "copper")'), 4)
        self.assertAlmostEqual(g.stackup_thickness_mm(), 2.0)
        self.assertEqual(g.snap(1.03), 1.0)
        self.assertTrue(g.boxes_overlap([0, 0, 1, 1], [0.5, 0.5, 2, 2]))
        self.assertFalse(g.boxes_overlap([0, 0, 1, 1], [1, 0, 2, 1]))
        with_json = json.dumps(g.zone_plan(), default=str)
        self.assertIn('"net": "KS_H"', with_json)


if __name__ == '__main__':
    unittest.main()
