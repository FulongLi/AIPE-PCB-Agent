# Power board (AIPE_SiC_Buck_Power) - Stage 3 DRC iteration log

**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

Only kicad-cli DRC manifests under `verification/drc/` (run through `automation.kicad_tools.run_check`, `--schematic-parity
--severity-all`) count as verification. Everything else below is diagnosis.

## 1. State found at the start of Stage 3 round 2 (2026-10-10 21:49 local)

- No routed power board existed in the repository. The routing generator `automation/kicad_tools/generate_sic_power_board.py`
  (owned by the sibling layout agent) was mid-run (PID 29816, started 21:12, `--no-drc`, output in scratch).
- The last repository DRC evidence was the floorplan snapshot `verification/drc/20261010T131707Z-drc-be0bc838/run.json`:
  16 violations (12 clearance, 4 silk_edge_clearance), 499 unconnected, parity 0.
- 22:03: the sibling run finished after 3062 s (3429 tracks, 621 vias, 33 zones, **109 unresolved router connections**:
  the signal-order trials gave 76 / 50 / 72 / 63 failures, best `span_asc`). The board was copied into
  `kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` (sha256 5038bde5...) and checked:
  `verification/drc/20261010T141722Z-drc-0be35e58/run.json` - **680 violations, 115 unconnected, parity 0**.
- 22:27-23:05 the sibling patched the generator again (fine-pitch escape stubs, PE spine, new island regions, U2 moved to
  x 108, R64/R65 moved) and started a new full run at 23:04 (still running while this log is written). Because that file is
  under concurrent modification, the Stage-3 work below was done on a **fork of the 21:11 generator text** and is delivered
  as a re-applicable patch script, not as an edit of the live file.

## 2. Method: zones-only DRC experiment (3 s build + 1 s DRC)

`zones_only_exp.py` builds the board with the generator's placement, pours, via groups, pre-routed chain tracks and zone
fill but turns the grid router off (fanout / route_net no-ops), writes nothing into the repository, and runs kicad-cli DRC
in a scratch copy of the project (`fp-lib-table` rewritten with absolute library paths). `drc_diag.py` maps every DRC item
uuid back to pad / track / via / zone with net, layer and position. This isolates the placement- and pour-level findings
from the router-induced ones and makes an iteration take seconds instead of 50 minutes.

Baseline (sibling generator text of 21:11, zones only): **162 violations**: 90 HV functional clearance (outer), 15
solder_mask_bridge, 13 HV-to-SELV, 10 HV-to-PE, 9 hole_clearance, 6 via_dangling, 5 shorting_items, 4 HV functional
(inner), 4 silk_edge_clearance, 2 zones_intersect, 1 tracks_crossing, 1 pin-field U10, 1 isolated_copper, 1 hole_to_hole.

Root causes found and fixed (all in the patch `stage3_power_patch/patch_s3_v2.py`):

| finding | cause | fix |
|---|---|---|
| zones_intersect x2 | PGND B.Cu polygons shared edges | one U-shaped PGND B.Cu polygon |
| HV inner clearance / VIN-VOUT overlap on In2 | VIN In2 backbone (to x 201.5) overlapped the VOUT In2 bar at equal priority (the filler clips only lower-priority zones) | VIN In2 backbone to x 152, east arm round the VOUT bar (y 61.5-134.5) to the sense ladder feed |
| HV outer clearance VIN vs VIN_RAW (1.0 / 1.5 mm) | equal-priority pours 1 mm apart; RT1 rotated with its VIN_RAW pad in the VIN pour | 3.0 mm gaps, VIN_RAW priority 3, RT1 rotated 270 |
| REDCUBE pin fields 1.43 mm (J2/J6, J3/J4) | terminals 13.5 mm apart | J5/J6 at x 23, J4 at y 65.5 |
| 60+ chain findings (tracks_crossing, shorting_items, mask bridges, 1.3-2.8 mm pad gaps, flanking tracks 2.3 mm apart) | bleeder / indicator / damping chains at 10 mm pitch with straight midpoint tracks across other pads; in-pad vias in 1206 pads 2.6 mm from the stub leaving the other pad | chains re-laid on the courtyard pitch (2512 7.8, 1206 4.7 mm) with same-net pads 0.6 mm apart joined by stubs that stay inside both courtyards (the `.kicad_dru` pin-field exceptions apply there), orientation so same-net pads face each other, DAMP_MID bypass along the board edge, indicator chains reversed so each LED's PGND pad abuts the bleeder's PGND pad (via in the 2512), R9 fed by a via 3 mm away + stub, no in-pad vias in R4/R9/R59/R64 |
| HF tier rows 2.1 mm apart; VIN via group 1.8 mm from C6 PGND; HS-island parts under the HF-tier via rings (mask bridges, hole clearance, 1.4-2.7 mm) | second HF row 5 mm below the first; islands drawn under the HF tier | row A (C1-C6) rotated (PGND pads to the sink side) and moved to y 126.5; islands moved east of / below the via rings; in-pad VIN vias dropped for C1-C10/C16/C17 (pads sit in the F.Cu pour); HV via rings and HV pads reserved for the auto-placer |
| HV ladders 0.9-2.7 mm from the U5 pad row and sense-island vias | ladders at y 132.3/137.3 over U5 | one ladder row at y 132 over U6/U7 (R59-R62 x 174-188, R65/R64 x 194.5/199.2), VIN feed via (169,132) + stub, R64 stub into the VOUT F.Cu strip; sense islands below y 129.5 / in the 135.8-137.4 band |
| PE stud 4.27 mm from VIN vias; PE link 3.65 mm | via group beside H1; R14-R16 at 7 mm pitch | top-band via group moved east of the damping legs, H1 at (31.5, 7); R14/R16/R15 at 9.5 mm pitch on B.Cu over the PGND pour |
| via_dangling (VOUT_L, U10 bar, D5, snubber) | VOUT_L has no inner copper; TMCS bar via over the barrier strip; D5 SW via over the KS pour | no VOUT_L vias; one bar via at the HV end; D5 fed by a B.Cu track from Q2 pin 1; snubber on F.Cu east of U1 with an SW-block tab |
| isolated_copper (PGND B.Cu right strip) | no stitching | 2 x 11 via array |
| 21 unconnected PGND (0603 pads) | pads without an in-pad via were also skipped by the router | skip only pads that received a via |
| D3 / D5 / TP1 / TP2 | D3 under C3's via ring; TP1/TP2 in the driver pad escape lanes | D3 on F.Cu over the VIN band (DESAT pad away from the drain pin), D5 beside Q2 pin 1, TP1 (89.5,134.5), TP2 (126,134.5) |

Result of the zones-only experiment with the patch: **18 findings = structural floor**

- 12 x clearance 'HV side to CTRL_SELV' 7.25-8.64 mm: the unconnected APWM pins of U1/U3 (pad 16) and the NC pin of U10
  (pad 5). Their nets `unconnected-(...)` fall in the Default net class, which the 9.0 mm rule includes, and the pin-field
  exceptions in `.kicad_dru` cover only CTRL_SELV. Not fixable by geometry (same footprint); needs a `.kicad_dru` / project
  change by the project owner.
- 2 x clearance HV functional outer 1.95 mm at the indicator LEDs D1/D2 (0805, 1.875 mm pad pitch): the two items that
  connect an LED's pads are inevitably < 3 mm apart, and the pin-field exceptions apply only to pairs that include a pad of
  that footprint. The geometry keeps exactly one finding per LED (two stubs). Needs a footprint or rule change.
- 4 x silk_edge_clearance warnings: the standard SOIC-16W silkscreen of U1/U3 crosses the board-level 1.2 mm Edge.Cuts
  isolation slot that the baseline prescribes for footprints without their own slot. Library-level.

Remaining unconnected items in the zones-only board are the router's job (fanout of 0603 PGND pads, SELV nets, driver
islands); none of the pour / chain nets (VIN, VIN_RAW, SW, VOUT, VOUT_L, DAMP_MID, SNUB_MID, PE_REF_MID, BLD_*, IND_*,
VIN_DIV_T*, VOUT_DIV_T1) is left unconnected.

## 3. Full router run of the patched fork

Started 23:26 local in scratch (`pzf/`, MAX_NODES 600k, one order trial, 12 rip-up rounds); finished 23:39 after 760 s
(router 754 s): 3781 tracks, 645 vias, 30 zones, **167 router-unresolved** (126 route failures + fanout failures, mostly
3V3 x29, GNDP_S x15, GNDP_L x13, GNDP_H x9, 12V_BIAS_* x18; the 12 rip-up rounds found no rippable path). Diagnostic
kicad-cli DRC (scratch project copy, not repository evidence): **624 violations / 154 unconnected / parity 0**:

| type | count | what it is |
|---|---|---|
| clearance HV functional (outer) | 262 | router tracks of one HV group 0.3-2 mm from pads/tracks of another group (e.g. VEE_L next to D5's SW pad, 5V_ISO next to the VIN feed stub): the grid router knows one clearance per net, not the class-pair rules |
| via_dangling | 133 | router vias ending on one layer only |
| clearance HV side to CTRL_SELV | 100 | HV-side and SELV-side escape stubs of the barrier packages within 9 mm of each other, SELV tracks reaching y 149-151 |
| items_not_allowed | 60 + 15 | router tracks at y 140.0 / 150.0 inside the ISO_BARRIER rule area (the plan keep-out leaves 140-140.5 and 149-150 open) and in other rule areas |
| clearance HV side to PE | 39 | PE routed by the router through the Y-capacitor column |
| clearance CTRL_SELV / DRV_LS / inner | 8 / 1 / 2 | router |
| silk_edge_clearance | 4 | structural (U1/U3 silkscreen over the board-level slot) |

So with the pours and placement at the structural floor, the remaining findings are produced by the signal router itself:
class-pair clearances between HV groups, the barrier-strip escapes and the PE net. These are exactly the items the
sibling's 22:27-23:05 patches address on its side (barrier-strip keep-outs `HV_COPPER_MAX_Y` / `SELV_COPPER_MIN_Y`,
fine-pitch exact stubs, PE spine pre-route, PE in `skip_nets`); the two change sets are complementary and need to be
merged into one generator. Layout metrics of the routed fork (checker dry run): driver-to-gate 14.36 mm (both), Q1 drain
to HF capacitor 8.56 mm, Q2 source to HF capacitor 41.1 mm (exceeds 15 mm - the second HF row sits beside Q1, a design
item inherited from the floorplan), U3 decoupling 16.3 mm (> 15), HS/LS island copper distance 1.15 mm on F.Cu after
routing (< 3 mm: router), KR-ISO-004 slot paths 9.44 mm (U1/U3), 10.08 (U2/U4/U5), 10.89 (U6/U7), 9.81 (U10).
Review renders: `scratchpad/pzf` (routed), `scratchpad/pz3/render/*.svg` (zones only).

## 4. Status / next steps

- The repository board `kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` and `routing_progress_power.json` are owned by
  the sibling run started 23:04; its manifest will land under `verification/drc/`.
- To apply this work: `python examples/sic-buck-400v-200v-5kw/verification/stage3_power_patch/patch_s3_v2.py <copy of the
  21:11 generator>` (asserted unique replacements; the hunks touch FIXED poses, REGIONS / ASSIGN_BY_REF, zone_plan,
  via_groups, hv_pad_vias, hv_chain_tracks, routing_plan (per-zone priorities), place_fixed reservations, build_power).
  Rebase onto the sibling's current text before use: the sibling's patch_p2 changed REGIONS, R14-R16, U2, R64/R65,
  routing_plan's signature and added fine-pitch escapes - those hunks will not match verbatim.

## 5. Cross-check: the sibling's current generator text (23:05) in the same zones-only experiment

Running the owner's 23:05 `generate_sic_power_board.py` through the identical zones-only experiment (router off) gives
**120 violations / 358 unconnected / parity 0**: 36 HV functional outer, 16 solder_mask_bridge, 15 HV-to-SELV (12 of them
the structural APWM/NC ones), 11 HV-to-PE, 10 shorting_items, 8 via_dangling, 5 items_not_allowed (vias in the heatsink
keep-out), 4 same-reference-island, 4 silk_edge, 3 hole_clearance, 2 zones_intersect, 1 DRV_LS, 1 DRV_HS, 1 tracks_crossing,
1 pin-field U10, 1 isolated_copper, 1 hole_to_hole. Its chains (C16/R12/C17/R13 at 54/62.5/72/80.5, R1-R6/D1, R7-R10/D2),
the VIN In2 / VOUT In2 overlap, the VIN / VIN_RAW gaps, the REDCUBE pin fields and the PGND B.Cu zone intersections are
unchanged from the 21:11 text, so the full run started at 23:04 cannot reach zero regardless of how the router does;
these ~100 non-structural findings are fixed by the pour / chain / terminal hunks of `patch_s3_v2.py`, which apply verbatim
to the 23:05 text (the dry run shows only six hunks that need rebasing: the C16/R1/C18 FIXED lines, the D3/D5/R11/C15 and
TP lines, the R59-R65 line, the REGIONS block, the hs_island/ls_island assignment lines and the plan's `prune_vias` line).

## 6. Files

- `verification/stage3_power_patch/patch_s3_v2.py` - the re-applicable Stage-3 patch (base: generator text of 21:11).
- `verification/stage3_power_patch/generate_sic_power_board_stage3_fork.py` - the patched generator as run (fork; reads
  `AIPE_ROOT` so a copy can run outside `automation/`).
- `verification/stage3_power_patch/hunks_vs_generator_2305.txt` - which hunks apply verbatim to the sibling's 23:05 text.
- `verification/stage3_power_patch/zones_only_drc_comparison.json` - per-type zones-only DRC counts: 21:11 text 162,
  23:05 text 120, Stage-3 fork 18 (12 + 2 + 4 structural).
- `verification/stage3_power_patch/{zones_only_exp.py, drc_diag.py, zone_islands.py, dump_board.py}` - the diagnostic tools
  (KiCad Python; the experiment writes only to a scratch directory).
- Review renders (scratch, kicad-cli svg, F.Cu / B.Cu / In2.Cu with Edge.Cuts and F.Fab): `scratchpad/pz3/render/` (fork,
  zones only), `scratchpad/pzf/render/` (fork, routed), `scratchpad/pzo/render/` (sibling 23:05 text, zones only).

## 7. Third fork iteration: router guards (started 23:44 local)

The routed-fork diagnosis (section 3) shows the remaining findings come from the signal router. Added to the patch and
verified with the zones-only experiment (still 18 = structural floor):

- every HV pour on a routing layer (VIN column/band, VIN_RAW, SW block + tab, VOUT F.Cu/B.Cu, VOUT_L) becomes a net-coded
  router keep-out (tracks and vias of other nets excluded) so foreign tracks can neither fragment the pours (the 4 lost VIN
  pads of section 3) nor approach HV copper inside the 3 mm class rule; the PGND B.Cu pours stay open for the PE route;
- notch-aware barrier-strip edge keep-outs (HV copper <= 139.6 mm, SELV copper >= 150.4 mm outside the pad-row notches),
  which removes the tracks at y 140.0 / 150.0 and the HV-side vs SELV-side escape stubs within 9 mm;
- 3 mm keep-outs around the ladder feed vias; PE router clearance 5.3 mm (5.0 mm rule plus grid rounding of the 2 mm track);
- two signal-order trials (the first fork run used one by mistake).

Expected trade: B.Cu island parts placed under the VIN F.Cu band (the strip x 64.5-83) cannot escape any more (their vias
would land in the pour), so they will show as unconnected instead of fragmenting VIN. Result: section 8 when available.

## 8. Status checkpoint (23:46 local)

- Repository power board: `kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` is the sibling's placement snapshot of 23:04
  (sha256 18c44b93...) while its full run (`generate_sic_power_board --trials 1 --ripup 60`, PIDs 38724/14232, started
  23:04) is still routing; that run will overwrite the board, `routing_progress_power.json` and add a DRC manifest.
- Last repository DRC evidence for a routed power board: `verification/drc/20261010T141722Z-drc-0be35e58` - 680 violations,
  115 unconnected, parity 0 (sibling board sha256 5038bde5...).
- Control board: `verification/drc/20261010T144718Z-drc-6798d486` - 0 violations, 1 unconnected (BIAS_EN), parity 0 on the
  repository board sha256 68c3558f... (`routing_progress_control.json` still cites the older manifest a497f454 with the same
  counts). Manufacturing exports and review images under `manufacturing/control_board/` and `review/` date from 18:50 and
  are older than this board.
- Stage-3 fork: pours and placement at the structural floor (18 findings, section 2); first routed fork 624 / 154 (section
  3); third iteration with router guards running (section 7).
- Not done: the power board has no routed, DRC-clean version in the repository; the two change sets (this patch and the
  sibling's router-side work) still have to be merged into one generator and run end to end.

## 9. Metrics-checker notes (check_sic_layout, power spec)

- KR-ISO-004 for U1/U3: the checker treats each Edge.Cuts line of the board-level slot rectangle as a candidate (width
  0.05 mm) and so reports the width criterion as failed; the slot itself is 1.2 x 15.5 mm with e = 3.025 mm beyond the pad
  rows (path 9.44 mm >= 9.0). Checker limitation (edge lines are not assembled into the cut-out), not a board defect.
- KR-ISO-004 for U6/U7 (AMC1311 DWV): the footprint NPTH slot gives e = 2.995 mm (5 um short of the 3.0 mm baseline),
  path 10.89 mm; library item (not editable here).
- The isolation pair rows (VIN/PGND 0.3 mm etc.) measure zone *outlines*, not the filled copper, so they report the
  pre-clip outline gaps; kicad-cli DRC on the filled board is the arbiter (zones-only run: no HV functional findings).
- PE-PCB-006 ">= 24 vias per net" is applied to every HV-class net including the bleeder / divider midpoints; only the
  25 A nets (VIN, PGND, SW, VOUT) are meaningful there (all within threshold).

## 10. Sibling run finished (23:50 local) - current repository evidence

`generate_sic_power_board --trials 1 --ripup 60` (generator text of 23:04/23:05) finished after 2736 s (router 2713 s):
3305 tracks, 563 vias, 33 zones, **161 router-unresolved**. Repository board `kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb`
sha256 246385bd..., `routing_progress_power.json` consistent (board sha, manifest), **DRC manifest
`verification/drc/20261010T154954Z-drc-48a5e8dc/run.json`: 373 violations, 161 unconnected, parity 0, exit 5** (this is the
repository verification evidence; previous: 680 / 115). By type: via_dangling 140, HV functional outer 98, HV-to-SELV 44
(12 structural APWM/NC), track_dangling 27, solder_mask_bridge 16, HV-to-PE 12, shorting_items 8, items_not_allowed 5,
same-reference-island 4, silk_edge 4, hole_clearance 3, DRV_LS 2, HV inner 2, DRV_HS 2, zones_intersect 2, tracks_crossing 1,
CTRL_SELV 1, isolated_copper 1, hole_to_hole 1 (`stage3_power_patch/repo_board_drc_48a5e8dc_by_type.txt`).

Reading: the sibling's router-side guards cut the router-induced classes (HV outer 98 vs 262 in the unguarded fork run,
HV-to-SELV 44 vs 100), while the pour / chain / terminal findings that `patch_s3_v2.py` removes are all still present
(zones_intersect 2, shorting_items 8, solder_mask_bridge 16, hole_clearance 3, tracks_crossing 1, isolated_copper 1,
hole_to_hole 1, same-island 4, most of the HV-to-PE 12 and part of the HV outer). Neither board is close to zero yet; the
merge of the two change sets is the next step, followed by the router-capacity work on the islands (161 / 167 unresolved).

## 11. Third fork iteration result (router guards) - 23:52 local

463 s (router 458 s, two order trials: plan 92 -> span_asc 74 route failures + 82 fanout failures = 156 unresolved), 3536
tracks, 596 vias. Diagnostic DRC (scratch): **241 violations / 146 unconnected / parity 0** (first fork run 624 / 154; the
sibling's repository run 373 / 161). By type: HV functional outer 97 (262 before), via_dangling 72 (133), HV-to-SELV 37
(100; 12 structural), items_not_allowed 20 (75), CTRL_SELV 7, silk_edge 4, pin-field R65 2, DRV_LS 1, track_dangling 1.
The HV pours stay intact (no VIN / PGND / SW / VOUT unconnected items any more); the unconnected list is now the router's
capacity problem: VEE_H 22 / VEE_L 20 / VDD_H 8 / VDD_L 6 (the 12-pin VEE / VDD rows of the UCC14141 modules whose pads the
fanout cannot escape one by one - the sibling's fine-pitch bar + exact-stub escape is the fix for that), 3V3 12, PWM_*_F 8,
PE 4 (blocked by the VIN column keep-out on F.Cu and routed on B.Cu through the PGND pour: needs the pre-routed PE spine).
Evidence: `stage3_power_patch/fork_full_run3_router_guards/` (run.json, drc.json, router_result.json, drc_diag_by_type.txt;
board sha256 adc1ac08...).

Merge plan (one generator, one end-to-end run): sibling's text as base + this patch's zone_plan / via_groups / hv_pad_vias
/ hv_chain_tracks / feed_stubs / d5_sw_track / routing_plan per-zone priorities / place_fixed reservations / chain and
terminal poses (25 hunks apply verbatim, 7 need a manual merge: top-band and PE-link poses, D3/D5/R11/C15/TP poses, ladder
poses, REGIONS, island assignments, the keep-out block and the plan's trials/ripup line) + this patch's HV-pour and
barrier-edge keep-outs + the sibling's fine-pitch escapes and PE spine. Then re-run `generate_sic_power_board` (DRC +
metrics) into the repository and iterate on the islands (capacity between the HF tier at x <= 88 and Q2 at x 112 remains
the binding constraint).

## 12. Stage 4 - one generator, three routing layers, regions (2026-10-11, this agent)

The two change sets were merged into one `automation/kicad_tools/generate_sic_power_board.py` and adapted to the regenerated
project (ERC manifest `verification/erc/20261010T165532Z-erc-02a2619f`): the UCC21710 footprint `UCC21710_DW0016A_Slot` now
carries its own 1.2 x 16.6 mm NPTH slot (the board-level Edge.Cuts slots and silkscreen hacks are gone), its 17.8 mm courtyard
no longer fits the sibling's barrier spacing (U2 at 111.5 overlapped U1), so the barrier line is the fork's order re-spaced for
the slot footprints: U2 77.5, U1 96.25, U3 124.0, U4 142.75, U5 163.0, U6 181.0, U7 195.0, U10 212.0 (courtyards >= 0.35 mm
apart). Netlist re-exported from the schematic at every build; the `.kicad_dru` pin-field exceptions for the no-connect pads
and the PGND_LV class make the former 14 "structural" findings disappear.

Base geometry: the stage-3 fork (pours, via groups, chain stubs with courtyard-contained ends, DAMP_MID bypass, LED feeds,
re-pitched REDCUBE terminals, VIN In2 backbone clear of the VOUT In2 bar, HV via rings / HV pads reserved for the auto-placer,
VOUT_L without vias, PGND right strip stitched) plus the sibling's router-side work (notch-aware barrier-edge keep-outs
HV_COPPER_MAX_Y 139.1 / SELV_COPPER_MIN_Y 150.9, exact stubs for the 0.65 mm rows, PE pre-route, trials / rip-up).

Changes of this stage (all in the generator unless noted):

| item | change |
|---|---|
| grid_router (backwards-compatible, tests pass) | `Grid.zocc` zone keep-outs (`keepout(..., zone=True)`: tracks stay out, via barrels pass - used for the In2 pours); per-net routing regions `net_rules[net]['region'] = {layer: [rects], 'vias': [rects]}` enforced in A*, soft A*, via placement and fanout; `fanout.escape_layer`; `fanout.direct_nets` (SMD pads become ports at the pad's outer end, no escape via per pad); exact stubs with an explicit direction and lateral offset |
| routing layers | F.Cu, In2.Cu, B.Cu; In2 is a zone keep-out everywhere except the two island windows (x 64.6-114.4 and 119.6-153.0, y 127.6-139.1) where the Kelvin pours live; KS_H / KS_L and the gate pours G_H / G_L are routed as signals and poured after the signal stage (`post_route` zones), so a track cutting through them costs nothing |
| routing regions | HS island nets (DRV_HS + DESAT_HS), the PGND-referenced island nets (DRV_LS + DESAT_LS + SENSE_ISO, one shared region) and every SELV net are confined to rect sets per layer whose edges are inset 0.6 mm from every 3 mm boundary to a foreign HV group (Q1 drain, Q2 PGND / KS pins, D3 / D5 drain pads, VIN band, SW block, ladders, feed vias, VOUT strip); vias only where F.Cu and B.Cu rects overlap; the island wall is x 114.4-118.6 |
| fine-pitch rows | same-net runs get a pad-wide bar and ONE 0.6/0.3 via beyond the row (in line with the middle pad of a run >= 3, between the two pads of a pair: 0.975 mm from the neighbours' centrelines); every other pad gets an exact stub (HV side 0.6 / 1.5 mm alternating, SELV side 1.0 / 1.9 mm); plane-net pads at a row end keep the shifted via escape; the SELV parts start 6.5 mm below the SELV pad rows (fan-out corridor) |
| SELV strip | In2 under the strip is now the 3V3 pour (31 pins reached by the escape vias), GND_CTRL stays on In1; 12V_PROT (11 pins) is routed; the three bias-module primaries sit beside their modules (L4 / C60-C63 east of J7's end) |
| placement | row A of the HF tier at y 125.9 with the PGND vias 0.15 mm outside the heatsink rule area and the VIN+ band cut at y 129.6 (3 mm from the islands' west strip, which can now carry vias from y 133.1), a VIN tab for D3's drain pad; TP1 / TP2 beside the gate pins; SW via group 5 x 5 at 1.7 x 1.1 mm between TP1 and Q2 pin 1; snubber R11 / C15 on F.Cu east of Q2's pins over the SW In2 neck (SW / PGND in-pad vias); D5 mirrored with its SW pad toward Q2 pin 1; PE group west of the heatsink (stud between the Y capacitors, link resistors with their PGND pads inside the PGND B.Cu column, spine x 58 on B.Cu); island regions with 0.8 mm channels between part rows and the island-aware placer gaps (3 mm from VIN / VOUT items, 3 mm from SW items only east of the wall, 3 mm from PGND items only west of it); the inductor's circular courtyard |
| tests | `tests/test_generate_sic_power_board.py` (13 host-python tests: floorplan coverage, barrier spacing, pours, via groups, rule areas, barrier polygon, regions and the wall, escape plan, plan validation, PE pre-route, chain stubs) |

Zones-only experiment of this geometry (`scratchpad/converge/power/pexp.py --zones-only`, router off): **23 violations, all
via_dangling (the bar vias waiting for their routes), 346 unconnected (the routed nets), parity 0** - the structural floor is
zero.

## 13. Stage 4 routing experiments (scratch, `pexp.py`; diagnostic DRC in a scratch project copy, not repository evidence)

Every row is one full build (placement, pours, fanout, signal router, zone fill) plus kicad-cli DRC with `--schematic-parity
--severity-all` in the scratch copy; "unres." is the router's own unresolved count, the DRC columns are violations /
unconnected / parity. One trial, no rip-up unless stated.

| run | change | router s | unres. | DRC | violation classes |
|---|---|---|---|---|---|
| r1 | merged generator, 3 routing layers, regions, direct ports | 141 | 125 | 69 / 117 / 0 | 26 CTRL_SELV 0.21 mm (12V_PROT 1.0 mm track vs 0.25 mm tracks: router clearance model at zero margin), 19 via_dangling, 14 track_dangling (unrouted bar vias / stubs), 5 HV-to-SELV 8.975 (DESAT track from pad centre vs 3V3 escape from pad centre), 2 items_not_allowed (track 0.05 mm inside the ISO_BARRIER notch), 2 HV outer 2.91 (ladder taps vs chain stubs), 1 shorting (sense part on a tap stub end) |
| r2 | tap-stub direction + lateral offset, PORT reservations, D5 mirrored (SW pad to Q2), SW via group 5 x 5, snubber over the SW In2 neck, PE group redesigned, ladder row y 132, sense filters upright under it | 188 | 121 | 34 / 116 / 0 | 16 via_dangling, 13 track_dangling, 4 DRV_LS 0.287 (two 1.0 mm tracks' end caps), 1 same-island 0.281 (via vs 0.5 mm track) |
| r3 | as r2 with 2 order trials + 12 rip-up rounds | 595 | 118 | 35 / 112 / 0 | the rip-up found nothing to rip (sealed ports, see below); span_asc order worse than the plan order (124 vs 117) |
| r4 | island rails 0.5 mm, +1 grid cell clearance margin for every net, sense F band continuous to the barrier | 167 | 125 | 39 / 119 / 0 | dangling only; the margin sealed 6 plane-pad escapes and every exact-stub port |
| r5 | margin only for nets wider than 0.35 mm, goal cell always enterable, through-hole ports keep a free layer choice, stubs marked at true width, 0.3 mm nets at 0.25, bias primaries 0.25 | 152 | 106 | 22 / 106 / 0 | dangling only |
| r6 | routed copper 0.25 mm (not 0.6) inside the rule-area notches: the outermost pads' centre cells were in the strip keep-out, which sealed every KS_H / KS_L port (U1.1 / U3.1) | 128 | 80 | 25 / 80 / 0 | dangling + 1 HV outer 2.8 (LS via vs D5 drain pad) |
| r7 | island channels 0.9 mm, island rails 0.4 mm, D6 to the B.Cu gate region, node budget 1.2 M, LS west rects from y 137.0 | 241 | 80 | 24 / 80 / 0 | dangling + 1 HV outer (LS_CLMP via vs SW) |

| r8 | mezzanine escape stubs (0.6 mm) on B.Cu, Kelvin nets after the rails | 175 | 100 | 40 / 99 / 0 | dangling only; the J7 stub ports were sealed again by other nets' tracks hugging the stub ends |
| r9 | island rails 0.35 mm (no clearance margin needed), south stubs 1.2 mm, strip parts 3 mm below the socket | 166 | 90 | 38 / 90 / 0 | dangling only |
| r9b | as r9 with 3 order trials + 12 rip-up rounds | 459 | 68 | 32 / 67 / 0 | plan 90 / span_asc 77 / span_desc 68; every rip-up round reverted (worse) |
| r10 | socket stubs toward the side of the socket where the net lives (jog through the other pin row), reference / OC group east of the socket, U5 primaries west of its end, RC networks in the HS strip region | 574 (3 trials) | 74 | 33 / 73 / 0 | dangling only; plan 83 / span_asc 74 / span_desc 83 |

**Repository checkpoint (first routed board of this stage)**: `generate_sic_power_board --trials 3 --ripup 0` with the r10 geometry ->
`kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` (237 footprints, 2328 tracks, 424 vias, 32 zones, 74 router-unresolved),
`design/placement_power.json`, `design/routing_plan_power.json`, `verification/routing_progress_power.json`, layout metrics
`engineering_checks/layout_metrics_power.{json,md}` (58 rows: 24 within, 9 exceeding, 25 measured-only), **DRC manifest
`verification/drc/20261010T191929Z-drc-4e5fe800/run.json`: 33 violations (23 track_dangling, 10 via_dangling - all at the unrouted
connections), 73 unconnected, parity 0, exit 5.** Previous repository evidence: 284 / 183 / 0 (`20261010T164654Z-drc-ccea4530`).

Diagnosis tool (`dbg_route.py`): routes only the named nets on a fresh build and flood-fills the reachable cells of every failed
connection under the router's own rules. Findings: (1) a connection whose A* ends with an exhausted heap (not the node budget)
has a *sealed* port - the dilated clearance halo of a neighbouring pad / stub / via covers every cell next to the port; the
0.65 mm stub rows (0.25 mm stubs 0.65 mm apart) seal any port whose net is dilated at all, so the stub-row nets must route at
the default width and the goal cell itself must stay enterable; (2) the mezzanine socket's 1.7 mm pads on a 2.54 mm pitch leave
0.84 mm between pins, less than two clearance halos (2 x 0.425 mm): on the grid every interior pin is boxed in on every layer,
so no mezzanine signal (PWM, RESET, FLT, RDY, OC, FAN_TACH, PG_BIAS, FAULT, SPARE, ISENSE, VIN/VOUT_SENSE, RELAY_ON) could
leave J7 in any run so far - fixed in r8 by B.Cu escape stubs perpendicular to the pin rows (`connector_stubs`); (3) a 0.8 mm
12V_PROT track cannot reach the choke pads (1 mm from their GND_CTRL pad) - 0.5 mm; (4) nets that route alone but fail in the
full run (FB networks, VDD/VEE, 5V_ISO, ISO_15V) are congestion / order effects for the rip-up stage.

### 13.1 Stage 4 continued - repository checkpoints r12 - r14 (2026-10-11)

Same columns as the table above; r13 and r14 are repository builds (`generate_sic_power_board --trials 3 --ripup N
--no-reexec`), their DRC manifests are under `verification/drc/` and `routing_progress_power.json` carries the counts.

| run | change | router s | unres. | DRC | violation classes |
|---|---|---|---|---|---|
| r8 | mezzanine escape stubs (`connector_stubs`), 12V_PROT 0.5 mm | - | 100 | 40 / 99 / 0 | dangling only |
| r9 | stub direction by destination side with a 1.27 mm jog through the other pin row, corridor regions | - | 90 | 38 / 90 / 0 | dangling only |
| r9b | as r9 with 3 order trials + rip-up | - | 68 | 32 / 67 / 0 | every rip-up round reverted |
| r10 (repository) | checkpoint state, 3 order trials (`20261010T191929Z-drc-4e5fe800`) | 190 | 74 | 33 / 73 / 0 | dangling only |
| r11 | per-group order trials (HS / PG / SELV keep their own best order), u5_bias split from ls_bias, shared 12V_PROT socket stub | 533 | 57 | 29 / 56 / 0 | dangling only; group bests HS 6, PG 14, SELV 37 |
| r12 | In2.Cu opened under the SELV strip (3V3 routed as 0.5 mm tracks, its In2 pour a post-route zone), exact stubs for the 1.27 mm barrier rows, Kruskal connection order with retirement of sealed ports (`route_net`), rails before the feedback nets, socket port boxes, probe loops beside the TO-247 courtyards, 4.7 uF Kelvin decoupling on F.Cu | 608 | 32 | 25 / 32 / 0 | 15 track_dangling, 9 via_dangling (5 SW group row under the Kelvin pour, 4 unused bar vias), 1 shorting (5V_ISO stub extended through C75's PGND via); group bests HS 7, PG 13, SELV 11 |
| r13 (repository) | soft clearance conflicts (-2 cells with the newer owner in `Grid.alt`) so the rip-up can cross halos, 12 rip-up rounds, pinned Kelvin / gate / rail / 3V3 nets, 24-via SW group in four rows, 0.8 mm HV stubs, via pruning by ring overlap, stub fallback never through foreign copper (`20261010T205007Z-drc-a96f9f56`) | 748 | 37 | 10 / 35 / 0 | 10 track_dangling only; the pinned prefix was missing from the replay of the best trial order, so the board routed an un-pinned order (41 failures before the rip-up instead of the trials' 36); rip-up kept 7 of 12 rounds |
| r14 (repository) | pinned prefix part of every trial order (replay fixed), 3V3 no longer pinned, SOIC-8 rows (U8 / U9) with short stubs, 30 rip-up rounds (`20261010T211948Z-drc-ddcc4a17`) | 1058 | 29 | 13 / 28 / 0 | 13 track_dangling only; trials HS 10 / PG 11 / SELV 15 = 36, rip-up kept 9 of 30 rounds (36 -> 29); the U8 stub ends are sealed by their row neighbours' escapes (reverted in r15) |

Mechanisms added in stage 4 (all in `grid_router.py`, backwards compatible, 62 host tests): per-net routing regions and zone
keep-outs, Kruskal connection order with retirement of sealed ports, soft clearance conflicts for the rip-up, `signal_pinned`
prefixes, exact stubs for through pads with a lateral jog, via pruning by ring overlap, stub fallback that never crosses
foreign copper.
| r15 (repository) | island rails, Kelvin and driver output nets at 0.25 mm (a 0.35 mm track passes only 1.4 mm channels), 1.75 mm channels in the gate / HS bias regions, LS gate area opened on F.Cu (vias), rip-up takes turns between failing nets with one penalty each, 40 rounds (`20261010T214849Z-drc-d7273d66`) | 915 | 15 | 10 / 15 / 0 | 10 track_dangling only; trials HS 8 / PG 6 / SELV 13 = 27, rip-up kept 13 of 40 rounds (27 -> 15); four of the rest are U8's inward stubs (0.65 mm VSSOP, reverted in r16) |
| r16 (repository, final state of this run) | U8 / U9 stubs outward again (U8 is a 0.65 mm VSSOP, U9 a SOT-23), 60 rip-up rounds (`20261010T223206Z-drc-5b8fb6d1`) | 2026 | 13 | 8 / 13 / 0 | 8 track_dangling only (the stub ends of the unrouted connections); trials HS 8 / PG 6 / SELV 15 = 29, rip-up kept 17 of 60 rounds (29 -> 13) |

### 13.2 Status after r16 - the power board is NOT finished

Native DRC of the repository board (`kicad-cli pcb drc --schematic-parity --severity-all`, manifest
`verification/drc/20261010T223206Z-drc-5b8fb6d1/run.json`): **8 violations (all `track_dangling` at the stub ends of unrouted
connections), 13 unconnected items, 0 schematic-parity findings.** No clearance, keep-out, isolation or shorting finding
remains; every structural rule (HV functional 3.0 / 1.0 mm, 9 mm HV-SELV, 5 mm HV-PE, slots, barrier) passes. The 13 open
connections (router records in `routing_progress_power.json`, DRC items in the manifest's `drc.json`):

| # | net | from | to | cause |
|---|---|---|---|---|
| 1 | HS_RLIM | U2 HV-row stub end (74.58, 138.50) F.Cu | R33.1 (79.59, 132.50) B.Cu | R33 sits at the east edge of `hs_bias`; its pad pocket is closed by the VEE_H / VDD_H tracks (rip-up rounds reverted) |
| 2 | VEE_H | C35.2 (76.78, 128.50) B.Cu | R32.2 (76.83, 132.00) B.Cu | top row of `hs_bias` mixes VDD_H and VEE_H pads: the VDD_H bus along the row boxes the VEE_H pad (structural, swapping the order only swaps the failing net) |
| 3 | DESAT_L_A | (123.88, 132.50) B.Cu, west edge of the LS region | R43.1 (134.68, 136.00) F.Cu | pad on the x = 123.9 region boundary next to D5's 3 mm SW halo |
| 4 | 5V_ISO | U6 HV-row stub end (182.88, 137.88) F.Cu | R57.2 (165.50, 118.09) B.Cu | stub end enclosed between the sense_b parts and the ladder halos |
| 5 | VIN_AMP_P | U8.3 stub end (161.98, 169.33) F.Cu | C81.1 (163.00, 174.78) | U8 is a 0.65 mm VSSOP: the neighbours' escapes wrap the stub end (rows of a strip part have no bar vias) |
| 6 | VOUT_AMP_N | U8.6 stub end (169.03, 169.33) F.Cu | C84.1 (168.00, 174.78) | same as 5 |
| 7 | VOUT_SENSE | U8.7 stub end (169.23, 168.68) F.Cu | its In2 track at (168.00, 163.50) | same as 5 |
| 8 | 3V3 | U8.8 stub end (167.98, 168.03) F.Cu | R82.1 (177.33, 177.50) and the J7 stub (162.75, 155.75) B.Cu | same as 5; the In2 3V3 pour therefore stays in two fragments (the second 3V3 item) |
| 9 | FLT_H_N | U1.13 SELV stub end (96.89, 152.58) F.Cu | B.Cu track (101.38, 154.13) | 1.27 mm barrier row: a track running along the stub-end line seals the short stub's bay |
| 10 | FLT_L_N | U3 SELV stub end (124.64, 152.58) F.Cu | J7 stub (186.87, 155.75) B.Cu | same as 9 |
| 11 | PWM_H | J7 stub (195.76, 155.75) B.Cu | R17.1 (101.83, 157.50) F.Cu | 94 mm strip crossing not found within the 1.2 M node budget after the other strip nets took the corridors |
| 12 | BIAS_EN_F | U4 SELV stub end (139.18, 152.80) F.Cu | B.Cu (136.50, 167.25) | 0.65 mm row: the short-stub bay is sealed by tracks along the row ends |
| 13 | 3V3 (zone) | In2 pour fragment | In2 pour fragment | consequence of 8 |

What would finish it (not done in this run): a per-row escape pattern for the 0.65 mm strip part U8 (bar vias or a second
escape layer), lanes that keep the row-end line of every stub row free of foreign tracks, and the VDD_H / VEE_H pad
orientation constraint for the hs_bias top row; the rip-up stage (one penalty per connection, nets taken in turns) resolved
17 of 29 trial failures in r16 and reverts the rest because the ripped nets cannot be re-routed either.

Layout metrics (`engineering_checks/layout_metrics_power.{json,md}`, 58 rows): 24 within threshold, 25 measured only, 9
exceeding - PE-PCB-002 Q2 source to the nearest HF capacitor 41.2 mm (floorplan heritage: the HF tier sits at the Q1 end of
the block), PE-PCB-006 VIN_RAW and VOUT_L without vias (single-layer pours by design), KR-ISO-002 HV-to-PE and the four HV
functional rows at 0.3 mm (the checker measures abutting zone outlines, the native DRC rules pass), KR-TH-002 B.Cu 0.0 (to be
reviewed); all nine are human-review rows, unchanged since the first checkpoint.

## 14. Stage 5 - fresh-eyes round on the r16 state (2026-10-11, this agent)

Diagnosis of the 13 open connections of r16 with pcbnew on the saved board (`converge/power2/diag_board.py`: copper within 1.6 mm
of every start / end point) and a flood fill of the router's own occupancy rebuilt from the saved board plus the saved plan
(`diag_flood.py`: reachable cells per layer and the frontier composition of every pocket; `diag_astar.py`: the real A* on that state):

| r16 item | finding on the saved board |
|---|---|
| HS_RLIM, VEE_H | start and end lie in one reachable region of 39 k / 51 k cells; the hard A* finds paths of 157 / 29 nodes. They became routable when later rip-up rounds moved VDD_H / KS_H copper, but `negotiate` logged "soft path crosses no rippable net" and skipped them (a free path has no victims) - a router defect, not a geometry problem |
| DESAT_L_A | R43.1 (F.Cu) is a 65-cell pocket: VEE_L / VDD_L / DESAT_L_OC halos overlap the pad halo on three sides (soft -2 cells) and the DESAT_L_OC In2 track under the pad blocks the via option (vocc is layer-free) - the rails, routed first, hugged the pad |
| 5V_ISO | the U6.1 stub end's pocket (8855 cells) is walled on B.Cu by the VIN_DIV / VOUT_DIV filter routes: the shelf packer had left-aligned the six sense_b parts at x 168.5-178.7, far from their taps (x 189.6 / 193.0) and AMC pins, so both filter nets crossed the 6 mm band |
| VIN_AMP_P, VOUT_AMP_N, VOUT_SENSE, 3V3 (U8) | U8's alternating 0.6 / 0.8 mm stubs: the two middle pads of each 0.65 mm column can only leave straight ahead; VIN_AMP_N wrapped pad 3's port (2 cells reachable), VOUT_AMP_P wrapped pads 6 and 7 (1-7 cells) |
| FLT_H_N, BIAS_EN_F | 1.27 mm (U1.13) and 0.65 mm (U4.4) stub ends sealed by the neighbours' escapes jogging to 0.5 mm beside the long stub and running south (163 / 14 cells reachable) |
| PWM_H | its J7 port sits in a 5818-cell pocket of the corridor north of the socket (x 188-212, y 153-158) closed on every layer by the east-west buses (BIAS_EN_F, ISENSE, FLT_H_N, 3V3, OC_N, RDY_H, VOUT_OUTN) and the socket stubs |
| FLT_L_N, 3V3 (J7.40), PWM_H (R17 side) | the strip is cut at x 175-177 south of the socket on all three layers by U8's network column (R71 / R72, their vias, FAN_TACH / 12V_PROT / VIN_OUTP verticals): regions of 625 k cells end at x 176.7 while others span the whole strip only through their own copper |

The mezzanine socket (1.7 mm pads on a 2.54 mm pitch) is a wall across the strip on the grid, so every net that needs the other
side goes round one end; the r16 geometry sent the inner-row pins north into the barrier escape corridor and the outer-row pins
south, and the corridor (5.7 mm, three layers) then had to carry the barrier escapes, the socket ports and ~16 east-west buses.

Corrections of this round (generator `generate_sic_power_board.py`, router `grid_router.py` - backwards compatible, new optional
plan keys only):

1. **Socket escapes all south** (`connector_stubs`): outer-row pins straight to y 162.05, inner-row pins jog 1.27 mm west and run
   between the outer pins to y 163.3 (0.295 mm to each pad, as the r9 north jogs did), same-net column pairs (12V_PROT 1/2, 3V3
   39/40, four GND pairs) are linked by a straight B.Cu track with one stub; every stub ends in a 0.6/0.3 via (`fanout.exact_via_pads`),
   so each of the 44 ports lives on all three strip layers and the corridor north of the socket carries only the barrier escapes
   and buses. Parts under the socket start at y 165.0 (`SELV_SOCKET_PARTS_Y`), the port boxes are no longer needed.
2. **1.27 mm rows** (U1 / U3 / U6 / U7 / U10 both sides, `fine_pitch_escapes`): a via at every exact stub end (ring gap 0.67 mm,
   0.845 mm to the neighbouring stub); the AMC1311 HV rows use 0.3 mm stubs and 0.3 mm bar vias so the vias sit between the
   AMC pads and the filter row.
3. **0.65 mm rows** (UCC14141 pads 3-5 / 32-34, the U8 columns): a deterministic fan per group of consecutive singles - the outer
   pads run a 1.3 mm leg sideways at 1.75 mm depth (past the bar vias), the middle pad continues 0.9 mm deeper (groups of three)
   or the two inner pads 1.3 mm deeper with legs (groups of four), each pad ending in its own via (`FAN_*`); the fan copper and vias
   are placer obstacles (`escape_obstacles`, `ESC_GAP`).
4. **Router** (`grid_router.py`): `negotiate` routes a failing connection directly when its hard path exists before looking for
   victims; `retry_unresolved` re-tries every open connection once at the end of the signal stage (`report['retried']`);
   `fanout.direct_lane_mm` reserves the exit corridor of every direct (pad-centre) port (0.75 mm here) and `fanout.exact_lane_pads` /
   a pre-routed via's `lane` reserve the corridor beyond a stub or fan via (the socket vias down to y 165.5 on B.Cu, the barrier SELV
   ports 2 mm into the corridor on F.Cu); the reservations are replayed by `rebuild_occupancy`, which the rip-up rounds call - in the
   first attempt they vanished at the first round and PWM_L ran straight through RDY_H's lane at y 164.0. `_register_pads` now
   rotates a slot's drill size with the pad: the barrier footprints' 16 mm NPTH slots (packages rotated 90 / 270) were marked as a
   vertical hole band through each package centre, which forbade vias at the centre pads of every 1.27 mm row (U1 / U3 pads 4, 5,
   12, 13 and their U6 / U7 / U10 counterparts: 10 stub-end vias skipped in b1-b3).
5. **Sensing island**: the six AMC1311 filter parts are fixed upright on B.Cu at y 136.0 (PGND pad down: in-pad via ring 3.6 mm
   from the ladder pads), C72 / C76 (5V_ISO decoupling) directly under U6.1 / U7.1, the VIN_DIV group under U6 and the VOUT_DIV
   group beside the VOUT tap; the ladder taps end in vias, so both filter nets stay on B.Cu and F.Cu in the band is free for 5V_ISO.
6. **Bias networks (U2 HS, U5 sensing) fixed instead of shelf-packed**: two rows of upright parts on B.Cu; row A's lower pads are the
   FB_VDD / FB_VEE / RLIM nodes right above their fan vias (1-2 mm straight connections, RLIM 4.5 mm along y 136.5), the rails on the
   upper pads and in row B, every PGND-carrying part east of x 157 so the F.Cu DESAT row keeps its room; parts with a PGND via stay
   3 mm from the snubber pads. The shelf-packed rows of r16 / b1 / b2 mixed the nets per column, and the VEE_H meanders between the
   rows sealed HS_FB_VEE / HS_FB_VDD in every run (the rip-up of VEE_H was reverted four times in b2).
7. **Strip regions**: `selv_east` starts at x 216 (3.7 mm passage round the socket's east end), the RESET_N and BIAS_EN input
   filters (R67 / C78 / R68, R69 / C79 / R70) move to `selv_ls` next to their consumers, U8 and its 0805 3V3 decoupling are fixed
   (the cap beside the 3V3 fan via), 3V3 routes at 0.25 mm (its In2 pour is the distribution copper), `MAX_NODES` 1.5 M, the
   `MEZZANINE J7` silkscreen moved east of the socket's west third.
8. **Socket exit band de-interleaved**: 17 of the 44 interleaved ports were GND_CTRL pins that only need a plane via; their jog stubs
   now stop right below the outer pads (via at y 161.6, ring 0.45 mm from the pads, no lane), so the exit band holds 25 outer ports at
   2.54 mm pitch plus 6 interleaved signal ports - between 2.54 mm lanes a via fits (1.07 mm vocc gap), between 1.27 mm lanes nothing
   does, which is why the last-routed ports of b2 / b4 (PG_BIAS_H_N 504 cells, FAN_TACH 3054) stayed sealed under the first bus.
9. **Lane release** (`Router.release_lanes`): a routed net's reserved corridor is obsolete and the corridors of other ports are free
   copper for the connections still open - the negotiate rounds drop the lanes of routed nets and the final retry pass drops them all
   (in b4 the flood fill without lanes showed PG_BIAS_H_N, FAN_TACH and 3V3 routable on the final copper while the router kept them
   sealed by reservations).
10. **LS bias network (U4) fixed rows** like HS / U5 (the shelf-packed 1206 decoupling capacitors boxed the VDD_L bar via: 1687 cells),
    `ls_gate` shrunk to x <= 134.5 with default channel gaps; **1.5 mm exit lanes for the end pads of the 1.27 mm HV rows** (U1.8's
    VEE_H via was sealed by DESAT_H_A / VDD_H / HS_CLMP buses running along the row front: 1415 cells); the U5 row keeps >= 3 mm from the
    VIN ladder feed via (R57 pad edge 165.5, C67 in the upper row) after b4's four 3 mm clearance findings.
11. **b7 (after the b5 checkpoint)**: a parts-free band y 176-179.5 along the whole strip bottom (`SELV_PARTS_MAX_Y`) for the long
    east-west buses, which b5 could not thread through U8's network column at x 176 (12V_PROT, BIAS_EN); the selv_ls rect under the
    socket's west end starts at y 169 so the J7.43-49 ports keep a 3.5 mm exit band (VOUT_SENSE's J7.49 port was boxed by L4); the HS
    gate network fixed in two B.Cu rows with the three gate resistors upright above their driver-pin stub vias (HS_OUTL / HS_CLMP / G_H
    pockets of 808 / 255 cells behind G_H and KS_H tracks of the shelf-packed layout); the RESET / BIAS filters back in selv_hs.

12. **b8**: a 2.2 mm placer corridor (`ESCCOL`, B side) above the single HV-side bar via of a net (VDD_H / VDD_L / ISO_15V), so the
    packed 1206 rows of `ls_bias` cannot box the VDD_L via exit again (b7: 1277 cells); the three inner socket pins whose nets live
    north of the socket (J7.30 PG_BIAS_S_N, J7.32 PG_BIAS_H_N, J7.36 SPARE_D1, `CONNECTOR_NORTH_PINS`) escape straight north into
    the corridor (via at y 155.9, 1 mm lane) and TP12 is fixed in the corridor at (176, 154), which removes three interleaved ports
    from the south exit band; four order trials (the fourth a seeded perturbation of the best) and 30 rip-up rounds by default
    (`SIGNAL_ORDER_TRIALS`, `RIPUP_ROUNDS`). Result in scratch: one open connection (VDD_L C56.1 -> C58.1 on the LS island), DRC
    0 violations / 1 unconnected / 0 parity.

13. **b9 / b10 - router lane restore and the LS DESAT row channels**: in b8 the last open link (VDD_L C56.1 -> C58.1, both F.Cu
    pads of the shelf-packed `ls_desat` rows) sat in a 5066-cell pocket - VEE_L had taken the single-track channel between the rows,
    G_L / DESAT_L_A ran on In2.Cu and DESAT_L_OC / LS_CLMP on B.Cu round C58.1, and a via cannot stand in a 0.9 mm channel. Two
    corrections: (a) `grid_router.py` remembers every exit lane it reserved (`_lane_memory`) and `negotiate` gives a ripped net (target
    or victim) its lanes back before the re-route (`restore_lanes`), so the connections routed first in a round cannot seal the
    ripped nets' ports; `retry_unresolved` runs twice, first with the open nets' own lanes still reserved, then without any lane
    (b9: router 1 open link, G_L R38.2 -> R39.2 on B.Cu, closed by the G_L pour - native DRC 0 / 0 / 0); (b) `REGION_GAPS['ls_desat']`
    = (0.8, 1.1): 1.1 mm between the courtyards is 1.56 mm pad to pad, room for two 0.25 mm tracks at 0.3 mm clearance (the 0.9 mm
    default holds one); R42, the upright 1206 at the region's east end, keeps the default gaps (`REF_GAPS`) so it still fits before
    the fixed U5 bias row at x 157.2. b10: 0 open connections, DRC 0 / 0 / 0 in scratch; r19 is the repository build of that code.

### 14.0 Builds of this round

| run | where | change | trials / rip-up | router s | unresolved | DRC viol. / unconn. / parity | manifest |
|---|---|---|---|---|---|---|---|
| b1 | scratch | south-only socket escapes with stub vias and links, stub vias on the 1.27 mm rows, fans with vias on the 0.65 mm rows (U2 / U4 / U5 singles, U8), direct-port lanes, retry pass, sensing filters fixed on B.Cu, RESET / BIAS filters west, 3V3 0.25 mm | 1 / 0 | 195 | 28 | 18 / 28 / 0 (17 track_dangling, 1 via_dangling) | scratch b1 |
| b2 | scratch | as b1 plus lanes beyond the socket / barrier SELV stub vias (not yet replayed after rip-up), bus band y 164-166 | 3 / 20 | 546 | 8 | 5 / 8 / 0 (5 track_dangling) | scratch b2 |
| b3 | scratch | lanes replayed by rebuild_occupancy, C72 / C76 under the AMC pins, U8 + C88 fixed | 1 / 0 | 311 | 25 | not run | scratch b3 |
| b4 | scratch | slot drill rotated in _register_pads (10 stub vias no longer skipped), HS / U5 bias networks as fixed rows, C72 / C76 under the AMC pins | 3 / 20 | 1125 | 9 | 11 / 9 / 0 (4 clearance: fixed U5 row inside the 3 mm halo of the VIN ladder feed via; 6 track_dangling, 1 via_dangling) | scratch b4 |
| b5 | scratch | lane release (routed nets per rip-up round, all before the retry), inner GND socket pins with shallow plane vias (no interleaved lane), U5 row >= 3 mm from the VIN feed via, C88 beside the 3V3 fan via | 3 / 20 | 764 | 6 | 4 / 5 / 0 (4 track_dangling) | scratch b5 |
| b6 | scratch | as b5 plus fixed LS bias rows, ls_gate shrunk, 1.5 mm lanes for the HV-row end pads - worse (PGND group 1 -> 6), reverted | 3 / 20 | 632 | 10 | 7 / 9 / 0 (7 track_dangling) | scratch b6 |
| r17 (repository) | repository | checkpoint of the b5 state (same code, deterministic router) | 3 / 20 | 826 | 6 | 4 / 5 / 0 (4 track_dangling at the open connections' stub ends) | `verification/drc/20261011T010622Z-drc-a0059690` |
| b7 | scratch | parts-free bus band y 176-179.5 (SELV_PARTS_MAX_Y), nothing under the socket west end above y 169, HS gate network in fixed B.Cu rows, RESET / BIAS filters back in selv_hs - HS island fully routed; new failures in the sensing strip (VOUT_SENSE R78.2 pocket 611 cells, 3V3 R82.1 94 cells), VDD_L bar via pocket (1277), PG_BIAS_H_N / SPARE_D1 / ISENSE socket ports sealed | 4 / 20 | 623 | 6 | 4 / 6 / 0 (3 track_dangling, 1 via_dangling) | scratch b7 |
| b8 | scratch | as b7 plus placer corridors (2.2 mm) above a net's single HV-side bar via (ESCCOL, B side), inner socket pins 30 / 32 / 36 escape north (via at y 155.9, 1 mm lane), TP12 fixed in the corridor (176, 154), 4 order trials (seeded perturbation of the best), 30 rip-up rounds | 4 / 30 | 753 | 1 | 0 / 1 / 0 (VDD_L C56.1 -> C58.1: VEE_L took the single-track channel between the ls_desat rows) | scratch b8 |
| r18 (repository) | repository | checkpoint of the b8 state (same code, deterministic router: same open connection) | 4 / 30 | 794 | 1 | 0 / 1 / 0 (VDD_L C56.1 -> C58.1) | `verification/drc/20261011T013853Z-drc-22d35aba` |
| b9 | scratch | as b8 plus router: a ripped net gets its reserved exit lanes back before the re-route (restore_lanes), the final retry runs first with the open nets' own lanes kept, then without any lane | 4 / 30 | 770 | 1 | 0 / 0 / 0 - the one router-open link (G_L R38.2 -> R39.2, B.Cu) is closed by the G_L B.Cu pour, so native DRC reports no unconnected item | scratch b9 |
| b10 | scratch | as b9 plus ls_desat rows 1.1 mm apart (two 0.25 mm tracks per F.Cu channel; the 0.9 mm default held one), R42 keeps the default gaps (upright 1206 before the fixed U5 row) | 4 / 30 | 728 | 0 | 0 / 0 / 0 | scratch b10 |
| r19 (repository) | repository | checkpoint of the b10 state (same code, deterministic router) | 4 / 30 | 748 | 0 | 0 / 0 / 0 | `verification/drc/20261011T015623Z-drc-280475df` |

### 14.1 Repository state after this round

Board `kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` (sha256 ae0f05d86ac6a104...): 237 footprints, 4752 tracks, 574 vias, 32 zones; router unresolved 0; **kicad-cli DRC (`--schematic-parity --severity-all`, manifest `20261011T015623Z-drc-280475df/run.json`): 0 violations, 0 unconnected items, 0 schematic-parity findings.**

No open connections remain in the router report.

### 14.2 Notes for the reviewer

- The r19 board is DRC-clean under the project's own rule set (`.kicad_dru` untouched: HV functional 3.0 / 1.0 mm, same-island 0.3 mm,
  HV-SELV 9 mm, HV-PE 5 mm, pin-field exceptions, CTRL_SELV 0.25 mm) with `--schematic-parity --severity-all`; no rule was excluded or weakened.
- `layout_metrics_power.{json,md}` (58 rows): 24 within threshold, 9 exceeding, 25 measured-only - the same nine rows as in r17 (PE-PCB-002
  Q2 source to C1.2 41.2 mm; PE-PCB-006 VIN_RAW / VOUT_L via counts; KR-ISO-002 raw copper distances measured inside the TO-247 pin fields
  and the snubber / sense taps, where the DRC rules carry the documented exceptions; KR-TH-002 B.Cu copper under the heatsink courtyard).
  They are engineering-review items of the floorplan, not routing findings, and they did not change in this round.
- b9 (scratch) showed that a router-open link can still be a DRC-connected board when a post-route pour (here the G_L B.Cu pour) closes it;
  r19 has no such case (router 0 open, DRC 0 unconnected).
- Scratch material of this round (diagnostics, patch scripts, the b1-b10 boards and their diagnostic DRC manifests, the r16 backup of the
  previous deliverables) lives in the agent scratchpad `converge/power2/`; nothing of it is repository evidence. Nothing was committed.


## 15. Round r20 - corrections from the second independent review (LR-20..LR-35), 2026-10-11, correction agent

Inputs: `verification/layout_review_findings.json` (schema 2) and `verification/pcb_rule_review.md` on the r19 board
(sha256 `ae0f05d86ac6a104...`, DRC manifest `20261011T021012Z-drc-0ebee900`). Snapshot of the r19 state kept as
`engineering_checks/layout_metrics_power_before2.{json,md}`; the r19 board copy and its geometry measurements live in the agent
scratchpad (`c2/before/`) and are referenced by sha256 in `optimisation_before_after.md` (Pass 2).

### 15.1 Generator changes (automation/kicad_tools/generate_sic_power_board.py)

- LR-20 (blocker, stored fills at 0.3 mm): `rule_aware_refill()` reloads the SAVED board in a fresh KiCad Python process
  (`pcbnew.LoadBoard` initialises the DRC engine from the project `.kicad_dru`, verified in scratch: a refill of the r19 board file
  this way reproduces the review's refilled areas - F.Cu VIN 5690 -> 4508 mm2, B.Cu PGND 10559 -> 8873 mm2 - and a no-refill DRC of
  the result is 0 / 0), refills every zone and saves with `aSkipSettings=True` (the project file is not touched; its hash is
  checked). `stored_fill_check()` then runs a kicad-cli DRC WITHOUT `--refill-zones` on a temporary copy and records the counts in
  `engineering_checks/stored_zone_fill_check_power.json` - a diagnostic of the stored copper, not verification; the verification DRC
  stays `run_check` (`--refill-zones --schematic-parity --severity-all`). The in-process `ZONE_FILLER` of the routing stage is left as
  it was (its fills are overwritten by the final refill); why it did not carry the netclass rules in the r19 run was not resolved.
- LR-21 (blocker): `HS1_HOLE_{1..4}` rule areas on all four copper layers around the sink's 3.2 mm NPTH holes - 16-gons circumscribed
  about r = 1.6 + 5.1 mm (pours and vias forbidden; tracks allowed because the PE spine, at sink potential, passes the north-west hole).
- LR-23 (blocker), final variant (r20d; the r20a variant J2 <-> J6 is described under 15.2): J2 (PGND input return) and J5 (relay
  input, VIN_RAW) swapped - J2 now at (23.0, 112.0) in the open east position of the UPPER input row, where the In1 return plane
  reaches it over its full width; J5 in the corner pocket at (7.5, 129.0) under J1 (same net, joined by the VIN_RAW pours - its
  current never leaves the pocket); J6 (VIN) stays at (23.0, 129.0) inside the VIN+ F.Cu band (band start x 14 -> 17); the PTC pad
  RT1.1 is fed by a 2 mm B.Cu VIN_RAW track from the J1 pin-field pour along y 101.5 (`rt1_vin_raw_feed`); the B.Cu PGND column
  continues under the HF tier (x 43.4-61.5, y >= 122.65).
- LR-28 (should-fix): SW In2 block top 119 -> 112 and neck top 100 -> 85 (the neck now passes the new north-east hole keep-out on
  both sides); 32 x 1.2 mm PGND stitching vias (170-191, 76-85) join the B.Cu output block (J4 field) to In1.
- LR-25 (should-fix): the MOV RV1 (23 mm) leaves the intake corridor for (165.0, 88.5) east of J4; the sink, J3 / J4 and the output
  films C13 / C14 moved 1.1 / 1.2 / 1.3 mm east so the input films C11 / C12 keep >= 20 mm courtyard distance (CR-23) while J3 / J4
  keep >= 5 mm to the courtyard and C13 keeps 20 mm; PE spine x 58 -> 59.5 (hole-wall clearance after the sink shift). RT1 (PTC,
  22 mm) stays: its VIN_RAW / VIN pads bridge the two pours and no corridor-free position reaches both.
- Silkscreen labels follow (RELAY / PGND at the input, VOUT+ / PGND at the output, heatsink texts).

### 15.2 Builds of this round

- r20a (12:48-13:02 local): LR-20 / LR-21 / LR-28 / LR-25 as above plus a first LR-23 variant (J2 <-> J6 swap: PGND at (23.0, 129.0),
  VIN relay terminal J6 in the corner pocket with a local outer-layer pour). Result: 4752 tracks, 606 vias, 38 zones, 0 open, kicad-cli
  DRC `verification/drc/20261011T050201Z-drc-70f9facd/run.json` 0 / 0 / 0, stored-fill DRC without refill 0 / 0, board sha256
  `37707a753fd7ea43...`; measured (erosion-connectivity, stored fills): PGND J2 -> HF tier In1 4.6 -> 12.1 mm, B.Cu 0 -> 10.1 mm,
  HS1 hole walls to HV copper In1 / In2 0.25 -> 5.1 mm, SW via group -> L1.1 In2 5.2 -> 11.1 mm - BUT VIN J6 -> Q1.1 In2 11.3 -> 3.9 mm:
  the pocket's 3.9 mm In1 / In2 passage simply moved from the return to the VIN terminal. Superseded (kept in the scratchpad `c2/r20a/`).
- r20b (13:08, placement stage): LR-24 variant with the LS gate region reduced to [123.5, 128.6, 140.5, 137.8] - `no placement space for
  R41`; region re-cut from the island top (127.6) in r20c.
- r20c (13:11-13:34 local, 1343 s): LR-23 as finally kept (J2 <-> J5: PGND at (23.0, 112.0), relay input J5 in the pocket under J1 - same
  net, RT1 fed by a B.Cu VIN_RAW track), SW In2 block top 95, plus the LR-24 / LR-26 layer-restriction attempt (LS gate loop B.Cu only,
  AMC1311 output pairs F.Cu only, LS gate region as one rect from y 127.6). Result: 4070 tracks, 555 vias, **9 open** (LS_OUTH / LS_OUTL /
  LS_CLMP failed at once - their U3 stub-end ports are F.Cu stubs and a single-layer region allows no via; VIN_OUTP / VOUT_OUTN could not
  cross the strip on F.Cu alone and sealed RDY_L / 3V3; LS_FB_VEE / DESAT_L_OC lost their channels to the re-packed gate region); DRC
  `verification/drc/20261011T053341Z-drc-ba043c49/run.json` 8 violations (7 dangling stub ends of the open nets, 1 clearance: the
  VIN_RAW feed track at y 101 was 2.75 mm from the C12 VIN pin) / 10 unconnected / 0 parity. Not kept: LR-24 and LR-26 reverted (the
  mechanism stays in the generator as empty lists `LS_GATE_LOOP_NETS` / `AMC_PAIR_NETS`), the LS gate region restored to its two rects,
  the VIN_RAW feed moved to y 101.5 and started inside the J1 pin-field pour (r20d).
- r20d (13:35-13:45 local, 565 s) - **the delivered board**: LR-20 / LR-21 / LR-23 (J2 <-> J5 variant, RT1 feed at y 101.5 from the J1
  pin-field pour) / LR-28 (SW block top 95) / LR-25 as in 15.1, LR-24 / LR-26 reverted. Result: 237 footprints, 4755 tracks, 606 vias
  (90 PGND), 36 zones (18 copper + 4 heatsink-hole keep-outs + 14 other rule areas), 12 order trials, 21 rip-up rounds, **0 open**;
  rule-aware refill changed F.Cu VIN 5639 -> 4530 mm2, B.Cu PGND 10760 -> 9042, In1 PGND 30031 -> 28680, In2 VIN 18091 -> 16940; kicad-cli
  DRC `verification/drc/20261011T054445Z-drc-d0914d79/run.json` (`--schematic-parity --severity-all --refill-zones`): **0 violations,
  0 unconnected, 0 parity** on board sha256 `b1bb5698194b9aea...`; stored fills checked WITHOUT refill (diagnostic,
  `engineering_checks/stored_zone_fill_check_power.json`): 0 / 0. Layout metrics (58 rows): 27 within, 6 exceeding, 25 measured-only
  (r19: 24 / 9 / 25); the six: PE-PCB-002 Q2.2 -> C1.2 41.2 mm (LR-22 open), PE-PCB-006 VIN_RAW / VOUT_L without vias (THT-joined pours),
  KR-ISO-002 VIN-PGND and VOUT-PGND 1.95 mm on F.Cu inside the R6 / R10 pin fields (per-footprint rules 1.79 mm), KR-TH-002 B.Cu PE link
  column inside the sink courtyard (LR-29) and the HF row-A PGND pads 4.955 mm from the courtyard on F.Cu.

### 15.3 Repository state after this round

- `kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` sha256 `b1bb5698194b9aea...` (r20d); `design/placement_power.json`,
  `design/routing_plan_power.json`, `verification/routing_progress_power.json` (with `rule_aware_refill` and `stored_fill_check`),
  `engineering_checks/layout_metrics_power.{json,md}` all describe this board; `engineering_checks/layout_metrics_power_before2.{json,md}`
  keep the r19 metrics.
- Measured before / after (erosion-connectivity necks on the stored fills, hole distances, courtyards, fill areas, via counts):
  `verification/optimisation_before_after.md` (Pass 2) and `.json` (`pass2`), dispositions in `verification/optimisation_finding_status_pass2.json`.
- The r20a, r20b and r20c boards and their logs live only in the agent scratchpad (`c2/`); their DRC manifests stay under `verification/drc/`
  as the history of this round. Nothing was committed; no rule, library, schematic or project file was changed (the project-file hash is
  recorded in every manifest).
