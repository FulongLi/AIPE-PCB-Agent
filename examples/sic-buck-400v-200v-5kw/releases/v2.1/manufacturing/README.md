# Manufacturing-file review bundle (V2.1, two boards)

**AI-GENERATED ENGINEERING PROTOTYPE V2.1 - HUMAN REVIEW REQUIRED**

Generated manufacturing formats for engineering / DFM review of the 400 V -> 200 V / 5 kW SiC synchronous buck (Option B: power board
plus stacked SELV control board, `../design/architecture.md`). No fabrication or assembly order is authorized or implied. V2.1 is a
drawing and routing generation of the V2 design: the schematics were redrawn with wires and the boards were re-routed with the upgraded
grid router (octilinear simplification, chamfers, tangent arcs); topology, components, placement, net classes, rule values, pours and via
groups are the V2 ones, and the netlists are identical to the frozen V2 (`../releases/v2`, read-only). Everything here was exported by
`automation.kicad_tools.export_outputs` from the board files as they stand on disk: power board 2026-10-12T18:06:33+08:00, control board
2026-10-12T19:46:53+08:00 (`CreationDate` of the gerber job files). Read the "State" column before using any file; every number below is
read from the named file.

| Board | KiCad project | Export directory | State |
| --- | --- | --- | --- |
| Power board `AIPE_SiC_Buck_Power`, 240 x 180 mm, 4 x 70 um, 2.0 mm (F.Cu / In1.Cu / In2.Cu / B.Cu) | `../kicad/power_board/` | `power_board/` | Board sha256 `ae4ca86c438f56b8cb23c3f93b8e415aea73a509a604c69a0f28f04ea5519b56` (V2: `b1bb5698194b9aea...`): 237 footprints, 3136 tracks (2991 straight segments + 145 arcs), 606 vias, 36 zones incl. rule areas (`../verification/routing_progress_power.json`; segment / arc split per `../verification/engineering_checks/routing_quality_power_compare.md`). Native `kicad-cli` 10.0.7 DRC with `--schematic-parity --severity-all --refill-zones` (`../verification/drc/20261012T100423Z-drc-8b9e64d1/run.json`, source hash = board hash): **0 violations, 0 unconnected, 0 parity**. Stored fills checked without refill: 0 violations / 0 unconnected (`../verification/engineering_checks/stored_zone_fill_check_power.json`, 2026-10-12T10:04Z, diagnostic), so gerbers / PDF / renders / STEP show the DRC-checked copper. 11/11 export commands exit 0, 35 hashed artifacts, 70 input hashes (`power_board/export-manifest.json`). CAD-complete; engineering-review items below. |
| Control board `AIPE_SiC_Buck_Control`, 120 x 80 mm, 4 x 35 um, 1.6 mm (F.Cu signals / In1.Cu GND_CTRL / In2.Cu rail islands / B.Cu signals + mezzanine header) | `../kicad/control_board/` | `control_board/` | Board sha256 `52ca6c234357948a1119db0082ffd5ddcb706a852d9778787f74450ea1183428` (V2: `dead06ed18d85154...`): 207 footprints (`../verification/netlist_check_control.json`), 4523 tracks (4262 + 261 arcs), 798 vias, 20 zones (`../verification/routing_progress_control.json`; `..._control_compare.md`). Native DRC, same options (`../verification/drc/20261012T114513Z-drc-3461f467/run.json`): **0 / 0 / 0**; stored fills without refill: 0 / 0 (`stored_zone_fill_check_control.json`, 2026-10-12T11:45Z). 11/11 export commands exit 0, 35 hashed artifacts, 42 input hashes (`control_board/export-manifest.json`). CAD-complete; human review items below. |

## What changed in V2.1 (both boards)

- Routing geometry only. The 4-direction search algorithm is the V2 one: on the power board its result is identical to V2 (eps 0.01, build C of
  `../verification/routing_iterations_power.md` 16.3); on the control board the halo tolerance eps 0.02 alters a few search paths
  (known_issues.md V2.1-18; one via moved 0.125 mm, see `control_board/` below). A final `beautify` stage straightens the routed chains (octilinear
  string pulling, short-run collapse, on-grid 45-degree chamfers) and replaces corners by tangent `PCB_ARC` fillets where the occupancy
  allows (power 145 arcs, radius 0.30-0.70 mm; control 261 arcs, 0.20-0.80 mm; 0 discontinuous arc joints on either board,
  `../verification/engineering_checks/routing_quality_{power,control}.md`). Per net against V2: 0 longer, 0 with more vias, 0 narrower on
  both boards (`routing_quality_{power,control}_compare.md`); 90-degree bends 3609 -> 1121 (power) and 4069 -> 1233 (control), routed length
  5744.6 -> 5545.6 mm and 7055.2 -> 6700.7 mm, vias 606 and 798 unchanged.
- Arcs in the gerbers. KiCad plots `PCB_ARC` tracks natively as Gerber multi-quadrant arcs (`G75` with `G02` / `G03`): power F.Cu 49, In2.Cu
  30, B.Cu 66 (the 145 arcs; In1.Cu is a plane layer with none); control F.Cu 111, In2.Cu 12, B.Cu 138 (261). The F.Fab and F.Silkscreen
  files carry 8 / 24 (power) and 12 / 34 (control) arc commands from footprint graphics, as in V2. Counted in the gerber files in this
  session. The V2 bundle had no track arcs; confirm with the fabricator that the CAM import accepts arc primitives (or asks for
  polygonised arcs) - known_issues.md V2-17.
- DNP attribute. The 16 power and 1 control DNP parts of the model carry the footprint DNP attribute (`(attr smd dnp)` /
  `(attr through_hole dnp)` in the board files) so that `--schematic-parity` matches the schematics' `(dnp yes)`. See the BOM and
  position notes below (known_issues.md V2.1-11).
- Label. Title blocks rev `V2.1`, silkscreen `POWER BOARD V2.1` / `CONTROL V2.1`, and the banner "AI-GENERATED ENGINEERING PROTOTYPE - V2.1 -
  HUMAN REVIEW REQUIRED" in every regenerated record and PDF (`../verification/v21_validation.md` item L). The title fields still read
  "AIPE V2 SiC buck ... board" by design: V2 is the design generation, V2.1 the drawing generation (known_issues.md V2.1-09).
- Not changed: placement (footprint layer, position and rotation identical to V2 for all 237 / 207 footprints, `../releases/v2/kicad/` against
  `../kicad/` compared in this session; `v21_validation.md` items 5 and 6), the HV spacing rows except
  KR-ISO-002 HV-to-SELV on B.Cu 12.025 -> 11.932 mm (threshold 9.0 mm, within; `layout_metrics_power.md`), the slots under the barrier
  packages, the drill tables, the six V2 layout-metric exceptions and every open engineering item of V2 (`../verification/known_issues.md`).

The V2 bundle, its round-r20 history (LR-20..LR-35) and the superseded r19 bundle note are preserved in `../releases/v2/manufacturing/README.md`.

## `power_board/`

- `gerber`: 13 files - F.Cu, In1.Cu, In2.Cu, B.Cu (70 um each), F/B mask, F/B paste, F/B silkscreen, Edge.Cuts, F.Fab (assembly reference) and
  the `.gbrjob` with the layer stack (Revision `V2.1`, 240.05 x 180.05 mm, 4 layers, 2.0 mm, finish ENIG as recorded in the job file); use
  the job file for the stack order. Track arcs are native Gerber arcs (above).
- `drill`: Excellon (PTH and NPTH merged) plus the native report (`drill-report.rpt`, 2026-10-12T18:06:34): plated 412 x 0.3 mm,
  13 x 0.4 mm, 181 x 0.6 mm, 4 x 0.8 mm, 59 x 1.0 mm, 4 x 1.3 mm, 8 x 1.5 mm, 16 x 1.6 mm, 54 x 1.85 mm, 2 x 3.2 mm, 1 x 4.3 mm (754 plated
  holes); non-plated 8 x 1.2 mm with 8 slots (the isolation slots under the barrier packages U1-U7, U10), 8 x 3.2 mm, 10 x 4.3 mm (26
  unplated). Identical to the V2 table (the two `drill-report.rpt` files differ only in their creation line): no via was added or removed, and all 606 via
  positions equal V2 (board files compared in this session).
- `bom/bom.csv`: KiCad's native grouped schematic export, 213 grouped rows (`Refs,Value,Footprint,Qty,DNP`); 16 rows are marked in the DNP
  column (C15, C16, C17, C18, C19, C21, C41, D4, D6, R11, R12, R13, R14, R23, R41, RV1) with KiCad's localised UI string "不作装配 (DNP)"
  (UTF-8) rather than a plain token - read the column by emptiness, not by text. Purchasing BOM: `../components/bom_power.csv` (237 rows,
  `dnp` column, 16 marked).
- `pick_and_place/positions.csv`: 212 placements in mm, both sides, including the 16 DNP parts (the export does not exclude DNP footprints).
  Filter by the BOM before assembly; verify origin and rotation conventions with the assembler.
- `step/board.step` (27,350,179 bytes, tracks and zones included); not a validated assembly. `logs/step.log` reports the WE-SL2 model of
  L2 / L3 / L4 as not found (LR-35, known_issues.md V2-48).
- `review`: `schematic.pdf` (7 sheets, wired style); `pcb_layout.pdf` (6 pages - F.Cu, In1.Cu, In2.Cu, B.Cu, F.SilkS, F.Fab, each with
  Edge.Cuts; A3 at scale 1.0 per `../verification/routing_iterations_power.md` 16.5); `pcb_front.png`, `pcb_back.png`, `pcb_3d.png`
  (1176 x 872 px, `v21_validation.md` item 9). Copies: `../review/pcb_{front,back,3d}_power.png`, `../review/pcb_layout_power.pdf`,
  `../review/schematic_power.pdf`.
- `netlist.xml` versus `../design/circuit_power.json` and the board: `../verification/netlist_check_power.json`, exact match (648 named pads,
  101 nets, 237 components; status passed, 2026-10-12T10:07Z). The same netlist is exact against the frozen V2 netlist
  (`../verification/schematic_gates/power/schematic_gates.json`, `netlist_vs_v2`).
- `logs`, `export-manifest.json`: CLI outcomes of the 11 commands (schematic_pdf, pcb_pdf, gerber, drill, bom, placement, step, front, back,
  isometric, netlist - all exit 0), 70 input-source hashes, 35 output hashes.

## `control_board/`

- Same export set (`gerber` with the four 35 um copper layers and the `.gbrjob`, `drill`, `bom`, `pick_and_place`, `step`, `review`,
  `netlist.xml`, `logs`, `export-manifest.json`); copies in `../review/pcb_{front,back,3d}_control.png`, `../review/pcb_layout_control.pdf`
  (6 pages) and `../review/schematic_control.pdf` (9 sheets).
- `drill` (`drill-report.rpt`, 2026-10-12T19:46:54): plated 798 x 0.3 mm (the vias), 2 x 0.8 mm, 76 x 1.0 mm, 2 x 1.3 mm (878 plated
  holes); non-plated 4 x 3.2 mm. Table unchanged from V2 (no via added or removed); one 0.3 mm via moved by 0.125 mm against V2,
  (84.375, 27.125) -> (84.5, 27.125) mm (board files compared in this session; known_issues.md V2.1-18 / V2.1-02).
- `bom/bom.csv`: 187 grouped rows, 1 marked DNP (C54, same localised string); purchasing BOM `../components/bom_control.csv` (207 rows,
  `dnp` 1; standoffs and the power-board socket are not in it).
- `pick_and_place/positions.csv`: 187 placements, both sides (mezzanine header J8 and the 1V9 per-pin capacitors on the bottom), C54
  included although DNP.
- `step/board.step` (43,558,858 bytes); not a validated assembly. `logs/step.log`: models not found for the HTSSOP-28-1EP (U3),
  TSSOP-16-1EP (U1) and SG8002CA oscillator (Y1) footprints (LR-35).
- `netlist.xml` versus `../design/circuit_control.json` and the board: `../verification/netlist_check_control.json`, exact match (667 named
  pads, 111 nets, 207 components; status passed, 2026-10-12T11:47Z); exact against the frozen V2 netlist
  (`../verification/schematic_gates/control/schematic_gates.json`).
- `export-manifest.json`: 11 commands exit 0, 42 input-source hashes, 35 output hashes.

## Review images (`../review/`)

Before / after crops with identical framing, 2400-2401 px long side (2401 px for 28 files, 2400 px for the sensing_island and signal_corridor
crops; PNG headers read in this session), single-layer kicad-cli PDF plots rasterised:
`../review/crops/power/<area>_{v2,v21}_{top,bottom}.png` for `hs_island`, `ls_island`, `sensing_island`, `selv_socket`, `selv_mid` and
`../review/crops/control/<area>_{v2,v21}_{top,bottom}.png` for `dsp_fanout`, `signal_corridor`, `protection_logic`, `j8_header` (36 files;
the 18 `*_v2_*` crops are byte-identical to the crops committed in 070e934, `v21_validation.md` item 9). The V2 renders and PDFs are under
`../releases/v2/review/`. The comparison text is `../review/v2_v21_comparison.md`.

## Layout metrics (`../verification/engineering_checks/`)

Measured on the V2.1 board files with `automation/verification/check_sic_layout.py` (board hashes recorded; straight-line and
copper-to-copper proxies on the stored rule-aware fills - not loop inductance, creepage per standard or EMI). No row is worse than V2
(`../verification/v21_validation.md` item 5).

- Power, 58 rows: 27 within, **6 exceeding**, 25 measured without threshold - the same exceptions as V2: PE-PCB-002 Q2 source pad to the
  nearest PGND HF-capacitor pad 41.165 mm (C1.2; the HF rows sit west of Q1, LR-22 open); PE-PCB-006 VIN_RAW / VOUT_L without vias
  (THT-joined pours, checker limitation LR-30); KR-ISO-002 VIN-PGND and VOUT-PGND 1.950 mm on F.Cu inside the R6 / R10 pin fields
  (per-footprint rules, LR-31 accepted deviation); KR-TH-002 B.Cu copper of the PE-reference link column inside the heatsink courtyard
  (0.000 mm, LR-29 note) and the HF row-A PGND pads 4.955 mm from the courtyard on F.Cu. Routed-track values that changed with the V2.1
  geometry: LS gate network 82.130 mm (V2 84.440), HS 39.720 (39.940); AMC1311 pairs VIN 78.571 / 78.643 mm (mismatch 0.073; V2 1.508),
  VOUT 63.785 / 61.148 mm (2.637; V2 1.758 - larger although both nets are shorter); ISENSE / ISENSE_REF 81.044 / 86.293 mm (V2 83.796 /
  90.100); HV-to-SELV B.Cu 11.932 mm (V2 12.025) (`layout_metrics_power.md`).
- Control, 31 rows: 2 within, **2 exceeding**, 17 measured without threshold, 10 not measured (power-stage rules without a control-board
  input). PE-PCB-008: DSP bypass pairs up to 5.381 mm against the 5.0 mm review proxy (unchanged). ISENSE / ISENSE_REF from J8 114.538 /
  51.569 mm (V2 122.175 / 54.550) (`layout_metrics_control.md`).
- Open review items on the control board (not changed by V2.1 - string pulling shortened the meanders and kept their topology and vias):
  LR-32 protection-line lengths (DSP_TRIP_N 207.1 mm / 21 vias, FAULT_N 303.0 / 16, OC_N 193.5 / 10, ESTOP_N 384.6 / 24 against V2 224.4 /
  21, 319.7 / 16, 204.1 / 10, 402.5 / 24; `routing_quality_control.json` and `_v2.json`), LR-33 ADC filter distances 6.9-14.8 mm, LR-27
  mezzanine overhang (mechanical), LR-34 / LR-35 DFM and 3D-model notes.
- Open review items on the power board (not changed by V2.1): LR-22 one-sided HF tier, LR-24 LS gate loop (7 vias on G_L, R41 / TP2 over
  the SW In2 pour), LR-26 layer-split AMC1311 pairs, LR-25 / LR-29 corridor and courtyard distances. Before-fabrication rows V2-01..V2-17
  of `../verification/known_issues.md` all remain open; the V2.1 rows V2.1-01..V2.1-18 add the drawing and routing items (remaining
  90-degree corners by reason, the opt-in 8-direction search, DNP in BOM and positions, native Gerber arcs, checker limits).

## Verification state

`PYTHONIOENCODING=utf-8 python -m automation.scripts.verify_sic_buck` -> `../verification/verification-summary.json`: status passed,
problems none; it names the manifests above (ERC `20261012T094955Z-erc-c574a866` / `20261012T095007Z-erc-caa10a79`, DRC
`20261012T100423Z-drc-8b9e64d1` / `20261012T114513Z-drc-3461f467`) and records `step_models_complete: false` for both boards. A
second AI agent's re-derivation of every TASK 7 check is `../verification/v21_validation.md`; it is not a human review. This bundle will be copied unchanged into the
V2.1 release snapshot by `python -m automation.scripts.freeze_release --version v2.1` (`../releases/v2.1/`, `v2.1-review-package.zip`),
to be run after the V2.1 documents are finalised; `../releases/v2/` stays frozen.
