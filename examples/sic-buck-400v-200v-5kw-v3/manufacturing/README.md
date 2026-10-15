# Manufacturing review package — NOT RELEASED

These files were exported from the delivered editable KiCad 10.0.7 boards. Do not order boards or parts from this review package until the release holds and human engineering review are complete. `power/export-manifest.json` and `control/export-manifest.json` retain the native commands, input hashes, logs and artifact hashes. The two boards are independent four-layer projects.

| Layer, top to bottom | Power thickness | Control thickness |
|---|---:|---:|
| F.Cu | 0.070 mm | 0.035 mm |
| Prepreg | 0.200 mm | 0.200 mm |
| In1.Cu | 0.070 mm | 0.035 mm |
| Core | 1.320 mm | 1.060 mm |
| In2.Cu | 0.070 mm | 0.035 mm |
| Prepreg | 0.200 mm | 0.200 mm |
| B.Cu | 0.070 mm | 0.035 mm |
| Total nominal | 2.000 mm | 1.600 mm |

The native stackup specifies R-1566(S)/R-1551(S), CTI≥600 subject to fabricator certification, ENIG, and assumed εr=4.3 /tanδ=0.02. Copper/lamination tolerances, minimum finished plating and dielectric qualification require a fabricator agreement. The copper mesh assumes 25 µm barrel plating; that assumption is not a certified process result. Power ordinary via 0.8/0.4 mm, control 0.6/0.3 mm; inspect the native drill reports for all PTH/NPTH sizes. Tented vias and mask/paste apertures are represented in the native sources; assembler process review is still required.

Each board folder contains four copper Gerbers, top/bottom mask/paste/silk, outline, Excellon drill and report, native schematic BOM, pick-and-place CSV, STEP and native PDF/PNG review exports. Board/component STEP omits tracks/zones; the Gerbers retain actual copper. Assembly drawings are `../review/assembly_power.pdf` and `assembly_control.pdf`, with front/back F.Fab/B.Fab orientation views. PCB PDF page order is F.Cu, In1.Cu, In2.Cu, B.Cu, F.SilkS. Review PDFs are scaled for framing, not 1:1 manufacturing masters.

Use `../components/bom_power.csv`, `bom_control.csv` and `bom_system.csv` for manufacturer/source/procurement notes. Native BOMs include design references such as net ties and mounting features; reconcile those with the model BOM before procurement. The custom off-board choke appears in the power schematic/model and system BOM and must not be counted twice. System wiring is not a third PCB. PnP rotations are KiCad values; assembler/library rotation and bottom-side conventions need confirmation.

All polarized diode/IC/connector pin assignments are checked by model/schematic/board equality and native parity; this does not validate machine rotation, real mating hardware or soldering. The UCC14141 footprint is the explicitly qualified-pending narrow-land variant described in the component report. Custom TO247/film/module geometry and the control PWP28 body use approximate 3D solids. Power L2/L3/L4 have no matching installed common-mode-choke 3D model; their native footprint/pad geometry remains present. Exact STEP absence is a mechanical hold, not a reason to omit the component from the BOM.
