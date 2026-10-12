# Routing quality

Status: measured - human review required
Board: `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\releases\v2\kicad\control_board\AIPE_SiC_Buck_Control.kicad_pcb` (sha256 dead06ed18d8, pcbnew 10.0.7)
Parameters: {"short_mm": 0.5, "l_short_mm": 1.0, "straight_tol_deg": 5.0, "tangent_tol_deg": 1.0, "min_turn_deg": 40.0, "quantum_nm": 1000, "efficiency_min_span_mm": 2.0}

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| board | 5995 | 0 | 798 | 7055.2 | 4069 | 0 | 12 | 435 | 31 | 3677 | 57.84 | 0.7802 |
| B.Cu | 2861 | 0 | 0 | 3506.2 | 2252 | 0 | 0 | 250 | 21 | 1888 | 64.23 | 0.7802 |
| F.Cu | 3004 | 0 | 0 | 3429.1 | 1691 | 0 | 12 | 177 | 6 | 1690 | 49.66 | 0.7802 |
| In2.Cu | 130 | 0 | 0 | 119.9 | 126 | 0 | 0 | 8 | 4 | 99 | 105.11 | 0.7802 |

## Attribution

| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |
|---|---|---|---|---|---|---|---|---|---|
| pad_link | 1105 | 0 | 996.7 | 96 | 0 | 12 | 0 | 0 | 459 |
| router | 4890 | 0 | 6058.6 | 3973 | 0 | 0 | 435 | 31 | 3218 |

## Arcs

count 0, joints 0, discontinuous joints 0

## Remaining 90-degree bends by reason

| reason | count |
|---|---|
| unexplained | 3973 |
| pad_link | 96 |

## Worst nets (bends 90)

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PG_BIAS_S_N | 237 | 0 | 15 | 213.2 | 216 | 0 | 0 | 22 | 0 | 180 | 101.32 | 0.8332 |
| DSP_TRIP_N | 191 | 0 | 21 | 224.4 | 166 | 0 | 0 | 21 | 0 | 126 | 73.97 | 0.7893 |
| FAN_TACH | 167 | 0 | 8 | 214.0 | 155 | 0 | 0 | 18 | 0 | 110 | 72.43 | 0.5824 |
| ESTOP_N | 271 | 0 | 24 | 402.5 | 154 | 0 | 0 | 17 | 0 | 169 | 38.26 | 0.8326 |
| FAULT_N | 297 | 0 | 16 | 319.7 | 140 | 0 | 0 | 13 | 2 | 207 | 43.79 | 0.6895 |
| OC_N | 187 | 0 | 10 | 204.1 | 129 | 0 | 1 | 14 | 0 | 124 | 63.68 | 0.7948 |
| PG_BIAS_L_N | 243 | 0 | 12 | 228.5 | 124 | 0 | 0 | 12 | 1 | 182 | 54.26 | 0.8683 |
| XRS_N | 156 | 0 | 21 | 226.1 | 122 | 0 | 1 | 17 | 0 | 84 | 54.4 | 0.8054 |
| ADC_VOUT | 134 | 0 | 14 | 139.2 | 116 | 0 | 0 | 14 | 2 | 88 | 83.3 | 0.8199 |
| UVLO_N | 110 | 0 | 8 | 77.2 | 98 | 0 | 0 | 9 | 2 | 82 | 127.02 | 0.8254 |
| SPARE_D1 | 101 | 0 | 6 | 121.0 | 94 | 0 | 0 | 10 | 1 | 74 | 77.65 | 0.8087 |
| PG_BIAS_H_N | 105 | 0 | 9 | 163.0 | 84 | 0 | 1 | 9 | 1 | 66 | 52.14 | 0.8054 |
| FLT_12V_N | 105 | 0 | 16 | 151.7 | 83 | 0 | 0 | 10 | 0 | 61 | 54.73 | 0.8563 |
| I12V_MON | 90 | 0 | 2 | 149.8 | 81 | 0 | 0 | 11 | 0 | 57 | 54.09 | 0.6951 |
| VIN_SENSE | 90 | 0 | 8 | 111.5 | 74 | 0 | 0 | 9 | 0 | 56 | 66.35 | 0.7858 |

Notes: geometry only: no inductance, EMI or current-capacity claim; bends are measured at joints of two straight items; arc joints are judged by tangency; chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure); attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'
