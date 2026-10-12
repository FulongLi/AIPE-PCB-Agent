"""Routing-quality checker for KiCad boards (V2.1 TASK 2).

Measures the geometry of the routed copper of a ``.kicad_pcb`` and writes ``routing_quality_<label>.json`` plus a
Markdown summary. Per board, per layer, per net and per attribution (router-made, pre-routed, pad link):

- counts: straight segments, arcs, vias, routed length (true arc length for arcs), minimum track width;
- bends at the joints of two straight items: 90-degree (85-95), 45-degree (40-50), other (> 5 deg), direction changes
  (every joint turning more than the straight tolerance), bends per 100 mm;
- short-run analysis on the straight parts of every chain: stair runs (>= 3 short segments with alternating turn signs,
  the 4-direction router's staircases), zigzag runs (other sign patterns: meanders and detours), short segments
  (< ``short_mm``) and runs of repeated short segments;
- routing efficiency per chain between anchors (pads, vias, junctions, layer changes): Euclidean span / routed length,
  length-weighted per net and per board; nets with filled zones are flagged (their connections may be through copper pours);
- arc continuity: angle error between an arc's tangent and the neighbouring item's direction at every arc joint;
- optional linkage to a native DRC manifest (``run.json`` of ``automation.kicad_tools.run_check``: finding counts and whether
  the DRC ran on the same board bytes) and to the routing plan (``pre_routed`` tracks -> attribution 'pre_routed';
  the ``beautify`` exception list of a routing report -> reasons for the remaining sharp corners).

The chain extraction is ``automation.kicad_tools.path_geometry.chains_from_items`` - the same code the router's beautify
stage uses - so router and checker agree on what a corner is. The measurement core works on a plain dict (the
``extract_board`` output), so it is unit-tested with the host interpreter; only ``extract_board`` needs pcbnew and the
script re-executes itself under KiCad's bundled Python when pcbnew is not importable.

Compare mode measures two boards (before / after) and writes the deltas. Dispositions are "measured - human review
required": the numbers describe geometry only, never inductance, EMI or current capacity.

Run:
    <kicad-python> automation/verification/check_routing_quality.py <board.kicad_pcb> [--compare <after.kicad_pcb>]
        [--output <dir>] [--label <name>] [--plan <routing_plan.json>] [--report <routing_progress.json>]
        [--drc <run.json>] [--baseline <routing_quality_x.json>] [--short-mm 0.5] [--l-short-mm 1.0]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.kicad_tools import path_geometry as pg  # noqa: E402

STATUS = 'measured - human review required'
SCHEMA_VERSION = 1
NM_PER_MM = 1_000_000
DEFAULT_PARAMS = dict(short_mm=0.5, l_short_mm=1.0, straight_tol_deg=pg.STRAIGHT_TOL_DEG, tangent_tol_deg=1.0, min_turn_deg=40.0,
                      quantum_nm=1000, efficiency_min_span_mm=2.0)
TOTAL_KEYS = ('segments', 'arcs', 'vias', 'length_mm', 'arc_length_mm', 'joints', 'bends_90', 'bends_45', 'bends_other', 'direction_changes',
              'stair_runs', 'zigzag_runs', 'short_run_segments', 'short_segments', 'short_segment_runs', 'arc_joints', 'arc_joints_discontinuous',
              'chains', 'degree2_joints', 'degree2_bends_90')


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ----- extraction (pcbnew) --------------------------------------------------------------------------------------------
def extract_board(board_path) -> dict:
    """Load a board read-only with pcbnew and return the plain-dict geometry the measurement core consumes: straight
    segments and arcs (nm endpoints, mm width and true length, KIID), vias, the endpoints that lie inside a pad of their
    net, the nets with filled zones and the copper layer names."""
    import pcbnew as pcb
    board_path = Path(board_path)
    board = pcb.LoadBoard(str(board_path))
    layer_name = {layer: board.GetLayerName(layer) for layer in board.GetEnabledLayers().CuStack()}
    layer_id_of = {name: layer for layer, name in layer_name.items()}
    items, vias = [], []
    for it in board.GetTracks():
        net = it.GetNetname()
        if isinstance(it, pcb.PCB_VIA):
            p = it.GetPosition()
            vias.append(dict(net=net, xy=[int(p.x), int(p.y)], diameter_mm=pcb.ToMM(it.GetWidth(pcb.F_Cu)),
                             layers=[layer_name[l] for l in layer_name if it.IsOnLayer(l)], uuid=it.m_Uuid.AsString()))
            continue
        a, b = it.GetStart(), it.GetEnd()
        rec = dict(net=net, layer=layer_name.get(it.GetLayer(), str(it.GetLayer())), a=[int(a.x), int(a.y)], b=[int(b.x), int(b.y)],
                   width_mm=pcb.ToMM(it.GetWidth()), length_mm=pcb.ToMM(it.GetLength()), uuid=it.m_Uuid.AsString(), kind='seg')
        if isinstance(it, pcb.PCB_ARC):
            m = it.GetMid()
            rec.update(kind='arc', mid=[int(m.x), int(m.y)], radius_mm=pcb.ToMM(it.GetRadius()))
        items.append(rec)
    pads_of = defaultdict(list)
    for pad in board.GetPads():
        if pad.GetNetname():
            pads_of[pad.GetNetname()].append(pad)
    hits = defaultdict(set)
    seen = set()
    for rec in items:
        layer_id = layer_id_of.get(rec['layer'])
        for key in (tuple(rec['a']), tuple(rec['b'])):
            if (rec['layer'], key) in seen:
                continue
            seen.add((rec['layer'], key))
            point = pcb.VECTOR2I(key[0], key[1])
            if any(pad.HitTest(point) and (layer_id is None or pad.IsOnLayer(layer_id)) for pad in pads_of.get(rec['net'], ())):
                hits[rec['net']].add(key)   # a pad hit anchors its own net only, and only where the pad has copper on the item's layer
    zone_nets = sorted({z.GetNetname() for z in board.Zones() if z.GetNetname() and not z.GetIsRuleArea()})
    return dict(board=dict(file=str(board_path), sha256=sha256_of(board_path), pcbnew_version=pcb.GetBuildVersion(),
                           layers=[layer_name[l] for l in layer_name]),
                items=items, vias=vias, pad_hits={net: sorted(list(k) for k in keys) for net, keys in hits.items()}, zone_nets=zone_nets)


# ----- measurement core (plain dicts) -----------------------------------------------------------------------------------
def _quant(key, q):
    return (int(round(key[0] / q)), int(round(key[1] / q)))


def _mm(key, q):
    return (key[0] * q / NM_PER_MM, key[1] * q / NM_PER_MM)


def pre_routed_keys(plan, q=DEFAULT_PARAMS['quantum_nm']):
    """{(net, layer, a, b)} of the plan's ``pre_routed`` tracks (either orientation), quantised like the board items.
    Accepts a plan dict, a wrapper with ``stage1_run_plan`` / ``run_plan`` or a sidecar {'tracks': [...]}."""
    if not plan:
        return set()
    section = plan.get('stage1_run_plan') or plan.get('run_plan') or plan
    tracks = (section.get('pre_routed') or {}).get('tracks') if isinstance(section.get('pre_routed'), dict) else plan.get('tracks', ())
    keys = set()
    for t in tracks or ():
        a = _quant((round(t['a'][0] * NM_PER_MM), round(t['a'][1] * NM_PER_MM)), q)
        b = _quant((round(t['b'][0] * NM_PER_MM), round(t['b'][1] * NM_PER_MM)), q)
        for layer in t.get('layers', [t.get('layer')]):
            keys.add((t['net'], layer, a, b)); keys.add((t['net'], layer, b, a))
    return keys


def _direction_out(edge, q):
    """Unit direction of travel at the end of an oriented edge."""
    a, b = _mm(edge['a'], q), _mm(edge['b'], q)
    if edge['kind'] == 'arc':
        return pg.tangent_at(a, _mm(edge['mid'], q), b, at_start=False)
    d = math.dist(a, b)
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d) if d else (1.0, 0.0)


def _direction_in(edge, q):
    """Unit direction of travel at the start of an oriented edge."""
    a, b = _mm(edge['a'], q), _mm(edge['b'], q)
    if edge['kind'] == 'arc':
        return pg.tangent_at(a, _mm(edge['mid'], q), b, at_start=True)
    d = math.dist(a, b)
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d) if d else (1.0, 0.0)


def _angle(u, v):
    cross = u[0] * v[1] - u[1] * v[0]
    dot = u[0] * v[0] + u[1] * v[1]
    return math.degrees(math.atan2(cross, dot))


def _new_bucket():
    return Counter()


def measure(doc, params=None, plan=None, report=None) -> dict:
    """Metrics of an ``extract_board`` document. ``plan`` (routing plan dict) attributes its ``pre_routed`` tracks; ``report``
    (router report / routing_progress with a ``beautify`` block) supplies the reasons of kept sharp corners by position."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    q = int(p['quantum_nm'])
    pre = pre_routed_keys(plan, q)
    reasons = {}
    for exc in ((report or {}).get('beautify') or {}).get('exceptions', ()) or ():
        reasons[(exc['net'], exc['layer'], _quant((round(exc['xy'][0] * NM_PER_MM), round(exc['xy'][1] * NM_PER_MM)), q))] = exc['reason']
    pad_hits = {net: {tuple(_quant(k, q)) for k in keys} for net, keys in doc.get('pad_hits', {}).items()}
    via_keys = defaultdict(set)
    vias_per_net = Counter()
    for v in doc.get('vias', ()):
        via_keys[v['net']].add(_quant(v['xy'], q)); vias_per_net[v['net']] += 1
    zone_nets = set(doc.get('zone_nets', ()))
    items = []
    for index, rec in enumerate(doc['items']):
        a, b = _quant(rec['a'], q), _quant(rec['b'], q)
        if a == b:
            continue
        attribution = 'pre_routed' if (rec['net'], rec['layer'], a, b) in pre else ('pad_link' if (a in pad_hits.get(rec['net'], ()) or b in pad_hits.get(rec['net'], ())) else 'router')
        items.append(dict(id=rec.get('uuid', index), net=rec['net'], layer=rec['layer'], a=a, b=b, width=rec['width_mm'], kind=rec.get('kind', 'seg'),
                          mid=_quant(rec['mid'], q) if rec.get('kind') == 'arc' else None, length=float(rec.get('length_mm') or 0.0),
                          attribution=attribution))
    fixed = set()   # anchors are keyed by (net, point): a via or pad of another net at the same xy does not split a chain
    for net, keys in via_keys.items():
        fixed |= {(net, k) for k in keys}
    for net, keys in pad_hits.items():
        fixed |= {(net, k) for k in keys}
    chains = pg.chains_from_items(items, fixed)
    totals = Counter(); by_layer = defaultdict(_new_bucket); by_net = defaultdict(_new_bucket); by_attr = defaultdict(_new_bucket)
    min_width = {}
    arc_radii = []
    efficiency_sum = Counter(); efficiency_len = Counter()
    worst_runs, worst_eff, tangency_failures, sharp_corners = [], [], [], []
    bend_reasons = Counter()
    # probe-equivalent figure: joints of exactly two straight items (same net and layer) regardless of anchors / width changes
    degree2 = defaultdict(list)
    for it in items:
        if it['kind'] == 'seg':
            for key in (it['a'], it['b']):
                degree2[(it['net'], it['layer'], key)].append(it)
    for (net, layer, key), pair in degree2.items():
        if len(pair) == 2:
            u = _direction_out(dict(kind='seg', a=pair[0]['b'] if pair[0]['a'] == key else pair[0]['a'], b=key), q)
            v = _direction_in(dict(kind='seg', a=key, b=pair[1]['b'] if pair[1]['a'] == key else pair[1]['a']), q)
            band = pg.classify_bend(_angle(u, v), straight_tol=p['straight_tol_deg'])
            totals['degree2_joints'] += 1
            if band == '90':
                totals['degree2_bends_90'] += 1
    for it in items:
        buckets = (totals, by_layer[it['layer']], by_net[it['net']], by_attr[it['attribution']])
        kind = 'arcs' if it['kind'] == 'arc' else 'segments'
        for bucket in buckets:
            bucket[kind] += 1; bucket['length_mm'] += it['length']
            if it['kind'] == 'arc':
                bucket['arc_length_mm'] += it['length']
            elif it['length'] < p['short_mm']:
                bucket['short_segments'] += 1
        min_width[it['net']] = min(min_width.get(it['net'], it['width']), it['width'])
        if it['kind'] == 'arc':
            try:
                arc_radii.append(pg.arc_from_points(_mm(it['a'], q), _mm(it['mid'], q), _mm(it['b'], q))[1])
            except ValueError:
                pass
    for net, count in vias_per_net.items():
        totals['vias'] += count; by_net[net]['vias'] += count
    for chain in chains:
        net, layer, edges = chain['net'], chain['layer'], chain['edges']
        routed = sum(items[e['index']]['length'] for e in edges)
        pts = [_mm(k, q) for k in chain['points']]
        span = math.dist(pts[0], pts[-1])
        buckets = (totals, by_layer[layer], by_net[net])
        for bucket in buckets:
            bucket['chains'] += 1
        if routed > 0 and span >= p['efficiency_min_span_mm'] and pts[0] != pts[-1]:
            for key in ('__all__', net):
                efficiency_sum[key] += span; efficiency_len[key] += routed
            worst_eff.append((span / routed, dict(net=net, layer=layer, from_mm=[round(v, 3) for v in pts[0]], to_mm=[round(v, 3) for v in pts[-1]],
                                                 span_mm=round(span, 3), routed_mm=round(routed, 3), efficiency=round(span / routed, 3))))
        # joints
        for e, f in zip(edges, edges[1:]):
            u, v = _direction_out(e, q), _direction_in(f, q)
            angle = _angle(u, v)
            attr_e, attr_f = items[e['index']]['attribution'], items[f['index']]['attribution']
            attribution = 'pre_routed' if 'pre_routed' in (attr_e, attr_f) else ('pad_link' if 'pad_link' in (attr_e, attr_f) else 'router')
            jb = (totals, by_layer[layer], by_net[net], by_attr[attribution])
            for bucket in jb:
                bucket['joints'] += 1
            if e['kind'] == 'arc' or f['kind'] == 'arc':
                for bucket in jb:
                    bucket['arc_joints'] += 1
                if abs(angle) > p['tangent_tol_deg']:
                    for bucket in jb:
                        bucket['arc_joints_discontinuous'] += 1
                    tangency_failures.append(dict(net=net, layer=layer, xy_mm=[round(v, 4) for v in _mm(e['b'], q)], error_deg=round(abs(angle), 3)))
                continue
            band = pg.classify_bend(angle, straight_tol=p['straight_tol_deg'])
            if band == 'straight':
                continue
            for bucket in jb:
                bucket['direction_changes'] += 1
                bucket[{'90': 'bends_90', '45': 'bends_45'}.get(band, 'bends_other')] += 1
            if band == '90':
                key = (net, layer, e['b'])
                reason = reasons.get(key) or ('pre_routed' if attribution == 'pre_routed' else 'pad_link' if attribution == 'pad_link' else 'unexplained')
                bend_reasons[reason] += 1
                if len(sharp_corners) < 500:
                    sharp_corners.append(dict(net=net, layer=layer, xy_mm=[round(v, 4) for v in _mm(e['b'], q)], reason=reason, attribution=attribution))
        # short runs over maximal straight sub-chains
        start = 0
        while start < len(edges):
            if edges[start]['kind'] == 'arc':
                start += 1; continue
            end = start
            while end + 1 < len(edges) and edges[end + 1]['kind'] != 'arc':
                end += 1
            sub = pts[start:end + 2]
            runs = pg.short_runs(sub, p['l_short_mm'], min_turn_deg=p['min_turn_deg'])
            for run in runs:
                name = 'stair_runs' if run['kind'] == 'stair' else 'zigzag_runs'
                attribution = Counter(items[e['index']]['attribution'] for e in edges[start + run['start']:start + run['end']]).most_common(1)[0][0]
                for bucket in (totals, by_layer[layer], by_net[net], by_attr[attribution]):
                    bucket[name] += 1; bucket['short_run_segments'] += run['segments']
                worst_runs.append((run['segments'], dict(net=net, layer=layer, kind=run['kind'], segments=run['segments'], length_mm=round(run['length'], 3),
                                                        from_mm=[round(v, 3) for v in sub[run['start']]], to_mm=[round(v, 3) for v in sub[run['end']]])))
            lengths = [math.dist(a, b) for a, b in zip(sub, sub[1:])]
            i = 0
            while i < len(lengths):  # runs of >= 2 consecutive short segments (repeated short segments)
                if lengths[i] >= p['short_mm']:
                    i += 1; continue
                j = i
                while j + 1 < len(lengths) and lengths[j + 1] < p['short_mm']:
                    j += 1
                if j > i:
                    for bucket in (totals, by_layer[layer], by_net[net]):
                        bucket['short_segment_runs'] += 1
                i = j + 1
            start = end + 1

    def finish(bucket, key=None):
        out = {k: (round(bucket[k], 3) if isinstance(bucket[k], float) else int(bucket[k])) for k in TOTAL_KEYS}
        out['bends_per_100mm'] = round(100.0 * (out['bends_90'] + out['bends_45'] + out['bends_other']) / out['length_mm'], 2) if out['length_mm'] else 0.0
        eff_key = '__all__' if key is None else key
        out['efficiency'] = round(efficiency_sum[eff_key] / efficiency_len[eff_key], 4) if efficiency_len[eff_key] else None
        return out

    nets = {}
    for net in sorted(by_net):
        nets[net] = finish(by_net[net], net)
        nets[net]['min_width_mm'] = round(min_width.get(net, 0.0), 4)
        nets[net]['zone_connected'] = net in zone_nets
    worst_runs.sort(key=lambda r: (-r[0], r[1]['net'], r[1]['layer']))
    worst_eff.sort(key=lambda r: (r[0], r[1]['net']))
    arc_radii.sort()
    return dict(
        schema_version=SCHEMA_VERSION, status=STATUS, generated_utc=datetime.now(timezone.utc).isoformat(),
        checker=dict(file='automation/verification/check_routing_quality.py', sha256=sha256_of(__file__) if Path(__file__).is_file() else None),
        board=doc.get('board', {}), parameters=p,
        totals=finish(totals),
        by_layer={layer: finish(by_layer[layer]) for layer in sorted(by_layer)},
        by_attribution={attr: {k: v[k] for k in ('segments', 'arcs', 'length_mm', 'bends_90', 'bends_45', 'bends_other', 'direction_changes', 'stair_runs', 'zigzag_runs', 'short_segments')}
                        for attr, v in ((a, finish(by_attr[a])) for a in sorted(by_attr))},
        nets=nets,
        arcs=dict(count=len(arc_radii), radius_mm=dict(min=round(arc_radii[0], 4), median=round(arc_radii[len(arc_radii) // 2], 4), max=round(arc_radii[-1], 4)) if arc_radii else None,
                  joints=int(totals['arc_joints']), discontinuous=int(totals['arc_joints_discontinuous']), tangency_failures=tangency_failures[:200]),
        sharp_corners=dict(bends_90=int(totals['bends_90']), by_reason=dict(bend_reasons), samples=sharp_corners[:200]),
        worst_cases=dict(short_runs=[r[1] for r in worst_runs[:10]], low_efficiency=[r[1] for r in worst_eff[:10]]),
        zone_connected_nets=sorted(zone_nets & set(nets)),
        notes=['geometry only: no inductance, EMI or current-capacity claim', 'bends are measured at joints of two straight items; arc joints are judged by tangency',
               'chain anchors (not counted as joints): via centres and pad hits of the same net, junctions, width changes; degree2_joints / degree2_bends_90 '
               'count every node where exactly two straight items of one net and layer meet, anchors included (the degree-2 probe figure)',
               "attribution 'pre_routed' needs --plan (pre_routed tracks); 'pad_link' = an item ending inside a pad of its net; everything else is 'router'"],
    )


def link_drc(doc, manifest_path) -> dict:
    """Finding counts of a run_check DRC manifest and whether it was run on the same board bytes."""
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))
    return dict(manifest=str(manifest_path), status=manifest.get('status'), finding_counts=manifest.get('finding_counts'),
                finding_count=manifest.get('finding_count'), tool_exit_code=manifest.get('tool_exit_code'),
                source_sha256=manifest.get('source_sha256'), board_sha256_matches_drc_source=manifest.get('source_sha256') == doc['board'].get('sha256'))


def compare(before, after) -> dict:
    """Deltas (after - before) of the totals, per-layer and per-net metrics of two measurement documents."""
    def delta(a, b):
        out = {}
        for k in TOTAL_KEYS + ('bends_per_100mm',):
            if isinstance(a.get(k), (int, float)) and isinstance(b.get(k), (int, float)):
                d = b[k] - a[k]
                out[k] = dict(before=a[k], after=b[k], delta=round(d, 3), ratio=round(b[k] / a[k], 4) if a[k] else None)
        if a.get('efficiency') is not None and b.get('efficiency') is not None:
            out['efficiency'] = dict(before=a['efficiency'], after=b['efficiency'], delta=round(b['efficiency'] - a['efficiency'], 4))
        return out
    nets = {}
    for net in sorted(set(before['nets']) | set(after['nets'])):
        a, b = before['nets'].get(net), after['nets'].get(net)
        if a and b:
            nets[net] = delta(a, b)
            nets[net]['min_width_mm'] = dict(before=a['min_width_mm'], after=b['min_width_mm'], same=abs(a['min_width_mm'] - b['min_width_mm']) < 1e-6)
        else:
            nets[net] = dict(only_in='before' if a else 'after')
    longer = [n for n, d in nets.items() if 'length_mm' in d and d['length_mm']['delta'] > 1e-3]
    return dict(schema_version=SCHEMA_VERSION, status=STATUS, generated_utc=datetime.now(timezone.utc).isoformat(),
                before=dict(board=before['board'], totals=before['totals']), after=dict(board=after['board'], totals=after['totals']),
                totals=delta(before['totals'], after['totals']),
                by_layer={layer: delta(before['by_layer'][layer], after['by_layer'][layer]) for layer in sorted(set(before['by_layer']) & set(after['by_layer']))},
                nets=nets, nets_longer_after=longer,
                nets_with_more_vias=[n for n, d in nets.items() if 'vias' in d and d['vias']['delta'] > 0],
                nets_with_changed_min_width=[n for n, d in nets.items() if 'min_width_mm' in d and not d['min_width_mm']['same']])


# ----- writers -----------------------------------------------------------------------------------------------------------
def _row(label, t):
    return (f"| {label} | {t['segments']} | {t['arcs']} | {t['vias']} | {t['length_mm']:.1f} | {t['bends_90']} | {t['bends_45']} | {t['bends_other']} | "
            f"{t['stair_runs']} | {t['zigzag_runs']} | {t['short_segments']} | {t['bends_per_100mm']} | {t['efficiency'] if t['efficiency'] is not None else '-'} |")


HEADER = ('| scope | segments | arcs | vias | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs | bends/100 mm | efficiency |\n'
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|')


def markdown(doc) -> str:
    """Markdown summary of a measurement document (or of a compare document)."""
    if 'before' in doc and 'after' in doc:
        lines = [f'# Routing quality comparison', '', f"Status: {doc['status']}", '',
                 f"Before: `{doc['before']['board'].get('file')}` (sha256 {str(doc['before']['board'].get('sha256'))[:12]})",
                 f"After: `{doc['after']['board'].get('file')}` (sha256 {str(doc['after']['board'].get('sha256'))[:12]})", '',
                 '| metric | before | after | delta | ratio |', '|---|---|---|---|---|']
        for k, d in doc['totals'].items():
            lines.append(f"| {k} | {d['before']} | {d['after']} | {d['delta']} | {d.get('ratio', '-')} |")
        lines += ['', f"Nets longer after: {len(doc['nets_longer_after'])} {doc['nets_longer_after'][:20]}",
                  f"Nets with more vias after: {doc['nets_with_more_vias']}", f"Nets whose minimum width changed: {doc['nets_with_changed_min_width']}", '']
        return '\n'.join(lines) + '\n'
    t = doc['totals']
    lines = ['# Routing quality', '', f"Status: {doc['status']}", f"Board: `{doc['board'].get('file')}` (sha256 {str(doc['board'].get('sha256'))[:12]}, pcbnew {doc['board'].get('pcbnew_version')})",
             f"Parameters: {json.dumps(doc['parameters'])}", '', HEADER, _row('board', t)]
    for layer, v in doc['by_layer'].items():
        lines.append(_row(layer, v))
    lines += ['', '## Attribution', '', '| attribution | segments | arcs | length mm | bends 90 | bends 45 | other | stair runs | zigzag runs | short segs |', '|---|---|---|---|---|---|---|---|---|---|']
    for attr, v in doc['by_attribution'].items():
        lines.append(f"| {attr} | {v['segments']} | {v['arcs']} | {v['length_mm']:.1f} | {v['bends_90']} | {v['bends_45']} | {v['bends_other']} | {v['stair_runs']} | {v['zigzag_runs']} | {v['short_segments']} |")
    arcs = doc['arcs']
    lines += ['', '## Arcs', '', f"count {arcs['count']}, joints {arcs['joints']}, discontinuous joints {arcs['discontinuous']}" + (f", radius mm {arcs['radius_mm']}" if arcs['radius_mm'] else ''),
              '', '## Remaining 90-degree bends by reason', '', '| reason | count |', '|---|---|']
    for reason, count in sorted(doc['sharp_corners']['by_reason'].items(), key=lambda kv: -kv[1]):
        lines.append(f'| {reason} | {count} |')
    lines += ['', '## Worst nets (bends 90)', '', HEADER]
    for net, v in sorted(doc['nets'].items(), key=lambda kv: (-kv[1]['bends_90'], kv[0]))[:15]:
        lines.append(_row(net + (' (zone)' if v['zone_connected'] else ''), v))
    if doc.get('drc'):
        d = doc['drc']
        lines += ['', f"DRC: {d.get('status')} findings {d.get('finding_counts')} same board bytes: {d.get('board_sha256_matches_drc_source')} ({d.get('manifest')})"]
    if doc.get('baseline'):
        b = doc['baseline']
        lines += ['', f"Baseline: `{b['file']}`", '', '| metric | baseline | this | delta |', '|---|---|---|---|']
        for k, d in b['deltas'].items():
            lines.append(f"| {k} | {d['before']} | {d['after']} | {d['delta']} |")
    lines += ['', 'Notes: ' + '; '.join(doc['notes']), '']
    return '\n'.join(lines)


def write_outputs(doc, out_dir, label) -> tuple[Path, Path]:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = out_dir / f'routing_quality_{label}.json', out_dir / f'routing_quality_{label}.md'
    json_path.write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')
    md_path.write_text(markdown(doc), encoding='utf-8')
    return json_path, md_path


def run_check(board_path, params=None, plan_path=None, report_path=None, drc_manifest=None, baseline_path=None) -> dict:
    """Extract (pcbnew), measure and link one board; returns the measurement document."""
    doc = extract_board(board_path)
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8')) if plan_path else None
    report = json.loads(Path(report_path).read_text(encoding='utf-8')) if report_path else None
    if report and 'report' in report and 'beautify' not in report:
        report = report['report']
    metrics = measure(doc, params, plan=plan, report=report)
    if drc_manifest:
        metrics['drc'] = link_drc(doc, drc_manifest)
    if baseline_path:
        base = json.loads(Path(baseline_path).read_text(encoding='utf-8'))
        metrics['baseline'] = dict(file=str(baseline_path), sha256=sha256_of(baseline_path), deltas=compare(base, metrics)['totals'])
    return metrics


def kicad_python():
    """Interpreter with pcbnew: AIPE_KICAD_PYTHON, .aipe/local-tools.json, next to kicad-cli, or None."""
    from automation.setup.detect_kicad import find_kicad_cli, read_config
    explicit = os.environ.get('AIPE_KICAD_PYTHON') or read_config().get('kicad_python')
    if explicit and Path(os.path.expandvars(explicit)).is_file():
        return Path(os.path.expandvars(explicit))
    try:
        cli = find_kicad_cli()
    except FileNotFoundError:
        cli = None
    if cli:
        for name in ('python.exe', 'python3', 'python'):
            if (cli.parent / name).is_file():
                return cli.parent / name
    try:
        import pcbnew  # noqa: F401
        return Path(sys.executable)
    except ImportError:
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('board', type=Path, help='KiCad board (.kicad_pcb) - the "before" board in compare mode')
    parser.add_argument('--compare', type=Path, help='second board ("after"): writes routing_quality_<label>_compare.json/.md as well')
    parser.add_argument('--output', type=Path, default=Path('.'), help='directory for routing_quality_<label>.json/.md')
    parser.add_argument('--label', default='board', help='output label')
    parser.add_argument('--plan', type=Path, help='routing plan JSON (pre_routed tracks -> attribution)')
    parser.add_argument('--report', type=Path, help='router report / routing_progress JSON (beautify exceptions -> reasons)')
    parser.add_argument('--drc', type=Path, help='run_check DRC manifest (run.json) to link')
    parser.add_argument('--baseline', type=Path, help='earlier routing_quality JSON for deltas')
    parser.add_argument('--short-mm', type=float, default=DEFAULT_PARAMS['short_mm'], help='short segment threshold (default 0.5)')
    parser.add_argument('--l-short-mm', type=float, default=DEFAULT_PARAMS['l_short_mm'], help='short-run segment threshold (default 1.0)')
    parser.add_argument('--no-reexec', action='store_true', help='internal: do not re-execute under KiCad Python')
    args = parser.parse_args(argv)
    try:
        import pcbnew  # noqa: F401
    except ImportError:
        if args.no_reexec:
            print('pcbnew is not importable in this interpreter', file=sys.stderr)
            return 2
        python = kicad_python()
        if python is None:
            print('No Python interpreter with pcbnew was found (set AIPE_KICAD_PYTHON or .aipe/local-tools.json)', file=sys.stderr)
            return 2
        passthrough = list(sys.argv[1:] if argv is None else argv)
        completed = subprocess.run([str(python), str(Path(__file__).resolve()), *passthrough, '--no-reexec'], cwd=str(ROOT))
        return completed.returncode
    params = dict(short_mm=args.short_mm, l_short_mm=args.l_short_mm)
    metrics = run_check(args.board, params, args.plan, args.report, args.drc, args.baseline)
    json_path, md_path = write_outputs(metrics, args.output, args.label)
    t = metrics['totals']
    print(f"{STATUS}: {t['segments']} segments, {t['arcs']} arcs, {t['vias']} vias, {t['length_mm']:.1f} mm, bends 90/45/other {t['bends_90']}/{t['bends_45']}/{t['bends_other']}, "
          f"stair/zigzag runs {t['stair_runs']}/{t['zigzag_runs']}, efficiency {t['efficiency']} -> {json_path}")
    if args.compare:
        after = run_check(args.compare, params, args.plan, args.report)
        write_outputs(after, args.output, f'{args.label}_after')
        cmp_doc = compare(metrics, after)
        cj, _ = write_outputs(cmp_doc, args.output, f'{args.label}_compare')
        ta = after['totals']
        print(f"after: {ta['segments']} segments, {ta['arcs']} arcs, {ta['vias']} vias, {ta['length_mm']:.1f} mm, bends 90/45/other {ta['bends_90']}/{ta['bends_45']}/{ta['bends_other']}, "
              f"stair/zigzag runs {ta['stair_runs']}/{ta['zigzag_runs']}, efficiency {ta['efficiency']} -> {cj}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
