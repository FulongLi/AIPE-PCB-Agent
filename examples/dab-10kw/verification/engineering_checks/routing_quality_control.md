# Routing quality

Status: measured - human review required
Board: `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\control\dab-control.kicad_pcb` (sha256 06229f8a11dc, pcbnew 10.0.6)
Parameters: {"short_mm": 0.5, "l_short_mm": 1.0, "straight_tol_deg": 5.0, "tangent_tol_deg": 1.0, "min_turn_deg": 40.0, "quantum_nm": 1000, "efficiency_min_span_mm": 2.0}

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| board | 2853 | 222 | 610 | 10222.1 | 170 | 952 | 170 | 51 | 20 | 739 | 12.64 | 0.8824 |
| B.Cu | 464 | 71 | 0 | 3797.5 | 2 | 205 | 0 | 0 | 3 | 44 | 5.45 | 0.8824 |
| F.Cu | 1982 | 82 | 0 | 3998.4 | 167 | 580 | 170 | 49 | 15 | 666 | 22.93 | 0.8824 |
| In2.Cu | 407 | 69 | 0 | 2426.2 | 1 | 167 | 0 | 2 | 2 | 29 | 6.92 | 0.8824 |

## Attribution

| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |
|---|---|---|---|---|---|---|---|---|---|
| pad_link | 988 | 1 | 1975.9 | 82 | 293 | 115 | 0 | 1 | 217 |
| pre_routed | 10 | 0 | 11.8 | 0 | 0 | 0 | 0 | 0 | 0 |
| router | 1855 | 221 | 8234.5 | 88 | 659 | 55 | 51 | 19 | 522 |

## Arcs

count 222, joints 437, discontinuous joints 1, radius mm {'min': 0.1962, 'median': 0.3968, 'max': 1.0008}

## Remaining 90-degree bends by reason

| reason | count |
|---|---|
| pad_link | 80 |
| unexplained | 37 |
| leg_too_short | 33 |
| clearance | 18 |
| pad_exit | 2 |

## Worst nets (bends 90)

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GND_CTRL (zone) | 334 | 0 | 131 | 209.0 | 38 | 14 | 22 | 1 | 0 | 156 | 35.41 | 0.8628 |
| 3V3 | 323 | 14 | 25 | 628.8 | 25 | 128 | 11 | 8 | 2 | 120 | 26.08 | 0.8623 |
| RS485_RX | 27 | 6 | 3 | 107.0 | 5 | 10 | 1 | 1 | 1 | 9 | 14.95 | 0.8883 |
| ADC_ITANK_S | 28 | 1 | 2 | 68.2 | 3 | 8 | 2 | 0 | 0 | 8 | 19.05 | 0.8677 |
| ADC_TEMP_P | 21 | 1 | 4 | 83.3 | 3 | 9 | 0 | 1 | 0 | 3 | 14.41 | 0.8156 |
| ADC_TEMP_S | 22 | 1 | 4 | 78.1 | 3 | 9 | 0 | 1 | 0 | 4 | 15.36 | 0.8181 |
| EPWM2A | 20 | 1 | 4 | 102.9 | 3 | 8 | 2 | 0 | 0 | 2 | 12.64 | 0.925 |
| OV_P_OK | 25 | 5 | 2 | 165.4 | 3 | 11 | 1 | 0 | 0 | 5 | 9.07 | 0.4227 |
| ADC_5V | 26 | 2 | 4 | 87.8 | 2 | 11 | 0 | 0 | 0 | 5 | 14.8 | 0.786 |
| ADC_ITANK_P | 18 | 0 | 6 | 67.6 | 2 | 6 | 0 | 1 | 0 | 2 | 11.83 | 0.9768 |
| ADC_VBUS_S | 20 | 0 | 5 | 66.1 | 2 | 8 | 0 | 0 | 0 | 4 | 15.12 | 0.9555 |
| BIAS_EN_MCU | 25 | 1 | 11 | 109.7 | 2 | 8 | 0 | 0 | 0 | 4 | 9.12 | 0.9596 |
| EMU0 | 8 | 1 | 1 | 78.9 | 2 | 3 | 0 | 1 | 0 | 2 | 6.33 | 0.9482 |
| EMU1 | 9 | 1 | 1 | 82.3 | 2 | 4 | 0 | 0 | 0 | 1 | 7.29 | 0.9304 |
| EPWM2B | 22 | 1 | 3 | 204.5 | 2 | 12 | 2 | 0 | 0 | 3 | 7.82 | 0.4794 |

DRC: failed findings {'violations': 28, 'unconnected_items': 24, 'schematic_parity': 0} same board bytes: True (D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\verification\drc\20261021T121733Z-drc-64a4df3c\run.json)

Notes: geometry only: no inductance, EMI or current-capacity claim; bends are measured at joints of two straight items; arc joints are judged by tangency; chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure); attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'
