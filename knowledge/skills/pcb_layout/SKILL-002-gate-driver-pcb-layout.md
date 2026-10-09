# SKILL-002 — Gate driver PCB layout

Status: **reference-derived** (cited calculations analytically checked) (manufacturer guidance + observed layouts; net classes netlist-checked) ·
Domain: PCB layout · Index: [`SKILL-002-gate-driver-pcb-layout.json`](SKILL-002-gate-driver-pcb-layout.json)

## Purpose

Turn a gate-driver schematic (SKILL-001) into placement, stack-up, routing and
isolation constraints a KiCad agent can apply and a reviewer can verify:
low-inductance gate loops, intact isolation barriers, correct creepage and
noise-immune signal routing.

## Applicable conditions

- Isolated gate drivers for SiC MOSFETs on multilayer PCBs (4 layers in all three reference boards).
- Drivers integrated on the power board (TIDA-010054) or on plug-in driver boards (CGD15SG00D2, CGD1700HB2M-UNA).

## Not applicable / out of scope

- Power-stage busbar or laminated-bus design (PRD-09301 notes ~200 kW+ systems typically separate drivers from the power stage).
- Numeric creepage/clearance values: these come from the applicable standard, not from this skill.

## Engineering principles

1. **Power loop first, gate loop second.** The commutation loop dominates overshoot; never compromise it for driver routing (KR-PCB-004, PE-PCB-003).
2. **Flux cancellation in the gate loop.** Route gate and Kelvin source as wide pours on adjacent layers; put the Kelvin-source layer between the gate and other circuitry as a shield (KR-PCB-001; PRD-09301 §2.2–2.3). Wolfspeed calls this the most influential gate-inductance measure.
3. **Compact loop includes the decoupling.** The high-frequency gate current closes through the driver's rail capacitors; place them between IC and output pins (KR-PCB-002). CGD15SG00D2 places source-referenced capacitors at the source output pin; CGD1700HB2M-UNA uses 20 µF per rail close to IC and output.
4. **Short distance to the device.** Driver beside its switch (TIDA-010054: drivers on the bottom side next to each TO-247-4); plug-in boards mate directly at the gate/source pins; connectors often dominate inductance (KR-PCB-005).
5. **Isolation barriers are copper-free on every layer.** Separate control side, each driver channel, and the HV side; only barrier-rated parts cross (KR-ISO-001). Plane partitioning on CGD15SG00D2: PGND under LV side and SOURCE under HV side (inner 1); VCC primary and VDD/VSS secondary planes (inner 2).
6. **Net classes by potential.** Group nets (control/primary, low-side channel, high-side channel, DESAT midpoint, drain) and give each class pair a clearance rule (KR-ISO-003; Allegro classes confirmed in EC-024).
7. **Creepage by geometry.** Slots/cut-outs extend creepage where clearance is adequate (KR-ISO-004); DESAT diodes keep full HV distance to other groups.
8. **Noise-immune signals.** Differential pairs adjacent; single-ended segment after the receiver short; RC filters at receiving pins (KR-GD-008).

## Design procedure

1. From the schematic, assign every net to a spacing class (control, per-channel isolated, DESAT midpoint, drain/HV). Create KiCad net classes and class-pair clearance rules from the governing standard (KR-ISO-002, KR-ISO-003).
2. Define stack-up so each driver channel has a gate layer with its Kelvin-source pour on the adjacent layer, Kelvin layer facing other circuitry.
3. Place the power stage and its HF capacitors first (SKILL-003), then each driver IC at its switch, rail capacitors between IC and gate/source pins, gate resistors and discharge resistor at the device end (KR-GD-007).
4. Place the isolated bias supply for each channel inside its island, with the input CM choke and input capacitor on the primary side close to the converter (KR-IS-002).
5. Draw isolation keep-outs per barrier on all layers; add slots where creepage-limited.
6. Route DESAT: drain connection short and direct; long runs only on the HV-diode side; detection resistor/capacitor compact and shielded (PRD-09301 §6.4).
7. Route PWM/fault: differential pairs to the receiver, short single-ended links to IC inputs, filters at the IC.
8. Provide a V_GS measurement point at the device side of R_G (MMCX on CGD1700HB2M-UNA) and drain-sense attachment points.
9. Run DRC with the class rules; inspect each copper layer image for barrier violations; record gate-loop dimensions for review.

## Component selection considerations

- Gate resistors and rail capacitors in packages that keep the loop compact (2512 pulse resistors on CGD1700, MELF 0207 on CGD15SG00D2).
- Connector inductance for plug-in drivers; MMCX probe connectors for V_GS fidelity.
- Bias modules/transformers whose pin spacing supports the required creepage (e.g. transformer notches to 8 mm on CGD15SG00D2).

## PCB constraints

KR-PCB-001 … KR-PCB-005, KR-ISO-001 … KR-ISO-004, KR-IS-002; existing project rules
PE-PCB-001, PE-PCB-007, PE-PCB-008 (docs/pcb-design-rules.md).

## Verification methods

- Automated: KiCad DRC with net-class clearances; netlist check that Kelvin-source and power-source nets are distinct (KR-PCB-003 hook).
- Semi-automated: extract driver-to-device distance and decoupling-loop size (extension of `automation/verification/check_power_layout.py`).
- Human review: per-layer images across every barrier; stack-up adjacency of gate/Kelvin pours.
- Measurement: V_GS ringing with an isolated probe at the device; common-mode noise on PWM/fault lines.

## Known limitations

- TI layout observations are visual (layer plots), not net-verified; the TI design guide contains no layout section.
- Wolfspeed layout guidance is manufacturer guidance for module drivers; no AIPE parasitic extraction has quantified it.
- Creepage figures in PRD-09301 Figure 20 were not extracted.

## Source references

- PRD-09301 §1.4, §2.1–2.7, §3.8, §4, §6 (CGD1700HB2M-UNA analysis decisions 6–7).
- CGD15SG00D2 PCB layout section and fab drawing (analysis decision 7).
- TIDA-010054 layer plots (analysis decision 10).
