"""Second correction pass (review LR-20..LR-35): measured before / after record for the V2 power and control boards.

Appends a "Pass 2" section to examples/sic-buck-400v-200v-5kw/verification/optimisation_before_after.md and a ``pass2`` key to the
.json written by optimisation_report_sic.py. "Before" are the boards the second review judged (copies given on the command line,
sha256 recorded), "after" are the current board files. Every figure is measured from the board files (pcbnew 10 geometry dump,
shapely analysis), copied from the named kicad-cli DRC manifests, the stored-fill diagnostics or the layout-metrics checker; the
finding dispositions come from verification/optimisation_finding_status_pass2.json. Only the DRC manifests are verification.

Run (host Python with shapely; the geometry dumps re-execute this file under KiCad's Python):
    python automation/scripts/optimisation_report_sic_pass2.py --before-power <copy> --before-control <copy>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXAMPLE = ROOT / 'examples/sic-buck-400v-200v-5kw'
VER = EXAMPLE / 'verification'
CHECKS = VER / 'engineering_checks'
POWER_PCB = EXAMPLE / 'kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb'
CONTROL_PCB = EXAMPLE / 'kicad/control_board/AIPE_SiC_Buck_Control.kicad_pcb'
BANNER = 'AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED'
HV_NETS = {'VIN', 'VIN_RAW', 'VIN_PRE', 'PGND', 'SW', 'VOUT', 'VOUT_L', 'SNUB_MID', 'DAMP_MID', 'PE_REF_MID', 'BLD_IN_1', 'BLD_IN_2', 'IND_IN_1',
           'IND_IN_2', 'IND_IN_3', 'BLD_OUT_1', 'IND_OUT_1', 'IND_OUT_2', 'VIN_DIV_T1', 'VIN_DIV_T2', 'VIN_DIV_T3', 'VOUT_DIV_T1'}
CONTROL_NETS = ('DSP_TRIP_N', 'FAULT_N', 'OC_N', 'XRS_N', 'ESTOP_N', 'FLT_H_N', 'FLT_L_N', 'RDY_L', 'ISENSE', 'ISENSE_REF', 'VIN_SENSE', 'VOUT_SENSE',
                'ADC_VOUT', 'EPWM1A', 'EPWM1B', 'PWM_H', 'PWM_L')


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


# --- KiCad-side geometry dump (runs under KiCad Python: --dump) ----------------------------------------------------------


def dump_geometry(board_path: str, kind: str, out: str) -> None:
    import pcbnew as pcb
    board = pcb.LoadBoard(board_path)
    mm = pcb.ToMM
    data = dict(board=board_path, sha256=sha(Path(board_path)), zones=[], tracks=[], vias=[], pads=[], footprints={}, rule_areas=0)
    for z in board.Zones():
        if z.GetIsRuleArea():
            data['rule_areas'] += 1
            continue
        for layer in z.GetLayerSet().Seq():
            fill = z.GetFilledPolysList(layer)
            polys = []
            for i in range(fill.OutlineCount()):
                ring = fill.Outline(i)
                shell = [[mm(ring.CPoint(k).x), mm(ring.CPoint(k).y)] for k in range(ring.PointCount())]
                holes = []
                for h in range(fill.HoleCount(i)):
                    hr = fill.Hole(i, h)
                    holes.append([[mm(hr.CPoint(k).x), mm(hr.CPoint(k).y)] for k in range(hr.PointCount())])
                polys.append(dict(shell=shell, holes=holes))
            data['zones'].append(dict(net=z.GetNetname(), layer=board.GetLayerName(layer), polys=polys))
    for t in board.GetTracks():
        if isinstance(t, pcb.PCB_VIA):
            data['vias'].append(dict(net=t.GetNetname(), xy=[mm(t.GetPosition().x), mm(t.GetPosition().y)], d=mm(t.GetWidth(t.GetLayer()))))
        else:
            data['tracks'].append(dict(net=t.GetNetname(), layer=board.GetLayerName(t.GetLayer()), a=[mm(t.GetStart().x), mm(t.GetStart().y)],
                                       b=[mm(t.GetEnd().x), mm(t.GetEnd().y)], w=mm(t.GetWidth()), length=mm(t.GetLength())))
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        try:
            cy = fp.GetCourtyard(pcb.B_CrtYd if fp.IsFlipped() else pcb.F_CrtYd).BBox()
            court = [mm(cy.GetX()), mm(cy.GetY()), mm(cy.GetRight()), mm(cy.GetBottom())]
        except Exception:
            court = None
        data['footprints'][ref] = dict(xy=[mm(fp.GetPosition().x), mm(fp.GetPosition().y)], side='B' if fp.IsFlipped() else 'F', courtyard=court)
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            data['pads'].append(dict(ref=ref, num=pad.GetNumber(), net=pad.GetNetname(), xy=[mm(pad.GetPosition().x), mm(pad.GetPosition().y)],
                                     box=[mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom())], thru=pad.GetAttribute() in (0, 3),
                                     layers=[board.GetLayerName(l) for l in pad.GetLayerSet().Seq() if board.GetLayerName(l).endswith('.Cu')],
                                     drill=mm(pad.GetDrillSize().x)))
    if kind == 'control':
        from automation.scripts import optimisation_report_sic as base
        data['control_measures'] = base.measure_control(Path(board_path))
    Path(out).write_text(json.dumps(data), encoding='utf-8')


def kicad_python():
    from automation.scripts.optimisation_report_sic import kicad_python as kp
    return kp()


def geometry(board: Path, kind: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'geom.json'
        cmd = [str(kicad_python()), str(Path(__file__).resolve()), '--dump', str(board), kind, str(out)]
        completed = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(ROOT), timeout=900)
        if completed.returncode or not out.is_file():
            raise RuntimeError(f'geometry dump failed for {board}: {completed.stderr[-1500:]}')
        return read_json(out)


# --- host-side analysis (shapely) -----------------------------------------------------------------------------------------


def copper(data, nets, layer):
    from shapely.geometry import LineString, Point, Polygon, box
    from shapely.ops import unary_union
    parts = []
    for z in data['zones']:
        if z['net'] in nets and z['layer'] == layer:
            for p in z['polys']:
                if len(p['shell']) >= 3:
                    parts.append(Polygon(p['shell'], [h for h in p['holes'] if len(h) >= 3]).buffer(0))
    for t in data['tracks']:
        if t['net'] in nets and t['layer'] == layer:
            parts.append(LineString([t['a'], t['b']]).buffer(t['w'] / 2))
    for v in data['vias']:
        if v['net'] in nets:
            parts.append(Point(v['xy']).buffer(v['d'] / 2))
    for p in data['pads']:
        if p['net'] in nets and (p['thru'] or layer in p['layers']):
            parts.append(box(*p['box']))
    return unary_union(parts) if parts else Polygon()


def pad_xy(data, ref, num):
    return next((p['xy'] for p in data['pads'] if p['ref'] == ref and p['num'] == num), None)


def inside_point(geom, near):
    from shapely.geometry import Point
    if geom.is_empty:
        return None
    pt = Point(near)
    best = min(getattr(geom, 'geoms', [geom]), key=lambda g: g.distance(pt))
    if best.contains(pt):
        return pt
    q = best.exterior.interpolate(best.exterior.project(pt))
    c = best.centroid
    for f in (0.3, 0.6, 1.0, 1.5, 2.0, 3.0):
        d = math.dist((q.x, q.y), (c.x, c.y)) or 1.0
        cand = Point(q.x + (c.x - q.x) / d * f, q.y + (c.y - q.y) / d * f)
        if best.contains(cand):
            return cand
    return best.representative_point()


def neck_width(geom, a, b, r_max=20.0):
    """Largest 2r (mm) such that a and b stay in one connected copper part after eroding the layer's copper by r (binary search):
    the narrowest passage of the current path between the two points, measured on the stored fills."""
    pa, pb = inside_point(geom, a), inside_point(geom, b)
    if pa is None or pb is None:
        return None

    def connected(r):
        # the eroded part must still reach the neighbourhood of both probe points: a point sitting 2 mm from the copper edge (a pad
        # centre, a via group) is r + 2 mm from the eroded part, so the tolerance grows with r (r + 3 mm)
        g = geom.buffer(-r) if r > 0 else geom
        if g.is_empty:
            return False
        tol = r + 3.0
        for part in getattr(g, 'geoms', [g]):
            if part.distance(pa) <= tol and part.distance(pb) <= tol:
                return True
        return False
    if not connected(0.0):
        return 0.0
    lo, hi = 0.0, r_max
    for _ in range(14):
        mid = (lo + hi) / 2
        if connected(mid):
            lo = mid
        else:
            hi = mid
    return round(2 * lo, 2)


def courtyard_distance(fa, fb):
    from shapely.geometry import box
    if not fa or not fb or not fa.get('courtyard') or not fb.get('courtyard'):
        return None
    return round(box(*fa['courtyard']).distance(box(*fb['courtyard'])), 2)


def analyse_power(data: dict) -> dict:
    from shapely.geometry import Point, Polygon
    fps = data['footprints']
    out = dict(sha256=data['sha256'], tracks=len(data['tracks']), vias=len(data['vias']), zone_layers=len(data['zones']), rule_areas=data['rule_areas'],
               total_track_mm=round(sum(t['length'] for t in data['tracks']), 1),
               vias_per_net={n: sum(1 for v in data['vias'] if v['net'] == n) for n in ('VIN', 'SW', 'PGND', 'VOUT')})
    areas = {}
    for z in data['zones']:
        key = f"{z['net']}/{z['layer']}"
        areas[key] = round(areas.get(key, 0.0) + sum(Polygon(p['shell'], p['holes']).area for p in z['polys'] if len(p['shell']) >= 3), 1)
    out['fill_areas_mm2'] = {k: areas[k] for k in ('VIN/F.Cu', 'VIN/In2.Cu', 'PGND/In1.Cu', 'PGND/B.Cu', 'SW/F.Cu', 'SW/In2.Cu', 'VOUT/F.Cu', 'VOUT/In2.Cu', 'VOUT/B.Cu') if k in areas}
    j2, j4, j6, j3 = (fps[r]['xy'] for r in ('J2', 'J4', 'J6', 'J3'))
    q2s, q1s, q1d, l1, c1p, c6v, c13 = (pad_xy(data, *k) for k in (('Q2', '2'), ('Q1', '2'), ('Q1', '1'), ('L1', '1'), ('C1', '2'), ('C6', '1'), ('C13', '1')))
    necks = {}
    for layer in ('In1.Cu', 'B.Cu'):
        g = copper(data, {'PGND'}, layer)
        necks[f'PGND J2 -> Q2.2 {layer}'] = neck_width(g, j2, q2s)
        necks[f'PGND J2 -> C1.2 {layer}'] = neck_width(g, j2, c1p)
        necks[f'PGND J4 -> Q2.2 {layer}'] = neck_width(g, j4, q2s)
    c6p = pad_xy(data, 'C6', '2')
    for layer in ('In1.Cu', 'B.Cu'):  # the HF tier's west end (the B.Cu PGND column reaches it; the HS bias island starts at x 64.6)
        necks[f'PGND J2 -> C6.2 {layer}'] = neck_width(copper(data, {'PGND'}, layer), j2, c6p)
    sw_in2 = copper(data, {'SW'}, 'In2.Cu')
    necks['SW Q1.2 -> L1.1 In2.Cu'] = neck_width(sw_in2, q1s, l1)
    necks['SW via group (109, 125) -> L1.1 In2.Cu'] = neck_width(sw_in2, (109.0, 125.0), l1)  # from the 24-via group, past the pin-field attachment
    necks['VIN J6 -> Q1.1 In2.Cu'] = neck_width(copper(data, {'VIN'}, 'In2.Cu'), j6, q1d)
    necks['VIN C6.1 -> Q1.1 F.Cu'] = neck_width(copper(data, {'VIN'}, 'F.Cu'), c6v, q1d)
    for layer in ('F.Cu', 'In2.Cu', 'B.Cu'):
        necks[f'VOUT C13.1 -> J3 {layer}'] = neck_width(copper(data, {'VOUT'}, layer), c13, j3)
    out['neck_widths_mm'] = necks
    holes = [p for p in data['pads'] if p['ref'] == 'HS1']
    out['hs1_hole_wall_to_hv_copper_mm'] = {layer: [round(copper(data, HV_NETS, layer).distance(Point(h['xy']).buffer(h['drill'] / 2)), 2) for h in holes]
                                            for layer in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')}
    out['courtyard_to_sink_mm'] = {r: courtyard_distance(fps.get(r), fps.get('HS1')) for r in ('C11', 'C12', 'C13', 'C14', 'L1', 'RT1', 'RV1', 'J3', 'J4')}
    out['films_to_L1_mm'] = {r: courtyard_distance(fps.get(r), fps.get('L1')) for r in ('C13', 'C14')}
    hf = {f'C{i}' for i in range(1, 11)}

    def nearest(point, net):
        best = None
        for p in data['pads']:
            if p['ref'] in hf and p['net'] == net:
                d = math.dist(point, p['xy'])
                if best is None or d < best[0]:
                    best = (round(d, 2), f"{p['ref']}.{p['num']}")
        return best
    out['hf_caps'] = {'Q1.1 VIN -> nearest VIN pad': nearest(q1d, 'VIN'), 'Q2.2 PGND -> nearest PGND pad': nearest(q2s, 'PGND')}
    out['positions'] = {r: [round(v, 2) for v in fps[r]['xy']] for r in ('HS1', 'J1', 'J2', 'J5', 'J6', 'J3', 'J4', 'RT1', 'RV1', 'C13', 'C14') if r in fps}
    return out


def analyse_control(data: dict) -> dict:
    out = dict(sha256=data['sha256'], tracks=len(data['tracks']), vias=len(data['vias']), total_track_mm=round(sum(t['length'] for t in data['tracks']), 1))
    out['nets'] = {n: dict(track_mm=round(sum(t['length'] for t in data['tracks'] if t['net'] == n), 1), vias=sum(1 for v in data['vias'] if v['net'] == n))
                   for n in CONTROL_NETS}
    m = data.get('control_measures', {})
    out['adc_filter_pin_to_cap_mm'] = m.get('adc_filter_pin_to_cap_mm')
    out['adc_filter_max_mm'] = m.get('adc_filter_max_mm')
    out['dsp_bypass_mm'] = m.get('dsp_bypass_mm')
    out['J8'] = m.get('J8')
    out['GND_CTRL_In1_area_mm2'] = m.get('GND_CTRL_In1_area_mm2')
    out['GND_CTRL_In1_outlines'] = m.get('GND_CTRL_In1_outlines')
    out['min_track_via_to_edge_mm'] = m.get('min_track_via_to_edge_mm')
    return out


# --- records -------------------------------------------------------------------------------------------------------------


def drc_summary(manifest_path):
    from automation.scripts.optimisation_report_sic import drc_summary as ds
    return ds(manifest_path)


def latest_drc_for(name):
    from automation.scripts.optimisation_report_sic import latest_drc_for as ld
    return ld(name)


def checker_rows(path):
    if not Path(path).is_file():
        return {}
    return {f"{r['rule']} | {r['metric'][:70]}": (r.get('measured'), r.get('disposition')) for r in read_json(path).get('rule_table', [])}


def changed_rows(before: dict, after: dict) -> list:
    return [[k, str(before[k][0])[:60], (before[k][1] or '')[:22], str(after[k][0])[:60], (after[k][1] or '')[:22]]
            for k in after if k in before and (before[k][0] != after[k][0] or before[k][1] != after[k][1])]


def md_table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '---|' * len(headers)]
    out += ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]
    return out


def pair(b, a, key, default='-'):
    return [b.get(key, default) if isinstance(b, dict) else default, a.get(key, default) if isinstance(a, dict) else default]


def power_rows(b: dict, a: dict, db: dict, da: dict, sfb: dict, sfa: dict) -> list:
    rows = [['Board sha256', b['sha256'][:16] + '...', a['sha256'][:16] + '...'],
            ['Tracks / vias / zone layers / rule areas', f"{b['tracks']} / {b['vias']} / {b['zone_layers']} / {b['rule_areas']}", f"{a['tracks']} / {a['vias']} / {a['zone_layers']} / {a['rule_areas']}"],
            ['Total track length (mm)', b['total_track_mm'], a['total_track_mm']],
            ['DRC violations / unconnected / parity (run_check, --refill-zones)', f"{db.get('violations')} / {db.get('unconnected_items')} / {db.get('schematic_parity')}",
             f"{da.get('violations')} / {da.get('unconnected_items')} / {da.get('schematic_parity')}"],
            ['DRC manifest', db.get('manifest'), da.get('manifest')],
            ['Stored fills checked WITHOUT refill: clearance findings (LR-20, diagnostic)', sfb, sfa],
            ['Fill areas (mm2) VIN F.Cu / VIN In2 / PGND In1 / PGND B.Cu / SW In2', ' / '.join(str(b['fill_areas_mm2'].get(k)) for k in ('VIN/F.Cu', 'VIN/In2.Cu', 'PGND/In1.Cu', 'PGND/B.Cu', 'SW/In2.Cu')),
             ' / '.join(str(a['fill_areas_mm2'].get(k)) for k in ('VIN/F.Cu', 'VIN/In2.Cu', 'PGND/In1.Cu', 'PGND/B.Cu', 'SW/In2.Cu'))],
            ['HS1 hole wall to HV copper, min per layer F / In1 / In2 / B (mm) (LR-21)', ' / '.join(str(min(b['hs1_hole_wall_to_hv_copper_mm'][l])) for l in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')),
             ' / '.join(str(min(a['hs1_hole_wall_to_hv_copper_mm'][l])) for l in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'))]]
    for key in b['neck_widths_mm']:
        rows.append([f'Neck width {key} (mm)', b['neck_widths_mm'][key], a['neck_widths_mm'].get(key)])
    rows += [['PGND / SW / VIN / VOUT vias', ' / '.join(str(b['vias_per_net'][n]) for n in ('PGND', 'SW', 'VIN', 'VOUT')), ' / '.join(str(a['vias_per_net'][n]) for n in ('PGND', 'SW', 'VIN', 'VOUT'))],
             ['Courtyard distance to the sink: C11 / C12 / C13 / L1 / RT1 / RV1 (mm) (LR-25)', ' / '.join(str(b['courtyard_to_sink_mm'][r]) for r in ('C11', 'C12', 'C13', 'L1', 'RT1', 'RV1')),
              ' / '.join(str(a['courtyard_to_sink_mm'][r]) for r in ('C11', 'C12', 'C13', 'L1', 'RT1', 'RV1'))],
             ['Films C13 / C14 to L1 courtyard (mm)', f"{b['films_to_L1_mm']['C13']} / {b['films_to_L1_mm']['C14']}", f"{a['films_to_L1_mm']['C13']} / {a['films_to_L1_mm']['C14']}"],
             ['Q1.1 -> nearest VIN HF pad; Q2.2 -> nearest PGND HF pad (mm) (LR-22)', f"{b['hf_caps']['Q1.1 VIN -> nearest VIN pad']} ; {b['hf_caps']['Q2.2 PGND -> nearest PGND pad']}",
              f"{a['hf_caps']['Q1.1 VIN -> nearest VIN pad']} ; {a['hf_caps']['Q2.2 PGND -> nearest PGND pad']}"],
             ['Positions J2 / J6 / RV1 / HS1 / J3 / J4 / C13 (mm)', ' ; '.join(f"{r} {b['positions'].get(r)}" for r in ('J2', 'J6', 'RV1', 'HS1', 'J3', 'J4', 'C13')),
              ' ; '.join(f"{r} {a['positions'].get(r)}" for r in ('J2', 'J6', 'RV1', 'HS1', 'J3', 'J4', 'C13'))]]
    return rows


def control_rows(b: dict, a: dict, db: dict, da: dict) -> list:
    rows = [['Board sha256', b['sha256'][:16] + '...', a['sha256'][:16] + '...'],
            ['Tracks / vias', f"{b['tracks']} / {b['vias']}", f"{a['tracks']} / {a['vias']}"],
            ['Total track length (mm)', b['total_track_mm'], a['total_track_mm']],
            ['DRC violations / unconnected / parity', f"{db.get('violations')} / {db.get('unconnected_items')} / {db.get('schematic_parity')}",
             f"{da.get('violations')} / {da.get('unconnected_items')} / {da.get('schematic_parity')}"],
            ['DRC manifest', db.get('manifest'), da.get('manifest')]]
    for n in CONTROL_NETS:
        rows.append([f'{n}: track (mm) / vias', f"{b['nets'][n]['track_mm']} / {b['nets'][n]['vias']}", f"{a['nets'][n]['track_mm']} / {a['nets'][n]['vias']}"])
    rows += [['ADC 1 nF filter pin-to-capacitor max (mm) (LR-33)', b.get('adc_filter_max_mm'), a.get('adc_filter_max_mm')],
             ['DSP bypass max / mean (mm)', f"{(b.get('dsp_bypass_mm') or {}).get('max')} / {(b.get('dsp_bypass_mm') or {}).get('mean')}", f"{(a.get('dsp_bypass_mm') or {}).get('max')} / {(a.get('dsp_bypass_mm') or {}).get('mean')}"],
             ['J8 side / pin 1 (mm) (LR-27)', f"{(b.get('J8') or {}).get('side')} / {(b.get('J8') or {}).get('pin1')}", f"{(a.get('J8') or {}).get('side')} / {(a.get('J8') or {}).get('pin1')}"],
             ['GND_CTRL In1.Cu area (mm2) / outlines', f"{b.get('GND_CTRL_In1_area_mm2')} / {b.get('GND_CTRL_In1_outlines')}", f"{a.get('GND_CTRL_In1_area_mm2')} / {a.get('GND_CTRL_In1_outlines')}"],
             ['Min track/via copper to board edge (mm)', b.get('min_track_via_to_edge_mm'), a.get('min_track_via_to_edge_mm')]]
    return rows


def main(argv=None) -> int:
    if argv is None and len(sys.argv) > 1 and sys.argv[1] == '--dump':
        dump_geometry(sys.argv[2], sys.argv[3], sys.argv[4])
        return 0
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--before-power', type=Path, required=True)
    parser.add_argument('--before-control', type=Path, required=True)
    parser.add_argument('--before-power-drc', default='verification/drc/20261011T021012Z-drc-0ebee900/run.json')
    parser.add_argument('--before-control-drc', default='verification/drc/20261011T021018Z-drc-b9c91de5/run.json')
    parser.add_argument('--status', type=Path, default=VER / 'optimisation_finding_status_pass2.json')
    args = parser.parse_args(argv)
    pb, pa = analyse_power(geometry(args.before_power, 'power')), analyse_power(geometry(POWER_PCB, 'power'))
    cb, ca = analyse_control(geometry(args.before_control, 'control')), analyse_control(geometry(CONTROL_PCB, 'control'))
    pdb, pda = drc_summary(EXAMPLE / args.before_power_drc) or {}, drc_summary(latest_drc_for('AIPE_SiC_Buck_Power')) or {}
    cdb, cda = drc_summary(EXAMPLE / args.before_control_drc) or {}, drc_summary(latest_drc_for('AIPE_SiC_Buck_Control')) or {}
    sf_before = read_json(CHECKS / 'stored_zone_fill_check.json') if (CHECKS / 'stored_zone_fill_check.json').is_file() else {}
    sfb = (sf_before.get('boards', {}).get('power', {}).get('stored_fill_drc', {}) or {}).get('violations_excluding_lib_warning', '-')
    sfa_rec = read_json(CHECKS / 'stored_zone_fill_check_power.json') if (CHECKS / 'stored_zone_fill_check_power.json').is_file() else {}
    sfa = f"{sfa_rec.get('violations', '-')} (by rule: {sfa_rec.get('by_rule')})" if sfa_rec else '-'
    status = read_json(args.status) if args.status.is_file() else {}
    findings = {f['id']: f for f in read_json(VER / 'layout_review_findings.json')['findings']}
    metrics = dict(power=(checker_rows(CHECKS / 'layout_metrics_power_before2.json'), checker_rows(CHECKS / 'layout_metrics_power.json')),
                   control=(checker_rows(CHECKS / 'layout_metrics_control_before2.json'), checker_rows(CHECKS / 'layout_metrics_control.json')))
    summary = {b: ((read_json(CHECKS / f'layout_metrics_{b}_before2.json').get('summary') if (CHECKS / f'layout_metrics_{b}_before2.json').is_file() else None),
                   (read_json(CHECKS / f'layout_metrics_{b}.json').get('summary') if (CHECKS / f'layout_metrics_{b}.json').is_file() else None)) for b in ('power', 'control')}
    progress = {b: read_json(VER / f'routing_progress_{b}.json') if (VER / f'routing_progress_{b}.json').is_file() else {} for b in ('power', 'control')}
    pass2 = dict(generated_utc=datetime.now(timezone.utc).isoformat(), review='verification/layout_review_findings.json (schema 2, LR-20..LR-35)',
                 before_boards=dict(power=dict(path=str(args.before_power), sha256=pb['sha256']), control=dict(path=str(args.before_control), sha256=cb['sha256'])),
                 power=dict(before=pb, after=pa, drc_before=pdb, drc_after=pda, stored_fill_check_before=sf_before.get('boards', {}).get('power'), stored_fill_check_after=sfa_rec,
                            checker_summary_before=summary['power'][0], checker_summary_after=summary['power'][1], checker_rows_changed=changed_rows(*metrics['power']),
                            routing_progress=dict(unresolved_count=progress['power'].get('unresolved_count'), stage=progress['power'].get('stage'),
                                                  rule_aware_refill=progress['power'].get('rule_aware_refill'), stored_fill_check=progress['power'].get('stored_fill_check'))),
                 control=dict(before=cb, after=ca, drc_before=cdb, drc_after=cda, checker_summary_before=summary['control'][0], checker_summary_after=summary['control'][1],
                              checker_rows_changed=changed_rows(*metrics['control']),
                              routing_progress=dict(unresolved_count=progress['control'].get('unresolved_count'), stage=progress['control'].get('stage'),
                                                    signal_order_selected=progress['control'].get('signal_order_selected'))),
                 finding_status=status)
    doc_path = VER / 'optimisation_before_after.json'
    doc = read_json(doc_path) if doc_path.is_file() else dict(schema_version=1, status=BANNER)
    doc['pass2'] = pass2
    doc_path.write_text(json.dumps(doc, indent=2, default=str) + '\n', encoding='utf-8')
    lines = ['', '---', '', '# Pass 2 - second independent review (LR-20..LR-35): measured before / after', '',
             f"Generated {pass2['generated_utc']} by `automation/scripts/optimisation_report_sic_pass2.py`. \"Before\" are the boards the second review judged "
             f"(power sha256 `{pb['sha256'][:16]}...`, control `{cb['sha256'][:16]}...`), \"after\" the current board files. Neck widths are erosion-connectivity "
             'measurements on the STORED fills (largest 2r for which the two named points stay connected after eroding the layer copper by r); hole and courtyard '
             'distances are copper / courtyard geometry. Only the DRC manifests are verification; the stored-fill rows are diagnostics.', '',
             '## Power board', '']
    lines += md_table(['Metric', 'Before (reviewed board)', 'After'], power_rows(pb, pa, pdb, pda, sfb, sfa))
    lines += ['', f"Checker summary before / after: {summary['power'][0]} / {summary['power'][1]}", '', '### Checker rows that changed value or disposition (power)', '']
    ch = pass2['power']['checker_rows_changed']
    lines += md_table(['Rule | metric', 'Before', 'Disp.', 'After', 'Disp.'], ch) if ch else ['(none)']
    lines += ['', '## Control board', '']
    lines += md_table(['Metric', 'Before (reviewed board)', 'After'], control_rows(cb, ca, cdb, cda))
    lines += ['', f"Checker summary before / after: {summary['control'][0]} / {summary['control'][1]}", '', '### Checker rows that changed value or disposition (control)', '']
    ch = pass2['control']['checker_rows_changed']
    lines += md_table(['Rule | metric', 'Before', 'Disp.', 'After', 'Disp.'], ch) if ch else ['(none)']
    lines += ['', '## Findings LR-20..LR-35: applied / not applied', '']
    lines += md_table(['ID', 'Severity', 'Board', 'Automation-verifiable', 'Status after pass 2'],
                      [[fid, f['severity'], f['board'], f['verifiable_by_automation'], status.get(fid, '(no disposition recorded)')] for fid, f in findings.items()])
    md_path = VER / 'optimisation_before_after.md'
    text = md_path.read_text(encoding='utf-8') if md_path.is_file() else f'**{BANNER}**\n\n# Layout-review corrections - measured before / after\n'
    marker = '\n---\n\n# Pass 2 - second independent review'
    if marker in text:
        text = text[:text.index(marker)]
    md_path.write_text(text.rstrip('\n') + '\n' + '\n'.join(lines) + '\n', encoding='utf-8')
    print('written', doc_path, 'and', md_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
