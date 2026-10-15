"""Pair-specific clearance overlays for the reusable grid router.

The callback returns (gap_mm, project_across_layers). The latter preserves a
planar isolation corridor across the whole stack, beyond ordinary same-layer
DRC. Pads are conservatively boxed; tracks/vias use their physical radii.
Native DRC and an independent barrier audit remain required.
"""
import math
import numpy as np
from automation.kicad_tools.grid_router import Router


def exclude_box(mask,grid,box,radius):
    x0,y0,x1,y1=box
    ix0=max(0,math.floor((x0-radius-grid.ox)/grid.grid));ix1=min(grid.nx-1,math.ceil((x1+radius-grid.ox)/grid.grid))
    iy0=max(0,math.floor((y0-radius-grid.oy)/grid.grid));iy1=min(grid.ny-1,math.ceil((y1+radius-grid.oy)/grid.grid))
    if ix0>ix1 or iy0>iy1:return
    xx=np.arange(ix0,ix1+1)*grid.grid+grid.ox;yy=np.arange(iy0,iy1+1)*grid.grid+grid.oy
    dx=np.maximum(np.maximum(x0-xx,xx-x1),0);dy=np.maximum(np.maximum(y0-yy,yy-y1),0)
    mask[iy0:iy1+1,ix0:ix1+1] &= (dy[:,None]**2+dx[None,:]**2)>radius**2


def exclude_segment(mask,grid,a,b,radius):
    x0,y0=min(a[0],b[0]),min(a[1],b[1]);x1,y1=max(a[0],b[0]),max(a[1],b[1])
    ix0=max(0,math.floor((x0-radius-grid.ox)/grid.grid));ix1=min(grid.nx-1,math.ceil((x1+radius-grid.ox)/grid.grid))
    iy0=max(0,math.floor((y0-radius-grid.oy)/grid.grid));iy1=min(grid.ny-1,math.ceil((y1+radius-grid.oy)/grid.grid))
    if ix0>ix1 or iy0>iy1:return
    xx=np.arange(ix0,ix1+1)[None,:]*grid.grid+grid.ox;yy=np.arange(iy0,iy1+1)[:,None]*grid.grid+grid.oy
    dx,dy=b[0]-a[0],b[1]-a[1];length2=dx*dx+dy*dy
    t=np.clip(((xx-a[0])*dx+(yy-a[1])*dy)/length2,0,1) if length2 else 0
    mask[iy0:iy1+1,ix0:ix1+1] &= ((xx-a[0]-t*dx)**2+(yy-a[1]-t*dy)**2)>radius**2


class PairwiseRouter(Router):
    def __init__(self,*args,pair_clearance,**kwargs):
        self.pair_clearance=pair_clearance;self._pair_cache={}
        super().__init__(*args,**kwargs)

    def refresh_pair_masks(self):self._pair_cache={}

    def region_masks(self,net):
        if net in self._pair_cache:return self._pair_cache[net]
        region,via_region=super().region_masks(net)
        shape=(self.grid.ny,self.grid.nx)
        allowed=[m.copy() if m is not None else np.ones(shape,dtype=bool) for m in region] if region else [np.ones(shape,dtype=bool) for _ in self.layers]
        vm=via_region.copy() if via_region is not None else np.ones(shape,dtype=bool)
        half=self.width_for(net)/2;vh=self.via_d/2;g=self.grid
        for p in self.pad_records:
            if not p['net'] or p['net']==net:continue
            gap,across=self.pair_clearance(net,p['net'])
            if gap<=self.clearance and not across:continue
            for layer in range(self.nl) if across or p['thru'] else p['layers']:
                exclude_box(allowed[layer],g,p['box'],gap+half+self.eps)
            exclude_box(vm,g,p['box'],gap+vh+self.eps)
        for t in self.board.GetTracks():
            foreign=t.GetNetname()
            if not foreign or foreign==net:continue
            gap,across=self.pair_clearance(net,foreign)
            if gap<=self.clearance and not across:continue
            via=isinstance(t,self.pcb.PCB_VIA)
            width=self.pcb.ToMM(t.GetWidth(self.pcb.F_Cu) if via else t.GetWidth())
            a=tuple(self.pcb.ToMM(t.GetPosition() if via else t.GetStart()))
            b=a if via else tuple(self.pcb.ToMM(t.GetEnd()))
            layers=range(self.nl) if across or via else [self.layers.index(t.GetLayer())] if t.GetLayer() in self.layers else []
            for layer in layers:exclude_segment(allowed[layer],g,a,b,gap+half+width/2+self.eps)
            exclude_segment(vm,g,a,b,gap+vh+width/2+self.eps)
        self._pair_cache={net:(allowed,vm)}
        return allowed,vm

    def route_net(self,net,*args,**kwargs):
        self.refresh_pair_masks()
        return super().route_net(net,*args,**kwargs)
