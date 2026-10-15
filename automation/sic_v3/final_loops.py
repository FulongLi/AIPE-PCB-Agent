"""Review actual V3 copper paths, local gate energy loops and quiet stars."""
import json, math
from pathlib import Path
from shapely.geometry import LineString, Point
from automation.kicad_tools.copper_review import geometry
from automation.kicad_tools.copper_paths import CopperPaths
from automation.kicad_tools.loop_geometry import analyse_loop
from automation.kicad_tools.copper_connectivity import analyse
from automation.sic_v3.model import EXAMPLE

OUT=EXAMPLE/'verification/engineering_checks'


def run():
    d=json.loads(Path('.aipe/v3/final-copper-power.json').read_text());r=d['records']
    def pad(ref,pin,layer=None):
        q=next(q for q in r if q['kind']=='pad' and q['ref']==ref and q['pin']==str(pin) and (layer is None or q['layer']==layer))
        return [*q['xy'],0. if q['layer']=='F.Cu' else -1.93]
    def cu(net,points):
        for a,b in zip(points,points[1:]):
            if a[2]!=b[2]:
                assert a[:2]==b[:2]
                assert any(q.get('through') and q['net']==net and math.dist(q['xy'],a[:2])<.003 for q in r)
            else:
                layer='F.Cu' if a[2]==0 else 'B.Cu'
                g=geometry([q for q in r if q['net']==net and q['layer']==layer]).buffer(.003)
                missing=LineString([a[:2],b[:2]]).difference(g).length
                if missing>.001:raise ValueError(f'{net} {a} {b} outside copper {missing}')
        return dict(role='copper',net=net,points=points,coverage_passed=True)
    def bridge(name,a,b):return dict(role='component',net=name,points=[a,b])
    def reverse(s):return {**s,'points':list(reversed(s['points']))}
    loops=[]
    for tag,dx,u,q,ron,roff,cp,cn in [('H',0,'U1','Q1','R9','R10','C21','C22'),('L',25,'U2','Q2','R19','R20','C33','C34')]:
        pt=lambda x,y,z=0:[x+dx,y,z]
        vdd=cu('VDD_'+tag,[pad(cp,1),pt(107.365,22.5,-1.93),pt(107.365,22.5),pad(u,5)])
        vee=cu('VEE_'+tag,[pad(cn,2),pt(103.555,22.5,-1.93),pt(103.555,22.5),pad(u,8)])
        ronpath=cu('OUTH_'+tag,[pad(u,4),pad(ron,1)])
        roffpath=cu('OUTL_'+tag,[pad(u,6),pad(roff,1)])
        gate=cu('G_'+tag,[pad(ron,2),pt(110.08,16.8425),pad(q,4,'F.Cu')])
        offgate=cu('G_'+tag,[pad(roff,2),pad(ron,2),pt(110.08,16.8425),pad(q,4,'F.Cu')])
        kspos=cu('KS_'+tag,[pad(q,3,'F.Cu'),pad(q,3,'B.Cu'),pt(107.54,18,-1.93),pt(107.54,19.05,-1.93),pad(cp,2)])
        ksneg=cu('KS_'+tag,[*kspos['points'][:-1],pad(cp,2),pt(107.375,19.125,-1.93),pt(103.75,19.125,-1.93),pad(cn,1)])
        clamp=cu('G_'+tag,[pad(u,7),pt(104.825,22.8),pt(104.65,22.625),pt(104.65,18.2875),pad(roff,2),pad(ron,2),pt(110.08,16.8425),pad(q,4,'F.Cu')])
        device=bridge(q+' G-KS terminal proxy',pad(q,4,'F.Cu'),pad(q,3,'F.Cu'))
        on=[vdd,bridge(u+' VDD-OUTH internal proxy',pad(u,5),pad(u,4)),ronpath,bridge(ron,pad(ron,1),pad(ron,2)),gate,device,kspos,bridge(cp,pad(cp,2),pad(cp,1))]
        off=[reverse(offgate),bridge(roff,pad(roff,2),pad(roff,1)),reverse(roffpath),bridge(u+' OUTL-VEE internal proxy',pad(u,6),pad(u,8)),reverse(vee),bridge(cn,pad(cn,2),pad(cn,1)),reverse(ksneg),reverse(device)]
        cl=[reverse(clamp),bridge(u+' CLMPI-VEE internal proxy',pad(u,7),pad(u,8)),reverse(vee),bridge(cn,pad(cn,2),pad(cn,1)),reverse(ksneg),reverse(device)]
        for mode,sections in [('turn_on',on),('turn_off',off),('clamp',cl)]:
            loops.append(dict(tag=tag,mode=mode,sections=sections,metrics=analyse_loop(sections)))
    result=dict(board_sha256=d['sha256'],gate_loops=loops,commutation=[],
                scope='Actual copper coverage checked. Closed geometric witnesses, not HF current distribution or inductance extraction. Component internals use straight terminal bridges.')
    graphs={n:CopperPaths(r,n,(70.,0.,141.,25.),grid=.25) for n in ['BUS','SW','PGND']}
    sw=graphs['SW'].path(pad('Q1',2,'F.Cu'),pad('Q2',1,'F.Cu'))
    for c in [f'C{i}' for i in range(5,13)]:
        sections=[graphs['BUS'].path(pad(c,1),pad('Q1',1,'F.Cu')),bridge('Q1 D-S',pad('Q1',1,'F.Cu'),pad('Q1',2,'F.Cu')),sw,
                  bridge('Q2 D-S',pad('Q2',1,'F.Cu'),pad('Q2',2,'F.Cu')),graphs['PGND'].path(pad('Q2',2,'F.Cu'),pad(c,2)),bridge(c,pad(c,2),pad(c,1))]
        result['commutation'].append(dict(capacitor=c,sections=sections,metrics=analyse_loop(sections)))
    (OUT/'power_closed_loops.json').write_text(json.dumps(result,indent=2)+'\n')
    print([(x['tag'],x['mode'],x['metrics']) for x in loops])
    print([(x['capacitor'],x['metrics']) for x in result['commutation']])
    # Remove the small star junction region from a COPY of copper geometry.
    # Confirm power-load terminals remain connected without that branch.
    stars=[]
    for tag,u,nt,vee,driver in [('H','U3','NT1','VEE_H','U1'),('L','U4','NT2','VEE_L','U2'),('S','U8','NT3','PGND','U5')]:
        a=pad(u,36);b=pad(nt,2);cut=LineString([a[:2],b[:2]]).buffer(.85)
        rec=[]
        for q in r:
            if q['net']!=vee:continue
            g=geometry([q]).difference(cut)
            if g.is_empty:continue
            polys=[g] if g.geom_type=='Polygon' else [p for p in g.geoms if p.geom_type=='Polygon']
            rec.append({**q,'polygons':[dict(shell=list(p.exterior.coords),holes=[list(h.coords) for h in p.interiors]) for p in polys]})
        f=Path(f'.aipe/v3/star-{tag}-cut.json');f.write_text(json.dumps(dict(sha256=d['sha256'],records=rec)))
        out=Path(f'.aipe/v3/star-{tag}-components.json');analyse(f,out);net=json.loads(out.read_text())['nets'][0]
        groups=[c['pads'] for c in net['components'] if c['pads']]
        quiet=sorted({(q['ref'],q['pin']) for q in r if q['net']==tag+'_VEEA' and q['kind']=='pad'})
        # All remaining load terminals must stay in one copper component.
        passed=len(groups)==1
        stars.append(dict(tag=tag,module=u,tie=nt,quiet_net_pad_members=quiet,pin36_xy=a[:2],tie_return_xy=b[:2],star_branch_straight_distance_mm=math.dist(a,b),
                          removal_test=dict(radius_mm=.85,all_layer_cut=True,remaining_pad_groups=groups,load_terminals_remain_connected=passed),
                          interpretation='Counterfactual copper-removal graph test demonstrates a load-return bypass; it does not measure current density/noise. Pin36/NT return junction is connected to the wider VEE network; the VEEA branch has no load pads.'))
    (OUT/'quiet_star_topology.json').write_text(json.dumps(dict(board_sha256=d['sha256'],stars=stars),indent=2)+'\n')
    print('Star removal tests',[(s['tag'],s['removal_test']['load_terminals_remain_connected']) for s in stars])


if __name__=='__main__':run()
