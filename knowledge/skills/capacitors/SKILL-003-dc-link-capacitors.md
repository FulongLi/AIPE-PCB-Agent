# SKILL-003 — DC-link capacitor selection and placement

Status: **reference-derived** (cited calculations analytically checked) · Domain: capacitors ·
Index: [`SKILL-003-dc-link-capacitors.json`](SKILL-003-dc-link-capacitors.json)

## Purpose

Select DC-link capacitance, technology and placement for SiC bridges so that
voltage ripple, ripple-current heating and high-frequency commutation-loop
inductance meet the design targets, and size series DC-blocking capacitors in
transformer-coupled bridges.

## Applicable conditions

- Voltage-source bridges (DAB, PSFB, half/full bridges, inverters) with switched DC-link current.
- DC links of hundreds of volts with switching frequencies in the tens to hundreds of kHz (TIDA-010054: 500/800 V, 100 kHz).

## Not applicable / out of scope

- Line-frequency energy storage and hold-up sizing (e.g. PFC bulk capacitors for 2·f_line ripple).
- Low-voltage converter output filters where ripple is set by an inductor current (the 48 V Buck V1 uses a different method).
- Capacitor lifetime modelling (not covered by the references).

## Engineering principles

1. **Charge balance sets capacitance.** C ≥ ΔQ/ΔV with ΔQ the largest ripple charge over every operating corner (KR-CAP-001). In TIDA-010054 ΔQ rises from 12 µC at nominal to 50 µC at low output voltage; with 5 V ripple this needs ≥10 µF (EC-012), and TI fitted 60 µF.
2. **RMS current sets technology and count.** Ripple current at f_sw heats the capacitor via ESR; low-ESR film is chosen for 100 kHz ripple (KR-CAP-002). Compute I_C,rms over the envelope (TIDUES0 Eq.19 for DAB).
3. **Two tiers.** Bulk film for energy/ripple plus distributed HV ceramics immediately beside each half-bridge for the HF commutation loop (KR-CAP-003, single-reference observation; links to PE-PCB-002).
4. **Voltage rating with margin.** TIDA-010054 uses 1.1 kV film and 1 kV ceramics on the 800 V side, 800 V film and 630 V ceramics on the 500 V side; TI does not state a derating rule, so AIPE does not derive one.
5. **DC-blocking in transformer bridges.** A series capacitor prevents flux walking from volt-second imbalance; size it so the series resonance with the tank inductance is a decade below f_s: C ≥ 100/(4π²f_s²L) (KR-CAP-004; EC-013), rated for full transformer RMS current.
6. **Ceramic DC-bias effect (AIPE caution).** X7R/X7T HV ceramics lose capacitance under DC bias; use manufacturer bias curves before counting them as bulk capacitance.

## Design procedure

1. Define the operating envelope (input/output voltages, power, modulation modes such as SPS/EPS).
2. Simulate or compute the DC-link capacitor current waveform at every corner; integrate for ΔQ; compute I_C,rms.
3. Required C = max(ΔQ)/ΔV_allowed; select film capacitors meeting C, voltage and RMS current at f_sw and maximum temperature; split into parallel parts for current sharing and layout.
4. Add HV ceramics in columns beside each bridge leg; check their effective capacitance at bias and their voltage rating.
5. For transformer-coupled bridges, size the DC-blocking capacitor (C_min, RMS current, voltage).
6. Hand placement to SKILL-002/SKILL-006: ceramics at the switch legs, film close to the bridge with low-inductance connections, thermal environment of film capacitors away from heat-sink exhaust.

## Component selection considerations

- Film: TDK B32716H1156K000 (15 µF, 1.1 kV) and B32716H8306K000 (30 µF, 800 V) in TIDA-010054 — datasheets not retrievable automatically; obtain ripple-current and ESR curves before reuse.
- HV MLCC: Knowles 2220Y1K00474KETWS2 (0.47 µF, 1 kV), TDK CGA9P1X7T2J474M250KC (0.47 µF, 630 V), KEMET C1812V104KDRACTU (0.1 µF, 1 kV).
- Prefer automotive-grade (AEC-Q200) ceramics where vibration/thermal cycling matters (all TI ceramics above are AEC-Q200).

## PCB constraints

- Ceramics adjacent to the switch pins; minimise loop to the opposite rail (KR-PCB-004, PE-PCB-002/003).
- Film capacitors with short, wide, multilayer connections (KR-PCB-006).
- HV creepage around film-capacitor leads and between DC-link polarities (KR-ISO-002).

## Verification methods

- Calculation: ΔQ→C (EC-012), DC-blocking C_min (EC-013), I_C,rms vs rating.
- Simulation: capacitor current at all corners; switch-node waveform with DC-blocking capacitor.
- Measurement: DC-link ripple voltage, capacitor case temperature, V_DS overshoot (commutation loop).

## Known limitations

- Based on one reference design (TIDA-010054) plus general practice; the two-tier placement rule is a single-reference observation.
- Film capacitor datasheets were not acquired; ripple ratings are not recorded.

## Source references

- TIDA-010054 [analysis](../../references/ti/tida-010054/analysis.md) decisions 2–3; TIDUES0 §2.3.4.5; BOM TIDRZW1; layer plots TIDRZW3.
