# Final power copper and current-path review

The native source is `kicad/power_board/sic-v3-power.kicad_pcb`. All numerical checks below bind to its SHA-256 in `verification/engineering_checks/`. Native KiCad 10.0.7 reports zero violations, zero unintended opens and zero schematic-parity differences. This establishes configured CAD-rule compliance, not ampacity, insulation certification or semiconductor qualification.

## Closed gate energy paths

`power_closed_loops.json` contains ordered XYZ sections, including local C21/C22 and C33/C34 reservoirs, driver terminals, split gate resistors, gate and Kelvin-source leads. Each external section is checked against the actual filled copper on its layer; vertical transitions must coincide with a real plated connection. Internal driver, MOSFET and capacitor paths are straight terminal bridges. They are not die/bond-wire models.

| Path, either H or L | External copper | Closed terminal-bridge proxy | XY vector-area projection | Physical F/B transitions |
|---|---:|---:|---:|---:|
| Turn-on, local positive reservoir | 19.306 mm | 27.591 mm | 16.476 mm² | 2 |
| Turn-off, local negative reservoir | 25.791 mm | 35.346 mm | 20.055 mm² | 2 |
| Active clamp, local negative reservoir | 30.233 mm | 35.593 mm | 12.502 mm² | 2 |

The gate conductor itself stays on F.Cu. The local reservoirs and Kelvin return use B.Cu, with one supply via and the Kelvin PTH transition. The 2 mm board thickness creates a real vertical loop component; projected XY area alone understates it. The 3D vector-area magnitudes are 23.253 / 27.027 / 22.013 mm². Signed-area cancellation and internal paths limit these metrics. No nH values are extracted.

The entire G_H/G_L networks are 44.384/67.078 mm, and KS_H/KS_L are 243.727/166.726 mm with 13 vias each. These totals include bias, sensing, bleed and other branches. They are much larger than the local switching-energy loops. Those branches remain potential noise coupling paths and require gate-bias/regulation testing; a short local path does not validate every connected branch.

## Actual commutation copper

The reusable raster path tool follows native filled polygons and holes, uses only physical PTH/via transitions, then verifies every output segment remains in copper. The grid is 0.25 mm. These paths are geometric witnesses; shortest length is not minimum inductance and does not predict which capacitors carry the HF current.

| HF capacitor | External copper witness | Complete closed proxy | XY projected vector area |
|---|---:|---:|---:|
| C5 | 99.127 mm | 114.387 mm | 457.438 mm² |
| C6 | 86.420 mm | 101.680 mm | 383.938 mm² |
| C7 | 75.763 mm | 91.023 mm | 340.688 mm² |
| C8 | 70.299 mm | 85.559 mm | 285.250 mm² |
| C9 | 70.006 mm | 85.266 mm | 247.813 mm² |
| C10 | 70.006 mm | 85.266 mm | 208.500 mm² |
| C11 | 71.367 mm | 86.627 mm | 169.281 mm² |
| C12 | 80.902 mm | 96.162 mm | 130.906 mm² |

These are longer than the initial B floorplan's 58.34 mm external proposal. Routing obstacles, actual returns and layer changes consume the idealized margin. The final topology remains a candidate for double-pulse testing, not a demonstrated commutation improvement over V2.2. The stored `copper_z_transitions` counts adjacent modeled layer intervals; several intervals can occur in the same physical plated hole. The eight capacitors do not constitute eight independent identical current loops in operation. Effective ceramic capacitance at 440 V, connection impedance and current sharing remain open.

## Quiet feedback star

U3/U4/U8 pin 35 and divider returns occupy distinct H/L/S_VEEA nets, with only one intentional net-tie junction each. The final graph records every quiet-net pad. To test the load-return assertion, the review removes a 0.85 mm radius corridor around the pin-36-to-net-tie branch **from a copy of all copper layers**, then recomputes connected components. All remaining load terminals stay in a single connected copper component for H, L and S. Thus the load network does not require that quiet branch for continuity. Pin 36 and the tie return also connect to the wider VEE network; this is not an isolated power terminal.

`quiet_star_topology.json` records the exact coordinates, remaining pad groups and board hash. This supports the physical branch design beyond net naming. It cannot prove actual high-frequency current density, substrate coupling or regulation noise. Load-step and switching-noise measurements remain mandatory.

## Continuous-current copper screen

The finite-square DC resistor mesh uses the native four-layer copper at 100°C, 70 µm per layer, 25 µm assumed plating and the actual 2 mm stack. Coarse/fine grid comparison changes the six endpoint resistance estimates by approximately 0.6–4.8%.

| Separate endpoint stress | Fine grid | Estimated resistance | Loss if 25 A DC through that endpoint pair |
|---|---:|---:|---:|
| J1 → Q1 drain, BUS | 0.25 mm | 1.119 mΩ | 0.699 W |
| Q1 power source → J3, SW | 0.125 mm | 1.672 mΩ | 1.045 W |
| Q2 drain → J3, SW | 0.125 mm | 1.159 mΩ | 0.724 W |
| J5 → J2, PGND | 0.25 mm | 1.352 mΩ | 0.845 W |
| Q2 power source → J2, PGND | 0.25 mm | 3.024 mΩ | 1.890 W |
| J4 → C14 positive, VOUT | 0.25 mm | 0.075 mΩ | 0.047 W |

The Q2 return initially concentrated through one F-to-inner via. Three parallel PGND vias were added; the largest modeled branch fraction fell from 1.0 to about 0.355. Actual sharing depends on plating, pad current crowding and AC effects. The model treats pads as solid lands without drill voids, idealizes endpoint contacts, and omits solder/lead/contact losses, skin/proximity effects and thermal feedback. Therefore neither the 3.024 mΩ estimate nor grid convergence establishes the 20 K temperature-rise target. Use a board-specific electrothermal model and thermography at 25 A and the proposed 30 A/1 s overload before release. The system budget uses 8 W PCB copper at 25 A; it is not a guaranteed bound. Do not sum all endpoint stresses as simultaneous converter losses.

## Insulation, return and EMI

Every actual copper net has one connected component in the geometric island audit. The independent hazardous/control projection check includes zones, pads and tracks on all four layers. Its minimum is **8.026933 mm**, against the predeclared 8 mm target; nearest points are recorded. Early pad/track-only masking allowed HV copper below otherwise empty control ground-plane area. The corrected zone tool reserves complete control planes too. Native same-layer DRC alone did not expose that projection problem.

SW copper areas are F 211.839, In1 627.771, In2 611.941 and B 211.839 mm². Inner overlap, the approximately 148 mm SW-terminal-to-choke-centre separation before wire bends, and the 160 mm control cable require common-mode/near-field testing. No enclosure capacitance or EMC limit is calculated from these areas. Functional pair-dependent spacing, reinforced projected separation and actual assembled creepage remain distinct requirements. No per-item electrical clearance waivers were added.

## Tool and CAD limits

Track repair retains protected gate/star geometry, normalizes real middle-of-track junctions before pruning native dangling tails, and tests exact segment clearance rather than rejecting every bounding-box overlap. Final routing retains some irregular branches and crowded fine-pitch escapes. Four layers were sufficient for connectivity; six layers were not added solely for appearance. Power-copper necks, branch return impedance and assembly limits remain visible in the release register.

Five native DRC checks retain KiCad's project defaults of ignore: missing courtyard, track endpoint centered on via, tuning-profile geometry, footprint-filter match and footprint-type match. Their exact keys are retained in the native report and completion manifest. Copper clearance, hole clearance, edge clearance, track width, shorts, opens, and schematic parity are checked. An ignored informational/default check is not an electrical-rule exemption or proof that all possible KiCad checks were enabled.
