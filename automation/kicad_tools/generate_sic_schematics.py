"""Generate the two V2 KiCad projects of the 400 V -> 200 V, 5 kW SiC buck from the board models.

AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED

generate(board) for board in ("power", "control") builds the electrical model
(sic_buck_power_model / sic_buck_control_model), validates the pad -> net mapping against the
installed KiCad 10 footprint library and the model's custom footprints, runs the ERC pre-check of
project_schematic.analyse_connectivity, prepares the project footprint libraries
(project_footprints.prepare_libraries: official footprints copied with their licence notice, the
model's CUSTOM_FOOTPRINTS and envelope models written to AIPE.pretty / AIPE.3dshapes), writes the
hierarchical schematic, the symbol library, the project file with net classes and board design
rules and the .kicad_dru (project_schematic.generate_project), and records the generation summary in
design/schematic_mapping_<board>.json.  run_erc() runs native kicad-cli ERC through
automation.kicad_tools.run_check into verification/erc; export_pdf() writes the review PDFs;
write_merged_bom() merges components/bom_power.csv and bom_control.csv into components/bom.csv
with a board column.

Single source of truth: examples/sic-buck-400v-200v-5kw/design/design_decisions.json (schema 3).
Values used here and where they come from:
  net_classes (architecture.power_board.net_classes): HV_VIN, HV_SW, HV_PGND, HV_VOUT, DRV_HS,
    DRV_LS, DESAT_HS, DESAT_LS, SENSE_ISO, PE, CTRL_SELV (+ KiCad's Default).
  kicad_rules_mm (standards_and_spacing): HV/DRV/DESAT/SENSE_ISO to CTRL_SELV 9.0 mm on all layers;
    HV to PE 5.0 mm; HV functional 3.0 mm outer / 1.0 mm inner; same reference island 0.3 mm;
    CTRL_SELV 0.2 mm (control board) - the power board uses 0.25 mm per assumptions_accepted
    ("0.25 mm track/space preferred on 70 um layers"); HV to board edge 1.0 mm;
    to247_pin_field_exception: per-package rule derived from pad geometry (the pattern of
    v2_pipeline_smoke.pin_field_rules, generalised to the class-pair clearances of this design).
  Track widths and via sizes are generator defaults (not baseline values): HV and PE classes 2.0 mm
    tracks / 1.2 x 0.6 mm vias (HV current is carried by pours sized per thermal.copper), driver and
    sensing islands 0.5 / 0.3 mm tracks with 0.8 x 0.4 mm vias, SELV 0.25 mm (power) or 0.2 mm
    (control) tracks with 0.6 x 0.3 mm vias; CTRL_PWR 1.0 mm tracks for the control-board rails
    (added assumption A-G2).

Net class patterns start from sic_buck_common.NET_CLASS_PATTERNS.  Deltas (added assumption A-G1,
recorded in the mapping file as net_class_pattern_deltas): DESAT_H*/DESAT_L* move from DRV_HS/DRV_LS
into the baseline's own DESAT_HS/DESAT_LS classes; "VIN_DIV*"/"VOUT_DIV*" narrow to the AMC1311 input
nodes VIN_DIV/VOUT_DIV so that the ladder taps (up to ~360 V) join HV_VIN/HV_VOUT; the HV
intermediate nodes the power model lists in HV_INTERMEDIATE_NETS (bleeder, indicator, snubber,
damping-leg, PE-reference and ladder-tap nodes) are assigned to the HV class of their reference
potential; every remaining power-board net is listed explicitly under CTRL_SELV, so no net is left
to the Default class.  The control board carries the shared HV patterns unchanged as guards (they
must match nothing; a match is a design error and raises), CTRL_PWR for the supply rails and
CTRL_SELV for every other net.

Verification levels: everything in this module is analytically checked (deterministic text and
arithmetic); the KiCad files have no CAD evidence until kicad-cli ERC has run (verification/erc)
and the .kicad_dru is only syntax-checked here (KiCad parses it at DRC time).  Pad gaps for the
pin-field exceptions come from axis-aligned pad records (rotation ignored, true gaps are never
smaller), so the exception clearances are lower bounds that KiCad can meet.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
from pathlib import Path

from automation.kicad_tools import project_footprints as pf
from automation.kicad_tools import project_schematic as ps
from automation.kicad_tools import sic_buck_common as common
from automation.kicad_tools import sic_buck_control_model as control_model
from automation.kicad_tools import sic_buck_power_model as power_model
from automation.kicad_tools.native_schematic import children, parse
from automation.setup.detect_kicad import find_kicad_cli

BOARDS = ("power", "control")
REVISION = "V2.1"
PAPER = "A3"
# Drawing style: "wired" = V2.1 presentation layer (schematic_presentation: groups, lanes, wires, rails, ports);
# "legacy" = the V2 one-global-label-per-pin drawing.  AIPE_SCHEMATIC_STYLE overrides the default.
SCHEMATIC_STYLE = os.environ.get("AIPE_SCHEMATIC_STYLE", "wired")
STYLES = ("wired", "legacy")
# Presentation policy per board (connectivity is untouched): rails are flag nets plus power_out nets; the TPS54302
# switch node is power_out in the model but is a signal, not a rail.  Groups come from the model's Circuit.block()
# annotations (circuit.groups) and fall back to the planner's automatic grouping.
PRESENTATION = {
    "power": dict(supply="auto", exclude_supply=[]),
    "control": dict(supply="auto", exclude_supply=["5V_SW"]),
}
RELEASE_V2 = common.EXAMPLE / "releases/v2"
GATES_DIR = common.EXAMPLE / "verification/schematic_gates"
ERC_ROOT = common.EXAMPLE / "verification/erc"
REVIEW_DIR = common.EXAMPLE / "review"
DESIGN_DIR = common.EXAMPLE / "design"
BOM_CSV = common.EXAMPLE / "components/bom.csv"
BOM_SOURCES = {"power": power_model.BOM_CSV, "control": control_model.BOM_CSV}
BOM_FIELDS = ["board", "reference", "value", "manufacturer", "mpn", "footprint", "datasheet", "dnp", "note"]

# Baseline spacing (standards_and_spacing.kicad_rules_mm) in mm.
HV_TO_SELV = 9.0
HV_TO_PE = 5.0
HV_FUNCTIONAL_OUTER = 3.0
HV_FUNCTIONAL_INNER = 1.0
SAME_ISLAND = 0.3
HV_TO_EDGE = 1.0
SELV_CLEARANCE = {"power": 0.25, "control": 0.2}

HV_CLASSES = ("HV_VIN", "HV_SW", "HV_PGND", "HV_VOUT")
SW_ISLAND = ("DRV_HS", "DESAT_HS")
PGND_ISLAND = ("DRV_LS", "DESAT_LS", "SENSE_ISO", "PGND_LV")
HV_SIDE = HV_CLASSES + SW_ISLAND + PGND_ISLAND
SELV_CLASSES = ("CTRL_SELV", "CTRL_PWR", "Default")
# Reference potential of every HV-side class: pairs across groups get the HV functional clearance,
# HV_SW with its driver island and HV_PGND with its island/sensing nets the same-island clearance.
REFERENCE_GROUP = {"HV_VIN": "VIN", "HV_VOUT": "VOUT", "HV_SW": "SW", "DRV_HS": "SW", "DESAT_HS": "SW",
                   "HV_PGND": "PGND", "DRV_LS": "PGND", "DESAT_LS": "PGND", "SENSE_ISO": "PGND", "PGND_LV": "PGND"}
SAME_ISLAND_PAIRS = (("HV_SW", SW_ISLAND), ("HV_PGND", PGND_ISLAND))

HV_VIA = dict(via_diameter=1.2, via_drill=0.6)
ISLAND_VIA = dict(via_diameter=0.8, via_drill=0.4)
SELV_VIA = dict(via_diameter=0.6, via_drill=0.3)

# Power-board HV-side patterns: sic_buck_common.NET_CLASS_PATTERNS with the deltas described above.
POWER_HV_PATTERNS = {
    "HV_VIN": ["VIN_RAW", "VIN", "VIN_PRE", "BLD_IN_*", "IND_IN_1", "IND_IN_2", "DAMP_MID", "VIN_DIV_T*"],
    "HV_SW": ["SW", "SNUB_MID"],
    "HV_PGND": ["PGND", "PE_REF_MID"],
    "PGND_LV": ["IND_IN_3", "IND_OUT_2"],
    "HV_VOUT": ["VOUT", "VOUT_L", "BLD_OUT_*", "IND_OUT_1", "VOUT_DIV_T*"],
    "DRV_HS": ["HS_*", "G_H", "KS_H", "VDD_H", "VEE_H"],
    "DRV_LS": ["LS_*", "G_L", "KS_L", "VDD_L", "VEE_L"],
    "DESAT_HS": ["DESAT_H_*"],
    "DESAT_LS": ["DESAT_L_*"],
    "SENSE_ISO": ["ISO_*", "5V_ISO", "VIN_DIV", "VOUT_DIV"],
    "PE": ["PE"],
}
NET_CLASS_PATTERN_DELTAS = [
    "A-G1: DESAT_H* / DESAT_L* moved from DRV_HS / DRV_LS (sic_buck_common) into the baseline classes DESAT_HS / DESAT_LS "
    "(each net belongs to exactly one class)",
    "A-G1: SENSE_ISO patterns VIN_DIV* / VOUT_DIV* narrowed to VIN_DIV / VOUT_DIV; the ladder taps VIN_DIV_T* / VOUT_DIV_T1 "
    "(up to ~360 V) join HV_VIN / HV_VOUT",
    "A-G1: HV intermediate nodes (sic_buck_power_model.HV_INTERMEDIATE_NETS) assigned by reference potential: BLD_IN_*, IND_IN_1/2, "
    "DAMP_MID -> HV_VIN; SNUB_MID -> HV_SW; PE_REF_MID -> HV_PGND; BLD_OUT_*, IND_OUT_1 -> HV_VOUT; the LED anode nodes IND_IN_3 and "
    "IND_OUT_2 sit about 2 V above PGND and form the PGND_LV class of the PGND reference island (0.3 mm to HV_PGND, 3.0 mm to the other HV groups, 9.0 mm to SELV), so the 0805 indicator LEDs need no 3 mm spacing (DRC round 2026-10-11)",
    "A-G1: CTRL_SELV lists every remaining power-board net explicitly (no net is left to Default)",
    "A-G2: control board - CTRL_PWR (1.0 mm tracks) for 12V_IN, 12V_PROT, EFUSE_RTN, 5V, 5V_SW, 3V3, 1V9, 3V3_BULK, 1V9_BULK, GND_CTRL; "
    "CTRL_SELV for every other net; the shared HV patterns are carried as guards that must match nothing",
]
CONTROL_PWR_NETS = ["12V_IN", "12V_PROT", "EFUSE_RTN", "5V", "5V_SW", "3V3", "1V9", "3V3_BULK", "1V9_BULK", "GND_CTRL"]

NOTICE_TEXT = {
    "power": ("Project footprint library of the AIPE V2 SiC buck POWER board, generated by "
              "automation.kicad_tools.generate_sic_schematics from sic_buck_power_model.CUSTOM_FOOTPRINTS and the official KiCad 10 "
              "library. Official footprints keep their licence (LICENSE.md, CC-BY-SA-4.0.txt). Custom AIPE footprints (film capacitors, "
              "toroid, heatsink envelope, UCC14141 / AMC1311 / TMCS1133 with isolation slots, PTC envelope) are dimensioned from the "
              "sources named in the model docstring and need independent review against the manufacturer drawings; the heatsink hole "
              "pattern and the PTC are placeholders. AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED."),
    "control": ("Project footprint library of the AIPE V2 SiC buck CONTROL board, generated by "
                "automation.kicad_tools.generate_sic_schematics; every footprint is copied unchanged from the official KiCad 10 library "
                "and keeps its licence (LICENSE.md, CC-BY-SA-4.0.txt). The ASV oscillator reuses the SG8002CA land pattern (fit "
                "unverified). AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED."),
}

POWER_PAGE_NOTES = {
    "01_power_stage": ("Q1/Q2 pads 1 D, 2 S, 3 KS, 4 G follow the Wolfspeed PRD 05966 front-view lead order - ASSUMPTION, verify the "
                       "footprint pad-1 side before fabrication. HV classes: VIN_RAW/VIN (HV_VIN), SW (HV_SW), VOUT_L/VOUT (HV_VOUT), "
                       "PGND (HV_PGND) plus bleeder, indicator, ladder-tap, snubber and damping nodes. DNP: snubber, damping leg, MOV, "
                       "PGND-PE link, Y2 capacitors."),
    "02_gate_driver_hs": ("UCC21710 IN+ = PWM_H_F, IN- = PWM_L_F (hardware interlock KR-GD-009); AIN tied to COM (CR-01); APWM not connected. "
                          "UCC14141 VDD-VEE 19.0 V (107 k / 16.2 k) and COM-VEE 4.0 V (9.76 k / 16.2 k) give +15 V / -4 V at the gate; "
                          "RLIM 1 k is a placeholder (human review). Decoupling sits between the driver pins and the gate/Kelvin connection "
                          "(KR-PCB-002); KS_H is never joined to SW on the PCB (KR-PCB-003)."),
    "03_gate_driver_ls": ("Mirror of the high-side channel: IN+ = PWM_L_F, IN- = PWM_H_F; DESAT diode cathode on SW; KS_L is never joined "
                          "to PGND on the PCB (KR-PCB-003). Isolation slot under the library SOIC-16W footprint is a layout task."),
    "04_sensing_island": ("Third UCC14141 (CR-12): VDD-VEE 15 V (80.6 k / 16.2 k, A-P2), COM-VEE 5.0 V = 5V_ISO, VEE = PGND. AMC1311 ladders "
                          "4 x 750 k (VIN, 602 V full scale) and 2 x 750 k (VOUT, 302 V) with 10.0 k bottoms; the taps VIN_DIV_T1..T3 and "
                          "VOUT_DIV_T1 are HV nodes (classes HV_VIN / HV_VOUT, 120 V steps)."),
    "05_selv_strip": ("Mezzanine socket SSW-125-01-G-D with the pin assignment of design_decisions.json; receiving networks 100 ohm / 100 pF / "
                      "10 k pull-down on RESET_N and BIAS_EN (A-P6); OPA2320 difference amplifiers gain 1.5; REF3125 -> VOC_SET 0.750 V "
                      "(I_OC 37.5 A); ISENSE_REF = 0.1 x 3V3 (A-P1); AO3400A + SS14 relay coil drive; fan header with tacho pull-up. "
                      "All nets on this sheet are SELV (CTRL_SELV)."),
    "06_mechanical": ("Heatsink envelope LAM 5 D K 100 12 (corner holes are placeholders), 6 x M4 baseplate standoffs, 4 x M3 control-board "
                      "standoffs, bare-PCB test pads. The PE stud and PGND-PE network are on sheet 01."),
}
CONTROL_PAGE_NOTES = {
    "01_aux_12v": ("TPS26400 eFuse: UVLO 10.0 / 9.3 V and OVP 14.45 / 13.4 V from 107 k / 4.42 k / 10.0 k, R_ILIM 6.04 k (I_CB about 1.96 A), "
                   "C_dVdT 100 nF, R_IMON 14.7 k, MODE open = circuit breaker (CR-18). RTN (EFUSE_RTN) is never tied to GND_CTRL (A-C3)."),
    "02_supplies": ("TPS54302 5 V buck (FB 100 k / 13.3 k), TPS767D301 dual LDO with core-first sequencing (1.9 V from 18.2 k / 30.1 k, 3.3 V fixed), "
                    "TPS3808G01 supervisor 101 k / 10 k (4.50 V threshold, CT 10 nF). The -EP LDO variant is NRND; TLV752 is the named alternative."),
    "03_dsp": "TMS320F28335PGFA, all 176 pins; units split into supplies, ADC, connected GPIO and unused pins. Pin map per design_decisions.json.",
    "04_dsp_decoupling": "One 100 nF per DSP supply pin (26), 2 x 2.2 uF per rail, 2.2 uF on ADCREFP/ADCREFM, 22 k on ADCRESEXT (SPRS439Q).",
    "05_clock_debug": "30 MHz oscillator on XCLKIN (X1 grounded, X2 open), 33 ohm series; boot straps GPIO84-87 pulled high; TI 14-pin JTAG; SCI-A header.",
    "06_pwm_fault_logic": ("ePWM1A/1B AND GATE_EN (SN74LVC2G08) -> 33 ohm -> mezzanine; SN74LVC1G74 fault latch (D = 1, CLK = ARM, CLR_N = "
                           "FAULT_LATCH_N, Q = FAULT_N = ARMED); 3 x SN74LV21A combiners; SN74LV04A restores the UVLO and PG_BIAS polarities "
                           "(A-C6, A-C7); TLV1702 comparators with REF3125-derived thresholds."),
    "07_adc_frontend": "1 k + 1 nF at every ADC input; heatsink NTC with 2.2 k to REF3V0 (REF3130); OTP threshold 42.2 k / 10 k = 0.575 V (110 C); LM61.",
    "08_interconnect": "Mezzanine header TSW-125-07-G-D (pin assignment per design_decisions.json), indicator LEDs, test pads, 4 x M3.",
}


# --- model access ---------------------------------------------------------------------------------------------

def board_model(board: str):
    """Model module of a board."""
    if board not in BOARDS:
        raise ValueError(f"board must be one of {BOARDS}, got {board!r}")
    return power_model if board == "power" else control_model


def project_name(board: str) -> str:
    return common.POWER_NAME if board == "power" else common.CONTROL_NAME


def project_title(board: str) -> str:
    return f"AIPE V2 SiC buck {board} board - {common.BASIS}"


def kicad_dir(board: str) -> Path:
    return common.POWER_DIR if board == "power" else common.CONTROL_DIR


def flag_page(board: str) -> str:
    model = board_model(board)
    return getattr(model, "FLAG_PAGE", None) or ("01_aux_12v" if board == "control" else list(model.PAGES)[-1])


def relative_path(path: Path) -> str:
    """Repository-relative POSIX path when `path` lies under the repository, else the absolute path."""
    path = Path(path).resolve()
    try:
        return path.relative_to(common.ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def build_circuit(board: str):
    """The board's Circuit (parts plus Circuit.block() presentation groups)."""
    return board_model(board).build()


def build_parts(board: str) -> list[dict]:
    """Deterministic part list of a board (shared model format, 'board' key set)."""
    return build_circuit(board).parts


def presentation_for(board: str, style: str | None = None, circuit=None) -> dict | None:
    """project_schematic presentation dict for a board and style (None = legacy drawing)."""
    style = style or SCHEMATIC_STYLE
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}, got {style!r}")
    if style == "legacy":
        return None
    result = dict(PRESENTATION[board], style="wired")
    groups = dict(getattr(circuit, "groups", {}) or {})
    titles = dict(getattr(circuit, "block_titles", {}) or {})
    if groups:
        result["groups"] = groups
    if titles:
        result["group_titles"] = titles
    return result


def net_names(parts) -> list[str]:
    return sorted({n for p in parts for n in p["nets"].values() if n})


# --- net classes ------------------------------------------------------------------------------------------------

def wildcard_match(pattern: str, name: str) -> bool:
    """Anchored, case-sensitive wildcard match (* and ?) as KiCad applies netclass patterns."""
    regex = "".join(".*" if ch == "*" else "." if ch == "?" else re.escape(ch) for ch in pattern)
    return re.fullmatch(regex, name) is not None


def classify(nets, patterns: dict) -> tuple[dict, list, list]:
    """(net -> class, unclassed nets, nets matching several classes) for class -> pattern list."""
    assignment, unclassed, composite = {}, [], []
    for net in nets:
        hits = [name for name, pats in patterns.items() if any(wildcard_match(p, net) for p in pats)]
        if not hits:
            unclassed.append(net)
        elif len(hits) > 1:
            composite.append((net, hits))
        else:
            assignment[net] = hits[0]
    return assignment, unclassed, composite


def _class(name, clearance, track, via, nets):
    return dict(name=name, clearance=clearance, track_width=track, nets=list(nets), **via)


def board_net_classes(board: str, parts) -> tuple[list, dict]:
    """Net classes of a board (project_schematic format) and the net -> class assignment.

    Power: the baseline's eleven classes with POWER_HV_PATTERNS and an explicit CTRL_SELV list.  Control: Default,
    the shared HV patterns as guards, CTRL_PWR and an explicit CTRL_SELV list.  Raises ValueError when a net would
    belong to several classes, when a control-board net matches an HV guard, or when a net stays unclassed.
    """
    nets = net_names(parts)
    selv = SELV_CLEARANCE[board]
    if board == "power":
        hv_assignment, remaining, composite = classify(nets, POWER_HV_PATTERNS)
        if composite:
            raise ValueError(f"nets match several HV-side classes: {composite}")
        patterns = {**POWER_HV_PATTERNS, "CTRL_SELV": list(remaining)}
        classes = [
            _class("Default", selv, selv, SELV_VIA, []),
            *[_class(name, HV_FUNCTIONAL_OUTER, 2.0, HV_VIA, POWER_HV_PATTERNS[name]) for name in HV_CLASSES],
            _class("DRV_HS", SAME_ISLAND, 0.5, ISLAND_VIA, POWER_HV_PATTERNS["DRV_HS"]),
            _class("DRV_LS", SAME_ISLAND, 0.5, ISLAND_VIA, POWER_HV_PATTERNS["DRV_LS"]),
            _class("DESAT_HS", SAME_ISLAND, 0.3, ISLAND_VIA, POWER_HV_PATTERNS["DESAT_HS"]),
            _class("DESAT_LS", SAME_ISLAND, 0.3, ISLAND_VIA, POWER_HV_PATTERNS["DESAT_LS"]),
            _class("SENSE_ISO", SAME_ISLAND, 0.3, ISLAND_VIA, POWER_HV_PATTERNS["SENSE_ISO"]),
            _class("PGND_LV", SAME_ISLAND, 0.5, ISLAND_VIA, POWER_HV_PATTERNS["PGND_LV"]),
            _class("PE", HV_TO_PE, 2.0, HV_VIA, POWER_HV_PATTERNS["PE"]),
            _class("CTRL_SELV", selv, selv, SELV_VIA, remaining),
        ]
    else:
        guards = {name: list(pats) for name, pats in common.NET_CLASS_PATTERNS.items()}
        guard_assignment, remaining, composite = classify(nets, guards)
        if guard_assignment or composite:
            raise ValueError(f"control-board nets match HV-side patterns (HV net on the SELV board?): "
                             f"{sorted(guard_assignment) + [c[0] for c in composite]}")
        pwr = [n for n in CONTROL_PWR_NETS if n in remaining]
        signal = [n for n in remaining if n not in pwr]
        patterns = {**guards, "CTRL_PWR": pwr, "CTRL_SELV": signal}
        classes = [
            _class("Default", selv, selv, SELV_VIA, []),
            *[_class(name, HV_FUNCTIONAL_OUTER, 2.0, HV_VIA, guards[name]) for name in HV_CLASSES],
            _class("DRV_HS", SAME_ISLAND, 0.5, ISLAND_VIA, guards["DRV_HS"]),
            _class("DRV_LS", SAME_ISLAND, 0.5, ISLAND_VIA, guards["DRV_LS"]),
            _class("SENSE_ISO", SAME_ISLAND, 0.3, ISLAND_VIA, guards["SENSE_ISO"]),
            _class("PE", HV_TO_PE, 2.0, HV_VIA, guards["PE"]),
            _class("CTRL_PWR", selv, 1.0, ISLAND_VIA, pwr),
            _class("CTRL_SELV", selv, 0.25, SELV_VIA, signal),
        ]
    assignment, unclassed, composite = classify(nets, patterns)
    if unclassed or composite:
        raise ValueError(f"unclassed nets {unclassed}, composite nets {composite}")
    return classes, assignment


def class_clearances(classes) -> dict:
    return {c["name"]: c["clearance"] for c in classes}


def required_clearance(class_a: str, class_b: str, clearances: dict) -> float:
    """Clearance (mm, outer layers) that the design rules demand between two nets of the given classes."""
    cl_a, cl_b = clearances.get(class_a, clearances["Default"]), clearances.get(class_b, clearances["Default"])
    pair = {class_a, class_b}
    hv = pair & set(HV_SIDE)
    if hv and (pair - hv) & set(SELV_CLASSES):
        return HV_TO_SELV
    if hv and "PE" in pair:
        return HV_TO_PE
    if pair <= set(HV_SIDE) and class_a != class_b:
        for main, island in SAME_ISLAND_PAIRS:
            if main in pair and (pair - {main}) <= set(island):
                return SAME_ISLAND
        if REFERENCE_GROUP[class_a] != REFERENCE_GROUP[class_b]:
            return HV_FUNCTIONAL_OUTER
    return max(cl_a, cl_b)


# --- design rules -----------------------------------------------------------------------------------------------

def _in(item: str, classes) -> str:
    return "(" + " || ".join(f"{item}.NetClass == '{c}'" for c in classes) + ")"


def _pair(classes_a, classes_b) -> str:
    return f"({_in('A', classes_a)} && {_in('B', classes_b)}) || ({_in('A', classes_b)} && {_in('B', classes_a)})"


def _rule(name: str, condition: str, constraint: str, layer: str | None = None) -> str:
    layer_clause = f" (layer {layer})" if layer else ""
    return f'(rule "{name}"{layer_clause}\n  (condition "{condition}")\n  (constraint {constraint}))'


def functional_condition() -> str:
    """HV-side pairs across reference groups, plus different nets of the same HV class."""
    groups = {}
    for name in HV_SIDE:
        groups.setdefault(REFERENCE_GROUP[name], []).append(name)
    keys = list(groups)
    terms = [_pair(groups[a], groups[b]) for i, a in enumerate(keys) for b in keys[i + 1:]]
    terms += [f"(A.NetClass == '{c}' && B.NetClass == '{c}')" for c in HV_CLASSES]
    return " || ".join(f"({t})" for t in terms)


def pad_records(text: str) -> list[dict]:
    """Numbered pad records (number, at, size) of a footprint with the size replaced by the axis-aligned bounding box
    of the rotated pad, so that rotated library pads (e.g. the 270 degree SSOP-8 pads) measure correctly."""
    tree = parse(text)
    if tree[0] != "footprint":
        raise ValueError("Not a footprint s-expression")
    records = []
    for pad in children(tree, "pad"):
        number = str(pad[1])
        if not number:
            continue
        at = children(pad, "at")[0]
        size = children(pad, "size")[0]
        x, y = float(at[1]), float(at[2])
        angle = math.radians(float(at[3])) if len(at) > 3 else 0.0
        w, h = float(size[1]), float(size[2])
        box_w = abs(w * math.cos(angle)) + abs(h * math.sin(angle))
        box_h = abs(w * math.sin(angle)) + abs(h * math.cos(angle))
        records.append(dict(number=number, type=pad[2], shape=pad[3], at=[x, y], size=[round(box_w, 6), round(box_h, 6)]))
    return records


def pad_geometry(parts, custom_footprints=None, source=None) -> dict:
    """Footprint id -> rotation-corrected pad records for every footprint used by `parts` (library or model custom text)."""
    custom = custom_footprints or {}
    geometry = {}
    for part in parts:
        if part["footprint"] in geometry:
            continue
        lib, name = pf.split_footprint(part)
        if lib == pf.CUSTOM_LIB and name in custom:
            geometry[part["footprint"]] = pad_records(pf.custom_text(custom[name]))
        else:
            path = pf.installed_footprint(lib, name, source)
            if path is None:
                raise FileNotFoundError(f"Footprint {lib}:{name} is not installed")
            geometry[part["footprint"]] = pad_records(path.read_text(encoding="utf-8-sig"))
    return geometry


def pad_gap(a: dict, b: dict) -> float:
    """Edge-to-edge distance of two axis-aligned pad records (0 when they touch or overlap)."""
    dx = max(0.0, abs(a["at"][0] - b["at"][0]) - (a["size"][0] + b["size"][0]) / 2)
    dy = max(0.0, abs(a["at"][1] - b["at"][1]) - (a["size"][1] + b["size"][1]) / 2)
    return math.hypot(dx, dy)


def exception_clearance(gap_mm: float) -> float:
    """Pin-field exception clearance: the pad gap less 0.01 mm (KiCad measures true shapes, never closer than the
    axis-aligned gap), never below 0.1 mm."""
    return round(max(0.1, gap_mm - 0.01), 2)


def exception_kind(required_mm: float) -> str:
    """barrier = HV side to SELV (slot required); hv = an HV spacing rule; pitch = package pitch below the class clearance."""
    if required_mm >= HV_TO_SELV:
        return "barrier"
    return "hv" if required_mm > SAME_ISLAND else "pitch"


def pin_field_exceptions(parts, geometry: dict, assignment: dict, clearances: dict) -> list[dict]:
    """Footprints whose own pads cannot meet the clearances: one record per reference and class pair.

    For every pad pair of a part carrying different nets, the required clearance comes from required_clearance();
    when the pad gap is smaller the pair is recorded under its (sorted) class pair with the smallest gap seen.  Follows
    v2_pipeline_smoke.pin_field_rules, generalised to the class pairs of this design: barrier parts (UCC21710,
    UCC14141, TMCS1133) appear because their land gap is below 9 mm - the baseline answers that with the 1.2 mm
    isolation slots; HV passives (ladders, indicator strings, DESAT diodes, snubber, PE resistors) because their
    package is shorter than the HV rule; fine-pitch packages because 0.65 mm pitch leaves 0.15-0.2 mm between pads
    (below the board minimum, fabricator confirmation per assumptions_accepted.corrections_to_seeds).
    """
    records = []
    for part in parts:
        pads = [p for p in geometry.get(part["footprint"], []) if p["number"]]
        pairs = {}
        for i, a in enumerate(pads):
            for b in pads[i + 1:]:
                net_a, net_b = part["nets"].get(a["number"]), part["nets"].get(b["number"])
                if net_a == net_b:
                    continue
                # A no-connect pad carries KiCad's "unconnected-(REF-PadN)" net, which lives in the Default class and is
                # therefore 9.0 mm away from every HV-side pad of the same package by the barrier rule; the package
                # geometry cannot change, so these pairs need the same exception as any other pad pair.
                class_a = assignment[net_a] if net_a else "Default"
                class_b = assignment[net_b] if net_b else "Default"
                required = required_clearance(class_a, class_b, clearances)
                gap = pad_gap(a, b)
                if gap < required - 1e-6:
                    key = tuple(sorted((class_a, class_b)))
                    record = pairs.get(key)
                    if record is None or gap < record["min_gap_mm"]:
                        pairs[key] = dict(ref=part["ref"], footprint=part["footprint"], classes=list(key), required_mm=required,
                                          min_gap_mm=round(gap, 4), clearance_mm=exception_clearance(gap), kind=exception_kind(required),
                                          pads=[a["number"], b["number"]], nets=[net_a or "unconnected", net_b or "unconnected"], pad_pairs=0)
                    pairs[key]["pad_pairs"] += 1
        records += [pairs[k] for k in sorted(pairs)]
    return sorted(records, key=lambda r: (ps.reference_prefix(r["ref"]), ps.pin_key(r["ref"][len(ps.reference_prefix(r["ref"])):]), r["classes"]))


def exception_rule(record: dict) -> str:
    ref, (a, b) = record["ref"], record["classes"]
    pair = _pair([a], [b]) if a != b else f"A.NetClass == '{a}' && B.NetClass == '{a}'"
    condition = f"A.memberOfFootprint('{ref}') && B.intersectsCourtyard('{ref}') && ({pair})"
    return _rule(f"pin field {ref} {a}-{b} ({record['kind']})", condition, f"clearance (min {pf.num(record['clearance_mm'])}mm)")


def design_rules_text(board: str, exceptions, header_lines=()) -> str:
    """Custom design rules of a board: baseline class-pair rules, HV edge clearance, pin-field exceptions last.

    Later rules override earlier ones in KiCad, so the 9.0 mm HV-to-SELV and 5.0 mm HV-to-PE rules follow the
    functional rules and the per-footprint exceptions come last; the exceptions apply only to pairs that involve
    the named footprint's own items and items intersecting its courtyard, for the recorded class pairs.
    """
    lines = ["(version 1)"]
    lines += [f"# {line}" for line in header_lines]
    lines += [
        "# Rule order matters: later rules override earlier ones. Net-class clearances (project file) apply first.",
        _rule("HV functional clearance (inner layers)", functional_condition(),
              f"clearance (min {pf.num(HV_FUNCTIONAL_INNER)}mm)", "inner"),
        _rule("HV functional clearance (outer layers)", functional_condition(),
              f"clearance (min {pf.num(HV_FUNCTIONAL_OUTER)}mm)", "outer"),
        _rule("Same reference island (SW island, PGND island)",
              " || ".join(f"({_pair([main], island)})" for main, island in SAME_ISLAND_PAIRS),
              f"clearance (min {pf.num(SAME_ISLAND)}mm)"),
        _rule("HV side to PE", _pair(HV_SIDE, ["PE"]), f"clearance (min {pf.num(HV_TO_PE)}mm)"),
        _rule("HV side to CTRL_SELV (all layers)", _pair(HV_SIDE, SELV_CLASSES), f"clearance (min {pf.num(HV_TO_SELV)}mm)"),
        _rule("HV side to board edge", _in("A", HV_SIDE), f"edge_clearance (min {pf.num(HV_TO_EDGE)}mm)"),
    ]
    if exceptions:
        kinds = {k: sum(1 for r in exceptions if r["kind"] == k) for k in ("barrier", "hv", "pitch")}
        lines.append(f"# Pin-field exceptions derived from pad geometry, one per footprint and class pair: {kinds['barrier']} barrier "
                     "(HV side to SELV inside a barrier package - the 1.2 mm isolation slot is mandatory), "
                     f"{kinds['hv']} HV (package shorter than the HV rule - creepage review), "
                     f"{kinds['pitch']} pitch (0.65 mm pitch leaves 0.15-0.2 mm between pads - fabricator confirmation).")
        lines += [exception_rule(r) for r in exceptions]
    elif board == "control":
        lines.append("# No pin-field exception: the control board is entirely SELV, the HV rules above are guards only.")
    return "\n".join(lines) + "\n"


def design_rules(board: str) -> dict:
    selv = SELV_CLEARANCE[board]
    return {"min_clearance": selv, "min_track_width": selv, "min_via_diameter": 0.6, "min_through_hole_diameter": 0.3,
            "min_hole_clearance": 0.25, "min_copper_edge_clearance": 0.5}


# --- schematic spec ---------------------------------------------------------------------------------------------

def header_lines(board: str, classes, exceptions) -> list[str]:
    """Root-sheet text describing the design basis, the rule set and the evidence locations."""
    model = board_model(board)
    module = Path(model.__file__).name
    hv = ", ".join(c["name"] for c in classes if c["name"] in HV_SIDE and c["nets"])
    lines = [
        f"Design basis: examples/sic-buck-400v-200v-5kw/design/design_decisions.json (schema 3, 2026-10-10) - single source of truth; "
        f"electrical model automation/kicad_tools/{module}; generator automation/kicad_tools/generate_sic_schematics.py.",
        f"{common.BASIS}.",
    ]
    if board == "power":
        lines += [
            f"Net classes: {hv} - HV classes {pf.num(HV_FUNCTIONAL_OUTER)} mm, driver / DESAT / sensing islands {pf.num(SAME_ISLAND)} mm "
            f"intra-class, PE {pf.num(HV_TO_PE)} mm, CTRL_SELV and Default {pf.num(SELV_CLEARANCE[board])} mm (70 um copper).",
            f"Board rules (.kicad_dru): HV side to CTRL_SELV {pf.num(HV_TO_SELV)} mm on all layers; HV to PE {pf.num(HV_TO_PE)} mm; "
            f"HV functional {pf.num(HV_FUNCTIONAL_OUTER)} mm outer / {pf.num(HV_FUNCTIONAL_INNER)} mm inner; HV to board edge "
            f"{pf.num(HV_TO_EDGE)} mm; {len(exceptions)} pin-field exceptions derived from pad geometry "
            f"({sum(1 for r in exceptions if r['kind'] == 'barrier')} barrier, {sum(1 for r in exceptions if r['kind'] == 'hv')} HV, "
            f"{sum(1 for r in exceptions if r['kind'] == 'pitch')} package pitch) - creepage review.",
            "Barrier parts (UCC21710 x2, UCC14141 x3, AMC1311 x2, TMCS1133) need the 1.2 mm non-plated isolation slot of the baseline; "
            "the custom AIPE footprints embed it, the UCC21710 library footprint does not (layout task).",
            "TO-247-4 pad order 1 D, 2 S, 3 KS, 4 G is an ASSUMPTION (Wolfspeed PRD 05966 front view); unverified parts and placeholders "
            "are listed in components/bom_power.csv notes and in the model docstring.",
        ]
    else:
        lines += [
            f"Net classes: CTRL_SELV and Default {pf.num(SELV_CLEARANCE[board])} mm (35 um copper), CTRL_PWR for the supply rails (1.0 mm "
            "tracks, added assumption A-G2); the shared HV patterns are guards and match no net of this SELV board.",
            "Board rules (.kicad_dru): the baseline class-pair rules are carried as guards; the control board must never carry HV copper "
            "and its copper never lies above HV copper of the power board (air clearance >= 11 mm, standards review item).",
            "Polarity adaptations A-C6 (UVLO flag inverted to UVLO_N) and A-C7 (raw PG_BIAS_x_N inverted before the AND combiner) use one "
            "SN74LV04A; the power board keeps the raw PG polarity on mezzanine pins 30/32/33.",
        ]
    lines.append("Evidence: native ERC manifests under verification/erc/<run>/run.json; review PDF under review/; this drawing has no CAD "
                 "evidence beyond those runs. AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED.")
    return lines


def build_spec(board: str, parts, kicad_target: Path, design_target: Path, *, exceptions, style: str | None = None,
               circuit=None) -> tuple[dict, dict]:
    """(project_schematic spec dict, net -> class assignment) of a board; `style` selects the drawing (wired / legacy)."""
    model = board_model(board)
    classes, assignment = board_net_classes(board, parts)
    heads = header_lines(board, classes, exceptions)
    spec = dict(name=project_name(board), title=project_title(board), kicad_dir=Path(kicad_target), design_dir=Path(design_target),
                pages=dict(model.PAGES), parts=parts, revision=REVISION, comment=common.BANNER, flag_nets=list(model.FLAG_NETS),
                flag_page=flag_page(board), header_lines=heads,
                page_notes=dict(POWER_PAGE_NOTES if board == "power" else CONTROL_PAGE_NOTES),
                net_classes=classes, design_rules=design_rules(board),
                dru_text=design_rules_text(board, exceptions, heads[:2] + [common.BANNER]),
                paper=PAPER, board=board, mapping_name=f"schematic_mapping_{board}.json",
                presentation=presentation_for(board, style, circuit))
    return spec, assignment


# --- generation -------------------------------------------------------------------------------------------------

def validate_model(board: str, parts, custom_footprints) -> dict:
    """Pad/net mapping and ERC pre-check; ValueError on any finding (the goal is zero native ERC findings)."""
    issues = pf.validate_pad_mapping(parts, custom_footprints=custom_footprints)
    if issues:
        raise ValueError(f"{board}: pad/net mapping inconsistent: " + "; ".join(issues))
    report = ps.analyse_connectivity(parts, board_model(board).FLAG_NETS)
    problems = {k: report[k] for k in ("undriven_power_nets", "pin_conflicts", "single_pin_nets", "no_connect_pins_with_nets") if report[k]}
    if problems:
        raise ValueError(f"{board}: connectivity pre-check failed: {json.dumps(problems)[:2000]}")
    return report


def generate(board: str, kicad_target: Path | None = None, design_target: Path | None = None, *, style: str | None = None) -> dict:
    """Generate one board's KiCad project; returns the summary (also merged into schematic_mapping_<board>.json).

    `style` is "wired" (V2.1 presentation layer) or "legacy" (V2 drawing); default SCHEMATIC_STYLE.  Both styles share
    the connectivity, the net classes, the .kicad_pro settings and the .kicad_dru text; the wired path additionally runs
    the connectivity guard of schematic_presentation before any file is written.
    """
    model = board_model(board)
    kicad_target = Path(kicad_target or kicad_dir(board))
    design_target = Path(design_target or DESIGN_DIR)
    circuit = build_circuit(board)
    parts = circuit.parts
    custom = dict(getattr(model, "CUSTOM_FOOTPRINTS", {}) or {})
    diagnostics = validate_model(board, parts, custom)
    libraries = pf.prepare_libraries(parts, kicad_target, custom_footprints=custom, notice_text=NOTICE_TEXT[board],
                                     descr=f"{project_name(board)} project footprint library")
    if libraries["warnings"]:
        raise ValueError(f"{board}: prepare_libraries warnings: " + "; ".join(libraries["warnings"]))
    classes, assignment = board_net_classes(board, parts)
    geometry = pad_geometry(parts, custom)
    exceptions = pin_field_exceptions(parts, geometry, assignment, class_clearances(classes))
    spec, assignment = build_spec(board, parts, kicad_target, design_target, exceptions=exceptions, style=style, circuit=circuit)
    result = ps.generate_project(spec)
    pages = {}
    for p in parts:
        pages[p["page"]] = pages.get(p["page"], 0) + 1
    by_class = {}
    for net, name in sorted(assignment.items()):
        by_class.setdefault(name, []).append(net)
    generation = dict(
        generator="automation.kicad_tools.generate_sic_schematics", board=board, project=project_name(board), revision=REVISION,
        banner=common.BANNER, basis=common.BASIS, baseline="design/design_decisions.json (schema 3)",
        model=f"automation/kicad_tools/{Path(model.__file__).name}",
        kicad_dir=relative_path(kicad_target), parts=len(parts), nets=len(net_names(parts)), dnp=sum(1 for p in parts if p.get("dnp")), pages=pages,
        sheets=[s["key"] for s in result["sheets"]], parts_placed=result["parts_placed"], symbol_fallbacks=result["symbol_fallbacks"],
        flags=result["flags"], flag_page=spec["flag_page"],
        libraries={k: libraries[k] for k in ("libraries", "copied", "custom", "models", "parts")},
        net_classes=[dict(c, nets=by_class.get(c["name"], []), patterns=c["nets"]) for c in classes],
        net_class_pattern_deltas=list(NET_CLASS_PATTERN_DELTAS), design_rules=design_rules(board),
        rules_mm=dict(hv_to_selv=HV_TO_SELV, hv_to_pe=HV_TO_PE, hv_functional_outer=HV_FUNCTIONAL_OUTER,
                      hv_functional_inner=HV_FUNCTIONAL_INNER, same_island=SAME_ISLAND, hv_to_edge=HV_TO_EDGE),
        pin_field_exceptions=exceptions, precheck=diagnostics, style=style or SCHEMATIC_STYLE,
        evidence="native ERC manifests under verification/erc/<run>/run.json; this record documents generation only",
    )
    mapping_path = Path(result["mapping"])
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["generation"] = generation
    mapping_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    return dict(result, generation=generation)


# --- V2.1 gates -------------------------------------------------------------------------------------------------

def export_netlist(board: str, kicad_target: Path | None, target: Path, cli=None) -> dict:
    """kicad-cli sch export netlist (kicadxml) of a board's root sheet."""
    cli = cli or find_kicad_cli()
    if not cli:
        raise FileNotFoundError("kicad-cli unavailable")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [str(cli), "sch", "export", "netlist", "--format", "kicadxml", "--output", str(target), str(root_sheet(board, kicad_target))]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    return dict(path=str(target), exit_code=completed.returncode, stderr=completed.stderr.strip()[-2000:])


def pad_map(parts) -> dict:
    return {(p["ref"], str(pad)): net for p in parts for pad, net in p["nets"].items() if net}


def compare_pad_maps(a: dict, b: dict) -> dict:
    keys = sorted(set(a) | set(b))
    mismatches = [dict(ref=r, pad=p, a=a.get((r, p)), b=b.get((r, p))) for r, p in keys if a.get((r, p)) != b.get((r, p))]
    return dict(exact=not mismatches, pads=len(keys), mismatch_count=len(mismatches), mismatches=mismatches[:50],
                net_names_equal=set(a.values()) == set(b.values()),
                extra_names=sorted(set(b.values()) - set(a.values()))[:50], missing_names=sorted(set(a.values()) - set(b.values()))[:50])


def verify_wired(board: str, kicad_target: Path | None = None, out_dir: Path | None = None, cli=None,
                 release: Path | None = None) -> dict:
    """V2.1 acceptance gates of a generated project; returns a dict with `passed` and one entry per gate.

    1. .kicad_dru byte-identical to the frozen V2 release of the board (the rule text depends only on parts and nets);
    2. .kicad_pro net_settings equal to the V2 release (net classes and patterns unchanged);
    3. native ERC with --severity-all reports zero findings (finding types are listed: footprint_link_issues alone means
       KiCad could not resolve ${KIPRJMOD} libraries from the project path, e.g. a subst/junction path, not a drawing fault);
    4. exported netlist (ref, pad) -> net identical to the live model and to the V2 release netlist, same net names;
    5. paper_fill: every sheet drawn on a paper larger than the base paper fills at least presentation min_fill of the
       drawable area (schematic_metrics hull), so escalation is driven by content, not by loose layouts.
    """
    from automation.kicad_tools.run_check import run_check
    from automation.verification.netlist_check_sic import load_xml
    kicad_target = Path(kicad_target or kicad_dir(board))
    out_dir = Path(out_dir or GATES_DIR / board)
    out_dir.mkdir(parents=True, exist_ok=True)
    release = Path(release or RELEASE_V2)
    name = project_name(board)
    rel_dir = release / "kicad" / f"{board}_board"
    gates = {}
    # the rule text and the net settings depend only on parts and nets: a legacy-style generation of the same model
    # into a scratch directory must produce byte-identical files; the frozen V2 release is compared as information
    # (the generator's class set may legitimately have moved on since the release was frozen)
    import tempfile
    with tempfile.TemporaryDirectory(prefix="aipe_legacy_") as temp:
        legacy = generate(board, Path(temp) / "kicad", Path(temp) / "design", style="legacy")
        dru_legacy = (Path(temp) / "kicad" / f"{name}.kicad_dru").read_bytes()
        pro_legacy = json.loads((Path(temp) / "kicad" / f"{name}.kicad_pro").read_text(encoding="utf-8"))["net_settings"]
    dru_new = (kicad_target / f"{name}.kicad_dru").read_bytes()
    dru_old = (rel_dir / f"{name}.kicad_dru").read_bytes()
    gates["dru_identical"] = dict(passed=dru_new == dru_legacy, identical_to_legacy_generation=dru_new == dru_legacy,
                                  identical_to_v2_release=dru_new == dru_old, bytes_new=len(dru_new), bytes_v2=len(dru_old))
    pro_new = json.loads((kicad_target / f"{name}.kicad_pro").read_text(encoding="utf-8"))["net_settings"]
    pro_old = json.loads((rel_dir / f"{name}.kicad_pro").read_text(encoding="utf-8"))["net_settings"]
    gates["net_settings_equal"] = dict(passed=pro_new == pro_legacy, equal_to_legacy_generation=pro_new == pro_legacy,
                                       equal_to_v2_release=pro_new == pro_old, classes=len(pro_new.get("classes", [])),
                                       classes_v2=len(pro_old.get("classes", [])))
    code, manifest_path = run_check("erc", root_sheet(board, kicad_target), out_dir / "erc", cli)
    manifest = read_manifest(manifest_path)
    details = manifest.get("details", [])
    finding_types = {}
    for d in details:
        finding_types[d.get("type")] = finding_types.get(d.get("type"), 0) + 1
    gates["erc_zero"] = dict(passed=manifest.get("finding_count") == 0 and manifest.get("tool_exit_code") == 0,
                             findings=manifest.get("finding_count"), manifest=str(manifest_path), finding_types=finding_types,
                             erc_nonfootprint_findings=sum(n for t, n in finding_types.items() if t != "footprint_link_issues"),
                             details=details[:20])
    xml = out_dir / "netlist.xml"
    export = export_netlist(board, kicad_target, xml, cli)
    drawn, refs, info, duplicates = load_xml(xml)
    model_parts = build_parts(board)
    model_map = pad_map(model_parts)
    vs_model = compare_pad_maps(model_map, drawn)
    v2_xml = release / "manufacturing" / f"{board}_board" / "netlist.xml"
    v2_map, v2_refs, _, _ = load_xml(v2_xml)
    vs_v2 = compare_pad_maps(v2_map, drawn)
    gates["netlist_vs_model"] = dict(passed=vs_model["exact"] and vs_model["net_names_equal"] and not duplicates
                                     and refs == {p["ref"] for p in model_parts}, export_exit=export["exit_code"],
                                     refs=len(refs), duplicates=duplicates[:10], **vs_model)
    gates["netlist_vs_v2"] = dict(passed=vs_v2["exact"] and vs_v2["net_names_equal"] and refs == v2_refs, source=str(v2_xml), **vs_v2)
    from automation.kicad_tools import schematic_metrics as sm
    presentation = presentation_for(board, "wired") or {}
    min_fill = float(presentation.get("min_fill", 0.25))
    metrics = sm.measure_project(kicad_target, root_name=name)
    escalated = [dict(sheet=sh["file"], paper=sh["paper"], fill=sh["paper_fill"])
                 for sh in metrics["sheets"] if not sh["root"] and sh["paper"] != PAPER]
    gates["paper_fill"] = dict(passed=all(e["fill"] is not None and e["fill"] >= min_fill for e in escalated), min_fill=min_fill,
                               base_paper=PAPER, escalated=escalated,
                               sheets={sh["file"]: dict(paper=sh["paper"], fill=sh["paper_fill"]) for sh in metrics["sheets"]},
                               text_overlaps=metrics["totals"]["text_overlaps"], name_tags=metrics["totals"]["name_tags"],
                               note="name_tags are single global labels: KiCad's default-ignored single_global_label check "
                                    "would report one warning per tag")
    result = dict(board=board, kicad_dir=str(kicad_target), passed=all(g["passed"] for g in gates.values()), gates=gates)
    (out_dir / "schematic_gates.json").write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    return result


# --- evidence ---------------------------------------------------------------------------------------------------

def root_sheet(board: str, kicad_target: Path | None = None) -> Path:
    return Path(kicad_target or kicad_dir(board)) / f"{project_name(board)}.kicad_sch"


def read_manifest(path) -> dict:
    """run_check manifest with the ERC finding details added from the JSON report."""
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    report = Path(manifest.get("report", ""))
    manifest["manifest"] = str(path)
    if report.is_file():
        data = json.loads(report.read_text(encoding="utf-8-sig"))
        manifest["details"] = [dict(sheet=sheet.get("path"), type=v.get("type"), severity=v.get("severity"), description=v.get("description"),
                                    items=[i.get("description") for i in v.get("items", [])])
                               for sheet in data.get("sheets", []) for v in sheet.get("violations", [])]
    return manifest


def run_erc(board: str, kicad_target: Path | None = None, output_root: Path = ERC_ROOT, cli=None) -> dict:
    """Native kicad-cli ERC of a board's root sheet through run_check; returns the manifest with details."""
    from automation.kicad_tools.run_check import run_check
    code, manifest_path = run_check("erc", root_sheet(board, kicad_target), Path(output_root), cli)
    manifest = read_manifest(manifest_path)
    manifest["wrapper_exit_code"] = code
    return manifest


def pdf_page_count(path: Path) -> int | None:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path)).pages)
    except Exception:  # pypdf missing or unreadable file: count page objects textually
        try:
            return len(re.findall(rb"/Type\s*/Page[^s]", path.read_bytes()))
        except OSError:
            return None


def export_pdf(board: str, kicad_target: Path | None = None, target: Path | None = None, cli=None) -> dict:
    """kicad-cli sch export pdf of the whole hierarchy; returns path, exit code and page count."""
    cli = cli or find_kicad_cli()
    if not cli:
        raise FileNotFoundError("kicad-cli unavailable")
    target = Path(target or REVIEW_DIR / f"schematic_{board}.pdf")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [str(cli), "sch", "export", "pdf", "--output", str(target), str(root_sheet(board, kicad_target))]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    return dict(path=str(target), exit_code=completed.returncode, pages=pdf_page_count(target) if target.is_file() else None,
                stderr=completed.stderr.strip()[-2000:])


def write_merged_bom(target: Path = BOM_CSV, sources: dict | None = None) -> dict:
    """components/bom.csv: bom_power.csv and bom_control.csv rows with a leading board column."""
    sources = sources or BOM_SOURCES
    rows = []
    for board, path in sources.items():
        with Path(path).open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = [f for f in BOM_FIELDS[1:] if f not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"{path}: columns {missing} missing")
            rows += [dict(board=board, **{f: row[f] for f in BOM_FIELDS[1:]}) for row in reader]
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=BOM_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    counts = {board: sum(1 for r in rows if r["board"] == board) for board in sources}
    return dict(path=str(target), rows=len(rows), per_board=counts, dnp=sum(1 for r in rows if r["dnp"] == "yes"))


def main(argv=None) -> int:
    """CLI: generate the projects, optionally run ERC, export the review PDFs and write the merged BOM."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--board", choices=BOARDS + ("all",), default="all")
    parser.add_argument("--erc", action="store_true", help="run native kicad-cli ERC into verification/erc")
    parser.add_argument("--pdf", action="store_true", help="export review/schematic_<board>.pdf")
    parser.add_argument("--bom", action="store_true", help="write components/bom.csv from the two board BOMs")
    parser.add_argument("--style", choices=STYLES, default=None, help=f"drawing style (default {SCHEMATIC_STYLE})")
    parser.add_argument("--gates", action="store_true", help="run the V2.1 gates (DRU identity, net_settings, ERC 0, netlist vs model and V2)")
    args = parser.parse_args(argv)
    boards = BOARDS if args.board == "all" else (args.board,)
    print(common.BANNER)
    failures = 0
    for board in boards:
        result = generate(board, style=args.style)
        gen = result["generation"]
        kinds = {k: sum(1 for r in gen["pin_field_exceptions"] if r["kind"] == k) for k in ("barrier", "hv", "pitch")}
        print(f"{board}: {gen['parts']} parts, {gen['nets']} nets, sheets {gen['sheets']}, fallbacks {sorted(gen['symbol_fallbacks'])}, "
              f"pin-field exceptions {kinds} -> {result['root']}")
        if args.erc:
            manifest = run_erc(board)
            print(f"{board} ERC: status {manifest['status']}, findings {manifest.get('finding_count')}, tool exit {manifest.get('tool_exit_code')} "
                  f"-> {manifest['manifest']}")
            for detail in manifest.get("details", [])[:40]:
                print(f"  {detail['severity']} {detail['type']}: {detail['description']} {detail['items']}")
            failures += manifest["wrapper_exit_code"] != 0
        if args.pdf:
            pdf = export_pdf(board)
            print(f"{board} PDF: {pdf['path']} ({pdf['pages']} pages, exit {pdf['exit_code']})")
            failures += pdf["exit_code"] != 0
        if args.gates:
            gates = verify_wired(board)
            print(f"{board} gates: {'passed' if gates['passed'] else 'FAILED'} " +
                  ", ".join(f"{k}={'ok' if v['passed'] else 'FAIL'}" for k, v in gates["gates"].items()))
            failures += not gates["passed"]
    if args.bom:
        print("BOM:", write_merged_bom())
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
