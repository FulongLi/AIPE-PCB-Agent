"""Readability metrics of KiCad schematic sheets, measured on the written .kicad_sch files.

One definition for every generator version: the V2 release sheets (releases/v2/kicad/<board>) and the V2.1
sheets are parsed with native_schematic.parse and measured alike, so before/after comparisons are honest.

Per sheet: symbols (parts), power_symbols (#PWR / #FLG references), wires, junctions, global_labels,
global_labels_on_pin_stubs (a global label at the end of a wire whose other end is a pin and which is the
pin's only connection - the V2 "stub + label" pattern), name_tags (other global labels), hierarchical_labels,
local_labels, no_connects, sheet_pins, crossings (perpendicular wires of the sheet intersecting strictly
inside both without a junction), text_overlaps (visible symbol fields, labels and texts whose estimated
boxes intersect), off_grid_points (wire ends, junctions, labels, pins not on the 1.27 mm grid), isolated_symbols
(parts with no pin touching a wire end, label, junction, no-connect or another pin), dangling_wire_ends,
wired_pin_share (connected pins that touch a wire end divided by connected pins), four_way_junctions,
paper_fill (hull of symbols, wires, labels and sheets over the drawable area of the paper; texts excluded).
Sheet-pin names count as text (they are drawn inside the sheet symbol) in text_overlaps.

CLI: python -m automation.kicad_tools.schematic_metrics <kicad_dir> [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from automation.kicad_tools.native_schematic import children, parse, pins, placed_pins

GRID = 1.27
TEXT_W = 0.9
PAPER = {'A4': (297.0, 210.0), 'A3': (420.0, 297.0), 'A2': (594.0, 420.0), 'A1': (841.0, 594.0), 'A0': (1189.0, 841.0)}
DRAWABLE_MARGINS = (6.35, 33.02, 12.7, 30.0)      # left, top, right, bottom (project_schematic paper_area)


def _at(node):
    at = children(node, 'at')[0]
    return (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)


def _pt(x, y):
    return (round(x, 4), round(y, 4))


def on_grid(value: float) -> bool:
    return abs(value / GRID - round(value / GRID)) < 1e-3


def _font_size(node, default=1.27) -> float:
    for effects in children(node, 'effects'):
        for font in children(effects, 'font'):
            for size in children(font, 'size'):
                return float(size[1])
    return default


def _justify(node) -> str:
    for effects in children(node, 'effects'):
        for just in children(effects, 'justify'):
            return ' '.join(just[1:])
    return ''


def _hidden(node) -> bool:
    return any(h[1] == 'yes' for h in children(node, 'hide'))


def text_box(x, y, text, size, justify, angle=0.0):
    width = max(1.0, TEXT_W * size * len(text))
    height = size * 1.4
    if int(angle) % 180 == 90:
        width, height = height, width
    if 'left' in justify:
        x0, x1 = x, x + width
    elif 'right' in justify:
        x0, x1 = x - width, x
    else:
        x0, x1 = x - width / 2, x + width / 2
    if 'top' in justify:
        y0, y1 = y, y + height
    elif 'bottom' in justify:
        y0, y1 = y - height, y
    else:
        y0, y1 = y - height / 2, y + height / 2
    return (x0, y0, x1, y1)


def boxes_overlap(a, b, tol=0.2) -> bool:
    return a[0] + tol < b[2] and b[0] + tol < a[2] and a[1] + tol < b[3] and b[1] + tol < a[3]


def measure_sheet(path: Path) -> dict:
    """Metrics of one .kicad_sch file."""
    tree = parse(Path(path).read_text(encoding='utf-8'))
    lib = {}
    for libs in children(tree, 'lib_symbols'):
        for sym in children(libs, 'symbol'):
            lib[sym[1]] = sym
    wires = []
    for w in children(tree, 'wire'):
        pts = children(children(w, 'pts')[0], 'xy')
        wires.append((_pt(float(pts[0][1]), float(pts[0][2])), _pt(float(pts[1][1]), float(pts[1][2]))))
    junctions = {_pt(*_at(j)[:2]) for j in children(tree, 'junction')}
    no_connects = {_pt(*_at(n)[:2]) for n in children(tree, 'no_connect')}
    labels = []
    for kind in ('global_label', 'hierarchical_label', 'label'):
        for l in children(tree, kind):
            x, y, angle = _at(l)
            labels.append(dict(kind=kind, name=l[1], point=_pt(x, y), angle=angle, size=_font_size(l, 1.27), justify=_justify(l)))
    texts = []
    for t in children(tree, 'text'):
        x, y, angle = _at(t)
        texts.append(dict(text=t[1], point=_pt(x, y), size=_font_size(t), justify=_justify(t)))
    sheet_pin_points = set()
    sheet_pin_boxes = []
    sheet_rects = []
    for sh in children(tree, 'sheet'):
        sx, sy, _ = _at(sh)
        size = children(sh, 'size')
        if size:
            sheet_rects.append((sx, sy, sx + float(size[0][1]), sy + float(size[0][2])))
        for pin in children(sh, 'pin'):
            x, y, angle = _at(pin)
            sheet_pin_points.add(_pt(x, y))
            # KiCad draws the name inside the sheet: angle 180 (left edge) reads to the right, angle 0 (right edge) to the left
            justify = _justify(pin) or ('left' if int(angle) == 180 else 'right')
            inset = 1.27 if 'left' in justify else -1.27
            sheet_pin_boxes.append((text_box(x + inset, y, pin[1], _font_size(pin, 1.27), justify), 'sheetpin:' + pin[1]))
    sheet_pins = len(sheet_pin_points)
    # symbols and pins
    symbols, power = 0, 0
    pin_points = defaultdict(list)       # point -> [(ref, connected?)]
    field_boxes = []
    isolated = 0
    sym_entries = []
    for sym in children(tree, 'symbol'):
        lib_id = children(sym, 'lib_id')[0][1]
        x, y, angle = _at(sym)
        mirror = children(sym, 'mirror')
        mirror = mirror[0][1] if mirror else None
        unit = int(children(sym, 'unit')[0][1]) if children(sym, 'unit') else 1
        ref = next(p[2] for p in children(sym, 'property') if p[1] == 'Reference')
        definition = lib.get(lib_id)
        is_power = ref.startswith('#')
        power += is_power
        symbols += not is_power
        points = []
        if definition is not None:
            text = _serialise(definition)
            for number, info in placed_pins(text, unit, x, y, int(angle), mirror).items():
                points.append(info['point'])
                pin_points[info['point']].append((ref, number))
        sym_entries.append(dict(ref=ref, points=points, power=is_power))
        for prop in children(sym, 'property'):
            if _hidden(prop) or prop[2] == '':
                continue
            px, py, pangle = _at(prop)
            field_boxes.append((text_box(px, py, prop[2], _font_size(prop), _justify(prop), (pangle + angle) % 360), f'{ref}:{prop[1]}'))
    wire_ends = defaultdict(int)
    for a, b in wires:
        wire_ends[a] += 1
        wire_ends[b] += 1
    label_points = {l['point'] for l in labels}
    for entry in sym_entries:
        if entry['power'] or not entry['points']:
            continue
        touched = any(p in wire_ends or p in label_points or p in junctions or p in no_connects or len(pin_points[p]) > 1
                      or any(_interior(p, a, b) for a, b in wires) for p in entry['points'])
        isolated += not touched
    # pins by connection: a pin is "wired" when its wire network (wire ends, junctions) reaches another pin,
    # "labelled" when it only reaches a label (the V2 stub-plus-label pattern) or sits directly on one
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in wires:
        union(a, b)
    for j in junctions:
        for a, b in wires:
            if _interior(j, a, b) or j in (a, b):
                union(j, a)
    for p in pin_points:
        find(p)
    pins_per_component = defaultdict(int)
    for p, refs in pin_points.items():
        if p not in no_connects:
            pins_per_component[find(p)] += len(refs)
    connected_pins = [p for p, refs in pin_points.items() for r in refs if not r[0].startswith('#') and p not in no_connects]
    wired = sum(1 for p in connected_pins if pins_per_component[find(p)] >= 2)
    labelled = sum(1 for p in connected_pins if pins_per_component[find(p)] < 2 and (p in label_points or any(
        find(lp) == find(p) for lp in label_points)))
    # stub labels: global label at the end of a wire whose other end is a pin with no other connection
    stub_labels = 0
    for l in labels:
        if l['kind'] != 'global_label':
            continue
        for a, b in wires:
            if l['point'] not in (a, b):
                continue
            other = b if l['point'] == a else a
            if other in pin_points and wire_ends[other] == 1 and wire_ends[l['point']] == 1:
                stub_labels += 1
                break
    # crossings and four-way junctions
    crossings = 0
    hs = [(a, b) for a, b in wires if a[1] == b[1]]
    vs = [(a, b) for a, b in wires if a[0] == b[0]]
    for (a, b) in hs:
        y = a[1]
        x0, x1 = sorted((a[0], b[0]))
        for (c, d) in vs:
            x = c[0]
            y0, y1 = sorted((c[1], d[1]))
            if x0 + 1e-3 < x < x1 - 1e-3 and y0 + 1e-3 < y < y1 - 1e-3 and (x, y) not in junctions:
                crossings += 1
    four_way = sum(1 for p, n in wire_ends.items() if n >= 4)
    # dangling ends
    dangling = 0
    for a, b in wires:
        for p in (a, b):
            if wire_ends[p] > 1 or p in pin_points or p in label_points or p in junctions or p in no_connects or p in sheet_pin_points:
                continue
            if any(_interior(p, c, d) for c, d in wires if (c, d) != (a, b)):
                continue
            dangling += 1
    # text overlaps
    boxes = list(field_boxes) + sheet_pin_boxes
    for l in labels:
        boxes.append((text_box(l['point'][0], l['point'][1], l['name'], l['size'], l['justify'] or ('left' if l['angle'] in (0, 90) else 'right'), l['angle']), l['kind'] + ':' + l['name']))
    for t in texts:
        lines = t['text'].split('\n')
        boxes.append((text_box(t['point'][0], t['point'][1], max(lines, key=len), t['size'], t['justify']), 'text'))
    overlaps = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if boxes_overlap(boxes[i][0], boxes[j][0]):
                overlaps += 1
    off_grid = sum(1 for a, b in wires for p in (a, b) if not (on_grid(p[0]) and on_grid(p[1])))
    off_grid += sum(1 for p in junctions | label_points if not (on_grid(p[0]) and on_grid(p[1])))
    off_grid += sum(1 for p in pin_points if not (on_grid(p[0]) and on_grid(p[1])))
    paper = children(tree, 'paper')
    paper_name = paper[0][1] if paper else None
    fill = None
    if paper_name in PAPER:
        xs = [p[0] for a, b in wires for p in (a, b)] + [p[0] for p in pin_points] + [l['point'][0] for l in labels] + \
             [p[0] for p in junctions | no_connects] + [v for r in sheet_rects for v in (r[0], r[2])] + \
             [v for b, _ in field_boxes for v in (b[0], b[2])]
        ys = [p[1] for a, b in wires for p in (a, b)] + [p[1] for p in pin_points] + [l['point'][1] for l in labels] + \
             [p[1] for p in junctions | no_connects] + [v for r in sheet_rects for v in (r[1], r[3])] + \
             [v for b, _ in field_boxes for v in (b[1], b[3])]
        width, height = PAPER[paper_name]
        left, top, right, bottom = DRAWABLE_MARGINS
        area = (width - left - right) * (height - top - bottom)
        fill = round((max(xs) - min(xs)) * (max(ys) - min(ys)) / area, 3) if xs and ys else 0.0
    return dict(file=Path(path).name, paper=paper_name, paper_fill=fill, symbols=symbols, power_symbols=power, wires=len(wires),
                junctions=len(junctions), global_labels=sum(1 for l in labels if l['kind'] == 'global_label'),
                global_labels_on_pin_stubs=stub_labels,
                name_tags=sum(1 for l in labels if l['kind'] == 'global_label') - stub_labels,
                hierarchical_labels=sum(1 for l in labels if l['kind'] == 'hierarchical_label'),
                local_labels=sum(1 for l in labels if l['kind'] == 'label'), no_connects=len(no_connects), sheet_pins=sheet_pins,
                crossings=crossings, four_way_junctions=four_way, text_overlaps=overlaps, off_grid_points=off_grid,
                isolated_symbols=isolated, dangling_wire_ends=dangling, connected_pins=len(connected_pins), wired_pins=wired,
                labelled_pins=labelled, wired_pin_share=round(wired / len(connected_pins), 4) if connected_pins else None,
                wire_length_mm=round(sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in wires), 2))


def _interior(p, a, b) -> bool:
    if a[0] == b[0]:
        return abs(p[0] - a[0]) < 1e-3 and min(a[1], b[1]) + 1e-3 < p[1] < max(a[1], b[1]) - 1e-3
    if a[1] == b[1]:
        return abs(p[1] - a[1]) < 1e-3 and min(a[0], b[0]) + 1e-3 < p[0] < max(a[0], b[0]) - 1e-3
    return False


def _serialise(node) -> str:
    """Back to s-expression text so native_schematic.pins() can read a parsed lib symbol."""
    if isinstance(node, list):
        return '(' + ' '.join(_serialise(n) for n in node) + ')'
    if isinstance(node, str):
        if re.fullmatch(r'[-+]?\d+(\.\d+)?', node) or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.:*~-]*', node):
            return node
        return json.dumps(node, ensure_ascii=False)
    return str(node)


SUM_KEYS = ('symbols', 'power_symbols', 'wires', 'junctions', 'global_labels', 'global_labels_on_pin_stubs', 'name_tags',
            'hierarchical_labels', 'local_labels', 'no_connects', 'sheet_pins', 'crossings', 'four_way_junctions', 'text_overlaps',
            'off_grid_points', 'isolated_symbols', 'dangling_wire_ends', 'connected_pins', 'wired_pins', 'labelled_pins', 'wire_length_mm')


def measure_project(kicad_dir: Path, root_name: str | None = None) -> dict:
    """Metrics of every .kicad_sch in a project directory plus totals (root sheet included, flagged)."""
    kicad_dir = Path(kicad_dir)
    sheets = []
    for path in sorted(kicad_dir.glob('*.kicad_sch')):
        entry = measure_sheet(path)
        entry['root'] = bool(root_name and path.stem == root_name) or bool(children(parse(path.read_text(encoding='utf-8')), 'sheet'))
        sheets.append(entry)
    totals = {k: round(sum(s[k] for s in sheets), 2) for k in SUM_KEYS}
    totals['wired_pin_share'] = round(totals['wired_pins'] / totals['connected_pins'], 4) if totals['connected_pins'] else None
    totals['sheets'] = len(sheets)
    totals['continuation_sheets'] = sum(1 for s in sheets if re.search(r'_\d+\.kicad_sch$', s['file']))
    totals['papers'] = sorted({s['paper'] for s in sheets if s['paper']})
    return dict(kicad_dir=str(kicad_dir), sheets=sheets, totals=totals)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('kicad_dir', type=Path)
    parser.add_argument('--json', type=Path, help='write the metrics here')
    args = parser.parse_args(argv)
    result = measure_project(args.kicad_dir)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['totals'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
