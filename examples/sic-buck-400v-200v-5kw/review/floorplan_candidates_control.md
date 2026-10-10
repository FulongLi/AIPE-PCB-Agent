**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# Control board floorplan candidates

Two deterministic floorplans of the TMS320F28335 control board were placed with `automation/kicad_tools/generate_sic_control_board.py`, measured with the layout checker (`automation/verification/check_sic_layout.py`, spec `verification/engineering_checks/layout_spec_control.json`) and compared on the measurable criteria below before routing. Path figures are Manhattan minimum-spanning-tree estimates over pad centres (pre-routing proxies, not routed lengths); separations are courtyard bounding-box distances; the DSP bypass distances are the checker rows from the model `near_dsp_pin` pattern. Scores are weighted normalised sums (0 = best on every criterion, lower is better); the weights are an agent choice recorded in `COMPARISON_WEIGHTS` and need human review.

## Candidate A: Control board floorplan A - DSP at 0 deg, PWM/ADC-A side facing left, JTAG at the right edge

TMS320F28335 (U5) in library orientation (pin 1 top-left): pins 1-44 (GPIO0-17 PWM/fault and ADCINA) face left toward a logic channel between the supplies and the DSP, the bottom side (ADCINB, GPIO18-27, JTAG) faces the header, XCLKIN faces right (oscillator right of the DSP), boot/UART pins face the top edge where J4/J5 sit. Same supply corner, 12V_PROT column, LDO corridor island and mezzanine position as candidate B; JTAG J3 vertical at the right edge, NTC at the bottom-right, status LEDs and E-stop at the upper right edge.

- Candidate A keeps the library orientation; the PWM/fault pins (left side, upper half) and the ADCINA pins (left side, lower half) share the same package side, so the analogue front end and the PWM gating compete for the channel left of the DSP and the PWM nets travel down to the header along the DSP's left flank.
- JTAG faces the header side and is brought to the right edge; the oscillator sits right of the DSP next to XCLKIN.

## Candidate B: Control board floorplan B - DSP rotated 90 deg, PWM/fault/ADC-A side facing the mezzanine header

TMS320F28335 (U5) rotated 90 deg so that pins 1-44 (GPIO0-17 PWM/fault lines and ADCINA0-A7) face the 2 x 25 mezzanine header J8 along the bottom edge; the former bottom side (ADCINB, GPIO18-27, JTAG) faces the right-hand analogue section, XCLKIN faces the oscillator above the DSP and the boot/UART pins face the left strip with J4/J5. Supplies (eFuse, 5 V buck, dual LDO) in the top-left corner, 12V_PROT running down the left column to mezzanine pins 1-3, LDO 1V9 output in a corridor island feeding the DSP core island on In2.Cu, JTAG at the top-right edge, status LEDs and E-stop at the right edge, NTC at the lower right.

- Candidate B puts the dense left package side (43 connected pins: GPIO0-17, ADCINA0-A4, VSS/VDD) toward the mezzanine so that the PWM, trip and analogue nets are short and the inner-escape vias of that side exit on B.Cu through the staggered outer via rows.
- The analogue section sits to the right of the DSP next to the ADCINB pins and the analogue end of the header (pins 43-49); the PWM gating and fault logic sits between the DSP bottom edge and the header's digital pins (7-37).

## Criteria

| Criterion | Candidate A | Candidate B | Better |
|---|---|---|---|
| DSP bypass capacitor to pin, maximum (mm) | 5.24 | 5.849 | lower |
| DSP bypass capacitor to pin, mean (mm) | 4.549 | 4.571 | lower |
| PWM chains ePWM1A/B -> gate -> 33 ohm -> J8 (Manhattan MST sum, mm) | 172.46 | 116.1 | lower |
| TZ nets FAULT_N + OC_N (Manhattan MST sum, mm) | 189.33 | 175.66 | lower |
| Analogue section to PWM gating parts (courtyard bbox distance, mm) | 20.96 | 20.68 | higher |
| Analogue nets (Manhattan MST sum, mm) | 1392.53 | 1009.44 | lower |
| Control-section to supply-section courtyard bbox distance (checker PE-PCB-007 proxy; 0 = boxes overlap, mm) | 0.0 | 0.0 | higher |
| Courtyard fraction, front | 0.3413 | 0.3413 | info |
| Courtyard fraction, back | 0.0067 | 0.0067 | info |
| Placed parts bounding box / board area | 0.979 | 0.979 | info |
| Supply loop bbox area: 5V buck (U2, input/output capacitors, L1) (mm2) | 477.2 | 464.2 | lower |
| Supply loop bbox area: dual LDO (U3, input and output capacitors) (mm2) | 4632.0 | 3155.3 | lower |

## Scores

| Criterion | Weight | A | B |
|---|---|---|---|
| dsp_bypass_max_mm | 2.0 | 5.24 | 5.849 |
| pwm_path_mm | 3.0 | 172.46 | 116.1 |
| tz_path_mm | 2.0 | 189.33 | 175.66 |
| analog_pwm_separation_mm | 2.0 | 20.96 | 20.68 |
| analog_path_mm | 1.0 | 1392.53 | 1009.44 |
| courtyard_fraction_front | 0.5 | 0.3413 | 0.3413 |
| **weighted score (lower is better)** | | 6.0 | 4.0 |

**Selected: candidate B.**

## Routed result of the selected candidate

Board `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\kicad\control_board\AIPE_SiC_Buck_Control.kicad_pcb`: 4151 tracks, 642 vias, 16 zones (saved board counts), 39 unresolved router items, 11 corridor zones, 58 inward / 57 outward DSP escapes (4 parity exceptions closed by corridors).

DRC (kicad-cli, schematic parity, severity-all): status **failed**, findings 39 (violations 0, unconnected 39, parity 0), manifest `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\verification\drc\20261010T104013Z-drc-7a5fd84b\run.json`.

Routed track lengths of the compared nets (mm, router sum; the layout metrics file carries the pcbnew figures):

- EPWM1A: 41.031
- PWM_H_G: 15.871
- PWM_H: 16.8
- EPWM1B: 23.181
- PWM_L_G: 17.371
- PWM_L: 22.675
- FAULT_N: 144.263
- OC_N: 57.888
- VIN_SENSE: 80.278
- VOUT_SENSE: 84.727
- ISENSE: 80.175
- ISENSE_REF: 56.55

## Limitations

- Candidates differ in the DSP orientation and the connector arrangement; the supply corner, the 12V_PROT column and the mezzanine position are shared, so the supply-loop figures are equal by construction.
- Manhattan MST estimates ignore layer changes and detours; routed lengths of the selected candidate are listed above for confirmation only.
- The checker dispositions are measurements against spec proxies, not engineering acceptance (human review required).
