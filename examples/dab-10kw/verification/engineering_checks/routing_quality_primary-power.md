# Routing quality

Status: measured - human review required
Board: `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\primary-power\dab-primary.kicad_pcb` (sha256 fd10e2ec8827, pcbnew 10.0.6)
Parameters: {"short_mm": 0.5, "l_short_mm": 1.0, "straight_tol_deg": 5.0, "tangent_tol_deg": 1.0, "min_turn_deg": 40.0, "quantum_nm": 1000, "efficiency_min_span_mm": 2.0}

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| board | 2470 | 0 | 411 | 5907.6 | 180 | 778 | 86 | 17 | 12 | 675 | 17.67 | 0.8751 |
| B.Cu | 454 | 0 | 0 | 2238.6 | 8 | 260 | 0 | 2 | 0 | 39 | 11.97 | 0.8751 |
| F.Cu | 1949 | 0 | 0 | 3236.3 | 170 | 479 | 86 | 15 | 12 | 630 | 22.71 | 0.8751 |
| In2.Cu | 67 | 0 | 0 | 432.8 | 2 | 39 | 0 | 0 | 0 | 6 | 9.47 | 0.8751 |

## Attribution

| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |
|---|---|---|---|---|---|---|---|---|---|
| pad_link | 1246 | 0 | 2076.5 | 108 | 346 | 74 | 0 | 1 | 247 |
| pre_routed | 20 | 0 | 84.0 | 0 | 0 | 0 | 0 | 0 | 0 |
| router | 1204 | 0 | 3747.1 | 72 | 432 | 12 | 17 | 11 | 428 |

## Arcs

count 0, joints 0, discontinuous joints 0

## Remaining 90-degree bends by reason

| reason | count |
|---|---|
| pad_link | 106 |
| policy_diagonal | 56 |
| unexplained | 18 |

## Worst nets (bends 90)

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PGND (zone) | 82 | 0 | 36 | 104.5 | 18 | 0 | 0 | 0 | 0 | 30 | 17.23 | 0.929 |
| GNDP_AL | 66 | 0 | 4 | 56.1 | 9 | 4 | 2 | 0 | 0 | 29 | 26.76 | 0.9854 |
| GNDP_BH | 65 | 0 | 4 | 54.9 | 9 | 5 | 2 | 0 | 0 | 30 | 29.16 | 0.9774 |
| GNDP_BL | 68 | 0 | 4 | 68.1 | 9 | 3 | 2 | 0 | 0 | 31 | 20.56 | 0.9928 |
| GNDP_AH | 62 | 0 | 7 | 40.7 | 8 | 3 | 2 | 0 | 0 | 32 | 31.92 | 0.9729 |
| GNDP_S | 59 | 0 | 0 | 87.5 | 8 | 8 | 2 | 0 | 0 | 15 | 20.56 | 0.6736 |
| GND_CTRL (zone) | 90 | 0 | 41 | 57.7 | 8 | 0 | 0 | 0 | 0 | 45 | 13.87 | 1.0 |
| VEE_BH | 72 | 0 | 10 | 96.5 | 7 | 14 | 3 | 0 | 0 | 21 | 24.87 | 0.6339 |
| VEE_BL | 79 | 0 | 6 | 112.9 | 7 | 23 | 3 | 0 | 0 | 22 | 29.23 | 0.5253 |
| PG_BIAS_N | 15 | 0 | 1 | 47.3 | 6 | 3 | 0 | 0 | 0 | 6 | 19.01 | 0.8007 |
| RDR_AH | 17 | 0 | 2 | 16.0 | 6 | 9 | 0 | 2 | 0 | 9 | 93.74 | 0.7777 |
| VEE_AH | 71 | 0 | 7 | 106.7 | 6 | 20 | 3 | 0 | 0 | 19 | 27.17 | 0.6954 |
| VEE_AL | 71 | 0 | 7 | 135.7 | 6 | 20 | 3 | 0 | 0 | 18 | 21.37 | 0.6625 |
| NTCR_BL | 8 | 0 | 0 | 11.1 | 5 | 2 | 0 | 0 | 0 | 3 | 63.19 | 0.5923 |
| KS_BH | 72 | 0 | 7 | 113.9 | 4 | 30 | 0 | 2 | 0 | 17 | 29.84 | 0.8328 |

DRC: failed findings {'violations': 57, 'unconnected_items': 82, 'schematic_parity': 0} same board bytes: True (D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\verification\drc\20261021T071523Z-drc-39f76185\run.json)

Notes: geometry only: no inductance, EMI or current-capacity claim; bends are measured at joints of two straight items; arc joints are judged by tangency; chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure); attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'
