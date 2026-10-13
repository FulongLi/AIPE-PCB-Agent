# Layout metrics - AIPE SiC buck TMS320F28335 control board (AIPE_SiC_Buck_Control) - layout metrics spec

Status: **measured-human-review-required**. Generated 2026-10-13T02:27:09.164357+00:00 by `automation/verification/check_sic_layout.py` (pcbnew 10.0.7, distance backend numpy, 0.547 s).

Board `examples\sic-buck-400v-200v-5kw\kicad\control_board\AIPE_SiC_Buck_Control.kicad_pcb` (sha256 `52ca6c234357948a...`), spec `examples\sic-buck-400v-200v-5kw\verification\engineering_checks\layout_spec_control.json`, model `examples\sic-buck-400v-200v-5kw\design\circuit_control.json`.

## Board

| Metric | Value |
| --- | --- |
| Outline (mm) | 120.00 x 80.00 |
| Outline area (mm2) | 9600.0 |
| Copper layers | 4 (F.Cu, In1.Cu, In2.Cu, B.Cu) |
| Thickness (mm) | 1.600 |
| Copper thickness (um, stackup text) | F.Cu=35.000; In1.Cu=35.000; In2.Cu=35.000; B.Cu=35.000 |
| Footprints / tracks / vias / zones / rule areas | 207 / 4523 / 798 / 20 / 0 |
| Nets | 199 |
| Zones without fill (areas read from the file) | none |
| Expected (spec) | outline_mm=120, 80; copper_layers=4; copper_um=35; thickness_mm=1.600 |

## Rule table

Dispositions follow the spec thresholds only; every row needs engineering acceptance by a human reviewer.

| Rule | Requirement | Metric | Measured | Threshold | Disposition | Note |
| --- | --- | --- | --- | --- | --- | --- |
| PE-PCB-001 | Minimise MOSFET gate loop | driver output to gate pad distance | n/a | n/a | not measured - spec input missing or reference not found | no gate_loops in the spec |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | HF capacitor to device pin distance | n/a | n/a | not measured - spec input missing or reference not found | no commutation section in the spec |
| PE-PCB-003 | Minimise HF commutation loop | commutation loop proxies | n/a | n/a | not measured - spec input missing or reference not found | no commutation section in the spec |
| PE-PCB-004 | Use Kelvin current sensing | ISENSE / ISENSE_REF from the mezzanine (J8 pins 43/45) to the ADC front ends track lengths (mm) and mismatch | ISENSE=114.538; ISENSE_REF=51.569; mismatch=62.969 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | Separate sensitive analog and switch-node paths | n/a | n/a | not measured - spec input missing or reference not found | no spec input for this rule |
| PE-PCB-006 | Justify high-current copper and via capacity | HV net copper | n/a | n/a | not measured - spec input missing or reference not found | no HV net classes in the spec |
| PE-PCB-007 | Separate control and switching structures | control section (45 parts) to power stage (32 parts) bounding-box distance (mm) | 26.180 | n/a | measured - human review required |  |
| PE-PCB-007 | Separate control and switching structures | GND_CTRL zone area (mm2) and island count per layer | In1.Cu=area=8376.100; islands=1 | area >= 8000.0 mm2 and required probe points covered | within spec threshold - human review required | V1 ground-plane extent guard generalised |
| PE-PCB-007 | Separate control and switching structures | board area (mm2), footprints per dm2, courtyard fraction front/back | area=9600.000; per_dm2=215.600; courtyard=front=0.300; back=0.048 | area <= 9600 mm2 | within spec threshold - human review required | HV bbox fraction n/a; power density n/a W/dm2, n/a W/L |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U5 supply pads ['4', '9', '15', '23', '29', '31', '34', '45', '59', '61', '71', '84', '93', '101', '107', '109', '117', '121', '126', '139', '143', '146', '154', '159', '167', '170'] to nearest decoupling capacitor pad, maximum (mm) | 5.381 | <= 5.0 mm | exceeds spec threshold - human review required | 4->C17.1 3.97; 9->C18.1 4.55; 15->C19.1 3.91; 23->C20.1 3.91; 29->C21.1 3.91; 31->C21.1 4.10; 34->C23.1 4.55; 45->C24.1 4.55; 59->C25.1 4.68; 61->C26.1 4.38; 71->C27.1 4.55; 84->C28.1 4.55; 93->C29.1 5.38; 101->C30.1 3.90; 107->C31.1 5.38; 109->C32.1 3.90; 117->C33.1 3.90; 121->C34.1 4.55; 126->C35.1 3.90; 139->C35.1 5.03; 143->C37.1 4.79; 146->C36.1 3.90; 154->C39.1 3.93; 159->C40.1 4.55; 167->C41.1 4.38; 170->C42.1 4.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U1 supply pads ['1', '2', '15', '16'] to nearest decoupling capacitor pad, maximum (mm) | 22.763 | n/a | measured - human review required | 1->C1.1 3.73; 2->C1.1 3.78; 15->C5.1 22.36; 16->C5.1 22.76 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U2 supply pads ['3'] to nearest decoupling capacitor pad, maximum (mm) | 2.038 | n/a | measured - human review required | 3->C5.1 2.04 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U3 supply pads ['5', '6', '11', '12', '17', '18', '23', '24'] to nearest decoupling capacitor pad, maximum (mm) | 8.025 | n/a | measured - human review required | 5->C13.1 4.64; 6->C13.1 4.70; 11->C10.1 5.73; 12->C10.1 5.65; 17->C37.1 5.90; 18->C37.1 6.54; 23->C43.1 8.03; 24->C43.1 7.38 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U4 supply pads ['6'] to nearest decoupling capacitor pad, maximum (mm) | 26.504 | n/a | measured - human review required | 6->C16.1 26.50 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U6 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 2.579 | n/a | measured - human review required | 8->C16.1 2.58 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U7 supply pads ['2', '7', '8'] to nearest decoupling capacitor pad, maximum (mm) | 6.958 | n/a | measured - human review required | 2->C58.1 6.96; 7->C58.1 3.59; 8->C58.1 3.53 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U8 supply pads ['14'] to nearest decoupling capacitor pad, maximum (mm) | 10.393 | n/a | measured - human review required | 14->C23.1 10.39 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U9 supply pads ['14'] to nearest decoupling capacitor pad, maximum (mm) | 2.552 | n/a | measured - human review required | 14->C57.1 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U10 supply pads ['12', '13', '14'] to nearest decoupling capacitor pad, maximum (mm) | 7.203 | n/a | measured - human review required | 12->C58.1 7.20; 13->C58.1 6.88; 14->C58.1 6.60 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U11 supply pads ['14'] to nearest decoupling capacitor pad, maximum (mm) | 9.588 | n/a | measured - human review required | 14->C60.1 9.59 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U12 supply pads ['1'] to nearest decoupling capacitor pad, maximum (mm) | 4.731 | n/a | measured - human review required | 1->C63.1 4.73 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U13 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 3.888 | n/a | measured - human review required | 8->C50.1 3.89 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U14 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 3.613 | n/a | measured - human review required | 8->C56.1 3.61 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U15 supply pads ['1'] to nearest decoupling capacitor pad, maximum (mm) | 4.275 | n/a | measured - human review required | 1->C61.1 4.28 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | Y1 supply pads ['1', '4'] to nearest decoupling capacitor pad, maximum (mm) | 3.960 | n/a | measured - human review required | 1->C49.1 3.96; 4->C29.1 3.62 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U5 bypass capacitors (26 from the model near_dsp_pin) maximum pad distance (mm) | 5.381 | <= 5.0 mm | exceeds spec threshold - human review required |  |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | Kelvin-source versus power-source separation | n/a | n/a | not measured - spec input missing or reference not found | no gate_loops in the spec |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | barrier strip copper check | n/a | n/a | not measured - spec input missing or reference not found | no barrier_keepouts in the spec |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | net-class pair copper distances | n/a | n/a | not measured - spec input missing or reference not found | no isolation pairs in the spec |
| KR-ISO-004 | Slots and cut-outs to extend creepage | slots under barrier parts | n/a | n/a | not measured - spec input missing or reference not found | no barrier_parts in the spec |
| KR-TH-002 | Rated insulating interface for shared heat sinks (HV copper keep-out at the sink) | HV copper distance to the heatsink envelope | n/a | n/a | not measured - spec input missing or reference not found | heatsink ref missing or not on the board |

Rows: 31 - within spec threshold 2, exceeding 2, measured without threshold 17, not measured 10.

## Decoupling

| IC | Pad | Net | Capacitor pad | Distance (mm) | Same net |
| --- | --- | --- | --- | --- | --- |
| U5 | 4 | 1V9 | C17.1 | 3.971 | yes |
| U5 | 9 | 3V3 | C18.1 | 4.550 | yes |
| U5 | 15 | 1V9 | C19.1 | 3.908 | yes |
| U5 | 23 | 1V9 | C20.1 | 3.908 | yes |
| U5 | 29 | 1V9 | C21.1 | 3.908 | yes |
| U5 | 31 | 1V9 | C21.1 | 4.095 | yes |
| U5 | 34 | 3V3 | C23.1 | 4.550 | yes |
| U5 | 45 | 3V3 | C24.1 | 4.550 | yes |
| U5 | 59 | 1V9 | C25.1 | 4.675 | yes |
| U5 | 61 | 1V9 | C26.1 | 4.383 | yes |
| U5 | 71 | 3V3 | C27.1 | 4.550 | yes |
| U5 | 84 | 3V3 | C28.1 | 4.550 | yes |
| U5 | 93 | 3V3 | C29.1 | 5.381 | yes |
| U5 | 101 | 1V9 | C30.1 | 3.900 | yes |
| U5 | 107 | 3V3 | C31.1 | 5.381 | yes |
| U5 | 109 | 1V9 | C32.1 | 3.900 | yes |
| U5 | 117 | 1V9 | C33.1 | 3.900 | yes |
| U5 | 121 | 3V3 | C34.1 | 4.550 | yes |
| U5 | 126 | 1V9 | C35.1 | 3.900 | yes |
| U5 | 139 | 1V9 | C35.1 | 5.030 | yes |
| U5 | 143 | 3V3 | C37.1 | 4.791 | yes |
| U5 | 146 | 1V9 | C36.1 | 3.900 | yes |
| U5 | 154 | 1V9 | C39.1 | 3.932 | yes |
| U5 | 159 | 3V3 | C40.1 | 4.550 | yes |
| U5 | 167 | 1V9 | C41.1 | 4.383 | yes |
| U5 | 170 | 3V3 | C42.1 | 4.550 | yes |
| U1 | 1 | 12V_IN | C1.1 | 3.725 | yes |
| U1 | 2 | 12V_IN | C1.1 | 3.781 | yes |
| U1 | 15 | 12V_PROT | C5.1 | 22.358 | yes |
| U1 | 16 | 12V_PROT | C5.1 | 22.763 | yes |
| U2 | 3 | 12V_PROT | C5.1 | 2.038 | yes |
| U3 | 5 | 5V | C13.1 | 4.639 | yes |
| U3 | 6 | 5V | C13.1 | 4.698 | yes |
| U3 | 11 | 5V | C10.1 | 5.726 | yes |
| U3 | 12 | 5V | C10.1 | 5.648 | yes |
| U3 | 17 | 3V3 | C37.1 | 5.896 | yes |
| U3 | 18 | 3V3 | C37.1 | 6.539 | yes |
| U3 | 23 | 1V9 | C43.1 | 8.025 | yes |
| U3 | 24 | 1V9 | C43.1 | 7.375 | yes |
| U4 | 6 | 3V3 | C16.1 | 26.504 | yes |
| U6 | 8 | 3V3 | C16.1 | 2.579 | yes |
| U7 | 2 | 3V3 | C58.1 | 6.958 | yes |
| U7 | 7 | 3V3 | C58.1 | 3.589 | yes |
| U7 | 8 | 3V3 | C58.1 | 3.525 | yes |
| U8 | 14 | 3V3 | C23.1 | 10.393 | yes |
| U9 | 14 | 3V3 | C57.1 | 2.551 | yes |
| U10 | 12 | 3V3 | C58.1 | 7.203 | yes |
| U10 | 13 | 3V3 | C58.1 | 6.877 | yes |
| U10 | 14 | 3V3 | C58.1 | 6.600 | yes |
| U11 | 14 | 3V3 | C60.1 | 9.588 | yes |
| U12 | 1 | 3V3 | C63.1 | 4.731 | yes |
| U13 | 8 | 3V3 | C50.1 | 3.888 | yes |
| U14 | 8 | 3V3 | C56.1 | 3.613 | yes |
| U15 | 1 | 3V3 | C61.1 | 4.276 | yes |
| Y1 | 1 | 3V3 | C49.1 | 3.960 | yes |
| Y1 | 4 | 3V3 | C29.1 | 3.623 | yes |

## Sensing

| Pair | Nets | Track (mm) | Vias | Mismatch (mm) | Min to SW (mm) |
| --- | --- | --- | --- | --- | --- |
| ISENSE / ISENSE_REF from the mezzanine (J8 pins 43/45) to the ADC front ends | ISENSE, ISENSE_REF | ISENSE=114.54; ISENSE_REF=51.57 | ISENSE=5; ISENSE_REF=6 | 62.969 | n/a |

## Control section

Control parts: 45, power parts: 32, bounding-box separation 26.180 mm.

| Ground layer | Area (mm2) | Islands | Zones | Required probes covered | Forbidden probes copper-free |
| --- | --- | --- | --- | --- | --- |
| In1.Cu | 8376.1 | 1 | 1 | 4/4 | 0/0 |

DSP bypass capacitors: 26, maximum pad distance 5.381 mm.

## Compactness

| Metric | Value |
| --- | --- |
| Board area (mm2 / dm2) | 9600.0 / 0.960 |
| Footprints per dm2 | 215.6 |
| Courtyard fraction front / back | 0.300 / 0.048 |
| HV bounding-box fraction of board | n/a |
| HV copper on outer layers (mm2, fraction of both sides) | 0 (0.000) |
| Tallest component | J1 12.0 mm |
| Assembly height (mm) declared / computed / used | n/a, 13.6, 13.6 |
| Rated power (W) | n/a |
| Power density (W/dm2, W/L) | n/a, n/a |

## Classified nets

| Net | Class | Track (mm) | Tracks | Vias | Pads | Layers | Zone area (mm2) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12V_IN | CTRL_PWR | 33.9 | 12 | 0 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_PROT | CTRL_PWR | 17.9 | 32 | 11 | 13 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=1381.000 |
| 1V9 | CTRL_SELV | 50.0 | 61 | 37 | 37 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=797.300 |
| 1V9_BULK | CTRL_SELV | 14.0 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 3V3 | CTRL_SELV | 121.4 | 195 | 84 | 89 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=5222.400 |
| 3V3_BULK | CTRL_SELV | 4.5 | 5 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 5V | CTRL_PWR | 23.7 | 43 | 15 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=625.300 |
| 5V_BST | CTRL_SELV | 2.5 | 1 | 0 | 2 | F.Cu |  |
| 5V_EN | CTRL_SELV | 22.5 | 18 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 5V_FB | CTRL_SELV | 48.1 | 28 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 5V_SW | CTRL_PWR | 14.3 | 4 | 0 | 3 | F.Cu |  |
| ADCREFM | CTRL_ANALOG | 8.6 | 14 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADCREFP | CTRL_ANALOG | 8.2 | 13 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADCRESEXT | CTRL_ANALOG | 27.7 | 18 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_I12V | CTRL_ANALOG | 31.1 | 27 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_ISENSE | CTRL_ANALOG | 34.7 | 33 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_ISENSE_REF | CTRL_ANALOG | 42.9 | 49 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_TEMP_CTRL | CTRL_ANALOG | 39.6 | 66 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_TEMP_HS | CTRL_ANALOG | 47.1 | 37 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_V12V | CTRL_ANALOG | 32.9 | 26 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_VIN | CTRL_ANALOG | 37.6 | 34 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_VOUT | CTRL_ANALOG | 131.9 | 99 | 14 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ARM | CTRL_SELV | 93.9 | 80 | 10 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BIAS_EN | CTRL_SELV | 55.7 | 24 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BOOT84 | CTRL_SELV | 56.3 | 20 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BOOT85 | CTRL_SELV | 8.2 | 10 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BOOT86 | CTRL_SELV | 11.0 | 18 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BOOT87 | CTRL_SELV | 14.3 | 12 | 0 | 2 | F.Cu |  |
| CLK30 | CTRL_SELV | 13.8 | 13 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| CLK30_SOURCE | CTRL_SELV | 5.7 | 7 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| CORE_OK | CTRL_SELV | 65.8 | 22 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DSP_TRIP_N | CTRL_SELV | 207.1 | 99 | 21 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_DVDT | CTRL_SELV | 31.6 | 31 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_ILIM | CTRL_SELV | 34.2 | 13 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_OVP | CTRL_SELV | 33.4 | 21 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_RTN | CTRL_PWR | 63.6 | 54 | 15 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_SHDN | CTRL_SELV | 13.3 | 12 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_UVLO | CTRL_SELV | 39.4 | 19 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EMU0 | CTRL_SELV | 49.8 | 35 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EMU1 | CTRL_SELV | 52.2 | 32 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EPWM1A | CTRL_SELV | 48.5 | 31 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EPWM1B | CTRL_SELV | 41.4 | 37 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ESTOP_N | CTRL_SELV | 384.6 | 232 | 24 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAN_TACH | CTRL_SELV | 205.0 | 128 | 8 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAULT_LATCH_N | CTRL_SELV | 64.6 | 29 | 5 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAULT_N | CTRL_SELV | 303.0 | 216 | 16 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FB19 | CTRL_SELV | 44.2 | 22 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_12V_N | CTRL_SELV | 146.1 | 75 | 16 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_H_N | CTRL_SELV | 99.8 | 51 | 8 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_L_N | CTRL_SELV | 89.2 | 71 | 10 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G1_N | CTRL_SELV | 18.3 | 10 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G2_N | CTRL_SELV | 9.4 | 7 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G3_N | CTRL_SELV | 12.5 | 9 | 0 | 2 | F.Cu |  |
| GATE_EN | CTRL_SELV | 81.3 | 42 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GND_CTRL | CTRL_SELV | 227.5 | 296 | 161 | 188 | F.Cu, In1.Cu, In2.Cu, B.Cu | In1.Cu=8376.100 |
| I12V_MON | CTRL_SELV | 140.2 | 39 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| IO_EN_N | CTRL_SELV | 36.4 | 16 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISENSE | CTRL_ANALOG | 114.5 | 69 | 5 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISENSE_REF | CTRL_ANALOG | 51.6 | 31 | 6 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_12V_A | CTRL_SELV | 5.0 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_ARMED_A | CTRL_SELV | 17.9 | 8 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_FAULT | CTRL_SELV | 24.4 | 7 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_FAULT_A | CTRL_SELV | 25.3 | 11 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_RUN | CTRL_SELV | 27.5 | 24 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_RUN_A | CTRL_SELV | 22.4 | 10 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| MON5 | CTRL_SELV | 19.0 | 11 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| MR_N | CTRL_SELV | 11.4 | 4 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_N | CTRL_SELV | 193.5 | 135 | 10 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OTP_N | CTRL_SELV | 70.8 | 52 | 8 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OTP_REF | CTRL_ANALOG | 28.8 | 18 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OVP_IN_N | CTRL_SELV | 66.6 | 52 | 5 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OVP_IN_REF | CTRL_ANALOG | 19.5 | 14 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OVP_N | CTRL_SELV | 24.0 | 12 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OVP_OUT_N | CTRL_SELV | 66.0 | 35 | 9 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OVP_OUT_REF | CTRL_ANALOG | 18.6 | 20 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_H_N | CTRL_SELV | 153.4 | 62 | 9 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_H_OK | CTRL_SELV | 21.8 | 23 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_L_N | CTRL_SELV | 222.2 | 185 | 12 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_L_OK | CTRL_SELV | 15.2 | 11 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_S_N | CTRL_SELV | 201.0 | 123 | 15 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_S_OK | CTRL_SELV | 21.7 | 29 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_H | CTRL_SELV | 15.3 | 9 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_H_G | CTRL_SELV | 10.7 | 12 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_L | CTRL_SELV | 25.9 | 8 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_L_G | CTRL_SELV | 8.9 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_H | CTRL_SELV | 75.2 | 32 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_L | CTRL_SELV | 92.9 | 55 | 9 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| REF2V5 | CTRL_ANALOG | 32.9 | 23 | 5 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| REF3V0 | CTRL_ANALOG | 22.1 | 23 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RELAY_ON | CTRL_SELV | 51.9 | 41 | 3 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RESET_CT | CTRL_SELV | 7.0 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RESET_N | CTRL_SELV | 54.2 | 47 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SEQ_BASE | CTRL_SELV | 12.0 | 11 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SPARE_D1 | CTRL_SELV | 113.3 | 30 | 6 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SPARE_D2 | CTRL_SELV | 94.4 | 46 | 7 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TCK | CTRL_SELV | 44.9 | 21 | 1 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TDI | CTRL_SELV | 31.0 | 15 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TDO | CTRL_SELV | 39.0 | 38 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_CTRL | CTRL_ANALOG | 27.6 | 11 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_HS_NTC | CTRL_ANALOG | 38.3 | 23 | 5 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TMS | CTRL_SELV | 33.8 | 25 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TRST | CTRL_SELV | 33.4 | 28 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UART_RX | CTRL_SELV | 60.3 | 29 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UART_TX | CTRL_SELV | 71.9 | 27 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UVLO | CTRL_SELV | 48.9 | 36 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UVLO_N | CTRL_SELV | 70.4 | 35 | 8 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UVLO_REF | CTRL_ANALOG | 26.3 | 20 | 4 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| V12V_MON | CTRL_SELV | 156.5 | 45 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_SENSE | CTRL_ANALOG | 103.8 | 63 | 8 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_SENSE | CTRL_ANALOG | 52.7 | 39 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| XRS_N | CTRL_SELV | 206.6 | 113 | 21 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| unconnected-(D2-NC-Pad2) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(J3-Pad6) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| unconnected-(U1-MODE-Pad6) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U1-NC-Pad13) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U1-NC-Pad4) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U10-NC-Pad11) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U10-NC-Pad3) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U11-5Y-Pad10) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U11-6Y-Pad12) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad1) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad13) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad14) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad15) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad16) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad19) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad2) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad20) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad21) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad26) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad27) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad7) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U3-NC-Pad8) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO23-Pad67) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO25-Pad69) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO30-Pad1) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO31-Pad176) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO32-Pad74) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO33-Pad75) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO34-Pad142) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO35-Pad148) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO36-Pad145) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO37-Pad150) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO38-Pad137) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO39-Pad175) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO40-Pad151) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO41-Pad152) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO42-Pad153) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO43-Pad156) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO44-Pad157) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO45-Pad158) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO46-Pad161) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO47-Pad162) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO48-Pad88) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO49-Pad89) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO50-Pad90) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO51-Pad91) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO52-Pad94) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO53-Pad95) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO54-Pad96) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO55-Pad97) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO56-Pad98) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO57-Pad99) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO58-Pad100) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO59-Pad110) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO60-Pad111) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO61-Pad112) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO62-Pad113) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO63-Pad114) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO64-Pad115) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO65-Pad116) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO66-Pad119) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO67-Pad122) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO68-Pad123) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO69-Pad124) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO70-Pad127) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO71-Pad128) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO72-Pad129) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO73-Pad130) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO74-Pad131) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO75-Pad132) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO76-Pad133) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO77-Pad134) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO78-Pad135) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO79-Pad136) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO80-Pad163) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO81-Pad164) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO82-Pad165) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-GPIO83-Pad168) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-TEST1-Pad81) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-TEST2-Pad82) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-X2-Pad102) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-XCLKOUT-Pad138) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U5D-XRD-Pad149) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U7-Q_N-Pad3) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U8-NC-Pad11) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U8-NC-Pad3) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U9-NC-Pad11) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |
| unconnected-(U9-NC-Pad3) | CTRL_SELV | 0.0 | 0 | 0 | 1 | F.Cu |  |

## Notes and limitations

- Straight-line pad distances, track sums and copper areas are geometric proxies; they are not loop inductance, current-path length, creepage per standard or EMI performance.
- Isolation distances are copper-to-copper on each layer (pads, tracks, vias, filled zones); through-air clearance between layers, component bodies, solder mask and coatings are not evaluated.
- Thresholds are those given in the layout spec (taken from the design baseline); no acceptance limit is invented here. Engineering acceptance of every row remains a human responsibility.
- Slot detection relies on non-plated oblong pads or Edge.Cuts graphics inside the barrier part courtyard; the fabricator must confirm the slot width after tolerance.
- The control board is entirely SELV (architecture option B): no isolation pairs, barrier strips or slots apply; the checker reports those rows as not measured by design.
- Reference designators follow the placed board generated by automation/kicad_tools/generate_sic_control_board.py from design/circuit_control.json: U5 = TMS320F28335PGFA, J8 = TSW-125-07-G-D mezzanine header, U1 = TPS26400 eFuse, U2 = TPS54302 5 V buck, U3 = TPS767D301 dual LDO, U4 = TPS3808 supervisor, U6 = SN74LVC2G08 PWM gate, U7 = SN74LVC1G74 latch, U8-U10 = SN74LV21A, U11 = SN74LV04A, U12/U15 = REF3125/REF3130, U13/U14 = TLV1702, U16 = LM61.
- The DSP bypass rows reuse the V1 near_dsp_pin pattern from the model passed with --model (circuit_control.json); the 1V9 capacitors sit on B.Cu under the package, the 3V3 capacitors on F.Cu outside the escape via rows.
- Thresholds: the baseline (design/design_decisions.json) gives the control board no numeric layout limits beyond the outline, stack and 'per-pin 100 nF capacitors within a few mm of the pins'. The 5.0 mm bypass proxy and the 8000 mm2 ground-plane proxy ('solid GND_CTRL, no splits under ADC or PWM tracks', pcb_stackup.md section 2) are agent-added review proxies, not baseline values; every other row is measured only.
- CTRL_PWR groups the supply-entry and switching nets (12V_IN, 12V_PROT, 5V, 5V_SW, EFUSE_RTN) so that PE-PCB-007 measures the distance between the analogue section and the supply section; GND_CTRL, 3V3 and 1V9 reach every section through the planes and are not used as section markers.
- Review LR-11: the section-separation proxy (PE-PCB-007) excludes J8 and U5, which carry nets of both sections; the ground probe points follow the review-corrected floorplan (DSP centre (68, 31) mm).
- Review LR-03: the mezzanine header J8 is on B.Cu (mates downward into the power-board socket); its 11.05 mm is the stack height, the component-side height is set by J1 (12.0 mm).
- Routing exception (correction run 2026-10-11): BIAS_EN (static bias-module enable, U5 pin 12 -> J8 pin 9) is one 0.2 mm track on In2.Cu through the 3V3 background zone, placed by the single-layer In2.Cu pass of generate_sic_control_board.py after the F.Cu/B.Cu stages (no lane was left under the DSP south escape rows); it keeps 0.5 mm from every rail-island polygon and 0.3 mm from vias and plated pads, so the per-net table may list In2.Cu among the layers of a signal net. All other signals stay on F.Cu/B.Cu; In1.Cu is the unbroken GND_CTRL plane. Fresh-eyes round 2026-10-11: the same pass also carries PG_BIAS_L_N (U5.62 escape via to a via of its logic-region copper group, 44.75 mm) and OVP_OUT_N (20.0 mm) as fallbacks for connections the F.Cu/B.Cu stages left open with the current shared router; In2.Cu tracks keep 3.0 mm from the rail islands except through their port exit channels (DRC manifest 20261011T002742Z-drc-0d33d344, 0 findings).
