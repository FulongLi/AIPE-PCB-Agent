"""Placement of the DAB-V1 boards from the floorplan requirement files (runs under KiCad's Python).

Every pose comes from requirements/floorplan_<board>.yaml, either directly (devices, heat sinks, terminals,
capacitor rows, connectors, holes) or through a named placement region searched by project_board.place_in_region
under the real courtyards and the pair-specific insulation gaps of rules.make_pair_gap.  Orientation of the
isolation packages is chosen by a predicate (hazardous pins towards the hazardous side), never by a literal angle.
The module also derives the copper plan of the power boards (pours, planes, keep-outs, per-net routing regions,
fine-pitch stub pads) and writes it with the placements to pcb/floorplan_<board>.json for routing.py and the
checkers.  Placement screening is geometric; native DRC remains mandatory.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from automation.dab_v1 import model as dab_model, requirements as rq, rules
from automation.kicad_tools.project_board import ProjectBoard, box_distance, place_in_region

PCB_DIR = rq.EXAMPLE / 'pcb'


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + '\n', encoding='utf-8')


def rect(x0, y0, x1, y1):
    return [float(x0), float(y0), float(x1), float(y1)]


def rect_poly(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def subtract_rects(base, cuts):
    """Axis-aligned difference base \\ union(cuts) as a list of rectangles (vertical slab decomposition)."""
    pieces = [list(base)]
    for cut in cuts:
        cx0, cy0, cx1, cy1 = cut
        out = []
        for x0, y0, x1, y1 in pieces:
            if cx0 >= x1 or cx1 <= x0 or cy0 >= y1 or cy1 <= y0:
                out.append([x0, y0, x1, y1])
                continue
            if cx0 > x0:
                out.append([x0, y0, cx0, y1])
            if cx1 < x1:
                out.append([cx1, y0, x1, y1])
            mx0, mx1 = max(x0, cx0), min(x1, cx1)
            if cy0 > y0:
                out.append([mx0, y0, mx1, cy0])
            if cy1 < y1:
                out.append([mx0, cy1, mx1, y1])
        pieces = out
    return [p for p in pieces if p[2] - p[0] > 0.2 and p[3] - p[1] > 0.2]


class Placer:
    """Placement driver around a ProjectBoard with orientation predicates and anchor-based regions."""

    def __init__(self, req, board: str):
        self.req, self.board_key = req, board
        self.cfg = req.board(board)
        self.fp = req.floorplans[board]
        self.name = self.cfg['name']
        self.directory = rq.EXAMPLE / board
        self.parts = json.loads((rq.DESIGN / f'circuit_{board}.json').read_text(encoding='utf-8'))
        groups = json.loads((rq.DESIGN / f'groups_{board}.json').read_text(encoding='utf-8'))
        self.groups = groups['groups']
        self.by_ref = {p['ref']: p for p in self.parts}
        self.b = ProjectBoard(self.directory, self.name, self.parts, rq.DESIGN / f'schematic_mapping_{board}.json',
                              layers=self.cfg['layers'], thickness=self.cfg['thickness_mm'], stackup=[tuple(r) for r in self.cfg['stackup']])
        title = self.b.board.GetTitleBlock()
        title.SetRevision(rq.GENERATION)
        title.SetComment(0, rq.BANNER)
        for ref, fp in self.b.fp.items():  # schematic parity: the DNP flag of the model travels to the footprint attribute
            if self.by_ref[ref].get('dnp'):
                fp.SetAttributes(fp.GetAttributes() | self.b.pcb.FP_DNP)
        w, h = self.cfg['size_mm']
        self.b.outline([(0, 0), (w, 0), (w, h), (0, h)])
        self.domains = rules.power_domains(self.parts) if self.cfg['side'] != 'control' else {}
        pair = rules.make_pair_gap(req, board, self.domains)
        self.pair_gap = lambda a, z: pair(a, z)[0]
        self.copper_gap = lambda a, z: pair(a, z)[0]
        self.log = []

    # ----- geometry helpers --------------------------------------------------------------------
    def pads_of(self, ref):
        return {p.GetNumber(): (tuple(self.b.pcb.ToMM(p.GetPosition())), p.GetNetname()) for p in self.b.fp[ref].Pads() if p.GetNumber()}

    def place_centred(self, ref, cx, cy, angle=0, side='F'):
        """Place so that the courtyard centre lands on (cx, cy)."""
        self.b.place(ref, 0, 0, angle, side)
        box = self.b.box(ref)
        dx, dy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        return self.b.place(ref, cx - dx, cy - dy, angle, side)

    def orient(self, ref, cx, cy, predicate, angles=(0, 90, 180, 270), side='F'):
        """First angle whose placement satisfies predicate(pads dict) -> pose; raises when none does."""
        for angle in angles:
            self.place_centred(ref, cx, cy, angle, side)
            if predicate(self.pads_of(ref)):
                return self.b.placed[ref]
        raise ValueError(f'{ref}: no orientation satisfies the placement predicate at ({cx}, {cy})')

    def hv_pins_up(self, pins):
        def predicate(pads):
            hv = [pads[n][0][1] for n in pins if n in pads]
            lv = [xy[1] for n, (xy, _) in pads.items() if n not in pins]
            return hv and lv and max(hv) < min(lv)
        return predicate

    def nets_up(self, nets):
        def predicate(pads):
            up = [xy[1] for (xy, net) in pads.values() if net in nets]
            down = [xy[1] for (xy, net) in pads.values() if net not in nets]
            return up and down and max(up) < min(down)
        return predicate

    def nets_right(self, nets):
        def predicate(pads):
            right = [xy[0] for (xy, net) in pads.values() if net in nets]
            left = [xy[0] for (xy, net) in pads.values() if net not in nets]
            return right and left and min(right) > max(left)
        return predicate

    def pin_left(self, number):
        def predicate(pads):
            xs = [xy[0] for xy, _ in pads.values()]
            return abs(pads[number][0][0] - min(xs)) < 0.01 and (max(xs) - min(xs)) > (max(xy[1] for xy, _ in pads.values()) - min(xy[1] for xy, _ in pads.values()))
        return predicate

    def anchors(self, part):
        """Weighted pad targets of an unplaced part from already placed parts sharing its nets (V3 rule, generic)."""
        result = []
        ref, group = part['ref'], self.groups.get(part['ref'])
        for pin, net in part['nets'].items():
            if not net:
                continue
            matches = []
            for other in self.b.placed:
                if other == ref:
                    continue
                p = self.by_ref[other]
                same = self.groups.get(other) == group
                if not same and p['kind'] not in ('IC', 'DSP', 'Q', 'J'):
                    continue
                if not same and net in ('GND_CTRL', '3V3', '5V0', '12V_E', 'BUS_P', 'PGND'):
                    continue
                for q in self.b.fp[other].Pads():
                    if q.GetNetname() == net:
                        matches.append((other, q, 5 if same and p['kind'] in ('IC', 'Q') else 2 if same else .2))
            byref = {}
            for other, q, w in matches:
                byref.setdefault(other, []).append((q, w))
            for other, items in byref.items():
                if part['kind'] == 'C' and len(part['nets']) == 2 and self.by_ref[other]['kind'] in ('IC', 'Q'):
                    other_net = next((n for n in part['nets'].values() if n != net), None)
                    partners = [q for q in self.b.fp[other].Pads() if q.GetNetname() == other_net]
                    if partners:
                        q, w = min(items, key=lambda item: min(math.dist(self.b.pcb.ToMM(item[0].GetPosition()), self.b.pcb.ToMM(pp.GetPosition())) for pp in partners))
                        result.append((pin, tuple(self.b.pcb.ToMM(q.GetPosition())), w * 3))
                        continue
                for q, w in items:
                    result.append((pin, tuple(self.b.pcb.ToMM(q.GetPosition())), w / len(items)))
        return result

    def fill_region(self, refs, region, *, side='F', step=.25, gap=.25, extra_targets=None, label=''):
        """Place refs (bypass capacitors first, then large parts) into a region with insulation-aware pad gaps."""
        pending = [self.by_ref[r] for r in refs if r in self.b.fp and r not in self.b.placed]

        def rank(p):
            box = self.b.box(p['ref'])
            area = (box[2] - box[0]) * (box[3] - box[1])
            return (0 if p['kind'] == 'C' and p['value'].startswith('100n') else 1 if area > 12 else 2, -area, p['ref'])
        pending.sort(key=rank)
        for p in pending:
            targets = self.anchors(p) + list((extra_targets or {}).get(p['ref'], []))
            try:
                place_in_region(self.b, p['ref'], region, targets, step=step, gap=gap, pad_gap=self.pair_gap, side=side)
            except ValueError as exc:
                self.log.append(dict(ref=p['ref'], region=region, label=label, error=str(exc)[:200]))
                raise
        return len(pending)

    def tag_of(self, part):
        for net in part['nets'].values():
            if not net:
                continue
            for tag in dab_model.TAGS:
                if net.endswith('_' + tag) or net == f'FLT_{tag}_N':
                    return tag
        return None

    def is_hv(self, part):
        return any(n in self.domains for n in part['nets'].values() if n)

    # ----- power boards --------------------------------------------------------------------------
    def place_power(self) -> dict:
        fp, b = self.fp, self.b
        comp = self.req.components
        side = self.cfg['side']
        row = fp['switch_row']
        hv_max, selv_min, ic_y = fp['barrier']['hv_max_y'], fp['barrier']['selv_min_y'], fp['barrier']['ic_centre_y']
        devices = {}
        for ref, role, x, angle in zip(row['refs'], row['roles'], row['x'], row['angle']):
            self.place_centred(ref, x, row['y'], angle)
            devices[role] = dict(ref=ref, x=x, pads=self.pads_of(ref))
        for hs in fp['heatsinks']:
            self.place_centred(hs['ref'], hs['x'], hs['y'], 0)
        lb = fp['left_block']
        for ref, (x, y) in lb['terminals'].items():
            self.place_centred(ref, x, y, 0)
        for ref, (x, y) in lb['film_caps'].items():
            self.orient(ref, x, y, self.nets_right({'BUS_P'}), angles=(lb['film_angle'], (lb['film_angle'] + 180) % 360, 90, 270))
        sw_a, sw_b, rb = fp['sw_a'], fp['sw_b'], fp['right_block']
        self.place_centred(sw_a['terminal']['ref'], sw_a['terminal']['x'], sw_a['terminal']['y'], 0)
        self.place_centred(rb['ac_b_terminal']['ref'], rb['ac_b_terminal']['x'], rb['ac_b_terminal']['y'], 0)
        # DC-link ceramics: alternate orientation so that neighbouring pads carry the same net
        hf = [p['ref'] for p in self.parts if self.groups.get(p['ref']) == 'dc_link' and p['footprint'].startswith('Capacitor_SMD')]
        slots = fp['device_row']['hf_cap_slots_x']
        for index, (ref, x) in enumerate(zip(hf, slots)):
            self.orient(ref, x, fp['device_row']['hf_cap_y'], lambda pads, even=index % 2 == 0: (pads['1'][0][0] < pads['2'][0][0]) == even, angles=(0, 180))
        # DC-blocking capacitors (primary): electrode 1 (SW_B) towards the top strip
        blk = [p['ref'] for p in self.parts if self.groups.get(p['ref']) == 'ac_path' and p['kind'] == 'C' and 'CBLK' in p['footprint']]
        for ref, x in zip(blk, rb['dc_block_caps']['x']):
            self.orient(ref, x, rb['dc_block_caps']['y'], self.nets_up({'SW_B'}), angles=(rb['dc_block_caps']['angle'], (rb['dc_block_caps']['angle'] + 180) % 360))
        # DESAT diodes in the device row: cathode (drain net) at desat_y, anode towards the island
        desat_pos = {}
        for role, dx in zip(row['roles'], fp['device_row']['desat_dx']):
            x = devices[role]['x'] + dx
            diode = next(p['ref'] for p in self.parts if self.groups.get(p['ref']) == f'desat_{role}' and p['kind'] == 'D' and 'DO-41' in p['footprint'])
            drain = dab_model.ROLE_NETS[role][0]
            self.orient(diode, x, fp['device_row']['desat_y'] + 5.08, self.nets_up({drain}), angles=(90, 270))
            desat_pos[role] = dict(ref=diode, x=x, cathode=self.pads_of(diode)['1'][0], anode=self.pads_of(diode)['2'][0])
        # barrier ICs: islands (driver and bias module), sensing amplifier/modulator, sense bias, Hall sensor
        drv_mpn, bias_mpn = comp['gate_driver']['mpn'], comp['isolated_bias']['mpn']
        islands = {}
        for role in row['roles']:
            xd = devices[role]['x']
            driver = next(p['ref'] for p in self.parts if p.get('island') == role and p['mpn'] == drv_mpn)
            bias = next(p['ref'] for p in self.parts if p.get('island') == role and p['mpn'] == bias_mpn)
            self.orient(driver, xd + fp['islands']['driver_dx'], ic_y, self.hv_pins_up({str(n) for n in range(1, 9)}))
            self.orient(bias, xd + fp['islands']['bias_dx'], ic_y, self.hv_pins_up({str(n) for n in range(19, 37)}))
            hw = fp['islands']['half_width']
            islands[role] = dict(driver=driver, bias=bias, x=xd, hv=rect(xd - hw, fp['islands']['hv_y'][0], xd + hw, fp['islands']['hv_y'][1]),
                                 selv=rect(xd - hw, fp['islands']['selv_y'][0], xd + hw, fp['islands']['selv_y'][1]))
        barrier = {p.get('barrier'): p['ref'] for p in self.parts if p.get('barrier')}
        self.orient(barrier['vsense'], rb['barrier_ics']['U_VSENSE'], ic_y, self.hv_pins_up({'1', '2', '3', '4'}))
        if 'vmod' in barrier:
            self.orient(barrier['vmod'], rb['barrier_ics']['U_VMOD'], ic_y, self.hv_pins_up({'1', '2', '3', '4'}))
        sbias = next(p['ref'] for p in self.parts if p.get('island') == 'S')
        self.orient(sbias, rb['barrier_ics']['U_SBIAS'], ic_y, self.hv_pins_up({str(n) for n in range(19, 37)}))
        hall_in = 'XF_B' if side == 'primary' else 'SW_B'
        self.orient(barrier['hall'], rb['barrier_ics']['U_HALL'], ic_y,
                    lambda pads: self.hv_pins_up({'1', '2'})(pads) and pads['1'][0][0] > pads['2'][0][0])
        # harness header horizontal with pin 1 on the left, mounting holes
        hr = fp['selv']['harness']
        self.orient(hr['ref'], hr['x'], hr['y'], self.pin_left('1'), angles=(hr['angle'], (hr['angle'] + 180) % 360, 0, 180))
        holes = [p['ref'] for p in self.parts if p['kind'] == 'H' and p['footprint'].startswith('MountingHole')]
        for ref, (x, y) in zip(holes, fp['mounting_holes']):
            b.place(ref, x, y, 0)
        # bleeder chain on the back side under the film capacitors
        bl = [p['ref'] for p in self.parts if self.groups.get(p['ref']) == 'bleeder']
        x0, x1 = lb['bleeder_row']['x']
        for i, ref in enumerate(bl):  # chain order BUS_P -> PGND runs from the BUS_P pad column (right) to the PGND column (left)
            x = x1 - 2.0 - (x1 - x0 - 4.0) * i / max(1, len(bl) - 1)
            self.orient(ref, x, lb['bleeder_row']['y'], lambda pads, i=i, n=len(bl): (pads['1'][0][0] > pads['2'][0][0]), angles=(0, 180), side=lb['bleeder_row']['side'])
        # regions for everything else
        placed_count = 0
        for role in row['roles']:
            isl = islands[role]
            hv_refs = [p['ref'] for p in self.parts if self.groups.get(p['ref']) in (f'driver_{role}', f'desat_{role}', f'bias_{role}') and self.is_hv(p)]
            selv_refs = [p['ref'] for p in self.parts if (self.groups.get(p['ref']) in (f'driver_{role}', f'desat_{role}', f'bias_{role}') and not self.is_hv(p))
                         or (self.groups.get(p['ref']) == 'harness' and self.tag_of(p) == role)]
            gate = devices[role]['pads']['4'][0]
            extra = {r: [('2', gate, 6)] for r in hv_refs if self.by_ref[r]['value'] in ('2', '2.0') and self.by_ref[r]['kind'] == 'R'}
            placed_count += self.fill_region(hv_refs, isl['hv'], extra_targets=extra, label=f'island {role} HV')
            placed_count += self.fill_region(selv_refs, isl['selv'], label=f'island {role} SELV')
        ladder_refs = [p['ref'] for p in self.parts if self.groups.get(p['ref']) == 'voltage_sense' and self.is_hv(p) and p['kind'] in ('R', 'C') and
                       any((n or '').startswith(('VDIV', 'MDIV', 'VADC', 'VMOD')) or n == 'BUS_P' for n in p['nets'].values())]
        sense_hv = [p['ref'] for p in self.parts if self.groups.get(p['ref']) in ('voltage_sense', 'bias_S') and self.is_hv(p) and p['ref'] not in ladder_refs
                    and p['kind'] not in ('IC',)]
        sense_selv = [p['ref'] for p in self.parts if self.groups.get(p['ref']) in ('voltage_sense', 'bias_S', 'ac_path') and not self.is_hv(p) and p['kind'] not in ('IC', 'C') or
                      (self.groups.get(p['ref']) in ('voltage_sense', 'bias_S', 'ac_path') and not self.is_hv(p) and p['kind'] == 'C' and 'CBLK' not in p['footprint'])]
        placed_count += self.fill_region(ladder_refs, rb['ladder_region'], label='ladder')
        placed_count += self.fill_region(sense_hv, rb['sense_iso_region'], label='sense iso')
        placed_count += self.fill_region(sense_selv, rb['selv_region'], label='sense SELV')
        left_refs = [p['ref'] for p in self.parts if self.groups.get(p['ref']) == 'temperature']
        bulk_refs = [p['ref'] for p in self.parts if self.groups.get(p['ref']) in ('aux_rails', 'harness') and p['ref'] not in self.b.placed and self.tag_of(p) is None]
        placed_count += self.fill_region(left_refs, fp['selv']['left_region'], label='temperature')
        placed_count += self.fill_region(bulk_refs, fp['selv']['bulk_region'], label='bulk')
        missing = [r for r in self.b.fp if r not in self.b.placed]
        if missing:
            raise ValueError(f'unplaced parts: {missing}')
        plan = self.copper_plan(devices, islands, desat_pos, barrier, sbias)
        plan.update(islands={k: dict(driver=v['driver'], bias=v['bias'], hv=v['hv'], selv=v['selv']) for k, v in islands.items()},
                    desat=desat_pos, devices={k: dict(ref=v['ref'], x=v['x']) for k, v in devices.items()})
        self.label_board(side)
        return plan

    def copper_plan(self, devices, islands, desat_pos, barrier, sbias) -> dict:
        """Pours, planes, keep-outs, net regions and stub pads of a power board, from the floorplan numbers."""
        fp, cfg = self.fp, self.cfg
        side = cfg['side']
        row, dr, lb, sa, sb, rb = fp['switch_row'], fp['device_row'], fp['left_block'], fp['sw_a'], fp['sw_b'], fp['right_block']
        W, H = cfg['size_mm']
        py0, py1 = dr['pour_y']
        hs_bases = [rect(h['x'] - h['width'] / 2, h['y'] - h['depth'] / 2, h['x'] + h['width'] / 2, h['y'] + h['depth'] / 2) for h in fp['heatsinks']]
        zones = {}

        def add(net, layer, r, priority=1):
            zones.setdefault(net, {}).setdefault(layer, []).append(rect_poly(r))
        pad = lambda role, n: devices[role]['pads'][n][0]
        # BUS_P: left block pour (minus heat-sink bases on F.Cu), island at the second BUS_P lead, DESAT tongues
        for r0 in lb['bus_p_pour']:
            for r in subtract_rects(rect(*r0), hs_bases):
                add('BUS_P', 'F.Cu', r, 2)
            add('BUS_P', 'B.Cu', rect(*r0), 2)
        bh_d = pad('BH', '1')
        island_b = rect(bh_d[0] - 2.0, py0, bh_d[0] + 11.0, dr['desat_y'] + 1.5)
        add('BUS_P', 'F.Cu', island_b, 2)
        add('BUS_P', 'B.Cu', rect(bh_d[0] - 2.0, py0, bh_d[0] + 11.0, py1), 2)
        for role in ('AH', 'BH'):
            cx, cy = desat_pos[role]['cathode']
            add('BUS_P', 'F.Cu', rect(cx - 2.0, py1 - 0.5, cx + 2.0, cy + 1.5), 2)
        # PGND: left block bottom pour, device-row span between the two PGND leads
        for r0 in lb['bus_n_pour']:
            add('PGND', 'F.Cu', rect(*r0), 2)
            add('PGND', 'B.Cu', rect(*r0), 2)
        al_s, bl_s = pad('AL', '2'), pad('BL', '2')
        add('PGND', 'F.Cu', rect(al_s[0] - 2.0, py0, bl_s[0] + 2.0, py1), 2)
        # SW_A: F.Cu lead band, B.Cu lead region + top strip + terminal
        sa_pad = rect(sa['pad_region']['x'][0], sa['pad_region']['y'][0], sa['pad_region']['x'][1], sa['pad_region']['y'][1])
        add('SW_A', 'F.Cu', rect(sa_pad[0], py0, sa_pad[2], py1), 3)
        add('SW_A', 'B.Cu', sa_pad, 3)
        add('SW_A', 'B.Cu', rect(sa['strip']['x'][0], sa['strip']['y'][0], sa['strip']['x'][1], sa['strip']['y'][1]), 3)
        tx, ty = sa['terminal']['x'], sa['terminal']['y']
        add('SW_A', 'B.Cu', rect(tx - 8, max(1.0, ty - 8), tx + 8, ty + 8), 3)
        al_desat = desat_pos['AL']['cathode']
        add('SW_A', 'F.Cu', rect(al_desat[0] - 2.0, py1 - 0.5, al_desat[0] + 2.0, al_desat[1] + 1.5), 3)
        # SW_B: F.Cu lead band, B.Cu lead region + top strip + capacitor feed (+ sensor feed on the secondary)
        sb_pad = rect(sb['pad_region']['x'][0], sb['pad_region']['y'][0], sb['pad_region']['x'][1], sb['pad_region']['y'][1])
        add('SW_B', 'F.Cu', rect(sb_pad[0], py0, sb_pad[2], py1), 3)
        add('SW_B', 'B.Cu', sb_pad, 3)
        add('SW_B', 'B.Cu', rect(sb['strip']['x'][0], sb['strip']['y'][0], sb['strip']['x'][1], sb['strip']['y'][1]), 3)
        feed = rect(sb['cap_feed']['x'][0], sb['cap_feed']['y'][0], sb['cap_feed']['x'][1], sb['cap_feed']['y'][1])
        bl_desat = desat_pos['BL']['cathode']
        add('SW_B', 'F.Cu', rect(bl_desat[0] - 2.0, py1 - 0.5, bl_desat[0] + 2.0, bl_desat[1] + 1.5), 3)
        xf = rect(rb['xf_b_pour']['x'][0], rb['xf_b_pour']['y'][0], rb['xf_b_pour']['x'][1], rb['xf_b_pour']['y'][1])
        if side == 'primary':
            add('SW_B', 'B.Cu', feed, 3)
            for layer in ('F.Cu', 'B.Cu'):
                add('XF_B', layer, xf, 3)
        else:
            add('SW_B', 'B.Cu', rect(feed[0], feed[1], feed[2], xf[3]), 3)
            add('SW_B', 'F.Cu', rect(feed[0], 44.0, feed[2], xf[3]), 3)
        # AC_B: Hall-sensor output bar to the terminal (F.Cu and In1.Cu)
        riser = rect(rb['ac_b_riser']['x'][0], rb['ac_b_riser']['y'][0], rb['ac_b_riser']['x'][1], rb['ac_b_riser']['y'][1])
        for layer in ('F.Cu', 'In1.Cu'):
            add('AC_B', layer, riser, 3)
        # laminated bus planes under the device row and the film block, excluding the switch-node copper
        px0, px1 = dr['plane_x']
        pyy0, pyy1 = dr['plane_y']
        grow = 1.0
        excl = [rect(sa_pad[0] - grow, sa_pad[1] - grow, sa_pad[2] + grow, sa_pad[3] + grow),
                rect(sa['strip']['x'][0] - grow, 0, sa['strip']['x'][1] + grow, sa['strip']['y'][1] + grow),
                rect(tx - 9, 0, tx + 9, ty + 9),
                rect(sb_pad[0] - grow, sb_pad[1] - grow, sb_pad[2] + grow, sb_pad[3] + grow),
                rect(sb['strip']['x'][0] - grow, 0, W, sb['strip']['y'][1] + grow)]
        base = rect(px0, pyy0, px1, pyy1)
        film_block = rect(*lb['plane_block'])
        for r in subtract_rects(base, excl) + subtract_rects(film_block, [base]):
            add('BUS_P', 'In1.Cu', r, 1)
            add('PGND', 'In2.Cu', r, 1)
        ic_boxes = [self.b.placed[r]['bbox'] for r in (barrier['vsense'], barrier.get('vmod'), sbias) if r]
        sense_x1 = max(box[2] for box in ic_boxes) + 1.0
        add('PGND', 'In2.Cu', rect(rb['ladder_region'][0] - 2, rb['ladder_region'][1], sense_x1, fp['barrier']['hv_max_y']), 1)
        # F.Cu / B.Cu PGND pours connect the 0.65 mm pitch VEE pins of the sensing bias module and the amplifier GND1 pins
        sense_pour = rect(rb['sense_iso_region'][0], rb['sense_iso_region'][1], sense_x1, fp['barrier']['hv_max_y'])
        amp_pour = rect(rb['ladder_region'][0] - 2, fp['barrier']['hv_max_y'] - 6.0, rb['sense_iso_region'][0], fp['barrier']['hv_max_y'])
        for layer in ('F.Cu', 'B.Cu'):
            add('PGND', layer, sense_pour, 2)
            add('PGND', layer, amp_pour, 2)
        gp = fp['selv']['ground_plane']
        ground = dict(net='GND_CTRL', layers=[gp['layer']], polygon=rect_poly(rect(gp['x'][0], gp['y'][0], gp['x'][1], gp['y'][1])), priority=0, clearance=0.25)
        # keep-outs: barrier band (no copper crossing), heat-sink bases (no tracks on F.Cu, no vias anywhere)
        keepouts = [dict(layer=None, rect=rect(0, fp['barrier']['hv_max_y'], W, fp['barrier']['selv_min_y']), vias=True)]
        for r in hs_bases:
            keepouts.append(dict(layer='F.Cu', rect=r, vias=True))
            keepouts.append(dict(layer=None, rect=rect(r[0], r[1], r[2], r[3]), vias=True, zone=True))
        # no vias within 1 mm of the net-tie star pads (KiCad hole-clearance treats net-tie pads as foreign copper)
        for ref, part in self.by_ref.items():
            if part['footprint'].startswith('NetTie') and ref in self.b.placed:
                x, y = self.b.placed[ref]['x'], self.b.placed[ref]['y']
                keepouts.append(dict(layer=None, rect=rect(x - 1.3, y - 1.0, x + 1.3, y + 1.0), vias=True, zone=True))
        # per-net routing regions
        regions = {}
        selv = [rect(1.0, fp['barrier']['selv_min_y'], W - 1.0, H - 1.0)]
        for role, isl in islands.items():
            xd = isl['x']
            dx = desat_pos[role]['x']
            x0, x1 = min(isl['hv'][0] - 2.0, dx - 3.0), max(isl['hv'][2] + 2.0, dx + 3.0)
            box = [rect(x0, py0 - 1.0, x1, fp['barrier']['hv_max_y'])]
            for net, (dom, _, _) in self.domains.items():
                if dom == f'island_{role.lower()}':
                    regions[net] = {'F.Cu': box, 'B.Cu': box}
        sense_box = [rect(rb['ladder_region'][0] - 2.0, rb['ladder_region'][1] - 2.0, sense_x1 + 1.0, fp['barrier']['hv_max_y'])]
        bleed_box = [rect(*lb['plane_block'])]
        bleeders = {n for p in self.parts if self.groups.get(p['ref']) == 'bleeder' for n in p['nets'].values() if n}
        for net, (dom, _, _) in self.domains.items():
            if net in bleeders and net not in ('BUS_P', 'PGND'):
                regions[net] = {'F.Cu': bleed_box, 'B.Cu': bleed_box}
            elif dom == 'sense_iso' or dom.startswith('ladder'):
                regions[net] = {'F.Cu': sense_box, 'B.Cu': sense_box}
        for net in {n for p in self.parts for n in p['nets'].values() if n} - set(self.domains):
            if net != 'GND_CTRL':
                regions[net] = {'F.Cu': selv, 'In2.Cu': selv, 'B.Cu': selv}
        # fine-pitch rows: exact outward stubs for every SMD IC pad of a routed net (pour nets connect through the pours
        # or through the escape vias of the default fan-out)
        pour_nets = set(zones) | {ground['net']}
        stubs = []
        for ref, part in self.by_ref.items():
            if part['kind'] != 'IC' or ref not in self.b.fp:
                continue
            cx, cy = self.b.pcb.ToMM(self.b.fp[ref].GetPosition())
            for q in self.b.fp[ref].Pads():
                if q.GetAttribute() != self.b.pcb.PAD_ATTRIB_SMD or not q.GetNumber() or not q.GetNetname() or q.GetNetname() in pour_nets:
                    continue
                x, y = self.b.pcb.ToMM(q.GetPosition())
                if abs(y - cy) > abs(x - cx):
                    direction = (0, 1 if y > cy else -1)
                else:
                    direction = (1 if x > cx else -1, 0)
                stubs.append([ref, q.GetNumber(), self.req.routing[self.board_key]['exact_stub_mm'], list(direction)])
        # DC-link ceramics: one deterministic via below each pad (clear of the other electrode and of the DESAT diodes),
        # joined to the pad by a short stub; the laminated planes connect the vias
        hf = [p['ref'] for p in self.parts if self.groups.get(p['ref']) == 'dc_link' and p['footprint'].startswith('Capacitor_SMD')]
        via_d, via_drill = self.req.board(self.board_key)['via_mm']
        pre_tracks, pre_vias, skip_pads = [], [], []
        drop = dr['hf_cap_band_y'][1] + via_d / 2 + 0.3
        for ref in hf:
            for q in self.b.fp[ref].Pads():
                x, y = self.b.pcb.ToMM(q.GetPosition())
                net = q.GetNetname()
                pre_tracks.append(dict(net=net, layer='F.Cu', a=[round(x, 3), round(y, 3)], b=[round(x, 3), round(drop, 3)], width=0.3))  # 0.5 left 3.95 mm to the other electrode (4.0 mm rule)
                pre_vias.append(dict(net=net, xy=[round(x, 3), round(drop, 3)], diameter=via_d, drill=via_drill))
                skip_pads.append([ref, q.GetNumber()])
        return dict(zones=zones, ground=ground, keepouts=keepouts, regions=regions, exact_stub_pads=stubs,
                    pre_routed=dict(tracks=pre_tracks, vias=pre_vias), skip_pads=skip_pads,
                    heatsink_bases=hs_bases, barrier=fp['barrier'])

    # ----- control board -------------------------------------------------------------------------
    def place_control(self) -> dict:
        fp, b = self.fp, self.b
        for ref, (x, y, angle) in fp['fixed'].items():
            if ref in ('J2', 'J3'):
                self.orient(ref, x, y, self.pin_left('1'), angles=(angle, (angle + 180) % 360, 0, 180))
            elif ref == 'J1':
                self.place_centred(ref, x, y, angle)
            else:
                self.place_centred(ref, x, y, angle)
        holes = [p['ref'] for p in self.parts if p['kind'] == 'H']
        for ref, (x, y) in zip(holes, fp['mounting_holes']):
            b.place(ref, x, y, 0)
        regions = fp['regions']
        mapping = fp['group_regions']
        order = ['card_bypass', 'aux_entry', 'buck_5v', 'ldo_3v3', 'supervisor', 'receivers', 'adc_conditioning', 'comparators', 'fault_logic', 'latch',
                 'pwm_gating', 'can', 'rs485', 'jtag', 'indicators', 'harness_filters']
        by_region = {}
        for p in self.parts:
            if p['ref'] in b.placed:
                continue
            region = mapping.get(self.groups.get(p['ref']))
            if region is None:
                raise ValueError(f'{p["ref"]}: group {self.groups.get(p["ref"])!r} has no placement region')
            by_region.setdefault(region, []).append(p['ref'])
        for region in order:
            refs = by_region.pop(region, [])
            self.fill_region(refs, regions[region], label=region, step=.25, gap=.25)
        if by_region:
            raise ValueError(f'regions without an order entry: {sorted(by_region)}')
        missing = [r for r in b.fp if r not in b.placed]
        if missing:
            raise ValueError(f'unplaced parts: {missing}')
        W, H = self.cfg['size_mm']
        gp = fp['ground_plane']
        plan = dict(zones={}, ground=dict(net='GND_CTRL', layers=[gp['layer']], polygon=rect_poly(rect(gp['x'][0], gp['y'][0], gp['x'][1], gp['y'][1])), priority=0, clearance=0.2),
                    keepouts=[], regions={}, exact_stub_pads=[], pre_routed=dict(tracks=[], vias=[]), skip_pads=[], heatsink_bases=[], barrier=None)
        stubs = []
        for ref, part in self.by_ref.items():
            if part['kind'] != 'IC' or ref not in b.fp:
                continue
            cx, cy = b.pcb.ToMM(b.fp[ref].GetPosition())
            for q in b.fp[ref].Pads():
                if q.GetAttribute() != b.pcb.PAD_ATTRIB_SMD or not q.GetNumber() or not q.GetNetname() or q.GetNetname() == 'GND_CTRL':
                    continue
                x, y = b.pcb.ToMM(q.GetPosition())
                direction = (0, 1 if y > cy else -1) if abs(y - cy) > abs(x - cx) else (1 if x > cx else -1, 0)
                stubs.append([ref, q.GetNumber(), self.req.routing['control']['exact_stub_mm'], list(direction)])
        plan['exact_stub_pads'] = stubs
        b.label(f'DAB-V1 CONTROL - {self.cfg["title"].split(" - ")[-1]}', (80, 2.5), size=1.0)
        b.label('NOT QUALIFIED', (151, 112), size=0.8)
        return plan

    def label_board(self, side):
        W, H = self.cfg['size_mm']
        self.b.label(f'DAB-V1 {side.upper()} POWER - {self.cfg["bus_voltage_V"]} V BUS', (50, H - 9), size=1.5)
        self.b.label('HAZARDOUS VOLTAGE - ENGINEERING REVIEW ONLY - NOT HARDWARE QUALIFIED', (240, H - 9), size=1.0)
        self.b.label('REINFORCED BARRIER BAND (8 mm reference, to be reviewed) - NO COPPER', (36, 74), size=0.8)

    def finish(self, plan: dict) -> Path:
        path = self.b.save()
        record = dict(board=self.board_key, project=self.name, generation=rq.GENERATION, outline_mm=self.cfg['size_mm'], layers=self.cfg['layers'],
                      placements=self.b.placed, pads=self.b.pads(), plan=plan, placement_log=self.log,
                      note='Placement is geometric (courtyards, pad boxes, insulation pair gaps); native DRC decides.')
        save_json(PCB_DIR / f'floorplan_{self.board_key}.json', record)
        return path


def build(req, board: str) -> Path:
    placer = Placer(req, board)
    plan = placer.place_control() if board == 'control' else placer.place_power()
    path = placer.finish(plan)
    print(f'{board}: placed {len(placer.b.placed)} parts -> {path}', flush=True)
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--board', choices=rq.BOARDS, required=True)
    args = parser.parse_args(argv)
    build(rq.load(), args.board)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
