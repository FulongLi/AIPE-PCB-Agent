# Drill interpretation

The native `AIPE_Buck_1kW.drl` uses KiCad Excellon attributes and combines both
plating types in one file (`TF.FileFunction,MixedPlating,1,6`). Tools T1-T9 are
explicitly marked plated; T10 is explicitly marked non-plated. The native report
counts 834 plated holes (including two plated slots) and eight 3.2 mm NPTH holes.

Do not strip the plating attributes or assume every drill is plated. If the
chosen fabricator requires physically separate files, export the same checked
PCB with `kicad-cli pcb export drill --excellon-separate-th` and review those
outputs before ordering. This is a fabrication-interface decision, not a change
to the frozen board's hole geometry.
