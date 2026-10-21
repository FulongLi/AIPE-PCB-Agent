# Routing quality

Status: measured - human review required
Board: `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\secondary-power\dab-secondary.kicad_pcb` (sha256 950f865e7226, pcbnew 10.0.6)
Parameters: {"short_mm": 0.5, "l_short_mm": 1.0, "straight_tol_deg": 5.0, "tangent_tol_deg": 1.0, "min_turn_deg": 40.0, "quantum_nm": 1000, "efficiency_min_span_mm": 2.0}

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| board | 2642 | 0 | 440 | 6320.5 | 198 | 869 | 95 | 13 | 12 | 737 | 18.38 | 0.8601 |
| B.Cu | 481 | 0 | 0 | 2432.5 | 9 | 279 | 0 | 2 | 0 | 42 | 11.84 | 0.8601 |
| F.Cu | 2087 | 0 | 0 | 3390.2 | 188 | 545 | 95 | 11 | 12 | 691 | 24.42 | 0.8601 |
| In2.Cu | 74 | 0 | 0 | 497.9 | 1 | 45 | 0 | 0 | 0 | 4 | 9.24 | 0.8601 |

## Attribution

| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |
|---|---|---|---|---|---|---|---|---|---|
| pad_link | 1301 | 0 | 2160.5 | 113 | 356 | 80 | 0 | 1 | 274 |
| pre_routed | 20 | 0 | 84.0 | 0 | 0 | 0 | 0 | 0 | 0 |
| router | 1321 | 0 | 4076.1 | 85 | 513 | 15 | 13 | 11 | 463 |

## Arcs

count 0, joints 0, discontinuous joints 0

## Remaining 90-degree bends by reason

| reason | count |
|---|---|
| pad_link | 110 |
| policy_diagonal | 60 |
| unexplained | 28 |

## Worst nets (bends 90)

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PGND (zone) | 102 | 0 | 41 | 119.4 | 24 | 0 | 0 | 0 | 0 | 36 | 20.11 | 0.8833 |
| GND_CTRL (zone) | 101 | 0 | 44 | 68.8 | 13 | 0 | 0 | 0 | 0 | 48 | 18.89 | 0.6364 |
| GNDP_AH | 64 | 0 | 7 | 48.8 | 10 | 6 | 2 | 0 | 0 | 29 | 36.88 | 0.9571 |
| GNDP_AL | 66 | 0 | 4 | 56.1 | 9 | 4 | 2 | 0 | 0 | 29 | 26.76 | 0.9854 |
| GNDP_BH | 65 | 0 | 4 | 54.9 | 9 | 5 | 2 | 0 | 0 | 30 | 29.16 | 0.9774 |
| GNDP_BL | 68 | 0 | 4 | 68.1 | 9 | 3 | 2 | 0 | 0 | 31 | 20.56 | 0.9928 |
| GNDP_S | 65 | 0 | 4 | 55.1 | 9 | 5 | 2 | 0 | 0 | 30 | 29.03 | 0.9775 |
| PG_BIAS_N | 16 | 0 | 1 | 45.9 | 7 | 2 | 0 | 0 | 0 | 7 | 19.62 | 0.8287 |
| VEE_BH | 74 | 0 | 10 | 95.2 | 7 | 14 | 3 | 0 | 0 | 22 | 25.21 | 0.6677 |
| VEE_BL | 79 | 0 | 6 | 112.9 | 7 | 23 | 3 | 0 | 0 | 22 | 29.23 | 0.5253 |
| RDR_AH | 17 | 0 | 2 | 16.0 | 6 | 9 | 0 | 2 | 0 | 9 | 93.74 | 0.7777 |
| VEE_AH | 71 | 0 | 7 | 106.7 | 6 | 20 | 3 | 0 | 0 | 19 | 27.17 | 0.6954 |
| VEE_AL | 72 | 0 | 9 | 109.7 | 6 | 19 | 3 | 0 | 0 | 19 | 25.53 | 0.7717 |
| NTCR_BL | 8 | 0 | 0 | 11.1 | 5 | 2 | 0 | 0 | 0 | 3 | 63.19 | 0.5923 |
| FBVDD_BH | 20 | 0 | 4 | 21.8 | 4 | 9 | 0 | 0 | 1 | 7 | 59.59 | 0.8962 |

DRC: failed findings {'violations': 37, 'unconnected_items': 81, 'schematic_parity': 0} same board bytes: True (D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\verification\drc\20261021T071639Z-drc-ce8b8c2f\run.json)

Notes: geometry only: no inductance, EMI or current-capacity claim; bends are measured at joints of two straight items; arc joints are judged by tangency; chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure); attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'
