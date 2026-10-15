# V3 clean-sheet engineering review

**V3 is complete as an editable engineering-prototype design and review package. Both routed PCBs are CAD VERIFIED. Executed behavioural cases are SIMULATION VERIFIED within their stated models. HARDWARE VALIDATION PENDING; RELEASE BLOCKED.** This is not a fabrication, procurement or energisation approval. The non-isolated 200 V output is hazardous.

Baseline: `20e96fdfa5ea76649daa416ee70b7ea7798a319d` (upstream main, V2.2). V1 and V2/V2.1/V2.2 directories are unchanged. V3 has its own requirements, circuit models, libraries, calculations, editable projects, simulation inputs, native checks and manufacturing exports. `package_manifest.json` records the review-file hashes.

## Architecture and electrical decisions

The selected architecture uses a 250 × 180 × 2 mm, four-layer 70 µm power PCB and an independently supported 160 × 120 × 1.6 mm, four-layer 35 µm control PCB. An isolated 40-way, 160 mm cable connects them. Heavy magnetics, aperture sensor, contactors, fuse holders and precharge resistor are chassis supported. Integrated and three-assembly alternatives are compared in `architecture/architecture_comparison.md`. Two independent native power floorplans were generated before routing. Candidate B accepts a slightly longer proposed commutation path than A in exchange for a common thermal contact plane and symmetric driver cells.

The design retains C4MS025120K and UCC21710-Q1 after comparing alternatives, with new gate/bias/feedback networks. The nominal gate bias is +17.167/−4.006 V; static positive tolerance is 16.800–17.535 V. Actual hot on-resistance at that drive voltage is not guaranteed by the 18 V datasheet test, so the loss calculation includes an explicit allowance. Separate UCC14141 supplies serve each gate cell and the three AMC1311B voltage channels. Their midpoint source/sink calculations include asymmetric current and effective MLCC capacitance assumptions.

The LEM HO 50-S-0100 removes the PCB current-sensor neck. OPA2320 buffers the actual sensor reference and implements `1.5 + 2 × (VOUT − VREF)`, nominally 32 mV/A with ±46.875 A ADC span. The hardware current window is ±38 A. A required sensor-end 4.7 kΩ OCD pull-up, board-side pull-down and reference plausibility channel address disconnected wiring; bidirectional sensing does not authorize regenerative power flow.

The chassis choke is four Magnetics 0058192A2 High Flux cores, 28 turns AWG10, about 432.8 µH at zero current and 391 µH at 25 A using manufacturer typical bias data. DC link/output banks are 4 × 15 µF/900 V and 2 × 100 µF/450 V film. Eight 0.47 µF/630 V ceramics provide the local HF bank, with effective capacitance at operating bias still a qualification item. Sources and exact part records are in `components/component_selection.md`, the circuit models and `requirements/source_manifest.json`.

Protection comprises KLKD020 input fuse, EV200 main/precharge contactors, HS100 2.2 kΩ precharge, contact feedback, passive bleeds, driver protection and a latched asynchronous PWM inhibit. Auxiliary coil/fan fusing uses KLKD008.T with a separate holder/cover. The controlled-source terminal transient limit ≤500 V is an operating restriction; no uncoordinated MOV is fitted. Overvoltage inhibition cannot clamp input surge energy or clear an output capacitor short. Source prospective fault energy, DC interruption and fuse coordination remain release blockers.

## Calculations and executed models

At 440 V/25 A with AL −8%, calculated ripple is 6.266 A peak-to-peak, peak current 28.133 A, and the capacitor/ESR output-ripple estimate is about 0.101 V. The updated total loss budget is 112.38 W, corresponding to **97.80% analytical efficiency**, including 8 W copper and 12 W auxiliary allowances. Estimated high-side junction temperature is approximately 103.45°C with the assumed 40°C ambient, 0.35 K/W sink and 0.5 K/W interface. These are conditional estimates; the copper budget, winding model, heatsink airflow and assembled interface are not measured.

The 200 ms digital soft start reaches approximately 200 V with 27.97 A peak in the event-aligned switched model. Load steps 12.5→25 A and back produce −13.99/+14.92 V deviation and 3.98/3.72 ms settling. The 360→440 V input step reaches about 201.82 V and 33.29 A. All 24 linear ZOH corners have poles inside the unit circle; minimum phase margin is about 67°. Independent native ngspice checks give 5.07/5.72/6.26 A ripple at 360/400/440 V. Their unsafe 2 ms open-loop ramp is retained as a counterexample, not the startup implementation.

Gate DESAT and Miller parameter sweeps are simplified sensitivity models. The fault model shows continuing diode/freewheel current after gate inhibition. No nonlinear vendor SiC model, extracted inductance, short-circuit withstand, measured EMI or hardware timing is claimed. The F28335 deliverable is an executed Python reference plus source-level implementation specification: 150 MHz, center-aligned 1500-count PWM, 45-count nominal dead time, synchronized ADC, one-cycle control delay and asynchronous TZ1/TZ2. No target compiler was installed and no target binary was built.

## Final CAD and engineering gates

| Gate | Evidence delivered | Disposition |
|---|---|---|
| A — electrical design | Models, sourced selections, corner calculations, sampled/switched/native simulations, protection review | Design addressed; semiconductor/protection qualification remains open |
| B — mechanical and safety | Explicit insulation basis, all-layer 8.027 mm copper projection, independent supports, thermal fixture and 30-volume assembly screen | Nominal geometry screened; material, ceramic, clamps, wire motion, fuse and enclosure qualifications block release |
| C — schematic | 9 power + 9 control + 5 system sheets; native ERC zero; editable hierarchical CAD and netlists | CAD VERIFIED against current inputs; every exported page visually inspected |
| D — PCB | 202 + 266 footprints, complete routing, native DRC zero, opens zero, parity zero on each board | CAD VERIFIED under recorded rules; no local electrical clearance waivers |
| E — system review | Closed-loop copper witnesses, current mesh, quiet-star topology, control returns, thermal/EMI review, all 18 E22 dispositions | Engineering review complete; physical qualification remains pending |

The actual local gate turn-on/turn-off copper lengths are 19.31/25.79 mm on each channel. Native-copper commutation witnesses are 70.01–99.13 mm externally, worse than the initial idealized B proposal. No improved nH or switching stress is inferred. Three feedback-star removal tests confirm that the load terminals remain connected without the small pin-36/tie branch. The 100°C copper mesh exposes the Q2 return as the most resistive tested path, approximately 3.024 mΩ; added parallel vias reduce its modeled single-branch concentration. See `pcb/routing_analysis/power_engineering_review.md` for assumptions and complete tables.

The control review includes actual plane holes, via-return distance, clock/PWM/fault/ADC paths and the coil-current partition. Projection gaps include ordinary signal-via antipads and are not automatic failures. Neither continuous DC ground nor a nearby bypass establishes high-frequency impedance. `control_engineering_review.md` identifies measurement needs and measured route metrics.

Native DRC retains five documented default ignored checks; their exact list is in each report. All-severity execution means all severities of **configured checks**, not every possible KiCad check enabled. No electrical-rule reduction was made to force a pass. The independent cross-layer barrier audit caught a condition that native same-layer clearance does not cover.

## Mechanical, manufacturing and qualification

The assembly reserve is 470 × 455 × 260 mm. The 30-envelope / 435-pair screen has zero unexplained intersections; two clamp/body envelope contacts are explicitly intentional, unqualified contacts. The model is not an exact vendor-solid fit check. Missing tab, fastener, ceramic edge, fuse-cover, winding and cable-motion details are listed in `mechanical/clearance_analysis.md`. UCC14141's 0.40 mm land width is an explicit variant from TI's 0.45 mm example and requires solder-joint/process qualification. Exact custom fixture fabrication and final supplier order configurations remain engineering release work.

Both boards have native Gerbers, drills, BOMs, placements, board/component STEP, front/back/isometric renders, PCB PDFs, and assembly drawings. STEP excludes copper to keep the mechanical exchange practical; Gerbers contain the copper. Power L2/L3/L4 have missing installed library models; the control PWP28 body and custom power bodies are explicitly approximate. Manufacturing files are marked engineering prototype review material and have not been sent to a fabricator.

The full regression run passed **373 tests, 2 skipped**; the native CAD and simulator evidence is separate from unit tests. The final verification manifest links the exact checks and hashes. See `remaining_issues.md` for the release hold register and `v22_vs_v3_comparison.md` for quantified benefits and regressions. Human engineering review must disposition those holds before any release decision. The GitHub PR is intentionally left unmerged.
