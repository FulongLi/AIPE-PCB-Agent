"""Power copper proposals with an explicit all-layer control-domain moat.

Three stages: export/apply with KiCad Python; clip with host Python (Shapely).
Native fill, DRC, connectivity and actual filled-copper current screening must
follow. Outlines alone are not claimed as current-carrying cross sections.
"""
import argparse,json
from pathlib import Path

WORK=Path('.aipe/v3/power')

def export(source):
    import pcbnew as pcb
    from automation.sic_v3.routing import wrapper
    from automation.sic_v3.schematics import power_domains
    from automation.sic_v3.model import power
    b=wrapper(pcb.LoadBoard(str((WORK/f'sic-v3-power-{source}.kicad_pcb').resolve())),'power')
    tracks=[]
    for t in b.board.GetTracks():
        via=isinstance(t,pcb.PCB_VIA)
        if isinstance(t,pcb.PCB_ARC):raise ValueError('Export arc geometry before using this pipeline')
        tracks.append(dict(net=t.GetNetname(),a=pcb.ToMM(t.GetPosition() if via else t.GetStart()),b=pcb.ToMM(t.GetPosition() if via else t.GetEnd()),
            width=pcb.ToMM(t.GetWidth(pcb.F_Cu) if via else t.GetWidth()),layer=b.board.GetLayerName(t.GetLayer()),via=via))
    (WORK/'copper-input.json').write_text(json.dumps(dict(source=source,pads=b.pads(),tracks=tracks,domains=power_domains(power().parts)),indent=2)+'\n')

def clip():
    from shapely.geometry import box,LineString,Point,Polygon
    from shapely.ops import unary_union
    d=json.loads((WORK/'copper-input.json').read_text());ds=d['domains'];groups={'HV':[],'CTRL':[]}
    for p in d['pads']:
        if p['net']:groups['HV' if p['net'] in ds else 'CTRL'].append(box(*p['box']))
    for t in d['tracks']:
        if not t['net']:continue
        shape=Point(t['a']) if t['via'] else LineString([t['a'],t['b']])
        groups['HV' if t['net'] in ds else 'CTRL'].append(shape.buffer(t['width']/2,quad_segs=16))
    masks={name:unary_union(shapes).buffer(8.075,quad_segs=16) for name,shapes in groups.items()}
    specs=[]
    def rect(net,layers,bounds,priority):
        for layer in layers:specs.append((net,layer,box(*bounds),priority))
    all_layers=['F.Cu','In1.Cu','In2.Cu','B.Cu']
    # Global PGND outline is clipped out of the accessible domain on every
    #layer. Higher-priority functional islands define the actual power paths.
    rect('PGND',all_layers,[1,1,249,179],0)
    rect('BUS',['F.Cu','In2.Cu','B.Cu'],[1,12,65,136],12)
    rect('BUS',['In2.Cu'],[1,6,102,30],12)
    rect('BUS',['B.Cu'],[62,6.8,134,11],12)
    rect('BUS',['B.Cu','F.Cu'],[94.5,9,102,17],12)
    # The two inner layers carry the switch-node distribution; outer layers
    #retain short terminal landing copper. Filled necks require measurement.
    rect('SW',['In1.Cu','In2.Cu'],[103,6,162,17.5],10)
    rect('SW',['F.Cu','B.Cu'],[148,9,162,23],10)
    rect('PGND',['F.Cu'],[126,1,140,18],15)
    rect('PGND',['B.Cu'],[1,1,249,4.3],15)
    rect('RAW',['F.Cu','B.Cu'],[7,140,21,154],5)
    rect('VOUT',all_layers,[183,17,231,145],5)
    for net,bounds in [('VEE_H',[64,1,121.5,24.5]),('VEE_L',[122,1,185.5,24.5])]:rect(net,['F.Cu','B.Cu'],bounds,6)
    for tag,bounds in [('H',[65,33.3,91,51]),('L',[153,33.3,185,51]),('S',[161,122,193,139.7])]:rect('GNDP_'+tag,['F.Cu','B.Cu'],bounds,6)
    rect('GND_CTRL',['In1.Cu'],[58,32,198,141],1)
    merged={}
    for net,layer,shape,priority in specs:merged.setdefault((net,layer,priority),[]).append(shape)
    specs=[(net,layer,unary_union(shapes),priority) for (net,layer,priority),shapes in merged.items()]
    # Accessible planes are conductors too. Pad/track-only masks would let
    #HV copper overlap an otherwise empty part of a control ground plane on
    #another layer. First establish CTRL plane outlines against actual HV
    #pads/tracks, then exclude their complete projected area from HV pours.
    # Dedicated high-current regions take precedence over otherwise empty
    #control-plane area, while still respecting every actual CTRL pad and
    #track. Do not give the global PGND background this precedence.
    power_corridors=[shape.difference(masks['CTRL']) for net,layer,shape,priority in specs if net in ['BUS','SW','VOUT','RAW']]
    masks['HV']=unary_union([*groups['HV'],*power_corridors]).buffer(8.075,quad_segs=16)
    control_planes=[shape.difference(masks['HV']) for net,layer,shape,priority in specs if net not in ds]
    masks['CTRL']=unary_union([*groups['CTRL'],*control_planes]).buffer(8.075,quad_segs=16)
    out=[]
    for net,layer,shape,priority in specs:
        shape=shape.difference(masks['CTRL' if net in ds else 'HV']).simplify(.003,preserve_topology=True)
        polys=list(shape.geoms) if shape.geom_type=='MultiPolygon' else [shape] if shape.geom_type=='Polygon' else []
        for poly in polys:
            if poly.area<.25:continue
            anchors=[box(*p['box']) for p in d['pads'] if p['net']==net and layer in p['layers']]
            anchors += [Point(t['a']).buffer(t['width']/2) if t['via'] else LineString([t['a'],t['b']]).buffer(t['width']/2) for t in d['tracks'] if t['net']==net and (t['via'] or t['layer']==layer)]
            if not anchors or not poly.intersects(unary_union(anchors)):continue
            out.append(dict(net=net,layer=layer,priority=priority,outline=list(poly.exterior.coords)[:-1],holes=[list(r.coords)[:-1] for r in poly.interiors],outline_area_mm2=poly.area))
    (WORK/'copper-polygons.json').write_text(json.dumps(dict(source=d['source'],barrier_buffer_mm=8.075,zones=out),indent=2)+'\n')
    print('Clipped zone outlines',len(out))

def apply(output):
    import pcbnew as pcb
    from automation.sic_v3 import routing
    from automation.kicad_tools.grid_router import Router
    d=json.loads((WORK/'copper-polygons.json').read_text());routing.WORK=WORK
    b=routing.wrapper(pcb.LoadBoard(str((WORK/f"sic-v3-power-{d['source']}.kicad_pcb").resolve())),'power');b._detached=[]
    # Rebuild the outlines from current routed copper; old masks must not
    #survive a re-clip and silently bridge a newly routed isolation moat.
    for z in list(b.board.Zones()):b._detached.append(z);b.board.Remove(z)
    # Remove the redundant same-net header via and the sub-pad neck flagged
    #by native DRC. Keep adjacent legal copper; reconnect if DRC requests it.
    for t in list(b.board.GetTracks()):
        via=isinstance(t,pcb.PCB_VIA);xy=pcb.ToMM(t.GetPosition())
        bad_header_via=via and t.GetNetname()=='PG_H_N' and __import__('math').dist(xy,(115.375,109.5))<.01
        redundant_neck=not via and t.GetNetname()=='VEE_L' and pcb.ToMM(t.GetLength())<.13 and __import__('math').dist(pcb.ToMM(t.GetStart()),(167.625,23))<.01
        if bad_header_via or redundant_neck:
            b._detached.append(t);b.board.Remove(t)
    r=Router(b.board,250,180,['F.Cu','In1.Cu','In2.Cu','B.Cu'],grid=.125,trace=.25,clearance=.25,via=(.8,.4))
    for z in d['zones']:r.zone(z['net'],z['layer'],z['outline'],priority=z['priority'],clearance=.25,min_thickness=.25,keepout_hole_polygons=z['holes'])
    routing.save(b,output,d)

def stitch(source,output):
    import pcbnew as pcb
    from automation.sic_v3 import routing
    from automation.sic_v3.schematics import power_domains
    from automation.sic_v3.model import power
    from automation.sic_v3.floorplan import pair_gap
    from automation.kicad_tools.pairwise_router import PairwiseRouter
    from automation.kicad_tools.plane_stitching import stitch_pads
    routing.WORK=WORK;b=routing.wrapper(pcb.LoadBoard(str((WORK/f'sic-v3-power-{source}.kicad_pcb').resolve())),'power');ds=power_domains(power().parts)
    r=PairwiseRouter(b.board,250,180,['F.Cu','In1.Cu','In2.Cu','B.Cu'],grid=.125,trace=.25,clearance=.25,via=(.8,.4),style=dict(eps=.02),
        pair_clearance=lambda a,z:(pair_gap(ds,a,z),(a in ds)!=(z in ds)))
    records=stitch_pads(b,r,['PGND','VEE_H','VEE_L','GNDP_H','GNDP_L','GNDP_S'])
    routing.save(b,output,dict(stitches=records));print('Stitch proposals',len(records),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['export','clip','apply','fill','stitch']);p.add_argument('--source',default='repair5');p.add_argument('--output',default='planes');a=p.parse_args()
    if a.stage=='export':export(a.source)
    elif a.stage=='clip':clip()
    elif a.stage=='apply':apply(a.output)
    elif a.stage=='stitch':stitch(a.source,a.output)
    else:
        from automation.sic_v3 import routing
        routing.WORK=WORK;routing.fill_checkpoint('power',a.output)
