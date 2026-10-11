"""Stage 3 (DRC) corrections for generate_sic_power_board.py, derived from the zones-only DRC experiment (pours, via groups,
chain tracks and fixed poses without the signal router) and the diagnostic DRC of the first routed board.

usage: python patch_s3_v2.py TARGET.py      (asserted unique replacements against the 2026-10-10 21:11 generator text)

Findings fixed (kicad-cli DRC types, zones-only experiment 162 -> structural floor):
  zones_intersect            PGND B.Cu polygons shared an edge -> one U-shaped polygon
  clearance HV outer/inner   VIN In2 backbone overlapped the VOUT In2 bar (equal priority) -> VIN In2 cut back to x <= 152 with a tab to
                             the VIN ladder feed; VIN F.Cu column vs VIN_RAW 1.0/1.5 mm -> 3.0 mm gaps, VIN_RAW priority 3; RT1 rotated
                             (VIN_RAW pad inside its pour); J2/J6 and J3/J4 REDCUBE pin fields 1.43 mm apart -> re-pitched;
                             chain parts (bleeders, indicators, damping, PE link, sense ladders): different-net pads of neighbouring
                             parts 1.3-2.8 mm apart and straight midpoint tracks across other pads -> chains laid out on the
                             pin-field pitch (same-net pads 0.15 mm apart, joined by stubs that stay inside the two courtyards
                             where the .kicad_dru pin-field exceptions apply), DAMP_MID bypass along the board edge, LED and 1206
                             feed pads connected through small F.Cu zone patches (courtyard exception) with the via 3 mm away;
                             HF-tier rows 2.1 mm apart -> row A 1.0 mm higher; HS-island parts under the HF-tier via rings ->
                             islands moved east/below the rings, HV via rings and HV pads reserved for the auto-placer, in-pad VIN
                             vias dropped for C1-C10/C16/C17; snubber on F.Cu between the devices; D3/D5 beside the drains (D5 fed
                             by a B.Cu track); TP1/TP2 clear of the driver pad escape lanes; sense islands clear of the ladder row
  via_dangling               VOUT_L in-pad vias removed (no inner copper); TMCS bar pads: one via at the HV end (U10 pin-field finding gone)
  isolated_copper            PGND B.Cu right strip stitched with a via array
  unconnected PGND           small PGND pads without an in-pad via are no longer skipped by the router fanout
  router budget              MAX_NODES 2.5M -> 600k, 2 order trials, rip-up rounds on
"""
import sys
from pathlib import Path

target = Path(sys.argv[1])
s = target.read_text(encoding='utf-8')


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:120])
    s = s.replace(old, new)


def block(start_marker, end_marker, new):
    """Replace the text from start_marker (inclusive) up to end_marker (exclusive)."""
    global s
    a = s.index(start_marker)
    b = s.index(end_marker, a)
    s = s[:a] + new + s[b:]


# ---- constants ---------------------------------------------------------------------------------------------------------
rep("ROOT = Path(__file__).resolve().parents[2]\n",
    "ROOT = Path(os.environ['AIPE_ROOT']) if os.environ.get('AIPE_ROOT') else Path(__file__).resolve().parents[2]  # AIPE_ROOT: run a copy of this module\n")
rep("MAX_NODES = 2500000\n", "MAX_NODES = 600000\nRIPUP_ROUNDS = 12\n")
rep("SIGNAL_ORDER_TRIALS = 4\n", "SIGNAL_ORDER_TRIALS = 2\n")
rep("# ---------------------------------------------------------------------------------------------------------------------\n"
    "# Floorplan: fixed poses",
    "HV_VIA_RING_GAP = 3.0  # outer-layer HV functional clearance kept between HV via rings / HV pads and auto-placed island parts\n"
    "CHAIN_TRACK_INSET = 0.15  # chain stubs start and end this far inside the pad edges\n"
    "# ---------------------------------------------------------------------------------------------------------------------\n"
    "# Floorplan: fixed poses")

# ---- fixed poses --------------------------------------------------------------------------------------------------------
rep("    'HS1': (99.25, 67.0, 0), 'H1': (38.0, 8.0, 0),\n", "    'HS1': (99.25, 67.0, 0), 'H1': (31.5, 7.0, 0),\n")
# HF tier left group: PGND pads toward the sink (rot 90) and the row 1.0 mm higher, so the PGND via rings (y 123.95) leave
# the B.Cu strip from y 128 free and the VIN pads keep 3.1 mm to the PGND pads of the second row
rep("    'C1': (79.0, 129.0, 270), 'C2': (72.8, 129.0, 270), 'C3': (66.6, 129.0, 270), 'C4': (60.4, 129.0, 270), 'C5': (54.2, 129.0, 270),\n"
    "    'C6': (48.0, 129.0, 270),",
    "    'C1': (79.0, 126.5, 90), 'C2': (72.8, 126.5, 90), 'C3': (66.6, 126.5, 90), 'C4': (60.4, 126.5, 90), 'C5': (54.2, 126.5, 90),\n"
    "    'C6': (48.0, 126.5, 90),")
rep("    'J1': (7.5, 112.0, 0), 'J5': (21.0, 112.0, 0), 'J2': (7.5, 129.0, 0), 'J6': (21.0, 129.0, 0), 'RT1': (32.5, 120.5, 90), 'RV1': (36.0, 75.0, 90),\n"
    "    'J3': (161.0, 50.0, 0), 'J4': (161.0, 63.5, 0),",
    "    'J1': (7.5, 112.0, 0), 'J5': (23.0, 112.0, 0), 'J2': (7.5, 129.0, 0), 'J6': (23.0, 129.0, 0), 'RT1': (35.5, 120.5, 270), 'RV1': (36.0, 85.0, 90),\n"
    "    'J3': (161.0, 50.0, 0), 'J4': (161.0, 65.5, 0),")
rep("    'C16': (54.0, 6.5, 0), 'R12': (62.5, 6.5, 0), 'C17': (72.0, 6.5, 0), 'R13': (80.5, 6.5, 0),\n"
    "    'R1': (89.0, 6.5, 0), 'R2': (97.5, 6.5, 0), 'R3': (106.0, 6.5, 0), 'R4': (113.5, 6.5, 0), 'R5': (119.0, 6.5, 0), 'R6': (124.5, 6.5, 0), 'D1': (129.5, 6.5, 0),\n"
    "    'C18': (32.0, 20.0, 0), 'C19': (32.0, 30.0, 0), 'R14': (36.0, 40.0, 0), 'R15': (36.0, 47.0, 0), 'R16': (36.0, 54.0, 0),",
    "    # top band, west -> east on the courtyard pitch (same-net pads of neighbouring parts ~0.6 mm apart joined by stubs inside the\n"
    "    # two courtyards where the .kicad_dru pin-field exceptions apply): bleeder R1-R3 (2512) ending in PGND, the indicator chain\n"
    "    # reversed so that the LED D1's PGND pad abuts R3's PGND pad (via in the 2512) and R4's VIN pad lies in the VIN+ pour, then\n"
    "    # the damping legs C16/R12 | R13/C17 (DAMP_MID bypass along the board edge)\n"
    "    'R1': (47.0, 6.5, 0), 'R2': (54.8, 6.5, 0), 'R3': (62.6, 6.5, 0), 'D1': (68.8, 6.5, 0), 'R6': (73.4, 6.5, 180), 'R5': (78.1, 6.5, 180), 'R4': (82.8, 6.5, 180),\n"
    "    'C16': (88.9, 6.5, 0), 'R12': (96.6, 6.5, 0), 'R13': (104.4, 6.5, 180), 'C17': (112.1, 6.5, 180),\n"
    "    # Y2 capacitors beside the PE stud; PGND-PE link resistors on B.Cu over the PGND pour (R14 PGND|PE, R16 MID|PE, R15 MID|PGND)\n"
    "    'C18': (33.0, 19.0, 0), 'C19': (33.0, 32.5, 0), 'R14': (38.0, 45.0, 180, 'B'), 'R16': (38.0, 54.5, 180, 'B'), 'R15': (38.0, 64.0, 0, 'B'),")
rep("    'D3': (64.0, 130.5, 0, 'B'), 'D5': (113.0, 136.0, 0, 'B'), 'R11': (102.0, 133.0, 270, 'B'), 'C15': (106.0, 134.0, 270, 'B'),\n"
    "    # V_GS probe loops (through-hole) at the device side of the gate resistors (CR-11)\n"
    "    'TP1': (97.5, 137.5, 90, 'B'), 'TP2': (118.5, 137.5, 90, 'B'),",
    "    # DESAT diodes beside the drains (D3 on F.Cu with its VIN pad in the VIN+ band and the DESAT pad away from the Q1 drain pin,\n"
    "    # D5 on B.Cu with its SW pad fed by a B.Cu track from Q2 pin 1); DNP snubber on F.Cu east of U1 (R11 SW pad on a tab of the\n"
    "    # SW block, C15 PGND pad -> In1 via)\n"
    "    'D3': (84.5, 133.5, 270), 'D5': (121.0, 132.5, 0, 'B'), 'R11': (114.0, 134.5, 0), 'C15': (121.5, 134.5, 0),\n"
    "    # V_GS probe loops (through-hole) at the device side of the gate resistors (CR-11), clear of the driver pad escape lanes\n"
    "    'TP1': (89.5, 134.5, 90, 'B'), 'TP2': (126.0, 134.5, 90, 'B'),")
rep("    'R7': (161.0, 6.0, 90), 'R8': (161.0, 16.0, 90), 'R9': (161.0, 25.0, 90), 'R10': (161.0, 31.0, 90), 'D2': (161.0, 37.0, 90),",
    "    # output bleeder / indicator column beside J3: bleeder R7/R8 ending in PGND, the indicator chain reversed so that the LED D2's\n"
    "    # PGND pad abuts R8's PGND pad (via in the 2512); VOUT from the In2 column tab (R7 in-pad via, R9 via + 3 mm stub)\n"
    "    'R7': (163.5, 5.0, 270), 'R8': (163.5, 12.8, 270), 'D2': (163.5, 19.0, 270), 'R10': (163.5, 23.6, 90), 'R9': (163.5, 28.3, 90),")
rep("    # HV sense ladders on F.Cu above the AMC1311s (VIN ladder row, VOUT ladder row; 3 mm between the rows)\n"
    "    'R59': (164.5, 132.3, 0), 'R60': (170.0, 132.3, 0), 'R61': (175.5, 132.3, 0), 'R62': (181.0, 132.3, 0), 'R64': (164.5, 137.3, 0), 'R65': (170.0, 137.3, 0),",
    "    # HV sense ladders on F.Cu in one row at y 132 above the AMC1311s (1206 on the 4.2 mm pin-field pitch; VIN / VOUT fed by\n"
    "    # vias 3 mm beyond the end pads with short stubs); the AMC1311 periphery sits below the row on B.Cu\n"
    "    'R59': (174.0, 132.0, 0), 'R60': (178.7, 132.0, 0), 'R61': (183.4, 132.0, 0), 'R62': (188.1, 132.0, 0), 'R65': (194.5, 132.0, 180), 'R64': (199.2, 132.0, 180),")

# ---- regions ------------------------------------------------------------------------------------------------------------
rep("    'hs_island': ('B', [[60.0, 118.0, 104.0, HV_LIMIT_Y]]),\n"
    "    'ls_island': ('B', [[116.0, 122.8, 152.0, HV_LIMIT_Y]]),\n"
    "    'sense_a': ('B', [[153.0, 118.0, 167.5, HV_LIMIT_Y]]),\n"
    "    'sense_b': ('B', [[182.0, 131.5, 202.5, HV_LIMIT_Y]]),",
    "    # driver islands below the device row and above the barrier pad escape lanes (y <= 137.4): HS between the HF tier's PGND\n"
    "    # via rings (3 mm) and Q2 plus the strip under the HF tier beside the U2 output pins (B.Cu), bias periphery on F.Cu\n"
    "    # below the SW block; LS east of the SW copper (B.Cu) with its periphery on F.Cu; sensing islands clear of the ladder row\n"
    "    'hs_island': ('B', [[91.0, 128.6, 116.0, 137.4], [83.0, 131.3, 116.0, 137.4], [64.5, 128.0, 83.0, 137.4]]),\n"
    "    'hs_island_f': ('F', [[91.5, 131.6, 108.3, 137.4]]),\n"
    "    'ls_island': ('B', [[122.5, 128.6, 153.0, 137.4]]),\n"
    "    'ls_island_f': ('F', [[128.5, 129.3, 153.0, 137.0], [123.5, 131.6, 153.0, 137.0]]),\n"
    "    'sense_a': ('B', [[155.5, 118.0, 168.3, 129.5], [153.0, 123.5, 168.3, 129.5], [153.0, 135.8, 172.0, 137.4]]),\n"
    "    'sense_b': ('B', [[175.0, 135.8, 202.5, 137.4]]),")
rep("    **{r: 'hs_island' for r in ('R19', 'R20', 'R21', 'R22', 'R23', 'C21', 'C22', 'C23', 'C24', 'C25', 'C26', 'R24', 'R25', 'R26', 'C29', 'D4',\n"
    "                                 'R29', 'R30', 'C34', 'R31', 'R32', 'C35', 'R33', 'C36', 'C37', 'C38', 'C39')},\n"
    "    **{r: 'ls_island' for r in ('R37', 'R38', 'R39', 'R40', 'R41', 'C41', 'C42', 'C43', 'C44', 'C45', 'C46', 'R42', 'R43', 'R44', 'C49', 'D6',\n"
    "                                 'R47', 'R48', 'C54', 'R49', 'R50', 'C55', 'R51', 'C56', 'C57', 'C58', 'C59')},",
    "    **{r: 'hs_island' for r in ('R19', 'R20', 'R21', 'R22', 'R23', 'C21', 'C22', 'C23', 'C24', 'C25', 'C26', 'C36', 'C37', 'C38', 'C39',\n"
    "                                 'R29', 'R30', 'C34', 'R31', 'R32', 'C35', 'R33')},\n"
    "    **{r: 'hs_island_f' for r in ('R24', 'R25', 'R26', 'C29', 'D4')},\n"
    "    **{r: 'ls_island' for r in ('R37', 'R38', 'R39', 'R40', 'R41', 'C41', 'C42', 'C43', 'C44', 'C45', 'C46', 'D6',\n"
    "                                 'R47', 'R48', 'C54', 'C55')},\n"
    "    **{r: 'ls_island_f' for r in ('C56', 'C57', 'C58', 'C59', 'R42', 'R43', 'R44', 'C49', 'R49', 'R50', 'R51')},")
rep("    ('PE', (38.0, 14.5), 1.0),", "    ('PE', (22.0, 8.0), 1.0),")
rep("('VOUT+', (161.0, 42.0), 1.0), ('PGND', (161.0, 71.0), 1.0),", "('VOUT+', (161.0, 42.0), 1.0), ('PGND', (161.0, 75.0), 1.0),")

# ---- zones --------------------------------------------------------------------------------------------------------------
block("    # VIN+ : F.Cu column, band under the device row (both HF rows), top band; In2.Cu backbone under the sink (SW strip excluded by priority)",
      "    for z in zones:\n        z.setdefault('clearance', ZONE_CLEARANCE)",
      """    # VIN+ : F.Cu column merged with the top band, band under the device row (both HF rows); In2.Cu backbone under the sink up
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
""")

# ---- via groups (optional diameter/drill per group) --------------------------------------------------------------------------
block("    groups = [\n", "    return groups\n",
      """    groups = [
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
""")
rep("        for ix in range(nx):\n"
    "            for iy in range(ny):\n"
    "                vias.append(dict(net=g['net'], xy=[snap(x0 + ix * px), snap(y0 + iy * py)], diameter=HV_VIA[0], drill=HV_VIA[1]))\n",
    "        for ix in range(nx):\n"
    "            for iy in range(ny):\n"
    "                vias.append(dict(net=g['net'], xy=[snap(x0 + ix * px), snap(y0 + iy * py)], diameter=g.get('diameter', HV_VIA[0]),\n"
    "                                 drill=g.get('drill', HV_VIA[1])))\n")

# ---- auto-placer: courtyard gaps, reserved HV via rings and HV pads of the fixed parts ------------------------------------
rep("        kind = part['kind']\n"
    "        if kind == 'TP':\n"
    "            return GAP_TP, GAP_TP\n",
    "        kind = part['kind']\n"
    "        if kind == 'TP':\n"
    "            return GAP_TP, GAP_TP\n"
    "        if (kind == 'Q' and len(local_pads) == 4) or part['ref'] in BARRIER_REFS:\n"
    "            return 0.5, 0.5  # TO-247 and barrier package courtyards already enclose the body: island parts may follow closely\n")
rep("        for g in via_groups():\n"
    "            (x0, y0), (px, py), (nx, ny) = g['origin'], g['pitch'], g['count']\n"
    "            box = [x0 - 1.0, y0 - 1.0, x0 + px * (nx - 1) + 1.0, y0 + py * (ny - 1) + 1.0]\n"
    "            for s in ('F', 'B'):\n"
    "                self.occupied[s].append((f\"VIAS:{g['net']}\", box, (0.0, 0.0)))\n",
    "        for g in via_groups():\n"
    "            (x0, y0), (px, py), (nx, ny) = g['origin'], g['pitch'], g['count']\n"
    "            r = g.get('diameter', HV_VIA[0]) / 2\n"
    "            box = [x0 - r, y0 - r, x0 + px * (nx - 1) + r, y0 + py * (ny - 1) + r]\n"
    "            gap = HV_VIA_RING_GAP if g['net'] != 'SW' else 0.5  # island parts are SW-referenced (0.3 mm same-island rule)\n"
    "            for s in ('F', 'B'):\n"
    "                self.occupied[s].append((f\"VIAS:{g['net']}\", box, (gap, gap)))\n"
    "        # in-pad HV vias of the fixed parts (HF tier PGND, chains, snubber) need the 3.0 mm outer rule on both sides; their HV\n"
    "        # pads need it on their own side (plated-through pads on both)\n"
    "        fixed_boxes = {key: b for key, b in pad_boxes(self.board).items() if key[0] in self.placements}\n"
    "        for via in hv_pad_vias(fixed_boxes):\n"
    "            if via['net'] == 'SW':\n"
    "                continue\n"
    "            r = via['diameter'] / 2\n"
    "            box = [via['xy'][0] - r, via['xy'][1] - r, via['xy'][0] + r, via['xy'][1] + r]\n"
    "            for s in ('F', 'B'):\n"
    "                self.occupied[s].append((f\"HVVIA:{via['net']}\", box, (HV_VIA_RING_GAP, HV_VIA_RING_GAP)))\n"
    "        for (ref, number), b in fixed_boxes.items():\n"
    "            if b['net'] not in HV_CLASS_NETS or b['net'] in ('SW', 'SNUB_MID'):  # HS island parts are SW-referenced (0.3 mm same-island rule)\n"
    "                continue\n"
    "            for s in (('F', 'B') if not b['smd'] else (b['layer'],)):\n"
    "                self.occupied[s].append((f\"HVPAD:{ref}.{number}\", list(b['bbox']), (HV_VIA_RING_GAP, HV_VIA_RING_GAP)))\n")
rep("                if ref.startswith(('TEXT:', 'AREA:', 'VIAS:')) or ref == 'HS1':\n",
    "                if ref.startswith(('TEXT:', 'AREA:', 'VIAS:', 'HVVIA:', 'HVPAD:')) or ref == 'HS1':\n")

# ---- pad table: keep the ref/pad key for the crossing report ---------------------------------------------------------------
rep("                table[(fp.GetReference(), pad.GetNumber())] = dict(bbox=[pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())],\n",
    "                table[(fp.GetReference(), pad.GetNumber())] = dict(ref_pad=f'{fp.GetReference()}.{pad.GetNumber()}',\n"
    "                                                                    bbox=[pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())],\n")

# ---- in-pad vias ----------------------------------------------------------------------------------------------------------
rep("BARRIER_REFS = ('U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U10')\n",
    "BARRIER_REFS = ('U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U10')\n"
    "# no in-pad vias: HF-tier / damping VIN pads (they sit in the F.Cu VIN+ pour; the through rings would block the B.Cu islands),\n"
    "# 1206 chain ends (a via next to the stub leaving the other pad is < 3 mm: fed by patches or 3 mm stubs instead), LED PGND pads\n"
    "NO_VIN_VIA_REFS = ('C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C16', 'C17', 'D3')\n"
    "NO_INPAD_VIA_REFS = ('R4', 'R9', 'R59', 'R64', 'D1', 'D2', 'D5', 'R11')\n")
block("def hv_pad_vias(boxes: dict) -> list[dict]:", "def routing_plan(",
      '''def hv_pad_vias(boxes: dict) -> list[dict]:
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


''')

# ---- chain tracks, feed stubs, D5 drain track ----------------------------------------------------------------------------------
block("def hv_chain_tracks(boxes: dict) -> list[dict]:", "def build_power(",
      '''def _segment_hits_pad(a, b, box, margin) -> bool:
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


''')

# ---- routing plan: one zone entry per polygon so every zone keeps its own priority (the patches need priority 3) --------------
rep("    power = {}\n"
    "    for z in zone_plan():\n"
    "        entry = power.setdefault(z['net'], dict(stubs=False, priority=z['priority'], clearance=z['clearance'], min_thickness=ZONE_MIN_THICKNESS, zones={}))\n"
    "        entry['zones'].setdefault(z['layer'], []).append(z['polygon'])\n"
    "    # grid_router zones: one polygon per layer per power entry; several polygons of a net/layer become extra entries\n"
    "    plan_power = {}\n"
    "    for net, entry in power.items():\n"
    "        layer_polys = entry['zones']\n"
    "        base = dict(stubs=False, priority=entry['priority'], clearance=entry['clearance'], min_thickness=ZONE_MIN_THICKNESS, zones={})\n"
    "        extra_entries = []\n"
    "        for layer, polys in layer_polys.items():\n"
    "            base['zones'][layer] = polys[0]\n"
    "            for i, poly in enumerate(polys[1:], 1):\n"
    "                extra_entries.append(dict(stubs=False, priority=entry['priority'], clearance=entry['clearance'], min_thickness=ZONE_MIN_THICKNESS, zones={layer: poly}))\n"
    "        plan_power[net] = base\n"
    "        for i, e in enumerate(extra_entries, 1):\n"
    "            plan_power[f'{net}#{i}'] = e  # resolved by the zone stage below (same net)\n",
    "    # grid_router zones: one plan entry per polygon, each with its own priority / clearance (the first polygon of a net is the\n"
    "    # base entry, the others become 'NET#i' entries resolved by the zone stage below)\n"
    "    plan_power, counters = {}, {}\n"
    "    for z in zone_plan():\n"
    "        entry = dict(stubs=False, priority=z['priority'], clearance=z['clearance'], min_thickness=ZONE_MIN_THICKNESS, zones={z['layer']: z['polygon']})\n"
    "        if z['net'] not in plan_power:\n"
    "            plan_power[z['net']] = entry\n"
    "        else:\n"
    "            counters[z['net']] = counters.get(z['net'], 0) + 1\n"
    "            plan_power[f\"{z['net']}#{counters[z['net']]}\"] = entry\n")

# ---- router guards: HV pours as net-coded keep-outs on the routing layers, barrier-strip edges, ladder feed vias ---------------
rep("        for layer in area['layers']:\n"
    "            if layer in ROUTING_LAYERS:\n"
    "                keepouts.append(dict(layer=layer, rect=box, net=None, vias=True))\n"
    "    plan = routing_plan(output_pcb, tracks, vias, skip_pads, keepouts)\n",
    "        for layer in area['layers']:\n"
    "            if layer in ROUTING_LAYERS:\n"
    "                keepouts.append(dict(layer=layer, rect=box, net=None, vias=True))\n"
    "    # HV pours on the routing layers are reserved for their own net: a foreign track or via inside a pour would be clipped\n"
    "    # 3 mm around by the filler, fragmenting the pour (VIN pads lost their copper in the first routed run) and violating the\n"
    "    # class-pair rules; the PGND B.Cu pours stay open because PE is routed through them (the filler keeps the 5 mm)\n"
    "    for z in zone_plan():\n"
    "        if z['layer'] not in ROUTING_LAYERS or not z.get('router_keepout', True):\n"
    "            continue\n"
    "        rects = z.get('keepout_rects')\n"
    "        if rects is None:\n"
    "            xs = [p[0] for p in z['polygon']]; ys = [p[1] for p in z['polygon']]\n"
    "            rects = [[min(xs), min(ys), max(xs), max(ys)]]\n"
    "        for r in rects:\n"
    "            keepouts.append(dict(layer=z['layer'], rect=list(r), net=z['net'], vias=True))\n"
    "    # barrier strip edges: outside the pad-row notches no copper between HV_LIMIT_Y - 0.3 and the strip, nor between the strip\n"
    "    # and SELV_START_Y (the 9 mm rule counts from the opposite pad rows: HV copper <= 139.6, SELV copper >= 150.4)\n"
    "    rows = barrier_pad_rows(boxes)\n"
    "    for hv_side, (ya, yb) in ((True, (139.6, ISO_STRIP[0] + 0.5)), (False, (149.0, 150.4))):\n"
    "        notches = sorted((r[0] - 0.3, r[2] + 0.3) for r in rows if (r[1] < BARRIER_Y) == hv_side)\n"
    "        x = 0.0\n"
    "        for x0, x1 in notches:\n"
    "            if x0 > x:\n"
    "                keepouts.append(dict(layer=None, rect=[x, ya, x0, yb], net=None, vias=True))\n"
    "            x = max(x, x1)\n"
    "        keepouts.append(dict(layer=None, rect=[x, ya, WIDTH, yb], net=None, vias=True))\n"
    "    # ladder feed vias and stubs: 3 mm outer rule against the sensing-island escapes\n"
    "    for g in via_groups():\n"
    "        if g['count'] == (1, 1):\n"
    "            x0, y0 = g['origin']; r = g.get('diameter', HV_VIA[0]) / 2 + 3.0\n"
    "            keepouts.append(dict(layer=None, rect=[x0 - r, y0 - r, x0 + r, y0 + r], net=g['net'], vias=True))\n"
    "    plan = routing_plan(output_pcb, tracks, vias, skip_pads, keepouts)\n")
rep("             'PE': dict(width=2.0, clearance=5.0),", "             'PE': dict(width=2.0, clearance=5.3),  # 5.0 mm rule plus grid rounding of the 2.0 mm track")

# ---- build_power: skip_pads only for pads with an in-pad via, stubs, D5 track, rip-up in the plan ------------------------------
rep("    pad_vias = hv_pad_vias(boxes)\n"
    "    vias += pad_vias\n"
    "    skip_pads = [[r, n] for (r, n), b in boxes.items() if b['smd'] and b['net'] == 'PGND' and r not in BARRIER_REFS]\n"
    "    tracks = hv_chain_tracks(boxes)\n",
    "    pad_vias = hv_pad_vias(boxes)\n"
    "    vias += pad_vias\n"
    "    via_pads = {tuple(v['pad']) for v in pad_vias if v.get('pad')}\n"
    "    skip_pads = [[r, n] for (r, n), b in boxes.items() if b['smd'] and b['net'] == 'PGND' and r not in BARRIER_REFS and (r, n) in via_pads]\n"
    "    tracks, chain_issues = hv_chain_tracks(boxes)\n"
    "    tracks += feed_stubs(boxes) + d5_sw_track(boxes)\n"
    "    result['chain_issues'] = chain_issues\n")
rep("        'prune_vias': True, 'fill': True, 'save': str(save), 'strict': False, 'max_nodes': MAX_NODES,\n"
    "        'signal_order_trials': SIGNAL_ORDER_TRIALS,\n",
    "        'prune_vias': True, 'fill': True, 'save': str(save), 'strict': False, 'max_nodes': MAX_NODES,\n"
    "        'signal_order_trials': SIGNAL_ORDER_TRIALS, 'ripup_rounds': RIPUP_ROUNDS,\n")
rep("                  pre_routed=dict(tracks=len(tracks), vias=len(vias), hv_pad_vias=len(pad_vias), via_groups=via_groups(), skip_pads=skip_pads))\n",
    "                  pre_routed=dict(tracks=len(tracks), vias=len(vias), hv_pad_vias=len(pad_vias), via_groups=via_groups(), skip_pads=skip_pads,\n"
    "                                  chain_issues=chain_issues))\n")

# ---- notes -------------------------------------------------------------------------------------------------------------------
rep("    'Only the kicad-cli DRC manifest (schematic parity, severity-all) is verification; the router report is a geometric proposal.',\n]",
    "    'Only the kicad-cli DRC manifest (schematic parity, severity-all) is verification; the router report is a geometric proposal.',\n"
    "    'Stage 3 corrections (from the zones-only DRC experiment): chain parts on the pin-field pitch with courtyard-contained stubs, DAMP_MID '\n"
    "    'bypass, LED / 1206 feeds through F.Cu zone patches and 3 mm vias, terminals re-pitched for the REDCUBE pin-field gap, VIN In2 backbone '\n"
    "    'clear of the VOUT In2 bar, HV ladders in one row with via feeds, driver islands east of / below the HF-tier via rings with the HV '\n"
    "    'via rings and HV pads reserved for the auto-placer, snubber on F.Cu, VOUT_L without vias, PGND right strip stitched, small PGND pads '\n"
    "    'routed by the fanout, router budget 600k nodes / 2 trials / rip-up.',\n]")

target.write_text(s, encoding='utf-8')
print('stage-3 patch applied to', target)
