"""Generate a readable hierarchical schematic and complete project-local symbols."""
from __future__ import annotations

import json
import math
from pathlib import Path

from automation.kicad_tools.buck_model import build, write_model, EXAMPLE
from automation.kicad_tools.native_schematic import Schematic, quote, uid, pins, extract_symbol

NAME="AIPE_Buck_1kW"
NOTE="AI-GENERATED ENGINEERING PROTOTYPE - V1 - HUMAN REVIEW REQUIRED"
PAGES={
 '01_power':'Power path / half bridge / Kelvin shunt',
 '02_capacitors':'Input and output bulk capacitor banks',
 '03_gate':'12 V half-bridge gate driver and gate networks',
 '04_aux12':'48 V to 12 V auxiliary supply',
 '05_aux5':'12 V to 5 V auxiliary supply',
 '06_dsp_supplies':'1.9 V / 3.3 V sequencing and reset',
 '07_sensing':'Current / voltage / temperature measurement',
 '08_protection':'Hardware comparators and fault collection',
 '09_pwm_logic':'Latched enable and PWM inhibition',
 '10_dsp':'F28335 pin assignment - all 176 pins',
 '11_dsp_decoupling':'DSP per-pin bypass capacitors',
 '12_clock_debug':'Clock / ADC reference / boot / JTAG / UART',
 '13_testpoints':'Test points and mechanical supports',
}


def units_for(part):
    if part['kind']!='DSP': return [list(part['pins'])]
    groups=[[],[],[],[]]
    for n,p in part['pins'].items():
        if p['name'].startswith(('VDD','VSS')): group=0
        elif p['name'].startswith('ADC'): group=1
        elif part['nets'][n] is not None: group=2
        else: group=3
        groups[group].append(n)
    assert sum(map(len,groups))==176
    return groups


def symbol_for(part):
    name='Sym_'+part['ref']
    standard={'Q':('Transistor_FET','Q_NMOS_GDS'),'L':('Device','L'),'D':('Device','D_Zener')}.get(part['kind'])
    if part['ref']=='F1':standard=('Device','Fuse')
    if standard:
        from automation.kicad_tools.buck_footprints import data_root
        library,original=standard
        definition=extract_symbol(data_root()/'symbols'/(library+'.kicad_sym'),original)
        definition=definition.replace('"'+original,'"'+name)
        assert {p['number'] for p in pins(definition)}==set(part['pins'])
        return name,definition,[(15.24,15.24)]
    bodies=[]; extents=[]
    groups=units_for(part)
    for unit,numbers in enumerate(groups,1):
        small=len(numbers)<=2
        half=math.ceil(len(numbers)/2)
        height=max(5.08, (half+1)*2.54)
        width=5.08 if small else 38.1
        extents.append((width,height))
        graphics=[]
        def line(x1,y1,x2,y2):
            return f'(polyline (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0.254) (type default)) (fill (type none)))'
        if part['kind']=='C' and small:
            graphics += [line(-0.8,-2.54,-0.8,2.54),line(0.8,-2.54,0.8,2.54),line(-2.54,0,-0.8,0),line(0.8,0,2.54,0)]
            if ':CP_' in part['footprint']:
                graphics += [line(-2.0,3.3,-2.0,4.7),line(-2.7,4,-1.3,4)]
        elif small and part['kind']=='R':
            graphics += ['(rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width 0.254) (type default)) (fill (type none)))']
        else:
            graphics += [f'(rectangle (start {-width/2} {height/2}) (end {width/2} {-height/2}) (stroke (width 0.254) (type default)) (fill (type background)))']
        for index,n in enumerate(numbers):
            right=index>=half
            row=index-half if right else index
            y=0 if small else round(height/2-2.54*(row+1),4)
            x=(width/2+5.08)*(1 if right else -1)
            p=part['pins'][n]
            display_name='~' if small else p['name']
            graphics.append(f'''(pin {p['type']} line (at {x} {y} {180 if right else 0}) (length 5.08)
                (name {quote(display_name)} (effects (font (size 1.0 1.0))))
                (number {quote(n)} (effects (font (size 1.0 1.0)))))''')
        bodies.append(f'(symbol "{name}_{unit}_1" {chr(10).join(graphics)})')
    definition=f'''(symbol {quote(name)} (pin_names (offset 0.508)) (in_bom yes) (on_board yes)
        (property "Reference" {quote(part['ref'][0])} (at 0 7.62 0) (effects (font (size 1.27 1.27))))
        (property "Value" {quote(part['value'])} (at 0 5.08 0) (effects (font (size 1.27 1.27))))
        (property "Footprint" {quote(part['footprint'])} (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
        {chr(10).join(bodies)})'''
    return name,definition,extents


def generate():
    write_model()
    parts=build().parts
    target=EXAMPLE/'kicad'; target.mkdir(parents=True,exist_ok=True)
    libs=target/'libraries'; libs.mkdir(exist_ok=True)
    root=Schematic(NAME,'48 V to 24 V / 1 kW synchronous buck','A3',revision='V1',comment=NOTE)
    root.text(NOTE,20,20,2)
    root.text('Design basis: 36-54 V input / 24 V 41.67 A / 100 kHz / 150 MHz F28335\nHardware review prototype. Firmware control loop and thermal performance are unvalidated.\nAll inter-page connections use explicit global net labels. GND is one continuous electrical net.',20,31,1.5)
    all_defs=[]; paths={}; placement={}
    for page_num,(page,title) in enumerate(PAGES.items(),2):
        sheet_id=uid(NAME+'/'+page+'/sheet')
        instance_path='/'+root.root_uuid+'/'+sheet_id
        sch=Schematic(NAME+'/'+page,title,'A3',project_name=NAME,instance_path=instance_path,revision='V1',comment=NOTE)
        sch.text(title,12.7,16.51,2)
        if page=='10_dsp': sch.text('Units: supply pins / ADC / connected digital pins / intentionally unused digital pins. TEST1, TEST2 and X2 are NC.',12.7,22.86,1)
        x,y,row_height=38.1,33.02,0
        for p in (part for part in parts if part['page']==page):
            symbol,definition,extents=symbol_for(p)
            all_defs.append(definition)
            for unit,(width,height) in enumerate(extents,1):
                cell_width=63.5 if len(p['pins'])<=2 or p['kind']=='Q' else 124.46
                cell_height=max(27.94,height+22.86)
                if x+cell_width/2>398:
                    x=38.1; y+=row_height; row_height=0
                if y+cell_height>267:
                    raise ValueError(f'Page overflow {page} {p["ref"]}: {y+cell_height}')
                center_x=x+(cell_width-63.5)/2
                center_y=y+height/2+7.62
                locations=sch.add_symbol('AIPE:'+symbol,definition,p['ref'],p['value'],p['footprint'],center_x,center_y,unit,
                                         property_y=-height/2-6.35,in_bom=p['kind'] not in ('TP','H'))
                for n,point in locations.items():
                    net=p['nets'][n]
                    if net is None:
                        sch.no_connect(point);continue
                    right=point[0]>center_x
                    end=(round(point[0]+(2.54 if right else -2.54),4),point[1])
                    sch.wire(point,end)
                    sch.global_label(net,end,0 if right else 180)
                paths.setdefault(p['ref'],instance_path+'/'+sch.references[p['ref']])
                placement.setdefault(p['ref'],[]).append(dict(sheet=page,unit=unit,x=center_x,y=center_y))
                x+=cell_width; row_height=max(row_height,cell_height)
        # Physical supply provenance. PWR_FLAGs do not replace protection checks.
        if page=='13_testpoints':
            for i,net in enumerate(('GND','VIN_RAW','VIN','VOUT','AUX12','5V','BOOT')):
                definition=f'''(symbol "SupplyFlag" (power) (pin_names (offset 0)) (in_bom no) (on_board no)
                    (property "Reference" "#FLG" (at 0 0 0) (effects (font (size 1 1)) hide))
                    (property "Value" "PWR_FLAG" (at 0 0 0) (effects (font (size 1 1)) hide))
                    (symbol "SupplyFlag_1_1" (pin power_out line (at 0 0 90) (length 0)
                      (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))'''
                ps=sch.add_symbol('AIPE:SupplyFlag',definition,'#FLG'+str(i+1),'PWR_FLAG','',38.1+i*45.72,243.84,in_bom=False,on_board=False)
                sch.global_label(net,ps['1'])
            all_defs.append(definition)
            sch.text('Flags: input source, fuse output, inductor output, auxiliary outputs through inductors, and bootstrap diode supply.\nThey state supply provenance for ERC; they do not prove voltage, current capacity, or protection.',12.7,257,1)
        sch.write(target/(page+'.kicad_sch'))
        ix=(page_num-2)%3; iy=(page_num-2)//3
        sx,sy=22.86+ix*124.46,63.5+iy*35.56
        root.items.append(f'''(sheet (at {sx} {sy}) (size 111.76 25.4) (stroke (width 0.254) (type default))
            (fill (color 0 0 0 0)) (uuid "{sheet_id}")
            (property "Sheetname" {quote(title)} (at {sx} {sy-1.27} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
            (property "Sheetfile" {quote(page+'.kicad_sch')} (at {sx} {sy+26.67} 0) (effects (font (size 1.0 1.0)) (justify left top)))
            (instances (project {quote(NAME)} (path "/{root.root_uuid}" (page "{page_num}")))))''')
    root.write(target/(NAME+'.kicad_sch'))
    (libs/'AIPE.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "aipe")\n'+'\n'.join(all_defs)+')\n',encoding='utf8')
    (target/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "AIPE") (type "KiCad") (uri "${KIPRJMOD}/libraries/AIPE.kicad_sym") (options "") (descr "V1 explicit pin mappings")))\n')
    (target/(NAME+'.kicad_pro')).write_text(json.dumps({
        'meta':{'filename':NAME+'.kicad_pro','version':1},
        'net_settings':{'classes':[{'name':'Default','clearance':0.2,'track_width':0.25,'via_diameter':0.6,'via_drill':0.3}], 'version':4},
        'board':{'design_settings':{'rules':{'min_clearance':0.15,'min_track_width':0.15,'min_via_diameter':0.55,'min_through_hole_diameter':0.25,'min_hole_clearance':0.25,'min_copper_edge_clearance':0.5}}},
    },indent=2)+'\n')
    (EXAMPLE/'design/schematic_mapping.json').write_text(json.dumps(dict(paths=paths,placement=placement),indent=2)+'\n')
    print(f'Generated {len(PAGES)+1} schematic sheets for {len(parts)} physical items.')


if __name__=='__main__': generate()
