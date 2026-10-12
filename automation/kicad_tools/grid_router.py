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

V2.1 geometry (all opt-in through the plan key ``style``; without it every stage is byte-for-byte V2):
``style.diagonal`` switches ``Grid.astar`` to 8 directions (octile heuristic, no corner cutting: both
orthogonal neighbours of a diagonal step must be free, parent-direction bend penalties in cells, cell
state so ``max_nodes`` keeps its meaning); pad-escape fanout and the rip-up victim search stay 4-direction.
``style.simplify = 'octilinear'`` and ``style.arcs`` run ``Router.beautify`` once after via pruning and
before the ground zones: per chain of router-made tracks between pads/vias/junctions, octilinear string
pulling, short-run collapse and on-grid 45-degree chamfers are validated by the exact grid rule the 8-direction
search uses, tangent fillets (adaptive radius, ``PCB_ARC``) by a corridor test on the dilated foreign mask;
a chain is rewritten whole or kept whole, so no net gets longer, no via moves and no width changes.
``smooth_policy`` keeps arcs off power/critical nets and wide tracks (diagonals only) unless the plan says otherwise.
"""
from __future__ import annotations

import heapq
import math
import re
import time
from collections import Counter, defaultdict

import numpy as np

from automation.kicad_tools import path_geometry as pg

EPS = 0.01
ESCAPE_DISTANCES = (0.65, 1.25, 1.9, 2.65, 3.5, 4.5, 6.0)
ESCAPE_SHIFTS = (0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2, -2)
PLAN_KEYS = {'board', 'layers', 'grid', 'trace', 'clearance', 'via', 'hole_clearance', 'directions',
             'net_rules', 'keepouts', 'pre_routed', 'critical', 'critical_layers', 'power', 'fanout',
             'signal_order', 'signal_layers', 'exclude_nets', 'front_fallback', 'ground', 'prune_vias',
             'fill', 'save', 'strict', 'max_nodes', 'signal_order_trials', 'ripup_rounds', 'ripup_penalty', 'signal_first', 'signal_groups',
             'signal_pinned', 'style'}
# V2.1 routing style (plan key ``style``). Every default reproduces V2: 4-direction search, no simplification, no arcs.
STYLE_DEFAULTS = dict(
    diagonal=False,            # 8-direction A* (octile heuristic, corner rule) for the route/negotiate/retry searches
    bend_penalty_cells=None,   # [45-degree, 90-degree] penalty in cells; None = [0.6, 2.0] when diagonal else [0, 0]
    via_cost_cells=8,          # layer-change cost of Grid.astar (V2: 8)
    heuristic_weight=1.0,      # emergency knob only: > 1 trades optimality for speed
    diagonal_pref_factor=1.075,  # diagonal step factor on a layer with a preferred direction (orthogonal off-direction: 1.15)
    simplify='none',           # 'octilinear': final-stage string pulling + short-run collapse (+ chamfer) of router chains
    chamfer=True,              # with simplify: cut remaining 90-degree corners by the largest clear on-grid 45-degree chamfer
    arcs=False,                # final-stage tangent fillets (PCB_ARC) on nets whose smooth_policy is 'arc'
    arc_radius_mm=[0.0, 0.0, 1.0],  # [minimum (0 = track width), preferred (0 = 2 x width), maximum]
    arc_steps=5,               # radius candidates tried per corner (geometric sequence preferred -> minimum)
    arc_dilate_cells=2,        # extra dilation of the foreign mask for the off-grid arc samples (see Router.check_arc)
    min_turn_deg=5.0,          # corners turning less are left as they are (no "almost straight" arcs)
    max_turn_deg=170.0,        # corners turning more (reversals) are never filleted
    corner_keep_mm={'via': None, 'port': 0.0},  # straight length kept at a chain end: via = via_d/2 + clearance when None; pads keep the whole exit leg
    straight_nets=[],          # names or prefixes whose chains are never touched
    max_width_for_arcs_mm=0.6,  # wider tracks get diagonals only
    smooth_power=False,        # power (zone) nets: diagonals only unless True
    smooth_critical=False,     # critical nets: diagonals only unless True
    stages=['signal', 'negotiate', 'retry', 'critical'],  # router stages whose copper beautify may rewrite ('fanout', 'power' optional)
    l_short_mm=None,           # short-run threshold for the collapse pass; None = max(2 x width, 4 x grid)
    eps=EPS,                   # marking slack added to every copper radius (raise to 0.02 on 0.2 mm clearance boards if DRC asks)
)
SMOOTH_POLICIES = ('none', 'diagonal', 'arc')
BEAUTIFY_STAGES = ('pre_routed', 'fanout', 'critical', 'power', 'signal', 'negotiate', 'retry')


def normalise_style(style):
    """Merge a plan ``style`` dict over ``STYLE_DEFAULTS`` (validated) and resolve the derived defaults."""
    style = dict(style or {})
    unknown = set(style) - set(STYLE_DEFAULTS)
    if unknown:
        raise ValueError(f'unknown style keys: {sorted(unknown)}')
    cfg = {**STYLE_DEFAULTS, **style}
    cfg['corner_keep_mm'] = {**STYLE_DEFAULTS['corner_keep_mm'], **dict(style.get('corner_keep_mm') or {})}
    if set(cfg['corner_keep_mm']) - {'via', 'port'}:
        raise ValueError('style.corner_keep_mm accepts via and port only')
    bend = cfg['bend_penalty_cells']
    if bend is None:
        bend = [0.6, 2.0] if cfg['diagonal'] else [0.0, 0.0]
    if len(bend) != 2 or any(float(b) < 0 for b in bend):
        raise ValueError('style.bend_penalty_cells must be [bend_45, bend_90] with non-negative cells')
    cfg['bend_penalty_cells'] = [float(bend[0]), float(bend[1])]
    if cfg['simplify'] not in ('none', 'octilinear'):
        raise ValueError("style.simplify must be 'none' or 'octilinear'")
    if float(cfg['via_cost_cells']) <= 0 or float(cfg['heuristic_weight']) < 1.0 or float(cfg['diagonal_pref_factor']) < 1.0:
        raise ValueError('style.via_cost_cells must be positive, heuristic_weight and diagonal_pref_factor at least 1')
    radii = list(cfg['arc_radius_mm'])
    if len(radii) != 3 or any(float(r) < 0 for r in radii) or (radii[1] and radii[1] > radii[2]) or radii[0] > radii[2]:
        raise ValueError('style.arc_radius_mm must be [min, preferred, max] with min <= preferred <= max (0 = width-derived)')
    cfg['arc_radius_mm'] = [float(r) for r in radii]
    if not 0 < float(cfg['min_turn_deg']) < float(cfg['max_turn_deg']) <= 180:
        raise ValueError('style.min_turn_deg must lie in (0, max_turn_deg] with max_turn_deg <= 180')
    if set(cfg['stages']) - set(BEAUTIFY_STAGES):
        raise ValueError(f'style.stages must be a subset of {BEAUTIFY_STAGES}')
    if float(cfg['eps']) < EPS:
        raise ValueError(f'style.eps must be at least {EPS}')
    if int(cfg['arc_steps']) < 1 or int(cfg['arc_dilate_cells']) < 1:
        raise ValueError('style.arc_steps and arc_dilate_cells must be at least 1')
    cfg['straight_nets'] = [str(n) for n in cfg['straight_nets']]
    cfg['stages'] = [str(s) for s in cfg['stages']]
    return cfg


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


def point_segment_distance(px, py, ax, ay, bx, by):
    """Distance from (px, py) to the segment a-b (same units)."""
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    t = 0.0 if den == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / den))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


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

    def __init__(self, nx, ny, layer_count, grid=0.25, margin_cells=4, origin=(0.0, 0.0), directions=None,
                 moves=4, bend=(0.0, 0.0), diagonal_pref_factor=1.075, heuristic_weight=1.0):
        if nx < 3 or ny < 3 or layer_count < 1 or grid <= 0:
            raise ValueError('grid needs at least 3 x 3 cells, one layer and a positive pitch')
        if int(moves) not in (4, 8):
            raise ValueError('moves must be 4 or 8')
        self.nx, self.ny, self.nl, self.grid = int(nx), int(ny), int(layer_count), float(grid)
        self.ox, self.oy = float(origin[0]), float(origin[1])
        self.margin = max(0, int(margin_cells))
        self.directions = list(directions) if directions is not None else default_directions(self.nl)
        self.moves = int(moves)  # default neighbourhood of astar (4 = V2, 8 = with 45-degree steps)
        self.bend = (float(bend[0]), float(bend[1]))  # parent-direction penalties in cells for 45 / 90 degree turns
        self.diagonal_pref_factor = float(diagonal_pref_factor)
        self.heuristic_weight = float(heuristic_weight)
        self.occ = np.zeros((self.nl, self.ny, self.nx), dtype=np.int16)
        self.zocc = np.zeros((self.nl, self.ny, self.nx), dtype=np.int16)  # zone keep-outs: block tracks, never via barrels
        self.alt = np.zeros((self.nl, self.ny, self.nx), dtype=np.int16)  # newer owner of a -2 cell (two nets' clearance halos overlap)
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
    def merge(view, mask, code, alt=None):
        """Mark masked cells with ``code``.

        A cell already owned by another code becomes -1 (blocked for everyone). With an ``alt`` view (the ``alt`` array of
        an occupancy layer) a conflict between two nets becomes -2 instead, a *soft* block that the rip-up search may cross,
        and ``alt`` records the newer owner (the item marked last, normally a track or via) as the net to rip; a hard
        code (-1: margin, keep-out, unconnected pad) always wins.
        """
        conflict = mask & (view != 0) & (view != code)
        if alt is None:
            view[conflict] = -1
        elif code > 0:
            soft = conflict & (view > 0)
            alt[soft] = code; view[soft] = -2
            alt[conflict & (view == -2)] = code
        else:
            view[conflict] = -1; alt[conflict] = -1
        view[mask & (view == 0)] = code

    def box(self, array, bb, inflate, code, alt=None):
        """Mark the axis-aligned mm box ``bb`` = (x0, y0, x1, y1) inflated by ``inflate`` mm (``alt``: see ``merge``)."""
        g = self.grid
        x0 = max(0, math.ceil((bb[0] - inflate - self.ox) / g)); x1 = min(self.nx - 1, math.floor((bb[2] + inflate - self.ox) / g))
        y0 = max(0, math.ceil((bb[1] - inflate - self.oy) / g)); y1 = min(self.ny - 1, math.floor((bb[3] + inflate - self.oy) / g))
        if x0 > x1 or y0 > y1:
            return
        view = array[y0:y1 + 1, x0:x1 + 1]
        self.merge(view, np.ones(view.shape, dtype=bool), code, None if alt is None else alt[y0:y1 + 1, x0:x1 + 1])

    def segment(self, array, a, b, radius, code, alt=None):
        """Mark every cell within ``radius`` mm of the mm segment a-b (a == b marks a disc; ``alt``: see ``merge``)."""
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
        self.merge(array[y0:y1 + 1, x0:x1 + 1], mask, code, None if alt is None else alt[y0:y1 + 1, x0:x1 + 1])

    def via_ok(self, x, y, code):
        """Plain via check: inside, no nearby drill and the via cell free or owned by ``code``."""
        return self.inside(x, y) and self.holes[y, x] == 0 and int(self.vocc[y, x]) in (0, code)

    # ----- read-only clearance tests for the beautify stage ---------------------------------------
    def foreign_mask(self, layer, code, extra=0.0, region=None, dilate_cells=0):
        """bool (ny, nx): cells net ``code`` may not use on ``layer`` - foreign copper halos and zone keep-outs dilated by
        ``extra`` + ``dilate_cells`` cells (exactly like ``astar`` for ``extra``), cells outside the net's ``region`` (per-layer
        list as in ``astar``) dilated by ``dilate_cells``. The margin frame is foreign copper (-1) already."""
        occ, zocc = self.occ[layer], self.zocc[layer]
        mask = ((occ != 0) & (occ != code)) | ((zocc != 0) & (zocc != code))
        if extra + dilate_cells > 0:
            mask = dilate(mask, extra + dilate_cells)
        if region is not None and layer < len(region) and region[layer] is not None:
            outside = ~region[layer]
            mask = mask | (dilate(outside, dilate_cells) if dilate_cells > 0 else outside)
        return mask

    def cells_free(self, mask, points):
        """True when the on-grid octilinear polyline ``points`` (integer cells, legs axis-parallel or exact diagonals) stays
        inside the routable area and off ``mask``, with the 8-direction corner rule for every diagonal step (both orthogonal
        neighbours free): the same test ``astar`` applies to its own moves, so the result is as safe as a routed path."""
        if not points:
            return False
        x, y = points[0]
        if not self.inside(x, y) or mask[y, x]:
            return False
        for p, q in zip(points, points[1:]):
            steps = pg._unit_steps(p, q)
            if steps is None:
                return False
            (ux, uy), n = steps
            x, y = p
            for _ in range(n):
                xx, yy = x + ux, y + uy
                if not self.inside(xx, yy) or mask[yy, xx]:
                    return False
                if ux and uy and (mask[y, xx] or mask[yy, x]):
                    return False
                x, y = xx, yy
        return True

    def samples_free(self, mask, samples):
        """True when the nearest cell of every mm sample lies inside the routable area and off ``mask`` (the caller dilates
        the mask so that an off-grid point between cell centres keeps its clearance; see Router.check_arc)."""
        for x, y in samples:
            gx, gy = self.to_grid(x, y)
            if not self.inside(gx, gy) or mask[gy, gx]:
                return False
        return True

    def astar(self, start, end, code, layers, max_nodes=700000, margin=None, extra=0.0, via_extra=0.0,
              transition=None, via_cost=8, allowed=None, via_allowed=None, moves=None, bend=None):
        """4- or 8-neighbour A* over (x, y, layer) cells for net ``code``.

        ``start``/``end`` are (x, y, layer); a ``None`` layer means any layer in
        ``layers`` (plated through pads). Planar steps cost 1.0 along a layer's
        preferred direction, else 1.15; a layer change costs ``via_cost`` and needs
        ``transition(x, y)`` or a free via cell. ``extra``/``via_extra`` (cells) dilate
        other-net occupancy for nets wider or with more clearance than the defaults.
        ``margin`` limits the search window around the endpoints. ``allowed`` (optional)
        is a per-layer list of bool arrays (ny, nx) - the routing region of the net: cells
        outside are never entered (a ``None`` entry leaves that layer unrestricted);
        ``via_allowed`` (bool array) restricts the cells where a layer change may happen.
        Zone keep-outs (``zocc``) block tracks like foreign copper. Returns the node
        list or None when no path exists within ``max_nodes`` expansions.

        ``moves`` (default ``self.moves``) = 8 adds the four diagonal steps (cost sqrt(2), times
        ``diagonal_pref_factor`` on a layer with a preferred direction) with the octile heuristic;
        a diagonal step is taken only when both orthogonally adjacent cells are free as well (no
        corner cutting, so the clearance argument of the inflated halos holds). ``bend`` (default
        ``self.bend``) = (b45, b90) adds a penalty in cells for turning relative to the direction the
        cell was reached from (135 degrees: b90 + b45, reversal: 2 x b90; the first step after a layer
        change is free); the state stays the cell, so the search is not strictly optimal with penalties
        but keeps the ``max_nodes`` budget semantics. With moves 4 and no penalties the search is the V2 one.
        """
        nx, ny = self.nx, self.ny
        moves = self.moves if moves is None else int(moves)
        b45, b90 = self.bend if bend is None else (float(bend[0]), float(bend[1]))
        eight = moves == 8
        table = pg.MOVES8 if eight else pg.MOVES4
        octants = [pg.OCTANT[m] for m in table]
        penalties = (0.0, b45, b90, b90 + b45, 2.0 * b90)
        use_bend = b45 > 0 or b90 > 0
        weight = self.heuristic_weight
        pref_factor = self.diagonal_pref_factor
        occ, vocc, holes, zocc = self.occ, self.vocc, self.holes, self.zocc
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
        region = list(allowed) if allowed is not None else None
        if extra > 0 or via_extra > 0:
            needed = set(layers) | {l for l in (sl, el) if l is not None}
            blocked = {l: dilate(((occ[l] != 0) & (occ[l] != code)) | ((zocc[l] != 0) & (zocc[l] != code)), extra) for l in needed}
            vblocked = dilate((vocc != 0) & (vocc != code), via_extra) | (holes != 0)
            if region is not None:
                for l in blocked:
                    if l < len(region) and region[l] is not None:
                        blocked[l] |= ~region[l]
            def free(l, x, y): return l in blocked and not blocked[l][y, x]
            def via_ok(x, y): return transition(x, y) or not vblocked[y, x]
        else:
            if region is not None:
                def free(l, x, y):
                    if int(occ[l, y, x]) not in (0, code) or int(zocc[l, y, x]) not in (0, code):
                        return False
                    return l >= len(region) or region[l] is None or bool(region[l][y, x])
            else:
                def free(l, x, y): return int(occ[l, y, x]) in (0, code) and int(zocc[l, y, x]) in (0, code)
            def via_ok(x, y): return transition(x, y) or (holes[y, x] == 0 and int(vocc[y, x]) in (0, code))
        if via_allowed is not None:
            base_via_ok = via_ok
            def via_ok(x, y): return bool(via_allowed[y, x]) and base_via_ok(x, y)  # noqa: F811
        directions = self.directions
        inf = math.inf

        if eight:
            def h(x, y, l): return pg.octile(ex - x, ey - y) * weight + (0 if el is None or l == el else 5)
        elif weight != 1.0:
            def h(x, y, l): return (abs(ex - x) + abs(ey - y)) * weight + (0 if el is None or l == el else 5)
        else:
            def h(x, y, l): return abs(ex - x) + abs(ey - y) + (0 if el is None or l == el else 5)
        def enc(x, y, l): return (l * ny + y) * nx + x
        def dec(k): return (k % nx, (k // nx) % ny, k // (nx * ny))
        heap, costs, parent = [], {}, {}
        for l in (layers if sl is None else (sl,)):
            k = enc(sx, sy, l); costs[k] = 0; heapq.heappush(heap, (h(sx, sy, l), 0, k))
        expanded = 0
        self.last_expanded = 0
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
                self.last_expanded = expanded
                return path
            expanded += 1
            if expanded > max_nodes:
                self.last_expanded = expanded
                return None
            pref = directions[l] if l < len(directions) else None
            d_in = pg.NO_DIR
            if use_bend:
                pk = parent.get(k)
                if pk is not None:
                    px, py, _pl = dec(pk)
                    if (px, py) != (x, y):
                        d_in = pg.OCTANT[(x - px, y - py)]  # a layer change resets the direction: the first step after a via is free
            for i, (dx, dy) in enumerate(table):
                xx, yy = x + dx, y + dy
                if not (xmin <= xx <= xmax and ymin <= yy <= ymax):
                    continue
                if not free(l, xx, yy) and not (xx == ex and yy == ey and int(occ[l, yy, xx]) in (0, code)):
                    continue  # the goal cell itself (the net's own port) is enterable even inside a dilated foreign halo
                if dx and dy:
                    if not (free(l, xx, y) and free(l, x, yy)):
                        continue  # no corner cutting: both orthogonal neighbours must be free (no goal exception for them)
                    step = pg.SQRT2 if pref is None else pg.SQRT2 * pref_factor
                else:
                    step = 1.0 if pref is None or (pref == 'h' and dy == 0) or (pref == 'v' and dx == 0) else 1.15
                if d_in != pg.NO_DIR:
                    step += penalties[pg.turn_class(d_in, octants[i])]
                nc = cost + step; nk = enc(xx, yy, l)
                if nc < costs.get(nk, inf):
                    costs[nk] = nc; parent[nk] = k; heapq.heappush(heap, (nc + h(xx, yy, l), nc, nk))
            if len(layers) > 1 and via_ok(x, y):
                for ll in layers:
                    if ll == l or not (free(ll, x, y) or (x == ex and y == ey and (el is None or ll == el) and int(occ[ll, y, x]) in (0, code))):
                        continue
                    nk = enc(x, y, ll); nc = cost + via_cost
                    if nc < costs.get(nk, inf):
                        costs[nk] = nc; parent[nk] = k; heapq.heappush(heap, (nc + h(x, y, ll), nc, nk))
        self.last_expanded = expanded  # heap exhausted: the reachable space is closed, no path exists
        return None


    def astar_soft(self, start, end, code, layers, penalty=40.0, max_nodes=700000, via_cost=8, rippable=None, allowed=None, via_allowed=None):
        """A* like ``astar`` but cells owned by another net (code > 0) are passable at ``penalty`` extra cost, and so
        are -2 cells (two nets' clearance halos overlap) when the newer owner recorded in ``alt`` can be ripped; -1 cells
        (pads of unconnected pins, keep-outs, margins) stay blocked, and so do cells of nets not in ``rippable`` (codes)
        when that set is given. Returns the node list or None. Used to find which nets to rip up for
        a connection the hard search cannot route. ``allowed`` / ``via_allowed`` as in ``astar``."""
        nx, ny = self.nx, self.ny
        occ, vocc, holes, zocc, alt = self.occ, self.vocc, self.holes, self.zocc, self.alt
        sx, sy, sl = start; ex, ey, el = end
        layers = tuple(layers)
        m = self.margin
        xmin, xmax, ymin, ymax = m, nx - 1 - m, m, ny - 1 - m
        inf = math.inf
        region = list(allowed) if allowed is not None else None

        def cell_cost(l, x, y):
            if region is not None and l < len(region) and region[l] is not None and not region[l][y, x]:
                return None
            if int(zocc[l, y, x]) not in (0, code):
                return None
            v = int(occ[l, y, x])
            if v == 0 or v == code:
                return 0.0
            if v == -2:
                v = int(alt[l, y, x])  # soft conflict: passable when its newer owner can be ripped
                if v == code:
                    return 0.0
            if v < 0 or (rippable is not None and v not in rippable):
                return None
            return penalty

        def via_cost_at(x, y):
            if holes[y, x] != 0 or (via_allowed is not None and not via_allowed[y, x]):
                return None
            v = int(vocc[y, x])
            if v == 0 or v == code:
                return 0.0
            if v < 0 or (rippable is not None and v not in rippable):
                return None
            return penalty

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
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if not (xmin <= xx <= xmax and ymin <= yy <= ymax):
                    continue
                extra = cell_cost(l, xx, yy)
                if extra is None:
                    if xx == ex and yy == ey and int(occ[l, yy, xx]) in (0, code):
                        extra = 0.0  # the goal cell (own port) is enterable
                    else:
                        continue
                nc = cost + 1.0 + extra; nk = enc(xx, yy, l)
                if nc < costs.get(nk, inf):
                    costs[nk] = nc; parent[nk] = k; heapq.heappush(heap, (nc + h(xx, yy, l), nc, nk))
            if len(layers) > 1:
                vextra = via_cost_at(x, y)
                if vextra is None:
                    continue
                for ll in layers:
                    if ll == l:
                        continue
                    extra = cell_cost(ll, x, y)
                    if extra is None:
                        continue
                    nk = enc(x, y, ll); nc = cost + via_cost + vextra + extra
                    if nc < costs.get(nk, inf):
                        costs[nk] = nc; parent[nk] = k; heapq.heappush(heap, (nc + h(x, y, ll), nc, nk))
        return None


class Router:
    """Grid router bound to an open pcbnew BOARD.

    ``layers`` lists the pcbnew copper layer ids (or names) used for routing, in
    order: index 0 is the component/front layer, the last index the back layer.
    Track methods take these *indices*; ``zone`` and keepouts take layer names or
    pcbnew ids. ``net_rules`` maps a net name to ``dict(width=, clearance=, fanout_width=)``
    overrides (also accepts ``critical``/``power`` flags; ``fanout_width`` is the pad-escape
    width of a wide net whose pads sit in a fine-pitch row). ``keepouts`` are
    ``(layer_index_or_None, x0, y0, x1, y1, net_code_or_-1[, block_vias])`` mm boxes;
    a net name may replace the code. ``critical`` nets stay on the front layer and
    never fall back; ``power`` nets never fall back to the front layer and keep
    their vias when pruning. Existing tracks and vias on the board are registered
    as occupancy so routing can be incremental. All vias are through vias.
    """

    def __init__(self, board, width_mm, height_mm, layers, grid=0.25, trace=0.2, clearance=0.2, via=(0.6, 0.3),
                 net_rules=None, keepouts=None, board_margin=1.0, origin=(0.0, 0.0), critical=(), power=(),
                 hole_clearance=0.25, directions=None, max_nodes=700000, style=None):
        import pcbnew as pcb
        self.pcb, self.board = pcb, board
        self.width, self.height = float(width_mm), float(height_mm)
        self.trace, self.clearance = float(trace), float(clearance)
        self.via_d, self.via_drill = float(via[0]), float(via[1])
        self.hole_clearance = float(hole_clearance); self.max_nodes = int(max_nodes)
        self.style = normalise_style(style)  # V2.1 geometry knobs; defaults = V2 behaviour
        self.eps = float(self.style['eps'])
        self.stage = 'pre_routed'  # run_plan names the stage whose copper is being created; beautify rewrites eligible stages only
        self.item_stage = {}  # KIID string -> stage of every track, arc and via this router created
        self.exceptions = []  # beautify: corners kept sharp, with a reason
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
        self.grid = Grid(nx, ny, self.nl, grid, max(1, math.ceil(board_margin / grid - 1e-9)), origin, directions,
                         moves=8 if self.style['diagonal'] else 4, bend=tuple(self.style['bend_penalty_cells']),
                         diagonal_pref_factor=self.style['diagonal_pref_factor'], heuristic_weight=self.style['heuristic_weight'])
        self.escape_distances, self.escape_shifts = ESCAPE_DISTANCES, ESCAPE_SHIFTS
        self.nets = {n.GetNetname(): n for n in board.GetNetInfo().NetsByNetcode().values() if n.GetNetCode()}
        self.code = {name: net.GetNetCode() for name, net in self.nets.items()}
        self.ports = defaultdict(list); self.pad_records = []; self.stats = defaultdict(int)
        self.length = defaultdict(float); self.unresolved = []; self.vias = {}; self.through = []
        self.created = None  # list of board items created while a snapshot is active (see snapshot/restore)
        self._keepouts = []  # keepout calls, replayed by rebuild_occupancy
        self._lanes = []  # reserved exit corridors (a, b, net, layer, width), replayed by rebuild_occupancy
        self._lane_memory = {}  # net -> every lane ever reserved for it: a ripped net gets its corridors back for the re-route
        self.net_items = defaultdict(list)  # signal-stage board items per net (rip-up candidates) while recording_net is set
        self.recording_net = None
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

    def fanout_width_for(self, net):
        """Width of the pad escape (fanout) tracks of ``net``: the ``fanout_width`` rule, else the net width.

        A wide power net whose pads sit in a fine-pitch row (0.65 mm HTSSOP, 0.95 mm SOT-23) cannot leave the
        pad at its full width without touching the neighbouring pads; the escape then uses the narrower
        fanout width up to the via and the routed tracks keep the net width.
        """
        return float(self.net_rules.get(net, {}).get('fanout_width', self.width_for(net)))

    def clearance_for(self, net):
        """Clearance used when marking copper of ``net`` (never below the default)."""
        return max(float(self.net_rules.get(net, {}).get('clearance', self.clearance)), self.clearance)

    def extra_for(self, net, width=None):
        """(track, via) extra radius in mm that ``net`` needs beyond the default marking (``width`` overrides the net width)."""
        more = self.clearance_for(net) - self.clearance
        width = self.width_for(net) if width is None else float(width)
        return max(0.0, (width - self.trace) / 2) + more, more

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
                    try:
                        angle = pad.GetOrientation().AsDegrees()  # KiCad 7+: EDA_ANGLE
                    except AttributeError:
                        angle = pad.GetOrientationDegrees()
                    if abs((angle % 180.0) - 90.0) < 1.0:  # a rotated slot: its drill size is given in the pad's own frame
                        drill = (drill[1], drill[0])
                    g.box(g.holes, [pos[0] - drill[0] / 2, pos[1] - drill[1] / 2, pos[0] + drill[0] / 2, pos[1] + drill[1] / 2],
                          self.hole_clearance + self.via_drill / 2 + 2 * EPS, -1)
                    if pad.GetAttribute() == pcb.PAD_ATTRIB_PTH:
                        g.segment(g.transitions, pos, pos, min(pcb.ToMM(pad.GetSize())) / 2 - 0.15, code)
                for layer in (range(self.nl) if thru else on):
                    g.box(g.occ[layer], box, clearance + self.trace / 2, code, alt=g.alt[layer])
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
            elif isinstance(item, pcb.PCB_ARC) and item.GetLayer() in self.layers:  # before the track branch: a PCB_ARC is a PCB_TRACK
                a, m, b = (tuple(pcb.ToMM(v)) for v in (item.GetStart(), item.GetMid(), item.GetEnd()))
                self._mark_arc(a, m, b, net, self.layers.index(item.GetLayer()), pcb.ToMM(item.GetWidth()), pcb.ToMM(item.GetLength()))
            elif item.GetLayer() in self.layers:
                a, b = tuple(pcb.ToMM(item.GetStart())), tuple(pcb.ToMM(item.GetEnd()))
                self._mark_track(a, b, net, self.layers.index(item.GetLayer()), pcb.ToMM(item.GetWidth()))

    def keepout(self, layer, x0, y0, x1, y1, net=-1, block_vias=False, zone=False):
        """Reserve a mm box on one routing layer index (or every layer when None) for ``net``.

        ``net`` is a net code, a net name or -1 (blocked for everyone). With
        ``block_vias`` the box also rejects via centres. A ``zone`` keep-out (a copper pour
        of another net on that layer) blocks tracks but lets through-via barrels of other
        nets pass (the zone filler clips the pour around them), so it is recorded in the
        grid's ``zocc`` array, which the via placement never consults.
        """
        code = self.net_code(net) if isinstance(net, str) else (-1 if net is None else int(net))
        if isinstance(layer, str):
            layer = self.layer_index(layer)
        self._keepouts.append((layer, x0, y0, x1, y1, code, block_vias, zone))
        target = self.grid.zocc if zone else self.grid.occ
        for index in (range(self.nl) if layer is None else (int(layer),)):
            self.grid.box(target[index], [x0, y0, x1, y1], 0, code, alt=None if zone else self.grid.alt[index])
        if block_vias:
            self.grid.box(self.grid.vocc, [x0, y0, x1, y1], 0, code)

    # ----- routing regions (per-net allowed areas) ---------------------------------------------
    def region_masks(self, net):
        """(per-layer allowed masks or None, via mask or None) for ``net`` from ``net_rules[net]['region']``.

        A region is a list of mm rects (all routing layers) or a dict ``{layer name: [rects], 'vias': [rects]}``;
        a layer missing from the dict is closed for that net. Without an explicit ``vias`` entry a via may sit only
        where the first and the last routing layer (the outer layers, which carry the via annuli that DRC measures)
        are both allowed. Masks are cached per distinct region specification.
        """
        spec = self.net_rules.get(net, {}).get('region')
        if spec is None:
            return None, None
        key = repr(spec)
        cache = getattr(self, '_region_cache', None)
        if cache is None:
            cache = self._region_cache = {}
        if key in cache:
            return cache[key]
        g = self.grid

        def mask_of(rects):
            m = np.zeros((g.ny, g.nx), dtype=bool)
            for x0, y0, x1, y1 in rects:
                cx0 = max(0, math.ceil((min(x0, x1) - g.ox) / g.grid - 1e-9)); cx1 = min(g.nx - 1, math.floor((max(x0, x1) - g.ox) / g.grid + 1e-9))
                cy0 = max(0, math.ceil((min(y0, y1) - g.oy) / g.grid - 1e-9)); cy1 = min(g.ny - 1, math.floor((max(y0, y1) - g.oy) / g.grid + 1e-9))
                if cx0 <= cx1 and cy0 <= cy1:
                    m[cy0:cy1 + 1, cx0:cx1 + 1] = True
            return m

        if isinstance(spec, dict):
            layers = [mask_of(spec.get(name, ())) for name in self.names]
            vias = mask_of(spec['vias']) if 'vias' in spec else (layers[0] & layers[-1])
        else:
            shared = mask_of(spec)
            layers = [shared for _ in self.names]
            vias = shared
        cache[key] = (layers, vias)
        return cache[key]

    # ----- copper creation -------------------------------------------------------------------
    def _mark_track(self, a, b, net, layer, width):
        g = self.grid; code = self.code[net]; clearance = self.clearance_for(net)
        g.segment(g.occ[layer], a, b, width / 2 + clearance + self.trace / 2 + self.eps, code, alt=g.alt[layer])
        g.segment(g.vocc, a, b, width / 2 + clearance + self.via_d / 2 + self.eps, code)
        self.length[net] += math.dist(a, b)

    def _mark_arc(self, a, m, b, net, layer, width, length):
        """Mark an arc (mm start, mid, end) as short chords with the track radii and add its true ``length`` (taken from the
        pcbnew item so that re-registration of a saved board reproduces ``net_length_mm`` exactly)."""
        g = self.grid; code = self.code[net]; clearance = self.clearance_for(net)
        pts = pg.sample_arc(a, m, b, g.grid / 2)
        for p, q in zip(pts, pts[1:]):
            g.segment(g.occ[layer], p, q, width / 2 + clearance + self.trace / 2 + self.eps, code, alt=g.alt[layer])
            g.segment(g.vocc, p, q, width / 2 + clearance + self.via_d / 2 + self.eps, code)
        self.length[net] += float(length)

    def _mark_via(self, xy, net, diameter, drill):
        g = self.grid; code = self.code[net]; clearance = self.clearance_for(net)
        for layer in range(self.nl):
            g.segment(g.occ[layer], xy, xy, diameter / 2 + clearance + self.trace / 2 + self.eps, code, alt=g.alt[layer])
        g.segment(g.vocc, xy, xy, diameter / 2 + clearance + self.via_d / 2 + self.eps, code)
        g.segment(g.holes, xy, xy, drill / 2 + self.hole_clearance + self.via_drill / 2 + 2 * EPS, -1)
        self.vias[self._key(xy)] = net

    def _tag(self, item):
        """Record the creating stage of a new board item (KIID string -> stage) and the created / rip-up bookkeeping."""
        self.item_stage[item.m_Uuid.AsString()] = self.stage
        if self.created is not None:
            self.created.append(item)
        if self.recording_net is not None:
            self.net_items[self.recording_net].append(item)

    def track(self, a, b, net, layer_index, width=None, mark_width=None):
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
        self._mark_track(a, b, net, layer_index, width if mark_width is None else max(float(mark_width), width))  # mark_width: wider occupancy for off-grid copper
        self.stats['tracks'] += 1
        self._tag(item)
        return item

    def arc(self, a, m, b, net, layer_index, width=None):
        """Add a PCB_ARC through the mm points start ``a``, ``m`` (on the arc) and end ``b``; returns the item or None.

        Occupancy is marked along the arc with the track radii; the arc length comes from the created item.
        """
        if math.dist(a, b) < 1e-6:
            return None
        width = self.width_for(net) if width is None else float(width)
        pcb = self.pcb
        item = pcb.PCB_ARC(self.board)
        item.SetStart(self.point(*a)); item.SetMid(self.point(*m)); item.SetEnd(self.point(*b)); item.SetWidth(pcb.FromMM(width))
        item.SetLayer(self.layers[layer_index]); item.SetNet(self.nets[net]); self.board.Add(item)
        self._mark_arc(a, m, b, net, layer_index, width, pcb.ToMM(item.GetLength()))
        self.stats['arcs'] += 1
        self._tag(item)
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
        self._tag(item)
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
        via_mask = self.region_masks(net)[1]
        if via_mask is not None and not via_mask[y, x]:
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

    def astar(self, start, end, net, layers=None, max_nodes=None, margin=None, width=None, moves=None):
        """Grid A* for ``net`` between (x, y, layer_index) cells; see ``Grid.astar``.

        ``layers`` are routing indices allowed for layer changes (default:
        ``default_layers``); ``max_nodes`` defaults to the router's budget; the
        net's width/clearance rule sets the dilation (``width`` overrides the width).
        ``moves`` overrides the grid's neighbourhood (the fanout escapes stay 4-direction).
        """
        layers = self.default_layers(net) if layers is None else tuple(layers)
        max_nodes = self.max_nodes if max_nodes is None else int(max_nodes)
        extra, via_extra = self.extra_for(net, width)
        g = self.grid
        allowed, via_allowed = self.region_masks(net)
        return g.astar(start, end, self.net_code(net), layers, max_nodes=max_nodes, margin=margin,
                       extra=extra / g.grid, via_extra=via_extra / g.grid,
                       transition=lambda x, y: self.existing_transition(self.to_mm(x, y), net),
                       allowed=allowed, via_allowed=via_allowed, via_cost=self.style['via_cost_cells'], moves=moves)

    def emit(self, path, net, width=None):
        """Realise an A* path as tracks (net rule width, or ``width``) and through vias."""
        segments, vias = compress_path(path)
        for x0, y0, x1, y1, layer in segments:
            self.track(self.to_mm(x0, y0), self.to_mm(x1, y1), net, layer, width)
        for x, y in vias:
            self.via(self.to_mm(x, y), net)

    # ----- routing stages --------------------------------------------------------------------
    @staticmethod
    def default_order_key(record):
        """Fanout order: ICs first, then natural reference order and pad number."""
        return (0 if record['ref'].startswith('U') else 1, natural_ref_key(record['ref']), pad_sort_key(record['number']))

    def fanout(self, order_key=None, skip=None, inpad_vias=(), inward=None, escape_layer=None, exact=None, direct=None,
               exact_via=None, direct_lane=0.0, exact_lane=None):
        """Escape every connected pad to a routing port; returns ``[ref, pad, net]`` failures.

        Through-hole pads register a port with layer None (reachable on every
        routing layer). Pads of critical nets register on their own layer without
        a via. Other SMD pads get a short escape on their layer to a via whose port
        is on ``escape_layer`` (default: the next inner layer; the back side mirrors).
        ``(ref, pad)`` pairs in ``inpad_vias`` get the via in the pad centre
        (thermal pads). ``skip(record)`` excludes pads, ``inward(record)`` prefers an
        escape towards the footprint centre (dense packages), ``order_key(record)``
        sets the pad order. ``exact(record)`` may return a length in mm (or a
        ``(length, (ux, uy)[, offset[, layer]])`` tuple with an explicit stub direction,
        a lateral offset of the stub inside the pad and - for plated through pads, which
        otherwise register a layer-free port - the layer of the stub and its port): the pad then
        gets an exact straight stub along its axis (pad centre to that length beyond
        the pad end, no via) and its port is the stub end on the pad's own layer -
        the escape for 0.65 mm pitch rows whose neighbours cannot host vias; such pads
        are escaped before the via escapes so that the vias keep clear of the stubs.
        ``direct(record)`` registers an SMD pad as a port on its own layer without any
        escape copper (the router adds vias where it needs them); exact stubs win over it.
        ``exact_via(record)`` puts a through via at the end of the pad's exact stub (when the
        via fits) and registers a layer-free port there, so a stub row whose pitch allows vias
        gets ports on every routing layer. ``direct_lane`` (mm) reserves, for every direct port,
        the exit corridor along the pad's outward axis for the net (no copper; the cells a track
        would occupy are marked so that foreign tracks cannot hug the pad and seal its port).
        ``exact_lane(record)`` (mm, optional) reserves the same kind of corridor beyond an exact
        stub's end, in the stub's direction on the stub's layer, so a row of stub (or stub-via)
        ports cannot be sealed by one foreign track running along the stub-end line.
        """
        skip = skip or (lambda record: False); inward = inward or (lambda record: False)
        exact = exact or (lambda record: None); direct = direct or (lambda record: False)
        exact_via = exact_via or (lambda record: False); direct_lane = float(direct_lane or 0.0)
        exact_lane = exact_lane or (lambda record: 0.0)
        inpad = {tuple(p) for p in inpad_vias}
        failures = []
        g = self.grid
        base_key = order_key or self.default_order_key
        for r in sorted(self.pad_records, key=lambda rec: (0 if exact(rec) else 1, base_key(rec))):
            net, ref, number = r['net'], r['ref'], r['number']
            if not net or net.startswith('unconnected-') or r['code'] <= 0 or skip(r):
                continue
            x, y = r['xy']; sx, sy = self.to_grid(x, y); side = r['side']
            thru_spec = exact(r) if r['thru'] else None
            if r['thru'] and not (isinstance(thru_spec, (tuple, list)) and len(thru_spec) > 3):
                self.ports[net].append((sx, sy, None, ref, number)); continue
            if r['thru']:  # (length, (ux, uy), offset, layer): straight stub out of a through pad on that layer, port at its end
                length, (ux, uy), lateral = float(thru_spec[0]), (int(thru_spec[1][0]), int(thru_spec[1][1])), float(thru_spec[2])
                layer = thru_spec[3]
                side = self.layer_index(layer) if isinstance(layer, str) else int(layer)
                x0, y0 = x, y
                x, y = x + (lateral if uy else 0.0), y + (lateral if ux else 0.0)
                extent = (r['box'][2] - r['box'][0]) / 2 if ux else (r['box'][3] - r['box'][1]) / 2
                escape_width = self.fanout_width_for(net)
                placed = False
                for more in (0.0, 0.5, 1.0, 1.5):
                    end = (x + ux * (extent + length + more), y + uy * (extent + length + more))
                    ex, ey = self.to_grid(*end)
                    if not g.inside(ex, ey) or int(g.occ[side, ey, ex]) not in (0, r['code']):
                        continue
                    if more and not self._stub_clear(side, (x + ux * (extent + length), y + uy * (extent + length)), end, r['code']):
                        continue  # the longer stub would cross foreign copper beyond the nominal end
                    if abs(lateral) > 1e-9:
                        self.track((x0, y0), (x, y), net, side, escape_width, escape_width + 0.05)  # jog from the pad centre into the gap
                    self.track((x, y), end, net, side, escape_width, escape_width + 0.05)
                    self.track(end, self.to_mm(ex, ey), net, side, escape_width, escape_width + 0.05)
                    self.ports[net].append((ex, ey, self._stub_port_layer(r, ex, ey, side, exact_via), ref, number)); placed = True
                    lane = float(exact_lane(r) or 0.0)
                    if lane > 0:
                        px, py = self.to_mm(ex, ey)
                        self._reserve_lane((px, py), (px + ux * lane, py + uy * lane), net, side)
                    break
                if not placed:
                    failures.append([ref, number, net])
                    self.unresolved.append(dict(stage='fanout', ref=ref, pad=number, net=net))
                continue
            if self.is_critical(net) or self.nl == 1:
                self.ports[net].append((sx, sy, side, ref, number)); continue
            cx, cy = self.pcb.ToMM(r['fp'].GetPosition())
            dx, dy = x - cx, y - cy
            if abs(dx) >= abs(dy):
                ux, uy = (1 if dx >= 0 else -1), 0
            else:
                ux, uy = 0, (1 if dy >= 0 else -1)
            if direct(r) and not exact(r):
                # port at the pad's outer end (long pads: the copper the router adds starts beyond the pad centre, so a track
                # leaving a barrier package stays as far from the opposite row as the pad itself)
                extent = (r['box'][2] - r['box'][0]) / 2 if ux else (r['box'][3] - r['box'][1]) / 2
                px, py = self.to_grid(x + ux * max(0.0, extent - 0.35), y + uy * max(0.0, extent - 0.35))
                if g.inside(px, py) and int(g.occ[side, py, px]) == r['code']:
                    sx, sy = px, py
                if direct_lane > 0:
                    self._reserve_lane((x, y), (x + ux * (extent + direct_lane), y + uy * (extent + direct_lane)), net, side)
                self.ports[net].append((sx, sy, side, ref, number)); continue
            port_layer = escape_layer if escape_layer is not None else (1 if side == 0 else self.nl - 2)
            escape_width = self.fanout_width_for(net)
            if (ref, number) in inpad:
                xy = self.to_mm(sx, sy); self.via(xy, net); self.track((x, y), xy, net, side, escape_width)
                self.ports[net].append((sx, sy, port_layer, ref, number)); continue
            primary = -1 if inward(r) else 1
            stub_length = exact(r)
            lateral = 0.0
            if isinstance(stub_length, (tuple, list)):  # (length, (ux, uy)[, offset]): explicit stub direction and lateral offset
                lateral = float(stub_length[2]) if len(stub_length) > 2 else 0.0
                stub_length, (ux, uy) = float(stub_length[0]), (int(stub_length[1][0]), int(stub_length[1][1]))
                primary = 1
                x, y = x + (lateral if uy else 0.0), y + (lateral if ux else 0.0)  # the stub runs beside the pad centreline
            extent = (r['box'][2] - r['box'][0]) / 2 if ux else (r['box'][3] - r['box'][1]) / 2
            if stub_length:
                placed = False
                for more in (0.0, 0.5, 1.0, 1.5):
                    reach = extent + float(stub_length) + more
                    end = (x + primary * ux * reach, y + primary * uy * reach)
                    ex, ey = self.to_grid(*end)
                    if not g.inside(ex, ey) or int(g.occ[side, ey, ex]) not in (0, r['code']):
                        continue
                    nominal = (x + primary * ux * (extent + float(stub_length)), y + primary * uy * (extent + float(stub_length)))
                    if more and not self._stub_clear(side, nominal, end, r['code']):
                        continue  # the longer stub would cross foreign copper (a via or track beyond the row)
                    # the stub starts in the outer half of the pad (its end cap must not reach past the pad centre towards the
                    # neighbouring row: isolation rules measure track copper, not pad copper); its occupancy is marked at the
                    # true (off-grid) position, so a neighbouring stub 0.65 mm away leaves the cells ahead of this one free
                    start = (x + primary * ux * extent * 0.45, y + primary * uy * extent * 0.45)
                    self.track(start, end, net, side, escape_width, escape_width + 0.05)
                    self.track(end, self.to_mm(ex, ey), net, side, escape_width, escape_width + 0.05)  # <= half a cell to the grid port
                    self.ports[net].append((ex, ey, self._stub_port_layer(r, ex, ey, side, exact_via), ref, number)); placed = True
                    lane = float(exact_lane(r) or 0.0)
                    if lane > 0:
                        px, py = self.to_mm(ex, ey)
                        self._reserve_lane((px, py), (px + primary * ux * lane, py + primary * uy * lane), net, side)
                    break
                if placed:
                    continue
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
                path = self.astar((sx, sy, side), (ex, ey, side), net, layers=(side,), max_nodes=1500, margin=10, width=escape_width, moves=4)
                if path is None:
                    continue
                self.track((x, y), self.to_mm(sx, sy), net, side, escape_width); self.emit(path, net, escape_width); self.via(self.to_mm(ex, ey), net)
                self.ports[net].append((ex, ey, port_layer, ref, number)); routed = True
                break
            if not routed:
                failures.append([ref, number, net])
                self.unresolved.append(dict(stage='fanout', ref=ref, pad=number, net=net))
        self.stats['fanout_unresolved'] += len(failures)
        return failures

    def _stub_clear(self, side, a, b, code):
        """True when every grid cell along the mm segment a-b (sampled at the grid pitch) is free or owned by ``code`` on layer ``side``."""
        g = self.grid
        n = max(1, int(math.ceil(math.dist(a, b) / g.grid)))
        for i in range(n + 1):
            x, y = self.to_grid(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            if not g.inside(x, y) or int(g.occ[side, y, x]) not in (0, code):
                return False
        return True

    def _stub_port_layer(self, record, ex, ey, side, exact_via):
        """Layer of an exact-stub port: the stub's layer, or None (every layer) when ``exact_via`` asks for a via at the stub end and
        a via fits there (hole, via occupancy and the net's via region); the via is added to the board."""
        if not exact_via(record):
            return side
        net = record['net']
        if not self.via_allowed(ex, ey, net):
            self.stats['exact_via_skipped'] += 1
            return side
        self.via(self.to_mm(ex, ey), net)
        return None

    def _reserve_lane(self, a, b, net, layer, width=None):
        """Reserve the corridor a-b (mm) on a routing layer index for ``net`` without adding copper: the cells a track of the net's
        width would occupy there (and the via centres it would exclude) are marked with the net's code, so foreign tracks keep clear
        of a port's exit until the net itself routes through it."""
        g = self.grid; code = self.code[net]; clearance = self.clearance_for(net)
        width = self.width_for(net) if width is None else float(width)
        lane = (tuple(a), tuple(b), net, int(layer), width)
        self._lanes.append(lane)
        self._lane_memory.setdefault(net, []).append(lane) if lane not in self._lane_memory.get(net, []) else None
        g.segment(g.occ[layer], a, b, width / 2 + clearance + self.trace / 2 + self.eps, code, alt=g.alt[layer])
        g.segment(g.vocc, a, b, width / 2 + clearance + self.via_d / 2 + self.eps, code)

    def route_net(self, net, ports=None, layers=None, allow_front_fallback=True):
        """Connect the ports of ``net`` with the shortest available connections first (Kruskal over the manhattan
        distances of the port pairs, merging components).

        ``ports`` default to the fanout ports; ``layers`` to ``default_layers``. Critical nets are forced to the
        front layer. When a path fails and the net is neither critical nor power, ``allow_front_fallback`` retries
        on every layer. A failed pair does not drop a port: when the search ran dry before the node budget one side
        sits in an enclosed pocket, and the side whose reachable area is smaller (the reverse search, capped at the
        forward count, tells which) is retired; a port that twice exhausts the budget is retired as well. The other
        ports keep merging, so a sealed port costs the net one connection instead of every connection from it.
        Returns one failure record per missing connection (also appended to ``unresolved``).
        """
        ports = list(self.ports.get(net, []) if ports is None else ports)
        layers = tuple(self.default_layers(net) if layers is None else layers)
        critical = self.is_critical(net)
        def resolve(p):
            layer = 0 if critical else p[2]
            return (p[0], p[1], layer)  # None (plated through pad / pre-routed via): any routing layer may start or end there
        points = list(dict.fromkeys(resolve(p) for p in ports))
        if len(points) < 2:
            return []
        g = self.grid
        fallback = allow_front_fallback and not critical and not self.is_power(net)
        every = tuple(range(self.nl))
        parent = list(range(len(points)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]; i = parent[i]
            return i

        def occ_at(p):
            return int(g.occ[layers[0] if p[2] is None else p[2], p[1], p[0]])

        def search(a, b, cap=None):
            path = self.astar(a, b, net, layers=layers, max_nodes=cap)
            expanded = int(getattr(g, 'last_expanded', 0))
            if path is None and fallback:
                path = self.astar(a, b, net, layers=every, max_nodes=cap)
                expanded = max(expanded, int(getattr(g, 'last_expanded', 0)))
            return path, expanded
        pairs = sorted((abs(a[0] - b[0]) + abs(a[1] - b[1]), i, j) for i, a in enumerate(points) for j, b in enumerate(points) if i < j)
        retired, strikes, last_failure, components = set(), defaultdict(int), {}, len(points)
        for _, i, j in pairs:
            if components < 2:
                break
            if i in retired or j in retired or find(i) == find(j):
                continue
            a, b = points[i], points[j]
            path, expanded = search(a, b)
            if path is None and expanded <= self.max_nodes:
                # ran dry: one side is enclosed; the reverse search (capped at the forward count) measures the other side
                back, back_expanded = search(b, a, cap=max(1, expanded))
                if back is not None:
                    path, a, b = back, b, a
                else:
                    retired.add(j if back_expanded <= expanded else i)
            elif path is None:
                for k in (i, j):
                    strikes[k] += 1
                    if strikes[k] >= 2:
                        retired.add(k)
            if path is not None:
                self.emit(path, net); parent[find(i)] = find(j); components -= 1
                continue
            record = dict(stage='route', net=net, start=a, end=b, expanded=expanded,
                          occupancy=dict(start=occ_at(a), end=occ_at(b), code=self.code[net]))
            last_failure[i] = record; last_failure[j] = record
        failures = []
        if components > 1:  # one record per component that stays apart from the largest one
            members = defaultdict(list)
            for i in range(len(points)):
                members[find(i)].append(i)
            main = max(members.values(), key=len)
            for group in members.values():
                if group is main:
                    continue
                k = next((m for m in group if m in last_failure), group[0])
                record = last_failure.get(k) or dict(stage='route', net=net, start=points[k], end=points[main[0]], expanded=0,
                                                       occupancy=dict(start=occ_at(points[k]), end=occ_at(points[main[0]]), code=self.code[net]))
                failures.append(record); self.unresolved.append(record)
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

    # ----- snapshot / restore (order trials) -----------------------------------------------------
    def snapshot(self):
        """Capture the occupancy grids, via map, lengths, stats and unresolved list; start recording created items."""
        g = self.grid
        state = dict(occ=g.occ.copy(), vocc=g.vocc.copy(), holes=g.holes.copy(), alt=g.alt.copy(), vias=dict(self.vias),
                     length=dict(self.length), stats=dict(self.stats), unresolved=list(self.unresolved))
        self.created = []
        return state

    def restore(self, state):
        """Remove every item created since ``snapshot`` and put the router back into the captured state."""
        g = self.grid
        for item in self.created or ():
            self.board.Remove(item)
        self.created = []
        g.occ[...] = state['occ']; g.vocc[...] = state['vocc']; g.holes[...] = state['holes']
        if 'alt' in state:
            g.alt[...] = state['alt']
        self.vias = dict(state['vias'])
        self.length = defaultdict(float, state['length'])
        self.stats = defaultdict(int, state['stats'])
        self.unresolved = list(state['unresolved'])

    def end_snapshot(self):
        """Stop recording created items (the current state is kept)."""
        self.created = None

    # ----- rip-up and re-route -----------------------------------------------------------------
    def rebuild_occupancy(self):
        """Recompute every occupancy array from the board (pads, keepouts, all tracks and vias on it)."""
        g = self.grid
        g.occ[...] = 0; g.vocc[...] = 0; g.holes[...] = 0; g.transitions[...] = 0; g.zocc[...] = 0; g.alt[...] = 0
        m = g.margin
        if m:
            g.occ[:, :m, :] = -1; g.occ[:, -m:, :] = -1; g.occ[:, :, :m] = -1; g.occ[:, :, -m:] = -1
            g.vocc[:m, :] = -1; g.vocc[-m:, :] = -1; g.vocc[:, :m] = -1; g.vocc[:, -m:] = -1
        self.vias = {}; self.through = []; self.pad_records = []
        self.length = defaultdict(float)
        self._register_pads()
        keepouts = list(self._keepouts)
        self._keepouts = []
        for layer, x0, y0, x1, y1, code, block_vias, *zone in keepouts:
            self.keepout(layer, x0, y0, x1, y1, code, block_vias, bool(zone and zone[0]))
        self._register_existing()
        lanes = list(self._lanes)
        self._lanes = []
        for a, b, net, layer, width in lanes:  # the reserved exit corridors are not board items: replay them
            self._reserve_lane(a, b, net, layer, width)

    def rip_net(self, net):
        """Remove the recorded signal-stage items of ``net`` from the board and drop its route failures."""
        for item in self.net_items.get(net, []):
            self.board.Remove(item)
        self.net_items[net] = []
        self.unresolved = [u for u in self.unresolved if not (u.get('stage') == 'route' and u.get('net') == net)]

    def signal_geometry(self):
        """Serialisable copy of every recorded signal-stage item (for restoring the best negotiation state)."""
        pcb = self.pcb
        out = {}
        for net, items in self.net_items.items():
            recs = []
            for it in items:
                if isinstance(it, pcb.PCB_VIA):
                    recs.append(('via', tuple(pcb.ToMM(it.GetPosition())), pcb.ToMM(it.GetWidth(pcb.F_Cu)), pcb.ToMM(it.GetDrillValue())))
                elif isinstance(it, pcb.PCB_ARC):  # before the track branch (a PCB_ARC is a PCB_TRACK): never serialise an arc as its chord
                    recs.append(('arc', tuple(pcb.ToMM(it.GetStart())), tuple(pcb.ToMM(it.GetMid())), tuple(pcb.ToMM(it.GetEnd())),
                                 self.layers.index(it.GetLayer()), pcb.ToMM(it.GetWidth())))
                else:
                    recs.append(('track', tuple(pcb.ToMM(it.GetStart())), tuple(pcb.ToMM(it.GetEnd())), self.layers.index(it.GetLayer()), pcb.ToMM(it.GetWidth())))
            out[net] = recs
        return out

    def restore_signal_geometry(self, geometry, unresolved):
        """Replace the recorded signal-stage items by ``geometry`` (see signal_geometry) and rebuild the occupancy."""
        for net in list(self.net_items):
            for item in self.net_items[net]:
                self.board.Remove(item)
            self.net_items[net] = []
        self.rebuild_occupancy()
        for net, recs in geometry.items():
            self.recording_net = net
            for rec in recs:
                if rec[0] == 'via':
                    self.via(rec[1], net, rec[2], rec[3])
                elif rec[0] == 'arc':
                    self.arc(rec[1], rec[2], rec[3], net, rec[4], rec[5])
                else:
                    self.track(rec[1], rec[2], net, rec[3], rec[4])
            self.recording_net = None
        self.unresolved = list(unresolved)

    def negotiate(self, layers, allow_front_fallback=True, rounds=20, penalty=40.0, protected=(), tabu=4):
        """Rip-up and re-route the unresolved signal connections; returns the log of rounds.

        For each failed connection a soft A* finds a path across other signal nets' copper; those nets are ripped up,
        the failed connection is routed first and the ripped nets are re-routed. A round is kept when the unresolved
        count does not grow and the resulting set of failures is new (a set seen before is a cycle and is reverted).
        The targets of the last ``tabu`` kept rounds cannot be ripped again, so two connections fighting over the same
        lane do not alternate forever. ``protected`` nets are never ripped.
        """
        log = []
        protected = set(protected)
        code_to_net = {code: name for name, code in self.code.items()}
        layers = tuple(layers)
        attempted = set()
        penalties = (float(penalty),)  # one attempt per failing connection and failure set (the 0.4x / 2.5x variants never succeeded in the stage-4 runs)
        last_failure_set = None
        seen = set()
        recent = []
        recent_targets = []
        for rnd in range(rounds):
            current = [u for u in self.unresolved if u.get('stage') == 'route']
            failing = {u['net'] for u in current}
            self.release_lanes({lane[2] for lane in self._lanes if lane[2] not in failing})  # routed nets no longer need their corridors
            failure_set = frozenset((u['net'], tuple(u['start']), tuple(u['end'])) for u in current)
            seen.add(failure_set)
            if failure_set != last_failure_set:
                attempted = set()  # the failing connections changed: every (connection, penalty) is worth another try
                last_failure_set = failure_set
            candidates = [(u, pen) for u in current for pen in penalties if (u['net'], tuple(u['start']), tuple(u['end']), pen) not in attempted]
            if not candidates:
                break
            fresh = [c for c in candidates if c[0]['net'] not in recent_targets]  # take turns between the failing nets
            target, pen = (fresh or candidates)[0]
            recent_targets.append(target['net']); del recent_targets[:-3]
            attempted.add((target['net'], tuple(target['start']), tuple(target['end']), pen))
            net = target['net']
            before_geometry, before_unresolved = self.signal_geometry(), list(self.unresolved)
            before_count = len(current)
            start, end = tuple(target['start']), tuple(target['end'])
            own = self.code[net]
            direct = self._hard_path(start, end, net, layers, allow_front_fallback)
            if direct is not None:  # routable now: copper moved by an earlier round, nothing to rip
                self.recording_net = net; self.emit(direct, net); self.recording_net = None
                self.unresolved = [u for u in self.unresolved if u is not target]
                log.append(dict(round=rnd, net=net, penalty=pen, result=f'routed directly ({before_count} -> {before_count - 1})'))
                continue
            blocked = protected | {n for n in recent if n != net}
            rippable = {self.code[n] for n in self.net_items if n not in blocked and n != net and self.net_items[n]}
            allowed, via_allowed = self.region_masks(net)
            path = self.grid.astar_soft(start, end, own, layers, penalty=pen, max_nodes=self.max_nodes, rippable=rippable,
                                        allowed=allowed, via_allowed=via_allowed)
            if path is None:
                log.append(dict(round=rnd, net=net, penalty=pen, result='no soft path'))
                continue
            victims = set()
            g = self.grid
            for (x, y, l) in path:
                v = int(g.occ[l, y, x])
                if v == -2:
                    v = int(g.alt[l, y, x])  # the newer owner of a soft conflict cell
                if v > 0 and v != own and code_to_net.get(v) in self.net_items and code_to_net[v] not in protected:
                    victims.add(code_to_net[v])
            segments, via_cells = compress_path(path)
            for (x, y) in via_cells:
                v = int(g.vocc[y, x])
                if v > 0 and v != own and code_to_net.get(v) in self.net_items and code_to_net[v] not in protected:
                    victims.add(code_to_net[v])
            victims = sorted(victims)
            if not victims:
                log.append(dict(round=rnd, net=net, penalty=pen, result='soft path crosses no rippable net'))
                continue
            for victim in victims:
                self.rip_net(victim)
            self.rip_net(net)
            self.restore_lanes(set(victims) | {net})  # the ripped nets' port exits stay open while the target routes first
            self.rebuild_occupancy()
            self.recording_net = net
            self.route_net(net, layers=layers, allow_front_fallback=allow_front_fallback)
            self.recording_net = None
            for victim in victims:
                self.recording_net = victim
                self.route_net(victim, layers=layers, allow_front_fallback=allow_front_fallback)
                self.recording_net = None
            after = [u for u in self.unresolved if u.get('stage') == 'route']
            after_count = len(after)
            after_set = frozenset((u['net'], tuple(u['start']), tuple(u['end'])) for u in after)
            if after_count > before_count:
                self.restore_signal_geometry(before_geometry, before_unresolved)
                log.append(dict(round=rnd, net=net, penalty=pen, victims=victims, result=f'reverted ({after_count} > {before_count})'))
            elif after_count == before_count and after_set in seen:
                self.restore_signal_geometry(before_geometry, before_unresolved)
                log.append(dict(round=rnd, net=net, penalty=pen, victims=victims, result=f'reverted (cycle: failure set seen before)'))
            else:
                log.append(dict(round=rnd, net=net, penalty=pen, victims=victims, result=f'kept ({before_count} -> {after_count})'))
                recent.append(net)
                if tabu:
                    del recent[:-int(tabu)]
                else:
                    recent.clear()
        return log

    def release_lanes(self, nets=None):
        """Drop the reserved exit corridors of ``nets`` (every lane when None) and rebuild the occupancy; returns the number dropped.
        A routed net's lane is obsolete (its track occupies what it needs), and before the final retry pass every lane is: the
        corridors reserved for other ports are free copper for the connections that are still open."""
        before = len(self._lanes)
        self._lanes = [] if nets is None else [lane for lane in self._lanes if lane[2] not in nets]
        if len(self._lanes) != before:
            self.rebuild_occupancy()
        return before - len(self._lanes)

    def restore_lanes(self, nets):
        """Re-list the remembered exit corridors of ``nets`` (dropped by release_lanes) without rebuilding the occupancy; returns
        the number re-listed. The caller rebuilds the occupancy (negotiate does so after the rip-up)."""
        active = set(self._lanes)
        added = 0
        for net in nets:
            for lane in self._lane_memory.get(net, []):
                if lane not in active:
                    self._lanes.append(lane); active.add(lane); added += 1
        return added

    def _hard_path(self, start, end, net, layers, allow_front_fallback=True):
        """Plain A* for one connection on ``layers`` (then on every layer when the fallback applies); None when no path exists."""
        path = self.astar(start, end, net, layers=tuple(layers))
        if path is None and allow_front_fallback and not self.is_critical(net) and not self.is_power(net):
            path = self.astar(start, end, net, layers=tuple(range(self.nl)))
        return path

    def retry_unresolved(self, layers, allow_front_fallback=True):
        """Route the unresolved signal connections whose ports have become mutually reachable (copper moved by later nets' rip-up
        rounds or by the order replay); returns the number routed. Each record gets one hard search."""
        routed = 0
        for keep_own in (True, False):  # first with the open nets' own corridors still reserved, then without any lane
            failing = {u['net'] for u in self.unresolved if u.get('stage') == 'route'}
            self.release_lanes({lane[2] for lane in self._lanes if lane[2] not in failing} if keep_own else None)
            for record in [u for u in self.unresolved if u.get('stage') == 'route']:
                net = record['net']
                if net not in self.code:
                    continue
                path = self._hard_path(tuple(record['start']), tuple(record['end']), net, layers, allow_front_fallback)
                if path is None:
                    continue
                self.recording_net = net; self.emit(path, net); self.recording_net = None
                self.unresolved = [u for u in self.unresolved if u is not record]
                routed += 1
        self.stats['retried'] += routed
        return routed

    def net_span(self, net):
        """Manhattan extent (cells) of a net's ports: a proxy for the routing length the net needs."""
        pts = self.ports.get(net, [])
        if len(pts) < 2:
            return 0
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

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
        """Remove vias whose net touches them on fewer than two layers; returns the count removed.

        Nets in ``exclude_nets`` (zone nets) are kept. A via is removed only when at least two items of its net
        overlap it (tracks ending at or running through its ring, pads under it), so no track end is left dangling:
        a pre-routed escape via whose port the router left on the via's own layer is such a case, a via with copper
        on two or more layers is a real layer change and stays. Grid occupancy is left reserved.
        """
        pcb = self.pcb; exclude = set(exclude_nets)
        segments = defaultdict(list)
        for item in self.board.GetTracks():
            if isinstance(item, pcb.PCB_VIA):
                continue
            a, b = item.GetStart(), item.GetEnd()
            if isinstance(item, pcb.PCB_ARC):  # an arc touches a via only at its ends: test its two chords (a-mid, mid-b)
                m = item.GetMid()
                segments[item.GetNetCode()].append((a.x, a.y, m.x, m.y, item.GetWidth() / 2, item.GetLayer()))
                segments[item.GetNetCode()].append((m.x, m.y, b.x, b.y, item.GetWidth() / 2, item.GetLayer()))
                continue
            segments[item.GetNetCode()].append((a.x, a.y, b.x, b.y, item.GetWidth() / 2, item.GetLayer()))
        pads = defaultdict(list)
        for pad in self.board.GetPads():
            pads[pad.GetNetCode()].append(pad)
        removed = 0
        for via in [t for t in self.board.GetTracks() if isinstance(t, pcb.PCB_VIA)]:
            if via.GetNetname() in exclude:
                continue
            xy = via.GetPosition()
            ring = via.GetWidth(pcb.F_Cu) / 2  # KiCad 10: via width needs a layer
            touching = [layer for ax, ay, bx, by, half, layer in segments[via.GetNetCode()]
                        if point_segment_distance(xy.x, xy.y, ax, ay, bx, by) <= ring + half]
            for pad in pads[via.GetNetCode()]:
                if pad.HitTest(xy):
                    touching.extend(layer for layer in self.layers if pad.IsOnLayer(layer))
            if len(set(touching)) < 2 and len(touching) >= 2:
                self.board.Remove(via); removed += 1
                self.vias.pop(self._key(tuple(pcb.ToMM(xy))), None)
        self.stats['pruned_unused_vias'] += removed
        return removed

    # ----- V2.1 geometry: policy, clearance tests and the final beautify stage -------------------------
    def smooth_policy(self, net):
        """'none' | 'diagonal' | 'arc' for ``net``: the net rule ``smooth`` wins, then ``style.straight_nets`` (names or prefixes),
        then power/critical nets and tracks wider than ``max_width_for_arcs_mm`` get diagonals only; arcs need ``style.arcs``."""
        cfg = self.style
        rule = self.net_rules.get(net, {}).get('smooth')
        if rule:
            if rule not in SMOOTH_POLICIES:
                raise ValueError(f'net rule smooth of {net!r} must be one of {SMOOTH_POLICIES}')
            return rule
        if any(net == pat or net.startswith(pat) for pat in cfg['straight_nets']):
            return 'none'
        active = cfg['simplify'] != 'none' or cfg['arcs']
        if not active:
            return 'none'
        if (self.is_power(net) and not cfg['smooth_power']) or (self.is_critical(net) and not cfg['smooth_critical']):
            return 'diagonal'
        if self.width_for(net) > float(cfg['max_width_for_arcs_mm']):
            return 'diagonal'
        return 'arc' if cfg['arcs'] else 'diagonal'

    def _mask_for(self, net, layer, width, dilate_cells=0):
        """Cached foreign mask of ``net`` on a routing layer index (see Grid.foreign_mask); the cache holds one net at a time."""
        cache = getattr(self, '_mask_cache', None)
        if cache is None or cache[0] != net:
            cache = self._mask_cache = (net, {})
        key = (layer, round(float(width), 6), int(dilate_cells))
        if key not in cache[1]:
            g = self.grid
            extra = self.extra_for(net, width)[0] / g.grid
            cache[1][key] = g.foreign_mask(layer, self.code[net], extra=extra, region=self.region_masks(net)[0], dilate_cells=dilate_cells)
        return cache[1][key]

    def check_cells(self, net, layer, cells, width):
        """True when the on-grid octilinear polyline ``cells`` of ``net`` (routing layer index, track ``width``) is as clear as a
        path of the 8-direction search would be (foreign halos with the net's extra dilation, zone keep-outs, region, corner rule)."""
        return self.grid.cells_free(self._mask_for(net, layer, width), cells)

    def check_arc(self, net, layer, a, m, b, width):
        """True when every point of the arc a-m-b (mm) keeps the net's clearance: the arc is sampled at half a cell and the nearest
        cell of every sample must be clear of the foreign mask dilated by ``style.arc_dilate_cells`` more cells than the search uses,
        which covers the up to half-diagonal offset of an off-grid point from its cell centre (conservative by about one cell)."""
        g = self.grid
        mask = self._mask_for(net, layer, width, dilate_cells=int(self.style['arc_dilate_cells']))
        return g.samples_free(mask, pg.sample_arc(a, m, b, g.grid / 2))

    def _fillet_chain(self, net, layer, points, width, keep_start, keep_end, exceptions):
        """Replace the interior corners of the mm polyline ``points`` by tangent arcs where the adaptive radius search finds a clear
        one; returns [('seg', a, b) | ('arc', a, m, b)]. ``keep_start``/``keep_end`` (mm) stay straight at the chain ends."""
        cfg = self.style
        r_min_cfg, r_pref_cfg, r_max = cfg['arc_radius_mm']
        r_min = max(r_min_cfg or width, self.grid.grid)
        r_pref = min(r_pref_cfg or 2.0 * width, r_max)
        min_turn, max_turn = float(cfg['min_turn_deg']), float(cfg['max_turn_deg'])
        n = len(points)
        turns = [abs(pg.turn_angle(points[i - 1], points[i], points[i + 1])) for i in range(1, n - 1)]
        candidate = [min_turn <= t <= max_turn for t in turns]
        legs = [math.dist(points[i], points[i + 1]) for i in range(n - 1)]
        prims = []
        cursor = points[0]
        for i in range(1, n - 1):
            p0, p1, p2 = points[i - 1], points[i], points[i + 1]
            theta = turns[i - 1]
            if not candidate[i - 1]:
                prims.append(('seg', cursor, p1)); cursor = p1
                continue
            room1 = legs[i - 1] - keep_start if i == 1 else (legs[i - 1] / 2 if candidate[i - 2] else legs[i - 1])
            room2 = legs[i] - keep_end if i == n - 2 else (legs[i] / 2 if candidate[i] else legs[i])
            d_max = min(room1, room2)
            tan_half = math.tan(math.radians(theta) / 2)
            r_cap = min(r_pref, d_max / tan_half if tan_half > 1e-12 else r_pref)
            chosen = None
            if r_cap >= r_min - 1e-9:
                radii = []
                r = r_cap
                for _ in range(int(cfg['arc_steps'])):
                    radii.append(max(r, r_min)); r *= 0.7
                    if r < r_min:
                        break
                if radii[-1] > r_min + 1e-9:
                    radii.append(r_min)
                tested = False
                for r in radii:
                    f = pg.fillet_corner(p0, p1, p2, r)
                    if f is None:
                        break
                    a, m, b, d, _ = f
                    if d > d_max + 1e-9:
                        continue
                    tested = True
                    if self.check_arc(net, layer, a, m, b, width):
                        chosen = (a, m, b, r)
                        break
                reason = None if chosen else ('clearance' if tested else 'leg_too_short')   # 'clearance' only when an arc sample test failed
            else:
                reason = 'pad_exit' if (i == 1 and keep_start >= legs[0] - 1e-9) or (i == n - 2 and keep_end >= legs[-1] - 1e-9) else 'leg_too_short'
            if chosen is None:
                exceptions.append(dict(net=net, layer=self.names[layer], xy=[round(p1[0], 4), round(p1[1], 4)], turn_deg=round(theta, 1),
                                       width=width, kind=f'bend_{int(round(theta / 45.0) * 45)}', reason=reason))
                prims.append(('seg', cursor, p1)); cursor = p1
                continue
            a, m, b, r = chosen
            if math.dist(cursor, a) > 1e-9:
                prims.append(('seg', cursor, a))
            prims.append(('arc', a, m, b)); cursor = b
            self.stats['fillets'] += 1
        prims.append(('seg', cursor, points[-1]))
        return [p for p in prims if p[0] == 'arc' or math.dist(p[1], p[2]) > 1e-9]

    def beautify(self):
        """Final geometric clean-up of the router's own copper (plan ``style``): per chain between pads, vias, junctions and
        copper of other stages, octilinear string pulling, short-run collapse and on-grid chamfers (policy 'diagonal' or 'arc'),
        then tangent fillets (policy 'arc'). Every candidate is validated against the current occupancy; a chain whose rewrite
        fails any check is kept whole. Lengths and stats are adjusted item by item. Returns the stage report.

        Conservatism: the occupancy (occ/vocc/alt) of a rewritten chain's old items is not cleared - the new primitives are only added -
        so chains of other nets handled later in the pass are also tested against the stale halos of already rewritten copper. This
        costs smoothing room (more 'clearance' exceptions) but can never admit a violation."""
        pcb = self.pcb; g = self.grid; cfg = self.style
        t0 = time.monotonic()
        stages = set(cfg['stages'])
        if cfg['simplify'] == 'none' and not cfg['arcs']:
            return dict(enabled=False)
        policy = {}
        items, fixed = [], set()
        layer_index = {layer: i for i, layer in enumerate(self.layers)}
        all_items = list(self.board.GetTracks())
        for it in all_items:
            if isinstance(it, pcb.PCB_VIA):
                p = it.GetPosition(); fixed.add((int(p.x), int(p.y)))
                continue
            a, b = it.GetStart(), it.GetEnd()
            ka, kb = (int(a.x), int(a.y)), (int(b.x), int(b.y))
            net = it.GetNetname()
            idx = layer_index.get(it.GetLayer())
            if net not in policy:
                policy[net] = self.smooth_policy(net) if net in self.code else 'none'
            eligible = (idx is not None and not isinstance(it, pcb.PCB_ARC) and policy[net] != 'none'
                        and self.item_stage.get(it.m_Uuid.AsString()) in stages)
            if eligible:
                items.append(dict(id=it.m_Uuid.AsString(), net=net, layer=idx, a=ka, b=kb, width=pcb.ToMM(it.GetWidth()), item=it))
            else:
                fixed.add(ka); fixed.add(kb)
        pads_of = defaultdict(list)
        for pad in self.board.GetPads():
            pads_of[pad.GetNetname()].append(pad)
        endpoints = {(rec['net'], key) for rec in items for key in (rec['a'], rec['b'])}
        for net, key in endpoints:  # a node inside a pad is an anchor even when two router tracks pass through it (a Kruskal tree node)
            point = pcb.VECTOR2I(key[0], key[1])
            if any(pad.HitTest(point) for pad in pads_of.get(net, ())):
                fixed.add(key)
        by_id = {rec['id']: rec for rec in items}
        chains = pg.chains_from_items(items, fixed)
        counts = Counter(); kept = Counter(); exceptions = self.exceptions
        before = dict(segments=len(items), length=0.0, bends=Counter()); after = dict(segments=0, arcs=0, length=0.0, bends=Counter())
        l_short_cfg = cfg['l_short_mm']
        self.stage = 'beautify'
        for chain in chains:
            net, layer, width = chain['net'], chain['layer'], float(chain['width'])
            pol = policy[net]
            counts['chains'] += 1; counts[f'policy_{pol}'] += 1
            cells, ok = [], True
            for key in chain['points']:
                mm = (pcb.ToMM(key[0]), pcb.ToMM(key[1]))
                c = g.to_grid(*mm)
                back = g.to_mm(*c)
                if abs(pcb.FromMM(back[0]) - key[0]) > 0 or abs(pcb.FromMM(back[1]) - key[1]) > 0:
                    ok = False
                    break
                cells.append(c)
            old_mm = [g.to_mm(*c) for c in cells] if ok else [(pcb.ToMM(k[0]), pcb.ToMM(k[1])) for k in chain['points']]
            old_len = pg.polyline_length(old_mm)
            before['length'] += old_len
            for i in range(1, len(old_mm) - 1):
                before['bends'][pg.classify_bend(pg.turn_angle(old_mm[i - 1], old_mm[i], old_mm[i + 1]))] += 1
            if not ok:
                kept['off_grid'] += 1; self._keep_chain(chain, old_mm, after); continue
            if len(cells) < 3:
                kept['straight'] += 1; self._keep_chain(chain, old_mm, after); continue
            # chain ends: a pad exit stays straight as a whole; a via keeps via_d/2 + clearance; other anchors keep corner_keep.port
            def end_kind(key):
                mm = pcb.VECTOR2I(key[0], key[1])
                if any(pad.HitTest(mm) for pad in pads_of.get(net, ())):
                    return 'pad'
                if key in fixed and self.vias.get(self._key((pcb.ToMM(key[0]), pcb.ToMM(key[1])))) == net:
                    return 'via'
                return 'port'
            kinds = (end_kind(chain['points'][0]), end_kind(chain['points'][-1]))
            keep_via = cfg['corner_keep_mm']['via']
            keep_via = self.via_d / 2 + self.clearance_for(net) if keep_via is None else float(keep_via)
            keep_mm = [keep_via if k == 'via' else float(cfg['corner_keep_mm']['port']) if k == 'port' else None for k in kinds]
            work = list(cells)
            keep_cells = [int(math.ceil(k / g.grid - 1e-9)) if k is not None else 0 for k in keep_mm]
            head = [work[0]] if kinds[0] == 'pad' and len(work) > 2 else []   # the pad exit leg is frozen
            tail = [work[-1]] if kinds[1] == 'pad' and len(work) > 2 else []
            core = work[len(head):len(work) - len(tail)]
            # corner_keep_mm.via: no diagonal of a shortcut / short-run / chamfer candidate may come closer than keep_cells to a via end,
            # so the via is always left by a straight orthogonal run of at least that length (the fillet stage keeps keep_mm as well)
            guards = [((cells[0], cells[-1])[k], keep_cells[k]) for k in (0, 1) if kinds[k] == 'via' and keep_cells[k] > 0]
            is_clear = lambda poly, _n=net, _l=layer, _w=width, _g=guards: pg.diagonals_clear_of(poly, _g) and self.check_cells(_n, _l, poly, _w)
            if cfg['simplify'] == 'octilinear' and len(core) >= 3:
                l_short = (l_short_cfg or max(2 * width, 4 * g.grid)) / g.grid
                core = pg.shortcut(core, is_clear)
                core = pg.collapse_short_runs(core, l_short, is_clear)
                if cfg['chamfer']:
                    core = pg.chamfer(core, is_clear, min_cut=2, keep_start=keep_cells[0] if not head else 0, keep_end=keep_cells[1] if not tail else 0)
            new_cells = pg.merge_collinear(head + core + tail)
            new_mm = [g.to_mm(*c) for c in new_cells]
            if new_cells[0] != cells[0] or new_cells[-1] != cells[-1] or pg.polyline_length(new_mm) > old_len + 1e-6:
                kept['length_check'] += 1; self._keep_chain(chain, old_mm, after); continue
            if not all(self.check_cells(net, layer, [p, q], width) for p, q in zip(new_cells, new_cells[1:]) if (p, q) not in zip(cells, cells[1:])):
                kept['clearance_recheck'] += 1; self._keep_chain(chain, old_mm, after); continue
            if pol == 'arc' and len(new_mm) >= 3:
                keep = [math.dist(new_mm[0], new_mm[1]) if kinds[0] == 'pad' else keep_mm[0], math.dist(new_mm[-2], new_mm[-1]) if kinds[1] == 'pad' else keep_mm[1]]
                prims = self._fillet_chain(net, layer, new_mm, width, keep[0], keep[1], exceptions)
            else:
                prims = [('seg', p, q) for p, q in zip(new_mm, new_mm[1:])]
                for i in range(1, len(new_mm) - 1):
                    theta = abs(pg.turn_angle(new_mm[i - 1], new_mm[i], new_mm[i + 1]))
                    if theta >= float(cfg['min_turn_deg']):
                        exceptions.append(dict(net=net, layer=self.names[layer], xy=[round(new_mm[i][0], 4), round(new_mm[i][1], 4)], turn_deg=round(theta, 1),
                                               width=width, kind=f'bend_{int(round(theta / 45.0) * 45)}', reason=f'policy_{pol}'))
            if prims == [('seg', p, q) for p, q in zip(old_mm, old_mm[1:])]:
                kept['unchanged'] += 1; self._keep_chain(chain, old_mm, after); continue
            # write back: remove the old items (exact length bookkeeping), create the new ones
            for edge in chain['edges']:
                rec = by_id[edge['id']]
                self.board.Remove(rec['item']); self.item_stage.pop(edge['id'], None)
                self.stats['tracks'] -= 1
            self.length[net] -= old_len
            removed = {edge['id'] for edge in chain['edges']}
            if net in self.net_items:
                self.net_items[net] = [it for it in self.net_items[net] if it.m_Uuid.AsString() not in removed]
            self.recording_net = net if net in self.net_items else None
            for prim in prims:
                if prim[0] == 'seg':
                    self.track(prim[1], prim[2], net, layer, width); after['segments'] += 1
                else:
                    self.arc(prim[1], prim[2], prim[3], net, layer, width); after['arcs'] += 1
            self.recording_net = None
            after['length'] += sum(math.dist(p[1], p[2]) if p[0] == 'seg' else pg.arc_length(p[1], p[2], p[3]) for p in prims)
            self._count_bends(prims, after['bends'])
            counts['rewritten'] += 1
        self._mask_cache = None
        by_reason = Counter(e['reason'] for e in exceptions)
        return dict(enabled=True, simplify=cfg['simplify'], arcs=bool(cfg['arcs']), chains=counts['chains'], rewritten=counts['rewritten'],
                    kept=sum(kept.values()), kept_reasons=dict(kept), policies={k[7:]: v for k, v in counts.items() if k.startswith('policy_')},
                    segments_before=before['segments'], segments_after=after['segments'], arcs_after=after['arcs'], fillets=int(self.stats['fillets']),
                    bends_before=dict(before['bends']), bends_after=dict(after['bends']),
                    length_before_mm=round(before['length'], 3), length_after_mm=round(after['length'], 3),
                    exceptions_by_reason=dict(by_reason), exceptions=exceptions[:5000], seconds=round(time.monotonic() - t0, 3))  # the checker joins reasons by position

    def _keep_chain(self, chain, mm, after):
        after['segments'] += len(chain['edges']); after['length'] += pg.polyline_length(mm)
        for i in range(1, len(mm) - 1):
            after['bends'][pg.classify_bend(pg.turn_angle(mm[i - 1], mm[i], mm[i + 1]))] += 1

    @staticmethod
    def _count_bends(prims, bends):
        """Bends between consecutive straight primitives (arc joints are tangent by construction)."""
        for p, q in zip(prims, prims[1:]):
            if p[0] == 'seg' and q[0] == 'seg':
                bends[pg.classify_bend(pg.turn_angle(p[1], p[2], q[2]))] += 1

    def report(self):
        """Summary dict: counts (vias = created minus pruned, i.e. the vias left on the board), pruned vias, unresolved records and
        per-net track length (mm)."""
        return dict(status='requires-native-DRC', tracks=int(self.stats['tracks']), vias=int(self.stats['vias'] - self.stats['pruned_unused_vias']),
                    arcs=int(self.stats['arcs']),
                    zones=int(self.stats['zones']), pruned=int(self.stats['pruned_unused_vias']),
                    unresolved=list(self.unresolved),
                    net_length_mm={net: round(value, 3) for net, value in sorted(self.length.items())},
                    grid=dict(nx=self.grid.nx, ny=self.grid.ny, pitch=self.grid.grid, margin_cells=self.grid.margin,
                              layers=list(self.names), directions=list(self.grid.directions)),
                    style=dict(self.style),
                    stats=dict(self.stats))


# ----- declarative plans ----------------------------------------------------------------------
def validate_plan(plan):
    """Check a routing plan dict (keys, sizes, types) and return a shallow copy.

    Plan keys: ``board`` {width, height, origin?, margin?}; ``layers`` [names];
    ``grid``/``trace``/``clearance``/``hole_clearance`` mm; ``via`` [diameter, drill];
    ``directions`` ['h'|'v'|None per layer]; ``net_rules`` {net: {width, clearance}};
    ``keepouts`` [{layer?, rect:[x0,y0,x1,y1], net?, vias?, zone?}] (``zone`` marks a pour of another net:
    tracks stay out, via barrels may pass); ``net_rules`` may carry ``region`` (list of rects or {layer: [rects],
    'vias': [rects]}) - the only area where that net's tracks and vias may go; ``pre_routed`` {tracks:
    [{net, layer|layers, a, b, width?}], vias: [{net, xy, diameter?, drill?, port?,
    if_allowed?}], via_arrays: [{net, origin, pitch, count, diameter?, drill?, port?}]};
    ``critical`` [nets in order]; ``critical_layers`` [names]; ``power`` {net: {anchors?:
    [refs], stubs?, layers?, zones?: {layer: polygon}, clearance?, priority?,
    min_thickness?, thermal_relief?}}; ``fanout`` {skip_refs?, skip_nets?, skip_pads?,
    inpad_vias?, inward_pads?, order?, escape_layer?, direct_nets?, exact_via_pads? ([[ref, pad], ...]: a via at the exact
    stub's end, port on every layer), direct_lane_mm? (reserved exit corridor of every direct port), exact_lane_pads? ([[ref, pad, mm], ...]:
    reserved corridor beyond the stub end)}; pre-routed vias may carry ``lane: [dx, dy, mm, layer]``; ``signal_order`` [names or prefixes];
    ``signal_layers`` [names]; ``exclude_nets``; ``front_fallback``; ``ground`` {net,
    layers, polygon?, holes?: {layer: [polygon,...]}, clearance?, priority?,
    thermal_relief?}; ``prune_vias``; ``fill``; ``save`` path; ``strict``; ``max_nodes``
    A* expansion budget per path (default 700000); ``signal_order_trials`` number of deterministic
    signal-stage orders tried (the best is kept; default 1); ``ripup_rounds`` rip-up and re-route
    rounds for the connections that stay unresolved (default 0 = off), ``ripup_penalty`` soft-path cost
    per foreign cell (default 40); ``signal_groups`` [[names or prefixes], ...] splits the signal nets into
    independent groups (regions that never meet) routed one after the other, each with its own order trials -
    nets matching no group form a last group; ``style`` {diagonal, bend_penalty_cells, via_cost_cells, heuristic_weight,
    diagonal_pref_factor, simplify, chamfer, arcs, arc_radius_mm, arc_steps, arc_dilate_cells, min_turn_deg, max_turn_deg,
    corner_keep_mm, straight_nets, max_width_for_arcs_mm, smooth_power, smooth_critical, stages, l_short_mm, eps} - the V2.1
    geometry knobs (see ``STYLE_DEFAULTS``; absent = V2 behaviour); ``net_rules[net].smooth`` ('none' | 'diagonal' | 'arc')
    overrides the per-net smoothing policy.
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
    if 'style' in plan and plan['style'] is not None:
        if not isinstance(plan['style'], dict):
            raise ValueError('plan.style must be a dict')
        normalise_style(plan['style'])
    for net, rule in plan.get('net_rules', {}).items():
        if isinstance(rule, dict) and rule.get('smooth') not in (None, *SMOOTH_POLICIES):
            raise ValueError(f'net_rules[{net!r}].smooth must be one of {SMOOTH_POLICIES}')
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


def orders_meta(router, remaining, trials, rank=None, first=()):
    """[(name, order)] of deterministic signal-stage base orders: the plan order, short-span nets first (long nets last),
    long nets first, and (when ``rank`` gives the plan priority rank of a net) the prioritised nets first in rank order
    followed by the rest short-span first (at most ``trials`` entries; further trials are perturbations built in run_plan)."""
    base = list(remaining)
    position = {n: i for i, n in enumerate(base)}
    result = [('plan', base)]
    if trials > 1:
        result.append(('span_asc', sorted(base, key=lambda n: (router.net_span(n), position[n]))))
    if trials > 2:
        result.append(('span_desc', sorted(base, key=lambda n: (-router.net_span(n), position[n]))))
    if trials > 3 and (first or rank is not None):
        if first:  # the plan's signal_first nets, in that order, then everything else short-span first
            prioritised = [n for n in first if n in position]
            rest = [n for n in base if n not in set(prioritised)]
            result.append(('first_span_asc', prioritised + sorted(rest, key=lambda n: (router.net_span(n), position[n]))))
        else:
            ranks = {n: rank(n) for n in base}
            top = max(ranks.values()) if ranks else 0
            prioritised = [n for n in base if ranks[n] < top]
            if prioritised:
                rest = [n for n in base if ranks[n] >= top]
                result.append(('priority_span_asc', sorted(prioritised, key=lambda n: (ranks[n], position[n])) +
                               sorted(rest, key=lambda n: (router.net_span(n), position[n]))))
    return result[:trials]


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
                    directions=plan.get('directions'), max_nodes=plan.get('max_nodes', 700000), style=plan.get('style'))
    router.stage = 'pre_routed'
    for keepout in plan.get('keepouts', ()):
        layer = keepout.get('layer')
        router.keepout(router.layer_index(layer) if isinstance(layer, str) else layer, *keepout['rect'],
                       net=keepout.get('net', -1) if keepout.get('net') is not None else -1, block_vias=bool(keepout.get('vias')),
                       zone=bool(keepout.get('zone')))
    pre = plan.get('pre_routed', {})
    for t in pre.get('tracks', ()):
        for layer in t.get('layers', [t.get('layer')]):
            router.track(tuple(t['a']), tuple(t['b']), t['net'], router.layer_index(layer), t.get('width'), t.get('mark_width'))
    for v in pre.get('vias', ()):
        xy = tuple(v['xy']); gx, gy = router.to_grid(*xy)
        if v.get('if_allowed') and not router.via_allowed(gx, gy, v['net']):
            continue
        router.via(xy, v['net'], v.get('diameter'), v.get('drill'))
        if v.get('port'):
            router.ports[v['net']].append((gx, gy, None, 'PRE_VIA', ''))
        if v.get('lane'):  # [dx, dy, mm, layer]: reserved exit corridor of a pre-routed port via
            dx, dy, length, layer = v['lane']
            router._reserve_lane(xy, (xy[0] + dx * length, xy[1] + dy * length), v['net'],
                                 router.layer_index(layer) if isinstance(layer, str) else int(layer))
    for array in pre.get('via_arrays', ()):
        (x0, y0), (px, py), (count_x, count_y) = array['origin'], array['pitch'], array['count']
        for ix in range(int(count_x)):
            for iy in range(int(count_y)):
                xy = (x0 + ix * px, y0 + iy * py)
                router.via(xy, array['net'], array.get('diameter'), array.get('drill'))
                if array.get('port'):
                    router.ports[array['net']].append((*router.to_grid(*xy), None, 'VIA_ARRAY', ''))
    fan = plan.get('fanout', {})
    router.stage = 'fanout'
    skip_refs, skip_nets = set(fan.get('skip_refs', ())), set(fan.get('skip_nets', ()))
    skip_pads = {tuple(p) for p in fan.get('skip_pads', ())}
    inward = {tuple(p) for p in fan.get('inward_pads', ())}
    exact_pads = {(p[0], p[1]): ((float(p[2]), tuple(p[3]), *p[4:6]) if len(p) > 3 else float(p[2])) if len(p) > 2 else 0.6 for p in fan.get('exact_stub_pads', ())}
    order = list(fan.get('order', ())); rank = {ref: i for i, ref in enumerate(order)}
    escape_layer = fan.get('escape_layer')
    direct_nets = set(fan.get('direct_nets', ()))
    exact_vias = {tuple(p) for p in fan.get('exact_via_pads', ())}
    exact_lanes = {(p[0], p[1]): float(p[2]) for p in fan.get('exact_lane_pads', ())}
    router.fanout(order_key=lambda r: (rank.get(r['ref'], len(order) + (0 if r['ref'].startswith('U') else 1)),
                                       natural_ref_key(r['ref']), pad_sort_key(r['number'])),
                  skip=lambda r: r['ref'] in skip_refs or r['net'] in skip_nets or (r['ref'], r['number']) in skip_pads,
                  inpad_vias=[tuple(p) for p in fan.get('inpad_vias', ())],
                  inward=lambda r: (r['ref'], r['number']) in inward,
                  exact=lambda r: exact_pads.get((r['ref'], r['number'])),
                  escape_layer=router.layer_index(escape_layer) if isinstance(escape_layer, str) else escape_layer,
                  direct=lambda r: r['net'] in direct_nets,
                  exact_via=lambda r: (r['ref'], r['number']) in exact_vias,
                  direct_lane=float(fan.get('direct_lane_mm', 0.0) or 0.0),
                  exact_lane=lambda r: exact_lanes.get((r['ref'], r['number']), 0.0))
    indices = lambda names: tuple(router.layer_index(n) for n in names) if names else None
    critical_layers = indices(plan.get('critical_layers'))
    router.stage = 'critical'
    for net in plan.get('critical', ()):
        if net in router.code:
            router.route_net(net, layers=critical_layers)
    router.stage = 'power'
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
    trials = max(1, int(plan.get('signal_order_trials', 1)))
    first = list(plan.get('signal_first', ()))
    pinned = list(plan.get('signal_pinned', ()))  # names or prefixes routed first (in this order) in every trial order of their group
    # independent signal groups (regions that never meet) are routed one after the other, each with its own order trials
    group_specs = [list(g) for g in plan.get('signal_groups', ())] or [None]
    groups, taken = [], set()
    for group_spec in group_specs:
        if group_spec is None:
            members = [n for n in remaining if n not in taken]
        else:
            members = [n for n in remaining if n not in taken and any(n == pat or n.startswith(pat) for pat in group_spec)]
        taken.update(members); groups.append(members)
    rest = [n for n in remaining if n not in taken]
    if rest:
        groups.append(rest)
    trial_log, selected = [], []
    router.stage = 'signal'
    for group_index, members in enumerate(g for g in groups if g):
        def pin(order):  # the plan's signal_pinned nets (names or prefixes) first, in that order, then the rest in the trial's order
            head = list(dict.fromkeys(n for pat in pinned for n in order if n == pat or n.startswith(pat)))
            return head + [n for n in order if n not in set(head)] if head else list(order)
        meta = [(name, pin(order)) for name, order in orders_meta(router, members, min(trials, 4), rank_net, first)]  # plan order, long nets last, long nets first, first/priority then short first
        best = None
        state = router.snapshot() if trials > 1 else None
        pre_unresolved = len(router.unresolved)
        group_log = []
        index = 0
        while index < trials:
            if index < len(meta):
                name, order = meta[index]
            else:  # refinement: seeded perturbation of the best order so far, the nets that failed in it promoted
                import random
                best_order, failed_before = meta[best[1]][1], best[2]
                rng = random.Random(index)
                rank = {n: i for i, n in enumerate(best_order)}
                spread = 0.15 + 0.1 * (index - len(orders_meta(router, members, min(trials, 4), rank_net, first)))  # widening perturbation
                def key(n):
                    base = rank[n] * (1.0 + rng.uniform(-spread, spread))
                    return base * (0.5 if n in failed_before else 1.0)
                order = pin(sorted(best_order, key=key))
                name = f'perturb_{index}'
                if any(order == o for _, o in meta):
                    break  # no new order to try
                meta.append((name, order))
            if state is not None and index > 0:
                router.restore(state)
                router.net_items = {k: v for k, v in router.net_items.items() if k not in set(members)} if group_index else defaultdict(list)
                router.net_items = defaultdict(list, router.net_items)
            for net in order:
                router.recording_net = net
                router.route_net(net, layers=signal_layers, allow_front_fallback=plan.get('front_fallback', True))
                router.recording_net = None
            new_failures = [u for u in router.unresolved[pre_unresolved:] if u.get('stage') == 'route']
            failed_nets = {u['net'] for u in new_failures}
            unresolved = len(new_failures)
            total = sum(router.length.values())
            group_log.append(dict(trial=index, group=group_index, order=name, unresolved=unresolved, track_mm=round(total, 1), failed_nets=sorted(failed_nets)))
            key = (unresolved, round(total, 3))
            if best is None or key < best[0]:
                best = (key, index, failed_nets)
            if unresolved == 0:
                break
            index += 1
        if state is not None and best is not None and best[1] != len(group_log) - 1:  # replay the best trial onto the board
            router.restore(state)
            router.net_items = defaultdict(list, {k: v for k, v in router.net_items.items() if k not in set(members)})
            for net in meta[best[1]][1]:
                router.recording_net = net
                router.route_net(net, layers=signal_layers, allow_front_fallback=plan.get('front_fallback', True))
                router.recording_net = None
        if state is not None:
            router.end_snapshot()
        trial_log.extend(group_log)
        selected.append(group_log[best[1]]['order'] if group_log and best is not None else None)
    ripup_log = []
    router.stage = 'negotiate'
    if int(plan.get('ripup_rounds', 0)) > 0 and any(u.get('stage') == 'route' for u in router.unresolved):
        ripup_log = router.negotiate(signal_layers if signal_layers else router.default_layers(remaining[0]) if remaining else (0,),
                                     allow_front_fallback=plan.get('front_fallback', True), rounds=int(plan['ripup_rounds']),
                                     penalty=float(plan.get('ripup_penalty', 40.0)), protected=excluded)
    retried = 0
    router.stage = 'retry'
    if any(u.get('stage') == 'route' for u in router.unresolved):  # connections that became routable while later nets moved
        retried = router.retry_unresolved(signal_layers if signal_layers else tuple(range(router.nl)), allow_front_fallback=plan.get('front_fallback', True))
    if plan.get('prune_vias', True):
        router.prune_unused_vias(exclude_nets=set(power) | ({ground_net} if ground_net else set()))
    beautify_report = None
    if router.style['simplify'] != 'none' or router.style['arcs']:  # V2.1 final geometry stage: after pruning, before the ground pours
        beautify_report = router.beautify()
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
    report.update(stage='routed_candidate', seconds=round(time.monotonic() - start, 3), signal_order_trials=trial_log,
                  signal_order_selected=(selected[0] if len(selected) == 1 else selected) if selected else None, ripup_rounds=ripup_log,
                  retried=retried)
    if beautify_report is not None:
        report['beautify'] = beautify_report
    if plan.get('save'):
        report['saved'] = save_and_reload(board, plan['save'])
    if plan.get('strict') and report['unresolved']:
        raise RuntimeError(f"{len(report['unresolved'])} unresolved routing items")
    return report
