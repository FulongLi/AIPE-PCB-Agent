**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# V1 (48 V -> 24 V / 1 kW Si buck) versus V2 (400 V -> 200 V / 5 kW SiC buck): process, knowledge, verification and layout comparison

Generated 2026-10-11T07:11:18.899919+00:00 by `python -m automation.scripts.compare_v1_v2`. Machine-readable twin: `v1_v2_comparison.json`. V1 sources are the frozen files under `examples/buck-48v-24v-1kw/` (read-only); V2 sources are under `examples/sic-buck-400v-200v-5kw/`. 0 V2 metrics are marked 'not yet available' because the PCB phase is running; re-run the script after placement, routing, DRC, layout metrics, exports and release exist to complete the tables.

## 0. How to read this comparison

- Raw PCB area, component density and specific power do not prove that either generation is better engineered: V2 carries 5x the power at 8x the voltage with an isolation barrier that V1 never needed, so most density ratios are specification effects (table 1).
- V2 layout, DRC, placement, export and release metrics are produced by a concurrent PCB phase; every such entry is marked 'not yet available' and the script must be re-run to complete the tables.
- Counts of files, rows, words, citations, tests and runs measure process coverage, not engineering correctness; a verified-with-corrections record can still contain a wrong number that both lenses missed.
- All thermal and efficiency figures of both generations are lumped analytical estimates; the V2 simulation is a behavioural ngspice model without SiC device physics, switching loss or firmware. Nothing in either generation is measured on hardware.
- V1 is frozen and read-only; this comparison never alters it, and its known issues remain the authoritative V1 review state.

Basis of every value: measured = CAD/simulation tool output; counted = counted from repository files; documented = stated in a design document; planned = design target not yet measured; derived = computed here; not yet available = source file missing.

## 1. Specification-driven differences (explain metric differences; not improvements)

These differences are fixed by the task. They change parts, spacing, copper and board count before any process quality enters. Read every row of tables 3 and 4 against this table first.

| Quantity | V1 | V2 | Effect on the metrics below (not an improvement) |
|---|---|---|---|
| Nominal input voltage | 48 V (36-54 V assumed range) | 400 V (360-440 V operating) | 8.3x higher voltage forces reinforced isolation, 9 mm HV-to-SELV spacing, copper-free barrier strips and 1200 V-class parts; it enlarges the HV area and lowers the achievable component density |
| Output voltage | 24 V | 200 V (hazardous, insulated like the input) | the output is a hazardous voltage in V2: isolated output sensing, bleeders and discharge-time requirements appear that V1 did not need |
| Output power | 1000 W | 5000 W | 5x power raises W/dm2 and W/L arithmetically; the specific-power ratio between generations is therefore mostly specification, not layout skill |
| Output current | 41.67 A | 25 A | V1 carries 1.7x more current at low voltage: heavy copper on six layers, 2 mohm shunt and M5 terminals were current-driven; V2 copper is sized for 25 A |
| Switching frequency | 100 kHz | 50 kHz | half the frequency with 8x the volt-seconds: a 27x larger inductance (custom 272 uH choke, 632 g) and film DC-link capacitors replace the 10 uH part and electrolytic bank |
| Semiconductor class | 4 x CSD19536KCS (100 V VDS; +/-20 V VGS, Package_TO_SOT_THT:TO-220-3_Vertical) | 2 x C4MS025120K (1200 V class, TO-247-4 Kelvin source) | SiC allows two devices instead of four paralleled Si parts; fewer power footprints and a shorter commutation cell are a technology effect, not a layout-process result |
| Gate drive | UCC27211DDAR: none (bootstrap half-bridge driver) | UCC21710QDWRQ1: isolated (5.7 kVrms, VIORM 2121 Vpk, VIOWM 1500 Vrms / 2121 VDC ...); bias 3 (HS gate, LS gate, sensing island) x UCC14141QDWNRQ1 | isolated drivers and three isolated bias modules add parts, barrier slots and decoupling islands; part count and BOM rows grow for safety reasons |
| Current sensing | INA240A1DR: 2 mohm shunt + INA240 (non-isolated Kelvin shunt) | TMCS1133C2AQDVGR: isolated Hall sensor in the inductor output path | isolated sensing removes the shunt loss and Kelvin-matching issue of V1 but adds an isolated supply and reinforced-isolation footprint |
| Isolation concept | 48 V SELV-class system on one board; no reinforced isolation barrier, no isolated gate bias, no isolated sensing | control electronics are a SELV domain; the single-point SGND-to-PE bond (PELV) is a PROPOSED DEVIATION from the SELV seed that the human reviewer must approve ... | KiCad spacing rules (HV to SELV (all layers) 9; barrier strip 10; HV to PE 5; HV functional outer/inner 3 x 1 mm) exist only in V2; any V2 clearance or barrier metric has no V1 counterpart |
| Board architecture | integrated_power_and_control_board (1 board) | option B: separate power PCB and DSP control PCB; drivers ... (2 boards, stacked mezzanine) | the two-board split is an AI architecture decision scored against alternatives (A/B/C), so layer-count and area comparisons mix a process choice with the specification |

## 2. Process metrics comparable across generations

### 2.1 Workflow completeness

States: done, not done, or not yet available (V2 PCB phase running). Evidence names the repository file that was read.

| Step | V1 | V2 |
|---|---|---|
| Requirements capture and assumptions register | done - input/requirements.yaml; design/assumptions.md (13 rows) | done - input/requirements.yaml; design/assumptions.md (49 register rows); design_decisions.json (34 accepted assumptions, 26 conflict resolutions) |
| Knowledge retrieval with traceable citations | not done - no knowledge system existed (0 skills/rules retrievable) | done - knowledge_trace.json: 91 logged queries over 10 areas, 317 citation rows |
| Reproducible calculations script | done - automation/scripts/calculate_buck.py -> design/calculations.json (3 input cases, 14 loss items, no invariants) | done - automation/scripts/calculate_sic_buck.py -> design/calculations.json (6 operating points, 250 registered inputs, 19 invariants, 58 baseline cross-checks of which 57 agree) |
| Component records with stress, margin and verification level | done - component_selection.csv: 220 rows x 13 fields; uniform verification sentence | done - component_records.json: 65 part-type records x 18 fields with per-part verification levels (fetched-datasheet 29; search-snippet 7; unverified 26; manufacturer-page 3) |
| Schematic complete and ERC clean | done - 14 sheets, latest ERC 0 findings | done - power 12; control 10 sheets; latest ERC findings power 0 / control 0 |
| Behavioural simulation campaign | not done - no simulation (docs/knowledge-status.md) | done - 20 ngspice transient runs + 4 parasitic cases; steady checks 120/120, event checks 23/32 |
| Placement candidates evaluated | done - design/placement.json: one placement, no alternatives compared | done - 2 placement file(s): placement_control 120 x 80; placement_power 240 x 180 |
| Board routed | done - 3491 tracks, 720 vias on 6 layers | done - 2 board file(s); 10750 tracks, 1404 vias |
| Native DRC (with parity and unrouted checks) clean | done - latest DRC 0 findings (14 runs recorded) | done - latest DRC findings power 0 / control 0 |
| Power-layout metrics measured against the engineering rules | done - power-layout-metrics.json: 18 critical topology checks, rule review in pcb_rule_review.md | done - layout_metrics_*.json for control / power: power rows 58; within 27; exceeding 6; not_measured 0; control rows 31; within 2; exceeding 2; not_measured 10 |
| Independent review / verification records | done - 2 review records (AI visual review, PCB rule review); known_issues.md 12 rows | done - 20 verify_*.json records (confirmed-with-corrections 20) + consistency review; PCB-level review not yet available |
| Frozen release with hash manifest | done - releases/v1 frozen with SHA256SUMS.json (5 files) and review package zip | done - frozen release with 6 hashed files |

Steps done: V1 10/12, V2 12/12 with 0 steps not yet available. V1 steps marked 'not done' (knowledge retrieval, simulation) were not part of the V1 workflow; this is the genuine process difference between the generations.

### 2.2 Knowledge utilisation

| Metric | V1 | V2 | Comment |
|---|---|---|---|
| Knowledge items used (skills/rules/blocks/components/references/project rules) | skills 0; rules 0; blocks 0; components 0; references 0; project_rules 8 | skills 6; rules 43; blocks 13; components 16; references 4; project_rules 10 | V2 totals available: skills 6; rules 43; blocks 13; components 19; references 4; project_rules 8; project_rules counts 2 aggregate citation string(s) such as 'PE-PCB-001..008' besides the 8 individual rules |
| Applicability classes of citations | direct 0; adapted 0; not-applicable 0; human-review 0 | direct 114; adapted 101; not-applicable 35; human-review 23 | direct / adapted / not-applicable / human-review (plus 'see text' rows cited in markdown only) |
| Logged retrieval queries | 0 | 91 |  |
| Citation rows / distinct ids | 0 / 0 | 317 / 96 | V1 column shows 0: no citations existed |
| Validation status of cited items | - | reference-derived 160; analytically-checked 42 | nothing in the knowledge base is simulated or hardware-validated |
| Unknown ids flagged by the trace | - | 5 | aggregate citations and external sources that the trace could not resolve |

### 2.3 Verification coverage and open issues

| Metric | V1 | V2 | Comment |
|---|---|---|---|
| Research records / verification records | 0 / 0 | 10 / 20 | two lenses per area in V2: engineering recompute and source fact-check |
| Verification verdicts | - | confirmed-with-corrections 20 |  |
| Checked items by status | - | verified 409; contradicted 91; unverified 100 |  |
| Recomputed quantities (agrees / disagrees) | - | agrees 353; disagrees 61 |  |
| Required changes raised / knowledge-misuse items | - | 223 / 105 |  |
| Calculation invariants / baseline cross-checks | 0 / 0 | 19 / 58 |  |
| Independent review records | 2 | 21 | V2 PCB-level review (rule review, known issues) not yet available |
| ERC findings (latest run) | 0 | 0 |  |
| DRC findings (latest run) | 0 | 0 |  |
| ERC / DRC runs recorded | 6 / 14 | 7 / 51 | history of native check runs, not a quality score |
| Verification summary status | passed | passed | V2 'failed' means missing PCB-phase artefacts, not failing checks |
| Pipeline smoke (all modules on a disposable board) | n/a | passed |  |
| Simulation runs / models / parasitic cases | 0 / 0 / 0 | 20 / 20 / 4 |  |
| Simulation checks passed (steady / event) | - | steady 120/120; event 23/32 | failing checks in cl_400V_dump (load_step_off), cl_400V_dump_irefmin0 (load_step_off), cl_400V_singleloop_modulePI (load_step_on), cl_440V_dump (load_step_off): the 12.5 A-step limits (10 V / 5 ms) applied to the 25 A load-dump events, whose design-basis limit is the 230 V output OVP, plus the deliberately failing single-loop reference case |
| Simulated output ripple (Vpp) | - | 0.153-0.411 Vpp | limit 2.0 Vpp; range over all runs |
| Simulated load-step excursion (V) / recovery (ms) | - | 7.5-16.2 V / 0.751-5.0 ms | ranges over all load events including the 25 A dumps and the deliberately failing single-loop reference case; limits for the 12.5 A step are 10 V / 5 ms |
| Documented open issues (PCB-level register) | 12 | 49 | V2 design-level open items: 13 in design_decisions.json, 10 in calculations.json |

### 2.4 Documentation volume, automation tests and release

| Metric | V1 | V2 | Comment |
|---|---|---|---|
| Design documents (files / words) | 11 / 6869 | 22 / 153890 | V2 includes generated tables; volume is not quality |
| Design report words | 1344 | 6844 |  |
| Schematic sheets | 14 | 22 |  |
| Automation test modules / functions | 1 / 6 | 16 / 253 | V1 figure from the V1-era module and docs/status.md; V2 counts every module in tests/ |
| Export manifest commands / artifacts | 11 / 38 | 22 / 70 |  |
| Frozen release | yes | yes |  |

## 3. Layout and architecture metrics

Caveat: these are straight-line board geometries, counts and ratios. They are not loop inductance, current capacity, creepage per standard or EMI performance, and raw area or density never proves superiority (section 1). V2 values marked 'planned' are design targets from `design_decisions.json`; values marked 'not yet available' appear after the routed boards are measured by `automation/verification/check_sic_layout.py`.

| Metric | V1 (measured, frozen) | V2 | Comment |
|---|---|---|---|
| Board outline(s) (mm) | integrated 300 x 220 mm | power 240 x 180; control 120 x 80 mm | V2 outlines are design targets until the routed boards are measured |
| Total PCB area (mm2) | 66000 mm2 | 52800 mm2 | area alone proves nothing: V2 must host a 9 mm isolation barrier, films and a heatsink |
| Copper layers | 6 | power 4; control 4 | fewer layers per board in V2 follow from moving the fine-pitch DSP off the heavy-copper board |
| Copper weight (um) | 70 outer/In2/In3, 35 In1/In4 um | power F.Cu 70; In1.Cu 70; In2.Cu 70; B.Cu 70; control F.Cu 35; In1.Cu 35; In2.Cu 35; B.Cu 35 um |  |
| Board thickness (mm) | 2 mm | power 2; control 1.6 mm |  |
| Cost index (layers x dm2) | 39.6 layer-dm2 | 21.1 layer-dm2 | fabrication proxy only; V2 adds a mezzanine connector pair and non-plated slots |
| Footprints / schematic items | 240 | 444 | V2 counts schematic items until the boards exist; includes test points and mounting holes on both generations |
| Components per dm2 | 36.4 1/dm2 | 84.1 1/dm2 | V2 is 5x the power with isolation parts, so a higher density is expected, not earned |
| Named nets (per board) | 85 | power 101; control 111 |  |
| Nets per board | 85 nets | 106 nets |  |
| Tracks | 3491 | 10750 |  |
| Vias | 720 | 1404 |  |
| HF capacitor to MOSFET pad (mm) | 11-16 mm | 8.4-41.2 mm | V2 target 5 mm (row 1) / 15 mm (row 2); straight-line proxy, not loop inductance |
| Driver output to gate pad (mm) | 8.7-16.2 mm | 14.4-14.4 mm | V2 target <= 15 mm; V1 range was flagged long in known issue V1-01 |
| Switch-node copper (mm2) | 1660.4 mm2 | 3660.2 mm2 | sum over layers; V2 SW carries 400 V at 110 V/ns so a smaller area is required, not optional |
| DSP bypass max pad distance (mm) | 6.9 mm | 5.4 mm | V1 maximum 6.86 mm was known issue V1-08 |
| Isolation min copper distance (mm) | n/a | 1.0 mm | no V1 counterpart (48 V board); V2 threshold 9.0 mm on all layers |
| Barrier parts (slots required) | 0 | 8 |  |
| Barrier surface path min (mm) | - | 9.8 mm | 2*sqrt((g/2)^2 + e^2) around the slot ends; required >= 9.0 mm |
| Assembly height used (mm) | 57 mm | 67 mm | V1: 2.0 mm board + 55 mm inductor; V2: 15 mm standoffs + 2 mm board + 50 mm heatsink |
| Specific power (W/dm2) | 151.5 W/dm2 | 947.0 W/dm2 | rated power over summed PCB area |
| Volumetric power (W/L) | 265.8 W/L | 1413.4 W/L | summed PCB area x assembly height; not an enclosure volume |
| Layout rule rows (within / exceeding) | 18 | power rows 58; within 27; exceeding 6; not_measured 0; control rows 31; within 2; exceeding 2; not_measured 10 | V1 checker had no thresholds; V2 rows carry spec thresholds where the design defines one |

### 3.1 Density and power density (derived)

Definitions: rated output power divided by the summed PCB area of all boards; rated output power divided by (summed PCB area x assembly height); V1 height = board 2.0 mm + 55 mm inductor, V2 height = 67 mm documented stack (15 + 2 + 50); footprints (V1 measured; V2 schematic items until the boards exist) divided by summed PCB area; sum over boards of copper layers x board area in dm2; relative fabrication proxy, not a quotation.

| Derived metric | V1 | V2 | Reading |
|---|---|---|---|
| Total PCB area (dm2) | 6.6 dm2 | 5.3 dm2 | V2 planned total 5.28 dm2 versus V1 6.6 dm2 - a 20 % smaller area at 5x power and 8x voltage is only meaningful once clearances and loops are measured |
| Specific power (W/dm2) | 151.5 W/dm2 | 947.0 W/dm2 | dominated by the 5x power specification |
| Volume used (L) | 3.8 L | 3.5 L | summed board area x assembly height |
| Volumetric power (W/L) | 265.8 W/L | 1413.4 W/L | heights 57 mm (V1) and 67 mm (V2) are documented envelopes, not measured assemblies |
| Components per dm2 | 36.4 1/dm2 | 84.1 1/dm2 | V2 counts schematic items until the boards exist |
| Nets per board | 85 nets | 106 nets |  |
| Cost index (layer-dm2) | 39.6 layer-dm2 | 21.1 layer-dm2 | V2 adds a mezzanine pair and slots that the index ignores |
| Power per MOSFET (W) | 250 W | 2500 W | technology effect (SiC 1200 V versus paralleled Si 100 V) |
| BOM rows per kW | 220 rows/kW | 88.8 rows/kW | isolation parts raise the V2 count while power lowers rows per kW |

## 4. Component selection rationale, thermal design completeness and manufacturability

### 4.1 Component selection rationale

| Metric | V1 | V2 | Comment |
|---|---|---|---|
| Records / fields per record | 220 / 13 | 65 / 18 | V1: one row per reference designator; V2: one record per part type |
| Distinct part numbers / manufacturers (BOM) | 68 / 17 | 116 / 22 |  |
| BOM rows (incl. DNP in V2) | 220 | 444 | V2 DNP parts power 16; control 1 |
| Per-part verification level | not recorded 220 | fetched-datasheet 29; search-snippet 7; unverified 26; manufacturer-page 3 | V2 states fetched-datasheet / manufacturer-page / search-snippet / unverified per record |
| Knowledge references inside component records | 0 | 235 |  |
| Open sourcing issues / alternatives recorded | - | 100 / 81 |  |
| Custom footprints | 3 | 9 | V2 isolation parts need slotted custom footprints |
| Magnetic design record | no | yes | V2 output choke is a custom wound part with a Magnetic Database record |

### 4.2 Thermal design completeness

| Metric | V1 | V2 | Comment |
|---|---|---|---|
| Thermal document words | 308 | 5751 |  |
| Loss / temperature corners evaluated | 1 | 24 |  |
| Heatsink | external sink <= 1.5 C/W, part not selected | Fischer Elektronik LAM 5 D K 100 12, R_th 0.30 K/W at nominal fan flow ... |  |
| Interface material | 0.5 C/W per isolated TO-220 interface, material not selected | Bergquist Sil-Pad TSP A2000 0.254 mm (6 kVac class) custom cut 28 x 32 mm per device ... |  |
| Expected / hottest junction temperature (C) | illustrative 95 C | 105.7 / 143.1 | lumped steady-state arithmetic in both generations; nothing simulated or measured; V2 hottest corner: 360V/27.5A max R, k_RG 2.0 |
| Cooling-failure analysis | no | yes |  |
| Temperature sensor to junction mapping | LM61 measures power-area PCB temperature, not junction | heatsink NTC mapped to T_J with a stated offset band |  |
| Efficiency estimate (converter) | 0.963 | 0.987 | V2 target/floor target 0.980; floor 0.975; V1 sensitivity 0.928 if loss doubles |
| Total loss estimate (W) | 38.7 W | 65.7 W | different power levels; compare loss fraction, not watts |

### 4.3 Manufacturability

| Metric | V1 | V2 | Comment |
|---|---|---|---|
| Boards x layers x copper | 1 x 6 layers, 70 outer/In2/In3, 35 In1/In4 um, 2 mm | power 4 layers / F.Cu 70; In1.Cu 70; In2.Cu 70; B.Cu 70 um / 2 mm; control 4 layers / F.Cu 35; In1.Cu 35; In2.Cu 35; B.Cu 35 um / 1.6 mm | V1 combined heavy copper with an LQFP-176 on one board (known issue V1-09); V2 keeps fine pitch off the heavy-copper board |
| Fine-pitch parts on heavy-copper board | yes (LQFP-176, 0.5 mm pitch on 70 um outer copper) | no (DSP on the 35 um control board) (planned) |  |
| Non-plated barrier slots | 0 | 8 | slots under isolators where the land gap is below 9 mm |
| Custom footprints | 3 | 9 |  |
| Export manifest (commands / artifacts) | 11 / 38 | control_board commands 11; artifacts 35; status passed; power_board commands 11; artifacts 35; status passed |  |
| Fabrication notes raised | plated slots, exposed-pad vias, fine pitch with heavy copper (V1-09) | 0.20 mm prepreg between two 70 um layers to confirm; 2.0 mm core stack; slot widths >= 1.0 mm after tolerance | from the stack-up documents; fabricator DFM feedback is pending in both generations |

## 5. Genuine process improvements versus specification effects

Process improvements (independent of the electrical specification): a knowledge system with logged retrieval and classified citations; research records with two independent verification lenses per decision area; a calculation record with a registered input list, invariants and baseline cross-checks; per-part verification levels in the component records; an ngspice simulation campaign with analytical cross-checks; a data-driven layout checker with spec thresholds; and an automation test suite an order of magnitude larger.

Specification effects (not improvements): higher W/dm2 and W/L, fewer power devices, a shorter commutation cell, film instead of electrolytic capacitors, isolated drivers and sensing, barrier slots and the mezzanine interconnect. The two-board architecture sits between the two: it was chosen by a scored comparison (a process step) but its payoff - fine pitch off the heavy-copper board - is only real once both boards are routed and checked.

## 6. What this comparison can and cannot show

It can show:

- whether each workflow step exists in each generation and which file is the evidence (table 2.1);
- how much of the knowledge base was retrieved, how it was classified (direct / adapted / not applicable / human review) and how many citations were checked by independent verifiers (tables 2.2 and 2.3);
- which automated checks exist and their recorded results (ERC, DRC, layout rules, simulation checks, calculation invariants, tests);
- the planned versus measured V2 board geometry once the layout metrics exist, against the V1 measurements already on record (table 3).

It cannot show:

- that V2 is a better converter: no efficiency, EMI, thermal rise, insulation or control-loop result is measured in either generation;
- that fewer layers, smaller area or higher W/dm2 are achievements: they follow from the specification and the two-board split, and V2 must still prove 9 mm clearances, slot creepage and loop inductance on the routed boards;
- that more documents, citations or tests mean higher quality; they show traceability and coverage, which the human reviewer still has to judge;
- anything about manufacturability beyond the stack-up statements and export manifests: no fabricator DFM review exists for either generation.

### 6.1 V2 metrics not yet available (0)

- none

### 6.2 Sources

V1 files read: 15; missing: 0.
V2 files read: 52; missing: 0.
