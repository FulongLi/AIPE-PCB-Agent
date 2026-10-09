# SKILL-004 — Isolated gate bias power supply design

Status: **reference-derived** (cited calculations analytically checked) · Domain: power electronics ·
Index: [`SKILL-004-isolated-gate-bias-supply.json`](SKILL-004-isolated-gate-bias-supply.json)

## Purpose

Choose and design the isolated supply that powers each SiC gate driver: topology,
rail generation (+V/−V around the source), power budget, isolation capacitance,
regulation and input protection.

## Applicable conditions

- Isolated SiC gate drivers needing a floating bipolar (or unipolar) supply per reference potential.
- Regulated low-voltage auxiliary input (12 V in all references) or, for some topologies, the HV bus.

## Not applicable / out of scope

- Bootstrap supplies (TIDA-010054 provides an untested bootstrap option only).
- Auxiliary supplies for controllers and logic (non-isolated).

## Engineering principles

1. **Budget the gate power.** P = Q_G · f_sw · (V_DD − V_EE) per device plus quiescent and shared loads must fit the supply rating at the actual input voltage (KR-IS-001). Worked examples: 118 nC, 18 V, 2 W → f_sw ≤ 940 kHz (EC-003); 1330 nC, 19 V, 2 W → 79 kHz, ~70 kHz with margin (EC-004). TI's TIDA-010054 uses an expression with an extra factor 2 (EC-014) — a recorded conflict; the Wolfspeed form follows from charge moved per cycle.
2. **Minimise isolation capacitance.** Common-mode current i = C_iso·dv/dt flows into the control side (KR-IS-003). The CGD15SG00D2 LLC transformer has 0.68 pF typ. inter-winding capacitance; PRD-04814 rates topologies qualitatively (module/LLC/push-pull low; multi-output flyback high).
3. **Block the common-mode path.** A CM choke at the converter input, close to it, with the input capacitor between choke and converter (KR-IS-002).
4. **Generate rails around the source.** Options: dual-output modules, single output + resistor–Zener split, or LDO post-regulation (CB-IS-001/003/004). The Zener split's negative rail is load dependent (CGD15SG00D2 measures −3.3 V with a 3.9 V Zener).
5. **Regulation to the need.** Unregulated module outputs suit most applications; characterisation and non-standard levels need LDOs with ≥0.3 V headroom (KR-IS-005; PRD-06992 §4.3.4). Changing V_DD shifts DESAT blanking when it is biased from V_DD.
6. **Share only with review.** Same-reference low sides may share a supply with decoupling resistors and a combined budget; TI provided but did not test sharing (KR-IS-004).
7. **Protect the auxiliary input** feeding all bias supplies (KR-PR-003; CB-PR-001).

## Design procedure

1. List switch positions and their reference nodes; group positions that share a reference.
2. For each supply compute required power (KR-IS-001) with margin; note input-voltage-dependent ratings (UCC14141-Q1: 1.5 W only at 10.8–13.2 V).
3. Select topology with the PRD-04814 comparison: module (simplest, certified, low C_iso, costlier), single-channel LLC (very low EMI/C_iso, specialised control — UCC25800), push-pull (small transformer, single rail — SN6501/SN6505, LT3999), flyback (flexible, higher C_iso/EMI — ADuM4138, Si828x integrated), multi-output flyback/bridge (lowest cost, hard layout, cross-regulation).
4. Choose rail generation and levels per SKILL-001/KR-GD-001; compute Zener/LDO operating points at min/max load.
5. Add input CM choke and input capacitor; local output decoupling sized for gate charge.
6. Verify isolation rating and creepage of transformer/module against the insulation requirement; estimate i_CM.
7. Define power-good/UVLO interaction with the driver.

## Component selection considerations

- Modules: RECOM R12P21503D (+15/−3 V, 2 W), Murata MGJ2D122005SC (+20/−5 V, 2 W) — only the named alternatives from sources are recorded (Mornsun QA15115R2, MGJ2D series).
- Integrated-transformer IC module: TI UCC14141-Q1 (+15/−4 V configured; RLIM sets current limit).
- Discrete LLC: TI UCC25800-Q1 + Würth 750319177 transformer.
- Post-regulators: Analog Devices LT3082 (positive, 10 µA SET) and LT3015 (negative) on CGD1700HB2M-UNA -R variants.

## PCB constraints

- Each supply inside its driver's isolated island; transformer/module straddles the barrier with required creepage (slots/notches) (KR-ISO-001, KR-ISO-004).
- CM choke and input capacitor order (KR-IS-002); output capacitors within the gate loop (KR-PCB-002).

## Verification methods

- Calculation: power budget (EC-003/EC-004/EC-014), LDO set-points (EC-005…EC-007), LLC frequency (EC-008).
- Measurement: rail regulation versus load and input (Wolfspeed Figure 5 method), ripple during switching, common-mode current/EMI pre-scan.
- Review: isolation coordination of the bias part; sharing configurations.

## Known limitations

- Module datasheets for R12P21503D and MGJ2D122005SC could not be verified automatically; their parameters come from Wolfspeed documents.
- PRD-04814 comparison is qualitative; no efficiency or C_iso numbers per topology.

## Source references

- PRD-04814 [analysis](../../references/wolfspeed/prd-04814/analysis.md); CGD15SG00D2 [analysis](../../references/wolfspeed/cgd15sg00d2/analysis.md) decisions 3–4; CGD1700HB2M-UNA [analysis](../../references/wolfspeed/cgd1700hb2m-una/analysis.md) decision 5; TIDA-010054 [analysis](../../references/ti/tida-010054/analysis.md) decisions 4, 7, 8.
