"""Power-board electrical model of the V2 SiC synchronous buck (board = "power").

AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED

400 V (360-440 V) -> 200 V, 5 kW, 25 A, 50 kHz non-isolated SiC synchronous buck; Wolfspeed
C4MS025120K half bridge, UCC21710-Q1 isolated drivers, UCC14141-Q1 isolated bias modules,
TMCS1133 Hall current sensor, AMC1311 isolated voltage sensing, SELV strip with the 2 x 25
mezzanine socket for the TMS320F28335 control board.  This module is the electrical source
of truth for the power board: an explicit pad -> net mapping with KiCad pin types for every
part, the custom footprints that have no KiCad library equivalent, and the provenance of
every pinout.  No CAD, no implicit wiring.  It writes design/circuit_power.json and
components/bom_power.csv.  The companion control-board model lives in
sic_buck_control_model.py; both import sic_buck_common (never modified here).

Single source of truth: examples/sic-buck-400v-200v-5kw/design/design_decisions.json
(schema 2).  Precedence applied: (1) design_decisions.json; (2) where silent, the research
record design/research/<area>.json after the required_changes of its two verify_*.json
reports; (3) added assumptions are labelled below with their basis.

NETS (all names are KiCad global labels; HV = hazardous, > 60 V DC against PGND or floating)
  HV power path (classes HV_VIN / HV_SW / HV_VOUT / HV_PGND of sic_buck_common):
    VIN_RAW   input terminal J1 (+), relay-contact terminal J5 (RLY_A), PTC RT1 side A.
    VIN       DC link after relay/PTC: J6 (RLY_B), Q1 drain, 10 x C_HF, C_IN1/2, MOV (DNP),
              bleeders, indicator string, damping leg (DNP), VIN ladder top, HS DESAT diode
              cathode, Y2 to PE (DNP).
    SW        Q1 source (power lead) = Q2 drain, L1 pin 1, LS DESAT diode cathode, snubber (DNP).
    VOUT_L    L1 pin 2 -> TMCS1133 IN+ bar (pad 1).
    VOUT      TMCS1133 IN- bar (pad 2) -> C_OUT1/2, output terminal J3, output bleeder and
              indicator, VOUT ladder top.
    PGND      common negative rail: J2/J4, Q2 source (power lead), capacitor returns, bleeder
              and LED returns, ladder bottoms, AMC1311 GND1/SHTDN, sensing bias VEE, PE
              network, snubber and damping returns.
    HV intermediate nodes (NOT covered by sic_buck_common.NET_CLASS_PATTERNS; the layout
    must give them HV functional spacing, see HV_INTERMEDIATE_NETS): BLD_IN_1, BLD_IN_2
    (input bleeder chain, 147-320 V), IND_IN_1..3 (indicator string), BLD_OUT_1, IND_OUT_1,
    IND_OUT_2, SNUB_MID (DNP snubber), DAMP_MID (DNP damping leg), PE_REF_MID (between the
    two 1 M PGND-PE resistors), VIN_DIV_T1..T3 and VOUT_DIV_T1 (ladder taps, 120 V steps).
  Driver islands (DRV_HS / DRV_LS; x = H or L):
    G_x       gate lead of Qx: R_ON, R_OFF, Miller-clamp 0 ohm link, R_GS, probe TP, DNP gate-
              Kelvin R.
    KS_x      Kelvin (driver) source lead: driver COM and AIN, bias COM (through RLIM
              resistor), decoupling, DESAT R3 / C_BL / Schottky, R_GS, probe TP.  Never joined
              to SW or PGND on the PCB (KR-PCB-003); checked by the unit test.
    VDD_x     +15 V above KS_x (UCC14141 VDD -> UCC21710 VDD, 2 x 4.7 uF + 100 nF).
    VEE_x     -4 V below KS_x (UCC14141 VEE -> UCC21710 VEE, 4.7 uF + 100 nF).
    DESAT_x_A node A of the DESAT network (VDD -> 2.2 k -> A -> US1M anode; cathode on the drain).
    DESAT_x_OC driver OC pin node (A -> 4.99 k -> OC; 1.00 k + 680 pF C0G to KS_x; BAT42W DNP).
    HS_OUTH / HS_OUTL / HS_CLMP (and LS_*)  driver output pins before R_ON / R_OFF / 0 ohm.
    HS_GK / LS_GK  mid node of the DNP gate-Kelvin RC.
    HS_FB_VDD, HS_FB_VEE, HS_RLIM (and LS_*)  UCC14141 feedback dividers and RLIM resistor.
  Bias primary side (SELV, after the CM choke; x = H, L or S):
    12V_BIAS_x  12 V after the WE-SL2 choke winding 1-4 -> UCC14141 VIN (3 x 10 uF + 100 nF).
    GNDP_x      primary ground after the choke winding 2-3 -> UCC14141 GNDP.  Joined to
                GND_CTRL only through the choke so that the choke is a common-mode impedance
                for the barrier displacement current (KR-IS-002); see added assumption A-P3.
  Sensing island (SENSE_ISO):
    5V_ISO    COM output of the sensing bias module U5 (COM-VEE 5.0 V) -> AMC1311 VDD1 x2.
    ISO_15V   VDD output of U5 (VDD-VEE 15 V, capacitor load only).
    VIN_DIV, VOUT_DIV   AMC1311 inputs (ladder bottoms 10.0 k with 1 nF + 100 pF to PGND).
    ISO_FB_VDD, ISO_FB_VEE, ISO_RLIM   U5 feedback dividers and RLIM resistor (PGND referenced).
  SELV (CTRL_SELV):
    12V_PROT, 3V3, GND_CTRL  from the control board over the mezzanine (PWR_FLAG nets here).
    PWM_H, PWM_L             raw PWM from the mezzanine; PWM_H_F, PWM_L_F after 100 ohm /
                             100 pF / 10 k (driver IN+ of the own channel, IN- of the other).
    RESET_N -> RESET_N_F     driver RST/EN (both) after 100 ohm / 100 pF / 10 k pull-down.
    BIAS_EN -> BIAS_EN_F     UCC14141 ENA (all three) after 100 ohm / 100 pF / 10 k pull-down.
    RELAY_ON -> RLY_G        AO3400A gate after 100 ohm, 10 k pull-down at the gate.
    FLT_H_N, FLT_L_N, RDY_H, RDY_L   driver open-drain outputs, 4.7 k pull-ups to 3V3.
    OC_N                     TMCS1133 OC (open drain), 10 k pull-up to 3V3.
    PG_BIAS_H_N, PG_BIAS_L_N, PG_BIAS_S_N   UCC14141 PG (open drain, active-low good), 10 k
                             pull-ups to 3V3.
    FAN_TACH                 fan header pin 3, 10 k pull-up to 3V3.
    FAULT_N, SPARE_D1, SPARE_D2   mezzanine lines terminated on test points only.
    ISENSE                   TMCS1133 VOUT (0.33 V + 50 mV/A).
    ISENSE_REF               0.1 x 3V3 ratiometric zero-current reference (added, A-P1).
    VIN_SENSE, VOUT_SENSE    OPA2320 difference-amplifier outputs (gain 1.5).
    VIN_OUTP/VIN_OUTN, VOUT_OUTP/VOUT_OUTN   AMC1311 differential outputs.
    VIN_AMP_P/VIN_AMP_N, VOUT_AMP_P/VOUT_AMP_N   op-amp summing nodes.
    REF2V5_PB                REF3125 2.5 V; VOC_SET = 0.750 V via 2.32 k / 1.00 k -> TMCS1133 VOC.
    K1_LOW                   relay-coil low side (AO3400A drain, SS14 anode).
    PE                       M4 PE pad; PGND-PE 0 ohm link (DNP), 2 x 1 M in series, Y2 (DNP).

PAGES: see PAGES.  PWR_FLAG nets: see FLAG_NETS (the connectivity analysis of
project_schematic reports no other undriven power net; checked by the unit test).

PINOUT VERIFICATION (details in PINOUT_SOURCES; levels: fetched-datasheet / manufacturer-
page / search-snippet / unverified / library-convention):
  UCC21710QDWRQ1  fetched-datasheet (SLUSDH8D, Jan 2019 rev. Jun 2024, pin table).
  UCC14141QDWNRQ1 fetched-datasheet (SLUSF10B, Feb 2023 rev. Jun 2023, Table 6-1 / Figure 6-1,
                  package drawing DWN0036A 4225960/A read from the rendered page).
  AMC1311BDWVR    fetched-datasheet (SBAS786C, Dec 2017 rev. Jun 2022; DWV0008A 4218796/A).
  TMCS1133C2AQDVGR fetched-datasheet (SBOSAG0E, Oct 2023 rev. May 2026; DVG0010A 4226847/C).
                  The package is a 10-pin SOIC with ONE wide (4.12-4.32 mm) lead per current
                  input (pins 1 = IN+, 2 = IN-), not a 16-pin with bussed pins; the footprint
                  follows the datasheet, not the task wording.
  OPA2320AIDGKR   fetched-datasheet (SBOS513F, Aug 2010 rev. Dec 2016).
  REF3125AIDBZR   fetched-datasheet (REF31 family SBVS046E, Dec 2003 rev. Apr 2026).
  AO3400A         fetched-datasheet (AOS Rev 3.1, July 2023, SOT-23 top view 1 G, 2 S, 3 D).
  C4MS025120K     fetched-datasheet (Rev. 2, Dec 2025; package drawing PRD 05966 rev 02):
                  lead 1 DRAIN, 2 SOURCE, 3 DRIVER SOURCE, 4 GATE, 5 (tab) DRAIN.
  744226S         fetched-datasheet (WE rev. 009.003, 2023-04-12): WE-SL2 9.2 x 6.0 x 5.0 mm,
                  windings 1-4 and 2-3; KiCad Inductor_SMD:L_CommonMode_Wuerth_WE-SL2 pads
                  (2.0 x 1.2 at +/-3.75 / +/-1.27) equal the WE land pattern.  The WE-SL5
                  footprint named in the task does NOT fit this part.
  Diodes (US1M-13-F, BAT42W-V, SS14) and the LED: library-convention (KiCad Diode_SMD /
                  LED_SMD pad 1 = cathode); part datasheets not fetched (search-snippet /
                  unverified per the research records).
  Connectors: Samtec SSW-125-01-G-D (distributor-level), Phoenix MKDS 1,5/2-5,08 order code
                  1715721 (unverified), Wuerth 74651195 (V1, fetched in V1).

TO-247-4 PAD MAPPING - PROMINENT ASSUMPTION: the KiCad Package_TO_SOT_THT:TO-247-4_Vertical
pads 1-4 are taken as the physical leads 1-4 in the left-to-right order of the Wolfspeed
front-view drawing (PRD 05966).  Hence pad 1 = DRAIN, pad 2 = SOURCE (power), pad 3 = DRIVER
(Kelvin) SOURCE, pad 4 = GATE.  This differs from the generic G-D-S-KS order assumed by the
smoke pipeline.  Human review must confirm the footprint's pad-1 side against the device's
pin-1 side before fabrication; a wrong order would put 400 V on the gate network.

CUSTOM FOOTPRINTS (AIPE library, see CUSTOM_FOOTPRINTS):
  C_Film_41.5x28x37_P37.5x10.2      TDK B32776G8206K000 20 uF 800 V, 4 leads 1,1,2,2.
  C_Film_41.5x30x45_P37.5x20.3      TDK B32776G4606K000 60 uF 450 V, 4 leads 1,1,2,2.
  L_Toroid_HF58x2_D69_H48_P25.4     custom choke, 2 x 3.2 mm PTH / 6.0 mm pads on 25.4 mm,
                                    4 x 4.3 mm NPTH on 60 x 60 mm (cup lugs beyond the 69 mm
                                    winding envelope).
  HS_LAM5DK_100x100_H50             Fischer LAM 5 D K 100 12 envelope 100.5 x 100 x 50 mm,
                                    4 x 3.2 mm NPTH at the corners (PLACEHOLDER: the Fischer
                                    drawing was not accessible; distributor dimensions).
  UCC14141_DWN0036A_Slot            36-pin SSOP 0.65 mm, pads 1.85 x 0.45 on a 9.95 mm span,
                                    1.2 x 17.5 mm NPTH isolation slot under the body.
  AMC1311_DWV0008A_Slot             8-pin wide SOIC 1.27 mm, pads 1.8 x 0.6 on 10.9 mm,
                                    1.2 x 10.4 mm slot.
  TMCS1133_DVG0010A_HV_Slot         TI HV land-pattern option (pad centre span 9.75 mm), input
                                    bar pads widened outward to 3.0 x 4.41 mm for 25 A, eight
                                    2.0 x 0.6 mm SELV pads, 1.2 x 15.5 mm slot.
  PTC_Disc_D20_P10_Envelope         leaded PTC disc, 10 mm pitch, 1.3 mm drill, 20 mm body.
  The slots implement the baseline rule (standards_and_spacing.slots: 1.2 mm non-plated slot
  extending >= 3 mm beyond the outermost pad edges) for the three custom barrier parts; the
  UCC21710_DW0016A_Slot             KiCad SOIC-16W_7.5x10.3mm_P1.27mm land pattern with a 1.2 x 16.6 mm slot.

ADDED ASSUMPTIONS (not in the baseline; labelled in the part notes):
  A-P1  ISENSE_REF is generated as 0.1 x 3V3 (9.09 k / 1.00 k 0.1 %, 100 nF) because the
        TMCS1133 has no VREF pin (SBOSAG0E pin table); the C2A zero-current output is 0.1 x VS.
  A-P2  Sensing module VDD-VEE divider top 80.6 k (14.94 V) - the baseline states 15 V but no
        resistor; nearest E96 value, VDD is unloaded.
  A-P3  Each bias module's primary ground is GNDP_x after the choke (not GND_CTRL directly):
        a CM choke must be in both lines to act on the i_CM pulses (KR-IS-002).
  A-P4  100 nF VDD-VEE at every UCC14141 (SLUSF10B pin table requirement, baseline silent).
  A-P5  10 k pull-ups on PG_BIAS_x_N (open-drain PG outputs; the fault combiner needs a level).
  A-P6  RESET_N and BIAS_EN get the baseline's generic receiving-pin network (100 ohm / 100 pF
        / 10 k pull-down, interconnect.signalling) - fail-safe off when the mezzanine is open.
  A-P7  Snubber placeholders 10 ohm 2512 / 1 nF 1 kV 1812 (DNP) - values from double-pulse test.
  A-P8  Op-amp +input leg gets the same 330 pF as the feedback leg (CMRR balance).
  A-P9  Test points on SPARE_D1 / SPARE_D2 so the spare mezzanine lines are terminated.
  A-P10 ALERT of the TMCS1133 tied to GND_CTRL per the datasheet (unused); typed passive so
        ERC accepts the tie.  TMCS1133 VS decoupling 100 nF + 1 uF.
  A-P11 PGND-PE reference resistors wired as 2 x 1 M in series (<= 240 V per element).

KNOWLEDGE CITATIONS (how they entered this model): SKILL-001 applied (driver stage per
procedure); SKILL-002 adapted (layout hand-off only); SKILL-004 applied (bias modules);
SKILL-005 applied (sensing chain); SKILL-003 not applied here (capacitor sizing is upstream);
SKILL-006 not applied (thermal upstream); KR-GD-002 applied (split R_ON/R_OFF); KR-GD-003
applied (Miller clamp required); KR-GD-005 applied (-4 V rail); KR-GD-007 applied (R_GS 10 k);
KR-GD-008 adapted (RC + pull-down at mezzanine receiving pins); KR-GD-009 applied (IN+/IN-
cross wiring); KR-GD-010 human-review (DNP gate-Kelvin RC); KR-IS-002 applied (CM choke, A-P3);
KR-IS-004 human-review (dedicated sensing module, CR-12); KR-PCB-002 applied (decoupling
between driver pins and gate/Kelvin); KR-PCB-003 applied (Kelvin nets distinct, tested);
KR-ISO-001/003/004 adapted (classes and slots); KR-SN-001/002/005 applied (sensor choices and
OC path); KR-PR-002 applied (FLT/RDY/RST interface); KR-TH-003 not applied (NTC is on the
control board, CR-01); CB-GD-001 adapted (DESAT values re-derived upstream); CB-PR-002
adapted-then-rejected (AIN tied to COM, CR-01); CB-SN-001/004 adapted (ladders, OC divider);
CB-IS-002 adapted (bias configuration); CMP-UCC21710-Q1, CMP-UCC14141-Q1, CMP-AMC1311,
CMP-TMCS1133 applied (part records re-verified against fetched datasheets here);
REF-TI-TIDA-010054 adapted (structure only); REF-WS-CGD1700HB2M-UNA adapted (choke, DESAT
topology, probe loop); PE-PCB-001/005/006/007/008 adapted into placement notes.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from automation.kicad_tools import project_footprints as pf
from automation.kicad_tools.native_schematic import parse
from automation.kicad_tools.sic_buck_common import (BANNER, BASIS, EXAMPLE, PASSIVE_CAPS, POWER_NAME, Circuit,
                                                    mezzanine_net, pin_defs)

BOARD = "power"
NAME = POWER_NAME
TITLE = f"AIPE V2 SiC buck power board - {BASIS}"
COMMENT = BANNER
CIRCUIT_JSON = EXAMPLE / "design/circuit_power.json"
BOM_CSV = EXAMPLE / "components/bom_power.csv"

PAGES = {
    "01_power_stage": "Input, half bridge, inductor, output, bleeders",
    "02_gate_driver_hs": "High-side isolated gate driver and bias",
    "03_gate_driver_ls": "Low-side isolated gate driver and bias",
    "04_sensing_island": "Isolated voltage sensing island and its bias module",
    "05_selv_strip": "SELV strip: mezzanine, conditioning, relay and fan interface",
    "06_mechanical": "Heatsink envelope, terminals, mounting, test points",
}
FLAG_PAGE = "05_selv_strip"

# PWR_FLAG nets: supply provenance for ERC only.  Power-source nets that have a real power_out pin
# (VDD_x, VEE_x, ISO_15V, REF2V5_PB) must NOT be flagged (power_out vs PWR_FLAG is an ERC error).
FLAG_NETS = ["VIN_RAW", "VIN", "PGND", "12V_PROT", "3V3", "GND_CTRL", "KS_H", "KS_L", "5V_ISO",
             "12V_BIAS_H", "12V_BIAS_L", "12V_BIAS_S", "GNDP_H", "GNDP_L", "GNDP_S"]

# HV-potential nets that no pattern of sic_buck_common.NET_CLASS_PATTERNS covers; the layout must
# apply HV functional spacing (3.0 mm outer / 1.0 mm inner, standards_and_spacing.kicad_rules_mm).
HV_INTERMEDIATE_NETS = ["BLD_IN_1", "BLD_IN_2", "IND_IN_1", "IND_IN_2", "IND_IN_3", "BLD_OUT_1", "IND_OUT_1",
                        "IND_OUT_2", "SNUB_MID", "DAMP_MID", "PE_REF_MID", "VIN_DIV_T1", "VIN_DIV_T2",
                        "VIN_DIV_T3", "VOUT_DIV_T1"]

TI = "Texas Instruments"
TI_DS = "https://www.ti.com/lit/ds/symlink/{}.pdf"
VISHAY_TNPW = "https://www.vishay.com/docs/28773/tnpwe3.pdf"
PANASONIC_ERJP = "https://industry.panasonic.com/global/en/products/control/resistor"

PINOUT_SOURCES = {
    "UCC21710QDWRQ1": dict(level="fetched-datasheet", document="SLUSDH8D (Jan 2019, rev. Jun 2024) Pin Functions, SOIC-16 DW",
                           pins="1 AIN, 2 OC, 3 COM, 4 OUTH, 5 VDD, 6 OUTL, 7 CLMPI, 8 VEE, 9 GND, 10 IN+, 11 IN-, 12 RDY, 13 FLT, 14 RST/EN, 15 VCC, 16 APWM"),
    "UCC14141QDWNRQ1": dict(level="fetched-datasheet", document="SLUSF10B (Feb 2023, rev. Jun 2023) Table 6-1 / Figure 6-1; DWN0036A drawing 4225960/A (rendered page)",
                            pins="GNDP 1,2,5,8-18; PG 3; ENA 4; VIN 6,7; VEE 19-27,30,31,36; VDD 28,29; RLIM 32; FBVEE 33; FBVDD 34; VEEA 35; pitch 0.65 mm, body 12.83 x 7.5 mm, pad span 9.95 mm"),
    "AMC1311BDWVR": dict(level="fetched-datasheet", document="SBAS786C (Dec 2017, rev. Jun 2022) Table 6-1; DWV0008A drawing 4218796/A",
                         pins="1 VDD1, 2 IN, 3 SHTDN (active high, tie to GND1), 4 GND1, 5 GND2, 6 OUTN, 7 OUTP, 8 VDD2; pads 1.8 x 0.6 at 1.27 mm, span 10.9 mm, body 5.85 x 7.5 mm"),
    "TMCS1133C2AQDVGR": dict(level="fetched-datasheet", document="SBOSAG0E (Oct 2023, rev. May 2026) Table 5-1; DVG0010A drawing 4226847/C, HV land-pattern option",
                             pins="1 IN+, 2 IN- (wide leads 4.12-4.32 mm), 3 GND, 4 ALERT, 5 NC, 6 VOUT, 7 OC, 8 VOC, 9 VS, 10 VS; SELV pads 0.6 wide at 1.27 mm, pad centre span 9.75 mm"),
    "OPA2320AIDGKR": dict(level="fetched-datasheet", document="SBOS513F (Aug 2010, rev. Dec 2016) Pin Functions OPA2320, VSSOP DGK",
                          pins="1 OUT A, 2 -IN A, 3 +IN A, 4 V-, 5 +IN B, 6 -IN B, 7 OUT B, 8 V+"),
    "REF3125AIDBZR": dict(level="fetched-datasheet", document="REF31 SBVS046E (Dec 2003, rev. Apr 2026) Table 5-1, DBZ SOT-23",
                          pins="1 IN, 2 OUT, 3 GND; supply bypass >= 0.47 uF recommended, no load capacitor required"),
    "AO3400A": dict(level="fetched-datasheet", document="Alpha and Omega AO3400A Rev 3.1 (July 2023) SOT-23 top view",
                    pins="1 G, 2 S, 3 D; RDS(on) < 48 mohm at VGS 2.5 V"),
    "C4MS025120K": dict(level="fetched-datasheet", document="Wolfspeed C4MS025120K Rev. 2 (Dec 2025); package outline PRD 05966 rev 02 (3/4/24)",
                        pins="lead 1 DRAIN, 2 SOURCE, 3 DRIVER SOURCE, 4 GATE, 5 (tab) DRAIN; KiCad pad order = front-view left-to-right ASSUMED (human review)"),
    "744226S": dict(level="fetched-datasheet", document="Wuerth 744226S rev. 009.003 (2023-04-12), WE-SL2 10 uH 1.6 A",
                    pins="windings 1-4 and 2-3; land pattern 2.0 x 1.2 mm pads at +/-3.75 / +/-1.27 mm = KiCad L_CommonMode_Wuerth_WE-SL2"),
    "US1M-13-F": dict(level="library-convention", document="Diodes Inc US1M product page (search-snippet in the research record); KiCad Diode_SMD:D_SMA pad 1 = cathode", pins="1 K, 2 A"),
    "BAT42W-V": dict(level="library-convention", document="Vishay 85660 not fetched (unverified); KiCad Diode_SMD:D_SOD-123 pad 1 = cathode", pins="1 K, 2 A"),
    "SS14": dict(level="library-convention", document="SMA Schottky 1 A 40 V, datasheet not fetched (unverified); KiCad Diode_SMD:D_SMA pad 1 = cathode", pins="1 K, 2 A"),
    "LTST-C170KRKT": dict(level="library-convention", document="Lite-On 0805 red LED, datasheet not fetched; KiCad LED_SMD pad 1 = cathode", pins="1 K, 2 A"),
    "SSW-125-01-G-D": dict(level="distributor", document="Samtec SSW series page; numbering per KiCad PinSocket_2xNN (odd / even rows, pairs across) - identical convention on the control board",
                           pins="1-50 per design_decisions.json interconnect.pin_assignment"),
    "MKDS 1,5/2-5,08": dict(level="unverified", document="Phoenix Contact order code 1715721 from memory - confirm", pins="1, 2"),
    "74651195": dict(level="fetched-datasheet (V1)", document="Wuerth REDCUBE THR M5, KiCad library footprint, single pad 1", pins="1"),
    "B32776G8206K000 / B32776G4606K000": dict(level="fetched-datasheet", document="TDK B3277* DC-link datasheet (June 2026) via the capacitor research record; pad positions from design_decisions.json capacitors.*.footprint",
                                              pins="4 leads 1,1,2,2 (two per electrode)"),
    "LAM 5 D K 100 12": dict(level="unverified", document="Fischer drawing not accessible; distributor dimensions 100.5 x 100 x 50 mm; corner holes are placeholders", pins="mechanical"),
}

# Capacitors beyond sic_buck_common.PASSIVE_CAPS (real orderable parts; verification per note).
EXTRA_CAPS = {
    "10n/300VAC/Y2": dict(footprint="Capacitor_THT:C_Disc_D12.5mm_W5.0mm_P10.00mm", mpn="VY2103M35Y5US6TV0", maker="Vishay",
                          source="https://www.vishay.com/docs/28534/vy2series.pdf",
                          note="Y2 10 nF 300 VAC disc; ordering suffix unverified; footprint D12.5/P10 approximates the disc"),
}

# Thin-film 0.1 % resistors (Vishay TNPW e3): value -> ordering code.  Format per the TNPW datasheet
# (value code, B = 0.1 %, E = 25 ppm/K); exact suffix availability is unverified.
TNPW_CODES = {"1k": "1K00", "2.32k": "2K32", "9.09k": "9K09", "9.76k": "9K76", "10k": "10K0", "15k": "15K0", "16.2k": "16K2",
              "80.6k": "80K6", "107k": "107K", "750k": "750K"}

FET_PINS = pin_defs("1:D:passive 2:S:passive 3:KS:passive 4:G:input")
DIODE_PINS = pin_defs("1:K:passive 2:A:passive")
UCC21710_PINS = pin_defs("1:AIN:input 2:OC:input 3:COM:power_in 4:OUTH:output 5:VDD:power_in 6:OUTL:output 7:CLMPI:passive "
                         "8:VEE:power_in 9:GND:power_in 10:IN+:input 11:IN-:input 12:RDY:open_collector 13:FLT:open_collector "
                         "14:RST/EN:input 15:VCC:power_in 16:APWM:output")
AMC1311_PINS = pin_defs("1:VDD1:power_in 2:IN:input 3:SHTDN:input 4:GND1:power_in 5:GND2:power_in 6:OUTN:output 7:OUTP:output 8:VDD2:power_in")
TMCS1133_PINS = pin_defs("1:IN+:passive 2:IN-:passive 3:GND:power_in 4:ALERT:passive 5:NC:no_connect 6:VOUT:output "
                         "7:OC:open_collector 8:VOC:input 9:VS:power_in 10:VS:passive")
OPA2320_PINS = pin_defs("1:OUTA:output 2:-INA:input 3:+INA:input 4:V-:power_in 5:+INB:input 6:-INB:input 7:OUTB:output 8:V+:power_in")
REF3125_PINS = pin_defs("1:IN:power_in 2:OUT:power_out 3:GND:power_in")
AO3400A_PINS = pin_defs("1:G:input 2:S:passive 3:D:passive")
CHOKE_PINS = pin_defs("1:W1A:passive 2:W2A:passive 3:W2B:passive 4:W1B:passive")


def ucc14141_pins(vee_type: str = "power_out") -> dict:
    """UCC14141-Q1 DWN pin names/types (SLUSF10B Table 6-1).  Duplicate supply pins are typed passive so that
    one power_in / power_out per rail carries the ERC semantics (KiCad flags power_out-power_out pairs).  `vee_type`
    is "passive" when VEE lands on a rail that already has a PWR_FLAG (the sensing module, VEE = PGND)."""
    names = {1: "GNDP", 2: "GNDP", 3: "PG", 4: "ENA", 5: "GNDP", 6: "VIN", 7: "VIN", 28: "VDD", 29: "VDD", 32: "RLIM",
             33: "FBVEE", 34: "FBVDD", 35: "VEEA"}
    names.update({n: "GNDP" for n in range(8, 19)})
    names.update({n: "VEE" for n in (19, 20, 21, 22, 23, 24, 25, 26, 27, 30, 31, 36)})
    types = {3: "open_collector", 4: "input", 7: "power_in", 8: "power_in", 19: vee_type, 28: "power_out", 32: "output",
             33: "input", 34: "input"}
    return {str(n): dict(name=names[n], type=types.get(n, "passive")) for n in range(1, 37)}


# --- custom footprints ------------------------------------------------------------------------

def _slot_pad(length_mm: float) -> str:
    """Non-plated 1.2 mm isolation slot centred under a barrier package (baseline standards_and_spacing.slots)."""
    return (f'(pad "" np_thru_hole oval (at 0 0) (size 1.2 {pf.num(length_mm)}) (drill oval 1.2 {pf.num(length_mm)}) '
            '(layers "*.Cu" "*.Mask"))')


def _dual_row_pads(per_side: int, pitch: float, x: float, pad_w: float, pad_h: float) -> list[str]:
    """SOIC-style numbering: pins 1..n down the left column (top to bottom), n+1..2n up the right column."""
    y0 = -(per_side - 1) * pitch / 2
    pads = [pf.smd_pad(str(i + 1), -x, y0 + i * pitch, pad_w, pad_h, "roundrect") for i in range(per_side)]
    pads += [pf.smd_pad(str(per_side + i + 1), x, -y0 - i * pitch, pad_w, pad_h, "roundrect") for i in range(per_side)]
    return pads


def _pin1_marks(x_outer: float, y_top: float) -> str:
    """Silkscreen pin-1 tick outside the top-left pad (make_footprint's own silkscreen is off for the ICs)."""
    x0, y = pf.num(-x_outer - 0.6), pf.num(y_top)
    return (f'(fp_line (start {x0} {y}) (end {pf.num(-x_outer - 1.6)} {y}) (stroke (width 0.15) (type default)) (layer "F.SilkS"))')


def tmcs1133_footprint(name="TMCS1133_DVG0010A_HV_Slot"):
    """TI DVG0010A, HV land-pattern option (SBOSAG0E 4226847/C): pads 1/2 = IN+/IN- bars 4.41 mm tall on a 5.08 mm
    pitch, widened outward from TI's 2.0 mm to 3.0 mm for the 25 A copper connection (inner edge kept at x = -3.875
    mm so TI's 8.1 mm HV option clearance is preserved); pads 3-10 = 2.0 x 0.6 mm at 1.27 mm (pin 3 bottom right,
    pin 10 top right); body 7.5 x 10.3 mm, 2.65 mm high; 1.2 x 15.5 mm isolation slot."""
    bars = [pf.smd_pad("1", -5.375, -2.54, 3.0, 4.41), pf.smd_pad("2", -5.375, 2.54, 3.0, 4.41)]
    selv = [pf.smd_pad(str(3 + i), 4.875, 4.445 - i * 1.27, 2.0, 0.6, "roundrect") for i in range(8)]
    pads = bars + selv + [_slot_pad(15.5)]
    text = pf.make_footprint(name, "\n  ".join(pads), 13.75, 15.5,
                             "TMCS1133 DVG0010A (10-pin SOIC, two 4.3 mm wide current leads) - TI HV land pattern option "
                             "(pad centre span 9.75 mm, 8.1 mm clearance), bar pads widened outward to 3.0 x 4.41 mm for 25 A, "
                             "1.2 x 15.5 mm NPTH isolation slot (>= 3 mm beyond the pads); F.Fab = pad/slot envelope, real body "
                             "7.5 x 10.3 x 2.65 mm; AIPE footprint from SBOSAG0E, review against the drawing",
                             name, tags="TMCS1133 DVG Hall sensor isolated", silkscreen=False, extra=_pin1_marks(6.875, -2.54))
    return text, [(0, 0, 1.325, 7.5, 10.3, 2.65, (0.15, 0.15, 0.15))]


def amc1311_footprint(name="AMC1311_DWV0008A_Slot"):
    """TI DWV0008A (SBAS786C 4218796/A): 8 pads 1.8 x 0.6 mm at 1.27 mm, centre span 10.9 mm (9.1 mm nominal
    clearance), body 5.85 x 7.5 mm (7.5 mm across the pins), 2.8 mm high; 1.2 x 10.4 mm isolation slot."""
    pads = _dual_row_pads(4, 1.27, 5.45, 1.8, 0.6) + [_slot_pad(10.8)]
    text = pf.make_footprint(name, "\n  ".join(pads), 12.7, 11.0,
                             "AMC1311 DWV0008A wide-body SOIC-8 (TI land pattern 8 x 1.8 x 0.6 mm, 1.27 mm pitch, 10.9 mm span) with a "
                             "1.2 x 10.8 mm NPTH isolation slot (>= 3 mm beyond the outer pad edges); F.Fab = pad/slot envelope, real body 7.5 x 5.85 x 2.8 mm; AIPE footprint "
                             "from SBAS786C, review against the drawing", name, tags="AMC1311 DWV isolated amplifier",
                             silkscreen=False, extra=_pin1_marks(6.35, -1.905))
    return text, [(0, 0, 1.4, 7.5, 5.85, 2.8, (0.15, 0.15, 0.15))]


def ucc21710_footprint(name="UCC21710_DW0016A_Slot"):
    """UCC21710 DW (SOIC-16 wide body): the KiCad SOIC-16W_7.5x10.3mm_P1.27mm land pattern (16 pads 2.05 x 0.6 mm at
    1.27 mm, centre span 9.3 mm, land gap 7.25 mm) plus the baseline 1.2 mm NPTH isolation slot, 16.6 mm long so it
    extends >= 3 mm beyond the outer pad edges (10.3 mm body); silkscreen limited to the pin-1 mark so nothing crosses
    the slot (replaces the library footprint whose outline crossed a board-level cut-out)."""
    pads = _dual_row_pads(8, 1.27, 4.65, 2.05, 0.6) + [_slot_pad(16.6)]
    text = pf.make_footprint(name, "\n  ".join(pads), 11.7, 16.8,
                             "UCC21710 SOIC-16 DW wide body (KiCad SOIC-16W_7.5x10.3mm_P1.27mm land pattern) with a 1.2 x 16.6 mm NPTH "
                             "isolation slot (>= 3 mm beyond the pads); F.Fab = pad/slot envelope, real body 7.5 x 10.3 x 2.65 mm; AIPE footprint "
                             "from the KiCad library geometry, review against SLUSDH8D", name, tags="UCC21710 DW isolated gate driver",
                             silkscreen=False, extra=_pin1_marks(5.675, -4.445))
    return text, [(0, 0, 1.325, 7.5, 10.3, 2.65, (0.15, 0.15, 0.15))]


def ucc14141_footprint(name="UCC14141_DWN0036A_Slot"):
    """TI DWN0036A 36-pin SSOP (SLUSF10B 4225960/A): pitch 0.65 mm, pads 1.85 x 0.45 mm, centre span 9.95 mm, body
    12.73-12.93 x 7.4-7.6 mm, 3.55 mm high, pin 1 top left, pins 1-18 left, 19-36 right; 1.2 x 17.5 mm slot."""
    pads = _dual_row_pads(18, 0.65, 4.975, 1.85, 0.45) + [_slot_pad(17.5)]
    text = pf.make_footprint(name, "\n  ".join(pads), 11.8, 17.5,
                             "UCC14141-Q1 DWN0036A 36-pin SSOP (TI land pattern 36 x 1.85 x 0.45 mm, 0.65 mm pitch, 9.95 mm span) with a "
                             "1.2 x 17.5 mm NPTH isolation slot; F.Fab = pad/slot envelope, real body 7.5 x 12.83 x 3.55 mm; AIPE footprint "
                             "from SLUSF10B, review against the drawing", name, tags="UCC14141 DWN isolated DC-DC",
                             silkscreen=False, extra=_pin1_marks(5.9, -5.525))
    return text, [(0, 0, 1.775, 7.5, 12.83, 3.55, (0.15, 0.15, 0.15))]


def toroid_footprint(name="L_Toroid_HF58x2_D69_H48_P25.4"):
    """Baseline magnetics.inductor.pcb_footprint: 2 x 3.2 mm PTH with 6.0 mm pads on 25.4 mm, winding envelope 69 mm,
    48 mm high, plus 4 x 4.3 mm NPTH on a 60 x 60 mm pattern for the potting-cup standoffs (lugs outside the
    69 mm circle)."""
    text, boxes = pf.toroid_inductor_footprint(name, 25.4, 3.2, 6.0, 69, 48)
    holes = [pf.npth_pad(x, y, 4.3) for x in (-30, 30) for y in (-30, 30)]
    body = text.rstrip()
    assert body.endswith(")")
    text = body[:-1] + "  " + "\n  ".join(holes) + "\n)\n"
    parse(text)
    text = text.replace("review against the winding drawing", "review against the winding drawing; 4 x 4.3 mm NPTH on 60 x 60 mm "
                        "for the cup standoffs (M4), 8 mm copper-free annulus to be enforced by the layout")
    return text, boxes


def heatsink_footprint(name="HS_LAM5DK_100x100_H50"):
    """Fischer LAM 5 D K 100 12 envelope: 100.5 x 100 mm base, 50 mm high, PE-bonded; 4 x 3.2 mm NPTH at (+/-45, +/-45)
    are PLACEHOLDERS (drawing not accessible).  Rule area forbids tracks, vias, copper pours and footprints on F.Cu."""
    holes = [(x, y, 3.2) for x in (-45, 45) for y in (-45, 45)]
    return pf.heatsink_envelope_footprint(name, 100.5, 100, 50, holes, keepout=("tracks", "vias", "copperpour", "footprints"))


def ptc_footprint(name="PTC_Disc_D20_P10_Envelope"):
    """Leaded PTC inrush-limiter disc envelope: 2 leads on 10 mm, drill 1.3 mm / pad 2.6 mm, 20 x 7 mm plan, 26 mm high."""
    pads = "\n  ".join([pf.tht_pad("1", -5, 0, 2.6, 1.3), pf.tht_pad("2", 5, 0, 2.6, 1.3)])
    text = pf.make_footprint(name, pads, 21, 8, "Leaded PTC disc envelope (TDK B59xxx class, part to be re-selected): 10 mm pitch, "
                             "1.3 mm drill, 20 mm disc standing on edge, 26 mm high; AIPE envelope", name, tags="PTC inrush thermistor")
    return text, [(0, 0, 13, 21, 8, 26, (0.4, 0.4, 0.4))]


CUSTOM_NAMES = dict(c_in="C_Film_41.5x28x37_P37.5x10.2", c_out="C_Film_41.5x30x45_P37.5x20.3", toroid="L_Toroid_HF58x2_D69_H48_P25.4",
                    heatsink="HS_LAM5DK_100x100_H50", ucc14141="UCC14141_DWN0036A_Slot", amc1311="AMC1311_DWV0008A_Slot",
                    tmcs1133="TMCS1133_DVG0010A_HV_Slot", ptc="PTC_Disc_D20_P10_Envelope", ucc21710="UCC21710_DW0016A_Slot")

CUSTOM_FOOTPRINTS = {
    CUSTOM_NAMES["c_in"]: pf.film_capacitor_footprint(CUSTOM_NAMES["c_in"], 37.5, 41.5, 28.0, 37.0, 1.6, pins=4, second_pitch_mm=10.2, pad_mm=3.0),
    CUSTOM_NAMES["c_out"]: pf.film_capacitor_footprint(CUSTOM_NAMES["c_out"], 37.5, 41.5, 30.0, 45.0, 1.6, pins=4, second_pitch_mm=20.3, pad_mm=3.0),
    CUSTOM_NAMES["toroid"]: toroid_footprint(),
    CUSTOM_NAMES["heatsink"]: heatsink_footprint(),
    CUSTOM_NAMES["ucc14141"]: ucc14141_footprint(),
    CUSTOM_NAMES["amc1311"]: amc1311_footprint(),
    CUSTOM_NAMES["tmcs1133"]: tmcs1133_footprint(),
    CUSTOM_NAMES["ptc"]: ptc_footprint(),
    CUSTOM_NAMES["ucc21710"]: ucc21710_footprint(),
}


def aipe(key: str) -> str:
    return f"{pf.CUSTOM_LIB}:{CUSTOM_NAMES[key]}"


# --- helpers ------------------------------------------------------------------------------------

def capx(c: Circuit, key: str, a, b, page, *, note="", dnp=False):
    """Capacitor from PASSIVE_CAPS or EXTRA_CAPS."""
    if key in PASSIVE_CAPS:
        return c.cap(key, a, b, page, note=note, dnp=dnp)
    spec = EXTRA_CAPS[key]
    return c.add("C", key.rsplit("/", 1)[0], spec["footprint"], {1: a, 2: b}, page=page, kind="C", mpn=spec["mpn"],
                 maker=spec["maker"], source=spec["source"], note=(note + "; " if note else "") + spec["note"], dnp=dnp)


def thin_film(c: Circuit, value: str, a, b, page, *, package="0603", note="", dnp=False):
    """0.1 % thin-film resistor (Vishay TNPW e3); ordering format per the series datasheet, availability unverified."""
    code = TNPW_CODES[value]
    return c.resistor(value, a, b, page, package=package, mpn=f"TNPW{package}{code}BEEA", maker="Vishay", source=VISHAY_TNPW,
                      note=(note + "; " if note else "") + "0.1 % 25 ppm/K thin film, TNPW ordering code unverified", dnp=dnp)


def erjp08(c: Circuit, value: str, code: str, a, b, page, *, note=""):
    """Panasonic ERJ-P08 1206 anti-surge resistor (0.66 W, 500 V); search-snippet level."""
    return c.resistor(value, a, b, page, package="1206", mpn=f"ERJ-P08F{code}V", maker="Panasonic", source=PANASONIC_ERJP,
                      note=(note + "; " if note else "") + "ERJ-P08 anti-surge 1206, 0.66 W / 500 V (search-snippet)")


def diode(c: Circuit, value, footprint, cathode, anode, page, *, mpn, maker, source, note="", dnp=False):
    return c.add("D", value, footprint, {1: cathode, 2: anode}, page=page, kind="D", mpn=mpn, maker=maker, source=source,
                 definitions=DIODE_PINS, note=note, dnp=dnp)


def testpoint(c: Circuit, net, page, *, note=""):
    return c.add("TP", net, "TestPoint:TestPoint_Pad_D2.0mm", {1: net}, page=page, kind="TP",
                 note=note or "SELV test pad, bare PCB (no purchased part)")


# --- building blocks --------------------------------------------------------------------------

def bias_module(c: Circuit, tag: str, page: str, *, vdd, vee, com, r_top_vdd, r_top_com, pg_net, ref, island, note):
    """UCC14141-Q1 isolated bias module with input CM choke, feedback dividers, RLIM and output capacitors.

    Primary: 12V_PROT / GND_CTRL -> 744226S (windings 1-4, 2-3) -> 12V_BIAS_<tag> / GNDP_<tag> -> VIN / GNDP, 3 x 10 uF +
    100 nF (baseline bias_supply.input).  Secondary: VDD-VEE = 2.5 V x (R_top + 16.2 k) / 16.2 k, COM-VEE likewise,
    330 pF C0G across each bottom resistor, RLIM 1 k placeholder (human review), 2 x 4.7 uF + 100 nF VDD-VEE, 4.7 uF COM-VEE.
    """
    with c.block(f"bias_{tag.lower()}", f"{island} isolated bias supply (UCC14141-Q1)"):
        vbias, gndp = f"12V_BIAS_{tag}", f"GNDP_{tag}"
        fb_vdd, fb_vee, rlim = f"{island}_FB_VDD", f"{island}_FB_VEE", f"{island}_RLIM"
        c.add("L", "744226S", "Inductor_SMD:L_CommonMode_Wuerth_WE-SL2", {1: "12V_PROT", 2: "GND_CTRL", 3: gndp, 4: vbias}, page=page,
              kind="L", mpn="744226S", maker="Wuerth Elektronik", source="https://www.we-online.com/components/products/datasheet/744226S.pdf",
              definitions=CHOKE_PINS, note=f"WE-SL2 CM choke 10 uH / 1.6 A at the {tag} bias input (KR-IS-002); windings 1-4 (12 V) and 2-3 (return); "
              "A-P3: module ground GNDP after the choke")
        for _ in range(3):
            capx(c, "10u/25V/1210", vbias, gndp, page, note="UCC14141 input capacitor (3 x 10 uF for >= 20 uF effective at 13.2 V, CR-19)")
        capx(c, "100n/50V/0603", vbias, gndp, page, note="UCC14141 VIN high-frequency bypass at pins 7/8 (SLUSF10B)")
        nets = {n: gndp for n in (1, 2, 5, *range(8, 19))}
        nets.update({3: pg_net, 4: "BIAS_EN_F", 6: vbias, 7: vbias, 28: vdd, 29: vdd, 32: rlim, 33: fb_vee, 34: fb_vdd, 35: vee})
        nets.update({n: vee for n in (19, 20, 21, 22, 23, 24, 25, 26, 27, 30, 31, 36)})
        c.add("U", "UCC14141QDWNRQ1", aipe("ucc14141"), nets, page=page, kind="IC", mpn="UCC14141QDWNRQ1", maker=TI,
              source=TI_DS.format("ucc14141-q1"), definitions=ucc14141_pins("passive" if vee in FLAG_NETS else "power_out"), ref=ref,
              note=note + "; reinforced isolated bias module, pinout SLUSF10B Table 6-1 (fetched-datasheet); PG active-low good")
        thin_film(c, r_top_vdd, vdd, fb_vdd, page, note=f"FBVDD top: VDD-VEE = 2.5 V x (R_top + 16.2 k)/16.2 k")
        thin_film(c, "16.2k", fb_vdd, vee, page, note="FBVDD bottom (VEEA single-point return)")
        capx(c, "330p/50V/0603", fb_vdd, vee, page, note="330 pF C0G across the FBVDD bottom resistor (SLUSF10B)")
        thin_film(c, r_top_com, com, fb_vee, page, note="FBVEE top: COM-VEE = 2.5 V x (R_top + 16.2 k)/16.2 k")
        thin_film(c, "16.2k", fb_vee, vee, page, note="FBVEE bottom (VEEA single-point return)")
        capx(c, "330p/50V/0603", fb_vee, vee, page, note="330 pF C0G across the FBVEE bottom resistor (SLUSF10B)")
        c.resistor("1k", rlim, com, page, package="0805", note="RLIM per SLUSF10B 'RLIM Resistor Selection'; 1 k placeholder, HUMAN REVIEW "
                   "(COM-VEE regulator sink/source current and the RLIM pin 0.125 A rms rating)")
        for _ in range(2):
            capx(c, "4.7u/25V/1206", vdd, vee, page, note="UCC14141 VDD-VEE output capacitor (baseline bias_supply.output_caps)")
        capx(c, "100n/50V/0603", vdd, vee, page, note="A-P4: 100 nF VDD-VEE next to the IC pins (SLUSF10B pin table)")
        capx(c, "4.7u/25V/1206", com, vee, page, note="UCC14141 COM-VEE output capacitor (baseline bias_supply.output_caps)")
        c.resistor("10k", "3V3", pg_net, page, note="A-P5: pull-up for the open-drain PG output (active-low power good)")


def gate_channel(c: Circuit, x: str, other: str, drain_net: str, page: str, *, q_ref, u_ref, bias_ref):
    """One UCC21710-Q1 channel with its UCC14141-Q1 bias module (baseline power_stage.gate_driver / bias_supply)."""
    island = "HS" if x == "H" else "LS"
    g, ks, vdd, vee = f"G_{x}", f"KS_{x}", f"VDD_{x}", f"VEE_{x}"
    node_a, node_oc, gk = f"DESAT_{x}_A", f"DESAT_{x}_OC", f"{island}_GK"
    outh, outl, clmp = f"{island}_OUTH", f"{island}_OUTL", f"{island}_CLMP"
    pwm_f, pwm_other_f = f"PWM_{x}_F", f"PWM_{other}_F"
    # Presentation block (V2.1): the driver's own satellites - PWM receiving network, gate network, decoupling and the
    # RDY / FLT pull-ups - are one functional group so they hang off the driver's pin lanes instead of forming tiny
    # groups that the sheet router has to join with long wires.  The DESAT network and the bias module stay separate.
    with c.block(f"driver_{x.lower()}", f"{island} isolated gate driver (UCC21710-Q1): PWM input, gate network, status pull-ups, decoupling"):
        # Mezzanine receiving network of the own PWM (baseline gate_driver.inputs: 100 ohm + 100 pF + 10 k pull-down).
        c.resistor("100", f"PWM_{x}", pwm_f, page, note=f"PWM_{x} series element of the 100 ohm / 100 pF / 10 k receiving network (KR-GD-008 adapted)")
        capx(c, "100p/50V/0603", pwm_f, "GND_CTRL", page, note="100 pF at the driver input pin (tau 10 ns)")
        c.resistor("10k", pwm_f, "GND_CTRL", page, note="10 k pull-down: driver input defined low when the mezzanine is open")
        nets = {1: ks, 2: node_oc, 3: ks, 4: outh, 5: vdd, 6: outl, 7: clmp, 8: vee, 9: "GND_CTRL", 10: pwm_f, 11: pwm_other_f,
                12: f"RDY_{x}", 13: f"FLT_{x}_N", 14: "RESET_N_F", 15: "3V3", 16: None}
        c.add("U", "UCC21710QDWRQ1", "AIPE:" + CUSTOM_NAMES["ucc21710"], nets, page=page, kind="IC", mpn="UCC21710QDWRQ1", maker=TI,
              source=TI_DS.format("ucc21710-q1"), definitions=UCC21710_PINS, ref=u_ref,
              note=f"{island} isolated SiC driver, pinout SLUSDH8D (fetched-datasheet); IN+ = PWM_{x}_F, IN- = PWM_{other}_F interlock (KR-GD-009); "
              "AIN tied to COM (CR-01); APWM unused; AIPE footprint with the KiCad SOIC-16W land pattern and the 1.2 x 16.6 mm isolation slot")
        erjp08(c, "10", "10R0", outh, g, page, note="R_ON 10 ohm bring-up (tuning target 6.8 ohm = ERJ-P08F6R80V), baseline rg_on_ohm")
        erjp08(c, "3.3", "3R30", outl, g, page, note="R_OFF 3.3 ohm, baseline rg_off_ohm")
        c.resistor("0", clmp, g, page, mpn="RC0603JR-070RL", note="Miller clamp link CLMPI -> gate, 0 ohm 0603, path <= 15 mm (KR-GD-003, REQUIRED)")
        c.resistor("10k", g, ks, page, package="0805", note="R_GS gate-to-Kelvin discharge at the device side of R_G (KR-GD-007)")
        c.resistor("1", g, gk, page, dnp=True, note="DNP gate-Kelvin RC (KR-GD-010 review): 1 ohm 0603 pads")
        capx(c, "470p/50V/0603", gk, ks, page, dnp=True, note="DNP gate-Kelvin RC (KR-GD-010 review): 470 pF C0G pads")
        c.add("TP", f"VGS_{x}", "TestPoint:TestPoint_2Pads_Pitch2.54mm_Drill0.8mm", {1: g, 2: ks}, page=page, kind="TP",
              definitions=pin_defs("1:G:passive 2:KS:passive"),
              note=f"V_GS probe loop at the device side of R_G (CR-11); {'floats at the switch node - ' if x == 'H' else ''}HV referenced, isolated probe only")
        for _ in range(2):
            capx(c, "4.7u/25V/1206", vdd, ks, page, note="VDD-COM decoupling between driver output pins and gate/Kelvin connection (KR-PCB-002)")
        capx(c, "100n/50V/0603", vdd, ks, page, note="VDD-COM high-frequency decoupling at the pins")
        capx(c, "4.7u/25V/1206", ks, vee, page, note="COM-VEE decoupling (KR-PCB-002)")
        capx(c, "100n/50V/0603", ks, vee, page, note="COM-VEE high-frequency decoupling at the pins")
        capx(c, "1u/50V/0805", "3V3", "GND_CTRL", page, note="VCC decoupling 1 uF (datasheet condition) at pin 15")
        capx(c, "100n/50V/0603", "3V3", "GND_CTRL", page, note="VCC high-frequency decoupling at pin 15")
    with c.block(f"desat_{x.lower()}", f"{island} DESAT protection network"):
        # DESAT network (baseline gate_driver.desat.network).
        erjp08(c, "2.2k", "2201", vdd, node_a, page, note="DESAT R1 2.2 k: VDD -> node A (bias 6-9 mA)")
        diode(c, "US1M 1000V", "Diode_SMD:D_SMA", drain_net, node_a, page, mpn="US1M-13-F", maker="Diodes Incorporated",
              source="https://www.diodes.com/part/view/US1M/", note=f"DESAT diode, cathode on the drain net {drain_net}, anode at node A; lifecycle unverified")
        c.resistor("4.99k", node_a, node_oc, page, note="DESAT R2 4.99 k: node A -> OC")
        c.resistor("1k", node_oc, ks, page, note="DESAT R3 1.00 k: OC -> COM (trip V_DS 3.6 V with R1/R2/R3)")
        capx(c, "680p/50V/0603", node_oc, ks, page, note="DESAT blanking 680 pF C0G at OC/COM (288 ns external blanking)")
        diode(c, "BAT42W Schottky", "Diode_SMD:D_SOD-123", node_oc, ks, page, mpn="BAT42W-V", maker="Vishay",
              source="https://www.vishay.com/docs/85660/bat42w.pdf", dnp=True,
              note="DNP reference-derived clamp COM -> OC (anode at COM); the -0.67 V DC case does not occur dynamically; unverified part")
    with c.block(f"driver_{x.lower()}"):
        # Same add order as V2 (reference numbering and netlist identity); presentation group = the driver block above.
        c.resistor("4.7k", "3V3", f"RDY_{x}", page, note="RDY open-drain pull-up (research record gate_driver.per_channel_bom R_PU)")
        c.resistor("4.7k", "3V3", f"FLT_{x}_N", page, note="FLT open-drain pull-up (latched fault, active low)")
    bias_module(c, x, page, vdd=vdd, vee=vee, com=ks, r_top_vdd="107k", r_top_com="9.76k", pg_net=f"PG_BIAS_{x}_N", ref=bias_ref, island=island,
                note=f"{island} gate bias VDD-VEE 19.0 V (107 k / 16.2 k), COM-VEE 4.0 V (9.76 k / 16.2 k) -> +15 V / -4 V at the gate "
                "(baseline bias_supply.gate_channels); +18 V option = FBVDD top 127 k (BOM option, C4MS only)")


def power_stage(c: Circuit):
    page = "01_power_stage"
    redcube = "TerminalBlock_Wuerth:Wuerth_REDCUBE-THR_WP-THRSH_74651195_THR"
    terminals = [("VIN_RAW (+IN)", "VIN_RAW", "DC input + from the fuse holder (off-board KLKD025.T)"),
                 ("PGND (-IN)", "PGND", "DC input return"),
                 ("VOUT (+OUT)", "VOUT", "DC output +"),
                 ("PGND (-OUT)", "PGND", "DC output return"),
                 ("RLY_A (VIN_RAW)", "VIN_RAW", "bypass relay contact terminal A (Omron G9EA-1 DC12, chassis mounted)"),
                 ("RLY_B (VIN)", "VIN", "bypass relay contact terminal B; PTC RT1 bridges A-B on board")]
    with c.block("terminals", "Power terminals, precharge PTC, MOV"):
        for value, net, note in terminals:
            c.add("J", value, redcube, {1: net}, page=page, kind="J", mpn="74651195", maker="Wurth Elektronik",
                  source="https://www.we-online.de/katalog/datasheet/74651195.pdf", note=f"REDCUBE THR M5 (CR-10); ring lug under IPXXB cover; {note}")
        c.add("RT", "PTC precharge (re-select)", aipe("ptc"), {1: "VIN_RAW", 2: "VIN"}, page=page, kind="RT",
              mpn="TDK B59xxx PTC to be re-selected", maker="TDK (EPCOS)", source="https://www.tdk-electronics.tdk.com/en/ptc-thermistors",
              note="Precharge PTC across the relay contacts: R25 100-150 ohm, Vmax >= 480 V DC, Vlink >= 620 V DC (CR-19, human review); envelope footprint")
        c.add("RV", "S20K385 MOV", "Varistor:RV_Disc_D21.5mm_W5.4mm_P10mm", {1: "VIN", 2: "PGND"}, page=page, kind="RV", mpn="B72220S0381K101",
              maker="TDK (EPCOS)", source="https://www.tdk-electronics.tdk.com/inf/70/db/var/SIOV_Leaded_StandarD.pdf", dnp=True,
              note="Optional input MOV (8 kA, 150 J, 1 W), DNP; disc thickness vs footprint W5.4 to confirm")
    with c.block("half_bridge", "Half bridge, HF capacitor bank, DC-link capacitors"):
        for ref, drain, source, ks, g, note in (("Q1", "VIN", "SW", "KS_H", "G_H", "high-side; tab = VIN (DC)"),
                                                ("Q2", "SW", "PGND", "KS_L", "G_L", "low-side; tab = SW (switching)")):
            c.add("Q", "C4MS025120K", "Package_TO_SOT_THT:TO-247-4_Vertical", {1: drain, 2: source, 3: ks, 4: g}, page=page, kind="Q",
                  mpn="C4MS025120K", maker="Wolfspeed", ref=ref, definitions=FET_PINS,
                  source="https://assets.wolfspeed.com/uploads/2025/11/Wolfspeed_C4MS025120K_data_sheet.pdf",
                  note=f"1200 V / 25 mohm SiC MOSFET TO-247-4 Kelvin source, {note}; pad order 1 D, 2 S, 3 KS, 4 G per PRD 05966 front view "
                  "(ASSUMPTION - verify pad-1 side); insulated to the PE-bonded heatsink with Sil-Pad TSP A2000 (CR-13)")
        for i in range(10):
            capx(c, "0.47u/630V/2220", "VIN", "PGND", page, note=f"C_HF {i + 1}/10, row {'1 (<= 5 mm)' if i < 5 else '2 (<= 15 mm)'} beside the TO-247-4 legs; "
                 "DC-bias curve unverified (open item)")
        for n in (1, 2):
            c.add("C", "20uF/800V film", aipe("c_in"), {1: "VIN", 2: "PGND"}, page=page, kind="C", mpn="B32776G8206K000", maker="TDK (EPCOS)",
                  source="https://www.tdk-electronics.tdk.com/inf/20/20/db/fc_2009/MKP_B32774_778.pdf",
                  note=f"DC-link input film C_IN{n} (14.5 A rms rating, 6.92 A each worst); alternates KEMET C4AQIBW5200A3JJ / Vishay MKP1848C62080JP4")
    with c.block("output", "Output inductor, current sensor, output capacitors"):
        c.add("L", "272uH/25A toroid", aipe("toroid"), {1: "SW", 2: "VOUT_L"}, page=page, kind="L", mpn="AIPE custom choke: 2 x Magnetics 0058192A2 stacked, 34 T AWG10",
              maker="custom winding (house to be selected)", source="design/research/inductor.json selection.magnetic_record",
              note="L1: 319 uH at 0 A, 272 uH at 25 A, 210 uH at 41 A (nominal); DCR 12.2 mohm; in the fan stream (CR-14); mass carried by the cup standoffs")
        c.add("U", "TMCS1133C2AQDVGR", aipe("tmcs1133"), {1: "VOUT_L", 2: "VOUT", 3: "GND_CTRL", 4: "GND_CTRL", 5: None, 6: "ISENSE", 7: "OC_N",
                                                         8: "VOC_SET", 9: "3V3", 10: "3V3"}, page=page, kind="IC", mpn="TMCS1133C2AQDVGR", maker=TI,
              source=TI_DS.format("tmcs1133"), definitions=TMCS1133_PINS, ref="U10",
              note="Isolated Hall current sensor in the inductor output path (IN+ bar = VOUT_L, IN- bar = VOUT), 50 mV/A, 0.33 V at 0 A, VS 3.3 V; "
              "OC threshold 37.5 A via VOC_SET 0.750 V; pinout SBOSAG0E (fetched-datasheet); ALERT unused -> GND per datasheet (A-P10)")
        for n in (1, 2):
            c.add("C", "60uF/450V film", aipe("c_out"), {1: "VOUT", 2: "PGND"}, page=page, kind="C", mpn="B32776G4606K000", maker="TDK (EPCOS)",
                  source="https://www.tdk-electronics.tdk.com/inf/20/20/db/fc_2009/MKP_B32774_778.pdf",
                  note=f"Output film C_OUT{n} (1.43 A rms each); 440 V high-side-short fault survivable")
    with c.block("bleeders", "Bleeders and LIVE indicators"):
        # Bleeders and indicators (baseline capacitors.bleeders, CR-03).
        for a, b in (("VIN", "BLD_IN_1"), ("BLD_IN_1", "BLD_IN_2"), ("BLD_IN_2", "PGND")):
            c.resistor("120k", a, b, page, package="2512", note="Input bleeder chain 3 x 120 k (360 k, 0.54 W at 440 V, 160 V per element at 480 V)")
        for a, b in (("VIN", "IND_IN_1"), ("IND_IN_1", "IND_IN_2"), ("IND_IN_2", "IND_IN_3")):
            c.resistor("150k", a, b, page, package="1206", note="Input DC-LINK LIVE indicator string 3 x 150 k 1206 (<= 160 V, 0.17 W per element)")
        c.add("D", "LED red", "LED_SMD:LED_0805_2012Metric", {1: "PGND", 2: "IND_IN_3"}, page=page, kind="D", mpn="LTST-C170KRKT", maker="Lite-On",
              source="https://optoelectronics.liteon.com/", definitions=DIODE_PINS, note="Input DC-LINK LIVE LED (warning only, not proof of safe voltage); part unverified")
        for a, b in (("VOUT", "BLD_OUT_1"), ("BLD_OUT_1", "PGND")):
            c.resistor("100k", a, b, page, package="2512", note="Output bleeder chain 2 x 100 k (200 k, 0.20 W; 0.97 W / 220 V per element in the 440 V fault)")
        for a, b in (("VOUT", "IND_OUT_1"), ("IND_OUT_1", "IND_OUT_2")):
            c.resistor("100k", a, b, page, package="1206", note="Output LIVE indicator string 2 x 100 k 1206")
        c.add("D", "LED red", "LED_SMD:LED_0805_2012Metric", {1: "PGND", 2: "IND_OUT_2"}, page=page, kind="D", mpn="LTST-C170KRKT", maker="Lite-On",
              source="https://optoelectronics.liteon.com/", definitions=DIODE_PINS, note="Output LIVE LED; part unverified")
    with c.block("snubber_damping", "Snubber and damping leg (DNP)"):
        # Snubber pads (DNP) across the LS device and the damping leg (DNP) across the HF tier.
        c.resistor("10", "SW", "SNUB_MID", page, package="2512", dnp=True, note="A-P7: RC snubber pads SW-PGND, DNP until double-pulse results (value placeholder)")
        capx(c, "1n/1kV/1812", "SNUB_MID", "PGND", page, dnp=True, note="A-P7: snubber capacitor 1 kV 1812 pads, DNP (value placeholder)")
        for _ in range(2):
            capx(c, "0.47u/630V/2220", "VIN", "DAMP_MID", page, dnp=True, note="Damping leg (DNP): 2 x 0.47 uF 630 V in parallel across the HF tier (baseline damping_leg_dnp)")
            c.resistor("0.47", "DAMP_MID", "PGND", page, package="2512", dnp=True, mpn="ERJ-1TRQFR47U", maker="Panasonic", source=PANASONIC_ERJP,
                       note="Damping leg (DNP): 2 x 0.47 ohm 1 W 2512 in parallel (>= 2 W for ~1 W ring energy); part number unverified")
    with c.block("pe", "PE network"):
        # PE network (baseline protection.power_path.pe).
        c.add("H", "PE M4 stud", "MountingHole:MountingHole_4.3mm_M4_Pad", {1: "PE"}, page=page, kind="H",
              note="M4 PE stud pad bonded to heatsink and baseplate (bond <= 0.1 ohm); IEC 60417-5019 label")
        c.resistor("0", "PGND", "PE", page, package="2512", dnp=True, mpn="CRCW25120000Z0EG", note="PGND-to-PE configurable link, DNP until the source earthing is defined (A-23 review)")
        c.resistor("1M", "PGND", "PE_REF_MID", page, package="2512", mpn="CRCW25121M00FKEG", note="A-P11: PGND-PE reference 2 x 1 M in series (<= 240 V per 500 V element)")
        c.resistor("1M", "PE_REF_MID", "PE", page, package="2512", mpn="CRCW25121M00FKEG", note="A-P11: PGND-PE reference, second element")
        capx(c, "10n/300VAC/Y2", "VIN", "PE", page, dnp=True, note="Y2 footprint VIN-PE, DNP (touch-current review)")
        capx(c, "10n/300VAC/Y2", "PGND", "PE", page, dnp=True, note="Y2 footprint PGND-PE, DNP (touch-current review)")


def sensing_island(c: Circuit):
    page = "04_sensing_island"
    bias_module(c, "S", page, vdd="ISO_15V", vee="PGND", com="5V_ISO", r_top_vdd="80.6k", r_top_com="16.2k", pg_net="PG_BIAS_S_N", ref="U5", island="ISO",
                note="Sensing-island bias (CR-12): VDD-VEE 15 V (A-P2: 80.6 k / 16.2 k = 14.94 V, capacitor load only), COM-VEE 5.0 V (16.2 k / 16.2 k) = 5V_ISO; VEE = PGND")
    with c.block("isolated_sensing", "Isolated VIN / VOUT sensing (AMC1311)"):
        for ref, label, top_net, div_net, outp, outn, count, fs in (("U6", "VIN", "VIN", "VIN_DIV", "VIN_OUTP", "VIN_OUTN", 4, "602 V"),
                                                                   ("U7", "VOUT", "VOUT", "VOUT_DIV", "VOUT_OUTP", "VOUT_OUTN", 2, "302 V")):
            prev = top_net
            for i in range(count):
                nxt = div_net if i == count - 1 else f"{label}_DIV_T{i + 1}"
                thin_film(c, "750k", prev, nxt, page, package="1206", note=f"{label} ladder element {i + 1}/{count} (750 k 1206 0.1 %, <= 120 V / 19 mW each)")
                prev = nxt
            thin_film(c, "10k", div_net, "PGND", page, note=f"{label} ladder bottom 10.0 k (full scale {fs} = 2 V)")
            capx(c, "1n/50V/0603", div_net, "PGND", page, note="1 nF C0G across the ladder bottom (16 kHz)")
            capx(c, "100p/50V/0603", div_net, "PGND", page, note="100 pF directly at the AMC1311 IN pin")
            c.add("U", "AMC1311BDWVR", aipe("amc1311"), {1: "5V_ISO", 2: div_net, 3: "PGND", 4: "PGND", 5: "GND_CTRL", 6: outn, 7: outp, 8: "3V3"},
                  page=page, kind="IC", mpn="AMC1311BDWVR", maker=TI, source=TI_DS.format("amc1311"), definitions=AMC1311_PINS, ref=ref,
                  note=f"Reinforced isolated {label} sense amplifier (2 V input range, gain 1); SHTDN tied to GND1 (active high); pinout SBAS786C (fetched-datasheet)")
            capx(c, "100n/50V/0603", "5V_ISO", "PGND", page, note=f"{ref} VDD1 decoupling (PE-PCB-008)")
            capx(c, "100n/50V/0603", "3V3", "GND_CTRL", page, note=f"{ref} VDD2 decoupling (PE-PCB-008)")


def selv_strip(c: Circuit):
    page = "05_selv_strip"
    with c.block("mezzanine", "Mezzanine socket and receiving networks"):
        nets = {str(n): mezzanine_net(str(n)) for n in range(1, 51)}
        c.add("J", "Mezzanine 2x25 socket", "Connector_PinSocket_2.54mm:PinSocket_2x25_P2.54mm_Vertical", nets, page=page, kind="J",
              mpn="SSW-125-01-G-D", maker="Samtec", source="https://www.samtec.com/products/ssw",
              definitions={str(n): dict(name=str(n), type="passive") for n in range(1, 51)},
              note="Stacked mezzanine to the control board (TSW-125-07-G-D header there); nets per design_decisions.json interconnect.pin_assignment; "
              "24 ground pins; stack height ~11 mm (unverified)")
        for raw, filtered, note in (("RESET_N", "RESET_N_F", "driver RST/EN x2"), ("BIAS_EN", "BIAS_EN_F", "UCC14141 ENA x3")):
            c.resistor("100", raw, filtered, page, note=f"A-P6: receiving network for {note} (100 ohm / 100 pF / 10 k pull-down, baseline interconnect.signalling)")
            capx(c, "100p/50V/0603", filtered, "GND_CTRL", page, note=f"A-P6: 100 pF at the receiving pins ({note})")
            c.resistor("10k", filtered, "GND_CTRL", page, note=f"A-P6: 10 k pull-down - {note} held off when the mezzanine is open")
    with c.block("difference_amplifiers", "OPA2320 difference amplifiers"):
        # OPA2320 difference amplifiers, gain 1.5 (baseline sensing.vin.conversion, CR-16).
        c.add("U", "OPA2320AIDGKR", "Package_SO:VSSOP-8_3x3mm_P0.65mm", {1: "VIN_SENSE", 2: "VIN_AMP_N", 3: "VIN_AMP_P", 4: "GND_CTRL", 5: "VOUT_AMP_P",
                                                                          6: "VOUT_AMP_N", 7: "VOUT_SENSE", 8: "3V3"}, page=page, kind="IC",
              mpn="OPA2320AIDGKR", maker=TI, source=TI_DS.format("opa2320"), definitions=OPA2320_PINS, ref="U8",
              note="Difference amplifiers A = VIN, B = VOUT, gain 1.5 (10.0 k / 15.0 k 0.1 %), 32 kHz; pinout SBOS513F (fetched-datasheet)")
        capx(c, "100n/50V/0603", "3V3", "GND_CTRL", page, note="OPA2320 supply decoupling")
        for label, outp, outn, amp_p, amp_n, out in (("VIN", "VIN_OUTP", "VIN_OUTN", "VIN_AMP_P", "VIN_AMP_N", "VIN_SENSE"),
                                                     ("VOUT", "VOUT_OUTP", "VOUT_OUTN", "VOUT_AMP_P", "VOUT_AMP_N", "VOUT_SENSE")):
            thin_film(c, "10k", outp, amp_p, page, note=f"{label} difference amplifier input resistor (+)")
            thin_film(c, "15k", amp_p, "GND_CTRL", page, note=f"{label} difference amplifier shunt resistor (+), gain 1.5")
            capx(c, "330p/50V/0603", amp_p, "GND_CTRL", page, note=f"A-P8: 330 pF on the (+) leg for CMRR balance ({label})")
            thin_film(c, "10k", outn, amp_n, page, note=f"{label} difference amplifier input resistor (-)")
            thin_film(c, "15k", amp_n, out, page, note=f"{label} difference amplifier feedback resistor, gain 1.5")
            capx(c, "330p/50V/0603", amp_n, out, page, note=f"330 pF across the feedback resistor (32 kHz) ({label})")
    with c.block("reference_oc", "REF3125 reference, OC threshold, ISENSE_REF"):
        # Reference, OC threshold and ISENSE_REF.
        c.add("U", "REF3125AIDBZR", "Package_TO_SOT_SMD:SOT-23", {1: "3V3", 2: "REF2V5_PB", 3: "GND_CTRL"}, page=page, kind="IC", mpn="REF3125AIDBZR", maker=TI,
              source="https://www.ti.com/lit/gpn/REF31", definitions=REF3125_PINS, ref="U9",
              note="2.5 V reference for the TMCS1133 OC threshold (power-board SELV strip, CR-16); pinout SBVS046E (fetched-datasheet)")
        capx(c, "1u/50V/0805", "3V3", "GND_CTRL", page, note="REF3125 supply bypass (>= 0.47 uF per SBVS046E)")
        capx(c, "100n/50V/0603", "REF2V5_PB", "GND_CTRL", page, note="REF3125 output capacitor (stable with any load capacitance)")
        thin_film(c, "2.32k", "REF2V5_PB", "VOC_SET", page, note="V_OC divider top: VOC = 2.5 V x 1.00 k / 3.32 k = 0.753 V -> I_OC 37.5 A (0.7487 V with the 120 k pin load)")
        thin_film(c, "1k", "VOC_SET", "GND_CTRL", page, note="V_OC divider bottom 1.00 k (< 10 k per SBOSAG0E Figure 9-5)")
        c.resistor("10k", "3V3", "OC_N", page, note="OC_N open-drain pull-up 10 k (task baseline); OC_N -> TZ2 and the fault latch on the control board")
        capx(c, "100n/50V/0603", "3V3", "GND_CTRL", page, note="A-P10: TMCS1133 VS decoupling 100 nF at pins 9/10")
        capx(c, "1u/50V/0805", "3V3", "GND_CTRL", page, note="A-P10: TMCS1133 VS bulk 1 uF")
        thin_film(c, "9.09k", "3V3", "ISENSE_REF", page, note="A-P1: ISENSE_REF = 3V3 x 1.00 k / 10.09 k = 0.327 V ratiometric zero-current reference (TMCS1133 has no VREF pin)")
        thin_film(c, "1k", "ISENSE_REF", "GND_CTRL", page, note="A-P1: ISENSE_REF divider bottom")
        capx(c, "100n/50V/0603", "ISENSE_REF", "GND_CTRL", page, note="A-P1: ISENSE_REF filter")
    with c.block("relay_fan", "Relay coil drive, fan header, 12 V bulk"):
        # Fan, relay coil, 12 V bulk.
        c.header(3, {1: "12V_PROT", 2: "GND_CTRL", 3: "FAN_TACH"}, page, note="FAN 12V/GND/TACH")
        c.resistor("10k", "3V3", "FAN_TACH", page, note="FAN_TACH open-collector pull-up (LAM 5 D K fan tacho, stall derating within 2 s)")
        c.add("J", "Relay coil K1", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal", {1: "12V_PROT", 2: "K1_LOW"}, page=page,
              kind="J", mpn="1715721", maker="Phoenix Contact", source="https://www.phoenixcontact.com/",
              note="Relay coil terminals (Omron G9EA-1 DC12 coil 417 mA, chassis mounted); firmware PWM hold 50-60 % REQUIRED; order code unverified")
        c.add("Q", "AO3400A", "Package_TO_SOT_SMD:SOT-23", {1: "RLY_G", 2: "GND_CTRL", 3: "K1_LOW"}, page=page, kind="Q", mpn="AO3400A",
              maker="Alpha and Omega Semiconductor", source="https://www.aosmd.com/res/datasheets/AO3400A.pdf", definitions=AO3400A_PINS,
              note="Relay coil low-side switch (30 V, 5.7 A, 48 mohm max at 2.5 V); pinout AOS Rev 3.1 (fetched-datasheet): 1 G, 2 S, 3 D")
        c.resistor("100", "RELAY_ON", "RLY_G", page, note="RELAY_ON gate series resistor")
        c.resistor("10k", "RLY_G", "GND_CTRL", page, note="Gate pull-down: relay off when the mezzanine is open")
        diode(c, "SS14 Schottky", "Diode_SMD:D_SMA", "12V_PROT", "K1_LOW", page, mpn="SS14", maker="onsemi / Vishay / Diodes Inc (multi-source)",
              source="https://www.onsemi.com/products/discrete-power-modules/schottky-diodes-schottky-rectifiers/ss14",
              note="Coil freewheel diode >= 1 A (CR-19): anode K1_LOW, cathode 12V_PROT; datasheet not fetched")
        capx(c, "100u/25V/elec", "12V_PROT", "GND_CTRL", page, note="12V_PROT bulk 100 uF (baseline aux_12V_protection.bulk_uF)")
        capx(c, "10u/25V/1210", "12V_PROT", "GND_CTRL", page, note="12V_PROT bulk 10 uF ceramic")


def mechanical(c: Circuit):
    page = "06_mechanical"
    with c.block("mounting", "Heatsink envelope and mounting holes"):
        c.add("HS", "LAM 5 D K 100 12", aipe("heatsink"), {}, page=page, kind="HS", mpn="LAM 5 D K 100 12", maker="Fischer Elektronik",
              source="https://www.fischerelektronik.de/", definitions={},
              note="Fan heatsink envelope 100.5 x 100 x 50 mm, 0.30 K/W distributor figure (unverified), PE-bonded; both TO-247-4 clipped to one face at 28 mm "
              "pitch; corner holes are placeholders; reserve 175 x 110 mm incl. air corridors")
        for i in range(6):
            c.add("H", "M4 standoff", "MountingHole:MountingHole_4.3mm_M4", {}, page=page, kind="H", definitions={},
                  note=f"Power-board mounting hole {i + 1}/6, M4 x 15 mm standoff on the PE-bonded baseplate")
        for i in range(4):
            c.add("H", "M3 standoff", "MountingHole:MountingHole_3.2mm_M3", {}, page=page, kind="H", definitions={},
                  note=f"Control-board standoff hole {i + 1}/4 (stack ~11 mm) on the SELV strip")
    with c.block("test_points", "Bare-PCB test pads (SELV signals)"):
        for net in ("3V3", "GND_CTRL", "GND_CTRL", "PWM_H_F", "PWM_L_F", "FAULT_N", "ISENSE", "VIN_SENSE", "VOUT_SENSE"):
            testpoint(c, net, page)
        for net in ("SPARE_D1", "SPARE_D2"):
            testpoint(c, net, page, note="A-P9: spare mezzanine line terminated on a test pad")


def build() -> Circuit:
    """Deterministic power-board part list."""
    c = Circuit(BOARD)
    power_stage(c)
    gate_channel(c, "H", "L", "VIN", "02_gate_driver_hs", q_ref="Q1", u_ref="U1", bias_ref="U2")
    gate_channel(c, "L", "H", "SW", "03_gate_driver_ls", q_ref="Q2", u_ref="U3", bias_ref="U4")
    sensing_island(c)
    selv_strip(c)
    mechanical(c)
    return c


def nets_of(parts) -> set[str]:
    return {n for p in parts for n in p["nets"].values() if n}


def summary(parts) -> dict:
    pages = {}
    for p in parts:
        pages[p["page"]] = pages.get(p["page"], 0) + 1
    return dict(parts=len(parts), nets=len(nets_of(parts)), dnp=sum(1 for p in parts if p.get("dnp")), pages=pages,
                custom_footprints=sorted(CUSTOM_FOOTPRINTS), flag_nets=list(FLAG_NETS))


def write_model() -> Circuit:
    """Write design/circuit_power.json and components/bom_power.csv; returns the built circuit."""
    circuit = build()
    parts = circuit.parts
    CIRCUIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    BOM_CSV.parent.mkdir(parents=True, exist_ok=True)
    CIRCUIT_JSON.write_text(json.dumps(parts, indent=2) + "\n", encoding="utf-8")
    fields = ["reference", "value", "manufacturer", "mpn", "footprint", "datasheet", "dnp", "note"]
    with BOM_CSV.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for p in parts:
            writer.writerow(dict(reference=p["ref"], value=p["value"], manufacturer=p["maker"], mpn=p["mpn"], footprint=p["footprint"],
                                 datasheet=p["source"], dnp="yes" if p.get("dnp") else "no", note=p["note"]))
    s = summary(parts)
    print(f"{BANNER}\nPower-board model: {s['parts']} parts ({s['dnp']} DNP), {s['nets']} nets; pages {s['pages']}")
    return circuit


if __name__ == "__main__":
    write_model()
