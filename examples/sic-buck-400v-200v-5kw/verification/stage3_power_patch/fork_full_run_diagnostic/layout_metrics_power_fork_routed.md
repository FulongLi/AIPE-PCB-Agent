# Layout metrics - AIPE SiC buck 400 V -> 200 V / 5 kW power board (AIPE_SiC_Buck_Power) - layout metrics spec

Status: **measured-human-review-required**. Generated 2026-10-10T15:50:37.378718+00:00 by `automation/verification/check_sic_layout.py` (pcbnew 10.0.7, distance backend numpy, 15.094 s).

Board `C:\Users\ZHONGN~1\AppData\Local\Temp\claude\d--Cursor-Workspace-AIPE-PCB-Agent\d8f6e3bc-7921-4cf9-b1d3-9695bd7c8da8\scratchpad\pzf\AIPE_SiC_Buck_Power.kicad_pcb` (sha256 `40f67690c8e99eab...`), spec `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\verification\engineering_checks\layout_spec_power.json`, model `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\design\circuit_power.json`.

## Board

| Metric | Value |
| --- | --- |
| Outline (mm) | 240.00 x 180.00 |
| Outline area (mm2) | 43162.8 |
| Copper layers | 4 (F.Cu, In1.Cu, In2.Cu, B.Cu) |
| Thickness (mm) | 2.000 |
| Copper thickness (um, stackup text) | F.Cu=70.000; In1.Cu=70.000; In2.Cu=70.000; B.Cu=70.000 |
| Footprints / tracks / vias / zones / rule areas | 237 / 3781 / 645 / 18 / 12 |
| Nets | 104 |
| Zones without fill (areas read from the file) | none |
| Expected (spec) | outline_mm=240, 180; copper_layers=4; copper_um=70; thickness_mm=2.000 |

## Rule table

Dispositions follow the spec thresholds only; every row needs engineering acceptance by a human reviewer.

| Rule | Requirement | Metric | Measured | Threshold | Disposition | Note |
| --- | --- | --- | --- | --- | --- | --- |
| PE-PCB-001 | Minimise MOSFET gate loop | U1 output pad 4 to Q1 gate pad 4 | 14.360 | <= 15 mm | within spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_H/HS_OUTH/HS_OUTL/HS_CLMP track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_H layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=58.210; adjacent=yes; over_kelvin_pour=0.123 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-001 | Minimise MOSFET gate loop | U3 output pad 4 to Q2 gate pad 4 | 14.360 | <= 15 mm | within spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_L/LS_OUTH/LS_OUTL/LS_CLMP track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_L layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=83.910; adjacent=yes; over_kelvin_pour=0.166 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q1 drain pad 1 (VIN) to nearest HF capacitor pad of the same net | 8.562 | <= 15.0 mm (row 2; row 1 <= 5.0 mm) | within spec threshold - human review required | nearest C1.1 |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q1 source pad 2 (SW) to nearest HF capacitor pad (any named net) | 13.240 | n/a | measured - human review required | pad net is not a capacitor net (switch node) |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q2 drain pad 1 (SW) to nearest HF capacitor pad (any named net) | 36.058 | n/a | measured - human review required | pad net is not a capacitor net (switch node) |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q2 source pad 2 (PGND) to nearest HF capacitor pad of the same net | 41.131 | <= 15.0 mm (row 2; row 1 <= 5.0 mm) | exceeds spec threshold - human review required | nearest C1.2 |
| PE-PCB-003 | Minimise HF commutation loop | SW copper area, all layers (mm2; per layer in JSON) | 2546.900 | n/a | measured - human review required | switch-node copper is a dv/dt coupling and radiation proxy; the baseline asks for the minimum that carries the current |
| PE-PCB-003 | Minimise HF commutation loop | HV ceramic group bounding box (x0, y0, x1, y1 mm) and pin distances (JSON) | 39.100, 123.050, 81.700, 139.950 | n/a | measured - human review required | bounding box of the HF capacitor pads on the named nets |
| PE-PCB-004 | Use Kelvin current sensing | AMC1311 VIN differential output track lengths (mm) and mismatch | VIN_OUTP=22.101; VIN_OUTN=29.851; mismatch=7.750 | n/a | measured - human review required |  |
| PE-PCB-004 | Use Kelvin current sensing | AMC1311 VOUT differential output track lengths (mm) and mismatch | VOUT_OUTP=24.351; VOUT_OUTN=20.851; mismatch=3.500 | n/a | measured - human review required |  |
| PE-PCB-004 | Use Kelvin current sensing | TMCS1133 ISENSE / ISENSE_REF track lengths (mm) and mismatch | ISENSE=85.760; ISENSE_REF=58.500; mismatch=27.260 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | AMC1311 VIN differential output minimum copper distance to SW (mm, any layer) | 30.464 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | AMC1311 VOUT differential output minimum copper distance to SW (mm, any layer) | 36.050 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | TMCS1133 ISENSE / ISENSE_REF minimum copper distance to SW (mm, any layer) | 23.947 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U6 pads: minimum copper distance to SW (mm, any layer) | 22.344 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U7 pads: minimum copper distance to SW (mm, any layer) | 25.150 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U10 pads: minimum copper distance to SW (mm, any layer) | 27.345 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U8 pads: minimum copper distance to SW (mm, any layer) | 37.475 | n/a | measured - human review required |  |
| PE-PCB-006 | Justify high-current copper and via capacity | VIN copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=5727.500; In2.Cu=19888.400; vias=34; track_mm=3.100 | >= 24 vias per net | within spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VIN_RAW copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=485.000; B.Cu=485.000; vias=0; track_mm=0.000 | >= 24 vias per net | exceeds spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | SW copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=154.300; In2.Cu=2091.000; vias=24; track_mm=9.600 | >= 24 vias per net | within spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | PGND copper (zone area per layer, via count, track length) | zone_area_mm2=B.Cu=10464.600; In1.Cu=30498.100; vias=72; track_mm=39.300 | >= 24 vias per net | within spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VOUT copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=2230.900; B.Cu=2436.700; In2.Cu=3261.800; vias=63; track_mm=6.100 | >= 24 vias per net | within spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VOUT_L copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=506.000; vias=0; track_mm=0.000 | >= 24 vias per net | exceeds spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-007 | Separate control and switching structures | control section (86 parts) to power stage (131 parts) bounding-box distance (mm) | 11.580 | >= 9.0 mm | within spec threshold - human review required |  |
| PE-PCB-007 | Separate control and switching structures | GND_CTRL zone area (mm2) and island count per layer | In1.Cu=area=5610.200; islands=1 | n/a | measured - human review required | V1 ground-plane extent guard generalised |
| PE-PCB-007 | Separate control and switching structures | board area (mm2), footprints per dm2, courtyard fraction front/back | area=43162.800; per_dm2=54.900; courtyard=front=0.588; back=0.011 | area <= 43200 mm2 | within spec threshold - human review required | HV bbox fraction 0.771; power density 1158.4 W/dm2, 1608.9 W/L |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U1 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 8.575 | <= 15 mm | within spec threshold - human review required | 5->C22.1 5.38; 8->C25.2 8.58 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U3 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 16.322 | <= 15 mm | exceeds spec threshold - human review required | 5->C42.1 10.17; 8->C57.2 16.32 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U2 supply pads ['6', '7', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '35', '36'] to nearest decoupling capacitor pad, maximum (mm) | 9.269 | n/a | measured - human review required | 6->C30.1 8.69; 7->C30.1 9.27; 19->C25.2 4.65; 20->C25.2 4.83; 21->C25.2 5.09; 22->C25.2 5.41; 23->C26.2 5.78; 24->C26.2 5.88; 25->C26.2 6.05; 26->C26.2 6.28; 27->C26.2 6.57; 28->C36.1 4.06; 29->C36.1 4.17; 30->C34.2 5.45; 31->C34.2 4.97; 35->C34.2 3.64; 36->C34.2 3.53 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U4 supply pads ['6', '7', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '35', '36'] to nearest decoupling capacitor pad, maximum (mm) | 12.295 | n/a | measured - human review required | 6->C50.1 11.86; 7->C50.1 12.30; 19->C54.2 5.33; 20->C54.2 5.30; 21->C54.2 5.36; 22->C54.2 5.49; 23->C54.2 5.69; 24->C45.2 5.33; 25->C45.2 5.02; 26->C45.2 4.78; 27->C45.2 4.62; 28->C56.1 6.80; 29->C56.1 6.52; 30->C45.2 4.69; 31->C45.2 4.88; 35->C57.2 5.47; 36->C57.2 5.24 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U5 supply pads ['6', '7', '28', '29'] to nearest decoupling capacitor pad, maximum (mm) | 21.964 | n/a | measured - human review required | 6->C60.1 21.96; 7->C60.1 21.62; 28->C66.1 14.54; 29->C66.1 14.53 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U6 supply pads ['1', '8'] to nearest decoupling capacitor pad, maximum (mm) | 19.937 | n/a | measured - human review required | 1->C72.1 3.05; 8->C85.1 19.94 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U7 supply pads ['1', '8'] to nearest decoupling capacitor pad, maximum (mm) | 14.100 | n/a | measured - human review required | 1->C76.1 11.59; 8->C85.1 14.10 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U8 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 3.613 | n/a | measured - human review required | 8->C73.1 3.61 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U9 supply pads ['1'] to nearest decoupling capacitor pad, maximum (mm) | 3.567 | n/a | measured - human review required | 1->C77.1 3.57 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U10 supply pads ['9', '10'] to nearest decoupling capacitor pad, maximum (mm) | 20.592 | n/a | measured - human review required | 9->C88.1 19.72; 10->C88.1 20.59 |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_H versus SW: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.300 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_L versus PGND: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.300 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS): minimum copper distance per layer (mm) | F.Cu=1.146; In1.Cu=1.450; In2.Cu=0.300; B.Cu=1.350 | outer=3.000; inner=1.000 mm | exceeds spec threshold - human review required |  |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER segment 1 barrier strip copper items per layer | n/a | n/a | not measured - spec input missing or reference not found | region not found (rect_mm or rule area name) |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER segment 2 barrier strip copper items per layer | n/a | n/a | not measured - spec input missing or reference not found | region not found (rect_mm or rule area name) |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER segment 3 barrier strip copper items per layer | n/a | n/a | not measured - spec input missing or reference not found | region not found (rect_mm or rule area name) |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER segment 4 barrier strip copper items per layer | n/a | n/a | not measured - spec input missing or reference not found | region not found (rect_mm or rule area name) |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER segment 5 barrier strip copper items per layer | n/a | n/a | not measured - spec input missing or reference not found | region not found (rect_mm or rule area name) |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER segment 6 barrier strip copper items per layer | n/a | n/a | not measured - spec input missing or reference not found | region not found (rect_mm or rule area name) |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER segment 7 barrier strip copper items per layer | n/a | n/a | not measured - spec input missing or reference not found | region not found (rect_mm or rule area name) |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER segment 8 barrier strip copper items per layer | n/a | n/a | not measured - spec input missing or reference not found | region not found (rect_mm or rule area name) |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER segment 9 barrier strip copper items per layer | n/a | n/a | not measured - spec input missing or reference not found | region not found (rect_mm or rule area name) |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers): minimum copper distance per layer (mm) | F.Cu=8.357; In1.Cu=8.925; In2.Cu=8.925; B.Cu=8.600 | all=9.000 mm | exceeds spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV to PE: minimum copper distance per layer (mm) | F.Cu=0.301; In1.Cu=0.301; In2.Cu=0.301; B.Cu=0.300 | all=5.000 mm | exceeds spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV functional VIN to PGND (outside the TO-247-4 pin fields): minimum copper distance per layer (mm) | F.Cu=0.300; In1.Cu=0.300; In2.Cu=0.300; B.Cu=0.300 | outer=3.000; inner=1.000 mm | exceeds spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV functional SW to PGND (outside the TO-247-4 pin fields): minimum copper distance per layer (mm) | F.Cu=9.300; In1.Cu=0.300; In2.Cu=0.300; B.Cu=0.300 | outer=3.000; inner=1.000 mm | exceeds spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV functional VIN to SW (outside the TO-247-4 pin fields): minimum copper distance per layer (mm) | F.Cu=2.700; In1.Cu=40.064; In2.Cu=0.300; B.Cu=40.064 | outer=3.000; inner=1.000 mm | exceeds spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV functional VOUT to PGND: minimum copper distance per layer (mm) | F.Cu=0.300; In1.Cu=0.300; In2.Cu=0.300; B.Cu=0.300 | outer=3.000; inner=1.000 mm | exceeds spec threshold - human review required |  |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U1 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=7.250; e=3.025; path=9.443; slots=2 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | exceeds spec threshold - human review required | edge segment |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U3 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=7.250; e=3.025; path=9.443; slots=2 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | exceeds spec threshold - human review required | edge segment |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U2 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=8.100; e=3.000; path=10.080; slots=4 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U2 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U4 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=8.100; e=3.000; path=10.080; slots=4 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U4 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U5 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=8.100; e=3.000; path=10.080; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U5 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U6 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=9.100; e=2.995; path=10.894; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | exceeds spec threshold - human review required | npth pad U6 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U7 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=9.100; e=2.995; path=10.894; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | exceeds spec threshold - human review required | npth pad U7 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U10 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=7.750; e=3.005; path=9.807; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U10 |
| KR-TH-002 | Rated insulating interface for shared heat sinks (HV copper keep-out at the sink) | HS1: minimum HV copper distance to the heatsink courtyard on the outer layers (mm) | F.Cu=4.975; B.Cu=4.975 | >= 5.0 mm | exceeds spec threshold - human review required | baseline: >= 5 mm HV copper keep-out around the PE-bonded sink; pad/clip insulation itself is a human-review item |

Rows: 66 - within spec threshold 16, exceeding 16, measured without threshold 25, not measured 9.

## Isolation: minimum copper distance per layer (mm)

| Pair | F.Cu | In1.Cu | In2.Cu | B.Cu | Threshold | Within |
| --- | --- | --- | --- | --- | --- | --- |
| HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers) | 8.357 | 8.925 | 8.925 | 8.600 | F.Cu=9.000; In1.Cu=9.000; In2.Cu=9.000; B.Cu=9.000 | no |
| HV to PE | 0.301 | 0.301 | 0.301 | 0.300 | F.Cu=5.000; In1.Cu=5.000; In2.Cu=5.000; B.Cu=5.000 | no |
| HV functional VIN to PGND (outside the TO-247-4 pin fields) | 0.300 | 0.300 | 0.300 | 0.300 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | no |
| HV functional SW to PGND (outside the TO-247-4 pin fields) | 9.300 | 0.300 | 0.300 | 0.300 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | no |
| HV functional VIN to SW (outside the TO-247-4 pin fields) | 2.700 | 40.064 | 0.300 | 40.064 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | no |
| HV functional VOUT to PGND | 0.300 | 0.300 | 0.300 | 0.300 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | no |
| HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS) | 1.146 | 1.450 | 0.300 | 1.350 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | no |

## Barrier strips (copper items per layer)

| Strip | Region | Box (mm) | F.Cu | In1.Cu | In2.Cu | B.Cu | Copper-free |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISO_BARRIER segment 1 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ISO_BARRIER segment 2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ISO_BARRIER segment 3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ISO_BARRIER segment 4 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ISO_BARRIER segment 5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ISO_BARRIER segment 6 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ISO_BARRIER segment 7 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ISO_BARRIER segment 8 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| ISO_BARRIER segment 9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Barrier parts: land gap, slot and surface path

| Ref | Found | HV pads | SELV pads | Land gap g (mm) | Slot | Extension e (mm) | Slot width (mm) | Surface path (mm) | Required e (mm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U1 | yes | 1, 2, 3, 4, 5, 6, 7, 8 | 9, 10, 11, 12, 13, 14, 15 | 7.250 | edge segment | 3.025 | 0.050 | 9.443 | 2.666 |
| U3 | yes | 1, 2, 3, 4, 5, 6, 7, 8 | 9, 10, 11, 12, 13, 14, 15 | 7.250 | edge segment | 3.025 | 0.050 | 9.443 | 2.666 |
| U2 | yes | 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 8.100 | npth pad | 3.000 | 1.200 | 10.080 | 1.962 |
| U4 | yes | 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 8.100 | npth pad | 3.000 | 1.200 | 10.080 | 1.962 |
| U5 | yes | 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 8.100 | npth pad | 3.000 | 1.200 | 10.080 | 1.962 |
| U6 | yes | 1, 2, 3, 4 | 5, 6, 7, 8 | 9.100 | npth pad | 2.995 | 1.200 | 10.895 | 0.000 |
| U7 | yes | 1, 2, 3, 4 | 5, 6, 7, 8 | 9.100 | npth pad | 2.995 | 1.200 | 10.895 | 0.000 |
| U10 | yes | 1, 2 | 3, 4, 6, 7, 8, 9, 10 | 7.750 | npth pad | 3.005 | 1.200 | 9.807 | 2.288 |

## Commutation loop proxies

| MOSFET | Role | Pin | Same-net cap (mm) | Pad | Any cap (mm) | Pad | Caps in row 1 | Caps in row 2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | HS | drain 1 (VIN) | 8.562 | C1.1 | 8.258 | C1.2 | 0 | 2 |
| Q1 | HS | source 2 (SW) | n/a | n/a | 13.240 | C1.2 | 0 | 0 |
| Q2 | LS | drain 1 (SW) | n/a | n/a | 36.058 | C1.2 | 0 | 0 |
| Q2 | LS | source 2 (PGND) | 41.131 | C1.2 | 41.131 | C1.2 | 0 | 0 |

Switch-node copper (mm2): F.Cu=230.000; In1.Cu=71.700; In2.Cu=2162.700; B.Cu=82.500

HV ceramic group bounding box (mm): 39.10, 123.05, 81.70, 139.95

## Gate loops

| MOSFET | Driver | Out->gate (mm) | Return->Kelvin (mm) | Gate track (mm) | Gate vias | Gate layers | Kelvin layers | Adjacent | Over Kelvin pour | KS distinct | KS copper min (mm) | KS copper contact | KS bridging parts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | U1 | 14.360 | 14.721 | 58.21 | 8 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.123 | yes | 0.300 | no |  |
| Q2 | U3 | 14.360 | 14.721 | 83.91 | 8 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.166 | yes | 0.300 | no |  |

## Heatsink envelope

| Layer | HV items | Min distance (mm) | Items within keep-out | Nearest |
| --- | --- | --- | --- | --- |
| F.Cu | 430 | 4.975 | 6 | pad J3.1 |
| B.Cu | 312 | 4.975 | 6 | pad J3.1 |

## Decoupling

| IC | Pad | Net | Capacitor pad | Distance (mm) | Same net |
| --- | --- | --- | --- | --- | --- |
| U1 | 5 | VDD_H | C22.1 | 5.377 | yes |
| U1 | 8 | VEE_H | C25.2 | 8.575 | yes |
| U3 | 5 | VDD_L | C42.1 | 10.171 | yes |
| U3 | 8 | VEE_L | C57.2 | 16.322 | yes |
| U2 | 6 | 12V_BIAS_H | C30.1 | 8.688 | yes |
| U2 | 7 | 12V_BIAS_H | C30.1 | 9.270 | yes |
| U2 | 19 | VEE_H | C25.2 | 4.653 | yes |
| U2 | 20 | VEE_H | C25.2 | 4.832 | yes |
| U2 | 21 | VEE_H | C25.2 | 5.087 | yes |
| U2 | 22 | VEE_H | C25.2 | 5.409 | yes |
| U2 | 23 | VEE_H | C26.2 | 5.779 | yes |
| U2 | 24 | VEE_H | C26.2 | 5.879 | yes |
| U2 | 25 | VEE_H | C26.2 | 6.048 | yes |
| U2 | 26 | VEE_H | C26.2 | 6.280 | yes |
| U2 | 27 | VEE_H | C26.2 | 6.568 | yes |
| U2 | 28 | VDD_H | C36.1 | 4.063 | yes |
| U2 | 29 | VDD_H | C36.1 | 4.166 | yes |
| U2 | 30 | VEE_H | C34.2 | 5.445 | yes |
| U2 | 31 | VEE_H | C34.2 | 4.968 | yes |
| U2 | 35 | VEE_H | C34.2 | 3.638 | yes |
| U2 | 36 | VEE_H | C34.2 | 3.534 | yes |
| U4 | 6 | 12V_BIAS_L | C50.1 | 11.863 | yes |
| U4 | 7 | 12V_BIAS_L | C50.1 | 12.295 | yes |
| U4 | 19 | VEE_L | C54.2 | 5.326 | yes |
| U4 | 20 | VEE_L | C54.2 | 5.301 | yes |
| U4 | 21 | VEE_L | C54.2 | 5.356 | yes |
| U4 | 22 | VEE_L | C54.2 | 5.488 | yes |
| U4 | 23 | VEE_L | C54.2 | 5.692 | yes |
| U4 | 24 | VEE_L | C45.2 | 5.330 | yes |
| U4 | 25 | VEE_L | C45.2 | 5.022 | yes |
| U4 | 26 | VEE_L | C45.2 | 4.783 | yes |
| U4 | 27 | VEE_L | C45.2 | 4.624 | yes |
| U4 | 28 | VDD_L | C56.1 | 6.799 | yes |
| U4 | 29 | VDD_L | C56.1 | 6.523 | yes |
| U4 | 30 | VEE_L | C45.2 | 4.687 | yes |
| U4 | 31 | VEE_L | C45.2 | 4.884 | yes |
| U4 | 35 | VEE_L | C57.2 | 5.466 | yes |
| U4 | 36 | VEE_L | C57.2 | 5.244 | yes |
| U5 | 6 | 12V_BIAS_S | C60.1 | 21.964 | yes |
| U5 | 7 | 12V_BIAS_S | C60.1 | 21.622 | yes |
| U5 | 28 | ISO_15V | C66.1 | 14.540 | yes |
| U5 | 29 | ISO_15V | C66.1 | 14.525 | yes |
| U6 | 1 | 5V_ISO | C72.1 | 3.053 | yes |
| U6 | 8 | 3V3 | C85.1 | 19.937 | yes |
| U7 | 1 | 5V_ISO | C76.1 | 11.589 | yes |
| U7 | 8 | 3V3 | C85.1 | 14.100 | yes |
| U8 | 8 | 3V3 | C73.1 | 3.613 | yes |
| U9 | 1 | 3V3 | C77.1 | 3.567 | yes |
| U10 | 9 | 3V3 | C88.1 | 19.721 | yes |
| U10 | 10 | 3V3 | C88.1 | 20.592 | yes |

## Sensing

| Pair | Nets | Track (mm) | Vias | Mismatch (mm) | Min to SW (mm) |
| --- | --- | --- | --- | --- | --- |
| AMC1311 VIN differential output | VIN_OUTP, VIN_OUTN | VIN_OUTP=22.10; VIN_OUTN=29.85 | VIN_OUTP=2; VIN_OUTN=2 | 7.750 | 30.464 |
| AMC1311 VOUT differential output | VOUT_OUTP, VOUT_OUTN | VOUT_OUTP=24.35; VOUT_OUTN=20.85 | VOUT_OUTP=0; VOUT_OUTN=2 | 3.500 | 36.050 |
| TMCS1133 ISENSE / ISENSE_REF | ISENSE, ISENSE_REF | ISENSE=85.76; ISENSE_REF=58.50 | ISENSE=2; ISENSE_REF=4 | 27.260 | 23.947 |

| Part | Found | Min to SW (mm) |
| --- | --- | --- |
| U6 | yes | 22.344 |
| U7 | yes | 25.150 |
| U10 | yes | 27.345 |
| U8 | yes | 37.475 |

## Control section

Control parts: 86, power parts: 131, bounding-box separation 11.580 mm.

| Ground layer | Area (mm2) | Islands | Zones | Required probes covered | Forbidden probes copper-free |
| --- | --- | --- | --- | --- | --- |
| In1.Cu | 5610.2 | 1 | 1 | 0/0 | 0/0 |

## Compactness

| Metric | Value |
| --- | --- |
| Board area (mm2 / dm2) | 43162.8 / 4.316 |
| Footprints per dm2 | 54.9 |
| Courtyard fraction front / back | 0.588 / 0.011 |
| HV bounding-box fraction of board | 0.771 |
| HV copper on outer layers (mm2, fraction of both sides) | 24236.5 (0.281) |
| Tallest component | HS1 50.0 mm |
| Assembly height (mm) declared / computed / used | 72, 52.0, 72.0 |
| Rated power (W) | 5000 |
| Power density (W/dm2, W/L) | 1158.4, 1608.9 |

## Classified nets

| Net | Class | Track (mm) | Tracks | Vias | Pads | Layers | Zone area (mm2) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12V_BIAS_H | CTRL_SELV | 10.7 | 21 | 7 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_BIAS_L | CTRL_SELV | 10.7 | 21 | 7 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_BIAS_S | CTRL_SELV | 10.2 | 20 | 7 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_PROT | CTRL_SELV | 10.9 | 11 | 6 | 11 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=5441.700 |
| 3V3 | CTRL_SELV | 40.4 | 75 | 27 | 31 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 5V_ISO | SENSE_ISO | 72.8 | 69 | 7 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BIAS_EN | CTRL_SELV | 177.6 | 86 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BIAS_EN_F | CTRL_SELV | 14.8 | 20 | 4 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BLD_IN_1 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| BLD_IN_2 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| BLD_OUT_1 | HV_VOUT | 0.9 | 1 | 0 | 2 | F.Cu |  |
| DAMP_MID | HV_VIN | 25.9 | 5 | 0 | 4 | F.Cu |  |
| DESAT_H_A | DESAT_HS | 76.3 | 117 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_H_OC | DESAT_HS | 33.2 | 77 | 4 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_L_A | DESAT_LS | 80.3 | 109 | 7 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_L_OC | DESAT_LS | 17.2 | 35 | 5 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAN_TACH | CTRL_SELV | 1.1 | 2 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAULT_N | CTRL_SELV | 1.6 | 1 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_H_N | CTRL_SELV | 130.5 | 98 | 9 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_L_N | CTRL_SELV | 2.8 | 4 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_H | CTRL_SELV | 57.6 | 82 | 16 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_L | CTRL_SELV | 70.4 | 103 | 17 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_S | CTRL_SELV | 36.1 | 58 | 16 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GND_CTRL | CTRL_SELV | 56.5 | 84 | 43 | 68 | F.Cu, In1.Cu, In2.Cu, B.Cu | In1.Cu=5610.200 |
| G_H | DRV_HS | 52.3 | 61 | 5 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G_L | DRV_LS | 74.4 | 158 | 5 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_CLMP | DRV_HS | 1.1 | 2 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_FB_VDD | DRV_HS | 3.8 | 7 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_FB_VEE | DRV_HS | 9.1 | 24 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_GK | DRV_HS | 3.2 | 5 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_OUTH | DRV_HS | 2.7 | 3 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_OUTL | DRV_HS | 2.2 | 3 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_RLIM | DRV_HS | 3.3 | 3 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| IND_IN_1 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| IND_IN_2 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| IND_IN_3 | HV_VIN | 1.4 | 1 | 0 | 2 | F.Cu |  |
| IND_OUT_1 | HV_VOUT | 0.9 | 1 | 0 | 2 | F.Cu |  |
| IND_OUT_2 | HV_VOUT | 1.4 | 1 | 0 | 2 | F.Cu |  |
| ISENSE | CTRL_SELV | 85.8 | 34 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISENSE_REF | CTRL_SELV | 58.5 | 47 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISO_15V | SENSE_ISO | 31.8 | 40 | 6 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISO_FB_VDD | SENSE_ISO | 21.4 | 27 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISO_FB_VEE | SENSE_ISO | 20.2 | 11 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISO_RLIM | SENSE_ISO | 1.3 | 2 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| K1_LOW | CTRL_SELV | 22.1 | 12 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_H | DRV_HS | 22.9 | 31 | 15 | 17 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=546.100 |
| KS_L | DRV_LS | 30.0 | 46 | 15 | 17 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=347.600 |
| LS_CLMP | DRV_LS | 5.7 | 9 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_FB_VDD | DRV_LS | 3.8 | 7 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_FB_VEE | DRV_LS | 7.2 | 13 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_GK | DRV_LS | 4.2 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_OUTH | DRV_LS | 1.2 | 2 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_OUTL | DRV_LS | 2.7 | 3 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_RLIM | DRV_LS | 2.3 | 3 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_N | CTRL_SELV | 26.7 | 31 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PE | PE | 23.5 | 62 | 0 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PE_REF_MID | HV_PGND | 6.5 | 1 | 0 | 2 | B.Cu |  |
| PGND | HV_PGND | 39.3 | 50 | 72 | 81 | F.Cu, In1.Cu, In2.Cu, B.Cu | B.Cu=10464.600; In1.Cu=30498.100 |
| PG_BIAS_H_N | CTRL_SELV | 107.0 | 74 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_L_N | CTRL_SELV | 41.5 | 18 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_S_N | CTRL_SELV | 32.9 | 46 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_H | CTRL_SELV | 119.7 | 30 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_H_F | CTRL_SELV | 146.8 | 107 | 7 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_L | CTRL_SELV | 67.5 | 36 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_L_F | CTRL_SELV | 147.6 | 139 | 6 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_H | CTRL_SELV | 151.6 | 144 | 11 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_L | CTRL_SELV | 2.8 | 4 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| REF2V5_PB | CTRL_SELV | 59.7 | 78 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RELAY_ON | CTRL_SELV | 1.1 | 2 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RESET_N | CTRL_SELV | 165.9 | 80 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RESET_N_F | CTRL_SELV | 121.7 | 111 | 7 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RLY_G | CTRL_SELV | 22.6 | 17 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SNUB_MID | HV_SW | 1.5 | 1 | 0 | 2 | F.Cu |  |
| SPARE_D1 | CTRL_SELV | 1.6 | 1 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SPARE_D2 | CTRL_SELV | 1.6 | 1 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SW | HV_SW | 9.6 | 2 | 24 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=154.300; In2.Cu=2091.000 |
| VDD_H | DRV_HS | 94.9 | 141 | 10 | 11 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDD_L | DRV_LS | 51.3 | 104 | 10 | 11 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_H | DRV_HS | 184.5 | 248 | 22 | 24 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_L | DRV_LS | 120.8 | 175 | 21 | 24 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN | HV_VIN | 3.1 | 1 | 34 | 33 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=5727.500; In2.Cu=19888.400 |
| VIN_AMP_N | CTRL_SELV | 28.8 | 27 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_AMP_P | CTRL_SELV | 35.0 | 39 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_DIV | SENSE_ISO | 74.3 | 76 | 6 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_DIV_T1 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| VIN_DIV_T2 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| VIN_DIV_T3 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| VIN_OUTN | CTRL_SELV | 29.9 | 22 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_OUTP | CTRL_SELV | 22.1 | 9 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_RAW | HV_VIN | 0.0 | 0 | 0 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=485.000; B.Cu=485.000 |
| VIN_SENSE | CTRL_SELV | 36.4 | 73 | 6 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOC_SET | CTRL_SELV | 25.3 | 13 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT | HV_VOUT | 6.1 | 2 | 63 | 17 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=2230.900; B.Cu=2436.700; In2.Cu=3261.800 |
| VOUT_AMP_N | CTRL_SELV | 21.5 | 25 | 5 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_AMP_P | CTRL_SELV | 39.0 | 17 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_DIV | SENSE_ISO | 22.1 | 22 | 4 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_DIV_T1 | HV_VOUT | 0.9 | 1 | 0 | 2 | F.Cu |  |
| VOUT_L | HV_VOUT | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=506.000 |
| VOUT_OUTN | CTRL_SELV | 20.9 | 11 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_OUTP | CTRL_SELV | 24.4 | 26 | 0 | 2 | F.Cu |  |
| VOUT_SENSE | CTRL_SELV | 50.5 | 46 | 7 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |

## Notes and limitations

- Straight-line pad distances, track sums and copper areas are geometric proxies; they are not loop inductance, current-path length, creepage per standard or EMI performance.
- Isolation distances are copper-to-copper on each layer (pads, tracks, vias, filled zones); through-air clearance between layers, component bodies, solder mask and coatings are not evaluated.
- Thresholds are those given in the layout spec (taken from the design baseline); no acceptance limit is invented here. Engineering acceptance of every row remains a human responsibility.
- Slot detection relies on non-plated oblong pads or Edge.Cuts graphics inside the barrier part courtyard; the fabricator must confirm the slot width after tolerance.
- Reference designators, pad numbers and net names follow design/circuit_power.json and the placed board generated by automation/kicad_tools/generate_sic_power_board.py: Q1 = HS C4MS025120K (TO-247-4 pads 1 D, 2 S, 3 KS, 4 G), Q2 = LS; U1/U3 = UCC21710 HS/LS drivers (pads 4 OUTH, 6 OUTL, 1 AIN = COM, 3 COM); U2/U4/U5 = UCC14141 HS/LS/sensing bias; U6/U7 = AMC1311 VIN/VOUT sense; U10 = TMCS1133; C1-C10 HF ceramics; C11/C12 input films; C13/C14 output films; L1 toroid; HS1 heatsink envelope; J7 mezzanine socket.
- Net classes copy the project net-class patterns of kicad/power_board/AIPE_SiC_Buck_Power.kicad_pro (first match in order); the barrier parts are the eight isolators on the straight barrier line.
- Thresholds are copied from design/design_decisions.json (architecture.target_metrics_after_layout, standards_and_spacing.kicad_rules_mm, standards_and_spacing.slots, architecture.power_board.heatsink); the checker adds none of its own. Rows for absent refs are reported as not measured, never as passed.
- ISO_BARRIER is realised as rule-area segments ISO_BARRIER_1..N between the barrier parts (the parts themselves bridge the band over their slots); every segment is listed so each is checked for copper.
- Stage-3 fork, first routed run (scratch diagnostic board, sha256 40f67690...), not the repository board
