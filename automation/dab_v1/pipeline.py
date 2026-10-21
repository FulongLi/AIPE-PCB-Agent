"""End-to-end driver of the DAB-V1 boards: schematic -> floorplan -> routing -> verification and exports.

    python -m automation.dab_v1.pipeline --board primary-power --stages schematic,floorplan,route,verify

Host Python runs the schematic generation (project_schematic), ERC, exports and host-side checks; the pcbnew stages
(floorplan, routing, netlist equality, copper islands) are re-executed under KiCad's bundled Python, which the
repository's detect_kicad finds next to kicad-cli.  Every stage writes its own evidence; this module only sequences
them and records the wall time in verification/pipeline_<board>.json.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

from automation.dab_v1 import requirements as rq
from automation.setup.detect_kicad import find_kicad_cli

STAGES = ('schematic', 'floorplan', 'copper', 'route', 'verify')


def kicad_python():
    cli = find_kicad_cli()
    candidate = cli.parent / ('python.exe' if os.name == 'nt' else 'python3')
    if not candidate.is_file():
        raise FileNotFoundError('KiCad Python not found next to kicad-cli')
    return candidate


def run_stage(board: str, stage: str, verify_stages: str, time_budget: float = 0.0) -> dict:
    start = time.monotonic()
    if stage == 'schematic':
        from automation.dab_v1 import schematics
        result = schematics.generate(rq.load(), board, erc=True)
        ok = result['erc']['exit_code'] == 0
    elif stage == 'copper':
        from automation.dab_v1 import copper
        record = copper.prepare(board)
        result = dict(zones={net: list(layers) for net, layers in record['plan']['zones'].items()})
        ok = True
    elif stage in ('floorplan', 'route'):
        module = 'automation.dab_v1.floorplan' if stage == 'floorplan' else 'automation.dab_v1.routing'
        command = [str(kicad_python()), '-m', module, '--board', board]
        if stage == 'route' and time_budget > 0:
            command += ['--time-budget', str(time_budget)]  # the router time-boxes itself and still pours, fills and saves
        completed = subprocess.run(command, cwd=str(rq.ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace',
                                   timeout=(time_budget + 2400) if (stage == 'route' and time_budget > 0) else 7200)
        result = dict(exit_code=completed.returncode, tail=(completed.stdout + completed.stderr)[-1500:])
        ok = completed.returncode == 0
    elif stage == 'verify':
        from automation.dab_v1 import verify
        summary = verify.run(rq.load(), board, verify_stages.split(','))
        result = {k: summary.get(k) for k in ('erc', 'drc', 'export', 'netlist', 'routing', 'copper_islands')}
        ok = bool(summary.get('drc', {}).get('exit_code') == 0 and summary.get('export', {}).get('status') == 'passed')
    else:
        raise ValueError(stage)
    return dict(stage=stage, ok=ok, seconds=round(time.monotonic() - start, 1), result=result)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--board', choices=rq.BOARDS, required=True)
    parser.add_argument('--stages', default=','.join(STAGES))
    parser.add_argument('--verify-stages', default='erc,drc,export,netlist,quality,layout,islands')
    parser.add_argument('--time-budget', type=float, default=0.0, help='router time box in seconds (0 = unlimited); unrouted nets are reported, the board is still saved')
    args = parser.parse_args(argv)
    log = dict(board=args.board, started_utc=datetime.now(timezone.utc).isoformat(), stages=[], time_budget_s=args.time_budget)
    worst = 0
    for stage in args.stages.split(','):
        entry = run_stage(args.board, stage, args.verify_stages, args.time_budget)
        log['stages'].append(entry)
        print(json.dumps({k: v for k, v in entry.items() if k != 'result'}), flush=True)
        if not entry['ok']:
            worst = 1
            if stage != 'verify':
                print(json.dumps(entry['result'], indent=2, default=str)[-2000:], flush=True)
                break
    log['finished_utc'] = datetime.now(timezone.utc).isoformat()
    rq.VERIFICATION.mkdir(parents=True, exist_ok=True)
    (rq.VERIFICATION / f'pipeline_{args.board}.json').write_text(json.dumps(log, indent=2, default=str) + '\n', encoding='utf-8')
    return worst


if __name__ == '__main__':
    raise SystemExit(main())
