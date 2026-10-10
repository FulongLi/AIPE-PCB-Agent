"""Dump placement / zones / rule areas / edge cuts / pads of selected refs from a board (KiCad Python).

usage: python dump_board.py BOARD.kicad_pcb [REF ...]
"""
import sys

import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
refs = set(sys.argv[2:])
mm = pcbnew.ToMM
tracks = [t for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
vias = [t for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
print(f"footprints {len(board.GetFootprints())}, tracks {len(tracks)}, vias {len(vias)}, zones {len(list(board.Zones()))}, "
      f"copper layers {board.GetCopperLayerCount()}")
bb = board.GetBoardEdgesBoundingBox()
print(f"edge bbox ({mm(bb.GetX()):.2f},{mm(bb.GetY()):.2f})-({mm(bb.GetRight()):.2f},{mm(bb.GetBottom()):.2f})")
print('\n--- Edge.Cuts shapes ---')
for d in board.GetDrawings():
    if isinstance(d, pcbnew.PCB_SHAPE) and d.GetLayer() == pcbnew.Edge_Cuts:
        b = d.GetBoundingBox()
        print(f"  {d.ShowShape()} ({mm(b.GetX()):.3f},{mm(b.GetY()):.3f})-({mm(b.GetRight()):.3f},{mm(b.GetBottom()):.3f})")
print('\n--- zones ---')
for z in board.Zones():
    b = z.GetBoundingBox()
    layers = ','.join(board.GetLayerName(l) for l in z.GetLayerSet().Seq())
    kind = 'RULE_AREA' if z.GetIsRuleArea() else 'ZONE'
    filled = ''
    if not z.GetIsRuleArea():
        try:
            area = 0.0
            for l in z.GetLayerSet().Seq():
                area += z.GetFilledPolysList(l).Area() / 1e12
            filled = f" filled_mm2={area:.0f}"
        except Exception:  # noqa: BLE001
            pass
    print(f"  {kind:9s} {z.GetZoneName() or '':22s} [{z.GetNetname() or '-':9s}] {layers:28s} prio={z.GetAssignedPriority()} "
          f"clr={mm(z.GetLocalClearance()):.2f} bbox=({mm(b.GetX()):.1f},{mm(b.GetY()):.1f})-({mm(b.GetRight()):.1f},{mm(b.GetBottom()):.1f}){filled}")
print('\n--- footprints ---')
for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
    p = fp.GetPosition()
    flag = '*' if fp.GetReference() in refs else ' '
    cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd).BBox()
    print(f" {flag}{fp.GetReference():5s} {str(fp.GetFPID().GetLibItemName()):40s} ({mm(p.x):7.3f},{mm(p.y):7.3f}) rot={fp.GetOrientationDegrees():5.1f} "
          f"side={'B' if fp.IsFlipped() else 'F'} crt=({mm(cy.GetX()):.1f},{mm(cy.GetY()):.1f})-({mm(cy.GetRight()):.1f},{mm(cy.GetBottom()):.1f})")
    if fp.GetReference() in refs:
        for pad in fp.Pads():
            pp = pad.GetPosition()
            attr = {pcbnew.PAD_ATTRIB_PTH: 'PTH', pcbnew.PAD_ATTRIB_NPTH: 'NPTH', pcbnew.PAD_ATTRIB_SMD: 'SMD', pcbnew.PAD_ATTRIB_CONN: 'CONN'}.get(pad.GetAttribute(), '?')
            print(f"        pad {pad.GetNumber():4s} [{pad.GetNetname() or '-':14s}] {attr:4s} ({mm(pp.x):7.3f},{mm(pp.y):7.3f}) "
                  f"size {mm(pad.GetSize().x):.2f}x{mm(pad.GetSize().y):.2f} drill {mm(pad.GetDrillSize().x):.2f}x{mm(pad.GetDrillSize().y):.2f}")
