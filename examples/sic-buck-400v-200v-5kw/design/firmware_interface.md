**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# Firmware interface contract - hardware V2 (400 V -> 200 V, 5 kW, 50 kHz SiC synchronous buck)

This is the hardware/firmware contract between the V2 power board and the TMS320F28335 control board. It is a required implementation contract, not firmware: no controller has been written, simulated or tested, and hardware CAD completion does not establish closed-loop operation. Values come from the baseline [design_decisions.json](design_decisions.json) (schema 4, which wins over everything else), then from the research records [controller_aux_interconnect.json](research/controller_aux_interconnect.json), [sensing_protection.json](research/sensing_protection.json) and [gate_driver.json](research/gate_driver.json) after applying the corrections of their verification reports (research/verify_*.json). The V1 contract [firmware_interface.md](../../buck-48v-24v-1kw/design/firmware_interface.md) is the model; sibling V2 documents are [architecture.md](architecture.md), [assumptions.md](assumptions.md), [thermal_analysis.md](thermal_analysis.md) and [knowledge_application.md](knowledge_application.md); pin numbers are from [tms320f28335_pgf_pins.csv](../components/tms320f28335_pgf_pins.csv) (SPRS439Q Table 6-1).

Verification tags: [FD] fetched datasheet, [MP] manufacturer page, [SS] search snippet, [U] unverified, [AC] analytically checked (arithmetic here or a verified research calculation), [HR] human-review proposal. Nothing in this document is simulated. Values not in the baseline are marked "added" with their basis.

## 1. DSP pin and function table

All logic is 3.3 V; active-low names end in _N; "DSP view" is the level the firmware reads after the on-board logic. GPIO0-GPIO11 have no reset pull-ups [FD], so the board defines PWM_H, PWM_L and ARM low (10 k), RELAY_ON and BIAS_EN low, DSP_TRIP_N and ESTOP_N high while the DSP is in reset.

| Signal | Pin | GPIO / function | Dir | Required interpretation |
|---|---|---|---|---|
| PWM_H / PWM_L | 5 / 6 | GPIO0 EPWM1A / GPIO1 EPWM1B [FD] | out | Active-high complementary pair, gated on board by PWM AND ARMED AND RUN_PERMIT (UVLO_N, RDY_H, RDY_L); PWM_H drives HS IN+ and LS IN-, PWM_L drives LS IN+ and HS IN- (KR-GD-009 interlock, applied directly) |
| ARM | 7 | GPIO2 | out | Rising edge clocks D = 1 into the SN74LVC1G74; succeeds only while the latched-fault bus (CLR_N) is high; hold >= 1 us; low at all other times |
| RELAY_ON | 10 | GPIO3 (EPWM2B mux option [U]) | out | High = coil on through the AO3400A; 100 % drive for 100 ms, then PWM hold 50-60 % (REQUIRED by the baseline); never dropped under load (section 3) |
| RESET_N | 11 | GPIO4 | out | UCC21710 RST/EN of both drivers; low >= 1 us clears a driver FLT and disables the outputs [FD]; internal pull-down 28.5-113 k [FD] |
| BIAS_EN | 12 | GPIO5 | out | ENA of the three UCC14141-Q1 (V_IH <= 2.1 V, V_IL >= 0.8 V, soft-start time-out 28.4 ms [FD]) |
| DSP_TRIP_N | 13 | GPIO6 | out, open-drain style | Low = software fault into the latched group; board pull-up; held low until the self-test passes |
| FLT_H_N / FLT_L_N | 16 / 17 | GPIO7 / GPIO8 | in | Driver DESAT fault, open drain, latched in the driver until a RESET_N pulse; also in the latched group |
| RDY_H / RDY_L | 18 / 19 | GPIO9 / GPIO10 | in | Driver VDD UVLO good (12.0 V typ on / 10.7 V off [FD]); run-permit group, not latched |
| OVP_N | 20 | GPIO11 | in | Combined input (460 V) or output (230 V) comparator state; classify by the ADC snapshot (one GPIO for both) |
| FAULT_N (= ARMED) | 21 | GPIO12 / TZ1 [FD] | in | Latch Q; low = disarmed or fault; TZ1 one-shot, asynchronous qualification |
| OC_N | 24 | GPIO13 / TZ2 [FD] | in | TMCS1133 OC flag (37.5 A); TZ2 one-shot; also in the latched group |
| UVLO_N | 25 | GPIO14 / TZ3 [FD] | in | Bus run permit 340 V on / 320 V off; TZ3 one-shot, firmware auto-restart |
| OTP_N | 26 | GPIO15 / TZ4 [FD] | in | Hardware OTP 100 C heatsink: low when the NTC voltage falls below 0.708 V (CR-25) [HR]; TZ4 one-shot; latched group |
| FLT_12V_N | 27 | GPIO16 | in | TPS26400 FLT (open drain); latched group; a circuit-breaker trip also removes control power (section 4) |
| PG_BIAS_H_N / L_N / S_N | 28 / 62 / 64 | GPIO17 / GPIO18 / GPIO20 | in | DSP view high = bias good. The UCC14141 PG pin is LOW when good [FD] while the AND combiner needs high = OK, so the baseline (CR-26) inverts them in an SN74LV04A (PG_BIAS_*_OK, high = good): confirm polarity at bring-up with BIAS_EN low |
| ESTOP_N | 63 | GPIO19 | in | J_ESTOP with pull-up: open header = run [HR, section 11] |
| LED_RUN / LED_FAULT | 65 / 66 | GPIO21 / GPIO22 | out | 2 mA indicators |
| FAN_TACH | 68 | GPIO24 / ECAP1 [FD] | in | Fan tachometer (section 8) |
| SPARE_D2 | 73 | GPIO27 | - | Mezzanine pin 37; SPARE_D1 (pin 36) has no DSP pin in the baseline (GPIO26 / pin 72 is free - proposal) |
| UART_TX / UART_RX | 2 / 141 | GPIO29 SCITXDA / GPIO28 SCIRXDA [FD] | - | 3.3 V SCI-A on J_UART, no RS-232 levels; 115200 8N1, 10 Hz status frame, STATUS/RESET commands (added) |
| VIN_SENSE | 42 | ADCINA0 | ADC | 4.9834e-3 V/V (4 x 750 k + 10.0 k, AMC1311B gain 1, OPA2320 x 1.5) [AC]; 147 mV/LSB; 320 / 340 / 400 / 460 / 480 V = 1.595 / 1.694 / 1.993 / 2.292 / 2.392 V (codes 2177 / 2313 / 2721 / 3129 / 3265); full scale 602 V |
| ISENSE | 41 | ADCINA1 | ADC | TMCS1133C2A 0.33 V + 0.050 V/A at VS = 3.3 V [FD]; 14.65 mA/LSB; 0 / 25 / 27.5 / 37.5 A = 0.330 / 1.580 / 1.705 / 2.205 V (codes 450 / 2157 / 2327 / 3010); no-load valley -3.4 A = 0.16 V; full scale 53.4 A [AC] |
| TEMP_HS_NTC | 40 | ADCINA2 | ADC | 3.00 V x R_NTC / (2.2 k + R_NTC), NTCALUG01A103F 10 k, B25/85 3984 K [FD]: 2.46 V at 25 C, 1.09 V at 80 C, 0.88 V at 90 C, 0.71 V at 100 C, 0.57 V at 110 C [AC]; > 2.9 V = open sensor, < 0.1 V = short; sensor time constant 5 s [FD] |
| TEMP_CTRL | 39 | ADCINA3 | ADC | LM61: 0.6 V + 10 mV/C, control-board temperature (V1 pattern, [U]) |
| ISENSE_REF | 38 | ADCINA4 | ADC | TMCS1133 zero-current reference output, about 0.33 V; used for offset and ratiometric correction (section 7) [U: VREF pin behaviour to confirm in SBOSAG0E] |
| I12V_MON | 46 | ADCINB0 | ADC | TPS26400 IMON x 14.7 k: 1.151 V/A typ (gain 72-85 uA/A [FD]); 0.64 mA/LSB; 3.0 V = 2.4-2.6 A |
| VOUT_SENSE | 47 | ADCINB1 | ADC | 9.9338e-3 V/V (2 x 750 k + 10.0 k) [AC]; 73.7 mV/LSB; 200 / 230 / 240 V = 1.987 / 2.285 / 2.384 V (codes 2712 / 3119 / 3255); full scale 302 V; sampled simultaneously with ISENSE (A1/B1 pair) |
| V12V_MON | 49 | ADCINB3 | ADC | 0.1808 V/V (45.3 k / 10.0 k); 4.05 mV/LSB; 10.8 / 12 / 13.2 V = 1.95 / 2.17 / 2.39 V |
| Clock, reset, boot, JTAG | 105; 80; 169 / 172 / 173 / 174; 76-79, 85-87 | XCLKIN (X1 pin 104 grounded, X2 pin 102 open); XRS open drain; GPIO84-87 straps; TDI / TDO / TRST / TMS / EMU0 / EMU1 / TCK | - | 30 MHz oscillator, PLL to 150 MHz only after a clock check; XRS is collected from the TPS3808G01 (4.5 V with 101 k / 10 k, CR-18), the LDO resets and J_RESET - never drive it push-pull; J_BOOT follows the V1 pattern (GPIO84 low = SCI-A boot, 1111 = flash), positions to be read from the V2 schematic |

ADC: 12 bit, 0-3.0 V conversion range, internal reference with the V1 ADCREFM/P/RESEXT bypass, ADCCLK 25 MHz, acquisition window 16 ADCCLK = 640 ns behind the 1 k + 1 nF front-end on every pin (0.16 % droop [AC]). The analog pins clamp a diode above VDDA2 with +/-2 mA [FD]; 3.0 V is not an absolute maximum. Run the TI ADC calibration routine (ADC_cal, OTP) after reset before trusting any code (TI device documentation item).

## 2. PWM configuration (ePWM1)

- TBCLK = SYSCLKOUT = 150 MHz, up-down count, TBPRD = 1500 -> 50.00 kHz, 6.667 ns/tick, duty step 1/1500 = 0.067 % (0.27 V at V_OUT per step) [AC].
- Action qualifier: EPWM1A set at CMPA on the up-count, clear at CMPA on the down-count, so the HS pulse is centred on CTR = PRD and CTR = ZERO is the centre of the LS interval. CMPA = TBPRD x (1 - D): D = 0.5 -> 750, ceiling 0.85 -> 225.
- Dead band: active-high complementary (EPWM1B = inverted A), both edges delayed, DBRED = DBFED = 45 ticks = 300 ns at bring-up (baseline). Skew erosion <= 35 ns (driver part-to-part 30 ns [FD] + 5 ns RC mismatch) leaves >= 265 ns at the gates; effective target 250 ns; tune toward 200 ns by double-pulse test; never below 150 ns (23 ticks) nor above 400 ns (60 ticks) (CR-07; KR-GD-009 direct). Body-diode conduction costs about 1.15 W per 100 ns at 25 A [AC: 4.6 V x 25 A x 2 x 50 kHz]. The IN+/IN- interlock does not create dead time; only the dead-band module does.
- Minimum gate pulse 200 ns (the driver deglitch rejects < 40 ns [FD]); with DBRED this requires 2 x (PRD - CMPA) >= 75 ticks, i.e. a commanded duty >= 2.5 %; smaller pulses are skipped during soft start. Duty ceiling 0.85 (D = 0.556 at 360 V plus margin).
- Shadow loads at CTR = ZERO (one-period update) at bring-up; see section 9 for the double-update requirement.
- Trip zones: TZ1 (FAULT_N), TZ2 (OC_N), TZ3 (UVLO_N), TZ4 (OTP_N), all one-shot, both outputs forced low, asynchronous input qualification on GPIO12-15, TZ interrupt enabled; TZCLR only inside the recovery sequence. Before ARM both outputs are software-forced low.
- SOCA at CTR = ZERO (baseline) starts SEQ1 with the simultaneous pair A1/B1 (ISENSE / VOUT_SENSE), then A0/B0, A2/B2, A3/B3, A4. The sample lands 0.64 us after the ripple midpoint, 0.47 A below the average at the 0.74 A/us LS slope [AC]; correct it as a constant or trigger with CMPB on the down-count 96 ticks before ZERO. At D <= 0.85 the edge-free window around ZERO is >= 3 us.

## 3. Start-up sequence

1. 12 V applied: eFuse ramp 8.9-12.2 ms [FD], 5 V, 1.9 V core before 3.3 V, XRS released (TPS3808 20 ms [MP], LDO reset 200 ms [MP]). Boot from flash; safe GPIO states of section 1; DSP_TRIP_N low; both PWM outputs software-forced low; LED_FAULT on.
2. Clock check, PLL 150 MHz, flash wait states, ADC_cal, reference settling, calibration constants loaded (section 7).
3. Self-test (<= 100 ms): 10.8 V <= V12V_MON <= 13.2 V (software floor), FLT_12V_N high, I12V_MON <= 0.8 A (control board 0.29 A + fan <= 0.5 A; added), ESTOP_N high, |ISENSE - ISENSE_REF| < 0.5 A, VOUT_SENSE < 5 V (no pre-bias; controller record), TEMP_HS_NTC within 0.2-2.9 V, LM61 plausible, VIN_SENSE recorded (the source may already be on). Any failure -> FAULT state.
4. BIAS_EN high; within 50 ms (module time-out 28.4 ms [FD]) PG_BIAS_H/L/S_N must read good and RDY_H, RDY_L high (driver UVLO 12.0 V typ on [FD], rails 15 V). Timeout -> BIAS_FAIL, latched software fault.
5. RESET_N low >= 2 us, then high; FLT_H_N and FLT_L_N must read high.
6. Precharge through the PTC that sits permanently across the relay contacts (tau 5.8 ms, 4.4-7.3 ms; 99 % in 27 ms, 20-34 ms, with 48.7 uF [AC]; PTC part to be re-selected, CR-19): wait for VIN_SENSE > 340 V and start the 500 ms timer at that instant (added interpretation of the baseline timeout); when |dV_IN| < 2 V over two consecutive 10 ms windows (added) and 340 V < V_IN < 460 V, set RELAY_ON: 100 % for 100 ms, then PWM hold 50-60 % (for example 20 kHz on EPWM2B, added; Omron publishes only must-release >= 8 %, so the hold level is [HR]). Timer expiry -> PRECHARGE_FAIL, latched. Wait 100 ms, re-check 340-460 V. Relay operate time <= 50 ms [FD, J186-E1-01].
7. Pre-arm: all latched-group inputs high, UVLO_N high, RDY_H, RDY_L high; DSP_TRIP_N released; CMPA = PRD (D = 0); TZ flags still set.
8. ARM: GPIO2 rising edge; within 10 us GPIO12 (ARMED) must read high, otherwise a source is still active -> abort. TZCLR all one-shot flags, remove the software force.
9. Soft start: closed-loop voltage-reference ramp 0 -> 200 V in 100 ms (2 V/ms = 0.26 A of capacitor current with 132 uF; added) under the current clamps of section 6, pulses below 2.5 % skipped. Relay plausibility: a sag of V_IN > 20 V within the first 10 ms of load means the PTC is still in circuit -> RELAY_FAIL (added). V_OUT must reach 95 % of the reference within 500 ms, else SOFTSTART_FAIL (added).
10. RUN: voltage loop active, LED_RUN; the monitors of sections 5-8 execute every 1 ms.

Shutdown: reference ramp down or PWM stop, outputs forced low, ARM low. RELAY_ON is dropped only >= 10 ms after PWM stop and only once the source is off (VIN_SENSE < 320 V and falling) or on an operator command after the source has been switched off: the G9EA-1 maximum switching voltage is 400 V [FD], so it must never break load current (baseline). A 12 V loss opens the coil uncommanded, but the PWM stops first (bias UVLO inside the driver deglitch) and the relay releases >= 15 ms later at bleeder current only [AC].

## 4. Fault handling

Hardware groups (CR-17; KR-PR-002 direct). LATCHED group -> CLR_N, clears ARMED asynchronously (PWM AND gates block within ~12 ns, TZ1 forces both outputs low; source-to-gate <= 240 ns [AC]): FLT_H_N, FLT_L_N, OC_N, OVP_IN_N, OVP_OUT_N, OTP_N, FLT_12V_N, XRS_N, ESTOP_N, DSP_TRIP_N, PG_BIAS_H/L/S_N. RUN-PERMIT group (not latched, gates the PWM AND): UVLO_N, RDY_H, RDY_L, ARMED. Firmware never re-enables the PWM after a latched fault on its own; the one-shot flag is cleared only by the recovery sequence. Software faults are asserted through DSP_TRIP_N so the same hardware path disarms.

TZ ISR (highest priority): snapshot all fault GPIOs and the last ADC frame, drop ARM, enter FAULT, LED_FAULT, log over UART; the relay stays closed.

| Source | Class | Policy |
|---|---|---|
| FLT_H_N / FLT_L_N (DESAT; 0.55-1.07 us inside the driver [AC]) | latched | Operator reset. The baseline allows at most one automatic attempt; bring-up default: no automatic retry after DESAT because the C4MS025120K short-circuit withstand is unpublished (KR-PR-001 hard constraint) [HR] |
| OC_N (37.5 A) | latched | One automatic retry maximum: >= 1 s wait, RESET_N pulse, all sources clear, new ARM, soft start; a second OC -> operator reset; the counter clears only on operator reset |
| OVP_IN, OVP_OUT, ESTOP, PRECHARGE_FAIL, RELAY_FAIL, SOFTSTART_FAIL, 10 s overload, software limits | latched | Operator reset only |
| OTP_N (100 C hardware comparator) and firmware OTP (90 C) (CR-25) | latched | Operator reset; optional automatic restart after cooling 15 K below the trip (configurable, default off) |
| UVLO_N (bus < 320 V), RDY_H, RDY_L | run permit | PWM inhibited in hardware; TZ3 flag cleared by firmware; auto-restart with soft start 100 ms after V_IN > 340 V settled; RDY low > 100 ms -> BIAS_FAIL (latched) |
| FLT_12V_N | latched | A circuit-breaker trip (I_CB about 1.96 A, 4 ms) removes control power for 540 ms [FD]; the DSP restarts cold into a charged bus and possibly a pre-biased output; the no-pre-bias rule then waits for the 200 k bleeder (tau 24 s with 120 uF [AC]) - a pre-positioned soft start is a review option |

Operator reset = UART command or J_RESET. Recovery: all sources inactive, >= 1 s, RESET_N pulse, steps 4-8 of section 3, soft start.

## 5. Protection thresholds and tolerances

| Function | Setting | Tolerance / timing | Status |
|---|---|---|---|
| TMCS1133 OC | 37.5 A (V_OC 0.750 V from REF3125 via 2.32 k / 1.00 k) | 36.7-38.2 A typ, 33.7-41.2 A worst (+/-2 % / +/-10 %), hysteresis 3.5 A; chain 546 ns; overshoot 1.4 A at 175 uH -> worst peak ~42.6 A (CR-05); worst overload peak 32.0 A leaves 1.7 A | response and error rows [U] until quoted from SBOSAG0E; margins [AC] |
| DESAT | V_DS 3.6 V (3.2-4.0 V), 288 ns blanking + 95-180 ns deglitch | trip 52-85 A at 175 C (R_DS(on) spread); false-trip margin 1.67x typ / 1.35x max-R at overload; response 0.55-1.07 us vs 1.5 us budget | driver [FD], margins [AC], levels [HR] (KR-GD-004) |
| OVP_IN | 459.9 V (1.00 k / 11.0 k on 2.5 V) | +/-0.4 % RSS to +/-0.8 % worst at 25 C (REF3125 0.2 %, AMC1311B gain 0.2 %, 0.1 % resistors) = +/-2-4 V; TLV1702 560 ns | [AC], drift excluded |
| OVP_OUT | 229.8 V (953 ohm / 10.0 k; CR-04) | +/-1-2 V, same budget; a 25 A load dump reaches 215-218 V | [AC] |
| Bus UVLO | 340 V on / 320 V off (1.00 k / 1.91 k + 21.5 k hysteresis) | +/-1.5-3 V plus the asymmetric open-collector hysteresis: simulate or implement in firmware (baseline) | [HR] |
| Hardware OTP | 100 C sink: the TLV1702 trips (OTP_N low) when the NTC voltage falls below 0.708 V = 3.00 V x 10.0 k / (32.4 k + 10.0 k), ratiometric to the 3.00 V REF3130 pull-up reference (CR-25) | NTC +/-1 % R and +/-1 % B -> +/-1.5 K, pull-up and divider 1 % -> about 1 K, total about +/-2 K [AC]; the NTC reads 4-6 K below the device tab and T_J,HS ~ T_NTC + 50-66 K at full load (baseline), so a 100 C sink corresponds to T_J,HS 150-166 C - below the 175 C absolute maximum, above the 150 C design limit only at the max-R overload corner; the earlier 110 C proposal (0.57 V) mapped to 176-178 C and was lowered | [HR] (KR-TH-003: cooling supervision, not junction protection; firmware T_J estimator recommended) |
| eFuse | UVLO 10.0 / 9.3 V, OVP 14.45 / 13.4 V, I_CB ~1.96 A | 9.55-10.5 V, 13.8-15.2 V; 4 ms, 540 ms retry | [FD] |
| Firmware back-ups (added, all below the hardware levels) | V_IN > 455 V or V_OUT > 225 V for 1 ms; V_IN < 320 V software UVLO; T_NTC > 90 C trip, > 80 C derate and overload inhibit (CR-25); T_LM61 > 70 C warning; one ISENSE sample > 45 A; V12V_MON < 10.5 V prepare stop | checked at the 50 kHz ADC rate | [HR] |

## 6. Current and power limits

- Output: inductor-current reference clamp 27.5 A average. Between 25.5 A and 27.5 A a 10 s timer runs (110 % overload, baseline); expiry -> controlled shutdown as a latched software fault (sensing record). Average above 28.5 A for 1 ms means loss of current control -> trip (added).
- Input-current limit 15.6 A below 360 V (CR-20): there is no input-current sensor, so I_in,est = I_L x V_OUT / (eta x V_IN) with eta = 0.98 fixed (added), and the clamp is I_ref,max = min(27.5 A, 0.0764 A/V x V_IN): 24.5 A at 320 V, 26.0 A at 340 V, 27.5 A at 360 V [AC]. The 25 A fuse then sees <= 62 % at the 320 V corner (70 % without the limit).
- Thermal derating (added, [HR]; levels per CR-25): above 80 C at the NTC inhibit the 110 % overload (I_ref,max = 25 A) and reduce I_ref,max linearly to zero at the 90 C firmware trip; when the T_J estimator of section 7 exceeds 135 C, reduce it linearly to zero at 150 C; fan stall -> 50 % within 2 s (section 8).
- Negative current: the no-load CCM valley is -2.8 to -3.4 A (inside the -4.6 A sensor range); the reference lower clamp is I_ref,min = 0 A at bring-up (added, section 9).

## 7. Sensing calibration plan

- Current (TMCS1133): at every start with V_OUT < 5 V record ISENSE - ISENSE_REF as the offset. Output and VREF are ratiometric to VS while the ADC uses its internal 3.0 V reference, so compute I = (V_ISENSE - V_REF) / (0.050 V/A x V_REF / 0.33 V) to cancel a 3V3 rail error [U: ratiometry and VREF pin to confirm in SBOSAG0E]. Gain: two-point factory calibration at 10 A and 25 A DC against a reference meter; store gain and sensor temperature (the sensor sits beside the hot inductor). The hardware OC reference comes from the REF3125 and is not ratiometric: a +/-2 % VS error moves the trip by about -/+0.75 A [AC].
- Voltage (AMC1311 ladders): zero at a discharged bus (DC-LINK LIVE LED off, > 60 s after switch-off); gain at 100 V and 400 V (input) and at 100 V and 200 V (output) against a calibrated HV meter; verify OVP_IN by slowly raising the source and OVP_OUT with a bench source on the output terminals while disarmed.
- Temperature: NTC lookup from the Vishay R/T table (not the single-B equation) with B25/85 = 3984 K [FD; 0.5 % vs 1 % tolerance conflict open]; one-point check against the LM61 at ambient; resistor-substitution check of the 100 C comparator with 682 ohm (683 ohm in the Vishay R/T table; trip at 0.708 V; CB-PR-002 calibration method, adapted). T_J,est = T_NTC + 5 K + 1.81 K/W x P_HS,est (R_pad 1.4 + R_thJC 0.41 K/W, P_HS from the loss model) is the junction-temperature estimator the baseline recommends (CR-25); it is logging-only until validated by thermocouple (KR-TH-003, human review).
- LM61 and V12V_MON: offset check at ambient against a DMM; I12V_MON accepted at +/-8.5 % (monitoring only).

## 8. Fan TACH supervision

FAN_TACH on eCAP1 (150 MHz capture) measures the tachometer period of the integrated 12 V fan of the LAM 5 D K 100 12 (current <= 0.5 A budgeted; fan datasheet and the existence of a TACH wire [U]). Assume 2 pulses per revolution (added). Stall = no edge for 500 ms (added) -> derate to 50 % within 2 s (baseline) and warn; speed below 70 % of the commissioning value -> warning. Fan failure takes the sink from 68 to 100 C in 50-100 s, so the OTP ladder is the back-up (baseline). Without a TACH, the fallbacks are the I12V_MON current signature (0.3-0.5 A step) and the NTC rise rate.

## 9. Control-loop requirements

Plant: synchronous buck in CCM at all loads. L falls with current: 319 uH (0 A), 272 uH (25 A) nominal, 235 uH (25 A) worst, 175 uH at the 41 A fault corner (baseline); design range 230-350 uH (worst -8 % at 25 A to +8 % at no load) [AC]. C_out 108-132 uF (120 uF nominal); LC resonance 740-1010 Hz [AC]. Inductor slew (V_IN - V_OUT)/L = 0.46-1.04 A/us up and V_OUT/L = 0.57-0.87 A/us down: 12.5 A in 12-27 us, faster than the loop.

Requirements: inner average-current loop with the clamps of section 6 (gain scheduled by 400 V / V_IN, proposal) and an outer voltage loop with 2.0-2.5 kHz crossover (baseline); 12.5 A step -> <= 10 V excursion and <= 5 ms recovery (7.4 V at 2.5 kHz, 9.2 V at 2.0 kHz per the capacitor record); anti-windup on both integrators; stability over L 230-350 uH, V_IN 360-440 V, 0-27.5 A, resistor or CC/CR electronic load (no constant-power load below 20 % without review). First-order phase budget at the voltage-loop crossover (plant -90 deg, PI zero at fc/5 = -11 deg) [AC, no simulation]:

| Contribution | 2.5 kHz | 2.0 kHz |
|---|---|---|
| VOUT sense chain (16 kHz ladder RC, 32 kHz OPA filter, 159 kHz ADC RC, ~220 kHz AMC1311) | 15 deg | 12 deg |
| Sample-to-edge delay, single update (20 us + 10 us modulator) | 27 deg | 22 deg |
| Same with double update (SOCA at ZERO, SOCB at PRD, about 12 us) | 11 deg | 9 deg |
| Inner current-loop lag, fc_i = 6 kHz | 23 deg | 18 deg |
| Phase margin, single update, fc_i 6 kHz | 14 deg | 27 deg |
| Phase margin, double update, fc_i 6 kHz | 30 deg | 40 deg |
| Phase margin, double update, fc_i 6 kHz, sense filters >= 50 kHz | 40 deg | 47 deg |

The 6 kHz current loop itself has about 49 deg margin only with double update (15 us delay; 17 deg with single update) [AC]. Consequences: double-update sampling at both ripple midpoints (SEQ1 at ZERO, SEQ2 at PRD; ZERO only while D < 0.15) is required for the baseline crossover; 2.0 kHz with about 40 deg is the realistic bring-up target; 2.5 kHz additionally needs faster VOUT filtering (the 16 kHz AMC1311 input RC and the 32 kHz OPA filter are sensing-baseline values - a conflict for human review) or acceptance of about 30 deg; a type-III voltage-mode compensator without inner loop is the documented fallback. Limit cycling: the duty step (0.27 V at V_OUT) is coarser than the VOUT ADC LSB (74 mV), so the integrator step must stay below one ADC LSB per sample and a hunting amplitude <= 0.5 V must be shown in simulation [HR]; the F2833x HRPWM does not apply in up-down mode [U].

Load dump 25 A -> 0 A: V_OUT rises to 215-218 V, below the 230 V OVP (CR-04). Removing the surplus 0.37-0.47 J by driving the inductor current negative returns it to the 48.7 uF input bank: +17-22 V at 440 V, i.e. up to about 462 V against the 460 V OVP with a source that cannot sink (unidirectional flow) [AC]. Therefore I_ref,min = 0 A at bring-up; the output then decays through the 200 k bleeder and the load (218.5 -> 200 V in about 2 s at no load [AC]). A negative clamp of about -3 A may be enabled after a review of the input-bus energy balance [HR].

## 10. Knowledge applied

KR-GD-009 (interlock plus controller dead time) and KR-PR-002 (latched combined fault, UVLO lock-out) applied directly; KR-SN-005 (hardware OC path, ADC limits as back-up only) directly; KR-PR-001 adapted (the DESAT response is compared with an unpublished withstand - test required); KR-TH-003 human review (NTC thresholds and the T_J estimator); KR-GD-008 adapted (single-ended mezzanine link; the open-connector fail-safe test belongs in the test plan); KR-GD-004 human review (DESAT values); CB-PR-002 adapted-then-rejected for the readout route (CR-01) but its calibration method kept; CB-SN-004 adapted (TI 45/70 A trips not copied); SKILL-001 principle 9 and procedure step 8 direct; SKILL-005 procedure step 7 (calibration) direct; PE-PCB-005/007 direct (layout items outside firmware). Reference instance values (TIDA-010054 eFuse and Hall settings, CGD1700 filters) were not reused.

## 11. Verification status and open items

Analytically checked: all ADC scalings, codes and LSBs; PWM time base, dead-band ticks and erosion; minimum-pulse duty; sample-offset error; input-current clamp law; relay release ordering; comparator tolerance budgets; OTP tolerance and T_J mapping; soft-start capacitor current; load-dump energy return; phase budget (first order); limit-cycle condition.

Simulated: nothing. No loop gains, no soft-start waveform, no fault timing has been simulated; the ngspice layer of the repository has not been applied to this contract.

Unverified: TMCS1133 OC response maximum, threshold-error rows, VREF pin behaviour and ratiometry (SBOSAG0E rows to quote); EPWM2B availability on GPIO3 and HRPWM mode restriction (SPRS439Q / SPRU924); LM61 parameters (V1 carry-over); fan current, TACH output and pulses per revolution (Fischer datasheet inaccessible); NTC B tolerance (0.5 vs 1 %); PTC part (re-selection pending, CR-19); PG_BIAS inverter polarity at bring-up (SN74LV04A per CR-26); SPARE_D1 DSP pin.

Human review: NTC thresholds 80 / 90 / 100 C (CR-25; the earlier 90 / 100 / 110 C ladder was lowered because its hardware trip mapped to T_J 176-178 C) against T_J,HS ~ T_NTC + 50-66 K (the 100 C hardware trip corresponds to T_J,HS 150-166 C, above the 150 C design limit at the max-R overload corner); DESAT auto-retry policy (one attempt allowed by the baseline, none proposed here); relay PWM hold level versus the Omron must-release specification and the never-open-under-load rule; E-stop polarity (open header = run; a normally-closed loop would be fail-safe); UVLO comparator hysteresis (simulate or move to firmware); the 2.0-2.5 kHz crossover versus the sensing-chain filters and the single-update delay (double update, faster filters or 2.0 kHz); I_ref,min = 0 versus active output pull-down (input OVP margin at 440 V); pre-biased-output start after an eFuse retry (89 s bleeder wait or a pre-positioned soft start); PG_BIAS polarity; OVP_N classification by ADC. What remains unvalidated is everything that depends on a running controller: loop stability and margins, soft-start and load-step behaviour, the fault-recovery sequence timing, the input-current estimate accuracy, the T_J estimator and all firmware thresholds marked [HR]. This document does not authorise fabrication, energisation or connection of any hardware.
