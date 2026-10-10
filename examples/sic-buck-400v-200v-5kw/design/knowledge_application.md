**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# Knowledge application record - V2 SiC synchronous buck (400 V -> 200 V, 5 kW, 50 kHz)

This document records how the Engineering Knowledge System (knowledge/, V0: 6 skills,
43 rules, 13 circuit blocks, 19 component records, 4 reference designs) influenced the
V2 design, decision by decision, and where it was adapted, rejected or found wrong.
Sources: the orchestrator baseline [design_decisions.json](design_decisions.json)
(schema 4, wins over everything below), the ten research records
[research/*.json](research/) with their `knowledge_queries` and `knowledge_used`
sections, the twenty verification reports [research/verify_*.json](research/) with
their `knowledge_misuse` lists, and the regenerated trace
[knowledge_trace.md](knowledge_trace.md) / [knowledge_trace.json](knowledge_trace.json)
(`python -m automation.scripts.knowledge_trace`, run twice in this session; the second
run picked up the assumptions fact-check that arrived after the first). Knowledge
texts were read from
[knowledge/skills](../../../knowledge/skills/),
[knowledge/rules/engineering_rules.json](../../../knowledge/rules/engineering_rules.json),
[knowledge/circuit_blocks](../../../knowledge/circuit_blocks/),
[knowledge/components](../../../knowledge/components/) and the four
[reference analyses](../../../knowledge/references/). Nothing under knowledge/ was changed;
section 6 lists proposals only.

Labels. Applicability: **direct** (rule or pattern applied as written), **adapted**
(condition extended or value re-derived; reason stated), **not applicable** (scope
excluded), **human-review** (rule says a qualified engineer decides). Verification level
of every number: fetched-datasheet, manufacturer-page, search-snippet, unverified,
analytically-checked, simulated. Nothing in this document is simulated; no verification
level is upgraded relative to the source record.

## 1. Retrieval record

91 query entries are logged across the ten records: 74 free-text BM25 searches
(`python -m automation.knowledge.query "<question>" --json --limit 8`), 11 `--get`
record reads (several ids each) and 6 direct file reads of skills and analyses. All runs
needed `PYTHONIOENCODING=utf-8` on this Windows host (code page 936; a cp1252 console
raised `UnicodeEncodeError` for the assumptions agent). Condensed table; full commands
and hit lists are in `knowledge_trace.json` -> `queries`.

| Area | Searches / gets / reads | Representative questions | Top hits that shaped the record |
|---|---|---|---|
| assumptions | 11 / 2 / 1 | ambient and derating; input range / UVLO; output ripple; inductor ripple; efficiency; copper and spacing; SELV crossing; commissioning | SKILL-006, KR-TH-001..003, SKILL-003, KR-CAP-001/002, KR-ISO-001, SKILL-001, REF-TI-TIDA-010054 |
| standards_safety | 6 / 1 / 0 | insulation coordination 400 V; slots / net classes; discharge and labels; fuse I2t vs DESAT; heatsink PE and Y capacitors; copper and vias | KR-ISO-001..004, KR-SN-001, KR-PR-001, KR-TH-002, KR-PCB-006, SKILL-002 |
| mosfet | 7 / 1 / 1 | voltage margin; V_GS limits; short-circuit withstand; thermal path; "transistor database scope"; commutation loop; dead time | KR-GD-001, KR-PR-001, KR-TH-001/002, KR-PCB-004, SKILL-001 (device choice out of scope), SKILL-006 |
| gate_driver | 5 / 1 / 1 | driver IC (CMTI, DESAT, clamp); bias power / C_iso; R_G, blanking, soft turn-off, interlock; layout; negative rail | SKILL-001, SKILL-004, CB-GD-001, CMP-UCC21710-Q1, KR-GD-001/004/005, KR-IS-001..003, REF-WS-PRD-04814 |
| inductor | 8 / 1 / 0 | powder-core inductor design; temperature rise; placement vs exhaust; 25 A copper; Steinmetz; litz / AWG; terminals | KR-PCB-006, SKILL-006, KR-TH-001 - no magnetics content exists; SKILL-003 and CMP-750319177 were false hits |
| capacitors | 5 / 1 / 0 | film RMS ripple; HV MLCC and loop; bleeder spacing; output capacitor transient; derating and heat | SKILL-003, KR-CAP-001..003, KR-PCB-004/006, KR-ISO-002..004, SKILL-006 |
| controller_aux_interconnect | 9 / 1 / 1 | eFuse and 12 V protection; PWM buffer / latch / RS-422; supplies and sequencing; connector and ground interleaving; fault handling; dead time | CMP-TPS2640, CB-PR-001, CB-GD-003, KR-GD-008/009, KR-PR-002/003, CMP-UCC14141-Q1, CB-IS-002 |
| sensing_protection | 11 / 1 / 0 | Hall sensing and OC trip; AMC1311 ladders and 5 V LDO; latched trip zones; NTC via AIN/APWM; precharge; fuse; discharge; TVS / MOV; probes; SDFM absence | CB-SN-001/004, CMP-TMCS1133, CMP-AMC1311, SKILL-005, KR-SN-001..005, CB-PR-002, KR-PR-002 |
| thermal | 7 / 1 / 1 | shared sink and pad; NTC to T_J mapping; hot-spot placement; grounded sink creepage; IPC copper; fan failure; TI's own parts | SKILL-006, KR-TH-001..003, CB-PR-002, KR-ISO-002, KR-PCB-006, REF-TI-TIDA-010054 decision 9 |
| architecture | 5 / 1 / 1 | power / control partition; driver adjacency vs driver card; barrier keep-out and slots; control connector at the edge; gate / Kelvin stack-up | REF-TI-TIDA-010054 decision 10, SKILL-002, KR-PCB-001/003/005, KR-ISO-001..004, KR-GD-008, CB-GD-003 |

Hit statistics over the 74 searches (counted from the trace): REF-TI-TIDA-010054 38
appearances, SKILL-001 30, REF-WS-CGD1700HB2M-UNA 29, SKILL-003 28, SKILL-002 and
SKILL-006 23 each, CB-GD-001 22, SKILL-005 and CMP-UCC21710-Q1 14 each. Three retrieval
findings matter for section 6: (a) `--get PE-PCB-001` answers `unknown id` (re-run in
this session) because the project rules live only in
[docs/pcb-design-rules.md](../../../docs/pcb-design-rules.md) and
`automation/verification/pcb_rules.json`; (b) every magnetics query returned capacitor
or bias-transformer records, which is how the knowledge gap of section 2.3 surfaced;
(c) `--get REF-WS-PRD-04814 --json` does return the record (re-run in this session), so
the architecture fact-check statement that it is "not a retrievable reference record"
is a verifier error, not a knowledge-base defect.

## 2. Skill-by-skill application

### SKILL-001 SiC gate driver design - direct (gate_driver, controller, standards), adapted (architecture, sensing), not applicable (mosfet: device choice)

Prescribes: isolate every position, reference the driver to the Kelvin source, gate
levels from the selected device datasheet, peak current both ways, split R_G,ON/OFF,
off-state immunity, DESAT with soft turn-off and latched fault, gate discharge resistor,
robust signalling and interlock, nine-step procedure. V2 executed steps 1-9 for the
C4MS025120K (Rev. 2 Dec 2025 datasheet, fetched): UCC21710QDWRQ1 x2 (5.7 kVrms, VIOWM
1500 Vrms, > 150 V/ns CMTI; SLUSDH8D fetched-datasheet), rails +15.0 / -4.0 V, R_G,ON 10 ->
6.8 ohm and R_G,OFF 3.3 ohm (peak 1.26 A source / 3.06 A sink against 10 A), 10 k gate-Kelvin
discharge, DESAT 2.2 k / 4.99 k / 1.00 k / 680 pF with one US1M 1000 V diode (trip 3.6 V,
blanking 288 ns, response 0.55-1.07 us against 1.5 us; analytically-checked), cross-wired
interlock and open-drain FLT/RDY into the SN74LV21A combiner; per-rule values are in
section 3.
Adaptations: PRD-04814's "0 V turn-off usable for buck" was overridden because the
synchronous buck is a half bridge (KR-GD-005, both verifiers asked that this be stated
explicitly - done in the baseline `why_negative`). Instance values 2 ohm, 1 ohm, 10 ohm,
6.4 V / 1 us, 6.7 V / 46 ns and 20 uF per rail were not copied; the gate-driver fact-check
noted that +15/-4 V and the 10 ohm bring-up value coincide with reference instances and
asked for the coincidence to be declared - it is derived (rails from the C4MS and C3M
limits, 10 ohm from the datasheet E_on curve sweep range 4.7-15 ohm).

Misapplications found and corrected: (1) KR-GD-003 - both the MOSFET and gate-driver
agents concluded "inherently immune" from a small-signal C_rss bound (1.3 V / 0.6-1.0 V
excursion); both engineering verifiers rejected the bound; the baseline uses the
charge-based estimate (Q_gd 20-27 nC into C_gs 3.08 nF through the 5.6 ohm off path,
4.5-5.2 V excursion, gate reaching +0.5 to +1.2 V against V_GS(th),min 2.0 V at 25 C,
hot minimum unpublished) and makes the Miller clamp REQUIRED (CLMPI through a 0 ohm link,
path <= 15 mm). (2) KR-GD-011 / KR-GD-012 are module-scoped and were labelled "direct";
relabelled adapted (conclusion unchanged: soft turn-off, no gate Zener). (3) KR-PR-001
was presented by the standards agent as a datasheet comparison; Wolfspeed publishes no
withstand time for the C4MS025120K, so the baseline states verification by destructive
short-circuit test (human-review). (4) The OC-pin Schottky and R_GS 10 k were taken from
CGD1700 without derivation; the Schottky is now a reference-derived DNP option.

### SKILL-002 Gate driver PCB layout - direct (architecture, assumptions, capacitors, sensing, standards), adapted (gate_driver, controller hand-offs)

Prescribes: power loop first, gate/Kelvin pours on adjacent layers with the Kelvin layer
shielding, decoupling inside the loop, driver beside the switch, copper-free barriers on
every layer, spacing classes, slots for creepage, RC filters at receiving pins; numeric
distances come from the standard, not from the skill. V2 result: 4-layer 70 um power
board, gate pours on B.Cu over Kelvin pours on In2.Cu across a 0.2 mm prepreg (KR-PCB-001,
the main argument for 4 rather than 2 layers); eleven KiCad net classes (KR-ISO-003);
10 mm copper-free ISO_BARRIER on all layers plus 9.0 mm HV-to-SELV clearance (values from
the standards agent, KR-ISO-002 human-review); 1.2 mm nominal slots under all eight
barrier parts (3 x UCC14141, 2 x UCC21710, 2 x AMC1311, TMCS1133) extending e >= 3 mm beyond the pad rows (KR-ISO-004); drivers within 15 mm
of the gate pins (agent metric, not a rule value - fact-check correction accepted); V_GS
probe as 2-pin loops at the device side of R_G (CR-11, instead of the MMCX of step 8).
Adaptation and correction: the skill's scope note that busbar systems (~200 kW+) separate
drivers from the power stage was used by the architecture agent as a rule-level reason
to reject the driver-card Option C; both verifiers objected (SKILL-002 explicitly covers
plug-in driver boards). The rejection now rests on the KR-PCB-005 rationale (connector
inductance in the gate loop), the second barrier instance per card (KR-ISO-001) and cost.
KR-ISO-004 was first applied with a wrong through-slot path model ("gap + 2 x board
thickness"); corrected to the around-the-end surface path 2 x sqrt((g/2)^2 + e^2) >= 9.0 mm.

### SKILL-003 DC-link capacitor selection - adapted everywhere it was used, not applicable for the inductor

Prescribes, for DAB/PSFB bridges: charge balance C >= dQ/dV over every corner, RMS
current sets technology, two tiers (film + HV ceramics at the leg), DC-blocking sizing,
hand-off to SKILL-002/006. The skill was written around a rectified-tank capacitor
current; V2 replaced the waveform by the buck's pulsating input current (I_o during D,
zero otherwise, plus ripple), giving dQ = D(1-D) I_o T_s = 137.5 uC worst at 400 V /
27.5 A, and by the triangular output current (I_C,rms = dI_L / sqrt(12)), evaluated at
nine corners (analytically-checked). Step 5 (DC blocking, KR-CAP-004) does not apply.
The output filter was sized with C >= dI_L / (8 f_s dV) and the 12.5 A load-step
excursion, as the skill's own exclusion ("inductor-ripple output filters of low-voltage
converters") requires - the inductor verifiers noted the agents dropped the qualifier
"of low-voltage converters"; conclusion unaffected. Baseline values: input 2 x TDK
B32776G8206K000 20 uF 800 V (I_rms 14.5 A rated vs 6.92 A each worst, 3.9 Vpp ripple at
27.5 A; TDK datasheet fetched); HF tier 10 x CGA9P1X7T2J474M250KC 0.47 uF 630 V 2220 with an
assumed 60 % DC-bias loss (TDK curve not fetched - open issue); output 2 x B32776G4606K000
60 uF 450 V (0.25 Vpp, 7.4 V step excursion at f_c 2.5 kHz); film-to-ceramic ring ~670 kHz,
~1.1 W, and a DNP RC damping leg (added by the capacitor engineering verifier). KR-CAP-003
was relabelled adapted because TI never states the purpose of its MLCC columns (the
knowledge base itself marks it inferred). TI's 30/60 uF, 5 V ripple, 14 MLCC, B32716 parts
and 630 V / 1 kV ratios were not copied. The misuse that mattered: the sensing agent
generated its own 60 uF / 40 uF values although the capacitor result existed; the baseline
(CR-03, precharge numbers) uses 48.7 uF effective / 132 uF.

### SKILL-004 Isolated gate bias supply - direct (gate_driver), adapted (five other areas)

Prescribes: budget P = Q_G f_sw (V_DD - V_EE) per device, minimise C_iso, CM choke with
the input capacitor between choke and converter, rails around the source, regulate only
as needed, share only with review (KR-IS-004), protect the auxiliary input. V2 followed
the procedure: positions grouped (HS: SW node, LS: PGND), topology chosen with the
PRD-04814 comparison (integrated module UCC14141-Q1; discrete LLC CB-IS-001 kept as
fallback), gate power 0.119 W (Wolfspeed form) / 0.24 W (TI Eq. 30 factor 2) - the KR-IS-001
conflict was dropped by the gate-driver agent, restored by three verifiers, and the
baseline budget uses the larger value; i_CM = C_iso dv/dt with a 5 pF upper bound at
120 V/ns = 0.72 A (CIO not legible in the extraction); Wuerth 744226S choke with
3 x 10 uF between choke and VIN (verifier correction from 2 x 10 uF for bias derating).
Dividers 107 k / 16.2 k (VDD-VEE 19.0 V) and 9.76 k / 16.2 k (COM-VEE 4.0 V), 0.1 %.
Rejected after the RLIM sink check: the TIDA-010054 decision-7 / CB-IS-002 pattern (LS
gate module also feeding a TLV76050 5 V LDO for the isolated amplifiers, RLIM 600 ohm).
The gate-driver engineering verifier showed that the LDO return current must be sunk by
the COM-VEE regulator through RLIM, which would need RLIM <= ~57-110 ohm, outside the
datasheet RLIM qualification (0.125 A rms pin limit with a 16 % run-time qualification);
with the KR-IS-004 sharing review this led to CR-12: a dedicated third UCC14141-Q1
(VDD-VEE 15 V, COM-VEE 5.0 V, VEE = PGND, the AMC1311s fed from COM in the sourcing
direction, ~20 mA). The shared pattern stays documented as the alternative. Also corrected: the UCC14141 power rating had been read without its conditions (section 6,
item 2); the baseline quotes 1.5 W (10.8-13.2 V, TA <= 85 C), 1.0 W (8-18 V) and 2.5 W
absolute maximum, SOA curve still to be read. RECOM R12P2 / Murata MGJ2 (CB-IS-003) are
basic-insulation parts (250 Vrms working; RxxP2xx REV 9-2024) and are excluded from the
barrier.

### SKILL-005 Current and voltage sensing - direct (sensing, standards), adapted (controller, assumptions, architecture, gate_driver), human-review (capacitors interface)

Prescribes: rate every barrier part, scale with headroom, bitstream for long paths,
Kelvin shunts, hardware OC path, distributed HV ladders, isolated-side supply from the
gate bias. The delta-sigma path (KR-SN-003, CB-SN-002, CB-SN-003 modulator variant,
CMP-AMC1306M05, CMP-AMC1336) is not applicable: the TMS320F28335 has no SDFM peripheral;
analog isolated chains with short routes to the ADC were used instead. The shunt path
(KR-SN-004, CB-SN-003, CMP-AMC1302-Q1) was evaluated and rejected (no fast OC output,
loss, HV supply). Baseline values: TMCS1133C2AQDVGR in the inductor-output path, 0.33 V +
0.05 V/A, ADC full scale 53.4 A, OC 37.5 A from V_OC = 0.750 V (REF3125, 2.32 k / 1.00 k),
trip chain 546 ns, overload margin 32.0 A worst peak vs 33.7 A worst low trip bound
(analytically-checked; OC response 100/250 ns rows still to quote - unverified);
AMC1311BDWVR ladders 4 x 750 k + 10.0 k (602 V full scale) and 2 x 750 k + 10.0 k (302 V),
OPA2320 gain 1.5 at 32 kHz moved to the power-board SELV strip (CR-16). Instance values 45/70 A, 8.2 k / 1.2 k, TMCS1133B1QDVGR and 8 x 634 k were not copied (the
10.0 k bottom resistor and 330 pF coincide with TIDA and are declared re-derived). Principle 7
(isolated supply from the gate bias) is the item rejected in CR-12. Misuse corrected: package
creepage (8 mm) had been compared with a laminate requirement at 480 V; the standards
agent's 440 V DC working voltage and 9.0 mm all-layer rule govern, with slots under the
DVG/DWV bodies. TMCS1133 isolation: TI product page 600 Vrms / 8.1 mm vs SBOSAG0E 950 Vrms /
1343 VDC reinforced; datasheet governs, TI confirmation open.

### SKILL-006 Thermal placement - adapted (seven areas), direct (capacitors, standards)

Prescribes: P_max = (T_J,max - T_A) / (R_th,JC + R_th,iso + 2 R_th,HS) with two devices
per sink, insulate shared sinks, losses first, thermal placement must not lengthen
loops, NTC is not T_J. V2 re-ran the budget with 50 C ambient (TI: 40 C, and TI warns the
DAB is for room ambient only), R_th,JC 0.41 K/W (fetched), the real pad and sink: P_max
41.5 W per device at 150 C against 34.1 W at the hottest corner (360 V / 27.5 A, max R),
margin 1.22 (analytically-checked); T_J,HS ~109 C typical, ~130 C worst corner (CR-21); Fischer
LAM 5 D K 100 12 at 0.30 K/W (distributor figure, unverified) after CR-06/CR-13; Sil-Pad
TSP A2000 0.254 mm, R_pad 1.4 K/W design value (fetched TDS impedance over the exposed-tab
area, CR-21), replacing an equal-share /
0.1-0.5 K/W pad assumption the assumptions verifier showed too optimistic. Adapted by
analogy to the inductor (KR-TH-001 with the Magnetics surface-area model; 125 C winding
limit is an added assumption, not a rule value) and to the film capacitors (step 3,
">= 20 mm from the sink, outside the exhaust" - the knowledge base marks this step as a
recommendation without source evidence, so it stays a recommendation). CR-14 places the
inductor in the fan stream because its 110-120 C still-air hot spot is unacceptable.
KR-TH-003 was applied as cooling supervision only; the 80 / 90 / 100 C thresholds (CR-25) are
human-review proposals, not design values (thermal verifier), with T_J,HS ~ T_NTC + 50-66 K at
full load: a 100 C sink corresponds to T_J,HS 150-166 C, so the earlier 90 / 100 / 110 C ladder
(hardware trip at T_J 176-178 C) was lowered and a firmware T_J estimator is recommended
(thermal_analysis.md section 6).
The skill's Ohmite / Wakefield instance values were not reused (section 5, last paragraph).

## 3. Rule-by-rule table

Applicability is the consolidated V2 position after verification (per-area labels are in
`knowledge_trace.md`). Verification tags: A = analytically-checked, D = fetched-datasheet,
M = manufacturer-page, S = search-snippet, U = unverified, H = human-review item.

| Rule | Category | V2 applicability | Decision influenced and design value | Ver. |
|---|---|---|---|---|
| KR-GD-001 | hard | direct | Rails +15 / -4 V (+/-1.3 %) vs C4MS025120K -10/+23 V and C3M0021120K -8/+19 V; the Gen-3 +19/-8 example was not assumed for Gen-4 | D, A; overshoot measurement H |
| KR-GD-002 | rec. | direct | Split OUTH/OUTL: R_G,ON 10 -> 6.8 ohm, R_G,OFF 3.3 ohm; steering diode (CB-GD-002) not needed | A |
| KR-GD-003 | rec. | adapted -> required | Miller clamp REQUIRED after the charge-based parasitic turn-on estimate (+0.5..+1.2 V vs 2.0 V threshold); exclusion not shown to apply | A; off-state V_GS test H |
| KR-GD-004 | human-review | human-review | DESAT trip 3.6 V, blanking 288 ns derived from C4MS curves; 6.4 V/1 us and 6.7 V/46 ns not reused; confirm on hardware | A, H |
| KR-GD-005 | rec. | direct (buck treated as half bridge) | -4 V turn-off; 0 V rejected (about 1 V margin) | A |
| KR-GD-006 | rec. | adapted (same supplier, two generations) | +18 V C4MS-only population option (FBVDD top resistor 127 k); blanking shift 288 -> 229 ns | A |
| KR-GD-007 | rec. | direct | 10 k gate-Kelvin at the device side of R_G (47 k alternative noted) | A |
| KR-GD-008 | rec. | adapted (mezzanine = short link) | Buffered single-ended PWM, 100 ohm + 100 pF + 10 k at each driver input; RS-422 (CB-GD-003) only for cables > 150 mm; CM-injection and open-connector tests in the plan | A; test H |
| KR-GD-009 | rec. | direct | IN+/IN- cross-wiring; dead time from ePWM: 300 ns programmed (45 ticks), 250 ns target, 150 ns minimum (CR-07) | A |
| KR-GD-010 | human-review | human-review | DNP 0603 gate-Kelvin RC pads (1 ohm + 470 pF) for review with double-pulse data | H |
| KR-GD-011 | rec. (modules) | adapted | UCC21710 400 mA soft turn-off; no two-level turn-off | D |
| KR-GD-012 | rec. (modules) | adapted | No gate-Kelvin Zener; damping zeta 1.6-3.8 | A |
| KR-IS-001 | hard | direct (both forms shown) | 0.119 W (Q_G f dV) / 0.24 W (TI factor 2) per channel; module budgets 0.32 / 0.32 / 0.4 W vs 1.5 W rating; input 0.45 A at 12 V | D, A; SOA at 10.8 V H |
| KR-IS-002 | rec. | direct | Wuerth 744226S + 3 x 10 uF between choke and VIN pin, 100 nF at VIN | D |
| KR-IS-003 | opt. | direct | i_CM 0.72 A at 5 pF / 120 V/ns (CIO < 3.5 pF not legible); LLC 0.68 pF noted | A, U |
| KR-IS-004 | human-review | human-review -> resolved | Shared LS supply rejected (CR-12); dedicated third UCC14141-Q1 for the sensing island | A, H |
| KR-IS-005 | rec. | direct | Regulated module (+/-1.3 %) so no LDO post-regulation; +/-5 % target met | D |
| KR-CAP-001 | hard | adapted (buck waveform) | dQ = D(1-D) I_o T_s = 137.5 uC; C_in >= 17 uF for 2 % -> 2 x 20 uF (48.7 uF effective with ceramics) | A |
| KR-CAP-002 | hard | direct (input) / adapted (output) | Film I_rms 6.92 A each vs 14.5 A rating at 50 kHz (ESR flat 10-70 kHz verified for Vishay only); output 1.43 A each | D, A |
| KR-CAP-003 | rec. | adapted (TI purpose inferred) | Two tiers: films + 10 x 0.47 uF 630 V within 5 / 15 mm of the device pins | S (MLCC), A |
| KR-CAP-004 | rec. | not applicable | No transformer, no DC-blocking capacitor | - |
| KR-SN-001 | hard | direct + human-review | UCC21710 (5.7 kVrms, VIOWM 1500 Vrms), AMC1311 (7 kVpk, 1500 Vrms), TMCS1133 (950 Vrms / 1343 VDC) at 440 V DC reinforced; UCC14141-Q1 certificate status and G9EA-1 coil-to-contact insulation open | D, H |
| KR-SN-002 | hard | direct | 480 V -> 2.392 V, 240 V -> 2.384 V of 3 V ADC; 37.5 A trip inside the 53.4 A range | A |
| KR-SN-003 | rec. | not applicable | F28335 has no SDFM; analog isolators to the ADC | - |
| KR-SN-004 | rec. | not applicable | No shunt; Hall sensor selected | - |
| KR-SN-005 | rec. | direct | TMCS1133 OC_N -> latch -> RST_EN + TZ1, and TZ2 directly; ADC limits are back-ups | A |
| KR-PCB-001 | rec. | direct | B.Cu gate pours over In2.Cu Kelvin pours (0.2 mm prepreg), Kelvin layer shields | - (layout pending) |
| KR-PCB-002 | rec. | direct | 2 x 4.7 uF + 100 nF (VDD-COM), 4.7 uF + 100 nF (COM-VEE) between driver and gate/Kelvin, C_eff >= 1.25 uF for 100 mV droop | A |
| KR-PCB-003 | hard | direct | COM/VEE return only to the Kelvin pin; netlist check that Kelvin and power source stay distinct | - (check pending) |
| KR-PCB-004 | opt. | direct | Commutation loop first: <= 20 nH board target, 40-60 nH with standing leads (25/35 nH were agent assumptions, not rule values) | A, U |
| KR-PCB-005 | rec. | direct | Drivers on the power board within 15 mm of the gate pins (agent metric); Option C rejected on the rule's rationale | - |
| KR-PCB-006 | rec. (low confidence) | direct, sizing added | 70 um on all layers, >= 12 mm outer / 22 mm inner per 25 A, 24 x 0.3 mm vias per transition (IPC-2221 formula, conservative vs IPC-2152) | A |
| KR-ISO-001 | hard | direct (both clauses) | 10 mm ISO_BARRIER on all layers; HS/LS inter-island barrier 3.0 / 1.0 mm; "no control copper above HV copper" is an agent extension for standards review | H |
| KR-ISO-002 | hard | human-review (values from the standards record) | 9.0 mm HV-to-SELV all layers, 5.0 mm HV-to-PE, 3.0 / 1.0 mm functional, 4 kV / 6 kV impulse basis (secondary-source until a licensed copy is read) | U/secondary, H |
| KR-ISO-003 | rec. | direct | Eleven net classes (HV_VIN, HV_SW, HV_PGND, HV_VOUT, DRV_HS, DRV_LS, DESAT_HS, DESAT_LS, SENSE_ISO, PE, CTRL_SELV) | - |
| KR-ISO-004 | rec. | direct (model corrected) | 1.2 mm nominal (>= 1.0 mm) slots under eight barrier parts, e >= 3 mm; CGD1700 0.76 mm slot not reusable at PD2 | A, H |
| KR-PR-001 | hard | direct, verification by test | DESAT 0.55-1.07 us vs no published withstand time; destructive short-circuit test required; fuse cannot protect the device | A, H |
| KR-PR-002 | rec. | direct (adapted for the bus UVLO ladder) | SN74LVC1G74 latch, three SN74LV21A combiners with SN74LV04A inverters (CR-26), latched vs run-permit groups (CR-17), operator reset after DESAT/OC | M (logic), A |
| KR-PR-003 | rec. | direct, thresholds human-review | TPS26400: UVLO 10.0 / 9.3 V, OVP 14.45 / 13.4 V, circuit-breaker mode I_CB ~1.96 A (R_ILIM 6.04 k) vs 1.76 A worst pull-in (CR-02, CR-18) | D, A, H |
| KR-TH-001 | hard | direct (adapted for the inductor) | P_max 41.5 W vs 34.1 W (1.22, R_pad 1.4 K/W, CR-21); inductor P_max 28.7 W vs 19.8 W typical / 23-26 W bounded | A |
| KR-TH-002 | rec. | direct, rating conflict human-review | Sil-Pad TSP A2000 (6 kVac class) 28 x 32 mm, R_pad 1.4 K/W on the exposed-tab area (CR-21); 2.5 kV vs 4 kV impulse view preserved (CR-13) | D, H |
| KR-TH-003 | human-review | human-review | NTCALUG01A103F on the sink top face; 80 / 90 / 100 C (CR-25) are review proposals; T_J ~ T_NTC + 50-66 K at full load | D (NTC), A, H |
| KR-PE-001 | human-review | not applicable | Hard-switched buck; no ZVS boundary | - |
| PE-PCB-001 | project | adapted (evidence prepared) | Gate loop: driver distance, adjacent-layer pair, decoupling inside the loop; overlay at layout review | H |
| PE-PCB-002 | project | direct | HF ceramics in two rows within 5 / 15 mm of the HS drain / LS source pins | H |
| PE-PCB-003 | project | direct | Commutation loop first, <= 20 nH board target, overlay including layer transitions | H |
| PE-PCB-004 | project | not applicable | No shunt; Hall conductor sizing falls under PE-PCB-006 | - |
| PE-PCB-005 | project | direct | Sense ladders, Kelvin pairs, NTC and TACH wiring away from SW; inductor keep-out circle + 10 mm | H |
| PE-PCB-006 | project | direct | Copper widths, 24 vias per 25 A transition, 25 um plating assumption, loss rationale supplied | A, H |
| PE-PCB-007 | project | direct | Two-board partition: control board entirely SELV; SELV strip behind the barrier | H |
| PE-PCB-008 | project | direct | Per-pin decoupling maps for UCC21710, UCC14141, TMCS1133, AMC1311, eFuse, buck, LDO, DSP | H |

## 4. Circuit blocks and component records

| Block | Function (knowledge base) | V2 use |
|---|---|---|
| CB-GD-001 | UCC21710 stage with split R_G, clamp, DESAT, soft turn-off, AIN/APWM | adapted: topology and the EC-001/EC-002 trip-and-blanking formulas kept; every value re-derived (2.2 k / 4.99 k / 1.00 k / 680 pF, one 1000 V US1M instead of two US3M, 3.6 V / 288 ns) |
| CB-GD-002 | single-output driver with steering diode | not applicable (split outputs available) |
| CB-GD-003 | RS-422 interface, fault AND, fail-safe polarity | not applicable for the stacked mezzanine; its fault-combining and RC-at-pin patterns reused; mandatory fallback for any cabled variant |
| CB-IS-001 | discrete LLC bias (UCC25800 + 750319177) | not applicable; retained as the fallback if the UCC14141 SOA check fails (lowest C_iso 0.68 pF) |
| CB-IS-002 | UCC14141 per driver, LS module optionally feeding a 5 V sensing LDO | adapted then partially rejected: module per channel adopted with re-derived dividers; the shared sensing-LDO option rejected after the COM-VEE sink check (CR-12) |
| CB-IS-003 | SIP module behind fuse and CM choke, optional LDOs | not applicable: RECOM -3 V / Murata -5 V unregulated and basic insulation only |
| CB-IS-004 | resistor-Zener split rails | not applicable: the module regulates VDD-COM and COM-VEE directly |
| CB-PR-001 | 12 V auxiliary protection (eFuse alternative A, P-FET + Zener alternative B) | adapted: TPS26400 with derived thresholds; TI's 15 V / 9 V / 2.2 A / 36 V TVS replaced |
| CB-PR-002 | thermistor on the driver AIN/APWM | adapted by three agents with different NTCs, networks and thresholds, then rejected for this grounding scheme (CR-01): with a PE-bonded sink and a PE-bonded SGND the NTC lug is at control potential, so a direct SELV NTC is used; the AIN path would put the floating PGND-to-PE voltage across the NTC; the block stays a fallback; both AIN pins tied to COM; the APWM polarity misread (88 % at 0.6 V, 10 % at 4.5 V) is a record gap, section 6 |
| CB-SN-001 | 800 V ladder into AMC1311 + OPA2320 | adapted: 4 x 750 k + 10 k (602 V FS) and 2 x 750 k + 10 k (302 V FS), gain 1.5, conditioning on the power-board SELV strip (CR-16) |
| CB-SN-002 | 500 V ladder into AMC1336 bitstream | not applicable (no SDFM) |
| CB-SN-003 | shunt with AMC1302 / AMC1306 | not applicable: evaluated and rejected |
| CB-SN-004 | Hall sensor with OC flag tripping PWM | adapted: TMCS1133C2AQDVGR in the DC output path, 37.5 A from SBOSAG0E Eq. 21 with REF3125, OC_N to TZ2 and latch |

Component records (19): reused directly - CMP-UCC21710-Q1 (re-verified against SLUSDH8D,
UVLO / deglitch / skew added), CMP-UCC14141-Q1 (conditions on the power rating found
missing), CMP-TPS2640 (circuit-breaker threshold missing from the record), CMP-AMC1311,
CMP-TMCS1133 (orderable variant corrected to the A-suffix). Evaluated and superseded -
CMP-CGA9P1X7T2J474M250KC adapted (same family, quantity 10 derived, DC-bias curve open);
CMP-2220Y1K00474KETWS2 as the 1 kV alternate (KXTWS2 variant, StackiCap height to verify);
CMP-R12P21503D and CMP-MGJ2D122005SC rejected (unregulated, basic insulation); CMP-UCC25800-Q1
with CMP-750319177 fallback only (the transformer record was also a false hit for the output
choke); CMP-UCC23514 rejected (no DESAT, KR-PR-001); CMP-AMC1302-Q1 rejected alternative;
CMP-B32716H8306K000 and CMP-B32716H1156K000 superseded by the TDK B32776 4-pin series
(fetched datasheet); CMP-C1812V104KDRACTU no corresponding position. Not touched -
CMP-GCM31CR71C106KA64L, CMP-AMC1306M05, CMP-AMC1336 (the latter two excluded with SKILL-005's
bitstream path). V2 parts with no record: C4MS025120K, C3M0021120K, UCC14141 sensing
configuration, B32776G8206K000 / G4606K000, TMCS1133C2AQDVGR, REF3125, REF3130, TLV1702, OPA2320,
SN74LVC1G74DCTR, SN74LV21A, SN74LV04A, TPS54302, TPS767D301, TPS3808G01, Fischer LAM 5 D K 100 12, Sil-Pad
TSP A2000 / 3500, NTCALUG01A103F, Omron G9EA-1 DC12, KLKD025.T, Magnetics 0058192A2, Wuerth
744226S, Samtec SSW/TSW, REDCUBE 74651195 (candidates for records, section 6).

## 5. Reference designs

**TIDA-010054 (REF-TI-TIDA-010054, 10 appearances, all adapted).** Transferred as patterns:
decision 4 (one isolated driver plus one integrated bias module per switch), decision 2
(two-tier DC link, dQ -> C method), decision 6 (sensing split, AMC1311 + OPA2320 chain, Hall
with OC flag), decision 8 (12 V eFuse at the entry), decision 9 (two TO-247 per insulated
forced-air sink, shared-sink reading of the factor 2), decision 10 (power board + control
card, drivers on the bottom beside each TO-247-4, LV circuitry at the edge, bus copper on
several layers). Explicitly not copied: 2 ohm gate resistors, 6.4 V / 1 us DESAT, 45 / 70 A
Hall trips, 8 x 634 k ladder, 30 / 60 uF film and 5 V ripple, 14 MLCC per side, 630 V / 1 kV
ratios, R_LIM 1 k / 600 ohm, OVP 15 V / UVLO 9 V / 2.2 A / 36 V TVS, 40 C ambient, 0.5 and
0.1 K/W, 50 / 69 W limits, SN74LVC126A buffers, TMP6131. Decision 7 (sensing supply from the
LS gate bias) was adopted structurally and then rejected after the sink check (CR-12) -
TI itself provided but did not test the sharing options, which the record states. Wrong or
stale: the "300 x 180 mm" size benchmark is not in the knowledge record (removed by the
assumptions and controller verifiers); the C3M0030090K cited for the 500 V side is
obsolete (manufacturer-page level); the utilisation ratios 0.67 / 0.56 were mis-attributed
to "decision 1" and are AIPE-derived from SKILL-006's EC-019/020 devices.

**CGD1700HB2M-UNA with PRD-09301 (REF-WS-CGD1700HB2M-UNA, 8 appearances, adapted).**
Transferred: split outputs with CLMPI link and 10 k discharge (decision 1), DESAT network
topology and the recomputed trip / blanking formulas (decision 2), soft shutdown and
latched global fault with RESET >= 1 us (decision 3), interlock cross-wiring and the rule
that on-board single-ended links are acceptable (decision 4), CM choke before the module
(decision 5), net-class structure PRIMARY / LS / HS / DESAT-midpoint / drain (decision 6),
gate / Kelvin pour guidance (decision 7), NTC isolation rationale (decision 8). Not copied:
1 ohm 2512 resistors, 6.7 V / 46 ns, 2 x US3M, 56 pF, 20 uF per rail, 120 ohm / 56 pF reset
filter (100 ohm / 100 pF derived), 0.76 mm slots, 25.4 x 30.5 mm islands (used only to
calibrate a 30 x 35 mm envelope), BAT42W necessity. Stale or inconsistent: the board size
differs between analysis.md (50.8 x 61.0 mm) and reference.json (50.8 x 59.69 mm);
PRD-08296 short-circuit data were cited under this reference although it is a separate
Wolfspeed note on module data; the APWM polarity is absent from the derived CB-PR-002.

**CGD15SG00D2 with PRD-06933 (REF-WS-CGD15SG00D2, 4 appearances, adapted).** Transferred:
LLC fallback (decision 3), source-referenced decoupling at the output pins (decision 5),
Miller-clamp path-length argument and the 10 k vs 47 k pull-down conflict (decision 6),
observed PCB practice Tg >= 170 C, ENIG, 1 mm non-plated slots (decision 7, cross-check
only). Not copied: 10 ohm resistors (coincidence with the bring-up value declared),
+15 / -3.3 V, 47 k, 8 mm creepage and 800 Vpk (board-specific, not assessed to a standard),
0.68 pF transformer. The record's statement that the board "has not been assessed to a
third-party standard" was respected.

**PRD-04814 (REF-WS-PRD-04814, 3 adapted, 2 not applicable).** Transferred: gate-level
method (+15 V, -3 to -4 V, +/-5 %) with the selected datasheet governing (KR-GD-001),
C_iso argument (KR-IS-003), topology comparison (SKILL-004 step 3), gate-Kelvin RC only
with a Kelvin source (KR-GD-010), sharing needs decoupling resistors (KR-IS-004). Not
transferred: the Gen-3 +19 / -8 V maxima (Gen-4 datasheet: -10 / +23 V), the "0 V turn-off
for buck" note, the resistor-Zener split tables. Nothing in it is a tested design.

**SKILL-006's TI instance values** (CR201-50VE 0.5 K/W, CD-02-05-247 0.1 K/W, two fans
1.14 -> 1.43 A) were not reused; the Ohmite sheet lists the series as discontinued since
August 2024 and gives a forced-convection chart at 10 W test power with the airflow for
0.5 K/W unstated (thermal fact-check, fetched copy via a distributor); the Wakefield figure
is 0.107 C-in2/W, an area-normalised quantity, not a per-device resistance.

## 6. Knowledge-base feedback (proposals only; nothing changed)

Corrections to existing records.

1. CB-PR-002: add the APWM transfer polarity from SLUSDH8D - 88 % duty at V_AIN 0.6 V,
   10 % at 4.5 V, D = 0.88 - 0.200 x (V_AIN - 0.6 V); hot NTC -> higher duty. Two agents
   decoded it inverted. Also record the datasheet treatment of an unused AIN (tie to COM)
   and the single-owner rule for the NTC chain.
2. CMP-UCC14141-Q1: attach the conditions to the power ratings (1.5 W at 10.8-13.2 V,
   TA <= 85 C; 1.0 W at 8-18 V; POUT_VDD_MAX 2.5 W at 25 C; SOA = lower of 1.5 W and the
   derating curve) and add the COM-VEE regulator sink path through RLIM with the 0.125 A rms
   pin limit; this is the fact that decided CR-12. Resolve the working-voltage figure: the
   baseline carries VIORM 1414 Vpk / VIOWM 1414 VDC, the gate-driver record 1000 Vrms /
   1414 VDC, and the standards verifier quoted 1500 Vrms / 2121 VDC - to be settled from
   SLUSF10B by the reviewer.
3. CMP-TPS2640: add the MODE table, the circuit-breaker threshold I_CB = 12 / R_ILIM - 0.03 A
   with 4 ms timeout and 540 ms retry; "2 A eFuse" is not a threshold.
4. CMP-TMCS1133: orderable_variants lists TMCS1133B1QDVGR, which SBOSAG0E does not
   contain; list the A-suffixed numbers (B1AQDVGR, C2AQDVGR, C9AQDVGR exist per the sensing
   fact-check) and note the product-page / datasheet VIOWM discrepancy (600 Vrms vs 950 Vrms).
5. CMP-R12P21503D (and CB-IS-003 / SKILL-004): record from the cached RxxP2xx REV 9-2024
   datasheet "working voltage 250 VACrms" and "insulation grade according to 62368-1:
   basic", so the family is screened out of reinforced HV barriers early.
6. SKILL-006 and the TIDA analysis: mark the C3M0030090K as obsolete and the CR201-50VE as
   discontinued (August 2024); state that 0.5 K/W and 0.1 K/W are TI instance values whose
   airflow and pressure conditions are not on record.
7. KR-GD-011 / KR-GD-012: add an applicability note for discrete devices ("applies by
   analogy; label adapted"), and KR-GD-008: express the exclusion by link length and
   noise environment rather than "on-board", with a measurement verification (CM
   injection, open-connector) attached.
8. KR-ISO-004: add the through-slot creepage model (surface path around the slot ends,
   2 x sqrt((g/2)^2 + e^2)) and the PD2 minimum slot width 1.0 mm after tolerance; the
   first application used a wrong model.
9. REF-WS-CGD1700HB2M-UNA: reconcile the board size between analysis.md and
   reference.json; cite PRD-08296 as its own document (module CAB016M12FM3 data, Nov 2023)
   or add a reference record for it.
10. SKILL-005 principle 7 and SKILL-004 principle 6: add the caveat that a sensing load
    returned to the gate module's COM must be sunk by the COM-VEE regulator (RLIM check)
    before sharing is accepted.
11. SKILL-003: keep the exclusion wording "inductor-ripple output filters of low-voltage
    converters" but add the HV buck case explicitly (input: dQ = D(1-D) I_o T_s; output:
    inductor-defined ripple and load-step energy), since two agents misquoted the scope.

Additions.

12. New skill "powder-core DC inductor design" from [research/inductor.json](research/inductor.json)
    `selection.magnetic_record` (AIPE-MAG-L1-SICBUCK-5KW-V2): LI^2 selector, percent-permeability
    fit %u = 1 / (a + b H^c), Steinmetz fit P = a B^b f^c (mW/cm3, T, kHz), DC-magnetisation
    fit, surface-area temperature model dT = (P_mW / A_cm2)^0.833 (an own approximation, not a
    catalogue caveat), the soft-saturation criterion L(41 A) >= 70 % of L(25 A) alongside the
    vendor 30 %-drop I_sat, and the datasheet-maximum core-loss case (1.44 x fit). Component
    records for Magnetics 0058192A2 / C058192A2 (orderable code to confirm). The fits were
    verified by the inductor verifiers against the Magnetics 2024 catalogue tables except
    the dT correlation and the relative-cost table.
13. Gen-4 device records: CMP-C4MS025120K (Rev. 2 Dec 2025, -10 / +23 V, R_th,JC 0.41 K/W,
    Q_G 125 nC, no short-circuit withstand time published, Arrow-only stock at search-snippet
    level), CMP-C3M0021120K fallback, and an open check on a Gen-4 750 V TO-247-4 family.
14. Component records for the V2 parts listed at the end of section 4, each with the
    verification level reached in V2 (TDK B32776, Bergquist TSP A2000 / 3500, Vishay
    NTCALUG01A, Omron G9EA-1 with its 400 V maximum switching voltage, Littelfuse KLKD
    with I2t still missing, Fischer LAM 5 D K distributor-only).
15. SKILL-002 / SKILL-006: record the V2 partition pattern (one barrier line through all
    eight isolators, device row on the HV side, SELV strip at the edge, control board stacked
    over the strip) as a reference-derived pattern once the layout exists.
16. A reference record for IEC 61800-5-1:2022 + COR1:2023 clause mapping (4.3.11 -> 4.4.9)
    once a licensed copy is on record; today the values are secondary-source.

Tooling.

17. query.py: index `automation/verification/pcb_rules.json` (or docs/pcb-design-rules.md)
    so PE-PCB-001..008 resolve with `--get` and appear in search hits; today `--get PE-PCB-001`
    returns `unknown id` (re-run in this session), and four research records cite the rules
    as if retrieved.
18. query.py: reconfigure stdout to UTF-8 (`sys.stdout.reconfigure(encoding="utf-8")`) or
    use `ensure_ascii` for the text output; without PYTHONIOENCODING the console output on
    this host (code page 936) is garbled and on a cp1252 console the tool raises.
19. Component-record cache paths (`.cache/references/datasheets/*.pdf`): the cache directory
    does not exist on this host (checked), and the cache is git-ignored by design; records
    should state that the cache is optional and that `automation.knowledge.acquire` restores
    it, or the sha256 / resolved_url alone should be treated as the evidence anchor.
20. knowledge_trace.py: split compound ids ("PE-PCB-001..008", "PE-PCB-005/PE-PCB-007/
    PE-PCB-008") instead of counting them as unknown ids and over-counting project rules
    (10/8); recognise `external-method` and `project-precedent` entries as declared
    non-knowledge sources rather than unknown ids.
21. Process: the KR-IS-001 factor-2 conflict and the KR-GD-003 exclusion were each lost by
    one agent and restored by verifiers; the research-record schema could require a
    `conflicts_preserved` field for every rule that carries a `conflicts` list.

## 7. Coverage statistics (from knowledge_trace.json, regenerated 2026-10-10 after all twenty verify files existed)

| Measure | Value |
|---|---|
| Trace rows | 317 (273 with an applicability label from `knowledge_used`, 44 "cited-in-text-only" ids that appear in a record's markdown without a `knowledge_used` entry) |
| Applicability of the 273 | direct 114 (41.8 %), adapted 101 (37.0 %), not applicable 35 (12.8 %), human-review 23 (8.4 %) |
| Rows by type | rule 138, skill 42, reference 27, block 22, component 20, project rule 22, project precedent 1, external method 1, cited-only 44 |
| Coverage | skills 6/6; rules 43/43; blocks 13/13 (CB-SN-002 only as a text citation); components 16/19 (unused: CMP-GCM31CR71C106KA64L, CMP-AMC1306M05, CMP-AMC1336); references 4/4; project rules reported 10/8 (compound ids, see item 20) |
| Unknown ids | 5: "PE-PCB-001..008" (x2), "PE-PCB-005/PE-PCB-007/PE-PCB-008", "V1 project precedent (examples/buck-48v-24v-1kw)", "Magnetics-2024-powder-core-catalog (external, proposed new SKILL)" |
| Query entries | 91 (74 searches, 11 `--get` reads, 6 direct reads); per area 5-14 |
| Verification verdicts | 20 of 20 "confirmed-with-corrections"; 105 knowledge_misuse entries (including explicit "no misuse found" entries) and 223 required_changes in total |

Per area (rows with a label: direct / adapted / not applicable / human-review; cited-only):
architecture 11 / 12 / 1 / 1; 8 - assumptions 15 / 11 / 3 / 1; 19 - capacitors 10 / 5 / 6 / 2; 0 -
controller_aux_interconnect 14 / 11 / 3 / 3; 1 - gate_driver 22 / 20 / 8 / 6; 0 - inductor
3 / 5 / 4 / 2; 1 - mosfet 4 / 9 / 1 / 2; 9 - sensing_protection 16 / 12 / 7 / 3; 4 -
standards_safety 15 / 6 / 1 / 1; 0 - thermal 4 / 10 / 1 / 2; 2. The inductor area is the
only one where the design method came from outside the knowledge base (one
external-method row); the thermal and mosfet areas carry the highest share of adapted
entries because SKILL-006 and the TIDA thermal model were written for a soft-switched
converter at 40 C ambient.

Reading of the statistics: the rules were all touched, but 23 human-review and the
"direct" labels that the verifiers downgraded to adapted (KR-CAP-002 output, KR-GD-006,
KR-GD-011, KR-GD-012, KR-PR-002 bus UVLO, KR-CAP-003) mean the 41.8 % direct share in the
trace overstates literal applicability by roughly six rows; the table in section 3 gives
the corrected position.

## Verification status and open items

Analytically checked in this document: the row, applicability, coverage, query and
verdict counts (computed by script from knowledge_trace.json in this session); the
`--get PE-PCB-001` ("unknown id") and `--get REF-WS-PRD-04814` (record returned) tool
behaviour; the absence of `.cache/references` on this host; the console-encoding
behaviour at code page 936. All design numbers quoted in sections 2-5 carry the
verification level of the baseline record they come from (fetched-datasheet for
UCC21710, UCC14141, AMC1311, TMCS1133, C4MS025120K, TDK B32776, Bergquist TSP, Vishay
NTCALUG01A; manufacturer-page for logic parts and lifecycle statements; search-snippet for
the CGA9P MLCC, Samtec, G9EA-1 variants, KLKD I2t, C4MS stock; analytically-checked for every
derived quantity). Simulated: nothing in this document; the knowledge base itself
contains no simulation-verified or hardware-validated item.

Unverified: UCC14141-Q1 working-voltage figure across three sources (item 2); UCC14141 SOA
at 10.8 V / 19 V and certificate status; TMCS1133 OC response rows and TI product-page
discrepancy; CGA9P DC-bias curve and lifecycle; Fischer LAM 5 D K 100 12 datasheet; KLKD
melting I2t; Magnetics orderable code; standards values not read from a licensed copy;
whether the component-record cache paths are valid on a host that ran `acquire`.

Human review: every KR-ISO-002 distance and the 4 kV vs 2.5 kV impulse basis; the SGND-to-PE
bond (A-23); KR-PR-001 by destructive short-circuit test; KR-GD-004 DESAT values on hardware;
KR-TH-002 pad voltage rating; KR-TH-003 thresholds; KR-IS-004 closure through CR-12; the
G9EA-1 coil-to-contact insulation; the 21 knowledge-base proposals of section 6, none of
which has been applied. Items this document could not resolve: the UCC14141-Q1 isolation
figure conflict; the exact number of distinct misuse findings (verifiers mixed "no misuse
found" statements into the same list); and whether the APWM-polarity and RLIM-sink items
should become rule-level entries (KR-level) or stay inside the block and component
records - proposed as record corrections here.
