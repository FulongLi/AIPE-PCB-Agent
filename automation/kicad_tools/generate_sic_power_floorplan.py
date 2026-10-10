"""Floorplan stage of the V2 SiC buck POWER board (AIPE_SiC_Buck_Power): place, zone and check candidate floorplans with pcbnew.

AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED

Companion of automation.kicad_tools.generate_sic_power_board (the routing-stage generator) and modelled on the completed
control-board generator (generate_sic_control_board.py) and v2_pipeline_smoke.board_stage(): kicad-cli XML netlist of the
project schematic, a pcbnew BOARD with the project footprint libraries and the symbol paths of
design/schematic_mapping_power.json, deterministic placement from a candidate file (fixed poses for every large or barrier
part, anchored grid placement inside named regions for the small parts with a net-aware courtyard-gap model and an
overlap check on both sides), the 4 x 70 um / 2.0 mm stackup injected as text, ISO_BARRIER rule-area segments between the
barrier parts, board-level 1.2 mm Edge.Cuts isolation slots under barrier footprints that carry none, the candidate's
power/ground zones filled through grid_router.Router.zone and refilled with the project rules, SaveBoard/LoadBoard, and the
floorplan checks (zone-band membership of every reference by its net classes, barrier orientation, heatsink keep-out,
film/inductor spacing, corridor heights, slot presence). Optional: the layout metrics checker, a kicad-cli DRC without
schematic parity into a scratch directory (floorplan comparison only) and the verification DRC through run_check.

Floorplan candidates live in design/floorplan_candidates/power_<A|B|C>.json; the three arrangements are compared on
measurable criteria (review/floorplan_candidates_power.md/.json) and the selected one is written to
design/placement_power.json with a routing-plan skeleton (design/routing_plan_power.json) for the routing stage.

Deterministic without KiCad: candidate loading and validation, net-class assignment, zone-band logic, spacing gaps, slot
geometry, the routing-plan skeleton, the stackup text and the comparison arithmetic. Requires native KiCad: netlist
export, footprint loading, placement/courtyards, zone fill, DRC and the metrics. Only the kicad-cli DRC manifest counts
as verification; placement checks are geometric proposals. Nothing is waived: every finding is reported with its path.

Run (re-executes itself under KiCad's bundled Python when pcbnew is not importable):
    python -m automation.kicad_tools.generate_sic_power_floorplan --candidate A|B|C [--output PATH] [--no-drc] [--drc-lite]
        [--no-metrics] [--scratch DIR] [--route]
    python -m automation.kicad_tools.generate_sic_power_floorplan --compare [--select] [--scratch DIR]
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import math
import os
import shutil
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
KICAD_DIR = EXAMPLE / 'kicad/power_board'
DESIGN_DIR = EXAMPLE / 'design'
VERIFICATION_DIR = EXAMPLE / 'verification'
REVIEW_DIR = EXAMPLE / 'review'
CANDIDATES_DIR = DESIGN_DIR / 'floorplan_candidates'
MODEL_JSON = DESIGN_DIR / 'circuit_power.json'
MAPPING_JSON = DESIGN_DIR / 'schematic_mapping_power.json'
SPEC_JSON = VERIFICATION_DIR / 'engineering_checks/layout_spec_power.json'
CHECKS_DIR = VERIFICATION_DIR / 'engineering_checks'
DRC_DIR = VERIFICATION_DIR / 'drc'
NAME = 'AIPE_SiC_Buck_Power'
TITLE = 'AIPE SiC buck 400 V -> 200 V / 5 kW - power board (SiC half bridge, drivers, isolators, SELV strip)'
BANNER = 'AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED'
REVISION = 'V2'
COPPER_LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
OUTER_LAYERS = ('F.Cu', 'B.Cu')
# Stackup (mm) written into the saved board as text (design/pcb_stackup.md section 1); pcbnew exposes no stackup mutation.
STACKUP = [('F.Cu', 'copper', 0.07), ('dielectric 1', 'prepreg', 0.2), ('In1.Cu', 'copper', 0.07),
           ('dielectric 2', 'core', 1.32), ('In2.Cu', 'copper', 0.07), ('dielectric 3', 'prepreg', 0.2), ('B.Cu', 'copper', 0.07)]
GRID, TRACE, CLEARANCE, HOLE_CLEARANCE = 0.25, 0.25, 0.25, 0.25
VIA = (0.6, 0.3)
POWER_VIA = (0.7, 0.3)  # 0.3 mm drill power-transition vias (>= 24 per 25 A transition, design_decisions standards_and_spacing.copper)
BOARD_MARGIN = 1.0
EDGE_COURTYARD = 0.4
PLACE_STEP = 0.5
ZONE_CLEARANCE, ZONE_MIN_THICKNESS = 0.3, 0.3
HV_ZONE_CLEARANCE = 0.5
SLOT_WIDTH, SLOT_EXTENSION = 1.2, 3.0  # board-level Edge.Cuts slot under a barrier footprint without its own NPTH slot
NPTH_ANNULUS_MM = 8.0  # copper-free annulus around the inductor standoff holes (inductor record)
HV_KEEPOUT_HS_MM = 5.0  # HV copper to the heatsink courtyard on the outer layers (KR-TH-002 proxy, baseline)
FILM_TO_HS_MM, INDUCTOR_TO_HS_MM, FILM_TO_INDUCTOR_MM = 20.0, 20.0, 15.0  # CR-23
CORRIDOR_PART_HEIGHT_MM = 15.0  # CR-26
HS_SELV_RULE_MM = 9.0
HV_FUNCTIONAL_MM = (3.0, 1.0)  # outer, inner
DRIVER_TO_GATE_MM = 15.0
HF_ROWS_MM = (5.0, 15.0)
# Project net classes (kicad/power_board/AIPE_SiC_Buck_Power.kicad_pro net_settings patterns); order matters for the
# first-match lookup, so HV_VIN's VIN_DIV_T* precedes SENSE_ISO's VIN_DIV.
NET_CLASS_PATTERNS = [
    ('HV_VIN', ['VIN_RAW', 'VIN', 'VIN_PRE', 'BLD_IN_*', 'IND_IN_*', 'DAMP_MID', 'VIN_DIV_T*']),
    ('HV_SW', ['SW', 'SNUB_MID']),
    ('HV_PGND', ['PGND', 'PE_REF_MID']),
    ('HV_VOUT', ['VOUT', 'VOUT_L', 'BLD_OUT_*', 'IND_OUT_*', 'VOUT_DIV_T*']),
    ('DRV_HS', ['HS_*', 'G_H', 'KS_H', 'VDD_H', 'VEE_H']),
    ('DRV_LS', ['LS_*', 'G_L', 'KS_L', 'VDD_L', 'VEE_L']),
    ('DESAT_HS', ['DESAT_H_*']),
    ('DESAT_LS', ['DESAT_L_*']),
    ('SENSE_ISO', ['ISO_*', '5V_ISO', 'VIN_DIV', 'VOUT_DIV']),
    ('PE', ['PE']),
    ('CTRL_SELV', ['*']),
]
HV_SIDE_CLASSES = {'HV_VIN', 'HV_SW', 'HV_PGND', 'HV_VOUT', 'DRV_HS', 'DRV_LS', 'DESAT_HS', 'DESAT_LS', 'SENSE_ISO', 'PE'}
HV_POWER_CLASSES = {'HV_VIN', 'HV_SW', 'HV_PGND', 'HV_VOUT'}
HS_ISLAND_CLASSES, LS_ISLAND_CLASSES = {'DRV_HS', 'DESAT_HS'}, {'DRV_LS', 'DESAT_LS'}
SELV_CLASSES = {'CTRL_SELV'}
BARRIER_REFS = ('U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U10')
GLOBAL_NETS = {'PGND', 'GND_CTRL'}  # never used as placement anchors
ANCHOR_PRIORITY_REFS = {'U1': 10, 'U3': 10}  # driver pins outweigh the bias-module pins for the shared rail nets
DECOUPLING_FIRST = ('C22', 'C23', 'C24', 'C25', 'C26', 'C42', 'C43', 'C44', 'C45', 'C46')  # UCC21710 VDD-COM / COM-VEE decoupling (KR-PCB-002)
RAIL_NETS = {'VIN', 'VOUT', 'SW', '3V3', '12V_PROT', 'VIN_RAW', 'VOUT_L'}  # anchors only for parts without another net
# Component heights (mm) for the corridor rule and the compactness metric (baseline envelopes; others are agent assumptions).
HEIGHTS = {'HS1': 50.0, 'L1': 48.0, 'C11': 37.0, 'C12': 37.0, 'C13': 45.0, 'C14': 45.0, 'RT1': 22.0, 'RV1': 23.0,
           'Q1': 23.6, 'Q2': 23.6, 'J1': 15.0, 'J2': 15.0, 'J3': 15.0, 'J4': 15.0, 'J5': 15.0, 'J6': 15.0,
           'J7': 8.5, 'J9': 12.0, 'J8': 9.0, 'C90': 10.5, 'C18': 13.0, 'C19': 13.0}
DEFAULT_HEIGHT = 3.0
# Courtyard-to-courtyard gaps (mm) for the anchored placement, by part spacing class (see spacing_class() / gap_between_parts()).
GAPS = {'HV': 3.2, 'PE': 5.2, 'DRV': 1.0, 'SELV': 0.9, 'TP': 0.8, 'J': 1.2, 'H': 1.0}
# Comparison weights (agent choice, recorded for review; lower score is better).
COMPARISON_WEIGHTS = {'power_path_mm': 2.0, 'power_path_layer_transitions': 1.0, 'hf_cap_row1_max_mm': 2.0, 'hf_pads_within_row2_min': 1.0,
                      'driver_to_gate_max_mm': 2.0, 'sw_copper_mm2': 1.0, 'hv_to_selv_min_mm': 1.5, 'heatsink_hv_min_mm': 1.0,
                      'film_to_heatsink_min_mm': 1.5, 'inductor_to_heatsink_mm': 1.5, 'film_to_inductor_min_mm': 1.0,
                      'tall_parts_in_corridors': 1.5, 'drc_lite_findings': 2.0, 'board_area_mm2': 0.5, 'placement_issues': 1.0}
COMPARISON_HIGHER_IS_BETTER = {'hf_pads_within_row2_min', 'hv_to_selv_min_mm', 'heatsink_hv_min_mm', 'film_to_heatsink_min_mm', 'inductor_to_heatsink_mm',
                               'film_to_inductor_min_mm'}
NOTES = [
    'Floorplan stage: all 237 parts are placed deterministically from the candidate file; zones are the candidate pours filled '
    'by pcbnew (refilled with the project rules) for the comparison; no tracks or vias exist yet, so every pad pair is an unconnected '
    'item in DRC by construction.',
    'The ISO_BARRIER band is realised as rule-area segments between the barrier parts (no copper of any kind, no footprints); '
    'the barrier parts themselves bridge it over their 1.2 mm slots, which the layout checker measures (KR-ISO-004).',
    'U1/U3 (UCC21710, official SOIC-16W footprint without a slot) receive a board-level 1.2 mm Edge.Cuts slot between the pad rows, '
    'extending 3 mm beyond the outermost pads (around-the-end path 2*sqrt((g/2)^2+e^2) = 9.4 mm for g = 7.25 mm).',
    'The 5 mm HV-copper keep-out around the PE-bonded heatsink courtyard puts the TO-247-4 lead row 7.5 mm from the sink face '
    '(baseline 3-5 mm); formed leads or a spacer are a mechanical review item.',
    'Heatsink corridors: intake and exhaust bands beside the sink (airflow along x) may hold parts <= 15 mm tall; the inductor '
    'is placed in the exhaust stream by design (CR-14) and is exempt from the corridor height rule but keeps >= 20 mm to the sink.',
    'The unconnected pins of the barrier packages (U1/U3 APWM pad 16, U10 NC pad 5) fall into the Default net class, which the 9 mm '
    'HV-to-SELV rule includes while the pin-field exceptions name only CTRL_SELV: 12 clearance findings inside the land patterns '
    '(7.25-8.64 mm) remain until the .kicad_dru / net-class patterns are amended (open issue, not a layout defect).',
    'Only the kicad-cli DRC manifest (run_check, schematic parity, severity-all) counts as verification; the DRC-lite run without '
    'parity in the scratch directory serves the floorplan comparison only.',
]
OPEN_ISSUES = [
    'DRU / net classes: the unconnected pins of U1/U3 (APWM, pad 16) and U10 (NC, pad 5) carry "unconnected-..." nets in the Default class; '
    'the 9 mm HV-to-SELV rule includes Default but the pin-field exceptions name only CTRL_SELV, so 12 clearance findings (7.25-8.64 mm) sit '
    'inside those land patterns on every build. Fix belongs to the project owner (.kicad_pro pattern or .kicad_dru exception), not the layout.',
    'Library: the AMC1311 DWV slot (10.4 mm) extends 2.995 mm beyond the pad rows, 5 um short of the 3.0 mm baseline (path 10.9 mm >= 9.0 mm); '
    'the official SOIC-16W silkscreen of U1/U3 crosses their board-level slots (4 silk_edge_clearance warnings; trimming the board copy would '
    'raise lib_footprint_mismatch instead).',
    'Mechanical: TO-247-4 lead row 7.5 mm from the sink face (5 mm HV-copper keep-out from the courtyard), baseline 3-5 mm - formed leads or a '
    'spacer; the LS source pin (second pin) cannot have a same-net HF capacitor pad within 5 mm (nearest 8.0 mm), the HS drain pin has 4.66 mm.',
    'Mezzanine: J7 pin 1 at (176, 163) with pins toward -x assumes the control board mounted rotated 180 deg about z (J8 at (28, 76) rotated '
    '90 deg); the two in-strip M3 holes (88, 163) / (200, 163) follow the 112 mm pattern, the other two M3 holes are spares - to be cross-checked '
    'with the control-board drawing.',
    'Metrics: PE-PCB-007 reports a 0 mm section separation because the barrier packages belong to both bounding boxes (artefact of the '
    'bounding-box proxy); PE-PCB-006 via counts are zero until routing.',
    'Candidate C (220 x 170 mm) could not place the PE group (two Y-capacitor discs and three 2512 links need 5 mm to every HV part) after '
    'sink, inductor, films and terminals; the stretch outline is confirmed infeasible with the baseline envelopes and spacings.',
    'Process: a parallel routing-stage generator owns automation/kicad_tools/generate_sic_power_board.py and will write design/placement_power.json, '
    'design/routing_plan_power.json and verification/routing_progress_power.json again when it routes; this floorplan stage keeps its own module '
    'generate_sic_power_floorplan.py and candidate/comparison files.',
]


# --- generic geometry ----------------------------------------------------------------------------------------------


def snap(value: float, grid: float = GRID) -> float:
    return round(round(value / grid) * grid, 6)


def boxes_overlap(a, b, gx: float = 0.0, gy: float = 0.0) -> bool:
    return a[0] - gx < b[2] and a[2] + gx > b[0] and a[1] - gy < b[3] and a[3] + gy > b[1]


def box_distance(a, b) -> float:
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return math.hypot(dx, dy)


def circle_box_distance(centre, radius, box) -> float:
    """Distance between a circle and an axis-aligned box (0 when they touch or overlap)."""
    cx, cy = centre
    px = min(max(cx, box[0]), box[2])
    py = min(max(cy, box[1]), box[3])
    return max(0.0, math.hypot(cx - px, cy - py) - radius)


def polygon_bbox(polygon):
    xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def point_in_polygon(point, polygon) -> bool:
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        (x0, y0), (x1, y1) = polygon[i], polygon[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def rect_polygon(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def text_box(text: str, xy, size: float):
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
    text = path.read_text(encoding='utf-8')
    if '(stackup' in text:
        return False
    if '(setup\n' not in text:
        raise ValueError(f'{path.name}: no (setup block to receive the stackup')
    text = text.replace('(paper "A4")', '(paper "A2")', 1).replace('(setup\n', '(setup\n' + stackup_text() + '\n', 1)
    path.write_text(text, encoding='utf-8')
    return True


# --- net classes, zone bands and spacing (pure) ------------------------------------------------------------------------


def net_class(net: str | None) -> str | None:
    """Project net class of a net name (first matching pattern, as the .kicad_pro assigns it)."""
    if not net:
        return None
    for name, patterns in NET_CLASS_PATTERNS:
        if any(fnmatch.fnmatchcase(net, p) for p in patterns):
            return name
    return None


def part_classes(part: dict) -> set:
    return {c for c in (net_class(n) for n in part['nets'].values() if n) if c}


def zone_of_part(part: dict) -> str:
    """'HV' | 'SELV' | 'BARRIER' | 'MECH' from the part's net classes (barrier parts carry both sides)."""
    classes = part_classes(part)
    hv = bool(classes & HV_SIDE_CLASSES)
    selv = bool(classes & SELV_CLASSES)
    if hv and selv:
        return 'BARRIER'
    if selv:
        return 'SELV'
    if hv:
        return 'HV'
    return 'MECH'


def spacing_class(part: dict) -> str:
    """Spacing class for the courtyard gaps: PE (5 mm rule), HV (3 mm functional), DRV (island), SELV, TP, J, H."""
    classes = part_classes(part)
    if 'PE' in classes:
        return 'PE'
    if part['kind'] == 'TP':
        return 'TP'
    if part['kind'] == 'H':
        return 'H'
    if part['kind'] == 'J':
        return 'J'
    if classes & HV_POWER_CLASSES or classes & {'SENSE_ISO'}:
        return 'HV'
    if classes & (HS_ISLAND_CLASSES | LS_ISLAND_CLASSES):
        return 'DRV'
    return 'SELV'


SAME_REFERENCE_PAIRS = {frozenset(p) for p in (('HV_SW', 'DRV_HS'), ('HV_SW', 'DESAT_HS'), ('HV_PGND', 'DRV_LS'), ('HV_PGND', 'DESAT_LS'),
                                                ('HV_PGND', 'SENSE_ISO'), ('DRV_HS', 'DESAT_HS'), ('DRV_LS', 'DESAT_LS'), ('DRV_LS', 'SENSE_ISO'),
                                                ('DESAT_LS', 'SENSE_ISO'))}


def class_pair_clearance(class_a: str, class_b: str) -> float:
    """Copper clearance (mm) the project rules require between two different nets of the given classes (outer layers)."""
    if 'PE' in (class_a, class_b):
        return 5.0
    if 'CTRL_SELV' in (class_a, class_b):
        return 9.0
    pair = frozenset((class_a, class_b))
    if pair in SAME_REFERENCE_PAIRS or (class_a == class_b and class_a not in HV_POWER_CLASSES):
        return 0.3
    return 3.0


def hv_side_nets(part: dict) -> set:
    """Nets of a part that belong to the HV side of the barrier (a barrier part's SELV pins lie 9 mm away in the strip)."""
    return {n for n in part['nets'].values() if n and net_class(n) in HV_SIDE_CLASSES}


def required_clearance(a: dict, b: dict):
    """Largest rule clearance between any two different HV-side nets of two parts (None when none applies).

    Barrier parts contribute only their HV-side pins: their SELV pins sit across the barrier band, so the 9 mm rule is
    met by the band itself and must not inflate the courtyard gap inside the driver islands."""
    worst = None
    for net_a in hv_side_nets(a):
        for net_b in hv_side_nets(b):
            if net_a == net_b:
                continue
            value = class_pair_clearance(net_class(net_a), net_class(net_b))
            worst = value if worst is None else max(worst, value)
    return worst


def gap_between_parts(a: dict, b: dict) -> float:
    """Courtyard-to-courtyard gap (mm) two parts need from each other, from their spacing classes and nets.

    PE-bonded items (PE net parts, M4 standoff holes) keep 5.2 mm from HV-side copper (5.0 mm rule + margin); two HV-side parts
    keep the largest rule clearance between any two different HV-side nets they carry plus 0.2 mm (3.2 mm across the HV groups,
    1.0 mm within a same-reference island); HV side to SELV side 9.2 mm (never in one band); SELV parts 0.9 mm; test points
    0.8 mm; connectors 1.2 mm; mechanical holes 1.0 mm."""
    ca, cb = spacing_class(a), spacing_class(b)
    hv_a = bool(part_classes(a) & (HV_SIDE_CLASSES - {'PE'}))
    hv_b = bool(part_classes(b) & (HV_SIDE_CLASSES - {'PE'}))
    selv_a = bool(part_classes(a) & SELV_CLASSES) and not hv_a
    selv_b = bool(part_classes(b) & SELV_CLASSES) and not hv_b
    if (hv_a and selv_b) or (hv_b and selv_a):
        return 9.2
    pe_a = ca == 'PE' or (a['kind'] == 'H' and a['footprint'].endswith('M4'))
    pe_b = cb == 'PE' or (b['kind'] == 'H' and b['footprint'].endswith('M4'))
    if (pe_a and hv_b) or (pe_b and hv_a):
        return GAPS['PE']
    if hv_a and hv_b:
        rule = required_clearance(a, b)
        return max(GAPS['DRV'], rule + 0.2) if rule is not None else GAPS['DRV']
    if ca == 'TP' or cb == 'TP':
        return GAPS['TP']
    if ca == 'J' or cb == 'J':
        return GAPS['J']
    if ca == 'H' or cb == 'H':
        return GAPS['H']
    return GAPS['SELV']


def part_height(ref: str) -> float:
    return float(HEIGHTS.get(ref, DEFAULT_HEIGHT))


# --- inputs ----------------------------------------------------------------------------------------------------------


def load_parts(path: Path = MODEL_JSON) -> list[dict]:
    parts = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(parts, list) or not parts:
        raise ValueError(f'{path}: expected a non-empty list of parts')
    refs = [p['ref'] for p in parts]
    if len(refs) != len(set(refs)):
        raise ValueError('duplicate references in the model')
    return parts


def candidate_path(candidate_id: str) -> Path:
    return CANDIDATES_DIR / f'power_{candidate_id}.json'


def load_candidate(path) -> dict:
    """Floorplan candidate JSON with structural validation (board, bands, fixed poses, regions, zones, heatsink spec)."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError(f'{path}: unsupported candidate schema_version {data.get("schema_version")}')
    for key in ('id', 'title', 'description', 'board_mm', 'bands', 'heatsink', 'fixed', 'regions', 'assign', 'zones', 'silkscreen'):
        if key not in data:
            raise ValueError(f'{path}: missing key {key!r}')
    width, height = data['board_mm']
    if not (100 <= width <= 400 and 100 <= height <= 400):
        raise ValueError(f'{path}: board_mm {data["board_mm"]} out of range')
    bands = data['bands']
    for key in ('hv_y_max', 'barrier', 'selv_y_min', 'barrier_line_y'):
        if key not in bands:
            raise ValueError(f'{path}: bands.{key} missing')
    b0, b1 = bands['barrier']
    if not (b0 < bands['barrier_line_y'] < b1 and bands['hv_y_max'] <= b0 and b1 <= bands['selv_y_min'] and b1 - b0 >= 10.0 - 1e-6):
        raise ValueError(f'{path}: bands must satisfy hv_y_max <= barrier[0] < line < barrier[1] <= selv_y_min and a >= 10 mm barrier')
    if height - bands['selv_y_min'] < 30.0 - 1e-6:
        raise ValueError(f'{path}: SELV strip must be >= 30 mm deep')
    for ref, pose in data['fixed'].items():
        if len(pose) != 4 or pose[3] not in ('F', 'B') or pose[2] % 90 != 0:
            raise ValueError(f'{path}: fixed {ref} needs [x, y, angle(multiple of 90), side F|B]')
        if not (0 <= pose[0] <= width and 0 <= pose[1] <= height):
            raise ValueError(f'{path}: fixed {ref} lies outside the board')
    for name, region in data['regions'].items():
        if region.get('side') not in ('F', 'B') or not region.get('rects'):
            raise ValueError(f'{path}: region {name} needs side F|B and rects')
        for rect in region['rects']:
            if len(rect) != 4 or rect[0] >= rect[2] or rect[1] >= rect[3]:
                raise ValueError(f'{path}: region {name} rect {rect} is degenerate')
            if rect[0] < EDGE_COURTYARD or rect[1] < EDGE_COURTYARD or rect[2] > width - EDGE_COURTYARD or rect[3] > height - EDGE_COURTYARD:
                raise ValueError(f'{path}: region {name} rect {rect} leaves less than the edge margin')
        if 'band' in region and region['band'] not in ('HV', 'SELV', 'BARRIER', 'ANY'):
            raise ValueError(f'{path}: region {name} band must be HV|SELV|BARRIER|ANY')
    seen = set()
    for zone in data['zones']:
        for key in ('net', 'layer', 'polygon', 'priority'):
            if key not in zone:
                raise ValueError(f'{path}: zone needs {key}: {zone}')
        if zone['layer'] not in COPPER_LAYERS:
            raise ValueError(f'{path}: zone layer {zone["layer"]} unknown')
        if len(zone['polygon']) < 3:
            raise ValueError(f'{path}: zone {zone["net"]}/{zone["layer"]} needs >= 3 points')
        box = polygon_bbox(zone['polygon'])
        if box[0] < BOARD_MARGIN - 1e-6 or box[1] < BOARD_MARGIN - 1e-6 or box[2] > width - BOARD_MARGIN + 1e-6 or box[3] > height - BOARD_MARGIN + 1e-6:
            raise ValueError(f'{path}: zone {zone["net"]}/{zone["layer"]} exceeds the board margin')
        key = (zone['layer'], zone['priority'])
        if key in seen:
            raise ValueError(f'{path}: zone priorities must be distinct per layer ({key})')
        seen.add(key)
        if net_class(zone['net']) in HV_SIDE_CLASSES and box[3] > bands['hv_y_max'] + 1e-6:
            raise ValueError(f'{path}: HV zone {zone["net"]}/{zone["layer"]} enters the barrier band')
        if net_class(zone['net']) in SELV_CLASSES and box[1] < bands['selv_y_min'] - 1e-6:
            raise ValueError(f'{path}: SELV zone {zone["net"]}/{zone["layer"]} enters the barrier band')
    hs = data['heatsink']
    for key in ('ref', 'airflow_axis', 'intake_side', 'corridor_mm', 'fan_mm'):
        if key not in hs:
            raise ValueError(f'{path}: heatsink.{key} missing')
    if hs['airflow_axis'] != 'x' or hs['intake_side'] not in ('left', 'right'):
        raise ValueError(f'{path}: heatsink airflow must be along x with intake left|right')
    return data


def region_of(part: dict, candidate: dict) -> str | None:
    assign = candidate['assign']
    ref = part['ref']
    if ref in assign.get('by_ref', {}):
        return assign['by_ref'][ref]
    for prefix, table in assign.get('by_net_prefix', {}).items():
        if ref.startswith(prefix) and not ref[len(prefix):].isalpha():
            nets = [n for n in part['nets'].values() if n]
            if nets and nets[0] in table:
                value = table[nets[0]]
                if isinstance(value, list):
                    index = int(''.join(ch for ch in ref if ch.isdigit()) or 0)
                    return value[index % len(value)]
                return value
    return assign.get('by_page', {}).get(part['page'])


def assignment_report(parts: list[dict], candidate: dict) -> dict:
    fixed = set(candidate['fixed'])
    report = dict(fixed=sorted(fixed), regions={}, unassigned=[], unknown_fixed=sorted(fixed - {p['ref'] for p in parts}))
    for part in parts:
        if part['ref'] in fixed:
            continue
        region = region_of(part, candidate)
        if region is None or region not in candidate['regions']:
            report['unassigned'].append(part['ref'])
        else:
            report['regions'].setdefault(region, []).append(part['ref'])
    return report


def band_of_y(y: float, bands: dict) -> str:
    if y <= bands['hv_y_max'] + 1e-6:
        return 'HV'
    if y >= bands['selv_y_min'] - 1e-6:
        return 'SELV'
    return 'BARRIER'


def band_violation(zone: str, courtyard, bands: dict) -> str | None:
    """Reason text when a part's courtyard sits outside the band its net classes require; None when consistent."""
    if zone == 'HV' and courtyard[3] > bands['hv_y_max'] + 0.05:
        return f'HV-side part reaches y={courtyard[3]:.2f} beyond the HV area ({bands["hv_y_max"]})'
    if zone == 'SELV' and courtyard[1] < bands['selv_y_min'] - 0.05:
        return f'SELV part reaches y={courtyard[1]:.2f} into the barrier/HV area (SELV strip starts at {bands["selv_y_min"]})'
    if zone == 'BARRIER' and not (courtyard[1] < bands['barrier_line_y'] < courtyard[3]):
        return f'barrier part courtyard {courtyard} does not straddle the barrier line y={bands["barrier_line_y"]}'
    return None


def heatsink_corridors(hs_box, spec: dict, board_mm) -> dict:
    """Intake/exhaust corridor rectangles (and the fan allowance) beside the sink courtyard, clipped to the board."""
    width, height = board_mm
    corridor, fan = float(spec['corridor_mm']), float(spec['fan_mm'])
    x0, y0, x1, y1 = hs_box
    if spec['intake_side'] == 'left':
        intake = [max(0.0, x0 - fan - corridor), y0, x0, y1]
        exhaust = [x1, y0, min(width, x1 + corridor), y1]
    else:
        intake = [x1, y0, min(width, x1 + fan + corridor), y1]
        exhaust = [max(0.0, x0 - corridor), y0, x0, y1]
    return dict(intake=[round(v, 3) for v in intake], exhaust=[round(v, 3) for v in exhaust],
                intake_on_board_mm=round(max(0.0, intake[2] - intake[0]), 3), exhaust_on_board_mm=round(max(0.0, exhaust[2] - exhaust[0]), 3))


# --- barrier slot geometry (pure) ------------------------------------------------------------------------------------


def slot_for_pads(hv_pads: list, selv_pads: list, width: float = SLOT_WIDTH, extension: float = SLOT_EXTENSION):
    """Board-level slot rectangle (x0, y0, x1, y1) between an HV and a SELV pad row given pad boxes (x0, y0, x1, y1).

    The gap axis is the axis of the larger centroid difference; the slot runs along the other axis through the middle of the
    land gap and extends ``extension`` beyond the outermost pad edges of both rows."""
    def centroid(boxes):
        return (sum((b[0] + b[2]) / 2 for b in boxes) / len(boxes), sum((b[1] + b[3]) / 2 for b in boxes) / len(boxes))
    c_hv, c_selv = centroid(hv_pads), centroid(selv_pads)
    gap_axis = 1 if abs(c_hv[1] - c_selv[1]) >= abs(c_hv[0] - c_selv[0]) else 0
    row_axis = 1 - gap_axis
    if gap_axis == 1:
        hv_inner = max(b[3] for b in hv_pads) if c_hv[1] < c_selv[1] else min(b[1] for b in hv_pads)
        selv_inner = min(b[1] for b in selv_pads) if c_hv[1] < c_selv[1] else max(b[3] for b in selv_pads)
    else:
        hv_inner = max(b[2] for b in hv_pads) if c_hv[0] < c_selv[0] else min(b[0] for b in hv_pads)
        selv_inner = min(b[0] for b in selv_pads) if c_hv[0] < c_selv[0] else max(b[2] for b in selv_pads)
    mid = (hv_inner + selv_inner) / 2
    gap = abs(selv_inner - hv_inner)
    lo = min(b[row_axis] for b in hv_pads + selv_pads) - extension
    hi = max(b[row_axis + 2] for b in hv_pads + selv_pads) + extension
    if gap_axis == 1:
        rect = (lo, mid - width / 2, hi, mid + width / 2)
    else:
        rect = (mid - width / 2, lo, mid + width / 2, hi)
    return dict(rect=[round(v, 4) for v in rect], land_gap_mm=round(gap, 4), row_axis='x' if row_axis == 0 else 'y',
                surface_path_mm=round(2 * math.sqrt((gap / 2) ** 2 + extension ** 2), 4))


def barrier_segments(strip, notches: list, margin: float = 0.3) -> list:
    """ISO_BARRIER rule-area rectangles: the strip (x0, y0, x1, y1) cut at every notch (x0, x1) inflated by ``margin``."""
    x0, y0, x1, y1 = strip
    cuts = sorted((max(x0, a - margin), min(x1, b + margin)) for a, b in notches)
    segments = []
    cursor = x0
    for a, b in cuts:
        if a - cursor >= 1.0:
            segments.append([round(cursor, 4), y0, round(a, 4), y1])
        cursor = max(cursor, b)
    if x1 - cursor >= 1.0:
        segments.append([round(cursor, 4), y0, round(x1, 4), y1])
    return segments


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
        by_type = {}
        for v in data.get('violations', []):
            by_type[v.get('type')] = by_type.get(v.get('type'), 0) + 1
        manifest['violations_by_type'] = dict(sorted(by_type.items()))
        manifest['details'] = [f"{v.get('type')}: {v.get('description')}" + (f" @ {v['items'][0].get('pos')}" if v.get('items') else '')
                               for key in ('violations', 'schematic_parity') for v in data.get(key, [])]
    return manifest


def project_files_beside(board_path: Path) -> list[str]:
    """Copy the project settings and rules next to a board in another directory, with an fp-lib-table pointing at the repository
    libraries (no library copy: Windows MAX_PATH would truncate long footprint names) so DRC and zone fills see the project rules."""
    copied = []
    target = board_path.parent
    if target.resolve() == KICAD_DIR.resolve():
        return copied
    for name in (f'{NAME}.kicad_pro', f'{NAME}.kicad_dru', f'{NAME}.kicad_sch'):
        source = KICAD_DIR / name
        if source.is_file():
            dest = target / (board_path.stem + source.suffix)
            shutil.copyfile(source, dest)
            copied.append(str(dest))
    for sheet in sorted(KICAD_DIR.glob('*.kicad_sch')):  # hierarchical sheets (and sym-lib-table) so that a parity DRC can read the schematic
        if sheet.name != f'{NAME}.kicad_sch':
            shutil.copyfile(sheet, target / sheet.name)
            copied.append(str(target / sheet.name))
    if (KICAD_DIR / 'sym-lib-table').is_file():
        sym = (KICAD_DIR / 'sym-lib-table').read_text(encoding='utf-8').replace('${KIPRJMOD}/libraries', (KICAD_DIR / 'libraries').resolve().as_posix())
        (target / 'sym-lib-table').write_text(sym, encoding='utf-8')
        copied.append(str(target / 'sym-lib-table'))
    table = (KICAD_DIR / 'fp-lib-table').read_text(encoding='utf-8')
    table = table.replace('${KIPRJMOD}/libraries', (KICAD_DIR / 'libraries').resolve().as_posix())
    dest = target / 'fp-lib-table'
    dest.write_text(table, encoding='utf-8')
    copied.append(str(dest))
    return copied


def drc_lite(board_path: Path, output_root: Path, cli=None) -> dict:
    """kicad-cli DRC WITHOUT schematic parity (severity-all, refill) for the floorplan comparison; never verification."""
    cli = cli or find_kicad_cli()
    if not cli:
        raise FileNotFoundError('kicad-cli unavailable')
    board_path = Path(board_path).resolve()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = Path(output_root).resolve() / f'{stamp}-drc-lite'
    output.mkdir(parents=True, exist_ok=True)
    report = output / 'drc.json'
    command = [str(cli), 'pcb', 'drc', '--format', 'json', '--severity-all', '--exit-code-violations', '--refill-zones',
               '--output', str(report), str(board_path)]
    manifest = dict(kind='drc-lite (no schematic parity; floorplan comparison only, not verification)', command=command,
                    source=str(board_path), source_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(), report=str(report))
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    (output / 'stdout.log').write_text(result.stdout, encoding='utf-8')
    (output / 'stderr.log').write_text(result.stderr, encoding='utf-8')
    manifest['tool_exit_code'] = result.returncode
    try:
        data = json.loads(report.read_text(encoding='utf-8-sig'))
        manifest['violations'] = len(data.get('violations', []))
        manifest['unconnected_items'] = len(data.get('unconnected_items', []))
        manifest['schematic_parity'] = len(data.get('schematic_parity', []))
        by_type = {}
        for v in data.get('violations', []):
            by_type[v.get('type')] = by_type.get(v.get('type'), 0) + 1
        manifest['violations_by_type'] = dict(sorted(by_type.items()))
        manifest['details'] = [f"{v.get('type')}: {v.get('description')}" + (f" @ {v['items'][0].get('pos')}" if v.get('items') else '')
                               for v in data.get('violations', [])]
        manifest['status'] = 'completed'
    except (OSError, ValueError) as exc:
        manifest['status'] = 'failed'
        manifest['error'] = str(exc)
    manifest_path = output / 'run.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    manifest['manifest'] = str(manifest_path)
    return manifest


class Builder:
    """pcbnew-bound board construction for one power-board candidate (placement, outline, slots, rule areas, zones, save)."""

    def __init__(self, candidate: dict, parts: list[dict], mapping: dict, pin_nets: dict):
        import pcbnew as pcb
        self.pcb = pcb
        self.candidate = candidate
        self.width, self.height = float(candidate['board_mm'][0]), float(candidate['board_mm'][1])
        self.bands = candidate['bands']
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
        self.circular: set = set()
        self.issues: list[str] = []
        self.slots: list[dict] = []
        self.rule_areas: list[dict] = []
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

    def is_through_hole(self, ref) -> bool:
        pcb = self.pcb
        return any(pad.GetAttribute() in (pcb.PAD_ATTRIB_PTH, pcb.PAD_ATTRIB_NPTH) for pad in self.footprints[ref].Pads())

    def is_circular(self, ref) -> bool:
        """True when the footprint's courtyard is a single circle (the toroid keep-out): overlap tests use the circle."""
        pcb = self.pcb
        fp = self.footprints[ref]
        return any(isinstance(g, pcb.PCB_SHAPE) and g.GetShape() == pcb.SHAPE_T_CIRCLE and g.GetLayer() == pcb.F_CrtYd for g in fp.GraphicalItems())

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
        except Exception:  # footprint without a courtyard on that side: fall back to the hull
            box = fp.GetBoundingHull().BBox()
        return [pcb.ToMM(box.GetX()), pcb.ToMM(box.GetY()), pcb.ToMM(box.GetRight()), pcb.ToMM(box.GetBottom())]

    def pose_geometry(self, ref, angle, side):
        """Local courtyard box, pad offsets and pad boxes of a footprint for one orientation/side (cached per footprint id)."""
        fp = self.footprints[ref]
        key = (self.by_ref[ref]['footprint'], angle, side)
        if key not in self.pose_cache:
            saved = (self.pcb.ToMM(fp.GetPosition()), fp.GetOrientationDegrees(), 'B' if fp.IsFlipped() else 'F')
            self.set_pose(fp, 0.0, 0.0, angle, side)
            box = self.courtyard(fp, side)
            pads = {pad.GetNumber(): tuple(self.pcb.ToMM(pad.GetPosition())) for pad in fp.Pads() if pad.GetNumber()}
            pad_boxes = []
            for pad in fp.Pads():
                if not pad.GetNumber():
                    continue
                bb = pad.GetBoundingBox()
                pad_boxes.append([self.pcb.ToMM(bb.GetX()), self.pcb.ToMM(bb.GetY()), self.pcb.ToMM(bb.GetRight()), self.pcb.ToMM(bb.GetBottom())])
            self.pose_cache[key] = (box, pads, pad_boxes)
            self.set_pose(fp, saved[0][0], saved[0][1], saved[1], saved[2])
        return self.pose_cache[key]

    def pad_boxes_of(self, ref) -> list:
        """Board-position bounding boxes of the numbered (copper) pads of a placed footprint."""
        pcb = self.pcb
        boxes = []
        for pad in self.footprints[ref].Pads():
            if not pad.GetNumber():
                continue
            bb = pad.GetBoundingBox()
            boxes.append([pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())])
        return boxes

    def gap_for(self, part: dict) -> float:
        return GAPS[spacing_class(part)]

    def gap_between(self, part: dict, other_ref: str) -> float:
        """Courtyard gap (mm) required between an auto-placed part and an occupied item (pairwise spacing classes)."""
        if other_ref.startswith('TEXT:'):
            return 0.3
        if '#' in other_ref:  # pseudo obstacle: 'REF#NPTH' (annulus already in the box) or 'REF#NET' (a single device pad)
            ref, tag = other_ref.split('#', 1)
            if tag == 'NPTH':
                return 0.3
            worst = 0.3
            for net in hv_side_nets(part):
                if net != tag:
                    worst = max(worst, class_pair_clearance(net_class(net), net_class(tag)))
            return worst + 0.2
        other = self.by_ref.get(other_ref)
        if other is None:
            return 0.5
        if other['kind'] == 'Q' and spacing_class(part) == 'DRV':
            return GAPS['DRV']  # the device courtyard: its pads carry their own net-aware obstacles
        return gap_between_parts(part, other)

    def obstacle_overlaps(self, ref, box, other_ref, other_box, gap=0.0) -> bool:
        """Box-vs-box overlap, or circle-vs-box when one of the two is a circular courtyard (inflated by ``gap``).

        'REF#NPTH' obstacles are copper-free annuli: only the copper (pad boxes) of ``ref`` must stay outside the circle."""
        if other_ref.endswith('#NPTH'):
            centre = ((other_box[0] + other_box[2]) / 2, (other_box[1] + other_box[3]) / 2)
            radius = (other_box[2] - other_box[0]) / 2
            return any(circle_box_distance(centre, radius, pbox) < gap - 1e-9 for pbox in self.pad_boxes_of(ref))
        if other_ref in self.circular:  # same test as the vectorised search: the candidate's box against the obstacle circle
            centre = ((other_box[0] + other_box[2]) / 2, (other_box[1] + other_box[3]) / 2)
            return circle_box_distance(centre, (other_box[2] - other_box[0]) / 2, box) < gap - 1e-9
        if ref in self.circular:
            centre = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            return circle_box_distance(centre, (box[2] - box[0]) / 2, other_box) < gap - 1e-9
        return boxes_overlap(box, other_box, gap, gap)

    def place(self, ref, x, y, angle, side='F', region=None, check=True):
        fp = self.footprints[ref]
        self.set_pose(fp, x, y, angle, side)
        box = self.courtyard(fp, side)
        if self.is_circular(ref):
            self.circular.add(ref)
        sides = ('F', 'B') if self.is_through_hole(ref) else (side,)
        if check:
            for s in sides:
                for other, other_box, _ in self.occupied[s]:
                    if self.obstacle_overlaps(ref, box, other, other_box):
                        raise ValueError(('courtyard overlap', ref, other, s, [round(v, 3) for v in box], [round(v, 3) for v in other_box]))
            if box[0] < EDGE_COURTYARD or box[1] < EDGE_COURTYARD or box[2] > self.width - EDGE_COURTYARD or box[3] > self.height - EDGE_COURTYARD:
                raise ValueError(('courtyard outside the board margin', ref, [round(v, 3) for v in box]))
        gap = self.gap_for(self.by_ref[ref])
        for s in sides:
            self.occupied[s].append((ref, box, gap))
        pcb = self.pcb
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            pbox = [pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())]
            if pad.GetAttribute() == pcb.PAD_ATTRIB_NPTH and ref in self.circular and self.by_ref[ref]['kind'] == 'L':
                # standoff holes of the toroid lie outside its circular courtyard: hole + 8 mm copper-free annulus (inductor record)
                cx, cy = pcb.ToMM(pad.GetPosition())
                radius = max(pcb.ToMM(pad.GetDrillSize())) / 2 + NPTH_ANNULUS_MM
                for s in ('F', 'B'):
                    self.occupied[s].append((f'{ref}#NPTH', [cx - radius, cy - radius, cx + radius, cy + radius], 0.0))
            elif self.by_ref[ref]['kind'] == 'Q' and pad.GetNumber():
                # device pads as individual net-aware obstacles: island parts may approach the KS/G/source pads (same-reference 0.3 mm)
                # while keeping the 3 mm functional distance from the drain pad of the other HV group
                for s in ('F', 'B'):
                    self.occupied[s].append((f'{ref}#{pad.GetNetname()}', pbox, 0.0))
        self.placements[ref] = dict(x=round(x, 4), y=round(y, 4), angle=angle, side=side, region=region, courtyard=[round(v, 3) for v in box],
                                    zone=zone_of_part(self.by_ref[ref]), through_hole=len(sides) == 2)
        return box

    # ----- placement stages ------------------------------------------------------------------------------------------
    def place_fixed(self):
        for ref, (x, y, angle, side) in self.candidate['fixed'].items():
            if ref not in self.footprints:
                raise ValueError(f'fixed part {ref} is not in the model')
            self.place(ref, x, y, angle, side, region='fixed')
        for item in self.candidate['silkscreen']:
            self.occupied['F'].append((f"TEXT:{item['text']}", list(text_box(item['text'], item['xy'], item['size'])), 0.3))

    def placed_pads(self) -> dict:
        table = {}
        for ref in self.placements:
            fp = self.footprints[ref]
            for pad in fp.Pads():
                if pad.GetNumber():
                    table[(ref, pad.GetNumber())] = dict(xy=tuple(self.pcb.ToMM(pad.GetPosition())), net=pad.GetNetname(), kind=self.by_ref[ref]['kind'])
        return table

    def anchors_for(self, part: dict, table: dict) -> dict:
        """net -> (weight, [(x, y), ...]) from placed pads sharing the part's nets (global nets ignored; rails only as a fallback)."""
        anchors: dict = {}
        nets = [n for n in part['nets'].values() if n and n not in GLOBAL_NETS]
        specific = [n for n in nets if n not in RAIL_NETS]
        use = specific if specific else nets
        for net in use:
            for (ref, pad_number), pad in table.items():
                if pad['net'] != net or ref == part['ref']:
                    continue
                weight = 4 if pad['kind'] in ('IC', 'Q', 'J', 'L') else 1
                if ref in ANCHOR_PRIORITY_REFS:  # gate drivers: their decoupling and gate parts cluster at the driver pins (KR-PCB-002)
                    weight = ANCHOR_PRIORITY_REFS[ref]
                entry = anchors.setdefault(net, [0, []])
                entry[0] = max(entry[0], weight)
                entry[1].append(pad['xy'])
        return anchors

    def search_position(self, part: dict, rects: list, side: str, table: dict, region: str):
        """Greedy grid search over the region rectangles: minimum weighted Manhattan distance to the net anchors."""
        import numpy as np
        anchors = self.anchors_for(part, table)
        sides = ('F', 'B') if self.is_through_hole(part['ref']) else (side,)
        best = None
        for rect in rects:
            for angle in (0, 90, 180, 270):
                box, local_pads, pad_boxes = self.pose_geometry(part['ref'], angle, side)
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
                for s in sides:
                    for other_ref, other, _ in self.occupied[s]:
                        g = self.gap_between(part, other_ref)
                        if other_ref.endswith('#NPTH'):  # copper-free annulus: every pad box of the candidate stays outside the circle
                            cx, cy, r = (other[0] + other[2]) / 2, (other[1] + other[3]) / 2, (other[2] - other[0]) / 2
                            for pb in pad_boxes:
                                ddx = np.maximum(np.maximum(X + pb[0] - cx, cx - (X + pb[2])), 0.0)
                                ddy = np.maximum(np.maximum(Y + pb[1] - cy, cy - (Y + pb[3])), 0.0)
                                valid &= np.hypot(ddx, ddy) >= r
                            continue
                        if other_ref in self.circular:  # toroid keep-out: nearest point of the candidate box to the circle centre
                            cx, cy, r = (other[0] + other[2]) / 2, (other[1] + other[3]) / 2, (other[2] - other[0]) / 2
                            ddx = np.maximum(np.maximum(X + box[0] - cx, cx - (X + box[2])), 0.0)
                            ddy = np.maximum(np.maximum(Y + box[1] - cy, cy - (Y + box[3])), 0.0)
                            valid &= np.hypot(ddx, ddy) >= r + g
                            continue
                        valid &= ~((X + box[0] - g < other[2]) & (X + box[2] + g > other[0]) & (Y + box[1] - g < other[3]) & (Y + box[3] + g > other[1]))
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
            inside = [ref for s in sides for ref, other, _ in self.occupied[s] if any(boxes_overlap(other, r) for r in rects)]
            raise RuntimeError(f"no placement space for {part['ref']} ({part['footprint']}) in region {region} {rects} side {side}; "
                               f"{len(inside)} items already inside: {sorted(set(inside))}")
        return best

    def band_limits(self, part: dict, region: dict):
        """(y_min, y_max) a grown region may reach for this part: never across the HV / barrier / SELV bands."""
        band = region.get('band') or zone_of_part(part)
        if band == 'HV' or (band == 'ANY' and zone_of_part(part) == 'HV'):
            return EDGE_COURTYARD, self.bands['hv_y_max'] - 0.5
        if band == 'SELV' or (band == 'ANY' and zone_of_part(part) == 'SELV'):
            return self.bands['selv_y_min'] + 0.5, self.height - EDGE_COURTYARD
        return EDGE_COURTYARD, self.height - EDGE_COURTYARD

    def auto_place(self, part: dict, region_name: str, table: dict):
        region = self.candidate['regions'][region_name]
        side = region['side']
        grown = [list(r) for r in region['rects']]
        y_lo, y_hi = self.band_limits(part, region)
        best = None
        for step in range(0, 6):
            try:
                best = self.search_position(part, grown, side, table, region_name)
                break
            except RuntimeError:
                if step == 5:
                    raise
                grown = [[max(EDGE_COURTYARD, r[0] - 1.5), max(y_lo, r[1] - 1.5), min(self.width - EDGE_COURTYARD, r[2] + 1.5),
                          min(y_hi, r[3] + 1.5)] for r in grown]
                self.issues.append(f"{part['ref']}: region {region_name} full, rectangles grown by {1.5 * (step + 1)} mm (within its band)")
        _, angle, x, y = best
        self.place(part['ref'], x, y, angle, side, region=region_name)

    def place_all(self) -> dict:
        self.place_fixed()
        report = assignment_report(self.parts, self.candidate)
        if report['unknown_fixed']:
            raise ValueError(f"fixed references not in the model: {report['unknown_fixed']}")
        if report['unassigned']:
            raise ValueError(f"parts without a region in candidate {self.candidate['id']}: {report['unassigned']}")
        remaining = [p for p in self.parts if p['ref'] not in self.placements]
        rank = {'IC': 0, 'Q': 0, 'J': 1, 'L': 1, 'D': 2, 'C': 3, 'R': 4, 'TP': 5, 'H': 6}

        def order(p):
            if p['ref'] in DECOUPLING_FIRST:  # driver rail decoupling takes the slots at the driver pins before the other island parts
                return (0.5, 0, gr.natural_ref_key(p['ref']))
            return (rank.get(p['kind'], 6), -len([n for n in p['nets'].values() if n]), gr.natural_ref_key(p['ref']))
        remaining.sort(key=order)
        for part in remaining:
            table = self.placed_pads()
            self.auto_place(part, region_of(part, self.candidate), table)
        return self.placements

    # ----- barrier parts: orientation check and slots -------------------------------------------------------------------
    def barrier_records(self) -> list[dict]:
        """Per barrier part: HV/SELV pad boxes, orientation check against the barrier line, slot (footprint NPTH or board)."""
        pcb = self.pcb
        records = []
        line = self.bands['barrier_line_y']
        for ref in self.placements:
            part = self.by_ref[ref]
            if zone_of_part(part) != 'BARRIER':
                continue
            fp = self.footprints[ref]
            hv, selv, npth = [], [], []
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                box = [pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())]
                if pad.GetAttribute() == pcb.PAD_ATTRIB_NPTH:
                    npth.append(box)
                    continue
                cls = net_class(pad.GetNetname()) if pad.GetNumber() else None
                if cls in SELV_CLASSES:
                    selv.append(box)
                elif cls in HV_SIDE_CLASSES:
                    hv.append(box)
            record = dict(ref=ref, hv_pads=len(hv), selv_pads=len(selv), hv_y_max=round(max(b[3] for b in hv), 3) if hv else None,
                          selv_y_min=round(min(b[1] for b in selv), 3) if selv else None)
            if hv and selv:
                record['hv_toward_hv_area'] = max(b[3] for b in hv) < line < min(b[1] for b in selv)
                if not record['hv_toward_hv_area']:
                    self.issues.append(f'{ref}: barrier part orientation wrong - HV pads must lie above the barrier line y={line} and SELV pads below')
                slot = slot_for_pads(hv, selv)
                record['land_gap_mm'] = slot['land_gap_mm']
                if npth:
                    record['slot'] = dict(kind='footprint NPTH', rects=[[round(v, 3) for v in b] for b in npth])
                    ext = min(min(b[0] for b in hv + selv) - min(n[0] for n in npth), max(n[2] for n in npth) - max(b[2] for b in hv + selv))
                    record['slot_extension_mm'] = round(ext, 3)
                else:
                    record['slot'] = dict(kind='board Edge.Cuts', rects=[slot['rect']])
                    record['slot_extension_mm'] = SLOT_EXTENSION
                    self.slots.append(dict(ref=ref, **slot))
                record['surface_path_mm'] = round(2 * math.sqrt((slot['land_gap_mm'] / 2) ** 2 + record['slot_extension_mm'] ** 2), 3)
            records.append(record)
        return records

    # ----- graphics --------------------------------------------------------------------------------------------------
    def add_outline(self):
        pcb = self.pcb
        W, H = self.width, self.height
        for a, b in [((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))]:
            edge = pcb.PCB_SHAPE(self.board)
            edge.SetShape(pcb.SHAPE_T_SEGMENT)
            edge.SetStart(self.point(*a))
            edge.SetEnd(self.point(*b))
            edge.SetLayer(pcb.Edge_Cuts)
            edge.SetWidth(pcb.FromMM(0.05))
            self.board.Add(edge)
        for slot in self.slots:
            x0, y0, x1, y1 = slot['rect']
            shape = pcb.PCB_SHAPE(self.board)
            shape.SetShape(pcb.SHAPE_T_RECT)
            shape.SetStart(self.point(x0, y0))
            shape.SetEnd(self.point(x1, y1))
            shape.SetLayer(pcb.Edge_Cuts)
            shape.SetWidth(pcb.FromMM(0.05))
            self.board.Add(shape)
            # The official SOIC silkscreen crosses the cut-out ("silkscreen clipped by board edge" warnings); it is kept so that the board
            # footprint stays identical to the library (trimming it would raise lib_footprint_mismatch instead). Reported, not waived.
            slot['silkscreen_note'] = 'library silkscreen crosses the slot (DRC warning silk_edge_clearance, cosmetic)'

    def add_rule_areas(self):
        """ISO_BARRIER segments between the barrier parts (all copper layers, nothing allowed) plus candidate keep-outs."""
        pcb = self.pcb
        b0, b1 = self.bands['barrier']
        notches = [(self.placements[r]['courtyard'][0], self.placements[r]['courtyard'][2]) for r in self.placements
                   if self.placements[r]['zone'] == 'BARRIER']
        segments = barrier_segments((BOARD_MARGIN, b0, self.width - BOARD_MARGIN, b1), notches)
        areas = [dict(name=f'ISO_BARRIER_{i + 1}', layers=COPPER_LAYERS, polygon=rect_polygon(*seg),
                      forbid=['tracks', 'vias', 'pads', 'copperpour', 'footprints']) for i, seg in enumerate(segments)]
        areas += [dict(a) for a in self.candidate.get('rule_areas', [])]
        for area in areas:
            zone = pcb.ZONE(self.board)
            zone.SetIsRuleArea(True)
            forbid = set(area.get('forbid', []))
            zone.SetDoNotAllowTracks('tracks' in forbid)
            zone.SetDoNotAllowVias('vias' in forbid)
            zone.SetDoNotAllowPads('pads' in forbid)
            zone.SetDoNotAllowFootprints('footprints' in forbid)
            if hasattr(zone, 'SetDoNotAllowZoneFills'):
                zone.SetDoNotAllowZoneFills('copperpour' in forbid)
            elif hasattr(zone, 'SetDoNotAllowCopperPour'):
                zone.SetDoNotAllowCopperPour('copperpour' in forbid)
            layers = pcb.LSET()
            for name in area['layers']:
                layer_id = self.board.GetLayerID(name)
                layers.addLayer(layer_id) if hasattr(layers, 'addLayer') else layers.AddLayer(layer_id)
            zone.SetLayerSet(layers)
            zone.SetZoneName(area['name'])
            outline = zone.Outline()
            outline.NewOutline()
            for x, y in area['polygon']:
                outline.Append(pcb.FromMM(x), pcb.FromMM(y))
            self.board.Add(zone)
            self.rule_areas.append(dict(name=area['name'], layers=list(area['layers']), bbox=[round(v, 3) for v in polygon_bbox(area['polygon'])],
                                        forbid=sorted(forbid)))
        return self.rule_areas

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
                if ref.startswith('TEXT:') or '#' in ref:
                    continue
                if boxes_overlap(box, other):
                    raise ValueError(f"silkscreen text {item['text']!r} overlaps the courtyard of {ref}")
            if box[0] < 0.5 or box[1] < 0.5 or box[2] > self.width - 0.5 or box[3] > self.height - 0.5:
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


REFILL_SCRIPT = (
    "import sys, pcbnew\n"
    "p = sys.argv[1]\n"
    "b = pcbnew.LoadBoard(p)\n"
    "b.BuildConnectivity()\n"
    "pcbnew.ZONE_FILLER(b).Fill(b.Zones())\n"
    "pcbnew.SaveBoard(p, b)\n"
    "print('refilled', len(list(b.Zones())))\n"
)


def refill_with_project_rules(board_path: Path) -> dict:
    """Refill every zone in a fresh KiCad Python process so the fill resolves the project's rule-based clearances.

    A BOARD() created in memory carries no project; pcbnew.LoadBoard() in a fresh interpreter loads the .kicad_pro/.kicad_dru that
    sit beside the board, and the saved fills (what the layout checker measures) then honour the net-class and custom rules."""
    python = kicad_python()
    if python is None:
        return dict(status='skipped', reason='no KiCad Python found')
    completed = subprocess.run([str(python), '-c', REFILL_SCRIPT, str(board_path)], capture_output=True, text=True, encoding='utf-8',
                               errors='replace', timeout=900, cwd=str(ROOT))
    return dict(status='ok' if completed.returncode == 0 else 'failed', returncode=completed.returncode,
                stdout=completed.stdout.strip()[-400:], stderr=completed.stderr.strip()[-800:])


def add_candidate_zones(board, candidate: dict, save_path: Path) -> dict:
    """Add the candidate's filled copper zones through the grid router's zone API, fill, save, refill with the project rules."""
    width, height = candidate['board_mm']
    router = gr.Router(board, width, height, ['F.Cu', 'B.Cu'], grid=GRID, trace=TRACE, clearance=CLEARANCE, via=VIA,
                       board_margin=BOARD_MARGIN, hole_clearance=HOLE_CLEARANCE)
    added = []
    for zone in candidate['zones']:
        if zone['net'] not in router.nets:
            raise ValueError(f"zone net {zone['net']} is not on the board")
        clearance = float(zone.get('clearance', HV_ZONE_CLEARANCE if net_class(zone['net']) in HV_SIDE_CLASSES else ZONE_CLEARANCE))
        router.zone(zone['net'], zone['layer'], [tuple(p) for p in zone['polygon']], priority=int(zone['priority']), clearance=clearance,
                    min_thickness=float(zone.get('min_thickness', ZONE_MIN_THICKNESS)), thermal_relief=bool(zone.get('thermal_relief', False)))
        added.append(dict(net=zone['net'], layer=zone['layer'], priority=zone['priority'], bbox=[round(v, 3) for v in polygon_bbox(zone['polygon'])]))
    router.fill()
    saved = gr.save_and_reload(board, save_path)
    refilled = refill_with_project_rules(save_path)
    return dict(zones=added, saved=saved, refill=refilled)


# --- floorplan checks (board-level, after placement) --------------------------------------------------------------------


def pad_table(board) -> dict:
    """(ref, number) -> dict(xy, net, box, thru, side) from a loaded board."""
    import pcbnew as pcb
    table = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNumber():
                continue
            bb = pad.GetBoundingBox()
            table[(fp.GetReference(), pad.GetNumber())] = dict(
                xy=tuple(pcb.ToMM(pad.GetPosition())), net=pad.GetNetname(), ref=fp.GetReference(),
                box=[pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())],
                thru=pad.GetAttribute() == pcb.PAD_ATTRIB_PTH, side='B' if fp.IsFlipped() else 'F')
    return table


def floorplan_checks(candidate: dict, placements: dict, table: dict, parts: list[dict]) -> dict:
    """Measurable floorplan rules from the placed geometry (soft: recorded, never waived)."""
    by_ref = {p['ref']: p for p in parts}
    bands = candidate['bands']
    hs_ref = candidate['heatsink']['ref']
    hs_box = placements[hs_ref]['courtyard']
    corridors = heatsink_corridors(hs_box, candidate['heatsink'], candidate['board_mm'])
    issues = []
    band_rows = []
    for ref, pose in placements.items():
        reason = band_violation(pose['zone'], pose['courtyard'], bands)
        if reason:
            issues.append(f'{ref}: {reason}')
            band_rows.append(dict(ref=ref, zone=pose['zone'], reason=reason))
    hv_min = None
    hv_hits = []
    for key, pad in table.items():
        cls = net_class(pad['net'])
        if cls not in HV_SIDE_CLASSES or pad['ref'] == hs_ref:
            continue
        d = box_distance(pad['box'], hs_box)
        if hv_min is None or d < hv_min:
            hv_min = d
        if d < HV_KEEPOUT_HS_MM - 1e-6:
            hv_hits.append(dict(pad=f'{key[0]}.{key[1]}', net=pad['net'], distance_mm=round(d, 3)))
    if hv_hits:
        issues.append(f'{len(hv_hits)} HV pads closer than {HV_KEEPOUT_HS_MM} mm to the {hs_ref} courtyard (first: {hv_hits[0]})')
    spacing = {}
    l1 = placements.get('L1')
    l1_centre = (l1['x'], l1['y']) if l1 else None
    l1_radius = 35.05
    for ref in ('C11', 'C12', 'C13', 'C14'):
        if ref not in placements:
            continue
        box = placements[ref]['courtyard']
        d_hs = box_distance(box, hs_box)
        d_l1 = circle_box_distance(l1_centre, l1_radius, box) if l1_centre else None
        spacing[ref] = dict(to_heatsink_mm=round(d_hs, 3), to_inductor_mm=None if d_l1 is None else round(d_l1, 3))
        if d_hs < FILM_TO_HS_MM - 1e-6:
            issues.append(f'{ref}: {d_hs:.1f} mm from the heatsink courtyard (< {FILM_TO_HS_MM} mm, CR-23)')
        if d_l1 is not None and d_l1 < FILM_TO_INDUCTOR_MM - 1e-6:
            issues.append(f'{ref}: {d_l1:.1f} mm from the inductor keep-out circle (< {FILM_TO_INDUCTOR_MM} mm, CR-23)')
    if l1_centre:
        d = circle_box_distance(l1_centre, l1_radius, hs_box)
        in_stream = corridors['exhaust'][1] <= l1_centre[1] <= corridors['exhaust'][3]
        spacing['L1'] = dict(to_heatsink_mm=round(d, 3), in_exhaust_stream=bool(in_stream))
        if d < INDUCTOR_TO_HS_MM - 1e-6:
            issues.append(f'L1: {d:.1f} mm from the heatsink courtyard (< {INDUCTOR_TO_HS_MM} mm, CR-23)')
    tall = []
    for ref, pose in placements.items():
        if ref in (hs_ref, 'L1') or part_height(ref) <= CORRIDOR_PART_HEIGHT_MM:
            continue
        for name in ('intake', 'exhaust'):
            if boxes_overlap(pose['courtyard'], corridors[name]):
                tall.append(dict(ref=ref, corridor=name, height_mm=part_height(ref)))
    if tall:
        issues.append(f'{len(tall)} parts taller than {CORRIDOR_PART_HEIGHT_MM} mm inside the heatsink corridors: ' + ', '.join(f"{t['ref']}({t['corridor']})" for t in tall))
    gate = {}
    for mosfet, driver, gate_pad in (('Q1', 'U1', '4'), ('Q2', 'U3', '4')):
        g = table.get((mosfet, gate_pad))
        outs = [table.get((driver, n)) for n in ('4', '6')]
        if g and all(outs):
            d = min(math.dist(g['xy'], o['xy']) for o in outs)
            gate[mosfet] = dict(driver=driver, distance_mm=round(d, 3), within_15mm=d <= DRIVER_TO_GATE_MM)
            if d > DRIVER_TO_GATE_MM:
                issues.append(f'{driver} output to {mosfet} gate pad {d:.1f} mm (> {DRIVER_TO_GATE_MM} mm)')
    hf = {}
    cap_pads = [p for (ref, _), p in table.items() if ref in {f'C{i}' for i in range(1, 11)}]
    for mosfet, pad_number, net in (('Q1', '1', 'VIN'), ('Q2', '2', 'PGND')):
        pin = table.get((mosfet, pad_number))
        if not pin:
            continue
        same = sorted(math.dist(pin['xy'], p['xy']) for p in cap_pads if p['net'] == net)
        hf[f'{mosfet}.{pad_number}'] = dict(net=net, nearest_mm=round(same[0], 3) if same else None,
                                            within_row1=sum(d <= HF_ROWS_MM[0] for d in same), within_row2=sum(d <= HF_ROWS_MM[1] for d in same))
        if not same or same[0] > HF_ROWS_MM[0]:
            issues.append(f'{mosfet} pin {pad_number} ({net}): no HF capacitor pad within {HF_ROWS_MM[0]} mm')
    hs_boxes = [placements[r]['courtyard'] for r in placements if part_classes(by_ref[r]) & HS_ISLAND_CLASSES and not part_classes(by_ref[r]) & LS_ISLAND_CLASSES]
    ls_boxes = [placements[r]['courtyard'] for r in placements if part_classes(by_ref[r]) & LS_ISLAND_CLASSES and not part_classes(by_ref[r]) & HS_ISLAND_CLASSES]
    island_gap = min((box_distance(a, b) for a in hs_boxes for b in ls_boxes), default=None)
    if island_gap is not None and island_gap < HV_FUNCTIONAL_MM[0]:
        issues.append(f'HS and LS island courtyards only {island_gap:.2f} mm apart (< {HV_FUNCTIONAL_MM[0]} mm outer barrier)')
    selv_pads = [p for p in table.values() if net_class(p['net']) in SELV_CLASSES]
    hv_pads = [p for p in table.values() if net_class(p['net']) in HV_SIDE_CLASSES]
    hv_selv_min, pair = None, None

    def shares_layer(a, b) -> bool:  # copper on a common layer only (a through pad is on every layer)
        return a['thru'] or b['thru'] or a['side'] == b['side']
    for a in hv_pads:
        for b in selv_pads:
            if a['ref'] == b['ref'] or not shares_layer(a, b):
                continue
            d = box_distance(a['box'], b['box'])
            if hv_selv_min is None or d < hv_selv_min:
                hv_selv_min, pair = d, (a['ref'], b['ref'])
    if hv_selv_min is not None and hv_selv_min < HS_SELV_RULE_MM:
        issues.append(f'HV pad to SELV pad only {hv_selv_min:.2f} mm between {pair} (< {HS_SELV_RULE_MM} mm)')
    return dict(issues=issues, band_violations=band_rows, heatsink_courtyard=hs_box, corridors=corridors,
                hv_pad_to_heatsink_min_mm=None if hv_min is None else round(hv_min, 3), hv_pads_inside_heatsink_keepout=hv_hits,
                spacing=spacing, tall_parts_in_corridors=tall, driver_to_gate=gate, hf_capacitors=hf,
                island_courtyard_gap_mm=None if island_gap is None else round(island_gap, 3),
                hv_to_selv_pad_min_mm=None if hv_selv_min is None else round(hv_selv_min, 3), hv_to_selv_pair=pair)


def power_path_estimate(table: dict, candidate: dict) -> dict:
    """VIN terminal -> Q1 drain -> SW -> L1 -> U10 -> VOUT terminal: pad-centre segments and the planned layer transitions."""
    def xy(ref, number):
        pad = table.get((ref, number))
        return pad['xy'] if pad else None
    chain = [('J1', '1'), ('RT1', '1'), ('RT1', '2'), ('J6', '1'), ('C11', '1'), ('Q1', '1'), ('Q1', '2'), ('Q2', '1'), ('L1', '1'), ('L1', '2'),
             ('U10', '1'), ('U10', '2'), ('C13', '1'), ('J3', '1')]
    points = [(f'{r}.{n}', xy(r, n)) for r, n in chain]
    segments, total = [], 0.0
    for (na, a), (nb, b) in zip(points, points[1:]):
        if a is None or b is None:
            continue
        d = math.dist(a, b)
        segments.append(dict(from_=na, to=nb, mm=round(d, 2)))
        total += d
    layers = candidate.get('power_path_layers', {})
    transitions = int(layers.get('transitions', 0))
    return dict(total_mm=round(total, 1), segments=segments, layer_transitions=transitions, layer_plan=layers.get('plan', []))


def checker_metrics(board_path: Path, output_dir: Path, label: str) -> dict:
    """Run automation.verification.check_sic_layout on a board (in-process, needs pcbnew) and write its outputs."""
    from automation.verification import check_sic_layout as cl
    spec = cl.load_spec(SPEC_JSON)
    model = cl.load_model(MODEL_JSON)
    metrics = cl.run_check(board_path, spec, model, backend=None, spec_path=SPEC_JSON, model_path=MODEL_JSON)
    json_path, md_path = cl.write_outputs(metrics, output_dir, label)
    return dict(metrics=metrics, json=str(json_path), md=str(md_path))


def criteria_from(result: dict) -> dict:
    """Flat comparison criteria (lower is better unless listed in COMPARISON_HIGHER_IS_BETTER)."""
    checks = result['checks']
    metrics = (result.get('layout_metrics') or {}).get('metrics') or {}
    iso = {p['name']: p for p in metrics.get('isolation', {}).get('pairs', [])}
    hv_selv = iso.get('HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers)', {}).get('min_mm')
    heat = metrics.get('heatsink', {}).get('per_layer', {})
    heat_min = min((e['min_distance_mm'] for e in heat.values() if e.get('min_distance_mm') is not None), default=None)
    sw = metrics.get('commutation', {}).get('sw_copper_mm2') or {}
    sw_total = round(sum(rec.get('total_mm2', 0.0) for rec in sw.values()), 1) if sw else None
    loops = {l['mosfet']: l for l in metrics.get('gate_loops', {}).get('loops', [])}
    d2g = [l.get('driver_output_to_gate_pad_mm') for l in loops.values() if l.get('driver_output_to_gate_pad_mm') is not None]
    hf = checks['hf_capacitors']
    row1 = [v['nearest_mm'] for v in hf.values() if v.get('nearest_mm') is not None]
    films = [v['to_heatsink_mm'] for k, v in checks['spacing'].items() if k != 'L1']
    film_l1 = [v['to_inductor_mm'] for k, v in checks['spacing'].items() if k != 'L1' and v.get('to_inductor_mm') is not None]
    drc = result.get('drc_lite') or {}
    width, height = result['board_mm']
    barrier = result.get('barrier', [])
    slots_ok = sum(1 for b in barrier if b.get('slot'))
    return {
        'board_area_mm2': width * height,
        'hv_area_utilisation': result.get('hv_area_utilisation'),
        'power_path_mm': result['power_path']['total_mm'],
        'power_path_layer_transitions': result['power_path']['layer_transitions'],
        'hf_cap_row1_max_mm': round(max(row1), 3) if row1 else None,
        'hf_pads_within_row2_min': result.get('hf_pads_within_row2_min'),
        'driver_to_gate_max_mm': round(max(d2g), 3) if d2g else (round(max(g['distance_mm'] for g in checks['driver_to_gate'].values()), 3) if checks['driver_to_gate'] else None),
        'sw_copper_mm2': sw_total,
        'hv_to_selv_min_mm': None if hv_selv is None else round(hv_selv, 3),
        'barrier_min_land_gap_mm': min((b['land_gap_mm'] for b in barrier if b.get('land_gap_mm') is not None), default=None),
        'barrier_slots_present': f'{slots_ok}/{len(barrier)}',
        'heatsink_hv_min_mm': None if heat_min is None else round(heat_min, 3),
        'film_to_heatsink_min_mm': round(min(films), 3) if films else None,
        'inductor_to_heatsink_mm': checks['spacing'].get('L1', {}).get('to_heatsink_mm'),
        'film_to_inductor_min_mm': round(min(film_l1), 3) if film_l1 else None,
        'tall_parts_in_corridors': len(checks['tall_parts_in_corridors']),
        'mezzanine_xy': result.get('mezzanine_xy'),
        'drc_lite_findings': drc.get('violations'),
        'drc_lite_by_type': drc.get('violations_by_type'),
        'placement_issues': len(result.get('placement_issues', [])) + len(checks['issues']),
    }


def score_candidates(criteria: dict) -> dict:
    ids = sorted(criteria)
    scores = {i: 0.0 for i in ids}
    detail = {}
    for key, weight in COMPARISON_WEIGHTS.items():
        values = {i: criteria[i].get(key) for i in ids}
        if any(v is None for v in values.values()):
            detail[key] = dict(skipped='missing value', values=values)
            continue
        lo, hi = min(values.values()), max(values.values())
        detail[key] = dict(values=values, weight=weight)
        for i in ids:
            if hi == lo:
                continue  # equal values: no candidate is penalised
            norm = (values[i] - lo) / (hi - lo)
            if key in COMPARISON_HIGHER_IS_BETTER:
                norm = 1.0 - norm
            scores[i] += weight * norm
    winner = min(ids, key=lambda i: (round(scores[i], 6), i))
    return dict(scores={i: round(s, 4) for i, s in scores.items()}, detail=detail, selected=winner)


# --- routing plan skeleton (pure) --------------------------------------------------------------------------------------


def routing_plan_skeleton(candidate: dict, save) -> dict:
    """grid_router plan skeleton for the routing agent: board, layers, rules, keepouts, power zones; validated by validate_plan."""
    width, height = candidate['board_mm']
    net_rules = {'VIN': dict(width=2.0, clearance=3.0, power=True), 'VIN_RAW': dict(width=2.0, clearance=3.0, power=True),
                 'SW': dict(width=2.0, clearance=3.0, power=True), 'PGND': dict(width=2.0, clearance=3.0, power=True),
                 'VOUT': dict(width=2.0, clearance=3.0, power=True), 'VOUT_L': dict(width=2.0, clearance=3.0, power=True),
                 'G_H': dict(width=1.0, clearance=0.3), 'G_L': dict(width=1.0, clearance=0.3),
                 'HS_OUTH': dict(width=1.0, clearance=0.3), 'HS_OUTL': dict(width=1.0, clearance=0.3), 'HS_CLMP': dict(width=0.5, clearance=0.3),
                 'LS_OUTH': dict(width=1.0, clearance=0.3), 'LS_OUTL': dict(width=1.0, clearance=0.3), 'LS_CLMP': dict(width=0.5, clearance=0.3),
                 'KS_H': dict(width=1.0, clearance=0.3, power=True), 'KS_L': dict(width=1.0, clearance=0.3, power=True),
                 'VDD_H': dict(width=0.5, clearance=0.3), 'VEE_H': dict(width=0.5, clearance=0.3), 'VDD_L': dict(width=0.5, clearance=0.3), 'VEE_L': dict(width=0.5, clearance=0.3),
                 '12V_PROT': dict(width=0.6), '3V3': dict(width=0.4), 'GND_CTRL': dict(width=0.4, power=True)}
    power = {}
    for zone in candidate['zones']:
        entry = power.setdefault(zone['net'], dict(stubs=False, priority=int(zone['priority']), clearance=float(zone.get('clearance', HV_ZONE_CLEARANCE)),
                                                   min_thickness=ZONE_MIN_THICKNESS, zones={}))
        entry['zones'][zone['layer']] = [list(p) for p in zone['polygon']]
    b0, b1 = candidate['bands']['barrier']
    keepouts = [dict(layer=None, rect=[BOARD_MARGIN, b0, width - BOARD_MARGIN, b1], net=None, vias=True,
                     note='ISO_BARRIER: no copper, no vias on any layer (barrier parts bridge it on their own pads)')]
    hs = candidate['fixed'][candidate['heatsink']['ref']]
    keepouts.append(dict(layer='F.Cu', rect=[round(hs[0] - 50.8 - HV_KEEPOUT_HS_MM, 3), round(hs[1] - 50.55 - HV_KEEPOUT_HS_MM, 3),
                                             round(hs[0] + 50.8 + HV_KEEPOUT_HS_MM, 3), round(hs[1] + 50.55 + HV_KEEPOUT_HS_MM, 3)], net=None, vias=True,
                         note='heatsink courtyard + 5 mm HV copper keep-out (outer layers); B.Cu equivalent to be added by the router stage'))
    plan = {
        'board': {'width': float(width), 'height': float(height), 'margin': BOARD_MARGIN},
        'layers': list(COPPER_LAYERS), 'grid': GRID, 'trace': TRACE, 'clearance': CLEARANCE, 'via': list(VIA), 'hole_clearance': HOLE_CLEARANCE,
        'directions': [None, 'h', 'v', None],
        'net_rules': net_rules,
        'keepouts': [{k: v for k, v in ko.items() if k != 'note'} for ko in keepouts],
        'pre_routed': {'tracks': [], 'vias': [], 'via_arrays': []},
        'fanout': {'order': ['U1', 'U3', 'U2', 'U4', 'U5', 'U6', 'U7', 'U10', 'U8', 'U9'], 'skip_refs': [], 'skip_pads': [], 'inpad_vias': []},
        'critical': ['G_H', 'HS_OUTH', 'HS_OUTL', 'HS_CLMP', 'G_L', 'LS_OUTH', 'LS_OUTL', 'LS_CLMP'], 'critical_layers': ['B.Cu'],
        'power': power,
        'signal_order': ['DESAT_', 'KS_', 'VDD_', 'VEE_', 'ISO_', '5V_ISO', 'VIN_DIV', 'VOUT_DIV', 'PWM_', 'FLT_', 'RDY_', 'OC_N', 'VIN_OUT', 'VOUT_OUT',
                         'VIN_AMP', 'VOUT_AMP', 'ISENSE', 'VIN_SENSE', 'VOUT_SENSE', '12V_', '3V3'],
        'signal_layers': ['F.Cu', 'B.Cu'], 'front_fallback': True,
        'ground': {'net': 'GND_CTRL', 'layers': ['In1.Cu'], 'clearance': ZONE_CLEARANCE, 'priority': 0,
                   'polygon': rect_polygon(BOARD_MARGIN, candidate['bands']['selv_y_min'] + 1.0, width - BOARD_MARGIN, height - BOARD_MARGIN)},
        'prune_vias': True, 'fill': True, 'save': str(save), 'strict': False, 'max_nodes': 2500000,
    }
    gr.validate_plan(plan)
    plan['keepout_notes'] = [ko['note'] for ko in keepouts]
    return plan


# --- build --------------------------------------------------------------------------------------------------------------


def hv_area_utilisation(placements: dict, candidate: dict, parts: list[dict]) -> float:
    """Courtyard area of HV-side and barrier parts (plus the sink) over the HV area (board width x hv_y_max)."""
    width = candidate['board_mm'][0]
    area = 0.0
    for ref, pose in placements.items():
        if pose['zone'] in ('HV', 'BARRIER') or ref == candidate['heatsink']['ref']:
            box = pose['courtyard']
            area += (box[2] - box[0]) * (box[3] - box[1])
    return round(area / (width * candidate['bands']['hv_y_max']), 3)


def build_power(candidate_json, output_pcb, *, route: bool = False, drc: bool = False, metrics: bool = True, drc_lite_dir: Path | None = None,
                write_outputs: bool = False, metrics_dir: Path | None = None, metrics_label: str = 'power', cli=None) -> dict:
    """Place one floorplan candidate into ``output_pcb`` (zones filled), run the floorplan checks and optional metrics / DRC.

    ``route`` is accepted for the CLI contract of the routing stage; the floorplan generator does not run the grid router
    (automation.kicad_tools.generate_sic_power_board does). Needs pcbnew (KiCad's Python)."""
    import pcbnew as pcb
    start = time.monotonic()
    candidate = load_candidate(candidate_json)
    parts = load_parts()
    mapping = json.loads(MAPPING_JSON.read_text(encoding='utf-8'))['paths']
    cli = cli or find_kicad_cli()
    pin_nets = export_netlist(KICAD_DIR / f'{NAME}.kicad_sch', DESIGN_DIR / 'netlist_power.xml', cli)
    output_pcb = Path(output_pcb)
    output_pcb.parent.mkdir(parents=True, exist_ok=True)
    copied = project_files_beside(output_pcb)
    builder = Builder(candidate, parts, mapping, pin_nets)
    placements = builder.place_all()
    barrier = builder.barrier_records()
    builder.add_outline()
    rule_areas = builder.add_rule_areas()
    silkscreen = builder.add_silkscreen()
    loaded = builder.save(output_pcb)
    zone_result = add_candidate_zones(loaded, candidate, output_pcb)
    if inject_stackup(output_pcb):
        gr.save_and_reload(pcb.LoadBoard(str(output_pcb)), output_pcb)
    final = pcb.LoadBoard(str(output_pcb))
    table = pad_table(final)
    checks = floorplan_checks(candidate, placements, table, parts)
    hf_row2 = []
    for mosfet, number, net in (('Q1', '1', 'VIN'), ('Q2', '2', 'PGND')):
        pin = table.get((mosfet, number))
        if pin:
            ds = [math.dist(pin['xy'], p['xy']) for (r, _), p in table.items() if r in {f'C{i}' for i in range(1, 11)} and p['net'] == net]
            hf_row2.append(sum(d <= HF_ROWS_MM[1] for d in ds))
    j7 = table.get(('J7', '1'))
    result = dict(candidate=candidate['id'], candidate_title=candidate['title'], candidate_file=str(candidate_json), board=str(output_pcb),
                  board_mm=list(candidate['board_mm']), bands=candidate['bands'], footprints=len(builder.footprints), nets=len(builder.nets),
                  netlist_nodes=len(pin_nets), placements=placements, placement_issues=list(builder.issues), barrier=barrier,
                  slots_added=builder.slots, rule_areas=rule_areas, zones=zone_result, silkscreen=silkscreen, project_files_copied=copied,
                  assignment=assignment_report(parts, candidate), checks=checks, power_path=power_path_estimate(table, candidate),
                  hv_area_utilisation=hv_area_utilisation(placements, candidate, parts),
                  hf_pads_within_row2_min=min(hf_row2) if hf_row2 else None,
                  mezzanine_xy=None if not j7 else [round(v, 3) for v in j7['xy']],
                  board_counts=dict(tracks=0, vias=0, zones=len(list(final.Zones()))), pcbnew_version=pcb.GetBuildVersion(),
                  stackup_mm=stackup_thickness_mm(), routed=False)
    if metrics:
        result['layout_metrics'] = checker_metrics(output_pcb, metrics_dir or output_pcb.parent, metrics_label)
    if drc_lite_dir is not None:
        result['drc_lite'] = drc_lite(output_pcb, drc_lite_dir, cli)
    if drc:
        from automation.kicad_tools.run_check import run_check
        code, manifest_path = run_check('drc', output_pcb, DRC_DIR, cli)
        manifest = read_manifest(manifest_path)
        result['drc'] = dict(manifest=str(manifest_path), wrapper_exit_code=code, tool_exit_code=manifest.get('tool_exit_code'),
                             status=manifest.get('status'), finding_count=manifest.get('finding_count'), violations=manifest.get('violations'),
                             violations_by_type=manifest.get('violations_by_type'), unconnected_items=manifest.get('unconnected_items'),
                             schematic_parity=manifest.get('schematic_parity'), details=manifest.get('details', [])[:200], error=manifest.get('error'))
    result['seconds'] = round(time.monotonic() - start, 3)
    result['criteria'] = criteria_from(result)
    if write_outputs:
        write_placement(result, candidate)
        write_routing_plan(result, candidate)
        write_progress(result, candidate, stage='floorplan-selected')
    return result


def compact_result(result: dict) -> dict:
    """Result without the per-part placements and the full metrics document (which lives in its own JSON file)."""
    compact = {k: v for k, v in result.items() if k != 'placements'}
    if 'layout_metrics' in compact and compact['layout_metrics']:
        lm = compact['layout_metrics']
        compact['layout_metrics'] = {k: v for k, v in lm.items() if k != 'metrics'} | dict(summary=(lm.get('metrics') or {}).get('summary'))
    return compact


def write_placement(result: dict, candidate: dict):
    DESIGN_DIR.mkdir(parents=True, exist_ok=True)
    data = dict(schema_version=1, status=BANNER, project=NAME, stage='floorplan-selected', generator='automation/kicad_tools/generate_sic_power_floorplan.py',
                candidate=candidate['id'], candidate_title=candidate['title'],
                board_mm=list(candidate['board_mm']), bands=candidate['bands'], copper_layers=COPPER_LAYERS,
                stackup=[dict(layer=l, type=t, thickness_mm=th) for l, t, th in STACKUP], heatsink=candidate['heatsink'],
                regions=candidate['regions'], zones=candidate['zones'], items=result['placements'], barrier=result['barrier'],
                slots_added=result['slots_added'], rule_areas=result['rule_areas'], silkscreen=result.get('silkscreen', []),
                checks=result['checks'], power_path=result['power_path'], placement_issues=result.get('placement_issues', []), notes=NOTES,
                open_issues=OPEN_ISSUES)
    (DESIGN_DIR / 'placement_power.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def write_routing_plan(result: dict, candidate: dict):
    plan = routing_plan_skeleton(candidate, KICAD_DIR / f'{NAME}.kicad_pcb')
    doc = dict(schema_version=1, status=BANNER, project=NAME, candidate=candidate['id'], stage='skeleton-for-routing-agent',
               generator='automation/kicad_tools/generate_sic_power_floorplan.py',
               stage1_run_plan={k: v for k, v in plan.items() if k != 'keepout_notes'}, keepout_notes=plan['keepout_notes'],
               routing_guidance=[
                   'Gate nets HS_OUTH/HS_OUTL -> R19/R20 -> G_H (and LS) as 1.0 mm tracks or pours on B.Cu directly under the device row; '
                   'KS_H / KS_L pours on In2.Cu beneath them (KR-PCB-001); never join KS_* to SW / PGND copper (KR-PCB-003).',
                   'VIN+ and PGND as overlapping pours F.Cu / In1.Cu under the HF tier (<= 20 nH board loop target); >= 24 x 0.3 mm vias per 25 A '
                   'layer transition; power pours >= 12 mm outer / >= 22 mm inner.',
                   'HV functional spacing 3.0 mm outer / 1.0 mm inner between VIN / SW / PGND / VOUT groups; HS/LS inter-island 3.0 / 1.0 mm; '
                   'HV to SELV 9.0 mm on all layers; HV copper >= 5 mm from the HS1 courtyard on the outer layers; nothing SELV in the HV area.',
                   'DESAT diodes D3/D5 keep the full 3.0 mm to every other group; drain runs short (KR-ISO-002).',
                   'Only kicad-cli DRC with --schematic-parity --severity-all through automation.kicad_tools.run_check counts as verification.'],
               notes=NOTES)
    (DESIGN_DIR / 'routing_plan_power.json').write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')


def write_progress(result: dict, candidate: dict, stage: str, extra: dict | None = None):
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    board = Path(result['board'])
    checks = result['checks']
    lm = result.get('layout_metrics') or {}
    layout_metrics = {k: v for k, v in lm.items() if k != 'metrics'} | dict(summary=(lm.get('metrics') or {}).get('summary')) if lm else None
    progress = dict(schema_version=1, status=BANNER, project=NAME, candidate=candidate['id'], generated_utc=datetime.now(timezone.utc).isoformat(),
                    stage=stage, generator='automation/kicad_tools/generate_sic_power_floorplan.py', board=str(board),
                    board_sha256=hashlib.sha256(board.read_bytes()).hexdigest() if board.is_file() else None,
                    board_mm=result['board_mm'], footprints=result['footprints'], tracks=result['board_counts']['tracks'], vias=result['board_counts']['vias'],
                    zones=result['board_counts']['zones'], routed=False,
                    unresolved_connections='all (floorplan stage: no tracks or vias yet; every pad pair of every net is unrouted)',
                    placement_issues=result.get('placement_issues', []), floorplan_issues=checks['issues'],
                    barrier=result['barrier'], slots_added=result['slots_added'], rule_areas=result['rule_areas'],
                    power_path=result['power_path'], checks={k: v for k, v in checks.items() if k not in ('issues',)}, criteria=result.get('criteria'),
                    layout_metrics=layout_metrics, drc_lite=result.get('drc_lite'), drc=result.get('drc'),
                    last_drc_manifest=(result.get('drc') or {}).get('manifest'), seconds=result['seconds'], open_issues=OPEN_ISSUES,
                    next_stage='route with automation/kicad_tools/generate_sic_power_board.py from design/placement_power.json and '
                               'design/routing_plan_power.json (candidate B poses, zones and keep-outs)',
                    evidence_note='Only a kicad-cli DRC manifest produced through automation.kicad_tools.run_check (schematic parity, severity-all) '
                                  'counts as verification; drc_lite (no parity, scratch) serves the floorplan comparison only.')
    if extra:
        progress.update(extra)
    (VERIFICATION_DIR / 'routing_progress_power.json').write_text(json.dumps(progress, indent=2, default=str) + '\n', encoding='utf-8')


# --- candidate comparison ----------------------------------------------------------------------------------------------


def evaluate_candidates(ids, scratch: Path, cli=None) -> dict:
    """Place every candidate unrouted into scratch/<id>/, measure it (checker, floorplan checks, DRC-lite) and score."""
    scratch = Path(scratch)
    results, criteria, failures = {}, {}, {}
    for cid in ids:
        out_dir = scratch / cid
        out_dir.mkdir(parents=True, exist_ok=True)
        board_path = out_dir / f'{NAME}.kicad_pcb'
        try:
            result = build_power(candidate_path(cid), board_path, metrics=True, drc_lite_dir=out_dir / 'drc', metrics_dir=out_dir,
                                 metrics_label=f'power_{cid}', cli=cli)
        except Exception as exc:  # a candidate that cannot be placed is a measurable outcome of the comparison
            failures[cid] = f'{type(exc).__name__}: {exc}'
            print(f'candidate {cid}: FAILED {failures[cid]}', flush=True)
            continue
        criteria[cid] = result['criteria']
        results[cid] = compact_result(result)
        results[cid]['placements_count'] = len(result['placements'])
        (out_dir / 'result.json').write_text(json.dumps(results[cid], indent=2, default=str) + '\n', encoding='utf-8')
        c = criteria[cid]
        print(f"candidate {cid}: placed {len(result['placements'])} parts in {result['seconds']} s; power path {c['power_path_mm']} mm, "
              f"HF row1 max {c['hf_cap_row1_max_mm']} mm, driver-gate max {c['driver_to_gate_max_mm']} mm, HV-SELV min {c['hv_to_selv_min_mm']} mm, "
              f"DRC-lite {c['drc_lite_findings']} violations {c['drc_lite_by_type']}, issues {c['placement_issues']}", flush=True)
    scoring = score_candidates(criteria) if criteria else dict(scores={}, detail={}, selected=None)
    return dict(candidates=results, criteria=criteria, scoring=scoring, selected=scoring['selected'], failures=failures)


CRITERIA_ROWS = [
    ('board_area_mm2', 'Board area (mm2)', 'lower'),
    ('hv_area_utilisation', 'HV-area utilisation (HV-side + barrier courtyards incl. sink / HV area)', 'info'),
    ('hf_cap_row1_max_mm', 'HF capacitor row 1: nearest same-net pad to Q1 drain / Q2 source, worse of the two (mm, <= 5)', 'lower'),
    ('hf_pads_within_row2_min', 'HF capacitor pads within 15 mm of the pin (same net), fewer of Q1 drain / Q2 source (count)', 'higher'),
    ('driver_to_gate_max_mm', 'Driver output pad to gate pad, worse of U1/Q1 and U3/Q2 (mm, <= 15)', 'lower'),
    ('power_path_mm', 'Power path J1 -> RT1 -> J6 -> C11 -> Q1 -> SW -> L1 -> U10 -> C13 -> J3 (pad-centre sum, mm)', 'lower'),
    ('power_path_layer_transitions', 'Planned layer transitions on the power path (count)', 'lower'),
    ('sw_copper_mm2', 'SW copper area, all layers (mm2, filled zones + pads)', 'lower'),
    ('hv_to_selv_min_mm', 'HV/DRV/DESAT/SENSE_ISO to CTRL_SELV minimum copper distance, any layer (mm, >= 9)', 'higher'),
    ('barrier_min_land_gap_mm', 'Smallest barrier-part land gap g (mm)', 'info'),
    ('barrier_slots_present', 'Barrier parts with a slot (footprint NPTH or board Edge.Cuts)', 'info'),
    ('heatsink_hv_min_mm', 'HV copper to the heatsink courtyard, outer layers (mm, >= 5)', 'higher'),
    ('film_to_heatsink_min_mm', 'Film capacitor courtyard to heatsink courtyard, minimum (mm, >= 20)', 'higher'),
    ('inductor_to_heatsink_mm', 'Inductor keep-out circle to heatsink courtyard (mm, >= 20)', 'higher'),
    ('film_to_inductor_min_mm', 'Film capacitor courtyard to inductor keep-out circle, minimum (mm, >= 15)', 'higher'),
    ('tall_parts_in_corridors', 'Parts taller than 15 mm inside the intake/exhaust corridors (count, inductor exempt)', 'lower'),
    ('mezzanine_xy', 'Mezzanine socket J7 pin 1 (x, y mm)', 'info'),
    ('drc_lite_findings', 'DRC-lite violations (kicad-cli, no parity, severity-all; unconnected items excluded)', 'lower'),
    ('drc_lite_by_type', 'DRC-lite violations by type', 'info'),
    ('placement_issues', 'Placement + floorplan rule issues recorded by the generator (count)', 'lower'),
]


def comparison_markdown(evaluation: dict, final: dict | None, scratch: Path) -> str:
    ids = sorted(evaluation['criteria'])
    crit = evaluation['criteria']
    lines = [f'**{BANNER}**', '', '# Power board floorplan candidates', '',
             'Three deterministic floorplans of the 400 V -> 200 V / 5 kW SiC buck power board were placed with '
             '`automation/kicad_tools/generate_sic_power_floorplan.py` (all 237 parts, zones filled, no routing), measured with the layout checker '
             '(`automation/verification/check_sic_layout.py`, spec `verification/engineering_checks/layout_spec_power.json`), the generator\'s '
             'floorplan checks and a kicad-cli DRC without schematic parity (DRC-lite, scratch only), and compared on the measurable criteria below. '
             'Pad-centre sums are pre-routing proxies, not routed lengths. Scores are weighted normalised sums (0 = best on every criterion, lower is '
             'better); the weights are an agent choice recorded in `COMPARISON_WEIGHTS` and need human review.', '',
             f'Scratch builds: `{scratch}` (one directory per candidate with the board, the project copies, `layout_metrics_power_<id>.json/.md`, '
             '`result.json` and `drc/<stamp>-drc-lite/run.json`).', '']
    for cid in sorted(set(ids) | set(evaluation.get('failures', {}))):
        cand = load_candidate(candidate_path(cid))
        lines += [f'## Candidate {cid}: {cand["title"]}', '', cand['description'], '']
        for note in cand.get('comparison_notes', []):
            lines.append(f'- {note}')
        if cid in evaluation.get('failures', {}):
            lines += ['', f"**Placement failed:** {evaluation['failures'][cid]}"]
        else:
            res = evaluation['candidates'][cid]
            lines += ['', f"Placed {res['placements_count']} parts; generator issues: {len(res.get('placement_issues', []))} placement "
                          f"(region growth within the band), {len(res['checks']['issues'])} floorplan rule findings:"]
            for issue in res['checks']['issues']:
                lines.append(f'  - {issue}')
            drc = res.get('drc_lite') or {}
            lines.append(f"DRC-lite: {drc.get('violations')} violations {drc.get('violations_by_type')}, {drc.get('unconnected_items')} unconnected items "
                         f"(unrouted by construction); manifest `{drc.get('manifest')}`.")
        lines.append('')
    lines += ['## Criteria', '']
    header = ['Criterion'] + [f'Candidate {i}' for i in ids] + ['Better']
    lines += ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    for key, label, better in CRITERIA_ROWS:
        lines.append('| ' + ' | '.join([label] + [str(crit[i].get(key)) for i in ids] + [better]) + ' |')
    lines += ['', '## Scores', '']
    lines += ['| Criterion | Weight | ' + ' | '.join(ids) + ' |', '|---|---|' + '---|' * len(ids)]
    for key, detail in evaluation['scoring']['detail'].items():
        if 'skipped' in detail:
            lines.append(f'| {key} | - | ' + ' | '.join(str(detail['values'].get(i)) for i in ids) + ' | (skipped: missing value)')
        else:
            lines.append(f"| {key} | {detail['weight']} | " + ' | '.join(str(detail['values'][i]) for i in ids) + ' |')
    lines.append('| **weighted score (lower is better)** | | ' + ' | '.join(str(evaluation['scoring']['scores'][i]) for i in ids) + ' |')
    lines += ['', f"**Selected: candidate {evaluation['selected']}.**", '']
    lines += ['## Selection rationale', '']
    for line in evaluation.get('rationale', []):
        lines.append(f'- {line}')
    if final:
        lines += ['', '## Selected candidate written to the repository', '',
                  f"Board `{final['board']}` (placed, zones filled, unrouted): {final['footprints']} footprints, {final['board_counts']['zones']} zones; "
                  f"`design/placement_power.json`, `design/routing_plan_power.json` (skeleton) and `verification/routing_progress_power.json` "
                  f"(stage floorplan-selected) were written.", '']
        drc = final.get('drc') or {}
        if drc:
            lines += [f"Verification DRC (run_check, schematic parity, severity-all): status **{drc.get('status')}**, findings {drc.get('finding_count')} "
                      f"(violations {drc.get('violations')} {drc.get('violations_by_type')}, unconnected {drc.get('unconnected_items')} - unrouted board, "
                      f"parity {drc.get('schematic_parity')}), manifest `{drc.get('manifest')}`.", '']
    lines += ['## Open issues for the orchestrator', '']
    lines += [f'- {issue}' for issue in OPEN_ISSUES]
    lines += ['', '## Limitations', '',
              '- No tracks or vias exist: every pad pair is an unconnected item; the DRC violation counts are placement/zone findings only.',
              '- Zone fills are pcbnew fills of the candidate pours (refilled with the project rules); the routing agent redefines the pours around the routed copper.',
              '- Thermal spacings are courtyard distances, not CFD; the corridor rule exempts the inductor by design (CR-14).',
              '- The checker dispositions are measurements against spec proxies, not engineering acceptance (human review required).', '']
    return '\n'.join(lines)


def write_comparison(evaluation: dict, final: dict | None, scratch: Path):
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    doc = dict(schema_version=1, status=BANNER, generated_utc=datetime.now(timezone.utc).isoformat(), scratch=str(scratch),
               generator='automation/kicad_tools/generate_sic_power_floorplan.py',
               weights=COMPARISON_WEIGHTS, higher_is_better=sorted(COMPARISON_HIGHER_IS_BETTER), criteria=evaluation['criteria'],
               scoring=evaluation['scoring'], selected=evaluation['selected'], failures=evaluation.get('failures', {}), rationale=evaluation.get('rationale', []),
               open_issues=OPEN_ISSUES,
               candidates={k: {kk: vv for kk, vv in v.items() if kk not in ('silkscreen', 'assignment')} for k, v in evaluation['candidates'].items()},
               final=None if not final else dict(board=final['board'], drc=final.get('drc'), checks=final['checks'], barrier=final['barrier']))
    (REVIEW_DIR / 'floorplan_candidates_power.json').write_text(json.dumps(doc, indent=2, default=str) + '\n', encoding='utf-8')
    (REVIEW_DIR / 'floorplan_candidates_power.md').write_text(comparison_markdown(evaluation, final, scratch), encoding='utf-8')


def rationale_lines(evaluation: dict) -> list[str]:
    """Reasoned selection text from the measured criteria (data-driven sentences; weights stay visible in the table)."""
    crit, sel = evaluation['criteria'], evaluation['selected']
    if not sel:
        return ['No candidate could be placed; see the failures above.']
    lines = [f'Candidate {sel} has the lowest weighted score ({evaluation["scoring"]["scores"][sel]}).']
    for key, label, better in CRITERIA_ROWS:
        if better == 'info' or key not in COMPARISON_WEIGHTS:
            continue
        values = {i: crit[i].get(key) for i in crit}
        if any(v is None for v in values.values()):
            continue
        best = (max if key in COMPARISON_HIGHER_IS_BETTER else min)(values.values())
        winners = sorted(i for i, v in values.items() if v == best)
        lines.append(f'{label}: ' + ', '.join(f'{i} = {values[i]}' for i in sorted(values)) + f' (best: {", ".join(winners)}).')
    for cid, failure in sorted(evaluation.get('failures', {}).items()):
        lines.append(f'Candidate {cid} could not be placed: {failure}')
    return lines


# --- CLI ----------------------------------------------------------------------------------------------------------------


def summary_line(result: dict) -> str:
    checks = result['checks']
    drc = result.get('drc') or {}
    lite = result.get('drc_lite') or {}
    return (f"candidate {result['candidate']}: {result['footprints']} footprints placed, {result['board_counts']['zones']} zones, "
            f"{len(result.get('placement_issues', []))} placement issues, {len(checks['issues'])} floorplan findings; "
            f"DRC-lite violations={lite.get('violations')} {lite.get('violations_by_type')}; DRC {drc.get('status')} findings={drc.get('finding_count')} "
            f"(violations {drc.get('violations')}, unconnected {drc.get('unconnected_items')}, parity {drc.get('schematic_parity')}) "
            f"manifest={drc.get('manifest')}; {result['seconds']} s")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--candidate', choices=['A', 'B', 'C'], help='build this candidate')
    parser.add_argument('--compare', action='store_true', help='place and compare every candidate in the scratch directory, select one')
    parser.add_argument('--select', action='store_true', help='with --compare: build the selected candidate into --output and write the repository outputs')
    parser.add_argument('--route', action='store_true', help='accepted for the routing-stage contract; the floorplan generator does not route')
    parser.add_argument('--output', type=Path, default=KICAD_DIR / f'{NAME}.kicad_pcb', help='board file of the built candidate')
    parser.add_argument('--scratch', type=Path, help='scratch directory for candidate boards, metrics and DRC-lite runs')
    parser.add_argument('--no-drc', action='store_true', help='skip the verification DRC through run_check (floorplan runs)')
    parser.add_argument('--drc-lite', action='store_true', help='also run the DRC without parity into the scratch directory')
    parser.add_argument('--metrics', action='store_true', help='run the layout metrics checker (default on; kept for the CLI contract)')
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
    scratch = args.scratch or (ROOT / '.aipe' / 'power-board-candidates')
    cli = find_kicad_cli()
    if not cli:
        print('kicad-cli not found', file=sys.stderr)
        return 2
    if args.route:
        print('note: --route belongs to the routing stage (generate_sic_power_board.py); the floorplan generator places and zones only', flush=True)
    if args.candidate and not args.compare:
        write = args.output.resolve() == (KICAD_DIR / f'{NAME}.kicad_pcb').resolve()
        result = build_power(candidate_path(args.candidate), args.output, drc=not args.no_drc and write, metrics=not args.no_metrics,
                             drc_lite_dir=(scratch / args.candidate / 'drc') if args.drc_lite else None, write_outputs=write,
                             metrics_dir=CHECKS_DIR if write else args.output.parent, metrics_label='power' if write else f'power_{args.candidate}', cli=cli)
        print(summary_line(result), flush=True)
        return 0
    evaluation = evaluate_candidates(('A', 'B', 'C'), scratch, cli=cli)
    evaluation['rationale'] = rationale_lines(evaluation)
    selected = evaluation['selected']
    print(f"selected candidate {selected} (scores {evaluation['scoring']['scores']})", flush=True)
    final = None
    if args.select and selected:
        final = build_power(candidate_path(selected), args.output, drc=not args.no_drc, metrics=not args.no_metrics, write_outputs=True,
                            metrics_dir=CHECKS_DIR, metrics_label='power', cli=cli)
        print(summary_line(final), flush=True)
    write_comparison(evaluation, final, scratch)
    print(f"comparison -> {REVIEW_DIR / 'floorplan_candidates_power.md'}", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
