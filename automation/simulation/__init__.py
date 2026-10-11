"""Behavioural circuit simulation for the V2 SiC buck (ngspice shared library + numpy cross-check).

Deterministic without native tools: parameter handling, deck generation, the exact
switched-state numpy model, metric extraction and the CSV/SVG/JSON writers. Requires
the KiCad-bundled ngspice shared library: every SPICE transient run in
``automation.simulation.ngspice_runner`` and ``automation.simulation.buck_stage.simulate``.
"""
