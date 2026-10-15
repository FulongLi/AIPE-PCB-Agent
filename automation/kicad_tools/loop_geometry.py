"""Ordered 3-D current-loop proxies, explicitly not inductance extraction."""
from __future__ import annotations
import math


def analyse_loop(sections):
    """Sections carry role=copper/component and ordered XYZ points in mm.

    The complete path must close, including device/capacitor terminal bridges.
    Component bridges are geometric placeholders, never internal package paths.
    Vector area is a signed projection proxy; self-crossing paths can cancel.
    """
    if not sections:raise ValueError('Empty loop')
    pts=[];lengths={'copper':0.,'component':0.};transitions=0
    for s in sections:
        path=[tuple(map(float,p)) for p in s['points']]
        if len(path)<2 or any(len(p)!=3 for p in path):raise ValueError('A section needs at least two XYZ points')
        if pts and math.dist(pts[-1],path[0])>1e-5:raise ValueError('Disconnected loop sections')
        role=s.get('role','copper')
        if role not in lengths:raise ValueError(role)
        lengths[role]+=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
        if role=='copper':transitions+=sum(abs(a[2]-b[2])>1e-6 for a,b in zip(path,path[1:]))
        pts.extend(path if not pts else path[1:])
    if math.dist(pts[0],pts[-1])>1e-5:raise ValueError('Loop is not closed')
    area=[0.,0.,0.]
    for a,b in zip(pts,pts[1:]):
        area[0]+=(a[1]*b[2]-a[2]*b[1])/2
        area[1]+=(a[2]*b[0]-a[0]*b[2])/2
        area[2]+=(a[0]*b[1]-a[1]*b[0])/2
    return dict(external_copper_length_mm=lengths['copper'],terminal_bridge_length_mm=lengths['component'],
        closed_proxy_length_mm=sum(lengths.values()),copper_z_transitions=transitions,
        signed_vector_area_mm2=area,projected_xy_area_mm2=abs(area[2]),
        vector_area_magnitude_mm2=math.sqrt(sum(x*x for x in area)),
        scope='Geometric proxy. Device/capacitor internals replaced by terminal bridges; vector area may cancel at crossings. No nH or field solution.')


def offset_pair_coverage(forward,return_path,*,distance_mm=1.,sample_mm=.2):
    """Fraction of forward XY length close to a specified return centreline."""
    from automation.kicad_tools.grid_router import point_segment_distance
    total=near=0.
    for a,b in zip(forward,forward[1:]):
        length=math.dist(a,b)
        if not length:continue
        count=max(1,math.ceil(length/sample_mm));ds=length/count
        for k in range(count):
            f=(k+.5)/count;x=a[0]+f*(b[0]-a[0]);y=a[1]+f*(b[1]-a[1])
            distance=min(point_segment_distance(x,y,*r[:2],*s[:2]) for r,s in zip(return_path,return_path[1:]))
            total+=ds
            if distance<=distance_mm:near+=ds
    return dict(distance_mm=distance_mm,covered_fraction=near/total if total else None,sampled_length_mm=total,
        scope='XY centreline proximity only; not proof of a continuous copper return or magnetic coupling')
