# Reproducing and checking V2 (SiC buck 400 V to 200 V, 5 kW)

**AI-GENERATED ENGINEERING PROTOTYPE V2 - HUMAN REVIEW REQUIRED**

V2 lives under `examples/sic-buck-400v-200v-5kw/` and was produced on Windows with
Python 3.10 (standard library plus the already-installed numpy, scipy, shapely and
pymupdf) and KiCad 10.0.7 (`kicad-cli`, the bundled Python with `pcbnew`, and the
bundled `ngspice.dll`). No software was installed; tool paths are read from
`.aipe/local-tools.json` or discovered as described in `docs/environment.md`. Nothing
below modifies the frozen V1 example.

## Inspect without changing anything

```text
python -m unittest discover -s tests -v
python -m automation.knowledge.query "SiC gate driver negative bias" --json
python -m automation.scripts.knowledge_trace
python -m automation.scripts.verify_sic_buck
python -m automation.scripts.compare_v1_v2
```

`verify_sic_buck` requires the LATEST native ERC and DRC run of each board to have
zero findings and to match the delivered KiCad files by hash, plus intact export
manifests, netlist checks and layout metrics; it writes
`verification/verification-summary.json`. Read `verification/known_issues.md` and
`review/design_report.md` before any physical work.

## Regenerate the design record

Run from the repository root. Use the KiCad Python executable for anything that
imports `pcbnew`.

```text
python -m automation.scripts.calculate_sic_buck
python -m automation.kicad_tools.sic_buck_power_model
python -m automation.kicad_tools.sic_buck_control_model
python -m automation.kicad_tools.generate_sic_schematics --board all --erc --pdf --bom
python examples/sic-buck-400v-200v-5kw/simulation/results/run_campaign.py
```

`calculate_sic_buck` rebuilds `design/calculations.json` and `calculations.md` from the
baseline `design/design_decisions.json` and asserts its invariants. The two model
modules rebuild `design/circuit_<board>.json` and `components/bom_<board>.csv`;
`generate_sic_schematics` rebuilds both KiCad projects (schematics, project-local
libraries, net classes and the `.kicad_dru` class-pair rules), runs native ERC into
`verification/erc`, exports the review PDFs and the merged BOM. The simulation driver
regenerates the twenty ngspice runs and their full waveform CSV files, which are not
committed because of their size.

## Regenerate the boards

```text
<kicad-python> automation/kicad_tools/generate_sic_power_board.py --help
<kicad-python> automation/kicad_tools/generate_sic_control_board.py --help
python -m automation.kicad_tools.run_check drc examples/sic-buck-400v-200v-5kw/kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb --output examples/sic-buck-400v-200v-5kw/verification/drc
python -m automation.kicad_tools.run_check drc examples/sic-buck-400v-200v-5kw/kicad/control_board/AIPE_SiC_Buck_Control.kicad_pcb --output examples/sic-buck-400v-200v-5kw/verification/drc
<kicad-python> automation/verification/check_sic_layout.py <board.kicad_pcb> --spec examples/sic-buck-400v-200v-5kw/verification/engineering_checks/layout_spec_<board>.json --model examples/sic-buck-400v-200v-5kw/design/circuit_<board>.json
<kicad-python> automation/verification/netlist_check_sic.py --board power
<kicad-python> automation/verification/netlist_check_sic.py --board control
python -m automation.kicad_tools.export_outputs examples/sic-buck-400v-200v-5kw/kicad/power_board/AIPE_SiC_Buck_Power.kicad_pro --output <fresh directory> --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.SilkS,B.SilkS,F.Fab,Edge.Cuts
```

The board generators place from `design/placement_<board>.json`, route with the grid
router according to `design/routing_plan_<board>.json`, fill zones, inject the stack-up
text and save; the floorplan candidates that were compared before selection are kept
under `design/floorplan_candidates/` with their comparison in
`review/floorplan_candidates_<board>.md`. Routing is a geometric proposal: only the
`kicad-cli` DRC manifest (schematic parity, all severities) in `verification/drc`
counts as verification, and `verification/routing_progress_<board>.json` lists every
connection the router could not complete. The grid router is deterministic for a given
plan and KiCad version; byte-identical boards across KiCad versions are not promised.

## Release

```text
python -m automation.scripts.freeze_v2
```

`freeze_v2` runs `verify_sic_buck` first and refuses to freeze when it fails. The frozen
snapshot under `releases/v2/` carries a SHA-256 manifest and must never be edited.

## Knowledge system

The design decisions cite knowledge ids (`SKILL-*`, `KR-*`, `CB-*`, `CMP-*`, `REF-*`).
`python -m automation.knowledge.query --get <ID> --json` prints a record with its related
items; `design/knowledge_trace.md` lists every citation with its applicability class;
`review/knowledge_utilisation_report.md` traces each design decision to the knowledge
retrieved, the verification performed and the resulting status. Proposed corrections
to the knowledge base are collected in `docs/knowledge-feedback-v2.md`; nothing under
`knowledge/` was changed by V2.
