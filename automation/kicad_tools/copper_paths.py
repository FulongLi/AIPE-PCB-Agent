"""Shortest geometric paths inside exported native copper; not EM extraction.

Raster paths retain zone holes and verified vertical connection locations.
The returned path is a geometric witness, not the dominant HF current path.
"""
import math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from shapely import contains_xy
from shapely.geometry import Point, LineString, box
from automation.kicad_tools.copper_review import geometry


class CopperPaths:
    def __init__(self, records, net, bounds, grid=.25,
                 layers=('F.Cu','In1.Cu','In2.Cu','B.Cu'), z=(0.,-.27,-1.66,-1.93)):
        self.records=[r for r in records if r['net']==net]
        self.net=net;self.grid=grid;self.layers=layers;self.z=z
        self.geo=[geometry([r for r in self.records if r['layer']==l]).intersection(box(*bounds)).buffer(.000003) for l in layers]
        x0,y0,x1,y1=bounds
        self.xs=np.arange(x0,x1+grid/2,grid);self.ys=np.arange(y0,y1+grid/2,grid)
        xx,yy=np.meshgrid(self.xs,self.ys);self.ids=[];self.coords=[];count=0;aa=[];bb=[];ww=[]
        for i,g in enumerate(self.geo):
            mask=contains_xy(g,xx,yy);idx=np.full(mask.shape,-1,dtype=np.int64)
            idx[mask]=np.arange(count,count+mask.sum());count+=mask.sum();self.ids.append(idx)
            self.coords.extend(zip(xx[mask],yy[mask],np.full(mask.sum(),z[i])))
            for dy,dx in [(0,1),(1,0),(1,1),(1,-1)]:
                ya=slice(0,len(self.ys)-dy);yb=slice(dy,len(self.ys))
                xa=slice(max(0,-dx),min(len(self.xs),len(self.xs)-dx));xb=slice(max(0,dx),min(len(self.xs),len(self.xs)+dx))
                a=idx[ya,xa];b=idx[yb,xb];keep=(a>=0)&(b>=0)
                # Midpoint checks prevent hopping across sub-grid holes.
                keep &= contains_xy(g,(xx[ya,xa]+xx[yb,xb])/2,(yy[ya,xa]+yy[yb,xb])/2)
                aa.extend(a[keep]);bb.extend(b[keep]);ww.extend(np.full(keep.sum(),grid*math.hypot(dx,dy)))
        self.vertical={}
        for r in {r['uuid']:r for r in self.records if r.get('through')}.values():
            if not box(*bounds).covers(Point(r['xy'])):continue
            contacts=[]
            for i in range(len(layers)):
                try:contacts.append((i,self.nearest(i,r['xy'],grid*2)))
                except ValueError:pass
            for (i,a),(j,b) in zip(contacts,contacts[1:]):
                if not all(self.geo[k].covers(LineString([self.coords[n][:2],r['xy']])) for k,n in [(i,a),(j,b)]):continue
                aa.append(a);bb.append(b);ww.append(abs(z[j]-z[i])+math.dist(self.coords[a][:2],r['xy'])+math.dist(self.coords[b][:2],r['xy']))
                self.vertical[(a,b)]=self.vertical[(b,a)]=r['xy']
        self.graph=coo_matrix((ww+ww,(aa+bb,bb+aa)),shape=(count,count)).tocsr()

    def nearest(self, layer, xy, radius):
        ix=round((xy[0]-self.xs[0])/self.grid);iy=round((xy[1]-self.ys[0])/self.grid);hits=[]
        for dy in range(-3,4):
            for dx in range(-3,4):
                x,y=ix+dx,iy+dy
                if not (0<=x<len(self.xs) and 0<=y<len(self.ys)):continue
                n=self.ids[layer][y,x]
                if n<0:continue
                p=(self.xs[x],self.ys[y]);dist=math.dist(xy,p)
                if dist<=radius and self.geo[layer].covers(LineString([xy,p])):hits.append((dist,int(n)))
        if not hits:raise ValueError(f'No copper mesh contact: {self.net} {layer} {xy}')
        return min(hits)[1]

    def path(self, start, end):
        """Start/end are XYZ pad centres on explicit physical layers."""
        a=self.nearest(self.z.index(start[2]),start[:2],self.grid*2)
        b=self.nearest(self.z.index(end[2]),end[:2],self.grid*2)
        dist,pred=dijkstra(self.graph,indices=a,return_predecessors=True)
        if not np.isfinite(dist[b]):raise ValueError(f'No path on {self.net}')
        nodes=[b]
        while nodes[-1]!=a:nodes.append(int(pred[nodes[-1]]))
        nodes.reverse();points=[list(start),list(self.coords[a])]
        for u,v in zip(nodes,nodes[1:]):
            if (u,v) in self.vertical:
                xy=self.vertical[(u,v)];points.extend([[*xy,self.coords[u][2]],[*xy,self.coords[v][2]]])
            points.append(list(self.coords[v]))
        points.append(list(end));simple=[]
        for p in points:
            if simple and math.dist(simple[-1],p)<1e-9:continue
            while len(simple)>1:
                u=np.array(simple[-1])-simple[-2];v=np.array(p)-simple[-1]
                if np.linalg.norm(np.cross(u,v))<1e-9 and np.dot(u,v)>=0:simple.pop()
                else:break
            simple.append(p)
        misses=[]
        for p,q in zip(simple,simple[1:]):
            if p[2]==q[2]:
                missing=LineString([p[:2],q[:2]]).difference(self.geo[self.z.index(p[2])]).length
                if missing>1e-5:misses.append(missing)
        if misses:raise ValueError(f'Path leaves native copper: {self.net} {misses}')
        return dict(role='copper',net=self.net,points=simple,grid_mm=self.grid,coverage_passed=True)
