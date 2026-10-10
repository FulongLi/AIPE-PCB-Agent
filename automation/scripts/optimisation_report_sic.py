"""Measured before/after record of the V2 layout-review corrections (examples/sic-buck-400v-200v-5kw).

Reads the control board before the corrections (a saved copy of the reviewed board, sha256 recorded) and the current
boards with pcbnew, re-measures the quantities the independent review (verification/layout_review_findings.json) used,
reads the DRC manifests, the layout-metrics files and the routing-progress records, and writes
verification/optimisation_before_after.json and .md. Every figure is measured from the board files or copied from
the named manifests; nothing is taken from the generating scripts' own claims.

Run (pcbnew required; re-executes itself under KiCad's bundled Python):
    python automation/scripts/optimisation_report_sic.py --before <copy of the reviewed control board>
        [--before-drc verification/drc/<run>/run.json] [--power-before-note TEXT]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXAMPLE = ROOT / 'examples/sic-buck-400v-200v-5kw'
VER = EXAMPLE / 'verification'
CHECKS = VER / 'engineering_checks'
CONTROL_PCB = EXAMPLE / 'kicad/control_board/AIPE_SiC_Buck_Control.kicad_pcb'
POWER_PCB = EXAMPLE / 'kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb'
BANNER = 'AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kicad_python():
    from automation.setup.detect_kicad import find_kicad_cli, read_config
    explicit = os.environ.get('AIPE_KICAD_PYTHON') or read_config().get('kicad_python')
    if explicit and Path(os.path.expandvars(explicit)).is_file():
        return Path(os.path.expandvars(explicit))
    cli = find_kicad_cli()
    if cli:
        for name in ('python.exe', 'python3', 'python'):
            if (cli.parent / name).is_file():
                return cli.parent / name
    return None


# --- control-board measurements (pcbnew) ------------------------------------------------------------------------------

ADC_FILTERS = {'38': 'C72', '39': 'C71', '40': 'C70', '41': 'C69', '42': 'C68', '46': 'C73', '47': 'C74', '49': 'C75'}


def measure_control(path: Path) -> dict:
    import pcbnew as pcb
    board = pcb.LoadBoard(str(path))
    mm = pcb.ToMM
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    pads = {}
    for ref, fp in fps.items():
        for pad in fp.Pads():
            if pad.GetNumber():
                pads[(ref, pad.GetNumber())] = dict(xy=(mm(pad.GetPosition().x), mm(pad.GetPosition().y)), net=pad.GetNetname(),
                                                    size=(mm(pad.GetSize().x), mm(pad.GetSize().y)), pad=pad)
    tracks = [t for t in board.GetTracks() if not isinstance(t, pcb.PCB_VIA)]
    vias = [t for t in board.GetTracks() if isinstance(t, pcb.PCB_VIA)]
    outline = board.GetBoardEdgesBoundingBox()
    width_mm, height_mm = mm(outline.GetWidth()), mm(outline.GetHeight())

    def dist(a, b):
        return math.dist(a, b)

    def net_tracks(net):
        return [t for t in tracks if t.GetNetname() == net]

    def net_vias(net):
        return [v for v in vias if v.GetNetname() == net]

    def in_pad_vias(ref, number):
        pad = pads[(ref, number)]['pad']
        return sum(1 for v in vias if v.GetNetname() == pad.GetNetname() and pad.HitTest(v.GetPosition()))

    r = {}
    r['sha256'] = sha(path)
    r['outline_mm'] = [round(width_mm, 2), round(height_mm, 2)]
    r['footprints'] = len(fps)
    r['footprints_B_Cu'] = sorted(ref for ref, fp in fps.items() if fp.IsFlipped())
    r['tracks'] = len(tracks)
    r['vias'] = len(vias)
    r['zones'] = len(list(board.Zones()))
    r['total_track_mm'] = round(sum(mm(t.GetLength()) for t in tracks), 1)
    j8 = fps.get('J8')
    r['J8'] = dict(side='B.Cu' if j8.IsFlipped() else 'F.Cu', xy=[round(mm(j8.GetPosition().x), 2), round(mm(j8.GetPosition().y), 2)],
                   pin1=[round(v, 2) for v in pads[('J8', '1')]['xy']], pin50=[round(v, 2) for v in pads[('J8', '50')]['xy']])
    # ADC filter capacitors: DSP pin -> capacitor pad on the same net
    adc = {}
    for pin, cap in ADC_FILTERS.items():
        p = pads[('U5', pin)]
        same = [q for (ref, n), q in pads.items() if ref == cap and q['net'] == p['net']]
        adc[f'U5.{pin}->{cap}'] = round(min(dist(p['xy'], q['xy']) for q in same), 2) if same else None
    r['adc_filter_pin_to_cap_mm'] = adc
    r['adc_filter_max_mm'] = round(max(v for v in adc.values() if v is not None), 2)
    r['adcref_caps_mm'] = {'U5.55->C47': round(dist(pads[('U5', '55')]['xy'], pads[('C47', '1')]['xy']), 2),
                           'U5.56->C48': round(dist(pads[('U5', '56')]['xy'], pads[('C48', '1')]['xy']), 2)}
    # 5 V buck hot loop
    u2vin = pads[('U2', '3')]['xy']
    r['buck'] = {'U2.3_to_C4.1_mm': round(dist(u2vin, pads[('C4', '1')]['xy']), 2), 'U2.3_to_C5.1_mm': round(dist(u2vin, pads[('C5', '1')]['xy']), 2),
                 'U2.3_to_C3.1_mm': round(dist(u2vin, pads[('C3', '1')]['xy']), 2),
                 '5V_SW_segments': len(net_tracks('5V_SW')), '5V_SW_vias': len(net_vias('5V_SW')),
                 '5V_SW_layers': sorted({board.GetLayerName(t.GetLayer()) for t in net_tracks('5V_SW')}),
                 '5V_SW_track_mm': round(sum(mm(t.GetLength()) for t in net_tracks('5V_SW')), 2),
                 '5V_SW_min_width_mm': round(min((mm(t.GetWidth()) for t in net_tracks('5V_SW')), default=0), 2),
                 'C6_pad2_to_U2.2_mm': round(dist(pads[('C6', '2')]['xy'], pads[('U2', '2')]['xy']), 2),
                 '5V_BST_vias': len(net_vias('5V_BST'))}
    # exposed pads
    r['exposed_pad_vias'] = {'U1.17': in_pad_vias('U1', '17'), 'U3.29': in_pad_vias('U3', '29')}
    # track widths of the supply nets
    widths = {}
    for net in ('12V_IN', '12V_PROT', 'EFUSE_RTN', '5V', '5V_SW', '5V_BST'):
        ts = net_tracks(net)
        widths[net] = dict(segments=len(ts), min_width_mm=round(min((mm(t.GetWidth()) for t in ts), default=0), 2),
                           max_width_mm=round(max((mm(t.GetWidth()) for t in ts), default=0), 2), track_mm=round(sum(mm(t.GetLength()) for t in ts), 1),
                           vias=len(net_vias(net)))
    r['supply_tracks'] = widths
    # connectors at the edges
    r['connectors_xy'] = {ref: [round(mm(fps[ref].GetPosition().x), 2), round(mm(fps[ref].GetPosition().y), 2)] for ref in ('J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8')}
    r['J4_J5_edge_distance_mm'] = {ref: round(min(mm(fps[ref].GetPosition().x), width_mm - mm(fps[ref].GetPosition().x)), 2) for ref in ('J4', 'J5')}
    # DSP bypass (model near_dsp_pin)
    model = json.loads((EXAMPLE / 'design/circuit_control.json').read_text(encoding='utf-8'))
    byp = []
    for part in model:
        if 'near_dsp_pin' in part:
            byp.append(dist(pads[('U5', str(part['near_dsp_pin']))]['xy'], pads[(part['ref'], '1')]['xy']))
    r['dsp_bypass_mm'] = dict(max=round(max(byp), 3), mean=round(sum(byp) / len(byp), 3), count=len(byp))
    # clock
    y1 = fps['Y1']
    r['Y1_to_XCLKIN_mm'] = round(dist((mm(y1.GetPosition().x), mm(y1.GetPosition().y)), pads[('U5', '105')]['xy']), 2)
    r['Y1_pad3_to_XCLKIN_mm'] = round(dist(pads[('Y1', '3')]['xy'], pads[('U5', '105')]['xy']), 2)
    # ISENSE pair
    r['isense_pair_mm'] = {n: round(sum(mm(t.GetLength()) for t in net_tracks(n)), 1) for n in ('ISENSE', 'ISENSE_REF')}
    r['isense_pair_mm']['mismatch'] = round(abs(r['isense_pair_mm']['ISENSE'] - r['isense_pair_mm']['ISENSE_REF']), 1)
    # PWM chains and TZ
    r['pwm_tz_track_mm'] = {n: round(sum(mm(t.GetLength()) for t in net_tracks(n)), 1) for n in ('EPWM1A', 'PWM_H_G', 'PWM_H', 'EPWM1B', 'PWM_L_G', 'PWM_L', 'FAULT_N', 'OC_N')}
    # zone fill slivers (In2) and GND area
    slivers = 0
    gnd_area = 0.0
    gnd_islands = 0
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for layer in z.GetLayerSet().Seq():
            fill = z.GetFilledPolysList(layer)
            for i in range(fill.OutlineCount()):
                area = fill.Outline(i).Area() / 1e12
                if area < 0.01:
                    slivers += 1
            if z.GetNetname() == 'GND_CTRL' and board.GetLayerName(layer) == 'In1.Cu':
                gnd_area += fill.Area() / 1e12
                gnd_islands += fill.OutlineCount()
    r['In_fill_slivers_lt_0.01mm2'] = slivers
    r['GND_CTRL_In1_area_mm2'] = round(gnd_area, 1)
    r['GND_CTRL_In1_outlines'] = gnd_islands
    # minimum copper to board edge (tracks/vias/pads)
    edge_min = min([min(mm(t.GetStart().x), mm(t.GetStart().y), width_mm - mm(t.GetStart().x), height_mm - mm(t.GetStart().y)) - mm(t.GetWidth()) / 2 for t in tracks] +
                   [min(mm(v.GetPosition().x), mm(v.GetPosition().y), width_mm - mm(v.GetPosition().x), height_mm - mm(v.GetPosition().y)) - mm(v.GetWidth(pcb.F_Cu)) / 2 for v in vias])
    r['min_track_via_to_edge_mm'] = round(edge_min, 2)
    return r


def measure_power(path: Path) -> dict:
    import pcbnew as pcb
    board = pcb.LoadBoard(str(path))
    mm = pcb.ToMM
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    tracks = [t for t in board.GetTracks() if not isinstance(t, pcb.PCB_VIA)]
    vias = [t for t in board.GetTracks() if isinstance(t, pcb.PCB_VIA)]
    outline = board.GetBoardEdgesBoundingBox()
    r = dict(sha256=sha(path), outline_mm=[round(mm(outline.GetWidth()), 2), round(mm(outline.GetHeight()), 2)], footprints=len(fps),
             footprints_B_Cu=sum(1 for fp in fps.values() if fp.IsFlipped()), tracks=len(tracks), vias=len(vias), zones=len(list(board.Zones())),
             rule_areas=sum(1 for z in board.Zones() if z.GetIsRuleArea()), hv_vias_1p2mm=sum(1 for v in vias if abs(mm(v.GetWidth(pcb.F_Cu)) - 1.2) < 0.01),
             total_track_mm=round(sum(mm(t.GetLength()) for t in tracks), 1))
    pos = {ref: (round(mm(fp.GetPosition().x), 2), round(mm(fp.GetPosition().y), 2)) for ref, fp in fps.items()}
    r['positions'] = {k: pos[k] for k in ('HS1', 'Q1', 'Q2', 'L1', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U10', 'J7', 'C11', 'C12', 'C13', 'C14') if k in pos}
    r['barrier_line_y_mm'] = sorted({pos[k][1] for k in ('U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U10') if k in pos})
    return r


# --- report ------------------------------------------------------------------------------------------------------------


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def drc_summary(manifest_path):
    if not manifest_path or not Path(manifest_path).is_file():
        return None
    m = read_json(manifest_path)
    out = dict(manifest=str(Path(manifest_path).relative_to(EXAMPLE)).replace('\\', '/'), status=m.get('status'), finding_count=m.get('finding_count'),
               tool_exit_code=m.get('tool_exit_code'), wrapper_exit_code=m.get('wrapper_exit_code'), source_sha256=m.get('source_sha256'),
               report_sha256=m.get('report_sha256'), command_flags=[f for f in m.get('command', []) if f.startswith('--')])
    report = Path(m.get('report', ''))
    if report.is_file():
        d = read_json(report)
        out['violations'] = len(d.get('violations', []))
        out['unconnected_items'] = len(d.get('unconnected_items', []))
        out['schematic_parity'] = len(d.get('schematic_parity', []))
        out['violation_types'] = sorted({v['type'] for v in d.get('violations', [])})
    return out


def latest_drc_for(name: str):
    best = None
    for run in sorted((VER / 'drc').glob('*-drc-*/run.json')):
        data = read_json(run)
        if Path(data['source']).stem == name:
            best = run
    return best


def md_table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '---|' * len(headers)]
    out += ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--before', type=Path, required=True, help='copy of the control board as reviewed (sha256 119d37df...)')
    parser.add_argument('--before-drc', type=Path, default=VER / 'drc/20261010T104013Z-drc-7a5fd84b/run.json')
    parser.add_argument('--no-reexec', action='store_true')
    args = parser.parse_args(argv)
    try:
        import pcbnew  # noqa: F401
    except ImportError:
        if args.no_reexec:
            return 2
        py = kicad_python()
        passthrough = list(sys.argv[1:] if argv is None else argv)
        return subprocess.run([str(py), str(Path(__file__).resolve()), *passthrough, '--no-reexec'], cwd=str(ROOT)).returncode
    before = measure_control(args.before)
    after = measure_control(CONTROL_PCB)
    findings = read_json(VER / 'layout_review_findings.json')
    before_drc = drc_summary(args.before_drc)
    after_drc_path = latest_drc_for('AIPE_SiC_Buck_Control')
    after_drc = drc_summary(after_drc_path)
    power = None
    power_drc = None
    if POWER_PCB.is_file():
        power = measure_power(POWER_PCB)
        pd = latest_drc_for('AIPE_SiC_Buck_Power')
        power_drc = drc_summary(pd)
    progress_c = read_json(VER / 'routing_progress_control.json') if (VER / 'routing_progress_control.json').is_file() else {}
    progress_p = read_json(VER / 'routing_progress_power.json') if (VER / 'routing_progress_power.json').is_file() else {}
    metrics_before = read_json(CHECKS / 'layout_metrics_control_before.json') if (CHECKS / 'layout_metrics_control_before.json').is_file() else {}
    metrics_after = read_json(CHECKS / 'layout_metrics_control.json') if (CHECKS / 'layout_metrics_control.json').is_file() else {}
    metrics_power = read_json(CHECKS / 'layout_metrics_power.json') if (CHECKS / 'layout_metrics_power.json').is_file() else {}

    def rows_of(m):
        return {(r['rule'], r['metric'][:70]): (r.get('measured'), r.get('disposition')) for r in m.get('rule_table', [])}

    disposition = {}
    if findings:
        disposition = {f['id']: f for f in findings['findings']}
    doc = dict(schema_version=1, status=BANNER, title='Layout-review corrections: measured before / after',
               generated_utc=datetime.now(timezone.utc).isoformat(), review_findings_file='verification/layout_review_findings.json',
               control=dict(before=dict(board_copy=str(args.before), **before), after=after, drc_before=before_drc, drc_after=after_drc,
                            routing_progress=dict(unresolved_count=progress_c.get('unresolved_count'), stage=progress_c.get('stage'),
                                                  unresolved_nets=sorted({u.get('net') for u in progress_c.get('unresolved', []) if u.get('net')}),
                                                  signal_order_trials=progress_c.get('signal_order_trials'), signal_order_selected=progress_c.get('signal_order_selected')),
                            checker_rows_before={f'{k[0]} | {k[1]}': v for k, v in rows_of(metrics_before).items()},
                            checker_rows_after={f'{k[0]} | {k[1]}': v for k, v in rows_of(metrics_after).items()}),
               power=dict(before='no board (review LR-01)', after=power, drc_after=power_drc,
                          routing_progress=dict(unresolved_count=progress_p.get('unresolved_count'), stage=progress_p.get('stage'),
                                                unresolved_nets=sorted({u.get('net') for u in progress_p.get('unresolved', []) if u.get('net')})),
                          checker_summary=metrics_power.get('summary'), checker_rows={f"{r['rule']} | {r['metric'][:70]}": (r.get('measured'), r.get('disposition')) for r in metrics_power.get('rule_table', [])}),
               findings=disposition)
    status_file = VER / 'optimisation_finding_status.json'
    doc['finding_status'] = read_json(status_file) if status_file.is_file() else {}
    (VER / 'optimisation_before_after.json').write_text(json.dumps(doc, indent=2, default=str) + '\n', encoding='utf-8')
    (VER / 'optimisation_before_after.md').write_text(markdown(doc), encoding='utf-8')
    print('written', VER / 'optimisation_before_after.json', 'and .md')
    return 0


def markdown(doc: dict) -> str:
    c = doc['control']
    b, a = c['before'], c['after']
    db, da = c['drc_before'] or {}, c['drc_after'] or {}
    lines = [f"**{BANNER}**", '', '# Layout-review corrections - measured before / after', '',
             f"Generated {doc['generated_utc']} by `automation/scripts/optimisation_report_sic.py` from the board files (pcbnew 10), the kicad-cli DRC "
             'manifests and the layout-metrics checker. "Before" is the reviewed control board (`verification/layout_review_findings.json`, sha256 '
             f"`{b['sha256'][:16]}...`); \"after\" is the current board. Only the DRC manifests are verification; every other figure is CAD geometry.", '']
    lines += ['## Control board', '']
    st = lambda net, key: a['supply_tracks'][net][key]  # noqa: E731
    sb = lambda net, key: b['supply_tracks'][net][key]  # noqa: E731
    rows = [
        ['Board sha256', b['sha256'][:16] + '...', a['sha256'][:16] + '...'],
        ['Outline (mm)', b['outline_mm'], a['outline_mm']],
        ['Footprints / on B.Cu', f"{b['footprints']} / {len(b['footprints_B_Cu'])}", f"{a['footprints']} / {len(a['footprints_B_Cu'])}"],
        ['Tracks / vias / zones', f"{b['tracks']} / {b['vias']} / {b['zones']}", f"{a['tracks']} / {a['vias']} / {a['zones']}"],
        ['Total track length (mm)', b['total_track_mm'], a['total_track_mm']],
        ['DRC violations / unconnected / parity', f"{db.get('violations')} / {db.get('unconnected_items')} / {db.get('schematic_parity')}",
         f"{da.get('violations')} / {da.get('unconnected_items')} / {da.get('schematic_parity')}"],
        ['DRC manifest', db.get('manifest'), da.get('manifest')],
        ['Router unresolved connections', '39 (recorded)', c['routing_progress'].get('unresolved_count')],
        ['J8 mezzanine header side (LR-03)', b['J8']['side'], a['J8']['side']],
        ['J8 pin 1 / pin 50 (mm)', f"{b['J8']['pin1']} / {b['J8']['pin50']}", f"{a['J8']['pin1']} / {a['J8']['pin50']}"],
        ['ADC 1 nF filter: DSP pin to capacitor pad, max (mm) (LR-04)', b['adc_filter_max_mm'], a['adc_filter_max_mm']],
        ['ADCREFM/P capacitors to pins (mm)', b['adcref_caps_mm'], a['adcref_caps_mm']],
        ['U2 VIN pad to C4.1 / C5.1 (mm) (LR-05)', f"{b['buck']['U2.3_to_C4.1_mm']} / {b['buck']['U2.3_to_C5.1_mm']}", f"{a['buck']['U2.3_to_C4.1_mm']} / {a['buck']['U2.3_to_C5.1_mm']}"],
        ['5V_SW segments / vias / layers (LR-05)', f"{b['buck']['5V_SW_segments']} / {b['buck']['5V_SW_vias']} / {b['buck']['5V_SW_layers']}",
         f"{a['buck']['5V_SW_segments']} / {a['buck']['5V_SW_vias']} / {a['buck']['5V_SW_layers']}"],
        ['5V_SW track length (mm) / min width (mm)', f"{b['buck']['5V_SW_track_mm']} / {b['buck']['5V_SW_min_width_mm']}", f"{a['buck']['5V_SW_track_mm']} / {a['buck']['5V_SW_min_width_mm']}"],
        ['C6 (bootstrap) pad 2 to U2.2 (mm)', b['buck']['C6_pad2_to_U2.2_mm'], a['buck']['C6_pad2_to_U2.2_mm']],
        ['Exposed-pad vias U1.17 / U3.29 (LR-06)', f"{b['exposed_pad_vias']['U1.17']} / {b['exposed_pad_vias']['U3.29']}", f"{a['exposed_pad_vias']['U1.17']} / {a['exposed_pad_vias']['U3.29']}"],
        ['12V_IN tracks: min-max width (mm) / vias (LR-07)', f"{sb('12V_IN', 'min_width_mm')}-{sb('12V_IN', 'max_width_mm')} / {sb('12V_IN', 'vias')}",
         f"{st('12V_IN', 'min_width_mm')}-{st('12V_IN', 'max_width_mm')} / {st('12V_IN', 'vias')}"],
        ['12V_PROT tracks: min-max width (mm) / vias', f"{sb('12V_PROT', 'min_width_mm')}-{sb('12V_PROT', 'max_width_mm')} / {sb('12V_PROT', 'vias')}",
         f"{st('12V_PROT', 'min_width_mm')}-{st('12V_PROT', 'max_width_mm')} / {st('12V_PROT', 'vias')}"],
        ['EFUSE_RTN / 5V max track width (mm)', f"{sb('EFUSE_RTN', 'max_width_mm')} / {sb('5V', 'max_width_mm')}", f"{st('EFUSE_RTN', 'max_width_mm')} / {st('5V', 'max_width_mm')}"],
        ['J4 / J5 distance to the nearer board edge (mm) (LR-09)', b['J4_J5_edge_distance_mm'], a['J4_J5_edge_distance_mm']],
        ['DSP bypass pin-to-capacitor max / mean (mm) (LR-13)', f"{b['dsp_bypass_mm']['max']} / {b['dsp_bypass_mm']['mean']}", f"{a['dsp_bypass_mm']['max']} / {a['dsp_bypass_mm']['mean']}"],
        ['Y1 centre / Y1 pad 3 to XCLKIN (mm) (LR-16)', f"{b['Y1_to_XCLKIN_mm']} / {b['Y1_pad3_to_XCLKIN_mm']}", f"{a['Y1_to_XCLKIN_mm']} / {a['Y1_pad3_to_XCLKIN_mm']}"],
        ['ISENSE / ISENSE_REF track (mm), mismatch (LR-14)', b['isense_pair_mm'], a['isense_pair_mm']],
        ['PWM / TZ track lengths (mm)', b['pwm_tz_track_mm'], a['pwm_tz_track_mm']],
        ['GND_CTRL In1.Cu area (mm2) / outlines', f"{b['GND_CTRL_In1_area_mm2']} / {b['GND_CTRL_In1_outlines']}", f"{a['GND_CTRL_In1_area_mm2']} / {a['GND_CTRL_In1_outlines']}"],
        ['Zone-fill slivers < 0.01 mm2 (LR-15)', b['In_fill_slivers_lt_0.01mm2'], a['In_fill_slivers_lt_0.01mm2']],
        ['Min track/via copper to board edge (mm)', b['min_track_via_to_edge_mm'], a['min_track_via_to_edge_mm']],
    ]
    lines += md_table(['Metric', 'Before (reviewed board)', 'After'], rows)
    lines += ['', 'ADC filter capacitor distances per pin (mm):', '']
    lines += md_table(['Pin -> capacitor', 'Before', 'After'], [[k, b['adc_filter_pin_to_cap_mm'].get(k), a['adc_filter_pin_to_cap_mm'].get(k)] for k in a['adc_filter_pin_to_cap_mm']])
    if c['routing_progress'].get('unresolved_nets'):
        lines += ['', f"Open connections after the corrections (router record, confirmed by the DRC unconnected count): {', '.join(c['routing_progress']['unresolved_nets'])}.", '']
    if c['routing_progress'].get('signal_order_trials'):
        lines += ['', 'Routing-order trials of the final run (grid router, same placement; the best was kept):', '']
        lines += md_table(['Trial', 'Order', 'Unresolved', 'Track (mm)'], [[t['trial'], t['order'], t['unresolved'], t['track_mm']] for t in c['routing_progress']['signal_order_trials']])
    lines += ['', '### Checker rows that changed value or disposition', '']
    rb, ra = c['checker_rows_before'], c['checker_rows_after']
    changed = [[k, str(rb[k][0])[:60], (rb[k][1] or '')[:22], str(ra[k][0])[:60], (ra[k][1] or '')[:22]] for k in ra if k in rb and (rb[k][0] != ra[k][0] or rb[k][1] != ra[k][1])]
    lines += md_table(['Rule | metric', 'Before', 'Disp.', 'After', 'Disp.'], changed) if changed else ['(none)']
    p = doc['power']
    lines += ['', '## Power board', '']
    if p['after']:
        pa, pdrc = p['after'], p['drc_after'] or {}
        rows = [['Board', 'absent (LR-01)', f"`kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb` sha256 {pa['sha256'][:16]}..."],
                ['Outline (mm)', '-', pa['outline_mm']], ['Footprints / on B.Cu', '-', f"{pa['footprints']} / {pa['footprints_B_Cu']}"],
                ['Tracks / vias (1.2 mm HV vias) / zones (rule areas)', '-', f"{pa['tracks']} / {pa['vias']} ({pa['hv_vias_1p2mm']}) / {pa['zones']} ({pa['rule_areas']})"],
                ['Total track length (mm)', '-', pa['total_track_mm']],
                ['DRC violations / unconnected / parity', 'no DRC', f"{pdrc.get('violations')} / {pdrc.get('unconnected_items')} / {pdrc.get('schematic_parity')}"],
                ['DRC manifest', '-', pdrc.get('manifest')], ['DRC violation types', '-', pdrc.get('violation_types')],
                ['Router unresolved connections', '-', p['routing_progress'].get('unresolved_count')],
                ['Barrier-part line y (mm)', '-', pa['barrier_line_y_mm']], ['Key positions (mm)', '-', pa['positions']],
                ['Checker summary', 'no metrics', p.get('checker_summary')]]
        lines += md_table(['Metric', 'Before (review)', 'After'], rows)
        lines += ['', 'Checker rows (power spec, corrected per LR-08):', '']
        lines += md_table(['Rule | metric', 'Measured', 'Disposition'], [[k, str(v[0])[:90], (v[1] or '')[:40]] for k, v in p['checker_rows'].items()])
    else:
        lines += ['No power board file exists after this run (LR-01 not closed).']
    lines += ['', '## Findings: applied / not applied', '']
    status = doc.get('finding_status', {})
    lines += md_table(['ID', 'Severity', 'Automation-verifiable', 'Status after this run'],
                      [[fid, f['severity'], f['verifiable_by_automation'], status.get(fid, '')] for fid, f in doc['findings'].items()])
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    raise SystemExit(main())
