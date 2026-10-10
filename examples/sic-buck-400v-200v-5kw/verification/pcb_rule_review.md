**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# Independent PCB layout review (task section 17) - V2 power and control boards

Reviewer: independent layout-review agent (did not create the boards). Date 2026-10-10.
Scope: the two V2 boards of the 400 V -> 200 V / 5 kW / 50 kHz SiC synchronous buck against
`design/design_decisions.json` (schema 4), `design/pcb_stackup.md`, `design/architecture.md`,
`docs/pcb-design-rules.md` (PE-PCB-001..008), SKILL-002 and the knowledge rules KR-PCB-001..006,
KR-ISO-001..004, KR-CAP-003, KR-TH-002. Every number below was measured by this review with pcbnew
10.0.7 (footprint sides and positions, pad nets, zone fills per layer, track widths, via counts) or
read from the named manifests; nothing was taken from the generating agents' own claims without
re-measurement. No board, schematic, library, rule file or model was edited.

Machine-readable findings: `layout_review_findings.json` (same directory). Dispositions used:
**pass**, **fail**, **unverified** (no artefact to measure), **human review** (engineering judgement
or outside the layout's reach).

## 0 Headline

| Item | State |
|---|---|
| Power board `kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` | **does not exist** - the layout stage produced no board (`verification/netlist_check_power.json`: `board_missing`; no DRC, metrics, exports or renders). Every power-board rule below is **unverified**. |
| Control board `kicad/control_board/AIPE_SiC_Buck_Control.kicad_pcb` (sha256 `119d37df...b04ecd`) | routed but **unfinished**: native DRC `verification/drc/20261010T104013Z-drc-7a5fd84b/` reports 0 violations, **39 unconnected items on 20 nets**, 0 schematic-parity findings, exit 5. Netlist model = schematic = board (667 pads). Exports hash-valid. |
| Blockers | power layout absent (LR-01); 39 open connections including XRS_N, TDI, FLT_H_N/FLT_L_N, RDY_H/L, RELAY_ON, BIAS_EN (LR-02); mezzanine header J8 on the **F.Cu** side although the board must stack 11 mm above the power-board SELV strip (LR-03). |

## 1 Evidence validity (DRC manifests, exports, netlist checks)

| Check | Evidence | Finding | Disposition |
|---|---|---|---|
| Latest control DRC manifest hashes | `verification/drc/20261010T104013Z-drc-7a5fd84b/run.json`: `source_sha256` recomputed = `119d37df1b737fd727e44429991f7ed9537c5c9b3a292292e13f046657b04ecd` (matches the board on disk and the export manifest input hash); 42/42 `dependency_sha256` entries (9 schematic sheets, .kicad_pro, .kicad_dru, fp-lib-table, sym-lib-table, 28 footprints, AIPE.kicad_sym) recomputed and equal; command carries `--schematic-parity --severity-all --exit-code-violations --refill-zones`; `drc.json` counts 0 / 39 / 0 agree with `finding_count` 39; tool and wrapper exit 5. | Chain is intact. The run record carries no hash of its own `drc.json`, and `drc.json` names the source only by basename - the report could be replaced without the record noticing (LR-19). | pass (chain) / note |
| Older control DRC manifests (8) | `20261010T095008Z` 193 violations + 63 unconnected ... `20261010T103701Z` 1 + 39; each `source_sha256` differs from the current board (earlier iterations), dependencies 42/42 valid. | Iteration history is honest; only the latest run describes the delivered board. | pass |
| Power DRC | none in `verification/drc/` | no board | unverified |
| ERC | `verification/erc/20261010T070357Z-erc-a2f64724` (power, 0 findings, source hash matches) and `...071810Z-erc-b207ac59` (control, 0 findings, matches) | schematics clean | pass |
| Control export manifest | `manufacturing/control_board/export-manifest.json`: 11/11 commands exit 0; 35/35 artefact sha256 + byte counts recomputed equal; 43/43 input hashes equal; review PNG/PDF copies in `review/` byte-identical to the manufacturing copies; drill report 642 x 0.3 mm vias, 76 x 1.0 mm, 2 x 0.8, 2 x 1.3, 4 x 3.2 NPTH. | `logs/step.log`: 3D models missing for U1, U3, Y1 (library bundle, LR-17). The gerbers describe a board with 39 open connections (README says so). | pass (integrity) / human review (content) |
| Netlist checks | `netlist_check_control.json`: model = schematic = board, 667 pads, 207 components, 0 mismatches. `netlist_check_power.json`: schematic = model (648 pads, 237 components), board missing. | - | pass (control) / unverified (power) |
| `verification-summary.json` | status `failed`; `control.drc.hashes_valid: false` | The `false` is a verifier defect: `verify_sic_buck.py` line 62 marks hashes invalid whenever any problem string starts with "control drc", which the "did not pass with zero findings" message does; this review confirmed the hashes are valid (LR-12). | note |
| Repository evidence test | `tests/test_generate_sic_control_board.py::test_recorded_drc_manifest_matches_the_board_and_the_recorded_state` run here: OK (it checks that the recorded state says `routed_with_unresolved_connections` and `failed`). | consistent with the manifest | pass |

## 2 Power board rules - all unverified (no `.kicad_pcb`)

The baseline geometry the missing board must satisfy is restated as the acceptance target so the
next run can be reviewed against it. The only power-board artefacts that exist are the schematics,
ERC, the `.kicad_pro` net classes, the `.kicad_dru` (3.0 mm HV outer / 1.0 mm inner, 9.0 mm HV-to-SELV
all layers, 5.0 mm PE, 0.3 mm same island, 1.0 mm HV edge, 36 pin-field exceptions) and the layout
spec `verification/engineering_checks/layout_spec_power.json` - which does **not** match the
schematic (LR-08).

| Rule | Requirement (baseline) | Evidence available | Finding | Disposition |
|---|---|---|---|---|
| KR-PCB-005 / PE-PCB-001 gate-driver placement | U1 (HS) / U3 (LS) UCC21710 with R_G, DESAT, decoupling and bias modules on B.Cu directly under the device row, within 15 mm of the TO-247-4 leads; V_GS probe loop at R_G (CR-11) | none | - | unverified |
| KR-PCB-001 gate / Kelvin pours | gate nets HS_OUTH/HS_OUTL -> G_H (LS: -> G_L) as wide B.Cu tracks/pours over KS_H / KS_L pours on In2.Cu (0.20 mm prepreg), Kelvin layer facing other copper | none | - | unverified |
| KR-PCB-002 decoupling inside the gate loop | 2 x 4.7 uF + 100 nF (VDD-COM) and 4.7 uF + 100 nF (COM-VEE) between driver pins and the gate/Kelvin connection, <= 15 mm | none | - | unverified |
| KR-PCB-003 Kelvin never tied to power source | KS_H distinct from SW, KS_L distinct from PGND on every layer (schematic keeps them distinct: Q1 pads 1 VIN / 2 SW / 3 KS_H / 4 G_H, Q2 1 SW / 2 PGND / 3 KS_L / 4 G_L) | schematic only | netlist-level separation holds; copper not checkable | unverified |
| KR-PCB-004 / KR-CAP-003 / PE-PCB-002 / PE-PCB-003 commutation loop | C1-C10 (0.47 uF / 630 V 2220) in two rows <= 5 mm and <= 15 mm beside the TO-247-4 legs, both sides of the device row; VIN+ (F.Cu) over PGND (In1.Cu) as overlapping pours through 0.20 mm prepreg; <= 20 nH board target; Q1/Q2 vertical at 28 mm pitch, leads trimmed | none | no loop overlay can be drawn; the required overlay is: C1-C10 VIN pad -> F.Cu VIN pour -> Q1 drain (pad 1) -> Q1 source (pad 2, SW) -> Q2 drain (pad 1) -> Q2 source (pad 2, PGND) -> via array to In1.Cu PGND pour -> back under the F.Cu VIN pour to the C1-C10 PGND pads | unverified |
| PE-PCB-005 inductor and SW copper | L1 (75 mm keep-out circle, 48 mm tall, 4 x 4.3 mm NPTH on 60 x 60) in the fan stream >= 20 mm from the sink, SW lead toward the half bridge, VOUT_L toward U10; SW copper limited to the half-bridge / L1 path | none | - | unverified |
| KR-TH-002 / SKILL-006 thermal | HS1 LAM 5 D K envelope 100 x 100 x 50 reserved with corridors (parts <= 15 mm), HV copper >= 5 mm from the sink courtyard on outer layers, PE stud H1 beside it, films C11/C12 and C13/C14 >= 20 mm from the sink and >= 15 mm from L1, Sil-Pad TSP A2000 under both devices | none | - | unverified |
| KR-PCB-006 / PE-PCB-006 copper and vias | pours >= 12 mm (outer, 70 um) / >= 22 mm (inner) for 25 A, >= 24 x 0.3 mm or 21 x 0.5 mm vias per layer transition, VIN+/SW/VOUT+ paralleled on F/In2/B | none | IPC-2221 check of the actual pours impossible | unverified |
| PE-PCB-004 / PE-PCB-007 / PE-PCB-008 sensing and grounding | TMCS1133 (U10) in the L1 -> VOUT path with fused IN+/IN- bars; AMC1311 ladders (U6/U7) short to the bus; OPA2320 (U8) / REF3125 (U9) on the SELV strip; GND_CTRL pour under the SELV strip on In1.Cu; nothing SELV in the HV area | none | - | unverified |
| KR-ISO-001 / KR-ISO-002 isolation | 10 mm ISO_BARRIER copper-free on all layers; 9.0 mm HV/DRV/DESAT/SENSE_ISO to CTRL_SELV on all layers; 5.0 mm to PE; 3.0 / 1.0 mm HV functional; 3.0 / 1.0 mm HS-island to LS-island; all eight barrier parts (U1, U3 UCC21710; U2, U4, U5 UCC14141; U6, U7 AMC1311; U10 TMCS1133) on one straight line, SELV pins toward the strip | `.kicad_dru` and net classes exist and encode these values | rules exist, geometry absent | unverified |
| KR-ISO-004 slots | 1.2 mm NPTH slot under each barrier body extending >= 3 mm beyond the outermost pads so that 2 x sqrt((g/2)^2 + e^2) >= 9.0 mm | none (the footprints `UCC14141_DWN0036A_Slot`, `AMC1311_DWV0008A_Slot`, `TMCS1133_DVG0010A_HV_Slot` carry "Slot" in their names; the UCC21710 uses the plain library SOIC-16W, so its slot must come from Edge.Cuts) | - | unverified |
| Area / compactness | <= 240 x 180 mm (43,200 mm2), HV area ~33,600 mm2, assembly height 67 mm (72 mm envelope) | none | - | unverified |
| Routing complexity | 4 x 70 um justified by the commutation (F/In1), gate/Kelvin (B/In2) and bus paralleling (F/In2/B) | none | - | unverified |
| Layout spec readiness (checker input) | spec refs/pads/nets must equal the placed board | `layout_spec_power.json` (unmodified since 14:48) vs `design/circuit_power.json`: barrier parts list U2 as the LS driver (schematic: UCC14141 HS bias), U3 as HS bias (schematic: UCC21710 LS driver), U8 as TMCS1133 (schematic: OPA2320; the TMCS1133 is U10 and is missing from the list); `gate_loops` Q2 `driver_ref` U2 (should be U3); MOSFET pads drain 2 / source 3 / gate 1 / kelvin 4 (schematic: 1 drain, 2 source, 3 Kelvin, 4 gate); decoupling nets COM_H/COM_L (schematic: KS_H/KS_L); kelvin pairs VIN_DIV_P/N (schematic: single VIN_DIV); CTRL_SELV patterns miss 12V_BIAS_*, GNDP_*, PWM_*_F, RESET_N_F, BIAS_EN_F, REF2V5_PB, K1_LOW, RLY_G, VIN/VOUT_AMP_*, VIN/VOUT_OUT*; height patterns `C2[0-9]` 45 mm (the 45 mm films are C13/C14) and L1 40 mm (baseline 48 mm) | **fail** (spec must be corrected before the power metrics can mean anything; LR-08) | fail |

## 3 Control board rules (measured)

Board: 120.00 x 80.00 mm, 4 x 35 um, 1.6 mm (stackup text F.Cu / 0.20 prepreg / In1.Cu / 1.06 core
/ In2.Cu / 0.20 prepreg / B.Cu); 207 footprints (192 F.Cu, 15 B.Cu - all fifteen are the 0603 1V9
bypass capacitors), 772 pads, 4151 tracks, 642 vias (all 0.6 / 0.3 mm through), 16 zones (In1.Cu
GND_CTRL; In2.Cu 12V_PROT 1453.7 mm2, 5V 608.5 mm2, 1V9 754.2 mm2, 3V3 background 5401.4 mm2 and
11 corridor patches of 1.9-7.0 mm2), 0 rule areas, 0 tracks on inner layers, 199 nets, design-rule
minimums 0.2 mm clearance / 0.2 mm track / 0.3 mm drill / 0.5 mm copper-to-edge. Track widths used:
0.2 mm (3629 segments), 0.25 (102), 0.3 (283), 0.4 (123), 0.6 (14). Minimum copper-to-edge
measured 2.67 mm (track), 3.03 mm (pad), 3.23 mm (via).

| Rule | Requirement | Evidence (measured) | Finding | Disposition |
|---|---|---|---|---|
| Routing completeness (prerequisite for every electrical rule) | all connections routed | DRC: 39 unconnected items on XRS_N (6: U4.1, TP13, R24, D2, U8.13, U5.80, U3.22), FLT_H_N (3), FLT_L_N (3), OTP_N (3), PG_BIAS_S_N (3), RDY_H (3), RDY_L (3), ADC_TEMP_HS (2), OVP_IN_N (2), and 1 each on BIAS_EN, BOOT87, G1_N, OVP_N, OVP_OUT_N, PG_BIAS_H_OK, PG_BIAS_L_OK, PG_BIAS_S_OK, RELAY_ON, SPARE_D2, TDI. `routing_progress_control.json`: all 39 are router "route" failures with occupancy codes, concentrated between the DSP's PWM/fault pin side (pins 10-26 at y = 45.7 mm) and the fault-combiner group U8/U10/U11 (y = 56-65 mm). | system reset, JTAG TDI, both driver fault inputs, both ready inputs, relay and bias enables are open: the board cannot function (LR-02) | fail |
| Mechanical / stacking (interconnect, architecture `control_board.mounting`) | header TSW-125-07-G-D mates downward into the power-board socket; board 11.05 mm above the SELV strip; stackup table: "B.Cu: signals, JTAG, mezzanine header" | J8 side **F.Cu** at (28.0, 76.0), rotation 90, pins at y 73.46 / 76.0, x 28.0-88.96, pin 1 left (silkscreen agrees); 3D render shows the 50 pins protruding from the component side. Tallest F.Cu parts J1 12.0 mm, C9 11.2 mm, C3 10.5 mm, J8 11.05 mm. H1-H4 at (4,4), (116,4), (4,76), (116,76). | As built the header points away from the power board; mating would require inverting the control board, which puts J1 (12.0 mm) and C9 (11.2 mm) against the 11.05 mm stack height and hides every connector and LED (LR-03). With J8 4 mm from the inner edge and the socket inside the 30 mm SELV strip the inner edge lies <= 34 mm from the power-board edge, i.e. an overhang >= 46 mm (documents: "about 40 mm"); H3/H4 are co-linear with the J8 bottom row (LR-18). | fail (side) / human review (stack geometry) |
| PE-PCB-008 DSP decoupling | 26 per-pin 100 nF within "a few mm" (agent proxy 5.0 mm) | pin-to-capacitor pad: 1V9 pins 3.90-5.03 mm (15 pins, capacitors on B.Cu under the body via the inward escape vias), 3V3 pins 5.05 mm (10 pins, F.Cu ring at 18.5 mm radius) and 5.85 mm (pin 143 -> C37); mean 4.54 mm; every capacitor GND pad has a GND via within 1.10 mm and every rail pad a rail via within 1.99 mm; three model `near_dsp_pin` capacitors are not the nearest to their pin (C22 -> 31: 4.10 mm, C36 -> 139: 5.24 mm, C38 -> 146: 4.50 mm). | compliant with the baseline wording, 0.85 mm over the agent proxy; the 3V3 ring could sit at ~17.3 mm (far escape row 15.9 + via + clearance + pad) for ~3.7 mm (LR-13) | human review |
| PE-PCB-008 other ICs | decoupling at the supply pins | nearest capacitor pad: U6 2.5, U8 2.6, U9 2.6, U11 2.6, U13 2.5, U7 4.7, U15 4.3, U12 4.8, U14 3.9, Y1 5.0, U4 5.9, U2 6.8 (C3 100 uF), U3 7.3 (5V in) / 6.5 (3V3 out) / 4.9 (1V9 out), U1 3.7 (in) / 8.8 (out), U10 8.7 mm (C18, a DSP capacitor - U10 has no own capacitor within 7.6 mm) | logic ICs fine; U10 (SN74LV21A run-permit) relies on a DSP bypass 7.6-8.7 mm away; U2/U1/U3 see LR-05/LR-06/LR-07 | human review |
| PE-PCB-005 analogue separation (control-board reading) | ADC front ends and comparators away from the PWM/logic group; "1 k + 1 nF at every ADC pin" | analogue section (45 parts touching ADC_/ADCREF/VIN_SENSE/VOUT_SENSE/ISENSE/TEMP_/REF/comparator-reference nets, U5 and J8 excluded) bbox x 87.1-114.8 mm; supply section (34 parts) bbox x 3.5-50.9 mm -> 36.3 mm apart; PWM gating parts (U6, R38-R41, TP7, TP8) bbox 36.0-66.5 x 52.2-69.0 -> 20.6 mm from the analogue bbox; minimum analogue-track to PWM-track distance 12.6 mm, no analogue track within 0.6 mm of a PWM track; minimum analogue track to 5V_SW / 5V_BST copper 53.4 mm; no analogue segment in the supply corner. **But** the 1 nF ADC filter capacitors C68-C75 are 10.5-17.3 mm from their DSP pins (ADC_VIN 10.5, ADC_ISENSE 11.3, ADC_TEMP_HS 12.2, ADC_VOUT 12.3, ADC_I12V 13.0, ADC_TEMP_CTRL 13.1, ADC_V12V 13.3, ADC_ISENSE_REF 17.3) with the 1 k series resistors 21.6-36.0 mm away; ADCREFP/ADCREFM capacitors 7.9 / 7.4 mm, ADCRESEXT resistor 12.8 mm. | sections are separated; the per-pin RC filters are not "at the pin" (LR-04) | pass (separation) / fail (filter placement) |
| PE-PCB-007 grounding | In1.Cu solid GND_CTRL, no splits under ADC or PWM tracks (proxy >= 8000 mm2) | In1.Cu: one GND_CTRL fill, 1 island, 8512.7 mm2, 0 tracks on In1/In2; 154 GND vias + 24 J8 GND pins + J1/J2 THT; all 4 spec probe points covered; In2.Cu rails: 12V_PROT L-shaped island along the left column to J8 pins 1-3, 5V island, 1V9 island under the DSP (adjacent to the B.Cu capacitors through 0.20 mm), 3V3 background; 7 slivers of 0.0025-0.0039 mm2 in the 3V3 background at corridor edges (LR-15). | checker proxy "0.000 mm separation / 1928 mm2 overlap" is an artefact of J8 and U5 belonging to both groups (LR-11) | pass |
| PWM / TZ paths | PWM_H/PWM_L from ePWM1A/B through U6 and 33 ohm to J8 pins 14/17 (GND on all neighbours); TZ inputs FAULT_N (TZ1), OC_N (TZ2) | EPWM1A 34.0 mm / 3 vias -> PWM_H_G 15.9 / 2 -> PWM_H 16.8 / 3 (total ~67 mm, J8.14 with GND at 13, 15, 16); EPWM1B 23.2 / 2 -> PWM_L_G 17.4 / 2 -> PWM_L 22.7 / 2 (~63 mm, J8.17 with GND at 16, 18, 19); GATE_EN 41.6 mm; FAULT_N 133.8 mm / 5 vias (multi-drop: J8.35, latch, LEDs, TZ1); OC_N 57.9 mm / 3 vias; DSP_TRIP_N 32.2 mm; all 0.2-0.25 mm over the unbroken In1 plane | acceptable for 3.3 V logic at 50 kHz; FLT_H_N / FLT_L_N / RDY_H / RDY_L of the same group are unrouted (LR-02) | pass (routed nets) |
| Clock | Y1 close to XCLKIN | Y1 centre 13.0 mm from U5.105 (XCLKIN); CLK30_SOURCE 12.3 mm + R26 + CLK30 11.6 mm, 4 vias | acceptable at 30 MHz, not tight (LR-16) | human review |
| PE-PCB-004 sensing (control reading) | ISENSE / ISENSE_REF from J8 pins 43/45 to the ADC front ends as a pair | ISENSE 80.2 mm / 4 vias, ISENSE_REF 56.5 mm / 2 vias, mismatch 23.6 mm, 18 segments cross the logic-region corner | ground-referenced DC signals; mismatch is not a measurement error source but the pair intent is not implemented (LR-14) | human review |
| PE-PCB-006 copper and vias (12 V and rails) | CTRL_PWR class 1.0 mm tracks (project), eFuse I_CB 1.96 A, 1.76 A worst pull-in | 12V_IN 42 segments at 0.4 mm (34 F.Cu, 8 B.Cu), 2 parallel vias at U1.1/U1.2; 12V_PROT 21 segments at 0.3 mm plus the In2 island, 2 parallel vias at U1.15/U1.16, island reaches J8 pins 1-3 directly; EFUSE_RTN 71 segments at 0.4 mm (49 on B.Cu); 5V 0.3 mm + island; 5V_SW 0.4 mm. IPC-2221 (35 um, external k 0.048): 1.96 A on 0.4 mm -> 28.8 K, 1.76 A -> 22.5 K, 1.96 A on 0.3 mm -> 46 K, on 1.0 mm -> 6.4 K; one 0.3 mm via (25 um plating, 0.0255 mm2) at 0.98 A -> 2.2 K (external) / 10.7 K (internal formula). Exposed pads: U3 (TPS767D301, 1.39 W) pad 29 has **1** via to GND; U1 pad 17 has 1 via on EFUSE_RTN, a net with no plane. | class width not applied (LR-07); EP thermal vias inadequate (LR-06) | fail |
| 5 V buck hot loop (PE-PCB-002/003 analogue) | input ceramic at U2 VIN/GND, SW node compact | U2 (SOT-23-6) VIN pad 3 -> nearest 12V_PROT capacitor: C3 100 uF electrolytic 6.85 mm, C5 100 nF 17.7 mm, C4 10 uF 21.2 mm (C4 GND pad 21.0 mm from U2 GND); 5V_SW: U2.2 -> L1.1 6.7 mm apart but the net has 10 segments on F.Cu and B.Cu with 3 vias (9.9 mm on B.Cu) and the bootstrap capacitor C6 7 mm from the SW pin | hot loop ~21 mm each way with no local ceramic (LR-05) | fail |
| Connector placement | J1, J3, J5, J4, J2, J6, J7 at the edges; J8 along one long edge | J1 (12.0, 8.3) top-left; J3 (93, 7) top edge; J2 (4.5, 44) left edge; J6 (113, 20) and J7 (113, 58) right edge; J8 along the bottom edge (2.2 mm from it); **J5 UART (44, 30) and J4 BOOT (44, 42) are 44 mm inboard** | LR-09 | fail (J4/J5) |
| Area / compactness | 120 x 80 mm | 9600.0 mm2 = the limit; 215.6 footprints/dm2; courtyard fraction 0.341 front / 0.007 back; assembly height 1.6 + 12.0 (J1) = 13.6 mm above the board | at the limit; smaller is not possible with the current escape geometry | pass |
| Routing complexity | 4 layers: F/B signals, In1 GND, In2 rails | 4151 tracks, 642 through vias, 0 blind/buried; 2 routing layers only; 58 inward / 57 outward LQFP escapes pre-routed; 11 corridor zones; 39 open connections | layer count justified (GND + rails + 2 signal); the 2 signal layers are saturated around the DSP's PWM/fault side, which is the root cause of LR-02 | human review |
| Fine-pitch pin fields | `.kicad_dru` exceptions 0.14 mm for U13/U14 (TLV1702 VSSOP-8) vs 0.15 mm fab minimum (pcb_stackup) | measured pad-to-pad gaps: U13/U14 0.15 mm, U5 LQFP 0.20 mm, U8 0.25 mm | at the 0.15 mm fabrication minimum; the 0.14 mm rule only lets DRC pass | human review |
| Schematic-level item surfaced by the layout | TPS26400 return | EFUSE_RTN (U1 pins 8 RTN and 17 PAD, R3, R4, R5, C2) is an isolated net - no copper or part joins it to GND_CTRL; the model note cites "A-C3", which does not exist in `design/assumptions.md`; the research record asked for the "PowerPAD stitched to the RTN/GND plane"; I12V_MON (IMON across R5 to EFUSE_RTN) is read by the ADC against GND_CTRL | not a layout error (the layout honours the netlist) but a probable schematic defect (LR-10) | human review |
| Visual checks (renders, layer PDF) | no copper outside the outline, zones filled, text inside the outline | all six PDF pages and the three renders inspected; In1 continuous; In2 islands as planned; B.Cu signal routing with one track between J8 pin rows (DRC-clean); silkscreen inside the outline; no ratsnest drawn, so the 39 open connections are invisible in the images; U1, U3, Y1 bodiless in the 3D views | - | pass (visual) |

## 4 Consolidated findings

| ID | Severity | Board | Rule | Summary | Automation-verifiable |
|---|---|---|---|---|---|
| LR-01 | blocker | power | all | no power-board layout exists | yes (run the power layout stage) |
| LR-02 | blocker | control | routing / DRC | 39 unconnected items on 20 nets (reset, TDI, faults, readies, enables) | yes |
| LR-03 | blocker | control | mechanical / interconnect | J8 on F.Cu, cannot mate downward; stackup says B.Cu | yes |
| LR-04 | should-fix | control | PE-PCB-005 / 008 | ADC 1 nF filters 10.5-17.3 mm from the pins | yes |
| LR-05 | should-fix | control | PE-PCB-002/003 (buck), 008 | U2 input ceramics 17.7-21.2 mm away, SW node on two layers with 3 vias | yes |
| LR-06 | should-fix | control | PE-PCB-006 | U3 (1.39 W) and U1 exposed pads with a single via | yes |
| LR-07 | should-fix | control | PE-PCB-006 | CTRL_PWR 1.0 mm class width not applied (0.3/0.4 mm, up to 29-46 K IPC rise) | yes |
| LR-08 | should-fix | power | spec / KR-ISO, KR-PCB-003 | `layout_spec_power.json` refs, pads and net patterns do not match the schematic | yes |
| LR-09 | should-fix | control | placement | J4 / J5 44 mm inboard, baseline wants edges | yes |
| LR-10 | should-fix (schematic) | control | PE-PCB-008 / grounding | EFUSE_RTN floating; A-C3 undefined | no |
| LR-11 | note | control | PE-PCB-007 (tooling) | section proxy overlap caused by shared J8/U5 | yes |
| LR-12 | note | both | evidence (tooling) | verifier `hashes_valid` false by prefix matching | yes |
| LR-13 | note | control | PE-PCB-008 | DSP bypass 5.85 mm max vs 5.0 mm proxy | yes |
| LR-14 | note | control | PE-PCB-004 | ISENSE / ISENSE_REF not routed as a pair (23.6 mm mismatch) | no |
| LR-15 | note | control | DFM | 7 copper slivers 20-30 um in the In2.Cu 3V3 fill | yes |
| LR-16 | note | control | clock | Y1 13 mm from XCLKIN, 4 vias | yes |
| LR-17 | note | control | exports | 3D models missing for U1, U3, Y1 | no |
| LR-18 | note | both | mechanical | overhang >= 46 mm vs documented 40 mm; power-board J7/H8-H11 must follow this board's J8/H3/H4 | no |
| LR-19 | note | both | evidence | DRC run record lacks the report's own hash | yes |

## 5 Open issues for the orchestrator

1. The power board must be laid out before sections 2 of this review can be executed; the spec
   `layout_spec_power.json` must be corrected to the schematic (LR-08) first, or its metrics will
   report the wrong parts as passing or not measured.
2. The control board needs a re-route after the placement corrections (LR-03, LR-04, LR-05, LR-09)
   with the router given room (or 0.15 mm geometry) at the DSP's PWM/fault side (LR-02), then a
   fresh kicad-cli DRC with `--schematic-parity --severity-all` and a re-run of the metrics checker.
3. Schematic question outside the layout agents' reach: EFUSE_RTN to GND_CTRL (LR-10).
4. Mechanical: the stacking geometry (J8 side, overhang, standoff positions) has to be fixed in the
   design documents and mirrored on the power board (LR-03, LR-18).
5. Tooling: `verify_sic_buck.py` hash flag (LR-12), checker section groups (LR-11), DRC record
   report hash (LR-19), library 3D models (LR-17).

Scope reminder: all values are CAD geometry; no electrical, thermal, EMI or safety performance is
qualified by this review.
