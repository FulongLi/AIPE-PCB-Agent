# AIPE-PCB-Agent - example history and milestone status (V1, V2, V2.1, V2.2, V3, knowledge system V0)

This page is the former repository README, moved here unchanged on 2026-10-21 when the README was reduced to the AIPE
template. It records the milestone statements of the SiC buck examples and the knowledge system as they were written at
the time (links adjusted to this location). The DAB-V1 three-board example is documented in
`docs/dab-10kw/` and `examples/dab-10kw/README.md`.

---

AI-assisted power-electronics PCB engineering with reproducible KiCad automation.

> **V3 clean-sheet 5 kW design — engineering prototype review; release blocked**

V3 independently redesigns the 400 V to 200 V converter, with two fully routed four-layer boards, 9 + 9 schematic sheets and a five-sheet system wiring project. Native ERC/DRC, unconnected-item and schematic-parity checks are clean. The package adds executed sampled/native simulations, real-copper loop and resistance screens, mechanical envelopes, manufacturing exports and a full disposition of the 18 V2.2 issues. Hardware qualification and human engineering review remain open; no fabrication or energisation is approved.

- [V3 package and editable projects](../examples/sic-buck-400v-200v-5kw-v3/README.md)
- [Design review and release holds](../examples/sic-buck-400v-200v-5kw-v3/review/design_review_report.md)
- [V2.2 versus V3 evidence](../examples/sic-buck-400v-200v-5kw-v3/review/v22_vs_v3_comparison.md) and [verification manifest](../examples/sic-buck-400v-200v-5kw-v3/verification/final_validation.json)

V1 and the complete V2/V2.1/V2.2 example history remain unchanged. The V2.2 description below records that earlier milestone.

> **V2.2 independent engineering review and circuit corrections — human review required**

The historical branch `feat/sic-buck-v2.2-engineering` corrected the current-sensor reference and isolated-sensing RLIM sizing, adds four local control-board bypasses, and repairs drawing margins and plot framing. A shorter gate-clamp candidate was rejected after its return-path geometry worsened. The original ratings and two-board architecture are retained. This revision includes actual CAD changes and explicitly differs electrically from V2/V2.1.

- [V2.2 design review and remaining blockers](../examples/sic-buck-400v-200v-5kw/review/v22/design_review_report.md)
- [Independent Stage A review and prioritised issue register](../examples/sic-buck-400v-200v-5kw/review/v22/stage_a_independent_review.md)
- [Measured comparison](../examples/sic-buck-400v-200v-5kw/review/v22/comparison.md), [validation evidence](../examples/sic-buck-400v-200v-5kw/review/v22/validation.json), [exact remaining ECOs](../examples/sic-buck-400v-200v-5kw/review/v22/remaining_engineering_ecos.md)

V2 and V2.1 below are historical milestones; their original example CAD/PDF paths contain V2.2. Their frozen release directories retain the original files. No fabrication, energisation or automatic merge is approved.

> **AI-GENERATED ENGINEERING PROTOTYPE V2.1 - HUMAN REVIEW REQUIRED**

V2.1 (branch `feat/sic-buck-v2.1-quality`) is a presentation and routing-geometry revision of the
V2 SiC buck below: the same electrical design, netlist-identical to the frozen V2 release, drawn as
wired engineering schematics in functional groups and routed with the upgraded grid router
(octilinear simplification and tangent arcs; the 8-direction search is available as an option). It
changes how the design is drawn and routed, not what it is; the V2 open engineering issues stay
open. See [V2.1 status](#v21-status).

> **AI-GENERATED ENGINEERING PROTOTYPE V2 - HUMAN REVIEW REQUIRED**

The second benchmark is a 400 V (360-440 V) to 200 V, 5 kW, 25 A, 50 kHz SiC
synchronous buck designed with the Engineering Knowledge System: a 240 x 180 mm
four-layer power board (two Wolfspeed C4MS025120K TO-247-4 devices, UCC21710-Q1
isolated drivers with UCC14141-Q1 bias modules, a custom 272 uH High Flux toroid,
TMCS1133 / AMC1311 isolated sensing) and a 120 x 80 mm TMS320F28335 control board
stacked on the power board's SELV strip through a 2 x 25 mezzanine. Both boards are
routed and at zero native ERC/DRC findings with schematic parity and all severities;
an independent layout review, a measured correction pass, a behavioural simulation
campaign and a knowledge-utilisation audit are on record. V2 is a CAD-complete review
deliverable with open review items, not a validated converter: nothing was fabricated,
energised or measured, and no firmware exists.

> **AI-GENERATED ENGINEERING PROTOTYPE — V1 — HUMAN REVIEW REQUIRED**

The first benchmark is a 48 V nominal to 24 V, 1 kW synchronous buck converter
with an integrated TMS320F28335 control section. The output current is
approximately 41.7 A. V1 is a review deliverable, not an energisation approval.

## V2.1 status

V2.1 is complete as CAD on `feat/sic-buck-v2.1-quality` (HEAD `7f93a61`): the V2 design, redrawn
and re-routed. Schematics: 7 + 9 sheets, pin-stub global labels 648 -> 7 (power) and 667 -> 7
(control), wired pin share 0.897 / 0.757, native ERC 0 findings on both projects, exported netlist
`(ref, pad) -> net` exact against the model and against the frozen V2 netlist
(`examples/sic-buck-400v-200v-5kw/verification/schematic_gates/<board>/schematic_gates.json`,
`verification/engineering_checks/schematic_readability_<board>.md`). Boards: 90-degree bends
3609 -> 1121 (power) and 4069 -> 1233 (control), 145 and 261 tangent arcs, routed length
5744.6 -> 5545.6 mm and 7055.2 -> 6700.7 mm, vias 606 and 798 as in V2, no net longer, no net
with more vias or narrower copper, native DRC 0 / 0 / 0 with `--schematic-parity --severity-all
--refill-zones` on both boards (`verification/engineering_checks/routing_quality_<board>_compare.md`,
`verification/drc/20261012T100423Z-drc-8b9e64d1`, `verification/drc/20261012T114513Z-drc-3461f467`).
Zero native findings is a CAD statement against the unchanged V2 rule set, not electrical, thermal, EMI or
insulation validation; nothing was built, energised or measured and no firmware exists.
The 8-direction search is implemented but opt-in (it left connections open on both boards), 1121 /
1233 90-degree bends remain, and the V2 open engineering issues keep their status; see
[V2.1 execution status](status-v2.1.md) for the milestone table, the open points and the
freeze and GitHub hand-off state.

- [V2 vs V2.1 comparison report](../examples/sic-buck-400v-200v-5kw/review/v2_v21_comparison.md)
- [Known issues](../examples/sic-buck-400v-200v-5kw/verification/known_issues.md) (the 49 V2 rows stay open with unchanged status - 15 of them annotated with the V2.1 value where the routing changed a quoted number - plus 18 V2.1 rows V2.1-01..V2.1-18) and [V2.1 validation](../examples/sic-buck-400v-200v-5kw/verification/v21_validation.md)
- [Schematic section crops](../examples/sic-buck-400v-200v-5kw/review/schematic_sections) (`<section>_{v2,v21}.png`, 200 dpi, index in `sections.json`)
- [Design report](../examples/sic-buck-400v-200v-5kw/review/design_report.md) (V2 design; still the design record)
- [V2.1 execution status](status-v2.1.md), [reproduction, V2.1 section](reproduce-v2.md), [architecture, V2.1 modules](architecture.md), [prepared PR body](v2.1-pull-request.md)
- Routing quality V2 -> V2.1: [power](../examples/sic-buck-400v-200v-5kw/verification/engineering_checks/routing_quality_power_compare.md), [control](../examples/sic-buck-400v-200v-5kw/verification/engineering_checks/routing_quality_control_compare.md); schematic readability: [power](../examples/sic-buck-400v-200v-5kw/verification/engineering_checks/schematic_readability_power.md), [control](../examples/sic-buck-400v-200v-5kw/verification/engineering_checks/schematic_readability_control.md)
- [Before / after routing crops](../examples/sic-buck-400v-200v-5kw/review/crops) (`<area>_{v2,v21}_{top,bottom}.png`, about 2400 px long side, identical framing)
- Schematic PDFs: [power board](../examples/sic-buck-400v-200v-5kw/review/schematic_power.pdf), [control board](../examples/sic-buck-400v-200v-5kw/review/schematic_control.pdf) (V2 copies under `examples/sic-buck-400v-200v-5kw/releases/v2/review/`)
- Layout PDFs: [power board](../examples/sic-buck-400v-200v-5kw/review/pcb_layout_power.pdf), [control board](../examples/sic-buck-400v-200v-5kw/review/pcb_layout_control.pdf)
- Power board renders: [front](../examples/sic-buck-400v-200v-5kw/review/pcb_front_power.png), [back](../examples/sic-buck-400v-200v-5kw/review/pcb_back_power.png), [3D](../examples/sic-buck-400v-200v-5kw/review/pcb_3d_power.png)
- Control board renders: [front](../examples/sic-buck-400v-200v-5kw/review/pcb_front_control.png), [back](../examples/sic-buck-400v-200v-5kw/review/pcb_back_control.png), [3D](../examples/sic-buck-400v-200v-5kw/review/pcb_3d_control.png)
- [Frozen V2.1](../examples/sic-buck-400v-200v-5kw/releases/v2.1/README.md) (1015 files, `SHA256SUMS.json`, source commit `4f533ac`)
- [Portable V2.1 review archive](../examples/sic-buck-400v-200v-5kw/releases/v2.1-review-package.zip)

## V2 status

The V2 CAD is complete on `feat/sic-buck-5kw-v2`: 22 schematic sheets on two KiCad
projects, 237 + 207 components, a routed 240 x 180 mm four-layer power board and a
routed 120 x 80 mm four-layer control board, both at zero native DRC findings
(`--schematic-parity --severity-all --refill-zones`, stored fills re-checked without
refill), exact netlist matches and 11 verified export commands per board. Six power-board
and two control-board layout-metric rows exceed their review thresholds, and ten review
findings are marked NOT APPLIED in
`examples/sic-buck-400v-200v-5kw/verification/optimisation_finding_status_pass2.json`
(six should-fix: LR-22, LR-24, LR-26, LR-27, LR-32, LR-33; four notes: LR-29, LR-31,
LR-34, LR-35), with LR-25, LR-28 and LR-30 partly applied; see
[V2 execution status](status-v2.md) for the milestone table, the open review
priorities and the freeze and GitHub handoff state.

- [V2 design report](../examples/sic-buck-400v-200v-5kw/review/design_report.md)
- [V2 known issues](../examples/sic-buck-400v-200v-5kw/verification/known_issues.md)
- [Knowledge utilisation report](../examples/sic-buck-400v-200v-5kw/review/knowledge_utilisation_report.md)
- Schematic PDFs: [power board](../examples/sic-buck-400v-200v-5kw/review/schematic_power.pdf), [control board](../examples/sic-buck-400v-200v-5kw/review/schematic_control.pdf)
- Layout PDFs: [power board](../examples/sic-buck-400v-200v-5kw/review/pcb_layout_power.pdf), [control board](../examples/sic-buck-400v-200v-5kw/review/pcb_layout_control.pdf)
- Power board renders: [front](../examples/sic-buck-400v-200v-5kw/review/pcb_front_power.png), [back](../examples/sic-buck-400v-200v-5kw/review/pcb_back_power.png), [3D](../examples/sic-buck-400v-200v-5kw/review/pcb_3d_power.png)
- Control board renders: [front](../examples/sic-buck-400v-200v-5kw/review/pcb_front_control.png), [back](../examples/sic-buck-400v-200v-5kw/review/pcb_back_control.png), [3D](../examples/sic-buck-400v-200v-5kw/review/pcb_3d_control.png)
- [Verification summary](../examples/sic-buck-400v-200v-5kw/verification/verification-summary.json)
- [V2 execution status](status-v2.md)
- [V2 reproduction instructions](reproduce-v2.md)
- [Knowledge-base feedback from V2](knowledge-feedback-v2.md)
- [Frozen V2](../examples/sic-buck-400v-200v-5kw/releases/v2/README.md) (868 files, `SHA256SUMS.json`, source commit `f72052f`)
- [Portable V2 review archive](../examples/sic-buck-400v-200v-5kw/releases/v2-review-package.zip)

## V1 status

The V1 converter CAD is complete on `codex/v1-buck-1kw`: 14 schematic sheets,
240 physical items, a fully routed 300 x 220 mm six-layer PCB, and zero native
ERC/DRC findings. Connectivity, source/export hashes and all eleven export
commands are verified. This establishes a CAD review package, not a validated
1 kW converter. See [execution status](status.md) for freeze and GitHub
handoff state.

- [V1 design report](../examples/buck-48v-24v-1kw/review/design_report.md)
- [Schematic PDF](../examples/buck-48v-24v-1kw/review/schematic.pdf)
- [PCB layer and assembly PDF](../examples/buck-48v-24v-1kw/review/pcb_layout.pdf)
- [Board 3D view](../examples/buck-48v-24v-1kw/review/pcb_3d.png)
- [Known issues](../examples/buck-48v-24v-1kw/verification/known_issues.md)
- [Verification summary](../examples/buck-48v-24v-1kw/verification/verification-summary.json)
- [Reproduction instructions](reproduce-v1.md)
- [Frozen V1](../examples/buck-48v-24v-1kw/releases/v1/README.md)
- [Portable V1 review archive](../examples/buck-48v-24v-1kw/releases/v1-review-package.zip)

## Engineering Knowledge System (V0)

AIPE now learns from manufacturer reference designs. The
[knowledge base](../knowledge/README.md) holds traceable, reusable power-electronics
knowledge extracted from TI TIDA-010054 and Wolfspeed CGD15SG00D2,
CGD1700HB2M-UNA and PRD-04814: six engineering Skills (SiC gate drivers,
gate-driver layout, DC-link capacitors, isolated gate bias, sensing, thermal
placement), 13 circuit building blocks, 19 component records and 43
machine-readable rules — each with evidence locations and an explicit
validation status (reference-derived or analytically checked; nothing is
simulated or hardware-validated yet).

```text
python -m automation.knowledge.query "recommended layout practices for an isolated SiC gate driver"
python -m automation.knowledge.validate
```

- [Architecture and reference-learning workflow](knowledge-system.md)
- [V0 status and findings](knowledge-status.md)
- [Retrieval demonstration](../knowledge/examples/retrieval-demo.md)

Raw manufacturer files are downloaded to the Git-ignored `.cache/references/`
by `python -m automation.knowledge.acquire`; only original analysis and
metadata are committed.

## Start here

- [Original task](../task071026.txt) and [execution constraints](../agents/CODEX_V1_TASK.md)
- [V2 task](../task09102026.txt), [V2 requirements](../examples/sic-buck-400v-200v-5kw/input/requirements.yaml) and [V2 execution status](status-v2.md)
- [V2.1 task](../task11102026.txt) (schematic readability and routing quality) and [V2.1 execution status](status-v2.1.md)
- [Workflow and acceptance gates](agent-workflow.md)
- [Automation architecture](architecture.md)
- [Installation proposal](installation-plan.md)
- [Host environment](environment.md)
- [PCB engineering rules](pcb-design-rules.md) and [knowledge rules](../knowledge/rules/engineering_rules.json)
- [Benchmark requirements](../examples/buck-48v-24v-1kw/input/requirements.yaml)

## Environment inspection

From the repository root, using an existing Python 3.10 or newer interpreter:

```text
python -m automation.setup.detect_environment --output .aipe/environment.json --markdown docs/environment.md
python -m unittest discover -s tests -v
```

The detector uses the Python standard library and does not install software.
Machine-specific paths belong in ignored `.aipe/local-tools.json`, using
`automation/setup/local-tools.example.json` as a template. Installing software
or dependencies requires the user's confirmation of both software and location.
