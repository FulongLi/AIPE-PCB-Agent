# Automation architecture

The repository is the engineering record. Each design input, generated CAD
source and verification output must remain traceable to a commit.

```text
Requirements + documented assumptions
    -> engineering calculations and component evidence
    -> deterministic design description
    -> KiCad schematic and PCB source
    -> real KiCad checks and exports
    -> engineering review and frozen V1 package
```

Python is the cross-platform orchestration language. Prefer `kicad-cli` for
checking and exporting; investigate official IPC/Python interfaces for editing.
Where an operation is unavailable, use the documented KiCad file formats and
validate the generated files with KiCad. No third-party MCP server is required.

The initial setup code uses only the Python standard library. Avoid relying on
shell activation, Unix-only locations, or modifying global Python packages.
Discover tool paths using explicit configuration, environment overrides, PATH,
and conventional platform locations. Record which path was actually used.

The CLI check wrapper must preserve nonzero exit codes, capture logs and reject
missing output reports. A unit test using a simulated process result is only a
test of this wrapper; it is not an ERC/DRC result or a CAD integration test.

The complete operation layer will grow with verified needs: project creation,
schematic connectivity and footprint assignment, board stack-up, placement,
tracks/vias/zones, checks, exports and review images. These are planned
capabilities, not a claim of current implementation.

## Engineering knowledge layer

Design decisions can draw on the reference-derived knowledge base in
`knowledge/` (skills, circuit blocks, component knowledge and rules with
evidence and validation status). It is produced and checked by
`automation/knowledge/` and queried through `automation.knowledge.query`. See
[knowledge-system.md](knowledge-system.md). It informs design and review; it
does not replace the KiCad checks above or human engineering review.

## V2.1 modules: presentation layer and routing geometry

**AI-GENERATED ENGINEERING PROTOTYPE V2.1 - HUMAN REVIEW REQUIRED**

V2.1 (branch `feat/sic-buck-v2.1-quality`) separates the electrical connectivity layer from the
presentation layer. The connectivity layer is unchanged: a part list in the shared model format
(`ref`, `value`, `footprint`, `nets` as `pad -> net`, `pins`, `page`, `kind`), built by a model
module on `sic_buck_common.Circuit`. The presentation layer decides how a project is drawn
(placement, orientation, visible wiring, functional groups, labels and ports, sheets) and how the
router shapes its copper (direction set, simplification, chamfers, arcs). Both layers are data-driven
and reusable; the SiC buck supplies only its model, its group annotations and two policy dicts.

```text
Circuit model (pads -> nets, pins, pages, Circuit.block() groups)
    -> project_schematic.generate_project(spec)        presentation None = V2 drawing style (code path unchanged)
         -> schematic_presentation.Planner             roles, groups, lanes, sheets, root
         -> schematic_wiring                           sheet router, KiCad normalisation, connectivity guard
         -> native_schematic.Schematic                 deterministic .kicad_sch emitter
    -> generate_sic_schematics --gates --readability   six gates, schematic_metrics V2 vs V2.1
Board plan dict (+ key 'style')
    -> grid_router.run_plan                            4- or 8-direction A*, trials, rip-up, pruning
         -> Router.beautify                            final geometry pass (path_geometry), then pours
    -> check_routing_quality                           measure / compare, DRC manifest linkage
    -> freeze_release --version <v>                    verified, non-overwritable snapshot
```

| Module | Contract |
|---|---|
| `automation/kicad_tools/grid_router.py` | Plan key `style` (`STYLE_DEFAULTS`, validated by `normalise_style`; a plan without it runs the unchanged V2 search: attempt C reproduced the frozen V2 quality totals, 4755 tracks, 606 vias, 5744.6 mm, 3609 bends_90, while file bytes differ through random KIIDs). `style.diagonal`: `Grid.astar(moves=8)` with an octile heuristic, no corner cutting (both orthogonal neighbours of a diagonal step must be free) and parent-direction bend penalties `[b45, b90]` in cells; pad-escape fanout and the rip-up victim search stay 4-direction. `style.simplify = 'octilinear'`, `style.chamfer`, `style.arcs`: `Router.beautify`, the final stage of `run_plan` after `prune_unused_vias` and before the ground pours. Per chain of router-made items (stage tags by KIID) between pads, vias, junctions and copper of other stages: octilinear string pulling, short-run collapse and on-grid 45-degree chamfers validated by the exact grid rule of the search (`Grid.cells_free`), then tangent `PCB_ARC` fillets with adaptive radius (`arc_radius_mm`, `arc_steps`) validated by a corridor test on the foreign mask dilated by `arc_dilate_cells` (`Router.check_arc`, `Grid.samples_free`). A chain is rewritten whole or kept whole; the reasons (`pad_exit`, `clearance`, `leg_too_short`) go into the report. `Router.smooth_policy(net)` -> `none`, `diagonal` or `arc` from `net_rules[net].smooth`, `style.straight_nets`, power / critical status and `max_width_for_arcs_mm`. Report fields `style`, `arcs`, `beautify`. |
| `automation/kicad_tools/path_geometry.py` | Pure Python (no numpy, no pcbnew): `MOVES8` (index = octant), `turn_class`, `octile`; `shortcut`, `collapse_short_runs`, `chamfer`, `merge_collinear`; `fillet_corner`, `arc_from_points`, `arc_length`, `sample_arc`, `tangent_at`; `chains_from_items` (maximal degree-2 chains between anchors), `connected_by_overlap`, `diagonals_clear_of`, `short_runs`, `classify_bend`. Every function is deterministic in its inputs; router and checker share one definition of a corner. |
| `automation/verification/check_routing_quality.py` | `extract_board` (pcbnew) -> `measure` (plain dicts, host-testable) -> `routing_quality_<label>.json` + Markdown; per board, layer, net and attribution (router, pre-routed, pad link); bends 90 / 45 / other, direction changes, stair and zigzag runs, short segments, efficiency, arc continuity; `compare` (before / after with per-net regressions), `link_drc` (same board bytes as the manifest?), `--plan`, `--report`, `--baseline`; re-executes under KiCad Python. |
| `automation/kicad_tools/native_schematic.py` | Deterministic `.kicad_sch` emitter (uuid5 of path-like names): `add_symbol` with angle, mirror, DNP and property placement, `placed_pins` / `transform` / `rotate_direction`, `wire`, `junction`, `label`, `global_label`, `hierarchical_label`, `power_symbol_definition`, `rectangle`, `no_connect`, `text`. |
| `automation/kicad_tools/project_schematic.py` | `ProjectSpec.presentation`: `None` or `'legacy'` keeps the V2 drawing path unchanged (the output differs from the V2 release only by the generation label; no byte comparison recorded); a dict or `'wired'` runs `_generate_wired`: `schematic_presentation.Planner` -> connectivity guard (`schematic_wiring.connectivity` and `compare_with_model`; on a mismatch nothing is written and `design/connectivity_guard_failure.json` is dumped) -> one sheet per page, root sheet, project files; `remove_stale_sheets` deletes continuation sheets of a previous generation; `design/<mapping_name>` (default `schematic_mapping.json`; the SiC generator passes `schematic_mapping_<board>.json`) records placement and planner counts. |
| `automation/kicad_tools/schematic_wiring.py` | `WireGrid` on the 1.27 mm sheet grid (symbol bodies, texts, pins, wires and labels per net); `route` (straight / L candidates, then Dijkstra with bend and crossing penalties, 4-neighbour, never through a point of another net); `normalise` (KiCad connection rules: T-splits, junctions, collinear merges, labels on a foreign wire recorded as `label_on_other_net`); `trim_dangling`; `crossings`; `connectivity` (re-derives `(ref, pad) -> net` with the KiCad 10 coincidence rules measured natively) and `compare_with_model`. |
| `automation/kicad_tools/schematic_presentation.py` | `DEFAULT_PRESENTATION` / `coerce_presentation`: `groups`, `group_titles`, `group_order`, `supply` (`'auto'` = flag nets plus `power_out` nets, or a list), `exclude_supply`, `include_supply`, `down_pattern`, `paper_escalation`, text sizes, `max_row_mm`, `max_col_mm`, `max_wire_mm`, `max_cross_wire_mm`, `loop_slack_mm`, `min_fill`. `classify_nets` assigns roles: `rail` (power symbols), `cross` (hierarchical label per sheet, sheet pin and global anchor on the root), `local` (wires plus one global name tag), `nc`. Groups come from `Circuit.block()` metadata, `part['group']` or `auto_groups` (two-terminal parts attach to the anchor they share a signal net with). `GroupLayout`: every anchor pin (`ANCHOR_KINDS` IC / DSP / Q) owns a lane; shunts hang to rails, series parts continue the lane, decoupling rows, free chains, terminal grids. `Planner.plan_page` (extras placement `auto` / `below` / `beside`, smallest paper wins), `pack_sheet` (drawing-order columns, first-fit-decreasing, bottom-left packing, then paper escalation), `route_sheet` (sheet router; long or looping wires become name-tag pairs), `plan_root` (port wall with one global anchor per sheet pin). Exceptions (`no_wire_path`, loop tags, label pairs) are reported in the mapping file, never silent. |
| `automation/kicad_tools/schematic_metrics.py` | `measure_sheet` / `measure_project` / `compare_projects` / `comparison_markdown`: stub labels, name tags, wires, junctions, hierarchical labels, sheet pins, crossings, text overlaps (estimated font boxes), off-grid points, isolated symbols, dangling ends, wired pin share, four-way junctions, paper fill. One definition for the V2 release sheets and the V2.1 sheets; CLI with `--compare`. |
| `automation/kicad_tools/generate_sic_schematics.py` | `--style wired|legacy`, `--gates` (`verify_wired`: `.kicad_dru` identical to a legacy generation of the same model, `net_settings` equal, ERC 0 with the finding types listed, netlist vs model and vs the V2 release, `paper_fill`), `--readability` (`write_readability_report`); `PRESENTATION` policy per board and `presentation_for` (SiC-specific data, generic pattern). |
| `automation/kicad_tools/sic_buck_common.py` | `GENERATION` / `BANNER`: one label for every artefact the generators write. `Circuit.block(name, title)`: a context manager that records the functional block of every `add()` out of band (`circuit.groups`, `circuit.block_titles`), so `design/circuit_<board>.json` stays identical in content with or without annotations. |
| `automation/scripts/freeze_release.py` | `RELEASES` table (label, title, notes per version); runs `verify_sic_buck` first; never overwrites; writes `releases/<version>/` with `README.md`, `SHA256SUMS.json` (source commit) and the portable zip. |
| Also changed | `v2_pipeline_smoke.py` (`--v21-style`, `V21_STYLE`: the styled router end to end on a synthetic board), `check_sic_layout.py` (arcs densified to 0.05 mm chords for the copper metrics), the two board generators (`--style` / `--no-style`, `--outputs` scratch mode, footprint DNP attribute from the model, deterministic corridor order and zone KIIDs on the control board). |

### Reuse for other converters (Buck, Boost, DAB, LLC)

A new project supplies three things: a `Circuit` model with `block()` annotations (what belongs
together), a `ProjectSpec` whose `presentation` dict names the rail policy and group titles, and a
board plan dict whose `style` block names the geometry. Nothing in the table above refers to a
converter: net roles are derived from pin types and page membership, groups from the annotations or
the anchor rule, lanes from the anchor pins, papers from the content, and the router's smoothing
from net rules and widths. The same checkers and metrics measure any `.kicad_pcb` or `.kicad_sch`
directory, which is how the V2 and V2.1 generations were compared with one definition.

### Honest limits

- The presentation layer was tuned on two boards. Its lane model assumes anchors (ICs, FETs,
  connectors) with two-terminal satellites; a transformer or coupled inductor of a DAB / LLC is not an
  anchor kind yet and would be drawn as a free chain. There are no "bridge" items (a two-pin part
  between two anchor pins), diodes and FETs without a matching library symbol are drawn from generic
  outlines, and dense sheets escalate to A2 (hull fills 0.40-0.68 on seven V2.1 sheets) because lane
  compaction is not implemented. Every local net keeps one global name tag so KiCad keeps the model's
  net names; KiCad's default-ignored `single_global_label` check would warn once per tag.
- The sheet router is 4-direction and local to a sheet; where it finds no path the planner falls back
  to a name-tag pair and reports it (one case on the power board).
- The router's 8-direction search is opt-in: on both delivered boards it exceeded the V2 run time and
  left connections open, so the delivered geometry comes from the unchanged 4-direction search plus the
  final pass. The pass is conservative by design (rewritten chains do not release their old occupancy;
  pads are modelled by bounding boxes), so corners survive where a human would still fillet; arcs are
  limited to nets up to `max_width_for_arcs_mm` and to non-power, non-critical nets unless the plan
  says otherwise. A zero `unresolved` list is a geometric proposal; only `kicad-cli pcb drc` is evidence.
- The checker measures geometry only (no inductance, EMI or current capacity), classifies remaining
  90-degree bends by the router's exception records and leaves the rest as `unexplained`, and pools pad
  hits per net across layers.
- Regeneration reproduces copper and zones item for item, not file bytes (random KIIDs of tracks,
  vias and footprints); one order-dependent occupancy code remains in the control routing records.
- The gates prove netlist identity and rule-file identity against a legacy generation of the same
  model, not that the drawing is good; readability is measured by `schematic_metrics`, and the
  TI TIDA-010054 schematic was the reference style, not a template.
