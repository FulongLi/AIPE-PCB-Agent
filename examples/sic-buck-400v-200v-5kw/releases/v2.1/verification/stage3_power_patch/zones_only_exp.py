"""Stage-3 diagnostic: build the power board with the generator's placement, pours, via groups and chain tracks but WITHOUT the
signal router (fanout / route_net turned into no-ops), save into a scratch copy of the project and run kicad-cli DRC there.
Writes nothing into the repository (write_outputs and the netlist export are redirected). KiCad Python only.

usage: KiCad python zones_only_exp.py SCRATCH_PROJECT_DIR
"""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(r'D:/Cursor Workspace/AIPE-PCB-Agent')
sys.path.insert(0, str(ROOT))
SCR = Path(sys.argv[1])
SCR.mkdir(parents=True, exist_ok=True)
import importlib.util  # noqa: E402
if len(sys.argv) > 2:
    import os
    os.environ['AIPE_ROOT'] = str(ROOT)
    _spec = importlib.util.spec_from_file_location('gen_s3', sys.argv[2])
    gen = importlib.util.module_from_spec(_spec)
    sys.modules['gen_s3'] = gen
    _spec.loader.exec_module(gen)
    from automation.kicad_tools import generate_sic_power_board as _repo  # the fork lives in scratch: take the repository paths
    for _name in ('ROOT', 'EXAMPLE', 'KICAD_DIR', 'DESIGN_DIR', 'VERIFICATION_DIR', 'MODEL_JSON', 'MAPPING_JSON', 'SPEC_JSON', 'CHECKS_DIR', 'DRC_DIR'):
        setattr(gen, _name, getattr(_repo, _name))
else:
    from automation.kicad_tools import generate_sic_power_board as gen  # noqa: E402
from automation.kicad_tools import grid_router as gr  # noqa: E402
from automation.kicad_tools.run_check import run_check  # noqa: E402

# project copy (rules, net classes, schematics for parity) next to the scratch board; the footprint libraries stay in the
# repository (Windows MAX_PATH) and the scratch fp-lib-table points at them with absolute URIs
for p in gen.KICAD_DIR.iterdir():
    if p.suffix in ('.kicad_pcb', '.kicad_prl') or p.is_dir():
        continue
    if p.name == 'fp-lib-table':
        text = p.read_text(encoding='utf-8').replace('${KIPRJMOD}', gen.KICAD_DIR.resolve().as_posix())
        (SCR / p.name).write_text(text, encoding='utf-8')
        continue
    shutil.copy2(p, SCR / p.name)

gen.write_outputs = lambda result: (SCR / 'result.json').write_text(json.dumps(result, indent=1, default=str), encoding='utf-8')
_export = gen.export_netlist
gen.export_netlist = lambda schematic, target, cli=None: _export(schematic, SCR / 'netlist_power.xml', cli)
gr.Router.fanout = lambda self, **kw: []
gr.Router.route_net = lambda self, net, ports=None, layers=None, allow_front_fallback=True: []
if '--route' in sys.argv:  # full router run (slow) instead of the zones-only diagnostic: keep the generator's trial count
    import automation.kicad_tools.grid_router as _gr2
    importlib.reload(_gr2)
    gen.gr = _gr2
else:
    gen.SIGNAL_ORDER_TRIALS = 1
out = SCR / f'{gen.NAME}.kicad_pcb'
t0 = time.monotonic()
result = gen.build_power(out, route=True, drc=False, metrics=False)
print(f"built {out} in {time.monotonic() - t0:.0f} s: counts {result.get('board_counts')} pre_routed tracks {result['pre_routed']['tracks']} "
      f"vias {result['pre_routed']['vias']}", flush=True)
t0 = time.monotonic()
code, manifest = run_check('drc', out, SCR / 'drc', gen.find_kicad_cli())
m = gen.read_manifest(manifest)
print(f"DRC exit {code} in {time.monotonic() - t0:.0f} s: violations {m.get('violations')} unconnected {m.get('unconnected_items')} "
      f"parity {m.get('schematic_parity')} manifest {manifest}", flush=True)
