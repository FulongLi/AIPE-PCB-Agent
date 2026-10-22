# DAB-V1 routing remediation (2026-10-21) - root causes and fixes

**Status: engineering prototype review material. AI-generated, human review required.** This note records why the
first routing pass of the three DAB-V1 boards (commit `641d478`, PR #7) left DRC errors and open connections, what in
the generator caused each failure class, and what was changed. Every statement about the boards is backed by a native
`kicad-cli` report or a router report under `examples/dab-10kw/`; nothing here is a qualification of the design.

## 1. Starting point (kicad-cli 10.0.6, `pcb drc --schematic-parity --severity-all --refill-zones`)

| Board | ERC | DRC errors | DRC warnings | Unconnected items | Router result |
|---|---|---|---|---|---|
| primary-power | 0 | 22 (20 `clearance`, 2 `hole_clearance`) | 35 dangling tracks/vias | 82 in 42 nets | 2470 tracks, 411 vias, 79 open connections (30 fan-out, 49 route), 1215 s |
| secondary-power | 0 | 2 (`hole_clearance`) | 35 dangling | 81 in 42 nets | 2703 tracks, 455 vias, 80 open (30 fan-out, 50 route), 1326 s |
| control | 0 | 0 | 0 | 499 (placed, never routed) | router stopped at the time box before it saved |

Reports: `verification/drc/20261021T071523Z-drc-39f76185` (primary), `20261021T071639Z-drc-ce8b8c2f` (secondary),
`20261021T072243Z-drc-bff9bf17` (control); router reports `pcb/routing_report_<board>.json` of that commit.

## 2. Root causes, by failure class

### 2.1 Twenty `clearance` errors at 3.95 mm against the 4.0 mm BUS_P-PGND rule (primary only)

*Evidence.* Every error pairs a 0.5 mm pre-routed capacitor stub on F.Cu (`pre_routed.tracks` of the plan) with the
opposite electrode of the same 2220 ceramic (`Functional HV_01-HV_02 800 V working envelope`, required 4.0 mm, actual
3.95 mm). The 2220 land gap is 3.3 mm; the stub leaves the pad centre, so its edge is 0.25 mm closer to the other land
than the pad edge, i.e. 3.3 + 0.9 - 0.25 = 3.95 mm. The pad-to-pad relaxation rule (`memberOfFootprint`) does not
cover tracks, correctly.

*Cause.* Stub width (generator constant), not a rule problem.

*Fix.* `floorplan.copper_plan` writes the stubs at 0.3 mm (3.3 + 0.9 - 0.15 = 4.05 mm). The fix was already in the
generator at `641d478` but the boards had not been regenerated with it.

### 2.2 Two `hole_clearance` errors at the VEEA net ties (both boards)

*Evidence.* `NT1`/`NT5`: a via of the tie's own net sits in the tie's 0.5 mm pad (`via [VEEA_AH] @ (96.00, 67.38)` on a
footprint at `(95.75, 66.75)`); KiCad measures the drill against the tie's bridging copper, a netless `fp_poly`.

*Cause.* Two gaps in the router's occupancy model (`automation/kicad_tools/grid_router.py`): footprint copper graphics
are not pads and were never registered, and a net may place a via on its own SMD land (via-in-pad), which the pad
halo permits because the land carries the net's own code. The 2.6 x 2.0 mm keep-out written at `641d478` as a fix
would also have blocked the tracks that must reach the tie's pads (it was never run).

*Fix.* `Router._register_pads` now registers every footprint copper graphic as a via and drill exclusion
(`graphics_registered` in the report); that alone keeps vias off the tie's bridge. A plan option `fanout.no_via_in_pad`
(SMD lands refuse via centres of every net including their own) was added as well, but the DAB plans leave it off: the
first re-run showed that forbidding every via near every land removed the few via positions the 0.6 mm gate-loop nets
have inside the islands. The keep-out code was removed.

### 2.3 Thirty fan-out failures per power board: the 0.65 mm UCC14141 rows

*Evidence.* The failing pads are pins 4, 5, 30-33 of every DWN-36 module (`unresolved[].stage == 'fanout'`). A host
reproduction with the real `Grid` class and the recorded pad boxes (`tests/test_dab_v1.py::FinePitchRowTests`) shows
that at the 0.35 mm stub length the stub's end cell is a soft-conflict cell (-2): the 0.40 mm lands at 0.65 mm pitch
are 0.25 mm apart, the pad halo of `clearance + trace/2` is 0.4 mm, so neighbouring halos overlap and whether a given
stub end lands on an overlapped cell depends on the beat between the 0.65 mm pitch and the 0.125 mm grid. At 0.45 mm
every end cell is clear.

*Cause.* Stub length below the halo band of the neighbouring lands; the end-cell test knew only the occupancy codes,
not the geometry.

*Fix.* `exact_stub_mm: 0.45` in `routing_*.yaml`, and `Router._exact_end_ok` accepts a -2 end cell when the stub copper
itself keeps the clearance from every foreign pad box (hard blocks and foreign copper still refuse), then claims the
cell so the search can start there.

### 2.4 About 35 route failures per power board: wide nets sealed in the fine-pitch rows

*Evidence.* `12V_BIAS_x`, `GNDP_x`, `PG_BIAS_N`, `VEE_x`, `VDD_x`, `DRV_RSTF`, `3V3` records with `expanded: 1` or
`occupancy.start: -2`; their ports are the stub ends of adjacent 0.65 mm pins.

*Cause.* A net wider than its stub (12V_BIAS 0.8 mm, GNDP 0.6 mm, VDD/VEE 0.5 mm) cannot leave a port that sits 0.65 mm
from the stubs of its neighbours: the router dilates foreign copper by `(width - trace)/2` for the net, the neighbour
stub halo (0.57 mm) plus the dilation (0.25 mm) exceeds the pitch, so every neighbour cell of the port is blocked. The
same-net pin pairs (GND 1-2, VIN 6-7, VDD 28-29, VEE 30-31) could not even be joined, because a 0.6-0.8 mm track does
not fit between the row's stubs. A wide net that did route at full width from its port (VDD before VEE in
`signal_first`) marked the neighbouring port as -2 and sealed it.

*Fix.* `automation/dab_v1/fanout_rows.py`: for every IC row below `fine_pitch_mm` (0.8 mm) consecutive same-net pads
are joined by a pre-routed *bridge* inside the lands (0.3 mm wide, within the 0.40 mm land, 0.25 mm from the next
land), each same-net run gets exactly one exact stub at the run's midpoint (on the bridge for even runs), the other
pads are skipped, and the stub length is computed from the occupancy model: clear of the lands' halo band, and for a
net wider than its stub beyond the dilated halo of every neighbouring stub (0.5 mm for 0.3 mm nets, 0.65-0.75 mm for
the paired 0.5-0.8 mm nets, 1.05-1.3 mm for a single wide pin between foreign stubs). Pads of pour nets (PGND of the
sensing module) are bridged and skipped. The row-end pads were also classified with the wrong escape direction
(the courtyard of the DWN-36 is nearly square); the direction now follows the pad row the pin belongs to.

### 2.5 Five stranded GND_CTRL capacitor pads per power board

*Evidence.* `C27/C51/C75/C99/C16 pad 2 [GND_CTRL]` fan-out failures; `copper_islands`: five one-pad GND_CTRL islands.

*Cause.* The 100 nF decoupling capacitors are placed, correctly, at the drivers' logic pins, but the cluster of pins,
1210 input capacitors and pull-up resistors leaves no spot for an escape via within the 12 x 4 mm search band, and the
ground net is connected only through escape vias to the In1.Cu plane; a failed escape is a dead pad.

*Fix.* `fanout.fallback_direct_nets: [GND_CTRL]` keeps such a pad as a direct port, and `ground.route_stranded` ties
every stranded ground port to the nearest via or plated pad of the net after the signal stage (`stranded_routing` in
the report; failures stay visible as unresolved records).

### 2.6 Sealed ports in the HV islands (`VDD_x`, `NTC_x`, `FBVEE_x`, `VEEA_x`, `3V3`, `DRV_RSTF`)

*Evidence.* Route records with 100 000-150 000 expansions (the whole reachable pocket flooded) for ports in the
islands; `3V3 (88.1, 80.0) -> (85.1, 81.3)` with 114 expansions: the 1210 input capacitor `C33` of the bias module sat
0.5 mm below the driver's 3V3 and DRV_RSTF stubs.

*Cause.* `fill_region` packed parts with a 0.25 mm courtyard gap, which leaves about 0.9 mm between pads - too little
for a 0.5-0.6 mm track with 0.25 mm clearance - and nothing reserved the room the fan-out stubs and the first track
segment need next to the ICs.

*Fix.* `placement.part_gap_mm` (0.6 mm on the power boards, 0.4 mm on the control board) and
`placement.ic_stub_reserve_mm` (1.8 / 1.2 mm: the IC courtyards are inflated by this margin while the regions are
filled). ICs are placed first in every region.

### 2.7 Split laminated planes and isolated pours

*Evidence.* `copper_islands_<board>.json`: BUS_P in 3 components (In1.Cu severed at x = 118, the ladder's BUS_P pad
alone), PGND in 3 (In2.Cu severed at x = 84-91, the sense-region pours 2 mm from the plane), AC_B in 4 (three of J4's
nine press-in lands outside the riser pour), 3V3 in 5. Cross-sections of the filled polygons confirm the cuts.

*Cause.* The DESAT diodes stood in the device row with the cathode at y = 24 mm and the anode at y = 34 mm, exactly
where the switch-node cut-outs already narrow the planes to the band y = 23-40 mm; the 4.0-4.15 mm exclusions of the
two diode pads plus the ceramic vias cut that band to a 0.6 mm sliver. The sense-region PGND pour started at y = 42 mm
(plane edge 40 mm), the ladder region had no BUS_P copper under it, and the AC_B riser covered only J4's centre row.

*Fix.* `desat_y: 32.8` puts the cathode below the ceramic row and the anode at the island top (y = 42.96 mm), so the
diode exclusions leave 4.5 mm of plane below the device pads; the sense-region PGND pour and a BUS_P finger on In1.Cu
start at the plane edge (merged into one polygon each by `copper.merge_zones`); the AC_B riser spans J4's footprint.
Human review item: the 4.5 mm plane necks at the diode columns are narrower than the rest of the laminated planes and
have to be assessed against the DC-link ripple current (R-13).

### 2.8 Router budget and the control board

*Evidence.* Long harness nets (`SDFM_D`, `VSNS_P`, `3V3`) with `expanded: 150001`; the control board routing exceeded
the 32-minute time box without saving.

*Cause.* `max_nodes: 150000` is small for a 2401 x 1201 cell grid with 8-direction moves; the router had no notion of a
time budget and saved only at the very end.

*Fix.* `max_nodes: 400000` on the power boards; `run_plan` accepts `time_budget_s` (nets not routed when the budget
is exceeded are recorded as unresolved with `reason: time_budget`, further order trials and rip-up rounds are skipped,
the board is still pruned, poured, filled and saved) and `checkpoint` (board saved after every stage under
`.aipe/dab/checkpoints/`). `pipeline.py --time-budget` passes the budget through.

### 2.9 Fan-out widths on the control board (preventive)

The ground pins of the 0.65 mm TSSOPs would have been escaped with 0.4 mm tracks (the GND_CTRL width); `GND_CTRL: 0.25`
and `SW5: 0.3` were added to `fanout_widths_mm` of `routing_control.yaml`. Ground pins in fine-pitch rows get exact
stubs with a via at the stub end where it fits (`exact_via_pads`), otherwise the stranded-ground routing applies.

### 2.10 First re-run of the day: the row exits were still sealed - by routing order, not by the fan-out

*Evidence.* With 2.1-2.9 in place (0.6 mm part gap, 1.8 mm reserve) the first re-run removed every DRC error at the
signal-stage checkpoint (0 clearance, 0 hole-clearance violations; refill DRC on a copy of the checkpoint board), but the
power boards still ended with 78 / 75 open connections, now with `expanded: 1-20` at the stub ports of the DWN rows and
of the drivers' 3V3 / gate pins, and the control board - routed to completion for the first time - with 49. Reading the
copper around the sealed ports of the final board shows three mechanisms:

1. Nets routed earlier turned sideways *at their ports* and ran across the neighbouring exits: `PG_BIAS_N` dropped a via at
   its stub end and ran on B.Cu 0.25 mm under the `GNDP_AH` port, `VEE_AH` ran on F.Cu 0.7 mm above the `RLIM`/`FBVEE`/
   `FBVDD` stub ends, `DRV_RSTF` ran under the driver's 3V3 port. Each neighbour was then sealed (`expanded 1-20`).
2. Two nets wider than their stubs cannot coexist side by side in a 0.65 mm row on this grid: the 0.8 mm `12V_BIAS_AH`
   track started at full width 0.875 mm from the `GNDP_AH` (0.6 mm) port, whose dilated foreign halo (0.82 + 0.25 mm) then
   covered the port's whole neighbourhood.
3. With a plain 0.6 mm courtyard gap the drivers' decoupling capacitors formed a wall directly above the HV pin row (0.7
   mm between courtyards); `OUTL_x`, routed before `G_x`, cut diagonally across the gate pin's only exit and no via fitted
   in the 2.3 mm band between pins and capacitors - all four `G_x` nets stayed open at the driver.

*Fix (second re-run).* Every IC pad gets a reserved *exit lane* of its stub width from the stub end (or, for the critical
gate-loop pads, from the land) to 1 mm before the parts (`fanout.exact_lane_pads`, `Router._reserve_lane`; lanes of
routed nets are released before rip-up and all lanes before the final retry, as before). A net wider than its stub ends
beyond the lane ends of its neighbours (`fanout_rows.plan_rows`, `band_mm`), so its full width starts where nothing runs
alongside. The wide row nets are routed first (`signal_first`), the fan-out band in front of the pin rows is 3.0 mm
(2.0 mm on the control board) and applies only to the sides that carry pad rows, and the module input rails
`12V_BIAS_x` / `GNDP_x` are routed at 0.5 mm instead of 0.8 / 0.6 mm (the UCC14141 input is below 0.5 A average; 0.5 mm
at 70 um carries about 2.5 A; the 0.65 mm row cannot host wider parallel exits - a width choice, not a clearance). The
control board's fine-pitch threshold covers its 0.8 mm card socket and 0.95 mm SOT-23 rows (`fine_pitch_mm: 1.0`) and its
search budget was raised to 800 000 nodes for the harness-to-card paths that ran dry.

## 3. What was not changed

No clearance, hole clearance, edge clearance or insulation value was reduced; no DRC rule was waived or disabled; the
`.kicad_dru` files, net classes and the IEC 60664-1 reference table are unchanged. Track widths were not reduced
(the stubs were always narrower than the nets). The sic-buck examples are not regenerated by these changes; their
tests pass unchanged (`python -m pytest`).

## 4. Results after the remediation (committed boards, kicad-cli 10.0.6, `--schematic-parity --severity-all --refill-zones`)

| Board | ERC | DRC errors (other than unconnected) | DRC warnings | Unconnected items (nets) | Parity | Router | Pour nets single island |
|---|---|---|---|---|---|---|---|
| primary-power | 0 | **0** (was 22) | 18 `track_dangling` (was 35) | **26 in 18 nets** (was 82 in 42) | 0 | 2501 tracks, 436 vias, 22 pours, 26 open, 1161 s | yes (9/9; was 3 split) |
| secondary-power | 0 | **0** (was 2) | 18 `track_dangling` (was 35) | **23 in 16 nets** (was 81 in 42) | 0 | 2598 tracks, 449 vias, 21 pours, 23 open, 1189 s | yes (8/8; was 3 split) |
| control | 0 | **0** (was 0, nothing routed) | 28 `track_dangling` (was 0) | **24 in 23 nets** (was 499, never routed) | 0 | 3090 tracks, 622 vias, 1 pour, 24 open (22 route, 2 stranded ground), 2714 s - 45 min budget reached after one signal trial | no (3V3 in 2, GND_CTRL in 3 pieces: the open connections) |

Report ids, SHA-256 values and the per-net lists are in `examples/dab-10kw/verification/summary_<board>.json` and
`docs/dab-10kw/review-report.md` (sections 3, 7 and 8). Barrier geometry of the power boards:
`verification/engineering_checks/barrier_geometry_<board>.json` - 8.0 mm HV-to-SELV on every copper layer and 8.0 mm
across the stack (the Hall sensor's own land gap is the minimum).

Open connections that remain, both power boards: the narrow nets of the UCC14141 rows (`BIAS_ENF` at all five modules,
`PG_BIAS_N`, `FBVEE_x`, `FBVDD_x`, `VEEA_x`, `RLIM_x`, `S_RLIM`), the drivers' `VEE_AH`/`VEE_BL` pin 8 into the islands
and `KS_BL`/`S_16V` on the primary. Mechanism (routing reports, `expanded` 24-37 at the stub ports): the exit lanes end
1 mm before the parts, the wide nets routed first turn sideways there at full width, and the narrow nets' first cell
beyond their lane end is inside that track's halo. The next step is an ordered row escape (river routing: staircase
lane ends per turning direction, or a staggered via field beyond the band), not another parameter change.

## 5. Iteration record (same day)

| Run | Change set | primary open / DRC errors | secondary open / DRC errors | control open |
|---|---|---|---|---|
| main 2de2ae5 | - | 79 / 22 | 80 / 2 | not routed (499 unconnected) |
| 1 | 2.1-2.9 (stubs, net tie, rows, stranded ground, 0.6 mm gap, planes, budget) | 78 / 0 | 75 / 0 | 49 |
| 2 | 2.10 (exit lanes, fan-out band 3.0 mm, wide-first, 0.5 mm module rails, no-via-in-pad off) | 29 / 0 | 24 / 0 | 22 (budget) |
| 3 | ground pins of coarse rows on the via escape, pour-net pads not skipped, stranded ground stubs, 800k nodes | 26 / 0 | 23 / 0 | 24 (budget reached) |
| 4 | AC_B riser capped at the Hall bars (geometry only; routing identical) | 26 / 0 | 23 / 0 | - |
