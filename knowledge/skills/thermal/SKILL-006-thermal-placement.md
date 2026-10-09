# SKILL-006 — Power electronics thermal placement

Status: **reference-derived** (cited calculations analytically checked) · Domain: thermal ·
Index: [`SKILL-006-thermal-placement.json`](SKILL-006-thermal-placement.json)

## Purpose

Place power semiconductors, heat sinks, gate drivers and temperature sensors so
that each device's loss stays inside its thermal-path limit at worst-case
ambient, insulation between shared-sink devices is maintained, and temperature
feedback is used correctly.

## Applicable conditions

- Through-hole or module SiC devices on heat sinks with natural or forced air (TIDA-010054: 4 sinks, 2 TO-247-4 each, two 12 V fans).
- Boards where gate drivers must sit next to devices that are mounted to heat sinks.

## Not applicable / out of scope

- Liquid cooling, baseplate-module cold plates, transient thermal impedance/power cycling (Wolfspeed lifetime papers were not acquired).
- Detailed CFD.

## Engineering principles

1. **Steady-state budget along the real path.** P_max = (T_J,max − T_A,max)/R_th,total, with R_th,total = R_th,JC + R_th,interface + the device's effective share of the sink resistance (KR-TH-001). TI's model gives 50 W (C3M0075120K) and 69 W (C3M0030090K) at 40 °C ambient with two devices per 0.5 °C/W sink and 0.1 °C/W pads (EC-019, EC-020). TI does not explain the factor 2 on the sink term — AIPE reads it as two devices sharing one sink.
2. **Insulate shared sinks.** Exposed-drain packages on a common sink need a rated insulating interface, whose resistance enters the budget (KR-TH-002; TI uses CD-02-05-247 pads).
3. **Loss estimates first.** Conduction (I_rms²·R_DS(on) at temperature) plus switching (turn-off only under ZVS; add turn-on where ZVS is lost) (TIDUES0 §2.3.5). Losses change with operating point.
4. **Thermal placement must not lengthen electrical loops.** In TIDA-010054 the drivers sit on the opposite board side directly beside each device's leads, keeping gate loops short while the devices stand on the sinks (observed).
5. **Temperature feedback ≠ junction temperature.** NTC/thermistor readings track substrate or board temperature; isolate their feedback and calibrate (KR-TH-003; CB-PR-002).

## Design procedure

1. Compute per-device losses over the operating envelope (worst case, including loss of ZVS).
2. Choose sink, interface and airflow; compute P_max per device with the shared-sink model; require margin over worst-case loss.
3. Place devices on sinks so heat sources are spread and airflow is not blocked; keep film capacitors and magnetics out of exhaust where possible (AIPE recommendation without source evidence — review).
4. Place gate drivers and decoupling directly at the device leads (opposite side if needed) — SKILL-002.
5. Place thermistors where they represent the quantity to supervise; route through the driver's isolated analog channel or an isolator.
6. Plan measurement: case/sink thermocouples during full-load tests.

## Component selection considerations

- Heat sinks: thermal resistance at the actual airflow (TI: Ohmite CR201-50VE, 0.5 °C/W datasheet value).
- Interface pads: voltage rating and thermal resistance (Wakefield-Vette CD-02-05-247, 0.1 °C/W per TI).
- Fans: airflow and supply budget on the auxiliary rail (TI fans raise 12 V current from 1.14 A to 1.43 A).
- Temperature sensors: TI TMP6131 thermistor on the high-side driver AIN; module NTC on CGD1700HB2M-UNA.

## PCB constraints

- Keep-outs around heat-sink footprints and mounting hardware; creepage from sink (if grounded) to HV pins.
- Driver placement as in SKILL-002 (KR-PCB-005).

## Verification methods

- Calculation: P_max (EC-019, EC-020) against loss estimates.
- Simulation: PLECS-style thermal simulation (TI provides a PLECS model, not acquired).
- Measurement: temperatures at full load and worst ambient.

## Known limitations

- Single reference for the thermal budget (TIDA-010054); TI's model assumes 40 °C ambient and equal sharing; TI warns the design is only intended for room ambient.
- No transient or lifetime analysis.

## Source references

- TIDA-010054 [analysis](../../references/ti/tida-010054/analysis.md) decisions 9–10; TIDUES0 §2.3.5–2.3.5.6.
- CGD1700HB2M-UNA [analysis](../../references/wolfspeed/cgd1700hb2m-una/analysis.md) decision 8; PRD-09301 §3.4.
