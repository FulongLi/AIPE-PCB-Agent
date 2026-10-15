"""Propose through stitches near SMT pads using actual native filled copper.

Preserves the caller's voltage-domain masks and avoids via-in-pad assembly.
Refill and native DRC remain mandatory after these proposals.
"""
import math
from automation.kicad_tools.project_board import box_distance


def stitch_pads(builder,router,nets,*,radius=2.5,max_per_net=40):
    b=builder;r=router;pcb=b.pcb;pads=b.pads();records=[]
    zones={n:[] for n in nets}
    for z in b.board.Zones():
        n=z.GetNetname()
        if n not in zones:continue
        for layer in r.layers:
            if z.IsOnLayer(layer):zones[n].append((layer,z.GetFilledPolysList(layer)))
    def filled(n,xy):
        point=pcb.VECTOR2I(pcb.FromMM(xy[0]),pcb.FromMM(xy[1]))
        return {layer for layer,poly in zones[n] if poly.Contains(point)}
    for net in nets:
        count=0
        for p in pads:
            if p['net']!=net or len(p['layers'])!=1:continue
            layer=b.board.GetLayerID(p['layers'][0]);x,y=p['xy']
            candidates=[]
            for dx in range(-int(radius/.25),int(radius/.25)+1):
                for dy in range(-int(radius/.25),int(radius/.25)+1):
                    if math.hypot(dx,dy)*.25>radius:continue
                    xy=(round((x+dx*.25)/r.grid.grid)*r.grid.grid,round((y+dy*.25)/r.grid.grid)*r.grid.grid)
                    layers=filled(net,xy)
                    if layer not in layers or len(layers)<2:continue
                    point=[*xy,*xy]
                    if any(q['net']==net and box_distance(point,q['box'])<r.via_d/2+.2 for q in pads):continue
                    gx,gy=r.to_grid(*xy)
                    if r.existing_transition(xy,net) or not r.via_allowed(gx,gy,net):continue
                    candidates.append((math.dist(xy,(x,y)),xy))
            if not candidates:continue
            _,xy=min(candidates);r.via(xy,net);count+=1
            records.append(dict(net=net,near=[p['ref'],p['pin']],xy=xy))
            if count>=max_per_net:break
        if hasattr(r,'refresh_pair_masks'):r.refresh_pair_masks()
    return records
