"""V2 power-stage simulation campaign driver (AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED).

Runs every model in ``simulation/models/campaign_manifest.json`` through the repository's behavioural
simulation layer (``automation.simulation.buck_stage`` + the KiCad-bundled ngspice shared library via
``automation.simulation.ngspice_runner``; both used unmodified), writes the per-run outputs of
``buck_stage.write_outputs`` (deck, parameters, waveform CSVs, SVG plots, summary.json) into
``results/<run>/`` and adds campaign-level products:

* ``results/<run>/campaign_metrics.json`` - event (load step / dump) excursions, startup, limit checks,
  textbook cross-check values and the numpy switched-model comparison table;
* ``results/<run>/controller.csv`` and ``event_*.svg`` for the cascaded-controller runs;
* ``results/parasitic_<case>/`` - the module's parasitic (L_loop, C_oss) overshoot study per case;
* ``results/loop_gain_analysis.json`` - small-signal crossover / phase-margin check of both controllers;
* ``results/campaign_summary.json`` and ``results/campaign_log.txt``.

Controller substitution: the module ships a single voltage-loop PI (an averaged stand-in for the DSP
firmware). The design baseline requires a 2.0-2.5 kHz outer voltage-loop crossover *with an inner
current loop*; a single PI cannot cross above the 930 Hz LC resonance with phase margin, so for the
runs whose manifest ``controller`` is ``cascade`` this driver replaces the eight controller lines of the
module deck (Bref, Rfb, Cfb, Bint, Cint, Rint, .ic V(vint), Bduty) by a cascaded average-current-mode
controller built from the manifest gains. Everything else in the deck (power stage, comparator PWM,
switch and diode models, probes) is the module's own. No firmware exists; the gains are documented
stand-ins, see simulation_report.md.

Usage (repository root):  python examples/sic-buck-400v-200v-5kw/simulation/results/run_campaign.py [--only NAME ...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))

from automation.simulation import buck_stage as bs  # noqa: E402
from automation.simulation.ngspice_runner import NgSpice  # noqa: E402

SIM_DIR = HERE.parents[1]
MODELS = SIM_DIR / "models"
RESULTS = SIM_DIR / "results"
LABEL = "AI-GENERATED BEHAVIOURAL SIMULATION - V2 - HUMAN REVIEW REQUIRED"
EXTRA_VECTORS = ["iref", "ilf", "duty_raw"]


def g(value: float) -> str:
    return f"{value:.12g}"


# ------------------------------------------------------------------ controller substitution --
def cascade_lines(p: dict, c: dict) -> list[str]:
    """Deck lines of the cascaded controller (outer voltage PI -> i_ref -> inner current PI -> duty)."""
    tss = p["soft_start"]
    ramp = f"min(1, time/{g(tss)})" if tss > 0 else "1"
    r_fb, r_if = 1e3, 1e3
    c_fb = 1.0 / (2 * math.pi * c["fb_filter_hz"] * r_fb)
    c_if = 1.0 / (2 * math.pi * c["i_filter_hz"] * r_if)
    err_v, err_i = "(V(ref)-V(fb))", "(V(iref)-V(ilf))"
    windup_v = (f"((V(iref_raw) >= {g(c['iref_max_A'])}) && (V(ref) > V(fb))) || "
                f"((V(iref_raw) <= {g(c['iref_min_A'])}) && (V(ref) < V(fb)))")
    windup_i = (f"((V(duty_raw) >= {g(c['d_max'])}) && (V(iref) > V(ilf))) || "
                f"((V(duty_raw) <= {g(c['d_min'])}) && (V(iref) < V(ilf)))")
    ff = f"V(ref)/{g(p['vin'])} + " if c.get("feedforward", True) else ""
    return [
        "* --- campaign controller: cascaded average-current-mode PI (replaces the module single-loop PI) ---",
        f"Bref ref 0 V = {g(p['vout_ref'])}*{ramp}",
        f"Rfb out fb {g(r_fb)}", f"Cfb fb 0 {g(c_fb)}",
        f"Bintv 0 vintv I = ({windup_v}) ? 0 : {g(c['kiv_A_per_V_s'])}*{err_v}",
        "Cintv vintv 0 1", "Rintv vintv 0 1G", ".ic V(vintv)=0",
        f"Birefraw iref_raw 0 V = {g(c['kpv_A_per_V'])}*{err_v} + V(vintv)",
        f"Biref iref 0 V = max({g(c['iref_min_A'])}, min({g(c['iref_max_A'])}, V(iref_raw)))",
        "Bil il 0 V = i(Vld) + i(Vcout)",
        f"Rif il ilf {g(r_if)}", f"Cif ilf 0 {g(c_if)}",
        f"Binti 0 vinti I = ({windup_i}) ? 0 : {g(c['kii_per_A_s'])}*{err_i}",
        "Cinti vinti 0 1", "Rinti vinti 0 1G", ".ic V(vinti)=0",
        f"Bdutyraw duty_raw 0 V = {ff}{g(c['kpi_per_A'])}*{err_i} + V(vinti)",
        f"Bduty duty 0 V = max({g(c['d_min'])}, min({g(c['d_max'])}, V(duty_raw)))",
    ]


def patch_deck(deck: list[str], p: dict, c: dict) -> list[str]:
    """Replace the module PI lines by the cascade; the rest of the module deck is untouched."""
    out, removed = [], 0
    for line in deck:
        head = line.split()[0] if line.strip() else ""
        if head in ("Bref", "Rfb", "Cfb", "Bint", "Cint", "Rint", "Bduty") or line.startswith(".ic V(vint)=0"):
            removed += 1
            if head == "Bduty":
                out += cascade_lines(p, c)
            continue
        out.append(line)
    if removed != 8:
        raise RuntimeError(f"unexpected module deck layout: removed {removed} controller lines instead of 8")
    return out


# ------------------------------------------------------------------ metrics -----------------
def event_metrics(p: dict, v: dict, t_ev: float, kind: str, limits: dict) -> dict:
    """Excursion, recovery and peaks after a load event; cycle-averaged like the module's load-step metric."""
    t, vout, il, iload = v["time"], v["out"], v["l1#branch"], v["vld#branch"]
    T, vref = p["period"], p["vout_ref"]
    grid, _, avg = bs._cycle_average(t, vout, T, T / 50)
    t_w = min(t_ev + 8e-3, float(grid[-1]))
    sel = (grid >= t_ev) & (grid <= t_w)
    dev = avg[sel] - vref
    i = int(np.argmax(np.abs(dev)))
    band = limits["recovery_band_pct"] / 100.0 * vref
    outside = np.abs(dev) > band
    recovered = bool(not outside[-1])
    idx = np.where(outside)[0]
    t_rec = float(grid[sel][idx[-1]] - t_ev) if (idx.size and recovered) else (0.0 if recovered else None)
    raw = (t >= t_ev) & (t <= t_w)
    i_before = bs.window_stats(t, iload, max(t_ev - 5 * T, float(t[0])), t_ev)["mean"]
    i_after = bs.window_stats(t, iload, t_w - 5 * T, t_w)["mean"]
    m = {
        "type": kind, "t_event_s": t_ev, "i_load_before_A": i_before, "i_load_after_A": i_after,
        "excursion_cycle_avg_V": float(dev[i]), "excursion_pct_of_vref": 100 * float(dev[i]) / vref,
        "t_excursion_after_event_s": float(grid[sel][i] - t_ev),
        "vout_raw_min_V": float(vout[raw].min()), "vout_raw_max_V": float(vout[raw].max()),
        "il_max_A": float(il[raw].max()), "il_min_A": float(il[raw].min()),
        "recovery_band_V": band, "recovered_within_window": recovered, "recovery_time_s": t_rec,
        "window_s": t_w - t_ev,
    }
    is_dump = i_after < 1.0
    m["limit_basis"] = ("load dump: must stay below the 230 V output OVP (CR-04); the 10 V / 5 ms figures apply to the 12.5 A step only"
                        if is_dump else "12.5 A load step: <= 10 V excursion, <= 5 ms recovery to the 1 % band")
    m["checks"] = {
        "excursion_within_10V": (None if is_dump else abs(m["excursion_cycle_avg_V"]) <= limits["load_step_excursion_max_V"]),
        "recovery_within_5ms": (None if is_dump else (t_rec is not None) and t_rec <= limits["load_step_recovery_max_ms"] * 1e-3),
        "vout_raw_below_ovp_230V": m["vout_raw_max_V"] < limits["ovp_out_V"],
        "il_below_oc_trip_37p5A": m["il_max_A"] < limits["oc_trip_A"],
    }
    return m


def startup_metrics(p: dict, v: dict, t_first_event: float | None, limits: dict) -> dict:
    """Closed-loop startup: overshoot against the reference, inductor peak, time to 99 % of the reference."""
    t, vout, il = v["time"], v["out"], v["l1#branch"]
    t_end = t_first_event if t_first_event else float(t[-1])
    pre = t <= t_end
    vref = p["vout_ref"]
    peak = float(vout[pre].max())
    reach = np.where(vout[pre] >= 0.99 * vref)[0]
    T = p["period"]
    grid, _, avg = bs._cycle_average(t[pre], vout[pre], T, T / 50)
    tail = grid >= t_end - 50 * T
    m = {"soft_start_s": p["soft_start"], "vout_peak_V": peak, "overshoot_V": peak - vref,
         "overshoot_pct": 100 * (peak - vref) / vref, "il_peak_A": float(il[pre].max()),
         "t_99pct_s": float(t[pre][reach[0]]) if reach.size else None,
         "vout_cycle_avg_pkpk_last_50T_V": float(np.ptp(avg[tail])) if tail.any() else None}
    m["checks"] = {"vout_peak_below_ovp_230V": peak < limits["ovp_out_V"],
                   "il_peak_below_oc_trip_37p5A": m["il_peak_A"] < limits["oc_trip_A"],
                   "overshoot_within_1pct_static_band": abs(peak - vref) <= 0.01 * vref}
    return m


def textbook_values(p: dict, m: dict) -> dict:
    """Closed-form values from the run's own parameters (the formulas of the research records)."""
    io = m["i_load_mean"]
    d = m["duty"] if p["closed_loop"] else p["duty"]
    fs, L, C, esr, td = p["fs"], p["L"], p["Cout"], p["Cout_esr"], p["dead_time"]
    di = p["vout_ref"] * (1 - d) / (L * fs)
    il_rms = math.sqrt(io ** 2 + di ** 2 / 12)
    i_hs_rms = math.sqrt(d * (io ** 2 + di ** 2 / 12))
    i_ls_rms = math.sqrt((1 - d) * (io ** 2 + di ** 2 / 12))
    i_cin = math.sqrt(max(d * (io ** 2 + di ** 2 / 12) - (d * io) ** 2, 0.0))
    dq = d * (1 - d) * io / fs
    return {
        "basis": "D from the run; dI = Vout (1-D)/(L fs); I_rms identities; I_Cin,rms = sqrt(D(Io^2+dI^2/12)-(D Io)^2); "
                 "P = I_rms^2 R; P_dt = 2 t_d fs V_SD Io; ripple dI/(8 fs C)+ESR dI; input ripple dQ/C_in + ESR_in (Io+dI/2)",
        "dIL_App": di, "il_peak_A": io + di / 2, "il_rms_A": il_rms, "i_hs_rms_A": i_hs_rms, "i_ls_rms_A": i_ls_rms,
        "i_cin_rms_A": i_cin, "i_cout_rms_A": di / math.sqrt(12),
        "p_cond_hs_W": i_hs_rms ** 2 * p["Rds_on_hs"], "p_cond_ls_W": i_ls_rms ** 2 * p["Rds_on_ls"],
        "p_cond_total_W": i_hs_rms ** 2 * p["Rds_on_hs"] + i_ls_rms ** 2 * p["Rds_on_ls"],
        "p_deadtime_W": 2 * td * fs * p["body_diode_vf"] * io,
        "p_dcr_W": il_rms ** 2 * p["L_dcr"],
        "vout_ripple_Vpp": di / (8 * fs * C) + esr * di,
        "vin_ripple_Vpp": dq / p["Cin"] + p["Cin_esr"] * (io + di / 2),
        "i_in_mean_A_ideal": d * io,
    }


def steady_checks(p: dict, m: dict, limits: dict) -> dict:
    return {
        "vout_ripple_below_2Vpp": m["vout_pkpk"] <= limits["vout_ripple_max_Vpp"],
        "vin_bus_ripple_below_2pct": m["vin_bus_pkpk"] <= limits["vin_ripple_max_pct_pp"] / 100 * p["vin"],
        "il_peak_below_oc_trip_37p5A": m["il_peak"] < limits["oc_trip_A"],
        "il_peak_below_isat_worst_35A": m["il_peak"] < limits["isat_30pct_worst_A"],
        "cin_rms_per_part_below_14p5A": m["i_cin_rms"] / 2 <= limits["cin_irms_rating_per_part_A"],
        "cout_rms_per_part_below_23p5A": m["i_cout_rms"] / 2 <= limits["cout_irms_rating_per_part_A"],
    }


# ------------------------------------------------------------------ loop-gain analysis --------
def loop_gain_analysis(p: dict, c: dict, module_pi: dict) -> dict:
    """Small-signal crossover and margins (continuous-time; comparator PWM as a T/2 delay)."""
    L, C, esr, dcr, T = p["L"], p["Cout"], p["Cout_esr"], p["L_dcr"], p["period"]
    f = np.logspace(1, 5, 6000)
    s = 2j * np.pi * f

    def lp(fc):
        return 1 / (1 + s / (2 * np.pi * fc))

    def margins(tl):
        mag = np.abs(tl)
        idx = np.where(np.diff(np.sign(mag - 1)) < 0)[0]
        cross = [{"f_Hz": float(f[i]), "phase_margin_deg": float(((180 + np.degrees(np.angle(tl[i]))) + 180) % 360 - 180)} for i in idx]
        ph = np.degrees(np.unwrap(np.angle(tl)))
        j = np.where(np.diff(np.sign(ph + 180)) != 0)[0]
        gm = float(-20 * np.log10(np.abs(tl[j[0]]))) if j.size else None
        return {"crossovers": cross, "gain_margin_dB": gm}

    out = {"method": "continuous-time small-signal model: duty -> iL = Vin/(sL + DCR + Zp), Zp = (ESR + 1/sC) || R; comparator PWM "
                     "modelled as a T/2 delay; current filter 10 kHz, voltage filter 20 kHz; inner loop closed analytically; "
                     "no sampling effects (no firmware exists)", "cases": []}
    for vin in (360.0, 400.0, 440.0):
        for r in (8.0, 16.0, 1e6):
            zc = esr + 1 / (s * C)
            zp = zc * r / (zc + r)
            gdi = vin / (s * L + dcr + zp)
            ti = (c["kpi_per_A"] + c["kii_per_A_s"] / s) * gdi * lp(c["i_filter_hz"]) * np.exp(-s * T / 2)
            tv = (c["kpv_A_per_V"] + c["kiv_A_per_V_s"] / s) * (ti / (1 + ti)) * zp * lp(c["fb_filter_hz"])
            tm = (module_pi["kp"] + module_pi["ki"] / s) * vin * zp / (s * L + dcr + zp) * lp(20e3) * np.exp(-s * T / 2)
            out["cases"].append({"vin_V": vin, "load_R_ohm": r, "cascade_inner": margins(ti), "cascade_outer": margins(tv),
                                 "module_single_loop_pi": margins(tm)})
    out["lc_filter"] = {"f0_Hz": 1 / (2 * math.pi * math.sqrt(L * C)), "Z0_ohm": math.sqrt(L / C),
                        "Q_at_8_ohm": 8.0 * math.sqrt(C / L),
                        "input_filter_f_Hz": 1 / (2 * math.pi * math.sqrt(p["L_in"] * p["Cin"])),
                        "input_filter_Q": math.sqrt(p["L_in"] / p["Cin"]) / (p["R_in"] + p["Cin_esr"])}
    return out


# ------------------------------------------------------------------ parasitic sweep -----------
def parasitic_sweep(spice: NgSpice, raw_model: dict, sweep: dict, log) -> list[dict]:
    results = []
    for case in sweep["cases"]:
        p = bs.resolve_params(dict(raw_model, parasitics=case))
        model = bs.numpy_switched_model(p)
        study = bs.simulate_parasitic(p, model, spice)
        # diagnostic re-run of the identical deck for the high-side current (commutation di/dt of the ideal switch)
        v2 = spice.run(study["deck"], vectors=["time", "vhs#branch"], expected_end=case["cycles"] * p["period"])
        t2, ihs = v2["time"], v2["vhs#branch"]
        di = np.diff(ihs) / np.diff(t2)
        after = t2[1:] >= p["period"]
        tag = f"parasitic_L{case['L_loop'] * 1e9:.0f}nH_R{case['R_loop']:g}ohm"
        out_dir = RESULTS / tag
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "deck.cir").write_text("\n".join(study["deck"]) + "\n", encoding="utf-8")
        vec = study["vectors"]
        sel = vec["time"] >= p["period"]
        bs.write_svg_plot(out_dir / "parasitic_vsw.svg", f"{tag}: switch node with ideal-switch commutation (estimate only)",
                          vec["time"][sel], [("vsw", vec["sw"][sel]), ("v_ds_hs", vec["v_ds_hs"][sel])], "V", x_unit="us")
        analytic = {f"{d:g}_A_per_ns": {"L_didt_overshoot_V": case["L_loop"] * d * 1e9,
                                        "vsw_peak_V_at_vin": p["vin"] + case["L_loop"] * d * 1e9}
                    for d in sweep["analytic_di_dt_A_per_ns"]}
        res = {k: val for k, val in bs._jsonable(study).items() if k != "deck"}
        res.update({
            "case": tag, "vin_V": p["vin"], "il_peak_used_A": model["il_peak"],
            "ideal_switch_di_dt_off_A_per_ns": float(-di[after].min() / 1e9),
            "ideal_switch_di_dt_on_A_per_ns": float(di[after].max() / 1e9),
            "analytic_L_didt": analytic,
            "energy_bound_I_sqrt_L_over_C_V": study["estimate_hs_turn_off_overshoot_V"],
            "Z0_ohm": math.sqrt(case["L_loop"] / case["C_oss"]),
            "Q_loop": math.sqrt(case["L_loop"] / case["C_oss"]) / case["R_loop"],
            "interpretation": "The behavioural switch commutates in about one solver step, so the deck's overshoot is the energy-transfer "
                              "bound of an instantaneous commutation damped only by R_loop; it is NOT a prediction of the C4MS025120K "
                              "turn-off overshoot. The engineering estimate is L_loop x di/dt at the gate-driver design edge "
                              "(2.5 A/ns) - see analytic_L_didt - to be replaced by double-pulse measurement.",
        })
        (out_dir / "study.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        log(f"  {tag}: vsw_max {study['vsw_max']:.0f} V (+{study['vsw_overshoot_above_vin']:.0f} V), v_ds_hs_max "
            f"{study['v_ds_hs_max']:.0f} V, f_ring {study['ring_frequency_Hz'] / 1e6:.0f} MHz, ideal-switch di/dt "
            f"{res['ideal_switch_di_dt_off_A_per_ns']:.1f} A/ns, L di/dt(2.5 A/ns) = {analytic['2.5_A_per_ns']['L_didt_overshoot_V']:.0f} V, "
            f"{study['runtime_s']:.2f} s")
        results.append(res)
    return results


# ------------------------------------------------------------------ one run ------------------
def run_one(spice: NgSpice, entry: dict, manifest: dict, log) -> dict:
    raw = json.loads((MODELS / entry["model"]).read_text(encoding="utf-8-sig"))
    p = bs.resolve_params(raw)
    limits = manifest["limits"]
    controller = entry.get("controller")
    deck = bs.build_deck(p)
    vectors = list(bs.WANTED_VECTORS)
    gains = dict(manifest["cascade_controller"], **entry.get("controller_overrides", {}))
    if controller == "cascade":
        deck = patch_deck(deck, p, gains)
        vectors += EXTRA_VECTORS
    start = time.perf_counter()
    v = spice.run(deck, vectors=vectors, expected_end=p["t_end"])
    runtime = time.perf_counter() - start
    metrics = bs.analyse(p, v)
    model = bs.numpy_switched_model(p)
    comparison = bs.compare(metrics, model)
    results = {
        "label": LABEL, "name": p["name"], "description": raw.get("description", ""),
        "ngspice": {"version": spice.version, "library": str(spice.library_path), "points": int(v["time"].size),
                    "runtime_s": runtime, "warnings": spice.warnings},
        "parameters": {k: val for k, val in p.items() if k != "description"},
        "metrics": metrics, "numpy_model": model, "comparison": comparison,
        "notes": [
            "Switches are ideal Ron/Roff elements: no switching, gate or Coss losses in the main run.",
            "Body diodes: exponential model (N=2) fitted to body_diode_vf at body_diode_i_ref; body_diode_rs 44 mohm keeps the "
            "fitted saturation current above the ngspice floor (about 1e-28 A) so that 4.6 V at 25 A is reproduced.",
            "Metrics are taken over the last metric_cycles periods; the load event must have recovered by then.",
        ],
    }
    camp = {"controller": controller or "open-loop PWL gates", "events": [], "steady_checks": steady_checks(p, metrics, limits),
            "textbook": textbook_values(p, metrics)}
    if controller == "cascade":
        camp["controller_gains"] = gains
        if entry.get("controller_overrides"):
            camp["controller_overrides"] = entry["controller_overrides"]
        results["notes"].append("Controller: cascaded average-current-mode PI from models/campaign_manifest.json replaces the module PI "
                                "(the 'pi' block in parameters is NOT what ran). No firmware exists.")
    elif controller == "module":
        camp["controller_gains"] = {"kp": p["pi"]["kp"], "ki": p["pi"]["ki"], "note": "module single-loop PI"}
    first_event = min((e["t"] for e in entry.get("events", [])), default=None)
    if p["closed_loop"]:
        camp["startup"] = startup_metrics(p, v, first_event if first_event and first_event > 1e-3 else None, limits)
    for e in entry.get("events", []):
        camp["events"].append(event_metrics(p, v, e["t"], e["type"], limits))
    camp["textbook_deviation_pct"] = {
        key: 100 * (metrics[mk] - camp["textbook"][tk]) / camp["textbook"][tk]
        for key, mk, tk in (("il_pkpk", "il_pkpk", "dIL_App"), ("il_peak", "il_peak", "il_peak_A"), ("il_rms", "il_rms", "il_rms_A"),
                            ("i_hs_rms", "i_hs_rms", "i_hs_rms_A"), ("i_cin_rms", "i_cin_rms", "i_cin_rms_A"),
                            ("i_cout_rms", "i_cout_rms", "i_cout_rms_A"), ("p_cond_hs", "p_cond_hs", "p_cond_hs_W"),
                            ("p_diode_deadtime", "p_diode_deadtime", "p_deadtime_W"), ("p_l_dcr", "p_l_dcr", "p_dcr_W"),
                            ("vout_pkpk", "vout_pkpk", "vout_ripple_Vpp"), ("vin_bus_pkpk", "vin_bus_pkpk", "vin_ripple_Vpp"))
        if camp["textbook"][tk] > 1e-9}
    results["campaign"] = camp
    out_dir = RESULTS / p["name"]
    files = bs.write_outputs(out_dir, p, deck, v, results)
    (out_dir / "campaign_metrics.json").write_text(json.dumps(bs._jsonable(camp), indent=2) + "\n", encoding="utf-8")
    if controller == "cascade":
        grid = np.arange(0.0, float(v["time"][-1]) + 0.5 * p["output"]["csv_dt"], p["output"]["csv_dt"])
        cols = {"time_s": grid}
        for name, key in (("vout_V", "out"), ("il_A", "l1#branch"), ("iref_A", "iref"), ("il_filtered_A", "ilf"),
                          ("duty", "duty"), ("duty_raw", "duty_raw"), ("i_load_A", "vld#branch")):
            cols[name] = bs.resample(v["time"], v[key], grid)
        bs.write_csv(out_dir / "controller.csv", cols)
        for e in camp["events"]:
            t0, t1 = e["t_event_s"] - 0.5e-3, e["t_event_s"] + 3e-3
            sel = (v["time"] >= t0) & (v["time"] <= t1)
            tag = f"{e['type']}_{e['t_event_s'] * 1e3:.0f}ms"
            ref = limits["ovp_out_V"] if "dump" in p["name"] else p["vout_ref"]
            bs.write_svg_plot(out_dir / f"event_{tag}_vout.svg", f"{p['name']}: output voltage around the {e['type']} (ref line {ref:g} V)",
                              v["time"][sel] - t0, [("vout", v["out"][sel])], "V", x_unit="us", reference=ref)
            bs.write_svg_plot(out_dir / f"event_{tag}_currents.svg", f"{p['name']}: inductor current and current reference",
                              v["time"][sel] - t0, [("iL", v["l1#branch"][sel]), ("i_ref", v["iref"][sel]), ("i_load", v["vld#branch"][sel])],
                              "A", x_unit="us")
        if camp.get("startup"):
            sel = v["time"] <= (first_event if first_event and first_event > 1e-3 else v["time"][-1])
            bs.write_svg_plot(out_dir / "startup_currents.svg", f"{p['name']}: startup inductor current and reference",
                              v["time"][sel], [("iL", v["l1#branch"][sel]), ("i_ref", v["iref"][sel])], "A")
    m = metrics
    log(f"{p['name']}: {results['ngspice']['points']} points, {runtime:.1f} s; vout {m['vout_mean']:.2f} V pkpk {m['vout_pkpk']:.3f} V; "
        f"iL pkpk {m['il_pkpk']:.2f} peak {m['il_peak']:.2f} rms {m['il_rms']:.2f} A; HS/LS rms {m['i_hs_rms']:.2f}/{m['i_ls_rms']:.2f} A; "
        f"Cin/Cout rms {m['i_cin_rms']:.2f}/{m['i_cout_rms']:.2f} A; Iin {m['i_in_mean']:.2f} A; Pcond {m['p_cond_hs'] + m['p_cond_ls']:.1f} W; "
        f"Pdt {m['p_diode_deadtime']:.2f} W; Vin bus pkpk {m['vin_bus_pkpk']:.2f} V; warnings {len(spice.warnings)}")
    for e in camp["events"]:
        rec = "n/a" if e["recovery_time_s"] is None else f"{e['recovery_time_s'] * 1e3:.2f} ms"
        log(f"    {e['type']} at {e['t_event_s'] * 1e3:.0f} ms: {e['i_load_before_A']:.1f} -> {e['i_load_after_A']:.1f} A, excursion "
            f"{e['excursion_cycle_avg_V']:+.2f} V (raw {e['vout_raw_min_V']:.1f}..{e['vout_raw_max_V']:.1f} V), recovery {rec}, "
            f"iL {e['il_min_A']:.1f}..{e['il_max_A']:.1f} A")
    if camp.get("startup"):
        s = camp["startup"]
        log(f"    startup: peak {s['vout_peak_V']:.2f} V ({s['overshoot_V']:+.2f} V), iL peak {s['il_peak_A']:.1f} A, "
            f"t99 {1e3 * s['t_99pct_s'] if s['t_99pct_s'] else float('nan'):.1f} ms")
    results["files"] = {k: str(path.relative_to(RESULTS)) for k, path in files.items()}
    return results


# ------------------------------------------------------------------ main ---------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="*", help="run only these manifest run names")
    parser.add_argument("--skip-parasitic", action="store_true")
    args = parser.parse_args(argv)
    manifest = json.loads((MODELS / "campaign_manifest.json").read_text(encoding="utf-8-sig"))
    RESULTS.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    def log(text: str):
        print(text)
        lines.append(text)

    spice = NgSpice()
    log(f"{LABEL}; {date.today().isoformat()}; {spice.version} from {spice.library_path}; numpy {np.__version__}")
    t_campaign = time.perf_counter()
    summary = {"label": LABEL, "date": date.today().isoformat(), "ngspice": spice.version, "library": str(spice.library_path),
               "manifest": "models/campaign_manifest.json", "runs": {}, "parasitic_sweep": [], "limits": manifest["limits"]}
    summary_path = RESULTS / "campaign_summary.json"
    if args.only and summary_path.exists():  # partial re-run: keep the entries of the runs not repeated
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["limits"] = manifest["limits"]
        log(f"partial run ({', '.join(args.only)}): merging into the existing campaign summary")
    for entry in manifest["runs"]:
        if args.only and entry["name"] not in args.only:
            continue
        try:
            res = run_one(spice, entry, manifest, log)
        except Exception as exc:  # keep the campaign going, report the failure
            log(f"{entry['name']}: FAILED - {exc}")
            summary["runs"][entry["name"]] = {"failed": str(exc)}
            continue
        m = res["metrics"]
        keys = ("duty", "vout_mean", "vout_pkpk", "vout_min", "vout_max", "vin_bus_mean", "vin_bus_pkpk", "il_mean", "il_pkpk",
                "il_peak", "il_min", "il_rms", "i_hs_rms", "i_hs_peak", "i_ls_rms", "i_ls_channel_rms", "i_diode_mean", "i_cin_rms",
                "i_cout_rms", "i_load_mean", "i_in_mean", "i_in_rms", "p_out", "p_in", "p_loss_total", "efficiency", "p_cond_hs",
                "p_cond_ls", "p_diode_deadtime", "p_diode_deadtime_estimate", "p_l_dcr", "p_cout_esr", "p_cin_esr", "p_r_in",
                "p_loss_modelled_sum", "steady_state", "startup", "load_step")
        summary["runs"][res["name"]] = {
            "controller": res["campaign"]["controller"], "points": res["ngspice"]["points"], "runtime_s": res["ngspice"]["runtime_s"],
            "warnings": res["ngspice"]["warnings"], "metrics": {k: m.get(k) for k in keys}, "comparison": res["comparison"],
            "numpy_model": {k: res["numpy_model"].get(k) for k in ("duty", "ccm", "warning", "vout_mean", "il_pkpk", "il_peak",
                                                                    "il_rms", "i_cin_rms", "i_cout_rms", "p_cond_hs", "p_cond_ls",
                                                                    "p_diode_deadtime", "p_l_dcr")},
            "campaign": res["campaign"], "files": res["files"],
        }
    if not args.skip_parasitic and not args.only:
        log("parasitic study (ideal-switch commutation; estimate only):")
        raw = json.loads((MODELS / (manifest["parasitic_sweep"]["base_run"] + ".json")).read_text(encoding="utf-8-sig"))
        summary["parasitic_sweep"] = parasitic_sweep(spice, raw, manifest["parasitic_sweep"], log)
    p_ref = bs.load_params(MODELS / "cl_400V_startup20ms_stepup.json")
    lga = loop_gain_analysis(p_ref, manifest["cascade_controller"], manifest["module_pi_reference"])
    (RESULTS / "loop_gain_analysis.json").write_text(json.dumps(lga, indent=2) + "\n", encoding="utf-8")
    for case in lga["cases"]:
        if case["load_R_ohm"] == 8.0:
            oc = case["cascade_outer"]["crossovers"][-1] if case["cascade_outer"]["crossovers"] else {}
            ic = case["cascade_inner"]["crossovers"][-1] if case["cascade_inner"]["crossovers"] else {}
            log(f"loop gain Vin {case['vin_V']:.0f} V / 8 ohm: outer fc {oc.get('f_Hz', 0):.0f} Hz PM {oc.get('phase_margin_deg', 0):.0f} deg "
                f"GM {case['cascade_outer']['gain_margin_dB']:.1f} dB; inner fc {ic.get('f_Hz', 0):.0f} Hz PM {ic.get('phase_margin_deg', 0):.0f} deg")
    # cross-check summary over the open-loop runs (numpy model valid: CCM, positive current during dead time)
    dev: dict[str, float] = {}
    for name, r in summary["runs"].items():
        if name.startswith("ol_") and "comparison" in r and r["numpy_model"].get("ccm"):
            for row in r["comparison"]:
                if row["deviation_pct"] is not None:
                    dev[row["metric"]] = max(dev.get(row["metric"], 0.0), abs(row["deviation_pct"]))
    summary["cross_check_max_abs_deviation_pct_open_loop_ccm_runs"] = dev
    summary["loop_gain_analysis"] = "results/loop_gain_analysis.json"
    if args.only:
        summary["partial_rerun_runtime_s"] = time.perf_counter() - t_campaign
    else:
        summary["total_runtime_s"] = time.perf_counter() - t_campaign
    log(f"campaign wall time {time.perf_counter() - t_campaign:.1f} s")
    summary_path.write_text(json.dumps(bs._jsonable(summary), indent=2) + "\n", encoding="utf-8")
    log_path = RESULTS / "campaign_log.txt"
    if args.only and log_path.exists():
        log_path.write_text(log_path.read_text(encoding="utf-8") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    else:
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
