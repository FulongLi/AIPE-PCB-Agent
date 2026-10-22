# Routing quality

Status: measured - human review required
Board: `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\secondary-power\dab-secondary.kicad_pcb` (sha256 27b69dd7dd0d, pcbnew 10.0.6)
Parameters: {"short_mm": 0.5, "l_short_mm": 1.0, "straight_tol_deg": 5.0, "tangent_tol_deg": 1.0, "min_turn_deg": 40.0, "quantum_nm": 1000, "efficiency_min_span_mm": 2.0}

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| board | 2598 | 0 | 449 | 7090.0 | 39 | 1062 | 161 | 14 | 14 | 606 | 17.8 | 0.871 |
| B.Cu | 514 | 0 | 0 | 2626.2 | 9 | 319 | 0 | 2 | 1 | 53 | 12.49 | 0.871 |
| F.Cu | 2017 | 0 | 0 | 3882.0 | 28 | 712 | 161 | 12 | 13 | 547 | 23.21 | 0.871 |
| In2.Cu | 67 | 0 | 0 | 581.9 | 2 | 31 | 0 | 0 | 0 | 6 | 5.67 | 0.871 |

## Attribution

| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |
|---|---|---|---|---|---|---|---|---|---|
| pad_link | 1251 | 0 | 2334.7 | 11 | 446 | 101 | 0 | 2 | 264 |
| pre_routed | 50 | 0 | 155.5 | 0 | 0 | 0 | 0 | 0 | 0 |
| router | 1297 | 0 | 4599.8 | 28 | 616 | 60 | 14 | 12 | 342 |

## Arcs

count 0, joints 0, discontinuous joints 0

## Remaining 90-degree bends by reason

| reason | count |
|---|---|
| policy_diagonal | 28 |
| pad_link | 9 |
| unexplained | 2 |

## Worst nets (bends 90)

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PGND (zone) | 82 | 0 | 43 | 101.2 | 5 | 0 | 0 | 0 | 0 | 32 | 4.94 | 1.0 |
| PG_BIAS_N | 62 | 0 | 8 | 260.0 | 5 | 25 | 6 | 1 | 1 | 19 | 13.84 | 0.9368 |
| GND_CTRL (zone) | 102 | 0 | 48 | 67.8 | 4 | 0 | 0 | 0 | 0 | 49 | 5.9 | - |
| FBVDD_BH | 18 | 0 | 2 | 33.5 | 3 | 9 | 2 | 0 | 0 | 5 | 41.79 | 0.7456 |
| S_FBVDD | 20 | 0 | 0 | 38.7 | 3 | 11 | 1 | 0 | 0 | 4 | 38.81 | 0.6925 |
| VEE_BH | 67 | 0 | 10 | 117.8 | 2 | 29 | 4 | 0 | 0 | 15 | 29.71 | 0.7811 |
| VMOD_IN | 22 | 0 | 4 | 45.4 | 2 | 12 | 2 | 1 | 0 | 8 | 35.27 | 0.6692 |
| BIAS_ENF | 19 | 0 | 0 | 18.0 | 1 | 6 | 5 | 0 | 0 | 5 | 66.52 | 0.5579 |
| DESAT_BL | 7 | 0 | 0 | 10.5 | 1 | 3 | 0 | 0 | 0 | 1 | 38.11 | 0.6597 |
| FBVEE_BH | 13 | 0 | 2 | 17.9 | 1 | 5 | 1 | 0 | 0 | 4 | 39.11 | 0.6181 |
| FLT_AH_N | 23 | 0 | 0 | 98.0 | 1 | 17 | 2 | 0 | 1 | 4 | 20.41 | 0.8902 |
| FLT_AL_N | 10 | 0 | 1 | 70.7 | 1 | 3 | 2 | 0 | 1 | 2 | 8.49 | 0.9587 |
| FLT_BH_N | 12 | 0 | 1 | 89.7 | 1 | 6 | 2 | 0 | 0 | 1 | 10.04 | 0.8959 |
| RDR_AL | 11 | 0 | 4 | 24.8 | 1 | 6 | 0 | 0 | 0 | 1 | 28.24 | 0.8151 |
| RDY_AH | 14 | 0 | 4 | 93.5 | 1 | 6 | 2 | 0 | 0 | 2 | 9.62 | 0.9565 |

DRC: failed findings {'violations': 18, 'unconnected_items': 23, 'schematic_parity': 0} same board bytes: True (D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\verification\drc\20261021T114746Z-drc-9d8d1f3f\run.json)

Notes: geometry only: no inductance, EMI or current-capacity claim; bends are measured at joints of two straight items; arc joints are judged by tangency; chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure); attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'
