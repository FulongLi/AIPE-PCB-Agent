"""Verification and export pipeline of the DAB-V1 boards (host Python; re-executes pcbnew steps under KiCad's Python).

Stages per board (all through the repository's generic tools):
  drc        kicad-cli pcb drc with --schematic-parity --severity-all --refill-zones (run_check), manifest under verification/drc
  export     Gerbers, drill, BOM, pick-and-place, STEP, PDFs, renders, XML netlist with hashed manifest (export_outputs.export)
  netlist    model / schematic netlist / board pad-net equality (netlist_check_sic.load_xml / load_board / compare)
  quality    routing geometry metrics (check_routing_quality) linked to the DRC manifest
  layout     layout-metric spec derived from the requirement files + check_sic_layout run
  islands    filled-copper island analysis of the power nets (copper_connectivity export + analyse)
  summary    verification/summary_<board>.json with every manifest hash and the honest status of each gate
A clean result is a CAD statement about the generated files under the recorded rule set; it is not electrical,
thermal, EMI or insulation qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from automation.dab_v1 import requirements as rq, rules
from automation.kicad_tools.run_check import run_check
from automation.setup.detect_kicad import find_kicad_cli

ROOT = rq.ROOT


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def kicad_python() -> Path:
    cli = find_kicad_cli()
    candidate = cli.parent / ('python.exe' if os.name == 'nt' else 'python3')
    if not candidate.is_file():
        raise FileNotFoundError('KiCad Python not found next to kicad-cli')
    return candidate


def paths(req, board: str) -> dict:
    cfg = req.board(board)
    directory = rq.EXAMPLE / board
    return dict(dir=directory, name=cfg['name'], pcb=directory / f'{cfg["name"]}.kicad_pcb', sch=directory / f'{cfg["name"]}.kicad_sch',
                manufacturing=rq.MANUFACTURING / board, verification=rq.VERIFICATION)


def stage_erc(req, board: str) -> dict:
    p = paths(req, board)
    code, manifest = run_check('erc', p['sch'], p['verification'] / 'erc', cli=find_kicad_cli())
    data = read(manifest)
    return dict(exit_code=code, manifest=str(Path(manifest).relative_to(ROOT)), finding_count=data.get('finding_count'), status=data.get('status'),
                report_sha256=data.get('report_sha256'))


def stage_drc(req, board: str) -> dict:
    p = paths(req, board)
    code, manifest = run_check('drc', p['pcb'], p['verification'] / 'drc', cli=find_kicad_cli())
    data = read(manifest)
    report = read(data['report']) if data.get('report') and Path(data['report']).exists() else {}
    by_type = {}
    for key in ('violations', 'unconnected_items', 'schematic_parity'):
        for v in report.get(key, []):
            k = f"{key}:{v['type']}:{v['severity']}"
            by_type[k] = by_type.get(k, 0) + 1
    unconnected_nets: dict = {}
    for v in report.get('unconnected_items', []):
        for item in v.get('items', []):
            text = item.get('description', '')
            if '[' in text and ']' in text:
                net = text[text.index('[') + 1:text.index(']')]
                unconnected_nets[net] = unconnected_nets.get(net, 0) + 1
    return dict(exit_code=code, manifest=str(Path(manifest).relative_to(ROOT)), finding_counts=data.get('finding_counts'), status=data.get('status'),
                by_type=dict(sorted(by_type.items())), ignored_checks=report.get('ignored_checks', []), report_sha256=data.get('report_sha256'),
                report=str(Path(data['report']).relative_to(ROOT)) if data.get('report') else None,
                unconnected_nets=dict(sorted(unconnected_nets.items(), key=lambda kv: (-kv[1], kv[0]))),
                note='KiCad lists at most about 500 unconnected items per report; counts are of listed items (pad ends), not of nets')


def stage_export(req, board: str, *, fresh: bool = True) -> dict:
    from automation.kicad_tools.export_outputs import export
    p = paths(req, board)
    out = p['manufacturing']
    if out.exists() and fresh:
        shutil.rmtree(out)
    layers = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.SilkS,B.SilkS,F.Fab,B.Fab,Edge.Cuts'
    try:
        export(Path(str(p['pcb'])[:-len('.kicad_pcb')]), out, layers, '0', step_copper=False)
        status = 'passed'
    except Exception as exc:  # the manifest records the failing command
        status = f'failed: {exc}'
    manifest = out / 'export-manifest.json'
    data = read(manifest) if manifest.exists() else {}
    return dict(status=status, manifest=str(manifest.relative_to(ROOT)) if manifest.exists() else None,
                commands=[(c['name'], c['exit_code']) for c in data.get('commands', [])], artifacts=len(data.get('artifacts', {})),
                manifest_sha256=sha(manifest) if manifest.exists() else None)


def stage_netlist(req, board: str) -> dict:
    """Pad/net equality of model, exported schematic netlist and board (pcbnew step under KiCad Python)."""
    p = paths(req, board)
    xml = p['manufacturing'] / 'netlist.xml'
    out = p['verification'] / 'circuit_checks' / f'netlist_equality_{board}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    script = f'''
import json, sys
sys.path.insert(0, {str(ROOT)!r})
from automation.verification.netlist_check_sic import load_xml, load_board, compare
parts = json.loads(open({str(rq.DESIGN / f'circuit_{board}.json')!r}, encoding='utf-8').read())
expected = {{(p['ref'], str(k)): v for p in parts for k, v in p['nets'].items() if v}}
refs = {{p['ref'] for p in parts}}
onboard = {{p['ref'] for p in parts if p.get('on_board', True)}}
a, ar, ai, ad = load_xml({str(xml)!r})
b, br, bi, bd = load_board({str(p['pcb'].resolve())!r})
sm = compare(a, expected, 'schematic', 'model', ar, refs)
bm = compare(b, {{k: v for k, v in expected.items() if k[0] in onboard}}, 'board', 'model', br, onboard)
row = dict(board={board!r}, schematic_vs_model=sm, board_vs_model=bm, schematic_info=ai, board_info=bi, duplicate_nodes=ad, conflicting_pads=bd)
row['passed'] = sm['exact'] and bm['exact'] and not ad and not bd
open({str(out)!r}, 'w', encoding='utf-8').write(json.dumps(row, indent=2) + chr(10))
print('netlist', row['passed'], sm['mismatches'], bm['mismatches'])
'''
    completed = subprocess.run([str(kicad_python()), '-c', script], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT), timeout=600)
    if completed.returncode:
        return dict(passed=False, error=(completed.stdout + completed.stderr)[-1500:])
    row = read(out)
    return dict(passed=row['passed'], schematic_mismatches=row['schematic_vs_model']['mismatches'], board_mismatches=row['board_vs_model']['mismatches'],
                duplicate_nodes=len(row['duplicate_nodes']), conflicting_pads=len(row['conflicting_pads']), file=str(out.relative_to(ROOT)), sha256=sha(out))


def stage_quality(req, board: str, drc_manifest: str | None) -> dict:
    p = paths(req, board)
    out = p['verification'] / 'engineering_checks'
    args = [sys.executable, str(ROOT / 'automation/verification/check_routing_quality.py'), str(p['pcb']), '--output', str(out), '--label', board,
            '--plan', str(rq.EXAMPLE / 'pcb' / f'routing_plan_{board}.json'), '--report', str(rq.EXAMPLE / 'pcb' / f'routing_report_{board}.json')]
    if drc_manifest:
        args += ['--drc', str(ROOT / drc_manifest)]
    completed = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT), timeout=900)
    result = dict(exit_code=completed.returncode, log=(completed.stdout + completed.stderr)[-800:])
    metrics = out / f'routing_quality_{board}.json'
    if metrics.exists():
        data = read(metrics)
        result.update(file=str(metrics.relative_to(ROOT)), sha256=sha(metrics),
                      summary={k: data.get(k) for k in ('tracks', 'vias', 'arcs', 'routed_length_mm', 'bends_90', 'bends_45') if k in data})
        if 'board' in data and isinstance(data['board'], dict):
            result['board_totals'] = {k: data['board'].get(k) for k in ('tracks', 'vias', 'arcs', 'length_mm', 'bends_90', 'bends_45', 'bends_other') if k in data['board']}
    return result


def layout_spec(req, board: str) -> dict:
    """check_sic_layout spec derived from the requirement files, the model and the floorplan record."""
    cfg = req.board(board)
    parts = read(rq.DESIGN / f'circuit_{board}.json')
    record = read(rq.EXAMPLE / 'pcb' / f'floorplan_{board}.json')
    built = rules.build_rules(req, board, parts)
    classes = {c['name']: list(c['nets']) for c in built['classes'] if c['name'] != 'Default' and c.get('nets')}
    spec = dict(schema_version=1, board=board, title=f'{cfg["title"]} - layout metrics spec (derived from requirements)',
                notes=['Generated by automation.dab_v1.verify from the requirement files; thresholds are the unverified design targets of specification.yaml.'],
                expected=dict(outline_mm=cfg['size_mm'], copper_layers=cfg['layers'], copper_um=cfg['copper_um'][0], thickness_mm=cfg['thickness_mm']),
                layers=dict(outer=['F.Cu', 'B.Cu']), net_classes=classes, class_groups={}, isolation=dict(pairs=[], barrier_keepouts=[], barrier_parts=[]),
                gate_loops=[], decoupling=[], commutation={}, heatsink={}, sensing={}, control={}, compactness={})
    if cfg['side'] == 'control':
        spec['class_groups'] = dict(CTRL=['CTRL_POWER', 'CTRL_SIGNAL'])
        return spec
    ev = built['evidence']
    hv = [c for c in classes if c != 'CTRL']
    spec['class_groups'] = dict(HV=hv, CTRL_SELV=['CTRL'])
    for c, info in ev['classes'].items():
        spec['class_groups'].setdefault(info['domain'].upper(), []).append(c)
    barrier_refs = [p['ref'] for p in parts if p.get('island') or p.get('barrier')]
    spec['isolation']['pairs'] = [dict(name='HV domains to SELV (all layers)', a=['HV'], b=['CTRL_SELV'], min_mm={'all': req.reinforced_gap_mm()},
                                       exclude_within_courtyards=barrier_refs, rules=['KR-ISO-002'])]
    targets = req.specification['unverified_design_targets']
    hf = [p['ref'] for p in parts if p['footprint'] == 'Capacitor_SMD:C_2220_5750Metric']
    roles = {p['ref']: p['role'] for p in parts if p.get('role')}
    spec['commutation'] = dict(vin_net='BUS_P', pgnd_net='PGND', sw_net='SW_A', hf_capacitor_refs=hf, hf_capacitor_nets=['BUS_P', 'PGND'],
                               pin_to_capacitor_mm_max=[targets['hf_capacitor_to_switch_mm_max'], 2 * targets['hf_capacitor_to_switch_mm_max']],
                               mosfets=[dict(ref=r, role=('HS' if role.endswith('H') else 'LS'), drain_pad='1', source_pad='2', gate_pad='4', kelvin_pad='3') for r, role in roles.items()])
    islands = record['plan']['islands']
    gate_loops = []
    for role, isl in islands.items():
        q = next(r for r, rr in roles.items() if rr == role)
        gate_loops.append(dict(mosfet=q, gate_pad='4', kelvin_pad='3', driver_ref=isl['driver'], driver_output_pads=['4', '6'], driver_return_pads=['3'],
                               gate_nets=[f'G_{role}', f'OUTH_{role}', f'OUTL_{role}'], kelvin_net=f'KS_{role}', power_source_net=dict(AH='SW_A', AL='PGND', BL='PGND', BH='SW_B')[role],
                               driver_to_gate_mm_max=targets['gate_loop_driver_to_gate_mm_max']))
        spec['decoupling'].append(dict(ic=isl['driver'], note=f'{role} driver VDD-KS and KS-VEE reservoirs', supply_nets=[f'VDD_{role}', f'VEE_{role}'], capacitor_prefix='C', max_mm=15))
    spec['gate_loops'] = gate_loops
    hs = [p['ref'] for p in parts if p['footprint'] == 'AIPE:DAB_HEATSINK_ENVELOPE']
    if hs:
        spec['heatsink'] = dict(ref=hs[0], keepout_mm=5.0, groups=['HV'], layers=['F.Cu'])
    spec['control'] = dict(section_groups=['CTRL_SELV'], power_groups=['HV'], section_refs=['J5'], separation_mm_min=req.reinforced_gap_mm(),
                           ground=dict(net='GND_CTRL', layers=['In1.Cu'], min_area_mm2=None, require_copper_at=[], forbid_copper_at=[]),
                           exclude_refs=barrier_refs, exclude_note='Barrier packages straddle the isolation band and belong to both sections.')
    spec['sensing'] = dict(sw_net='SW_A', kelvin_pairs=[dict(name='AMC1311 differential output', nets=['VSNS_P', 'VSNS_N'], match_mm_max=None)],
                           parts=[p['ref'] for p in parts if p.get('barrier')])
    return spec


def stage_layout(req, board: str) -> dict:
    p = paths(req, board)
    out = p['verification'] / 'engineering_checks'
    out.mkdir(parents=True, exist_ok=True)
    spec_path = out / f'layout_spec_{board}.json'
    spec_path.write_text(json.dumps(layout_spec(req, board), indent=2) + '\n', encoding='utf-8')
    args = [sys.executable, str(ROOT / 'automation/verification/check_sic_layout.py'), str(p['pcb']), '--spec', str(spec_path), '--model',
            str(rq.DESIGN / f'circuit_{board}.json'), '--output', str(out), '--label', board]
    completed = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT), timeout=1800)
    result = dict(exit_code=completed.returncode, log=(completed.stdout + completed.stderr)[-1200:], spec=str(spec_path.relative_to(ROOT)))
    metrics = out / f'layout_metrics_{board}.json'
    if metrics.exists():
        data = read(metrics)
        result.update(file=str(metrics.relative_to(ROOT)), sha256=sha(metrics), summary=data.get('summary'), warnings=data.get('warnings'))
    return result


def stage_islands(req, board: str) -> dict:
    """Filled-copper islands of the power nets: export under KiCad Python, analyse with Shapely on the host."""
    p = paths(req, board)
    out = p['verification'] / 'engineering_checks'
    out.mkdir(parents=True, exist_ok=True)
    nets = ['BUS_P', 'PGND', 'SW_A', 'SW_B', 'XF_B', 'AC_B', 'GND_CTRL', '12V_E', '3V3'] if req.board(board)['side'] != 'control' else ['GND_CTRL', '5V0', '3V3', '12V_E']
    raw = ROOT / '.aipe' / 'dab' / f'copper_{board}.json'
    raw.parent.mkdir(parents=True, exist_ok=True)
    script = (f'import sys; sys.path.insert(0, {str(ROOT)!r}); from automation.kicad_tools.copper_connectivity import export; '
              f'export({str(p["pcb"])!r}, {str(raw)!r}, {nets!r})')
    completed = subprocess.run([str(kicad_python()), '-c', script], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT), timeout=900)
    if completed.returncode:
        return dict(passed=None, error=(completed.stdout + completed.stderr)[-800:])
    try:
        from automation.kicad_tools.copper_connectivity import analyse
        target = out / f'copper_islands_{board}.json'
        analyse(raw, target)
    except ImportError as exc:
        return dict(passed=None, error=f'shapely unavailable: {exc}')
    data = read(target)
    counts = {n['net']: n['component_count'] for n in data['nets']}
    return dict(passed=all(v == 1 for v in counts.values()), components=counts, file=str(target.relative_to(ROOT)), sha256=sha(target))


def run(req, board: str, stages: list, fresh_export: bool = True) -> dict:
    p = paths(req, board)
    summary_path = p['verification'] / f'summary_{board}.json'
    summary = read(summary_path) if summary_path.exists() else {}
    summary.update(board=board, project=p['name'], generation=rq.GENERATION, updated_utc=datetime.now(timezone.utc).isoformat(),
                   inputs={str(f.relative_to(ROOT)): sha(f) for f in [p['pcb'], p['sch']] if f.exists()},
                   requirement_sha256={k: sha(v) for k, v in rq.requirement_files().items()})
    if 'erc' in stages:
        summary['erc'] = stage_erc(req, board)
    if 'drc' in stages:
        summary['drc'] = stage_drc(req, board)
    if 'export' in stages:
        summary['export'] = stage_export(req, board, fresh=fresh_export)
    if 'netlist' in stages:
        summary['netlist'] = stage_netlist(req, board)
    if 'quality' in stages:
        summary['routing_quality'] = stage_quality(req, board, summary.get('drc', {}).get('manifest'))
    if 'layout' in stages:
        summary['layout_metrics'] = stage_layout(req, board)
    if 'islands' in stages:
        summary['copper_islands'] = stage_islands(req, board)
    routing_report = rq.EXAMPLE / 'pcb' / f'routing_report_{board}.json'
    if routing_report.exists():
        rep = read(routing_report)
        summary['routing'] = dict(tracks=rep.get('tracks'), vias=rep.get('vias'), zones=rep.get('zones'), unresolved=len(rep.get('unresolved', [])),
                                  seconds=rep.get('wall_seconds'), file=str(routing_report.relative_to(ROOT)), sha256=sha(routing_report))
    summary['scope'] = ('CAD evidence only: native ERC/DRC under the recorded rule set, export hashes, pad/net equality and geometric layout metrics. '
                        'No electrical, thermal, EMI, insulation or manufacturability qualification is established by these checks.')
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, default=str) + '\n', encoding='utf-8')
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--board', choices=rq.BOARDS, required=True)
    parser.add_argument('--stages', default='erc,drc,export,netlist,quality,layout,islands')
    parser.add_argument('--keep-export', action='store_true', help='do not delete an existing manufacturing folder first')
    args = parser.parse_args(argv)
    summary = run(rq.load(), args.board, args.stages.split(','), fresh_export=not args.keep_export)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('requirement_sha256', 'inputs')}, indent=2, default=str)[:6000])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
