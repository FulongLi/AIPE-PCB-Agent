# Reproducing and checking V2 (SiC buck 400 V to 200 V, 5 kW)

**AI-GENERATED ENGINEERING PROTOTYPE V2 - HUMAN REVIEW REQUIRED**

V2 lives under `examples/sic-buck-400v-200v-5kw/` and was produced on Windows with
Python 3.10 (standard library plus the already-installed numpy, scipy and shapely recorded
in `verification/environment/smoke-test-2026-10-10.json`, and pymupdf for datasheet text
extraction, which the environment files do not record) and KiCad 10.0.7 (`kicad-cli`, the
bundled Python with `pcbnew`, and the bundled `ngspice.dll`). No software was installed;
tool paths are read from `.aipe/local-tools.json` or discovered as described in
`docs/environment.md`. Nothing below modifies the frozen V1 example. The exported
manufacturing formats are review material only: nothing in this guide authorises
fabrication, purchase or energisation, and no firmware exists.

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
libraries, net classes and the `.kicad_dru` rules, both the class-pair rules and the
per-footprint pin-field exceptions), runs native ERC into
`verification/erc`, exports the review PDFs and the merged BOM. The simulation driver
regenerates the twenty ngspice runs and their full waveform CSV files, which are not
committed because of their size.

## Regenerate the boards

Both generators re-execute themselves under the KiCad Python interpreter when started
from the host Python (`--no-reexec` is the internal flag that stops this), so plain
`python` from the repository root works; `D:/EngineeringTools/KiCad/10.0/bin/python.exe`
can be used directly instead. The options below are what `--help` printed on
2026-10-11 (host Python 3.10, KiCad 10.0.7):

```text
python automation/kicad_tools/generate_sic_power_board.py --help
usage: generate_sic_power_board.py [-h] [--output OUTPUT] [--no-route] [--no-drc]
                                   [--no-metrics] [--no-reexec] [--trials TRIALS]
                                   [--ripup RIPUP]
  --output OUTPUT
  --no-route
  --no-drc
  --no-metrics
  --no-reexec
  --trials TRIALS  signal routing-order trials (default 4)
  --ripup RIPUP    rip-up negotiation rounds (default 30)

python automation/kicad_tools/generate_sic_control_board.py --help
usage: generate_sic_control_board.py [-h] [--candidate {A,B}] [--scratch SCRATCH]
                                     [--output OUTPUT] [--no-route] [--no-drc]
                                     [--no-metrics] [--no-reexec]
  --candidate {A,B}  build only this candidate (default: compare A and B, build the winner)
  --scratch SCRATCH  scratch directory for the candidate boards and their metrics
  --output OUTPUT    board file of the built candidate
  --no-route         placement only
  --no-drc           skip the kicad-cli DRC (debugging only; never evidence)
  --no-metrics       skip the layout metrics checker
  --no-reexec        internal: do not re-execute under KiCad Python
```

The power generator prints no description for `--output`, `--no-route`, `--no-drc` and
`--no-metrics`; from its `main()`: `--output` defaults to the delivered
`kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb`, `--no-route` stops after placement
and pours, `--no-drc` skips the `kicad-cli` DRC (never evidence) and `--no-metrics`
skips the layout checker. The control generator's `--output` defaults to the delivered
`kicad/control_board/AIPE_SiC_Buck_Control.kicad_pcb` and `--scratch` to
`.aipe/control-board-candidates`. The delivered boards were produced with the defaults
(power: `--trials 4 --ripup 30`; `verification/routing_progress_power.json` records 12
order-trial entries because the trials run per routing group, 4 in each of the 3 groups
HS / PG / SELV, and 21 rip-up round entries, rounds 0-20 of the 30 allowed; control:
candidate B) - see `verification/routing_iterations_<board>.md` (power: sections 13.1
and 15.2).

**A regeneration changes the verification state of the example.** With the default
`--output` the delivered board file is overwritten. Independently of `--output`, both
generators write into the example: `design/placement_<board>.json`,
`design/routing_plan_<board>.json`, `verification/routing_progress_<board>.json`,
`verification/engineering_checks/layout_metrics_<board>.{json,md}` (unless
`--no-metrics`) and a new `run_check` DRC manifest under `verification/drc/` (unless
`--no-drc`); the control generator also rewrites
`review/floorplan_candidates_control.{json,md}` when it compares candidates, and the
power generator writes `engineering_checks/stored_zone_fill_check_power.json`.
`verify_sic_buck` requires the LATEST DRC manifest of each board to pass and to match
the delivered board hash, so after any regeneration either work in a scratch copy of
the repository, or re-run `verify_sic_buck` and expect it to judge the regenerated
board, not the delivered one. Routing is a geometric proposal: only the `kicad-cli` DRC
manifest (schematic parity, all severities, refilled zones) counts as verification, and
`verification/routing_progress_<board>.json` lists every connection the router could
not complete (`unresolved_count` 0 for both delivered boards).

Placement sources: the power generator carries its floorplan table and routing regions
in the module itself (`FIXED`, `REGIONS`) and writes `design/placement_power.json` as
the record of what it placed; the control generator places from
`design/floorplan_candidates/control_<A|B>.json`. The candidates compared before
selection are kept under `design/floorplan_candidates/` with their comparison in
`review/floorplan_candidates_<board>.md`. Candidate B of the power board was amended
on 2026-10-11 (C6 / C8 moved from y 137.0 to 135.5 mm) so that the slotted UCC21710
footprint introduced by the structural DRC fixes no longer overlaps them and the
stage-1 floorplan tool places it again; the scores were not recomputed and the
delivered power board had already moved away from that candidate during routing
convergence (`review/floorplan_candidates_power.md`, amendment section).

Shared-router caveat: the delivered control board was routed with
`automation/kicad_tools/grid_router.py` at sha256 `b78a49cc48f2c82656a382e94078d9cb442a54ad4d3e68f7237161798c48c7b3`
(`shared_router_sha256` in `verification/routing_progress_control.json`); the power-board
convergence changed the module afterwards (now `c666ba734e5450014c683fafc87b9e4debffc9e4dddba71a28dd0f07416df860`).
A scratch regeneration of candidate B with the current module
(`verification/engineering_checks/control_regeneration_check.json`, diagnostic) reproduced
every track, via, footprint and zone of the delivered board (5995 / 798 / 207 / 20, 0 items
present in only one board, uuids and timestamps ignored) with 0 unresolved connections;
the file hashes differ through uuids and timestamps only, and a DRC of the regenerated
board inside a project copy gave 0 unconnected / 0 schematic-parity plus one
`lib_footprint_issues` warning attributed to the copied library path. This is one observed
reproduction with the newer module, not a determinism guarantee: repeated runs with a
single module version were not performed, byte-identical files are not promised, and the
delivered boards are verified by their own DRC manifests and hashes, which do not depend
on the router.

Checks on the delivered boards (read-only except for the new manifest or output
directory they write):

```text
python -m automation.kicad_tools.run_check drc examples/sic-buck-400v-200v-5kw/kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb --output examples/sic-buck-400v-200v-5kw/verification/drc
python -m automation.kicad_tools.run_check drc examples/sic-buck-400v-200v-5kw/kicad/control_board/AIPE_SiC_Buck_Control.kicad_pcb --output examples/sic-buck-400v-200v-5kw/verification/drc
<kicad-python> automation/verification/check_sic_layout.py <board.kicad_pcb> --spec examples/sic-buck-400v-200v-5kw/verification/engineering_checks/layout_spec_<board>.json --model examples/sic-buck-400v-200v-5kw/design/circuit_<board>.json
<kicad-python> automation/verification/netlist_check_sic.py --board power
<kicad-python> automation/verification/netlist_check_sic.py --board control
python -m automation.kicad_tools.export_outputs examples/sic-buck-400v-200v-5kw/kicad/power_board/AIPE_SiC_Buck_Power.kicad_pro --output <fresh directory> --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.SilkS,B.SilkS,F.Fab,Edge.Cuts
```

A `run_check` DRC of an unchanged delivered board adds a manifest for the same source
hash and keeps the verifier valid; the stored-fill diagnostic
(`engineering_checks/stored_zone_fill_check_<board>.json`) is a DRC without
`--refill-zones` on a temporary copy and is not itself verification evidence.

## Release

```text
python -m automation.scripts.freeze_v2
```

`freeze_v2` runs `verify_sic_buck` first and refuses to freeze when it fails. At the time
of writing `freeze_v2` has not run and `releases/` is empty (`docs/status-v2.md` records
when it runs). When the orchestrator runs it, the snapshot under `releases/v2/` will carry
`SHA256SUMS.json` plus `releases/v2-review-package.zip` and must never be edited afterwards.

## Knowledge system

The design decisions cite knowledge ids (`SKILL-*`, `KR-*`, `CB-*`, `CMP-*`, `REF-*`).
`python -m automation.knowledge.query --get <ID> --json` prints a record with its related
items; `design/knowledge_trace.md` lists every citation with its applicability class;
`review/knowledge_utilisation_report.md` traces each design decision to the knowledge
retrieved, the verification performed and the resulting status. Proposed corrections
to the knowledge base are collected in `docs/knowledge-feedback-v2.md`; nothing under
`knowledge/` was changed by V2.
