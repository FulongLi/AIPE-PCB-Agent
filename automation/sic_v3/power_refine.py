"""Repair power-board connectivity without relaxing voltage-domain rules."""
import argparse,json
from pathlib import Path
import pcbnew as pcb
from automation.sic_v3 import routing
from automation.sic_v3.model import power
from automation.sic_v3.schematics import power_domains
from automation.sic_v3.floorplan import pair_gap
from automation.kicad_tools.native_route_repair import connect_opens
from automation.kicad_tools.pad_escape_repair import reserve_escape
from automation.kicad_tools.project_board import place_in_region

WORK=Path('.aipe/v3/power')
POWER_NETS=['BUS','PGND','SW','VOUT','RAW']

def repair(source,report,output,all_taps=False):
    routing.WORK=WORK
    b=routing.wrapper(pcb.LoadBoard(str((WORK/f'sic-v3-power-{source}.kicad_pcb').resolve())),'power')
    data=json.loads(Path(report).read_text(encoding='utf-8'))
    # Only the short branch at the 0.65 mm output row needs a narrow neck.
    # The source row itself has 0.25 mm copper spacing by design.
    for t in b.board.GetTracks():
        if isinstance(t,pcb.PCB_VIA):continue
        a,z=pcb.ToMM(t.GetStart()),pcb.ToMM(t.GetEnd())
        if t.GetNetname() in ['VDD_H','VEE_H','VDD_L','VEE_L'] and t.GetLayer()==pcb.F_Cu and abs(a[1]-21.75)<.01 and abs(z[1]-21.75)<.01:
            t.SetWidth(pcb.FromMM(.25))
    domains=power_domains(power().parts);rules={}
    for n in b.nets:
        rules[n]=dict(width=.25)
        if n in domains and (n.endswith('_H') or n.startswith('H_')):rules[n]['region']=[[64,1.25,121.5,24.6]]
        elif n in domains and (n.endswith('_L') or n.startswith('L_')):rules[n]['region']=[[122,1.25,185.5,24.6]]
        elif n in domains and (n.startswith('S_') or n.endswith('ADCIN') or '_DIV' in n):rules[n]['region']=[[69,149,200,178.5]]
    result=connect_opens(b.board,data,width_mm=250,height_mm=180,layers=['F.Cu','In1.Cu','In2.Cu','B.Cu'],trace=.25,clearance=.25,via=(.8,.4),
        max_nodes=150000 if all_taps else 40000,max_tries=30 if all_taps else 8,net_rules=rules,skip_nets=() if all_taps else POWER_NETS,style_eps=.01,
        pair_clearance=lambda a,z:(pair_gap(domains,a,z),(a in domains)!=(z in domains)),
        allowed_layers=lambda n:(0,3) if n.startswith(('G_','KS_','OUTH_','OUTL_')) else (0,1,2,3) if n in domains else (0,2,3),
        progress=lambda result:routing.save(b,output,result))
    routing.save(b,output,result)

def reserve(source,report,output):
    routing.WORK=WORK
    b=routing.wrapper(pcb.LoadBoard(str((WORK/f'sic-v3-power-{source}.kicad_pcb').resolve())),'power')
    data=json.loads(Path(report).read_text(encoding='utf-8'));ds=power_domains(power().parts)
    items={i.m_Uuid.AsString():i for i in list(b.board.GetTracks())+[p for f in b.board.GetFootprints() for p in f.Pads()]}
    b.board.BuildConnectivity();seen=set();components=[]
    for issue in data['unconnected_items']:
        for item in issue['items']:
            a=items.get(item['uuid'])
            if a is None or a.GetNetname() in POWER_NETS:continue
            comp=list(b.board.GetConnectivity().GetConnectedItems(a));key=frozenset(t.m_Uuid.AsString() for t in comp)
            if key in seen:continue
            seen.add(key)
            if any(t.Type()==pcb.PCB_VIA_T or (isinstance(t,pcb.PAD) and t.GetAttribute()==pcb.PAD_ATTRIB_PTH) for t in comp):continue
            pads=[t for t in comp if isinstance(t,pcb.PAD)]
            pads.sort(key=lambda t:(not t.GetParentFootprint().GetReference().startswith('U'),t.GetParentFootprint().GetReference(),t.GetNumber()))
            components.append(pads)
    protected=['G_H','G_L','KS_H','KS_L','OUTH_H','OUTH_L','OUTL_H','OUTL_L','H_VEEA','L_VEEA','S_VEEA','VEE_H','VEE_L']
    records=[]
    for index,pads in enumerate(components):
        result=None
        for pad in pads[:4]:
            ref=pad.GetParentFootprint().GetReference();pin=pad.GetNumber();x,y=b.xy(ref,pin);cx,cy=pcb.ToMM(b.fp[ref].GetPosition())
            distances=[1,1.25,1.5,1.75,2,2.5,3,3.5,4.]
            directions=[(0,1 if y>cy else -1)] if ref.startswith('U') else [(1,0),(-1,0),(0,1),(0,-1)]
            candidates=[(round((x+dx*d+(shift if dy else 0))/.125)*.125,round((y+dy*d+(shift if dx else 0))/.125)*.125) for dx,dy in directions for d in distances for shift in [0,.125,-.125,.25,-.25]]
            result=reserve_escape(b,ref,pin,candidates,width=.25,diameter=.8,drill=.4,clearance=.25,protected_nets=protected,
                pair_clearance=lambda a,z:(pair_gap(ds,a,z),(a in ds)!=(z in ds)))
            if result['status']=='escape_reserved':break
        records.append(result);print('reserve',index,len(components),result,flush=True)
        routing.save(b,output,dict(reservations=records))

def relocate(source,output):
    routing.WORK=WORK
    b=routing.wrapper(pcb.LoadBoard(str((WORK/f'sic-v3-power-{source}.kicad_pcb').resolve())),'power');ds=power_domains(power().parts)
    for ref,fp in b.fp.items():
        x,y=pcb.ToMM(fp.GetPosition());b.placed[ref]=dict(x=x,y=y,angle=fp.GetOrientationDegrees(),side='B' if fp.IsFlipped() else 'F',bbox=b.box(ref))
    refs=['R28','C29','C30','C31','C32','C94','R13','R12','R18','C26','C55'];records=[]
    for ref in refs:
        x,y=pcb.ToMM(b.fp[ref].GetPosition());angle=b.fp[ref].GetOrientationDegrees();side='B' if b.fp[ref].IsFlipped() else 'F';region=[max(1,x-9),max(1,y-8),min(249,x+9),min(178,y+8)]
        targets=[]
        for pin,net in b.parts[ref]['nets'].items():
            matches=[q for rr,f in b.fp.items() if rr.startswith('U') for q in f.Pads() if q.GetNetname()==net]
            if matches:
                q=min(matches,key=lambda q:__import__('math').dist((x,y),pcb.ToMM(q.GetPosition())))
                targets.append((pin,pcb.ToMM(q.GetPosition()),10))
        try:
            place_in_region(b,ref,region,targets,side='B',step=.25,gap=.25,pad_gap=lambda a,z:pair_gap(ds,a,z),copper_gap=lambda a,z:pair_gap(ds,a,z))
            records.append(dict(ref=ref,status='relocated',pose=b.placed[ref]))
        except ValueError:
            # Restore this part if conservative search cannot find space.
            b.place(ref,x,y,angle,side);records.append(dict(ref=ref,status='no_candidate'))
        print(records[-1],flush=True);routing.save(b,output,dict(relocations=records))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',default='signals');p.add_argument('--report',default='.aipe/v3/power-signals-drc.json');p.add_argument('--output',default='repair1');p.add_argument('--reserve',action='store_true');p.add_argument('--relocate',action='store_true');p.add_argument('--all-taps',action='store_true');a=p.parse_args()
    if a.relocate:relocate(a.source,a.output)
    elif a.reserve:reserve(a.source,a.report,a.output)
    else:repair(a.source,a.report,a.output,a.all_taps)
