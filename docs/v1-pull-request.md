# AI-generated 48V to 24V 1kW Synchronous Buck - V1

This adds the first complete integrated power/DSP CAD benchmark: a 48 V nominal
to 24 V / 1 kW synchronous buck using TMS320F28335, documented 36-54 V bench-input
assumptions, real component selection, fourteen schematic sheets and a fully
routed six-layer 300 x 220 mm board. Deterministic Python/KiCad automation,
manufacturer references, calculations, review PDFs/renders and manufacturing
formats are included with a frozen V1 checksum manifest.

Validation: KiCad 10.0.7 ERC/DRC with all severities and schematic parity return
zero findings and no unrouted connections. The exported netlist matches 645
assigned pins on 85 named nets; all 240 physical items have matched footprints
and net assignments. All eleven exports and their hashes pass verification.
Six wrapper tests and the real smoke example pass. Layer-image review also
found and fixed a ground-plane geometry problem that DRC alone did not catch.

**AI-GENERATED ENGINEERING PROTOTYPE - V1 - HUMAN REVIEW REQUIRED.** The package
does not establish fabrication/energization readiness. Review priorities are
gate/commutation geometry, hard-short trip delay, input-capacitor ripple/inrush,
thermal and mechanical assembly, rail sequencing, and the as-yet unvalidated
firmware/control loop. See `review/design_report.md` and
`verification/known_issues.md` in the example. No V2 or physical power-up is
part of this PR.

Target: `codex/v1-buck-1kw` -> `main` in `FulongLi/AIPE-PCB-Agent`.
This file is the prepared PR body; it is not evidence that a remote PR exists.
