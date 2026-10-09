# PRD-04814 — engineering analysis

Reference: `REF-WS-PRD-04814` · Wolfspeed application note "Design Options for
SiC MOSFET Gate Bias Power Supplies", Rev 0.1, January 2025 · located through
the official CGD15SG00D2 and CGD1700HB2M-UNA product pages and cited by
PRD-06992 and PRD-09301 · analysed 2026-10-09.

> Original AIPE analysis; Wolfspeed text is not reproduced. This is guidance,
> not a tested design: the note contains no measurements.

## Decision 1 — Recommended gate-drive levels and margins

1. **Stated:** for Wolfspeed 3rd-generation devices keep transients within +19 V / −8 V maxima; recommended operation +15 V and −3 V to −4 V; ±5 % rail tolerance; −3 V gives 5 V margin to −8 V and ≈5 V to the minimum threshold. 0 V turn-off is usable in single-ended topologies (buck, boost, flyback) but half bridges benefit from −2 V to −4 V. (§1, introduction)
2. **Why:** high dv/dt in half bridges can cause parasitic turn-on; overshoot below the negative limit stresses the oxide.
3. **Problem solved:** balancing turn-off immunity against negative-transient margin.
4. **Applicability:** Wolfspeed Gen-3 C3M parts; other manufacturers and generations specify other levels — the note's purpose is multi-sourcing flexibility.
5. **Evidence:** stated (manufacturer guidance).
6. **AIPE reuse:** KR-GD-001 as a hard constraint expressed **against the selected device datasheet**, with the Wolfspeed numbers as an example basis only; KR-GD-005 for −3/−4 V selection.
7. **Verification:** compare rail tolerance + measured transient extremes with the device's absolute maxima.

## Decision 2 — Isolation capacitance of the bias supply matters

1. **Stated:** coupling capacitance across the bias supply must be very low because SiC dv/dt drives current through it, causing noise and EMC problems (§1).
2. **Why:** i = C_iso · dv/dt.
3. **Problem solved:** common-mode current into control circuitry.
4. **Applicability:** all isolated bias supplies; most relevant for high-side and fast-switching positions.
5. **Evidence:** stated; corroborated by PRD-09301 §3.8 (CM choke) and the 0.68 pF inter-winding capacitance of the CGD15SG00D2 transformer.
6. **AIPE reuse:** KR-IS-003 (select by C_iso; estimate i_CM).
7. **Verification:** i_CM = C_iso · dv/dt with datasheet C_iso; EMI pre-scan.

## Decision 3 — Topology comparison for six-channel gate bias

1. **Stated:** relative comparison of DC/DC module, single-channel flyback, push-pull and LLC, multi-channel flyback and bridge on cost, size, isolation capacitance, operation from HV bus and layout difficulty. Examples: RECOM RxxP21503D, Murata MGJ2D, Mornsun QA15115R2 modules; ADuM4138 / Si828x drivers with integrated flyback controllers; SN6501/SN6505 and LT3999 push-pull; UCC25800 LLC; UCC27524 for a microcontroller-driven bridge. (§2)
2. **Why:** best option depends on topology, layout and multi-sourcing.
3. **Problem solved:** structured selection instead of default choice.
4. **Applicability:** comparison is qualitative.
5. **Evidence:** stated table.
6. **AIPE reuse:** SKILL-004 decision table and component alternatives (only these named parts are recorded as alternatives).
7. **Verification:** quantitative check of the chosen option (power, C_iso, efficiency) from datasheets.

## Decision 4 — Sharing a low-side bias supply needs decoupling resistors

1. **Stated:** low-side devices referenced to the same node may share a supply; place decoupling resistors between drivers to avoid circulating currents during transients (§2, Figure 5).
2. **Why:** PCB parasitic inductance and dv/dt create circulating currents through shared references.
3. **Problem solved:** cost reduction without coupling paths.
4. **Applicability:** three-phase inverter low sides, totem-pole PFC low sides. PRD-09301 §3.6 lists additional trade-offs (reduced maximum f_sw, symmetry) and notes it does not apply with source-referenced current-viewing resistors.
5. **Evidence:** stated in two Wolfspeed documents.
6. **AIPE reuse:** KR-IS-004 (human-review requirement when sharing).
7. **Verification:** power budget for all shared drivers; layout symmetry review.

## Decision 5 — Flexible split-rail circuits (BOM-configurable V_GS)

1. **Stated:** four example circuits generate Vcc/Vss from (1) fixed DC/DC + resistor–Zener, (2) fixed DC/DC + linear regulator + resistor–Zener, (3) adjustable DC/DC + resistor–Zener, (4) dual-output DC/DC + resistor–Zener with jumpers; tables give populated values for +15/−3 … +20/−5 V (4.99 kΩ, Zener 2–5 V, 0.1 µF + 10 µF). (§3)
2. **Why:** one PCB supports multiple SiC suppliers with minor BOM change.
3. **Problem solved:** multi-sourcing of SiC devices with different V_GS recommendations.
4. **Applicability:** the DC/DC must operate over the needed output range (circuit 3); the linear regulator variant suits multi-output flyback cross-regulation.
5. **Evidence:** stated tables.
6. **AIPE reuse:** CB-IS-004 with configuration table; KR-GD-006 (design for configurable gate levels — recommendation).
7. **Verification:** solve each configuration for Zener current at min/max load and dissipation.

## Decision 6 — Gate–source capacitance only with a Kelvin source

1. **Stated:** a small capacitor or RC between gate and Kelvin source can reduce overshoot/undershoot; do **not** add an external gate–source capacitor on devices without a Kelvin source (e.g. TO-247-3) because it can increase oscillation. (§1)
2. **Why:** with a shared source the capacitor forms a resonant loop with common-source inductance.
3. **Problem solved:** gate overshoot without destabilising three-lead packages.
4. **Applicability:** four-terminal packages only.
5. **Evidence:** stated; PRD-06933 adds that external C_GS lowers PTO peak but lengthens the excursion.
6. **AIPE reuse:** KR-GD-010 (hard constraint scoped to three-lead packages, single manufacturer guidance flagged).
7. **Verification:** package check in the BOM + human review of any gate–source capacitor.

## Source-quality note

Page 3 contains an unrelated paragraph about turn-on loss measurement (240 V,
17.2 A, "figure 7") that does not belong to this note. It was excluded.
