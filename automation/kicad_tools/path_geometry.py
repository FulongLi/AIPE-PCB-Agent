"""Pure-Python path geometry shared by the grid router's ``beautify`` stage and the routing-quality checker.

Everything here works on plain tuples (grid cells or millimetres, the caller decides) and needs neither numpy nor
pcbnew, so the host interpreter tests it. Three groups of helpers:

1. Search support: the 8-direction move table (``MOVES8``, index = octant), ``turn_class`` between two octants and the
   ``octile`` heuristic that is admissible for unit / sqrt(2) step costs.
2. Polyline simplification on the grid: ``octilinear_candidates`` (the two 0/45/90-degree connections of two cells),
   ``shortcut`` (greedy string pulling validated by a caller-supplied clearance test), ``collapse_short_runs`` (residual
   zigzags / stair-steps), ``chamfer`` (on-grid 45-degree cuts of 90-degree corners) and ``merge_collinear``.
3. Arcs: ``fillet_corner`` (tangent arc replacing a corner, construction verified in pcbnew: radius, sweep and tangents
   reproduce to nm rounding), ``arc_from_points``/``arc_length``/``sample_arc``/``tangent_at`` for marking and checking.

``chains_from_items`` turns board items (segments and arcs with exact endpoint keys) into maximal degree-2 chains between
anchors (pads, vias, junctions, caller-fixed points); the router and the checker share it so both agree on what a
"corner" is. ``short_runs`` finds zigzag / stair-step runs on a chain; ``classify_bend`` bands a turn angle.

Determinism: every function is a pure function of its inputs; candidate orders are fixed.
"""
from __future__ import annotations

import math

SQRT2 = math.sqrt(2.0)
MOVES4 = ((1, 0), (-1, 0), (0, 1), (0, -1))  # the V2 neighbour order (grid_router.Grid.astar)
MOVES8 = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))  # index = octant (45-degree steps)
NO_DIR = 8
OCTANT = {move: index for index, move in enumerate(MOVES8)}
BEND_BANDS = {'45': (40.0, 50.0), '90': (85.0, 95.0)}
STRAIGHT_TOL_DEG = 5.0


# ----- search support ------------------------------------------------------------------------------------------------
def turn_class(d_in, d_out):
    """0 straight, 1 = 45 deg, 2 = 90 deg, 3 = 135 deg, 4 = reversal between two octant indices (``NO_DIR`` -> 0)."""
    if d_in == NO_DIR or d_out == NO_DIR:
        return 0
    diff = abs(int(d_in) - int(d_out)) % 8
    return min(diff, 8 - diff)


def octile(dx, dy):
    """8-direction free-space distance in cells for absolute deltas: max + (sqrt2 - 1) * min."""
    dx, dy = abs(dx), abs(dy)
    return max(dx, dy) + (SQRT2 - 1.0) * min(dx, dy)


# ----- polylines -----------------------------------------------------------------------------------------------------
def polyline_length(points):
    """Sum of the segment lengths of a point list."""
    return sum(math.dist(points[i], points[i + 1]) for i in range(len(points) - 1))


def turn_angle(p0, p1, p2):
    """Signed turn in degrees at p1 between p0->p1 and p1->p2 (0 straight, 180 reversal; sign = cross product sign)."""
    ux, uy = p1[0] - p0[0], p1[1] - p0[1]
    vx, vy = p2[0] - p1[0], p2[1] - p1[1]
    if (ux == 0 and uy == 0) or (vx == 0 and vy == 0):
        return 0.0
    cross = ux * vy - uy * vx
    dot = ux * vx + uy * vy
    return math.degrees(math.atan2(cross, dot))


def classify_bend(angle_deg, bands=BEND_BANDS, straight_tol=STRAIGHT_TOL_DEG):
    """'straight' (< tol), '45', '90' (inside the bands) or 'other' for an unsigned turn angle in degrees."""
    a = abs(angle_deg)
    if a < straight_tol:
        return 'straight'
    for name, (lo, hi) in bands.items():
        if lo <= a <= hi:
            return name
    return 'other'


def merge_collinear(points, tol=1e-9):
    """Drop repeated points and interior vertices where the direction does not change."""
    out = []
    for p in points:
        if out and math.dist(out[-1], p) <= tol:
            continue
        if len(out) >= 2:
            ax, ay = out[-1][0] - out[-2][0], out[-1][1] - out[-2][1]
            bx, by = p[0] - out[-1][0], p[1] - out[-1][1]
            if abs(ax * by - ay * bx) <= tol * max(1.0, math.hypot(ax, ay) * math.hypot(bx, by)) and ax * bx + ay * by > 0:
                out[-1] = p
                continue
        out.append(p)
    return out


def _sign(v):
    return (v > 0) - (v < 0)


def octilinear_candidates(a, b):
    """0/45/90-degree connections of a to b: [] when equal, [[a, b]] when axis-parallel or an exact diagonal, else the
    two bent forms [a, a + m*(sx, sy), b] (diagonal first) and [a, b - m*(sx, sy), b] (axis first), m = min(|dx|, |dy|).
    Both are shorter than the Manhattan path (max + (sqrt2 - 1) * min)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == 0 and dy == 0:
        return []
    if dx == 0 or dy == 0 or abs(dx) == abs(dy):
        return [[a, b]]
    m = min(abs(dx), abs(dy))
    sx, sy = _sign(dx), _sign(dy)
    kind = type(a[0])
    k1 = (kind(a[0] + m * sx), kind(a[1] + m * sy))
    k2 = (kind(b[0] - m * sx), kind(b[1] - m * sy))
    return [[a, k1, b], [a, k2, b]]


def shortcut(points, is_clear, candidates=octilinear_candidates):
    """Greedy string pulling: from each vertex jump to the farthest later vertex reachable by a clear candidate polyline
    (``is_clear(polyline) -> bool``); endpoints stay, the result is never longer, collinear leftovers are merged."""
    pts = list(points)
    n = len(pts)
    if n < 3:
        return pts
    out = [pts[0]]
    i = 0
    while i < n - 1:
        jumped = False
        for j in range(n - 1, i + 1, -1):
            for cand in candidates(pts[i], pts[j]):
                if polyline_length(cand) <= polyline_length(pts[i:j + 1]) + 1e-9 and is_clear(cand):
                    out.extend(cand[1:]); i = j; jumped = True
                    break
            if jumped:
                break
        if not jumped:
            out.append(pts[i + 1]); i += 1
    return merge_collinear(out)


def short_runs(points, l_short, min_turn_deg=40.0, min_segments=3):
    """Maximal runs of >= ``min_segments`` consecutive segments shorter than ``l_short`` whose joints all turn by at least
    ``min_turn_deg``. Returns [dict(start, end, segments, kind, length)] with vertex indices and kind 'stair' (alternating
    turn signs: a staircase approximating a diagonal) or 'zigzag' (any other sign pattern: meanders and detours)."""
    n = len(points) - 1
    if n < min_segments:
        return []
    lengths = [math.dist(points[i], points[i + 1]) for i in range(n)]
    turns = [turn_angle(points[i - 1], points[i], points[i + 1]) for i in range(1, n)]  # turns[i-1] is the joint before segment i
    runs = []
    i = 0
    while i < n:
        if lengths[i] >= l_short:
            i += 1; continue
        j = i
        while j + 1 < n and lengths[j + 1] < l_short and abs(turns[j]) >= min_turn_deg:
            j += 1
        if j - i + 1 >= min_segments:
            signs = [_sign(turns[k]) for k in range(i, j)]
            kind = 'stair' if all(signs[k] != signs[k + 1] for k in range(len(signs) - 1)) else 'zigzag'
            runs.append(dict(start=i, end=j + 1, segments=j - i + 1, kind=kind, length=sum(lengths[i:j + 1])))
        i = j + 1
    return runs


def collapse_short_runs(points, l_short, is_clear, candidates=octilinear_candidates, min_segments=2):
    """Replace runs of >= ``min_segments`` consecutive short segments (< ``l_short``) by a clear octilinear connection of
    the run's ends (also tried one vertex wider on either side); the result is never longer."""
    pts = list(points)
    changed = True
    while changed and len(pts) >= 3:
        changed = False
        n = len(pts) - 1
        lengths = [math.dist(pts[i], pts[i + 1]) for i in range(n)]
        i = 0
        while i < n:
            if lengths[i] >= l_short:
                i += 1; continue
            j = i
            while j + 1 < n and lengths[j + 1] < l_short:
                j += 1
            if j - i + 1 >= min_segments:
                for lo, hi in ((i, j + 1), (max(0, i - 1), j + 1), (i, min(n, j + 2)), (max(0, i - 1), min(n, j + 2))):
                    if hi - lo < 2:
                        continue
                    done = False
                    for cand in candidates(pts[lo], pts[hi]):
                        if len(cand) < hi - lo + 1 and polyline_length(cand) <= polyline_length(pts[lo:hi + 1]) + 1e-9 and is_clear(cand):
                            pts[lo:hi + 1] = cand; done = True
                            break
                    if done:
                        changed = True
                        break
                if changed:
                    break
            i = j + 1
        pts = merge_collinear(pts)
    return pts


def _unit_steps(p, q):
    """(unit move, step count) of an axis or exact-diagonal leg p->q in integer cells, or None."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    if dx == 0 and dy == 0:
        return None
    if dx != 0 and dy != 0 and abs(dx) != abs(dy):
        return None
    steps = max(abs(dx), abs(dy))
    return (_sign(dx), _sign(dy)), steps


def chamfer(points, is_clear, min_cut=2, keep_start=0, keep_end=0, min_turn_deg=80.0, tries=5):
    """Cut remaining >= ``min_turn_deg`` corners of an on-grid octilinear polyline (integer cells) by the largest clear
    45-degree chamfer: ``c`` unit steps are removed from each leg (c from the legs' room down to ``min_cut`` in ~5
    geometric steps). ``keep_start``/``keep_end`` steps of the first/last leg stay straight. Never longer; deterministic."""
    pts = list(points)
    i = 1
    while i < len(pts) - 1:
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        leg1, leg2 = _unit_steps(p0, p1), _unit_steps(p1, p2)
        if leg1 is None or leg2 is None or abs(turn_angle(p0, p1, p2)) < min_turn_deg:
            i += 1; continue
        (u1, n1), (u2, n2) = leg1, leg2
        # the previous vertex is final (chamfered or kept), so the whole incoming leg is available; the outgoing leg is
        # shared with the next vertex when that one is a sharp corner too (half each); chain ends keep their straight exit
        room1 = n1 - keep_start if i == 1 else n1
        if i == len(pts) - 2:
            room2 = n2 - keep_end
        else:
            room2 = n2 // 2 if abs(turn_angle(p1, p2, pts[i + 2])) >= min_turn_deg else n2
        cmax = min(room1, room2)
        if cmax < min_cut:
            i += 1; continue
        cuts = []
        c = cmax
        while len(cuts) < tries and c >= min_cut:
            if c not in cuts:
                cuts.append(c)
            c = int(c * 0.6) if int(c * 0.6) < c else c - 1
        if min_cut not in cuts:
            cuts.append(min_cut)
        done = False
        for c in cuts:
            a = (p1[0] - c * u1[0], p1[1] - c * u1[1]); b = (p1[0] + c * u2[0], p1[1] + c * u2[1])
            if is_clear([a, b]):
                pts[i:i + 1] = [a, b]; done = True
                break
        i += 2 if done else 1
    return merge_collinear(pts)


# ----- arcs ----------------------------------------------------------------------------------------------------------
def fillet_corner(p0, p1, p2, radius):
    """Tangent arc of ``radius`` replacing the corner p0-p1-p2: (A, M, B, trim, turn_deg) with A = p1 - d*u1,
    B = p1 + d*u2, d = r*tan(theta/2), M the arc point on the bisector; None for near-straight (< 1 deg) or
    near-reversal (> 179 deg) corners or when ``radius`` <= 0."""
    if radius <= 0:
        return None
    l1, l2 = math.dist(p0, p1), math.dist(p1, p2)
    if l1 < 1e-12 or l2 < 1e-12:
        return None
    u1 = ((p1[0] - p0[0]) / l1, (p1[1] - p0[1]) / l1)
    u2 = ((p2[0] - p1[0]) / l2, (p2[1] - p1[1]) / l2)
    theta = math.radians(abs(turn_angle(p0, p1, p2)))
    if theta < math.radians(1.0) or theta > math.radians(179.0):
        return None
    d = radius * math.tan(theta / 2)
    a = (p1[0] - d * u1[0], p1[1] - d * u1[1])
    b = (p1[0] + d * u2[0], p1[1] + d * u2[1])
    nx, ny = u2[0] - u1[0], u2[1] - u1[1]
    nn = math.hypot(nx, ny)
    nx, ny = nx / nn, ny / nn
    dist_c = radius / math.cos(theta / 2)
    cx, cy = p1[0] + nx * dist_c, p1[1] + ny * dist_c
    m = (cx - nx * radius, cy - ny * radius)
    return a, m, b, d, math.degrees(theta)


def arc_from_points(a, m, b):
    """(centre, radius, start_angle, sweep) of the circle through a, m, b, the arc running a -> m -> b (sweep signed,
    radians, positive = increasing angle). Raises ValueError for collinear points."""
    ax, ay = a; mx, my = m; bx, by = b
    d = 2 * (ax * (my - by) + mx * (by - ay) + bx * (ay - my))
    if abs(d) < 1e-15:
        raise ValueError('collinear points define no arc')
    a2, m2, b2 = ax * ax + ay * ay, mx * mx + my * my, bx * bx + by * by
    cx = (a2 * (my - by) + m2 * (by - ay) + b2 * (ay - my)) / d
    cy = (a2 * (bx - mx) + m2 * (ax - bx) + b2 * (mx - ax)) / d
    r = math.hypot(ax - cx, ay - cy)
    ang_a, ang_m, ang_b = (math.atan2(p[1] - cy, p[0] - cx) for p in (a, m, b))
    ccw_b = (ang_b - ang_a) % (2 * math.pi)
    ccw_m = (ang_m - ang_a) % (2 * math.pi)
    sweep = ccw_b if ccw_m <= ccw_b else ccw_b - 2 * math.pi
    return (cx, cy), r, ang_a, sweep


def arc_length(a, m, b):
    """Length of the arc a -> m -> b."""
    _, r, _, sweep = arc_from_points(a, m, b)
    return r * abs(sweep)


def sample_arc(a, m, b, max_chord):
    """Points along the arc from a to b (inclusive) with chords no longer than ``max_chord``."""
    (cx, cy), r, start, sweep = arc_from_points(a, m, b)
    n = max(2, int(math.ceil(r * abs(sweep) / max(max_chord, 1e-9))) + 1)
    pts = [(cx + r * math.cos(start + sweep * k / (n - 1)), cy + r * math.sin(start + sweep * k / (n - 1))) for k in range(n)]
    pts[0] = tuple(a); pts[-1] = tuple(b)
    return pts


def tangent_at(a, m, b, at_start):
    """Unit tangent of the arc a -> m -> b in the direction of travel at its start (``at_start``) or end."""
    (cx, cy), r, start, sweep = arc_from_points(a, m, b)
    phi = start if at_start else start + sweep
    s = 1.0 if sweep >= 0 else -1.0
    return (-math.sin(phi) * s, math.cos(phi) * s)


def point_segment_distance(c, p, q):
    """Distance from point ``c`` to the segment ``p``-``q``."""
    vx, vy = q[0] - p[0], q[1] - p[1]
    l2 = vx * vx + vy * vy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((c[0] - p[0]) * vx + (c[1] - p[1]) * vy) / l2))
    return math.dist(c, (p[0] + t * vx, p[1] + t * vy))


def diagonals_clear_of(points, guards):
    """True when no diagonal segment of the polyline comes closer than ``keep`` to any guard point (``guards``:
    [(point, keep)]); orthogonal segments are free. Used to keep a straight orthogonal run of ``keep`` at a via end."""
    for p, q in zip(points, points[1:]):
        if p[0] != q[0] and p[1] != q[1]:
            for c, keep in guards:
                if point_segment_distance(c, p, q) < keep - 1e-9:
                    return False
    return True


# ----- chains ----------------------------------------------------------------------------------------------------------
def chains_from_items(items, fixed=()):
    """Maximal same-net, same-layer chains of items between anchors.

    ``items``: dicts with ``id``, ``net``, ``layer``, ``a``, ``b`` (exact, hashable endpoint keys), ``width`` and optionally
    ``kind`` ('seg' default or 'arc') and ``mid``. A node is an anchor when its degree is not 2, when it is listed in
    ``fixed`` (via centres, pad hits), or when the two items meeting there differ in width (arcs are ordinary edges, so a
    seg-arc-seg fillet is one chain and the checker can judge the joints' tangency). Returns
    [dict(net, layer, width, points, edges, fixed_start, fixed_end)] where ``edges`` are the items oriented along the
    chain (``a`` -> ``b`` as walked, with ``index`` into ``items``). Deterministic: chains start at the smaller anchor and
    are sorted by (net, layer, first point)."""
    fixed = set(fixed)
    nodes = {}
    for index, it in enumerate(items):
        for p in (it['a'], it['b']):
            nodes.setdefault((it['net'], it['layer'], p), []).append(index)

    def anchor(net, layer, p):
        ids = nodes[(net, layer, p)]
        if len(ids) != 2 or p in fixed or (net, p) in fixed:   # ``fixed`` holds points (any net) or (net, point) pairs
            return True
        i1, i2 = (items[k] for k in ids)
        return abs(float(i1['width']) - float(i2['width'])) > 1e-9

    visited = set()
    chains = []
    order = sorted(range(len(items)), key=lambda k: (str(items[k]['net']), str(items[k]['layer']), min(items[k]['a'], items[k]['b']),
                                                      max(items[k]['a'], items[k]['b']), str(items[k].get('id', k))))

    def walk(start_index, start_point):
        it = items[start_index]
        net, layer = it['net'], it['layer']
        p = start_point
        edges, points = [], [p]
        index = start_index
        while True:
            visited.add(index)
            it = items[index]
            q = it['b'] if it['a'] == p else it['a']
            edges.append(dict(index=index, id=it.get('id', index), a=p, b=q, kind=it.get('kind', 'seg'), mid=it.get('mid'), width=it['width']))
            points.append(q)
            if anchor(net, layer, q):
                return points, edges, True
            nxt = [k for k in nodes[(net, layer, q)] if k != index]
            if not nxt or nxt[0] in visited:
                return points, edges, False
            index, p = nxt[0], q

    # Two passes: items with an anchor end first, so every open chain is walked whole from one of its anchors (starting at an
    # interior degree-2 item would split the chain at an arbitrary vertex); what is left afterwards are closed loops.
    anchored = [(k, [p for p in (items[k]['a'], items[k]['b']) if anchor(items[k]['net'], items[k]['layer'], p)]) for k in order]
    for k, ends in [(k, e) for k, e in anchored if e] + [(k, e) for k, e in anchored if not e]:
        if k in visited:
            continue
        it = items[k]
        start = min(ends) if ends else min(it['a'], it['b'])
        points, edges, closed = walk(k, start)
        chains.append(dict(net=it['net'], layer=it['layer'], width=it['width'], points=points, edges=edges,
                           fixed_start=bool(ends), fixed_end=closed))
    chains.sort(key=lambda c: (str(c['net']), str(c['layer']), c['points'][0], c['points'][-1]))
    return chains
