**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# Independent PCB layout review (task section 17) - V2 power and control boards

Reviewer: independent layout-review agent (did not create either board). Date 2026-10-11. This review
supersedes the 2026-10-10 review of the previous state (power board absent, control board with 39 open
connections); none of the earlier findings LR-01..LR-19 is carried forward unchanged - each was re-measured.

Scope: `kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` (sha256 `ae0f05d86ac6a104...`) and
`kicad/control_board/AIPE_SiC_Buck_Control.kicad_pcb` (sha256 `dead06ed18d85154...`) against
`design/design_decisions.json` (schema 4: architecture, standards_and_spacing, thermal, interconnect,
CR-21..CR-26), `design/pcb_stackup.md`, `docs/pcb-design-rules.md` (PE-PCB-001..008) and the knowledge
rules KR-PCB-001..006, KR-ISO-001..004, KR-CAP-003, KR-TH-002.

Method (every number below was produced by this review, not copied from the layout agents' claims):

- geometry read with pcbnew 10.0.7 through `automation.verification.check_sic_layout.extract_board` into
  JSON, then measured with shapely (pad polygons, track/via geometry, zone fills per layer, courtyards);
- **two fill states** of the power board were measured: the fills **stored** in the delivered file (what the
  gerbers, renders and the layout-metrics checker show) and a **rule-aware refill** produced in scratch with
  `kicad-cli pcb drc --refill-zones --save-board` on a copy (the copper the verification DRC actually judged;
  a no-refill DRC of that saved copy gives 0 findings, so it is a faithful image of the DRC'd copper);
- copper width along a current path = largest erosion radius that keeps the two terminals in one connected
  copper component ("neck width"), with 3 mm discs at the terminals so that the pad itself does not set the
  limit; IPC-2221 k = 0.048 / 0.024, exponents 0.44 / 0.725, 70 um, long-trace formula (conservative for a
  short isthmus, as the baseline uses it);
- all 6 review PNGs and the 12 layer-PDF pages were rasterised (pymupdf, 200-300 dpi) and inspected, with
  300 dpi crops of the half bridge / driver islands, the PE corner and the SELV strip on every copper layer,
  and of the DSP region and the two control-board planes;
- DRC evidence re-validated by recomputing every hash in the `run.json` records; stored-fill DRC and the
  rule-aware refill were re-run independently (scratch copies, nothing in the repository touched).

No board, generator, schematic, library, rule file, model or export was edited. Dispositions: **pass**,
**fail**, **unverified** (no artefact to measure), **human review** (engineering judgement or outside the
layout's reach). Machine-readable findings: `layout_review_findings.json` (same directory).

## 0 Headline

| Item | State |
|---|---|
| Power board | Routed, 0 open connections, netlist = schematic = board (648 pads). kicad-cli DRC with `--schematic-parity --severity-all --refill-zones` is 0/0/0 (`verification/drc/20261011T021012Z-drc-0ebee900`, hashes intact). **The board is not finished:** (1) the copper stored in the file and exported to `manufacturing/power_board/` violates the project's own rules in 499 places (re-run here: 324 inner / 154 outer HV functional, 16 HV-to-PE, 5 pin-field) because the generator filled the zones with the 0.3 mm zone clearance only; the zero holds only for copper KiCad refills in memory; (2) the heatsink's four M3 mounting holes have HV copper (In1 PGND, In2 VIN pours) 0.25 mm from the hole wall on both inner layers with PE-bonded hardware through them; (3) the input PGND return narrows to 3.8 mm of inner copper at (23.0, 137.9) for the full input current. Twelve further should-fix items (commutation-loop geometry, SW copper, LS gate loop, AMC1311 pair routing, mezzanine support, thermal corridor). |
| Control board | Routed, 0 open connections, DRC 0/0/0 with the same options (`...021018Z-drc-b9c91de5`), stored fills = DRC'd copper (0 findings without refill), netlist exact (667 pads). J8 on B.Cu, mates with power-board J7 to 0.00 mm, 2 of 4 standoff holes land on power-board holes. No blocker; should-fix items are routing quality (DSP_TRIP_N 224 mm / 21 vias, FAULT_N 320 mm, ISENSE 122 mm pair split) and the ADC filter capacitors 6.9-14.8 mm from the pins. |
| Evidence set | DRC/ERC/netlist/export manifests are hash-consistent (56 + 42 dependencies, report hashes recorded - the earlier LR-19 gap is closed). But for the power board the gerbers, renders and `layout_metrics_power.*` describe the stored fills, i.e. copper that fails the project rules, while the DRC describes the refilled copper: the power-board evidence set is internally inconsistent until the board is refilled and re-exported. |

## 1 Evidence validity

| Check | Evidence (this review) | Finding | Disposition |
|---|---|---|---|
| Power DRC record | `20261011T021012Z-drc-0ebee900/run.json`: command `pcb drc --format json --severity-all --exit-code-violations --schematic-parity --refill-zones`; `source_sha256` recomputed = `ae0f05d86ac6a104...` (board on disk); 56/56 `dependency_sha256` recomputed equal; `report_sha256` recomputed equal (`bbc9b463...`); `drc.json` 0 violations / 0 unconnected / 0 parity, kicad 10.0.7, `ignored_checks` = KiCad defaults only (missing_courtyard, track_not_centered_on_via, tuning ...). Same for the layout agent's `...015623Z-drc-280475df`. | Record intact. | pass (chain) |
| Control DRC record | `20261011T021018Z-drc-b9c91de5` and `...002742Z-drc-0d33d344`: source `dead06ed18d85154...` matches, 42/42 dependencies, report hash equal, 0/0/0. | Record intact. | pass |
| Stored fills vs DRC'd copper (power) | Scratch copy of `kicad/power_board/`, `kicad-cli pcb drc --severity-all` **without** `--refill-zones`: 499 clearance violations (+1 copied-path lib warning): HV functional inner 324, outer 154, HV side to PE 16, pin-field R4/R5/R6/R14 5; all at 0.30 mm. Scratch copy refilled with `--refill-zones --save-board` then checked without refill: 0. Refill changes the pours materially: F.Cu VIN 5690 -> 4508 mm2, In2 VIN 19890 -> 18915, In1 PGND 30560 -> 29181, B.Cu PGND 10559 -> 8873, VOUT_L F.Cu 506 -> 422. | **The delivered file and every export derived from it (gerbers F.Cu/In1/In2/B.Cu, PDFs, PNGs, STEP) carry copper that fails the project's `.kicad_dru`.** The DRC zero is true only of the in-memory refill. `export_outputs.py` plots without `--check-zones`. | **fail** (LR-20) |
| Stored fills (control) | Same no-refill DRC on a scratch copy: 0 violations (lib warning only). | Stored fills are the DRC'd copper. | pass |
| Layout metrics | `layout_metrics_power.md` (58 rows, generated 02:11 from the same hash) reports KR-ISO-002 distances of 0.300 mm (HV-PE, VIN-PGND, SW-PGND, VIN-SW, VOUT-PGND): these are the stored fills, re-measured here as 0.30 mm; on the refilled copper the same pairs are 5.0 / 1.95-3.0 / 1.0-3.0 / 1.0-3.0 / 0.9-3.0 mm (section 3). | The checker measures the wrong copper for the power board; its 9 "exceeding" rows include 5 that disappear on refill and 4 that are real (PE-PCB-002 Q2.2 41.2 mm, PE-PCB-006 VIN_RAW/VOUT_L via counts, KR-TH-002 B.Cu). | human review |
| ERC | `verification/erc/20261010T165532Z-erc-02a2619f` (power) and `...071810Z-erc-b207ac59` (control), 0 findings; verifier `verification-summary.json` status passed, problems []. | The verifier checks hash currency only; it cannot see LR-20. | pass (scope) |
| Netlist checks | `netlist_check_power.json`: exact, 648 pads / 101 nets / 237 refs; control exact, 667 / 111 / 207. | - | pass |
| Export manifests | `manufacturing/*/export-manifest.json`: 11/11 commands exit 0, 35 hashed artefacts each; `logs/step.log` missing 3D models power L2/L3/L4 (WE-SL2), control U1/U3/Y1 (library bundle). Power gerbers = stored fills (LR-20). | Control bundle consistent; power bundle blocked. | pass (control) / fail (power) |

## 2 Power board - placement as built (measured)

Outline 240 x 180 mm (0,0)-(240,180); 4 x 70 um, 2.0 mm; 237 footprints, 4752 tracks, 574 vias (412 x 0.3 mm,
149 x 0.6 mm, 13 x 0.4 mm), 20 copper zones + 12 rule areas. All ICs on F.Cu; B.Cu carries the driver-island
passives (R19-R23, R29-R33, C21, C25, C34, C35 HS; R37-R41, R47-R51, C41-C43, C45, C54, C55, D5 LS), the PE
reference network R14/R15/R16 and the V_GS probe loops TP1/TP2.

| Item | Position / geometry |
|---|---|
| Heatsink HS1 LAM 5 D K | centre (99.25, 67.0), courtyard x 48.5-150.0, y 16.5-117.5 (101.5 x 101 mm), four 3.2 mm NPTH at (54.25/144.25, 22/112); F.Cu rule area `HEATSINK_HV_KEEPOUT` 43.4-155.1 x 11.4-122.6 (5 mm around the courtyard, **F.Cu only**) |
| Devices | Q1 HS pads 1-4 at x 87.0 / 92.08 / 94.62 / 97.16, Q2 LS at 115.0 / 120.08 / 122.62 / 125.16, row y = 126.0 (28 mm pitch, pads 1.905 x 4.5 mm); courtyards 5.9 mm below the sink courtyard (baseline lead row 3-5 mm from the sink face: formed leads / spacer, mechanical HR) |
| HF ceramics | C1-C6 (0.47 uF/630 V 2220) in one row at y 125.9, x 48.0-79.0 (6.2 mm pitch), **west of Q1 only**; C7-C10 at y 136.5, x 41.8-60.4; VIN pads at y 128.5, PGND pads at y 123.3 (upper row) / 133.9 (lower row); group bbox 41.8-79.0 x 123.3-139.1 |
| Drivers | U1 (HS) (96.2, 145.0), U3 (LS) (124.0, 145.0) on the barrier line; U1.4 -> Q1.4 14.35 mm, U3.4 -> Q2.4 14.36 mm; COM pins to Kelvin pads 14.78 / 14.72 mm |
| Barrier line | U2 (77.5), U1 (96.2), U3 (124.0), U4 (142.8), U5 (163.0), U6 (181.0), U7 (195.0), U10 (212.0), all at y = 145.0; ISO_BARRIER rule area 0-240 x 140-150 on all four layers |
| Inductor L1 | centre (204.5, 95.0), courtyard 169.5-239.5 x 60.0-130.0 (70 mm), pads SW (191.8, 95.0) / VOUT_L (217.2, 95.0) 3.2 mm, four 4.3 mm standoff holes with all-layer rule areas |
| Films | C11/C12 20 uF/800 V at (14.9, 33.0) / (14.9, 77.0) (37 mm tall); C13/C14 60 uF/450 V at (185.5, 23.5) / (217.5, 23.5) (45 mm tall) |
| Terminals | J1 VIN_RAW (7.5, 112), J2 PGND-in (7.5, 129), J5/J6 relay contacts (23, 112) / (23, 129) (J6 = VIN after the relay), J3 VOUT (161, 50), J4 PGND-out (161, 65.5); 3 x 3 REDCUBE THR fields |
| PE | H1 M4 stud (43.8, 27.5) on the F.Cu VIN pour edge; Y caps C18 (PE pad (42.5, 19.0)), C19 (PE pad (42.5, 36.0)); R14 0 R PGND-PE link, R15/R16 1 M (B.Cu, (45.6, 45-64)) |
| SELV strip | GND_CTRL In1 pour 1.2-238.8 x 151.0-178.8 (5866 mm2, one island); 86 SELV-only parts in y 153.5-174.5; J7 socket (211, 160) rotated -90, pin 1 (211.0, 160.0), pin 50 (150.04, 157.46); H8 (235, 158), H9 (123, 158) M3 |

## 3 Power board - isolation (KR-ISO-001..004, standards_and_spacing)

Minimum copper-to-copper distances per layer, (stored fill | rule-aware refill), mm. Pads of the barrier
packages excluded where stated (they bridge the barrier by design).

| Pair / rule | F.Cu | In1.Cu | In2.Cu | B.Cu | Requirement | Finding | Disposition |
|---|---|---|---|---|---|---|---|
| HV/DRV/DESAT/SENSE_ISO to CTRL_SELV, barrier packages excluded | 9.49 / 9.49 | 11.10 / 11.10 | 11.10 / 11.10 | 11.30 / 11.30 | 9.0 all layers | met on every layer in both fill states | pass |
| same, including the barrier packages' own pads | 7.25 / 7.25 | - | - | - | 9.0 | the land patterns themselves set 7.25 mm (UCC21710 DW), 8.1 (UCC14141 DWN), 7.75 (TMCS1133 DVG), 9.1 (AMC1311 DWV): the package, not the board, is the clearance limit; standard minimum per `pcb_stackup.md` is 5.5 mm | human review (package rating vs the strict 9.0 mm column, already an HR item) |
| ISO_BARRIER 10 mm strip, copper items | 0 tracks/vias/zones on any layer (94.6 mm2 of barrier-package pads inside the strip, allowed by the rule area) | | | | none | copper-free strip 0-240 x 140-150 | pass |
| CTRL_SELV items on the HV side (y < 140), HV-side items on the SELV side (y > 150) | 0 / 0 items | | | | none | no intrusion either way; SELV-only parts occupy y 153.5-174.5 | pass |
| HV (VIN/SW/PGND/VOUT) to PE | 0.30 / 5.00 | 0.30 / 5.00 | 0.30 / 5.00 | 0.30 / 4.69 | 5.0 (3.0 absolute) | stored fills: the VIN F.Cu/In2 and PGND In1/B.Cu pours run 0.30 mm from the PE stud H1 and the Y-cap PE pads C18.2 / C19.2 on all four layers (16 DRC errors without refill); refilled: 5.0 everywhere except R14.2/R16.2 (B.Cu 4.69, 2512 pin-field exception in `.kicad_dru`) | **fail** on the stored copper (LR-20); pass after refill; R14/R16 human review |
| DRV/DESAT/SENSE_ISO to PE | 99.2 | 99.2 | 93.3 | 65.0 | 5.0 | - | pass |
| HV functional VIN-PGND (outside Q1/Q2/D1) | 0.30 / 1.95 | 0.30 / 1.00 | 0.30 / 1.00 | 0.30 / 3.00 | 3.0 outer / 1.0 inner | refilled values meet the rule except F.Cu 1.95 mm, which the DRC accepts through a pin-field exception (R4/R5/R6 bleeder / damping pads) | pass after refill (exceptions HR) |
| SW-PGND | 2.70 / 2.70 | 0.30 / 1.00 | 0.30 / 1.00 | 0.30 / 3.00 | 3.0 / 1.0 | F.Cu 2.70 mm is the snubber R11/C15 pad pair (exception) | pass after refill (HR) |
| VIN-SW | 2.70 / 3.00 | 25.6 | 0.30 / 1.00 | 25.6 | 3.0 / 1.0 | - | pass after refill |
| VOUT-PGND | 0.30 / 0.90 | 0.30 / 1.00 | 0.30 / 1.00 | 0.30 / 3.00 | 3.0 / 1.0 | F.Cu 0.90 mm after refill = C13/C14 film pad fields / output divider pads (exception rules) | pass after refill (HR) |
| HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS) | 6.27 | 6.40 | 4.80 | 6.40 | 3.0 / 1.0 (CR-23) | - | pass |
| DESAT_HS to VIN (full bus when off) | 3.22 | 26.7 | 0.30 / 1.00 | 25.4 | 3.0 / 1.0 | - | pass after refill |
| HV copper to board edge | left 1.22, top 1.12, right 1.22 (refilled, F.Cu and B.Cu) | | | | 1.0 | - | pass |
| KR-ISO-004 slots | U1/U3: g 7.25, e 3.55, path 10.15; U2/U4/U5: g 8.10, e 3.00, path 10.08; U6/U7: g 9.10, e 3.19, path 11.12; U10: g 7.75, e 3.00, path 9.81; all slots 1.20 mm wide (y 144.4-145.6), one per package, centred on the barrier line | | | | path >= 9.0, e >= 3.0, width >= 1.0 | recomputed from the pad polygons, equal to the checker | pass (slot width / routing tolerance with the fabricator: HR) |
| KR-ISO-003 classes | every net on the board carries a class (only the three unconnected pads are unclassified); 45 custom rules incl. 39 pin-field exceptions | | | | all nets classed | - | pass |
| Heatsink mounting holes (PE-bonded hardware through the board) | HV-side copper to each of the four HS1 3.2 mm holes: F.Cu 8.85-15.05, B.Cu 9.0-11.0, **In1.Cu 0.25, In2.Cu 0.25** (both fill states; the PGND In1 and VIN In2 pours stop only at the default hole clearance) | | | | 5.0 mm HV copper keep-out around the PE-bonded sink (baseline); the M4 standoffs H2-H7 and the L1 standoffs do have all-layer rule areas | the four sink screws/standoffs pass 0.25 mm of FR4 from 400 V inner copper; nothing in the DRC can see it (NPTH pads carry no net) | **fail** (LR-21) |

## 4 Power board - gate drive (KR-PCB-001/002/003/005, PE-PCB-001)

| Rule | Evidence (measured) | Finding | Disposition |
|---|---|---|---|
| KR-PCB-005 / PE-PCB-001 driver beside its switch | U1 output pad 4 -> Q1 gate pad 4 = 14.35 mm; U3.4 -> Q2.4 = 14.36 mm; COM -> Kelvin pads 14.78 / 14.72 mm. Drivers on F.Cu on the barrier line (forced by the slotted SOIC-16 footprint), gate resistors R19-R23 (HS) and R37-R41 (LS) on B.Cu between driver and device. V_GS probe loops TP1 (102.0, 126.0) G_H/KS_H and TP2 (130.0, 126.0) G_L/KS_L on B.Cu at the devices (CR-11). | Within the 15 mm target but at its edge; the baseline's "drivers on B.Cu directly under the device row" was not realised - the slotted barrier footprint fixes the drivers on the barrier line 19 mm from the lead row. | pass (geometry) / human review |
| HS gate path (KR-PCB-001) | G_H: 26.4 mm of 0.35 mm B.Cu track + 77 mm2 B.Cu pour, 0 vias; HS_OUTH / HS_OUTL / HS_CLMP 3-5 mm each with one via (F.Cu driver pin -> B.Cu resistor); gate-side copper 40 mm in total. KS_H: In2 pour 505 mm2 under the island + 54 mm F.Cu / 36 mm B.Cu / 8 mm In2 track, 11 vias. 70 % of the B.Cu gate copper (56.6 of 80.9 mm2) lies over KS_H copper on In2 (0.20 mm prepreg). | Gate over Kelvin on adjacent layers, compact loop. | pass |
| LS gate path (KR-PCB-001) | G_L: 15.6 mm F.Cu + 8.6 mm B.Cu + 8.9 mm In2 track, 34 mm2 B.Cu pour, **7 vias**; LS_OUTH 19.6 mm / 3 vias, LS_CLMP 21.5 mm / 3 vias, LS_OUTL 10.2 mm / 1 via; 84 mm in total (2.1 x the HS side). KS_L: In2 pour 248 mm2 + 26.6 mm F.Cu / 55.0 mm B.Cu / 6.6 mm In2 track, 9 vias. 57 % of the B.Cu gate copper over KS_L In2 copper; the F.Cu (11.1 mm2) and In2 (4.3 mm2) gate copper has no Kelvin copper on an adjacent layer. R41 (G_L / LS_GK) at (134.0, 121.5) and TP2 sit on B.Cu directly over the In2 SW pour (0.20 mm dielectric). | The LS gate loop changes layer seven times and is twice as long as the HS loop; the gate-Kelvin pull-down R41 couples to the switch node through 0.2 mm of prepreg (about 1.5 pF for a 2512 pad pair; at 20 kV/us about 30 mA displacement current into the gate node). | **should-fix** (LR-24) |
| KR-PCB-002 decoupling inside the gate loop | HS: C24 (VDD_H-KS_H, (93.5, 131.0)) and C26 (KS_H-VEE_H, (97.5, 131.0)) 5.1 / 5.8 mm from Q1.3, 14 mm from U1, on the driver-gate axis (0.73); bulk C22 / C23 / C25 at (69.5-75.0, 130.5-134.5) 20-27 mm from Q1.3 and 24-29 mm from U1, west of the device. LS: C44 / C46 at (126-130, 132.5) 7.3 / 9.8 mm from Q2.3; bulk C42 / C43 / C45 on B.Cu at (143-154, 130.0) 21-32 mm from Q2.3, 24-34 mm from U3, beyond the device toward +x (axis 0.85-0.88). U1.5/8 -> C37 6.9 / 7.6 mm; U3.5/8 -> C56 4.7 / 9.5 mm. | The 100 nF capacitors close the HF gate current near the Kelvin pin; the 4.7 uF bulk capacitors are outside the driver-gate span on both channels. | pass (HF) / should-fix for the bulk (LR-24) |
| KR-PCB-003 Kelvin never tied to power source | KS_H vs SW and KS_L vs PGND: distinct nets, the only part on both nets is the device (Q1 / Q2), copper distance > 0 on every layer (0.30 mm at the pin fields, same-reference-island rule), netlist exact. | Hard constraint met. | pass |

## 5 Power board - commutation loop and HF capacitors (KR-PCB-004, KR-CAP-003, PE-PCB-002/003)

Loop overlay as built (pad centres; layer transitions in brackets):

C1..C6 VIN pads (y 128.5, x 48-79, F.Cu) -> F.Cu VIN pour (HF-tier component 14.0-88.2 x 120.0-139.9,
664 mm2 after refill) -> Q1.1 drain (87.0, 126.0) [THT, all layers] -> Q1.2 source SW (92.08) -> **In2 SW
pour** (the F.Cu SW strip 91.0-116.1 x 122.6-128.6 passes the KS_H / G_H pads through 0.8 mm slivers at
(95.9, 123.0), so F.Cu is not a current path) [THT -> In2, attachment 3.4 mm wide at (102.0, 120.8)] ->
Q2.1 drain (115.0) [In2 -> THT, 4.5 mm at (118.1, 121.0)] -> Q2.2 source PGND (120.08) [THT -> In1,
attachment 4.9 mm at (119.5, 123.8)] -> **In1 PGND plane** westward under the SW strip and the F.Cu VIN pour
(overlap VIN-F.Cu / PGND-In1 206 mm2 refilled, 506 stored; SW-In2 / PGND-In1 197 mm2) -> one 0.6 mm via per
capacitor into each PGND pad (y 123.3 / 133.9) -> C1..C6 (C7..C10 through the same pour).

| Rule | Evidence | Finding | Disposition |
|---|---|---|---|
| PE-PCB-002 capacitors beside the half bridge | VIN pad -> Q1.1: C1 8.4, C2 14.4, C3 20.5, C4 26.7, C5 32.9, C6 39.1, C7 29.6, C8 35.3, C9 41.1, C10 47.0 mm. PGND pad -> Q2.2: 41.2 (C1) ... 78.7 mm (C10). Target: rows <= 5 and <= 15 mm, columns beside the legs on both sides. | Only C1/C2 are within 15 mm of the HS drain; no capacitor is within 40 mm of the LS source; the whole tier sits west of Q1 in the 17 mm band between the sink keep-out (y <= 122.6) and the barrier (y >= 140). The band east of Q2 (x 128-170, y 123-140) holds only LS bulk decoupling and the snubber. | **fail** (LR-22) |
| PE-PCB-003 loop geometry | Forward path F.Cu (VIN) and In2 (SW) over the In1 return (0.20 mm prepreg F.Cu-In1, **1.32 mm core In2-In1**); span 72 mm (C6 -> Q2.2) plus two TO-247 lead pairs; return plane perforated under the SW strip by the 7 x 4 field of 0.6 mm SW vias (merged 1.0 mm antipads, about 10 x 5 mm hole at x 104-114). Estimate L = mu0 h l / w: F.Cu/In1 section (l 40, w 10, h 0.2 mm) about 1 nH; In2/In1 SW section (l 28, w 12, h 1.32 mm) about 4 nH; vias and THT transitions 1-2 nH; board loop about 6-8 nH, below the 20 nH target but with the SW leg on the core side of the stack. | The SW current moves to In2 (core-separated from the return) because the F.Cu SW strip is cut by the pin field; the baseline put SW on F.Cu over the In1 return. | human review / should-fix with LR-22 |
| KR-CAP-003 film + ceramics | Films C11/C12 at x 15 (20 uF each) 83-107 mm from Q1.1, joined to the tier through the In2 VIN pour only (the F.Cu VIN pour is two components: 1.2-88.9 x 1.2-101.5 and the tier 14.0-88.2 x 120.0-139.9; the 32 VIN vias sit at the films (20), the tier (6) and the damping network (6)). Ten 0.47 uF ceramics = 4.7 uF local. | Structure as designed; the local tier is one-sided (LR-22). | pass (structure) |
| Refill effect on the tier | After the rule-aware refill the F.Cu VIN pour between the capacitors narrows to 2.0 mm at (38.9, 138.9) (C1 -> C10 spine) and 2.3 mm at (72.7, 128.4) (Q1.1 -> C6): the 3.0 mm outer clearance to the PGND pads of the neighbouring 2220 capacitors (pad gap 5.2 mm) and the sink keep-out at y 122.6 leave no room for a wide VIN pour along the row; the stored 0.3 mm fill hid this. | With compliant clearances the far capacitors (C4-C6, C8-C10) are fed through about 2 mm wide F.Cu necks and the In2 pour; their HF contribution is inductive. | **should-fix** (LR-22) |

## 6 Power board - inductor, SW copper, thermal (PE-PCB-005, KR-TH-002, SKILL-006, CR-23)

| Rule | Evidence | Finding | Disposition |
|---|---|---|---|
| PE-PCB-005 SW copper extent | SW copper: F.Cu 120 mm2 (91.0-116.1 x 122.6-128.6), In2 2052 mm2 refilled (89.0-195.5 x 91.5-126.8), B.Cu 6 mm2; 24 x 0.6 mm SW vias at x 100-120. Sensitive copper to SW: AMC1311 outputs >= 29.2 mm, TMCS1133 outputs >= 32.4 mm, U6/U7/U10/U8 pads >= 22.3 mm; LS-island B.Cu copper over the In2 SW pour 5.4 mm2 (R41, TP2), HS-island 1.9 mm2 (TP1). | The 2052 mm2 inner switch-node pour spans the whole gap to L1 and is the only SW current path (section 7). Sensing is far from it. | human review |
| Inductor placement | L1 courtyard 19.5 mm from the sink courtyard (body-to-body about 20.3 mm); SW pad 76.8 mm from Q1.2 in x; L1 in the exhaust corridor (+x) as the floorplan intended. | CR-23 20 mm met to the body, not to the courtyard. | pass (marginal) |
| Films / PTC / MOV spacing | C11, C12 courtyards 19.1 mm from the sink courtyard (about 19.9 mm body), RT1 8.5 mm, RV1 8.4 mm; C13 20.0, C14 52.0 mm; films to L1 15.3 / 15.4 mm (>= 15). | The sink is not flush with the left edge as floorplan B described: a 48 mm band (x 0.5-43) at the intake side holds C11/C12 (37 mm tall), RT1 (22 mm) and RV1 (23 mm). If the LAM 5 D K draws air from the -x face (exhaust +x per the floorplan) the corridor rule (parts <= 15 mm tall) is broken by four parts and the films are 0.9 mm inside the 20 mm limit. | **should-fix** / human review (LR-25) |
| KR-TH-002 HV keep-out, outer layers | F.Cu: no HV-side copper within 5 mm of the courtyard (rule area present). B.Cu: PE_REF_MID copper (R15.2, R16.1, track) inside the courtyard at 0.0 mm and the LS gate parts R41 (G_L / LS_GK) with their tracks 4.0 mm from it; no B.Cu rule area. | The B.Cu intrusion is the PE reference divider (PE_REF_MID between PGND and PE through R15 / R16 = 1 M; at PGND potential when the 0 R link R14 is fitted). Under the sink on the bottom side only the mounting hardware matters - LR-21. | fail (rule) / human review (consequence) |
| KR-TH-002 interface | Sil-Pad TSP A2000 per device, clip force, pad voltage rating vs 4 kV impulse: not board geometry (CR-21). | - | human review |

## 7 Power board - high-current copper and vias (KR-PCB-006, PE-PCB-006, IPC-2221)

IPC-2221 minimum for 25 A at 20 K rise, 70 um: 8.4 mm outer / 21.8 mm inner (the baseline's 12 mm outer
corresponds to a 10 K rise); 27.5 A: 9.5 / 24.8 mm. Currents used: SW and VOUT 25 A (inductor current), input
dc 12.5 A, 17.7 A rms in the film-to-tier path. Widths are neck widths on the **refilled** copper (the stored
fills are wider by the clearance difference and are not the copper the DRC accepted). Via capacity: 0.6 mm
drill, 25 um plating, about 0.05 mm2 each (about 2 A at 20 K).

| Path | Layer(s) carrying it | Neck width (location) | Finding | Disposition |
|---|---|---|---|---|
| VIN_RAW J1 -> RT1 / J5 | F.Cu 12.4 + B.Cu 12.4 mm (THT terminals join the layers; the checker's "0 vias" is a proxy artefact) | 24.8 mm outer-equivalent | adequate | pass |
| VIN after the relay, J6 -> Q1.1 (12.5 A dc) | F.Cu tier pour 35 mm, In2 pour > 80 mm | wide | adequate | pass |
| VIN films C11/C12 -> tier (17.7 A rms) | In2 pour only (> 80 mm wide); F.Cu VIN is two separate components joined through 26 vias and the THT pads | In2 wide, F.Cu not continuous | 2-3 A/mm2 on the inner pour: thermally fine, but the baseline's F/In2/B paralleling is not implemented between films and tier | pass (thermal) / note |
| **SW Q1.2 / Q2.1 -> L1.1 (25 A)** | **In2 only**: attachments 3.4 mm at (102.0, 120.8) and 4.5 mm at (118.1, 121.0) (pin-field limited), bulk pour 12.7 mm at (144.3, 120.2); F.Cu SW strip 0.8 mm slivers at the KS/G pads; B.Cu 6 mm2 | 12.7 mm inner = 48 K by IPC-2221 at 25 A (28 A/mm2) vs 21.8 mm required inner, or 12 + 22 mm paralleled per baseline | the switch-node current to the inductor runs on one inner layer at roughly half the required width; nothing usable on F.Cu or B.Cu | **fail** (LR-23) |
| **PGND input J2 -> plane (17.7 A rms)** | In1 only: J2's B.Cu copper is an isolated 415 mm2 island (1.2-43.4 x 120.0-139.9), no F.Cu PGND; the In1 plane leaves the J2 pocket between the J6 pin field and the barrier through a 3.8 mm passage at (23.0, 137.9) plus a 2.2 mm passage above J6 (6.8 mm total at x = 23, 8.1 mm at x = 20 / 26) | 3.8 / 6.8 mm inner = 160 / 62 K by IPC-2221 at 17.7 A (66 / 37 A/mm2) | the whole input return crosses a 6.8 mm inner isthmus; it is short (about 5 mm) so the real rise is lower, but far outside every target | **fail** (LR-23) |
| PGND films C12.2 -> Q2.2 | In1 plane 16.1 mm at (20.2, 62.3), 5.0 mm at the Q2.2 attachment (119.5, 123.8) | plane path wide, attachment pin-field limited | - | pass |
| PGND output J4 -> C13.2 (25 A) | In1 only (B.Cu PGND J4 -> C13.2 not connected): 19.3 mm at (154.1, 28.0) | 24 K by IPC-2221 at 25 A | marginal vs 21.8 mm; the B.Cu PGND pours near the output (1903 + 1213 mm2) are not joined to the J4 field | should-fix (LR-23) |
| VOUT U10.2 -> C13/C14 -> J3 (25 A) | F.Cu 24.6 + In2 25.5 + B.Cu 25.5 mm (J3 reached on F.Cu and In2) | about 60 mm outer-equivalent | three paralleled pours, 61 x 0.6 mm vias, as the baseline intends | pass |
| VOUT_L L1.2 -> U10.1 (25 A) | F.Cu only, 4.8 mm at the TMCS1133 pins (215.8, 138.3); pour 422 mm2 refilled | 50 K by IPC-2221 at the pin funnel (75 A/mm2) | the package land pattern is the limit (as on TI's EVM); add B.Cu copper in parallel to the pins and keep the funnel short | human review |
| Via arrays | VIN 32 x 0.6 (films 20, tier 6, damping 6), SW 24 x 0.6 at the devices, PGND 32 x 0.6 + 18 x 0.3 + 8 x 0.4 (output side 22, tier 10), VOUT 61 x 0.6 (L1/U10 region 36, films/J3 25); tier PGND pads: exactly one 0.6 mm via per capacitor (C1-C10), VIN pads none (fed by the pour) | >= 24 per transition met where arrays exist; the tier return uses ten single vias | about 0.5 nH per capacitor in series, small in parallel | pass / note |
| SELV supply track widths | 12V_PROT 261 segments 0.25-0.35 mm, 277 mm; 3V3 0.25-0.55 mm, 434 mm; 12V_BIAS_S 0.25-0.4 mm, 100 mm | 0.25 mm x 70 um about 2 A at 20 K; 12V_PROT load (fan 0.5 A + three bias modules about 0.25 A each) about 1.3 A -> about 8 K, about 0.27 ohm series | acceptable; a 0.5 mm class width would halve the drop | note |

## 8 Power board - sensing, grounding, mezzanine (PE-PCB-004/007/008, interconnect)

| Rule | Evidence | Finding | Disposition |
|---|---|---|---|
| PE-PCB-004 TMCS1133 | U10 (212.0, 145.0) straddles the barrier in the L1.2 -> VOUT path (VOUT_L 45 mm from L1.2); ISENSE U10.6 -> J7.43 / TP9: 84 mm (In2 58, B.Cu 24, F.Cu 2), 7 vias; ISENSE_REF is generated on the strip (R82 9.09 k / R83 1 k / C89 from 3V3) -> J7.45: 90 mm, 5 vias; the two nets do not run together. | ISENSE_REF is a local dc reference, not a Kelvin return, so the mismatch is not a measurement error; the 84 mm single-ended run is long for a 50 kHz current signal. | note |
| PE-PCB-004 AMC1311 outputs | VIN_OUTP 80.9 mm **on In2** / VIN_OUTN 79.4 mm **on F.Cu**; VOUT_OUTP 64.9 mm **on B.Cu** / VOUT_OUTN 63.1 mm **on In2**; mismatch 1.5 / 1.8 mm; U6 (181, 145), U7 (195, 145) to U8 (165.5, 170) 30-40 mm apart, routed 62-81 mm. | Each differential pair is split across two layers for its whole length - the pair's common-mode rejection at the OPA2320 relies on matched coupling that two layers cannot give. | **should-fix** (LR-26) |
| PE-PCB-005 analogue vs SW | Minimum copper distance of all sense nets and of U6/U7/U8/U10 pads to SW copper 22.3-42.1 mm (any layer). | - | pass |
| PE-PCB-007 separation / grounding | SELV section to HV section 12.3 mm (checker proxy, barrier packages excluded); GND_CTRL In1 pour 5866 mm2, one island under the strip (y 151-178.8); PGND-to-PE link R14 0 R / R15, R16 1 M at the stud (open item "PGND floating vs bonded" unchanged); REF3125 U9 (222.5, 162.0) and OPA2320 U8 on the strip. | - | pass / human review (bonding option) |
| PE-PCB-008 decoupling (power board) | U1 7.6 mm, U3 9.5 mm (UCC21710 rails: C37 / C56 at the driver, 4.7 uF bulk 20-34 mm away, section 4); U2 9.4, U4 13.9, U5 27.5 mm (UCC14141 pins 6/7 to C60), U6/U7 4.3 / 8.3, U8 3.7, U9 5.2, U10 15.5 mm. | U5 (sensing bias module) input decoupling 27.5 mm and U10 15.5 mm are loose; the rest within 15 mm. | note |
| Mezzanine mating | J7 pins 1/2/49/50 map onto J8 pins 1/2/49/50 with 0.00 mm error under a 180 deg rotation (no mirror: control board component side up, header on its B.Cu); control outline projected onto the power board x 119.0-239.0, y 154.0-234.0 -> 26 mm over the SELV strip (y 154-180), **54 mm overhang** beyond the edge (architecture: about 40 mm); control H3/H4 land on power H8 (235, 158) / H9 (123, 158) to 0.00 mm; control H1/H2 map to (235, 230) / (123, 230), 50 mm beyond the edge - no standoff; power H10 (60, 170) / H11 (90, 170) match nothing on the control board. HV-side copper under the projected control outline: 0 mm2 on every layer, nearest 12.6 mm. | Electrically clean (no HV copper under the control board, 11 mm air-gap argument unchanged); mechanically a 120 x 80 mm board held by two standoffs and the 50-pin socket, cantilevered 54 mm. | **should-fix** (LR-27) |
| HV probing / test points | No HV test points; TP1/TP2 V_GS loops on B.Cu at the devices; SELV test points TP3-TP13 on the strip. | - | pass |

## 9 Power board - area, compactness, routing complexity, exports

| Item | Evidence | Finding | Disposition |
|---|---|---|---|
| Area vs baseline | 240 x 180 mm = 43 200 mm2 (target 240 x 180; stretch 230 x 170 not attempted); HV bbox fraction 0.77; 54.9 footprints/dm2; 1157 W/dm2, 1608 W/L at 72 mm assembly height; courtyard fraction front 0.59, back 0.01. | Target met; the back side is essentially unused (1 %), which is where the baseline wanted the drivers. | pass |
| Routing complexity | 4752 track segments (4379 at 0.25 mm), 574 vias; CTRL_SELV 4282 mm / 266 vias, DRV_LS 500 mm / 58 vias, DRV_HS 350 mm / 37 vias, SENSE_ISO 190 mm / 16 vias; longest nets 3V3 434 mm, 12V_PROT 277, PG_BIAS_H_N 269, RELAY_ON 204; 21 rip-up rounds and 12 order trials (748 s) to reach 0 open; serpentine bundles under J7 on B.Cu (layer PDF). | Functional; the strip routing is grid-router meandering rather than a designed bus - a rework burden, not an electrical defect. | note |
| Exports (power) | 11/11 commands, 35 hashed artefacts, but all copper layers plotted from the stored fills (LR-20); drill 722 PTH + 26 NPTH (8 slots 1.2 mm, 8 x 3.2, 10 x 4.3); 3D models missing for L2/L3/L4. | Bundle must be regenerated after a rule-aware refill. | **fail** (LR-20) |

## 10 Control board (TMS320F28335, 120 x 80 mm, 4 x 35 um, 1.6 mm)

207 footprints, 5995 track segments (5485 at 0.20 mm), 798 x 0.3 mm vias, 7055 mm of track, 20 zones;
stored fills = DRC'd copper; U5 at (68.0, 31.0) rotated 90 deg (candidate B); J8 2 x 25 header on **B.Cu** at
(28.0, 74.0), pin 1 (28.0, 74.0), pin 50 (88.96, 76.54).

| Rule / item | Evidence (measured) | Finding | Disposition |
|---|---|---|---|
| PE-PCB-008 DSP decoupling | 26 bypass capacitors (15 x 1V9 on B.Cu under the body, 11 x 3V3 on F.Cu): pin -> capacitor pad 3.90-5.38 mm (C29, C31 at 5.38; C37 4.79; mean 4.4), every GND pad has a GND via within 1.1-2.0 mm; 1V9 In2 island 779 mm2 (46-81 x 3-44) under the DSP, 37 vias; 3V3 island 5200 mm2, 84 vias. | Two capacitors 0.38 mm over the 5.0 mm spec proxy; return path short on every capacitor. | pass (note) |
| Plane continuity (In1 GND_CTRL) | One island, 8376 mm2 of 9600 (87 %), bbox 1-119 x 1-79; voids > 4 mm2: 28, the largest the four 3.2 mm holes (10.8 mm2), J1 (9.4), a 10 x 1.1 mm slot of merged escape-via antipads under the DSP's ADC side at (62.7-72.8, 41.7-42.8) and a 2.5 x 7.8 mm void at (39.6-42.1, 67.3-75.1); outer-layer track length not over In1 copper: EPWM1A 5.1 of 51.3 mm, PWM_H/L 4.2 / 3.9 of 15.3 / 26.7, CLK30 2.2 of 14.6, ADC_VIN 2.2 of 40.0, ADC_VOUT 17.7 of 139.2, FAULT_N 40.8 of 319.7, DSP_TRIP_N 29.3 of 224.4 (these include pad / antipad crossings). | Solid plane; the escape-via slot under the ADC side is the only designed-in discontinuity, crossed by ADC_VOUT and the fault lines. | pass / note (LR-34) |
| PWM path | EPWM1A 51.3 mm / 4 vias, EPWM1B 42.9 / 2 (DSP -> gating logic); PWM_H_G 11.1 / 2, PWM_L_G 8.9 / 2; PWM_H 15.3 / 2, PWM_L 26.7 / 2 to J8 pins 14 / 17. | Short, over the plane. | pass |
| Trip / fault path | DSP_TRIP_N 224.4 mm / **21 vias**; FAULT_N 319.7 mm / 16 vias; XRS_N 226.1 / 21; OC_N 204.1 / 10; ESTOP_N 403 / 24; FLT_H_N 105 / 8, FLT_L_N 92 / 10, RDY_L 99 / 9. | The hardware trip into the DSP TZ input and the fault combiner lines are grid-router meanders of 200-400 mm with 10-24 vias across the board - no timing problem at these speeds, but long antennas for a protection path and a rework burden. | **should-fix** (LR-32) |
| Analogue separation (PE-PCB-005) | ADC filter capacitors to DSP pins: ADC_VIN 6.9, ADC_ISENSE 9.3, ADC_I12V 9.9, ADC_TEMP_HS 10.2, ADC_VOUT 10.1, ADC_V12V 10.7, ADC_TEMP_CTRL 11.1, ADC_ISENSE_REF 14.8 mm (baseline "1 k + 1 nF at every ADC pin"); ADCREFM/P capacitors 5.8 / 6.4 mm. Same-layer proximity analogue vs clock/PWM/fault nets < 0.6 mm: ISENSE_REF-FAULT_N 1.6 mm parallel on F.Cu, otherwise < 0.6 mm of parallel run. ISENSE 122.2 mm / 5 vias vs ISENSE_REF 54.5 mm / 6 vias (Hausdorff 21 mm - not routed together); VIN_SENSE 111.5 / 8 vias vs VOUT_SENSE 55.5 / 2; ADC_VOUT 139.2 mm / 14 vias. | No coupling hazard found; the front-end capacitors are still 7-15 mm from the pins and the sense lines from J8 wander. | **should-fix** (LR-33) |
| Clock | Y1 (72.5, 7.4) 11.1 mm from U5.105 (XCLKIN); CLK30 14.6 mm / 2 vias, CLK30_SOURCE 6.0 mm / 2 vias, over the plane. | - | pass |
| Supplies | 12V_IN 0.5-1.0 mm (12 segments), 12V_PROT 0.4-1.0 mm + In2 island 1375 mm2 (left column), EFUSE_RTN 0.4 mm / 68 mm / 15 vias, 5V 0.4 mm + island 610 mm2, 5V_SW 4 segments 0.5-0.7 mm / 14 mm on F.Cu only, 3V3 / 1V9 stubs 0.25-0.3 mm into the islands; U2 TPS54302 VIN pin -> C5 2.04 mm; U1 TPS26400 pad 17 (EFUSE_RTN) 8 vias, U3 TPS767D301 pad 29 (GND_CTRL) 8 vias. | Earlier LR-05 / LR-06 / LR-07 items resolved. | pass |
| Connectors | J1 12 V in (12.0, 8.3) top edge; J2 reset (4.5, 44.0), J4 boot (4.5, 35.0), J5 UART (4.5, 25.0) left edge; J3 JTAG (93.0, 7.0) top edge; J6 E-stop (113.0, 20.0), J7 NTC (113.0, 58.0) right edge; J8 mezzanine (28.0, 74.0) bottom edge on B.Cu; all within 4.5-8.3 mm of an edge; copper to edge >= 1.52 mm. | - | pass |
| Mezzanine on B.Cu (interconnect) | J8 on B.Cu; mates with power J7 at 0.00 mm (section 8); pins 39/40 carry net 3V3 where the baseline table says +3V3_PWRBOARD (naming, schematic level); H1-H4 3.2 mm NPTH at (4/116, 4/76), no net (no PE bond on this board). | - | pass (naming note) |
| In2 islands | 1V9 779 mm2, 3V3 5200 (two islands), 5V 610, 12V_PROT 1375, plus eleven 2-6 mm2 fragments (3V3 / 5V / 1V9 "corridor" zones, e.g. (60.4-61.9, 41.6-44.5), (43.0-44.8, 26.5-28.5)). | Fragments are via-fed and harmless; DFM tidiness (earlier LR-15 pattern). | note (LR-34) |
| Area / complexity | 9600 mm2 (target 120 x 80), 215.6 footprints/dm2, courtyard front 0.30 / back 0.05; 5 routing-order trials (best 0 open). | - | pass |
| Exports | 11/11 commands, 35 hashed artefacts, stored fills = DRC'd copper; 3D models missing for U1, U3, Y1. | Bundle consistent. | pass (note) |

## 11 Summary and supersession

**Power board - not finished.** Blockers: LR-20 (stored fills violate the project rules; exports and
metrics describe non-compliant copper), LR-21 (heatsink mounting holes 0.25 mm from HV inner copper, no
rule areas), LR-23 (input PGND return through a 3.8 / 6.8 mm inner isthmus at (23.0, 137.9)). Should-fix:
LR-22 one-sided HF tier and 2 mm VIN necks after refill, LR-24 LS gate loop, LR-25 intake corridor /
film spacing, LR-26 AMC1311 pairs split across layers, LR-27 mezzanine support, LR-28 SW current on In2
only (12.7 mm) and output PGND 19.3 mm. Passes: isolation strip, 9 mm HV-to-SELV, slots (all eight
packages, path 9.8-11.1 mm), HS/LS island barrier, Kelvin separation, HS gate loop, VOUT copper, area.

**Control board - acceptable for prototype fabrication**; should-fix LR-32 (trip / fault meanders) and
LR-33 (ADC front end and sense-line routing), notes LR-34.

Of the previous review's findings: LR-01 (power board absent), LR-02 (39 open connections), LR-03 (J8 on
F.Cu), LR-05/06/07 (TPS54302 loop, exposed-pad vias, supply widths), LR-09 (J4/J5 position), LR-12
(verifier hashes_valid), LR-19 (report hash) are resolved; LR-04 (ADC capacitors) and LR-14 (ISENSE pair)
are partly addressed and continue as LR-33; LR-08 (spec correctness) is resolved for the barrier parts
but the spec's HV_VIN / SENSE_ISO patterns both match VIN_DIV_T* (LR-30); LR-10 (EFUSE_RTN) is unchanged
at schematic level; LR-11, LR-13, LR-15, LR-16, LR-17, LR-18 continue as notes (LR-34, LR-35, LR-27).

Required before the power board can be called finished: a rule-aware zone fill saved into the board
(generator-side through the DRC engine, or `kicad-cli pcb drc --refill-zones --save-board`), all-layer HV
keep-out rule areas around the four HS1 holes, a widened input PGND return (move J2 out of the J1/J6
pocket or add a B.Cu / F.Cu PGND bridge to the plane), then DRC through `run_check`, netlist check,
metrics on the refilled copper and a fresh export.
