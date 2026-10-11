"""Place, pour, route and check the V2 SiC buck POWER board (AIPE_SiC_Buck_Power) with pcbnew and the grid router.

AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED

Follows automation.kicad_tools.v2_pipeline_smoke.board_stage() and generate_sic_control_board.py: kicad-cli XML
netlist of the generated schematic, a pcbnew BOARD with the project footprint libraries and the symbol paths of
design/schematic_mapping_power.json, a deterministic placement (every structural part fixed by the floorplan
below, the small island / strip parts auto-placed in regions with a courtyard-overlap check), the 4 x 70 um /
2.0 mm stackup injected as text, the HV copper as zones (VIN+ F.Cu/In2.Cu over PGND In1.Cu for the commutation
loop, SW F.Cu/B.Cu, VOUT In2.Cu/B.Cu, Kelvin-source pours on In2.Cu under the driver islands), HV via groups of
1.2/0.6 mm, grid_router.run_plan for the signals (driver islands on B.Cu, SELV strip on F.Cu/B.Cu), rule areas
(ISO_BARRIER, heatsink keep-out, standoff annuli), non-plated isolation slots under the two UCC21710 (Edge.Cuts
cut-outs; the custom barrier footprints carry their own slots), zone fill, SaveBoard/LoadBoard, then kicad-cli DRC
with --schematic-parity --severity-all through automation.kicad_tools.run_check and the layout metrics checker.

Floorplan (design/design_decisions.json schema 4, design/pcb_stackup.md): 240 x 180 mm; HV area y < 140, ISO_BARRIER
strip y 140-150 (copper-free on every layer except the barrier packages' pad rows, which sit over 1.2 mm slots), SELV
strip y 150-180 with the mezzanine socket J7 and the four M3 standoff holes; heatsink HS1 (100 x 100 mm) at the
top centre with the two TO-247-4 standing against its lower face at 28 mm pitch, the eight barrier parts on the line
y = 145 with their HV pins toward the device row, the HF ceramics beside the device legs over the VIN+/PGND pour
pair, films and the inductor in the fan stream, the input terminals at the left and the output at the right.

Only the kicad-cli DRC report counts as verification; the router report and the placement checks are geometric
proposals. Nothing is waived: findings are reported with their manifest paths.

Run (re-executes itself under KiCad's bundled Python when pcbnew is not importable):
    python -m automation.kicad_tools.generate_sic_power_board [--no-route] [--no-drc] [--no-metrics]
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
BANNER = 'AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED'
REVISION = 'V2'
WIDTH, HEIGHT = 240.0, 180.0
COPPER_LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
ROUTING_LAYERS = ['F.Cu', 'B.Cu']
STACKUP = [('F.Cu', 'copper', 0.07), ('dielectric 1', 'prepreg', 0.2), ('In1.Cu', 'copper', 0.07),
           ('dielectric 2', 'core', 1.32), ('In2.Cu', 'copper', 0.07), ('dielectric 3', 'prepreg', 0.2), ('B.Cu', 'copper', 0.07)]
GRID, TRACE, CLEARANCE, HOLE_CLEARANCE = 0.125, 0.25, 0.25, 0.25  # project Default class 0.25 / 0.25
VIA = (0.6, 0.3)  # signal vias (project minimum); HV transitions use HV_VIA groups
HV_VIA = (1.2, 0.6)
BOARD_MARGIN = 1.2  # copper to board edge (HV rule 1.0 mm)
EDGE_COURTYARD = 0.4
ZONE_CLEARANCE, ZONE_MIN_THICKNESS = 0.3, 0.3  # the .kicad_dru class rules (3.0 / 1.0 / 9.0 / 5.0 mm) override the zone clearance where larger
MAX_NODES = 600000
RIPUP_ROUNDS = 12
PLACE_STEP = 0.5
BARRIER_Y = 145.0  # barrier-part centres; ISO_BARRIER strip 140-150
ISO_STRIP = (140.0, 150.0)
HV_LIMIT_Y = 139.9  # HV copper stays above this line (9.0 mm + to the SELV strip copper at y >= 151)
SELV_START_Y = 151.0
SINK_CENTRE = (99.25, 67.0)
SINK_KEEPOUT_MM = 5.0  # HV copper keep-out around the heatsink courtyard on the outer layers (KR-TH-002, baseline)
L1_CENTRE = (204.5, 95.0)
L1_HOLE_PITCH = 30.0
L1_ANNULUS_R = 6.15  # 4.3 mm NPTH + 4 mm copper-free (8 mm annulus of the inductor record)
M4_KEEPOUT_R = 8.5  # ~17 mm PE keep-out circle around each baseplate standoff (pcb_stackup.md section 9)
HV_ZONE_NETS = ('VIN', 'VIN_RAW', 'PGND', 'SW', 'VOUT', 'VOUT_L')
KELVIN_NETS = ('KS_H', 'KS_L')
SELV_ZONE_NETS = ('GND_CTRL', '12V_PROT')
HV_CLASS_NETS = ('VIN', 'VIN_RAW', 'VIN_PRE', 'SW', 'PGND', 'VOUT', 'VOUT_L', 'SNUB_MID', 'DAMP_MID', 'PE_REF_MID',
                 'BLD_IN_1', 'BLD_IN_2', 'IND_IN_1', 'IND_IN_2', 'IND_IN_3', 'BLD_OUT_1', 'IND_OUT_1', 'IND_OUT_2',
                 'VIN_DIV_T1', 'VIN_DIV_T2', 'VIN_DIV_T3', 'VOUT_DIV_T1')
# routed-net rules (mm): gate nets as wide B.Cu tracks (KR-PCB-001), driver rails 0.8, DESAT/SENSE 0.3, SELV 0.25
NET_RULES = {'G_H': dict(width=1.0, clearance=0.3), 'G_L': dict(width=1.0, clearance=0.3),
             'HS_OUTH': dict(width=1.0, clearance=0.3), 'HS_OUTL': dict(width=1.0, clearance=0.3),
             'LS_OUTH': dict(width=1.0, clearance=0.3), 'LS_OUTL': dict(width=1.0, clearance=0.3),
             'HS_CLMP': dict(width=0.5, clearance=0.3), 'LS_CLMP': dict(width=0.5, clearance=0.3),
             'VDD_H': dict(width=0.8, clearance=0.3, fanout_width=0.4), 'VEE_H': dict(width=0.8, clearance=0.3, fanout_width=0.4),
             'VDD_L': dict(width=0.8, clearance=0.3, fanout_width=0.4), 'VEE_L': dict(width=0.8, clearance=0.3, fanout_width=0.4),
             'ISO_15V': dict(width=0.5, clearance=0.3, fanout_width=0.4), '5V_ISO': dict(width=0.5, clearance=0.3, fanout_width=0.4),
             'PE': dict(width=2.0, clearance=5.3),  # 5.0 mm rule plus grid rounding of the 2.0 mm track 'PGND': dict(clearance=0.3), 'KS_H': dict(clearance=0.3), 'KS_L': dict(clearance=0.3),
             '12V_PROT': dict(width=1.0, fanout_width=0.4), '12V_BIAS_H': dict(width=0.8, fanout_width=0.4),
             '12V_BIAS_L': dict(width=0.8, fanout_width=0.4), '12V_BIAS_S': dict(width=0.8, fanout_width=0.4),
             'GNDP_H': dict(width=0.6, fanout_width=0.4), 'GNDP_L': dict(width=0.6, fanout_width=0.4), 'GNDP_S': dict(width=0.6, fanout_width=0.4),
             '3V3': dict(width=0.5), 'K1_LOW': dict(width=0.8, fanout_width=0.4)}
for _net in ('DESAT_H_A', 'DESAT_H_OC', 'DESAT_L_A', 'DESAT_L_OC', 'VIN_DIV', 'VOUT_DIV', 'ISO_RLIM', 'ISO_FB_VDD', 'ISO_FB_VEE',
             'HS_RLIM', 'HS_FB_VDD', 'HS_FB_VEE', 'LS_RLIM', 'LS_FB_VDD', 'LS_FB_VEE', 'HS_GK', 'LS_GK'):
    NET_RULES.setdefault(_net, dict(width=0.3, clearance=0.3))
SIGNAL_ORDER = ['G_H', 'G_L', 'HS_OUTH', 'HS_OUTL', 'LS_OUTH', 'LS_OUTL', 'HS_CLMP', 'LS_CLMP', 'VDD_', 'VEE_', 'DESAT_', 'HS_', 'LS_',
                'ISO_', '5V_ISO', 'VIN_DIV', 'VOUT_DIV', 'PE', 'VIN_OUT', 'VOUT_OUT', 'VIN_AMP', 'VOUT_AMP', 'ISENSE', 'VOC_SET', 'REF2V5_PB',
                'PWM_', 'RESET_N', 'BIAS_EN', 'FLT_', 'RDY_', 'OC_N', 'PG_BIAS', 'FAULT_N', 'RELAY_ON', 'RLY_G', 'K1_LOW', 'FAN_TACH', '12V_BIAS',
                'GNDP_', '3V3', 'SPARE_']
SIGNAL_ORDER_TRIALS = 2
# courtyard gaps (mm) for the auto-placer: (along the pad axis, across) for 2-pad parts, per kind otherwise
GAP_AXIS, GAP_LATERAL, GAP_TP, GAP_IC, GAP_CONNECTOR, GAP_HV = 1.3, 0.7, 0.5, 1.6, 0.8, 3.3

HV_VIA_RING_GAP = 3.0  # outer-layer HV functional clearance kept between HV via rings / HV pads and auto-placed island parts
CHAIN_TRACK_INSET = 0.15  # chain stubs start and end this far inside the pad edges
# ---------------------------------------------------------------------------------------------------------------------
# Floorplan: fixed poses (x, y, angle[, side]) - angles chosen so that barrier parts have their HV pins toward the device row
# (pcbnew rotation: 90 deg maps local (x, y) -> (y, -x); 270 deg maps (x, y) -> (-y, x)).
# ---------------------------------------------------------------------------------------------------------------------
FIXED = {
    # mechanical
    'HS1': (99.25, 67.0, 0), 'H1': (31.5, 7.0, 0),
    'H2': (6.0, 6.0, 0), 'H3': (140.0, 6.0, 0), 'H4': (235.0, 52.0, 0), 'H5': (6.0, 174.0, 0), 'H6': (120.0, 174.0, 0), 'H7': (234.0, 174.0, 0),
    'H8': (235.0, 158.0, 0), 'H9': (123.0, 158.0, 0), 'H10': (60.0, 170.0, 0), 'H11': (90.0, 170.0, 0),
    # half bridge (pad 1 = drain at the footprint origin, pads along +x) and the inductor (pad 1 = SW at the left)
    'Q1': (87.0, 126.0, 0), 'Q2': (115.0, 126.0, 0), 'L1': (204.5, 95.0, 0),
    # HF ceramics: left group vertical (VIN pad up) beside Q1's drain, right group horizontal (PGND pad toward Q2's source)
    'C1': (79.0, 126.5, 90), 'C2': (72.8, 126.5, 90), 'C3': (66.6, 126.5, 90), 'C4': (60.4, 126.5, 90), 'C5': (54.2, 126.5, 90),
    'C6': (48.0, 126.5, 90), 'C7': (60.4, 136.5, 90), 'C8': (54.2, 136.5, 90), 'C9': (48.0, 136.5, 90), 'C10': (41.8, 136.5, 90),
    # films: input left column (rotated, VIN pads at the bottom), output top right (VOUT pads at the bottom)
    'C11': (14.95, 33.0, 90), 'C12': (14.95, 77.0, 90), 'C13': (185.5, 23.5, 90), 'C14': (217.5, 23.5, 90),
    # terminals, precharge PTC, MOV
    'J1': (7.5, 112.0, 0), 'J5': (23.0, 112.0, 0), 'J2': (7.5, 129.0, 0), 'J6': (23.0, 129.0, 0), 'RT1': (35.5, 120.5, 270), 'RV1': (36.0, 85.0, 90),
    'J3': (161.0, 50.0, 0), 'J4': (161.0, 65.5, 0),
    # bleeder / indicator chains and the DNP damping legs in the top band, PE link parts beside the PE stud
    # top band, west -> east on the courtyard pitch (same-net pads of neighbouring parts ~0.6 mm apart joined by stubs inside the
    # two courtyards where the .kicad_dru pin-field exceptions apply): bleeder R1-R3 (2512) ending in PGND, the indicator chain
    # reversed so that the LED D1's PGND pad abuts R3's PGND pad (via in the 2512) and R4's VIN pad lies in the VIN+ pour, then
    # the damping legs C16/R12 | R13/C17 (DAMP_MID bypass along the board edge)
    'R1': (47.0, 6.5, 0), 'R2': (54.8, 6.5, 0), 'R3': (62.6, 6.5, 0), 'D1': (68.8, 6.5, 0), 'R6': (73.4, 6.5, 180), 'R5': (78.1, 6.5, 180), 'R4': (82.8, 6.5, 180),
    'C16': (88.9, 6.5, 0), 'R12': (96.6, 6.5, 0), 'R13': (104.4, 6.5, 180), 'C17': (112.1, 6.5, 180),
    # Y2 capacitors beside the PE stud; PGND-PE link resistors on B.Cu over the PGND pour (R14 PGND|PE, R16 MID|PE, R15 MID|PGND)
    'C18': (33.0, 19.0, 0), 'C19': (33.0, 32.5, 0), 'R14': (38.0, 45.0, 180, 'B'), 'R16': (38.0, 54.5, 180, 'B'), 'R15': (38.0, 64.0, 0, 'B'),
    # barrier line (HV pins up): UCC14141 at 90, UCC21710 / AMC1311 / TMCS1133 at 270
    'U2': (78.0, BARRIER_Y, 90), 'U1': (96.0, BARRIER_Y, 270), 'U3': (124.0, BARRIER_Y, 270), 'U4': (142.0, BARRIER_Y, 90),
    'U5': (163.0, BARRIER_Y, 90), 'U6': (181.0, BARRIER_Y, 270), 'U7': (195.0, BARRIER_Y, 270), 'U10': (212.0, BARRIER_Y, 270),
    # DESAT diodes and the DNP snubber on B.Cu in the island band (VIN / SW pads get HV vias to the pours)
    # DESAT diodes beside the drains (D3 on F.Cu with its VIN pad in the VIN+ band and the DESAT pad away from the Q1 drain pin,
    # D5 on B.Cu with its SW pad fed by a B.Cu track from Q2 pin 1); DNP snubber on F.Cu east of U1 (R11 SW pad on a tab of the
    # SW block, C15 PGND pad -> In1 via)
    'D3': (84.5, 133.5, 270), 'D5': (121.0, 132.5, 0, 'B'), 'R11': (114.0, 134.5, 0), 'C15': (121.5, 134.5, 0),
    # V_GS probe loops (through-hole) at the device side of the gate resistors (CR-11), clear of the driver pad escape lanes
    'TP1': (89.5, 134.5, 90, 'B'), 'TP2': (126.0, 134.5, 90, 'B'),
    # output bleeder / indicator chain between the sink keep-out and the output films
    # output bleeder / indicator column beside J3: bleeder R7/R8 ending in PGND, the indicator chain reversed so that the LED D2's
    # PGND pad abuts R8's PGND pad (via in the 2512); VOUT from the In2 column tab (R7 in-pad via, R9 via + 3 mm stub)
    'R7': (163.5, 5.0, 270), 'R8': (163.5, 12.8, 270), 'D2': (163.5, 19.0, 270), 'R10': (163.5, 23.6, 90), 'R9': (163.5, 28.3, 90),
    # HV sense ladders on F.Cu in one row at y 132 above the AMC1311s (1206 on the 4.2 mm pin-field pitch; VIN / VOUT fed by
    # vias 3 mm beyond the end pads with short stubs); the AMC1311 periphery sits below the row on B.Cu
    'R59': (174.0, 132.0, 0), 'R60': (178.7, 132.0, 0), 'R61': (183.4, 132.0, 0), 'R62': (188.1, 132.0, 0), 'R65': (194.5, 132.0, 180), 'R64': (199.2, 132.0, 180),
    # mezzanine socket (pin 1 at the right end, even pins toward the barrier) and SELV-strip connectors
    'J7': (211.0, 160.0, 270), 'J9': (18.0, 172.0, 0), 'J8': (36.0, 173.0, 90),
}
REGIONS = {  # name -> (side, [rects])
    # driver islands below the device row and above the barrier pad escape lanes (y <= 137.4): HS between the HF tier's PGND
    # via rings (3 mm) and Q2 plus the strip under the HF tier beside the U2 output pins (B.Cu), bias periphery on F.Cu
    # below the SW block; LS east of the SW copper (B.Cu) with its periphery on F.Cu; sensing islands clear of the ladder row
    'hs_island': ('B', [[91.0, 128.6, 116.0, 137.4], [83.0, 131.3, 116.0, 137.4], [64.5, 128.0, 83.0, 137.4]]),
    'hs_island_f': ('F', [[91.5, 131.6, 108.3, 137.4]]),
    'ls_island': ('B', [[122.5, 128.6, 153.0, 137.4]]),
    'ls_island_f': ('F', [[128.5, 129.3, 153.0, 137.0], [123.5, 131.6, 153.0, 137.0]]),
    'sense_a': ('B', [[155.5, 118.0, 168.3, 129.5], [153.0, 123.5, 168.3, 129.5], [153.0, 135.8, 172.0, 137.4]]),
    'sense_b': ('B', [[175.0, 135.8, 202.5, 137.4]]),
    'selv_left': ('F', [[2.0, 151.5, 58.0, 178.5]]),
    'selv_hs': ('F', [[60.0, 151.5, 104.0, 178.5]]),
    'selv_ls': ('F', [[106.0, 151.5, 147.0, 178.5]]),
    'selv_sense': ('F', [[153.0, 163.5, 232.0, 178.5]]),
}
ASSIGN_BY_REF = {
    # HS island (driver U1 / bias U2 output side)
    **{r: 'hs_island' for r in ('R19', 'R20', 'R21', 'R22', 'R23', 'C21', 'C22', 'C23', 'C24', 'C25', 'C26', 'C36', 'C37', 'C38', 'C39',
                                 'R29', 'R30', 'C34', 'R31', 'R32', 'C35', 'R33')},
    **{r: 'hs_island_f' for r in ('R24', 'R25', 'R26', 'C29', 'D4')},
    **{r: 'ls_island' for r in ('R37', 'R38', 'R39', 'R40', 'R41', 'C41', 'C42', 'C43', 'C44', 'C45', 'C46', 'D6',
                                 'R47', 'R48', 'C54', 'C55')},
    **{r: 'ls_island_f' for r in ('C56', 'C57', 'C58', 'C59', 'R42', 'R43', 'R44', 'C49', 'R49', 'R50', 'R51')},
    **{r: 'sense_a' for r in ('R53', 'R54', 'C64', 'R55', 'R56', 'C65', 'R57', 'C66', 'C67', 'C68', 'C69', 'R63', 'C70', 'C71')},
    **{r: 'sense_b' for r in ('C72', 'R66', 'C74', 'C75', 'C76')},
    # SELV strip: driver input filters, pull-ups, bias chokes and input capacitors
    **{r: 'selv_hs' for r in ('R17', 'C20', 'R18', 'C27', 'C28', 'R27', 'R28', 'L2', 'C30', 'C31', 'C32', 'C33', 'R34')},
    **{r: 'selv_ls' for r in ('R35', 'C40', 'R36', 'C47', 'C48', 'R45', 'R46', 'L3', 'C50', 'C51', 'C52', 'C53', 'R52')},
    **{r: 'selv_sense' for r in ('L4', 'C60', 'C61', 'C62', 'C63', 'R58', 'C73', 'C77', 'U8', 'C80', 'R71', 'R72', 'C81', 'R73', 'R74', 'C82',
                                  'R75', 'R76', 'C83', 'R77', 'R78', 'C84', 'U9', 'C85', 'C86', 'R79', 'R80', 'R81', 'C87', 'C88', 'R82', 'R83', 'C89',
                                  'TP9', 'TP10', 'TP11', 'TP12', 'TP13', 'TP6', 'TP7', 'TP8')},
    **{r: 'selv_left' for r in ('R67', 'C78', 'R68', 'R69', 'C79', 'R70', 'R84', 'Q3', 'R85', 'R86', 'D7', 'C90', 'C91', 'TP3', 'TP4', 'TP5')},
}
SILKSCREEN = [
    ('AIPE SiC BUCK 400V -> 200V / 5kW - POWER BOARD V2', (120.0, 121.2), 1.0),
    ('AI-GENERATED PROTOTYPE - HUMAN REVIEW REQUIRED', (120.0, 118.9), 0.9),
    ('DANGER - 400 V DC - DC LINK LIVE UP TO 60 s AFTER SWITCH-OFF', (99.0, 14.0), 1.0),
    ('ISO BARRIER 10 mm - NO COPPER', (30.0, 145.0), 0.9),
    ('VIN+', (9.0, 103.0), 1.0), ('PGND', (9.0, 138.0), 1.0), ('RELAY', (23.0, 103.0), 1.0), ('VOUT+', (161.0, 42.0), 1.0), ('PGND', (161.0, 75.0), 1.0),
    ('PE', (22.0, 8.0), 1.0), ('HEATSINK LAM 5 D K 100 x 100 x 50 - FAN', (99.25, 60.0), 1.2), ('AIR FLOW -->', (99.25, 70.0), 1.2),
    ('MEZZANINE J7 - PIN 1 RIGHT', (180.0, 165.0), 0.9), ('FAN', (36.0, 166.0), 0.8), ('RELAY COIL', (18.0, 165.5), 0.8),
]
NOTES = [
    'Every structural part (half bridge, HF ceramics, films, inductor, heatsink, terminals, barrier parts, connectors, standoff holes) is '
    'fixed by the floorplan table; the island, sensing and SELV-strip passives are auto-placed in their regions by Manhattan distance to their nets.',
    'HV copper is pours: VIN+ on F.Cu (left column, band under the device row, top band, right cap group) and In2.Cu (backbone under the sink), '
    'PGND on In1.Cu (whole HV area) and B.Cu (outside the islands), SW on F.Cu with a B.Cu parallel leg to the inductor, VOUT on In2.Cu/B.Cu '
    'strips to the output bank; 1.2/0.6 mm via groups join the layers; the Kelvin-source pours sit on In2.Cu under the driver islands.',
    'The ISO_BARRIER rule area forbids tracks, vias and pours on every copper layer in the 10 mm strip; the barrier packages pad rows are '
    'notched out of it and the UCC21710 packages get 15.5 x 1.2 mm Edge.Cuts slots (the custom barrier footprints carry their own slots).',
    'The grid router routes the driver islands (B.Cu, gate nets 1.0 mm), the sensing networks and the SELV strip (F.Cu/B.Cu); the HV nets are '
    'excluded from routing and connected by the pours and via groups only.',
    'Only the kicad-cli DRC manifest (schematic parity, severity-all) is verification; the router report is a geometric proposal.',
    'Stage 3 corrections (from the zones-only DRC experiment): chain parts on the pin-field pitch with courtyard-contained stubs, DAMP_MID '
    'bypass, LED / 1206 feeds through F.Cu zone patches and 3 mm vias, terminals re-pitched for the REDCUBE pin-field gap, VIN In2 backbone '
    'clear of the VOUT In2 bar, HV ladders in one row with via feeds, driver islands east of / below the HF-tier via rings with the HV '
    'via rings and HV pads reserved for the auto-placer, snubber on F.Cu, VOUT_L without vias, PGND right strip stitched, small PGND pads '
    'routed by the fanout, router budget 600k nodes / 2 trials / rip-up.',
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


def zone_plan() -> list[dict]:
    """[{net, layer, polygon, priority, clearance}] - HV, Kelvin and SELV pours. Polygons are generous; the
    KiCad filler clips them to the .kicad_dru clearances (3.0 mm HV functional on the outer layers, 1.0 mm inner,
    9.0 mm to SELV, 5.0 mm to PE, 0.3 mm same-reference island) and to the rule areas."""
    hv = HV_LIMIT_Y
    m = BOARD_MARGIN
    zones = []
    # VIN+ : F.Cu column merged with the top band, band under the device row (both HF rows); In2.Cu backbone under the sink up
    # to x 152 (clear of the VOUT In2 bar) with a tab to the VIN ladder feed via
    zones.append(dict(net='VIN', layer='F.Cu', polygon=[[m, m], [150.0, m], [150.0, 11.4], [43.0, 11.4], [43.0, 101.5], [m, 101.5]], priority=2,
                      keepout_rects=[[m, m, 43.0, 101.5], [43.0, m, 150.0, 11.4]]))
    zones.append(dict(net='VIN', layer='F.Cu', polygon=rect_poly(14.0, 120.0, 88.3, hv), priority=2))
    zones.append(dict(net='VIN', layer='In2.Cu', polygon=[[m, m], [152.0, m], [152.0, 61.5], [201.5, 61.5], [201.5, 134.5], [150.0, 134.5],
                                                         [150.0, hv], [m, hv]], priority=2))  # east arm round the VOUT bar to the VIN ladder feed
    # VIN_RAW: terminals J1/J5 and the PTC on F.Cu and B.Cu (3.0 mm from the VIN pours, higher priority so the filler clips VIN)
    for layer in ('F.Cu', 'B.Cu'):
        zones.append(dict(net='VIN_RAW', layer=layer, polygon=rect_poly(m, 104.5, 40.0, 117.0), priority=3))
    # PGND: In1 whole HV area; B.Cu one polygon (left column + top band + output block) and a stitched right strip
    zones.append(dict(net='PGND', layer='In1.Cu', polygon=rect_poly(m, m, WIDTH - m, hv), priority=1))
    zones.append(dict(net='PGND', layer='B.Cu', polygon=[[m, m], [WIDTH - m, m], [WIDTH - m, 11.4], [199.5, 11.4], [199.5, 92.0], [155.2, 92.0],
                                                        [155.2, 11.4], [43.4, 11.4], [43.4, hv], [m, hv]], priority=1, router_keepout=False))
    zones.append(dict(net='PGND', layer='B.Cu', polygon=rect_poly(218.5, 63.5, WIDTH - m, hv), priority=1, router_keepout=False))  # PE routes on B.Cu here
    # SW: F.Cu device block from x 91 (Q1 drain pad keeps its VIN copper) with a tab down to the snubber resistor pad, 24-via group
    # to In2; In2.Cu block + 26.8 mm neck + 22 mm strip
    zones.append(dict(net='SW', layer='F.Cu', polygon=[[91.0, 122.6], [117.0, 122.6], [117.0, 131.3], [113.5, 131.3], [113.5, 139.0], [108.5, 139.0],
                                                       [108.5, 131.3], [91.0, 131.3]], priority=3,
                      keepout_rects=[[91.0, 122.6, 117.0, 131.3], [108.5, 131.3, 113.5, 139.0]]))  # tab down to the snubber resistor pad
    zones.append(dict(net='SW', layer='In2.Cu', polygon=[[89.0, 119.0], [117.0, 119.0], [117.0, 100.0], [160.0, 100.0], [160.0, 91.5], [195.5, 91.5],
                                                        [195.5, 113.5], [160.0, 113.5], [160.0, 126.8], [89.0, 126.8]], priority=3))
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
    # Kelvin-source pours under the driver islands (In2.Cu, shield between the B.Cu gate copper and the rest)
    zones.append(dict(net='KS_H', layer='In2.Cu', polygon=rect_poly(64.5, 128.0, 116.0, hv), priority=4))
    zones.append(dict(net='KS_L', layer='In2.Cu', polygon=rect_poly(119.0, 128.0, 153.0, hv), priority=4))
    # SELV strip: GND_CTRL on In1, 12V_PROT on In2
    zones.append(dict(net='GND_CTRL', layer='In1.Cu', polygon=rect_poly(m, SELV_START_Y, WIDTH - m, HEIGHT - m), priority=1))
    zones.append(dict(net='12V_PROT', layer='In2.Cu', polygon=rect_poly(m, SELV_START_Y, WIDTH - m, HEIGHT - m), priority=1))
    for z in zones:
        z.setdefault('clearance', ZONE_CLEARANCE)
    return zones


def via_groups() -> list[dict]:
    """HV layer transitions as 1.2/0.6 mm via groups: [{net, origin, pitch, count}] (origin = first via)."""
    groups = [
        dict(net='VIN', origin=(39.0, 121.5), pitch=(2.2, 2.0), count=(2, 3)),  # F.Cu band -> In2 backbone (6, plus the J6 / RT1 plated pads)
        dict(net='VIN', origin=(4.0, 72.0), pitch=(2.2, 2.2), count=(10, 2)),  # column -> In2 (20), between the C12 pad rows
        dict(net='VIN', origin=(124.5, 4.0), pitch=(2.2, 2.2), count=(3, 2)),  # top band -> In2 (6), east of the damping legs
        dict(net='PGND', origin=(224.5, 76.0), pitch=(3.0, 4.0), count=(2, 11)),  # stitches the B.Cu right strip to In1 (22)
        dict(net='VOUT', origin=(163.5, 33.875), pitch=(2.2, 2.2), count=(1, 1), diameter=0.8, drill=0.4),  # R9 VOUT feed <- In2 column tab (3 mm stub)
        dict(net='VIN', origin=(169.0, 132.0), pitch=(2.2, 2.2), count=(1, 1), diameter=0.8, drill=0.4),  # VIN ladder feed (stub east to R59 pad 1)
        dict(net='SW', origin=(101.5, 123.3), pitch=(1.7, 1.6), count=(8, 3)),  # F.Cu device block -> In2 strip (24)
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
        r = M4_KEEPOUT_R
        areas.append(dict(name=f'M4_STANDOFF_{i}', layers=COPPER_LAYERS, polygon=rect_poly(x - r, y - r, x + r, y + r), tracks=True, vias=True, pours=True))
    return areas


def iso_barrier_polygon(pad_rows: list[tuple]) -> list[list[float]]:
    """ISO_BARRIER strip (y 140-150, full width) with notches around the barrier packages' pad rows.

    ``pad_rows``: [(x0, x1, y0, y1)] copper boxes of the HV-side rows (overlapping the strip's top edge) and the
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

    def gap_for(self, part: dict, local_pads: dict):
        kind = part['kind']
        if kind == 'TP':
            return GAP_TP, GAP_TP
        if (kind == 'Q' and len(local_pads) == 4) or part['ref'] in BARRIER_REFS:
            return 0.5, 0.5  # TO-247 and barrier package courtyards already enclose the body: island parts may follow closely
        if kind in ('J', 'H', 'HS'):
            return GAP_CONNECTOR, GAP_CONNECTOR
        hv = any(n in HV_CLASS_NETS and n != 'PGND' for n in part['nets'].values() if n)  # PGND-only parts sit in the islands (0.3 mm same-island rule)
        if len(local_pads) == 2 and kind in ('C', 'R', 'D', 'L', 'RV', 'RT'):
            (ax, ay), (bx, by) = list(local_pads.values())
            gaps = (GAP_AXIS, GAP_LATERAL) if abs(ax - bx) >= abs(ay - by) else (GAP_LATERAL, GAP_AXIS)
            return (max(gaps[0], GAP_HV), max(gaps[1], GAP_HV)) if hv else gaps
        return (GAP_IC, GAP_IC)

    def place(self, ref, x, y, angle, side='F', region=None, check=True):
        fp = self.footprints[ref]
        self.set_pose(fp, x, y, angle, side)
        box = self.courtyard(fp, side)
        thru = any(pad.GetAttribute() in (self.pcb.PAD_ATTRIB_PTH, self.pcb.PAD_ATTRIB_NPTH) for pad in fp.Pads())
        sides = ('F', 'B') if thru else (side,)
        if check:
            for s in sides:
                for other, other_box, _ in self.occupied[s]:
                    if boxes_overlap(box, other_box):
                        raise ValueError(('courtyard overlap', ref, other, [round(v, 3) for v in box], [round(v, 3) for v in other_box]))
            if box[0] < EDGE_COURTYARD or box[1] < EDGE_COURTYARD or box[2] > WIDTH - EDGE_COURTYARD or box[3] > HEIGHT - EDGE_COURTYARD:
                raise ValueError(('courtyard outside the board margin', ref, [round(v, 3) for v in box]))
        _, local_pads = self.pose_geometry(ref, angle, side)
        gaps = self.gap_for(self.by_ref[ref], local_pads)
        for s in sides:
            self.occupied[s].append((ref, box, gaps))
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

    def place_fixed(self):
        for ref, pose in FIXED.items():
            if ref not in self.footprints:
                raise ValueError(f'fixed part {ref} is not in the model')
            x, y, angle = pose[:3]
            self.place(ref, x, y, angle, side=pose[3] if len(pose) == 4 else 'F', region='fixed')
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
        for via in hv_pad_vias(fixed_boxes):
            if via['net'] == 'SW':
                continue
            r = via['diameter'] / 2
            box = [via['xy'][0] - r, via['xy'][1] - r, via['xy'][0] + r, via['xy'][1] + r]
            for s in ('F', 'B'):
                self.occupied[s].append((f"HVVIA:{via['net']}", box, (HV_VIA_RING_GAP, HV_VIA_RING_GAP)))
        for (ref, number), b in fixed_boxes.items():
            if b['net'] not in HV_CLASS_NETS or b['net'] in ('SW', 'SNUB_MID'):  # HS island parts are SW-referenced (0.3 mm same-island rule)
                continue
            for s in (('F', 'B') if not b['smd'] else (b['layer'],)):
                self.occupied[s].append((f"HVPAD:{ref}.{number}", list(b['bbox']), (HV_VIA_RING_GAP, HV_VIA_RING_GAP)))

    def anchors_for(self, part: dict, table: dict) -> dict:
        anchors: dict = {}
        for number, net in part['nets'].items():
            if not net or net in ('GND_CTRL', 'PGND'):
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
        for rect in rects:
            for angle in (0, 90, 180, 270):
                box, local_pads = self.pose_geometry(part['ref'], angle, side)
                gx, gy = self.gap_for(part, local_pads)
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
                for _, other, og in self.occupied[side]:
                    ex, ey = max(gx, og[0]), max(gy, og[1])
                    valid &= ~((X + box[0] - ex < other[2]) & (X + box[2] + ex > other[0]) & (Y + box[1] - ey < other[3]) & (Y + box[3] + ey > other[1]))
                if not valid.any():
                    continue
                X, Y = X[valid], Y[valid]
                if anchors:
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
            grown = [list(r) for r in rects]
            for step in range(4):
                try:
                    best = self.search_position(part, grown, table, side, region)
                    break
                except RuntimeError:
                    if step == 3:
                        raise
                    grown = [[r[0] - 1.0, r[1] - 1.0, r[2] + 1.0, r[3] + 1.0] for r in grown]
                    self.issues.append(f"{part['ref']}: region {region} full, rectangles grown by {1.0 * (step + 1)} mm")
            _, angle, x, y = best
            self.place(part['ref'], x, y, angle, side=side, region=region)
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
                if ref.startswith(('TEXT:', 'AREA:', 'VIAS:', 'HVVIA:', 'HVPAD:')) or ref == 'HS1':
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
                                                                    layer='B' if fp.IsFlipped() else 'F')
    return table


BARRIER_REFS = ('U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U10')
# no in-pad vias: HF-tier / damping VIN pads (they sit in the F.Cu VIN+ pour; the through rings would block the B.Cu islands),
# 1206 chain ends (a via next to the stub leaving the other pad is < 3 mm: fed by patches or 3 mm stubs instead), LED PGND pads
NO_VIN_VIA_REFS = ('C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C16', 'C17', 'D3')
NO_INPAD_VIA_REFS = ('R4', 'R9', 'R59', 'R64', 'D1', 'D2', 'D5', 'R11')


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
    """In-pad HV vias for the SMD pads of the zone nets (PGND pads -> In1 pour, VIN pads -> In2, VOUT bars) sized to the pad.
    Each via carries ``pad=[ref, number]`` so the router skips exactly the pads that got one."""
    vias = []
    for (ref, number), b in sorted(boxes.items()):
        if not b['smd'] or b['net'] not in ('PGND', 'VIN', 'VOUT', 'SW'):
            continue  # VOUT_L has no inner copper (F.Cu bar only): no vias
        if ref in BARRIER_REFS and b['net'] == 'PGND':
            continue  # fine-pitch sensing-island PGND pads: router fanout
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


def routing_plan(save: Path, extra_tracks, extra_vias, skip_pads, keepouts) -> dict:
    # grid_router zones: one plan entry per polygon, each with its own priority / clearance (the first polygon of a net is the
    # base entry, the others become 'NET#i' entries resolved by the zone stage below)
    plan_power, counters = {}, {}
    for z in zone_plan():
        entry = dict(stubs=False, priority=z['priority'], clearance=z['clearance'], min_thickness=ZONE_MIN_THICKNESS, zones={z['layer']: z['polygon']})
        if z['net'] not in plan_power:
            plan_power[z['net']] = entry
        else:
            counters[z['net']] = counters.get(z['net'], 0) + 1
            plan_power[f"{z['net']}#{counters[z['net']]}"] = entry
    return {
        'board': {'width': WIDTH, 'height': HEIGHT, 'margin': BOARD_MARGIN},
        'layers': list(ROUTING_LAYERS), 'grid': GRID, 'trace': TRACE, 'clearance': CLEARANCE, 'via': list(VIA), 'hole_clearance': HOLE_CLEARANCE,
        'directions': [None, None],
        'net_rules': {k: dict(v) for k, v in NET_RULES.items()},
        'keepouts': keepouts,
        'pre_routed': {'tracks': extra_tracks, 'vias': extra_vias},
        'fanout': {'order': ['U1', 'U3', 'U2', 'U4', 'U5', 'U6', 'U7', 'U10', 'U8', 'U9'], 'skip_refs': ['HS1'], 'skip_pads': skip_pads,
                   'skip_nets': ['VIN', 'VIN_RAW', 'SW', 'VOUT', 'VOUT_L', 'PE_REF_MID', 'SNUB_MID', 'DAMP_MID', 'BLD_IN_1', 'BLD_IN_2', 'IND_IN_1',
                                 'IND_IN_2', 'IND_IN_3', 'BLD_OUT_1', 'IND_OUT_1', 'IND_OUT_2', 'VIN_DIV_T1', 'VIN_DIV_T2', 'VIN_DIV_T3', 'VOUT_DIV_T1']},
        'critical': [], 'critical_layers': list(ROUTING_LAYERS),
        'power': plan_power,
        'signal_order': list(SIGNAL_ORDER), 'signal_layers': list(ROUTING_LAYERS), 'front_fallback': True,
        'ground': None,
        'prune_vias': True, 'fill': True, 'save': str(save), 'strict': False, 'max_nodes': MAX_NODES,
        'signal_order_trials': SIGNAL_ORDER_TRIALS, 'ripup_rounds': RIPUP_ROUNDS,
    }


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
            ax, ay = a['xy']; bx, by = b['xy']
            axis = 0 if abs(bx - ax) >= abs(by - ay) else 1
            sign = 1 if (bx, by)[axis] >= (ax, ay)[axis] else -1
            half_a = (a['bbox'][axis + 2] - a['bbox'][axis]) / 2
            half_b = (b['bbox'][axis + 2] - b['bbox'][axis]) / 2
            start = [ax, ay]; end = [bx, by]
            start[axis] += sign * max(0.0, half_a - CHAIN_TRACK_INSET)
            end[axis] -= sign * max(0.0, half_b - CHAIN_TRACK_INSET)
            if sign * (end[axis] - start[axis]) <= 0.05:
                continue  # pads overlap along the axis: already joined by copper
            others = [o for o in boxes.values() if o['net'] != net and (o['layer'] == layer[0] or not o['smd'])]
            crossing = [o for o in others if _segment_hits_pad(start, end, o['bbox'], 0.3 + 0.3)]
            if crossing:
                issues.append(f"{net}: straight link skipped, it would cross {sorted(o.get('ref_pad', '?') for o in crossing)}")
                continue
            tracks.append(dict(net=net, layer=layer, a=[round(start[0], 4), round(start[1], 4)], b=[round(end[0], 4), round(end[1], 4)], width=0.6))
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
    """F.Cu stubs from the ladder feed vias (via_groups: VIN above R59, VOUT east of R64) to the end pads of the sense ladders
    (R59 pad 1 VIN, R64 pad 1 VOUT): an in-pad via would sit 2.6 mm from the stub leaving the other pad of the 1206. The stub
    runs along the dominant axis from the via into the pad and ends CHAIN_TRACK_INSET inside the far pad edge."""
    tracks = []
    for ref, net, via_xy in (('R59', 'VIN', (169.0, 132.0)), ('R64', 'VOUT', (203.5, 132.0)), ('R9', 'VOUT', (163.5, 33.875))):  # R64: into the VOUT F.Cu strip
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


def build_power(output_pcb: Path, *, route=True, drc=True, metrics=True, cli=None) -> dict:
    import pcbnew as pcb
    start = time.monotonic()
    parts = load_parts()
    mapping = json.loads(MAPPING_JSON.read_text(encoding='utf-8'))['paths']
    cli = cli or find_kicad_cli()
    pin_nets = export_netlist(KICAD_DIR / f'{NAME}.kicad_sch', DESIGN_DIR / 'netlist_power.xml', cli)
    builder = Builder(parts, mapping, pin_nets)
    placements = builder.place_all()
    boxes = pad_boxes(builder.board)
    # slots under the UCC21710 packages (the custom barrier footprints carry their own)
    slots = []
    for ref in ('U1', 'U3'):
        rows = [b['bbox'] for (r, n), b in boxes.items() if r == ref]
        x0 = min(b[0] for b in rows) - 3.0
        x1 = max(b[2] for b in rows) + 3.0
        slots.append((round(x0, 3), BARRIER_Y - 0.6, round(x1, 3), BARRIER_Y + 0.6))
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
        write_outputs(result)
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
    skip_pads = [[r, n] for (r, n), b in boxes.items() if b['smd'] and b['net'] == 'PGND' and r not in BARRIER_REFS and (r, n) in via_pads]
    tracks, chain_issues = hv_chain_tracks(boxes)
    tracks += feed_stubs(boxes) + d5_sw_track(boxes)
    result['chain_issues'] = chain_issues
    keepouts = []
    for area in areas:
        poly = area['polygon']
        if area['name'] == 'ISO_BARRIER':
            keepouts.append(dict(layer=None, rect=[0.0, ISO_STRIP[0] + 0.5, WIDTH, 149.0], net=None, vias=True))
            continue
        box = [min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly)]
        for layer in area['layers']:
            if layer in ROUTING_LAYERS:
                keepouts.append(dict(layer=layer, rect=box, net=None, vias=True))
    # HV pours on the routing layers are reserved for their own net: a foreign track or via inside a pour would be clipped
    # 3 mm around by the filler, fragmenting the pour (VIN pads lost their copper in the first routed run) and violating the
    # class-pair rules; the PGND B.Cu pours stay open because PE is routed through them (the filler keeps the 5 mm)
    for z in zone_plan():
        if z['layer'] not in ROUTING_LAYERS or not z.get('router_keepout', True):
            continue
        rects = z.get('keepout_rects')
        if rects is None:
            xs = [p[0] for p in z['polygon']]; ys = [p[1] for p in z['polygon']]
            rects = [[min(xs), min(ys), max(xs), max(ys)]]
        for r in rects:
            keepouts.append(dict(layer=z['layer'], rect=list(r), net=z['net'], vias=True))
    # barrier strip edges: outside the pad-row notches no copper between HV_LIMIT_Y - 0.3 and the strip, nor between the strip
    # and SELV_START_Y (the 9 mm rule counts from the opposite pad rows: HV copper <= 139.6, SELV copper >= 150.4)
    rows = barrier_pad_rows(boxes)
    for hv_side, (ya, yb) in ((True, (139.6, ISO_STRIP[0] + 0.5)), (False, (149.0, 150.4))):
        notches = sorted((r[0] - 0.3, r[2] + 0.3) for r in rows if (r[1] < BARRIER_Y) == hv_side)
        x = 0.0
        for x0, x1 in notches:
            if x0 > x:
                keepouts.append(dict(layer=None, rect=[x, ya, x0, yb], net=None, vias=True))
            x = max(x, x1)
        keepouts.append(dict(layer=None, rect=[x, ya, WIDTH, yb], net=None, vias=True))
    # ladder feed vias and stubs: 3 mm outer rule against the sensing-island escapes
    for g in via_groups():
        if g['count'] == (1, 1):
            x0, y0 = g['origin']; r = g.get('diameter', HV_VIA[0]) / 2 + 3.0
            keepouts.append(dict(layer=None, rect=[x0 - r, y0 - r, x0 + r, y0 + r], net=g['net'], vias=True))
    plan = routing_plan(output_pcb, tracks, vias, skip_pads, keepouts)
    # grid_router power entries named 'NET#i' must map to the real net: expand them into separate zone calls after run_plan
    extra_zone_entries = {k: v for k, v in plan['power'].items() if '#' in k}
    plan['power'] = {k: v for k, v in plan['power'].items() if '#' not in k}
    report = gr.run_plan(loaded, plan)
    if extra_zone_entries:
        router = gr.Router(loaded, WIDTH, HEIGHT, ROUTING_LAYERS, grid=GRID, trace=TRACE, clearance=CLEARANCE, via=VIA, net_rules=NET_RULES,
                           board_margin=BOARD_MARGIN, hole_clearance=HOLE_CLEARANCE)
        for key, entry in extra_zone_entries.items():
            net = key.split('#')[0]
            for layer, polygon in entry['zones'].items():
                router.zone(net, layer, [tuple(p) for p in polygon], priority=entry['priority'], clearance=entry['clearance'], min_thickness=entry['min_thickness'])
        router.fill()
        report['extra_zones'] = len(extra_zone_entries)
        report['saved'] = gr.save_and_reload(loaded, output_pcb)
    if inject_stackup(output_pcb):
        report['stackup_reinjected'] = True
        gr.save_and_reload(pcb.LoadBoard(str(output_pcb)), output_pcb)
    final = pcb.LoadBoard(str(output_pcb))
    counts = dict(tracks=sum(1 for t in final.GetTracks() if not isinstance(t, pcb.PCB_VIA)), vias=sum(1 for t in final.GetTracks() if isinstance(t, pcb.PCB_VIA)),
                  zones=len(list(final.Zones())))
    result.update(report=report, board_counts=counts, routing_plan={k: v for k, v in plan.items() if k not in ('pre_routed',)},
                  pre_routed=dict(tracks=len(tracks), vias=len(vias), hv_pad_vias=len(pad_vias), via_groups=via_groups(), skip_pads=skip_pads,
                                  chain_issues=chain_issues))
    if metrics:
        from automation.verification import check_sic_layout as cl
        spec = cl.load_spec(SPEC_JSON)
        model = cl.load_model(MODEL_JSON)
        m = cl.run_check(output_pcb, spec, model, backend=None, spec_path=SPEC_JSON, model_path=MODEL_JSON)
        json_path, md_path = cl.write_outputs(m, CHECKS_DIR, 'power')
        result['layout_metrics'] = dict(json=str(json_path), md=str(md_path), summary=m.get('summary'))
    if drc:
        from automation.kicad_tools.run_check import run_check
        code, manifest_path = run_check('drc', output_pcb, DRC_DIR, cli)
        manifest = read_manifest(manifest_path)
        result['drc'] = dict(manifest=str(manifest_path), wrapper_exit_code=code, tool_exit_code=manifest.get('tool_exit_code'), status=manifest.get('status'),
                             finding_count=manifest.get('finding_count'), violations=manifest.get('violations'), unconnected_items=manifest.get('unconnected_items'),
                             schematic_parity=manifest.get('schematic_parity'), details=manifest.get('details', [])[:400], error=manifest.get('error'))
    result['seconds'] = round(time.monotonic() - start, 3)
    write_outputs(result)
    return result


def write_outputs(result: dict):
    DESIGN_DIR.mkdir(parents=True, exist_ok=True)
    placement = dict(schema_version=1, status=BANNER, project=NAME, board_mm=[WIDTH, HEIGHT], copper_layers=COPPER_LAYERS,
                     stackup=[dict(layer=l, type=t, thickness_mm=th) for l, t, th in STACKUP], fixed=FIXED, regions=REGIONS, items=result['placements'],
                     silkscreen=result.get('silkscreen', []), slots=result.get('slots'), rule_areas=result.get('rule_areas'),
                     placement_issues=result.get('placement_issues', []), notes=NOTES)
    (DESIGN_DIR / 'placement_power.json').write_text(json.dumps(placement, indent=2, default=str) + '\n', encoding='utf-8')
    if 'routing_plan' in result:
        plan_doc = dict(schema_version=1, status=BANNER, project=NAME, run_plan=result['routing_plan'], zones=zone_plan(), via_groups=via_groups(),
                        pre_routed=result.get('pre_routed'), notes=NOTES)
        (DESIGN_DIR / 'routing_plan_power.json').write_text(json.dumps(plan_doc, indent=2, default=str) + '\n', encoding='utf-8')
        report = result['report']
        counts = result.get('board_counts') or {}
        progress = dict(schema_version=1, status=BANNER, project=NAME, generated_utc=datetime.now(timezone.utc).isoformat(), board=result['board'],
                        board_sha256=hashlib.sha256(Path(result['board']).read_bytes()).hexdigest(),
                        stage='routed' if not report.get('unresolved') else 'routed_with_unresolved_connections', router_status=report.get('status'),
                        tracks=counts.get('tracks'), vias=counts.get('vias'), zones=counts.get('zones'),
                        router_report_counts=dict(tracks=report.get('tracks'), vias=report.get('vias'), zones=report.get('zones')),
                        unresolved=report.get('unresolved'), unresolved_count=len(report.get('unresolved', [])),
                        signal_order_trials=report.get('signal_order_trials'), signal_order_selected=report.get('signal_order_selected'),
                        net_length_mm=report.get('net_length_mm'), grid=report.get('grid'), routing_seconds=report.get('seconds'),
                        drc=result.get('drc'), layout_metrics=result.get('layout_metrics'), seconds=result['seconds'],
                        evidence_note='Only the kicad-cli DRC manifest listed under drc counts as verification; the router figures are geometric proposals.')
        (VERIFICATION_DIR / 'routing_progress_power.json').write_text(json.dumps(progress, indent=2, default=str) + '\n', encoding='utf-8')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--output', type=Path, default=KICAD_DIR / f'{NAME}.kicad_pcb')
    parser.add_argument('--no-route', action='store_true')
    parser.add_argument('--no-drc', action='store_true')
    parser.add_argument('--no-metrics', action='store_true')
    parser.add_argument('--no-reexec', action='store_true')
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
    result = build_power(args.output, route=not args.no_route, drc=not args.no_drc, metrics=not args.no_metrics, cli=cli)
    report = result.get('report', {})
    drc = result.get('drc') or {}
    counts = result.get('board_counts') or {}
    print(f"power board: {result['footprints']} footprints, {counts.get('tracks')} tracks, {counts.get('vias')} vias, {counts.get('zones')} zones, "
          f"{len(report.get('unresolved', []))} unresolved; DRC {drc.get('status')} findings={drc.get('finding_count')} (violations {drc.get('violations')}, "
          f"unconnected {drc.get('unconnected_items')}, parity {drc.get('schematic_parity')}) manifest={drc.get('manifest')}; {result['seconds']} s", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
