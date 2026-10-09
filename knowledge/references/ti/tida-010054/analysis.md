# TIDA-010054 — engineering analysis

Reference: `REF-TI-TIDA-010054` · TI 10 kW bidirectional dual-active-bridge (DAB) ·
hardware E4, design guide TIDUES0 Rev F, CAD Rev D · analysed 2026-10-09.

> Original AIPE analysis. No TI text, figure or CAD content is reproduced; TI's
> notice prohibits redistribution. Evidence locations point into the documents
> listed in [`reference.json`](reference.json) so a reviewer with the cached
> files can check every statement. "Stated" = TI wrote it; "observed" = seen in
> BOM, schematic or layer plot; "calculated" = recomputed in
> [`knowledge/verification/evidence-checks.json`](../../../verification/evidence-checks.json);
> "inferred" = AIPE interpretation that TI does not state.

## Evidence base and its limits

| Evidence | Used for | Strength |
|---|---|---|
| Design guide TIDUES0F (81 pp.) | topology, ratings, design equations, sensing and bias choices, test results | stated |
| BOM TIDRZW1B | real part numbers, quantities, values | observed |
| Schematic TIDRZW0C (text) and design-guide schematic figures | refdes and values in sensing and gate-drive circuits | observed |
| Layer plots TIDRZW3C (rendered) | placement, partitioning, copper strategy | observed, qualitative |
| Altium project TIDRZW4D | inventory only | not parsed |

TI's own text contains stale content from an earlier hardware revision (see
`source_discrepancies` in the record). Where text and BOM disagree, the BOM is
taken as describing the fitted E4 hardware.

## Decision 1 — Dual-active-bridge topology with SPS and EPS modulation

1. **Implemented:** two full bridges (4 × 1200 V on 800 V side, 4 × 900 V on 500 V side) linked by a 24:15 planar transformer with integrated series inductance (34–35 µH), 50 % duty per leg, power controlled by phase shift; extended-phase-shift (EPS) firmware option. (TIDUES0 §2.3.1–2.3.4, §4.5)
2. **Why:** bidirectional power flow for V2G/charging, modular stacking and inherent ZVS without auxiliary components; LLC, PSFB and CLLC were considered and rejected (§1).
3. **Problem solved:** galvanic isolation plus bidirectional DC/DC at 700–800 V ↔ 250–500 V with soft switching.
4. **Applicability:** isolated bidirectional DC/DC with moderate voltage-ratio range. Single-phase-shift loses ZVS at light load when the voltage ratio departs from 1 (§2.3.4.2); EPS is needed to reach 10 kW down to 350 V and 5 kW at 250 V (§4.5.1).
5. **Evidence:** power equation and 22.85 kW theoretical maximum (§2.3.4.1), 23° phase shift at 10 kW (§2.3.4.4) — both recomputed in checks EC-010 and EC-011.
6. **AIPE reuse:** topology-selection knowledge for an isolated bidirectional stage; the P(φ) relation and ZVS boundary form a sizing calculator for series inductance and phase-shift resolution.
7. **Verification:** recompute P_max and φ(P) for the target operating envelope; simulate ZVS boundaries over the full V-ratio range before layout.

## Decision 2 — DC-link: film bulk capacitors plus distributed high-voltage MLCCs

1. **Implemented:** primary 2 × 15 µF 1.1 kV film (TDK B32716H1156K000), secondary 2 × 30 µF 800 V film (TDK B32716H8306K000); in addition 14 × 0.47 µF 1 kV 2220 MLCC (Knowles 2220Y1K00474KETWS2) and 14 × 0.47 µF 630 V 2220 MLCC (TDK CGA9P1X7T2J474M250KC) in columns beside the bridges, plus 8 × 0.1 µF 1 kV 1812 MLCC (KEMET C1812V104KDRACTU). (BOM; Figure 3-1; top overlay)
2. **Why:** TI sizes output capacitance from the ripple charge ΔQ (12 µC nominal, 50 µC at low output voltage) and a 5 V ripple target giving ≥10 µF, then selects low-ESR film for the switching-frequency ripple current; 60 µF output and 30 µF input were fitted (§2.3.4.5). The MLCC columns are not explained in the text (inferred: high-frequency commutation-loop decoupling close to the TO-247 legs).
3. **Problem solved:** ripple-voltage limit and RMS ripple-current capability at 100 kHz; HF current loop minimisation.
4. **Applicability:** square-wave current converters (DAB, PSFB) where the capacitor current is the difference between a rectified tank current and DC load current. The ΔQ method requires the actual current waveform at every corner of the operating envelope.
5. **Evidence:** C = ΔQ/ΔV recomputed (EC-012); ratings from BOM; placement from top overlay (observed).
6. **AIPE reuse:** SKILL-003 procedure (ripple charge → capacitance; RMS current → technology; voltage derating; split into bulk film + local HF ceramic).
7. **Verification:** recompute ΔQ and I_C,rms from a simulated capacitor current; check film RMS rating at f_sw and temperature; measure ripple and capacitor temperature rise.

## Decision 3 — Series DC-blocking capacitor sized from a resonance criterion

1. **Implemented:** DC-blocking capacitors in the transformer path; minimum value from C ≥ 100 / (4π² f_s² L) = 7.2 µF (§2.3.4.5.1).
2. **Why:** prevent transformer saturation from volt-second imbalance caused by PWM mismatch, driver delay mismatch or transients (§2.3.4.5.1).
3. **Problem solved:** DC flux walking in the isolation transformer.
4. **Applicability:** bridges driving a transformer with no inherent DC-blocking; requires the capacitor to carry full transformer RMS current and withstand full voltage.
5. **Evidence:** the expression places the C–L series resonance one decade below f_s (inferred interpretation of the factor 100 = 10²; recomputed EC-013).
6. **AIPE reuse:** calculation template in SKILL-003.
7. **Verification:** check resonance f_r ≤ f_s/10, RMS current rating, and simulated switch-node waveform distortion.

## Decision 4 — One isolated driver and one isolated bias module per switch

1. **Implemented:** 8 × UCC21710QDWQ1 isolated drivers and 8 × UCC14141QDWNRQ1 isolated bias modules, configured for +15 V / −4 V; R_LIM 1 kΩ (driver only) or 600 Ω (driver plus isolated-sense supply) (§3.4.2, §3.5, BOM).
2. **Why:** UCC21710 chosen for integrated DESAT/overcurrent, active Miller clamp and soft turn-off; UCC14141 for smallest footprint and height (§3.4.2, §3.5).
3. **Problem solved:** each switch has an independent floating reference at 700–800 V with high dv/dt.
4. **Applicability:** discrete SiC bridges at hundreds of volts; the option to share one bias supply between low-side FETs or to use bootstrap was provided on the PCB but **not tested** (§3.4.2).
5. **Evidence:** BOM quantities; DESAT set to 6.4 V with 1 µs blanking via TI calculator (§3.5, stated).
6. **AIPE reuse:** CB-GD-001 and CB-IS-002; contrasts with the Wolfspeed 46 ns blanking approach (alternative preserved in KR-GD-004).
7. **Verification:** gate-charge power budget against 1.5 W module rating (EC-014 style); short-circuit withstand time of the chosen FET vs. blanking + response time; double-pulse and short-circuit test.

## Decision 5 — Gate-loop components and turn-on/turn-off resistors

1. **Implemented:** separate OUTH/OUTL 2.0 Ω 1206 resistors per driver (16 × CRCW12062R00JNEA), US1Q-TP 1200 V DESAT diode per driver, 100 pF timing capacitors, TMP6131 thermistor on the high-side driver AIN (Figure 3-13; BOM).
2. **Why:** resistors "dampen oscillations" at the gate (§2.3.5.4, stated); thermistor allows isolated temperature sensing through APWM (§2.2.1).
3. **Problem solved:** gate ringing and independent tuning of dv/dt at turn-on and turn-off.
4. **Applicability:** TO-247-4 Kelvin-source devices at 100 kHz ZVS operation; values are design-instance values, not a general recommendation.
5. **Evidence:** BOM and Figure 3-13 (observed).
6. **AIPE reuse:** example values in CB-GD-001; KR-GD-002 (independent R_on/R_off) is multi-source.
7. **Verification:** double-pulse test across resistor values; check V_DS overshoot and dv/dt limits.

## Decision 6 — Isolated sensing split by distance to the controller

1. **Implemented:** primary DC voltage via 8 × 634 kΩ + 10 kΩ divider into AMC1311 (2 V input) and OPA2320 differential-to-single-ended stage; primary DC current via 3 mΩ shunt into AMC1302 (±50 mV); secondary voltage and battery voltage via AMC1336 ΔΣ modulators and secondary current via 1.5 mΩ shunt into AMC1306M05, all decoded by the C2000 SDFM; transformer (tank) currents via TMCS1133 Hall sensors with built-in overcurrent flags at 45 A / 70 A (§3.2–3.3).
2. **Why:** a digital bitstream is "less vulnerable to noise" over the longer path from the secondary side (§3.2.2, stated); Hall sensor chosen for low propagation delay and 1 MHz bandwidth to support switch-node overcurrent protection (§3.3).
3. **Problem solved:** accurate, isolated feedback with noise immunity proportional to signal path length; fast tank-current protection.
4. **Applicability:** MCUs with ΔΣ filter peripherals (SDFM) for the modulator approach; analog isolated amplifiers suit short paths to an ADC.
5. **Evidence:** divider ratios recomputed (EC-015, EC-016); shunt full-scale recomputed (EC-017, EC-018).
6. **AIPE reuse:** CB-SN-001 to CB-SN-004 and SKILL-005.
7. **Verification:** recompute divider/shunt scaling, power dissipation and voltage rating of every resistor in the HV ladder; check input-range headroom at worst-case overvoltage; check SDFM clock routing and propagation-delay compensation.

## Decision 7 — Isolated sensing supply derived from a gate-driver bias module

1. **Implemented:** the low-side gate-driver bias (+15 V) also powers a TLV76050 5 V LDO for the high-side of the isolated amplifiers/modulators, with a series resistor before the LDO to reduce its dissipation (§3.4.3).
2. **Why:** avoids a dedicated isolated supply for the sensors (inferred from context; TI states only the arrangement).
3. **Problem solved:** fewer isolated converters; sensors referenced to the same node as the low-side switch.
4. **Applicability:** only for sensors referenced to the same potential as that switch's source (here primary/secondary negative rail).
5. **Evidence:** R_LIM 600 Ω chosen for modules that also feed the sensor LDO (§3.4.2).
6. **AIPE reuse:** design option in CB-IS-002; requires bias power budget check.
7. **Verification:** add sensor and LDO current to the bias power budget; confirm the module current limit setting.

## Decision 8 — Auxiliary 12 V input protection with an eFuse

1. **Implemented:** TPS26400 eFuse with OVP 15 V, UVLO 9 V, 2.2 A limit, TVS diodes (SMCJ36CA, SMBJ36CA) and Schottky (B250A) (§3.4.1).
2. **Why:** the 12 V input directly feeds fans, relays and all isolated bias modules (§3.4.1, stated).
3. **Problem solved:** protects the whole auxiliary tree against overvoltage, reverse polarity and overload.
4. **Applicability:** bench or system 12 V auxiliary buses.
5. **Evidence:** circuit Figure 3-8 (observed). Note the conflicting J15 supply description (`source_discrepancies`).
6. **AIPE reuse:** CB-PR-001 alternative A.
7. **Verification:** check thresholds against bias-module input range (UCC14141 1.5 W rating applies at 10.8–13.2 V).

## Decision 9 — Thermal path: two TO-247 per heat sink with insulating pads and forced air

1. **Implemented:** four Ohmite CR201-50VE heat sinks, two FETs per sink, Wakefield-Vette CD-02-05-247 insulating phase-change pads, two 12 V fans (§2.3.5.6; BOM).
2. **Why:** shared heat sink requires electrical insulation between exposed drains (§2.3.5.6).
3. **Problem solved:** junction temperature limit with a simple series thermal model.
4. **Applicability:** through-hole TO-247 on vertical sinks with forced air; model assumes 40 °C ambient and equal sharing.
5. **Evidence:** P_max = (T_J,max − T_A)/(2R_th,HS + R_th,iso + R_th,JC) gives 50 W and 69 W — recomputed EC-019, EC-020. TI does not explain the factor 2 on R_th,HS (inferred: the sink resistance is shared by two devices).
6. **AIPE reuse:** SKILL-006 thermal-budget method and KR-TH-001.
7. **Verification:** recompute with actual loss split, ambient, airflow and pad pressure; measure case/heat-sink temperatures.

## Decision 10 — Layout partitioning (observed from layer plots)

1. **Implemented:** primary bridge on one side and secondary on the other with the planar transformer in a central board cut-out; DC-bus copper repeated on top, inner 1 and bottom layers; gate drivers and bias modules on the bottom side in a column directly beside each TO-247-4; control card connector, eFuse and low-voltage circuitry along the board edge away from the power stage; a continuous copper gap separates primary and secondary power areas. 300 × 180 mm, four copper layers. (TIDRZW3 pages 1, 3, 4, 6, 10)
2. **Why:** not stated by TI (no layout section in the design guide). Inferred: short gate loops per device, high current capacity through parallel layers, isolation between transformer sides.
3. **Problem solved (inferred):** gate-loop inductance, copper current density, primary/secondary isolation.
4. **Applicability:** board-mounted discrete power stage of ~10 kW.
5. **Evidence:** visual only; net names and clearances not machine-verified.
6. **AIPE reuse:** placement-partitioning patterns in SKILL-002 and SKILL-006 (flagged as observation, single source).
7. **Verification:** in an AIPE design, extract driver-to-FET distances and creepage gaps with the PCB checker; human review of layer images.

## What AIPE should not generalise from this design

- The 2 Ω gate resistors, 6.4 V/1 µs DESAT setting and 45 A/70 A Hall trip levels are instance values for this DAB and these FETs.
- Efficiency figures are TI measurements under TI test conditions.
- The bias-sharing and bootstrap options are untested by TI.
