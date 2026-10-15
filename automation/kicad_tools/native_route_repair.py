"""Connect native DRC opens using real connected components as routing anchors.

Does not suppress findings or change rules. Zones are temporarily omitted to
avoid treating separate filled islands as one connected object. Refill and
native DRC are mandatory afterwards.
"""
import itertools
import math
from automation.kicad_tools.grid_router import Router


def prune_unanchored_signal_islands(board):
    """Remove copper components with no pad and no same-net plane intent.

    These are remnants of local rip-up, not unfinished pad escapes. Plane
    nets are excluded so intentional stitching vias remain. Retain returned
    SWIG wrappers until after the board has been saved.
    """
    import pcbnew as pcb
    zones=list(board.Zones());plane_nets={z.GetNetname() for z in zones}
    for z in zones:board.Remove(z)
    board.BuildConnectivity();c=board.GetConnectivity();seen=set();removed=[]
    for item in list(board.GetTracks()):
        if item.GetNetname() in plane_nets or item.m_Uuid.AsString() in seen:continue
        comp=list(c.GetConnectedItems(item));seen.update(v.m_Uuid.AsString() for v in comp)
        if any(isinstance(v,pcb.PAD) for v in comp):continue
        for v in comp:
            if v.Type()==pcb.PCB_VIA_T:v=pcb.Cast_to_PCB_VIA(v)
            if isinstance(v,pcb.PCB_TRACK):removed.append(v)
    for v in removed:board.Remove(v)
    for z in zones:board.Add(z)
    return removed,zones


def prune_native_dangling(board,report,*,vias=False):
    """Remove only native-reported dangling items; return retained wrappers.

    Refill/recheck after every pass. The caller must retain returned objects
    through save because of KiCad's SWIG object-lifetime requirements.
    """
    kinds={'track_dangling','via_dangling'} if vias else {'track_dangling'}
    ids={i['uuid'] for issue in report.get('violations',[]) if issue['type'] in kinds for i in issue['items']}
    retained=[t for t in board.GetTracks() if t.m_Uuid.AsString() in ids]
    for t in retained:board.Remove(t)
    return retained


def connect_opens(board,report,*,width_mm,height_mm,layers,grid=.125,trace=.2,clearance=.2,via=(.6,.3),max_nodes=150000,max_tries=18,progress=None,net_rules=None,pair_clearance=None,skip_nets=(),allowed_layers=None,style_eps=.02,origin=(0.,0.)):
    import pcbnew as pcb
    from automation.kicad_tools.pairwise_router import PairwiseRouter
    router_type=PairwiseRouter if pair_clearance else Router
    extra={'pair_clearance':pair_clearance} if pair_clearance else {}
    r=router_type(board,width_mm,height_mm,layers,grid=grid,trace=trace,clearance=clearance,via=via,net_rules=net_rules,origin=origin,**extra,
        style=dict(diagonal=True,eps=style_eps,via_cost_cells=20),max_nodes=max_nodes)
    r.stage='retry'
    # GetConnectedItems traverses a ZONE as one object even when its filled
    # polygons are disjoint. Native DRC does distinguish those islands.
    # Route between solid tracks/pads/vias only, then restore/refill zones.
    retained_zones=list(board.Zones())
    for zone in retained_zones:board.Remove(zone)
    items={i.m_Uuid.AsString():i for i in list(board.GetTracks())+[p for f in board.GetFootprints() for p in f.Pads()]+list(board.Zones())}
    results=[]
    def ports(component):
        pts=set()
        for item in component:
            # Connectivity returns a PCB_TRACK wrapper for native PCB_VIA
            # objects in KiCad 10. Preserve the physical through-layer port.
            if item.Type()==pcb.PCB_VIA_T:item=pcb.Cast_to_PCB_VIA(item)
            if isinstance(item,pcb.ZONE):continue
            if isinstance(item,pcb.PCB_VIA):pts.add((*r.to_grid(*pcb.ToMM(item.GetPosition())),None))
            elif isinstance(item,pcb.PAD):
                on=[l for l,layer in enumerate(r.layers) if item.IsOnLayer(layer)]
                if not on:continue
                lay=None if item.GetAttribute()==pcb.PAD_ATTRIB_PTH else on[0]
                x,y=pcb.ToMM(item.GetPosition());pts.add((*r.to_grid(x,y),lay))
                # All pad edge points remain inside the actual land; no
                #unscreened stub is emitted just to reach a grid cell.
                box=item.GetBoundingBox();x0,y0,x1,y1=[pcb.ToMM(v) for v in (box.GetX(),box.GetY(),box.GetRight(),box.GetBottom())]
                for px,py in [(x0+.15,y),(x1-.15,y),(x,y0+.15),(x,y1-.15)]:pts.add((*r.to_grid(px,py),lay))
            elif item.GetLayer() in r.layers:
                lay=r.layers.index(item.GetLayer())
                pts.add((*r.to_grid(*pcb.ToMM(item.GetStart())),lay));pts.add((*r.to_grid(*pcb.ToMM(item.GetEnd())),lay))
        return sorted(pts,key=lambda v:(v[0],v[1],-1 if v[2] is None else v[2]))
    for i,issue in enumerate(report.get('unconnected_items',[])):
        a,b=[items.get(q['uuid']) for q in issue['items'][:2]]
        if a is None or b is None:results.append(dict(index=i,status='missing_item'));continue
        net=a.GetNetname()
        if not net or b.GetNetname()!=net:results.append(dict(index=i,status='net_mismatch'));continue
        if net in skip_nets:results.append(dict(index=i,net=net,status='deferred'));continue
        if pair_clearance:r.refresh_pair_masks()
        board.BuildConnectivity();c=board.GetConnectivity()
        ca=list(c.GetConnectedItems(a));cb=list(c.GetConnectedItems(b))
        if {v.m_Uuid.AsString() for v in ca}&{v.m_Uuid.AsString() for v in cb}:
            results.append(dict(index=i,net=net,status='already_connected'));continue
        aa,bb=ports(ca),ports(cb)
        pairs=sorted(itertools.product(aa,bb),key=lambda z:(int(z[0][2] is not None)+int(z[1][2] is not None),abs(z[0][0]-z[1][0])+abs(z[0][1]-z[1][1])))
        done=False
        # Prioritise diverse launch/landing anchors, not dozens of nearly
        #identical short segments around the same closed pocket.
        tested=set();tried=0
        for start,end in pairs:
            key=(start[0]//4,start[1]//4,start[2],end[0]//4,end[1]//4,end[2])
            if key in tested:continue
            tested.add(key);tried+=1
            route_layers=allowed_layers(net) if allowed_layers else tuple(range(r.nl))
            path=r.astar(start,end,net,layers=route_layers)
            if path is not None:r.emit(path,net);done=True;break
            if tried>=max_tries:break
        results.append(dict(index=i,net=net,status='connected_proposal' if done else 'unresolved',tries=tried))
        print('native open',i,net,results[-1]['status'],flush=True)
        if progress is not None:progress(dict(results=results,router=r.report()))
    for zone in retained_zones:board.Add(zone)
    return dict(results=results,router=r.report())
