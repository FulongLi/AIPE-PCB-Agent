"""Compare complete proposed multilayer loops before final routing."""
from pathlib import Path
import json
import math
from automation.sic_v3.model import EXAMPLE
from automation.kicad_tools.loop_geometry import analyse_loop


def at(data,ref,pin,z=0.):
    pad=next(p for p in data['pads'] if p['ref']==ref and p['pin']==str(pin))
    return [*pad['xy'],z]


def section(role,net,*points):return dict(role=role,net=net,points=list(points))


def commutation(data,cap):
    cp,cn=at(data,cap,1,-1.93),at(data,cap,2,-1.93)
    hd,hs,ld,ls=[at(data,r,p) for r,p in [('Q1',1),('Q1',2),('Q2',1),('Q2',2)]]
    # Explicit copper layers: BUS B.Cu; SW F.Cu; return In1.Cu. Each
    #transition is included. Final routing must replace these proposed
    #corridors and add the finite via-array and neck geometry.
    sections=[section('copper','BUS',cp,[*hd[:2],-1.93],hd),section('component','Q1 D-to-S',hd,hs),
        section('copper','SW',hs,ld),section('component','Q2 D-to-S',ld,ls),
        section('copper','PGND',ls,[*ls[:2],-.27],[*cn[:2],-.27],cn),section('component',cap,cn,cp)]
    return dict(capacitor=cap,sections=sections,**analyse_loop(sections))


def gate(data,tag):
    q,u,r=('Q1','U1','R9') if tag=='H' else ('Q2','U2','R19')
    out,a,z,g,ks,com=[at(data,ref,pin) for ref,pin in [(u,4),(r,1),(r,2),(q,4),(q,3),(u,3)]]
    sections=[section('copper','OUTH_'+tag,out,a),section('component',r,a,z),section('copper','G_'+tag,z,g),
        section('component',q+' G-to-KS',g,ks),section('copper','KS_'+tag,ks,com),section('component',u+' COM-to-OUTH',com,out)]
    return dict(sections=sections,**analyse_loop(sections))


def main():
    out=EXAMPLE/'pcb/floorplan_candidates';results={}
    for candidate in ['A','B']:
        data=json.loads((out/f'power_{candidate}.json').read_text())
        loops=[commutation(data,f'C{i}') for i in range(5,13)]
        results[candidate]=dict(area_mm2=data['width_mm']*data['height_mm'],layers=data['layers'],
            commutation_all_capacitors=loops,shortest_commutation=min(loops,key=lambda r:r['external_copper_length_mm']),
            gates={t:gate(data,t) for t in ['H','L']})
    result=dict(evidence_level='Complete proposed multilayer centreline paths for floorplan selection; not routed measurements or extraction',
        selected='B',selection_reason='Common planar thermal fixture and symmetric local gate cells, while retaining comparable commutation geometry. Candidate A needs two orthogonal contact planes and more complex accessible-control routing. Final choice remains subject to routed loop and native DRC gates.',candidates=results)
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    rows=['# V3 floorplan selection','',result['evidence_level']+'.','',
      '| Candidate | PCB area | External commutation copper proxy | Closed loop proxy | XY area proxy | H/L gate copper proxies |',
      '|---|---:|---:|---:|---:|---:|']
    for key,r in results.items():
        c=r['shortest_commutation'];g=r['gates']
        rows.append(f"| {key} | {r['area_mm2']:.0f} mm² | {c['external_copper_length_mm']:.2f} mm | {c['closed_proxy_length_mm']:.2f} mm | {c['projected_xy_area_mm2']:.2f} mm² | {g['H']['external_copper_length_mm']:.2f} / {g['L']['external_copper_length_mm']:.2f} mm |")
    rows+=['','Selected **B**. '+result['selection_reason'],'',
      'Both are independent 202-part native four-layer floorplans. A uses opposed 90°/270° devices, drivers above/below, and a two-row HF bank beside the pair. B uses co-oriented devices along one edge, independent same-orientation gate cells and a back-side HF row. Bulk banks, separately supported magnetics and the four board supports are common system constraints.',
      '', 'Every capacitor is evaluated, including its return and layer transitions. Component-internal paths are straight terminal bridges, not package extraction. The proposed BUS path is B.Cu, SW F.Cu and PGND In1.Cu. Paths are preliminary corridors, not proof that the final track/zone avoids all pads. Values must be replaced by actual routed geometry in the final report; no nH is asserted. A low projected area alone does not prove low inductance or low EMI.',
      '', 'B separates the central control region from hazardous gate cells above and hazardous sensing cells below. Accessible control copper cannot underlie a hazardous island on any layer. Heavy film capacitors stay beside, rather than underneath, the thermal fixture. Quiet VEEA tie and divider placement is explicit; routing must prove that load return does not bypass the intended star.',
      '', 'The footprint-only native checks are retained separately from final routed DRC. Unconnected items are expected at this stage; a floorplan is not CAD-complete. Thermal fixtures, harness engagement, copper minimum widths and semiconductor timing remain independent gates.']
    (out/'comparison.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print({k:dict(commutation_external_mm=r['shortest_commutation']['external_copper_length_mm'],gate_external_mm={t:g['external_copper_length_mm'] for t,g in r['gates'].items()}) for k,r in results.items()})

if __name__=='__main__':main()
