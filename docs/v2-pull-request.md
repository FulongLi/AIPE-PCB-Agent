# AIPE-PCB-Agent V2 — Knowledge-Driven 5kW SiC Buck

This adds the second benchmark of the repository: a 400 V (360-440 V) to 200 V, 5 kW,
25 A, 50 kHz SiC synchronous buck designed with the AIPE Engineering Knowledge System
(V0: 6 skills, 43 rules, 13 circuit blocks, 19 component records). It consists of a
240 x 180 mm four-layer power board (two Wolfspeed C4MS025120K TO-247-4 devices,
UCC21710-Q1 isolated drivers with UCC14141-Q1 bias modules, a custom 272 uH High Flux
toroid, TMCS1133 and AMC1311 isolated sensing) and a 120 x 80 mm TMS320F28335 control
board stacked on the power board's SELV strip through a 2 x 25 mezzanine. The example
`examples/sic-buck-400v-200v-5kw/` (EX below) carries the design record (baseline with
26 conflict resolutions, 19 calculation invariants, 65 component records, a magnetic
record), 22 ERC-clean schematic sheets, 20 behavioural ngspice runs, both routed boards
at zero native DRC findings with schematic parity and all severities, hashed
manufacturing exports, an independent rule-by-rule layout review with a measured
correction pass, and a knowledge-utilisation audit of 24 decisions. V1
(`examples/buck-48v-24v-1kw`) is frozen and untouched.

**AI-GENERATED ENGINEERING PROTOTYPE V2 - HUMAN REVIEW REQUIRED**

Target: `feat/sic-buck-5kw-v2` (fork `MrCoconut616/AIPE-PCB-Agent`) -> `main` in
`FulongLi/AIPE-PCB-Agent`. The PR is not merged automatically and must not be merged
without human engineering review. This file is the prepared PR body; it is not evidence
that a remote PR exists. Every number below names its source file. All sources are in EX
except the knowledge-base counts (`knowledge/README.md`, repeated in EX
`review/knowledge_utilisation_report.md` section 1) and the unit-test result, whose run log
is kept outside the repository (`docs/status-v2.md`).

## Engineering design summary

| Item | Value | Source |
|---|---|---|
| Requirement | 400 V nominal -> 200 V, 5 kW, 25 A, 50 kHz, non-isolated synchronous buck, Wolfspeed SiC, TMS320F28335, KiCad | EX `input/requirements.yaml` |
| Accepted assumptions | 360-440 V operating, 460 V input OVP, 480 V / 100 ms survival, 27.5 A for 10 s, 12.5 A load step <= 10 V / 5 ms, 50 C ambient, T_J limit 150 C (125 C preferred), 98.0 % target / 97.5 % floor | EX `design/design_decisions.json` `assumptions_accepted`; `design/assumptions.md` |
| Inductor ripple | 7.3 App at 400 V (about 30 %), 8.7 App at 440 V worst | `design_decisions.json` `magnetics.inductor` |
| Power stage | 2 x C4MS025120K (HS, LS), +15 V / -4 V gate rails, R_G 10 ohm on (6.8 ohm tuning target) / 3.3 ohm off, DESAT 3.6 V / 288 ns blanking, active Miller clamp required | `design_decisions.json` `power_stage` |
| Bias | 3 x UCC14141QDWNRQ1 (HS gate, LS gate, sensing island), 19.0 V / 4.0 V gate channels, 15.0 V / 5.0 V sensing channel | `design_decisions.json` `power_stage.bias_supply` |
| Magnetics | custom 2 x Magnetics 0058192A2 High Flux stacked, 34 T AWG 10, 319 uH at 0 A / 272 uH at 25 A | EX `components/magnetic_record.json`; `design/component_selection.md` section 4 |
| DC link | 2 x TDK B32776G8206K000 20 uF 800 V film + 10 x CGA9P1X7T2J474M250KC 0.47 uF 630 V 2220; output 2 x B32776G4606K000 60 uF 450 V | `design_decisions.json` `capacitors` |
| Sensing and protection | TMCS1133 (0.05 V/A, OC 37.5 A), 2 x AMC1311B with HV ladders, OPA2320 conditioning, heatsink NTC with 80 / 90 / 100 C ladder, SN74LV21A fault combiner, SN74LVC1G74 latch, TPS26400 eFuse | `design_decisions.json` `sensing`, `protection`, `controller` |
| Boards | power 240 x 180 mm, 4 x 70 um, 2.0 mm; control 120 x 80 mm, 4 x 35 um, 1.6 mm; HV-to-SELV 9.0 mm on all layers, HV-to-PE 5.0 mm, functional 3.0 / 1.0 mm, 1.2 mm slots under eight barrier parts | EX `design/pcb_stackup.md` sections 1-5 |
| Efficiency budget (analytical) | converter 98.70 % typical expected, 98.27 % bounded worst; with aux electronics 98.55 % / 98.12 % | EX `design/calculations.md` section 12 |

## Circuit verification

Calculation record (EX `design/calculations.md` section 13, `calculations.json`): 19
invariants asserted by `automation/scripts/calculate_sic_buck`, all PASS. Examples:
T_J,HS 143.1 C < 150 C at every corner including max-R and k_RG 2.0 (`calculations.md`
section 9: 360 V / 27.5 A, max-R, k_RG 2.0, the upper bound of the k_RG range in which the
10 ohm bring-up resistor reads 1.9; the thermal table below uses k_RG 1.3 and gives 129.8 C
for the same corner); voltage utilisation
0.508 < 0.80 (worst 60 nH, 460 V); 12.5 A load step 9.23 V <= 10 V; load dump 220.3 V <
230 V OVP; DESAT response 1.066 us <= 1.5 us; OC trip lower bound 33.7 A > 32.0 A worst
overload peak; typical efficiency including aux 98.5 % >= 98.0 %, bounded worst 98.1 % >=
97.5 %.

Simulation (EX `simulation/simulation_report.md` sections 1, 10 and 12): 20 ngspice-46
transient runs plus 4 parasitic cases, behavioural switches, no SiC device physics.

| Quantity (400 V / 25 A unless stated) | Simulated | Reference / limit | Status |
|---|---|---|---|
| Inductor ripple at 360 / 400 / 440 V | 6.51 / 7.35 / 8.03 App | 6.5 / 7.3 / 8.0 App analytical | agrees within 1 % |
| Output ripple | 0.16-0.22 Vpp | <= 2.0 Vpp | pass |
| Input bus ripple | 3.56-3.97 Vpp | <= 8 Vpp (2 %) | pass |
| C_in RMS per film part | 6.4-7.1 A | 14.5 A rating | pass |
| 12.5 A load step, cascaded controller | -7.74 / +7.80 V, recovery 0.75-0.77 ms | <= 10 V, <= 5 ms | pass |
| 25 A -> 0 A dump | peak 216.2 V | < 230 V OVP | pass |
| Single-loop PI reference | -16.2 V, 5.0 ms, I_L 38.5 A | 10 V / 5 ms / 37.5 A OC | fails: inner current loop required |

Not verified by simulation: switching losses and efficiency, absolute switch-node
overshoot and dv/dt, gate behaviour, DESAT / OC / OVP action, thermal limits, EMI,
anything depending on firmware (none exists). ERC: 0 findings on both projects. Netlist:
exact pad-net match between model, schematic and board, 648 pads / 101 nets (power) and
667 / 111 (control) (EX `verification/netlist_check_{power,control}.json`).

## Chosen architecture

Option B, separate power PCB and all-SELV control PCB, selected by weighted scoring
A 2.75 / B 4.00 / C 3.10; B leads every sensitivity set by at least 0.37 (EX
`review/architecture_comparison.md` section 5). All eight barrier parts (3 x UCC14141,
2 x UCC21710, 2 x AMC1311, TMCS1133) sit on one straight barrier line on the power
board, so the control board carries no hazardous voltage (EX `design/architecture.md`
sections 1 and 3). Measured on the delivered power board (EX
`verification/engineering_checks/layout_metrics_power.md`): minimum HV-to-SELV copper
distance 9.486 / 11.100 / 11.100 / 12.025 mm on F.Cu / In1 / In2 / B.Cu against the 9.0 mm
rule; the 10 mm ISO_BARRIER strip is copper-free on all four layers; the eight slots are
1.2 mm wide with around-the-end surface paths of 9.807-11.119 mm (land gaps 7.25-9.1 mm);
HV-to-PE 5.0 mm on every layer. The control board's J8 mates power-board J7 with 0.00 mm
error, but the 80 mm deep control board overhangs the 30 mm SELV strip by 54 mm and two
of its four standoffs land beyond the power-board edge (LR-27, open).

## Selected SiC MOSFET

Wolfspeed C4MS025120K, TO-247-4 with Kelvin source, two devices (EX
`design/component_selection.md` section 2; `design_decisions.json` `power_stage.mosfet`):
1200 V class, R_DS(on) 28 mohm typical at V_GS 15 V (48.5 mohm at 150 C interpolated,
57.2 mohm "max-R" scaled), Q_G 125 nC, E_on / E_off 470 / 64 uJ at 800 V / 39.2 A, R_thJC
0.41 K/W typical with no published maximum. Voltage utilisation 42-46 % at 440 V with a
62-88 V overshoot allowance for 25-35 nH at 2.5 A/ns (49 % even at 150 V overshoot);
a 650 V device would sit at 77-84 %. Losses per pair 46.7-52 W at 400 V / 25 A / 150 C.
Rejected: C3M0015065K (650 V), the obsolete C3M0030090K cited by the knowledge base,
C4MS018120K (no stock found). Fallback with the same footprint and rails: C3M0021120K
(+8 W). Open: stock at Arrow only with a 13-week lead elsewhere; no short-circuit
withstand time is published, so KR-PR-001 is closed only by a destructive test.

## Gate-driver design

UCC21710QDWRQ1 per device (EX `design/component_selection.md` section 3): 5.7 kVrms,
VIOWM 2121 VDC, CMTI > 150 V/ns against a computed 110-122 V/ns turn-off edge (1.25x on
the peak edge; double-pulse measurement mandatory), split outputs, DESAT pin with
external blanking, soft turn-off, RDY / FLT. Rails +15.0 V / -4.0 V from one
UCC14141QDWNRQ1 per position (19.0 V VDD-VEE, 4.0 V COM-VEE, 0.1 % dividers); the
negative rail is kept because the charge-based parasitic turn-on estimate reaches
+0.5 to +1.2 V from -4 V against V_GS(th) min 2.0 V, which also makes the Miller clamp
REQUIRED (0 ohm link <= 15 mm from the gate pin). R_G 10 ohm on at bring-up with a
6.8 ohm tuning target and 3.3 ohm off (1.26 A / 3.06 A against +/-10 A). DESAT: trip
V_DS 3.6 V, external blanking 288 ns, total response 0.55-1.07 us against the 1.5 us
budget. Hardware interlock by cross-wired IN+ / IN-; dead time 300 ns programmed at
bring-up (>= 265 ns after erosion), 250 ns target. A third UCC14141-Q1 feeds the sensing
island (CR-12): the TIDA-010054 pattern of sharing the LS gate rail failed the COM-VEE
RLIM sink check. As built (EX `verification/engineering_checks/layout_metrics_power.md`):
driver output pad to gate pad 14.353 mm (U1 -> Q1) and 14.360 mm (U3 -> Q2) against
<= 15 mm; HS gate net G_H 26.4 mm with 0 vias, LS gate net G_L 33.1 mm with 7 vias and
R41 / TP2 over the SW pour (LR-24, open).

## Magnetic and capacitor selection

Inductor L1 (EX `design/component_selection.md` section 4; `components/magnetic_record.json`):
custom toroid, 2 x Magnetics 0058192A2 High Flux 60u stacked, 34 turns AWG 10 heavy
build, potted cup about 72 x 46 mm, 632 g bare. L 319 uH at 0 A, 272 uH at 25 A, 210 uH
at 41 A nominal (175 uH worst); soft-saturation criterion L(41 A) / L(25 A) 0.765 nominal
and 0.743 worst against >= 0.70; vendor-style I_sat (30 % drop) 37.3 A nominal / about
35 A worst against the 37.5 A OC trip, accepted in CR-05 with the 3-stack fallback. DCR
12.2 / 16.0 mohm at 20 / 100 C; losses 16.4 W at 400 V / 25 A typical, 23-26 W bounded;
still-air hot spot 110-120 C, so forced air over the cup is required. No standard part
exists for 220-300 uH at 25-32 A (13 families searched).

Capacitors (section 5): input 2 x TDK B32776G8206K000 20 uF 800 V film, 6.92 A each
worst against 14.5 A, 0.55-0.60 of V_R, 3.9 Vpp bus ripple at 27.5 A; HF tier 10 x TDK
CGA9P1X7T2J474M250KC 0.47 uF 630 V X7T 2220 with 1.88 uF effective assumed (60 % DC-bias
loss, curve not fetched - open); output 2 x B32776G4606K000 60 uF 450 V film, 1.43 A each
against 23.5 A, step 7.4-9.2 V, load dump 214.8-218.5 V below the 230 V OVP; bleeders
3 x 120 k and 2 x 100 k 2512 discharge both banks below 60 V in 36.5 s (20.3 s with the
indicator chains). DNP positions: RC snubber across the LS device, 1 uF + 0.47 ohm
damping leg, MOV, PGND-to-PE link.

## Thermal analysis

Lumped steady-state arithmetic, no CFD, no measurement (EX `design/thermal_analysis.md`).
Shared PE-bonded Fischer LAM 5 D K 100 12 sink, 0.30 K/W forced (distributor-level
figure; the Fischer datasheet was not accessible), Bergquist Sil-Pad TSP A2000 0.254 mm
pads, design R_pad 1.4 K/W, R_pad + R_JC 1.81 K/W per device.

| Corner | P_tot (W) | T_sink (C) | T_J,HS (C) | Source |
|---|---|---|---|---|
| 400 V / 25 A, typical | 46.8 | 64.0 | 109.4 | `thermal_analysis.md` section 3 |
| 360 V / 27.5 A, max-R (HS hottest) | 60.2 | 68.1 | 129.8 | section 3 |
| 440 V / 27.5 A, max-R | 62.9 | 68.9 | 126.3 | section 3 |
| KR-TH-001 P_max per device at 150 C | 41.5 W against 34.1 W (margin 1.22) | | | section 3 |

The 125 C preference holds with typical parts at 25 A but not at the max-R overload
corner; stacked pessimistic assumptions reach about 158 C during the 10 s overload
(section 3 sensitivities). Fan failure gives T_J above 175 C at any natural-convection
estimate, so the OTP ladder (80 C derate, 90 C firmware trip, 100 C hardware trip,
CR-25) is mandatory. Copper by IPC-2221 at 70 um and 20 K: 25 A needs 8.4 mm outer /
21.7 mm inner width (section 7). Measured on the stored fills after the correction pass
(EX `verification/optimisation_before_after.md`, pass 2): input return PGND J2 -> Q2.2
neck 24.22 mm on In1 (was 4.56 mm), SW via group -> L1.1 18.48 mm on In2 (was 5.22 mm),
VIN J6 -> Q1.1 8.87 mm on In2, VOUT C13.1 -> J3 22.85 mm on In2 and 15.83 mm on F.Cu.
Courtyard distance to the sink: input films C11 / C12 20.06 mm, L1 18.31 mm against the
20 mm placement rule (LR-25, partly applied).

## PCB images

Renders exported by `kicad-cli` from the delivered board files (EX
`manufacturing/*/export-manifest.json`; copies under EX `review/`). They show the stored
zone fills, which for both boards are the rule-aware copper the DRC judged (stored-fill
check 0 / 0, see the next section). The links point at the pushed branch
`feat/sic-buck-5kw-v2` of `MrCoconut616/AIPE-PCB-Agent`; the files are EX
`review/pcb_{front,back,3d}_{power,control}.png`.

Power board, 240 x 180 mm, front:

![Power board front](https://raw.githubusercontent.com/MrCoconut616/AIPE-PCB-Agent/feat/sic-buck-5kw-v2/examples/sic-buck-400v-200v-5kw/review/pcb_front_power.png)

Power board, back:

![Power board back](https://raw.githubusercontent.com/MrCoconut616/AIPE-PCB-Agent/feat/sic-buck-5kw-v2/examples/sic-buck-400v-200v-5kw/review/pcb_back_power.png)

Power board, 3D (STEP models of the WE-SL2 chokes L2-L4 are missing from the library bundle, LR-35):

![Power board 3D](https://raw.githubusercontent.com/MrCoconut616/AIPE-PCB-Agent/feat/sic-buck-5kw-v2/examples/sic-buck-400v-200v-5kw/review/pcb_3d_power.png)

Control board, 120 x 80 mm, front:

![Control board front](https://raw.githubusercontent.com/MrCoconut616/AIPE-PCB-Agent/feat/sic-buck-5kw-v2/examples/sic-buck-400v-200v-5kw/review/pcb_front_control.png)

Control board, back (mezzanine header J8 on B.Cu):

![Control board back](https://raw.githubusercontent.com/MrCoconut616/AIPE-PCB-Agent/feat/sic-buck-5kw-v2/examples/sic-buck-400v-200v-5kw/review/pcb_back_control.png)

Control board, 3D (models of U1, U3 and Y1 missing, LR-35):

![Control board 3D](https://raw.githubusercontent.com/MrCoconut616/AIPE-PCB-Agent/feat/sic-buck-5kw-v2/examples/sic-buck-400v-200v-5kw/review/pcb_3d_control.png)

Layer-by-layer PDFs: EX `review/pcb_layout_power.pdf` (A3, six pages) and
`review/pcb_layout_control.pdf`; schematics: EX `review/schematic_power.pdf`,
`review/schematic_control.pdf`.

## ERC/DRC results

All runs by `kicad-cli` 10.0.7 (`kicad_version` in each `erc.json` / `drc.json`) through
`automation.kicad_tools.run_check`, which hashes the source, every dependency and the
report. DRC options: `--schematic-parity --severity-all --refill-zones`. The stored-fill
check is a diagnostic DRC of the saved zone fills WITHOUT `--refill-zones` on a scratch
copy (EX `verification/engineering_checks/stored_zone_fill_check_{power,control}.json`).

| Board | Check | Run id (EX `verification/...`) | Result | Source sha256 (first 16) | Stored-fill check |
|---|---|---|---|---|---|
| Power | ERC | `erc/20261010T165532Z-erc-02a2619f` | 0 findings, 12 sheets | `2bd65b021c8fb3b4` (root schematic) | - |
| Control | ERC | `erc/20261010T071810Z-erc-b207ac59` | 0 findings | `b3a08ddc99227c05` (root schematic) | - |
| Power | DRC | `drc/20261011T054445Z-drc-d0914d79` | 0 violations / 0 unconnected / 0 schematic-parity | `b1bb5698194b9aea` | 0 violations / 0 unconnected |
| Control | DRC | `drc/20261011T051246Z-drc-f801ed3c` | 0 / 0 / 0 | `dead06ed18d85154` | 0 / 0 |

51 DRC manifests are kept under EX `verification/drc/`, failed iterations included; the
two most recent failures are part of the record: `20261011T053341Z-drc-ba043c49`
(power build r20c with the LR-24 / LR-26 layer restrictions, 8 violations / 10
unconnected, reverted) and `20261011T051014Z-drc-b9164471` (control LR-32 attempt,
0 / 1 / 0, reverted). The example verifier (`python -m automation.scripts.verify_sic_buck`
-> EX `verification/verification-summary.json`) reports `status: passed` with an empty
problem list; its scope is "CAD connectivity, native check currency and export integrity
only; hardware unqualified". The control ERC manifest predates the report-hash field
(`report_hash_checked: false` in the summary). Layout metrics against review thresholds
(EX `verification/engineering_checks/layout_metrics_{power,control}.md`): power 58 rows,
27 within / 6 exceeding / 25 measured without threshold; control 31 rows, 2 within /
2 exceeding / 17 measured without threshold / 10 not measured. The exceeding rows are
review items, listed under Known limitations.

## Knowledge utilisation report

EX `review/knowledge_utilisation_report.md` audits 24 decisions (section 3) and
condenses to these indicators (section 7):

| Indicator | Value |
|---|---|
| Significant decisions audited | 24 |
| Decisions where a knowledge item set the method or a value | 22 of 24 (magnetics D-11 and precharge / fuse / relay D-23 had no applicable item) |
| Decisions where a human-review rule was surfaced instead of decided | 10 |
| Design errors the knowledge prevented or exposed before verification | at least 9 (negative turn-off rail, no copied DESAT values, gate-discharge resistor, interlock, latched fault with UVLO lock-out, hardware OC path, bias sharing flagged -> CR-12, slots under barrier parts, NTC not treated as T_J) |
| Knowledge misapplications caught by the verifiers | 30, of which 12 changed a value, requirement or part and 5 were label-only |
| Knowledge found wrong, stale or incomplete | 9 (obsolete C3M0030090K, discontinued CR201-50VE / CLA-TO-21E, TMCS1133 orderable, UCC14141 rating conditions, TPS2640 threshold, CB-PR-002 polarity, RECOM insulation grade, CGD1700 board size, PE-PCB rules not indexed) |
| Retrieval and citation coverage | 91 query entries (74 searches, 11 `--get` reads, 6 direct reads), 317 citation rows over 96 ids; 273 labelled rows: 41.8 % direct, 37.0 % adapted, 12.8 % not applicable, 8.4 % human review (sections 1 and 2.2) |
| Validation status of cited items | reference-derived or analytically-checked only; nothing simulation-verified or hardware-validated |

The report's judgement (section 7): "The honest conclusion is conditional: the knowledge
improved the design *together with* independent verification; alone it would have
improved the questions asked and degraded a few answers." Its 25 knowledge-base proposals
(section 6) and the PCB-phase proposals are collected in `docs/knowledge-feedback-v2.md`;
nothing under `knowledge/` was changed by V2.

## Known limitations

Nothing in this PR is fabricated, energised, measured or validated; CAD completeness
with zero native findings is not engineering validation. The PR must not be merged
without human engineering review. The full register is EX `verification/known_issues.md`
(49 rows V2-01..V2-49); the bullets below condense it and its sources
(`layout_review_findings.json`, `optimisation_finding_status_pass2.json`,
`review/knowledge_utilisation_report.md` section 8.2, `design/design_decisions.json`
`open_items_for_human_review`):

- LR-22 (should-fix, open): all ten HF ceramics sit west of Q1; Q2 source pad to the
  nearest same-net HF pad is 41.2 mm against the 15 mm review threshold and the F.Cu VIN
  neck narrows to 2.35 mm after the rule-aware refill; the review's board-loop estimate
  is 6-8 nH, the simulation requires L_loop <= 36 nH in total at 2.5 A/ns while standing
  TO-247 leads alone add 40-60 nH.
- LR-24 (should-fix, open): LS gate loop G_L 33.1 mm with 7 vias and 84 mm of
  gate-network copper against 40 mm on the HS side; R41 / TP2 over the SW In2 pour; a
  B.Cu-only attempt (build r20c) left 9 connections open and was reverted.
- LR-26 (should-fix, open): AMC1311 output pairs routed on different layers
  (VIN_OUTP In2 / VIN_OUTN F.Cu, VOUT_OUTP B.Cu / VOUT_OUTN In2); ISENSE 84 mm with
  7 vias on the power board.
- LR-27 (should-fix, open, mechanical): the control board overhangs the power board by
  54 mm; two of four standoffs need a bracket or a redesigned depth.
- LR-32 / LR-33 (should-fix, open, control board): DSP_TRIP_N 224.4 mm / 21 vias,
  FAULT_N 319.7 mm / 16 vias, ESTOP_N 403 mm / 24 vias; ADC 1 nF filter capacitors
  6.9-14.8 mm from the DSP pins; sense pairs split (ISENSE 122.2 mm vs ISENSE_REF 54.5 mm).
- LR-25 (partly applied): L1 at 18.31 mm courtyard distance from the sink against the
  20 mm rule; RT1 stays 9.51 mm from the sink in the intake corridor; fan-intake face
  unconfirmed.
- LR-28 (partly applied) / V2-03, V2-04, V2-05 (`verification/known_issues.md`): the 25 A
  switch-node current runs on In2 only through an 18.48 mm neck against the 21.7 mm inner
  width by IPC-2221 at 20 K (`design/thermal_analysis.md` section 7; 21.8 mm by the review's
  figure in V2-03); the input PGND return J2 -> Q2.2 is a single 24.22 mm In1 neck with
  0.0 mm B.Cu return copper against the baseline's paralleled 12 mm outer / 22 mm inner;
  VOUT_L is F.Cu only, 4.8 mm wide at the TMCS1133 pins (review estimate 50 K). Thermal
  acceptance or widening before fabrication.
- Mechanical and assembly (V2-08, V2-13): the four HS1 heatsink mounting holes are
  placeholders (`components/bom.csv` HS1 note; the real hole pattern is unknown until the
  Fischer drawing is obtained); no assembly drawing exists, and lead forming or spacer,
  clips, insulating pad, fasteners and PE bond are not specified.
- Layout metric rows still exceeding their thresholds: PE-PCB-002 (41.2 mm above),
  PE-PCB-006 VIN_RAW / VOUT_L with 0 vias (THT-joined pours, checker limitation LR-30),
  KR-ISO-002 VIN-PGND and VOUT-PGND 1.95 mm on F.Cu inside the R6 / R10 pin fields
  (per-footprint exceptions, LR-31), KR-TH-002 B.Cu copper of the PE-reference link
  column inside the heatsink courtyard (LR-29) and HF row-A pads 4.955 mm from it;
  control-board DSP bypass pairs up to 5.38 mm against the 5.0 mm proxy.
- Insulation coordination is a human-review item throughout: 4 kV versus 2.5 kV impulse
  basis, 9.0 mm rule versus the 5.5 mm standard minimum, barrier land gaps 7.25-9.1 mm
  below the board rule, pin-field exceptions of 0.9-2.7 mm outer copper, stacked-board
  clearance, pad rating and relay coil-to-contact insulation; standard values were read
  from secondary sources, not a licensed copy.
- Short-circuit protection: DESAT 0.55-1.07 us against an unpublished C4MS025120K
  withstand time; closure requires a destructive test. Off-state V_GS with the clamp,
  R_G sweep, CMTI margin and UCC14141-Q1 RLIM / SOA / certification are unverified.
- Thermal: about 130 C junction at the 360 V / 27.5 A max-R corner versus the 125 C
  preference; R_pad 1.4 K/W and R_th,HS 0.30 K/W are design values to be measured; the
  Fischer datasheet and fan current are unavailable; no CFD.
- Controller: the simulation shows an inner current loop is required; stand-in gains,
  no sampling effects, no firmware exists (`design/firmware_interface.md` is a contract
  only); load-dump reverse-current policy against the 460 V input OVP is open.
- Components: C4MS025120K stock Arrow-only with a 13-week lead elsewhere; TDK CGA9P
  DC-bias curve not fetched; custom inductor winding house, core orderable code and
  potting cup unresolved; several ratings at distributor level (Samtec, G9EA-1, KLKD
  I2t, SMBJ15CA, AO3400A, US1M, BAT42W).
- Simulation scope: behavioural model, ideal switches, no device physics, no switching
  loss, no EMI, no thermal coupling, idealised continuous-time control.
- Exports: STEP models missing for L2-L4 (power) and U1 / U3 / Y1 (control); 3V3 versus
  +3V3_PWRBOARD net naming across the mezzanine (LR-34); no fabricator DFM review exists.
- Reproducibility: the control board was routed with `grid_router.py` at sha256
  `b78a49cc...`; the shared module changed during power-board convergence (now
  `c666ba73...`). A scratch regeneration with the current module (EX
  `verification/engineering_checks/control_regeneration_check.json`, diagnostic)
  reproduced every track, via, footprint and zone (5995 / 798 / 207 / 20, 0 items in only
  one board) with 0 unresolved connections; file hashes differ through uuids and
  timestamps only. Byte-identical files across KiCad or module versions are not promised.
- The release was frozen after the reports were finalised: `automation/scripts/freeze_v2.py`
  (verifier re-run first) wrote `examples/sic-buck-400v-200v-5kw/releases/v2/` (868 files, `SHA256SUMS.json` with `source_commit` `f72052fb53aa70163fad21294c36379d3921aec0`, label "AI-GENERATED ENGINEERING PROTOTYPE V2 - HUMAN REVIEW REQUIRED", created 2026-10-11T07:10 UTC) and `releases/v2-review-package.zip` (32,070,559 bytes). The snapshot must never be edited;
  `docs/status-v2.md` records the freeze and the GitHub hand-off.

## How to review and reproduce

Read-only checks from the repository root (host Python 3.10; `verify_sic_buck` only
reads):

```text
PYTHONIOENCODING=utf-8 python -m automation.scripts.verify_sic_buck
python -m unittest discover -s tests
python -m automation.knowledge.query --get KR-ISO-004 --json
```

Expected: `verification/verification-summary.json` with `status: passed`; "Ran 253
tests ... OK (skipped=2)" (re-run 2026-10-11). Review order: `docs/status-v2.md`, then in
EX `review/design_report.md` (14 sections) and `verification/known_issues.md` (49 rows
V2-01..V2-49 grouped before fabrication / before energisation / before design release /
documentation and tooling), `review/knowledge_utilisation_report.md`,
`verification/pcb_rule_review.md` with `layout_review_findings.json` and
`optimisation_before_after.md`, the schematic and layout PDFs under `review/`, and
`design/design_decisions.json` as the single source of truth. Regeneration commands,
the real generator options and the caveats (regeneration writes new placement /
routing-progress files and a new DRC manifest into the example; shared-router change;
floorplan-candidate amendment) are in `docs/reproduce-v2.md`. The frozen snapshot is EX
`releases/v2/` (`README.md`, `SHA256SUMS.json`, 868 files, source commit `f72052f`) with the
portable `releases/v2-review-package.zip`; the example directory on this branch is the same
content plus the refreshed `review/v1_v2_comparison.*`. Nothing here authorises
fabrication, purchase or energisation.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
