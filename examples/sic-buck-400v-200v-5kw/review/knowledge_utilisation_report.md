**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# Knowledge utilisation report - V2 SiC synchronous buck (400 V -> 200 V, 5 kW, 50 kHz; power board + TMS320F28335 control board)

Audit of how the engineering knowledge system shaped the V2 design, organised by design decision. For each significant decision it states the engineering problem, the AIPE Skill retrieved, the rule applied and its applicability class, the manufacturer reference behind it and what was deliberately not copied, the effect on the circuit or PCB actually built, the verification performed, and the resulting status (analytically checked, simulated, ERC-verified, pending the PCB phase, unverified, human review). Knowledge retrieved but not applicable, knowledge applied wrongly and corrected by verification, and knowledge-base defects are reported in sections 4 to 6. The companion [knowledge_application.md](../design/knowledge_application.md) is organised by skill and rule and is not repeated here.

## 1. Purpose, method and evidence base

**Purpose.** The central V2 experiment is whether manufacturer-derived knowledge (V0 system: 6 skills, 43 rules, 13 circuit blocks, 19 component records, 4 reference designs, 26 evidence checks; [knowledge/README.md](../../../knowledge/README.md)) improves autonomous design quality. Every item carries a validation status of `reference-derived` or `analytically-checked`; the README states that nothing in it is simulated or hardware-validated. This report therefore judges knowledge *use* and keeps it apart from knowledge *truth*.

**Retrieval.** Ten research agents, one per design area, queried the lexical BM25 interface (`PYTHONIOENCODING=utf-8 python -m automation.knowledge.query "<question>" --json --limit 8`), read records with `--get <ID> --json` and read skill and reference-analysis texts directly. Each research record (`design/research/<area>.json`) logs `knowledge_queries` (command, top hits) and `knowledge_used` (id, applicability label, `how_applied`). The trace regenerated for this audit on 2026-10-10 ([knowledge_trace.json](../design/knowledge_trace.json), [knowledge_trace.md](../design/knowledge_trace.md); `python -m automation.scripts.knowledge_trace`) holds 91 query entries (74 searches, 11 `--get` reads, 6 direct reads) and 317 citation rows over 96 distinct ids. Every run on this Windows host needed `PYTHONIOENCODING=utf-8` (code page 936).

**Application classes.** Per the README ("respect applicability and exclusions, surface human-review-requirement rules instead of deciding them"): **direct** = applied as written inside its conditions; **adapted** = a condition extended or a value re-derived, reason stated; **not applicable** = scope excludes the case; **human review** = a human-review-requirement rule or a rule whose own verification method is human review. Labels in this report are the position *after* verification (verifier downgrades applied).

**Verification layers.** (1) Two verifiers per area, twenty reports ([research/verify_*.json](../design/research/)): an *engineering recompute and applicability* lens and a *source fact-check* lens, each with verdict, `checked_items`, `recomputed`, `knowledge_misuse`, `required_changes`; all twenty verdicts are `confirmed-with-corrections` (105 misuse entries including explicit "no misuse found" statements; 223 required changes). (2) The orchestrator baseline [design_decisions.json](../design/design_decisions.json) (schema 4) resolves them into CR-01..CR-26 and governs every downstream artefact. (3) `automation/scripts/calculate_sic_buck.py` -> [calculations.json](../design/calculations.json): 250 registered inputs, 19 invariants (all PASS), 58 baseline cross-checks (57 agree, 1 explained). (4) The ngspice campaign ([simulation_report.md](../simulation/simulation_report.md), [campaign_summary.json](../simulation/results/campaign_summary.json)): 20 transient runs + 4 parasitic cases, exact numpy cross-check within 0.15 %. Native KiCad ERC ran five times (two power, three control), all passed with zero findings ([verification/erc](../verification/)); current manifests `20261010T070357Z-erc-a2f64724` (power) and `20261010T071810Z-erc-b207ac59` (control). The [consistency_review.md](../design/consistency_review.md) aligned nine documents to the baseline.

**Pending from the PCB phase.** No `.kicad_pcb`, no DRC (`verification/drc/` absent), no layout metrics (checker `automation/verification/check_sic_layout.py` and [layout_spec_power.json](../verification/engineering_checks/layout_spec_power.json) / `layout_spec_control.json` exist, metric files do not), no `pcb_rule_review.md`, no export manifest, no release. [verification-summary.json](../verification/verification-summary.json) therefore shows `status: failed` with eight "missing" problems - missing artefacts, not failing checks. Layout-dependent decisions are marked **P** and close through `verification/pcb_rule_review.md` and the regenerated `verification-summary.json`.

**Status marks.** **A** analytically checked (both verifiers and/or calculate_sic_buck.py); **S** simulated (behavioural ngspice, no device physics); **E** ERC-verified (the implementing circuit exists in a zero-finding schematic); **P** pending PCB phase; **U** unverified parameter; **H** human-review item. Each decision gets all applicable marks and one primary mark (section 8).

**Evidence read.** All inputs named in the task were readable: the baseline, knowledge_application.md, the regenerated trace, ten research records and twenty verify reports, calculations.json, simulation report and campaign summary, five ERC manifests, circuit_power.json (237 items) and circuit_control.json (207 items), [component_records.json](../components/component_records.json) (65 records), [magnetic_record.json](../components/magnetic_record.json), consistency_review.md, [v1_v2_comparison.md](v1_v2_comparison.md), the knowledge base (README, six skill texts, `rules/engineering_rules.json`, 13 blocks, 19 component records, four reference records and analyses, evidence checks), `docs/knowledge-system.md`, `automation/verification/pcb_rules.json`. Three observations: knowledge_trace.md is a bare table without banner; the simulation ran before calculations.json existed, so the one-to-one check between them is still open; the layout specs use placeholder designators (U1..U8) that differ from the schematic (U1/U3 drivers, U2/U4/U5 bias, U6/U7 AMC1311, U10 TMCS1133) and must be adjusted, as the spec notes.

## 2. Retrieval record

### 2.1 Queries run (condensed from `knowledge_queries`)

| Area | Searches / gets / reads | Representative questions | Hits that shaped the record | Queries with no applicable hit |
|---|---|---|---|---|
| assumptions | 11 / 2 / 1 | ambient and derating; input range / UVLO; output ripple; inductor ripple; efficiency; copper and spacing; SELV crossings; commissioning | SKILL-006, KR-TH-001..003, SKILL-003, KR-CAP-001/002, KR-ISO-001, SKILL-001, REF-TI-TIDA-010054 | inductor ripple / saturation |
| standards_safety | 6 / 1 / 0 | insulation coordination; slots and net classes; discharge and labels; fuse I2t vs DESAT; heatsink PE, Y capacitors; copper and vias | KR-ISO-001..004, KR-SN-001, KR-PR-001, KR-TH-002, KR-PCB-006, SKILL-002 | discharge / labels |
| mosfet | 7 / 1 / 1 | voltage margin; V_GS limits; SC withstand; thermal path; device-choice scope; commutation loop; dead time | KR-GD-001, KR-PR-001, KR-TH-001/002, KR-PCB-004, SKILL-001 (device choice out of scope), SKILL-006 | voltage margin (SKILL-003 and a film capacitor ranked first) |
| gate_driver | 5 / 1 / 1 | driver IC; bias power and C_iso; R_G, blanking, soft turn-off, interlock; layout; negative rail | SKILL-001, SKILL-004, CB-GD-001, CMP-UCC21710-Q1, KR-GD-001/004/005, KR-IS-001..003, REF-WS-PRD-04814 | none |
| inductor | 8 / 1 / 0 | powder-core design; temperature rise; placement vs exhaust; 25 A copper; Steinmetz; litz / AWG; terminals | KR-PCB-006, SKILL-006, KR-TH-001 (by analogy) | powder core, Steinmetz, wire (SKILL-003 exclusion and CMP-750319177 were false hits), terminals |
| capacitors | 5 / 1 / 0 | film RMS ripple; HV MLCC and loop; bleeder spacing; output transient and lifetime; derating | SKILL-003, KR-CAP-001..003, KR-PCB-004/006, KR-ISO-002..004, SKILL-006 | output transient / lifetime (SKILL-003 exclusion only) |
| controller_aux_interconnect | 9 / 1 / 1 | eFuse; PWM buffer / latch / RS-422; supplies and sequencing; connector and grounds; fault handling; dead time | CMP-TPS2640, CB-PR-001, CB-GD-003, KR-GD-008/009, KR-PR-002/003, CMP-UCC14141-Q1, CB-IS-002 | control supplies / sequencing |
| sensing_protection | 11 / 1 / 0 | Hall sensing and OC; AMC1311 ladders; latched trips; NTC via AIN/APWM; precharge; fuse; discharge; TVS/MOV; probes; SDFM absence | CB-SN-001/004, CMP-TMCS1133, CMP-AMC1311, SKILL-005, KR-SN-001..005, CB-PR-002, KR-PR-002 | precharge, fuse I2t, discharge, HV MOV |
| thermal | 7 / 1 / 1 | shared sink and pad; NTC to T_J; hot-spot placement; grounded-sink creepage; IPC copper; fan failure; TI's parts | SKILL-006, KR-TH-001..003, CB-PR-002, KR-ISO-002, KR-PCB-006, TIDA decision 9 | fan failure |
| architecture | 5 / 1 / 1 | partition; driver adjacency vs driver card; barrier keep-outs and slots; connector at the edge; gate/Kelvin stack-up | TIDA decision 10, SKILL-002, KR-PCB-001/003/005, KR-ISO-001..004, KR-GD-008, CB-GD-003 | none |

By this audit's count about one in six of the 74 searches (12-14) returned no applicable top hit; in each case the agent recorded the gap and used an external method or its own derivation rather than forcing a knowledge item onto the problem (clearest in D-11). The hit statistics in knowledge_application.md section 1 (REF-TI-TIDA-010054 in 38 searches, SKILL-001 in 30, REF-WS-CGD1700HB2M-UNA in 29, SKILL-003 in 28) show that retrieval is dominated by the one system-level reference - a property of the V0 corpus. Re-checked in this audit: `--get PE-PCB-001` still answers `unknown id` (the project PCB rules live in `docs/pcb-design-rules.md` and `automation/verification/pcb_rules.json`), `--get REF-WS-PRD-04814 --json` does return the record (so the architecture fact-check's "not retrievable" statement is a verifier error), and a magnetics search ("powder core inductor design for a 25 A output choke") returns SKILL-004, CB-IS-003 and the SKILL-003 exclusion - confirming the gap.

### 2.2 Coverage statistics (recomputed from knowledge_trace.json)

| Measure | Value |
|---|---|
| Citation rows | 317 (gate_driver 56, assumptions 49, sensing_protection 42, architecture 33, controller 32, mosfet 25, capacitors 23, standards 23, thermal 19, inductor 15); 96 distinct ids; 312 resolve, 5 do not |
| Rows by type | rule 138, skill 42, reference 27, block 22, component 20, project rule 22, project precedent 1, external method 1, cited-in-text-only 44 |
| Applicability of the 273 labelled rows | direct 114 (41.8 %), adapted 101 (37.0 %), not applicable 35 (12.8 %), human review 23 (8.4 %) |
| Per area (direct / adapted / n.a. / review) | architecture 11/12/1/1; assumptions 15/11/3/1; capacitors 10/5/6/2; controller 14/11/3/3; gate_driver 22/20/8/6; inductor 3/5/4/2; mosfet 4/9/1/2; sensing 16/12/7/3; standards 15/6/1/1; thermal 4/10/1/2 |
| Coverage | skills 6/6; rules 43/43; blocks 13/13 (CB-SN-002 as a text citation only); components 16/19 (unused: CMP-GCM31CR71C106KA64L, CMP-AMC1306M05, CMP-AMC1336); references 4/4; project rules 10/8 (compound ids) |
| Rules only ever not applicable | KR-CAP-004, KR-PE-001, KR-SN-003, KR-SN-004 |
| Rules with a human-review label | KR-GD-004, KR-GD-010, KR-IS-004, KR-ISO-002, KR-PR-001, KR-PR-003, KR-SN-001, KR-TH-003 |
| Validation status of cited items | reference-derived 160 rows, analytically-checked 42, no status 115 (references, project rules, cited-only); nothing simulation-verified or hardware-validated |
| Unknown ids | `PE-PCB-001..008` (x2), `PE-PCB-005/PE-PCB-007/PE-PCB-008`, the V1 precedent, the Magnetics catalogue - all declared non-index sources or compound ids |
| Verdicts | 20/20 confirmed-with-corrections |

The 41.8 % direct share overstates literal applicability: the verifiers downgraded at least six rows (KR-CAP-002 output capacitor, KR-GD-006, KR-GD-011, KR-GD-012, KR-PR-002 bus UVLO, KR-CAP-003), and the thermal and MOSFET areas carry the highest adapted share because SKILL-006 and the TIDA thermal model were written for a soft-switched DAB at 40 C. The whole rule set was touched, but one area's method (magnetics) came from outside it.

## 3. Decision register

Each entry: problem; knowledge retrieved and rules applied (consolidated applicability); reference - transferred / not copied; influence with values and reference designators from [circuit_power.json](../design/circuit_power.json) and [circuit_control.json](../design/circuit_control.json) (power board unless stated); verification; status and evidence.

### D-01 MOSFET voltage class and part

- **Problem.** Device class and part for 360-440 V (460 V OVP, 480 V survival), 25 A / 27.5 A for 10 s, hard-switched at 50 kHz, within a 2 % loss allowance.
- **Knowledge and rules.** SKILL-001 (device choice excluded: "Transistor Database scope"), SKILL-006 EC-019/020. KR-GD-001 direct as selection filter (rails vs -10/+23 V read from the C4MS datasheet, not the Gen-3 +19/-8 V example); KR-TH-001 adapted (50 C, R_thJC 0.41 K/W); KR-PR-001 direct hard constraint (no published withstand time - destructive test); KR-PCB-004 adapted (25/35 nH are agent assumptions); KR-GD-006 adapted (same-supplier fallback; relabelled by both verifiers).
- **Reference.** TIDA device choices (utilisation 0.67 / 0.56) used as evidence only - the 900 V part is obsolete, the DAB soft-switched, TI states no derating rule. Not copied: 2 ohm, 0.1 K/W pad, 40 C, 50/69 W limits.
- **Influence.** Q1 (tab = VIN) and Q2 (tab = SW) = C4MS025120K TO-247-4 Kelvin source (Rev. 2 Dec 2025 fetched; 28 mohm typ at 15 V, Q_G 125 nC); utilisation 42-46 % including the 62-88 V overshoot allowance; 650 V C3M0015065K rejected at 77-84 %; fallback C3M0021120K (+8 W); pair losses 46.7-52 W at 400 V / 25 A / 150 C (k_RG 1.3-2.0).
- **Verification.** Both verifiers recomputed losses, utilisation and thermal path; adopted: k_RG range, HS E_oss (~1 W), "37 mohm max" relabelled as scaled, 27.5 A shares renormalised, PRD-08296 cited separately, Gen-4 750 V check opened. Invariants utilisation 0.508 <= 0.8 and hottest T_J 143.1 C <= 150 PASS; simulation reproduced conduction (29.7-29.9 W vs 30.6 W) and dead-time (2.89 W) losses and peaks within 0.1 A; ERC clean.
- **Status.** A, S, E; U (switching energies at 400 V, 15 V-gate R_DS(on) maximum, Arrow-only stock); H (80/90/70 % utilisation limits, withstand by test). Primary **A**. Evidence: [mosfet.json](../design/research/mosfet.json), verify_power_semiconductor_*, calculations.json `mosfet`, simulation_report.md 5.1.

### D-02 Single device per position versus parallel

- **Problem.** One TO-247-4 per position (seed) or two in parallel to reduce conduction loss.
- **Knowledge and rules.** No item covers paralleling discretes (SKILL-001 known limitation). Method only: SKILL-006 principle 3, KR-IS-001 (gate power doubles), KR-PCB-004 - all adapted.
- **Reference.** TIDA uses one TO-247-4 per switch; a consistent pattern, nothing copied.
- **Influence.** Single C4MS025120K per position; paralleling documented as the efficiency alternative (-15 W; the 31.4 W pair figure is a lower bound because E_on and E_rr rise with doubled C_oss / Q_rr).
- **Verification.** MOSFET engineering verifier recomputed; efficiency roll-up 98.55 % typical / 98.12 % bounded with auxiliaries vs the 98.0 % target (invariants PASS, no margin at the bounded worst case).
- **Status.** A; H (efficiency budget allocation, 97.5 % floor). Primary **A**. Evidence: mosfet.json "One vs two devices", calculations.json `efficiency`.

### D-03 Gate rails +15 V / -4 V

- **Problem.** Rails plus tolerance and transients inside the device maxima, turn-off margin against parasitic turn-on, compatible with the C3M fallback.
- **Knowledge and rules.** SKILL-001 principle 3 / step 3, SKILL-004 step 4, PRD-04814 decision 1, CB-IS-004 (not needed). KR-GD-001 direct (+15.0 / -4.0 V +/-1.3 %, extremes about +15.7 / -4.6 V at zeta 1.6-3.8 vs -10/+23 V C4MS and -8/+19 V C3M); KR-GD-005 direct - its exclusion lists "buck", but the synchronous buck is a complementary half bridge (stated explicitly in `why_negative` after the fact-check asked); KR-GD-006 adapted (+18 V C4MS-only option, FBVDD 127 k); KR-IS-005 direct (regulated module, no post-regulation).
- **Reference.** PRD-04814 levels (+15 V, -3 to -4 V, +/-5 %) as method; its "0 V turn-off usable for buck" note overridden; the coincidence of +15/-4 V with the TIDA configuration declared.
- **Influence.** UCC14141 dividers 107 k / 16.2 k (VDD-VEE 19.0 V) and 9.76 k / 16.2 k (COM-VEE 4.0 V), 0.1 %, 330 pF C0G across the bottom resistors: R29-R32 / C34, C35 (U2) and R47-R50 / C54, C55 (U4).
- **Verification.** Dividers recomputed by both verifiers (19.01 / 4.006 V); calculations.json `gate_drive.rails_check`; ERC clean; the rule's measurement (isolated probe at the device side of R_G, TP1/TP2) awaits hardware.
- **Status.** A, E; H (V_GS overshoot and off-state measurement). Primary **A**. Evidence: [gate_driver.json](../design/research/gate_driver.json), verify_isolated_sic_gate_driver_*.

### D-04 Driver IC with DESAT and Miller clamp

- **Problem.** Isolated driver with hardware short-circuit protection, soft turn-off, active clamp, CMTI above the 110-122 V/ns turn-off dv/dt estimate, reinforced isolation at 440 V DC.
- **Knowledge and rules.** SKILL-001 step 4 (instances UCC21710-Q1 in TIDA and CGD1700; UCC23514 in CGD15SG00D2), CB-GD-001, CB-GD-002, CMP-UCC21710-Q1, CMP-UCC23514. KR-PR-001 direct (product design: UCC23514 rejected, no DESAT); KR-SN-001 direct (5.7 kVrms, VIOWM 1500 Vrms, > 8 mm); KR-GD-002 direct (split outputs make CB-GD-002 unnecessary); KR-GD-011 adapted (400 mA soft turn-off; module-scoped rule; UCC21732-Q1 two-level turn-off not chosen).
- **Reference.** One driver per switch (TIDA decision 4, CGD1700 decision 1) adopted; CMP-UCC21710-Q1 re-verified against SLUSDH8D (UVLO 12 V, deglitch 120 ns, skew 30 ns added). Si8285 and UCC5870-Q1 fail the CMTI margin at the peak.
- **Influence.** U1 (HS) and U3 (LS) UCC21710QDWRQ1, VCC 3.3 V; CMTI margin 1.25x instantaneous / 3.1x average.
- **Verification.** Fact-check confirmed every record parameter; ERC clean; the dv/dt envelope is an estimate until the double-pulse test.
- **Status.** A, E; U (turn-off dv/dt); H (CMTI acceptance). Primary **A**. Evidence: gate_driver.json candidates, verify_isolated_sic_gate_driver_*_factcheck.

### D-05 Gate resistors and the Miller-clamp requirement

- **Problem.** Starting R_G,on / R_G,off for a 2.5 A/ns edge; whether parasitic turn-on makes the clamp mandatory.
- **Knowledge and rules.** SKILL-001 principles 5-6, step 5; CGD15SG00D2 decision 6 (clamp path length). KR-GD-002 direct (R_ON 10 -> 6.8 ohm, R_OFF 3.3 ohm; peaks 1.26 A source / 3.06 A sink vs +/-10 A); KR-GD-003 adapted and raised to REQUIRED; KR-GD-007 direct (10 k at the device side of R_G); KR-GD-010 human review (DNP 1 ohm + 470 pF); KR-GD-012 adapted (no Zener; module-scoped).
- **Reference.** Not copied: TI 2 ohm, Wolfspeed 1 ohm 2512, CGD15SG00D2 10 ohm (coincidence declared), 47 k pull-down (10 k vs 47 k conflict preserved).
- **Influence.** R19/R20 (U1), R37/R38 (U3) ERJ-P08F10R0V / ERJ-P08F3R30V 1206 anti-surge; CLMPI links R21/R39 (0 ohm, path <= 15 mm, same Kelvin return); discharge resistors R22/R40 10 k; probe loops TP1/TP2 (CR-11); E_on penalty +1.9 W at 6.8 ohm / +3.8 W at 10 ohm in the efficiency budget.
- **Verification.** The main misapplication of the run: the MOSFET agent (1.3 V, small-signal C_rss) and the gate-driver agent (0.6-1.0 V, capacitance divider) both concluded "inherently immune", invoking the KR-GD-003 exclusion in effect; both engineering verifiers rejected the bound. Baseline: charge-based estimate (Q_gd 20-27 nC into C_gs 3.08 nF through 5.6 ohm) gives 4.5-5.2 V excursion, gate +0.5 to +1.2 V vs V_GS(th),min 2.0 V (25 C; hot minimum unpublished); calculations.json widens it to 3.6-7.0 V - the clamp is mandatory either way. ERC clean.
- **Status.** A, E; H (double-pulse R_G tuning, off-state V_GS per PRD-09301 6.1, RC population). Primary **A**. Evidence: verify_power_semiconductor_*_engineering, verify_isolated_sic_gate_driver_*_engineering, calculations.json `mosfet.parasitic_turn_on`.

### D-06 DESAT trip and blanking versus short-circuit withstand

- **Problem.** Trip above the 32.0 A overload peak with false-trip margin, blanking above the turn-on ringing, total response shorter than an unpublished withstand time.
- **Knowledge and rules.** CB-GD-001 (EC-001/EC-002 formulas), KR-GD-004 (human review; conflict 6.4 V / 1 us vs 6.7 V / 46 ns preserved), KR-PR-001, KR-GD-011, PRD-09301 5.1, PRD-08296 (external, module data). KR-GD-004 human review - values derived from the C4MS 175 C output curve; KR-PR-001 direct hard constraint, compliance by destructive test (the standards agent's "withstand from the datasheet" wording and the MOSFET agent's "human-review" label were both corrected); KR-GD-011 adapted (fault overshoot 684 V at 460 V / 35 nH).
- **Reference.** CGD1700 network topology kept, values re-derived: 2.2 k / 4.99 k / 1.00 k / 680 pF, one US1M 1000 V instead of two US3M; the BAT42W OC clamp (CGD1700 DT5) was adopted without derivation and downgraded to DNP once the verifier showed the -0.67 V DC case does not occur dynamically.
- **Influence.** R24/R25/R26/C29/D3 (U1), R42/R43/R44/C49/D5 (U3), D4/D6 BAT42W-V DNP. Trip V_DS 3.6 V (3.2-4.0), trip current 52-85 A at 175 C, false-trip margin 1.67x typical / 1.35x max-R, blanking 288 ns (252-326) + deglitch 95-180 ns, response 0.55-1.07 us vs the 1.5 us budget.
- **Verification.** Both gate-driver verifiers recomputed and restated the margins with the R_DS(on) spread; invariant "DESAT response 1.066 us <= 1.5 us" PASS; ERC clean; not simulated (no fault model).
- **Status.** A, E; H (hardware confirmation of trip and blanking, destructive short-circuit test, Wolfspeed statement). Primary **A**. Evidence: calculations.json `desat`, verify_isolated_sic_gate_driver_*.

### D-07 Isolated bias module per position and its power budget

- **Problem.** Floating bipolar rails per position from 12 V +/-10 % at 50 C board ambient, low C_iso, with the recorded KR-IS-001 factor-2 conflict.
- **Knowledge and rules.** SKILL-004 steps 1-7; CB-IS-001..004; CMP-UCC14141-Q1, CMP-UCC25800-Q1 + CMP-750319177, CMP-R12P21503D, CMP-MGJ2D122005SC; PRD-04814 decision 3. KR-IS-001 direct with both forms (Wolfspeed 0.119 W, TI Eq. 30 0.24 W per channel; module budgets 0.32 / 0.32 / 0.40 W vs 1.5 W at 10.8-13.2 V and TA <= 85 C); KR-IS-005 direct; KR-IS-003 adapted (D-09).
- **Reference.** TIDA module-per-switch adopted; CB-IS-003 rejected - RECOM -3 V / Murata -5 V unregulated and, per the cached RxxP2xx datasheet (REV 9-2024) found by the fact-check, basic insulation at 250 Vrms (the record omits this); CB-IS-001 LLC (C_iso 0.68 pF) kept as fallback; TI RLIM 1 k / 600 ohm not adopted (R33/R51/R57 1 k placeholders, human review).
- **Influence.** U2 (HS), U4 (LS), U5 (sensing, D-08) UCC14141QDWNRQ1 (custom DWN-36 footprint); output 2 x 4.7 uF + 4.7 uF per module (C36/C37/C39, C56/C57/C59, C66/C67/C69); 0.45 A at 12 V for three modules.
- **Verification.** Misapplications corrected: the gate-driver agent dropped the factor-2 conflict (restored by three verifiers) and misread the rating conditions; the controller agent used a flat 1.0 W unconditionally. Baseline: 1.5 W (10.8-13.2 V, TA <= 85 C), 1.0 W (8-18 V), 2.5 W absolute maximum, SOA still to read. Three sources give three working-voltage figures (1414 Vpk / 1000 Vrms / 1500 Vrms) - unresolved (section 6). ERC clean.
- **Status.** A, E; U (SOA at 10.8 / 19 V, CIO legibility, certifications "planned" in SLUSF10B); H (RLIM). Primary **A**. Evidence: gate_driver.json, verify_isolated_sic_gate_driver_*, verify_controller_*_engineering, calculations.json `gate_drive.bias`.

### D-08 Dedicated sensing-island supply (CR-12)

- **Problem.** Isolated 5 V for the two AMC1311 high sides (GND1 = PGND); TIDA shares the LS gate module through a TLV76050.
- **Knowledge and rules.** SKILL-005 principle 7, SKILL-004 principle 6, KR-IS-004 (human review), CB-IS-002 optional LDO, TIDA decision 7 (recorded as provided but untested by TI). KR-IS-004 human review -> resolved by CR-12; KR-IS-001 direct (0.4 W).
- **Reference.** The TIDA pattern was adopted structurally by the gate-driver and sensing agents (R_pre 270 ohm, 16.9 / 23.1 mA). The gate-driver engineering verifier showed from SLUSF10B that the LDO return must be sunk by the COM-VEE regulator through RLIM, requiring RLIM <= 57-110 ohm - outside the RLIM qualification (0.125 A rms, 16 % run time). Rejected; documented as the alternative.
- **Influence.** U5 configured VDD-VEE 15 V (R53 80.6 k / R54 16.2 k), COM-VEE 5.0 V (R55/R56 16.2 k), VEE = PGND, COM = 5V_ISO feeding U6/U7 VDD1 directly (~20 mA); CM choke L4; PG pull-up R58.
- **Verification.** Analytical sink check (verifier); calculations.json: sourcing 20 mA through RLIM needs RLIM <= ~470 ohm and dissipates ~0.2 W continuously - again outside the 16 % run-time qualification, so the feasibility of this configuration is itself open. ERC clean.
- **Status.** A, E; U/H (feasibility of the sourcing configuration; RLIM). Primary **A**. Evidence: verify_isolated_sic_gate_driver_*_engineering, CR-12, calculations.json open items.

### D-09 Common-mode choke and isolation capacitance

- **Problem.** Common-mode current i = C_iso dv/dt into the SELV side at 110-120 V/ns; EMI path through the bias input.
- **Knowledge and rules.** SKILL-004 principles 2-3; PRD-04814 decision 2; CGD1700 decision 5; CGD15SG00D2 decision 3. KR-IS-002 direct; KR-IS-003 adapted (CIO < 3.5 pF not legible in the extraction, 5 pF bound: 0.72 A including the driver; LLC 0.08-0.2 A; RECOM 1.2-1.3 A).
- **Reference.** The Wuerth 744226S is the CGD1700 choke - a declared reuse of a reference part; input capacitance re-derived (3 x 10 uF 25 V X7R 1210 for >= 20 uF at 13.2 V; verifier correction from 2 x 10 uF, CR-19); choke-capacitor order per the rule.
- **Influence.** L2/L3/L4 744226S, 3 x 10 uF + 100 nF per module, on the SELV side of each barrier part.
- **Verification.** i_CM analytical; 744226S datasheet fetched; the rule's layout review (choke-capacitor order) and the CM-current measurement are pending; ERC clean.
- **Status.** A, E; P (component order); U (CIO); H (EMI pre-scan). Primary **A**. Evidence: gate_driver.json "Common-mode current", verify_isolated_sic_gate_driver_*_factcheck.

### D-10 Hardware interlock, fault latch and run-permit logic

- **Problem.** Shoot-through prevention independent of firmware; latched faults with explicit reset; UVLO lock-out; run permits; the mezzanine interface.
- **Knowledge and rules.** SKILL-001 principle 9 / step 8; CB-GD-003; CGD1700 decisions 3-4; TIDA decision 10 (SN74LVC126A buffers); CMP-UCC21710-Q1. KR-GD-009 direct (IN+/IN- cross-wiring of U1/U3; dead time in the ePWM only: 300 ns programmed, 250 ns target, 150 ns minimum, CR-07); KR-PR-002 direct for the driver subsystem, adapted for the 400 V bus UVLO ladder; KR-SN-005 direct (OC_N to TZ2 and to the latch); KR-GD-008 adapted (D-20).
- **Reference.** CGD1700 fault-combining and reset-filter patterns with derived values (100 ohm / 100 pF, not 120 ohm / 56 pF); RS-422 not used.
- **Influence.** Control board: U7 SN74LVC1G74DCTR latch (D = 1, CLK = ARM, CLR_N = combined fault, Q = ARMED = FAULT_N -> TZ1); U8-U10 3 x SN74LV21APWR (CR-17, CR-26: 13 latched inputs; run-permit group UVLO_N, RDY_H, RDY_L, ARMED -> GATE_EN); U11 SN74LV04APWR; U6 SN74LVC2G08 PWM gating; 10 k pull-downs R40-R42 (GPIO0-11 lack reset pull-ups); E-stop loop J6. Power board: receiving networks R17/C20/R18, R35/C40/R36 and R67-R70 (100 ohm / 100 pF / 10 k). Restart only by operator after DESAT/OC.
- **Verification.** ERC zero findings on both boards is the verification that directly tests this decision (connectivity of the fault groups and the mezzanine pin table, verified pin for pin by the consistency review); latency <= 240 ns analytical; the wired-OR node dropped (CR-17); the non-existent SN74LVC1G74DCKR suffix caught (CR-19); the asymmetric UVLO hysteresis (R59 21.5 k, C54 DNP) flagged for simulation or firmware. Fault-injection and both-inputs-high tests await hardware.
- **Status.** E, A; H (fault injection, interlock test, UVLO hysteresis). Primary **E**. Evidence: ERC manifests, [controller_aux_interconnect.json](../design/research/controller_aux_interconnect.json), verify_controller_*.

### D-11 Inductor custom design (no knowledge coverage)

- **Problem.** 220-300 uH at 25-32 A with 30 % ripple, soft saturation to 41 A, acceptable loss and hot spot at 50 C; no orderable standard part (13 families searched).
- **Knowledge and rules.** No skill exists; eight searches returned capacitor and bias-transformer records. By analogy: KR-TH-001 adapted (P_max 28.7 W vs 19.8 W typical / 23-26 W bounded; the 125 C winding limit is an added assumption, not rule content); SKILL-006 step 3 as a flagged recommendation (CR-14: inductor in the fan stream); KR-PCB-006 direct with IPC-2221 sizing; KR-ISO-002 (4 mm terminal spacing); KR-TH-002/003 not applicable / human review.
- **External method (proposed skill).** Magnetics Powder Core Catalog 2024: LI^2 selector, %u = 1/(a + b H^c) (0.01, 6.413e-8, 2.291), Steinmetz (246.54, 2.218, 1.311), DC-magnetisation fit, dT = (P_mW / A_cm2)^0.833; 0058192A2 datasheet (rev 10/6/2021).
- **Influence.** L1 = 2 x 0058192A2 High Flux 60u stacked, 34 T AWG 10: L 319 / 272 / 248 / 210 uH at 0 / 25 / 31.6 / 41 A, worst 235 / 215 / 175 uH; I_sat(30 %) 37.3 / ~35 A; DCR 12.2 / 16.0 mohm; loss 16.4 W (400 V / 25 A), 19.8 W overload, 23-26 W bounded; hot spot 110-120 C in still air -> forced air mandatory, thermocouple acceptance <= 110 C; 632 g in a potted cup on M4 standoffs; footprint `AIPE:L_Toroid_HF58x2_D69_H48_P25.4`; record AIPE-MAG-L1-SICBUCK-5KW-V2.
- **Verification.** Both verifiers recomputed everything and fetched the datasheet and catalogue (fits match; dT correlation and cost table unverifiable; "+/-30 %" wrongly attributed to the catalogue; SKILL-003 exclusion misquoted; "stricter than vendor I_sat" claim removed; datasheet-maximum core loss 1.44x added). Simulation: ripple 6.51 / 7.35 / 8.03 App, peaks within 0.1 A, worst 9.30 App / 32.15 A at 235 uH, DCR loss 10.06-12.22 W (fixed L, no core loss). Invariants saturation 0.765 / 0.743 >= 0.70, flux 0.804 T, thermal limit 19.9 W <= 28.7 W PASS.
- **Status.** A, S, E; U (still-air correlation, worst core loss, orderable code 0058192A2 vs C058192A2, winding house, acoustic noise); H (custom-build acceptance). Primary **A**. Evidence: [inductor.json](../design/research/inductor.json), verify_output_inductor_*, [magnetic_record.json](../components/magnetic_record.json), simulation_report.md 5.

### D-12 DC-link film plus HV ceramic two-tier bank

- **Problem.** Input capacitance for 2 % ripple with the pulsating buck input current; RMS rating at 50 kHz; HF commutation tier; 440 V / 480 V.
- **Knowledge and rules.** SKILL-003 steps 1-4, 6 (written for DAB/PSFB); CMP-B32716H8306K000 / H1156K000 (no datasheets in the KB), CMP-CGA9P1X7T2J474M250KC, CMP-2220Y1K00474KETWS2, CMP-C1812V104KDRACTU; TIDA decision 2. KR-CAP-001 adapted (dQ = D(1-D) I_o T_s = 137.5 uC -> C_in >= 17.2 uF -> 2 x 20 uF, 3.9 Vpp at 27.5 A); KR-CAP-002 direct (6.92 A per part vs 14.5 A; ESR flat to 70 kHz verified for Vishay only - extrapolation noted); KR-CAP-003 adapted (10 x 0.47 uF 630 V within 5 / 15 mm, 60 % DC-bias loss assumed; ring ~670 kHz, ~1.1 W, 0.75-1.4 A rms per MLCC added by the verifier); KR-CAP-004 not applicable.
- **Reference.** Two-tier pattern and dQ method transferred; not copied: 30 / 60 uF, 5 V ripple, 14 MLCC, B32716 parts, 630 V / 1 kV ratios; film series changed to TDK B32776 after fetching its datasheet; same MLCC family at ratio 0.70 (TI 0.79), derived count.
- **Influence.** C11/C12 B32776G8206K000 20 uF 800 V; C1-C10 CGA9P1X7T2J474M250KC (rows <= 5 / <= 15 mm); damping leg C16/C17/R12/R13 DNP; RV1 S20K385 DNP; alternates KEMET C4AQIBW5200A3JJ, Vishay MKP1848C62080JP4, Knowles 2220Y1K00474KXTWS2.
- **Verification.** 21 calculations recomputed (ESR term 44.1 -> 32 A corrected); datasheets fetched; simulation: input ripple 3.56-3.97 Vpp (limit 8 Vpp), C_in RMS 6.4-7.1 A per part; invariants PASS. The HF tier and ring are not in the lumped deck; MLCC DC bias unverified.
- **Status.** S, A, E; U (MLCC DC bias, lifecycle); P (placement, loop extraction); H (damping leg). Primary **S**. Evidence: [capacitors.json](../design/research/capacitors.json), verify_dc_link_*, simulation_report.md 5 and 8.

### D-13 Output capacitor technology and transient sizing

- **Problem.** <= 2 Vpp ripple, 12.5 A step <= 10 V in <= 5 ms, 25 A dump below the 230 V OVP, 440 V fault survivable.
- **Knowledge and rules.** SKILL-003 explicitly excludes "low-voltage converter output filters where ripple is set by an inductor current" - adapted: C >= dI_L / (8 f_s dV) (12.5 uF, not limiting) plus C >= dI / (2 pi f_c dV) -> 108 uF minimum / 120 uF nominal; KR-CAP-002 adapted (1.43 A vs 23.5 A). Both inductor verifiers noted the dropped qualifier "of low-voltage converters"; conclusion unaffected.
- **Reference.** Nothing transferable (the TIDA output is a DC link); all-film over hybrid electrolytic; lifetime modelling is outside the KB and the comparison (48,000-96,000 h) was not used.
- **Influence.** C13/C14 B32776G4606K000 60 uF 450 V; 0.25 Vpp; 7.4 V step at 2.5 kHz; dump 215-218 V vs 230 V OVP (CR-04 raised the trip from 220 V); the 2.0-2.5 kHz crossover *with an inner current loop* placed in the firmware contract.
- **Verification.** Simulation: ripple 0.16-0.22 Vpp; steps -7.54 / -7.74 / +7.80 V with 0.75-0.77 ms recovery; dump 216.2 / 215.8 V (13.8 V margin); the module single-loop PI fails (-16.2 V, 5.0 ms, 38.5 A above the OC trip) - the inner current loop is required; invariants load step 9.23 V <= 10 V, dump 220.3 V <= 230 V PASS; ERC clean.
- **Status.** S, A, E; H (controller structure vs the firmware contract's 30-40 deg margins; load-dump reverse-current policy against the 460 V input OVP with a non-sinking source). Primary **S**. Evidence: simulation_report.md 6 and 12, calculations.json `capacitors.output`.

### D-14 Bleeders, discharge time and indicator strings

- **Problem.** Discharge both banks below 60 V in a defined time with labels; a live indicator per bank; element limits.
- **Knowledge and rules.** No item covers discharge (queries returned SKILL-001, CB-GD-001, SKILL-003). IEC 61800-5-1 4.3.11 / 6.5.2 at secondary-source level (2022 edition: 4.4.9); KR-ISO-002 human review for element voltages; KR-CAP-001 parametric. The 60 s + label choice is a project decision (CR-03).
- **Reference.** None.
- **Influence.** Input R1-R3 3 x CRCW2512120KFKEG (360 k, 0.54 W, 160 V per element at 480 V) + indicator R4-R6 3 x 150 k 1206 + D1; output R7/R8 2 x CRCW2512100KFKEG (200 k) + R9/R10 2 x 100 k 1206 + D2; discharge ~20 s merged / ~36 s bleeders alone (the baseline "about 30 s" is the bleeder-only estimate - the one calculations cross-check that "differs", explained); 5 s passive option (~4.5 W) documented; labels IEC 60417-5036 + 60 s, ISO 7010 W012.
- **Verification.** Misapplications corrected: the sensing agent's 2 x 220 k 1206 string exceeded 200 V / 0.25 W per element (CR-03); the sensing agent used its own 60 / 40 uF although the capacitor result existed (48.7 / 132 uF); the standards agent left the sizing parametric and duplicated ownership. Invariants 20.3 s / 36.5 s <= 60 s PASS; the output indicator chain sees 220 V / 0.48 W per element under a 440 V high-side-short fault (calculations open item). ERC clean.
- **Status.** A, E; U (standard clauses not read from a licensed copy); H (60 s + label vs 5 s; indicator fault stress). Primary **A**. Evidence: calculations.json `capacitors.bleeders`, verify_sensing_protection_*, [standards_safety.json](../design/research/standards_safety.json).

### D-15 TMCS1133 inductor-current sensing with fast OC

- **Problem.** Isolated current measurement to a controller without SDFM and a hardware OC path faster than the ADC loop; trip above the 32.0 A overload peak and below saturation roll-off.
- **Knowledge and rules.** SKILL-005 steps 1-7; CB-SN-004; CB-SN-003 + CMP-AMC1302-Q1 (shunt, rejected: no fast OC output, loss, HV supply); CB-SN-002 / CMP-AMC1336 / CMP-AMC1306M05 (bitstream, not applicable); CMP-TMCS1133. KR-SN-002 direct (0.33 V + 0.05 V/A, full scale 53.4 A, LSB 14.65 mA); KR-SN-005 direct (OC_N -> latch -> RST_EN + TZ1, and TZ2; an output short ramps to the trip in 4.4-7.3 us); KR-SN-003/004 not applicable; KR-SN-001 direct (950 Vrms / 1343 VDC per SBOSAG0E; TI product page 600 Vrms - datasheet governs, TI confirmation open).
- **Reference.** TIDA Hall-with-OC pattern; not copied: 45 / 70 A, 8.2 k / 1.2 k, the B1 variant (the record's TMCS1133B1QDVGR does not exist; A suffix corrected); V_OC 0.750 V from a REF3125 via 2.32 k / 1.00 k (R79/R80, SBOSAG0E Eq. 21) = 37.5 A; sensor in the DC output path.
- **Influence.** U10 TMCS1133C2AQDVGR (custom DVG-16 with fused bar pads); U9 REF3125 on the power-board SELV strip (CR-16); R81 OC_N pull-up; trip chain 546 ns; margin 32.0 A vs 33.7 A worst low bound; worst trip peak ~42.6 A at 175 uH (CR-05: soft roll-off).
- **Verification.** Both sensing verifiers recomputed; the fact-check located the SBOSAG0E rows (100 / 250 ns, +/-2 / +/-10 %) but the baseline still says "rows to quote"; simulation peaks 32.15 A (worst steady), 33.1 A (5 ms soft-start artefact), 38.5 A (module PI) vs 37.5 A; invariant OC trip 33.69 A >= 32.0 A PASS; ERC clean.
- **Status.** A, S, E; U (OC response rows in the baseline; product-page discrepancy); H (CR-05). Primary **A**. Evidence: [sensing_protection.json](../design/research/sensing_protection.json), verify_sensing_protection_*, calculations.json `sensing.tmcs1133`.

### D-16 AMC1311 voltage sensing with HV ladders and SELV conditioning location (CR-16)

- **Problem.** Isolated V_IN (to 480 V) and V_OUT (to 240 V) into the 0-3 V ADC with headroom; ladder stress and creepage; where to convert differential to single-ended given a 50-pin mezzanine.
- **Knowledge and rules.** CB-SN-001 (EC-015 / EC-021 methods), CMP-AMC1311, SKILL-005 principle 6. KR-SN-002 direct (602 V full scale -> 2.392 V at 480 V; 302 V -> 2.384 V at 240 V); KR-SN-001 direct (7 kVpk, 1500 Vrms, >= 8.5 mm); KR-ISO-002 human review; the 1.1x / 1.25x headroom factors are agent-selected (assumptions fact-check).
- **Reference.** CB-SN-001 rescaled: 4 x 750 k + 10.0 k (R59-R63) and 2 x 750 k + 10.0 k (R64-R66), 0.1 % 1206 (<= 120 V / 19 mW each), 1 nF + 100 pF; the 10.0 k and 330 pF coincide with the TIDA instance and are declared re-derived; gain 1.5 at 32 kHz.
- **Influence.** U6/U7 AMC1311BDWVR; U8 OPA2320 difference amplifiers on the power-board SELV strip (CR-16) so only single-ended VIN_SENSE / VOUT_SENSE / ISENSE / ISENSE_REF cross J7/J8 (pins 43-49) - the controller verifier found the differential pairs lacked connector pins; ADC front ends 1 k + 1 nF (control board R67/C68, R73/C74).
- **Verification.** Recomputed by both sensing verifiers; SBAS786C confirmed; the agent's package-creepage-vs-laminate comparison at 480 V replaced by the 440 V DC working voltage, the 9.0 mm rule and slots (D-21); ERC clean.
- **Status.** A, E; P (ladder creepage, slots under U6/U7); H (KR-ISO-002). Primary **A**. Evidence: sensing_protection.json "Input voltage ladder", verify_sensing_protection_*, verify_controller_*_engineering.

### D-17 Heatsink NTC route (CR-01) and OTP ladder (CR-25)

- **Problem.** Supervise the heatsink temperature, map it to T_J, keep the NTC insulated on a PE-bonded sink, set derate / trip thresholds.
- **Knowledge and rules.** CB-PR-002 (thermistor via AIN/APWM), SKILL-006 principle 5, CGD1700 decision 8, CMP-UCC21710-Q1, TIDA decision 5 (TMP6131). KR-TH-003 human review -> cooling supervision only, thresholds are proposals, a firmware T_J estimator recommended; CB-PR-002 adapted then rejected for this grounding scheme (CR-01).
- **Reference.** CB-PR-002 was adapted by three agents independently (3.3 k + 10 k + 10 nF network; TDK M703 with 95 / 85 C; ring-lug NTC read directly), two decoding the APWM polarity inverted (datasheet: 88 % at 0.6 V, 10 % at 4.5 V; absent from the record). With a PE-bonded sink and a single-point SGND-to-PE bond (proposed PELV deviation A-23) the lug is at control potential; the AIN route would put the floating PGND-to-PE voltage across the NTC. CB-PR-002 stays a fallback; both AIN pins tied to COM.
- **Influence.** Vishay NTCALUG01A103F (1500 Vac lug insulation; CR-08 replaced a misquoted TDK B57703) on the sink top face beside the HS footprint (CR-06) -> control-board J7, R64 2.2 k pull-up to 3.00 V from U15 REF3130AIDBZR (CR-26), 1 k + 1 nF to ADCINA2; OTP comparator U14 with R65 32.4 k / R66 10.0 k = 0.708 V = 100 C; ladder 80 C derate and overload inhibit / 90 C firmware trip / 100 C hardware trip (CR-25) because T_J,HS = T_NTC + 50-66 K at full load and the earlier 90 / 100 / 110 C ladder put the hardware trip at T_J 176-178 C.
- **Verification.** Analytical mapping (calculations.json: offsets 58-69 K with the 1.4 K/W pad, so even the lowered ladder maps the hardware trip to T_J 158-169 C at the max-R overload corner - open item); fan-fail 117-263 s to the 90 C trip; thermal verifiers caught thresholds presented as design values and the mounting conflict; controller verifiers caught the APWM polarity; ERC clean.
- **Status.** A (mapping), E; H (all three thresholds, estimator, potentiometer calibration). Primary **H**. Evidence: [thermal.json](../design/research/thermal.json), verify_thermal_*, calculations.json `sensing.comparators`, `thermal.ntc_to_TJ_offset_K`.

### D-18 Shared PE-bonded heatsink with a rated insulating pad (CR-21)

- **Problem.** Two exposed-tab devices (HS tab = VIN+, LS tab = SW) on one grounded sink: insulation, edge creepage, pad thermal resistance, displacement current.
- **Knowledge and rules.** SKILL-006 principle 2; TIDA decision 9 (CD-02-05-247, 0.1 K/W instance); standards values 5.0 / 3.0 mm. KR-TH-002 direct (pad resistance in the budget; voltage rating and creepage human review - the rule has no numeric content); KR-ISO-002 human review; KR-ISO-004 (slots at mounting hardware).
- **Reference.** TI's 0.1 K/W pad not reused (the Wakefield 0.107 C-in2/W is area-normalised); Bergquist TDS (Nov 2018) fetched instead.
- **Influence.** Sil-Pad TSP A2000 0.254 mm (6 kVac class), 28 x 32 mm per device; R_pad 1.4 K/W clip / 1.16 K/W screw on the exposed tab (~2.3 cm2; CR-21 - the 16 x 21 mm body outline had given 0.96 K/W); TSP 3500 alternative (1.20 / 0.92 K/W); clips >= 40 N, clip-to-lead >= 3 mm; screw only with a full-depth bushing (Boyd 7721-7PPSG rejected); LS-tab displacement current 2.8-4.1 A (56-82 pF); HV keep-out >= 5 mm around HS1.
- **Verification.** Thermal fact-check found the pad-area error (3.37 vs 2.3 cm2) -> CR-21 propagated through seven documents; pad rating vs impulse basis (2.5 kV OVC II vs 4 kV; a D149 breakdown is not a withstand rating) preserved as CR-13; the standards fact-check noted KR-TH-002 contains no ">= 4 kV" limit (adapted).
- **Status.** A, E, P (keep-out, slots); U (clip force, spreading 0.1-0.2 K/W, measured R_pad); H (pad type test, edge creepage). Primary **A**. Evidence: thermal.json, verify_thermal_*_factcheck, design_decisions.json `thermal.interface_pad`.

### D-19 Heatsink selection and thermal budget (KR-TH-001)

- **Problem.** Sink for P_HS up to 34.1 W (360 V / 27.5 A, max R_DS(on)) at 50 C with T_J <= 150 C (125 C preferred) within 80 mm height.
- **Knowledge and rules.** SKILL-006 (P_max form, factor 2 read as two devices per sink, TI 40 C and the room-ambient warning, CR201-50VE 0.5 C/W instance), EC-019/020, TIDA decision 9. KR-TH-001 direct: P_max = (150 - 50) / (0.41 + 1.4 + 2 x 0.30) = 41.5 W vs 34.1 W (margin 1.22; 1.18 at k_RG 2.0, 143.1 C, 151 C with spreading); 125 C met only with typical parts at 400 V / 25 A.
- **Reference.** TI's parts evaluated and not selected: CR201-50VE / CLA-TO-21E discontinued since August 2024 (CR-24; its datasheet does carry a forced-convection chart, so the agent's "0.5 C/W unsupported" was overstated); 50 / 69 W and 40 C not copied; the room-ambient warning produced the explicit 50 C design point.
- **Influence.** HS1 Fischer LAM 5 D K 100 12 (double width, integrated fan, 0.30 K/W distributor figure), replacing the single-width LAM 5 K 100 12 (0.68 K/W: 152.6 C with the 1.4 K/W pad) and the architecture reservation (CR-06, CR-13); pitch 28 mm; fan capped at 0.5 A; fan failure -> OTP mandatory, FAN_TACH derating within 2 s.
- **Verification.** Both thermal verifiers recomputed; hottest HS corner found at 360 V / 27.5 A; the 6-10 W inductor placeholder replaced by 16-20 W (CR-14, CR-23); 24 corners in calculations.json, invariant 143.1 C <= 150 PASS; no CFD; Fischer data distributor-level.
- **Status.** A; U (LAM 5 D K datasheet: R_th, airflow, fan current, mass); H (about 130 C at the max-R corner vs 125 C preference; fan-fail strategy). Primary **A**. Evidence: calculations.json `thermal`, verify_thermal_*_engineering, consistency_review.md 1.

### D-20 PCB architecture Option B and the mezzanine signalling

- **Problem.** Partition between the power stage with its isolators and the fine-pitch DSP (V1-09: LQFP-176 on heavy copper); barrier count; PWM / fault integrity across the interconnect.
- **Knowledge and rules.** TIDA decision 10; SKILL-002 principles 1-8 and scope note; CB-GD-003; CGD1700 decisions 4, 6; CGD15SG00D2 decision 7; PE-PCB-007; V1 precedent. KR-PCB-005 direct on its rationale (connector inductance outside the gate loop; "within 15 mm" is an agent metric); KR-GD-008 adapted (stacked mezzanine, <= 100 mm segment as the exclusion; RS-422 if a cable > 150 mm - agent thresholds); KR-ISO-001 direct (10 mm ISO_BARRIER all layers; second clause -> HS/LS inter-island 3.0 / 1.0 mm, CR-23); KR-PCB-001 direct (four layers: B.Cu gate pours over In2.Cu Kelvin pours, 0.2 mm prepreg); KR-PR-003 adapted (eFuse at the 12 V entry on the control board).
- **Reference.** TIDA partition transferred; its attributed "300 x 180 mm" is not in the record and was removed; CGD1700 island sizes calibrate a 30 x 35 mm envelope; the CGD15SG00D2 card models Option C.
- **Influence.** Option B (scores A 2.75 / B 4.00 / C 3.10): power board 240 x 180 mm, 4 x 70 um, 2.0 mm (core 1.32 mm, CR-22), HV area 33,600 mm2 at 73 % (CR-22 corrected 28,800 / 86 %), SELV strip 30 mm; control board 120 x 80 mm, 4 x 35 um, stacked ~11.05 mm on J7 SSW-125-01-G-D / J8 TSW-125-07-G-D (50 pins, 24 grounds); buffered single-ended PWM with 100 ohm / 100 pF / 10 k at each driver input.
- **Verification.** Misapplications corrected: the SKILL-002 "~200 kW+" scope note (busbar systems; the skill covers plug-in driver boards) and KR-PCB-005 used as rule-level reasons against Option C; the KR-GD-008 extension silently resolved a conflict two records had made conditional (RS-422 when boards are separated) - now a documented deviation for review; the inter-board "no control copper above HV copper" labelled an agent extension; the KR-TH-001 sanity check (R_pad 0.5 K/W) replaced by the thermal table. ERC clean, mezzanine pin table verified pin for pin; geometry unmeasured.
- **Status.** A, E; P (outline, 9.0 mm clearances, driver distance, loops); H (RS-422 deviation, >= 11 mm stacked-board clearance at PD2, 2 vs 4 layers). Primary **A**. Evidence: [architecture.json](../design/research/architecture.json), verify_pcb_architecture_*, [architecture_comparison.md](architecture_comparison.md).

### D-21 Insulation coordination: 9.0 mm all-layer rule, slots, net classes

- **Problem.** Reinforced HV-to-SELV insulation at 440 V DC working voltage, PD2, CTI >= 175 (IIIa); impulse basis; functional spacing; creepage under barrier parts with land gaps below 9 mm; DRC-able net classes.
- **Knowledge and rules.** SKILL-002 principles 5-7 (numbers come from the standard); KR-SN-001; CGD1700 decision 6 (class structure, 0.76 mm slots); CGD15SG00D2 decision 7 (8 mm for 800 Vpk basic, "not assessed to a third-party standard"). KR-ISO-002 human review with values the standards agent derived from IEC 61800-5-1:2007 tables (secondary source; reproduce IEC 60664-1 Annex F, Tables F.1 / F.2 / F.4 corroborated): 4 kV basic / 6 kV reinforced (600 V-system row; an OVC II 300 V system would allow 2.5 kV with 1.5 / 3.0 mm - conflict preserved), 9.0 mm HV-to-SELV all layers (standard minimum 5.5 mm), 5.0 mm HV-to-PE, 3.0 / 1.0 mm functional (CR-09), 0.3 / 0.2 mm; KR-ISO-003 direct (eleven classes); KR-ISO-004 direct with corrected model: 1.2 mm nominal (>= 1.0 mm = PD2 X value) slots under eight parts (U1/U3, U2/U4/U5, U6/U7, U10) extending e >= 3 mm so that 2 sqrt((g/2)^2 + e^2) >= 9.0 mm; KR-ISO-001 direct.
- **Reference.** CGD15SG00D2 8 mm as cross-check only; CGD1700 0.76 mm slot not reusable at PD2; class structure mirrored.
- **Influence.** The baseline `kicad_rules_mm`; `.kicad_dru` files in both projects (hashed in the ERC manifests, exercised only by DRC); slotted footprints `UCC14141_DWN0036A_Slot`, `TMCS1133_DVG0010A_HV_Slot`; [layout_spec_power.json](../verification/engineering_checks/layout_spec_power.json) encodes the pairs (9.0 all layers; HV-PE 5.0; functional 3.0 / 1.0 outside the TO-247-4 courtyards; HS/LS islands 3.0 / 1.0) and barrier rows (surface path 9.0 mm, extension 3.0 mm, width 1.0 mm).
- **Verification.** Misapplications corrected: the "gap + 2 x board thickness" slot model (1 mm extension gave 7.9-8.3 mm); stale RECOM / Murata candidates in the KR-SN-001 review; an unreproducible 6.4 mm TOV clearance (9.0 mm governs); "[V] read from the standard" tags downgraded (no copy in the repository); the sensing agent's 480 V / 10 mm reading reconciled. Path arithmetic recomputed; no DRC yet.
- **Status.** A (path arithmetic), P (DRC with class rules, slot geometry, layer images), H (every distance, impulse basis, stacked-board clearance, pad rating), U (standard values secondary-source). Primary **P**. Evidence: standards_safety.json, verify_applicable_standards_*, design_decisions.json `standards_and_spacing`.

### D-22 Commutation and gate-loop layout constraints (hand-off)

- **Problem.** Switch-node overshoot within the 90 V allowance (530 V recurring peak at 440 V) at 2.5 A/ns; gate-loop inductance and shielding; decoupling inside both loops; copper for 25 A.
- **Knowledge and rules.** SKILL-002 steps 2-3; CGD1700 decision 7 (PRD-09301); TIDA decision 10; PE-PCB-001/002/003/006/008. KR-PCB-001 direct (adjacent-layer pours, Kelvin shield); KR-PCB-002 direct (C_eff >= 1.25 uF for 100 mV droop -> 2 x 4.7 uF + 100 nF VDD-COM and 4.7 uF + 100 nF COM-VEE between driver and gate/Kelvin: C22/C23/C25, C42/C43/C45); KR-PCB-003 direct hard constraint (Kelvin never tied to the power source); KR-PCB-004 direct (power loop first; the <= 20 nH board target and 40-60 nH total with standing leads are design figures, the rule carries no number); KR-PCB-005 direct; KR-PCB-006 direct with IPC-2221 sizing (12 mm outer / 22 mm inner per 25 A at 20 K; 24 x 0.3 mm vias per transition; 25 um plating assumed).
- **Reference.** CGD1700 20 uF per rail not copied; TIDA multi-layer bus copper adopted as a pattern.
- **Influence.** The baseline placement rules and stack-up (F.Cu ceramics and pours / In1.Cu PGND return / In2.Cu Kelvin pours / B.Cu gate pours and drivers); layout-spec blocks `commutation` (C1-C10 to the Q1/Q2 pins <= 5 / 15 mm), `gate_loops` (U1 -> Q1, U3 -> Q2 <= 15 mm; KS_H / KS_L distinct from SW / PGND - the KR-PCB-003 hook), `decoupling` (<= 15 mm), `copper` (24 vias).
- **Verification.** The parasitic sweep (ideal switch; the +344 V bound is not a prediction) yields the requirement L_loop <= 36 nH at 2.5 A/ns (22 nH at 4 A/ns), leaving ~15 nH for package and leads above the 20 nH board target. ERC shows the Kelvin and power-source nets exist separately; netlist check, every geometric metric and the overlay reviews are pending; the double-pulse test (R_G,on sweep, V_DS <= 528 V at 440 V) is required.
- **Status.** S (L x di/dt budget), P (all layout metrics), H (overlay review). Primary **P**. Evidence: simulation_report.md 7, layout_spec_power.json, design_decisions.json `architecture.placement_rules`.

### D-23 Precharge, fuse and relay power path (CR-15)

- **Problem.** Inrush into 48.7 uF at 440-480 V; a fuse that cannot protect SiC; a bypass relay at 400 V DC that must never open under load; coil budget.
- **Knowledge and rules.** No block covers precharge, fuses or relays (false hits KR-CAP-001, CMP-TPS2640, CB-IS-003). KR-PR-001 direct as a coordination statement (device I2t 0.08-0.27 A2s is orders of magnitude below any 25 A fuse's melting I2t, so the fuse protects wiring and board only); KR-SN-001 human review (coil-to-contact insulation); KR-PR-003 pattern for the 12 V side only.
- **Reference.** None transferable. External: TDK PTC and SIOV datasheets, Omron J186-E1-01, Littelfuse product page (50 kA at 600 VDC; melting I2t not found).
- **Influence.** RT1 PTC across the relay contacts (TDK B59xxx to be re-selected: R25 100-150 ohm, Vmax >= 480 V DC, Vlink >= 620 V - the quoted B59773C0120A070 does not carry the quoted parameters); Omron G9EA-1 DC12 chassis-mounted on J5/J6 (60 A; 400 V maximum switching voltage, hence never commanded open under load; close at V_bus > 340 V and dV/dt < 2 V per 10 ms, 500 ms timeout); Q3 AO3400A coil switch, D7 SS14 (CR-19), PWM hold 50-60 % required; off-board fuse KLKD025.T 25 A 600 V DC (CR-15: 20 A reaches 88 % at the 320 V stop corner); firmware input-current limit 15.6 A below 360 V (CR-20); tau 5.8 ms, t99 27 ms, 4.7-5.6 J, PTC dT 2.7 K.
- **Verification.** Both sensing verifiers recomputed with the corrected capacitance, corrected the PTC and MOV codes (B72220S0381K101), deleted the unsupported relay-break claim, evaluated the 320 V fuse corner; calculations.json `power_path` loading 46-70 %; ERC clean; nothing simulated.
- **Status.** A, E; U (KLKD I2t, PTC part, relay variants / lifecycle); H (relay sequencing, coil-to-contact insulation at 440 V DC, source limit 18-25 A). Primary **A**. Evidence: sensing_protection.json, verify_sensing_protection_*, calculations.json `power_path`.

### D-24 Auxiliary 12 V protection and budget (CB-PR-001, CR-02, CR-18)

- **Problem.** Protect the 12 V tree feeding three bias modules, fan, relay coil and control board; thresholds consistent with the UCC14141 (UVLO 8.2 V / OVLO 22 V) and TPS54302; inrush; budget against an eFuse that is a circuit breaker in MODE = open.
- **Knowledge and rules.** SKILL-004 principle 7; CB-PR-001 (alternatives A eFuse / B P-FET + Zener); CMP-TPS2640; TIDA decision 8; KR-IS-001. KR-PR-003 direct, thresholds human review; CB-PR-001 adapted (alternative A for UVLO, limit and inrush control); CMP-TPS2640 direct.
- **Reference.** TI thresholds (OVP 15 V, UVLO 9 V, 2.2 A, 36 V TVS) replaced by derived values; the 100 uF bulk coincides with alternative B and is re-justified.
- **Influence.** Control board: U1 TPS26400PWPR, D1 SMBJ15CA (bidirectional, reverse input blocked by the eFuse), R1 107 k / R2 4.42 k / R3 10 k (UVLO 10.0 / 9.3 V, OVP 14.45 / 13.4 V), R4 6.04 k -> I_CB about 1.96 A with 4 ms timeout / 540 ms retry (CR-18), C2 100 nF dVdT (8.9-12.2 ms), R5 14.7 k IMON; budget at 10.8 V: 0.40 + 0.15 + 0.29 + relay pull-in 0.42 (hold 0.25) + fan 0.50 = 1.76 A / 1.59 A steady, margins 1.11x / 1.23x; 2.5 A supply recommended, fan-upstream fallback; U4 TPS3808G01 101 k / 10 k = 4.50 V (CR-18).
- **Verification.** Misapplications corrected: I_OL used as the trip threshold in circuit-breaker mode (the record lacks I_CB); relay coil budgeted at 100 mA vs 417 mA (CR-02); flat UCC14141 1.0 W reading; TPS3808 divider (105 k = 4.66 V). Invariant aux budget 1.76 A <= 1.957 A PASS, but calculations.json notes zero margin against an assumed -10 % I_CB minimum during relay pull-in (stagger or move the fan). ERC clean.
- **Status.** A, E; H (KR-PR-003 threshold review; relay / fan staggering); U (SMBJ15CA, AO3400A, Samtec at distributor level). Primary **A**. Evidence: controller_aux_interconnect.json, verify_controller_*, calculations.json `aux_12V`.

## 4. Knowledge misapplications caught by verification and their correction

| # | Misapplication (agent) | Caught by | Correction in the baseline | Design impact |
|---|---|---|---|---|
| 1 | KR-ISO-004 with the through-slot model "gap + 2 x board thickness"; 1 mm extension gives 7.9-8.3 mm < 9.0; slot width without tolerance (standards) | standards engineering | path 2 sqrt((g/2)^2 + e^2) >= 9.0 mm, e >= 3 mm, 1.2 mm nominal / >= 1.0 mm | yes - eight footprints, layout spec |
| 2 | KR-GD-003 exclusion invoked in effect via "inherently immune" from small-signal bounds (mosfet, gate-driver) | both engineering verifiers | charge-based estimate; Miller clamp REQUIRED | yes - R21/R39 mandatory, test required |
| 3 | KR-IS-001 recorded conflict (factor 2, EC-014) not carried (gate-driver; assumptions) | gate-driver both lenses, assumptions fact-check | both forms shown; budget uses 0.24 W per channel | yes - module budgets |
| 4 | KR-GD-011 / KR-GD-012 (module-scoped) labelled direct (gate-driver) | gate-driver both lenses | adapted | label only |
| 5 | KR-GD-006 (multi-supplier) labelled direct for a same-supplier fallback (mosfet) | mosfet both lenses | adapted | label only |
| 6 | KR-PR-001 presented as a datasheet comparison of an unpublished withstand time (standards); labelled human-review though a hard constraint (mosfet) | standards engineering; mosfet fact-check | hard constraint; 0.55-1.07 us vs 1.5 us; destructive test | yes - test requirement |
| 7 | KR-CAP-003 labelled direct although TI's MLCC purpose is "inferred" (capacitors) | capacitor engineering | adapted | label only |
| 8 | KR-CAP-002 labelled direct for the buck output capacitor (assumptions) | assumptions engineering | adapted | label only |
| 9 | KR-PR-002 labelled direct while used for the bus UVLO ladder (assumptions) | assumptions fact-check | adapted | label only |
| 10 | SKILL-003 exclusion misquoted without "of low-voltage converters" (inductor, assumptions) | inductor both lenses | wording restored | none |
| 11 | SKILL-002 "~200 kW+" scope note and KR-PCB-005 used as rule-level reasons against Option C (architecture) | architecture both lenses | rationale, second barrier instance, cost | none |
| 12 | KR-GD-008 exclusion silently extended to the mezzanine; 100 / 150 mm thresholds presented as rule content (architecture, controller) | architecture both lenses, controller engineering | adapted; tests in the plan; documented deviation | open item |
| 13 | KR-ISO-001 second clause (HS/LS barrier) not carried; inter-board clause presented as rule content (architecture) | architecture both lenses | 3.0 / 1.0 mm inter-island barrier (CR-23); extension labelled | yes - placement rule, spec pair |
| 14 | KR-TH-001 sanity check with inputs contradicting the owning agent (architecture) | architecture engineering | thermal table referenced | none |
| 15 | KR-TH-002 cited for ">= 4 kV AC" and ">= 5.0 mm" it does not contain (standards, architecture) | standards and architecture fact-checks | 5.0 mm attributed to the DRC derivation; 4 kV restated; CR-13 preserved | none |
| 16 | KR-TH-003 thresholds as design values (thermal); 95 / 85 C fixed without the thermal model (sensing) | thermal and sensing engineering | proposals; ladder 80 / 90 / 100 C (CR-25) | yes - OTP divider, firmware thresholds |
| 17 | KR-CAP-001 marked not applicable yet used for own 60 / 40 uF while the capacitor result existed (sensing) | sensing engineering | 48.7 / 132 uF; precharge and discharge recomputed (CR-03) | yes - precharge numbers, bleeder merge |
| 18 | KR-ISO-002: package creepage vs laminate at the 480 V TOV (sensing) | sensing engineering | 440 V DC, 9.0 mm rule, slots | none beyond D-21 |
| 19 | KR-SN-001 review on stale candidates (RECOM / Murata, generic relay); RECOM basic grade "not found" though in the cached datasheet (standards) | standards both lenses | UCC14141 and G9EA-1 named; RECOM / Murata excluded (CR-12) | yes - exclusion |
| 20 | Reference values adopted or coinciding undeclared: R_GS 10 k, BAT42W, +15/-4 V, 10 ohm (gate-driver); 10.0 k / 330 pF, 10 nF (sensing) | gate-driver both lenses, sensing fact-check | declared re-derived; BAT42W to DNP | yes - D4/D6 DNP |
| 21 | CMP-UCC14141-Q1 ratings read without conditions (gate-driver, controller) | gate-driver both lenses, controller engineering | 1.5 W (10.8-13.2 V, TA <= 85 C), 1.0 W (8-18 V), 2.5 W abs max | open item (SOA) |
| 22 | CMP-TPS2640 used with I_OL in circuit-breaker mode (controller) | controller engineering | I_CB = 12 / R_ILIM - 0.03 A (CR-18) | yes - R_ILIM 6.04 k, margins |
| 23 | CB-PR-002 APWM polarity inverted (controller, sensing) | controller both lenses | polarity recorded; moot after CR-01 | none after CR-01 |
| 24 | CB-PR-002 adapted three ways with no owner | gate-driver engineering | one owner; route rejected (CR-01) | yes - direct SELV NTC |
| 25 | TIDA utilisation ratios attributed to "decision 1" (mosfet) | mosfet engineering | AIPE-derived via SKILL-006 EC-019/020 | none |
| 26 | PRD-08296 cited under REF-WS-CGD1700HB2M-UNA (mosfet) | mosfet fact-check | separate Wolfspeed note (module data) | none |
| 27 | "TIDA 300 x 180 mm" not in the record (assumptions, controller) | assumptions engineering, controller fact-check | removed | none |
| 28 | KR-PR-001 cited for testability (architecture) | architecture fact-check | replaced by A-37 / CGD1700 practice | none |
| 29 | PE-PCB-005/006 listed as `--get` hits the tool cannot return (inductor, sensing) | inductor and sensing fact-checks | cited from docs/pcb-design-rules.md | tooling item |
| 30 | SKILL-006 equal-share limitation not carried (assumptions) | assumptions engineering | P_max against the worse device (41.5 W vs 34.1 W) | yes - thermal margin statement |

Two verifier statements were themselves wrong and are recorded as such: REF-WS-PRD-04814 *is* retrievable (section 2.1), and the "CR201-50VE 0.5 C/W unsupported" caveat was overstated by the thermal agent and softened by the fact-check (the finding that stands is the discontinuation).

## 5. Knowledge the references did not cover and what was done instead

| Gap | Evidence of the gap | Used instead (verification level) |
|---|---|---|
| Magnetics design | eight inductor searches with no magnetics hit | Magnetics 2024 catalogue fits and 0058192A2 datasheet (fetched; fits verified by both verifiers; dT correlation unverifiable); Dowell AC-resistance estimate (added assumption); proposed new skill (D-11) |
| 1200 V Gen-4 devices | the KB names C3M0075120K and the obsolete C3M0030090K as reference usage only | C4MS025120K Rev. 2 and C3M0021120K Rev. 4 datasheets (fetched); PRD-08296 and forum statements for withstand (not datasheet values); 15 candidates compared |
| 50 kHz hard-switched buck waveforms | SKILL-003 is written for the DAB tank waveform; SKILL-006 principle 3 for ZVS | dQ = D(1-D) I_o T_s, triangular output current, HS/LS RMS, dead-time loss - derived, analytically checked and simulated |
| Numeric insulation values | SKILL-002 and KR-ISO-002 carry no numbers by design; the CGD15SG00D2 8 mm is board-specific | IEC 61800-5-1:2007 tables as read by the standards agent (secondary, no licensed copy), IEC 60664-1 Annex F corroboration, IPC-2221B Table 6-1 |
| Spacing and copper on 70 um layers | KR-PCB-006 is a low-confidence single-reference rule | IPC-2221 current-capacity formula (conservative vs IPC-2152), via barrel arithmetic, fabricator capability assumptions (0.25 mm preferred, 0.20 mm only with confirmation) |
| Electrolytic lifetime | SKILL-003 excludes lifetime modelling | all-film output bank; comparison computed, not used |
| Precharge, fuse, relay, HV MOV | no block or rule; false hits | TDK PTC / SIOV datasheets, Omron J186-E1-01, Littelfuse product page (I2t missing); relay sequencing rule derived from the 400 V maximum switching voltage |
| Control supplies, supervisor, logic, DSP | no KB content | V1 precedent (TPS54302, TPS767D301, TPS3808, LM61, 30 MHz oscillator); TI datasheets / pages for SN74LV21A, SN74LV04A, SN74LVC1G74, SN74LVC2G08, TLV1702, REF3125, REF3130, OPA2320, TMS320F28335 |
| Heatsink, pad, NTC, connectors, HV terminals | SKILL-006 names TI instance parts only (one discontinued) | Fischer LAM 5 D K (distributor level), Bergquist TSP A2000 / 3500 TDS, Vishay NTCALUG01A, Samtec catalogue, Wuerth REDCUBE, Isola 370HR, Delta fan sheet |
| Film capacitor data | the TIDA B32716 records have no datasheets | TDK B32776 (June 2026), KEMET C4AQ, Vishay MKP1848C and CRCW2512 datasheets fetched |

The knowledge base has no `simulation-verified` or `hardware-validated` item, so every quantity the design relies on is at most analytically checked or simulated by V2 itself.

## 6. Knowledge-base defects and proposed updates (proposals only; nothing under knowledge/ was changed)

Record corrections.

1. CB-PR-002: add the APWM transfer direction (88 % duty at 0.6 V, 10 % at 4.5 V; D = 0.88 - 0.200/V x (V_AIN - 0.6 V)), the treatment of an unused AIN (tie to COM), a single-owner note and the grounding condition under which the AIN route is wrong.
2. CMP-UCC14141-Q1: attach the conditions to the power ratings (1.5 W at 10.8-13.2 V and TA <= 85 C; 1.0 W at 8-18 V; POUT_VDD_MAX 2.5 W at 25 C; SOA = lower of 1.5 W and the derating curve); add the COM-VEE regulator sink / source path through RLIM with the 0.125 A rms pin limit and 16 % run-time qualification (the fact behind CR-12); reconcile the working-voltage figure (1414 Vpk / 1000 Vrms / 1500 Vrms) from SLUSF10B; record certification status.
3. CMP-TPS2640: add the MODE table and I_CB = 12 / R_ILIM - 0.03 A with the 4 ms timeout and 540 ms retry; "2 A eFuse" is not a threshold.
4. CMP-TMCS1133: replace the non-existent TMCS1133B1QDVGR by the A-suffixed orderables; note the product-page (600 Vrms / 8.1 mm) vs datasheet (950 Vrms / 1343 VDC) discrepancy.
5. CMP-R12P21503D, CB-IS-003, SKILL-004: record from the cached RxxP2xx REV 9-2024 datasheet "working voltage 250 VACrms" and "insulation grade according to 62368-1: basic"; fix the 5.2 / 6.4 kVDC attribution.
6. SKILL-006 and the TIDA analysis: mark C3M0030090K obsolete and CR201-50VE / CLA-TO-21E discontinued (August 2024); state that 0.5 and 0.1 C/W are TI instance values with unrecorded airflow, pressure and test power; note that the Wakefield figure is area-normalised.
7. KR-GD-011 / KR-GD-012: "applies by analogy to discretes; label adapted". KR-GD-008: express the exclusion by link length and noise environment and attach the measurement verification. KR-GD-005: state that a synchronous buck is a half bridge for the exclusion list.
8. KR-ISO-004: add the around-the-slot-end creepage model and the PD2 minimum slot width 1.0 mm after tolerance.
9. KR-ISO-001: add the stacked-PCB case as an explicit condition or exclusion.
10. REF-WS-CGD1700HB2M-UNA: reconcile the board size (50.8 x 61.0 vs 50.8 x 59.69 mm); cite PRD-08296 as its own document or add a reference record.
11. SKILL-005 principle 7 and SKILL-004 principle 6: add the RLIM sink check as a precondition for sharing.
12. SKILL-003: keep the exclusion wording and add the HV buck case explicitly (input dQ = D(1-D) I_o T_s; inductor-defined output ripple plus load-step energy).
13. KR-TH-002 and KR-CAP-003: note that the rules carry no numeric or temperature content (three agents cited them for 4 kV, 5.0 mm, 125 C).
14. KR-PR-001: add "if no withstand time is published, compliance is shown by destructive test"; name PRD-08296 as module-level context only.

Additions.

15. New skill "powder-core DC inductor design" from the inductor and magnetic records (LI^2 selector, permeability / loss / magnetisation fits, still-air model as an own approximation, soft-saturation criterion L(1.3 I_pk) >= 70 % of L(I_o) beside the vendor 30 %-drop I_sat, datasheet-maximum core-loss case); component records for 0058192A2 / C058192A2.
16. Gen-4 device records CMP-C4MS025120K (Rev. 2; -10/+23 V; R_thJC 0.41 K/W typical, no maximum; Q_G 125 nC; no withstand time; Arrow-only stock) and CMP-C3M0021120K; an open check on a Gen-4 750 V TO-247-4 industrial family.
17. A block "DC-link precharge, bypass relay and passive discharge" - the area with no knowledge item and the most part-number errors.
18. Component records for the V2 parts without a record, at the verification level reached: TDK B32776G8206K000 / G4606K000, CGA9P (DC bias open), Bergquist TSP A2000 / 3500, Vishay NTCALUG01A103F, Omron G9EA-1 DC12 (400 V maximum switching voltage), Littelfuse KLKD025.T (I2t missing), Fischer LAM 5 D K 100 12 (distributor-only), Wuerth 744226S, REF3125 / REF3130, TLV1702, OPA2320, SN74LVC1G74 (DCTR / DCUR), SN74LV21A, SN74LV04A, Samtec SSW / TSW, REDCUBE 74651195.
19. SKILL-002 / SKILL-006: record the V2 partition pattern (one barrier line through all eight isolators, device row on the HV side, SELV strip at the edge, stacked control board) once the layout metrics exist.
20. A reference record for IEC 61800-5-1:2022 + COR1:2023 (clause 4.3.11 -> 4.4.9) once a licensed copy is on record.

Tooling and process.

21. query.py: index `automation/verification/pcb_rules.json` (or docs/pcb-design-rules.md) so PE-PCB-001..008 resolve with `--get` (re-checked: `unknown id`), and reconfigure stdout to UTF-8.
22. Component-record cache paths (`.cache/references/datasheets/*.pdf`) do not exist on a host that has not run `acquire`; state that sha256 and resolved URL are the evidence anchor.
23. knowledge_trace.py: split compound ids, recognise `external-method` / `project-precedent` entries as declared sources, and emit a banner and header in knowledge_trace.md.
24. Research-record schema: require `conflicts_preserved` for every rule that carries a `conflicts` list (KR-IS-001 and KR-GD-003 each lost one) and one owner per circuit block (CB-PR-002 was adapted three ways).
25. Validation status: V2 is the first run in which knowledge-derived quantities were simulated. The agreement of the buck applications of KR-CAP-001 / KR-CAP-002 and of KR-GD-009 (dead-time loss) with the ngspice campaign could justify `simulation-verified` for those *applications* after human review, with the caveat that the model has no device physics; the rules themselves stay reference-derived or analytically-checked.

## 7. Assessment: did the knowledge improve the design?

| Indicator | Value |
|---|---|
| Significant decisions audited | 24 |
| Decisions where a knowledge item set the method or a value (direct or adapted) | 22 of 24 (D-11 magnetics and D-23 precharge / fuse / relay had no applicable item; D-23 used KR-PR-001 only for the coordination statement) |
| Decisions where a human-review-requirement rule was surfaced instead of decided | 10 (KR-GD-004, KR-GD-010, KR-IS-004, KR-ISO-002, KR-PR-003, KR-SN-001, KR-TH-003 across D-03, D-05, D-06, D-07, D-08, D-16, D-17, D-18, D-21, D-24) |
| Design errors the knowledge prevented or exposed before verification | at least 9: negative turn-off rail kept despite the single-ended exclusion (KR-GD-005); no reference DESAT values copied (KR-GD-004); gate-discharge resistor (KR-GD-007); interlock as last barrier (KR-GD-009); latched combined fault with UVLO lock-out (KR-PR-002); hardware OC path, ADC shown too slow (KR-SN-005); bias sharing flagged for review (KR-IS-004 -> CR-12); slots under barrier parts (KR-ISO-004); NTC not treated as T_J (KR-TH-003 -> CR-25) |
| Knowledge misapplications caught by the verifiers | 30 (section 4): 12 changed a value, requirement or part; 7 were label-only |
| Knowledge found wrong, stale or incomplete | 9: obsolete C3M0030090K; discontinued CR201-50VE / CLA-TO-21E; TMCS1133 orderable; UCC14141 rating conditions and RLIM path; TPS2640 threshold; CB-PR-002 polarity; RECOM insulation grade; CGD1700 board-size inconsistency; PE-PCB rules not indexed |
| Reference instance values copied without derivation | none found by the verifiers except the BAT42W clamp (now DNP); coincidences (+15/-4 V, 10 ohm, 10 k, 330 pF, 10 nF, 744226S) declared |
| Justified deviations from the references | 0 V turn-off note overridden; sensing supply not shared; single-ended mezzanine instead of RS-422 (documented deviation); direct SELV NTC instead of AIN/APWM; 50 C instead of 40 C; 1200 V class at 42-46 % instead of TI's 0.56-0.67 ratios; DESAT 3.6 V / 288 ns; 10 MLCC instead of 14; B32776 instead of B32716; 9.0 mm instead of 8 mm |
| Verification coverage of the 24 decisions | A 23, S 6, E 20, P 7, U 14, H 24 (section 8) |

**Judgement.** The knowledge system did three things V1 could not and that a review would otherwise have to supply from the reviewer's experience: it put the right questions in front of every agent (DESAT timing versus withstand, Kelvin-source return, barrier parts rated for the node, decoupling inside the gate loop, a bias budget at the actual input voltage); it carried manufacturer conflicts (factor 2, 0 V versus negative turn-off, 46 ns versus 1 us blanking, 10 k versus 47 k) into the record so the verifiers could check that they were resolved and not ignored; and it made applicability auditable - every one of the 273 labelled citations could be, and in 30 cases was, challenged. The largest quality effect traceable to a knowledge item is CR-12 (KR-IS-004 plus the UCC14141 record led to the RLIM sink check that falsified the TIDA sharing pattern), followed by the mandatory Miller clamp (KR-GD-003 after correction), the slot geometry (KR-ISO-004 after correction) and the lowered OTP ladder (KR-TH-003).

The knowledge also introduced risk. Nine items were stale or incomplete and roughly one labelled citation in nine was challenged. The misapplications cluster where a scope note reads like a result (KR-GD-003, KR-GD-008, KR-ISO-004), where a component record omits a datasheet condition (UCC14141, TPS2640), and where a block is adapted by several agents at once (CB-PR-002). Without the two-verifier layer, items 1, 2, 3, 17, 22 and 24 of section 4 would have reached the schematic. The honest conclusion is conditional: the knowledge improved the design *together with* independent verification; alone it would have improved the questions asked and degraded a few answers.

**What cannot be concluded without hardware.** The knowledge base has no simulated or hardware-validated item and V2 adds only a behavioural simulation. Nothing in this run shows that the gate rails stay inside the maxima at the device, that the clamp holds the off-state gate, that 3.6 V / 288 ns trips before the C4MS025120K fails, that a 1.25x CMTI margin suffices, that the commutation loop lands below 36 nH, that R_pad is 1.4 K/W and R_th,HS 0.30 K/W, that common-mode current and EMI are acceptable, that the control loop reaches 2.3 kHz with real sensing delays (no firmware exists), or that any insulation distance passes a type test. The baseline's test plan lists these measurements; the knowledge system cannot replace them.

**Comparison with V1 (process terms only; [v1_v2_comparison.md](v1_v2_comparison.md)).** V1 used no knowledge system (0 skills, 0 rules, 0 queries, 0 citations), no simulation and no independent research-verification records; it relied on the eight project PCB rules and two review records. V2 logged 91 queries and 317 citations over 96 ids, 10 research records with 20 verification reports, 19 invariants, 20 simulation runs and 65 component records with per-part verification levels. These are coverage and traceability measures, not correctness: V1 has a routed, DRC-clean, frozen release and V2 does not yet have a layout, so no layout or product-quality claim is possible in either direction.

## 8. Verification status summary and open items for human review

### 8.1 Status per decision

| Decision | A | S | E | P | U | H | Primary |
|---|---|---|---|---|---|---|---|
| D-01 MOSFET class and part | x | x | x | | x | x | A |
| D-02 Single vs parallel | x | | | | | x | A |
| D-03 Gate rails | x | | x | | | x | A |
| D-04 Driver IC | x | | x | | x | x | A |
| D-05 Gate resistors, Miller clamp | x | | x | | | x | A |
| D-06 DESAT vs withstand | x | | x | | | x | A |
| D-07 Bias module and budget | x | | x | | x | x | A |
| D-08 Sensing-island supply | x | | x | | x | x | A |
| D-09 CM choke, C_iso | x | | x | x | x | x | A |
| D-10 Interlock, latch, run permit | x | | x | | | x | E |
| D-11 Inductor | x | x | x | | x | x | A |
| D-12 DC-link bank | x | x | x | x | x | x | S |
| D-13 Output capacitor | x | x | x | | | x | S |
| D-14 Bleeders, discharge | x | | x | | x | x | A |
| D-15 TMCS1133 OC | x | x | x | | x | x | A |
| D-16 AMC1311 sensing | x | | x | x | | x | A |
| D-17 NTC route, OTP ladder | x | | x | | | x | H |
| D-18 Shared sink, pad | x | | x | x | x | x | A |
| D-19 Heatsink, thermal budget | x | | | | x | x | A |
| D-20 Architecture, mezzanine | x | | x | x | | x | A |
| D-21 Insulation coordination | x | | | x | x | x | P |
| D-22 Loop constraints | | x | | x | | x | P |
| D-23 Precharge, fuse, relay | x | | x | | x | x | A |
| D-24 Aux 12 V eFuse | x | | x | | x | x | A |
| **Count** | **23** | **6** | **20** | **7** | **14** | **24** | A 18, S 2, E 1, P 2, H 1 |

Every decision carries at least one human-review item; none is closed. The six simulated decisions are verified for passive-network and loss quantities only, not for switching, protection or thermal behaviour. The seven decisions marked P close through `verification/pcb_rule_review.md` (DRC with class rules, layout metrics from check_sic_layout.py against the layout specs, per-layer barrier images, overlay reviews for PE-PCB-001/003) and the regenerated `verification-summary.json`.

### 8.2 Open items for human review

1. Insulation coordination: 4 kV vs 2.5 kV impulse basis; 9.0 mm all-layer rule vs the 5.5 mm minimum; slots under eight parts; stacked-board clearance; pad rating and type test; relay coil-to-contact insulation; standard values at secondary-source level (D-18, D-21, D-23).
2. The SGND-to-PE single-point bond (PELV) as a proposed deviation from the SELV seed; PGND reference strategy and Y capacitors (D-17, D-20).
3. Short-circuit protection: destructive test against the 0.55-1.07 us response; DESAT trip and blanking on hardware; CMTI margin (D-04, D-06).
4. Gate drive: off-state V_GS with the clamp, double-pulse R_G sweep, gate-Kelvin RC population, RLIM selection, UCC14141 SOA and certification status, the three working-voltage figures (D-03, D-05, D-07).
5. Sensing-island supply: feasibility of the COM-VEE 5.0 V sourcing configuration through RLIM (D-08).
6. Thermal: about 130 C at the max-R overload corner vs the 125 C preference; measured R_pad and sink R_th (Fischer datasheet); the OTP ladder, whose lowered levels still map the hardware trip above 150 C at the worst corner; the firmware T_J estimator (D-17, D-18, D-19).
7. Single-ended mezzanine signalling by adaptation of the KR-GD-008 exclusion where two records asked for RS-422 (D-20).
8. Controller: the inner current loop is required (simulation); stand-in margins (41-55 deg, 4.5-5 dB) vs the firmware contract (30-40 deg with real filters); load-dump reverse-current policy against the 460 V input OVP with a non-sinking source (D-13).
9. Power path: PTC re-selection, fuse melting I2t, relay sequencing, source current limit 18-25 A, aux-budget margin during relay pull-in (D-23, D-24).
10. Magnetics: winding house, orderable core code, potting cup, acoustic noise, worst-case core loss, thermocouple acceptance <= 110 C (D-11).
11. MLCC DC-bias curve and lifecycle; damping-leg population after loop extraction (D-12).
12. The 25 knowledge-base proposals of section 6, none applied; and the simulation-versus-calculations one-to-one check not yet run because calculations.json post-dates the campaign.

### Verification status of this report

Analytically checked in this audit: the trace statistics of section 2.2 (recomputed by script from knowledge_trace.json), the five ERC run statuses, the invariant and cross-check counts of calculations.json, the query-tool behaviours of section 2.1, and the existence or absence of every file named in section 1. Every design value quoted carries the verification level of the baseline or research record it comes from; no level was upgraded. Simulated: only the quantities marked S, by the V2 campaign. Unverified: everything marked U. Human review: everything marked H and the twelve items above.
