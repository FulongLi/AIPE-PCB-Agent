# Reproducing and checking V1

Use Python 3.10+ for standard-library automation and KiCad 10.0.7 with its
`pcbnew` Python environment and NumPy for board generation/routing. No external
autorouter, MCP service, mouse automation or cloud CAD service is required.
The Windows installation and exact detected paths are documented in
environment.md. On macOS, configure paths to the corresponding installed
KiCad CLI/Python environment; generation has not been executed there.

Machine paths are read from `.aipe/local-tools.json`, explicit environment
configuration or the discovery search. A future install still requires user
approval of software and location. Do not include personal tool paths in Git.

## Inspect without changing the frozen release

Open `examples/buck-48v-24v-1kw/kicad/AIPE_Buck_1kW.kicad_pro` in KiCad.
Symbols, footprint tables, custom footprints and envelope models are project
relative. Standard 3D models use the installed KiCad 10 model directory.
Frozen STEP and review renders do not require those model files to view.

From the repository root:

```text
python -m unittest discover -s tests -v
python -m automation.verification.verify_smoke
python -m automation.verification.verify_buck
```

The converter verifier requires source/dependency hashes, native zero-finding
reports, XML netlist equivalence, six copper Gerbers, export file hashes and a
STEP log without missing-model messages. It does not qualify electrical or
thermal performance. Paths recorded in historical command logs describe the
original host; the verifier resolves source and output paths relative to the
repository.

## Regenerate development sources

These operations replace generated development files. Preserve manual edits
first and do not target `releases/v1`. Run board scripts with the KiCad Python
executable rather than a Python interpreter that cannot import pcbnew.

```text
python -m automation.scripts.calculate_buck
python -m automation.kicad_tools.generate_buck_schematic
python -m automation.scripts.component_records
<kicad-python> automation/kicad_tools/generate_buck_board.py
<kicad-python> automation/kicad_tools/route_buck.py
python -m automation.kicad_tools.run_check erc examples/buck-48v-24v-1kw/kicad/AIPE_Buck_1kW.kicad_sch --output examples/buck-48v-24v-1kw/verification
python -m automation.kicad_tools.run_check drc examples/buck-48v-24v-1kw/kicad/AIPE_Buck_1kW.kicad_pcb --output examples/buck-48v-24v-1kw/verification
<kicad-python> automation/verification/check_power_layout.py
```

Use `export_outputs` with a **fresh output directory**, then assemble the review
package after placing the verified export under manufacturing. Required layer
list: `F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.SilkS,B.SilkS,F.Fab,Edge.Cuts`.
Pass `--pdf-scale 0.9` for this A3 board drawing so it clears the title block.
The exporter adds paste and mask layers and records every command and hash.

The current router uses a 0.25 mm grid, conservative obstacle expansion,
alternating DSP fanout, dedicated gate routing, internal signal routing and
explicit power copper. Geometric proposal generation is followed by official
KiCad zone fill and native checks. UUIDs and route details can vary across
KiCad/library versions, so byte-for-byte reproduction on another version is
not promised. Never reuse an older passing report after editing a child sheet,
footprint, project rule, model or board.

No control-loop firmware is generated. Review the hardware/firmware contract
before writing or running any later converter software.
