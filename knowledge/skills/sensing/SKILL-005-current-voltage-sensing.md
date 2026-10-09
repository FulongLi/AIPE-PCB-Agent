# SKILL-005 — Current and voltage sensing

Status: **reference-derived** (cited calculations analytically checked) · Domain: sensing ·
Index: [`SKILL-005-current-voltage-sensing.json`](SKILL-005-current-voltage-sensing.json)

## Purpose

Select and design isolated voltage and current measurement chains for
high-voltage SiC converters: sensing element, isolation device, signal format
(analog vs. delta-sigma bitstream), scaling, filtering, fast protection paths
and supplies for the isolated side.

## Applicable conditions

- DC-bus, output and battery voltages of hundreds of volts; DC and switch-node/tank currents of tens of amperes (TIDA-010054: 800 V/12.5 A primary, 500 V/20 A secondary, 45 A/70 A tank trip levels).
- Controllers with ADCs and/or sigma-delta filter peripherals (C2000 SDFM).

## Not applicable / out of scope

- Non-isolated low-side current sensing at low voltage (e.g. INA240 in the Buck V1 benchmark).
- Current transformers and Rogowski coils (not used in the references; PRD-09301 §6.3 mentions them only for gate-current metrology).

## Engineering principles

1. **Rate every barrier part for the node** (KR-SN-001). TIDA-010054 uses reinforced isolated amplifiers/modulators (7–8 kVpk class) and a reinforced Hall sensor.
2. **Scale for linear range with headroom** (KR-SN-002): 800 V → 1.57 V of a 2 V input (EC-015); 500 V → 0.76 V of ±1 V (EC-016); 12.5 A × 3 mΩ = 37.5 mV and 20 A × 1.5 mΩ = 30 mV of ±50 mV (EC-017, EC-018).
3. **Signal format by distance**: analog isolated amplifier to a nearby ADC; delta-sigma bitstream for long paths, decoded by the MCU (KR-SN-003, single-reference).
4. **Shunts need Kelvin connection and input filtering** (KR-SN-004; existing PE-PCB-004).
5. **Fast protection is a hardware path.** Hall sensor with ~100 ns OC flag tripping PWM for tank current; DESAT for switches; ADC loops are too slow (KR-SN-005).
6. **HV dividers are distributed ladders.** Eight 634 kΩ resistors share ~100 V each at 800 V (EC-021); check each element's limiting voltage and the creepage along the ladder.
7. **Isolated-side supply** may be derived from the same-reference gate-bias supply via an LDO (TIDA-010054 §3.4.3) within the bias power budget.

## Design procedure

1. List measured quantities, ranges, accuracy and bandwidth needs, and protection thresholds.
2. For each: choose element (divider, shunt, Hall) and isolation device (AMC1311/AMC1302 analog; AMC1336/AMC1306 bitstream; TMCS1133 Hall).
3. Compute scaling at maximum operating and trip values; check shunt/divider dissipation and voltage stress.
4. Choose signal format and route (analog differential to conversion stage near ADC, or bitstream + clock to SDFM with delay compensation).
5. Design input filters and the isolated supply; budget its current on the gate-bias supply if shared.
6. Define fast protection paths and their thresholds; connect to PWM trip.
7. Plan calibration (TIDA-010054 Lab 2 calibrates voltage sensing).

## Component selection considerations

- AMC1311 (2 V input, gain 1, B grade ±0.2 %), AMC1302-Q1 (±50 mV, gain 41), AMC1336 (±1 V, 1.5 GΩ input), AMC1306M05 (±50 mV, CMOS bitstream), TMCS1133 (1 MHz, OC detection, 80 Arms).
- Check current datasheet revisions: TI's design guide states 1100 VDC working voltage for TMCS1133 while the 2026 datasheet states 1343 VDC reinforced; the BOM orderable number differs from current datasheet listings.
- 0.1 % divider resistors in the HV ladders; 3 W metal-element shunts.

## PCB constraints

- Divider ladders along the creepage path with keep-out from LV nets (KR-ISO-002).
- Shunt sense routed as a tight Kelvin pair to the filter at the IC (KR-SN-004).
- Bitstream clock/data short with series termination; analog differential outputs routed as pairs.
- Isolated-side ground and supply confined to their island (KR-ISO-001).

## Verification methods

- Calculation: scaling and dissipation (EC-015…EC-018, EC-021).
- Measurement: calibration against a reference meter; trip-level tests at low voltage (TIDA-010054 Lab 2 procedure sets low trip limits and raises phase shift until trip).
- Review: insulation coordination of each barrier part.

## Known limitations

- All sensing knowledge comes from one reference design (TIDA-010054) plus Wolfspeed protection guidance.
- Accuracy budgets (tolerance, drift, CMRR) were not computed.

## Source references

- TIDA-010054 [analysis](../../references/ti/tida-010054/analysis.md) decisions 6–7; TIDUES0 §3.2–3.4; BOM.
- PRD-09301 §5.1 (protection speed), §3.4 (isolated NTC feedback).
