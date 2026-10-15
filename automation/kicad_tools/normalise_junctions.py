"""Make same-net track/via junctions explicit before pruning native tails.

A native dangling finding can describe a long segment that also crosses a
useful branch. Deleting the entire reported segment can open that branch.
Split at actual centreline junctions first, and replace reliance on a via's
annulus edge with a short connection to its centre. Native DRC is mandatory.
No net, footprint, rule or zone is changed. Arc inputs are rejected.
"""
import math


def projection(q,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];ll=dx*dx+dy*dy
    t=max(0.,min(1.,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/ll)) if ll else 0.
    return t,(a[0]+t*dx,a[1]+t*dy)


def intersection(a,b,c,d):
    x,y=b[0]-a[0],b[1]-a[1];u,v=d[0]-c[0],d[1]-c[1];det=x*v-y*u
    if abs(det)<1e-12:return None
    t=((c[0]-a[0])*v-(c[1]-a[1])*u)/det
    s=((c[0]-a[0])*y-(c[1]-a[1])*x)/det
    return (t,(a[0]+t*x,a[1]+t*y)) if -.000001<=t<=1.000001 and -.000001<=s<=1.000001 else None


def normalise(builder,report):
    b=builder;p=b.pcb
    warnings={q['uuid'] for r in report['violations'] if r['type'] in ['track_dangling','via_dangling'] for q in r['items']}
    tracks=[];vias=[]
    for t in b.board.GetTracks():
        if isinstance(t,p.PCB_ARC):raise ValueError('Normalise straight tracks before arc beautification')
        if isinstance(t,p.PCB_VIA):vias.append(t);continue
        tracks.append(dict(item=t,net=t.GetNetname(),layer=t.GetLayer(),a=p.ToMM(t.GetStart()),z=p.ToMM(t.GetEnd()),width=p.ToMM(t.GetWidth())))
    removed=[];joins=[];splits=0
    # Explicit landing at every overlapping via. A via connected only on
    #one layer may still have been used as a same-layer copper bridge.
    for v in vias:
        xy=p.ToMM(v.GetPosition());radius=p.ToMM(v.GetWidth(p.F_Cu))/2
        for t in tracks:
            if t['net']!=v.GetNetname():continue
            f,q=projection(xy,t['a'],t['z']);gap=math.dist(q,xy)
            if .001<gap<radius+t['width']/2-.001:
                joins.append((t['net'],[q,xy],t['width'],b.board.GetLayerName(t['layer'])))
    for t in tracks:
        if t['item'].m_Uuid.AsString() not in warnings:continue
        points={0.:t['a'],1.:t['z']}
        for q in tracks:
            if q is t or q['net']!=t['net'] or q['layer']!=t['layer']:continue
            hit=intersection(t['a'],t['z'],q['a'],q['z'])
            if hit and .000001<hit[0]<.999999:points[hit[0]]=hit[1]
            for end in [q['a'],q['z']]:
                f,xy=projection(end,t['a'],t['z']);dist=math.dist(xy,end)
                if .000001<f<.999999 and dist<(t['width']+q['width'])/2-.001:
                    points[f]=xy
                    if dist>.001:joins.append((t['net'],[end,xy],min(t['width'],q['width']),b.board.GetLayerName(t['layer'])))
        for v in vias:
            if v.GetNetname()!=t['net']:continue
            f,xy=projection(p.ToMM(v.GetPosition()),t['a'],t['z'])
            if .000001<f<.999999 and math.dist(xy,p.ToMM(v.GetPosition()))<p.ToMM(v.GetWidth(p.F_Cu))/2+t['width']/2-.001:points[f]=xy
        if len(points)>2:
            removed.append(t['item']);b.board.Remove(t['item']);splits+=1
            ordered=[xy for _,xy in sorted(points.items())]
            for a,z in zip(ordered,ordered[1:]):
                if math.dist(a,z)>.001:b.track(t['net'],[a,z],t['width'],b.board.GetLayerName(t['layer']))
    # KiCad truncates to integer nanometres. A 10 nm key prevents repeated
    #sub-nanometre projections becoming nominally identical new stubs.
    unique={(t['net'],b.board.GetLayerName(t['layer']),tuple(sorted(tuple(round(x,5) for x in q) for q in [t['a'],t['z']]))) for t in tracks}
    added=0
    for net,pts,width,layer in joins:
        key=(net,layer,tuple(sorted(tuple(round(x,5) for x in q) for q in pts)))
        if key in unique:continue
        unique.add(key);b.track(net,pts,width,layer);added+=1
    b._detached=getattr(b,'_detached',[])+removed
    return dict(split_tracks=splits,explicit_junctions=added,requires_native_drc=True)


def remove_exact_duplicates(builder):
    """Remove only coincident straight segments with identical net/width/layer."""
    b=builder;p=b.pcb;seen=set();removed=[]
    for t in list(b.board.GetTracks()):
        if isinstance(t,(p.PCB_VIA,p.PCB_ARC)):continue
        a=t.GetStart();z=t.GetEnd();key=(t.GetNetCode(),t.GetLayer(),t.GetWidth(),tuple(sorted(((a.x,a.y),(z.x,z.y)))))
        if key in seen:removed.append(t);b.board.Remove(t)
        else:seen.add(key)
    b._detached=getattr(b,'_detached',[])+removed
    return len(removed)
