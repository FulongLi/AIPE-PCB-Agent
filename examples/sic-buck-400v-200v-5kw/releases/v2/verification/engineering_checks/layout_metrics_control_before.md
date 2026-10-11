# Layout metrics - AIPE SiC buck TMS320F28335 control board (AIPE_SiC_Buck_Control) - layout metrics spec

Status: **measured-human-review-required**. Generated 2026-10-10T10:40:13.467742+00:00 by `automation/verification/check_sic_layout.py` (pcbnew 10.0.7, distance backend numpy, 0.844 s).

Board `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\kicad\control_board\AIPE_SiC_Buck_Control.kicad_pcb` (sha256 `119d37df1b737fd7...`), spec `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\verification\engineering_checks\layout_spec_control.json`, model `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\design\circuit_control.json`.

## Board

| Metric | Value |
| --- | --- |
| Outline (mm) | 120.00 x 80.00 |
| Outline area (mm2) | 9600.0 |
| Copper layers | 4 (F.Cu, In1.Cu, In2.Cu, B.Cu) |
| Thickness (mm) | 1.600 |
| Copper thickness (um, stackup text) | F.Cu=35.000; In1.Cu=35.000; In2.Cu=35.000; B.Cu=35.000 |
| Footprints / tracks / vias / zones / rule areas | 207 / 4151 / 642 / 16 / 0 |
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
| PE-PCB-004 | Use Kelvin current sensing | ISENSE / ISENSE_REF from the mezzanine (J8 pins 43/45) to the ADC front ends track lengths (mm) and mismatch | ISENSE=80.175; ISENSE_REF=56.550; mismatch=23.625 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | Separate sensitive analog and switch-node paths | n/a | n/a | not measured - spec input missing or reference not found | no spec input for this rule |
| PE-PCB-006 | Justify high-current copper and via capacity | HV net copper | n/a | n/a | not measured - spec input missing or reference not found | no HV net classes in the spec |
| PE-PCB-007 | Separate control and switching structures | control section (46 parts) to power stage (33 parts) bounding-box distance (mm) | 0.000 | n/a | measured - human review required | overlap 1928 mm2 |
| PE-PCB-007 | Separate control and switching structures | GND_CTRL zone area (mm2) and island count per layer | In1.Cu=area=8512.700; islands=1 | area >= 8000.0 mm2 and required probe points covered | within spec threshold - human review required | V1 ground-plane extent guard generalised |
| PE-PCB-007 | Separate control and switching structures | board area (mm2), footprints per dm2, courtyard fraction front/back | area=9600.000; per_dm2=215.600; courtyard=front=0.341; back=0.007 | area <= 9600 mm2 | within spec threshold - human review required | HV bbox fraction n/a; power density n/a W/dm2, n/a W/L |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U5 supply pads ['4', '9', '15', '23', '29', '31', '34', '45', '59', '61', '71', '84', '93', '101', '107', '109', '117', '121', '126', '139', '143', '146', '154', '159', '167', '170'] to nearest decoupling capacitor pad, maximum (mm) | 5.849 | <= 5.0 mm | exceeds spec threshold - human review required | 4->C17.1 3.97; 9->C18.1 5.05; 15->C19.1 3.91; 23->C20.1 3.91; 29->C21.1 3.91; 31->C21.1 4.10; 34->C23.1 5.05; 45->C24.1 5.05; 59->C25.1 4.68; 61->C26.1 4.38; 71->C27.1 5.05; 84->C28.1 5.05; 93->C29.1 5.05; 101->C30.1 3.90; 107->C31.1 5.05; 109->C32.1 3.90; 117->C33.1 3.90; 121->C34.1 5.05; 126->C35.1 3.90; 139->C35.1 5.03; 143->C37.1 5.85; 146->C36.1 3.90; 154->C39.1 3.93; 159->C40.1 5.05; 167->C41.1 4.38; 170->C42.1 5.05 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U1 supply pads ['1', '2', '15', '16'] to nearest decoupling capacitor pad, maximum (mm) | 8.830 | n/a | measured - human review required | 1->C1.1 3.73; 2->C1.1 3.78; 15->C4.1 8.18; 16->C4.1 8.83 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U2 supply pads ['3'] to nearest decoupling capacitor pad, maximum (mm) | 6.845 | n/a | measured - human review required | 3->C3.1 6.85 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U3 supply pads ['5', '6', '11', '12', '17', '18', '23', '24'] to nearest decoupling capacitor pad, maximum (mm) | 7.308 | n/a | measured - human review required | 5->C7.1 7.31; 6->C7.1 6.91; 11->C7.1 5.69; 12->C7.1 5.64; 17->C37.1 5.81; 18->C37.1 6.46; 23->C43.1 4.93; 24->C43.1 4.77 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U4 supply pads ['6'] to nearest decoupling capacitor pad, maximum (mm) | 5.865 | n/a | measured - human review required | 6->C16.1 5.87 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U6 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 2.526 | n/a | measured - human review required | 8->C58.1 2.53 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U7 supply pads ['2', '7', '8'] to nearest decoupling capacitor pad, maximum (mm) | 4.670 | n/a | measured - human review required | 2->C57.1 4.67; 7->C57.1 3.18; 8->C57.1 2.53 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U8 supply pads ['14'] to nearest decoupling capacitor pad, maximum (mm) | 2.552 | n/a | measured - human review required | 14->C62.1 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U9 supply pads ['14'] to nearest decoupling capacitor pad, maximum (mm) | 2.552 | n/a | measured - human review required | 14->C60.1 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U10 supply pads ['12', '13', '14'] to nearest decoupling capacitor pad, maximum (mm) | 8.748 | n/a | measured - human review required | 12->C18.1 8.75; 13->C58.1 8.23; 14->C58.1 7.63 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U11 supply pads ['14'] to nearest decoupling capacitor pad, maximum (mm) | 2.552 | n/a | measured - human review required | 14->C59.1 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U12 supply pads ['1'] to nearest decoupling capacitor pad, maximum (mm) | 4.819 | n/a | measured - human review required | 1->C56.1 4.82 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U13 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 2.528 | n/a | measured - human review required | 8->C61.1 2.53 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U14 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 3.888 | n/a | measured - human review required | 8->C50.1 3.89 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U15 supply pads ['1'] to nearest decoupling capacitor pad, maximum (mm) | 4.275 | n/a | measured - human review required | 1->C55.1 4.28 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | Y1 supply pads ['1', '4'] to nearest decoupling capacitor pad, maximum (mm) | 5.025 | n/a | measured - human review required | 1->C34.1 5.03; 4->C49.1 3.96 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U5 bypass capacitors (26 from the model near_dsp_pin) maximum pad distance (mm) | 5.849 | <= 5.0 mm | exceeds spec threshold - human review required |  |
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
| U5 | 9 | 3V3 | C18.1 | 5.050 | yes |
| U5 | 15 | 1V9 | C19.1 | 3.908 | yes |
| U5 | 23 | 1V9 | C20.1 | 3.908 | yes |
| U5 | 29 | 1V9 | C21.1 | 3.908 | yes |
| U5 | 31 | 1V9 | C21.1 | 4.095 | yes |
| U5 | 34 | 3V3 | C23.1 | 5.050 | yes |
| U5 | 45 | 3V3 | C24.1 | 5.050 | yes |
| U5 | 59 | 1V9 | C25.1 | 4.675 | yes |
| U5 | 61 | 1V9 | C26.1 | 4.383 | yes |
| U5 | 71 | 3V3 | C27.1 | 5.050 | yes |
| U5 | 84 | 3V3 | C28.1 | 5.050 | yes |
| U5 | 93 | 3V3 | C29.1 | 5.050 | yes |
| U5 | 101 | 1V9 | C30.1 | 3.900 | yes |
| U5 | 107 | 3V3 | C31.1 | 5.050 | yes |
| U5 | 109 | 1V9 | C32.1 | 3.900 | yes |
| U5 | 117 | 1V9 | C33.1 | 3.900 | yes |
| U5 | 121 | 3V3 | C34.1 | 5.050 | yes |
| U5 | 126 | 1V9 | C35.1 | 3.900 | yes |
| U5 | 139 | 1V9 | C35.1 | 5.030 | yes |
| U5 | 143 | 3V3 | C37.1 | 5.849 | yes |
| U5 | 146 | 1V9 | C36.1 | 3.900 | yes |
| U5 | 154 | 1V9 | C39.1 | 3.932 | yes |
| U5 | 159 | 3V3 | C40.1 | 5.050 | yes |
| U5 | 167 | 1V9 | C41.1 | 4.383 | yes |
| U5 | 170 | 3V3 | C42.1 | 5.050 | yes |
| U1 | 1 | 12V_IN | C1.1 | 3.725 | yes |
| U1 | 2 | 12V_IN | C1.1 | 3.781 | yes |
| U1 | 15 | 12V_PROT | C4.1 | 8.182 | yes |
| U1 | 16 | 12V_PROT | C4.1 | 8.830 | yes |
| U2 | 3 | 12V_PROT | C3.1 | 6.845 | yes |
| U3 | 5 | 5V | C7.1 | 7.308 | yes |
| U3 | 6 | 5V | C7.1 | 6.912 | yes |
| U3 | 11 | 5V | C7.1 | 5.687 | yes |
| U3 | 12 | 5V | C7.1 | 5.638 | yes |
| U3 | 17 | 3V3 | C37.1 | 5.811 | yes |
| U3 | 18 | 3V3 | C37.1 | 6.460 | yes |
| U3 | 23 | 1V9 | C43.1 | 4.929 | yes |
| U3 | 24 | 1V9 | C43.1 | 4.769 | yes |
| U4 | 6 | 3V3 | C16.1 | 5.865 | yes |
| U6 | 8 | 3V3 | C58.1 | 2.526 | yes |
| U7 | 2 | 3V3 | C57.1 | 4.670 | yes |
| U7 | 7 | 3V3 | C57.1 | 3.175 | yes |
| U7 | 8 | 3V3 | C57.1 | 2.525 | yes |
| U8 | 14 | 3V3 | C62.1 | 2.551 | yes |
| U9 | 14 | 3V3 | C60.1 | 2.551 | yes |
| U10 | 12 | 3V3 | C18.1 | 8.748 | yes |
| U10 | 13 | 3V3 | C58.1 | 8.232 | yes |
| U10 | 14 | 3V3 | C58.1 | 7.628 | yes |
| U11 | 14 | 3V3 | C59.1 | 2.551 | yes |
| U12 | 1 | 3V3 | C56.1 | 4.819 | yes |
| U13 | 8 | 3V3 | C61.1 | 2.527 | yes |
| U14 | 8 | 3V3 | C50.1 | 3.888 | yes |
| U15 | 1 | 3V3 | C55.1 | 4.276 | yes |
| Y1 | 1 | 3V3 | C34.1 | 5.025 | yes |
| Y1 | 4 | 3V3 | C49.1 | 3.962 | yes |

## Sensing

| Pair | Nets | Track (mm) | Vias | Mismatch (mm) | Min to SW (mm) |
| --- | --- | --- | --- | --- | --- |
| ISENSE / ISENSE_REF from the mezzanine (J8 pins 43/45) to the ADC front ends | ISENSE, ISENSE_REF | ISENSE=80.17; ISENSE_REF=56.55 | ISENSE=4; ISENSE_REF=2 | 23.625 | n/a |

## Control section

Control parts: 46, power parts: 33, bounding-box separation 0.000 mm, overlap 1928.2 mm2.

| Ground layer | Area (mm2) | Islands | Zones | Required probes covered | Forbidden probes copper-free |
| --- | --- | --- | --- | --- | --- |
| In1.Cu | 8512.7 | 1 | 1 | 4/4 | 0/0 |

DSP bypass capacitors: 26, maximum pad distance 5.849 mm.

## Compactness

| Metric | Value |
| --- | --- |
| Board area (mm2 / dm2) | 9600.0 / 0.960 |
| Footprints per dm2 | 215.6 |
| Courtyard fraction front / back | 0.341 / 0.007 |
| HV bounding-box fraction of board | n/a |
| HV copper on outer layers (mm2, fraction of both sides) | 0 (0.000) |
| Tallest component | J1 12.0 mm |
| Assembly height (mm) declared / computed / used | n/a, 13.6, 13.6 |
| Rated power (W) | n/a |
| Power density (W/dm2, W/L) | n/a, n/a |

## Classified nets

| Net | Class | Track (mm) | Tracks | Vias | Pads | Layers | Zone area (mm2) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12V_IN | CTRL_PWR | 62.0 | 42 | 6 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_PROT | CTRL_PWR | 14.9 | 21 | 10 | 13 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=1469.400 |
| 1V9 | CTRL_SELV | 50.0 | 61 | 37 | 37 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=759.100 |
| 1V9_BULK | CTRL_SELV | 19.2 | 8 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 3V3 | CTRL_SELV | 119.6 | 183 | 84 | 89 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=5422.100 |
| 3V3_BULK | CTRL_SELV | 10.5 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 5V | CTRL_PWR | 24.2 | 44 | 15 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=610.900 |
| 5V_BST | CTRL_SELV | 16.7 | 13 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 5V_EN | CTRL_SELV | 24.9 | 35 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 5V_FB | CTRL_SELV | 44.1 | 26 | 5 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 5V_SW | CTRL_PWR | 18.0 | 10 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADCREFM | CTRL_ANALOG | 11.0 | 15 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADCREFP | CTRL_ANALOG | 10.1 | 11 | 0 | 2 | F.Cu |  |
| ADCRESEXT | CTRL_ANALOG | 18.4 | 26 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_I12V | CTRL_ANALOG | 33.6 | 27 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_ISENSE | CTRL_ANALOG | 42.0 | 41 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_ISENSE_REF | CTRL_ANALOG | 45.4 | 70 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_TEMP_CTRL | CTRL_ANALOG | 48.5 | 33 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_TEMP_HS | CTRL_ANALOG | 0.1 | 2 | 0 | 3 | F.Cu |  |
| ADC_V12V | CTRL_ANALOG | 33.2 | 42 | 5 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_VIN | CTRL_ANALOG | 34.6 | 37 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_VOUT | CTRL_ANALOG | 42.5 | 28 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ARM | CTRL_SELV | 61.4 | 69 | 6 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BIAS_EN | CTRL_SELV | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BOOT84 | CTRL_SELV | 27.9 | 20 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BOOT85 | CTRL_SELV | 17.5 | 15 | 0 | 2 | F.Cu |  |
| BOOT86 | CTRL_SELV | 16.6 | 13 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BOOT87 | CTRL_SELV | 0.1 | 1 | 0 | 2 | F.Cu |  |
| CLK30 | CTRL_SELV | 11.6 | 19 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| CLK30_SOURCE | CTRL_SELV | 12.3 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| CORE_OK | CTRL_SELV | 66.1 | 38 | 5 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DSP_TRIP_N | CTRL_SELV | 32.2 | 26 | 5 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_DVDT | CTRL_SELV | 6.5 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_ILIM | CTRL_SELV | 39.5 | 13 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_OVP | CTRL_SELV | 43.7 | 54 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_RTN | CTRL_PWR | 67.2 | 71 | 8 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_SHDN | CTRL_SELV | 35.3 | 11 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EFUSE_UVLO | CTRL_SELV | 36.5 | 14 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EMU0 | CTRL_SELV | 50.7 | 67 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EMU1 | CTRL_SELV | 100.4 | 46 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EPWM1A | CTRL_SELV | 34.0 | 27 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EPWM1B | CTRL_SELV | 23.2 | 22 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ESTOP_N | CTRL_SELV | 168.8 | 119 | 11 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAN_TACH | CTRL_SELV | 207.2 | 162 | 13 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAULT_LATCH_N | CTRL_SELV | 56.9 | 28 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAULT_N | CTRL_SELV | 133.8 | 75 | 5 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FB19 | CTRL_SELV | 45.1 | 18 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_12V_N | CTRL_SELV | 139.2 | 129 | 6 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_H_N | CTRL_SELV | 0.1 | 2 | 0 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_L_N | CTRL_SELV | 0.1 | 2 | 0 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G1_N | CTRL_SELV | 0.1 | 2 | 0 | 2 | F.Cu |  |
| G2_N | CTRL_SELV | 9.7 | 7 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G3_N | CTRL_SELV | 19.7 | 26 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GATE_EN | CTRL_SELV | 41.6 | 22 | 5 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GND_CTRL | CTRL_SELV | 213.9 | 270 | 154 | 188 | F.Cu, In1.Cu, In2.Cu, B.Cu | In1.Cu=8512.700 |
| I12V_MON | CTRL_SELV | 121.5 | 62 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| IO_EN_N | CTRL_SELV | 42.6 | 13 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISENSE | CTRL_ANALOG | 80.2 | 71 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISENSE_REF | CTRL_ANALOG | 56.5 | 68 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_12V_A | CTRL_SELV | 5.0 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_ARMED_A | CTRL_SELV | 24.7 | 22 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_FAULT | CTRL_SELV | 28.2 | 61 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_FAULT_A | CTRL_SELV | 34.0 | 17 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_RUN | CTRL_SELV | 27.4 | 33 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LED_RUN_A | CTRL_SELV | 24.5 | 17 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| MON5 | CTRL_SELV | 27.1 | 16 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| MR_N | CTRL_SELV | 8.4 | 4 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_N | CTRL_SELV | 57.9 | 30 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OTP_N | CTRL_SELV | 0.1 | 3 | 0 | 4 | F.Cu |  |
| OTP_REF | CTRL_ANALOG | 51.9 | 68 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OVP_IN_N | CTRL_SELV | 20.3 | 17 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OVP_IN_REF | CTRL_ANALOG | 22.2 | 24 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OVP_N | CTRL_SELV | 0.1 | 1 | 0 | 2 | F.Cu |  |
| OVP_OUT_N | CTRL_SELV | 59.2 | 67 | 6 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OVP_OUT_REF | CTRL_ANALOG | 39.8 | 34 | 7 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_H_N | CTRL_SELV | 73.7 | 72 | 9 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_H_OK | CTRL_SELV | 0.0 | 2 | 0 | 2 | F.Cu |  |
| PG_BIAS_L_N | CTRL_SELV | 126.9 | 173 | 8 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_L_OK | CTRL_SELV | 0.1 | 2 | 0 | 2 | F.Cu |  |
| PG_BIAS_S_N | CTRL_SELV | 0.1 | 2 | 0 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_S_OK | CTRL_SELV | 0.1 | 2 | 0 | 2 | F.Cu |  |
| PWM_H | CTRL_SELV | 16.8 | 7 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_H_G | CTRL_SELV | 15.9 | 12 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_L | CTRL_SELV | 22.7 | 18 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_L_G | CTRL_SELV | 17.4 | 28 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_H | CTRL_SELV | 0.1 | 2 | 0 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_L | CTRL_SELV | 0.1 | 2 | 0 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| REF2V5 | CTRL_ANALOG | 34.5 | 43 | 5 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| REF3V0 | CTRL_ANALOG | 19.7 | 15 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RELAY_ON | CTRL_SELV | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RESET_CT | CTRL_SELV | 5.5 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RESET_N | CTRL_SELV | 59.7 | 69 | 5 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SEQ_BASE | CTRL_SELV | 14.1 | 9 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SPARE_D1 | CTRL_SELV | 85.0 | 44 | 5 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SPARE_D2 | CTRL_SELV | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TCK | CTRL_SELV | 45.2 | 38 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TDI | CTRL_SELV | 81.0 | 99 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TDO | CTRL_SELV | 44.0 | 60 | 3 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_CTRL | CTRL_ANALOG | 19.5 | 12 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_HS_NTC | CTRL_ANALOG | 44.9 | 41 | 5 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TMS | CTRL_SELV | 36.2 | 62 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TRST | CTRL_SELV | 73.9 | 59 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UART_RX | CTRL_SELV | 46.1 | 19 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UART_TX | CTRL_SELV | 114.1 | 65 | 10 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UVLO | CTRL_SELV | 86.4 | 83 | 7 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UVLO_N | CTRL_SELV | 51.4 | 44 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| UVLO_REF | CTRL_ANALOG | 39.2 | 53 | 5 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| V12V_MON | CTRL_SELV | 115.7 | 47 | 5 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_SENSE | CTRL_ANALOG | 80.3 | 66 | 7 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_SENSE | CTRL_ANALOG | 84.7 | 75 | 5 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| XRS_N | CTRL_SELV | 0.3 | 5 | 0 | 7 | F.Cu |  |
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
