# Routing quality

Status: measured - human review required
Board: `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\releases\v2\kicad\power_board\AIPE_SiC_Buck_Power.kicad_pcb` (sha256 b1bb5698194b, pcbnew 10.0.7)
Parameters: {"short_mm": 0.5, "l_short_mm": 1.0, "straight_tol_deg": 5.0, "tangent_tol_deg": 1.0, "min_turn_deg": 40.0, "quantum_nm": 1000, "efficiency_min_span_mm": 2.0}

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| board | 4755 | 0 | 606 | 5744.6 | 3609 | 6 | 109 | 382 | 12 | 2914 | 64.83 | 0.7759 |
| B.Cu | 1824 | 0 | 0 | 2177.6 | 1471 | 4 | 56 | 150 | 10 | 1178 | 70.31 | 0.7759 |
| F.Cu | 1765 | 0 | 0 | 1988.6 | 1154 | 2 | 53 | 121 | 1 | 940 | 60.8 | 0.7759 |
| In2.Cu | 1166 | 0 | 0 | 1578.4 | 984 | 0 | 0 | 111 | 1 | 796 | 62.34 | 0.7759 |

## Attribution

| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |
|---|---|---|---|---|---|---|---|---|---|
| pad_link | 741 | 0 | 1355.4 | 285 | 3 | 65 | 0 | 0 | 132 |
| router | 4014 | 0 | 4389.2 | 3324 | 3 | 44 | 382 | 12 | 2782 |

## Arcs

count 0, joints 0, discontinuous joints 0

## Remaining 90-degree bends by reason

| reason | count |
|---|---|
| unexplained | 3324 |
| pad_link | 285 |

## Worst nets (bends 90)

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 12V_PROT | 261 | 0 | 14 | 276.6 | 234 | 0 | 2 | 19 | 0 | 192 | 85.31 | 0.8432 |
| 3V3 (zone) | 389 | 0 | 22 | 433.9 | 211 | 2 | 5 | 24 | 0 | 226 | 50.24 | 0.8296 |
| FLT_H_N | 198 | 0 | 11 | 166.3 | 182 | 0 | 4 | 18 | 0 | 152 | 111.85 | 0.8078 |
| PG_BIAS_H_N | 182 | 0 | 4 | 268.5 | 174 | 2 | 0 | 20 | 0 | 139 | 65.54 | 0.529 |
| RESET_N | 144 | 0 | 3 | 129.2 | 138 | 1 | 1 | 14 | 1 | 114 | 108.32 | 0.8064 |
| PWM_L | 136 | 0 | 7 | 111.6 | 125 | 0 | 2 | 15 | 0 | 103 | 113.77 | 0.8316 |
| GNDP_S | 142 | 0 | 9 | 119.3 | 122 | 0 | 0 | 12 | 1 | 97 | 102.26 | 0.7684 |
| PWM_H | 127 | 0 | 4 | 132.3 | 121 | 0 | 2 | 11 | 0 | 98 | 92.98 | 0.8334 |
| FLT_L_N | 130 | 0 | 6 | 120.0 | 120 | 0 | 3 | 13 | 1 | 99 | 102.5 | 0.8455 |
| VEE_L | 148 | 0 | 16 | 100.1 | 105 | 0 | 1 | 9 | 1 | 91 | 105.87 | 0.7202 |
| RELAY_ON | 108 | 0 | 5 | 203.8 | 101 | 0 | 2 | 13 | 1 | 74 | 50.53 | 0.8735 |
| BIAS_EN | 107 | 0 | 10 | 147.9 | 95 | 0 | 2 | 13 | 0 | 77 | 65.6 | 0.864 |
| RDY_L | 101 | 0 | 4 | 112.3 | 89 | 0 | 4 | 10 | 0 | 71 | 82.82 | 0.854 |
| LS_FB_VDD | 111 | 0 | 4 | 72.8 | 87 | 0 | 0 | 9 | 0 | 76 | 119.49 | 0.7655 |
| 12V_BIAS_S | 96 | 0 | 6 | 100.1 | 86 | 0 | 0 | 9 | 0 | 58 | 85.94 | 0.6702 |

Notes: geometry only: no inductance, EMI or current-capacity claim; bends are measured at joints of two straight items; arc joints are judged by tangency; chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure); attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'
