# Layout metrics - AIPE SiC buck 400 V -> 200 V / 5 kW power board (AIPE_SiC_Buck_Power) - layout metrics spec

Status: **measured-human-review-required**. Generated 2026-10-11T05:44:44.993007+00:00 by `automation/verification/check_sic_layout.py` (pcbnew 10.0.7, distance backend numpy, 26.016 s).

Board `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\kicad\power_board\AIPE_SiC_Buck_Power.kicad_pcb` (sha256 `b1bb5698194b9aea...`), spec `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\verification\engineering_checks\layout_spec_power.json`, model `D:\Cursor Workspace\AIPE-PCB-Agent\examples\sic-buck-400v-200v-5kw\design\circuit_power.json`.

## Board

| Metric | Value |
| --- | --- |
| Outline (mm) | 240.00 x 180.00 |
| Outline area (mm2) | 43200.0 |
| Copper layers | 4 (F.Cu, In1.Cu, In2.Cu, B.Cu) |
| Thickness (mm) | 2.000 |
| Copper thickness (um, stackup text) | F.Cu=70.000; In1.Cu=70.000; In2.Cu=70.000; B.Cu=70.000 |
| Footprints / tracks / vias / zones / rule areas | 237 / 4755 / 606 / 20 / 16 |
| Nets | 104 |
| Zones without fill (areas read from the file) | none |
| Expected (spec) | outline_mm=240, 180; copper_layers=4; copper_um=70; thickness_mm=2.000 |

## Rule table

Dispositions follow the spec thresholds only; every row needs engineering acceptance by a human reviewer.

| Rule | Requirement | Metric | Measured | Threshold | Disposition | Note |
| --- | --- | --- | --- | --- | --- | --- |
| PE-PCB-001 | Minimise MOSFET gate loop | U1 output pad 4 to Q1 gate pad 4 | 14.353 | <= 15 mm | within spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_H/HS_OUTH/HS_OUTL/HS_CLMP track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_H layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=39.940; adjacent=yes; over_kelvin_pour=0.216 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-001 | Minimise MOSFET gate loop | U3 output pad 4 to Q2 gate pad 4 | 14.360 | <= 15 mm | within spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_L/LS_OUTH/LS_OUTL/LS_CLMP track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_L layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=84.440; adjacent=yes; over_kelvin_pour=0.264 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q1 drain pad 1 (VIN) to nearest HF capacitor pad of the same net | 8.367 | <= 15.0 mm (row 2; row 1 <= 5.0 mm) | within spec threshold - human review required | nearest C1.1 |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q1 source pad 2 (SW) to nearest HF capacitor pad (any named net) | 13.307 | n/a | measured - human review required | pad net is not a capacitor net (switch node) |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q2 drain pad 1 (SW) to nearest HF capacitor pad (any named net) | 36.083 | n/a | measured - human review required | pad net is not a capacitor net (switch node) |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q2 source pad 2 (PGND) to nearest HF capacitor pad of the same net | 41.165 | <= 15.0 mm (row 2; row 1 <= 5.0 mm) | exceeds spec threshold - human review required | nearest C1.2 |
| PE-PCB-003 | Minimise HF commutation loop | SW copper area, all layers (mm2; per layer in JSON) | 3660.200 | n/a | measured - human review required | switch-node copper is a dv/dt coupling and radiation proxy; the baseline asks for the minimum that carries the current |
| PE-PCB-003 | Minimise HF commutation loop | HV ceramic group bounding box (x0, y0, x1, y1 mm) and pin distances (JSON) | 39.100, 122.450, 81.700, 139.950 | n/a | measured - human review required | bounding box of the HF capacitor pads on the named nets |
| PE-PCB-004 | Use Kelvin current sensing | AMC1311 VIN differential output track lengths (mm) and mismatch | VIN_OUTP=80.905; VIN_OUTN=79.397; mismatch=1.508 | n/a | measured - human review required |  |
| PE-PCB-004 | Use Kelvin current sensing | AMC1311 VOUT differential output track lengths (mm) and mismatch | VOUT_OUTP=64.905; VOUT_OUTN=63.147; mismatch=1.758 | n/a | measured - human review required |  |
| PE-PCB-004 | Use Kelvin current sensing | TMCS1133 ISENSE / ISENSE_REF track lengths (mm) and mismatch | ISENSE=83.796; ISENSE_REF=90.100; mismatch=6.304 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | AMC1311 VIN differential output minimum copper distance to SW (mm, any layer) | 29.182 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | AMC1311 VOUT differential output minimum copper distance to SW (mm, any layer) | 36.050 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | TMCS1133 ISENSE / ISENSE_REF minimum copper distance to SW (mm, any layer) | 32.354 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U6 pads: minimum copper distance to SW (mm, any layer) | 22.344 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U7 pads: minimum copper distance to SW (mm, any layer) | 25.150 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U10 pads: minimum copper distance to SW (mm, any layer) | 27.345 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U8 pads: minimum copper distance to SW (mm, any layer) | 42.073 | n/a | measured - human review required |  |
| PE-PCB-006 | Justify high-current copper and via capacity | VIN copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=4530.400; In2.Cu=16940.000; vias=34; track_mm=3.100 | >= 24 vias per net | within spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VIN_RAW copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=422.800; B.Cu=422.800; vias=0; track_mm=51.300 | >= 24 vias per net | exceeds spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | SW copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=120.000; In2.Cu=3236.600; vias=25; track_mm=9.600 | >= 24 vias per net | within spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | PGND copper (zone area per layer, via count, track length) | zone_area_mm2=B.Cu=9042.000; In1.Cu=28679.700; vias=90; track_mm=22.500 | >= 24 vias per net | within spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VOUT copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=2218.800; B.Cu=2406.000; In2.Cu=3126.300; vias=63; track_mm=6.100 | >= 24 vias per net | within spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VOUT_L copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=422.200; vias=0; track_mm=0.000 | >= 24 vias per net | exceeds spec threshold - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-007 | Separate control and switching structures | control section (86 parts) to power stage (131 parts) bounding-box distance (mm) | 12.307 | >= 9.0 mm | within spec threshold - human review required |  |
| PE-PCB-007 | Separate control and switching structures | GND_CTRL zone area (mm2) and island count per layer | In1.Cu=area=5866.400; islands=1 | n/a | measured - human review required | V1 ground-plane extent guard generalised |
| PE-PCB-007 | Separate control and switching structures | board area (mm2), footprints per dm2, courtyard fraction front/back | area=43200.000; per_dm2=54.900; courtyard=front=0.594; back=0.010 | area <= 43200 mm2 | within spec threshold - human review required | HV bbox fraction 0.770; power density 1157.4 W/dm2, 1607.5 W/L |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U1 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 7.597 | <= 15 mm | within spec threshold - human review required | 5->C37.1 6.86; 8->C37.2 7.60 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U3 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 9.477 | <= 15 mm | within spec threshold - human review required | 5->C56.1 4.66; 8->C56.2 9.48 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U2 supply pads ['6', '7', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '35', '36'] to nearest decoupling capacitor pad, maximum (mm) | 9.370 | n/a | measured - human review required | 6->C30.1 7.55; 7->C30.1 7.60; 19->C35.2 9.37; 20->C35.2 8.89; 21->C35.2 8.44; 22->C35.2 8.01; 23->C35.2 7.62; 24->C35.2 7.26; 25->C35.2 6.94; 26->C35.2 6.68; 27->C35.2 6.46; 28->C23.1 6.62; 29->C23.1 6.29; 30->C35.2 6.20; 31->C35.2 6.25; 35->C34.2 6.73; 36->C34.2 6.51 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U4 supply pads ['6', '7', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '35', '36'] to nearest decoupling capacitor pad, maximum (mm) | 13.911 | n/a | measured - human review required | 6->C50.1 13.49; 7->C50.1 13.91; 19->C55.2 7.10; 20->C55.2 7.03; 21->C55.2 7.03; 22->C59.2 7.03; 23->C59.2 7.03; 24->C59.2 7.09; 25->C54.2 7.11; 26->C54.2 7.04; 27->C54.2 7.03; 28->C57.1 8.57; 29->C57.1 8.21; 30->C57.2 7.06; 31->C57.2 7.03; 35->C58.2 7.20; 36->C58.2 6.71 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U5 supply pads ['6', '7', '28', '29'] to nearest decoupling capacitor pad, maximum (mm) | 27.532 | n/a | measured - human review required | 6->C60.1 27.10; 7->C60.1 27.53; 28->C66.1 11.11; 29->C66.1 11.22 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U6 supply pads ['1', '8'] to nearest decoupling capacitor pad, maximum (mm) | 4.336 | n/a | measured - human review required | 1->C72.1 4.34; 8->C73.1 3.83 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U7 supply pads ['1', '8'] to nearest decoupling capacitor pad, maximum (mm) | 8.263 | n/a | measured - human review required | 1->C76.1 4.35; 8->C77.1 8.26 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U8 supply pads ['8'] to nearest decoupling capacitor pad, maximum (mm) | 3.656 | n/a | measured - human review required | 8->C88.1 3.66 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U9 supply pads ['1'] to nearest decoupling capacitor pad, maximum (mm) | 5.176 | n/a | measured - human review required | 1->C85.1 5.18 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U10 supply pads ['9', '10'] to nearest decoupling capacitor pad, maximum (mm) | 15.508 | n/a | measured - human review required | 9->C87.1 15.51; 10->C87.1 15.41 |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_H versus SW: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.300 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_L versus PGND: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.300 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS): minimum copper distance per layer (mm) | F.Cu=6.270; In1.Cu=6.397; In2.Cu=4.800; B.Cu=6.397 | outer=3.000; inner=1.000 mm | within spec threshold - human review required |  |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | ISO_BARRIER strip barrier strip copper items per layer | F.Cu=0; In1.Cu=0; In2.Cu=0; B.Cu=0 | no copper on any layer | within spec threshold - human review required | region rule area 'ISO_BARRIER' |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers): minimum copper distance per layer (mm) | F.Cu=9.486; In1.Cu=11.100; In2.Cu=11.100; B.Cu=12.025 | all=9.000 mm | within spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV to PE: minimum copper distance per layer (mm) | F.Cu=5.000; In1.Cu=5.000; In2.Cu=5.000; B.Cu=5.000 | all=5.000 mm | within spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV functional VIN to PGND (outside the TO-247-4 pin fields): minimum copper distance per layer (mm) | F.Cu=1.950; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | outer=3.000; inner=1.000 mm | exceeds spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV functional SW to PGND (outside the TO-247-4 pin fields): minimum copper distance per layer (mm) | F.Cu=6.433; In1.Cu=1.000; In2.Cu=1.450; B.Cu=3.001 | outer=3.000; inner=1.000 mm | within spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV functional VIN to SW (outside the TO-247-4 pin fields): minimum copper distance per layer (mm) | F.Cu=3.000; In1.Cu=23.582; In2.Cu=1.000; B.Cu=23.582 | outer=3.000; inner=1.000 mm | within spec threshold - human review required |  |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV functional VOUT to PGND: minimum copper distance per layer (mm) | F.Cu=1.950; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | outer=3.000; inner=1.000 mm | exceeds spec threshold - human review required |  |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U1 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=7.250; e=3.555; path=10.155; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U1 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U3 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=7.250; e=3.555; path=10.155; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U3 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U2 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=8.100; e=3.000; path=10.080; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U2 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U4 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=8.100; e=3.000; path=10.080; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U4 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U5 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=8.100; e=3.000; path=10.080; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U5 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U6 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=9.100; e=3.195; path=11.119; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U6 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U7 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=9.100; e=3.195; path=11.119; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U7 |
| KR-ISO-004 | Slots and cut-outs to extend creepage | U10 land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm) | g=7.750; e=3.005; path=9.807; slots=1 | path >= 9.0 mm, e >= 3.0 mm, width >= 1.0 mm | within spec threshold - human review required | npth pad U10 |
| KR-TH-002 | Rated insulating interface for shared heat sinks (HV copper keep-out at the sink) | HS1: minimum HV copper distance to the heatsink courtyard on the outer layers (mm) | F.Cu=4.955; B.Cu=0.000 | >= 5.0 mm | exceeds spec threshold - human review required | baseline: >= 5 mm HV copper keep-out around the PE-bonded sink; pad/clip insulation itself is a human-review item |

Rows: 58 - within spec threshold 27, exceeding 6, measured without threshold 25, not measured 0.

## Isolation: minimum copper distance per layer (mm)

| Pair | F.Cu | In1.Cu | In2.Cu | B.Cu | Threshold | Within |
| --- | --- | --- | --- | --- | --- | --- |
| HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers) | 9.486 | 11.100 | 11.100 | 12.025 | F.Cu=9.000; In1.Cu=9.000; In2.Cu=9.000; B.Cu=9.000 | yes |
| HV to PE | 5.000 | 5.000 | 5.000 | 5.000 | F.Cu=5.000; In1.Cu=5.000; In2.Cu=5.000; B.Cu=5.000 | yes |
| HV functional VIN to PGND (outside the TO-247-4 pin fields) | 1.950 | 1.000 | 1.000 | 3.000 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | no |
| HV functional SW to PGND (outside the TO-247-4 pin fields) | 6.433 | 1.000 | 1.450 | 3.001 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | yes |
| HV functional VIN to SW (outside the TO-247-4 pin fields) | 3.000 | 23.582 | 1.000 | 23.582 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | yes |
| HV functional VOUT to PGND | 1.950 | 1.000 | 1.000 | 3.000 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | no |
| HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS) | 6.271 | 6.397 | 4.800 | 6.397 | F.Cu=3.000; In1.Cu=1.000; In2.Cu=1.000; B.Cu=3.000 | yes |

## Barrier strips (copper items per layer)

| Strip | Region | Box (mm) | F.Cu | In1.Cu | In2.Cu | B.Cu | Copper-free |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISO_BARRIER strip | rule area 'ISO_BARRIER' | 0.0, 140.0, 240.0, 150.0 | 0 | 0 | 0 | 0 | yes |

## Barrier parts: land gap, slot and surface path

| Ref | Found | HV pads | SELV pads | Land gap g (mm) | Slot | Extension e (mm) | Slot width (mm) | Surface path (mm) | Required e (mm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U1 | yes | 1, 2, 3, 4, 5, 6, 7, 8 | 9, 10, 11, 12, 13, 14, 15 | 7.250 | npth pad | 3.555 | 1.200 | 10.155 | 2.666 |
| U3 | yes | 1, 2, 3, 4, 5, 6, 7, 8 | 9, 10, 11, 12, 13, 14, 15 | 7.250 | npth pad | 3.555 | 1.200 | 10.155 | 2.666 |
| U2 | yes | 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 8.100 | npth pad | 3.000 | 1.200 | 10.080 | 1.962 |
| U4 | yes | 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 8.100 | npth pad | 3.000 | 1.200 | 10.080 | 1.962 |
| U5 | yes | 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 | 8.100 | npth pad | 3.000 | 1.200 | 10.080 | 1.962 |
| U6 | yes | 1, 2, 3, 4 | 5, 6, 7, 8 | 9.100 | npth pad | 3.195 | 1.200 | 11.119 | 0.000 |
| U7 | yes | 1, 2, 3, 4 | 5, 6, 7, 8 | 9.100 | npth pad | 3.195 | 1.200 | 11.119 | 0.000 |
| U10 | yes | 1, 2 | 3, 4, 6, 7, 8, 9, 10 | 7.750 | npth pad | 3.005 | 1.200 | 9.807 | 2.288 |

## Commutation loop proxies

| MOSFET | Role | Pin | Same-net cap (mm) | Pad | Any cap (mm) | Pad | Caps in row 1 | Caps in row 2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | HS | drain 1 (VIN) | 8.367 | C1.1 | 8.367 | C1.1 | 0 | 2 |
| Q1 | HS | source 2 (SW) | n/a | n/a | 13.307 | C1.1 | 0 | 0 |
| Q2 | LS | drain 1 (SW) | n/a | n/a | 36.083 | C1.1 | 0 | 0 |
| Q2 | LS | source 2 (PGND) | 41.165 | C1.2 | 41.153 | C1.1 | 0 | 0 |

Switch-node copper (mm2): F.Cu=196.200; In1.Cu=72.200; In2.Cu=3308.800; B.Cu=83.000

HV ceramic group bounding box (mm): 39.10, 122.45, 81.70, 139.95

## Gate loops

| MOSFET | Driver | Out->gate (mm) | Return->Kelvin (mm) | Gate track (mm) | Gate vias | Gate layers | Kelvin layers | Adjacent | Over Kelvin pour | KS distinct | KS copper min (mm) | KS copper contact | KS bridging parts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | U1 | 14.353 | 14.779 | 39.94 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.216 | yes | 0.300 | no |  |
| Q2 | U3 | 14.360 | 14.721 | 84.44 | 14 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.264 | yes | 0.300 | no |  |

## Heatsink envelope

| Layer | HV items | Min distance (mm) | Items within keep-out | Nearest |
| --- | --- | --- | --- | --- |
| F.Cu | 420 | 4.955 | 6 | pad C2.2 |
| B.Cu | 337 | 0.000 | 3 | pad R16.1 |

## Decoupling

| IC | Pad | Net | Capacitor pad | Distance (mm) | Same net |
| --- | --- | --- | --- | --- | --- |
| U1 | 5 | VDD_H | C37.1 | 6.858 | yes |
| U1 | 8 | VEE_H | C37.2 | 7.597 | yes |
| U3 | 5 | VDD_L | C56.1 | 4.656 | yes |
| U3 | 8 | VEE_L | C56.2 | 9.477 | yes |
| U2 | 6 | 12V_BIAS_H | C30.1 | 7.553 | yes |
| U2 | 7 | 12V_BIAS_H | C30.1 | 7.601 | yes |
| U2 | 19 | VEE_H | C35.2 | 9.370 | yes |
| U2 | 20 | VEE_H | C35.2 | 8.893 | yes |
| U2 | 21 | VEE_H | C35.2 | 8.439 | yes |
| U2 | 22 | VEE_H | C35.2 | 8.012 | yes |
| U2 | 23 | VEE_H | C35.2 | 7.617 | yes |
| U2 | 24 | VEE_H | C35.2 | 7.259 | yes |
| U2 | 25 | VEE_H | C35.2 | 6.943 | yes |
| U2 | 26 | VEE_H | C35.2 | 6.676 | yes |
| U2 | 27 | VEE_H | C35.2 | 6.463 | yes |
| U2 | 28 | VDD_H | C23.1 | 6.622 | yes |
| U2 | 29 | VDD_H | C23.1 | 6.287 | yes |
| U2 | 30 | VEE_H | C35.2 | 6.201 | yes |
| U2 | 31 | VEE_H | C35.2 | 6.248 | yes |
| U2 | 35 | VEE_H | C34.2 | 6.733 | yes |
| U2 | 36 | VEE_H | C34.2 | 6.507 | yes |
| U4 | 6 | 12V_BIAS_L | C50.1 | 13.493 | yes |
| U4 | 7 | 12V_BIAS_L | C50.1 | 13.911 | yes |
| U4 | 19 | VEE_L | C55.2 | 7.096 | yes |
| U4 | 20 | VEE_L | C55.2 | 7.034 | yes |
| U4 | 21 | VEE_L | C55.2 | 7.031 | yes |
| U4 | 22 | VEE_L | C59.2 | 7.034 | yes |
| U4 | 23 | VEE_L | C59.2 | 7.031 | yes |
| U4 | 24 | VEE_L | C59.2 | 7.089 | yes |
| U4 | 25 | VEE_L | C54.2 | 7.111 | yes |
| U4 | 26 | VEE_L | C54.2 | 7.039 | yes |
| U4 | 27 | VEE_L | C54.2 | 7.028 | yes |
| U4 | 28 | VDD_L | C57.1 | 8.565 | yes |
| U4 | 29 | VDD_L | C57.1 | 8.210 | yes |
| U4 | 30 | VEE_L | C57.2 | 7.055 | yes |
| U4 | 31 | VEE_L | C57.2 | 7.025 | yes |
| U4 | 35 | VEE_L | C58.2 | 7.200 | yes |
| U4 | 36 | VEE_L | C58.2 | 6.707 | yes |
| U5 | 6 | 12V_BIAS_S | C60.1 | 27.103 | yes |
| U5 | 7 | 12V_BIAS_S | C60.1 | 27.532 | yes |
| U5 | 28 | ISO_15V | C66.1 | 11.112 | yes |
| U5 | 29 | ISO_15V | C66.1 | 11.223 | yes |
| U6 | 1 | 5V_ISO | C72.1 | 4.336 | yes |
| U6 | 8 | 3V3 | C73.1 | 3.832 | yes |
| U7 | 1 | 5V_ISO | C76.1 | 4.353 | yes |
| U7 | 8 | 3V3 | C77.1 | 8.264 | yes |
| U8 | 8 | 3V3 | C88.1 | 3.656 | yes |
| U9 | 1 | 3V3 | C85.1 | 5.176 | yes |
| U10 | 9 | 3V3 | C87.1 | 15.508 | yes |
| U10 | 10 | 3V3 | C87.1 | 15.410 | yes |

## Sensing

| Pair | Nets | Track (mm) | Vias | Mismatch (mm) | Min to SW (mm) |
| --- | --- | --- | --- | --- | --- |
| AMC1311 VIN differential output | VIN_OUTP, VIN_OUTN | VIN_OUTP=80.91; VIN_OUTN=79.40 | VIN_OUTP=2; VIN_OUTN=0 | 1.508 | 29.182 |
| AMC1311 VOUT differential output | VOUT_OUTP, VOUT_OUTN | VOUT_OUTP=64.91; VOUT_OUTN=63.15 | VOUT_OUTP=2; VOUT_OUTN=2 | 1.758 | 36.050 |
| TMCS1133 ISENSE / ISENSE_REF | ISENSE, ISENSE_REF | ISENSE=83.80; ISENSE_REF=90.10 | ISENSE=7; ISENSE_REF=5 | 6.304 | 32.354 |

| Part | Found | Min to SW (mm) |
| --- | --- | --- |
| U6 | yes | 22.344 |
| U7 | yes | 25.150 |
| U10 | yes | 27.345 |
| U8 | yes | 42.073 |

## Control section

Control parts: 86, power parts: 131, bounding-box separation 12.307 mm.

| Ground layer | Area (mm2) | Islands | Zones | Required probes covered | Forbidden probes copper-free |
| --- | --- | --- | --- | --- | --- |
| In1.Cu | 5866.4 | 1 | 1 | 0/0 | 0/0 |

## Compactness

| Metric | Value |
| --- | --- |
| Board area (mm2 / dm2) | 43200.0 / 4.320 |
| Footprints per dm2 | 54.9 |
| Courtyard fraction front / back | 0.594 / 0.010 |
| HV bounding-box fraction of board | 0.770 |
| HV copper on outer layers (mm2, fraction of both sides) | 21331.8 (0.247) |
| Tallest component | HS1 50.0 mm |
| Assembly height (mm) declared / computed / used | 72, 52.0, 72.0 |
| Rated power (W) | 5000 |
| Power density (W/dm2, W/L) | 1157.4, 1607.5 |

## Classified nets

| Net | Class | Track (mm) | Tracks | Vias | Pads | Layers | Zone area (mm2) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12V_BIAS_H | CTRL_SELV | 30.4 | 11 | 4 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_BIAS_L | CTRL_SELV | 37.8 | 26 | 2 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_BIAS_S | CTRL_SELV | 100.1 | 96 | 6 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_PROT | CTRL_SELV | 276.6 | 261 | 14 | 11 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 3V3 | CTRL_SELV | 433.9 | 389 | 22 | 31 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=4152.300 |
| 5V_ISO | SENSE_ISO | 66.4 | 65 | 7 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BIAS_EN | CTRL_SELV | 147.9 | 107 | 10 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BIAS_EN_F | CTRL_SELV | 133.2 | 74 | 9 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BLD_IN_1 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| BLD_IN_2 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| BLD_OUT_1 | HV_VOUT | 0.9 | 1 | 0 | 2 | F.Cu |  |
| DAMP_MID | HV_VIN | 25.9 | 5 | 0 | 4 | F.Cu |  |
| DESAT_H_A | DESAT_HS | 37.1 | 29 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_H_OC | DESAT_HS | 29.3 | 34 | 3 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_L_A | DESAT_LS | 44.0 | 28 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_L_OC | DESAT_LS | 99.1 | 107 | 5 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAN_TACH | CTRL_SELV | 158.5 | 47 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FAULT_N | CTRL_SELV | 33.4 | 31 | 3 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_H_N | CTRL_SELV | 166.3 | 198 | 11 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_L_N | CTRL_SELV | 120.0 | 130 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_H | CTRL_SELV | 49.8 | 40 | 3 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_L | CTRL_SELV | 55.9 | 43 | 4 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_S | CTRL_SELV | 119.3 | 142 | 9 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GND_CTRL | CTRL_SELV | 153.5 | 140 | 62 | 68 | F.Cu, In1.Cu, In2.Cu, B.Cu | In1.Cu=5866.400 |
| G_H | DRV_HS | 26.4 | 28 | 0 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu | B.Cu=77.200 |
| G_L | DRV_LS | 33.1 | 29 | 7 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu | B.Cu=34.400 |
| HS_CLMP | DRV_HS | 5.5 | 6 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_FB_VDD | DRV_HS | 13.6 | 8 | 1 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_FB_VEE | DRV_HS | 8.3 | 5 | 1 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_GK | DRV_HS | 6.6 | 8 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_OUTH | DRV_HS | 4.1 | 8 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_OUTL | DRV_HS | 4.0 | 4 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| HS_RLIM | DRV_HS | 9.4 | 14 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| IND_IN_1 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| IND_IN_2 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| IND_IN_3 | HV_VIN | 1.4 | 1 | 0 | 2 | F.Cu |  |
| IND_OUT_1 | HV_VOUT | 0.9 | 1 | 0 | 2 | F.Cu |  |
| IND_OUT_2 | HV_VOUT | 1.4 | 1 | 0 | 2 | F.Cu |  |
| ISENSE | CTRL_SELV | 83.8 | 56 | 7 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISENSE_REF | CTRL_SELV | 90.1 | 94 | 5 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISO_15V | SENSE_ISO | 32.6 | 18 | 1 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISO_FB_VDD | SENSE_ISO | 17.7 | 12 | 1 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISO_FB_VEE | SENSE_ISO | 13.2 | 8 | 1 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISO_RLIM | SENSE_ISO | 8.7 | 14 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| K1_LOW | CTRL_SELV | 16.8 | 3 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_H | DRV_HS | 97.7 | 76 | 11 | 17 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=501.400 |
| KS_L | DRV_LS | 88.2 | 73 | 9 | 17 | F.Cu, In1.Cu, In2.Cu, B.Cu | In2.Cu=248.300 |
| LS_CLMP | DRV_LS | 21.4 | 28 | 3 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_FB_VDD | DRV_LS | 72.8 | 111 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_FB_VEE | DRV_LS | 44.2 | 56 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_GK | DRV_LS | 13.2 | 30 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_OUTH | DRV_LS | 19.7 | 19 | 3 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_OUTL | DRV_LS | 10.2 | 6 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| LS_RLIM | DRV_LS | 17.2 | 6 | 3 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_N | CTRL_SELV | 75.7 | 74 | 6 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PE | PE | 76.9 | 6 | 0 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PE_REF_MID | HV_PGND | 3.1 | 1 | 0 | 2 | B.Cu |  |
| PGND | HV_PGND | 22.5 | 20 | 90 | 81 | F.Cu, In1.Cu, In2.Cu, B.Cu | B.Cu=9042.000; In1.Cu=28679.700 |
| PG_BIAS_H_N | CTRL_SELV | 268.5 | 182 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_L_N | CTRL_SELV | 56.4 | 33 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PG_BIAS_S_N | CTRL_SELV | 52.4 | 24 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_H | CTRL_SELV | 132.3 | 127 | 4 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_H_F | CTRL_SELV | 56.9 | 31 | 2 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_L | CTRL_SELV | 111.6 | 136 | 7 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_L_F | CTRL_SELV | 54.7 | 35 | 6 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_H | CTRL_SELV | 128.0 | 77 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_L | CTRL_SELV | 112.3 | 101 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| REF2V5_PB | CTRL_SELV | 12.4 | 8 | 0 | 3 | F.Cu |  |
| RELAY_ON | CTRL_SELV | 203.9 | 108 | 5 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RESET_N | CTRL_SELV | 129.2 | 144 | 3 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RESET_N_F | CTRL_SELV | 48.1 | 43 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RLY_G | CTRL_SELV | 18.1 | 11 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SNUB_MID | HV_SW | 1.5 | 1 | 0 | 2 | F.Cu |  |
| SPARE_D1 | CTRL_SELV | 12.2 | 4 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SPARE_D2 | CTRL_SELV | 47.0 | 57 | 3 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SW | HV_SW | 9.6 | 2 | 25 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=120.000; In2.Cu=3236.600 |
| VDD_H | DRV_HS | 86.3 | 68 | 9 | 11 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDD_L | DRV_LS | 80.1 | 59 | 6 | 11 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_H | DRV_HS | 88.4 | 85 | 9 | 24 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_L | DRV_LS | 100.1 | 148 | 16 | 24 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN | HV_VIN | 3.1 | 1 | 34 | 33 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=4530.400; In2.Cu=16940.000 |
| VIN_AMP_N | CTRL_SELV | 35.0 | 27 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_AMP_P | CTRL_SELV | 29.0 | 30 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_DIV | SENSE_ISO | 30.2 | 27 | 3 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_DIV_T1 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| VIN_DIV_T2 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| VIN_DIV_T3 | HV_VIN | 0.9 | 1 | 0 | 2 | F.Cu |  |
| VIN_OUTN | CTRL_SELV | 79.4 | 24 | 0 | 2 | F.Cu |  |
| VIN_OUTP | CTRL_SELV | 80.9 | 30 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VIN_RAW | HV_VIN | 51.3 | 3 | 0 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=422.800; B.Cu=422.800 |
| VIN_SENSE | CTRL_SELV | 71.6 | 89 | 5 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOC_SET | CTRL_SELV | 12.0 | 12 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT | HV_VOUT | 6.1 | 2 | 63 | 17 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=2218.800; B.Cu=2406.000; In2.Cu=3126.300 |
| VOUT_AMP_N | CTRL_SELV | 25.5 | 16 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_AMP_P | CTRL_SELV | 22.2 | 24 | 0 | 4 | F.Cu |  |
| VOUT_DIV | SENSE_ISO | 21.2 | 19 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_DIV_T1 | HV_VOUT | 0.9 | 1 | 0 | 2 | F.Cu |  |
| VOUT_L | HV_VOUT | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=422.200 |
| VOUT_OUTN | CTRL_SELV | 63.1 | 19 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_OUTP | CTRL_SELV | 64.9 | 15 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOUT_SENSE | CTRL_SELV | 71.3 | 97 | 8 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |

## Notes and limitations

- Straight-line pad distances, track sums and copper areas are geometric proxies; they are not loop inductance, current-path length, creepage per standard or EMI performance.
- Isolation distances are copper-to-copper on each layer (pads, tracks, vias, filled zones); through-air clearance between layers, component bodies, solder mask and coatings are not evaluated.
- Thresholds are those given in the layout spec (taken from the design baseline); no acceptance limit is invented here. Engineering acceptance of every row remains a human responsibility.
- Slot detection relies on non-plated oblong pads or Edge.Cuts graphics inside the barrier part courtyard; the fabricator must confirm the slot width after tolerance.
- Reference designators, pad numbers and net names follow design/circuit_power.json and the placed board generated by automation/kicad_tools/generate_sic_power_board.py: Q1 = HS C4MS025120K (TO-247-4 pads 1 D, 2 S, 3 KS, 4 G), Q2 = LS; U1/U3 = UCC21710 HS/LS drivers (pads 4 OUTH, 6 OUTL, 1 AIN = COM, 3 COM); U2/U4/U5 = UCC14141 HS/LS/sensing bias; U6/U7 = AMC1311 VIN/VOUT sense; U10 = TMCS1133; C1-C10 HF ceramics; C11/C12 input films; C13/C14 output films; L1 toroid; HS1 heatsink envelope; J7 mezzanine socket.
- Net classes copy the project net-class patterns of kicad/power_board/AIPE_SiC_Buck_Power.kicad_pro (first match in order); the barrier parts are the eight isolators on the straight barrier line.
- Thresholds are copied from design/design_decisions.json (architecture.target_metrics_after_layout, standards_and_spacing.kicad_rules_mm, standards_and_spacing.slots, architecture.power_board.heatsink); the checker adds none of its own. Rows for absent refs are reported as not measured, never as passed.
- ISO_BARRIER is realised as one full-length rule area named ISO_BARRIER in the generated board (checked for copper on every layer); the barrier parts bridge the band over their slots.
