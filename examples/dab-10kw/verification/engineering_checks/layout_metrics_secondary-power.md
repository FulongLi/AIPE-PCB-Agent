# Layout metrics - AIPE 10 kW DAB - secondary power board (400 V bus) - layout metrics spec (derived from requirements)

Status: **measured-human-review-required**. Generated 2026-10-21T07:16:50.821031+00:00 by `automation/verification/check_sic_layout.py` (pcbnew 10.0.6, distance backend numpy, 0.86 s).

Board `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\secondary-power\dab-secondary.kicad_pcb` (sha256 `950f865e72268c6c...`), spec `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\verification\engineering_checks\layout_spec_secondary-power.json`, model `D:\Cursor Workspace\AIPE-Full-Ecosystem-Integration\repos\AIPE-PCB-Agent\examples\dab-10kw\design\circuit_secondary-power.json`.

## Board

| Metric | Value |
| --- | --- |
| Outline (mm) | 300.00 x 150.00 |
| Outline area (mm2) | 45000.0 |
| Copper layers | 4 (F.Cu, In1.Cu, In2.Cu, B.Cu) |
| Thickness (mm) | 2.000 |
| Copper thickness (um, stackup text) | F.Cu=70.000; In1.Cu=70.000; In2.Cu=70.000; B.Cu=70.000 |
| Footprints / tracks / vias / zones / rule areas | 312 / 2642 / 440 / 22 / 0 |
| Nets | 132 |
| Zones without fill (areas read from the file) | none |
| Expected (spec) | outline_mm=300, 150; copper_layers=4; copper_um=70; thickness_mm=2.000 |

## Rule table

Dispositions follow the spec thresholds only; every row needs engineering acceptance by a human reviewer.

| Rule | Requirement | Metric | Measured | Threshold | Disposition | Note |
| --- | --- | --- | --- | --- | --- | --- |
| PE-PCB-001 | Minimise MOSFET gate loop | U2 output pad 4 to Q1 gate pad 4 | 52.571 | <= 15 mm | exceeds spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_AH/OUTH_AH/OUTL_AH track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_AH layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=85.440; adjacent=yes; over_kelvin_pour=0.000 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-001 | Minimise MOSFET gate loop | U4 output pad 4 to Q2 gate pad 4 | 52.571 | <= 15 mm | exceeds spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_AL/OUTH_AL/OUTL_AL track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_AL layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=82.320; adjacent=yes; over_kelvin_pour=0.000 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-001 | Minimise MOSFET gate loop | U6 output pad 4 to Q3 gate pad 4 | 50.956 | <= 15 mm | exceeds spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_BL/OUTH_BL/OUTL_BL track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_BL layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=81.990; adjacent=yes; over_kelvin_pour=0.000 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
| PE-PCB-001 | Minimise MOSFET gate loop | U8 output pad 4 to Q4 gate pad 4 | 50.956 | <= 15 mm | exceeds spec threshold - human review required |  |
| PE-PCB-001 | Minimise MOSFET gate loop | G_BH/OUTH_BH/OUTL_BH track length (mm), layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], Kelvin KS_BH layers ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'] | track_mm=88.300; adjacent=yes; over_kelvin_pour=0.000 | n/a | measured - human review required | KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1 |
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
| PE-PCB-004 | Use Kelvin current sensing | AMC1311 differential output track lengths (mm) and mismatch | VSNS_P=94.549; VSNS_N=92.428; mismatch=2.121 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | AMC1311 differential output minimum copper distance to SW_A (mm, any layer) | 88.409 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U1 pads: minimum copper distance to SW_A (mm, any layer) | 112.753 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U11 pads: minimum copper distance to SW_A (mm, any layer) | 83.366 | n/a | measured - human review required |  |
| PE-PCB-005 | Separate sensitive analog and switch-node paths | U12 pads: minimum copper distance to SW_A (mm, any layer) | 90.185 | n/a | measured - human review required |  |
| PE-PCB-006 | Justify high-current copper and via capacity | AC_B copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=201.200; In1.Cu=213.100; vias=1; track_mm=2.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BLD1 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=5.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BLD2 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=5.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BLD3 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=5.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | BUS_P copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=1416.900; B.Cu=1415.400; In1.Cu=7018.900; vias=13; track_mm=45.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | DESAT_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=1; track_mm=12.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | DESAT_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=14.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | DESAT_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=39.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | DESAT_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=18.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVDD_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=27.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVDD_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=27.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVDD_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=21.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVDD_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=25.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVEE_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=4.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVEE_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=4.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVEE_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=12.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | FBVEE_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=6.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | G_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=68.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | G_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=65.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | G_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=70.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | G_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=64.100 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | KS_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=10; track_mm=114.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | KS_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=11; track_mm=130.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | KS_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=5; track_mm=124.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | KS_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=7; track_mm=109.600 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | MDIV1 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | MDIV2 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | MDIV3 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=30.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTCR_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=0.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTCR_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=0.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTCR_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=6.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTCR_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=11.100 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTC_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=36.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTC_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=43.600 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTC_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=24.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | NTC_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=24.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OC_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=45.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OC_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=46.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OC_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=6; track_mm=20.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OC_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=21.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTH_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTH_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTH_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.600 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTH_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.600 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTL_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTL_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=8.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTL_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=9.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | OUTL_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=9.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | PGND copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=1485.500; B.Cu=1459.800; In2.Cu=7981.800; vias=41; track_mm=119.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RDR_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=16.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RDR_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=45.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RDR_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=5.100 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RDR_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=11.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RLIM_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=2.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RLIM_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=2.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RLIM_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=6.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | RLIM_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=6.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | SW_A copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=202.600; B.Cu=919.800; vias=0; track_mm=0.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | SW_B copper (zone area per layer, via count, track length) | zone_area_mm2=F.Cu=1122.900; B.Cu=3477.700; vias=1; track_mm=2.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_16V copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=32.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_5V copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=8; track_mm=35.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_FBVDD copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=3; track_mm=10.600 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_FBVEE copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=26.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_RLIM copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=0.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | S_VEEA copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=49.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VADC_IN copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=18.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDD_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=13; track_mm=73.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDD_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=15; track_mm=90.300 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDD_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=6; track_mm=117.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDD_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=8; track_mm=75.500 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV1 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=2.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV2 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=1.800 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VDIV3 copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=17.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEEA_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=42.000 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEEA_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=0; track_mm=22.100 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEEA_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=23.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEEA_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=2; track_mm=17.400 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEE_AH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=7; track_mm=106.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEE_AL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=9; track_mm=109.700 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEE_BH copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=10; track_mm=95.200 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VEE_BL copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=6; track_mm=112.900 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-006 | Justify high-current copper and via capacity | VMOD_IN copper (zone area per layer, via count, track length) | zone_area_mm2=; vias=4; track_mm=11.600 | n/a | measured - human review required | Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths. |
| PE-PCB-007 | Separate control and switching structures | control section (84 parts) to power stage (207 parts) bounding-box distance (mm) | 9.740 | >= 8.0 mm | within spec threshold - human review required |  |
| PE-PCB-007 | Separate control and switching structures | GND_CTRL zone area (mm2) and island count per layer | In1.Cu=area=19818.200; islands=1 | n/a | measured - human review required | V1 ground-plane extent guard generalised |
| PE-PCB-007 | Separate control and switching structures | board area (mm2), footprints per dm2, courtyard fraction front/back | area=45000.000; per_dm2=69.300; courtyard=front=0.229; back=0.001 | n/a | measured - human review required | HV bbox fraction 0.464; power density n/a W/dm2, n/a W/L |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U2 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 2.547 | <= 15 mm | within spec threshold - human review required | 5->C23.1 2.45; 8->C24.2 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U4 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 2.547 | <= 15 mm | within spec threshold - human review required | 5->C47.1 2.45; 8->C48.2 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U6 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 2.547 | <= 15 mm | within spec threshold - human review required | 5->C71.1 2.45; 8->C72.2 2.55 |
| PE-PCB-008 | Place decoupling adjacent to supply pins | U8 supply pads ['5', '8'] to nearest decoupling capacitor pad, maximum (mm) | 2.547 | <= 15 mm | within spec threshold - human review required | 5->C95.1 2.45; 8->C96.2 2.55 |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_AH versus SW_A: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.250 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_AL versus PGND: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.250 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_BL versus PGND: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.250 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-PCB-003 | Never tie the device Kelvin source to the power source in the layout | KS_BH versus SW_B: distinct nets, no bridging part, no copper contact, minimum copper distance (mm) | distinct=yes; bridging=; contact=no; min_mm=0.250 | distinct nets, no part other than the device on both nets, copper distance > 0 on every layer | within spec threshold - human review required | hard constraint; the device itself is the only permitted connection |
| KR-ISO-001 | No copper crossing an isolation barrier on any layer | barrier strip copper check | n/a | n/a | not measured - spec input missing or reference not found | no barrier_keepouts in the spec |
| KR-ISO-002 | Creepage and clearance per standard for every net-class pair | HV domains to SELV (all layers): minimum copper distance per layer (mm) | F.Cu=8.000; In1.Cu=8.002; In2.Cu=9.650; B.Cu=8.925 | all=8.000 mm | within spec threshold - human review required |  |
| KR-ISO-004 | Slots and cut-outs to extend creepage | slots under barrier parts | n/a | n/a | not measured - spec input missing or reference not found | no barrier_parts in the spec |
| KR-TH-002 | Rated insulating interface for shared heat sinks (HV copper keep-out at the sink) | HS1: minimum HV copper distance to the heatsink courtyard on the outer layers (mm) | F.Cu=0.000 | >= 5.0 mm | exceeds spec threshold - human review required | baseline: >= 5 mm HV copper keep-out around the PE-bonded sink; pad/clip insulation itself is a human-review item |

Rows: 120 - within spec threshold 14, exceeding 5, measured without threshold 99, not measured 2.

## Isolation: minimum copper distance per layer (mm)

| Pair | F.Cu | In1.Cu | In2.Cu | B.Cu | Threshold | Within |
| --- | --- | --- | --- | --- | --- | --- |
| HV domains to SELV (all layers) | 8.001 | 8.002 | 9.650 | 8.925 | F.Cu=8.000; In1.Cu=8.000; In2.Cu=8.000; B.Cu=8.000 | yes |

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

Switch-node copper (mm2): F.Cu=295.800; In1.Cu=93.200; In2.Cu=93.200; B.Cu=1013.000

HV ceramic group bounding box (mm): 73.55, 24.80, 200.25, 30.20

## Gate loops

| MOSFET | Driver | Out->gate (mm) | Return->Kelvin (mm) | Gate track (mm) | Gate vias | Gate layers | Kelvin layers | Adjacent | Over Kelvin pour | KS distinct | KS copper min (mm) | KS copper contact | KS bridging parts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | U2 | 52.571 | 51.875 | 85.44 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.000 | yes | 0.251 | no |  |
| Q2 | U4 | 52.571 | 51.875 | 82.32 | 8 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.000 | yes | 0.251 | no |  |
| Q3 | U6 | 50.956 | 51.004 | 81.99 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.000 | yes | 0.251 | no |  |
| Q4 | U8 | 50.956 | 51.004 | 88.30 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu, In1.Cu, In2.Cu, B.Cu | yes | 0.000 | yes | 0.251 | no |  |

## Heatsink envelope

| Layer | HV items | Min distance (mm) | Items within keep-out | Nearest |
| --- | --- | --- | --- | --- |
| F.Cu | 2110 | 0.000 | 19 | zone BUS_P |

## Decoupling

| IC | Pad | Net | Capacitor pad | Distance (mm) | Same net |
| --- | --- | --- | --- | --- | --- |
| U2 | 5 | VDD_AH | C23.1 | 2.452 | yes |
| U2 | 8 | VEE_AH | C24.2 | 2.547 | yes |
| U4 | 5 | VDD_AL | C47.1 | 2.452 | yes |
| U4 | 8 | VEE_AL | C48.2 | 2.547 | yes |
| U6 | 5 | VDD_BL | C71.1 | 2.452 | yes |
| U6 | 8 | VEE_BL | C72.2 | 2.547 | yes |
| U8 | 5 | VDD_BH | C95.1 | 2.452 | yes |
| U8 | 8 | VEE_BH | C96.2 | 2.547 | yes |

## Sensing

| Pair | Nets | Track (mm) | Vias | Mismatch (mm) | Min to SW (mm) |
| --- | --- | --- | --- | --- | --- |
| AMC1311 differential output | VSNS_P, VSNS_N | VSNS_P=94.55; VSNS_N=92.43 | VSNS_P=2; VSNS_N=1 | 2.121 | 88.409 |

| Part | Found | Min to SW (mm) |
| --- | --- | --- |
| U1 | yes | 112.752 |
| U11 | yes | 83.366 |
| U12 | yes | 90.184 |

## Control section

Control parts: 84, power parts: 207, bounding-box separation 9.740 mm.

| Ground layer | Area (mm2) | Islands | Zones | Required probes covered | Forbidden probes copper-free |
| --- | --- | --- | --- | --- | --- |
| In1.Cu | 19818.2 | 1 | 1 | 0/0 | 0/0 |

## Compactness

| Metric | Value |
| --- | --- |
| Board area (mm2 / dm2) | 45000.0 / 4.500 |
| Footprints per dm2 | 69.3 |
| Courtyard fraction front / back | 0.230 / 0.001 |
| HV bounding-box fraction of board | 0.464 |
| HV copper on outer layers (mm2, fraction of both sides) | 13543.3 (0.150) |
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
| 12V_BIAS_S | CTRL | 18.1 | 9 | 0 | 7 | F.Cu |  |
| 12V_E | CTRL | 251.2 | 39 | 13 | 10 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| 3V3 | CTRL | 446.6 | 156 | 23 | 38 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| AC_B | HV_00 | 2.2 | 2 | 1 | 10 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=201.200; In1.Cu=213.100 |
| BIAS_EN | CTRL | 28.3 | 3 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| BIAS_ENF | CTRL | 7.0 | 7 | 0 | 8 | F.Cu |  |
| BLD1 | HV_09 | 5.4 | 1 | 0 | 2 | B.Cu |  |
| BLD2 | HV_08 | 5.2 | 1 | 0 | 2 | B.Cu |  |
| BLD3 | HV_07 | 5.4 | 1 | 0 | 2 | B.Cu |  |
| BUS_P | HV_02 | 45.5 | 16 | 13 | 30 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=1416.900; B.Cu=1415.400; In1.Cu=7018.900 |
| DESAT_AH | HV_03 | 12.0 | 3 | 1 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_AL | HV_04 | 14.4 | 4 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_BH | HV_05 | 39.8 | 14 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DESAT_BL | HV_06 | 18.9 | 4 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DRV_RST | CTRL | 28.0 | 3 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| DRV_RSTF | CTRL | 118.4 | 31 | 9 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVDD_AH | HV_03 | 27.2 | 14 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVDD_AL | HV_04 | 27.2 | 14 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVDD_BH | HV_05 | 21.8 | 20 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVDD_BL | HV_06 | 25.9 | 14 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVEE_AH | HV_03 | 4.7 | 2 | 0 | 4 | F.Cu |  |
| FBVEE_AL | HV_04 | 4.7 | 2 | 0 | 4 | F.Cu |  |
| FBVEE_BH | HV_05 | 12.4 | 5 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FBVEE_BL | HV_06 | 6.9 | 7 | 0 | 4 | F.Cu |  |
| FLT_AH_N | CTRL | 94.7 | 13 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_AL_N | CTRL | 69.6 | 11 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_BH_N | CTRL | 83.9 | 8 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| FLT_BL_N | CTRL | 65.4 | 7 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_AH | CTRL | 48.8 | 64 | 7 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_AL | CTRL | 56.1 | 66 | 4 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_BH | CTRL | 54.9 | 65 | 4 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_BL | CTRL | 68.1 | 68 | 4 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GNDP_S | CTRL | 55.1 | 65 | 4 | 19 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| GND_CTRL | CTRL | 68.8 | 101 | 44 | 60 | F.Cu, In1.Cu, In2.Cu, B.Cu | In1.Cu=19818.200 |
| G_AH | HV_03 | 68.9 | 18 | 2 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G_AL | HV_04 | 65.7 | 18 | 4 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G_BH | HV_05 | 70.4 | 20 | 3 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| G_BL | HV_06 | 64.1 | 19 | 3 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| ISNS | CTRL | 131.7 | 16 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_AH | HV_03 | 114.8 | 68 | 10 | 21 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_AL | HV_04 | 130.9 | 83 | 11 | 21 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_BH | HV_05 | 124.5 | 74 | 5 | 21 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| KS_BL | HV_06 | 109.6 | 70 | 7 | 21 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| MDIV1 | HV_09 | 1.8 | 1 | 0 | 2 | F.Cu |  |
| MDIV2 | HV_08 | 1.8 | 1 | 0 | 2 | F.Cu |  |
| MDIV3 | HV_07 | 30.5 | 7 | 0 | 2 | F.Cu |  |
| NTCR_AH | HV_03 | 0.0 | 0 | 0 | 2 | F.Cu |  |
| NTCR_AL | HV_04 | 0.0 | 0 | 0 | 2 | F.Cu |  |
| NTCR_BH | HV_05 | 6.0 | 3 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTCR_BL | HV_06 | 11.1 | 8 | 0 | 2 | F.Cu |  |
| NTC_AH | HV_03 | 36.7 | 16 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTC_AL | HV_04 | 43.6 | 14 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTC_BH | HV_05 | 24.8 | 12 | 2 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTC_BL | HV_06 | 24.5 | 17 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| NTC_HS | CTRL | 7.4 | 5 | 0 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_AH | HV_03 | 45.3 | 23 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_AL | HV_04 | 46.7 | 26 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| OC_BH | HV_05 | 20.5 | 14 | 6 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
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
| PGND | HV_01 | 119.4 | 102 | 41 | 58 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=1485.500; B.Cu=1459.800; In2.Cu=7981.800 |
| PG_BIAS_N | CTRL | 45.9 | 16 | 1 | 7 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWMF_AH | CTRL | 57.9 | 20 | 5 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWMF_AL | CTRL | 58.7 | 18 | 4 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWMF_BH | CTRL | 83.6 | 23 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWMF_BL | CTRL | 61.1 | 19 | 2 | 5 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_AH | CTRL | 49.1 | 4 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_AL | CTRL | 44.3 | 2 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_BH | CTRL | 74.6 | 4 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| PWM_BL | CTRL | 47.7 | 3 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDR_AH | HV_03 | 16.0 | 17 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDR_AL | HV_04 | 45.3 | 12 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDR_BH | HV_05 | 5.1 | 3 | 0 | 2 | F.Cu |  |
| RDR_BL | HV_06 | 11.2 | 8 | 0 | 2 | F.Cu |  |
| RDY_AH | CTRL | 97.0 | 15 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_AL | CTRL | 74.1 | 11 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_BH | CTRL | 81.2 | 11 | 3 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RDY_BL | CTRL | 63.5 | 8 | 2 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| RLIM_AH | HV_03 | 2.8 | 1 | 0 | 3 | F.Cu |  |
| RLIM_AL | HV_04 | 2.8 | 1 | 0 | 3 | F.Cu |  |
| RLIM_BH | HV_05 | 6.7 | 5 | 0 | 3 | F.Cu |  |
| RLIM_BL | HV_06 | 6.7 | 5 | 0 | 3 | F.Cu |  |
| SDFM_CLK | CTRL | 84.0 | 4 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SDFM_CLKIN | CTRL | 17.6 | 12 | 0 | 2 | F.Cu |  |
| SDFM_D | CTRL | 83.7 | 6 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SDFM_DOUT | CTRL | 5.4 | 6 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| SW_A | HV_11 | 0.0 | 0 | 0 | 12 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=202.600; B.Cu=919.800 |
| SW_B | HV_12 | 2.2 | 2 | 1 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu | F.Cu=1122.900; B.Cu=3477.700 |
| S_16V | HV_10 | 32.7 | 31 | 2 | 9 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_5V | HV_10 | 35.7 | 30 | 8 | 9 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_FBVDD | HV_10 | 10.6 | 6 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| S_FBVEE | HV_10 | 26.9 | 13 | 0 | 4 | F.Cu |  |
| S_RLIM | HV_10 | 0.0 | 0 | 0 | 2 | F.Cu |  |
| S_VEEA | HV_10 | 49.5 | 41 | 2 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_HS | CTRL | 136.7 | 13 | 0 | 3 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_PWM_AH | CTRL | 103.1 | 15 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_PWM_AL | CTRL | 74.5 | 7 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_PWM_BH | CTRL | 77.0 | 10 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| TEMP_PWM_BL | CTRL | 60.7 | 7 | 0 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VADC_IN | HV_10 | 18.8 | 14 | 0 | 4 | F.Cu |  |
| VDD_AH | HV_03 | 73.9 | 51 | 13 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDD_AL | HV_04 | 90.3 | 55 | 15 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDD_BH | HV_05 | 117.8 | 63 | 6 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDD_BL | HV_06 | 75.5 | 56 | 8 | 16 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VDIV1 | HV_09 | 2.2 | 2 | 0 | 2 | F.Cu |  |
| VDIV2 | HV_08 | 1.8 | 1 | 0 | 2 | F.Cu |  |
| VDIV3 | HV_07 | 17.0 | 4 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEEA_AH | HV_03 | 42.0 | 30 | 4 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEEA_AL | HV_04 | 22.1 | 16 | 0 | 6 | F.Cu |  |
| VEEA_BH | HV_05 | 23.2 | 16 | 4 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEEA_BL | HV_06 | 17.4 | 13 | 2 | 6 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_AH | HV_03 | 106.7 | 71 | 7 | 23 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_AL | HV_04 | 109.7 | 72 | 9 | 23 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_BH | HV_05 | 95.2 | 74 | 10 | 23 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VEE_BL | HV_06 | 112.9 | 79 | 6 | 23 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VMOD_IN | HV_10 | 11.6 | 14 | 4 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VOC_SET | CTRL | 11.1 | 9 | 3 | 4 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VSNS_N | CTRL | 92.4 | 10 | 1 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |
| VSNS_P | CTRL | 94.5 | 11 | 2 | 2 | F.Cu, In1.Cu, In2.Cu, B.Cu |  |

## Notes and limitations

- Straight-line pad distances, track sums and copper areas are geometric proxies; they are not loop inductance, current-path length, creepage per standard or EMI performance.
- Isolation distances are copper-to-copper on each layer (pads, tracks, vias, filled zones); through-air clearance between layers, component bodies, solder mask and coatings are not evaluated.
- Thresholds are those given in the layout spec (taken from the design baseline); no acceptance limit is invented here. Engineering acceptance of every row remains a human responsibility.
- Slot detection relies on non-plated oblong pads or Edge.Cuts graphics inside the barrier part courtyard; the fabricator must confirm the slot width after tolerance.
- Generated by automation.dab_v1.verify from the requirement files; thresholds are the unverified design targets of specification.yaml.
