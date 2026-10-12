"""Place, route and check the SiC buck CONTROL board (AIPE_SiC_Buck_Control; V2 design, V2.1 generation) with pcbnew and the grid router.

AI-GENERATED ENGINEERING PROTOTYPE - V2.1 - HUMAN REVIEW REQUIRED (label: sic_buck_common.GENERATION)

Follows automation.kicad_tools.v2_pipeline_smoke.board_stage(): kicad-cli XML netlist of the generated
schematic, a pcbnew BOARD with the project footprint libraries and the symbol paths of
design/schematic_mapping_control.json, deterministic placement with a courtyard-overlap check, the
4 x 35 um / 1.6 mm stackup injected as text, grid_router.run_plan for the routing (LQFP-176 escapes
pre-routed as alternating inward/outward vias with staggered outer rows, signals on F.Cu/B.Cu, In1.Cu
one solid GND_CTRL plane, In2.Cu rail islands 12V_PROT / 5V / 1V9 over a 3V3 background), a single-layer
In2.Cu pass for INNER_SIGNAL_NETS (BIAS_EN) and for any connection the F.Cu/B.Cu stages leave unresolved
(islands are keepouts, vias and plated pads obstacles, a pruned DSP escape via is re-created at a fallback port), the
rip-up negotiation driven through RIPUP_PENALTY_LADDER by LadderRouter (the shared grid_router is used unchanged), zone fill, corridor zones for rail copper outside its
island (records sorted by net and rectangle before their distinct priorities are assigned, so the result does not depend on the via order of
the reloaded board), a sliver trim that widens corridor edges next to sub-0.05 mm2 fill fragments (review LR-15), deterministic zone KIIDs
before the final fill (KiCad resolves touching zones of equal priority and different nets by KIID order),
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
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # re-executed by KiCad's Python with this file as a script
    sys.path.insert(0, str(ROOT))

from automation.kicad_tools import grid_router as gr  # noqa: E402  (numpy only at import time)
from automation.kicad_tools import sic_buck_common as common  # noqa: E402
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
BANNER = common.BANNER  # generation label shared with the schematics, the models and the evidence writers
REVISION = common.GENERATION
WIDTH, HEIGHT = 120.0, 80.0
COPPER_LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
ROUTING_LAYERS = ['F.Cu', 'B.Cu']  # In1.Cu is the unbroken GND_CTRL plane, In2.Cu carries only rail islands
GROUND_LAYER, ISLAND_LAYER = 'In1.Cu', 'In2.Cu'
# Nets routed as single tracks on the island layer In2.Cu (through the 3V3 background, never through another rail's island) by
# a separate single-layer router pass after the F.Cu/B.Cu stages. BIAS_EN is the static bias-module enable (DSP GPIO -> mezzanine
# pin 9); under the DSP's south escape rows the 43 south-side escapes and the mezzanine fan-in left no F.Cu/B.Cu lane for it
# (the rip-up negotiation cycled against DSP_TRIP_N for 97 rounds, DRC 1 unconnected). The In2.Cu pass keeps INNER_KEEPOUT_MARGIN
# from every island polygon, treats vias and plated pads as obstacles with INNER_CLEARANCE and is itself an obstacle for the
# stage-2 corridor zones, so no island or corridor is cut; the fill is rebuilt afterwards and the kicad-cli DRC judges the result.
INNER_SIGNAL_NETS = ('BIAS_EN',)
INNER_LAYER_FALLBACK = True  # connections the F.Cu/B.Cu stages leave unresolved also get one In2.Cu attempt (reported as 'fallback')
INNER_KEEPOUT_MARGIN = 0.5  # In2.Cu signal track to rail-island polygon edge (mm): island fill (0.25 mm zone clearance) stays whole
INNER_CLEARANCE = 0.3  # In2.Cu signal track to vias / plated pads (mm): the 0.2 mm rule plus margin for the 0.25 mm zone clearance
INNER_TURN_SEARCH = (1.5, 10.0, 0.25)  # the horizontal leg of an In2.Cu route lies 1.5-10 mm beyond the first port (0.25 mm steps);
# the ordinate with the fewest through items within INNER_TURN_RADIUS of the leg wins (ties: nearest), so the track leaves the DSP
# escape via rows and their corridor fingers before it turns
INNER_TURN_RADIUS = 1.0
INNER_EDGE_BAND = 3.0  # an In2.Cu signal track keeps this distance from every rail-island polygon except along its own port's exit channel:
# a track running parallel to an island edge closer than this isolates the strip of background copper between them, and that strip is
# where the corridor notches of the island's exception vias reach the background (iteration 6: PG_BIAS_L_N along the 1V9 island's east
# edge cut off the 3V3 exit of U5.45's corridor - DRC manifest 20261010T233115Z-drc-2e44897b, 1 unconnected)
INNER_CHANNEL_HALF_WIDTH = 0.5  # half width of a port's straight exit channel through the band (0.2 mm track + 0.3 mm clearance per side)
GROUND = 'GND_CTRL'
RAILS = ('12V_PROT', '5V', '3V3', '1V9')
# KiCad fills zones of equal priority and different nets in KIID order (ZONE::HigherPriority: the greater KIID keeps its outline, the
# other steps back by the zone clearance). The 12V_PROT and 5V islands share the edge x = 21 mm, so with random KIIDs about 6 mm2 of
# In2.Cu copper changed owner between builds. zone_identity() derives every zone's KIID from this order (first = keeps its outline;
# 12V_PROT first reproduces the frozen V2 board) and from the zone's net, layer, priority and outline.
ZONE_TIE_BREAK_ORDER = (*RAILS, GROUND)
ZONE_IDENTITY_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, 'aipe://sic-buck/control-board/zone')
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
# Review LR-15: the 3V3 background fill left 20-30 um wide fragments along corridor-zone edges where a foreign via's clearance
# ring crosses the edge. After the corridor zones are filled, every rail fill outline below SLIVER_AREA_MM2 on In2.Cu is a sliver;
# the adjacent same-net corridor edge is widened by SLIVER_TRIM_STEP and the zones are refilled, for at most SLIVER_TRIM_ROUNDS
# rounds (a nudge that would bring the corridor within the zone clearance of an other-net corridor is skipped and reported).
SLIVER_AREA_MM2, SLIVER_TRIM_STEP, SLIVER_TRIM_ROUNDS = 0.05, 0.125, 8
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
SIGNAL_ORDER_TRIALS = 6  # grid_router signal-stage orders tried (plan order, long nets last/first, then seeded perturbations of the best)
RIPUP_ROUNDS = 240  # grid_router rip-up and re-route rounds for the connections the best order leaves unresolved (round 9 was still gaining at 84/90)
ROUTING_STYLE = dict(diagonal=False, simplify='octilinear', arcs=True, eps=0.02)  # V2.1 grid_router geometry (plan key 'style'): the V2
# 4-direction search with the same algorithm, order trials and 240 rip-up rounds, then the final octilinear simplification (string pulling,
# short-run collapse, on-grid chamfers) and tangent arcs on the signal nets (power/critical nets and tracks above 0.6 mm: diagonals only).
# eps 0.02 (V2: 0.01) widens every marking halo on this 0.2 mm clearance / 0.125 mm grid board, so routes can differ from the frozen V2 run
# (B2 scratch build: BOOT84 and EMU0 longer, 798 vias as V2, DRC 0); routing_progress records the eps in use. ROUTING_STYLE_DIAGONAL adds the 8-direction search with
# bend penalties; it is opt-in (build_control(style=ROUTING_STYLE_DIAGONAL)) because with MAX_NODES 2.5 M and 240 rip-up rounds its control-board
# run time exceeded 1.5 x the V2 1155 s in the V2.1 scratch builds. build_control(style={}) routes with the V2 geometry; the frozen V2 plan has no 'style'.
ROUTING_STYLE_DIAGONAL = dict(ROUTING_STYLE, diagonal=True, bend_penalty_cells=[0.6, 2.0])
RIPUP_PENALTY_LADDER = (1.0, 0.4, 2.5)  # multiples of the plan's ripup_penalty that LadderRouter.negotiate cycles through. The shared
# grid_router.negotiate() tries one penalty per failing connection since the power-board agent's 2026-10-11 change (the variants never
# helped the power board); the control board's last connections closed in iteration 4 only through the 2.5x step, and without the
# ladder the negotiation stops at 2 unconnected (RDY_H, PG_BIAS_L_N; DRC manifest 20261010T230400Z-drc-a401f5ad). The generator
# therefore keeps the ladder on its side of the shared module (LadderRouter), which stays unchanged.
SIGNAL_ORDER = ['EPWM1A', 'EPWM1B', 'PWM_H_G', 'PWM_L_G', 'PWM_H', 'PWM_L', 'GATE_EN', 'FAULT_N', 'OC_N', 'FAULT_LATCH_N',
                'CLK30', 'ADC_', 'ADCREF', 'ADCRESEXT', 'VIN_SENSE', 'VOUT_SENSE', 'ISENSE', 'TEMP_', 'I12V_MON', 'V12V_MON',
                'REF', '5V_SW', '5V_BST', '5V_FB', '12V_IN', 'EFUSE_']
# Track widths per net (mm). CTRL_PWR class value 1.0 mm (project .kicad_pro) where the pad geometry allows it:
# 12V_IN is pre-routed as a 1.0 mm F.Cu bus (candidate pre_routed), 12V_PROT and 5V reach their In2.Cu islands
# through fanout vias only (the island is the conductor), so their routed width matters for stubs alone; the pad
# escape of a 0.65 mm pitch HTSSOP / 0.95 mm SOT-23 pin cannot exceed ~0.4 mm without touching its neighbours
# (fanout_width). EFUSE_RTN is the TPS26400 device return (RTN pin 8 between two other-net 0.65 mm pins), not the
# load path, and keeps 0.4 mm. IPC-2221 (35 um, external): 0.54 A on 0.4 mm -> ~1.6 K; 1.96 A on 1.0 mm -> 6.4 K.
NET_RULES = {'12V_IN': dict(width=1.0, fanout_width=0.4), 'EFUSE_RTN': dict(width=0.4), '5V_SW': dict(width=0.7, fanout_width=0.4),
             '5V_BST': dict(width=0.3), '3V3_BULK': dict(width=0.6), '1V9_BULK': dict(width=0.6),
             '12V_PROT': dict(width=1.0, fanout_width=0.4), '5V': dict(width=0.6, fanout_width=0.4), '3V3': dict(width=0.3), '1V9': dict(width=0.3)}
INPAD_VIAS = [['U1', '17'], ['U3', '29']]  # HTSSOP exposed pads: EFUSE_RTN PowerPad and the LDO ground pad (single via unless the
# candidate defines exposed_pad_vias arrays; the refs still select the exposed-pad escape gap in gap_for)
EXPOSED_PAD_MARGIN = 0.45  # via centre to exposed-pad edge (0.3 mm via radius + 0.15 mm inside the pad copper)
EXPOSED_PAD_COMB_WIDTH = 0.4  # B.Cu tracks joining the vias of an exposed-pad array whose net has no plane (EFUSE_RTN)
PREROUTE_GAP = 0.3  # placement keep-away around candidate pre-routed copper (clearance 0.2 + margin)
CORRIDOR_HALF_WIDTH_BY_NET = {'12V_PROT': 1.0, '5V': 1.0}  # >= 2 mm wide In2.Cu corridor fingers for the current-carrying rails
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
    'Candidate pre_routed entries (12V_IN 1.0 mm F.Cu bus, 5V_SW/5V_BST hot-loop tracks, eFuse-output via group) and exposed_pad_vias arrays are '
    'placed before the fanout; their pads are skipped by the fanout and the auto-placer keeps parts off that copper.',
    'The mezzanine header J8 is on B.Cu (pins toward the power-board socket); through-hole parts block both placement sides.',
    'BIAS_EN (static bias-module enable, DSP pin 12 -> J8 pin 9) is routed as one 0.2 mm track on In2.Cu through the 3V3 background by a '
    'single-layer router pass after the F.Cu/B.Cu stages: the band under the DSP south escape rows had no lane for it. The track keeps '
    '0.5 mm from every rail-island polygon and 0.3 mm from vias/plated pads, counts as an obstacle for the corridor zones, and the island '
    'fills are rebuilt afterwards; connections the F.Cu/B.Cu stages leave unresolved get the same In2.Cu attempt (reported as fallback; '
    'a DSP escape via the outer stages pruned is re-created at the port when it still fits). Every In2.Cu signal track keeps INNER_EDGE_BAND '
    'from the island polygons except along its own port exit channel: a track hugging an island edge isolates the background strip in which the '
    'corridor notches of that island reach the background (iteration 6, U5.45 3V3).',
    'Reproducible zone fill (V2.1): the stage-2 corridor records are sorted by net and rectangle before their distinct priorities are '
    'assigned (the via order of a reloaded board is not reproducible, and overlapping same-net corridors are owned by the higher priority), '
    'and every zone gets a deterministic KIID (zone_identity: ZONE_TIE_BREAK_ORDER rank, then a uuid5 of net, layer, priority and outline) '
    'before the final fill, because KiCad resolves touching zones of equal priority and different nets by KIID order (the 12V_PROT and 5V '
    'islands share the edge x = 21 mm; about 6 mm2 changed owner between builds). Geometry and priorities are unchanged.',
    'The rip-up negotiation runs with the penalty ladder 1x / 0.4x / 2.5x of the plan ripup_penalty (LadderRouter in this generator; '
    'the shared grid_router tries one penalty per failing connection since 2026-10-11): without the ladder the control board stops at '
    '2 unconnected (RDY_H, PG_BIAS_L_N).',
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


def rectilinear_rectangles(polygon) -> list[tuple]:
    """Axis-aligned rectangles (x0, y0, x1, y1) whose union is the rectilinear ``polygon`` (strip decomposition along the
    vertex ordinates; every cell between consecutive vertex abscissae is classified by its midpoint)."""
    xs = sorted({float(p[0]) for p in polygon})
    ys = sorted({float(p[1]) for p in polygon})
    rects = []
    for y0, y1 in zip(ys, ys[1:]):
        mid_y = (y0 + y1) / 2
        run = None
        for x0, x1 in zip(xs, xs[1:]):
            if point_in_polygon(((x0 + x1) / 2, mid_y), polygon):
                run = x0 if run is None else run
            elif run is not None:
                rects.append((run, y0, x0, y1))
                run = None
        if run is not None:
            rects.append((run, y0, xs[-1], y1))
    return rects


def rect_minus(rect, holes) -> list[tuple]:
    """Axis-aligned ``rect`` (x0, y0, x1, y1) minus the ``holes`` rectangles, as disjoint rectangles (pure)."""
    pieces = [tuple(float(v) for v in rect)]
    for hole in holes:
        hx0, hy0, hx1, hy1 = hole
        out = []
        for x0, y0, x1, y1 in pieces:
            if hx1 <= x0 or hx0 >= x1 or hy1 <= y0 or hy0 >= y1:
                out.append((x0, y0, x1, y1))
                continue
            ix0, iy0, ix1, iy1 = max(x0, hx0), max(y0, hy0), min(x1, hx1), min(y1, hy1)
            if iy0 > y0:
                out.append((x0, y0, x1, iy0))
            if iy1 < y1:
                out.append((x0, iy1, x1, y1))
            if ix0 > x0:
                out.append((x0, iy0, ix0, iy1))
            if ix1 < x1:
                out.append((ix1, iy0, x1, iy1))
        pieces = out
    return pieces


def inflated_rect(rect, margin: float) -> tuple:
    return (rect[0] - margin, rect[1] - margin, rect[2] + margin, rect[3] + margin)


def port_channel(port, island_rects, band: float = INNER_EDGE_BAND, *, half_width: float = INNER_CHANNEL_HALF_WIDTH,
                 margin: float = INNER_KEEPOUT_MARGIN):
    """Exit channel of an inner-layer port that lies inside an island's edge band (pure): ``(rect, axis, sign)`` of the straight
    channel from the port away from the nearest island side to ``half_width`` beyond the band, ``axis`` 'x' for a horizontal
    exit and 'y' for a vertical one, ``sign`` +1 towards larger coordinates; None when the port lies outside every band (or
    inside an island keepout, where no route can start anyway). With several bands the nearest island side decides."""
    px, py = float(port[0]), float(port[1])
    best = None
    for x0, y0, x1, y1 in island_rects:
        if not (x0 - band <= px <= x1 + band and y0 - band <= py <= y1 + band):
            continue
        if x0 - margin <= px <= x1 + margin and y0 - margin <= py <= y1 + margin:
            continue
        sides = [('x', x0 - px, -1, x0 - band - half_width), ('x', px - x1, +1, x1 + band + half_width),
                 ('y', y0 - py, -1, y0 - band - half_width), ('y', py - y1, +1, y1 + band + half_width)]
        axis, dist, sign, end = max(sides, key=lambda s: s[1])  # the side the port lies beyond (largest outside distance)
        if best is None or dist < best[0]:
            best = (dist, axis, sign, end)
    if best is None:
        return None
    _dist, axis, sign, end = best
    if axis == 'x':  # the channel starts half a width behind the port: Grid.box marks its bounds inclusively, so the port cell stays free
        start = px - sign * half_width
        return ((min(start, end), py - half_width, max(start, end), py + half_width), 'x', sign)
    start = py - sign * half_width
    return ((px - half_width, min(start, end), px + half_width, max(start, end)), 'y', sign)


def band_keepouts(island_rects, ports, band: float = INNER_EDGE_BAND, *, margin: float = INNER_KEEPOUT_MARGIN):
    """Keepout rectangles of the island edge bands minus the exit channels of ``ports`` (pure).

    Returns ``(rects, channels)``: ``rects`` cover every island rectangle inflated by ``band`` except the channels, so an inner
    track can leave or reach a port that sits inside a band only straight through its channel and otherwise stays ``band`` away
    from the islands; ``channels`` maps each such port (rounded tuple) to ``(rect, axis, sign)``."""
    channels = {}
    for port in ports:
        key = (round(float(port[0]), 4), round(float(port[1]), 4))
        if key in channels:
            continue
        channel = port_channel(key, island_rects, band, margin=margin)
        if channel is not None:
            channels[key] = channel
    holes = [channel[0] for channel in channels.values()]
    rects = []
    for island in island_rects:
        rects.extend(rect_minus(inflated_rect(island, band), holes))
    return rects, channels


def inner_route_waypoints(a, b, through_items, *, search=INNER_TURN_SEARCH, radius: float = INNER_TURN_RADIUS, grid: float = GRID,
                          axis: str = 'y', direction=None) -> list:
    """Grid-snapped waypoints of a Z-shaped inner-layer route from port ``a`` to port ``b``: a vertical leg away from ``a``,
    a horizontal leg at the ordinate (``search`` = (min, max, step) mm beyond ``a`` towards ``b``) crossed by the fewest
    ``through_items`` ({xy} vias / plated pads within ``radius`` of the leg; ties: the nearest ordinate), then a vertical leg
    to ``b``. ``axis='x'`` transposes the Z (a horizontal leg away from ``a`` first: ports whose exit channel is horizontal);
    ``direction`` (+1 / -1) forces the first leg's sense (the port channel's outward side) even when ``b`` lies the other way,
    which turns the Z into a U. Ports closer than the minimum, or aligned ports, get the direct two-point list."""
    if axis == 'x':
        swapped = inner_route_waypoints([a[1], a[0]], [b[1], b[0]], [dict(xy=[it['xy'][1], it['xy'][0]]) for it in through_items],
                                        search=search, radius=radius, grid=grid, axis='y', direction=direction)
        return [[pt[1], pt[0]] for pt in swapped]
    ax, ay = snap(a[0], grid), snap(a[1], grid)
    bx, by = snap(b[0], grid), snap(b[1], grid)
    if abs(ax - bx) < 1e-9 or (abs(ay - by) < 1e-9 and direction is None):
        return [[ax, ay], [bx, by]]
    towards = 1.0 if by > ay else -1.0
    sign = float(direction) if direction in (1, -1, 1.0, -1.0) else towards
    lo, hi, step = search
    x_lo, x_hi = min(ax, bx) - radius, max(ax, bx) + radius
    best = None
    t = lo
    while t <= hi + 1e-9:
        y = snap(ay + sign * t, grid)
        if sign == towards and ((sign > 0 and y >= by) or (sign < 0 and y <= by)):
            break
        crossing = sum(1 for item in through_items if abs(item['xy'][1] - y) < radius and x_lo < item['xy'][0] < x_hi)
        if best is None or crossing < best[0]:
            best = (crossing, y)
        t = round(t + step, 6)
    if best is None:
        return [[ax, ay], [bx, by]]
    return [[ax, ay], [ax, best[1]], [bx, best[1]], [bx, by]]


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
        if len(pose) not in (3, 4) or (len(pose) == 4 and pose[3] not in ('F', 'B')):
            raise ValueError(f'{path}: fixed {ref} needs [x, y, angle] or [x, y, angle, "F"|"B"]')
    for item in data.get('pre_routed', []):
        for key in ('net', 'layer', 'width', 'points'):
            if key not in item:
                raise ValueError(f'{path}: pre_routed item needs {key!r}: {item}')
        if item['layer'] not in ROUTING_LAYERS or len(item['points']) < 1:
            raise ValueError(f'{path}: pre_routed item layer/points invalid: {item}')
    for ref, cfg in data.get('exposed_pad_vias', {}).items():
        if 'pad' not in cfg or len(cfg.get('count', [])) != 2 or min(cfg['count']) < 1:
            raise ValueError(f'{path}: exposed_pad_vias.{ref} needs pad and count [nx, ny]')
    if not isinstance(data.get('signal_priority', []), list):
        raise ValueError(f'{path}: signal_priority must be a list of net names or prefixes')
    for ref, spec in data.get('dsp_near_rings', {}).items():
        if 'pin' not in spec or spec.get('side') not in ('F', 'B') or spec.get('radius_mm', 0) <= 0:
            raise ValueError(f'{path}: dsp_near_rings.{ref} needs pin, side F|B and radius_mm')
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
        if 'near_dsp_pin' in part or part['ref'] in candidate.get('dsp_near_rings', {}):
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


def rail_item_key(item: dict) -> tuple:
    """Deterministic order of rail items and obstacles (net, rounded position, kind): a reloaded board lists its vias in an order
    that is not reproducible between runs, so nothing derived from them may follow that order."""
    return (str(item['net']), tuple(round(float(v), 4) for v in item['xy']), str(item.get('kind') or ''))


def corridor_sort_key(record: dict) -> tuple:
    """Deterministic order of the corridor records: net, rounded rectangle (x0, y0, x1, y1), origin, leg and kind. The distinct
    zone priorities CORRIDOR_PRIORITY + index follow this order, and with them the fill ownership where same-net corridors overlap."""
    return (str(record['net']), tuple(round(float(v), 4) for v in polygon_bbox(record['polygon'])),
            tuple(round(float(v), 4) for v in record['xy']), int(record.get('leg') or 0), str(record.get('kind') or ''))


def zone_identity(net: str, layer: str, priority: int, polygon) -> str:
    """Deterministic KIID string of a zone: the first 32 bits rank the net by ZONE_TIE_BREAK_ORDER (first = greatest = keeps its
    outline where equal-priority zones of different nets touch), the remaining 96 bits are the uuid5 of net, layer, priority and the
    rounded outline (distinct zones, distinct KIIDs). Pure; assign_zone_identities() applies it to a board before the final fill."""
    rank = ZONE_TIE_BREAK_ORDER.index(net) if net in ZONE_TIE_BREAK_ORDER else len(ZONE_TIE_BREAK_ORDER)
    outline = ';'.join(f'{round(float(x), 4)},{round(float(y), 4)}' for x, y in polygon)
    digest = uuid.uuid5(ZONE_IDENTITY_NAMESPACE, f'{net}|{layer}|{int(priority)}|{outline}')
    return f'{len(ZONE_TIE_BREAK_ORDER) - rank:08x}' + str(digest)[8:]


def island_corridors(items: list[dict], islands: dict, *, obstacles: list[dict] | None = None, half_width: float = CORRIDOR_HALF_WIDTH,
                     overshoot: float = CORRIDOR_OVERSHOOT, max_mm: float = CORRIDOR_MAX_MM, via_radius: float = VIA[0] / 2,
                     clearance: float = ZONE_CLEARANCE, half_width_by_net: dict | None = None) -> dict:
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
    no usable corridor within ``max_mm`` are reported as issues. Items are visited in rail_item_key order and the records are
    sorted by corridor_sort_key before the priorities are assigned, so the result is the same for every input order.
    """
    polys = {n: p for n, p in islands.items() if p != 'background'}
    corridors, issues = [], []
    obstacles = items if obstacles is None else obstacles
    widths = dict(half_width_by_net or {})
    default_half_width = half_width

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
    for item in sorted(items, key=rail_item_key):
        net, xy = item['net'], tuple(item['xy'])
        if net not in islands or territory(net, xy):
            continue
        half_width = float(widths.get(net, default_half_width))  # the closures above read the per-item value
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
                               reason='every corridor direction is severed by other-net copper: ' + ', '.join(f"{b['net']}@{b['xy']}" for b in sorted(hit, key=rail_item_key))))
            continue
        total, offset, leg1_dir, leg1, corner, d, found, leg2 = min(l_shapes, key=lambda o: (o[0], o[1]))
        corridors.append(record(item, xy, leg1_dir, abs(offset), leg1, shape='L', leg=1))
        corridors.append(record(item, corner, d, found + overshoot, leg2, shape='L', leg=2))
    corridors.sort(key=corridor_sort_key)  # reproducible priorities and overlap ownership whatever the via order of the reloaded board
    for i, a in enumerate(corridors):
        a['priority'] = CORRIDOR_PRIORITY + i  # distinct priorities: KiCad rejects intersecting same-net zones of equal priority (L legs overlap)
        for b in corridors[i + 1:]:
            if a['net'] != b['net'] and boxes_overlap(polygon_bbox(a['polygon']), polygon_bbox(b['polygon']), clearance, clearance):
                issues.append(dict(net=a['net'], xy=a['xy'], kind='corridor', reason=f"corridor overlaps a {b['net']} corridor at {b['xy']}"))
    return dict(corridors=corridors, issues=issues)


def sliver_edge(rect, sliver_bbox, tol: float = 0.03, slack: float = 0.3):
    """Which edge of the corridor rectangle ``rect`` (x0, y0, x1, y1) a fill sliver's bounding box touches: 'x0' (left), 'x1',
    'y0' (top) or 'y1', else None. The sliver lies outside the rectangle along that edge within ``tol``; its centre must lie
    within the edge's extent plus ``slack``."""
    x0, y0, x1, y1 = sliver_bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if abs(rect[0] - x1) < tol and rect[1] - slack <= cy <= rect[3] + slack:
        return 'x0'
    if abs(rect[2] - x0) < tol and rect[1] - slack <= cy <= rect[3] + slack:
        return 'x1'
    if abs(rect[1] - y1) < tol and rect[0] - slack <= cx <= rect[2] + slack:
        return 'y0'
    if abs(rect[3] - y0) < tol and rect[0] - slack <= cx <= rect[2] + slack:
        return 'y1'
    return None


def widened(rect, edge, step: float):
    """Rectangle ``rect`` with ``edge`` ('x0'/'y0'/'x1'/'y1') moved outward by ``step`` mm."""
    x0, y0, x1, y1 = rect
    return {'x0': (round(x0 - step, 4), y0, x1, y1), 'y0': (x0, round(y0 - step, 4), x1, y1),
            'x1': (x0, y0, round(x1 + step, 4), y1), 'y1': (x0, y0, x1, round(y1 + step, 4))}[edge]


def uncovered_rail_items(items: list[dict], islands: dict, corridors: list[dict]) -> list[dict]:
    """Rail items that are outside their own territory and not covered by a corridor of their net (expected: none)."""
    polys = {n: p for n, p in islands.items() if p != 'background'}
    result = []
    for item in sorted(items, key=rail_item_key):
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
                 dsp_signal_nets=(), lanes: dict | None = None, extra: dict | None = None, inpad_vias=None, style=None) -> dict:
    """grid_router plan: pre-routed LQFP escapes with B.Cu exit stubs, pre-routed fine-pitch IC escapes, the candidate's
    pre-routed copper and exposed-pad via arrays (``extra`` = {tracks, vias, skip_pads}), fanout for the rest (DSP and
    pre-routed pads skipped), signals on F.Cu/B.Cu (candidate signal_priority, then the DSP nets), rail islands and the GND plane."""
    extra = extra or {}
    tracks = [dict(net=e['net'], layer='F.Cu', a=list(e['pad']), b=list(e['via']), width=TRACE) for e in escapes]
    vias = [dict(net=e['net'], xy=list(e['via']), port=True) for e in escapes]
    tracks += [dict(t) for t in extra.get('tracks', [])]
    vias += [dict(v) for v in extra.get('vias', [])]
    stubs = 0
    lanes = lanes or {}
    lane_ends = lanes.get('ends', {})
    if dsp_centre is not None:
        for e in escapes:
            if e['net'] in RAILS or e['net'] == GROUND:
                continue
            if e['direction'] != 'in':
                if e['net'] in INNER_SIGNAL_NETS:
                    continue  # leaves its escape via on In2.Cu (inner_layer_route); no F.Cu lane is reserved for it
                # outward pins leave on F.Cu: reserve the straight exit from the via to STUB_RADIUS (between the far-row
                # vias) so that no earlier-routed net seals the pin in; the router continues from the lane end
                lane = outward_stub(e, dsp_centre, STUB_RADIUS)
                for a, b in zip(lane, lane[1:]):
                    if math.dist(a, b) > 1e-6:
                        tracks.append(dict(net=e['net'], layer='F.Cu', a=list(a), b=list(b), width=TRACE))
                        stubs += 1
                continue
            points = exit_stub(e, escapes, dsp_centre, min(STUB_B_MAX, lane_ends.get(e['number'], STUB_RADIUS)))
            layer = 'B.Cu'
            for a, b in zip(points, points[1:]):
                if math.dist(a, b) > 1e-6:
                    tracks.append(dict(net=e['net'], layer=layer, a=list(a), b=list(b), width=TRACE))
            stubs += 1 if points else 0
        for peel in lanes.get('peel_offs', []):
            if math.dist(peel['a'], peel['b']) > 1e-6:
                tracks.append(dict(net=peel['net'], layer=peel['layer'], a=list(peel['a']), b=list(peel['b']), width=TRACE))
    skip_pads = [[candidate['dsp']['ref'], e['number']] for e in escapes] + [list(p) for p in extra.get('skip_pads', [])]
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
    signal_order = list(candidate.get('signal_priority', []))  # the candidate's congestion-critical nets first
    signal_first = list(candidate.get('signal_first', []))  # routed before everything else in the 4th order trial
    signal_order += [n for n in SIGNAL_ORDER if n not in signal_order]
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
        'fanout': {'order': order, 'skip_refs': [candidate['dsp']['ref']], 'skip_pads': skip_pads,
                   'inpad_vias': [list(p) for p in (INPAD_VIAS if inpad_vias is None else inpad_vias)]},
        'critical': [], 'critical_layers': list(ROUTING_LAYERS),
        'power': power,
        'signal_order': signal_order, 'signal_layers': list(ROUTING_LAYERS), 'front_fallback': True,
        'exclude_nets': list(INNER_SIGNAL_NETS),  # routed on In2.Cu after the F.Cu/B.Cu stages (inner_layer_route)
        'ground': {'net': GROUND, 'layers': [GROUND_LAYER], 'clearance': ZONE_CLEARANCE, 'priority': 0, 'polygon': background_polygon()},
        'prune_vias': True, 'fill': True, 'save': str(save), 'strict': False, 'max_nodes': MAX_NODES,
        'signal_first': signal_first,
        'signal_pinned': list(candidate.get('signal_pinned', [])),  # r20 (LR-32): the protection lines routed first in every order trial (direct runs)
        'signal_order_trials': SIGNAL_ORDER_TRIALS, 'ripup_rounds': RIPUP_ROUNDS,
        **({'style': dict(style)} if style else {}),  # V2.1 geometry (ROUTING_STYLE); absent = the V2 plan
    }


# --- candidate pre-routed copper (pure) --------------------------------------------------------------------------------


def resolve_point(spec, table: dict):
    """Board point (x, y) of a candidate point spec: ``[x, y]`` absolute, or ``["@REF.PAD", dx, dy]`` relative to a placed pad."""
    if len(spec) == 2:
        return (float(spec[0]), float(spec[1]))
    if len(spec) == 3 and isinstance(spec[0], str) and spec[0].startswith('@') and '.' in spec[0]:
        ref, number = spec[0][1:].split('.', 1)
        pad = table.get((ref, number))
        if pad is None:
            raise ValueError(f'pre-routed point {spec}: pad {ref}.{number} is not placed')
        return (round(pad['xy'][0] + float(spec[1]), 4), round(pad['xy'][1] + float(spec[2]), 4))
    raise ValueError(f'unsupported point spec {spec}')


def candidate_pre_routed(candidate: dict, table: dict) -> dict:
    """grid_router pre_routed tracks/vias and the fanout skip_pads from the candidate's ``pre_routed`` list.

    Each entry: {net, layer, width, points: [...], vias?: [...], port_vias?: [...], skip_pads?: [[ref, pad], ...]}.
    Consecutive points become tracks; ``vias`` are plain through vias (connected by the tracks or a zone), ``port_vias``
    additionally register as routing ports so the router joins the rest of the net to them; ``skip_pads`` lists the
    pads the copper already connects (no fanout via). Point specs: see resolve_point.
    """
    tracks, vias, skip = [], [], []
    for item in candidate.get('pre_routed', []):
        points = [resolve_point(pt, table) for pt in item['points']]
        for a, b in zip(points, points[1:]):
            if math.dist(a, b) > 1e-6:
                tracks.append(dict(net=item['net'], layer=item['layer'], a=[a[0], a[1]], b=[b[0], b[1]], width=float(item['width'])))
        for pt in item.get('vias', []):
            x, y = resolve_point(pt, table)
            vias.append(dict(net=item['net'], xy=[x, y], port=False))
        for pt in item.get('port_vias', []):
            x, y = resolve_point(pt, table)
            vias.append(dict(net=item['net'], xy=[x, y], port=True))
        skip.extend([list(p) for p in item.get('skip_pads', [])])
    return dict(tracks=tracks, vias=vias, skip_pads=skip)


def exposed_pad_arrays(pad_boxes: dict, candidate: dict, plane_nets=()) -> dict:
    """Via arrays inside exposed pads: ``exposed_pad_vias`` {ref: {pad, count: [nx, ny]}} with the pad boxes
    {(ref, pad): dict(bbox=[x0, y0, x1, y1], net=...)} of the placed board.

    Vias sit EXPOSED_PAD_MARGIN inside the pad edges on an even grid (0.125 mm snapped). For a net with a plane or
    island (``plane_nets``) the zone connects the vias; otherwise a B.Cu comb (EXPOSED_PAD_COMB_WIDTH) joins them and the
    first via is a routing port, so the net reaches the array once and every via carries copper on two layers.
    """
    tracks, vias, skip, records = [], [], [], []
    for ref, cfg in sorted(candidate.get('exposed_pad_vias', {}).items()):
        key = (ref, str(cfg['pad']))
        if key not in pad_boxes:
            raise ValueError(f'exposed_pad_vias: pad {ref}.{cfg["pad"]} not on the board')
        box, net = pad_boxes[key]['bbox'], pad_boxes[key]['net']
        nx, ny = int(cfg['count'][0]), int(cfg['count'][1])
        xs = [snap((box[0] + box[2]) / 2)] if nx == 1 else [snap(box[0] + EXPOSED_PAD_MARGIN + (box[2] - box[0] - 2 * EXPOSED_PAD_MARGIN) * i / (nx - 1)) for i in range(nx)]
        ys = [snap((box[1] + box[3]) / 2)] if ny == 1 else [snap(box[1] + EXPOSED_PAD_MARGIN + (box[3] - box[1] - 2 * EXPOSED_PAD_MARGIN) * j / (ny - 1)) for j in range(ny)]
        for xa, xb in zip(xs, xs[1:]):
            if xb - xa < VIA[1] + HOLE_CLEARANCE:
                raise ValueError(f'exposed_pad_vias {ref}: x pitch {xb - xa} below the hole-to-hole minimum')
        for ya, yb in zip(ys, ys[1:]):
            if yb - ya < VIA[1] + HOLE_CLEARANCE:
                raise ValueError(f'exposed_pad_vias {ref}: y pitch {yb - ya} below the hole-to-hole minimum')
        grid_pts = [(x, y) for x in xs for y in ys]
        plane = net in plane_nets
        for i, (x, y) in enumerate(grid_pts):
            vias.append(dict(net=net, xy=[x, y], port=(not plane and i == 0)))
        if not plane:  # comb: columns joined vertically, the first row joined horizontally
            for x in xs:
                for ya, yb in zip(ys, ys[1:]):
                    tracks.append(dict(net=net, layer='B.Cu', a=[x, ya], b=[x, yb], width=EXPOSED_PAD_COMB_WIDTH))
            for xa, xb in zip(xs, xs[1:]):
                tracks.append(dict(net=net, layer='B.Cu', a=[xa, ys[0]], b=[xb, ys[0]], width=EXPOSED_PAD_COMB_WIDTH))
        skip.append([ref, str(cfg['pad'])])
        records.append(dict(ref=ref, pad=str(cfg['pad']), net=net, vias=len(grid_pts), positions=grid_pts, comb=not plane, pad_bbox=[round(v, 3) for v in box]))
    return dict(tracks=tracks, vias=vias, skip_pads=skip, records=records)


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


def stored_fill_check(board_path: Path, cli, label: str = 'control') -> dict:
    """Diagnostic (NOT verification evidence): kicad-cli DRC WITHOUT --refill-zones on a temporary copy of the board directory, i.e.
    of the zone fills as stored in the file - the copper that the gerber / PDF / render / STEP exports contain. Writes
    engineering_checks/stored_zone_fill_check_<label>.json and returns the counts. The verification DRC stays run_check (--refill-zones)."""
    import re
    import shutil
    import tempfile
    board_path = Path(board_path)
    tmp = Path(tempfile.mkdtemp(prefix='aipe_sf_'))  # short system temp path: the library file names exceed MAX_PATH under long scratch paths
    record = dict(schema_version=2, status=BANNER, title='Stored zone fills checked without refill (diagnostic, not a verification record)',
                  generated_utc=datetime.now(timezone.utc).isoformat(), board=str(board_path), board_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),
                  method='copy of the board directory in a temporary folder; kicad-cli pcb drc --format json --severity-all WITHOUT --refill-zones '
                         '(no schematic parity: copper only); counts of the stored fills. The run_check manifests under verification/drc remain the evidence.')
    try:
        copy = tmp / board_path.parent.name
        shutil.copytree(board_path.parent, copy)
        report = tmp / 'drc_stored_fills.json'
        command = [str(cli), 'pcb', 'drc', '--format', 'json', '--severity-all', '--output', str(report), str(copy / board_path.name)]
        completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
        record['tool_exit_code'] = completed.returncode
        data = json.loads(report.read_text(encoding='utf-8-sig'))
        violations = data.get('violations', [])
        by_type: dict = {}
        by_rule: dict = {}
        for v in violations:
            by_type[v.get('type')] = by_type.get(v.get('type'), 0) + 1
            m = re.search(r'\((.+?) clearance ', v.get('description', ''))
            rule = m.group(1) if m else v.get('type')
            by_rule[rule] = by_rule.get(rule, 0) + 1
        record.update(violations=len(violations), unconnected_items=len(data.get('unconnected_items', [])), by_type=by_type, by_rule=by_rule,
                      lib_warnings_note='lib_footprint_issues / lib_footprint_mismatch entries, if any, are copied-path artefacts of the temporary folder')
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        record['error'] = str(exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    CHECKS_DIR.mkdir(parents=True, exist_ok=True)
    (CHECKS_DIR / f'stored_zone_fill_check_{label}.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return {k: record.get(k) for k in ('violations', 'unconnected_items', 'by_type', 'by_rule', 'error') if k in record}


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


def negotiate_with_ladder(step, count, rounds: int, penalty: float, ladder=RIPUP_PENALTY_LADDER) -> list[dict]:
    """Drive a single-penalty rip-up negotiation ``step(penalty, rounds) -> log`` through the penalty ``ladder`` (pure).

    ``count()`` returns the number of unresolved route connections. Each ladder step runs until the step itself gives up
    (every failing connection attempted at that penalty); a step that lowers the count restarts the ladder at its first
    multiple on the new failure set. The negotiation stops at zero, after a full ladder cycle without progress, or when
    ``rounds`` is spent (a step that attempts nothing still costs one round, so the loop terminates). Returns the merged
    log with the rounds renumbered and the ladder multiple recorded on every entry.
    """
    log = []
    remaining = int(rounds)
    while remaining > 0 and count() > 0:
        progressed = False
        for multiple in ladder:
            before = count()
            if before == 0 or remaining <= 0:
                break
            part = step(float(penalty) * multiple, remaining)
            for entry in part:
                entry = dict(entry)
                entry['round'] = len(log)
                entry['ladder'] = multiple
                log.append(entry)
            remaining -= max(1, len(part))
            if count() < before:
                progressed = True
                break  # restart at the first multiple on the new failure set
        if not progressed:
            break
    return log


class LadderRouter(gr.Router):
    """grid_router.Router whose rip-up negotiation cycles RIPUP_PENALTY_LADDER (negotiate_with_ladder). build_control installs
    it as gr.Router for the duration of gr.run_plan, so the shared module is used unchanged; every other behaviour is inherited."""

    def negotiate(self, layers, allow_front_fallback=True, rounds=20, penalty=40.0, protected=(), tabu=4):
        def step(pen, budget):
            return super(LadderRouter, self).negotiate(layers, allow_front_fallback=allow_front_fallback, rounds=int(budget), penalty=pen,
                                                      protected=protected, tabu=tabu)

        def count():
            return sum(1 for u in self.unresolved if u.get('stage') == 'route')
        return negotiate_with_ladder(step, count, rounds, penalty)


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
            if part.get('dnp'):
                fp.SetDNP(True)  # V2.1: the schematics write (dnp yes) for DNP parts and kicad-cli --schematic-parity compares the attribute
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
        gaps = self.gap_for(self.by_ref[ref], angle, local_pads)
        self.occupied[side].append((ref, box, gaps))
        if any(pad.GetAttribute() in (self.pcb.PAD_ATTRIB_PTH, self.pcb.PAD_ATTRIB_NPTH) for pad in fp.Pads()):
            other = 'B' if side == 'F' else 'F'  # through-hole pins are copper on both outer layers: block the other side too
            if check:
                for other_ref, other_box, _ in self.occupied[other]:
                    if boxes_overlap(box, other_box):
                        raise ValueError(('courtyard overlap (through-hole, other side)', ref, other_ref, [round(v, 3) for v in box], [round(v, 3) for v in other_box]))
            self.occupied[other].append((ref, box, gaps))
        self.placements[ref] = dict(x=round(x, 4), y=round(y, 4), angle=angle, side=side, region=region, courtyard=[round(v, 3) for v in box])
        return box

    # ----- placement stages ------------------------------------------------------------------------------------------
    def place_fixed(self):
        c = self.candidate
        dsp = c['dsp']
        self.place(dsp['ref'], dsp['xy'][0], dsp['xy'][1], dsp['angle'], region='dsp')
        for ref, pose in c['fixed'].items():
            if ref not in self.footprints:
                raise ValueError(f'fixed part {ref} is not in the model')
            x, y, angle = pose[:3]
            self.place(ref, x, y, angle, side=pose[3] if len(pose) == 4 else 'F', region='fixed')
        for item in c['silkscreen']:
            self.occupied['F'].append((f"TEXT:{item['text']}", list(text_box(item['text'], item['xy'], item['size'])), (0.3, 0.3)))
        # candidate pre-routed copper (12V_IN bus, 5 V buck hot loop, eFuse output vias): keep auto-placed parts off it
        table = self.placed_pads()
        for item in c.get('pre_routed', []):
            points = [resolve_point(pt, table) for pt in item['points']]
            half = float(item['width']) / 2 + PREROUTE_GAP
            side = 'B' if item['layer'] == 'B.Cu' else 'F'
            for a, b in zip(points, points[1:]):
                box = [min(a[0], b[0]) - half, min(a[1], b[1]) - half, max(a[0], b[0]) + half, max(a[1], b[1]) + half]
                self.occupied[side].append((f"PREROUTE:{item['net']}", box, (0.0, 0.0)))
            for pt in list(item.get('vias', [])) + list(item.get('port_vias', [])):
                x, y = resolve_point(pt, table)
                r = VIA[0] / 2 + PREROUTE_GAP
                for s_ in ('F', 'B'):
                    self.occupied[s_].append((f"PREROUTE:{item['net']}", [x - r, y - r, x + r, y + r], (0.0, 0.0)))

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
        rings = c.get('dsp_near_rings', {})  # {ref: {pin, side, radius_mm}}: further parts placed radially at their DSP pin (review LR-04)
        groups: dict = {}
        for part in self.parts:
            if 'near_dsp_pin' in part:
                pad = pads[str(part['near_dsp_pin'])]
                rail = part['nets'].get('1')
                if rail not in cfg:
                    raise ValueError(f"{part['ref']}: no dsp_bypass configuration for rail {rail}")
                ring = (cfg[rail]['side'], float(cfg[rail]['radius_mm']), rail)
            elif part['ref'] in rings:
                spec = rings[part['ref']]
                pad = pads[str(spec['pin'])]
                ring = (spec['side'], float(spec['radius_mm']), f"ring{spec['radius_mm']}")
            else:
                continue
            dx, dy = pad['xy'][0] - centre[0], pad['xy'][1] - centre[1]
            if abs(dx) >= abs(dy):
                side_key, out, lateral = ('E' if dx > 0 else 'W'), (1 if dx > 0 else -1, 0), pad['xy'][1]
            else:
                side_key, out, lateral = ('S' if dy > 0 else 'N'), (0, 1 if dy > 0 else -1), pad['xy'][0]
            groups.setdefault((side_key, ring), []).append(dict(part=part, pad=pad, out=out, lateral=lateral))
        rails = sorted({ring for (_, ring) in groups}, key=lambda r: (r[0], r[1], r[2]))
        for rail in rails:
            side, radius = rail[0], rail[1]
            queue = []
            for (side_key, r_), items in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1][0], kv[0][1][1], kv[0][1][2])):
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
                            self.place(it['part']['ref'], x, y, angle, side=side, region=f'dsp_bypass_{rail[2]}')
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


def pad_boxes(board) -> dict:
    """(ref, number) -> dict(bbox=[x0, y0, x1, y1] mm, net) of every numbered pad (axis-aligned copper box) of a loaded board."""
    import pcbnew as pcb
    table = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNumber():
                bb = pad.GetBoundingBox()
                table[(fp.GetReference(), pad.GetNumber())] = dict(bbox=[pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())],
                                                                    net=pad.GetNetname())
    return table


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


def copper_obstacles(board, track_sample_mm: float = 0.25) -> list[dict]:
    """Every via and plated through pad on the board with its copper radius, plus the tracks on the island layer sampled
    every ``track_sample_mm`` as discs of half their width: In2.Cu corridor obstacles."""
    import pcbnew as pcb
    items = []
    island_layer = board.GetLayerID(ISLAND_LAYER)
    for item in board.GetTracks():
        if isinstance(item, pcb.PCB_VIA):
            items.append(dict(net=item.GetNetname(), xy=[round(v, 4) for v in pcb.ToMM(item.GetPosition())], r=round(pcb.ToMM(item.GetWidth(getattr(pcb, ISLAND_LAYER.replace('.', '_')))) / 2, 4)))
        elif item.GetLayer() == island_layer:
            a, b = pcb.ToMM(item.GetStart()), pcb.ToMM(item.GetEnd())
            steps = max(1, int(math.ceil(math.dist(a, b) / track_sample_mm - 1e-9)))
            radius = round(pcb.ToMM(item.GetWidth()) / 2, 4)
            for i in range(steps + 1):
                items.append(dict(net=item.GetNetname(), xy=[round(a[0] + (b[0] - a[0]) * i / steps, 4), round(a[1] + (b[1] - a[1]) * i / steps, 4)], r=radius, kind='track'))
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
                ends[(t.GetNetCode(), pt.x, pt.y, t.GetLayer())] += 1  # V2.1: per layer - a track end on another layer is no connection without a via
        via_keys = {(v.GetNetCode(), v.GetPosition().x, v.GetPosition().y) for v in vias}
        changed = False
        for t in tracks:  # every net: a track end connects only to another track end on its layer, a via or a pad (zones connect vias)
            half = t.GetWidth() // 2  # a wide cross piece ending between two same-net pads still overlaps both pads
            layer = t.GetLayer()
            for pt in (t.GetStart(), t.GetEnd()):
                key = (t.GetNetCode(), pt.x, pt.y)
                if ends[(*key, layer)] > 1 or key in via_keys or any(pad.IsOnLayer(layer) and pad.HitTest(pt, half) for pad in pads_by_code[t.GetNetCode()]):
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
                if pad.HitTest(pos, v.GetWidth(pcb.F_Cu) // 2):
                    layers.update(layer for layer in (pcb.F_Cu, pcb.B_Cu) if pad.IsOnLayer(layer))
            if len(layers) < 2:  # connected on one layer only (KiCad: via_dangling)
                board.Remove(v)
                removed['vias'] += 1
                changed = True
        if not changed:
            break
    return removed


def add_zones(board, zones: list[dict], save_path: Path) -> dict:
    """Add corridor zones with the grid router's zone API, give every zone its deterministic KIID, refill every zone and save/reload."""
    router = gr.Router(board, WIDTH, HEIGHT, ROUTING_LAYERS, grid=GRID, trace=TRACE, clearance=CLEARANCE, via=VIA,
                       net_rules=NET_RULES, board_margin=BOARD_MARGIN, hole_clearance=HOLE_CLEARANCE)
    for zone in zones:
        router.zone(zone['net'], ISLAND_LAYER, [tuple(p) for p in zone['polygon']], priority=zone['priority'], clearance=ZONE_CLEARANCE,
                    min_thickness=ZONE_MIN_THICKNESS)
    assign_zone_identities(board)  # before the fill: KiCad breaks equal-priority ties between zones by KIID
    router.fill()
    return gr.save_and_reload(board, save_path)


def refill_zones(board):
    """Rebuild connectivity and refill every zone (copper was added or removed outside a grid_router pass)."""
    import pcbnew as pcb
    board.BuildConnectivity()
    pcb.ZONE_FILLER(board).Fill(board.Zones())


def zone_outline_mm(board, zone) -> list[list[float]]:
    """Outer outline of a zone in mm (rounded to 4 decimals)."""
    import pcbnew as pcb
    chain = zone.Outline().Outline(0)
    return [[round(v, 4) for v in pcb.ToMM(chain.CPoint(i))] for i in range(chain.PointCount())]


def assign_zone_identities(board) -> list[dict]:
    """Set every zone's KIID to zone_identity(net, layer, priority, outline) (a no-op for a zone that already carries it); the fill that
    follows then resolves equal-priority ties the same way in every build. Returns [{net, layer, priority, uuid}]. Needs pcbnew."""
    import pcbnew as pcb
    rows, seen = [], set()
    for zone in board.Zones():
        layer, priority = board.GetLayerName(zone.GetLayer()), int(zone.GetAssignedPriority())
        identity = zone_identity(zone.GetNetname(), layer, priority, zone_outline_mm(board, zone))
        if identity in seen:
            raise RuntimeError(f'two zones share the identity {identity} ({zone.GetNetname()} {layer} priority {priority})')
        seen.add(identity)
        if zone.m_Uuid.AsString() != identity:
            zone.SetUuid(pcb.KIID(identity))
        rows.append(dict(net=zone.GetNetname(), layer=layer, priority=priority, uuid=identity))
    return rows


def zone_table(board) -> list[dict]:
    """Every zone with net, layer, priority, KIID, outline bounding box and filled area (mm2): the record a second build is compared with."""
    rows = []
    for zone in board.Zones():
        layer = zone.GetLayer()
        bbox = polygon_bbox(zone_outline_mm(board, zone))
        rows.append(dict(net=zone.GetNetname(), layer=board.GetLayerName(layer), priority=int(zone.GetAssignedPriority()), uuid=zone.m_Uuid.AsString(),
                         bbox=[round(v, 4) for v in bbox], outline_mm2=round(zone.Outline().Area() / 1e12, 3),
                         filled_mm2=round(zone.GetFilledPolysList(layer).Area() / 1e12, 3)))
    return sorted(rows, key=lambda r: (r['layer'], r['net'], r['priority'], r['bbox']))


def through_items(board) -> list[dict]:
    """Vias and plated through pads {net, xy, kind}: the only copper a single-layer inner route can start or end on."""
    import pcbnew as pcb
    items = []
    for item in board.GetTracks():
        if isinstance(item, pcb.PCB_VIA):
            items.append(dict(net=item.GetNetname(), xy=[round(v, 4) for v in pcb.ToMM(item.GetPosition())], kind='via'))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute() == pcb.PAD_ATTRIB_PTH and pad.GetNetname():
                items.append(dict(net=pad.GetNetname(), xy=[round(v, 4) for v in pcb.ToMM(pad.GetPosition())], kind=f'pad {fp.GetReference()}.{pad.GetNumber()}'))
    return items


def group_components(records: list[dict]) -> list[list[dict]]:
    """Connected groups of copper ``records`` by coincident geometry (pure). A record is dict(kind, pos=(x, y)[, layer][, hits]):
    track ends ('end', one per end, with its layer) join other ends of the same layer at the same position; vias and plated
    pads ('via' / 'pth', no layer) join everything at their position; ``hits`` names the record ids a pad overlaps. Positions
    coincide within 1e-3 mm. Each record carries ``id`` (the owning item); the groups are lists of records."""
    parent = {}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
    for r in records:
        parent.setdefault(r['id'], r['id'])
    by_pos = {}
    for r in records:
        key = (round(r['pos'][0] * 1000), round(r['pos'][1] * 1000))
        by_pos.setdefault(key, []).append(r)
    for group in by_pos.values():
        anchors = [r for r in group if r.get('layer') is None]
        by_layer = {}
        for r in group:
            if r.get('layer') is not None:
                by_layer.setdefault(r['layer'], []).append(r)
        for same in by_layer.values():
            for r in same[1:]:
                union(same[0]['id'], r['id'])
        for a in anchors:
            for r in group:
                union(a['id'], r['id'])
    for r in records:
        for other in r.get('hits', ()):
            if other in parent:
                union(r['id'], other)
    groups = {}
    for r in records:
        groups.setdefault(find(r['id']), []).append(r)
    return list(groups.values())


def net_components(board, net) -> list[dict]:
    """Copper groups of ``net`` on ``board`` (tracks, vias, pads) by coincident geometry: [{points: {(x, y)}, through: [{xy, kind}]}].
    Track ends meet on one layer, vias and plated pads on every layer, a pad takes the track ends and via centres it covers."""
    import pcbnew as pcb
    mm = pcb.ToMM
    records = []
    tracks = [item for item in board.GetTracks() if item.GetNetname() == net]
    pads = [pad for pad in board.GetPads() if pad.GetNetname() == net]
    for index, item in enumerate(tracks):
        tid = ('t', index)
        if isinstance(item, pcb.PCB_VIA):
            records.append(dict(id=tid, kind='via', pos=tuple(round(v, 4) for v in mm(item.GetPosition()))))
        else:
            for pt in (item.GetStart(), item.GetEnd()):
                records.append(dict(id=tid, kind='end', pos=tuple(round(v, 4) for v in mm(pt)), layer=item.GetLayer()))
    for index, pad in enumerate(pads):
        pid = ('p', index)
        pth = pad.GetAttribute() == pcb.PAD_ATTRIB_PTH
        hits = set()
        for tindex, item in enumerate(tracks):
            if isinstance(item, pcb.PCB_VIA):
                if pth and pad.HitTest(item.GetPosition()):
                    hits.add(('t', tindex))
            elif any((pth or pad.IsOnLayer(item.GetLayer())) and pad.HitTest(pt) for pt in (item.GetStart(), item.GetEnd())):
                hits.add(('t', tindex))
        records.append(dict(id=pid, kind='pth' if pth else 'smd', pos=tuple(round(v, 4) for v in mm(pad.GetPosition())),
                            layer=None if pth else pad.GetLayer(), hits=hits, label=f'pad {pad.GetParentFootprint().GetReference()}.{pad.GetNumber()}'))
    components = []
    for group in group_components(records):
        points = {r['pos'] for r in group}
        through = []
        seen = set()
        for r in group:
            if r['kind'] in ('via', 'pth') and r['pos'] not in seen:
                seen.add(r['pos'])
                through.append(dict(xy=list(r['pos']), kind=r.get('label', 'via')))
        components.append(dict(points=points, through=through))
    return components


def component_through_items(components: list[dict], xy, tolerance: float = 1e-3) -> list[dict]:
    """Through items (vias, plated pads) of the copper group that contains the point ``xy`` (pure)."""
    for component in components:
        if any(abs(px - xy[0]) < tolerance and abs(py - xy[1]) < tolerance for px, py in component['points']):
            return list(component['through'])
    return []


def inner_layer_route(board, nets, unresolved, candidate: dict, *, port_hints: dict | None = None, layer: str = ISLAND_LAYER, style=None) -> dict:
    """Route whole ``nets`` and single unresolved F.Cu/B.Cu connections (grid_router 'route' records) as tracks on the island
    layer with a single-layer grid_router pass: every rail island polygon (inflated by INNER_KEEPOUT_MARGIN) is a keepout, so is
    the INNER_EDGE_BAND around it except for each port's straight exit channel (band_keepouts), vias and plated pads are obstacles
    at INNER_CLEARANCE. Each connection is tried as a Z (inner_route_waypoints: leave the first port straight along its channel
    axis, turn where the fewest through items lie) and then directly. ``port_hints`` {net: [[x, y], ...]} are escape via positions
    the F.Cu/B.Cu pass pruned (their grid cells stayed reserved for the net): they are re-created for a whole net, and at a fallback
    port when inner_via_fits allows it. Fallback connections carry their source record under ``source``.
    Returns dict(layer, keepouts, band_keepouts, channels, tracks, vias_added, routed=[{net, kind, start, end, waypoints, length_mm}],
    failed=[...]).
    """
    wanted = list(dict.fromkeys(list(nets) + [u['net'] for u in unresolved]))
    result = dict(layer=layer, keepouts=0, band_keepouts=0, channels=[], tracks=0, vias_added=[], routed=[], failed=[])
    if not wanted:
        return result
    router = gr.Router(board, WIDTH, HEIGHT, [layer], grid=GRID, trace=ROUTER_TRACE, clearance=CLEARANCE, via=VIA,
                       net_rules={net: dict(clearance=INNER_CLEARANCE) for net in wanted}, board_margin=BOARD_MARGIN,
                       hole_clearance=HOLE_CLEARANCE, max_nodes=MAX_NODES, style=style)
    router.stage = 'signal'  # V2.1: this pass's own tracks are eligible for Router.beautify (style.stages); the registered copper stays fixed
    start_length = dict(router.length)  # registered copper per net: the inner-layer addition is the difference after beautify
    island_rects = []
    for net, polygon in candidate['islands'].items():
        if polygon == 'background':
            continue
        for rect in rectilinear_rectangles(polygon):
            island_rects.append(rect)
            x0, y0, x1, y1 = rect
            router.keepout(0, x0 - INNER_KEEPOUT_MARGIN, y0 - INNER_KEEPOUT_MARGIN, x1 + INNER_KEEPOUT_MARGIN, y1 + INNER_KEEPOUT_MARGIN, -1)
            result['keepouts'] += 1
    items = through_items(board)

    def at(net, xy, tolerance=0.1):
        return [it for it in items if it['net'] == net and math.dist(it['xy'], xy) < tolerance]

    def port(xy):
        gx, gy = router.to_grid(*xy)
        return (gx, gy, 0, 'INNER', '')

    # ---- the connections to route (no copper yet except re-created escape vias) --------------------------------------------
    connections = []  # (net, kind, a, b, extra)
    for net in nets:
        if net not in router.code:
            result['failed'].append(dict(net=net, kind='net', reason='net not on the board'))
            continue
        for xy in (port_hints or {}).get(net, []):
            if not at(net, xy, 1e-3):
                router.via(tuple(xy), net)
                items.append(dict(net=net, xy=[round(v, 4) for v in xy], kind='via'))
                result['vias_added'].append(dict(net=net, xy=[round(v, 4) for v in xy], kind='net'))
        anchors = [list(it['xy']) for it in sorted((it for it in items if it['net'] == net), key=lambda it: (0 if it['kind'] == 'via' else 1, it['xy']))]
        if len(anchors) < 2:
            result['failed'].append(dict(net=net, kind='net', reason=f'{len(anchors)} through item(s) of {net}: nothing to join on {layer}'))
            continue
        connected, rest = [anchors[0]], anchors[1:]
        while rest:  # nearest-first chain; a two-pin net is one connection starting at its escape via
            _, a, b = min((abs(a[0] - b[0]) + abs(a[1] - b[1]), a, b) for a in connected for b in rest)
            connections.append((net, 'net', a, b, {}))
            connected.append(b)
            rest.remove(b)
    for u in unresolved:
        net = u['net']
        if net not in router.code:
            continue
        a, b = [round(v, 4) for v in router.to_mm(*u['start'][:2])], [round(v, 4) for v in router.to_mm(*u['end'][:2])]
        recreated = []
        components = None

        def outside_islands(xy):
            return not any(x0 - INNER_KEEPOUT_MARGIN <= xy[0] <= x1 + INNER_KEEPOUT_MARGIN and y0 - INNER_KEEPOUT_MARGIN <= xy[1] <= y1 + INNER_KEEPOUT_MARGIN
                           for x0, y0, x1, y1 in island_rects)

        def candidates(xy, other):
            """Through items usable as this side's port: the point itself, a re-created escape via there, or the through items
            of the point's own copper group (nearest to the other side first), all outside the island keepouts."""
            nonlocal components
            if at(net, xy):
                return [list(xy)]
            if any(math.dist(xy, hint) < 1e-3 for hint in (port_hints or {}).get(net, [])) and inner_via_fits(router, board, net, xy, layer):
                if router.via(tuple(xy), net) is not None:  # a pruned escape via: its F.Cu pad track is still there, the grid cell stayed reserved
                    items.append(dict(net=net, xy=[round(v, 4) for v in xy], kind='via'))
                    result['vias_added'].append(dict(net=net, xy=[round(v, 4) for v in xy], kind='fallback'))
                recreated.append([round(v, 4) for v in xy])
                return [list(xy)]
            if components is None:
                components = net_components(board, net)
            through = [list(it['xy']) for it in component_through_items(components, xy) if outside_islands(it['xy'])]
            return sorted(through, key=lambda p: (abs(p[0] - other[0]) + abs(p[1] - other[1]), p))
        starts, ends = candidates(a, b), candidates(b, a)
        if not starts or not ends:
            result['failed'].append(dict(net=net, kind='fallback', start=a, end=b, source=dict(u),
                                         reason=f'no via or plated pad of {net} in the copper group of {[xy for xy, c in ((a, starts), (b, ends)) if not c]}'))
            continue
        _, a2, b2 = min((abs(s[0] - e[0]) + abs(s[1] - e[1]), s, e) for s in starts[:6] for e in ends[:6])
        connections.append((net, 'fallback', a2, b2, dict(source=dict(u), vias_recreated=recreated, recorded_ports=[a, b])))
    # ---- island edge bands, open only along each port's exit channel -----------------------------------------------------------
    ports = [c[2] for c in connections] + [c[3] for c in connections]
    band_rects, channels = band_keepouts(island_rects, ports)
    for x0, y0, x1, y1 in band_rects:
        router.keepout(0, x0, y0, x1, y1, -1)
    result['band_keepouts'] = len(band_rects)
    result['band_mm'] = INNER_EDGE_BAND
    result['channels'] = [dict(port=list(key), axis=axis, direction=sign, rect=[round(v, 4) for v in rect]) for key, (rect, axis, sign) in sorted(channels.items())]

    def connect(net, kind, a, b, **extra):
        before, length_before = len(router.unresolved), router.length[net]
        channel = channels.get((round(a[0], 4), round(a[1], 4)))
        axis, direction, search = 'y', None, INNER_TURN_SEARCH
        if channel is not None:  # leave straight through the channel; the first turn lies beyond its far end
            rect, axis, direction = channel
            reach = ((rect[2] - a[0]) if direction > 0 else (a[0] - rect[0])) if axis == 'x' else ((rect[3] - a[1]) if direction > 0 else (a[1] - rect[1]))
            search = (max(INNER_TURN_SEARCH[0], reach + 2 * GRID), INNER_TURN_SEARCH[1], INNER_TURN_SEARCH[2])
        waypoints = inner_route_waypoints(a, b, items, axis=axis, direction=direction, search=search)
        failures = router.route_net(net, ports=[port(p) for p in waypoints], layers=(0,), allow_front_fallback=False)
        if failures and len(waypoints) > 2:  # a leg of the Z is blocked: plain A* between the two ports (prune_dangling drops leftover legs)
            waypoints = [waypoints[0], waypoints[-1]]
            failures = router.route_net(net, ports=[port(p) for p in waypoints], layers=(0,), allow_front_fallback=False)
        del router.unresolved[before:]
        record = dict(net=net, kind=kind, start=[round(v, 4) for v in a], end=[round(v, 4) for v in b], waypoints=waypoints, axis=axis, direction=direction,
                      length_mm=round(router.length[net] - length_before, 3), **extra)
        if failures:
            record['reason'] = 'no path on the inner layer within the via/pad/island/band constraints'
        (result['failed'] if failures else result['routed']).append(record)
        return not failures

    for net, kind, a, b, extra in connections:
        connect(net, kind, a, b, **extra)
    if router.style['simplify'] != 'none' or router.style['arcs']:  # V2.1: the final geometry stage of grid_router.run_plan, on this pass's copper
        result['beautify'] = router.beautify()
    result['tracks'] = int(router.stats['tracks'])
    result['arcs'] = int(router.stats['arcs'])
    result['net_length_mm'] = {net: round(router.length[net] - start_length.get(net, 0.0), 3) for net in dict.fromkeys(r['net'] for r in result['routed'])}
    return result


def connectivity_unconnected(board) -> int:
    """KiCad's own count of missing connections (ratsnest lines) on ``board`` after a connectivity rebuild - the same figure the
    DRC reports as unconnected items; zone fills count as copper."""
    board.BuildConnectivity()
    return int(board.GetConnectivity().GetUnconnectedCount(False))


def point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    """Distance from point (px, py) to the segment (ax, ay)-(bx, by)."""
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 <= 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def inner_via_fits(router, board, net, xy, layer: str) -> bool:
    """A via re-created at ``xy`` for ``net`` keeps the inner router's via rules (other vias, holes, regions) and INNER_CLEARANCE
    to every other-net track on the inner ``layer``. The F.Cu/B.Cu copper around a pruned escape via is unchanged: the outer
    stages kept its grid cell reserved for the net after prune_unused_vias."""
    import pcbnew as pcb
    gx, gy = router.to_grid(*xy)
    if not router.via_allowed(gx, gy, net):
        return False
    layer_id = board.GetLayerID(layer)
    for item in board.GetTracks():
        if isinstance(item, pcb.PCB_VIA) or item.GetLayer() != layer_id or item.GetNetname() == net:
            continue
        a, b = pcb.ToMM(item.GetStart()), pcb.ToMM(item.GetEnd())
        gap = point_segment_distance(xy[0], xy[1], a[0], a[1], b[0], b[1]) - pcb.ToMM(item.GetWidth()) / 2 - VIA[0] / 2
        if gap < INNER_CLEARANCE - 1e-9:
            return False
    return True


def fill_slivers(board, max_area: float = SLIVER_AREA_MM2) -> list[dict]:
    """Rail-zone fill outlines on the island layer below ``max_area`` mm2 (review LR-15 fragments), with their bounding boxes."""
    import pcbnew as pcb
    layer = board.GetLayerID(ISLAND_LAYER)
    found = []
    for zone in board.Zones():
        if zone.GetNetname() not in RAILS or not zone.IsOnLayer(layer):
            continue
        filled = zone.GetFilledPolysList(layer)
        for i in range(filled.OutlineCount()):
            outline = filled.Outline(i)
            area = abs(outline.Area()) / 1e12
            if area < max_area:
                bb = outline.BBox()
                found.append(dict(net=zone.GetNetname(), priority=int(zone.GetAssignedPriority()), area_mm2=round(area, 5),
                                  bbox=[round(pcb.ToMM(bb.GetX()), 4), round(pcb.ToMM(bb.GetY()), 4), round(pcb.ToMM(bb.GetRight()), 4), round(pcb.ToMM(bb.GetBottom()), 4)]))
    return found


def trim_fill_slivers(board, corridors: list[dict], save_path: Path, *, step: float = SLIVER_TRIM_STEP, rounds: int = SLIVER_TRIM_ROUNDS) -> dict:
    """Widen the same-net corridor edge next to every In2.Cu fill sliver by ``step``, refill and repeat (at most ``rounds`` times).

    Corridor records are matched to their board zones by net and priority (distinct per corridor) and their polygons are
    updated in place, so the rail-coverage check and the routing-plan record see the trimmed geometry. A nudge that would
    put the corridor within ZONE_CLEARANCE of an other-net corridor is skipped and listed. Returns dict(rounds=[sliver count
    per round], adjusted=[...], skipped=[...], remaining=[slivers left], saved=counts | None)."""
    import pcbnew as pcb
    layer = board.GetLayerID(ISLAND_LAYER)
    zones = {(z.GetNetname(), int(z.GetAssignedPriority())): z for z in board.Zones() if z.IsOnLayer(layer)}
    counts, adjusted, skipped = [], [], []
    for round_index in range(rounds + 1):
        slivers = fill_slivers(board)
        counts.append(len(slivers))
        if not slivers or round_index == rounds:
            break
        moved = 0
        for sliver in slivers:
            for record in corridors:
                if record['net'] != sliver['net']:
                    continue
                rect = polygon_bbox(record['polygon'])
                edge = sliver_edge(rect, sliver['bbox'])
                if edge is None:
                    continue
                new_rect = widened(rect, edge, step)
                if any(other['net'] != record['net'] and boxes_overlap(new_rect, polygon_bbox(other['polygon']), ZONE_CLEARANCE, ZONE_CLEARANCE) for other in corridors):
                    skipped.append(dict(net=record['net'], xy=record['xy'], edge=edge, reason='would come within the zone clearance of an other-net corridor', sliver=sliver))
                    continue
                zone = zones.get((record['net'], int(record['priority'])))
                if zone is None:
                    skipped.append(dict(net=record['net'], xy=record['xy'], edge=edge, reason='corridor zone not found on the board', sliver=sliver))
                    continue
                record['polygon'] = [[new_rect[0], new_rect[1]], [new_rect[2], new_rect[1]], [new_rect[2], new_rect[3]], [new_rect[0], new_rect[3]]]
                record['sliver_trim_mm'] = round(record.get('sliver_trim_mm', 0.0) + step, 4)
                outline = zone.Outline()
                outline.RemoveAllContours()
                outline.NewOutline()
                for x, y in record['polygon']:
                    outline.Append(pcb.FromMM(x), pcb.FromMM(y))
                adjusted.append(dict(net=record['net'], xy=record['xy'], priority=record['priority'], edge=edge, step_mm=step, sliver_mm2=sliver['area_mm2'], sliver_bbox=sliver['bbox']))
                moved += 1
        if not moved:
            break
        refill_zones(board)
    saved = gr.save_and_reload(board, save_path) if adjusted else None
    return dict(rounds=counts, adjusted=adjusted, skipped=skipped, remaining=fill_slivers(board), saved=saved)


def rail_zone_outlines(board) -> list[dict]:
    """Filled-outline statistics of every rail zone on the island layer: outline count, outlines above 1 mm2 (the rest are
    fill slivers) and the largest outline's area. Island zones are expected to fill as one outline; the 3V3 background may
    carry more where corridor zones or tracks separate same-net fragments."""
    layer = board.GetLayerID(ISLAND_LAYER)
    rows = []
    for zone in board.Zones():
        if zone.GetNetname() not in RAILS or not zone.IsOnLayer(layer):
            continue
        filled = zone.GetFilledPolysList(layer)
        areas = []
        for i in range(filled.OutlineCount()):
            try:
                areas.append(abs(filled.Outline(i).Area()) / 1e12)
            except Exception:  # noqa: BLE001 - SWIG surface differences between KiCad builds
                areas.append(None)
        known = [a for a in areas if a is not None]
        rows.append(dict(net=zone.GetNetname(), priority=int(zone.GetAssignedPriority()), outlines=int(filled.OutlineCount()),
                         outlines_over_1mm2=sum(1 for a in known if a > 1.0) if known else None,
                         largest_mm2=round(max(known), 1) if known else None, area_mm2=round(filled.Area() / 1e12, 1)))
    return sorted(rows, key=lambda r: (r['net'], r['priority']))


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


def routing_quality_metrics(board_path, output_dir, label: str, plan: dict | None, report: dict | None) -> dict:
    """Run automation.verification.check_routing_quality on a board (in-process, needs pcbnew) and write routing_quality_<label>.json/.md;
    ``plan`` attributes its pre-routed tracks, ``report`` (router report with a ``beautify`` block) explains the remaining sharp corners."""
    from automation.verification import check_routing_quality as cq
    doc = cq.extract_board(board_path)
    m = cq.measure(doc, plan=plan, report=report)
    json_path, md_path = cq.write_outputs(m, output_dir, label)
    return dict(json=str(json_path), md=str(md_path), totals=m['totals'], by_attribution=m['by_attribution'],
                sharp_corners_by_reason=m['sharp_corners']['by_reason'], arcs={k: v for k, v in m['arcs'].items() if k != 'tangency_failures'})


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
                  plan_filter=None, style=None) -> dict:
    """Place (and optionally route, zone, check and DRC) one floorplan candidate into ``output_pcb``.

    Returns a result dict with the placement, the escape plan, the router report, the rail-island
    checks, the DRC manifest summary and the layout-metrics paths. Needs pcbnew (KiCad's Python).
    ``style``: grid_router V2.1 ``style`` block (None = ``ROUTING_STYLE``, {} = V2 geometry).
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
    # candidate pre-routed copper (12V_IN bus, 5 V buck hot loop, eFuse output via group) and exposed-pad via arrays
    extra = candidate_pre_routed(candidate, table)
    arrays = exposed_pad_arrays(pad_boxes(loaded), candidate, plane_nets=set(RAILS) | {GROUND})
    extra['tracks'] += arrays['tracks']
    extra['vias'] += arrays['vias']
    extra['skip_pads'] += arrays['skip_pads']
    inpad = [] if candidate.get('exposed_pad_vias') else None
    plan = routing_plan(candidate, escapes, output_pcb, ic_refs=ic_refs, ic_escapes=ic_escapes, dsp_centre=centre, dsp_signal_nets=dsp_signal_nets,
                        lanes=lanes, extra=extra, inpad_vias=inpad, style=ROUTING_STYLE if style is None else style)
    result['pre_routed_copper'] = dict(candidate_tracks=len(extra['tracks']) - len(arrays['tracks']), candidate_vias=len(extra['vias']) - len(arrays['vias']),
                                       skip_pads=extra['skip_pads'], exposed_pad_arrays=arrays['records'])
    if plan_filter is not None:  # diagnostics hook (tests, experiments): may restrict or adjust the plan before routing
        plan = plan_filter(plan)
    plan['escape_distances'] = list(ESCAPE_DISTANCES)  # recorded in the plan file; applied to the router module below
    default_distances, default_router = gr.ESCAPE_DISTANCES, gr.Router
    gr.ESCAPE_DISTANCES = tuple(ESCAPE_DISTANCES)
    gr.Router = LadderRouter  # rip-up negotiation with RIPUP_PENALTY_LADDER; the shared module itself is unchanged
    try:
        report = gr.run_plan(loaded, {k: v for k, v in plan.items() if k != 'escape_distances'})
    finally:
        gr.ESCAPE_DISTANCES = default_distances
        gr.Router = default_router
    report['ripup_penalty_ladder'] = [round(float(plan.get('ripup_penalty', 40.0)) * m, 3) for m in RIPUP_PENALTY_LADDER]
    report['shared_router_sha256'] = hashlib.sha256(Path(gr.__file__).read_bytes()).hexdigest()  # grid_router.py is edited by the power-board agent
    # ---- stage 1b: In2.Cu pass for the inner-layer nets and the connections the F.Cu/B.Cu stages left unresolved ------
    board_nets = {p['net'] for p in table.values()}
    inner_nets = [net for net in INNER_SIGNAL_NETS if net in board_nets]
    hints = {}  # every DSP escape via: the In2.Cu pass re-creates one the F.Cu/B.Cu stage pruned when a route needs it as a port
    for e in escapes:
        hints.setdefault(e['net'], []).append(list(e['via']))
    leftovers = [u for u in report.get('unresolved', []) if u.get('stage') == 'route'] if INNER_LAYER_FALLBACK else []
    inner = inner_layer_route(loaded, inner_nets, leftovers, candidate, port_hints=hints, style=plan.get('style'))  # same V2.1 style as the plan
    inner['port_hints'] = sum(len(v) for v in hints.values())
    resolved = [r['source'] for r in inner['routed'] if r.get('kind') == 'fallback']
    report['unresolved'] = [u for u in report.get('unresolved', []) if u not in resolved]
    report['inner_layer'] = inner
    report['tracks'] = int(report.get('tracks') or 0) + inner['tracks']
    report['vias'] = int(report.get('vias') or 0) + len(inner['vias_added'])
    report['arcs'] = int(report.get('arcs') or 0) + int(inner.get('arcs') or 0)
    for net, added in inner.get('net_length_mm', {}).items():  # after the pass's beautify (the routed records keep the pre-beautify lengths)
        report.setdefault('net_length_mm', {})[net] = round(report['net_length_mm'].get(net, 0.0) + added, 3)
    inner_beautify = inner.get('beautify')
    if inner_beautify and inner_beautify.get('enabled') and (report.get('beautify') or {}).get('enabled'):  # one exception list for the checker's reasons
        main = report['beautify']
        main['exceptions'] = list(main.get('exceptions', [])) + list(inner_beautify.get('exceptions', []))
        for reason, count in inner_beautify.get('exceptions_by_reason', {}).items():
            main.setdefault('exceptions_by_reason', {})[reason] = main['exceptions_by_reason'].get(reason, 0) + count
        inner['beautify'] = {k: v for k, v in inner_beautify.items() if k != 'exceptions'}
    pruned = prune_dangling(loaded, protected_nets=set(RAILS) | {GROUND})
    report['pruned_dangling'] = pruned
    inner_copper = bool(inner['routed'] or inner['vias_added'])
    if inner_copper:
        refill_zones(loaded)  # the island fills step back from the new In2.Cu copper (zone clearance 0.25 mm)
    if pruned['tracks'] or pruned['vias'] or inner_copper:
        report['saved'] = gr.save_and_reload(loaded, output_pcb)
    if inject_stackup(output_pcb):
        report['stackup_reinjected'] = True
        gr.save_and_reload(pcb.LoadBoard(str(output_pcb)), output_pcb)
    # ---- stage 2: corridor zones for rail copper outside its island ------------------------------------------------
    board2 = pcb.LoadBoard(str(output_pcb))
    items = rail_items(board2)
    corridor_result = island_corridors(items, candidate['islands'], obstacles=copper_obstacles(board2), half_width_by_net=CORRIDOR_HALF_WIDTH_BY_NET)
    if corridor_result['corridors']:
        corridor_result['saved'] = add_zones(board2, corridor_result['corridors'], output_pcb)  # assigns the zone KIIDs before its fill
        corridor_result['sliver_trim'] = trim_fill_slivers(board2, corridor_result['corridors'], output_pcb)  # review LR-15
    else:  # no corridor: the final fill still has to run on deterministic zone KIIDs
        assign_zone_identities(board2)
        refill_zones(board2)
        corridor_result['saved'] = gr.save_and_reload(board2, output_pcb)
    uncovered = uncovered_rail_items(items, candidate['islands'], corridor_result['corridors'])
    fanout_rail_failures = rail_smd_pads_without_via(board2, report)
    final_board = pcb.LoadBoard(str(output_pcb))
    board_counts = dict(tracks=sum(1 for t in final_board.GetTracks() if not isinstance(t, pcb.PCB_VIA)),
                        vias=sum(1 for t in final_board.GetTracks() if isinstance(t, pcb.PCB_VIA)), zones=len(list(final_board.Zones())))
    result['connectivity_unconnected'] = connectivity_unconnected(final_board)  # KiCad's ratsnest count on the finished copper (0 expected)
    result.update(escapes=dict(records=escapes, inward=sum(e['direction'] == 'in' for e in escapes), outward=sum(e['direction'] == 'out' for e in escapes),
                               candidate_pre_routed=result.get('pre_routed_copper'),
                               exceptions=[e for e in escapes if e['exception']], stubs=sum(1 for t in plan['pre_routed']['tracks'] if t['layer'] == 'B.Cu'),
                               lanes=lanes, ic_escapes={ref: len(recs) for ref, recs in ic_escapes.items()}),
                  routing_plan=plan, report=report, corridors=corridor_result, board_counts=board_counts,
                  rail_items_without_island_or_corridor=uncovered, rail_fanout_failures=fanout_rail_failures,
                  rail_zone_outlines=rail_zone_outlines(final_board), zone_table=zone_table(final_board))
    # ---- metrics and DRC --------------------------------------------------------------------------------------------
    if metrics:
        result['layout_metrics'] = checker_metrics(output_pcb, metrics_dir or CHECKS_DIR, metrics_label)
        result['layout_metrics'].pop('metrics', None) if write_outputs else None
        result['routing_quality'] = routing_quality_metrics(output_pcb, metrics_dir or CHECKS_DIR, metrics_label, plan, report)  # V2.1 TASK 2
    if drc:
        from automation.kicad_tools.run_check import run_check
        code, manifest_path = run_check('drc', output_pcb, DRC_DIR, cli)
        manifest = read_manifest(manifest_path)
        result['drc'] = dict(manifest=str(manifest_path), wrapper_exit_code=code, tool_exit_code=manifest.get('tool_exit_code'),
                             status=manifest.get('status'), finding_count=manifest.get('finding_count'), violations=manifest.get('violations'),
                             unconnected_items=manifest.get('unconnected_items'), schematic_parity=manifest.get('schematic_parity'),
                             details=manifest.get('details', [])[:200], error=manifest.get('error'))
        if write_outputs:
            result['stored_fill_check'] = stored_fill_check(output_pcb, cli, metrics_label)  # diagnostic: the fills as stored (exports) vs the refill DRC
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
                    stage1b_inner_layer_pass=dict(layer=ISLAND_LAYER, nets=list(INNER_SIGNAL_NETS), fallback_for_unresolved=INNER_LAYER_FALLBACK,
                                                  keepout_margin_mm=INNER_KEEPOUT_MARGIN, clearance_mm=INNER_CLEARANCE, turn_search_mm=list(INNER_TURN_SEARCH),
                                                  edge_band_mm=INNER_EDGE_BAND, channel_half_width_mm=INNER_CHANNEL_HALF_WIDTH,
                                                  result=result['report'].get('inner_layer')),
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
                    signal_order_trials=report.get('signal_order_trials'), signal_order_selected=report.get('signal_order_selected'),
                    ripup_rounds=report.get('ripup_rounds'), ripup_penalty_ladder=report.get('ripup_penalty_ladder'),
                    shared_router_sha256=report.get('shared_router_sha256'),
                    net_length_mm=report.get('net_length_mm'), grid=report.get('grid'), routing_seconds=report.get('seconds'),
                    style=report.get('style'), arcs=report.get('arcs'), beautify=report.get('beautify'), routing_quality=result.get('routing_quality'),  # V2.1
                    inner_layer=report.get('inner_layer'),
                    corridor_zones=len(result['corridors']['corridors']), corridor_issues=result['corridors']['issues'],
                    sliver_trim=result['corridors'].get('sliver_trim'),
                    rail_items_without_island_or_corridor=result['rail_items_without_island_or_corridor'],
                    rail_fanout_failures=result['rail_fanout_failures'], rail_zone_outlines=result.get('rail_zone_outlines'),
                    zone_table=result.get('zone_table'),  # net, layer, priority, deterministic KIID, outline bbox, filled mm2 per zone (reproducibility record)
                    connectivity_unconnected=result.get('connectivity_unconnected'),
                    drc=result.get('drc'), stored_fill_check=result.get('stored_fill_check'), layout_metrics=result.get('layout_metrics'), seconds=result['seconds'],
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
            f"{counts.get('zones')} zones, {len(report.get('unresolved', []))} unresolved, "
            f"{len((report.get('inner_layer') or {}).get('routed', []))} In2.Cu routes, {len(result.get('corridors', {}).get('corridors', []))} corridors, "
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
    parser.add_argument('--no-style', action='store_true', help='route with the V2 geometry (no 8-direction search, simplification or arcs)')
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
        result = build_control(candidate_path(args.candidate), args.output, route=not args.no_route, drc=not args.no_drc, metrics=not args.no_metrics, cli=cli,
                               style={} if args.no_style else None)
        print(summary_line(result) if not args.no_route else f"candidate {result['candidate']}: placed {len(result['placements'])} parts -> {result['board']}", flush=True)
        return 0
    evaluation = evaluate_candidates(('A', 'B'), scratch, cli=cli)
    selected = evaluation['selected']
    print(f"selected candidate {selected} (scores {evaluation['scoring']['scores']})", flush=True)
    final = None
    if not args.no_route:
        final = build_control(candidate_path(selected), args.output, route=True, drc=not args.no_drc, metrics=not args.no_metrics, cli=cli,
                              style={} if args.no_style else None)
        print(summary_line(final), flush=True)
    else:
        final = None
        build_control(candidate_path(selected), args.output, route=False, drc=False, metrics=False, cli=cli)
    write_comparison(evaluation, final)
    print(f"comparison -> {REVIEW_DIR / 'floorplan_candidates_control.md'}", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
