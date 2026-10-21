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
| primary-power | 0 findings (`20261021T071523Z-erc-e2894fc6`) | violations 57, unconnected 82, parity 0; unconnected_items (error) x82, clearance (error) x20, hole_clearance (error) x2, track_dangling (warning) x34, via_dangling (warning) x1 (`20261021T071523Z-drc-39f76185`) | missing_courtyard, track_not_centered_on_via, tuning_profile_track_geometries, footprint_filters_mismatch, footprint_type_mismatch | 2470 tracks, 411 vias, 23 zones, 79 unresolved connections, 1214.6 s |
| secondary-power | 0 findings (`20261021T071639Z-erc-a3528079`) | violations 37, unconnected 81, parity 0; unconnected_items (error) x81, hole_clearance (error) x2, track_dangling (warning) x33, via_dangling (warning) x2 (`20261021T071639Z-drc-ce8b8c2f`) | missing_courtyard, track_not_centered_on_via, tuning_profile_track_geometries, footprint_filters_mismatch, footprint_type_mismatch | 2703 tracks, 455 vias, 22 zones, 80 unresolved connections, 1325.7 s |
| control | 0 findings (`20261021T072243Z-erc-a7b01b14`) | violations 0, unconnected 499, parity 0; unconnected_items (error) x499 (`20261021T072243Z-drc-bff9bf17`) | missing_courtyard, track_not_centered_on_via, tuning_profile_track_geometries, footprint_filters_mismatch, footprint_type_mismatch | - |
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
- **primary-power**: 57 DRC violations remain (clearance x20, hole_clearance x2, track_dangling x34, via_dangling x1); 82 unconnected items remain in 42 nets (router: 79 open connections); unrouted or partly routed nets: BIAS_ENF (10), GND_CTRL (10), PG_BIAS_N (10), 3V3 (8), AC_B (6), GNDP_AH (6), GNDP_BH (6), GNDP_BL (6), GNDP_S (6), VEEA_AL (6), 12V_BIAS_AH (4), 12V_BIAS_AL (4), 12V_BIAS_BH (4), 12V_BIAS_BL (4), 12V_BIAS_S (4), BUS_P (4), FBVEE_AH (4), FBVEE_AL (4), GNDP_AL (4), PGND (4), VEEA_BL (4), VEE_AH (4), VEE_AL (4), DRV_RSTF (2), FBVEE_BH (2), FBVEE_BL (2), NTCR_AH (2), NTC_AH (2), NTC_AL (2), RLIM_AH (2), RLIM_AL (2), RLIM_BH (2), RLIM_BL (2), SDFM_D (2), S_FBVDD (2), S_FBVEE (2), S_RLIM (2), VDD_AH (2), VDD_AL (2), VEEA_AH (2), VEEA_BH (2), VSNS_P (2); model/schematic/board pad-net equality: exact (schematic mismatches 0, board mismatches 0); filled-copper islands per power net: {'12V_E': 1, '3V3': 5, 'AC_B': 4, 'BUS_P': 3, 'GND_CTRL': 6, 'PGND': 3, 'SW_A': 1, 'SW_B': 1, 'XF_B': 1} (split nets or not analysed); routing geometry: {'arcs': {'count': 0, 'radius_mm': None, 'joints': 0, 'discontinuous': 0, 'tangency_failures': []}}; layout-metric rows: 13 within, 6 exceeding, 101 measured only, 2 not measured (thresholds are the unverified design targets; geometry only).
- **secondary-power**: 37 DRC violations remain (hole_clearance x2, track_dangling x33, via_dangling x2); 81 unconnected items remain in 42 nets (router: 80 open connections); unrouted or partly routed nets: BIAS_ENF (10), GND_CTRL (10), PG_BIAS_N (10), 3V3 (6), AC_B (6), GNDP_AH (6), GNDP_BH (6), GNDP_BL (6), GNDP_S (6), VEEA_AL (6), VEEA_BH (6), 12V_BIAS_AH (4), 12V_BIAS_AL (4), 12V_BIAS_BH (4), 12V_BIAS_BL (4), 12V_BIAS_S (4), FBVEE_AH (4), FBVEE_AL (4), GNDP_AL (4), VEEA_BL (4), VEE_AH (4), VEE_AL (4), BUS_P (2), DRV_RSTF (2), FBVEE_BH (2), FBVEE_BL (2), NTCR_AH (2), NTCR_AL (2), NTC_AH (2), NTC_AL (2), PGND (2), RLIM_AH (2), RLIM_AL (2), RLIM_BH (2), RLIM_BL (2), S_5V (2), S_FBVDD (2), S_FBVEE (2), S_RLIM (2), VDD_AH (2), VDD_AL (2), VEEA_AH (2); model/schematic/board pad-net equality: exact (schematic mismatches 0, board mismatches 0); filled-copper islands per power net: {'12V_E': 1, '3V3': 4, 'AC_B': 4, 'BUS_P': 2, 'GND_CTRL': 6, 'PGND': 2, 'SW_A': 1, 'SW_B': 1} (split nets or not analysed); routing geometry: {'arcs': {'count': 0, 'radius_mm': None, 'joints': 0, 'discontinuous': 0, 'tangency_failures': []}}; layout-metric rows: 14 within, 5 exceeding, 99 measured only, 2 not measured (thresholds are the unverified design targets; geometry only).
- **control**: 499 unconnected items remain in 123 nets (router: n/a open connections); unrouted or partly routed nets: GND_CTRL (336), 3V3 (120), 5V0 (52), 12V_E (26), PWM_ENABLE (18), 12V_IN (12), E_RTN (10), ADC_5V (8), ADC_ITANK_P (8), ADC_ITANK_S (8), ADC_TEMP_P (8), ADC_TEMP_S (8), ADC_V12 (8), ADC_VBUS_P (8), ADC_VBUS_S (8), P_VBUS_RX (8), S_VBUS_RX (8), ALL_GOOD (6), CANH (6), CANL (6), FB5 (6), NRST (6), P_VA (6), P_VM (6), REF3 (6), S_VA (6), S_VM (6), V_OV_P (6), ARM (4), ARMED (4), AUX_FLT_N (4), BIAS_EN (4), BIAS_EN_MCU (4), CAN_MID (4), DRV_RST (4), DRV_RST_MCU (4), EN5 (4), EPWM1A (4), EPWM1B (4), EPWM2A (4), EPWM2B (4), EPWM3A (4), EPWM3B (4), EPWM4A (4), EPWM4B (4), E_IMON (4), E_OV (4), E_UV (4), MON3V3 (4), P_ISNS_BUF (4), P_PG_BIAS_N (4), P_RDY_AH (4), P_RDY_AL (4), P_RDY_BH (4), P_RDY_BL (4), RS485_A (4), RS485_B (4), RS485_DE (4), RUN_EN (4), SW5 (4) ...; model/schematic/board pad-net equality: exact (schematic mismatches 0, board mismatches 0); filled-copper islands per power net: {'12V_E': 14, '3V3': 61, '5V0': 27, 'GND_CTRL': 169} (split nets or not analysed); layout-metric rows: 0 within, 0 exceeding, 1 measured only, 13 not measured (thresholds are the unverified design targets; geometry only).
- The router report is a geometric proposal; every remaining DRC item above is a real finding of the generated copper and must be resolved or dispositioned by a human before any fabrication decision. Routing quality metrics are geometry, not inductance or EMI.
<!-- /RESULTS-REMAINING -->

## 8. Evidence index

<!-- RESULTS-EVIDENCE -->
| Board | Evidence file | SHA-256 |
|---|---|---|
| primary-power | `examples/dab-10kw/verification/summary_primary-power.json` | `2767aef7e1a13135...` |
| primary-power | `examples/dab-10kw/verification/erc/20261021T071523Z-erc-e2894fc6/run.json` | `2061a30b9d4d1609...` |
| primary-power | `examples/dab-10kw/verification/drc/20261021T071523Z-drc-39f76185/run.json` | `ba1fdec5f6496940...` |
| primary-power | `examples/dab-10kw/manufacturing/primary-power/export-manifest.json` | `2a0b9eddc45449d6...` |
| primary-power | `examples/dab-10kw/verification/circuit_checks/netlist_equality_primary-power.json` | `0772c34054abddf5...` |
| primary-power | `examples/dab-10kw/verification/engineering_checks/routing_quality_primary-power.json` | `0865c7b49863c3e1...` |
| primary-power | `examples/dab-10kw/verification/engineering_checks/layout_metrics_primary-power.json` | `45344243037981f1...` |
| primary-power | `examples/dab-10kw/verification/engineering_checks/copper_islands_primary-power.json` | `14eb2f5b26358eca...` |
| primary-power | `examples/dab-10kw/pcb/routing_report_primary-power.json` | `be25a47269282ef6...` |
| secondary-power | `examples/dab-10kw/verification/summary_secondary-power.json` | `a9dbf1e07b85f244...` |
| secondary-power | `examples/dab-10kw/verification/erc/20261021T071639Z-erc-a3528079/run.json` | `8ce923ac0fc97574...` |
| secondary-power | `examples/dab-10kw/verification/drc/20261021T071639Z-drc-ce8b8c2f/run.json` | `991ab2fe3f370e67...` |
| secondary-power | `examples/dab-10kw/manufacturing/secondary-power/export-manifest.json` | `2a9655da76f7b71d...` |
| secondary-power | `examples/dab-10kw/verification/circuit_checks/netlist_equality_secondary-power.json` | `181efe851b8b90ca...` |
| secondary-power | `examples/dab-10kw/verification/engineering_checks/routing_quality_secondary-power.json` | `e331e7eaaf5ce8f5...` |
| secondary-power | `examples/dab-10kw/verification/engineering_checks/layout_metrics_secondary-power.json` | `b45c7460186a271f...` |
| secondary-power | `examples/dab-10kw/verification/engineering_checks/copper_islands_secondary-power.json` | `e6577817874b1e8e...` |
| secondary-power | `examples/dab-10kw/pcb/routing_report_secondary-power.json` | `e905aae23e8a8ea9...` |
| control | `examples/dab-10kw/verification/summary_control.json` | `0d98a0dd3c2ea712...` |
| control | `examples/dab-10kw/verification/erc/20261021T072243Z-erc-a7b01b14/run.json` | `856e581649b74e7c...` |
| control | `examples/dab-10kw/verification/drc/20261021T072243Z-drc-bff9bf17/run.json` | `514decb574a3c3e6...` |
| control | `examples/dab-10kw/manufacturing/control/export-manifest.json` | `1d12aa77d98f6150...` |
| control | `examples/dab-10kw/verification/circuit_checks/netlist_equality_control.json` | `dce45fe1071e4194...` |
| control | `examples/dab-10kw/verification/engineering_checks/layout_metrics_control.json` | `cdf0cd0b654c8493...` |
| control | `examples/dab-10kw/verification/engineering_checks/copper_islands_control.json` | `30ffb745b9d517c6...` |
| all | `examples/dab-10kw/requirements/source_manifest.json` | `5a92700f390f9c42...` |
<!-- /RESULTS-EVIDENCE -->
