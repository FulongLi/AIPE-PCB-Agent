"""V3 routing from the committed native floorplans; never loads legacy CAD.

Run with KiCad's Python. Intermediate checkpoints remain under .aipe/v3;
only the final verified board is promoted to the editable project.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import pcbnew as pcb
from automation.sic_v3.model import EXAMPLE,control,power
from automation.kicad_tools.grid_router import Router
from automation.kicad_tools.project_board import ProjectBoard
from automation.kicad_tools.project_board import place_in_region
from automation.kicad_tools.qfp_escape import plan_dsp_escapes,row_axis
from automation.kicad_tools.pairwise_router import PairwiseRouter
from automation.sic_v3.floorplan import pair_gap
from automation.sic_v3.schematics import power_domains

WORK=Path('.aipe/v3');WORK.mkdir(parents=True,exist_ok=True)

def wrapper(board,which):
    b=ProjectBoard.__new__(ProjectBoard);b.pcb=pcb;b.board=board;b.stackup=None
    b.directory=EXAMPLE/'kicad'/f'{which}_board';b.name=f'sic-v3-{which}'
    b.fp={f.GetReference():f for f in board.GetFootprints()}
    b.nets={n.GetNetname():n for n in board.GetNetInfo().NetsByNetcode().values() if n.GetNetCode()}
    b.parts={p['ref']:p for p in (control() if which=='control' else power()).parts}
    b.placed={}
    return b

def load(which,checkpoint=None):
    source=Path(checkpoint) if checkpoint else EXAMPLE/'kicad'/f'{which}_board'/f'sic-v3-{which}.kicad_pcb'
    b=wrapper(pcb.LoadBoard(str(source.resolve())),which)
    if checkpoint is None:
        for t in list(b.board.GetTracks()):b.board.Remove(t)
        for z in list(b.board.Zones()):b.board.Remove(z)
    return b

def save(b,stage,report=None):
    path=WORK/f'{b.name}-{stage}.kicad_pcb';b.save(path)
    # Native DRC/zone fill must resolve the actual .pro/.dru and local libraries.
    import shutil
    for ext in ['kicad_pro','kicad_dru']:
        shutil.copyfile(b.directory/(b.name+'.'+ext),path.with_suffix('.'+ext))
    (WORK/'fp-lib-table').write_text((b.directory/'fp-lib-table').read_text(encoding='utf-8').replace('${KIPRJMOD}',b.directory.resolve().as_posix()),encoding='utf-8')
    if report is not None:path.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return path

def control_escapes():
    b=load('control');f=b.fp['U5'];pads=[]
    for p in f.Pads():
        if p.GetNetname() and not p.GetNetname().startswith('unconnected-'):
            pads.append(dict(number=p.GetNumber(),net=p.GetNetname(),xy=pcb.ToMM(p.GetPosition()),size=pcb.ToMM(p.GetSize())))
    escapes=plan_dsp_escapes(pads,pcb.ToMM(f.GetPosition()))
    # Clock has a short direct front-layer route; no DSP escape via.
    escapes=[e for e in escapes if e['net']!='CLK30']
    for e in escapes:
        b.track(e['net'],[e['pad'],e['via']],.2);b.via(e['net'],e['via'],.6,.3)
    # Place a small thermal via array only inside actual exposed lands. Tent
    # bottom; assembly stencil/fill must be agreed with the assembler.
    for ref,pin,nx,ny,pitch in [('U1','17',3,4,.8),('U3','29',6,3,.8)]:
        pad=b.pad(ref,pin);x,y=pcb.ToMM(pad.GetPosition())
        for i in range(nx):
            for j in range(ny):b.via(pad.GetNetname(),(x+(i-(nx-1)/2)*pitch,y+(j-(ny-1)/2)*pitch),.6,.3)
    # Escape-space refinement: preserve the floorplan snapshot, reposition
    #only the local DSP bypass/filter parts against the actual via geometry.
    #The early floorplan gate did not include escape copper.
    poses=json.loads((EXAMPLE/'pcb/floorplan_candidates/control_B.json').read_text())['placements']
    b.placed=dict(poses)
    bypass=[p for p in b.parts.values() if 'near_dsp_pin' in p]
    for p in bypass:b.placed.pop(p['ref'])
    groups=control().groups
    front=['C43','C44','C45','C46','C47','C48','R23','R24']+[ref for ref in b.parts if groups.get(ref)=='adc' and ref not in ['U9','C73']]
    for ref in front:b.placed.pop(ref,None)
    changed={}
    for p in bypass:
        target=next(e['via'] for e in escapes if e['number']==str(p['near_dsp_pin']))
        x,y=target
        place_in_region(b,p['ref'],[x-5,y-5,x+5,y+5],[('1',target,20)],side='B',step=.25,gap=.2,copper_gap=lambda a,z:.22)
        changed[p['ref']]=b.placed[p['ref']]
    for ref in front:
        pose=poses[ref];x,y=pose['x'],pose['y']
        targets=[]
        for pin,net in b.parts[ref]['nets'].items():
            if net in ['GND_CTRL','3V3']:continue
            for pad in b.fp['U5'].Pads():
                if pad.GetNetname()==net:targets.append((pin,pcb.ToMM(pad.GetPosition()),10))
        region=[101.5,40,121,73] if groups.get(ref)=='adc' else [x-6,y-6,x+6,y+6]
        place_in_region(b,ref,region,targets,step=.25,gap=.25,copper_gap=lambda a,z:.22)
        changed[ref]=b.placed[ref]
    save(b,'escapes',dict(escapes=escapes,escape_placement_refinements=changed))
    print('DSP escapes',len(escapes),flush=True)

def control_route():
    b=load('control',WORK/'sic-v3-control-escapes.kicad_pcb')
    es=json.loads((WORK/'sic-v3-control-escapes.json').read_text())['escapes']
    rails=['1V9','3V3','5V','12V_E','12V_IN','12V_COIL','MAIN_LOW','PRE_LOW']
    rules={n:dict(width=.4,fanout_width=.2) for n in rails}
    rules.update({n:dict(width=1.5,fanout_width=.3) for n in ['12V_COIL','MAIN_LOW','PRE_LOW']})
    rules['SW5']=dict(width=.7,fanout_width=.3)
    r=Router(b.board,160,120,['F.Cu','In2.Cu','B.Cu'],grid=.125,trace=.2,clearance=.2,via=(.6,.3),net_rules=rules,
        style=dict(diagonal=True,simplify='octilinear',arcs=True,eps=.02,via_cost_cells=18),max_nodes=500000)
    r.escape_distances=(.65,1.3,2.15,2.9,3.65,4.5,6.)
    for e in es:r.ports[e['net']].append((*r.to_grid(*e['via']),None,'U5',e['number']))
    # Outward-normal exact escapes are necessary for 0.65 mm SO rows. Side
    #classification from the package centre fails at the end of long packages.
    axes={ref:row_axis([dict(xy=pcb.ToMM(p.GetPosition())) for p in fp.Pads() if p.GetNumber() not in ['','17','29']]) for ref,fp in b.fp.items() if ref.startswith('U') and ref!='U5'}
    def exact(rec):
        ref=rec['ref'];axis=axes.get(ref)
        if axis and not rec['thru']:
            x,y=rec['xy'];cx,cy=pcb.ToMM(rec['fp'].GetPosition())
            return (.55,(1 if x>cx else -1,0)) if axis=='x' else (.55,(0,1 if y>cy else -1))
        return None
    r.stage='fanout'
    failures=r.fanout(skip=lambda q:(q['ref']=='U5' and q['net']!='CLK30') or (q['ref'],q['number']) in [('U1','17'),('U3','29')],
        exact=exact,direct=lambda q:q['net']!='GND_CTRL',exact_via=lambda q:q['net']=='GND_CTRL',direct_lane=.5)
    # Exposed thermal pads are already connected through their via arrays.
    for ref,pin in [('U1','17'),('U3','29')]:
        pad=b.pad(ref,pin);r.ports[pad.GetNetname()].append((*r.to_grid(*pcb.ToMM(pad.GetPosition())),None,ref,pin))
    print('Fanout failures',failures,flush=True)
    save(b,'fanout',r.report())
    first=['CLK_SRC','CLK30','BST5','SW5','FB5','FB19','ADCREFP','ADCREFM','ADCRESEXT','ADC_CURRENT','ADC_BUS','ADC_OUT','ADC_RAW','ADC_TEMP','ADC_IREF','ADC_V12',
           'EPWM_A','EPWM_B','ARMED','CURRENT_OK','PWM_H_SRC','PWM_L_SRC','PWM_H','PWM_L']
    order=list(dict.fromkeys(first+sorted([n for n in r.ports if n not in ['GND_CTRL','1V9','3V3']],key=lambda n:(r.net_span(n),n))))
    r.stage='signal'
    for i,net in enumerate(order):
        if net not in r.ports:continue
        r.recording_net=net
        failed=r.route_net(net,layers=(0,2),allow_front_fallback=net not in first[:5])
        r.recording_net=None
        print(i,net,'connections',len(r.ports[net]),'failed',len(failed),flush=True)
        if i%20==0:save(b,'routing',r.report())
    save(b,'signals',r.report())
    # All references on In1.Cu; core/IO distribution is handled separately
    #after the signal escape geometry is checked.
    r.zone_rect('GND_CTRL','In1.Cu',1,1,159,119,clearance=.2,min_thickness=.2)
    save(b,'routed',r.report())
    print('Routing unresolved',len(r.unresolved),flush=True)

def control_finish():
    b=load('control',WORK/'sic-v3-control-routed.kicad_pcb')
    old=json.loads((WORK/'sic-v3-control-routed.json').read_text())
    r=Router(b.board,160,120,['F.Cu','In2.Cu','B.Cu'],grid=.125,trace=.2,clearance=.2,via=(.6,.3),
        style=dict(diagonal=True,simplify='octilinear',arcs=True,eps=.03,via_cost_cells=18),max_nodes=1000000)
    r.stage='fanout';r.escape_distances=(.65,1.3,2.15,2.9,3.65,4.5,6.)
    fails=r.fanout(skip=lambda q:q['ref']=='U5' or (q['net'] not in ['1V9','3V3'] and (q['ref'],q['number'])!=('U12','4')))
    es=json.loads((WORK/'sic-v3-control-escapes.json').read_text())['escapes']
    for e in es:
        if e['net'] in ['1V9','3V3']:r.ports[e['net']].append((*r.to_grid(*e['via']),None,'U5',e['number']))
    print('Rail/ground fanout remaining',fails,flush=True)
    r.unresolved += [u for u in old['unresolved'] if u['stage']=='route']
    r.stage='retry';r.retry_unresolved((0,1,2))
    print('After signal retry',r.unresolved,flush=True)
    save(b,'signal-retry',r.report())
    r.stage='power'
    for n in ['1V9','3V3']:
        # Narrow terminal escapes above are .2 mm. Distribution starts at
        #through vias; inner copper will reinforce the connected network.
        r.net_rules[n]=dict(width=.4,fanout_width=.2)
        f=r.route_net(n,layers=(0,1,2));print('Rail',n,'failures',len(f),flush=True)
        save(b,'rails',r.report())
    r.zone_rect('1V9','In2.Cu',73,55,97,79,priority=2,clearance=.2,min_thickness=.2)
    r.zone_rect('3V3','In2.Cu',1,1,159,119,priority=1,clearance=.2,min_thickness=.2)
    save(b,'finished',r.report())

def fill_checkpoint(which,stage):
    path=(WORK/f'sic-v3-{which}-{stage}.kicad_pcb').resolve()
    board=pcb.LoadBoard(str(path));board.BuildConnectivity();pcb.ZONE_FILLER(board).Fill(board.Zones());pcb.SaveBoard(str(path),board,True)
    print('Stored native zone fill',path,flush=True)

def power_route(only_fanout=False):
    b=load('power');domains=power_domains(power().parts)
    # Route-driven refinement: align turn-on/turn-off resistors to their
    #driver pins and place the HF supply bypasses behind the output bank.
    for tag,u,q,ron,roff,cp,cn,dx in [('H','U1','Q1','R9','R10','C21','C22',0),('L','U2','Q2','R19','R20','C33','C34',25)]:
        # Look up the bypass references by net/value instead of assuming the
        #opposite channel's sequential numbering.
        cands=[p for p in b.parts.values() if p['kind']=='C' and p['value'].startswith('100n') and p['nets'].get('1')=='VDD_'+tag and p['nets'].get('2')=='KS_'+tag]
        cp=cands[0]['ref']
        cands=[p for p in b.parts.values() if p['kind']=='C' and p['value'].startswith('100n') and p['nets'].get('1')=='KS_'+tag and p['nets'].get('2')=='VEE_'+tag]
        cn=cands[0]['ref']
        b.place(ron,108.635+dx,19.75,90);b.place(roff,106.095+dx,19.75,90)
        b.place(cp,107.365+dx,20,90,'B');b.place(cn,103.555+dx,20,270,'B')
        for pin,res in [('4',ron),('6',roff)]:b.track(b.pad(u,pin).GetNetname(),[b.xy(u,pin),b.xy(res,1)],.4)
        g='G_'+tag
        b.track(g,[b.xy(u,7),(104.825+dx,22.8),(104.65+dx,22.625),(104.65+dx,18.2875),b.xy(roff,2)],.25)
        b.track(g,[b.xy(roff,2),b.xy(ron,2),(110.08+dx,16.8425),b.xy(q,4)],.4)
        for pin,net in [('3','KS_'+tag),('5','VDD_'+tag),('8','VEE_'+tag)]:
            x,y=b.xy(u,pin);v=(x,22.5)
            b.track(net,[(x,y),v],.35);b.via(net,v)
        b.track('KS_'+tag,[(109.905+dx,22.5),(110.755+dx,21.65),(110.755+dx,18.),(107.54+dx,18.),b.xy(q,3)],.5,'B.Cu')
    for nt,x,y,angle in [('NT1',72.4,21.4,180),('NT2',164.4,21.4,180),('NT3',182.6,151.6,0)]:b.place(nt,x,y,angle)
    # VEEA has one explicit quiet connection to pin 36 through the schematic
    #net tie. Load and capacitor returns use the other VEE terminals.
    for u,nt,sign in [('U3','NT1',-1),('U4','NT2',-1),('U8','NT3',1)]:
        for pin,tie_pin in [('35','1'),('36','2')]:
            a=b.xy(u,pin);z=b.xy(nt,tie_pin)
            start=(a[0],a[1]+sign*.35)
            if pin=='35':points=[start,(a[0],z[1]-sign*abs(z[0]-a[0])),z]
            else:
                bend=(a[0],a[1]+sign*.625)
                points=[start,bend,(z[0],bend[1]+sign*abs(z[0]-a[0])),z]
            b.track(b.pad(u,pin).GetNetname(),points,.25)
    rules={}
    for tag in ['H','L']:
        for n in ['G_','KS_','OUTH_','OUTL_']:rules[n+tag]=dict(width=.35,fanout_width=.25)
        for n in ['VDD_','VEE_']:rules[n+tag]=dict(width=.4,fanout_width=.25)
    for n in ['12V_E','3V3','GND_CTRL','GNDP_H','GNDP_L','GNDP_S','12V_H_BIAS','12V_L_BIAS','12V_S_BIAS']:
        rules[n]=dict(width=.5,fanout_width=.25)
    # Gate/supply/feedback loops must not escape around the board perimeter
    #just because a global connectivity search can find such a path.
    for n in b.nets:
        if n in domains and (n.endswith('_H') or n.startswith('H_')):
            rules.setdefault(n,{})['region']=[[64,1.25,121.5,24.6]]
        elif n in domains and (n.endswith('_L') or n.startswith('L_')):
            rules.setdefault(n,{})['region']=[[122,1.25,185.5,24.6]]
        elif n in domains and (n.startswith('S_') or n.endswith('ADCIN') or '_DIV' in n):
            rules.setdefault(n,{})['region']=[[69,149,200,178.5]]
    r=PairwiseRouter(b.board,250,180,['F.Cu','In1.Cu','In2.Cu','B.Cu'],grid=.125,trace=.25,clearance=.25,via=(.8,.4),
        net_rules=rules,pair_clearance=lambda a,z:(pair_gap(domains,a,z),(a in domains)!=(z in domains)),
        style=dict(diagonal=True,simplify='octilinear',arcs=False,eps=.025,via_cost_cells=30,heuristic_weight=1.1),max_nodes=120000)
    power_nets=['BUS','PGND','SW','VOUT','RAW']
    def exact(q):
        if q['ref'].startswith('U'):
            x,y=q['xy'];cx,cy=pcb.ToMM(q['fp'].GetPosition())
            return (.35,(0,1 if y>cy else -1))
        return None
    r.stage='fanout'
    failures=r.fanout(skip=lambda q:q['net'] in power_nets or (q['ref'] in ['U3','U4','U8'] and q['number'] in ['35','36']),
        exact=exact,direct=lambda q:True,direct_lane=0)
    # Register already wired star anchors instead of pin-row ports.
    for nt in ['NT1','NT2','NT3']:
        for p in b.fp[nt].Pads():r.ports[p.GetNetname()].append((*r.to_grid(*pcb.ToMM(p.GetPosition())),0,nt,p.GetNumber()))
    print('Power fanout failures',failures,flush=True)
    save(b,'fanout',r.report())
    if only_fanout:return
    first=['OUTH_H','OUTL_H','OUTH_L','OUTL_L','G_H','G_L','KS_H','KS_L',
        'H_VEEA','L_VEEA','S_VEEA','H_FBVDD','H_FBVEE','L_FBVDD','L_FBVEE','S_FBVDD','S_FBVEE',
        'VDD_H','VEE_H','VDD_L','VEE_L','OC_H','OC_L','DESAT_H','DESAT_L','H_RLIM','L_RLIM','S_RLIM']
    order=list(dict.fromkeys(first+sorted([n for n in r.ports if n not in power_nets],key=lambda n:(r.net_span(n),n))))
    for i,n in enumerate(order):
        if n not in r.ports:continue
        r.stage='critical' if i<len(first) else 'signal';r.recording_net=n
        layer=(0,) if n in first[:6] else (0,3) if n in domains else (0,2,3)
        failed=r.route_net(n,layers=layer,allow_front_fallback=n not in domains);r.recording_net=None
        print(i,n,'ports',len(r.ports[n]),'failures',len(failed),flush=True)
        if i%8==0:save(b,'routing',r.report())
    save(b,'signals',r.report())
    print('Power signal unresolved',len(r.unresolved),flush=True)

def main():
    global WORK
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['control-escapes','control-route','control-finish','control-fill','power-route','power-fanout'],required=True);a=ap.parse_args()
    if a.stage.startswith('power'):WORK=WORK/'power';WORK.mkdir(exist_ok=True)
    {'control-escapes':control_escapes,'control-route':control_route,'control-finish':control_finish,'control-fill':lambda:fill_checkpoint('control','finished'),'power-route':power_route,'power-fanout':lambda:power_route(True)}[a.stage]()

if __name__=='__main__':main()
