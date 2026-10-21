# Routing quality

Status: measured - human review required
Board: `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\primary-power\dab-primary.kicad_pcb` (sha256 a8067aee4d8b, pcbnew 10.0.6)
Parameters: {"short_mm": 0.5, "l_short_mm": 1.0, "straight_tol_deg": 5.0, "tangent_tol_deg": 1.0, "min_turn_deg": 40.0, "quantum_nm": 1000, "efficiency_min_span_mm": 2.0}

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| board | 2501 | 0 | 436 | 6820.4 | 41 | 995 | 153 | 13 | 13 | 573 | 17.43 | 0.8866 |
| B.Cu | 488 | 0 | 0 | 2538.2 | 4 | 296 | 0 | 0 | 1 | 40 | 11.82 | 0.8866 |
| F.Cu | 1926 | 0 | 0 | 3685.0 | 33 | 656 | 153 | 13 | 12 | 525 | 22.85 | 0.8866 |
| In2.Cu | 87 | 0 | 0 | 597.1 | 4 | 43 | 0 | 0 | 0 | 8 | 7.87 | 0.8866 |

## Attribution

| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |
|---|---|---|---|---|---|---|---|---|---|
| pad_link | 1217 | 0 | 2301.6 | 14 | 441 | 96 | 0 | 2 | 252 |
| pre_routed | 50 | 0 | 155.5 | 0 | 0 | 0 | 0 | 0 | 0 |
| router | 1234 | 0 | 4363.3 | 27 | 554 | 57 | 13 | 11 | 321 |

## Arcs

count 0, joints 0, discontinuous joints 0

## Remaining 90-degree bends by reason

| reason | count |
|---|---|
| policy_diagonal | 26 |
| pad_link | 10 |
| unexplained | 5 |

## Worst nets (bends 90)

| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PGND (zone) | 76 | 0 | 37 | 104.0 | 11 | 0 | 0 | 0 | 0 | 27 | 10.58 | 0.9538 |
| FBVDD_BH | 18 | 0 | 2 | 33.5 | 3 | 9 | 2 | 0 | 0 | 5 | 41.79 | 0.7456 |
| FLT_AH_N | 22 | 0 | 1 | 98.0 | 2 | 14 | 2 | 0 | 1 | 3 | 18.37 | 0.8976 |
| FLT_BH_N | 13 | 0 | 1 | 91.7 | 2 | 6 | 2 | 0 | 0 | 1 | 10.91 | 0.8782 |
| GND_CTRL (zone) | 94 | 0 | 45 | 61.4 | 2 | 0 | 0 | 0 | 0 | 46 | 3.26 | - |
| RDY_AH | 12 | 0 | 3 | 97.2 | 2 | 4 | 2 | 0 | 0 | 2 | 8.23 | 0.9155 |
| RDY_BH | 10 | 0 | 3 | 98.7 | 2 | 3 | 1 | 0 | 0 | 2 | 6.08 | 0.8555 |
| S_VEEA | 20 | 0 | 0 | 33.1 | 2 | 9 | 1 | 0 | 0 | 5 | 36.23 | 0.8118 |
| VADC_IN | 12 | 0 | 0 | 16.7 | 2 | 5 | 1 | 0 | 0 | 4 | 47.94 | 0.8145 |
| VEE_BH | 67 | 0 | 10 | 117.8 | 2 | 29 | 4 | 0 | 0 | 15 | 29.71 | 0.7811 |
| VSNS_P | 9 | 0 | 1 | 100.5 | 2 | 2 | 2 | 1 | 0 | 3 | 5.97 | 0.8992 |
| DESAT_BL | 7 | 0 | 0 | 10.5 | 1 | 3 | 0 | 0 | 0 | 1 | 38.11 | 0.6597 |
| FBVEE_BH | 13 | 0 | 2 | 17.9 | 1 | 5 | 1 | 0 | 0 | 4 | 39.11 | 0.6181 |
| PWMF_AH | 17 | 0 | 2 | 56.1 | 1 | 6 | 4 | 2 | 0 | 3 | 19.62 | 0.9618 |
| RDR_AL | 11 | 0 | 4 | 24.8 | 1 | 6 | 0 | 0 | 0 | 1 | 28.24 | 0.8151 |

DRC: failed findings {'violations': 18, 'unconnected_items': 26, 'schematic_parity': 0} same board bytes: True (D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\verification\drc\20261021T114704Z-drc-8c4572df\run.json)

Notes: geometry only: no inductance, EMI or current-capacity claim; bends are measured at joints of two straight items; arc joints are judged by tangency; chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure); attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'
