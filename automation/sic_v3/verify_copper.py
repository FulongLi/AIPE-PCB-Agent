"""Reproduce V3 native-copper geometry and DC-mesh engineering screens.

export: KiCad Python. review/mesh: host Python with Shapely/SciPy.
Canonical native projects are inputs; no CAD geometry is modified here.
"""
import argparse,json,hashlib
from pathlib import Path
from automation.sic_v3.model import EXAMPLE,power
from automation.sic_v3.schematics import power_domains

WORK=Path('.aipe/v3');OUT=EXAMPLE/'verification/engineering_checks'


def source(which):return WORK/f'final-copper-{which}.json'


def export():
    import pcbnew as p
    from automation.kicad_tools.copper_connectivity import export as copper_export
    for which in ['power','control']:
        f=EXAMPLE/f'kicad/{which}_board/sic-v3-{which}.kicad_pcb';b=p.LoadBoard(str(f.resolve()))
        copper_export(f,source(which),[n.GetNetname() for n in b.GetNetInfo().NetsByNetcode().values() if n.GetNetCode()])


def review():
    from automation.kicad_tools.copper_review import barrier,geometry,reference_coverage
    from automation.kicad_tools.copper_connectivity import analyse
    OUT.mkdir(parents=True,exist_ok=True)
    for which in ['power','control']:
        analyse(source(which),OUT/f'{which}_copper_islands.json')
    d=json.loads(source('power').read_text());result=barrier(d['records'],power_domains(power().parts));result['board_sha256']=d['sha256']
    (OUT/'power_projected_isolation.json').write_text(json.dumps(result,indent=2)+'\n')
    areas={l:geometry([q for q in d['records'] if q['net']=='SW' and q['layer']==l]).area for l in ['F.Cu','In1.Cu','In2.Cu','B.Cu']}
    (OUT/'switch_node_area.json').write_text(json.dumps(dict(board_sha256=d['sha256'],area_mm2_by_layer=areas,evidence='Native filled copper union, not enclosure coupling or EMC extraction'),indent=2)+'\n')
    d=json.loads(source('control').read_text());nets=['CLK_SRC','CLK30','EPWM_A','EPWM_B','PWM_H','PWM_L','ARMED','CURRENT_OK','ADC_CURRENT','ADC_BUS','ADC_OUT','ADC_RAW','ADC_TEMP','ADC_IREF','ADC_V12','ADCREFP','ADCREFM','ADCRESEXT']
    (EXAMPLE/'pcb/routing_analysis/control_return_projection.json').write_text(json.dumps(dict(board_sha256=d['sha256'],evidence='Actual native filled copper and track/arc centreline projection; not impedance extraction',results=reference_coverage(d['records'],nets)),indent=2)+'\n')
    print('Projected barrier:',result,flush=True)


def mesh():
    from automation.kicad_tools.sheet_resistance import solve
    d=json.loads(source('power').read_text());OUT.mkdir(parents=True,exist_ok=True);out=OUT/'power_copper_dc_mesh.json'
    result=dict(board_sha256=d['sha256'],tool_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['automation/kicad_tools/sheet_resistance.py',__file__]},cases=[])
    cases=[('BUS',('J1','1'),('Q1','1'),[.5,.25]),('SW',('Q1','2'),('J3','1'),[.25,.125]),('SW',('Q2','1'),('J3','1'),[.25,.125]),('PGND',('J5','1'),('J2','1'),[.5,.25]),('PGND',('Q2','2'),('J2','1'),[.5,.25]),('VOUT',('J4','1'),('C14','1'),[.5,.25])]
    for net,a,z,steps in cases:
        for grid in steps:
            v=solve(d['records'],net,{a},{z},grid=grid);v.update(source=a,sink=z);result['cases'].append(v)
            out.write_text(json.dumps(result,indent=2)+'\n');print(net,a,z,grid,v.get('resistance_mOhm',v['status']),flush=True)
    result['mesh_changes_percent']=[100*abs(a['resistance_mOhm']-b['resistance_mOhm'])/b['resistance_mOhm'] for a,b in zip(result['cases'][::2],result['cases'][1::2])]
    result['interpretation']='Geometric DC resistor-mesh screen only. Grid convergence does not validate contact, plating, AC, thermal or hardware assumptions. 25 A endpoint tests are separate stress screens and are not all simultaneous operating currents.'
    out.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['export','review','mesh']);a=p.parse_args();globals()[a.stage]()
