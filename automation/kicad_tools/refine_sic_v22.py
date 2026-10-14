"""Reproducible, bounded V2.2 ECOs applied to hash-checked frozen V2.1 boards.

Run after generate_sic_schematics and both write_model entry points, under KiCad Python:
    python -m automation.kicad_tools.refine_sic_v22 --board all
Native ERC/DRC and three-way netlist comparison remain independent acceptance gates.
This is an ECO replay, not an unconstrained reroute or a fabrication approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import uuid
from pathlib import Path

from automation.kicad_tools.sic_buck_common import EXAMPLE, BANNER, GENERATION

BASE_HASH = {
    "power": "ae4ca86c438f56b8cb23c3f93b8e415aea73a509a604c69a0f28f04ea5519b56",
    "control": "52ca6c234357948a1119db0082ffd5ddcb706a852d9778787f74450ea1183428",
}
REMOVED_ITEMS = []  # Keep SWIG wrappers alive until board serialization completes.
# Cap centre, rotation, existing VCC escape via. B.Cu avoids consuming the IC's front courtyard.
LOCAL_BYPASS = {
    "C76": ((13.5, 48.0), 180, (15.5, 48.0), "U4"),
    "C77": ((72.75, 57.0), 0, (71.75, 58.0), "U8"),
    "C78": ((56.0, 58.75), 180, (57.0, 59.75), "U10"),
    "C79": ((61.375, 67.25), 180, (62.625, 68.5), "U11"),
}


def mm(point):
    import pcbnew as pcb
    return tuple(pcb.ToMM(point))


def point(xy):
    import pcbnew as pcb
    return pcb.VECTOR2I(*(pcb.FromMM(v) for v in xy))


def pads(fp):
    return {p.GetNumber(): p for p in fp.Pads() if p.GetNumber()}


def track(board, a, b, net, layer, width=0.25):
    import pcbnew as pcb
    if math.dist(a, b) < 1e-6:
        return
    t = pcb.PCB_TRACK(board)
    t.SetStart(point(a)); t.SetEnd(point(b)); t.SetWidth(pcb.FromMM(width))
    t.SetLayer(layer); t.SetNet(board.FindNet(net)); board.Add(t)


def load_part(board, part, mapping, directory, xy, angle, side="B", old=None):
    import pcbnew as pcb
    lib, name = part["footprint"].split(":")
    fp = pcb.FootprintLoad(str(directory / "libraries" / f"{lib}.pretty"), name)
    if fp is None:
        raise ValueError(f"Missing footprint {part['footprint']}")
    board.Add(fp)  # KiCad 10 Flip requires a parent board (copper layer stack).
    fp.SetFPID(pcb.LIB_ID(lib, name)); fp.SetReference(part["ref"]); fp.SetValue(part["value"])
    fp.SetPath(pcb.KIID_PATH(mapping[part["ref"]])); fp.SetDNP(bool(part.get("dnp")))
    if side == "B":
        fp.Flip(fp.GetPosition(), pcb.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(angle); fp.SetPosition(point(xy))
    fp.Reference().SetLayer(pcb.B_Fab if side == "B" else pcb.F_Fab)
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    fp.SetUuid(pcb.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL, f"aipe/v22/{part['board']}/{part['ref']}"))))
    for p in fp.Pads():
        if p.GetNumber():
            net = part["nets"][p.GetNumber()]
            if net:
                p.SetNet(board.FindNet(net))
    if old:
        board.Remove(old)
        REMOVED_ITEMS.append(old)
    return fp


def route_between(router, net, a, b, layers, width=0.25):
    """Coordinates include routing-layer index; never silently accept a missing route."""
    start = (*router.to_grid(*a[:2]), a[2]); end = (*router.to_grid(*b[:2]), b[2])
    path = router.astar(start, end, net, layers=layers, width=width)
    if not path:
        print("Route endpoint occupancy", net, start, end, router.code[net],
              [int(router.grid.occ[i,start[1],start[0]]) for i in layers],
              [int(router.grid.occ[i,end[1],end[0]]) for i in layers], flush=True)
        raise ValueError(f"No bounded ECO route: {net} {a} -> {b}")
    router.emit(path, net, width)
    # Exact pad centres need not be on the router grid.
    if a[2] is not None:
        router.track(a[:2], router.to_mm(*start[:2]), net, a[2], width)
    if b[2] is not None:
        router.track(router.to_mm(*end[:2]), b[:2], net, b[2], width)


def power_eco(board, parts, mapping, directory):
    import pcbnew as pcb
    from automation.kicad_tools.grid_router import Router
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    old = fps["R57"]; before = {n: mm(p.GetPosition()) for n, p in pads(old).items()}
    replacement = load_part(board, parts["R57"], mapping, directory, (169.0, 137.25), 0, "B", old)
    for item in list(board.GetTracks()):
        if item.GetNetname() == "ISO_RLIM" and item.GetLayer() == pcb.B_Cu and not isinstance(item, pcb.PCB_VIA):
            board.Remove(item); REMOVED_ITEMS.append(item)
    hv_router = Router(board, 23, 12, ["F.Cu", "In2.Cu", "B.Cu"], origin=(153, 128),
                       grid=0.125, trace=0.25, clearance=0.35, via=(0.6, 0.3), style={"diagonal": True},
                       net_rules={n: {"clearance": 3.1} for n in ("VIN", "VOUT", "SW", "VOUT_L")})
    for n, pad in pads(replacement).items():
        source = (161.375, 137.35, None) if n == "1" else (166.125, 135.5, None)
        route_between(hv_router, pad.GetNetname(), source, (*mm(pad.GetPosition()), 2), (0, 1, 2))
    # Detach only the verified terminal branch from R82 to its old 3V3 tree.
    edges = [((182.875, 174.5), (182.875, 173.0)), ((182.875, 173.0), (184.125, 173.0)),
             ((184.125, 173.0), (184.625, 172.5)), ((184.625, 172.5), (184.625, 172.125)),
             ((184.625, 172.125), (185.375, 172.125))]
    removed = 0
    for item in list(board.GetTracks()):
        if type(item) is pcb.PCB_TRACK and item.GetNetname() == "3V3" and item.GetLayer() == pcb.F_Cu:
            ends = {mm(item.GetStart()), mm(item.GetEnd())}
            if any(ends == set(e) for e in edges):
                board.Remove(item); REMOVED_ITEMS.append(item); removed += 1
    if removed != len(edges):
        raise ValueError(f"Frozen terminal branch differs: removed {removed}, expected {len(edges)}")
    for item in list(board.GetTracks()):
        if isinstance(item, pcb.PCB_VIA) and item.GetNetname() == "3V3" and mm(item.GetPosition()) == (185.375, 172.125):
            board.Remove(item); REMOVED_ITEMS.append(item)
        elif isinstance(item, pcb.PCB_VIA) and item.GetNetname() == "5V_ISO" and mm(item.GetPosition()) == (164.75, 133.5):
            board.Remove(item); REMOVED_ITEMS.append(item)
    for ref in ("R82", "R83"):
        fps[ref].SetValue(parts[ref]["value"])
        for n, pad in pads(fps[ref]).items():
            pad.SetNet(board.FindNet(parts[ref]["nets"][n]))
    router = Router(board, 240, 30, ["F.Cu", "In2.Cu", "B.Cu"], origin=(0, 150),
                    grid=0.125, trace=0.25, clearance=0.3, via=(0.6, 0.3),
                    style={"diagonal": True}, max_nodes=1500000)
    a = mm(pads(fps["R82"])["1"].GetPosition())
    b = mm(pads(fps["C86"])["1"].GetPosition())
    route_between(router, "REF2V5_PB", (*a, 0), (*b, 0), (0, 1, 2))
    return {"R57": {"old": "1k / 0805", "new": "160 / 1206 / 0.66 W"},
            "R82": "6.65k from REF2V5_PB", "R83": "1.01k to GND_CTRL", "removed_3v3_branch_segments": removed,
            "routing": router.report(), "clamp_candidate": "Not applied: lower Kelvin-pour projection; see review/v22/clamp_candidate_rejected.json"}


def refine_clamp(board):
    """Experimental candidate, NOT applied by refine(): rejected after return-path comparison.

    Retained as a reproducible candidate generator, not as an accepted electrical improvement.
    """
    import pcbnew as pcb
    from automation.kicad_tools.grid_router import Router
    net = "LS_CLMP"
    def metrics():
        items = [t for t in board.GetTracks() if t.GetNetname() == net]
        return dict(length_mm=sum(pcb.ToMM(t.GetLength()) for t in items if not isinstance(t, pcb.PCB_VIA)),
                    vias=sum(isinstance(t, pcb.PCB_VIA) for t in items))
    before = metrics()
    for item in list(board.GetTracks()):
        if item.GetNetname() != net:
            continue
        keep = (isinstance(item, pcb.PCB_VIA) and mm(item.GetPosition()) == (120.875, 138.5))
        keep |= (type(item) is pcb.PCB_TRACK and item.GetLayer() == pcb.F_Cu and max(mm(item.GetStart())[0], mm(item.GetEnd())[0]) < 121)
        if not keep:
            board.Remove(item); REMOVED_ITEMS.append(item)
    router = Router(board, 25, 15, ["F.Cu", "In2.Cu", "B.Cu"], origin=(118,125),
                    grid=.125, trace=.25, clearance=.31, via=(.6,.3), style={"diagonal": True},
                    net_rules={n: {"clearance": 3.1} for n in ("VIN", "VOUT", "SW", "VOUT_L")})
    goal = next(p for f in board.GetFootprints() if f.GetReference() == "R39" for p in f.Pads() if p.GetNumber() == "1")
    route_between(router, net, (120.875,138.5,None), (*mm(goal.GetPosition()),2), (0,1,2), .25)
    after = metrics()
    if after['length_mm'] >= before['length_mm'] or after['vias'] > before['vias']:
        raise ValueError(f"Clamp candidate does not improve geometry: {before} -> {after}")
    return dict(before=before, after=after, scope="Connection geometry only; no measured inductance or clamp transient validation")


def control_eco(board, parts, mapping, directory):
    import pcbnew as pcb
    import numpy as np
    from automation.kicad_tools.grid_router import Router
    router = Router(board, 120, 80, ["F.Cu", "In2.Cu", "B.Cu"], grid=0.125,
                    trace=0.25, clearance=0.2, via=(0.6, 0.3), style={"diagonal": True})
    rows = []
    for ref, (_, _, source, target) in LOCAL_BYPASS.items():
        fp = load_part(board, parts[ref], mapping, directory, (-20, -20), 0)
        # Search local placements against actual existing copper, not a decorative anchor.
        # A pre-existing same-net via must stay outside the SMD land (no via-in-pad process assumed).
        legal = []
        for dx in range(-14, 15):
            for dy in range(-14, 15):
                xy = (source[0] + dx*.25, source[1] + dy*.25)
                for angle in (0, 90, 180, 270):
                    fp.SetOrientationDegrees(angle); fp.SetPosition(point(xy))
                    pp = pads(fp); good = True
                    for pad in pp.values():
                        box = pad.GetBoundingBox()
                        x0,y0 = router.to_grid(pcb.ToMM(box.GetX()), pcb.ToMM(box.GetY()))
                        x1,y1 = router.to_grid(pcb.ToMM(box.GetRight()), pcb.ToMM(box.GetBottom()))
                        occupied = router.grid.occ[2, y0:y1+1, x0:x1+1]
                        if occupied.size == 0 or np.any((occupied != 0) & (occupied != pad.GetNetCode())):
                            good = False; break
                        box.Inflate(pcb.FromMM(.35))
                        for t in board.GetTracks():
                            if isinstance(t, pcb.PCB_VIA) and box.Contains(t.GetPosition()):
                                good = False; break
                        if not good: break
                    if good:
                        a = mm(pp['1'].GetPosition()); g = mm(pp['2'].GetPosition())
                        legal.append((math.dist(a, source)+.2*math.dist(g, source), xy, angle))
        if not legal:
            raise ValueError(f"No copper-clear local placement for {ref}")
        ground = None
        for _, xy, angle in sorted(legal):
            fp.SetOrientationDegrees(angle); fp.SetPosition(point(xy)); router.rebuild_occupancy()
            pp = pads(fp); a = mm(pp["1"].GetPosition()); g = mm(pp["2"].GetPosition())
            supply = router.astar((*router.to_grid(*a), 2), (*router.to_grid(*source), None), "3V3", layers=(0, 1, 2), width=.25)
            if not supply or len(supply)*.125 > 6:
                continue
            state = router.snapshot()
            route_between(router, "3V3", (*a, 2), (*source, None), (0, 1, 2), 0.25)
            # Keep the ground return short and exclude via-in-pad processing.
            candidates = sorted(((g[0]+dx*.125, g[1]+dy*.125) for dx in range(-16,17) for dy in range(-16,17)
                                 if .85 <= math.hypot(dx*.125,dy*.125) <= 2), key=lambda v: (math.dist(g,v),v))
            for candidate in candidates:
                ix, iy = router.to_grid(*candidate)
                if router.via_allowed(ix, iy, "GND_CTRL"):
                    start = (*router.to_grid(*g), 2); end = (ix, iy, 2)
                    path = router.astar(start, end, "GND_CTRL", layers=(2,), width=.25)
                    if path and len(path)*.125 < 3:
                        ground = router.to_mm(ix, iy)
                        router.emit(path, "GND_CTRL", .25); router.via(ground, "GND_CTRL")
                        router.track(g, router.to_mm(*start[:2]), "GND_CTRL", 2, .25)
                        break
            if ground is not None:
                router.end_snapshot()
                break
            REMOVED_ITEMS.extend(router.created or ())
            router.restore(state)
        if ground is None:
            raise ValueError(f"No short ground escape for {ref}")
        rows.append(dict(ref=ref, target=target, centre_mm=xy, rotation=angle, supply_pad_mm=a, existing_vcc_via_mm=source,
                         ground_pad_mm=g, ground_via_mm=ground))
    return {"local_bypasses": rows, "routing": router.report()}


def refine(label):
    import pcbnew as pcb
    from automation.kicad_tools.generate_sic_power_board import rule_aware_refill
    name = f"AIPE_SiC_Buck_{label.title()}"
    directory = EXAMPLE / "kicad" / f"{label}_board"
    base = EXAMPLE / "releases/v2.1/kicad" / f"{label}_board" / f"{name}.kicad_pcb"
    if hashlib.sha256(base.read_bytes()).hexdigest() != BASE_HASH[label]:
        raise ValueError("Frozen board identity changed; review the baseline before applying this ECO")
    board = pcb.LoadBoard(str(base))
    parts = {p["ref"]: p for p in json.loads((EXAMPLE / f"design/circuit_{label}.json").read_text())}
    mapping = json.loads((EXAMPLE / f"design/schematic_mapping_{label}.json").read_text())["paths"]
    result = (power_eco if label == "power" else control_eco)(board, parts, mapping, directory)
    board.GetTitleBlock().SetRevision(GENERATION); board.GetTitleBlock().SetComment(0, BANNER)
    board.GetTitleBlock().SetTitle(f"SiC buck 400V / 200V / 5kW - {label} board")
    for index in range(1, 9):
        board.GetTitleBlock().SetComment(index, "")
    for item in board.GetDrawings():
        if isinstance(item, pcb.PCB_TEXT):
            item.SetText(item.GetText().replace("V2.1", "V2.2"))
    destination = directory / f"{name}.kicad_pcb"
    pcb.SaveBoard(str(destination), board, True)
    result["refill"] = rule_aware_refill(destination)
    result.update(baseline_sha256=BASE_HASH[label], output_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                  native_verification="Pending; see subsequent independent ERC/DRC/netlist reports")
    path = EXAMPLE / f"review/v22/eco_{label}.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(label, "ECO written", destination, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", choices=("power", "control", "all"), default="all")
    args = parser.parse_args()
    for label in (("power", "control") if args.board == "all" else (args.board,)):
        refine(label)


if __name__ == "__main__":
    main()
