"""Axis-aligned assembly-envelope screening, with explicit contact intent.

This is a dimensional reservation check. It cannot validate curved surfaces,
terminal insulation, deformation, cable movement or assembly tolerances.
"""
import itertools,math


def bounds(part):
    return ([c-s/2 for c,s in zip(part['centre_mm'],part['size_mm'])],
            [c+s/2 for c,s in zip(part['centre_mm'],part['size_mm'])])


def compare(a,b):
    lo,hi=bounds(a);llo,hhi=bounds(b)
    overlap=[min(x,y)-max(u,v) for x,y,u,v in zip(hi,hhi,lo,llo)]
    gaps=[max(0,-d) for d in overlap]
    return dict(a=a['name'],b=b['name'],minimum_distance_mm=math.sqrt(sum(g*g for g in gaps)),
                overlap_mm=overlap,interference_volume_mm3=math.prod(overlap) if min(overlap)>1e-8 else 0.)


def screen(parts,contact_intent=None):
    contact_intent=contact_intent or {};pairs=[compare(a,b) for a,b in itertools.combinations(parts,2)]
    intersections=[]
    for pair in pairs:
        if pair['interference_volume_mm3']<=0:continue
        pair['contact_intent']=contact_intent.get(frozenset((pair['a'],pair['b'])))
        intersections.append(pair)
    return dict(pair_count=len(pairs),intersections=intersections,
                unexplained_intersections=[p for p in intersections if not p['contact_intent']],
                qualification='Envelope screening only; not a mechanical-fit or electrical-insulation approval')
