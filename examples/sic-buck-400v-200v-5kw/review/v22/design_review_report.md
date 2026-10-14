# V2.2 engineering review and bounded redesign

**400 V → 200 V, 5 kW, 25 A, 50 kHz synchronous SiC buck. Human engineering review required. Fabrication and energisation are not approved.**

This revision implements feasible corrections from the independent [Stage A review](stage_a_independent_review.md). It preserves the two-board/four-layer architecture and the C4MS025120K, UCC21710-Q1 and TMS320F28335 selections. It is not a claim that the remaining high-power, insulation or mechanical problems have been solved. Frozen V2/V2.1 releases remain unchanged.

## Accepted changes

| Change | Engineering reason | Verification / limitation |
|---|---|---|
| R82: 9.09 k from 3V3 → 6.65 k from REF2V5_PB; R83: 1 k → 1.01 k | TMCS1133 Cxx has a fixed 0.33 V zero output. The old reference moved with 3V3 and injected false current. | Actual model/schematic/PCB pin equality; nominal new reference 0.329634 V. Sensor, reference, resistor and ADC errors still require calibration. |
| R57: 1 k 0805 placeholder → Panasonic ERJP08F1600V, 160 ohm 1%, 0.66 W 1206, at (169, 137.25) mm, B.Cu | TI's dual-positive RLIM equation cannot support two maximum-current AMC1311 loads with 1 k. A larger package also needs a new physical location. | Required design current 20.4 mA, typical equation limit 215 ohm. Local tracks rerouted; native DRC clean. Startup and hot-load regulator qualification remain open. |
| Dedicated 100 nF C76/U4, C77/U8, C78/U10 and C79/U11 | Reset/fault logic previously depended on distant bypasses. | Actual copper-aware placement search; local ground vias and bounded routes to existing VCC vias, avoiding via-in-pad. Native DRC and netlist equality pass. |
| Correct firmware calibration requirements and RLIM calculation | Previous documentation used a nonexistent sensor VREF output, an unsupported ratiometric correction and the wrong RLIM numerator. | Formula now subtracts a zero-current calibrated offset; sensitivity is not divided by VREF/0.33. Native circuit and documentation agree. No firmware was implemented. |
| Wider schematic margins, shorter title blocks and corrected PCB plot scales | Existing labels crossed drawing frames; the power layout PDF clipped board geometry. | Reusable drawing generator adjusted; native XML equality retained. Each regenerated PDF page rendered and reviewed. |

Power board: 237 footprint/model entries. Control board: 211, including the four additions. Consolidated BOM: 448 entries, 17 DNP. Schematics: 7 power pages and 9 control pages; PCB review PDFs contain six views each. Native manufacturing exports include four copper layers, both silkscreens, mask, paste, drills, placement, BOM and STEP. These are **review outputs**, not a production release.

## Measured benefits and limits

[comparison.md](comparison.md) and [validation.json](validation.json) record the native measurements, source hashes and calculation inputs. The nearest-bypass maximum distances for U4/U8/U10/U11 change from 26.50/10.39/7.20/9.59 mm to approximately 1.51/1.00/4.41/4.26 mm. For U10 the generic metric includes input pins 12/13 tied to 3V3; its actual VCC pin 14 changes from 6.60 to 3.71 mm. These are pad distances, not extracted loop inductance; some supply paths use an additional layer transition to avoid existing copper. DSP, ADC and oscillator placement remain subject to the Stage A findings.

The current-reference change removes the old divider's ±0.327 A supply-induced error contribution for an assumed ±5% 3V3 variation. New nominal reference mismatch is −0.366 mV (−7.31 mA reference-equivalent); that number is not total current-measurement accuracy. An independent REF3125 reference cannot track each sensor's individual offset or cancel ADC errors.

For R57, 160 ohm with +1% tolerance, 4.935 V and an **assumed** 60 ohm internal switch resistance gives 22.27 mA by the datasheet equation, versus the 20.4 mA load budget. The 60 ohm value is a stress assumption, not a published maximum. Conservative normal-operation resistor-plus-switch dissipation is about 0.204 W; the selected resistor's ambient-derating estimate at 100°C is 0.427 W. This comparison does not qualify startup pulses, regulator dynamics, board temperature or continuous midpoint operation. Gate-channel RLIM placeholders remain separately open.

Recalculation retained 19 analytical invariants. Nominal inductor ripple is about 7.34 A peak-to-peak and the corner overload peak about 32.01 A in that model. Predicted semiconductor loss, junction temperature and efficiency remain conditional on the assumptions catalogued in `design/calculations.md`; they are not measured performance.

## Verification evidence

- Both native ERC reports: zero findings. Both native DRC reports: zero violations, zero unconnected items, zero schematic-parity findings. Latest source hashes and report paths are in `validation.json`.
- Independent exported XML, board pad nets and circuit models agree on 648 assigned power pins and 675 control pins. The release comparison allows only R82.1's reviewed net change and the eight added capacitor pins; unrelated changes fail the gate.
- Custom safety constraints were not relaxed to accept the ECO. Existing pin-field exceptions remain explicit review items; zero DRC findings do not establish compliance with an insulation standard.
- Frozen releases are checked against every SHA-256 manifest entry: 868 V2 files and 1015 V2.1 files.
- Native export manifests bind each manufactured/review output to the CAD input and record actual command exit codes. Some supplied 3D models remain incomplete; STEP is not mechanical sign-off.
- Unit/native regression: 345 tests ran in 78.475 s, 343 passed and 2 skipped (optional JSON-schema dependency and the local reference cache are absent). Full results are in `regression_results.txt`. The reusable replay uses frozen-board identity checks and refuses a geometry candidate that misses its routing/length criteria.

Two representative ngspice regressions were rerun into `simulation_regression/`, using the **unchanged behavioural power-stage models**: nominal open loop gives 200.04 V mean, 0.180 V ripple and 7.35 A inductor ripple; the 12.5 → 25 A closed-loop step gives −7.54 V excursion and 0.76 ms recovery. The assumed cascade controller is not DSP firmware. These models do not include the corrected sense-bias regulator, actual PCB parasitics, semiconductor switching-loss detail or measured EMI. Their successful execution does not qualify those elements.

## Unresolved work and rejected automatic changes

The Stage A register is the authoritative prioritised issue list. Disposition:

| Issues | V2.2 disposition |
|---|---|
| E22-01 | Circuit/reference-law error corrected; calibration and sensing accuracy remain to be validated. |
| E22-02 | Placeholder resistor and erroneous sizing equation corrected; startup/temperature/continuous-load qualification remains open. |
| E22-03 | **Open blocker:** U2/U4/U5 VEEA requires a physically quiet feedback star. Existing plane connectivity was not relabelled as compliant. |
| E22-04, E22-05, E22-10 | **Open blockers:** insulation exceptions, heatsink/tab/hardware clearance, and unsupported control-board overhang need a coordinated mechanical/insulation ECO. |
| E22-06, E22-08, E22-09 | **Open:** commutation loop, current bottlenecks and switching-node EMI. No copper-current capability or EMI pass is claimed. |
| E22-07 | **Open:** a shorter clamp-route candidate was rejected because its Kelvin-pour projection worsened. Original gate routing retained. |
| E22-11 | Four local bypasses implemented and measured; impedance/transient immunity still needs bench validation. |
| E22-12 through E22-17 | Retained open with the corrected sensor law. Firmware, protection timing, magnetics, capacitors, precharge and reverse-energy behaviour need independent review. |
| E22-18 | Plot framing and margins corrected; conventional vertical half-bridge presentation and further fine annotation cleanup remain future drawing improvements. |

A routed clamp candidate passed native DRC and shortened LS_CLMP copper from 20.7606 to 18.9801 mm (8.58%), retaining three vias. However, the aggregate low-side gate-network projection over Kelvin-source copper fell from about 24.4% to 22.1%. Without a field extraction or measured loop response, shorter copper alone does not establish improvement. The candidate was rejected and the original route retained; [clamp_candidate_rejected.json](clamp_candidate_rejected.json) records both geometries and the candidate's native check. This explicitly prevents a length-only optimisation from being promoted as a verified gate-drive improvement.

Moving an input HF capacitor between the MOSFETs looks attractive if only the sum of endpoint distances is minimised, but that region contains Kelvin/test pads, SW via arrays and the heatsink keepout. Moving capacitors farther right can shorten their distance to Q2 while lengthening the VIN connection to Q1. Neither demonstrates a smaller complete commutation loop. Enlarging high-current copper at the sensor can consume the isolation gap or couple more switching copper into the control region. These changes were not accepted on endpoint-distance or cosmetic grounds alone.

Exact next ECO requirements are in [remaining_engineering_ecos.md](remaining_engineering_ecos.md). A revised mechanical drawing and field/thermal or bench evidence are needed before choosing a larger floorplan change. The intended outcome of this PR is human engineering review, not automatic merge or approval to operate a 400 V prototype.

## Reproduction

Use the already installed KiCad 10.0.7 and repository Python environment; no new software was installed. Regenerate both circuit models, then `generate_sic_schematics --board all --erc --pdf --bom --gates --readability`. Replay `refine_sic_v22 --board all` using KiCad's Python. Run native DRC, `netlist_check_sic` and `check_sic_layout` for each board. Export to fresh directories with `export_outputs` and all four copper layers plus F/B silkscreen, mask/paste/drill; PCB PDF scales are 1.1 power and 2.2 control. Finally run `report_sic_v22` under KiCad Python and the regression suite. Frozen snapshots are inputs, never output destinations.

Primary datasheet references and evidence classifications are linked in the Stage A report. Reusable findings have also been added to `knowledge/lessons/v22-independent-review.md`.

The [native layout comparisons](comparison.md) use the same coordinate windows and scale for each revision.
`visual_artifacts.json` records their input/output hashes and those of all four final review PDFs.
All 28 PDF pages were rendered and inspected, with enlarged checks of the modified control-supply and fault-logic sheets.
Frame clipping and long title overflow are corrected. This is not a claim of perfect schematic presentation:
the geometric readability checker still flags local name-tag/field crowding and wire crossings in the inherited wired drawing style,
which remain in E22-18 for follow-up; none changes the independently verified netlist.
