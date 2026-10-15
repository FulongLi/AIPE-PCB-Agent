"""Reserve a pad escape by cutting obstructing tracks, never pads.

Candidate geometry is checked against real pad rectangles and existing vias.
Vias may be removed only from explicitly allowed nets. Interrupted tracks retain their outside portions and must be reconnected by
native-component routing, then checked by native DRC. No rule is relaxed.
"""
import math
from automation.kicad_tools.grid_router import point_segment_distance
from automation.kicad_tools.project_board import box_distance,segment_box_distance

def reserve_escape(builder,ref,pin,candidates,*,width=.2,diameter=.6,drill=.3,clearance=.2,pair_clearance=None,protected_nets=(),protected_item_ids=(),removable_via_nets=(),add_via=True,diagnostics=False,layer=None):
    b=builder;pcb=b.pcb;pad=b.pad(ref,pin);net=pad.GetNetname();start=b.xy(ref,pin);layer=pad.GetLayer() if layer is None else b.layer(layer)
    if not pad.IsOnLayer(layer):raise ValueError('Escape layer must contain the starting pad')
    records=b.pads();vias=[t for t in b.board.GetTracks() if isinstance(t,pcb.PCB_VIA)]
    drilled=[p for f in b.board.GetFootprints() for p in f.Pads() if max(p.GetDrillSize().x,p.GetDrillSize().y)>0]
    best=None;rejections=[]
    def reject(reason,**details):
        if diagnostics:rejections.append(dict(reason=reason,**details))
    def dist(p,a,z):return point_segment_distance(*p,*a,*z)
    for candidate_path in candidates:
        # Legacy candidates are end points; explicit waypoint lists allow a
        #straight lead-row exit followed by a dogleg outside adjacent pads.
        path=[start,*candidate_path] if isinstance(candidate_path[0],(tuple,list)) else [start,candidate_path]
        end=path[-1]
        point=[*end,*end];valid=True
        for p in records:
            if not p['net'] or p['net']==net:continue
            gap,across=pair_clearance(net,p['net']) if pair_clearance else (clearance,False)
            if add_via and box_distance(point,p['box'])<diameter/2+gap+.01:reject('via_to_pad',ref=p['ref'],net=p['net'],box=p['box']);valid=False;break
            if (across or b.board.GetLayerName(layer) in p['layers']) and any(segment_box_distance(a,z,*p['box'])<width/2+gap+.01 for a,z in zip(path,path[1:])):reject('path_to_pad',ref=p['ref'],net=p['net'],box=p['box']);valid=False;break
        if not valid:continue
        for p in drilled if add_via else []:
            radius=pcb.ToMM(max(p.GetDrillSize().x,p.GetDrillSize().y))/2
            if math.dist(end,pcb.ToMM(p.GetPosition()))<drill/2+radius+.25+.01:reject('drilled_pad',ref=p.GetParentFootprint().GetReference(),pin=p.GetNumber());valid=False;break
        if not valid:continue
        removed_vias=[]
        for v in vias:
            xy=pcb.ToMM(v.GetPosition());rad=pcb.ToMM(v.GetWidth(pcb.F_Cu))/2
            gap,_=pair_clearance(net,v.GetNetname()) if pair_clearance else (clearance,False)
            conflict=v.GetNetname()!=net and ((add_via and math.dist(end,xy)<diameter/2+rad+gap+.01) or min(dist(xy,a,z) for a,z in zip(path,path[1:]))<width/2+rad+gap+.01)
            conflict |= add_via and math.dist(end,xy)<drill/2+pcb.ToMM(v.GetDrillValue())/2+.25+.01
            if conflict:
                if v.GetNetname()!=net and v.GetNetname() in removable_via_nets and v.m_Uuid.AsString() not in protected_item_ids:removed_vias.append(v)
                else:reject('via',net=v.GetNetname(),xy=xy);valid=False;break
        if not valid:continue
        cuts=[];cost=sum(math.dist(a,z) for a,z in zip(path,path[1:]))+5*len(removed_vias)
        for t in b.board.GetTracks():
            if isinstance(t,pcb.PCB_VIA) or t.GetNetname()==net:continue
            if isinstance(t,pcb.PCB_ARC):raise ValueError('Reserve escapes before arc beautification')
            a,z=pcb.ToMM(t.GetStart()),pcb.ToMM(t.GetEnd());radius=pcb.ToMM(t.GetWidth())/2
            gap,across=pair_clearance(net,t.GetNetname()) if pair_clearance else (clearance,False)
            count=max(1,math.ceil(math.dist(a,z)/.08));hit=[]
            for i in range(count+1):
                f=i/count;q=(a[0]+(z[0]-a[0])*f,a[1]+(z[1]-a[1])*f)
                if (add_via and math.dist(q,end)<radius+diameter/2+gap+.01) or ((across or t.GetLayer()==layer) and min(dist(q,a,z) for a,z in zip(path,path[1:]))<radius+width/2+gap+.01):hit.append(i)
            if hit:
                if t.GetNetname() in protected_nets or t.m_Uuid.AsString() in protected_item_ids:reject('protected_track',net=t.GetNetname(),a=a,b=z);valid=False;break
                lo=max(0,(min(hit)-1)/count);hi=min(1,(max(hit)+1)/count)
                cuts.append((t,a,z,lo,hi));cost+=1+(hi-lo)*math.dist(a,z)
        if not valid:continue
        candidate=(cost,tuple(end),cuts,path,removed_vias)
        if best is None or candidate[:2]<best[:2]:best=candidate
    if best is None:return dict(ref=ref,pin=pin,net=net,status='no_pad_via_safe_candidate',**({'rejections':rejections[:8]} if diagnostics else {}))
    _,end,cuts,path,removed_vias=best;retained=getattr(b,'_detached',[]);b._detached=retained;cut_nets=[]
    via_records=[dict(net=v.GetNetname(),xy=pcb.ToMM(v.GetPosition())) for v in removed_vias]
    for v in removed_vias:retained.append(v);b.board.Remove(v)
    for t,a,z,lo,hi in cuts:
        n=t.GetNetname();w=pcb.ToMM(t.GetWidth());lay=b.board.GetLayerName(t.GetLayer());cut_nets.append(n)
        retained.append(t);b.board.Remove(t)
        at=lambda f:(a[0]+(z[0]-a[0])*f,a[1]+(z[1]-a[1])*f)
        if lo>0:b.track(n,[a,at(lo)],w,lay)
        if hi<1:b.track(n,[at(hi),z],w,lay)
    b.track(net,path,width,b.board.GetLayerName(layer))
    if add_via:b.via(net,end,diameter,drill)
    return dict(ref=ref,pin=pin,net=net,status='escape_reserved',via=end if add_via else None,path=path,cut_nets=sorted(set(cut_nets)),cut_segments=len(cuts),removed_vias=via_records)
