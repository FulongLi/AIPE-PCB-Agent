# Schematic readability - power board (V2 -> V2.2)

`V2`: D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\releases\v2\kicad\power_board  
`V2.2`: D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\kicad\power_board

## Totals (all sheets, root included)

| metric | V2 | V2.2 | delta |
|---|---:|---:|---:|
| sheets | 12 | 7 | -5 |
| continuation_sheets | 5 | 0 | -5 |
| papers | A3 | A2 / A3 | - |
| symbols | 237 | 237 | 0 |
| power_symbols | 15 | 230 | 215 |
| wires | 648 | 1232 | 584 |
| wire_length_mm | 1645.9 | 7716.5 | 6070.6 |
| junctions | 0 | 302 | 302 |
| four_way_junctions | 0 | 1 | 1 |
| global_labels | 663 | 126 | -537 |
| global_labels_on_pin_stubs | 648 | 7 | -641 |
| name_tags | 15 | 119 | 104 |
| hierarchical_labels | 0 | 71 | 71 |
| local_labels | 0 | 0 | 0 |
| sheet_pins | 0 | 64 | 64 |
| no_connects | 3 | 3 | 0 |
| crossings | 0 | 2 | 2 |
| text_overlaps | 0 | 3 | 3 |
| off_grid_points | 0 | 0 | 0 |
| isolated_symbols | 0 | 0 | 0 |
| dangling_wire_ends | 0 | 0 | 0 |
| connected_pins | 648 | 648 | 0 |
| wired_pins | 0 | 581 | 581 |
| labelled_pins | 648 | 67 | -581 |
| wired_pin_share | 0.000 | 0.897 | 0.897 |
| single_global_labels | 0 | 40 | 40 |

## Per page

| page | V2 sheets / paper / fill | V2.2 paper / fill | wires V2 -> V2.2 | stub labels | hier labels | junctions | power symbols | crossings | text overlaps | isolated | wired pin share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01_power_stage | 2 / A3 / A3 / 0.804 / 0.136 | A2 / 0.557 | 104 -> 181 | 104 -> 0 | 0 -> 11 | 0 -> 44 | 0 -> 40 | 0 -> 1 | 0 -> 1 | 0 -> 0 | 0.000 -> 0.923 |
| 02_gate_driver_hs | 2 / A3 / A3 / 0.639 / 0.398 | A2 / 0.538 | 137 -> 250 | 137 -> 2 | 0 -> 9 | 0 -> 70 | 0 -> 49 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.934 |
| 03_gate_driver_ls | 2 / A3 / A3 / 0.639 / 0.398 | A2 / 0.535 | 137 -> 250 | 137 -> 2 | 0 -> 10 | 0 -> 70 | 0 -> 48 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.927 |
| 04_sensing_island | 2 / A3 / A3 / 0.783 / 0.032 | A2 / 0.406 | 120 -> 218 | 120 -> 0 | 0 -> 7 | 0 -> 63 | 0 -> 47 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.950 |
| 05_selv_strip | 2 / A3 / A3 / 0.707 / 0.578 | A2 / 0.526 | 139 -> 258 | 139 -> 3 | 0 -> 26 | 0 -> 55 | 15 -> 43 | 0 -> 1 | 0 -> 2 | 0 -> 0 | 0.000 -> 0.813 |
| 06_mechanical | 1 / A3 / 0.333 | A3 / 0.221 | 11 -> 11 | 11 -> 0 | 0 -> 8 | 0 -> 0 | 0 -> 3 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0.000 -> 0.273 |
| root | 1 / A3 / 0.508 | A3 / 0.366 | 0 -> 64 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 0 -> 0 | - -> - |

## Planner counts (V2.2)

| sheet | paper | fill | label fallbacks | loop tags | tag pairs | layout variant |
|---|---|---:|---:|---:|---:|---|
| 01_power_stage | A2 | 0.306 | 0 | 0 | 2 | auto |
| 02_gate_driver_hs | A2 | 0.483 | 0 | 0 | 1 | below |
| 03_gate_driver_ls | A2 | 0.483 | 0 | 0 | 1 | below |
| 04_sensing_island | A2 | 0.420 | 0 | 0 | 0 | below |
| 05_selv_strip | A2 | 0.353 | 1 | 0 | 4 | auto |
| 06_mechanical | A3 | 0.213 | 0 | 0 | 0 | auto |
| total | | | 1 | 0 | 8 | |

Name tags (single global labels naming local nets): 62; root sheet: {'paper': 'A3', 'sheet_pins': 64, 'global_anchors': 64}.

Label fallbacks (no wire path found, drawn as a tag pair):
- 05_selv_strip: VIN_AMP_N at [[48.26, 167.64], [77.47, 177.8]]

## single_global_label / four_way_junction dependency

Every local net keeps at least one global name tag: KiCad names the net after it, which the netlist gates against the live model and the frozen V2 netlist (bare V2 net names) rely on; a local net gets a second tag only where the planner repeats the name at a far-away pin or replaces a long / looping wire by a tag pair.  single_global_labels counts the global labels whose name occurs exactly once in the project: each one is a warning of KiCad's single_global_label ERC check, which is ignored by default and is not part of the ERC gate (0 findings with --severity-all).  four_way_junctions counts points where four wires meet (one junction dot, two nets would be unreadable there): the planner itself only draws T-joins, the sheet router may land a fourth leg on an existing junction of the same net, so a non-zero count is a reading-ambiguity figure, not a connectivity error.

## Definitions

One definition for every generator version: the V2 release sheets (releases/v2/kicad/<board>) and the V2.1
sheets are parsed with native_schematic.parse and measured alike, so before/after comparisons are honest.
