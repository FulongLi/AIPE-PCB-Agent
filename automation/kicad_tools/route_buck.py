"""AI-directed routing: critical gate nets, multilayer signals, then power planes.

No external autorouter is used. Grid routing is only a geometric proposal; native
KiCad DRC and connectivity, followed by engineering review, decide acceptance.
"""
from __future__ import annotations

import heapq
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from automation.kicad_tools.buck_model import EXAMPLE,build

GRID=0.25
NX,NY=1201,881
TRACE=0.2
CLEAR=0.2
VIA=0.6
CRITICAL={'HO','LO','GH1','GH2','GL1','GL2','BOOT'}
POWER={'VIN_RAW','VIN','SW','IL_FORCE','VOUT'}


class Router:
    def __init__(self,board):
        import numpy as np
        import pcbnew as pcb
        self.np,self.pcb,self.board=np,pcb,board
        self.layers=[pcb.F_Cu,pcb.In2_Cu,pcb.In3_Cu,pcb.B_Cu]
        self.occ=np.zeros((4,NY,NX),dtype=np.int16)
        self.vocc=np.zeros((NY,NX),dtype=np.int16)
        self.holes=np.zeros((NY,NX),dtype=np.int16)
        self.transitions=np.zeros((NY,NX),dtype=np.int16)
        self.vias={}; self.through=[]
        self.nets={n.GetNetname():n for n in board.GetNetInfo().NetsByNetcode().values() if n.GetNetCode()}
        self.code={name:net.GetNetCode() for name,net in self.nets.items()}
        self.ports=defaultdict(list);self.pad_records=[];self.stats=defaultdict(int)
        self.occ[:,:4,:]=-1;self.occ[:,-4:,:]=-1;self.occ[:,:,:4]=-1;self.occ[:,:,-4:]=-1
        self.vocc[:4,:]=-1;self.vocc[-4:,:]=-1;self.vocc[:,:4]=-1;self.vocc[:,-4:]=-1
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                net=pad.GetNetname();code=pad.GetNetCode() or -1
                pos=pcb.ToMM(pad.GetPosition());bb=pad.GetBoundingBox()
                box=[pcb.ToMM(bb.GetX()),pcb.ToMM(bb.GetY()),pcb.ToMM(bb.GetRight()),pcb.ToMM(bb.GetBottom())]
                thru=pad.GetAttribute() in (pcb.PAD_ATTRIB_PTH,pcb.PAD_ATTRIB_NPTH)
                if not thru and not pad.IsOnLayer(pcb.F_Cu):continue
                if thru:
                    self.through.append((pad,net))
                    drill=pcb.ToMM(pad.GetDrillSize())
                    self.box(self.holes,[pos[0]-drill[0]/2,pos[1]-drill[1]/2,pos[0]+drill[0]/2,pos[1]+drill[1]/2],0.42,-1)
                    if pad.GetAttribute()==pcb.PAD_ATTRIB_PTH:
                        self.segment(self.transitions,pos,pos,min(pcb.ToMM(pad.GetSize()))/2-0.15,code)
                for layer in range(4) if thru else (0,):self.box(self.occ[layer],box,0.3,code)
                self.box(self.vocc,box,0.5,code)
                self.pad_records.append(dict(fp=fp,pad=pad,net=net,code=code,xy=pos,box=box,thru=thru))
        # Reserve the main SW extension from ordinary inner-layer signal routing.
        for layer in (1,2): self.box(self.occ[layer],[133,36,156,58],0,self.code['SW'])

    def point(self,x,y):return self.pcb.VECTOR2I(self.pcb.FromMM(x),self.pcb.FromMM(y))

    def merge(self,view,mask,code):
        view[mask & (view!=0) & (view!=code)] = -1
        view[mask & (view==0)] = code

    def box(self,array,bb,inflate,code):
        x0=max(0,math.ceil((bb[0]-inflate)/GRID));x1=min(NX-1,math.floor((bb[2]+inflate)/GRID))
        y0=max(0,math.ceil((bb[1]-inflate)/GRID));y1=min(NY-1,math.floor((bb[3]+inflate)/GRID))
        v=array[y0:y1+1,x0:x1+1]
        self.merge(v,self.np.ones(v.shape,dtype=bool),code)

    def segment(self,array,a,b,radius,code):
        np=self.np
        x0=max(0,math.ceil((min(a[0],b[0])-radius)/GRID));x1=min(NX-1,math.floor((max(a[0],b[0])+radius)/GRID))
        y0=max(0,math.ceil((min(a[1],b[1])-radius)/GRID));y1=min(NY-1,math.floor((max(a[1],b[1])+radius)/GRID))
        if x0>x1 or y0>y1:return
        xx,yy=np.meshgrid(np.arange(x0,x1+1)*GRID,np.arange(y0,y1+1)*GRID)
        dx,dy=b[0]-a[0],b[1]-a[1]
        den=dx*dx+dy*dy
        t=np.clip(((xx-a[0])*dx+(yy-a[1])*dy)/(den or 1),0,1)
        mask=(xx-a[0]-t*dx)**2+(yy-a[1]-t*dy)**2 < radius**2-1e-9
        self.merge(array[y0:y1+1,x0:x1+1],mask,code)

    def track(self,a,b,net,layer,width=TRACE):
        if math.dist(a,b)<1e-6:return
        p=self.pcb.PCB_TRACK(self.board);p.SetStart(self.point(*a));p.SetEnd(self.point(*b))
        p.SetWidth(self.pcb.FromMM(width));p.SetLayer(self.layers[layer]);p.SetNet(self.nets[net]);self.board.Add(p)
        self.segment(self.occ[layer],a,b,width/2+CLEAR+TRACE/2+0.01,self.code[net])
        self.segment(self.vocc,a,b,width/2+CLEAR+VIA/2+0.01,self.code[net])
        self.stats['tracks']+=1

    def via(self,xy,net,diameter=VIA,drill=0.3):
        if self.existing_transition(xy,net):return
        p=self.pcb.PCB_VIA(self.board);p.SetPosition(self.point(*xy));p.SetWidth(self.pcb.FromMM(diameter));p.SetDrill(self.pcb.FromMM(drill))
        p.SetLayerPair(self.pcb.F_Cu,self.pcb.B_Cu);p.SetViaType(self.pcb.VIATYPE_THROUGH);p.SetNet(self.nets[net]);self.board.Add(p)
        for layer in range(4):self.segment(self.occ[layer],xy,xy,diameter/2+CLEAR+TRACE/2+0.01,self.code[net])
        self.segment(self.vocc,xy,xy,diameter/2+CLEAR+VIA/2+0.01,self.code[net])
        self.segment(self.holes,xy,xy,drill/2+0.25+0.15+0.02,-1)
        self.vias[tuple(xy)]=net
        self.stats['vias']+=1

    def existing_transition(self,xy,net):
        if self.vias.get(tuple(xy))==net:return True
        # HitTest also accepts the bounding-box corners of oval pads. Use the
        # inscribed circle so a skipped via really lands on plated copper.
        gx,gy=round(xy[0]/GRID),round(xy[1]/GRID)
        if abs(gx*GRID-xy[0])+abs(gy*GRID-xy[1])<1e-6:
            return int(self.transitions[gy,gx])==self.code[net]
        return any(name==net and pad.GetAttribute()==self.pcb.PAD_ATTRIB_PTH
                   and math.dist(xy,self.pcb.ToMM(pad.GetPosition())) <= min(self.pcb.ToMM(pad.GetSize()))/2-0.15
                   for pad,name in self.through)

    def via_allowed(self,x,y,net):
        if self.existing_transition((x*GRID,y*GRID),net):return True
        return self.holes[y,x]==0 and int(self.vocc[y,x]) in (0,self.code[net])

    def astar(self,start,end,net,layers=(1,2,3),max_nodes=700000,margin=None):
        code=self.code[net]
        sx,sy,sl=start;ex,ey,el=end
        if margin is not None:
            xmin=max(4,min(sx,ex)-margin);xmax=min(NX-5,max(sx,ex)+margin)
            ymin=max(4,min(sy,ey)-margin);ymax=min(NY-5,max(sy,ey)+margin)
        else:xmin,xmax,ymin,ymax=4,NX-5,4,NY-5
        def h(x,y,l):return abs(ex-x)+abs(ey-y)+(0 if l==el else 5)
        def enc(x,y,l):return (l*NY+y)*NX+x
        def dec(k):return (k%NX,(k//NX)%NY,k//(NX*NY))
        key=enc(sx,sy,sl);goal=enc(ex,ey,el)
        heap=[(h(sx,sy,sl),0,key)];costs={key:0};parent={};expanded=0
        while heap:
            _,cost,k=heapq.heappop(heap)
            if cost!=costs.get(k):continue
            if k==goal:
                path=[dec(k)]
                while k in parent:k=parent[k];path.append(dec(k))
                path.reverse();return path
            expanded+=1
            if expanded>max_nodes:return None
            x,y,l=dec(k)
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                xx,yy=x+dx,y+dy
                if not(xmin<=xx<=xmax and ymin<=yy<=ymax):continue
                v=int(self.occ[l,yy,xx])
                if v not in (0,code):continue
                step=1.0 if l==0 or (l==1 and dy==0) or (l==2 and dx==0) or l==3 else 1.15
                nc=cost+step;nk=enc(xx,yy,l)
                if nc<costs.get(nk,math.inf):
                    costs[nk]=nc;parent[nk]=k;heapq.heappush(heap,(nc+h(xx,yy,l),nc,nk))
            if len(layers)>1 and self.via_allowed(x,y,net):
                for ll in layers:
                    if ll==l or int(self.occ[ll,y,x]) not in (0,code):continue
                    nk=enc(x,y,ll);nc=cost+8
                    if nc<costs.get(nk,math.inf):
                        costs[nk]=nc;parent[nk]=k;heapq.heappush(heap,(nc+h(x,y,ll),nc,nk))
        return None

    def emit(self,path,net):
        if len(path)<2:return
        first=last=path[0];direction=None
        for node in path[1:]:
            delta=(node[0]-last[0],node[1]-last[1],node[2]-last[2])
            if node[2]!=last[2]:
                self.track((first[0]*GRID,first[1]*GRID),(last[0]*GRID,last[1]*GRID),net,last[2])
                self.via((last[0]*GRID,last[1]*GRID),net);first=node;direction=None
            elif direction is not None and delta!=direction:
                self.track((first[0]*GRID,first[1]*GRID),(last[0]*GRID,last[1]*GRID),net,last[2]);first=last
            direction=delta;last=node
        self.track((first[0]*GRID,first[1]*GRID),(last[0]*GRID,last[1]*GRID),net,last[2])

    def fanout(self):
        records=sorted(self.pad_records,key=lambda r:(0 if r['fp'].GetReference()=='U16' else 1 if r['fp'].GetReference().startswith('U') else 2, r['fp'].GetReference(),-1 if r['fp'].GetReference()=='U15' and r['pad'].GetNumber()=='4' else int(r['pad'].GetNumber() or 0)))
        failures=[]
        for r in records:
            net=r['net']
            if not net or net.startswith('unconnected-'):continue
            x,y=r['xy'];sx,sy=round(x/GRID),round(y/GRID)
            ref=r['fp'].GetReference();number=r['pad'].GetNumber()
            if r['thru'] or net in CRITICAL:
                layer=0 if net in CRITICAL else 1
                self.ports[net].append((sx,sy,layer,ref,number));continue
            if (ref,number) in (('U1','9'),('U2','9'),('U4','29')):
                # Thermal exposed-pad vias are intentionally in-pad; assembly
                # notes call out solder-wicking control and via treatment.
                xy=(sx*GRID,sy*GRID);self.via(xy,net)
                self.track((x,y),xy,net,0)
                self.ports[net].append((sx,sy,1,ref,number));continue
            cx,cy=self.pcb.ToMM(r['fp'].GetPosition())
            dx,dy=x-cx,y-cy
            if abs(dx)>=abs(dy):ux,uy=(1 if dx>=0 else -1),0
            else:ux,uy=0,(1 if dy>=0 else -1)
            extent=(r['box'][2]-r['box'][0])/2 if ux else (r['box'][3]-r['box'][1])/2
            candidates=[]
            primary=-1 if ref=='U16' and int(number)%2==0 else 1
            for sign in (primary,-primary):
                for distance in (extent+0.65,extent+1.25,extent+1.9,extent+2.65,extent+3.5,extent+4.5,extent+6):
                    for shift in (0,0.5,-0.5,1.0,-1.0,1.5,-1.5,2,-2):
                        ex=round((x+sign*ux*distance-uy*shift)/GRID);ey=round((y+sign*uy*distance+ux*shift)/GRID)
                        if not(4<=ex<NX-4 and 4<=ey<NY-4):continue
                        if not self.via_allowed(ex,ey,net):continue
                        if any(int(self.occ[l,ey,ex]) not in (0,r['code']) for l in range(4)):continue
                        candidates.append((distance+abs(shift)*1.4+(10 if sign!=primary else 0),ex,ey))
            routed=False
            for _,ex,ey in sorted(set(candidates)):
                path=self.astar((sx,sy,0),(ex,ey,0),net,layers=(0,),max_nodes=1500,margin=10)
                if path is None:continue
                self.track((x,y),(sx*GRID,sy*GRID),net,0);self.emit(path,net);self.via((ex*GRID,ey*GRID),net)
                self.ports[net].append((ex,ey,1,ref,number));routed=True;break
            if not routed:failures.append([ref,number,net])
        print(f'Fanout: {self.stats["vias"]} vias; {len(failures)} unresolved pads',flush=True)
        return failures

    def route_net(self,net,ports=None,layers=(1,2,3)):
        ports=ports or self.ports[net]
        points=list(dict.fromkeys((p[0],p[1],0 if net in CRITICAL else p[2]) for p in ports))
        if len(points)<2:return []
        connected=[points.pop(0)];failures=[]
        while points:
            distance,a,b=min((abs(a[0]-b[0])+abs(a[1]-b[1]),a,b) for a in connected for b in points)
            path=self.astar(a,b,net,layers=layers)
            if path is None and net not in POWER|CRITICAL:
                # A dense package escape may need to use the component layer
                # briefly before reaching the ordinary signal layers.
                path=self.astar(a,b,net,layers=(0,1,2,3))
            if path is None:
                failures.append([net,a,b,{'start':int(self.occ[a[2],a[1],a[0]]),'end':int(self.occ[b[2],b[1],b[0]]),'code':self.code[net]}]);points.remove(b);continue
            self.emit(path,net);connected.append(b);points.remove(b)
        return failures


def main():
    import pcbnew as pcb
    path=EXAMPLE/'kicad/AIPE_Buck_1kW.kicad_pcb'
    board=pcb.LoadBoard(str(path))
    if len(list(board.GetTracks())) or len(board.Zones()):raise RuntimeError('Start from generated placement; refusing to add duplicate routing')
    start=time.monotonic();r=Router(board)
    # Short individual drain/source connections into the larger copper regions.
    for x in (114.54,128.54):
        for layer in (0,1):r.track((x,42),(x,37),'VIN',layer,2.2)
    for x in (117.08,131.08):
        for layer in (0,3):r.track((x,55),(x,62),'GND',layer,2.2)
    for x,y in [(122.35,47.45),(123.65,47.45),(122.35,48.75),(123.65,48.75),
                (33.35,142.35),(34.65,142.35),(33.35,143.65),(34.65,143.65)]:
        r.via((x,y),'GND')
    for x in (124.35,125.65):
        for y in (141.05,142.35,143.65,144.95):r.via((x,y),'GND')
    # 32 vias on each shunt force side spread the outer-layer current transfer.
    for net,x0 in [('IL_FORCE',195),('VOUT',214)]:
        for ix in range(4):
            for iy in range(8):r.via((x0+ix*1.5,39.5+iy*1.5),net,1.0,0.5)
    # Stitch divided switch-node copper around the driver/boot escape. These
    # intentional SW vias remain inside the power partition.
    for xy in ((118,47),(130,43.5),(130,55.5),(134,41),(145,44),(120,54)):
        if r.via_allowed(round(xy[0]/GRID),round(xy[1]/GRID),'SW'):
            r.via(xy,'SW')
            r.ports['SW'].append((round(xy[0]/GRID),round(xy[1]/GRID),1,'SW_STITCH',''))
    failures=r.fanout()
    if failures:
        (EXAMPLE/'verification/routing_progress.json').write_text(json.dumps(dict(stage='fanout',unresolved=failures),indent=2)+'\n')
        pcb.SaveBoard(str(ROOT/'.aipe/buck-routing-debug.kicad_pcb'),board)
        raise RuntimeError('Resolve fanout before general routing')
    for net in sorted(CRITICAL):
        before=len(failures)
        failures.extend(r.route_net(net,layers=(0,3)))
        print('Critical net',net,'unresolved',len(failures)-before,flush=True)
    # Main power terminals join through the dimensioned copper zones below.
    mainrefs={f'C{i}' for i in range(1,27)}|{'Q1','Q2','Q3','Q4','L1','R9','J1','J2','J3','J4','F1','D1'}
    for net in sorted(POWER):
        anchors=[p for p in r.ports[net] if p[3] in mainrefs]
        for port in (p for p in r.ports[net] if p[3] not in mainrefs):
            anchor=min(anchors,key=lambda p:abs(port[0]-p[0])+abs(port[1]-p[1]))
            failures.extend(r.route_net(net,[anchor,port]))
    remaining=[n for n in r.ports if n not in POWER|CRITICAL|{'GND'}]
    remaining.sort(key=lambda n:(0 if n.startswith(('ISENSE','ADC','CLK')) else 1 if n in ('1V9','3V3','AUX12','5V') else 2,len(r.ports[n])))
    for i,net in enumerate(remaining,1):
        failures.extend(r.route_net(net))
        if i%8==0:print(f'Signal nets {i}/{len(remaining)}; unresolved routes {len(failures)}; elapsed {time.monotonic()-start:.1f}s',flush=True)

    # A fallback can return along the original component-layer escape, leaving
    # an electrically unnecessary via at its starting point. Remove only vias
    # with fewer than two incident copper layers on nets without copper zones.
    tracks=[t for t in board.GetTracks() if not isinstance(t,pcb.PCB_VIA)]
    for via in list(board.GetTracks()):
        if not isinstance(via,pcb.PCB_VIA) or via.GetNetname() in POWER|{'GND'}:continue
        xy=via.GetPosition()
        attached={t.GetLayer() for t in tracks if t.GetNetCode()==via.GetNetCode()
                  and (t.GetStart()==xy or t.GetEnd()==xy)}
        for pad in board.GetPads():
            if pad.GetNetCode()==via.GetNetCode() and pad.HitTest(xy):
                attached.update(layer for layer in r.layers if pad.IsOnLayer(layer))
        if len(attached)<2:board.Remove(via);r.stats['pruned_unused_vias']+=1

    def zone(net,layer,points,priority=1,clearance=0.5):
        z=pcb.ZONE(board);z.SetNet(r.nets[net]);z.SetLayer(layer);z.SetAssignedPriority(priority)
        z.SetLocalClearance(pcb.FromMM(clearance));z.SetPadConnection(pcb.ZONE_CONNECTION_FULL)
        z.SetMinThickness(pcb.FromMM(0.2));poly=z.Outline();poly.NewOutline()
        z.SetIslandRemovalMode(pcb.ISLAND_REMOVAL_MODE_ALWAYS)
        for x,y in points:poly.Append(pcb.FromMM(x),pcb.FromMM(y))
        board.Add(z);return z
    power_shapes={
        'VIN_RAW':[(8,8),(48,8),(48,24),(8,24)],
        'VIN':[(62,8),(94,8),(94,27),(137,27),(137,38.5),(106,38.5),(106,67),(132.5,67),(132.5,74),(106,74),(106,115),(20,115),(20,27),(62,27)],
        'SW':[(116.3,40.5),(132.3,40.5),(132.3,39),(153.5,39),(153.5,58),(113.3,58),(113.3,51),(116.3,51)],
        'IL_FORCE':[(175,37),(206,37),(206,53),(175,53)],
        'VOUT':[(210,25),(289,25),(289,74),(210,74)],
    }
    for net,points in power_shapes.items():
        layers=(pcb.F_Cu,pcb.In2_Cu) if net=='VIN' else (pcb.F_Cu,pcb.In3_Cu,pcb.B_Cu) if net=='SW' else (pcb.F_Cu,pcb.B_Cu)
        for layer in layers:zone(net,layer,points)
    for layer in (pcb.F_Cu,pcb.In1_Cu,pcb.In4_Cu,pcb.B_Cu):
        z=zone('GND',layer,[(1,1),(299,1),(299,219),(1,219)],0,0.25)
        if layer in (pcb.In1_Cu,pcb.In4_Cu):
            polygon=z.Outline();hole=polygon.NewHole()
            for x,y in [(133,36),(156,36),(156,58),(133,58)]:polygon.Append(pcb.FromMM(x),pcb.FromMM(y),0,hole)
    board.BuildConnectivity();pcb.ZONE_FILLER(board).Fill(board.Zones());pcb.SaveBoard(str(path),board)
    report=dict(stage='routed_candidate',seconds=time.monotonic()-start,stats=dict(r.stats),unresolved=failures,
                status='requires-native-DRC',power_polygon_vertices=power_shapes)
    (EXAMPLE/'verification/routing_progress.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('seconds','stats','unresolved','status')},indent=2))


if __name__=='__main__':main()
