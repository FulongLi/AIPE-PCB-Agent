# Lessons from the V2.2 independent review

These additions extend the reference-design knowledge with findings from actual AIPE CAD and primary component datasheets. They are engineering review evidence, not hardware validation. The complete issue register is in `examples/sic-buck-400v-200v-5kw/review/v22/stage_a_independent_review.md`.

1. **Identify a sensor's reference law before designing offset compensation.** A zero output near 10% of a nominal supply does not establish ratiometry. TMCS1133 Cxx uses a fixed 0.33 V internal zero reference: [TI SBOSAG0E §8.3.5](https://www.ti.com/lit/ds/symlink/tmcs1133.pdf). AIPE V2.1's 3V3 divider and firmware supply-ratio formula were therefore incorrect. Trace the generated netlist and firmware equations together. An independent divider still requires zero-current and gain calibration.

2. **Select the correct isolated midpoint-regulator operating configuration.** Dual-positive loads and a positive/negative gate supply have different RLIM equations. For UCC14141 dual-positive operation use VOUT2 / maximum load current minus internal switch resistance ([TI SLUSF10B Eq. 9](https://www.ti.com/lit/ds/symlink/ucc14141-q1.pdf)); do not substitute the voltage dropped from the upper rail. Add both isolators' maximum current, feedback current, resistor tolerance and hot derating. Typical internal resistance is not a guaranteed limit. Preserve explicit startup/continuous-load validation requirements.

3. **A quiet analogue return is a copper-topology requirement.** VEEA and VEE may ultimately be connected but a shared plane does not implement the quiet feedback star specified in SLUSF10B §9.5. Verify current paths and keepout topology on every layer. A descriptive part note cannot establish compliance.

4. **Treat native DRC and physical suitability as separate gates.** A pin-field rule exception only changes the CAD check. Slots do not increase air clearance; package insulation certification does not certify the complete assembly. Keep unresolved insulation and mechanical items as release blockers even when DRC has zero findings.

5. **Report geometry at its actual evidential strength.** Summed gate-net copper length is not closed-loop inductance. Filled-copper erosion is a neck screening proxy, not an electrothermal current rating. Compare pad distance, actual routed path, vias, return copper and changed layer transitions together. V2.2 rejected a shorter clamp candidate because Kelvin-pour projection worsened; passing DRC and reducing length were insufficient to accept it.

6. **Local ECO automation must account for manufacturing details.** Search against existing pads/tracks/vias, keep ground returns short, avoid unqualified via-in-pad construction, and run native DRC and model/schematic/PCB equality after replay. Hash-check immutable input boards, allow only explicitly reviewed connectivity deltas, and reject a candidate that fails the stated metric.

Reusable implementations: `automation/kicad_tools/refine_sic_v22.py`, `generate_sic_schematics.approved_release_map`, and `tests/test_sic_v22_engineering.py`. Frozen V2/V2.1 artefacts retain their original assumptions for traceability; this document and the V2.2 report supersede the identified incorrect claims in the active design.
