"""Editable off-board wiring schematic and explicit terminal-to-terminal list.

Board connectors are mating interfaces, not additional BOM components. Contact,
coil and auxiliary symbols with a common K1/K2 stem belong to one EV200 each.
This passive wiring ERC does not validate insulation or contact interruption.
"""
import argparse,json,csv
from automation.sic_v3.model import EXAMPLE,HARNESS,control,power
from automation.kicad_tools.sic_buck_common import Circuit
from automation.kicad_tools import project_schematic as ps
from automation.kicad_tools.run_check import run_check
from automation.setup.detect_kicad import find_kicad_cli


def model():
    c=Circuit('system');ports=[]
    def add(ref,value,nets,page,kind='J',symbol=None,names=None):
        defs={str(k):dict(name=(names or {}).get(str(k),str(k)),type='passive') for k in nets}
        p=c.add(ref.rstrip('0123456789') or 'X',value,'',nets,page=page,kind=kind,ref=ref,definitions=defs)
        p.update(on_board=False,in_bom=False)
        if symbol:p['symbol']=symbol
        return p
    boards={'power':{p['ref']:p for p in power().parts},'control':{p['ref']:p for p in control().parts}}
    def port(board,ref,page,remap=None):
        p=boards[board][ref];r=('XP' if board=='power' else 'XC')+ref[1:]
        wiring={pin:(remap or {}).get(net,net) for pin,net in p['nets'].items()}
        add(r,board.upper()+' PCB '+ref,wiring,page)
        ports.append(dict(ref=r,board=board,board_ref=ref,pin_map=p['nets'],external_wiring_nets=wiring))
    p='01_hv'
    with c.block('input','Fused input, parallel main/precharge paths; 360-440 V DC'):
        add('XIN','LAB SOURCE + / -',{1:'SOURCE_P',2:'PGND'},p)
        add('F1','KLKD020.T / 600 VDC',{1:'SOURCE_P',2:'RAW'},p,'R','Device:Fuse')
        add('K1','EV200 MAIN A1+ / A2-',{1:'RAW',2:'BUS'},p,'passive','Switch:SW_SPST')
        add('K2','EV200 PRE A1+ / A2-',{1:'RAW',2:'PRE_R'},p,'passive','Switch:SW_SPST')
        add('RPRE','HS100 2k2 / chassis',{1:'PRE_R',2:'BUS'},p,'R')
        for ref in ['J1','J2','J6']:port('power',ref,p)
    with c.block('output','Chassis choke, insulated primary conductor, hazardous output'):
        port('power','J3',p)
        add('L1','4 x 0058192A2 / 28T AWG10',{1:'SW',2:'CHOKE_OUT'},p,'L')
        add('S1P','HO50 aperture: insulated wire; +IP towards output',{1:'CHOKE_OUT',2:'VOUT'},p,names={'1':'IP_IN','2':'IP_OUT'})
        for ref in ['J4','J5']:port('power',ref,p)
        add('XOUT','200 V / 25 A LOAD + / -',{1:'VOUT',2:'PGND'},p)
    with c.block('earth','Dedicated PE bonds; no signal-ground or power-return bond implied'):
        for ref,value in [('XPE','PROTECTIVE EARTH IN'),('XCH','CHASSIS / BASE'),('XHS','HEATSINK'),('XRP','PRECHARGE MOUNTING PLATE')]:add(ref,value,{1:'PE'},p)
    p='02_aux'
    with c.block('supply','Independent isolated 12 V / 10 A source, separate branch returns'):
        add('XAUX','12 V auxiliary + / -',{1:'AUX12',2:'GND_CTRL'},p)
        add('F2','KLKD008.T / 8 A / 600 VDC',{1:'AUX12',2:'12V_COIL'},p,'R','Device:Fuse')
        # Same source node, physically separate branch into the PCB eFuse.
        port('control','J1',p,{'12V_IN':'AUX12'});port('control','J6',p)
    with c.block('contactors','K1/K2 coil and auxiliary circuits; PCB contains switches and suppression'):
        for k,tag,coil,aux in [('1','MAIN','J7','J9'),('2','PRE','J8','J10')]:
            port('control',coil,p)
            add('K'+k+'C',tag+' EV200 coil RED+ / BLACK-',{1:'12V_COIL',2:tag+'_LOW'},p,'L')
            port('control',aux,p)
            add('K'+k+'A',tag+' EV200 NO auxiliary (white leads)',{1:'12V_COIL',2:tag+'_AUX'},p,'passive','Switch:SW_SPST')
    with c.block('thermal','Fail-open chain; not a certified emergency-stop safety function'):
        port('control','J11',p)
        add('TS1','67L090P / sink / NC',{1:'3V3',2:'THERM_1'},p,'passive','Switch:SW_Push_Open')
        add('TS2','67L110P / choke / NC',{1:'THERM_1',2:'THERM_2'},p,'passive','Switch:SW_Push_Open')
        add('SSTOP','Maintained emergency stop / NC',{1:'THERM_2',2:'THERM_OK'},p,'passive','Switch:SW_Push_Open')
    with c.block('fan','12 V fan tach supervised by firmware; PWM lead insulated open'):
        port('control','J12',p)
        add('M1','9GA0812P4G001: - / + / tach',{1:'GND_CTRL',2:'12V_COIL',3:'FAN_TACH',4:None},p,
            names={'1':'BLACK_GND','2':'RED_12V','3':'YELLOW_TACH','4':'BROWN_PWM_OPEN'})
    p='03_sensor'
    with c.block('receiver','Control-board mating connector; 5-wire cable to sensor'):
        port('control','J5',p)
    with c.block('sensor','SENSOR END: fit ROCD here, beside sensor connector'):
        add('S1S','Same HO 50-S-0100 as S1P',{1:'5V',2:'GND_CTRL',3:'I_RAW',4:'I_REF',5:'I_OCD_RAW'},p,
            names={'1':'VCC','2':'GND','3':'VOUT','4':'VREF','5':'OCD'})
        add('ROCD','4k7 / sensor pins 1-to-5',{1:'5V',2:'I_OCD_RAW'},p,'R')
    p='04_harness'
    # Distinct wire IDs preserve all forty physical conductors. Their
    #signal names/board-internal commoning are recorded by HARNESS.
    nets={pin:f'W{int(pin):02}_{net}' for pin,net in HARNESS.items()}
    with c.block('power_plug','160 mm keyed cable: POWER end, J7; pin n to pin n'):
        add('XWP','Power PCB J7 mating plug',nets,p)
    with c.block('control_plug','CONTROL end, J13; same wire IDs; no crossover'):
        add('XWC','Control PCB J13 mating plug',nets,p)
    return c,ports


def generate(erc=False):
    c,ports=model();out=EXAMPLE/'kicad/system_wiring';out.mkdir(parents=True,exist_ok=True)
    notes={
      '01_hv':['S1P is one continuous insulated primary conductor through the sensor aperture; no electrical sensor terminal exists there.',
               'K1 and K2 are normally open. Their coil/auxiliary symbols are on sheet 02. RPRE is bolted to the PE thermal plate.',
               'Output remains hazardous. Contactors do not provide service isolation; lock out both DC and auxiliary sources.',
               'No MOV: controlled source terminal transients <=500 V is an operating restriction; fault-energy coordination remains open.'],
      '02_aux':['TS1, TS2 and SSTOP symbols represent contacts closed in the healthy/cold condition; open-on-rise or actuated opens the chain.',
                'Actual thermostat contact load: 3.3 V /3.3 mA. Dry-contact reliability and temperature lag require qualification.',
                'F2: KLKD008.T in separate L60030M1C + SPL001. Inrush, derating and source/fuse coordination still require qualification.',
                'K1/K2 each require up to3.8 A for130 ms. Keep their pickup-current returns out of the electronics input harness.',
                'M1 PWM open behavior and lead colors require exact-revision supplier confirmation before wiring.'],
      '03_sensor':['ROCD MUST be assembled at the sensor connector. A disconnected harness must pull the PCB I_OCD_RAW low through its own network.',
                   'Primary insulation, conductor aperture fit, sensing polarity and reference calibration require hardware verification.'],
      '04_harness':['Each Wxx_SIGNAL net denotes a physical conductor. Same-named grounds/rails are connected on the actual boards.',
                    'Samtec IDSD cable mates TST headers. Confirm polarisation, pin1, retention and finished-length convention on assembly drawing.']}
    spec=ps.ProjectSpec(name='sic-v3-system',title='V3 system wiring / off-board assembly',kicad_dir=out,design_dir=EXAMPLE/'design',
        pages={'01_hv':'High-voltage input, precharge, choke and PE','02_aux':'Auxiliary supply, contactors, thermal chain and fan',
               '03_sensor':'Current-sensor signal harness','04_harness':'Straight-through control harness'},parts=c.parts,revision='V3',board='system',
        comment='ENGINEERING PROTOTYPE REVIEW - RELEASE BLOCKED',header_lines=['Mating interfaces reference actual power/control PCB connector numbers. No extra PCB is implied.'],
        page_notes={k:' '.join(v) for k,v in notes.items()},mapping_name='schematic_mapping_system.json',presentation=dict(style='wired',groups=c.groups,group_titles=c.block_titles,max_row_mm=250))
    ps.generate_project(spec)
    # Keep the sensor-end caption clear of the physical 5 V cable wire
    #that runs between these two deliberately separate functional blocks.
    sensor=out/'03_sensor.kicad_sch'
    content=sensor.read_text(encoding='utf-8')
    content=content.replace('(text "SENSOR END: fit ROCD here, beside sensor connector" (at 20.32 82.55 0)',
                            '(text "SENSOR END: fit ROCD here, beside sensor connector" (at 48.26 82.55 0)')
    sensor.write_text(content,encoding='utf-8')
    auxiliary=out/'02_aux.kicad_sch'
    content=auxiliary.read_text(encoding='utf-8').replace(
        '(text "K1/K2 coil and auxiliary circuits; PCB contains switches and suppression" (at 20.32 105.41 0)',
        '(text "Contactor coils and auxiliary contacts" (at 180.34 105.41 0)')
    auxiliary.write_text(content,encoding='utf-8')
    root_schematic=out/'sic-v3-system.kicad_sch'
    root_schematic.write_text('\n'.join(line.rstrip() for line in root_schematic.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    (EXAMPLE/'design/circuit_system.json').write_text(json.dumps(c.parts,indent=2)+'\n',encoding='utf-8')
    (EXAMPLE/'mechanical/system_ports.json').write_text(json.dumps(ports,indent=2)+'\n',encoding='utf-8')
    if erc:print(run_check('erc',out/'sic-v3-system.kicad_sch',EXAMPLE/'verification/erc',cli=find_kicad_cli()))
    print('Native editable system wiring generated.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--erc',action='store_true');generate(p.parse_args().erc)
