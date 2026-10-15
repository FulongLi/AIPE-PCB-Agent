"""Small reusable native-board builder driven by explicit project inputs.

No example paths or placement coordinates live here. Native schematic netlists
and symbol paths are the electrical source of truth. Placement screening uses
real footprint courtyards and pad boxes; final native DRC remains mandatory.
"""
from __future__ import annotations
import json
import math
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


class ProjectBoard:
    def __init__(self, directory, name, parts, mapping, *, layers=4, thickness=1.6, cli=None,stackup=None):
        import pcbnew as pcb
        self.pcb=pcb;self.directory=Path(directory);self.name=name
        self.stackup=stackup
        self.parts={p['ref']:p for p in parts if p.get('on_board',True)}
        self.board=pcb.BOARD();self.board.SetCopperLayerCount(layers)
        self.board.GetDesignSettings().SetBoardThickness(pcb.FromMM(thickness))
        title=self.board.GetTitleBlock();title.SetTitle(name);title.SetRevision('V3')
        title.SetComment(0,'ENGINEERING PROTOTYPE REVIEW - RELEASE BLOCKED')
        if cli is None:
            from automation.setup.detect_kicad import find_kicad_cli
            cli=find_kicad_cli()
        target=self.directory/(name+'.net.xml')
        subprocess.run([str(cli),'sch','export','netlist','--format','kicadxml','--output',str(target),
                        str(self.directory/(name+'.kicad_sch'))],check=True,capture_output=True)
        root=ET.parse(target).getroot()
        pin_nets={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in root.findall('nets/net') for n in net.findall('node')}
        self.nets={}
        for name in sorted(set(pin_nets.values())):
            net=pcb.NETINFO_ITEM(self.board,name);self.board.Add(net);self.nets[name]=net
        self.fp={};self.placed={}
        paths=json.loads(Path(mapping).read_text(encoding='utf-8'))['paths']
        for ref,part in self.parts.items():
            lib,footprint=part['footprint'].split(':')
            fp=pcb.FootprintLoad(str(self.directory/'libraries'/(lib+'.pretty')),footprint)
            if fp is None:raise ValueError((ref,part['footprint']))
            fp.SetFPID(pcb.LIB_ID(lib,footprint));fp.SetReference(ref);fp.SetValue(part['value'])
            fp.SetPath(pcb.KIID_PATH(paths[ref]));fp.Value().SetVisible(False)
            fp.Reference().SetLayer(pcb.F_Fab);fp.Reference().SetVisible(False)
            fp.SetPosition(self.point(0,0))
            seen=set()
            for pad in fp.Pads():
                num=pad.GetNumber()
                if not num:continue
                seen.add(num)
                if num not in part['nets']:raise ValueError((ref,'unexpected pad',num))
                net=pin_nets.get((ref,num))
                if net:pad.SetNet(self.nets[net])
            if seen!=set(part['nets']):raise ValueError((ref,'missing pads',set(part['nets'])-seen))
            self.board.Add(fp);self.fp[ref]=fp

    def point(self,x,y):return self.pcb.VECTOR2I(self.pcb.FromMM(float(x)),self.pcb.FromMM(float(y)))

    def layer(self,name):
        aliases={'F.SilkS':'F.Silkscreen','B.SilkS':'B.Silkscreen'}
        layer=self.board.GetLayerID(aliases.get(name,name))
        if layer<0:raise ValueError(('Unknown layer',name))
        return layer

    def pad(self,ref,number):
        return next(p for p in self.fp[ref].Pads() if p.GetNumber()==str(number))

    def xy(self,ref,number):return tuple(self.pcb.ToMM(self.pad(ref,number).GetPosition()))

    def box(self,ref):
        fp=self.fp[ref]
        # GetCourtyard needs a cache rebuild after a new footprint is loaded.
        fp.BuildCourtyardCaches()
        layer=self.pcb.B_CrtYd if fp.IsFlipped() else self.pcb.F_CrtYd
        courtyard=fp.GetCourtyard(layer)
        box=courtyard.BBox() if courtyard.OutlineCount() else fp.GetBoundingHull().BBox()
        return [self.pcb.ToMM(v) for v in (box.GetX(),box.GetY(),box.GetRight(),box.GetBottom())]

    def place(self,ref,x,y,angle=0,side='F'):
        fp=self.fp[ref]
        if fp.IsFlipped()!=(side=='B'):fp.Flip(fp.GetPosition(),False)
        fp.SetOrientationDegrees(angle);fp.SetPosition(self.point(x,y))
        self.placed[ref]=dict(x=float(x),y=float(y),angle=float(angle),side=side,bbox=self.box(ref))
        return self.placed[ref]

    def outline(self,points):
        for a,b in zip(points,points[1:]+points[:1]):
            line=self.pcb.PCB_SHAPE(self.board);line.SetShape(self.pcb.SHAPE_T_SEGMENT)
            line.SetStart(self.point(*a));line.SetEnd(self.point(*b));line.SetWidth(self.pcb.FromMM(.05));line.SetLayer(self.pcb.Edge_Cuts)
            self.board.Add(line)

    def track(self,net,points,width=.25,layer='F.Cu'):
        for a,b in zip(points,points[1:]):
            if math.dist(a,b)<1e-6:continue
            t=self.pcb.PCB_TRACK(self.board);t.SetStart(self.point(*a));t.SetEnd(self.point(*b));t.SetWidth(self.pcb.FromMM(width))
            t.SetLayer(self.layer(layer));t.SetNet(self.nets[net]);self.board.Add(t)

    def via(self,net,xy,diameter=.8,drill=.4):
        v=self.pcb.PCB_VIA(self.board);v.SetPosition(self.point(*xy));v.SetWidth(self.pcb.FromMM(diameter))
        v.SetDrill(self.pcb.FromMM(drill));v.SetViaType(self.pcb.VIATYPE_THROUGH);v.SetLayerPair(self.pcb.F_Cu,self.pcb.B_Cu)
        v.SetNet(self.nets[net]);self.board.Add(v)

    def label(self,text,xy,*,size=1.2,layer='F.SilkS'):
        t=self.pcb.PCB_TEXT(self.board);t.SetText(text);t.SetPosition(self.point(*xy));t.SetLayer(self.layer(layer))
        t.SetTextSize(self.point(size,size));t.SetTextThickness(self.pcb.FromMM(.15));self.board.Add(t)

    def pads(self):
        out=[]
        for ref,fp in self.fp.items():
            for pad in fp.Pads():
                box=pad.GetBoundingBox()
                out.append(dict(ref=ref,pin=pad.GetNumber(),net=pad.GetNetname(),xy=list(self.pcb.ToMM(pad.GetPosition())),
                    box=[self.pcb.ToMM(v) for v in (box.GetX(),box.GetY(),box.GetRight(),box.GetBottom())],
                    layers=[self.board.GetLayerName(l) for l in pad.GetLayerSet().CuStack()],thru=pad.GetAttribute()!=self.pcb.PAD_ATTRIB_SMD))
        return out

    def save(self,path=None):
        path=Path(path or self.directory/(self.name+'.kicad_pcb'));path.parent.mkdir(parents=True,exist_ok=True)
        self.pcb.SaveBoard(str(path),self.board,True)
        if self.stackup:write_stackup(path,self.stackup)
        return path


def write_stackup(path,layers,material='R-1566(S)/R-1551(S); CTI>=600 fabricator-qualified'):
    """Write the specified physical stack; never silently retain a default stack."""
    text=Path(path).read_text(encoding='utf-8')
    if '(stackup' in text:
        start=text.index('(stackup');depth=0;quoted=False;escaped=False
        for end in range(start,len(text)):
            ch=text[end]
            if ch=='"' and not escaped:quoted=not quoted
            if not quoted:
                if ch=='(':depth+=1
                elif ch==')':
                    depth-=1
                    if depth==0:break
            escaped=ch=='\\' and not escaped
        text=text[:start]+text[end+1:]
    entries=['(stackup']
    for name,kind,thickness in layers:
        prop='' if kind=='copper' else f' (material "{material}") (epsilon_r 4.3) (loss_tangent 0.02)'
        entries.append(f'(layer "{name}" (type "{kind}") (thickness {thickness}){prop})')
    entries.append('(copper_finish "ENIG") (dielectric_constraints yes))')
    marker='(setup\n'
    if marker not in text:raise ValueError('Missing board setup')
    text=text.replace('(paper "A4")','(paper "A3")',1).replace(marker,marker+'\n'.join(entries)+'\n',1)
    Path(path).write_text(text,encoding='utf-8',newline='\n')


def overlap(a,b,gap=0.):
    return a[0]<b[2]+gap and a[2]>b[0]-gap and a[1]<b[3]+gap and a[3]>b[1]-gap


def box_distance(a,b):
    return math.hypot(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))


def place_in_region(builder,ref,region,targets,*,angles=(0,90,180,270),side='F',step=.5,gap=.3,pad_gap=None):
    """Minimise weighted pad-to-anchor distance under real courtyard constraints.

    targets = [(own_pin, target_xy, weight)]. pad_gap(own_net, foreign_net)
    can enforce pair-specific insulation before native DRC. All vias/planes
    still need the separate routing/DRC check. No old design positions used.
    """
    import numpy as np
    b=builder;fp=b.fp[ref]
    x0,y0,x1,y1=region
    xs=np.arange(math.ceil(x0/step),math.floor(x1/step)+1)*step
    ys=np.arange(math.ceil(y0/step),math.floor(y1/step)+1)*step
    xx,yy=np.meshgrid(xs,ys);xx=xx.ravel();yy=yy.ravel();best=None
    foreign=[p for p in b.pads() if p['ref'] in b.placed and p['ref']!=ref] if pad_gap else []
    for angle in angles:
        b.place(ref,0,0,angle,side);local=b.box(ref)
        valid=(xx+local[0]>=x0)&(xx+local[2]<=x1)&(yy+local[1]>=y0)&(yy+local[3]<=y1)
        for other,p in b.placed.items():
            if other==ref:continue
            # A through-hole component has physical assembly occupancy on both sides.
            other_thru=any(pad.GetAttribute()!=b.pcb.PAD_ATTRIB_SMD for pad in b.fp[other].Pads())
            this_thru=any(pad.GetAttribute()!=b.pcb.PAD_ATTRIB_SMD for pad in fp.Pads())
            if p['side']!=side and not other_thru and not this_thru:continue
            box=p['bbox'];valid &= ~((xx+local[0]<box[2]+gap)&(xx+local[2]>box[0]-gap)&(yy+local[1]<box[3]+gap)&(yy+local[3]>box[1]-gap))
        cx,cy=xx[valid],yy[valid]
        if not len(cx):continue
        own=[p for p in b.pads() if p['ref']==ref]
        if pad_gap:
            mask=np.ones(len(cx),dtype=bool)
            for a in own:
                if not a['net']:continue
                for f in foreign:
                    if not f['net'] or a['net']==f['net']:continue
                    clearance=pad_gap(a['net'],f['net'])
                    if clearance<8 and not (set(a['layers'])&set(f['layers'])):continue
                    ab=a['box'];fb=f['box']
                    dx=np.maximum(np.maximum(cx+ab[0]-fb[2],fb[0]-(cx+ab[2])),0)
                    dy=np.maximum(np.maximum(cy+ab[1]-fb[3],fb[1]-(cy+ab[3])),0)
                    mask &= dx*dx+dy*dy >= (clearance+.03)**2
            cx,cy=cx[mask],cy[mask]
        if not len(cx):continue
        score=np.zeros(len(cx))
        for pin,target,weight in targets:
            px,py=b.xy(ref,pin)
            score+=weight*np.hypot(cx+px-target[0],cy+py-target[1])
        if not targets:score+=(cx-(x0+x1)/2)**2+(cy-(y0+y1)/2)**2
        j=int(np.argmin(score));candidate=(float(score[j]),float(cx[j]),float(cy[j]),angle)
        if best is None or candidate<best:best=candidate
    if best is None:
        b.placed.pop(ref,None)
        raise ValueError(('No feasible placement',ref,region))
    _,x,y,angle=best;b.place(ref,x,y,angle,side)
    return b.placed[ref]
