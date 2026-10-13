# V2.2 Stage A — independent engineering review

Review baseline: upstream `main`, `294b10e`, V2.1 tree. Prepared before changing the circuit or PCB. Reviewer: AI engineering assistant; no claim of licensed sign-off or physical testing. Task: `task131026.txt`.

## Assessment and evidence boundary

The existing design is an extensive CAD prototype, not ready for fabrication or energisation. Native electrical connectivity is internally consistent, but this does not establish circuit correctness, insulation compliance, thermal capability or transient immunity. Two additional circuit problems were independently identified: the current-sensor offset reference incorrectly tracks its supply, and the isolated voltage-sensor supply's midpoint current-limit resistor is too large. These take priority over route appearance.

The 400 V / 200 V / 5 kW / 25 A / 50 kHz specification, C4MS025120K, UCC21710-Q1, TMS320F28335 and separate four-layer boards remain appropriate development constraints. There is no evidence justifying replacement of the major architecture at this stage.

Evidence generated directly from the baseline:

- `baseline/source_integrity.json`: all 868 V2 and 1015 V2.1 manifest entries verified; both frozen releases intact. Independently exported schematic XML agrees with the circuit models on 648 assigned power-board pins and 667 control-board pins.
- `baseline/netlist_power.xml` and `netlist_control.xml`: actual KiCad connectivity, not inferred from prose.
- `baseline/layout_metrics_power.json`, `layout_metrics_control.json`: rerun measurements of live PCB files; all four copper layers included. The accompanying Markdown describes metrics and limits.
- `baseline/geometry_power.json`, `power_physical.json`: actual pads, vias, tracks, filled copper and courtyard geometry. Copper-neck estimates are erosion-based screening proxies, not a current-rating certification or a precise minimum cross-section.
- Visual inspection of all six pages in each existing PCB PDF and the power-board 3D view. The large power-board PDF is clipped; control-board plots fit. Standing MOSFET/heatsink compatibility is not established by a collision-free schematic or approximate 3D view.

Measurements are explicitly CAD measurements. Numbers calculated from an electrical model are estimates; datasheet limits apply only under their specified conditions. Existing ngspice results are behavioural simulations without extracted package/board parasitics or validated hardware firmware.

## Prioritised issue register

| ID | Priority / evidence | Finding and consequence | Planned disposition and acceptance |
|---|---|---|---|
| E22-01 | P0, actual netlist + TI datasheet | R82/R83 derive ISENSE_REF from 3V3. TMCS1133 Cxx has a **fixed 0.33 V** internal zero-current output, independent of VS. Reference-supply movement creates false measured current. | Use the existing REF3125 reference, 6.65 k / 1.01 k divider. Verify changed pin nets, BOM, ADC offset calculation, zero-current calibration requirement. |
| E22-02 | P0, actual netlist + maximum supply current | U5's R57 = 1 k is a placeholder. Two AMC1311B at 5 V require up to 19.4 mA before feedback margin. UCC14141 dual-positive Eq. 9 gives only 4.85 mA with 1 k + 30 ohm. | Recalculate RLIM with explicit current, resistance, temperature and power assumptions; fit a suitably rated resistor. Bench startup/load regulation remains mandatory. |
| E22-03 | P0, actual copper + TI layout guidance | U2/U4/U5 VEEA pin 35 and feedback returns share the power VEE net/plane. Notes asserting a quiet single-point return do not prove one exists physically. | A separate quiet feedback star requires coordinated local copper/routing changes. Do not declare solved by a net-name change. Retain as a blocking issue unless full physical separation is verified. |
| E22-04 | P0, rule and pad geometry | Local clearance exceptions include driver barrier pad gaps 7.24 mm versus the design's 9 mm target; bias module 8.09 mm, sensor 7.74 mm. Slots increase surface path but not air clearance. DESAT SMA pads have about 1.49 mm separation; HV resistor fields about 1.79 mm. | Human insulation coordination: working voltage, pollution, material group, altitude, applicable standard and component ratings. No new waivers to make DRC green. Explicit fabrication hold. |
| E22-05 | P0, actual assembly geometry | Control board transformed into the proposed assembly extends to y=234 mm beyond power-board y=180 mm; two mounting holes lack support. MOSFET drain tabs, insulating interfaces, screw torque and standing lead bends not qualified. | Mechanical drawing and bracket/insulation design required. Preserve PCB architecture; do not claim assembly approval. |
| E22-06 | P1, measured geometry | Nearest HF input cap C1 is 8.37 mm from Q1 drain but 41.16 mm from Q2 power source. All HF capacitors lie west of Q1. Complete commutation loop remains large. | Compare local capacitor relocation against isolation/heatsink/driver constraints. Reject improvement that merely shortens one endpoint or cuts a return plane. Full floorplan candidate remains a future engineering ECO if local placement cannot pass. |
| E22-07 | P1, measured geometry | Low-side gate-related copper totals 82.13 mm / 14 vias versus high-side 39.72 mm; only roughly 24%/22% projects over its Kelvin-source pour. Net-total length is not closed-loop inductance. | Evaluate local low-side gate shelf changes; preserve independent Kelvin source, short clamp path and return continuity. Report actual geometry, not an invented nH reduction. |
| E22-08 | P1, filled-copper analysis | SW In2 path Q1–L1 has an 11.78 mm neck proxy; VOUT_L to sensor is principally a 4.8 mm F.Cu path; VOUT lower-layer neck is 3.2 mm. TMCS pin region is a local current-density risk. | Require electrothermal validation and manufacturer sensor land-pattern review. Compare parallel copper/via options, accounting for aggregate current and proximity to SELV. IPC-style estimates alone cannot close this item. |
| E22-09 | P1, copper area + physical inference | SW copper about 3660 mm², including 3237 mm² on In2, couples to adjacent copper and enclosure. Larger copper lowers resistance but can raise common-mode current. | Keep thermal/EMI tradeoff explicit; measure dv/dt and conducted/radiated emissions with the intended chassis. Do not minimise area at the expense of current necks. |
| E22-10 | P1, actual geometry | L1 courtyard-to-heatsink distance 18.31 mm, RT1 9.51 mm, RV1 12.03 mm. Some projected HV/PE copper overlaps the heatsink region on B.Cu; F.Cu HF-cap PGND spacing is 4.955 mm against 5 mm intent. | Mechanical and insulation blockers remain; no rounding down acceptance. Actual heatsink projection/mount hardware must be agreed before moving L1 against the board edge. |
| E22-11 | P1, control geometry | Reset U4 nearest 3V3 bypass is 26.5 mm away. Logic U8/U11/U10 bypass distances are 10.39/9.59/6.60 mm. Long supply loops can upset a hardware fault chain. | Add dedicated 100 nF bypasses with direct local supply connections and ground vias. Verify actual distance and native DRC; keep existing bulk/decoupling. |
| E22-12 | P1, control geometry | DSP bypasses mostly local (worst about 5.38 mm); ADC conditioning capacitors 6.83–14.75 mm from pins, oscillator bypass about 3.96 mm. In1 ground is broadly continuous but DSP antipads merge locally. | Preserve uninterrupted returns; review ADC settling with source impedance and acquisition window. No unjustified length matching on slow analogue signals. |
| E22-13 | P1, connectivity + timing assumptions | Asynchronous fault latch, PWM hardware gates and direct OC→TZ2 exist. Cross-input interlock does not create dead time. No validated firmware, reset sequencing or measured total fault latency. | Preserve fail-off truth table. Require startup/brownout/unplug/OC/DESAT/OTP/OVP injection and dead-time measurement before high voltage. |
| E22-14 | P1, electrical calculation | 1200 V MOSFET nominal static voltage margin is ample at 440 V, but 15 V drive has no published maximum RDS(on). Switching-loss scaling and standing-lead inductance are assumptions. | Retain +15/−4 V and 10/3.3 ohm start values; double-pulse test over temperature. Separate Eon/Eoff, diode recovery and Coss accounting to avoid unexamined double counting. |
| E22-15 | P1, calculation + procurement | Custom choke saturation, fringing, winding loss, DC-link ripple sharing/ESL and capacitor lifetime are not established by ideal L/C values. | Require magnetic vendor design, impedance/ripple-current and temperature tests. Recalculate corner operating points; retain thermal/current derating assumptions explicitly. |
| E22-16 | P0, circuit + procurement | Precharge PTC selection remains unresolved; relay coil/hold behaviour and DC interruption not fully qualified. MOV/fuse coordination, reverse energy and discharge after disconnection need system-level tests. | Do not release a BOM with RT1 placeholder as production-ready. Evaluate independent discharge verification and faulted precharge. |
| E22-17 | P1, datasheet | TMCS1133 C2A at 3.3 V measures only limited negative current (about −4.6 A useful range); this is not a symmetric bidirectional 25 A measurement channel. | Keep motoring/buck operating assumption; prohibit unqualified reverse-energy operation. Calibrate current zero; OC threshold uses its separate 20 mV/A law. |
| E22-18 | P2, plot inspection | Power-board PDF clips outline/copper near top and left. Existing functional schematic drawing remains dense and label-heavy in places. | Correct native plot framing; inspect every regenerated page. Preserve wired functional blocks; improve presentation only where connectivity equality is verified. |

P0 means a release/energisation blocker, not a claim that every item will be solved in this revision. P1 items also need disposition before operation at rated power. Drawing fixes cannot close electrical or physical risks.

## Independent circuit checks and calculations

The actual half bridge maps Q1 drain to VIN, power source to SW, Kelvin source to KS_H, gate to G_H; Q2 drain to SW, source to PGND, Kelvin to KS_L and gate to G_L. The UCC21710 COM pins return to the corresponding Kelvin nets; separate OUTH/OUTL and clamp networks exist. AMC1311 supply/shutdown pin connectivity and the hardware fault-gating polarity were checked in the XML/model. These checks establish intended connections, not analogue stability or immunity.

At 360/400/440 V, ideal duty ratios are 0.5556/0.5000/0.4545. The DC-link capacitor RMS switching current is approximately `25*sqrt(D*(1-D))`, near **12.5 A** at nominal load; total capacitance alone is insufficient without current sharing, ESR, ESL and hot-life analysis. For the chosen inductance L, inductor ripple is `200*(1-D)/(50000*L)` and peak is `25+deltaI/2`; the actual bias-dependent inductance must be substituted. Output step hold-up satisfies `deltaV ≈ deltaI_load*response_time/Cout + deltaI_load*ESR`; behavioural control assumptions are not measured response time.

Using 28 mΩ at 15 V and the assumed 1.88 hot resistance multiplier, the pair's conduction estimate before ripple is `25²*0.028*1.88 = 32.9 W`. This is an estimate, not a worst-case datasheet guarantee. A 60 nH commutation loop at the assumed 2.5 A/ns gives **150 V** overshoot, illustrating why the previous 90 V allowance cannot be treated as verified. Gate charge 125 nC at 50 kHz is 6.25 mA mean charge-transfer current per channel, but does not replace peak/imbalance and effective capacitance checks.

Old current reference: `3.3*1/10.09 = 0.327057 V`. A ±5% 3V3 variation contributes ±16.35 mV reference movement, or ±0.327 A at 50 mV/A, without matching sensor-zero movement. Proposed reference: `2.5*1.01/(6.65+1.01) = 0.329634 V`; nominal mismatch versus 0.330 V is −0.366 mV (−7.31 mA reference-equivalent). REF3125 tolerance, divider tolerance, sensor offset/gain and ADC errors remain. Added reference load is about 0.326 mA.

For the 5 V sense rail, a 20.4 mA design load includes both 9.7 mA maximum AMC1311 loads and 1 mA allowance. Eq. 9 gives `Rlim <= 5/0.0204 - 30 = 215 ohm` at typical internal resistance. A 160 ohm candidate gives margin with a **non-guaranteed engineering stress assumption** of 60 ohm internal resistance: `4.935/(161.6+60)=22.27 mA`. Final thermal and startup behaviour must be checked; do not pass an 0805 placeholder solely from its nominal ohmic value.

## Alternatives and implementation gates

| Alternative | Benefit | Cost / risk | Decision |
|---|---|---|---|
| A: local circuit ECO, bypass additions, constrained copper refinements | Corrects newly identified errors while retaining frozen design provenance; bounded native CAD validation | Does not resolve all commutation, current-density or mechanical issues | Implement feasible, independently verifiable changes in V2.2 |
| B: move HF capacitors between/behind the two MOSFETs; paired gate-return routing | Potentially reduces full loop area and gate coupling | Existing heatsink footprint, isolation strip and driver shelves constrain placement; requires mechanical and current-path rework | Evaluate geometry; carry exact unresolved ECO requirements if a safe local change cannot be demonstrated |
| C: move drivers/HV boundary and repartition assembly | More freedom for magnetic/switching loops and supported control-board mounting | Extensive requalification, mechanical redesign, new routing and insulation constraints | Not justified as an automatic architectural change in this revision |

Implementation order: preserve this review → fix offset reference and sense-bias sizing → local control bypasses → evaluate constrained power-loop refinements → redraw/export → regenerate native checks and measurement comparisons → independent review PR. No new software is required.

Every material accepted ECO must have actual schematic/PCB/model equality, native ERC and DRC including unconnected items, unchanged intended safety constraints, affected calculations, and a before/after geometry record. Reject candidates with worse spacing or unresolved new routing. Preserve V2/V2.1 file hashes. Reports must disclose both improvements and open blockers. Final PR must not be merged automatically.

## Primary references consulted

- [TI TMCS1133, SBOSAG0E](https://www.ti.com/lit/ds/symlink/tmcs1133.pdf), §8.3.5 fixed internal zero-current reference and OC threshold equation.
- [TI AMC1311, SBAS786C](https://www.ti.com/lit/ds/symlink/amc1311.pdf), 4.5–5.5 V high-side supply-current maximum.
- [TI UCC14141-Q1, SLUSF10B](https://www.ti.com/lit/ds/symlink/ucc14141-q1.pdf), Eq. 9 dual-positive RLIM selection, pin 35 and §9.5 layout guidance.
- [TI UCC21710-Q1, SLUSDH8D](https://www.ti.com/lit/ds/symlink/ucc21710-q1.pdf), pinout, interlock, clamp, OC and supply bypass requirements.
- [Wolfspeed C4MS025120K, Rev. 2](https://assets.wolfspeed.com/uploads/2025/11/Wolfspeed_C4MS025120K_data_sheet.pdf), operating limits, pinout and condition-dependent switching data.
- Existing `knowledge/` TI TIDA-010054 and Wolfspeed CGD1700HB2M-UNA analyses were reviewed critically: a DAB's ZVS capacitor/thermal behaviour does not directly validate a hard-switched buck; gate/Kelvin layout guidance transfers more directly.

Manufacturer documents were rechecked independently. Existing reports serve as traceable prior assumptions, not evidence that the prototype meets its ratings.
