"""Measure the actual routed board; geometry is not thermal/EMI qualification."""
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from automation.kicad_tools.buck_model import build,EXAMPLE


def check():
    import pcbnew as pcb
    path=EXAMPLE/'kicad/AIPE_Buck_1kW.kicad_pcb'
    board=pcb.LoadBoard(str(path));parts=build().parts
    fps={f.GetReference():f for f in board.GetFootprints()}
    pads={(f.GetReference(),p.GetNumber()):p for f in fps.values() for p in f.Pads() if p.GetNumber()}
    assert set(fps)=={p['ref'] for p in parts}
    for part in parts:
        assert fps[part['ref']].GetFPID().GetLibItemName()==part['footprint'].split(':')[1]
        for number,net in part['nets'].items():
            actual=pads[part['ref'],number].GetNetname()
            assert actual==net if net is not None else actual.startswith('unconnected-'),(part['ref'],number,net,actual)
    # Independent critical-topology checks, not just a component-count match.
    topology={('Q1','2'):'VIN',('Q1','3'):'SW',('Q3','2'):'SW',('Q3','3'):'GND',
              ('L1','1'):'SW',('L1','2'):'IL_FORCE',('R9','1'):'IL_FORCE',('R9','2'):'VOUT',
              ('R9','3'):'ISENSE_P',('R9','4'):'ISENSE_N',('U16','5'):'PWM_H',('U16','6'):'PWM_L',
              ('U16','21'):'FAULT_N',('U16','80'):'XRS_N',('U16','105'):'CLK30',
              ('J8','1'):'GND',('J8','2'):'BOOT84',('J8','3'):'3V3'}
    for pin,net in topology.items():assert pads[pin].GetNetname()==net
    length=defaultdict(float);vias=defaultdict(int);bounds={}
    layers=defaultdict(set);segments=defaultdict(list)
    for t in board.GetTracks():
        net=t.GetNetname()
        if isinstance(t,pcb.PCB_VIA):vias[net]+=1;continue
        length[net]+=pcb.ToMM(t.GetLength());layers[net].add(t.GetLayerName())
        a,b=pcb.ToMM(t.GetStart()),pcb.ToMM(t.GetEnd());segments[net].append((a,b))
        box=bounds.setdefault(net,[math.inf,math.inf,-math.inf,-math.inf])
        box[:]=[min(box[0],a[0],b[0]),min(box[1],a[1],b[1]),max(box[2],a[0],b[0]),max(box[3],a[1],b[1])]
    bypass=[]
    for part in parts:
        if 'near_dsp_pin' not in part:continue
        supply=pads['U16',part['near_dsp_pin']];cap=pads[part['ref'],'1']
        bypass.append(dict(capacitor=part['ref'],dsp_pin=part['near_dsp_pin'],distance_mm=round(math.dist(pcb.ToMM(supply.GetPosition()),pcb.ToMM(cap.GetPosition())),3)))
    zones=[]
    for z in board.Zones():
        layer=z.GetLayer();poly=z.GetFilledPolysList(layer)
        zones.append(dict(net=z.GetNetname(),layer=board.GetLayerName(layer),area_mm2=round(poly.Area()/1e12,2),islands=poly.OutlineCount()))
        if z.GetNetname()=='GND' and layer in (pcb.In1_Cu,pcb.In4_Cu):
            # A misplaced polygon append once produced a large diagonal notch.
            # Enforce the intended nearly complete ground-plane area and hole.
            assert poly.Area()/1e12>62000,('unexpected ground-plane cutout',layer)
            assert not poly.Contains(pcb.VECTOR2I(pcb.FromMM(145),pcb.FromMM(45)))
            assert poly.Contains(pcb.VECTOR2I(pcb.FromMM(50),pcb.FromMM(100)))
    hf=[]
    for q in ('Q1','Q2','Q3','Q4'):
        point=pcb.ToMM(pads[q,'2'].GetPosition())
        d,ref=min((math.dist(point,pcb.ToMM(pads['C'+str(i),'1'].GetPosition())),'C'+str(i)) for i in range(15,23))
        hf.append(dict(mosfet=q,capacitor=ref,pad_center_distance_mm=round(d,3)))
    report=dict(status='measured-human-review-required',board_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                footprints=len(fps),purchased_components=sum(p['kind'] not in ('TP','H') for p in parts),
                tracks=sum(not isinstance(t,pcb.PCB_VIA) for t in board.GetTracks()),vias=sum(vias.values()),
                copper_layers=board.GetCopperLayerCount(),thickness_mm=pcb.ToMM(board.GetDesignSettings().GetBoardThickness()),
                exact_pad_net_mapping=True,critical_topology_checks=len(topology),
                per_net_tracks_mm={k:round(v,3) for k,v in sorted(length.items())},per_net_vias=dict(vias),
                per_net_layers={k:sorted(v) for k,v in layers.items()},per_net_bounds_mm=bounds,
                dsp_bypass=bypass,hf_capacitor_distances=hf,zones=zones,
                notes=['Track sums include branches and are not point-to-point loop length.',
                       'Pad distance is not current-path distance or loop inductance.',
                       'Plane current sharing, hot spots and return paths need field/thermal analysis and measurement.'])
    report['driver_to_gate_pin_distance_mm']={q:round(math.dist(pcb.ToMM(pads['U1','3' if q in ('Q1','Q2') else '8'].GetPosition()),pcb.ToMM(pads[q,'1'].GetPosition())),3) for q in ('Q1','Q2','Q3','Q4')}
    (EXAMPLE/'verification/power-layout-metrics.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('footprints','purchased_components','tracks','vias','exact_pad_net_mapping','driver_to_gate_pin_distance_mm')}))
    print('DSP bypass maximum pad distance:',max(p['distance_mm'] for p in bypass))
    return report


if __name__=='__main__':check()
