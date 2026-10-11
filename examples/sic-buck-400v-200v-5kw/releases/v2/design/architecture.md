**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# V2 electrical and physical architecture

400 V (360-440 V) -> 200 V, 5 kW, 25 A, 50 kHz non-isolated SiC synchronous buck with a
TMS320F28335 control board. This document describes the architecture as built from the
orchestrator baseline [`design_decisions.json`](design_decisions.json) (schema 4), which
supersedes the research records [`research/architecture.json`](research/architecture.json),
[`research/controller_aux_interconnect.json`](research/controller_aux_interconnect.json) and
[`research/standards_safety.json`](research/standards_safety.json) after their verification
reports (`research/verify_*.json`). The option trade-off is in
[`../review/architecture_comparison.md`](../review/architecture_comparison.md); layer stacks,
rules and reservations are in [`pcb_stackup.md`](pcb_stackup.md). V1 (48 V / 1 kW,
`examples/buck-48v-24v-1kw`) is frozen and used only as precedent.

Verification tags: [DS] fetched datasheet, [MP] manufacturer page, [SS] search snippet,
[U] unverified, [AC] analytically checked (no layout, no simulation), [HR] human-review item.
Knowledge items are tagged direct / adapted / not applied / HR. Values without a record name
come from the baseline.

## 1 Partition: Option B

| Board | Outline | Layers / copper | Thickness | Zones and content | Spacing classes |
|---|---|---|---|---|---|
| Power board | 240 x 180 mm (baseline stretch target 230 x 170 mm; judged unreachable in section 9) | 4 x 70 um | 2.0 mm nominal (arithmetic note in the stack-up document) | HV area 240 x 140 mm, ISO_BARRIER 10 mm copper-free on all layers, SELV strip 30 mm along the bottom edge | HV_VIN, HV_SW, HV_PGND, HV_VOUT, DRV_HS, DRV_LS, DESAT_HS, DESAT_LS, SENSE_ISO, PE, CTRL_SELV |
| Control board | 120 x 80 mm | 4 x 35 um | 1.6 mm | F28335, supplies, PWM gating, fault latch and combiner, comparators, JTAG/UART, LEDs | CTRL_SELV only (PE at the bonded mounting hole) |

Every barrier part (3 x UCC14141-Q1, 2 x UCC21710-Q1, 2 x AMC1311B, TMCS1133) sits on the
power board on one straight barrier line, so the control board carries no isolation barrier
and no hazardous voltage. This is the TIDA-010054 decision 10 pattern (REF-TI-TIDA-010054,
adapted: the partition is reused; TI's 300 x 180 mm, parts and "visual only" evidence are not
copied) and it answers the standards record's request that the single barrier live on one
board (KR-ISO-001 direct). Weighted scores A 2.75 / B 4.00 / C 3.10 [AC].

## 2 Functional blocks and nets

### 2.1 Power path (HV area, PGND reference)

J_VIN+ / J_PGND_IN (Wuerth REDCUBE THR M5 74651195, CR-10) -> VIN+ bus -> C_IN 2 x TDK
B32776G8206K000 20 uF 800 V [DS] with the input bleeder 3 x 120 k 2512 and the DC-LINK LIVE
chain (3 x 150 k 1206 + LED) -> HF tier 10 x TDK CGA9P1X7T2J474M 0.47 uF 630 V 2220 (row 1
within 5 mm, row 2 within 15 mm of the device pins, both sides of the row) -> Q_HS
C4MS025120K drain (tab = VIN+) -> SW -> Q_LS drain (tab = SW); Q_LS source -> PGND. SW ->
L1 custom 2-stack High Flux toroid, 272 uH at 25 A, 319 uH at 0 A [AC, inductor record] ->
TMCS1133 IN+/IN- (0.7 mohm) -> VOUT+ -> C_OUT 2 x B32776G4606K000 60 uF 450 V [DS] with the
output bleeder 2 x 100 k 2512 and LED chain -> J_VOUT+ / J_PGND_OUT. DNP footprints: RC
snubber across Q_LS (2512 + 1812 1 kV), 1 uF film + 0.47 ohm damping leg across the HF tier,
MOV B72220S0381K101 across VIN+/PGND, PGND-to-PE link with 2 x 1 M 500 V and Y2 10 nF pads.
Two further REDCUBE terminals bring the chassis relay K1 contacts to the board; the precharge
PTC sits across them (section 5).

Nets: VIN+ (HV_VIN), VIN_PRE (fuse side of the relay contacts, HV_VIN class), SW (HV_SW),
PGND (HV_PGND; input and output returns are one net), VOUT+ (HV_VOUT).

### 2.2 Driver islands (B.Cu, under the device row)

Two identical islands: UCC21710QDWRQ1 [DS] with its own UCC14141QDWNRQ1 [DS] set to VDD-VEE
19.0 V / COM-VEE 4.0 V (+15 V / -4 V at the gate), R_G(on) 10 ohm, R_G(off) 3.3 ohm, the
REQUIRED Miller-clamp link (<= 15 mm), 10 k gate discharge (KR-GD-007 direct), DESAT network
with a US1M-13-F diode to the drain, rail decoupling between the driver pins and the
gate/Kelvin connection (KR-PCB-002 direct) and a 2-pin V_GS probe loop at R_G (CR-11); values
per the baseline `power_stage.gate_driver`. Nets per island: GATE_x, KS_x (Kelvin source),
VDD_x, COM_x (= KS_x), VEE_x, DESAT_x. The LS Kelvin net stays separate from PGND copper
although both are at PGND potential (KR-PCB-003 direct, hard constraint); DESAT_HS / DESAT_LS
carry the full bus potential when their device is off (KR-ISO-002). References: SW for the HS
island (class DRV_HS), KS_LS for the LS island (DRV_LS). AIN is tied to COM on both drivers,
APWM unconnected (CR-01).

### 2.3 Sensing island (SENSE_ISO, PGND reference)

Third UCC14141-Q1 (CR-12): VDD-VEE 15.0 V, COM-VEE 5.0 V, VEE = PGND, COM = 5V_ISO feeding
both AMC1311BDWVR VDD1 pins (about 20 mA). VIN ladder 4 x 750 k 1206 0.1 % + 10.0 k (full
scale 602 V; 2.392 V at the ADC for 480 V) and VOUT ladder 2 x 750 k + 10.0 k (full scale
302 V), 1 nF across the bottom resistor and 100 pF at IN; AMC1311 GND1 = PGND.
TMCS1133C2AQDVGR (0.33 V + 0.05 V/A; 950 Vrms / 1343 VDC reinforced [DS]; the TI product page
shows 600 Vrms, the datasheet governs, to confirm with TI [HR]) in the inductor-to-output
path. The TIDA-010054 TLV76050-from-the-LS-module pattern (CB-IS-002, adapted then set aside
in CR-12) remains the documented alternative.

### 2.4 Power-board SELV strip (CTRL_SELV, GND_CTRL reference)

Mezzanine socket; three Wuerth 744226S CM chokes, each followed by 3 x 10 uF 25 V 1210 +
100 nF at the UCC14141 VIN pin (KR-IS-002 direct; SKILL-004 adapted); 100 ohm + 100 pF +
10 k at every UCC21710 IN+, IN- and RST/EN pin; OPA2320 difference amplifiers (gain 1.5,
32 kHz) converting the AMC1311 pairs to single-ended VIN_SENSE / VOUT_SENSE (CR-16); a
REF3125 with a 2.32 k / 1.00 k divider giving V_OC = 0.750 V (37.5 A) to the TMCS1133;
relay-coil low-side switch AO3400A with a >= 1 A freewheel diode and the coil terminals
(12V_PROT, K1_COIL_LOW); fan connector (12V_PROT, GND_CTRL, FAN_TACH); 3V3_PWRBOARD
decoupling; SELV test points; four M3 standoff holes.

### 2.5 Control board

J_12V (2-pin 5.08 mm) -> SMBJ15CA [SS] -> TPS26400PWPR eFuse [DS] (UVLO 10.0 / 9.3 V, OVP
14.45 / 13.4 V, R_ILIM 6.04 k -> I_CB about 1.96 A, MODE open = circuit breaker, IMON to
ADCINB0) -> 100 uF -> 12V_PROT -> TPS54302DDCR 5 V -> TPS767D301PWPR 1.9 V and 3.3 V, core
first, supervised by a TPS3808G01 (101 k / 10 k, 4.5 V, CR-18). TMS320F28335PGFA with a
30 MHz oscillator on XCLKIN, 14-pin JTAG, 3.3 V UART and boot straps GPIO84-87; all 176 pins
are mapped in `../components/tms320f28335_pgf_pins.csv`. Logic: SN74LVC2G08 PWM gating with
33 ohm source resistors, SN74LVC1G74DCTR latch (SSOP-8, CR-19), 3 x SN74LV21A combiner with
SN74LV04A inverters for the UVLO and PG polarities (CR-26). Comparators: 2 x TLV1702 with a
second REF3125 (OVP_IN 460 V, OVP_OUT 230 V via 953 ohm / 10.0 k, UVLO 340 / 320 V) and the
OTP comparator at 100 C (32.4 k / 10.0 k from the 3.00 V NTC reference = 0.708 V, ratiometric;
CR-25). Sensing: LM61CIM3 on ADCINA3; J_NTC with a 2.2 k pull-up to the 3.00 V REF3130AIDBZR
reference (CR-26; the earlier "REF3125 buffered" wording was withdrawn - a 2.5 V reference
cannot supply 3.00 V without a gain stage); 1 k + 1 nF at every ADC pin. LEDs; J_ESTOP,
J_RESET, J_BOOT, J_UART, J_JTAG.

## 3 Isolation domains and the barrier line

| Domain | Reference | Potential to PE (assumption A-4) | Members |
|---|---|---|---|
| SELV control (PELV if A-23 is approved) | GND_CTRL = SGND | 0 V, single-point bond | control board, SELV strip, mezzanine, fan, relay coil, NTC lead pair, primary sides of all isolators |
| HV, PGND-referenced | PGND | <= 440 V DC continuous, 480 V for 100 ms (source earthing unknown) | VIN+, SW, PGND, VOUT+, LS driver island, sensing island, DESAT_LS |
| HV, SW-referenced | KS_HS = SW | PGND + 0...440 V swinging at 110-120 V/ns | HS driver island, DESAT_HS |
| PE | heatsink, baseplate, PE stud, standoffs, fan frame, NTC lug | 0 V | - |

Barrier realisation (values from the baseline `standards_and_spacing`):

- HV to SELV, reinforced (440 V DC working, 6 kV impulse basis): 9.0 mm copper gap on every
  layer and a 10 mm ISO_BARRIER keep-out along the full 240 mm between HV area and SELV strip.
  Only the eight barrier parts bridge it, each over a 1.2 mm non-plated slot where its land gap
  g is below 9 mm, the slot extended e >= 3 mm beyond the outer pad edges so that the
  around-the-end path 2 x sqrt((g/2)^2 + e^2) >= 9.0 mm (KR-ISO-001 direct; KR-ISO-004 direct
  with the corrected formula; KR-ISO-002 HR). Working-voltage ratings: UCC21710-Q1 2121 VDC,
  UCC14141-Q1 1414 VDC (certifications "planned" in SLUSF10B, HR), AMC1311B 2120 VDC,
  TMCS1133 1343 VDC, all with > 8 mm package creepage [DS]. The off-board relay K1
  coil-to-contact insulation must be shown reinforced for 440 V DC
  or the coil placed behind protective separation (Omron states 4,500 V impulse, no working-
  voltage class [DS extract]; HR). RECOM R12P2 / Murata MGJ2 modules are basic-insulation parts
  and are excluded from this barrier (CR-12).
- HS island to LS island, functional (440 V DC, 530 V recurring peak): copper-free, 3.0 mm on
  outer and 1.0 mm on inner layers (KR-ISO-001 second clause, direct; named explicitly after
  verification).
- HV to PE, basic (4 kV impulse): 5.0 mm copper to the heatsink outline, clips, standoffs and
  PE stud (3.0 mm absolute minimum); Bergquist Sil-Pad TSP A2000 0.254 mm (6 kVac class) under
  both devices (CR-13; KR-TH-002 direct, the rule carries no distance); Vishay NTCALUG01A103F
  lug with 1500 Vac insulation; the TO-247-4 lead-to-sink air gap and the 2.54 mm pin pitch are
  per-package exceptions for the creepage review (HR).
- Between the boards: no control-board copper above HV copper; air clearance 11.05 mm at zero
  lateral offset, 12.1 mm at 5 mm, 14.9 mm at 10 mm [AC] against the 9.0 mm project rule and
  the 5.5 mm reinforced minimum; the through-air argument at pollution degree 2 is a standards
  review item (HR) and must be re-run once the connector height is confirmed.

## 4 Mezzanine interface

Samtec SSW-125-01-G-D socket on the power-board SELV strip (live SELV pins never exposed, a
bench fixture can plug in) and TSW-125-07-G-D header on the control board; alternative Wuerth
WR-PHD (50-pin orderable code unconfirmed [U]). Ratings: SSW 465 VAC / 655 VDC, 4.7 A per pin
(SSW/TSM pairing) or 6.3 A (SSW+TSW) [MP, Samtec catalogue extract]; mated height 8.51 +
2.54 = 11.05 mm derived from the insulator heights, seating depth unconfirmed [U]. The four
M3 standoffs carry the control board; the contacts carry no mechanical load.

Pin table (baseline `interconnect.pin_assignment`; odd pins row A, even pins row B;
C->P = control to power board):

| Pin | Net | Dir | Type / termination |
|---|---|---|---|
| 1-3 | +12V_PROT | C->P | eFuse output; 1.47 A worst (relay pull-in) / 1.30 A steady cross the connector = 0.49 / 0.43 A per pin [AC] |
| 4-6 | GND_CTRL | - | |
| 7 | RELAY_ON | C->P | GPIO3; 100 ohm to the AO3400A gate, 10 k pull-down at the gate |
| 8 | GND_CTRL | - | |
| 9 | BIAS_EN | C->P | GPIO5 to the three UCC14141 ENA pins; pull-down |
| 10 | GND_CTRL | - | |
| 11 | RESET_N | C->P | GPIO4 to both UCC21710 RST/EN; 100 ohm + 100 pF + 10 k at each pin; the driver-internal 55 k typ pull-down disables the stage when the control board is absent |
| 12-13 | GND_CTRL | - | |
| 14 | PWM_H | C->P | SN74LVC2G08 output via 33 ohm; 100 ohm + 100 pF + 10 k at HS IN+ and LS IN-; GND on all four neighbours |
| 15-16 | GND_CTRL | - | |
| 17 | PWM_L | C->P | as PWM_H, to LS IN+ and HS IN- (KR-GD-009 interlock, direct) |
| 18-19 | GND_CTRL | - | |
| 20 | FLT_H_N | P->C | UCC21710 open drain, latched; 4.7 k pull-up to 3V3 on the control board |
| 21 | FLT_L_N | P->C | as above |
| 22 | GND_CTRL | - | |
| 23 | RDY_H | P->C | open drain, pull-up on the control board; run permit |
| 24 | RDY_L | P->C | as above |
| 25-26 | GND_CTRL | - | |
| 27 | OC_N | P->C | TMCS1133 fault flag; to the latched group and directly to TZ2 (GPIO13) |
| 28 | GND_CTRL | - | |
| 29 | FAN_TACH | P->C | fan open-collector tach, pull-up on the control board, GPIO24/ECAP1 |
| 30 | PG_BIAS_S_N | P->C | sensing-module PG (open drain, active low = good), latched group |
| 31 | GND_CTRL | - | |
| 32 | PG_BIAS_H_N | P->C | HS module PG |
| 33 | PG_BIAS_L_N | P->C | LS module PG |
| 34 | GND_CTRL | - | |
| 35 | FAULT_N | C->P | = ARMED from the latch Q; power-board ARMED indicator / test point only (the gating is on the control board) |
| 36 | SPARE_D1 | - | no DSP pin in the baseline; GPIO26 (pin 72) is the natural candidate [added assumption, basis: controller record] |
| 37 | SPARE_D2 | - | GPIO27 (pin 73) |
| 38 | GND_CTRL | - | |
| 39-40 | +3V3_PWRBOARD | C->P | driver VCC, AMC1311 VDD2, TMCS1133 VS, OPA2320, REF3125: about 40 mA [AC] |
| 41-42 | GND_CTRL | - | analogue return |
| 43 | ISENSE | P->C | 0-3 V to ADCINA1 through 1 k + 1 nF |
| 44 | GND_CTRL | - | |
| 45 | ISENSE_REF | P->C | TMCS1133 VREF output to ADCINA4 |
| 46 | GND_CTRL | - | |
| 47 | VIN_SENSE | P->C | OPA2320 output to ADCINA0 |
| 48 | GND_CTRL | - | |
| 49 | VOUT_SENSE | P->C | OPA2320 output to ADCINB1 |
| 50 | GND_CTRL | - | |

24 ground pins (count verified), 3 x 12 V, 2 x 3V3, 17 digital, 4 analogue. Signalling rules:

1. Buffered single-ended logic only. Every receiving pin on either board has 100 ohm +
   100 pF (tau 13 ns, 10-90 % rise 29 ns, below the 28-60 ns UCC21710 deglitch and far below
   the 300 ns dead time [AC]) and a defined pull resistor. This applies KR-GD-008 by
   adaptation: its exclusion reads "short on-board links"; the 11 mm stack plus <= 80 mm of
   strip trace is treated as one, supported by TIDA-010054's buffered SN74LVC126A control-card
   link. Assumption A-21 and the gate-driver record required CB-GD-003 RS-422 for separated
   boards, so this is a recorded conflict (HR); RS-422 becomes mandatory if a cable > 150 mm is
   ever used (threshold is an agent assumption). KR-GD-008 verification is by measurement
   (common-mode injection, open-connector test) and belongs in the test plan.
2. Fail-safe with the control board removed: PWM and RST/EN fall to 0 V through the 10 k and
   the internal 28.5-113 k pull-downs, BIAS_EN low disables the bias modules, RELAY_ON low
   releases the relay.
3. No barrier-crossing net exists on the connector; every pin is CTRL_SELV (KR-ISO-001,
   KR-ISO-003 direct).
4. Analogue group at the far end behind the 3V3 pair, each pin flanked by GND; no analogue
   trace parallel to a PWM trace for more than 10 mm; 1 k + 1 nF at the ADC pins (PE-PCB-005 /
   PE-PCB-007 direct, evidence human review).
5. Defined pull resistors on every GPIO0-11 driven net because the F28335 has no reset
   pull-ups [DS]: 10 k pull-downs on PWM_H, PWM_L and ARM at the gate/latch inputs; pull-ups on
   DSP_TRIP_N and ESTOP_N.

## 5 Power path: fuse, precharge, relay

Fuse: Littelfuse KLKD025.T 25 A 600 V DC fast-acting midget in a 10 x 38 mm holder on the
input lead (off-board, CR-15): 57 % loading at 360 V / 25 A, 70 % at the 320 V stop corner
with 27.5 A [AC]; interrupting 50 kA at 600 VDC [MP]; melting I2t not obtained [U]. With a
<= 20 A current-limited source the fuse never opens; protection then rests on the source
limit, the OC/UVLO logic and the 4.3 J stored at 440 V. The fuse never protects the SiC
devices (KR-PR-001 direct: a 200 A / 2 us event is 0.08 A2s).

Precharge: TDK B59xxx PTC on-board across the two relay-contact terminals (to be re-selected:
R25 100-150 ohm, Vmax >= 480 V DC, Vlink >= 620 V DC; the quoted B59773C0120A070 code does not
carry these parameters, CR-19 [U]); tau 5.8 ms (4.4-7.3), t99 27 ms (20-34), 4.7-5.6 J
absorbed, PTC rise 2.7 K [AC]. Bypass relay Omron G9EA-1 DC12, chassis-mounted (60 A carry,
400 V maximum switching voltage, coil 28.8 ohm: 0.375 / 0.417 / 0.458 A at 10.8 / 12 /
13.2 V [DS]). Firmware closes it when V_bus > 340 V and dV/dt < 2 V per 10 ms (500 ms timeout
-> PRECHARGE_FAIL), holds the coil by PWM at 50-60 % after pull-in (REQUIRED for the 12 V
budget) and never opens it under load: open >= 10 ms after PWM stop and only after the source
is off. Relay state is inferred from VIN_SENSE (no auxiliary contact). The coil switch
(AO3400A, R_DS(on) 48 mohm max at 2.5 V [DS]) and the >= 1 A freewheel diode sit on the SELV
strip.

12 V budget at 10.8 V (CR-02): gate bias 0.40 A + sensing bias 0.15 A + control board 0.29 A
+ relay 0.42 A pull-in (0.25 A PWM hold) + fan 0.50 A maximum = 1.76 A pull-in / 1.59 A
steady against I_CB about 1.96 A (1.11x / 1.23x) [AC]; external supply 2.0 A minimum, 2.5 A
recommended; fan upstream of the eFuse is the fallback if the margin proves insufficient.

## 6 Fault architecture

Fast hardware paths that need no firmware: DESAT per switch inside the UCC21710 (trip 3.6 V,
52-85 A, 288 ns external blanking, total response 0.55-1.07 us against a 1.5 us budget;
Wolfspeed publishes no short-circuit withstand time, so KR-PR-001 is closed only by a
destructive test [HR]), the only protection against shoot-through; TMCS1133 OC at 37.5 A
(trip chain 546 ns [AC]) -> OC_N -> TZ2 directly and into the latched group.

LATCHED group, 13 active-low inputs AND-combined by 3 x SN74LV21A (tpd 12 ns max at 3.3 V
[DS]; CR-26) into CLR_N of the SN74LVC1G74 (D = 1, CLK = ARM on GPIO2): FLT_H_N, FLT_L_N, OC_N,
OVP_IN_N (460 V), OVP_OUT_N (230 V), OTP_N (100 C), FLT_12V_N, XRS_N, ESTOP_N, DSP_TRIP_N,
PG_BIAS_H_N, PG_BIAS_L_N, PG_BIAS_S_N. Any one clears Q = ARMED = FAULT_N asynchronously;
ARMED drives TZ1 (GPIO12, one-shot) and the SN74LVC2G08 PWM gates and returns high only on a
new ARM edge with every source released (KR-PR-002 direct). Worst-case fault-to-gate-off
through logic, mezzanine RC and driver is about 234 ns plus the source delay [AC].

RUN-PERMIT group, not latched, auto-restart with soft start: UVLO_N (340 V start / 320 V
stop), RDY_H, RDY_L, ARMED -> PWM enable (PWM AND ARMED AND RUN_PERMIT). Gate count [AC, this
document]: the 13 latched inputs consume four 4-input gates (three first-stage gates plus one
second-stage gate taking PG_BIAS_S_N and the three first-stage outputs); the run-permit AND
needs a fifth, so three SN74LV21A packages are used, plus SN74LV04A inverters for the UVLO and
PG polarities - the schema 4 baseline (CR-26) now lists both, matching `component_selection.md`
and the control-board schematic (the earlier "2 x SN74LV21A" text is withdrawn).

Restart policy: operator reset only after a DESAT/OC fault (one attempt maximum); UVLO
auto-restart with soft start; OTP auto-restart after cool-down optional. RST/EN low >= 1 us
clears a driver fault. The heatsink NTC is cooling supervision, not junction protection
(KR-TH-003 HR): 80 C derate and overload inhibit / 90 C firmware trip / 100 C hardware
comparator (0.708 V) are proposals (CR-25 lowered the earlier 90 / 100 / 110 C ladder, whose
hardware trip mapped to T_J 176-178 C); T_J,HS is about T_NTC + 50-66 K at full load (1.4 K/W
pad; up to 66 K with maximum-R parts at the overload corner), so a 100 C sink means T_J,HS
150-166 C - below the 175 C absolute maximum, above the 150 C design limit only at the max-R
overload corner; a firmware T_J estimator is recommended - a KR-TH-003 review item
([`thermal_analysis.md`](thermal_analysis.md) section 6).

## 7 Grounding, PE and the PELV deviation

GND_CTRL is one net on the control board (analogue and digital together, placement-controlled
returns, no splits under ADC or PWM tracks, V1 practice reused; PE-PCB-007 / PE-PCB-008
direct, evidence human review) and continues through the 24 mezzanine ground pins to the
SELV strip. It is bonded to PE at exactly one point, a defined control-board mounting hole or
link (A-23). This makes the control domain PELV rather than SELV and is a PROPOSED DEVIATION
from the SELV seed that the human reviewer must approve: consequences are a ground loop
through any earthed JTAG probe or PC and EMI return paths through the baseplate; benefits are
a defined potential for the PE-bonded heatsink so that the NTC lug can be read directly
(CR-01; the CB-PR-002 route through the LS driver AIN is adapted-then-rejected for this
grounding scheme and stays a fallback) and safe earthed debuggers. PGND is NOT hard-bonded:
footprints for a configurable link, 2 x 1 M 500 V reference resistors and optional Y2 10 nF
pads at the HV terminals, all DNP until the source earthing is defined (A-4); the Y2
touch-current estimate 0.85-1.8 mA at 50 kHz excludes mains-frequency ripple of a
rectifier-derived bus [AC, HR]. PE: M4 stud bonded to heatsink and baseplate, PE conductor
cross-section >= supply conductor, bonding resistance <= 0.1 ohm, HV copper >= 5.0 mm from
all PE metal; labels per the stack-up document.

## 8 Firmware boundary

Hardware acts alone: DESAT, OC trip, latch and PWM gating, run permits, eFuse circuit
breaker, driver VDD UVLO, relay release on loss of 12 V, fail-safe pull-downs. Firmware
(contract only; no firmware is delivered in this task) owns: the start-up sequence (12 V ramp
-> rails -> XRS release -> safe GPIO states -> self-test with V12V_MON >= 10.8 V -> BIAS_EN ->
RDY and PG within 50 ms -> RESET_N pulse -> precharge criterion -> RELAY_ON -> 100 ms ->
340-460 V check -> ARM edge -> soft start); ePWM1 up-down count, TBCLK 150 MHz, TBPRD 1500,
6.667 ns tick, dead band 45 ticks = 300 ns at bring-up (effective >= 265 ns after skew
erosion, target 250 ns, bounds 150-400 ns, CR-07), duty ceiling 0.85 initially, ADC SOC at
CTR = ZERO; an inner current loop with the outer voltage loop at 2.0-2.5 kHz; software limits
ahead of the hardware trips (27.5 A for 10 s; input current 15.6 A below 360 V, CR-20);
relay PWM hold; FAN_TACH stall derating within 2 s; OTP 80 / 90 C (derate / trip, CR-25); fault logging and the
one-retry rule. ADC map: VIN_SENSE A0, ISENSE A1, TEMP_HS_NTC A2, TEMP_CTRL A3, ISENSE_REF
A4, I12V_MON B0, VOUT_SENSE B1, V12V_MON B3.

## 9 Mechanical concept and floor-plan check

Open frame on a PE-bonded aluminium baseplate (A-24: <= 300 x 250 x 80 mm). Power board on
6 x M4 x 15 mm standoffs, bottom-side parts <= 10 mm; control board stacked 11 mm above the
SELV strip, overhanging the board edge by about 40 mm, on 4 x M3 standoffs; heights 15 + 2 +
50 = 67 mm (sink; 72 mm envelope with a 5 mm allowance for clips and fan housing, CR-26; below
the 80 mm limit), 65 mm (inductor), 62 mm
(films), 38.6 mm (control stack) [AC]; mass about 1.9 kg [U, estimate]. Heatsink Fischer LAM 5 D K 100 12 (about 100 x 100 mm plan, 50 mm high,
integrated 12 V fan, 0.30 K/W distributor figure [SS]; CR-06, CR-13) over the device row,
both TO-247-4 vertical against one face at 28 mm pitch, leads trimmed short; reservation
175 x 110 mm including fan, intake and exhaust corridors (corridors may hold parts <= 15 mm
tall, CR-26); PE-bonded; HV copper keep-out >= 5 mm; clip-to-lead >= 3 mm. A fan failure drives T_J
above 175 C in steady state, so OTP is mandatory (thermal record). Inductor (keep-out circle
75 mm, 48 mm high, cup on 4 x M4 at 60 x 60 mm)
in the fan stream (CR-14, forced air mandatory), >= 20 mm from the sink; film capacitors
>= 20 mm from the sink, >= 15 mm from the inductor and outside the exhaust (baseline
placement rule 7 and CR-23; the older 10 mm figure in placement rule 4 is the weaker statement
and is superseded).

Floor-plan feasibility [AC, this document, no layout run]: with the baseline sink reservation
the exclusive HV zone sum is about 33,400 mm2 (sink 115 x 110 mm without corridors 12,650;
inductor 6,375; films 5,160; HF tier 560; eight barrier parts 2,000; driver islands 1,050;
terminals, relay/PTC, bleeders, snubber, NTC, PE and six standoff keep-outs about 5,600)
against 33,600 mm2 available, i.e. 99 %, and 119 % if the two 30 mm corridors stay empty. The
230 x 170 mm stretch outline is therefore out of reach and the 240 x 180 mm target is at
risk; in addition, C_IN cannot be within the capacitor record's 30-40 mm of the half bridge
while the sink body occupies the space behind the device row. Options for the orchestrator:
grow the HV depth (HV 240 x 170 -> outline 240 x 210, 50,400 mm2, inside A-24 and below V1's
66,000 mm2), relax the C_IN distance on the strength of the HF tier, or place the intake
corridor off the board edge. 240 x 180 mm remains the baseline acceptance limit until the
layout agent proves or disproves it.

## Verification status and open items

- Analytically checked: weighted scores and sensitivities, areas, heights, volumes, zone
  sums, mezzanine currents and pin count, RC time constants, fault latency, combiner gate
  count, slot path, inter-board air gaps, 12 V budget margins, fuse loading.
- Fetched datasheet: UCC21710-Q1, UCC14141-Q1, AMC1311, TMCS1133, TPS2640, TMS320F28335,
  C4MS025120K, TDK B32776 films, Omron G9EA-1, AO3400A, SN74LV21A, Wuerth WR-PHD series.
- Manufacturer page / search snippet: Samtec catalogue values, Fischer LAM 5 D K 100 12,
  KLKD025 ratings, SMBJ15CA, PTC family parameters.
- Unverified: mezzanine seating depth (11.05 mm derived), heatsink datasheet (R_th, fan
  current, mass, mounting), PTC part number, fuse melting I2t, mass estimate, WR-PHD 50-pin
  code, UCC14141-Q1 certificate status.
- Simulated: nothing in this document.
- Human review: SGND-to-PE bond (A-23, PELV); PGND/PE strategy and Y2 use; 9.0 mm all-layer
  rule versus the 5.5 mm standard minimum; stacked-board through-air clearance; relay
  coil-to-contact insulation; pad rating versus impulse basis; TO-247-4 lead-to-sink gap and
  pin-field exception; single-ended mezzanine versus A-21 RS-422; UCC14141 COM-VEE 5 V
  sensing configuration and RLIM; KR-PR-001 closure by destructive test; fifth combiner gate;
  SPARE_D1 pin; 3.00 V NTC reference stage; floor-plan feasibility of 240 x 180 mm.
