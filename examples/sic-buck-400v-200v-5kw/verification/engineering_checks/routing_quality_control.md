# Routing quality

Status: measured - human review required
Board: `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\kicad\control_board\AIPE_SiC_Buck_Control.kicad_pcb` (sha256 a3f3604a516c, pcbnew 10.0.7)
Parameters: {"short_mm": 0.5, "l_short_mm": 1.0, "straight_tol_deg": 5.0, "tangent_tol_deg": 1.0, "min_turn_deg": 40.0, "quantum_nm": 1000, "efficiency_min_span_mm": 2.0}

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| board | 4262 | 261 | 798 | 6700.7 | 1233 | 839 | 15 | 144 | 41 | 1937 | 31.15 | 0.8272 |
| B.Cu | 1865 | 138 | 0 | 3305.4 | 634 | 478 | 0 | 80 | 23 | 870 | 33.64 | 0.8272 |
| F.Cu | 2357 | 111 | 0 | 3284.6 | 590 | 345 | 15 | 64 | 16 | 1051 | 28.92 | 0.8272 |
| In2.Cu | 40 | 12 | 0 | 110.6 | 9 | 16 | 0 | 0 | 2 | 16 | 22.6 | 0.8272 |

## Attribution

| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |
|---|---|---|---|---|---|---|---|---|---|
| pad_link | 981 | 2 | 769.8 | 84 | 15 | 15 | 0 | 0 | 459 |
| pre_routed | 142 | 0 | 258.8 | 3 | 0 | 0 | 0 | 0 | 1 |
| router | 3139 | 259 | 5672.1 | 1146 | 824 | 0 | 144 | 41 | 1477 |

## Arcs

count 261, joints 519, discontinuous joints 0, radius mm {'min': 0.1962, 'median': 0.3968, 'max': 0.8001}

## Remaining 90-degree bends by reason

| reason | count |
|---|---|
| leg_too_short | 723 |
| unexplained | 341 |
| pad_exit | 63 |
| pad_link | 52 |
| clearance | 51 |
| pre_routed | 3 |

## Worst nets (bends 90)

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FAN_TACH | 122 | 6 | 8 | 205.0 | 72 | 32 | 0 | 12 | 0 | 68 | 50.72 | 0.6081 |
| PG_BIAS_S_N | 115 | 8 | 15 | 201.0 | 64 | 22 | 0 | 9 | 0 | 62 | 42.79 | 0.8838 |
| ADC_VOUT | 93 | 6 | 14 | 131.9 | 45 | 24 | 0 | 7 | 4 | 48 | 52.31 | 0.8681 |
| ESTOP_N | 215 | 17 | 24 | 384.6 | 44 | 37 | 0 | 5 | 3 | 112 | 21.06 | 0.8753 |
| PG_BIAS_L_N | 179 | 6 | 12 | 222.2 | 39 | 16 | 0 | 6 | 1 | 122 | 24.75 | 0.8962 |
| ADC_TEMP_CTRL | 65 | 1 | 4 | 39.6 | 36 | 19 | 0 | 3 | 2 | 45 | 138.79 | 0.582 |
| 3V3 (zone) | 195 | 0 | 84 | 121.4 | 35 | 0 | 0 | 3 | 0 | 101 | 28.84 | 0.791 |
| RESET_N | 47 | 0 | 2 | 54.2 | 35 | 8 | 0 | 5 | 0 | 34 | 79.27 | 0.817 |
| FLT_12V_N | 72 | 3 | 16 | 146.1 | 30 | 17 | 0 | 3 | 0 | 30 | 32.17 | 0.8896 |
| OC_N | 120 | 15 | 10 | 193.5 | 30 | 16 | 1 | 2 | 0 | 57 | 24.29 | 0.8427 |
| FLT_L_N | 69 | 2 | 10 | 89.2 | 29 | 22 | 1 | 4 | 2 | 32 | 58.28 | 0.758 |
| ARM | 77 | 3 | 10 | 93.9 | 26 | 19 | 0 | 3 | 1 | 45 | 47.9 | 0.8221 |
| GND_CTRL (zone) | 296 | 0 | 161 | 227.5 | 26 | 0 | 0 | 0 | 1 | 131 | 11.43 | 0.8215 |
| ISENSE | 63 | 6 | 5 | 114.5 | 26 | 18 | 0 | 2 | 2 | 28 | 38.42 | 0.7501 |
| OVP_IN_N | 52 | 0 | 5 | 66.6 | 26 | 12 | 0 | 2 | 1 | 25 | 57.07 | 0.7968 |

DRC: passed findings {'violations': 0, 'unconnected_items': 0, 'schematic_parity': 0} same board bytes: True (D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\verification\drc\20261012T103755Z-drc-0a4fa5cf\run.json)

Baseline: `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\verification\engineering_checks\routing_quality_control_v2.json`

| metric | baseline | this | delta |
|---|---|---|---|
| segments | 5995 | 4262 | -1733 |
| arcs | 0 | 261 | 261 |
| vias | 798 | 798 | 0 |
| length_mm | 7055.216 | 6700.663 | -354.553 |
| arc_length_mm | 0 | 78.968 | 78.968 |
| joints | 4094 | 2619 | -1475 |
| bends_90 | 4069 | 1233 | -2836 |
| bends_45 | 0 | 839 | 839 |
| bends_other | 12 | 15 | 3 |
| direction_changes | 4081 | 2087 | -1994 |
| stair_runs | 435 | 144 | -291 |
| zigzag_runs | 31 | 41 | 10 |
| short_run_segments | 2957 | 1023 | -1934 |
| short_segments | 3677 | 1937 | -1740 |
| short_segment_runs | 518 | 204 | -314 |
| arc_joints | 0 | 519 | 519 |
| arc_joints_discontinuous | 0 | 0 | 0 |
| chains | 1901 | 1904 | 3 |
| degree2_joints | 4691 | 2696 | -1995 |
| degree2_bends_90 | 4184 | 1339 | -2845 |
| bends_per_100mm | 57.84 | 31.15 | -26.69 |
| efficiency | 0.7802 | 0.8272 | 0.047 |

Notes: geometry only: no inductance, EMI or current-capacity claim; bends are measured at joints of two straight items; arc joints are judged by tangency; chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure); attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'
