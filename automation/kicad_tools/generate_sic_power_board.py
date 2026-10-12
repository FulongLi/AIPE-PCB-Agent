"""Place, pour, route and check the SiC buck POWER board (AIPE_SiC_Buck_Power; V2 design, V2.1 generation) with pcbnew and the grid router.

AI-GENERATED ENGINEERING PROTOTYPE - V2.1 - HUMAN REVIEW REQUIRED (label: sic_buck_common.GENERATION)

Follows automation.kicad_tools.v2_pipeline_smoke.board_stage() and generate_sic_control_board.py: kicad-cli XML
netlist of the generated schematic, a pcbnew BOARD with the project footprint libraries and the symbol paths of
design/schematic_mapping_power.json, a deterministic placement (every structural part fixed by the floorplan
below, the small island / strip parts auto-placed in regions with a courtyard-overlap check), the 4 x 70 um /
2.0 mm stackup injected as text, the HV copper as zones (VIN+ F.Cu/In2.Cu over PGND In1.Cu for the commutation
loop, SW F.Cu/In2.Cu, VOUT F.Cu/In2.Cu/B.Cu, Kelvin-source pours on In2.Cu under the driver islands, GND_CTRL on
In1.Cu and 3V3 on In2.Cu under the SELV strip), HV via groups of 1.2/0.6 mm, grid_router.run_plan for the signals
on three routing layers (F.Cu, In2.Cu inside the driver islands, B.Cu) with per-net routing regions (every island
net stays inside its island footprint, every SELV net inside the SELV strip), rule areas (ISO_BARRIER, heatsink
keep-out, standoff annuli), zone fill, SaveBoard/LoadBoard, then kicad-cli DRC with --schematic-parity
--severity-all through automation.kicad_tools.run_check and the layout metrics checker.

Floorplan (design/design_decisions.json schema 4, design/pcb_stackup.md): 240 x 180 mm; HV area y < 140, ISO_BARRIER
strip y 140-150 (copper-free on every layer except the barrier packages' pad rows, which sit over the footprints'
own 1.2 mm NPTH slots), SELV strip y 150-180 with the mezzanine socket J7 and the four M3 standoff holes; heatsink
HS1 (100 x 100 mm) at the top centre with the two TO-247-4 standing against its lower face at 28 mm pitch, the eight
barrier parts on the line y = 145 with their HV pins toward the device row, the HF ceramics beside the device legs
over the VIN+/PGND pour pair, films and the inductor in the fan stream, the input terminals at the left and the
output at the right.

Stage-3 corrections merged from verification/stage3_power_patch (zones-only DRC experiment at the structural floor):
chain parts on the pin-field pitch with courtyard-contained stubs, DAMP_MID bypass along the board edge, LED feeds,
terminals re-pitched for the REDCUBE pin-field gap, VIN In2 backbone clear of the VOUT In2 bar, HV ladders in one row
with via feeds, HV via rings and HV pads reserved for the auto-placer, VOUT_L without vias, PGND right strip stitched.

Only the kicad-cli DRC report counts as verification; the router report and the placement checks are geometric
proposals. Nothing is waived: findings are reported with their manifest paths.

Run (re-executes itself under KiCad's bundled Python when pcbnew is not importable):
    python -m automation.kicad_tools.generate_sic_power_board [--no-route] [--no-drc] [--no-metrics] [--trials N] [--ripup N]
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

ROOT = Path(os.environ['AIPE_ROOT']) if os.environ.get('AIPE_ROOT') else Path(__file__).resolve().parents[2]  # AIPE_ROOT: run a copy of this module
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.kicad_tools import grid_router as gr  # noqa: E402
from automation.kicad_tools import sic_buck_common as common  # noqa: E402
from automation.setup.detect_kicad import find_kicad_cli, read_config  # noqa: E402

EXAMPLE = ROOT / 'examples/sic-buck-400v-200v-5kw'
KICAD_DIR = EXAMPLE / 'kicad/power_board'
DESIGN_DIR = EXAMPLE / 'design'
VERIFICATION_DIR = EXAMPLE / 'verification'
MODEL_JSON = DESIGN_DIR / 'circuit_power.json'
MAPPING_JSON = DESIGN_DIR / 'schematic_mapping_power.json'
SPEC_JSON = VERIFICATION_DIR / 'engineering_checks/layout_spec_power.json'
CHECKS_DIR = VERIFICATION_DIR / 'engineering_checks'
DRC_DIR = VERIFICATION_DIR / 'drc'
NAME = 'AIPE_SiC_Buck_Power'
TITLE = 'AIPE SiC buck 400 V -> 200 V / 5 kW - power board (SiC half bridge, drivers, isolators, SELV strip)'
BANNER = common.BANNER  # generation label shared with the schematics, the models and the evidence writers
REVISION = common.GENERATION
WIDTH, HEIGHT = 240.0, 180.0
COPPER_LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
ROUTING_LAYERS = ['F.Cu', 'In2.Cu', 'B.Cu']  # In2.Cu only inside the driver islands (zone keep-outs elsewhere); In1.Cu is never routed
STACKUP = [('F.Cu', 'copper', 0.07), ('dielectric 1', 'prepreg', 0.2), ('In1.Cu', 'copper', 0.07),
           ('dielectric 2', 'core', 1.32), ('In2.Cu', 'copper', 0.07), ('dielectric 3', 'prepreg', 0.2), ('B.Cu', 'copper', 0.07)]
GRID, TRACE, CLEARANCE, HOLE_CLEARANCE = 0.125, 0.25, 0.3, 0.25  # project Default class 0.25 / 0.25; the router keeps 0.3 (grid rounding margin)
VIA = (0.6, 0.3)  # signal vias (project minimum); HV transitions use HV_VIA groups
HV_VIA = (1.2, 0.6)
BOARD_MARGIN = 1.2  # copper to board edge (HV rule 1.0 mm)
EDGE_COURTYARD = 0.4
ZONE_CLEARANCE, ZONE_MIN_THICKNESS = 0.3, 0.3  # the .kicad_dru class rules (3.0 / 1.0 / 9.0 / 5.0 mm) override the zone clearance where larger
MAX_NODES = 1500000  # A* expansions per connection: the long SELV-strip nets need more than the islands
PLACE_STEP = 0.5
BARRIER_Y = 145.0  # barrier-part centres; ISO_BARRIER strip 140-150
ISO_STRIP = (140.0, 150.0)
HV_LIMIT_Y = 139.9  # HV copper stays above this line (9.0 mm + to the SELV strip copper at y >= 151)
SELV_START_Y = 151.0
HV_COPPER_MAX_Y = 139.1  # routed copper (via edges included) outside the barrier courtyards: 9 mm below the SELV pad rows (top edge 149.05)
SELV_COPPER_MIN_Y = 150.9  # and 9 mm above the HV pad rows (bottom edge 140.95); inside the courtyards the pin-field rules apply
SELV_FAN_Y = 156.5  # SELV-strip auto-placed parts start here under the barrier parts: fan-out corridor for the barrier SELV escapes
SELV_SOCKET_PARTS_Y = 166.0  # parts under the mezzanine socket start here: below the two rows of socket escape vias (y 162.05 / 163.3) and a 2 mm bus band
SOCKET_LANE_END_Y = 165.5  # the socket ports' reserved B.Cu exit lanes run from the stub-end vias to here (no foreign B.Cu track may cross them)
BARRIER_SELV_LANE_MM = 2.0  # the barrier SELV-row ports (stub-end vias and fan vias) keep an F.Cu exit lane this long into the corridor
DIRECT_LANE_MM = 0.75  # reserved exit corridor of every direct (pad-centre) port: foreign tracks may not hug a pad and seal it
SELV_PARTS_MAX_Y = 176.0  # SELV-strip parts end here: y 176-179.5 is a parts-free band for the long east-west buses (b5: the strip was cut at x 176 on all layers by U8's network column; 12V_PROT and BIAS_EN could not cross it)
ISLAND_WALL_X = (114.4, 118.6)  # no routing between the SW-referenced and PGND-referenced islands (3 mm functional clearance incl. track widths)
ISLAND_TOP_Y = 127.6  # island copper (B.Cu / In2.Cu) starts here: 3 mm below the HF row A PGND via rings (edge y 124.0)
NOTCH_INSET = 0.25  # routed copper (0.25 mm tracks, grid-snapped) keeps this far inside the ISO_BARRIER rule-area notches around the pad rows; the outermost pads' centre cells stay free
SKIP_ESCAPE_NETS = ('VIN', 'VIN_RAW', 'SW', 'VOUT', 'VOUT_L', 'PE', 'PE_REF_MID', 'SNUB_MID', 'DAMP_MID', 'BLD_IN_1', 'BLD_IN_2', 'IND_IN_1',
                    'IND_IN_2', 'IND_IN_3', 'BLD_OUT_1', 'IND_OUT_1', 'IND_OUT_2', 'VIN_DIV_T1', 'VIN_DIV_T2', 'VIN_DIV_T3', 'VOUT_DIV_T1')
SINK_CENTRE = (100.35, 67.0)  # r20 (LR-25): 1.1 mm east of the r19 position so the input films C11 / C12 keep >= 20 mm courtyard distance (CR-23)
SINK_KEEPOUT_MM = 5.1  # HV copper keep-out around the heatsink courtyard on the outer layers (KR-TH-002 >= 5.0 mm plus 0.1 mm fill-polygon margin)
HS1_HOLE_OFFSETS = ((-45.0, -45.0), (-45.0, 45.0), (45.0, -45.0), (45.0, 45.0))  # the LAM 5 D K footprint's four 3.2 mm NPTH mounting holes about the sink centre
HS1_HOLE_D = 3.2  # r20 (LR-21): all-layer HV keep-out (pours, vias) >= 5 mm around the hole walls of the PE-bonded sink; PE tracks (sink potential) may pass
L1_CENTRE = (204.5, 95.0)
L1_HOLE_PITCH = 30.0
L1_ANNULUS_R = 6.15  # 4.3 mm NPTH + 4 mm copper-free (8 mm annulus of the inductor record)
M4_KEEPOUT_R = 8.5  # ~17 mm PE keep-out circle around each baseplate standoff in the HV area (pcb_stackup.md section 9)
M4_KEEPOUT_R_SELV = 5.5  # SELV-strip standoffs: washer / head envelope plus 1 mm (no HV copper there; CTRL_SELV has no PE rule)
PE_SPINE_X = 59.5  # PE spine on B.Cu: >= 5 mm east of the link resistors' MID pads (x <= 49.7), 1.55 mm east of the heatsink NPTH hole wall (hole 55.35, r 1.6; r20)
HV_ZONE_NETS = ('VIN', 'VIN_RAW', 'PGND', 'SW', 'VOUT', 'VOUT_L')
KELVIN_NETS = ('KS_H', 'KS_L')
SELV_ZONE_NETS = ('GND_CTRL', '3V3')  # In1.Cu pour / In2.Cu post-route pour under the SELV strip; 3V3 (tracks + pour) and 12V_PROT (11 pins) are routed
HV_CLASS_NETS = ('VIN', 'VIN_RAW', 'VIN_PRE', 'SW', 'PGND', 'VOUT', 'VOUT_L', 'SNUB_MID', 'DAMP_MID', 'PE_REF_MID',
                 'BLD_IN_1', 'BLD_IN_2', 'IND_IN_1', 'IND_IN_2', 'IND_IN_3', 'BLD_OUT_1', 'IND_OUT_1', 'IND_OUT_2',
                 'VIN_DIV_T1', 'VIN_DIV_T2', 'VIN_DIV_T3', 'VOUT_DIV_T1')
# island net groups: each group routes only inside its island footprint (routing regions below)
HS_NETS = ('G_H', 'KS_H', 'VDD_H', 'VEE_H', 'HS_OUTH', 'HS_OUTL', 'HS_CLMP', 'HS_GK', 'HS_RLIM', 'HS_FB_VDD', 'HS_FB_VEE', 'DESAT_H_A', 'DESAT_H_OC')
LS_NETS = ('G_L', 'KS_L', 'VDD_L', 'VEE_L', 'LS_OUTH', 'LS_OUTL', 'LS_CLMP', 'LS_GK', 'LS_RLIM', 'LS_FB_VDD', 'LS_FB_VEE', 'DESAT_L_A', 'DESAT_L_OC')
SENSE_NETS = ('ISO_15V', 'ISO_RLIM', 'ISO_FB_VDD', 'ISO_FB_VEE', '5V_ISO', 'VIN_DIV', 'VOUT_DIV')
LS_GATE_LOOP_NETS = ()  # r20 (LR-24) attempt, NOT kept: ('G_L', 'LS_OUTH', 'LS_OUTL', 'LS_CLMP') restricted to B.Cu failed at once (r20c) - the U3 stub-end ports are F.Cu stubs and a single-layer region allows no via
AMC_PAIR_NETS = ()  # r20 (LR-26) attempt, NOT kept: ('VIN_OUTP', 'VIN_OUTN', 'VOUT_OUTP', 'VOUT_OUTN') restricted to F.Cu left VIN_OUTP / VOUT_OUTN open and sealed RDY_L / 3V3 in the strip (r20c)
# routed-net rules (mm): the gate nets as 0.35 mm tracks; the driver rails, the Kelvin and the driver output nets at the default
# 0.25 mm - a 0.35 mm track (one grid cell of dilation) passes only the 1.4 mm island channels while 0.25 mm passes the 0.9 mm
# ones too (stage-4 diagnosis: every persistent island failure was a 0.35 mm net sealed inside a packed region); the gate pours on
# B.Cu and the Kelvin pours on In2.Cu add the copper that carries the loop currents (KR-PCB-001); DESAT / SENSE / SELV 0.25
NET_RULES = {'G_H': dict(width=0.35, clearance=0.3, fanout_width=0.25), 'G_L': dict(width=0.35, clearance=0.3, fanout_width=0.25),
             'HS_OUTH': dict(width=0.25, clearance=0.3), 'HS_OUTL': dict(width=0.25, clearance=0.3),
             'LS_OUTH': dict(width=0.25, clearance=0.3), 'LS_OUTL': dict(width=0.25, clearance=0.3),
             'HS_CLMP': dict(width=0.25, clearance=0.3), 'LS_CLMP': dict(width=0.25, clearance=0.3),
             'KS_H': dict(width=0.25, clearance=0.3), 'KS_L': dict(width=0.25, clearance=0.3),
             'VDD_H': dict(width=0.25, clearance=0.3), 'VEE_H': dict(width=0.25, clearance=0.3),
             'VDD_L': dict(width=0.25, clearance=0.3), 'VEE_L': dict(width=0.25, clearance=0.3),
             'ISO_15V': dict(width=0.25, clearance=0.3), '5V_ISO': dict(width=0.25, clearance=0.3),
             'PE': dict(width=2.0, clearance=5.3),  # 5.0 mm rule plus grid rounding of the 2.0 mm track
             'PGND': dict(clearance=0.3),
             '12V_PROT': dict(width=0.35, fanout_width=0.25),  # <= 1.5 A; a wider track's halo cannot reach the choke pads (1 mm from their GND pad)
             '3V3': dict(width=0.25, clearance=0.3),  # routed on the three strip layers as stitching; its In2 pour (post-route zone) is the distribution copper
             # bias-module primaries (<= 0.6 A): default width - their ports are exact stubs in the 0.65 mm SELV rows, which a wider
             # track's clearance halo would seal
             '12V_BIAS_H': dict(width=0.25), '12V_BIAS_L': dict(width=0.25), '12V_BIAS_S': dict(width=0.25),
             'GNDP_H': dict(width=0.25), 'GNDP_L': dict(width=0.25), 'GNDP_S': dict(width=0.25),
             'K1_LOW': dict(width=0.35, fanout_width=0.25)}
for _net in ('DESAT_H_A', 'DESAT_H_OC', 'DESAT_L_A', 'DESAT_L_OC', 'VIN_DIV', 'VOUT_DIV', 'ISO_RLIM', 'ISO_FB_VDD', 'ISO_FB_VEE',
             'HS_RLIM', 'HS_FB_VDD', 'HS_FB_VEE', 'LS_RLIM', 'LS_FB_VDD', 'LS_FB_VEE', 'HS_GK', 'LS_GK'):
    NET_RULES.setdefault(_net, dict(width=0.25, clearance=0.3))  # default width: these nets leave 0.65 mm pad rows through exact stubs
# VIN / VOUT potentials and their divider, bleeder and damping chains are never routed; every routed net (SW-, PGND-referenced
# or SELV) must keep the 3 mm outer-layer functional clearance from their pads, vias and chain tracks, so their router halo is 3 mm.
for _net in ('VIN', 'VIN_RAW', 'VOUT', 'VOUT_L', 'VIN_DIV_T1', 'VIN_DIV_T2', 'VIN_DIV_T3', 'VOUT_DIV_T1', 'BLD_IN_1', 'BLD_IN_2',
             'IND_IN_1', 'IND_IN_2', 'IND_IN_3', 'BLD_OUT_1', 'IND_OUT_1', 'IND_OUT_2', 'DAMP_MID', 'SNUB_MID'):
    NET_RULES.setdefault(_net, {})['clearance'] = 3.0
# Kelvin nets first (17 ports each, they need the straight paths), then the gate loops and the island rails (0.35 mm: they need the
# channels before the 0.25 mm feedback nets fill them), the island small nets, the
# sensing island, then the SELV strip (long nets last); the order trials permute this
SIGNAL_ORDER = ['KS_H', 'KS_L', 'G_H', 'G_L', 'VDD_', 'VEE_', 'ISO_15V', '5V_ISO', 'HS_OUTH', 'HS_OUTL', 'LS_OUTH', 'LS_OUTL', 'HS_CLMP', 'LS_CLMP',
                'HS_GK', 'LS_GK', 'DESAT_', 'HS_', 'LS_', 'ISO_', 'VIN_DIV', 'VOUT_DIV',
                '3V3', '12V_BIAS', 'GNDP_', 'PG_BIAS', 'BIAS_EN', 'PWM_', 'RESET_N', 'FLT_', 'RDY_', 'OC_N', 'ISENSE', 'VOC_SET', 'REF2V5_PB',
                'VIN_OUT', 'VOUT_OUT', 'VIN_AMP', 'VOUT_AMP', 'VIN_SENSE', 'VOUT_SENSE', 'FAN_TACH', 'FAULT_N', 'SPARE_',
                'RELAY_ON', 'RLY_G', 'K1_LOW', '12V_PROT']
SIGNAL_ORDER_TRIALS = 4  # plan order, short nets first, long nets first, then a seeded perturbation of the best - the best is kept
SIGNAL_PINNED = ['KS_H', 'KS_L', 'G_H', 'G_L', 'VDD_H', 'VEE_H', 'VDD_L', 'VEE_L', 'ISO_15V', '5V_ISO']  # routed first in every order trial: the Kelvin and gate nets and the island rails (0.35 mm) - the nets whose pads the 0.25 mm feedback nets would otherwise seal inside the packed regions
RIPUP_ROUNDS = 30  # grid_router rip-up negotiation after the best order trial (stage 5: direct routing of connections that became free, lane release; 7 of 20 rounds kept in b5)
ROUTING_STYLE_V21 = dict(diagonal=True, bend_penalty_cells=[0.6, 2.0], simplify='octilinear', arcs=True, straight_nets=['PE'])  # V2.1 grid_router
# geometry (plan key 'style'): 8-direction A* with bend penalties, final octilinear simplification and tangent arcs on the signal nets (zone/power
# nets and tracks above 0.6 mm: diagonals only). eps stays at the V2 0.01: on this 0.125 mm grid a diagonal step between free cells can intrude
# at most 0.0039 / R mm into a round halo of radius R (<= 0.007 mm for the smallest 0.56 mm signal halos), below eps, and the router's 0.3 mm
# clearance already exceeds the 0.25 mm Default class; eps 0.02 (the control board's 0.125 mm / 0.2 mm setting) changed the V2 search itself
# (attempt B, 2026-10-12: KS_L 88 -> 131 mm, FLT_H_N +3 vias), so the search stays byte-identical to V2 and only the final geometry differs.
ROUTING_STYLE_OCTILINEAR = dict(diagonal=False, simplify='octilinear', arcs=True, straight_nets=['PE'])  # V2.1 fallback geometry: the V2
# 4-direction search (same algorithm, order trials and rip-up rounds, same routes as the frozen V2 board), then the final octilinear
# simplification (string pulling, short-run collapse, on-grid chamfers) and tangent arcs on the signal nets - the control board's
# ROUTING_STYLE without its eps 0.02 (see above) plus the untouched PE spine.
ROUTING_STYLE = ROUTING_STYLE_OCTILINEAR  # V2.1 default (build_power(style=None) / --style default). Chosen 2026-10-12 after three attempts on the
# full board (verification/routing_iterations_power.md section 16): the 8-direction block (--style v21) routed in 1605 s (3.8 x V2), left
# LS_FB_VDD and VDD_L unresolved (DRC 1 + 2) and lengthened 10 nets (3V3 +88 mm, RDY_L +35 mm / +9 vias, DESAT_H_A +2 vias), while this block
# keeps the V2 search (same routes, 606 vias, no net longer) and only rewrites the final geometry: bends_90 3609 -> 1121, 145 tangent arcs,
# stair runs 382 -> 124, DRC 0 / 0 / 0. build_power(style={}) / --style none routes the V2 geometry.
FINE_PITCH_MM = 1.0  # pad rows below this pitch escape with exact straight stubs (no via at the row) and 0.25 mm escapes
BARRIER_ROW_PITCH_MM = 1.5  # barrier packages: the 1.27 mm rows (SOIC-16W / SOIC-8W / TMCS) escape through exact stubs too - a port at the pad end is sealed by the first track that runs along the row
STUB_ROW_REFS = ()  # (r14: short stubs on the strip SOIC-8 rows were sealed by their row neighbours' escapes; U8 / U9 escape inward instead, INWARD_REFS)
INWARD_REFS = ()  # (r15: U8 is a 0.65 mm VSSOP and U9 a SOT-23 - their exact stubs went inward under the body and sealed each other; outward stubs with the 1.2 mm courtyard gaps instead)
EXACT_STUB_HV_MM = (0.6, 0.8)  # HV-side stub length beyond the pad end, alternating along the row so the grid-snap jogs never face each other (ends >= 0.4 mm above the island parts and the sense_b vias)
EXACT_STUB_SELV_MM = (1.0, 1.9)  # SELV side: the stubs end inside the fan-out corridor above the SELV parts (SELV_FAN_Y)
EXACT_STUB_HV_BY_REF = {'U6': (0.3, 0.3), 'U7': (0.3, 0.3)}  # AMC1311 HV rows: the stub-end via sits just beyond the pad end (ring 138.05-138.65), below the sensing-row parts (courtyards <= 137.75)
BAR_VIA_DEPTH_MM = 0.7  # bar-joined same-net runs escape through one 0.6/0.3 via this far beyond the pad ends
BAR_VIA_DEPTH_BY_REF = {'U6': 0.3, 'U7': 0.3}  # same reason as EXACT_STUB_HV_BY_REF (the PGND pair of the AMC1311 HV row)
# 1.27 mm rows (SOIC-16W / SOIC-8W / TMCS1133 DVG, mezzanine socket stubs) get a 0.6/0.3 via at every stub end: at that pitch two vias and a
# track fit side by side (ring gap 0.67 mm, 0.845 mm to the neighbouring stub), so every port lives on all three routing layers and a
# track running along the stub-end line on one layer no longer seals it. 0.65 mm rows cannot host vias in line; their single pads
# between the bars escape through a deterministic fan: the outer pads of a group of singles run a leg sideways at FAN_DEPTH_MM
# (beyond the bar vias' shadow) and the inner ones continue straight to FAN_DEPTH_MM + FAN_LEG_MM, every pad ending in its own via
FAN_DEPTH_MM = 1.75  # first fan depth beyond the pad end: 1.05 mm past the bar vias (BAR_VIA_DEPTH_MM) -> >= 0.9 mm centre distance to them
FAN_DEPTH_STRIP_MM = 1.0  # strip parts without bars (the VSSOP U8)
FAN_LEG_MM = 1.3  # sideways leg of the outer singles and the depth step of the two inner pads of a group of four (via-to-via >= 1.45 mm, via-to-track >= 0.9 mm)
FAN_STEP_MM = 0.9  # depth step of the middle pad of a group of three (its via sits 1.11 mm from the outer pads' stub ends)
# courtyard gaps (mm) for the auto-placer: (along the pad axis, across) for 2-pad parts, per kind otherwise
GAP_AXIS, GAP_LATERAL, GAP_TP, GAP_IC, GAP_CONNECTOR, GAP_HV = 0.8, 0.9, 0.5, 1.6, 0.8, 3.3  # axis gap + courtyard insets host a 0.6 mm via, the lateral gap a 0.3 mm track channel
REGION_GAPS = {'selv_left': (1.4, 0.9), 'selv_hs': (1.4, 0.9), 'selv_ls': (1.4, 0.9), 'selv_sense': (1.4, 0.9), 'selv_east': (1.4, 0.9), 'selv_decouple': (0.8, 0.5),
               'sense_b': (0.8, 0.9),  # one row of 0603s under the ladders
               'hs_bias': (0.8, 2.6), 'hs_bias_f': (0.8, 0.9), 'hs_gate': (0.8, 1.75), 'ls_gate': (0.8, 1.75),
               'ls_desat': (0.8, 1.1)}  # ls_desat: 1.1 mm channels hold two 0.25 mm tracks (pad to pad 1.56 mm; the 0.9 mm default holds one) (b8: VDD_L C56.1 -> C58.1 lost the single-track channel to VEE_L)  # hs_bias: 2.6 mm channels (three 0.25 mm tracks) between its two rows  # two 0.25 mm tracks per channel between the parts of a row; the LS bias, DESAT and U5 bias regions keep the default 0.9 mm channels (one 0.25 mm track each: ten parts leave no room for more)
NARROW_REGIONS = frozenset()  # single-row regions whose parts stand upright (none: the 2 mm sensing row holds horizontal 0603s only)
REF_GAPS = {'D5': (0.5, 0.5), 'D3': (0.5, 0.5), 'L1': (0.5, 0.5),  # DESAT diodes: only their drain pad carries the 3 mm rule (kept by the island regions); L1: circular courtyard
            'U8': (1.0, 1.0), 'U9': (1.2, 1.2),
            'R42': (0.8, 0.9)}  # the upright 1206 at the east end of ls_desat keeps the default gaps: with the region's 1.1 mm channel gap it no longer fits before the fixed U5 bias row (x 157.2)  # U8 (0.65 mm VSSOP): its fan copper and vias become placer obstacles once it is placed (FAN_OBSTACLE_REFS); U9 (SOT-23) keeps the via fanout
FAN_OBSTACLE_REFS = ('U8',)  # auto-placed fine-pitch parts whose escape fan is registered as placer obstacles right after they are placed
PLACE_QUANT = 3.0  # mm: anchor-distance quantum within which the packer prefers the top-left position
PACK_REGIONS = frozenset(('hs_gate', 'hs_bias', 'hs_bias_f', 'hs_desat', 'ls_gate', 'ls_desat', 'ls_bias', 'u5_bias'))  # shelf-packed regions (the SELV regions and the sensing row place by anchor distance)
HV_VIA_RING_GAP = 3.0  # outer-layer HV functional clearance kept between HV via rings / HV pads and auto-placed island parts
CHAIN_TRACK_INSET = 0.15  # chain stubs start and end this far inside the pad edges

# ---------------------------------------------------------------------------------------------------------------------
SENSE_FILTER_Y = 136.0  # centre line of the upright AMC1311 filter parts (courtyard 134.52-137.48: two B.Cu lanes above, the HV stub-end vias below)
# UCC14141 secondary networks (HS bias U2, sensing bias U5) as two rows of upright parts on B.Cu: row A's lower pads (y 135.4) are the
# FB_VDD / FB_VEE / RLIM nodes, each directly above its fan via (y 136.45 / 137.35) - straight 1-2 mm connections instead of the meanders
# that sealed the shelf-packed rows in r16 / b2; the rails (VEE, COM, PGND, ISO_15V, 5V_ISO) sit on the upper pads (y 133.8) and in row B,
# with a 0.775 mm lane between the rows. Angle 'pad1_down' / None (pad 2 down) is resolved from the pad order at placement time.
BIAS_ROW_A_Y, BIAS_ROW_B_Y = 134.6, 130.5
GATE_ROW_B_Y = 130.6  # second row of the HS gate network: 0603 courtyards 129.1-132.1, clear of Q1's standing TO-247 courtyard (y <= 129.0) and of row A's 1206s (y >= 132.26)
# Floorplan: fixed poses (x, y, angle[, side]) - angles chosen so that barrier parts have their HV pins toward the device row
# (pcbnew rotation: 90 deg maps local (x, y) -> (y, -x); 270 deg maps (x, y) -> (-y, x); a flipped part mirrors x first).
# Barrier line west -> east: U2 (HS bias), U1 (HS driver), U3 (LS driver), U4 (LS bias), U5 (sense bias), U6, U7 (AMC1311), U10
# (TMCS1133); the slot footprints' courtyards (18.5 / 17.8 / 12.0 / 16.5 mm along x) sit 0.5 mm apart.
# ---------------------------------------------------------------------------------------------------------------------
FIXED = {
    # mechanical
    'HS1': (SINK_CENTRE[0], SINK_CENTRE[1], 0), 'H1': (43.8, 27.5, 0),
    'H2': (6.0, 6.0, 0), 'H3': (140.0, 6.0, 0), 'H4': (235.0, 52.0, 0), 'H5': (6.0, 174.0, 0), 'H6': (120.0, 174.0, 0), 'H7': (234.0, 174.0, 0),
    'H8': (235.0, 158.0, 0), 'H9': (123.0, 158.0, 0), 'H10': (60.0, 170.0, 0), 'H11': (90.0, 170.0, 0),
    # half bridge (pad 1 = drain at the footprint origin, pads along +x) and the inductor (pad 1 = SW at the left)
    'Q1': (87.0, 126.0, 0), 'Q2': (115.0, 126.0, 0), 'L1': (204.5, 95.0, 0),
    # HF ceramics: row A beside Q1's drain with the PGND pads toward the sink (their 1.2 mm in-pad vias end 0.15 mm outside the
    # heatsink keep-out and 3 mm above the islands; the VIN pads end at y 129.35 so the VIN+ band can stop at y 129.6), row B below
    'C1': (79.0, 125.9, 90), 'C2': (72.8, 125.9, 90), 'C3': (66.6, 125.9, 90), 'C4': (60.4, 125.9, 90), 'C5': (54.2, 125.9, 90),
    'C6': (48.0, 125.9, 90), 'C7': (60.4, 136.5, 90), 'C8': (54.2, 136.5, 90), 'C9': (48.0, 136.5, 90), 'C10': (41.8, 136.5, 90),
    # films: input left column (rotated, VIN pads at the bottom), output top right (VOUT pads at the bottom)
    'C11': (14.95, 33.0, 90), 'C12': (14.95, 77.0, 90), 'C13': (186.8, 23.5, 90), 'C14': (218.8, 23.5, 90),  # C13 / C14 follow the sink shift (r20): >= 20 mm courtyard distance kept
    # terminals (REDCUBE pin-field gap: 13.5 mm pitch between the two input rows), precharge PTC, MOV.
    # r20 (LR-23): the corner pocket (J1 above, barrier below, 3.9 mm In1 / In2 passage east of it) can only hold a terminal whose
    # current never has to leave it: the relay input terminal J5 (VIN_RAW) now sits under J1 (VIN_RAW) - same net, joined by the
    # VIN_RAW pours over the two pin fields. The input return J2 (PGND) takes the open east position of the UPPER row, where the In1
    # return plane and the B.Cu PGND column reach it over their full width; the relay output terminal J6 (VIN) keeps the east position
    # of the lower row inside the VIN+ F.Cu band. The precharge PTC RT1 stays; its VIN_RAW pad is fed by a 2 mm B.Cu track from the
    # J1 / J5 pour (rt1_vin_raw_feed) that passes north of J2's pin field.
    # r20 (LR-25): the MOV RV1 (23 mm tall) leaves the fan-intake corridor west of the sink for the exhaust side east of J4 (VIN pin
    # into the In2 backbone, PGND pin into In1 / the B.Cu output block); RT1 (22 mm, PTC) stays: its VIN_RAW / VIN pads bridge the two
    # pours and no corridor-free position reaches both.
    'J1': (7.5, 112.0, 0), 'J5': (7.5, 129.0, 0), 'J2': (23.0, 112.0, 0), 'J6': (23.0, 129.0, 0), 'RT1': (35.5, 120.5, 270), 'RV1': (165.0, 88.5, 90),
    'J3': (162.2, 50.0, 0), 'J4': (162.2, 65.5, 0),  # r20: 1.2 mm east with the sink (pads stay >= 5 mm from the sink courtyard)
    # top band, west -> east on the courtyard pitch (same-net pads of neighbouring parts ~0.6 mm apart joined by stubs inside the
    # two courtyards where the .kicad_dru pin-field exceptions apply): bleeder R1-R3 (2512) ending in PGND, the indicator chain
    # reversed so that the LED D1's PGND pad abuts R3's PGND pad (via in the 2512) and R4's VIN pad lies in the VIN+ pour, then
    # the damping legs C16/R12 | R13/C17 (DAMP_MID bypass along the board edge)
    'R1': (47.0, 6.5, 0), 'R2': (54.8, 6.5, 0), 'R3': (62.6, 6.5, 0), 'D1': (68.8, 6.5, 0), 'R6': (73.4, 6.5, 180), 'R5': (78.1, 6.5, 180), 'R4': (82.8, 6.5, 180),
    'C16': (88.9, 6.5, 0), 'R12': (96.6, 6.5, 0), 'R13': (104.4, 6.5, 180), 'C17': (112.1, 6.5, 180),
    # PE group west of the heatsink base: the M4 stud pad (r 4.3) between the two Y2 capacitors (pad 1 VIN / PGND at the footprint
    # origin, PE pad 10 mm east), whose PE pads reach the stud by short B.Cu stubs; the link resistors sit on B.Cu with their
    # PGND pads just inside the PGND B.Cu column (x <= 43.4) and the MID / PE pads east of it (R15 PGND|MID, R16 MID|PE standing
    # vertically, R14 PGND|PE); the PE spine (B.Cu, x 58) joins R14 / R16 to the stud 5 mm from every HV_PGND / VIN item
    'C18': (32.5, 19.0, 0), 'C19': (32.5, 36.0, 0), 'R15': (45.65, 45.0, 0, 'B'), 'R16': (48.9, 53.0, 270, 'B'), 'R14': (45.65, 64.0, 0, 'B'),
    # barrier line (HV pins up): UCC14141 at 90, UCC21710 / AMC1311 / TMCS1133 at 270
    'U2': (77.5, BARRIER_Y, 90), 'U1': (96.25, BARRIER_Y, 270), 'U3': (124.0, BARRIER_Y, 270), 'U4': (142.75, BARRIER_Y, 90),
    'U5': (163.0, BARRIER_Y, 90), 'U6': (181.0, BARRIER_Y, 270), 'U7': (195.0, BARRIER_Y, 270), 'U10': (212.0, BARRIER_Y, 270),
    # DESAT diodes beside the drains (D3 on F.Cu with its VIN pad in the VIN+ band and the DESAT pad away from the Q1 drain pin,
    # D5 on B.Cu - angle 0: the mirrored SW pad faces Q2 pin 1 and is fed by a B.Cu track from that pin); the DNP snubber on F.Cu
    # east of Q2's pins above the LS island (R11 SW pad -> In2 strip via, C15 PGND pad -> In1 via; 3 mm from every other group)
    'D3': (84.5, 133.5, 270), 'D5': (121.0, 132.5, 0, 'B'), 'R11': (146.5, 125.0, 0), 'C15': (154.0, 125.0, 0),
    # V_GS probe loops (through-hole) upright beside the TO-247 courtyards of Q1 / Q2 (CR-11), below the silkscreen band and clear of the SW via group
    'TP1': (102.0, 126.0, 90, 'B'), 'TP2': (130.0, 126.0, 90, 'B'),  # pin 1 at the origin: the loop spans y 122.2 - 127.3
    # output bleeder / indicator column beside J3: bleeder R7/R8 ending in PGND, the indicator chain reversed so that the LED D2's
    # PGND pad abuts R8's PGND pad (via in the 2512); VOUT from the In2 column tab (R7 in-pad via, R9 via + 3 mm stub)
    'R7': (163.5, 5.0, 270), 'R8': (163.5, 12.8, 270), 'D2': (163.5, 19.0, 270), 'R10': (163.5, 23.6, 90), 'R9': (163.5, 28.3, 90),
    # HV sense ladders on F.Cu in one row at y 132 above the AMC1311s (1206 on the 4.7 mm pin-field pitch, just outside the
    # inductor keep-out circle and below the L1 standoff rule area; VIN / VOUT fed by vias 3 mm beyond the end pads with short
    # stubs); the AMC1311 filters stand upright on B.Cu in one row 3 mm below the ladder pads, the U5 periphery west of the feed via
    'R59': (174.0, 132.0, 0), 'R60': (178.7, 132.0, 0), 'R61': (183.4, 132.0, 0), 'R62': (188.1, 132.0, 0), 'R65': (194.5, 132.0, 180), 'R64': (199.2, 132.0, 180),
    # mezzanine socket (pin 1 at the right end) and SELV-strip connectors
    'J7': (211.0, 160.0, 270), 'J9': (18.0, 172.0, 0), 'J8': (36.0, 173.0, 90),
    # AMC1311 input filters (R / C / C to PGND): upright 0603s on B.Cu in the band between the ladder taps and the AMC HV rows, the
    # PGND pad downwards (angle None: resolved at placement time from the pad order) so its in-pad via keeps 3 mm from the ladder pads
    # (ring top 136.475 vs pad edge 132.8); the VIN_DIV group under U6, the VOUT_DIV group beside the VOUT tap (the taps end in vias,
    # so both nets stay on B.Cu); 2.5 mm pitch leaves 1 mm gaps for the B.Cu tracks between the parts
    # HS gate network on B.Cu: the three gate resistors stand upright directly above their driver pins' stub vias (U1.6 HS_OUTL (94.375, 138.75),
    # U1.4 HS_OUTH (96.875, 138.75), U1.7 HS_CLMP (93.125, 138.5)) with the pin-side pad down and the G_H pad up; the pull-down R22, the
    # Kelvin-gate RC R23 / C21 in the row above, 3 mm below Q1's pins; the G_H pour (B.Cu, post-route) covers the rows. The shelf-packed
    # layout boxed R20.1 / R23.1 behind G_H and KS_H tracks (b5: 808 / 255 cells)
    'R21': (92.0, BIAS_ROW_A_Y, 'pad1_down', 'B'), 'R20': (94.6, BIAS_ROW_A_Y, 'pad1_down', 'B'), 'R19': (97.2, BIAS_ROW_A_Y, 'pad1_down', 'B'),
    'R22': (99.8, BIAS_ROW_A_Y, None, 'B'),  # pull-down: G_H pad up with the other G_H pads, KS_H down
    'R23': (94.6, GATE_ROW_B_Y, 'pad1_down', 'B'), 'C21': (97.2, GATE_ROW_B_Y, None, 'B'),  # HS_GK pads up, side by side
    # OPA2320 (0.65 mm VSSOP) under the socket's west third with its 0805 3V3 decoupling beside the 3V3 fan via (pad 8 -> (169.4, 167.7))
    'U8': (165.5, 170.0, 0), 'C88': (171.0, 166.3, 0),
    'TP12': (176.0, 154.0, 0),  # SPARE_D1 test point in the fan-out corridor between U5's and U6's escapes: SPARE_D1 (J7.36, north stub) stays local
    # HS bias network (U2 fan vias: HS_FB_VDD (71.975, 137.35), HS_FB_VEE (73.925, 136.45), HS_RLIM (75.875, 137.35); VEE_H bar vias at
    # x 72.3 / 75.55 / 80.425, VDD_H at 76.85, all at y 138.4): row A C34 R30 | R32 C35 R31 | R33 with the FB / RLIM pads down, row B the
    # VDD_H divider resistor (FB_VDD down, two columns west of C34) and the KS_H-VEE_H output capacitor (VEE_H down, over the VEE_H bus)
    'C34': (70.0, BIAS_ROW_A_Y, 'pad1_down', 'B'), 'R30': (72.0, BIAS_ROW_A_Y, 'pad1_down', 'B'), 'R32': (74.0, BIAS_ROW_A_Y, 'pad1_down', 'B'),
    'C35': (76.0, BIAS_ROW_A_Y, 'pad1_down', 'B'), 'R31': (78.0, BIAS_ROW_A_Y, None, 'B'), 'R33': (80.0, BIAS_ROW_A_Y, 'pad1_down', 'B'),
    'R29': (68.0, BIAS_ROW_B_Y, None, 'B'), 'C25': (75.0, BIAS_ROW_B_Y, None, 'B'),
    # sensing bias network (U5 fan vias: ISO_FB_VDD (157.475, 137.35), ISO_FB_VEE (159.425, 136.45), ISO_RLIM (161.375, 137.35); PGND bar
    # vias at x 157.8 / 161.05 / 165.925, ISO_15V at 162.35): row A R54 | R56 C65 | R57 (0805) at 2.5 mm pitch (a track passes between any two
    # columns), row B the upper divider resistors R53 / R55 and the FB_VDD capacitor over the inter-column gaps, the rail capacitors east;
    # every part with a PGND pad (in-pad via, F.Cu annulus) stays east of x 157 so the F.Cu ls_desat row keeps its room
    'R54': (158.0, BIAS_ROW_A_Y, 'pad1_down', 'B'), 'R56': (160.5, BIAS_ROW_A_Y, 'pad1_down', 'B'), 'C65': (163.0, BIAS_ROW_A_Y, 'pad1_down', 'B'),
    'R57': (164.8, BIAS_ROW_A_Y, 'pad1_down', 'B'),  # pad edge 165.5: 3.1 mm from the VIN ladder feed via (169.0, 132.0, r 0.4)
    'R53': (157.9, 125.5, None, 'B'), 'C64': (159.25, BIAS_ROW_B_Y, 'pad1_down', 'B'), 'R55': (161.75, BIAS_ROW_B_Y, None, 'B'),  # R53 above the rows: ls_bias keeps its full width
    'C66': (164.25, BIAS_ROW_B_Y, None, 'B'),
    'C69': (164.5, 125.5, None, 'B'), 'C67': (167.5, 125.5, None, 'B'), 'C68': (161.0, 125.3, 0, 'B'),  # upper row: PGND vias same-net with the snubber's PGND pad, >= 4.5 mm from the VIN feed via
    # C72 / C76 (5V_ISO decoupling of the two AMC1311s) stand directly under U6.1 / U7.1 (x 182.9 / 196.9); C74 sits between the two tap ports
    **{ref: (x, SENSE_FILTER_Y, None, 'B') for ref, x in (('C71', 177.6), ('C70', 180.1), ('C72', 182.6), ('R63', 185.1), ('R66', 187.6),
                                                           ('C74', 191.3), ('C75', 194.9), ('C76', 197.4))},
}
# Placement regions (side, [rects]). Island regions follow the .kicad_dru outer-layer functional rule (3 mm between the VIN,
# SW-referenced, PGND-referenced and VOUT groups, through-hole pads and vias included): the HS gate loop on B.Cu beside Q1's
# gate / Kelvin pins, the HS bias periphery on B.Cu under the HF tier next to U2's HV row, the DESAT network on F.Cu between
# the SW block and U1's escape vias; the LS island east of the SW copper and D5; the sensing islands clear of the ladder row
# and the VIN feed via; the SELV regions start below the barrier fan-out corridor (SELV_FAN_Y) and the mezzanine socket.
REGIONS = {
    'hs_gate': ('B', [[88.4, 127.6, 106.0, 137.8]]),
    'hs_bias': ('B', [[64.6, 127.6, 82.4, 137.8]]),  # under U2's bar vias (y 138.4): parts end at 137.8
    'hs_bias_f': ('F', [[66.5, 133.1, 79.2, 135.7]]),  # F.Cu west of D3, 3.5 mm below the VIN+ band: the 4.7 uF VDD-COM decoupling (1206, 2.3 mm courtyard) over the In2 Kelvin pour; U2's HV fan vias (ring >= 136.15) lie below
    'hs_desat': ('F', [[91.9, 129.2, 114.0, 137.8]]),
    'ls_gate': ('B', [[123.5, 128.6, 140.5, 137.8], [131.5, 120.5, 139.9, 128.6]]),  # r20 (LR-24) attempt NOT kept: one rect from the island top (127.6) placed all six parts but LS_FB_VEE / DESAT_L_OC lost their channels (r20c); the second rect over the SW In2 pour stays
    'ls_desat': ('F', [[124.0, 131.4, 157.0, 137.8]]),
    # LS bias periphery beside U4's HV row and the U5 periphery beside U5's (both PGND-referenced; vias to In2 are possible here)
    'ls_bias': ('B', [[140.5, 128.6, 157.0, 137.8]]),  # the HV-side bar vias keep a 2.2 mm placer corridor above them (escape_obstacles): the VDD_L via exit stays free (b7: pocket of 1277 cells under the packed 1206s)
    'u5_bias': ('B', [[157.0, 128.6, 168.0, 137.8], [156.0, 112.0, 168.0, 128.6]]),  # second rect under the heatsink (B.Cu only: no vias north of y 123)
    # AMC1311 input filters (R / C / C to PGND) as one row of 0603s on B.Cu between the ladder taps and the AMC HV rows, placed by anchor
    # distance so each group sits under its own AMC and tap; their in-pad PGND vias (y >= 136.5, ring >= 136.2) keep the 3 mm outer rule
    # from the ladder pads (y <= 132.8) and the U6 / U7 HV stub-end vias (ring 138.05-138.65) sit 0.5 mm below the parts' pads. The taps
    # end in a via too, so VIN_DIV / VOUT_DIV stay on B.Cu (tap via -> filter -> AMC stub-end via); F.Cu in the band carries 5V_ISO west
    'sense_b': ('B', [[168.5, 135.7, 199.4, 137.75]]),
    'selv_left': ('F', [[2.0, 151.5, 60.0, SELV_PARTS_MAX_Y]]),
    'selv_hs': ('F', [[61.0, SELV_FAN_Y, 109.5, SELV_PARTS_MAX_Y]]),
    'selv_ls': ('F', [[110.0, SELV_FAN_Y, 147.5, SELV_PARTS_MAX_Y], [148.0, 169.0, 161.5, SELV_PARTS_MAX_Y]]),  # second rect (U5's primaries) starts 3.5 mm below the J7.43-49 port lanes so their exits and the west-around passage stay open (b5: VOUT_SENSE's J7.49 port boxed by L4 at y 165-172)
    'selv_sense': ('F', [[162.0, SELV_SOCKET_PARTS_Y, 213.0, SELV_PARTS_MAX_Y]]),  # under the socket, below its two escape via rows
    'selv_east': ('F', [[216.0, 153.5, 229.0, SELV_PARTS_MAX_Y]]),  # east of the socket: the reference / OC group fed from U10's SELV row; x 212-216 stays a passage round the socket end
    'selv_decouple': ('F', [[174.0, 152.4, 203.0, 155.5]]),
}
ASSIGN_BY_REF = {
    # HS island: gate loop + Kelvin-referenced decoupling on B.Cu beside Q1, bias periphery on B.Cu beside U2, DESAT network on F.Cu
    **{r: 'hs_bias_f' for r in ('C22', 'C23')},
    **{r: 'hs_desat' for r in ('R24', 'R25', 'R26', 'C29', 'D4', 'C36', 'C37', 'C38', 'C39', 'C24', 'C26')},
    **{r: 'ls_gate' for r in ('R37', 'R38', 'R39', 'R40', 'R41', 'C41')},
    **{r: 'ls_bias' for r in ('C42', 'C43', 'C45', 'R47', 'R48', 'C54', 'R49', 'R50', 'C55', 'R51')},
    **{r: 'ls_desat' for r in ('R42', 'R43', 'R44', 'C49', 'D6', 'C56', 'C57', 'C58', 'C59', 'C44', 'C46')},
    # sensing island: the AMC1311 filters stand upright under the ladder row
    # SELV strip: driver input filters, pull-ups, bias chokes and input capacitors, sense amplifiers, test points
    # the RESET_N and BIAS_EN input filters (consumers U1 / U3 pin 14, U2 / U4 / U5 pin 4) sit in the roomy selv_hs region
    **{r: 'selv_hs' for r in ('R17', 'C20', 'R18', 'C27', 'C28', 'R27', 'R28', 'R34', 'L2', 'C30', 'C31', 'C32', 'C33', 'TP6',
                              'R67', 'C78', 'R68', 'R69', 'C79', 'R70')},
    **{r: 'selv_ls' for r in ('R35', 'C40', 'R36', 'C47', 'C48', 'R45', 'R46', 'R52', 'L3', 'C50', 'C51', 'C52', 'C53', 'L4', 'C60', 'C61', 'C62',
                              'C63', 'R58', 'TP7')},
    **{r: 'selv_sense' for r in ('C80', 'R71', 'R72', 'C81', 'R73', 'R74', 'C82', 'R75', 'R76', 'C83', 'R77', 'R78', 'C84', 'R82', 'R83',
                                 'C89', 'TP8', 'TP9', 'TP10', 'TP11', 'TP13')},
    **{r: 'selv_east' for r in ('U9', 'C85', 'C86', 'R79', 'R80', 'R81', 'C87')},
    **{r: 'selv_decouple' for r in ('C73', 'C77')},
    **{r: 'selv_left' for r in ('R84', 'Q3', 'R85', 'R86', 'D7', 'C90', 'C91', 'TP3', 'TP4', 'TP5')},
}
SILKSCREEN = [
    (f'AIPE SiC BUCK 400V -> 200V / 5kW - POWER BOARD {REVISION}', (120.0, 121.2), 1.0),
    (BANNER, (120.0, 118.9), 0.9),
    ('DANGER - 400 V DC - HAZARDOUS - DC LINK LIVE: DISCHARGE 60 s AFTER SWITCH-OFF', (99.0, 14.0), 1.0),
    ('ISO BARRIER 10 mm - NO COPPER', (30.0, 145.0), 0.9), ('HV SIDE', (228.0, 136.0), 1.0), ('SELV SIDE', (228.0, 153.5), 1.0),
    ('VIN+', (9.0, 103.0), 1.0), ('RELAY', (9.0, 138.0), 1.0), ('PGND', (23.0, 103.0), 1.0), ('RELAY', (23.0, 138.0), 1.0), ('VOUT+', (162.2, 42.0), 1.0),
    ('PGND', (158.0, 75.0), 1.0),
    ('PE', (22.0, 8.0), 1.0), ('HEATSINK LAM 5 D K 100 x 100 x 50 - FAN', (SINK_CENTRE[0], 60.0), 1.2), ('AIR FLOW -->', (SINK_CENTRE[0], 70.0), 1.2),
    ('MEZZANINE J7 - PIN 1 RIGHT', (200.0, 165.0), 0.9), ('FAN', (36.0, 166.0), 0.8), ('RELAY COIL', (18.0, 165.5), 0.8),
]
NOTES = [
    'Every structural part (half bridge, HF ceramics, films, inductor, heatsink, terminals, barrier parts, connectors, standoff holes) is '
    'fixed by the floorplan table; the island, sensing and SELV-strip passives are auto-placed in their regions (islands shelf-packed, '
    'SELV parts by Manhattan distance to their nets).',
    'HV copper is pours: VIN+ on F.Cu (left column merged with the top band, band under the HF tier) and In2.Cu (backbone under the sink '
    'with an east arm to the VIN ladder feed), PGND on In1.Cu (whole HV area) and B.Cu (outside the islands), SW on F.Cu (device block) '
    'and In2.Cu (strip to the inductor), VOUT on F.Cu/In2.Cu/B.Cu to the output bank; 1.2/0.6 mm via groups join the layers; the '
    'Kelvin-source pours sit on In2.Cu under the driver islands and the gate pours on B.Cu over them (KR-PCB-001).',
    'The ISO_BARRIER rule area forbids tracks, vias and pours on every copper layer in the 10 mm strip; the barrier packages pad rows are '
    'notched out of it and every barrier footprint carries its own 1.2 mm NPTH isolation slot (KR-ISO-004).',
    'The grid router routes the driver islands (F.Cu / In2.Cu / B.Cu inside the island footprints, gate nets 1.0 mm), the sensing networks '
    'and the SELV strip (F.Cu / B.Cu; GND_CTRL on In1.Cu and 3V3 on In2.Cu are pours reached by the escape vias); every routed net is '
    'confined to its own routing region, so no island net can approach another HV group; the HV nets are excluded from routing and '
    'connected by the pours and via groups only.',
    'Stage 3 corrections (zones-only DRC experiment): chain parts on the pin-field pitch with courtyard-contained stubs, DAMP_MID bypass, '
    'LED / 1206 feeds through F.Cu zone patches and 3 mm vias, terminals re-pitched for the REDCUBE pin-field gap, VIN In2 backbone clear '
    'of the VOUT In2 bar, HV ladders in one row with via feeds, HV via rings and HV pads reserved for the auto-placer, VOUT_L without vias, '
    'PGND right strip stitched, small PGND pads routed by the fanout.',
    'Round r20 (second independent review, verification/layout_review_findings.json LR-20..LR-35): the saved zone fills are refilled in a '
    'fresh KiCad Python process after routing so that the stored copper is the rule-aware copper (LR-20; a no-refill DRC of the stored '
    'fills is recorded as a diagnostic in engineering_checks/stored_zone_fill_check.json); all-layer pour / via keep-outs around the '
    'four heatsink mounting holes (LR-21); input return terminal J2 moved out of the corner pocket to the open east position of the upper '
    'input row, the relay input J5 (same net as J1) takes the pocket, the PTC pad RT1.1 is fed by a 2 mm B.Cu VIN_RAW track and the B.Cu '
    'PGND column is extended under the HF tier (LR-23); SW In2 block / neck '
    'widened and 32 PGND stitching vias in the J4 output block (LR-28); sink, output terminals and output films shifted east so the input '
    'films keep >= 20 mm and the MOV RV1 moved to the exhaust side (LR-25).',
    'Only the kicad-cli DRC manifest (schematic parity, severity-all) is verification; the router report is a geometric proposal.',
]


# --- helpers -------------------------------------------------------------------------------------------------------


def snap(v: float, grid: float = GRID) -> float:
    return round(round(v / grid) * grid, 4)


def boxes_overlap(a, b, gx: float = 0.0, gy: float = 0.0) -> bool:
    return a[0] - gx < b[2] and a[2] + gx > b[0] and a[1] - gy < b[3] and a[3] + gy > b[1]


def rect_poly(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def text_box(text: str, xy, size: float):
    width = len(text) * size * 1.1 + 0.6
    height = size * 1.7
    return (xy[0] - width / 2, xy[1] - height / 2, xy[0] + width / 2, xy[1] + height / 2)


def stackup_text() -> str:
    lines = ['(stackup']
    for layer, kind, thickness in STACKUP:
        if kind == 'copper':
            lines.append(f'(layer "{layer}" (type "copper") (thickness {thickness}))')
        else:
            lines.append(f'(layer "{layer}" (type "{kind}") (thickness {thickness}) (material "FR4") (epsilon_r 4.3) (loss_tangent 0.02))')
    lines.append('(copper_finish "ENIG") (dielectric_constraints no))')
    return '\n'.join(lines)


def stackup_thickness_mm() -> float:
    return round(sum(t for _, _, t in STACKUP), 3)


def inject_stackup(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    if '(stackup' in text:
        return False
    text = text.replace('(paper "A4")', '(paper "A3")', 1)
    marker = '(setup\n'
    if marker not in text:
        raise RuntimeError('board file has no (setup block')
    path.write_text(text.replace(marker, marker + stackup_text() + '\n', 1), encoding='utf-8')
    return True


def load_parts(path: Path = MODEL_JSON) -> list[dict]:
    parts = json.loads(Path(path).read_text(encoding='utf-8'))
    refs = [p['ref'] for p in parts]
    if len(refs) != len(set(refs)):
        raise ValueError('duplicate references in the model')
    return parts


def export_netlist(schematic: Path, target: Path, cli=None) -> dict:
    cli = cli or find_kicad_cli()
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(cli), 'sch', 'export', 'netlist', '--format', 'kicadxml', '--output', str(target), str(schematic)],
                   check=True, capture_output=True, timeout=300)
    tree = ET.parse(target).getroot()
    return {(node.attrib['ref'], node.attrib['pin']): net.attrib['name'] for net in tree.findall('nets/net') for node in net.findall('node')}


def kicad_python():
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


REFILL_SCRIPT = r'''
import json, sys
import pcbnew as pcb
path = sys.argv[1]
board = pcb.LoadBoard(path)
def areas(b):
    out = {}
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for layer in z.GetLayerSet().Seq():
            key = z.GetNetname() + "/" + b.GetLayerName(layer)
            out[key] = round(out.get(key, 0.0) + z.GetFilledPolysList(layer).Area() / 1e12, 1)
    return out
before = areas(board)
board.BuildConnectivity()
ok = pcb.ZONE_FILLER(board).Fill(board.Zones())
pcb.SaveBoard(path, board, True)
after = areas(pcb.LoadBoard(path))
print("AIPE_REFILL_JSON " + json.dumps(dict(filled=bool(ok), before=before, after=after)))
'''


def rule_aware_refill(board_path: Path) -> dict:
    """r20 (LR-20): refill every zone of the SAVED board in a fresh KiCad Python process and save it again, so that the stored fills
    are the rule-aware copper. pcbnew.LoadBoard initialises the board's DRC engine from the project .kicad_dru (netclass rules 3.0 /
    1.0 / 9.0 / 5.0 mm and the pin-field exceptions) and ZONE_FILLER applies it; the in-process fills of the routing stage did not
    carry these rules (the r19 board stored 0.3 mm fills: 499 clearance findings without --refill-zones). Returns the fill areas
    (mm2 per net/layer) before and after; the project file is not touched (SaveBoard with aSkipSettings)."""
    python = kicad_python() or Path(sys.executable)
    completed = subprocess.run([str(python), '-c', REFILL_SCRIPT, str(board_path)], capture_output=True, text=True, encoding='utf-8',
                               errors='replace', timeout=900, cwd=str(ROOT))
    line = next((ln for ln in (completed.stdout + '\n' + completed.stderr).splitlines() if ln.startswith('AIPE_REFILL_JSON ')), None)
    if completed.returncode or line is None:
        raise RuntimeError(f'rule-aware refill failed (exit {completed.returncode}): {completed.stderr[-2000:]}')
    data = json.loads(line[len('AIPE_REFILL_JSON '):])
    changed = {k: [data['before'].get(k), data['after'].get(k)] for k in sorted(set(data['before']) | set(data['after']))
               if data['before'].get(k) != data['after'].get(k)}
    return dict(filled=data['filled'], python=str(python), zones=len(data['after']), changed_areas_mm2=changed)


def stored_fill_check(board_path: Path, cli, label: str = 'power', checks_dir: Path = CHECKS_DIR) -> dict:
    """r20 (LR-20) diagnostic (NOT verification evidence): kicad-cli DRC WITHOUT --refill-zones on a temporary copy of the board
    directory, i.e. of the zone fills as stored in the file - the copper that gerber / PDF / render / STEP exports contain. Writes
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
    checks_dir = Path(checks_dir)
    checks_dir.mkdir(parents=True, exist_ok=True)
    (checks_dir / f'stored_zone_fill_check_{label}.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return {k: record.get(k) for k in ('violations', 'unconnected_items', 'by_type', 'by_rule', 'error') if k in record}


def read_manifest(path) -> dict:
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


# --- geometry of the pours, rule areas and via groups (pure) --------------------------------------------------------


def sink_courtyard():
    cx, cy = SINK_CENTRE
    return [cx - 50.75, cy - 50.5, cx + 50.75, cy + 50.5]


def sink_keepout_rect():
    c = sink_courtyard()
    k = SINK_KEEPOUT_MM
    return [c[0] - k, c[1] - k, c[2] + k, c[3] + k]


def l1_holes():
    cx, cy = L1_CENTRE
    p = L1_HOLE_PITCH
    return [(cx - p, cy - p), (cx - p, cy + p), (cx + p, cy - p), (cx + p, cy + p)]


def m4_holes():
    return [FIXED[r][:2] for r in ('H2', 'H3', 'H4', 'H5', 'H6', 'H7')]


def hs1_holes():
    """Centres (mm) of the heatsink footprint's four NPTH mounting holes."""
    cx, cy = SINK_CENTRE
    return [(cx + dx, cy + dy) for dx, dy in HS1_HOLE_OFFSETS]


def hs1_hole_keepout_polygon(x: float, y: float, sides: int = 16) -> list[list[float]]:
    """Regular polygon circumscribed about the circle hole_radius + SINK_KEEPOUT_MM (its flats, not only its corners, keep the distance)."""
    r = (HS1_HOLE_D / 2 + SINK_KEEPOUT_MM) / math.cos(math.pi / sides)
    return [[round(x + r * math.cos(2 * math.pi * k / sides), 4), round(y + r * math.sin(2 * math.pi * k / sides), 4)] for k in range(sides)]


L1_COURTYARD_R = 35.05  # the toroid footprint's circular courtyard (75 mm keep-out circle of the inductor record)


def l1_circle_clear(box) -> bool:
    """True when the mm box lies entirely outside the inductor's circular courtyard."""
    cx, cy = L1_CENTRE
    nx = min(max(cx, box[0]), box[2]); ny = min(max(cy, box[1]), box[3])
    return math.dist((nx, ny), (cx, cy)) > L1_COURTYARD_R


VIN_BAND_CUT_Y = 129.6  # the VIN+ F.Cu band under the HF tier ends here east of row B so the HS island's west strip can escape (3 mm rule)
D3_TAB = (82.8, VIN_BAND_CUT_Y, 86.2, 132.7)  # VIN+ band tab down to the HS DESAT diode's drain pad (D3 pad 1 at y 130.25-132.75; 1.55 mm to its DESAT pad)
VIN_BAND_CUT_X = 63.5
VIN_BAND_X0 = 17.0  # r20 (LR-23): the VIN+ F.Cu band under the HF tier starts 3 mm east of the J1 / J5 VIN_RAW pin fields (x <= 13.54)
VIN_RAW_X1 = 14.5  # r20: the VIN_RAW pours (F.Cu / B.Cu) cover the J1 / J5 column only (the filler keeps 3 mm to J2's and J6's pin fields)
RT1_FEED_Y = 101.5  # r20: B.Cu VIN_RAW feed of the PTC pad RT1.1 runs along this line: 3.47 mm from J2's PGND pins (y >= 105.97), 3.25 mm from the C12 VIN pins (y <= 97.25)
RT1_FEED_X0 = 12.0  # the feed leaves the J1 / J5 VIN_RAW B.Cu pour inside the J1 pin field (x <= 13.96 after the 3 mm clip to J2) and climbs to RT1_FEED_Y
PGND_TIER_X1 = 61.5  # r20 (LR-23 / LR-22): the B.Cu PGND column continues east under the HF tier to 3 mm before the HS bias island (x 64.6)
SW_BLOCK_TOP_Y, SW_NECK_TOP_Y = 95.0, 85.0  # r20 (LR-28): SW In2 block 31.8 mm tall at the device pins, neck 41.8 mm tall (28.4 mm beside the sink hole keep-out)


def zone_plan() -> list[dict]:
    """[{net, layer, polygon, priority, clearance[, keepout_rects, router_keepout]}] - HV, Kelvin, gate and SELV pours. Polygons are
    generous; the KiCad filler clips them to the .kicad_dru clearances (3.0 mm HV functional on the outer layers, 1.0 mm inner,
    9.0 mm to SELV, 5.0 mm to PE, 0.3 mm same-reference island) and to the rule areas. ``keepout_rects`` are the router's
    net-coded keep-out boxes for the pour (default: the polygon's bounding box); ``router_keepout=False`` leaves a pour open to
    foreign tracks (the filler clips around them); ``post_route`` zones are added after the signal stage (their nets are routed
    as signals, the pour is an enhancement, so cutting through it costs nothing)."""
    hv = HV_LIMIT_Y
    m = BOARD_MARGIN
    zones = []
    # VIN+ : F.Cu column merged with the top band, band under the HF tier (cut back to y 133 east of row B so the HS island's west
    # strip keeps 3 mm from it); In2.Cu backbone under the sink up to x 152 (clear of the VOUT In2 bar) with an east arm to the
    # VIN ladder feed via
    zones.append(dict(net='VIN', layer='F.Cu', polygon=[[m, m], [150.0, m], [150.0, 11.4], [43.0, 11.4], [43.0, 101.5], [m, 101.5]], priority=2,
                      keepout_rects=[[m, m, 43.0, 101.5], [43.0, m, 150.0, 11.4]]))
    vb = VIN_BAND_X0
    zones.append(dict(net='VIN', layer='F.Cu', polygon=[[vb, 120.0], [88.3, 120.0], [88.3, VIN_BAND_CUT_Y], [D3_TAB[2], VIN_BAND_CUT_Y], [D3_TAB[2], D3_TAB[3]],
                                                        [D3_TAB[0], D3_TAB[3]], [D3_TAB[0], VIN_BAND_CUT_Y], [VIN_BAND_CUT_X, VIN_BAND_CUT_Y],
                                                        [VIN_BAND_CUT_X, hv], [vb, hv]], priority=2,
                      keepout_rects=[[vb, 120.0, 88.3, VIN_BAND_CUT_Y], [vb, VIN_BAND_CUT_Y, VIN_BAND_CUT_X, hv], list(D3_TAB)]))
    zones.append(dict(net='VIN', layer='In2.Cu', polygon=[[m, m], [152.0, m], [152.0, 61.5], [201.5, 61.5], [201.5, 134.5], [150.0, 134.5],
                                                         [150.0, hv], [m, hv]], priority=2))
    # VIN_RAW: the J1 / J5 terminal column on F.Cu and B.Cu (3.0 mm from the VIN pours, higher priority so the filler clips VIN); the
    # PTC pad RT1.1 is fed by the B.Cu track of rt1_vin_raw_feed (r20)
    for layer in ('F.Cu', 'B.Cu'):
        zones.append(dict(net='VIN_RAW', layer=layer, polygon=rect_poly(m, 104.5, VIN_RAW_X1, 137.0), priority=3))
    # PGND: In1 whole HV area; B.Cu one polygon (left column + top band + output block) and a stitched right strip
    zones.append(dict(net='PGND', layer='In1.Cu', polygon=rect_poly(m, m, WIDTH - m, hv), priority=1))
    sk = sink_keepout_rect()
    tier_y = round(sk[3] + 0.05, 3)  # r20: B.Cu PGND under the HF tier starts 5 mm below the sink courtyard (KR-TH-002 outer-layer keep-out)
    out_x0 = round(sk[2] + 0.05, 3)  # the B.Cu output block (J4 field) starts 5 mm east of the sink courtyard
    zones.append(dict(net='PGND', layer='B.Cu', polygon=[[m, m], [WIDTH - m, m], [WIDTH - m, 11.4], [199.5, 11.4], [199.5, 92.0], [out_x0, 92.0],
                                                        [out_x0, 11.4], [43.4, 11.4], [43.4, tier_y], [PGND_TIER_X1, tier_y], [PGND_TIER_X1, hv], [m, hv]],
                      priority=1, router_keepout=False))
    zones.append(dict(net='PGND', layer='B.Cu', polygon=rect_poly(218.5, 63.5, WIDTH - m, hv), priority=1, router_keepout=False))  # PE routes on B.Cu here
    # SW: F.Cu device block from x 91 (Q1 drain pad keeps its VIN copper) to 3 mm west of Q2's PGND pin, 24-via group to In2;
    # In2.Cu block + 26.8 mm neck + 22 mm strip to the inductor (the snubber R11 sits over the neck with an in-pad HV via)
    zones.append(dict(net='SW', layer='F.Cu', polygon=rect_poly(91.0, 122.6, 116.1, 128.6), priority=3))
    zones.append(dict(net='SW', layer='In2.Cu', polygon=[[89.0, SW_BLOCK_TOP_Y], [117.0, SW_BLOCK_TOP_Y], [117.0, SW_NECK_TOP_Y], [160.0, SW_NECK_TOP_Y],
                                                        [160.0, 91.5], [195.5, 91.5], [195.5, 113.5], [160.0, 113.5], [160.0, 126.8], [89.0, 126.8]], priority=3))
    # VOUT_L: F.Cu bar from the inductor to the TMCS1133 input bar (no inner copper)
    zones.append(dict(net='VOUT_L', layer='F.Cu', polygon=rect_poly(214.0, 89.0, 224.0, hv), priority=3))
    # VOUT: F.Cu bar beside the VOUT_L bar + output bank + J3 patch + R9 feed patch; In2 bar with the J3-column feed tab (output
    # bleeder / indicator chain), the strip under the bar and the bottom tab for the TMCS1133 and the VOUT ladder feed; B.Cu strip
    zones.append(dict(net='VOUT', layer='F.Cu', polygon=[[155.5, 44.0], [168.0, 44.0], [168.0, 36.0], [WIDTH - m, 36.0], [WIDTH - m, 60.0], [210.5, 60.0],
                                                         [210.5, hv], [203.0, hv], [203.0, 60.0], [168.0, 60.0], [168.0, 56.0], [155.5, 56.0]], priority=2,
                      keepout_rects=[[155.5, 44.0, 168.0, 56.0], [168.0, 36.0, WIDTH - m, 60.0], [203.0, 60.0, 210.5, hv]]))
    zones.append(dict(net='VOUT', layer='In2.Cu', polygon=[[155.5, 1.5], [167.0, 1.5], [167.0, 36.0], [WIDTH - m, 36.0], [WIDTH - m, 60.0], [215.0, 60.0],
                                                           [215.0, hv], [161.0, hv], [161.0, 136.0], [203.0, 136.0], [203.0, 60.0], [155.5, 60.0]], priority=2))
    zones.append(dict(net='VOUT', layer='B.Cu', polygon=[[168.0, 36.0], [WIDTH - m, 36.0], [WIDTH - m, 60.0], [215.0, 60.0], [215.0, hv], [203.0, hv],
                                                         [203.0, 60.0], [168.0, 60.0]], priority=2,
                      keepout_rects=[[168.0, 36.0, WIDTH - m, 60.0], [203.0, 60.0, 215.0, hv]]))
    # Kelvin-source pours under the driver islands (In2.Cu, shield between the B.Cu gate copper and the rest) and the gate pours on
    # B.Cu over them (KR-PCB-001); both nets are also routed as signals, the pours are added after the signal stage
    zones.append(dict(net='KS_H', layer='In2.Cu', polygon=rect_poly(64.6, ISLAND_TOP_Y, ISLAND_WALL_X[0], hv), priority=4, post_route=True))
    zones.append(dict(net='KS_L', layer='In2.Cu', polygon=rect_poly(ISLAND_WALL_X[1] + 1.0, ISLAND_TOP_Y, 153.0, hv), priority=4, post_route=True))
    zones.append(dict(net='G_H', layer='B.Cu', polygon=rect_poly(*REGIONS['hs_gate'][1][0]), priority=5, post_route=True))
    zones.append(dict(net='G_L', layer='B.Cu', polygon=rect_poly(*REGIONS['ls_gate'][1][0]), priority=5, post_route=True))
    # SELV strip: GND_CTRL on In1, 3V3 on In2 (both reached by the escape vias of every pad of those nets)
    zones.append(dict(net='GND_CTRL', layer='In1.Cu', polygon=rect_poly(m, SELV_START_Y, WIDTH - m, HEIGHT - m), priority=1))
    zones.append(dict(net='3V3', layer='In2.Cu', polygon=rect_poly(m, SELV_START_Y, WIDTH - m, HEIGHT - m), priority=4, post_route=True))  # 3V3 is routed; the pour is added after the signal stage and clipped around the strip's In2 tracks
    for z in zones:
        z.setdefault('clearance', ZONE_CLEARANCE)
    return zones


FEED_VIAS = {'R59': (169.0, 132.0), 'R64': (203.5, 132.0), 'R9': (163.5, 33.875)}
# ladder taps (SENSE_ISO pads of the 1206 ladders): exact stub (length beyond the pad end, direction, lateral offset inside the pad)
# southwards into the sensing island; the offset keeps the track 3 mm from the chain stub that enters the other pad of the 1206
TAP_STUBS = {('R62', '2'): (3.6, (0, 1), 0.25), ('R65', '2'): (3.6, (0, 1), -0.25)}  # ladder / indicator feed vias (0.8/0.4): VIN west of R59, VOUT in the F.Cu strip east of R64, VOUT below R9


def via_groups() -> list[dict]:
    """HV layer transitions as 1.2/0.6 mm via groups: [{net, origin, pitch, count[, diameter, drill]}] (origin = first via)."""
    groups = [
        dict(net='VIN', origin=(39.0, 121.5), pitch=(2.2, 2.0), count=(2, 3)),  # F.Cu band -> In2 backbone (6, plus the J6 / RT1 plated pads)
        dict(net='VIN', origin=(4.0, 72.0), pitch=(2.2, 2.2), count=(10, 2)),  # column -> In2 (20), between the C12 pad rows
        dict(net='VIN', origin=(124.5, 4.0), pitch=(2.2, 2.2), count=(3, 2)),  # top band -> In2 (6), east of the damping legs
        dict(net='PGND', origin=(224.5, 76.0), pitch=(3.0, 4.0), count=(2, 11)),  # stitches the B.Cu right strip to In1 (22)
        dict(net='PGND', origin=(170.0, 76.0), pitch=(3.0, 3.0), count=(8, 4)),  # r20 (LR-28): stitches the B.Cu PGND output block (J4 field) to In1 (32)
        dict(net='VOUT', origin=FEED_VIAS['R9'], pitch=(2.2, 2.2), count=(1, 1), diameter=0.8, drill=0.4),  # R9 VOUT feed <- In2 column tab (3 mm stub)
        dict(net='VIN', origin=FEED_VIAS['R59'], pitch=(2.2, 2.2), count=(1, 1), diameter=0.8, drill=0.4),  # VIN ladder feed (stub east to R59 pad 1)
        dict(net='SW', origin=(104.8, 123.3), pitch=(1.7, 1.1), count=(6, 4)),  # F.Cu device block -> In2 strip (24): four rows above the Kelvin pour (a row at y 127.7 lies under it and dangles), six columns between the TP1 loop and Q2 pin 1
        dict(net='VOUT', origin=(204.5, 66.0), pitch=(2.5, 3.0), count=(3, 12)),  # F.Cu bar <-> In2 <-> B.Cu strips (36)
        dict(net='VOUT', origin=(178.0, 46.0), pitch=(2.6, 2.6), count=(8, 3)),  # output bank F.Cu <-> In2 <-> B.Cu (24)
    ]
    return groups


def rule_areas() -> list[dict]:
    """Keep-out rule areas: [{name, layers, polygon, tracks, vias, pours}]."""
    areas = []
    sk = sink_keepout_rect()
    areas.append(dict(name='HEATSINK_HV_KEEPOUT', layers=['F.Cu'], polygon=rect_poly(*sk), tracks=True, vias=True, pours=True))  # B.Cu under the sink holds the driver islands (DRV nets, not HV copper)
    for i, (x, y) in enumerate(l1_holes(), 1):
        r = L1_ANNULUS_R
        areas.append(dict(name=f'L1_STANDOFF_{i}', layers=COPPER_LAYERS, polygon=rect_poly(x - r, y - r, x + r, y + r), tracks=True, vias=True, pours=True))
    for i, (x, y) in enumerate(m4_holes(), 1):
        r = M4_KEEPOUT_R_SELV if y > ISO_STRIP[1] else M4_KEEPOUT_R
        areas.append(dict(name=f'M4_STANDOFF_{i}', layers=COPPER_LAYERS, polygon=rect_poly(x - r, y - r, x + r, y + r), tracks=True, vias=True, pours=True))
    for i, (x, y) in enumerate(hs1_holes(), 1):  # r20 (LR-21): >= 5 mm all-layer pour / via keep-out around the PE-bonded sink's mounting holes
        areas.append(dict(name=f'HS1_HOLE_{i}', layers=COPPER_LAYERS, polygon=hs1_hole_keepout_polygon(x, y), tracks=False, vias=True, pours=True))
    return areas


def iso_barrier_polygon(pad_rows: list[tuple]) -> list[list[float]]:
    """ISO_BARRIER strip (y 140-150, full width) with notches around the barrier packages' pad rows.

    ``pad_rows``: [(x0, y0, x1, y1)] copper boxes of the HV-side rows (overlapping the strip's top edge) and the
    SELV-side rows (overlapping its bottom edge); the strip polygon dips/rises around each by 0.3 mm."""
    y_top, y_bot = ISO_STRIP
    top_notches = sorted((r[0] - 0.3, r[2] + 0.3, r[3] + 0.3) for r in pad_rows if r[1] < BARRIER_Y)  # (x0, x1, depth y)
    bot_notches = sorted((r[0] - 0.3, r[2] + 0.3, r[1] - 0.3) for r in pad_rows if r[1] > BARRIER_Y)
    pts = [[0.0, y_top]]
    for x0, x1, depth in top_notches:
        if depth <= y_top:
            continue
        pts += [[x0, y_top], [x0, depth], [x1, depth], [x1, y_top]]
    pts += [[WIDTH, y_top], [WIDTH, y_bot]]
    for x0, x1, height in sorted(bot_notches, reverse=True):
        if height >= y_bot:
            continue
        pts += [[x1, y_bot], [x1, height], [x0, height], [x0, y_bot]]
    pts += [[0.0, y_bot]]
    return pts


# --- board construction (pcbnew) ---------------------------------------------------------------------------------------


class Builder:
    def __init__(self, parts: list[dict], mapping: dict, pin_nets: dict):
        import pcbnew as pcb
        self.pcb = pcb
        self.parts = parts
        self.by_ref = {p['ref']: p for p in parts}
        self.pin_nets = pin_nets
        self.board = pcb.BOARD()
        self.board.SetCopperLayerCount(len(COPPER_LAYERS))
        self.board.GetDesignSettings().SetBoardThickness(pcb.FromMM(stackup_thickness_mm()))
        title = self.board.GetTitleBlock()
        title.SetTitle(TITLE)
        title.SetRevision(REVISION)
        title.SetComment(0, BANNER)
        self.nets = {}
        for name in sorted(set(pin_nets.values())):
            self.nets[name] = pcb.NETINFO_ITEM(self.board, name)
            self.board.Add(self.nets[name])
        self.footprints: dict = {}
        self.occupied = {'F': [], 'B': []}
        self.placements: dict = {}
        self.pose_cache: dict = {}
        self.issues: list[str] = []
        for part in parts:
            lib, name = part['footprint'].split(':')
            fp = pcb.FootprintLoad(str(KICAD_DIR / 'libraries' / f'{lib}.pretty'), name)
            if fp is None:
                raise ValueError(f"{part['ref']}: pcbnew could not load {part['footprint']}")
            fp.SetFPID(pcb.LIB_ID(lib, name))
            fp.SetReference(part['ref'])
            fp.SetValue(part['value'])
            if part.get('dnp'):
                fp.SetDNP(True)  # V2.1: the wired schematics write (dnp yes) (in_bom / on_board stay yes); kicad-cli --schematic-parity compares the attribute
            if part['ref'] not in mapping:
                raise ValueError(f"{part['ref']}: no schematic path in {MAPPING_JSON.name}")
            fp.SetPath(pcb.KIID_PATH(mapping[part['ref']]))
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
                if key in pin_nets:
                    pad.SetNet(self.nets[pin_nets[key]])
                elif part['nets'][number] is not None:
                    raise ValueError((part['ref'], 'pad without a netlist node', number))
            if seen != set(part['nets']):
                raise ValueError((part['ref'], 'missing pads', sorted(set(part['nets']) - seen)))
            self.board.Add(fp)
            self.footprints[part['ref']] = fp

    def point(self, x, y):
        return self.pcb.VECTOR2I(self.pcb.FromMM(x), self.pcb.FromMM(y))

    def mm(self, v):
        return self.pcb.ToMM(v)

    def set_pose(self, fp, x, y, angle, side='F'):
        if fp.IsFlipped() != (side == 'B'):
            fp.Flip(fp.GetPosition(), self.pcb.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(angle)
        fp.SetPosition(self.point(x, y))

    def courtyard(self, fp, side='F'):
        pcb = self.pcb
        layer = pcb.F_CrtYd if side == 'F' else pcb.B_CrtYd
        try:
            box = fp.GetCourtyard(layer).BBox()
            if box.GetWidth() <= 0 or box.GetHeight() <= 0:
                raise ValueError
        except Exception:
            box = fp.GetBoundingHull().BBox()
        return [self.mm(box.GetX()), self.mm(box.GetY()), self.mm(box.GetRight()), self.mm(box.GetBottom())]

    def pose_geometry(self, ref, angle, side):
        fp = self.footprints[ref]
        key = (self.by_ref[ref]['footprint'], angle, side)
        if key not in self.pose_cache:
            saved = ((self.mm(fp.GetPosition().x), self.mm(fp.GetPosition().y)), fp.GetOrientationDegrees(), 'B' if fp.IsFlipped() else 'F')
            self.set_pose(fp, 0.0, 0.0, angle, side)
            box = self.courtyard(fp, side)
            pads = {pad.GetNumber(): (self.mm(pad.GetPosition().x), self.mm(pad.GetPosition().y)) for pad in fp.Pads() if pad.GetNumber()}
            self.pose_cache[key] = (box, pads)
            self.set_pose(fp, saved[0][0], saved[0][1], saved[1], saved[2])
        return self.pose_cache[key]

    def gap_for(self, part: dict, local_pads: dict, region=None):
        kind = part['kind']
        extra = REGION_GAPS.get(region, (0.0, 0.0))
        if part['ref'] in REF_GAPS:
            return REF_GAPS[part['ref']]
        if kind == 'TP':
            return max(GAP_TP, extra[0]), max(GAP_TP, extra[1])
        if kind in ('J', 'H', 'HS'):
            return GAP_CONNECTOR, GAP_CONNECTOR
        if (kind == 'Q' and len(local_pads) == 4) or part['ref'] in BARRIER_REFS:
            return 0.5, 0.5  # TO-247 and barrier package courtyards already enclose the body: island parts may follow closely
        hv = any(n in HV_CLASS_NETS and n != 'PGND' for n in part['nets'].values() if n)  # PGND-only parts sit in the islands (0.3 mm same-island rule)
        if len(local_pads) == 2 and kind in ('C', 'R', 'D', 'L', 'RV', 'RT'):
            (ax, ay), (bx, by) = list(local_pads.values())
            gaps = (GAP_AXIS, GAP_LATERAL) if abs(ax - bx) >= abs(ay - by) else (GAP_LATERAL, GAP_AXIS)
            if region in REGION_GAPS:  # region gaps override the island defaults (axis, across) in the part's own orientation
                gaps = extra if abs(ax - bx) >= abs(ay - by) else (extra[1], extra[0])
            return (max(gaps[0], GAP_HV), max(gaps[1], GAP_HV)) if hv else gaps
        return (max(GAP_IC, extra[0]), max(GAP_IC, extra[1]))

    def sides_for(self, ref, side):
        """Board sides a part occupies for the courtyard packer: both for through-hole parts (except the barrier packages, whose only
        through feature is the isolation slot inside the no-copper strip) and for parts whose pads get in-pad vias to the inner pours."""
        fp = self.footprints[ref]
        if ref == 'HS1':
            return ('F',)  # the heatsink stands on the component side; B.Cu under it holds the driver islands (its NPTH holes are far from them)
        thru = any(pad.GetAttribute() in (self.pcb.PAD_ATTRIB_PTH, self.pcb.PAD_ATTRIB_NPTH) for pad in fp.Pads())
        return ('F', 'B') if (thru and ref not in BARRIER_REFS) else (side,)  # in-pad HV vias are reserved separately (HVVIA boxes, 3 mm)

    def place(self, ref, x, y, angle, side='F', region=None, check=True):
        fp = self.footprints[ref]
        self.set_pose(fp, x, y, angle, side)
        box = self.courtyard(fp, side)
        sides = self.sides_for(ref, side)
        if check:
            for s in sides:
                for other, other_box, _ in self.occupied[s]:
                    if boxes_overlap(box, other_box):
                        if other == 'L1' and l1_circle_clear(box):
                            continue  # the toroid's courtyard is a circle: a box outside the circle but inside its bounding box is fine
                        raise ValueError(('courtyard overlap', ref, other, [round(v, 3) for v in box], [round(v, 3) for v in other_box]))
            if box[0] < EDGE_COURTYARD or box[1] < EDGE_COURTYARD or box[2] > WIDTH - EDGE_COURTYARD or box[3] > HEIGHT - EDGE_COURTYARD:
                raise ValueError(('courtyard outside the board margin', ref, [round(v, 3) for v in box]))
        _, local_pads = self.pose_geometry(ref, angle, side)
        gaps = self.gap_for(self.by_ref[ref], local_pads, region)
        for s in sides:
            self.occupied[s].append((ref, box, gaps))
        if len(sides) == 1 and ref not in BARRIER_REFS:  # PGND pads get in-pad vias to In1: block a small box on the far side
            far = 'B' if side == 'F' else 'F'
            for pad in fp.Pads():
                if pad.GetNetname() == 'PGND' and pad.GetAttribute() == self.pcb.PAD_ATTRIB_SMD:
                    px, py = self.mm(pad.GetPosition().x), self.mm(pad.GetPosition().y)
                    self.occupied[far].append((f'VIA:{ref}', [px - 0.9, py - 0.9, px + 0.9, py + 0.9], (0.0, 0.0)))
        self.placements[ref] = dict(x=round(x, 4), y=round(y, 4), angle=angle, side=side, region=region, courtyard=[round(v, 3) for v in box])
        return box

    def placed_pads(self) -> dict:
        table = {}
        for ref in self.placements:
            fp = self.footprints[ref]
            for pad in fp.Pads():
                if pad.GetNumber():
                    table[(ref, pad.GetNumber())] = dict(xy=(self.mm(pad.GetPosition().x), self.mm(pad.GetPosition().y)), net=pad.GetNetname(),
                                                         kind=self.by_ref[ref]['kind'])
        return table

    def upright_angle(self, ref, side, down='2'):
        """Rotation (90 or 270) that stands a two-pad part upright with pad ``down`` below the other pad on the given side."""
        for angle in (90, 270):
            _, pads = self.pose_geometry(ref, angle, side)
            (x1, y1), (x2, y2) = pads['1'], pads['2']
            if abs(x1 - x2) < 0.05 and ((y2 > y1) == (down == '2')):
                return angle
        raise ValueError(f'{ref}: no upright pose with pad {down} below the other pad')

    def place_fixed(self):
        for ref, pose in FIXED.items():
            if ref not in self.footprints:
                raise ValueError(f'fixed part {ref} is not in the model')
            x, y, angle = pose[:3]
            side = pose[3] if len(pose) == 4 else 'F'
            if angle is None or isinstance(angle, str):
                angle = self.upright_angle(ref, side, down='1' if angle == 'pad1_down' else '2')
            self.place(ref, x, y, angle, side=side, region='fixed')
        for text, xy, size in SILKSCREEN:
            self.occupied['F'].append((f'TEXT:{text}', list(text_box(text, xy, size)), (0.3, 0.3)))
        # keep auto-placed parts off the rule areas and the via groups
        for area in rule_areas():
            box = [min(p[0] for p in area['polygon']), min(p[1] for p in area['polygon']), max(p[0] for p in area['polygon']), max(p[1] for p in area['polygon'])]
            for s in ('F', 'B'):
                if any(l in area['layers'] for l in (('F.Cu',) if s == 'F' else ('B.Cu',))):
                    self.occupied[s].append((f"AREA:{area['name']}", box, (0.0, 0.0)))
        for g in via_groups():
            (x0, y0), (px, py), (nx, ny) = g['origin'], g['pitch'], g['count']
            r = g.get('diameter', HV_VIA[0]) / 2
            box = [x0 - r, y0 - r, x0 + px * (nx - 1) + r, y0 + py * (ny - 1) + r]
            gap = HV_VIA_RING_GAP if g['net'] != 'SW' else 0.5  # island parts are SW-referenced (0.3 mm same-island rule)
            for s in ('F', 'B'):
                self.occupied[s].append((f"VIAS:{g['net']}", box, (gap, gap)))
        # in-pad HV vias of the fixed parts (HF tier PGND, chains, snubber) need the 3.0 mm outer rule on both sides; their HV
        # pads need it on their own side (plated-through pads on both)
        fixed_boxes = {key: b for key, b in pad_boxes(self.board).items() if key[0] in self.placements}
        # the gap an HV via / pad needs from the auto-placed parts depends on which island faces it: SW-group items (SW, SNUB_MID)
        # are same-reference to the HS island (0.3 mm) but 3 mm from the PGND-referenced islands east of the wall; PGND-group items
        # (PGND, PE_REF_MID) the other way round; VIN / VOUT potentials need 3 mm everywhere
        def island_gap(net, x):
            if net in ('SW', 'SNUB_MID'):
                return 0.5 if x < ISLAND_WALL_X[1] else HV_VIA_RING_GAP
            if net in ('PGND', 'PE_REF_MID'):
                return HV_VIA_RING_GAP if x < ISLAND_WALL_X[1] else 0.5
            return HV_VIA_RING_GAP
        for via in hv_pad_vias(fixed_boxes):
            r = via['diameter'] / 2
            box = [via['xy'][0] - r, via['xy'][1] - r, via['xy'][0] + r, via['xy'][1] + r]
            gap = island_gap(via['net'], via['xy'][0])
            for s in ('F', 'B'):
                self.occupied[s].append((f"HVVIA:{via['net']}", box, (gap, gap)))
        for (ref, number), b in fixed_boxes.items():
            if b['net'] not in HV_CLASS_NETS:
                continue
            gap = island_gap(b['net'], b['xy'][0])
            for s in (('F', 'B') if not b['smd'] else (b['layer'],)):
                self.occupied[s].append((f"HVPAD:{ref}.{number}", list(b['bbox']), (gap, gap)))
        # the barrier packages' escape copper (bars, fan legs, exact stubs and their vias) must stay clear of the auto-placed parts, and so
        # must the fans of the fixed fine-pitch strip parts
        fan_refs = tuple(BARRIER_REFS) + tuple(r for r in FAN_OBSTACLE_REFS if r in self.placements)
        for name, box, gap in escape_obstacles(fixed_boxes, refs=fan_refs):
            for s in (('B',) if name.startswith('ESCCOL') else ('F', 'B')):  # the bar-via exit corridors matter for the B.Cu island parts only
                self.occupied[s].append((name, box, gap))
        # landing areas of the explicit tap stubs (router ports): no auto-placed part may sit on a stub end
        for (ref, number), (length, (ux, uy), offset) in TAP_STUBS.items():
            b = fixed_boxes.get((ref, number))
            if not b:
                continue
            x, y = b['xy']
            extent = (b['bbox'][2] - b['bbox'][0]) / 2 if ux else (b['bbox'][3] - b['bbox'][1]) / 2
            ex, ey = x + ux * (extent + length) + (offset if uy else 0.0), y + uy * (extent + length) + (offset if ux else 0.0)
            for s in ('F', 'B'):
                self.occupied[s].append((f"PORT:{ref}.{number}", [min(x, ex) - 0.6, min(y, ey) - 0.6, max(x, ex) + 0.6, max(y, ey) + 0.9], (0.3, 0.3)))

    def anchors_for(self, part: dict, table: dict) -> dict:
        anchors: dict = {}
        for number, net in part['nets'].items():
            if not net or net in ('GND_CTRL', 'PGND', '3V3'):
                continue
            for (ref, pad_number), pad in table.items():
                if pad['net'] != net or ref == part['ref']:
                    continue
                weight = 4 if pad['kind'] in ('IC', 'Q', 'J', 'L') else 1
                entry = anchors.setdefault(net, [0, []])
                entry[0] = max(entry[0], weight)
                entry[1].append(pad['xy'])
        return anchors

    def search_position(self, part: dict, rects: list, table: dict, side: str, region: str):
        import numpy as np
        anchors = self.anchors_for(part, table)
        best = None
        for rect_index, rect in enumerate(rects):
            for angle in (0, 90, 180, 270):
                box, local_pads = self.pose_geometry(part['ref'], angle, side)
                gx, gy = self.gap_for(part, local_pads, region)
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
                for s in self.sides_for(part['ref'], side):  # a part with through features or in-pad vias must be clear on both sides
                    for oref, other, og in self.occupied[s]:
                        if oref.startswith('ESC'):  # escape copper of the barrier packages: its own clearance gap, no routing channel
                            ex, ey = og
                        else:
                            ex, ey = max(gx, og[0]), max(gy, og[1])
                        if oref == 'L1':  # the toroid's courtyard is a circle: keep the candidate box (plus gap) outside it
                            cx, cy = L1_CENTRE
                            nx_ = np.minimum(np.maximum(cx, X + box[0] - ex), X + box[2] + ex); ny_ = np.minimum(np.maximum(cy, Y + box[1] - ey), Y + box[3] + ey)
                            valid &= (nx_ - cx) ** 2 + (ny_ - cy) ** 2 > L1_COURTYARD_R ** 2
                            continue
                        valid &= ~((X + box[0] - ex < other[2]) & (X + box[2] + ex > other[0]) & (Y + box[1] - ey < other[3]) & (Y + box[3] + ey > other[1]))
                if not valid.any():
                    continue
                X, Y = X[valid], Y[valid]
                if region in PACK_REGIONS:
                    # shelf packing for the small, dense islands: fill the top row left to right, then the next row; the
                    # anchor (pin proximity) term is dropped - the islands are a few mm across and the router closes the gaps
                    cost = 4.0 * (Y - rect[1]) + (X - rect[0]) + 100.0 * rect_index  # earlier rectangles fill first
                    if region in NARROW_REGIONS:
                        cost = cost + 10.0 * (box[2] - box[0])  # one-row regions: stand the parts upright so more fit along the row
                elif anchors:
                    cost = np.zeros(X.shape)
                    total = 0.0
                    for net, (weight, points) in anchors.items():
                        offsets = [local_pads[n] for n, pn in part['nets'].items() if pn == net and n in local_pads]
                        if not offsets:
                            continue
                        net_cost = None
                        for ox, oy in offsets:
                            for ax, ay in points:
                                d = np.abs(X + ox - ax) + np.abs(Y + oy - ay)
                                net_cost = d if net_cost is None else np.minimum(net_cost, d)
                        cost += weight * net_cost
                        total += weight
                    cost /= max(total, 1e-9)
                else:
                    cost = np.abs(X - (rect[0] + rect[2]) / 2) + np.abs(Y - (rect[1] + rect[3]) / 2)
                # quantise the net-distance cost so that positions within PLACE_QUANT of the best are tied, then pack
                # towards the region's top-left corner: dense rows instead of parts scattered around their anchors
                if region not in PACK_REGIONS:
                    cost = np.floor(cost / PLACE_QUANT) * PLACE_QUANT + 1e-3 * ((X - rect[0]) + (Y - rect[1]))
                index = int(np.argmin(cost))
                score = (round(float(cost[index]), 6), angle, float(X[index]), float(Y[index]))
                if best is None or score < best:
                    best = score
        if best is None:
            inside = [ref for ref, other, _ in self.occupied[side] if any(boxes_overlap(other, r) for r in rects)]
            raise RuntimeError(f"no placement space for {part['ref']} ({part['footprint']}) in region {region} {rects} side {side}; inside: {inside}")
        return best

    def place_all(self) -> dict:
        self.place_fixed()
        remaining = [p for p in self.parts if p['ref'] not in self.placements]
        unassigned = [p['ref'] for p in remaining if p['ref'] not in ASSIGN_BY_REF]
        if unassigned:
            raise ValueError(f'parts without a region: {unassigned}')
        rank = {'IC': 0, 'Q': 0, 'L': 1, 'J': 1, 'C': 2, 'D': 3, 'R': 4, 'TP': 5}
        remaining.sort(key=lambda p: (rank.get(p['kind'], 6), -len([n for n in p['nets'].values() if n]), gr.natural_ref_key(p['ref'])))
        for part in remaining:
            region = ASSIGN_BY_REF[part['ref']]
            side, rects = REGIONS[region]
            table = self.placed_pads()
            # the region rectangles are hard bounds: they encode the 3 mm functional clearances to the other HV groups and the
            # barrier escape strips, so a full region is an error to fix in the floorplan, never grown into forbidden space
            best = self.search_position(part, [list(r) for r in rects], table, side, region)
            _, angle, x, y = best
            self.place(part['ref'], x, y, angle, side=side, region=region)
            if part['ref'] in FAN_OBSTACLE_REFS:  # its escape fan (legs and vias) keeps the later parts away
                boxes = {k: b for k, b in pad_boxes(self.board).items() if k[0] == part['ref']}
                for name, box, gap in escape_obstacles(boxes, refs=(part['ref'],)):
                    for s in ('F', 'B'):
                        self.occupied[s].append((name, box, gap))
        return self.placements

    # ----- graphics, rule areas, zones --------------------------------------------------------------------------------
    def add_outline_and_slots(self, slots: list[tuple]):
        pcb = self.pcb
        def edge(a, b):
            e = pcb.PCB_SHAPE(self.board)
            e.SetShape(pcb.SHAPE_T_SEGMENT)
            e.SetStart(self.point(*a)); e.SetEnd(self.point(*b))
            e.SetLayer(pcb.Edge_Cuts); e.SetWidth(pcb.FromMM(0.05))
            self.board.Add(e)
        for a, b in [((0, 0), (WIDTH, 0)), ((WIDTH, 0), (WIDTH, HEIGHT)), ((WIDTH, HEIGHT), (0, HEIGHT)), ((0, HEIGHT), (0, 0))]:
            edge(a, b)
        for x0, y0, x1, y1 in slots:  # closed inner outline = cut-out
            for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
                edge(a, b)

    def add_silkscreen(self):
        pcb = self.pcb
        records = []
        for text, xy, size in SILKSCREEN:
            item = pcb.PCB_TEXT(self.board)
            item.SetText(text)
            item.SetPosition(self.point(*xy))
            item.SetTextSize(self.point(size, size))
            item.SetTextThickness(pcb.FromMM(round(max(0.12, size * 0.15), 3)))
            item.SetLayer(pcb.F_SilkS)
            self.board.Add(item)
            bb = item.GetBoundingBox()
            box = [self.mm(bb.GetX()), self.mm(bb.GetY()), self.mm(bb.GetRight()), self.mm(bb.GetBottom())]
            for ref, other, _ in self.occupied['F']:
                if ref.startswith(('TEXT:', 'AREA:', 'VIAS:', 'VIA:', 'HVVIA:', 'HVPAD:', 'PORT:')) or ref == 'HS1':
                    continue
                if boxes_overlap(box, other):
                    raise ValueError(f'silkscreen text {text!r} overlaps the courtyard of {ref}')
            records.append(dict(text=text, xy=list(xy), size=size, bbox=[round(v, 3) for v in box]))
        return records

    def add_rule_area(self, name: str, layers, polygon, tracks=True, vias=True, pours=True):
        pcb = self.pcb
        z = pcb.ZONE(self.board)
        z.SetIsRuleArea(True)
        z.SetZoneName(name)
        lset = pcb.LSET()
        for layer in layers:
            lset.addLayer(self.board.GetLayerID(layer))
        z.SetLayerSet(lset)
        z.SetDoNotAllowTracks(bool(tracks)); z.SetDoNotAllowVias(bool(vias)); z.SetDoNotAllowZoneFills(bool(pours))
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        outline = z.Outline(); outline.NewOutline()
        for x, y in polygon:
            outline.Append(pcb.FromMM(x), pcb.FromMM(y))
        self.board.Add(z)
        return z

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


# --- board-level derived geometry -------------------------------------------------------------------------------------


def pad_boxes(board) -> dict:
    import pcbnew as pcb
    table = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNumber():
                bb = pad.GetBoundingBox()
                table[(fp.GetReference(), pad.GetNumber())] = dict(ref_pad=f'{fp.GetReference()}.{pad.GetNumber()}',
                                                                    bbox=[pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())],
                                                                    net=pad.GetNetname(), smd=pad.GetAttribute() == pcb.PAD_ATTRIB_SMD,
                                                                    xy=(pcb.ToMM(pad.GetPosition().x), pcb.ToMM(pad.GetPosition().y)),
                                                                    size=(pcb.ToMM(pad.GetSize().x), pcb.ToMM(pad.GetSize().y)),
                                                                    layer='B' if fp.IsFlipped() else 'F',
                                                                    centre=(pcb.ToMM(fp.GetPosition().x), pcb.ToMM(fp.GetPosition().y)))
    return table


BARRIER_REFS = ('U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U10')
# no in-pad vias: HF-tier / damping VIN pads (they sit in the F.Cu VIN+ pour; the through rings would block the B.Cu islands),
# 1206 chain ends (a via next to the stub leaving the other pad is < 3 mm: fed by patches or 3 mm stubs instead), LED PGND pads
NO_VIN_VIA_REFS = ('C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C16', 'C17', 'D3')
NO_INPAD_VIA_REFS = ('R4', 'R9', 'R59', 'R64', 'D1', 'D2', 'D5', 'R14', 'R15')  # R14 / R15: a PGND via beside the PE / MID pad breaks the 5 mm rule; the B.Cu column feeds the pad


ESC_GAP = 0.25  # copper edge of the escape items to the auto-placed courtyards (whose pads lie >= 0.23 mm inside): >= 0.48 mm to the pads
BAR_EXIT_CORRIDOR_MM = 2.2  # placer corridor above the HV-side bar vias (ends at y 136.2, just below the fixed bias rows' courtyards)


def escape_obstacles(boxes: dict, refs=BARRIER_REFS) -> list[tuple]:
    """Placer obstacles ``(name, box, gap)`` for the escape copper of ``refs`` (default: the barrier packages): fan legs, bars and
    their vias from fine_pitch_escapes, plus the exact stubs (with their stub-end vias) of the 1.27 mm rows, all with the ESC_GAP
    clearance to the auto-placed courtyards."""
    fixed = {k: b for k, b in boxes.items() if k[0] in refs}
    power = {z['net'] for z in zone_plan() if not z.get('post_route')}
    esc = fine_pitch_escapes(fixed, {r: True for r in refs}, power)
    out = []
    for t in esc['tracks']:
        w = t['width'] / 2
        out.append((f"ESC:{t['net']}", [min(t['a'][0], t['b'][0]) - w, min(t['a'][1], t['b'][1]) - w, max(t['a'][0], t['b'][0]) + w, max(t['a'][1], t['b'][1]) + w], (ESC_GAP, ESC_GAP)))
    bar_count = {}
    for v in esc['vias']:
        if v.get('bar') and v['xy'][1] < BARRIER_Y:
            bar_count[v['net']] = bar_count.get(v['net'], 0) + 1
    for v in esc['vias']:
        r = v['diameter'] / 2
        out.append((f"ESCVIA:{v['net']}", [v['xy'][0] - r, v['xy'][1] - r, v['xy'][0] + r, v['xy'][1] + r], (ESC_GAP, ESC_GAP)))
        if v.get('bar') and v['xy'][1] < BARRIER_Y and bar_count.get(v['net']) == 1:
            # the only HV-side bar via of its net (VDD_H / VDD_L / ISO_15V): a 2.2 mm exit corridor into the island stays free of auto-placed parts
            out.append((f"ESCCOL:{v['net']}", [v['xy'][0] - 0.55, v['xy'][1] - BAR_EXIT_CORRIDOR_MM, v['xy'][0] + 0.55, v['xy'][1]], (ESC_GAP, ESC_GAP)))
    vias = {tuple(p) for p in esc['exact_vias']}
    for ref, num, length in esc['exact']:
        b = fixed[(ref, num)]
        x, y = b['xy']
        cx, cy = b['centre']
        r = 0.3 if (ref, num) in vias else 0.125
        if abs(y - cy) >= abs(x - cx):  # rows along x: stubs leave the row along y (barrier packages)
            end_y = y + (1 if y > cy else -1) * ((b['bbox'][3] - b['bbox'][1]) / 2 + length)
            out.append((f"ESC:{b['net']}", [x - r, min(y, end_y) - r, x + r, max(y, end_y) + r], (ESC_GAP, ESC_GAP)))
        else:
            end_x = x + (1 if x > cx else -1) * ((b['bbox'][2] - b['bbox'][0]) / 2 + length)
            out.append((f"ESC:{b['net']}", [min(x, end_x) - r, y - r, max(x, end_x) + r, y + r], (ESC_GAP, ESC_GAP)))
    return out


def barrier_pad_rows(boxes: dict) -> list[tuple]:
    """Copper boxes (x0, y0, x1, y1) of the HV-side and SELV-side pad rows of every barrier package."""
    rows = []
    for ref in BARRIER_REFS:
        hv = [b['bbox'] for (r, n), b in boxes.items() if r == ref and b['bbox'][3] < BARRIER_Y]
        selv = [b['bbox'] for (r, n), b in boxes.items() if r == ref and b['bbox'][1] > BARRIER_Y]
        for group in (hv, selv):
            if group:
                rows.append((min(b[0] for b in group), min(b[1] for b in group), max(b[2] for b in group), max(b[3] for b in group)))
    return rows


def hv_pad_vias(boxes: dict) -> list[dict]:
    """In-pad HV vias for the SMD pads of the zone nets (PGND pads -> In1 pour, VIN pads -> In2, VOUT bars, SW snubber pad -> In2
    strip) sized to the pad. Each via carries ``pad=[ref, number]`` so the router skips exactly the pads that got one."""
    vias = []
    for (ref, number), b in sorted(boxes.items()):
        if not b['smd'] or b['net'] not in ('PGND', 'VIN', 'VOUT', 'SW'):
            continue  # VOUT_L has no inner copper (F.Cu bar only): no vias
        if ref in BARRIER_REFS and b['net'] == 'PGND':
            continue  # fine-pitch sensing-island PGND pads: bar vias / router fanout
        if ref in NO_INPAD_VIA_REFS or (ref in NO_VIN_VIA_REFS and b['net'] == 'VIN'):
            continue
        w, h = b['size']
        inner = min(w, h)
        if inner >= 1.7:
            d, drill = HV_VIA
        elif inner >= 1.1:
            d, drill = 0.8, 0.4
        elif inner >= 0.9:
            d, drill = 0.6, 0.3
        else:
            continue
        x, y = b['xy']
        if b['net'] == 'VOUT' and max(w, h) >= 4.0:  # TMCS1133 bar: one via at the HV-area end (the other end sits over the barrier strip)
            vias.append(dict(net=b['net'], xy=[snap(x), snap(y - 1.1)] if h > w else [snap(x - 1.1), snap(y)], diameter=d, drill=drill, pad=[ref, number]))
            continue
        vias.append(dict(net=b['net'], xy=[snap(x), snap(y)], diameter=d, drill=drill, pad=[ref, number]))
    return vias


def _segment_hits_pad(a, b, box, margin) -> bool:
    """True when the segment a-b (mm) comes within ``margin`` of the pad bounding box (sampled every 0.1 mm)."""
    x0, y0, x1, y1 = box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin
    length = max(math.dist(a, b), 1e-9)
    steps = max(1, int(length / 0.1))
    for i in range(steps + 1):
        t = i / steps
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False


def _pad_stub(a: dict, b: dict, layer: str):
    """Straight stub between two pad records of one net along their dominant axis, starting and ending CHAIN_TRACK_INSET
    inside the pad edges; None when the pads already overlap along that axis."""
    ax, ay = a['xy']; bx, by = b['xy']
    axis = 0 if abs(bx - ax) >= abs(by - ay) else 1
    sign = 1 if (bx, by)[axis] >= (ax, ay)[axis] else -1
    half_a = (a['bbox'][axis + 2] - a['bbox'][axis]) / 2
    half_b = (b['bbox'][axis + 2] - b['bbox'][axis]) / 2
    start = [ax, ay]; end = [bx, by]
    start[axis] += sign * max(0.0, half_a - CHAIN_TRACK_INSET)
    end[axis] -= sign * max(0.0, half_b - CHAIN_TRACK_INSET)
    if sign * (end[axis] - start[axis]) <= 0.05:
        return None
    return dict(net=a['net'], layer=layer, a=[round(start[0], 4), round(start[1], 4)], b=[round(end[0], 4), round(end[1], 4)], width=0.6)


def hv_chain_tracks(boxes: dict) -> tuple[list[dict], list[str]]:
    """Stubs joining the pads of the two-terminal HV chain nets that have no pour (bleeders, indicators, dividers, damping /
    snubber midpoints, PE link): consecutive pads of the same net joined by a straight 0.6 mm track that starts and ends
    CHAIN_TRACK_INSET inside the pad edges. The chain parts sit on the pin-field pitch, so each stub stays inside the two
    courtyards where the .kicad_dru pin-field exceptions apply, and the stubs flanking one part stay >= 3 mm apart. A link
    whose straight line would cross another pad is skipped and reported; DAMP_MID (two parallel RC legs sharing one
    midpoint) gets an explicit bypass along the board edge. Returns (tracks, issues)."""
    chains = ('BLD_IN_1', 'BLD_IN_2', 'IND_IN_1', 'IND_IN_2', 'IND_IN_3', 'BLD_OUT_1', 'IND_OUT_1', 'IND_OUT_2', 'VIN_DIV_T1', 'VIN_DIV_T2',
              'VIN_DIV_T3', 'VOUT_DIV_T1', 'DAMP_MID', 'SNUB_MID', 'PE_REF_MID')
    tracks, issues = [], []
    for net in chains:
        pads = sorted([b for b in boxes.values() if b['net'] == net], key=lambda b: (b['xy'][0], b['xy'][1]))
        layers = {b['layer'] for b in pads}
        for a, b in zip(pads, pads[1:]):
            layer = 'B.Cu' if a['layer'] == 'B' and b['layer'] == 'B' else 'F.Cu'
            if len(layers) > 1 and a['layer'] != b['layer']:
                continue  # mixed-side chain: left to the router
            stub = _pad_stub(a, b, layer)
            if stub is None:
                continue  # pads overlap along the axis: already joined by copper
            others = [o for o in boxes.values() if o['net'] != net and (o['layer'] == layer[0] or not o['smd'])]
            crossing = [o for o in others if _segment_hits_pad(stub['a'], stub['b'], o['bbox'], 0.3 + 0.3)]
            if crossing:
                issues.append(f"{net}: straight link skipped, it would cross {sorted(o.get('ref_pad', '?') for o in crossing)}")
                continue
            tracks.append(stub)
    # the indicator LEDs' PGND pads abut the bleeder chains' PGND pads (in-pad via in the 2512): join them with a stub
    for ra, na, rb, nb in (('R3', '2', 'D1', '1'), ('R8', '2', 'D2', '1')):
        a = boxes.get((ra, na)); b = boxes.get((rb, nb))
        if a and b and a['net'] == 'PGND' and b['net'] == 'PGND':
            stub = _pad_stub(a, b, 'F.Cu')
            if stub:
                tracks.append(stub)
    # DAMP_MID bypass: R12 pad 1 and R13 pad 1 face each other with the two PGND pads in between -> go round along the top edge
    r12 = boxes.get(('R12', '1')); r13 = boxes.get(('R13', '1'))
    if r12 and r13 and r12['net'] == 'DAMP_MID' and r13['net'] == 'DAMP_MID':
        y_edge = 1.4  # track edge 1.1 mm from the board edge (HV edge rule 1.0 mm), 3.1 mm from the 2512 pad tops
        (x1, y1), (x2, y2) = r12['xy'], r13['xy']
        tracks += [dict(net='DAMP_MID', layer='F.Cu', a=[x1, y1], b=[x1, y_edge], width=0.6),
                   dict(net='DAMP_MID', layer='F.Cu', a=[x1, y_edge], b=[x2, y_edge], width=0.6),
                   dict(net='DAMP_MID', layer='F.Cu', a=[x2, y_edge], b=[x2, y2], width=0.6)]
    return tracks, issues


def feed_stubs(boxes: dict) -> list[dict]:
    """F.Cu stubs from the ladder feed vias (via_groups: VIN west of R59, VOUT east of R64, VOUT below R9) to the end pads of
    the sense ladders / indicator chain: an in-pad via would sit 2.6 mm from the stub leaving the other pad of the 1206. The
    stub runs along the dominant axis from the via into the pad and ends CHAIN_TRACK_INSET inside the far pad edge."""
    tracks = []
    for ref, net, via_xy in (('R59', 'VIN', FEED_VIAS['R59']), ('R64', 'VOUT', FEED_VIAS['R64']), ('R9', 'VOUT', FEED_VIAS['R9'])):  # R64: into the VOUT F.Cu strip
        pad = boxes.get((ref, '1'))
        if not pad or pad['net'] != net:
            continue
        x, y = pad['xy']
        axis = 0 if abs(via_xy[0] - x) >= abs(via_xy[1] - y) else 1
        half = (pad['bbox'][axis + 2] - pad['bbox'][axis]) / 2
        end = [via_xy[0], y] if axis == 0 else [x, via_xy[1]]  # keep the stub straight along the axis
        start = list(via_xy)
        end[axis] = (x, y)[axis] - (half - CHAIN_TRACK_INSET) if via_xy[axis] < (x, y)[axis] else (x, y)[axis] + (half - CHAIN_TRACK_INSET)
        if axis == 0:
            start[1] = y
        else:
            start[0] = x
            tracks.append(dict(net=net, layer='F.Cu', a=[via_xy[0], via_xy[1]], b=[round(x, 4), via_xy[1]], width=0.6))  # jog onto the pad axis
        tracks.append(dict(net=net, layer='F.Cu', a=[round(start[0], 4), round(start[1], 4)], b=[round(end[0], 4), round(end[1], 4)], width=0.6))
    return tracks


def d5_sw_track(boxes: dict) -> list[dict]:
    """B.Cu feed of the LS DESAT diode drain pad (D5 pin 1, SW) from the Q2 drain pin (SW, plated through): the LS island has
    no SW copper on In2, so an in-pad via would dangle; the track leaves Q2 pin 1 downwards and bends to the pad."""
    q2 = boxes.get(('Q2', '1')); d5 = boxes.get(('D5', '1'))
    if not q2 or not d5 or q2['net'] != 'SW' or d5['net'] != 'SW':
        return []
    (qx, qy), (dx, dy) = q2['xy'], d5['xy']
    knee = [qx, snap(dy - 1.0)]
    return [dict(net='SW', layer='B.Cu', a=[qx, qy], b=knee, width=0.6), dict(net='SW', layer='B.Cu', a=knee, b=[dx, dy], width=0.6)]


def rt1_vin_raw_feed(boxes: dict) -> list[dict]:
    """r20 (LR-23): 2.0 mm B.Cu VIN_RAW track from the J1 / J5 VIN_RAW pour (x <= VIN_RAW_X1) along RT1_FEED_Y, north of the input
    return terminal J2's pin field, then south into the PTC's VIN_RAW pad (RT1.1, plated). VIN_RAW is never routed by the grid router;
    the PGND B.Cu column is clipped 3 mm around the track by the filler."""
    pad = boxes.get(('RT1', '1'))
    if not pad or pad['net'] != 'VIN_RAW':
        return []
    x, y = pad['xy']
    j1 = [b for (r, n), b in boxes.items() if r == 'J1' and b['net'] == 'VIN_RAW']
    start_y = round(min(b['bbox'][1] for b in j1) + 0.5, 4) if j1 else 106.0  # inside the pour and the J1 pin field (same net)
    rise = [RT1_FEED_X0, RT1_FEED_Y]
    knee = [round(x, 4), RT1_FEED_Y]
    return [dict(net='VIN_RAW', layer='B.Cu', a=[RT1_FEED_X0, start_y], b=rise, width=2.0),
            dict(net='VIN_RAW', layer='B.Cu', a=rise, b=knee, width=2.0),
            dict(net='VIN_RAW', layer='B.Cu', a=knee, b=[round(x, 4), round(y, 4)], width=2.0)]


def pe_pre_route(boxes: dict) -> tuple[list[dict], list[list]]:
    """PE on B.Cu: a 2.0 mm spine from the PE stud H1 along PE_SPINE_X (5 mm east of every HV_PGND item of the link column) down to
    the lowest PE pad, with 1.0 mm stubs west to the plated Y-capacitor pads and the B.Cu PE pads of the link resistors; the 5 mm
    HV-to-PE rule against the pours is kept by the filler (it clips the PGND B.Cu column and top band around the PE copper).
    Returns (tracks, pads to skip); the router never touches PE (skip_nets)."""
    pe = {k: b for k, b in boxes.items() if b['net'] == 'PE'}
    if not pe:
        return [], []
    spine_x = PE_SPINE_X
    stud = max(pe.values(), key=lambda b: max(b['size']))  # the M4 stud pad
    sx, sy = stud['xy']; stud_r = max(stud['size']) / 2
    tracks = []
    smd = sorted((b for b in pe.values() if b['smd'] and b['layer'] == 'B'), key=lambda b: b['xy'][1])
    bottom = max(b['xy'][1] for b in smd) if smd else sy
    tracks.append(dict(net='PE', layer='B.Cu', a=[round(sx + stud_r - 0.6, 3), sy], b=[spine_x, sy], width=2.0))  # stud -> spine
    tracks.append(dict(net='PE', layer='B.Cu', a=[spine_x, sy], b=[spine_x, bottom], width=2.0))
    for b in smd:
        x, y = b['xy']; half = (b['bbox'][2] - b['bbox'][0]) / 2
        if abs(y - bottom) < 0.05:  # the lowest link pad: stub from inside its east edge to the spine
            tracks.append(dict(net='PE', layer='B.Cu', a=[round(x + half - 0.5, 3), y], b=[spine_x, y], width=1.0))
        else:  # a higher link pad (vertical R16): straight down to the lowest pad's row, away from its own MID pad
            tracks.append(dict(net='PE', layer='B.Cu', a=[x, y], b=[x, bottom], width=1.0))
    for b in pe.values():  # plated Y-capacitor PE pads: overlap the stud pad or reach it with a vertical stub
        if b['smd'] or b is stud:
            continue
        x, y = b['xy']
        if math.dist((x, y), (sx, sy)) <= stud_r + max(b['size']) / 2 - 0.3:
            continue  # the pad overlaps the stud pad
        tracks.append(dict(net='PE', layer='B.Cu', a=[x, y], b=[x, round(sy + (stud_r - 0.6) * (1 if y > sy else -1), 3)], width=1.0))
    return tracks, [[ref, num] for (ref, num) in sorted(pe)]


def fine_pitch_escapes(boxes: dict, footprints: dict, power_nets: set) -> dict:
    """Escape plan for the fine-pitch pad rows (barrier packages, VSSOP). Consecutive same-net pads of a row are bridged by a pad-wide
    bar and escape through ONE 0.6/0.3 via beyond the row end (in line with the middle pad of a run of three or more, between the two
    pads of a pair). Single pads: on 1.27 mm rows an exact straight stub whose length alternates along the row (the grid-snap jogs
    never face each other) with a via at its end (``exact_vias``: a port on every routing layer); on 0.65 mm rows, where no via fits
    in line, each group of consecutive singles escapes through a fan (see FAN_DEPTH_MM) ending in one via per pad. Plane-net pads at
    the end of a coarse row keep the fanout's via escape (it can shift sideways). SELV-side ports (stub vias and fan vias) carry a
    reserved exit lane into the fan-out corridor (``exact_lanes`` / via ``lane``). Returns dict(tracks, vias, skip, exact, exact_vias,
    exact_lanes, widths, issues)."""
    rows = {}
    for (ref, num), b in boxes.items():
        if not b['smd'] or not num or ref not in footprints:
            continue
        rows.setdefault(ref, []).append((num, b))
    out = dict(tracks=[], vias=[], skip=[], exact=[], exact_vias=[], exact_lanes=[], widths={}, issues=[])
    for ref, pads in sorted(rows.items()):
        if len(pads) < 3:
            continue
        xs = sorted({round(b['xy'][0], 3) for _, b in pads}); ys = sorted({round(b['xy'][1], 3) for _, b in pads})
        along_x = len(xs) >= len(ys)  # rows run along x (packages rotated +-90) or along y
        key = (lambda b: round(b['xy'][1], 2)) if along_x else (lambda b: round(b['xy'][0], 2))
        pos = (lambda b: b['xy'][0]) if along_x else (lambda b: b['xy'][1])
        groups = {}
        for num, b in pads:
            groups.setdefault(key(b), []).append((num, b))
        pitch = None
        for row in groups.values():
            ps = sorted(pos(b) for _, b in row)
            gaps = [q - p for p, q in zip(ps, ps[1:]) if q - p > 0.05]
            if gaps:
                pitch = min(gaps) if pitch is None else min(pitch, min(gaps))
        if pitch is None or pitch >= (BARRIER_ROW_PITCH_MM if (ref in BARRIER_REFS or ref in STUB_ROW_REFS) else FINE_PITCH_MM):
            continue
        coarse = pitch >= FINE_PITCH_MM  # 1.27 mm barrier rows: stubs with vias; finer rows: fans
        bar_depth = BAR_VIA_DEPTH_BY_REF.get(ref, BAR_VIA_DEPTH_MM)
        for row_key, row in groups.items():
            row = sorted(row, key=lambda item: pos(item[1]))
            cx, cy = row[0][1]['centre']
            layer = 'F.Cu' if row[0][1]['layer'] == 'F' else 'B.Cu'
            selv_side = row_key > BARRIER_Y if along_x else row[0][1]['xy'][1] > BARRIER_Y
            outward = (1 if row_key > (cy if along_x else cx) else -1)
            axis = 0 if along_x else 1  # along-row axis
            row_centre = row[0][1]['xy'][1] if along_x else row[0][1]['xy'][0]  # exact pad coordinate across the row
            extent = (row[0][1]['bbox'][3] - row[0][1]['bbox'][1]) / 2 if along_x else (row[0][1]['bbox'][2] - row[0][1]['bbox'][0]) / 2

            def pt(along, depth):
                """Board point (mm) at an along-row coordinate and a depth beyond the pad end (negative: inside the pad)."""
                across = round(row_centre + outward * (extent + depth), 4)
                return [round(along, 4), across] if along_x else [across, round(along, 4)]
            for _, b in row:
                if b['net'] and not b['net'].startswith('unconnected-'):
                    out['widths'][b['net']] = 0.25
            runs = []
            i = 0
            while i < len(row):
                j = i
                while j + 1 < len(row) and row[j + 1][1]['net'] == row[i][1]['net']:
                    j += 1
                runs.append(row[i:j + 1])
                i = j + 1
            stub_index = 0
            fan_group: list = []

            def emit_fan(group):
                """Fan escape of consecutive singles (pads sorted along the row): legs sideways for the outer pads, deeper for the inner."""
                k = len(group)
                depth1 = FAN_DEPTH_MM if ref in BARRIER_REFS else FAN_DEPTH_STRIP_MM
                leg = FAN_LEG_MM
                depth2 = depth1 + leg
                ps = [pos(b) for _, b in group]
                if k == 1:
                    plans = [[(ps[0], depth1)]]
                elif k == 2:
                    plans = [[(ps[0], depth1), (ps[0] - leg, depth1)], [(ps[1], depth1), (ps[1] + leg, depth1)]]
                elif k == 3:
                    plans = [[(ps[0], depth1), (ps[0] - leg, depth1)], [(ps[1], depth1 + FAN_STEP_MM)], [(ps[2], depth1), (ps[2] + leg, depth1)]]
                elif k == 4:
                    plans = [[(ps[0], depth1), (ps[0] - leg, depth1)], [(ps[1], depth2), (ps[1] - leg, depth2)],
                             [(ps[2], depth2), (ps[2] + leg, depth2)], [(ps[3], depth1), (ps[3] + leg, depth1)]]
                else:
                    out['issues'].append(f"{ref}: {k} consecutive single pads in a {pitch:.2f} mm row - alternating stubs without vias")
                    for n, (num, b) in enumerate(group):
                        out['exact'].append([ref, num, EXACT_STUB_HV_MM[n % 2]])
                    return
                for (num, b), waypoints in zip(group, plans):
                    net = b['net']
                    points = [pt(ps[group.index((num, b))], -0.55 * extent)] + [pt(a, d) for a, d in waypoints]
                    for a, z in zip(points, points[1:]):
                        if a != z:
                            out['tracks'].append(dict(net=net, layer=layer, a=a, b=z, width=0.25, mark_width=0.3))
                    via = dict(net=net, xy=points[-1], diameter=VIA[0], drill=VIA[1], port=True)
                    if selv_side and ref in BARRIER_REFS:  # exit lane into the fan-out corridor (away from the body)
                        via['lane'] = [0 if along_x else outward, outward if along_x else 0, BARRIER_SELV_LANE_MM, layer]
                    out['vias'].append(via)
                    out['skip'].append([ref, num])

            def flush():
                if fan_group:
                    emit_fan(list(fan_group))
                    fan_group.clear()
            for k, run in enumerate(runs):
                net = run[0][1]['net']
                if not net or net.startswith('unconnected-') or net in SKIP_ESCAPE_NETS:
                    flush()
                    continue
                if len(run) > 1:
                    flush()
                    a, z = list(run[0][1]['xy']), list(run[-1][1]['xy'])
                    bar_w = round(min(run[0][1]['size']) - 0.05, 2)
                    a[axis] += 0.1; z[axis] -= 0.1  # end caps stay 0.3 mm (class clearance) from the next group's bar
                    out['tracks'].append(dict(net=net, layer=layer, a=a, b=z, width=bar_w, mark_width=bar_w + 0.15))
                    lateral = pos(run[len(run) // 2][1]) if len(run) >= 3 else (pos(run[0][1]) + pos(run[1][1])) / 2
                    via_xy = pt(lateral, bar_depth)
                    bar_point = [lateral, row_centre] if along_x else [row_centre, lateral]
                    out['tracks'].append(dict(net=net, layer=layer, a=bar_point, b=via_xy, width=0.25, mark_width=0.4))
                    out['vias'].append(dict(net=net, xy=via_xy, diameter=VIA[0], drill=VIA[1], port=True, bar=True))
                    for num, _ in run:
                        out['skip'].append([ref, num])
                    continue
                num, b = run[0]
                if coarse:
                    flush()
                    row_end = k == 0 or k == len(runs) - 1
                    if net in power_nets and row_end:
                        continue  # plane net at the row end: the fanout places a via shifted away from the row
                    if net in power_nets:
                        out['issues'].append(f'{ref}.{num} {net}: plane net pad between two foreign pads of a coarse row gets a stub only')
                    lengths = EXACT_STUB_SELV_MM if (selv_side and ref in BARRIER_REFS) else EXACT_STUB_HV_BY_REF.get(ref, EXACT_STUB_HV_MM)
                    out['exact'].append([ref, num, lengths[stub_index % 2]])
                    out['exact_vias'].append([ref, num])
                    if selv_side and ref in BARRIER_REFS:
                        out['exact_lanes'].append([ref, num, BARRIER_SELV_LANE_MM])
                    stub_index += 1
                    continue
                fan_group.append((num, b))
            flush()
    return out


CONNECTOR_STUB_END_Y = {'outer': 162.05, 'inner': 163.3, 'inner_plane': 161.6, 'inner_north': 155.9}  # mezzanine-pin escape stub ends south of the socket: outer-row pins straight, inner-row signal pins half a pitch deeper (via rows 1.78 mm apart); inner-row plane pins (GND_CTRL) stop right below the outer pads (via ring 0.45 mm from them) so they add no port to the exit band
CONNECTOR_JOG_MM = 1.27  # an inner-row pin jogs half a pitch west first and passes between the outer row's pins (0.295 mm to each pad)
CONNECTOR_NORTH_PINS = {'J7': ('30', '32', '36')}  # inner-row signal pins whose nets live north of the socket (PG_BIAS_S_N -> U5.3, PG_BIAS_H_N -> U2.3, SPARE_D1 -> TP12 in the corridor): straight north stub + via, which also removes three interleaved ports from the south exit band


def connector_stubs(boxes: dict, power_nets: set, refs=('J7',)) -> tuple[list[list], list[dict], list[list]]:
    """Mezzanine-socket escapes: every connected pin leaves the socket southwards on B.Cu, so the fan-out corridor north of the socket
    stays free for the barrier packages' escapes and the east-west buses, and the strip south of the socket is reached without
    crossing the pin rows (1.7 mm pads on a 2.54 mm pitch leave no routable gap on the grid).

    Returns ``(specs, links, skip)``: exact-stub specs ``[ref, pad, length, [ux, uy], offset, layer]`` (outer-row pins straight
    south to CONNECTOR_STUB_END_Y['outer'], inner-row pins jogging CONNECTOR_JOG_MM west and running between the outer row's pins to
    CONNECTOR_STUB_END_Y['inner']; the router puts a via at every stub end), pre-routed ``links`` (a straight B.Cu track from an
    inner pin to the outer pin of the same net in its column, which then carries the only stub) and the pads those links replace.
    Plane pins (GND_CTRL) escape the same way; their via reaches the In1 pour."""
    specs, links, skip = [], [], []
    for ref in refs:
        pads = {num: b for (r, num), b in boxes.items() if r == ref and b['net'] and not b['net'].startswith('unconnected-')}
        if not pads:
            continue
        rows = sorted({round(b['xy'][1], 2) for b in pads.values()})
        mid = (rows[0] + rows[-1]) / 2
        columns: dict = {}
        for num, b in sorted(pads.items(), key=lambda kv: gr.pad_sort_key(kv[0])):
            columns.setdefault(round(b['xy'][0], 2), {})['outer' if b['xy'][1] > mid else 'inner'] = (num, b)
        for x in sorted(columns, reverse=True):
            col = columns[x]
            inner, outer = col.get('inner'), col.get('outer')
            if inner and outer and inner[1]['net'] == outer[1]['net']:  # same net in one column: link them, one stub from the outer pin
                a, z = inner[1]['xy'], outer[1]['xy']
                links.append(dict(net=inner[1]['net'], layer='B.Cu', a=[round(a[0], 4), round(a[1], 4)], b=[round(z[0], 4), round(z[1], 4)], width=0.25))
                skip.append([ref, inner[0]])
                inner = None
            if outer:
                num, b = outer
                extent = (b['bbox'][3] - b['bbox'][1]) / 2
                specs.append([ref, num, round(CONNECTOR_STUB_END_Y['outer'] - b['xy'][1] - extent, 3), [0, 1], 0.0, 'B.Cu'])
            if inner:
                num, b = inner
                extent = (b['bbox'][3] - b['bbox'][1]) / 2
                if num in CONNECTOR_NORTH_PINS.get(ref, ()):  # net north of the socket: straight north into the corridor
                    specs.append([ref, num, round(b['xy'][1] - extent - CONNECTOR_STUB_END_Y['inner_north'], 3), [0, -1], 0.0, 'B.Cu'])
                    continue
                end = CONNECTOR_STUB_END_Y['inner_plane' if b['net'] in power_nets else 'inner']
                specs.append([ref, num, round(end - b['xy'][1] - extent, 3), [0, 1], -CONNECTOR_JOG_MM, 'B.Cu'])
    return specs, links, skip


CONNECTOR_PORT_BOX = (0.8, 1.5)  # half-width along the pin row and depth beyond the stub end of the net-coded box that keeps a socket port open


def connector_port_keepouts(boxes: dict, stubs: list[list]) -> list[dict]:
    """Net-coded B.Cu keep-outs (vias blocked) around the socket stub ends: CONNECTOR_PORT_BOX half-width either side of the stub
    and its depth beyond the end, so no other net's track or via centre can sit on the port while it waits for its turn."""
    keepouts = []
    half, depth = CONNECTOR_PORT_BOX
    for ref, num, length, (ux, uy), offset, layer in stubs:
        b = boxes.get((ref, num))
        if not b:
            continue
        x = b['xy'][0] + offset
        extent = (b['bbox'][3] - b['bbox'][1]) / 2
        end_y = b['xy'][1] + uy * (extent + length)
        rect = [x - half, min(end_y - 0.3, end_y + uy * depth), x + half, max(end_y + 0.3, end_y + uy * depth)]
        keepouts.append(dict(layer=layer, rect=[round(v, 3) for v in rect], net=b['net'], vias=True))
    return keepouts


def route_regions(boxes: dict) -> dict:
    """Per-net routing regions ({layer: [rects]}) for the grid router: the two driver islands, the sensing island and the SELV
    strip, each extended by its barrier packages' pad-row notches. Rect edges are inset 0.6 mm from every 3 mm boundary to a
    foreign HV group (track half-width 0.5 mm plus grid rounding), so copper centred inside a region keeps the outer-layer rule;
    vias may sit only where the F.Cu and the B.Cu rect sets overlap (their annuli lie on both outer layers)."""
    hv_max, selv_min = HV_COPPER_MAX_Y, SELV_COPPER_MIN_Y
    notches = {}
    for ref in BARRIER_REFS:
        hv = [b['bbox'] for (r, n), b in boxes.items() if r == ref and b['bbox'][3] < BARRIER_Y]
        selv = [b['bbox'] for (r, n), b in boxes.items() if r == ref and b['bbox'][1] > BARRIER_Y]
        if hv:
            notches[(ref, 'hv')] = [min(b[0] for b in hv) - 0.3 + NOTCH_INSET, hv_max, max(b[2] for b in hv) + 0.3 - NOTCH_INSET, max(b[3] for b in hv) + 0.3]
        if selv:
            notches[(ref, 'selv')] = [min(b[0] for b in selv) - 0.3 + NOTCH_INSET, min(b[1] for b in selv) - 0.3, max(b[2] for b in selv) + 0.3 - NOTCH_INSET, selv_min]
    wall_w, wall_e = ISLAND_WALL_X
    hs_notch = [notches[(r, 'hv')] for r in ('U1', 'U2') if (r, 'hv') in notches]
    ls_notch = [notches[(r, 'hv')] for r in ('U3', 'U4') if (r, 'hv') in notches]
    sense_notch = [notches[(r, 'hv')] for r in ('U5', 'U6', 'U7') if (r, 'hv') in notches]
    selv_notch = [notches[(r, 'selv')] for r in BARRIER_REFS if (r, 'selv') in notches]
    hs = {'F.Cu': [[91.9, 129.0, wall_w, hv_max], [66.5, VIN_BAND_CUT_Y + 3.5, D3_TAB[0] - 3.6, hv_max], [D3_TAB[0] - 3.6, D3_TAB[3] + 3.6, 91.9, hv_max]] + hs_notch,
          'B.Cu': [[64.6, ISLAND_TOP_Y, 82.45, hv_max], [82.45, 131.85, wall_w, hv_max], [91.55, ISLAND_TOP_Y, wall_w, 131.85], [92.5, 120.5, 104.5, ISLAND_TOP_Y]] + hs_notch,
          'In2.Cu': [[64.6, ISLAND_TOP_Y, wall_w, hv_max]]}
    # the LS island and the sensing islands are both PGND-referenced (0.3 mm between their nets): one shared region, 3 mm from the
    # SW copper (block, D5, snubber), the VIN / VOUT ladders and feed vias and the VOUT F.Cu strip
    pg = {'F.Cu': [[124.0, 131.9, 168.0, hv_max], [wall_e, 137.0, 124.0, hv_max], [155.5, 123.1, 168.0, 131.9], [125.0, 123.2, 139.9, 131.9],
                   [166.5, 136.4, 199.4, hv_max]] + ls_notch + sense_notch,
          'B.Cu': [[123.9, 128.6, 168.0, hv_max], [wall_e, 137.0, 123.9, hv_max], [121.5, 120.0, 139.9, 128.6], [155.5, 112.0, 168.0, 128.6],
                   [166.5, 133.0, 199.4, hv_max]] + ls_notch + sense_notch,
          'In2.Cu': [[wall_e + 1.0, ISLAND_TOP_Y, 153.0, hv_max]]}
    ls = sense = pg
    # the strip routes on all three layers: In2 under the strip carries the 3V3 post-route pour, which the SELV tracks may cut
    selv = {'F.Cu': [[0.5, selv_min, WIDTH - 0.5, HEIGHT - 0.5]] + selv_notch, 'B.Cu': [[0.5, selv_min, WIDTH - 0.5, HEIGHT - 0.5]] + selv_notch,
            'In2.Cu': [[0.5, selv_min, WIDTH - 0.5, HEIGHT - 0.5]]}
    regions = {}
    for net in HS_NETS:
        regions[net] = hs
    for net in LS_NETS:
        regions[net] = ls
    for net in SENSE_NETS:
        regions[net] = sense
    power = {z['net'] for z in zone_plan() if not z.get('post_route')} | {'PE'} | set(HV_CLASS_NETS)
    for net in sorted({b['net'] for b in boxes.values() if b['net'] and not b['net'].startswith('unconnected-')}):
        if net not in regions and net not in power:
            regions[net] = selv
    # r20 (LR-24): the LS gate-loop nets stay on B.Cu over the KS_L In2 pour as the HS side does (a layer missing from the dict is closed
    # for the net, so no via): their ports are the U3 stub-end vias (all layers), the B.Cu gate network pads and the plated Q2 / TP2 pins
    for net in LS_GATE_LOOP_NETS:
        regions[net] = {'B.Cu': pg['B.Cu']}
    # r20 (LR-26): each AMC1311 differential output pair runs on one layer (F.Cu) from the stub-end vias to the OPA2320 networks
    for net in AMC_PAIR_NETS:
        if net in regions:
            regions[net] = {'F.Cu': selv['F.Cu']}
    return regions


def inward_escape_pads(boxes: dict, refs=INWARD_REFS) -> list[list]:
    """[ref, pad] of the routed-net pads of ``refs`` whose fanout via goes towards the footprint centre (under the body)."""
    return [[ref, num] for (ref, num), b in sorted(boxes.items()) if ref in refs and b['net'] and not b['net'].startswith('unconnected-')]


def routing_plan(save: Path, extra_tracks, extra_vias, skip_pads, keepouts, net_rules=None, exact_stub_pads=(), trials=None, ripup=None,
                 direct_nets=(), inward_pads=(), exact_via_pads=(), direct_lane=0.0, exact_lane_pads=(), style=None) -> dict:
    # grid_router zones: one plan entry per polygon, each with its own priority / clearance (the first polygon of a net is the
    # base entry, the others become 'NET#i' entries resolved by the zone stage below); post-route zones are added after routing
    plan_power, counters = {}, {}
    for z in zone_plan():
        if z.get('post_route'):
            continue
        entry = dict(stubs=False, priority=z['priority'], clearance=z['clearance'], min_thickness=ZONE_MIN_THICKNESS, zones={z['layer']: z['polygon']})
        if z['net'] not in plan_power:
            plan_power[z['net']] = entry
        else:
            counters[z['net']] = counters.get(z['net'], 0) + 1
            plan_power[f"{z['net']}#{counters[z['net']]}"] = entry
    return {
        'board': {'width': WIDTH, 'height': HEIGHT, 'margin': BOARD_MARGIN},
        'layers': list(ROUTING_LAYERS), 'grid': GRID, 'trace': TRACE, 'clearance': CLEARANCE, 'via': list(VIA), 'hole_clearance': HOLE_CLEARANCE,
        'directions': [None] * len(ROUTING_LAYERS),
        'net_rules': {k: dict(v) for k, v in (net_rules or NET_RULES).items()},
        'keepouts': keepouts,
        'pre_routed': {'tracks': extra_tracks, 'vias': extra_vias},
        'fanout': {'order': ['U1', 'U3', 'U2', 'U4', 'U5', 'U6', 'U7', 'U10', 'U8', 'U9'], 'skip_refs': ['HS1'], 'skip_pads': skip_pads,
                   'exact_stub_pads': [list(p) for p in exact_stub_pads], 'escape_layer': 'B.Cu', 'direct_nets': list(direct_nets or ()),
                   'inward_pads': [list(p) for p in inward_pads], 'exact_via_pads': [list(p) for p in exact_via_pads], 'direct_lane_mm': float(direct_lane),
                   'exact_lane_pads': [list(p) for p in exact_lane_pads],
                   'skip_nets': list(SKIP_ESCAPE_NETS)},
        'critical': [], 'critical_layers': list(ROUTING_LAYERS),
        'power': plan_power,
        'signal_order': list(SIGNAL_ORDER), 'signal_pinned': list(SIGNAL_PINNED), 'signal_layers': list(ROUTING_LAYERS), 'front_fallback': True,
        'signal_groups': [list(HS_NETS), list(LS_NETS) + list(SENSE_NETS)],  # HS island, PGND-referenced islands, then the SELV strip: each keeps its own best order
        'ground': None,
        'prune_vias': True, 'fill': True, 'save': str(save), 'strict': False, 'max_nodes': MAX_NODES,
        'signal_order_trials': SIGNAL_ORDER_TRIALS if trials is None else int(trials),
        'ripup_rounds': RIPUP_ROUNDS if ripup is None else int(ripup),
        **({'style': dict(style)} if style else {}),  # V2.1 geometry; absent = the V2 plan
    }


def router_keepouts(boxes: dict, areas: list[dict]) -> list[dict]:
    """Grid-router keep-outs: island wall, ISO_BARRIER strip with notch-aware edges, rule areas, HV pours on the outer routing layers
    (net-coded, vias blocked), the In2.Cu zone keep-out everywhere outside the two island windows (the In2 pours: tracks stay out,
    via barrels pass) and 3 mm halos around the ladder feed vias."""
    keepouts = [dict(layer=None, rect=[ISLAND_WALL_X[0], 119.0, ISLAND_WALL_X[1], HV_LIMIT_Y], net=None, vias=True)]  # island wall
    edge = TRACE / 2 + 0.35  # a track centred just outside a rule area still intersects it: inflate the router boxes
    rows = barrier_pad_rows(boxes)
    for area in areas:
        poly = area['polygon']
        if area['name'] == 'ISO_BARRIER':
            keepouts.append(dict(layer=None, rect=[0.0, ISO_STRIP[0] + 0.5, WIDTH, 149.0], net=None, vias=True))
            # the strip edges outside the pad-row notches: HV-side copper ends at HV_COPPER_MAX_Y, SELV copper starts at SELV_COPPER_MIN_Y
            for side_y, (ya, yb) in (('hv', (HV_COPPER_MAX_Y, ISO_STRIP[0] + 0.5)), ('selv', (149.0, SELV_COPPER_MIN_Y))):
                notches = sorted((r[0] - 0.3 + NOTCH_INSET, r[2] + 0.3 - NOTCH_INSET) for r in rows if (r[1] < BARRIER_Y) == (side_y == 'hv'))  # inside the rule-area notch
                x = 0.0
                for x0, x1 in notches:
                    if x0 > x:
                        keepouts.append(dict(layer=None, rect=[x, ya, x0, yb], net=None, vias=True))
                    x = max(x, x1)
                keepouts.append(dict(layer=None, rect=[x, ya, WIDTH, yb], net=None, vias=True))
            continue
        box = [min(p[0] for p in poly) - edge, min(p[1] for p in poly) - edge, max(p[0] for p in poly) + edge, max(p[1] for p in poly) + edge]
        for layer in area['layers']:
            if layer in ROUTING_LAYERS:
                keepouts.append(dict(layer=layer, rect=box, net=None, vias=True))
    # HV pours on the outer routing layers are reserved for their own net: a foreign track or via inside a pour would be clipped
    # 3 mm around by the filler, fragmenting the pour and violating the class-pair rules; the PGND B.Cu pours stay open
    for z in zone_plan():
        if z['layer'] not in ('F.Cu', 'B.Cu') or z.get('post_route') or not z.get('router_keepout', True):
            continue
        rects = z.get('keepout_rects')
        if rects is None:
            xs = [p[0] for p in z['polygon']]; ys = [p[1] for p in z['polygon']]
            rects = [[min(xs), min(ys), max(xs), max(ys)]]
        for r in rects:
            keepouts.append(dict(layer=z['layer'], rect=list(r), net=z['net'], vias=True))
    # In2.Cu carries pours everywhere except under the driver islands (Kelvin pours of nets that are also routed): zone keep-out
    # outside the two island windows, so In2 tracks exist only inside the islands while via barrels pass anywhere
    w0, w1 = 64.6, ISLAND_WALL_X[0]
    e0, e1 = ISLAND_WALL_X[1] + 1.0, 153.0
    y0, y1 = ISLAND_TOP_Y, HV_COPPER_MAX_Y
    for rect in ([0.0, 0.0, WIDTH, y0], [0.0, y1, WIDTH, SELV_COPPER_MIN_Y], [0.0, y0, w0, y1], [w1, y0, e0, y1], [e1, y0, WIDTH, y1]):  # the SELV strip (3V3 post-route pour) stays open
        keepouts.append(dict(layer='In2.Cu', rect=rect, net=None, vias=False, zone=True))
    # ladder feed vias and stubs: 3 mm outer rule against the sensing-island escapes
    for g in via_groups():
        if g['count'] == (1, 1):
            x0, y0 = g['origin']; r = g.get('diameter', HV_VIA[0]) / 2 + 3.0
            keepouts.append(dict(layer=None, rect=[x0 - r, y0 - r, x0 + r, y0 + r], net=g['net'], vias=True))
    return keepouts


def build_power(output_pcb: Path, *, route=True, drc=True, metrics=True, cli=None, trials=None, ripup=None, style=None, outputs=None) -> dict:
    """Place, route, zone, check and DRC the power board into ``output_pcb``. ``style``: grid_router V2.1 ``style`` block
    (None = ``ROUTING_STYLE``, {} = V2 geometry, ``ROUTING_STYLE_V21`` = the 8-direction block). ``outputs``: None = the example's
    design/ and verification/ folders; a directory = scratch build (candidate comparison) whose netlist, placement, routing plan,
    progress JSON, engineering checks (``engineering_checks/``) and DRC manifests (``drc/``) are written there instead - the
    output board still needs the project files (.kicad_pro / .kicad_dru / schematics / libraries) next to it for the parity DRC."""
    import pcbnew as pcb
    start = time.monotonic()
    outputs = Path(outputs) if outputs is not None else None
    checks_dir = CHECKS_DIR if outputs is None else outputs / 'engineering_checks'
    drc_dir = DRC_DIR if outputs is None else outputs / 'drc'
    parts = load_parts()
    mapping = json.loads(MAPPING_JSON.read_text(encoding='utf-8'))['paths']
    cli = cli or find_kicad_cli()
    pin_nets = export_netlist(KICAD_DIR / f'{NAME}.kicad_sch', (DESIGN_DIR if outputs is None else outputs) / 'netlist_power.xml', cli)
    builder = Builder(parts, mapping, pin_nets)
    placements = builder.place_all()
    boxes = pad_boxes(builder.board)
    slots: list[tuple] = []  # every barrier footprint (UCC14141 DWN, UCC21710 DW, AMC1311 DWV, TMCS1133 DVG) carries its own NPTH slot
    builder.add_outline_and_slots(slots)
    silkscreen = builder.add_silkscreen()
    areas = rule_areas()
    areas.append(dict(name='ISO_BARRIER', layers=COPPER_LAYERS, polygon=iso_barrier_polygon(barrier_pad_rows(boxes)), tracks=True, vias=True, pours=True))
    for area in areas:
        builder.add_rule_area(area['name'], area['layers'], area['polygon'], area['tracks'], area['vias'], area['pours'])
    loaded = builder.save(output_pcb)
    result = dict(board=str(output_pcb), footprints=len(builder.footprints), placement_issues=list(builder.issues), nets=len(builder.nets),
                  netlist_nodes=len(pin_nets), placements=placements, silkscreen=silkscreen, slots=slots, rule_areas=[a['name'] for a in areas],
                  pcbnew_version=pcb.GetBuildVersion(), stackup_mm=stackup_thickness_mm())
    if not route:
        result['seconds'] = round(time.monotonic() - start, 3)
        write_outputs(result, outputs)
        return result
    # ---- copper: HV via groups, in-pad vias, chain tracks, zones, then the router for the signals -------------------
    boxes = pad_boxes(loaded)
    vias = []
    for g in via_groups():
        (x0, y0), (px, py), (nx, ny) = g['origin'], g['pitch'], g['count']
        for ix in range(nx):
            for iy in range(ny):
                vias.append(dict(net=g['net'], xy=[snap(x0 + ix * px), snap(y0 + iy * py)], diameter=g.get('diameter', HV_VIA[0]),
                                 drill=g.get('drill', HV_VIA[1])))
    pad_vias = hv_pad_vias(boxes)
    vias += pad_vias
    via_pads = {tuple(v['pad']) for v in pad_vias if v.get('pad')}
    skip_pads = [[r, n] for (r, n), b in boxes.items() if b['smd'] and b['net'] in ('PGND', 'SW', 'VIN', 'VOUT') and (r, n) in via_pads]
    tracks, chain_issues = hv_chain_tracks(boxes)
    tracks += feed_stubs(boxes) + d5_sw_track(boxes) + rt1_vin_raw_feed(boxes)
    pe_tracks, pe_skip = pe_pre_route(boxes)
    tracks += pe_tracks; skip_pads += pe_skip
    power_nets = {z['net'] for z in zone_plan() if not z.get('post_route')}
    fine = fine_pitch_escapes(boxes, builder.footprints, power_nets)
    tracks += fine['tracks']; vias += fine['vias']; skip_pads += fine['skip']
    exact_vias = [list(p) for p in fine['exact_vias']]
    # pads whose neighbour carries a 3 mm router halo (their own footprint's pin-field rule allows less): straight exact stubs; the
    # ladder taps leave their 1206 southwards into the sensing island (3.6 mm: past the 3 mm halo of the ladder pads)
    exact_pads = fine['exact'] + [['D3', '2', 0.6]] + [[ref, num, length, list(direction), offset] for (ref, num), (length, direction, offset) in TAP_STUBS.items()]
    exact_vias += [[ref, num] for (ref, num) in TAP_STUBS]  # the ladder taps end in a via: the sensing filters sit on B.Cu
    # pads connected by chain stubs or pours without a via of their own: LED cathodes (stub to the bleeder's PGND pad), link resistors'
    # PGND pads (inside the PGND B.Cu column)
    skip_pads += [[r, n] for (r, n), b in boxes.items() if b['net'] == 'PGND' and r in ('D1', 'D2', 'R14', 'R15')]
    # mezzanine socket pins: 1.7 mm pads on a 2.54 mm pitch are boxed in by their neighbours' clearance halos on the grid, so every
    # routed-net pin leaves the socket through a B.Cu stub perpendicular to the row (outer row south, inner row north) and the
    # router starts at the stub end; plane pins (GND_CTRL -> In1) connect to their pour directly
    stubs, links, link_skip = connector_stubs(boxes, power_nets)
    exact_pads += stubs; tracks += links; skip_pads += link_skip
    exact_vias += [[ref, num] for ref, num, *_ in stubs]  # a via at every socket stub end: ports on all three strip layers
    exact_lanes = [list(p) for p in fine['exact_lanes']]
    for ref, num, length, (ux, uy), offset, layer in stubs:  # reserved B.Cu exit lane from every routed socket via down to the bus band
        b = boxes[(ref, num)]
        if b['net'] in power_nets:
            continue  # plane pins: the via is the connection, no port to protect
        end_y = b['xy'][1] + uy * ((b['bbox'][3] - b['bbox'][1]) / 2 + length)
        exact_lanes.append([ref, num, round(SOCKET_LANE_END_Y - end_y, 3) if uy > 0 else 1.0])  # north ports: 1 mm lane into the corridor
    net_rules = {k: dict(v) for k, v in NET_RULES.items()}
    for net, w in fine['widths'].items():
        entry = net_rules.setdefault(net, {})
        entry['fanout_width'] = min(w, entry.get('fanout_width', w))
    regions = route_regions(boxes)
    for net, region in regions.items():
        net_rules.setdefault(net, {})['region'] = region
    keepouts = router_keepouts(boxes, areas)
    # routed nets register their SMD pads as ports on the pad's own layer (no escape via per pad) with a reserved exit lane: the router
    # adds vias where it needs them inside the net's region; plane nets (GND_CTRL, PGND) keep the via escape that reaches their pour
    plan = routing_plan(output_pcb, tracks, vias, skip_pads, keepouts, net_rules=net_rules, exact_stub_pads=exact_pads, trials=trials, ripup=ripup,
                        direct_nets=sorted(regions), inward_pads=inward_escape_pads(boxes), exact_via_pads=exact_vias, direct_lane=DIRECT_LANE_MM,
                        exact_lane_pads=exact_lanes, style=ROUTING_STYLE if style is None else style)
    # grid_router power entries named 'NET#i' must map to the real net: expand them into separate zone calls after run_plan
    extra_zone_entries = {k: v for k, v in plan['power'].items() if '#' in k}
    plan['power'] = {k: v for k, v in plan['power'].items() if '#' not in k}
    report = gr.run_plan(loaded, plan)
    post_zones = [z for z in zone_plan() if z.get('post_route')]
    if extra_zone_entries or post_zones:
        router = gr.Router(loaded, WIDTH, HEIGHT, ROUTING_LAYERS, grid=GRID, trace=TRACE, clearance=CLEARANCE, via=VIA, net_rules=NET_RULES,
                           board_margin=BOARD_MARGIN, hole_clearance=HOLE_CLEARANCE)
        for key, entry in extra_zone_entries.items():
            net = key.split('#')[0]
            for layer, polygon in entry['zones'].items():
                router.zone(net, layer, [tuple(p) for p in polygon], priority=entry['priority'], clearance=entry['clearance'], min_thickness=entry['min_thickness'])
        for z in post_zones:  # Kelvin-source / gate pours over the routed islands (their nets are routed as signals as well)
            router.zone(z['net'], z['layer'], [tuple(p) for p in z['polygon']], priority=z['priority'], clearance=z['clearance'], min_thickness=ZONE_MIN_THICKNESS)
        router.fill()
        report['extra_zones'] = len(extra_zone_entries) + len(post_zones)
        report['saved'] = gr.save_and_reload(loaded, output_pcb)
    if inject_stackup(output_pcb):
        report['stackup_reinjected'] = True
        gr.save_and_reload(pcb.LoadBoard(str(output_pcb)), output_pcb)
    report['rule_aware_refill'] = rule_aware_refill(output_pcb)  # r20 (LR-20): the stored fills become the rule-aware copper
    final = pcb.LoadBoard(str(output_pcb))
    counts = dict(tracks=sum(1 for t in final.GetTracks() if not isinstance(t, pcb.PCB_VIA)), vias=sum(1 for t in final.GetTracks() if isinstance(t, pcb.PCB_VIA)),
                  zones=len(list(final.Zones())))
    result.update(report=report, board_counts=counts, routing_plan={k: v for k, v in plan.items() if k not in ('pre_routed',)},
                  chain_issues=chain_issues, escape_issues=fine['issues'],
                  pre_routed=dict(tracks=len(tracks), vias=len(vias), hv_pad_vias=len(pad_vias), bar_vias=len(fine['vias']), via_groups=via_groups(),
                                  skip_pads=skip_pads, exact_stub_pads=exact_pads, exact_via_pads=exact_vias, exact_lane_pads=exact_lanes, connector_links=len(links),
                                  chain_issues=chain_issues, escape_issues=fine['issues']))
    if metrics:
        from automation.verification import check_sic_layout as cl
        spec = cl.load_spec(SPEC_JSON)
        model = cl.load_model(MODEL_JSON)
        m = cl.run_check(output_pcb, spec, model, backend=None, spec_path=SPEC_JSON, model_path=MODEL_JSON)
        json_path, md_path = cl.write_outputs(m, checks_dir, 'power')
        result['layout_metrics'] = dict(json=str(json_path), md=str(md_path), summary=m.get('summary'))
        result['routing_quality'] = routing_quality_metrics(output_pcb, checks_dir, 'power', plan, report)  # V2.1 TASK 2 (plan still carries pre_routed)
    if drc:
        from automation.kicad_tools.run_check import run_check
        code, manifest_path = run_check('drc', output_pcb, drc_dir, cli)
        manifest = read_manifest(manifest_path)
        result['drc'] = dict(manifest=str(manifest_path), wrapper_exit_code=code, tool_exit_code=manifest.get('tool_exit_code'), status=manifest.get('status'),
                             finding_count=manifest.get('finding_count'), violations=manifest.get('violations'), unconnected_items=manifest.get('unconnected_items'),
                             schematic_parity=manifest.get('schematic_parity'), details=manifest.get('details', [])[:400], error=manifest.get('error'))
        result['stored_fill_check'] = stored_fill_check(output_pcb, cli, checks_dir=checks_dir)  # r20 (LR-20) diagnostic: the stored fills judged without refill
    result['seconds'] = round(time.monotonic() - start, 3)
    write_outputs(result, outputs)
    return result


def routing_quality_metrics(board_path, output_dir, label: str, plan: dict | None, report: dict | None) -> dict:
    """Run automation.verification.check_routing_quality on a board (in-process, needs pcbnew) and write routing_quality_<label>.json/.md;
    ``plan`` attributes its pre-routed tracks, ``report`` (router report with a ``beautify`` block) explains the remaining sharp corners."""
    from automation.verification import check_routing_quality as cq
    doc = cq.extract_board(board_path)
    m = cq.measure(doc, plan=plan, report=report)
    json_path, md_path = cq.write_outputs(m, output_dir, label)
    return dict(json=str(json_path), md=str(md_path), totals=m['totals'], by_attribution=m['by_attribution'],
                sharp_corners_by_reason=m['sharp_corners']['by_reason'], arcs={k: v for k, v in m['arcs'].items() if k != 'tangency_failures'})


def write_outputs(result: dict, outputs=None):
    """placement_power.json / routing_plan_power.json (design/) and routing_progress_power.json (verification/); ``outputs`` = one scratch directory for all three."""
    design_dir = DESIGN_DIR if outputs is None else Path(outputs)
    verification_dir = VERIFICATION_DIR if outputs is None else Path(outputs)
    design_dir.mkdir(parents=True, exist_ok=True)
    placement = dict(schema_version=1, status=BANNER, project=NAME, board_mm=[WIDTH, HEIGHT], copper_layers=COPPER_LAYERS,
                     stackup=[dict(layer=l, type=t, thickness_mm=th) for l, t, th in STACKUP], fixed=FIXED, regions=REGIONS, items=result['placements'],
                     silkscreen=result.get('silkscreen', []), slots=result.get('slots'), rule_areas=result.get('rule_areas'),
                     placement_issues=result.get('placement_issues', []), notes=NOTES)
    (design_dir / 'placement_power.json').write_text(json.dumps(placement, indent=2, default=str) + '\n', encoding='utf-8')
    if 'routing_plan' in result:
        plan_doc = dict(schema_version=1, status=BANNER, project=NAME, run_plan=result['routing_plan'], zones=zone_plan(), via_groups=via_groups(),
                        pre_routed=result.get('pre_routed'), notes=NOTES)
        (design_dir / 'routing_plan_power.json').write_text(json.dumps(plan_doc, indent=2, default=str) + '\n', encoding='utf-8')
        report = result['report']
        counts = result.get('board_counts') or {}
        progress = dict(schema_version=1, status=BANNER, project=NAME, generated_utc=datetime.now(timezone.utc).isoformat(), board=result['board'],
                        board_sha256=hashlib.sha256(Path(result['board']).read_bytes()).hexdigest(),
                        stage='routed' if not report.get('unresolved') else 'routed_with_unresolved_connections', router_status=report.get('status'),
                        footprints=len(result['placements']), tracks=counts.get('tracks'), vias=counts.get('vias'), zones=counts.get('zones'),
                        ripup_rounds=report.get('ripup_rounds'),
                        router_report_counts=dict(tracks=report.get('tracks'), vias=report.get('vias'), zones=report.get('zones')),
                        unresolved=report.get('unresolved'), unresolved_count=len(report.get('unresolved', [])),
                        signal_order_trials=report.get('signal_order_trials'), signal_order_selected=report.get('signal_order_selected'),
                        chain_issues=result.get('chain_issues'), escape_issues=result.get('escape_issues'),
                        net_length_mm=report.get('net_length_mm'), grid=report.get('grid'), routing_seconds=report.get('seconds'),
                        style=report.get('style'), arcs=report.get('arcs'), beautify=report.get('beautify'), routing_quality=result.get('routing_quality'),  # V2.1
                        rule_aware_refill=report.get('rule_aware_refill'), stored_fill_check=result.get('stored_fill_check'),
                        drc=result.get('drc'), layout_metrics=result.get('layout_metrics'), seconds=result['seconds'],
                        evidence_note='Only the kicad-cli DRC manifest listed under drc counts as verification; the router figures are geometric proposals.')
        (verification_dir / 'routing_progress_power.json').write_text(json.dumps(progress, indent=2, default=str) + '\n', encoding='utf-8')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--output', type=Path, default=KICAD_DIR / f'{NAME}.kicad_pcb')
    parser.add_argument('--no-route', action='store_true')
    parser.add_argument('--no-drc', action='store_true')
    parser.add_argument('--no-metrics', action='store_true')
    parser.add_argument('--no-reexec', action='store_true')
    parser.add_argument('--trials', type=int, default=None, help=f'signal routing-order trials (default {SIGNAL_ORDER_TRIALS})')
    parser.add_argument('--ripup', type=int, default=None, help=f'rip-up negotiation rounds (default {RIPUP_ROUNDS})')
    parser.add_argument('--outputs', type=Path, default=None,
                        help='scratch build: write the netlist, placement, routing plan, progress JSON, engineering checks and DRC manifests under this '
                             'directory instead of the example design/ and verification/ folders (candidate comparison; not verification)')
    parser.add_argument('--style', choices=['default', 'v21', 'octilinear', 'none'], default='default',
                        help='grid_router geometry: default = ROUTING_STYLE, v21 = ROUTING_STYLE_V21 (8-direction search, simplification, arcs), '
                             'octilinear = ROUTING_STYLE_OCTILINEAR (4-direction search, simplification, arcs), none = V2')
    args = parser.parse_args(argv)
    try:
        import pcbnew  # noqa: F401
    except ImportError:
        if args.no_reexec:
            print('pcbnew is not importable in this interpreter', file=sys.stderr)
            return 2
        python = kicad_python()
        if python is None:
            print('No Python interpreter with pcbnew was found', file=sys.stderr)
            return 2
        passthrough = list(sys.argv[1:] if argv is None else argv)
        completed = subprocess.run([str(python), str(Path(__file__).resolve()), *passthrough, '--no-reexec'], cwd=str(ROOT))
        return completed.returncode
    cli = find_kicad_cli()
    style = {'default': None, 'v21': ROUTING_STYLE_V21, 'octilinear': ROUTING_STYLE_OCTILINEAR, 'none': {}}[args.style]
    result = build_power(args.output, route=not args.no_route, drc=not args.no_drc, metrics=not args.no_metrics, cli=cli, trials=args.trials, ripup=args.ripup,
                         style=style, outputs=args.outputs)
    report = result.get('report', {})
    drc = result.get('drc') or {}
    counts = result.get('board_counts') or {}
    print(f"power board: {result['footprints']} footprints, {counts.get('tracks')} tracks, {counts.get('vias')} vias, {counts.get('zones')} zones, "
          f"{len(report.get('unresolved', []))} unresolved; DRC {drc.get('status')} findings={drc.get('finding_count')} (violations {drc.get('violations')}, "
          f"unconnected {drc.get('unconnected_items')}, parity {drc.get('schematic_parity')}) manifest={drc.get('manifest')}; {result['seconds']} s", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
