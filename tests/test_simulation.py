"""Tests for the behavioural buck simulation layer.

The numpy switched-state model, deck generation, metric extraction and the runner's
pure-Python helpers run everywhere. Tests that need the KiCad-bundled ngspice shared
library skip cleanly when it cannot be located; a skip is never reported as a pass.
"""

import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from automation.simulation import buck_stage, ngspice_runner
from automation.simulation.buck_stage import (EXAMPLE_PARAMS, analyse, build_deck, build_parasitic_deck, compare,
                                              gate_pwl, numpy_switched_model, resolve_params, window_stats)
from automation.simulation.ngspice_runner import (classify_messages, find_ngspice_library, ngspice_available,
                                                  normalise_deck, resample, uniform_grid)

OPEN_LOOP = {"name": "test-open-loop", "vin": 400.0, "vout_ref": 200.0, "fs": 50e3, "duty": 0.5,
             "L": 267e-6, "Cout": 60e-6, "load_R": 8.0, "closed_loop": False, "soft_start_ms": 1.0,
             "t_end": 6e-3, "load_step": None, "parasitics": None}
NGSPICE_SKIP = "ngspice shared library not found (set AIPE_NGSPICE_DLL or configure KiCad)"


class NumpyModelTests(unittest.TestCase):
    def test_ripple_matches_textbook_formula_within_5_percent(self):
        p = resolve_params(OPEN_LOOP)
        result = numpy_switched_model(p)
        formula = p["vout_ref"] * (1 - p["duty"]) / (p["L"] * p["fs"])
        self.assertAlmostEqual(formula, 7.4906, places=3)
        self.assertLess(abs(result["il_pkpk"] - formula) / formula, 0.05)
        self.assertTrue(result["ccm"])
        self.assertGreater(result["il_peak"], result["il_mean"])

    def test_ideal_elements_reproduce_formula_closely(self):
        ideal = dict(OPEN_LOOP, L_dcr=0.0, Cout_esr=0.0, Rds_on_hs=0.0, Rds_on_ls=0.0, dead_time=0.0, R_in=0.0)
        p = resolve_params(ideal)
        result = numpy_switched_model(p)
        formula = p["vout_ref"] * (1 - p["duty"]) / (p["L"] * p["fs"])
        self.assertLess(abs(result["il_pkpk"] - formula) / formula, 0.002)
        self.assertAlmostEqual(result["vout_mean"], 200.0, delta=0.05)
        self.assertAlmostEqual(result["vout_pkpk"], result["il_pkpk"] / (8 * p["fs"] * p["Cout"]), delta=0.003)

    def test_metric_identities(self):
        result = numpy_switched_model(resolve_params(OPEN_LOOP))
        io = result["il_mean"]
        self.assertAlmostEqual(result["il_rms"] ** 2, io ** 2 + result["il_pkpk"] ** 2 / 12, delta=0.01 * io ** 2)
        self.assertAlmostEqual(result["i_hs_rms"] ** 2 + result["i_ls_rms"] ** 2, result["il_rms"] ** 2,
                               delta=0.01 * result["il_rms"] ** 2)
        self.assertAlmostEqual(result["i_cin_rms"], math.sqrt(0.5 * 0.5) * io, delta=0.03 * io)
        self.assertAlmostEqual(result["i_cout_rms"], result["il_pkpk"] / math.sqrt(12), delta=0.02)
        self.assertAlmostEqual(result["p_cond_hs"], result["i_hs_rms"] ** 2 * 25e-3, places=9)

    def test_closed_loop_duty_solution_hits_reference(self):
        p = resolve_params(dict(OPEN_LOOP, closed_loop=True, load_R=16.0,
                                load_step={"t": 3e-3, "R_parallel": 16.0}))
        result = numpy_switched_model(p)
        self.assertAlmostEqual(result["vout_mean"], 200.0, delta=1e-3)
        self.assertGreater(result["duty"], 0.5)
        self.assertAlmostEqual(result["load_R"], 8.0)

    def test_example_parameters_resolve(self):
        p = resolve_params(EXAMPLE_PARAMS)
        self.assertEqual(p["pwm"], "comparator")
        self.assertAlmostEqual(p["i_out_nominal"], 25.0)
        self.assertEqual(p["parasitics"]["cycles"], 3)
        with self.assertRaises(ValueError):
            resolve_params(dict(OPEN_LOOP, bogus=1))
        with self.assertRaises(ValueError):
            resolve_params(dict(OPEN_LOOP, closed_loop=True, pwm="pwl"))
        with self.assertRaises(ValueError):
            resolve_params(dict(OPEN_LOOP, load_step={"t": 1e-3}))


class DeckTests(unittest.TestCase):
    def test_open_loop_deck_uses_pwl_gates_and_models(self):
        p = resolve_params(OPEN_LOOP)
        deck = build_deck(p)
        text = "\n".join(deck)
        self.assertTrue(deck[0].startswith("*"))
        self.assertEqual(deck[-1], ".end")
        for needle in ("Shs hs_a sw ghs 0 SWHS", ".model SWHS SW(Ron=0.025", ".model DBODY D(Is=", "Vghs ghs 0 PWL(",
                       "Vgls gls 0 PWL(", ".ic V(out)=0", ".options method=gear", ".tran 1e-07 0.006"):
            self.assertIn(needle, text)
        self.assertNotIn("Vsaw", text)
        sense = [line for line in deck if line.startswith("V") and len(line.split()) == 4 and line.split()[-1] == "0"]
        self.assertEqual(len(sense), 6)  # Vcin, Vhs, Vdls, Vls, Vcout, Vld zero-volt current probes

    def test_closed_loop_deck_has_comparator_and_pi(self):
        p = resolve_params(dict(OPEN_LOOP, closed_loop=True, load_step={"t": 3e-3, "R_parallel": 8.0}))
        text = "\n".join(build_deck(p))
        for needle in ("Vsaw saw 0 PULSE(0 1 0", "Bghs ghs 0 V = (V(duty) > V(saw)) ? 1 : 0", "Bint 0 vint I =",
                       "Bduty duty 0 V = max(0, min(0.95, V(ref)/400 + 0.0002*", "Sld ld ld2 gld 0 SWLD", "Rstep ld2 0 8"):
            self.assertIn(needle, text)

    def test_gate_pwl_timing(self):
        p = resolve_params(dict(OPEN_LOOP, soft_start_ms=0.0))
        hs, ls = gate_pwl(p, lambda t: 0.5, 3 * p["period"])
        times = [t for t, _ in hs]
        self.assertTrue(all(b > a for a, b in zip(times, times[1:])))
        T, tr, td = p["period"], p["gate_edge"], p["dead_time"]
        # second period: on-ramp centred on T, off-ramp centred on 1.5 T
        self.assertAlmostEqual(hs[5][0], T - tr / 2, places=15)
        self.assertAlmostEqual(hs[7][0], T + 0.5 * T - tr / 2, places=15)
        self.assertAlmostEqual(ls[5][0], T + 0.5 * T + td - tr / 2, places=15)
        self.assertAlmostEqual(ls[7][0], 2 * T - td - tr / 2, places=15)

    def test_parasitic_deck_uses_initial_conditions(self):
        p = resolve_params(dict(OPEN_LOOP, parasitics={"L_loop": 20e-9}))
        text = "\n".join(build_parasitic_deck(p, 0.5, [21.0, 199.0]))
        for needle in ("Lloop in hsn 2e-08", "Coss_hs hs_a sw 2e-10", "L1 sw lx 0.000267 ic=21", "Cout out cx 6e-05 ic=199", "uic"):
            self.assertIn(needle, text)


class AnalysisTests(unittest.TestCase):
    def synthetic_vectors(self, p):
        T = p["period"]
        t = np.arange(0.0, p["t_end"] + T / 400, T / 400)
        phase = (t / T) % 1.0
        il = 25.0 + 7.5 * np.where(phase < 0.5, phase / 0.5 - 0.5, 0.5 - (phase - 0.5) / 0.5)
        hs_on = phase < 0.5
        v = {"time": t, "out": 200.0 + 0.15 * np.sin(2 * np.pi * t / T), "sw": np.where(hs_on, 400.0, 0.0),
             "in": np.full_like(t, 400.0), "duty": np.full_like(t, 0.5), "l1#branch": il,
             "vhs#branch": np.where(hs_on, il, 0.0), "vls#branch": -np.where(hs_on, 0.0, il),
             "vdls#branch": np.zeros_like(t), "vcin#branch": np.where(hs_on, il, 0.0) - 12.5,
             "vcout#branch": il - 25.0, "vld#branch": np.full_like(t, 25.0), "vin#branch": np.full_like(t, -12.5)}
        return v

    def test_window_metrics_from_synthetic_waveforms(self):
        p = resolve_params(dict(OPEN_LOOP, t_end=2e-3))
        m = analyse(p, self.synthetic_vectors(p))
        self.assertAlmostEqual(m["il_mean"], 25.0, places=2)
        self.assertAlmostEqual(m["il_pkpk"], 7.5, places=2)
        self.assertAlmostEqual(m["il_rms"], math.sqrt(25 ** 2 + 7.5 ** 2 / 12), places=2)
        self.assertAlmostEqual(m["i_hs_rms"], math.sqrt(0.5 * (25 ** 2 + 7.5 ** 2 / 12)), places=1)
        self.assertAlmostEqual(m["i_cin_rms"], 12.5, delta=0.2)
        self.assertAlmostEqual(m["vout_pkpk"], 0.3, places=3)
        self.assertAlmostEqual(m["p_out"], 5000.0, delta=1.0)
        self.assertEqual(m["window"]["cycles"], 10)
        self.assertAlmostEqual(m["window"]["t1"] - m["window"]["t0"], 10 * p["period"], places=12)

    def test_window_stats_time_weighting(self):
        t = np.array([0.0, 1.0, 1.0001, 2.0])
        y = np.array([0.0, 0.0, 10.0, 10.0])
        stats = window_stats(t, y, 0.0, 2.0)
        self.assertAlmostEqual(stats["mean"], 5.0, places=2)
        self.assertAlmostEqual(stats["pkpk"], 10.0)

    def test_compare_table(self):
        rows = compare({"il_pkpk": 7.4, "vout_mean": 199.0}, {"il_pkpk": 7.5, "vout_mean": 200.0, "extra": 1})
        self.assertEqual([r["metric"] for r in rows], ["vout_mean", "il_pkpk"])
        self.assertAlmostEqual(rows[1]["deviation_pct"], -100 / 75, places=6)


class RunnerHelperTests(unittest.TestCase):
    def test_normalise_deck_adds_title_and_end(self):
        self.assertEqual(normalise_deck([".tran 1u 1m", "R1 a 0 1k", ".end", ".end"]),
                         ["* AIPE deck", ".tran 1u 1m", "R1 a 0 1k", ".end"])
        with self.assertRaises(ValueError):
            normalise_deck([])

    def test_message_classification(self):
        errors, warnings = classify_messages(["stderr Warning: can't find the initialization file spinit.",
                                              "stderr Error: unknown subckt: xbogus a b nosuch",
                                              "stderr doAnalyses: TRAN:  Timestep too small; time = 1e-5",
                                              "stdout Doing analysis at TEMP = 27.000000"])
        self.assertEqual(len(errors), 2)
        self.assertEqual(len(warnings), 1)

    def test_library_override_must_exist(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"AIPE_NGSPICE_DLL": str(Path(folder) / "absent.dll")}):
                with self.assertRaises(FileNotFoundError):
                    find_ngspice_library({})
                self.assertFalse(ngspice_available({}))
            fake = Path(folder) / "ngspice.dll"
            fake.touch()
            with patch.dict(os.environ, {"AIPE_NGSPICE_DLL": str(fake)}):
                self.assertEqual(find_ngspice_library({}), fake.resolve())

    def test_resampler(self):
        grid = uniform_grid(0.0, 1.0, 0.25)
        self.assertEqual(grid.size, 5)
        values = resample(np.array([0.0, 0.5, 0.5, 1.0]), np.array([0.0, 1.0, 1.0, 2.0]), grid)
        np.testing.assert_allclose(values, [0.0, 0.5, 1.0, 1.5, 2.0])
        with self.assertRaises(ValueError):
            uniform_grid(0.0, 1.0, 0.0)


@unittest.skipUnless(ngspice_available(), NGSPICE_SKIP)
class NgSpiceTests(unittest.TestCase):
    def test_rc_transient_matches_analytic(self):
        spice = ngspice_runner.NgSpice()
        vectors = spice.run(["* rc", "V1 a 0 DC 2", "R1 a b 1k", "C1 b 0 1u", ".ic V(b)=0", ".tran 1u 4m"],
                            expected_end=4e-3)
        self.assertIn("b", vectors)
        self.assertAlmostEqual(vectors["b"][-1], 2 * (1 - math.exp(-4)), delta=0.01)
        self.assertGreater(vectors["time"].size, 100)

    def test_error_deck_raises_and_runner_recovers(self):
        spice = ngspice_runner.NgSpice()
        with self.assertRaises(ngspice_runner.NgSpiceError):
            spice.run(["* bad", "V1 a 0 DC 1", "R1 a b 1k", "Xbogus a b nosuch", ".tran 1u 1m"])
        with self.assertRaises(ngspice_runner.NgSpiceError):
            spice.run(["* short", "V1 a 0 DC 1", "R1 a b 1k", "C1 b 0 1u", ".tran 1u 1m"], expected_end=4e-3)
        vectors = spice.run(["* ok", "V1 a 0 DC 1", "R1 a b 1k", "C1 b 0 1u", ".tran 1u 1m"], expected_end=1e-3)
        self.assertAlmostEqual(vectors["time"][-1], 1e-3, places=9)

    def test_open_loop_buck_agrees_with_numpy_model(self):
        with tempfile.TemporaryDirectory(prefix="aipe sim ") as folder:
            results = buck_stage.simulate(OPEN_LOOP, Path(folder))
            m, model = results["metrics"], results["numpy_model"]
            self.assertLess(abs(m["il_pkpk"] - model["il_pkpk"]) / model["il_pkpk"], 0.03)
            self.assertLess(abs(m["vout_mean"] - model["vout_mean"]) / model["vout_mean"], 0.02)
            self.assertLess(abs(m["i_cin_rms"] - model["i_cin_rms"]) / model["i_cin_rms"], 0.05)
            self.assertLess(m["vout_pkpk"], 2.0)
            self.assertGreater(results["ngspice"]["runtime_s"], 0.0)
            summary = json.loads((Path(folder) / "summary.json").read_text())
            self.assertEqual(summary["metrics"]["window"]["cycles"], 10)
            for name in ("waveforms.csv", "waveforms_zoom.csv", "vout.svg", "il.svg", "zoom_currents.svg"):
                self.assertTrue((Path(folder) / name).exists(), name)
            self.assertTrue((Path(folder) / "test-open-loop.cir").exists())

    def test_closed_loop_regulates_and_reports_load_step(self):
        params = dict(OPEN_LOOP, name="test-closed-loop", closed_loop=True, load_R=16.0, t_end=14e-3,
                      load_step={"t": 6e-3, "R_parallel": 16.0}, parasitics={"L_loop": 20e-9, "cycles": 2})
        results = buck_stage.simulate(params)
        m = results["metrics"]
        self.assertAlmostEqual(m["vout_mean"], 200.0, delta=2.0)
        self.assertIn("load_step", m)
        self.assertLess(m["load_step"]["excursion_avg_V"], 0.0)
        self.assertGreater(results["parasitic_study"]["vsw_max"], 400.0)


if __name__ == "__main__":
    unittest.main()
