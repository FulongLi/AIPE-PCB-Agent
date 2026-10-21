# AIPE 10 kW DAB (DAB-V1) - review report

**AI-generated engineering prototype. Human review required. Clean ERC/DRC does not establish electrical safety,
standards compliance, EMC, thermal adequacy or manufacturability.** This report states what was generated, which native
checks were run with which settings and results, which checks KiCad ignored, what the export bundles contain, and what a
human reviewer must verify before any board is ordered, built or energised.

## 1. What a clean native result means here

- `kicad-cli sch erc --severity-all --exit-code-violations` on each root schematic: zero findings means the generated
  symbols, pin types, labels, PWR_FLAGs and footprint links are consistent under KiCad's default ERC matrix. It does not
  check that a connection is electrically right; the model (`design/circuit_<board>.json`) is the engineering statement
  and it is unverified by hardware.
- `kicad-cli pcb drc --schematic-parity --severity-all --refill-zones` on each board: zero violations means the copper
  respects the recorded rule set (`<board>.kicad_pro` net classes, `<board>.kicad_dru`), every pad of every net is
  connected, and the board matches the schematic. The rule set encodes IEC 60664-1 *reference* values and documented
  package relaxations; the values themselves are review inputs (section 5).
- KiCad ignores five checks by default on these projects (listed per board below); they were not disabled by this
  generation and are reported, not waived.
- Export manifests record the exact kicad-cli commands, exit codes, input hashes and artifact hashes. They prove the
  files were produced from the hashed sources, nothing about their fitness for fabrication.

## 2. Generated content

<!-- RESULTS-TABLE-GENERATED -->
| Board | Project | Size / stack | Parts (model) | Sheets | Nets | Net classes | DRU rules | Package relaxations |
|---|---|---|---|---|---|---|---|---|
| primary-power | `dab-primary` | 300 x 150 mm, 4 layers, 70 um, 2.0 mm | 309 | 7 | 132 | 23 | 223 | 22 |
| secondary-power | `dab-secondary` | 300 x 150 mm, 4 layers, 70 um, 2.0 mm | 312 | 7 | 131 | 15 | 73 | 0 |
| control | `dab-control` | 160 x 120 mm, 4 layers, 35 um, 1.6 mm | 224 | 7 | 165 | 3 | 1 | 0 |
<!-- /RESULTS-TABLE-GENERATED -->

## 3. Native ERC / DRC results

<!-- RESULTS-ERC-DRC -->
| Board | ERC (`sch erc --severity-all`) | DRC (`pcb drc --schematic-parity --severity-all --refill-zones`) | Checks ignored by KiCad (default, not disabled here) | Router result |
|---|---|---|---|---|
| primary-power | 0 findings (`20261021T114704Z-erc-82fe6ef8`) | violations 18, unconnected 26, parity 0; unconnected_items (error) x26, track_dangling (warning) x18 (`20261021T114704Z-drc-8c4572df`) | missing_courtyard, track_not_centered_on_via, tuning_profile_track_geometries, footprint_filters_mismatch, footprint_type_mismatch | 2501 tracks, 436 vias, 22 zones, 26 unresolved connections, 1160.5 s |
| secondary-power | 0 findings (`20261021T114746Z-erc-c5f3b0ce`) | violations 18, unconnected 23, parity 0; unconnected_items (error) x23, track_dangling (warning) x18 (`20261021T114746Z-drc-9d8d1f3f`) | missing_courtyard, track_not_centered_on_via, tuning_profile_track_geometries, footprint_filters_mismatch, footprint_type_mismatch | 2598 tracks, 449 vias, 21 zones, 23 unresolved connections, 1189.0 s |
| control | 0 findings (`20261021T121733Z-erc-61086698`) | violations 28, unconnected 24, parity 0; unconnected_items (error) x24, track_dangling (warning) x28 (`20261021T121733Z-drc-64a4df3c`) | missing_courtyard, track_not_centered_on_via, tuning_profile_track_geometries, footprint_filters_mismatch, footprint_type_mismatch | 3090 tracks, 622 vias, 1 zones, 24 unresolved connections, 2713.5 s |
<!-- /RESULTS-ERC-DRC -->

## 4. Export bundles

<!-- RESULTS-EXPORTS -->
| Board | Status | Commands (exit codes) | Artifacts | Manifest |
|---|---|---|---|---|
| primary-power | passed | schematic_pdf=0, pcb_pdf=0, gerber=0, drill=0, bom=0, placement=0, step=0, front=0, back=0, isometric=0, netlist=0 | 36 | `examples\dab-10kw\manufacturing\primary-power\export-manifest.json` |
| secondary-power | passed | schematic_pdf=0, pcb_pdf=0, gerber=0, drill=0, bom=0, placement=0, step=0, front=0, back=0, isometric=0, netlist=0 | 36 | `examples\dab-10kw\manufacturing\secondary-power\export-manifest.json` |
| control | passed | schematic_pdf=0, pcb_pdf=0, gerber=0, drill=0, bom=0, placement=0, step=0, front=0, back=0, isometric=0, netlist=0 | 36 | `examples\dab-10kw\manufacturing\control\export-manifest.json` |
<!-- /RESULTS-EXPORTS -->

## 5. Insulation-coordination inputs (to be reviewed)

The net classes and `.kicad_dru` of the power boards are derived from `requirements/design_constraints.yaml`:

- IEC 60664-1 clearance by rated impulse (2.5 kV 1.5 mm, 4 kV 3.0 mm, 6 kV 5.5 mm, 8 kV 8.0 mm) and creepage at
  pollution degree 2 / material group I (400 V 2.0 mm, 500 V 2.5 mm, 630 V 3.2 mm, 800 V 4.0 mm, 1000 V 5.0 mm),
  used as **reference inputs**; functional spacing between hazardous domains is interpolated from the working-voltage
  difference of an explicit potential model (`design/spacing_<board>.json` lists every class pair, voltage and value).
- Reinforced HV-to-SELV separation 8.0 mm on every copper layer (2 x creepage at 800 V; clearance at 6 kV would be
  5.5 mm), also applied to the 400 V secondary as margin.
- Package-limited relaxations on the primary board only: the TO-247-4 drain/source lead field (3.175 mm pad gap for a
  table value of 4.0 mm) and the 2220 DC-link capacitors (3.3 mm pad gap for 4.0 mm), each as a pair-specific rule on
  the component's own pads, justified by the component's own voltage rating. None on the secondary board.
- Inner layers use the outer-layer values; no solid-insulation evaluation was made. The applicable standard, pollution
  degree, laminate CTI certificate, impulse category, and the heat-sink insulation system are open (R-01, R-03, R-11).

## 6. What a human reviewer must check (minimum)

1. **controlCARD contact map (R-01)** - `interfaces.yaml -> controlcard.signals` is an ASSUMED assignment modelled on the
   180-contact C2000 controlCARD layout; verify every contact (PWM, ADC, SDFM, TZ, GPIO, 5 V, GND, JTAG) against the
   TMDSCNCD280039C pin-out, and the Samtec socket orderable/polarisation (the task says "HSEC8-160"; the card has 180
   contacts, Samtec's HSEC8-190 size).
2. **Pin tables marked `transcribed` in `automation/dab_v1/parts.py::PINOUT_SOURCES`** (AMC1336, TPS7A2033, TCAN1042,
   THVD1450, TLV76050, PESD1CAN) and the TO-247-4 lead order of the C3M devices (R-02).
3. **Insulation (R-03)** - section 5; package creepage of the DW / DWN / DWV / DVG packages versus the 8.0-9.1 mm AIPE
   land gaps; the barrier band is copper-free by rule, inspect the Gerbers.
4. **Gate loop and DESAT (R-04, R-07)** - double-pulse tests for 2 ohm / 2 ohm, dv/dt and overshoot; recompute the
   DESAT blanking and verify short-circuit withstand of the devices against detection + soft turn-off time.
5. **Dead time and trip zone (R-05)** - controller functions; the hardware interlock only blocks identical commands.
6. **Capacitors (R-06)** - film dimensions are reserved envelopes (datasheets not located); ripple-current ratings of the
   DC-link and DC-blocking capacitors at 100 kHz; effective capacitance of the 1 kV / 630 V ceramics under bias.
7. **Hall over-current threshold (R-08)** - the VOC divider is a placeholder; apply the SBOSAG0E equation for 45 A / 70 A;
   confirm the TMCS1133B1 orderable.
8. **Analogue trip chain (R-09)** - tolerance budget of ladder, AMC1311, receiver and comparator; decide on a hardware
   HV under-voltage trip.
9. **External magnetics and harnesses (R-10)** - transformer and 35 uH inductor terminations, external switch-node
   conductors, 160 mm SELV harness (SDFM clock integrity, 12V_E contact current).
10. **Thermal (R-11)** - two devices per 0.5 K/W sink with insulating pads; the sink is PE-bonded; junction-temperature
    budget was not computed by this package.
11. **Common-mode and EMI (R-12, R-13)** - no plane under the islands or switch nodes by design; loop geometry is
    measured by `check_sic_layout` as geometry only; no inductance, EMI or current-capacity evidence exists.
12. **Discharge, fault-path delays, eFuse polarity, auxiliary budget (R-14 to R-17)** as listed in the architecture
    review.
13. **Manufacturability** - the UCC14141 footprint uses 0.40 mm lands at 0.65 mm pitch (narrower than TI's 0.45 mm) to
    keep the 0.25 mm board clearance: assembler qualification is required; via-in-pad is not used; copper/plating
    tolerances, mask/paste apertures and the press-in terminals need fabricator agreement.

## 7. Remaining findings and honest limits

<!-- RESULTS-REMAINING -->
- **primary-power**: 18 DRC violations remain (track_dangling x18); 26 unconnected items remain in 18 nets (router: 26 open connections); unrouted or partly routed nets: BIAS_ENF (10), VEEA_BL (6), FBVEE_AL (4), PG_BIAS_N (4), FBVDD_AL (2), FBVDD_BL (2), FBVEE_AH (2), FBVEE_BH (2), FBVEE_BL (2), KS_BL (2), RLIM_BL (2), S_16V (2), S_RLIM (2), VEEA_AH (2), VEEA_AL (2), VEEA_BH (2), VEE_AH (2), VEE_BL (2); model/schematic/board pad-net equality: exact (schematic mismatches 0, board mismatches 0); filled-copper islands per power net: {'12V_E': 1, '3V3': 1, 'AC_B': 1, 'BUS_P': 1, 'GND_CTRL': 1, 'PGND': 1, 'SW_A': 1, 'SW_B': 1, 'XF_B': 1} (all single); routing geometry: {'arcs': {'count': 0, 'radius_mm': None, 'joints': 0, 'discontinuous': 0, 'tangency_failures': []}}; layout-metric rows: 14 within, 5 exceeding, 101 measured only, 2 not measured (thresholds are the unverified design targets; geometry only).
- **secondary-power**: 18 DRC violations remain (track_dangling x18); 23 unconnected items remain in 16 nets (router: 23 open connections); unrouted or partly routed nets: BIAS_ENF (10), VEEA_BL (6), FBVEE_AL (4), FBVDD_AL (2), FBVDD_BL (2), FBVEE_AH (2), FBVEE_BH (2), FBVEE_BL (2), PG_BIAS_N (2), RLIM_BL (2), S_RLIM (2), VEEA_AH (2), VEEA_AL (2), VEEA_BH (2), VEE_AH (2), VEE_BL (2); model/schematic/board pad-net equality: exact (schematic mismatches 0, board mismatches 0); filled-copper islands per power net: {'12V_E': 1, '3V3': 1, 'AC_B': 1, 'BUS_P': 1, 'GND_CTRL': 1, 'PGND': 1, 'SW_A': 1, 'SW_B': 1} (all single); routing geometry: {'arcs': {'count': 0, 'radius_mm': None, 'joints': 0, 'discontinuous': 0, 'tangency_failures': []}}; layout-metric rows: 14 within, 5 exceeding, 99 measured only, 2 not measured (thresholds are the unverified design targets; geometry only).
- **control**: 28 DRC violations remain (track_dangling x28); 24 unconnected items remain in 23 nets (router: 24 open connections); unrouted or partly routed nets: GND_CTRL (4), 3V3 (2), ARM (2), DRV_RST_MCU (2), EPWM3A (2), E_IMON (2), NRST (2), PG_S_OK (2), PROT_OK (2), P_FLT_BH_N (2), P_FLT_BL_N (2), P_RDY_BL (2), P_VBUS_RX (2), RS485_DE (2), RS485_TX (2), RUN_EN (2), SUPPLY_OK (2), S_FLT_BL_N (2), S_PG_BIAS_N (2), S_PWM_AL_SRC (2), TEMP_PWM_P_BH (2), TEMP_PWM_S_AL (2), V_OV_S (2); model/schematic/board pad-net equality: exact (schematic mismatches 0, board mismatches 0); filled-copper islands per power net: {'12V_E': 1, '3V3': 2, '5V0': 1, 'GND_CTRL': 3} (split nets or not analysed); routing geometry: {'arcs': {'count': 222, 'radius_mm': {'min': 0.1962, 'median': 0.3968, 'max': 1.0008}, 'joints': 437, 'discontinuous': 1, 'tangency_failures': [{'net': 'RS485_RX', 'layer': 'F.Cu', 'xy_mm': [21.625, 87.125], 'error_deg': 129.603}]}}; layout-metric rows: 0 within, 0 exceeding, 1 measured only, 13 not measured (thresholds are the unverified design targets; geometry only).
- The router report is a geometric proposal; every remaining DRC item above is a real finding of the generated copper and must be resolved or dispositioned by a human before any fabrication decision. Routing quality metrics are geometry, not inductance or EMI.
<!-- /RESULTS-REMAINING -->

## 8. Evidence index

<!-- RESULTS-EVIDENCE -->
| Board | Evidence file | SHA-256 |
|---|---|---|
| primary-power | `examples/dab-10kw/verification/summary_primary-power.json` | `91c60d1c30a57267...` |
| primary-power | `examples/dab-10kw/verification/erc/20261021T114704Z-erc-82fe6ef8/run.json` | `41e80f378fa448ca...` |
| primary-power | `examples/dab-10kw/verification/drc/20261021T114704Z-drc-8c4572df/run.json` | `4647bcb7a44413fa...` |
| primary-power | `examples/dab-10kw/manufacturing/primary-power/export-manifest.json` | `910a2f80505f6211...` |
| primary-power | `examples/dab-10kw/verification/circuit_checks/netlist_equality_primary-power.json` | `0772c34054abddf5...` |
| primary-power | `examples/dab-10kw/verification/engineering_checks/routing_quality_primary-power.json` | `55dc35c1ec3116fc...` |
| primary-power | `examples/dab-10kw/verification/engineering_checks/layout_metrics_primary-power.json` | `cf9e71ef25563c9f...` |
| primary-power | `examples/dab-10kw/verification/engineering_checks/copper_islands_primary-power.json` | `77766bdf7cb15326...` |
| primary-power | `examples/dab-10kw/pcb/routing_report_primary-power.json` | `2fe9b72df72bd7bf...` |
| secondary-power | `examples/dab-10kw/verification/summary_secondary-power.json` | `a31fea1173f931ca...` |
| secondary-power | `examples/dab-10kw/verification/erc/20261021T114746Z-erc-c5f3b0ce/run.json` | `947b6d1886d11737...` |
| secondary-power | `examples/dab-10kw/verification/drc/20261021T114746Z-drc-9d8d1f3f/run.json` | `0d06707594cf959e...` |
| secondary-power | `examples/dab-10kw/manufacturing/secondary-power/export-manifest.json` | `304ae04568cc3fb3...` |
| secondary-power | `examples/dab-10kw/verification/circuit_checks/netlist_equality_secondary-power.json` | `181efe851b8b90ca...` |
| secondary-power | `examples/dab-10kw/verification/engineering_checks/routing_quality_secondary-power.json` | `e48d66cb0ff2d611...` |
| secondary-power | `examples/dab-10kw/verification/engineering_checks/layout_metrics_secondary-power.json` | `4ccfd149e2e200d6...` |
| secondary-power | `examples/dab-10kw/verification/engineering_checks/copper_islands_secondary-power.json` | `62bc1d6dd6914d72...` |
| secondary-power | `examples/dab-10kw/pcb/routing_report_secondary-power.json` | `936ff14ed1921c99...` |
| control | `examples/dab-10kw/verification/summary_control.json` | `208bc689f9c5d0b4...` |
| control | `examples/dab-10kw/verification/erc/20261021T121733Z-erc-61086698/run.json` | `5229e7e4e66e829b...` |
| control | `examples/dab-10kw/verification/drc/20261021T121733Z-drc-64a4df3c/run.json` | `8bfbbf883c408713...` |
| control | `examples/dab-10kw/manufacturing/control/export-manifest.json` | `d47455f653f0167a...` |
| control | `examples/dab-10kw/verification/circuit_checks/netlist_equality_control.json` | `dce45fe1071e4194...` |
| control | `examples/dab-10kw/verification/engineering_checks/routing_quality_control.json` | `0b879d6f36f1ccb8...` |
| control | `examples/dab-10kw/verification/engineering_checks/layout_metrics_control.json` | `2238691442916033...` |
| control | `examples/dab-10kw/verification/engineering_checks/copper_islands_control.json` | `0b6585485e800411...` |
| control | `examples/dab-10kw/pcb/routing_report_control.json` | `bd70ce40b3176216...` |
| all | `examples/dab-10kw/requirements/source_manifest.json` | `ac0fab19fb26d91c...` |
<!-- /RESULTS-EVIDENCE -->
