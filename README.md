# AIPE-PCB-Agent

AI-assisted power-electronics PCB engineering with reproducible KiCad automation.

> **AI-GENERATED ENGINEERING PROTOTYPE — V1 — HUMAN REVIEW REQUIRED**

The first benchmark is a 48 V nominal to 24 V, 1 kW synchronous buck converter
with an integrated TMS320F28335 control section. The output current is
approximately 41.7 A. V1 is a review deliverable, not an energisation approval.

## Current status

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

## Start here

- [Original task](task071026.txt) and [execution constraints](agents/CODEX_V1_TASK.md)
- [Workflow and acceptance gates](docs/agent-workflow.md)
- [Automation architecture](docs/architecture.md)
- [Installation proposal](docs/installation-plan.md)
- [Host environment](docs/environment.md)
- [PCB engineering rules](docs/pcb-design-rules.md)
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
