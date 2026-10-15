"""Replayable control routing refinements, preserving the global signal plan."""
import argparse,json
import pcbnew as pcb
from automation.sic_v3.routing import wrapper,save,WORK,fill_checkpoint
from automation.kicad_tools.grid_router import Router
from automation.kicad_tools.native_route_repair import connect_opens
from automation.kicad_tools.pad_escape_repair import reserve_escape
from automation.kicad_tools.project_board import place_in_region

def refine():
    b=wrapper(pcb.LoadBoard(str(WORK/'sic-v3-control-repair1.kicad_pcb')),'control')
    removed=[];retained=[]  # Keep detached SWIG wrappers alive through SaveBoard.
    for t in list(b.board.GetTracks()):
        n=t.GetNetname()
        if n=='E_DVDT' or (n=='E_RTN' and not isinstance(t,pcb.PCB_VIA)):
            removed.append(t.m_Uuid.AsString());retained.append(t);b.board.Remove(t)
        elif n=='5V' and not isinstance(t,pcb.PCB_VIA):
            a,z=pcb.ToMM(t.GetStart()),pcb.ToMM(t.GetEnd())
            if min(__import__('math').dist(x,(56.125,94.25)) for x in [a,z])<.9:t.SetWidth(pcb.FromMM(.2))
    r=Router(b.board,160,120,['F.Cu','In2.Cu','B.Cu'],grid=.125,trace=.2,clearance=.2,via=(.6,.3),
        style=dict(diagonal=True,eps=.03,via_cost_cells=18),max_nodes=40000)
    target={('U1',n) for n in ['5','8','10','11','12','14']}|{('U2','5'),('U12','4'),('U13','9'),('U14','5'),('U14','14'),('U17','6'),('U18','4'),('U19','6'),('U19','8'),('R28','1')}
    r.stage='fanout'
    fail=r.fanout(skip=lambda q:(q['ref'],q['number']) not in target and q['net'] not in ['E_RTN','E_DVDT'],
        inward=lambda q:q['ref'] not in ['U1','U2'],inpad_vias=())
    print('Refined fanout failures',fail,flush=True)
    for n in ['E_RTN','E_DVDT']:
        # Include exposed-pad vias as ground-return anchors.
        for t in b.board.GetTracks():
            if isinstance(t,pcb.PCB_VIA) and t.GetNetname()==n:r.ports[n].append((*r.to_grid(*pcb.ToMM(t.GetPosition())),None,'EXISTING',''))
        r.stage='signal';r.route_net(n,layers=(0,1,2))
    save(b,'refine',dict(removed_rerouted_items=removed,router=r.report()))

def repair(source,report,output):
    b=wrapper(pcb.LoadBoard(str(WORK/f'sic-v3-control-{source}.kicad_pcb')),'control')
    data=json.loads((WORK/report).read_text(encoding='utf-8'))
    r=connect_opens(b.board,data,width_mm=160,height_mm=120,layers=['F.Cu','In2.Cu','B.Cu'],max_nodes=150000,max_tries=30,net_rules={'SW5':dict(width=.7)},
        progress=lambda result:save(b,output,result))
    save(b,output,r)

def prune(source,output):
    import subprocess
    from automation.kicad_tools.native_route_repair import prune_native_dangling
    b=wrapper(pcb.LoadBoard(str((WORK/f'sic-v3-control-{source}.kicad_pcb').resolve())),'control');save(b,output)
    records=[];history=[b];cli=r'D:\EngineeringTools\KiCad\10.0\bin\kicad-cli.exe'
    for step in range(50):
        fill_checkpoint('control',output)
        path=(WORK/f'sic-v3-control-{output}.kicad_pcb').resolve();report=(WORK/f'control-{output}-drc.json').resolve()
        subprocess.run([cli,'pcb','drc','--format','json','--severity-all','--output',str(report),str(path)],check=True,capture_output=True)
        data=json.loads(report.read_text(encoding='utf8'));b=wrapper(pcb.LoadBoard(str(path)),'control');history.append(b)
        b._detached=prune_native_dangling(b.board,data,vias=not data['unconnected_items'])
        records.append(dict(pass_index=step,removed=len(b._detached),opens=len(data['unconnected_items'])))
        print(records[-1],flush=True)
        if not b._detached:break
        save(b,output,dict(pruning=records))

def reserve(second=False):
    b=wrapper(pcb.LoadBoard(str(WORK/('sic-v3-control-reserved.kicad_pcb' if second else 'sic-v3-control-refine.kicad_pcb'))),'control');records=[]
    pins=[('U19','8'),('U19','6'),('U17','6'),('U18','4'),('U14','14'),('U14','5'),('U13','9'),('U12','4'),('U1','14'),('U1','11'),('U1','10'),('U1','5'),('U2','5'),('R28','1')]
    if second:
        pins=[('U1','14'),('U1','11'),('U1','10'),('U1','5'),('U14','14'),('U14','5'),('U13','9'),('R28','1')]
        b._detached=[]
        for t in list(b.board.GetTracks()):
            n=t.GetNetname();x,y=pcb.ToMM(t.GetPosition())
            thermal=isinstance(t,pcb.PCB_VIA) and 23.5<x<26.5 and 16.5<y<21.5
            if n in ['E_RTN','E_DVDT'] and not thermal:b._detached.append(t);b.board.Remove(t)
        for ref,fp in b.fp.items():
            x,y=pcb.ToMM(fp.GetPosition());b.placed[ref]=dict(x=x,y=y,angle=fp.GetOrientationDegrees(),side='B' if fp.IsFlipped() else 'F',bbox=b.box(ref))
        place_in_region(b,'C1',[30,8,35,29],[('1',b.xy('U1','12'),10)],gap=.25,copper_gap=lambda a,z:.2,step=.25)
    for ref,pin in pins:
        x,y=b.xy(ref,pin);cx,cy=pcb.ToMM(b.fp[ref].GetPosition())
        sign=1 if x>cx else -1
        distances=[1.1,1.25,1.4,1.6,1.85,2.1,2.4,2.7,3.0]
        sense=sign if ref in ['U1','U2','R28'] else -sign
        candidates=[(round((x+s*d)/.125)*.125,round((y+shift)/.125)*.125) for s in ([sense,-sense] if second else [sense]) for d in distances for shift in [0,.125,-.125,.25,-.25]]
        if ref=='R28':candidates += [(round((x+shift)/.125)*.125,round((y+s*d)/.125)*.125) for s in [-1,1] for d in distances for shift in [0,.125,-.125]]
        result=reserve_escape(b,ref,pin,candidates);records.append(result);print(result,flush=True)
        save(b,'reserved2' if second else 'reserved',dict(reserved=records))

def reserve3():
    b=wrapper(pcb.LoadBoard(str((WORK/'sic-v3-control-repair3.kicad_pcb').resolve())),'control');records=[]
    for ref,fp in b.fp.items():
        x,y=pcb.ToMM(fp.GetPosition());b.placed[ref]=dict(x=x,y=y,angle=fp.GetOrientationDegrees(),side='B' if fp.IsFlipped() else 'F',bbox=b.box(ref))
    for ref,region,targets in [('C2',[12,10,22,23],[('1',b.xy('U1','1'),10)]),('R28',[60,65,72,78],[('2',b.xy('U5','87'),10)])]:
        place_in_region(b,ref,region,targets,side='B' if ref=='C2' else 'F',gap=.25,copper_gap=lambda a,z:.2,step=.25)
        records.append(dict(ref=ref,status='relocated',pose=b.placed[ref]))
    for ref,pin in [('U1','5'),('U1','12'),('R28','1'),('R28','2'),('C2','1'),('C2','2')]:
        x,y=b.xy(ref,pin);cx,cy=pcb.ToMM(b.fp[ref].GetPosition());sign=1 if x>cx else -1
        candidates=[(round((x+sign*d)/.125)*.125,round((y+shift)/.125)*.125) for d in [.9,1.1,1.3,1.6,1.9,2.2,2.6,3.,3.5] for shift in [0,.125,-.125,.25,-.25]]
        if ref not in ['U1']:
            candidates += [(round((x+shift)/.125)*.125,round((y+s*d)/.125)*.125) for s in [-1,1] for d in [.9,1.1,1.3,1.6,2,2.5] for shift in [0,.125,-.125]]
        result=reserve_escape(b,ref,pin,candidates);records.append(result);print(result,flush=True)
    save(b,'reserved3',dict(reserved=records))

def reserve4():
    b=wrapper(pcb.LoadBoard(str((WORK/'sic-v3-control-repair4.kicad_pcb').resolve())),'control');b._detached=[]
    for t in list(b.board.GetTracks()):
        if isinstance(t,pcb.PCB_VIA) and t.GetNetname()=='E_ILIM' and __import__('math').dist(pcb.ToMM(t.GetPosition()),(28.875,19.125))<.01:
            b._detached.append(t);b.board.Remove(t)
    x,y=b.xy('U1','12')
    candidates=[(round((x+d)/.125)*.125,round((y+s)/.125)*.125) for d in [.9,1.1,1.4,1.8,2.2,2.6,3,3.5] for s in [0,.125,-.125,.25,-.25]]
    result=reserve_escape(b,'U1','12',candidates);print(result,flush=True);save(b,'reserved4',result)

def reserve5():
    b=wrapper(pcb.LoadBoard(str((WORK/'sic-v3-control-repair6.kicad_pcb').resolve())),'control');records=[]
    for ref,pin in [('U14','6'),('D7','1')]:
        x,y=b.xy(ref,pin)
        candidates=[(round((x+dx*d+(s if dy else 0))/.125)*.125,round((y+dy*d+(s if dx else 0))/.125)*.125) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)] for d in [.9,1.1,1.3,1.6,1.9,2.2,2.6,3] for s in [0,.125,-.125]]
        result=reserve_escape(b,ref,pin,candidates);records.append(result);print(result,flush=True)
    save(b,'reserved5',dict(reserved=records))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['refine','repair','fill','reserve','reserve2','reserve3','reserve4','reserve5','prune']);p.add_argument('--source');p.add_argument('--report');p.add_argument('--output');a=p.parse_args()
    if a.mode=='refine':refine()
    elif a.mode=='repair':repair(a.source,a.report,a.output)
    elif a.mode=='reserve':reserve()
    elif a.mode=='reserve2':reserve(True)
    elif a.mode=='reserve3':reserve3()
    elif a.mode=='reserve4':reserve4()
    elif a.mode=='reserve5':reserve5()
    elif a.mode=='prune':prune(a.source,a.output)
    else:fill_checkpoint('control',a.source)
