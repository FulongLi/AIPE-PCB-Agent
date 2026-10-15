"""Reserve a pad escape by cutting obstructing tracks, never pads or vias.

Candidate geometry is checked against real pad rectangles and existing vias.
Interrupted tracks retain their outside portions and must be reconnected by
native-component routing, then checked by native DRC. No rule is relaxed.
"""
import math
from automation.kicad_tools.grid_router import point_segment_distance
from automation.kicad_tools.project_board import box_distance

def reserve_escape(builder,ref,pin,candidates,*,width=.2,diameter=.6,drill=.3,clearance=.2,pair_clearance=None,protected_nets=()):
    b=builder;pcb=b.pcb;pad=b.pad(ref,pin);net=pad.GetNetname();start=b.xy(ref,pin);layer=pad.GetLayer()
    records=b.pads();vias=[t for t in b.board.GetTracks() if isinstance(t,pcb.PCB_VIA)]
    drilled=[p for f in b.board.GetFootprints() for p in f.Pads() if max(p.GetDrillSize().x,p.GetDrillSize().y)>0]
    best=None
    def dist(p,a,z):return point_segment_distance(*p,*a,*z)
    for end in candidates:
        stub=[min(start[0],end[0]),min(start[1],end[1]),max(start[0],end[0]),max(start[1],end[1])]
        point=[*end,*end];valid=True
        for p in records:
            if not p['net'] or p['net']==net:continue
            gap,across=pair_clearance(net,p['net']) if pair_clearance else (clearance,False)
            if box_distance(point,p['box'])<diameter/2+gap+.01:valid=False;break
            if (across or b.board.GetLayerName(layer) in p['layers']) and box_distance(stub,p['box'])<width/2+gap+.01:valid=False;break
        if not valid:continue
        for p in drilled:
            radius=pcb.ToMM(max(p.GetDrillSize().x,p.GetDrillSize().y))/2
            if math.dist(end,pcb.ToMM(p.GetPosition()))<drill/2+radius+.25+.01:valid=False;break
        if not valid:continue
        for v in vias:
            xy=pcb.ToMM(v.GetPosition());rad=pcb.ToMM(v.GetWidth(pcb.F_Cu))/2
            gap,_=pair_clearance(net,v.GetNetname()) if pair_clearance else (clearance,False)
            if v.GetNetname()!=net and (math.dist(end,xy)<diameter/2+rad+gap+.01 or dist(xy,start,end)<width/2+rad+gap+.01):valid=False;break
            if math.dist(end,xy)<drill/2+pcb.ToMM(v.GetDrillValue())/2+.25+.01:valid=False;break
        if not valid:continue
        cuts=[];cost=math.dist(start,end)
        for t in b.board.GetTracks():
            if isinstance(t,pcb.PCB_VIA) or t.GetNetname()==net:continue
            if isinstance(t,pcb.PCB_ARC):raise ValueError('Reserve escapes before arc beautification')
            a,z=pcb.ToMM(t.GetStart()),pcb.ToMM(t.GetEnd());radius=pcb.ToMM(t.GetWidth())/2
            gap,across=pair_clearance(net,t.GetNetname()) if pair_clearance else (clearance,False)
            count=max(1,math.ceil(math.dist(a,z)/.08));hit=[]
            for i in range(count+1):
                f=i/count;q=(a[0]+(z[0]-a[0])*f,a[1]+(z[1]-a[1])*f)
                if math.dist(q,end)<radius+diameter/2+gap+.05 or ((across or t.GetLayer()==layer) and dist(q,start,end)<radius+width/2+gap+.05):hit.append(i)
            if hit:
                if t.GetNetname() in protected_nets:valid=False;break
                lo=max(0,(min(hit)-1)/count);hi=min(1,(max(hit)+1)/count)
                cuts.append((t,a,z,lo,hi));cost+=1+(hi-lo)*math.dist(a,z)
        if not valid:continue
        candidate=(cost,tuple(end),cuts)
        if best is None or candidate[:2]<best[:2]:best=candidate
    if best is None:return dict(ref=ref,pin=pin,net=net,status='no_pad_via_safe_candidate')
    _,end,cuts=best;retained=getattr(b,'_detached',[]);b._detached=retained;cut_nets=[]
    for t,a,z,lo,hi in cuts:
        n=t.GetNetname();w=pcb.ToMM(t.GetWidth());lay=b.board.GetLayerName(t.GetLayer());cut_nets.append(n)
        retained.append(t);b.board.Remove(t)
        at=lambda f:(a[0]+(z[0]-a[0])*f,a[1]+(z[1]-a[1])*f)
        if lo>0:b.track(n,[a,at(lo)],w,lay)
        if hi<1:b.track(n,[at(hi),z],w,lay)
    b.track(net,[start,end],width,b.board.GetLayerName(layer));b.via(net,end,diameter,drill)
    return dict(ref=ref,pin=pin,net=net,status='escape_reserved',via=end,cut_nets=sorted(set(cut_nets)),cut_segments=len(cuts))
