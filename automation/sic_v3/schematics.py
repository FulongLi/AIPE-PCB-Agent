"""Native V3 schematic generation. Reads only V3 models; never writes old designs."""
from __future__ import annotations
import argparse
import csv
import json
from automation.sic_v3.model import EXAMPLE, power, control, POWER_PAGES, CONTROL_PAGES
from automation.sic_v3.footprints import custom
from automation.kicad_tools import project_footprints as pf, project_schematic as ps
from automation.kicad_tools.run_check import run_check
from automation.setup.detect_kicad import find_kicad_cli

FLAGS={
 'power':['12V_H_BIAS','12V_L_BIAS','12V_S_BIAS','3V3','GNDP_H','GNDP_L','GNDP_S','GND_CTRL','KS_H','KS_L','PGND','S_5V','RAW','BUS','VOUT'],
 'control':['12V_IN','5V','GND_CTRL'],
}

def power_domains(parts):
    """Working-potential expressions for insulation screening, not field extraction.

    Coefficients apply to independent RAW/BUS/VOUT/SW states. Gate potentials
    use their source domain plus a local +/-22V envelope. 500V bus, 250V output
    are design envelopes; reinforced barrier uses a separate 800V basis.
    """
    nets={n for p in parts for n in p['nets'].values() if n}
    domains={}
    def add(net,profile):
        if net in nets: domains[net]=profile
    for net,vec in [('RAW',(1,0,0,0,0)),('BUS',(0,1,0,0,0)),('VOUT',(0,0,1,0,0)),('SW',(0,0,0,1,0)),('PGND',(0,0,0,0,0))]:add(net,vec)
    for tag in ['H','L']:
        vec=(0,0,0,1 if tag=='H' else 0,22)
        for n in [f'{s}_{tag}' for s in ['KS','G','VDD','VEE','NTC','NTC_R','OUTH','OUTL','OC','DESAT']]+[f'{tag}_{s}' for s in ['VEEA','RLIM','RDR','FBVDD','FBVEE']]:add(n,vec)
    for n in ['S_5V','S_16V','S_VEEA','S_RLIM','S_FBVDD','S_FBVEE','RAW_ADCIN','BUS_ADCIN','OUT_ADCIN']:add(n,(0,0,0,0,22))
    for tag,axis,count in [('RAW',0,4),('BUS',1,4),('OUT',2,2)]:
        for i in range(1,count):
            v=[0,0,0,0,0];v[axis]=(count-i)/count
            add(f'{tag}_DIV{i}',tuple(v))
    for tag,axis in [('IN',1),('OUT',2)]:
        for i in range(1,4):
            v=[0,0,0,0,0];v[axis]=(4-i)/4
            add(f'BLEED_{tag}_{i}',tuple(v))
    return domains

def rules(board,parts):
    allnets=sorted({n for p in parts for n in p['nets'].values() if n})
    cls=lambda name,nets,clearance=.25,width=.3:dict(name=name,nets=nets,clearance=clearance,track_width=width,via_diameter=.8 if board=='power' else .6,via_drill=.4 if board=='power' else .3)
    classes=[cls('Default',[],.25 if board=='power' else .2)]
    if board=='control':
        rails=['12V_IN','12V_E','12V_COIL','MAIN_LOW','PRE_LOW','5V','1V9','3V3','GND_CTRL']
        classes+=[cls('CTRL_POWER',rails,.2,.6),cls('CTRL_SIGNAL',[n for n in allnets if n not in rails],.2,.2)]
        return classes,'(version 1)\n',{}
    domains=power_domains(parts)
    byprofile={}
    for n,prof in domains.items():byprofile.setdefault(prof,[]).append(n)
    profiles={f'HV_{i:02}':p for i,p in enumerate(sorted(byprofile))}
    classes += [cls(name,sorted(byprofile[p])) for name,p in profiles.items()]
    classes.append(cls('CTRL',[n for n in allnets if n not in domains]))
    dru=['(version 1)',
         '(rule "Reinforced hazardous-control barrier, all copper layers" (condition "(A.NetClass == \'CTRL\' && B.NetClass != \'CTRL\') || (B.NetClass == \'CTRL\' && A.NetClass != \'CTRL\')") (constraint clearance (min 8.0)))',
         '(rule "Hazardous copper to board edge" (condition "A.NetClass != \'CTRL\'") (constraint edge_clearance (min 1.0)))']
    evidence=[]
    for i,(a,pa) in enumerate(profiles.items()):
        for b,pb in list(profiles.items())[i+1:]:
            d=[(pa[k]-pb[k])*m for k,m in enumerate([500,500,250,500])]
            dv=max(abs(sum(x for x in d if x<0)),sum(x for x in d if x>0))+pa[4]+pb[4]
            gap=.25 if dv<=50 else .8 if dv<=160 else 1.6 if dv<=320 else 3.0
            dru.append(f'(rule "Functional {a}-{b} {dv:g}V envelope" (condition "(A.NetClass == \'{a}\' && B.NetClass == \'{b}\') || (A.NetClass == \'{b}\' && B.NetClass == \'{a}\')") (constraint clearance (min {gap})))')
            evidence.append(dict(a=a,b=b,voltage_envelope_V=dv,clearance_mm=gap))
    return classes,'\n'.join(dru)+'\n',dict(profiles=profiles,pairs=evidence,notes='Functional spacing is a documented design selection for CTI>=600 PD2; 3mm at500V DC/4kV impulse. 8mm reinforced barrier. No pin-field exemptions.')

def generate(board):
    circuit=power() if board=='power' else control()
    parts=circuit.parts
    out=EXAMPLE/'kicad'/f'{board}_board';out.mkdir(parents=True,exist_ok=True)
    design=EXAMPLE/'design';design.mkdir(exist_ok=True)
    report=ps.analyse_connectivity(parts,FLAGS[board])
    if any(report[k] for k in ['undriven_power_nets','pin_conflicts','single_pin_nets','no_connect_pins_with_nets']):
        raise ValueError(report)
    libraries=pf.prepare_libraries(parts,out,custom_footprints=custom() if board=='power' else {})
    classes,dru,spacing=rules(board,parts)
    presentation=dict(style='wired',groups=circuit.groups,group_titles=circuit.block_titles,exclude_supply=['SW5'],
                      include_supply=['BUS','VOUT','RAW'] if board=='power' else ['REF3'],max_row_mm=250)
    if board=='power':
        presentation['group_templates']={'01_stage/half_bridge':dict(type='buck_half_bridge',high_side='Q1',low_side='Q2',inductor='L1',output_net='VOUT')}
    spec=ps.ProjectSpec(name=f'sic-v3-{board}',title=f'V3 400V / 200V / 5kW - {board}',kicad_dir=out,design_dir=design,
        pages=POWER_PAGES if board=='power' else CONTROL_PAGES,parts=parts,revision='V3',board=board,
        comment='ENGINEERING PROTOTYPE REVIEW - RELEASE BLOCKED - NOT HARDWARE QUALIFIED',
        flag_nets=FLAGS[board],flag_page='08_interface' if board=='power' else '01_supply',
        net_classes=classes,dru_text=dru,design_rules=dict(min_clearance=.25 if board=='power' else .2,min_track_width=.25 if board=='power' else .15,
        min_via_diameter=.8 if board=='power' else .6,min_through_hole_diameter=.4 if board=='power' else .3,min_hole_clearance=.25,min_copper_edge_clearance=.5),
        mapping_name=f'schematic_mapping_{board}.json',presentation=presentation,
        header_lines=['Independent V3 design; 360-440 V DC input; hazardous non-isolated 200 V output.',
                      'Off-board choke, contactors and current sensor require the system assembly drawing.'])
    result=ps.generate_project(spec)
    (design/f'spacing_{board}.json').write_text(json.dumps(spacing,indent=2)+'\n',encoding='utf-8')
    (design/f'library_{board}.json').write_text(json.dumps(libraries,indent=2)+'\n',encoding='utf-8')
    components=EXAMPLE/'components';components.mkdir(exist_ok=True)
    with (components/f'bom_{board}.csv').open('w',newline='',encoding='utf-8') as handle:
        keys=['board','ref','value','mpn','maker','footprint','source','dnp','on_board','note']
        w=csv.DictWriter(handle,keys);w.writeheader()
        for p in parts:
            if p['kind'] in ('TP','H'):continue
            w.writerow({k:p.get(k,True if k=='on_board' else '') for k in keys})
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--board',choices=['power','control','both'],default='both');ap.add_argument('--erc',action='store_true')
    args=ap.parse_args()
    for board in ['power','control'] if args.board=='both' else [args.board]:
        result=generate(board)
        print(board,'schematic generated',flush=True)
        if args.erc:
            report=run_check('erc',EXAMPLE/'kicad'/f'{board}_board'/f'sic-v3-{board}.kicad_sch',EXAMPLE/'verification/erc',cli=find_kicad_cli())
            print(report)

if __name__=='__main__':main()
