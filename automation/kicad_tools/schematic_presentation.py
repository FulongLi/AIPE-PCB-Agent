"""Schematic presentation layer: functional groups, signal-flow lanes, wires, rails, ports (V2.1).

The connectivity layer (part dicts with ref / pads -> nets / pins / page) stays untouched; this module
decides *how* a project is drawn when ProjectSpec.presentation is set:

* net roles - rail (power symbols; supply:'auto' = flag nets plus nets with a power_out pin, minus an
  exclude list), cross (pins on several pages: hierarchical label per sheet, sheet pins and global
  anchors on the root), local (one page: wires plus exactly one global-label name tag), nc (no_connect);
* groups - explicit (Circuit.block() metadata or part['group']) or an automatic fallback that attaches
  two-terminal parts to the anchor (IC / FET / connector) they share a signal net with;
* lanes - every anchor pin owns a horizontal lane leaving the body: shunts to rails hang vertically
  off the lane (rail symbol at their far end), series parts sit inline and continue the lane with the
  next net, the lane ends in a port (cross net), a name tag (local net) or a rail symbol;  consecutive
  rail pins share one bus and one symbol; decoupling capacitors form rows between a rail wire and a
  ground wire;  parts no lane reaches are laid out as free chains;
* sheets - one sheet per page (paper grows A3 -> A2 -> ... instead of continuation sheets), groups
  packed on shelves with headings, root sheet as a port wall with one global anchor per sheet pin;
* a connectivity guard re-derives (ref, pad) -> net from the drawn geometry before anything is written.

Everything is deterministic (model order, sorted keys, 1.27 mm grid) and independent of the project
being drawn; the SiC buck only supplies its groups and rail policy through the presentation dict.
"""
from __future__ import annotations

import json
import math
import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from automation.kicad_tools import native_schematic as ns
from automation.kicad_tools import schematic_wiring as sw
from automation.kicad_tools.native_schematic import Schematic, pins, placed_pins, power_symbol_definition, quote, uid

GRID = 1.27
PITCH = 12.7            # lane slot pitch for hanging parts
CAP_PITCH = 12.7        # decoupling row pitch (room for values such as 0.47u/630V beside each part)
STUB = 2.54
JOG0 = 3.81
GAP = 1.27
TEXT_W = 0.9            # text width per character per mm of size (approximate font metric)
DEFAULT_DOWN_PATTERN = r'(^|_)(GND|PGND|GNDP|VSS|VEE|COM|KS)(_|$|\d)|GND'
RAIL_RANK = ((r'VEE|VSS|PGND|^GND|_GND', 3), (r'GNDP|GND', 2), (r'KS|COM', 1))
DEFAULT_PRESENTATION = dict(style='wired', groups={}, group_titles={}, group_order={}, supply='auto', exclude_supply=[],
                            include_supply=[],     # passive-fed nets promoted to rails (power symbols) in addition to supply
                            down_pattern=DEFAULT_DOWN_PATTERN, paper_escalation=['A3', 'A2', 'A1', 'A0'],
                            title_size=3.5, heading_size=2.5, note_size=1.0, note_width=170, frames=False,
                            label_size=1.27,       # hierarchical labels, name tags and root anchors (KiCad default 1.27)
                            max_row_mm=250.0,      # anchors of one group wrap into a new row beyond this width
                            max_col_mm=180.0,      # free lanes of one group wrap into a new column beyond this height
                            max_wire_mm=150.0,     # longer same-sheet connections are drawn as a pair of name tags
                            loop_slack_mm=12.7,    # a routed wire longer than 1.5 x distance + slack becomes a tag pair
                            min_fill=0.3)          # escalated papers must reach this hull / drawable area ratio (gate floor)
ANCHOR_KINDS = ('IC', 'DSP', 'Q')
DRIVING = ('output', 'power_out', 'open_collector', 'open_emitter', 'tri_state')


def snap(value: float) -> float:
    return round(round(value / GRID) * GRID, 4)


def snap_up(value: float) -> float:
    return round(math.ceil(value / GRID - 1e-6) * GRID, 4)


def r4(value: float) -> float:
    return round(value, 4)


def coerce_presentation(value) -> dict | None:
    """Validated presentation dict (None keeps the legacy drawing); unknown keys raise ValueError."""
    if value is None or value is False:
        return None
    if isinstance(value, str):
        value = dict(style=value)
    if not isinstance(value, dict):
        raise ValueError('presentation must be None, a style name or a dict')
    unknown = set(value) - set(DEFAULT_PRESENTATION)
    if unknown:
        raise ValueError(f'Unknown presentation keys: {sorted(unknown)}')
    result = {**DEFAULT_PRESENTATION, **value}
    if result['style'] == 'legacy':
        return None
    if result['style'] != 'wired':
        raise ValueError(f"presentation style must be 'wired' or 'legacy', got {result['style']!r}")
    if result['supply'] != 'auto' and not isinstance(result['supply'], (list, tuple, set)):
        raise ValueError("presentation.supply must be 'auto' or a list of net names")
    result['groups'] = {str(k): str(v) for k, v in dict(result['groups']).items()}
    result['group_titles'] = {str(k): str(v) for k, v in dict(result['group_titles']).items()}
    result['group_order'] = {str(k): [str(g) for g in v] for k, v in dict(result['group_order']).items()}
    result['exclude_supply'] = [str(n) for n in result['exclude_supply']]
    result['include_supply'] = [str(n) for n in result['include_supply']]
    result['label_size'] = float(result['label_size'])
    re.compile(result['down_pattern'])
    return result


# --- net roles -----------------------------------------------------------------------------------------------------

def classify_nets(parts: list, flag_nets, presentation: dict) -> dict:
    """{net: dict(role, pages, pins, driven, down)} with role in rail / cross / local."""
    pins_by_net = defaultdict(list)
    for part in parts:
        for pad, net in part['nets'].items():
            if net is None:
                continue
            pins_by_net[net].append((part['ref'], pad, part['pins'][pad]['type'], part['page']))
    if presentation['supply'] == 'auto':
        rails = set(flag_nets) | {net for net, items in pins_by_net.items() if any(t == 'power_out' for *_, t, _ in items)}
    else:
        rails = set(presentation['supply'])
    rails |= set(presentation.get('include_supply', ()))
    rails -= set(presentation['exclude_supply'])
    down = re.compile(presentation['down_pattern'])
    result = {}
    for net in sorted(set(pins_by_net) | set(flag_nets)):
        items = pins_by_net.get(net, [])
        pages = sorted({page for *_, page in items})
        role = 'rail' if net in rails else 'cross' if len(pages) > 1 else 'local'
        result[net] = dict(role=role, pages=pages, pins=items, driven=any(t in DRIVING for *_, t, _ in items) or net in flag_nets,
                           down=bool(down.search(net)))
    return result


def rail_rank(net: str) -> int:
    for pattern, rank in RAIL_RANK:
        if re.search(pattern, net):
            return rank
    return 0


def port_shape(net: str, page: str, info: dict) -> str:
    """Hierarchical-label / sheet-pin shape of a cross net on one page from the pin types per page."""
    drivers = {pg for _, _, t, pg in info['pins'] if t in DRIVING}
    if not drivers:
        return 'passive'
    if drivers == {page}:
        return 'output'
    if page in drivers:
        return 'bidirectional'
    return 'input'


# --- groups ----------------------------------------------------------------------------------------------------------

def is_anchor(part: dict) -> bool:
    connected = [n for n in part['nets'].values() if n is not None]
    if part['kind'] in ('H', 'HS', 'TP'):
        return False
    if part['kind'] == 'Q':
        return True
    if len(connected) <= 2:
        return False
    return part['kind'] in ANCHOR_KINDS or len(part['pins']) > 2


def is_mechanical(part: dict) -> bool:
    return part['kind'] in ('H', 'HS') or not any(n is not None for n in part['nets'].values())


def auto_groups(page_parts: list, nets: dict) -> dict:
    """ref -> group id for one page: every anchor opens a group, two-terminal parts follow their signal nets."""
    groups, anchors = {}, [p for p in page_parts if is_anchor(p)]
    page = page_parts[0]['page'] if page_parts else ''
    for anchor in anchors:
        groups[anchor['ref']] = f'{page}/{anchor["ref"]}'
    anchor_nets = {a['ref']: {n for n in a['nets'].values() if n and nets[n]['role'] != 'rail'} for a in anchors}
    pending = [p for p in page_parts if p['ref'] not in groups and not is_mechanical(p)]
    changed = True
    while pending and changed:
        changed = False
        rest = []
        for part in pending:
            signal = {n for n in part['nets'].values() if n and nets[n]['role'] != 'rail'}
            best, score = None, 0
            for anchor in anchors:
                shared = len(signal & anchor_nets[anchor['ref']])
                if shared > score:
                    best, score = anchor['ref'], shared
            if best is None:
                for other in page_parts:
                    if other['ref'] in groups and other['ref'] not in {a['ref'] for a in anchors}:
                        if signal & {n for n in other['nets'].values() if n and nets[n]['role'] != 'rail'}:
                            best = groups[other['ref']]
                            break
                if best:
                    groups[part['ref']] = best
                    changed = True
                    continue
            else:
                groups[part['ref']] = groups[best]
                changed = True
                continue
            rest.append(part)
        pending = rest
    for part in pending:  # rail-only parts: the nearest preceding anchor in model order (decoupling), else misc
        previous = [a for a in anchors if page_parts.index(a) < page_parts.index(part)]
        groups[part['ref']] = groups[previous[-1]['ref']] if previous else (groups[anchors[0]['ref']] if anchors else f'{page}/misc')
    for part in page_parts:
        if is_mechanical(part):
            groups[part['ref']] = f'{page}/mechanical'
    return groups


def group_title(group_id: str, titles: dict, members: list) -> str:
    short = group_id.split('/', 1)[1] if '/' in group_id else group_id
    for key in (group_id, short):
        if key in titles:
            return titles[key]
    tail = group_id.split('/')[-1]
    anchors = [p['ref'] for p in members if is_anchor(p)]
    if tail in anchors:
        part = next(p for p in members if p['ref'] == tail)
        return f'{tail} {part["value"]}'.strip()
    return tail.replace('_', ' ').strip().capitalize() or group_id


# --- geometry ---------------------------------------------------------------------------------------------------------

@dataclass
class Placed:
    ref: str
    unit: int
    part: dict
    name: str
    definition: str
    angle: int = 0
    x: float = 0.0
    y: float = 0.0
    kind: str = 'part'              # part | power | flag
    net: str | None = None          # power / flag symbols
    texts: dict = field(default_factory=dict)   # 'Reference'/'Value' -> (x, y, justify) or None for legacy placement
    hide_reference: bool = False
    hide_value: bool = False
    property_y: float | None = None

    def pins(self) -> dict:
        return placed_pins(self.definition, self.unit, self.x, self.y, self.angle)

    def body(self) -> tuple:
        """(x0, y0, x1, y1) of the body (hull of the inner pin ends and a minimal core)."""
        xs, ys = [self.x], [self.y]
        for p in pins(self.definition, self.unit):
            ix, iy = p['x'] + p['length'] * {0: 1, 180: -1, 90: 0, 270: 0}[int(p['angle']) % 360], \
                p['y'] + p['length'] * {0: 0, 180: 0, 90: 1, 270: -1}[int(p['angle']) % 360]
            ox, oy = ns.transform(ix, iy, self.angle)
            xs.append(self.x + ox)
            ys.append(self.y + oy)
        if self.kind == 'part':
            core = 1.27
            xs += [self.x - core, self.x + core]
            ys += [self.y - core, self.y + core]
        return (r4(min(xs)), r4(min(ys)), r4(max(xs)), r4(max(ys)))

    def shift(self, dx: float, dy: float) -> None:
        self.x, self.y = r4(self.x + dx), r4(self.y + dy)
        self.texts = {k: (r4(v[0] + dx), r4(v[1] + dy), v[2]) if v else None for k, v in self.texts.items()}


def angle_for(definition: str, unit: int, pad: str, outward: tuple) -> int:
    """Rotation at which `pad` of a symbol leaves the body in direction `outward` (sheet coordinates)."""
    for angle in (0, 90, 180, 270):
        info = placed_pins(definition, unit, 0, 0, angle)
        if info[pad]['outward'] == tuple(outward):
            return angle
    raise ValueError(f'pad {pad} cannot face {outward}')


def two_pin_span(definition: str) -> float:
    """Distance between the two connection points of a two-pin symbol."""
    info = pins(definition, 1)
    (a, b) = info[0], info[1]
    return r4(abs(a['x'] - b['x']) + abs(a['y'] - b['y']))


def text_box(x: float, y: float, text: str, size: float, justify: str | None) -> tuple:
    width = max(1.0, TEXT_W * size * len(text))
    if justify and 'left' in justify:
        x0, x1 = x, x + width
    elif justify and 'right' in justify:
        x0, x1 = x - width, x
    else:
        x0, x1 = x - width / 2, x + width / 2
    return (r4(x0), r4(y - size * 0.75), r4(x1), r4(y + size * 0.75))


# --- lane layout -------------------------------------------------------------------------------------------------------

@dataclass
class Lane:
    pin: str                      # anchor pad (or '' for free lanes)
    net: str | None
    kind: str                     # signal | power | bundle | nc | free
    pin_point: tuple
    dx: int                       # +1 right, -1 left
    items: list = field(default_factory=list)
    end: tuple | None = None      # (kind, net) end marker: port | tag | power | open
    above: float = GAP
    below: float = GAP
    length: float = 0.0
    y: float = 0.0
    bundle_pins: list = field(default_factory=list)
    needs_jog: bool = False
    rank: int = 0
    flip: bool = False
    items_start: float = 0.0


class GroupLayout:
    """Lays one group out in a local frame (origin top-left after finishing)."""

    def __init__(self, planner: 'Planner', page: str, group_id: str, members: list):
        self.planner, self.page, self.group_id, self.members = planner, page, group_id, members
        self.placed: list[Placed] = []
        self.segments: list[sw.Segment] = []
        self.labels: list[dict] = []          # kind global|hier, name, point, angle, shape
        self.no_connects: list[tuple] = []
        self.pool = {p['ref']: p for p in members if not is_anchor(p) and not is_mechanical(p)}
        self.anchors = [p for p in members if is_anchor(p)]
        self.mech = [p for p in members if is_mechanical(p)]
        self.bbox = None
        self.exceptions: list[dict] = []
        self.extra_x = 10.16
        self.anchor_blocks: list = []

    # --- helpers ------------------------------------------------------------------------------------------------
    @property
    def nets(self):
        return self.planner.nets

    def role(self, net):
        return self.nets[net]['role'] if net else 'nc'

    def is_down(self, net):
        return self.nets[net]['down']

    def symbol(self, part):
        return self.planner.symbol(part)

    def place(self, part, unit, x, y, angle, texts=None, hide_reference=False, property_y=None) -> Placed:
        name, definition = self.symbol(part)[:2]
        placed = Placed(part['ref'], unit, part, name, definition, angle, r4(x), r4(y), texts=texts or {},
                        hide_reference=hide_reference, property_y=property_y)
        self.placed.append(placed)
        return placed

    def power(self, net, point, down=None, text_side: int = 0) -> Placed:
        """Power symbol at `point`; text_side -1/+1 writes the rail name beside the glyph (left/right), 0 above/below it."""
        down = self.is_down(net) if down is None else down
        name = self.planner.power_name(net)
        placed = Placed(self.planner.next_power_ref(), 1, dict(ref='#PWR', value=net, footprint='', kind='power', nets={}, pins={}),
                        name, self.planner.power_definition(net), 180 if down else 0, r4(point[0]), r4(point[1]), kind='power', net=net,
                        hide_reference=True)
        if text_side < 0:
            placed.texts = {'Value': (r4(point[0] - 1.905), r4(point[1]), 'right', 1.0)}
        elif text_side > 0:
            placed.texts = {'Value': (r4(point[0] + 1.905), r4(point[1]), 'left', 1.0)}
        else:
            placed.texts = {'Value': (r4(point[0]), r4(point[1] + (3.302 if down else -3.302)), None, 1.0)}
        self.placed.append(placed)
        return placed

    def wire(self, net, a, b):
        if a != b:
            self.segments.append(sw.Segment(net, a, b))

    def port(self, net, point, angle):
        shape = port_shape(net, self.page, self.nets[net])
        self.labels.append(dict(kind='hier', name=net, point=point, angle=angle, shape=shape))
        self.planner.ports_placed[(self.page, net)] = shape

    def tag(self, net, point, angle):
        self.labels.append(dict(kind='global', name=net, point=point, angle=angle, shape='bidirectional'))
        self.planner.tags_placed.add(net)

    def marker_kind(self, net) -> str:
        """What the end of a lane carrying `net` would receive: power / port / tag / open."""
        role = self.role(net)
        if role == 'rail':
            return 'power'
        if role == 'cross':
            return 'port' if (self.page, net) not in self.planner.ports_placed else 'open'
        return 'tag' if net not in self.planner.tags_placed else 'open'

    def end_marker(self, net, point, dx, angle=None):
        """Port / tag / power / open end for the final net of a lane at `point`; returns the marker kind.
        `angle` 90 / 270 writes the label vertically (text away from the wire end, above / below)."""
        role = self.role(net)
        angle = (0 if dx > 0 else 180) if angle is None else angle
        if role == 'rail':
            self.power(net, point)
            return 'power'
        if role == 'cross':
            if (self.page, net) not in self.planner.ports_placed:
                self.port(net, point, angle)
                return 'port'
            return 'open'
        if net not in self.planner.tags_placed:
            self.tag(net, point, angle)
            return 'tag'
        return 'open'

    # --- lane content ---------------------------------------------------------------------------------------------
    def satellites_on(self, net):
        return [p for p in self.members if p['ref'] in self.pool and net in p['nets'].values()]

    def classify_item(self, part, net):
        """(kind, far_net) of a pooled part seen from `net`: shunt / series / terminal / decoupling."""
        pads = [n for n in part['nets'].values() if n is not None]
        if len(part['pins']) == 1 or len(pads) == 1:
            return 'terminal', None
        if len(part['pins']) != 2:
            return 'multi', None
        far = next(n for pad, n in part['nets'].items() if n != net) if len(set(pads)) > 1 else None
        if far is None:
            return 'terminal', None
        if self.role(far) == 'rail':
            return 'shunt', far
        return 'series', far

    def collect_items(self, net, depth=0) -> list:
        """Ordered lane items for `net`: shunts, branches, then at most one inline series continuation."""
        if depth > 12:
            return []
        items = []
        shunts, series = [], []
        for part in self.satellites_on(net):
            kind, far = self.classify_item(part, net)
            if kind == 'multi':
                continue
            if kind == 'series':
                series.append((part, far))
            else:
                shunts.append((part, far, kind))
        for part, far, kind in shunts:
            self.pool.pop(part['ref'], None)
            items.append(dict(kind=kind, part=part, net=net, far=far))
        if series:
            # continue inline with the series part whose far net has the most unplaced content
            def weight(entry):
                part, far = entry
                leaves = 0 if self.role(far) in ('rail', 'cross') else 1
                return (leaves, -len([p for p in self.satellites_on(far) if p is not part]))
            series.sort(key=weight)
            inline, branches = series[0], series[1:]
            for part, far in branches:
                self.pool.pop(part['ref'], None)
                items.append(dict(kind='branch', part=part, net=net, far=far))
            part, far = inline
            self.pool.pop(part['ref'], None)
            items.append(dict(kind='series', part=part, net=net, far=far))
            items.extend(self.collect_items(far, depth + 1))
        return items

    def item_extents(self, item) -> tuple:
        """(above, below, width) of one lane item."""
        part = item['part']
        name, definition, extents, _ = self.symbol(part)
        if item['kind'] in ('shunt', 'branch'):
            span = two_pin_span(definition)
            tail = 5.08
            if item['kind'] == 'branch' and self.role(item['far']) != 'rail':
                tail = max(tail, TEXT_W * self.planner.presentation.get('label_size', 1.27) * len(item['far']) + 3.0)
            tall = STUB + span + STUB + tail
            if item['kind'] == 'shunt' and not self.is_down(item['far']):
                return tall, GAP, PITCH
            return GAP, tall, PITCH
        if item['kind'] == 'series':
            return 5.08, 5.08, two_pin_span(definition) + 2 * STUB
        if item['kind'] == 'terminal':
            w, h = extents[0]
            return GAP, STUB + w + 5.08 + 2.54, PITCH
        return GAP, GAP, PITCH

    # --- anchor lanes ----------------------------------------------------------------------------------------------
    def anchor_lanes(self, anchor: Placed) -> dict:
        info = anchor.pins()
        lanes = {'left': [], 'right': [], 'up': [], 'down': []}
        side_of = {(-1, 0): 'left', (1, 0): 'right', (0, -1): 'up', (0, 1): 'down'}
        ordered = sorted(info.items(), key=lambda kv: (side_of[tuple(kv[1]['outward'])], kv[1]['point'][1], kv[1]['point'][0]))
        for side in ('left', 'right'):
            pins_here = [(pad, i) for pad, i in ordered if side_of[tuple(i['outward'])] == side]
            dx = -1 if side == 'left' else 1
            index = 0
            while index < len(pins_here):
                pad, pin_info = pins_here[index]
                net = anchor.part['nets'][pad]
                if net is None:
                    lanes[side].append(Lane(pad, None, 'nc', pin_info['point'], dx, above=0, below=0))
                    index += 1
                    continue
                if self.role(net) == 'rail':
                    run = [pad]
                    j = index + 1
                    while j < len(pins_here) and anchor.part['nets'][pins_here[j][0]] == net and \
                            abs(pins_here[j][1]['point'][1] - pins_here[j - 1][1]['point'][1] - STUB) < 1e-3:
                        run.append(pins_here[j][0])
                        j += 1
                    if len(run) > 1:
                        lane = Lane(pad, net, 'bundle', pin_info['point'], dx, bundle_pins=[(p, info[p]['point']) for p in run])
                        down = self.is_down(net)
                        lane.above, lane.below = (0.0, 3.81) if down else (3.81, 0.0)
                        lanes[side].append(lane)
                        index = j
                        continue
                    lane = Lane(pad, net, 'power', pin_info['point'], dx)
                    lane.above, lane.below = (0.0, 3.81) if self.is_down(net) else (3.81, 0.0)
                    lanes[side].append(lane)
                    index += 1
                    continue
                lane = Lane(pad, net, 'signal', pin_info['point'], dx)
                lane.items = self.collect_items(net)
                above, below, length = GAP, GAP, 0.0
                for item in lane.items:
                    a, b, w = self.item_extents(item)
                    above, below, length = max(above, a), max(below, b), length + w
                final = lane.items[-1]['far'] if lane.items and lane.items[-1]['kind'] == 'series' else net
                lane.end = ('marker', final)
                if self.role(final) == 'rail':
                    above = max(above, 5.08) if not self.is_down(final) else above
                    below = max(below, 5.08) if self.is_down(final) else below
                lane.above, lane.below, lane.length = above, below, length + 2 * STUB + 5.08
                lanes[side].append(lane)
                index += 1
        for side in ('up', 'down'):
            dy = -1 if side == 'up' else 1
            for pad, pin_info in ordered:
                if side_of[tuple(pin_info['outward'])] != side:
                    continue
                net = anchor.part['nets'][pad]
                lane = Lane(pad, net, 'nc' if net is None else 'vertical', pin_info['point'], dy)
                lanes[side].append(lane)
        return lanes

    def pack_side(self, lanes: list) -> None:
        """Vertical packing of one side's lanes: monotonic, each lane at or below its pin."""
        bottom = -1e9
        for lane in lanes:
            pin_y = lane.pin_point[1]
            if lane.kind == 'nc':
                lane.y = pin_y
                continue
            if lane.kind == 'bundle':
                lane.y = pin_y
                ys = [p[1] for _, p in lane.bundle_pins]
                # the symbol sits at the outer end of the bus unless the lane above reaches into that glyph
                lane.flip = (not self.is_down(lane.net)) and (min(ys) - lane.above < bottom - 1e-6)
                bottom = max(bottom, max(ys) + (lane.below if not lane.flip else 2.54))
                continue
            if lane.kind == 'power' and pin_y - lane.above >= bottom - 1e-6:
                lane.y, lane.needs_jog = pin_y, False     # fixed: stub plus symbol right at the pin row
                bottom = pin_y + lane.below
                continue
            y = max(pin_y, snap_up(bottom + lane.above + GAP))
            lane.y = y
            lane.needs_jog = y > pin_y + 1e-6
            bottom = y + lane.below
        jog_lanes = [lane for lane in lanes if lane.needs_jog]
        for i, lane in enumerate(jog_lanes):
            lane.rank = len(jog_lanes) - 1 - i          # the top lane jogs farthest out
        n = len(jog_lanes)
        for lane in lanes:
            lane.items_start = JOG0 + GRID * n + STUB

    def draw_lane(self, lane: Lane) -> tuple:
        """Emit the geometry of one lane; returns the far x reached."""
        px, py = lane.pin_point
        dx = lane.dx
        if lane.kind == 'nc':
            self.no_connects.append((px, py))
            return px
        if lane.kind == 'bundle':
            bus_x = r4(px + dx * STUB)
            ys = [p[1] for _, p in lane.bundle_pins]
            for _, p in lane.bundle_pins:
                self.wire(lane.net, p, (bus_x, p[1]))
            down = self.is_down(lane.net)
            self.wire(lane.net, (bus_x, min(ys)), (bus_x, max(ys)))
            at_bottom = down or getattr(lane, 'flip', False)
            self.power(lane.net, (bus_x, max(ys) if at_bottom else min(ys)), down=down)
            return bus_x
        if lane.kind == 'vertical':
            dy = lane.dx
            end = (px, r4(py + dy * STUB))
            kind = self.marker_kind(lane.net)
            if kind == 'open':
                return px
            self.wire(lane.net, (px, py), end)
            if kind == 'power':
                self.power(lane.net, end, down=(dy > 0))
            elif kind == 'port':
                self.port(lane.net, end, 270 if dy < 0 else 90)
            else:
                self.tag(lane.net, end, 270 if dy < 0 else 90)
            return px
        # power or signal lane: optional jog to lane.y
        y = lane.y
        if lane.needs_jog:
            xj = r4(px + dx * (JOG0 + GRID * lane.rank))
            self.wire(lane.net, (px, py), (xj, py))
            self.wire(lane.net, (xj, py), (xj, y))
            cursor = xj
        else:
            cursor = px
        if lane.kind == 'power':
            end_x = r4(cursor + dx * (STUB if not lane.needs_jog else GRID))
            self.wire(lane.net, (cursor, y), (end_x, y))
            self.power(lane.net, (end_x, y))
            return end_x
        # signal lane with items
        start_items = r4(px + dx * lane.items_start)
        net = lane.net
        if lane.items:
            x = start_items
            for item in lane.items:
                part = item['part']
                name, definition, extents, _ = self.symbol(part)
                near_pad = next(pad for pad, n in part['nets'].items() if n == item['net'])
                far_pad = next((pad for pad, n in part['nets'].items() if pad != near_pad), None)
                if item['kind'] in ('shunt', 'branch', 'terminal'):
                    x_item = r4(x + dx * PITCH / 2)
                    hang_down = not (item['kind'] == 'shunt' and not self.is_down(item['far']))
                    s = 1 if hang_down else -1
                    self.wire(item['net'], (cursor, y), (x_item, y))
                    cursor = x_item
                    near_point = (x_item, r4(y + s * STUB))
                    self.wire(item['net'], (x_item, y), near_point)
                    angle = angle_for(definition, 1, near_pad, (0, -s))
                    probe = placed_pins(definition, 1, 0, 0, angle)
                    ox, oy = probe[near_pad]['point']
                    placed = self.place(part, 1, near_point[0] - ox, near_point[1] - oy, angle)
                    self.side_texts(placed)
                    if item['kind'] == 'terminal':
                        self.terminal_rails(placed, near_pad)
                    else:
                        far_point = placed.pins()[far_pad]['point']
                        rail_point = (far_point[0], r4(far_point[1] + s * STUB))
                        if item['kind'] == 'shunt':
                            self.wire(item['far'], far_point, rail_point)
                            self.power(item['far'], rail_point, down=hang_down)
                        elif self.marker_kind(item['far']) != 'open':
                            self.wire(item['far'], far_point, rail_point)
                            self.end_marker(item['far'], rail_point, dx, angle=270 if hang_down else 90)
                    x = r4(x + dx * PITCH)
                else:  # series: inline part, the lane continues with the far net
                    near_point = (r4(x + dx * STUB), y)
                    self.wire(item['net'], (cursor, y), near_point)
                    self.spine_tag(item['net'], cursor, near_point, y, dx)
                    angle = angle_for(definition, 1, near_pad, (-dx, 0))
                    probe = placed_pins(definition, 1, 0, 0, angle)
                    ox, oy = probe[near_pad]['point']
                    placed = self.place(part, 1, near_point[0] - ox, near_point[1] - oy, angle)
                    self.inline_texts(placed)
                    far_point = placed.pins()[far_pad]['point']
                    cursor = far_point[0]
                    x = cursor
                    net = item['far']
            end_x = r4(cursor + dx * STUB)
        else:
            end_x = r4(cursor + dx * (STUB if not lane.needs_jog else GRID))
        if self.marker_kind(net) == 'open':
            return cursor
        self.wire(net, (cursor, y), (end_x, y))
        self.end_marker(net, (end_x, y), dx)
        return end_x

    def spine_tag(self, net, cursor, near_point, y, dx) -> None:
        """Name tag (local net) or port (cross net) of a net that continues through a series part: vertical label above the spine."""
        kind = self.marker_kind(net)
        if kind not in ('tag', 'port'):
            return
        mid = r4(cursor + dx * GRID) if abs(near_point[0] - cursor) >= 2 * GRID - 1e-6 else cursor
        if mid == cursor:
            mid = r4(cursor + dx * GRID)
            self.wire(net, (cursor, y), (mid, y))
        top = (mid, r4(y - STUB))
        self.wire(net, (mid, y), top)
        if kind == 'tag':
            self.tag(net, top, 90)
        else:
            self.port(net, top, 90)

    def terminal_rails(self, placed: Placed, near_pad: str) -> None:
        """Stub plus power symbol on every other rail pin of a part drawn as a terminal (the router skips rails)."""
        for pad, info in placed.pins().items():
            net = placed.part['nets'].get(pad)
            if pad == near_pad or net is None or self.role(net) != 'rail':
                continue
            ox, oy = info['outward']
            end = (r4(info['point'][0] + ox * STUB), r4(info['point'][1] + oy * STUB))
            self.wire(net, info['point'], end)
            self.power(net, end, down=(oy > 0) if oy else None)

    def side_texts(self, placed: Placed) -> None:
        """Reference above value, both right of a vertical two-pin part (reference-style rule F2)."""
        x = r4(placed.x + 2.54 + 0.762)
        placed.texts = {'Reference': (x, r4(placed.y - 1.27), 'left'), 'Value': (x, r4(placed.y + 1.27), 'left')}

    def inline_texts(self, placed: Placed) -> None:
        placed.texts = {'Reference': (placed.x, r4(placed.y - 3.175), None), 'Value': (placed.x, r4(placed.y + 3.175), None)}

    # --- group assembly ---------------------------------------------------------------------------------------------
    def layout(self) -> None:
        x_cursor = 0.0
        max_bottom = 0.0
        row_top, row_width = 0.0, 0.0
        self.anchor_blocks = []
        max_row = self.planner.presentation.get('max_row_mm', 250.0)
        for anchor_part in self.sorted_anchors():
            name, definition, extents, _ = self.symbol(anchor_part)
            for unit, (w, h) in enumerate(extents, 1):
                probe = Placed(anchor_part['ref'], unit, anchor_part, name, definition, 0, 0.0, 0.0)
                lanes = self.anchor_lanes(probe)
                for side in ('left', 'right'):
                    self.pack_side(lanes[side])
                left_len = max([l.length + l.items_start for l in lanes['left'] if l.kind == 'signal'] +
                               [JOG0 + GRID * 8 + 5.08 for l in lanes['left'] if l.kind == 'power'] + [7.62])
                right_len = max([l.length + l.items_start for l in lanes['right'] if l.kind == 'signal'] +
                                [JOG0 + GRID * 8 + 5.08 for l in lanes['right'] if l.kind == 'power'] + [7.62])
                top_room = max([l.above for l in lanes['left'][:1] + lanes['right'][:1]] + [10.16]) + (7.62 if lanes['up'] else 0)
                body = probe.body()
                pin_pts = [i['point'] for i in probe.pins().values()]
                x_min = min([body[0]] + [p[0] for p in pin_pts])
                y_min = min([body[1]] + [p[1] for p in pin_pts])
                block_width = left_len + (body[2] - x_min) + right_len
                if x_cursor > 0 and x_cursor + block_width > max_row:
                    row_top, x_cursor = snap_up(max_bottom + 12.7), 0.0      # new anchor row below the previous one
                ox = snap(x_cursor + left_len - x_min)
                oy = snap(row_top + top_room - y_min + 7.62)
                anchor = self.place(anchor_part, unit, ox, oy, 0, property_y=-h / 2 - 6.35)
                for side in ('left', 'right', 'up', 'down'):
                    for lane in lanes[side]:
                        lane.pin_point = (r4(lane.pin_point[0] + ox), r4(lane.pin_point[1] + oy))
                        lane.bundle_pins = [(pad, (r4(pt[0] + ox), r4(pt[1] + oy))) for pad, pt in lane.bundle_pins]
                        lane.y = r4(lane.y + oy)
                xs = []
                for side in ('left', 'right', 'up', 'down'):
                    for lane in lanes[side]:
                        xs.append(self.draw_lane(lane))
                for side in ('left', 'right'):
                    for lane in lanes[side]:
                        max_bottom = max(max_bottom, lane.y + lane.below if lane.kind in ('signal', 'power') else
                                         (max(p[1] for _, p in lane.bundle_pins) + lane.below if lane.kind == 'bundle' else lane.pin_point[1]))
                body = anchor.body()
                max_bottom = max(max_bottom, body[3] + 7.62 + (7.62 if lanes['down'] else 0))
                x_cursor = snap(max([body[2]] + xs) + 15.24)
                row_width = max(row_width, x_cursor)
                self.anchor_blocks.append(anchor)
        anchors_w, anchors_h = row_width, max_bottom
        max_col = self.planner.presentation.get('max_col_mm', 180.0)
        pairs = {self.classify_decoupling(part) for part in self.pool.values()} - {None}
        free = [r for r, part in self.pool.items() if not self.classify_decoupling(part)]
        extras_estimate = 7.62 + 13.0 * len(free) + 26.0 * len(pairs) + (20.0 if self.mech else 0.0)
        if self.anchor_blocks and (anchors_h > 110.0 or (anchors_h >= 50.0 and anchors_h + extras_estimate > max_col)):
            self.extra_x, y_cursor = snap_up(anchors_w + 7.62), 12.7     # tall anchor block: extras in a column beside it
        else:
            self.extra_x, y_cursor = 10.16, snap_up(max_bottom + 7.62)
        y_cursor = self.free_lanes(y_cursor)
        y_cursor = self.decoupling_rows(y_cursor)
        y_cursor = self.mechanical_grid(y_cursor)
        self.finish()

    def sorted_anchors(self) -> list:
        """Anchors in signal-flow order: a driving pin of A on a net with an input pin of B puts A before B."""
        anchors = list(self.anchors)
        order = {p['ref']: i for i, p in enumerate(anchors)}
        edges = defaultdict(set)
        for a in anchors:
            for pad, net in a['nets'].items():
                if net is None or self.role(net) == 'rail' or a['pins'][pad]['type'] not in DRIVING:
                    continue
                for b in anchors:
                    if b is a:
                        continue
                    if any(n == net and b['pins'][p]['type'] in ('input', 'passive', 'bidirectional') for p, n in b['nets'].items()):
                        edges[a['ref']].add(b['ref'])
        indegree = {p['ref']: 0 for p in anchors}
        for src, dsts in edges.items():
            for d in dsts:
                indegree[d] += 1
        ready = sorted([r for r, n in indegree.items() if n == 0], key=order.get)
        result = []
        seen = set()
        while ready:
            ref = ready.pop(0)
            if ref in seen:
                continue
            seen.add(ref)
            result.append(ref)
            for d in sorted(edges.get(ref, ()), key=order.get):
                indegree[d] -= 1
                if indegree[d] <= 0 and d not in seen:
                    ready.append(d)
            ready.sort(key=order.get)
        for p in anchors:
            if p['ref'] not in seen:
                result.append(p['ref'])
        by_ref = {p['ref']: p for p in anchors}
        return [by_ref[r] for r in result]

    def content_right(self) -> float:
        """Right edge of everything drawn so far in the group frame."""
        xs = [p.body()[2] for p in self.placed] + [max(s.a[0], s.b[0]) for s in self.segments]
        for l in self.labels:
            x = l['point'][0]
            xs.append(x + (TEXT_W * self.planner.presentation.get('label_size', 1.27) * len(l['name']) + 3.0 if l.get('angle', 0) == 0 else 0))
        for p in self.placed:
            for v in p.texts.values():
                if v:
                    xs.append(text_box(v[0], v[1], p.ref if 'Ref' in str(v) else str(p.net or p.part['value']), 1.27, v[2])[2])
        return max(xs, default=0.0)

    def free_lanes(self, y_cursor: float) -> float:
        """Chains of pooled parts no anchor lane reached: one horizontal lane per connected component; the lanes wrap
        into a new column (right of everything drawn so far) when a column would grow beyond max_col_mm."""
        col_top, col_x, max_col = y_cursor, self.extra_x, self.planner.presentation.get('max_col_mm', 180.0)
        bottom_seen = y_cursor
        while True:
            decoupling = [r for r, p in self.pool.items() if self.classify_decoupling(p)]
            candidates = [r for r in self.pool if r not in decoupling]
            if not candidates:
                return max(y_cursor, bottom_seen)
            start_ref = candidates[0]
            part = self.pool[start_ref]
            # choose the starting net: a cross net first, then a rail, then a local net
            nets_of = [n for n in part['nets'].values() if n is not None]
            start_net = sorted(nets_of, key=lambda n: ({'cross': 0, 'rail': 1, 'local': 2}[self.role(n)], n))[0]
            lane = Lane('', start_net, 'free', (0.0, 0.0), 1)
            lane.items = self.collect_items(start_net)
            if not lane.items and start_ref in self.pool:
                # a lone part (e.g. test point on a rail): place it as a terminal
                self.pool.pop(start_ref)
                lane.items = [dict(kind='terminal', part=part, net=start_net, far=None)]
            above, below, length = 5.08, GAP, 0.0
            for item in lane.items:
                a, b, w = self.item_extents(item)
                above, below, length = max(above, a), max(below, b), length + w
            if y_cursor > col_top + 1e-6 and y_cursor + above + below > max(col_top + 40.0, max_col):
                bottom_seen = max(bottom_seen, y_cursor)
                col_x, y_cursor = snap_up(self.content_right() + 12.7), col_top        # new column beside the previous one
            lane.y = snap_up(y_cursor + above)
            x0 = col_x
            # start marker
            if self.role(start_net) == 'rail':
                self.power(start_net, (x0, lane.y))
                cursor = x0
            elif self.role(start_net) == 'cross' and (self.page, start_net) not in self.planner.ports_placed:
                self.port(start_net, (x0, lane.y), 180)
                cursor = x0
            elif self.role(start_net) == 'local' and start_net not in self.planner.tags_placed:
                self.tag(start_net, (x0, lane.y), 180)
                cursor = x0
            else:
                cursor = x0
            x = r4(x0 + STUB)
            net = start_net
            for item in lane.items:
                part = item['part']
                name, definition, extents, _ = self.symbol(part)
                near_pad = next(pad for pad, n in part['nets'].items() if n == item['net'])
                far_pad = next((pad for pad, n in part['nets'].items() if pad != near_pad), None)
                if item['kind'] in ('shunt', 'branch', 'terminal'):
                    x_item = r4(x + PITCH / 2)
                    hang_down = not (item['kind'] == 'shunt' and not self.is_down(item['far']))
                    s = 1 if hang_down else -1
                    self.wire(item['net'], (cursor, lane.y), (x_item, lane.y))
                    cursor = x_item
                    near_point = (x_item, r4(lane.y + s * STUB))
                    self.wire(item['net'], (x_item, lane.y), near_point)
                    angle = angle_for(definition, 1, near_pad, (0, -s))
                    ox, oy = placed_pins(definition, 1, 0, 0, angle)[near_pad]['point']
                    placed = self.place(part, 1, near_point[0] - ox, near_point[1] - oy, angle)
                    self.side_texts(placed)
                    if item['kind'] == 'terminal':
                        self.terminal_rails(placed, near_pad)
                    else:
                        far_point = placed.pins()[far_pad]['point']
                        rail_point = (far_point[0], r4(far_point[1] + s * STUB))
                        if item['kind'] == 'shunt':
                            self.wire(item['far'], far_point, rail_point)
                            self.power(item['far'], rail_point, down=hang_down)
                        elif self.marker_kind(item['far']) != 'open':
                            self.wire(item['far'], far_point, rail_point)
                            self.end_marker(item['far'], rail_point, 1, angle=270 if hang_down else 90)
                    x = r4(x + PITCH)
                else:
                    near_point = (r4(x + STUB), lane.y)
                    self.wire(item['net'], (cursor, lane.y), near_point)
                    self.spine_tag(item['net'], cursor, near_point, lane.y, 1)
                    angle = angle_for(definition, 1, near_pad, (-1, 0))
                    ox, oy = placed_pins(definition, 1, 0, 0, angle)[near_pad]['point']
                    placed = self.place(part, 1, near_point[0] - ox, near_point[1] - oy, angle)
                    self.inline_texts(placed)
                    far_point = placed.pins()[far_pad]['point']
                    cursor = far_point[0]
                    x = cursor
                    net = item['far']
            if self.marker_kind(net) != 'open':
                end_x = r4(cursor + STUB)
                self.wire(net, (cursor, lane.y), (end_x, lane.y))
                self.end_marker(net, (end_x, lane.y), 1)
            y_cursor = snap_up(lane.y + below + GAP)
            bottom_seen = max(bottom_seen, y_cursor)

    def classify_decoupling(self, part) -> tuple | None:
        """(up rail, down rail) when a two-pin part sits between two rails."""
        nets_ = [n for n in part['nets'].values() if n is not None]
        if len(part['pins']) != 2 or len(set(nets_)) != 2 or not all(self.role(n) == 'rail' for n in nets_):
            return None
        a, b = sorted(set(nets_), key=lambda n: (rail_rank(n), n))
        return (a, b)

    def decoupling_rows(self, y_cursor: float) -> float:
        rows = defaultdict(list)
        for ref in list(self.pool):
            pair = self.classify_decoupling(self.pool[ref])
            if pair:
                rows[pair].append(self.pool.pop(ref))
        for (up, down), parts in sorted(rows.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            y_top = snap_up(y_cursor + 5.08 + 1.27)
            x0 = self.extra_x
            last_x = x0
            spans = []
            for i, part in enumerate(parts):
                name, definition, extents, _ = self.symbol(part)
                up_pad = next(pad for pad, n in part['nets'].items() if n == up)
                angle = angle_for(definition, 1, up_pad, (0, -1))
                ox, oy = placed_pins(definition, 1, 0, 0, angle)[up_pad]['point']
                x_item = r4(x0 + STUB + i * CAP_PITCH)
                placed = self.place(part, 1, x_item - ox, (y_top + STUB) - oy, angle)
                self.side_texts(placed)
                info = placed.pins()
                down_pad = next(pad for pad, n in part['nets'].items() if n == down)
                spans.append(info[down_pad]['point'][1])
                self.wire(up, (x_item, y_top), info[up_pad]['point'])
                last_x = x_item
            y_bottom = r4(max(spans) + STUB)
            for i, part in enumerate(parts):
                placed = next(p for p in self.placed if p.ref == part['ref'])
                info = placed.pins()
                down_pad = next(pad for pad, n in part['nets'].items() if n == down)
                self.wire(down, info[down_pad]['point'], (info[down_pad]['point'][0], y_bottom))
            self.wire(up, (x0, y_top), (last_x, y_top))
            self.wire(down, (x0, y_bottom), (last_x, y_bottom))
            self.power(up, (x0, y_top), down=False)
            self.power(down, (x0, y_bottom), down=True)
            y_cursor = snap_up(y_bottom + 5.08 + 2.54)
        return y_cursor

    def mechanical_grid(self, y_cursor: float) -> float:
        if not self.mech:
            return y_cursor
        x, y = self.extra_x, snap_up(y_cursor + 10.16)
        row_h = 0.0
        for part in self.mech:
            name, definition, extents, _ = self.symbol(part)
            w, h = extents[0]
            if x + w > self.extra_x + 170 and x > self.extra_x:
                x, y = self.extra_x, snap_up(y + row_h + 10.16)
                row_h = 0.0
            placed = self.place(part, 1, snap(x + w / 2 + 5.08), snap(y + h / 2), 0, property_y=-h / 2 - 6.35)
            for pad, info in placed.pins().items():
                if part['nets'][pad] is None:
                    self.no_connects.append(info['point'])
                elif self.marker_kind(part['nets'][pad]) != 'open':  # a pad on a net (e.g. the PE stud): stub and marker
                    end = (info['point'][0], r4(info['point'][1] - STUB))
                    self.wire(part['nets'][pad], info['point'], end)
                    self.end_marker(part['nets'][pad], end, 1)
            x = snap(x + w + 12.7)
            row_h = max(row_h, h + 7.62)
        return snap_up(y + row_h)

    def finish(self) -> None:
        """Normalise the frame so the group's bounding box starts at (0, 0); every placed pin whose model net is None
        receives a no_connect marker (lane, free-lane and mechanical placements alike)."""
        marked = {(r4(q[0]), r4(q[1])) for q in self.no_connects}
        for p in self.placed:
            if p.kind != 'part':
                continue
            for pad, info in p.pins().items():
                point = (r4(info['point'][0]), r4(info['point'][1]))
                if p.part['nets'].get(pad) is None and point not in marked:
                    self.no_connects.append(point)
                    marked.add(point)
        label_size = self.planner.presentation.get('label_size', 1.27)
        xs, ys = [], []
        for p in self.placed:
            b = p.body()
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
            if p.kind == 'part' and p.property_y is not None:       # reference / value fields above the body
                for dy, text in ((p.property_y, p.ref), (p.property_y + 2.54, p.part['value'])):
                    tb = text_box(p.x, p.y + dy, text, 1.27, None)
                    xs += [tb[0], tb[2]]
                    ys += [tb[1], tb[3]]
            for v in p.texts.values():
                if v:
                    tb = text_box(v[0], v[1], p.ref if 'Ref' in str(v) else p.part['value'], 1.27, v[2])
                    xs += [tb[0], tb[2]]
                    ys += [tb[1], tb[3]]
        for s in self.segments:
            xs += [s.a[0], s.b[0]]
            ys += [s.a[1], s.b[1]]
        for l in self.labels:
            width = TEXT_W * label_size * len(l['name']) + 3.0
            angle = l.get('angle', 0)
            x, y = l['point']
            if angle == 180:
                xs += [x - width, x]
            elif angle == 0:
                xs += [x, x + width]
            else:
                ys += [y - width, y + width]
            ys += [y - 1.5, y + 1.5]
            xs += [x]
        for p in self.no_connects:
            xs.append(p[0])
            ys.append(p[1])
        if not xs:
            self.bbox = (0.0, 0.0, 10.0, 10.0)
            return
        dx, dy = snap(-min(xs) + 2.54), snap(-min(ys) + 2.54)
        self.shift(dx, dy)
        self.bbox = (0.0, 0.0, snap_up(max(xs) + dx + 2.54), snap_up(max(ys) + dy + 2.54))

    def shift(self, dx, dy) -> None:
        for p in self.placed:
            p.shift(dx, dy)
        self.segments = [sw.Segment(s.net, (s.a[0] + dx, s.a[1] + dy), (s.b[0] + dx, s.b[1] + dy)) for s in self.segments]
        for l in self.labels:
            l['point'] = (r4(l['point'][0] + dx), r4(l['point'][1] + dy))
        self.no_connects = [(r4(p[0] + dx), r4(p[1] + dy)) for p in self.no_connects]
        if self.bbox:
            self.bbox = (r4(self.bbox[0] + dx), r4(self.bbox[1] + dy), r4(self.bbox[2] + dx), r4(self.bbox[3] + dy))


# --- planner -----------------------------------------------------------------------------------------------------------

class Planner:
    """Builds the drawing plan of every page; project_schematic emits it."""

    def __init__(self, spec, parts: list, presentation: dict, symbol_for):
        self.spec, self.parts, self.presentation = spec, parts, presentation
        self._symbol_for = symbol_for
        self._symbols: dict = {}
        self.nets = classify_nets(parts, spec.flag_nets, presentation)
        self.ports_placed: dict = {}
        self.tags_placed: set = set()
        self.power_counter = 0
        self.power_definitions: dict = {}
        self.sheets: dict = {}
        self.exceptions: list = []
        self.groups_by_page: dict = {}

    def symbol(self, part):
        if part['ref'] not in self._symbols:
            self._symbols[part['ref']] = self._symbol_for(part)
        return self._symbols[part['ref']]

    def power_name(self, net):
        return 'PWR_' + re.sub(r'[^A-Za-z0-9_+\-]', '_', net)

    def power_definition(self, net):
        name = self.power_name(net)
        if name not in self.power_definitions:
            self.power_definitions[name] = power_symbol_definition(name, net, down=self.nets[net]['down'])
        return self.power_definitions[name]

    def next_flag_index(self) -> int:
        self.flag_counter = getattr(self, 'flag_counter', 0) + 1
        return self.flag_counter

    def next_power_ref(self):
        self.power_counter += 1
        return f'#PWR{self.power_counter:03d}'

    def groups_for(self, page: str, page_parts: list) -> list:
        """[(group id, title, members)] in drawing order."""
        explicit = {p['ref']: self.presentation['groups'].get(p['ref']) or p.get('group') for p in page_parts}
        auto = auto_groups(page_parts, self.nets)
        ids = {}
        for p in page_parts:
            gid = explicit[p['ref']] or auto[p['ref']]
            ids[p['ref']] = gid if '/' in gid else f'{page}/{gid}'
        members = defaultdict(list)
        for p in page_parts:
            members[ids[p['ref']]].append(p)
        order = list(dict.fromkeys(ids[p['ref']] for p in page_parts))
        wanted = self.presentation['group_order'].get(page)
        if wanted:
            wanted = [g if '/' in g else f'{page}/{g}' for g in wanted]
            order = [g for g in wanted if g in members] + [g for g in order if g not in wanted]
        return [(gid, group_title(gid, self.presentation['group_titles'], members[gid]), members[gid]) for gid in order]

    def flags_for_page(self, page: str, flag_nets: list, is_flag_page: bool) -> list:
        """PWR_FLAG nets drawn on this page: a flag must share a sheet with real pins of its net (KiCad reports a
        power symbol whose only sheet-local partner is the flag as pin_not_connected), so every flag net goes to the
        spec's flag page when the net has pins there, otherwise to the first page (in order) where it has pins."""
        chosen = []
        for net in flag_nets:
            pages = self.nets.get(net, {}).get('pages') or []
            target = self.spec.flag_page if (self.spec.flag_page in pages or not pages) else pages[0]
            if target == page:
                chosen.append(net)
        return chosen

    def plan_page(self, page: str, page_parts: list, flag_nets: list, is_flag_page: bool) -> dict:
        layouts = []
        for gid, title, members in self.groups_for(page, page_parts):
            layout = GroupLayout(self, page, gid, members)
            layout.layout()
            layout.title = title
            layouts.append(layout)
        page_flags = self.flags_for_page(page, flag_nets, is_flag_page)
        if page_flags:
            layouts.append(self.flag_block(page, page_flags))
        self.groups_by_page[page] = [dict(id=l.group_id, title=getattr(l, 'title', l.group_id), parts=[p.ref for p in l.placed if p.kind == 'part'])
                                     for l in layouts]
        return dict(page=page, layouts=layouts)

    def flag_block(self, page: str, flag_nets: list) -> GroupLayout:
        layout = GroupLayout(self, page, f'{page}/supply_flags', [])
        layout.title = 'Supply provenance (PWR_FLAG)'
        x, y = 5.08, 7.62
        for net in flag_nets:
            index = self.next_flag_index()
            if x > 320:
                x, y = 5.08, snap(y + 17.78)
            point = (snap(x), y)
            layout.power(net, point)
            flag_point = (r4(point[0] + 5.08), y)
            layout.wire(net, point, flag_point)
            flag = Placed(f'#FLG{index}', 1, dict(ref=f'#FLG{index}', value='PWR_FLAG', footprint='', kind='flag', nets={}, pins={}),
                          'PWR_FLAG', self.flag_definition, 0, flag_point[0], flag_point[1], kind='flag', net=net, hide_reference=True,
                          hide_value=True)
            layout.placed.append(flag)
            x = snap(x + max(20.32, TEXT_W * len(net) + 12.7))
        layout.finish()
        return layout

    @property
    def flag_definition(self):
        from automation.kicad_tools.project_schematic import FLAG_DEFINITION
        return FLAG_DEFINITION


# --- sheet assembly ------------------------------------------------------------------------------------------------------

@dataclass
class SheetPlan:
    key: str
    page: str
    title: str
    paper: str
    placed: list
    wiring: sw.SheetWiring
    labels: list
    texts: list
    rectangles: list
    ports: dict               # net -> shape
    counts: dict = field(default_factory=dict)


def paper_area(paper: str, PAPER: dict) -> tuple:
    width, height = PAPER[paper]
    return 6.35, 33.02, width - 12.7, height - 30.0


def _pack_columns(layouts: list, left: float, top: float, right: float, bottom: float, ffd: bool) -> list | None:
    """Column packing (top to bottom, then the next column) in drawing order or first-fit-decreasing by height."""
    heading = 5.08
    if not ffd:
        x, y, col_w = left, top, 0.0
        positions = []
        for layout in layouts:
            w, h = layout.bbox[2], layout.bbox[3]
            if y > top and y + h + heading > bottom:
                x, y, col_w = snap(x + col_w + 12.7), top, 0.0
            if x + w > right or h + heading > bottom - top:
                return None
            positions.append((layout, snap(x), snap(y + heading)))
            y = snap_up(y + h + heading + 7.62)
            col_w = max(col_w, w)
        return positions
    columns = []           # [x, width, next_y, [(layout, x, y)]]
    order = sorted(layouts, key=lambda l: (-l.bbox[3], layouts.index(l)))
    for layout in order:
        w, h = layout.bbox[2], layout.bbox[3]
        if h + heading > bottom - top:
            return None
        placed = False
        for col in columns:
            if col[2] + h + heading <= bottom and col[0] + max(col[1], w) <= right:
                col[3].append((layout, snap(col[0]), snap(col[2] + heading)))
                col[2] = snap_up(col[2] + h + heading + 7.62)
                col[1] = max(col[1], w)
                placed = True
                break
        if not placed:
            x = snap(columns[-1][0] + columns[-1][1] + 12.7) if columns else left
            if x + w > right:
                return None
            columns.append([x, w, snap_up(top + h + heading + 7.62), [(layout, snap(x), snap(top + heading))]])
    positions = [entry for col in columns for entry in col[3]]
    positions.sort(key=lambda e: layouts.index(e[0]))
    return positions


def _pack_bottom_left(layouts: list, left: float, top: float, right: float, bottom: float, by_height: bool) -> list | None:
    """Bottom-left 2D packing: each group goes to the top-most, then left-most free corner where it fits."""
    heading = 5.08
    order = sorted(layouts, key=lambda l: (-l.bbox[3], layouts.index(l))) if by_height else list(layouts)
    rects = []           # (x0, y0, x1, y1) including the heading strip and gaps
    positions = []
    for layout in order:
        w, h = layout.bbox[2] + 12.7, layout.bbox[3] + heading + 7.62
        candidates = {(left, top)}
        for (x0, y0, x1, y1) in rects:
            candidates.add((x1, y0))
            candidates.add((x0, y1))
        best = None
        for (cx, cy) in sorted(candidates, key=lambda c: (c[1], c[0])):
            if cx + w - 12.7 > right or cy + h - 7.62 > bottom:
                continue
            if any(cx < x1 - 1e-6 and x0 < cx + w - 1e-6 and cy < y1 - 1e-6 and y0 < cy + h - 1e-6 for (x0, y0, x1, y1) in rects):
                continue
            best = (cx, cy)
            break
        if best is None:
            return None
        rects.append((best[0], best[1], best[0] + w, best[1] + h))
        positions.append((layout, snap(best[0]), snap(best[1] + heading)))
    positions.sort(key=lambda e: layouts.index(e[0]))
    return positions


def paper_fill(layouts: list, paper: str, PAPER: dict, header_height: float = 0.0) -> float:
    """Sum of the group bounding boxes over the drawable area of the paper."""
    left, top, right, bottom = paper_area(paper, PAPER)
    area = (right - left) * (bottom - top - header_height)
    return round(sum((l.bbox[2] - l.bbox[0]) * (l.bbox[3] - l.bbox[1]) for l in layouts) / area, 3) if area > 0 else 0.0


def pack_sheet(layouts: list, paper_names: list, PAPER: dict, header_height: float) -> tuple:
    """Pack group layouts on the smallest paper: drawing-order columns, first-fit-decreasing columns, then bottom-left
    2D packing (drawing order, then by height); escalates the paper only when all four fail."""
    for paper in paper_names:
        left, top, right, bottom = paper_area(paper, PAPER)
        top = snap_up(top + header_height)
        for ffd in (False, True):
            positions = _pack_columns(layouts, left, top, right, bottom, ffd)
            if positions is not None:
                return paper, positions
        for by_height in (False, True):
            positions = _pack_bottom_left(layouts, left, top, right, bottom, by_height)
            if positions is not None:
                return paper, positions
    raise ValueError('page does not fit on any supported paper')


def route_sheet(planner: Planner, key: str, positions: list, paper: str, PAPER: dict, texts: list) -> SheetPlan:
    """Translate groups onto the sheet, route the remaining connections, normalise and count."""
    left, top, right, bottom = paper_area(paper, PAPER)
    grid = sw.WireGrid(left, 20.0, right, bottom)
    wiring = sw.SheetWiring()
    placed_all, labels_all, headings = [], [], []
    for layout, gx, gy in positions:
        layout.shift(gx, gy)
        headings.append((layout.title, gx, r4(gy - 2.54)))
        placed_all.extend(layout.placed)
        wiring.segments.extend(layout.segments)
        labels_all.extend(layout.labels)
        wiring.no_connects.extend(layout.no_connects)
    # occupancy
    for p in placed_all:
        b = p.body()
        grid.block_rect(b[0], b[1], b[2], b[3], margin=GRID)
        for key_, value in p.texts.items():
            if value:
                text = p.ref if key_ == 'Reference' else (p.net or p.part['value'])
                if (key_ == 'Reference' and p.hide_reference) or (key_ == 'Value' and p.hide_value):
                    continue
                tb = text_box(value[0], value[1], text, 1.27 if p.kind == 'part' else 1.0, value[2])
                grid.block_rect(tb[0], tb[1], tb[2], tb[3])
        info = p.pins()
        for pad, pin in info.items():
            net = p.part['nets'].get(pad) if p.kind == 'part' else p.net
            grid.add_pin(pin['point'], net)
            if p.kind == 'part':
                wiring.pins[(p.ref, pad)] = dict(point=pin['point'], net=net)
            else:
                wiring.labels.append(dict(kind='power', name=p.net, point=pin['point']))
    label_size = planner.presentation.get('label_size', 1.27)
    for label in labels_all:
        if label['kind'] == 'open':
            continue
        grid.add_label(label['point'], label['name'])
        width = TEXT_W * label_size * len(label['name']) + 2.0
        x, y = label['point']
        angle = label.get('angle', 0)
        if angle == 180:
            grid.block_rect(x - width, y - 1.0, x - GRID, y + 1.0)
        elif angle == 0:
            grid.block_rect(x + GRID, y - 1.0, x + width, y + 1.0)
        elif angle == 90:
            grid.block_rect(x - 1.0, y - width, x + 1.0, y - GRID)
        else:
            grid.block_rect(x - 1.0, y + GRID, x + 1.0, y + width)
        wiring.labels.append(dict(kind=label['kind'], name=label['name'], point=label['point']))
    for seg in wiring.segments:
        grid.add_segment(seg)
    # connect the remaining components of every net on this sheet
    outward = {}
    for p in placed_all:
        if p.kind == 'part':
            for pad, pin in p.pins().items():
                outward[pin['point']] = tuple(pin['outward'])
    exceptions, label_pairs = [], []
    max_wire = planner.presentation.get('max_wire_mm', 150.0)
    loop_slack = planner.presentation.get('loop_slack_mm', 25.4)
    for net in sorted({info['net'] for info in wiring.pins.values() if info['net']} | {s.net for s in wiring.segments}):
        if planner.nets[net]['role'] == 'rail':
            continue
        components = net_components(wiring, net)
        while len(components) > 1:
            components.sort(key=lambda c: (min(p[1] for p in c), min(p[0] for p in c)))
            base = components[0]
            best = None
            for other in components[1:]:
                d = min(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a in base for b in other)
                if best is None or d < best[0]:
                    best = (d, other)
            other = best[1]
            if best[0] > max_wire and planner.nets[net]['role'] != 'cross':
                a = min(base, key=lambda p: (p[1], p[0]))
                b = min(other, key=lambda p: (p[1], p[0]))
                for p in (a, b):
                    if not any(l['point'] == p for l in wiring.labels):
                        wiring.labels.append(dict(kind='global', name=net, point=p))
                        grid.add_label(p, net)
                label_pairs.append(dict(net=net, distance=round(best[0], 1), reason='distance'))
                planner.tags_placed.add(net)
                components = [base | other] + [c for c in components if c is not base and c is not other]
                continue
            sources = {}
            for p in base:
                attached = any(s.a == p or s.b == p for s in wiring.segments if s.net == net)
                sources[sw.cell(p)] = [outward[p]] if (p in outward and not attached) else None
            targets = {sw.cell(p) for p in other}
            path = grid.route(net, sources, targets)
            if path is None:
                # label fallback: a global label at the nearest point of each component
                a = min(base, key=lambda p: p[1])
                b = min(other, key=lambda p: p[1])
                for p in (a, b):
                    if not any(l['point'] == p for l in wiring.labels):
                        wiring.labels.append(dict(kind='global', name=net, point=p))
                        grid.add_label(p, net)
                exceptions.append(dict(sheet=key, net=net, reason='no_wire_path', at=[a, b]))
                planner.tags_placed.add(net)
                components = [base | other] + components[1:]
                components.remove(other)
                continue
            length = sum(abs(path[i + 1][0] - path[i][0]) + abs(path[i + 1][1] - path[i][1]) for i in range(len(path) - 1))
            if length > 1.5 * best[0] + loop_slack:
                # the only wire path loops around other content: a pair of name tags reads better than the loop
                a = min(base, key=lambda p: (p[1], p[0]))
                b = min(other, key=lambda p: (p[1], p[0]))
                for p in (a, b):
                    if not any(l['point'] == p for l in wiring.labels):
                        wiring.labels.append(dict(kind='global', name=net, point=p))
                        grid.add_label(p, net)
                label_pairs.append(dict(net=net, distance=round(best[0], 1), wire_length=round(length, 1), reason='loop'))
                planner.tags_placed.add(net)
                components = [base | other] + [c for c in components if c is not base and c is not other]
                continue
            for i in range(len(path) - 1):
                seg = sw.Segment(net, path[i], path[i + 1])
                wiring.segments.append(seg)
                grid.add_segment(seg)
            components = net_components(wiring, net)
    sw.normalise(wiring)
    trimmed = sw.trim_dangling(wiring)
    if trimmed:
        sw.normalise(wiring)
    planner.exceptions.extend(exceptions)
    labels = [l for l in wiring.labels if l['kind'] in ('global', 'hier')]
    plan = SheetPlan(key, key, '', paper, placed_all, wiring, labels, texts + [dict(kind='heading', text=t, x=x, y=y) for t, x, y in headings],
                     [], {net: shape for (page, net), shape in planner.ports_placed.items() if page == key})
    plan.counts = dict(wires=len(wiring.segments), junctions=len(wiring.junctions), power_symbols=sum(1 for p in placed_all if p.kind == 'power'),
                       global_labels=sum(1 for l in labels if l['kind'] == 'global'), hierarchical_labels=sum(1 for l in labels if l['kind'] == 'hier'),
                       no_connects=len(wiring.no_connects), crossings=sw.crossings(wiring.segments), label_fallbacks=len(exceptions),
                       label_pairs=len(label_pairs), loop_tags=sum(1 for lp in label_pairs if lp.get('reason') == 'loop'),
                       trimmed_dangling=trimmed, paper_fill=paper_fill([l for l, _, _ in positions], paper, PAPER))
    plan.label_pairs = label_pairs
    return plan


def net_components(wiring: sw.SheetWiring, net: str) -> list:
    """Connected point sets of one net from its segments and pins (end-to-end and pin coincidence only)."""
    uf = sw.UnionFind()
    points = set()
    for seg in wiring.segments:
        if seg.net == net:
            uf.union(seg.a, seg.b)
            points.update((seg.a, seg.b))
    for (ref, pad), info in wiring.pins.items():
        if info['net'] == net:
            points.add(info['point'])
            uf.find(info['point'])
    for label in wiring.labels:
        if label['name'] == net and label['kind'] in ('hier', 'power', 'global'):
            points.add(label['point'])
            uf.find(label['point'])
    # a point lying on the interior of a same-net segment is connected once normalise() splits it there
    segs = [s for s in wiring.segments if s.net == net]
    for p in list(points):
        for s in segs:
            if sw.interior(p, s.a, s.b):
                uf.union(p, s.a)
    groups = defaultdict(set)
    for p in points:
        groups[uf.find(p)].add(p)
    return [frozenset(g) for g in groups.values()]


# --- root sheet ------------------------------------------------------------------------------------------------------------

def plan_root(sheets: list, planner: Planner, PAPER: dict, paper: str, top: float) -> dict:
    """Sheet symbols with pins (inputs left, others right), stubs and one global anchor per pin."""
    entries = []
    longest = max([len(n) for s in sheets for n in s['ports']] + [4])
    label_w = snap_up(TEXT_W * planner.presentation.get('label_size', 1.27) * longest + 7.62)
    sheet_w = 111.76
    pitch_x = snap_up(sheet_w + 2 * label_w + 7.62)
    for s in sheets:
        ports = sorted(s['ports'].items())
        left = [(n, sh) for n, sh in ports if sh == 'input']
        right = [(n, sh) for n, sh in ports if sh != 'input']
        rows = max(len(left), len(right))
        h = max(25.4, snap_up(2.54 * (rows + 2)))
        entries.append(dict(sheet=s, left=left, right=right, w=sheet_w, h=h))
    for name in list(PAPER)[list(PAPER).index(paper):]:
        width, height = PAPER[name]
        columns = max(1, int((width - 12.7 - label_w - 12.7) // pitch_x))
        x0 = snap(12.7 + label_w)
        x, y, row_h = x0, top, 0.0
        positions, ok = [], True
        for e in entries:
            if x > x0 and x + e['w'] > width - 12.7 - label_w:
                x, y, row_h = x0, snap_up(y + row_h + 12.7), 0.0
            if y + e['h'] > height - 30:
                ok = False
                break
            positions.append((snap(x), snap(y)))
            x = snap(x + pitch_x)
            row_h = max(row_h, e['h'])
        if ok:
            return dict(paper=name, entries=entries, positions=positions, columns=columns)
    raise ValueError('root sheet does not fit on any supported paper')
