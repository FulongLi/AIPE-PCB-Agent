# Layout metrics - AIPE 10 kW DAB - primary power board (800 V bus) - layout metrics spec (derived from requirements)

Status: **measured-human-review-required**. Generated 2026-10-21T07:15:38.416989+00:00 by `automation/verification/check_sic_layout.py` (pcbnew 10.0.6, distance backend numpy, 0.828 s).

Board `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\primary-power\dab-primary.kicad_pcb` (sha256 `fd10e2ec8827f097...`), spec `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\verification\engineering_checks\layout_spec_primary-power.json`, model `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\design\circuit_primary-power.json`.

## Board

| Metric | Value |
| --- | --- |
| Outline (mm) | 300.00 x 150.00 |
| Outline area (mm2) | 45000.0 |
| Copper layers | 4 (F.Cu, In1.Cu, In2.Cu, B.Cu) |
| Thickness (mm) | 2.000 |
| Copper thickness (um, stackup text) | F.Cu=70.000; In1.Cu=70.000; In2.Cu=70.000; B.Cu=70.000 |
| Footprints / tracks / vias / zones / rule areas | 309 / 2470 / 411 / 23 / 0 |
| Nets | 133 |
| Zones without fill (areas read from the file) | none |
| Expected (spec) | outline_mm=300, 150; copper_layers=4; copper_um=70; thickness_mm=2.000 |

## Rule table

Dispositions follow the spec thresholds only; every row needs engineering acceptance by a human reviewer.

| Rule | Requirement | Metric | Measured | Threshold | Disposition | Note |
| --- | --- | --- | --- | --- | --- | --- |
| PE-PCB-001 | Minimise MOSFET gate loop | U2 output pad 4 to Q1 gate pad 4 | 52.571 | <= 15 mm | exceeds spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_AH/OUTH_AH/OUTL_AH track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_AH layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=85.440; adjacent=yes; over_kelvin_pour=0.000 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-001 | Minimise MOSFET gate loop | U4 output pad 4 to Q2 gate pad 4 | 52.571 | <= 15 mm | exceeds spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_AL/OUTH_AL/OUTL_AL track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_AL layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=82.540; adjacent=yes; over_kelvin_pour=0.000 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-001 | Minimise MOSFET gate loop | U6 output pad 4 to Q3 gate pad 4 | 50.956 | <= 15 mm | exceeds spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_BL/OUTH_BL/OUTL_BL track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_BL layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=84.060; adjacent=yes; over_kelvin_pour=0.000 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-001 | Minimise MOSFET gate loop | U8 output pad 4 to Q4 gate pad 4 | 50.956 | <= 15 mm | exceeds spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_BH/OUTH_BH/OUTL_BH track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_BH layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=89.750; adjacent=yes; over_kelvin_pour=0.000 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q1 drain pad 1 (BUS_P) to nearest HF capacitor pad of the same net | 15.789 | <= 30.0 mm (row 2; row 1 <= 15.0 mm) | within spec threshold - human review required | nearest C3.1 |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q1 source pad 2 (SW_A) to nearest HF capacitor pad (any named net) | 15.773 | n/a | measured - human review required | pad net is not a capacitor net (switch node) |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q2 drain pad 1 (SW_A) to nearest HF capacitor pad (any named net) | 9.685 | n/a | measured - human review required | pad net is not a capacitor net (switch node) |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q2 source pad 2 (PGND) to nearest HF capacitor pad of the same net | 10.969 | <= 30.0 mm (row 2; row 1 <= 15.0 mm) | within spec threshold - human review required | nearest C4.2 |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q3 drain pad 1 (SW_B) to nearest HF capacitor pad (any named net) | 9.827 | n/a | measured - human review required | pad net is not a capacitor net (switch node) |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q3 source pad 2 (PGND) to nearest HF capacitor pad of the same net | 9.517 | <= 30.0 mm (row 2; row 1 <= 15.0 mm) | within spec threshold - human review required | nearest C9.2 |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q4 drain pad 1 (BUS_P) to nearest HF capacitor pad of the same net | 10.936 | <= 30.0 mm (row 2; row 1 <= 15.0 mm) | within spec threshold - human review required | nearest C12.1 |
| PE-PCB-002 | Place HF DC-link capacitors close to the half bridge | Q4 source pad 2 (SW_B) to nearest HF capacitor pad (any named net) | 9.338 | n/a | measured - human review required | pad net is not a capacitor net (switch node) |
| PE-PCB-003 | Minimise HF commutation loop | SW_A copper area, all layers (mm2; per layer in JSON) | 1495.200 | n/a | measured - human review required | switch-node copper is a dv/dt coupling and radiation proxy; the baseline asks for the minimum that carries the current |
| PE-PCB-003 | Minimise HF commutation loop | HV ceramic group bounding box (x0, y0, x1, y1 mm) and pin distances (JSON) | 73.550, 24.800, 200.250, 30.200 | n/a | measured - human review required | bounding box of the HF capacitor pads on the named nets |
| PE-PCB-004 | Use Kelvin current sensing | AMC1311 differential output track lengths (mm) and mismatch | VSNS_P=0.896; VSNS_N=90.011; mismatch=89.115 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | AMC1311 differential output minimum copper distance to SW_A (mm, any layer) | 88.465 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U1 pads: minimum copper distance to SW_A (mm, any layer) | 112.832 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U11 pads: minimum copper distance to SW_A (mm, any layer) | 83.433 | n/a | measured - human review required |  |
| PE-PCB-006 | Justify high-current copper and via capacity | AC_B copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=191.200; In1.Cu=201.200; vias=1; track_mm=2.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BLD1 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BLD2 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BLD3 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BLD4 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BLD5 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BUS_P copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=1394.600; B.Cu=1372.700; In1.Cu=5978.200; vias=12; track_mm=44.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | DESAT_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=1; track_mm=12.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | DESAT_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=14.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | DESAT_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=21.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | DESAT_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=18.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVDD_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=27.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVDD_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=27.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVDD_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=26.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVDD_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=25.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVEE_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=4.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVEE_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=4.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVEE_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=6.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVEE_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=6.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | G_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=68.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | G_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=66.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | G_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=71.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | G_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=66.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | KS_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=10; track_mm=114.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | KS_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=12; track_mm=119.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | KS_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=7; track_mm=113.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | KS_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=7; track_mm=112.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTCR_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=0.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTCR_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=9.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTCR_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=12.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTCR_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=11.100 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTC_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=36.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTC_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=45.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTC_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=24.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTC_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=24.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OC_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=45.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OC_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=46.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OC_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=22.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OC_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=21.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTH_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTH_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTH_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.600 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTH_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.600 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTL_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTL_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTL_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=9.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTL_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=9.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | PGND copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=1438.900; B.Cu=1407.400; In2.Cu=7008.100; vias=36; track_mm=104.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RDR_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=16.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RDR_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=19.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RDR_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=11.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RDR_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=11.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RLIM_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=2.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RLIM_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=2.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RLIM_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=6.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RLIM_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=6.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | SW_A copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=203.100; B.Cu=919.200; vias=0; track_mm=0.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | SW_B copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=180.800; B.Cu=2459.800; vias=0; track_mm=0.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_16V copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=7; track_mm=44.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_5V copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=5; track_mm=30.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_FBVDD copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=10.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_FBVEE copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=3.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_RLIM copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=0.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_VEEA copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=39.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VADC_IN copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=6.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDD_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=13; track_mm=73.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDD_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=16; track_mm=97.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDD_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=8; track_mm=76.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDD_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=8; track_mm=75.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV1 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=2.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV2 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV3 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV4 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=2.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV5 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=2.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV6 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=2.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV7 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=16.100 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEEA_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=42.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEEA_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=22.100 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEEA_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=18.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEEA_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=17.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEE_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=7; track_mm=106.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEE_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=7; track_mm=135.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEE_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=10; track_mm=96.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEE_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=6; track_mm=112.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | XF_B copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=360.000; B.Cu=360.000; vias=1; track_mm=2.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-007 | Separate control and switching structures | control section (82 parts) to power stage (207 parts) bounding-box distance (mm) | 7.960 | >= 8.0 mm | exceeds spec threshold - human review required |  |
| PE-PCB-007 | Separate control and switching structures | GND_CTRL zone area (mm2) and island count per layer | In1.Cu=area=19835.000; islands=1 | n/a | measured - human review required | V1 ground-plane extent guard generalised |
| PE-PCB-007 | Separate control and switching structures | board area (mm2), footprints per dm2, courtyard fraction front/back | area=45000.000; per_dm2=68.700; courtyard=front=0.250; back=0.002 | n/a | measured - human review required | HV bbox fraction 0.464; power density n/a W/dm2, n/a W/L |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U2 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 2.547 | <= 15 mm | within spec threshold - human review required | 5->C25.1 2.45; 8->C26.2 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U4 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 2.547 | <= 15 mm | within spec threshold - human review required | 5->C49.1 2.45; 8->C50.2 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U6 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 2.547 | <= 15 mm | within spec threshold - human review required | 5->C73.1 2.45; 8->C74.2 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U8 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 2.547 | <= 15 mm | within spec threshold - human review required | 5->C97.1 2.45; 8->C98.2 2.55 |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_AH versus SW_A: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.250 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_AL versus PGND: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.250 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_BL versus PGND: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.250 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_BH versus SW_B: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.250 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | barrier strip copper check | n/a | n/a | not measured - spec input missing or reference not found | no barrier_keepouts in the spec |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV domains to SELV (all layers): minimum copper distance per layer (mm) | F.Cu=8.450; In1.Cu=8.002; In2.Cu=9.650; B.Cu=8.925 | all=8.000 mm | within spec threshold - human review required |  |
| KR-ISO-004 | Slots and cut-outs to extend creepage | slots under barrier parts | n/a | n/a | not measured - spec input missing or reference not found | no barrier_parts in the spec |
| KR-TH-002 | Rated insulating interface for shared heat sinks (HV copper keep-out at the sink) | HS1: minimum HV copper distance to the heatsink courtyard on the outer layers (mm) | F.Cu=0.000 | >= 5.0 mm | exceeds spec threshold - human review required | baseline: >= 5 mm HV copper keep-out around the PE-bonded sink; pad/clip insulation itself is a human-review item |

Rows: 122 - within spec threshold 13, exceeding 6, measured without threshold 101, not measured 2.

## Isolation: minimum copper distance per layer (mm)

| Pair | F.Cu | In1.Cu | In2.Cu | B.Cu | Threshold | Within |
| --- | --- | --- | --- | --- | --- | --- |
| HV domains to SELV (all layers) | 8.450 | 8.002 | 9.650 | 8.925 | F.Cu=8.000; In1.Cu=8.000; In2.Cu=8.000; B.Cu=8.000 | yes |

## Commutation loop proxies

| MOSFET | Role | Pin | Same-net cap (mm) | Pad | Any cap (mm) | Pad | Caps in row 1 | Caps in row 2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | HS | drain 1 (BUS_P) | 15.789 | C3.1 | 12.170 | C3.2 | 0 | 1 |
| Q1 | HS | source 2 (SW_A) | n/a | n/a | 15.774 | C3.2 | 0 | 0 |
| Q2 | LS | drain 1 (SW_A) | n/a | n/a | 9.685 | C4.2 | 0 | 0 |
| Q2 | LS | source 2 (PGND) | 10.969 | C4.2 | 9.685 | C4.1 | 3 | 5 |
| Q3 | LS | drain 1 (SW_B) | n/a | n/a | 9.827 | C9.2 | 0 | 0 |
| Q3 | LS | source 2 (PGND) | 9.517 | C9.2 | 9.517 | C9.2 | 2 | 7 |
| Q4 | HS | drain 1 (BUS_P) | 10.936 | C12.1 | 10.936 | C12.1 | 1 | 3 |
| Q4 | HS | source 2 (SW_B) | n/a | n/a | 9.338 | C12.1 | 0 | 0 |

Switch-node copper (mm2): F.Cu=296.300; In1.Cu=93.200; In2.Cu=93.200; B.Cu=1012.500

HV ceramic group bounding box (mm): 73.55, 24.80, 200.25, 30.20

## Gate loops

| MOSFET | Driver | Out->gate (mm) | Return->Kelvin (mm) | Gate track (mm) | Gate vias | Gate layers | Kelvin layers | Adjacent | Over Kelvin pour | KS distinct | KS copper min (mm) | KS copper contact | KS bridging parts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | U2 | 52.571 | 51.875 | 85.44 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.000 | yes | 0.251 | no |  |
| Q2 | U4 | 52.571 | 51.875 | 82.54 | 8 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.000 | yes | 0.251 | no |  |
| Q3 | U6 | 50.956 | 51.004 | 84.06 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.000 | yes | 0.251 | no |  |
| Q4 | U8 | 50.956 | 51.004 | 89.75 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.000 | yes | 0.251 | no |  |

## Heatsink envelope

| Layer | HV items | Min distance (mm) | Items within keep-out | Nearest |
| --- | --- | --- | --- | --- |
| F.Cu | 2007 | 0.000 | 17 | zone BUS_P |

## Decoupling

| IC | Pad | Net | Capacitor pad | Distance (mm) | Same net |
| --- | --- | --- | --- | --- | --- |
| U2 | 5 | VDD_AH | C25.1 | 2.452 | yes |
| U2 | 8 | VEE_AH | C26.2 | 2.547 | yes |
| U4 | 5 | VDD_AL | C49.1 | 2.452 | yes |
| U4 | 8 | VEE_AL | C50.2 | 2.547 | yes |
| U6 | 5 | VDD_BL | C73.1 | 2.452 | yes |
| U6 | 8 | VEE_BL | C74.2 | 2.547 | yes |
| U8 | 5 | VDD_BH | C97.1 | 2.452 | yes |
| U8 | 8 | VEE_BH | C98.2 | 2.547 | yes |

## Sensing

| Pair | Nets | Track (mm) | Vias | Mismatch (mm) | Min to SW (mm) |
| --- | --- | --- | --- | --- | --- |
| AMC1311 differential output | VSNS_P, VSNS_N | VSNS_P=0.90; VSNS_N=90.01 | VSNS_P=0; VSNS_N=1 | 89.115 | 88.465 |

| Part | Found | Min to SW (mm) |
| --- | --- | --- |
| U1 | yes | 112.832 |
| U11 | yes | 83.433 |

## Control section

Control parts: 82, power parts: 207, bounding-box separation 7.960 mm.

| Ground layer | Area (mm2) | Islands | Zones | Required probes covered | Forbidden probes copper-free |
| --- | --- | --- | --- | --- | --- |
| In1.Cu | 19835.0 | 1 | 1 | 0/0 | 0/0 |

## Compactness

| Metric | Value |
| --- | --- |
| Board area (mm2 / dm2) | 45000.0 / 4.500 |
| Footprints per dm2 | 68.7 |
| Courtyard fraction front / back | 0.250 / 0.002 |
| HV bounding-box fraction of board | 0.464 |
| HV copper on outer layers (mm2, fraction of both sides) | 12154.1 (0.135) |
| Tallest component | U9 0.0 mm |
| Assembly height (mm) declared / computed / used | n/a, 2.0, 2.0 |
| Rated power (W) | n/a |
| Power density (W/dm2, W/L) | n/a, n/a |

## Classified nets

| Net | Class | Track (mm) | Tracks | Vias | Pads | Layers | Zone area (mm2) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12V_BIAS_AH | CTRL | 18.1 | 12 | 2 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_BIAS_AL | CTRL | 18.1 | 11 | 2 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_BIAS_BH | CTRL | 18.1 | 11 | 2 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_BIAS_BL | CTRL | 18.1 | 11 | 2 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 12V_BIAS_S | CTRL | 21.5 | 12 | 0 | 7 | F.Cu |  |
| 12V_E | CTRL | 249.5 | 35 | 11 | 10 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 3V3 | CTRL | 412.7 | 140 | 22 | 35 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| AC_B | HV_00 | 2.2 | 2 | 1 | 10 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=191.200; In1.Cu=201.200 |
| BIAS_EN | CTRL | 28.3 | 3 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BIAS_ENF | CTRL | 4.6 | 5 | 0 | 8 | F.Cu |  |
| BLD1 | HV_16 | 1.9 | 1 | 0 | 2 | B.Cu |  |
| BLD2 | HV_14 | 1.9 | 1 | 0 | 2 | B.Cu |  |
| BLD3 | HV_12 | 1.8 | 1 | 0 | 2 | B.Cu |  |
| BLD4 | HV_10 | 1.9 | 1 | 0 | 2 | B.Cu |  |
| BLD5 | HV_08 | 1.9 | 1 | 0 | 2 | B.Cu |  |
| BUS_P | HV_02 | 44.3 | 14 | 12 | 29 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=1394.600; B.Cu=1372.700; In1.Cu=5978.200 |
| DESAT_AH | HV_03 | 12.0 | 3 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_AL | HV_04 | 14.4 | 4 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_BH | HV_05 | 21.3 | 4 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_BL | HV_06 | 18.9 | 4 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DRV_RST | CTRL | 28.0 | 3 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DRV_RSTF | CTRL | 126.7 | 35 | 6 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVDD_AH | HV_03 | 27.2 | 14 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVDD_AL | HV_04 | 27.2 | 14 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVDD_BH | HV_05 | 26.5 | 16 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVDD_BL | HV_06 | 25.9 | 14 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVEE_AH | HV_03 | 4.7 | 2 | 0 | 4 | F.Cu |  |
| FBVEE_AL | HV_04 | 4.7 | 2 | 0 | 4 | F.Cu |  |
| FBVEE_BH | HV_05 | 6.9 | 7 | 0 | 4 | F.Cu |  |
| FBVEE_BL | HV_06 | 6.9 | 7 | 0 | 4 | F.Cu |  |
| FLT_AH_N | CTRL | 94.7 | 11 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_AL_N | CTRL | 69.6 | 11 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_BH_N | CTRL | 83.9 | 7 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_BL_N | CTRL | 65.4 | 8 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_AH | CTRL | 40.7 | 62 | 7 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_AL | CTRL | 56.1 | 66 | 4 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_BH | CTRL | 54.9 | 65 | 4 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_BL | CTRL | 68.1 | 68 | 4 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_S | CTRL | 87.5 | 59 | 0 | 19 | F.Cu |  |
| GND_CTRL | CTRL | 57.7 | 90 | 41 | 57 | F.Cu, In1.Cu, In2.Cu, B.Cu | In1.Cu=19835.000 |
| G_AH | HV_03 | 68.9 | 18 | 2 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G_AL | HV_04 | 66.0 | 17 | 4 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G_BH | HV_05 | 71.8 | 20 | 3 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G_BL | HV_06 | 66.2 | 20 | 3 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISNS | CTRL | 131.7 | 16 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_AH | HV_03 | 114.8 | 68 | 10 | 21 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_AL | HV_04 | 119.2 | 72 | 12 | 21 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_BH | HV_05 | 113.9 | 72 | 7 | 21 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_BL | HV_06 | 112.2 | 72 | 7 | 21 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTCR_AH | HV_03 | 0.0 | 0 | 0 | 2 | F.Cu |  |
| NTCR_AL | HV_04 | 9.5 | 10 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTCR_BH | HV_05 | 12.8 | 7 | 0 | 2 | F.Cu |  |
| NTCR_BL | HV_06 | 11.1 | 8 | 0 | 2 | F.Cu |  |
| NTC_AH | HV_03 | 36.7 | 16 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTC_AL | HV_04 | 45.0 | 15 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTC_BH | HV_05 | 24.5 | 17 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTC_BL | HV_06 | 24.5 | 17 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTC_HS | CTRL | 7.4 | 5 | 0 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_AH | HV_03 | 45.3 | 23 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_AL | HV_04 | 46.7 | 26 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_BH | HV_05 | 22.3 | 12 | 4 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_BL | HV_06 | 21.3 | 12 | 4 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_TRIP_N | CTRL | 143.9 | 16 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OUTH_AH | HV_03 | 8.2 | 3 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OUTH_AL | HV_04 | 8.2 | 3 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OUTH_BH | HV_05 | 8.6 | 3 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OUTH_BL | HV_06 | 8.6 | 3 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OUTL_AH | HV_03 | 8.3 | 3 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OUTL_AL | HV_04 | 8.3 | 3 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OUTL_BH | HV_05 | 9.3 | 3 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OUTL_BL | HV_06 | 9.3 | 3 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PGND | HV_01 | 104.5 | 82 | 36 | 52 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=1438.900; B.Cu=1407.400; In2.Cu=7008.100 |
| PG_BIAS_N | CTRL | 47.3 | 15 | 1 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWMF_AH | CTRL | 56.6 | 14 | 4 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWMF_AL | CTRL | 58.7 | 16 | 3 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWMF_BH | CTRL | 58.0 | 17 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWMF_BL | CTRL | 61.2 | 20 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_AH | CTRL | 49.1 | 4 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_AL | CTRL | 44.3 | 2 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_BH | CTRL | 74.6 | 4 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_BL | CTRL | 47.7 | 3 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDR_AH | HV_03 | 16.0 | 17 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDR_AL | HV_04 | 19.5 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDR_BH | HV_05 | 11.2 | 8 | 0 | 2 | F.Cu |  |
| RDR_BL | HV_06 | 11.2 | 8 | 0 | 2 | F.Cu |  |
| RDY_AH | CTRL | 100.5 | 11 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_AL | CTRL | 71.2 | 10 | 4 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_BH | CTRL | 84.6 | 11 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_BL | CTRL | 62.8 | 9 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RLIM_AH | HV_03 | 2.8 | 1 | 0 | 3 | F.Cu |  |
| RLIM_AL | HV_04 | 2.8 | 1 | 0 | 3 | F.Cu |  |
| RLIM_BH | HV_05 | 6.7 | 5 | 0 | 3 | F.Cu |  |
| RLIM_BL | HV_06 | 6.7 | 5 | 0 | 3 | F.Cu |  |
| SDFM_CLK | CTRL | 56.1 | 4 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SDFM_D | CTRL | 0.0 | 0 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SW_A | HV_19 | 0.0 | 0 | 0 | 12 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=203.100; B.Cu=919.200 |
| SW_B | HV_20 | 0.0 | 0 | 0 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=180.800; B.Cu=2459.800 |
| S_16V | HV_18 | 44.3 | 37 | 7 | 9 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_5V | HV_18 | 30.4 | 15 | 5 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_FBVDD | HV_18 | 10.8 | 6 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_FBVEE | HV_18 | 3.8 | 2 | 0 | 4 | F.Cu |  |
| S_RLIM | HV_18 | 0.0 | 0 | 0 | 2 | F.Cu |  |
| S_VEEA | HV_18 | 39.0 | 31 | 2 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_HS | CTRL | 136.7 | 13 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_PWM_AH | CTRL | 103.1 | 17 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_PWM_AL | CTRL | 74.5 | 7 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_PWM_BH | CTRL | 77.3 | 10 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_PWM_BL | CTRL | 60.7 | 7 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VADC_IN | HV_18 | 6.0 | 7 | 0 | 4 | F.Cu |  |
| VDD_AH | HV_03 | 73.9 | 50 | 13 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDD_AL | HV_04 | 97.5 | 53 | 16 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDD_BH | HV_05 | 76.8 | 55 | 8 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDD_BL | HV_06 | 75.5 | 56 | 8 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDIV1 | HV_17 | 2.2 | 2 | 0 | 2 | F.Cu |  |
| VDIV2 | HV_15 | 1.8 | 1 | 0 | 2 | F.Cu |  |
| VDIV3 | HV_13 | 1.8 | 1 | 0 | 2 | F.Cu |  |
| VDIV4 | HV_12 | 2.3 | 2 | 0 | 2 | F.Cu |  |
| VDIV5 | HV_11 | 2.2 | 2 | 0 | 2 | F.Cu |  |
| VDIV6 | HV_09 | 2.0 | 2 | 0 | 2 | F.Cu |  |
| VDIV7 | HV_07 | 16.1 | 8 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEEA_AH | HV_03 | 42.0 | 30 | 4 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEEA_AL | HV_04 | 22.1 | 16 | 0 | 6 | F.Cu |  |
| VEEA_BH | HV_05 | 18.8 | 18 | 0 | 6 | F.Cu |  |
| VEEA_BL | HV_06 | 17.4 | 13 | 2 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_AH | HV_03 | 106.7 | 71 | 7 | 23 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_AL | HV_04 | 135.7 | 71 | 7 | 23 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_BH | HV_05 | 96.5 | 72 | 10 | 23 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_BL | HV_06 | 112.9 | 79 | 6 | 23 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOC_SET | CTRL | 11.1 | 9 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VSNS_N | CTRL | 90.0 | 10 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VSNS_P | CTRL | 0.9 | 2 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| XF_B | HV_00 | 2.2 | 2 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=360.000; B.Cu=360.000 |

## Notes and limitations

- Straight-line pad distances, track sums and copper areas are geometric proxies; they are not loop inductance, current-path length, creepage per standard or EMI performance.
- Isolation distances are copper-to-copper on each layer (pads, tracks, vias, filled zones); through-air clearance between layers, component bodies, solder mask and coatings are not evaluated.
- Thresholds are those given in the layout spec (taken from the design baseline); no acceptance limit is invented here. Engineering acceptance of every row remains a human responsibility.
- Slot detection relies on non-plated oblong pads or Edge.Cuts graphics inside the barrier part courtyard; the fabricator must confirm the slot width after tolerance.
- Generated by automation.dab_v1.verify from the requirement files; thresholds are the unverified design targets of specification.yaml.
