"""Export native copper and identify separate filled islands geometrically.

Export runs with pcbnew; analyse runs with Shapely. Unlike a zone object's
connectivity membership, individual filled polygons remain separate. This is
an inspection aid; native DRC remains authoritative. Pad lands are exported
without drill subtraction, so this representation is not a copper-loss mesh.
"""
import argparse,json,hashlib
from pathlib import Path


def export(board_path,output,nets):
    import pcbnew as p
    b=p.LoadBoard(str(Path(board_path).resolve()));layers=list(b.GetEnabledLayers().CuStack());records=[]
    def rings(poly):
        points=lambda chain:[list(p.ToMM(chain.CPoint(k))) for k in range(chain.PointCount())]
        return [dict(shell=points(poly.COutline(i)),holes=[points(poly.CHole(i,h)) for h in range(poly.HoleCount(i))]) for i in range(poly.OutlineCount())]
    for item in [q for f in b.GetFootprints() for q in f.Pads()]+list(b.GetTracks())+list(b.Zones()):
        net=item.GetNetname()
        if net not in nets:continue
        via=isinstance(item,p.PCB_VIA);pad=isinstance(item,p.PAD);zone=isinstance(item,p.ZONE)
        through=via or pad and item.GetAttribute()==p.PAD_ATTRIB_PTH
        for layer in layers:
            if not item.IsOnLayer(layer):continue
            if zone:poly=item.GetFilledPolysList(layer)
            else:
                poly=p.SHAPE_POLY_SET();item.TransformShapeToPolygon(poly,layer,0,p.FromMM(.002),p.ERROR_INSIDE)
            rr=rings(poly)
            if rr:records.append(dict(net=net,layer=b.GetLayerName(layer),uuid=item.m_Uuid.AsString(),kind='zone' if zone else 'pad' if pad else 'via' if via else 'track',
                ref=item.GetParentFootprint().GetReference() if pad else '',pin=item.GetNumber() if pad else '',through=through,xy=list(p.ToMM(item.GetPosition())) if through or pad else None,
                drill_mm=list(p.ToMM(item.GetDrillSize())) if pad else [p.ToMM(item.GetDrillValue())]*2 if via else None,
                start=list(p.ToMM(item.GetStart())) if not pad and not zone and not via else None,
                end=list(p.ToMM(item.GetEnd())) if not pad and not zone and not via else None,
                mid=list(p.ToMM(item.GetMid())) if isinstance(item,p.PCB_ARC) else None,
                width_mm=p.ToMM(item.GetWidth(layer)) if via else p.ToMM(item.GetWidth()) if not pad and not zone else None,
                polygons=rr))
    Path(output).write_text(json.dumps(dict(board=str(board_path),sha256=hashlib.sha256(Path(board_path).read_bytes()).hexdigest(),records=records),separators=(',',':')))


def analyse(source,output):
    from shapely.geometry import Polygon,Point
    from shapely.ops import unary_union,nearest_points
    d=json.loads(Path(source).read_text());by={};items=d['records']
    for r in items:
        by.setdefault((r['net'],r['layer']),[]).extend(Polygon(v['shell'],v['holes']).buffer(0) for v in r['polygons'])
    out=[]
    for net in sorted({n for n,l in by}):
        parts=[]
        for (n,layer),shapes in by.items():
            if n!=net:continue
            geom=unary_union(shapes).buffer(.002)
            for g in geom.geoms if geom.geom_type=='MultiPolygon' else [geom]:parts.append((layer,g))
        parent=list(range(len(parts)))
        def find(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        def union(i,j):parent[find(i)]=find(j)
        for r in items:
            if r['net']!=net or not r['through']:continue
            pt=Point(r['xy']);hit=[i for i,(layer,g) in enumerate(parts) if g.covers(pt)]
            for i in hit[1:]:union(hit[0],i)
        groups={}
        for i,(layer,g) in enumerate(parts):groups.setdefault(find(i),[]).append((layer,g))
        comps=[]
        for seq in groups.values():
            pads=[]
            for r in items:
                if r['net']!=net or r['kind']!='pad':continue
                if any(layer==r['layer'] and g.covers(Point(r['xy'])) for layer,g in seq):pads.append([r['ref'],r['pin']])
            comps.append(dict(layers=sorted({l for l,g in seq}),pads=sorted({tuple(x) for x in pads}),bounds=unary_union([g for l,g in seq]).bounds,area_mm2=sum(g.area for l,g in seq)))
        seqs=list(groups.values());links=[]
        for i,aa in enumerate(seqs):
            best=None
            for j,bb in enumerate(seqs):
                if j==i:continue
                for la,a in aa:
                    for lb,b in bb:
                        if la!=lb:continue
                        dist=a.distance(b)
                        if best is None or dist<best[0]:
                            x,y=nearest_points(a,b);best=(dist,j,la,list(x.coords)[0],list(y.coords)[0])
            if best:links.append(dict(component=i,distance_mm=best[0],to=best[1],layer=best[2],a=best[3],b=best[4]))
        out.append(dict(net=net,component_count=len(comps),components=comps,nearest=links))
    Path(output).write_text(json.dumps(dict(board_sha256=d['sha256'],nets=out),indent=2)+'\n')
    print([(x['net'],x['component_count']) for x in out])


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['export','analyse']);ap.add_argument('source');ap.add_argument('output');ap.add_argument('--nets',nargs='+',default=['PGND','VEE_L','BUS','SW','VOUT','RAW']);a=ap.parse_args()
    if a.stage=='export':export(a.source,a.output,a.nets)
    else:analyse(a.source,a.output)
