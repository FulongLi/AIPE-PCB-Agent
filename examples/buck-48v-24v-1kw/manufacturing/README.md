# Manufacturing-file review bundle

**AI-GENERATED ENGINEERING PROTOTYPE - V1 - HUMAN REVIEW REQUIRED**

These are generated manufacturing formats for engineering/DFM review. No
fabrication or assembly order is authorized or implied.

- `gerber`: F.Cu, In1.Cu, In2.Cu, In3.Cu, In4.Cu and B.Cu are the six copper
  layers. Mask, paste, silkscreen and Edge.Cuts are separate outputs. F.Fab is
  an assembly/reference drawing, not an additional copper layer. Use the
  `.gbrjob` layer metadata rather than inferring stack order alphabetically.
- `drill`: Excellon PTH/NPTH files and the native drill report. Review the
  inductor's plated oval slots, bolt holes and exposed-pad via treatment.
- `bom/purchasing_bom.csv`: 220 electronic components with manufacturer/MPN.
  `bom/bom.csv` is KiCad's native schematic export. Mounting holes/test pads
  are bare PCB features; mechanical hardware is not a completed purchasing BOM.
- `pick_and_place`: Native coordinate export in mm. Separate SMT/THT/manual
  operations and verify origin/rotation with an assembler before using it.
- `step`: Populated board with tracks/zones and dimensioned custom envelopes.
  Heatsinks, cables, clamps, hardware and exact vendor mechanical details are
  not a validated assembly. STEP export was checked for missing-model messages.
- `review`: Source PDF and PNG exports, also copied to the example's review
  entry point. The F.Fab PDF page supplies component designators.
- `logs` and `export-manifest.json`: Actual CLI command outcomes, input-source
  hashes and output hashes. Additional purchasing/README files are covered by
  the frozen release manifest rather than the original export manifest.

Build requirements and constraints are in `../design/pcb_stackup.md`; unresolved
engineering issues are in `../verification/known_issues.md`. The six-layer,
heavy-copper/fine-pitch combination needs fabricator agreement before ordering.
