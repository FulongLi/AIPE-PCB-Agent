# CGD1700HB2M-UNA — engineering analysis

Reference: `REF-WS-CGD1700HB2M-UNA` · Wolfspeed dual-channel isolated gate driver
for SiC half bridges (modules and discretes) · board Rev A, user guide PRD-06992
rev 2 (Oct 2025), OrCAD/Allegro sources, 2025 combined BOM · with application
note PRD-09301 rev 1 (May 2025) "Gate Driver Design for SiC Power Modules",
which uses this board as its running example · analysed 2026-10-09.

> Original AIPE analysis; Wolfspeed material is not reproduced. Connectivity
> statements marked *netlist* were confirmed with
> `automation/knowledge/allegro_netlist.py` against the Allegro expanded
> netlist and are re-run by `automation/knowledge/check_evidence.py`.

## Evidence base

| Evidence | Used for | Strength |
|---|---|---|
| PRD-06992 user guide | ratings, interfaces, protection settings, formulas | stated |
| PRD-09301 application note | layout and design rationale (general guidance) | stated, manufacturer guidance |
| Allegro `pstxnet.dat` (2020) | DESAT, gate and clamp connectivity; net classes | netlist |
| Schematic PDF Rev V1 (2021) | topology and values | observed |
| Combined BOM (2025) | variant part numbers | observed |
| Board specification text | 4 layers, 50.8 × 59.69 mm, slots | observed |

## Decision 1 — Integrated-protection isolated driver per channel (UCC21710)

1. **Implemented:** one UCC21710QDWRQ1 per channel; split OUTH/OUTL to separate 1 Ω 2512 resistors (RT27/RT28 low side, RT30/RT31 high side); CLMPI to the gate through a 0 Ω link (RT29/RT32); 10 kΩ gate–source resistor (RT33/RT34). (*netlist* EC-023; BOM)
2. **Why:** separate turn-on and turn-off tuning, Miller clamp independent of R_G,OFF, gate discharge when unpowered (PRD-09301 §3.2, §5.8, §5.9).
3. **Problem solved:** switching-dynamics tuning within SOA; parasitic turn-on; gate charge build-up before the driver is powered.
4. **Applicability:** half-bridge SiC up to the IC's isolation rating (1.5 kVrms working). Wolfspeed states the Miller clamp is "not strictly needed" with low R_G and low-inductance routing (PRD-09301 §5.8).
5. **Evidence:** netlist; user-guide Table 3 (R_G(IC)-ON 0.7 Ω, R_G(IC)-OFF 0.3 Ω typ.).
6. **AIPE reuse:** CB-GD-001; KR-GD-002, KR-GD-003, KR-GD-007.
7. **Verification:** netlist check that OUTH, OUTL and CLMPI each reach the gate through their intended element; double-pulse tuning; V_GS measured on the device side of R_G (PRD-09301 §6.1).

## Decision 2 — DESAT overcurrent detection with two series HV diodes and configurable blanking

1. **Implemented:** VDD → RT25 2.2 kΩ → node → DB8 + DT7 (US3M-13, 1 kV each, in series) → drain connector JT4; node → RT22 2.2 kΩ → OC pin; RT21 220 Ω OC → source; CT19 56 pF blanking capacitor and BAT42W clamp from OC to source. Trip V_DS ≈ 6.7 V and external blanking ≈ 46 ns, plus the IC's 120 ns deglitch. (*netlist* EC-022; PRD-06992 §4.4.4; checks EC-001, EC-002)
2. **Why:** detect short-circuit/shoot-through in microseconds without a shunt in the power loop (PRD-09301 §5.1); two diodes raise the blocking voltage and ease creepage routing (PRD-09301 §5.1).
3. **Problem solved:** SiC short-circuit withstand time is short; ADC-based protection is too slow.
4. **Applicability:** devices whose on-state V_DS at the intended trip current is known; trip current depends on R_DS(on) temperature (C3M0032120J1 example: 6.7 V ≈ 103 A at 150 °C, PRD-06992). The default trip "may not be optimal for all applications" (stated).
5. **Evidence:** formulas recomputed exactly (EC-001: 6.70 V; EC-002: 45.9 ns).
6. **AIPE reuse:** CB-GD-001 DESAT sub-block with a calculator; KR-PR-001 and KR-GD-004.
7. **Verification:** recompute trip and blanking for the chosen device and diode V_F; measure in hardware (Wolfspeed: "precise value should be measured on the hardware").

## Decision 3 — Soft shutdown, UVLO/RDY and latched global fault

1. **Implemented:** UCC21710 400 mA soft turn-off on OC; per-channel RDY and FLT combined by an SN74HC21 4-input AND into one differential FAULT; latched OC fault cleared by RESET/EN low ≥ 1000 ns; RESET has an RC filter (120 Ω/56 pF) with a schematic note to increase the capacitor for long cables. (PRD-06992 §4.4–4.5; schematic sheets 1–2)
2. **Why:** hard turn-off at kiloampere fault currents causes destructive V_DS overshoot; a single global fault simplifies the controller (PRD-09301 §5.2, §5.5).
3. **Problem solved:** safe fault turn-off, supply-fault lock-out and simple controller interface.
4. **Applicability:** module and discrete half-bridges; two-level turn-off is explicitly **not recommended** by Wolfspeed for modules (PRD-09301 §5.3).
5. **Evidence:** stated + schematic.
6. **AIPE reuse:** CB-GD-001, CB-GD-003; KR-PR-002.
7. **Verification:** fault-injection test; confirm fault latching and reset timing in firmware.

## Decision 4 — Differential (RS-422) signalling with filtering and interlock

1. **Implemented:** SN65C1167 transceiver; each received pair has 1 µH series inductors, 56 pF to ground and 120 Ω termination; P/N lines deliberately swapped so an open input yields an inverted (off) PWM; UCC21710 IN+/IN− cross-wired for hardware interlock (XOR behaviour); RC filters on PWM, fault and reset. (PRD-06992 §3.1, §4.2, §4.4.6; schematic sheet 1)
2. **Why:** single-ended signals over cables are susceptible to switching noise; differential is recommended below 2 kV over fibre for cost (PRD-09301 §4.2–4.3); interlock is a last barrier, not dead-time generation (PRD-09301 §5.6).
3. **Problem solved:** noise-induced false turn-on and shoot-through from a faulty controller.
4. **Applicability:** gate drivers on separate boards or cable-connected; on-board short single-ended links are acceptable with buffering and RC filtering (PRD-09301 §4.1).
5. **Evidence:** schematic note on fail-safe inversion; interlock truth table (PRD-06992 Table 16).
6. **AIPE reuse:** CB-GD-003; KR-GD-008, KR-GD-009.
7. **Verification:** open-cable test (outputs stay off); both-inputs-high test; measure common-mode noise at receiver.

## Decision 5 — Isolated bias: SIP module per channel, input CM choke, optional LDO post-regulation

1. **Implemented:** per channel a 2 W isolated module (RECOM R12P21503D +15/−3 V in the default variant; Murata MGJ2D122005SC +20/−5 V in -R1/-R2), a 10 µH common-mode choke (Würth 744226S) before the module with the 10 µF input capacitor between choke and module, a 750 mA fuse; -R1/-R2 add LT3082 (positive, 10 µA SET current, R_FB = 1.5 MΩ → 15 V, 1.8 MΩ → 18 V) and LT3015 (negative) LDOs; 2 × 10 µF + 2 × 10 µF decoupling per channel (20 µF each rail). (PRD-06992 §4.3; PRD-09301 §2.4, §2.6, §3.8; BOM)
2. **Why:** modules are simple, pre-certified and have low isolation capacitance (PRD-04814); unregulated outputs are acceptable for most end applications but characterisation needs LDOs (PRD-06992 §1.1); the CM choke raises common-mode impedance of the coupling path through the PSU (PRD-09301 §3.8).
3. **Problem solved:** per-channel floating supply with controlled common-mode current; optional precise rails.
4. **Applicability:** linear-regulator output range is limited to 0.3 V inside the module rails (PRD-06992 §4.3.4); changing V_GS also shifts the DESAT blanking (biased from VDD).
5. **Evidence:** LDO equations recomputed for both the schematic and the 2025 BOM divider values (EC-005, EC-006, EC-007).
6. **AIPE reuse:** CB-IS-003; KR-IS-001 (power budget), KR-IS-002 (CM choke placement).
7. **Verification:** power budget P = Q_G · f_sw · ΔV against 2 W (EC-003, EC-004); output-rail ripple during switching.

## Decision 6 — Net-class-driven isolation layout with slots

1. **Implemented:** Allegro net spacing classes PRIMARY, LOW-SIDE, HIGH-SIDE, LS/HS-DESAT-MIDPOINT and LS/HS-DRAIN; no copper crosses the control/driver barrier or the HS/LS barrier on any layer; slots in isolation regions; DESAT diodes kept far from other groups because they block bus voltage. Isolated HS and LS sections 25.4 × 30.5 mm; whole board 50.8 × 61.0 mm. (*netlist* EC-024; PRD-09301 §2.1, §2.5, §2.7)
2. **Why:** pins within one group differ by ~20 V, groups by the bus voltage; grouping lets low-voltage nets route tightly while groups keep creepage (PRD-09301 §2.7).
3. **Problem solved:** compact layout that still satisfies creepage/clearance and blocks capacitive noise coupling between channels.
4. **Applicability:** any isolated driver; actual distances come from the applicable standard (UL 61800-5-1, IEC 60664-1, IPC-2221A are named examples).
5. **Evidence:** net-class names from the netlist; distances in PRD-09301 Figure 20 were not extracted numerically.
6. **AIPE reuse:** KR-ISO-001, KR-ISO-002, KR-ISO-003; AIPE's KiCad net classes can mirror the six groups.
7. **Verification:** KiCad net-class assignment check plus DRC clearance rules per class; human review of copper on every layer across barriers.

## Decision 7 — Gate loop and Kelvin-source routing guidance (from PRD-09301)

1. **Implemented (guidance):** gate and Kelvin-source as wide pours on adjacent layers; Kelvin-source layer between the gate layer and any other circuitry (shield); compact gate loop including decoupling capacitors; never tie the module Kelvin-source to the power source in the layout; connector inductance often dominates. (PRD-09301 §1.1, §1.4, §2.2, §2.3, §2.5, §2.6)
2. **Why:** flux cancellation is "the most influential aspect of gate inductance"; tying KS to power source reintroduces common-source inductance and overloads internal KS bonds (stated).
3. **Problem solved:** gate overshoot/ringing, delay, false turn-on.
4. **Applicability:** all SiC devices with a Kelvin source; power-loop inductance still takes priority over gate-loop inductance (stated).
5. **Evidence:** manufacturer guidance (not measured by AIPE).
6. **AIPE reuse:** SKILL-002 core content; KR-PCB-001, KR-PCB-003, KR-PCB-004.
7. **Verification:** stack-up review (gate/KS adjacency), loop-area extraction, V_GS ringing measurement with an isolated probe at the device side of R_G.

## Decision 8 — Isolated thermistor feedback through the driver's AIN/APWM

1. **Implemented:** JB1 thermistor input biased by the UCC21710 200 µA AIN source, converted to a 400 kHz, 10–88 % duty signal and sent differentially; optional current mirror not populated. (PRD-06992 §4.7)
2. **Why:** module NTCs can lose isolation after a catastrophic failure, so an isolation barrier on NTC feedback is recommended (PRD-09301 §3.4).
3. **Problem solved:** isolated temperature monitoring without an extra isolator.
4. **Applicability:** prefer the driver referenced to a stable node (low side) (PRD-09301 §3.4). NTC temperature is not junction temperature (PRD-06992 §4.7).
5. **Evidence:** stated.
6. **AIPE reuse:** CB-PR-002 and SKILL-006.
7. **Verification:** calibrate with a potentiometer in place of the NTC (stated method).

## Conflicts and alternatives to keep visible

- **DESAT blanking:** CGD1700 uses ≈46 ns external + 120 ns IC deglitch; TI TIDA-010054 configured 1 µs. Different devices, topologies (hard-switched characterisation vs ZVS DAB) and risk tolerance — preserved in KR-GD-004.
- **Gate discharge resistor:** 10 kΩ (this board, PRD-09301 §5.9) vs 47 kΩ (CGD15SG00D2).
- **Gate–source Zener clamp:** Wolfspeed does not use one on module drivers (PRD-09301 §5.4).
- **Gate–KS capacitor:** PRD-04814 allows a small C or RC between gate and Kelvin source but warns against an external gate–source capacitor on three-lead (no Kelvin) packages; PRD-06933 shows added C_GS lowers the PTO peak but lengthens its duration.
