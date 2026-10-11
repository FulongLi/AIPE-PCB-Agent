**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# Power board floorplan candidates

Three deterministic floorplans of the 400 V -> 200 V / 5 kW SiC buck power board were placed with `automation/kicad_tools/generate_sic_power_floorplan.py` (all 237 parts, zones filled, no routing), measured with the layout checker (`automation/verification/check_sic_layout.py`, spec `verification/engineering_checks/layout_spec_power.json`), the generator's floorplan checks and a kicad-cli DRC without schematic parity (DRC-lite, scratch only), and compared on the measurable criteria below. Pad-centre sums are pre-routing proxies, not routed lengths. Scores are weighted normalised sums (0 = best on every criterion, lower is better); the weights are an agent choice recorded in `COMPARISON_WEIGHTS` and need human review.

Scratch builds: `C:\Users\ZHONGN~1\AppData\Local\Temp\claude\d--Cursor-Workspace-AIPE-PCB-Agent\d8f6e3bc-7921-4cf9-b1d3-9695bd7c8da8\scratchpad\power_board\floorplan` (one directory per candidate with the board, the project copies, `layout_metrics_power_<id>.json/.md`, `result.json` and `drc/<stamp>-drc-lite/run.json`).

## Candidate A: Power board floorplan A - heatsink top centre(-left), device row facing the barrier, inductor right, films left

Sink centred at x = 97.5 (courtyard 46.7-148.3) with its intake and fan allowance on the board (x < 46.7) and the exhaust toward +x; three films in a left-hand column beside the intake, the fourth above the inductor; inductor at (203.4, 65) 20 mm from the sink; sensing island at the right end of the barrier line under the inductor; output terminals at the right edge; input terminals in the band above the sink.

- Follows the brief literally (films left, inductor right): the left film column sits in the intake corridor (37-45 mm tall parts in front of the fan) and 16.7 mm from the sink; the fourth film lies 0.4 mm from the inductor keep-out circle.
- The VIN bus is short (films beside the HF tier) but the SW run to the inductor is the longest of the three candidates.
- Device row: TO-247-4 pads 7.5 mm below the heatsink courtyard so that the pad copper keeps the 5 mm HV keep-out to the PE-bonded sink (baseline lead row 3-5 mm from the face: formed leads / spacer are a mechanical review item).
- Barrier parts straddle the barrier line with HV pins toward the HV area; U1/U3 get board-level Edge.Cuts slots (official SOIC footprint has none), the five custom AIPE footprints carry their 1.2 mm NPTH slots (e >= 3 mm).
- Mezzanine socket J7 at 270 deg (pins increasing toward -x) so that the control board (J8 at (28, 76) rotated 90 deg) mates when mounted rotated 180 deg about z; the two in-strip M3 holes follow the 112 mm pattern, the other two are spares at the bottom edge (review item).

Placed 237 parts; generator issues: 35 placement (region growth within the band), 7 floorplan rule findings:
  - 13 HV pads closer than 5.0 mm to the HS1 courtyard (first: {'pad': 'R22.1', 'net': 'G_H', 'distance_mm': 4.255})
  - C11: 16.2 mm from the heatsink courtyard (< 20.0 mm, CR-23)
  - C12: 16.2 mm from the heatsink courtyard (< 20.0 mm, CR-23)
  - C13: 15.2 mm from the heatsink courtyard (< 20.0 mm, CR-23)
  - C14: 0.4 mm from the inductor keep-out circle (< 15.0 mm, CR-23)
  - 3 parts taller than 15.0 mm inside the heatsink corridors: C11(intake), C12(intake), C13(intake)
  - Q2 pin 2 (PGND): no HF capacitor pad within 5.0 mm
DRC-lite: 20 violations {'clearance': 12, 'isolated_copper': 2, 'items_not_allowed': 2, 'silk_edge_clearance': 4}, 499 unconnected items (unrouted by construction); manifest `C:\Users\Zhongnan Qian\AppData\Local\Temp\claude\d--Cursor-Workspace-AIPE-PCB-Agent\d8f6e3bc-7921-4cf9-b1d3-9695bd7c8da8\scratchpad\power_board\floorplan\A\drc\20261010T131552Z-drc-lite\run.json`.

## Candidate B: Power board floorplan B - heatsink top-left, inductor and films in a row to the right

Fischer LAM 5 D K sink flush with the left board edge (fan and intake off-board, exhaust along +x), device row at y = 129 on the sink's barrier-side face with Q1 at x = 62 and Q2 at x = 90, HF tier around the pins, HS/LS driver islands on B.Cu under the row with U2/U1 and U3/U4 on the barrier line; inductor in the exhaust stream at (158, 92) 20.4 mm from the sink; input film C11 above the inductor, C12/C13/C14 in a right-hand column 16 mm from the inductor; output terminals under the film column; TMCS1133 under the inductor's VOUT_L lead, AMC1311s and the sensing bias module at the right end of the barrier line; input terminals, relay terminals and PTC in the 20 mm band above the sink; mezzanine socket at (176, 163) with the control board overhanging the bottom edge.

- Shortest commutation-to-driver geometry of the three: drivers 11.4 mm from the gate pads, HF caps 4.5-14.8 mm from the pins.
- All four films, the inductor and the sink keep the CR-23 spacings (films >= 20 mm from the sink, >= 15 mm from the inductor; inductor 20.4 mm from the sink) on the 240 x 180 mm outline; the price is a long VIN bus (input films at the top right, reaching the HF tier on In2.Cu under the sink) and a VOUT return along the bottom band.
- Intake corridor and fan allowance lie off the board edge (architecture.md section 9 option); nothing tall sits in the exhaust corridor except the inductor.
- Device row: TO-247-4 pads 7.5 mm below the heatsink courtyard so that the pad copper keeps the 5 mm HV keep-out to the PE-bonded sink (baseline lead row 3-5 mm from the face: formed leads / spacer are a mechanical review item).
- Barrier parts straddle the barrier line with HV pins toward the HV area; U1/U3 get board-level Edge.Cuts slots (official SOIC footprint has none), the five custom AIPE footprints carry their 1.2 mm NPTH slots (e >= 3 mm).
- Mezzanine socket J7 at 270 deg (pins increasing toward -x) so that the control board (J8 at (28, 76) rotated 90 deg) mates when mounted rotated 180 deg about z; the two in-strip M3 holes follow the 112 mm pattern, the other two are spares at the bottom edge (review item).

Placed 237 parts; generator issues: 13 placement (region growth within the band), 1 floorplan rule findings:
  - Q2 pin 2 (PGND): no HF capacitor pad within 5.0 mm
DRC-lite: 16 violations {'clearance': 12, 'silk_edge_clearance': 4}, 499 unconnected items (unrouted by construction); manifest `C:\Users\Zhongnan Qian\AppData\Local\Temp\claude\d--Cursor-Workspace-AIPE-PCB-Agent\d8f6e3bc-7921-4cf9-b1d3-9695bd7c8da8\scratchpad\power_board\floorplan\B\drc\20261010T131628Z-drc-lite\run.json`.

## Candidate C: Power board floorplan C - tighter 220 x 170 mm attempt (heatsink top-left, inductor right, films at the right edge)

Same block order as B on a 220 x 170 mm outline: sink flush left, HV area 130 mm deep, device row at y = 119, barrier line at y = 135; inductor 15 mm from the sink; input film C11 above the inductor, C13/C14/C12 stacked at the right edge with 0.5 mm courtyard gaps; terminals and PTC stacked in the exhaust corridor beside the sink (no band above the sink); output terminals below the inductor next to the sensing island.

- Tests the baseline stretch target: 220 mm width = sink 101.6 + inductor gap 15 + inductor 70 + film column 29.1 leaves 4.3 mm, so the inductor gap drops to 15 mm (CR-23: 20) and the right film column touches the inductor keep-out (2.3 mm, CR-23: 15).
- The HV terminals and the PTC stand in the exhaust corridor because the band above the sink is only 10 mm deep.
- Device row: TO-247-4 pads 7.5 mm below the heatsink courtyard so that the pad copper keeps the 5 mm HV keep-out to the PE-bonded sink (baseline lead row 3-5 mm from the face: formed leads / spacer are a mechanical review item).
- Barrier parts straddle the barrier line with HV pins toward the HV area; U1/U3 get board-level Edge.Cuts slots (official SOIC footprint has none), the five custom AIPE footprints carry their 1.2 mm NPTH slots (e >= 3 mm).
- Mezzanine socket J7 at 270 deg (pins increasing toward -x) so that the control board (J8 at (28, 76) rotated 90 deg) mates when mounted rotated 180 deg about z; the two in-strip M3 holes follow the 112 mm pattern, the other two are spares at the bottom edge (review item).

**Placement failed:** RuntimeError: no placement space for C19 (Capacitor_THT:C_Disc_D12.5mm_W5.0mm_P10.00mm) in region pe_group [[4.5, 104.5, 48.5, 129.5], [167.0, 0.4, 195.5, 37.5]] side F; 22 items already inside: ['C11', 'C13', 'C18', 'C3', 'C4', 'C5', 'C7', 'D3', 'H1', 'HS1', 'L1', 'L1#NPTH', 'TEXT:PE', 'U2']

## Criteria

| Criterion | Candidate A | Candidate B | Better |
|---|---|---|---|
| Board area (mm2) | 43200.0 | 43200.0 | lower |
| HV-area utilisation (HV-side + barrier courtyards incl. sink / HV area) | 0.752 | 0.752 | info |
| HF capacitor row 1: nearest same-net pad to Q1 drain / Q2 source, worse of the two (mm, <= 5) | 8.0 | 8.0 | lower |
| HF capacitor pads within 15 mm of the pin (same net), fewer of Q1 drain / Q2 source (count) | 2 | 2 | higher |
| Driver output pad to gate pad, worse of U1/Q1 and U3/Q2 (mm, <= 15) | 11.378 | 11.378 | lower |
| Power path J1 -> RT1 -> J6 -> C11 -> Q1 -> SW -> L1 -> U10 -> C13 -> J3 (pad-centre sum, mm) | 889.1 | 639.2 | lower |
| Planned layer transitions on the power path (count) | 3 | 3 | lower |
| SW copper area, all layers (mm2, filled zones + pads) | 3922.9 | 3087.8 | lower |
| HV/DRV/DESAT/SENSE_ISO to CTRL_SELV minimum copper distance, any layer (mm, >= 9) | 12.0 | 12.0 | higher |
| Smallest barrier-part land gap g (mm) | 7.25 | 7.25 | info |
| Barrier parts with a slot (footprint NPTH or board Edge.Cuts) | 8/8 | 8/8 | info |
| HV copper to the heatsink courtyard, outer layers (mm, >= 5) | 5.075 | 5.075 | higher |
| Film capacitor courtyard to heatsink courtyard, minimum (mm, >= 20) | 15.16 | 33.91 | higher |
| Inductor keep-out circle to heatsink courtyard (mm, >= 20) | 20.055 | 20.355 | higher |
| Film capacitor courtyard to inductor keep-out circle, minimum (mm, >= 15) | 0.405 | 15.334 | higher |
| Parts taller than 15 mm inside the intake/exhaust corridors (count, inductor exempt) | 3 | 0 | lower |
| Mezzanine socket J7 pin 1 (x, y mm) | [185.0, 163.0] | [176.0, 163.0] | info |
| DRC-lite violations (kicad-cli, no parity, severity-all; unconnected items excluded) | 20 | 16 | lower |
| DRC-lite violations by type | {'clearance': 12, 'isolated_copper': 2, 'items_not_allowed': 2, 'silk_edge_clearance': 4} | {'clearance': 12, 'silk_edge_clearance': 4} | info |
| Placement + floorplan rule issues recorded by the generator (count) | 42 | 14 | lower |

## Scores

| Criterion | Weight | A | B |
|---|---|---|---|
| power_path_mm | 2.0 | 889.1 | 639.2 |
| power_path_layer_transitions | 1.0 | 3 | 3 |
| hf_cap_row1_max_mm | 2.0 | 8.0 | 8.0 |
| hf_pads_within_row2_min | 1.0 | 2 | 2 |
| driver_to_gate_max_mm | 2.0 | 11.378 | 11.378 |
| sw_copper_mm2 | 1.0 | 3922.9 | 3087.8 |
| hv_to_selv_min_mm | 1.5 | 12.0 | 12.0 |
| heatsink_hv_min_mm | 1.0 | 5.075 | 5.075 |
| film_to_heatsink_min_mm | 1.5 | 15.16 | 33.91 |
| inductor_to_heatsink_mm | 1.5 | 20.055 | 20.355 |
| film_to_inductor_min_mm | 1.0 | 0.405 | 15.334 |
| tall_parts_in_corridors | 1.5 | 3 | 0 |
| drc_lite_findings | 2.0 | 20 | 16 |
| board_area_mm2 | 0.5 | 43200.0 | 43200.0 |
| placement_issues | 1.0 | 42 | 14 |
| **weighted score (lower is better)** | | 11.5 | 0.0 |

**Selected: candidate B.**

## Selection rationale

- Candidate B has the lowest weighted score (0.0).
- Board area (mm2): A = 43200.0, B = 43200.0 (best: A, B).
- HF capacitor row 1: nearest same-net pad to Q1 drain / Q2 source, worse of the two (mm, <= 5): A = 8.0, B = 8.0 (best: A, B).
- HF capacitor pads within 15 mm of the pin (same net), fewer of Q1 drain / Q2 source (count): A = 2, B = 2 (best: A, B).
- Driver output pad to gate pad, worse of U1/Q1 and U3/Q2 (mm, <= 15): A = 11.378, B = 11.378 (best: A, B).
- Power path J1 -> RT1 -> J6 -> C11 -> Q1 -> SW -> L1 -> U10 -> C13 -> J3 (pad-centre sum, mm): A = 889.1, B = 639.2 (best: B).
- Planned layer transitions on the power path (count): A = 3, B = 3 (best: A, B).
- SW copper area, all layers (mm2, filled zones + pads): A = 3922.9, B = 3087.8 (best: B).
- HV/DRV/DESAT/SENSE_ISO to CTRL_SELV minimum copper distance, any layer (mm, >= 9): A = 12.0, B = 12.0 (best: A, B).
- HV copper to the heatsink courtyard, outer layers (mm, >= 5): A = 5.075, B = 5.075 (best: A, B).
- Film capacitor courtyard to heatsink courtyard, minimum (mm, >= 20): A = 15.16, B = 33.91 (best: B).
- Inductor keep-out circle to heatsink courtyard (mm, >= 20): A = 20.055, B = 20.355 (best: B).
- Film capacitor courtyard to inductor keep-out circle, minimum (mm, >= 15): A = 0.405, B = 15.334 (best: B).
- Parts taller than 15 mm inside the intake/exhaust corridors (count, inductor exempt): A = 3, B = 0 (best: B).
- DRC-lite violations (kicad-cli, no parity, severity-all; unconnected items excluded): A = 20, B = 16 (best: B).
- Placement + floorplan rule issues recorded by the generator (count): A = 42, B = 14 (best: B).
- Candidate C could not be placed: RuntimeError: no placement space for C19 (Capacitor_THT:C_Disc_D12.5mm_W5.0mm_P10.00mm) in region pe_group [[4.5, 104.5, 48.5, 129.5], [167.0, 0.4, 195.5, 37.5]] side F; 22 items already inside: ['C11', 'C13', 'C18', 'C3', 'C4', 'C5', 'C7', 'D3', 'H1', 'HS1', 'L1', 'L1#NPTH', 'TEXT:PE', 'U2']

## Selected candidate written to the repository

Board `C:\Users\ZHONGN~1\AppData\Local\Temp\claude\d--Cursor-Workspace-AIPE-PCB-Agent\d8f6e3bc-7921-4cf9-b1d3-9695bd7c8da8\scratchpad\power_board\floorplan\selected\AIPE_SiC_Buck_Power.kicad_pcb` (placed, zones filled, unrouted): 237 footprints, 23 zones; `design/placement_power.json`, `design/routing_plan_power.json` (skeleton) and `verification/routing_progress_power.json` (stage floorplan-selected) were written.

Verification DRC (run_check, schematic parity, severity-all): status **failed**, findings 515 (violations 16 {'clearance': 12, 'silk_edge_clearance': 4}, unconnected 499 - unrouted board, parity 0), manifest `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\verification\drc\20261010T131707Z-drc-be0bc838\run.json`.

## Open issues for the orchestrator

- DRU / net classes: the unconnected pins of U1/U3 (APWM, pad 16) and U10 (NC, pad 5) carry "unconnected-..." nets in the Default class; the 9 mm HV-to-SELV rule includes Default but the pin-field exceptions name only CTRL_SELV, so 12 clearance findings (7.25-8.64 mm) sit inside those land patterns on every build. Fix belongs to the project owner (.kicad_pro pattern or .kicad_dru exception), not the layout.
- Library: the AMC1311 DWV slot (10.4 mm) extends 2.995 mm beyond the pad rows, 5 um short of the 3.0 mm baseline (path 10.9 mm >= 9.0 mm); the official SOIC-16W silkscreen of U1/U3 crosses their board-level slots (4 silk_edge_clearance warnings; trimming the board copy would raise lib_footprint_mismatch instead).
- Mechanical: TO-247-4 lead row 7.5 mm from the sink face (5 mm HV-copper keep-out from the courtyard), baseline 3-5 mm - formed leads or a spacer; the LS source pin (second pin) cannot have a same-net HF capacitor pad within 5 mm (nearest 8.0 mm), the HS drain pin has 4.66 mm.
- Mezzanine: J7 pin 1 at (176, 163) with pins toward -x assumes the control board mounted rotated 180 deg about z (J8 at (28, 76) rotated 90 deg); the two in-strip M3 holes (88, 163) / (200, 163) follow the 112 mm pattern, the other two M3 holes are spares - to be cross-checked with the control-board drawing.
- Metrics: PE-PCB-007 reports a 0 mm section separation because the barrier packages belong to both bounding boxes (artefact of the bounding-box proxy); PE-PCB-006 via counts are zero until routing.
- Candidate C (220 x 170 mm) could not place the PE group (two Y-capacitor discs and three 2512 links need 5 mm to every HV part) after sink, inductor, films and terminals; the stretch outline is confirmed infeasible with the baseline envelopes and spacings.
- Process: a parallel routing-stage generator owns automation/kicad_tools/generate_sic_power_board.py and will write design/placement_power.json, design/routing_plan_power.json and verification/routing_progress_power.json again when it routes; this floorplan stage keeps its own module generate_sic_power_floorplan.py and candidate/comparison files.

## Limitations

- No tracks or vias exist: every pad pair is an unconnected item; the DRC violation counts are placement/zone findings only.
- Zone fills are pcbnew fills of the candidate pours (refilled with the project rules); the routing agent redefines the pours around the routed copper.
- Thermal spacings are courtyard distances, not CFD; the corridor rule exempts the inductor by design (CR-14).
- The checker dispositions are measurements against spec proxies, not engineering acceptance (human review required).

## Amendment 2026-10-11 (after the structural DRC fixes)

The comparison above was scored with the KiCad library SOIC-16W footprint for U1/U3 and the 10.4 mm AMC1311 slot. The
structural DRC fixes of 2026-10-11 replaced them at the source (`AIPE:UCC21710_DW0016A_Slot`, 1.2 x 16.6 mm NPTH slot;
AMC1311 slot 10.8 mm). The slotted UCC21710 footprint occupies both board sides with a 17.9 x 12.8 mm courtyard that reaches
y = 138.6 mm, which overlapped C6 and C8 at their recorded y = 137.0 mm in candidate B; both capacitors were moved to the
y = 135.5 mm row (note in `design/floorplan_candidates/power_B.json`). With this change candidate B places again (237 footprints,
8 barrier parts, no board-level slot added because every barrier footprint now carries its own). The scores in this file were not
recomputed: the live power board is placed from `design/placement_power.json`, which had already moved far from this candidate
during routing convergence (`verification/routing_iterations_power.md`).
