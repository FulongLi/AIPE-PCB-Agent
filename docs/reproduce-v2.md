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

The V2.1 regeneration (wired schematics, upgraded router, generator gates, readability and
routing-quality reports, `freeze_release`) is described in the
[V2.1 section](#v21-schematic-presentation-and-routing-geometry) at the end of this file.
Everything before it describes V2 and still holds (where that part says "delivered board" it means the
V2 board, now frozen under `releases/v2/`; the live `kicad/` boards are the V2.1 generation); the V2 paths
remain reachable as
`--style legacy` (schematics), `--style none` (power board) and `--no-style` (control board).

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

Shared-router caveat (V2 history): the V2 control board was routed with
`automation/kicad_tools/grid_router.py` at sha256 `b78a49cc48f2c82656a382e94078d9cb442a54ad4d3e68f7237161798c48c7b3`
(`shared_router_sha256` in `releases/v2/verification/routing_progress_control.json`); the power-board
convergence changed the module to `c666ba734e5450014c683fafc87b9e4debffc9e4dddba71a28dd0f07416df860`
(`current_repository_router_sha256` in `verification/engineering_checks/control_regeneration_check.json`,
written 2026-10-11), and V2.1 changed it again: the delivered V2.1 control board records
`5850b26ee2d7c6f1de9ebad7dd18d0eeb8a09e2bc57dfb4c2b2d095149473a0a` (`shared_router_sha256` in
`verification/routing_progress_control.json`), which is the hash of the current module.
A scratch regeneration of candidate B with the module of 2026-10-11 (`c666ba73...`;
`verification/engineering_checks/control_regeneration_check.json`, diagnostic) reproduced
every track, via, footprint and zone of the V2 control board (`releases/v2/kicad/control_board/`, sha256
`dead06ed18d851542f76d7175ec4a1cfff3fa2ee4a69203e33f15d1d008f1288`; 5995 / 798 / 207 / 20, 0 items
present in only one board, uuids and timestamps ignored) with 0 unresolved connections;
the file hashes differ through uuids and timestamps only, and a DRC of the regenerated
board inside a project copy gave 0 unconnected / 0 schematic-parity plus one
`lib_footprint_issues` warning attributed to the copied library path. This is one observed
reproduction with the newer module, not a determinism guarantee: repeated runs with a
single module version were not performed at that time (the V2.1 section records the later
determinism check of the control board), byte-identical files are not promised, and the
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

`freeze_v2` runs `verify_sic_buck` first and refuses to freeze when it fails. It was run
on 2026-10-11 from commit `f72052f` and wrote `releases/v2/` (868 files, `README.md`,
`SHA256SUMS.json`) plus `releases/v2-review-package.zip`; the snapshot must never be edited.
Running the command again fails on purpose (`releases/v2` already exists); a later reviewed
generation gets its own snapshot.

## Knowledge system

The design decisions cite knowledge ids (`SKILL-*`, `KR-*`, `CB-*`, `CMP-*`, `REF-*`).
`python -m automation.knowledge.query --get <ID> --json` prints a record with its related
items; `design/knowledge_trace.md` lists every citation with its applicability class;
`review/knowledge_utilisation_report.md` traces each design decision to the knowledge
retrieved, the verification performed and the resulting status. Proposed corrections
to the knowledge base are collected in `docs/knowledge-feedback-v2.md`; nothing under
`knowledge/` was changed by V2.

## V2.1 (schematic presentation and routing geometry)

**AI-GENERATED ENGINEERING PROTOTYPE V2.1 - HUMAN REVIEW REQUIRED**

V2.1 (branch `feat/sic-buck-v2.1-quality`) regenerates the same example with the wired schematic
presentation and the upgraded grid router. The electrical model, the design baseline, the placement
inputs, the rules, `knowledge/` and `releases/v2/` are unchanged. The options below are what
`--help` printed on 2026-10-12 (host Python 3.10, KiCad 10.0.7); the V2 caveats above (a
regeneration changes the verification state, only `run_check` manifests are evidence) apply
unchanged.

### Schematics

```text
python -m automation.kicad_tools.generate_sic_schematics --board all --erc --pdf --bom --gates --readability
  --board {power,control,all}
  --erc                   run native kicad-cli ERC into verification/erc
  --pdf                   export review/schematic_<board>.pdf
  --bom                   write components/bom.csv from the two board BOMs
  --style {wired,legacy}  drawing style (default wired)
  --gates                 run the V2.1 gates (DRU identity, net_settings, ERC 0, netlist vs model and V2)
  --readability           write verification/engineering_checks/schematic_readability_<board>.{json,md}
                          (V2 release vs this generation)
```

`--style wired` is the default (`AIPE_SCHEMATIC_STYLE=legacy` in the environment changes it) and
draws through `schematic_presentation`; `--style legacy` draws the V2 one-global-label-per-pin style
from the same model (code path unchanged); its sheets differ from the V2 release in the generation label
(rev `V2.1` and the V2.1 banner: `generate_sic_schematics.py`, `REVISION = common.GENERATION`), and no byte
comparison against `releases/v2` is committed (a scratch check is noted in `scratchpad/v21/progress_schematic.md`,
not in the repository). `--gates` writes `verification/schematic_gates/<board>/schematic_gates.json`
with six gates: `.kicad_dru` identical to a legacy generation of the same model, `.kicad_pro`
`net_settings` equal, native ERC 0 with `--severity-all` (manifest under
`schematic_gates/<board>/erc/`), exported netlist `(ref, pad) -> net` exact against the live model
and against `releases/v2/manufacturing/<board>/netlist.xml` with equal net names, and `paper_fill`
>= 0.25 for every sheet escalated beyond A3. Run the gates from the repository path, not from a
subst or junction path: KiCad then cannot resolve `${KIPRJMOD}` and reports
`footprint_link_issues`, which the gate lists separately and does not waive. `--readability`
compares the generated sheets with `releases/v2/kicad/<board>` through
`schematic_metrics.compare_projects` (one definition for both generations). The generator removes
stale continuation sheets of the previous generation (`*_2.kicad_sch`) and refuses to write a
project whose drawn geometry does not reproduce the model
(`design/connectivity_guard_failure.json`).

A schematic regeneration writes `kicad/<board>_board/` (sheets, symbol library, project,
`.kicad_dru`, libraries), `design/schematic_mapping_<board>.json` and the date line of
`design/netlist_<board>.xml`; with the flags also `verification/erc/<run>/`,
`review/schematic_<board>.pdf`, `components/bom.csv`, `verification/schematic_gates/<board>/` and
the readability report pair. The boards must be regenerated afterwards, because
`--schematic-parity` compares symbol paths that the regeneration changes
(`verification/routing_iterations_power.md`, section 16).

### Boards

```text
python automation/kicad_tools/generate_sic_power_board.py [--output OUTPUT] [--no-route] [--no-drc]
       [--no-metrics] [--no-reexec] [--trials TRIALS] [--ripup RIPUP] [--outputs OUTPUTS]
       [--style {default,v21,octilinear,none}]
  --outputs OUTPUTS   scratch build: write the netlist, placement, routing plan, progress JSON,
                      engineering checks and DRC manifests under this directory instead of the
                      example design/ and verification/ folders (candidate comparison; not verification)
  --style             grid_router geometry: default = ROUTING_STYLE, v21 = ROUTING_STYLE_V21
                      (8-direction search, simplification, arcs), octilinear = ROUTING_STYLE_OCTILINEAR
                      (4-direction search, simplification, arcs), none = V2

python automation/kicad_tools/generate_sic_control_board.py [--candidate {A,B}] [--scratch SCRATCH]
       [--output OUTPUT] [--no-route] [--no-drc] [--no-metrics] [--no-style] [--no-reexec]
  --no-style          route with the V2 geometry (no 8-direction search, simplification or arcs)
```

The delivered power board is `--style default` = `ROUTING_STYLE_OCTILINEAR` (the V2 4-direction
search, octilinear simplification, chamfers, tangent arcs, `PE` untouched, eps 0.01; 4 trials, 30
rip-up rounds): 3136 tracks of which 145 arcs, 606 vias, 0 unresolved, routing 769 s
(`verification/routing_progress_power.json`). The delivered control board is `--candidate B` with
the default `ROUTING_STYLE` (same pass, eps 0.02; 6 trials, 240 rip-up rounds): 4523 tracks of
which 261 arcs, 798 vias, 0 unresolved, routing 1218 s (`routing_progress_control.json`).
`--style v21` (power) and `ROUTING_STYLE_DIAGONAL` (control, `build_control(style=...)`, no CLI
flag) add the 8-direction search with bend penalties; they are opt-in because they left
connections open and exceeded the V2 run time on both boards (`routing_iterations_<board>.md`,
V2.1 sections). `--style none` / `--no-style` route the V2 geometry with the current generators: on
the power board this reproduced the frozen V2 quality totals exactly (attempt C in section 16.3);
on the control board the layer-aware `prune_dangling` and eps 0.02 can make routes differ from the
frozen file.

In addition to the V2 outputs listed above, a board regeneration writes
`verification/engineering_checks/routing_quality_<board>{,_v2,_compare}.{json,md}` (the V2
baseline measured on `releases/v2`, this board with plan / report / DRC linkage, and the deltas),
the `style`, `arcs`, `beautify` and `routing_quality` fields of `routing_progress_<board>.json`,
the stored-fill diagnostic for both boards, and for the control board the `zone_table` record.

### Checkers on existing boards and sheets (read-only except their output directory)

```text
<kicad-python> automation/verification/check_routing_quality.py <before.kicad_pcb> --compare <after.kicad_pcb> --output <dir> --label <name>
<kicad-python> automation/verification/check_routing_quality.py <board.kicad_pcb> --output <dir> --label <name> [--plan design/routing_plan_<board>.json] [--report verification/routing_progress_<board>.json] [--drc verification/drc/<run>/run.json] [--baseline <routing_quality_x.json>]
python -m automation.kicad_tools.schematic_metrics <kicad_dir> [--json out.json]
python -m automation.kicad_tools.schematic_metrics <kicad_dir> --compare <older kicad_dir> [--mapping design/schematic_mapping_<board>.json] --json c.json --markdown c.md
```

`check_routing_quality.py` re-executes itself under KiCad's Python when `pcbnew` is not importable
(`--no-reexec` is internal). In compare mode the positional board is the "before" board and
`--compare` the "after" board; the one-shot compare writes the before measurement into
`routing_quality_<label>.json`, so the delivered reports were produced in three steps (V2 board
-> `_v2`, new board with `--plan --report --drc --baseline` -> `<board>`, compare -> `_compare`).
Dispositions are "measured - human review required": geometry only, no inductance, EMI or
current-capacity claim.

### Determinism

The same inputs reproduce the copper and the zones, not the file bytes. Power: a `--style none`
regeneration reproduced the frozen V2 quality totals exactly, and the default style only rewrites
the final geometry of that search. Control: since commit `7f93a61` the stage-2 corridor zones are
sorted (`corridor_sort_key`) before their priorities are assigned and every zone gets a
deterministic KIID (`zone_identity`); the repository board and an independent second full build
have identical zone tables (20 zones: priorities, outlines, filled areas, KIIDs), identical tracks,
arcs and vias per layer, and per-net length sums equal within 0.001 mm
(`verification/routing_iterations_control.md`, "Final state (run 13)";
`verification/v21_validation.md`, item D). The `.kicad_pcb` bytes differ between builds through
the random KIIDs of tracks, vias and footprints, so compare geometry (the quality checker,
`pcbnew`), not hashes. The delivered boards are verified by their own DRC manifests and hashes,
which do not depend on the router.

### Release

```text
python -m automation.scripts.freeze_release --version v2.1
```

`freeze_release` (the generalised `freeze_v2`) runs `verify_sic_buck` first and refuses when it
fails; it writes `releases/v2.1/` (`README.md` with the V2.1 label, `SHA256SUMS.json` with the
source commit, every example folder without the full-length waveforms) and
`releases/v2.1-review-package.zip`, and refuses to run when the snapshot already exists. The V2.1
freeze runs after this section was written; `docs/status-v2.1.md` records its result.
