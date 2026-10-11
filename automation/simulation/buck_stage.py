"""Behavioural synchronous-buck power-stage simulation (ngspice) with an exact numpy cross-check.

Deterministic without native tools: ``resolve_params``, ``build_deck`` / ``build_parasitic_deck``
(text only), ``gate_pwl``, ``numpy_switched_model`` (periodic steady state of the ideal switched
state equations through exact matrix exponentials), ``analyse`` (metrics from waveform arrays)
and the CSV / JSON / SVG writers. Requires the KiCad-bundled ngspice shared library:
``simulate`` and ``simulate_parasitic`` run the decks through ``NgSpice``.

Model scope (review this before quoting numbers): voltage-controlled switches with Ron/Roff
(no switching-loss or Coss model in the main run), body diodes as exponential diodes with
series resistance, an LC input filter so the input capacitor carries the AC component, an
averaged voltage-mode PI as a stand-in for the DSP firmware, and an optional parasitic
loop-inductance study whose switch-node overshoot is an order-of-magnitude estimate only.
Open-loop gates are PWL sources with exact breakpoints (0.05 % agreement with the exact
model); closed-loop gates come from a behavioural comparator whose switching instants are
aligned to the solver grid, so the PWM resolution is ``vin * t_step / T`` at the output
(default ``t_step`` 50 ns -> 1 V here) and the PI can hunt by up to that amount; the
metrics report it. Nothing here is hardware-validated.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

from automation.simulation.ngspice_runner import NgSpice, ngspice_available, resample, uniform_grid

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DIR = ROOT / "examples/sic-buck-400v-200v-5kw/simulation"
THERMAL_VOLTAGE = 0.02585

DEFAULTS: dict = {
    "name": "buck",
    "vin": 400.0, "vout_ref": 200.0, "fs": 50e3,
    "closed_loop": False, "duty": None,
    "dead_time": 200e-9,
    "L": 267e-6, "L_dcr": 10e-3,
    "Cout": 60e-6, "Cout_esr": 10e-3,
    "Cin": 100e-6, "Cin_esr": 10e-3,
    "L_in": 10e-6, "R_in": 0.1,
    "Rds_on_hs": 25e-3, "Rds_on_ls": 25e-3,
    "body_diode_vf": 3.5, "body_diode_rs": 0.02, "body_diode_i_ref": None,
    "load_R": None, "load_P": None, "load_step": None,
    "soft_start_ms": 2.0,
    "t_end": 12e-3, "t_step": None,
    "metric_cycles": 10,
    "pwm": "auto", "gate_edge": 10e-9,
    "pi": {"kp": 2e-4, "ki": 1.5, "d_min": 0.0, "d_max": 0.95, "fb_filter_hz": 20e3, "feedforward": True},
    "parasitics": None,
    "spice_options": {"method": "gear", "reltol": 1e-3, "abstol": 1e-6, "vntol": 1e-4},
    "output": {"csv_dt": 1e-6, "zoom_cycles": 3, "svg": True},
    "recovery_band": 0.01,
}
PARASITIC_DEFAULTS = {"L_loop": 20e-9, "R_loop": 0.5, "C_oss": 200e-12, "cycles": 3, "t_step": 2e-9}

EXAMPLE_PARAMS: dict = {
    "name": "sic-buck-400v-200v-5kw",
    "description": "400 V -> 200 V, 5 kW, 50 kHz SiC synchronous buck; L = 267 uH, Cout = 60 uF film; "
                   "closed-loop PI stand-in with 2 ms soft start and a 50 % -> 100 % load step at 7 ms.",
    "vin": 400.0, "vout_ref": 200.0, "fs": 50e3,
    "closed_loop": True, "duty": 0.5,
    "dead_time": 200e-9,
    "L": 267e-6, "L_dcr": 10e-3,
    "Cout": 60e-6, "Cout_esr": 10e-3,
    "Cin": 100e-6, "Cin_esr": 10e-3,
    "L_in": 10e-6, "R_in": 0.1,
    "Rds_on_hs": 25e-3, "Rds_on_ls": 25e-3,
    "body_diode_vf": 3.5, "body_diode_rs": 0.02,
    "load_R": 16.0, "load_step": {"t": 7e-3, "R_parallel": 16.0, "t_rise": 1e-6},
    "soft_start_ms": 2.0,
    "t_end": 16e-3,
    "metric_cycles": 10,
    "parasitics": {"L_loop": 20e-9, "R_loop": 0.5, "C_oss": 200e-12, "cycles": 3, "t_step": 2e-9},
}

WANTED_VECTORS = ["time", "out", "sw", "in", "duty", "ref", "l1#branch", "vhs#branch", "vls#branch",
                  "vdls#branch", "vcin#branch", "vcout#branch", "vld#branch", "vin#branch"]
COMPARED_METRICS = ["vout_mean", "vout_pkpk", "il_mean", "il_pkpk", "il_peak", "il_min", "il_rms",
                    "i_hs_rms", "i_ls_rms", "i_cin_rms", "i_cout_rms", "i_in_mean", "p_cond_hs",
                    "p_cond_ls", "p_diode_deadtime"]

# dataviz reference palette (categorical slots 1-3, light surface)
SERIES_COLOURS = ("#2a78d6", "#eb6834", "#1baf7a")
SURFACE, INK, INK_SECONDARY, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"


# ---------------------------------------------------------------- parameters ----------
def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def resolve_params(params: dict) -> dict:
    """Merge user parameters over ``DEFAULTS``, derive load/duty values and validate them."""
    p = _merge(DEFAULTS, params or {})
    unknown = set(p) - set(DEFAULTS) - {"description"}
    if unknown:
        raise ValueError(f"unknown parameters: {sorted(unknown)}")
    if p["pwm"] == "auto":
        p["pwm"] = "comparator" if p["closed_loop"] else "pwl"
    if p["t_step"] is None:
        # comparator PWM resolves switching instants to the solver grid: finer default
        p["t_step"] = 50e-9 if p["pwm"] == "comparator" else 100e-9
    for key in ("vin", "vout_ref", "fs", "L", "Cout", "t_end", "t_step"):
        if not (isinstance(p[key], (int, float)) and p[key] > 0):
            raise ValueError(f"parameter {key} must be a positive number")
    if not 0 < p["vout_ref"] < p["vin"]:
        raise ValueError("buck needs 0 < vout_ref < vin")
    if p["load_R"] is None:
        p["load_R"] = p["vout_ref"] ** 2 / (p["load_P"] or 1.0) if p["load_P"] else \
            p["vout_ref"] ** 2 / 5000.0
    if p["duty"] is None:
        p["duty"] = p["vout_ref"] / p["vin"]
    if not 0 < p["duty"] < 1:
        raise ValueError("duty must lie strictly between 0 and 1")
    p["period"] = 1.0 / p["fs"]
    if 2 * p["dead_time"] >= (1 - p["duty"]) * p["period"]:
        raise ValueError("dead time leaves no low-side conduction interval")
    p["i_out_nominal"] = p["vout_ref"] / final_load_resistance(p)
    if p["body_diode_i_ref"] is None:
        p["body_diode_i_ref"] = max(p["i_out_nominal"], 1.0)
    p["soft_start"] = float(p["soft_start_ms"]) * 1e-3
    if p["pwm"] not in ("pwl", "comparator"):
        raise ValueError("pwm must be 'auto', 'pwl' or 'comparator'")
    if p["closed_loop"] and p["pwm"] == "pwl":
        raise ValueError("closed-loop control needs the comparator PWM")
    step = p["load_step"]
    if step is not None:
        if not isinstance(step, dict) or "t" not in step:
            raise ValueError("load_step must be a dict with key t")
        if ("R_parallel" in step) == ("I" in step):
            raise ValueError("load_step needs exactly one of R_parallel or I")
        step.setdefault("t_rise", 1e-6)
        step.setdefault("t_off", None)
        step.setdefault("v_fold", 10.0)
    if p["parasitics"] is not None:
        p["parasitics"] = _merge(PARASITIC_DEFAULTS, p["parasitics"])
    if p["metric_cycles"] * p["period"] > p["t_end"]:
        raise ValueError("metric_cycles exceeds the simulated time")
    return p


def final_load_resistance(p: dict) -> float:
    """Load resistance seen at the end of the run (after a resistive load step, if any)."""
    r = float(p["load_R"])
    step = p.get("load_step")
    if step and step.get("R_parallel") and step.get("t_off") is None and step["t"] < p["t_end"]:
        r = r * step["R_parallel"] / (r + step["R_parallel"])
    return r


def load_params(path: Path | str) -> dict:
    """Read a JSON parameter file and resolve it against the defaults."""
    return resolve_params(json.loads(Path(path).read_text(encoding="utf-8-sig")))


def diode_saturation_current(p: dict) -> float:
    """Is of the N=2 body-diode model giving ``body_diode_vf`` at ``body_diode_i_ref``."""
    knee = p["body_diode_vf"] - p["body_diode_i_ref"] * p["body_diode_rs"]
    if knee <= 0:
        raise ValueError("body_diode_vf must exceed body_diode_i_ref * body_diode_rs")
    return p["body_diode_i_ref"] * math.exp(-knee / (2 * THERMAL_VOLTAGE))


# ---------------------------------------------------------------- deck ----------------
def _g(value: float) -> str:
    return f"{value:.12g}"


def gate_pwl(p: dict, duty_at, t_end: float) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """PWL corner lists for the HS and LS gates; ``duty_at(t)`` is sampled at each period start.

    HS conducts for duty*T from the period start; LS conducts from the HS turn-off plus the
    dead time to the period end minus the dead time. Pulses shorter than the gate edge are
    dropped (minimum on-time), gate edges are centred on the nominal instants.
    """
    T, td, tr = p["period"], p["dead_time"], p["gate_edge"]
    hs, ls = [(0.0, 0.0)], [(0.0, 0.0)]
    for k in range(int(math.ceil(t_end / T)) + 1):
        t0 = k * T
        ton = float(duty_at(t0)) * T
        if ton > tr:
            hs += [(t0 - tr / 2, 0.0), (t0 + tr / 2, 1.0), (t0 + ton - tr / 2, 1.0), (t0 + ton + tr / 2, 0.0)]
        on, off = t0 + ton + td, t0 + T - td
        if off - on > tr:
            ls += [(on - tr / 2, 0.0), (on + tr / 2, 1.0), (off - tr / 2, 1.0), (off + tr / 2, 0.0)]
    return _monotonic(hs), _monotonic(ls)


def _monotonic(points):
    out, last = [], -1.0
    for t, v in points:
        t = max(t, 0.0)
        if t <= last:
            t = last + 1e-12
        out.append((t, v))
        last = t
    return out


def _pwl_lines(name: str, nodes: str, points, per_line: int = 16) -> list[str]:
    chunks = [" ".join(f"{_g(t)} {v:g}" for t, v in points[i:i + per_line]) for i in range(0, len(points), per_line)]
    lines = [f"{name} {nodes} PWL({chunks[0]}"] + [f"+ {chunk}" for chunk in chunks[1:]]
    lines[-1] += ")"
    return lines


def build_deck(p: dict) -> list[str]:
    """ngspice deck for the behavioural power stage described by resolved parameters ``p``."""
    T, td, tss = p["period"], p["dead_time"], p["soft_start"]
    ramp = f"min(1, time/{_g(tss)})" if tss > 0 else "1"
    lines = [f"* AIPE behavioural synchronous buck: {p['name']}",
             f"Vin src 0 DC {_g(p['vin'])}",
             f"Lin src inf {_g(max(p['L_in'], 1e-12))}",
             f"Rin inf in {_g(max(p['R_in'], 1e-6))}",
             f"Cin in cinx {_g(p['Cin'])}", f"Rcin cinx cins {_g(max(p['Cin_esr'], 1e-6))}", "Vcin cins 0 0",
             "Vhs in hs_a 0", "Shs hs_a sw ghs 0 SWHS", "Dhs sw hs_a DBODY",
             "Sls sw ls_a gls 0 SWLS", "Dls dls_a sw DBODY", "Vdls ls_a dls_a 0", "Vls ls_a 0 0",
             f"L1 sw lx {_g(p['L'])}", f"Rdcr lx out {_g(max(p['L_dcr'], 1e-6))}",
             f"Cout out cx {_g(p['Cout'])}", f"Resr cx cs {_g(max(p['Cout_esr'], 1e-6))}", "Vcout cs 0 0",
             "Vld out ld 0", f"Rload ld 0 {_g(p['load_R'])}"]
    step = p["load_step"]
    if step:
        t_on, t_rise = step["t"], step["t_rise"]
        gate = f"PWL(0 0 {_g(t_on)} 0 {_g(t_on + t_rise)} 1"
        if step["t_off"] is not None:
            gate += f" {_g(step['t_off'])} 1 {_g(step['t_off'] + t_rise)} 0"
        lines.append(f"Vgld gld 0 {gate})")
        if step.get("R_parallel"):
            lines += ["Sld ld ld2 gld 0 SWLD", f"Rstep ld2 0 {_g(step['R_parallel'])}",
                      ".model SWLD SW(Ron=1e-3 Roff=1e9 Vt=0.5 Vh=0.1)"]
        else:
            lines.append(f"Bstep ld 0 I = V(gld)*{_g(step['I'])}*min(1, max(0, V(out))/{_g(step['v_fold'])})")
    if p["closed_loop"]:
        pi = p["pi"]
        r_fb = 1e3
        c_fb = 1.0 / (2 * math.pi * pi["fb_filter_hz"] * r_fb) if pi["fb_filter_hz"] > 0 else 1e-15
        err = "(V(ref)-V(fb))"
        feedforward = f"V(ref)/{_g(p['vin'])} + " if pi.get("feedforward", True) else ""
        windup = (f"((V(duty) >= {_g(pi['d_max'])}) && (V(ref) > V(fb))) || "
                  f"((V(duty) <= {_g(pi['d_min'])}) && (V(ref) < V(fb)))")
        lines += [f"Bref ref 0 V = {_g(p['vout_ref'])}*{ramp}",
                  f"Rfb out fb {_g(r_fb)}", f"Cfb fb 0 {_g(c_fb)}",
                  f"Bint 0 vint I = ({windup}) ? 0 : {_g(pi['ki'])}*{err}",
                  "Cint vint 0 1", "Rint vint 0 1G", ".ic V(vint)=0",
                  f"Bduty duty 0 V = max({_g(pi['d_min'])}, min({_g(pi['d_max'])}, "
                  f"{feedforward}{_g(pi['kp'])}*{err} + V(vint)))"]
    else:
        lines.append(f"Bduty duty 0 V = {_g(p['duty'])}*{ramp}")
    if p["pwm"] == "comparator":
        lines += [f"Vsaw saw 0 PULSE(0 1 0 {_g(T - 2e-9)} 1n 1n {_g(T)})",
                  "Bghs ghs 0 V = (V(duty) > V(saw)) ? 1 : 0",
                  f"Bgls gls 0 V = ((V(saw) > V(duty) + {_g(td / T)}) && (V(saw) < {_g(1 - td / T)})) ? 1 : 0"]
    else:
        duty_at = (lambda t: p["duty"] * min(1.0, t / tss)) if tss > 0 else (lambda t: p["duty"])
        hs, ls = gate_pwl(p, duty_at, p["t_end"])
        lines += _pwl_lines("Vghs", "ghs 0", hs) + _pwl_lines("Vgls", "gls 0", ls)
    opts = " ".join(f"{k}={v}" for k, v in p["spice_options"].items())
    lines += ["Rghs ghs 0 1Meg", "Rgls gls 0 1Meg",
              f".model SWHS SW(Ron={_g(p['Rds_on_hs'])} Roff=1e6 Vt=0.5 Vh=0.1)",
              f".model SWLS SW(Ron={_g(p['Rds_on_ls'])} Roff=1e6 Vt=0.5 Vh=0.1)",
              f".model DBODY D(Is={diode_saturation_current(p):.6g} N=2 Rs={_g(p['body_diode_rs'])})",
              ".ic V(out)=0",
              f".options {opts}",
              f".tran {_g(p['t_step'])} {_g(p['t_end'])}",
              ".end"]
    return lines


def build_parasitic_deck(p: dict, duty: float, x0) -> list[str]:
    """Short steady-state deck with loop inductance and Coss for the switch-node overshoot estimate."""
    q = p["parasitics"]
    T = p["period"]
    t_end = q["cycles"] * T
    duty_at = lambda t: duty  # noqa: E731
    hs, ls = gate_pwl(p, duty_at, t_end)
    lines = [f"* AIPE parasitic overshoot study: {p['name']}",
             f"Vin in 0 DC {_g(p['vin'])}", f"Cin in cinx {_g(p['Cin'])} ic={_g(p['vin'])}",
             f"Rcin cinx 0 {_g(max(p['Cin_esr'], 1e-6))}"]
    if q["L_loop"] > 0:
        lines += [f"Lloop in hsn {_g(q['L_loop'])}", f"Rloop hsn hsr {_g(max(q['R_loop'], 1e-6))}", "Vhs hsr hs_a 0"]
    else:
        lines.append("Vhs in hs_a 0")
    lines += ["Shs hs_a sw ghs 0 SWHS", "Dhs sw hs_a DBODY", f"Coss_hs hs_a sw {_g(q['C_oss'])}",
              "Sls sw ls_a gls 0 SWLS", "Dls dls_a sw DBODY", "Vdls ls_a dls_a 0", "Vls ls_a 0 0",
              f"Coss_ls sw ls_a {_g(q['C_oss'])}",
              f"L1 sw lx {_g(p['L'])} ic={_g(float(x0[0]))}", f"Rdcr lx out {_g(max(p['L_dcr'], 1e-6))}",
              f"Cout out cx {_g(p['Cout'])} ic={_g(float(x0[1]))}", f"Resr cx cs {_g(max(p['Cout_esr'], 1e-6))}",
              "Vcout cs 0 0", f"Rload out 0 {_g(final_load_resistance(p))}"]
    lines += _pwl_lines("Vghs", "ghs 0", hs) + _pwl_lines("Vgls", "gls 0", ls)
    opts = " ".join(f"{k}={v}" for k, v in p["spice_options"].items())
    lines += ["Rghs ghs 0 1Meg", "Rgls gls 0 1Meg",
              f".model SWHS SW(Ron={_g(p['Rds_on_hs'])} Roff=1e6 Vt=0.5 Vh=0.1)",
              f".model SWLS SW(Ron={_g(p['Rds_on_ls'])} Roff=1e6 Vt=0.5 Vh=0.1)",
              f".model DBODY D(Is={diode_saturation_current(p):.6g} N=2 Rs={_g(p['body_diode_rs'])})",
              f".options {opts}",
              f".tran {_g(q['t_step'] / 10)} {_g(t_end)} 0 {_g(q['t_step'])} uic",
              ".end"]
    return lines


# ---------------------------------------------------------------- numpy model ---------
def _expm(matrix: np.ndarray) -> np.ndarray:
    """Matrix exponential by scaling and squaring with a 24-term Taylor series."""
    norm = float(np.max(np.sum(np.abs(matrix), axis=1)))
    squarings = max(0, int(math.ceil(math.log2(norm / 0.5)))) if norm > 0 else 0
    scaled = matrix / (2.0 ** squarings)
    n = matrix.shape[0]
    result, term = np.eye(n), np.eye(n)
    for k in range(1, 25):
        term = term @ scaled / k
        result = result + term
    for _ in range(squarings):
        result = result @ result
    return result


def _affine_step(A: np.ndarray, b: np.ndarray, h: float) -> tuple[np.ndarray, np.ndarray]:
    """Exact propagator of x' = A x + b over ``h``: x(h) = Phi x(0) + gamma."""
    n = A.shape[0]
    aug = np.zeros((n + 1, n + 1))
    aug[:n, :n] = A * h
    aug[:n, n] = b * h
    exp = _expm(aug)
    return exp[:n, :n], exp[:n, n]


def _steady_state(p: dict, duty: float, r_load: float, samples_per_cycle: int, vin: float | None = None):
    """Periodic steady state of [iL, vC] with intervals HS-on, dead, LS-on, dead (CCM, iL > 0).

    ``vin`` defaults to the source voltage minus the DC drop over ``R_in`` (two fixed-point
    passes); the input filter dynamics themselves are not part of this model.
    """
    L, C, esr, dcr, T, td = p["L"], p["Cout"], p["Cout_esr"], p["L_dcr"], p["period"], p["dead_time"]
    if vin is None:
        vin = p["vin"]
        for _ in range(2):
            x0, t, X, mode = _steady_state(p, duty, r_load, 200, vin)
            i_in = _cycle_mean(t, np.where(mode == "hs", X[:, 0], 0.0))
            vin = p["vin"] - p["R_in"] * i_in
    k = r_load / (r_load + esr)

    def system(r_switch: float, u: float):
        """State matrices for one switch state: series resistance ``r_switch`` and switch-node drive ``u``."""
        A = np.array([[-(dcr + r_switch + esr * k) / L, -k / L], [k / C, -1.0 / ((r_load + esr) * C)]])
        return A, np.array([u / L, 0.0])

    knee = p["body_diode_vf"] - p["body_diode_i_ref"] * p["body_diode_rs"]
    intervals = [(system(p["Rds_on_hs"], vin), duty * T, "hs"),
                 (system(p["body_diode_rs"], -knee), td, "diode"),
                 (system(p["Rds_on_ls"], 0.0), (1 - duty) * T - 2 * td, "ls"),
                 (system(p["body_diode_rs"], -knee), td, "diode")]
    phi, gamma, steps = np.eye(2), np.zeros(2), []
    for (A, b), h, mode in intervals:
        if h <= 0:
            continue
        P, g = _affine_step(A, b, h)
        steps.append((A, b, h, mode))
        phi, gamma = P @ phi, P @ gamma + g
    x0 = np.linalg.solve(np.eye(2) - phi, gamma)
    times, states, modes = [], [], []
    t, x = 0.0, x0.copy()
    for A, b, h, mode in steps:
        n = max(2, int(round(h / T * samples_per_cycle)))
        P, g = _affine_step(A, b, h / n)
        xs = [x]
        for _ in range(n):
            xs.append(P @ xs[-1] + g)
        times.append(t + np.linspace(0.0, h, n + 1))
        states.append(np.array(xs))
        modes.append(np.full(n + 1, mode))
        t, x = t + h, xs[-1]
    return x0, np.concatenate(times), np.vstack(states), np.concatenate(modes)


def _cycle_mean(t: np.ndarray, y: np.ndarray) -> float:
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(t)) / (t[-1] - t[0]))


def numpy_switched_model(params: dict, samples_per_cycle: int = 4000) -> dict:
    """Exact periodic steady state of the ideal switched buck (independent of ngspice).

    Uses the final load, the resolved open-loop duty or, for closed-loop parameters, the duty
    that makes the cycle-mean output equal ``vout_ref`` (secant iteration). Returns the
    same ripple, peak, RMS and conduction-loss metrics as ``analyse`` plus the start-of-cycle
    state ``x0`` used to initialise the parasitic study. The input source is ideal here, so
    ``i_cin_rms`` is the AC component of the high-side current.
    """
    p = resolve_params(params) if "period" not in params else params
    r_load = final_load_resistance(p)
    duty = p["duty"]
    if p["closed_loop"]:
        d0, d1 = p["vout_ref"] / p["vin"], min(0.98, p["vout_ref"] / p["vin"] * 1.02)
        f0 = _steady_state_vout(p, d0, r_load) - p["vout_ref"]
        for _ in range(12):
            f1 = _steady_state_vout(p, d1, r_load) - p["vout_ref"]
            if abs(f1) < 1e-6 or f1 == f0:
                break
            d0, d1, f0 = d1, d1 - f1 * (d1 - d0) / (f1 - f0), f1
            d1 = min(max(d1, 1e-3), 0.99)
        duty = d1
    x0, t, X, mode = _steady_state(p, duty, r_load, samples_per_cycle)
    il, vc = X[:, 0], X[:, 1]
    esr = p["Cout_esr"]
    vout = r_load * (vc + esr * il) / (r_load + esr)
    i_cout = (r_load * il - vc) / (r_load + esr)
    i_hs = np.where(mode == "hs", il, 0.0)
    i_ls_channel = np.where(mode == "ls", il, 0.0)
    i_diode = np.where(mode == "diode", il, 0.0)
    i_ls_total = i_ls_channel + i_diode
    mean = lambda y: _cycle_mean(t, y)  # noqa: E731
    rms = lambda y: math.sqrt(_cycle_mean(t, y ** 2))  # noqa: E731
    i_in_mean = mean(i_hs)
    v_diode = p["body_diode_vf"] - p["body_diode_i_ref"] * p["body_diode_rs"] + i_diode * p["body_diode_rs"]
    result = {
        "method": "exact matrix-exponential periodic steady state (4 intervals per cycle)",
        "duty": float(duty), "load_R": r_load, "ccm": bool(il.min() > 0),
        "vout_mean": mean(vout), "vout_pkpk": float(vout.max() - vout.min()),
        "il_mean": mean(il), "il_pkpk": float(il.max() - il.min()), "il_peak": float(il.max()),
        "il_min": float(il.min()), "il_rms": rms(il),
        "i_hs_rms": rms(i_hs), "i_ls_rms": rms(i_ls_total), "i_ls_channel_rms": rms(i_ls_channel),
        "i_diode_mean": mean(i_diode), "i_cin_rms": rms(i_hs - i_in_mean), "i_cout_rms": rms(i_cout),
        "i_in_mean": i_in_mean,
        "p_cond_hs": rms(i_hs) ** 2 * p["Rds_on_hs"], "p_cond_ls": rms(i_ls_channel) ** 2 * p["Rds_on_ls"],
        "p_diode_deadtime": mean(i_diode * v_diode), "p_l_dcr": rms(il) ** 2 * p["L_dcr"],
        "p_cout_esr": rms(i_cout) ** 2 * esr, "p_cin_esr": rms(i_hs - i_in_mean) ** 2 * p["Cin_esr"],
        "formula_il_pkpk": p["vout_ref"] * (1 - duty) / (p["L"] * p["fs"]),
        "x0": [float(x0[0]), float(x0[1])],
    }
    if not result["ccm"]:
        result["warning"] = "inductor current reverses; dead-time diode assignment assumes iL > 0"
    return result


def _steady_state_vout(p: dict, duty: float, r_load: float) -> float:
    x0, t, X, _ = _steady_state(p, duty, r_load, 400)
    esr = p["Cout_esr"]
    vout = r_load * (X[:, 1] + esr * X[:, 0]) / (r_load + esr)
    return _cycle_mean(t, vout)


# ---------------------------------------------------------------- analysis ------------
def window_stats(t: np.ndarray, y: np.ndarray, t0: float, t1: float) -> dict:
    """Time-weighted mean/RMS and extrema of a non-uniform waveform over [t0, t1]."""
    inside = (t > t0) & (t < t1)
    tt = np.concatenate(([t0], t[inside], [t1]))
    yy = np.concatenate(([np.interp(t0, t, y)], y[inside], [np.interp(t1, t, y)]))
    dt = np.diff(tt)
    mean = float(np.sum(0.5 * (yy[1:] + yy[:-1]) * dt) / (t1 - t0))
    rms = math.sqrt(float(np.sum(0.5 * (yy[1:] ** 2 + yy[:-1] ** 2) * dt) / (t1 - t0)))
    return {"mean": mean, "rms": rms, "min": float(yy.min()), "max": float(yy.max()),
            "pkpk": float(yy.max() - yy.min())}


def _cycle_average(t: np.ndarray, y: np.ndarray, period: float, dt: float):
    """Resample onto ``dt`` and apply a centred one-period moving average (valid region only)."""
    grid = uniform_grid(float(t[0]), float(t[-1]), dt)
    values = resample(t, y, grid)
    n = max(1, int(round(period / dt)))
    if values.size <= n:
        return grid, values, values.copy()
    csum = np.cumsum(np.concatenate(([0.0], values)))
    averaged = (csum[n:] - csum[:-n]) / n
    offset = (n - 1) // 2
    return grid[offset:offset + averaged.size], values[offset:offset + averaged.size], averaged


def analyse(p: dict, v: dict) -> dict:
    """Metrics from the ngspice vectors over the last ``metric_cycles`` complete periods."""
    t = v["time"]
    T = p["period"]
    t_last = math.floor(t[-1] / T + 1e-9) * T
    t0 = t_last - p["metric_cycles"] * T
    t1 = t_last
    il, vout, vsw, vin_bus = v["l1#branch"], v["out"], v["sw"], v["in"]
    i_hs, i_ls, i_diode = v["vhs#branch"], -v["vls#branch"], v["vdls#branch"]
    i_cin, i_cout, i_load, i_in = v["vcin#branch"], v["vcout#branch"], v["vld#branch"], -v["vin#branch"]
    i_ls_channel = i_ls - i_diode
    s = {name: window_stats(t, y, t0, t1) for name, y in
         [("vout", vout), ("il", il), ("vsw", vsw), ("vin_bus", vin_bus), ("i_hs", i_hs), ("i_ls", i_ls),
          ("i_ls_channel", i_ls_channel), ("i_diode", i_diode), ("i_cin", i_cin), ("i_cout", i_cout),
          ("i_load", i_load), ("i_in", i_in), ("duty", v["duty"])]}
    p_out = window_stats(t, vout * i_load, t0, t1)["mean"]
    p_in = window_stats(t, p["vin"] * i_in, t0, t1)["mean"]
    p_diode = window_stats(t, i_diode * (-vsw), t0, t1)["mean"]
    m = {
        "window": {"t0": t0, "t1": t1, "cycles": p["metric_cycles"]},
        "duty": s["duty"]["mean"],
        "vout_mean": s["vout"]["mean"], "vout_pkpk": s["vout"]["pkpk"], "vout_min": s["vout"]["min"],
        "vout_max": s["vout"]["max"],
        "vin_bus_mean": s["vin_bus"]["mean"], "vin_bus_pkpk": s["vin_bus"]["pkpk"],
        "il_mean": s["il"]["mean"], "il_pkpk": s["il"]["pkpk"], "il_peak": s["il"]["max"], "il_min": s["il"]["min"],
        "il_rms": s["il"]["rms"],
        "i_hs_rms": s["i_hs"]["rms"], "i_hs_mean": s["i_hs"]["mean"], "i_hs_peak": s["i_hs"]["max"],
        "i_ls_rms": s["i_ls"]["rms"], "i_ls_mean": s["i_ls"]["mean"], "i_ls_channel_rms": s["i_ls_channel"]["rms"],
        "i_diode_mean": s["i_diode"]["mean"],
        "i_cin_rms": s["i_cin"]["rms"], "i_cin_mean": s["i_cin"]["mean"],
        "i_cout_rms": s["i_cout"]["rms"], "i_load_mean": s["i_load"]["mean"],
        "i_in_mean": s["i_in"]["mean"], "i_in_rms": s["i_in"]["rms"],
        "vsw_max": s["vsw"]["max"], "vsw_min": s["vsw"]["min"],
        "p_out": p_out, "p_in": p_in, "p_loss_total": p_in - p_out,
        "efficiency": p_out / p_in if p_in > 0 else None,
        "p_cond_hs": s["i_hs"]["rms"] ** 2 * p["Rds_on_hs"],
        "p_cond_ls": s["i_ls_channel"]["rms"] ** 2 * p["Rds_on_ls"],
        "p_diode_deadtime": p_diode,
        "p_diode_deadtime_estimate": 2 * p["dead_time"] * p["fs"] * p["body_diode_vf"] * s["il"]["mean"],
        "p_l_dcr": s["il"]["rms"] ** 2 * p["L_dcr"],
        "p_cout_esr": s["i_cout"]["rms"] ** 2 * p["Cout_esr"],
        "p_cin_esr": s["i_cin"]["rms"] ** 2 * p["Cin_esr"],
        "p_r_in": s["i_in"]["rms"] ** 2 * p["R_in"],
        "i_cin_rms_formula": math.sqrt(max(s["i_hs"]["rms"] ** 2 - s["i_hs"]["mean"] ** 2, 0.0)),
    }
    m["p_loss_modelled_sum"] = sum(m[k] for k in ("p_cond_hs", "p_cond_ls", "p_diode_deadtime", "p_l_dcr",
                                                    "p_cout_esr", "p_cin_esr", "p_r_in"))
    # steady-state check: cycle-averaged output over the last 50 periods and the comparator PWM resolution
    grid, _, avg = _cycle_average(t, vout, T, T / 50)
    tail = grid >= t1 - min(50 * T, t1 - t[0])
    lsb = p["vin"] * p["t_step"] / T if p["pwm"] == "comparator" else 0.0
    m["steady_state"] = {"vout_cycle_avg_pkpk_V": float(np.ptp(avg[tail])) if tail.any() else None,
                         "pwm_lsb_V": lsb,
                         "limit_cycle_suspected": bool(tail.any() and lsb > 0 and np.ptp(avg[tail]) > 0.5 * lsb),
                         "energy_balance_pct": 100 * (p_in - p_out - m["p_loss_modelled_sum"]) / p_out if p_out else None}
    # startup
    step = p["load_step"]
    t_startup_end = step["t"] if step else t[-1]
    pre = t <= t_startup_end
    target = p["vout_ref"] if p["closed_loop"] else m["vout_mean"]
    peak = float(vout[pre].max())
    m["startup"] = {"vout_peak": peak, "target": target, "overshoot_V": peak - target,
                    "overshoot_pct": 100 * (peak - target) / target,
                    "il_peak": float(il[pre].max()), "soft_start_s": p["soft_start"]}
    if step:
        m["load_step"] = _load_step_metrics(p, t, vout, il, i_load, m["vout_mean"], step)
    return m


def _load_step_metrics(p, t, vout, il, i_load, v_final, step):
    T = p["period"]
    t_step = step["t"]
    grid, raw, avg = _cycle_average(t, vout, T, T / 50)
    band = p["recovery_band"] * p["vout_ref"]
    pre = (grid >= t_step - 5 * T) & (grid <= t_step)
    v_pre = float(np.mean(avg[pre])) if pre.any() else float("nan")
    post = grid >= t_step
    dev = avg[post] - v_final
    idx = int(np.argmax(np.abs(dev)))
    excursion = float(dev[idx])
    outside = np.abs(dev) > band
    recovered = bool(outside.size and not outside[-1])
    t_rec = float(grid[post][np.where(outside)[0][-1]] - t_step) if outside.any() and recovered else \
        (0.0 if recovered else None)
    i_pre = window_stats(t, i_load, max(t_step - 5 * T, t[0]), t_step)["mean"]
    return {"t_step": t_step, "i_load_before": i_pre, "i_load_after": window_stats(t, i_load, t[-1] - 5 * T, t[-1])["mean"],
            "vout_before_avg": v_pre, "vout_final_avg": v_final,
            "excursion_avg_V": excursion, "excursion_avg_pct": 100 * excursion / p["vout_ref"],
            "t_excursion": float(grid[post][idx]),
            "vout_raw_min_after": float(vout[t >= t_step].min()), "vout_raw_max_after": float(vout[t >= t_step].max()),
            "il_peak_after": float(il[t >= t_step].max()),
            "recovery_band_V": band, "recovered": recovered, "recovery_time_s": t_rec}


def compare(spice: dict, model: dict) -> list[dict]:
    """Side-by-side table of the shared metrics with the relative deviation in percent."""
    rows = []
    for key in COMPARED_METRICS:
        a, b = spice.get(key), model.get(key)
        if a is None or b is None:
            continue
        dev = 100 * (a - b) / abs(b) if abs(b) > 1e-12 else None
        rows.append({"metric": key, "spice": a, "numpy": b, "deviation_pct": dev})
    return rows


# ---------------------------------------------------------------- simulation ----------
def simulate(params: dict, out_dir: Path | str | None = None) -> dict:
    """Run the ngspice power-stage transient, analyse it, cross-check it and write outputs.

    Returns a results dict (parameters, metrics, numpy cross-check, comparison, optional
    load-step / parasitic results, runtimes, ngspice warnings, written files). When
    ``out_dir`` is given, the deck, waveform CSVs, SVG plots and ``summary.json`` are written there.
    """
    p = resolve_params(params)
    deck = build_deck(p)
    spice = NgSpice()
    start = time.perf_counter()
    vectors = spice.run(deck, vectors=WANTED_VECTORS, expected_end=p["t_end"])
    runtime = time.perf_counter() - start
    metrics = analyse(p, vectors)
    model = numpy_switched_model(p)
    results = {
        "label": "AI-GENERATED BEHAVIOURAL SIMULATION - HUMAN REVIEW REQUIRED",
        "name": p["name"], "description": p.get("description", ""),
        "ngspice": {"version": spice.version, "library": str(spice.library_path), "points": int(vectors["time"].size),
                    "runtime_s": runtime, "warnings": spice.warnings},
        "parameters": {k: v for k, v in p.items() if k != "description"},
        "metrics": metrics, "numpy_model": model, "comparison": compare(metrics, model),
        "notes": [
            "Switches are ideal Ron/Roff elements: no switching, gate or Coss losses in the main run.",
            "Body diodes: exponential model (N=2) fitted to body_diode_vf at body_diode_i_ref.",
            "The PI controller is an averaged stand-in for the DSP firmware, not the F28335 implementation.",
            "Closed-loop gate instants align to the solver grid (t_step); open-loop gates use exact PWL breakpoints.",
            "Comparator PWM has a resolution of vin*t_step/T volts at the output; the PI may hunt (limit cycle) by up "
            "to that amount - see metrics.steady_state.",
            "Metrics are taken over the last metric_cycles periods; the load step must have recovered by then.",
        ],
    }
    if p["parasitics"] is not None:
        results["parasitic_study"] = simulate_parasitic(p, model, spice)
    if out_dir is not None:
        results["files"] = write_outputs(Path(out_dir), p, deck, vectors, results)
    return results


def simulate_parasitic(p: dict, model: dict, spice: NgSpice | None = None) -> dict:
    """Few-cycle run from the exact steady state with L_loop + C_oss; overshoot is an estimate only."""
    q = p["parasitics"]
    deck = build_parasitic_deck(p, model["duty"], model["x0"])
    spice = spice or NgSpice()
    start = time.perf_counter()
    v = spice.run(deck, vectors=["time", "sw", "hs_a", "l1#branch", "vhs#branch", "vls#branch"],
                  expected_end=q["cycles"] * p["period"])
    runtime = time.perf_counter() - start
    t, vsw, il = v["time"], v["sw"], v["l1#branch"]
    v_ds_hs = v["hs_a"] - vsw
    after_first = t >= p["period"]
    z = math.sqrt(q["L_loop"] / q["C_oss"]) if q["C_oss"] > 0 else 0.0
    f_ring = 1 / (2 * math.pi * math.sqrt(q["L_loop"] * q["C_oss"])) if q["L_loop"] > 0 and q["C_oss"] > 0 else None
    result = {
        "deck": deck, "runtime_s": runtime, "points": int(t.size), "warnings": spice.warnings,
        "L_loop": q["L_loop"], "R_loop": q["R_loop"], "C_oss": q["C_oss"], "cycles": q["cycles"],
        "vsw_max": float(vsw[after_first].max()), "vsw_min": float(vsw[after_first].min()),
        "vsw_overshoot_above_vin": float(vsw[after_first].max() - p["vin"]),
        "v_ds_hs_max": float(v_ds_hs[after_first].max()),
        "il_min": float(il[after_first].min()), "il_max": float(il[after_first].max()),
        "estimate_hs_turn_off_overshoot_V": float(il[after_first].max()) * z,
        "estimate_sw_turn_on_step_overshoot_V": p["vin"] if q["L_loop"] > 0 else 0.0,
        "ring_frequency_Hz": f_ring,
        "note": "Ideal-switch commutation with lumped L_loop and C_oss: HS turn-off rings L_loop with C_oss "
                "(estimate I*sqrt(L/C)); HS turn-on applies a voltage step to the L_loop/C_oss(LS) tank, which "
                "undamped would overshoot by Vin. Real di/dt, diode capacitance, package and gate-loop "
                "parasitics are not modelled. Use as an order-of-magnitude indicator only.",
        "vectors": {"time": t, "sw": vsw, "v_ds_hs": v_ds_hs, "il": il},
    }
    return result


# ---------------------------------------------------------------- outputs -------------
def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items() if k != "vectors"}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return f if math.isfinite(f) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, Path):
        return str(value)
    return value


def write_csv(path: Path, columns: dict[str, np.ndarray]) -> Path:
    """Write named equal-length arrays as a CSV with a header row."""
    names = list(columns)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(names)
        for row in zip(*(columns[name] for name in names)):
            writer.writerow([f"{value:.9g}" for value in row])
    return path


def _nice_ticks(lo: float, hi: float, count: int = 5) -> list[float]:
    if hi <= lo:
        hi = lo + 1.0
    raw = (hi - lo) / count
    magnitude = 10 ** math.floor(math.log10(raw))
    step = min((s for s in (1, 2, 2.5, 5, 10) if s * magnitude >= raw), default=10) * magnitude
    first = math.ceil(lo / step) * step
    ticks = []
    while first <= hi + step * 1e-9:
        ticks.append(round(first, 12))
        first += step
    return ticks


def _fmt(value: float) -> str:
    text = f"{value:.6g}"
    return "0" if text in ("-0", "-0.0") else text


def _decimate(x: np.ndarray, y: np.ndarray, bins: int = 1500):
    if x.size <= 2 * bins:
        return x, y
    edges = np.linspace(0, x.size, bins + 1).astype(int)
    xs, ys = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a:
            continue
        seg_y = y[a:b]
        i_min, i_max = int(np.argmin(seg_y)), int(np.argmax(seg_y))
        for i in sorted({i_min, i_max}):
            xs.append(x[a + i])
            ys.append(seg_y[i])
    return np.array(xs), np.array(ys)


def write_svg_plot(path: Path, title: str, x: np.ndarray, series: list[tuple[str, np.ndarray]], y_label: str,
                   x_unit: str = "auto", reference: float | None = None, width: int = 960, height: int = 400) -> Path:
    """Pure-Python SVG line chart (one unit per chart, legend for two or more series)."""
    x = np.asarray(x, float)
    span = float(x[-1] - x[0]) if x.size > 1 else 1.0
    if x_unit == "auto":
        x_unit = "ms" if span >= 1e-3 else "us"
    scale = {"s": 1.0, "ms": 1e3, "us": 1e6, "ns": 1e9}[x_unit]
    xs = x * scale
    left, right, top, bottom = 72, 28, 44, 48
    plot_w, plot_h = width - left - right, height - top - bottom
    ys_all = np.concatenate([np.asarray(y, float) for _, y in series] + ([np.array([reference])] if reference is not None else []))
    y_lo, y_hi = float(np.nanmin(ys_all)), float(np.nanmax(ys_all))
    pad = (y_hi - y_lo) * 0.08 or abs(y_hi) * 0.1 or 1.0
    y_lo, y_hi = y_lo - pad, y_hi + pad
    x_lo, x_hi = float(xs[0]), float(xs[-1]) if span > 0 else float(xs[0]) + 1.0
    sx = lambda v: left + (v - x_lo) / (x_hi - x_lo) * plot_w  # noqa: E731
    sy = lambda v: top + (y_hi - v) / (y_hi - y_lo) * plot_h  # noqa: E731
    font = "font-family='Inter, Helvetica, Arial, sans-serif'"
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
           f"<rect width='{width}' height='{height}' fill='{SURFACE}'/>",
           f"<text x='{left}' y='24' {font} font-size='14' font-weight='600' fill='{INK}'>{_esc(title)}</text>",
           f"<text x='{left}' y='{top - 8}' {font} font-size='11' fill='{INK_SECONDARY}'>{_esc(y_label)}</text>"]
    for tick in _nice_ticks(y_lo, y_hi):
        yy = sy(tick)
        out.append(f"<line x1='{left}' y1='{yy:.1f}' x2='{left + plot_w}' y2='{yy:.1f}' stroke='{GRID}' stroke-width='1'/>")
        out.append(f"<text x='{left - 8}' y='{yy + 4:.1f}' {font} font-size='11' text-anchor='end' fill='{INK_SECONDARY}'>{_fmt(tick)}</text>")
    for tick in _nice_ticks(x_lo, x_hi, 8):
        xx = sx(tick)
        out.append(f"<line x1='{xx:.1f}' y1='{top + plot_h}' x2='{xx:.1f}' y2='{top + plot_h + 4}' stroke='{INK_SECONDARY}' stroke-width='1'/>")
        out.append(f"<text x='{xx:.1f}' y='{top + plot_h + 18}' {font} font-size='11' text-anchor='middle' fill='{INK_SECONDARY}'>{_fmt(tick)}</text>")
    out.append(f"<line x1='{left}' y1='{top + plot_h}' x2='{left + plot_w}' y2='{top + plot_h}' stroke='{INK_SECONDARY}' stroke-width='1'/>")
    out.append(f"<text x='{left + plot_w / 2:.1f}' y='{height - 10}' {font} font-size='11' text-anchor='middle' fill='{INK_SECONDARY}'>time / {x_unit}</text>")
    out.append(f"<clipPath id='plot'><rect x='{left}' y='{top}' width='{plot_w}' height='{plot_h}'/></clipPath>")
    if reference is not None:
        yy = sy(reference)
        out.append(f"<line x1='{left}' y1='{yy:.1f}' x2='{left + plot_w}' y2='{yy:.1f}' stroke='{INK_SECONDARY}' stroke-width='1' opacity='0.6'/>")
        out.append(f"<text x='{left + plot_w - 4}' y='{yy - 4:.1f}' {font} font-size='10' text-anchor='end' fill='{INK_SECONDARY}'>ref {_fmt(reference)}</text>")
    for index, (label, y) in enumerate(series):
        colour = SERIES_COLOURS[index % len(SERIES_COLOURS)]
        dx, dy = _decimate(xs, np.asarray(y, float))
        points = " ".join(f"{sx(a):.1f},{sy(b):.1f}" for a, b in zip(dx, dy))
        out.append(f"<polyline clip-path='url(#plot)' fill='none' stroke='{colour}' stroke-width='2' "
                   f"stroke-linejoin='round' stroke-linecap='round' points='{points}'/>")
    if len(series) > 1:
        lx = left + plot_w - 8
        for index, (label, _) in reversed(list(enumerate(series))):
            colour = SERIES_COLOURS[index % len(SERIES_COLOURS)]
            text_w = 7 * len(label) + 28
            lx -= text_w
            out.append(f"<line x1='{lx}' y1='{top - 10}' x2='{lx + 16}' y2='{top - 10}' stroke='{colour}' stroke-width='2'/>")
            out.append(f"<text x='{lx + 22}' y='{top - 6}' {font} font-size='11' fill='{INK}'>{_esc(label)}</text>")
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    return path


def _esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;")


def write_outputs(out_dir: Path, p: dict, deck: list[str], v: dict, results: dict) -> dict:
    """Write deck, resolved parameters, waveform CSVs, SVG plots and summary.json into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    files["deck"] = out_dir / f"{p['name']}.cir"
    files["deck"].write_text("\n".join(deck) + "\n", encoding="utf-8")
    files["parameters"] = out_dir / "parameters.json"
    files["parameters"].write_text(json.dumps(_jsonable(p), indent=2) + "\n", encoding="utf-8")
    t = v["time"]
    T = p["period"]
    signals = {"vout_V": v["out"], "vsw_V": v["sw"], "vin_bus_V": v["in"], "il_A": v["l1#branch"],
               "i_hs_A": v["vhs#branch"], "i_ls_A": -v["vls#branch"], "i_diode_ls_A": v["vdls#branch"],
               "i_cin_A": v["vcin#branch"], "i_cout_A": v["vcout#branch"], "i_in_A": -v["vin#branch"],
               "i_load_A": v["vld#branch"], "duty": v["duty"]}
    if "ref" in v:
        signals["vref_V"] = v["ref"]
    grid = uniform_grid(float(t[0]), float(t[-1]), p["output"]["csv_dt"])
    files["waveforms_csv"] = write_csv(out_dir / "waveforms.csv",
                                       {"time_s": grid, **{k: resample(t, y, grid) for k, y in signals.items()}})
    w = results["metrics"]["window"]
    zoom0 = w["t1"] - p["output"]["zoom_cycles"] * T
    zoom = (t >= zoom0) & (t <= w["t1"])
    files["zoom_csv"] = write_csv(out_dir / "waveforms_zoom.csv", {"time_s": t[zoom], **{k: y[zoom] for k, y in signals.items()}})
    if p["output"]["svg"]:
        ref = p["vout_ref"] if p["closed_loop"] else None
        files["svg_vout"] = write_svg_plot(out_dir / "vout.svg", f"{p['name']}: output voltage", t, [("vout", v["out"])], "V", reference=ref)
        files["svg_il"] = write_svg_plot(out_dir / "il.svg", f"{p['name']}: inductor current", t, [("iL", v["l1#branch"])], "A")
        tz = t[zoom] - zoom0
        files["svg_zoom_vout"] = write_svg_plot(out_dir / "zoom_vout.svg", f"{p['name']}: output ripple, last {p['output']['zoom_cycles']} cycles",
                                                tz, [("vout", v["out"][zoom])], "V", x_unit="us")
        files["svg_zoom_currents"] = write_svg_plot(out_dir / "zoom_currents.svg", f"{p['name']}: switch and inductor currents",
                                                    tz, [("i_hs", v["vhs#branch"][zoom]), ("i_ls", -v["vls#branch"][zoom]), ("iL", v["l1#branch"][zoom])], "A", x_unit="us")
        files["svg_zoom_capacitors"] = write_svg_plot(out_dir / "zoom_capacitor_currents.svg", f"{p['name']}: capacitor currents",
                                                      tz, [("i_cin", v["vcin#branch"][zoom]), ("i_cout", v["vcout#branch"][zoom])], "A", x_unit="us")
        files["svg_zoom_vsw"] = write_svg_plot(out_dir / "zoom_vsw.svg", f"{p['name']}: switch node", tz, [("vsw", v["sw"][zoom])], "V", x_unit="us")
        if p["load_step"]:
            ts = p["load_step"]["t"]
            sel = (t >= ts - 1e-3) & (t <= t[-1])
            grid_s, raw, avg = _cycle_average(t[sel], v["out"][sel], T, T / 50)
            files["svg_load_step"] = write_svg_plot(out_dir / "load_step.svg", f"{p['name']}: load step response",
                                                    grid_s, [("vout", raw), ("vout cycle average", avg)], "V", reference=p["vout_ref"])
        study = results.get("parasitic_study")
        if study:
            vec = study["vectors"]
            sel = vec["time"] >= T
            files["svg_parasitic"] = write_svg_plot(out_dir / "parasitic_vsw.svg", f"{p['name']}: switch node with L_loop (estimate only)",
                                                    vec["time"][sel], [("vsw", vec["sw"][sel]), ("v_ds_hs", vec["v_ds_hs"][sel])], "V", x_unit="us")
    files["summary"] = out_dir / "summary.json"
    summary = _jsonable({k: val for k, val in results.items() if k != "files"})
    summary["files"] = {k: str(path.relative_to(out_dir)) for k, path in files.items()}
    files["summary"].write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return files


def format_report(results: dict) -> str:
    """Compact human-readable summary of a results dict."""
    m, model = results["metrics"], results["numpy_model"]
    lines = [f"{results['name']}: ngspice {results['ngspice']['version']} {results['ngspice']['points']} points in "
             f"{results['ngspice']['runtime_s']:.2f} s", f"{'metric':22s}{'spice':>12s}{'numpy':>12s}{'dev %':>9s}"]
    for row in results["comparison"]:
        dev = "" if row["deviation_pct"] is None else f"{row['deviation_pct']:+.2f}"
        lines.append(f"{row['metric']:22s}{row['spice']:12.4f}{row['numpy']:12.4f}{dev:>9s}")
    lines.append(f"efficiency {100 * m['efficiency']:.2f} % (p_in {m['p_in']:.1f} W, p_out {m['p_out']:.1f} W, "
                 f"modelled losses {m['p_loss_modelled_sum']:.1f} W)")
    ss = m["steady_state"]
    lines.append(f"steady state: cycle-averaged vout pk-pk {ss['vout_cycle_avg_pkpk_V']:.3f} V over the last 50 periods "
                 f"(PWM LSB {ss['pwm_lsb_V']:.2f} V, limit cycle suspected: {ss['limit_cycle_suspected']}); "
                 f"energy balance residual {ss['energy_balance_pct']:+.2f} % of p_out")
    lines.append(f"startup overshoot {m['startup']['overshoot_V']:+.2f} V ({m['startup']['overshoot_pct']:+.2f} %)")
    if "load_step" in m:
        ls = m["load_step"]
        rec = "not recovered" if ls["recovery_time_s"] is None else f"recovered in {1e3 * ls['recovery_time_s']:.2f} ms"
        lines.append(f"load step at {1e3 * ls['t_step']:.1f} ms: {ls['i_load_before']:.1f} -> {ls['i_load_after']:.1f} A, "
                     f"excursion {ls['excursion_avg_V']:+.2f} V ({ls['excursion_avg_pct']:+.1f} %), {rec} "
                     f"(band {ls['recovery_band_V']:.2f} V)")
    study = results.get("parasitic_study")
    if study:
        lines.append(f"parasitic study (estimate only): vsw max {study['vsw_max']:.0f} V, v_ds_hs max "
                     f"{study['v_ds_hs_max']:.0f} V; analytic HS turn-off I*sqrt(L/C) = "
                     f"{study['estimate_hs_turn_off_overshoot_V']:.0f} V, undamped turn-on step = "
                     f"{study['estimate_sw_turn_on_step_overshoot_V']:.0f} V; {study['runtime_s']:.2f} s")
    if results["ngspice"]["warnings"]:
        lines.append("ngspice warnings: " + " | ".join(results["ngspice"]["warnings"][:5]))
    return "\n".join(lines)


def main(argv=None) -> int:
    """CLI: run a parameter file (default: the built-in 5 kW example) and write results."""
    parser = argparse.ArgumentParser(description="Behavioural synchronous-buck simulation (ngspice + numpy)")
    parser.add_argument("params", nargs="?", help="JSON parameter file (default: built-in 5 kW SiC example)")
    parser.add_argument("--out", help="output directory (default: examples/.../simulation/results/<name>)")
    parser.add_argument("--open-loop", action="store_true", help="force open loop at the resolved duty")
    parser.add_argument("--numpy-only", action="store_true", help="skip ngspice; print the exact model only")
    parser.add_argument("--write-example", metavar="PATH", help="write the example parameter JSON and exit")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=JSON", help="override a top-level parameter")
    args = parser.parse_args(argv)
    if args.write_example:
        Path(args.write_example).parent.mkdir(parents=True, exist_ok=True)
        Path(args.write_example).write_text(json.dumps(EXAMPLE_PARAMS, indent=2) + "\n", encoding="utf-8")
        print(args.write_example)
        return 0
    raw = json.loads(Path(args.params).read_text(encoding="utf-8-sig")) if args.params else copy.deepcopy(EXAMPLE_PARAMS)
    for item in args.set:
        key, _, value = item.partition("=")
        raw[key] = json.loads(value)
    if args.open_loop:
        raw["closed_loop"] = False
        raw["name"] = raw.get("name", "buck") + "-open-loop"
    if args.numpy_only:
        print(json.dumps(_jsonable(numpy_switched_model(raw)), indent=2))
        return 0
    if not ngspice_available():
        print("ngspice shared library not found; set AIPE_NGSPICE_DLL or configure KiCad", file=sys.stderr)
        return 2
    out_dir = Path(args.out) if args.out else EXAMPLE_DIR / "results" / raw.get("name", "buck")
    results = simulate(raw, out_dir)
    print(format_report(results))
    print("written:", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
