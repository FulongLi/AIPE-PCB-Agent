"""Orthogonal schematic wire routing on the 1.27 mm sheet grid, wire normalisation and connectivity.

Standalone (no dependency on the PCB grid_router): a sheet is a small grid (A3 = 331 x 234 cells), so a
plain Python search is enough.  WireGrid keeps the occupancy of symbol bodies, texts, pin points, wire
segments and labels per net; route() tries the straight / L candidates first and then a Dijkstra search
with bend and crossing penalties (4-neighbour, so every wire stays horizontal or vertical).  The router
never lets a wire overlap, end on or run through a point of another net, and crossings are only allowed
straight through the interior of the other wire, which is exactly what KiCad treats as "not connected".

normalise() applies KiCad's connection rules to a set of segments: wire ends on the interior of a
same-net wire split that wire and get a junction, three or more connections at one point get a
junction, collinear two-wire corners are merged.  connectivity() re-derives {(ref, pad): net name}
from the drawn geometry (wires, junctions, labels, power symbols, hierarchical labels + sheet pins) with
the coincidence rules measured natively for KiCad 10 (see the V2.1 design notes), so a generator can
prove netlist identity before any file is written.
"""
from __future__ import annotations

import heapq
from collections import defaultdict
from dataclasses import dataclass, field

GRID = 1.27
BEND_COST = 3
CROSS_COST = 8
STEP_COST = 1
DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))
AXIS = {(1, 0): 'h', (-1, 0): 'h', (0, 1): 'v', (0, -1): 'v'}


def snap(value: float) -> float:
    return round(round(value / GRID) * GRID, 4)


def cell(point) -> tuple[int, int]:
    return (int(round(point[0] / GRID)), int(round(point[1] / GRID)))


def point(c) -> tuple[float, float]:
    return (snap(c[0] * GRID), snap(c[1] * GRID))


def pt(x, y) -> tuple[float, float]:
    return (round(x, 4), round(y, 4))


def cells_between(a, b):
    """Cells covered by the axis-aligned segment a-b (both ends included); ValueError when diagonal."""
    (ax, ay), (bx, by) = cell(a), cell(b)
    if ax != bx and ay != by:
        raise ValueError(f'diagonal wire {a}-{b}')
    if ax == bx:
        step = 1 if by >= ay else -1
        return [(ax, y) for y in range(ay, by + step, step)]
    step = 1 if bx >= ax else -1
    return [(x, ay) for x in range(ax, bx + step, step)]


def on_segment(p, a, b) -> bool:
    """True when p lies on the axis-aligned segment a-b (ends included)."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    eps = 1e-3
    if abs(ax - bx) < eps:
        return abs(px - ax) < eps and min(ay, by) - eps <= py <= max(ay, by) + eps
    if abs(ay - by) < eps:
        return abs(py - ay) < eps and min(ax, bx) - eps <= px <= max(ax, bx) + eps
    return False


def interior(p, a, b) -> bool:
    return on_segment(p, a, b) and p != a and p != b


@dataclass
class Segment:
    net: str
    a: tuple
    b: tuple

    def __post_init__(self):
        self.a, self.b = pt(*self.a), pt(*self.b)
        if self.a[0] != self.b[0] and self.a[1] != self.b[1]:
            raise ValueError(f'diagonal wire {self.a}-{self.b} on {self.net}')

    @property
    def axis(self) -> str:
        return 'v' if self.a[0] == self.b[0] else 'h'

    @property
    def length(self) -> float:
        return abs(self.a[0] - self.b[0]) + abs(self.a[1] - self.b[1])


class WireGrid:
    """Occupancy of one sheet in 1.27 mm cells."""

    def __init__(self, x0: float, y0: float, x1: float, y1: float):
        self.cx0, self.cy0 = cell((x0, y0))
        self.cx1, self.cy1 = cell((x1, y1))
        self.blocked: set = set()
        self.h: dict = {}          # cell -> net of a horizontal wire covering it
        self.v: dict = {}          # cell -> net of a vertical wire covering it
        self.ends: dict = defaultdict(set)   # cell -> nets with a wire endpoint there
        self.pins: dict = {}       # cell -> net (None for no-connect pins) of a pin point
        self.labels: dict = {}     # cell -> net of a label / power pin
        self.net_cells: dict = defaultdict(set)   # net -> cells of its wires and pins
        self.degree: dict = defaultdict(int)      # cell -> number of wire ends
        self.crossings = 0

    # --- occupancy ------------------------------------------------------------------------------------------
    def block_rect(self, x0: float, y0: float, x1: float, y1: float, margin: float = 0.0) -> None:
        a, b = cell((min(x0, x1) - margin, min(y0, y1) - margin)), cell((max(x0, x1) + margin, max(y0, y1) + margin))
        for x in range(a[0], b[0] + 1):
            for y in range(a[1], b[1] + 1):
                self.blocked.add((x, y))

    def add_pin(self, p, net) -> None:
        c = cell(p)
        self.pins[c] = net
        if net is not None:
            self.net_cells[net].add(c)

    def add_label(self, p, net) -> None:
        c = cell(p)
        self.labels[c] = net
        self.net_cells[net].add(c)

    def add_segment(self, seg: Segment) -> None:
        cells = cells_between(seg.a, seg.b)
        table = self.h if seg.axis == 'h' else self.v
        for c in cells:
            if table.get(c) not in (None, seg.net) or (c in self.pins and self.pins[c] != seg.net):
                self.crossings += 0  # occupancy conflicts are prevented by route(); recorded by normalise()
            table[c] = seg.net
            self.net_cells[seg.net].add(c)
        for c in (cells[0], cells[-1]):
            self.ends[c].add(seg.net)
            self.degree[c] += 1

    def other_net_at(self, c, net):
        """Net of another wire/pin/label at this cell, or None."""
        for table in (self.h, self.v, self.pins, self.labels):
            other = table.get(c)
            if other is not None and other != net:
                return other
        return None

    def free(self, c, net=None) -> bool:
        return c not in self.blocked and self.other_net_at(c, net) is None and not (self.ends.get(c) - {net} if c in self.ends else set())

    # --- search ---------------------------------------------------------------------------------------------
    def _enterable(self, c, net, move, targets):
        """(allowed, cost, must_go_straight) for entering cell c with unit move `move`."""
        if c in targets:
            return True, 0, False
        if c in self.blocked or not (self.cx0 <= c[0] <= self.cx1 and self.cy0 <= c[1] <= self.cy1):
            return False, 0, False
        if c in self.pins or c in self.labels:
            return False, 0, False
        if self.ends.get(c):
            return False, 0, False
        axis = AXIS[move]
        same = (self.h if axis == 'h' else self.v).get(c)
        cross = (self.v if axis == 'h' else self.h).get(c)
        if same is not None:
            return False, 0, False          # overlap with any wire (own-net wires are targets)
        if cross is not None:
            return True, CROSS_COST, True   # cross another net straight through its interior
        return True, 0, False

    def straight_candidates(self, net, a, b, targets):
        """Straight or single-bend paths from cell a to cell b whose cells are all enterable; cheapest first."""
        paths = []
        if a[0] == b[0] or a[1] == b[1]:
            paths.append([a, b])
        else:
            paths.append([a, (b[0], a[1]), b])
            paths.append([a, (a[0], b[1]), b])
        good = []
        for corners in paths:
            cost, ok = 0, True
            prev_straight = False
            for i in range(len(corners) - 1):
                cells = cells_between(point(corners[i]), point(corners[i + 1]))
                move = (max(-1, min(1, cells[1][0] - cells[0][0])), max(-1, min(1, cells[1][1] - cells[0][1]))) if len(cells) > 1 else None
                if move is None:
                    ok = False
                    break
                if i > 0 and prev_straight:
                    ok = False      # turning inside another net's wire
                    break
                for c in cells[1:]:
                    allowed, extra, straight = self._enterable(c, net, move, targets if c == cells[-1] or c in targets else set())
                    if not allowed or (c in targets and c != corners[-1]):
                        ok = False
                        break
                    cost += STEP_COST + extra
                    prev_straight = straight
                if not ok:
                    break
                cost += BEND_COST if i > 0 else 0
            if ok and corners[-1] in targets:
                good.append((cost, corners))
        good.sort()
        return [c for _, c in good]

    def route(self, net: str, sources: dict, targets: set, margin: int = 24) -> list | None:
        """Shortest orthogonal path (list of corner points) from any source cell to any target cell.

        `sources` maps cell -> allowed first moves (None = any).  Returns None when no path exists.
        """
        if not sources or not targets:
            return None
        # fast path: straight / L candidates between the closest source-target pair
        best = None
        for s in sources:
            for t in targets:
                d = abs(s[0] - t[0]) + abs(s[1] - t[1])
                if best is None or d < best[0]:
                    best = (d, s, t)
        _, s, t = best
        for corners in self.straight_candidates(net, s, t, targets):
            first = (max(-1, min(1, corners[1][0] - corners[0][0])), max(-1, min(1, corners[1][1] - corners[0][1])))
            if sources[s] is None or first in sources[s]:
                return [point(c) for c in corners]
        for region in (margin, None):
            path = self._dijkstra(net, sources, targets, region)
            if path:
                return path
        return None

    def _dijkstra(self, net, sources, targets, margin):
        xs = [c[0] for c in list(sources) + list(targets)]
        ys = [c[1] for c in list(sources) + list(targets)]
        if margin is None:
            bx0, by0, bx1, by1 = self.cx0, self.cy0, self.cx1, self.cy1
        else:
            bx0, by0 = max(self.cx0, min(xs) - margin), max(self.cy0, min(ys) - margin)
            bx1, by1 = min(self.cx1, max(xs) + margin), min(self.cy1, max(ys) + margin)
        heap = []
        best = {}
        parent = {}
        for s, allowed in sorted(sources.items()):
            heapq.heappush(heap, (0, s, None, 0))
            best[(s, None)] = 0
        counter = 1
        while heap:
            cost, c, d, _ = heapq.heappop(heap)
            if best.get((c, d), float('inf')) < cost:
                continue
            if c in targets and c not in sources:
                return self._backtrack(parent, (c, d))
            straight_only = parent.get((c, d), (None, None, False))[2]
            for move in DIRECTIONS:
                if d is None and c in sources and sources[c] is not None and move not in sources[c]:
                    continue
                if d is not None and move == (-d[0], -d[1]):
                    continue
                if straight_only and move != d:
                    continue
                n = (c[0] + move[0], c[1] + move[1])
                if not (bx0 <= n[0] <= bx1 and by0 <= n[1] <= by1):
                    continue
                allowed, extra, straight = self._enterable(n, net, move, targets)
                if not allowed:
                    continue
                if n in sources:
                    continue
                step = STEP_COST + extra + (BEND_COST if d is not None and move != d else 0)
                state = (n, move)
                new = cost + step
                if new < best.get(state, float('inf')):
                    best[state] = new
                    parent[state] = ((c, d), move, straight)
                    counter += 1
                    heapq.heappush(heap, (new, n, move, counter))
        return None

    def _backtrack(self, parent, state):
        cells = [state[0]]
        while state in parent:
            state = parent[state][0]
            cells.append(state[0])
        cells.reverse()
        corners = [cells[0]]
        for i in range(1, len(cells) - 1):
            if (cells[i][0] - cells[i - 1][0], cells[i][1] - cells[i - 1][1]) != (cells[i + 1][0] - cells[i][0], cells[i + 1][1] - cells[i][1]):
                corners.append(cells[i])
        corners.append(cells[-1])
        return [point(c) for c in corners]


# --- normalisation -------------------------------------------------------------------------------------------------

@dataclass
class SheetWiring:
    """Drawn connectivity of one sheet: wires per net plus the points KiCad connects them to."""
    segments: list = field(default_factory=list)              # Segment
    pins: dict = field(default_factory=dict)                   # (ref, pad) -> dict(point, net)
    labels: list = field(default_factory=list)                 # dict(kind='global'|'hier'|'power'|'local', name, point)
    no_connects: list = field(default_factory=list)            # points
    junctions: list = field(default_factory=list)              # points (filled by normalise)
    problems: list = field(default_factory=list)


def normalise(w: SheetWiring) -> SheetWiring:
    """Split wires at same-net T-joins and pins, merge collinear corners, compute junctions; records problems."""
    pin_points = defaultdict(list)
    for key, info in w.pins.items():
        pin_points[info['point']].append((key, info['net']))
    label_points = {pt(*l['point']): l for l in w.labels}
    changed = True
    segments = list(w.segments)
    while changed:
        changed = False
        for i, seg in enumerate(segments):
            split_at = None
            for other in segments:
                if other is seg or other.net != seg.net:
                    continue
                for p in (other.a, other.b):
                    if interior(p, seg.a, seg.b):
                        split_at = p
                        break
                if split_at:
                    break
            if not split_at:
                for p, infos in pin_points.items():
                    if any(net == seg.net for _, net in infos) and interior(p, seg.a, seg.b):
                        split_at = p
                        break
            if not split_at:
                for p, label in label_points.items():
                    if not interior(p, seg.a, seg.b):
                        continue
                    # KiCad 10 connects a text label anywhere on a wire whatever its name (measured, adversarial case B): a
                    # label of another net on this wire's interior merges the nets, so the split is recorded as a problem.
                    # A power-symbol pin is a pin: it connects at a wire end or a junction only.
                    if label['kind'] in ('hier', 'global', 'local'):
                        if label['name'] != seg.net:
                            w.problems.append(dict(kind='label_on_other_net', net=label['name'], other=seg.net, at=p))
                        split_at = p
                        break
                    if label['kind'] == 'power' and label['name'] == seg.net:
                        split_at = p
                        break
            if split_at:
                segments[i:i + 1] = [Segment(seg.net, seg.a, split_at), Segment(seg.net, split_at, seg.b)]
                changed = True
                break
    # merge collinear pairs that meet end to end at a point with nothing else attached
    ends = defaultdict(list)
    for seg in segments:
        ends[seg.a].append(seg)
        ends[seg.b].append(seg)
    merged = True
    while merged:
        merged = False
        for p, segs in list(ends.items()):
            if len(segs) != 2 or p in pin_points or p in label_points:
                continue
            s1, s2 = segs
            if s1.net != s2.net or s1.axis != s2.axis or s1 is s2:
                continue
            far1 = s1.b if s1.a == p else s1.a
            far2 = s2.b if s2.a == p else s2.a
            new = Segment(s1.net, far1, far2)
            segments = [s for s in segments if s is not s1 and s is not s2] + [new]
            ends = defaultdict(list)
            for seg in segments:
                ends[seg.a].append(seg)
                ends[seg.b].append(seg)
            merged = True
            break
    w.segments = segments
    # junctions: >= 3 connections (wire ends + pins + power pins) at one point
    counts = defaultdict(int)
    for seg in segments:
        counts[seg.a] += 1
        counts[seg.b] += 1
    for p, infos in pin_points.items():
        counts[p] += len([1 for _, net in infos if net is not None])
    for p, label in label_points.items():
        if label['kind'] == 'power':
            counts[p] += 1
    w.junctions = sorted(p for p, n in counts.items() if n >= 3)
    # problems: a wire end on the interior of another net's wire, overlapping wires of different nets
    for seg in segments:
        for other in segments:
            if other is seg or other.net == seg.net:
                continue
            if interior(seg.a, other.a, other.b) or interior(seg.b, other.a, other.b):
                w.problems.append(dict(kind='end_on_other_net', net=seg.net, other=other.net, at=seg.a))
            if seg.axis == other.axis and (on_segment(seg.a, other.a, other.b) or on_segment(seg.b, other.a, other.b)
                                           or on_segment(other.a, seg.a, seg.b)):
                w.problems.append(dict(kind='overlap', net=seg.net, other=other.net, at=seg.a))
    return w


def trim_dangling(w: SheetWiring) -> int:
    """Remove wire segments with an end that touches nothing (no pin, label, junction or other wire); returns the count."""
    removed = 0
    pin_points = {pt(*i['point']) for i in w.pins.values() if i['net'] is not None}
    label_points = {pt(*l['point']) for l in w.labels}
    while True:
        ends = defaultdict(int)
        for seg in w.segments:
            ends[seg.a] += 1
            ends[seg.b] += 1
        junctions = set(pt(*j) for j in w.junctions)
        victim = None
        for seg in w.segments:
            for p in (seg.a, seg.b):
                touching = ends[p] > 1 or p in pin_points or p in label_points or p in junctions or \
                    any(interior(p, o.a, o.b) for o in w.segments if o is not seg and o.net == seg.net)
                if not touching:
                    victim = seg
                    break
            if victim:
                break
        if not victim:
            return removed
        w.segments.remove(victim)
        removed += 1


def crossings(segments: list) -> int:
    """Number of perpendicular segment pairs of different nets intersecting strictly inside both."""
    count = 0
    hs = [s for s in segments if s.axis == 'h']
    vs = [s for s in segments if s.axis == 'v']
    for h in hs:
        y = h.a[1]
        x0, x1 = sorted((h.a[0], h.b[0]))
        for v in vs:
            if v.net == h.net:
                continue
            x = v.a[0]
            y0, y1 = sorted((v.a[1], v.b[1]))
            if x0 + 1e-3 < x < x1 - 1e-3 and y0 + 1e-3 < y < y1 - 1e-3:
                count += 1
    return count


# --- connectivity (guard) -------------------------------------------------------------------------------------------

class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def connectivity(sheets: dict, root_pins: list, root_labels: list) -> dict:
    """{(ref, pad): name} implied by the drawn geometry of all sheets, with KiCad 10 coincidence rules.

    sheets: {sheet key: SheetWiring (normalised)}; root_pins: [dict(sheet, name, point)] sheet pins on the
    root; root_labels: [dict(name, point)] global labels on the root, root_wires optional via key '_root'.
    Rules: wire end == wire end, pin point == wire end (or a junction on a wire), junction connects every
    wire touching its point, labels and power pins connect at a wire end or on a wire interior, hierarchical
    labels connect to the root sheet pin of the same sheet and name, global labels and power Values connect
    by name across the project.  Text labels (global / hierarchical / local) also connect on a wire interior,
    whatever the wire's net (normalise() records a different net as 'label_on_other_net'); a power-symbol pin
    connects at a wire end or junction only.  A pin whose model net is None must carry a no_connect marker and
    touch nothing ('nc_missing' / 'nc_pin_connected' in dangling); no_connects = distinct markers drawn.  Returns dict(pads={(ref, pad): name}, unnamed=[...], multi_named=[...],
    dangling=[...], problems=[...]).
    """
    uf = UnionFind()
    names = defaultdict(set)
    dangling, problems = [], []
    for key, w in sheets.items():
        node = lambda p, key=key: ('pt', key, pt(*p))
        wire_cells = []
        for seg in w.segments:
            uf.union(node(seg.a), node(seg.b))
            wire_cells.append(seg)
        junction_set = set(pt(*j) for j in w.junctions)
        for j in junction_set:
            for seg in w.segments:
                if on_segment(j, seg.a, seg.b):
                    uf.union(node(j), node(seg.a))
        ends = set()
        for seg in w.segments:
            ends.add(seg.a)
            ends.add(seg.b)
        nc_points = {pt(*q) for q in w.no_connects}
        for (ref, pad), info in w.pins.items():
            p = pt(*info['point'])
            uf.union(('pad', ref, pad), node(p))
            if info['net'] is None:
                # an unconnected pin carries a no_connect marker and touches no wire, junction, label or other pin
                others = [k for k, i in w.pins.items() if k != (ref, pad) and pt(*i['point']) == p]
                if p in ends or p in junction_set or others or any(pt(*l['point']) == p for l in w.labels) or \
                        any(interior(p, s.a, s.b) for s in w.segments):
                    dangling.append(dict(sheet=key, ref=ref, pad=pad, at=p, kind='nc_pin_connected'))
                elif p not in nc_points:
                    dangling.append(dict(sheet=key, ref=ref, pad=pad, at=p, kind='nc_missing'))
                continue
            if p not in ends and p not in junction_set:
                if not any(l for l in w.labels if pt(*l['point']) == p):
                    dangling.append(dict(sheet=key, ref=ref, pad=pad, at=p, kind='pin_without_wire'))
        for label in w.labels:
            p = pt(*label['point'])
            at_pin = any(pt(*i['point']) == p for i in w.pins.values())
            touching = p in ends or p in junction_set or at_pin
            if label['kind'] != 'power':
                for s in w.segments:            # KiCad 10 connects a text label lying anywhere on a wire (not a power pin)
                    if interior(p, s.a, s.b):
                        uf.union(node(p), node(s.a))
                        touching = True
            if not touching:
                problems.append(dict(sheet=key, kind='label_dangling', name=label['name'], at=p))
            if label['kind'] in ('global', 'power'):
                uf.union(('name', label['name']), node(p))
                names[uf.find(node(p))].add(label['name'])
            elif label['kind'] == 'hier':
                uf.union(('hier', key, label['name']), node(p))
            elif label['kind'] == 'local':
                uf.union(('local', key, label['name']), node(p))
        for seg in w.segments:
            for p in (seg.a, seg.b):
                others = [s for s in w.segments if s is not seg and (s.a == p or s.b == p or (p in junction_set and on_segment(p, s.a, s.b)))]
                pins_here = [i for i in w.pins.values() if pt(*i['point']) == p]
                labels_here = [l for l in w.labels if pt(*l['point']) == p]
                if not others and not pins_here and not labels_here and p not in junction_set:
                    dangling.append(dict(sheet=key, net=seg.net, at=p, kind='wire_end'))
        problems.extend(dict(sheet=key, **pr) for pr in w.problems)
    for spin in root_pins:
        uf.union(('hier', spin['sheet'], spin['name']), ('pt', '_root', pt(*spin['point'])))
    for label in root_labels:
        uf.union(('name', label['name']), ('pt', '_root', pt(*label['point'])))
    root_wiring = sheets.get('_root')
    # names per component
    component_names = defaultdict(set)
    for item in list(uf.parent):
        if item[0] == 'name':
            component_names[uf.find(item)].add(item[1])
    pads, unnamed, multi = {}, [], []
    for key, w in sheets.items():
        for (ref, pad), info in w.pins.items():
            if info['net'] is None:
                continue
            root = uf.find(('pad', ref, pad))
            found = sorted(component_names.get(root, ()))
            if len(found) == 1:
                pads[(ref, pad)] = found[0]
            elif not found:
                unnamed.append(dict(ref=ref, pad=pad, sheet=key, expected=info['net']))
            else:
                multi.append(dict(ref=ref, pad=pad, sheet=key, names=found))
    no_connects = sum(len({pt(*q) for q in w.no_connects}) for w in sheets.values())
    return dict(pads=pads, unnamed=unnamed, multi_named=multi, dangling=dangling, problems=problems, no_connects=no_connects)


def compare_with_model(derived: dict, parts: list) -> dict:
    """Compare connectivity() output with the model's (ref, pad) -> net; returns dict(identical, mismatches, ...)."""
    expected = {(p['ref'], str(pad)): net for p in parts for pad, net in p['nets'].items() if net is not None}
    pads = derived['pads']
    mismatches = [dict(ref=r, pad=p, model=expected.get((r, p)), drawn=pads.get((r, p)))
                  for r, p in sorted(set(expected) | set(pads)) if expected.get((r, p)) != pads.get((r, p))]
    nc_expected = sum(1 for p in parts for net in p['nets'].values() if net is None)
    nc_drawn = derived.get('no_connects')
    nc_ok = nc_drawn is None or nc_drawn == nc_expected
    identical = not mismatches and not derived['unnamed'] and not derived['multi_named'] and not derived['dangling'] \
        and not derived['problems'] and nc_ok
    return dict(identical=identical, pads_checked=len(expected), mismatches=mismatches[:50], mismatch_count=len(mismatches),
                no_connects=dict(expected=nc_expected, drawn=nc_drawn),
                unnamed=derived['unnamed'][:50], multi_named=derived['multi_named'][:50], dangling=derived['dangling'][:50],
                problems=derived['problems'][:50])
