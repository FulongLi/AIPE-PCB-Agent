# AIPE-PCB-Agent

AI-assisted power-electronics PCB engineering with reproducible KiCad automation.

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
[V2 execution status](docs/status-v2.md) for the milestone table, the open review
priorities and the freeze and GitHub handoff state.

- [V2 design report](examples/sic-buck-400v-200v-5kw/review/design_report.md)
- [V2 known issues](examples/sic-buck-400v-200v-5kw/verification/known_issues.md)
- [Knowledge utilisation report](examples/sic-buck-400v-200v-5kw/review/knowledge_utilisation_report.md)
- Schematic PDFs: [power board](examples/sic-buck-400v-200v-5kw/review/schematic_power.pdf), [control board](examples/sic-buck-400v-200v-5kw/review/schematic_control.pdf)
- Layout PDFs: [power board](examples/sic-buck-400v-200v-5kw/review/pcb_layout_power.pdf), [control board](examples/sic-buck-400v-200v-5kw/review/pcb_layout_control.pdf)
- Power board renders: [front](examples/sic-buck-400v-200v-5kw/review/pcb_front_power.png), [back](examples/sic-buck-400v-200v-5kw/review/pcb_back_power.png), [3D](examples/sic-buck-400v-200v-5kw/review/pcb_3d_power.png)
- Control board renders: [front](examples/sic-buck-400v-200v-5kw/review/pcb_front_control.png), [back](examples/sic-buck-400v-200v-5kw/review/pcb_back_control.png), [3D](examples/sic-buck-400v-200v-5kw/review/pcb_3d_control.png)
- [Verification summary](examples/sic-buck-400v-200v-5kw/verification/verification-summary.json)
- [V2 execution status](docs/status-v2.md)
- [V2 reproduction instructions](docs/reproduce-v2.md)
- [Knowledge-base feedback from V2](docs/knowledge-feedback-v2.md)
- Frozen V2: not yet written when this README was updated (`examples/sic-buck-400v-200v-5kw/releases/` is empty); `automation/scripts/freeze_v2.py` will create `releases/v2/` (`README.md`, `SHA256SUMS.json`) and `releases/v2-review-package.zip` there, and [docs/status-v2.md](docs/status-v2.md) records whether it has run

## V1 status

The V1 converter CAD is complete on `codex/v1-buck-1kw`: 14 schematic sheets,
240 physical items, a fully routed 300 x 220 mm six-layer PCB, and zero native
ERC/DRC findings. Connectivity, source/export hashes and all eleven export
commands are verified. This establishes a CAD review package, not a validated
1 kW converter. See [execution status](docs/status.md) for freeze and GitHub
handoff state.

- [V1 design report](examples/buck-48v-24v-1kw/review/design_report.md)
- [Schematic PDF](examples/buck-48v-24v-1kw/review/schematic.pdf)
- [PCB layer and assembly PDF](examples/buck-48v-24v-1kw/review/pcb_layout.pdf)
- [Board 3D view](examples/buck-48v-24v-1kw/review/pcb_3d.png)
- [Known issues](examples/buck-48v-24v-1kw/verification/known_issues.md)
- [Verification summary](examples/buck-48v-24v-1kw/verification/verification-summary.json)
- [Reproduction instructions](docs/reproduce-v1.md)
- [Frozen V1](examples/buck-48v-24v-1kw/releases/v1/README.md)
- [Portable V1 review archive](examples/buck-48v-24v-1kw/releases/v1-review-package.zip)

## Engineering Knowledge System (V0)

AIPE now learns from manufacturer reference designs. The
[knowledge base](knowledge/README.md) holds traceable, reusable power-electronics
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

- [Architecture and reference-learning workflow](docs/knowledge-system.md)
- [V0 status and findings](docs/knowledge-status.md)
- [Retrieval demonstration](knowledge/examples/retrieval-demo.md)

Raw manufacturer files are downloaded to the Git-ignored `.cache/references/`
by `python -m automation.knowledge.acquire`; only original analysis and
metadata are committed.

## Start here

- [Original task](task071026.txt) and [execution constraints](agents/CODEX_V1_TASK.md)
- [V2 task](task09102026.txt), [V2 requirements](examples/sic-buck-400v-200v-5kw/input/requirements.yaml) and [V2 execution status](docs/status-v2.md)
- [Workflow and acceptance gates](docs/agent-workflow.md)
- [Automation architecture](docs/architecture.md)
- [Installation proposal](docs/installation-plan.md)
- [Host environment](docs/environment.md)
- [PCB engineering rules](docs/pcb-design-rules.md) and [knowledge rules](knowledge/rules/engineering_rules.json)
- [Benchmark requirements](examples/buck-48v-24v-1kw/input/requirements.yaml)

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
