# Schematic readability - control board (V2 -> V2.2)

`V2`: D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\releases\v2\kicad\control_board  
`V2.2`: D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\kicad\control_board

## Totals (all sheets, root included)

| metric | V2 | V2.2 | delta |
|---|---:|---:|---:|
| sheets | 10 | 9 | -1 |
| continuation_sheets | 1 | 0 | -1 |
| papers | A3 | A2 / A3 | - |
| symbols | 210 | 214 | 4 |
| power_symbols | 3 | 190 | 187 |
| wires | 667 | 1323 | 656 |
| wire_length_mm | 1694.2 | 7752.1 | 6057.9 |
| junctions | 0 | 263 | 263 |
| four_way_junctions | 0 | 0 | 0 |
| global_labels | 670 | 207 | -463 |
| global_labels_on_pin_stubs | 667 | 7 | -660 |
| name_tags | 3 | 200 | 197 |
| hierarchical_labels | 0 | 162 | 162 |
| local_labels | 0 | 0 | 0 |
| sheet_pins | 0 | 143 | 143 |
| no_connects | 88 | 88 | 0 |
| crossings | 0 | 5 | 5 |
| text_overlaps | 0 | 3 | 3 |
| off_grid_points | 0 | 0 | 0 |
| isolated_symbols | 0 | 0 | 0 |
| dangling_wire_ends | 0 | 0 | 0 |
| connected_pins | 667 | 675 | 8 |
| wired_pins | 0 | 513 | 513 |
| labelled_pins | 667 | 162 | -505 |
| wired_pin_share | 0.000 | 0.760 | 0.760 |
| single_global_labels | 0 | 18 | 18 |

## Per page

| page | V2 sheets / paper / fill | V2.2 paper / fill | wires V2 -> V2.2 | stub labels | hier labels | junctions | power symbols | crossings | text overlaps | isolated | wired pin share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01_aux_12v | 1 / A3 / 0.345 | A3 / 0.345 | 42 -> 82 | 42 -> 2 | 0 -> 4 | 0 -> 15 | 3 -> 16 | 0 -> 0 | 0 -> 2 | 0 -> 0 | 0.000 -> 0.786 |
| 02_supplies | 1 / A3 / 0.825 | A2 / 0.671 | 93 -> 159 | 93 -> 2 | 0 -> 3 | 0 -> 35 | 0 -> 42 | 0 -> 0 | 0 -> 1 | 0 -> 0 | 0.000 -> 0.926 |
| 03_dsp | 1 / A3 / 0.276 | A3 / 0.305 | 115 -> 171 | 115 -> 0 | 0 -> 52 | 0 -> 54 | 0 -> 9 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.548 |
| 04_dsp_decoupling | 1 / A3 / 0.538 | A3 / 0.329 | 66 -> 129 | 66 -> 0 | 0 -> 3 | 0 -> 56 | 0 -> 7 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.955 |
| 05_clock_debug | 1 / A3 / 0.407 | A3 / 0.662 | 49 -> 81 | 49 -> 0 | 0 -> 14 | 0 -> 12 | 0 -> 22 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.878 |
| 06_pwm_fault_logic | 2 / A3 / A3 / 0.77 / 0.264 | A2 / 0.773 | 162 -> 326 | 162 -> 3 | 0 -> 35 | 0 -> 47 | 0 -> 55 | 0 -> 5 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.744 |
| 07_adc_frontend | 1 / A3 / 0.49 | A3 / 0.517 | 56 -> 76 | 56 -> 0 | 0 -> 17 | 0 -> 14 | 0 -> 23 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.839 |
| 08_interconnect | 1 / A3 / 0.848 | A3 / 0.581 | 84 -> 156 | 84 -> 0 | 0 -> 34 | 0 -> 30 | 0 -> 16 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.607 |
| root | 1 / A3 / 0.371 | A2 / 0.628 | 0 -> 143 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0 -> 0 | - -> - |

## Planner counts (V2.2)

| sheet | paper | fill | label fallbacks | loop tags | tag pairs | layout variant |
|---|---|---:|---:|---:|---:|---|
| 01_aux_12v | A3 | 0.325 | 0 | 0 | 0 | auto |
| 02_supplies | A2 | 0.463 | 0 | 0 | 3 | below |
| 03_dsp | A3 | 0.415 | 0 | 0 | 0 | auto |
| 04_dsp_decoupling | A3 | 0.397 | 0 | 0 | 0 | auto |
| 05_clock_debug | A3 | 0.481 | 0 | 0 | 0 | auto |
| 06_pwm_fault_logic | A2 | 0.566 | 0 | 0 | 1 | beside |
| 07_adc_frontend | A3 | 0.596 | 0 | 0 | 2 | auto |
| 08_interconnect | A3 | 0.329 | 0 | 0 | 1 | auto |
| total | | | 0 | 0 | 7 | |

Name tags (single global labels naming local nets): 64; root sheet: {'paper': 'A2', 'sheet_pins': 143, 'global_anchors': 143}.

## single_global_label / four_way_junction dependency

Every local net keeps at least one global name tag: KiCad names the net after it, which the netlist gates against the live model and the frozen V2 netlist (bare V2 net names) rely on; a local net gets a second tag only where the planner repeats the name at a far-away pin or replaces a long / looping wire by a tag pair.  single_global_labels counts the global labels whose name occurs exactly once in the project: each one is a warning of KiCad's single_global_label ERC check, which is ignored by default and is not part of the ERC gate (0 findings with --severity-all).  four_way_junctions counts points where four wires meet (one junction dot, two nets would be unreadable there): the planner itself only draws T-joins, the sheet router may land a fourth leg on an existing junction of the same net, so a non-zero count is a reading-ambiguity figure, not a connectivity error.

## Definitions

One definition for every generator version: the V2 release sheets (releases/v2/kicad/<board>) and the V2.1
sheets are parsed with native_schematic.parse and measured alike, so before/after comparisons are honest.
