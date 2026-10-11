# Manufacturing-file review bundle (V2, two boards)

**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

Generated manufacturing formats for engineering/DFM review of the 400 V -> 200 V / 5 kW SiC synchronous buck (Option B: power board
plus stacked SELV control board, `../design/architecture.md`). No fabrication or assembly order is authorized or implied. Everything
here was exported on 2026-10-11 05:47 UTC from the board files as they stand on disk (correction round r20, second independent review LR-20..LR-35 applied
as recorded in `../verification/optimisation_before_after.md`). Read the "State of each board" row before using any file.

| Board | KiCad project | Export directory | State |
| --- | --- | --- | --- |
| Power board `AIPE_SiC_Buck_Power`, 240 x 180 mm, 4 x 70 um, 2.0 mm (F.Cu / In1.Cu / In2.Cu / B.Cu) | `../kicad/power_board/` | `power_board/` | Board sha256 `b1bb5698194b9aea...`: 237 footprints, 4755 tracks, 606 vias, 36 zones (incl. rule areas). Native `kicad-cli` DRC with `--schematic-parity --severity-all --refill-zones` (`../verification/drc/20261011T054445Z-drc-d0914d79/run.json`): **0 violations, 0 unconnected, 0 parity**. The zone fills STORED in the board file are the rule-aware copper: a DRC of the stored fills without refill reports 0 violations / 0 unconnected (`../verification/engineering_checks/stored_zone_fill_check_power.json`, diagnostic), so gerbers / PDF / renders / STEP show the DRC-checked copper. 11/11 export commands exit 0, 35 hashed artifacts. CAD-complete; engineering-review items below. |
| Control board `AIPE_SiC_Buck_Control`, 120 x 80 mm, 4 x 35 um, 1.6 mm (F.Cu signals / In1.Cu GND_CTRL / In2.Cu rail islands / B.Cu signals + mezzanine header) | `../kicad/control_board/` | `control_board/` | Board sha256 `dead06ed18d85154...` (unchanged since the second review): 207 footprints, 5995 tracks, 798 vias, 20 zones. Native DRC (`../verification/drc/20261011T051246Z-drc-f801ed3c/run.json`): **0 / 0 / 0**; stored fills checked without refill: 0 / 0 (`stored_zone_fill_check_control.json`). 11/11 export commands exit 0, 35 hashed artifacts. CAD-complete; human review items listed below. |

## What changed in round r20 (power board)

- LR-20: the generator refills every zone in a fresh KiCad Python process after routing (project `.kicad_dru` applied) and stores that copper; the
  r19 bundle plotted 0.3 mm fills (499 findings without refill) and is superseded (moved out of the repository).
- LR-21: all-layer pour / via keep-outs (>= 5 mm) around the four PE-bonded heatsink mounting holes (`HS1_HOLE_1..4` rule areas).
- LR-23: input return terminal J2 (PGND) moved to the open east position of the upper input row (23.0, 112.0); the relay input J5 (VIN_RAW) takes the
  corner pocket under J1 (same net); the B.Cu PGND column continues under the HF tier; the PTC pad RT1.1 is fed by a 2 mm B.Cu VIN_RAW track.
- LR-28: SW In2 block / neck widened (block top y 95, neck top y 85), 32 PGND stitching vias in the J4 output block.
- LR-25: MOV RV1 moved out of the fan-intake corridor to (165.0, 88.5); sink, J3 / J4 and the output films shifted east so the input films keep
  >= 20 mm courtyard distance (L1 is now 18.3 mm courtyard / about 18.9 mm body from the sink - the 240 mm width cannot give both sides 20 mm).
- LR-24 / LR-26 were attempted in build r20c (LS gate-loop nets restricted to B.Cu; each AMC1311 differential pair restricted to F.Cu) and
  **not applied**: the build left 9 connections open (DRC 8 / 10 / 0, `../verification/drc/20261011T053341Z-drc-ba043c49/`) and was reverted
  in the delivered r20d; the LS gate loop (G_L 7 vias, R41 / TP2 over the SW In2 pour) and the layer-split AMC1311 pairs remain open review
  items. Measured values before / after: `../verification/optimisation_before_after.md` (Pass 2).

## `power_board/`

- `gerber`: 13 files - F.Cu, In1.Cu, In2.Cu, B.Cu (70 um each), F/B mask, F/B paste, F/B silkscreen, Edge.Cuts, F.Fab (assembly reference) and the
  `.gbrjob` with the layer stack; use the job file for the stack order.
- `drill`: Excellon (PTH and NPTH merged) plus the native report: plated 412 x 0.3 mm, 13 x 0.4 mm, 181 x 0.6 mm, 4 x 0.8 mm, 59 x 1 mm, 4 x 1.3 mm, 8 x 1.5 mm, 16 x 1.6 mm, 54 x 1.85 mm, 2 x 3.2 mm, 1 x 4.3 mm; non-plated 8 x 3.2 mm, 10 x 4.3 mm; slots 8 x 1.2 mm (the 1.2 mm isolation slots under the barrier packages U1-U7, U10).
- `bom/bom.csv`: KiCad's native grouped schematic export (213 grouped rows; `Refs,Value,Footprint,Qty,DNP`); purchasing BOM `../components/bom_power.csv`.
- `pick_and_place/positions.csv`: 212 placements in mm, both sides. Verify origin and rotation conventions with the assembler.
- `step/board.step` (31.0 MB, tracks and zones included); not a validated assembly.
- `review`: `schematic.pdf`; `pcb_layout.pdf` (A3, scale 1.0, six pages - F.Cu, In1.Cu, In2.Cu, B.Cu, F.SilkS, F.Fab - each with Edge.Cuts);
  `pcb_front.png`, `pcb_back.png`, `pcb_3d.png`. Copies: `../review/pcb_{front,back,3d}_power.png`, `../review/pcb_layout_power.pdf`.
- `netlist.xml` versus `../design/circuit_power.json` and the board: `../verification/netlist_check_power.json`, exact match (648 named pads; status passed).
- `logs`, `export-manifest.json`: CLI outcomes, 75 input-source hashes, 35 output hashes.

## `control_board/`

- Same export set (`gerber` with the four 35 um copper layers, `drill`, `bom`, `pick_and_place`, `step`, `review`, `netlist.xml`, `logs`,
  `export-manifest.json`); `review/pcb_layout.pdf` is A3 at scale 2.0; copies in `../review/pcb_{front,back,3d}_control.png` and
  `../review/pcb_layout_control.pdf`.
- `drill`: plated 798 x 0.3 mm, 2 x 0.8 mm, 76 x 1 mm, 2 x 1.3 mm; non-plated 4 x 3.2 mm.
- `bom/bom.csv`: 187 grouped rows; purchasing BOM `../components/bom_control.csv` (standoffs and the power-board socket are not in it).
- `pick_and_place/positions.csv`: 187 placements, both sides (mezzanine header J8 and the 1V9 per-pin capacitors on the bottom).
- `step/board.step` (50.7 MB); not a validated assembly.
- `netlist.xml` versus `../design/circuit_control.json` and the board: `../verification/netlist_check_control.json`, exact match (667 named pads; status passed).

## Layout metrics (`../verification/engineering_checks/`)

Measured on the delivered board files with `automation/verification/check_sic_layout.py` (board hashes recorded; straight-line and
copper-to-copper proxies on the stored fills - which are now the rule-aware fills - not loop inductance, creepage per standard or EMI).

- Power, 58 rows: 27 within, **6 exceeding**, 25 measured without threshold. Remaining
  exceedances: PE-PCB-002 Q2 source pad to the nearest PGND HF-capacitor pad (41.2 mm, C1.2 - the HF rows sit west of Q1, LR-22 open); PE-PCB-006
  VIN_RAW / VOUT_L without vias (THT-joined pours, checker limitation LR-30); KR-ISO-002 VIN-PGND and VOUT-PGND 1.95 mm on F.Cu inside the R6 / R10
  pin fields (per-footprint rules 1.79 mm, LR-31 accepted deviation); KR-TH-002 B.Cu copper of the PE-reference link column inside the heatsink
  courtyard (LR-29 note) and the HF row-A PGND pads 4.955 mm from the courtyard on F.Cu.
- Control, 31 rows: 2 within, **2 exceeding**, 17 measured without threshold, 10 not measured (power-stage rules without a control-board input). PE-PCB-008: DSP bypass pairs up to 5.38 mm against the 5.0 mm review proxy.
- Open review items on the control board (not changed in r20): LR-32 protection-line lengths (an attempt with pinned routing of DSP_TRIP_N /
  FAULT_N / OC_N left one connection open and was reverted, `../verification/routing_iterations_control.md`), LR-33 ADC filter distances
  6.9-14.8 mm, LR-27 mezzanine overhang (mechanical), LR-34 / LR-35 DFM and 3D-model notes.

## Verification state

`PYTHONIOENCODING=utf-8 python -m automation.scripts.verify_sic_buck` -> see `../verification/verification-summary.json` (written after this export).
