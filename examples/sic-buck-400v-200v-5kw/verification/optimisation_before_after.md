**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# Layout-review corrections - measured before / after

Generated 2026-10-10T16:48:06.649288+00:00 by `automation/scripts/optimisation_report_sic.py` from the board files (pcbnew 10), the kicad-cli DRC manifests and the layout-metrics checker. "Before" is the reviewed control board (`verification/layout_review_findings.json`, sha256 `119d37df1b737fd7...`); "after" is the current board. Only the DRC manifests are verification; every other figure is CAD geometry.

## Control board

| Metric | Before (reviewed board) | After |
|---|---|---|
| Board sha256 | 119d37df1b737fd7... | 68c3558fb0353dc1... |
| Outline (mm) | [120.05, 80.05] | [120.05, 80.05] |
| Footprints / on B.Cu | 207 / 15 | 207 / 16 |
| Tracks / vias / zones | 4151 / 642 / 16 | 5858 / 784 / 20 |
| Total track length (mm) | 4628.8 | 6674.5 |
| DRC violations / unconnected / parity | 0 / 39 / 0 | 0 / 1 / 0 |
| DRC manifest | verification/drc/20261010T104013Z-drc-7a5fd84b/run.json | verification/drc/20261010T144718Z-drc-6798d486/run.json |
| Router unresolved connections | 39 (recorded) | 1 |
| J8 mezzanine header side (LR-03) | F.Cu | B.Cu |
| J8 pin 1 / pin 50 (mm) | [28.0, 76.0] / [88.96, 73.46] | [28.0, 74.0] / [88.96, 76.54] |
| ADC 1 nF filter: DSP pin to capacitor pad, max (mm) (LR-04) | 17.27 | 14.75 |
| ADCREFM/P capacitors to pins (mm) | {'U5.55->C47': 7.38, 'U5.56->C48': 7.87} | {'U5.55->C47': 4.88, 'U5.56->C48': 5.6} |
| U2 VIN pad to C4.1 / C5.1 (mm) (LR-05) | 21.24 / 17.7 | 4.23 / 2.04 |
| 5V_SW segments / vias / layers (LR-05) | 10 / 3 / ['B.Cu', 'F.Cu'] | 4 / 0 / ['F.Cu'] |
| 5V_SW track length (mm) / min width (mm) | 17.96 / 0.4 | 14.35 / 0.5 |
| C6 (bootstrap) pad 2 to U2.2 (mm) | 10.0 | 3.57 |
| Exposed-pad vias U1.17 / U3.29 (LR-06) | 1 / 1 | 8 / 8 |
| 12V_IN tracks: min-max width (mm) / vias (LR-07) | 0.4-0.4 / 6 | 0.5-1.0 / 0 |
| 12V_PROT tracks: min-max width (mm) / vias | 0.3-0.3 / 10 | 0.4-1.0 / 11 |
| EFUSE_RTN / 5V max track width (mm) | 0.4 / 0.3 | 0.4 / 0.4 |
| J4 / J5 distance to the nearer board edge (mm) (LR-09) | {'J4': 44.0, 'J5': 44.0} | {'J4': 4.5, 'J5': 4.5} |
| DSP bypass pin-to-capacitor max / mean (mm) (LR-13) | 5.849 / 4.571 | 5.381 / 4.402 |
| Y1 centre / Y1 pad 3 to XCLKIN (mm) (LR-16) | 13.02 / 14.4 | 11.06 / 8.86 |
| ISENSE / ISENSE_REF track (mm), mismatch (LR-14) | {'ISENSE': 80.2, 'ISENSE_REF': 56.5, 'mismatch': 23.7} | {'ISENSE': 105.2, 'ISENSE_REF': 89.0, 'mismatch': 16.2} |
| PWM / TZ track lengths (mm) | {'EPWM1A': 34.0, 'PWM_H_G': 15.9, 'PWM_H': 16.8, 'EPWM1B': 23.2, 'PWM_L_G': 17.4, 'PWM_L': 22.7, 'FAULT_N': 133.8, 'OC_N': 57.9} | {'EPWM1A': 50.0, 'PWM_H_G': 11.1, 'PWM_H': 15.3, 'EPWM1B': 42.9, 'PWM_L_G': 8.9, 'PWM_L': 26.7, 'FAULT_N': 248.2, 'OC_N': 97.1} |
| GND_CTRL In1.Cu area (mm2) / outlines | 8512.7 / 1 | 8388.6 / 1 |
| Zone-fill slivers < 0.01 mm2 (LR-15) | 7 | 9 |
| Min track/via copper to board edge (mm) | 2.65 | 1.2 |

ADC filter capacitor distances per pin (mm):

| Pin -> capacitor | Before | After |
|---|---|---|
| U5.38->C72 | 17.27 | 14.75 |
| U5.39->C71 | 13.11 | 10.35 |
| U5.40->C70 | 12.21 | 9.41 |
| U5.41->C69 | 11.33 | 8.48 |
| U5.42->C68 | 10.48 | 6.83 |
| U5.46->C73 | 12.96 | 9.84 |
| U5.47->C74 | 12.33 | 9.67 |
| U5.49->C75 | 13.25 | 10.42 |

Open connections after the corrections (router record, confirmed by the DRC unconnected count): BIAS_EN.


Routing-order trials of the final run (grid router, same placement; the best was kept):

| Trial | Order | Unresolved | Track (mm) |
|---|---|---|---|
| 0 | plan | 43 | 5254.3 |
| 1 | span_asc | 11 | 6043.8 |
| 2 | span_desc | 40 | 5575.3 |
| 3 | priority_span_asc | 43 | 5253.5 |
| 4 | perturb_4 | 22 | 5739.0 |
| 5 | perturb_5 | 26 | 5939.0 |

### Checker rows that changed value or disposition

| Rule | metric | Before | Disp. | After | Disp. |
|---|---|---|---|---|
| PE-PCB-004 | ISENSE / ISENSE_REF from the mezzanine (J8 pins 43/45) to the ADC fron | {'ISENSE': 80.175, 'ISENSE_REF': 56.55, 'mismatch': 23.625} | measured - human revie | {'ISENSE': 105.175, 'ISENSE_REF': 89.05, 'mismatch': 16.125} | measured - human revie |
| PE-PCB-007 | GND_CTRL zone area (mm2) and island count per layer | {'In1.Cu': {'area': 8512.7, 'islands': 1}} | within spec threshold  | {'In1.Cu': {'area': 8388.6, 'islands': 1}} | within spec threshold  |
| PE-PCB-007 | board area (mm2), footprints per dm2, courtyard fraction front/back | {'area': 9600.0, 'per_dm2': 215.6, 'courtyard': {'front': 0. | within spec threshold  | {'area': 9600.0, 'per_dm2': 215.6, 'courtyard': {'front': 0. | within spec threshold  |
| PE-PCB-008 | U5 supply pads ['4', '9', '15', '23', '29', '31', '34', '45', '59', '6 | 5.849 | exceeds spec threshold | 5.381 | exceeds spec threshold |
| PE-PCB-008 | U1 supply pads ['1', '2', '15', '16'] to nearest decoupling capacitor  | 8.83 | measured - human revie | 22.763 | measured - human revie |
| PE-PCB-008 | U2 supply pads ['3'] to nearest decoupling capacitor pad, maximum (mm) | 6.845 | measured - human revie | 2.038 | measured - human revie |
| PE-PCB-008 | U3 supply pads ['5', '6', '11', '12', '17', '18', '23', '24'] to neare | 7.308 | measured - human revie | 8.025 | measured - human revie |
| PE-PCB-008 | U4 supply pads ['6'] to nearest decoupling capacitor pad, maximum (mm) | 5.865 | measured - human revie | 26.504 | measured - human revie |
| PE-PCB-008 | U6 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 2.526 | measured - human revie | 2.579 | measured - human revie |
| PE-PCB-008 | U7 supply pads ['2', '7', '8'] to nearest decoupling capacitor pad, ma | 4.67 | measured - human revie | 6.958 | measured - human revie |
| PE-PCB-008 | U8 supply pads ['14'] to nearest decoupling capacitor pad, maximum (mm | 2.552 | measured - human revie | 10.393 | measured - human revie |
| PE-PCB-008 | U10 supply pads ['12', '13', '14'] to nearest decoupling capacitor pad | 8.748 | measured - human revie | 7.203 | measured - human revie |
| PE-PCB-008 | U11 supply pads ['14'] to nearest decoupling capacitor pad, maximum (m | 2.552 | measured - human revie | 9.588 | measured - human revie |
| PE-PCB-008 | U12 supply pads ['1'] to nearest decoupling capacitor pad, maximum (mm | 4.819 | measured - human revie | 4.731 | measured - human revie |
| PE-PCB-008 | U13 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm | 2.528 | measured - human revie | 3.888 | measured - human revie |
| PE-PCB-008 | U14 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm | 3.888 | measured - human revie | 3.613 | measured - human revie |
| PE-PCB-008 | Y1 supply pads ['1', '4'] to nearest decoupling capacitor pad, maximum | 5.025 | measured - human revie | 3.96 | measured - human revie |
| PE-PCB-008 | U5 bypass capacitors (26 from the model near_dsp_pin) maximum pad dist | 5.849 | exceeds spec threshold | 5.381 | exceeds spec threshold |

## Power board

| Metric | Before (review) | After |
|---|---|---|
| Board | absent (LR-01) | `kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` sha256 378ead6bdd14b6ef... |
| Outline (mm) | - | [240.05, 180.05] |
| Footprints / on B.Cu | - | 237 / 49 |
| Tracks / vias (1.2 mm HV vias) / zones (rule areas) | - | 3624 / 548 (126) / 33 (12) |
| Total track length (mm) | - | 3925.0 |
| DRC violations / unconnected / parity | no DRC | 284 / 183 / 0 |
| DRC manifest | - | verification/drc/20261010T164654Z-drc-ccea4530/run.json |
| DRC violation types | - | ['clearance', 'isolated_copper', 'items_not_allowed', 'silk_edge_clearance', 'track_dangling', 'via_dangling'] |
| Router unresolved connections | - | 174 |
| Barrier-part line y (mm) | - | [145.0] |
| Key positions (mm) | - | {'HS1': (99.25, 67.0), 'Q1': (87.0, 126.0), 'Q2': (115.0, 126.0), 'L1': (204.5, 95.0), 'U1': (96.0, 145.0), 'U2': (111.5, 145.0), 'U3': (130.0, 145.0), 'U4': (150.0, 145.0), 'U5': (170.0, 145.0), 'U6': (185.5, 145.0), 'U7': (197.5, 145.0), 'U10': (212.0, 145.0), 'J7': (211.0, 160.0), 'C11': (14.95, 33.0), 'C12': (14.95, 77.0), 'C13': (185.5, 23.5), 'C14': (217.5, 23.5)} |
| Checker summary | no metrics | {'rows': 58, 'within_threshold': 17, 'exceeding_threshold': 16, 'measured_only': 25, 'not_measured': 0} |

Checker rows (power spec, corrected per LR-08):

| Rule | metric | Measured | Disposition |
|---|---|---|
| PE-PCB-001 | U1 output pad 4 to Q1 gate pad 4 | 14.36 | within spec threshold - human review req |
| PE-PCB-001 | G_H/HS_OUTH/HS_OUTL/HS_CLMP track length (mm), layers ['F.Cu', 'In1.Cu | {'track_mm': 42.85, 'adjacent': True, 'over_kelvin_pour': 0.829} | measured - human review required |
| PE-PCB-001 | U3 output pad 6 to Q2 gate pad 4 | 14.647 | within spec threshold - human review req |
| PE-PCB-001 | G_L/LS_OUTH/LS_OUTL/LS_CLMP track length (mm), layers ['F.Cu', 'In1.Cu | {'track_mm': 74.15, 'adjacent': True, 'over_kelvin_pour': 0.77} | measured - human review required |
| PE-PCB-002 | Q1 drain pad 1 (VIN) to nearest HF capacitor pad of the same net | 8.013 | within spec threshold - human review req |
| PE-PCB-002 | Q1 source pad 2 (SW) to nearest HF capacitor pad (any named net) | 13.088 | measured - human review required |
| PE-PCB-002 | Q2 drain pad 1 (SW) to nearest HF capacitor pad (any named net) | 36.003 | measured - human review required |
| PE-PCB-002 | Q2 source pad 2 (PGND) to nearest HF capacitor pad of the same net | 41.453 | exceeds spec threshold - human review re |
| PE-PCB-003 | SW copper area, all layers (mm2; per layer in JSON) | 2350.2 | measured - human review required |
| PE-PCB-003 | HV ceramic group bounding box (x0, y0, x1, y1 mm) and pin distances (J | [39.1, 125.55, 81.7, 139.95] | measured - human review required |
| PE-PCB-004 | AMC1311 VIN differential output track lengths (mm) and mismatch | {'VIN_OUTP': 25.601, 'VIN_OUTN': 32.351, 'mismatch': 6.75} | measured - human review required |
| PE-PCB-004 | AMC1311 VOUT differential output track lengths (mm) and mismatch | {'VOUT_OUTP': 21.101, 'VOUT_OUTN': 30.351, 'mismatch': 9.25} | measured - human review required |
| PE-PCB-004 | TMCS1133 ISENSE / ISENSE_REF track lengths (mm) and mismatch | {'ISENSE': 80.01, 'ISENSE_REF': 70.25, 'mismatch': 9.76} | measured - human review required |
| PE-PCB-005 | AMC1311 VIN differential output minimum copper distance to SW (mm, any | 36.05 | measured - human review required |
| PE-PCB-005 | AMC1311 VOUT differential output minimum copper distance to SW (mm, an | 36.077 | measured - human review required |
| PE-PCB-005 | TMCS1133 ISENSE / ISENSE_REF minimum copper distance to SW (mm, any la | 37.354 | measured - human review required |
| PE-PCB-005 | U6 pads: minimum copper distance to SW (mm, any layer) | 25.15 | measured - human review required |
| PE-PCB-005 | U7 pads: minimum copper distance to SW (mm, any layer) | 25.15 | measured - human review required |
| PE-PCB-005 | U10 pads: minimum copper distance to SW (mm, any layer) | 27.345 | measured - human review required |
| PE-PCB-005 | U8 pads: minimum copper distance to SW (mm, any layer) | 42.475 | measured - human review required |
| PE-PCB-006 | VIN copper (zone area per layer, via count, track length) | {'zone_area_mm2': {'F.Cu': 5835.6, 'In2.Cu': 22411.6}, 'vias': 36, 'track_mm': 0.0} | within spec threshold - human review req |
| PE-PCB-006 | VIN_RAW copper (zone area per layer, via count, track length) | {'zone_area_mm2': {'F.Cu': 475.2, 'B.Cu': 475.2}, 'vias': 0, 'track_mm': 0.0} | exceeds spec threshold - human review re |
| PE-PCB-006 | SW copper (zone area per layer, via count, track length) | {'zone_area_mm2': {'F.Cu': 185.8, 'In2.Cu': 1898.8}, 'vias': 18, 'track_mm': 0.0} | exceeds spec threshold - human review re |
| PE-PCB-006 | PGND copper (zone area per layer, via count, track length) | {'zone_area_mm2': {'B.Cu': 10560.2, 'In1.Cu': 30624.8}, 'vias': 36, 'track_mm': 22.5} | within spec threshold - human review req |
| PE-PCB-006 | VOUT copper (zone area per layer, via count, track length) | {'zone_area_mm2': {'F.Cu': 2289.5, 'B.Cu': 2462.3, 'In2.Cu': 2035.7}, 'vias': 65, 'track_m | within spec threshold - human review req |
| PE-PCB-006 | VOUT_L copper (zone area per layer, via count, track length) | {'zone_area_mm2': {'F.Cu': 509.0}, 'vias': 2, 'track_mm': 0.0} | exceeds spec threshold - human review re |
| PE-PCB-007 | control section (86 parts) to power stage (131 parts) bounding-box dis | 14.01 | within spec threshold - human review req |
| PE-PCB-007 | GND_CTRL zone area (mm2) and island count per layer | {'In1.Cu': {'area': 5714.5, 'islands': 1}} | measured - human review required |
| PE-PCB-007 | board area (mm2), footprints per dm2, courtyard fraction front/back | {'area': 43162.8, 'per_dm2': 54.9, 'courtyard': {'front': 0.592, 'back': 0.008}} | within spec threshold - human review req |
| PE-PCB-008 | U1 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum | 8.33 | within spec threshold - human review req |
| PE-PCB-008 | U3 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum | 7.909 | within spec threshold - human review req |
| PE-PCB-008 | U2 supply pads ['6', '7', '19', '20', '21', '22', '23', '24', '25', '2 | 31.111 | measured - human review required |
| PE-PCB-008 | U4 supply pads ['6', '7', '19', '20', '21', '22', '23', '24', '25', '2 | 17.726 | measured - human review required |
| PE-PCB-008 | U5 supply pads ['6', '7', '28', '29'] to nearest decoupling capacitor  | 19.844 | measured - human review required |
| PE-PCB-008 | U6 supply pads ['1', '8'] to nearest decoupling capacitor pad, maximum | 17.091 | measured - human review required |
| PE-PCB-008 | U7 supply pads ['1', '8'] to nearest decoupling capacitor pad, maximum | 20.318 | measured - human review required |
| PE-PCB-008 | U8 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 3.613 | measured - human review required |
| PE-PCB-008 | U9 supply pads ['1'] to nearest decoupling capacitor pad, maximum (mm) | 5.875 | measured - human review required |
| PE-PCB-008 | U10 supply pads ['9', '10'] to nearest decoupling capacitor pad, maxim | 23.716 | measured - human review required |
| KR-PCB-003 | KS_H versus SW: distinct nets, no bridging part, no copper contact, mi | {'distinct': True, 'bridging': [], 'contact': False, 'min_mm': 0.3} | within spec threshold - human review req |
| KR-PCB-003 | KS_L versus PGND: distinct nets, no bridging part, no copper contact,  | {'distinct': True, 'bridging': [], 'contact': False, 'min_mm': 0.3} | within spec threshold - human review req |
| KR-ISO-001 | HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS): minimum c | {'F.Cu': 2.775, 'In1.Cu': 2.775, 'In2.Cu': 0.825, 'B.Cu': 2.775} | exceeds spec threshold - human review re |
| KR-ISO-001 | ISO_BARRIER strip barrier strip copper items per layer | {'F.Cu': 0, 'In1.Cu': 0, 'In2.Cu': 0, 'B.Cu': 0} | within spec threshold - human review req |
| KR-ISO-002 | HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers): minimum copper dista | {'F.Cu': 8.975, 'In1.Cu': 11.1, 'In2.Cu': 11.1, 'B.Cu': 10.425} | exceeds spec threshold - human review re |
| KR-ISO-002 | HV to PE: minimum copper distance per layer (mm) | {'F.Cu': 0.3, 'In1.Cu': 0.301, 'In2.Cu': 0.301, 'B.Cu': 0.301} | exceeds spec threshold - human review re |
| KR-ISO-002 | HV functional VIN to PGND (outside the TO-247-4 pin fields): minimum c | {'F.Cu': 0.3, 'In1.Cu': 0.3, 'In2.Cu': 0.3, 'B.Cu': 0.3} | exceeds spec threshold - human review re |
| KR-ISO-002 | HV functional SW to PGND (outside the TO-247-4 pin fields): minimum co | {'F.Cu': 7.3, 'In1.Cu': 0.3, 'In2.Cu': 2.9, 'B.Cu': 0.3} | exceeds spec threshold - human review re |
| KR-ISO-002 | HV functional VIN to SW (outside the TO-247-4 pin fields): minimum cop | {'F.Cu': 0.7, 'In1.Cu': 31.68, 'In2.Cu': 0.3, 'B.Cu': 31.68} | exceeds spec threshold - human review re |
| KR-ISO-002 | HV functional VOUT to PGND: minimum copper distance per layer (mm) | {'F.Cu': 0.425, 'In1.Cu': 0.3, 'In2.Cu': 0.3, 'B.Cu': 0.3} | exceeds spec threshold - human review re |
| KR-ISO-004 | U1 land gap g (mm), slot extension e (mm), around-the-end surface path | {'g': 7.25, 'e': 3.025, 'path': 9.443, 'slots': 2} | exceeds spec threshold - human review re |
| KR-ISO-004 | U3 land gap g (mm), slot extension e (mm), around-the-end surface path | {'g': 7.25, 'e': 3.025, 'path': 9.443, 'slots': 2} | exceeds spec threshold - human review re |
| KR-ISO-004 | U2 land gap g (mm), slot extension e (mm), around-the-end surface path | {'g': 8.1, 'e': 3.0, 'path': 10.08, 'slots': 7} | within spec threshold - human review req |
| KR-ISO-004 | U4 land gap g (mm), slot extension e (mm), around-the-end surface path | {'g': 8.1, 'e': 3.0, 'path': 10.08, 'slots': 1} | within spec threshold - human review req |
| KR-ISO-004 | U5 land gap g (mm), slot extension e (mm), around-the-end surface path | {'g': 8.1, 'e': 3.0, 'path': 10.08, 'slots': 1} | within spec threshold - human review req |
| KR-ISO-004 | U6 land gap g (mm), slot extension e (mm), around-the-end surface path | {'g': 9.1, 'e': 2.995, 'path': 10.894, 'slots': 1} | exceeds spec threshold - human review re |
| KR-ISO-004 | U7 land gap g (mm), slot extension e (mm), around-the-end surface path | {'g': 9.1, 'e': 2.995, 'path': 10.894, 'slots': 1} | exceeds spec threshold - human review re |
| KR-ISO-004 | U10 land gap g (mm), slot extension e (mm), around-the-end surface pat | {'g': 7.75, 'e': 3.005, 'path': 9.807, 'slots': 1} | within spec threshold - human review req |
| KR-TH-002 | HS1: minimum HV copper distance to the heatsink courtyard on the outer | {'F.Cu': 4.975, 'B.Cu': 4.975} | exceeds spec threshold - human review re |

## Findings: applied / not applied

| ID | Severity | Automation-verifiable | Status after this run |
|---|---|---|---|
| LR-01 | blocker | True | {'status': 'applied', 'detail': "automation/kicad_tools/generate_sic_power_board.py written (no power generator existed; the task's generate_sic_boards.py is not in the tree). Board kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb produced: 237 footprints, 3624 tracks, 548 vias, 33 zones. kicad-cli DRC (--schematic-parity --severity-all) manifest verification/drc/20261010T164654Z-drc-ccea4530/run.json: 284 violations / 183 unconnected / 0 parity; router unresolved 174. Metrics against the corrected layout_spec_power.json in engineering_checks/layout_metrics_power.{json,md}."} |
| LR-02 | blocker | True | {'status': 'applied (partially effective)', 'detail': "Routing room and order: logic region moved to y >= 57 mm (DSP at y = 31), outward F.Cu escape stubs for the DSP's bottom pins, candidate signal_priority, routing-order trials and rip-up negotiation in grid_router. Unconnected items 39 -> 1 (DRC manifest verification/drc/20261010T141539Z-drc-a497f454/run.json); router unresolved: BIAS_EN. NOT taken from the proposal: 0.15 mm track/clearance - the frozen .kicad_dru minimum is 0.2 mm and rules are not downgraded; a pre-routed XRS_N spine was not added because the DSP-side geometry of the remaining failures changes with every trial."} |
| LR-03 | blocker | True | {'status': 'applied', 'detail': "J8 on B.Cu (candidate fixed entry [28.0, 74.0, 270, 'B']; load_candidate accepts a side field, the placer flips the footprint). Measured side B.Cu, pin 1 at [28.0, 74.0] (left end, as documented), silkscreen 'J8 PIN 1 >' and 'MEZZANINE (B.Cu)' re-derived. JTAG J3 stays on F.Cu for accessibility (documented in the candidate)."} |
| LR-04 | should-fix | True | {'status': 'applied (partially effective)', 'detail': "New adc_filters region beside the ADC pins (C68-C75, C47, C48, R25 assigned). DSP pin to filter capacitor pad: max 17.27 -> 14.75 mm; per pin: {'U5.38->C72': 14.75, 'U5.39->C71': 10.35, 'U5.40->C70': 9.41, 'U5.41->C69': 8.48, 'U5.42->C68': 6.83, 'U5.46->C73': 9.84, 'U5.47->C74': 9.67, 'U5.49->C75': 10.42}. The proposed 3-5 mm is not reached: the capacitors sit outside the LQFP's outward escape via rows (15.9 mm radius) and the region is shared by ten parts; ADCREFM/P capacitors {'U5.55->C47': 7.38, 'U5.56->C48': 7.87} -> {'U5.55->C47': 4.88, 'U5.56->C48': 5.6} mm."} |
| LR-05 | should-fix | True | {'status': 'applied', 'detail': "C5 (19.9, 19.6) and C4 (21.2, 23.4) at the U2 VIN/GND pins, C6 at the pins, 5V_SW pre-routed on F.Cu as a 0.7 mm track U2.2 -> L1.1 with the C6 branch, 5V_BST pre-routed 0.3 mm. U2.3 to C4.1 / C5.1: 21.24 / 17.7 -> 4.23 / 2.04 mm; 5V_SW segments/vias/layers 10/3/['B.Cu', 'F.Cu'] -> 4/0/['F.Cu']."} |
| LR-06 | should-fix | True | {'status': 'applied', 'detail': 'exposed_pad_vias arrays (2 x 4, 0.3 mm drill) in U1 pad 17 (EFUSE_RTN, joined by 0.4 mm B.Cu combs because the net has no plane) and U3 pad 29 (GND_CTRL to In1.Cu). Vias in pad: U1.17 1 -> 8, U3.29 1 -> 8.'} |
| LR-07 | should-fix | True | {'status': 'applied (EFUSE_RTN kept at 0.4 mm)', 'detail': 'NET_RULES: 12V_IN 1.0 mm (pre-routed bus) , 12V_PROT 1.0 mm with three 0.3 mm vias at the eFuse output, 5V 0.6 mm, 5V_SW 0.7 mm, 0.4 mm fanout stubs where the HTSSOP/SOT pads limit; 12V_PROT and 5V In2.Cu corridor fingers >= 2 mm (CORRIDOR_HALF_WIDTH_BY_NET). Measured 12V_IN width 0.5-1.0 mm, 12V_PROT 0.4-1.0 mm / 11 vias. EFUSE_RTN stays 0.4 mm: it is a net of 0603 sense-divider pads and the PowerPad array on an isolated net (LR-10) - its current is the divider/PowerPad return, not the 1.96 A load path, and a 1.0 mm track between the 0.65 mm pitch HTSSOP pins is not routable at 0.2 mm clearance.'} |
| LR-08 | should-fix | True | {'status': 'applied', 'detail': "layout_spec_power.json rewritten from circuit_power.json: barrier_parts U1, U3 (UCC21710), U2, U4, U5 (UCC14141), U6, U7 (AMC1311), U10 (TMCS1133); gate loops Q1 -> U1, Q2 -> U3 with the placed footprint's pad numbers; MOSFET pads 1 drain / 2 source / 3 Kelvin / 4 gate; full CTRL_SELV pattern list; ISO_BARRIER zone and rectangle; heights; sensing pairs. Used for layout_metrics_power."} |
| LR-09 | should-fix | True | {'status': 'applied', 'detail': "J5 (4.5, 25) and J4 (4.5, 35) in the left edge strip next to J2 (4.5, 44). Distance to the nearer edge: {'J4': 44.0, 'J5': 44.0} -> {'J4': 4.5, 'J5': 4.5} mm."} |
| LR-10 | should-fix | False | {'status': 'not applied - schematic-level, recorded as open issue', 'detail': 'EFUSE_RTN is isolated from GND_CTRL in the model; routed as drawn (PowerPad array joined on B.Cu). Schematic owner to decide; no layout change made.'} |
| LR-11 | note | True | {'status': 'applied', 'detail': "check_sic_layout.control_metrics honours control.exclude_refs (['J8', 'U5'] in layout_spec_control.json) for the section-separation groups; the result records excluded_refs."} |
| LR-12 | note | True | {'status': 'applied', 'detail': "verify_sic_buck.py: hashes_valid is derived only from 'source changed' / 'dependency changed' / report-hash problems; the DRC pass/fail message no longer flips it."} |
| LR-13 | note | True | {'status': 'applied (18.0 mm, not 17.3 mm)', 'detail': 'dsp_bypass 3V3 ring radius 18.5 -> 18.0 mm; 17.3 mm collided with the outward F.Cu escape stubs/vias of the LQFP escape plan (the stubs end at 46.5 mm below the body, i.e. 15.5 mm from the centre, plus via and courtyard clearance). DSP bypass pin-to-capacitor max/mean 5.849/4.571 -> 5.381/4.402 mm.'} |
| LR-14 | note | False | {'status': 'not applied - manual plan entry, open', 'detail': "ISENSE/ISENSE_REF pair not pre-routed (no differential mode in the grid router). Measured {'ISENSE': 105.2, 'ISENSE_REF': 89.0, 'mismatch': 16.2}."} |
| LR-15 | note | True | {'status': 'not resolved', 'detail': 'Corridor fingers of island_corridors() widened to >= 2 mm for 12V_PROT / 5V and the board re-filled, but the In2.Cu background-fill fragments between the background and the higher-priority corridor zones were not removed: slivers < 0.01 mm2 7 -> 9. A fill-grid snap of the corridor edges remains open.'} |
| LR-16 | note | True | {'status': 'applied (partially effective)', 'detail': 'Y1 fixed at (72.5, 7.4) rotation 180 next to the XCLKIN escape (the proposed ~5 mm collides with the top escape via rows and the 3V3 ring); Y1 centre / pad 3 to XCLKIN pin: 13.02 / 14.4 -> 11.06 / 8.86 mm.'} |
| LR-17 | note | False | {'status': 'not applied - library-level, open', 'detail': 'U1, U3, Y1 3D models are absent from the KiCad 10.0.7 bundle; libraries are frozen for the layout agents. STEP/renders still show the three parts bodiless.'} |
| LR-18 | note | False | {'status': 'not applied - documentation/mechanical, open', 'detail': "architecture.md / pcb_stackup.md overhang and hole pattern text not changed (docs are frozen for this agent). Power-board J7 and H8-H11 were placed from the control board's J8 pin 1 (28.0, 74.0) and H3/H4 as proposed."} |
| LR-19 | note | True | {'status': 'applied', 'detail': 'run_check manifests now carry report_sha256 and finding_counts (violations / unconnected_items / schematic_parity); verify_sic_buck.py recomputes the report hash (report_hash_checked).'} |
