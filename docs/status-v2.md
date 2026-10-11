# Execution status - V2

Recorded 2026-10-11, Asia/Shanghai. Branch: `feat/sic-buck-5kw-v2`. Last commit on
the branch when this file was written: `99dfc01` ("feat(pcb): both V2 boards placed,
routed and at native DRC zero; exports, metrics, review and correction pass").

**AI-GENERATED ENGINEERING PROTOTYPE V2 - HUMAN REVIEW REQUIRED**

V2 is the 400 V (360-440 V) to 200 V, 5 kW, 25 A, 50 kHz SiC synchronous buck under
`examples/sic-buck-400v-200v-5kw/` (called EX below): a 240 x 180 mm four-layer power
board (Wolfspeed C4MS025120K TO-247-4 pair, UCC21710-Q1 isolated drivers with
UCC14141-Q1 bias modules, custom 272 uH High Flux toroid, TMCS1133 / AMC1311 isolated
sensing) and a 120 x 80 mm TMS320F28335 control board stacked on the power board's SELV
strip through a 2 x 25 mezzanine. Every row below names the file the number comes from.

| Milestone | State | Evidence |
|---|---|---|
| Environment and smoke test | Complete | KiCad 10.0.7 at `D:/EngineeringTools/KiCad/10.0` (`kicad_version` in every `drc.json` / `erc.json`; command paths in the `run.json` manifests); KiCad-bundled ngspice-46 (EX `simulation/results/campaign_summary.json`); host Python 3.10; nothing installed. Pipeline smoke on a disposable board: passed (`tests/test_v2_pipeline_smoke.py`; EX `review/v1_v2_comparison.md` table 2.3) |
| Knowledge-driven research and verification | Complete | 10 research records, 20 verification records (EX `verification/verification-summary.json`); 91 query entries (74 searches, 11 `--get` reads, 6 direct reads), 317 citation rows over 96 ids, 273 labelled rows: 114 direct / 101 adapted / 35 not applicable / 23 human review (EX `review/knowledge_utilisation_report.md` sections 1, 2.2 and 7); 20/20 verdicts confirmed-with-corrections |
| Baseline and calculations | Complete for review | EX `design/design_decisions.json` schema 4, 26 conflict resolutions CR-01..CR-26, 13 open items for human review; EX `design/calculations.json`: 19 invariants, all PASS, 58 baseline cross-checks (EX `design/calculations.md` sections 13-14) |
| Schematics and ERC | Complete | Power project 12 sheets, ERC 0 findings (EX `verification/erc/20261010T165532Z-erc-02a2619f/run.json`); control project ERC 0 findings (EX `verification/erc/20261010T071810Z-erc-b207ac59/run.json`); 22 sheets in total (EX `review/v1_v2_comparison.md` table 2.4); 45 custom `.kicad_dru` rules on the power project: 6 class-pair rules and 39 documented per-footprint pin-field exceptions inside packages (hv / barrier / pitch), which are why the KR-ISO-002 rows read 1.95 mm on F.Cu with a zero DRC (EX `verification/known_issues.md` V2-09, V2-44); eight slotted barrier footprints (commit `ea8e874`) |
| Simulation campaign | Complete (behavioural only) | 20 ngspice transient runs plus 4 parasitic cases; no SiC device physics, no switching loss, no firmware (EX `simulation/simulation_report.md` sections 1 and 10; `simulation_runs: 20` in `verification-summary.json`) |
| Component records and BOM | Complete for review | 65 component records (EX `components/component_records.json`); merged BOM 444 rows, power 237, control 207 (EX `components/bom.csv`, `bom_power.csv`, `bom_control.csv`); magnetic record `AIPE-MAG-L1-SICBUCK-5KW-V2` (EX `components/magnetic_record.json`) |
| Placement and routing - power board | Complete (CAD) | 237 footprints, 4755 tracks, 606 vias, 36 zones, 0 unresolved connections, 523.7 s routing (EX `verification/routing_progress_power.json`); builds r1..r20d in EX `verification/routing_iterations_power.md` (sections 1-15); delivered board r20d |
| Placement and routing - control board | Complete (CAD) | candidate B, 207 components, 5995 tracks, 798 vias, 20 zones, 0 unresolved, 1155.4 s routing (EX `verification/routing_progress_control.json`, `verification-summary.json`); history in EX `verification/routing_iterations_control.md`; regeneration with the current shared router reproduces every track, via, footprint and zone (EX `verification/engineering_checks/control_regeneration_check.json`, see below) |
| Native DRC - power board | Passed, 0 / 0 / 0 | EX `verification/drc/20261011T054445Z-drc-d0914d79/run.json`: kicad-cli 10.0.7, `--schematic-parity --severity-all --refill-zones`, 0 violations / 0 unconnected / 0 schematic-parity, source sha256 `b1bb5698194b9aea...`; stored fills checked without refill: 0 / 0 (EX `verification/engineering_checks/stored_zone_fill_check_power.json`) |
| Native DRC - control board | Passed, 0 / 0 / 0 | EX `verification/drc/20261011T051246Z-drc-f801ed3c/run.json`: same options, 0 / 0 / 0, source sha256 `dead06ed18d85154...`; stored fills without refill: 0 / 0 (`stored_zone_fill_check_control.json`). 51 DRC manifests are kept under EX `verification/drc/`, failed iterations included |
| Netlist and layout metrics | Passed / measured | Exact pad-net match model = schematic = board: 648 pads / 101 nets (power), 667 / 111 (control) (EX `verification/netlist_check_{power,control}.json`); layout metrics power 58 rows: 27 within / 6 exceeding / 25 measured without threshold; control 31 rows: 2 / 2 / 17 / 10 not measured (EX `verification/engineering_checks/layout_metrics_{power,control}.md`) |
| Exports | Complete | 11 commands, 35 hashed artifacts per board (EX `manufacturing/{power_board,control_board}/export-manifest.json`); STEP exports miss library 3D models (`step_models_complete: false` in `verification-summary.json`; LR-35); bundle description EX `manufacturing/README.md` |
| Layout review and correction pass | Complete; open items stay visible | Independent review EX `verification/pcb_rule_review.md` and `layout_review_findings.json` (LR-20..LR-35); corrections EX `verification/optimisation_before_after.md` (pass 1 and pass 2) with `optimisation_finding_status.json` / `optimisation_finding_status_pass2.json`. Applied: LR-20, LR-21, LR-23. Partly applied: LR-25, LR-28, LR-30. Not applied / open (ten): LR-22, LR-24, LR-26, LR-27, LR-32, LR-33 and the notes LR-29, LR-31, LR-34, LR-35 (`optimisation_finding_status_pass2.json`) |
| Whole-example verifier | Passed | `python -m automation.scripts.verify_sic_buck` -> EX `verification/verification-summary.json` `status: passed`, `problems: []`; scope "CAD connectivity, native check currency and export integrity only; hardware unqualified" |
| Reports | Complete | EX `design/*.md`, `review/knowledge_utilisation_report.md` (24 decisions audited), `review/v1_v2_comparison.md`, `review/architecture_comparison.md`, `review/floorplan_candidates_{power,control}.md`, `manufacturing/README.md`, [docs/reproduce-v2.md](reproduce-v2.md), [docs/knowledge-feedback-v2.md](knowledge-feedback-v2.md), [docs/v2-pull-request.md](v2-pull-request.md), this file; EX `review/design_report.md` (14 sections, written 2026-10-11 per its opening paragraph) and EX `verification/known_issues.md` (49 rows V2-01..V2-49; the file carries no date statement) |
| Unit tests | 253 run, 0 failures, 2 skipped | `python -m unittest discover -s tests`, re-run 2026-10-11 after the floorplan-candidate amendment: "Ran 253 tests ... OK (skipped=2)" (run log kept in the orchestrator scratch directory, not committed); 16 test modules under `tests/` |
| Frozen V2 | Complete | `python -m automation.scripts.freeze_v2` (verifier re-run first, passed) wrote `examples/sic-buck-400v-200v-5kw/releases/v2/` (868 files, `SHA256SUMS.json` with `source_commit` `f72052fb53aa70163fad21294c36379d3921aec0`, label "AI-GENERATED ENGINEERING PROTOTYPE V2 - HUMAN REVIEW REQUIRED", created 2026-10-11T07:10 UTC) and `releases/v2-review-package.zip` (32,070,559 bytes). The snapshot copies of `review/v1_v2_comparison.*` were taken before the freeze and therefore still count zero release manifests; the branch copies were refreshed afterwards |
| GitHub push / PR | Pending | pending; fork `MrCoconut616/AIPE-PCB-Agent`, PR from `feat/sic-buck-5kw-v2` to `FulongLi/AIPE-PCB-Agent` `main`, title "AIPE-PCB-Agent V2 — Knowledge-Driven 5kW SiC Buck", not merged automatically; prepared body in [docs/v2-pull-request.md](v2-pull-request.md) |

## Control-board reproducibility check

The delivered control board was routed with `automation/kicad_tools/grid_router.py` at
sha256 `b78a49cc48f2c82656a382e94078d9cb442a54ad4d3e68f7237161798c48c7b3`
(`shared_router_sha256` in EX `verification/routing_progress_control.json`). The power-board
convergence changed the shared module afterwards; the file on the branch now hashes to
`c666ba734e5450014c683fafc87b9e4debffc9e4dddba71a28dd0f07416df860`. A scratch
regeneration of candidate B with the current module (EX
`verification/engineering_checks/control_regeneration_check.json`, diagnostic, not a
verification record) finished with 0 unresolved connections in 1189.8 s and produced
5995 tracks, 798 vias, 207 footprints and 20 zones; a pcbnew comparison of every track,
via, footprint and zone (uuids and timestamps ignored) found 0 items present in only one
board (`geometry_comparison.identical: true`). The file hashes differ
(`b87775eae00fc97c...` regenerated versus `dead06ed18d85154...` delivered) through uuids
and timestamps only. A kicad-cli DRC of the regenerated board inside a copy of the
project reported 0 unconnected / 0 schematic-parity and one `lib_footprint_issues`
warning that the check attributes to the copied library path (the 211 findings of a
DRC on the bare board file are recorded as an artefact of running without the project
files). The delivered board remains verified by its own DRC manifest and hash; the
regeneration check is reported as geometric reproduction, not as a second verification.

## What V2 is and is not

V2 is a CAD-complete, knowledge-driven engineering prototype: both boards are placed,
routed, netlist-consistent and at zero native ERC/DRC findings with schematic parity
and all severities enabled, with manufacturing formats exported and hashed, an
independent rule-by-rule layout review, a correction pass with measured before/after
values, a behavioural simulation campaign and a traced knowledge audit. It is not a
validated converter. Zero native findings prove copper-rule compliance in KiCad against a
rule set that includes 39 documented per-footprint pin-field exceptions (for example
VIN-PGND / VOUT-PGND at 1.95 mm on F.Cu inside the R6 / R10 pin fields, EX
`verification/known_issues.md` V2-09), not electrical, thermal, EMI or insulation
adequacy: six power-board and two control-board metric rows exceed their review
thresholds, ten review findings are marked NOT APPLIED in
`optimisation_finding_status_pass2.json` (LR-22, LR-24, LR-26, LR-27, LR-32, LR-33 and
the notes LR-29, LR-31, LR-34, LR-35; LR-25, LR-28 and LR-30 partly applied), every one of
the 24 audited decisions carries a human-review item, no firmware exists, nothing was
fabricated, purchased, energised or measured, and V1 (`examples/buck-48v-24v-1kw`) is
frozen and untouched.

## Remaining external action

Human power-electronics review of the example before any physical step. The register
EX `verification/known_issues.md` (49 rows V2-01..V2-49 in four priority groups: before
fabrication, before energisation, before design release, documentation and tooling)
is the authoritative list; its first five rows, all "before fabrication", are:

1. V2-01 (LR-22, not applied): the HF DC-link tier C1-C10 sits only west of Q1; Q2
   source pad to the nearest same-net HF pad 41.165 mm against the <= 15 mm row rule
   (Q1.1 to C1.1 8.367 mm); the F.Cu VIN neck C6.1 -> Q1.1 is 2.35 mm after the
   rule-aware refill; review loop estimate 6-8 nH against the L_loop <= 36 nH that the
   90 V overshoot allowance needs at 2.5 A/ns. Review of the complete commutation loop
   and a decision on a second capacitor column before fabrication.
2. V2-02 (LR-24, not applied after one attempt): LS gate network 84.44 mm of track
   against 39.94 mm on the HS side, G_L with 7 vias, R41 / TP2 over the In2 SW pour;
   build r20c (B.Cu-only region) left 9 connections open and was reverted. Gate-loop
   inductance and dv/dt coupling review; double-pulse test with the V_GS probes.
3. V2-03 (LR-28, partly applied): the 25 A switch-node current runs on In2 only, neck
   SW via group -> L1.1 18.48 mm (5.22 mm before r20) against 21.8 mm inner for 25 A at
   20 K; output return J4 -> Q2.2 on In1 only. Temperature rise of the In2 neck at
   25-27.5 A; accept or widen.
4. V2-04 (LR-23 applied, single-layer result): input return J2 -> Q2.2 neck on In1
   24.22 mm (4.56 mm before r20) with no B.Cu return copper, against the baseline's
   paralleled 12 mm outer / 22 mm inner per 25 A. Confirm the single-layer 70 um return
   thermally or add outer-layer PGND copper; check the J2 / J5 terminal swap against the
   enclosure wiring.
5. V2-05: VOUT_L (L1.2 -> U10.1, 25 A) is F.Cu only, 4.8 mm wide at the TMCS1133 pins
   (review estimate 50 K by IPC-2221 at the pin funnel); the PE-PCB-006 rows VOUT_L and
   VIN_RAW read "exceeds" because the checker counts vias only (LR-30). Current handling
   of the TMCS1133 land pattern against the TI EVM; add B.Cu copper or accept with a
   thermocouple on U10.

The energisation-level items follow in the same register: insulation coordination
(V2-18), PE and grounding strategy (V2-19), short-circuit protection with the
unpublished withstand time (V2-20), gate-drive values (V2-21), the thermal corner at
about 130 C (V2-23), the single-ended mezzanine (V2-25) and the missing controller and
firmware (V2-26, V2-27). Section 8.2 of EX `review/knowledge_utilisation_report.md`
lists the same open items by design decision.

After the review the remaining orchestrator steps are the V2 freeze
(`automation/scripts/freeze_v2.py`, which re-runs the verifier first) and the GitHub
push of `feat/sic-buck-5kw-v2` from the fork with the prepared PR body. Neither step
authorises fabrication, purchase or energisation.

## Validation scope

Native checks use the real KiCad 10.0.7 tools with all severities and schematic parity.
Pad-net equality, stored-fill DRC, layout metrics against review thresholds, calculation
invariants and the behavioural simulation have executable checks. Loop inductance,
creepage per standard, EMI, thermal rise, insulation type tests, fault response on
hardware and the control loop are not measured anywhere in V2 and need engineering
review and later hardware work. Windows execution is proven; other operating systems
were not exercised.
