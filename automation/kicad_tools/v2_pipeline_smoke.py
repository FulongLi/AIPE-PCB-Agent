"""End-to-end smoke of the V2 KiCad automation pipeline on a disposable mini half-bridge project.

The smoke runs the V2 modules in the order the real 400 V -> 200 V, 5 kW design will use them: a
shared-format part list carrying a "board" key (project_footprints.validate_pad_mapping, then
prepare_libraries for the power board only), project_schematic.generate_project (4-layer design rules,
HV / GATE / Default net classes and a generated .kicad_dru), kicad-cli ERC through run_check, a pcbnew
board built from the kicad-cli XML netlist (footprints loaded from the project libraries, SetPath from
schematic_mapping.json, deterministic placement, a 4-layer stackup injected as text, SaveBoard then
LoadBoard), grid_router.run_plan (fanout, critical gate nets, VIN / SW / VOUT zones on F.Cu and B.Cu,
PGND zones on the inner layers), kicad-cli DRC with --schematic-parity through run_check,
export_outputs.export (11 commands) and the ngspice behavioural simulation
(automation.simulation.buck_stage with its built-in example parameters).

Deterministic without KiCad: the part list, the placement table, the zone polygons and routing plan,
the design-rule text (pin-field exceptions are derived from pad geometry alone), spec validation and
the layout of the evidence summary. Requires native KiCad: everything that counts as evidence - ERC,
netlist export, pcbnew footprint loading, board save / load and zone fill, DRC with parity and the
exports; the simulation needs the ngspice shared library bundled with KiCad. Finding counts are read
from KiCad's JSON reports through run_check; nothing is waived and a missing tool is reported as a
failure, never as a pass.

Run: python -m automation.kicad_tools.v2_pipeline_smoke --output <scratch dir> [--evidence <json>]
     [--skip-simulation]. The board stage re-executes this file under KiCad's bundled Python when
pcbnew is not importable in the calling interpreter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # the board stage is re-executed by KiCad's Python with this file as a script
    sys.path.insert(0, str(ROOT))

from automation.kicad_tools import grid_router as gr  # noqa: E402  (numpy only at import time)
from automation.kicad_tools import project_footprints as pf  # noqa: E402
from automation.kicad_tools import project_schematic as ps  # noqa: E402
from automation.setup.detect_kicad import find_kicad_cli, read_config  # noqa: E402

NAME = 'AIPE_V2_Smoke'
TITLE = 'AIPE V2 pipeline smoke - SiC half bridge, toroid and DC-link film capacitor'
COMMENT = 'AUTOMATION SMOKE ONLY - NOT A CONVERTER DESIGN - HUMAN REVIEW REQUIRED'
WIDTH, HEIGHT = 120.0, 80.0
LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
EXPORT_LAYERS = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.SilkS,B.SilkS,F.Fab,Edge.Cuts'
HV_NETS = ('VIN', 'SW', 'VOUT')
GROUND = 'PGND'
HV_CLEARANCE, HV_TO_PGND, PIN_FIELD = 2.5, 3.0, 0.5
GATE_PATTERNS = ('G_*', 'GATE_*', 'KS_*')
CRITICAL = ['G_H', 'GATE_H', 'KS_H', 'G_L', 'GATE_L', 'KS_L']
DESIGN_RULES = {'min_clearance': 0.2, 'min_track_width': 0.2, 'min_via_diameter': 0.6, 'min_through_hole_diameter': 0.3,
                'min_hole_clearance': 0.25, 'min_copper_edge_clearance': 0.5}
NET_CLASSES = [dict(name='HV', clearance=HV_CLEARANCE, track_width=1.0, via_diameter=1.2, via_drill=0.6, nets=list(HV_NETS)),
               dict(name='GATE', clearance=0.2, track_width=0.5, via_diameter=0.8, via_drill=0.4, nets=list(GATE_PATTERNS))]
PAGES = {'01_power': 'Half bridge, toroid inductor and DC-link film capacitor',
         '02_driver': 'Isolated dual gate driver, bootstrap and control header',
         '03_mechanical': 'Heatsink envelope and mounting holes'}
FLAG_NETS = ['VIN', '12V', GROUND, 'BOOT_H']
# Stackup (mm) written into the saved board as text, as V1 did; pcbnew exposes no stackup mutation.
STACKUP = [('F.Cu', 'copper', 0.035), ('dielectric 1', 'prepreg', 0.2), ('In1.Cu', 'copper', 0.035),
           ('dielectric 2', 'core', 1.065), ('In2.Cu', 'copper', 0.035), ('dielectric 3', 'prepreg', 0.2), ('B.Cu', 'copper', 0.035)]
MODULES = {'project_footprints': 'automation/kicad_tools/project_footprints.py',
           'project_schematic': 'automation/kicad_tools/project_schematic.py',
           'grid_router': 'automation/kicad_tools/grid_router.py',
           'buck_stage': 'automation/simulation/buck_stage.py',
           'ngspice_runner': 'automation/simulation/ngspice_runner.py',
           'v2_pipeline_smoke': 'automation/kicad_tools/v2_pipeline_smoke.py',
           'run_check': 'automation/kicad_tools/run_check.py',
           'export_outputs': 'automation/kicad_tools/export_outputs.py'}
NOTES = [
    'Smoke circuit only: part values, the TO-247-4 pin order (G/D/S/KS in KiCad footprint pad order) and the bootstrap '
    'bias of the high-side channel are placeholders for exercising the pipeline, not V2 design decisions.',
    'HV net-class clearance 2.5 mm and the HV-to-PGND rule 3.0 mm cannot be met inside a TO-247-4 pin field (2.54 mm '
    'pitch); the generated .kicad_dru adds one explicit pin-field rule per such package, derived from pad geometry, '
    'instead of lowering the classes. The real design needs the same treatment plus a creepage review.',
    'HV nets are connected by zones only (no HV tracks or fanout vias); PGND reaches SMD pads through the fanout vias of '
    'the grid router.',
    'Signal nets may run on In1.Cu where PGND is poured; the fill yields to them. Layout quality is not assessed here.',
    'Router occupancy is conservative; kicad-cli DRC with schematic parity is the acceptance gate, not the router report.',
]

# --- deterministic model -------------------------------------------------------------------------------------


def pin_defs(text: str) -> dict:
    """V1 pin declaration syntax 'number:name:type ...' -> {number: {name, type}}."""
    return {n: dict(name=name, type=kind) for n, name, kind in (item.split(':') for item in text.split())}


TWO = pin_defs('1:1:passive 2:2:passive')
FET_PINS = pin_defs('1:G:input 2:D:passive 3:S:passive 4:KS:passive')
DRIVER_PINS = pin_defs('1:INA:input 2:INB:input 3:VCCI:power_in 4:GND:power_in 5:DIS:input 6:DT:passive 7:NC:no_connect '
                       '8:VCCI:power_in 9:VSSB:passive 10:OUTB:output 11:VDDB:power_in 12:NC:no_connect 13:NC:no_connect '
                       '14:VSSA:passive 15:OUTA:output 16:VDDA:power_in')
CUSTOM_NAMES = dict(toroid='L_Toroid_D40_P30_Flat', film='C_Film_41.5x20x39.5_P37.5x10.2', heatsink='HS_Envelope_50x10x35')


def custom_footprints() -> dict:
    """Custom AIPE footprints of the smoke: flat toroid, four-lead film capacitor and a heatsink envelope."""
    return {
        CUSTOM_NAMES['toroid']: pf.toroid_inductor_footprint(CUSTOM_NAMES['toroid'], 30, 2.6, 5.0, 40, 20, 6.5),
        CUSTOM_NAMES['film']: pf.film_capacitor_footprint(CUSTOM_NAMES['film'], 37.5, 41.5, 20, 39.5, 1.2, pins=4,
                                                          second_pitch_mm=10.2),
        CUSTOM_NAMES['heatsink']: pf.heatsink_envelope_footprint(CUSTOM_NAMES['heatsink'], 50, 10, 35,
                                                                 [(-20, 0, 3.2), (20, 0, 3.2)]),
    }


def _part(ref, value, footprint, nets, page, kind, pins=None, board='power', **extra):
    nets = {str(k): v for k, v in nets.items()}
    part = dict(ref=ref, value=value, footprint=footprint, nets=nets, page=page, kind=kind, mpn=extra.pop('mpn', ''),
                maker=extra.pop('maker', ''), source=extra.pop('source', ''),
                pins=pins or {n: dict(name=n, type='passive') for n in nets}, note=extra.pop('note', ''), xy=None, board=board)
    part.update(extra)
    return part


def build_parts() -> list[dict]:
    """Shared-format part list (V1 keys plus "board"): the power-board parts and one control-board mating header."""
    aipe = pf.CUSTOM_LIB
    header = {1: 'PWM_H', 2: GROUND, 3: 'PWM_L', 4: GROUND, 5: 'DIS', 6: GROUND, 7: '12V', 8: GROUND, 9: '12V', 10: GROUND}
    return [
        _part('Q1', 'C3M0021120K', 'Package_TO_SOT_THT:TO-247-4_Vertical', {1: 'G_H', 2: 'VIN', 3: 'SW', 4: 'KS_H'}, '01_power', 'Q',
              FET_PINS, mpn='C3M0021120K', maker='Wolfspeed', note='High-side SiC MOSFET; Kelvin source; verify pin order against the datasheet'),
        _part('Q2', 'C3M0021120K', 'Package_TO_SOT_THT:TO-247-4_Vertical', {1: 'G_L', 2: 'SW', 3: GROUND, 4: 'KS_L'}, '01_power', 'Q',
              FET_PINS, mpn='C3M0021120K', maker='Wolfspeed', note='Low-side SiC MOSFET; Kelvin source'),
        _part('C1', '1u/630V', 'Capacitor_SMD:C_2220_5750Metric', {1: 'VIN', 2: GROUND}, '01_power', 'C', TWO, note='DC-link ceramic snubber'),
        _part('C2', '1u/630V', 'Capacitor_SMD:C_2220_5750Metric', {1: 'VIN', 2: GROUND}, '01_power', 'C', TWO, note='DC-link ceramic snubber'),
        _part('L1', '267uH/30A', f'{aipe}:{CUSTOM_NAMES["toroid"]}', {1: 'SW', 2: 'VOUT'}, '01_power', 'L', TWO,
              note='Powder-core toroid lying flat, central insulated bolt'),
        _part('C4', '60u/500V film', f'{aipe}:{CUSTOM_NAMES["film"]}', {1: 'VOUT', 2: GROUND}, '01_power', 'C', TWO,
              note='Four-lead box film capacitor; leads 1,1 and 2,2 share pad numbers'),
        _part('U1', 'UCC21520DW', 'Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm',
              {1: 'PWM_H', 2: 'PWM_L', 3: '12V', 4: GROUND, 5: 'DIS', 6: GROUND, 7: None, 8: '12V', 9: 'KS_H', 10: 'GATE_H',
               11: 'BOOT_H', 12: None, 13: None, 14: 'KS_L', 15: 'GATE_L', 16: '12V'}, '02_driver', 'IC', DRIVER_PINS,
              mpn='UCC21520DW', maker='Texas Instruments', note='Isolated dual gate driver; channel B bootstrapped (smoke only)'),
        _part('R1', '4.7', 'Resistor_SMD:R_1206_3216Metric', {1: 'GATE_H', 2: 'G_H'}, '02_driver', 'R', TWO, note='High-side gate resistor'),
        _part('R2', '4.7', 'Resistor_SMD:R_1206_3216Metric', {1: 'GATE_L', 2: 'G_L'}, '02_driver', 'R', TWO, note='Low-side gate resistor'),
        _part('D1', 'US1M', 'Diode_SMD:D_SMA', {1: 'BOOT_H', 2: '12V'}, '02_driver', 'D', pin_defs('1:K:passive 2:A:passive'),
              note='Bootstrap diode; KiCad pad 1 = cathode'),
        _part('C3', '1u/50V', 'Capacitor_SMD:C_1210_3225Metric', {1: 'BOOT_H', 2: 'KS_H'}, '02_driver', 'C', TWO, note='Bootstrap capacitor'),
        _part('J1', 'CTRL 2x05', 'Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical', header, '02_driver', 'J',
              note='PWM, DIS, 12 V and ground from the control board'),
        _part('HS1', 'Heatsink 50x10x35', f'{aipe}:{CUSTOM_NAMES["heatsink"]}', {}, '03_mechanical', 'HEATSINK',
              note='Envelope only; isolated TO-247 mounting; rule area forbids tracks and vias under the base'),
        _part('H1', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, '03_mechanical', 'H'),
        _part('H2', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, '03_mechanical', 'H'),
        # Control-board mate of J1: shares the model but belongs to the other KiCad project, so both board filters skip it.
        _part('J2', 'CTRL 2x05', 'Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical', header, '02_driver', 'J',
              board='control', note='Control-board header (not part of the power project)'),
    ]


def power_parts(parts=None) -> list[dict]:
    """The parts of the power board (the only KiCad project the smoke generates)."""
    return pf.select_parts(parts or build_parts(), 'power')


# Placement in board mm (x, y, angle); the heatsink base sits behind the vertical TO-247 bodies.
PLACEMENT = {
    'Q2': (22.0, 36.0, 0), 'Q1': (46.0, 36.0, 0), 'R2': (16.0, 36.0, 0), 'R1': (40.0, 36.0, 0),
    'HS1': (39.0, 27.5, 0), 'U1': (36.0, 52.0, 0), 'C1': (50.0, 45.0, 270), 'C2': (57.0, 45.0, 270),
    'D1': (66.0, 50.0, 0), 'C3': (66.0, 54.0, 0), 'L1': (90.0, 26.0, 0), 'C4': (92.0, 62.0, 180),
    'J1': (8.0, 60.0, 0), 'H1': (5.0, 5.0, 0), 'H2': (116.0, 76.4, 0),
}
# Zone polygons (mm). SW takes the higher priority; VIN and SW meet only inside Q1's pin field.
VIN_POLYGON = [(50.1, 37.0), (52.1, 37.0), (52.1, 38.6), (60.5, 38.6), (60.5, 44.5), (48.5, 44.5), (48.5, 38.6), (50.1, 38.6)]
SW_POLYGON = [(25.0, 24.0), (78.0, 24.0), (78.0, 31.0), (54.6, 31.0), (54.6, 35.0), (52.6, 35.0), (52.6, 31.0), (28.1, 31.0),
              (28.1, 35.0), (26.1, 35.0), (26.1, 31.0), (25.0, 31.0)]
VOUT_POLYGON = [(102.0, 22.0), (113.0, 22.0), (113.0, 70.0), (102.0, 70.0)]
ZONES = {'VIN': dict(polygon=VIN_POLYGON, priority=1), 'SW': dict(polygon=SW_POLYGON, priority=2), 'VOUT': dict(polygon=VOUT_POLYGON, priority=1)}
GROUND_HOLES = [[(42.0, 30.5), (60.5, 30.5), (60.5, 41.5), (42.0, 41.5)], [(18.0, 30.5), (28.3, 30.5), (28.3, 41.5), (18.0, 41.5)]]
# Router reservations (rect, net, inflate_mm) on F.Cu and B.Cu; inflation keeps other nets off the narrow zone legs.
ZONE_KEEPOUTS = [((48.5, 38.6, 60.5, 44.5), 'VIN', 0.5), ((50.1, 37.0, 52.1, 38.6), 'VIN', 3.0),
                 ((25.0, 24.0, 78.0, 31.0), 'SW', 0.0), ((52.6, 31.0, 54.6, 35.0), 'SW', 2.0),
                 ((26.1, 31.0, 28.1, 35.0), 'SW', 2.0), ((102.0, 22.0, 113.0, 70.0), 'VOUT', 0.5)]
HEATSINK_BASE = (14.0, 22.5, 64.0, 32.5)
KS_H_STUB = ((1.84, 0.0), (1.84, -3.0))  # offsets from Q1 pad 4: escape the SW pad's clearance band, then the port via
SIGNAL_ORDER = ['PWM_', 'DIS', 'BOOT_H', '12V']


# --- design rules -------------------------------------------------------------------------------------------


def pad_geometry(parts, custom=None, source=None) -> dict:
    """Footprint id -> pad records (number, net-independent geometry) for every footprint used by `parts`."""
    custom = custom or {}
    geometry = {}
    for part in parts:
        lib, name = pf.split_footprint(part)
        if part['footprint'] in geometry:
            continue
        if lib == pf.CUSTOM_LIB and name in custom:
            geometry[part['footprint']] = pf.pads_in_text(pf.custom_text(custom[name]))
        else:
            geometry[part['footprint']] = pf.footprint_pad_details(lib, name, source)
    return geometry


def pad_gap(a: dict, b: dict) -> float:
    """Edge-to-edge distance of two axis-aligned pad records (0 when they touch or overlap)."""
    dx = max(0.0, abs(a['at'][0] - b['at'][0]) - (a['size'][0] + b['size'][0]) / 2)
    dy = max(0.0, abs(a['at'][1] - b['at'][1]) - (a['size'][1] + b['size'][1]) / 2)
    return math.hypot(dx, dy)


def pin_field_rules(parts, geometry, hv_nets=HV_NETS, ground=GROUND, hv_clearance=HV_CLEARANCE,
                    hv_to_ground=HV_TO_PGND) -> list[dict]:
    """Footprints whose own pads cannot satisfy the HV clearances: one record per reference.

    For every pad pair of a part with different nets where at least one net is HV, the required
    clearance is `hv_to_ground` when the other pad is the ground net and `hv_clearance` otherwise;
    a record (ref, footprint, pads, gap_mm, required_mm) is returned when the pad gap is smaller.
    """
    records = []
    for part in parts:
        pads = [p for p in geometry.get(part['footprint'], []) if p['number']]
        worst = None
        for i, a in enumerate(pads):
            for b in pads[i + 1:]:
                net_a, net_b = part['nets'].get(a['number']), part['nets'].get(b['number'])
                if net_a == net_b or not (net_a in hv_nets or net_b in hv_nets):
                    continue
                required = hv_to_ground if ground in (net_a, net_b) else hv_clearance
                gap = pad_gap(a, b)
                if gap < required - 1e-9 and (worst is None or gap - required < worst['gap_mm'] - worst['required_mm']):
                    worst = dict(ref=part['ref'], footprint=part['footprint'], pads=[a['number'], b['number']],
                                 gap_mm=round(gap, 4), required_mm=required)
        if worst:
            records.append(worst)
    return sorted(records, key=lambda r: ps.pin_key(r['ref'][1:]) if r['ref'][1:].isdigit() else (1, 0, r['ref']))


def design_rules_text(rules) -> str:
    """Custom design rules: HV-to-PGND clearance plus one pin-field exception per listed footprint.

    Later rules override earlier ones in KiCad, so the package exceptions come last; they apply only
    between a package's own pads and items intersecting its courtyard, and only to pairs involving an
    HV net, so gate and logic pins keep their class clearances inside the courtyard.
    """
    lines = ['(version 1)',
             f'(rule "HV to {GROUND}" (condition "A.NetClass == \'HV\' && B.NetName == \'{GROUND}\'") '
             f'(constraint clearance (min {pf.num(HV_TO_PGND)}mm)))']
    for rule in rules:
        ref = rule['ref']
        condition = (f"A.memberOfFootprint('{ref}') && B.intersectsCourtyard('{ref}') "
                     "&& (A.NetClass == 'HV' || B.NetClass == 'HV')")
        lines.append(f'(rule "pin field {ref}" (condition "{condition}") (constraint clearance (min {pf.num(PIN_FIELD)}mm)))')
    return '\n'.join(lines) + '\n'


def schematic_spec(kicad_dir, design_dir, parts, dru_text) -> dict:
    """project_schematic spec of the power-board project (dict form, validated by coerce_spec)."""
    return dict(name=NAME, title=TITLE, revision='smoke', comment=COMMENT, kicad_dir=Path(kicad_dir), design_dir=Path(design_dir),
                pages=dict(PAGES), parts=parts, board='power', flag_nets=list(FLAG_NETS), flag_page='02_driver',
                header_lines=['Generated by automation.kicad_tools.v2_pipeline_smoke for the V2 automation smoke.',
                              'Exercises project_footprints, project_schematic, grid_router, run_check, export_outputs and buck_stage.'],
                page_notes={'01_power': 'Q1/Q2 pin order follows the KiCad TO-247-4 footprint pads; verify against the device datasheet.'},
                net_classes=[dict(c) for c in NET_CLASSES], design_rules=dict(DESIGN_RULES), dru_text=dru_text, paper='A3')


# --- routing plan -------------------------------------------------------------------------------------------


def inflate(rect, margin):
    """Axis-aligned rect (x0, y0, x1, y1) grown by `margin` mm on every side."""
    return [rect[0] - margin, rect[1] - margin, rect[2] + margin, rect[3] + margin]


def point_in_polygon(point, polygon) -> bool:
    """Even-odd test of a point against a polygon (both in mm)."""
    x, y = point
    inside = False
    for (x0, y0), (x1, y1) in zip(polygon, polygon[1:] + polygon[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def zone_coverage(pads: dict) -> list[str]:
    """Pads the zone polygons must reach but do not; an empty list means the polygons match the placement.

    `pads` maps (ref, pad number) to a list of (x, y) centres taken from the placed board. Pads of the
    FET pin fields are tested at the point where their zone leg overlaps them, the others at their centre.
    """
    expected = {'VIN': [('C1', '1', 0, 0), ('C2', '1', 0, 0), ('Q1', '2', 0, 1.8)],
                'SW': [('L1', '1', 0, 0), ('Q2', '2', 0, -1.8), ('Q1', '3', 0, -1.8)],
                'VOUT': [('L1', '2', 0, 0), ('C4', '1', 0, 0)]}
    missing = []
    for net, checks in expected.items():
        polygon = ZONES[net]['polygon']
        for ref, number, dx, dy in checks:
            for x, y in pads.get((ref, number), []):
                if not point_in_polygon((x + dx, y + dy), polygon):
                    missing.append(f'{net}: {ref}.{number} at ({x}, {y}) outside the zone polygon')
    return missing


def routing_plan(pads: dict, save) -> dict:
    """grid_router plan for the placed board; `pads` maps (ref, pad) to [(x, y)] in mm, `save` is the board path."""
    (qx, qy), = pads[('Q1', '4')]
    stub = [(round(qx + dx, 4), round(qy + dy, 4)) for dx, dy in KS_H_STUB]
    keepouts = [dict(layer='F.Cu', rect=list(HEATSINK_BASE), net=None, vias=True)]
    for rect, net, margin in ZONE_KEEPOUTS:
        keepouts += [dict(layer=layer, rect=inflate(rect, margin), net=net, vias=True) for layer in ('F.Cu', 'B.Cu')]
    net_rules = {net: dict(width=1.0, clearance=HV_TO_PGND) for net in HV_NETS}
    net_rules.update({net: dict(width=0.5) for net in CRITICAL})
    power = {net: dict(stubs=False, priority=spec['priority'], clearance=0.5,
                       zones={'F.Cu': [list(p) for p in spec['polygon']], 'B.Cu': [list(p) for p in spec['polygon']]})
             for net, spec in ZONES.items()}
    return {
        'board': {'width': WIDTH, 'height': HEIGHT, 'margin': 1.0},
        'layers': list(LAYERS), 'grid': 0.25, 'trace': 0.25, 'clearance': 0.2, 'via': [0.6, 0.3], 'hole_clearance': 0.25,
        'net_rules': net_rules, 'keepouts': keepouts,
        'pre_routed': {'tracks': [dict(net='KS_H', layer='F.Cu', a=[qx, qy], b=list(stub[0]), width=0.5),
                                  dict(net='KS_H', layer='F.Cu', a=list(stub[0]), b=list(stub[1]), width=0.5)],
                       'vias': [dict(net='KS_H', xy=list(stub[1]), port=True)]},
        'fanout': {'order': ['U1'], 'skip_pads': [['Q1', '4']], 'skip_nets': list(HV_NETS)},
        'critical': list(CRITICAL), 'critical_layers': ['F.Cu', 'B.Cu'],
        'power': power, 'signal_order': list(SIGNAL_ORDER),
        'ground': {'net': GROUND, 'layers': ['In1.Cu', 'In2.Cu'], 'clearance': 0.5,
                   'holes': {'In1.Cu': [list(map(list, h)) for h in GROUND_HOLES], 'In2.Cu': [list(map(list, h)) for h in GROUND_HOLES]}},
        'prune_vias': True, 'fill': True, 'save': str(save), 'strict': False,
    }


# --- board stage (pcbnew) -----------------------------------------------------------------------------------


def stackup_text() -> str:
    """Native KiCad stackup block for the 4-layer board (FR4, ENIG)."""
    lines = ['(stackup']
    for layer, kind, thickness in STACKUP:
        extra = ' (material "FR4") (epsilon_r 4.3) (loss_tangent 0.02)' if kind != 'copper' else ''
        lines.append(f'(layer "{layer}" (type "{kind}") (thickness {thickness}){extra})')
    lines.append('(copper_finish "ENIG") (dielectric_constraints no))')
    return '\n'.join(lines)


def inject_stackup(path: Path) -> bool:
    """Insert the stackup block into a saved board file unless one is present; returns True when written."""
    text = path.read_text(encoding='utf-8')
    if '(stackup' in text:
        return False
    if '(setup\n' not in text:
        raise ValueError(f'{path.name}: no (setup block to receive the stackup')
    text = text.replace('(paper "A4")', '(paper "A3")', 1).replace('(setup\n', '(setup\n' + stackup_text() + '\n', 1)
    path.write_text(text, encoding='utf-8')
    return True


def export_netlist(schematic: Path, target: Path, cli=None) -> dict:
    """kicad-cli XML netlist export; returns {(ref, pad): net} for every node."""
    import xml.etree.ElementTree as ET
    cli = cli or find_kicad_cli()
    if not cli:
        raise FileNotFoundError('kicad-cli unavailable')
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(cli), 'sch', 'export', 'netlist', '--format', 'kicadxml', '--output', str(target), str(schematic)],
                   check=True, capture_output=True, timeout=180)
    tree = ET.parse(target).getroot()
    return {(node.attrib['ref'], node.attrib['pin']): net.attrib['name']
            for net in tree.findall('nets/net') for node in net.findall('node')}


def board_stage(kicad_dir, design_dir, result_path=None) -> dict:
    """Build, place, stack up, route and save the power board with pcbnew; returns the stage summary.

    Needs pcbnew (KiCad's bundled Python). The netlist comes from kicad-cli, footprints from the project
    libraries written by prepare_libraries, symbol paths from schematic_mapping.json; the saved board is
    reloaded after the stackup injection and again by run_plan's save_and_reload.
    """
    import pcbnew as pcb
    kicad_dir, design_dir = Path(kicad_dir), Path(design_dir)
    start = time.monotonic()
    parts = power_parts()
    mapping = json.loads((design_dir / 'schematic_mapping.json').read_text(encoding='utf-8'))['paths']
    pin_nets = export_netlist(kicad_dir / f'{NAME}.kicad_sch', design_dir / 'netlist.xml')
    board = pcb.BOARD()
    board.SetCopperLayerCount(len(LAYERS))
    board.GetDesignSettings().SetBoardThickness(pcb.FromMM(1.6))
    title = board.GetTitleBlock()
    title.SetTitle(TITLE)
    title.SetRevision('smoke')
    title.SetComment(0, COMMENT)
    nets = {}
    for name in sorted(set(pin_nets.values())):
        nets[name] = pcb.NETINFO_ITEM(board, name)
        board.Add(nets[name])

    def point(x, y):
        return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))

    def courtyard(fp):
        try:
            box = fp.GetCourtyard(pcb.F_CrtYd).BBox()
            if box.GetWidth() <= 0 or box.GetHeight() <= 0:
                raise ValueError
        except Exception:  # footprint without a courtyard: fall back to the hull
            box = fp.GetBoundingHull().BBox()
        return [pcb.ToMM(box.GetX()), pcb.ToMM(box.GetY()), pcb.ToMM(box.GetRight()), pcb.ToMM(box.GetBottom())]

    footprints, occupied, placements = {}, [], {}
    for part in parts:
        lib, name = part['footprint'].split(':')
        fp = pcb.FootprintLoad(str(kicad_dir / 'libraries' / f'{lib}.pretty'), name)
        if fp is None:
            raise ValueError(f'{part["ref"]}: pcbnew could not load {part["footprint"]}')
        fp.SetFPID(pcb.LIB_ID(lib, name))
        fp.SetReference(part['ref'])
        fp.SetValue(part['value'])
        fp.SetPath(pcb.KIID_PATH(mapping[part['ref']]))
        fp.Value().SetVisible(False)
        fp.Reference().SetLayer(pcb.F_Fab)
        if any(isinstance(g, pcb.PCB_TEXT) and g.GetText() == '${REFERENCE}' for g in fp.GraphicalItems()):
            fp.Reference().SetVisible(False)
        fp.Reference().SetTextSize(point(1, 1))
        fp.Reference().SetTextThickness(pcb.FromMM(0.15))
        seen = set()
        for pad in fp.Pads():
            number = pad.GetNumber()
            if not number:
                continue
            if number not in part['nets']:
                raise ValueError((part['ref'], 'unexpected pad', number))
            seen.add(number)
            if (part['ref'], number) in pin_nets:
                pad.SetNet(nets[pin_nets[part['ref'], number]])
        if seen != set(part['nets']):
            raise ValueError((part['ref'], 'missing pads', sorted(set(part['nets']) - seen)))
        board.Add(fp)
        x, y, angle = PLACEMENT[part['ref']]
        fp.SetOrientationDegrees(angle)
        fp.SetPosition(point(x, y))
        box = courtyard(fp)
        for other, other_box in occupied:
            if box[0] < other_box[2] and box[2] > other_box[0] and box[1] < other_box[3] and box[3] > other_box[1]:
                raise ValueError(('courtyard overlap', part['ref'], other, box, other_box))
        if box[0] < 0 or box[1] < 0 or box[2] > WIDTH or box[3] > HEIGHT:
            raise ValueError(('courtyard outside the board', part['ref'], box))
        occupied.append((part['ref'], box))
        placements[part['ref']] = dict(x=x, y=y, angle=angle, courtyard=[round(v, 3) for v in box])
        footprints[part['ref']] = fp
    for a, b in [((0, 0), (WIDTH, 0)), ((WIDTH, 0), (WIDTH, HEIGHT)), ((WIDTH, HEIGHT), (0, HEIGHT)), ((0, HEIGHT), (0, 0))]:
        edge = pcb.PCB_SHAPE(board)
        edge.SetShape(pcb.SHAPE_T_SEGMENT)
        edge.SetStart(point(*a))
        edge.SetEnd(point(*b))
        edge.SetLayer(pcb.Edge_Cuts)
        edge.SetWidth(pcb.FromMM(0.05))
        board.Add(edge)
    for value, x, y, size in [('AIPE V2 PIPELINE SMOKE - NOT A CONVERTER DESIGN', 45, 74.5, 1.5),
                              ('AI-GENERATED - HUMAN REVIEW REQUIRED', 45, 77.5, 1.2)]:
        item = pcb.PCB_TEXT(board)
        item.SetText(value)
        item.SetPosition(point(x, y))
        item.SetTextSize(point(size, size))
        item.SetTextThickness(pcb.FromMM(0.18))
        item.SetLayer(pcb.F_SilkS)
        board.Add(item)
    path = kicad_dir / f'{NAME}.kicad_pcb'
    board.BuildConnectivity()
    pcb.SaveBoard(str(path), board)
    inject_stackup(path)
    loaded = pcb.LoadBoard(str(path))
    if loaded.GetCopperLayerCount() != len(LAYERS):
        raise RuntimeError(f'reloaded board has {loaded.GetCopperLayerCount()} copper layers')
    pads = {}
    for fp in loaded.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNumber():
                pads.setdefault((fp.GetReference(), pad.GetNumber()), []).append(tuple(round(v, 4) for v in pcb.ToMM(pad.GetPosition())))
    coverage = zone_coverage(pads)
    if coverage:
        raise ValueError('zone polygons do not reach their pads: ' + '; '.join(coverage))
    plan = routing_plan(pads, path)
    report = gr.run_plan(loaded, plan)
    if inject_stackup(path):  # pcbnew round-trips the stackup; this only guards a future format change
        report['stackup_reinjected'] = True
        gr.save_and_reload(pcb.LoadBoard(str(path)), path)
    final = pcb.LoadBoard(str(path))
    geometry = {}
    for fp in final.GetFootprints():
        geometry[fp.GetReference()] = {'position': list(pcb.ToMM(fp.GetPosition())), 'angle': fp.GetOrientationDegrees(), 'pads': [
            {'number': p.GetNumber(), 'net': p.GetNetname(), 'xy': list(pcb.ToMM(p.GetPosition())), 'size': list(pcb.ToMM(p.GetSize())),
             'drill': list(pcb.ToMM(p.GetDrillSize())), 'type': int(p.GetAttribute())} for p in fp.Pads()]}
    (design_dir / 'placement.json').write_text(json.dumps(dict(board_mm=[WIDTH, HEIGHT], items=placements), indent=2) + '\n', encoding='utf-8')
    (design_dir / 'board_geometry.json').write_text(json.dumps(geometry, indent=2) + '\n', encoding='utf-8')
    (design_dir / 'routing_plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    (design_dir / 'routing_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    result = dict(board=str(path), footprints=len(footprints), copper_layers=final.GetCopperLayerCount(),
                  stackup_present='(stackup' in path.read_text(encoding='utf-8'), nets=len(nets),
                  netlist_nodes=len(pin_nets), report=report, seconds=round(time.monotonic() - start, 3),
                  pcbnew_version=pcb.GetBuildVersion())
    if result_path:
        Path(result_path).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def kicad_python():
    """Interpreter with pcbnew: AIPE_KICAD_PYTHON, local-tools.json, next to kicad-cli, or None."""
    explicit = os.environ.get('AIPE_KICAD_PYTHON') or read_config().get('kicad_python')
    if explicit and Path(os.path.expandvars(explicit)).is_file():
        return Path(os.path.expandvars(explicit))
    try:
        cli = find_kicad_cli()
    except FileNotFoundError:
        cli = None
    if cli:
        for name in ('python.exe', 'python3', 'python'):
            if (cli.parent / name).is_file():
                return cli.parent / name
    try:
        import pcbnew  # noqa: F401
        return Path(sys.executable)
    except ImportError:
        return None


def run_board_stage(kicad_dir, design_dir, result_path) -> dict:
    """Run board_stage in this process when pcbnew imports, else under KiCad's Python as a subprocess."""
    try:
        import pcbnew  # noqa: F401
        return board_stage(kicad_dir, design_dir, result_path)
    except ImportError:
        pass
    python = kicad_python()
    if python is None:
        raise FileNotFoundError('No Python interpreter with pcbnew was found (set AIPE_KICAD_PYTHON or local-tools.json)')
    command = [str(python), str(Path(__file__).resolve()), '--board-stage', str(kicad_dir), str(design_dir), str(result_path)]
    completed = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
    Path(result_path).with_suffix('.log').write_text(completed.stdout + completed.stderr, encoding='utf-8')
    if completed.returncode or not Path(result_path).is_file():
        raise RuntimeError(f'board stage failed (exit {completed.returncode}): {(completed.stdout + completed.stderr)[-3000:]}')
    return json.loads(Path(result_path).read_text(encoding='utf-8'))


# --- orchestration -------------------------------------------------------------------------------------------


def module_versions() -> dict:
    """sha256 and line count of every module the smoke exercises (the repository has no version attributes)."""
    versions = {}
    for key, relative in MODULES.items():
        path = ROOT / relative
        data = path.read_bytes()
        versions[key] = dict(path=relative, sha256=hashlib.sha256(data).hexdigest(), lines=data.count(b'\n'))
    return versions


def tool_versions(cli) -> dict:
    """kicad-cli version string (None when the CLI is missing)."""
    if not cli:
        return dict(kicad_cli=None, kicad_cli_version=None)
    probe = subprocess.run([str(cli), 'version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    return dict(kicad_cli=str(cli), kicad_cli_version=probe.stdout.strip() or None)


def read_manifest(path) -> dict:
    """run_check manifest with the DRC category counts added from the JSON report when present."""
    manifest = json.loads(Path(path).read_text(encoding='utf-8'))
    report = Path(manifest.get('report', ''))
    if report.is_file():
        data = json.loads(report.read_text(encoding='utf-8-sig'))
        if 'sheets' in data:
            manifest['violations'] = sum(len(sheet.get('violations', [])) for sheet in data['sheets'])
            manifest['details'] = [f"{v.get('type')}: {v.get('description')}" for sheet in data['sheets'] for v in sheet.get('violations', [])]
        else:
            manifest['violations'] = len(data.get('violations', []))
            manifest['unconnected_items'] = len(data.get('unconnected_items', []))
            manifest['schematic_parity'] = len(data.get('schematic_parity', []))
            manifest['details'] = [f"{v.get('type')}: {v.get('description')}" for key in ('violations', 'unconnected_items', 'schematic_parity')
                                   for v in data.get(key, [])]
    return manifest


def run_simulation(out_dir: Path, python=None) -> dict:
    """Run automation.simulation.buck_stage with its example parameters into `out_dir`; returns a summary."""
    out_dir = Path(out_dir)
    command = [str(python or sys.executable), '-m', 'automation.simulation.buck_stage', '--out', str(out_dir)]
    start = time.monotonic()
    completed = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'buck_stage.log').write_text(completed.stdout + completed.stderr, encoding='utf-8')
    result = dict(command=command, exit_code=completed.returncode, seconds=round(time.monotonic() - start, 3),
                  status='passed' if completed.returncode == 0 else 'failed')
    summary = out_dir / 'summary.json'
    if summary.is_file():
        data = json.loads(summary.read_text(encoding='utf-8'))
        metrics = data.get('metrics', {})
        result.update(name=data.get('name'), ngspice_version=data.get('ngspice', {}).get('version'), points=data.get('ngspice', {}).get('points'),
                      ngspice_runtime_s=data.get('ngspice', {}).get('runtime_s'), warnings=len(data.get('ngspice', {}).get('warnings', [])),
                      vout_mean_V=metrics.get('vout_mean'), il_pkpk_A=metrics.get('il_pkpk'), efficiency=metrics.get('efficiency'),
                      files=sorted(data.get('files', {}).values()))
    elif result['status'] == 'passed':
        result.update(status='failed', error='buck_stage exited 0 without writing summary.json')
    if result['status'] == 'failed' and 'error' not in result:
        result['error'] = (completed.stdout + completed.stderr)[-2000:]
    return result


def run(output, *, skip_simulation=False, cli=None) -> dict:
    """Execute the whole smoke into `output` and return the summary (also written as smoke-summary.json).

    Steps: model validation -> libraries -> schematic/project -> ERC -> board (pcbnew) -> DRC with
    parity -> exports -> simulation. A failing step is recorded with its error and later steps that
    depend on it are skipped; `status` is 'passed' only when every executed step passed and none was
    skipped for lack of a tool.
    """
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    kicad_dir, design_dir, checks = output / 'kicad', output / 'design', output / 'checks'
    try:
        cli = cli or find_kicad_cli()
    except FileNotFoundError as exc:
        cli = None
        cli_error = str(exc)
    else:
        cli_error = None if cli else 'kicad-cli not found'
    started = time.monotonic()
    summary = dict(schema_version=1, name=NAME, generated_utc=datetime.now(timezone.utc).isoformat(), output=str(output),
                   host=f'{platform.system()} {platform.release()} {platform.version()}', python=sys.version.split()[0],
                   tools=tool_versions(cli), modules=module_versions(), steps={}, notes=list(NOTES), status='failed')
    if cli_error:
        summary['tools']['error'] = cli_error
    steps = summary['steps']

    def step(name, function, *args, **kwargs):
        start = time.monotonic()
        try:
            result = function(*args, **kwargs)
            record = dict(status=result.pop('status', 'passed') if isinstance(result, dict) else 'passed', seconds=round(time.monotonic() - start, 3))
            record.update(result if isinstance(result, dict) else {})
        except Exception as exc:  # recorded, never hidden
            record = dict(status='failed', seconds=round(time.monotonic() - start, 3), error=f'{type(exc).__name__}: {exc}',
                          traceback=traceback.format_exc()[-4000:])
        steps[name] = record
        print(f'{name}: {record["status"]} ({record["seconds"]} s)' + (f' - {record["error"]}' if 'error' in record else ''), flush=True)
        return record

    parts = build_parts()
    custom = custom_footprints()

    def model():
        selected = power_parts(parts)
        issues = pf.validate_pad_mapping(parts, custom, board='power')
        if issues:
            raise ValueError('pad/net mapping inconsistent: ' + '; '.join(issues))
        nets = sorted({n for p in selected for n in p['nets'].values() if n})
        return dict(parts=len(parts), power_parts=len(selected), control_parts=[p['ref'] for p in parts if p['board'] != 'power'],
                    nets=len(nets), net_names=nets, custom_footprints=sorted(custom), pad_mapping_issues=issues,
                    connectivity=ps.analyse_connectivity([dict(p, nets=p['nets'], pins=p['pins']) for p in ps.coerce_spec(
                        schematic_spec(kicad_dir, design_dir, parts, '(rule "x" (constraint clearance (min 1mm)))')).parts], FLAG_NETS))

    def libraries():
        result = pf.prepare_libraries(parts, kicad_dir, custom_footprints=custom, board='power',
                                      notice_text='Disposable V2 pipeline smoke library; see automation/kicad_tools/v2_pipeline_smoke.py.')
        if result['warnings']:
            raise ValueError('prepare_libraries warnings: ' + '; '.join(result['warnings']))
        return {k: result[k] for k in ('libraries', 'copied', 'custom', 'models', 'parts')}

    def schematic():
        geometry = pad_geometry(power_parts(parts), custom)
        rules = pin_field_rules(power_parts(parts), geometry)
        result = ps.generate_project(schematic_spec(kicad_dir, design_dir, parts, design_rules_text(rules)))
        return dict(root=result['root'], project=result['project'], mapping=result['mapping'], sheets=[s['key'] for s in result['sheets']],
                    parts_placed=result['parts_placed'], skipped=result['skipped'], symbol_fallbacks=result['symbol_fallbacks'],
                    flags=result['flags'], diagnostics=result['diagnostics'], pin_field_rules=rules,
                    net_classes=[c['name'] for c in ps.coerce_spec(schematic_spec(kicad_dir, design_dir, parts, 'x')).net_classes])

    def check(kind, source):
        from automation.kicad_tools.run_check import run_check
        code, manifest_path = run_check(kind, Path(source), checks, cli)
        manifest = read_manifest(manifest_path)
        result = dict(status=manifest['status'], wrapper_exit_code=code, tool_exit_code=manifest.get('tool_exit_code'),
                      finding_count=manifest.get('finding_count'), manifest=str(manifest_path), source_sha256=manifest['source_sha256'])
        for key in ('violations', 'unconnected_items', 'schematic_parity', 'error'):
            if key in manifest:
                result[key] = manifest[key]
        if manifest.get('details'):
            result['details'] = manifest['details'][:50]
        return result

    def exports():
        from automation.kicad_tools.export_outputs import export
        target = output / 'exports'
        export(kicad_dir / NAME, target, EXPORT_LAYERS)
        manifest = json.loads((target / 'export-manifest.json').read_text(encoding='utf-8'))
        codes = [c['exit_code'] for c in manifest['commands']]
        return dict(status=manifest['status'], commands=len(codes), exit_codes=codes, files=len(manifest['artifacts']), directory=str(target))

    step('model', model)
    if cli is None:
        steps['erc'] = steps['board'] = steps['drc'] = steps['exports'] = dict(status='skipped', error='kicad-cli unavailable')
        print('kicad-cli unavailable: KiCad steps skipped (this is a failure, not a pass)', flush=True)
    else:
        if steps['model']['status'] == 'passed' and step('libraries', libraries)['status'] == 'passed' \
                and step('schematic', schematic)['status'] == 'passed':
            step('erc', check, 'erc', steps['schematic']['root'])
            if step('board', run_board_stage, kicad_dir, design_dir, design_dir / 'board_stage.json')['status'] == 'passed':
                step('drc', check, 'drc', steps['board']['board'])
                step('exports', exports)
    if skip_simulation:
        steps['simulation'] = dict(status='skipped', reason='--skip-simulation')
    else:
        step('simulation', run_simulation, output / 'simulation')
    required = ['model', 'libraries', 'schematic', 'erc', 'board', 'drc', 'exports'] + ([] if skip_simulation else ['simulation'])
    summary['status'] = 'passed' if all(steps.get(name, {}).get('status') == 'passed' for name in required) else 'failed'
    summary['seconds'] = round(time.monotonic() - started, 3)
    (output / 'smoke-summary.json').write_text(json.dumps(summary, indent=2, default=str) + '\n', encoding='utf-8')
    print(f'smoke {summary["status"]} in {summary["seconds"]} s -> {output / "smoke-summary.json"}', flush=True)
    return summary


def evidence_summary(summary: dict) -> dict:
    """Compact evidence record for examples/.../verification/environment: status, counts, versions, runtime."""
    steps = summary['steps']
    erc, drc, board, exports, sim = (steps.get(k, {}) for k in ('erc', 'drc', 'board', 'exports', 'simulation'))
    report = board.get('report', {})
    return dict(
        schema_version=1,
        purpose='End-to-end smoke of the V2 automation modules (project_footprints, project_schematic, grid_router, run_check, '
                'export_outputs, buck_stage) on a disposable mini half-bridge project generated into a scratch directory; '
                'see automation/kicad_tools/v2_pipeline_smoke.py.',
        generated_utc=summary['generated_utc'], host=summary['host'], host_python=summary['python'],
        status=summary['status'], runtime_s=summary.get('seconds'),
        tools=summary['tools'] | dict(pcbnew_version=board.get('pcbnew_version'), ngspice_version=sim.get('ngspice_version')),
        module_versions={k: dict(sha256=v['sha256'], lines=v['lines']) for k, v in summary['modules'].items()},
        model={k: steps.get('model', {}).get(k) for k in ('parts', 'power_parts', 'control_parts', 'nets', 'custom_footprints')},
        schematic={k: steps.get('schematic', {}).get(k) for k in ('sheets', 'parts_placed', 'skipped', 'symbol_fallbacks', 'flags', 'net_classes')},
        pin_field_rules=steps.get('schematic', {}).get('pin_field_rules'),
        erc=dict(status=erc.get('status'), finding_count=erc.get('finding_count'), tool_exit_code=erc.get('tool_exit_code')),
        board=dict(status=board.get('status'), size_mm=[WIDTH, HEIGHT], copper_layers=board.get('copper_layers'), stackup_present=board.get('stackup_present'),
                   footprints=board.get('footprints'), tracks=report.get('tracks'), vias=report.get('vias'), zones=report.get('zones'),
                   pruned_vias=report.get('pruned'), unresolved=len(report.get('unresolved', [])), routing_seconds=report.get('seconds'),
                   saved=report.get('saved')),
        drc=dict(status=drc.get('status'), finding_count=drc.get('finding_count'), violations=drc.get('violations'),
                 unconnected_items=drc.get('unconnected_items'), schematic_parity=drc.get('schematic_parity'), tool_exit_code=drc.get('tool_exit_code')),
        exports=dict(status=exports.get('status'), commands=exports.get('commands'), exit_codes=exports.get('exit_codes'), files=exports.get('files')),
        simulation={k: sim.get(k) for k in ('status', 'name', 'points', 'ngspice_runtime_s', 'vout_mean_V', 'il_pkpk_A', 'efficiency', 'warnings')},
        step_seconds={name: record.get('seconds') for name, record in steps.items()},
        notes=summary['notes'],
    )


def main(argv=None) -> int:
    """CLI: run the smoke into --output; optionally write the evidence summary; exit 0 only when it passed."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--output', type=Path, help='scratch directory receiving kicad/, design/, checks/, exports/, simulation/')
    parser.add_argument('--evidence', type=Path, help='write the compact evidence JSON here (e.g. examples/.../v2-pipeline-smoke.json)')
    parser.add_argument('--skip-simulation', action='store_true', help='leave out the ngspice step')
    parser.add_argument('--board-stage', nargs=3, metavar=('KICAD_DIR', 'DESIGN_DIR', 'RESULT_JSON'),
                        help='internal: run only the pcbnew board stage (needs KiCad Python)')
    args = parser.parse_args(argv)
    if args.board_stage:
        board_stage(*args.board_stage)
        return 0
    if args.output is None:
        parser.error('--output is required')
    summary = run(args.output, skip_simulation=args.skip_simulation)
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence_summary(summary), indent=2, default=str) + '\n', encoding='utf-8')
        print(f'evidence -> {args.evidence}', flush=True)
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
