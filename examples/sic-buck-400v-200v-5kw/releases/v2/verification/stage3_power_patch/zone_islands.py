"""List the fill islands of every zone of the given nets and the pads / vias each island touches (KiCad Python).

usage: python zone_islands.py BOARD.kicad_pcb NET [NET ...]
"""
import sys

import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
nets = set(sys.argv[2:])
mm = pcbnew.ToMM
pads = [(fp.GetReference(), p) for fp in board.GetFootprints() for p in fp.Pads() if p.GetNetname() in nets]
vias = [t for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() in nets]
for z in board.Zones():
    if z.GetIsRuleArea() or z.GetNetname() not in nets:
        continue
    for layer in z.GetLayerSet().Seq():
        poly = z.GetFilledPolysList(layer)
        bb = z.GetBoundingBox()
        print(f"zone [{z.GetNetname()}] {board.GetLayerName(layer)} prio={z.GetAssignedPriority()} bbox=({mm(bb.GetX()):.1f},{mm(bb.GetY()):.1f})-"
              f"({mm(bb.GetRight()):.1f},{mm(bb.GetBottom()):.1f}) islands={poly.OutlineCount()}")
        for i in range(poly.OutlineCount()):
            outline = poly.Outline(i)
            ob = outline.BBox()
            island = pcbnew.SHAPE_POLY_SET(outline)
            touching_pads = [f"{ref}.{p.GetNumber()}" for ref, p in pads if p.IsOnLayer(layer) and island.Collide(p.GetEffectiveShape(layer), 0)]
            touching_vias = [f"({mm(v.GetPosition().x):.1f},{mm(v.GetPosition().y):.1f})" for v in vias if island.Collide(v.GetEffectiveShape(layer), 0)]
            print(f"   island {i}: bbox=({mm(ob.GetX()):.1f},{mm(ob.GetY()):.1f})-({mm(ob.GetRight()):.1f},{mm(ob.GetBottom()):.1f}) "
                  f"area={outline.Area()/1e12:.0f} mm2 pads={len(touching_pads)} {touching_pads[:8]} vias={len(touching_vias)} {touching_vias[:6]}")
