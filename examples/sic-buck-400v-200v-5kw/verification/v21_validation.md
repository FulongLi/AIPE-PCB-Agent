# V2.1 independent validation (TASK 7)

Generated 2026-10-12T09:29:15Z - AI-GENERATED ENGINEERING PROTOTYPE - V2.1 - HUMAN REVIEW REQUIRED. Scope: CAD evidence only (native KiCad ERC/DRC currency, netlist equivalence, connectivity, zone fills, layout metrics, documents); no electrical, thermal or EMI qualification. Every result below was re-derived with commands run by the validator (scripts and raw outputs in `scratchpad/v21/val/`; project copies for the native re-runs in `%TEMP%/aipe_v21_val/`). Repository files were read-only except this report pair; `verify_sic_buck` rewrote `verification-summary.json` as a side effect of running it.

Boards: power `AIPE_SiC_Buck_Power.kicad_pcb` sha256 `dcd148fb...307a` (V2 `b1bb5698...f7a2`), control `AIPE_SiC_Buck_Control.kicad_pcb` sha256 `4bbf1ee8...ad8b` (V2 `dead06ed...1288`). KiCad 10.0.7.

| # | Check | Command / evidence path | Result | Verdict |
|---|---|---|---|---|
| 1 | Native KiCad ERC - latest manifest per board: 0 findings, --severity-all, source hashes = current .kicad_sch files | verification/erc/20261012T075113Z-erc-df18ce6e/run.json (power); verification/erc/20261012T075120Z-erc-7a14cacb/run.json (control); independent re-run on project copies: scratchpad/v21/val/erc_power/20261012T091719Z-erc-07d2b350, erc_control/20261012T091743Z-erc-780082cf | power: status passed, finding_count 0 over 7 sheets, tool exit 0, command `kicad-cli sch erc --format json --severity-all --exit-code-violations`; source_sha256 9097ea7f... = current AIPE_SiC_Buck_Power.kicad_sch, all 6 sub-sheet dependency hashes = current files (sha256sum). control: passed, 0 findings over 9 sheets, tool exit 0; source 5911a317... = current, all 8 sub-sheets match. ERC ignored-check list identical to the frozen V2 runs (single_global_label, four_way_junction, simulation_model_issue, footprint_filter). Re-run on full project copies in C:/Users/ZHONGN~1/AppData/Local/Temp/aipe_v21_val/: 0 findings both boards; no footprint_link_issues artefact arose because the whole project folder (libraries, lib tables) was copied. | **PASS** |
| 2 | Native KiCad DRC - latest manifest per board: 0 violations / 0 unconnected / 0 parity, --schematic-parity --severity-all in the command, source hash = current .kicad_pcb; re-run on copies | verification/drc/20261012T090308Z-drc-8fd50803/run.json (power, latest); verification/drc/20261012T084327Z-drc-7f07f983/run.json (control, latest); re-run: scratchpad/v21/val/drc_power/20261012T091715Z-drc-b5eaf378/run.json, drc_control/20261012T091733Z-drc-0acea6bf/run.json; rule diffs: releases/v2/kicad/*/ vs kicad/*/ (.kicad_dru, .kicad_pro) | power: passed 0/0/0, tool exit 0, command `pcb drc --format json --severity-all --exit-code-violations --output ... --schematic-parity --refill-zones`, source_sha256 dcd148fb... = current PCB. control: passed 0/0/0, source 4bbf1ee8... = current PCB. Both are the latest manifest for their board (20261012T084719Z-drc-93962d5d is the FAILED power attempt A on a superseded board 2c885298..., 1 violation + 2 unconnected, kept as history; 20261012T081528Z-drc-6094e0f4 is the superseded control run 10). Re-run with run_check on short-path copies: power 0/0/0, control 0/0/0, tool exit 0; copy hashes unchanged by the runs; no lib_footprint_issues warning appeared (full project folders copied). Rules not weakened: power .kicad_dru byte-identical to V2; both .kicad_pro files identical to V2 after flattening (net classes, clearances, severities: 0 differing keys); DRC ignored-check lists identical to the V2 runs. Control .kicad_dru differs from V2 only by additional "OR NetClass == PGND_LV" alternatives inside 6 existing HV conditions (adds a class, removes nothing); PGND_LV is a power-board class (IND_IN_3/IND_OUT_2) and is not defined in the control .kicad_pro, so the control rule semantics are unchanged (see open point 5). | **PASS** |
| 3 | Schematic/netlist equivalence vs V2 - (ref,pad)->net maps and net-name sets of design/netlist_<board>.xml, manufacturing netlist, schematic_gates netlist and a fresh kicad-cli export vs releases/v2/manufacturing/<board>/netlist.xml; netlist_check_<board>.json exact | scratchpad/v21/val/netlist_equiv.py / netlist_equiv.json; scratchpad/v21/val/netlist_fresh_<board>.xml (kicad-cli sch export netlist on the copies); verification/netlist_check_power.json, netlist_check_control.json | power: 651 pads (648 named, 101 named nets, 237 components) - pad map exact, net partition equal, named-net set equal and component set equal to V2 for design, manufacturing, gates and the fresh export; design map == manufacturing map. control: 755 pads (667 named, 111 named nets, 207 components) - all four sources exact vs V2. netlist_check_power.json exact_match True (board sha dcd148fb...), netlist_check_control.json exact_match True (board sha 4bbf1ee8...): model = schematic = board, 648 / 667 pads, 0 problems. | **PASS** |
| 4 | PCB connectivity and copper zones - router unresolved 0, pcbnew GetConnectivity().GetUnconnectedCount 0, stored zone fills rule-aware (no-refill DRC 0/0 on copies), zone fill state | verification/routing_progress_<board>.json; scratchpad/v21/val/kicad_conn.py / kicad_conn.json (KiCad 10.0.7 Python); verification/engineering_checks/stored_zone_fill_check_<board>.json; scratchpad/v21/val/norefill_<board>.json, norefill_parity_<board>.json | routing_progress unresolved [] for both boards. pcbnew (board loaded from disk, BuildConnectivity): power unconnected 0, control unconnected 0. Item counts match the progress JSON: power 2991 straight + 145 arcs = 3136 tracks, 606 vias, 20 copper zones + 16 rule areas; control 4262 + 261 = 4523 tracks, 798 vias, 20 copper zones. Every copper zone IsFilled with a non-empty fill polygon on each of its layers (unfilled 0/0, empty-layer fills 0/0). stored_zone_fill_check_power/control.json: 0 violations / 0 unconnected (board hashes current). My no-refill DRC on the copies (--severity-all, WITHOUT --refill-zones): copper-only 0/0 and with --schematic-parity 0/0/0 for both boards -> the stored fills are the rule-aware fills. DNP attribute present on the board: power 16 footprints, control ['C54'] (parity 0). | **PASS** |
| 5 | High-voltage spacing - KR-ISO rows, HV-to-SELV / HV-to-PE / barrier metrics of layout_metrics_power.json vs releases/v2 (no row may be worse); checker re-run | scratchpad/v21/val/metrics_compare.py / metrics_compare.json; verification/engineering_checks/layout_metrics_power.json vs releases/v2/verification/engineering_checks/layout_metrics_power.json; checker re-run scratchpad/v21/val/metrics/layout_metrics_power.json | Rule table 58 rows in both (27 within / 6 exceeding / 25 measured-only, same as V2); 0 rows with a worse row value; all 17 KR-ISO rows have identical row values and dispositions except KR-ISO-002 "HV/DRV/DESAT/SENSE_ISO to CTRL_SELV" whose B.Cu per-layer distance is 12.025 -> 11.932 mm (threshold 9.0 mm, within; the governing row minimum 9.486 mm on F.Cu is unchanged; In1/In2 11.1 unchanged). HV to PE 5.0005 mm on all four layers (unchanged); ISO_BARRIER strip copper-free on all layers (unchanged); U1..U10 barrier slots g/e/path unchanged; HS-LS island 6.27/6.40/4.80/6.40 mm unchanged; functional VIN-PGND, SW-PGND, VIN-SW, VOUT-PGND distances unchanged to 0.1 um. Pre-existing exceptions identical to V2: KR-ISO-002 VIN<->PGND and VOUT<->PGND F.Cu 1.95 mm (< 3.0 outer), KR-TH-002 HS1 HV copper 4.955 (F.Cu) / 0.0 mm (B.Cu, pad R16.1 PE_REF_MID) (< 5.0) - only the reported tie pad changed C2.2 -> C6.2 at the same 4.955 mm. Re-running check_sic_layout.py on the current boards reproduces the stored files exactly (0 differing rows; isolation, gate_loops, sensing and commutation sections identical; control 31 rows also identical). | **PASS with one per-layer note (regression list #1)** |
| 6 | Critical power and gate loops - PE-PCB-001..005 / KR-PCB rows V2 vs V2.1 and per-net length / vias / min width of G_H, G_L, KS_H, KS_L, SW, VIN, VOUT, PGND, DESAT_*, sense pairs (routing_quality_<board>_compare.json plus an independent pcbnew re-measurement) | scratchpad/v21/val/rq_compare.py / rq_compare.json (compare files; before-board hashes b1bb5698... / dead06ed... = sha256 of releases/v2 boards); scratchpad/v21/val/pernet_measure.py / pernet_measure.json (pcbnew on V2 and V2.1 boards); metrics_compare.json gate_loops / sensing / decoupling | Layout metrics: only PE-PCB-001, PE-PCB-004 and KR-ISO-002 (B.Cu) rows changed; PE-PCB-002 (commutation), PE-PCB-003, PE-PCB-005, PE-PCB-006 and all decoupling max distances (U1 7.60, U3 9.48, U2 9.37, U4 13.91 ... U10 15.51 mm) are identical (placement unchanged). PE-PCB-001: Q1 gate-net track 39.94 -> 39.72 mm, Q2 84.44 -> 82.13 mm; driver-output-to-gate-pad 14.35 / 14.36 mm, return-to-kelvin 14.78 / 14.72 mm, gate vias 3 / 14, kelvin min copper distance 0.3005 mm, gate/kelvin adjacent layers - all unchanged. PE-PCB-004 sense pairs: VIN_OUTP/N 80.91/79.40 -> 78.57/78.64 mm (mismatch 1.51 -> 0.07), VOUT_OUTP/N 64.91/63.15 -> 63.79/61.15 mm (mismatch 1.76 -> 2.64, see regression #2), ISENSE/ISENSE_REF 83.80/90.10 -> 81.04/86.29 mm (mismatch 6.30 -> 5.25); via counts unchanged; control PE-PCB-004 ISENSE/ISENSE_REF 122.2/54.6 -> 114.5/51.6 mm. Independent pcbnew re-measurement of every net: power 66 shorter, 34 equal, 0 longer, 0 with more vias, 0 with a smaller minimum width (100 nets; total 5744.594 -> 5545.648 mm, vias 606 = 606); control 96 shorter, 15 equal, 0 longer, 0 more vias, 0 narrower (111 nets; 7055.22 -> 6700.668 mm, vias 798 = 798) - identical to the compare files. Critical nets (V2 -> V2.1 mm, vias): G_H 26.375 -> 26.302 (0), G_L 33.125 -> 33.052 (7), KS_H 97.70 -> 95.91 (11), KS_L 88.20 -> 86.59 (9), SW 9.623 = (25), VIN 3.125 = (34), VOUT 6.125 = (63), PGND 22.477 = (90), PE 76.912 = (0), DESAT_H_A 37.06 -> 36.18, DESAT_H_OC 29.35 -> 27.40, DESAT_L_A 44.00 -> 42.61, DESAT_L_OC 99.10 -> 94.84, HS_OUTH 4.07 -> 3.92, HS_OUTL/HS_CLMP/HS_GK unchanged, LS_OUTH 19.69 -> 18.64, LS_GK 13.25 -> 11.74, VDD_H/VEE_H/VDD_L/VEE_L 86.3/88.4/80.1/100.1 -> 83.3/85.8/78.8/94.8; min widths unchanged (0.35 gate, 0.6 power, 0.25 signal, 1.0 PE). | **PASS (no per-net regression; one measured-only pair-mismatch note, regression list #2)** |
| 7 | No new unrouted connections - DRC unconnected_items 0 and router unresolved 0 for both boards | DRC manifests of item 2 + re-runs; routing_progress_<board>.json unresolved; pcbnew ratsnest (item 4) | power: DRC unconnected 0 (repo manifest and re-run), router unresolved [] (0), ratsnest 0. control: DRC unconnected 0 (repo and re-run), unresolved [] (0), connectivity_unconnected 0 in the progress JSON, ratsnest 0. | **PASS** |
| 8 | PDFs regenerated - schematic and layout PDFs newer than the V2 ones, page counts | scratchpad/v21/val/docs_images.py / docs_images.json (pymupdf page counts, mtimes, sha256 vs releases/v2/review and releases/v2/manufacturing/*/review) | review/schematic_power.pdf: 7 pages (V2 12), 2026-10-12 15:51:14 (V2 2026-10-11 13:45:42), newer True, bytes differ True; review/schematic_control.pdf: 9 pages (V2 10), 2026-10-12 15:51:21 (V2 2026-10-11 13:45:43), newer True, bytes differ True; review/pcb_layout_power.pdf: 6 pages (V2 6), 2026-10-12 17:04:02 (V2 2026-10-11 13:45:42), newer True, bytes differ True; review/pcb_layout_control.pdf: 6 pages (V2 6), 2026-10-12 16:47:57 (V2 2026-10-11 13:45:43), newer True, bytes differ True. Schematic page sizes: A3 (1191x842 pt) and A2 (1684x1191 pt) sheets (V2: A3 only) - power 7 pages = root + 6 sheets (V2 12 incl. 5 continuation sheets), control 9 = root + 8 (V2 10). Layout PDFs 6 pages each (= V2). The manufacturing/<board>/review copies have the same byte sizes as the review/ files and are also newer than V2. | **PASS** |
| 9 | 2D/3D review images regenerated - 6 renders + crops exist, sizes | docs_images.json; review/pcb_{front,back,3d}_{power,control}.png; review/crops/power (20 files), review/crops/control (16 files); manufacturing/<board>/export-manifest.json | 6 renders present, all 1176x872 px, 68-329 kB, mtimes 2026-10-12 16:47 (control) / 17:04 (power), each newer than and byte-different from its V2 counterpart (6/6 newer, 6/6 differ). Crops: power 20 files (10 v2 + 10 v21; 5 areas x top/bottom), control 16 files (8 + 8; 4 areas x top/bottom); 2400 px long side (2400x1920 ... 2401x495), smallest 57162 bytes, none below 20 kB. Export manifests: power and control status passed, 11/11 commands, 35 artefacts each, input hashes = current board/schematic files (verified by verify_sic_buck). | **PASS** |
| V | PYTHONIOENCODING=utf-8 python -m automation.scripts.verify_sic_buck | verification/verification-summary.json (rewritten by the script; previous copy in scratchpad/v21/val/verification-summary.before.json) | exit 0, status "passed", problems []. Both boards: erc passed (0 findings, hashes_valid, report hash checked), drc passed (0, hashes_valid), exports passed 11 commands / 35 files, netlist_check passed, layout_metrics passed (board hash matches). Side effect: the script rewrote verification-summary.json - the only differences to the previous file are the manifest paths now pointing at the V2.1 runs and report_hash_checked true for the control ERC. step_models_complete is false for both boards - identical to V2 (6 missing-3D-model lines per step.log in V2 and V2.1), pre-existing, not a regression. | **PASS** |

## Regression list and open points

1. **[minor] HV spacing (item 5)** - KR-ISO-002 HV/DRV/DESAT/SENSE_ISO to CTRL_SELV: B.Cu per-layer minimum copper distance 12.025 -> 11.932 mm (between a PGND via and a GNDP_S track; threshold 9.0 mm, still within by 2.93 mm). The row minimum (9.486 mm on F.Cu) and disposition are unchanged; In1.Cu/In2.Cu 11.1 mm unchanged.
2. **[minor] Sense pairs (item 6)** - PE-PCB-004 AMC1311 VOUT differential pair: VOUT_OUTP 64.905 -> 63.785 mm and VOUT_OUTN 63.147 -> 61.148 mm are both shorter, but the pair mismatch grew 1.758 -> 2.637 mm (measured-only row, no threshold). VIN pair mismatch 1.508 -> 0.073 mm and ISENSE pair 6.304 -> 5.249 mm improved.
3. **[info] Routing quality counters** - zigzag_runs counter increased (power 12 -> 26, control 31 -> 41) while stair runs, bends_90, direction changes, short segments and length all fell; the implementers attribute the rise to chamfer pairs of collapsed stairs - not independently verified here.
4. **[info] Labels** - generate_sic_control_board.py still carries BANNER/REVISION "V2": verification/routing_progress_control.json and engineering_checks/stored_zone_fill_check_control.json say "... - V2 - ..." while the power files say V2.1.
5. **[info] Rule file provenance** - kicad/control_board/AIPE_SiC_Buck_Control.kicad_dru references net class PGND_LV (6 conditions) which the control .kicad_pro does not define; the committed HEAD file and releases/v2 do not contain it (generator template shared with the power board since commit ea8e874). Harmless for DRC (never matches), but it will appear as a diff in the PR and should be stated in the known-issues register.
6. **[info] Pre-existing exceptions (unchanged from V2)** - Power: PE-PCB-002 Q2 source pad to nearest PGND HF capacitor 41.165 mm (<= 15); PE-PCB-006 VIN_RAW / VOUT_L 0 stitching vias (>= 24); KR-ISO-002 VIN<->PGND and VOUT<->PGND F.Cu 1.95 mm (outer >= 3.0); KR-TH-002 HS1 HV copper 4.955 / 0.0 mm (>= 5.0). Control: PE-PCB-008 U5 bypass max 5.381 mm (<= 5.0). All identical values and dispositions in V2 and V2.1 - placement/pour items outside the routing scope; they remain documented, not fixed.
7. **[info] Remaining sharp corners** - 90-degree bends remaining: power 1121 (leg_too_short 614, pad_exit 252, unexplained 141, pad_link 71, clearance 43), control 1233 (leg_too_short 723, unexplained 341, pad_exit 63, pad_link 52, clearance 51, pre_routed 3). The "unexplained" buckets (141 / 341) have no exception record from the beautify stage.
8. **[info] Evidence hygiene** - verification/drc/20261012T084719Z-drc-93962d5d (power 8-direction attempt A, FAILED 1 violation / 2 unconnected, board 2c885298...) and 20261012T081528Z-drc-6094e0f4 (control run 10, passed) remain in verification/drc as history; they are not the latest manifest for their board, so verify_sic_buck ignores them. Running verify_sic_buck (as requested) rewrote verification/verification-summary.json.

## Quality totals (checker files, before-board hash verified = frozen V2 boards)

| metric | power V2 | power V2.1 | control V2 | control V2.1 |
|---|---|---|---|---|
| segments | 4755 | 2991 | 5995 | 4262 |
| arcs | 0 | 145 | 0 | 261 |
| vias | 606 | 606 | 798 | 798 |
| length_mm | 5744.589 | 5545.646 | 7055.216 | 6700.663 |
| bends_90 | 3609 | 1121 | 4069 | 1233 |
| bends_45 | 6 | 583 | 0 | 839 |
| direction_changes | 3724 | 1814 | 4081 | 2087 |
| stair_runs | 382 | 124 | 435 | 144 |
| zigzag_runs | 12 | 26 | 31 | 41 |
| short_segments | 2914 | 1225 | 3677 | 1937 |
| arc_joints_discontinuous | 0 | 0 | 0 | 0 |
| degree2_bends_90 | 3739 | 1251 | 4184 | 1339 |
| bends_per_100mm | 64.83 | 32.71 | 57.84 | 31.15 |
| efficiency | 0.7759 | 0.8061 | 0.7802 | 0.8272 |

## Critical nets (V2 -> V2.1; length mm, vias, min width mm, 90-degree bends, arcs)

| board | net | len V2 | len V2.1 | d | vias V2 | vias V2.1 | w V2 | w V2.1 | b90 V2 | b90 V2.1 | arcs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| power | G_H | 26.375 | 26.302 | -0.073 | 0 | 0 | 0.35 | 0.35 | 12 | 9 | 0 |
| power | G_L | 33.125 | 33.052 | -0.073 | 7 | 7 | 0.35 | 0.35 | 15 | 12 | 0 |
| power | KS_H | 97.702 | 95.908 | -1.794 | 11 | 11 | 0.25 | 0.25 | 44 | 19 | 2 |
| power | KS_L | 88.202 | 86.591 | -1.611 | 9 | 9 | 0.25 | 0.25 | 43 | 20 | 0 |
| power | SW | 9.623 | 9.623 | 0 | 25 | 25 | 0.6 | 0.6 | 0 | 0 | 0 |
| power | VIN | 3.125 | 3.125 | 0 | 34 | 34 | 0.6 | 0.6 | 0 | 0 | 0 |
| power | VOUT | 6.125 | 6.125 | 0 | 63 | 63 | 0.6 | 0.6 | 0 | 0 | 0 |
| power | PGND | 22.477 | 22.477 | 0 | 90 | 90 | 0.25 | 0.25 | 0 | 0 | 0 |
| power | DESAT_H_A | 37.062 | 36.184 | -0.878 | 3 | 3 | 0.25 | 0.25 | 23 | 6 | 0 |
| power | DESAT_H_OC | 29.345 | 27.404 | -1.941 | 3 | 3 | 0.25 | 0.25 | 26 | 6 | 2 |
| power | DESAT_L_A | 44.0 | 42.609 | -1.391 | 6 | 6 | 0.25 | 0.25 | 20 | 10 | 0 |
| power | DESAT_L_OC | 99.095 | 94.837 | -4.258 | 5 | 5 | 0.25 | 0.25 | 68 | 8 | 4 |
| power | HS_OUTH | 4.066 | 3.919 | -0.147 | 1 | 1 | 0.25 | 0.25 | 4 | 0 | 0 |
| power | HS_OUTL | 3.953 | 3.953 | 0 | 1 | 1 | 0.25 | 0.25 | 1 | 1 | 0 |
| power | HS_CLMP | 5.545 | 5.545 | 0 | 1 | 1 | 0.25 | 0.25 | 2 | 2 | 0 |
| power | HS_GK | 6.625 | 6.625 | 0 | 2 | 2 | 0.25 | 0.25 | 3 | 3 | 0 |
| power | LS_OUTH | 19.691 | 18.644 | -1.047 | 3 | 3 | 0.25 | 0.25 | 15 | 2 | 1 |
| power | LS_OUTL | 10.203 | 9.669 | -0.534 | 1 | 1 | 0.25 | 0.25 | 3 | 2 | 1 |
| power | LS_CLMP | 21.42 | 20.761 | -0.659 | 3 | 3 | 0.25 | 0.25 | 23 | 14 | 0 |
| power | LS_GK | 13.25 | 11.743 | -1.507 | 2 | 2 | 0.25 | 0.25 | 27 | 7 | 2 |
| power | VIN_OUTP | 80.905 | 78.571 | -2.334 | 2 | 2 | 0.25 | 0.25 | 28 | 8 | 3 |
| power | VIN_OUTN | 79.397 | 78.643 | -0.754 | 0 | 0 | 0.25 | 0.25 | 21 | 13 | 1 |
| power | VOUT_OUTP | 64.905 | 63.785 | -1.12 | 2 | 2 | 0.25 | 0.25 | 13 | 6 | 1 |
| power | VOUT_OUTN | 63.147 | 61.148 | -1.999 | 2 | 2 | 0.25 | 0.25 | 16 | 8 | 1 |
| power | ISENSE | 83.796 | 81.044 | -2.752 | 7 | 7 | 0.25 | 0.25 | 46 | 8 | 2 |
| power | ISENSE_REF | 90.1 | 86.293 | -3.807 | 5 | 5 | 0.25 | 0.25 | 69 | 32 | 0 |
| power | VIN_SENSE | 71.614 | 68.85 | -2.764 | 5 | 5 | 0.25 | 0.25 | 81 | 30 | 3 |
| power | VOUT_SENSE | 71.286 | 69.162 | -2.124 | 8 | 8 | 0.25 | 0.25 | 84 | 46 | 0 |
| power | VIN_AMP_P | 29.047 | 28.608 | -0.439 | 2 | 2 | 0.25 | 0.25 | 23 | 16 | 0 |
| power | VIN_AMP_N | 35.047 | 34.534 | -0.513 | 4 | 4 | 0.25 | 0.25 | 22 | 11 | 0 |
| power | VOUT_AMP_P | 22.247 | 21.295 | -0.952 | 0 | 0 | 0.25 | 0.25 | 20 | 3 | 0 |
| power | VOUT_AMP_N | 25.547 | 25.4 | -0.147 | 3 | 3 | 0.25 | 0.25 | 10 | 5 | 0 |
| power | VDD_H | 86.341 | 83.311 | -3.03 | 9 | 9 | 0.25 | 0.25 | 45 | 18 | 5 |
| power | VEE_H | 88.374 | 85.759 | -2.615 | 9 | 9 | 0.25 | 0.25 | 55 | 14 | 3 |
| power | VDD_L | 80.091 | 78.773 | -1.318 | 6 | 6 | 0.25 | 0.25 | 33 | 23 | 0 |
| power | VEE_L | 100.124 | 94.839 | -5.285 | 16 | 16 | 0.25 | 0.25 | 105 | 47 | 4 |
| power | PWM_H | 132.286 | 124.931 | -7.355 | 4 | 4 | 0.25 | 0.25 | 121 | 6 | 6 |
| power | PWM_L | 111.624 | 106.731 | -4.893 | 7 | 7 | 0.25 | 0.25 | 125 | 60 | 4 |
| power | FLT_H_N | 166.3 | 154.653 | -11.647 | 11 | 11 | 0.25 | 0.25 | 182 | 13 | 7 |
| power | FLT_L_N | 119.996 | 111.135 | -8.861 | 6 | 6 | 0.25 | 0.25 | 120 | 9 | 4 |
| power | RDY_H | 127.993 | 124.655 | -3.338 | 2 | 2 | 0.25 | 0.25 | 71 | 52 | 2 |
| power | RDY_L | 112.289 | 107.412 | -4.877 | 4 | 4 | 0.25 | 0.25 | 89 | 16 | 9 |
| power | PE | 76.912 | 76.912 | 0 | 0 | 0 | 1.0 | 1.0 | 1 | 1 | 0 |
| control | FAULT_N | 319.684 | 303.045 | -16.639 | 16 | 16 | 0.2 | 0.2 | 140 | 23 | 6 |
| control | OC_N | 204.137 | 193.499 | -10.638 | 10 | 10 | 0.2 | 0.2 | 129 | 30 | 15 |
| control | DSP_TRIP_N | 224.402 | 207.078 | -17.324 | 21 | 21 | 0.2 | 0.2 | 166 | 22 | 13 |
| control | VIN_SENSE | 111.528 | 103.835 | -7.693 | 8 | 8 | 0.2 | 0.2 | 74 | 16 | 5 |
| control | VOUT_SENSE | 55.477 | 52.66 | -2.817 | 2 | 2 | 0.2 | 0.2 | 31 | 18 | 2 |
| control | ISENSE | 122.175 | 114.538 | -7.637 | 5 | 5 | 0.2 | 0.2 | 64 | 26 | 6 |
| control | ISENSE_REF | 54.55 | 51.569 | -2.981 | 6 | 6 | 0.2 | 0.2 | 50 | 10 | 3 |
| control | EPWM1A | 51.281 | 48.52 | -2.761 | 4 | 4 | 0.2 | 0.2 | 29 | 6 | 3 |
| control | EPWM1B | 42.931 | 41.415 | -1.516 | 2 | 2 | 0.2 | 0.2 | 37 | 17 | 3 |
| control | PWM_H | 15.3 | 15.3 | 0 | 2 | 2 | 0.2 | 0.2 | 4 | 4 | 0 |
| control | PWM_L | 26.675 | 25.87 | -0.805 | 2 | 2 | 0.2 | 0.2 | 4 | 1 | 0 |
| control | ADCREFP | 8.375 | 8.229 | -0.146 | 2 | 2 | 0.2 | 0.2 | 12 | 7 | 0 |
| control | ADCREFM | 8.725 | 8.579 | -0.146 | 2 | 2 | 0.2 | 0.2 | 12 | 8 | 0 |
| control | ADCRESEXT | 28.1 | 27.661 | -0.439 | 4 | 4 | 0.2 | 0.2 | 16 | 8 | 0 |
| control | ESTOP_N | 402.527 | 384.604 | -17.923 | 24 | 24 | 0.2 | 0.2 | 154 | 44 | 17 |
| control | RESET_N | 57.175 | 54.246 | -2.929 | 2 | 2 | 0.2 | 0.2 | 54 | 35 | 0 |
| control | CLK30 | 14.6 | 13.76 | -0.84 | 2 | 2 | 0.2 | 0.2 | 9 | 3 | 2 |
| control | 3V3 | 121.357 | 121.357 | 0 | 84 | 84 | 0.25 | 0.25 | 35 | 35 | 0 |
| control | 1V9 | 50.003 | 50.003 | 0 | 37 | 37 | 0.25 | 0.25 | 3 | 3 | 0 |
| control | 12V | not in compare (not routed by router / zone-only?) | | | | | | | | | |
| control | 5V | 23.745 | 23.745 | 0 | 15 | 15 | 0.4 | 0.4 | 13 | 13 | 0 |
| control | ADC_VIN | 40.025 | 37.557 | -2.468 | 2 | 2 | 0.2 | 0.2 | 39 | 16 | 3 |
| control | ADC_VOUT | 139.25 | 131.915 | -7.335 | 14 | 14 | 0.2 | 0.2 | 116 | 45 | 6 |
| control | ADC_ISENSE | 36.25 | 34.695 | -1.555 | 6 | 6 | 0.2 | 0.2 | 29 | 12 | 1 |
| control | ADC_V12V | 34.5 | 32.889 | -1.611 | 6 | 6 | 0.2 | 0.2 | 47 | 8 | 0 |

## HV isolation pairs (layout_metrics_power.json, V2 -> V2.1, mm)

| pair | layer | V2 | V2.1 | threshold | verdict |
|---|---|---|---|---|---|
| HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers) | F.Cu | 9.4864 | 9.4864 | 9.0 | same |
| HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers) | In1.Cu | 11.1 | 11.1 | 9.0 | same |
| HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers) | In2.Cu | 11.1 | 11.1 | 9.0 | same |
| HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers) | B.Cu | 12.025 | 11.9323 | 9.0 | WORSE |
| HV/DRV/DESAT/SENSE_ISO to CTRL_SELV (all layers) | min | 9.4864 | 9.4864 | None | same |
| HV to PE | F.Cu | 5.0005 | 5.0005 | 5.0 | same |
| HV to PE | In1.Cu | 5.0005 | 5.0005 | 5.0 | same |
| HV to PE | In2.Cu | 5.0005 | 5.0005 | 5.0 | same |
| HV to PE | B.Cu | 5.0005 | 5.0005 | 5.0 | same |
| HV to PE | min | 5.0005 | 5.0005 | None | same |
| HV functional VIN to PGND (outside the TO-247-4 pin fields) | F.Cu | 1.95 | 1.95 | 3.0 | same |
| HV functional VIN to PGND (outside the TO-247-4 pin fields) | In1.Cu | 1.0005 | 1.0005 | 1.0 | same |
| HV functional VIN to PGND (outside the TO-247-4 pin fields) | In2.Cu | 1.0005 | 1.0005 | 1.0 | same |
| HV functional VIN to PGND (outside the TO-247-4 pin fields) | B.Cu | 3.0004 | 3.0004 | 3.0 | same |
| HV functional VIN to PGND (outside the TO-247-4 pin fields) | min | 1.0005 | 1.0005 | None | same |
| HV functional SW to PGND (outside the TO-247-4 pin fields) | F.Cu | 6.4332 | 6.4332 | 3.0 | same |
| HV functional SW to PGND (outside the TO-247-4 pin fields) | In1.Cu | 1.0005 | 1.0005 | 1.0 | same |
| HV functional SW to PGND (outside the TO-247-4 pin fields) | In2.Cu | 1.45 | 1.45 | 1.0 | same |
| HV functional SW to PGND (outside the TO-247-4 pin fields) | B.Cu | 3.0005 | 3.0005 | 3.0 | same |
| HV functional SW to PGND (outside the TO-247-4 pin fields) | min | 1.0005 | 1.0005 | None | same |
| HV functional VIN to SW (outside the TO-247-4 pin fields) | F.Cu | 3.0004 | 3.0004 | 3.0 | same |
| HV functional VIN to SW (outside the TO-247-4 pin fields) | In1.Cu | 23.582 | 23.582 | 1.0 | same |
| HV functional VIN to SW (outside the TO-247-4 pin fields) | In2.Cu | 1.0003 | 1.0003 | 1.0 | same |
| HV functional VIN to SW (outside the TO-247-4 pin fields) | B.Cu | 23.582 | 23.582 | 3.0 | same |
| HV functional VIN to SW (outside the TO-247-4 pin fields) | min | 1.0003 | 1.0003 | None | same |
| HV functional VOUT to PGND | F.Cu | 1.95 | 1.95 | 3.0 | same |
| HV functional VOUT to PGND | In1.Cu | 1.0005 | 1.0005 | 1.0 | same |
| HV functional VOUT to PGND | In2.Cu | 1.0005 | 1.0005 | 1.0 | same |
| HV functional VOUT to PGND | B.Cu | 3.0004 | 3.0004 | 3.0 | same |
| HV functional VOUT to PGND | min | 1.0005 | 1.0005 | None | same |
| HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS) | F.Cu | 6.2705 | 6.2705 | 3.0 | same |
| HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS) | In1.Cu | 6.3967 | 6.3967 | 1.0 | same |
| HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS) | In2.Cu | 4.8 | 4.8 | 1.0 | same |
| HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS) | B.Cu | 6.3967 | 6.3967 | 3.0 | same |
| HS island to LS island (DRV_HS/DESAT_HS vs DRV_LS/DESAT_LS) | min | 4.8 | 4.8 | None | same |

## Overall

All nine TASK 7 checks verified independently with my own commands; no electrical regression found (no net longer, no net with more vias or a smaller width, no layout rule row worse); two minor measured notes (#1, #2) and six informational open points listed.

