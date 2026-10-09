"""Deterministic functional placement for the integrated six-layer prototype."""
from __future__ import annotations

import json
import math
import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from automation.kicad_tools.buck_model import build,EXAMPLE
from automation.kicad_tools.buck_footprints import prepare
from automation.setup.detect_kicad import find_kicad_cli

NAME='AIPE_Buck_1kW'
WIDTH,HEIGHT=300.0,220.0


def generate():
    import pcbnew as pcb
    import numpy as np
    prepare()
    parts=build().parts
    mapping=json.loads((EXAMPLE/'design/schematic_mapping.json').read_text())['paths']
    board=pcb.BOARD();board.SetCopperLayerCount(6)
    board.GetDesignSettings().SetBoardThickness(pcb.FromMM(2.0))
    netlist=EXAMPLE/'verification/schematic_netlist.xml'
    netlist.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(find_kicad_cli()),'sch','export','netlist','--format','kicadxml','--output',str(netlist),str(EXAMPLE/'kicad'/(NAME+'.kicad_sch'))],check=True,capture_output=True)
    tree=ET.parse(netlist).getroot()
    cad_pin_nets={(node.attrib['ref'],node.attrib['pin']):net.attrib['name'] for net in tree.findall('nets/net') for node in net.findall('node')}
    nets={}
    for name in sorted(set(cad_pin_nets.values())):
        net=pcb.NETINFO_ITEM(board,name); board.Add(net);nets[name]=net

    def point(x,y): return pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y))

    footprints={}; byref={p['ref']:p for p in parts}
    for p in parts:
        lib,name=p['footprint'].split(':')
        fp=pcb.FootprintLoad(str(EXAMPLE/'kicad/libraries'/(lib+'.pretty')),name)
        if fp is None:raise ValueError(p['footprint'])
        fp.SetFPID(pcb.LIB_ID(lib,name)); fp.SetReference(p['ref']);fp.SetValue(p['value'])
        fp.SetPath(pcb.KIID_PATH(mapping[p['ref']]))
        fp.Value().SetVisible(False)
        fp.Reference().SetLayer(pcb.F_Fab)
        fp.Reference().SetTextSize(point(1,1));fp.Reference().SetTextThickness(pcb.FromMM(0.15))
        # Package drawings remain unchanged. Electrical pad mapping is explicit.
        seen=set()
        for pad in fp.Pads():
            n=pad.GetNumber()
            if not n:continue
            if n not in p['nets']:raise ValueError((p['ref'],'unexpected pad',n))
            seen.add(n)
            if (p['ref'],n) in cad_pin_nets:pad.SetNet(nets[cad_pin_nets[p['ref'],n]])
        if seen != set(p['nets']):raise ValueError((p['ref'],'missing pads',set(p['nets'])-seen))
        board.Add(fp); footprints[p['ref']]=fp

    occupied=[]; placements={}
    def bounds(fp):
        hull=fp.GetBoundingHull()
        box=hull.BBox()
        return [pcb.ToMM(box.GetX()),pcb.ToMM(box.GetY()),pcb.ToMM(box.GetRight()),pcb.ToMM(box.GetBottom())]

    def overlaps(a,b,gap=0.5):
        return a[0]<b[2]+gap and a[2]>b[0]-gap and a[1]<b[3]+gap and a[3]>b[1]-gap

    def place(ref,x,y,angle=0,check=True):
        fp=footprints[ref]; fp.SetOrientationDegrees(angle);fp.SetPosition(point(x,y))
        bb=bounds(fp)
        if check:
            for other,box in occupied:
                if overlaps(bb,box):raise ValueError(('placement overlap',ref,other,bb,box))
        placements[ref]=dict(x=x,y=y,angle=angle,bbox=bb)
        occupied.append((ref,bb))
        return bb

    fixed={'J1':(15,15),'J2':(12,104),'J3':(280,40),'J4':(280,90),
        'F1':(55,15),'D1':(84,15),'Q1':(112,42),'Q2':(126,42),
        'Q3':(112,55),'Q4':(126,55),'L1':(165,45),'R9':(207,45),
        'U1':(123,48.1),'U2':(34,143),'U3':(81,143),'U4':(125,143),
        'U5':(147,131),'U6':(210,68),'U7':(128,62),'U8':(223,124),
        'U9':(251,139),'U10':(256,157),'U11':(274,157),
        'U12':(126,91),'U13':(143,89),'U14':(143,97),'U15':(126,101),
        'U16':(181,173),'Y1':(206,172),
        'R1':(109,46),'R2':(107.5,50),'R3':(135,46),'R4':(137,50),
        'R5':(109,59),'R6':(107.5,63),'R7':(135,59),'R8':(137,63),
        'C27':(111,78),'C28':(121,78),
        'L2':(47,146),'L3':(93,146),
        'J5':(151,145),'J6':(275,140),'J7':(221,191),'J8':(240,206),'J9':(270,206)}
    # Verify device identities before relying on these physical anchors.
    assert byref['U16']['kind']=='DSP' and byref['U6']['mpn']=='INA240A1DR'
    assert byref['U7']['mpn'].startswith('LM61') and byref['U15']['mpn'].startswith('SN74LVC2G08')
    for ref,xy in fixed.items():place(ref,*xy,angle=90 if ref in {f'R{i}' for i in range(1,9)} else 0)
    for i in range(14):
        col=i%4;row=i//4
        place('C'+str(i+1),30+col*21,39+row*21)
    for i in range(8):place('C'+str(15+i),109+(i%4)*7,31 if i<4 else 71)
    for i in range(4):place('C'+str(23+i),237+(i%2)*23,32+(i//2)*25)
    holes=[(4,4),(295,5),(5,215),(150,215),(295,215),(136,24),(193,24),(165,76)]
    for i,xy in enumerate(holes,1):place('H'+str(i),*xy)

    # Each partition has clear physical intent. Candidates minimize pin-to-pin
    # connection length inside that partition while respecting courtyards.
    regions={
        '02_capacitors':(18,113,98,124),
        '03_gate':(103,26,142,80),
        '04_aux12':(18,128,67,171),
        '05_aux5':(70,128,108,176),
        '06_dsp_supplies':(112,118,157,165),
        '07_sensing':(203,68,247,145),
        '08_protection':(243,130,288,187),
        '09_pwm_logic':(108,80,156,110),
        '11_dsp_decoupling':(156,147,207,200),
        '12_clock_debug':(152,152,248,211),
        '13_testpoints':(18,181,288,211),
    }
    def anchors(part):
        result=[]
        for n in part['nets'].values():
            if not n or n=='GND':continue
            for ref in placements:
                other=byref[ref]
                if n not in other['nets'].values():continue
                # IC supply pin dominates bypass location; other rails must not
                # pull a control capacitor back into the power section.
                if other['page']!=part['page'] and part['kind']!='TP':continue
                for pad in footprints[ref].Pads():
                    if pad.GetNetname()==n:
                        x,y=pcb.ToMM(pad.GetPosition())
                        result.append((x,y,4 if other['kind'] in ('IC','DSP') else 1))
        return result

    # Dedicated supply-pin bypass placement before ordinary passives.
    remaining=[p for p in parts if p['ref'] not in placements]
    remaining.sort(key=lambda p:(0 if 'near_dsp_pin' in p else 1 if p['kind']=='C' else 2, -len(p['pins'])))
    for p in remaining:
        region=regions[p['page']];x0,y0,x1,y1=region
        fp=footprints[p['ref']]
        targets=anchors(p)
        if 'near_dsp_pin' in p:
            pad=next(pad for pad in footprints['U16'].Pads() if pad.GetNumber()==p['near_dsp_pin'])
            tx,ty=pcb.ToMM(pad.GetPosition());targets=[(tx,ty,10)]
        if not targets:targets=[((x0+x1)/2,(y0+y1)/2,1)]
        candidates=[]
        for angle in (0,90):
            fp.SetOrientationDegrees(angle);fp.SetPosition(point(0,0));local=bounds(fp)
            xs=np.arange(math.ceil(x0*2),math.floor(x1*2)+1)/2
            ys=np.arange(math.ceil(y0*2),math.floor(y1*2)+1)/2
            xx,yy=np.meshgrid(xs,ys);xx=xx.ravel();yy=yy.ravel()
            valid=(xx+local[0]>=x0)&(xx+local[2]<=x1)&(yy+local[1]>=y0)&(yy+local[3]<=y1)
            for _,box in occupied:
                valid &= ~((xx+local[0]<box[2]+0.5)&(xx+local[2]>box[0]-0.5)&(yy+local[1]<box[3]+0.5)&(yy+local[3]>box[1]-0.5))
            xx=xx[valid]; yy=yy[valid]
            if not len(xx):continue
            scores=sum(w*(np.abs(xx-tx)+np.abs(yy-ty)) for tx,ty,w in targets)/sum(t[2] for t in targets)
            best=int(np.argmin(scores));candidates.append((float(scores[best]),float(xx[best]),float(yy[best]),angle))
        if not candidates:raise RuntimeError(('No placement space',p['ref'],p['page']))
        _,x,y,angle=min(candidates)
        place(p['ref'],x,y,angle)

    for a,b in [((0,0),(WIDTH,0)),((WIDTH,0),(WIDTH,HEIGHT)),((WIDTH,HEIGHT),(0,HEIGHT)),((0,HEIGHT),(0,0))]:
        edge=pcb.PCB_SHAPE(board);edge.SetShape(pcb.SHAPE_T_SEGMENT);edge.SetStart(point(*a));edge.SetEnd(point(*b));edge.SetLayer(pcb.Edge_Cuts);edge.SetWidth(pcb.FromMM(0.05));board.Add(edge)
    def text(value,x,y,size=1.2,layer=pcb.F_SilkS):
        item=pcb.PCB_TEXT(board);item.SetText(value);item.SetPosition(point(x,y));item.SetTextSize(point(size,size));item.SetTextThickness(pcb.FromMM(0.18));item.SetLayer(layer);board.Add(item)
    text('AIPE 48V > 24V / 1kW',202,16,2)
    text('V1 - HUMAN REVIEW REQUIRED',231,22,1.3)
    text('AI-GENERATED ENGINEERING PROTOTYPE',79,207,1.1)
    text('INPUT 36-54V',32,7,1)
    text('OUTPUT 24V / 41.7A',266,18,1)
    text('POWER / HOT',183,91,1.2)
    text('CONTROL',180,130,1.2)
    for label,x,y in [('VIN+',15,5.8),('VIN-',12,117),('VOUT+',282,54),('VOUT-',282,104),
                      ('JTAG',230,200),('BOOT',240,214),('UART 3V3',276,214),('RESET',156,152),('STOP',282,145)]:
        text(label,x,y,1.0)
    for ref,record in placements.items():
        fp=footprints[ref]
        # Silkscreen labels outside component bodies are finalized after routing.
        fp.Reference().SetTextAngle(pcb.EDA_ANGLE(0,pcb.DEGREES_T))
    path=EXAMPLE/'kicad'/(NAME+'.kicad_pcb')
    board.BuildConnectivity();pcb.SaveBoard(str(path),board)
    # pcbnew does not expose stackup mutation in this build; edit documented
    # native stackup syntax then let the official parser load it for validation.
    copper=[('F.Cu',0.07),('In1.Cu',0.035),('In2.Cu',0.07),('In3.Cu',0.07),('In4.Cu',0.035),('B.Cu',0.07)]
    dielectrics=[0.18,0.30,0.69,0.30,0.18]
    stack=[]
    for i,(layer,thickness) in enumerate(copper):
        stack.append(f'(layer "{layer}" (type "copper") (thickness {thickness}))')
        if i<5:stack.append(f'(layer "dielectric {i+1}" (type "{ "core" if i in (1,3) else "prepreg" }") (thickness {dielectrics[i]}) (material "FR4") (epsilon_r 4.3) (loss_tangent 0.02))')
    native=path.read_text(encoding='utf8')
    native=native.replace('(setup\n','(setup\n (stackup\n'+'\n'.join(stack)+'\n(copper_finish "ENIG") (dielectric_constraints no))\n',1)
    path.write_text(native,encoding='utf8')
    loaded=pcb.LoadBoard(str(path));assert loaded.GetCopperLayerCount()==6
    (EXAMPLE/'design/placement.json').write_text(json.dumps(dict(board_mm=[WIDTH,HEIGHT],items=placements),indent=2)+'\n')
    geometry={}
    for fp in loaded.GetFootprints():
        geometry[fp.GetReference()]={'position':list(pcb.ToMM(fp.GetPosition())), 'pads':[
            {'number':p.GetNumber(),'net':p.GetNetname(),'xy':list(pcb.ToMM(p.GetPosition())),
             'size':list(pcb.ToMM(p.GetSize())),'drill':list(pcb.ToMM(p.GetDrillSize())),
             'angle':p.GetOrientationDegrees(),'type':int(p.GetAttribute()),'shape':int(p.GetShape())} for p in fp.Pads()]}
    (EXAMPLE/'design/board_geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
    print(f'Placed {len(placements)} items on {WIDTH} x {HEIGHT} mm / 6 layers. Routing pending.')


if __name__=='__main__':generate()
