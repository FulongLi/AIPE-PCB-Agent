"""Fine-pitch row escapes of the DAB-V1 boards: same-net bridges, one stub per same-net run, stub lengths from the
router's occupancy model.

Why this exists (DAB-V1 routing remediation, docs/dab-10kw/routing-remediation.md): the UCC14141 DWN-36 rows (0.40 mm
lands at 0.65 mm pitch) and the 0.65 mm TSSOP/VSSOP rows of the control board cannot be escaped pad by pad.  A grid
router models every pad with a clearance halo of ``clearance + trace/2`` (0.4 mm), wider than the 0.25 mm land gap, and
a net wider than its stub (12V_BIAS 0.8 mm, GNDP 0.6 mm, VDD/VEE 0.5 mm) cannot leave a port that sits between the
stubs of its neighbours: the port is sealed and the connection is reported as unresolved after one expansion.  The
2026-10-21 runs lost 30 fan-out connections and about 35 route connections per power board this way.

The remedy is geometric and lives in the plan, not in the router:

* consecutive pads of one net are joined by a *bridge*, a pre-routed track along the row inside the lands (width at
  most 0.3 mm, so it stays within the 0.40 mm land and keeps the 0.25 mm clearance to the next land);
* each run of a routed net gets exactly one exact stub, at the run's midpoint (between two lands for even runs, on the
  bridge), the other pads of the run are skipped by the fan-out;
* a stub's length is the smallest value that puts its port clear of the neighbouring lands' halos and, for a net wider
  than its stub, clear of the dilated halos of the neighbouring stubs, so the full-width track can start at the port;
* pads of pour-connected nets (PGND, BUS_P planes) are bridged and keep the fan-out's via escape; ground pads of fine rows get
  a stub with a via at its end where it fits, otherwise they become stranded ports that run_plan ties to the nearest ground via.

Everything here is pure Python over ``ProjectBoard.pads()`` records so that the row plan is unit-tested on the host;
the result is consumed by ``grid_router.run_plan`` through ``fanout.exact_stub_pads`` (``[ref, pad, length, [ux, uy],
lateral]``), ``pre_routed.tracks``, ``fanout.skip_pads`` and ``fanout.exact_via_pads``.  Native DRC decides.
"""
from __future__ import annotations

import fnmatch
import math

BRIDGE_WIDTH_MAX = 0.3


def first_match(net: str, table: dict, default=None):
    """First glob pattern of ``table`` matching ``net`` (the routing requirement files list widths this way)."""
    for pattern, value in table.items():
        if fnmatch.fnmatchcase(net, pattern):
            return value
    return default


def outward_direction(xy, bbox) -> tuple:
    """Unit step (ux, uy) pointing from the footprint out through the pad, normalised by the courtyard half sizes.

    The raw comparison of |dx| and |dy| fails at the ends of long packages (a DWN-36 end pad is 5.5 mm from the centre
    along the row but only 5.0 mm across it): dividing by the half sizes classifies every pad of a row alike.
    """
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    hw, hh = max((bbox[2] - bbox[0]) / 2, 1e-6), max((bbox[3] - bbox[1]) / 2, 1e-6)
    nx, ny = (xy[0] - cx) / hw, (xy[1] - cy) / hh
    if abs(ny) >= abs(nx):
        return (0, 1 if ny > 0 else -1)
    return (1 if nx > 0 else -1, 0)


def halo_mm(width: float, trace: float, clearance: float, eps: float) -> float:
    """Radius the router marks around a track of ``width`` (grid_router._mark_track)."""
    return width / 2 + clearance + trace / 2 + eps


def dilation_mm(width: float, trace: float, grid: float) -> float:
    """Extra dilation (whole cells) the router applies to foreign copper for a net wider than the default trace."""
    return math.ceil(max(0.0, (width - trace) / 2) / grid - 1e-9) * grid


def pad_direction(p: dict, candidates: list, bbox, *, t_tolerance: float = 0.1) -> tuple:
    """Outward step of pad ``p``: across the pad row it belongs to.

    The row is the larger of the two pad clusters sharing the pad's y (a row along x) or its x (a row along y) within
    ``t_tolerance``; the sign points away from the footprint centre.  A tie (two-pad parts, corner pads of grids) falls
    back to the courtyard-normalised direction.
    """
    same_y = sum(1 for q in candidates if abs(q['xy'][1] - p['xy'][1]) <= t_tolerance)
    same_x = sum(1 for q in candidates if abs(q['xy'][0] - p['xy'][0]) <= t_tolerance)
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    if same_y > same_x:
        return (0, 1 if p['xy'][1] > cy else -1)
    if same_x > same_y:
        return (1 if p['xy'][0] > cx else -1, 0)
    return outward_direction(p['xy'], bbox)


def group_rows(pads: list, bbox, *, max_pad_mm: float = 1.0, t_tolerance: float = 0.1) -> list:
    """Rows of SMD pads of one footprint: same outward direction and same coordinate across it, sorted along it.

    Returns ``[dict(direction, t, pads, pitch)]``; ``pitch`` is the median spacing (None for a single pad).  Pads larger
    than ``max_pad_mm`` in both dimensions (thermal pads) and plated pads are left out.
    """
    rows = []
    candidates = [p for p in pads if not p.get('thru') and p.get('pin') and min(p['box'][2] - p['box'][0], p['box'][3] - p['box'][1]) <= max_pad_mm]
    for p in candidates:
        ux, uy = pad_direction(p, candidates, bbox, t_tolerance=t_tolerance)
        t = p['xy'][1] if uy else p['xy'][0]
        s = p['xy'][0] if uy else p['xy'][1]
        for row in rows:
            if row['direction'] == (ux, uy) and abs(row['t'] - t) <= t_tolerance:
                row['pads'].append((s, p))
                break
        else:
            rows.append(dict(direction=(ux, uy), t=t, pads=[(s, p)]))
    out = []
    for row in rows:
        row['pads'].sort(key=lambda sp: sp[0])
        gaps = sorted(b[0] - a[0] for a, b in zip(row['pads'], row['pads'][1:]))
        pitch = gaps[len(gaps) // 2] if gaps else None
        out.append(dict(direction=row['direction'], t=round(row['t'], 4), pads=[p for _, p in row['pads']], s=[s for s, _ in row['pads']], pitch=pitch))
    return out


def plan_rows(ref: str, pads: list, bbox, *, width_of, fanout_width_of, trace: float, clearance: float, grid: float, eps: float,
              base_stub: float, pour_nets=(), exact_via_nets=(), critical_nets=(), fine_pitch_mm: float = 0.8, band_mm: float = 0.0,
              max_rounds: int = 8) -> dict:
    """Escape plan of one IC footprint; see the module docstring.

    ``width_of(net)`` / ``fanout_width_of(net)`` give the routed and the stub width; ``pour_nets`` are connected by pours
    (bridged, not stubbed); ``exact_via_nets`` get a via at the stub end when it fits; ``critical_nets`` keep their pad-centre
    ports (no stub) but get an exit lane.  ``band_mm`` is the free fan-out band in front of the pin rows (the placement's IC
    stub reserve): every stub gets a reserved exit *lane* of its own width up to ``band_mm - 1.0`` beyond the land, so that no
    earlier-routed net can run across the row's exits (the 2026-10-21 run lost the DWN rows this way: nets turned sideways at
    their ports and sealed their neighbours), and a net wider than its stub gets a stub that ends beyond the neighbouring
    lanes, where its full width can start.  Returns ``dict(stubs, bridges, lanes, skip_pads, exact_via_pads, rows, warnings)``.
    """
    stubs, bridges, lanes, skip_pads, exact_via, summaries, warnings = [], [], [], [], [], [], []
    pour_nets, exact_via_nets, critical_nets = set(pour_nets), set(exact_via_nets), set(critical_nets)
    lane_end = max(0.0, float(band_mm) - 1.0)  # lanes and long stubs stop 1 mm before the parts start

    def add_lane(pin, length):
        if length > grid:
            lanes.append([ref, pin, round(length, 3)])

    for row in group_rows(pads, bbox):
        ux, uy = row['direction']
        fine = row['pitch'] is not None and row['pitch'] < fine_pitch_mm
        if not fine:
            for p in row['pads']:
                if not p['net'] or p['net'] in pour_nets or p['net'] in exact_via_nets:
                    continue  # pour nets and the ground: the default via escape of the fan-out (a stub via rarely fits next to 0.6 mm lands)
                if p['net'] in critical_nets:
                    add_lane(p['pin'], lane_end)  # port at the pad centre, lane from the land outwards
                    continue
                stubs.append([ref, p['pin'], round(base_stub, 3), [ux, uy], 0.0])
                add_lane(p['pin'], lane_end - base_stub)
            continue
        # same-net runs along the row
        runs, current = [], []
        for s, p in zip(row['s'], row['pads']):
            if current and p['net'] == current[-1][1]['net'] and p['net']:
                current.append((s, p))
            else:
                if current:
                    runs.append(current)
                current = [(s, p)]
        if current:
            runs.append(current)
        layer = row['pads'][0]['layers'][0] if row['pads'][0].get('layers') else 'F.Cu'
        stubbed = []  # (s_mid, net, stub pad, lateral)
        for run in runs:
            net = run[0][1]['net']
            if not net:
                continue
            first, last = run[0][1], run[-1][1]
            extent = ((first['box'][3] - first['box'][1]) if uy else (first['box'][2] - first['box'][0])) / 2
            pad_w = ((first['box'][2] - first['box'][0]) if uy else (first['box'][3] - first['box'][1]))
            t_bridge = row['t'] + (uy or ux) * 0.45 * extent
            if len(run) >= 2:
                width = round(min(BRIDGE_WIDTH_MAX, pad_w - 0.1), 3)
                a = (run[0][0], t_bridge) if uy else (t_bridge, run[0][0])
                b = (run[-1][0], t_bridge) if uy else (t_bridge, run[-1][0])
                bridges.append(dict(net=net, layer=layer, a=[round(a[0], 4), round(a[1], 4)], b=[round(b[0], 4), round(b[1], 4)], width=width,
                                    note=f'{ref} pins {first["pin"]}-{last["pin"]} same-net row bridge'))
            if net in pour_nets:
                continue  # bridged; the pads keep the default via escape so that a pour pocket enclosed by the row's tracks still reaches the plane
            s_mid = (run[0][0] + run[-1][0]) / 2
            stub_s, stub_pad = min(run, key=lambda sp: (abs(sp[0] - s_mid), sp[0]))
            for s, p in run:
                if p is not stub_pad:
                    skip_pads.append([ref, p['pin']])
            stubbed.append(dict(s=s_mid, net=net, pad=stub_pad, lateral=round(s_mid - stub_s, 4), extent=extent))
        # stub lengths: clear of the lands' halos; a net wider than its stub ends beyond the exit lanes / stubs of its neighbours
        lengths = {}
        for item in stubbed:
            W = float(width_of(item['net']))
            lengths[id(item)] = max(base_stub, clearance + trace / 2 + dilation_mm(W, trace, grid) + 0.1)
        for _ in range(max_rounds):
            changed = False
            for item in stubbed:
                W = float(width_of(item['net']))
                dil = dilation_mm(W, trace, grid)
                for other in stubbed:
                    if other is item or other['net'] == item['net']:
                        continue
                    d = abs(item['s'] - other['s'])
                    w_other = float(fanout_width_of(other['net']))
                    need = halo_mm(w_other, trace, clearance, eps) + dil
                    if d < need - 1e-9:
                        reach = max(lengths[id(other)], lane_end)  # the neighbour's copper or reserved lane ends here
                        wanted = reach + w_other / 2 + math.sqrt(need * need - d * d) + grid
                        if wanted > lengths[id(item)] + 1e-9:
                            lengths[id(item)] = wanted
                            changed = True
            if not changed:
                break
        else:
            warnings.append(f'{ref}: adjacent wide nets chase each other in the row at t={row["t"]}; lengths capped after {max_rounds} rounds')
        for item in stubbed:
            length = math.ceil(lengths[id(item)] / 0.05 - 1e-9) * 0.05
            stubs.append([ref, item['pad']['pin'], round(length, 3), [ux, uy], item['lateral']])
            add_lane(item['pad']['pin'], lane_end - length)
            if item['net'] in exact_via_nets:
                exact_via.append([ref, item['pad']['pin']])
        summaries.append(dict(ref=ref, direction=[ux, uy], t=row['t'], pitch=round(row['pitch'], 4), pads=len(row['pads']), runs=len(runs),
                              bridges=sum(1 for r in runs if len(r) >= 2), stubs=len(stubbed), lane_end=lane_end,
                              lengths={item['net']: round(lengths[id(item)], 3) for item in stubbed}))
    return dict(stubs=stubs, bridges=bridges, lanes=lanes, skip_pads=skip_pads, exact_via_pads=exact_via, rows=summaries, warnings=warnings)
