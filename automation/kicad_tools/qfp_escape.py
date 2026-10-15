"""Package-relative QFP escape planning without project coordinates or file IO.

Extracted from the validated V2 router; dimensions and voltage-net names are
explicit arguments. A plan is geometry only; native DRC must validate it against
other components, back-side pads and project rules.
"""
from __future__ import annotations
import math

def snap(value,grid):return round(value/grid)*grid

def classify_side(pad_xy, centre):
    """('E'|'W'|'S'|'N', lateral coordinate, outward unit vector) of a pad relative to a package centre."""
    dx, dy = pad_xy[0] - centre[0], pad_xy[1] - centre[1]
    if abs(dx) >= abs(dy):
        return ('E' if dx > 0 else 'W'), pad_xy[1], (1 if dx > 0 else -1, 0)
    return ('S' if dy > 0 else 'N'), pad_xy[0], (0, 1 if dy > 0 else -1)


def row_axis(pads: list[dict]):
    """'x' when the pads form two columns (SO package, rows left/right), 'y' for two rows top/bottom, None for four sides."""
    xs = {round(p['xy'][0], 2) for p in pads}
    ys = {round(p['xy'][1], 2) for p in pads}
    if len(xs) <= 2 < len(ys):
        return 'x'
    if len(ys) <= 2 < len(xs):
        return 'y'
    return None


def pad_runs(pads: list[dict], centre, pitch_max: float = 0.75):
    """Pads grouped by package side and split into runs of consecutive pins (lateral gap <= pitch_max).

    Two-row packages are classified by their row axis (corner pins of a tall SO package lie closer to the short
    sides than to their own row and would otherwise escape through the row's end)."""
    sides: dict = {}
    axis = row_axis(pads)
    for pad in pads:
        if axis == 'x':
            dx = pad['xy'][0] - centre[0]
            key, lateral, out = ('E' if dx > 0 else 'W'), pad['xy'][1], (1 if dx > 0 else -1, 0)
        elif axis == 'y':
            dy = pad['xy'][1] - centre[1]
            key, lateral, out = ('S' if dy > 0 else 'N'), pad['xy'][0], (0, 1 if dy > 0 else -1)
        else:
            key, lateral, out = classify_side(pad['xy'], centre)
        sides.setdefault(key, []).append((round(lateral, 4), pad, out))
    runs = []
    for key in sorted(sides):
        items = sorted(sides[key], key=lambda t: t[0])
        run = []
        for item in items:
            if run and item[0] - run[-1][0] > pitch_max:
                runs.append((key, run))
                run = []
            run.append(item)
        if run:
            runs.append((key, run))
    return runs


def _escape_record(pad, key, lateral, out, direction, distance, grid, exception=False):
    sign = -1 if direction == 'in' else 1
    half = max(pad['size']) / 2
    ux, uy = out
    end = (pad['xy'][0] + sign * ux * half, pad['xy'][1] + sign * uy * half)
    via = (end[0] + sign * ux * distance, end[1] + sign * uy * distance)
    if grid:
        via = (snap(via[0], grid), snap(via[1], grid))
    return dict(number=str(pad['number']), net=pad['net'], side=key, lateral=lateral, direction=direction, distance=distance,
                out=[ux, uy], pad=[round(pad['xy'][0], 4), round(pad['xy'][1], 4)], via=[round(via[0], 4), round(via[1], 4)], exception=exception)


def plan_dsp_escapes(pads: list[dict], centre, *, grid: float = .25, inward: float = .65, outward=(.65,2.0),
                     core_net: str = '1V9', io_net: str = '3V3', via_diameter: float = .6, clearance: float = .2) -> list[dict]:
    """Escape records for the connected LQFP pads: direction, distance and the grid-snapped via position.

    ``pads``: [{number, net, xy, size}] in board mm (connected pads only). Along each contiguous run of
    connected pins (0.5 mm pitch) the directions alternate; the phase of a run minimises weighted parity
    violations (core-rail pin outward counts 2, I/O-rail pin inward counts 1) and ties follow the greedy
    router (first pin outward). Outward pins alternate the near/far row distances along the run.
    """
    for pad in pads:
        _, lateral, _ = classify_side(pad['xy'], centre)
        if abs(lateral - snap(lateral, grid)) > 1e-6:
            raise ValueError(f"DSP pad {pad['number']} lateral coordinate {lateral} is off the {grid} mm escape grid; move the DSP")
    records = []
    for key, run in pad_runs(pads, centre):
        best = None
        for phase in (0, 1):  # pins whose index % 2 == phase go inward
            violations = sum(2 for i, (_, p, _) in enumerate(run) if p['net'] == core_net and i % 2 != phase)
            violations += sum(1 for i, (_, p, _) in enumerate(run) if p['net'] == io_net and i % 2 == phase)
            score = (violations, 0 if phase == 1 else 1)
            if best is None or score < best[0]:
                best = (score, phase)
        phase = best[1]
        k_out = 0
        for i, (lateral, pad, out) in enumerate(run):
            direction = 'in' if i % 2 == phase else 'out'
            if direction == 'in':
                distance = inward
            else:
                distance = outward[k_out % len(outward)]
                k_out += 1
            exception = (pad['net'] == core_net and direction == 'out') or (pad['net'] == io_net and direction == 'in')
            records.append(_escape_record(pad, key, lateral, out, direction, distance, grid, exception))
    for i, a in enumerate(records):
        for b in records[i + 1:]:
            if math.dist(a['via'], b['via']) < via_diameter + clearance - 1e-6:
                raise ValueError(f"escape vias of DSP pads {a['number']} and {b['number']} are closer than {via_diameter + clearance} mm")
    return records

