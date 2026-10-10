"""Electrical model of the V2 SiC buck CONTROL BOARD (board = "control").

AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED

Scope
-----
TMS320F28335 control board of the 400 V (360-440 V) -> 200 V / 25 A / 5 kW / 50 kHz SiC
synchronous buck: 12 V entry with TPS26400 eFuse, 5 V buck, dual LDO with core-first
sequencing, 5 V supervisor, the DSP with clock / boot / JTAG / UART, PWM gating, fault latch
and AND combiners, protection comparators, ADC front ends, heatsink-NTC readout, LEDs, the
2 x 25 mezzanine header, test points and mounting holes. The board is entirely SELV; every HV,
driver-island and sensing-island net (VIN_RAW, VIN, SW, VOUT_L, VOUT, PGND, G_H/KS_H/VDD_H/
VEE_H/DESAT_H_*, G_L/KS_L/VDD_L/VEE_L/DESAT_L_*, 5V_ISO, ISO_15V, VIN_DIV, VOUT_DIV, PE,
K1_LOW, VOC_SET, REF2V5_PB) lives on the power board (sic_buck_power_model.py).

Source of truth: examples/sic-buck-400v-200v-5kw/design/design_decisions.json (schema 2).
Where it is silent, design/research/controller_aux_interconnect.json is used after the
required_changes of verify_controller_auxiliary_supplies_pwm_fault__{engineering,factcheck}.json
(TPS3808 top resistor 101 k, R_ILIM 6.04 k / I_CB basis, pull resistors on GPIO0-11 nets,
SN74LV21A tpd 12 ns verified, 1 k + 1 nF ADC front ends harmonised with the sensing agent).
Everything added beyond those records is listed in ADDED_ASSUMPTIONS with its basis.
Knowledge applied (see the research record for the full trace): SKILL-001 principle 1 and 9
(SELV control domain, latched fault, applied directly), KR-PR-002 (latched combined fault with
power-on lock-out, direct), KR-PR-003 / CB-PR-001 (eFuse pattern, adapted: ladder and I_CB
re-derived), KR-GD-008 / KR-GD-009 (buffered single-ended PWM over a short mezzanine with the
interlock on the power board, adapted), KR-SN-005 (OC_N straight to TZ2, direct), KR-TH-003
(NTC = cooling supervision, human review), PE-PCB-007 / PE-PCB-008 (SELV grouping and local
100 nF decoupling, direct), REF-TI-TIDA-010054 decision 8 (aux eFuse, method only).

Nets
----
SELV power: 12V_IN (connector side of the eFuse, PWR_FLAG); EFUSE_RTN (TPS26400 RTN reference,
never tied to GND_CTRL - SLVSFQ6A 9.3.5.5); 12V_PROT (eFuse output, mezzanine pins 1-3); 5V
(TPS54302 output, PWR_FLAG); 5V_SW, 5V_BST; 1V9 (DSP core) and 1V9_BULK; 3V3 (I/O, logic,
mezzanine pins 39-40) and 3V3_BULK; REF2V5 (REF3125); REF3V0 (REF3130, NTC pull-up and OTP
reference); GND_CTRL (PWR_FLAG; all 24 mezzanine ground pins).
eFuse / supply control: EFUSE_UVLO, EFUSE_OVP (107 k / 4.42 k / 10.0 k ladder nodes), EFUSE_ILIM
(6.04 k), EFUSE_DVDT (100 nF), EFUSE_SHDN (100 k to 12V_IN), I12V_MON (IMON x 14.7 k),
V12V_MON (150 k / 33.2 k), FLT_12V_N; 5V_EN, 5V_FB; FB19, CORE_OK (1RESET_N), SEQ_BASE, IO_EN_N,
MON5 (101 k / 10 k), RESET_CT, MR_N, XRS_N.
DSP digital: EPWM1A, EPWM1B (GPIO0/1 before the AND gates, 10 k pull-downs); PWM_H_G, PWM_L_G
(gate outputs); PWM_H, PWM_L (after 33 ohm, mezzanine 14 / 17; the power board adds the
100 ohm + 100 pF + 10 k and names the filtered nets PWM_H_F / PWM_L_F); ARM (GPIO2, 10 k
pull-down); RELAY_ON, RESET_N, BIAS_EN (pull-downs on the power board); DSP_TRIP_N (10 k
pull-up); FLT_H_N, FLT_L_N, RDY_H, RDY_L, OC_N (open-drain from the power board, 10 k pull-ups);
PG_BIAS_H_N, PG_BIAS_L_N, PG_BIAS_S_N (raw UCC14141-Q1 PG, open-drain, LOW = good, 10 k
pull-ups) and their inversions PG_BIAS_H_OK, PG_BIAS_L_OK, PG_BIAS_S_OK (HIGH = good) for the
AND combiner; ESTOP_N (10 k pull-down, J_ESTOP closes it to 3V3); OVP_IN_N, OVP_OUT_N, OTP_N
(comparator outputs, 10 k pull-ups); UVLO (comparator output, active-high under-voltage flag of
the baseline hysteresis network) and UVLO_N (inverted); G1_N, G2_N, G3_N (combiner stages);
FAULT_LATCH_N (-> CLR_N); FAULT_N (= ARMED, latch Q, TZ1, mezzanine 35); OVP_N (GPIO11); GATE_EN
(run permit); LED_RUN, LED_FAULT; FAN_TACH (10 k pull-up); SPARE_D1, SPARE_D2; UART_RX, UART_TX;
CLK30_SOURCE, CLK30; BOOT84-BOOT87; TDI, TDO, TRST, TMS, TCK, EMU0, EMU1.
Analogue: VIN_SENSE, VOUT_SENSE, ISENSE, ISENSE_REF (mezzanine 47 / 49 / 43 / 45, 0-3 V single
ended); TEMP_HS_NTC (J_NTC, 2.2 k to REF3V0); TEMP_CTRL (LM61); filtered ADC pin nets ADC_VIN,
ADC_VOUT, ADC_ISENSE, ADC_ISENSE_REF, ADC_V12V, ADC_I12V, ADC_TEMP_HS, ADC_TEMP_CTRL (1 k + 1 nF);
references OVP_IN_REF (2.2917 V), OVP_OUT_REF (2.2825 V), UVLO_REF (1.641 V), OTP_REF (0.708 V);
ADCREFP, ADCREFM, ADCRESEXT.
Indicators: LED_12V_A, LED_ARMED_A, LED_RUN_A, LED_FAULT_A (anode nodes after the resistors).

Footprints: every part uses an installed KiCad 10 library footprint (pad numbers checked with
project_footprints.footprint_pads); no custom footprint is needed on this board, so
CUSTOM_FOOTPRINTS is empty. Pin numbering of every IC comes from the manufacturer pin table
named in PINOUT_SOURCES together with its verification level.
"""
from __future__ import annotations

import csv
import json

from automation.kicad_tools.sic_buck_common import (BANNER, CONTROL_NAME, EXAMPLE, PASSIVE_CAPS, Circuit, decisions,
                                                    mezzanine_net, pin_defs)

BOARD = "control"
PROJECT = CONTROL_NAME
GND = "GND_CTRL"
MODEL_JSON = EXAMPLE / "design/circuit_control.json"
BOM_CSV = EXAMPLE / "components/bom_control.csv"
DSP_CSV = EXAMPLE / "components/tms320f28335_pgf_pins.csv"

PAGES = {
    "01_aux_12v": "12 V entry, TVS and TPS26400 eFuse",
    "02_supplies": "5 V buck, dual LDO, supervisor and reset",
    "03_dsp": "TMS320F28335 - all 176 pins",
    "04_dsp_decoupling": "DSP per-pin bypass and ADC reference",
    "05_clock_debug": "Oscillator, boot straps, JTAG, UART",
    "06_pwm_fault_logic": "PWM gating, fault latch, combiners, comparators",
    "07_adc_frontend": "ADC conditioning, NTC readout, monitors",
    "08_interconnect": "Mezzanine header, connectors, LEDs, test points, mounting",
}

# Nets that need a PWR_FLAG for ERC: supplies that enter through a connector or an inductor.
FLAG_NETS = ["12V_IN", GND, "5V"]

# No custom footprint is required on the control board (all parts are installed KiCad 10 library parts).
CUSTOM_FOOTPRINTS: dict[str, tuple[str, list]] = {}

TI = "Texas Instruments"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SOT23_6 = "Package_TO_SOT_SMD:SOT-23-6"
SSOP8 = "Package_SO:SSOP-8_2.95x2.8mm_P0.65mm"
TSSOP14 = "Package_SO:TSSOP-14_4.4x5mm_P0.65mm"
VSSOP8 = "Package_SO:VSSOP-8_3x3mm_P0.65mm"
HTSSOP16 = "Package_SO:HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm"
HTSSOP28 = "Package_SO:HTSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP2.85x5.4mm"

# Pin tables: number:name:KiCad-type. The datasheet and verification level of every table is in PINOUT_SOURCES.
IC = {
    "TPS26400PWPR": (HTSSOP16, "1:IN:power_in 2:IN:power_in 3:UVLO:input 4:NC:no_connect 5:OVP:input 6:MODE:input "
                               "7:SHDN:input 8:RTN:passive 9:GND:power_in 10:IMON:output 11:ILIM:passive 12:dVdT:passive "
                               "13:NC:no_connect 14:FLT:open_collector 15:OUT:power_out 16:OUT:passive 17:PAD:passive",
                     "https://www.ti.com/lit/ds/symlink/tps2640.pdf", TI),
    "TPS54302DDCR": (SOT23_6, "1:GND:power_in 2:SW:power_out 3:VIN:power_in 4:FB:input 5:EN:input 6:BOOT:passive",
                     "https://www.ti.com/lit/ds/symlink/tps54302.pdf", TI),
    "TPS767D301PWPR": (HTSSOP28, "1:NC:no_connect 2:NC:no_connect 3:1GND:power_in 4:1EN_N:input 5:1IN:power_in 6:1IN:power_in "
                                 "7:NC:no_connect 8:NC:no_connect 9:2GND:power_in 10:2EN_N:input 11:2IN:power_in 12:2IN:power_in "
                                 "13:NC:no_connect 14:NC:no_connect 15:NC:no_connect 16:NC:no_connect 17:2OUT:power_out 18:2OUT:passive "
                                 "19:NC:no_connect 20:NC:no_connect 21:NC:no_connect 22:2RESET_N:open_collector 23:1OUT:power_out "
                                 "24:1OUT:passive 25:1FB:input 26:NC:no_connect 27:NC:no_connect 28:1RESET_N:open_collector 29:EP:power_in",
                       "https://www.ti.com/lit/ds/symlink/tps767d301.pdf", TI),
    "TPS3808G01DBVR": (SOT23_6, "1:RESET_N:open_collector 2:GND:power_in 3:MR_N:input 4:CT:passive 5:SENSE:input 6:VDD:power_in",
                       "https://www.ti.com/lit/ds/symlink/tps3808.pdf", TI),
    "SN74LVC1G74DCTR": (SSOP8, "1:CLK:input 2:D:input 3:Q_N:output 4:GND:power_in 5:Q:output 6:CLR_N:input 7:PRE_N:input 8:VCC:power_in",
                        "https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf", TI),
    "SN74LVC2G08DCTR": (SSOP8, "1:1A:input 2:1B:input 3:2Y:output 4:GND:power_in 5:2A:input 6:2B:input 7:1Y:output 8:VCC:power_in",
                        "https://www.ti.com/lit/ds/symlink/sn74lvc2g08.pdf", TI),
    "SN74LV21APWR": (TSSOP14, "1:1A:input 2:1B:input 3:NC:no_connect 4:1C:input 5:1D:input 6:1Y:output 7:GND:power_in "
                              "8:2Y:output 9:2A:input 10:2B:input 11:NC:no_connect 12:2C:input 13:2D:input 14:VCC:power_in",
                     "https://www.ti.com/lit/ds/symlink/sn74lv21a.pdf", TI),
    "SN74LV04APWR": (TSSOP14, "1:1A:input 2:1Y:output 3:2A:input 4:2Y:output 5:3A:input 6:3Y:output 7:GND:power_in "
                              "8:4Y:output 9:4A:input 10:5Y:output 11:5A:input 12:6Y:output 13:6A:input 14:VCC:power_in",
                     "https://www.ti.com/lit/ds/symlink/sn74lv04a.pdf", TI),
    "TLV1702AIDGKR": (VSSOP8, "1:1OUT:open_collector 2:1IN-:input 3:1IN+:input 4:V-:power_in 5:2IN+:input 6:2IN-:input "
                              "7:2OUT:open_collector 8:V+:power_in", "https://www.ti.com/lit/ds/symlink/tlv1702.pdf", TI),
    "REF3125AIDBZR": (SOT23, "1:IN:power_in 2:OUT:power_out 3:GND:power_in", "https://www.ti.com/lit/gpn/ref3125", TI),
    "REF3130AIDBZR": (SOT23, "1:IN:power_in 2:OUT:power_out 3:GND:power_in", "https://www.ti.com/lit/gpn/ref3130", TI),
    "LM61CIM3/NOPB": (SOT23, "1:+VS:power_in 2:VOUT:output 3:GND:power_in", "https://www.ti.com/lit/ds/symlink/lm61.pdf", TI),
    "MMBT3904,215": (SOT23, "1:B:input 2:E:passive 3:C:passive", "https://assets.nexperia.com/documents/data-sheet/MMBT3904.pdf", "Nexperia"),
    "BAT54,215": (SOT23, "1:A:passive 2:NC:no_connect 3:K:passive", "https://assets.nexperia.com/documents/data-sheet/BAT54_SER.pdf", "Nexperia"),
    "ASV-30.000MHZ-EJ-T": ("Oscillator:Oscillator_SMD_SeikoEpson_SG8002CA-4Pin_7.0x5.0mm",
                           "1:TRI:input 2:GND:power_in 3:OUT:output 4:VDD:power_in", "https://abracon.com/Oscillators/ASV.pdf", "Abracon"),
}

# Verification level of every pin table (never upgraded): fetched-datasheet means the manufacturer PDF or its
# text extraction was read in this run (or the repository cache .cache/datasheets of V1 was re-read).
PINOUT_SOURCES = {
    "TMS320F28335PGFA": "components/tms320f28335_pgf_pins.csv (TI SPRS439Q Table 6-1, PGF column); cached SPRS439Q text re-read for "
                        "ADCRESEXT (22 k to analog ground), XCLKIN with X1 grounded and X2 open, unused ADC inputs to analog ground - fetched-datasheet",
    "TPS26400PWPR": "TI SLVSFQ6A (Nov 2020, rev. Jun 2021) Table 6-1 HTSSOP column, PDF fetched and text-extracted - fetched-datasheet",
    "TPS54302DDCR": "TI SLVSDG6C (May 2016, rev. Mar 2026) Table 4-1 - fetched-datasheet (repository cache)",
    "TPS767D301PWPR": "TI SLVS209H (Jul 1999, rev. Aug 2008) Terminal Functions; EN is active low ('TTL high shuts down') - fetched-datasheet (repository cache)",
    "TPS3808G01DBVR": "TI SBVS050N (May 2004, rev. Aug 2026) Table 5-1; MR has a 90 k internal pull-up; VIT 0.405 V - fetched-datasheet (repository cache)",
    "SN74LVC1G74DCTR": "TI SCES794G (Oct 2009, rev. Sep 2021) Pin Functions, DCT = SM8 - fetched-datasheet (repository cache)",
    "SN74LVC2G08DCTR": "TI SCES198N (Apr 1999, rev. Dec 2015) Pin Functions - fetched-datasheet (repository cache)",
    "SN74LV21APWR": "TI SCES340F (Sep 2000, rev. Jul 2023) Table 4-1; tpd 12 ns max at 3.3 V / 50 pF - fetched-datasheet",
    "SN74LV04APWR": "TI SCLS388K (Sep 1997, rev. Dec 2014) Pin Functions; tpd 12 ns max at 3.3 V / 50 pF (13 ns at 125 C) - fetched-datasheet",
    "TLV1702AIDGKR": "TI SBOS589D (Dec 2013, rev. Jun 2015) Pin Functions DGK column; V_CM = V- to V+; tpd 560 ns - fetched-datasheet",
    "REF3125AIDBZR": "TI SBVS046E (Dec 2003, rev. Apr 2026) Table 5-1: 1 IN, 2 OUT, 3 GND; VIN >= VREF + 0.05 V - fetched-datasheet (repository cache)",
    "REF3130AIDBZR": "same SBVS046E family table as REF3125 - fetched-datasheet (repository cache)",
    "LM61CIM3/NOPB": "TI SNIS121J (Jun 1999, rev. Nov 2016) Pin Functions, DBZ: 1 +VS, 2 VOUT, 3 GND - fetched-datasheet (repository cache)",
    "MMBT3904,215": "Nexperia MMBT3904 product data sheet 8 Apr 2026 Table 2: 1 B, 2 E, 3 C - fetched-datasheet",
    "BAT54,215": "V1 declaration (1 A, 2 NC, 3 K) carried over; Nexperia BAT54 series sheet not re-fetched - unverified",
    "ASV-30.000MHZ-EJ-T": "Abracon ASV datasheet rev. 09.02.14 (repository cache): 1 Tri-state, 2 GND/case, 3 Output, 4 Vdd; "
                          "KiCad SG8002CA 7.0 x 5.0 mm land pattern reused, fit against the ASV drawing to confirm - fetched-datasheet (pins) / unverified (land pattern)",
    "SMBJ15CA": "bidirectional TVS, no polarity; Littelfuse datasheet not fetched (distributor data in the research record) - unverified",
    "LTST-C170KRKT / LTST-C170KGKT": "2-pad LED; model pad 1 = cathode (KiCad LED footprint convention); Lite-On polarity mark to be checked at layout - unverified",
    "connectors and passives": "two-pad or sequential pin numbering from the KiCad library footprints - analytically-checked",
}

# Passives that the shared table does not carry (real orderable parts; verification level in the note).
CONTROL_CAPS = {
    "56p/50V/0603": dict(footprint="Capacitor_SMD:C_0603_1608Metric", mpn="GRM1885C1H560JA01D", maker="Murata",
                         source="https://www.murata.com/en-us/products/productdetail?partno=GRM1885C1H560JA01%23",
                         note="C0G 5 %; distributor listings found (search-snippet), one lists NRND - check lifecycle"),
    "220u/16V/radial": dict(footprint="Capacitor_THT:CP_Radial_D6.3mm_P2.50mm", mpn="EEU-FR1C221", maker="Panasonic",
                            source="https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models/EEUFR1C221",
                            note="6.3 x 11.2 mm, pitch 2.5 mm, 455 mA ripple, 5000 h at 105 C (distributor data, search-snippet)"),
    "100u/6.3V/polymer": dict(footprint="Capacitor_SMD:CP_Elec_6.3x5.9", mpn="6SVP100M", maker="Panasonic",
                              source="https://industrial.panasonic.com/ww/products/pt/os-con/models/6SVP100M",
                              note="OS-CON SVP 6.3 x 5.9 mm, 40 mohm (distributor data, search-snippet)"),
}
R_SHUNT_0R1 = dict(mpn="RL0805FR-070R1L", maker="Yageo",
                   source="https://www.yageogroup.com/component-documentation/download/specsheet/RL0805FR-070R1L")

# DSP nets: net -> (PGF pin, name expected in components/tms320f28335_pgf_pins.csv). Checked at build time.
DSP_PINS = {
    "EPWM1A": (5, "GPIO0"), "EPWM1B": (6, "GPIO1"), "ARM": (7, "GPIO2"), "RELAY_ON": (10, "GPIO3"), "RESET_N": (11, "GPIO4"),
    "BIAS_EN": (12, "GPIO5"), "DSP_TRIP_N": (13, "GPIO6"), "FLT_H_N": (16, "GPIO7"), "FLT_L_N": (17, "GPIO8"), "RDY_H": (18, "GPIO9"),
    "RDY_L": (19, "GPIO10"), "OVP_N": (20, "GPIO11"), "FAULT_N": (21, "GPIO12"), "OC_N": (24, "GPIO13"), "UVLO_N": (25, "GPIO14"),
    "OTP_N": (26, "GPIO15"), "FLT_12V_N": (27, "GPIO16"), "PG_BIAS_H_N": (28, "GPIO17"), "PG_BIAS_L_N": (62, "GPIO18"),
    "ESTOP_N": (63, "GPIO19"), "PG_BIAS_S_N": (64, "GPIO20"), "LED_RUN": (65, "GPIO21"), "LED_FAULT": (66, "GPIO22"),
    "FAN_TACH": (68, "GPIO24"), "SPARE_D1": (72, "GPIO26"), "SPARE_D2": (73, "GPIO27"), "UART_RX": (141, "GPIO28"), "UART_TX": (2, "GPIO29"),
    "ADC_VIN": (42, "ADCINA0"), "ADC_ISENSE": (41, "ADCINA1"), "ADC_TEMP_HS": (40, "ADCINA2"), "ADC_TEMP_CTRL": (39, "ADCINA3"),
    "ADC_ISENSE_REF": (38, "ADCINA4"), "ADC_I12V": (46, "ADCINB0"), "ADC_VOUT": (47, "ADCINB1"), "ADC_V12V": (49, "ADCINB3"),
    "ADCREFM": (55, "ADCREFM"), "ADCREFP": (56, "ADCREFP"), "ADCRESEXT": (57, "ADCRESEXT"),
    "TDI": (76, "TDI"), "TDO": (77, "TDO"), "TRST": (78, "TRST"), "TMS": (79, "TMS"), "XRS_N": (80, "XRS"), "EMU0": (85, "EMU0"),
    "EMU1": (86, "EMU1"), "TCK": (87, "TCK"), "CLK30": (105, "XCLKIN"),
    "BOOT84": (169, "GPIO84"), "BOOT85": (172, "GPIO85"), "BOOT86": (173, "GPIO86"), "BOOT87": (174, "GPIO87"),
}
# First token of each baseline dsp_pin_map label -> net of this model (signal names differ where the model needs
# the physical node: the DSP sees ePWM before the AND gates and the ADC pins after the 1 k + 1 nF filters).
BASELINE_SIGNAL_NET = {
    "PWM_H": "EPWM1A", "PWM_L": "EPWM1B", "VIN_SENSE": "ADC_VIN", "ISENSE": "ADC_ISENSE", "TEMP_HS_NTC": "ADC_TEMP_HS",
    "TEMP_CTRL": "ADC_TEMP_CTRL", "ISENSE_REF": "ADC_ISENSE_REF", "I12V_MON": "ADC_I12V", "VOUT_SENSE": "ADC_VOUT", "V12V_MON": "ADC_V12V",
}

ADDED_ASSUMPTIONS = [
    ("A-C1", "TPS26400 SHDN pulled to 12V_IN through 100 k", "SLVSFQ6A 9.3.5.7: SHDN must be >= 1 V to enable; abs max SHDN-to-RTN 45 V; a resistor keeps a GPIO shutdown option open"),
    ("A-C2", "100 nF ceramic at the TPS26400 IN pin", "SLVSFQ6A 10.2.2.4.3 recommends 0.1-1 uF C(IN)"),
    ("A-C3", "TPS26400 RTN is its own net EFUSE_RTN with ladder, R_ILIM, C_dVdT, R_IMON and PowerPad on it; GND pin to GND_CTRL",
     "SLVSFQ6A 9.3.5.5 / 10.4: connecting RTN to GND disables the reverse-polarity protection and damages the device under that fault"),
    ("A-C4", "10 uF 1210 + 100 nF at the TPS54302 VIN pin (the baseline's 10 uF companion of the 100 uF bulk placed there)", "SLVSDG6C 7.2.3.1: >= 10 uF ceramic decoupling, optional 0.1 uF"),
    ("A-C5", "1 uF at IN and 1 uF at OUT of REF3125 and REF3130", "SBVS046E 8.1: 0.47 uF supply bypass recommended, stable with any load capacitance"),
    ("A-C6", "UVLO comparator output is the active-high under-voltage flag of the baseline network (reference 1.00 k / 1.91 k on IN+, 21.5 k from OUT to that node, VIN_SENSE on IN-); SN74LV04A inverts it to UVLO_N",
     "verify_sensing_protection_..._engineering.json: hysteresis works only with the threshold on IN+ -> active-high flag; thresholds with the 10 k pull-up: 1.675 V / 1.592 V = 336 V on / 319.5 V off (339 V on with an ideal 3.3 V source) - simulation item"),
    ("A-C7", "PG_BIAS_H_N / PG_BIAS_L_N / PG_BIAS_S_N are inverted (SN74LV04A) before the AND combiner; the DSP reads the raw lines",
     "SLUSF10B via gate_driver.json: UCC14141-Q1 PG is open-drain, LOW = all rails within the UVP/OVP windows; an AND combiner needs HIGH = good"),
    ("A-C8", "10 k pull-up to 3V3 on FAN_TACH", "open-collector tachometer assumed; the Fischer LAM 5 D K fan data were not accessible (baseline open item)"),
    ("A-C9", "J_RESET on the TPS3808 MR_N pin instead of directly on XRS_N", "SBVS050N: MR has a 90 k internal pull-up and restarts the delay; CT 10 nF -> t_D = 10/175 + 0.5 ms = 57.6 ms (Eq. 1)"),
    ("A-C10", "TLV1702 comparators supplied from 3V3", "SBOS589D: V_CM = V- to V+ (rail-to-rail inputs), 2.2-36 V supply; outputs pulled up to 3V3"),
    ("A-C11", "comparator threshold dividers in 1 % thick film (Yageo RC0603)", "baseline gives values only; +/-1 % resistors move OVP_IN by about +/-2.3 V (0.5 %) - tolerance budget is a review item"),
    ("A-C12", "no capacitor on the UVLO reference node (its footprint is kept DNP); 100 nF on the other threshold nodes", "a capacitor on the positive-feedback node delays the hysteresis step; V1 pattern kept where no feedback exists"),
    ("A-C13", "LED currents 2.1 mA (12V_OK, 4.7 k from 12V_PROT) and about 0.9 mA (3.3 V logic LEDs, 1.5 k)", "baseline resistor values; Lite-On 2.0 V forward voltage from distributor data - brightness review"),
    ("A-C14", "VDDA2 / VDDAIO / VDD3VFL tied to 3V3 with 100 nF per pin, no ferrite bead", "V1 pattern; SPRS439Q lists them as 3.3 V supplies - analogue-supply filtering is a review item"),
    ("A-C15", "0.1 ohm (Yageo RL0805) in series with a 100 uF polymer per LDO rail plus the 2.2 uF ceramics", "V1 pattern; SLVS209H requires >= 10 uF low-ESR output capacitance, the exact ESR window was not re-read - review"),
    ("A-C16", "56 pF feed-forward across the 100 k FB resistor of the TPS54302", "baseline / V1 value; SLVSDG6C Table 7-2 lists 75 pF for the 5 V design - minor, review"),
    ("A-C17", "unused ADC inputs and ADCREFIN tied to GND_CTRL, X1 grounded, X2 and unused GPIO left open with no-connect flags", "SPRS439Q pin table and 'unused pins' guidance"),
    ("A-C18", "unused SN74LV04A inputs to GND_CTRL, outputs no-connect", "TI unused-input guidance for LV logic"),
    ("A-C19", "SMBJ15CA source: Littelfuse product page; Samtec, Phoenix 1715022, Lite-On and Coilcraft parts cited from manufacturer pages", "distributor-level data for the TVS (research record), manufacturer pages for the others"),
]


def _ic(c: Circuit, mpn: str, nets: dict, page: str, *, note: str = "", ref: str | None = None, prefix: str = "U", symbol: str | None = None):
    footprint, declaration, source, maker = IC[mpn]
    defs = pin_defs(declaration)
    nets = {str(k): v for k, v in nets.items()}
    for n, p in defs.items():
        if p["type"] == "no_connect":
            nets.setdefault(n, None)
    missing = sorted(set(defs) - set(nets), key=int)
    if missing:
        raise KeyError(f"{mpn}: pins without a net {missing}")
    part = c.add(prefix, mpn, footprint, nets, page=page, kind="IC", mpn=mpn, maker=maker, source=source, definitions=defs, note=note, ref=ref)
    if symbol:
        part["symbol"] = symbol
    return part


def _cap(c: Circuit, key: str, a, b, page: str, *, note: str = "", dnp: bool = False):
    if key in PASSIVE_CAPS:
        return c.cap(key, a, b, page, note=note, dnp=dnp)
    spec = CONTROL_CAPS[key]
    return c.add("C", key.rsplit("/", 1)[0], spec["footprint"], {1: a, 2: b}, page=page, kind="C", mpn=spec["mpn"], maker=spec["maker"],
                 source=spec["source"], note=note or spec["note"], dnp=dnp)


def _led(c: Circuit, colour: str, anode, cathode, page: str, note: str):
    mpn = {"red": "LTST-C170KRKT", "green": "LTST-C170KGKT"}[colour]
    url = {"red": "https://optoelectronics.liteon.com/upload/download/DS-22-99-0150/LTST-C170KRKT.pdf",
           "green": "https://optoelectronics.liteon.com/upload/download/DS22-2000-073/LTST-C170KGKT.pdf"}[colour]
    part = c.add("D", f"LED {colour}", "LED_SMD:LED_0805_2012Metric", {1: cathode, 2: anode}, page=page, kind="D", mpn=mpn, maker="Lite-On",
                 source=url, definitions=pin_defs("1:K:passive 2:A:passive"), note=note)
    part["symbol"] = "Device:LED"
    return part


def _pullup(c: Circuit, net: str, page: str, value: str = "10k", note: str = ""):
    return c.resistor(value, "3V3", net, page, note=note)


def _adc_rc(c: Circuit, source: str, adc: str, page: str, note: str):
    c.resistor("1k", source, adc, page, note=f"ADC front end {note}")
    _cap(c, "1n/50V/0603", adc, GND, page, note=f"ADC front end {note}; 1 k + 1 nF per baseline")


def dsp_pins() -> tuple[dict, dict]:
    """Pin definitions and default nets of the F28335 from the verified CSV; the DSP_PINS map is asserted against it."""
    defs, nets = {}, {}
    with DSP_CSV.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 176:
        raise ValueError(f"expected 176 PGF pins, found {len(rows)}")
    for row in rows:
        n, name = row["pin"], row["name"]
        kind = "bidirectional" if name.startswith("GPIO") or name in ("EMU0", "EMU1") else "input"
        if name.startswith(("VDD", "VSS")):
            kind = "power_in"
        if name in ("TEST1", "TEST2"):
            kind = "no_connect"
        if name in ("X2", "XRD", "XCLKOUT", "ADCREFP", "ADCREFM", "TDO"):
            kind = "output"
        if name == "XRS":
            kind = "open_collector"
        defs[n] = dict(name=name, type=kind)
        net = None
        if name in ("VDD", "VDD1A18", "VDD2A18"):
            net = "1V9"
        elif name.startswith("VDD"):
            net = "3V3"
        elif name.startswith("VSS") or name in ("ADCLO", "ADCREFIN", "X1") or name.startswith("ADCIN"):
            net = GND  # SPRS439Q: unused ADC inputs and ADCREFIN to analog ground; X1 grounded with a 3.3 V oscillator on XCLKIN
        nets[n] = net
    for net, (pin, expected) in DSP_PINS.items():
        actual = defs[str(pin)]["name"]
        if actual != expected:
            raise ValueError(f"DSP pin {pin} is {actual} in the CSV, model expects {expected} for {net}")
        nets[str(pin)] = net
    for label, pin, _function in decisions()["controller"]["dsp_pin_map"]:
        token = label.split()[0]
        net = BASELINE_SIGNAL_NET.get(token, token)
        if DSP_PINS[net][0] != pin:
            raise ValueError(f"baseline maps {label} to pin {pin}, model uses pin {DSP_PINS[net][0]}")
    return defs, nets


def build() -> Circuit:
    c = Circuit(BOARD)

    # ---- 01 12 V entry, TVS and eFuse ------------------------------------------------------------------------
    p = "01_aux_12v"
    c.add("J", "12 V in", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal", {1: "12V_IN", 2: GND}, page=p, kind="J",
          mpn="1715022", maker="Phoenix Contact", source="https://www.phoenixcontact.com/en-pc/products/pcb-terminal-block-mkds-15-2-508-1715022",
          note="J_12V: external regulated 12 V +/-10 %, 2.5 A recommended; pin 1 +12 V, pin 2 return")
    c.add("D", "SMBJ15CA", "Diode_SMD:D_SMB", {1: "12V_IN", 2: GND}, page=p, kind="D", mpn="SMBJ15CA", maker="Littelfuse",
          source="https://www.littelfuse.com/products/tvs-diodes/surface-mount/smbj/smbj15ca", definitions=pin_defs("1:A1:passive 2:A2:passive"),
          note="bidirectional TVS 15 V standoff, V_BR 16.7-18.5 V > eFuse OVP 15.2 V max, V_C 24.4 V < 45 V abs max (distributor data, unverified)")
    _ic(c, "TPS26400PWPR", {1: "12V_IN", 2: "12V_IN", 3: "EFUSE_UVLO", 5: "EFUSE_OVP", 6: None, 7: "EFUSE_SHDN", 8: "EFUSE_RTN", 9: GND, 10: "I12V_MON",
                            11: "EFUSE_ILIM", 12: "EFUSE_DVDT", 14: "FLT_12V_N", 15: "12V_PROT", 16: "12V_PROT", 17: "EFUSE_RTN"}, p,
        note="eFuse, MODE open = circuit breaker with 4 ms timeout and 540 ms auto-retry (CR-18); RTN separate from GND (A-C3); PowerPad on RTN")
    _cap(c, "100n/50V/0603", "12V_IN", GND, p, note="C(IN) local bypass (A-C2)")
    c.resistor("107k", "12V_IN", "EFUSE_UVLO", p, note="ladder R1: UVLO 10.02 V rising / 9.26 V falling")
    c.resistor("4.42k", "EFUSE_UVLO", "EFUSE_OVP", p, note="ladder R2: OVP 14.45 V rising / 13.36 V falling")
    c.resistor("10k", "EFUSE_OVP", "EFUSE_RTN", p, note="ladder R3 to RTN")
    c.resistor("6.04k", "EFUSE_ILIM", "EFUSE_RTN", p, note="R_ILIM: I_CB = 12/6.04 - 0.03 = 1.96 A (CR-02); I_OL about 1.99 A")
    _cap(c, "100n/50V/0603", "EFUSE_DVDT", "EFUSE_RTN", p, note="C_dVdT: 8.9-12.2 ms output ramp at 12 V (verified dVdT relation)")
    c.resistor("14.7k", "I12V_MON", "EFUSE_RTN", p, note="R_IMON: 3.0 V at 2.4 A with 85 uA/A; no capacitor on IMON (datasheet)")
    c.resistor("100k", "12V_IN", "EFUSE_SHDN", p, note="SHDN enable pull-up (A-C1)")
    _pullup(c, "FLT_12V_N", p, note="RFLTb 10 k (10-100 k allowed); FLT_12V_N -> GPIO16 and latched fault group")
    _cap(c, "100u/25V/elec", "12V_PROT", GND, p, note="protected-rail bulk 100 uF (baseline); EEE-FK1E101P 25 V")
    c.resistor("150k", "12V_PROT", "V12V_MON", p, note="V12 monitor divider top: 0.1812 ratio, 3.0 V at 16.55 V")
    c.resistor("33.2k", "V12V_MON", GND, p, note="V12 monitor divider bottom")

    # ---- 02 5 V buck, dual LDO, supervisor -------------------------------------------------------------------
    p = "02_supplies"
    _ic(c, "TPS54302DDCR", {1: GND, 2: "5V_SW", 3: "12V_PROT", 4: "5V_FB", 5: "5V_EN", 6: "5V_BST"}, p,
        note="12V_PROT -> 5 V, 400 kHz, I_5V 0.54 A; VFB 0.596 V; EN 1.23 V rising")
    _cap(c, "10u/25V/1210", "12V_PROT", GND, p, note="buck input decoupling >= 10 uF ceramic (A-C4; the baseline's 10 uF)")
    _cap(c, "100n/50V/0603", "12V_PROT", GND, p, note="buck input HF bypass (A-C4)")
    c.resistor("100k", "12V_PROT", "5V_EN", p, note="EN divider top: start about 7.4 V")
    c.resistor("20k", "5V_EN", GND, p, note="EN divider bottom")
    _cap(c, "100n/50V/0603", "5V_BST", "5V_SW", p, note="BOOT capacitor 0.1 uF (SLVSDG6C 7.2.3.2)")
    c.add("L", "10uH", "Inductor_SMD:L_Coilcraft_MSS1048-XXX", {1: "5V_SW", 2: "5V"}, page=p, kind="L", mpn="MSS1048-103MLC", maker="Coilcraft",
          source="https://www.coilcraft.com/en-us/products/power/shielded-inductors/ferrite-drum/mss-mos/mss1048/mss1048-103/",
          note="10 uH shielded (baseline, V1); ripple about 0.6 A pp at 12 V in")
    for _ in range(2):
        _cap(c, "22u/25V/1210", "5V", GND, p, note="5 V output ceramic (2 x 22 uF)")
    _cap(c, "220u/16V/radial", "5V", GND, p, note="5 V bulk / hold-up: power-down reset margin 1.1 ms >> 8 us (verified)")
    c.resistor("100k", "5V", "5V_FB", p, note="FB divider top: 0.596 V x 113.3/13.3 = 5.08 V")
    c.resistor("13.3k", "5V_FB", GND, p, note="FB divider bottom")
    _cap(c, "56p/50V/0603", "5V", "5V_FB", p, note="feed-forward across the 100 k (A-C16)")
    _ic(c, "TPS767D301PWPR", {3: GND, 4: GND, 5: "5V", 6: "5V", 9: GND, 10: "IO_EN_N", 11: "5V", 12: "5V", 17: "3V3", 18: "3V3", 22: "XRS_N",
                              23: "1V9", 24: "1V9", 25: "FB19", 28: "CORE_OK", 29: GND}, p,
        note="dual LDO: 1 = 1.9 V adjustable core (always enabled), 2 = 3.3 V fixed enabled after core RESET1 (core-first); P_LDO 1.39 W; "
             "commercial part ACTIVE, -EP NRND, TLV752 named alternative (baseline)")
    c.resistor("18.2k", "1V9", "FB19", p, note="1V9 set point: 1.1834 V x (1 + 18.2/30.1) = 1.899 V")
    c.resistor("30.1k", "FB19", GND, p, note="1V9 divider bottom (40 uA divider current per SLVS209H)")
    c.resistor("10k", "5V", "CORE_OK", p, note="1RESET_N open-drain pull-up")
    c.resistor("10k", "5V", "IO_EN_N", p, note="2EN_N pull-up: 3.3 V regulator off until the core is good")
    c.resistor("10k", "CORE_OK", "SEQ_BASE", p, note="sequencer base resistor")
    c.resistor("100k", "SEQ_BASE", GND, p, note="sequencer base pull-down")
    _ic(c, "MMBT3904,215", {1: "SEQ_BASE", 2: GND, 3: "IO_EN_N"}, p, prefix="Q", symbol="Transistor_BJT:Q_NPN_BEC",
        note="core-first sequencer: CORE_OK high -> 2EN_N low -> 3.3 V enabled (V1 pattern)")
    _ic(c, "BAT54,215", {1: "XRS_N", 3: "CORE_OK"}, p, prefix="D", note="core failure (1RESET_N low) asserts XRS_N (V1 pattern); anode XRS_N, cathode CORE_OK")
    for rail in ("1V9", "3V3"):
        c.resistor("0.1", rail, rail + "_BULK", p, package="0805", note=f"explicit ESR for the {rail} polymer output capacitor (A-C15)", **R_SHUNT_0R1)
        _cap(c, "100u/6.3V/polymer", rail + "_BULK", GND, p, note=f"{rail} LDO output bulk, low-ESR polymer behind 0.1 ohm (A-C15)")
    _cap(c, "100n/50V/0603", "5V", GND, p, note="LDO input HF bypass")
    _cap(c, "22u/25V/1210", "5V", GND, p, note="LDO input bulk (V1 pattern)")
    _ic(c, "TPS3808G01DBVR", {1: "XRS_N", 2: GND, 3: "MR_N", 4: "RESET_CT", 5: "MON5", 6: "3V3"}, p,
        note="5 V supervisor: SENSE 101 k / 10 k -> 4.4955 V (CR-18); CT 10 nF -> 57.6 ms; RESET open drain to XRS_N")
    c.resistor("101k", "5V", "MON5", p, note="supervisor divider top (CR-18: 105 k would trip at 4.66 V)")
    c.resistor("10k", "MON5", GND, p, note="supervisor divider bottom")
    _cap(c, "10n/50V/0603", "RESET_CT", GND, p, note="reset delay capacitor: t_D = (10 nF / 175) + 0.5 ms = 57.6 ms (SBVS050N Eq. 1)")
    _cap(c, "100n/50V/0603", "3V3", GND, p, note="TPS3808 VDD bypass")
    _pullup(c, "XRS_N", p, note="XRS_N wired-OR pull-up (TPS3808 RESET, LDO 2RESET, DSP XRS, BAT54 from CORE_OK)")
    c.header(2, {1: "MR_N", 2: GND}, p, note="J_RESET: manual reset through the supervisor MR pin (A-C9)")

    # ---- 03 DSP -------------------------------------------------------------------------------------------
    defs, nets = dsp_pins()
    c.add("U", "TMS320F28335PGFA", "Package_QFP:LQFP-176_24x24mm_P0.5mm", nets, page="03_dsp", kind="DSP", mpn="TMS320F28335PGFA", maker=TI,
          source="https://www.ti.com/lit/ds/symlink/tms320f28335.pdf", definitions=defs,
          note="150 MHz; ePWM1A/1B on GPIO0/1; TZ1 = FAULT_N (GPIO12), TZ2 = OC_N (GPIO13); ADC 0-3 V; pin map per design_decisions.json controller.dsp_pin_map")

    # ---- 04 DSP decoupling --------------------------------------------------------------------------------
    p = "04_dsp_decoupling"
    for n, net in nets.items():
        if defs[n]["name"].startswith("VDD"):
            cap = _cap(c, "100n/50V/0603", net, GND, p, note=f"DSP pin {n} {defs[n]['name']}; place at the pin")
            cap["near_dsp_pin"] = n
    for net in ("1V9", "1V9", "3V3", "3V3"):
        _cap(c, "2.2u/25V/0805", net, GND, p, note=f"{net} rail bulk ceramic at the DSP")
    for net in ("ADCREFM", "ADCREFP"):
        _cap(c, "2.2u/25V/0805", net, GND, p, note="ADC reference low-ESR bypass (SPRS439Q)")
    c.resistor("22k", "ADCRESEXT", GND, p, note="ADC external current bias resistor, 22 k to analog ground (SPRS439Q pin table)")

    # ---- 05 clock, boot, JTAG, UART -----------------------------------------------------------------------
    p = "05_clock_debug"
    _ic(c, "ASV-30.000MHZ-EJ-T", {1: "3V3", 2: GND, 3: "CLK30_SOURCE", 4: "3V3"}, p, prefix="Y",
        note="30 MHz 3.3 V HCMOS oscillator on XCLKIN (X1 grounded, X2 open); tri-state pin high = oscillating")
    _cap(c, "100n/50V/0603", "3V3", GND, p, note="oscillator Vdd bypass")
    c.resistor("33", "CLK30_SOURCE", "CLK30", p, note="clock series termination")
    for net in ("BOOT84", "BOOT85", "BOOT86", "BOOT87", "EMU0", "EMU1", "TMS", "TDI"):
        c.resistor("4.7k", "3V3", net, p, note="boot strap / JTAG pull-up (1111 = jump to flash)")
    c.resistor("2.2k", "TRST", GND, p, note="TRST pull-down (JTAG inactive without an emulator)")
    c.resistor("10k", "TCK", GND, p, note="TCK pull-down")
    c.header(14, {1: "TMS", 2: "TRST", 3: "TDI", 4: GND, 5: "3V3", 6: None, 7: "TDO", 8: GND, 9: "TCK", 10: GND, 11: "TCK", 12: GND, 13: "EMU0", 14: "EMU1"}, p,
             note="J_JTAG: TI 14-pin, key pin 6 absent; TCK_RET tied to TCK; pin 4 TDIS to ground", rows=2)
    c.header(3, {1: GND, 2: "BOOT84", 3: "3V3"}, p, note="J_BOOT: jumper 1-2 = SCI-A boot, 2-3 or open = flash")
    c.header(3, {1: "UART_TX", 2: "UART_RX", 3: GND}, p, note="J_UART: SCI-A, 3.3 V levels only")
    _pullup(c, "UART_RX", p, note="SCI-A RX idle high")

    # ---- 06 PWM gating, latch, combiners, comparators -----------------------------------------------------
    p = "06_pwm_fault_logic"
    _ic(c, "SN74LVC2G08DCTR", {1: "EPWM1A", 2: "GATE_EN", 7: "PWM_H_G", 5: "EPWM1B", 6: "GATE_EN", 3: "PWM_L_G", 4: GND, 8: "3V3"}, p,
        note="PWM gating: PWM_H = ePWM1A AND GATE_EN, PWM_L = ePWM1B AND GATE_EN (tpd 4.7 ns max)")
    c.resistor("33", "PWM_H_G", "PWM_H", p, note="series to the mezzanine (RC with 100 ohm + 100 pF on the power board: tau 13.3 ns)")
    c.resistor("33", "PWM_L_G", "PWM_L", p, note="series to the mezzanine")
    for net in ("EPWM1A", "EPWM1B", "ARM"):
        c.resistor("10k", net, GND, p, note="pull-down: GPIO0-11 have no reset pull-ups (SPRS439Q)")
    _ic(c, "SN74LVC1G74DCTR", {1: "ARM", 2: "3V3", 3: None, 4: GND, 5: "FAULT_N", 6: "FAULT_LATCH_N", 7: "3V3", 8: "3V3"}, p,
        note="fault latch: D = 1, CLK = ARM, CLR_N = FAULT_LATCH_N, Q = ARMED = FAULT_N (TZ1, mezzanine 35, LED); SSOP-8 DCT (CR-19)")
    _ic(c, "SN74LV21APWR", {1: "FLT_H_N", 2: "FLT_L_N", 4: "OC_N", 5: "OVP_IN_N", 6: "G1_N", 7: GND,
                            9: "OVP_OUT_N", 10: "OTP_N", 12: "FLT_12V_N", 13: "XRS_N", 8: "G2_N", 14: "3V3"}, p,
        note="latched group g1 (FLT_H_N, FLT_L_N, OC_N, OVP_IN_N) and g2 (OVP_OUT_N, OTP_N, FLT_12V_N, XRS_N)")
    _ic(c, "SN74LV21APWR", {1: "ESTOP_N", 2: "DSP_TRIP_N", 4: "PG_BIAS_H_OK", 5: "PG_BIAS_L_OK", 6: "G3_N", 7: GND,
                            9: "G1_N", 10: "G2_N", 12: "G3_N", 13: "PG_BIAS_S_OK", 8: "FAULT_LATCH_N", 14: "3V3"}, p,
        note="latched group g3 (ESTOP_N, DSP_TRIP_N, PG_BIAS_H_OK, PG_BIAS_L_OK) and g4 = g1 AND g2 AND g3 AND PG_BIAS_S_OK -> FAULT_LATCH_N")
    _ic(c, "SN74LV21APWR", {1: "UVLO_N", 2: "RDY_H", 4: "RDY_L", 5: "FAULT_N", 6: "GATE_EN", 7: GND,
                            9: "OVP_IN_N", 10: "OVP_OUT_N", 12: "3V3", 13: "3V3", 8: "OVP_N", 14: "3V3"}, p,
        note="run-permit g5 (UVLO_N, RDY_H, RDY_L, ARMED) -> GATE_EN; spare gate g6 = OVP_IN_N AND OVP_OUT_N -> OVP_N (GPIO11), unused inputs to 3V3")
    _ic(c, "SN74LV04APWR", {1: "UVLO", 2: "UVLO_N", 3: "PG_BIAS_H_N", 4: "PG_BIAS_H_OK", 5: "PG_BIAS_L_N", 6: "PG_BIAS_L_OK", 7: GND,
                            9: "PG_BIAS_S_N", 8: "PG_BIAS_S_OK", 11: GND, 10: None, 13: GND, 12: None, 14: "3V3"}, p,
        note="polarity restoration (A-C6, A-C7): UVLO flag -> UVLO_N; raw PG (low = good) -> PG_*_OK (high = good); gates 5/6 unused")
    for net in ("FLT_H_N", "FLT_L_N", "RDY_H", "RDY_L", "OC_N", "PG_BIAS_H_N", "PG_BIAS_L_N", "PG_BIAS_S_N"):
        _pullup(c, net, p, note="open-drain line from the power board")
    _pullup(c, "DSP_TRIP_N", p, note="GPIO6 software kill, high = run (no reset pull-up on GPIO0-11)")
    c.resistor("10k", "ESTOP_N", GND, p, note="E-stop pull-down: open loop = fault")
    c.header(2, {1: "3V3", 2: "ESTOP_N"}, p, note="J_ESTOP: normally-closed E-stop loop between 3V3 and ESTOP_N")
    _ic(c, "REF3125AIDBZR", {1: "3V3", 2: "REF2V5", 3: GND}, p, note="2.5 V reference for the OVP / UVLO thresholds (0.2 %, 20 ppm/K)")
    _cap(c, "1u/50V/0805", "3V3", GND, p, note="REF3125 supply bypass (A-C5)")
    _cap(c, "1u/50V/0805", "REF2V5", GND, p, note="REF2V5 output capacitor (A-C5)")
    c.resistor("1k", "REF2V5", "OVP_IN_REF", p, note="OVP_IN threshold 2.5 x 11/12 = 2.2917 V = 459.9 V")
    c.resistor("11k", "OVP_IN_REF", GND, p)
    _cap(c, "100n/50V/0603", "OVP_IN_REF", GND, p, note="threshold node bypass")
    c.resistor("953", "REF2V5", "OVP_OUT_REF", p, note="OVP_OUT threshold 2.5 x 10/10.953 = 2.2825 V = 229.8 V (CR-04)")
    c.resistor("10k", "OVP_OUT_REF", GND, p)
    _cap(c, "100n/50V/0603", "OVP_OUT_REF", GND, p, note="threshold node bypass")
    c.resistor("1k", "REF2V5", "UVLO_REF", p, note="UVLO threshold 2.5 x 1.91/2.91 = 1.641 V = 329 V centre")
    c.resistor("1.91k", "UVLO_REF", GND, p)
    c.resistor("21.5k", "UVLO", "UVLO_REF", p, note="hysteresis from the open-collector output: 336 V on / 319.5 V off with the 10 k pull-up (A-C6)")
    _cap(c, "100n/50V/0603", "UVLO_REF", GND, p, note="DNP: footprint kept for simulation-tuning of the hysteresis node (A-C12)", dnp=True)
    _ic(c, "TLV1702AIDGKR", {1: "OVP_IN_N", 2: "VIN_SENSE", 3: "OVP_IN_REF", 4: GND, 5: "OVP_OUT_REF", 6: "VOUT_SENSE", 7: "OVP_OUT_N", 8: "3V3"}, p,
        note="OVP comparators: OVP_IN_N high while VIN_SENSE < 2.2917 V; OVP_OUT_N high while VOUT_SENSE < 2.2825 V (tpd 560 ns)")
    _ic(c, "TLV1702AIDGKR", {1: "UVLO", 2: "VIN_SENSE", 3: "UVLO_REF", 4: GND, 5: "TEMP_HS_NTC", 6: "OTP_REF", 7: "OTP_N", 8: "3V3"}, p,
        note="UVLO flag (high = under-voltage, inverted to UVLO_N) and OTP_N (high while the NTC voltage is above 0.708 V = below 100 C)")
    for net in ("OVP_IN_N", "OVP_OUT_N", "UVLO", "OTP_N"):
        _pullup(c, net, p, note="comparator open-collector pull-up")
    for _ in range(2):
        _cap(c, "100n/50V/0603", "3V3", GND, p, note="TLV1702 supply bypass")
    for _ in range(3):
        _cap(c, "100n/50V/0603", "3V3", GND, p, note="SN74LV21A supply bypass")
    for part in ("SN74LVC1G74", "SN74LVC2G08", "SN74LV04A"):
        _cap(c, "100n/50V/0603", "3V3", GND, p, note=f"{part} supply bypass")

    # ---- 07 ADC front ends, NTC, monitors -----------------------------------------------------------------
    p = "07_adc_frontend"
    _ic(c, "REF3130AIDBZR", {1: "3V3", 2: "REF3V0", 3: GND}, p, note="3.00 V NTC pull-up / OTP reference; VIN min 3.05 V < 3.234 V (3V3 - 2 %)")
    _cap(c, "1u/50V/0805", "3V3", GND, p, note="REF3130 supply bypass (A-C5)")
    _cap(c, "1u/50V/0805", "REF3V0", GND, p, note="REF3V0 output capacitor (A-C5)")
    c.header(2, {1: "TEMP_HS_NTC", 2: GND}, p, note="J_NTC: Vishay NTCALUG01A103F heatsink lug NTC (10 k, B 3984 K), SELV lead (CR-01)")
    c.resistor("2.2k", "REF3V0", "TEMP_HS_NTC", p, note="NTC pull-up: 2.46 V at 25 C, 0.88 V at 90 C, 0.71 V at 100 C, 0.57 V at 110 C")
    _cap(c, "100n/50V/0603", "TEMP_HS_NTC", GND, p, note="NTC line filter (baseline)")
    c.resistor("32.4k", "REF3V0", "OTP_REF", p, note="OTP threshold 3.0 x 10/42.4 = 0.7075 V = 100 C hardware trip (ratiometric to REF3V0)")
    c.resistor("10k", "OTP_REF", GND, p)
    _cap(c, "100n/50V/0603", "OTP_REF", GND, p, note="threshold node bypass")
    _ic(c, "LM61CIM3/NOPB", {1: "3V3", 2: "TEMP_CTRL", 3: GND}, p, note="control-board ambient sensor, 600 mV + 10 mV/K (V1 pattern)")
    _cap(c, "100n/50V/0603", "3V3", GND, p, note="LM61 supply bypass")
    for source, adc, note in (("VIN_SENSE", "ADC_VIN", "VIN_SENSE -> ADCINA0 (0.0049834 V/V, 2.392 V at 480 V)"),
                              ("ISENSE", "ADC_ISENSE", "ISENSE -> ADCINA1 (0.33 V + 0.05 V/A)"),
                              ("TEMP_HS_NTC", "ADC_TEMP_HS", "heatsink NTC -> ADCINA2"),
                              ("TEMP_CTRL", "ADC_TEMP_CTRL", "LM61 -> ADCINA3"),
                              ("ISENSE_REF", "ADC_ISENSE_REF", "TMCS1133 VREF -> ADCINA4"),
                              ("I12V_MON", "ADC_I12V", "eFuse IMON -> ADCINB0"),
                              ("VOUT_SENSE", "ADC_VOUT", "VOUT_SENSE -> ADCINB1 (0.0099338 V/V)"),
                              ("V12V_MON", "ADC_V12V", "12 V monitor -> ADCINB3")):
        _adc_rc(c, source, adc, p, note)

    # ---- 08 interconnect, LEDs, test points, mounting -----------------------------------------------------
    p = "08_interconnect"
    c.header(50, {pin: mezzanine_net(str(pin)) for pin in range(1, 51)}, p, rows=2, mpn="TSW-125-07-G-D",
             note="J_MEZZ: 2 x 25 header to the power-board SSW-125-01-G-D socket; nets per design_decisions.json interconnect.pin_assignment")
    _pullup(c, "FAN_TACH", p, note="fan tachometer pull-up (A-C8)")
    c.resistor("4.7k", "12V_PROT", "LED_12V_A", p, note="12V_OK LED, about 2.1 mA")
    _led(c, "red", "LED_12V_A", GND, p, "12V_OK: protected 12 V present")
    c.resistor("1.5k", "FAULT_N", "LED_ARMED_A", p, note="ARMED LED from the latch Q, about 0.9 mA")
    _led(c, "green", "LED_ARMED_A", GND, p, "ARMED: latch set, no fault")
    c.resistor("1.5k", "LED_RUN", "LED_RUN_A", p, note="RUN LED (GPIO21)")
    _led(c, "green", "LED_RUN_A", GND, p, "RUN (firmware)")
    c.resistor("1.5k", "LED_FAULT", "LED_FAULT_A", p, note="FAULT LED (GPIO22)")
    _led(c, "red", "LED_FAULT_A", GND, p, "FAULT (firmware)")
    for net in ("3V3", "1V9", "5V", "12V_PROT", GND, GND, "PWM_H", "PWM_L", "FAULT_N", "ARM", "FAULT_LATCH_N", "GATE_EN", "XRS_N",
                "VIN_SENSE", "VOUT_SENSE", "ISENSE"):
        c.add("TP", net, "TestPoint:TestPoint_Pad_D2.0mm", {1: net}, page=p, kind="TP",
              note="bare PCB test point; ARMED is the FAULT_N net (latch Q), so ARM, FAULT_LATCH_N and GATE_EN are probed instead of a duplicate")
    for _ in range(4):
        c.add("H", "M3", "MountingHole:MountingHole_3.2mm_M3", {}, page=p, kind="H",
              note="M3 standoff to the power-board SELV strip (stack height about 11 mm, unverified)")
    return c


def bom_rows(circuit: Circuit) -> list[dict]:
    """Per-reference BOM rows (reference, value, manufacturer, mpn, footprint, datasheet, dnp, note)."""
    return [dict(reference=p["ref"], value=p["value"], manufacturer=p["maker"], mpn=p["mpn"], footprint=p["footprint"], datasheet=p["source"],
                 dnp="yes" if p.get("dnp") else "no", note=p["note"]) for p in circuit.parts]


def write_model(circuit: Circuit | None = None) -> Circuit:
    """Write design/circuit_control.json (list of parts, V1 format) and components/bom_control.csv."""
    circuit = circuit or build()
    MODEL_JSON.parent.mkdir(parents=True, exist_ok=True)
    BOM_CSV.parent.mkdir(parents=True, exist_ok=True)
    MODEL_JSON.write_text(json.dumps(circuit.parts, indent=2) + "\n", encoding="utf-8")
    fields = ["reference", "value", "manufacturer", "mpn", "footprint", "datasheet", "dnp", "note"]
    with BOM_CSV.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(bom_rows(circuit))
    return circuit


def net_names(parts: list[dict]) -> set[str]:
    return {n for p in parts for n in p["nets"].values() if n}


def validate(parts: list[dict]) -> dict:
    """Pad/net mapping against the installed footprints and the ERC pre-check; empty lists mean clean."""
    from automation.kicad_tools.project_footprints import validate_pad_mapping
    from automation.kicad_tools.project_schematic import analyse_connectivity
    report = analyse_connectivity(parts, FLAG_NETS)
    report["pad_mapping_issues"] = validate_pad_mapping(parts, custom_footprints=CUSTOM_FOOTPRINTS)
    report["parts"] = len(parts)
    report["nets"] = len(net_names(parts))
    return report


def main() -> int:
    circuit = write_model()
    report = validate(circuit.parts)
    print(BANNER)
    print(f"{PROJECT}: {report['parts']} parts, {report['nets']} nets -> {MODEL_JSON} and {BOM_CSV}")
    print(json.dumps({k: v for k, v in report.items() if k not in ("parts", "nets")}, indent=1))
    clean = not (report["undriven_power_nets"] or report["pin_conflicts"] or report["no_connect_pins_with_nets"] or report["pad_mapping_issues"])
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
