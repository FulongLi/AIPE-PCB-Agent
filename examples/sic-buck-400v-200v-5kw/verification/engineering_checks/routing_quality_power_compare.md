# Routing quality comparison

Status: measured - human review required

Before: `examples\sic-buck-400v-200v-5kw\releases\v2\kicad\power_board\AIPE_SiC_Buck_Power.kicad_pcb` (sha256 b1bb5698194b)
After: `examples\sic-buck-400v-200v-5kw\kicad\power_board\AIPE_SiC_Buck_Power.kicad_pcb` (sha256 dcd148fbdf65)

| metric | before | after | delta | ratio |
|---|---|---|---|---|
| segments | 4755 | 2991 | -1764 | 0.629 |
| arcs | 0 | 145 | 145 | None |
| vias | 606 | 606 | 0 | 1.0 |
| length_mm | 5744.589 | 5545.646 | -198.943 | 0.9654 |
| arc_length_mm | 0 | 56.422 | 56.422 | None |
| joints | 3727 | 2107 | -1620 | 0.5653 |
| bends_90 | 3609 | 1121 | -2488 | 0.3106 |
| bends_45 | 6 | 583 | 577 | 97.1667 |
| bends_other | 109 | 110 | 1 | 1.0092 |
| direction_changes | 3724 | 1814 | -1910 | 0.4871 |
| stair_runs | 382 | 124 | -258 | 0.3246 |
| zigzag_runs | 12 | 26 | 14 | 2.1667 |
| short_run_segments | 2721 | 835 | -1886 | 0.3069 |
| short_segments | 2914 | 1225 | -1689 | 0.4204 |
| short_segment_runs | 448 | 165 | -283 | 0.3683 |
| arc_joints | 0 | 287 | 287 | None |
| arc_joints_discontinuous | 0 | 0 | 0 | None |
| chains | 1028 | 1029 | 1 | 1.001 |
| degree2_joints | 3972 | 2065 | -1907 | 0.5199 |
| degree2_bends_90 | 3739 | 1251 | -2488 | 0.3346 |
| bends_per_100mm | 64.83 | 32.71 | -32.12 | 0.5046 |
| efficiency | 0.7759 | 0.8061 | 0.0302 | - |

Nets longer after: 0 []
Nets with more vias after: []
Nets whose minimum width changed: []

