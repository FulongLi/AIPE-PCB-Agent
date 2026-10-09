# AIPE-PCB-Agent

AI-assisted power-electronics PCB engineering with reproducible KiCad automation.

> **AI-GENERATED ENGINEERING PROTOTYPE — V1 — HUMAN REVIEW REQUIRED**

The first benchmark is a 48 V nominal to 24 V, 1 kW synchronous buck converter
with an integrated TMS320F28335 control section. The output current is
approximately 41.7 A. V1 is a review deliverable, not an energisation approval.

## Current status

Repository bootstrap and initial environment inspection are complete locally on
`codex/v1-buck-1kw`; KiCad 10.0.7 is installed and the small automation smoke
test passed real ERC/DRC, connectivity and export checks. No converter
schematic, PCB, passing CAD checks, or frozen
V1 release exists yet. See [execution status](docs/status.md).

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
