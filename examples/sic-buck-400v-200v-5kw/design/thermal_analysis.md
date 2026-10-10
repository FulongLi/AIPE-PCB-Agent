**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# V2 thermal analysis: shared heatsink, insulating interface, NTC/OTP mapping, envelopes and test plan

[design_decisions.json](design_decisions.json) (schema 3) governs every value below. Where it is silent the research record [research/thermal.json](research/thermal.json) is used after applying the required changes of its two verifications ([engineering](research/verify_thermal_design_heatsink_interface_materi_engineering.json), [fact-check](research/verify_thermal_design_heatsink_interface_materi_factcheck.json)). Loss inputs come from [research/mosfet.json](research/mosfet.json); inductor and capacitor heat from [research/inductor.json](research/inductor.json) and [research/capacitors.json](research/capacitors.json). Nothing here is simulated or measured: every result is lumped steady-state arithmetic from tagged inputs.

Tags: [DS] fetched datasheet, [MP] manufacturer page, [SS] search-snippet or distributor listing, [UV] unverified assumption or estimate, [AC] analytically checked from the tagged inputs. No value in this document is [SIM] simulated.

## 1. Knowledge applied

| Id | Status | Use |
|---|---|---|
| SKILL-006 | adapted | principles 1-5 and procedure 1-6 at this design's 50 C ambient and 150/125 C limits; TI instance values (40 C, 0.5 and 0.1 C/W, 50/69 W) not copied; step 3 (films and magnetics out of the exhaust) is an AIPE recommendation without source evidence |
| KR-TH-001 | direct | hard constraint P_max with the shared-sink term, evaluated at every corner (section 3) |
| KR-TH-002 | direct; rating is human review | rated pad in the budget; rating, edge creepage and resistance closed numerically in section 8; rating conflict preserved (CR-13) |
| KR-TH-003 | human-review | NTC is cooling supervision; 90/100/110 C are review proposals; the direct SELV route (CR-01) deviates from "isolate NTC feedback" and is logged |
| CB-PR-002 | adapted, then rejected for this grounding scheme | driver-AIN thermistor path is fallback only (CR-01); its potentiometer calibration is kept |
| REF-TI-TIDA-010054 D9/D10 | adapted | two TO-247-4 per insulated forced-air sink, drivers under the leads; factor 2 read as a shared sink |
| REF-WS-CGD1700HB2M-UNA D8 | adapted | NTC isolation rationale; here the lug sits on a PE-bonded sink |
| KR-PCB-006, PE-PCB-006 | adapted | copper sized by the IPC-2221 formula (section 7); the low-confidence rule does not carry the sizing |
| KR-ISO-002, KR-ISO-004 | human-review / adapted | 5.0 mm HV-to-PE DRC taken from the baseline, not derived here; slots if creepage limits |
| KR-PCB-004/005, PE-PCB-001/003/005 | direct | sink placement must not lengthen the loops; NTC and TACH wiring away from SW |
| KR-CAP-003 | placement rule only | the >= 125 C ceramic rating is an AIPE recommendation, not KR-CAP-003 content |
| KR-PR-001, KR-GD-011, SKILL-003 | not applicable | OTP is a seconds-scale supervisor, no protection against device faults |
| CMP-* | none applied | no component record exists for the LAM 5, Sil-Pad or NTCALUG parts; CMP-B32716H8306K000 is a different TDK film part |

## 2. Thermal path and inputs

Model (KR-TH-001; SKILL-006 principle 1): T_sink = T_A + P_total R_th,HS; T_J,dev = T_sink + P_dev (R_pad + R_spread + R_JC). Equal sharing enters only through the lumped sink term; the HS/LS split (57/43 % at 360 V) is carried explicitly. KR-TH-001 P_max form: (T_J,lim - T_A)/(2 R_th,HS + R_pad + R_JC).

| Input | Value | Tag |
|---|---|---|
| Ambient at the fan intake | 50 C, no enclosure preheating | baseline assumption |
| T_J design limit / preference / absolute | 150 / 125 / 175 C | baseline; 175 C [DS] |
| R_th,JC C4MS025120K | 0.41 K/W typical, no maximum published | [DS] Rev. 2, Dec 2025 |
| R_DS(on) at 150 C | 48.5 mohm typ (28 mohm at 15 V, tempco 1.88 at 175 C); "max-R" 57.2 mohm (33 mohm 18 V maximum, scaled); 64.1 mohm (37 mohm 15 V scaled estimate) | interpolated from [DS] 25/175 C data, not datasheet values |
| Heatsink Fischer LAM 5 D K 100 12 | 0.30 K/W forced, 14.3 m3/h, 100 x 100.5 x 50 mm, integrated 12 V fan | [SS] novapart; Fischer site blocked |
| Fan at 10.8 V | flow -10 %, R_th +6 % (flow exponent 0.6-0.8) | [UV] |
| Interface Sil-Pad TSP A2000, 0.254 mm | impedance 0.59/0.50/0.42 C-in2/W at 10/25/50 psi; design R_pad 1.4 K/W (clip, about 25 psi on the 2.3 cm2 exposed tab metal; 1.16 K/W screw-mounted at 50 psi) | [DS] TDS Nov 2018; 1.4 K/W [AC] on the exposed-tab area (section 8; baseline CR-21) |
| Spreading, two sources on one profile | 0.1-0.2 K/W per device (+3-7 K) | [UV] allowance, to be measured |
| Natural-convection R_th, fan stalled | 1.73 K/W (sibling D K 125 24) to about 2.2 K/W (length-scaled) | [SS] / [UV] |
| Heatsink mass with fan | 0.3-0.6 kg | [UV] |

## 3. Device losses and junction temperatures (baseline sink and pad)

Losses at T_J 150 C from the MOSFET record (k_RG 1.3, dead time 250 ns) [AC]. "max-R" scales conduction by 57.2/48.5 = 1.18, the basis of the baseline thermal results; the 64.1 mohm basis behind the baseline "400V_25A_max_rds 56.5 W" appears as a sensitivity. Thermal path per device R_pad + R_JC = 1.4 + 0.41 = 1.81 K/W (CR-21).

| V_in / I_out | typ P_HS / P_LS / P_tot (W) | max-R P_HS / P_LS / P_tot (W) | T_sink typ / max-R (C) | T_J,HS typ / max-R (C) | T_J,LS typ / max-R (C) |
|---|---|---|---|---|---|
| 360 V / 25 A | 26.0 / 19.7 / 45.7 | 29.0 / 22.1 / 51.2 | 63.7 / 65.4 | 110.8 / 117.9 | 99.4 / 105.4 |
| 360 V / 27.5 A, HS hottest | 30.4 / 23.2 / 53.6 | 34.1 / 26.1 / 60.2 | 66.1 / 68.1 | 121.1 / 129.8 | 108.1 / 115.4 |
| 400 V / 25 A, nominal | 25.1 / 21.7 / 46.8 | 27.8 / 24.4 / 52.3 | 64.0 / 65.7 | 109.4 / 116.1 | 103.3 / 109.9 |
| 440 V / 25 A | 24.6 / 23.4 / 48.0 | 27.1 / 26.4 / 53.5 | 64.4 / 66.0 | 108.9 / 115.1 | 106.8 / 113.8 |
| 440 V / 27.5 A, highest P_tot | 28.7 / 27.6 / 56.3 | 31.7 / 31.2 / 62.9 | 66.9 / 68.9 | 118.8 / 126.3 | 116.8 / 125.4 |

Baseline results (schema 3, CR-21) reproduced within rounding: 400 V / 25 A typ T_sink 64 C, T_J,HS 109.4 C; 360 V / 27.5 A max-R T_sink 68 C, T_J,HS 129.8 C; 440 V / 27.5 A max-R 126.2-126.3 C. The HS junction is hottest at minimum input (D = 0.556) while the sink is hottest at maximum input; the 360 V / 27.5 A max-R corner governs.

KR-TH-001: P_max = 100/(0.60 + 1.4 + 0.41) = 41.5 W at 150 C, margin 1.22 over 34.1 W (1.36 over 30.4 W typ); 31.1 W at 125 C, i.e. 0.91 of the 34.1 W max-R overload loss and 1.02 of the 30.4 W typical value. The 125 C preference therefore holds at 400 V / 25 A with typical parts (109 C), at every 25 A corner with max-R parts (<= 118 C) and at the typical overload corners (119-121 C), but not at the 10 s overload with max-R parts (126-130 C) - as the baseline records (CR-21); any spreading allowance adds 3-7 K on top.

Sensitivities at 360 V / 27.5 A, max-R [AC]:

| Case | P_HS (W) | T_sink (C) | T_J,HS (C) | P_max margin |
|---|---|---|---|---|
| spreading +0.1 / +0.2 K/W | 34.1 | 68.1 | 133.2 / 136.6 | 1.22 |
| R_pad 1.16 K/W (screw-mounted at 50 psi; full-depth insulating bushing only) | 34.1 | 68.1 | 121.6 | 1.35 |
| R_pad 0.96 K/W (full body-outline area; optimistic, lower bound of the measurement band only) | 34.1 | 68.1 | 114.8 | 1.49 |
| fan at 10.8 V (R_th 0.318 K/W) | 34.1 | 69.1 | 130.8 | 1.20 |
| R_G,on 10 ohm at bring-up (k_RG 1.9) + 1 W HS E_oss | 39.6 | 69.7 | 141.5 | 1.05 |
| 64.1 mohm basis | 37.0 | 69.6 | 136.6 | 1.12 |
| 64.1 mohm + k_RG 1.9 + E_oss | 42.6 | 71.3 | 148.4 | 0.97 |
| all of the above + spreading 0.2 + fan 10.8 V | 42.6 | 72.6 | 158 | none |

Each pessimistic assumption on its own keeps T_J,HS below 150 C, but the margins are thin: the 10 ohm bring-up gate resistor alone takes the max-R overload corner to about 141 C, the 64.1 mohm basis combined with it to about 148 C (P_max margin 0.97), and the fully stacked case (every bound at once during the 10 s overload) reaches about 158 C, below the 175 C absolute maximum - hence the R_pad and spreading measurements (section 11), the R_G,on tuning toward 6.8 ohm and the overload-inhibit proposal of section 6. Expected operation is cooler: iterating R_DS(on) with T_J at 400 V / 25 A converges to 40.9 mohm, 42.0 W, T_sink 63 C, T_J,HS 104 C.

## 4. Single-width cost-down option (LAM 5 K 100 12, 0.68 K/W [SS])

| 360 V / 27.5 A max-R (34.1 W, 60.2 W) | T_sink (C) | T_J,HS (C) | P_max at 150 C (margin) | sink for T_J 150 C |
|---|---|---|---|---|
| R_pad 1.4 (TSP A2000 design value, CR-21) | 90.9 | 152.6 | 31.5 W (0.93) | 84 C |
| R_pad 1.16 (screw-mounted at 50 psi) | 90.9 | 144.4 | 34.1 W (1.00) | 92 C |
| R_pad 1.0 (baseline admissibility condition: measured R_pad <= 1 K/W) | 90.9 | 139.0 | 36.1 W (1.06) | 98 C |
| R_pad 0.96 (TSP 3500 at 40 N, body-outline area) | 90.9 | 137.6 | 36.6 W (1.07) | 99 C |
| R_pad 1.0, fan at 10.8 V | 93.4 | 141.5 | - | - |

With the 1.4 K/W design pad the single-width sink fails the 150 C limit at the hottest max-R corner (153 C) and P_max falls below the 34.1 W HS loss; only a measured R_pad <= 1 K/W restores a 6-7 % margin, the 125 C preference is lost at every corner (400 V / 25 A typ: 117-127 C for R_pad 1.0-1.4 K/W), and the steady-state sink (91-93 C) sits above the 90 C derate proposal and 7 K below the 100 C trip. The baseline conditions stand: cost-down only if the measured R_pad is <= 1 K/W and the OTP thresholds are raised consistently (sink <= 98 C for T_J 150 C at full load), with the 125 C preference explicitly waived. Not recommended for the prototype.

## 5. Fan failure and fan budget

The natural-convection resistance of the D K 100 12 is unknown. With 1.73-2.2 K/W [SS]/[UV] the fan-stalled steady state at 400 V / 25 A typ is T_sink 131-153 C and T_J,HS 176-198 C; at the overload corner 154-182 C and 216-244 C. T_J exceeds the 175 C absolute maximum at every estimate, so the OTP is mandatory and full power without the fan is impossible. Time from the 68 C steady state to the 100 C trip: adiabatic bound 185-370 s for 0.3-0.6 kg [UV], lumped 280-670 s; the baseline's 50-100 s (carried over from the hotter single-width case) is kept as the conservative requirement for the supervision chain: sample the NTC at least once per second and derate within 2 s of a FAN_TACH (GPIO24/ECAP1) stall. A derate to 50 % load (about 16 W total) gives a natural-convection sink of about 85 C at 2.2 K/W, below the 90 C warn level; 25 % load gives about 63 C [AC on [UV] R_nat] - review proposal for the firmware contract. T_J,HS reaches 175 C at a sink temperature of about 130 C (400 V / 25 A typ losses), 20 K above the hardware trip.

Fan: integrated 12 V unit, current unknown, budgeted 0.5 A maximum (12 V budget 1.76 A worst pull-in against I_CB about 1.96 A, CR-02); fed behind the TPS26400 with the upstream fallback; inrush not budgeted [UV]; at 10.8 V flow -10 % gives R_th +6 % and +1 K on the sink.

## 6. NTC position, readout, mapping and threshold logic (KR-TH-003, CR-01, CR-06, CR-08)

Sensor Vishay NTCALUG01A103F [DS, document 29092 rev 14-Jan-2026]: 10 kohm 1 %, B25/85 3984 K 0.5 %, -55 to +150 C, 13 mW/K, thermal time constant 5 s, 1500 Vac terminals-to-lug, 100 Mohm at 500 VDC, M3 ring lug, AEC-Q200. Mounting: M3 thread-forming hole on the sink top face beside the HS footprint (no bare aluminium exists between the bodies at 28 mm pitch with 28 mm pads); spreading offset +4-6 K [UV]. Route: two-wire lead to J_NTC, 2.2 kohm pull-up to the buffered 3.00 V REF3125 + 100 nF, 1 k + 1 nF at ADCINA2. The lug is at PE and GND_CTRL is PE-bonded at one point (A-23), so no isolator is needed; this is a logged deviation from the rule's "isolate NTC feedback", with CB-PR-002 through the LS driver AIN as fallback only.

| T_sink (C) | R_NTC (ohm) | V_ADC (V) | 12-bit count | note |
|---|---|---|---|---|
| 25 | 10000 | 2.459 | 3357 | calibration point |
| 70 | 1734 | 1.322 | 1805 | steady state 64-72 C |
| 85 | 1066 | 0.979 | 1337 | end of the B25/85 range; use the Vishay R/T table above 85 C (1-2 K extrapolation error) |
| 90 | 915 | 0.881 | 1203 | warn / derate proposal; 18.8 mV/K |
| 100 | 682 | 0.710 | 969 | firmware trip proposal; 15.5 mV/K = 21 LSB/K |
| 110 | 516 | 0.570 | 778 | hardware TLV1702 trip, ratiometric 0.190 x V_ref; 12.5 mV/K |

Self-heating <= 1.0 mW / 13 mW/K = 0.08 K. Tolerances (R25 1 %, B 0.5 %, pull-up 1 %) give about +/-1.2 K at 100 C plus the R/T extrapolation; calibrate with a potentiometer in place of the NTC (CB-PR-002 method) and validate against the thermocouple at the NTC position.

Mapping T_J,HS = T_NTC + (4-6 K) + P_HS (R_pad + R_JC), with R_pad + R_JC = 1.4 + 0.41 = 1.81 K/W [AC] (baseline: T_NTC + 50-66 K at full load); T_J values use the 4 K spreading offset, +2 K at 6 K:

| Load case | P_HS (W) | offset (K) | T_J,HS at sink 90 / 100 / 110 C | sink for T_J 150 C |
|---|---|---|---|---|
| 400 V / 25 A typ | 25.1 | 49-51 | 139 / 149 / 159 | 101 C |
| 400 V / 25 A max-R | 27.8 | 54-56 | 144 / 154 / 164 | 96 C |
| 440 V / 27.5 A max-R | 31.7 | 61-63 | 151 / 161 / 171 | 89 C |
| 360 V / 27.5 A max-R | 34.1 | 66-68 | 156 / 166 / 176 | 84 C |

The baseline's "T_NTC + 50-66 K at full load (1.4 K/W pad; up to 66 K with max-R parts)" is reproduced: 49-51 K at 400 V / 25 A with typical parts, 54-56 K at 25 A with max-R parts and 66-68 K at the max-R overload corner. Threshold logic with the D K sink: the 90 C warn level is 18-26 K above every legal steady state (64-72 C), hence nuisance-free (unlike the single-width case); but at the 100 C firmware trip T_J,HS is already 149-151 C at rated 25 A with typical parts and 154-156 C with max-R parts, and during the 110 % overload with max-R parts it would reach 166-168 C at the firmware trip and 176-178 C at the hardware trip. The 110 C comparator alone therefore does not keep T_J below the 175 C absolute maximum at that corner, and the 100 C firmware trip does not keep it below the 150 C design limit at any full-load corner. Proposals for review: (a) the 90 C warn level inhibits the overload and limits I_out to 25 A, so that the 100 C trip bounds T_J at about 151 C (typical) / 156 C (max-R); (b) added proposal, basis this mapping: if T_J <= 150 C at the firmware trip is required, the ladder must move down to about 84 / 94 / 104 C (the sink temperature for T_J 150 C is 96 C at the 25 A max-R corner and 84 C at the max-R overload corner) or the trip must use the T_J estimator of the firmware contract. All three levels remain KR-TH-003 review proposals (cooling supervision, not junction protection); with a 5 s time constant and a 49-68 K offset the NTC cannot see a single-device fault.

## 7. Inductor, film capacitors, ceramics and copper

Inductor L1 (2 x Magnetics 0058192A2 High Flux, 34 turns AWG 10, potted cup 72 x 46 mm): losses 16.4 W (400 V / 25 A), 17.7 W (440 V / 25 A), 19.8 W (440 V / 27.5 A) typical and 23-26 W bounded (datasheet-maximum core loss 1.44 x fit plus DC-bias allowance) [AC from Magnetics catalogue fits and [DS] core data]. Surface 161 cm2 (the cup offers about 145-185 cm2 with the bottom partly blocked).

| P_L (W) | still air, Magnetics (P_mW/A_cm2)^0.833 | forced, h 24-34 W/m2K incl. radiation | hot spot (+10-15 K) in 50 C bypass air | in 62-64 C exhaust air |
|---|---|---|---|---|
| 16.4 | 47 K | 30-42 K | 90-107 C | 102-121 C |
| 19.8 | 55 K | 36-51 K | 96-116 C | 108-130 C |
| 23-26 | 62-69 K | 47-67 K | 107-132 C | 119-146 C |

The still-air hot spot of 110-120 C typical and up to 134 C bounded confirms CR-14: forced air over the cup is required. The D K exhaust carries 47-63 W in 14.3 m3/h [SS]: +10-14 K and about 1.3 m/s mean velocity (0.005 m2, 60 % open) [AC on [SS] flow]; the ">= 2 m/s" seed is not demonstrated and is superseded by the sink's rated R_th once the Fischer datasheet is obtained. The inductor therefore belongs in the bypass or side stream at 50 C air, >= 20 mm from the sink (baseline placement rule, CR-23; films >= 20 mm from the sink and >= 15 mm from the inductor), not in the exhaust cone. Acceptance (inductor record): inner-diameter winding thermocouple <= 110 C after 1 h at 440 V / 25 A / 50 C; the typical case passes with 3-20 K margin, the bounded case fails and triggers the 3-stack fallback (CR-14). Thermal mass about 440 J/K, tau about 20 min: the 10 s overload adds < 0.1 K. Potting class >= 130 C, wire 200 C class.

Film capacitors (TDK B32776G8206K input, B32776G4606K output [DS]): input 6.92 A each worst, ESR 7.5 mohm -> 0.36 W, R_th 12.7 K/W (from the 20 K / 14.5 A rating) -> +4.6 K, plus 3.1 K for the 0.25 W film-to-ceramic ring share: hot spot about 68 C at 60 C local air (assumption A6), about 72 C if placed in the exhaust; output 1.43 A each, +0.1 K. Limits: 105 C case class, 85 C full-voltage point [DS]; the -1.33 %/K derating above 85 C is unverified (514 V at 105 C if it holds, above 480 V). Baseline rule: >= 20 mm from the sink and outside the exhaust (SKILL-006 step 3 recommendation); the 37 and 45 mm tall parts cannot sit in the <= 10 mm corridors anyway.

HV ceramics beside the legs: case temperatures at 400 V / 25 A typ are HS 99 C and LS 94 C (T_sink + P R_pad with 1.4 K/W), lead copper 80-95 C; the X7T 125 C rating keeps >= 25 K margin (AIPE recommendation). TMCS1133 conductor 0.44 / 0.53 W at 25 / 27.5 A; its 80 Arms rating is a 25 C figure (44 Arms at 125 C) [DS].

Copper by the IPC-2221 formula I = k dT^0.44 A^0.725 (k 0.048 outer / 0.024 inner, A in mil2, 70 um; conservative relative to IPC-2152) [AC]:

| Current | outer width for 10 / 20 / 30 K | inner width for 10 / 20 / 30 K | baseline 12 mm outer | baseline 22 mm inner |
|---|---|---|---|---|
| 25 A | 12.7 / 8.4 / 6.5 mm | 33.1 / 21.7 / 17.0 mm | 11 K | 20 K |
| 27.5 A | 14.5 / 9.5 / 7.5 mm | 37.8 / 24.8 / 19.4 mm | 14 K | 24 K |

Vias with 25 um plating: 0.3 mm drill = 36.5 mil2 -> 1.22 A at 20 K, so 24 vias carry 25 A at 1.04 A each; 0.5 mm drill 1.76 A, 21 vias at 1.19 A each. Loss at 100 C: 12 mm x 70 um = 0.265 mohm/cm -> 0.17 W/cm at 25 A, about 2.5 W for a 15 cm path (0.05 %). The SW pour is held to the width that meets 20 K (dv/dt coupling, PE-PCB-005); VIN+, VOUT+ and PGND pours use >= 12 mm outer and >= 22 mm inner on two stitched layers.

## 8. Interface, hardware and insulation (KR-TH-002 closed numerically)

Pad: Bergquist Sil-Pad TSP A2000, 0.254 mm [DS TDS Nov 2018]: 2.0 W/mK, impedance 0.59/0.50/0.42/0.34 C-in2/W at 10/25/50/100 psi, 6000 Vac ASTM D149 breakdown, Dk 7.0, -60 to 180 C, fibreglass carrier, UL 94 V-0; custom cut 28 x 32 mm per device, no hole.

| Clip force | area 3.37 cm2 (16 x 21 mm body outline) | area 2.3 cm2 (exposed metal D1 x E1 about 17.0 x 13.6 mm, to confirm on the TO-247-4L drawing) |
|---|---|---|
| 40 N | 17 psi -> 1.05 K/W | 25 psi -> 1.40 K/W |
| 60 N | 26 psi -> 0.95 K/W | 38 psi -> 1.29 K/W |

The baseline's 1.4 K/W design value (CR-21) is the 40 N / about 25 psi case on the exposed tab metal; the body-outline figures (0.95-1.05 K/W) are optimistic and serve only as the lower bound of the 1.0-1.4 K/W measurement band, which the D K sink absorbs (section 3) and the measurement plan resolves; 1.16 K/W applies to screw mounting at 50 psi, admissible only with a full-depth insulating bushing (below). Capacitance to the earthed sink 56-82 pF -> LS (SW) tab displacement current 2.8-4.1 A at 50 V/ns (6-9 A at the 110-120 V/ns quoted by the inductor record); the HS tab is at VIN+ (DC). The baseline's "2.3 A" is the TSP 3500 (47 pF) figure - EMC/PE input to update. TSP 3500 (4000 Vac, 3.5 W/mK, 1.20 K/W clip / 0.92 K/W screw on the exposed-tab area; 0.96 K/W at 40 N on the body area) remains the thermal alternative only if the assembled-pad type test at the 4 kV impulse basis passes.

Insulation geometry [AC]: the 28 x 32 mm pad against the 16 x 21 mm outline gives 6.0 / 5.5 mm overhang -> surface path tab edge to sink >= 5.5 mm against the baseline HV-to-PE DRC of 5.0 mm (IEC 60664-1 Table F.4, 500 V, PD2, group IIIa, secondary source; KR-ISO-002 review). Stock 19 x 24 mm die-cuts give 1.5 / 1.5 mm and are rejected (arithmetic corrected). At 28 mm pitch two 28 mm pads abut with zero gap; one 60 x 32 mm strip (8.0 / 5.5 mm margins) is the equivalent single cut, recommended for assembly. Should the isolation review adopt the IEC 60947-derived 6.3 mm, a 30 x 34 mm pad or 60 x 34 mm strip (6.5 mm) is needed; a reinforced 10 mm cannot be met at 28 mm pitch. Clip metal to the leads >= 3 mm: the LAM 5 K clip bears on the plastic body above the lead row, but clip width and spring force (>= 40 N to verify) are unpublished [UV] and must be checked on the mechanical drawing. Pad voltage rating: 6000 Vac breakdown is a destructive 60 Hz value, not a withstand rating; the 4 kV impulse basis (600 V-system row) against 2.5 kV (OVC II, 300 V system) is a preserved human-review conflict (CR-13), and the type test on the assembled pad is the isolation review's to define.

Hardware: LAM 5 K retaining clips primary. The baseline (CR-21) rejects the Boyd 7721-7PPSG shoulder washer named in the research record: its 0.81 mm shoulder covers one third of the 2.23-2.54 mm hole depth, leaving 0.4-0.55 mm of air between the screw and the drain-potential hole wall - not acceptable at 400-480 V. Screw mounting is admissible only with a TO-247 bushing whose shoulder covers the full hole depth and is rated for the working voltage (part still to be found - human review); otherwise the screw alternative is deleted.

Electrical side effect of the standing geometry (bodies 20-25 mm above the PCB, leads trimmed short): 15-25 nH per lead, 40-60 nH total loop against the <= 20 nH board target; the 1200 V class absorbs it (62-150 V overshoot, 42-49 % utilisation).

## 9. Mechanical envelopes to reserve

| Item | Footprint and height | Mass | Notes |
|---|---|---|---|
| Heatsink LAM 5 D K 100 12 with corridors | 175 x 110 mm strip (100 body + 15 fan + 30 intake + 30 exhaust; 100.5 mm profile + 5 mm keep-out each side); 50 mm high, device bodies 20-25 mm above the PCB | 0.3-0.6 kg [UV] | stands on the power board, 2-4 M3 fixings plus the M4 PE stud bond to the baseplate; corridor parts <= 10 mm tall; no HV copper on outer layers within 5 mm of the outline, clips and mounting pins; exhaust toward a vent |
| TO-247-4 pair | 28 mm pitch on one face, lead row 3-5 mm from the face | - | drivers and decoupling on B.Cu within 15 mm of the leads |
| NTC | M3 hole on the top face beside the HS footprint | - | twisted pair away from SW |
| Inductor cup | keep-out circle 75 mm, 48 mm high; 4 x M4 standoffs on 60 x 60 mm; 4.3 mm NPTH with 8 mm copper-free annulus | 0.75-0.8 kg potted | >= 20 mm from the sink (CR-23), in the bypass stream; films >= 15 mm from the cup; mass never on the solder joints |
| C_IN, 2 x B32776G8206K | courtyard 28 x 42 mm, 37 mm high | - | >= 20 mm from the sink, outside the exhaust |
| C_OUT, 2 x B32776G4606K | courtyard 30 x 45 mm, 45 mm high | - | same |
| Standoffs and stack | power board on 6 x M4 x 15 mm; control board 11 mm above the SELV strip | - | heights above the baseplate: sink 15 + 2 + 50 = 67 mm (the baseline mechanical line sums 15 + 2 + 55 = 72 mm with an unexplained 55 mm sink term - orchestrator item), inductor 65, C_OUT 62, C_IN 54, control board about 40 mm, all under the 80 mm limit |

Total assembly about 1.9 kg (estimate).

## 10. Cooling assumptions and model limitations

No CFD or thermal simulation. Lumped steady-state model with an isothermal sink; equal sharing enters only through the sink term, and TI's factor 2 is interpreted as two devices per sink, not explained. All Fischer figures (0.30 K/W, 14.3 m3/h, fan current, mass, natural R_th) are distributor-level and valid for a uniformly heated profile, hence the separate spreading allowance. R_th,JC is a typical value without maximum; the 150 C R_DS(on) values are interpolations; the interface resistance depends on clamp pressure and the true contact area (1.4 K/W design value on the exposed tab metal; 1.0-1.4 K/W band to be measured). 50 C is assumed at the fan intake with no recirculation; radiation and PCB conduction are neglected (conservative). The 10 s overload is evaluated with steady-state losses: exact for the device terms (seconds) and conservative for the sink term (tau 80-160 s forced). The inductor rise rests on an empirical correlation (+/-30 %) and an assumed convective coefficient. No transient or power-cycling lifetime analysis (SKILL-006 known limitation).

## 11. Measurement plan

Thermocouples (type K, 0.2 mm, cemented or taped under polyimide, logged at 1 Hz):

| Point | Location | Acceptance |
|---|---|---|
| TC1, TC2 | sink face beside the HS and LS footprints (1 mm pockets or flat spots) | <= 75 C at 400 V / 25 A / 50 C (predicted 64 C) |
| TC3 | at the NTC lug position | NTC within +/-3 K of TC3 after calibration; TC3 - TC1 is the spreading offset (expected 4-6 K) |
| TC4, TC5 | HS and LS case: exposed tab edge above the pad, or a groove in the pad | (TC4 - TC1)/P_HS <= 1.4 K/W (design value; 1.6 K/W with the spreading allowance); above 1.0 K/W the single-width option is dead |
| TC6, TC7 | inductor inner-diameter winding (fitted at winding, under the potting) and cup surface | TC6 <= 110 C after 1 h at 440 V / 25 A |
| TC8, TC9 | C_IN film body (hot spot); HV ceramic row beside the legs | <= 85 C; <= 110 C |
| TC10 | SW / VOUT pour neck | <= 20 K above TC11 |
| TC11, TC12 | intake air; exhaust air | exhaust minus intake 10-14 K at full load |
| TC13 | TMCS1133 package | <= 110 C |

Sequence: (1) NTC chain calibration with a precision potentiometer in place of the NTC at the 25 / 90 / 100 / 110 C resistances (10000 / 915 / 682 / 516 ohm) and comparator trip check at 0.570 V; (2) soak at 400 V / 25 A in a 50 C chamber (or at room ambient with the rise added) until every point drifts < 1 K per 10 min (>= 30 min sink, >= 60 min inductor); (3) 360 V / 27.5 A for 10 s at the end of the soak, then 440 V / 27.5 A for 10 s, TC4 and TC5 logged at 10 Hz; (4) repeat (2) with the fan at 10.8 V; (5) fan-stall test at 25 % load with all trips armed: block the fan, log TC1 and the NTC, confirm the TACH derate within 2 s, the 90 C warn, the 100 C firmware trip and, with the firmware trip masked, the 110 C comparator; abort manually at TC4 120 C; the slope yields R_nat and the time constant; (6) optional T_J estimate by the body-diode V_SD method after switch-off, and an infrared scan of the open board. Derived quantities: R_th,sink = (TC1 - TC11)/P_total with P_total from the electrical loss measurement or exhaust-air calorimetry (rho c_p Q dT); R_pad + spreading = (TC4 - TC1)/P_HS. The results decide the single-width option, the OTP thresholds and the 2-stack versus 3-stack inductor.

## 12. Verification status and open items

Analytically checked: losses at the operating points on three R_DS(on) bases; T_sink and T_J for the baseline sink and pad with seven sensitivities; KR-TH-001 P_max and margins; the single-width option; fan-fail steady state and time to trip; NTC divider, sensitivity, tolerance and mapping; inductor rise with two models; film self-heating; IPC-2221 widths, via capacity and copper loss; pad resistance against force and area, capacitance, creepage margins; height stack.

Simulated: nothing; no thermal network or CFD model was run.

Fetched-datasheet level: C4MS025120K R_th,JC, R_DS(on) and T_J,max; Sil-Pad TSP A2000 and TSP 3500 TDS; Vishay NTCALUG01A103F rev 14-Jan-2026; TDK B32776 film data; Magnetics core data. Search-snippet level: every Fischer LAM 5 figure; Boyd washer dimensions. Unverified: natural-convection R_th and mass of the D K unit, fan current and inrush, flow exponent, spreading allowance, true pad contact area and clip force, inductor convective coefficient and bounded core loss, the 5.0 mm creepage figure, the -1.33 %/K film derating.

Human review: KR-TH-002 pad voltage rating against the impulse basis (CR-13) and the type test; KR-ISO-002 creepage value (5.0 / 6.3 / 10 mm) and pad size; KR-TH-003 thresholds 90/100/110 C, the overload-inhibit proposal and the direct SELV NTC route (deviation from "isolate NTC feedback", contingent on A-23); a full-depth TO-247 insulating bushing if screw mounting is wanted (Boyd 7721-7PPSG rejected, CR-21); the NTC threshold ladder against the 1.81 K/W mapping (110 C hardware trip = T_J 176-178 C at the max-R overload corner, 100 C firmware trip = 154-156 C at 25 A max-R; proposals (a)/(b) of section 6); baseline figures to update: LS tab displacement current 2.3 A -> 2.8-4.1 A with TSP A2000, fan-fail time to trip 50-100 s -> 3-11 min (kept as a conservative requirement); fan derate levels; the stacked worst case (158 C at the 10 s overload) pending measurement; the single-width option; 2-stack versus 3-stack inductor after the thermocouple test; the Fischer datasheet before BOM freeze.
