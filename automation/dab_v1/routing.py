"""Routing of the DAB-V1 boards: floorplan copper plan + routing YAML -> grid_router.run_plan (KiCad Python).

The declarative plan is assembled from pcb/floorplan_<board>.json (pours, planes, keep-outs, per-net regions,
fine-pitch stubs - all derived from the floorplan requirement file) and requirements/routing_<board>.yaml (router
parameters, widths, stage order).  Power boards run the plan through a PairwiseRouter whose pair clearances come
from the insulation table (rules.make_pair_gap); the control board uses the plain Router.  The router report is
written to pcb/routing_report_<board>.json.  A zero unresolved count is a geometric proposal; native DRC decides.
"""
from __future__ import annotations

import argparse
import fnmatch
import functools
import json
import time
from pathlib import Path

from automation.dab_v1 import requirements as rq, rules
from automation.dab_v1.floorplan import PCB_DIR, save_json
from automation.kicad_tools.grid_router import Router, run_plan, validate_plan
from automation.kicad_tools.pairwise_router import PairwiseRouter


def first_match(net: str, table: dict, default=None):
    for pattern, value in table.items():
        if fnmatch.fnmatchcase(net, pattern):
            return value
    return default


def build_plan(req, board: str, plan_record: dict, nets: list, save_path: Path | None) -> dict:
    """run_plan dictionary for one board (pure function of the requirement files and the floorplan record)."""
    cfg = req.board(board)
    rp = req.routing[board]
    copper = plan_record['plan']
    power_nets = [n for n in rp.get('power_nets', []) if n in nets]
    domains = rules.power_domains(json.loads((rq.DESIGN / f'circuit_{board}.json').read_text(encoding='utf-8'))) if cfg['side'] != 'control' else {}
    pair = rules.make_pair_gap(req, board, domains)
    net_rules = {}
    for net in nets:
        rule = {}
        width = first_match(net, rp.get('widths_mm', {}))
        if width is not None:
            rule['width'] = float(width)
        fan = first_match(net, rp.get('fanout_widths_mm', {}))
        if fan is not None:
            rule['fanout_width'] = float(fan)
        if net in copper['regions']:
            rule['region'] = copper['regions'][net]
        if rule:
            net_rules[net] = rule
    critical = [n for pat in rp.get('critical_patterns', []) for n in nets if fnmatch.fnmatchcase(n, pat) and n not in power_nets]
    critical = list(dict.fromkeys(critical))
    signal_first = [n for pat in rp.get('signal_first', []) for n in nets if fnmatch.fnmatchcase(n, pat)]
    power = {}
    for net, layers in copper['zones'].items():
        if net not in nets:
            continue
        power[net] = dict(stubs=False, zones={layer: polys for layer, polys in layers.items()}, priority=2, clearance=cfg['min_clearance_mm'],
                          min_thickness=0.25)
    direct = [n for n in nets if n not in power_nets and n != copper['ground']['net']]
    if cfg['side'] != 'control' and not copper.get('zones_merged'):
        raise ValueError(f'{board}: run automation.dab_v1.copper (host Python, Shapely) before routing so that overlapping pours are merged')
    plan = dict(board=dict(width=float(cfg['size_mm'][0]), height=float(cfg['size_mm'][1]), margin=1.0),
                layers=list(rp['layers']), grid=float(rp['grid_mm']), trace=float(rp['trace_mm']), clearance=float(rp['clearance_mm']),
                via=[float(v) for v in rp['via_mm']], hole_clearance=float(cfg['min_hole_clearance_mm']),
                net_rules=net_rules, keepouts=copper['keepouts'], critical=critical, critical_layers=list(rp.get('critical_layers', [])),
                power=power, fanout=dict(direct_nets=direct, exact_stub_pads=copper['exact_stub_pads'], direct_lane_mm=float(rp.get('direct_lane_mm', 0.0)),
                                         skip_pads=copper.get('skip_pads', [])),
                pre_routed=copper.get('pre_routed', dict(tracks=[], vias=[])),
                signal_first=signal_first, signal_order=signal_first, exclude_nets=[], front_fallback=True,
                ground=dict(copper['ground']), prune_vias=bool(rp.get('prune_vias', True)), fill=bool(rp.get('fill', True)),
                max_nodes=int(rp['max_nodes']), signal_order_trials=int(rp.get('signal_order_trials', 1)), ripup_rounds=int(rp.get('ripup_rounds', 0)),
                style=dict(rp.get('style', {})), strict=False)
    if save_path is not None:
        plan['save'] = str(save_path)
    return validate_plan(plan)


def route(req, board: str) -> dict:
    import pcbnew as pcb
    cfg = req.board(board)
    directory = rq.EXAMPLE / board
    board_path = (directory / f'{cfg["name"]}.kicad_pcb').resolve()
    record = json.loads((PCB_DIR / f'floorplan_{board}.json').read_text(encoding='utf-8'))
    pcb_board = pcb.LoadBoard(str(board_path))
    # start from the placed board: drop copper of an earlier routing run
    for item in list(pcb_board.GetTracks()):
        pcb_board.Remove(item)
    for zone in list(pcb_board.Zones()):
        pcb_board.Remove(zone)
    nets = sorted(n.GetNetname() for n in pcb_board.GetNetInfo().NetsByNetcode().values() if n.GetNetCode())
    plan = build_plan(req, board, record, nets, board_path)
    save_json(PCB_DIR / f'routing_plan_{board}.json', plan)
    factory = None
    if cfg['side'] != 'control':
        domains = rules.power_domains(json.loads((rq.DESIGN / f'circuit_{board}.json').read_text(encoding='utf-8')))
        factory = functools.partial(PairwiseRouter, pair_clearance=rules.make_pair_gap(req, board, domains))
    start = time.monotonic()
    report = run_plan(pcb_board, plan, router_factory=factory)
    report['wall_seconds'] = round(time.monotonic() - start, 1)
    report['board'] = board
    save_json(PCB_DIR / f'routing_report_{board}.json', report)
    print(f'{board}: tracks {report["tracks"]} vias {report["vias"]} zones {report["zones"]} unresolved {len(report["unresolved"])} in {report["wall_seconds"]} s', flush=True)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--board', choices=rq.BOARDS, required=True)
    args = parser.parse_args(argv)
    report = route(rq.load(), args.board)
    return 1 if report['unresolved'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
