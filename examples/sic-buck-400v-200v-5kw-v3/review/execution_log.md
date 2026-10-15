# V3 execution record

## 2026-10-15 — requirements and architecture

- Read the complete V3 task and the V2.2 E22-01…18 review, remaining ECOs and reference-design analyses.
- Confirmed PR #5 merged; fetched upstream main and created `feat/sic-buck-v3-clean-sheet` at `20e96fdfa5ea76649daa416ee70b7ea7798a319d`.
- Verified existing KiCad 10.0.7, pcbnew, Python, ngspice and GitHub access. No software installed.
- Retrieved primary datasheets and recorded SHA-256 provenance. Found the TI HV driver land-pattern option and the current LEM full datasheet URL; these correct limitations of preliminary footprint and sensor information.
- Selected separate supported power/control PCBs, with chassis-mounted heavy parts, before placement. Set the environmental and insulation assumptions before routing.
- Status: requirements/architecture milestone in progress; electrical detail, calculations, simulation, editable CAD, A/B floorplans, routing, native verification, manufacturing review package and PR remain to be executed. **No completion or release claim.**

## 2026-10-15 — electrical design and behavioural verification

- Built independent V3 circuit models and manufacturer-dimensioned barrier/power footprints. Off-board choke remains an actual schematic component excluded from the PCB.
- Calculated biased inductance, component stresses, gate/midrail load balance, precharge/discharge and loss/temperature envelopes. Revised positive gate bias to preserve tolerance margin below 18 V and corrected the input bleed chain to 364 kΩ.
- Replaced the current reference with a buffered LEM reference, added an explicit cable-disconnect inhibit and ADC reference plausibility channel, and verified the coil diode as SSC54 in SMC.
- Generated two native nine-page schematics. Added a reusable wired vertical buck template and genuine amplifier/comparator glyphs. Native ERC reached zero violations on both boards; final exports will be repeated after layout-related circuit changes.
- Ran the averaged and event-aligned sampled control models, 24 stability corners, native ngspice switching/DESAT/Miller networks and a conditional system-fault envelope. Preserved the unsafe open-loop startup counterexample. No semiconductor survival or hardware timing claim.
- Ran 61 relevant regression tests successfully. No new software was installed. PCB placement/routing and final engineering gates are still outstanding.

## 2026-10-15 — thermal fixture and native floorplans

- Defined a common PE sink, separate copper contact blocks and an unpunctured AlN plate before final routing. Recorded exact missing contact/clamp/insulation qualifications. Both boards have four independent supports; heavy parts remain chassis mounted.
- Built two independent 202-part power-board floorplans and a 266-part control-board floorplan from the V3 netlists. DSP per-pin bypasses are positioned on the back against actual rotated supply pads.
- Native pre-routing DRC reached zero geometry violations on A, B and control; B/control also have zero schematic-parity findings. Unconnected items remain expected at this stage. These are **not** completed routed boards.
- Selected B after comparing complete proposed multilayer current paths. A saves about 1.65 mm of the external commutation proxy; B has shorter symmetric gate paths and one common thermal contact plane. No extracted inductance is claimed. Final routed geometry must replace these preliminary values.
- Kept the prescribed clearance rules. Replaced generic control VSSOP lands with TI DGK0008A recommended dimensions. The UCC14141 narrow-land variant and its assembly-qualification risk are explicitly recorded; its body envelope now uses the correct 3.55 mm maximum height.
- Added generic native board construction, pair-aware placement and closed-loop geometry analysis; ten V3 tests pass, including rejection of incomplete current loops. Routing, final mechanical model, engineering review matrix, manufacturing package and PR remain outstanding.
