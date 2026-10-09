# KiCad automation smoke test

This is a passive 10k/10k divider with a three-pin connector. It is not the
1 kW converter. Sources, reports and outputs demonstrate the CAD pipeline only.

The 25 x 18 mm, two-layer board has three components, three nets, routed top and
bottom tracks, a through via and a filled bottom ground zone. All symbol pins
are connected. Official KiCad symbols and footprints are retained locally as
small library subsets. KiCad's installed 3D library supplies the component models.

## Run

1. Configure the existing KiCad CLI/Python in `.aipe/local-tools.json`.
2. Run `automation/kicad_tools/generate_smoke.py` using KiCad's bundled Python.
3. Run `python -m automation.kicad_tools.run_check erc examples/automation-smoke/kicad/AIPE_Smoke.kicad_sch --output examples/automation-smoke/verification`.
4. Run the same wrapper with `drc` and the `.kicad_pcb` source.
5. Run `python -m automation.kicad_tools.export_outputs examples/automation-smoke/kicad/AIPE_Smoke.kicad_pro --output <fresh-output-directory>`.

The checked-in successful exports are under `outputs/`. Export deliberately
requires a fresh directory so stale files cannot establish a passing run.
`python -m automation.verification.verify_smoke` checks the latest reports,
source hashes, exact three-net connectivity and the recorded export hashes.

## Observed result

KiCad 10.0.7 on Windows: ERC zero findings; DRC zero findings, unconnected items
and schematic-parity issues. No checks were disabled by the generator. The
reports list KiCad's default ignored checks explicitly; no exclusions were added.
Schematic PDF, four-page layer PDF, Gerber, drill, BOM, positions, STEP and
front/back/isometric images exported successfully. The final schematic and four
PCB PDF pages were rendered and visually inspected. STEP includes component
models, confirmed by the board renders. The exported netlist matches all seven
expected component-pin connections exactly.

Early failed runs remain in `verification/` as diagnostic history. The
`smoke-result.json` identifies the passing evidence. This test establishes only
this small pipeline, not the correctness of future converter circuitry or layout.

For non-Windows installations provide `AIPE_KICAD_DATA` if the data directory is
not beside the executable at `../share/kicad`, and use an interpreter that can
import the installed KiCad PCB bindings. Those hosts are not tested yet.
