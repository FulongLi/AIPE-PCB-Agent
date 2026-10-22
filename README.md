# AIPE — PCB Agent

AIPE-PCB-Agent is the PCB design automation of the AIPE power-electronics ecosystem. Python generators turn a
requirement file set (specification, insulation table, components, interfaces, floorplan and routing inputs) into
native KiCad 10 projects — hierarchical schematics, placed and grid-routed boards, net classes and design rules —
and run the real `kicad-cli` ERC, DRC and exports with SHA-256 manifests. It sits downstream of
AIPE-Electrical-Design in the AIPE-Workflows pipeline. Its output is an AI-generated engineering prototype for human
review: nothing has been fabricated, energised or measured.

## Features

- Requirement-driven generators (`automation/dab_v1`, `automation/sic_v3`, `automation/kicad_tools`): schematics with
  project libraries, insulation-aware placement, a deterministic grid router with fine-pitch row escapes, pour nets,
  rip-up, time budget and checkpoints.
- Net classes and `.kicad_dru` rules derived from an IEC 60664-1 reference table; values are documented review inputs
  and are never relaxed by the code.
- Native verification: `kicad-cli sch erc`, `pcb drc --schematic-parity --severity-all --refill-zones`, exports
  (Gerber, drill, BOM, placement, STEP, PDF, netlist) with hashed manifests; netlist-equality, routing-quality,
  layout-metric and copper-island checkers.
- Engineering knowledge base (skills, rules, component records) with traceable manufacturer sources.
- Worked examples: SiC buck V1–V3 and the 10 kW dual-active-bridge three-board set DAB-V1.

## Installation

```text
python -m pip install -e ".[test]"          # Python 3.10+; numpy, PyYAML, Shapely, pytest
python -m automation.setup.detect_kicad    # locates an installed KiCad 10 (kicad-cli and its Python); installs nothing
```

## Usage

```text
python -m pytest -q
python -m automation.knowledge.query "recommended layout practices for an isolated SiC gate driver"
python -m automation.dab_v1.pipeline --board primary-power --stages floorplan,copper,route,verify --time-budget 2700
```

The tests run without KiCad (KiCad-dependent tests skip and say so); the pipeline's board stages need KiCad 10.
`--time-budget` time-boxes the router: unrouted nets are reported, the board is still saved and verified.

## Project Information

- Version: 0.1.0 (`pyproject.toml`; first declared version, aligned with `aipe.yaml` schema 0.1.0)
- Status: Prototype. SiC buck V3: two routed boards at zero native ERC/DRC findings. DAB-V1 (re-run of 2026-10-21):
  ERC 0 on all three boards, DRC 0 violations other than unconnected items (18 / 18 / 28 dangling-track warnings),
  26 / 23 / 24 connections still open on primary / secondary / control (from 82 / 81 / 499) - routing candidates, not
  finished boards. No board has been fabricated.
- Developer: Fulong Li
- Organisation: Spirit Connect / AIPE Labs
- License: code — MIT is declared in `aipe.yaml`, but the repository contains no LICENSE file yet (the licence text has
  to be added by the maintainer); KiCad library data under `examples/*/libraries` — CC-BY-SA-4.0 with the KiCad
  library exception (`examples/dab-10kw/control/libraries/LICENSE.md`).

## Documentation

- [Automation architecture](docs/architecture.md), [workflow and acceptance gates](docs/agent-workflow.md),
  [PCB design rules](docs/pcb-design-rules.md), [knowledge system](docs/knowledge-system.md)
- DAB-V1: [example README](examples/dab-10kw/README.md), [architecture review](docs/dab-10kw/architecture-review.md),
  [review report](docs/dab-10kw/review-report.md), [routing remediation](docs/dab-10kw/routing-remediation.md)
- SiC buck examples and milestone history (former README): [docs/history.md](docs/history.md),
  [V3 package](examples/sic-buck-400v-200v-5kw-v3/README.md)
- [Host environment](docs/environment.md), [installation plan](docs/installation-plan.md),
  [CI workflow](.github/workflows/tests.yml)
