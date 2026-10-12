# Routing quality

Status: measured - human review required
Board: `examples\sic-buck-400v-200v-5kw\kicad\power_board\AIPE_SiC_Buck_Power.kicad_pcb` (sha256 dcd148fbdf65, pcbnew 10.0.7)
Parameters: {"short_mm": 0.5, "l_short_mm": 1.0, "straight_tol_deg": 5.0, "tangent_tol_deg": 1.0, "min_turn_deg": 40.0, "quantum_nm": 1000, "efficiency_min_span_mm": 2.0}

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| board | 2991 | 145 | 606 | 5545.6 | 1121 | 583 | 110 | 124 | 26 | 1225 | 32.71 | 0.8061 |
| B.Cu | 1091 | 66 | 0 | 2089.6 | 472 | 202 | 56 | 54 | 9 | 471 | 34.94 | 0.8061 |
| F.Cu | 1257 | 49 | 0 | 1932.5 | 433 | 167 | 54 | 39 | 9 | 491 | 33.84 | 0.8061 |
| In2.Cu | 643 | 30 | 0 | 1523.6 | 216 | 214 | 0 | 31 | 8 | 263 | 28.22 | 0.8061 |

## Attribution

| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |
|---|---|---|---|---|---|---|---|---|---|
| pad_link | 742 | 1 | 1361.9 | 266 | 22 | 65 | 0 | 0 | 132 |
| router | 2249 | 144 | 4183.7 | 855 | 561 | 45 | 124 | 26 | 1093 |

## Arcs

count 145, joints 287, discontinuous joints 0, radius mm {'min': 0.3044, 'median': 0.5004, 'max': 0.6965}

## Remaining 90-degree bends by reason

| reason | count |
|---|---|
| leg_too_short | 614 |
| pad_exit | 252 |
| unexplained | 141 |
| pad_link | 71 |
| clearance | 43 |

## Worst nets (bends 90)

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RESET_N | 102 | 3 | 3 | 123.4 | 80 | 14 | 1 | 8 | 0 | 74 | 76.99 | 0.8446 |
| PWM_L | 87 | 4 | 7 | 106.7 | 60 | 12 | 2 | 7 | 0 | 58 | 69.33 | 0.8702 |
| RDY_H | 71 | 2 | 2 | 124.7 | 52 | 11 | 3 | 7 | 1 | 50 | 52.95 | 0.7729 |
| VEE_L | 113 | 4 | 16 | 94.8 | 47 | 19 | 1 | 4 | 2 | 56 | 70.65 | 0.774 |
| GNDP_S | 98 | 3 | 9 | 114.9 | 46 | 29 | 0 | 5 | 2 | 50 | 65.26 | 0.8003 |
| PG_BIAS_H_N | 85 | 7 | 4 | 257.0 | 46 | 25 | 0 | 4 | 0 | 40 | 27.63 | 0.5529 |
| VOUT_SENSE | 77 | 0 | 8 | 69.2 | 46 | 18 | 1 | 6 | 1 | 41 | 93.98 | 0.8166 |
| 12V_BIAS_S | 64 | 3 | 6 | 96.4 | 44 | 7 | 0 | 4 | 0 | 31 | 52.89 | 0.6964 |
| 3V3 (zone) | 263 | 12 | 22 | 417.8 | 41 | 33 | 6 | 3 | 1 | 113 | 19.15 | 0.872 |
| 12V_PROT | 96 | 7 | 14 | 261.8 | 35 | 27 | 2 | 6 | 1 | 35 | 24.45 | 0.8914 |
| ISENSE_REF | 72 | 0 | 5 | 86.3 | 32 | 15 | 2 | 6 | 0 | 37 | 56.78 | 0.7799 |
| VIN_SENSE | 52 | 3 | 5 | 68.8 | 30 | 11 | 1 | 4 | 0 | 22 | 61.0 | 0.7165 |
| OC_N | 52 | 1 | 6 | 72.8 | 25 | 17 | 2 | 2 | 0 | 30 | 60.42 | 0.8079 |
| FAULT_N | 33 | 0 | 3 | 32.5 | 24 | 4 | 1 | 3 | 1 | 20 | 89.24 | 0.8644 |
| VDD_L | 61 | 0 | 6 | 78.8 | 23 | 12 | 2 | 3 | 0 | 21 | 46.97 | 0.833 |

DRC: passed findings {'violations': 0, 'unconnected_items': 0, 'schematic_parity': 0} same board bytes: True (examples\sic-buck-400v-200v-5kw\verification\drc\20261012T090308Z-drc-8fd50803\run.json)

Notes: geometry only: no inductance, EMI or current-capacity claim; bends are measured at joints of two straight items; arc joints are judged by tangency; chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure); attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'
