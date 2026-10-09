# SKILL-001 — SiC gate driver design

Status: **reference-derived** (cited calculations analytically checked) · Domain: gate drivers ·
Index: [`SKILL-001-sic-gate-driver-design.json`](SKILL-001-sic-gate-driver-design.json)

## Purpose

Design the circuit between a PWM signal and a SiC MOSFET gate: isolation,
drive strength, gate levels, turn-on/turn-off resistance, off-state immunity,
overcurrent protection and the controller interface. The output is a
schematic-level gate-driver specification that a PCB agent can place and route
with [SKILL-002](../pcb_layout/SKILL-002-gate-driver-pcb-layout.md).

## Applicable conditions

- SiC MOSFETs (discrete or module) in half bridges, full bridges or single-ended stages.
- Bus voltages within the isolation and working-voltage ratings of the chosen driver IC.
- Floating references (high side, or bridges with several references) that need isolated drive.

## Not applicable / out of scope

- Non-isolated low-voltage drivers (e.g. the 48 V Buck V1 benchmark uses a bootstrap half-bridge driver; this skill does not cover that design).
- GaN HEMT gate drive (different gate limits); IGBT-specific short-circuit strategies beyond DESAT basics.
- Choosing the power semiconductor itself (AIPE Transistor Database scope).

## Engineering principles

1. **Isolate every position.** Wolfspeed recommends an isolated driver for every module switch position, including low sides, for safety, removal of noise paths and ground loops, and modularity (PRD-09301 §1.2). TIDA-010054 uses one isolated driver per discrete switch.
2. **Reference the driver to the Kelvin source.** The gate is controlled relative to the source; a dedicated Kelvin source removes common-source inductance from the gate loop (PRD-09301 §1.1). Rule KR-PCB-003.
3. **Gate levels are device-specific.** Keep rails plus tolerance and transients inside the device's absolute maxima (KR-GD-001). For Wolfspeed Gen-3 the guidance is +15 V and −3 to −4 V with ±5 % rails, maxima +19/−8 V (PRD-04814). Negative turn-off is recommended in half bridges but 0 V can be acceptable after evaluation (KR-GD-005, conflict preserved).
4. **Peak current both ways.** Gate current peaks occur at turn-on *and* turn-off; modules with many dies need several amperes (≈6 A in Wolfspeed's CAB006M12GM3 example, PRD-09301 §1.3).
5. **Independent R_G,ON / R_G,OFF.** Tune turn-on for overshoot/EMI and turn-off for loss and immunity (KR-GD-002). Use split OUTH/OUTL drivers (CB-GD-001) or a steering diode (CB-GD-002).
6. **Off-state immunity.** Parasitic turn-on is driven by C_GD·dv/dt into C_GS; mitigations are a higher capacitance-ratio device, negative bias, lower R_G,OFF and an active Miller clamp whose path to the die is short (PRD-06933; KR-GD-003).
7. **Hardware short-circuit protection.** DESAT with HV blocking diode(s), configurable trip and blanking, soft turn-off and a latched fault (CB-GD-001; KR-PR-001, KR-GD-004, KR-GD-011). ADC-based protection is too slow (PRD-09301 §5.1).
8. **Discharge the gate when unpowered.** Gate–source resistor on the device side of R_G (KR-GD-007).
9. **Robust signalling.** Differential/fibre over cables, single-ended conversion close to the IC, RC filters on all signals, hardware interlock as a last barrier (KR-GD-008, KR-GD-009).

## Design procedure

1. Collect device data: V_GS absolute maxima and recommended levels, Q_G at those levels, C_iss/C_rss (capacitance ratio), R_DS(on)(T), short-circuit withstand time, Kelvin-source availability.
2. Choose isolation: working voltage and insulation class at the switch node → driver IC rating (KR-SN-001 applies to every barrier part).
3. Choose gate rails (KR-GD-001, KR-GD-005) and the bias supply with SKILL-004; run the power budget P = Q_G·f_sw·(V_DD−V_EE) (KR-IS-001).
4. Choose driver IC by peak current, split outputs, Miller clamp, DESAT/soft turn-off, UVLO and isolated analog channel needs. Reference instances: UCC21710-Q1 (both TIDA-010054 and CGD1700HB2M-UNA), UCC23514 (CGD15SG00D2, no protection).
5. Select starting R_G,ON/R_G,OFF from device datasheet dv/dt and switching-energy curves (PRD-09301 §3.2 example: 3 Ω on / 1.3 Ω off for a 25 V/ns limit); plan to tune by double-pulse test.
6. Design DESAT: number and rating of HV diodes (≥ device voltage), bias/divider for the trip V_DS at the target current and temperature, blanking capacitor from measured ringing and risk tolerance. Use the CB-GD-001 formulas (checked in EC-001/EC-002).
7. Add gate discharge resistor, rail decoupling sized for Q_G (CGD1700: 20 µF per rail), Miller clamp connection if used.
8. Define the controller interface: interlock wiring, fault/RDY combination and latching, reset timing, signalling standard and filters (CB-GD-003).
9. Record every value as an instance with its basis; hand off placement constraints to SKILL-002.

## Component selection considerations

- Driver IC: isolation (working voltage, surge, CMTI vs. expected dv/dt), peak source/sink current, split outputs, Miller clamp current, DESAT threshold accuracy (UCC21710-Q1 V_OCTH 0.63–0.77 V), soft turn-off current, UVLO levels matched to the chosen rails, propagation delay and skew.
- DESAT diodes: blocking voltage ≥ device rating (or several in series), fast recovery, low capacitance; creepage of the diode bodies to other nets.
- Gate resistors: pulse-rated parts (Wolfspeed uses 2512 pulse-proof resistors); power from Q_G·ΔV·f_sw.
- Steering diodes (if used): fast Schottky, low inductance package.
- Alternatives named in sources only: drivers with integrated flyback controller (ADuM4138, Si828x) for combined bias (PRD-04814).

## PCB constraints (hand-off to SKILL-002)

KR-PCB-001 (gate/Kelvin adjacent layers), KR-PCB-002 (decoupling in the gate loop),
KR-PCB-003 (no KS-to-power-source tie), KR-PCB-005 (driver adjacent to switch),
KR-ISO-001/002/003 (barriers, creepage, net classes), DESAT routing: short drain
connection, compact low-voltage detection side (PRD-09301 §6.4).

## Verification methods

- Calculations: DESAT trip/blanking (EC-001, EC-002), bias power and f_sw limit (EC-003, EC-004), rail set-points (EC-005 … EC-007).
- Netlist checks: gate path, clamp and DESAT connectivity (EC-022, EC-023, EC-026 pattern).
- Measurements: double-pulse test for R_G tuning; off-state V_GS during complementary switching with an optically isolated probe at the device side of R_G (PRD-09301 §6.1–6.2); short-circuit and UVLO fault injection; open-cable/both-inputs-high interlock tests.

## Known limitations

- Values from the references are instance values (TI 2 Ω, 6.4 V/1 µs; Wolfspeed 1 Ω, 6.7 V/46 ns; CGD15SG00D2 10 Ω).
- No AIPE simulation or hardware test underlies this skill; status is reference-derived with checked arithmetic and connectivity.
- Module-level guidance (PRD-09301) is applied to discrete devices only where the physics is the same; module-specific items (multiple gate pins, paralleling) are not expanded here.

## Source references

- TI TIDA-010054 — [analysis](../../references/ti/tida-010054/analysis.md) decisions 4–5.
- Wolfspeed CGD15SG00D2 — [analysis](../../references/wolfspeed/cgd15sg00d2/analysis.md) decisions 1, 2, 6; PRD-06933.
- Wolfspeed CGD1700HB2M-UNA and PRD-09301 — [analysis](../../references/wolfspeed/cgd1700hb2m-una/analysis.md) decisions 1–4.
- Wolfspeed PRD-04814 — [analysis](../../references/wolfspeed/prd-04814/analysis.md) decisions 1, 6.
