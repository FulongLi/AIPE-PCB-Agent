"""V2 power-electronics layout metrics checker (data-driven successor of check_power_layout.py).

Measures a routed KiCad board against a JSON "layout spec" and writes ``layout_metrics_<board>.json``
plus a Markdown summary with one row per engineering rule (PE-PCB-001..008, KR-PCB-003, KR-ISO-001,
KR-ISO-002, KR-ISO-004, KR-TH-002). Every reference designator, pad number, net name, region and
threshold comes from the spec; nothing about a particular design is hard-coded, so the same checker
serves the 5 kW SiC power board, its SELV control board, the pipeline-smoke half bridge and the V1 board.

Measured quantities (all straight-line board geometry in mm, never loop inductance, current capacity,
creepage per standard or EMI performance):

1. board outline, area, copper layers / thickness (stackup text), item counts, per-net track length,
   via count and layer set;
2. commutation-loop proxies: MOSFET drain/source pad to nearest HF-capacitor pad, HV ceramic group
   bounding box relative to the device pins, switch-node copper area per layer;
3. gate-loop proxies: driver output pad to gate pad distance, gate-net track length, gate/Kelvin layer
   adjacency and pour overlap, Kelvin-source versus power-source separation (KR-PCB-003: distinct nets,
   no bridging part, no copper contact on any layer, minimum copper distance);
4. isolation: minimum copper-to-copper distance per layer between net-class groups (pads, tracks, vias,
   filled zones) against the spec thresholds, copper-free barrier strips, non-plated slots under barrier
   parts and the around-the-end surface path 2*sqrt((g/2)^2 + e^2);
5. heat-sink envelope: HV copper distance to the heatsink courtyard on the outer layers;
6. decoupling: IC supply pad to nearest decoupling-capacitor pad;
7. sensing: Kelvin-pair track length match and distance of sensing nets/parts from switch-node copper;
8. control section: bounding-box separation from the power stage, DSP bypass distances (V1 ``near_dsp_pin``
   model pattern), ground-zone area, island count and probe points;
9. compactness: component density, courtyard fraction, HV-area utilisation, assembly height, W/dm2, W/L.

Dispositions are "measured - human review required"; where the spec carries a threshold the row states
whether the measurement is within or exceeds that threshold and nothing more. Shapely is used for
polygon distances when importable, otherwise an exact numpy edge/segment implementation (bounding-box
pruned) runs; both are standard-library + numpy apart from the optional shapely.

Run (pcbnew is required; the script re-executes itself under KiCad's bundled Python when needed):
    <kicad-python> automation/verification/check_sic_layout.py <board.kicad_pcb> --spec <spec.json>
        [--model <circuit_<board>.json>] [--output <dir>] [--label <board>] [--backend numpy|shapely]
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from automation.kicad_tools import path_geometry as pg  # noqa: E402

EXAMPLE = ROOT / 'examples/sic-buck-400v-200v-5kw'
CHECKS_DIR = EXAMPLE / 'verification/engineering_checks'
DEFAULT_SPECS = {'power': CHECKS_DIR / 'layout_spec_power.json', 'control': CHECKS_DIR / 'layout_spec_control.json'}
SPEC_SCHEMA_VERSION = 1
METRICS_SCHEMA_VERSION = 1
STATUS = 'measured-human-review-required'
MEASURED = 'measured - human review required'
WITHIN = 'within spec threshold - human review required'
EXCEEDS = 'exceeds spec threshold - human review required'
NOT_MEASURED = 'not measured - spec input missing or reference not found'

# Rule register served by this checker: id -> (requirement, metric family). Thresholds never live here.
RULES = {
    'PE-PCB-001': ('Minimise MOSFET gate loop', 'gate_loops'),
    'PE-PCB-002': ('Place HF DC-link capacitors close to the half bridge', 'commutation'),
    'PE-PCB-003': ('Minimise HF commutation loop', 'commutation'),
    'PE-PCB-004': ('Use Kelvin current sensing', 'sensing'),
    'PE-PCB-005': ('Separate sensitive analog and switch-node paths', 'sensing'),
    'PE-PCB-006': ('Justify high-current copper and via capacity', 'nets'),
    'PE-PCB-007': ('Separate control and switching structures', 'control'),
    'PE-PCB-008': ('Place decoupling adjacent to supply pins', 'decoupling'),
    'KR-PCB-003': ('Never tie the device Kelvin source to the power source in the layout', 'gate_loops'),
    'KR-ISO-001': ('No copper crossing an isolation barrier on any layer', 'isolation'),
    'KR-ISO-002': ('Creepage and clearance per standard for every net-class pair', 'isolation'),
    'KR-ISO-004': ('Slots and cut-outs to extend creepage', 'isolation'),
    'KR-TH-002': ('Rated insulating interface for shared heat sinks (HV copper keep-out at the sink)', 'heatsink'),
}
NOTES = [
    'Straight-line pad distances, track sums and copper areas are geometric proxies; they are not loop inductance, '
    'current-path length, creepage per standard or EMI performance.',
    'Isolation distances are copper-to-copper on each layer (pads, tracks, vias, filled zones); through-air clearance '
    'between layers, component bodies, solder mask and coatings are not evaluated.',
    'Thresholds are those given in the layout spec (taken from the design baseline); no acceptance limit is invented '
    'here. Engineering acceptance of every row remains a human responsibility.',
    'Slot detection relies on non-plated oblong pads or Edge.Cuts graphics inside the barrier part courtyard; the '
    'fabricator must confirm the slot width after tolerance.',
]


# --- pure geometry -----------------------------------------------------------------------------------------------


def bbox_of_points(points) -> tuple:
    """Axis-aligned (x0, y0, x1, y1) of an iterable of (x, y)."""
    arr = np.asarray(list(points), dtype=float).reshape(-1, 2)
    return (float(arr[:, 0].min()), float(arr[:, 1].min()), float(arr[:, 0].max()), float(arr[:, 1].max()))


def bbox_distance(a, b) -> float:
    """Minimum distance between two axis-aligned boxes (0 when they overlap or touch)."""
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return math.hypot(dx, dy)


def bbox_union(boxes) -> tuple | None:
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def bbox_area(box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def inflate(box, margin) -> tuple:
    return (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)


def point_in_bbox(point, box) -> bool:
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def polygon_area(ring) -> float:
    """Shoelace area of a closed ring given as (n, 2) points (positive)."""
    r = np.asarray(ring, dtype=float)
    if len(r) < 3:
        return 0.0
    x, y = r[:, 0], r[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)


def ring_edges(ring) -> np.ndarray:
    """(n, 4) array of closing edges x0, y0, x1, y1 of a ring."""
    r = np.asarray(ring, dtype=float)
    return np.concatenate([r, np.roll(r, -1, axis=0)], axis=1)


def point_in_ring(point, ring) -> bool:
    """Even-odd test of a point against a ring ((n, 2) array)."""
    r = np.asarray(ring, dtype=float)
    x, y = float(point[0]), float(point[1])
    xs, ys = r[:, 0], r[:, 1]
    xn, yn = np.roll(xs, -1), np.roll(ys, -1)
    crosses = (ys > y) != (yn > y)
    with np.errstate(divide='ignore', invalid='ignore'):
        xint = xs + (y - ys) * (xn - xs) / (yn - ys)
    return bool(np.count_nonzero(crosses & (x < xint)) % 2)


def point_in_polygon(point, rings) -> bool:
    """Inside the outline ring and outside every hole ring."""
    if not rings or not point_in_ring(point, rings[0]):
        return False
    return not any(point_in_ring(point, hole) for hole in rings[1:])


def _point_segment_distances(points, segments) -> np.ndarray:
    """points (n, 2), segments (m, 4) -> (n, m) Euclidean distances."""
    P = np.asarray(points, dtype=float).reshape(-1, 2)
    S = np.asarray(segments, dtype=float).reshape(-1, 4)
    A, B = S[:, :2], S[:, 2:]
    AB = B - A
    L2 = (AB ** 2).sum(axis=1)
    AP = P[:, None, :] - A[None, :, :]
    t = (AP * AB[None, :, :]).sum(axis=2)
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(L2[None, :] > 0, t / L2[None, :], 0.0)
    t = np.clip(t, 0.0, 1.0)
    C = A[None, :, :] + t[..., None] * AB[None, :, :]
    D = P[:, None, :] - C
    return np.hypot(D[..., 0], D[..., 1])


def _orient(a, b, c):
    return (b[..., 0] - a[..., 0]) * (c[..., 1] - a[..., 1]) - (b[..., 1] - a[..., 1]) * (c[..., 0] - a[..., 0])


def segments_distance_matrix(E1, E2) -> np.ndarray:
    """(n, 4) x (m, 4) segments -> (n, m) minimum distances; 0 where segments cross."""
    E1 = np.asarray(E1, dtype=float).reshape(-1, 4)
    E2 = np.asarray(E2, dtype=float).reshape(-1, 4)
    d = np.minimum.reduce([_point_segment_distances(E1[:, :2], E2), _point_segment_distances(E1[:, 2:], E2),
                           _point_segment_distances(E2[:, :2], E1).T, _point_segment_distances(E2[:, 2:], E1).T])
    a, b = E1[:, None, :2], E1[:, None, 2:]
    c, e = E2[None, :, :2], E2[None, :, 2:]
    crossing = (_orient(a, b, c) * _orient(a, b, e) < 0) & (_orient(c, e, a) * _orient(c, e, b) < 0)
    d[crossing] = 0.0
    return d


def segment_segment_distance(a0, a1, b0, b1) -> float:
    return float(segments_distance_matrix([[*a0, *a1]], [[*b0, *b1]])[0, 0])


def edges_min_distance(E1, E2, stop_at=0.0, budget=2_000_000) -> float:
    """Minimum distance between two edge sets, chunked so that no matrix exceeds ``budget`` cells."""
    if len(E1) == 0 or len(E2) == 0:
        return math.inf
    if len(E1) < len(E2):
        E1, E2 = E2, E1
    rows = max(1, budget // max(1, len(E2)))
    best = math.inf
    for i in range(0, len(E1), rows):
        best = min(best, float(segments_distance_matrix(E1[i:i + rows], E2).min()))
        if best <= stop_at:
            break
    return best


class Primitive:
    """One piece of copper (or a probe region): polygon with holes, stroked segment or circle, all in mm."""

    __slots__ = ('kind', 'net', 'layer', 'source', 'item', 'ref', 'bbox', 'rings', 'edges', 'a', 'b', 'w', 'c', 'r', 'cache')

    def __init__(self, kind, net, layer, source, item=None, ref=None):
        self.kind, self.net, self.layer, self.source, self.item, self.ref = kind, net, layer, source, item, ref
        self.rings = self.edges = self.a = self.b = self.c = None
        self.w = self.r = 0.0
        self.bbox = None
        self.cache = None

    def area(self) -> float:
        if self.kind == 'poly':
            return polygon_area(self.rings[0]) - sum(polygon_area(h) for h in self.rings[1:])
        if self.kind == 'seg':
            return math.dist(self.a, self.b) * self.w + math.pi * (self.w / 2) ** 2
        return math.pi * self.r ** 2

    def anchor(self):
        return tuple(self.rings[0][0]) if self.kind == 'poly' else (self.a if self.kind == 'seg' else self.c)

    def describe(self) -> dict:
        return dict(item=self.item, source=self.source, net=self.net, layer=self.layer, ref=self.ref)


def make_polygon(rings, net=None, layer=None, source='polygon', item='poly', ref=None) -> Primitive | None:
    rings = [np.asarray(r, dtype=float).reshape(-1, 2) for r in rings]
    rings = [r for r in rings if len(r) >= 3]
    if not rings:
        return None
    p = Primitive('poly', net, layer, source, item, ref)
    p.rings = rings
    p.edges = np.concatenate([ring_edges(r) for r in rings])
    p.bbox = bbox_of_points(rings[0])
    return p


def make_rect(box, net=None, layer=None, source='rect', item='rect', ref=None) -> Primitive:
    x0, y0, x1, y1 = box
    return make_polygon([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]], net, layer, source, item, ref)


def make_segment(a, b, width, net=None, layer=None, source='track', item='track', ref=None) -> Primitive:
    p = Primitive('seg', net, layer, source, item, ref)
    p.a, p.b, p.w = (float(a[0]), float(a[1])), (float(b[0]), float(b[1])), float(width)
    p.edges = np.array([[*p.a, *p.b]], dtype=float)
    p.bbox = inflate(bbox_of_points([p.a, p.b]), p.w / 2)
    return p


def make_circle(centre, radius, net=None, layer=None, source='via', item='via', ref=None) -> Primitive:
    p = Primitive('circle', net, layer, source, item, ref)
    p.c, p.r = (float(centre[0]), float(centre[1])), float(radius)
    p.bbox = (p.c[0] - p.r, p.c[1] - p.r, p.c[0] + p.r, p.c[1] + p.r)
    return p


def shapely_available() -> bool:
    try:
        import shapely  # noqa: F401
        return True
    except ImportError:
        return False


def distance_backend(preferred=None) -> str:
    """'shapely' when importable and not refused, else 'numpy' (exact edge/segment arithmetic)."""
    preferred = preferred or os.environ.get('AIPE_LAYOUT_DISTANCE_BACKEND')
    if preferred == 'numpy':
        return 'numpy'
    if preferred == 'shapely' and not shapely_available():
        raise RuntimeError('shapely backend requested but shapely is not importable')
    return 'shapely' if shapely_available() else 'numpy'


def _shapely_geometry(p: Primitive):
    if p.cache is None:
        from shapely.geometry import LineString, Point, Polygon
        if p.kind == 'poly':
            geom = Polygon(p.rings[0], [r for r in p.rings[1:]])
            if not geom.is_valid:
                geom = geom.buffer(0)
        elif p.kind == 'seg':
            geom = LineString([p.a, p.b]).buffer(p.w / 2) if p.w > 0 else LineString([p.a, p.b])
        else:
            geom = Point(p.c).buffer(p.r)
        p.cache = geom
    return p.cache


def primitive_distance(p: Primitive, q: Primitive, backend='numpy') -> float:
    """Exact minimum copper distance between two primitives (0 when they touch or overlap)."""
    if backend == 'shapely':
        return float(_shapely_geometry(p).distance(_shapely_geometry(q)))
    if p.kind == 'poly' and q.kind == 'poly':
        if point_in_polygon(q.anchor(), p.rings) or point_in_polygon(p.anchor(), q.rings):
            return 0.0
        return edges_min_distance(p.edges, q.edges)
    if 'poly' in (p.kind, q.kind):
        poly, other = (p, q) if p.kind == 'poly' else (q, p)
        if other.kind == 'seg':
            if point_in_polygon(other.a, poly.rings) or point_in_polygon(other.b, poly.rings):
                return 0.0
            return max(0.0, edges_min_distance(poly.edges, other.edges) - other.w / 2)
        if point_in_polygon(other.c, poly.rings):
            return 0.0
        return max(0.0, float(_point_segment_distances([other.c], poly.edges).min()) - other.r)
    if p.kind == 'seg' and q.kind == 'seg':
        return max(0.0, edges_min_distance(p.edges, q.edges) - p.w / 2 - q.w / 2)
    if 'seg' in (p.kind, q.kind):
        seg, circ = (p, q) if p.kind == 'seg' else (q, p)
        return max(0.0, float(_point_segment_distances([circ.c], seg.edges).min()) - seg.w / 2 - circ.r)
    return max(0.0, math.dist(p.c, q.c) - p.r - q.r)


def group_min_distance(A, B, backend='numpy', stop_at=0.0, budget=4_000_000):
    """Minimum distance between two primitive groups with bounding-box pruning.

    Returns (distance, pair) where pair is (a, b) primitives, or (None, None) for an empty group.
    """
    if not A or not B:
        return None, None
    BA = np.array([p.bbox for p in A], dtype=float)
    BB = np.array([q.bbox for q in B], dtype=float)
    best, pair = math.inf, None
    rows = max(1, budget // max(1, len(B)))
    for i0 in range(0, len(A), rows):
        sub = BA[i0:i0 + rows]
        dx = np.maximum(0.0, np.maximum(sub[:, None, 0], BB[None, :, 0]) - np.minimum(sub[:, None, 2], BB[None, :, 2]))
        dy = np.maximum(0.0, np.maximum(sub[:, None, 1], BB[None, :, 1]) - np.minimum(sub[:, None, 3], BB[None, :, 3]))
        lower = np.hypot(dx, dy)
        candidates = np.argwhere(lower < best)
        if candidates.size == 0:
            continue
        values = lower[candidates[:, 0], candidates[:, 1]]
        for k in np.argsort(values, kind='stable'):
            if values[k] >= best:
                break
            i, j = int(candidates[k, 0]) + i0, int(candidates[k, 1])
            d = primitive_distance(A[i], B[j], backend)
            if d < best:
                best, pair = d, (A[i], B[j])
            if best <= stop_at:
                return best, pair
    return best, pair


def slot_surface_path_mm(gap_mm: float, extension_mm: float) -> float:
    """Around-the-end surface path of a through slot: 2*sqrt((g/2)^2 + e^2) (gap g, extension e beyond the pads)."""
    return 2.0 * math.sqrt((gap_mm / 2.0) ** 2 + max(0.0, extension_mm) ** 2)


def slot_extension_for_path_mm(gap_mm: float, required_path_mm: float) -> float:
    """Slot extension beyond the pad edges needed for the required surface path (0 when the gap alone suffices)."""
    half = required_path_mm / 2.0
    if half <= gap_mm / 2.0:
        return 0.0
    return math.sqrt(half ** 2 - (gap_mm / 2.0) ** 2)


# --- spec, model and net classes --------------------------------------------------------------------------------


def load_json(path) -> object:
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def load_spec(path) -> dict:
    """Layout spec JSON; validates the schema version and fills the structural defaults."""
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f'layout spec must be a JSON object: {path}')
    if int(data.get('schema_version', SPEC_SCHEMA_VERSION)) != SPEC_SCHEMA_VERSION:
        raise ValueError(f"unsupported layout spec schema_version {data.get('schema_version')} (expected {SPEC_SCHEMA_VERSION})")
    spec = dict(data)
    spec.setdefault('board', 'board')
    spec.setdefault('title', f"{spec['board']} layout spec")
    spec.setdefault('net_classes', {})
    spec.setdefault('class_groups', {})
    iso = spec.setdefault('isolation', {})
    iso.setdefault('pairs', [])
    iso.setdefault('barrier_keepouts', [])
    iso.setdefault('barrier_parts', [])
    for key in ('gate_loops', 'decoupling'):
        spec.setdefault(key, [])
    for key in ('commutation', 'heatsink', 'sensing', 'control', 'compactness', 'expected'):
        spec.setdefault(key, {})
    for name, patterns in spec['net_classes'].items():
        if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
            raise ValueError(f'net class {name!r} must list glob patterns')
    return spec


def load_model(path) -> list[dict]:
    """Shared-format part list (V1 circuit.json list, or an object with a 'parts' list)."""
    data = load_json(path)
    if isinstance(data, dict):
        data = data.get('parts', [])
    if not isinstance(data, list):
        raise ValueError(f'model must be a list of parts or an object with a parts list: {path}')
    return [p for p in data if isinstance(p, dict) and 'ref' in p]


def net_class(net: str, patterns: dict) -> str | None:
    """First class (in spec order) whose glob patterns match the net name."""
    for name, globs in patterns.items():
        if any(fnmatch.fnmatchcase(net, g) for g in globs):
            return name
    return None


def classes_of_groups(groups, spec) -> set:
    """Expand group names (class_groups keys) and plain class names into a set of class names."""
    classes = set()
    for g in groups:
        classes.update(spec['class_groups'].get(g, [g] if g in spec['net_classes'] else []))
    return classes


def nets_of_groups(nets, groups, spec) -> list[str]:
    classes = classes_of_groups(groups, spec)
    return sorted(n for n in nets if net_class(n, spec['net_classes']) in classes)


def layer_kind(layer: str, outer: list[str]) -> str:
    return 'outer' if layer in outer else 'inner'


def threshold_for(min_mm, kind: str):
    """Threshold for a layer kind from {'all': x} / {'outer': x, 'inner': y} / a bare number."""
    if min_mm is None:
        return None
    if isinstance(min_mm, (int, float)):
        return float(min_mm)
    value = min_mm.get(kind, min_mm.get('all'))
    return None if value is None else float(value)


def row(rule, metric, measured, threshold=None, passed=None, note=''):
    """One rule-table row; the disposition follows the spec threshold only."""
    if measured is None:
        disposition = NOT_MEASURED
    elif threshold is None or passed is None:
        disposition = MEASURED
    else:
        disposition = WITHIN if passed else EXCEEDS
    return dict(rule=rule, requirement=RULES.get(rule, ('', ''))[0], metric=metric, measured=measured,
                threshold=threshold, disposition=disposition, note=note)


def fmt(value, digits=3):
    if value is None:
        return 'n/a'
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if isinstance(value, float):
        if math.isinf(value):
            return 'inf'
        return f'{value:.{digits}f}'
    if isinstance(value, (list, tuple)):
        return ', '.join(fmt(v, digits) for v in value)
    if isinstance(value, dict):
        return '; '.join(f'{k}={fmt(v, digits)}' for k, v in value.items())
    return str(value)


def rounded(value, digits=3):
    if isinstance(value, float):
        return None if math.isinf(value) or math.isnan(value) else round(value, digits)
    if isinstance(value, (list, tuple)):
        return [rounded(v, digits) for v in value]
    if isinstance(value, dict):
        return {k: rounded(v, digits) for k, v in value.items()}
    return value


# --- board extraction (pcbnew) ----------------------------------------------------------------------------------


def polyset_rings(poly, mm) -> list:
    """SHAPE_POLY_SET -> list of polygons, each [outline, hole, hole, ...] as lists of (x, y) in mm."""
    polygons = []
    for i in range(poly.OutlineCount()):
        outline = [mm(p) for p in poly.Outline(i).CPoints()]
        if len(outline) < 3:
            continue
        holes = []
        for h in range(poly.HoleCount(i)):
            points = [mm(p) for p in poly.Hole(i, h).CPoints()]
            if len(points) >= 3:
                holes.append(points)
        polygons.append([outline] + holes)
    return polygons


def balanced_block(text: str, start: int) -> str:
    """The s-expression starting at ``start`` ('(' expected) up to its matching ')'."""
    depth = 0
    in_string = False
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '"' and (i == 0 or text[i - 1] != '\\'):
            in_string = not in_string
        if in_string:
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:]


def parse_stackup(text: str) -> list[dict]:
    """Stackup layers from the board file text (pcbnew exposes no Python accessor): layer, type, thickness."""
    match = re.search(r'\(stackup\b', text)
    if not match:
        return []
    block = balanced_block(text, match.start())
    items = []
    for lm in re.finditer(r'\(layer\s+"([^"]+)"\s*\(type\s+"([^"]+)"\)(.*?)(?=\(layer\s+"|\(copper_finish|\Z)', block, re.S):
        name, kind, rest = lm.groups()
        record = dict(layer=name, type=kind)
        thickness = re.search(r'\(thickness\s+([0-9.]+)', rest)
        if thickness:
            record['thickness_mm'] = float(thickness.group(1))
            if kind == 'copper':
                record['thickness_um'] = round(float(thickness.group(1)) * 1000.0, 1)
        items.append(record)
    return items


def shape_record(shape, pcb, mm, owner=None) -> dict | None:
    """Edge.Cuts graphic as a kind + bounding box (slot/cut-out detection does not need exact arcs)."""
    kind = shape.GetShape()
    width = mm(shape.GetWidth())
    try:
        if kind == pcb.SHAPE_T_SEGMENT:
            name, points = 'segment', [mm(shape.GetStart()), mm(shape.GetEnd())]
        elif kind == pcb.SHAPE_T_RECT:
            try:
                points = [mm(c) for c in shape.GetRectCorners()]
            except Exception:
                points = [mm(shape.GetStart()), mm(shape.GetEnd())]
            name = 'rect'
        elif kind == pcb.SHAPE_T_CIRCLE:
            c, r = mm(shape.GetCenter()), mm(shape.GetRadius())
            name, points = 'circle', [(c[0] - r, c[1] - r), (c[0] + r, c[1] + r)]
        elif kind == pcb.SHAPE_T_ARC:
            name, points = 'arc', [mm(shape.GetStart()), mm(shape.GetMid()), mm(shape.GetEnd())]
        elif kind == pcb.SHAPE_T_POLY:
            name = 'poly'
            points = [pt for poly in polyset_rings(shape.GetPolyShape(), mm) for pt in poly[0]]
        else:
            return None
    except Exception:  # unusual shape: skip rather than abort the whole measurement
        return None
    if not points:
        return None
    box = inflate(bbox_of_points(points), width / 2.0)
    return dict(kind=name, owner=owner, bbox=tuple(round(v, 4) for v in box), width=round(width, 4))


class BoardData:
    """Plain-Python snapshot of a pcbnew board in mm; the metrics never touch pcbnew objects."""

    def __init__(self):
        self.path = self.sha256 = self.pcbnew_version = None
        self.title = ''
        self.layers: list[str] = []
        self.outline_bbox = None
        self.outline_area = None
        self.outline_polygons: list = []
        self.thickness_mm = None
        self.stackup: list = []
        self.copper_um: dict = {}
        self.footprints: dict = {}
        self.tracks: list = []
        self.vias: list = []
        self.zones: list = []
        self.edge_shapes: list = []
        self._pads = None
        self._prims = None

    # ----- lookups ----------------------------------------------------------------------------------------------
    def nets(self) -> set:
        names = {p['net'] for f in self.footprints.values() for p in f['pads']}
        names |= {t['net'] for t in self.tracks} | {v['net'] for v in self.vias} | {z['net'] for z in self.zones if not z['rule_area']}
        names.discard('')
        return names

    def pad_lookup(self) -> dict:
        if self._pads is None:
            table = {}
            for ref, fp in self.footprints.items():
                for pad in fp['pads']:
                    table.setdefault((ref, pad['number']), []).append(pad)
            self._pads = table
        return self._pads

    def pad(self, ref, number) -> dict | None:
        pads = self.pad_lookup().get((str(ref), str(number)))
        return pads[0] if pads else None

    def pads_of(self, ref) -> list:
        fp = self.footprints.get(ref)
        return list(fp['pads']) if fp else []

    def layer_index(self, name: str) -> int:
        return self.layers.index(name)

    def outer_layers(self) -> list[str]:
        return [self.layers[0], self.layers[-1]] if len(self.layers) > 1 else list(self.layers)

    def courtyard_polygons(self, ref) -> list:
        fp = self.footprints.get(ref)
        if not fp:
            return []
        return [poly for polys in fp['courtyards'].values() for poly in polys]

    def courtyard_bbox(self, ref) -> tuple | None:
        fp = self.footprints.get(ref)
        if not fp:
            return None
        polys = self.courtyard_polygons(ref)
        if polys:
            return bbox_union(bbox_of_points(poly[0]) for poly in polys)
        return fp['bbox']

    def courtyard_area(self, ref, side=None) -> float:
        fp = self.footprints.get(ref)
        if not fp:
            return 0.0
        total = 0.0
        for s, polys in fp['courtyards'].items():
            if side and s != side:
                continue
            total += sum(polygon_area(poly[0]) - sum(polygon_area(h) for h in poly[1:]) for poly in polys)
        if not fp['courtyards'] and (side is None or side == fp['side']):
            total += bbox_area(fp['bbox'])
        return total

    # ----- copper geometry --------------------------------------------------------------------------------------
    def copper_primitives(self) -> dict:
        """Layer name -> list of copper Primitives (pad polygons, stroked tracks, via circles, zone fills)."""
        if self._prims is not None:
            return self._prims
        prims = {name: [] for name in self.layers}
        for ref, fp in self.footprints.items():
            for pad in fp['pads']:
                for layer, polygons in pad['polys'].items():
                    for rings in polygons:
                        p = make_polygon(rings, pad['net'], layer, f"pad {ref}.{pad['number']}", 'pad', ref)
                        if p is not None:
                            prims.setdefault(layer, []).append(p)
        for t in self.tracks:
            # arcs are densified to 0.05 mm chords (two chords a-mid-b under-estimate the copper by the sagitta, up to 0.06 mm at r 0.8 mm)
            points = pg.sample_arc(t['a'], t['mid'], t['b'], 0.05) if t.get('arc') else [t['a'], t['b']]
            for a, b in zip(points, points[1:]):
                prims.setdefault(t['layer'], []).append(make_segment(a, b, t['width'], t['net'], t['layer'], 'track', 'track'))
        for v in self.vias:
            for layer in v['layers']:
                prims.setdefault(layer, []).append(make_circle(v['xy'], v['diameter'] / 2.0, v['net'], layer, 'via', 'via'))
        for z in self.zones:
            for layer, fill in z['fills'].items():
                for rings in fill['polygons']:
                    p = make_polygon(rings, z['net'], layer, f"zone {z['name'] or z['net']}", 'zone')
                    if p is not None:
                        prims.setdefault(layer, []).append(p)
        self._prims = prims
        return prims

    def primitives(self, nets=None, layers=None, items=None, exclude_refs=()) -> list:
        nets = None if nets is None else set(nets)
        selected = []
        for layer, prims in self.copper_primitives().items():
            if layers is not None and layer not in layers:
                continue
            for p in prims:
                if nets is not None and p.net not in nets:
                    continue
                if items is not None and p.item not in items:
                    continue
                if p.ref in exclude_refs:
                    continue
                selected.append(p)
        return selected

    def net_layers(self, net, routed_only=False) -> list[str]:
        """Layers carrying copper of ``net``; ``routed_only`` counts tracks, vias and zones but not pads (THT pads span every layer)."""
        items = ('track', 'via', 'zone') if routed_only else None
        layers = [layer for layer, prims in self.copper_primitives().items()
                  if any(p.net == net and (items is None or p.item in items) for p in prims)]
        if routed_only and not layers:
            layers = self.net_layers(net)
        return layers


def extract_board(path) -> BoardData:
    """Load the board with pcbnew and snapshot everything the metrics need (mm)."""
    import pcbnew as pcb
    path = Path(path)
    board = pcb.LoadBoard(str(path))
    mm = pcb.ToMM
    data = BoardData()
    data.path = str(path)
    data.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    data.pcbnew_version = pcb.GetBuildVersion()
    data.title = board.GetTitleBlock().GetTitle()
    enabled = list(board.GetEnabledLayers().CuStack())
    names = {layer: board.GetLayerName(layer) for layer in enabled}
    data.layers = [names[layer] for layer in enabled]
    outline = pcb.SHAPE_POLY_SET()
    try:
        ok = board.GetBoardPolygonOutlines(outline, True)
    except TypeError:
        ok = board.GetBoardPolygonOutlines(outline)
    box = board.GetBoardEdgesBoundingBox()
    data.outline_bbox = (mm(box.GetX()), mm(box.GetY()), mm(box.GetRight()), mm(box.GetBottom()))
    if ok and outline.OutlineCount():
        data.outline_polygons = polyset_rings(outline, mm)
        data.outline_area = outline.Area() / 1e12
    else:
        data.outline_area = bbox_area(data.outline_bbox)
    data.thickness_mm = mm(board.GetDesignSettings().GetBoardThickness())
    data.stackup = parse_stackup(path.read_text(encoding='utf-8', errors='replace'))
    data.copper_um = {s['layer']: s.get('thickness_um') for s in data.stackup if s['type'] == 'copper'}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        courtyards = {}
        for side, layer in (('F', pcb.F_CrtYd), ('B', pcb.B_CrtYd)):
            try:
                polys = polyset_rings(fp.GetCourtyard(layer), mm)
            except Exception:
                polys = []
            if polys:
                courtyards[side] = polys
        try:
            fbox = fp.GetBoundingBox(False, False)
        except TypeError:
            fbox = fp.GetBoundingBox()
        pads = []
        for pad in fp.Pads():
            attribute = int(pad.GetAttribute())
            npth = attribute == pcb.PAD_ATTRIB_NPTH
            on = [layer for layer in enabled if pad.IsOnLayer(layer)]
            polys = {}
            if not npth:
                for layer in on:
                    rings = polyset_rings(pad.GetEffectivePolygon(layer), mm)
                    if rings:
                        polys[names[layer]] = rings
            drill = mm(pad.GetDrillSize())
            hole_bbox = None
            if max(drill) > 0:
                try:  # board-oriented hole outline (the drill size itself is unrotated: a 90 deg footprint swaps its slot axes)
                    hb = pad.GetEffectiveHoleShape().BBox()
                    hole_bbox = (mm(hb.GetX()), mm(hb.GetY()), mm(hb.GetRight()), mm(hb.GetBottom()))
                except Exception:
                    hole_bbox = None
            pads.append(dict(number=pad.GetNumber(), net=pad.GetNetname(), xy=mm(pad.GetPosition()), layers=[names[layer] for layer in on],
                             attribute=attribute, npth=npth, drill=drill, hole_bbox=hole_bbox, size=mm(pad.GetSize()), polys=polys,
                             oblong=bool(pad.GetDrillShape() == pcb.PAD_DRILL_SHAPE_OBLONG and max(drill) > 0 and drill[0] != drill[1])))
        for graphic in fp.GraphicalItems():
            if isinstance(graphic, pcb.PCB_SHAPE) and graphic.GetLayer() == pcb.Edge_Cuts:
                record = shape_record(graphic, pcb, mm, ref)
                if record:
                    data.edge_shapes.append(record)
        data.footprints[ref] = dict(ref=ref, value=fp.GetValue(), footprint=str(fp.GetFPID().GetLibItemName()),
                                    library=str(fp.GetFPID().GetLibNickname()), side='B' if fp.IsFlipped() else 'F',
                                    xy=mm(fp.GetPosition()), angle=float(fp.GetOrientationDegrees()),
                                    bbox=(mm(fbox.GetX()), mm(fbox.GetY()), mm(fbox.GetRight()), mm(fbox.GetBottom())),
                                    courtyards=courtyards, pads=pads)
    for item in board.GetTracks():
        if isinstance(item, pcb.PCB_VIA):
            on_ids = [layer for layer in item.GetLayerSet().CuStack() if layer in enabled]
            if not on_ids:
                continue
            try:
                diameter = mm(item.GetWidth(on_ids[0]))
            except TypeError:
                diameter = mm(item.GetWidth(item.GetLayer()))  # KiCad 10: PCB_VIA.GetWidth needs a layer (else a blocking wx assert dialog)
            data.vias.append(dict(net=item.GetNetname(), xy=mm(item.GetPosition()), diameter=diameter,
                                  drill=mm(item.GetDrillValue()), layers=[names[layer] for layer in on_ids]))
        else:
            record = dict(net=item.GetNetname(), layer=names.get(item.GetLayer(), board.GetLayerName(item.GetLayer())),
                          a=mm(item.GetStart()), b=mm(item.GetEnd()), width=mm(item.GetWidth()), length=mm(item.GetLength()), arc=False)
            if isinstance(item, pcb.PCB_ARC):
                record.update(arc=True, mid=mm(item.GetMid()))
            data.tracks.append(record)
    for zone in board.Zones():
        on_ids = [layer for layer in zone.GetLayerSet().CuStack() if layer in enabled]
        rule = bool(zone.GetIsRuleArea())
        outline_polys = polyset_rings(zone.Outline(), mm)
        fills = {}
        if not rule:
            for layer in on_ids:
                filled = zone.GetFilledPolysList(layer)
                fills[names[layer]] = dict(polygons=polyset_rings(filled, mm), area=filled.Area() / 1e12, islands=int(filled.OutlineCount()))
        keepout = None
        if rule:
            keepout = {}
            for key, getter in (('copper', 'GetDoNotAllowZoneFills'), ('copper', 'GetDoNotAllowCopperPour'), ('tracks', 'GetDoNotAllowTracks'),
                                ('vias', 'GetDoNotAllowVias'), ('pads', 'GetDoNotAllowPads'), ('footprints', 'GetDoNotAllowFootprints')):
                if hasattr(zone, getter) and key not in keepout:
                    keepout[key] = bool(getattr(zone, getter)())
        data.zones.append(dict(name=zone.GetZoneName(), net=zone.GetNetname(), layers=[names[layer] for layer in on_ids], rule_area=rule,
                               priority=int(zone.GetAssignedPriority()), outline=outline_polys,
                               bbox=bbox_of_points(outline_polys[0][0]) if outline_polys else None, fills=fills, keepout=keepout))
    for drawing in board.GetDrawings():
        if isinstance(drawing, pcb.PCB_SHAPE) and drawing.GetLayer() == pcb.Edge_Cuts:
            record = shape_record(drawing, pcb, mm, None)
            if record:
                data.edge_shapes.append(record)
    return data


# --- metrics ----------------------------------------------------------------------------------------------------


def pad_point(data: BoardData, ref, number):
    pad = data.pad(ref, number)
    return None if pad is None else pad['xy']


def nearest_pad(point, pads):
    """(distance, pad) of the pad centre nearest to ``point``; (None, None) without candidates."""
    best = (None, None)
    for pad in pads:
        d = math.dist(point, pad['xy'])
        if best[0] is None or d < best[0]:
            best = (d, pad)
    return best


def board_summary(data: BoardData, spec: dict) -> dict:
    box = bbox_union(bbox_of_points(poly[0]) for poly in data.outline_polygons) or data.outline_bbox
    x0, y0, x1, y1 = box
    expected = spec.get('expected', {})
    return dict(file=data.path, sha256=data.sha256, title=data.title, pcbnew_version=data.pcbnew_version,
                outline_mm=[x1 - x0, y1 - y0], outline_bbox_mm=list(box), edge_cuts_bbox_mm=list(data.outline_bbox), outline_area_mm2=data.outline_area,
                outline_cutouts=sum(len(poly) - 1 for poly in data.outline_polygons), copper_layers=len(data.layers), layers=list(data.layers),
                outer_layers=data.outer_layers(), thickness_mm=data.thickness_mm, copper_um=data.copper_um, stackup=data.stackup,
                footprints=len(data.footprints), tracks=len(data.tracks), vias=len(data.vias),
                zones=sum(not z['rule_area'] for z in data.zones), rule_areas=sum(z['rule_area'] for z in data.zones),
                unfilled_zones=[dict(name=z['name'], net=z['net'], layers=z['layers']) for z in data.zones
                                if not z['rule_area'] and all(f['area'] <= 0 for f in z['fills'].values())],
                nets=len(data.nets()), expected=expected)


def net_summary(data: BoardData, spec: dict) -> dict:
    """Per net: class, track length, track/via/pad counts, layers with copper, zone fill area per layer."""
    nets = {}
    for net in sorted(data.nets()):
        nets[net] = dict(cls=net_class(net, spec['net_classes']), track_mm=0.0, tracks=0, vias=0, pads=0, layers=set(), zone_area_mm2={}, zone_islands={})
    for t in data.tracks:
        rec = nets.get(t['net'])
        if rec:
            rec['track_mm'] += t['length']
            rec['tracks'] += 1
            rec['layers'].add(t['layer'])
    for v in data.vias:
        rec = nets.get(v['net'])
        if rec:
            rec['vias'] += 1
            rec['layers'].update(v['layers'])
    for fp in data.footprints.values():
        for pad in fp['pads']:
            rec = nets.get(pad['net'])
            if rec:
                rec['pads'] += 1
                rec['layers'].update(pad['polys'])
    for z in data.zones:
        rec = nets.get(z['net'])
        if rec:
            for layer, fill in z['fills'].items():
                rec['zone_area_mm2'][layer] = rec['zone_area_mm2'].get(layer, 0.0) + fill['area']
                rec['zone_islands'][layer] = rec['zone_islands'].get(layer, 0) + fill['islands']
                if fill['area'] > 0:
                    rec['layers'].add(layer)
    for rec in nets.values():
        rec['layers'] = sorted(rec['layers'], key=lambda n: data.layer_index(n) if n in data.layers else 99)
    return nets


def copper_rows(nets: dict, spec: dict) -> list:
    """PE-PCB-006 rows: HV-group net copper (zone area per layer, via count) against spec copper references."""
    copper = spec.get('copper', {})
    hv_nets = [n for n in copper['nets'] if n in nets] if copper.get('nets') else (nets_of_groups(nets, copper.get('groups', ['HV']), spec) if spec['net_classes'] else [])
    rows = []
    vias_required = copper.get('vias_per_transition_min')
    for net in hv_nets:
        rec = nets[net]
        measured = dict(zone_area_mm2={k: round(v, 1) for k, v in rec['zone_area_mm2'].items()}, vias=rec['vias'], track_mm=round(rec['track_mm'], 1))
        passed = None if vias_required is None else rec['vias'] >= vias_required
        rows.append(row('PE-PCB-006', f'{net} copper (zone area per layer, via count, track length)', measured,
                        None if vias_required is None else f'>= {vias_required} vias per net', passed,
                        'Copper width/current capacity needs the IPC-2221 rationale in the baseline; areas are fill areas, not conductor widths.'))
    if not rows:
        rows.append(row('PE-PCB-006', 'HV net copper', None, note='no HV net classes in the spec'))
    return rows


def commutation_metrics(data: BoardData, spec: dict) -> dict:
    """Drain/source pad to nearest HF-capacitor pad, HV ceramic group box versus device pins, SW copper area."""
    cfg = spec.get('commutation') or {}
    result = dict(mosfets=[], hf_capacitors=[], hf_group_bbox_mm=None, sw_copper_mm2=None, rows=[])
    if not cfg:
        result['rows'].append(row('PE-PCB-002', 'HF capacitor to device pin distance', None, note='no commutation section in the spec'))
        result['rows'].append(row('PE-PCB-003', 'commutation loop proxies', None, note='no commutation section in the spec'))
        return result
    cap_nets = set(cfg.get('hf_capacitor_nets', [n for n in (cfg.get('vin_net'), cfg.get('pgnd_net')) if n]))
    cap_refs = list(cfg.get('hf_capacitor_refs', []))
    for pattern in cfg.get('hf_capacitor_ref_patterns', []):
        cap_refs += [r for r in data.footprints if fnmatch.fnmatchcase(r, pattern) and r not in cap_refs]
    cap_pads = [dict(p, ref=ref) for ref in cap_refs for p in data.pads_of(ref) if p['net'] in cap_nets]
    result['hf_capacitors'] = [dict(ref=ref, found=ref in data.footprints, pads=[(p['number'], p['net']) for p in data.pads_of(ref) if p['net'] in cap_nets])
                               for ref in cap_refs]
    if cap_pads:
        result['hf_group_bbox_mm'] = list(bbox_union([bbox_of_points(ring) for p in cap_pads for polys in p['polys'].values() for ring in [polys[0][0]]]
                                                     or [bbox_of_points([p['xy'] for p in cap_pads])]))
    limits = cfg.get('pin_to_capacitor_mm_max')
    row1 = row2 = None
    if isinstance(limits, (list, tuple)) and limits:
        row1, row2 = float(limits[0]), float(limits[-1])
    elif isinstance(limits, (int, float)):
        row1 = row2 = float(limits)
    for m in cfg.get('mosfets', []):
        ref = m['ref']
        record = dict(ref=ref, role=m.get('role'), found=ref in data.footprints, pins={})
        for role in ('drain', 'source'):
            number = m.get(f'{role}_pad')
            pad = data.pad(ref, number) if number is not None else None
            if pad is None:
                record['pins'][role] = None
                continue
            same = [p for p in cap_pads if p['net'] == pad['net']]
            d_same, p_same = nearest_pad(pad['xy'], same)
            d_any, p_any = nearest_pad(pad['xy'], cap_pads)
            entry = dict(pad=number, net=pad['net'], xy=list(pad['xy']),
                         nearest_same_net_mm=d_same, nearest_same_net_pad=None if p_same is None else f"{p_same['ref']}.{p_same['number']}",
                         nearest_any_mm=d_any, nearest_any_pad=None if p_any is None else f"{p_any['ref']}.{p_any['number']}",
                         capacitors_within_row1=None if row1 is None else sum(math.dist(pad['xy'], p['xy']) <= row1 for p in same),
                         capacitors_within_row2=None if row2 is None else sum(math.dist(pad['xy'], p['xy']) <= row2 for p in same))
            if result['hf_group_bbox_mm']:
                entry['distance_to_hf_group_bbox_mm'] = bbox_distance((pad['xy'][0], pad['xy'][1], pad['xy'][0], pad['xy'][1]), result['hf_group_bbox_mm'])
            record['pins'][role] = entry
            if d_same is not None:
                result['rows'].append(row('PE-PCB-002', f'{ref} {role} pad {number} ({pad["net"]}) to nearest HF capacitor pad of the same net',
                                          round(d_same, 3), None if row2 is None else f'<= {row2} mm (row 2; row 1 <= {row1} mm)',
                                          None if row2 is None else d_same <= row2,
                                          None if p_same is None else f"nearest {p_same['ref']}.{p_same['number']}"))
            elif cap_pads:
                result['rows'].append(row('PE-PCB-002', f'{ref} {role} pad {number} ({pad["net"]}) to nearest HF capacitor pad (any named net)',
                                          None if d_any is None else round(d_any, 3), None, None, 'pad net is not a capacitor net (switch node)'))
        result['mosfets'].append(record)
        if not record['found']:
            result['rows'].append(row('PE-PCB-002', f'{ref} HF capacitor distance', None, note='MOSFET reference not on the board'))
    sw = cfg.get('sw_net')
    if sw:
        per_layer = {}
        for p in data.primitives(nets=[sw]):
            per_layer.setdefault(p.layer, dict(zone_mm2=0.0, pad_mm2=0.0, track_mm2=0.0, via_mm2=0.0))
            key = {'zone': 'zone_mm2', 'pad': 'pad_mm2', 'track': 'track_mm2', 'via': 'via_mm2'}.get(p.item, 'track_mm2')
            per_layer[p.layer][key] += p.area()
        for layer, rec in per_layer.items():
            rec['total_mm2'] = sum(rec.values())
        result['sw_copper_mm2'] = per_layer
        total = sum(rec['total_mm2'] for rec in per_layer.values())
        result['rows'].append(row('PE-PCB-003', f'{sw} copper area, all layers (mm2; per layer in JSON)', round(total, 1), None, None,
                                  'switch-node copper is a dv/dt coupling and radiation proxy; the baseline asks for the minimum that carries the current'))
    if result['hf_group_bbox_mm']:
        b = result['hf_group_bbox_mm']
        result['rows'].append(row('PE-PCB-003', 'HV ceramic group bounding box (x0, y0, x1, y1 mm) and pin distances (JSON)',
                                  [round(v, 2) for v in b], None, None, 'bounding box of the HF capacitor pads on the named nets'))
    elif cap_refs:
        result['rows'].append(row('PE-PCB-003', 'HV ceramic group bounding box', None, note='no HF capacitor pads on the named nets found'))
    return result


def gate_loop_metrics(data: BoardData, spec: dict) -> dict:
    """Driver output to gate pad, gate-net length, gate/Kelvin layer adjacency and KR-PCB-003 separation.

    KR-PCB-003 is evaluated from the board itself: the two nets must be distinct, no part other than the
    device may sit as a two-terminal element between the nets (netlist tie), and the minimum copper distance between the two nets
    on every layer must be greater than zero (a zero means touching or overlapping copper, which pcbnew's
    per-net connectivity clusters would never report).
    """
    result = dict(loops=[], rows=[])
    loops = spec.get('gate_loops') or []
    if not loops:
        result['rows'].append(row('PE-PCB-001', 'driver output to gate pad distance', None, note='no gate_loops in the spec'))
        result['rows'].append(row('KR-PCB-003', 'Kelvin-source versus power-source separation', None, note='no gate_loops in the spec'))
        return result
    nets_all = data.nets()
    for loop in loops:
        mosfet, driver = loop.get('mosfet'), loop.get('driver_ref')
        gate_nets = [n for n in (loop.get('gate_nets') or [loop.get('gate_net')]) if n]
        kelvin, source_net = loop.get('kelvin_net'), loop.get('power_source_net')
        record = dict(mosfet=mosfet, driver=driver, gate_nets=gate_nets, kelvin_net=kelvin, power_source_net=source_net)
        gate_pad = data.pad(mosfet, loop.get('gate_pad', '1')) if mosfet else None
        outputs = [data.pad(driver, n) for n in loop.get('driver_output_pads', [])] if driver else []
        outputs = [p for p in outputs if p is not None]
        limit = loop.get('driver_to_gate_mm_max')
        if gate_pad and outputs:
            d, pad = nearest_pad(gate_pad['xy'], outputs)
            record['driver_output_to_gate_pad_mm'] = d
            record['driver_output_pad'] = pad['number']
            result['rows'].append(row('PE-PCB-001', f'{driver} output pad {pad["number"]} to {mosfet} gate pad {gate_pad["number"]}', round(d, 3),
                                      None if limit is None else f'<= {limit} mm', None if limit is None else d <= float(limit)))
        else:
            record['driver_output_to_gate_pad_mm'] = None
            result['rows'].append(row('PE-PCB-001', f'{driver} output to {mosfet} gate pad', None, note='driver/gate pad not found'))
        returns = [data.pad(driver, n) for n in loop.get('driver_return_pads', [])] if driver else []
        kelvin_pad = data.pad(mosfet, loop.get('kelvin_pad', '4')) if mosfet else None
        if kelvin_pad and any(returns):
            d, pad = nearest_pad(kelvin_pad['xy'], [p for p in returns if p])
            record['driver_return_to_kelvin_pad_mm'] = d
        gate_track = sum(t['length'] for t in data.tracks if t['net'] in gate_nets)
        gate_vias = sum(v['net'] in gate_nets for v in data.vias)
        gate_layers = sorted({layer for n in gate_nets for layer in data.net_layers(n, routed_only=True)}, key=data.layer_index)
        kelvin_layers = sorted(data.net_layers(kelvin, routed_only=True), key=data.layer_index) if kelvin else []
        record.update(gate_track_mm=gate_track, gate_vias=gate_vias, gate_layers=gate_layers, kelvin_layers=kelvin_layers)
        adjacent = sorted({(g, k) for g in gate_layers for k in kelvin_layers if abs(data.layer_index(g) - data.layer_index(k)) == 1})
        record['adjacent_layer_pairs'] = [list(p) for p in adjacent]
        record['gate_kelvin_on_adjacent_layers'] = bool(adjacent)
        # fraction of gate track length whose midpoint lies over a Kelvin-net zone fill on an adjacent layer
        kelvin_zones = [(layer, rings) for z in data.zones if z['net'] == kelvin for layer, fill in z['fills'].items() for rings in fill['polygons']]
        covered = 0.0
        for t in data.tracks:
            if t['net'] not in gate_nets or t['length'] <= 0:
                continue
            mid = ((t['a'][0] + t['b'][0]) / 2, (t['a'][1] + t['b'][1]) / 2)
            if any(abs(data.layer_index(layer) - data.layer_index(t['layer'])) == 1 and point_in_polygon(mid, rings) for layer, rings in kelvin_zones):
                covered += t['length']
        record['gate_track_over_kelvin_pour_fraction'] = (covered / gate_track) if gate_track > 0 else None
        kelvin_text = f'Kelvin {kelvin} layers {kelvin_layers}' if kelvin else 'no Kelvin-source net'
        result['rows'].append(row('PE-PCB-001', f'{"/".join(gate_nets)} track length (mm), layers {gate_layers}, {kelvin_text}',
                                  dict(track_mm=round(gate_track, 2), adjacent=bool(adjacent), over_kelvin_pour=rounded(record['gate_track_over_kelvin_pour_fraction'])),
                                  None, None, 'KR-PCB-001 adjacency proxy: a gate/Kelvin layer pair with stack index difference 1'))
        # KR-PCB-003
        if kelvin and source_net:
            distinct = kelvin != source_net and kelvin in nets_all and source_net in nets_all
            ks_prims = data.primitives(nets=[kelvin])
            src_prims = data.primitives(nets=[source_net])
            per_layer = {}
            for layer in data.layers:
                d, pair = group_min_distance([p for p in ks_prims if p.layer == layer], [p for p in src_prims if p.layer == layer],
                                             backend=spec.get('_backend', 'numpy'))
                if d is not None:
                    per_layer[layer] = dict(distance_mm=d, between=[pair[0].source, pair[1].source] if pair else None)
            minimum = min((v['distance_mm'] for v in per_layer.values()), default=None)
            contact = None if minimum is None else minimum <= 0.0
            # a PCB-level tie is a two-terminal element (0 ohm link, jumper, DNP RC) sitting between the two nets;
            # an IC with a pin on each net (driver COM on KS, primary GND on the power return) is not a tie
            bridging = sorted(ref for ref, fp in data.footprints.items()
                              if ref != mosfet and {p['net'] for p in fp['pads'] if p['net']} == {kelvin, source_net})
            record['kelvin_separation'] = dict(distinct_nets=distinct, min_copper_distance_mm=minimum, per_layer=per_layer,
                                               copper_contact=contact, bridging_parts=bridging)
            ok = distinct and not contact and not bridging
            result['rows'].append(row('KR-PCB-003', f'{kelvin} versus {source_net}: distinct nets, no bridging part, no copper contact, minimum copper distance (mm)',
                                      dict(distinct=distinct, bridging=bridging, contact=contact, min_mm=rounded(minimum)),
                                      'distinct nets, no part other than the device on both nets, copper distance > 0 on every layer',
                                      ok, 'hard constraint; the device itself is the only permitted connection'))
        else:
            result['rows'].append(row('KR-PCB-003', f'{mosfet} Kelvin separation', None, note='kelvin_net/power_source_net missing'))
        result['loops'].append(record)
    return result


def isolation_metrics(data: BoardData, spec: dict) -> dict:
    """Class-pair copper distances per layer, barrier keep-out copper, slots and surface paths."""
    cfg = spec['isolation']
    backend = spec.get('_backend', 'numpy')
    outer = spec.get('layers', {}).get('outer') or data.outer_layers()
    nets = data.nets()
    result = dict(pairs=[], barrier_keepouts=[], barrier_parts=[], rows=[])
    for pair in cfg.get('pairs', []):
        nets_a = nets_of_groups(nets, pair.get('a', []), spec)
        nets_b = nets_of_groups(nets, pair.get('b', []), spec)
        exclude = tuple(pair.get('exclude_within_courtyards', []))
        boxes = [data.courtyard_bbox(r) for r in exclude if data.courtyard_bbox(r)]
        record = dict(name=pair.get('name'), nets_a=nets_a, nets_b=nets_b, per_layer={}, min_mm=None, min_layer=None, excluded_refs=list(exclude))
        for layer in data.layers:
            A = [p for p in data.primitives(nets=nets_a, layers=[layer]) if not _excluded(p, exclude, boxes)]
            B = [p for p in data.primitives(nets=nets_b, layers=[layer]) if not _excluded(p, exclude, boxes)]
            d, pr = group_min_distance(A, B, backend=backend)
            kind = layer_kind(layer, outer)
            threshold = threshold_for(pair.get('min_mm'), kind)
            entry = dict(kind=kind, items_a=len(A), items_b=len(B), distance_mm=d, threshold_mm=threshold,
                         within=None if (d is None or threshold is None) else d >= threshold,
                         between=None if not pr else [pr[0].describe(), pr[1].describe()])
            record['per_layer'][layer] = entry
            if d is not None and (record['min_mm'] is None or d < record['min_mm']):
                record['min_mm'], record['min_layer'] = d, layer
        measured_layers = {l: e for l, e in record['per_layer'].items() if e['distance_mm'] is not None}
        thresholds = {e['threshold_mm'] for e in measured_layers.values()}
        passed = None if not measured_layers or any(e['within'] is None for e in measured_layers.values()) else all(e['within'] for e in measured_layers.values())
        record['within_threshold'] = passed
        result['pairs'].append(record)
        for rule in pair.get('rules', ['KR-ISO-002']):
            result['rows'].append(row(rule, f"{pair.get('name')}: minimum copper distance per layer (mm)",
                                      None if not measured_layers else {l: round(e['distance_mm'], 3) for l, e in measured_layers.items()},
                                      None if not thresholds or thresholds == {None} else fmt(pair.get('min_mm')) + ' mm', passed,
                                      'no items of one group on any layer' if not measured_layers else ''))
    for keep in cfg.get('barrier_keepouts', []):
        region, origin = _barrier_region(data, keep)
        record = dict(name=keep.get('name'), region=origin, bbox_mm=None if region is None else list(region.bbox), per_layer={}, copper_free=None)
        if region is not None:
            for layer in data.layers:
                hits = [p for p in data.copper_primitives().get(layer, []) if bbox_distance(p.bbox, region.bbox) == 0 and primitive_distance(p, region, backend) == 0]
                record['per_layer'][layer] = dict(copper_items=len(hits), nets=sorted({p.net for p in hits}), sources=sorted({p.source for p in hits})[:10])
            record['copper_free'] = all(e['copper_items'] == 0 for e in record['per_layer'].values())
        result['barrier_keepouts'].append(record)
        result['rows'].append(row('KR-ISO-001', f"{keep.get('name')} barrier strip copper items per layer",
                                  None if region is None else {l: e['copper_items'] for l, e in record['per_layer'].items()},
                                  None if region is None else 'no copper on any layer', record['copper_free'],
                                  'region not found (rect_mm or rule area name)' if region is None else f"region {origin}"))
    for part in cfg.get('barrier_parts', []):
        result['barrier_parts'].append(_barrier_part(data, spec, part, result['rows']))
    if not cfg.get('pairs'):
        result['rows'].append(row('KR-ISO-002', 'net-class pair copper distances', None, note='no isolation pairs in the spec'))
    if not cfg.get('barrier_keepouts'):
        result['rows'].append(row('KR-ISO-001', 'barrier strip copper check', None, note='no barrier_keepouts in the spec'))
    if not cfg.get('barrier_parts'):
        result['rows'].append(row('KR-ISO-004', 'slots under barrier parts', None, note='no barrier_parts in the spec'))
    return result


def _excluded(p: Primitive, refs, boxes) -> bool:
    if p.ref in refs:
        return True
    return any(p.bbox[0] >= b[0] and p.bbox[1] >= b[1] and p.bbox[2] <= b[2] and p.bbox[3] <= b[3] for b in boxes)


def _barrier_region(data: BoardData, keep: dict):
    if keep.get('rect_mm'):
        return make_rect(keep['rect_mm'], source=keep.get('name'), item='region'), 'rect_mm'
    name = keep.get('zone_name')
    for z in data.zones:
        if name and z['name'] == name and z['outline']:
            return make_polygon(z['outline'][0], source=name, item='region'), f'rule area {name!r}'
    return None, None


def _barrier_part(data: BoardData, spec: dict, part: dict, rows: list) -> dict:
    """Land gap, slot detection and around-the-end surface path for one barrier component."""
    ref = part['ref']
    backend = spec.get('_backend', 'numpy')
    record = dict(ref=ref, found=ref in data.footprints, land_gap_mm=None, slots=[], best_slot=None, surface_path_mm=None)
    if ref not in data.footprints:
        rows.append(row('KR-ISO-004', f'{ref} slot / surface path', None, note='barrier part not on the board'))
        return record
    pads = data.pads_of(ref)
    selv_classes = classes_of_groups(part.get('selv_groups', ['CTRL_SELV']), spec)
    if part.get('hv_pads') or part.get('selv_pads'):
        hv = [p for p in pads if p['number'] in set(map(str, part.get('hv_pads', [])))]
        selv = [p for p in pads if p['number'] in set(map(str, part.get('selv_pads', [])))]
    else:
        selv = [p for p in pads if net_class(p['net'], spec['net_classes']) in selv_classes]
        hv = [p for p in pads if p['polys'] and p not in selv and net_class(p['net'], spec['net_classes']) is not None]
    record.update(hv_pads=[p['number'] for p in hv], selv_pads=[p['number'] for p in selv])
    prims_hv = [make_polygon(rings, p['net'], layer, f"pad {ref}.{p['number']}", 'pad', ref) for p in hv for layer, polys in p['polys'].items() for rings in polys]
    prims_selv = [make_polygon(rings, p['net'], layer, f"pad {ref}.{p['number']}", 'pad', ref) for p in selv for layer, polys in p['polys'].items() for rings in polys]
    gap, _ = group_min_distance([p for p in prims_hv if p], [p for p in prims_selv if p], backend=backend)
    record['land_gap_mm'] = gap
    court = data.courtyard_bbox(ref)
    margin = float(part.get('slot_search_margin_mm', 2.0))
    search = inflate(court, margin) if court else None
    all_pads = hv + selv if (hv or selv) else pads
    pad_boxes = [bbox_of_points(ring) for p in all_pads for polys in p['polys'].values() for ring in [polys[0][0]]]
    row_box = bbox_union(pad_boxes) or court
    if row_box is None:
        rows.append(row('KR-ISO-004', f'{ref} slot / surface path', None, note='no pad geometry'))
        return record
    if hv and selv:  # the gap runs between the two centroids; the pad rows run along the other axis
        c_hv = (sum(p['xy'][0] for p in hv) / len(hv), sum(p['xy'][1] for p in hv) / len(hv))
        c_selv = (sum(p['xy'][0] for p in selv) / len(selv), sum(p['xy'][1] for p in selv) / len(selv))
        axis = 1 if abs(c_hv[0] - c_selv[0]) >= abs(c_hv[1] - c_selv[1]) else 0
    else:
        axis = 0 if (row_box[2] - row_box[0]) >= (row_box[3] - row_box[1]) else 1  # pad rows run along the longer extent
    record['row_axis'] = 'x' if axis == 0 else 'y'
    candidates = []
    for fp_ref, fp in data.footprints.items():
        for p in fp['pads']:
            if p['npth'] and max(p['drill']) > 0 and search and point_in_bbox(p['xy'], search):
                if p.get('hole_bbox'):
                    box = tuple(p['hole_bbox'])  # oriented with the footprint (a rotated slot swaps its axes)
                else:
                    half = (p['drill'][0] / 2, p['drill'][1] / 2)
                    box = (p['xy'][0] - half[0], p['xy'][1] - half[1], p['xy'][0] + half[0], p['xy'][1] + half[1])
                candidates.append(dict(kind='npth pad', owner=fp_ref, bbox=box, width=min(box[2] - box[0], box[3] - box[1]), oblong=p['oblong']))
    for shape in data.edge_shapes:
        if search and bbox_distance(shape['bbox'], search) == 0:
            candidates.append(dict(kind=f"edge {shape['kind']}", owner=shape['owner'], bbox=shape['bbox'],
                                   width=min(shape['bbox'][2] - shape['bbox'][0], shape['bbox'][3] - shape['bbox'][1]), oblong=True))
    required = part.get('required_surface_path_mm')
    ext_min = part.get('slot_extension_min_mm')
    width_min = part.get('slot_width_min_mm')
    for c in candidates:
        b = c['bbox']
        ext_low = row_box[axis] - b[axis]
        ext_high = b[axis + 2] - row_box[axis + 2]
        extension = min(ext_low, ext_high)
        slot_width = min(b[2] - b[0], b[3] - b[1])
        slot_length = max(b[2] - b[0], b[3] - b[1])
        perpendicular_centre = (b[1 - axis] + b[3 - axis]) / 2
        between = row_box[1 - axis] <= perpendicular_centre <= row_box[3 - axis]
        slot = dict(kind=c['kind'], owner=c['owner'], bbox_mm=[round(v, 3) for v in b], width_mm=slot_width, length_mm=slot_length,
                    extension_mm=extension, extension_each_end_mm=[ext_low, ext_high], between_pad_rows=between,
                    surface_path_mm=None if gap is None else slot_surface_path_mm(gap, extension))
        record['slots'].append(slot)
    valid = [s for s in record['slots'] if s['between_pad_rows']]
    if valid:
        best = max(valid, key=lambda s: s['extension_mm'])
        record['best_slot'] = best
        record['surface_path_mm'] = best['surface_path_mm']
    elif gap is not None:
        record['surface_path_mm'] = gap  # no slot: the surface path is the land gap itself
    if gap is not None and required is not None:
        record['required_extension_mm'] = slot_extension_for_path_mm(gap, float(required))
    rows.append(row('KR-ISO-004', f'{ref} land gap g (mm), slot extension e (mm), around-the-end surface path 2*sqrt((g/2)^2+e^2) (mm)',
                    dict(g=rounded(gap), e=None if not record['best_slot'] else rounded(record['best_slot']['extension_mm']), path=rounded(record['surface_path_mm']),
                         slots=len(valid)),
                    None if required is None else f'path >= {required} mm' + ('' if ext_min is None else f', e >= {ext_min} mm') + ('' if width_min is None else f', width >= {width_min} mm'),
                    None if required is None or record['surface_path_mm'] is None else (
                        record['surface_path_mm'] >= float(required) and (ext_min is None or (record['best_slot'] is not None and record['best_slot']['extension_mm'] >= float(ext_min)))
                        and (width_min is None or (record['best_slot'] is not None and record['best_slot']['width_mm'] >= float(width_min)))),
                    'no slot detected under the part' if not valid else f"{best['kind']} {best['owner'] or ''}".strip()))
    return record


def heatsink_metrics(data: BoardData, spec: dict) -> dict:
    cfg = spec.get('heatsink') or {}
    result = dict(ref=cfg.get('ref'), rows=[])
    ref = cfg.get('ref')
    if not ref or ref not in data.footprints:
        result['rows'].append(row('KR-TH-002', 'HV copper distance to the heatsink envelope', None, note='heatsink ref missing or not on the board'))
        return result
    backend = spec.get('_backend', 'numpy')
    polys = data.courtyard_polygons(ref)
    regions = [make_polygon(poly, source=f'{ref} courtyard', item='region') for poly in polys] or [make_rect(data.footprints[ref]['bbox'], source=f'{ref} bbox', item='region')]
    regions = [r for r in regions if r]
    keepout = cfg.get('keepout_mm')
    hv_nets = nets_of_groups(data.nets(), cfg.get('groups', ['HV']), spec)
    outer = spec.get('layers', {}).get('outer') or data.outer_layers()
    per_layer = {}
    for layer in (cfg.get('layers') or outer):
        prims = data.primitives(nets=hv_nets, layers=[layer])
        d, pair = group_min_distance(prims, regions, backend=backend)
        within = None if keepout is None else sum(1 for p in prims if bbox_distance(p.bbox, regions[0].bbox) < float(keepout)
                                                   and min(primitive_distance(p, r, backend) for r in regions) < float(keepout))
        per_layer[layer] = dict(hv_items=len(prims), min_distance_mm=d, nearest=None if not pair else pair[0].describe(), items_within_keepout=within)
    result.update(courtyard_bbox_mm=list(data.courtyard_bbox(ref)), hv_nets=hv_nets, per_layer=per_layer, keepout_mm=keepout,
                  npth_holes=[list(p['xy']) for p in data.pads_of(ref) if p['npth']])
    minimum = min((e['min_distance_mm'] for e in per_layer.values() if e['min_distance_mm'] is not None), default=None)
    result['rows'].append(row('KR-TH-002', f'{ref}: minimum HV copper distance to the heatsink courtyard on the outer layers (mm)',
                              None if minimum is None else {l: rounded(e['min_distance_mm']) for l, e in per_layer.items()},
                              None if keepout is None else f'>= {keepout} mm', None if keepout is None or minimum is None else minimum >= float(keepout),
                              'baseline: >= 5 mm HV copper keep-out around the PE-bonded sink; pad/clip insulation itself is a human-review item'))
    return result


def decoupling_metrics(data: BoardData, spec: dict) -> dict:
    result = dict(ics=[], rows=[])
    entries = spec.get('decoupling') or []
    if not entries:
        result['rows'].append(row('PE-PCB-008', 'supply pad to decoupling capacitor distance', None, note='no decoupling entries in the spec'))
        return result
    for entry in entries:
        ic = entry.get('ic')
        record = dict(ic=ic, found=ic in data.footprints, pads=[])
        if not record['found']:
            result['rows'].append(row('PE-PCB-008', f'{ic} decoupling', None, note='IC not on the board'))
            result['ics'].append(record)
            continue
        cap_refs = list(entry.get('capacitor_refs', []))
        for pattern in entry.get('capacitor_ref_patterns', []):
            cap_refs += [r for r in data.footprints if fnmatch.fnmatchcase(r, pattern) and r not in cap_refs]
        limit = entry.get('max_mm')
        numbers = [str(n) for n in entry.get('supply_pads', [])]
        if not numbers and entry.get('supply_nets'):
            numbers = [p['number'] for p in data.pads_of(ic) if p['net'] in set(entry['supply_nets'])]
        worst = None
        for number in numbers:
            pad = data.pad(ic, number)
            if pad is None:
                record['pads'].append(dict(pad=number, found=False))
                continue
            if cap_refs:
                cands = [dict(p, ref=r) for r in cap_refs for p in data.pads_of(r)]
            else:
                prefix = entry.get('capacitor_prefix', 'C')
                cands = [dict(p, ref=r) for r, fp in data.footprints.items() if r.startswith(prefix) and r != ic for p in fp['pads']]
            same = [c for c in cands if c['net'] == pad['net']]
            d, cap = nearest_pad(pad['xy'], same or cands)
            record['pads'].append(dict(pad=number, net=pad['net'], distance_mm=d, capacitor=None if cap is None else f"{cap['ref']}.{cap['number']}",
                                       same_net=bool(same)))
            if d is not None and (worst is None or d > worst):
                worst = d
        record['max_distance_mm'] = worst
        result['ics'].append(record)
        result['rows'].append(row('PE-PCB-008', f'{ic} supply pads {numbers} to nearest decoupling capacitor pad, maximum (mm)', rounded(worst),
                                  None if limit is None else f'<= {limit} mm', None if limit is None or worst is None else worst <= float(limit),
                                  '; '.join(f"{p['pad']}->{p.get('capacitor')} {fmt(p.get('distance_mm'), 2)}" for p in record['pads'] if p.get('capacitor'))))
    return result


def sensing_metrics(data: BoardData, spec: dict) -> dict:
    cfg = spec.get('sensing') or {}
    result = dict(kelvin_pairs=[], parts=[], rows=[])
    backend = spec.get('_backend', 'numpy')
    sw = cfg.get('sw_net') or (spec.get('commutation') or {}).get('sw_net')
    sw_prims = data.primitives(nets=[sw]) if sw else []
    if not cfg.get('kelvin_pairs'):
        result['rows'].append(row('PE-PCB-004', 'Kelvin sense pair length match', None, note='no sensing.kelvin_pairs in the spec'))
    for pair in cfg.get('kelvin_pairs', []):
        nets = pair.get('nets', [])
        lengths = {n: sum(t['length'] for t in data.tracks if t['net'] == n) for n in nets}
        vias = {n: sum(v['net'] == n for v in data.vias) for n in nets}
        layers = {n: data.net_layers(n) for n in nets}
        mismatch = (max(lengths.values()) - min(lengths.values())) if len(lengths) >= 2 else None
        prims = data.primitives(nets=nets)
        d, pr = group_min_distance(prims, sw_prims, backend=backend) if sw_prims else (None, None)
        limit = pair.get('match_mm_max')
        record = dict(name=pair.get('name'), nets=nets, track_mm=lengths, vias=vias, layers=layers, mismatch_mm=mismatch, min_distance_to_sw_mm=d,
                      present=all(n in data.nets() for n in nets))
        result['kelvin_pairs'].append(record)
        result['rows'].append(row('PE-PCB-004', f"{pair.get('name') or '/'.join(nets)} track lengths (mm) and mismatch", dict(**rounded(lengths), mismatch=rounded(mismatch)) if record['present'] else None,
                                  None if limit is None else f'mismatch <= {limit} mm', None if limit is None or mismatch is None else mismatch <= float(limit),
                                  '' if record['present'] else 'nets not on the board'))
        if sw:
            result['rows'].append(row('PE-PCB-005', f"{pair.get('name') or '/'.join(nets)} minimum copper distance to {sw} (mm, any layer)", rounded(d),
                                      None if pair.get('sw_distance_mm_min') is None else f">= {pair['sw_distance_mm_min']} mm",
                                      None if pair.get('sw_distance_mm_min') is None or d is None else d >= float(pair['sw_distance_mm_min'])))
    for ref in cfg.get('parts', []):
        if ref not in data.footprints:
            result['parts'].append(dict(ref=ref, found=False))
            result['rows'].append(row('PE-PCB-005', f'{ref} distance to {sw} copper', None, note='part not on the board'))
            continue
        prims = [make_polygon(rings, p['net'], layer, f"pad {ref}.{p['number']}", 'pad', ref) for p in data.pads_of(ref) for layer, polys in p['polys'].items() for rings in polys]
        d, pr = group_min_distance([p for p in prims if p], sw_prims, backend=backend) if sw_prims else (None, None)
        limit = cfg.get('part_sw_distance_mm_min')
        result['parts'].append(dict(ref=ref, found=True, min_distance_to_sw_mm=d, nearest=None if not pr else pr[1].describe()))
        result['rows'].append(row('PE-PCB-005', f'{ref} pads: minimum copper distance to {sw} (mm, any layer)', rounded(d),
                                  None if limit is None else f'>= {limit} mm', None if limit is None or d is None else d >= float(limit)))
    if not cfg.get('parts') and not cfg.get('kelvin_pairs'):
        result['rows'].append(row('PE-PCB-005', 'sensing versus switch node distance', None, note='no sensing section in the spec'))
    return result


def control_metrics(data: BoardData, spec: dict, model=None) -> dict:
    cfg = spec.get('control') or {}
    result = dict(rows=[])
    if not cfg:
        result['rows'].append(row('PE-PCB-007', 'control section versus power stage separation', None, note='no control section in the spec'))
        return result
    nets = data.nets()

    excluded_refs = set(cfg.get('exclude_refs', []))  # parts shared by both sections (mezzanine connector, DSP) distort the bbox proxy

    def refs_for(key_refs, key_groups, exclude_groups=()):
        refs = set(cfg.get(key_refs, []))
        for pattern in cfg.get(key_refs + '_patterns', []):
            refs.update(r for r in data.footprints if fnmatch.fnmatchcase(r, pattern))
        groups = cfg.get(key_groups)
        if groups:
            wanted = set(nets_of_groups(nets, groups, spec))
            banned = set(nets_of_groups(nets, exclude_groups, spec)) if exclude_groups else set()
            for ref, fp in data.footprints.items():
                pad_nets = {p['net'] for p in fp['pads'] if p['net']}
                if pad_nets & wanted and not pad_nets & banned:
                    refs.add(ref)
        return sorted(r for r in refs if r in data.footprints and r not in excluded_refs)

    control_refs = refs_for('section_refs', 'section_groups', cfg.get('power_groups', ['HV', 'DRV', 'DESAT']))
    power_refs = refs_for('power_refs', 'power_groups')
    control_box = bbox_union(data.courtyard_bbox(r) for r in control_refs)
    power_box = bbox_union(data.courtyard_bbox(r) for r in power_refs)
    separation = None if control_box is None or power_box is None else bbox_distance(control_box, power_box)
    overlap = None
    if control_box and power_box and separation == 0:
        ix = (max(control_box[0], power_box[0]), max(control_box[1], power_box[1]), min(control_box[2], power_box[2]), min(control_box[3], power_box[3]))
        overlap = bbox_area(ix)
    result.update(control_refs=control_refs, power_refs=power_refs, control_bbox_mm=control_box, power_bbox_mm=power_box,
                  bbox_separation_mm=separation, bbox_overlap_mm2=overlap, excluded_refs=sorted(excluded_refs))
    limit = cfg.get('separation_mm_min')
    result['rows'].append(row('PE-PCB-007', f'control section ({len(control_refs)} parts) to power stage ({len(power_refs)} parts) bounding-box distance (mm)',
                              rounded(separation), None if limit is None else f'>= {limit} mm', None if limit is None or separation is None else separation >= float(limit),
                              f'overlap {overlap:.0f} mm2' if overlap else ''))
    # DSP bypass (V1 near_dsp_pin pattern) from the model
    dsp = cfg.get('dsp_ref')
    key = cfg.get('model_near_pin_key', 'near_dsp_pin')
    bypass = []
    if model and dsp and dsp in data.footprints:
        for part in model:
            if key not in part or part.get('board', spec['board']) not in (spec['board'], None):
                continue
            supply = data.pad(dsp, part[key])
            cap = data.pad(part['ref'], part.get('near_pad', '1'))
            if supply and cap:
                bypass.append(dict(capacitor=part['ref'], dsp_pin=str(part[key]), distance_mm=math.dist(supply['xy'], cap['xy'])))
        worst = max((b['distance_mm'] for b in bypass), default=None)
        limit = cfg.get('dsp_bypass_mm_max')
        result['rows'].append(row('PE-PCB-008', f'{dsp} bypass capacitors ({len(bypass)} from the model {key}) maximum pad distance (mm)', rounded(worst),
                                  None if limit is None else f'<= {limit} mm', None if limit is None or worst is None else worst <= float(limit)))
    result['dsp_bypass'] = bypass
    # ground zones
    ground = cfg.get('ground') or {}
    if ground.get('net'):
        gnet = ground['net']
        layers = ground.get('layers') or data.layers
        per_layer = {}
        for layer in layers:
            fills = [fill for z in data.zones if z['net'] == gnet for l, fill in z['fills'].items() if l == layer]
            area = sum(f['area'] for f in fills)
            islands = sum(f['islands'] for f in fills)
            polygons = [rings for f in fills for rings in f['polygons']]
            probes = dict(required=[dict(xy=pt, copper=any(point_in_polygon(pt, rings) for rings in polygons)) for pt in ground.get('require_copper_at', [])],
                          forbidden=[dict(xy=pt, copper=any(point_in_polygon(pt, rings) for rings in polygons)) for pt in ground.get('forbid_copper_at', [])])
            per_layer[layer] = dict(area_mm2=area, islands=islands, zones=len(fills), probes=probes)
        result['ground'] = dict(net=gnet, per_layer=per_layer)
        min_area = ground.get('min_area_mm2')
        passed = None
        if min_area is not None or ground.get('require_copper_at') or ground.get('forbid_copper_at'):
            passed = all((min_area is None or e['area_mm2'] >= float(min_area)) and all(p['copper'] for p in e['probes']['required'])
                         and not any(p['copper'] for p in e['probes']['forbidden']) for e in per_layer.values())
        result['rows'].append(row('PE-PCB-007', f'{gnet} zone area (mm2) and island count per layer',
                                  {l: dict(area=round(e['area_mm2'], 1), islands=e['islands']) for l, e in per_layer.items()} if per_layer else None,
                                  None if passed is None else ' and '.join(filter(None, [f'area >= {min_area} mm2' if min_area is not None else '',
                                                                                        'required probe points covered' if ground.get('require_copper_at') else '',
                                                                                        'forbidden probe points copper-free' if ground.get('forbid_copper_at') else ''])),
                                  passed, 'V1 ground-plane extent guard generalised'))
    return result


def compactness_metrics(data: BoardData, spec: dict) -> dict:
    cfg = spec.get('compactness') or {}
    area = data.outline_area or bbox_area(data.outline_bbox)
    dm2 = area / 1e4
    n = len(data.footprints)
    heights = cfg.get('component_heights_mm', {}) or {}
    default_h = float(heights.get('default', 0.0))

    def height_of(ref, fp):
        if ref in heights:
            return float(heights[ref])
        for pattern, value in heights.items():
            if pattern != 'default' and (fnmatch.fnmatchcase(ref, pattern) or fnmatch.fnmatchcase(fp['footprint'], pattern)):
                return float(value)
        return default_h

    tallest = max(((height_of(ref, fp), ref) for ref, fp in data.footprints.items()), default=(0.0, None))
    front = sum(data.courtyard_area(ref, 'F') for ref in data.footprints)
    back = sum(data.courtyard_area(ref, 'B') for ref in data.footprints)
    hv_nets = nets_of_groups(data.nets(), cfg.get('hv_groups', ['HV']), spec)
    hv_prims = data.primitives(nets=hv_nets)
    hv_box = bbox_union(p.bbox for p in hv_prims)
    outer = data.outer_layers()
    hv_copper_outer = sum(p.area() for p in hv_prims if p.layer in outer and p.item in ('zone', 'pad'))
    rated = cfg.get('rated_power_W')
    declared_height = cfg.get('assembly_height_mm')
    computed_height = (data.thickness_mm or 0.0) + tallest[0]
    height = float(declared_height) if declared_height is not None else computed_height
    result = dict(board_area_mm2=area, board_area_dm2=dm2, footprints=n, footprints_per_dm2=(n / dm2) if dm2 > 0 else None,
                  courtyard_area_mm2=dict(front=front, back=back), courtyard_fraction=dict(front=front / area if area else None, back=back / area if area else None),
                  hv_nets=hv_nets, hv_bbox_mm=list(hv_box) if hv_box else None, hv_bbox_fraction=(bbox_area(hv_box) / area) if hv_box and area else None,
                  hv_outer_copper_mm2=hv_copper_outer, hv_outer_copper_fraction=(hv_copper_outer / (2 * area)) if area else None,
                  tallest_component=dict(ref=tallest[1], height_mm=tallest[0]), assembly_height_mm=dict(declared=declared_height, computed=computed_height, used=height),
                  rated_power_W=rated, power_density_W_per_dm2=(rated / dm2) if rated and dm2 > 0 else None,
                  power_density_W_per_L=(rated / (area * height / 1e6)) if rated and area and height else None, rows=[])
    area_max = cfg.get('board_area_mm2_max')
    result['rows'].append(row('PE-PCB-007', 'board area (mm2), footprints per dm2, courtyard fraction front/back',
                              dict(area=round(area, 1), per_dm2=rounded(result['footprints_per_dm2'], 1), courtyard=rounded(result['courtyard_fraction'])),
                              None if area_max is None else f'area <= {area_max} mm2', None if area_max is None else area <= float(area_max),
                              f"HV bbox fraction {fmt(result['hv_bbox_fraction'])}; power density {fmt(result['power_density_W_per_dm2'], 1)} W/dm2, {fmt(result['power_density_W_per_L'], 1)} W/L"))
    return result


# --- report assembly ---------------------------------------------------------------------------------------------


def jsonable(value):
    """JSON-ready copy: tuples/sets to lists, numpy scalars to Python, floats rounded to 4 decimals."""
    if isinstance(value, Primitive):
        return value.describe()
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, set):
        return sorted(jsonable(v) for v in value)
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, float):
        if math.isinf(value) or math.isnan(value):
            return None
        return round(value, 4)
    return value


def assemble_rule_table(sections: dict, extra_rows=()) -> list:
    """Rows from every metric family in rule order; every registered rule gets at least one row."""
    rows = []
    for key in ('commutation', 'gate_loops', 'isolation', 'heatsink', 'decoupling', 'sensing', 'control', 'compactness'):
        rows.extend(sections.get(key, {}).get('rows', []))
    rows.extend(extra_rows)
    present = {r['rule'] for r in rows}
    for rule in RULES:
        if rule not in present:
            rows.append(row(rule, RULES[rule][0], None, note='no spec input for this rule'))
    order = list(RULES)
    rows.sort(key=lambda r: order.index(r['rule']) if r['rule'] in order else len(order))
    return rows


def md_table(headers, rows) -> list[str]:
    def cell(value):
        return fmt(value).replace('|', '\\|').replace('\n', ' ')
    lines = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
    lines += ['| ' + ' | '.join(cell(v) for v in r) + ' |' for r in rows]
    return lines


def markdown_report(metrics: dict) -> str:
    board = metrics['board']
    lines = [f"# Layout metrics - {metrics['spec']['title']}", '',
             f"Status: **{metrics['status']}**. Generated {metrics['generated_utc']} by `automation/verification/check_sic_layout.py` "
             f"(pcbnew {board.get('pcbnew_version')}, distance backend {metrics['distance_backend']}, {metrics['runtime_s']} s).", '',
             f"Board `{board['file']}` (sha256 `{board['sha256'][:16]}...`), spec `{metrics['spec']['file']}`"
             + (f", model `{metrics['model_file']}`" if metrics.get('model_file') else '') + '.', '',
             '## Board', '']
    lines += md_table(['Metric', 'Value'], [
        ['Outline (mm)', f"{fmt(board['outline_mm'][0], 2)} x {fmt(board['outline_mm'][1], 2)}"],
        ['Outline area (mm2)', fmt(board['outline_area_mm2'], 1)],
        ['Copper layers', f"{board['copper_layers']} ({', '.join(board['layers'])})"],
        ['Thickness (mm)', fmt(board['thickness_mm'], 3)],
        ['Copper thickness (um, stackup text)', fmt(board['copper_um']) if board['copper_um'] else 'no stackup block'],
        ['Footprints / tracks / vias / zones / rule areas', f"{board['footprints']} / {board['tracks']} / {board['vias']} / {board['zones']} / {board['rule_areas']}"],
        ['Nets', board['nets']],
        ['Zones without fill (areas read from the file)', len(board.get('unfilled_zones', [])) or 'none'],
        ['Expected (spec)', fmt(board.get('expected')) if board.get('expected') else 'none given']])
    lines += ['', '## Rule table', '',
              'Dispositions follow the spec thresholds only; every row needs engineering acceptance by a human reviewer.', '']
    lines += md_table(['Rule', 'Requirement', 'Metric', 'Measured', 'Threshold', 'Disposition', 'Note'],
                      [[r['rule'], r['requirement'], r['metric'], fmt(r['measured']), fmt(r['threshold']), r['disposition'], r.get('note', '')] for r in metrics['rule_table']])
    summary = metrics['summary']
    lines += ['', f"Rows: {summary['rows']} - within spec threshold {summary['within_threshold']}, exceeding {summary['exceeding_threshold']}, "
                  f"measured without threshold {summary['measured_only']}, not measured {summary['not_measured']}.", '']
    iso = metrics.get('isolation', {})
    if iso.get('pairs'):
        lines += ['## Isolation: minimum copper distance per layer (mm)', '']
        layers = board['layers']
        lines += md_table(['Pair', *layers, 'Threshold', 'Within'],
                          [[p['name'], *[fmt(p['per_layer'].get(l, {}).get('distance_mm')) for l in layers],
                            fmt({l: p['per_layer'][l]['threshold_mm'] for l in layers if l in p['per_layer']}), fmt(p.get('within_threshold'))] for p in iso['pairs']])
        lines.append('')
    if iso.get('barrier_keepouts'):
        lines += ['## Barrier strips (copper items per layer)', '']
        lines += md_table(['Strip', 'Region', 'Box (mm)', *board['layers'], 'Copper-free'],
                          [[k['name'], k.get('region'), fmt(k.get('bbox_mm'), 1), *[fmt(k['per_layer'].get(l, {}).get('copper_items')) for l in board['layers']], fmt(k['copper_free'])]
                           for k in iso['barrier_keepouts']])
        lines.append('')
    if iso.get('barrier_parts'):
        lines += ['## Barrier parts: land gap, slot and surface path', '']
        lines += md_table(['Ref', 'Found', 'HV pads', 'SELV pads', 'Land gap g (mm)', 'Slot', 'Extension e (mm)', 'Slot width (mm)', 'Surface path (mm)', 'Required e (mm)'],
                          [[b['ref'], fmt(b['found']), fmt(b.get('hv_pads')), fmt(b.get('selv_pads')), fmt(b['land_gap_mm']),
                            (b['best_slot'] or {}).get('kind', 'none'), fmt((b['best_slot'] or {}).get('extension_mm')), fmt((b['best_slot'] or {}).get('width_mm')),
                            fmt(b['surface_path_mm']), fmt(b.get('required_extension_mm'))] for b in iso['barrier_parts']])
        lines.append('')
    com = metrics.get('commutation', {})
    if com.get('mosfets'):
        lines += ['## Commutation loop proxies', '']
        rows = []
        for m in com['mosfets']:
            for role, e in (m.get('pins') or {}).items():
                if e:
                    rows.append([m['ref'], m.get('role'), f"{role} {e['pad']} ({e['net']})", fmt(e['nearest_same_net_mm']), e.get('nearest_same_net_pad'),
                                 fmt(e['nearest_any_mm']), e.get('nearest_any_pad'), fmt(e.get('capacitors_within_row1')), fmt(e.get('capacitors_within_row2'))])
        lines += md_table(['MOSFET', 'Role', 'Pin', 'Same-net cap (mm)', 'Pad', 'Any cap (mm)', 'Pad', 'Caps in row 1', 'Caps in row 2'], rows)
        if com.get('sw_copper_mm2'):
            lines += ['', 'Switch-node copper (mm2): ' + fmt({l: round(v['total_mm2'], 1) for l, v in com['sw_copper_mm2'].items()})]
        if com.get('hf_group_bbox_mm'):
            lines += ['', 'HV ceramic group bounding box (mm): ' + fmt(com['hf_group_bbox_mm'], 2)]
        lines.append('')
    gl = metrics.get('gate_loops', {})
    if gl.get('loops'):
        lines += ['## Gate loops', '']
        lines += md_table(['MOSFET', 'Driver', 'Out->gate (mm)', 'Return->Kelvin (mm)', 'Gate track (mm)', 'Gate vias', 'Gate layers', 'Kelvin layers', 'Adjacent', 'Over Kelvin pour', 'KS distinct', 'KS copper min (mm)', 'KS copper contact', 'KS bridging parts'],
                          [[g['mosfet'], g['driver'], fmt(g.get('driver_output_to_gate_pad_mm')), fmt(g.get('driver_return_to_kelvin_pad_mm')), fmt(g['gate_track_mm'], 2), g['gate_vias'],
                            fmt(g['gate_layers']), fmt(g['kelvin_layers']), fmt(g['gate_kelvin_on_adjacent_layers']), fmt(g.get('gate_track_over_kelvin_pour_fraction')),
                            fmt((g.get('kelvin_separation') or {}).get('distinct_nets')), fmt((g.get('kelvin_separation') or {}).get('min_copper_distance_mm')),
                            fmt((g.get('kelvin_separation') or {}).get('copper_contact')), fmt((g.get('kelvin_separation') or {}).get('bridging_parts'))] for g in gl['loops']])
        lines.append('')
    hs = metrics.get('heatsink', {})
    if hs.get('per_layer'):
        lines += ['## Heatsink envelope', '']
        lines += md_table(['Layer', 'HV items', 'Min distance (mm)', 'Items within keep-out', 'Nearest'],
                          [[l, e['hv_items'], fmt(e['min_distance_mm']), fmt(e['items_within_keepout']), fmt((e.get('nearest') or {}).get('source'))] for l, e in hs['per_layer'].items()])
        lines.append('')
    dec = metrics.get('decoupling', {})
    if dec.get('ics'):
        lines += ['## Decoupling', '']
        lines += md_table(['IC', 'Pad', 'Net', 'Capacitor pad', 'Distance (mm)', 'Same net'],
                          [[ic['ic'], p.get('pad'), p.get('net'), p.get('capacitor'), fmt(p.get('distance_mm')), fmt(p.get('same_net'))] for ic in dec['ics'] for p in ic.get('pads', [])])
        lines.append('')
    sen = metrics.get('sensing', {})
    if sen.get('kelvin_pairs') or sen.get('parts'):
        lines += ['## Sensing', '']
        if sen.get('kelvin_pairs'):
            lines += md_table(['Pair', 'Nets', 'Track (mm)', 'Vias', 'Mismatch (mm)', 'Min to SW (mm)'],
                              [[k['name'], fmt(k['nets']), fmt(k['track_mm'], 2), fmt(k['vias']), fmt(k['mismatch_mm']), fmt(k['min_distance_to_sw_mm'])] for k in sen['kelvin_pairs']])
        if sen.get('parts'):
            lines += ['', *md_table(['Part', 'Found', 'Min to SW (mm)'], [[p['ref'], fmt(p['found']), fmt(p.get('min_distance_to_sw_mm'))] for p in sen['parts']])]
        lines.append('')
    ctl = metrics.get('control', {})
    if ctl.get('control_refs') is not None:
        lines += ['## Control section', '',
                  f"Control parts: {len(ctl['control_refs'])}, power parts: {len(ctl['power_refs'])}, bounding-box separation {fmt(ctl.get('bbox_separation_mm'))} mm"
                  + (f", overlap {fmt(ctl.get('bbox_overlap_mm2'), 1)} mm2" if ctl.get('bbox_overlap_mm2') else '') + '.']
        if ctl.get('ground'):
            lines += ['', *md_table(['Ground layer', 'Area (mm2)', 'Islands', 'Zones', 'Required probes covered', 'Forbidden probes copper-free'],
                                    [[l, fmt(e['area_mm2'], 1), e['islands'], e['zones'],
                                      f"{sum(p['copper'] for p in e['probes']['required'])}/{len(e['probes']['required'])}",
                                      f"{sum(not p['copper'] for p in e['probes']['forbidden'])}/{len(e['probes']['forbidden'])}"] for l, e in ctl['ground']['per_layer'].items()])]
        if ctl.get('dsp_bypass'):
            lines += ['', f"DSP bypass capacitors: {len(ctl['dsp_bypass'])}, maximum pad distance {fmt(max(b['distance_mm'] for b in ctl['dsp_bypass']))} mm."]
        lines.append('')
    cmp_ = metrics.get('compactness', {})
    if cmp_:
        lines += ['## Compactness', '']
        lines += md_table(['Metric', 'Value'], [
            ['Board area (mm2 / dm2)', f"{fmt(cmp_['board_area_mm2'], 1)} / {fmt(cmp_['board_area_dm2'], 3)}"],
            ['Footprints per dm2', fmt(cmp_['footprints_per_dm2'], 1)],
            ['Courtyard fraction front / back', f"{fmt(cmp_['courtyard_fraction']['front'])} / {fmt(cmp_['courtyard_fraction']['back'])}"],
            ['HV bounding-box fraction of board', fmt(cmp_['hv_bbox_fraction'])],
            ['HV copper on outer layers (mm2, fraction of both sides)', f"{fmt(cmp_['hv_outer_copper_mm2'], 1)} ({fmt(cmp_['hv_outer_copper_fraction'])})"],
            ['Tallest component', f"{cmp_['tallest_component']['ref']} {fmt(cmp_['tallest_component']['height_mm'], 1)} mm"],
            ['Assembly height (mm) declared / computed / used', fmt([cmp_['assembly_height_mm']['declared'], cmp_['assembly_height_mm']['computed'], cmp_['assembly_height_mm']['used']], 1)],
            ['Rated power (W)', fmt(cmp_['rated_power_W'])],
            ['Power density (W/dm2, W/L)', f"{fmt(cmp_['power_density_W_per_dm2'], 1)}, {fmt(cmp_['power_density_W_per_L'], 1)}"]])
        lines.append('')
    nets = metrics.get('nets', {})
    classed = [(n, r) for n, r in nets.items() if r.get('cls')]
    if classed:
        lines += ['## Classified nets', '']
        lines += md_table(['Net', 'Class', 'Track (mm)', 'Tracks', 'Vias', 'Pads', 'Layers', 'Zone area (mm2)'],
                          [[n, r['cls'], fmt(r['track_mm'], 1), r['tracks'], r['vias'], r['pads'], fmt(r['layers']), fmt({k: round(v, 1) for k, v in r['zone_area_mm2'].items()})] for n, r in classed])
        lines.append('')
    if metrics.get('warnings'):
        lines += ['## Warnings', ''] + [f'- {w}' for w in metrics['warnings']] + ['']
    lines += ['## Notes and limitations', ''] + [f'- {n}' for n in metrics['notes']] + ['']
    return '\n'.join(lines)


def run_check(board_path, spec: dict, model=None, backend=None, spec_path=None, model_path=None) -> dict:
    """Measure one board against a loaded spec; returns the metrics document (JSON-ready)."""
    start = time.monotonic()
    spec = dict(spec)
    spec['_backend'] = distance_backend(backend)
    data = extract_board(board_path)
    sections = dict(board=board_summary(data, spec))
    nets = net_summary(data, spec)
    sections['commutation'] = commutation_metrics(data, spec)
    sections['gate_loops'] = gate_loop_metrics(data, spec)
    sections['isolation'] = isolation_metrics(data, spec)
    sections['heatsink'] = heatsink_metrics(data, spec)
    sections['decoupling'] = decoupling_metrics(data, spec)
    sections['sensing'] = sensing_metrics(data, spec)
    sections['control'] = control_metrics(data, spec, model)
    sections['compactness'] = compactness_metrics(data, spec)
    rows = assemble_rule_table(sections, copper_rows(nets, spec))
    for section in sections.values():
        section.pop('rows', None)
    summary = dict(rows=len(rows), within_threshold=sum(r['disposition'] == WITHIN for r in rows),
                   exceeding_threshold=sum(r['disposition'] == EXCEEDS for r in rows),
                   measured_only=sum(r['disposition'] == MEASURED for r in rows), not_measured=sum(r['disposition'] == NOT_MEASURED for r in rows))
    metrics = dict(schema_version=METRICS_SCHEMA_VERSION, status=STATUS, generated_utc=datetime.now(timezone.utc).isoformat(),
                   checker='automation/verification/check_sic_layout.py',
                   spec=dict(file=str(spec_path) if spec_path else None, sha256=hashlib.sha256(Path(spec_path).read_bytes()).hexdigest() if spec_path else None,
                             board=spec['board'], title=spec['title']),
                   model_file=str(model_path) if model_path else None, distance_backend=spec['_backend'], runtime_s=None,
                   board=sections['board'], nets=nets, commutation=sections['commutation'], gate_loops=sections['gate_loops'],
                   isolation=sections['isolation'], heatsink=sections['heatsink'], decoupling=sections['decoupling'], sensing=sections['sensing'],
                   control=sections['control'], compactness=sections['compactness'], rule_table=rows, summary=summary,
                   notes=list(NOTES) + list(spec.get('notes', [])))
    metrics['warnings'] = []
    if sections['board']['unfilled_zones']:
        metrics['warnings'].append(f"{len(sections['board']['unfilled_zones'])} zone(s) carry no fill in the file; zone areas and "
                                   "zone-based distances are measured from stored fills - refill and save the board before reading them")
    metrics['runtime_s'] = round(time.monotonic() - start, 3)
    return jsonable(metrics)


def write_outputs(metrics: dict, output_dir, label: str) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f'layout_metrics_{label}.json'
    md_path = output_dir / f'layout_metrics_{label}.md'
    json_path.write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
    md_path.write_text(markdown_report(metrics), encoding='utf-8')
    return json_path, md_path


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
    parser.add_argument('board', type=Path, help='KiCad board (.kicad_pcb)')
    parser.add_argument('--spec', type=Path, help='layout spec JSON (default: the V2 power/control spec chosen by --label)')
    parser.add_argument('--model', type=Path, help='shared-format part list (circuit_<board>.json) for the DSP bypass pattern')
    parser.add_argument('--output', type=Path, default=CHECKS_DIR, help='directory for layout_metrics_<label>.json/.md')
    parser.add_argument('--label', help="output label (default: the spec's board name)")
    parser.add_argument('--backend', choices=['numpy', 'shapely'], help='polygon distance backend (default: shapely if importable)')
    parser.add_argument('--fail-on-threshold', action='store_true', help='exit 3 when a spec threshold is exceeded')
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
    spec_path = args.spec or DEFAULT_SPECS.get(args.label or 'power')
    if spec_path is None or not Path(spec_path).is_file():
        print(f'layout spec not found: {spec_path}', file=sys.stderr)
        return 2
    spec = load_spec(spec_path)
    model = load_model(args.model) if args.model else None
    metrics = run_check(args.board, spec, model, backend=args.backend, spec_path=spec_path, model_path=args.model)
    label = args.label or spec['board']
    json_path, md_path = write_outputs(metrics, args.output, label)
    summary = metrics['summary']
    print(f"{STATUS}: {summary['rows']} rule rows ({summary['within_threshold']} within, {summary['exceeding_threshold']} exceeding spec thresholds, "
          f"{summary['measured_only']} measured only, {summary['not_measured']} not measured) in {metrics['runtime_s']} s -> {json_path}")
    if args.fail_on_threshold and summary['exceeding_threshold']:
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
