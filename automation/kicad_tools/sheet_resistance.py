"""DC resistor-mesh screen of native multilayer copper, using SciPy/Shapely.

This finite square mesh is not a qualified electrothermal solver. Pad lands
are solid (drill voids/current crowding omitted), contacts are equipotential,
and via/lead plating is assumed. Compare mesh spacings and retain limitations.
No IPC ampacity or temperature-rise claim follows from this calculation.
"""
import math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from scipy.sparse.csgraph import connected_components
from shapely import contains_xy
from shapely.geometry import Point
from automation.kicad_tools.copper_review import geometry


def solve(records,net,sources,sinks,*,grid=.5,temperature=100.,thickness=.07,
          layers=('F.Cu','In1.Cu','In2.Cu','B.Cu'),z=(0.,.27,1.66,1.93),plating=.025):
    rec=[r for r in records if r['net']==net];geo={l:geometry([r for r in rec if r['layer']==l]) for l in layers}
    allgeom=geometry(rec);x0,y0,x1,y1=allgeom.bounds
    x0=math.floor(x0/grid)*grid;y0=math.floor(y0/grid)*grid
    xs=np.arange(x0+grid/2,x1+grid,grid);ys=np.arange(y0+grid/2,y1+grid,grid);xx,yy=np.meshgrid(xs,ys)
    ids=[];coords=[];count=0;aa=[];bb=[];gg=[];rho=1.724e-5*(1+.00393*(temperature-20)) # ohm mm
    for l in layers:
        mask=contains_xy(geo[l],xx,yy);index=np.full(mask.shape,-1,dtype=np.int64);index[mask]=np.arange(count,count+mask.sum());count+=mask.sum();ids.append(index)
        coords.extend(zip(xx[mask],yy[mask],np.full(mask.sum(),layers.index(l))))
        for a,b in [(index[:,:-1],index[:,1:]),(index[:-1,:],index[1:,:])]:
            keep=(a>=0)&(b>=0);aa.extend(a[keep]);bb.extend(b[keep]);gg.extend(np.full(keep.sum(),thickness/rho))
    def nearest(layer,xy,radius):
        ix=round((xy[0]-xs[0])/grid);iy=round((xy[1]-ys[0])/grid);candidates=[]
        for dy in range(-2,3):
            for dx in range(-2,3):
                x,y=ix+dx,iy+dy
                if 0<=x<len(xs) and 0<=y<len(ys) and ids[layer][y,x]>=0:
                    distance=math.hypot(xs[x]-xy[0],ys[y]-xy[1])
                    if distance<=radius+grid*.71:candidates.append((distance,ids[layer][y,x]))
        return min(candidates)[1] if candidates else None
    through={r['uuid']:r for r in rec if r.get('through')};missed=[]
    for key,r in through.items():
        drill=max(r.get('drill_mm') or [0.])
        if not drill:continue
        # Native through-pad/via is a vertical conductive barrel. Approximate
        #one mesh contact per layer; diameter/plating and spreading are open.
        contacts=[nearest(i,r['xy'],max(drill/2,(r.get('width_mm') or 0)/2)) for i in range(len(layers))]
        hits=[i for i,n in enumerate(contacts) if n is not None]
        if len(hits)<2:missed.append(key)
        for i,j in zip(hits,hits[1:]):
            aa.append(contacts[i]);bb.append(contacts[j]);gg.append(math.pi*drill*plating/(rho*abs(z[j]-z[i])))
    aa=np.asarray(aa,dtype=np.int64);bb=np.asarray(bb,dtype=np.int64);gg=np.asarray(gg)
    graph=coo_matrix((np.ones(len(aa)*2),(np.r_[aa,bb],np.r_[bb,aa])),shape=(count,count)).tocsr()
    _,labels=connected_components(graph,directed=False)
    def contact(pads):
        selected=[]
        for r in rec:
            if r['kind']!='pad' or (r['ref'],r['pin']) not in pads:continue
            i=layers.index(r['layer']);mask=contains_xy(geometry([r]).buffer(.0001),xx,yy);selected.extend(ids[i][mask & (ids[i]>=0)])
        return np.unique(selected).astype(np.int64)
    src=contact(sources);dst=contact(sinks)
    if not len(src) or not len(dst):return dict(status='contact_not_resolved',net=net,grid_mm=grid)
    common=set(labels[src])&set(labels[dst])
    if not common:return dict(status='mesh_disconnected',net=net,grid_mm=grid,nodes=int(count),missed_through=len(missed))
    keep=np.isin(labels,list(common));remap=np.full(count,-1,dtype=np.int64);remap[keep]=np.arange(keep.sum())
    valid=keep[aa]&keep[bb];a=remap[aa[valid]];b=remap[bb[valid]];g=gg[valid];n=keep.sum()
    src=remap[src[keep[src]]];dst=remap[dst[keep[dst]]]
    lap=coo_matrix((np.r_[g,g,-g,-g],(np.r_[a,b,a,b],np.r_[a,b,b,a])),shape=(n,n)).tocsr()
    fixed=np.zeros(n,dtype=bool);fixed[src]=True;fixed[dst]=True;v=np.zeros(n);v[src]=1.;free=~fixed
    v[free]=spsolve(lap[free][:,free],-lap[free][:,fixed]@v[fixed])
    current=float((lap@v)[src].sum());r=1/current;branch=g*(v[a]-v[b])/current
    positions=np.asarray(coords)[keep];worst=int(np.argmax(np.abs(branch)))
    return dict(status='mesh_solved',net=net,grid_mm=grid,nodes=int(n),temperature_C=temperature,resistance_mOhm=r*1000,
                loss_at_25A_W=625*r,source_contacts=len(src),sink_contacts=len(dst),missed_through=len(missed),
                maximum_branch_fraction=float(np.max(np.abs(branch))),
                maximum_branch_endpoints=[positions[a[worst]].tolist(),positions[b[worst]].tolist()],
                assumptions=dict(copper_mm=thickness,plating_mm=plating,resistivity_ohm_mm=rho,layer_z_mm=z,
                    pad_drill_voids='omitted; optimistic local pad conduction',contacts='ideal equipotential land contacts on all layers',
                    interpretation='DC mesh estimate only; excludes AC proximity/skin losses, solder/lead/contact losses, copper tolerances and temperature coupling'))
