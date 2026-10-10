"""Reproduce the V2 first-order design calculations of the 400 V -> 200 V, 5 kW,
50 kHz SiC synchronous buck (SI units) from the orchestrator baseline.

Run from the repository root:

    python -m automation.scripts.calculate_sic_buck

Single source of truth: examples/sic-buck-400v-200v-5kw/design/design_decisions.json
(schema 3).  Where the baseline is silent, the research records
design/research/<area>.json are used after applying the required_changes of their
verify_*.json reports.  Every input is registered with its source and verification
level (user-requirement / fetched-datasheet / manufacturer-page / search-snippet /
unverified / analytically-checked / added-assumption); every function documents
its formula and source record; the invariants that must hold are asserted and the
script fails loudly if one is violated.

Standard library only.  Writes design/calculations.json and design/calculations.md.
Nothing here is simulated or measured: every result is a first-order analytical
estimate for human review.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/sic-buck-400v-200v-5kw"
OUT = EXAMPLE / "design"
BANNER = "**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**"

# --------------------------------------------------------------------------- #
# Verification levels and the input register                                   #
# --------------------------------------------------------------------------- #
LV_USER = "user-requirement"
LV_DS = "fetched-datasheet"
LV_PAGE = "manufacturer-page"
LV_SNIP = "search-snippet"
LV_UNV = "unverified"
LV_AN = "analytically-checked"
LV_ASM = "added-assumption"
LV_STD = "standard-formula-secondary-source"

REGISTER: list[dict] = []


def param(name: str, value, unit: str, source: str, level: str, note: str = ""):
    """Register an input with its source record and verification level; return it."""
    REGISTER.append(dict(name=name, value=value, unit=unit, source=source,
                         verification=level, note=note))
    return value


BASE = "design_decisions.json"  # the baseline (schema 3); wins over every research record

# --- user requirements and accepted assumptions (baseline) ------------------ #
V_OUT = param("V_OUT", 200.0, "V", f"{BASE} requirements_user.vout_V", LV_USER)
P_OUT = param("P_OUT", 5000.0, "W", f"{BASE} requirements_user.pout_W", LV_USER)
I_OUT = param("I_OUT", 25.0, "A", f"{BASE} requirements_user.iout_A", LV_USER)
F_SW = param("F_SW", 50e3, "Hz", f"{BASE} requirements_user.fsw_Hz", LV_USER)
VIN_LIST = param("VIN_corners", [360.0, 400.0, 440.0], "V",
                 f"{BASE} assumptions_accepted.vin_operating_range_V", LV_AN,
                 "seed accepted by the assumptions agent (A-01)")
I_OVL = param("I_OVERLOAD", 27.5, "A", f"{BASE} assumptions_accepted.overload_A_10s", LV_AN, "110 % for 10 s")
VIN_OVP = param("VIN_OVP", 460.0, "V", f"{BASE} assumptions_accepted.ovp_input_trip_V", LV_AN)
VIN_SURV = param("VIN_SURVIVAL", 480.0, "V", f"{BASE} assumptions_accepted.survival_V_100ms", LV_AN)
UVLO_START, UVLO_STOP = param("UVLO_start_stop", [340.0, 320.0], "V",
                              f"{BASE} assumptions_accepted.uvlo_start_stop_V", LV_AN)
VOUT_OVP = param("VOUT_OVP", 230.0, "V", f"{BASE} protection.comparators.ovp_out_V", LV_AN, "CR-04")
VIN_RIPPLE_PCT = param("VIN_ripple_max_pct_pp", 2.0, "%", f"{BASE} assumptions_accepted.vin_ripple_max_pct_pp", LV_AN)
VOUT_RIPPLE_MAX = param("VOUT_ripple_max_Vpp", 2.0, "V", f"{BASE} assumptions_accepted.vout_ripple_max_Vpp", LV_AN)
I_STEP = param("load_step_A", 12.5, "A", f"{BASE} assumptions_accepted.load_step_A", LV_AN)
V_STEP_MAX = param("load_step_excursion_max_V", 10.0, "V", f"{BASE} assumptions_accepted.load_step_excursion_max_V", LV_AN)
FC_LIST = param("voltage_loop_crossover_Hz", [2000.0, 2500.0], "Hz", f"{BASE} assumptions_accepted.voltage_loop_crossover_Hz", LV_AN)
T_A = param("T_ambient_max", 50.0, "degC", f"{BASE} assumptions_accepted.ambient_C", LV_AN)
TJ_LIMIT = param("TJ_design_limit", 150.0, "degC", f"{BASE} assumptions_accepted.tj_design_limit_C", LV_AN)
TJ_PREF = param("TJ_preferred", 125.0, "degC", f"{BASE} assumptions_accepted.tj_preferred_C", LV_AN)
ETA_TARGET = param("efficiency_target", 0.980, "-", f"{BASE} assumptions_accepted.efficiency_target_pct", LV_AN)
ETA_FLOOR = param("efficiency_floor", 0.975, "-", f"{BASE} assumptions_accepted.efficiency_acceptance_floor_pct", LV_AN)
I_IN_FW_LIMIT = param("firmware_input_current_limit", 15.6, "A", f"{BASE} assumptions_accepted.firmware_input_current_limit_A", LV_AN, "CR-20")
V_OVERSHOOT_ALLOW = param("switch_node_overshoot_allowance", 90.0, "V", f"{BASE} assumptions_accepted.switch_node_overshoot_allowance_V", LV_AN)
UTIL_LIMIT_REP = param("utilisation_limit_repetitive", 0.80, "-", "research/mosfet.json assumptions_added (engineering judgement, human review)", LV_ASM)
DEAD_TIME = param("dead_time_ns", {"minimum": 150, "programmed_bring_up": 300, "effective_target": 250, "upper_bound": 400}, "ns",
                  f"{BASE} assumptions_accepted.dead_time_ns", LV_AN, "250 ns is an agent assumption, CR-07")

# --- C4MS025120K (Wolfspeed Rev. 2, Dec 2025, fetched) ---------------------- #
R25_15V = param("MOSFET_R25_typ_15V", 28e-3, "ohm", "C4MS025120K datasheet Rev. 2 (fetched)", LV_DS, "typical at V_GS = 15 V; no 15 V maximum published")
R25_18V_TYP = param("MOSFET_R25_typ_18V", 25e-3, "ohm", "C4MS025120K datasheet Rev. 2", LV_DS)
R25_18V_MAX = param("MOSFET_R25_max_18V", 33e-3, "ohm", "C4MS025120K datasheet Rev. 2", LV_DS)
TEMPCO_175 = param("MOSFET_R175_over_R25", 1.88, "-", "C4MS025120K datasheet Rev. 2 (family value at 18 V)", LV_DS,
                   "applying the 18 V tempco to the 15 V value is an assumption (verify_power_semiconductor factcheck)")
E_ON_TEST = param("E_on_test", 470e-6, "J", "C4MS025120K Rev. 2: 800 V, 39.2 A, R_G 1 ohm, T_J 175 degC, body-diode FWD", LV_DS)
E_OFF_TEST = param("E_off_test", 64e-6, "J", "C4MS025120K Rev. 2 (175 degC)", LV_DS)
E_RR_TEST = param("E_rr_test", 256e-6, "J", "C4MS025120K Rev. 2 (175 degC, 15.8 A/ns)", LV_DS, "factor-two uncertainty at the design di/dt")
V_TEST = param("E_test_voltage", 800.0, "V", "C4MS025120K Rev. 2", LV_DS)
I_TEST = param("E_test_current", 39.2, "A", "C4MS025120K Rev. 2", LV_DS)
E_OSS_800 = param("E_oss_800V", 63e-6, "J", "C4MS025120K Rev. 2", LV_DS)
E_OSS_EXP = param("E_oss_voltage_exponent", 1.5, "-", "added: E_oss ~ V^1.5 (C_oss ~ V^-0.5 above the knee)", LV_ASM,
                  "bounds: linear-C 0.5*145 pF*V^2 (0.58 W at 400 V) and E ~ V (1.6 W); 1.5 gives 1.1 W, the baseline '~1 W'")
Q_G = param("Q_G", 125e-9, "C", "C4MS025120K Rev. 2 (-4/+18 V, 800 V)", LV_DS, "about 105 nC at -4/+15 V (Fig. 12, graph read)")
Q_GD_800 = param("Q_GD_800V", 30e-9, "C", "C4MS025120K Rev. 2", LV_DS)
Q_GD_400_RANGE = param("Q_GD_0_400V_range", [20e-9, 27e-9], "C", f"{BASE} power_stage.mosfet.parasitic_turn_on", LV_AN, "derived from Q_GD 30 nC at 800 V")
C_ISS = param("C_iss", 3087e-12, "F", "C4MS025120K Rev. 2 (1000 V)", LV_DS)
C_OSS_1000 = param("C_oss_1000V", 103e-12, "F", "C4MS025120K Rev. 2", LV_DS)
C_RSS_1000 = param("C_rss_1000V", 4.7e-12, "F", "C4MS025120K Rev. 2", LV_DS)
C_OSS_400 = param("C_oss_400V_est", 130e-12, "F", "research/gate_driver.json assumptions_added", LV_ASM, "from 103 pF at 1000 V and Co(tr) 238 pF")
R_G_INT = param("R_G_int", 2.6, "ohm", "C4MS025120K Rev. 2", LV_DS)
V_SD_19P6_175 = param("V_SD_19.6A_175C", 4.6, "V", "C4MS025120K Rev. 2 (graph value at 175 degC; table 5.1 V at 25 degC)", LV_DS)
R_D_SD = param("V_SD_slope", 0.07, "ohm", "added: body-diode differential resistance at 175 degC, V_GS -4 V", LV_ASM,
               "about 1.5x R_DS(on)(175 degC); datasheet Fig. 8-10 not digitised; +/-0.03 ohm")
R_TH_JC = param("R_thJC", 0.41, "K/W", "C4MS025120K Rev. 2 (typical, no maximum published)", LV_DS)
V_DS_MAX = param("V_DS_max", 1200.0, "V", "C4MS025120K Rev. 2", LV_DS)
V_GS_TH_MIN_25 = param("V_GS_th_min_25C", 2.0, "V", "C4MS025120K Rev. 2 (25 degC; hot minimum unpublished)", LV_DS)
I_D_100C = param("I_D_100C", 62.0, "A", "C4MS025120K Rev. 2 (V_GS 18 V)", LV_DS)
I_DM = param("I_DM", 274.0, "A", "C4MS025120K Rev. 2", LV_DS)
K_RG_RANGE = param("k_RG_range", {"1.3": 1.3, "1.6 (6.8 ohm)": 1.6, "1.9 (10 ohm)": 1.9, "2.0": 2.0}, "-",
                   f"{BASE} power_stage.mosfet.losses_W_per_pair + gate_driver eon_penalty_W", LV_UNV,
                   "E_on-vs-R_G Fig. 25 graph readings (1.6 at 6.8 ohm, 1.9 at 10 ohm); double-pulse test required")
L_LOOP = param("L_loop_board_nH", [25.0, 35.0], "nH", f"{BASE} power_stage.mosfet.selection_basis", LV_ASM, "typical / worst board loop")
L_LOOP_LEADS = param("L_loop_with_standing_leads_nH", [40.0, 60.0], "nH", f"{BASE} power_stage.mosfet.selection_basis", LV_ASM, "15-25 nH per standing TO-247 lead")
DI_DT_DESIGN = param("di_dt_design", 2.5e9, "A/s", "research/mosfet.json assumptions_added", LV_ASM, "set by R_G,off; verify by double-pulse test")
TJ_EXPECTED = param("TJ_expected", 100.0, "degC", "research/mosfet.json assumptions_added", LV_ASM)

# --- UCC21710-Q1 driver, gate network, DESAT (SLUSDH8D June 2024, fetched) -- #
V_DD = param("V_DD_COM", 15.0, "V", f"{BASE} power_stage.gate_driver.rails_V", LV_AN, "+/-1.3 % regulated by UCC14141-Q1")
V_EE = param("V_EE_COM", -4.0, "V", f"{BASE} power_stage.gate_driver.rails_V", LV_AN)
R_G_ON = param("R_G_on", 10.0, "ohm", f"{BASE} power_stage.gate_driver.rg_on_ohm", LV_AN, "6.8 ohm tuning target")
R_G_ON_TUNE = param("R_G_on_tuning_target", 6.8, "ohm", f"{BASE} power_stage.gate_driver.rg_on_tuning_target_ohm", LV_AN)
R_G_OFF = param("R_G_off", 3.3, "ohm", f"{BASE} power_stage.gate_driver.rg_off_ohm", LV_AN)
R_OUTH = param("UCC21710_R_OUTH", [1.5, 2.5, 4.9], "ohm", "SLUSDH8D (min/typ/max)", LV_DS)
R_OUTL = param("UCC21710_R_OUTL", [0.1, 0.3, 0.7], "ohm", "SLUSDH8D", LV_DS)
R_CLAMP = param("UCC21710_clamp_R", 0.6, "ohm", "SLUSDH8D (4 A Miller clamp)", LV_DS)
I_VDDQ_MAX = param("UCC21710_I_VDDQ_max", 5.9e-3, "A", "SLUSDH8D", LV_DS)
V_OCTH = param("UCC21710_V_OCTH", [0.63, 0.70, 0.77], "V", "SLUSDH8D", LV_DS)
T_OCFIL = param("UCC21710_t_OCFIL_ns", [95, 120, 180], "ns", "SLUSDH8D", LV_DS)
T_OCOFF = param("UCC21710_t_OCOFF_ns", [150, 270, 400], "ns", "SLUSDH8D (to OUT(L) 90 %)", LV_DS)
I_STO = param("UCC21710_I_STO", [0.25, 0.40, 0.57], "A", "SLUSDH8D soft turn-off", LV_DS)
CMTI_MIN = param("UCC21710_CMTI_min", 150.0, "V/ns", "SLUSDH8D", LV_DS)
T_INFIL = param("UCC21710_T_INFIL_ns", [28, 40, 60], "ns", "SLUSDH8D", LV_DS)
T_PD_MAX = param("UCC21710_tPD_max_ns", 130.0, "ns", "SLUSDH8D", LV_DS)
T_SKEW = param("UCC21710_skew_ns", 30.0, "ns", "SLUSDH8D", LV_DS)
T_PWD = param("UCC21710_PWD_ns", 30.0, "ns", "SLUSDH8D", LV_DS)
C_IO_DRV = param("UCC21710_C_IO_est", 1e-12, "F", "research/gate_driver.json assumptions_added", LV_ASM)
R1_DESAT = param("DESAT_R1", 2200.0, "ohm", f"{BASE} power_stage.gate_driver.desat.network", LV_AN)
R2_DESAT = param("DESAT_R2", 4990.0, "ohm", f"{BASE} power_stage.gate_driver.desat.network", LV_AN)
R3_DESAT = param("DESAT_R3", 1000.0, "ohm", f"{BASE} power_stage.gate_driver.desat.network", LV_AN)
C_BLANK = param("DESAT_C_blank", 680e-12, "F", f"{BASE} power_stage.gate_driver.desat.network", LV_AN)
V_F_DESAT = param("DESAT_diode_V_F", 0.6, "V", "research/gate_driver.json assumptions_added (US1M at 5-9 mA)", LV_ASM, "US1M table gives 1.7 V at 1 A only")
Q_GATE_15_TO_3 = param("Q_gate_15V_to_3V", 85e-9, "C", "research/gate_driver.json (graph read)", LV_UNV)
TD_OFF_NS = param("td_off_at_3.3ohm_ns", 50.0, "ns", "C4MS025120K Fig. 27 (graph read)", LV_UNV)
TF_NS = param("t_f_ns", 13.0, "ns", "C4MS025120K Fig. 27 (graph read)", LV_UNV)
TD_ON_NS = param("td_on_at_10ohm_ns", 28.0, "ns", "C4MS025120K Fig. 27 (graph read)", LV_UNV)
L_GATE_LOOP = param("L_gate_loop", 12e-9, "H", "research/gate_driver.json assumptions_added", LV_ASM)
TBCLK = param("TBCLK", 150e6, "Hz", f"{BASE} controller.pwm", LV_AN, "TMS320F28335 at 150 MHz")
DT_EROSION_NS = param("dead_time_erosion_ns", 35.0, "ns", "research/controller_aux_interconnect.json (30 ns skew + 5 ns RC mismatch)", LV_AN)
P_DT_SENS_W_PER_100NS = param("dead_time_loss_sensitivity", 1.2, "W per 100 ns", "research/gate_driver.json (hand-off)", LV_AN)
V_DV_DT_ENVELOPE = param("dv_dt_envelope", 120.0, "V/ns", "research/gate_driver.json", LV_AN, "turn-off, load-current limited")

# --- UCC14141-Q1 bias modules (SLUSF10B June 2023, fetched) ----------------- #
P_BIAS_RATING = param("UCC14141_rating_W", 1.5, "W", "SLUSF10B: 10.8-13.2 V, TA <= 85 degC", LV_DS, "1.0 W for 8-18 V; abs max 2.5 W at 25 degC; SOA curve at 19 V / 10.8 V not read")
P_BIAS_IN_NOLOAD = param("UCC14141_P_in_no_load", 0.48, "W", "SLUSF10B 40 mA no load at 12 V", LV_DS)
K_BIAS_IN = param("UCC14141_incremental_input_W_per_W", 1.92, "W/W", "SLUSF10B (200 mA at 1.0 W)", LV_DS, "0.48 W + 1.92 x P_out model")
C_IO_BIAS = param("UCC14141_C_IO", [3.5e-12, 5e-12], "F", "SLUSF10B '< 3.5 pF' (not legible in extraction); 5 pF upper bound", LV_UNV)
R_LIM_INT = param("UCC14141_RLIM_int", 30.0, "ohm", "SLUSF10B", LV_DS)
P_DESAT_BIAS = param("P_DESAT_bias_per_channel", 0.07, "W", "research/gate_driver.json", LV_AN)
P_MISC_CH = param("P_misc_per_channel", 0.015, "W", "research/gate_driver.json (pull-down, AIN)", LV_AN)
P_SENS_BUDGET = param("P_sensing_module_budget", 0.40, "W", f"{BASE} power_stage.bias_supply.power_budget_W.sensing", LV_AN)
I_AMC_VDD1_MAX = param("AMC1311_IDD1_max", 9.7e-3, "A", "SBAS786C (fetched)", LV_DS, "7.1 mA typical")
I_SENS_MISC = param("sensing_island_misc_mA", 0.6e-3, "A", "added: decoupling leakage and REF-side loads on 5V_ISO", LV_ASM)
C_DECOUP_VDD = param("C_VDD_COM_nominal", 2 * 4.7e-6, "F", f"{BASE} power_stage.gate_driver.decoupling", LV_AN)
C_DECOUP_VEE = param("C_COM_VEE_nominal", 4.7e-6, "F", f"{BASE} power_stage.gate_driver.decoupling", LV_AN)
K_X7R_LOSS = param("X7R_bias_loss_at_15V", 0.35, "-", "research/gate_driver.json assumptions_added", LV_ASM, "TDK curve not extracted")
DV_DROOP_SPEC = param("decoupling_droop_spec", 0.1, "V", "research/gate_driver.json (KR-PCB-002 derivation)", LV_AN)

# --- Inductor: 2 x Magnetics 0058192A2 High Flux 60u, 34 T AWG 10 ----------- #
AL_NH = param("core_AL_per_core_nH", 138.0, "nH/T^2", "Magnetics 0058192A2 datasheet rev 10/6/2021 (fetched), +/-8 %", LV_DS)
AL_TOL = param("core_AL_tolerance", 0.08, "-", "Magnetics 0058192A2 datasheet", LV_DS)
N_STACK = param("cores_stacked", 2, "-", f"{BASE} magnetics.inductor.core", LV_AN)
N_TURNS = param("turns", 34, "-", f"{BASE} magnetics.inductor.turns", LV_AN)
AE_CORE = param("core_Ae_per_core", 229e-6, "m^2", "Magnetics 0058192A2 datasheet", LV_DS)
LE_M = param("core_le", 125e-3, "m", "Magnetics 0058192A2 datasheet", LV_DS)
VE_STACK_CM3 = param("core_Ve_stack", 57.2, "cm^3", "Magnetics 0058192A2 datasheet (28.6 cm^3 x 2)", LV_DS)
B_SAT = param("B_sat_HighFlux", 1.5, "T", "Magnetics catalogue 2024 material table", LV_DS)
MU_A, MU_B, MU_C = param("perm_vs_H_fit", [0.01, 6.413e-8, 2.291], "-", "Magnetics catalogue 2024 p.63: %u = 1/(a + b H^c), H in Oe", LV_DS)
PV_A, PV_B, PV_C = param("core_loss_fit", [246.54, 2.218, 1.311], "-", "Magnetics catalogue 2024 p.109: Pv[mW/cm3] = a B[T]^b f[kHz]^c", LV_DS)
BDC_COEF = param("dc_magnetisation_fit", [3.828e-2, 1.800e-2, 7.012e-4, 7.063e-2, 4.502e-4, 1.630], "-",
                 "Magnetics catalogue 2024 p.129/130: B = ((a+bH+cH^2)/(1+dH+eH^2))^x, T, Oe", LV_DS)
MIN_CURVE_ANCHORS = param("dc_bias_minimum_anchors", {"90 Oe": 80.0, "170 Oe": 50.0}, "%", "Magnetics 0058192A2 datasheet (DC bias min)", LV_DS)
K_WAVEFORM = param("core_loss_waveform_factor", 1.10, "-", "research/inductor.json assumptions_added", LV_ASM, "iGSE gives 0.95 for triangular flux, so 1.10 is conservative")
K_CORE_MAX = param("core_loss_datasheet_max_over_fit", 1.44, "-", "verify_output_inductor (900 vs 625 mW/cm3 at 100 kHz / 100 mT)", LV_AN)
K_BIAS_LOSS = param("core_loss_dc_bias_allowance", [1.2, 1.3], "-", "research/inductor.json open_issues (+20-30 %)", LV_ASM)
A_W = param("wire_area_AWG10", 5.261e-6, "m^2", "standard AWG table", LV_STD)
D_W = param("wire_diameter_AWG10", 2.588e-3, "m", "standard AWG table", LV_STD)
L_WIRE = param("wire_length_N_x_MLT", 3.73, "m", "research/inductor.json (MLT 110 mm x 34)", LV_AN, "about 0.25 m of leads (+1 mohm) not included")
RHO_20 = param("copper_rho_20C", 1.724e-8, "ohm m", "IACS copper", LV_STD)
ALPHA_CU = param("copper_tempco", 0.00393, "1/K", "IACS copper", LV_STD)
T_CU = param("copper_temperature_for_loss", 100.0, "degC", "research/inductor.json assumptions_added", LV_ASM)
A_SURF_CM2 = param("inductor_surface_area", 161.0, "cm^2", "research/inductor.json assumptions_added (+/-15 %)", LV_ASM)
DT_EXP = param("temperature_rise_exponent", 0.833, "-", "Magnetics catalogue dT = (P_mW/A_cm2)^0.833 (still air)", LV_DS, "+/-30 % accuracy is an added assumption, not a catalogue statement")
HOT_SPOT_ALLOW = param("hot_spot_allowance_K", [10.0, 15.0], "K", "verify_output_inductor engineering (ID double layer under potting)", LV_AN)
T_HOT_LIMIT = param("winding_hot_spot_limit", 125.0, "degC", "research/inductor.json assumptions_added", LV_ASM)
T_HOT_ACCEPT = param("thermocouple_acceptance", 110.0, "degC", f"{BASE} magnetics.inductor.temperature", LV_AN)
I_MARGIN_FACTOR = param("saturation_margin_factor", 1.3, "-", f"{BASE} assumptions_accepted.corrections_to_seeds", LV_AN)
L_RATIO_MIN = param("saturation_ratio_criterion", 0.70, "-", f"{BASE} assumptions_accepted.corrections_to_seeds (L(41 A) >= 70 % of L(25 A))", LV_AN)
B_RATIO_MAX = param("flux_criterion", 0.80, "-", f"{BASE} assumptions_accepted.corrections_to_seeds (B_dc + B_ac <= 0.8 B_sat)", LV_AN)
L_TRIP_WORST = param("L_for_trip_overshoot", 175e-6, "H", f"{BASE} sensing.current.trip_overshoot_worst (worst L at 41 A, AL -8 %, minimum curve)", LV_AN)

# --- Capacitors --------------------------------------------------------------- #
C_IN_FILM_EACH = param("C_in_film_each", 20e-6, "F", "TDK B32776G8206K000 (datasheet June 2026, fetched)", LV_DS)
C_IN_FILM_QTY = param("C_in_film_qty", 2, "-", f"{BASE} capacitors.input_film.qty", LV_AN)
C_TOL = param("film_tolerance", 0.10, "-", "TDK K code", LV_DS)
I_RMS_IN_RATING = param("C_in_I_rms_rating", 14.5, "A", "TDK B32776G8206K000: 70 degC, 10 kHz, dT <= 20 K", LV_DS)
ESR_IN_EACH = param("C_in_ESR_each", 7.5e-3, "ohm", "TDK B32776G8206K000 (10 kHz)", LV_DS, "flat to 50 kHz verified for Vishay only (extrapolation)")
ESL_IN_EACH = param("C_in_ESL_each", 10e-9, "H", "TDK B32776G8206K000", LV_DS)
DT_RATED_IN = param("C_in_rating_dT", 20.0, "K", "TDK B32776G8206K000", LV_DS)
V_R_IN = param("C_in_V_R", 800.0, "V", "TDK B32776G8206K000 (V_R,70; V_op,85 700 V)", LV_DS)
C_OUT_FILM_EACH = param("C_out_film_each", 60e-6, "F", "TDK B32776G4606K000 (datasheet June 2026, fetched)", LV_DS)
C_OUT_FILM_QTY = param("C_out_film_qty", 2, "-", f"{BASE} capacitors.output_film.qty", LV_AN)
I_RMS_OUT_RATING = param("C_out_I_rms_rating", 23.5, "A", "TDK B32776G4606K000", LV_DS)
ESR_OUT_EACH = param("C_out_ESR_each", 3.6e-3, "ohm", "TDK B32776G4606K000", LV_DS)
V_R_OUT = param("C_out_V_R", 450.0, "V", "TDK B32776G4606K000 (V_R,70 = V_op,85)", LV_DS)
C_HF_EACH = param("C_HF_each_nominal", 0.47e-6, "F", "TDK CGA9P1X7T2J474M250KC (630 V X7T 2220)", LV_SNIP)
C_HF_QTY = param("C_HF_qty", 10, "-", f"{BASE} capacitors.input_hf_ceramic.qty", LV_AN)
K_HF_BIAS_REMAIN = param("C_HF_remaining_at_440V", 0.40, "-", f"{BASE} capacitors.input_hf_ceramic.dc_bias_note (60 % loss assumed)", LV_ASM, "TDK curve not fetched")
L_INT_LIST = param("film_to_ceramic_interconnect_nH", [20.0, 30.0, 40.0], "nH", "research/capacitors.json assumption A7", LV_ASM)
R_LOOP_RANGE = param("ring_loop_resistance", [6e-3, 20e-3], "ohm", "verify_dc_link engineering (Q 6-21)", LV_ASM)
T_AIR_LOCAL = param("film_local_air_rise", 10.0, "K", "research/capacitors.json assumption A6", LV_ASM)
# bleeders (merged networks, CR-03)
R_BL_IN = param("R_bleed_in", 3 * 120e3, "ohm", f"{BASE} capacitors.bleeders.input (3 x CRCW2512120K, 1 W, 500 V)", LV_DS)
R_IND_IN = param("R_indicator_in", 3 * 150e3, "ohm", f"{BASE} capacitors.bleeders.input (3 x 150 k 1206 + LED)", LV_UNV, "1206 limiting voltage 200 V / 0.25 W assumed")
R_BL_OUT = param("R_bleed_out", 2 * 100e3, "ohm", f"{BASE} capacitors.bleeders.output (2 x CRCW2512100K)", LV_DS)
R_IND_OUT = param("R_indicator_out", 2 * 100e3, "ohm", f"{BASE} capacitors.bleeders.output (2 x 100 k 1206 + LED)", LV_UNV)
V_LED = param("indicator_LED_drop", 2.0, "V", "added: red LED forward drop at ~1 mA", LV_ASM)
C_IN_DISCHARGE = param("C_in_for_discharge", 48.7e-6, "F", "research/capacitors.json (44 uF film at +10 % + 4.7 uF ceramic)", LV_AN)
C_OUT_DISCHARGE = param("C_out_for_discharge", 132e-6, "F", "research/capacitors.json (120 uF at +10 %)", LV_AN)
V_SAFE = param("safe_voltage", 60.0, "V", f"{BASE} capacitors.bleeders.criterion", LV_AN)
T_DISCHARGE_MAX = param("discharge_time_limit_with_label", 60.0, "s", f"{BASE} capacitors.bleeders.criterion", LV_AN)
R_5S_OPTION = param("R_5s_option", {"input": 60e3, "output": 32e3}, "ohm", f"{BASE} capacitors.bleeders.criterion", LV_AN, "sized at nominal 40 uF / 120 uF")
R_2512_LIMITS = param("CRCW2512_limits", {"P70_W": 1.0, "U_max_V": 500.0}, "-", "Vishay 20035 rev 14-Apr-2026 (fetched)", LV_DS)
R_1206_LIMITS = param("1206_thick_film_limits", {"P70_W": 0.25, "U_max_V": 200.0}, "-", "typical 1206 ratings (part not selected)", LV_UNV)

# --- Sensing (TMCS1133C2A, AMC1311B, comparators, NTC) ---------------------- #
S_TMCS = param("TMCS1133C2A_sensitivity", 0.050, "V/A", "SBOSAG0E (Oct 2023, rev May 2026, fetched)", LV_DS)
V0_TMCS = param("TMCS1133C2A_zero_current_output", 0.33, "V", "SBOSAG0E", LV_DS)
VS_TMCS = param("TMCS1133_VS", 3.3, "V", f"{BASE} sensing.current.vs_V", LV_AN)
ADC_FS = param("ADC_full_scale", 3.0, "V", "SPRS439Q (0-3 V conversion range)", LV_DS)
ADC_BITS = param("ADC_bits", 12, "-", "SPRS439Q", LV_DS)
R_OC_TOP = param("OC_divider_top", 2320.0, "ohm", f"{BASE} sensing.current.oc_setting", LV_AN)
R_OC_BOT = param("OC_divider_bottom", 1000.0, "ohm", f"{BASE} sensing.current.oc_setting", LV_AN)
R_VOC_PIN = param("TMCS1133_VOC_pin_impedance", 120e3, "ohm", "SBOSAG0E", LV_DS)
V_REF = param("REF3125", 2.5, "V", "SBVS046E (cached)", LV_DS)
OC_ERR = param("TMCS1133_OC_threshold_error", [0.02, 0.10], "-", "SBOSAG0E (typ / max over -40..125 degC)", LV_DS)
OC_HYST = param("TMCS1133_OC_hysteresis", 3.5, "A", "SBOSAG0E (x2A variants)", LV_DS)
T_OC_MAX = param("TMCS1133_OC_response_max_ns", 250.0, "ns", "SBOSAG0E (100 typ / 250 max)", LV_DS)
T_LATCH = param("SN74LVC1G74_tpd_ns", 5.9, "ns", "SCES794G (CLK-to-Q; CLR-to-Q same order)", LV_DS)
T_GATE_FALL = param("gate_fall_in_trip_chain_ns", 100.0, "ns", "research/sensing_protection.json assumptions_added", LV_ASM)
I_PK_OVL_WORST = param("overload_peak_worst", 32.0, "A", f"{BASE} operating_points (440 V, 27.5 A, AL -8 %)", LV_AN)
R_IN_TMCS = param("TMCS1133_R_IN", 0.7e-3, "ohm", "SBOSAG0E", LV_DS)
R_LADDER_TOP = param("ladder_top_resistor", 750e3, "ohm", f"{BASE} sensing.vin.ladder", LV_AN)
R_LADDER_BOT = param("ladder_bottom_resistor", 10e3, "ohm", f"{BASE} sensing.vin.ladder", LV_AN)
N_TOP_VIN = param("ladder_top_count_vin", 4, "-", f"{BASE} sensing.vin.ladder", LV_AN)
N_TOP_VOUT = param("ladder_top_count_vout", 2, "-", f"{BASE} sensing.vout.ladder", LV_AN)
G_OPA = param("OPA2320_difference_gain", 1.5, "-", f"{BASE} sensing.vin.conversion", LV_AN)
AMC_FSR = param("AMC1311_linear_full_scale", 2.0, "V", "SBAS786C", LV_DS)
R_OVP_IN = param("OVP_in_divider", [1000.0, 11000.0], "ohm", f"{BASE} protection.comparators (1.00 k / 11.0 k)", LV_AN)
R_OVP_OUT = param("OVP_out_divider", [953.0, 10000.0], "ohm", f"{BASE} protection.comparators.ovp_out_divider", LV_AN)
R_UVLO = param("UVLO_divider", [1000.0, 1910.0], "ohm", "research/sensing_protection.json (1.00 k / 1.91 k)", LV_AN)
R_UVLO_HYST = param("UVLO_hysteresis_resistor", 21.5e3, "ohm", "research/sensing_protection.json", LV_AN)
V_LOGIC = param("comparator_pull_up_rail", 3.3, "V", "research/sensing_protection.json", LV_AN)
NTC_R25 = param("NTCALUG01A103F_R25", 10e3, "ohm", "Vishay 29092 rev 14-Jan-2026 (fetched by verifier)", LV_DS)
NTC_B = param("NTCALUG01A103F_B25_85", 3984.0, "K", "Vishay 29092", LV_DS)
NTC_DISS = param("NTCALUG01A103F_dissipation_factor", 13e-3, "W/K", "Vishay 29092 rev 14-Jan-2026", LV_DS, "the thermal record quoted 23 mW/K from a superseded revision")
R_NTC_PULLUP = param("NTC_pull_up", 2200.0, "ohm", f"{BASE} sensing.heatsink_temperature.route", LV_AN)
V_NTC_REF = param("NTC_reference", 3.00, "V", f"{BASE} sensing.heatsink_temperature.route (REF3125 buffered)", LV_AN)
T_OTP = param("OTP_thresholds_degC", {"warn_derate": 90, "firmware_trip": 100, "hardware_comparator_trip": 110}, "degC",
              f"{BASE} sensing.heatsink_temperature.thresholds_C_review_proposals", LV_AN, "human-review proposals (KR-TH-003)")
R_OTP_PROPOSAL = param("OTP_comparator_divider_proposal", [10000.0, 2370.0], "ohm", "added: E96 pair from the 3.00 V NTC reference for the 110 degC trip", LV_ASM)
T_SPREAD_NTC = param("NTC_spreading_offset_K", [4.0, 6.0], "K", f"{BASE} sensing.heatsink_temperature.mounting", LV_ASM)

# --- Thermal ----------------------------------------------------------------- #
R_TH_HS = param("R_th_heatsink_forced", 0.30, "K/W", f"{BASE} thermal.heatsink (Fischer LAM 5 D K 100 12, distributor figure)", LV_SNIP, "datasheet to confirm; CR-13")
R_PAD = param("R_th_pad_design", 1.4, "K/W", f"{BASE} thermal.interface_pad (Sil-Pad TSP A2000 0.254 mm, clip at about 25 psi; CR-21)", LV_AN,
              "TDS 0.50 degC-in2/W at 25 psi over the exposed tab metal 2.3 cm2 = 0.36 in2 (the 16 x 21 mm body outline would give 0.96 K/W); 1.16 K/W screw-mounted at 50 psi; measured value required")
R_SPREAD = param("sink_spreading_allowance_per_device", [0.1, 0.2], "K/W", f"{BASE} thermal.results.spreading_allowance_K_W", LV_ASM)
R_TH_NAT = param("R_th_natural_estimate", [1.73, 2.5], "K/W", "verify_thermal (LAM 5 D K 125 24 listing 1.73 K/W, length-scaled)", LV_UNV)
M_SINK = param("heatsink_mass_estimate", [0.3, 0.6], "kg", "added: double-width 100 mm LAM 5 profile with fan", LV_UNV)
CP_AL = param("aluminium_c_p", 900.0, "J/(kg K)", "textbook", LV_STD)
FAN_DERATE_RTH = param("R_th_increase_at_10.8V_fan", 0.06, "-", f"{BASE} thermal.fan (flow -10 % -> R_th +6 %)", LV_ASM)
K_IPC_EXT = param("IPC2221_k_external", 0.048, "-", "IPC-2221 formula (secondary sources)", LV_STD)
K_IPC_INT = param("IPC2221_k_internal", 0.024, "-", "IPC-2221 formula", LV_STD)
IPC_B, IPC_C = param("IPC2221_exponents", [0.44, 0.725], "-", "IPC-2221 formula", LV_STD)
CU_THICK_UM = param("outer_copper_thickness", 70.0, "um", f"{BASE} architecture.power_board.copper_um", LV_AN)
VIA_PLATING_UM = param("via_plating", 25.0, "um", f"{BASE} thermal.copper.method", LV_ASM)
VIA_DRILLS_MM = param("via_drills_mm", [0.3, 0.5], "mm", f"{BASE} thermal.copper.vias_per_25A_transition", LV_AN)
RHO_100 = param("copper_rho_100C", 2.23e-8, "ohm m", "IACS copper at 100 degC", LV_STD)
PATH_LEN_CM = param("power_path_length", 15.0, "cm", "research/thermal.json (about 2.5 W per 15 cm)", LV_ASM)
PATH_WIDTH_MM = param("power_path_width", 12.0, "mm", f"{BASE} thermal.copper.outer_70um_width_mm_25A_20K", LV_AN)
VIA_COUNT_BASELINE = param("vias_per_25A_transition_baseline", {"0.3 mm": 24, "0.5 mm": 21}, "-", f"{BASE} thermal.copper.vias_per_25A_transition", LV_AN)

# --- Auxiliary 12 V, eFuse, supervisor, relay, mezzanine -------------------- #
V_AUX_NOM = param("V_aux_nominal", 12.0, "V", f"{BASE} assumptions_accepted.aux_12V", LV_AN)
V_AUX_MIN = param("V_aux_min", 10.8, "V", f"{BASE} assumptions_accepted.aux_12V", LV_AN)
V_AUX_MAX = param("V_aux_max", 13.2, "V", f"{BASE} assumptions_accepted.aux_12V", LV_AN)
AUX_BUDGET_10P8 = param("aux_budget_A_at_10.8V", {"gate_bias_modules": 0.40, "sensing_bias_module": 0.15, "control_board": 0.29,
                                                   "relay_coil_pull_in": 0.42, "relay_coil_pwm_hold": 0.25, "heatsink_fan_max": 0.50},
                        "A", f"{BASE} controller.aux_12V_protection.budget_A_at_10p8V", LV_AN, "CR-02; gate-bias figure carries the controller agent's 250 nC bound and 20 % margin")
R_ILIM = param("TPS26400_R_ILIM", 6.04e3, "ohm", f"{BASE} controller.aux_12V_protection.r_ilim_kohm", LV_AN)
I_CB_TOL = param("TPS26400_I_CB_tolerance", [-0.10, 0.09], "-", "added: from the SLVSFQ6A circuit-breaker table spread (2.0/2.21/2.4 A at 5.36 k)", LV_ASM)
C_DVDT = param("TPS26400_C_dVdT", 100e-9, "F", f"{BASE} controller.aux_12V_protection.dvdt_C_nF", LV_AN)
I_DVDT = param("TPS26400_I_dVdT", [4.0e-6, 4.7e-6, 5.5e-6], "A", "SLVSFQ6A", LV_DS)
GAIN_DVDT = param("TPS26400_GAIN_dVdT", 24.6, "-", "SLVSFQ6A", LV_DS)
C_DOWNSTREAM_12V = param("C_downstream_12V", 194e-6 + 10e-6, "F", "research/controller_aux_interconnect.json (194 uF) + third module 10 uF", LV_AN)
R_EFUSE_LADDER = param("TPS26400_ladder", [107e3, 4.42e3, 10e3], "ohm", f"{BASE} controller.aux_12V_protection", LV_AN)
V_UVLO_PIN = param("TPS26400_UVLO_pin_thresholds", {"rising": 1.19, "falling": 1.1}, "V", "SLVSFQ6A", LV_DS)
GAIN_IMON = param("TPS26400_IMON_gain", [72e-6, 78.28e-6, 85e-6], "A/A", "SLVSFQ6A", LV_DS)
R_IMON = param("TPS26400_R_IMON", 14.7e3, "ohm", f"{BASE} controller.aux_12V_protection.imon_R_kohm", LV_AN)
V_IT_3808 = param("TPS3808G01_V_IT", 0.405, "V", "TPS3808 datasheet (cached V1 copy)", LV_DS)
R_3808 = param("TPS3808_divider", [101e3, 10e3], "ohm", f"{BASE} controller.supplies (101 k / 10 k)", LV_AN, "CR-18; 105 k would trip at 4.66 V")
HYST_3808 = param("TPS3808_hysteresis", 0.015, "-", "verify_controller engineering (1.5 % typ / 3 % max)", LV_DS)
I_5V = param("I_5V_control", 0.54, "A", f"{BASE} controller.supplies", LV_AN)
I_1V9, I_3V3 = param("LDO_rail_currents", [0.350, 0.179], "A", "research/controller_aux_interconnect.json", LV_AN)
C_5V_BULK = param("C_5V_rail", 264e-6, "F", "research/controller_aux_interconnect.json (220 uF + 2 x 22 uF)", LV_AN)
P_CONTROL_IN = param("control_board_input_power", 3.17, "W", "research/controller_aux_interconnect.json (2.70 W / 0.85)", LV_AN)
R_COIL = param("G9EA-1_coil_resistance", 28.8, "ohm", "Omron J186-E1-01 (fetched)", LV_DS)
HOLD_DUTY = param("relay_pwm_hold_duty", [0.5, 0.6], "-", f"{BASE} protection.power_path.relay_coil_drive", LV_AN)
I_FAN_MAX = param("fan_current_cap", 0.5, "A", f"{BASE} thermal.fan", LV_UNV, "datasheet value unknown")
T_RELAY_OPERATE = param("G9EA-1_operate_time_max", 50e-3, "s", "Omron J186-E1-01", LV_DS)
R_CONTACT_RELAY = param("G9EA-1_contact_resistance_typ", 0.6e-3, "ohm", "Omron J186-E1-01 (0.6 mohm typ, 30 mohm max)", LV_DS)
N_12V_PINS = param("mezzanine_12V_pins", 3, "-", f"{BASE} interconnect.pin_assignment", LV_AN)
I_PIN_RATING = param("mezzanine_pin_rating", {"WR-PHD": 3.0, "SSW/TSM": 4.7, "SSW+TSW": 6.3}, "A", "Wuerth 6130xx21121 (fetched); Samtec catalog (verify_pcb_architecture factcheck)", LV_DS)
I_PIN_TARGET = param("mezzanine_pin_target", 0.4, "A", f"{BASE} architecture target_metrics (0.4 A per pin)", LV_AN)

# --- Power path: fuse, precharge --------------------------------------------- #
I_FUSE = param("fuse_rating", 25.0, "A", f"{BASE} protection.power_path.fuse (KLKD025.T)", LV_PAGE, "CR-15; I2t not found")
R_PTC = param("PTC_R25", {"nominal": 120.0, "min": 90.0, "max": 150.0}, "ohm", f"{BASE} protection.power_path.precharge (R25 100-150 ohm, re-selection pending)", LV_UNV,
              "baseline tau 5.8 ms (4.4-7.3 ms) corresponds to 120 ohm +/-25 %")
C_TH_PTC = param("PTC_C_th_candidates", [0.6, 1.4, 2.1], "J/K", "verify_sensing factcheck (TDK 2018: 0.6; 2015 short-form: 1.4); sensing record 2.1 (not found in any TDK document)", LV_UNV)
T_REF_PTC = param("PTC_T_ref", [115.0, 130.0], "degC", "verify_sensing factcheck (115) / sensing record (130)", LV_UNV)
T_A_PTC = param("PTC_ambient_in_enclosure", 60.0, "degC", "research/sensing_protection.json assumptions_added", LV_ASM)
R_FUSE_COLD = param("fuse_cold_resistance", 4.5e-3, "ohm", "KLKD020 distributor value (25 A member likely lower)", LV_SNIP)

# --- Baseline figures used for the cross-check (design_decisions.json) ------- #
BASELINE_FIGURES = {
    "dIL_App_nominal_25A": {"360": 6.5, "400": 7.3, "440": 8.0},
    "dIL_App_440V_AL_minus8": 8.7,
    "ipk_A_25A": {"360": 28.3, "400": 28.7, "440": 29.0},
    "ipk_A_27p5A": {"360": 30.8, "400": 31.2, "440": 31.6},
    "ipk_A_27p5A_worst": 32.0,
    "iin_A_eta98_25A": {"360": 14.17, "400": 12.76, "440": 11.6},
    "rds_on_150C_mohm": 48.5,
    "mosfet_pair_400V_25A_150C_k1p3_W": 46.7,
    "mosfet_pair_400V_25A_150C_k2p0_W": 52.0,
    "mosfet_pair_440V_27p5A_150C_W": 56.2,
    "P_HS_360V_27p5A_typ_W": 30.4,
    "P_HS_360V_27p5A_maxR_W": 34.1,
    "gate_power_W_wolfspeed_form": 0.119,
    "gate_power_W_TI_form": 0.24,
    "peak_gate_current_A": {"source": 1.26, "sink": 3.06},
    "com_vee_droop_mV": 41,
    "desat_trip_vds_V": 3.6,
    "desat_blanking_ns": 288,
    "desat_response_us": [0.55, 1.07],
    "L_uH": {"0A": 319, "25A": 272, "31p6A": 248, "41A": 210},
    "L_worst_uH": {"25A": 235, "31p5A": 215, "41A": 175, "46A": 160},
    "isat_30pct_A": 37.3,
    "inductor_loss_W": {"400V_25A": 16.4, "440V_27p5A": 19.8},
    "cin_irms_each_A_worst": 6.92,
    "cin_ripple_Vpp_27p5A": 3.9,
    "cout_step_V_fc2p5kHz": 7.4,
    "cout_load_dump_V": 14.8,
    "discharge_s": 30,
    "tmcs_lsb_mA": 14.65,
    "tmcs_fs_A": 53.4,
    "oc_trip_chain_ns": 546,
    "oc_worst_peak_A": 42.6,
    "ovp_out_V": 229.8,
    "ovp_in_V": 460,
    "ntc_readout_V": {"25": 2.46, "90": 0.88, "100": 0.71, "110": 0.57},
    "T_J_HS_400V_25A_C": 109.4,
    "T_J_HS_360V_27p5A_maxR_C": 129.8,
    "T_J_HS_440V_27p5A_maxR_C": 126.2,
    "P_max_per_device_W": 41.5,
    "copper_width_25A_20K_mm": 12,
    "i_cb_A": 1.96,
    "aux_total_pull_in_A": 1.76,
    "aux_total_steady_A": 1.59,
    "precharge_tau_ms": 5.8,
    "precharge_E_J": [4.7, 5.6],
}


# --------------------------------------------------------------------------- #
# Operating points                                                             #
# --------------------------------------------------------------------------- #
def duty(vin: float) -> float:
    """D = Vout / Vin (ideal CCM buck).  Source: design basis, research/assumptions.json."""
    return V_OUT / vin


def input_current(vin: float, io: float, eta: float) -> float:
    """Iin = Vout * Io / (eta * Vin).  Source: research/assumptions.json operating points."""
    return V_OUT * io / (eta * vin)


def h_oersted(i: float) -> float:
    """H[Oe] = 0.4 pi N I / le[cm].  Source: Magnetics catalogue (research/inductor.json)."""
    return 0.4 * math.pi * N_TURNS * i / (LE_M * 100.0)


def pct_mu_fit(h: float) -> float:
    """Percent permeability of High Flux 60u toroids: %u = 1/(a + b H^c), H in Oe.
    Source: Magnetics catalogue 2024 p.63 (fetched)."""
    return 1.0 / (MU_A + MU_B * h ** MU_C)


def l_nominal(i: float, al_nh: float = AL_NH) -> float:
    """L(I) = n AL N^2 %u(H(I)) / 100.  Source: research/inductor.json calculation 'Inductance vs current'."""
    return N_STACK * al_nh * 1e-9 * N_TURNS ** 2 * pct_mu_fit(h_oersted(i)) / 100.0


def min_curve_ratio(h: float) -> float:
    """Ratio datasheet-minimum / fitted permeability, interpolated linearly in H between the
    0058192A2 anchors (80 % at 90 Oe, 50 % at 170 Oe) and extrapolated outside them (capped at 1).
    Added assumption (verify_output_inductor engineering: 'datasheet-minimum curve')."""
    r90 = MIN_CURVE_ANCHORS["90 Oe"] / pct_mu_fit(90.0)
    r170 = MIN_CURVE_ANCHORS["170 Oe"] / pct_mu_fit(170.0)
    r = r90 + (h - 90.0) / (170.0 - 90.0) * (r170 - r90)
    return min(r, 1.0)


def l_worst(i: float) -> float:
    """Worst-case inductance: AL -8 % and the datasheet-minimum bias curve.
    L_worst(I) = (1 - 0.08) n AL N^2 min(%u_fit(H) r(H), 100) / 100."""
    pct = min(pct_mu_fit(h_oersted(i)) * min_curve_ratio(h_oersted(i)), 100.0)
    return (1.0 - AL_TOL) * N_STACK * AL_NH * 1e-9 * N_TURNS ** 2 * pct / 100.0


def l_flat80_worst(i: float) -> float:
    """Baseline hand-off variant: AL -8 % with a flat 80 % minimum (gives 235 uH at 25 A).
    Source: design_decisions.json magnetics.inductor.L_uH_worst_minus8pct_AL_min_curve."""
    pct = min(pct_mu_fit(h_oersted(i)), MIN_CURVE_ANCHORS["90 Oe"])
    return (1.0 - AL_TOL) * N_STACK * AL_NH * 1e-9 * N_TURNS ** 2 * pct / 100.0


def ripple(vin: float, l_h: float) -> float:
    """dI_L = Vout (1 - D) / (L fs).  Source: design basis (all records)."""
    return V_OUT * (1.0 - duty(vin)) / (l_h * F_SW)


def operating_point(vin: float, io: float) -> dict:
    """One corner of the operating envelope.  Formulas (research/assumptions.json, mosfet.json,
    capacitors.json, verifier-corrected):
      D = Vout/Vin; Iin = Po/(eta Vin); dI = Vout(1-D)/(L(Io) fs) with L(Io) of the real choke
      (nominal AL; AL -8 %; AL -8 % + minimum curve); I_pk = Io + dI/2;
      I_L,rms = sqrt(Io^2 + dI^2/12); I_HS,rms = sqrt(D) I_L,rms; I_LS,rms = sqrt(1-D) I_L,rms;
      I_Cin,rms = sqrt(D (Io^2 + dI^2/12) - (D Io)^2); I_Cout,rms = dI/sqrt(12);
      I_on = Io - dI/2 (HS turn-on at the valley); I_off = Io + dI/2 (HS turn-off at the peak)."""
    d = duty(vin)
    po = V_OUT * io
    l_nom = l_nominal(io)
    l_m8 = l_nominal(io, AL_NH * (1.0 - AL_TOL))
    l_w = l_worst(io)
    di = ripple(vin, l_nom)
    di_m8 = ripple(vin, l_m8)
    di_w = ripple(vin, l_w)
    il_rms = math.sqrt(io ** 2 + di ** 2 / 12.0)
    return dict(
        vin_V=vin, iout_A=io, pout_W=po, D=d,
        iin_A_eta1=input_current(vin, io, 1.0), iin_A_eta98=input_current(vin, io, 0.98),
        L_uH_nominal=l_nom * 1e6, L_uH_AL_minus8=l_m8 * 1e6, L_uH_worst_min_curve=l_w * 1e6,
        dIL_App=di, dIL_App_AL_minus8=di_m8, dIL_App_worst=di_w,
        ipk_A=io + di / 2.0, ipk_A_AL_minus8=io + di_m8 / 2.0, ipk_A_worst=io + di_w / 2.0,
        ivalley_A=io - di / 2.0,
        iL_rms_A=il_rms, iHS_rms_A=math.sqrt(d) * il_rms, iLS_rms_A=math.sqrt(1.0 - d) * il_rms,
        iCin_rms_A=math.sqrt(d * (io ** 2 + di ** 2 / 12.0) - (d * io) ** 2),
        iCout_rms_A=di / math.sqrt(12.0), iCout_rms_A_worst=di_w / math.sqrt(12.0),
        i_on_A=io - di / 2.0, i_off_A=io + di / 2.0,
        ripple_pct_of_Io=100.0 * di / io,
    )


def corner_name(op: dict) -> str:
    return f"{op['vin_V']:.0f}V/{op['iout_A']:g}A"


# --------------------------------------------------------------------------- #
# MOSFET losses (C4MS025120K) per research/mosfet.json with verifier corrections  #
# --------------------------------------------------------------------------- #
def rds_on(tj: float, r25: float = R25_15V) -> float:
    """R(T_J) = R25 [1 + (k175 - 1)(T_J - 25)/(175 - 25)], linear between the datasheet 25 and
    175 degC points (slightly conservative for a convex curve).  Source: mosfet.json
    'R_DS(on) at 150 degC' (datasheet tempco note)."""
    return r25 * (1.0 + (TEMPCO_175 - 1.0) * (tj - 25.0) / 150.0)


def rds_on_max_scaled(tj: float) -> float:
    """Maximum-R variant scaled from the only published maximum (33 mohm at 18 V):
    R_max(T) = 33 mohm [1 + 0.88 (T - 25)/150] -> 57.2 mohm at 150 degC.  A 15 V maximum is not
    published; 37 mohm (28 x 33/25) would give 64.1 mohm (reported as a sensitivity)."""
    return rds_on(tj, R25_18V_MAX)


def e_switch(e_test: float, vin: float, i: float, k_rg: float) -> float:
    """Linear scaling of a datasheet switching energy: E = E_test (Vin/V_test)(I/I_test) k_RG.
    Uncertainty about +/-30 % plus the k_RG range.  Source: mosfet.json 'High-side switching loss'."""
    return e_test * (vin / V_TEST) * (i / I_TEST) * k_rg


def e_oss(vin: float) -> float:
    """HS output-capacitance energy dissipated at turn-on: E_oss(V) = E_oss(800 V) (V/800)^1.5.
    Added by the verifier (the measured E_on does not contain the DUT's own E_oss)."""
    return E_OSS_800 * (vin / V_TEST) ** E_OSS_EXP


def v_sd(i: float) -> float:
    """Body-diode forward voltage at the actual current: V_SD(I) = 4.6 V + r_d (I - 19.6 A)
    (175 degC, V_GS = -4 V; r_d = 0.07 ohm is an added, unverified assumption)."""
    return V_SD_19P6_175 + R_D_SD * (i - 19.6)


def mosfet_losses(op: dict, r_hot: float, k_rg: float, t_dt_s: float, flat_vsd: bool = False) -> dict:
    """Per-device losses of one half-bridge pair at one corner.
      HS: P_cond = I_HS,rms^2 R(T_J); P_sw = (E_on(I_on) + E_off(I_off)) fs; P_oss = E_oss(Vin) fs
      LS: P_cond = I_LS,rms^2 R(T_J); P_rr = E_rr (Vin/800)(I_on/39.2) fs (lower bound, x2 uncertainty)
          P_dt = fs t_dt [V_SD(I_on) I_on + V_SD(I_off) I_off]  (both dead-time intervals)
      LS turn-on is ZVS-like and LS turn-off commutates into its own body diode (E_sw,LS = 0).
    Source: research/mosfet.json section 5 with verify_power_semiconductor required_changes
    (E_oss term, V_SD at the actual current, k_RG as a range, 5.5 kW normalisation)."""
    vin, io = op["vin_V"], op["iout_A"]
    i_on, i_off = op["i_on_A"], op["i_off_A"]
    hs_cond = op["iHS_rms_A"] ** 2 * r_hot
    e_on = e_switch(E_ON_TEST, vin, i_on, k_rg)
    e_off = e_switch(E_OFF_TEST, vin, i_off, k_rg)
    hs_sw = (e_on + e_off) * F_SW
    hs_oss = e_oss(vin) * F_SW
    ls_cond = op["iLS_rms_A"] ** 2 * r_hot
    ls_rr = E_RR_TEST * (vin / V_TEST) * (i_on / I_TEST) * F_SW
    if flat_vsd:
        ls_dt = F_SW * t_dt_s * V_SD_19P6_175 * (i_on + i_off)
    else:
        ls_dt = F_SW * t_dt_s * (v_sd(i_on) * i_on + v_sd(i_off) * i_off)
    p_hs = hs_cond + hs_sw + hs_oss
    p_ls = ls_cond + ls_rr + ls_dt
    return dict(
        corner=corner_name(op), R_hot_mohm=r_hot * 1e3, k_RG=k_rg, t_dt_ns=t_dt_s * 1e9,
        E_on_uJ=e_on * 1e6, E_off_uJ=e_off * 1e6, E_oss_uJ=e_oss(vin) * 1e6,
        HS_cond_W=hs_cond, HS_sw_W=hs_sw, HS_oss_W=hs_oss, HS_total_W=p_hs,
        LS_cond_W=ls_cond, LS_rr_W=ls_rr, LS_dt_W=ls_dt, LS_total_W=p_ls,
        pair_W=p_hs + p_ls, share_of_5kW_pct=100.0 * (p_hs + p_ls) / P_OUT,
        share_of_actual_Pout_pct=100.0 * (p_hs + p_ls) / op["pout_W"],
        V_SD_on_V=v_sd(i_on), V_SD_off_V=v_sd(i_off),
    )


def utilisation(vin: float, l_loop_h: float, di_dt: float = DI_DT_DESIGN) -> dict:
    """V_pk = Vin + L_loop di/dt; U = V_pk / V_DS,max.  Source: mosfet.json 'Switching overshoot
    and utilisation' (KR-PCB-004 / PE-PCB-003 context; limits are engineering judgement)."""
    v_os = l_loop_h * di_dt
    return dict(vin_V=vin, L_loop_nH=l_loop_h * 1e9, V_os_V=v_os, V_pk_V=vin + v_os, utilisation=(vin + v_os) / V_DS_MAX)


def parasitic_turn_on(q_gd: float, t_edge: float, r_path: float) -> float:
    """Charge-based off-state excursion: the Miller charge Q_gd(0-400 V) is injected as a current
    I = Q/t_edge into C_iss in parallel with the off path R:  dV = I R (1 - exp(-t_edge/(R C_iss))).
    Source: verify_power_semiconductor engineering (charge-based method replaces C_rss dv/dt R)."""
    tau = r_path * C_ISS
    return (q_gd / t_edge) * r_path * (1.0 - math.exp(-t_edge / tau))


# --------------------------------------------------------------------------- #
# Gate drive, bias supply, dv/dt                                              #
# --------------------------------------------------------------------------- #
def gate_power_wolfspeed() -> float:
    """KR-IS-001 (Wolfspeed PRD-09301 Eq. 1): P_g = Q_G f_sw (V_DD - V_EE)."""
    return Q_G * F_SW * (V_DD - V_EE)


def gate_power_ti() -> float:
    """KR-IS-001 recorded conflict (TI TIDA-010054 Eq. 30, EC-014): P_g = 2 Q_G f_sw (V_DD - V_EE)."""
    return 2.0 * gate_power_wolfspeed()


def peak_gate_currents() -> dict:
    """I_pk,on = (V_DD - V_EE)/(R_on + R_int + R_OUTH); I_pk,off = (V_DD - V_EE)/(R_off + R_int + R_OUTL).
    Source: research/gate_driver.json 'Peak gate currents' (SKILL-001 principle 4)."""
    sw = V_DD - V_EE
    return dict(
        source_A_10ohm=sw / (R_G_ON + R_G_INT + R_OUTH[1]),
        source_A_10ohm_range=[sw / (R_G_ON + R_G_INT + R_OUTH[2]), sw / (R_G_ON + R_G_INT + R_OUTH[0])],
        source_A_6p8ohm=sw / (R_G_ON_TUNE + R_G_INT + R_OUTH[1]),
        sink_A=sw / (R_G_OFF + R_G_INT + R_OUTL[1]),
        sink_A_range=[sw / (R_G_OFF + R_G_INT + R_OUTL[2]), sw / (R_G_OFF + R_G_INT + R_OUTL[0])],
        driver_capability_A=10.0,
    )


def gate_resistor_power() -> dict:
    """Average P_R = 0.5 Q_G dV f_sw R/R_total (half the gate energy per edge, shared by resistance);
    pulse P = I_pk^2 R for tau = R_total C_iss.  Source: research/gate_driver.json."""
    pg = gate_power_wolfspeed()
    r_on_tot = R_G_ON + R_G_INT + R_OUTH[1]
    r_off_tot = R_G_OFF + R_G_INT + R_OUTL[1]
    ipk = peak_gate_currents()
    return dict(
        R_on_avg_W=0.5 * pg * R_G_ON / r_on_tot, R_on_pulse_W=ipk["source_A_10ohm"] ** 2 * R_G_ON,
        R_on_tau_ns=r_on_tot * C_ISS * 1e9,
        R_off_avg_W=0.5 * pg * R_G_OFF / r_off_tot, R_off_pulse_W=ipk["sink_A"] ** 2 * R_G_OFF,
        R_off_tau_ns=r_off_tot * C_ISS * 1e9, package_rating_W=0.66,
    )


def decoupling() -> dict:
    """KR-PCB-002 derivation: C_eff >= Q_G/dV; C_nom = C_eff/(1 - k_bias); droop = Q_G / C_eff,fitted.
    Source: research/gate_driver.json 'Rail decoupling from gate charge' (COM-VEE droop 41 mV per verifier)."""
    c_req = Q_G / DV_DROOP_SPEC
    return dict(
        C_eff_required_uF=c_req * 1e6, C_nominal_required_uF=c_req / (1.0 - K_X7R_LOSS) * 1e6,
        VDD_COM_fitted_uF=C_DECOUP_VDD * 1e6, VDD_COM_effective_uF=C_DECOUP_VDD * (1.0 - K_X7R_LOSS) * 1e6,
        VDD_COM_droop_mV=Q_G / (C_DECOUP_VDD * (1.0 - K_X7R_LOSS)) * 1e3,
        COM_VEE_fitted_uF=C_DECOUP_VEE * 1e6, COM_VEE_droop_mV=Q_G / (C_DECOUP_VEE * (1.0 - K_X7R_LOSS)) * 1e3,
    )


def bias_budget() -> dict:
    """Per-module output budget (KR-IS-001 both forms) and 12 V input current:
      P_gate_ch = P_g + I_VDDQ,max (V_DD - V_EE) + P_DESAT + P_misc
      P_sens = (2 I_DD1,max + I_misc) (V_DD - V_EE)_sens  with the COM-VEE 5 V output fed from the 15 V rail
      P_in,module = 0.48 W + 1.92 P_out (SLUSF10B interpolation); I_12V = sum P_in / V_aux.
    Source: research/gate_driver.json, controller_aux_interconnect.json, CR-12 (sensing module)."""
    sw = V_DD - V_EE
    pg_ws, pg_ti = gate_power_wolfspeed(), gate_power_ti()
    pq = I_VDDQ_MAX * sw
    gate_ch_ws = pg_ws + pq + P_DESAT_BIAS + P_MISC_CH
    gate_ch_ti = pg_ti + pq + P_DESAT_BIAS + P_MISC_CH
    i_sens = 2 * I_AMC_VDD1_MAX + I_SENS_MISC
    v_sens_dd = 15.0  # VDD-VEE of the sensing module (CR-12)
    v_sens_com = 5.0
    p_sens_load = i_sens * v_sens_com
    p_sens_module = i_sens * v_sens_dd  # COM-VEE regulator sources from VDD through RLIM
    p_rlim_sens = i_sens * (v_sens_dd - v_sens_com)
    rlim_max_sens = (v_sens_dd - v_sens_com) / i_sens - R_LIM_INT
    budget = {"hs_gate": max(gate_ch_ws, 0.32), "ls_gate": max(gate_ch_ws, 0.32), "sensing": P_SENS_BUDGET}
    p_in = {k: P_BIAS_IN_NOLOAD + K_BIAS_IN * v for k, v in budget.items()}
    p_in_total = sum(p_in.values())
    return dict(
        P_gate_channel_W_wolfspeed_form=gate_ch_ws, P_gate_channel_W_TI_form=gate_ch_ti,
        P_quiescent_W=pq, P_DESAT_bias_W=P_DESAT_BIAS, P_misc_W=P_MISC_CH,
        sensing_load_mA=i_sens * 1e3, sensing_load_W_at_5V=p_sens_load, sensing_module_output_W_at_15V=p_sens_module,
        sensing_RLIM_dissipation_W=p_rlim_sens, sensing_RLIM_max_ohm=rlim_max_sens,
        budget_W=budget, utilisation_of_1p5W_rating={k: v / P_BIAS_RATING for k, v in budget.items()},
        P_in_W_per_module=p_in, P_in_total_W=p_in_total,
        I_12V_A_at_12V=p_in_total / V_AUX_NOM, I_12V_A_at_10p8V=p_in_total / V_AUX_MIN,
        I_12V_A_at_10p8V_with_20pct_margin=1.2 * p_in_total / V_AUX_MIN,
        baseline_budget_A_at_10p8V=AUX_BUDGET_10P8["gate_bias_modules"] + AUX_BUDGET_10P8["sensing_bias_module"],
    )


def dv_dt_and_cmti(op: dict) -> dict:
    """Turn-off dv/dt (load-current limited): dv/dt = I_off / (2 C_oss(400 V)); CMTI margin = 150 / dv/dt.
    Common-mode current through the HS barriers: i_CM = (C_IO,bias + C_IO,driver) dv/dt (KR-IS-003).
    Source: research/gate_driver.json."""
    dvdt = op["i_off_A"] / (2.0 * C_OSS_400)  # V/s
    return dict(corner=corner_name(op), turn_off_dv_dt_V_per_ns=dvdt / 1e9, CMTI_margin=CMTI_MIN / (dvdt / 1e9),
                i_CM_A_3p5pF=(C_IO_BIAS[0] + C_IO_DRV) * V_DV_DT_ENVELOPE * 1e9,
                i_CM_A_5pF_bound=(C_IO_BIAS[1] + C_IO_DRV) * V_DV_DT_ENVELOPE * 1e9)


def gate_loop_damping() -> dict:
    """Z0 = sqrt(L_g / C_iss); zeta = R_total / (2 Z0).  Source: research/gate_driver.json (KR-GD-001/012)."""
    z0 = math.sqrt(L_GATE_LOOP / C_ISS)
    return dict(Z0_ohm=z0, zeta_on=(R_G_ON + R_G_INT + R_OUTH[1]) / (2 * z0), zeta_off=(R_G_OFF + R_G_INT + R_OUTL[1]) / (2 * z0))


# --------------------------------------------------------------------------- #
# DESAT (CB-GD-001 EC-001 / EC-002 patterns) and dead time (KR-GD-009)        #
# --------------------------------------------------------------------------- #
def desat() -> dict:
    """Trip: V_A = V_OCTH (R2 + R3)/R3; V_DS,trip = V_A - V_F.
    Trip current (linear estimate): I_trip = V_DS,trip / R_DS(on)(175 degC) over the R spread.
    False-trip margin: V_OC = (I_pk,ovl R_hot + V_F) R3/(R2 + R3) against V_OCTH,min.
    Blanking: V_th = V_DD R3/(R1+R2+R3); R_th = R3 (R1+R2)/(R1+R2+R3); t_bl = -R_th C ln(1 - V_OCTH/V_th).
    Response: t = t_bl + t_OCOFF + Q(15 V -> 3 V)/I_STO.  Source: research/gate_driver.json with
    verify_isolated_gate_driver corrections (R_DS(on) spread, 1.67x / 1.35x margins)."""
    k = (R2_DESAT + R3_DESAT) / R3_DESAT
    v_a = [v * k for v in V_OCTH]
    v_trip = [v - V_F_DESAT for v in v_a]
    r_hot_typ18 = R25_18V_TYP * TEMPCO_175
    r_hot_typ15 = R25_15V * TEMPCO_175
    r_hot_max = R25_15V * (R25_18V_MAX / R25_18V_TYP) * TEMPCO_175  # 15 V-equivalent maximum (28 x 33/25 x 1.88 = 69.5 mohm), the baseline's convention
    i_trip_typ = v_trip[1] / r_hot_typ15
    i_trip_min = v_trip[1] / r_hot_max  # typical trip voltage, maximum R (baseline '52 A')
    i_trip_abs_min = v_trip[0] / r_hot_max
    i_trip_max = v_trip[2] / r_hot_typ18
    v_oc_ovl_typ = (I_PK_OVL_WORST * r_hot_typ15 + V_F_DESAT) / k
    v_oc_ovl_max = (I_PK_OVL_WORST * r_hot_max + V_F_DESAT) / k
    r_sum = R1_DESAT + R2_DESAT + R3_DESAT
    v_th = V_DD * R3_DESAT / r_sum
    r_th = R3_DESAT * (R1_DESAT + R2_DESAT) / r_sum
    t_bl = [-r_th * C_BLANK * math.log(1.0 - v / v_th) for v in V_OCTH]
    v_th18 = 18.0 * R3_DESAT / r_sum
    t_bl_18 = -r_th * C_BLANK * math.log(1.0 - V_OCTH[1] / v_th18)
    t_resp = [t_bl[0] + T_OCOFF[0] * 1e-9 + Q_GATE_15_TO_3 / I_STO[2],
              t_bl[1] + T_OCOFF[1] * 1e-9 + Q_GATE_15_TO_3 / I_STO[1],
              t_bl[2] + T_OCOFF[2] * 1e-9 + Q_GATE_15_TO_3 / I_STO[0]]
    # soft turn-off fault overshoot (KR-GD-011): dV_GS/dt = I_STO / C_iss; di/dt = I_sc / t(5 V of gate swing)
    dvgs_dt = I_STO[1] / C_ISS
    t_cut = 5.0 / dvgs_dt
    i_sc = 250.0
    di_dt_fault = i_sc / t_cut
    v_pk_fault = VIN_OVP + L_LOOP[1] * 1e-9 * di_dt_fault
    return dict(
        V_A_V=v_a, V_DS_trip_V=v_trip,
        R_hot_175C_mohm={"typ_18V": r_hot_typ18 * 1e3, "typ_15V": r_hot_typ15 * 1e3, "max_scaled": r_hot_max * 1e3},
        I_trip_A={"min_typV_maxR": i_trip_min, "min_absolute_minV_maxR": i_trip_abs_min, "typ_linear": i_trip_typ, "max": i_trip_max, "baseline_graph_read": "52-85 (75 typical)"},
        trip_over_overload_peak={"min": i_trip_min / I_PK_OVL_WORST, "typ": i_trip_typ / I_PK_OVL_WORST},
        false_trip_margin={"typ": V_OCTH[0] / v_oc_ovl_typ, "max_R": V_OCTH[0] / v_oc_ovl_max,
                           "V_OC_at_overload_V_typ": v_oc_ovl_typ, "V_OC_at_overload_V_maxR": v_oc_ovl_max},
        blanking={"V_th_V": v_th, "R_th_ohm": r_th, "t_bl_ns_min_typ_max": [t * 1e9 for t in t_bl],
                  "t_bl_ns_typ_at_18V": t_bl_18 * 1e9, "ic_deglitch_ns": T_OCFIL},
        response_us_min_typ_max=[t * 1e6 for t in t_resp], response_budget_us=1.5,
        fault_turn_off={"gate_slew_V_per_ns": dvgs_dt / 1e9, "cut_off_ns": t_cut * 1e9, "I_sc_assumed_A": i_sc,
                        "di_dt_A_per_ns": di_dt_fault / 1e9, "V_pk_V_at_460V_35nH": v_pk_fault,
                        "utilisation": v_pk_fault / V_DS_MAX},
        withstand_note="Wolfspeed publishes no short-circuit withstand time for C4MS025120K; KR-PR-001 compliance by destructive test",
    )


def dead_time() -> dict:
    """Minimum: t_dt >= skew + PWD + td(off) + t_f - td(on), x1.5 margin.  Programmed 300 ns = 45 TBCLK
    ticks; effective = programmed - erosion (30 ns skew + 5 ns RC mismatch).
    Source: research/gate_driver.json 'Dead-time requirement', controller_aux_interconnect.json, CR-07."""
    t_min_raw = T_SKEW + T_PWD + TD_OFF_NS + TF_NS - TD_ON_NS
    tick_ns = 1e9 / TBCLK
    return dict(
        raw_requirement_ns=t_min_raw, minimum_with_1p5_margin_ns=1.5 * t_min_raw,
        minimum_adopted_ns=DEAD_TIME["minimum"], programmed_ns=DEAD_TIME["programmed_bring_up"],
        programmed_ticks=DEAD_TIME["programmed_bring_up"] / tick_ns, tick_ns=tick_ns,
        effective_after_erosion_ns=DEAD_TIME["programmed_bring_up"] - DT_EROSION_NS,
        effective_target_ns=DEAD_TIME["effective_target"], upper_bound_ns=DEAD_TIME["upper_bound"],
        TBPRD_up_down=TBCLK / (2 * F_SW), duty_resolution_pct=100.0 / (TBCLK / (2 * F_SW)),
        loss_sensitivity_W_per_100ns=P_DT_SENS_W_PER_100NS,
    )


# --------------------------------------------------------------------------- #
# Inductor (research/inductor.json with verify_output_inductor corrections)   #
# --------------------------------------------------------------------------- #
def b_dc(h: float) -> float:
    """DC flux density of High Flux 60u: B = ((a + bH + cH^2)/(1 + dH + eH^2))^x, T, Oe.
    Source: Magnetics catalogue 2024 p.129/130."""
    a, b, c, d, e, x = BDC_COEF
    return ((a + b * h + c * h * h) / (1.0 + d * h + e * h * h)) ** x


def flux_swing(vin: float) -> float:
    """dB = Vout (1 - D) / (N n Ae fs) (volt-second balance, independent of L).  Source: inductor.json."""
    return V_OUT * (1.0 - duty(vin)) / (N_TURNS * N_STACK * AE_CORE * F_SW)


def core_loss_density(b_pk: float) -> float:
    """Pv[mW/cm3] = 246.54 B_pk[T]^2.218 f[kHz]^1.311.  Source: Magnetics catalogue 2024 p.109."""
    return PV_A * b_pk ** PV_B * (F_SW / 1e3) ** PV_C


def r_dc(t_c: float) -> float:
    """R_dc(T) = rho20 (1 + alpha (T - 20)) N MLT / A_w.  Source: inductor.json 'DC copper resistance'."""
    return RHO_20 * (1.0 + ALPHA_CU * (t_c - 20.0)) * L_WIRE / A_W


def dowell_single_layer() -> dict:
    """delta = sqrt(rho/(pi f mu0)); x = (pi/4)^0.75 (d/delta) sqrt(0.85); F_R = x (sinh2x + sin2x)/(cosh2x - cos2x).
    Source: inductor.json 'Skin depth and AC copper loss' (added assumption: single-layer Dowell)."""
    rho = RHO_20 * (1.0 + ALPHA_CU * (T_CU - 20.0))
    delta = math.sqrt(rho / (math.pi * F_SW * 4e-7 * math.pi))
    x = (math.pi / 4.0) ** 0.75 * (D_W / delta) * math.sqrt(0.85)
    fr = x * (math.sinh(2 * x) + math.sin(2 * x)) / (math.cosh(2 * x) - math.cos(2 * x))
    return dict(skin_depth_mm=delta * 1e3, d_over_delta=D_W / delta, x=x, F_R=fr)


def inductor_corner(op: dict, k_core: float = 1.0) -> dict:
    """Losses at one corner: P_core = Pv(B_pk) Ve k_wave k_core; P_dc = Io^2 R_dc(100 degC);
    P_ac = 1.02 F_R R_dc dI^2/12; P_tot = P_core + P_dc + P_ac.  k_core = 1 (typical fit) or 1.44
    (datasheet maximum), optionally times the DC-bias allowance 1.2-1.3."""
    db = flux_swing(op["vin_V"])
    b_pk = db / 2.0
    pv = core_loss_density(b_pk) * k_core
    p_core = pv * VE_STACK_CM3 * K_WAVEFORM / 1e3
    rdc = r_dc(T_CU)
    fr = dowell_single_layer()["F_R"]
    p_dc = op["iout_A"] ** 2 * rdc
    p_ac = 1.02 * fr * rdc * op["dIL_App"] ** 2 / 12.0
    h = h_oersted(op["ipk_A"])
    return dict(corner=corner_name(op), dB_mT=db * 1e3, B_pk_ac_mT=b_pk * 1e3, Pv_mW_cm3=pv, P_core_W=p_core,
                P_cu_dc_W=p_dc, P_cu_ac_W=p_ac, P_total_W=p_core + p_dc + p_ac,
                B_dc_at_peak_T=b_dc(h), B_total_at_peak_T=b_dc(h) + b_pk, k_core=k_core)


def temperature_rise(p_w: float) -> float:
    """dT = (P[mW] / A_s[cm2])^0.833 (Magnetics still-air correlation; average surface rise)."""
    return (p_w * 1e3 / A_SURF_CM2) ** DT_EXP


def i_sat_30pct(worst: bool) -> float:
    """Vendor-style I_sat: current at which L falls to 70 % of L(0 A), solved by bisection on the
    nominal or worst-case curve.  Source: verify_output_inductor engineering (37.3 A / ~35 A)."""
    f = l_worst if worst else l_nominal
    target = 0.70 * f(0.0)
    lo, hi = 0.0, 80.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def i_at_ratio_of_l25(ratio: float) -> float:
    """Current at which L(I) = ratio x L(25 A) on the nominal curve (bisection)."""
    target = ratio * l_nominal(I_OUT)
    lo, hi = I_OUT, 120.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if l_nominal(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def inductor_summary(ops: list[dict]) -> dict:
    i_margin = I_MARGIN_FACTOR * max(op["ipk_A_AL_minus8"] for op in ops if op["iout_A"] == I_OVL)
    i41 = 41.0
    l_table = {}
    for i in (0.0, 5.0, 12.5, 20.0, 25.0, 27.5, 28.7, 31.6, 41.0, 46.0, 55.0):
        l_table[f"{i:g}A"] = dict(H_Oe=h_oersted(i), pct_mu=pct_mu_fit(h_oersted(i)), L_uH_nominal=l_nominal(i) * 1e6,
                                 L_uH_AL_minus8=l_nominal(i, AL_NH * (1 - AL_TOL)) * 1e6,
                                 L_uH_AL_plus8=l_nominal(i, AL_NH * (1 + AL_TOL)) * 1e6,
                                 L_uH_worst_min_curve=l_worst(i) * 1e6, L_uH_worst_flat80=l_flat80_worst(i) * 1e6)
    corners_typ = [inductor_corner(op) for op in ops]
    corners_max = [inductor_corner(op, K_CORE_MAX) for op in ops]
    corners_bounded = [inductor_corner(op, K_CORE_MAX * K_BIAS_LOSS[1]) for op in ops]
    worst_typ = max(corners_typ, key=lambda c: c["P_total_W"])
    worst_bounded = max(corners_bounded, key=lambda c: c["P_total_W"])
    nominal_440 = next(c for c in corners_typ if c["corner"] == "440V/25A")
    dt_nom = temperature_rise(nominal_440["P_total_W"])
    dt_ovl = temperature_rise(worst_typ["P_total_W"])
    dt_bounded_lo = temperature_rise(max(c["P_total_W"] for c in corners_max))
    dt_bounded_hi = temperature_rise(worst_bounded["P_total_W"])
    p_max = A_SURF_CM2 * (T_HOT_LIMIT - T_A) ** (1.0 / DT_EXP) / 1e3
    h25, h41 = h_oersted(I_OUT), h_oersted(i41)
    return dict(
        L_vs_I=l_table, i_margin_A=i_margin,
        saturation={
            "L41_over_L25_nominal": l_nominal(i41) / l_nominal(I_OUT),
            "L41_over_L25_worst_min_curve": l_worst(i41) / l_worst(I_OUT),
            "L41_over_L25_worst_flat80_handoff": l_flat80_worst(i41) / l_flat80_worst(I_OUT),
            "criterion_ratio": L_RATIO_MIN,
            "B_dc_41A_T": b_dc(h41), "B_ac_pk_440V_T": flux_swing(440.0) / 2.0,
            "B_total_41A_T": b_dc(h41) + flux_swing(440.0) / 2.0, "B_limit_T": B_RATIO_MAX * B_SAT,
            "B_dc_25A_T": b_dc(h25),
            "I_sat_30pct_drop_from_L0_A_nominal": i_sat_30pct(False), "I_sat_30pct_drop_from_L0_A_worst": i_sat_30pct(True),
            "I_at_70pct_of_L25_A": i_at_ratio_of_l25(0.70), "I_at_50pct_of_L0_A": i_at_ratio_of_l25(0.5 * l_nominal(0.0) / l_nominal(I_OUT)),
        },
        copper={"R_dc_20C_mohm": r_dc(20.0) * 1e3, "R_dc_100C_mohm": r_dc(T_CU) * 1e3, **dowell_single_layer(),
                "lead_allowance_note": "about 0.25 m of leads (+1 mohm, +0.6 W at 25 A) not included (verifier)"},
        corners_typical_core=corners_typ, corners_datasheet_max_core=corners_max, corners_bounded_core=corners_bounded,
        thermal={"surface_rise_K_440V_25A": dt_nom, "surface_rise_K_overload": dt_ovl,
                 "surface_rise_K_bounded_range": [dt_bounded_lo, dt_bounded_hi],
                 "hot_spot_C_typ_overload": [T_A + dt_nom + HOT_SPOT_ALLOW[0], T_A + dt_ovl + HOT_SPOT_ALLOW[1]],
                 "hot_spot_C_bounded": [T_A + dt_bounded_lo + HOT_SPOT_ALLOW[0], T_A + dt_bounded_hi + HOT_SPOT_ALLOW[1]],
                 "P_max_W_at_125C_hot_spot": p_max, "margin_over_overload_loss": p_max / worst_typ["P_total_W"],
                 "margin_over_bounded_loss": p_max / worst_bounded["P_total_W"],
                 "R_th_equivalent_K_per_W": dt_nom / nominal_440["P_total_W"],
                 "acceptance_thermocouple_C": T_HOT_ACCEPT},
        no_load_ccm_reverse_current_A=[-(ripple(v, l_nominal(0.0)) / 2.0) for v in VIN_LIST],
        load_transient_slew_A_per_us=[(v - V_OUT) / l_nominal(I_OUT) / 1e6 for v in VIN_LIST],
    )


# --------------------------------------------------------------------------- #
# Capacitors (research/capacitors.json with verify_dc_link corrections)       #
# --------------------------------------------------------------------------- #
def input_capacitors(ops: list[dict]) -> dict:
    """KR-CAP-001: dQ = D(1-D) Io Ts (exact because Io - dI/2 > D Io at all corners); C_in >= dQ_max/dV.
    Realised ripple: dV = dQ/C_min + ESR_bank I_C,pp with I_C,pp = Io + dI/2 (verifier-corrected).
    KR-CAP-002: I_part = I_Cin,rms/2; P = I^2 ESR; R_th = dT_rated/(I_rated^2 ESR); dT = P R_th.
    HF tier: C_eff = n C (1 - loss); f_r = 1/(2 pi sqrt(L_int C_eff)); Z0 = sqrt(L_int/C_eff);
    quarter-period dip dV = I_pk T/4 / C_eff (conservative) and exact step dip I_pk Z0.
    Ring: E = 0.5 L_int (I_off^2 + I_on^2) per period -> P = E fs (dissipated in the loop resistance,
    independent of Q); ring RMS I^2 = sum (I0^2/2)(tau/2)/Ts with tau = 2 L_int/R_loop."""
    ts = 1.0 / F_SW
    rows = []
    for op in ops:
        d, io = op["D"], op["iout_A"]
        rows.append(dict(corner=corner_name(op), dQ_uC=d * (1 - d) * io * ts * 1e6, exact=(op["ivalley_A"] > d * io),
                         iCin_rms_A=op["iCin_rms_A"], iCin_pp_A=io + op["dIL_App"] / 2.0))
    dq_max = max(r["dQ_uC"] for r in rows) * 1e-6
    dv_allow = VIN_RIPPLE_PCT / 100.0 * 400.0
    c_min = C_IN_FILM_QTY * C_IN_FILM_EACH * (1 - C_TOL)
    esr_bank = ESR_IN_EACH / C_IN_FILM_QTY
    worst = max(rows, key=lambda r: r["iCin_rms_A"])
    i_part = worst["iCin_rms_A"] / C_IN_FILM_QTY
    p_part = i_part ** 2 * ESR_IN_EACH
    r_th = DT_RATED_IN / (I_RMS_IN_RATING ** 2 * ESR_IN_EACH)
    dt_self = p_part * r_th
    # HF tier and ring
    c_eff = C_HF_QTY * C_HF_EACH * K_HF_BIAS_REMAIN
    ovl440 = next(op for op in ops if op["vin_V"] == 440.0 and op["iout_A"] == I_OVL)
    i_off, i_on = ovl440["i_off_A"], ovl440["i_on_A"]
    hf = []
    for l_nh in L_INT_LIST:
        l_int = l_nh * 1e-9
        f_r = 1.0 / (2 * math.pi * math.sqrt(l_int * c_eff))
        z0 = math.sqrt(l_int / c_eff)
        e_ring = 0.5 * l_int * (i_off ** 2 + i_on ** 2)
        rms = []
        for r_loop in R_LOOP_RANGE:
            tau = 2 * l_int / r_loop
            i2 = (i_off ** 2 / 2.0) * (tau / 2.0) / ts + (i_on ** 2 / 2.0) * (tau / 2.0) / ts
            rms.append(math.sqrt(i2))
        hf.append(dict(L_int_nH=l_nh, f_r_kHz=f_r / 1e3, Z0_ohm=z0, quarter_period_ns=0.25 / f_r * 1e9,
                       dQ_uC=i_off * 0.25 / f_r * 1e6, dip_V_quarter_period=i_off * 0.25 / f_r / c_eff,
                       dip_V_exact_IZ0=i_off * z0, dip_pct_of_440V=100.0 * i_off * 0.25 / f_r / c_eff / 440.0,
                       ring_energy_uJ_per_period=e_ring * 1e6, ring_loss_W=e_ring * F_SW,
                       ring_rms_A_total_range=rms, ring_rms_A_per_MLCC_range=[x / C_HF_QTY for x in rms],
                       Q_range=[math.sqrt(l_int / c_eff) / r for r in R_LOOP_RANGE][::-1]))
    hf30 = hf[1]
    film_ring_share = (esr_bank / (esr_bank + 0.008)) * hf30["ring_loss_W"]  # film ESR vs ~8 mohm total loop
    return dict(
        rows=rows, dQ_max_uC=dq_max * 1e6, dV_allowed_Vpp=dv_allow,
        C_in_required_uF=dq_max / dv_allow * 1e6, C_in_required_nominal_uF=dq_max / dv_allow / (1 - C_TOL) * 1e6,
        C_in_nominal_uF=C_IN_FILM_QTY * C_IN_FILM_EACH * 1e6, C_in_min_uF=c_min * 1e6,
        ripple_Vpp_27p5A=dq_max / c_min + esr_bank * (I_OVL + ovl440["dIL_App"] / 2.0),
        ripple_pct_27p5A=100.0 * (dq_max / c_min + esr_bank * (I_OVL + ovl440["dIL_App"] / 2.0)) / 400.0,
        ripple_Vpp_25A=max(r["dQ_uC"] for r in rows if r["corner"].endswith("/25A")) * 1e-6 / c_min
        + esr_bank * (I_OUT + next(op for op in ops if op["vin_V"] == 440.0 and op["iout_A"] == I_OUT)["dIL_App"] / 2.0),
        film={"I_rms_each_A_worst": i_part, "rating_A": I_RMS_IN_RATING, "margin": I_RMS_IN_RATING / i_part,
              "P_each_W": p_part, "R_th_K_per_W": r_th, "dT_self_K": dt_self,
              "ring_share_each_W": film_ring_share / C_IN_FILM_QTY,
              "dT_with_ring_K": (p_part + film_ring_share / C_IN_FILM_QTY) * r_th,
              "hotspot_C": T_A + T_AIR_LOCAL + (p_part + film_ring_share / C_IN_FILM_QTY) * r_th,
              "voltage_ratio_440_460_480": [440.0 / V_R_IN, VIN_OVP / V_R_IN, VIN_SURV / V_R_IN]},
        hf_tier={"C_nominal_uF": C_HF_QTY * C_HF_EACH * 1e6, "C_effective_uF_at_440V": c_eff * 1e6, "requirement_uF": 1.5,
                 "fifty_kHz_share_A": worst["iCin_rms_A"] * c_eff / (c_min + c_eff),
                 "per_MLCC_50kHz_mA": worst["iCin_rms_A"] * c_eff / (c_min + c_eff) / C_HF_QTY * 1e3,
                 "voltage_ratio_440_480": [440.0 / 630.0, VIN_SURV / 630.0], "by_interconnect": hf},
        stored_energy_J_440V=0.5 * C_IN_FILM_QTY * C_IN_FILM_EACH * (1 + C_TOL) * 440.0 ** 2,
    )


def output_capacitors(ops: list[dict]) -> dict:
    """Ripple: dV = dI/(8 fs C_min) + ESR dI (C >= dI/(8 fs (dV - ESR dI)) for the 2 Vpp spec).
    Load step: dV = dI_step/(2 pi f_c C_min) + ESR dI_step; load dump 25 A and 27.5 A likewise, compared
    with the 230 V output OVP; LI^2 energy floor: dV = sqrt(V^2 + L I_pk^2 / C) - V.
    KR-CAP-002: I_Cout,rms = dI/sqrt(12) shared by two parts.  Source: research/capacitors.json."""
    c_min = C_OUT_FILM_QTY * C_OUT_FILM_EACH * (1 - C_TOL)
    esr_bank = ESR_OUT_EACH / C_OUT_FILM_QTY
    di_worst = max(op["dIL_App_worst"] for op in ops)
    di_220 = ripple(440.0, 220e-6)
    rows = []
    for fc in FC_LIST:
        rows.append(dict(fc_Hz=fc,
                         step_12p5A_V=I_STEP / (2 * math.pi * fc * c_min) + esr_bank * I_STEP,
                         dump_25A_V=I_OUT / (2 * math.pi * fc * c_min) + esr_bank * I_OUT,
                         dump_27p5A_V=I_OVL / (2 * math.pi * fc * c_min) + esr_bank * I_OVL,
                         C_required_for_10V_uF=I_STEP / (2 * math.pi * fc * (V_STEP_MAX - esr_bank * I_STEP)) * 1e6))
    ipk_nom = max(op["ipk_A"] for op in ops if op["iout_A"] == I_OUT)
    l_pk = l_nominal(ipk_nom)
    dv_li2 = math.sqrt(V_OUT ** 2 + l_pk * ipk_nom ** 2 / c_min) - V_OUT
    i_rms = di_worst / math.sqrt(12.0)
    return dict(
        C_nominal_uF=C_OUT_FILM_QTY * C_OUT_FILM_EACH * 1e6, C_min_uF=c_min * 1e6, ESR_bank_mohm=esr_bank * 1e3,
        ripple_Vpp_worst_real_choke=di_worst / (8 * F_SW * c_min) + esr_bank * di_worst,
        ripple_Vpp_220uH_bound=di_220 / (8 * F_SW * c_min) + esr_bank * di_220,
        C_required_for_2Vpp_uF=di_220 / (8 * F_SW * (VOUT_RIPPLE_MAX - esr_bank * di_220)) * 1e6,
        I_rms_total_A=i_rms, I_rms_each_A=i_rms / C_OUT_FILM_QTY, rating_A=I_RMS_OUT_RATING,
        margin=I_RMS_OUT_RATING / (i_rms / C_OUT_FILM_QTY), P_each_W=(i_rms / C_OUT_FILM_QTY) ** 2 * ESR_OUT_EACH,
        transients=rows, load_dump_peak_V_fc2kHz=V_OUT + rows[0]["dump_25A_V"], load_dump_peak_V_fc2p5kHz=V_OUT + rows[1]["dump_25A_V"],
        load_dump_27p5A_peak_V_fc2kHz=V_OUT + rows[0]["dump_27p5A_V"], ovp_out_V=VOUT_OVP,
        LI2_energy_excursion_V=dv_li2, lc_corner_Hz=1.0 / (2 * math.pi * math.sqrt(l_nominal(I_OUT) * C_OUT_FILM_QTY * C_OUT_FILM_EACH)),
        voltage_ratio_200_220_440fault=[V_OUT / V_R_OUT, 220.0 / V_R_OUT, 440.0 / V_R_OUT],
    )


def discharge_coupled(c_in: float, c_out: float, r_in: float, r_out: float, v_in0: float, v_out0: float,
                      dt: float = 1e-3) -> dict:
    """Two-bank RC decay with an ideal-diode coupling (HS body diode through L) whenever
    V_out - V_in > 0.7 V: charge is shared until V_out = V_in + 0.7 V.  Source: research/capacitors.json
    'Bleeder discharge time (coupled banks)'."""
    vin, vout, t = v_in0, v_out0, 0.0
    t_in = t_out = None
    coupled = False
    while (vin > V_SAFE or vout > V_SAFE) and t < 1000.0:
        if vout - vin > 0.7:
            q = c_in * vin + c_out * vout
            vin = (q - c_out * 0.7) / (c_in + c_out)
            vout = vin + 0.7
            coupled = True
        vin -= vin / r_in * dt / c_in
        vout -= vout / r_out * dt / c_out
        t += dt
        if t_in is None and vin <= V_SAFE:
            t_in = t
        if t_out is None and vout <= V_SAFE:
            t_out = t
    return dict(time_to_both_below_60V_s=t, input_s=t_in, output_s=t_out, coupling_acted_above_60V=coupled)


def bleeders() -> dict:
    """Merged networks (CR-03): R_in = 360 k || 450 k (indicator chain), R_out = 200 k || 200 k.
    Dissipation P = V^2/R; element stress V_elem = V/n, P_elem = V_elem^2/R_elem; discharge by the
    coupled two-bank model from 460/200 V and 480/220 V; bleeder-only variant and the 5 s option
    (R <= t/(C ln(V0/60))) for comparison.  Source: capacitors.json, standards_safety.json, CR-03."""
    r_in = 1.0 / (1.0 / R_BL_IN + 1.0 / R_IND_IN)
    r_out = 1.0 / (1.0 / R_BL_OUT + 1.0 / R_IND_OUT)
    merged = discharge_coupled(C_IN_DISCHARGE, C_OUT_DISCHARGE, r_in, r_out, VIN_OVP, V_OUT)
    merged_480 = discharge_coupled(C_IN_DISCHARGE, C_OUT_DISCHARGE, r_in, r_out, VIN_SURV, 220.0)
    bleed_only = discharge_coupled(C_IN_DISCHARGE, C_OUT_DISCHARGE, R_BL_IN, R_BL_OUT, VIN_OVP, V_OUT)
    bleed_only_480 = discharge_coupled(C_IN_DISCHARGE, C_OUT_DISCHARGE, R_BL_IN, R_BL_OUT, VIN_SURV, 220.0)

    def elem(v, r_total, n):
        return dict(V_per_element_V=v / n, P_per_element_W=(v / n) ** 2 / (r_total / n))

    r5_in_nom = 5.0 / (40e-6 * math.log(VIN_SURV / V_SAFE))
    r5_out_nom = 5.0 / (120e-6 * math.log(220.0 / V_SAFE))
    r5_in_eff = 5.0 / (C_IN_DISCHARGE * math.log(VIN_SURV / V_SAFE))
    r5_out_eff = 5.0 / (C_OUT_DISCHARGE * math.log(220.0 / V_SAFE))
    return dict(
        R_in_merged_kohm=r_in / 1e3, R_out_merged_kohm=r_out / 1e3,
        discharge_merged_from_460_200V=merged, discharge_merged_from_480_220V=merged_480,
        discharge_bleeders_only_from_460_200V=bleed_only, discharge_bleeders_only_from_480_220V=bleed_only_480,
        standby_W_at_440V_200V={"input_total": 440.0 ** 2 / r_in, "input_bleeder": 440.0 ** 2 / R_BL_IN, "input_indicator": 440.0 ** 2 / R_IND_IN,
                                "output_total": V_OUT ** 2 / r_out, "total": 440.0 ** 2 / r_in + V_OUT ** 2 / r_out},
        standby_W_at_400V_200V_total=400.0 ** 2 / r_in + V_OUT ** 2 / r_out,
        element_stress={
            "input_bleeder_2512_at_440V": elem(440.0, R_BL_IN, 3), "input_bleeder_2512_at_480V": elem(VIN_SURV, R_BL_IN, 3),
            "input_indicator_1206_at_440V": elem(440.0 - V_LED, R_IND_IN, 3), "input_indicator_1206_at_480V": elem(VIN_SURV - V_LED, R_IND_IN, 3),
            "output_bleeder_2512_at_200V": elem(V_OUT, R_BL_OUT, 2), "output_bleeder_2512_at_440V_HS_short_fault": elem(440.0, R_BL_OUT, 2),
            "output_indicator_1206_at_200V": elem(V_OUT - V_LED, R_IND_OUT, 2), "output_indicator_1206_at_440V_HS_short_fault": elem(440.0 - V_LED, R_IND_OUT, 2),
            "limits": {"2512": R_2512_LIMITS, "1206_assumed": R_1206_LIMITS}},
        indicator_LED_current_mA_at_440V=(440.0 - V_LED) / R_IND_IN * 1e3,
        option_5s={"R_in_kohm_nominal_C": r5_in_nom / 1e3, "R_out_kohm_nominal_C": r5_out_nom / 1e3,
                   "R_in_kohm_effective_C": r5_in_eff / 1e3, "R_out_kohm_effective_C": r5_out_eff / 1e3,
                   "baseline_kohm": {k: v / 1e3 for k, v in R_5S_OPTION.items()},
                   "P_W_at_440V_200V_baseline": 440.0 ** 2 / R_5S_OPTION["input"] + V_OUT ** 2 / R_5S_OPTION["output"],
                   "P_W_at_440V_220V_baseline": 440.0 ** 2 / R_5S_OPTION["input"] + 220.0 ** 2 / R_5S_OPTION["output"],
                   "time_s_baseline_R_effective_C": discharge_coupled(C_IN_DISCHARGE, C_OUT_DISCHARGE, R_5S_OPTION["input"], R_5S_OPTION["output"], VIN_SURV, 220.0)["time_to_both_below_60V_s"]},
        criterion={"V_safe": V_SAFE, "t_max_with_label_s": T_DISCHARGE_MAX, "label": "IEC 60417-5036 + 60 s"},
    )


# --------------------------------------------------------------------------- #
# Sensing and protection thresholds (research/sensing_protection.json)        #
# --------------------------------------------------------------------------- #
def tmcs1133(ops: list[dict]) -> dict:
    """V_OUT = V0 + S I; LSB = 3 V/4096; FS = (3 V - V0)/S; OC: V_OC = S I_OC/2.5 from 2.5 V through
    2.32 k / 1.00 k loaded by the 120 k pin; band +/-2 % typ, +/-10 % max; trip chain t = t_OC,max +
    t_latch + T_INFIL,max + tPD,max + t_gate; overshoot dI = (V_in,max / L_worst) t; worst peak = I_OC,max + dI.
    Source: sensing_protection.json with verify_sensing corrections (L 175 uH, 32.0 A overload peak)."""
    lsb_v = ADC_FS / 2 ** ADC_BITS
    pts = [0.0, I_OUT, I_OVL, max(op["ipk_A"] for op in ops if op["iout_A"] == I_OUT),
           max(op["ipk_A"] for op in ops if op["iout_A"] == I_OVL), 37.5, 40.0]
    table = [dict(I_A=i, V_out_V=V0_TMCS + S_TMCS * i, code=int(round((V0_TMCS + S_TMCS * i) / lsb_v))) for i in pts]
    r_bot_eff = 1.0 / (1.0 / R_OC_BOT + 1.0 / R_VOC_PIN)
    v_oc = V_REF * r_bot_eff / (R_OC_TOP + r_bot_eff)
    i_oc = v_oc * 2.5 / S_TMCS
    band_typ = [i_oc * (1 - OC_ERR[0]), i_oc * (1 + OC_ERR[0])]
    band_max = [i_oc * (1 - OC_ERR[1]), i_oc * (1 + OC_ERR[1])]
    t_chain = T_OC_MAX + T_LATCH + T_INFIL[2] + T_PD_MAX + T_GATE_FALL
    di_dt = 440.0 / L_TRIP_WORST
    overshoot = di_dt * t_chain * 1e-9
    ramp = {f"L{l*1e6:.0f}uH_{v:.0f}V": (37.5 - 28.75) * l / v * 1e6 for l in (220e-6, 300e-6, l_nominal(33.0)) for v in (360.0, 440.0)}
    return dict(
        LSB_mV=lsb_v * 1e3, LSB_mA=lsb_v / S_TMCS * 1e3, full_scale_A=(ADC_FS - V0_TMCS) / S_TMCS, table=table,
        OC={"V_OC_unloaded_V": V_REF * R_OC_BOT / (R_OC_TOP + R_OC_BOT), "V_OC_loaded_V": v_oc, "I_OC_A": i_oc,
            "band_A_typ": band_typ, "band_A_max": band_max, "hysteresis_A": OC_HYST,
            "margin_A_overload_peak_to_low_bound": band_max[0] - I_PK_OVL_WORST},
        trip_chain={"t_ns": t_chain, "terms_ns": {"OC_max": T_OC_MAX, "latch": T_LATCH, "RST_EN_deglitch_max": T_INFIL[2], "tPD_max": T_PD_MAX, "gate_fall_assumed": T_GATE_FALL},
                    "L_worst_uH": L_TRIP_WORST * 1e6, "di_dt_A_per_us": di_dt / 1e6, "overshoot_A": overshoot,
                    "worst_peak_A": band_max[1] + overshoot, "typ_peak_A": band_typ[1] + overshoot,
                    "L_at_worst_peak_uH_nominal": l_nominal(band_max[1] + overshoot) * 1e6},
        output_short_ramp_to_trip_us=ramp,
        conductor_loss_W={"25A": I_OUT ** 2 * R_IN_TMCS, "27.5A": I_OVL ** 2 * R_IN_TMCS},
        no_load_valley_A=min(-(ripple(v, l_nominal(0.0)) / 2.0) for v in VIN_LIST), linear_range_low_A=-4.6,
    )


def ladder(n_top: int, voltages: list[float]) -> dict:
    """k = R_b/(n R_t + R_b); V_AMC = k V; V_ADC = 1.5 k V; FS = 2.0 V / k; LSB = FS/4096;
    per-resistor V_R = V R_t/(n R_t + R_b), P_R = V_R^2/R_t.  Source: CB-SN-001 adapted (sensing_protection.json)."""
    k = R_LADDER_BOT / (n_top * R_LADDER_TOP + R_LADDER_BOT)
    rows = []
    for v in voltages:
        v_r = v * R_LADDER_TOP / (n_top * R_LADDER_TOP + R_LADDER_BOT)
        rows.append(dict(V=v, V_AMC_V=k * v, V_ADC_V=G_OPA * k * v, code=int(round(G_OPA * k * v / (ADC_FS / 2 ** ADC_BITS))),
                         V_per_resistor_V=v_r, P_per_resistor_mW=v_r ** 2 / R_LADDER_TOP * 1e3, I_divider_uA=v / (n_top * R_LADDER_TOP + R_LADDER_BOT) * 1e6))
    return dict(k=k, full_scale_V=AMC_FSR / k, ADC_full_scale_V=ADC_FS / (G_OPA * k), LSB_V=ADC_FS / (G_OPA * k) / 2 ** ADC_BITS, rows=rows,
                headroom_at_max_pct=100.0 * k * max(voltages) / AMC_FSR)


def ntc_r(t_c: float) -> float:
    """R(T) = R25 exp(B (1/T - 1/298.15 K)).  Source: Vishay NTCALUG01A (beta model; R/T table above 85 degC preferred)."""
    t = t_c + 273.15
    return NTC_R25 * math.exp(NTC_B * (1.0 / t - 1.0 / 298.15))


def ntc_v(t_c: float) -> float:
    """V = 3.00 V R_NTC/(2.2 k + R_NTC).  Source: design_decisions.json sensing.heatsink_temperature.route."""
    r = ntc_r(t_c)
    return V_NTC_REF * r / (R_NTC_PULLUP + r)


def ntc_t_from_v(v: float) -> float:
    r = R_NTC_PULLUP * v / (V_NTC_REF - v)
    return 1.0 / (1.0 / 298.15 + math.log(r / NTC_R25) / NTC_B) - 273.15


def comparators() -> dict:
    """Thresholds from REF3125 2.5 V: V_th = 2.5 R_b/(R_t + R_b); bus = V_th/(1.5 k_in); output = V_th/(1.5 k_out).
    UVLO hysteresis from a 0/3.3 V open-collector output through 21.5 k: shift = (V_o - V_th) R_th/(R_h + R_th).
    OTP: ratiometric to the 3.00 V NTC reference; V_trip = V_NTC(T); proposal divider 10.0 k / 2.37 k.
    Source: sensing_protection.json 'Comparator thresholds', CR-04, CR-01, KR-TH-003 (proposals)."""
    k_in = R_LADDER_BOT / (N_TOP_VIN * R_LADDER_TOP + R_LADDER_BOT) * G_OPA
    k_out = R_LADDER_BOT / (N_TOP_VOUT * R_LADDER_TOP + R_LADDER_BOT) * G_OPA
    v_ovp_in = V_REF * R_OVP_IN[1] / sum(R_OVP_IN)
    v_ovp_out = V_REF * R_OVP_OUT[1] / sum(R_OVP_OUT)
    v_uvlo = V_REF * R_UVLO[1] / sum(R_UVLO)
    r_th = R_UVLO[0] * R_UVLO[1] / sum(R_UVLO)
    shift_hi = (V_LOGIC - v_uvlo) * r_th / (R_UVLO_HYST + r_th)
    shift_lo = -v_uvlo * r_th / (R_UVLO_HYST + r_th)
    ntc_table = [dict(T_C=t, R_ohm=ntc_r(t), V_V=ntc_v(t)) for t in (25, 50, 70, 85, 90, 100, 110, 125)]
    v_otp = {k: ntc_v(v) for k, v in T_OTP.items()}
    v_prop = V_NTC_REF * R_OTP_PROPOSAL[1] / sum(R_OTP_PROPOSAL)
    return dict(
        OVP_in={"V_th_V": v_ovp_in, "bus_V": v_ovp_in / k_in, "target_V": VIN_OVP},
        OVP_out={"V_th_V": v_ovp_out, "output_V": v_ovp_out / k_out, "target_V": VOUT_OVP},
        UVLO={"V_centre_V": v_uvlo, "bus_centre_V": v_uvlo / k_in, "on_V": (v_uvlo + shift_hi) / k_in, "off_V": (v_uvlo + shift_lo) / k_in,
              "targets_V": [UVLO_START, UVLO_STOP], "note": "open-collector hysteresis asymmetric; verify by simulation or implement in firmware (baseline)"},
        NTC_table=ntc_table, NTC_sensitivity_mV_per_K_90_100=(ntc_v(90) - ntc_v(100)) / 10.0 * 1e3,
        NTC_self_heating_K_at_110C=ntc_v(110) ** 2 / ntc_r(110) / NTC_DISS,
        OTP_threshold_voltages_V=v_otp,
        OTP_hardware_divider_proposal={"R_top_ohm": R_OTP_PROPOSAL[0], "R_bottom_ohm": R_OTP_PROPOSAL[1], "V_th_V": v_prop, "trip_C": ntc_t_from_v(v_prop)},
    )


# --------------------------------------------------------------------------- #
# Thermal (KR-TH-001 shared-sink model, research/thermal.json corrections)    #
# --------------------------------------------------------------------------- #
def junction(p_hs: float, p_ls: float, r_hs: float = R_TH_HS, r_pad: float = R_PAD, r_spread: float = 0.0) -> dict:
    """T_sink = T_A + R_th,HS (P_HS + P_LS); T_J,dev = T_sink + P_dev (R_pad + R_JC + R_spread).
    Equal-sharing lumped model (TI factor 2 read as two devices per sink).  Source: KR-TH-001, SKILL-006
    principle 1, research/thermal.json."""
    t_sink = T_A + r_hs * (p_hs + p_ls)
    return dict(T_sink_C=t_sink, T_J_HS_C=t_sink + p_hs * (r_pad + R_TH_JC + r_spread), T_J_LS_C=t_sink + p_ls * (r_pad + R_TH_JC + r_spread))


def p_max_kr_th_001(tj_lim: float, r_hs: float = R_TH_HS, r_pad: float = R_PAD) -> float:
    """P_max = (T_J,lim - T_A) / (2 R_th,HS + R_pad + R_JC)  (KR-TH-001, EC-019/020 pattern)."""
    return (tj_lim - T_A) / (2 * r_hs + r_pad + R_TH_JC)


def fan_failure(p_total: float, t_start: float) -> list[dict]:
    """Natural-convection steady state T_ss = T_A + P R_nat; lumped time to the 100 degC firmware trip
    t = -tau ln(1 - (T_trip - T_0)/(T_ss - T_0)), tau = m c_p R_nat; initial slope P/(m c_p).
    Source: research/thermal.json 'Fan failure' (R_nat and mass unverified for the D K unit)."""
    rows = []
    for r_nat in R_TH_NAT:
        for m in M_SINK:
            t_ss = T_A + p_total * r_nat
            tau = m * CP_AL * r_nat
            t_trip = T_OTP["firmware_trip"]
            t_to_trip = -tau * math.log(1.0 - (t_trip - t_start) / (t_ss - t_start)) if t_ss > t_trip else None
            rows.append(dict(R_nat_K_per_W=r_nat, mass_kg=m, T_sink_ss_C=t_ss, T_J_HS_ss_C=t_ss + 31.4 * (R_PAD + R_TH_JC),
                             tau_s=tau, initial_slope_K_per_s=p_total / (m * CP_AL), time_to_100C_trip_s=t_to_trip))
    return rows


# --------------------------------------------------------------------------- #
# Copper and vias (IPC-2221 formula; KR-PCB-006 / PE-PCB-006)                 #
# --------------------------------------------------------------------------- #
def ipc_width_mm(i_a: float, dt_k: float, k: float, t_um: float = CU_THICK_UM) -> float:
    """A[mil2] = (I/(k dT^0.44))^(1/0.725); w = A / t[mil] (1 mil = 25.4 um).  Source: IPC-2221 (secondary)."""
    a_mil2 = (i_a / (k * dt_k ** IPC_B)) ** (1.0 / IPC_C)
    return a_mil2 / (t_um / 25.4) * 25.4 / 1000.0


def via_current_a(drill_mm: float, dt_k: float = 20.0) -> float:
    """Barrel area A = pi (d + t) t; I = k_int dT^0.44 A[mil2]^0.725 (conservative internal constant).
    Source: standards_safety.json 'Via barrel area, resistance and current'."""
    t = VIA_PLATING_UM * 1e-3
    a_mm2 = math.pi * (drill_mm + t) * t
    a_mil2 = a_mm2 / (0.0254 ** 2)
    return K_IPC_INT * dt_k ** IPC_B * a_mil2 ** IPC_C


def copper() -> dict:
    rows = []
    for i in (I_OUT, I_OVL):
        for dt in (10.0, 20.0, 30.0):
            rows.append(dict(I_A=i, dT_K=dt, width_external_mm=ipc_width_mm(i, dt, K_IPC_EXT), width_internal_mm=ipc_width_mm(i, dt, K_IPC_INT)))
    vias = []
    for d in VIA_DRILLS_MM:
        i_via = via_current_a(d)
        n_min = I_OUT / i_via
        base = VIA_COUNT_BASELINE[f"{d} mm"]
        r_via = RHO_100 * 2.0e-3 / (math.pi * (d * 1e-3 + VIA_PLATING_UM * 1e-6) * VIA_PLATING_UM * 1e-6)
        vias.append(dict(drill_mm=d, I_per_via_A_20K=i_via, minimum_count_25A=n_min, baseline_count=base,
                         baseline_margin=base * i_via / I_OUT, R_per_via_mohm_2mm_board=r_via * 1e3,
                         P_W_baseline_count_25A=I_OUT ** 2 * r_via / base))
    r_per_cm = RHO_100 / (PATH_WIDTH_MM * 1e-3 * CU_THICK_UM * 1e-6) / 100.0
    return dict(ipc_widths=rows, vias=vias,
                path_loss={"width_mm": PATH_WIDTH_MM, "length_cm": PATH_LEN_CM, "R_mohm_per_cm": r_per_cm * 1e3,
                           "P_W_per_cm_25A": I_OUT ** 2 * r_per_cm, "P_W_total_25A": I_OUT ** 2 * r_per_cm * PATH_LEN_CM,
                           "P_W_total_27p5A": I_OVL ** 2 * r_per_cm * PATH_LEN_CM})


# --------------------------------------------------------------------------- #
# Auxiliary 12 V, eFuse, supervisor, relay, mezzanine                         #
# --------------------------------------------------------------------------- #
def aux_12v(bias: dict) -> dict:
    """I_CB = 12/R_ILIM[kohm] - 0.03 A (SLVSFQ6A Eq. 4, MODE open = circuit breaker, 4 ms, 540 ms retry);
    budget per baseline (CR-02); dVdT slew = GAIN I_dVdT / C -> t = V/slew; charging current C_down slew;
    ladder UVLO/OVP; IMON; TPS3808 V_trip = V_IT (R_top + R_bot)/R_bot; relay coil I = V/R; mezzanine
    pin current = I_12V,power-board / 3.  Source: controller_aux_interconnect.json + verify corrections."""
    i_cb = 12.0 / (R_ILIM / 1e3) - 0.03  # SLVSFQ6A Eq. 4 uses R_ILIM in kohm
    i_cb_min = i_cb * (1 + I_CB_TOL[0])
    b = AUX_BUDGET_10P8
    pull_in = b["gate_bias_modules"] + b["sensing_bias_module"] + b["control_board"] + b["relay_coil_pull_in"] + b["heatsink_fan_max"]
    steady = b["gate_bias_modules"] + b["sensing_bias_module"] + b["control_board"] + b["relay_coil_pwm_hold"] + b["heatsink_fan_max"]
    no_fan_pull_in = pull_in - b["heatsink_fan_max"]
    slews = [GAIN_DVDT * i / C_DVDT for i in I_DVDT]
    r1, r2, r3 = R_EFUSE_LADDER
    uvlo_r = V_UVLO_PIN["rising"] * (r1 + r2 + r3) / (r2 + r3)
    uvlo_f = V_UVLO_PIN["falling"] * (r1 + r2 + r3) / (r2 + r3)
    ovp_r = V_UVLO_PIN["rising"] * (r1 + r2 + r3) / r3
    ovp_f = V_UVLO_PIN["falling"] * (r1 + r2 + r3) / r3
    v3808 = V_IT_3808 * sum(R_3808) / R_3808[1]
    v3808_105k = V_IT_3808 * (105e3 + R_3808[1]) / R_3808[1]
    coil = {f"{v:g}V": v / R_COIL for v in (V_AUX_MIN, V_AUX_NOM, V_AUX_MAX)}
    power_board_12v = {"pull_in": pull_in - b["control_board"], "steady": steady - b["control_board"]}
    return dict(
        I_CB_A_typ=i_cb, I_CB_A_min_assumed=i_cb_min, I_CB_A_max_assumed=i_cb * (1 + I_CB_TOL[1]),
        budget_A_at_10p8V=dict(b), total_pull_in_A=pull_in, total_steady_A=steady, total_pull_in_without_fan_A=no_fan_pull_in,
        margin_pull_in=i_cb / pull_in, margin_steady=i_cb / steady, margin_pull_in_vs_I_CB_min=i_cb_min / pull_in,
        margin_steady_vs_I_CB_min=i_cb_min / steady,
        bottom_up_bias_A_at_10p8V=bias["I_12V_A_at_10p8V_with_20pct_margin"],
        dVdT={"slew_V_per_ms_min_typ_max": [s / 1e3 for s in slews], "ramp_ms_at_12V": [12.0 / s * 1e3 for s in slews][::-1],
              "charging_current_A": [C_DOWNSTREAM_12V * s for s in slews], "C_downstream_uF": C_DOWNSTREAM_12V * 1e6},
        ladder={"UVLO_rising_V": uvlo_r, "UVLO_falling_V": uvlo_f, "OVP_rising_V": ovp_r, "OVP_falling_V": ovp_f, "I_ladder_uA_12V": 12.0 / sum(R_EFUSE_LADDER) * 1e6},
        IMON={"V_at_2p4A_max_gain_V": 2.4 * GAIN_IMON[2] * R_IMON, "V_at_1p59A_typ_V": steady * GAIN_IMON[1] * R_IMON, "mA_per_LSB": (ADC_FS / 2 ** ADC_BITS) / (GAIN_IMON[1] * R_IMON) * 1e3},
        TPS3808={"V_trip_V_101k": v3808, "V_release_V_101k": v3808 * (1 + HYST_3808), "V_trip_V_105k": v3808_105k,
                 "power_down_margin_ms": C_5V_BULK * (v3808 - (1.9 + 0.35)) / I_5V * 1e3, "requirement_us": 8.0},
        LDO={"P_W": (5.0 - 1.9) * I_1V9 + (5.0 - 3.3) * I_3V3, "I_5V_A": I_5V, "P_in_control_W": P_CONTROL_IN},
        relay_coil_A=coil, relay_hold_A_at_10p8V=[V_AUX_MIN / R_COIL * d for d in HOLD_DUTY], relay_coil_P_W_12V=12.0 ** 2 / R_COIL,
        relay_contact_loss_W={"25A": I_OUT ** 2 * R_CONTACT_RELAY, "27.5A": I_OVL ** 2 * R_CONTACT_RELAY},
        mezzanine={"power_board_12V_A": power_board_12v, "per_pin_A_pull_in": power_board_12v["pull_in"] / N_12V_PINS,
                   "per_pin_A_steady": power_board_12v["steady"] / N_12V_PINS, "target_A_per_pin": I_PIN_TARGET,
                   "ratings_A": I_PIN_RATING, "margin_WR_PHD": I_PIN_RATING["WR-PHD"] / (power_board_12v["pull_in"] / N_12V_PINS)},
    )


# --------------------------------------------------------------------------- #
# Power path: fuse, precharge, firmware derating                               #
# --------------------------------------------------------------------------- #
def power_path(ops: list[dict]) -> dict:
    """Fuse loading = I_in/I_fuse at the corners incl. the 320 V stop corner; precharge tau = R C,
    t99 = 4.6 tau, E = 0.5 C V^2, I_pk = V/R, I2t = C V^2/(2R), dT_PTC = E/C_th, N = C V^2/(2 C_th (T_ref - T_A));
    firmware derating below 360 V: P_out,max = eta I_lim V_in.  Source: sensing_protection.json,
    standards_safety.json, CR-15, CR-20 and verify_sensing corrections (PTC parameters stale)."""
    loads = {}
    for op in ops:
        loads[corner_name(op)] = op["iin_A_eta98"] / I_FUSE
    loads["320V/27.5A_unlimited"] = input_current(UVLO_STOP, I_OVL, 0.98) / I_FUSE
    loads["320V_with_15.6A_limit"] = I_IN_FW_LIMIT / I_FUSE
    derate = {f"{v:g}V": {"I_in_27p5A_A": input_current(v, I_OVL, 0.98), "P_out_max_W_at_15p6A": 0.98 * I_IN_FW_LIMIT * v,
                          "I_out_max_A_at_15p6A": 0.98 * I_IN_FW_LIMIT * v / V_OUT} for v in (320.0, 340.0, 360.0)}
    c = C_IN_DISCHARGE
    pre = {}
    for key, r in R_PTC.items():
        pre[key] = dict(R_ohm=r, tau_ms=r * c * 1e3, t99_ms=4.6 * r * c * 1e3, I_pk_A_440V=440.0 / r, I_pk_A_480V=VIN_SURV / r,
                        I2t_A2s_480V=c * VIN_SURV ** 2 / (2 * r))
    e440, e480 = 0.5 * c * 440.0 ** 2, 0.5 * c * VIN_SURV ** 2
    dt_ptc = {f"C_th_{cth}J_per_K": e480 / cth for cth in C_TH_PTC}
    n_elem = {f"C_th_{cth}_Tref_{tr}": c * VIN_SURV ** 2 / (2 * cth * (tr - T_A_PTC)) for cth in C_TH_PTC for tr in T_REF_PTC}
    i_bleed_440 = 440.0 / (1.0 / (1.0 / R_BL_IN + 1.0 / R_IND_IN)) + 440.0 / (N_TOP_VIN * R_LADDER_TOP + R_LADDER_BOT)
    return dict(fuse={"rating_A": I_FUSE, "loading": loads, "I2R_cold_W_at_12p76A_distributor_R": input_current(400.0, I_OUT, 0.98) ** 2 * R_FUSE_COLD},
                firmware_derating_below_360V=derate,
                precharge={"by_R": pre, "E_J_440V": e440, "E_J_480V": e480, "dT_PTC_K_480V": dt_ptc, "N_elements_required": n_elem,
                           "relay_closing_dV_V": i_bleed_440 * R_PTC["nominal"], "relay_operate_time_ms": T_RELAY_OPERATE * 1e3,
                           "closing_criterion": "V_bus > 340 V and dV/dt < 2 V per 10 ms, 500 ms timeout"})


# --------------------------------------------------------------------------- #
# Efficiency roll-up                                                          #
# --------------------------------------------------------------------------- #
def efficiency(ops: list[dict], ind: dict, cin: dict, cu: dict, bl: dict, bias: dict) -> dict:
    """P_loss = MOSFET pair + inductor + copper/interconnect + film-ceramic ring + bleeders (+ aux electronics,
    relay hold, fan).  eta = P_out/(P_out + P_loss).  Scenarios span the k_RG range, T_J 100/150 degC,
    typical/max R, typical/bounded inductor, 250/300 ns dead time.  Source: design_decisions.json
    open_items (77-99 W, 98.0-98.5 %) with the verifier corrections."""
    op = next(o for o in ops if o["vin_V"] == 400.0 and o["iout_A"] == I_OUT)
    ind_typ = next(c for c in ind["corners_typical_core"] if c["corner"] == "400V/25A")["P_total_W"]
    ind_bounded = next(c for c in ind["corners_bounded_core"] if c["corner"] == "400V/25A")["P_total_W"]
    hf = cin["hf_tier"]["by_interconnect"]
    ring_typ, ring_max = hf[1]["ring_loss_W"], hf[2]["ring_loss_W"]
    tmcs = I_OUT ** 2 * R_IN_TMCS
    relay_contact = I_OUT ** 2 * R_CONTACT_RELAY
    fuse = input_current(400.0, I_OUT, 0.98) ** 2 * R_FUSE_COLD
    interconnect = cu["path_loss"]["P_W_total_25A"] + tmcs + relay_contact + fuse
    bleed = bl["standby_W_at_400V_200V_total"]
    aux_electronics = 1.2 * (bias["P_in_total_W"] + P_CONTROL_IN)
    relay_hold = (12.0 ** 2 / R_COIL) * HOLD_DUTY[0]
    fan = I_FAN_MAX * 12.0
    dt250, dt300 = DEAD_TIME["effective_target"] * 1e-9, DEAD_TIME["programmed_bring_up"] * 1e-9

    def scen(name, r_hot, k, t_dt, ind_w, ring_w, note):
        m = mosfet_losses(op, r_hot, k, t_dt)
        conv = m["pair_W"] + ind_w + interconnect + ring_w + bleed
        return dict(scenario=name, note=note, mosfet_pair_W=m["pair_W"], inductor_W=ind_w, interconnect_W=interconnect,
                    ring_W=ring_w, bleeders_W=bleed, converter_loss_W=conv, eta_converter_only=P_OUT / (P_OUT + conv),
                    aux_electronics_W=aux_electronics, loss_with_aux_electronics_W=conv + aux_electronics,
                    eta_with_aux_electronics=P_OUT / (P_OUT + conv + aux_electronics),
                    relay_hold_W=relay_hold, fan_W=fan, system_loss_W=conv + aux_electronics + relay_hold + fan,
                    eta_system=P_OUT / (P_OUT + conv + aux_electronics + relay_hold + fan))

    scenarios = [
        scen("typical_expected", rds_on(TJ_EXPECTED), 1.3, dt250, ind_typ, ring_typ, "T_J 100 degC, typ R, k_RG 1.3, 250 ns, typical core, 30 nH"),
        scen("design_limit_150C_k1p3", rds_on(TJ_LIMIT), 1.3, dt250, ind_typ, ring_typ, "T_J 150 degC, typ R, k_RG 1.3"),
        scen("design_limit_150C_k1p9_10ohm", rds_on(TJ_LIMIT), 1.9, dt250, ind_typ, ring_typ, "T_J 150 degC, typ R, k_RG 1.9 (10 ohm bring-up)"),
        scen("design_limit_150C_k2p0", rds_on(TJ_LIMIT), 2.0, dt250, ind_typ, ring_typ, "T_J 150 degC, typ R, k_RG 2.0"),
        scen("bounded_worst", rds_on_max_scaled(TJ_LIMIT), 2.0, dt300, ind_bounded, ring_max,
             "max-R 150 degC, k_RG 2.0, 300 ns, datasheet-max core x1.3 bias allowance, 40 nH ring"),
    ]
    return dict(items_W={"interconnect_pcb_copper": cu["path_loss"]["P_W_total_25A"], "TMCS1133_conductor": tmcs, "relay_contact_0p6mohm": relay_contact,
                         "fuse_cold_resistance": fuse, "bleeders_at_400V": bleed, "aux_electronics_with_20pct_margin": aux_electronics,
                         "relay_hold_50pct": relay_hold, "fan_cap": fan},
                scenarios=scenarios, target=ETA_TARGET, floor=ETA_FLOOR,
                loss_budget_W={"98.0 %": P_OUT * (1 / ETA_TARGET - 1), "97.5 %": P_OUT * (1 / ETA_FLOOR - 1)})


# --------------------------------------------------------------------------- #
# Assembly, invariants, baseline cross-check, knowledge applicability          #
# --------------------------------------------------------------------------- #
KNOWLEDGE_APPLICABILITY = [
    ("SKILL-001", "skill", "adapted", "Steps 3-6 supply the gate-power, decoupling, peak-current and resistor-pulse formulas; device selection is out of its scope."),
    ("SKILL-002", "skill", "not-applicable", "Layout skill; only its hand-off (driver within 15 mm, Kelvin pours) is referenced, no calculation here."),
    ("SKILL-003", "skill", "adapted", "DC-link procedure steps 1-4 with the buck pulsating input current instead of the DAB tank waveform; the 200 V output filter is sized by the buck ripple equation."),
    ("SKILL-004", "skill", "direct", "Bias-supply power budget per channel and 12 V input model (KR-IS-001); three UCC14141-Q1 modules (CR-12)."),
    ("SKILL-005", "skill", "direct", "Sensing scaling, headroom (KR-SN-002) and the hardware OC path (KR-SN-005) are computed exactly as the skill prescribes."),
    ("SKILL-006", "skill", "adapted", "Shared-sink budget with this design's 50 degC, 150 degC limit, 0.30 K/W sink and 1.4 K/W pad; TI's 40 degC / 0.5 / 0.1 K/W instance values are not used."),
    ("KR-CAP-001", "rule", "adapted", "C >= dQ_max/dV with dQ = D(1-D) Io Ts derived for the buck (exact at all corners)."),
    ("KR-CAP-002", "rule", "direct", "Film RMS current versus the 10 kHz / 70 degC / dT 20 K rating, self-heating via ESR x R_th; output capacitor by extension of the DC-link condition."),
    ("KR-CAP-003", "rule", "adapted", "Two-tier bank; the HF tier is sized by the film-to-ceramic resonance model (TI's purpose is inferred, not stated)."),
    ("KR-CAP-004", "rule", "not-applicable", "No transformer, no DC-blocking capacitor."),
    ("KR-GD-001", "rule", "direct", "Rails +15/-4 V +/-1.3 % plus < 0.5 V gate-loop overshoot checked against -10/+23 V (datasheet) - not the Gen-3 example limits."),
    ("KR-GD-002", "rule", "direct", "Split R_G,on / R_G,off used in the peak-current and resistor-power formulas."),
    ("KR-GD-003", "rule", "adapted", "Charge-based (Q_gd) off-state excursion replaces the small-signal C_rss dv/dt R estimate; the Miller clamp is REQUIRED (not optional) pending the PRD-09301 6.1 measurement."),
    ("KR-GD-004", "rule", "human-review", "DESAT trip 3.6 V / blanking 288 ns derived from the C4MS025120K data (TIDA 6.4 V / 1 us not copied); values must be confirmed on hardware."),
    ("KR-GD-005", "rule", "direct", "-4 V turn-off kept because the synchronous buck is a complementary half bridge (the buck exclusion of PRD-04814 does not apply)."),
    ("KR-GD-006", "rule", "adapted", "+15/-4 V shared with the C3M0021120K fallback; +18 V is a C4MS-only BOM option (same-supplier generation change)."),
    ("KR-GD-009", "rule", "direct", "Dead time from the ePWM dead-band module; 150 ns minimum derived from skew/PWD/td; cross-wired IN+/IN- interlock."),
    ("KR-GD-011", "rule", "adapted", "Soft turn-off (400 mA) fault overshoot computed; module-scoped rule applied to a discrete."),
    ("KR-IS-001", "rule", "direct", "Both forms shown: Wolfspeed Q_G f_sw dV (0.119 W) and the recorded TI factor-2 conflict (0.24 W); the budget uses the larger."),
    ("KR-IS-003", "rule", "adapted", "i_CM = (C_IO,bias + C_IO,driver) dv/dt for the HS barrier at 120 V/ns (3.5 pF and 5 pF bound)."),
    ("KR-IS-004", "rule", "human-review", "No shared supply: dedicated sensing module (CR-12); the COM-VEE sourcing check (RLIM) is reported for review."),
    ("KR-IS-005", "rule", "direct", "Regulated module, no LDO post-regulation; droop of the gate decoupling computed from Q_G."),
    ("KR-PR-001", "rule", "direct", "Hard constraint: DESAT response 0.55-1.07 us against the <= 1.5 us budget; the withstand time is unpublished, so compliance is by destructive test (owner: gate-driver/test)."),
    ("KR-PR-002", "rule", "direct", "Latched OC path: TMCS1133 OC -> latch -> RST/EN + TZ1; UVLO non-latched run permit."),
    ("KR-PR-003", "rule", "human-review", "eFuse thresholds (10.0 / 14.45 V, I_CB 1.96 A) computed; review against downstream ratings is the rule's verification method."),
    ("KR-SN-001", "rule", "direct", "Isolation ratings of UCC21710-Q1, UCC14141-Q1, AMC1311, TMCS1133 taken from datasheets; UCC14141 certificate status is an open item."),
    ("KR-SN-002", "rule", "direct", "Ladder full scales 602 V / 302 V and the 0.33 V + 50 mV/A current scaling keep every measured value inside the 2 V isolator range and the 0-3 V ADC."),
    ("KR-SN-003", "rule", "not-applicable", "TMS320F28335 has no sigma-delta filter module."),
    ("KR-SN-004", "rule", "not-applicable", "Hall sensor, no shunt."),
    ("KR-SN-005", "rule", "direct", "Hardware trip chain 546 ns computed; ADC loop shown too slow (output short ramps to trip in 4-7 us)."),
    ("KR-TH-001", "rule", "direct", "P_max = (T_J,lim - T_A)/(2 R_th,HS + R_pad + R_JC) = 41.5 W (margin 1.22 over the 34.1 W HS corner); T_J at every corner incl. the stacked worst case."),
    ("KR-TH-002", "rule", "direct", "Pad resistance 1.4 K/W (exposed-tab area, CR-21) in the budget; pad voltage rating vs impulse basis stays a human-review conflict (CR-13)."),
    ("KR-TH-003", "rule", "human-review", "NTC readout and NTC-to-T_J offset computed; 90/100/110 degC thresholds are proposals (cooling supervision, not junction protection)."),
    ("KR-PCB-006", "rule", "adapted", "IPC-2221 copper widths and via counts (rule is a low-confidence pattern; sizing method added)."),
    ("KR-PE-001", "rule", "not-applicable", "Hard-switched buck; no soft-switching boundary."),
    ("KR-ISO-002", "rule", "human-review", "Element voltages of the bleeder/indicator chains computed; spacing itself comes from the standards agent (not recomputed here)."),
    ("CB-GD-001", "block", "adapted", "DESAT trip and blanking formulas (EC-001/EC-002 pattern) with the C4MS025120K values 2.2 k / 4.99 k / 1.0 k / 680 pF."),
    ("CB-GD-003", "block", "not-applicable", "Mezzanine link, no cable; RS-422 fallback only."),
    ("CB-IS-002", "block", "adapted", "UCC14141-Q1 dividers 107 k / 16.2 k and 9.76 k / 16.2 k; TI RLIM values not adopted."),
    ("CB-PR-001", "block", "adapted", "TPS26400 eFuse at the 12 V entry with derived ladder, I_CB and dVdT (TI 9 V / 15 V / 2.2 A not copied)."),
    ("CB-PR-002", "block", "not-applicable", "Adapted-then-rejected (CR-01): the NTC is read directly on the SELV control board (2.2 k pull-up to 3.00 V), not through the driver AIN/APWM channel."),
    ("CB-SN-001", "block", "adapted", "Ladders rescaled to 4 x 750 k + 10 k and 2 x 750 k + 10 k with gain 1.5."),
    ("CB-SN-004", "block", "adapted", "TMCS1133 OC threshold from datasheet Eq. 21 with REF3125 (TI 45/70 A not copied)."),
    ("CMP-UCC21710-Q1", "component", "direct", "SLUSDH8D parameters (V_OCTH, t_OCOFF, I_STO, R_OUT, deglitch, tPD, skew, CMTI)."),
    ("CMP-UCC14141-Q1", "component", "direct", "SLUSF10B ratings, input-current model, RLIM internal resistance, C_IO bound."),
    ("CMP-TMCS1133", "component", "direct", "SBOSAG0E C2A transfer, OC equation, pin impedance, error band, response time."),
    ("CMP-AMC1311", "component", "direct", "SBAS786C 2 V linear range and IDD1 maximum."),
    ("CMP-TPS2640", "component", "direct", "SLVSFQ6A circuit-breaker threshold, dVdT, IMON gain, UVLO/OVP pin thresholds."),
    ("CMP-CGA9P1X7T2J474M250KC", "component", "adapted", "0.47 uF 630 V part counted at 40 % remaining capacitance (DC-bias curve unverified)."),
    ("REF-TI-TIDA-010054", "reference", "adapted", "Shared-sink thermal model (decision 9), two-tier capacitor method (decision 2), eFuse pattern (decision 8); no instance value copied."),
    ("REF-WS-CGD1700HB2M-UNA", "reference", "adapted", "DESAT network topology and commutation-loop priority (KR-PCB-004); module values (1 ohm, 6.7 V / 46 ns, 20 uF) not used."),
    ("REF-WS-PRD-04814", "reference", "adapted", "+15 V / -3..-4 V level guidance; the Gen-4 datasheet window governs."),
    ("PE-PCB-006", "project-rule", "human-review", "Copper widths, via plating assumption, current and loss rationale provided as the review evidence."),
    ("Magnetics 2024 catalogue (external, no KB record)", "external-method", "direct", "Permeability, core-loss and DC-magnetisation fits and the dT correlation; proposed as a new skill."),
]

LIMITATIONS = [
    "Switching-energy scaling (E ~ V, E ~ I, k_RG 1.3-2.0) carries about +/-30 % uncertainty plus the k_RG range; E_rr at the design di/dt is uncertain by about a factor of two; a double-pulse test at 400 V / 30 A is the verification step.",
    "No circuit, thermal or electromagnetic simulation underlies any number here; everything is a first-order analytical estimate (verification level 'analytically-checked' at best).",
    "Heat-sink data (0.30 K/W, airflow, fan current, mass, natural-convection resistance) are distributor-level; the Fischer LAM 5 D K 100 12 datasheet was not accessible; the pad resistance 1.4 K/W rests on the exposed-tab area read from the package table (CR-21) and is to be measured.",
    "R_DS(on) at 150 degC is interpolated from the 25 / 175 degC datasheet points with the 18 V tempco; the 57.2 mohm maximum is scaled from the 18 V maximum (no 15 V maximum is published).",
    "The body-diode voltage slope (0.07 ohm) and the E_oss voltage exponent (1.5) are added assumptions; the inductor hot-spot allowance (+10-15 K), surface area (161 cm2) and still-air correlation are empirical with roughly +/-30 % accuracy.",
    "MLCC DC-bias (40 % remaining at 440 V), film-to-ceramic interconnect inductance (20-40 nH) and loop resistance (6-20 mohm) are assumptions until the layout is extracted and the TDK curve is read.",
    "The 10 s overload is treated as thermal steady state (conservative for the sink and the choke).",
    "The merged-bleeder discharge uses an ideal-diode two-bank model with 1 ms steps; LED forward drops are only included in the element-stress figures.",
    "The precharge PTC parameters (R25, C_th, T_ref) belong to a part still to be re-selected (CR-19); results are shown for the candidate ranges.",
]


def check(name: str, expression: str, value, limit, ok: bool, unit: str = "", note: str = "") -> dict:
    return dict(name=name, expression=expression, value=value, limit=limit, unit=unit, status="PASS" if ok else "FAIL", note=note)


def calculate() -> dict:
    ops = [operating_point(v, i) for i in (I_OUT, I_OVL) for v in VIN_LIST]
    dt250 = DEAD_TIME["effective_target"] * 1e-9
    dt300 = DEAD_TIME["programmed_bring_up"] * 1e-9
    r150, r150max, r100 = rds_on(TJ_LIMIT), rds_on_max_scaled(TJ_LIMIT), rds_on(TJ_EXPECTED)

    # ---- MOSFET loss tables ------------------------------------------------ #
    mos_rows = []
    for op in ops:
        for label, r in (("typ", r150), ("max", r150max)):
            for k in (1.3, 1.6, 1.9, 2.0):
                row = mosfet_losses(op, r, k, dt250)
                row["R_variant"] = label
                row["LS_dt_W_300ns"] = mosfet_losses(op, r, k, dt300)["LS_dt_W"]
                row["LS_dt_W_250ns_flat_4p6V"] = mosfet_losses(op, r, k, dt250, flat_vsd=True)["LS_dt_W"]
                mos_rows.append(row)
    op400 = next(o for o in ops if o["vin_V"] == 400.0 and o["iout_A"] == I_OUT)
    mos_expected = mosfet_losses(op400, r100, 1.3, dt250)
    mos_expected_k2 = mosfet_losses(op400, r100, 2.0, dt250)
    util_rows = [utilisation(v, l * 1e-9) for v in (440.0, VIN_OVP) for l in L_LOOP + L_LOOP_LEADS]
    util_rows.append(dict(vin_V=VIN_SURV, L_loop_nH=0.0, V_os_V=0.0, V_pk_V=VIN_SURV, utilisation=VIN_SURV / V_DS_MAX, note="static 100 ms survival"))
    para = []
    for q in Q_GD_400_RANGE:
        for te in (8e-9, 13e-9):
            for label, rp in (("no clamp 5.6 ohm", R_G_OFF + R_G_INT - 0.3), ("clamp 3.2 ohm", R_CLAMP + R_G_INT)):
                dv = parasitic_turn_on(q, te, rp)
                para.append(dict(Q_gd_nC=q * 1e9, t_edge_ns=te * 1e9, path=label, dV_GS_V=dv, V_GS_peak_V=V_EE + dv,
                                 margin_to_Vth_min_25C_V=V_GS_TH_MIN_25 - (V_EE + dv)))
    mosfet = dict(
        R_DS_on_mohm={"25C_typ_15V": R25_15V * 1e3, "100C_typ": r100 * 1e3, "150C_typ": r150 * 1e3, "150C_max_scaled_from_33mohm": r150max * 1e3,
                      "150C_from_derived_37mohm_15V_max": rds_on(TJ_LIMIT, 37e-3) * 1e3, "175C_typ": rds_on(175.0) * 1e3},
        rows=mos_rows, expected_400V_25A_100C_k1p3=mos_expected, expected_400V_25A_100C_k2p0=mos_expected_k2,
        utilisation=util_rows, utilisation_limit=UTIL_LIMIT_REP,
        current_margins={"I_D_100C_over_I_rms_max": I_D_100C / max(o["iLS_rms_A"] for o in ops), "I_DM_over_I_pk_worst": I_DM / max(o["ipk_A_worst"] for o in ops)},
        parasitic_turn_on=para,
        parasitic_note="baseline range 4.5-5.2 V (+0.5..+1.2 V); this RC model spans the stated Q_gd and edge-time ranges; margin to the 25 degC minimum threshold is 0-3 V without clamp -> clamp REQUIRED, measurement decisive",
    )

    gate = dict(power_W={"wolfspeed_form": gate_power_wolfspeed(), "TI_form_factor2": gate_power_ti()}, peak_currents=peak_gate_currents(),
                resistor_power=gate_resistor_power(), decoupling=decoupling(), bias=bias_budget(),
                dv_dt=[dv_dt_and_cmti(o) for o in ops if o["vin_V"] == 440.0 or o["vin_V"] == 400.0],
                gate_loop=gate_loop_damping(), rails_check={"V_GS_extremes_V": [V_DD + 0.7, V_EE - 0.6], "abs_max_V": [-10, 23], "fallback_C3M_abs_max_V": [-8, 19]})
    des = desat()
    dtm = dead_time()
    ind = inductor_summary(ops)
    cin = input_capacitors(ops)
    cout = output_capacitors(ops)
    bl = bleeders()
    sens = dict(tmcs1133=tmcs1133(ops), ladder_vin=ladder(N_TOP_VIN, [UVLO_STOP, UVLO_START, 360.0, 400.0, 440.0, VIN_OVP, VIN_SURV]),
                ladder_vout=ladder(N_TOP_VOUT, [V_OUT, 220.0, VOUT_OVP, 240.0]), comparators=comparators())

    # ---- thermal corners ---------------------------------------------------- #
    therm_rows = []
    for row in mos_rows:
        if row["k_RG"] in (1.3, 2.0):
            j = junction(row["HS_total_W"], row["LS_total_W"])
            j_spread = junction(row["HS_total_W"], row["LS_total_W"], r_spread=R_SPREAD[1])
            j_fan = junction(row["HS_total_W"], row["LS_total_W"], r_hs=R_TH_HS * (1 + FAN_DERATE_RTH))
            therm_rows.append(dict(corner=row["corner"], R_variant=row["R_variant"], k_RG=row["k_RG"], P_HS_W=row["HS_total_W"], P_LS_W=row["LS_total_W"],
                                   P_total_W=row["pair_W"], **j, T_J_HS_with_spreading_C=j_spread["T_J_HS_C"], T_J_HS_fan_10p8V_C=j_fan["T_J_HS_C"]))
    exp_j = junction(mos_expected["HS_total_W"], mos_expected["LS_total_W"])
    hs_hot = max(therm_rows, key=lambda r: r["T_J_HS_C"])
    hs_hot_k13_max = max((r for r in therm_rows if r["k_RG"] == 1.3 and r["R_variant"] == "max"), key=lambda r: r["T_J_HS_C"])
    p_hs_for_offset = hs_hot_k13_max["P_HS_W"]
    thermal = dict(
        model=f"T_sink = T_A + R_th,HS (P_HS + P_LS); T_J = T_sink + P_dev (R_pad + R_JC); R_th,HS {R_TH_HS:.2f}, R_pad {R_PAD:.2f}, R_JC {R_TH_JC:.2f} K/W, T_A {T_A:.0f} degC",
        corners=therm_rows, expected_400V_25A_100C=dict(P_HS_W=mos_expected["HS_total_W"], P_LS_W=mos_expected["LS_total_W"], **exp_j),
        hottest_HS_corner=hs_hot, hottest_HS_corner_k1p3_maxR=hs_hot_k13_max,
        P_max_W={"150C": p_max_kr_th_001(TJ_LIMIT), "125C": p_max_kr_th_001(TJ_PREF)},
        P_max_margin_over_hottest_HS_k1p3_maxR=p_max_kr_th_001(TJ_LIMIT) / p_hs_for_offset,
        fan_failure=fan_failure(hs_hot_k13_max["P_total_W"], hs_hot_k13_max["T_sink_C"]),
        ntc_to_TJ_offset_K={"typ_440V_27p5A": T_SPREAD_NTC[0] + next(r for r in therm_rows if r["corner"] == "440V/27.5A" and r["R_variant"] == "typ" and r["k_RG"] == 1.3)["P_HS_W"] * (R_PAD + R_TH_JC),
                            "maxR_360V_27p5A": T_SPREAD_NTC[1] + p_hs_for_offset * (R_PAD + R_TH_JC),
                            "baseline_statement_K": [50, 66], "note": "baseline (schema 3) states T_NTC + 50-66 K at full load with the 1.4 K/W pad (4 K spreading offset, loss table without E_oss); the offsets here include E_oss and the 6 K upper offset for the max-R case and are load dependent (the earlier +45 K figure belonged to a 0.80 K/W pad)"},
        copper=copper(),
    )
    aux = aux_12v(gate["bias"])
    pp = power_path(ops)
    eff = efficiency(ops, ind, cin, thermal["copper"], bl, gate["bias"])

    # ---- invariants ---------------------------------------------------------- #
    sat = ind["saturation"]
    worst_util = max(r["utilisation"] for r in util_rows)
    tj_max = max(r["T_J_HS_C"] for r in therm_rows)
    eta_typ = next(s for s in eff["scenarios"] if s["scenario"] == "typical_expected")["eta_with_aux_electronics"]
    eta_worst = next(s for s in eff["scenarios"] if s["scenario"] == "bounded_worst")["eta_with_aux_electronics"]
    step_worst = max(r["step_12p5A_V"] for r in cout["transients"])
    dump_worst = max(cout["load_dump_peak_V_fc2kHz"], cout["load_dump_27p5A_peak_V_fc2kHz"])
    invariants = [
        check("input film RMS margin", "I_rated (14.5 A) > I_Cin,rms/2", cin["film"]["I_rms_each_A_worst"], I_RMS_IN_RATING, cin["film"]["I_rms_each_A_worst"] < I_RMS_IN_RATING, "A"),
        check("output film RMS margin", "I_rated (23.5 A) > I_Cout,rms/2", cout["I_rms_each_A"], I_RMS_OUT_RATING, cout["I_rms_each_A"] < I_RMS_OUT_RATING, "A"),
        check("saturation ratio nominal", "L(41 A)/L(25 A) >= 0.70", sat["L41_over_L25_nominal"], L_RATIO_MIN, sat["L41_over_L25_nominal"] >= L_RATIO_MIN),
        check("saturation ratio worst", "L_worst(41 A)/L_worst(25 A) >= 0.70", sat["L41_over_L25_worst_min_curve"], L_RATIO_MIN, sat["L41_over_L25_worst_min_curve"] >= L_RATIO_MIN),
        check("flux criterion", "B_dc(41 A) + B_ac,pk <= 0.8 B_sat", sat["B_total_41A_T"], sat["B_limit_T"], sat["B_total_41A_T"] <= sat["B_limit_T"], "T"),
        check("junction temperature", "T_J,HS < 150 degC at every corner incl. max-R and k_RG 2.0", tj_max, TJ_LIMIT, tj_max < TJ_LIMIT, "degC"),
        check("voltage utilisation", "(Vin + L_loop di/dt)/1200 V < 0.80 (worst 60 nH, 460 V)", worst_util, UTIL_LIMIT_REP, worst_util < UTIL_LIMIT_REP),
        check("discharge merged networks", "both banks < 60 V within 60 s", bl["discharge_merged_from_480_220V"]["time_to_both_below_60V_s"], T_DISCHARGE_MAX,
              bl["discharge_merged_from_480_220V"]["time_to_both_below_60V_s"] < T_DISCHARGE_MAX, "s"),
        check("discharge bleeders only", "both banks < 60 V within 60 s (indicator chains absent)", bl["discharge_bleeders_only_from_480_220V"]["time_to_both_below_60V_s"], T_DISCHARGE_MAX,
              bl["discharge_bleeders_only_from_480_220V"]["time_to_both_below_60V_s"] < T_DISCHARGE_MAX, "s"),
        check("aux budget vs I_CB", "I_12V,pull-in (10.8 V) < I_CB,typ", aux["total_pull_in_A"], aux["I_CB_A_typ"], aux["total_pull_in_A"] < aux["I_CB_A_typ"], "A",
              "margin against the assumed -10 % I_CB minimum is only " + f"{aux['margin_pull_in_vs_I_CB_min']:.2f}x during relay pull-in (human review)"),
        check("load step", "12.5 A step excursion <= 10 V at fc 2.0 kHz", step_worst, V_STEP_MAX, step_worst <= V_STEP_MAX, "V"),
        check("load dump vs output OVP", "25 A / 27.5 A dump peak < 230 V (fc 2.0 kHz)", dump_worst, VOUT_OVP, dump_worst < VOUT_OVP, "V"),
        check("input ripple", "dV_in <= 2 % at 27.5 A", cin["ripple_pct_27p5A"], VIN_RIPPLE_PCT, cin["ripple_pct_27p5A"] <= VIN_RIPPLE_PCT, "%"),
        check("DESAT response", "blanking + t_OCOFF + soft turn-off <= 1.5 us (max)", des["response_us_min_typ_max"][2], 1.5, des["response_us_min_typ_max"][2] <= 1.5, "us"),
        check("OC trip vs overload", "I_OC lower bound (-10 %) > worst overload peak 32.0 A", sens["tmcs1133"]["OC"]["band_A_max"][0], I_PK_OVL_WORST, sens["tmcs1133"]["OC"]["band_A_max"][0] > I_PK_OVL_WORST, "A"),
        check("dead time", "programmed 300 ns - 35 ns erosion >= 150 ns minimum", dtm["effective_after_erosion_ns"], dtm["minimum_adopted_ns"], dtm["effective_after_erosion_ns"] >= dtm["minimum_adopted_ns"], "ns"),
        check("efficiency target", "typical (incl. aux electronics) >= 98.0 %", eta_typ, ETA_TARGET, eta_typ >= ETA_TARGET),
        check("efficiency floor", "bounded worst (incl. aux electronics) >= 97.5 %", eta_worst, ETA_FLOOR, eta_worst >= ETA_FLOOR),
        check("inductor thermal limit", "P_loss,overload < P_max(125 degC hot spot)", ind["thermal"]["P_max_W_at_125C_hot_spot"] / ind["thermal"]["margin_over_overload_loss"],
              ind["thermal"]["P_max_W_at_125C_hot_spot"], ind["thermal"]["margin_over_overload_loss"] > 1.0, "W"),
    ]

    # ---- baseline cross-check ----------------------------------------------- #
    def xc(name, computed, baseline, tol_abs, note=""):
        diff = computed - baseline
        return dict(item=name, computed=computed, baseline=baseline, difference=diff, tolerance=tol_abs, status="agrees" if abs(diff) <= tol_abs else "differs", note=note)

    bf = BASELINE_FIGURES
    xchk = []
    for op in ops:
        key = f"{op['vin_V']:.0f}"
        if op["iout_A"] == I_OUT:
            xchk.append(xc(f"dI_L {corner_name(op)}", op["dIL_App"], bf["dIL_App_nominal_25A"][key], 0.1))
            xchk.append(xc(f"I_pk {corner_name(op)}", op["ipk_A"], bf["ipk_A_25A"][key], 0.1))
            xchk.append(xc(f"I_in eta 0.98 {corner_name(op)}", op["iin_A_eta98"], bf["iin_A_eta98_25A"][key], 0.02))
        else:
            xchk.append(xc(f"I_pk {corner_name(op)}", op["ipk_A"], bf["ipk_A_27p5A"][key], 0.15, "27.5 A rows evaluated with L(27.5 A) = 263 uH (verifier); baseline rounded to 0.1 A"))
    o440 = next(o for o in ops if o["vin_V"] == 440.0 and o["iout_A"] == I_OUT)
    xchk.append(xc("dI_L 440 V AL -8 %", o440["dIL_App_AL_minus8"], bf["dIL_App_440V_AL_minus8"], 0.1))
    o440o = next(o for o in ops if o["vin_V"] == 440.0 and o["iout_A"] == I_OVL)
    xchk.append(xc("I_pk worst 440 V / 27.5 A (AL -8 %)", o440o["ipk_A_AL_minus8"], bf["ipk_A_27p5A_worst"], 0.1))
    xchk.append(xc("R_DS(on) 150 degC typ [mohm]", r150 * 1e3, bf["rds_on_150C_mohm"], 0.1))
    m13 = next(r for r in mos_rows if r["corner"] == "400V/25A" and r["R_variant"] == "typ" and r["k_RG"] == 1.3)
    xchk.append(xc("MOSFET pair 400 V/25 A, 150 degC, k 1.3 [W] (baseline excludes E_oss and uses flat V_SD)",
                   m13["pair_W"] - m13["HS_oss_W"] - m13["LS_dt_W"] + m13["LS_dt_W_250ns_flat_4p6V"], bf["mosfet_pair_400V_25A_150C_k1p3_W"], 0.3))
    m20 = next(r for r in mos_rows if r["corner"] == "400V/25A" and r["R_variant"] == "typ" and r["k_RG"] == 2.0)
    xchk.append(xc("MOSFET pair 400 V/25 A, 150 degC, k 2.0 [W] (same convention)", m20["pair_W"] - m20["HS_oss_W"] - m20["LS_dt_W"] + m20["LS_dt_W_250ns_flat_4p6V"], bf["mosfet_pair_400V_25A_150C_k2p0_W"], 0.5))
    m44 = next(r for r in mos_rows if r["corner"] == "440V/27.5A" and r["R_variant"] == "typ" and r["k_RG"] == 1.3)
    xchk.append(xc("MOSFET pair 440 V/27.5 A, 150 degC, k 1.3 [W] (same convention)", m44["pair_W"] - m44["HS_oss_W"] - m44["LS_dt_W"] + m44["LS_dt_W_250ns_flat_4p6V"], bf["mosfet_pair_440V_27p5A_150C_W"], 0.6,
                   "ripple from the real choke L(27.5 A) differs from the 267 uH seed"))
    m36 = next(r for r in mos_rows if r["corner"] == "360V/27.5A" and r["R_variant"] == "typ" and r["k_RG"] == 1.3)
    xchk.append(xc("P_HS 360 V/27.5 A typ [W] (baseline excludes E_oss)", m36["HS_total_W"] - m36["HS_oss_W"], bf["P_HS_360V_27p5A_typ_W"], 0.4))
    xchk.append(xc("gate power Wolfspeed form [W]", gate["power_W"]["wolfspeed_form"], bf["gate_power_W_wolfspeed_form"], 0.002))
    xchk.append(xc("peak gate source current [A]", gate["peak_currents"]["source_A_10ohm"], bf["peak_gate_current_A"]["source"], 0.02))
    xchk.append(xc("peak gate sink current [A]", gate["peak_currents"]["sink_A"], bf["peak_gate_current_A"]["sink"], 0.02))
    xchk.append(xc("COM-VEE droop [mV]", gate["decoupling"]["COM_VEE_droop_mV"], bf["com_vee_droop_mV"], 1.0))
    xchk.append(xc("DESAT trip V_DS typ [V]", des["V_DS_trip_V"][1], bf["desat_trip_vds_V"], 0.05))
    xchk.append(xc("DESAT blanking typ [ns]", des["blanking"]["t_bl_ns_min_typ_max"][1], bf["desat_blanking_ns"], 2.0))
    xchk.append(xc("DESAT response max [us]", des["response_us_min_typ_max"][2], bf["desat_response_us"][1], 0.02))
    xchk.append(xc("L(25 A) nominal [uH]", ind["L_vs_I"]["25A"]["L_uH_nominal"], bf["L_uH"]["25A"], 1.0))
    xchk.append(xc("L(41 A) nominal [uH]", ind["L_vs_I"]["41A"]["L_uH_nominal"], bf["L_uH"]["41A"], 2.0))
    xchk.append(xc("L_worst(25 A) [uH] (baseline uses flat 80 % minimum)", ind["L_vs_I"]["25A"]["L_uH_worst_flat80"], bf["L_worst_uH"]["25A"], 1.0))
    xchk.append(xc("L_worst(41 A) [uH] (interpolated minimum curve; baseline hand-off 175)", ind["L_vs_I"]["41A"]["L_uH_worst_min_curve"], bf["L_worst_uH"]["41A"], 4.0,
                   "178 vs 175: the baseline figure is the more conservative hand-off and is used for the trip overshoot"))
    xchk.append(xc("I_sat 30 % drop [A]", sat["I_sat_30pct_drop_from_L0_A_nominal"], bf["isat_30pct_A"], 0.2))
    xchk.append(xc("inductor loss 400 V/25 A [W]", next(c for c in ind["corners_typical_core"] if c["corner"] == "400V/25A")["P_total_W"], bf["inductor_loss_W"]["400V_25A"], 0.2))
    xchk.append(xc("inductor loss 440 V/27.5 A [W]", next(c for c in ind["corners_typical_core"] if c["corner"] == "440V/27.5A")["P_total_W"], bf["inductor_loss_W"]["440V_27p5A"], 0.3))
    xchk.append(xc("input film RMS each [A]", cin["film"]["I_rms_each_A_worst"], bf["cin_irms_each_A_worst"], 0.05))
    xchk.append(xc("input ripple 27.5 A [Vpp]", cin["ripple_Vpp_27p5A"], bf["cin_ripple_Vpp_27p5A"], 0.1))
    xchk.append(xc("output step excursion fc 2.5 kHz [V]", cout["transients"][1]["step_12p5A_V"], bf["cout_step_V_fc2p5kHz"], 0.1))
    xchk.append(xc("load dump 25 A fc 2.5 kHz [V]", cout["transients"][1]["dump_25A_V"], bf["cout_load_dump_V"], 0.1))
    xchk.append(xc("discharge merged networks [s] (baseline 'about 30' = bleeder-only estimate at nominal C)", bl["discharge_merged_from_460_200V"]["time_to_both_below_60V_s"], bf["discharge_s"], 5.0,
                   "with the indicator chains in parallel the time is about 20 s; bleeders alone give about 36 s; both < 60 s"))
    xchk.append(xc("TMCS1133 LSB [mA]", sens["tmcs1133"]["LSB_mA"], bf["tmcs_lsb_mA"], 0.02))
    xchk.append(xc("TMCS1133 full scale [A]", sens["tmcs1133"]["full_scale_A"], bf["tmcs_fs_A"], 0.1))
    xchk.append(xc("OC trip chain [ns]", sens["tmcs1133"]["trip_chain"]["t_ns"], bf["oc_trip_chain_ns"], 1.0))
    xchk.append(xc("OC worst peak with L 175 uH [A]", sens["tmcs1133"]["trip_chain"]["worst_peak_A"], bf["oc_worst_peak_A"], 0.1))
    xchk.append(xc("OVP_out [V]", sens["comparators"]["OVP_out"]["output_V"], bf["ovp_out_V"], 0.2))
    xchk.append(xc("OVP_in [V]", sens["comparators"]["OVP_in"]["bus_V"], bf["ovp_in_V"], 0.5))
    for t, v in bf["ntc_readout_V"].items():
        xchk.append(xc(f"NTC readout {t} degC [V]", ntc_v(float(t)), v, 0.01))
    xchk.append(xc("T_J,HS 400 V/25 A typ [degC] (baseline excludes E_oss)", junction(m13["HS_total_W"] - m13["HS_oss_W"], m13["LS_total_W"])["T_J_HS_C"], bf["T_J_HS_400V_25A_C"], 1.5))
    t36 = next(r for r in therm_rows if r["corner"] == "360V/27.5A" and r["R_variant"] == "max" and r["k_RG"] == 1.3)
    xchk.append(xc("T_J,HS 360 V/27.5 A max-R [degC] (incl. E_oss and V_SD(I))", t36["T_J_HS_C"], bf["T_J_HS_360V_27p5A_maxR_C"], 3.0))
    t44 = next(r for r in therm_rows if r["corner"] == "440V/27.5A" and r["R_variant"] == "max" and r["k_RG"] == 1.3)
    xchk.append(xc("T_J,HS 440 V/27.5 A max-R [degC]", t44["T_J_HS_C"], bf["T_J_HS_440V_27p5A_maxR_C"], 3.0))
    xchk.append(xc("P_max per device [W]", thermal["P_max_W"]["150C"], bf["P_max_per_device_W"], 0.2))
    xchk.append(xc("copper width 25 A / 10 K external [mm] (baseline 12 mm rule)", ipc_width_mm(I_OUT, 10.0, K_IPC_EXT), bf["copper_width_25A_20K_mm"], 1.0, "baseline rounds 12.7 mm (10 K) to the 12 mm design rule"))
    xchk.append(xc("I_CB [A]", aux["I_CB_A_typ"], bf["i_cb_A"], 0.01))
    xchk.append(xc("aux total pull-in [A]", aux["total_pull_in_A"], bf["aux_total_pull_in_A"], 0.01))
    xchk.append(xc("aux total steady [A]", aux["total_steady_A"], bf["aux_total_steady_A"], 0.01))
    xchk.append(xc("precharge tau nominal [ms]", pp["precharge"]["by_R"]["nominal"]["tau_ms"], bf["precharge_tau_ms"], 0.1))
    xchk.append(xc("precharge energy 440 V [J]", pp["precharge"]["E_J_440V"], bf["precharge_E_J"][0], 0.1))

    off_typ = thermal["ntc_to_TJ_offset_K"]["typ_440V_27p5A"]
    off_max = thermal["ntc_to_TJ_offset_K"]["maxR_360V_27p5A"]
    ff_times = [r["time_to_100C_trip_s"] for r in thermal["fan_failure"] if r["time_to_100C_trip_s"] is not None]
    ff_min, ff_max = min(ff_times), max(ff_times)
    bw = next(sc for sc in eff["scenarios"] if sc["scenario"] == "bounded_worst")
    open_items = [
        "Parasitic turn-on: the charge-based RC model spans 3.6-7.0 V of off-state excursion over the stated Q_gd (20-27 nC) and edge (8-13 ns) ranges, i.e. V_GS up to about +3 V against the 2.0 V (25 degC) minimum threshold; the baseline's 4.5-5.2 V is the mid-range. Miller clamp mandatory; off-state V_GS measurement (PRD-09301 6.1) decides R_G,off and bias.",
        f"NTC-to-T_J offset with the 1.4 K/W design pad is {off_typ:.0f} K (typical, 440 V / 27.5 A) to {off_max:.0f} K (max-R, 360 V / 27.5 A) at full load, consistent with the baseline's 50-66 K band; the 110 degC hardware trip then maps to T_J about {110 + off_typ:.0f}-{110 + off_max:.0f} degC and the 100 degC firmware trip to about {100 + off_typ:.0f}-{100 + off_max:.0f} degC at full load - neither threshold holds T_J at the 150 degC design limit at full load, so the 90/100/110 degC ladder needs review (KR-TH-003).",
        f"Fan-fail time to the 100 degC firmware trip from the {hs_hot_k13_max['T_sink_C']:.0f} degC steady state is {ff_min:.0f}-{ff_max:.0f} s for the lumped D K sink (R_nat 1.73-2.5 K/W and mass 0.3-0.6 kg unverified), not the 50-100 s carried in the baseline (that figure was the single-width unit from 88 degC); the conclusion (T_J > 175 degC at stall, OTP and FAN_TACH derate mandatory) stands.",
        "Merged bleeder + indicator networks discharge both banks in about 20 s (bleeders alone about 36 s); the baseline's 'about 30 s' is the nominal-C bleeder-only estimate. Output indicator chain (2 x 100 k 1206) sees 220 V / 0.48 W per element under a high-side-short fault at 440 V - above typical 1206 ratings; use >= 3 elements or 2512 parts if the fault must be survived.",
        "Aux 12 V: the pull-in total (1.76 A at 10.8 V) exceeds an assumed -10 % circuit-breaker minimum (1.76 A) with zero margin for the 50 ms relay operate time; stagger fan start and relay pull-in or move the fan upstream of the eFuse (baseline fallback).",
        "Mezzanine 12 V pins carry 0.43-0.49 A each (fan, relay coil and bias modules all sit on the power board), above the architecture's 0.4 A per-pin target but 6x below the 3 A WR-PHD rating.",
        "Dead-time loss with V_SD at the actual current is 3.1-3.6 W (250 ns) / 3.8-4.3 W (300 ns) versus the 2.9-3.2 W flat-4.6 V figures of the baseline loss table (body-diode slope 0.07 ohm is an unverified assumption).",
        "Sensing bias module: sourcing about 20 mA into the 5 V COM output through RLIM needs RLIM <= about 470 ohm and dissipates about 0.2 W in RLIM plus the internal FET (continuous, outside the RLIM pin's 16 %-run-time qualification) - feasibility of the COM-VEE 5.0 V configuration remains the baseline's open item.",
        f"Bounded-worst efficiency is {100 * bw['eta_converter_only']:.2f} % converter-only, {100 * bw['eta_with_aux_electronics']:.2f} % with the aux electronics (baseline convention) and {100 * bw['eta_system']:.2f} % as a full system with relay hold and fan - at or just below the 98.0 % target and {100 * (bw['eta_system'] - ETA_FLOOR):.1f} % above the 97.5 % floor; the k_RG factor (1.3-2.0) is the largest single uncertainty and must be measured by double-pulse test.",
        "The twentieth verification report (assumptions-register fact-check, verify_assumptions_register_and_requirements_se_factcheck.json) was recovered after the first run of this script; its required changes concern the register text (ADC LSB, inrush charge-time range, CTI class bound, the 0.51 A maximum rating of a candidate fan that is not the baseline part) and change no input of this script.",
    ]

    return dict(
        schema="aipe-v2-calculations/1",
        title="V2 calculation record: 400 V -> 200 V, 5 kW, 50 kHz SiC synchronous buck (C4MS025120K, UCC21710-Q1, custom High Flux choke)",
        status=BANNER.strip("*"),
        generated_by="python -m automation.scripts.calculate_sic_buck",
        precedence="design_decisions.json (schema 3) > research record after its two verify_*.json required_changes > added assumptions (labelled)",
        verification_levels_used=[LV_USER, LV_DS, LV_PAGE, LV_SNIP, LV_UNV, LV_AN, LV_ASM, LV_STD, "simulated: none"],
        inputs_register=REGISTER,
        operating_points=ops, mosfet=mosfet, gate_drive=gate, desat=des, dead_time=dtm, inductor=ind,
        capacitors=dict(input=cin, output=cout, bleeders=bl), sensing=sens, thermal=thermal, aux_12V=aux, power_path=pp,
        efficiency=eff, invariants=invariants, baseline_crosscheck=xchk,
        knowledge_applicability=[dict(id=i, type=t, applicability=a, how_applied=h) for i, t, a, h in KNOWLEDGE_APPLICABILITY],
        limitations=LIMITATIONS, open_items=open_items,
    )



# --------------------------------------------------------------------------- #
# Markdown report                                                             #
# --------------------------------------------------------------------------- #
def fmt(x, nd: int = 2) -> str:
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if x == 0:
            return "0"
        if abs(x) >= 1000:
            return f"{x:,.0f}"
        return f"{x:.{nd}f}"
    if x is None:
        return "-"
    return str(x)


def table(headers: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(fmt(c) if not isinstance(c, str) else c for c in r) + " |")
    out.append("")
    return out


def markdown(d: dict) -> str:
    L: list[str] = []
    A = L.append
    A(BANNER)
    A("")
    A("# V2 calculation record - 400 V to 200 V, 5 kW, 50 kHz SiC synchronous buck")
    A("")
    A("Generated by `python -m automation.scripts.calculate_sic_buck` (standard library only). Machine-readable results: [calculations.json](calculations.json). "
      "Baseline: [design_decisions.json](design_decisions.json) (schema 3), which wins over every research record; where it is silent the research records "
      "([research/mosfet.json](research/mosfet.json), [research/gate_driver.json](research/gate_driver.json), [research/inductor.json](research/inductor.json), "
      "[research/capacitors.json](research/capacitors.json), [research/sensing_protection.json](research/sensing_protection.json), [research/thermal.json](research/thermal.json), "
      "[research/controller_aux_interconnect.json](research/controller_aux_interconnect.json), [research/standards_safety.json](research/standards_safety.json)) are used after applying the "
      "required_changes of their verify_*.json reports. Every number is a first-order analytical estimate; nothing is simulated or measured. "
      "Verification tags: fetched-datasheet, manufacturer-page, search-snippet, unverified, analytically-checked, added-assumption (basis stated), standard-formula. "
      "All invariants listed in section 13 passed when this file was generated; the script fails loudly otherwise.")
    A("")

    # 1 inputs
    A("## 1. Inputs and verification levels")
    A("")
    A("The complete register (" + str(len(d["inputs_register"])) + " entries) is in `calculations.json` -> `inputs_register`. Key inputs:")
    A("")
    key = ["V_OUT", "P_OUT", "F_SW", "VIN_corners", "I_OVERLOAD", "MOSFET_R25_typ_15V", "MOSFET_R175_over_R25", "E_on_test", "E_off_test", "E_rr_test", "E_oss_800V",
           "Q_G", "R_thJC", "k_RG_range", "V_SD_slope", "E_oss_voltage_exponent", "core_AL_per_core_nH", "turns", "perm_vs_H_fit", "core_loss_fit", "C_in_film_each", "C_out_film_each",
           "C_HF_remaining_at_440V", "TMCS1133C2A_sensitivity", "R_th_heatsink_forced", "R_th_pad_design", "TPS26400_R_ILIM", "TPS26400_I_CB_tolerance", "PTC_R25", "fan_current_cap"]
    reg = {r["name"]: r for r in d["inputs_register"]}
    rows = []
    for k in key:
        r = reg[k]
        v = r["value"]
        vs = json.dumps(v) if isinstance(v, (list, dict)) else (f"{v:.4g}" if isinstance(v, float) else str(v))
        rows.append([k, vs, r["unit"], r["verification"], r["source"] + (" - " + r["note"] if r["note"] else "")])
    L += table(["Input", "Value", "Unit", "Verification", "Source / note"], rows)

    # 2 operating points
    A("## 2. Operating points")
    A("")
    A("Formulas: D = Vout/Vin; Iin = Pout/(eta Vin); dI_L = Vout(1-D)/(L(Io) fs) with L(Io) of the real choke (nominal AL, AL -8 %, AL -8 % with the datasheet-minimum bias curve); "
      "I_pk = Io + dI/2; I_L,rms = sqrt(Io^2 + dI^2/12); I_HS,rms = sqrt(D) I_L,rms; I_LS,rms = sqrt(1-D) I_L,rms; I_Cin,rms = sqrt(D(Io^2 + dI^2/12) - (D Io)^2); I_Cout,rms = dI/sqrt(12). "
      "The 27.5 A rows use L(27.5 A) = 263 uH (verifier correction), so the overload peak is 31.65 A nominal / 32.0 A at AL -8 %.")
    A("")
    rows = [[corner_name(o), fmt(o["D"], 3), fmt(o["iin_A_eta1"]), fmt(o["iin_A_eta98"]), fmt(o["L_uH_nominal"], 0), fmt(o["dIL_App"]), fmt(o["dIL_App_AL_minus8"]), fmt(o["dIL_App_worst"]),
             fmt(o["ipk_A"]), fmt(o["ipk_A_AL_minus8"]), fmt(o["iL_rms_A"]), fmt(o["iHS_rms_A"]), fmt(o["iLS_rms_A"]), fmt(o["iCin_rms_A"]), fmt(o["iCout_rms_A"])] for o in d["operating_points"]]
    L += table(["Corner", "D", "Iin eta=1 / A", "Iin eta=0.98 / A", "L(Io) / uH", "dI nom / App", "dI AL-8% / App", "dI worst / App", "I_pk / A", "I_pk AL-8% / A",
                "I_L,rms / A", "I_HS,rms / A", "I_LS,rms / A", "I_Cin,rms / A", "I_Cout,rms / A"], rows)

    # 3 MOSFET
    m = d["mosfet"]
    A("## 3. MOSFET losses (C4MS025120K, one device per position)")
    A("")
    A("R_DS(on)(T) = R25 [1 + 0.88 (T-25)/150]: " + ", ".join(f"{k} {fmt(v, 1)} mohm" for k, v in m["R_DS_on_mohm"].items()) + ". "
      "HS: P_cond = I_HS,rms^2 R; E_on/E_off = E_test (Vin/800)(I/39.2) k_RG with I_on = Io - dI/2, I_off = Io + dI/2; P_oss = E_oss(800 V)(Vin/800)^1.5 fs (added by the verifier, about 1 W). "
      "LS: P_cond = I_LS,rms^2 R; P_rr = E_rr (Vin/800)(I_on/39.2) fs (lower bound, factor-two uncertainty); P_dt = fs t_dt [V_SD(I_on) I_on + V_SD(I_off) I_off] with V_SD(I) = 4.6 V + 0.07 ohm (I - 19.6 A). "
      "Share is given against the rated 5 kW and against the actual output power (5.5 kW at 27.5 A). Scaling uncertainty about +/-30 %.")
    A("")
    rows = []
    for r in m["rows"]:
        if r["R_variant"] == "typ" and r["k_RG"] in (1.3, 2.0):
            rows.append([r["corner"], r["k_RG"], fmt(r["HS_cond_W"], 1), fmt(r["HS_sw_W"], 1), fmt(r["HS_oss_W"], 1), fmt(r["HS_total_W"], 1), fmt(r["LS_cond_W"], 1), fmt(r["LS_rr_W"], 1),
                         fmt(r["LS_dt_W"], 1), fmt(r["LS_dt_W_300ns"], 1), fmt(r["LS_total_W"], 1), fmt(r["pair_W"], 1), fmt(r["share_of_5kW_pct"], 2), fmt(r["share_of_actual_Pout_pct"], 2)])
    L += table(["Corner (T_J 150 degC, typ R)", "k_RG", "HS cond / W", "HS sw / W", "HS E_oss / W", "HS total / W", "LS cond / W", "LS E_rr / W", "LS dt 250 ns / W", "LS dt 300 ns / W",
                "LS total / W", "Pair / W", "Share of 5 kW / %", "Share of Pout / %"], rows)
    rows = []
    for r in m["rows"]:
        if r["R_variant"] == "max" and r["k_RG"] in (1.3, 2.0) and r["corner"] in ("400V/25A", "360V/27.5A", "440V/27.5A"):
            rows.append([r["corner"], r["k_RG"], fmt(r["HS_total_W"], 1), fmt(r["LS_total_W"], 1), fmt(r["pair_W"], 1), fmt(r["share_of_actual_Pout_pct"], 2)])
    e = m["expected_400V_25A_100C_k1p3"]
    rows.append(["400V/25A expected T_J 100 degC", 1.3, fmt(e["HS_total_W"], 1), fmt(e["LS_total_W"], 1), fmt(e["pair_W"], 1), fmt(e["share_of_5kW_pct"], 2)])
    e = m["expected_400V_25A_100C_k2p0"]
    rows.append(["400V/25A expected T_J 100 degC", 2.0, fmt(e["HS_total_W"], 1), fmt(e["LS_total_W"], 1), fmt(e["pair_W"], 1), fmt(e["share_of_5kW_pct"], 2)])
    L += table(["Variant (max-R 57.2 mohm at 150 degC unless noted)", "k_RG", "HS total / W", "LS total / W", "Pair / W", "Share / %"], rows)
    A("Dead-time loss at the baseline's flat 4.6 V: " + ", ".join(f"{r['corner']} {fmt(r['LS_dt_W_250ns_flat_4p6V'], 1)} W" for r in m["rows"] if r["R_variant"] == "typ" and r["k_RG"] == 1.3) +
      " (250 ns). Current margins: I_D(100 degC)/I_rms,max = " + fmt(m["current_margins"]["I_D_100C_over_I_rms_max"], 1) + "x, I_DM/I_pk,worst = " + fmt(m["current_margins"]["I_DM_over_I_pk_worst"], 1) + "x.")
    A("")
    A("Voltage utilisation V_pk = Vin + L_loop di/dt (di/dt 2.5 A/ns), U = V_pk/1200 V; limits 80 % repetitive / 90 % at OVP / 70 % DC are engineering judgement for human review:")
    A("")
    L += table(["Vin / V", "L_loop / nH", "V_os / V", "V_pk / V", "Utilisation"], [[fmt(r["vin_V"], 0), fmt(r["L_loop_nH"], 0), fmt(r["V_os_V"], 0), fmt(r["V_pk_V"], 0), fmt(r["utilisation"], 3)] for r in m["utilisation"]])
    A("Parasitic turn-on (charge-based, KR-GD-003 adapted): dV_GS = (Q_gd/t_edge) R [1 - exp(-t_edge/(R C_iss))] with C_iss 3.09 nF, off path 5.6 ohm (3.2 ohm with the clamp engaged); V_GS = -4 V + dV_GS against V_GS(th),min 2.0 V (25 degC; hot minimum unpublished):")
    A("")
    L += table(["Q_gd / nC", "t_edge / ns", "Path", "dV_GS / V", "V_GS peak / V", "Margin to 2.0 V / V"],
               [[fmt(r["Q_gd_nC"], 0), fmt(r["t_edge_ns"], 0), r["path"], fmt(r["dV_GS_V"]), fmt(r["V_GS_peak_V"]), fmt(r["margin_to_Vth_min_25C_V"])] for r in m["parasitic_turn_on"]])
    A(m["parasitic_note"] + ".")
    A("")

    # 4 gate drive
    g = d["gate_drive"]
    A("## 4. Gate drive, bias supply, dv/dt")
    A("")
    b = g["bias"]
    pc = g["peak_currents"]
    rp = g["resistor_power"]
    dc = g["decoupling"]
    rows = [
        ["Gate power, Wolfspeed form Q_G fs (V_DD - V_EE)", fmt(g["power_W"]["wolfspeed_form"], 3), "W", "KR-IS-001"],
        ["Gate power, TI TIDA-010054 Eq. 30 form (factor 2, EC-014 conflict)", fmt(g["power_W"]["TI_form_factor2"], 3), "W", "KR-IS-001 conflict; budget uses the larger"],
        ["Peak gate current source, 10 ohm: 19 V/(10 + 2.6 + 2.5)", fmt(pc["source_A_10ohm"]) + " (" + fmt(pc["source_A_10ohm_range"][0]) + "-" + fmt(pc["source_A_10ohm_range"][1]) + ")", "A", "6.8 ohm: " + fmt(pc["source_A_6p8ohm"]) + " A; driver 10 A"],
        ["Peak gate current sink, 3.3 ohm: 19 V/(3.3 + 2.6 + 0.3)", fmt(pc["sink_A"]) + " (" + fmt(pc["sink_A_range"][0]) + "-" + fmt(pc["sink_A_range"][1]) + ")", "A", "driver 10 A"],
        ["R_G,on average / pulse power", fmt(rp["R_on_avg_W"], 3) + " / " + fmt(rp["R_on_pulse_W"], 1), "W", "pulse tau " + fmt(rp["R_on_tau_ns"], 0) + " ns; 1206 anti-surge 0.66 W"],
        ["R_G,off average / pulse power", fmt(rp["R_off_avg_W"], 3) + " / " + fmt(rp["R_off_pulse_W"], 1), "W", "pulse tau " + fmt(rp["R_off_tau_ns"], 0) + " ns"],
        ["Decoupling required C_eff >= Q_G/0.1 V; nominal with 35 % X7R loss", fmt(dc["C_eff_required_uF"]) + " / " + fmt(dc["C_nominal_required_uF"]), "uF", "KR-PCB-002"],
        ["VDD-COM 2 x 4.7 uF: effective / droop", fmt(dc["VDD_COM_effective_uF"], 1) + " uF / " + fmt(dc["VDD_COM_droop_mV"], 0) + " mV", "", ""],
        ["COM-VEE 4.7 uF droop", fmt(dc["COM_VEE_droop_mV"], 0), "mV", "baseline ~41 mV"],
        ["Bias per gate channel (Wolfspeed / TI form)", fmt(b["P_gate_channel_W_wolfspeed_form"]) + " / " + fmt(b["P_gate_channel_W_TI_form"]), "W", "gate + quiescent " + fmt(b["P_quiescent_W"], 3) + " W + DESAT 0.07 W + misc 0.015 W; budget 0.32 W"],
        ["Sensing module load (2 x AMC1311 IDD1 max + misc)", fmt(b["sensing_load_mA"], 1) + " mA = " + fmt(b["sensing_module_output_W_at_15V"]) + " W at 15 V", "", "0.4 W budget; RLIM dissipates " + fmt(b["sensing_RLIM_dissipation_W"]) + " W; RLIM <= " + fmt(b["sensing_RLIM_max_ohm"], 0) + " ohm (human review)"],
        ["Utilisation of the 1.5 W rating (HS / LS / sensing)", " / ".join(fmt(100 * v, 0) for v in b["utilisation_of_1p5W_rating"].values()), "%", "1.5 W valid 10.8-13.2 V, TA <= 85 degC; SOA curve not read"],
        ["Module input power, 0.48 W + 1.92 P_out, three modules", fmt(b["P_in_total_W"]), "W", fmt(b["I_12V_A_at_12V"], 2) + " A at 12 V; " + fmt(b["I_12V_A_at_10p8V_with_20pct_margin"], 2) + " A at 10.8 V with 20 % margin; baseline budget " + fmt(b["baseline_budget_A_at_10p8V"], 2) + " A"],
        ["Gate loop Z0 / zeta_on / zeta_off", fmt(g["gate_loop"]["Z0_ohm"]) + " ohm / " + fmt(g["gate_loop"]["zeta_on"], 1) + " / " + fmt(g["gate_loop"]["zeta_off"], 1), "", "overdamped; V_GS extremes about +15.7 / -4.6 V vs -10/+23 V"],
    ]
    L += table(["Quantity", "Value", "Unit", "Source / remark"], rows)
    A("Turn-off dv/dt = I_off/(2 C_oss(400 V)), CMTI margin 150 V/ns / dv/dt, common-mode current i_CM = (C_IO,bias + C_IO,driver) x 120 V/ns:")
    A("")
    L += table(["Corner", "dv/dt / V/ns", "CMTI margin", "i_CM (3.5 pF) / A", "i_CM (5 pF bound) / A"],
               [[r["corner"], fmt(r["turn_off_dv_dt_V_per_ns"], 0), fmt(r["CMTI_margin"]), fmt(r["i_CM_A_3p5pF"]), fmt(r["i_CM_A_5pF_bound"])] for r in g["dv_dt"]])

    # 5 DESAT and dead time
    s = d["desat"]
    dt = d["dead_time"]
    A("## 5. DESAT protection and dead time")
    A("")
    A("CB-GD-001 formulas with the C4MS025120K network (R1 2.2 k, R2 4.99 k, R3 1.0 k, C 680 pF, one US1M diode, V_F 0.6 V assumed): V_A = V_OCTH (R2+R3)/R3; V_DS,trip = V_A - V_F; "
      "I_trip = V_DS,trip/R_DS(on)(175 degC) (linear); V_th = V_DD R3/(R1+R2+R3), R_th = R3 (R1+R2)/(R1+R2+R3), t_bl = -R_th C ln(1 - V_OCTH/V_th); response = t_bl + t_OCOFF + Q(15->3 V)/I_STO.")
    A("")
    bl_ = s["blanking"]
    rows = [
        ["V_A (min/typ/max)", " / ".join(fmt(v) for v in s["V_A_V"]), "V"],
        ["V_DS,trip (min/typ/max)", " / ".join(fmt(v) for v in s["V_DS_trip_V"]), "V"],
        ["R_DS(on) 175 degC typ 18 V / typ 15 V / 15 V-equivalent maximum", " / ".join(fmt(v, 1) for v in s["R_hot_175C_mohm"].values()), "mohm"],
        ["Trip current: max R at typ V_trip / absolute min (min V_trip, max R) / typ (linear) / max", fmt(s["I_trip_A"]["min_typV_maxR"], 0) + " / " + fmt(s["I_trip_A"]["min_absolute_minV_maxR"], 0) + " / " + fmt(s["I_trip_A"]["typ_linear"], 0) + " / " + fmt(s["I_trip_A"]["max"], 0) + " (baseline graph read " + s["I_trip_A"]["baseline_graph_read"] + ")", "A"],
        ["Trip / worst overload peak 32.0 A (max R / typ)", fmt(s["trip_over_overload_peak"]["min"]) + " / " + fmt(s["trip_over_overload_peak"]["typ"]), "x"],
        ["False-trip margin at overload (typ R / max R)", fmt(s["false_trip_margin"]["typ"]) + " / " + fmt(s["false_trip_margin"]["max_R"]), "x"],
        ["Blanking V_th / R_th", fmt(bl_["V_th_V"], 3) + " V / " + fmt(bl_["R_th_ohm"], 0) + " ohm", ""],
        ["External blanking (V_OCTH min/typ/max); typ at 18 V", " / ".join(fmt(v, 0) for v in bl_["t_bl_ns_min_typ_max"]) + "; " + fmt(bl_["t_bl_ns_typ_at_18V"], 0), "ns"],
        ["IC deglitch", " / ".join(str(v) for v in bl_["ic_deglitch_ns"]), "ns"],
        ["Total response min / typ / max (budget 1.5 us)", " / ".join(fmt(v) for v in s["response_us_min_typ_max"]), "us"],
        ["Soft turn-off fault overshoot: gate slew, cut-off, di/dt, V_pk at 460 V / 35 nH", fmt(s["fault_turn_off"]["gate_slew_V_per_ns"], 2) + " V/ns, " + fmt(s["fault_turn_off"]["cut_off_ns"], 0) + " ns, " + fmt(s["fault_turn_off"]["di_dt_A_per_ns"], 1) + " A/ns, " + fmt(s["fault_turn_off"]["V_pk_V_at_460V_35nH"], 0) + " V (" + fmt(100 * s["fault_turn_off"]["utilisation"], 0) + " %)", ""],
        ["Dead time: raw requirement skew+PWD+td(off)+t_f-td(on); x1.5; adopted minimum", fmt(dt["raw_requirement_ns"], 0) + "; " + fmt(dt["minimum_with_1p5_margin_ns"], 0) + "; " + fmt(dt["minimum_adopted_ns"], 0), "ns"],
        ["Programmed 300 ns = ticks at 6.667 ns; effective after 35 ns erosion; target; upper bound", fmt(dt["programmed_ticks"], 0) + "; " + fmt(dt["effective_after_erosion_ns"], 0) + "; " + fmt(dt["effective_target_ns"], 0) + "; " + fmt(dt["upper_bound_ns"], 0), "ns"],
        ["TBPRD (up-down, 150 MHz) / duty resolution", fmt(dt["TBPRD_up_down"], 0) + " / " + fmt(dt["duty_resolution_pct"], 3) + " %", ""],
    ]
    L += table(["Quantity", "Value", "Unit"], rows)
    A(s["withstand_note"] + ".")
    A("")

    # 6 inductor
    ind = d["inductor"]
    A("## 6. Inductor (2 x Magnetics 0058192A2 High Flux 60u, 34 T AWG 10)")
    A("")
    A("H[Oe] = 0.4 pi N I/le[cm]; %u = 1/(0.01 + 6.413e-8 H^2.291); L = n AL N^2 %u/100 (nominal AL; AL -8 %; AL -8 % with the datasheet-minimum curve interpolated between 80 % at 90 Oe and 50 % at 170 Oe; "
      "the baseline hand-off uses a flat 80 % minimum at 25 A). dB = Vout(1-D)/(N n Ae fs); Pv = 246.54 B_pk^2.218 f^1.311 mW/cm3; P_core = Pv Ve x 1.10 (x1.44 datasheet maximum, x1.2-1.3 DC-bias allowance); "
      "R_dc = rho(100 degC) N MLT/A_w; P_ac = 1.02 F_R R_dc dI^2/12 (Dowell single layer); dT = (P_mW/161 cm2)^0.833 (still air, average surface); B_dc from the catalogue magnetisation fit.")
    A("")
    L += table(["I / A", "H / Oe", "%u fit", "L nominal / uH", "L AL-8% / uH", "L AL+8% / uH", "L worst (min curve) / uH", "L worst (flat 80 %) / uH"],
               [[k, fmt(v["H_Oe"], 1), fmt(v["pct_mu"], 1), fmt(v["L_uH_nominal"], 0), fmt(v["L_uH_AL_minus8"], 0), fmt(v["L_uH_AL_plus8"], 0), fmt(v["L_uH_worst_min_curve"], 0), fmt(v["L_uH_worst_flat80"], 0)] for k, v in ind["L_vs_I"].items()])
    rows = []
    for c, cm, cb in zip(ind["corners_typical_core"], ind["corners_datasheet_max_core"], ind["corners_bounded_core"]):
        rows.append([c["corner"], fmt(c["dB_mT"], 0), fmt(c["B_pk_ac_mT"], 0), fmt(c["Pv_mW_cm3"], 0), fmt(c["P_core_W"], 1), fmt(cm["P_core_W"], 1), fmt(cb["P_core_W"], 1), fmt(c["P_cu_dc_W"], 1), fmt(c["P_cu_ac_W"], 2),
                     fmt(c["P_total_W"], 1), fmt(cm["P_total_W"], 1), fmt(cb["P_total_W"], 1), fmt(c["B_total_at_peak_T"], 2)])
    L += table(["Corner", "dB / mT", "B_pk,ac / mT", "Pv typ / mW/cm3", "P_core typ / W", "P_core x1.44 / W", "P_core x1.44x1.3 / W", "P_cu,dc / W", "P_cu,ac / W", "P_tot typ / W", "P_tot x1.44 / W", "P_tot bounded / W", "B_dc+B_ac at I_pk / T"], rows)
    cu = ind["copper"]
    th = ind["thermal"]
    sat = ind["saturation"]
    rows = [
        ["R_dc 20 / 100 degC", fmt(cu["R_dc_20C_mohm"], 1) + " / " + fmt(cu["R_dc_100C_mohm"], 1), "mohm", cu["lead_allowance_note"]],
        ["Skin depth / d/delta / F_R", fmt(cu["skin_depth_mm"], 3) + " mm / " + fmt(cu["d_over_delta"], 1) + " / " + fmt(cu["F_R"], 1), "", "AC rms current is only dI/sqrt(12), so P_ac < 0.6 W"],
        ["Average surface rise 440 V/25 A; overload; bounded core", fmt(th["surface_rise_K_440V_25A"], 0) + "; " + fmt(th["surface_rise_K_overload"], 0) + "; " + fmt(th["surface_rise_K_bounded_range"][0], 0) + "-" + fmt(th["surface_rise_K_bounded_range"][1], 0), "K", "still-air correlation, +/-30 %; forced air not credited"],
        ["Hot spot in still air at 50 degC ambient (+10-15 K internal allowance): typical / overload; bounded core", fmt(th["hot_spot_C_typ_overload"][0], 0) + "-" + fmt(th["hot_spot_C_typ_overload"][1], 0) + "; " + fmt(th["hot_spot_C_bounded"][0], 0) + "-" + fmt(th["hot_spot_C_bounded"][1], 0), "degC", "forced air over the inductor REQUIRED (CR-14); acceptance thermocouple <= " + fmt(th["acceptance_thermocouple_C"], 0) + " degC at the ID winding; 3-stack fallback"],
        ["P_max at 125 degC hot spot; margin over overload / bounded loss", fmt(th["P_max_W_at_125C_hot_spot"], 1) + " W; " + fmt(th["margin_over_overload_loss"]) + "x / " + fmt(th["margin_over_bounded_loss"]) + "x", "", "KR-TH-001 by analogy"],
        ["L(41 A)/L(25 A) nominal / worst (min curve) / worst (flat 80 % hand-off)", fmt(sat["L41_over_L25_nominal"], 3) + " / " + fmt(sat["L41_over_L25_worst_min_curve"], 3) + " / " + fmt(sat["L41_over_L25_worst_flat80_handoff"], 3), "", "criterion >= 0.70 (baseline definition for the soft-saturating powder core)"],
        ["B_dc(41 A) + B_ac,pk(440 V)", fmt(sat["B_dc_41A_T"], 2) + " + " + fmt(sat["B_ac_pk_440V_T"], 2) + " = " + fmt(sat["B_total_41A_T"], 2), "T", "limit 0.8 B_sat = " + fmt(sat["B_limit_T"], 1) + " T; B_dc(25 A) " + fmt(sat["B_dc_25A_T"], 2) + " T"],
        ["Vendor-style I_sat (30 % drop from L0) nominal / worst", fmt(sat["I_sat_30pct_drop_from_L0_A_nominal"], 1) + " / " + fmt(sat["I_sat_30pct_drop_from_L0_A_worst"], 1), "A", "below the 41 A margin current and the 42.6 A worst trip corner: reported alongside, met only under the ratio definition (CR-05, human review)"],
        ["Current at 70 % of L(25 A) / at 50 % of L0", fmt(sat["I_at_70pct_of_L25_A"], 1) + " / " + fmt(sat["I_at_50pct_of_L0_A"], 1), "A", ""],
        ["No-load CCM reverse current (360/400/440 V)", " / ".join(fmt(v, 1) for v in ind["no_load_ccm_reverse_current_A"]), "A", "informational hand-off (TMCS1133 linear range -4.6 A)"],
        ["Load-transient slew (Vin - Vout)/L (360/400/440 V)", " / ".join(fmt(v, 2) for v in ind["load_transient_slew_A_per_us"]), "A/us", "12.5 A step in 14-21 us << loop response"],
    ]
    L += table(["Quantity", "Value", "Unit", "Remark"], rows)

    # 7 capacitors
    cin, cout, blr = d["capacitors"]["input"], d["capacitors"]["output"], d["capacitors"]["bleeders"]
    A("## 7. Capacitors")
    A("")
    A("Input (KR-CAP-001/002/003): dQ = D(1-D) Io Ts (exact because Io - dI/2 > D Io at every corner); C_in >= dQ_max/dV (dV = 2 % of 400 V); realised ripple dV = dQ/C_min + ESR_bank I_C,pp with I_C,pp = Io + dI/2 (verifier-corrected); "
      "per-part I = I_Cin,rms/2, P = I^2 ESR, R_th = 20 K/(14.5^2 x 7.5 mohm), dT = P R_th. HF tier: C_eff = 10 x 0.47 uF x 40 %; f_r = 1/(2 pi sqrt(L_int C_eff)); Z0 = sqrt(L_int/C_eff); dip = I_pk T/4 / C_eff (conservative) or I_pk Z0 (exact step). "
      "Ring (verifier addition): E = 0.5 L_int (I_off^2 + I_on^2) per period, P = E fs independent of Q; ring RMS from tau = 2 L_int/R_loop.")
    A("")
    L += table(["Corner", "dQ / uC", "exact", "I_Cin,rms / A", "I_C,pp / A"], [[r["corner"], fmt(r["dQ_uC"], 1), r["exact"], fmt(r["iCin_rms_A"]), fmt(r["iCin_pp_A"], 1)] for r in cin["rows"]])
    f = cin["film"]
    hf = cin["hf_tier"]
    rows = [
        ["dQ_max; C_in required (min / nominal at -10 %)", fmt(cin["dQ_max_uC"], 1) + " uC; " + fmt(cin["C_in_required_uF"], 1) + " / " + fmt(cin["C_in_required_nominal_uF"], 1) + " uF", "fitted 2 x 20 uF = " + fmt(cin["C_in_nominal_uF"], 0) + " uF nominal, " + fmt(cin["C_in_min_uF"], 0) + " uF minimum"],
        ["Realised input ripple 27.5 A / 25 A", fmt(cin["ripple_Vpp_27p5A"]) + " Vpp (" + fmt(cin["ripple_pct_27p5A"]) + " %) / " + fmt(cin["ripple_Vpp_25A"]) + " Vpp", "limit 8 Vpp (2 %)"],
        ["Film RMS each / rating / margin", fmt(f["I_rms_each_A_worst"]) + " / " + fmt(f["rating_A"], 1) + " A / " + fmt(f["margin"]) + "x", "TDK rating basis 70 degC, 10 kHz, dT 20 K"],
        ["Film self-heating: P each, R_th, dT; with ring share", fmt(f["P_each_W"]) + " W, " + fmt(f["R_th_K_per_W"], 1) + " K/W, " + fmt(f["dT_self_K"], 1) + " K; " + fmt(f["dT_with_ring_K"], 1) + " K", "hotspot " + fmt(f["hotspot_C"], 0) + " degC with +10 K local air (V_op,85 700 V applies up to 85 degC)"],
        ["Voltage ratio 440 / 460 / 480 V of 800 V", " / ".join(fmt(v, 3) for v in f["voltage_ratio_440_460_480"]), ""],
        ["HF tier C_nominal / C_eff at 440 V / requirement", fmt(hf["C_nominal_uF"], 1) + " / " + fmt(hf["C_effective_uF_at_440V"]) + " / " + fmt(hf["requirement_uF"], 1) + " uF", "DC-bias loss 60 % assumed (unverified); 630 V ratio 0.70 / 0.76"],
        ["50 kHz share of the ceramics / per MLCC", fmt(hf["fifty_kHz_share_A"]) + " A / " + fmt(hf["per_MLCC_50kHz_mA"], 0) + " mA", ""],
        ["Stored input energy at 440 V (44 uF)", fmt(cin["stored_energy_J_440V"], 1) + " J", "precharge / fault energy"],
    ]
    L += table(["Quantity", "Value", "Remark"], rows)
    L += table(["L_int / nH", "f_r / kHz", "Z0 / ohm", "T/4 / ns", "dQ / uC", "dip T/4 / V", "dip I Z0 / V", "dip / % of 440 V", "ring energy / uJ", "ring loss / W", "ring RMS total / A", "ring RMS per MLCC / A", "Q"],
               [[fmt(r["L_int_nH"], 0), fmt(r["f_r_kHz"], 0), fmt(r["Z0_ohm"], 3), fmt(r["quarter_period_ns"], 0), fmt(r["dQ_uC"], 1), fmt(r["dip_V_quarter_period"], 1), fmt(r["dip_V_exact_IZ0"], 1), fmt(r["dip_pct_of_440V"], 1),
                 fmt(r["ring_energy_uJ_per_period"], 1), fmt(r["ring_loss_W"]), fmt(r["ring_rms_A_total_range"][0], 1) + "-" + fmt(r["ring_rms_A_total_range"][1], 1), fmt(r["ring_rms_A_per_MLCC_range"][0]) + "-" + fmt(r["ring_rms_A_per_MLCC_range"][1]),
                 fmt(r["Q_range"][0], 0) + "-" + fmt(r["Q_range"][1], 0)] for r in hf["by_interconnect"]])
    A("Output (2 x 60 uF 450 V, C_min " + fmt(cout["C_min_uF"], 0) + " uF, ESR_bank " + fmt(cout["ESR_bank_mohm"], 1) + " mohm): dV_ripple = dI/(8 fs C_min) + ESR dI; dV_step = dI/(2 pi fc C_min) + ESR dI; LI^2 floor dV = sqrt(V^2 + L I_pk^2/C) - V.")
    A("")
    rows = [
        ["Output ripple with the real choke worst dI / with the 220 uH bound", fmt(cout["ripple_Vpp_worst_real_choke"]) + " / " + fmt(cout["ripple_Vpp_220uH_bound"]) + " Vpp", "limit 2.0 Vpp; C required for 2 Vpp only " + fmt(cout["C_required_for_2Vpp_uF"], 1) + " uF"],
        ["I_Cout,rms total / each / rating / margin", fmt(cout["I_rms_total_A"]) + " / " + fmt(cout["I_rms_each_A"]) + " / " + fmt(cout["rating_A"], 1) + " A / " + fmt(cout["margin"], 0) + "x", "P each " + fmt(cout["P_each_W"], 3) + " W"],
    ]
    for r in cout["transients"]:
        rows.append([f"fc {r['fc_Hz']:.0f} Hz: 12.5 A step / 25 A dump / 27.5 A dump; C for 10 V", fmt(r["step_12p5A_V"], 1) + " / " + fmt(r["dump_25A_V"], 1) + " / " + fmt(r["dump_27p5A_V"], 1) + " V; " + fmt(r["C_required_for_10V_uF"], 0) + " uF", "step limit 10 V"])
    rows.append(["Load-dump peak vs 230 V OVP: 25 A at 2.0 / 2.5 kHz; 27.5 A at 2.0 kHz", fmt(cout["load_dump_peak_V_fc2kHz"], 1) + " / " + fmt(cout["load_dump_peak_V_fc2p5kHz"], 1) + " V; " + fmt(cout["load_dump_27p5A_peak_V_fc2kHz"], 1) + " V", "all below the 230 V trip (CR-04)"])
    rows.append(["LI^2 energy floor (I_pk 29 A into 108 uF)", "+" + fmt(cout["LI2_energy_excursion_V"], 1) + " V", "controller bandwidth dominates"])
    rows.append(["LC corner; voltage ratios 200 / 220 / 440 V (HS-short fault) of 450 V", fmt(cout["lc_corner_Hz"], 0) + " Hz; " + " / ".join(fmt(v, 2) for v in cout["voltage_ratio_200_220_440fault"]), "fault survivable within V_op,85 = 450 V"])
    L += table(["Quantity", "Value", "Remark"], rows)
    A("Bleeders (CR-03, merged networks): R_in = 360 k || 450 k = " + fmt(blr["R_in_merged_kohm"], 0) + " k, R_out = 200 k || 200 k = " + fmt(blr["R_out_merged_kohm"], 0) + " k; two-bank model with ideal-diode coupling when V_out > V_in + 0.7 V; C_in 48.7 uF, C_out 132 uF.")
    A("")
    dm, dm4, dbo, dbo4 = blr["discharge_merged_from_460_200V"], blr["discharge_merged_from_480_220V"], blr["discharge_bleeders_only_from_460_200V"], blr["discharge_bleeders_only_from_480_220V"]
    sb = blr["standby_W_at_440V_200V"]
    es = blr["element_stress"]
    rows = [
        ["Discharge to 60 V, merged networks, from 460/200 V and 480/220 V", fmt(dm["time_to_both_below_60V_s"], 1) + " s / " + fmt(dm4["time_to_both_below_60V_s"], 1) + " s", "coupling acted above 60 V: " + fmt(dm["coupling_acted_above_60V"]) + "; limit 60 s with IEC 60417-5036 label"],
        ["Discharge to 60 V, bleeder chains only (indicator chains absent)", fmt(dbo["time_to_both_below_60V_s"], 1) + " s / " + fmt(dbo4["time_to_both_below_60V_s"], 1) + " s", "the baseline 'about 30 s' is the nominal-C bleeder-only estimate"],
        ["Standby dissipation at 440 V / 200 V: input (bleeder + indicator) / output / total", fmt(sb["input_total"]) + " (" + fmt(sb["input_bleeder"]) + " + " + fmt(sb["input_indicator"]) + ") / " + fmt(sb["output_total"]) + " / " + fmt(sb["total"]) + " W", "at 400 V: " + fmt(blr["standby_W_at_400V_200V_total"]) + " W total"],
        ["Input 2512 element at 440 / 480 V", fmt(es["input_bleeder_2512_at_440V"]["V_per_element_V"], 0) + " V, " + fmt(es["input_bleeder_2512_at_440V"]["P_per_element_W"]) + " W / " + fmt(es["input_bleeder_2512_at_480V"]["V_per_element_V"], 0) + " V, " + fmt(es["input_bleeder_2512_at_480V"]["P_per_element_W"]) + " W", "limits 500 V / 1 W"],
        ["Input 1206 indicator element at 440 / 480 V", fmt(es["input_indicator_1206_at_440V"]["V_per_element_V"], 0) + " V, " + fmt(es["input_indicator_1206_at_440V"]["P_per_element_W"]) + " W / " + fmt(es["input_indicator_1206_at_480V"]["V_per_element_V"], 0) + " V, " + fmt(es["input_indicator_1206_at_480V"]["P_per_element_W"]) + " W", "assumed 1206 limits 200 V / 0.25 W; LED " + fmt(blr["indicator_LED_current_mA_at_440V"], 2) + " mA"],
        ["Output 2512 element at 200 V / under a 440 V HS-short fault", fmt(es["output_bleeder_2512_at_200V"]["V_per_element_V"], 0) + " V, " + fmt(es["output_bleeder_2512_at_200V"]["P_per_element_W"]) + " W / " + fmt(es["output_bleeder_2512_at_440V_HS_short_fault"]["V_per_element_V"], 0) + " V, " + fmt(es["output_bleeder_2512_at_440V_HS_short_fault"]["P_per_element_W"]) + " W", "within 500 V / 1 W"],
        ["Output 1206 indicator element at 200 V / under a 440 V HS-short fault", fmt(es["output_indicator_1206_at_200V"]["V_per_element_V"], 0) + " V, " + fmt(es["output_indicator_1206_at_200V"]["P_per_element_W"]) + " W / " + fmt(es["output_indicator_1206_at_440V_HS_short_fault"]["V_per_element_V"], 0) + " V, " + fmt(es["output_indicator_1206_at_440V_HS_short_fault"]["P_per_element_W"]) + " W", "fault case exceeds typical 1206 ratings - human review (>= 3 elements or 2512)"],
        ["5 s option: R <= t/(C ln(V0/60)) at nominal C (40/120 uF) / effective C (48.7/132 uF)", fmt(blr["option_5s"]["R_in_kohm_nominal_C"], 0) + " / " + fmt(blr["option_5s"]["R_out_kohm_nominal_C"], 0) + " k; " + fmt(blr["option_5s"]["R_in_kohm_effective_C"], 0) + " / " + fmt(blr["option_5s"]["R_out_kohm_effective_C"], 0) + " k", "baseline 60 k / 32 k: " + fmt(blr["option_5s"]["P_W_at_440V_200V_baseline"], 1) + " W at 440/200 V (" + fmt(blr["option_5s"]["P_W_at_440V_220V_baseline"], 1) + " W at 220 V); " + fmt(blr["option_5s"]["time_s_baseline_R_effective_C"], 1) + " s with the effective capacitance"],
    ]
    L += table(["Quantity", "Value", "Remark"], rows)

    # 8 sensing
    sn = d["sensing"]
    t = sn["tmcs1133"]
    A("## 8. Sensing and protection thresholds")
    A("")
    A("TMCS1133C2A: V = 0.33 V + 0.050 V/A x I; LSB = 3 V/4096 = " + fmt(t["LSB_mV"], 3) + " mV = " + fmt(t["LSB_mA"]) + " mA; full scale " + fmt(t["full_scale_A"], 1) + " A. OC: V_OC = S I_OC/2.5 from 2.5 V through 2.32 k / 1.00 k loaded by the 120 k pin; "
      "trip chain t = t_OC,max + t_latch + RST/EN deglitch,max + tPD,max + gate fall = " + " + ".join(f"{fmt(v, 1)}" for v in t["trip_chain"]["terms_ns"].values()) + " ns; overshoot dI = (440 V / L_worst) t.")
    A("")
    L += table(["I / A", "V_out / V", "ADC code"], [[fmt(r["I_A"], 2), fmt(r["V_out_V"], 3), r["code"]] for r in t["table"]])
    oc = t["OC"]
    tc = t["trip_chain"]
    rows = [
        ["V_OC unloaded / loaded; I_OC", fmt(oc["V_OC_unloaded_V"], 4) + " / " + fmt(oc["V_OC_loaded_V"], 4) + " V; " + fmt(oc["I_OC_A"], 1) + " A", "hysteresis " + fmt(oc["hysteresis_A"], 1) + " A"],
        ["Trip band +/-2 % typ / +/-10 % max", fmt(oc["band_A_typ"][0], 1) + "-" + fmt(oc["band_A_typ"][1], 1) + " / " + fmt(oc["band_A_max"][0], 1) + "-" + fmt(oc["band_A_max"][1], 1) + " A", "margin low bound to the 32.0 A worst overload peak " + fmt(oc["margin_A_overload_peak_to_low_bound"], 1) + " A"],
        ["Trip chain / di/dt at 440 V with L " + fmt(tc["L_worst_uH"], 0) + " uH / overshoot", fmt(tc["t_ns"], 0) + " ns / " + fmt(tc["di_dt_A_per_us"]) + " A/us / " + fmt(tc["overshoot_A"]) + " A", "worst peak " + fmt(tc["worst_peak_A"], 1) + " A (typ " + fmt(tc["typ_peak_A"], 1) + " A); nominal L there " + fmt(tc["L_at_worst_peak_uH_nominal"], 0) + " uH (soft roll-off, CR-05)"],
        ["Output short: ramp 28.75 -> 37.5 A", "; ".join(f"{k} {fmt(v, 1)} us" for k, v in t["output_short_ramp_to_trip_us"].items()), "inside one 20 us period -> hardware path mandatory (KR-SN-005)"],
        ["Conductor loss 25 / 27.5 A", fmt(t["conductor_loss_W"]["25A"]) + " / " + fmt(t["conductor_loss_W"]["27.5A"]) + " W", "0.7 mohm; 80 Arms rating at 25 degC (44 Arms at 125 degC)"],
        ["No-load valley vs linear range", fmt(t["no_load_valley_A"], 1) + " A vs " + fmt(t["linear_range_low_A"], 1) + " A", ""],
    ]
    L += table(["Quantity", "Value", "Remark"], rows)
    for name, lad, label in (("Vin", sn["ladder_vin"], "4 x 750 k + 10.0 k"), ("Vout", sn["ladder_vout"], "2 x 750 k + 10.0 k")):
        A(f"{name} ladder {label}: k = " + fmt(lad["k"], 6) + "; AMC1311 full scale " + fmt(lad["full_scale_V"], 0) + " V = ADC 3.0 V; LSB " + fmt(lad["LSB_V"] * 1e3, 1) + " mV of bus voltage; headroom at the maximum " + fmt(lad["headroom_at_max_pct"], 0) + " % of 2 V.")
        A("")
        L += table(["V / V", "AMC input / V", "ADC / V", "code", "V per resistor / V", "P per resistor / mW", "divider current / uA"],
                   [[fmt(r["V"], 0), fmt(r["V_AMC_V"], 3), fmt(r["V_ADC_V"], 3), r["code"], fmt(r["V_per_resistor_V"], 1), fmt(r["P_per_resistor_mW"], 1), fmt(r["I_divider_uA"], 0)] for r in lad["rows"]])
    c = sn["comparators"]
    A("Comparators from REF3125 2.5 V (V_th = 2.5 R_b/(R_t+R_b)); UVLO hysteresis from the 0/3.3 V open-collector output through 21.5 k; OTP ratiometric to the 3.00 V NTC reference (NTC 10 k, B 3984 K, 2.2 k pull-up): V = 3.00 R_NTC/(2.2 k + R_NTC).")
    A("")
    rows = [
        ["OVP_in 1.00 k / 11.0 k", fmt(c["OVP_in"]["V_th_V"], 4) + " V -> " + fmt(c["OVP_in"]["bus_V"], 1) + " V", "target 460 V"],
        ["OVP_out 953 / 10.0 k", fmt(c["OVP_out"]["V_th_V"], 4) + " V -> " + fmt(c["OVP_out"]["output_V"], 1) + " V", "target 230 V (CR-04)"],
        ["UVLO 1.00 k / 1.91 k centre; on / off with 21.5 k", fmt(c["UVLO"]["V_centre_V"], 4) + " V -> " + fmt(c["UVLO"]["bus_centre_V"], 1) + " V; " + fmt(c["UVLO"]["on_V"], 1) + " / " + fmt(c["UVLO"]["off_V"], 1) + " V", "targets 340 / 320 V; " + c["UVLO"]["note"]],
        ["OTP voltages warn 90 / firmware 100 / hardware 110 degC", " / ".join(fmt(v, 3) for v in c["OTP_threshold_voltages_V"].values()) + " V", "sensitivity " + fmt(c["NTC_sensitivity_mV_per_K_90_100"], 1) + " mV/K; self-heating " + fmt(c["NTC_self_heating_K_at_110C"], 2) + " K"],
        ["Hardware OTP divider proposal 10.0 k / 2.37 k from 3.00 V", fmt(c["OTP_hardware_divider_proposal"]["V_th_V"], 4) + " V -> " + fmt(c["OTP_hardware_divider_proposal"]["trip_C"], 1) + " degC", "proposal, KR-TH-003 human review"],
    ]
    L += table(["Threshold", "Value", "Remark"], rows)
    L += table(["T / degC", "R_NTC / ohm", "V readout / V"], [[r["T_C"], fmt(r["R_ohm"], 0), fmt(r["V_V"], 3)] for r in c["NTC_table"]])

    # 9 thermal
    th = d["thermal"]
    A("## 9. Thermal")
    A("")
    A(th["model"] + ". Device losses from section 3 (HS incl. E_oss, LS with V_SD(I), 250 ns). Spreading allowance 0.2 K/W per device and the 10.8 V fan case (+6 % R_th) are shown as sensitivities.")
    A("")
    rows = []
    for r in th["corners"]:
        if (r["k_RG"] == 1.3) or (r["k_RG"] == 2.0 and r["R_variant"] == "max"):
            rows.append([r["corner"], r["R_variant"], r["k_RG"], fmt(r["P_HS_W"], 1), fmt(r["P_LS_W"], 1), fmt(r["P_total_W"], 1), fmt(r["T_sink_C"], 1), fmt(r["T_J_HS_C"], 1), fmt(r["T_J_LS_C"], 1), fmt(r["T_J_HS_with_spreading_C"], 1), fmt(r["T_J_HS_fan_10p8V_C"], 1)])
    L += table(["Corner", "R", "k_RG", "P_HS / W", "P_LS / W", "P_total / W", "T_sink / degC", "T_J,HS / degC", "T_J,LS / degC", "T_J,HS +0.2 K/W spreading", "T_J,HS fan at 10.8 V"], rows)
    ex = th["expected_400V_25A_100C"]
    A("Expected operating point 400 V / 25 A with R_DS(on)(100 degC): P_HS " + fmt(ex["P_HS_W"], 1) + " W, P_LS " + fmt(ex["P_LS_W"], 1) + " W, T_sink " + fmt(ex["T_sink_C"], 1) + " degC, T_J,HS " + fmt(ex["T_J_HS_C"], 1) + " degC. "
      "Hottest HS corner: " + th["hottest_HS_corner"]["corner"] + " (" + th["hottest_HS_corner"]["R_variant"] + " R, k_RG " + fmt(th["hottest_HS_corner"]["k_RG"], 1) + ") at " + fmt(th["hottest_HS_corner"]["T_J_HS_C"], 1) + " degC. "
      "KR-TH-001: P_max = (150 - 50)/(2 x 0.30 + 1.4 + 0.41) = " + fmt(th["P_max_W"]["150C"], 1) + " W per device (" + fmt(th["P_max_W"]["125C"], 1) + " W for 125 degC); margin over the hottest HS loss at k_RG 1.3 / max R (" + fmt(th["hottest_HS_corner_k1p3_maxR"]["P_HS_W"], 1) + " W) = " + fmt(th["P_max_margin_over_hottest_HS_k1p3_maxR"]) + "x.")
    A("")
    A("Fan failure (natural convection; R_nat and mass of the D K unit unverified): T_ss = 50 + P R_nat; tau = m c_p R_nat; time from the 68-70 degC steady state to the 100 degC firmware trip t = -tau ln(1 - (100 - T_0)/(T_ss - T_0)):")
    A("")
    L += table(["R_nat / K/W", "mass / kg", "T_sink,ss / degC", "T_J,HS,ss / degC", "tau / s", "initial slope / K/s", "time to 100 degC / s"],
               [[fmt(r["R_nat_K_per_W"], 2), fmt(r["mass_kg"], 1), fmt(r["T_sink_ss_C"], 0), fmt(r["T_J_HS_ss_C"], 0), fmt(r["tau_s"], 0), fmt(r["initial_slope_K_per_s"], 3), fmt(r["time_to_100C_trip_s"], 0)] for r in th["fan_failure"]])
    off = th["ntc_to_TJ_offset_K"]
    A("NTC-to-T_J offset = spreading (4-6 K) + P_HS (R_pad + R_JC): typical 440 V / 27.5 A " + fmt(off["typ_440V_27p5A"], 0) + " K; max-R 360 V / 27.5 A " + fmt(off["maxR_360V_27p5A"], 0) + " K. " + off["note"] + ".")
    A("")
    cu = th["copper"]
    A("Copper (IPC-2221 formula, 70 um = 2.756 mil, k 0.048 external / 0.024 internal): A[mil2] = (I/(k dT^0.44))^(1/0.725), w = A/t. Vias: barrel area pi (d + t) t with 25 um plating, I = 0.024 dT^0.44 A^0.725 at 20 K.")
    A("")
    L += table(["I / A", "dT / K", "external width / mm", "internal width / mm"], [[fmt(r["I_A"], 1), fmt(r["dT_K"], 0), fmt(r["width_external_mm"], 1), fmt(r["width_internal_mm"], 1)] for r in cu["ipc_widths"]])
    L += table(["Drill / mm", "I per via / A", "minimum count 25 A", "baseline count", "baseline margin", "R per via (2.0 mm board) / mohm", "P at 25 A with baseline count / W"],
               [[fmt(r["drill_mm"], 1), fmt(r["I_per_via_A_20K"]), fmt(r["minimum_count_25A"], 1), r["baseline_count"], fmt(r["baseline_margin"]), fmt(r["R_per_via_mohm_2mm_board"]), fmt(r["P_W_baseline_count_25A"], 3)] for r in cu["vias"]])
    pl = cu["path_loss"]
    A("Power path " + fmt(pl["width_mm"], 0) + " mm x 70 um at 100 degC: " + fmt(pl["R_mohm_per_cm"], 3) + " mohm/cm, " + fmt(pl["P_W_per_cm_25A"], 3) + " W/cm at 25 A, " + fmt(pl["P_W_total_25A"], 1) + " W for " + fmt(pl["length_cm"], 0) + " cm (" + fmt(pl["P_W_total_27p5A"], 1) + " W at 27.5 A).")
    A("")

    # 10 aux
    ax = d["aux_12V"]
    A("## 10. Auxiliary 12 V, eFuse, supervisor, relay, mezzanine")
    A("")
    A("TPS26400 MODE open = circuit breaker: I_CB = 12/R_ILIM - 0.03 A (SLVSFQ6A Eq. 4), 4 ms timeout, 540 ms retry; budget per CR-02 at 10.8 V; dVdT slew = 24.6 I_dVdT/C; UVLO/OVP ladder 107 k / 4.42 k / 10.0 k; TPS3808G01 V_trip = 0.405 V (R_top + R_bot)/R_bot.")
    A("")
    rows = [
        ["I_CB typical / assumed -10 % minimum / +9 % maximum", fmt(ax["I_CB_A_typ"], 3) + " / " + fmt(ax["I_CB_A_min_assumed"], 2) + " / " + fmt(ax["I_CB_A_max_assumed"], 2), "A", "R_ILIM 6.04 k"],
        ["Budget at 10.8 V (CR-02)", ", ".join(f"{k} {fmt(v, 2)}" for k, v in ax["budget_A_at_10p8V"].items()), "A", "gate-bias figure carries the controller agent's 250 nC bound and 20 % margin"],
        ["Total during relay pull-in / steady with PWM hold / pull-in without fan", fmt(ax["total_pull_in_A"], 2) + " / " + fmt(ax["total_steady_A"], 2) + " / " + fmt(ax["total_pull_in_without_fan_A"], 2), "A", ""],
        ["Margin to I_CB typ: pull-in / steady", fmt(ax["margin_pull_in"]) + "x / " + fmt(ax["margin_steady"]) + "x", "", "to the assumed minimum: " + fmt(ax["margin_pull_in_vs_I_CB_min"]) + "x / " + fmt(ax["margin_steady_vs_I_CB_min"]) + "x (human review: stagger fan and relay or fan upstream)"],
        ["Bottom-up bias current (three modules, +20 %) at 10.8 V", fmt(ax["bottom_up_bias_A_at_10p8V"], 2), "A", "baseline budget 0.55 A is conservative"],
        ["dVdT slew min/typ/max; ramp at 12 V; charging current into " + fmt(ax["dVdT"]["C_downstream_uF"], 0) + " uF", " / ".join(fmt(v, 2) for v in ax["dVdT"]["slew_V_per_ms_min_typ_max"]) + " V/ms; " + fmt(ax["dVdT"]["ramp_ms_at_12V"][0], 1) + "-" + fmt(ax["dVdT"]["ramp_ms_at_12V"][2], 1) + " ms; " + fmt(ax["dVdT"]["charging_current_A"][0]) + "-" + fmt(ax["dVdT"]["charging_current_A"][2]) + " A", "", "baseline 8.9-12.2 ms"],
        ["eFuse UVLO rising / falling; OVP rising / falling", fmt(ax["ladder"]["UVLO_rising_V"]) + " / " + fmt(ax["ladder"]["UVLO_falling_V"]) + "; " + fmt(ax["ladder"]["OVP_rising_V"]) + " / " + fmt(ax["ladder"]["OVP_falling_V"]), "V", "ladder current " + fmt(ax["ladder"]["I_ladder_uA_12V"], 0) + " uA"],
        ["IMON: V at 2.4 A (max gain) / at the 1.59 A steady load (typ gain); resolution", fmt(ax["IMON"]["V_at_2p4A_max_gain_V"]) + " / " + fmt(ax["IMON"]["V_at_1p59A_typ_V"]) + " V; " + fmt(ax["IMON"]["mA_per_LSB"], 2) + " mA/LSB", "", ""],
        ["TPS3808G01 trip with 101 k / release; with 105 k", fmt(ax["TPS3808"]["V_trip_V_101k"], 3) + " / " + fmt(ax["TPS3808"]["V_release_V_101k"], 3) + " V; " + fmt(ax["TPS3808"]["V_trip_V_105k"], 2) + " V", "", "power-down margin " + fmt(ax["TPS3808"]["power_down_margin_ms"]) + " ms >> 8 us"],
        ["Dual LDO dissipation (1.9 V 0.35 A, 3.3 V 0.179 A from 5 V); control-board input power", fmt(ax["LDO"]["P_W"]) + " W; " + fmt(ax["LDO"]["P_in_control_W"]) + " W", "", ""],
        ["Relay coil 10.8 / 12 / 13.2 V; PWM hold 50-60 % at 10.8 V; coil power at 12 V", " / ".join(fmt(v, 3) for v in ax["relay_coil_A"].values()) + " A; " + fmt(ax["relay_hold_A_at_10p8V"][0]) + "-" + fmt(ax["relay_hold_A_at_10p8V"][1]) + " A; " + fmt(ax["relay_coil_P_W_12V"], 1) + " W", "", "contact loss " + fmt(ax["relay_contact_loss_W"]["25A"]) + " W at 25 A (0.6 mohm typ)"],
        ["Mezzanine +12V_PROT on 3 pins (bias, relay, fan on the power board): per pin pull-in / steady", fmt(ax["mezzanine"]["per_pin_A_pull_in"]) + " / " + fmt(ax["mezzanine"]["per_pin_A_steady"]), "A", "target 0.4 A/pin exceeded; ratings 3 A (WR-PHD) / 4.7 A (SSW/TSM) / 6.3 A (SSW+TSW); margin " + fmt(ax["mezzanine"]["margin_WR_PHD"], 1) + "x"],
    ]
    L += table(["Quantity", "Value", "Unit", "Remark"], rows)

    # 11 power path
    pp = d["power_path"]
    A("## 11. Power path: fuse, precharge, firmware derating")
    A("")
    fz = pp["fuse"]
    rows = [[k, fmt(100 * v, 0) + " %"] for k, v in fz["loading"].items()]
    L += table(["Fuse KLKD025.T loading (I_in at eta 0.98 / 25 A)", "Loading"], rows)
    A("Fuse I2R with the distributor cold resistance of the 20 A member (4.5 mohm): " + fmt(fz["I2R_cold_W_at_12p76A_distributor_R"]) + " W at 400 V / 25 A (unverified; melting I2t not found).")
    A("")
    L += table(["Vin / V", "I_in at 27.5 A unlimited / A", "P_out,max with 15.6 A limit / W", "I_out,max / A"],
               [[k, fmt(v["I_in_27p5A_A"]), fmt(v["P_out_max_W_at_15p6A"], 0), fmt(v["I_out_max_A_at_15p6A"], 1)] for k, v in pp["firmware_derating_below_360V"].items()])
    pr = pp["precharge"]
    A("Precharge (PTC across the relay contacts, C_in 48.7 uF): tau = R C, t99 = 4.6 tau, I_pk = V/R, I2t = C V^2/(2R); E = 0.5 C V^2 = " + fmt(pr["E_J_440V"], 2) + " J at 440 V / " + fmt(pr["E_J_480V"], 2) + " J at 480 V; relay closing voltage difference I_bleed R_PTC = " + fmt(pr["relay_closing_dV_V"], 2) + " V; relay operate time " + fmt(pr["relay_operate_time_ms"], 0) + " ms max; " + pr["closing_criterion"] + ".")
    A("")
    L += table(["PTC R / ohm", "tau / ms", "t99 / ms", "I_pk 440 V / A", "I_pk 480 V / A", "I2t 480 V / A2s"],
               [[fmt(v["R_ohm"], 0), fmt(v["tau_ms"], 1), fmt(v["t99_ms"], 0), fmt(v["I_pk_A_440V"], 1), fmt(v["I_pk_A_480V"], 1), fmt(v["I2t_A2s_480V"], 3)] for v in pr["by_R"].values()])
    A("PTC temperature rise per 480 V charge E/C_th: " + ", ".join(f"{k.replace('_', ' ')} {fmt(v, 1)} K" for k, v in pr["dT_PTC_K_480V"].items()) + ". Elements required N = C V^2/(2 C_th (T_ref - 60 degC)): " +
      ", ".join(f"{k.replace('_', ' ')} {fmt(v, 2)}" for k, v in pr["N_elements_required"].items()) + " (one element in every case; parameters of the re-selected part to be inserted).")
    A("")

    # 12 efficiency
    ef = d["efficiency"]
    A("## 12. Efficiency budget roll-up at 400 V / 25 A")
    A("")
    A("P_loss = MOSFET pair + inductor + interconnect (PCB copper 15 cm x 12 mm, TMCS1133 conductor, relay contact, fuse) + film-ceramic ring + bleeders; eta_converter = 5000/(5000 + P_loss). "
      "'With aux electronics' adds the 12 V input power of the three bias modules and the control board (+20 %), the baseline convention ('aux ~8 W'); 'system' also adds the relay PWM hold and the 0.5 A fan cap. Loss budget: " +
      fmt(ef["loss_budget_W"]["98.0 %"], 0) + " W for 98.0 %, " + fmt(ef["loss_budget_W"]["97.5 %"], 0) + " W for 97.5 %.")
    A("")
    L += table(["Item", "W"], [[k.replace("_", " "), fmt(v)] for k, v in ef["items_W"].items()])
    L += table(["Scenario", "MOSFET pair / W", "Inductor / W", "Interconnect / W", "Ring / W", "Bleeders / W", "Converter loss / W", "eta converter", "+ aux electronics / W", "eta with aux", "System loss / W", "eta system"],
               [[s["scenario"] + " (" + s["note"] + ")", fmt(s["mosfet_pair_W"], 1), fmt(s["inductor_W"], 1), fmt(s["interconnect_W"], 1), fmt(s["ring_W"]), fmt(s["bleeders_W"]), fmt(s["converter_loss_W"], 1),
                 fmt(100 * s["eta_converter_only"]) + " %", fmt(s["loss_with_aux_electronics_W"], 1), fmt(100 * s["eta_with_aux_electronics"]) + " %", fmt(s["system_loss_W"], 1), fmt(100 * s["eta_system"]) + " %"] for s in ef["scenarios"]])

    # 13 invariants
    A("## 13. Invariants asserted by the script")
    A("")
    L += table(["Check", "Expression", "Value", "Limit", "Unit", "Status", "Note"], [[i["name"], i["expression"], fmt(i["value"], 3), fmt(i["limit"], 3), i["unit"], i["status"], i["note"]] for i in d["invariants"]])

    # 14 cross-check
    A("## 14. Cross-check against the baseline figures")
    A("")
    L += table(["Item", "Computed", "Baseline", "Difference", "Tolerance", "Status", "Note"],
               [[x["item"], fmt(x["computed"], 3), fmt(x["baseline"], 3), fmt(x["difference"], 3), fmt(x["tolerance"], 3), x["status"], x["note"]] for x in d["baseline_crosscheck"]])

    # 15 knowledge
    A("## 15. Knowledge applicability")
    A("")
    L += table(["Knowledge id", "Type", "Applicability", "How it was used in these calculations"], [[k["id"], k["type"], k["applicability"], k["how_applied"]] for k in d["knowledge_applicability"]])

    # 16 limitations
    A("## 16. Limitations")
    A("")
    for x in d["limitations"]:
        A("- " + x)
    A("")

    # 17 status
    A("## Verification status and open items")
    A("")
    A("Analytically checked (this script): operating points at six corners with the real choke; MOSFET conduction, switching (k_RG 1.3-2.0), E_oss, recovery and dead-time losses with efficiency shares of 5 kW and 5.5 kW; "
      "utilisation and charge-based parasitic turn-on; gate power (both KR-IS-001 forms), peak currents, resistor pulse power, decoupling droop, bias budgets and 12 V current; DESAT trip, false-trip, blanking, response and fault overshoot; dead-time requirement; "
      "inductor L(I) (nominal, AL -8 %, minimum curve), ripple and peaks, flux, core loss (typical, datasheet-maximum, bounded), copper loss, surface rise, saturation criteria and I_sat; input dQ, C_in, ripple, film RMS and self-heating, HF tier, ring energy and current; "
      "output ripple, load step and load dump; coupled-bank discharge of the merged bleeder networks, dissipation, element stress and the 5 s option; TMCS1133 scaling, OC band and trip-chain overshoot; ladders, comparator thresholds, NTC readout; shared-sink T_J at every corner, P_max, fan-fail estimate, NTC-to-T_J offset; IPC-2221 copper and vias; "
      "aux 12 V budget vs I_CB, dVdT, eFuse ladder, IMON, TPS3808, relay, mezzanine pin current; fuse loading, firmware derating, precharge; efficiency roll-up.")
    A("")
    A("Simulated: nothing. No SPICE, thermal or electromagnetic simulation underlies this record.")
    A("")
    A("Unverified or estimated inputs: k_RG switching-energy factor (graph read, 1.3-2.0); body-diode V_SD slope and E_oss exponent; L_loop 25-60 nH and 2.5 A/ns; C_oss and C_rss at 400 V; Q_gd(0-400 V) and the 8-13 ns edge; "
      "Fischer LAM 5 D K 100 12 R_th 0.30 K/W (distributor), natural R_th, mass and fan current; pad R_th 1.4 K/W (exposed-tab area, to be measured); MLCC DC-bias (40 % remaining), interconnect 20-40 nH, loop resistance; 1206 indicator-resistor ratings; "
      "KLKD025 cold resistance and I2t; PTC parameters (re-selection pending); TPS26400 I_CB tolerance (-10 % assumed); UCC14141 C_IO legibility and SOA at 19 V / 10.8 V; TMCS1133 OC response maximum (datasheet row quoted by the verifier); Samtec/WR-PHD orderable ratings.")
    A("")
    A("Human review (not decided here): utilisation limits 80/90/70 %; KR-GD-004 DESAT values and KR-PR-001 short-circuit test; Miller-clamp necessity and off-state V_GS measurement; KR-TH-002 pad rating vs the 4 kV impulse basis (CR-13); KR-TH-003 OTP thresholds and the NTC-to-T_J offset with the 1.4 K/W pad; "
      "saturation-margin definition (ratio vs vendor I_sat, CR-05); discharge option (60 s + label vs 5 s); output indicator chain under the HS-short fault; aux budget margin against the I_CB minimum during relay pull-in; mezzanine per-pin current above the 0.4 A target; sensing-module COM-VEE sourcing and RLIM; efficiency budget with no margin at the bounded worst case.")
    A("")
    A("Open items found while reproducing the baseline:")
    A("")
    for x in d["open_items"]:
        A("- " + x)
    A("")
    return "\n".join(L)


def main() -> None:
    d = calculate()
    failed = [i for i in d["invariants"] if i["status"] != "PASS"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "calculations.json").write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    (OUT / "calculations.md").write_text(markdown(d), encoding="utf-8")
    if failed:
        for i in failed:
            print("INVARIANT FAILED:", i["name"], "-", i["expression"], "value", i["value"], "limit", i["limit"])
        raise AssertionError(f"{len(failed)} invariant(s) violated - see calculations.json")
    op400 = next(o for o in d["operating_points"] if o["vin_V"] == 400.0 and o["iout_A"] == I_OUT)
    m13 = next(r for r in d["mosfet"]["rows"] if r["corner"] == "400V/25A" and r["R_variant"] == "typ" and r["k_RG"] == 1.3)
    m20 = next(r for r in d["mosfet"]["rows"] if r["corner"] == "400V/25A" and r["R_variant"] == "typ" and r["k_RG"] == 2.0)
    summary = {
        "dIL_400V_25A_App": round(op400["dIL_App"], 2), "ipk_440V_27p5A_worst_A": round(max(o["ipk_A_AL_minus8"] for o in d["operating_points"]), 2),
        "mosfet_pair_400V_25A_150C_W_k1p3_to_k2p0": [round(m13["pair_W"], 1), round(m20["pair_W"], 1)],
        "T_J_HS_hottest_C": round(d["thermal"]["hottest_HS_corner"]["T_J_HS_C"], 1), "P_max_W": round(d["thermal"]["P_max_W"]["150C"], 1),
        "inductor_loss_400V_25A_W": round(next(c for c in d["inductor"]["corners_typical_core"] if c["corner"] == "400V/25A")["P_total_W"], 1),
        "discharge_merged_s": round(d["capacitors"]["bleeders"]["discharge_merged_from_480_220V"]["time_to_both_below_60V_s"], 1),
        "I_CB_A": round(d["aux_12V"]["I_CB_A_typ"], 3), "aux_pull_in_A": d["aux_12V"]["total_pull_in_A"],
        "eta_typical_with_aux": round(100 * d["efficiency"]["scenarios"][0]["eta_with_aux_electronics"], 2),
        "eta_bounded_worst_with_aux": round(100 * d["efficiency"]["scenarios"][-1]["eta_with_aux_electronics"], 2),
        "invariants": f"{len(d['invariants'])} passed", "crosscheck_differs": [x["item"] for x in d["baseline_crosscheck"] if x["status"] == "differs"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
