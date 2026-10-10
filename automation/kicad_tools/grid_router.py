"""Reusable grid router for AI-directed KiCad routing (generalised from route_buck.py).

The V1 ``Router`` in ``route_buck.py`` was written for one 300 x 220 mm six-layer
board. This module keeps its proven mechanics (int16 occupancy cells, inflated
pad/track/via marking, 4-neighbour A* with via transitions, pad escape fanout,
greedy spanning connection, FULL-connection zones, SaveBoard then LoadBoard) and
makes board size, grid pitch, layer list, trace/clearance/via sizes, per-net
rules, keepouts and the routing order explicit. ``run_plan`` executes a
declarative plan dict so a board script is mostly data.

Deterministic: grid sizing, pad/track/via occupancy, A* search (heap with stable
tie-breaking), path compression, fanout candidate order, connection order, the
plan validation and the report. The same board and plan give the same geometry
(same multiset of segments, vias, zones and fills); only the item order inside
the saved ``.kicad_pcb`` follows the random KIIDs, so compare geometry, not bytes.

Requires native KiCad checks: pcbnew assigns fresh KIIDs to every new item; pads
are modelled by bounding boxes and clearances by inflated discs, so clearance,
hole-to-hole, copper-to-edge, annular-ring, zone-fill and connectivity results
must come from ``kicad-cli pcb drc`` (``automation.kicad_tools.run_check``) and
engineering review. A zero ``unresolved`` list is a geometric proposal, not DRC.

Only ``Router`` and ``run_plan`` import pcbnew; ``Grid`` and the helpers need
numpy alone so they can be unit-tested with the host interpreter.
"""
from __future__ import annotations

import heapq
import math
import re
import time
from collections import defaultdict

import numpy as np

EPS = 0.01
ESCAPE_DISTANCES = (0.65, 1.25, 1.9, 2.65, 3.5, 4.5, 6.0)
ESCAPE_SHIFTS = (0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2, -2)
PLAN_KEYS = {'board', 'layers', 'grid', 'trace', 'clearance', 'via', 'hole_clearance', 'directions',
             'net_rules', 'keepouts', 'pre_routed', 'critical', 'critical_layers', 'power', 'fanout',
             'signal_order', 'signal_layers', 'exclude_nets', 'front_fallback', 'ground', 'prune_vias',
             'fill', 'save', 'strict', 'max_nodes'}


def grid_shape(width_mm, height_mm, grid=0.25):
    """Return (nx, ny) cell counts covering a width x height board at the grid pitch."""
    if width_mm <= 0 or height_mm <= 0 or grid <= 0:
        raise ValueError('board size and grid pitch must be positive')
    return int(round(width_mm / grid)) + 1, int(round(height_mm / grid)) + 1


def default_directions(layer_count):
    """Preferred direction per layer index: outer layers free, inner layers alternate 'h'/'v'."""
    directions = [None] * layer_count
    for i, layer in enumerate(range(1, layer_count - 1)):
        directions[layer] = 'h' if i % 2 == 0 else 'v'
    return directions


def dilate(mask, radius_cells):
    """Binary dilation of a bool array by a disc of ceil(radius_cells) cells (numpy only)."""
    r = int(math.ceil(radius_cells - 1e-9)) if radius_cells > 0 else 0
    out = mask.copy()
    if r <= 0 or not mask.any():
        return out
    ny, nx = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r or (dx == 0 and dy == 0):
                continue
            out[max(0, dy):ny + min(0, dy), max(0, dx):nx + min(0, dx)] |= \
                mask[max(0, -dy):ny + min(0, -dy), max(0, -dx):nx + min(0, -dx)]
    return out


def compress_path(path):
    """Turn an A* node list into (segments, vias): (x0,y0,x1,y1,layer) runs and via cells."""
    segments, vias = [], []
    if len(path) < 2:
        return segments, vias
    first = last = path[0]
    direction = None
    for node in path[1:]:
        delta = (node[0] - last[0], node[1] - last[1])
        if node[2] != last[2]:
            if (first[0], first[1]) != (last[0], last[1]):
                segments.append((first[0], first[1], last[0], last[1], last[2]))
            vias.append((last[0], last[1]))
            first = node
            direction = None
        elif direction is not None and delta != direction:
            segments.append((first[0], first[1], last[0], last[1], last[2]))
            first = last
            direction = delta
        else:
            direction = delta
        last = node
    if (first[0], first[1]) != (last[0], last[1]):
        segments.append((first[0], first[1], last[0], last[1], last[2]))
    return segments, vias


def pad_sort_key(number):
    """Sort pad numbers numerically when possible ('2' before '10', letters last)."""
    text = str(number or '')
    return (0, int(text), '') if text.isdigit() else (1, 0, text)


def natural_ref_key(ref):
    """Sort references naturally: C2 before C10, and by prefix first."""
    match = re.match(r'([A-Za-z#_]*)(\d*)(.*)', str(ref))
    prefix, digits, rest = match.groups()
    return (prefix, int(digits) if digits else -1, rest)


class Grid:
    """Occupancy model: a cell holds 0 (free), a net code (that net may use it) or -1 (blocked).

    ``occ[layer]`` is copper occupancy per routing layer, ``vocc`` via-centre occupancy,
    ``holes`` drill exclusion (hole-to-hole) and ``transitions`` plated through pads that
    change layers without a new via. Coordinates are grid cells; ``origin`` and ``grid``
    map them to board millimetres.
    """

    def __init__(self, nx, ny, layer_count, grid=0.25, margin_cells=4, origin=(0.0, 0.0), directions=None):
        if nx < 3 or ny < 3 or layer_count < 1 or grid <= 0:
            raise ValueError('grid needs at least 3 x 3 cells, one layer and a positive pitch')
        self.nx, self.ny, self.nl, self.grid = int(nx), int(ny), int(layer_count), float(grid)
        self.ox, self.oy = float(origin[0]), float(origin[1])
        self.margin = max(0, int(margin_cells))
        self.directions = list(directions) if directions is not None else default_directions(self.nl)
        self.occ = np.zeros((self.nl, self.ny, self.nx), dtype=np.int16)
        self.vocc = np.zeros((self.ny, self.nx), dtype=np.int16)
        self.holes = np.zeros((self.ny, self.nx), dtype=np.int16)
        self.transitions = np.zeros((self.ny, self.nx), dtype=np.int16)
        m = self.margin
        if m:
            self.occ[:, :m, :] = -1; self.occ[:, -m:, :] = -1; self.occ[:, :, :m] = -1; self.occ[:, :, -m:] = -1
            self.vocc[:m, :] = -1; self.vocc[-m:, :] = -1; self.vocc[:, :m] = -1; self.vocc[:, -m:] = -1

    def to_grid(self, x, y):
        """Nearest cell for a board coordinate in mm."""
        return round((x - self.ox) / self.grid), round((y - self.oy) / self.grid)

    def to_mm(self, gx, gy):
        """Board coordinate in mm of a cell."""
        return (self.ox + gx * self.grid, self.oy + gy * self.grid)

    def inside(self, x, y):
        """True when the cell lies inside the routable area (outside the margin frame)."""
        m = self.margin
        return m <= x <= self.nx - 1 - m and m <= y <= self.ny - 1 - m

    @staticmethod
    def merge(view, mask, code):
        """Mark masked cells with ``code``; cells already owned by another code become -1."""
        view[mask & (view != 0) & (view != code)] = -1
        view[mask & (view == 0)] = code

    def box(self, array, bb, inflate, code):
        """Mark the axis-aligned mm box ``bb`` = (x0, y0, x1, y1) inflated by ``inflate`` mm."""
        g = self.grid
        x0 = max(0, math.ceil((bb[0] - inflate - self.ox) / g)); x1 = min(self.nx - 1, math.floor((bb[2] + inflate - self.ox) / g))
        y0 = max(0, math.ceil((bb[1] - inflate - self.oy) / g)); y1 = min(self.ny - 1, math.floor((bb[3] + inflate - self.oy) / g))
        if x0 > x1 or y0 > y1:
            return
        view = array[y0:y1 + 1, x0:x1 + 1]
        self.merge(view, np.ones(view.shape, dtype=bool), code)

    def segment(self, array, a, b, radius, code):
        """Mark every cell within ``radius`` mm of the mm segment a-b (a == b marks a disc)."""
        g = self.grid
        x0 = max(0, math.ceil((min(a[0], b[0]) - radius - self.ox) / g)); x1 = min(self.nx - 1, math.floor((max(a[0], b[0]) + radius - self.ox) / g))
        y0 = max(0, math.ceil((min(a[1], b[1]) - radius - self.oy) / g)); y1 = min(self.ny - 1, math.floor((max(a[1], b[1]) + radius - self.oy) / g))
        if x0 > x1 or y0 > y1:
            return
        xx, yy = np.meshgrid(self.ox + np.arange(x0, x1 + 1) * g, self.oy + np.arange(y0, y1 + 1) * g)
        dx, dy = b[0] - a[0], b[1] - a[1]
        den = dx * dx + dy * dy
        t = np.clip(((xx - a[0]) * dx + (yy - a[1]) * dy) / (den or 1), 0, 1)
        mask = (xx - a[0] - t * dx) ** 2 + (yy - a[1] - t * dy) ** 2 < radius ** 2 - 1e-9
        self.merge(array[y0:y1 + 1, x0:x1 + 1], mask, code)

    def via_ok(self, x, y, code):
        """Plain via check: inside, no nearby drill and the via cell free or owned by ``code``."""
        return self.inside(x, y) and self.holes[y, x] == 0 and int(self.vocc[y, x]) in (0, code)

    def astar(self, start, end, code, layers, max_nodes=700000, margin=None, extra=0.0, via_extra=0.0,
              transition=None, via_cost=8):
        """4-neighbour A* over (x, y, layer) cells for net ``code``.

        ``start``/``end`` are (x, y, layer); a ``None`` layer means any layer in
        ``layers`` (plated through pads). Planar steps cost 1.0 along a layer's
        preferred direction, else 1.15; a layer change costs ``via_cost`` and needs
        ``transition(x, y)`` or a free via cell. ``extra``/``via_extra`` (cells) dilate
        other-net occupancy for nets wider or with more clearance than the defaults.
        ``margin`` limits the search window around the endpoints. Returns the node
        list or None when no path exists within ``max_nodes`` expansions.
        """
        nx, ny = self.nx, self.ny
        occ, vocc, holes = self.occ, self.vocc, self.holes
        sx, sy, sl = start; ex, ey, el = end
        layers = tuple(layers)
        if sl is None and not layers:
            raise ValueError('a start without a layer needs at least one routing layer')
        m = self.margin
        if margin is not None:
            xmin = max(m, min(sx, ex) - margin); xmax = min(nx - 1 - m, max(sx, ex) + margin)
            ymin = max(m, min(sy, ey) - margin); ymax = min(ny - 1 - m, max(sy, ey) + margin)
        else:
            xmin, xmax, ymin, ymax = m, nx - 1 - m, m, ny - 1 - m
        transition = transition or (lambda x, y: int(self.transitions[y, x]) == code)
        if extra > 0 or via_extra > 0:
            needed = set(layers) | {l for l in (sl, el) if l is not None}
            blocked = {l: dilate((occ[l] != 0) & (occ[l] != code), extra) for l in needed}
            vblocked = dilate((vocc != 0) & (vocc != code), via_extra) | (holes != 0)
            def free(l, x, y): return l in blocked and not blocked[l][y, x]
            def via_ok(x, y): return transition(x, y) or not vblocked[y, x]
        else:
            def free(l, x, y): return int(occ[l, y, x]) in (0, code)
            def via_ok(x, y): return transition(x, y) or (holes[y, x] == 0 and int(vocc[y, x]) in (0, code))
        directions = self.directions
        inf = math.inf

        def h(x, y, l): return abs(ex - x) + abs(ey - y) + (0 if el is None or l == el else 5)
        def enc(x, y, l): return (l * ny + y) * nx + x
        def dec(k): return (k % nx, (k // nx) % ny, k // (nx * ny))
        heap, costs, parent = [], {}, {}
        for l in (layers if sl is None else (sl,)):
            k = enc(sx, sy, l); costs[k] = 0; heapq.heappush(heap, (h(sx, sy, l), 0, k))
        expanded = 0
        while heap:
            _, cost, k = heapq.heappop(heap)
            if cost != costs.get(k):
                continue
            x, y, l = dec(k)
            if x == ex and y == ey and (el is None or l == el):
                path = [(x, y, l)]
                while k in parent:
                    k = parent[k]; path.append(dec(k))
                path.reverse()
                return path
            expanded += 1
            if expanded > max_nodes:
                return None
            pref = directions[l] if l < len(directions) else None
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if not (xmin <= xx <= xmax and ymin <= yy <= ymax) or not free(l, xx, yy):
                    continue
                step = 1.0 if pref is None or (pref == 'h' and dy == 0) or (pref == 'v' and dx == 0) else 1.15
                nc = cost + step; nk = enc(xx, yy, l)
                if nc < costs.get(nk, inf):
                    costs[nk] = nc; parent[nk] = k; heapq.heappush(heap, (nc + h(xx, yy, l), nc, nk))
            if len(layers) > 1 and via_ok(x, y):
                for ll in layers:
                    if ll == l or not free(ll, x, y):
                        continue
                    nk = enc(x, y, ll); nc = cost + via_cost
                    if nc < costs.get(nk, inf):
                        costs[nk] = nc; parent[nk] = k; heapq.heappush(heap, (nc + h(x, y, ll), nc, nk))
        return None


class Router:
    """Grid router bound to an open pcbnew BOARD.

    ``layers`` lists the pcbnew copper layer ids (or names) used for routing, in
    order: index 0 is the component/front layer, the last index the back layer.
    Track methods take these *indices*; ``zone`` and keepouts take layer names or
    pcbnew ids. ``net_rules`` maps a net name to ``dict(width=, clearance=)``
    overrides (also accepts ``critical``/``power`` flags). ``keepouts`` are
    ``(layer_index_or_None, x0, y0, x1, y1, net_code_or_-1[, block_vias])`` mm boxes;
    a net name may replace the code. ``critical`` nets stay on the front layer and
    never fall back; ``power`` nets never fall back to the front layer and keep
    their vias when pruning. Existing tracks and vias on the board are registered
    as occupancy so routing can be incremental. All vias are through vias.
    """

    def __init__(self, board, width_mm, height_mm, layers, grid=0.25, trace=0.2, clearance=0.2, via=(0.6, 0.3),
                 net_rules=None, keepouts=None, board_margin=1.0, origin=(0.0, 0.0), critical=(), power=(),
                 hole_clearance=0.25, directions=None, max_nodes=700000):
        import pcbnew as pcb
        self.pcb, self.board = pcb, board
        self.width, self.height = float(width_mm), float(height_mm)
        self.trace, self.clearance = float(trace), float(clearance)
        self.via_d, self.via_drill = float(via[0]), float(via[1])
        self.hole_clearance = float(hole_clearance); self.max_nodes = int(max_nodes)
        self.net_rules = {k: dict(v) for k, v in (net_rules or {}).items()}
        self.critical = set(critical) | {n for n, r in self.net_rules.items() if r.get('critical')}
        self.power = set(power) | {n for n, r in self.net_rules.items() if r.get('power')}
        copper = list(board.GetEnabledLayers().CuStack())
        self.layers = [self.layer_id(l) for l in layers]
        if not self.layers or len(set(self.layers)) != len(self.layers) or any(l not in copper for l in self.layers):
            raise ValueError(f'routing layers must be distinct enabled copper layers: {list(layers)}')
        self.names = [board.GetLayerName(l) for l in self.layers]
        self.nl = len(self.layers)
        nx, ny = grid_shape(width_mm, height_mm, grid)
        self.grid = Grid(nx, ny, self.nl, grid, max(1, math.ceil(board_margin / grid - 1e-9)), origin, directions)
        self.escape_distances, self.escape_shifts = ESCAPE_DISTANCES, ESCAPE_SHIFTS
        self.nets = {n.GetNetname(): n for n in board.GetNetInfo().NetsByNetcode().values() if n.GetNetCode()}
        self.code = {name: net.GetNetCode() for name, net in self.nets.items()}
        self.ports = defaultdict(list); self.pad_records = []; self.stats = defaultdict(int)
        self.length = defaultdict(float); self.unresolved = []; self.vias = {}; self.through = []
        self._register_pads()
        for keepout in keepouts or ():
            self.keepout(*keepout)
        self._register_existing()

    # ----- helpers -------------------------------------------------------------------------
    def layer_id(self, layer):
        """pcbnew layer id for a layer name or id (names are looked up on the board)."""
        if isinstance(layer, str):
            found = self.board.GetLayerID(layer)
            if found < 0:
                raise ValueError(f'unknown layer name {layer!r}')
            return found
        return int(layer)

    def layer_index(self, layer):
        """Routing index (position in ``layers``) of a layer name; raises for unrouted layers."""
        if not isinstance(layer, str):
            raise TypeError('layer_index takes a layer name; routing methods already take indices')
        if layer not in self.names:
            raise ValueError(f'{layer!r} is not a routing layer {self.names}')
        return self.names.index(layer)

    def point(self, x, y):
        """pcbnew VECTOR2I for a board coordinate in mm."""
        return self.pcb.VECTOR2I(self.pcb.FromMM(x), self.pcb.FromMM(y))

    def to_grid(self, x, y):
        """Nearest grid cell for a board coordinate in mm."""
        return self.grid.to_grid(x, y)

    def to_mm(self, gx, gy):
        """Board coordinate in mm of a grid cell."""
        return self.grid.to_mm(gx, gy)

    def width_for(self, net):
        """Track width for ``net`` (net rule or default trace width)."""
        return float(self.net_rules.get(net, {}).get('width', self.trace))

    def clearance_for(self, net):
        """Clearance used when marking copper of ``net`` (never below the default)."""
        return max(float(self.net_rules.get(net, {}).get('clearance', self.clearance)), self.clearance)

    def extra_for(self, net):
        """(track, via) extra radius in mm that ``net`` needs beyond the default marking."""
        more = self.clearance_for(net) - self.clearance
        return max(0.0, (self.width_for(net) - self.trace) / 2) + more, more

    def is_critical(self, net):
        """True when ``net`` must stay on the component layer."""
        return net in self.critical

    def is_power(self, net):
        """True when ``net`` is a zone/power net (no front fallback; vias kept)."""
        return net in self.power

    def net_code(self, net):
        """Net code of a board net; raises for unknown names."""
        try:
            return self.code[net]
        except KeyError:
            raise ValueError(f'net {net!r} is not on the board') from None

    def default_layers(self, net):
        """Default routing layer indices: front + back for critical nets, else every layer but the front."""
        if self.nl == 1:
            return (0,)
        return (0, self.nl - 1) if self.is_critical(net) else tuple(range(1, self.nl))

    def _key(self, xy):
        return (round(xy[0], 4), round(xy[1], 4))

    def _register_pads(self):
        pcb = self.pcb
        g = self.grid
        for fp in self.board.GetFootprints():
            for pad in fp.Pads():
                net = pad.GetNetname(); code = pad.GetNetCode() or -1
                pos = tuple(pcb.ToMM(pad.GetPosition())); bb = pad.GetBoundingBox()
                box = [pcb.ToMM(bb.GetX()), pcb.ToMM(bb.GetY()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())]
                thru = pad.GetAttribute() in (pcb.PAD_ATTRIB_PTH, pcb.PAD_ATTRIB_NPTH)
                on = [i for i, layer in enumerate(self.layers) if pad.IsOnLayer(layer)]
                if not thru and not on:
                    continue
                clearance = self.clearance_for(net) if code > 0 else self.clearance
                if thru:
                    self.through.append((pad, net))
                    drill = pcb.ToMM(pad.GetDrillSize())
                    g.box(g.holes, [pos[0] - drill[0] / 2, pos[1] - drill[1] / 2, pos[0] + drill[0] / 2, pos[1] + drill[1] / 2],
                          self.hole_clearance + self.via_drill / 2 + 2 * EPS, -1)
                    if pad.GetAttribute() == pcb.PAD_ATTRIB_PTH:
                        g.segment(g.transitions, pos, pos, min(pcb.ToMM(pad.GetSize())) / 2 - 0.15, code)
                for layer in (range(self.nl) if thru else on):
                    g.box(g.occ[layer], box, clearance + self.trace / 2, code)
                g.box(g.vocc, box, clearance + self.via_d / 2, code)
                self.pad_records.append(dict(fp=fp, pad=pad, ref=fp.GetReference(), number=pad.GetNumber(), net=net, code=code,
                                             xy=pos, box=box, thru=thru, layers=on, side=0 if (thru or 0 in on) else on[-1]))

    def _register_existing(self):
        pcb = self.pcb
        for item in list(self.board.GetTracks()):
            net = item.GetNetname()
            if not net or net not in self.code:
                continue
            if isinstance(item, pcb.PCB_VIA):
                xy = tuple(pcb.ToMM(item.GetPosition()))
                if self._key(xy) in self.vias:
                    continue
                self._mark_via(xy, net, pcb.ToMM(item.GetWidth(pcb.F_Cu)), pcb.ToMM(item.GetDrillValue()))  # KiCad 10: via width needs a layer
            elif item.GetLayer() in self.layers:
                a, b = tuple(pcb.ToMM(item.GetStart())), tuple(pcb.ToMM(item.GetEnd()))
                self._mark_track(a, b, net, self.layers.index(item.GetLayer()), pcb.ToMM(item.GetWidth()))

    def keepout(self, layer, x0, y0, x1, y1, net=-1, block_vias=False):
        """Reserve a mm box on one routing layer index (or every layer when None) for ``net``.

        ``net`` is a net code, a net name or -1 (blocked for everyone). With
        ``block_vias`` the box also rejects via centres.
        """
        code = self.net_code(net) if isinstance(net, str) else (-1 if net is None else int(net))
        if isinstance(layer, str):
            layer = self.layer_index(layer)
        for index in (range(self.nl) if layer is None else (int(layer),)):
            self.grid.box(self.grid.occ[index], [x0, y0, x1, y1], 0, code)
        if block_vias:
            self.grid.box(self.grid.vocc, [x0, y0, x1, y1], 0, code)

    # ----- copper creation -------------------------------------------------------------------
    def _mark_track(self, a, b, net, layer, width):
        g = self.grid; code = self.code[net]; clearance = self.clearance_for(net)
        g.segment(g.occ[layer], a, b, width / 2 + clearance + self.trace / 2 + EPS, code)
        g.segment(g.vocc, a, b, width / 2 + clearance + self.via_d / 2 + EPS, code)
        self.length[net] += math.dist(a, b)

    def _mark_via(self, xy, net, diameter, drill):
        g = self.grid; code = self.code[net]; clearance = self.clearance_for(net)
        for layer in range(self.nl):
            g.segment(g.occ[layer], xy, xy, diameter / 2 + clearance + self.trace / 2 + EPS, code)
        g.segment(g.vocc, xy, xy, diameter / 2 + clearance + self.via_d / 2 + EPS, code)
        g.segment(g.holes, xy, xy, drill / 2 + self.hole_clearance + self.via_drill / 2 + 2 * EPS, -1)
        self.vias[self._key(xy)] = net

    def track(self, a, b, net, layer_index, width=None):
        """Add a straight track (mm endpoints) on a routing layer index; returns the PCB_TRACK or None.

        The width defaults to the net rule. Occupancy is inflated by the net's
        clearance plus half the default trace so other nets keep their distance.
        """
        if math.dist(a, b) < 1e-6:
            return None
        width = self.width_for(net) if width is None else float(width)
        pcb = self.pcb
        item = pcb.PCB_TRACK(self.board)
        item.SetStart(self.point(*a)); item.SetEnd(self.point(*b)); item.SetWidth(pcb.FromMM(width))
        item.SetLayer(self.layers[layer_index]); item.SetNet(self.nets[net]); self.board.Add(item)
        self._mark_track(a, b, net, layer_index, width)
        self.stats['tracks'] += 1
        return item

    def via(self, xy, net, diameter=None, drill=None):
        """Add a through via at ``xy`` (mm) unless a same-net transition already exists there.

        Returns the PCB_VIA, or None when an existing via or plated pad of the net
        already provides the layer change.
        """
        if self.existing_transition(xy, net):
            return None
        diameter = self.via_d if diameter is None else float(diameter)
        drill = self.via_drill if drill is None else float(drill)
        pcb = self.pcb
        item = pcb.PCB_VIA(self.board)
        item.SetPosition(self.point(*xy)); item.SetWidth(pcb.FromMM(diameter)); item.SetDrill(pcb.FromMM(drill))
        item.SetLayerPair(pcb.F_Cu, pcb.B_Cu); item.SetViaType(pcb.VIATYPE_THROUGH); item.SetNet(self.nets[net])
        self.board.Add(item)
        self._mark_via(tuple(xy), net, diameter, drill)
        self.stats['vias'] += 1
        return item

    def existing_transition(self, xy, net):
        """True when a via or plated through pad of ``net`` already covers ``xy`` (mm).

        Plated pads count only within their inscribed circle (minus 0.15 mm) so a
        skipped via really lands on copper of that pad.
        """
        if self.vias.get(self._key(xy)) == net:
            return True
        gx, gy = self.to_grid(*xy)
        mx, my = self.to_mm(gx, gy)
        if abs(mx - xy[0]) + abs(my - xy[1]) < 1e-6 and 0 <= gx < self.grid.nx and 0 <= gy < self.grid.ny:
            return int(self.grid.transitions[gy, gx]) == self.code.get(net, 0)
        pcb = self.pcb
        return any(name == net and pad.GetAttribute() == pcb.PAD_ATTRIB_PTH
                   and math.dist(xy, pcb.ToMM(pad.GetPosition())) <= min(pcb.ToMM(pad.GetSize())) / 2 - 0.15
                   for pad, name in self.through)

    def via_allowed(self, x, y, net):
        """True when ``net`` may place (or reuse) a via at grid cell (x, y), honouring its clearance rule."""
        g = self.grid
        if not g.inside(x, y):
            return False
        if self.existing_transition(self.to_mm(x, y), net):
            return True
        code = self.code[net]
        if g.holes[y, x] != 0:
            return False
        r = int(math.ceil(self.extra_for(net)[1] / g.grid - 1e-9))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy > r * r:
                    continue
                xx, yy = x + dx, y + dy
                if 0 <= xx < g.nx and 0 <= yy < g.ny and int(g.vocc[yy, xx]) not in (0, code):
                    return False
        return True

    def astar(self, start, end, net, layers=None, max_nodes=None, margin=None):
        """Grid A* for ``net`` between (x, y, layer_index) cells; see ``Grid.astar``.

        ``layers`` are routing indices allowed for layer changes (default:
        ``default_layers``); ``max_nodes`` defaults to the router's budget; the
        net's width/clearance rule sets the dilation.
        """
        layers = self.default_layers(net) if layers is None else tuple(layers)
        max_nodes = self.max_nodes if max_nodes is None else int(max_nodes)
        extra, via_extra = self.extra_for(net)
        g = self.grid
        return g.astar(start, end, self.net_code(net), layers, max_nodes=max_nodes, margin=margin,
                       extra=extra / g.grid, via_extra=via_extra / g.grid,
                       transition=lambda x, y: self.existing_transition(self.to_mm(x, y), net))

    def emit(self, path, net):
        """Realise an A* path as tracks (net rule width) and through vias."""
        segments, vias = compress_path(path)
        for x0, y0, x1, y1, layer in segments:
            self.track(self.to_mm(x0, y0), self.to_mm(x1, y1), net, layer)
        for x, y in vias:
            self.via(self.to_mm(x, y), net)

    # ----- routing stages --------------------------------------------------------------------
    @staticmethod
    def default_order_key(record):
        """Fanout order: ICs first, then natural reference order and pad number."""
        return (0 if record['ref'].startswith('U') else 1, natural_ref_key(record['ref']), pad_sort_key(record['number']))

    def fanout(self, order_key=None, skip=None, inpad_vias=(), inward=None, escape_layer=None):
        """Escape every connected pad to a routing port; returns ``[ref, pad, net]`` failures.

        Through-hole pads register a port with layer None (reachable on every
        routing layer). Pads of critical nets register on their own layer without
        a via. Other SMD pads get a short escape on their layer to a via whose port
        is on ``escape_layer`` (default: the next inner layer; the back side mirrors).
        ``(ref, pad)`` pairs in ``inpad_vias`` get the via in the pad centre
        (thermal pads). ``skip(record)`` excludes pads, ``inward(record)`` prefers an
        escape towards the footprint centre (dense packages), ``order_key(record)``
        sets the pad order.
        """
        skip = skip or (lambda record: False); inward = inward or (lambda record: False)
        inpad = {tuple(p) for p in inpad_vias}
        failures = []
        g = self.grid
        for r in sorted(self.pad_records, key=order_key or self.default_order_key):
            net, ref, number = r['net'], r['ref'], r['number']
            if not net or net.startswith('unconnected-') or r['code'] <= 0 or skip(r):
                continue
            x, y = r['xy']; sx, sy = self.to_grid(x, y); side = r['side']
            if r['thru']:
                self.ports[net].append((sx, sy, None, ref, number)); continue
            if self.is_critical(net) or self.nl == 1:
                self.ports[net].append((sx, sy, side, ref, number)); continue
            port_layer = escape_layer if escape_layer is not None else (1 if side == 0 else self.nl - 2)
            if (ref, number) in inpad:
                xy = self.to_mm(sx, sy); self.via(xy, net); self.track((x, y), xy, net, side)
                self.ports[net].append((sx, sy, port_layer, ref, number)); continue
            cx, cy = self.pcb.ToMM(r['fp'].GetPosition())
            dx, dy = x - cx, y - cy
            if abs(dx) >= abs(dy):
                ux, uy = (1 if dx >= 0 else -1), 0
            else:
                ux, uy = 0, (1 if dy >= 0 else -1)
            extent = (r['box'][2] - r['box'][0]) / 2 if ux else (r['box'][3] - r['box'][1]) / 2
            primary = -1 if inward(r) else 1
            candidates = []
            for sign in (primary, -primary):
                for distance in self.escape_distances:
                    for shift in self.escape_shifts:
                        reach = extent + distance
                        ex, ey = self.to_grid(x + sign * ux * reach - uy * shift, y + sign * uy * reach + ux * shift)
                        if not g.inside(ex, ey) or not self.via_allowed(ex, ey, net):
                            continue
                        if any(int(g.occ[l, ey, ex]) not in (0, r['code']) for l in range(self.nl)):
                            continue
                        candidates.append((distance + abs(shift) * 1.4 + (10 if sign != primary else 0), ex, ey))
            routed = False
            for _, ex, ey in sorted(set(candidates)):
                path = self.astar((sx, sy, side), (ex, ey, side), net, layers=(side,), max_nodes=1500, margin=10)
                if path is None:
                    continue
                self.track((x, y), self.to_mm(sx, sy), net, side); self.emit(path, net); self.via(self.to_mm(ex, ey), net)
                self.ports[net].append((ex, ey, port_layer, ref, number)); routed = True
                break
            if not routed:
                failures.append([ref, number, net])
                self.unresolved.append(dict(stage='fanout', ref=ref, pad=number, net=net))
        self.stats['fanout_unresolved'] += len(failures)
        return failures

    def route_net(self, net, ports=None, layers=None, allow_front_fallback=True):
        """Connect the ports of ``net`` with a greedy nearest-first spanning set of A* paths.

        ``ports`` default to the fanout ports; ``layers`` to ``default_layers``.
        Critical nets are forced to the front layer. When a path fails and the net
        is neither critical nor power, ``allow_front_fallback`` retries on every
        layer. Returns the failure records (also appended to ``unresolved``).
        """
        ports = list(self.ports.get(net, []) if ports is None else ports)
        layers = tuple(self.default_layers(net) if layers is None else layers)
        critical = self.is_critical(net)
        def resolve(p):
            layer = 0 if critical else p[2]
            return (p[0], p[1], layers[0] if layer is None else layer)
        points = list(dict.fromkeys(resolve(p) for p in ports))
        if len(points) < 2:
            return []
        connected = [points.pop(0)]; failures = []
        g = self.grid
        while points:
            _, a, b = min((abs(a[0] - b[0]) + abs(a[1] - b[1]), a, b) for a in connected for b in points)
            path = self.astar(a, b, net, layers=layers)
            if path is None and allow_front_fallback and not critical and not self.is_power(net):
                path = self.astar(a, b, net, layers=tuple(range(self.nl)))
            if path is None:
                record = dict(stage='route', net=net, start=a, end=b,
                              occupancy=dict(start=int(g.occ[a[2], a[1], a[0]]), end=int(g.occ[b[2], b[1], b[0]]), code=self.code[net]))
                failures.append(record); self.unresolved.append(record); points.remove(b)
                continue
            self.emit(path, net); connected.append(b); points.remove(b)
        return failures

    def route_power_stub(self, net, anchors, ports, layers=None):
        """Connect each port of a power net to its nearest anchor port (manhattan, grid cells)."""
        anchors = list(anchors); failures = []
        if not anchors:
            record = dict(stage='power_stub', net=net, error='no anchors', ports=len(list(ports)))
            self.unresolved.append(record)
            return [record]
        for port in ports:
            anchor = min(anchors, key=lambda p: (abs(port[0] - p[0]) + abs(port[1] - p[1]), p[0], p[1]))
            failures.extend(self.route_net(net, [anchor, port], layers=layers))
        return failures

    # ----- zones ------------------------------------------------------------------------------
    def zone(self, net, layer, points, priority=1, clearance=0.5, min_thickness=0.2, thermal_relief=False,
             keepout_hole_polygons=None):
        """Add a filled copper zone for ``net`` on a layer name or pcbnew id with an mm polygon.

        Pads connect solid unless ``thermal_relief``; islands are always removed.
        ``keepout_hole_polygons`` cuts polygon holes (list of point lists). The fill
        itself happens in ``fill()``.
        """
        pcb = self.pcb
        z = pcb.ZONE(self.board)
        z.SetNet(self.nets[net]); z.SetLayer(self.layer_id(layer)); z.SetAssignedPriority(int(priority))
        z.SetLocalClearance(pcb.FromMM(clearance)); z.SetMinThickness(pcb.FromMM(min_thickness))
        z.SetIslandRemovalMode(pcb.ISLAND_REMOVAL_MODE_ALWAYS)
        if thermal_relief:
            z.SetPadConnection(pcb.ZONE_CONNECTION_THERMAL)
            z.SetThermalReliefGap(pcb.FromMM(0.5)); z.SetThermalReliefSpokeWidth(pcb.FromMM(0.5))
        else:
            z.SetPadConnection(pcb.ZONE_CONNECTION_FULL)
        polygon = z.Outline(); polygon.NewOutline()
        for x, y in points:
            polygon.Append(pcb.FromMM(x), pcb.FromMM(y))
        for hole_points in keepout_hole_polygons or ():
            hole = polygon.NewHole()
            for x, y in hole_points:
                polygon.Append(pcb.FromMM(x), pcb.FromMM(y), 0, hole)
        self.board.Add(z)
        self.stats['zones'] += 1
        return z

    def zone_rect(self, net, layer, x0, y0, x1, y1, **kwargs):
        """Rectangular ``zone`` helper with mm corners."""
        return self.zone(net, layer, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kwargs)

    def fill(self):
        """Rebuild connectivity and fill every zone on the board."""
        self.board.BuildConnectivity()
        self.pcb.ZONE_FILLER(self.board).Fill(self.board.Zones())

    # ----- clean-up and reporting --------------------------------------------------------------
    def prune_unused_vias(self, exclude_nets=()):
        """Remove vias touching copper on fewer than two layers; returns the count removed.

        Nets in ``exclude_nets`` (zone nets) are kept. A via is removed only when at
        least two tracks or pads meet at its centre, so no track end is left dangling.
        Grid occupancy is left reserved.
        """
        pcb = self.pcb; exclude = set(exclude_nets)
        ends = defaultdict(list)
        for item in self.board.GetTracks():
            if isinstance(item, pcb.PCB_VIA):
                continue
            for p in (item.GetStart(), item.GetEnd()):
                ends[(item.GetNetCode(), p.x, p.y)].append(item.GetLayer())
        pads = defaultdict(list)
        for pad in self.board.GetPads():
            pads[pad.GetNetCode()].append(pad)
        removed = 0
        for via in [t for t in self.board.GetTracks() if isinstance(t, pcb.PCB_VIA)]:
            if via.GetNetname() in exclude:
                continue
            xy = via.GetPosition()
            touching = list(ends.get((via.GetNetCode(), xy.x, xy.y), []))
            for pad in pads[via.GetNetCode()]:
                if pad.HitTest(xy):
                    touching.extend(layer for layer in self.layers if pad.IsOnLayer(layer))
            if len(set(touching)) < 2 and len(touching) >= 2:
                self.board.Remove(via); removed += 1
                self.vias.pop(self._key(tuple(pcb.ToMM(xy))), None)
        self.stats['pruned_unused_vias'] += removed
        return removed

    def report(self):
        """Summary dict: counts, pruned vias, unresolved records and per-net track length (mm)."""
        return dict(status='requires-native-DRC', tracks=int(self.stats['tracks']), vias=int(self.stats['vias']),
                    zones=int(self.stats['zones']), pruned=int(self.stats['pruned_unused_vias']),
                    unresolved=list(self.unresolved),
                    net_length_mm={net: round(value, 3) for net, value in sorted(self.length.items())},
                    grid=dict(nx=self.grid.nx, ny=self.grid.ny, pitch=self.grid.grid, margin_cells=self.grid.margin,
                              layers=list(self.names), directions=list(self.grid.directions)),
                    stats=dict(self.stats))


# ----- declarative plans ----------------------------------------------------------------------
def validate_plan(plan):
    """Check a routing plan dict (keys, sizes, types) and return a shallow copy.

    Plan keys: ``board`` {width, height, origin?, margin?}; ``layers`` [names];
    ``grid``/``trace``/``clearance``/``hole_clearance`` mm; ``via`` [diameter, drill];
    ``directions`` ['h'|'v'|None per layer]; ``net_rules`` {net: {width, clearance}};
    ``keepouts`` [{layer?, rect:[x0,y0,x1,y1], net?, vias?}]; ``pre_routed`` {tracks:
    [{net, layer|layers, a, b, width?}], vias: [{net, xy, diameter?, drill?, port?,
    if_allowed?}], via_arrays: [{net, origin, pitch, count, diameter?, drill?, port?}]};
    ``critical`` [nets in order]; ``critical_layers`` [names]; ``power`` {net: {anchors?:
    [refs], stubs?, layers?, zones?: {layer: polygon}, clearance?, priority?,
    min_thickness?, thermal_relief?}}; ``fanout`` {skip_refs?, skip_nets?, skip_pads?,
    inpad_vias?, inward_pads?, order?}; ``signal_order`` [names or prefixes];
    ``signal_layers`` [names]; ``exclude_nets``; ``front_fallback``; ``ground`` {net,
    layers, polygon?, holes?: {layer: [polygon,...]}, clearance?, priority?,
    thermal_relief?}; ``prune_vias``; ``fill``; ``save`` path; ``strict``; ``max_nodes``
    A* expansion budget per path (default 700000).
    """
    if not isinstance(plan, dict):
        raise ValueError('plan must be a dict')
    unknown = set(plan) - PLAN_KEYS
    if unknown:
        raise ValueError(f'unknown plan keys: {sorted(unknown)}')
    board = plan.get('board')
    if not isinstance(board, dict) or not all(isinstance(board.get(k), (int, float)) and board[k] > 0 for k in ('width', 'height')):
        raise ValueError('plan.board needs positive width and height')
    layers = plan.get('layers')
    if not isinstance(layers, (list, tuple)) or not layers or not all(isinstance(l, str) for l in layers):
        raise ValueError('plan.layers must be a non-empty list of layer names')
    via = plan.get('via', (0.6, 0.3))
    if len(via) != 2 or via[1] >= via[0]:
        raise ValueError('plan.via must be [diameter, drill] with drill < diameter')
    for keepout in plan.get('keepouts', ()):
        if not isinstance(keepout, dict) or len(keepout.get('rect', ())) != 4:
            raise ValueError(f'keepout needs rect [x0, y0, x1, y1]: {keepout}')
    for name in ('net_rules', 'power', 'pre_routed', 'fanout'):
        if name in plan and not isinstance(plan[name], dict):
            raise ValueError(f'plan.{name} must be a dict')
    for net, spec in plan.get('power', {}).items():
        if not isinstance(spec, dict):
            raise ValueError(f'power net {net} needs a dict')
        for layer, polygon in spec.get('zones', {}).items():
            if len(polygon) < 3:
                raise ValueError(f'power zone {net}/{layer} needs at least 3 points')
    ground = plan.get('ground')
    if ground is not None and (not isinstance(ground, dict) or not ground.get('net') or not ground.get('layers')):
        raise ValueError('plan.ground needs net and layers')
    return dict(plan)


def save_and_reload(board, path):
    """SaveBoard then LoadBoard and compare item counts; returns the reloaded counts."""
    import pcbnew as pcb

    def counts(b):
        tracks = list(b.GetTracks())
        return dict(footprints=len(b.GetFootprints()), tracks=sum(1 for t in tracks if not isinstance(t, pcb.PCB_VIA)),
                    vias=sum(1 for t in tracks if isinstance(t, pcb.PCB_VIA)), zones=len(b.Zones()),
                    nets=len([n for n in b.GetNetInfo().NetsByNetcode().values() if n.GetNetCode()]))
    pcb.SaveBoard(str(path), board)
    before, after = counts(board), counts(pcb.LoadBoard(str(path)))
    if before != after:
        raise RuntimeError(f'reloaded board differs from the saved one: {before} vs {after}')
    return dict(path=str(path), **after)


def run_plan(board, plan):
    """Execute a declarative routing plan on an open pcbnew BOARD and return the report dict.

    Stages: router setup (rules, keepouts) -> pre-routed tracks/vias/via arrays ->
    fanout -> critical nets in plan order -> power stubs and zones -> signal nets by
    priority -> via pruning -> ground zones -> zone fill -> optional save/reload.
    ``strict`` raises RuntimeError when anything stays unresolved.
    """
    plan = validate_plan(plan)
    start = time.monotonic()
    spec = plan['board']
    power = plan.get('power', {})
    router = Router(board, spec['width'], spec['height'], plan['layers'], grid=plan.get('grid', 0.25),
                    trace=plan.get('trace', 0.2), clearance=plan.get('clearance', 0.2), via=tuple(plan.get('via', (0.6, 0.3))),
                    net_rules=plan.get('net_rules'), board_margin=spec.get('margin', 1.0), origin=tuple(spec.get('origin', (0.0, 0.0))),
                    critical=plan.get('critical', ()), power=list(power), hole_clearance=plan.get('hole_clearance', 0.25),
                    directions=plan.get('directions'), max_nodes=plan.get('max_nodes', 700000))
    for keepout in plan.get('keepouts', ()):
        layer = keepout.get('layer')
        router.keepout(router.layer_index(layer) if isinstance(layer, str) else layer, *keepout['rect'],
                       net=keepout.get('net', -1) if keepout.get('net') is not None else -1, block_vias=bool(keepout.get('vias')))
    pre = plan.get('pre_routed', {})
    for t in pre.get('tracks', ()):
        for layer in t.get('layers', [t.get('layer')]):
            router.track(tuple(t['a']), tuple(t['b']), t['net'], router.layer_index(layer), t.get('width'))
    for v in pre.get('vias', ()):
        xy = tuple(v['xy']); gx, gy = router.to_grid(*xy)
        if v.get('if_allowed') and not router.via_allowed(gx, gy, v['net']):
            continue
        router.via(xy, v['net'], v.get('diameter'), v.get('drill'))
        if v.get('port'):
            router.ports[v['net']].append((gx, gy, None, 'PRE_VIA', ''))
    for array in pre.get('via_arrays', ()):
        (x0, y0), (px, py), (count_x, count_y) = array['origin'], array['pitch'], array['count']
        for ix in range(int(count_x)):
            for iy in range(int(count_y)):
                xy = (x0 + ix * px, y0 + iy * py)
                router.via(xy, array['net'], array.get('diameter'), array.get('drill'))
                if array.get('port'):
                    router.ports[array['net']].append((*router.to_grid(*xy), None, 'VIA_ARRAY', ''))
    fan = plan.get('fanout', {})
    skip_refs, skip_nets = set(fan.get('skip_refs', ())), set(fan.get('skip_nets', ()))
    skip_pads = {tuple(p) for p in fan.get('skip_pads', ())}
    inward = {tuple(p) for p in fan.get('inward_pads', ())}
    order = list(fan.get('order', ())); rank = {ref: i for i, ref in enumerate(order)}
    router.fanout(order_key=lambda r: (rank.get(r['ref'], len(order) + (0 if r['ref'].startswith('U') else 1)),
                                       natural_ref_key(r['ref']), pad_sort_key(r['number'])),
                  skip=lambda r: r['ref'] in skip_refs or r['net'] in skip_nets or (r['ref'], r['number']) in skip_pads,
                  inpad_vias=[tuple(p) for p in fan.get('inpad_vias', ())],
                  inward=lambda r: (r['ref'], r['number']) in inward)
    indices = lambda names: tuple(router.layer_index(n) for n in names) if names else None
    critical_layers = indices(plan.get('critical_layers'))
    for net in plan.get('critical', ()):
        if net in router.code:
            router.route_net(net, layers=critical_layers)
    for net, item in power.items():
        if net not in router.code:
            continue
        if item.get('stubs', True) and item.get('anchors'):
            anchors = set(item['anchors'])
            router.route_power_stub(net, [p for p in router.ports[net] if p[3] in anchors],
                                    [p for p in router.ports[net] if p[3] not in anchors], layers=indices(item.get('layers')))
        for layer, polygon in item.get('zones', {}).items():
            router.zone(net, layer, [tuple(p) for p in polygon], priority=item.get('priority', 1), clearance=item.get('clearance', 0.5),
                        min_thickness=item.get('min_thickness', 0.2), thermal_relief=bool(item.get('thermal_relief')))
    ground = plan.get('ground')
    ground_net = ground['net'] if ground else None
    excluded = set(plan.get('exclude_nets', ())) | set(plan.get('critical', ())) | set(power) | ({ground_net} if ground_net else set())
    priority = list(plan.get('signal_order', ()))
    def rank_net(net):
        return next((i for i, pattern in enumerate(priority) if net == pattern or net.startswith(pattern)), len(priority))
    remaining = sorted((n for n in router.ports if n not in excluded), key=lambda n: (rank_net(n), len(router.ports[n]), n))
    signal_layers = indices(plan.get('signal_layers'))
    for net in remaining:
        router.route_net(net, layers=signal_layers, allow_front_fallback=plan.get('front_fallback', True))
    if plan.get('prune_vias', True):
        router.prune_unused_vias(exclude_nets=set(power) | ({ground_net} if ground_net else set()))
    if ground:
        margin = spec.get('margin', 1.0); ox, oy = spec.get('origin', (0.0, 0.0))
        polygon = ground.get('polygon') or [(ox + margin, oy + margin), (ox + spec['width'] - margin, oy + margin),
                                            (ox + spec['width'] - margin, oy + spec['height'] - margin), (ox + margin, oy + spec['height'] - margin)]
        for layer in ground['layers']:
            router.zone(ground_net, layer, [tuple(p) for p in polygon], priority=ground.get('priority', 0),
                        clearance=ground.get('clearance', 0.25), thermal_relief=bool(ground.get('thermal_relief')),
                        keepout_hole_polygons=[[tuple(p) for p in hole] for hole in ground.get('holes', {}).get(layer, ())])
    if plan.get('fill', True):
        router.fill()
    report = router.report()
    report.update(stage='routed_candidate', seconds=round(time.monotonic() - start, 3))
    if plan.get('save'):
        report['saved'] = save_and_reload(board, plan['save'])
    if plan.get('strict') and report['unresolved']:
        raise RuntimeError(f"{len(report['unresolved'])} unresolved routing items")
    return report
