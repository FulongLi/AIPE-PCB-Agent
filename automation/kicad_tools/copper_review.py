"""Filled-copper evidence, projected insulation and reference-plane coverage.

This is geometric screening, not a field solver or a creepage certification.
Native filled polygons, including their holes, are required as inputs.
"""
import math
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union,nearest_points


def geometry(records):
    return unary_union([Polygon(p['shell'],p['holes']).buffer(0) for r in records for p in r['polygons']])


def arc_points(a,m,b):
    if m is None:return [a,b]
    ax,ay=a;mx,my=m;bx,by=b
    div=2*(ax*(my-by)+mx*(by-ay)+bx*(ay-my))
    if abs(div)<1e-12:return [a,m,b]
    ux=((ax*ax+ay*ay)*(my-by)+(mx*mx+my*my)*(by-ay)+(bx*bx+by*by)*(ay-my))/div
    uy=((ax*ax+ay*ay)*(bx-mx)+(mx*mx+my*my)*(ax-bx)+(bx*bx+by*by)*(mx-ax))/div
    angle=lambda p:math.atan2(p[1]-uy,p[0]-ux)
    start,mid,end=map(angle,[a,m,b]);sweep=(end-start)%(2*math.pi)
    if (mid-start)%(2*math.pi)>sweep:sweep-=2*math.pi
    radius=math.dist(a,(ux,uy));n=max(2,math.ceil(abs(sweep)*radius/.025))
    return [[ux+radius*math.cos(start+sweep*i/n),uy+radius*math.sin(start+sweep*i/n)] for i in range(n+1)]


def reference_coverage(records,nets,reference='GND_CTRL',layer='In1.Cu'):
    plane=geometry([r for r in records if r['net']==reference and r['layer']==layer]);out=[]
    returns={r['uuid']:r for r in records if r['net']==reference and r.get('through',False)}
    for net in nets:
        paths=[r for r in records if r['net']==net and r['kind']=='track'];total=gap=0.;segments=[]
        for r in paths:
            line=LineString(arc_points(r['start'],r.get('mid'),r['end']));missing=line.difference(plane)
            total+=line.length;gap+=missing.length
            if missing.length>.01:segments.append(dict(layer=r['layer'],uuid=r['uuid'],uncovered_mm=missing.length))
        vias={r['uuid']:r for r in records if r['net']==net and r['kind']=='via'}
        return_distances=[dict(signal_via=key,xy=r['xy'],nearest_return_connection_mm=min((math.dist(r['xy'],q['xy']) for q in returns.values()),default=None)) for key,r in vias.items()]
        out.append(dict(net=net,trace_length_mm=total,reference_layer=layer,uncovered_projection_mm=gap,
                        projected_coverage=1-gap/total if total else None,via_count=len(vias),return_transitions=return_distances,uncovered_segments=segments,
                        interpretation='Uncovered projection includes the necessary antipads around signal vias. Inspect transition-to-ground distance and nearby plane holes; do not equate this metric with return-path failure.'))
    return out


def barrier(records,hazardous_nets):
    hv=geometry([r for r in records if r['net'] in hazardous_nets]);ctrl=geometry([r for r in records if r['net'] and r['net'] not in hazardous_nets])
    a,b=nearest_points(hv,ctrl)
    return dict(projected_all_layer_minimum_mm=hv.distance(ctrl),nearest_hazardous=list(a.coords)[0],nearest_control=list(b.coords)[0],
                criterion_mm=8.,passed=hv.distance(ctrl)>=7.999,
                limitation='Projected copper separation only; excludes solder, connector/wire motion, dielectric qualification and assembled surface creepage.')
