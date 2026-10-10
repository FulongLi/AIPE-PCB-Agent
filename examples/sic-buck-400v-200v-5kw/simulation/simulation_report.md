**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# V2 power-stage simulation campaign: 400 V -> 200 V, 5 kW, 50 kHz SiC synchronous buck

Behavioural ngspice campaign (KiCad-bundled ngspice-46 through `automation.simulation.ngspice_runner`, decks and
metrics from `automation.simulation.buck_stage`, both unmodified) with an exact numpy switched-model cross-check.
Every parameter comes from the orchestrator baseline [design_decisions.json](../design/design_decisions.json)
(schema 3) or, where the baseline is silent, from the research records
[mosfet.json](../design/research/mosfet.json), [capacitors.json](../design/research/capacitors.json),
[inductor.json](../design/research/inductor.json), [gate_driver.json](../design/research/gate_driver.json) after
their `verify_*.json` corrections. Task-provided values and added assumptions are labelled. Nothing here is
hardware-validated; the model has no SiC device physics, no switching losses, no thermal coupling and no firmware.
Parameter files: [models/](models/); driver: [results/run_campaign.py](results/run_campaign.py); per-run outputs:
[results/](results/) (deck, parameters, waveform CSVs, SVG plots, summary.json, campaign_metrics.json);
campaign summary: [results/campaign_summary.json](results/campaign_summary.json) and
[results/campaign_log.txt](results/campaign_log.txt).

## 1. Summary

| Quantity (400 V / 25 A unless stated) | Simulated | Analytical reference | Design-basis limit | Status |
|---|---|---|---|---|
| Inductor ripple dI_L, 360 / 400 / 440 V, 272 uH | 6.51 / 7.35 / 8.03 App | 6.5 / 7.3 / 8.0 App (baseline operating_points) | 30 % target at 400 V (29 %) | agrees within 1 % |
| Worst ripple / peak, 440 V, 27.5 A, 235 uH | 9.30 App / 32.15 A | 9.0 App / 32.0 A (baseline worst) | OC trip 37.5 A; I_sat(30 %) 37.3 nominal / 35 worst | 2.85 A below the worst I_sat |
| Output ripple | 0.16-0.22 Vpp | 0.25 Vpp (capacitors.json, 9.92 A ripple) | <= 2.0 Vpp | pass, 9x margin |
| Input bus ripple (36 uF, lab-lead model) | 3.56-3.61 Vpp (25 A), 3.91-3.97 Vpp (27.5 A) | 3.5 / 3.9 Vpp | <= 2 % = 8 Vpp | pass (0.9-1.0 %) |
| C_in RMS per part (two B32776G8206) | 6.4-6.5 A (25 A), 7.0-7.1 A (27.5 A) | 6.92 A worst (capacitors.json) | 14.5 A rating | pass |
| C_out RMS per part | 0.94-1.34 A | 1.43 A worst | 23.5 A rating | pass |
| MOSFET conduction, both devices, 48.5 mohm | 29.7-29.9 W (25 A); 35.1 W at 57.2 mohm; 35.9-36.1 W (27.5 A) | 2 x 15.3 = 30.6 W (mosfet.json) | - | agrees within 3 % |
| Dead-time body-diode loss, 250 / 300 ns | 2.89 / 3.47 W (25 A); 3.25-3.27 W (27.5 A) | 2.9 W (mosfet.json, KR-GD-009) | - | agrees |
| Inductor DCR loss (16 mohm, 100 C) | 10.06-10.12 W (25 A); 12.16-12.22 W (27.5 A) | 10.0 / 12.1 W (inductor.json) | - | agrees |
| 12.5 A load step, cascaded controller, 360 / 400 / 440 V | -7.74 / -7.54 (up), +7.80 / +7.59 V (down); recovery 0.75-0.77 ms | 8.1 V at 2.3 kHz (7.4 at 2.5 kHz, 9.2 at 2.0 kHz) | <= 10 V, <= 5 ms | pass |
| 25 A -> 0 A dump, 400 / 440 V | peak 216.2 / 215.8 V (+16.1 / +15.7 V) | 216.1 V at 2.3 kHz (215-218 V, CR-04) | < 230 V output OVP | pass, 13.8 V margin |
| Startup, 20 ms soft start, 12.5 A / 25 A load | +0.60 / +0.41 V overshoot; I_L peak 17.2 / 29.7 A | - | within the 1 % static band; < OVP | pass |
| Module single-loop PI reference (97 Hz) | -16.2 V, recovery 5.0 ms, I_L 38.5 A | - | 10 V / 5 ms / 37.5 A OC | FAILS: inner current loop required |
| Switch-node overshoot (parasitic study, ideal switch) | +344..+348 V (R_loop 0.5 ohm), +246 V (2 ohm): energy-transfer bound, not a prediction | L x di/dt = 62 / 88 / 125 V at 25 / 35 / 50 nH and 2.5 A/ns | 90 V allowance, 530 V recurring peak | L_loop <= 36 nH at 2.5 A/ns; double-pulse test required |
| Conduction-class losses (simulated) + switching-class (analytical) | 43.1 W + 32-36 W = 75-79 W -> 98.4-98.5 % | 77-99 W (baseline efficiency budget) | >= 98.0 % target, 97.5 % floor | consistent; not a measured efficiency |

Twenty transient runs (0.9-2.0 s each open loop, 6.7-31 s each closed loop) plus four parasitic cases; total wall
time 187 s for the final full campaign on the host shared with the other agents (122 s when the host was idle).
All runs completed without ngspice warnings or convergence failures.

## 2. Model and method

**Power stage (module deck, `buck_stage.build_deck`).** Source `Vin` -> lead `L_in` 10 uH / `R_in` 50 mohm ->
input bank `C_in` 36 uF + ESR; high-side and low-side voltage-controlled switches (`SW(Ron Roff=1e6 Vt=0.5
Vh=0.1)`, ideal hysteretic switches, no gate, no C_oss, no switching loss) each with an anti-parallel exponential
body diode (`D(Is N=2 Rs)`), inductor `L` with series DCR, output bank `C_out` + ESR, resistive load with an
optional switched parallel resistor for load events. Zero-volt probes give the HS, LS, LS-diode, C_in, C_out,
load and source currents. Open-loop runs use PWL gate sources with exact 10 ns edges (HS on for D T from the
period start, LS on from the HS turn-off + t_dead to the period end - t_dead). Closed-loop runs use a 0-1 V
sawtooth comparator PWM whose switching instants align to the 25 ns solver grid, i.e. a PWM resolution of
V_in x t_step / T = 0.45-0.55 V at the output; the module reports whether the loop limit-cycles against it.
Solver: `method=gear reltol=1e-3 abstol=1e-6 vntol=1e-4`; `t_step` 100 ns (open loop) / 25 ns (closed loop) /
2 ns (parasitic decks).

**Metrics (`buck_stage.analyse`).** Time-weighted mean, RMS and extrema over the last ten complete periods,
conduction losses I_rms^2 R from the probe currents, dead-time loss as the mean of i_diode x v_diode, cycle-averaged
output voltage for the transient excursions, startup overshoot, energy balance. The driver adds event metrics for
load-step-off and dump events (the module's own load-step metric covers only the step-on), a startup block for
every closed-loop run, limit checks and closed-form "textbook" values computed from the run's own parameters.

**Cross-check (`buck_stage.numpy_switched_model`).** Periodic steady state of the ideal switched state equations
through exact matrix exponentials (four intervals per cycle: HS on, dead time, LS on, dead time), independent of
ngspice. The open-loop duty of every steady-state run is the duty at which this exact model yields 200.0 V at the
run's load (secant iteration), so the open-loop runs sit at 200.0 V rather than at D = V_out/V_in; the resolved
values are stored in the model files (`duty` 0.5050 at 400 V / 25 A against the ideal 0.5000).

**Controller.** The module ships a single voltage-loop PI (an averaged stand-in for the DSP firmware). The
baseline requires a 2.0-2.5 kHz outer voltage-loop crossover *with an inner current loop*
(assumptions_accepted.voltage_loop_crossover_Hz, controller.pwm.outer_loop_crossover_Hz). With L 272 uH and
C_out 108 uF the LC resonance is 929 Hz (Z0 1.59 ohm, Q 5.0 at 8 ohm), so a single PI cannot cross above the
resonance with phase margin; the analytical loop gain of the module PI (section 6.4) crosses at 97 Hz and is
marginal (0.6 dB gain margin at half load). For the runs marked `cascade` the driver therefore replaces the eight
controller lines of the module deck by a cascaded average-current-mode controller (section 6.4); the power stage,
PWM, switch and diode models and probes stay the module's own. The run `cl_400V_singleloop_modulePI` keeps the
module PI as a reference. **No firmware exists** (assumptions register A-34): both controllers are behavioural
stand-ins.

**Parasitic study (`buck_stage.simulate_parasitic`).** Three-cycle deck started from the exact steady state with a
lumped commutation-loop inductance `L_loop` + `R_loop` in series with the HS drain and `C_oss` 130 pF across each
device. The behavioural switch commutates in about one solver step, so the deck's overshoot is the energy-transfer
bound of an instantaneous commutation damped only by `R_loop`; the module documents it as an order-of-magnitude
indicator. The driver measures the actual deck di/dt and tabulates L x di/dt at the gate-driver design edge.

**Body-diode model note (module finding).** ngspice floors the diode saturation current at about 1e-28 A; the
module's N = 2 fit of V_SD = 4.6 V at 25 A with the default R_s = 20 mohm needs I_s = 9e-34 A and therefore gives
4.00 V at 25 A (standalone DC sweep: 24.9 A at 4.0 V), under-reporting the dead-time loss by 13 %. All runs use
`body_diode_rs` = 44 mohm, which places the fitted I_s at 9.9e-29 A (inside the valid range) and reproduces 4.60 V
at 25 A (4.37 V at 20 A, 4.90 V at 31.6 A, standalone check). The 44 mohm slope is a model-fitting choice, not a
datasheet value; the datasheet gives V_SD 4.6 V at 175 C / 19.6 A (fetched-datasheet) and the 29-32 A value the
MOSFET verification asked for remains unread.

## 3. Parameters and their provenance

| Parameter | Value used | Source | Verification level |
|---|---|---|---|
| V_in | 360 / 400 / 440 V; V_out,ref 200 V; f_s 50 kHz | baseline requirements and operating range | requirement |
| Load | 8.0 ohm (25 A), 7.27 ohm (27.5 A overload), 16 ohm (12.5 A), 80 ohm (2.5 A), 1 Mohm (no load), 200 kohm (bleeder, one dump case) | baseline; capacitors.bleeders.output | requirement / fetched-datasheet (bleeder value) |
| L | 272 uH nominal (25 A); 235 uH worst (AL -8 %, datasheet-minimum bias curve); 319 uH at 0 A | baseline magnetics.inductor.L_uH_*; inductor.json | analytically-checked (core data fetched-datasheet; no measurement); fixed per run, no L(i) roll-off in the model |
| DCR | 16.0 mohm (100 C) | baseline dcr_mohm_20C_100C | analytically-checked |
| C_out / ESR | 108 uF (2 x 60 uF -10 %) / 4.0 mohm | baseline output_film; ESR task-provided | capacitance fetched-datasheet; ESR: TDK 3.6 mohm per part -> 1.8 mohm bank is the record value, the 4.0 mohm used is a task-provided allowance (added assumption; sensitivity run shows no effect on any conclusion) |
| C_in / ESR | 36 uF (2 x 20 uF -10 %) / 1.9 mohm | baseline input_film; ESR task-provided | capacitance fetched-datasheet; ESR: capacitors.json gives 7.5 mohm per part -> 3.75 mohm bank; the task's "1.9 mohm (two 3.75 mohm parts)" halves it - inconsistency recorded; sensitivity run `ol_400V_25A_esrRecord` with 3.75 / 1.8 mohm changes only P_Cin,ESR (0.32 -> 0.62 W) and the input ripple (3.61 -> 3.66 Vpp) |
| Source lead | L_in 10 uH, R_in 50 mohm, ideal voltage source behind it | task-provided laboratory-supply model | unverified assumption; the source can sink current (see section 6.5) |
| R_DS(on) | 48.5 mohm both devices (150 C estimate); 57.2 mohm maximum case | baseline rds_on_150C_mohm_est; thermal.results.rth_jc_note | analytically-checked scaling of the fetched 25 C datasheet value; no 15 V maximum published (unverified) |
| Body diode | V_SD 4.6 V at 25 A, R_s 44 mohm (fit), I_ref 25 A | baseline vsd_V (4.6 V at 175 C, 19.6 A) | fetched-datasheet value applied at 25 A (verification asked for the 29-32 A row: unverified); R_s is a model-fit choice (section 2) |
| Dead time | 250 ns target; 300 ns bring-up (CR-07) | baseline dead_time_ns | agent assumption / orchestrator decision |
| Soft start | 20 ms reference ramp (closed-loop startup runs); 5 ms in the event runs (runtime economy, stated); 2 ms open-loop duty ramp (settling only) | task-provided 20 ms | assumption; [firmware_interface.md](../design/firmware_interface.md) proposes 100 ms - a slower ramp only reduces the figures reported here |
| Controller | cascade: k_pv 1.2325 A/V, k_iv 3097.7 A/(V s), k_pi 0.01709 1/A, k_ii 85.91 1/(A s), i_ref clamp -10..35 A (0..35 A in one dump case), duty clamp 0..0.85, V_ref/V_in feedforward, 10 kHz current filter, 20 kHz voltage filter; module PI k_p 2e-4, k_i 1.5 (reference) | manifest; design basis section 6.4 | analytically-checked loop gains; no firmware |
| Parasitic study | L_loop 25 / 35 / 50 nH, R_loop 0.5 (2.0) ohm, C_oss 130 pF per device at 400 V, design di/dt 2.5 A/ns | baseline mosfet.selection_basis (KR-PCB-004 adapted); gate_driver.json turn-off envelope | unverified until layout extraction / double-pulse; C_oss 130 pF is an interpolation of the fetched 103 pF (1000 V) / Co(tr) 238 pF |
| Limits | ripple 2.0 Vpp; 2 % input ripple; 10 V / 5 ms step; 230 V OVP; 37.5 A OC; I_sat 37.3 / 35 A; 14.5 / 23.5 A capacitor ratings | baseline assumptions_accepted, sensing, magnetics, capacitors | requirement / orchestrator decision |

## 4. Run matrix

| Run | Loop | V_in / V | Load | L / uH | Other | Purpose |
|---|---|---|---|---|---|---|
| ol_360V_25A_Lnom, ol_400V_25A_Lnom, ol_440V_25A_Lnom | open | 360 / 400 / 440 | 25 A | 272 | - | steady-state ripple, RMS, losses at the three corners |
| ol_440V_25A_Lworst | open | 440 | 25 A | 235 | - | worst-case inductance |
| ol_360V_27p5A_Lnom, ol_400V_27p5A_Lnom | open | 360 / 400 | 27.5 A | 272 | - | 10 s overload (360 V = highest HS RMS) |
| ol_440V_27p5A_Lworst | open | 440 | 27.5 A | 235 | - | worst ripple / peak corner |
| ol_400V_25A_RdsMax | open | 400 | 25 A | 272 | 57.2 mohm | maximum-R_DS(on) conduction loss |
| ol_400V_25A_dt300 | open | 400 | 25 A | 272 | 300 ns dead time | bring-up dead time |
| ol_400V_2p5A_L319 | open | 400 | 2.5 A | 319 | - | light load, reverse inductor current |
| ol_400V_25A_esrRecord | open | 400 | 25 A | 272 | ESR 3.75 / 1.8 mohm | ESR provenance sensitivity |
| cl_400V_startup20ms_stepup | cascade | 400 | 12.5 -> 25 A at 28 ms | 272 | 20 ms soft start | startup + step up |
| cl_400V_startup20ms_fullload | cascade | 400 | 25 A | 272 | 20 ms soft start | startup into full load |
| cl_400V_stepdown, cl_440V_stepdown | cascade | 400 / 440 | 25 -> 12.5 A at 14 ms | 272 | 5 ms soft start | step down |
| cl_360V_stepup | cascade | 360 | 12.5 -> 25 A at 14 ms | 272 | 5 ms soft start | step up at the least slew headroom |
| cl_400V_dump, cl_440V_dump | cascade | 400 / 440 | 25 -> 0 A at 14 ms (1 Mohm) | 272 | i_ref,min -10 A | load dump vs 230 V OVP |
| cl_400V_dump_irefmin0 | cascade | 400 | 25 -> 0 A at 14 ms (200 kohm bleeder) | 272 | i_ref,min 0 A | firmware-contract dump policy |
| cl_400V_singleloop_modulePI | module PI | 400 | 12.5 -> 25 A at 28 ms | 272 | 20 ms soft start | why the inner loop is needed |
| parasitic_L25nH_R0.5ohm, _L35nH_R0.5ohm, _L50nH_R0.5ohm, _L25nH_R2ohm | open, 3 cycles | 400 | 25 A | 272 | C_oss 130 pF | switch-node overshoot estimate and its limits |

## 5. Steady-state results (open loop, last 10 of 600 cycles)

| Run | V_in / V | I_o / A | L / uH | D | V_out mean / V | V_out ripple / Vpp | dI_L / App | I_L peak / A | I_L rms / A | HS rms / A | LS rms / A | C_in rms / A | C_out rms / A | I_in mean / A | V_in bus ripple / Vpp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ol_360V_25A_Lnom | 360 | 25.0 | 272 | 0.5614 | 200.04 | 0.160 | 6.51 | 28.26 | 25.08 | 18.80 | 16.60 | 12.79 | 1.88 | 14.04 | 3.56 |
| ol_400V_25A_Lnom | 400 | 25.0 | 272 | 0.5050 | 200.04 | 0.180 | 7.35 | 28.68 | 25.10 | 17.84 | 17.65 | 12.90 | 2.12 | 12.63 | 3.61 |
| ol_440V_25A_Lnom | 440 | 25.0 | 272 | 0.4590 | 200.04 | 0.196 | 8.03 | 29.02 | 25.12 | 17.02 | 18.47 | 12.86 | 2.32 | 11.48 | 3.59 |
| ol_440V_25A_Lworst | 440 | 25.0 | 235 | 0.4590 | 200.03 | 0.219 | 9.30 | 29.65 | 25.15 | 17.04 | 18.49 | 12.89 | 2.68 | 11.48 | 3.59 |
| ol_360V_27p5A_Lnom | 360 | 27.5 | 272 | 0.5619 | 200.03 | 0.157 | 6.51 | 30.75 | 27.57 | 20.67 | 18.24 | 14.05 | 1.88 | 15.46 | 3.91 |
| ol_400V_27p5A_Lnom | 400 | 27.5 | 272 | 0.5055 | 200.03 | 0.176 | 7.35 | 31.17 | 27.59 | 19.62 | 19.39 | 14.17 | 2.12 | 13.91 | 3.97 |
| ol_440V_27p5A_Lworst | 440 | 27.5 | 235 | 0.4594 | 200.03 | 0.218 | 9.30 | 32.15 | 27.64 | 18.74 | 20.31 | 14.16 | 2.68 | 12.64 | 3.95 |
| ol_400V_25A_RdsMax | 400 | 25.0 | 272 | 0.5056 | 200.04 | 0.179 | 7.35 | 28.68 | 25.10 | 17.85 | 17.64 | 12.90 | 2.12 | 12.65 | 3.61 |
| ol_400V_25A_dt300 | 400 | 25.0 | 272 | 0.5051 | 200.04 | 0.180 | 7.35 | 28.68 | 25.10 | 17.84 | 17.65 | 12.90 | 2.12 | 12.64 | 3.61 |
| ol_400V_2p5A_L319 | 400 | 2.6 | 319 | 0.5007 | 205.25 | 0.198 | 6.35 | 5.76 | 3.16 | 2.27 | 2.20 | 1.87 | 1.81 | 1.33 | 0.46 |
| ol_400V_25A_esrRecord | 400 | 25.0 | 272 | 0.5050 | 200.03 | 0.179 | 7.35 | 28.68 | 25.10 | 17.84 | 17.65 | 12.90 | 2.12 | 12.63 | 3.66 |

Reading: the ripple and peak currents reproduce the baseline operating points (6.5 / 7.3 / 8.0 App, 28.3 / 28.7 /
29.0 A at 25 A; 30.8 / 31.2 / 31.6 A at 27.5 A) within 0.1 A. The 235 uH worst case gives 9.30 App and 32.15 A
at 440 V / 27.5 A against the baseline's 9.0 App / 32.0 A (the baseline worst peak uses L(27.5 A) at AL -8 %; the
235 uH figure also applies the datasheet-minimum bias curve, so it is the more pessimistic of the two). The
input current 14.04 / 12.63 / 11.48 A is 0.1 A below the baseline's 14.17 / 12.76 / 11.6 A because the model has
no switching losses (section 5.1). The light-load run sits at 205.25 V because the exact model used to pick the
open-loop duty assumes positive current during the dead times: at 2.5 A with 319 uH the inductor current reverses
to -0.58 A, the HS body diode conducts during the dead times and the average switch-node voltage rises by about
2 x t_dead x f_s x (V_in + V_SD) = 10 V per unit duty error; the module flagged this (`warning: inductor current
reverses`). A closed loop corrects it; the run is kept to show synchronous CCM operation with reverse current.

### 5.1 Losses

| Run | P_cond HS / W | P_cond LS / W | P_dead-time / W (2 t_d f_s V_SD I_o) | P_DCR / W | P_Cin ESR / W | P_Cout ESR / W | P_lead R_in / W | Sum modelled / W | P_in - P_out / W | Conduction-only efficiency / % |
|---|---|---|---|---|---|---|---|---|---|---|
| ol_360V_25A_Lnom | 17.13 | 12.60 | 2.89 (2.88) | 10.06 | 0.31 | 0.014 | 9.87 | 52.9 | 53.8 | 98.93 |
| ol_400V_25A_Lnom | 15.44 | 14.34 | 2.89 (2.88) | 10.08 | 0.32 | 0.018 | 7.99 | 51.1 | 52.0 | 98.97 |
| ol_440V_25A_Lnom | 14.05 | 15.77 | 2.89 (2.88) | 10.09 | 0.31 | 0.021 | 6.60 | 49.7 | 50.7 | 99.00 |
| ol_440V_25A_Lworst | 14.09 | 15.80 | 2.90 (2.88) | 10.12 | 0.32 | 0.029 | 6.60 | 49.9 | 50.4 | 99.00 |
| ol_360V_27p5A_Lnom | 20.73 | 15.21 | 3.25 (3.16) | 12.16 | 0.37 | 0.014 | 11.96 | 63.7 | 64.4 | 98.84 |
| ol_400V_27p5A_Lnom | 18.67 | 17.31 | 3.26 (3.16) | 12.18 | 0.38 | 0.018 | 9.68 | 61.5 | 62.2 | 98.88 |
| ol_440V_27p5A_Lworst | 17.03 | 19.07 | 3.27 (3.16) | 12.22 | 0.38 | 0.029 | 8.00 | 60.0 | 60.4 | 98.91 |
| ol_400V_25A_RdsMax | 18.23 | 16.89 | 2.89 (2.88) | 10.08 | 0.32 | 0.018 | 8.00 | 56.4 | 57.3 | 98.87 |
| ol_400V_25A_dt300 | 15.44 | 14.18 | 3.47 (3.45) | 10.08 | 0.32 | 0.018 | 7.99 | 51.5 | 52.5 | 98.96 |
| ol_400V_2p5A_L319 | 0.25 | 0.22 | 0.26 (0.30) | 0.16 | 0.01 | 0.013 | 0.09 | 1.0 | 6.9 | 98.72 |
| ol_400V_25A_esrRecord | 15.44 | 14.34 | 2.89 (2.88) | 10.08 | 0.62 | 0.008 | 7.99 | 51.4 | 52.3 | 98.96 |

The "efficiency" column is conduction-only and includes 6.6-12 W dissipated in the 50 mohm laboratory lead,
which is not a converter loss; it must not be compared with the 98 % target. Energy balance residuals are
+0.01 to +0.02 % of P_out (the 6.9 W "P_in - P_out" of the light-load run contains the 5 W of stored-energy drift
of a run that is not fully settled at 205 V; its modelled losses are 1.0 W). Combining the simulated
conduction-class losses at 400 V / 25 A (29.8 W conduction + 2.89 W dead time + 10.08 W DCR + 0.34 W ESR = 43.1 W)
with the analytical switching-class items of the baseline (HS switching 9.8-13.6 W for k_RG 1.3-1.9, LS recovery
3.5 W, HS E_oss about 1 W, inductor core 5.9 W, copper about 3 W, HF ring about 1 W, auxiliary about 8 W) gives
75-79 W, i.e. 98.4-98.5 %, inside the baseline's 77-99 W budget. The maximum-R_DS(on) case adds 5.3 W of conduction
(x 1.18 = 57.2 / 48.5), the 300 ns bring-up dead time adds 0.58 W. The dead-time loss at 27.5 A (3.25-3.27 W) is
3 % above the 4.6 V formula because the fitted diode drops 4.7-4.9 V at 28-31 A.

### 5.2 Cross-check against the exact switched model and the closed-form expressions

| Metric (ol_400V_25A_Lnom) | ngspice | numpy exact model | Deviation / % |
|---|---|---|---|
| vout_mean / V | 200.0374 | 200.0000 | +0.02 |
| vout_pkpk / V | 0.1797 | 0.1712 | +4.98 |
| il_mean / A | 25.0095 | 25.0000 | +0.04 |
| il_pkpk / A | 7.3507 | 7.3458 | +0.07 |
| il_peak / A | 28.6786 | 28.6729 | +0.02 |
| il_min / A | 21.3279 | 21.3271 | +0.00 |
| il_rms / A | 25.0992 | 25.0897 | +0.04 |
| i_hs_rms / A | 17.8424 | 17.8314 | +0.06 |
| i_ls_rms / A | 17.6528 | 17.6503 | +0.01 |
| i_cin_rms / A | 12.8973 | 12.5906 | +2.44 |
| i_cout_rms / A | 2.1195 | 2.1188 | +0.03 |
| i_in_mean / A | 12.6348 | 12.6268 | +0.06 |
| p_cond_hs / W | 15.4400 | 15.4210 | +0.12 |
| p_cond_ls / W | 14.3400 | 14.3361 | +0.03 |
| p_diode_deadtime / W | 2.8910 | 2.8891 | +0.07 |

Over the ten open-loop CCM runs the largest deviations are 0.15 % for every current, voltage and loss metric
except `i_cin_rms` (2.44 %: the exact model has an ideal source and no input filter, ngspice adds the 8.4 kHz
L_in / C_in filter ripple) and `vout_pkpk` (5.7 %, 10 mV: the exact model ignores the input-bus ripple that
modulates the switch-node voltage). The full tables per run are in each `results/<run>/summary.json`
(`comparison`) and in `campaign_summary.json`. Against the closed-form expressions of the research records
(computed by the driver from each run's own D, I_o, L, C, ESR: `results/<run>/campaign_metrics.json`,
`textbook`) the simulated ripple is +1.0 % (DCR and ESR voltage drops), I_L peak +0.1 %, HS conduction +0.1 %,
dead-time loss +0.5 %, DCR loss +0.1 %, C_out RMS +0.9 %, C_in RMS +2.4 %, input ripple +2.4 %, output ripple -9 %
(the triangular approximation overstates the capacitive term). The light-load run is excluded from the cross-check
(the exact model's dead-time assignment is invalid for reversing current).

## 6. Closed-loop results

### 6.1 Controller used and its analytical margins

Cascaded average-current-mode controller (campaign driver, manifest `cascade_controller`):

* outer voltage PI: i_ref = k_pv (V_ref - V_fb) + k_iv integral, k_pv = 1.2325 A/V, k_iv = 3097.7 A/(V s) (zero at
  400 Hz), clamp -10 ... +35 A (35 A: below the 37.5 A OC trip and the 37.3 A I_sat; -10 A: synchronous operation
  continues at no load, consistent with the baseline's -2.8 to -3.4 A no-load reverse current; both added
  assumptions), anti-windup on the clamp; V_fb through the module's 20 kHz first-order filter;
* inner current PI: d = V_ref / V_in,nominal + k_pi (i_ref - i_L,f) + k_ii integral, k_pi = 0.01709 1/A
  (= 2 pi 4 kHz L / 400 V), k_ii = 85.91 1/(A s) (zero at 800 Hz), duty clamp 0 ... 0.85 (baseline
  duty_ceiling_initial), anti-windup; i_L,f = i(Vld) + i(Vcout) (exact inductor current) through a 10 kHz
  first-order filter as the stand-in for the ePWM CTR = ZERO average sampling; feedforward uses the nominal V_in
  of the run, not a measured bus voltage.

k_pi sets an inner crossover of about 4 kHz (f_s / 12.5); k_pv was tuned by bisection on the small-signal loop
gain (plant 1/(sC) || R behind the closed inner loop, 20 kHz filter, T/2 modulator delay) for an outer crossover of
2.3 kHz, the middle of the 2.0-2.5 kHz band. Margins recomputed by the driver
([results/loop_gain_analysis.json](results/loop_gain_analysis.json)):

| V_in / V | Load / ohm | Inner loop f_c / Hz, PM / deg, GM / dB | Outer loop f_c / Hz, PM / deg, GM / dB | Module single-loop PI (k_p 2e-4, k_i 1.5): crossovers f_c / Hz, PM / deg; GM / dB |
|---|---|---|---|---|
| 360 | 8 | 3685 / 45 / 12.7 | 2336 / 47 / 4.8 | 87 / 92; GM 7.7 |
| 360 | 16 | 3685 / 45 / 12.7 | 2354 / 44 / 4.6 | 87 / 93 and 940 / 21; GM 1.5 |
| 360 | 1e6 | 3685 / 44 / 12.7 | 2372 / 41 / 4.5 | 87 / 94 and 978 / -50; GM -18.6 (unstable) |
| 400 | 8 | 3997 / 43 / 11.8 | 2300 / 51 / 4.9 | 97 / 93; GM 6.7 |
| 400 | 16 | 3997 / 43 / 11.8 | 2321 / 49 / 4.8 | 97 / 93 and 954 / 7; GM 0.6 |
| 400 | 1e6 | 3997 / 43 / 11.8 | 2339 / 46 / 4.7 | 97 / 94 and 984 / -51; GM -19.5 (unstable) |
| 440 | 8 | 4303 / 41 / 11.0 | 2265 / 55 / 5.0 | 107 / 93; GM 5.9 |
| 440 | 16 | 4303 / 41 / 11.0 | 2282 / 52 / 4.9 | 107 / 94 and 963 / 0; GM -0.2 (marginal) |
| 440 | 1e6 | 4310 / 41 / 11.0 | 2300 / 50 / 4.8 | 107 / 94 and 990 / -51; GM -20.3 (unstable) |

The outer loop sits at 2.27-2.37 kHz with 41-55 deg phase margin over V_in and load; its 4.5-5.0 dB gain margin is
set by the resonant peak of the closed inner loop and is low for a product controller. The inner-loop gain scales
with V_in because k_pi is fixed at the 400 V design (3.7-4.3 kHz); the firmware contract's proposal to schedule
the current-loop gain by 400 V / V_in would remove this. The module PI is a 97 Hz loop with a second, marginal
crossover at the LC resonance from half load upwards, which is what the reference run shows as limit cycling.
Relation to [firmware_interface.md](../design/firmware_interface.md) section 9 (written concurrently): that
contract budgets a 6 kHz inner loop with double-update sampling and finds 30-40 deg at 2.0-2.5 kHz once the
real sensing filters (16 / 32 kHz) and the sample-to-edge delay are included. The present model has no sampling,
no ADC chain and a 10 kHz current filter, so its margins are optimistic relative to the DSP implementation; the
transient magnitudes below depend mainly on C_out and the realised crossover and transfer, the margins do not.

### 6.2 Load steps and load dump

| Run | Controller | Event | I_load / A | Excursion (cycle average) / V | Raw V_out min / max / V | Recovery to +/-2 V / ms | I_L min / max / A | Applicable limit | Result |
|---|---|---|---|---|---|---|---|---|---|
| cl_400V_startup20ms_stepup | cascade | step on at 28 ms | 12.5 -> 25.0 | -7.54 | 192.4 / 200.1 | 0.76 | 8.8 / 30.0 | 10 V / 5 ms | pass |
| cl_360V_stepup | cascade | step on at 14 ms | 12.5 -> 25.0 | -7.74 | 192.2 / 200.1 | 0.77 | 9.2 / 30.0 | 10 V / 5 ms | pass |
| cl_400V_stepdown | cascade | step off at 14 ms | 25.0 -> 12.5 | +7.80 | 199.9 / 207.9 | 0.75 | 7.0 / 28.5 | 10 V / 5 ms | pass |
| cl_440V_stepdown | cascade | step off at 14 ms | 25.0 -> 12.5 | +7.59 | 199.9 / 207.7 | 0.75 | 7.0 / 28.9 | 10 V / 5 ms | pass |
| cl_400V_dump | cascade, i_ref,min -10 A | dump at 14 ms | 25.0 -> 0.0 | +16.09 | 199.9 / 216.2 | 0.96 | -7.5 / 28.3 | < 230 V OVP | pass, 13.8 V margin |
| cl_440V_dump | cascade, i_ref,min -10 A | dump at 14 ms | 25.0 -> 0.0 | +15.68 | 199.9 / 215.8 | 0.95 | -7.3 / 28.7 | < 230 V OVP | pass, 14.2 V margin |
| cl_400V_dump_irefmin0 | cascade, i_ref,min 0 A | dump at 14 ms | 25.0 -> 0.0 (200 kohm) | +16.09 | 200.0 / 216.2 | none within 8 ms; parked at 209.1 V | -7.5 / 28.4 | < 230 V OVP | pass, 13.8 V margin |
| cl_400V_singleloop_modulePI | module PI | step on at 28 ms | 12.4 -> 25.1 | -16.21 | 183.7 / 214.2 | 5.02 | 9.1 / 38.5 | 10 V / 5 ms, 37.5 A OC | FAIL on all three |

The 12.5 A step excursions (7.5-7.8 V) match the closed form dI / (2 pi f_c C_min) + ESR dI = 8.1 V at the
realised 2.3 kHz (7.4 V at 2.5 kHz, 9.2 V at 2.0 kHz in capacitors.json) and recover in 0.75-0.77 ms; the
inductor reaches its new current in about 20 us (slew 0.59-0.88 A/us), so the excursion is capacitor- and
loop-limited as the record assumed. The input bus rings on the 8.4 kHz L_in / C_in filter (Q about 10 with the
50 mohm lead and the 1.9 mohm ESR) between 396.7 and 401.8 V after the step, inside the 2 % ripple allowance;
the source-current swing is 6.1-15.3 A. The dump peaks at 216.2 V (400 V) / 215.8 V (440 V), i.e. +16.1 / +15.7 V,
against the record's 215-218 V window (16.1 V at 2.3 kHz) and the 230 V OVP (CR-04); the peak occurs 115 us
after the event and is set by the 38 us the inductor needs to ramp 28 A down at V_out / L plus the loop's response,
not by the i_ref clamp. The output returns to the 2 V band in 0.96 ms only because the controller drives the
inductor current negative (cycle average down to -3.8 A, instantaneous -7.5 A). The module PI reference run
excursions -16.2 V to 183.7 V, overshoots to 214.2 V, needs 5.0 ms and pushes the inductor to 38.5 A, above the
37.5 A OC trip: a slow single voltage loop would trip the hardware protection on the specified 12.5 A step.
Its steady state also limit-cycles against the 0.5 V PWM resolution (cycle-average pk-pk 1.5-2.9 V, 0.41 Vpp
ripple) as predicted by the marginal second crossover; none of the cascaded runs limit-cycle (cycle-average pk-pk
0.001-0.03 V).

**Dump energy and the input bus (cross-document item).** Discharging the output from 216 V back to 200 V removes
0.36 J. With i_ref,min = -10 A the model returns 0.96 mC (400 V) / 0.88 mC (440 V) to the input during 14-18 ms;
the ideal source behind the 10 uH / 50 mohm lead sinks it and the bus rises only to 403 / 443 V. On a 48.7 uF
non-sinking bus the same charge would raise V_in by about 18-20 V, which is the +17-22 V against the 460 V input
OVP that the firmware contract computes and the reason it sets i_ref,min = 0 at bring-up. The i_ref,min = 0 case
shows two things the contract should know: (1) the peak is unchanged (216.2 V) because the clamp acts after the
inductor energy has already charged C_out; (2) the inner current loop still drives the average inductor current
to -3.8 A for about 100 us after the clamp engages (the proportional path reacts to the filtered current being
above the clamped reference, and the integrator unwinds), returning 0.59 mC (equivalent to about +12 V on a
48.7 uF non-sinking bus) before the output parks at 209 V and decays through the 200 kohm bleeder (time
constant about 22 s). Avoiding any reverse current therefore needs a duty floor or a hold-off in the inner loop,
not only a reference clamp. The model cannot show the input-side consequence because its source sinks current;
this is a human-review item for the firmware and architecture agents.

### 6.3 Startup

| Run | Soft start / ms | Load during start | V_out peak / V | Overshoot / V (%) | I_L peak / A | t(99 % of 200 V) / ms | Cycle-average V_out pk-pk, last 50 T before the event / V |
|---|---|---|---|---|---|---|---|
| cl_400V_startup20ms_stepup | 20 | 12.5 A | 200.60 | +0.60 (+0.30 %) | 17.2 | 19.8 | 0.005 |
| cl_400V_startup20ms_fullload | 20 | 25.0 A | 200.41 | +0.41 (+0.20 %) | 29.7 | 19.8 | 0.005 |
| cl_400V_singleloop_modulePI | 20 | 12.5 A | 201.81 | +1.81 (+0.91 %) | 17.3 | 19.8 | 2.945 (limit cycle) |
| cl_400V_stepdown, cl_400V_dump, cl_400V_dump_irefmin0 | 5 | 25.0 A | 201.37 | +1.37 (+0.69 %) | 32.8 | 5.0 | 0.004-0.006 |
| cl_440V_stepdown, cl_440V_dump | 5 | 25.0 A | 201.31 | +1.31 (+0.65 %) | 33.1 | 5.0 | 0.002 |
| cl_360V_stepup | 5 | 12.5 A | 202.22 | +1.11 (+1.11 %) | 20.0 | 5.0 | 0.011 |

With the 20 ms reference ramp the output tracks the ramp (199.7 V at 20 ms, 99.6 V at 10 ms), overshoots by 0.4-0.6 V
and the inductor peak (29.7 A into the 8 ohm load) is the steady-state ripple peak plus 1 A of capacitor charging
current (108 uF x 10 V/ms = 1.1 A); the input bus sags to 397.4 V with a source current of at most 13.6 A, below the
15.6 A firmware input-current limit and the 18-25 A source limit. The 5 ms ramp used in the event runs (runtime
economy) is four times faster than the task's 20 ms and twenty times faster than the 100 ms of the firmware
contract: it raises the overshoot to 1.3-2.2 V (the 360 V half-load case exceeds the 1 % static band) and the
inductor peak to 32.8-33.1 A (above the 31.6 A overload peak, below the 37.5 A trip). These 5 ms figures are
artefacts of the test setup, not a property of the design; the design soft start should be >= 20 ms. The
converter starts into a discharged output in every run (no pre-bias case was simulated, consistent with A-12).

### 6.4 Closed-loop steady state at the final load

| Run | V_out mean / V | V_out ripple / Vpp | Cycle-average pk-pk, last 50 T / V | PWM LSB / V | Limit cycle suspected | dI_L / App | I_L peak / A | C_in rms / A | HS rms / A |
|---|---|---|---|---|---|---|---|---|---|
| cl_400V_startup20ms_stepup | 200.00 | 0.174 | 0.004 | 0.50 | no | 7.35 | 28.66 | 12.89 | 17.83 |
| cl_400V_startup20ms_fullload | 200.00 | 0.174 | 0.005 | 0.50 | no | 7.35 | 28.67 | 12.89 | 17.83 |
| cl_400V_stepdown | 200.00 | 0.174 | 0.005 | 0.50 | no | 7.36 | 16.17 | 6.58 | 8.99 |
| cl_400V_dump | 200.01 | 0.185 | 0.025 | 0.50 | no | 7.38 | 3.70 | 1.53 | 1.50 |
| cl_360V_stepup | 200.00 | 0.153 | 0.001 | 0.45 | no | 6.51 | 28.25 | 12.78 | 18.78 |
| cl_440V_stepdown | 200.00 | 0.192 | 0.012 | 0.55 | no | 8.05 | 16.52 | 6.57 | 8.60 |
| cl_440V_dump | 200.00 | 0.192 | 0.008 | 0.55 | no | 8.04 | 4.02 | 1.58 | 1.56 |
| cl_400V_singleloop_modulePI | 200.73 | 0.411 | 1.544 | 0.50 | yes | 7.97 | 29.14 | 12.99 | 17.97 |
| cl_400V_dump_irefmin0 | 209.12 (parked after the dump) | 0.179 | 0.029 | 0.50 | no | 7.36 | 3.68 | 1.56 | 1.53 |

The closed-loop steady states at 25 A reproduce the open-loop metrics (ripple 7.35 App, C_in RMS 12.89 A,
conduction 29.8 W, dead-time 2.82-2.84 W) and regulate to 200.00 V; at no load the inductor current swings
+/-3.7 A around zero (synchronous CCM, 3.7 A reverse peak against the baseline's -2.8 to -3.4 A estimate made
with 319 uH; the model keeps 272 uH).

## 7. Parasitic study: switch-node overshoot estimate and its limits

| Case | L_loop / nH | R_loop / ohm | C_oss / pF | Q = Z0 / R | f_ring / MHz | Deck di/dt (ideal switch) / A/ns | Deck v_sw max / V (above V_in) | Deck v_DS,HS max / V | Energy bound I sqrt(L/C) / V | L x di/dt at 1.0 / 2.5 / 4.0 A/ns / V |
|---|---|---|---|---|---|---|---|---|---|---|
| parasitic_L25nH_R0.5ohm | 25 | 0.5 | 130 | 27.7 | 88 | 13.0 | 748 (+348) | 460 | 386 | 25 / 62 / 100 |
| parasitic_L35nH_R0.5ohm | 35 | 0.5 | 130 | 32.8 | 75 | 9.0 | 747 (+347) | 535 | 456 | 35 / 88 / 140 |
| parasitic_L50nH_R0.5ohm | 50 | 0.5 | 130 | 39.2 | 62 | 6.5 | 744 (+344) | 632 | 545 | 50 / 125 / 200 |
| parasitic_L25nH_R2ohm | 25 | 2.0 | 130 | 6.9 | 88 | 10.3 | 646 (+246) | 448 | 351 | 25 / 62 / 100 |

What the deck shows: the ideal switch turns the 28 A inductor current off in about one 2 ns solver step
(measured 6.5-13 A/ns, limited only by the loop inductance itself), so the inductive energy 1/2 L I^2 transfers
almost entirely into the 130 pF C_oss and the switch node rings at 62-88 MHz to +344..+348 V above V_in with
R_loop 0.5 ohm (Q 28-39) and to +246 V with 2 ohm. These numbers are the undamped energy-transfer bound of an
instantaneous commutation; they are **not** a prediction of the C4MS025120K turn-off, whose current fall is
gate-controlled (the gate-driver record's design edge is 2.5 A/ns with 110-120 V/ns at the top of the swing, the
fault turn-off up to 6.4 A/ns) and whose non-linear C_oss and channel absorb part of the energy. Changing the
module's `gate_edge` (10 -> 100 ns) does not change the result because the switch element is hysteretic (hard
transition at the threshold), which is why the design-basis estimate stays the inductive one: dV = L_loop x di/dt
= 62 / 88 / 125 V at 25 / 35 / 50 nH and 2.5 A/ns (the 62-88 V allowance of the baseline), 25-50 V at 1 A/ns,
100-200 V at 4 A/ns. Against the baseline's 90 V overshoot allowance and 530 V recurring peak at 440 V, the
commutation loop must stay below 36 nH at 2.5 A/ns (22 nH at 4 A/ns), i.e. the board target of <= 20 nH leaves
room for about 15 nH of package and lead inductance at the design edge; a 50 nH loop (standing TO-247 leads)
would reach 565 V at 440 V and consume the 1200 V margin the device selection reserved for it (47 %). The ring
frequency 88 MHz at 25 nH / 130 pF compares with the gate-driver record's 82 MHz at 150 pF and its blanking
argument (about 8 cycles, 100-150 ns, below the 252 ns minimum DESAT blanking). None of this replaces the
double-pulse test required by the baseline (R_G,on sweep for dv/dt and V_DS overshoot <= 528 V at 440 V).

## 8. Comparison with analytical values and design-basis limits

| Item | Analytical / baseline value | Simulated | Deviation | Limit | Verdict |
|---|---|---|---|---|---|
| dI_L 360 / 400 / 440 V | 6.5 / 7.3 / 8.0 App | 6.51 / 7.35 / 8.03 App | < +0.7 % | 30 % target at 400 V (29.4 % simulated) | agrees |
| dI_L worst (440 V, 27.5 A, L worst) | 9.0 App (251 uH) / 8.7 App (25 A) | 9.30 App (235 uH) | +3 % (more pessimistic L) | - | consistent |
| I_L peak 25 A corners | 28.3 / 28.7 / 29.0 A | 28.26 / 28.68 / 29.02 A | < 0.1 A | 37.5 A OC, 37.3 / 35 A I_sat | pass |
| I_L peak 27.5 A corners | 30.8 / 31.2 / 31.6 (32.0 worst) A | 30.75 / 31.17 / 32.15 A | < 0.2 A | 35 A worst I_sat | pass, 2.85 A margin |
| I_in 25 A corners | 14.17 / 12.76 / 11.6 A (eta 98 %) | 14.04 / 12.63 / 11.48 A | -1 % (no switching loss) | 15.6 A firmware limit below 360 V; 18-25 A source | 15.46 A at 360 V / 27.5 A |
| C_in RMS | 12.50-12.64 A (25 A), 13.74-13.87 A (27.5 A) | 12.79-12.90 A, 14.05-14.17 A | +2.4 % (input-filter ripple) | 2 x 14.5 A | pass (49 % of rating) |
| Input ripple | 3.5 / 3.9 Vpp | 3.56-3.61 / 3.91-3.97 Vpp | +2 % | 8 Vpp (2 %) | pass |
| C_out RMS | 2.16 A (400 V), 2.86 A worst (220 uH) | 2.12 A, 2.68 A (235 uH) | -2 %, consistent | 2 x 23.5 A | pass |
| Output ripple | 0.25 Vpp (worst), 0.20 Vpp (400 V, 4 mohm) | 0.16-0.22 Vpp | -9 % vs the triangle formula | 2.0 Vpp | pass |
| Conduction loss both devices | 30.6 W (2 x 15.3 W) | 29.7-29.9 W (48.5 mohm), 35.1 W (57.2 mohm) | -3 % | - | agrees |
| Dead-time loss | 2.9 W (250 ns, 25 A) | 2.89 W; 3.47 W (300 ns); 3.25-3.27 W (27.5 A) | < 1 % | - | agrees |
| DCR loss | 10.0 / 12.1 W | 10.06-10.12 / 12.16-12.22 W | +1 % | - | agrees |
| 12.5 A step excursion | 7.4 V (2.5 kHz), 8.1 V (2.3 kHz), 9.2 V (2.0 kHz) | 7.5-7.8 V at the realised 2.3 kHz | -4 to -7 % vs 8.1 V | 10 V | pass |
| Step recovery | - | 0.75-0.77 ms | - | 5 ms | pass |
| 25 A dump peak | 215-218 V (CR-04), 216.1 V at 2.3 kHz | 216.2 / 215.8 V | agrees | 230 V OVP | pass, 13.8 V margin |
| Startup overshoot, 20 ms | - | +0.4 to +0.6 V | - | 1 % band, 230 V OVP | pass |
| Switch-node overshoot | 62-88 V (25-35 nH, 2.5 A/ns), allowance 90 V, peak 530 V | deck bound +344..+348 V (ideal switch); L di/dt 62 / 88 / 125 V | not comparable (artefact) | 90 V / 530 V | L_loop <= 36 nH at 2.5 A/ns; test required |
| Efficiency | 98.0 % target, 97.5 % floor; budget 77-99 W | conduction-class 43.1 W simulated; 75-79 W with the analytical switching-class items (98.4-98.5 %) | - | 98.0 % | consistent with the budget; unverified until measured |

`design/calculations.json` was not available when the campaign ran (checked at the start and at the end of this
task); the comparison uses the baseline and the verified research records. When the
calculations agent publishes its file, the `textbook` block of every `campaign_metrics.json` and the tables above
give the simulated counterparts for a one-to-one check.

## 9. Knowledge applied

| Id | Applicability here | How |
|---|---|---|
| SKILL-003 (DC-link capacitors) | adapted | its ripple-charge / RMS quantities for the buck's pulsating input current are the metrics verified in section 5; the output filter is outside the skill's scope (inductor-defined) and is checked with the C >= dI/(8 f_s dV) form instead |
| KR-CAP-001 (capacitance from worst-case ripple charge) | direct | simulated input ripple 3.56-3.97 Vpp against the 8 Vpp (2 %) requirement with C_min 36 uF |
| KR-CAP-002 (RMS within rating) | direct | 7.1 A per film part vs 14.5 A; 1.34 A per output part vs 23.5 A |
| KR-CAP-003 (bulk film plus distributed HF ceramics) | not applicable in this model | the 10 x 0.47 uF HF tier, the film ESL and the 670 kHz film-ceramic ring of the capacitor verification are not in the lumped deck; layout extraction and the DNP damping leg remain human-review items |
| KR-GD-009 (dead time from the controller, interlock as last barrier) | direct | 250 / 300 ns dead times modelled with their body-diode loss (2.89 / 3.47 W); the interlock itself is not modelled |
| KR-GD-001 / 002 / 003 / 005 / 010 / 012 (gate voltages, split R_G, Miller clamp, negative bias) | not applicable | behavioural switches have no gate; the gate-driver record owns these |
| KR-GD-004 (DESAT), KR-PR-001 (protection faster than withstand), KR-PR-002 (latched faults) | not applicable | no fault, no DESAT and no protection timing is simulated; the 37.5 A OC level is only compared with simulated peaks |
| KR-SN-005 (fast hardware OC path) | adapted | simulated inductor peaks 32.15 A (worst steady corner), 33.1 A (5 ms soft start) and 38.5 A (module-PI reference step) against the 37.5 A trip: the specified loop structure keeps the peaks below the trip, a slow single loop does not |
| KR-PCB-004, PE-PCB-003 (commutation loop first, <= 20 nH) | adapted | parasitic sweep 25 / 35 / 50 nH and the L x di/dt budget (<= 36 nH for the 90 V allowance at 2.5 A/ns) |
| KR-TH-001 / 002 / 003 | not applicable | no thermal coupling; the loss table is the hand-off to the thermal document |
| SKILL-001 (SiC gate driver design), SKILL-006 (thermal placement) | not applicable | out of the model's scope |
| REF-TI-TIDA-010054 | adapted | the inner-current / outer-voltage control structure follows the baseline requirement; no TIDA instance value (gains, filters, sinks) was used |
| Component parameters (C4MS025120K, B32776G8206 / G4606, 0058192A2 choke) | direct | taken from the verified research records at the levels stated in section 3; there is no CMP record for the C4MS025120K in the knowledge base (knowledge-base item) |
| A-39 (simulation scope rule) | direct | circuit simulation was possible for ripple, RMS currents, conduction-class losses, transients and startup; where it was not (switching losses, overshoot, DESAT), the limitation is recorded instead of replaced by an assumption |

## 10. Model limitations (plain statement)

* Switches are ideal Ron / Roff elements with a 10 ns control edge and a hard transition: no SiC device model,
  no channel saturation, no C_oss (except as a lumped 130 pF in the parasitic deck), no gate drive, no switching
  loss, no dv/dt or di/dt fidelity. All switching-class losses (E_on, E_off, E_rr, E_oss, gate) come from the
  analytical records, not from this simulation.
* Body diodes are exponential diodes fitted to 4.6 V at 25 A with a 44 mohm slope: no reverse recovery, no
  temperature dependence, no third-quadrant channel conduction.
* The inductor is a fixed L per run with a fixed 100 C DCR: no L(i) roll-off inside a run, no core loss, no AC
  resistance, no winding capacitance. The capacitors are C + ESR only: no ESL, no HF ceramic tier, no DC bias.
* The input is an ideal voltage source behind 10 uH / 50 mohm that can sink current; the real source cannot
  (unidirectional flow), so input-OVP interactions after a dump are not represented.
* No thermal coupling (parameters are at fixed assumed temperatures), no EMI, no layout parasitics beyond the
  parasitic deck's lumped loop, no fault cases, no DESAT / OC / OVP action.
* Control is idealised: continuous-time, no ADC sampling, no computation delay, no quantisation other than the
  0.5 V PWM grid, exact inductor-current and output-voltage measurements through first-order filters, nominal
  V_in feedforward. No firmware exists; the gains are stand-ins and the margins are optimistic relative to a
  sampled implementation.
* The parasitic deck's overshoot is an energy-transfer bound with an unrealistic commutation speed; its absolute
  values are not usable as a device stress prediction.

What the simulation verifies: inductor ripple, peak and RMS currents at every corner; HS / LS / C_in / C_out RMS
currents; conduction and dead-time losses; input and output ripple with the specified passive values; the
transient magnitude and recovery of the 12.5 A steps and the 25 A dump for the specified loop structure and
crossover; startup overshoot and inductor peak with the 20 ms soft start; the consistency of the exact
switched-model and closed-form values with a circuit solver. What it does not verify: switching losses and
efficiency, switch-node overshoot absolute values, dv/dt, gate behaviour, DESAT / OC / OVP behaviour, thermal
limits, EMI, and anything depending on the real firmware.

## 11. Files and reproduction

* Parameter files: `models/ol_*.json` (11), `models/cl_*.json` (9), each loadable by
  `python -m automation.simulation.buck_stage <file> --out <dir>` (the `cl_*` files then run with the module's own
  PI; the cascaded controller is applied only by the driver), and `models/campaign_manifest.json` (run list,
  controller gains and clamps, parasitic sweep, limits, analytical references).
* Driver: `results/run_campaign.py` (repository root: `python examples/sic-buck-400v-200v-5kw/simulation/results/run_campaign.py`,
  `--only <run>` for a partial re-run that merges into the summary). It imports `automation.simulation.buck_stage`
  and `ngspice_runner` unchanged; `tests/test_simulation.py` was not touched (no module change was needed).
* Per run (`results/<run>/`): `<run>.cir` (the deck that ran, with the cascade block where applicable),
  `parameters.json`, `waveforms.csv` (1 us grid open loop, 2 us closed loop) - the full-length CSVs (39 MB) are not committed to Git and are regenerated by `run_campaign.py`, `waveforms_zoom.csv` (last three
  cycles at solver resolution), `vout.svg`, `il.svg`, `zoom_vout.svg`, `zoom_currents.svg`,
  `zoom_capacitor_currents.svg`, `zoom_vsw.svg`, `load_step.svg` (runs with an event), `summary.json` (module
  results, comparison table, campaign block), `campaign_metrics.json`; cascaded runs add `controller.csv`
  (i_ref, filtered i_L, duty), `startup_currents.svg` and `event_*_vout.svg` / `event_*_currents.svg`.
* Parasitic cases (`results/parasitic_*/`): `deck.cir`, `parasitic_vsw.svg`, `study.json`.
* Campaign: `results/campaign_summary.json`, `results/campaign_log.txt`, `results/loop_gain_analysis.json`.
* Runtimes (ngspice-46, Windows host shared with other agents): open-loop runs 0.9-2.0 s (154k points, 12 ms),
  closed-loop runs 6.7-31 s (0.9-1.8 M points, 22-44 ms at 25 ns), parasitic cases 0.25-0.28 s; final full
  campaign 187 s wall (122 s on the idle host). The result set is 59 MB, dominated by the waveform CSVs.

## 12. Verification status and open items

**Simulated (this campaign, behavioural model, not hardware-validated).** Ripple, peak and RMS currents, input
and output ripple, conduction and dead-time losses at eleven open-loop corners; eight cascaded-controller
transients (steps, dumps, startups) and one module-PI reference; four parasitic cases.

**Analytically checked.** The exact switched-model cross-check (<= 0.15 % on every current, voltage and loss
metric, 2.4 % on C_in RMS, 5.7 % on the 0.18 V output ripple); the closed-form values of the research records
(within 1-3 %, 9 % on the output ripple); the loop-gain margins of both controllers; the L x di/dt and ring
frequency table; the dump energy and its equivalent input-bus rise; the body-diode model check against ngspice's
saturation-current floor.

**Unverified.** Every switching-class loss and the efficiency; the absolute switch-node overshoot and dv/dt;
C_oss 130 pF at 400 V (interpolated); L_loop 25-50 nH and R_loop (assumed until layout extraction); the
laboratory-source lead model (10 uH / 50 mohm, sinking source); V_SD at 29-32 A (datasheet row not read); the
15 V-gate maximum R_DS(on) (not published); the task-provided ESR values (1.9 / 4.0 mohm) against the record's
3.75 / 1.8 mohm (shown to be immaterial); the 20 ms soft start against the firmware contract's 100 ms.

**Human review.**
1. Controller: the 2.0-2.5 kHz outer crossover is only reachable with an inner current loop; the module's
   single-loop PI fails the 10 V / 5 ms step and would trip the 37.5 A OC. The cascaded stand-in (gains in the
   manifest) has 41-55 deg phase margin but only 4.5-5 dB gain margin in a sampling-free model; the firmware
   contract's sampled analysis finds 30-40 deg at 2.0-2.5 kHz with the real sensing filters and demands
   double-update sampling - reconcile the two before firmware design. No firmware exists.
2. Load-dump policy: with i_ref,min = -10 A the dump recovers in 1 ms but returns 0.9 mC to the input (about
   +18-20 V on a 48.7 uF non-sinking bus, against the 460 V input OVP); with i_ref,min = 0 the inner loop still
   returns 0.6 mC through its transient undershoot and the output parks at 209 V until the bleeder discharges it.
   The reverse-current limit must be implemented in the inner loop (duty floor / hold-off), and the input-side
   consequence must be judged with a non-sinking source model (A-07, A-43).
3. Switch-node overshoot: the parasitic deck cannot predict it; L_loop <= 36 nH at 2.5 A/ns is required for the
   90 V allowance (board target 20 nH plus leads), to be confirmed by layout extraction and the double-pulse test
   (R_G,on sweep, V_DS <= 528 V at 440 V).
4. Light-load behaviour: synchronous CCM with up to 3.7 A reverse inductor current at no load was assumed
   (consistent with the baseline); diode emulation / burst mode was not analysed and the open-loop light-load
   point rises 5 V because of the dead-time polarity reversal - the closed loop must be checked at light load with
   the final firmware.
5. The 5 ms soft start of the event runs produced 32.8-33.1 A inductor peaks and up to 2.2 V overshoot; keep the
   design ramp >= 20 ms (100 ms in the firmware contract) and limit the startup current reference.
6. Module findings for the tooling owners (no code changed): ngspice floors the diode I_s near 1e-28 A, so the
   module's N = 2 body-diode fit silently gives 4.0 V instead of 4.6 V at 25 A with R_s = 20 mohm (44 mohm used
   here as a workaround); `_load_step_metrics` and `startup` cover only a step-on event; the parasitic study's
   `gate_edge` has no effect because the switch is hysteretic; a cascaded-controller option in `build_deck` would
   remove the driver-side deck patch.
7. calculations.json was not available; the comparison in section 8 uses the baseline and the verified research
   records and should be repeated against the calculations agent's file when it exists.
