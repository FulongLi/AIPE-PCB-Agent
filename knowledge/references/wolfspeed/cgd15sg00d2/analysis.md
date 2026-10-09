# CGD15SG00D2 — engineering analysis

Reference: `REF-WS-CGD15SG00D2` · Wolfspeed single-channel isolated gate driver
for discrete SiC MOSFETs · board Rev 7.0, user guide PRD-08391 rev 4 · also
PRD-06933 (capacitance ratio and parasitic turn-on) · analysed 2026-10-09.

> Original AIPE analysis; Wolfspeed material is not reproduced. Evidence
> locations refer to the documents in [`reference.json`](reference.json).
> Values in PRD-08391 Table 1 were reconciled against footnotes because the PDF
> text fuses footnote markers into numbers (see `evidence_limitations`).

## Evidence base

| Evidence | Used for | Strength |
|---|---|---|
| User guide PRD-08391 | function, ratings, layout narrative | stated |
| Schematic Rev 7.0 (rendered) | topology, values, D3 polarity | observed |
| BOM XLSX (converted) | manufacturer part numbers | observed |
| ODB++ (eda/data, components) | connectivity of D3/R6/R7/U1 | netlist |
| Fab/assembly drawing | stack-up, finish, slots | observed |
| PRD-06933 | parasitic turn-on mechanism and mitigations | stated |

## Decision 1 — Opto-compatible capacitive-isolated driver replacing optocoupler + driver

1. **Implemented:** TI UCC23514MDWVR (e-diode input, 4.5 A/5.3 A peak, Miller clamp variant) replaces the Rev 4 optocoupler plus non-isolated driver; PWM input via 510 Ω resistors in each input leg, optional input capacitor C3 not populated. (PRD-08391 Introduction, Schematic sheet 1, BOM)
2. **Why:** "SiC gate driver technology has since undergone vast improvements"; combining U1/U2 while keeping the board a plug-in replacement (stated).
3. **Problem solved:** fewer parts and higher CMTI (150 kV/µs stated for the IC) on a drop-in footprint.
4. **Applicability:** single switch positions driven from a current-mode (opto-style) PWM source; the input is not differential, so long cables need care (cross-reference PRD-09301 Noise Immunity).
5. **Evidence:** BOM line 24; datasheet page 1 (5.0 kVrms, 150 kV/µs min, 8.5 mm creepage).
6. **AIPE reuse:** CB-GD-002 and CMP-UCC23514.
7. **Verification:** check e-diode forward current from the PWM source voltage and input resistors against the datasheet; verify CMTI margin against the expected dv/dt.

## Decision 2 — Steering diode for independent turn-off resistance

1. **Implemented:** R6 = 10 Ω directly from VOUT to GATE; R7 = 10 Ω in series with Schottky D3 (1N5819HW-7-F) in parallel with R6. D3 cathode faces VOUT, so the R7 branch conducts only when current flows out of the gate (turn-off). Turn-on resistance ≈ R6 = 10 Ω; turn-off ≈ R6 ∥ (R7 + diode) ≈ 5 Ω plus diode effect. (Schematic sheet 1; ODB++ nets NetD3_1/NetD3_2)
2. **Why:** "separate gate turn-on and gate turn-off resistors with a dedicated diode" for bench optimisation (stated). This matches the "turn-off steering diode" variant described in PRD-09301 §3.2, where the turn-off resistor is placed in parallel because turn-off usually tolerates a lower value.
3. **Problem solved:** independent tuning of turn-on dv/dt (overshoot/EMI) and turn-off speed (loss, Miller immunity) with a single-output driver IC.
4. **Applicability:** drivers without split OUTH/OUTL outputs. Diode forward drop and recovery affect low-resistance tuning; a fast Schottky with low inductance is needed.
5. **Evidence:** schematic symbol orientation (observed) and ODB++ connectivity (netlist, check EC-025); equivalent resistances recomputed (EC-009).
6. **AIPE reuse:** CB-GD-002 calculation; KR-GD-002 alternatives list.
7. **Verification:** confirm diode orientation from footprint pin mapping before fabrication; double-pulse measurement of both edges.

## Decision 3 — Discrete open-loop LLC isolated bias supply

1. **Implemented:** TI UCC25800AQDGNQ1 half-bridge transformer driver at ≈500 kHz (R_T 47 kΩ, note "Fsw = R·10 Hz"), Würth 750319177 transformer (1:1.67), two 22 nF resonant capacitors and two 1 A Schottkys in a voltage-doubler, 4.7 µF X7R storage. Input from 12 V through a 22 µH common-mode choke (DLW43SH220XK2L). (PRD-08391 Schematic and Functionality; Schematic sheet 2; BOM)
2. **Why:** "LLC-based discrete solution as opposed to the module-level solution" and "ultra-low-EMI" (stated); 2 W output to operate larger MOSFETs at higher frequency.
3. **Problem solved:** low primary-to-secondary capacitance — the transformer datasheet gives 0.68 pF typ. inter-winding capacitance — limits common-mode current injected by high dv/dt.
4. **Applicability:** per-switch bias of a few watts from a regulated 9–34 V rail (UCC25800 input range); open-loop, so output tracks input and load.
5. **Evidence:** schematic values; datasheet facts (UCC25800-Q1 page 1; 750319177 page 1). R_T check EC-008 (470 kHz vs "approximately 500 kHz").
6. **AIPE reuse:** CB-IS-001; PRD-04814 places single-channel LLC as "very low EMI, very low isolation capacitance, specialised control".
7. **Verification:** load-regulation measurement across 0–2 W (Wolfspeed Figure 5 shows the trend); thermal check of resonant capacitors and diodes.

## Decision 4 — Resistor–Zener split of a single isolated output into +15 V / −3.x V

1. **Implemented:** across VDD2–SOURCE a 15 V Zener (1SMB5929B) in parallel with 20 kΩ; across SOURCE–VSS2 a 3.9 V Zener (1SMA5915B) in parallel with 5.1 kΩ; 2 × 4.7 µF on each rail. (Schematic sheet 2; BOM)
2. **Why:** keep both rails within ≈5 % across load and "ensure proportional charging and discharging" of the rail capacitors (stated).
3. **Problem solved:** one isolated winding provides a positive and a negative gate rail referenced to the source.
4. **Applicability:** when the total isolated output exceeds the sum of the desired rails; typical value table published in PRD-04814 example circuit 1.
5. **Evidence:** typical outputs +15.4 V / −3.3 V (PRD-08391 Table 1). Note the measured negative rail (−3.3 V) is below the 3.9 V Zener rating, so the split depends on load (discrepancy recorded).
6. **AIPE reuse:** CB-IS-004 (generic split-rail block) and KR-GD-005.
7. **Verification:** solve the split under minimum and maximum gate-drive load; check Zener dissipation at light load.

## Decision 5 — Source-referenced decoupling at the output pins

1. **Implemented:** C10 10 nF, C11 100 nF, C12 4.7 µF from SOURCE to VSS2 placed "very close to the source output pin"; C9 4.7 µF VDD2–VSS2 at the driver supply pins; bias-supply output capacitors C6/C7/C14/C15. (PRD-08391 p.10–11; schematic)
2. **Why:** "to minimise stray inductance and achieve tight coupling" (stated).
3. **Problem solved:** supplies the gate-charge transient locally so the driver loop closes through short paths.
4. **Applicability:** all isolated gate drivers; capacitance must scale with gate charge.
5. **Evidence:** stated + schematic.
6. **AIPE reuse:** KR-PCB-002.
7. **Verification:** layout review: capacitor pads within the driver/output-connector loop; ripple on VDD2/VSS2 during switching.

## Decision 6 — Provisional Miller-clamp pin and 47 kΩ gate pull-down

1. **Implemented:** UCC23514 CLAMP pin brought to TP1/J2 (4-pin header optional); R8 47 kΩ gate–source. (PRD-08391 p.11; schematic)
2. **Why:** "improve immunity to high dv/dt by holding the gate to VSS2 with low impedance" (stated). The clamp is only effective when the clamp path to the device is short — PRD-06933 notes Miller clamps lose effectiveness with longer paths.
3. **Problem solved:** parasitic turn-on (PTO) induced through C_GD (PRD-06933 §2).
4. **Applicability:** discrete devices where the clamp connection can reach the gate with low inductance; for modules PRD-06933 cautions that clamp paths are often too long.
5. **Evidence:** stated.
6. **AIPE reuse:** KR-GD-003 (Miller clamp is conditional) and KR-GD-007 (gate discharge resistor: note this board uses 47 kΩ while PRD-09301 suggests ~10 kΩ — alternative preserved).
7. **Verification:** measure V_GS on the off device during the complementary turn-on; compare with and without clamp (PRD-06933 §5 method).

## Decision 7 — Isolation by slots and plane partitioning in a small 4-layer board

1. **Implemented:** creepage-enhancing grooves between logic and power sides (three 1 mm non-plated slots), notches increasing transformer creepage to 8 mm; inner layer 1 carries a PGND plane under the LV side and a SOURCE plane under the HV side; inner layer 2 carries VCC (primary) and VDD/VSS planes (secondary) under the components using them. 4-layer, 62.4 mil, 1 oz, ENIG, Tg ≥ 170 °C. (PRD-08391 PCB Layout; fab drawing)
2. **Why:** planes "help with signal integrity and minimise overall parasitic inductance" and enable "mutual inductance cancellation through via paths" (stated).
3. **Problem solved:** creepage across the isolation barrier in a 47.6 × 17.8 mm board; low-inductance supply/return paths.
4. **Applicability:** compact isolated driver boards. The 8 mm creepage relates to this board's 800 Vpk basic insulation rating — not a universal value.
5. **Evidence:** stated + fab drawing.
6. **AIPE reuse:** KR-ISO-001/002 and SKILL-002 partitioning steps.
7. **Verification:** creepage/clearance measurement against the applicable standard for the system voltage, pollution degree and material group.

## What AIPE should not generalise

- 10 Ω gate resistors, 47 kΩ pull-down and +15/−3.3 V levels are instance values for an evaluation board.
- The 8 mm creepage and 800 Vpk isolation apply to this board only; the board "has not been assessed to a third-party standard" (PRD-08391 Table 1 note).
