"""Place, route and check the V2 SiC buck CONTROL board (AIPE_SiC_Buck_Control) with pcbnew and the grid router.

AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED

Follows automation.kicad_tools.v2_pipeline_smoke.board_stage(): kicad-cli XML netlist of the generated
schematic, a pcbnew BOARD with the project footprint libraries and the symbol paths of
design/schematic_mapping_control.json, deterministic placement with a courtyard-overlap check, the
4 x 35 um / 1.6 mm stackup injected as text, grid_router.run_plan for the routing (LQFP-176 escapes
pre-routed as alternating inward/outward vias with staggered outer rows, signals on F.Cu/B.Cu, In1.Cu
one solid GND_CTRL plane, In2.Cu rail islands 12V_PROT / 5V / 1V9 over a 3V3 background), zone fill,
SaveBoard/LoadBoard, then kicad-cli DRC with --schematic-parity --severity-all through
automation.kicad_tools.run_check and the layout metrics checker automation.verification.check_sic_layout.

Two floorplan candidates (design/floorplan_candidates/control_<A|B>.json: DSP orientation, connector
arrangement, regions, rail islands, silkscreen) are placed, measured and compared on measurable criteria
(DSP bypass distances, PWM/TZ Manhattan path estimates, analogue-to-PWM separation, supply loop sizes,
area usage); the selected candidate is routed into kicad/control_board/AIPE_SiC_Buck_Control.kicad_pcb.

Deterministic without KiCad: candidate loading and validation, the DSP escape plan, the island corridor
geometry, the routing plan, the stackup text and the comparison arithmetic. Requires native KiCad:
netlist export, footprint loading, placement/courtyards, routing, zone fill, DRC and the metrics. Only
the kicad-cli DRC report counts as verification; the router report and the placement checks are
geometric proposals. Nothing is waived: findings are reported with their manifest paths.

Run (re-executes itself under KiCad's bundled Python when pcbnew is not importable):
    python -m automation.kicad_tools.generate_sic_control_board [--candidate A|B] [--scratch DIR]
        [--no-route] [--no-drc] [--no-metrics]
Without --candidate both candidates are placed and compared and the winner is built.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # re-executed by KiCad's Python with this file as a script
    sys.path.insert(0, str(ROOT))

from automation.kicad_tools import grid_router as gr  # noqa: E402  (numpy only at import time)
from automation.setup.detect_kicad import find_kicad_cli, read_config  # noqa: E402

EXAMPLE = ROOT / 'examples/sic-buck-400v-200v-5kw'
KICAD_DIR = EXAMPLE / 'kicad/control_board'
DESIGN_DIR = EXAMPLE / 'design'
VERIFICATION_DIR = EXAMPLE / 'verification'
REVIEW_DIR = EXAMPLE / 'review'
CANDIDATES_DIR = DESIGN_DIR / 'floorplan_candidates'
MODEL_JSON = DESIGN_DIR / 'circuit_control.json'
MAPPING_JSON = DESIGN_DIR / 'schematic_mapping_control.json'
SPEC_JSON = VERIFICATION_DIR / 'engineering_checks/layout_spec_control.json'
CHECKS_DIR = VERIFICATION_DIR / 'engineering_checks'
DRC_DIR = VERIFICATION_DIR / 'drc'
NAME = 'AIPE_SiC_Buck_Control'
TITLE = 'AIPE SiC buck 400 V -> 200 V / 5 kW - TMS320F28335 control board (SELV mezzanine)'
BANNER = 'AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED'
REVISION = 'V2'
WIDTH, HEIGHT = 120.0, 80.0
COPPER_LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
ROUTING_LAYERS = ['F.Cu', 'B.Cu']  # In1.Cu is the unbroken GND_CTRL plane, In2.Cu carries only rail islands
GROUND_LAYER, ISLAND_LAYER = 'In1.Cu', 'In2.Cu'
GROUND = 'GND_CTRL'
RAILS = ('12V_PROT', '5V', '3V3', '1V9')
CORE_NET, IO_NET = '1V9', '3V3'
# Stackup (mm) written into the saved board as text (design/pcb_stackup.md section 2); pcbnew exposes no stackup mutation.
STACKUP = [('F.Cu', 'copper', 0.035), ('dielectric 1', 'prepreg', 0.2), ('In1.Cu', 'copper', 0.035),
           ('dielectric 2', 'core', 1.06), ('In2.Cu', 'copper', 0.035), ('dielectric 3', 'prepreg', 0.2), ('B.Cu', 'copper', 0.035)]
GRID, TRACE, CLEARANCE, HOLE_CLEARANCE = 0.125, 0.25, 0.2, 0.25  # 0.125 mm grid: 0.65 mm pitch pad rows stay on their own cell rows
ROUTER_TRACE = 0.2  # width of router-routed signal tracks (pcb_stackup.md section 2 default, Default net class); the pre-routed
# LQFP structures keep TRACE = 0.25 mm. With 0.2 mm the router's via mark radius is 0.61 mm, so a 0.65 mm pitch escape track
# passes a neighbouring via after 0.125 mm grid snapping (0.625 mm) - at 0.25 mm (0.635 mm radius) the row-end pins failed
ESCAPE_GRID = 0.25  # DSP escape vias snap to this coarser pitch (pad laterals of the LQFP are multiples of 0.25 mm)
VIA = (0.6, 0.3)
BOARD_MARGIN = 1.0
EDGE_COURTYARD = 0.4  # courtyards may come this close to the outline (mounting holes); copper keeps BOARD_MARGIN
ZONE_CLEARANCE, ZONE_MIN_THICKNESS = 0.25, 0.25
ESCAPE_IN, ESCAPE_OUT = 0.65, (0.65, 2.0)  # LQFP: inward single row; outward near/far rows (14.0 / 15.5 mm from the centre after
# snapping) so that the B.Cu exit of an inward pin passes both rows with 1.0 mm lateral distance to every outward via
STUB_RADIUS = 16.25  # LQFP exit lanes reach at least this radius: a tangential track here clears the far via row (15.5 + 0.3 + 0.2 + 0.125)
STUB_STEP, STUB_TURN_MM = 0.5, 1.0  # staircase step between lanes turning the same way; |destination offset| that counts as a turn
STUB_B_MAX = 22.0  # B.Cu lanes and peel-offs may run under neighbouring parts (no copper there before the fanout)
LANE_EDGE_MM = 1.0  # a pre-routed peel-off runs this far beyond the last lane of its group before the router takes over
IC_EXIT_STUB = (0.75, 0.5)  # B.Cu reserved exits of fine-pitch IC escape vias: near row inward, far row outward (mm)
STUB_JOG_RADII = (13.5, 14.75)  # the exit jogs 0.25 mm sideways before the near via row and back between the rows
STUB_JOG = 0.25  # lateral jog: every outward via stays >= 0.75 mm from the B.Cu exit (0.325 mm copper clearance)
IC_ESCAPE_ROWS = (0.65, 2.3)  # fine-pitch SO packages with an exposed pad: outward escapes alternate between these rows (1.65 mm
# apart so each via keeps > 0.635 mm from the other row's vias); packages without an exposed pad alternate inward/outward at
IC_ESCAPE_IN = 0.65  # this distance inside the pad end (under the body), facing rows with opposite phase at equal laterals
FINE_PITCH_MAX = 0.7  # pad pitch (mm) at or below which an IC's escapes are pre-routed instead of left to the router fanout
PREROUTE_ICS = False  # the router fanout (with ESCAPE_DISTANCES below) handles the fine-pitch ICs; True pre-routes them instead
ESCAPE_DISTANCES = (0.65, 1.3, 2.15, 2.9, 3.65, 4.5, 6.0)  # fanout via rows beyond a pad end. The router ranks a candidate by
# distance + 1.4 x |lateral shift|, so the second row must cost less than a 0.5 mm shift (1.35) to be preferred over stealing the
# neighbour's slot; 1.3 mm keeps >= sqrt(0.625^2 + 0.525^2) = 0.816 mm between staggered vias of 0.65 mm pitch pins after
# 0.125 mm grid snapping (the router blocks below 0.81 mm); the module default (1.25 mm) can snap to 0.80 mm and fail
CORRIDOR_HALF_WIDTH, CORRIDOR_OVERSHOOT, CORRIDOR_MAX_MM = 0.65, 0.5, 20.0
CORRIDOR_PRIORITY = 3
PLACE_STEP = 0.5
CORNER_EXCLUSION = 2.4  # DSP bypass rings stop this far (mm) before the package corners so the side groups never meet
# Courtyard-to-courtyard gaps (mm); a pair uses the larger of both parts' values per axis. Escape geometry: the second
# staggered via row ends 2.6 mm beyond a pin row and pads sit ~0.3 mm inside their courtyards, so 2.2 mm leaves 0.2 mm
# clearance; two passives facing each other need 2 x 0.95 + 0.2 - 0.6 = 1.5 mm, one-sided 1.3 mm covers a via plus clearance.
GAP_AXIS, GAP_LATERAL, GAP_TP = 1.3, 0.7, 0.5  # 2-pad passives: along the pad axis / across it; test points
GAP_IC_ESCAPE, GAP_IC_SIDE, GAP_CONNECTOR = 1.6, 0.8, 0.8  # ICs: pin-row sides (via 0.65 + 0.3 + exit stub, see IC_EXIT_STUB) / other
GAP_IC_EP_ESCAPE = 2.0  # exposed-pad packages cannot escape inward: both staggered rows lie outside (1.4 + 0.3 + 0.2 - 0.6 + margin)
GAP_QFP = 2.7  # the LQFP-176: its far escape row ends 15.875 mm from the centre, 2.15 mm beyond the 13.725 mm courtyard
MAX_NODES = 2500000
SIGNAL_ORDER = ['EPWM1A', 'EPWM1B', 'PWM_H_G', 'PWM_L_G', 'PWM_H', 'PWM_L', 'GATE_EN', 'FAULT_N', 'OC_N', 'FAULT_LATCH_N',
                'CLK30', 'ADC_', 'ADCREF', 'ADCRESEXT', 'VIN_SENSE', 'VOUT_SENSE', 'ISENSE', 'TEMP_', 'I12V_MON', 'V12V_MON',
                'REF', '5V_SW', '5V_BST', '5V_FB', '12V_IN', 'EFUSE_']
NET_RULES = {'12V_IN': dict(width=0.4), 'EFUSE_RTN': dict(width=0.4), '5V_SW': dict(width=0.4),
             '3V3_BULK': dict(width=0.6), '1V9_BULK': dict(width=0.6),
             '12V_PROT': dict(width=0.3), '5V': dict(width=0.3), '3V3': dict(width=0.3), '1V9': dict(width=0.3)}
INPAD_VIAS = [['U1', '17'], ['U3', '29']]  # HTSSOP exposed pads: EFUSE_RTN PowerPad and the LDO ground pad
ANALOG_NETS = ('ADC_', 'ADCREF', 'ADCRESEXT', 'VIN_SENSE', 'VOUT_SENSE', 'ISENSE', 'TEMP_', 'I12V_MON', 'V12V_MON', 'REF2V5', 'REF3V0',
               'OVP_IN_REF', 'OVP_OUT_REF', 'UVLO_REF', 'OTP_REF')
# Nets that define the analogue SECTION for the separation metric (the 12 V monitor dividers V12V_MON / I12V_MON belong to the supply entry).
ANALOG_SECTION_NETS = ('ADC_', 'ADCREF', 'ADCRESEXT', 'VIN_SENSE', 'VOUT_SENSE', 'ISENSE', 'TEMP_', 'REF2V5', 'REF3V0',
                       'OVP_IN_REF', 'OVP_OUT_REF', 'UVLO_REF', 'OTP_REF')
PWM_NETS = ('EPWM1A', 'EPWM1B', 'PWM_H_G', 'PWM_L_G', 'PWM_H', 'PWM_L')
PWM_CHAINS = {'PWM_H': ['EPWM1A', 'PWM_H_G', 'PWM_H'], 'PWM_L': ['EPWM1B', 'PWM_L_G', 'PWM_L']}
TZ_NETS = ('FAULT_N', 'OC_N')
SUPPLY_LOOPS = {'5V buck (U2, input/output capacitors, L1)': ['U2', 'C4', 'C5', 'L1', 'C7', 'C8'],
                'dual LDO (U3, input and output capacitors)': ['U3', 'C13', 'C14', 'C11', 'C12', 'R20', 'R21']}
COMPARISON_WEIGHTS = {'dsp_bypass_max_mm': 2.0, 'pwm_path_mm': 3.0, 'tz_path_mm': 2.0, 'analog_pwm_separation_mm': 2.0,
                      'analog_path_mm': 1.0, 'courtyard_fraction_front': 0.5}
COMPARISON_HIGHER_IS_BETTER = {'analog_pwm_separation_mm'}
NOTES = [
    'The LQFP-176 escapes are pre-routed: adjacent 0.5 mm pins cannot both leave the pin row on one side with 0.6 mm vias and 0.2 mm '
    'clearance (a track passing a neighbouring via at 0.5 mm lateral offset leaves 0.075 mm), so pins alternate inward/outward along '
    'each contiguous run; 1V9 pins prefer inward (core island under the body), 3V3 pins outward (background island); the few parity '
    'conflicts are closed by In2.Cu corridor zones (notches/fingers) computed from the routed via positions.',
    'Outward escape vias alternate between a near (0.65 mm) and a far (1.9 mm) row so that B.Cu exits of the inward vias pass between them.',
    'In1.Cu is one unbroken GND_CTRL zone (no routing layer); In2.Cu carries only the rail islands and their corridors; signals use F.Cu/B.Cu.',
    'Rail nets reach their islands through the fanout vias; a rail via outside its island is reported and bridged by a corridor zone.',
    'The grid router report is a geometric proposal; only the kicad-cli DRC manifest (schematic parity, severity-all) is verification.',
    'Silkscreen text is placed in part-free areas and its real bounding boxes are checked against the courtyards before saving.',
]


# --- generic geometry ----------------------------------------------------------------------------------------------


def snap(value: float, grid: float = GRID) -> float:
    return round(round(value / grid) * grid, 6)


def rect_contains(rect, box) -> bool:
    return rect[0] <= box[0] and rect[1] <= box[1] and rect[2] >= box[2] and rect[3] >= box[3]


def boxes_overlap(a, b, gx: float = 0.0, gy: float = 0.0) -> bool:
    return a[0] - gx < b[2] and a[2] + gx > b[0] and a[1] - gy < b[3] and a[3] + gy > b[1]


def point_in_polygon(point, polygon) -> bool:
    """Even-odd test (mm); points on a vertical/horizontal edge count as inside for axis-aligned islands."""
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        (x0, y0), (x1, y1) = polygon[i], polygon[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def polygon_bbox(polygon):
    xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def manhattan_mst(points) -> float:
    """Length of the Manhattan minimum spanning tree over (x, y) points (Prim, deterministic)."""
    points = list(points)
    if len(points) < 2:
        return 0.0
    in_tree = [points[0]]
    rest = points[1:]
    total = 0.0
    while rest:
        best = min(((abs(a[0] - b[0]) + abs(a[1] - b[1]), i) for i, b in enumerate(rest) for a in in_tree), key=lambda t: (t[0], t[1]))
        total += best[0]
        in_tree.append(rest.pop(best[1]))
    return total


def text_box(text: str, xy, size: float):
    """Conservative bounding box estimate of a centred stroke-font text (mm)."""
    width = len(text) * size * 1.1 + 0.6
    height = size * 1.7
    return (xy[0] - width / 2, xy[1] - height / 2, xy[0] + width / 2, xy[1] + height / 2)


def stackup_text() -> str:
    lines = ['(stackup']
    for layer, kind, thickness in STACKUP:
        extra = ' (material "FR4") (epsilon_r 4.3) (loss_tangent 0.02)' if kind != 'copper' else ''
        lines.append(f'(layer "{layer}" (type "{kind}") (thickness {thickness}){extra})')
    lines.append('(copper_finish "ENIG") (dielectric_constraints no))')
    return '\n'.join(lines)


def stackup_thickness_mm() -> float:
    return round(sum(t for _, _, t in STACKUP), 6)


def inject_stackup(path: Path) -> bool:
    """Insert the stackup block into a saved board unless present; returns True when written."""
    text = path.read_text(encoding='utf-8')
    if '(stackup' in text:
        return False
    if '(setup\n' not in text:
        raise ValueError(f'{path.name}: no (setup block to receive the stackup')
    text = text.replace('(paper "A4")', '(paper "A3")', 1).replace('(setup\n', '(setup\n' + stackup_text() + '\n', 1)
    path.write_text(text, encoding='utf-8')
    return True


# --- inputs ----------------------------------------------------------------------------------------------------------


def load_parts(path: Path = MODEL_JSON) -> list[dict]:
    """Shared-format part list of the control board (design/circuit_control.json)."""
    parts = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(parts, list) or not parts:
        raise ValueError(f'{path}: expected a non-empty list of parts')
    refs = [p['ref'] for p in parts]
    if len(refs) != len(set(refs)):
        raise ValueError('duplicate references in the model')
    return parts


def candidate_path(candidate_id: str) -> Path:
    return CANDIDATES_DIR / f'control_{candidate_id}.json'


def load_candidate(path) -> dict:
    """Floorplan candidate JSON with structural validation (board size, regions, islands, assignments)."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError(f'{path}: unsupported candidate schema_version {data.get("schema_version")}')
    for key in ('id', 'dsp', 'fixed', 'dsp_bypass', 'regions', 'assign', 'islands', 'island_priority', 'silkscreen'):
        if key not in data:
            raise ValueError(f'{path}: missing key {key!r}')
    if list(data.get('board_mm', [])) != [WIDTH, HEIGHT]:
        raise ValueError(f'{path}: board_mm must be [{WIDTH}, {HEIGHT}]')
    for name, rects in data['regions'].items():
        for rect in rects:
            if len(rect) != 4 or rect[0] >= rect[2] or rect[1] >= rect[3]:
                raise ValueError(f'{path}: region {name} rect {rect} is degenerate')
            if rect[0] < 2.0 or rect[1] < 1.0 or rect[2] > WIDTH - 2.0 or rect[3] > HEIGHT - 1.0:
                raise ValueError(f'{path}: region {name} rect {rect} leaves less than the edge margin')
    for net, polygon in data['islands'].items():
        if polygon == 'background':
            continue
        if len(polygon) < 4:
            raise ValueError(f'{path}: island {net} needs at least 4 vertices')
        for i in range(len(polygon)):
            a, b = polygon[i], polygon[(i + 1) % len(polygon)]
            if a[0] != b[0] and a[1] != b[1]:
                raise ValueError(f'{path}: island {net} must be rectilinear (edge {a}-{b})')
        box = polygon_bbox(polygon)
        if box[0] < BOARD_MARGIN or box[1] < BOARD_MARGIN or box[2] > WIDTH - BOARD_MARGIN or box[3] > HEIGHT - BOARD_MARGIN:
            raise ValueError(f'{path}: island {net} exceeds the board margin')
    for net in RAILS:
        if net not in data['islands'] or net not in data['island_priority']:
            raise ValueError(f'{path}: island/priority for {net} missing')
    for ref, pose in data['fixed'].items():
        if len(pose) != 3:
            raise ValueError(f'{path}: fixed {ref} needs [x, y, angle]')
    dsp = data['dsp']
    if dsp['angle'] % 90 != 0:
        raise ValueError(f'{path}: dsp angle must be a multiple of 90')
    for rail in (CORE_NET, IO_NET):
        cfg = data['dsp_bypass'].get(rail)
        if not cfg or cfg.get('side') not in ('F', 'B') or cfg.get('radius_mm', 0) <= 0:
            raise ValueError(f'{path}: dsp_bypass.{rail} needs side F|B and radius_mm')
    return data


def islands_overlap(candidate: dict) -> list[str]:
    """Pairs of explicit islands whose polygons overlap (sampled at 0.25 mm); empty when disjoint."""
    polys = {n: p for n, p in candidate['islands'].items() if p != 'background'}
    problems = []
    names = sorted(polys)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            box = polygon_bbox(polys[a])
            other = polygon_bbox(polys[b])
            if not boxes_overlap(box, other):
                continue
            x0, y0 = max(box[0], other[0]), max(box[1], other[1])
            x1, y1 = min(box[2], other[2]), min(box[3], other[3])
            x = x0 + 0.125
            hit = False
            while x < x1 and not hit:
                y = y0 + 0.125
                while y < y1:
                    if point_in_polygon((x, y), polys[a]) and point_in_polygon((x, y), polys[b]):
                        hit = True
                        break
                    y += 0.25
                x += 0.25
            if hit:
                problems.append(f'{a} overlaps {b}')
    return problems


def region_of(part: dict, candidate: dict) -> str | None:
    """Region name of a part from the candidate assignment (by_ref, then TP net prefix, then page)."""
    assign = candidate['assign']
    ref = part['ref']
    if ref in assign.get('by_ref', {}):
        return assign['by_ref'][ref]
    prefix_rules = assign.get('by_net_prefix', {})
    for prefix, table in prefix_rules.items():
        if ref.startswith(prefix) and not ref[len(prefix):].isalpha():
            nets = [n for n in part['nets'].values() if n]
            if nets and nets[0] in table:
                value = table[nets[0]]
                if isinstance(value, list):  # several regions in turn (e.g. two ground test points)
                    index = int(''.join(ch for ch in ref if ch.isdigit()) or 0)
                    return value[index % len(value)]
                return value
    return assign.get('by_page', {}).get(part['page'])


def assignment_report(parts: list[dict], candidate: dict) -> dict:
    """Which parts are fixed, DSP bypass, auto-placed per region, or unassigned (an empty list is required)."""
    fixed = set(candidate['fixed']) | {candidate['dsp']['ref']}
    report = dict(fixed=sorted(fixed), bypass=[], regions={}, unassigned=[])
    for part in parts:
        if part['ref'] in fixed:
            continue
        if 'near_dsp_pin' in part:
            report['bypass'].append(part['ref'])
            continue
        region = region_of(part, candidate)
        if region is None or region not in candidate['regions']:
            report['unassigned'].append(part['ref'])
        else:
            report['regions'].setdefault(region, []).append(part['ref'])
    return report


# --- DSP escape plan (pure) -------------------------------------------------------------------------------------------


def classify_side(pad_xy, centre):
    """('E'|'W'|'S'|'N', lateral coordinate, outward unit vector) of a pad relative to a package centre."""
    dx, dy = pad_xy[0] - centre[0], pad_xy[1] - centre[1]
    if abs(dx) >= abs(dy):
        return ('E' if dx > 0 else 'W'), pad_xy[1], (1 if dx > 0 else -1, 0)
    return ('S' if dy > 0 else 'N'), pad_xy[0], (0, 1 if dy > 0 else -1)


def row_axis(pads: list[dict]):
    """'x' when the pads form two columns (SO package, rows left/right), 'y' for two rows top/bottom, None for four sides."""
    xs = {round(p['xy'][0], 2) for p in pads}
    ys = {round(p['xy'][1], 2) for p in pads}
    if len(xs) <= 2 < len(ys):
        return 'x'
    if len(ys) <= 2 < len(xs):
        return 'y'
    return None


def pad_runs(pads: list[dict], centre, pitch_max: float = 0.75):
    """Pads grouped by package side and split into runs of consecutive pins (lateral gap <= pitch_max).

    Two-row packages are classified by their row axis (corner pins of a tall SO package lie closer to the short
    sides than to their own row and would otherwise escape through the row's end)."""
    sides: dict = {}
    axis = row_axis(pads)
    for pad in pads:
        if axis == 'x':
            dx = pad['xy'][0] - centre[0]
            key, lateral, out = ('E' if dx > 0 else 'W'), pad['xy'][1], (1 if dx > 0 else -1, 0)
        elif axis == 'y':
            dy = pad['xy'][1] - centre[1]
            key, lateral, out = ('S' if dy > 0 else 'N'), pad['xy'][0], (0, 1 if dy > 0 else -1)
        else:
            key, lateral, out = classify_side(pad['xy'], centre)
        sides.setdefault(key, []).append((round(lateral, 4), pad, out))
    runs = []
    for key in sorted(sides):
        items = sorted(sides[key], key=lambda t: t[0])
        run = []
        for item in items:
            if run and item[0] - run[-1][0] > pitch_max:
                runs.append((key, run))
                run = []
            run.append(item)
        if run:
            runs.append((key, run))
    return runs


def _escape_record(pad, key, lateral, out, direction, distance, grid, exception=False):
    sign = -1 if direction == 'in' else 1
    half = max(pad['size']) / 2
    ux, uy = out
    end = (pad['xy'][0] + sign * ux * half, pad['xy'][1] + sign * uy * half)
    via = (end[0] + sign * ux * distance, end[1] + sign * uy * distance)
    if grid:
        via = (snap(via[0], grid), snap(via[1], grid))
    return dict(number=str(pad['number']), net=pad['net'], side=key, lateral=lateral, direction=direction, distance=distance,
                out=[ux, uy], pad=[round(pad['xy'][0], 4), round(pad['xy'][1], 4)], via=[round(via[0], 4), round(via[1], 4)], exception=exception)


def plan_dsp_escapes(pads: list[dict], centre, *, grid: float = ESCAPE_GRID, inward: float = ESCAPE_IN, outward=ESCAPE_OUT,
                     core_net: str = CORE_NET, io_net: str = IO_NET) -> list[dict]:
    """Escape records for the connected LQFP pads: direction, distance and the grid-snapped via position.

    ``pads``: [{number, net, xy, size}] in board mm (connected pads only). Along each contiguous run of
    connected pins (0.5 mm pitch) the directions alternate; the phase of a run minimises weighted parity
    violations (core-rail pin outward counts 2, I/O-rail pin inward counts 1) and ties follow the greedy
    router (first pin outward). Outward pins alternate the near/far row distances along the run.
    """
    for pad in pads:
        _, lateral, _ = classify_side(pad['xy'], centre)
        if abs(lateral - snap(lateral, grid)) > 1e-6:
            raise ValueError(f"DSP pad {pad['number']} lateral coordinate {lateral} is off the {grid} mm escape grid; move the DSP")
    records = []
    for key, run in pad_runs(pads, centre):
        best = None
        for phase in (0, 1):  # pins whose index % 2 == phase go inward
            violations = sum(2 for i, (_, p, _) in enumerate(run) if p['net'] == core_net and i % 2 != phase)
            violations += sum(1 for i, (_, p, _) in enumerate(run) if p['net'] == io_net and i % 2 == phase)
            score = (violations, 0 if phase == 1 else 1)
            if best is None or score < best[0]:
                best = (score, phase)
        phase = best[1]
        k_out = 0
        for i, (lateral, pad, out) in enumerate(run):
            direction = 'in' if i % 2 == phase else 'out'
            if direction == 'in':
                distance = inward
            else:
                distance = outward[k_out % len(outward)]
                k_out += 1
            exception = (pad['net'] == core_net and direction == 'out') or (pad['net'] == io_net and direction == 'in')
            records.append(_escape_record(pad, key, lateral, out, direction, distance, grid, exception))
    for i, a in enumerate(records):
        for b in records[i + 1:]:
            if math.dist(a['via'], b['via']) < VIA[0] + CLEARANCE - 1e-6:
                raise ValueError(f"escape vias of DSP pads {a['number']} and {b['number']} are closer than {VIA[0] + CLEARANCE} mm")
    return records


def plan_ic_escapes(pads: list[dict], centre, *, rows=IC_ESCAPE_ROWS, blocked=(), pitch_max: float = 0.75,
                    inward_allowed: bool = True) -> list[dict]:
    """Escape records for a fine-pitch SO package.

    Packages without an exposed pad alternate inward (via IC_ESCAPE_IN inside the pad end, under the body) and outward
    (via rows[0]) along each pin row, with facing rows phased so that pins at equal laterals escape in opposite
    directions (their inward vias would otherwise coincide). Exposed-pad packages escape outward only, alternating
    between the two ``rows``. ``blocked``: via positions already planned - a pad whose via would come closer than
    via diameter + clearance to one of them is left to the router fanout. Vias are exact (not grid-snapped) so the
    escape track stays on the pad centreline.
    """
    records = []
    taken = [tuple(v) for v in blocked]
    runs = pad_runs(pads, centre, pitch_max)
    phase_by_lateral: dict = {}
    for key, run in runs:
        for i, (lateral, pad, out) in enumerate(run):
            if inward_allowed:
                partner = phase_by_lateral.get((lateral, _opposite(key)))
                if partner is not None:
                    direction = 'in' if partner == 'out' else 'out'
                elif i == 0:
                    direction = 'out'
                else:
                    direction = 'in' if records_run_last(records, run, i) == 'out' else 'out'
                distance = IC_ESCAPE_IN if direction == 'in' else rows[0]
                phase_by_lateral[(lateral, key)] = direction
            else:
                direction, distance = 'out', rows[i % len(rows)]
            record = _escape_record(pad, key, lateral, out, direction, distance, None)
            if any(math.dist(record['via'], v) < VIA[0] + CLEARANCE - 1e-6 for v in taken):
                continue
            taken.append(tuple(record['via']))
            records.append(record)
    return records


def _opposite(key: str) -> str:
    return {'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}[key]


def records_run_last(records: list[dict], run, i: int) -> str:
    """Direction of the previous pin of the run (by pad number), 'in' when it was not pre-routed."""
    previous = str(run[i - 1][1]['number'])
    for r in reversed(records):
        if r['number'] == previous:
            return r['direction']
    return 'in'


def lane_side_laterals(record: dict, escapes: list[dict]):
    """(near_left, far_left) flags of the outward neighbours 0.5 mm beside an inward escape (None when absent)."""
    near_left = far_left = None
    for other in escapes:
        if other['side'] != record['side'] or other['direction'] != 'out' or abs(abs(other['lateral'] - record['lateral']) - 0.5) > 1e-6:
            continue
        is_left = other['lateral'] < record['lateral']
        if other['distance'] == ESCAPE_OUT[0]:
            near_left = is_left
        else:
            far_left = is_left
    return near_left, far_left


def side_point(record: dict, centre, lateral: float, radius: float):
    """Board point at ``lateral`` along a package side and ``radius`` from the package centre, in the escape's frame."""
    ux, uy = record['out']
    if ux:
        return [round(centre[0] + ux * radius, 4), round(lateral, 4)]
    return [round(lateral, 4), round(centre[1] + uy * radius, 4)]


def exit_stub(record: dict, escapes: list[dict], centre, radius: float = STUB_RADIUS) -> list:
    """B.Cu exit polyline of an inward LQFP escape, from its via to ``radius`` from the package centre.

    The lane jogs ``STUB_JOG`` sideways away from the neighbouring near-row via before that row and back
    past the neighbouring far-row via between the rows, so every outward via keeps >= 0.75 mm lateral
    distance from the lane; an isolated inward pin (no outward neighbour) gets a straight stub.
    """
    ux, uy = record['out']
    lateral = record['lateral']
    via_r = abs((record['via'][0] - centre[0]) if ux else (record['via'][1] - centre[1]))
    shift = lane_jog(record, escapes)
    if shift == 0.0:
        return [side_point(record, centre, lateral, via_r), side_point(record, centre, lateral, radius)]
    j1, j2 = STUB_JOG_RADII
    return [side_point(record, centre, lateral, via_r), side_point(record, centre, lateral, j1), side_point(record, centre, lateral + shift, j1),
            side_point(record, centre, lateral + shift, j2), side_point(record, centre, lateral - shift, j2), side_point(record, centre, lateral - shift, radius)]


def outward_stub(record: dict, centre, radius: float) -> list:
    """F.Cu lane of an outward LQFP escape: straight on from its via to ``radius``."""
    ux, uy = record['out']
    via_r = abs((record['via'][0] - centre[0]) if ux else (record['via'][1] - centre[1]))
    if radius <= via_r + 1e-6:
        return []
    return [list(record['via']), side_point(record, centre, record['lateral'], radius)]


def lane_destinations(escapes: list[dict], table: dict, dsp_ref: str) -> dict:
    """net -> lateral coordinate (per side frame) of the centroid of the net's pads outside the DSP; None without other pads."""
    result = {}
    for e in escapes:
        others = [pad['xy'] for (ref, _), pad in table.items() if pad['net'] == e['net'] and ref != dsp_ref]
        if not others:
            result[e['net']] = None
            continue
        cx = sum(x for x, _ in others) / len(others)
        cy = sum(y for _, y in others) / len(others)
        result[e['net']] = cy if e['out'][0] else cx
    return result


def lane_plan(escapes: list[dict], destinations: dict, centre, base: float = STUB_RADIUS, step: float = STUB_STEP) -> dict:
    """Deterministic B.Cu breakout of the inward LQFP signal lanes (the outward pins leave on F.Cu through the router).

    Per side, inward lanes are classed L / R / S by the lateral offset of their destination centroid. A turning lane
    passes the same-layer lanes between its own lateral and its target lateral (destination, clamped to LANE_EDGE_MM
    beyond the group); its end radius is base + step x rank where rank is one more than the highest rank among the
    same-way lanes it passes (longest path, so chains stay compact). A lane that would pass a straight or opposite-way
    lane is "conflicted" (left to the router, straight stub only). Straight lanes end beyond every turning lane and
    continue radially through the router. Non-conflicted turners get their tangential peel-off pre-routed on B.Cu.
    Returns dict(ends={pad: radius}, peel_offs=[{net, number, layer, a, b}], conflicted=[pad], classes={pad: cls}).
    """
    ends, peel_offs, conflicted, classes = {}, [], [], {}
    groups: dict = {}
    for e in escapes:
        if e['net'] in RAILS or e['net'] == GROUND or e['direction'] != 'in':
            continue
        groups.setdefault(e['side'], []).append(e)
    for side, lanes in sorted(groups.items()):
        laterals = [e['lateral'] for e in lanes]
        lo, hi = min(laterals) - LANE_EDGE_MM, max(laterals) + LANE_EDGE_MM
        targets = {}
        for e in lanes:
            d = destinations.get(e['net'])
            if d is None or abs(d - e['lateral']) <= STUB_TURN_MM:
                classes[e['number']] = 'S'
            elif d < e['lateral']:
                classes[e['number']] = 'L'
                targets[e['number']] = max(lo, d)
            else:
                classes[e['number']] = 'R'
                targets[e['number']] = min(hi, d)
        passes = {}
        for e in lanes:
            if classes[e['number']] == 'S':
                continue
            t = targets[e['number']]
            a, b = min(e['lateral'], t), max(e['lateral'], t)
            passes[e['number']] = [o for o in lanes if o is not e and a < o['lateral'] < b]
        rank = {}

        def rank_of(e, depth=0):
            if e['number'] in rank:
                return rank[e['number']]
            if depth > len(lanes):
                return 0
            same = [o for o in passes.get(e['number'], []) if classes[o['number']] == classes[e['number']] or o['number'] in conflicted]
            value = 1 + max((rank_of(o, depth + 1) for o in same), default=-1)
            rank[e['number']] = value
            return value

        for e in sorted(lanes, key=lambda r: len(passes.get(r['number'], []))):
            cls = classes[e['number']]
            if cls == 'S':
                continue
            if any(classes[o['number']] != cls and o['number'] not in conflicted for o in passes[e['number']]):
                conflicted.append(e['number'])
        for e in lanes:
            if e['number'] in conflicted:
                rank[e['number']] = 0  # base-length stub: peel-offs of ranked lanes pass beyond its end
        for e in lanes:
            if classes[e['number']] != 'S' and e['number'] not in conflicted:
                rank_of(e)
        top = base + step * (max(rank.values(), default=-1) + 1)
        for e in lanes:
            cls = classes[e['number']]
            if cls == 'S':
                ends[e['number']] = min(top, STUB_B_MAX)
            elif e['number'] in conflicted:
                ends[e['number']] = base
            else:
                ends[e['number']] = min(base + step * rank[e['number']], STUB_B_MAX)
        for e in lanes:
            cls = classes[e['number']]
            if cls == 'S' or e['number'] in conflicted:
                continue
            r = ends[e['number']]
            a = side_point(e, centre, e['lateral'] - lane_jog(e, escapes), r)
            b = side_point(e, centre, targets[e['number']], r)
            peel_offs.append(dict(net=e['net'], number=e['number'], layer='B.Cu', a=a, b=b))
    return dict(ends=ends, peel_offs=peel_offs, conflicted=conflicted, classes=classes)


def lane_jog(record: dict, escapes: list[dict]) -> float:
    """Signed jog of an inward lane at its far end (0 for a straight stub), see exit_stub."""
    near_left, far_left = lane_side_laterals(record, escapes)
    if near_left is None and far_left is None:
        return 0.0
    if near_left is not None:
        return STUB_JOG if near_left else -STUB_JOG
    return -STUB_JOG if far_left else STUB_JOG


# --- island corridors (pure) ------------------------------------------------------------------------------------------


CORRIDOR_MIN_NECK = 0.5  # a corridor counts as severed when an obstacle's clearance ring leaves less fill width than this
CORRIDOR_L_OFFSETS = (1.5, -1.5, 2.0, -2.0, 2.5, -2.5, 3.0, -3.0)  # lateral first legs tried for an L-shaped corridor


def island_corridors(items: list[dict], islands: dict, *, obstacles: list[dict] | None = None, half_width: float = CORRIDOR_HALF_WIDTH,
                     overshoot: float = CORRIDOR_OVERSHOOT, max_mm: float = CORRIDOR_MAX_MM, via_radius: float = VIA[0] / 2,
                     clearance: float = ZONE_CLEARANCE) -> dict:
    """Corrective In2.Cu corridor zones for rail vias/through pads that sit outside their own island.

    ``items``: [{net, xy, kind}] for every via and plated through pad of a rail net; ``islands``: {net: polygon |
    'background'}; ``obstacles``: [{net, xy, r}] for every via and plated through pad on the board (default: the
    items themselves). An item inside another rail's island, or outside its own (non-background) island, gets an
    axis-aligned corridor rectangle from its position to the nearest point that lies in its own territory (own
    polygon, or outside every other island for the background rail). A corridor is severed where the clearance ring
    of an other-net obstacle leaves less than CORRIDOR_MIN_NECK of fill width; such directions are not used. When
    every straight direction is severed, an L-shaped corridor (lateral first leg of CORRIDOR_L_OFFSETS, then toward
    the territory) is tried; its two legs are emitted as two records sharing ``xy`` with ``leg`` 1 and 2. Every corridor
    gets its own zone priority above the islands (KiCad flags intersecting same-net zones of equal priority). Items with
    no usable corridor within ``max_mm`` are reported as issues.
    """
    polys = {n: p for n, p in islands.items() if p != 'background'}
    corridors, issues = [], []
    obstacles = items if obstacles is None else obstacles

    def territory(net, point) -> bool:
        if any(point_in_polygon(point, poly) for n, poly in polys.items() if n != net):
            return False
        return net not in polys or point_in_polygon(point, polys[net])

    def reach(net, origin, d):
        """Distance along d from origin to the first point in the net's territory, None when beyond max_mm."""
        t = 0.1
        while t <= max_mm:
            if territory(net, (origin[0] + d[0] * t, origin[1] + d[1] * t)):
                return t
            t = round(t + 0.1, 6)
        return None

    def rectangle(origin, d, length):
        x0 = min(origin[0] - d[0] * half_width, origin[0] + d[0] * length) if d[0] else origin[0] - half_width
        x1 = max(origin[0] - d[0] * half_width, origin[0] + d[0] * length) if d[0] else origin[0] + half_width
        y0 = min(origin[1] - d[1] * half_width, origin[1] + d[1] * length) if d[1] else origin[1] - half_width
        y1 = max(origin[1] - d[1] * half_width, origin[1] + d[1] * length) if d[1] else origin[1] + half_width
        return (round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4))

    def blockers(net, origin, d, rect):
        """Other-net obstacles whose clearance ring severs the corridor rectangle (fill neck below CORRIDOR_MIN_NECK)."""
        found = []
        for o in obstacles:
            if o['net'] == net:
                continue
            ox, oy = o['xy']
            ring = float(o.get('r', via_radius)) + clearance
            if d[0]:
                lateral, axial_inside = abs(oy - origin[1]), rect[0] - ring < ox < rect[2] + ring
            else:
                lateral, axial_inside = abs(ox - origin[0]), rect[1] - ring < oy < rect[3] + ring
            if axial_inside and half_width + lateral - ring < CORRIDOR_MIN_NECK:
                found.append(o)
        return found

    def record(item, origin, d, length, rect, **extra):
        return dict(net=item['net'], xy=list(item['xy']), kind=item.get('kind'), direction=list(d), length_mm=round(length, 3),
                    polygon=[[rect[0], rect[1]], [rect[2], rect[1]], [rect[2], rect[3]], [rect[0], rect[3]]], priority=CORRIDOR_PRIORITY, **extra)

    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for item in items:
        net, xy = item['net'], tuple(item['xy'])
        if net not in islands or territory(net, xy):
            continue
        straight, severed = [], []
        for d in directions:
            found = reach(net, xy, d)
            if found is None:
                continue
            rect = rectangle(xy, d, found + overshoot)
            hit = blockers(net, xy, d, rect)
            (severed if hit else straight).append((found, d, rect, hit))
        if straight:
            found, d, rect, _ = min(straight, key=lambda o: (o[0], o[1]))
            corridors.append(record(item, xy, d, found + overshoot, rect))
            continue
        if not severed:
            issues.append(dict(net=net, xy=list(xy), kind=item.get('kind'), reason=f'no territory of {net} within {max_mm} mm'))
            continue
        l_shapes = []
        for found0, d, _, _ in severed:
            perp = (d[1], d[0])
            for offset in CORRIDOR_L_OFFSETS:
                corner = (round(xy[0] + perp[0] * offset, 4), round(xy[1] + perp[1] * offset, 4))
                leg1_dir = (perp[0] * (1 if offset > 0 else -1), perp[1] * (1 if offset > 0 else -1))
                leg1 = rectangle(xy, leg1_dir, abs(offset))
                if blockers(net, xy, leg1_dir, leg1):
                    continue
                found = reach(net, corner, d)
                if found is None:
                    continue
                leg2 = rectangle(corner, d, found + overshoot)
                if blockers(net, corner, d, leg2):
                    continue
                l_shapes.append((abs(offset) + found, offset, leg1_dir, leg1, corner, d, found, leg2))
        if not l_shapes:
            hit = severed[0][3]
            issues.append(dict(net=net, xy=list(xy), kind=item.get('kind'),
                               reason='every corridor direction is severed by other-net copper: ' + ', '.join(f"{b['net']}@{b['xy']}" for b in hit)))
            continue
        total, offset, leg1_dir, leg1, corner, d, found, leg2 = min(l_shapes, key=lambda o: (o[0], o[1]))
        corridors.append(record(item, xy, leg1_dir, abs(offset), leg1, shape='L', leg=1))
        corridors.append(record(item, corner, d, found + overshoot, leg2, shape='L', leg=2))
    for i, a in enumerate(corridors):
        a['priority'] = CORRIDOR_PRIORITY + i  # distinct priorities: KiCad rejects intersecting same-net zones of equal priority (L legs overlap)
        for b in corridors[i + 1:]:
            if a['net'] != b['net'] and boxes_overlap(polygon_bbox(a['polygon']), polygon_bbox(b['polygon']), clearance, clearance):
                issues.append(dict(net=a['net'], xy=a['xy'], kind='corridor', reason=f"corridor overlaps a {b['net']} corridor at {b['xy']}"))
    return dict(corridors=corridors, issues=issues)


def uncovered_rail_items(items: list[dict], islands: dict, corridors: list[dict]) -> list[dict]:
    """Rail items that are outside their own territory and not covered by a corridor of their net (expected: none)."""
    polys = {n: p for n, p in islands.items() if p != 'background'}
    result = []
    for item in items:
        net, xy = item['net'], tuple(item['xy'])
        if net not in islands:
            continue
        foreign = any(point_in_polygon(xy, poly) for n, poly in polys.items() if n != net)
        own = net not in polys or point_in_polygon(xy, polys[net])
        if own and not foreign:
            continue
        if any(c['net'] == net and point_in_polygon(xy, c['polygon']) for c in corridors):
            continue
        result.append(dict(net=net, xy=list(xy), kind=item.get('kind')))
    return result


# --- routing plan (pure) ---------------------------------------------------------------------------------------------


def background_polygon():
    m = BOARD_MARGIN
    return [[m, m], [WIDTH - m, m], [WIDTH - m, HEIGHT - m], [m, HEIGHT - m]]


def island_polygon(candidate: dict, net: str):
    polygon = candidate['islands'][net]
    return background_polygon() if polygon == 'background' else [list(p) for p in polygon]


def routing_plan(candidate: dict, escapes: list[dict], save, *, ic_refs=(), ic_escapes: dict | None = None, dsp_centre=None,
                 dsp_signal_nets=(), lanes: dict | None = None) -> dict:
    """grid_router plan: pre-routed LQFP escapes with B.Cu exit stubs, pre-routed fine-pitch IC escapes, fanout for the
    rest (DSP and pre-routed pads skipped), signals on F.Cu/B.Cu (DSP nets first), rail islands and the GND plane."""
    tracks = [dict(net=e['net'], layer='F.Cu', a=list(e['pad']), b=list(e['via']), width=TRACE) for e in escapes]
    vias = [dict(net=e['net'], xy=list(e['via']), port=True) for e in escapes]
    stubs = 0
    lanes = lanes or {}
    lane_ends = lanes.get('ends', {})
    if dsp_centre is not None:
        for e in escapes:
            if e['net'] in RAILS or e['net'] == GROUND:
                continue
            if e['direction'] != 'in':
                continue  # outward pins leave on F.Cu through the router (free layer beyond the far via row)
            points = exit_stub(e, escapes, dsp_centre, min(STUB_B_MAX, lane_ends.get(e['number'], STUB_RADIUS)))
            layer = 'B.Cu'
            for a, b in zip(points, points[1:]):
                if math.dist(a, b) > 1e-6:
                    tracks.append(dict(net=e['net'], layer=layer, a=list(a), b=list(b), width=TRACE))
            stubs += 1 if points else 0
        for peel in lanes.get('peel_offs', []):
            if math.dist(peel['a'], peel['b']) > 1e-6:
                tracks.append(dict(net=peel['net'], layer=peel['layer'], a=list(peel['a']), b=list(peel['b']), width=TRACE))
    skip_pads = [[candidate['dsp']['ref'], e['number']] for e in escapes]
    for ref, records in sorted((ic_escapes or {}).items()):
        for e in records:
            tracks.append(dict(net=e['net'], layer='F.Cu', a=list(e['pad']), b=list(e['via']), width=TRACE))
            vias.append(dict(net=e['net'], xy=list(e['via']), port=True))
            skip_pads.append([ref, e['number']])
            ux, uy = e['out']
            if e['direction'] == 'in':
                sign, length = -1, IC_EXIT_STUB[0]  # further under the body
            else:
                sign, length = (1, IC_EXIT_STUB[1]) if e['distance'] != IC_ESCAPE_ROWS[0] or e['direction'] == 'out' else (-1, IC_EXIT_STUB[0])
            end = [round(e['via'][0] + sign * ux * length, 4), round(e['via'][1] + sign * uy * length, 4)]
            tracks.append(dict(net=e['net'], layer='B.Cu', a=list(e['via']), b=end, width=TRACE))
    power = {}
    for net in RAILS:
        power[net] = dict(stubs=False, priority=int(candidate['island_priority'][net]), clearance=ZONE_CLEARANCE,
                          min_thickness=ZONE_MIN_THICKNESS, zones={ISLAND_LAYER: island_polygon(candidate, net)})
    order = [candidate['dsp']['ref']] + [r for r in ic_refs if r != candidate['dsp']['ref']]
    signal_order = list(SIGNAL_ORDER)
    for net in dsp_signal_nets:  # every DSP net before the generic remainder, PWM/TZ keep their place at the top
        if net not in signal_order:
            signal_order.append(net)
    return {
        'board': {'width': WIDTH, 'height': HEIGHT, 'margin': BOARD_MARGIN},
        'layers': list(ROUTING_LAYERS), 'grid': GRID, 'trace': ROUTER_TRACE, 'clearance': CLEARANCE, 'via': list(VIA), 'hole_clearance': HOLE_CLEARANCE,
        'directions': [None, None],
        'net_rules': {k: dict(v) for k, v in NET_RULES.items()},
        'keepouts': [],
        'pre_routed': {'tracks': tracks, 'vias': vias},
        'fanout': {'order': order, 'skip_refs': [candidate['dsp']['ref']], 'skip_pads': skip_pads, 'inpad_vias': [list(p) for p in INPAD_VIAS]},
        'critical': [], 'critical_layers': list(ROUTING_LAYERS),
        'power': power,
        'signal_order': signal_order, 'signal_layers': list(ROUTING_LAYERS), 'front_fallback': True,
        'ground': {'net': GROUND, 'layers': [GROUND_LAYER], 'clearance': ZONE_CLEARANCE, 'priority': 0, 'polygon': background_polygon()},
        'prune_vias': True, 'fill': True, 'save': str(save), 'strict': False, 'max_nodes': MAX_NODES,
    }


# --- pcbnew helpers --------------------------------------------------------------------------------------------------


def export_netlist(schematic: Path, target: Path, cli=None) -> dict:
    """kicad-cli XML netlist export; returns {(ref, pad): net} for every node."""
    cli = cli or find_kicad_cli()
    if not cli:
        raise FileNotFoundError('kicad-cli unavailable')
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(cli), 'sch', 'export', 'netlist', '--format', 'kicadxml', '--output', str(target), str(schematic)],
                   check=True, capture_output=True, timeout=300)
    tree = ET.parse(target).getroot()
    return {(node.attrib['ref'], node.attrib['pin']): net.attrib['name'] for net in tree.findall('nets/net') for node in net.findall('node')}


def kicad_python():
    """Interpreter with pcbnew: AIPE_KICAD_PYTHON, .aipe/local-tools.json, next to kicad-cli, or None."""
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


def read_manifest(path) -> dict:
    """run_check manifest with the DRC category counts and finding details added from KiCad's JSON report."""
    manifest = json.loads(Path(path).read_text(encoding='utf-8'))
    report = Path(manifest.get('report', ''))
    if report.is_file():
        data = json.loads(report.read_text(encoding='utf-8-sig'))
        manifest['violations'] = len(data.get('violations', []))
        manifest['unconnected_items'] = len(data.get('unconnected_items', []))
        manifest['schematic_parity'] = len(data.get('schematic_parity', []))
        manifest['details'] = [f"{v.get('type')}: {v.get('description')}" + (f" @ {v['items'][0].get('pos')}" if v.get('items') else '')
                               for key in ('violations', 'unconnected_items', 'schematic_parity') for v in data.get(key, [])]
    return manifest


class Builder:
    """pcbnew-bound board construction for one candidate (placement, outline, silkscreen, save)."""

    def __init__(self, candidate: dict, parts: list[dict], mapping: dict, pin_nets: dict):
        import pcbnew as pcb
        self.pcb = pcb
        self.candidate = candidate
        self.parts = parts
        self.by_ref = {p['ref']: p for p in parts}
        self.mapping = mapping
        self.pin_nets = pin_nets
        self.board = pcb.BOARD()
        self.board.SetCopperLayerCount(len(COPPER_LAYERS))
        self.board.GetDesignSettings().SetBoardThickness(pcb.FromMM(stackup_thickness_mm()))
        title = self.board.GetTitleBlock()
        title.SetTitle(TITLE)
        title.SetRevision(REVISION)
        title.SetComment(0, BANNER)
        title.SetComment(1, f"floorplan candidate {candidate['id']}: {candidate['title']}")
        self.nets = {}
        for name in sorted(set(pin_nets.values())):
            self.nets[name] = pcb.NETINFO_ITEM(self.board, name)
            self.board.Add(self.nets[name])
        self.footprints: dict = {}
        self.occupied = {'F': [], 'B': []}
        self.placements: dict = {}
        self.pose_cache: dict = {}
        self.served_supply_pads: set = set()
        self.issues: list[str] = []
        self._load_footprints()

    # ----- footprints ------------------------------------------------------------------------------------------------
    def point(self, x, y):
        return self.pcb.VECTOR2I(self.pcb.FromMM(x), self.pcb.FromMM(y))

    def _load_footprints(self):
        pcb = self.pcb
        for part in self.parts:
            lib, name = part['footprint'].split(':')
            fp = pcb.FootprintLoad(str(KICAD_DIR / 'libraries' / f'{lib}.pretty'), name)
            if fp is None:
                raise ValueError(f"{part['ref']}: pcbnew could not load {part['footprint']} from the project library")
            fp.SetFPID(pcb.LIB_ID(lib, name))
            fp.SetReference(part['ref'])
            fp.SetValue(part['value'])
            if part['ref'] not in self.mapping:
                raise ValueError(f"{part['ref']}: no schematic path in {MAPPING_JSON.name}")
            fp.SetPath(pcb.KIID_PATH(self.mapping[part['ref']]))
            fp.Value().SetVisible(False)
            fp.Reference().SetLayer(pcb.F_Fab)
            if any(isinstance(g, pcb.PCB_TEXT) and g.GetText() == '${REFERENCE}' for g in fp.GraphicalItems()):
                fp.Reference().SetVisible(False)
            fp.Reference().SetTextSize(self.point(1, 1))
            fp.Reference().SetTextThickness(pcb.FromMM(0.15))
            seen = set()
            for pad in fp.Pads():
                number = pad.GetNumber()
                if not number:
                    continue
                if number not in part['nets']:
                    raise ValueError((part['ref'], 'unexpected pad', number))
                seen.add(number)
                key = (part['ref'], number)
                if key in self.pin_nets:
                    pad.SetNet(self.nets[self.pin_nets[key]])
                elif part['nets'][number] is not None:
                    raise ValueError((part['ref'], 'pad without a netlist node', number))
            if seen != set(part['nets']):
                raise ValueError((part['ref'], 'missing pads', sorted(set(part['nets']) - seen)))
            self.board.Add(fp)
            self.footprints[part['ref']] = fp

    def set_pose(self, fp, x, y, angle, side='F'):
        pcb = self.pcb
        if fp.IsFlipped() != (side == 'B'):
            fp.Flip(fp.GetPosition(), pcb.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(angle)
        fp.SetPosition(self.point(x, y))

    def courtyard(self, fp, side='F'):
        pcb = self.pcb
        layer = pcb.F_CrtYd if side == 'F' else pcb.B_CrtYd
        try:
            box = fp.GetCourtyard(layer).BBox()
            if box.GetWidth() <= 0 or box.GetHeight() <= 0:
                raise ValueError
        except Exception:  # footprint without a courtyard: fall back to the hull
            box = fp.GetBoundingHull().BBox()
        return [pcb.ToMM(box.GetX()), pcb.ToMM(box.GetY()), pcb.ToMM(box.GetRight()), pcb.ToMM(box.GetBottom())]

    def pose_geometry(self, ref, angle, side):
        """Local courtyard box and pad offsets of a footprint for one orientation/side (cached per footprint id)."""
        fp = self.footprints[ref]
        key = (self.by_ref[ref]['footprint'], angle, side)
        if key not in self.pose_cache:
            saved = (self.pcb.ToMM(fp.GetPosition()), fp.GetOrientationDegrees(), 'B' if fp.IsFlipped() else 'F')
            self.set_pose(fp, 0.0, 0.0, angle, side)
            box = self.courtyard(fp, side)
            pads = {pad.GetNumber(): tuple(self.pcb.ToMM(pad.GetPosition())) for pad in fp.Pads() if pad.GetNumber()}
            self.pose_cache[key] = (box, pads)
            self.set_pose(fp, saved[0][0], saved[0][1], saved[1], saved[2])
        return self.pose_cache[key]

    def place(self, ref, x, y, angle, side='F', region=None, check=True):
        fp = self.footprints[ref]
        self.set_pose(fp, x, y, angle, side)
        box = self.courtyard(fp, side)
        if check:
            for other, other_box, _ in self.occupied[side]:
                if boxes_overlap(box, other_box):
                    raise ValueError(('courtyard overlap', ref, other, [round(v, 3) for v in box], [round(v, 3) for v in other_box]))
            if box[0] < EDGE_COURTYARD or box[1] < EDGE_COURTYARD or box[2] > WIDTH - EDGE_COURTYARD or box[3] > HEIGHT - EDGE_COURTYARD:
                raise ValueError(('courtyard outside the board margin', ref, [round(v, 3) for v in box]))
        _, local_pads = self.pose_geometry(ref, angle, side)
        self.occupied[side].append((ref, box, self.gap_for(self.by_ref[ref], angle, local_pads)))
        self.placements[ref] = dict(x=round(x, 4), y=round(y, 4), angle=angle, side=side, region=region, courtyard=[round(v, 3) for v in box])
        return box

    # ----- placement stages ------------------------------------------------------------------------------------------
    def place_fixed(self):
        c = self.candidate
        dsp = c['dsp']
        self.place(dsp['ref'], dsp['xy'][0], dsp['xy'][1], dsp['angle'], region='dsp')
        for ref, (x, y, angle) in c['fixed'].items():
            if ref not in self.footprints:
                raise ValueError(f'fixed part {ref} is not in the model')
            self.place(ref, x, y, angle, region='fixed')
        for item in c['silkscreen']:
            self.occupied['F'].append((f"TEXT:{item['text']}", list(text_box(item['text'], item['xy'], item['size'])), (0.3, 0.3)))

    def dsp_pads(self, connected_only=True) -> list[dict]:
        dsp = self.footprints[self.candidate['dsp']['ref']]
        records = []
        for pad in dsp.Pads():
            net = pad.GetNetname()
            if connected_only and (not net or net.startswith('unconnected-')):
                continue
            records.append(dict(number=pad.GetNumber(), net=net, xy=tuple(self.pcb.ToMM(pad.GetPosition())), size=tuple(self.pcb.ToMM(pad.GetSize()))))
        return records

    def place_dsp_bypass(self):
        """DSP per-pin 100 nF capacitors: radial to their pin at the configured radius and side, laterally spread."""
        c = self.candidate
        dsp_ref = c['dsp']['ref']
        centre = tuple(self.pcb.ToMM(self.footprints[dsp_ref].GetPosition()))
        pads = {p['number']: p for p in self.dsp_pads(connected_only=False)}
        cfg = c['dsp_bypass']
        pitch = float(cfg.get('min_lateral_pitch_mm', 2.35))
        groups: dict = {}
        for part in self.parts:
            if 'near_dsp_pin' not in part:
                continue
            pad = pads[str(part['near_dsp_pin'])]
            rail = part['nets'].get('1')
            if rail not in cfg:
                raise ValueError(f"{part['ref']}: no dsp_bypass configuration for rail {rail}")
            dx, dy = pad['xy'][0] - centre[0], pad['xy'][1] - centre[1]
            if abs(dx) >= abs(dy):
                side_key, out, lateral = ('E' if dx > 0 else 'W'), (1 if dx > 0 else -1, 0), pad['xy'][1]
            else:
                side_key, out, lateral = ('S' if dy > 0 else 'N'), (0, 1 if dy > 0 else -1), pad['xy'][0]
            groups.setdefault((side_key, rail), []).append(dict(part=part, pad=pad, out=out, lateral=lateral))
        rails = sorted({rail for (_, rail) in groups})
        for rail in rails:
            radius = float(cfg[rail]['radius_mm'])
            side = cfg[rail]['side']
            queue = []
            for (side_key, r_), items in sorted(groups.items()):
                if r_ != rail:
                    continue
                items.sort(key=lambda it: it['lateral'])
                laterals = [it['lateral'] for it in items]
                for i in range(1, len(laterals)):  # spread to the minimum pitch, then re-centre the group on its pins
                    if laterals[i] - laterals[i - 1] < pitch:
                        laterals[i] = laterals[i - 1] + pitch
                shift = (sum(laterals) - sum(it['lateral'] for it in items)) / len(items)
                centre_lateral = centre[1] if items[0]['out'][0] else centre[0]
                for it, lateral in zip(items, [v - shift for v in laterals]):
                    queue.append((abs(lateral - centre_lateral), side_key, it, lateral, centre_lateral))
            # corner-most capacitors first: they keep their radial slot, the ones nearer the side centre nudge
            queue.sort(key=lambda q: (-q[0], q[1], q[2]['part']['ref']))
            for _, side_key, it, lateral, centre_lateral in queue:
                towards = 1.0 if centre_lateral >= lateral else -1.0
                offsets = [0.0] + [towards * 0.25 * k for k in range(1, 25)] + [-towards * 0.25 * k for k in range(1, 9)]
                placed = False
                for radial_step in range(0, 8):
                    r = radius - 0.5 * radial_step
                    for offset in offsets:
                        lat = snap(lateral + offset)
                        if abs(lat - centre_lateral) > radius + 0.5:  # never beyond the ring corner
                            continue
                        ux, uy = it['out']
                        x, y = (snap(centre[0] + ux * r), lat) if ux else (lat, snap(centre[1] + uy * r))
                        poses = []
                        for angle in (0, 90, 180, 270):
                            box, local_pads = self.pose_geometry(it['part']['ref'], angle, side)
                            p1 = (x + local_pads['1'][0], y + local_pads['1'][1])
                            poses.append((math.dist(p1, it['pad']['xy']), angle, box, local_pads))
                        poses.sort(key=lambda q: (round(q[0], 6), q[1]))
                        for _, angle, box, local_pads in poses:  # nearest pad 1 first; a blocked pose falls back to the next one
                            gx, gy = self.gap_for(it['part'], angle, local_pads)
                            candidate_box = [x + box[0], y + box[1], x + box[2], y + box[3]]
                            if any(boxes_overlap(candidate_box, other, gx if ref_ == dsp_ref else max(gx, og[0]), gy if ref_ == dsp_ref else max(gy, og[1]))
                                   for ref_, other, og in self.occupied[side]):
                                continue
                            self.place(it['part']['ref'], x, y, angle, side=side, region=f'dsp_bypass_{rail}')
                            placed = True
                            break
                        if placed:
                            break
                    if placed:
                        break
                if not placed:
                    ux, uy = it['out']
                    x, y = (snap(centre[0] + ux * radius), snap(lateral)) if ux else (snap(lateral), snap(centre[1] + uy * radius))
                    box, local_pads = self.pose_geometry(it['part']['ref'], 0, side)
                    gx, gy = self.gap_for(it['part'], 0, local_pads)
                    nominal = [x + box[0], y + box[1], x + box[2], y + box[3]]
                    blockers = [(ref, [round(v, 2) for v in other]) for ref, other, og in self.occupied[side]
                                if boxes_overlap(nominal, other, max(gx, og[0]), max(gy, og[1]))]
                    raise RuntimeError(f"no free position for DSP bypass {it['part']['ref']} ({side_key}/{rail}) near pin {it['pad']['number']}; "
                                       f"nominal {[round(v, 2) for v in nominal]} blocked by {blockers}")

    def placed_pads(self) -> dict:
        """(ref, number) -> dict(xy, net, kind) for every placed footprint."""
        table = {}
        for ref in self.placements:
            fp = self.footprints[ref]
            for pad in fp.Pads():
                if pad.GetNumber():
                    table[(ref, pad.GetNumber())] = dict(xy=tuple(self.pcb.ToMM(pad.GetPosition())), net=pad.GetNetname(), kind=self.by_ref[ref]['kind'])
        return table

    def anchors_for(self, part: dict, table: dict) -> dict:
        """net -> (weight, [(x, y), ...]) from placed pads sharing the part's nets (ground ignored; rails only for capacitors)."""
        anchors: dict = {}
        for number, net in part['nets'].items():
            if not net or net == GROUND:
                continue
            rail = net in RAILS
            if rail and part['kind'] != 'C':
                continue
            for (ref, pad_number), pad in table.items():
                if pad['net'] != net or ref == part['ref']:
                    continue
                if rail:
                    if pad['kind'] not in ('IC', 'DSP') or (ref, pad_number) in self.served_supply_pads:
                        continue
                    weight = 4
                else:
                    weight = 4 if pad['kind'] in ('IC', 'DSP', 'J', 'L') else 1
                entry = anchors.setdefault(net, [0, []])
                entry[0] = max(entry[0], weight)
                entry[1].append(pad['xy'])
        return anchors

    def gap_for(self, part: dict, angle: int, local_pads: dict):
        """(gap_x, gap_y) in mm a part needs around its courtyard for its escape vias and routing room."""
        if part['kind'] == 'TP':
            return GAP_TP, GAP_TP
        if part['kind'] in ('J', 'H'):
            return GAP_CONNECTOR, GAP_CONNECTOR
        if len(local_pads) == 2 and part['kind'] in ('C', 'R', 'D', 'L'):
            (ax, ay), (bx, by) = list(local_pads.values())
            return (GAP_AXIS, GAP_LATERAL) if abs(ax - bx) >= abs(ay - by) else (GAP_LATERAL, GAP_AXIS)
        along_x = sum(1 for (px, py) in local_pads.values() if abs(px) >= abs(py))
        along_y = len(local_pads) - along_x
        if along_x and along_y and min(along_x, along_y) >= len(local_pads) / 4:  # pins on all four sides (QFP)
            return GAP_QFP, GAP_QFP
        escape = GAP_IC_EP_ESCAPE if part['ref'] in {ref for ref, _ in INPAD_VIAS} else GAP_IC_ESCAPE  # exposed pad: two outward rows
        return (escape, GAP_IC_SIDE) if along_x >= along_y else (GAP_IC_SIDE, escape)

    def search_position(self, part: dict, rects: list, table: dict, region: str):
        """Greedy grid search over the region rectangles: minimum weighted Manhattan distance to the net anchors."""
        import numpy as np
        anchors = self.anchors_for(part, table)
        best = None
        for rect in rects:
            for angle in (0, 90, 180, 270):
                box, local_pads = self.pose_geometry(part['ref'], angle, 'F')
                gx, gy = self.gap_for(part, angle, local_pads)
                x_lo = math.ceil((rect[0] - box[0]) / PLACE_STEP) * PLACE_STEP
                x_hi = math.floor((rect[2] - box[2]) / PLACE_STEP) * PLACE_STEP
                y_lo = math.ceil((rect[1] - box[1]) / PLACE_STEP) * PLACE_STEP
                y_hi = math.floor((rect[3] - box[3]) / PLACE_STEP) * PLACE_STEP
                if x_hi < x_lo - 1e-9 or y_hi < y_lo - 1e-9:
                    continue
                xs = np.round(np.arange(x_lo, x_hi + PLACE_STEP / 2, PLACE_STEP), 4)
                ys = np.round(np.arange(y_lo, y_hi + PLACE_STEP / 2, PLACE_STEP), 4)
                X, Y = np.meshgrid(xs, ys)
                X, Y = X.ravel(), Y.ravel()
                valid = np.ones(X.shape, dtype=bool)
                for _, other, og in self.occupied['F']:
                    ex, ey = max(gx, og[0]), max(gy, og[1])
                    valid &= ~((X + box[0] - ex < other[2]) & (X + box[2] + ex > other[0]) & (Y + box[1] - ey < other[3]) & (Y + box[3] + ey > other[1]))
                if not valid.any():
                    continue
                X, Y = X[valid], Y[valid]
                if anchors:
                    cost = np.zeros(X.shape)
                    total_weight = 0.0
                    for net, (weight, points) in anchors.items():
                        pad_offsets = [local_pads[n] for n, pn in part['nets'].items() if pn == net and n in local_pads]
                        if not pad_offsets:
                            continue
                        net_cost = None
                        for ox, oy in pad_offsets:
                            for ax, ay in points:
                                d = np.abs(X + ox - ax) + np.abs(Y + oy - ay)
                                net_cost = d if net_cost is None else np.minimum(net_cost, d)
                        cost += weight * net_cost
                        total_weight += weight
                    cost /= max(total_weight, 1e-9)
                else:
                    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
                    cost = np.abs(X - cx) + np.abs(Y - cy)
                index = int(np.argmin(cost))
                score = (round(float(cost[index]), 6), angle, float(X[index]), float(Y[index]))
                if best is None or score < best:
                    best = score
        if best is None:
            inside = [ref for ref, other, _ in self.occupied['F'] if any(boxes_overlap(other, r) for r in rects)]
            raise RuntimeError(f"no placement space for {part['ref']} ({part['footprint']}) in region {region} {rects}; "
                               f"{len(inside)} items already inside: {inside}")
        return best

    def auto_place(self, part: dict, rects: list, table: dict, region: str):
        """Place in the region; when it is full, grow the rectangles in 1.5 mm steps (recorded as an issue)."""
        grown = [list(r) for r in rects]
        for step in range(0, 4):
            try:
                best = self.search_position(part, grown, table, region)
                break
            except RuntimeError:
                if step == 3:
                    raise
                grown = [[max(2.0, r[0] - 1.5), max(1.0, r[1] - 1.5), min(WIDTH - 2.0, r[2] + 1.5), min(HEIGHT - 1.0, r[3] + 1.5)] for r in grown]
                self.issues.append(f"{part['ref']}: region {region} full, rectangles grown by {1.5 * (step + 1)} mm")
        _, angle, x, y = best
        self.place(part['ref'], x, y, angle, region=region)
        if part['kind'] == 'C':  # a bypass capacitor serves the nearest unserved IC supply pad of its rail
            for number, net in part['nets'].items():
                if net in RAILS:
                    _, local_pads = self.pose_geometry(part['ref'], angle, 'F')
                    cap_pad = (x + local_pads[number][0], y + local_pads[number][1])
                    nearest = min(((math.dist(pad['xy'], cap_pad), key) for key, pad in table.items()
                                   if pad['net'] == net and pad['kind'] in ('IC', 'DSP') and key not in self.served_supply_pads), default=None)
                    if nearest and nearest[0] <= 6.0:
                        self.served_supply_pads.add(nearest[1])

    def place_all(self) -> dict:
        self.place_fixed()
        self.place_dsp_bypass()
        report = assignment_report(self.parts, self.candidate)
        if report['unassigned']:
            raise ValueError(f"parts without a region in candidate {self.candidate['id']}: {report['unassigned']}")
        remaining = [p for p in self.parts if p['ref'] not in self.placements]
        rank = {'IC': 0, 'DSP': 0, 'J': 1, 'L': 1, 'C': 2, 'D': 3, 'R': 4, 'TP': 5}
        remaining.sort(key=lambda p: (rank.get(p['kind'], 6), -len([n for n in p['nets'].values() if n]), gr.natural_ref_key(p['ref'])))
        for part in remaining:
            region = region_of(part, self.candidate)
            table = self.placed_pads()
            self.auto_place(part, self.candidate['regions'][region], table, region)
        return self.placements

    # ----- graphics --------------------------------------------------------------------------------------------------
    def add_outline(self):
        pcb = self.pcb
        for a, b in [((0, 0), (WIDTH, 0)), ((WIDTH, 0), (WIDTH, HEIGHT)), ((WIDTH, HEIGHT), (0, HEIGHT)), ((0, HEIGHT), (0, 0))]:
            edge = pcb.PCB_SHAPE(self.board)
            edge.SetShape(pcb.SHAPE_T_SEGMENT)
            edge.SetStart(self.point(*a))
            edge.SetEnd(self.point(*b))
            edge.SetLayer(pcb.Edge_Cuts)
            edge.SetWidth(pcb.FromMM(0.05))
            self.board.Add(edge)

    def add_silkscreen(self) -> list[dict]:
        pcb = self.pcb
        records = []
        for item in self.candidate['silkscreen']:
            text = pcb.PCB_TEXT(self.board)
            text.SetText(item['text'])
            text.SetPosition(self.point(*item['xy']))
            text.SetTextSize(self.point(item['size'], item['size']))
            text.SetTextThickness(pcb.FromMM(round(max(0.12, item['size'] * 0.15), 3)))
            text.SetLayer(pcb.F_SilkS)
            self.board.Add(text)
            bb = text.GetBoundingBox()
            box = [pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())]
            for ref, other, _ in self.occupied['F']:
                if ref.startswith('TEXT:'):
                    continue
                if boxes_overlap(box, other):
                    raise ValueError(f"silkscreen text {item['text']!r} overlaps the courtyard of {ref}")
            if box[0] < 0.5 or box[1] < 0.5 or box[2] > WIDTH - 0.5 or box[3] > HEIGHT - 0.5:
                raise ValueError(f"silkscreen text {item['text']!r} leaves the board")
            records.append(dict(text=item['text'], xy=item['xy'], size=item['size'], bbox=[round(v, 3) for v in box]))
        return records

    def save(self, path: Path):
        pcb = self.pcb
        path.parent.mkdir(parents=True, exist_ok=True)
        self.board.BuildConnectivity()
        pcb.SaveBoard(str(path), self.board)
        inject_stackup(path)
        loaded = pcb.LoadBoard(str(path))
        if loaded.GetCopperLayerCount() != len(COPPER_LAYERS):
            raise RuntimeError(f'reloaded board has {loaded.GetCopperLayerCount()} copper layers')
        return loaded


# --- board-level inspection ------------------------------------------------------------------------------------------


def dsp_net_order(escapes: list[dict], table: dict, centre, lanes: dict | None = None) -> list[str]:
    """DSP signal nets ordered for routing: inward lanes (pre-routed B.Cu exits) first, then the outward pins by side:
    straight-ahead nets, then lanes turning toward smaller laterals from the smallest lateral up, then lanes turning
    toward larger laterals from the largest lateral down, so that each turn on F.Cu lands beyond the previous one."""
    destinations = lane_destinations(escapes, table, 'U5')
    inward, outward = [], []
    for e in escapes:
        if e['net'] in RAILS or e['net'] == GROUND:
            continue
        (inward if e['direction'] == 'in' else outward).append(e)
    order = []
    for e in sorted(inward, key=lambda r: (r['side'], r['lateral'])):
        if e['net'] not in order:
            order.append(e['net'])
    by_side: dict = {}
    for e in outward:
        by_side.setdefault(e['side'], []).append(e)
    for side, items in sorted(by_side.items()):
        straight, left, right = [], [], []
        for e in items:
            d = destinations.get(e['net'])
            if d is None or abs(d - e['lateral']) <= STUB_TURN_MM:
                straight.append(e)
            elif d < e['lateral']:
                left.append(e)
            else:
                right.append(e)
        for e in sorted(straight, key=lambda r: r['lateral']) + sorted(left, key=lambda r: r['lateral']) + sorted(right, key=lambda r: -r['lateral']):
            if e['net'] not in order:
                order.append(e['net'])
    return order


def fine_pitch_ic_escapes(board, parts: list[dict], blocked=()) -> dict:
    """{ref: escape records} for every IC whose pad pitch is at or below FINE_PITCH_MAX (exposed pads excluded)."""
    import pcbnew as pcb
    by_ref = {p['ref']: p for p in parts}
    inpad = {(ref, number) for ref, number in INPAD_VIAS}
    result = {}
    taken = [tuple(v) for v in blocked]
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        part = by_ref.get(ref)
        if not part or part['kind'] != 'IC':
            continue
        centre = tuple(pcb.ToMM(fp.GetPosition()))
        pads = []
        for pad in fp.Pads():
            number = pad.GetNumber()
            net = pad.GetNetname()
            if not number or not net or net.startswith('unconnected-') or (ref, number) in inpad:
                continue
            size = tuple(pcb.ToMM(pad.GetSize()))
            if min(size) > 1.0:  # exposed pads and other large pads are not row pins
                continue
            pads.append(dict(number=number, net=net, xy=tuple(pcb.ToMM(pad.GetPosition())), size=size))
        if len(pads) < 4:
            continue
        laterals = sorted(classify_side(p['xy'], centre)[1] for p in pads)
        pitch = min((b - a for a, b in zip(laterals, laterals[1:]) if b - a > 1e-6), default=99.0)
        if pitch > FINE_PITCH_MAX:
            continue
        exposed = any(pcb.ToMM(pad.GetSize())[0] > 1.0 and pcb.ToMM(pad.GetSize())[1] > 1.0 for pad in fp.Pads() if pad.GetNumber())
        records = plan_ic_escapes(pads, centre, blocked=taken, inward_allowed=not exposed)
        taken.extend(tuple(r['via']) for r in records)
        result[ref] = records
    return result


def pad_table(board) -> dict:
    """(ref, number) -> dict(xy, net, thru) from a loaded board."""
    import pcbnew as pcb
    table = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNumber():
                table[(fp.GetReference(), pad.GetNumber())] = dict(xy=tuple(pcb.ToMM(pad.GetPosition())), net=pad.GetNetname(),
                                                                    thru=pad.GetAttribute() == pcb.PAD_ATTRIB_PTH, ref=fp.GetReference())
    return table


def rail_items(board) -> list[dict]:
    """Vias and plated through pads of the rail nets (the only copper that must reach the In2.Cu islands)."""
    import pcbnew as pcb
    items = []
    for item in board.GetTracks():
        if isinstance(item, pcb.PCB_VIA) and item.GetNetname() in RAILS:
            items.append(dict(net=item.GetNetname(), xy=[round(v, 4) for v in pcb.ToMM(item.GetPosition())], kind='via'))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() in RAILS and pad.GetAttribute() == pcb.PAD_ATTRIB_PTH:
                items.append(dict(net=pad.GetNetname(), xy=[round(v, 4) for v in pcb.ToMM(pad.GetPosition())], kind=f'pad {fp.GetReference()}.{pad.GetNumber()}'))
    return items


def copper_obstacles(board) -> list[dict]:
    """Every via and plated through pad on the board with its copper radius: In2.Cu corridor obstacles."""
    import pcbnew as pcb
    items = []
    for item in board.GetTracks():
        if isinstance(item, pcb.PCB_VIA):
            items.append(dict(net=item.GetNetname(), xy=[round(v, 4) for v in pcb.ToMM(item.GetPosition())], r=round(pcb.ToMM(item.GetWidth(getattr(pcb, ISLAND_LAYER.replace('.', '_')))) / 2, 4)))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute() == pcb.PAD_ATTRIB_PTH:
                size = pcb.ToMM(pad.GetSize())
                items.append(dict(net=pad.GetNetname(), xy=[round(v, 4) for v in pcb.ToMM(pad.GetPosition())], r=round(max(size) / 2, 4)))
    return items


def rail_smd_pads_without_via(board, report: dict) -> list[dict]:
    """Rail SMD pads whose fanout failed (from the router report) - they cannot reach the In2.Cu island."""
    failed = {(u['ref'], u['pad']) for u in report.get('unresolved', []) if u.get('stage') == 'fanout'}
    import pcbnew as pcb
    result = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() in RAILS and pad.GetAttribute() == pcb.PAD_ATTRIB_SMD and (fp.GetReference(), pad.GetNumber()) in failed:
                result.append(dict(ref=fp.GetReference(), pad=pad.GetNumber(), net=pad.GetNetname()))
    return result


def prune_dangling(board, protected_nets=()) -> dict:
    """Remove track ends and vias that connect to nothing (pre-routed stubs the router did not use), iteratively.

    A track end is connected when another track end, a via centre or a pad of the same net lies on it; a via is
    connected when at least two items (track ends on any layer, pads) meet at its centre. Vias of ``protected_nets``
    (zone nets: they connect through the filled islands and the ground plane) are never removed."""
    import pcbnew as pcb
    from collections import defaultdict
    protected = set(protected_nets)
    removed = dict(tracks=0, vias=0)
    pads_by_code = defaultdict(list)
    for pad in board.GetPads():
        pads_by_code[pad.GetNetCode()].append(pad)
    while True:
        items = list(board.GetTracks())
        tracks = [t for t in items if not isinstance(t, pcb.PCB_VIA)]
        vias = [t for t in items if isinstance(t, pcb.PCB_VIA)]
        ends = defaultdict(int)
        for t in tracks:
            for pt in (t.GetStart(), t.GetEnd()):
                ends[(t.GetNetCode(), pt.x, pt.y)] += 1
        via_keys = {(v.GetNetCode(), v.GetPosition().x, v.GetPosition().y) for v in vias}
        changed = False
        for t in tracks:  # every net: a track end connects only to another track end, a via or a pad (zones connect vias)
            for pt in (t.GetStart(), t.GetEnd()):
                key = (t.GetNetCode(), pt.x, pt.y)
                if ends[key] > 1 or key in via_keys or any(pad.HitTest(pt) for pad in pads_by_code[t.GetNetCode()]):
                    continue
                board.Remove(t)
                removed['tracks'] += 1
                changed = True
                break
        if changed:
            continue
        layers_at = defaultdict(set)
        for t in tracks:
            for pt in (t.GetStart(), t.GetEnd()):
                layers_at[(t.GetNetCode(), pt.x, pt.y)].add(t.GetLayer())
        for v in vias:
            if v.GetNetname() in protected:
                continue
            pos = v.GetPosition()
            layers = set(layers_at.get((v.GetNetCode(), pos.x, pos.y), set()))
            for pad in pads_by_code[v.GetNetCode()]:
                if pad.HitTest(pos):
                    layers.update(layer for layer in (pcb.F_Cu, pcb.B_Cu) if pad.IsOnLayer(layer))
            if len(layers) < 2:  # connected on one layer only (KiCad: via_dangling)
                board.Remove(v)
                removed['vias'] += 1
                changed = True
        if not changed:
            break
    return removed


def add_zones(board, zones: list[dict], save_path: Path) -> dict:
    """Add corridor zones with the grid router's zone API, refill every zone and save/reload."""
    router = gr.Router(board, WIDTH, HEIGHT, ROUTING_LAYERS, grid=GRID, trace=TRACE, clearance=CLEARANCE, via=VIA,
                       net_rules=NET_RULES, board_margin=BOARD_MARGIN, hole_clearance=HOLE_CLEARANCE)
    for zone in zones:
        router.zone(zone['net'], ISLAND_LAYER, [tuple(p) for p in zone['polygon']], priority=zone['priority'], clearance=ZONE_CLEARANCE,
                    min_thickness=ZONE_MIN_THICKNESS)
    router.fill()
    return gr.save_and_reload(board, save_path)


# --- comparison metrics ------------------------------------------------------------------------------------------------


def net_pads(table: dict, net: str) -> list:
    return [p['xy'] for p in table.values() if p['net'] == net]


def part_box(placements: dict, ref: str):
    return placements[ref]['courtyard'] if ref in placements else None


def union_box(boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def box_distance(a, b) -> float:
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return math.hypot(dx, dy)


def placement_estimates(table: dict, placements: dict, parts: list[dict], dsp_ref: str) -> dict:
    """Pre-routing, measurable floorplan criteria from pad centres and courtyards (Manhattan MST estimates)."""
    pwm = {name: round(sum(manhattan_mst(net_pads(table, n)) for n in nets), 2) for name, nets in PWM_CHAINS.items()}
    tz = {net: round(manhattan_mst(net_pads(table, net)), 2) for net in TZ_NETS}
    analog_nets = sorted({p['net'] for p in table.values() if p['net'] and p['net'].startswith(ANALOG_NETS)})
    analog_paths = {net: round(manhattan_mst(net_pads(table, net)), 2) for net in analog_nets}

    def refs_touching(predicate, exclude=()):
        refs = set()
        for (ref, _), pad in table.items():
            if ref in exclude or not pad['net']:
                continue
            if predicate(pad['net']):
                refs.add(ref)
        return sorted(refs)

    analog_refs = refs_touching(lambda n: n.startswith(ANALOG_SECTION_NETS), exclude=(dsp_ref, 'J8'))
    pwm_refs = refs_touching(lambda n: n in PWM_NETS, exclude=(dsp_ref, 'J8'))
    analog_box = union_box(part_box(placements, r) for r in analog_refs)
    pwm_box = union_box(part_box(placements, r) for r in pwm_refs)
    separation = box_distance(analog_box, pwm_box) if analog_box and pwm_box else None
    loops = {}
    for name, refs in SUPPLY_LOOPS.items():
        box = union_box(part_box(placements, r) for r in refs)
        loops[name] = dict(refs=refs, bbox_mm=[round(v, 2) for v in box] if box else None,
                           area_mm2=round((box[2] - box[0]) * (box[3] - box[1]), 1) if box else None)
    all_box = union_box(p['courtyard'] for p in placements.values())
    return dict(pwm_path_mm=pwm, pwm_path_total_mm=round(sum(pwm.values()), 2), tz_path_mm=tz, tz_path_total_mm=round(sum(tz.values()), 2),
                analog_path_mm=analog_paths, analog_path_total_mm=round(sum(analog_paths.values()), 2),
                analog_refs=analog_refs, pwm_refs=pwm_refs, analog_bbox_mm=analog_box, pwm_bbox_mm=pwm_box,
                analog_pwm_separation_mm=None if separation is None else round(separation, 2), supply_loops=loops,
                placed_bbox_mm=[round(v, 2) for v in all_box] if all_box else None,
                placed_bbox_fraction=round((all_box[2] - all_box[0]) * (all_box[3] - all_box[1]) / (WIDTH * HEIGHT), 3) if all_box else None,
                front_parts=sum(1 for p in placements.values() if p['side'] == 'F'), back_parts=sum(1 for p in placements.values() if p['side'] == 'B'))


def checker_metrics(board_path: Path, output_dir: Path, label: str) -> dict:
    """Run automation.verification.check_sic_layout on a board (in-process, needs pcbnew) and write its outputs."""
    from automation.verification import check_sic_layout as cl
    spec = cl.load_spec(SPEC_JSON)
    model = cl.load_model(MODEL_JSON)
    metrics = cl.run_check(board_path, spec, model, backend=None, spec_path=SPEC_JSON, model_path=MODEL_JSON)
    json_path, md_path = cl.write_outputs(metrics, output_dir, label)
    return dict(metrics=metrics, json=str(json_path), md=str(md_path))


def criteria_from(metrics: dict, estimates: dict) -> dict:
    """Flat comparison criteria (lower is better unless listed in COMPARISON_HIGHER_IS_BETTER)."""
    control = metrics.get('control', {})
    bypass = control.get('dsp_bypass', [])
    distances = [b['distance_mm'] for b in bypass]
    compact = metrics.get('compactness', {})
    courtyard = compact.get('courtyard_fraction', {}) or {}
    return {
        'dsp_bypass_max_mm': round(max(distances), 3) if distances else None,
        'dsp_bypass_mean_mm': round(sum(distances) / len(distances), 3) if distances else None,
        'dsp_bypass_count': len(distances),
        'pwm_path_mm': estimates['pwm_path_total_mm'],
        'tz_path_mm': estimates['tz_path_total_mm'],
        'analog_pwm_separation_mm': estimates['analog_pwm_separation_mm'],
        'analog_path_mm': estimates['analog_path_total_mm'],
        'supply_loop_area_mm2': {k: v['area_mm2'] for k, v in estimates['supply_loops'].items()},
        'courtyard_fraction_front': round(courtyard.get('front') or 0.0, 4),
        'courtyard_fraction_back': round(courtyard.get('back') or 0.0, 4),
        'placed_bbox_fraction': estimates['placed_bbox_fraction'],
        'analog_supply_separation_mm': control.get('bbox_separation_mm'),
    }


def score_candidates(criteria: dict) -> dict:
    """Weighted normalised score per candidate (0 = best on every criterion); ties resolved by id order."""
    ids = sorted(criteria)
    scores = {i: 0.0 for i in ids}
    detail = {}
    for key, weight in COMPARISON_WEIGHTS.items():
        values = {i: criteria[i].get(key) for i in ids}
        if any(v is None for v in values.values()):
            detail[key] = dict(skipped='missing value')
            continue
        lo, hi = min(values.values()), max(values.values())
        detail[key] = dict(values=values, weight=weight)
        for i in ids:
            norm = 0.0 if hi == lo else (values[i] - lo) / (hi - lo)
            if key in COMPARISON_HIGHER_IS_BETTER:
                norm = 1.0 - norm
            scores[i] += weight * norm
    winner = min(ids, key=lambda i: (round(scores[i], 6), i))
    return dict(scores={i: round(s, 4) for i, s in scores.items()}, detail=detail, selected=winner)


# --- build ------------------------------------------------------------------------------------------------------------


def build_control(candidate_json, output_pcb, *, route: bool = True, drc: bool = True, metrics: bool = True,
                  write_outputs: bool = True, metrics_dir: Path | None = None, metrics_label: str = 'control', cli=None,
                  plan_filter=None) -> dict:
    """Place (and optionally route, zone, check and DRC) one floorplan candidate into ``output_pcb``.

    Returns a result dict with the placement, the escape plan, the router report, the rail-island
    checks, the DRC manifest summary and the layout-metrics paths. Needs pcbnew (KiCad's Python).
    """
    import pcbnew as pcb
    start = time.monotonic()
    candidate = load_candidate(candidate_json)
    overlaps = islands_overlap(candidate)
    if overlaps:
        raise ValueError(f"candidate {candidate['id']}: rail islands overlap: {overlaps}")
    parts = load_parts()
    mapping = json.loads(MAPPING_JSON.read_text(encoding='utf-8'))['paths']
    cli = cli or find_kicad_cli()
    pin_nets = export_netlist(KICAD_DIR / f'{NAME}.kicad_sch', DESIGN_DIR / 'netlist_control.xml', cli)
    output_pcb = Path(output_pcb)
    builder = Builder(candidate, parts, mapping, pin_nets)
    placements = builder.place_all()
    builder.add_outline()
    silkscreen = builder.add_silkscreen()
    loaded = builder.save(output_pcb)
    result = dict(candidate=candidate['id'], candidate_file=str(candidate_json), board=str(output_pcb), footprints=len(builder.footprints), placement_issues=list(builder.issues),
                  nets=len(builder.nets), netlist_nodes=len(pin_nets), placements=placements, silkscreen=silkscreen,
                  assignment=assignment_report(parts, candidate), pcbnew_version=pcb.GetBuildVersion(), stackup_mm=stackup_thickness_mm())
    table = pad_table(loaded)
    result['estimates'] = placement_estimates(table, placements, parts, candidate['dsp']['ref'])
    if not route:
        result['seconds'] = round(time.monotonic() - start, 3)
        if write_outputs:
            write_placement(result, candidate)
        return result
    # ---- stage 1: escapes, fanout, signals, islands, ground plane --------------------------------------------------
    dsp_fp = next(fp for fp in loaded.GetFootprints() if fp.GetReference() == candidate['dsp']['ref'])
    centre = tuple(pcb.ToMM(dsp_fp.GetPosition()))
    dsp_pads = [dict(number=p.GetNumber(), net=p.GetNetname(), xy=tuple(pcb.ToMM(p.GetPosition())), size=tuple(pcb.ToMM(p.GetSize())))
                for p in dsp_fp.Pads() if p.GetNetname() and not p.GetNetname().startswith('unconnected-')]
    escapes = plan_dsp_escapes(dsp_pads, centre)
    ic_refs = [p['ref'] for p in parts if p['kind'] in ('IC', 'DSP')]
    ic_escapes = fine_pitch_ic_escapes(loaded, parts, blocked=[e['via'] for e in escapes]) if PREROUTE_ICS else {}
    lanes = lane_plan(escapes, lane_destinations(escapes, table, candidate['dsp']['ref']), centre)
    dsp_signal_nets = dsp_net_order(escapes, table, centre, lanes)
    plan = routing_plan(candidate, escapes, output_pcb, ic_refs=ic_refs, ic_escapes=ic_escapes, dsp_centre=centre, dsp_signal_nets=dsp_signal_nets,
                        lanes=lanes)
    if plan_filter is not None:  # diagnostics hook (tests, experiments): may restrict or adjust the plan before routing
        plan = plan_filter(plan)
    plan['escape_distances'] = list(ESCAPE_DISTANCES)  # recorded in the plan file; applied to the router module below
    default_distances = gr.ESCAPE_DISTANCES
    gr.ESCAPE_DISTANCES = tuple(ESCAPE_DISTANCES)
    try:
        report = gr.run_plan(loaded, {k: v for k, v in plan.items() if k != 'escape_distances'})
    finally:
        gr.ESCAPE_DISTANCES = default_distances
    pruned = prune_dangling(loaded, protected_nets=set(RAILS) | {GROUND})
    report['pruned_dangling'] = pruned
    if pruned['tracks'] or pruned['vias']:
        report['saved'] = gr.save_and_reload(loaded, output_pcb)
    if inject_stackup(output_pcb):
        report['stackup_reinjected'] = True
        gr.save_and_reload(pcb.LoadBoard(str(output_pcb)), output_pcb)
    # ---- stage 2: corridor zones for rail copper outside its island ------------------------------------------------
    board2 = pcb.LoadBoard(str(output_pcb))
    items = rail_items(board2)
    corridor_result = island_corridors(items, candidate['islands'], obstacles=copper_obstacles(board2))
    if corridor_result['corridors']:
        corridor_result['saved'] = add_zones(board2, corridor_result['corridors'], output_pcb)
    uncovered = uncovered_rail_items(items, candidate['islands'], corridor_result['corridors'])
    fanout_rail_failures = rail_smd_pads_without_via(board2, report)
    final_board = pcb.LoadBoard(str(output_pcb))
    board_counts = dict(tracks=sum(1 for t in final_board.GetTracks() if not isinstance(t, pcb.PCB_VIA)),
                        vias=sum(1 for t in final_board.GetTracks() if isinstance(t, pcb.PCB_VIA)), zones=len(list(final_board.Zones())))
    result.update(escapes=dict(records=escapes, inward=sum(e['direction'] == 'in' for e in escapes), outward=sum(e['direction'] == 'out' for e in escapes),
                               exceptions=[e for e in escapes if e['exception']], stubs=sum(1 for t in plan['pre_routed']['tracks'] if t['layer'] == 'B.Cu'),
                               lanes=lanes, ic_escapes={ref: len(recs) for ref, recs in ic_escapes.items()}),
                  routing_plan=plan, report=report, corridors=corridor_result, board_counts=board_counts,
                  rail_items_without_island_or_corridor=uncovered, rail_fanout_failures=fanout_rail_failures)
    # ---- metrics and DRC --------------------------------------------------------------------------------------------
    if metrics:
        result['layout_metrics'] = checker_metrics(output_pcb, metrics_dir or CHECKS_DIR, metrics_label)
        result['layout_metrics'].pop('metrics', None) if write_outputs else None
    if drc:
        from automation.kicad_tools.run_check import run_check
        code, manifest_path = run_check('drc', output_pcb, DRC_DIR, cli)
        manifest = read_manifest(manifest_path)
        result['drc'] = dict(manifest=str(manifest_path), wrapper_exit_code=code, tool_exit_code=manifest.get('tool_exit_code'),
                             status=manifest.get('status'), finding_count=manifest.get('finding_count'), violations=manifest.get('violations'),
                             unconnected_items=manifest.get('unconnected_items'), schematic_parity=manifest.get('schematic_parity'),
                             details=manifest.get('details', [])[:200], error=manifest.get('error'))
    result['seconds'] = round(time.monotonic() - start, 3)
    if write_outputs:
        write_placement(result, candidate)
        write_routing_outputs(result, candidate)
    return result


def write_placement(result: dict, candidate: dict):
    DESIGN_DIR.mkdir(parents=True, exist_ok=True)
    data = dict(schema_version=1, status=BANNER, project=NAME, candidate=candidate['id'], candidate_title=candidate['title'],
                board_mm=[WIDTH, HEIGHT], copper_layers=COPPER_LAYERS, stackup=[dict(layer=l, type=t, thickness_mm=th) for l, t, th in STACKUP],
                dsp=candidate['dsp'], dsp_bypass=candidate['dsp_bypass'], regions=candidate['regions'], islands=candidate['islands'],
                items=result['placements'], silkscreen=result.get('silkscreen', []), estimates=result.get('estimates'),
                placement_issues=result.get('placement_issues', []), notes=NOTES)
    (DESIGN_DIR / 'placement_control.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def write_routing_outputs(result: dict, candidate: dict):
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    plan = dict(result['routing_plan'])
    plan_doc = dict(schema_version=1, status=BANNER, project=NAME, candidate=candidate['id'], stage1_run_plan=plan,
                    stage2_corridor_zones=result['corridors']['corridors'], corridor_issues=result['corridors']['issues'],
                    dsp_escape_plan=dict(inward=result['escapes']['inward'], outward=result['escapes']['outward'], stubs=result['escapes']['stubs'],
                                         lanes=result['escapes'].get('lanes', {}), exceptions=result['escapes']['exceptions'],
                                         records=result['escapes']['records']),
                    fine_pitch_ic_escapes=result['escapes']['ic_escapes'],
                    notes=NOTES)
    (DESIGN_DIR / 'routing_plan_control.json').write_text(json.dumps(plan_doc, indent=2) + '\n', encoding='utf-8')
    report = result['report']
    counts = result.get('board_counts') or {}
    progress = dict(schema_version=1, status=BANNER, project=NAME, candidate=candidate['id'], generated_utc=datetime.now(timezone.utc).isoformat(),
                    board=result['board'], board_sha256=hashlib.sha256(Path(result['board']).read_bytes()).hexdigest(),
                    stage='routed' if not report.get('unresolved') else 'routed_with_unresolved_connections',
                    router_status=report.get('status'), tracks=counts.get('tracks'), vias=counts.get('vias'), zones=counts.get('zones'),
                    router_report_counts=dict(tracks=report.get('tracks'), vias=report.get('vias'), zones=report.get('zones')),
                    pruned_vias=report.get('pruned'), pruned_dangling=report.get('pruned_dangling'),
                    unresolved=report.get('unresolved'), unresolved_count=len(report.get('unresolved', [])),
                    net_length_mm=report.get('net_length_mm'), grid=report.get('grid'), routing_seconds=report.get('seconds'),
                    corridor_zones=len(result['corridors']['corridors']), corridor_issues=result['corridors']['issues'],
                    rail_items_without_island_or_corridor=result['rail_items_without_island_or_corridor'],
                    rail_fanout_failures=result['rail_fanout_failures'],
                    drc=result.get('drc'), layout_metrics=result.get('layout_metrics'), seconds=result['seconds'],
                    evidence_note='Only the kicad-cli DRC manifest listed under drc counts as verification; the router figures are geometric proposals.')
    (VERIFICATION_DIR / 'routing_progress_control.json').write_text(json.dumps(progress, indent=2, default=str) + '\n', encoding='utf-8')


# --- candidate comparison ----------------------------------------------------------------------------------------------


def evaluate_candidates(ids, scratch: Path, cli=None) -> dict:
    """Place every candidate unrouted into scratch/<id>/, measure it (checker + estimates) and score."""
    scratch = Path(scratch)
    results, criteria = {}, {}
    for cid in ids:
        out_dir = scratch / f'candidate_{cid}'
        out_dir.mkdir(parents=True, exist_ok=True)
        board_path = out_dir / f'{NAME}.kicad_pcb'
        result = build_control(candidate_path(cid), board_path, route=False, drc=False, metrics=False, write_outputs=False, cli=cli)
        checked = checker_metrics(board_path, out_dir, f'control_{cid}')
        result['layout_metrics_files'] = dict(json=checked['json'], md=checked['md'])
        criteria[cid] = criteria_from(checked['metrics'], result['estimates'])
        criteria[cid]['checker_rows'] = [r for r in checked['metrics']['rule_table'] if r['rule'] in ('PE-PCB-007', 'PE-PCB-008')]
        results[cid] = {k: v for k, v in result.items() if k not in ('placements',)}
        results[cid]['placements_count'] = len(result['placements'])
        print(f"candidate {cid}: placed {len(result['placements'])} parts in {result['seconds']} s; "
              f"PWM path {criteria[cid]['pwm_path_mm']} mm, TZ {criteria[cid]['tz_path_mm']} mm, analog/PWM separation "
              f"{criteria[cid]['analog_pwm_separation_mm']} mm, DSP bypass max {criteria[cid]['dsp_bypass_max_mm']} mm", flush=True)
    scoring = score_candidates(criteria)
    return dict(candidates=results, criteria=criteria, scoring=scoring, selected=scoring['selected'])


def comparison_markdown(evaluation: dict, final: dict | None) -> str:
    ids = sorted(evaluation['criteria'])
    crit = evaluation['criteria']
    lines = [f'**{BANNER}**', '', '# Control board floorplan candidates', '',
             'Two deterministic floorplans of the TMS320F28335 control board were placed with '
             '`automation/kicad_tools/generate_sic_control_board.py`, measured with the layout checker '
             '(`automation/verification/check_sic_layout.py`, spec `verification/engineering_checks/layout_spec_control.json`) and compared on '
             'the measurable criteria below before routing. Path figures are Manhattan minimum-spanning-tree estimates over pad centres '
             '(pre-routing proxies, not routed lengths); separations are courtyard bounding-box distances; the DSP bypass distances are the '
             'checker rows from the model `near_dsp_pin` pattern. Scores are weighted normalised sums (0 = best on every criterion, lower is better); '
             'the weights are an agent choice recorded in `COMPARISON_WEIGHTS` and need human review.', '']
    for cid in ids:
        cand = load_candidate(candidate_path(cid))
        lines += [f'## Candidate {cid}: {cand["title"]}', '', cand['description'], '']
        for note in cand.get('comparison_notes', []):
            lines.append(f'- {note}')
        lines.append('')
    lines += ['## Criteria', '']
    header = ['Criterion'] + [f'Candidate {i}' for i in ids] + ['Better']
    rows = []
    keys = [('dsp_bypass_max_mm', 'DSP bypass capacitor to pin, maximum (mm)', 'lower'), ('dsp_bypass_mean_mm', 'DSP bypass capacitor to pin, mean (mm)', 'lower'),
            ('pwm_path_mm', 'PWM chains ePWM1A/B -> gate -> 33 ohm -> J8 (Manhattan MST sum, mm)', 'lower'), ('tz_path_mm', 'TZ nets FAULT_N + OC_N (Manhattan MST sum, mm)', 'lower'),
            ('analog_pwm_separation_mm', 'Analogue section to PWM gating parts (courtyard bbox distance, mm)', 'higher'),
            ('analog_path_mm', 'Analogue nets (Manhattan MST sum, mm)', 'lower'), ('analog_supply_separation_mm', 'Control-section to supply-section courtyard bbox distance (checker PE-PCB-007 proxy; 0 = boxes overlap, mm)', 'higher'),
            ('courtyard_fraction_front', 'Courtyard fraction, front', 'info'), ('courtyard_fraction_back', 'Courtyard fraction, back', 'info'),
            ('placed_bbox_fraction', 'Placed parts bounding box / board area', 'info')]
    for key, label, better in keys:
        rows.append([label] + [str(crit[i].get(key)) for i in ids] + [better])
    for name in SUPPLY_LOOPS:
        rows.append([f'Supply loop bbox area: {name} (mm2)'] + [str(crit[i]['supply_loop_area_mm2'].get(name)) for i in ids] + ['lower'])
    lines += ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    lines += ['| ' + ' | '.join(r) + ' |' for r in rows]
    lines += ['', '## Scores', '']
    lines += ['| Criterion | Weight | ' + ' | '.join(ids) + ' |', '|---|---|' + '---|' * len(ids)]
    for key, detail in evaluation['scoring']['detail'].items():
        if 'skipped' in detail:
            lines.append(f'| {key} | - | ' + ' | '.join('n/a' for _ in ids) + ' |')
        else:
            lines.append(f"| {key} | {detail['weight']} | " + ' | '.join(str(detail['values'][i]) for i in ids) + ' |')
    lines.append(f"| **weighted score (lower is better)** | | " + ' | '.join(str(evaluation['scoring']['scores'][i]) for i in ids) + ' |')
    lines += ['', f"**Selected: candidate {evaluation['selected']}.**", '']
    if final:
        report = final.get('report', {})
        counts = final.get('board_counts') or report
        drc = final.get('drc') or {}
        lines += ['## Routed result of the selected candidate', '',
                  f"Board `{final['board']}`: {counts.get('tracks')} tracks, {counts.get('vias')} vias, {counts.get('zones')} zones (saved board counts), "
                  f"{len(report.get('unresolved', []))} unresolved router items, {len(final['corridors']['corridors'])} corridor zones, "
                  f"{final['escapes']['inward']} inward / {final['escapes']['outward']} outward DSP escapes "
                  f"({len(final['escapes']['exceptions'])} parity exceptions closed by corridors).",
                  '', f"DRC (kicad-cli, schematic parity, severity-all): status **{drc.get('status')}**, findings {drc.get('finding_count')} "
                  f"(violations {drc.get('violations')}, unconnected {drc.get('unconnected_items')}, parity {drc.get('schematic_parity')}), "
                  f"manifest `{drc.get('manifest')}`.", '']
        lengths = report.get('net_length_mm', {})
        lines += ['Routed track lengths of the compared nets (mm, router sum; the layout metrics file carries the pcbnew figures):', '']
        for net in list(PWM_CHAINS['PWM_H']) + list(PWM_CHAINS['PWM_L']) + list(TZ_NETS) + ['VIN_SENSE', 'VOUT_SENSE', 'ISENSE', 'ISENSE_REF']:
            lines.append(f'- {net}: {lengths.get(net)}')
        lines.append('')
    lines += ['## Limitations', '',
              '- Candidates differ in the DSP orientation and the connector arrangement; the supply corner, the 12V_PROT column and the mezzanine position are shared, so the supply-loop figures are equal by construction.',
              '- Manhattan MST estimates ignore layer changes and detours; routed lengths of the selected candidate are listed above for confirmation only.',
              '- The checker dispositions are measurements against spec proxies, not engineering acceptance (human review required).', '']
    return '\n'.join(lines)


def write_comparison(evaluation: dict, final: dict | None):
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    doc = dict(schema_version=1, status=BANNER, generated_utc=datetime.now(timezone.utc).isoformat(), weights=COMPARISON_WEIGHTS,
               higher_is_better=sorted(COMPARISON_HIGHER_IS_BETTER), criteria=evaluation['criteria'], scoring=evaluation['scoring'],
               selected=evaluation['selected'], candidates={k: {kk: vv for kk, vv in v.items() if kk not in ('silkscreen',)} for k, v in evaluation['candidates'].items()},
               final=None if not final else dict(board=final['board'], drc=final.get('drc'), unresolved=len(final['report'].get('unresolved', [])),
                                                 tracks=(final.get('board_counts') or final['report']).get('tracks'),
                                                 vias=(final.get('board_counts') or final['report']).get('vias'), corridors=len(final['corridors']['corridors']),
                                                 rail_items_without_island_or_corridor=final.get('rail_items_without_island_or_corridor'),
                                                 escapes=dict(inward=final['escapes']['inward'], outward=final['escapes']['outward'], exceptions=len(final['escapes']['exceptions'])),
                                                 net_length_mm=final['report'].get('net_length_mm')))
    (REVIEW_DIR / 'floorplan_candidates_control.json').write_text(json.dumps(doc, indent=2, default=str) + '\n', encoding='utf-8')
    (REVIEW_DIR / 'floorplan_candidates_control.md').write_text(comparison_markdown(evaluation, final), encoding='utf-8')


# --- CLI --------------------------------------------------------------------------------------------------------------


def summary_line(result: dict) -> str:
    report = result.get('report', {})
    counts = result.get('board_counts') or report
    drc = result.get('drc') or {}
    return (f"candidate {result['candidate']}: {result['footprints']} footprints, {counts.get('tracks')} tracks, {counts.get('vias')} vias, "
            f"{counts.get('zones')} zones, {len(report.get('unresolved', []))} unresolved, {len(result.get('corridors', {}).get('corridors', []))} corridors, "
            f"{len(result.get('rail_items_without_island_or_corridor', []))} rail items without island/corridor; "
            f"DRC {drc.get('status')} findings={drc.get('finding_count')} (violations {drc.get('violations')}, unconnected {drc.get('unconnected_items')}, "
            f"parity {drc.get('schematic_parity')}) manifest={drc.get('manifest')}; {result['seconds']} s")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--candidate', choices=['A', 'B'], help='build only this candidate (default: compare A and B, build the winner)')
    parser.add_argument('--scratch', type=Path, help='scratch directory for the candidate boards and their metrics')
    parser.add_argument('--output', type=Path, default=KICAD_DIR / f'{NAME}.kicad_pcb', help='board file of the built candidate')
    parser.add_argument('--no-route', action='store_true', help='placement only')
    parser.add_argument('--no-drc', action='store_true', help='skip the kicad-cli DRC (debugging only; never evidence)')
    parser.add_argument('--no-metrics', action='store_true', help='skip the layout metrics checker')
    parser.add_argument('--no-reexec', action='store_true', help='internal: do not re-execute under KiCad Python')
    args = parser.parse_args(argv)
    try:
        import pcbnew  # noqa: F401
    except ImportError:
        if args.no_reexec:
            print('pcbnew is not importable in this interpreter', file=sys.stderr)
            return 2
        python = kicad_python()
        if python is None:
            print('No Python interpreter with pcbnew was found (set AIPE_KICAD_PYTHON or .aipe/local-tools.json)', file=sys.stderr)
            return 2
        passthrough = list(sys.argv[1:] if argv is None else argv)
        completed = subprocess.run([str(python), str(Path(__file__).resolve()), *passthrough, '--no-reexec'], cwd=str(ROOT))
        return completed.returncode
    scratch = args.scratch or (ROOT / '.aipe' / 'control-board-candidates')
    cli = find_kicad_cli()
    if not cli:
        print('kicad-cli not found', file=sys.stderr)
        return 2
    if args.candidate:
        result = build_control(candidate_path(args.candidate), args.output, route=not args.no_route, drc=not args.no_drc, metrics=not args.no_metrics, cli=cli)
        print(summary_line(result) if not args.no_route else f"candidate {result['candidate']}: placed {len(result['placements'])} parts -> {result['board']}", flush=True)
        return 0
    evaluation = evaluate_candidates(('A', 'B'), scratch, cli=cli)
    selected = evaluation['selected']
    print(f"selected candidate {selected} (scores {evaluation['scoring']['scores']})", flush=True)
    final = None
    if not args.no_route:
        final = build_control(candidate_path(selected), args.output, route=True, drc=not args.no_drc, metrics=not args.no_metrics, cli=cli)
        print(summary_line(final), flush=True)
    else:
        final = None
        build_control(candidate_path(selected), args.output, route=False, drc=False, metrics=False, cli=cli)
    write_comparison(evaluation, final)
    print(f"comparison -> {REVIEW_DIR / 'floorplan_candidates_control.md'}", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
