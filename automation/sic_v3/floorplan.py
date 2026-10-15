"""Independent V3 placement. Run under the installed KiCad Python.

Candidate B starts from the common thermal fixture and independent supports;
the A experiment is defined separately. No previous-generation coordinates
are loaded. All physical electrical spacing precedes routing.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from automation.sic_v3.model import power,control,EXAMPLE
from automation.sic_v3.schematics import power_domains
from automation.kicad_tools.project_board import ProjectBoard,place_in_region,overlap,box_distance

STACK_POWER=[('F.Cu','copper',.07),('dielectric 1','prepreg',.2),('In1.Cu','copper',.07),
             ('dielectric 2','core',1.32),('In2.Cu','copper',.07),('dielectric 3','prepreg',.2),('B.Cu','copper',.07)]
STACK_CONTROL=[('F.Cu','copper',.035),('dielectric 1','prepreg',.2),('In1.Cu','copper',.035),
               ('dielectric 2','core',1.06),('In2.Cu','copper',.035),('dielectric 3','prepreg',.2),('B.Cu','copper',.035)]


def save_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def pair_gap(domains,a,b):
    if a==b:return 0.
    if (a in domains)!=(b in domains):return 8.
    if a not in domains:return .25
    pa,pb=domains[a],domains[b]
    d=[(pa[k]-pb[k])*m for k,m in enumerate([500,500,250,500])]
    dv=max(abs(sum(x for x in d if x<0)),sum(x for x in d if x>0))+pa[4]+pb[4]
    return .25 if dv<=50 else .8 if dv<=160 else 1.6 if dv<=320 else 3.


def anchors(b,c,part):
    result=[];ref=part['ref'];group=c.groups.get(ref)
    for pin,net in part['nets'].items():
        if not net:continue
        matches=[]
        for other in b.placed:
            if other==ref:continue
            p=b.parts[other]
            same=c.groups.get(other)==group
            if not same and p['kind'] not in ['IC','DSP','Q','J']:continue
            if not same and net in ['GND_CTRL','3V3','5V','12V_E']:continue
            for q in b.fp[other].Pads():
                if q.GetNetname()==net:
                    matches.append((other,q,5 if same and p['kind']=='IC' else 2 if same else .2))
        # Avoid large multi-pin ground banks dominating one capacitor's location.
        byref={}
        for other,q,w in matches:byref.setdefault(other,[]).append((q,w))
        for other,items in byref.items():
            if part['kind']=='C' and len(part['nets'])==2 and b.parts[other]['kind']=='IC':
                other_net=next((n for n in part['nets'].values() if n!=net),None)
                partners=[q for q in b.fp[other].Pads() if q.GetNetname()==other_net]
                if partners:
                    import math
                    q,w=min(items,key=lambda item:min(math.dist(b.pcb.ToMM(item[0].GetPosition()),b.pcb.ToMM(p.GetPosition())) for p in partners))
                    result.append((pin,tuple(b.pcb.ToMM(q.GetPosition())),w*3));continue
            for q,w in items:result.append((pin,tuple(b.pcb.ToMM(q.GetPosition())),w/len(items)))
    return result


def power_floorplan(candidate='B'):
    c=power();b=ProjectBoard(EXAMPLE/'kicad/power_board','sic-v3-power',c.parts,EXAMPLE/'design/schematic_mapping_power.json',thickness=2.,stackup=STACK_POWER)
    b.outline([(0,0),(250,0),(250,180),(0,180)])
    fixed={
      'Q1':(105,14,0),'Q2':(130,14,0),
      'U1':(108,28.5,270),'U2':(133,28.5,270),'U3':(78,28,90),'U4':(170,28,90),
      'U5':(103,145,90),'U6':(125,145,90),'U7':(147,145,90),'U8':(177,145,270),
      'C1':(28,32,0),'C2':(28,57,0),'C3':(28,82,0),'C4':(28,107,0),
      'C13':(215,36,0),'C14':(215,80,0),
      'J1':(58,24,0),'J2':(58,47,0),'J3':(155,16,0),'J4':(216,116,0),'J5':(239,116,0),'J6':(14,147,0),
      'J7':(96,112,90),'H1':(6,6,0),'H2':(244,6,0),'H3':(6,174,0),'H4':(244,174,0),
      'R9':(112,19.75,90),'R10':(108,19.75,90),'R19':(137,19.75,90),'R20':(133,19.75,90),
      'D1':(91.5,23,90),'D3':(145.5,17,90),
      'NT1':(72.8,21.4,180),'NT2':(164.8,21.4,180),'NT3':(182.2,151.6,0),
    }
    if candidate=='A':
        # Opposed devices and drivers; two different thermal contact planes.
        # Coordinates are independently specified, not a scaled B floorplan.
        fixed.update(Q1=(105,35,90),Q2=(122,35,270),U1=(105,17,90),U2=(122,54,270),
            U3=(78,17,270),U4=(150,54,90),R9=(103,24.8,0),R10=(108,24.8,0),
            R19=(120,46.0,180),R20=(125,46.0,180),D1=(93,40,90),D3=(129,44.5,0),
            NT1=(83.2,23.6,0),NT2=(144.8,47.4,180),J3=(167,85,0))
    for ref,pose in fixed.items():b.place(ref,*pose)
    for k in range(8):
        if candidate=='B':b.place(f'C{k+5}',85+6.5*k,5.5,90,'B')
        else:b.place(f'C{k+5}',131+6.5*(k%4),27.5+9*(k//4),90,'B')
    domains=power_domains(c.parts)
    def region(p):
        group=c.groups.get(p['ref']);hv=any(n in domains for n in p['nets'].values() if n)
        if candidate=='A':
            if group in ['driver_H','desat_H']:return [86,24,114,50] if hv else [94,2,117,11]
            if group in ['driver_L','desat_L']:return [115,24,137,48] if hv else [113,60.5,138,85]
            if group=='bias_H':return [65,23.5,86,51] if hv else [65,2,92,11]
            if group=='bias_L':return [139,26,174,48] if hv else [140,60.5,180,81]
        if group in ['driver_H','desat_H']:return [89,2,120,22.5] if hv else [96,34.5,122,61]
        if group in ['driver_L','desat_L']:return [122,2,147,22.5] if hv else [124,34.5,150,61]
        if group=='bias_H':return [65,2,89,22.5] if hv else [65,34.5,94,65]
        if group=='bias_L':return [150,2,185,22.5] if hv else [153,34.5,185,65]
        if group=='voltage_RAW':return [70,152.5,113,177] if hv else [94,123,112,138.5]
        if group=='voltage_BUS':return [115,152.5,137,177] if hv else [116,123,134,138.5]
        if group=='voltage_OUT':return [139,152.5,160,177] if hv else [138,123,156,138.5]
        if group=='bias_S':return [162,151.5,199,177] if hv else [161,123,193,138.5]
        if group=='discharge':return [5,121,68,133] if p['ref'] in ['R1','R2','R3','R4'] else [190,131,242,143]
        if group=='cable':return [90,68,160,99]
        raise ValueError((p['ref'],group))
    pending=[p for p in c.parts if p['ref'] in b.fp and p['ref'] not in b.placed]
    def rank(p):
        # Local HF bypasses, then large parts, then the remaining signal network.
        box=b.box(p['ref']);area=(box[2]-box[0])*(box[3]-box[1])
        return (0 if p['kind']=='C' and p['value'].startswith('100n') else 1 if area>12 else 2,-area,p['ref'])
    pending.sort(key=rank)
    for index,p in enumerate(pending):
        place_in_region(b,p['ref'],region(p),anchors(b,c,p),step=.25,gap=.25,pad_gap=lambda a,z:pair_gap(domains,a,z))
        if index%20==0:print('placed power',candidate,index+1,'/',len(pending),p['ref'],flush=True)
    b.label('V3 POWER - 400V / 200V 5kW',(125,75),size=1.5)
    b.label('HAZARDOUS VOLTAGE - ENGINEERING REVIEW ONLY',(125,80),size=1.0)
    b.label('SELV HARNESS / NO GATE CURRENT',(125,104),size=1.)
    b.label('RELEASE BLOCKED',(125,86),size=1.)
    if candidate=='B':b.save()
    else:
        import shutil
        for ext in ['kicad_pro','kicad_dru']:
            shutil.copyfile(b.directory/(b.name+'.'+ext),b.directory/(b.name+'-A.'+ext))
        b.save(b.directory/(b.name+'-A.kicad_pcb'))
    out=EXAMPLE/'pcb/floorplan_candidates'
    b.save(out/f'power_{candidate}.kicad_pcb')
    save_json(out/f'power_{candidate}.json',dict(candidate=candidate,objective='Common thermal fixture, supported boards, compact local gate cells' if candidate=='B' else 'Opposed transistor stage with local external drivers; two thermal contact planes',
        width_mm=250,height_mm=180,layers=4,placements=b.placed,pads=b.pads()))
    print('Power',candidate,'placed',len(b.placed),flush=True)
    return b


def control_floorplan():
    c=control();b=ProjectBoard(EXAMPLE/'kicad/control_board','sic-v3-control',c.parts,EXAMPLE/'design/schematic_mapping_control.json',stackup=STACK_CONTROL)
    b.outline([(0,0),(160,0),(160,120),(0,120)])
    fixed=dict(U5=(85,67,180),U1=(25,19,0),U2=(40,21,0),L1=(51,21,0),U3=(64,28,90),U4=(62,43,0),
        J1=(10,16,0),J2=(52,44,0),Y1=(62,64,0),R24=(68.5,64.25,0),J3=(72,24,90),J4=(94,24,90),
        U6=(126,48,0),U7=(108,35,0),U8=(130,64,0),U9=(149,48,0),J5=(148,65,0),
        U10=(126,78,0),U11=(141,78,0),U12=(141,90,0),U13=(112,101,0),U14=(125,101,0),U15=(143,104,0),
        U16=(126,116,0),U17=(105,85,0),U18=(105,95,0),U19=(110,75,0),
        J6=(8,94,0),J7=(21,111,0),J8=(41,111,0),Q2=(23,88,0),Q3=(42,88,0),U20=(52,93,0),
        J9=(7,72,0),J10=(7,82,0),J11=(7,59,0),J12=(10,105,0),J13=(77,7,90),
        H1=(4,4,0),H2=(156,4,0),H3=(4,116,0),H4=(156,116,0))
    for ref,pose in fixed.items():b.place(ref,*pose)
    # Back-side per-pin capacitors are placed against the actual rotated DSP
    #pads, not the package centre. The final via/track length is audited later.
    bypass=[p for p in c.parts if 'near_dsp_pin' in p]
    for p in bypass:
        target=b.xy('U5',p['near_dsp_pin']);x,y=target
        place_in_region(b,p['ref'],[x-4,y-4,x+4,y+4],[('1',target,20)],side='B',step=.25,gap=.20)
    def region(p):
        group=c.groups.get(p['ref'])
        if group=='entry':return [3,5,35,38]
        if group=='buck':return [35,7,59,40]
        if group=='ldo':return [48,13,79,42]
        if group=='reset':return [48,38,70,51]
        if group=='pin_bypass':return [67,43,106,92]
        if group=='clock':return [57,46,107,94]
        if group=='debug':return [69,16,105,43]
        if group=='voltage_receive':return [108,20,155,58]
        if group=='current':return [117,58,158,72]
        if group=='adc':return [98,30,158,72]
        if group=='thresholds':return [113,70,158,100]
        if group=='logic':return [99,74,153,119]
        if group=='coil_supply':return [3,88,36,106]
        if group=='coils':return [18,76,60,119]
        if group=='feedback':return [3,65,50,85]
        if group=='thermal':return [3,51,30,63]
        if group=='cable':return [72,2,136,17]
        raise ValueError((p['ref'],group))
    pending=[p for p in c.parts if p['ref'] not in b.placed]
    def rank(p):
        box=b.box(p['ref']);area=(box[2]-box[0])*(box[3]-box[1])
        return (0 if p['kind']=='C' and p['value'].startswith('100n') else 1 if area>12 else 2,-area,p['ref'])
    pending.sort(key=rank)
    for index,p in enumerate(pending):
        targets=anchors(b,c,p)
        # ADC shunt and reference components belong at the receiving pin.
        for pin,net in p['nets'].items():
            if net and net.startswith('ADC'):
                for q in b.fp['U5'].Pads():
                    if q.GetNetname()==net:targets.append((pin,tuple(b.pcb.ToMM(q.GetPosition())),25))
        try:place_in_region(b,p['ref'],region(p),targets,step=.25,gap=.25)
        except ValueError:
            save_json(Path('.aipe/v3/control_failed.json'),dict(failed=p['ref'],placements=b.placed,pads=b.pads()))
            raise
        if index%25==0:print('placed control',index+1,'/',len(pending),p['ref'],flush=True)
    b.label('V3 F28335 CONTROL - ISOLATED DOMAIN',(80,113),size=1.2)
    b.label('ENGINEERING REVIEW - RELEASE BLOCKED',(80,118),size=.8)
    b.save()
    out=EXAMPLE/'pcb/floorplan_candidates'
    save_json(out/'control_B.json',dict(width_mm=160,height_mm=120,layers=4,placements=b.placed,pads=b.pads()))
    print('Control placed',len(b.placed),flush=True)
    return b


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--board',choices=['power','control'],default='power');ap.add_argument('--candidate',choices=['A','B'],default='B');args=ap.parse_args()
    if args.board=='power':power_floorplan(args.candidate)
    else:control_floorplan()


if __name__=='__main__':main()
