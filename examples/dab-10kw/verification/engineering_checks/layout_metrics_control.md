# Layout metrics - AIPE 10 kW DAB - control board (TMS320F280039C controlCARD) - layout metrics spec (derived from requirements)

Status: **measured-human-review-required**. Generated 2026-10-21T07:22:51.375344+00:00 by `automation/verification/check_sic_layout.py` (pcbnew 10.0.6, distance backend numpy, 0.156 s).

Board `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\control\dab-control.kicad_pcb` (sha256 `baffe51c611330f4...`), spec `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\verification\engineering_checks\layout_spec_control.json`, model `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\design\circuit_control.json`.

## Board

| Metric | Value |
| --- | --- |
| Outline (mm) | 160.00 x 120.00 |
| Outline area (mm2) | 19200.0 |
| Copper layers | 4 (F.Cu, In1.Cu, In2.Cu, B.Cu) |
| Thickness (mm) | 1.600 |
| Copper thickness (um, stackup text) | F.Cu=35.000; In1.Cu=35.000; In2.Cu=35.000; B.Cu=35.000 |
| Footprints / tracks / vias / zones / rule areas | 224 / 0 / 0 / 0 / 0 |
| Nets | 298 |
| Zones without fill (areas read from the file) | none |
| Expected (spec) | outline_mm=160, 120; copper_layers=4; copper_um=35; thickness_mm=1.600 |

## Rule table

Dispositions follow the spec thresholds only; every row needs engineering acceptance by a human reviewer.

| Rule | Requirement | Metric | Measured | Threshold | Disposition | Note |
| --- | --- | --- | --- | --- | --- | --- |
| PE-PCB-001 | Minimise MOSFET gate loop | driver output to gate pad distance | n/a | n/a | not measured - spec input missing or reference not found | no gate_loops in the spec |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | HF capacitor to device pin distance | n/a | n/a | not measured - spec input missing or reference not found | no commutation section in the spec |
| PE-PCB-003 | Minimise HF commutation loop | commutation loop proxies | n/a | n/a | not measured - spec input missing or reference not found | no commutation section in the spec |
| PE-PCB-004 | Use Kelvin current sensing | Kelvin sense pair length match | n/a | n/a | not measured - spec input missing or reference not found | no sensing.kelvin_pairs in the spec |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | sensing versus switch node distance | n/a | n/a | not measured - spec input missing or reference not found | no sensing section in the spec |
| PE-PCB-006 | Justify high-current copper and via capacity | HV net copper | n/a | n/a | not measured - spec input missing or reference not found | no HV net classes in the spec |
| PE-PCB-007 | Separate control and switching structures | control section versus power stage separation | n/a | n/a | not measured - spec input missing or reference not found | no control section in the spec |
| PE-PCB-007 | Separate control and switching structures | board area (mm2), footprints per dm2, courtyard fraction front/back | area=19200.000; per_dm2=116.700; courtyard=front=0.231; back=0.000 | n/a | measured - human review required | HV bbox fraction n/a; power density n/a W/dm2, n/a W/L |
| PE-PCB-008 | Place decoupling adjacent to supply pins | supply pad to decoupling capacitor distance | n/a | n/a | not measured - spec input missing or reference not found | no decoupling entries in the spec |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | Kelvin-source versus power-source separation | n/a | n/a | not measured - spec input missing or reference not found | no gate_loops in the spec |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | barrier strip copper check | n/a | n/a | not measured - spec input missing or reference not found | no barrier_keepouts in the spec |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | net-class pair copper distances | n/a | n/a | not measured - spec input missing or reference not found | no isolation pairs in the spec |
| KR-ISO-004 | Slots and cut-outs to extend creepage | slots under barrier parts | n/a | n/a | not measured - spec input missing or reference not found | no barrier_parts in the spec |
| KR-TH-002 | Rated insulating interface for shared heat sinks (HV copper keep-out at the sink) | HV copper distance to the heatsink envelope | n/a | n/a | not measured - spec input missing or reference not found | heatsink ref missing or not on the board |

Rows: 14 - within spec threshold 0, exceeding 0, measured without threshold 1, not measured 13.

## Compactness

| Metric | Value |
| --- | --- |
| Board area (mm2 / dm2) | 19200.0 / 1.920 |
| Footprints per dm2 | 116.7 |
| Courtyard fraction front / back | 0.231 / 0.000 |
| HV bounding-box fraction of board | n/a |
| HV copper on outer layers (mm2, fraction of both sides) | 0 (0.000) |
| Tallest component | U9 0.0 mm |
| Assembly height (mm) declared / computed / used | n/a, 1.6, 1.6 |
| Rated power (W) | n/a |
| Power density (W/dm2, W/L) | n/a, n/a |

## Classified nets

| Net | Class | Track (mm) | Tracks | Vias | Pads | Layers | Zone area (mm2) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12V_E | CTRL_POWER | 0.0 | 0 | 0 | 14 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_IN | CTRL_POWER | 0.0 | 0 | 0 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 3V3 | CTRL_POWER | 0.0 | 0 | 0 | 61 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 5V0 | CTRL_POWER | 0.0 | 0 | 0 | 27 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ADC_5V | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| ADC_ITANK_P | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| ADC_ITANK_S | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| ADC_TEMP_P | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| ADC_TEMP_S | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| ADC_V12 | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| ADC_VBUS_P | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| ADC_VBUS_S | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| ALL_GOOD | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| ARM | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| ARMED | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| AUX_FLT_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| BIAS_EN | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BIAS_EN_MCU | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| BST5 | CTRL_POWER | 0.0 | 0 | 0 | 2 | F.Cu |  |
| CANH | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| CANL | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| CAN_MID | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| CAN_RX | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| CAN_TX | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| DRIVERS_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| DRV_RST | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DRV_RST_MCU | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| EMU0 | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EMU1 | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| EN5 | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| EPWM1A | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| EPWM1B | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| EPWM2A | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| EPWM2B | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| EPWM3A | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| EPWM3B | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| EPWM4A | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| EPWM4B | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| E_DVDT | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| E_EN | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| E_ILIM | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| E_IMON | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| E_OV | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| E_RTN | CTRL_SIGNAL | 0.0 | 0 | 0 | 6 | F.Cu |  |
| E_UV | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| FAULT_RD | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| FB5 | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| FLT_P_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| FLT_S_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| GND_CTRL | CTRL_POWER | 0.0 | 0 | 0 | 169 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GPIO_LED_RUN | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| LED_FAULT_K | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| LED_PWR_K | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| LED_RUN_K | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| MON3V3 | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| MR_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NRST | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| OV_P_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| OV_S_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| PG_P_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| PG_S_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| PROT_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| PWM_ENABLE | CTRL_SIGNAL | 0.0 | 0 | 0 | 10 | F.Cu |  |
| P_FLT_AH_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_FLT_AL_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_FLT_BH_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_FLT_BL_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_ISNS | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_ISNS_BUF | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| P_OC_TRIP_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_PG_BIAS_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_PWM_AH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_PWM_AH_SRC | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| P_PWM_AL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_PWM_AL_SRC | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| P_PWM_BH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_PWM_BH_SRC | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| P_PWM_BL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_PWM_BL_SRC | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| P_RDY_AH | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_RDY_AL | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_RDY_BH | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_RDY_BL | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_SDFM_CLK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_SDFM_D | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_TEMP_HS | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_TEMP_PWM_AH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_TEMP_PWM_AL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_TEMP_PWM_BH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_TEMP_PWM_BL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_VA | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| P_VBUS_CMP | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| P_VBUS_RX | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| P_VM | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| P_VSNS_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| P_VSNS_P | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_P_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| RDY_S_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| REF3 | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| RESET_CT | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| RS485_A | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RS485_B | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RS485_DE | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| RS485_RX | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| RS485_TX | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| RUN_EN | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| SDFM_P_CLK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| SDFM_P_D | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| SDFM_S_CLK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| SDFM_S_D | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| SUPPLY_OK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| SW5 | CTRL_POWER | 0.0 | 0 | 0 | 3 | F.Cu |  |
| S_FLT_AH_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_FLT_AL_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_FLT_BH_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_FLT_BL_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_ISNS | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_ISNS_BUF | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| S_OC_TRIP_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_PG_BIAS_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_PWM_AH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_PWM_AH_SRC | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| S_PWM_AL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_PWM_AL_SRC | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| S_PWM_BH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_PWM_BH_SRC | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| S_PWM_BL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_PWM_BL_SRC | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| S_RDY_AH | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_RDY_AL | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_RDY_BH | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_RDY_BL | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_SDFM_CLK | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_SDFM_D | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_TEMP_HS | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_TEMP_PWM_AH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_TEMP_PWM_AL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_TEMP_PWM_BH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_TEMP_PWM_BL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_VA | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| S_VBUS_CMP | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| S_VBUS_RX | CTRL_SIGNAL | 0.0 | 0 | 0 | 5 | F.Cu |  |
| S_VM | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| S_VSNS_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_VSNS_P | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TCK | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TDI | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TDO | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_PWM_P_AH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| TEMP_PWM_P_AL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| TEMP_PWM_P_BH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| TEMP_PWM_P_BL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| TEMP_PWM_S_AH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| TEMP_PWM_S_AL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| TEMP_PWM_S_BH | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| TEMP_PWM_S_BL | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| TMS | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TRIPPED | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| TRST_N | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TZ_TRIP | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |
| V12_DIV | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| V5_DIV | CTRL_SIGNAL | 0.0 | 0 | 0 | 3 | F.Cu |  |
| V_OV_P | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| V_OV_S | CTRL_SIGNAL | 0.0 | 0 | 0 | 4 | F.Cu |  |
| XRS_CARD | CTRL_SIGNAL | 0.0 | 0 | 0 | 2 | F.Cu |  |

## Notes and limitations

- Straight-line pad distances, track sums and copper areas are geometric proxies; they are not loop inductance, current-path length, creepage per standard or EMI performance.
- Isolation distances are copper-to-copper on each layer (pads, tracks, vias, filled zones); through-air clearance between layers, component bodies, solder mask and coatings are not evaluated.
- Thresholds are those given in the layout spec (taken from the design baseline); no acceptance limit is invented here. Engineering acceptance of every row remains a human responsibility.
- Slot detection relies on non-plated oblong pads or Edge.Cuts graphics inside the barrier part courtyard; the fabricator must confirm the slot width after tolerance.
- Generated by automation.dab_v1.verify from the requirement files; thresholds are the unverified design targets of specification.yaml.
