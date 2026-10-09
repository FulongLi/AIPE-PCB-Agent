"""Recompute the calculations and connectivity claims cited by knowledge records.

Usage (repository root):

    python -m automation.knowledge.check_evidence            # write results
    python -m automation.knowledge.check_evidence --check    # compare only

Each check reproduces one number or connectivity fact that a skill, block or
rule relies on, using inputs taken from the cited source. Calculation checks
need no downloaded files. Netlist checks read the Git-ignored reference cache;
if the cache is absent they are reported as ``skipped`` - never as passed.

A passed check upgrades a statement to "analytically checked" (the arithmetic
and connectivity agree with the source). It is not simulation or hardware
validation.
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from automation.knowledge import allegro_netlist, odb_netlist
from automation.knowledge.common import CACHE, KNOWLEDGE, load_json, sha256_file, write_json

RESULTS = KNOWLEDGE / "verification" / "evidence-checks.json"
CGD1700_NETLIST = (CACHE / "REF-WS-CGD1700HB2M-UNA" / "extracted" / "CGD1700-ORCAD"
                   / "OrCAD Capture Schematic" / "allegro" / "pstxnet.dat")
CGD15_ODB = (CACHE / "REF-WS-CGD15SG00D2" / "extracted" / "CGD15SG00D2-ALL"
             / "CGD15SG00D2_rev7.0" / "ODB" / "CGD15SG00D2_rev7.0.t_g_z")


@dataclass
class Check:
    id: str
    title: str
    reference: str
    location: str
    kind: str  # "calculation" or "netlist"
    run: Callable[[], dict]
    source_file: Path | None = None
    tags: list = field(default_factory=list)


def calc(inputs: dict, computed: float, unit: str, stated: float | None, tolerance: float) -> dict:
    """Compare a recomputed value with the value stated in the source."""
    result = {"inputs": inputs, "computed": round(computed, 6), "unit": unit}
    if stated is None:
        result["status"] = "computed"
        return result
    error = abs(computed - stated) / abs(stated)
    result.update(stated=stated, relative_error=round(error, 4), tolerance=tolerance,
                  status="pass" if error <= tolerance else "fail")
    return result


# --- Wolfspeed CGD1700HB2M-UNA (PRD-06992) ---------------------------------
def desat_trip() -> dict:
    v_th, r2, r3, n, vf = 0.7, 2200.0, 220.0, 2, 0.5
    return calc({"V_OC_thresh_V": v_th, "R2_ohm": r2, "R3_ohm": r3, "diodes": n, "Vf_V": vf},
                v_th * (r2 + r3) / r3 - n * vf, "V", 6.7, 0.01)


def desat_blanking() -> dict:
    r1, r2, r3, c, v_th, v_dd = 2200.0, 2200.0, 220.0, 56e-12, 0.7, 15.0
    rs = r1 + r2 + r3
    t = -(r1 + r2) / rs * r3 * c * math.log(1 - rs / r3 * v_th / v_dd)
    return calc({"R1": r1, "R2": r2, "R3": r3, "C_blank_F": c, "V_OC_thresh_V": v_th, "VDD_V": v_dd},
                t * 1e9, "ns", 46.0, 0.02)


def fsw_limit_cgd1700() -> dict:
    p, qg, dv = 2.0, 118e-9, 18.0
    return calc({"P_W": p, "QG_C": qg, "dV_V": dv}, p / (qg * dv) / 1e3, "kHz", 940.0, 0.01)


def fsw_limit_xm3() -> dict:
    p, qg, dv = 2.0, 1330e-9, 19.0
    return calc({"P_W": p, "QG_C": qg, "dV_V": dv}, p / (qg * dv) / 1e3, "kHz", 79.0, 0.01)


def lt3015(r_top_a: float, r_top_b: float, r_bottom: float) -> float:
    r2 = 1 / (1 / r_top_a + 1 / r_top_b)
    return -1.22 * (1 + r2 / r_bottom) - 30e-9 * r2


def neg_ldo_bom() -> dict:
    return calc({"R2": "54.9k||54.9k", "R1": 12.1e3, "I_ADJ_A": 30e-9},
                lt3015(54.9e3, 54.9e3, 12.1e3), "V", -4.0, 0.01)


def neg_ldo_schematic() -> dict:
    return calc({"R2": "10k||10k", "R1": 2.2e3, "I_ADJ_A": 30e-9},
                lt3015(10e3, 10e3, 2.2e3), "V", -4.0, 0.01)


def pos_ldo() -> dict:
    return calc({"I_SET_A": 10e-6, "R_FB_ohm": 1.8e6}, 10e-6 * 1.8e6, "V", 18.0, 0.001)


# --- Wolfspeed CGD15SG00D2 (PRD-08391) ---------------------------------------
def llc_frequency() -> dict:
    # Schematic note "Fsw = R*10 Hz" with R12 = 47 k; user guide says "approximately 500 kHz".
    return calc({"R_T_ohm": 47e3, "relation": "Fsw = R * 10 Hz"}, 47e3 * 10 / 1e3, "kHz", 500.0, 0.10)


def steering_resistances() -> dict:
    r6, r7 = 10.0, 10.0
    result = calc({"R6_ohm": r6, "R7_ohm": r7, "diode": "ideal (drop ignored)"},
                  r6 * r7 / (r6 + r7), "ohm", None, 0)
    result["note"] = "turn-on R = R6 = 10 ohm; turn-off R ~ R6 || R7 = 5 ohm before diode drop"
    return result


# --- TI TIDA-010054 (TIDUES0F) ------------------------------------------------
def dab_pmax() -> dict:
    n, v1, v2, fs, l = 1.6, 800.0, 500.0, 100e3, 35e-6
    return calc({"N": n, "V1": v1, "V2": v2, "fs": fs, "L": l}, n * v1 * v2 / (8 * fs * l) / 1e3, "kW", 22.85, 0.005)


def dab_phase() -> dict:
    n, v1, v2, fs, l, p = 1.6, 800.0, 500.0, 100e3, 35e-6, 10e3
    phi = math.pi / 2 * (1 - math.sqrt(1 - 8 * fs * l * p / (n * v1 * v2)))
    return calc({"N": n, "V1": v1, "V2": v2, "fs": fs, "L": l, "P": p}, math.degrees(phi), "deg", 23.0, 0.03)


def dab_cout() -> dict:
    return calc({"dQ_C": 50e-6, "V_ripple_V": 5.0}, 50e-6 / 5.0 * 1e6, "uF", 10.0, 0.001)


def dc_block() -> dict:
    fs, l = 100e3, 35e-6
    return calc({"fs": fs, "L": l, "criterion": "f_res = fs/10"}, 100 / (4 * math.pi ** 2 * fs ** 2 * l) * 1e6, "uF", 7.2, 0.01)


def gate_power_ti() -> dict:
    vdd, vee, qg, fs = 15.0, -4.0, 53e-9, 100e3
    standard = (vdd - vee) * qg * fs
    result = calc({"VDD": vdd, "VEE": vee, "QG": qg, "fs": fs, "TI_expression": "2*(VDD-VEE)*QG*fs"},
                  2 * standard, "W", 0.2, 0.02)
    result["note"] = (f"TI Eq.30 includes a factor 2 ({2 * standard:.3f} W); the Wolfspeed/standard "
                      f"expression P = QG*fs*dV gives {standard:.3f} W. Conflict preserved in KR-IS-001.")
    return result


def divider(top: float, n_top: int, bottom: float, v_in: float) -> float:
    return v_in * bottom / (n_top * top + bottom)


def divider_primary() -> dict:
    return calc({"R_top": "8 x 634k", "R_bottom": 10e3, "V_in": 800}, divider(634e3, 8, 10e3, 800), "V", 1.57, 0.01)


def divider_secondary() -> dict:
    return calc({"R_top": "8 x 634k", "R_bottom": 7.68e3, "V_in": 500}, divider(634e3, 8, 7.68e3, 500), "V", 0.76, 0.01)


def shunt_primary() -> dict:
    result = calc({"I_A": 12.5, "R_ohm": 3e-3}, 12.5 * 3e-3 * 1e3, "mV", 37.5, 0.001)
    result["note"] = f"shunt dissipation {12.5 ** 2 * 3e-3:.3f} W; AMC1302 linear input +/-50 mV"
    return result


def shunt_secondary() -> dict:
    result = calc({"I_A": 20.0, "R_ohm": 1.5e-3}, 20 * 1.5e-3 * 1e3, "mV", 30.0, 0.001)
    result["note"] = f"shunt dissipation {20 ** 2 * 1.5e-3:.3f} W; AMC1306M05 input +/-50 mV"
    return result


def thermal(r_jc: float, stated: float) -> Callable[[], dict]:
    def run() -> dict:
        tj, ta, r_hs, r_iso = 150.0, 40.0, 0.5, 0.1
        return calc({"TJ_max": tj, "TA": ta, "Rth_HS": r_hs, "Rth_iso": r_iso, "Rth_JC": r_jc,
                     "model": "two FETs share one heat sink"},
                    (tj - ta) / (2 * r_hs + r_iso + r_jc), "W", stated, 0.02)
    return run


def ladder_stress() -> dict:
    v, n, r = 800.0, 8, 634e3
    per = v * r / (n * r + 10e3)
    result = calc({"V_bus": v, "resistors": n, "R_each": r}, per, "V", None, 0)
    result["note"] = (f"each resistor sees ~{per:.0f} V and dissipates {per ** 2 / r * 1e3:.1f} mW; "
                      "compare with the resistor's limiting element voltage and pulse rating (not verified here)")
    return result


# --- Netlist checks ---------------------------------------------------------
def cgd1700_desat() -> dict:
    nets = allegro_netlist.parse(CGD1700_NETLIST)
    want = {
        "RT25 VDD->bias node": allegro_netlist.connected(nets, ("RT25", "2"), ("UT2", "5")),
        "bias node->DB8 anode": allegro_netlist.connected(nets, ("RT25", "1"), ("DB8", "A")),
        "DB8 and DT7 in series": allegro_netlist.connected(nets, ("DB8", "C"), ("DT7", "A")),
        "DT7 cathode->drain connector JT4": allegro_netlist.connected(nets, ("DT7", "C"), ("JT4", "1")),
        "RT22 bias node->OC pin": allegro_netlist.connected(nets, ("RT22", "2"), ("RT25", "1"))
        and allegro_netlist.connected(nets, ("RT22", "1"), ("UT2", "2")),
        "RT21 OC->source": allegro_netlist.connected(nets, ("RT21", "2"), ("UT2", "2"))
        and allegro_netlist.connected(nets, ("RT21", "1"), ("UT2", "3")),
        "CT19 blanking cap OC->source": allegro_netlist.connected(nets, ("CT19", "1"), ("UT2", "2"))
        and allegro_netlist.connected(nets, ("CT19", "2"), ("UT2", "3")),
        "DT5 clamp OC->source": allegro_netlist.connected(nets, ("DT5", "C"), ("UT2", "2")),
    }
    return {"assertions": want, "status": "pass" if all(want.values()) else "fail"}


def cgd1700_gate() -> dict:
    nets = allegro_netlist.parse(CGD1700_NETLIST)
    gate = allegro_netlist.net_of(nets, "RT33", "1")
    want = {
        "OUTH->RT27": allegro_netlist.connected(nets, ("UT2", "4"), ("RT27", "1")),
        "OUTL->RT28": allegro_netlist.connected(nets, ("UT2", "6"), ("RT28", "1")),
        "CLMPI->RT29": allegro_netlist.connected(nets, ("UT2", "7"), ("RT29", "1")),
        "RT27, RT28, RT29 and RT33 share the gate net": bool(gate) and
        {("RT27", "2"), ("RT28", "2"), ("RT29", "2"), ("RT33", "1")} <= gate.nodes,
        "RT33 gate->source": allegro_netlist.connected(nets, ("RT33", "2"), ("UT2", "3")),
    }
    return {"assertions": want, "gate_net": gate.name if gate else None,
            "status": "pass" if all(want.values()) else "fail"}


def cgd1700_classes() -> dict:
    classes = allegro_netlist.spacing_classes(allegro_netlist.parse(CGD1700_NETLIST))
    want = {name: name in classes for name in
            ("PRIMARY", "LOW-SIDE", "HIGH-SIDE", "LS-DESAT-MIDPOINT", "HS-DESAT-MIDPOINT", "LS-DRAIN", "HS-DRAIN")}
    return {"assertions": want, "net_counts": classes, "status": "pass" if all(want.values()) else "fail"}


def cgd1700_hs_desat() -> dict:
    nets = allegro_netlist.parse(CGD1700_NETLIST)
    want = {
        "DB7 and DT8 in series": allegro_netlist.connected(nets, ("DB7", "C"), ("DT8", "A")),
        "DT8 cathode->drain connector JT5": allegro_netlist.connected(nets, ("DT8", "C"), ("JT5", "1")),
        "RT23 OC->HS source": allegro_netlist.connected(nets, ("RT23", "2"), ("UT3", "2"))
        and allegro_netlist.connected(nets, ("RT23", "1"), ("UT3", "3")),
    }
    return {"assertions": want, "status": "pass" if all(want.values()) else "fail"}


def cgd15_gate() -> dict:
    nets = odb_netlist.connectivity(CGD15_ODB)
    d3, r6, r7, u1 = (odb_netlist.nets_of(nets, r) for r in ("D3", "R6", "R7", "U1"))
    want = {
        "D3 pin 1 on driver VOUT (U1 pin 7)": d3.get("1") == u1.get("7"),
        "R6 from VOUT to GATE": {r6.get("1"), r6.get("2")} == {u1.get("7"), "GATE"},
        "R7 from D3 pin 2 to GATE": {r7.get("1"), r7.get("2")} == {d3.get("2"), "GATE"},
        "Zener D4 across SOURCE-VDD2": set(odb_netlist.nets_of(nets, "D4").values()) == {"SOURCE", "VDD2"},
        "Zener D5 across SOURCE-VSS2": set(odb_netlist.nets_of(nets, "D5").values()) == {"SOURCE", "VSS2"},
    }
    return {"assertions": want, "status": "pass" if all(want.values()) else "fail",
            "note": "Diode polarity is not in the netlist; schematic symbol shows the D3 cathode at pin 1."}


TI, WS15, WS17 = "REF-TI-TIDA-010054", "REF-WS-CGD15SG00D2", "REF-WS-CGD1700HB2M-UNA"
CHECKS = [
    Check("EC-001", "CGD1700 DESAT trip voltage", WS17, "PRD-06992 §4.4.4", "calculation", desat_trip),
    Check("EC-002", "CGD1700 DESAT external blanking time", WS17, "PRD-06992 §4.4.4", "calculation", desat_blanking),
    Check("EC-003", "Max f_sw from 2 W bias, CCB032M12FM3T", WS17, "PRD-06992 §4.8", "calculation", fsw_limit_cgd1700),
    Check("EC-004", "Max f_sw from 2 W bias, CAB450M12XM3", WS17, "PRD-09301 §3.7 Eq.3", "calculation", fsw_limit_xm3),
    Check("EC-005", "LT3015 negative rail, 2025 BOM divider", WS17, "PRD-06992 §4.3.4; BOM sheet 2", "calculation", neg_ldo_bom),
    Check("EC-006", "LT3015 negative rail, Rev V1 schematic divider", WS17, "CGD1700 schematic sheet 3", "calculation", neg_ldo_schematic),
    Check("EC-007", "LT3082 positive rail (R2 variant)", WS17, "PRD-06992 Table 14", "calculation", pos_ldo),
    Check("EC-008", "UCC25800 switching frequency from R_T", WS15, "CGD15SG00D2 schematic sheet 2; PRD-08391 p.11", "calculation", llc_frequency),
    Check("EC-009", "Steering-diode equivalent turn-off resistance", WS15, "CGD15SG00D2 schematic sheet 1", "calculation", steering_resistances),
    Check("EC-010", "DAB theoretical maximum power", TI, "TIDUES0F §2.3.4.1", "calculation", dab_pmax),
    Check("EC-011", "DAB phase shift at 10 kW", TI, "TIDUES0F §2.3.4.4", "calculation", dab_phase),
    Check("EC-012", "DAB output capacitance from ripple charge", TI, "TIDUES0F §2.3.4.5", "calculation", dab_cout),
    Check("EC-013", "DC-blocking capacitor minimum", TI, "TIDUES0F Eq.20", "calculation", dc_block),
    Check("EC-014", "Gate-drive power per primary FET (TI expression)", TI, "TIDUES0F Eq.30", "calculation", gate_power_ti),
    Check("EC-015", "Primary HV divider output at 800 V", TI, "TIDUES0F §3.2.1", "calculation", divider_primary),
    Check("EC-016", "Secondary HV divider output at 500 V", TI, "TIDUES0F §3.2.2", "calculation", divider_secondary),
    Check("EC-017", "Primary shunt full-scale signal", TI, "TIDUES0F §3.3", "calculation", shunt_primary),
    Check("EC-018", "Secondary shunt full-scale signal", TI, "TIDUES0F §3.3", "calculation", shunt_secondary),
    Check("EC-019", "Max loss per primary FET (C3M0075120K)", TI, "TIDUES0F Eq.32", "calculation", thermal(1.1, 50.0)),
    Check("EC-020", "Max loss per secondary FET (C3M0030090K)", TI, "TIDUES0F Eq.32", "calculation", thermal(0.48, 69.0)),
    Check("EC-021", "Voltage stress per HV divider resistor", TI, "TIDUES0F Figure 3-2; BOM RT0805BRD07634KL", "calculation", ladder_stress),
    Check("EC-022", "CGD1700 low-side DESAT network connectivity", WS17, "pstxnet.dat", "netlist", cgd1700_desat, CGD1700_NETLIST),
    Check("EC-023", "CGD1700 low-side gate path connectivity", WS17, "pstxnet.dat", "netlist", cgd1700_gate, CGD1700_NETLIST),
    Check("EC-024", "CGD1700 net spacing classes", WS17, "pstxnet.dat NET_SPACING_TYPE", "netlist", cgd1700_classes, CGD1700_NETLIST),
    Check("EC-025", "CGD15SG00D2 steering diode and Zener split connectivity", WS15, "ODB++ eda/data", "netlist", cgd15_gate, CGD15_ODB),
    Check("EC-026", "CGD1700 high-side DESAT network connectivity", WS17, "pstxnet.dat", "netlist", cgd1700_hs_desat, CGD1700_NETLIST),
]


def run_all() -> dict:
    results = []
    for check in CHECKS:
        entry = {"id": check.id, "title": check.title, "reference": check.reference,
                 "location": check.location, "kind": check.kind}
        if check.source_file is not None and not check.source_file.exists():
            entry.update(status="skipped", note="source file not in local cache; run acquire and inspect_sources")
        else:
            entry.update(check.run())
            if check.source_file is not None:
                entry["source_sha256"] = sha256_file(check.source_file)
        results.append(entry)
    counts: dict[str, int] = {}
    for entry in results:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return {"generator": "automation/knowledge/check_evidence.py",
            "meaning": "pass = recomputed value or connectivity agrees with the source; computed = value derived "
                       "for review without a stated source value; skipped = source not cached (not a pass).",
            "summary": dict(sorted(counts.items())), "checks": results}


def ids() -> set[str]:
    return {check.id for check in CHECKS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="do not write; fail if results differ")
    args = parser.parse_args(argv)
    report = run_all()
    for entry in report["checks"]:
        print(f"{entry['id']} {entry['status']:8} {entry['title']}")
    print("summary:", report["summary"])
    failed = report["summary"].get("fail", 0)
    if args.check:
        stored = {c["id"]: c for c in load_json(RESULTS)["checks"]} if RESULTS.exists() else {}
        differing = []
        for entry in report["checks"]:
            previous = stored.get(entry["id"])
            if entry["status"] == "skipped":
                # Without the cache only confirm the stored result came from a real run.
                if not previous or previous["status"] == "skipped":
                    differing.append(entry["id"])
            elif entry != previous:
                differing.append(entry["id"])
        if differing or set(stored) != ids():
            print("stored evidence-checks.json differs from a fresh run:", differing)
            return 1
        print("stored evidence-checks.json reproduces (skipped checks not re-run)")
    else:
        write_json(RESULTS, report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
