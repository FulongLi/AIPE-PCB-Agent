# Automation architecture

The repository is the engineering record. Each design input, generated CAD
source and verification output must remain traceable to a commit.

```text
Requirements + documented assumptions
    -> engineering calculations and component evidence
    -> deterministic design description
    -> KiCad schematic and PCB source
    -> real KiCad checks and exports
    -> engineering review and frozen V1 package
```

Python is the cross-platform orchestration language. Prefer `kicad-cli` for
checking and exporting; investigate official IPC/Python interfaces for editing.
Where an operation is unavailable, use the documented KiCad file formats and
validate the generated files with KiCad. No third-party MCP server is required.

The initial setup code uses only the Python standard library. Avoid relying on
shell activation, Unix-only locations, or modifying global Python packages.
Discover tool paths using explicit configuration, environment overrides, PATH,
and conventional platform locations. Record which path was actually used.

The CLI check wrapper must preserve nonzero exit codes, capture logs and reject
missing output reports. A unit test using a simulated process result is only a
test of this wrapper; it is not an ERC/DRC result or a CAD integration test.

The complete operation layer will grow with verified needs: project creation,
schematic connectivity and footprint assignment, board stack-up, placement,
tracks/vias/zones, checks, exports and review images. These are planned
capabilities, not a claim of current implementation.
