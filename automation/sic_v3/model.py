"""Independent V3 circuit model. No call to a previous-generation build/write function.

Generic part helpers and previously verified IC pin tables are reused read-only.
All connections, reference designators, functional groups and placement inputs below
belong to V3. Physical verification is performed by the separate CAD pipeline.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from automation.kicad_tools.sic_buck_common import Circuit, pin_defs, PASSIVE_CAPS
from automation.kicad_tools.sic_buck_control_model import IC as VERIFIED_IC, CONTROL_CAPS
from automation.kicad_tools.sic_buck_power_model import UCC21710_PINS, AMC1311_PINS, OPA2320_PINS, ucc14141_pins

ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=ROOT/'examples/sic-buck-400v-200v-5kw-v3'
TI='Texas Instruments'
DS='https://www.ti.com/lit/ds/symlink/{}.pdf'
GND='GND_CTRL'
POWER_PAGES={
 '01_stage':'SiC half bridge, DC link and output filter',
 '02_hs':'High-side drive and short-circuit protection',
 '03_ls':'Low-side drive and short-circuit protection',
 '04_hs_bias':'High-side isolated gate-bias supply',
 '05_ls_bias':'Low-side isolated gate-bias supply',
 '06_measure':'Raw input, DC-link and output isolated voltage measurement',
 '07_sense_bias':'Independent isolated sensing supply',
 '08_interface':'Keyed control harness, fail-safe inputs and mounting',
}
CONTROL_PAGES={
 '01_supply':'Protected electronics supply and DSP power sequencing',
 '02_dsp':'TMS320F28335 controller and signal assignment',
 '03_bypass':'DSP per-pin bypass and ADC reference',
 '04_debug':'Clock, boot, JTAG and communications',
 '05_analog':'Isolated voltage receiver and bipolar current conditioning',
 '06_trip':'Asynchronous protection, fault latch and PWM gating',
 '07_actuate':'Contactor, feedback, fan and thermal interlock',
 '08_interface':'Power-board harness and mechanical support',
}
# Straight-through 40-way keyed harness; adjacent odd/even pins form signal-return pairs.
HARNESS={str(i):n for i,n in enumerate([
 GND,'PWM_H',GND,'PWM_L',GND,'DRV_RESET',GND,'BIAS_EN',
 GND,'FLT_H_N',GND,'FLT_L_N',GND,'RDY_H',GND,'RDY_L',
 GND,'PG_H_N',GND,'PG_L_N',GND,'PG_S_N','RAW_P','RAW_N',
 'BUS_P','BUS_N','OUT_P','OUT_N',GND,'TH_H_PWM',GND,'TH_L_PWM',
 '12V_E','12V_E',GND,GND,'3V3','3V3',GND,GND],1)}
EXTRA_IC={
 'OPA2320AIDGKR':('Package_SO:VSSOP-8_3x3mm_P0.65mm',OPA2320_PINS,DS.format('opa2320')),
 'OPA4192IPWR':('Package_SO:TSSOP-14_4.4x5mm_P0.65mm',pin_defs('1:OUTA:output 2:INA-:input 3:INA+:input 4:V+:power_in 5:INB+:input 6:INB-:input 7:OUTB:output 8:OUTC:output 9:INC-:input 10:INC+:input 11:V-:power_in 12:IND+:input 13:IND-:input 14:OUTD:output'),DS.format('opa4192')),
 'TLV3202AIDGKR':('Package_SO:VSSOP-8_3x3mm_P0.65mm',pin_defs('1:OUTA:output 2:INA-:input 3:INA+:input 4:V-:power_in 5:INB+:input 6:INB-:input 7:OUTB:output 8:V+:power_in'),DS.format('tlv3202')),
}

def ic(c,mpn,nets,page,*,ref=None,note='',prefix='U'):
    if mpn in EXTRA_IC:
        fp,defs,source=EXTRA_IC[mpn];maker=TI
    else:
        fp,pins,source,maker=VERIFIED_IC[mpn];defs=pin_defs(pins)
    nets={str(k):v for k,v in nets.items()}
    for n,p in defs.items():
        if p['type']=='no_connect': nets.setdefault(n,None)
    if mpn=='BAT54,215':
        # Two-pad package gives an unambiguous conventional Schottky glyph.
        return diode(c,'BAT46W-E3-08','Diode_SMD:D_SOD-123',nets['3'],nets['1'],page,
                     source='https://www.vishay.com/docs/86406/bat46w.pdf',ref=ref,note=note)
    part=c.add(prefix,mpn,fp,nets,page=page,kind='Q' if prefix=='Q' else 'IC',mpn=mpn,maker=maker,source=source,definitions=defs,ref=ref,note=note)
    if mpn=='MMBT3904,215':part['symbol']='Transistor_BJT:Q_NPN_BEC'
    if mpn in ('OPA2320AIDGKR','OPA4192IPWR','TLV3202AIDGKR'):
        channels=[(3,2,1),(5,6,7)]
        if mpn=='OPA4192IPWR':channels += [(10,9,8),(12,13,14)]
        part['amplifier_channels']=[dict(zip(('positive','negative','output'),map(str,ch))) for ch in channels]
    return part

def cap(c,key,a,b,p,**kw):
    if key in PASSIVE_CAPS:return c.cap(key,a,b,p,**kw)
    if key=='680p/50V/0603':
        return c.add('C','680p/50V','Capacitor_SMD:C_0603_1608Metric',{1:a,2:b},page=p,kind='C',mpn='GRM1885C1H681JA01D',maker='Murata',source='https://www.murata.com/en-us/products/productdetail?partno=GRM1885C1H681JA01D',**kw)
    if key=='10u/50V/1210':
        return c.add('C','10u/50V','Capacitor_SMD:C_1210_3225Metric',{1:a,2:b},page=p,kind='C',mpn='GRM32ER71H106KA12L',maker='Murata',source='https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM32ER71H106KA12-04A.pdf',**kw)
    s=CONTROL_CAPS[key]
    return c.add('C',key.split('/')[0],s['footprint'],{1:a,2:b},page=p,kind='C',mpn=s['mpn'],maker=s['maker'],source=s['source'],**kw)

def resistor(c,value,a,b,p,*,precision=False,package='0603',**kw):
    if kw.get('maker')=='Panasonic' and 'source' not in kw:
        kw['source']='https://industrial.panasonic.com/ww/products/pt/small-and-high-power-chip-resistors'
    # Manufacturer ordering suffix verified independently in component procurement review.
    if precision:
        from decimal import Decimal
        val=Decimal(value.rstrip('kM'))*(1000 if value.endswith('k') else 1000000 if value.endswith('M') else 1)
        exp=0
        while val>=1000: val/=1000;exp+=3
        token=f'{val:g}'.replace('.','K' if exp==3 else 'M' if exp==6 else 'R')
        if not any(x in token for x in 'KMR'):token+=('K' if exp==3 else 'M' if exp==6 else 'R')
        token=token.ljust(4,'0')
        kw.update(mpn=f'TNPW{package}{token}BEEA',maker='Vishay',source='https://www.vishay.com/docs/28773/tnpwe3.pdf')
    return c.resistor(value,a,b,p,package=package,**kw)

def diode(c,mpn,fp,k,a,p,*,source,note='',ref=None):
    return c.add('D',mpn,fp,{1:k,2:a},page=p,kind='D',mpn=mpn,maker='Vishay',source=source,definitions=pin_defs('1:K:passive 2:A:passive'),note=note,ref=ref)

def tp(c,net,p):
    return c.add('TP',net,'TestPoint:TestPoint_Pad_D1.0mm',{1:net},page=p,kind='TP')

def keyed(c,p):
    return c.add('J','POWER / CONTROL — 40-way','Connector_IDC:IDC-Header_2x20_P2.54mm_Vertical',HARNESS,page=p,kind='J',
                 mpn='TST-120-01-G-D',maker='Samtec',source='https://www.samtec.com/products/tst',
                 note='Keyed 100 mm maximum straight-through harness; verify mating cable pin 1 and rating; no gate-current path in this cable')

def mounts(c,p):
    for _ in range(4):
        c.add('H','M3 insulated standoff','MountingHole:MountingHole_3.2mm_M3',{},page=p,kind='H',note='Four independent chassis supports; no unsupported board overhang')

def bias(c,tag,p,*,sense=False):
    vdd='S_16V' if sense else f'VDD_{tag}'
    vee='PGND' if sense else f'VEE_{tag}'
    com='S_5V' if sense else f'KS_{tag}'
    quiet=f'{tag}_VEEA'
    vb,gp=f'12V_{tag}_BIAS',f'GNDP_{tag}'
    with c.block(f'bias_{tag}',f'{tag}: isolated DC/DC and physical feedback star'):
        c.add('L','744226S','Inductor_SMD:L_CommonMode_Wuerth_WE-SL2',{1:'12V_E',2:GND,3:gp,4:vb},page=p,kind='L',
              mpn='744226S',maker='Wuerth Elektronik',source='https://www.we-online.com/components/products/datasheet/744226S.pdf',
              definitions=pin_defs('1:W1A:passive 2:W2A:passive 3:W2B:passive 4:W1B:passive'))
        for _ in range(3):cap(c,'10u/25V/1210',vb,gp,p)
        cap(c,'100n/50V/0603',vb,gp,p,note='Same-side bypass at VIN7/GNDP8; no via in HF branch')
        nets={n:gp for n in (1,2,5,*range(8,19))}
        nets.update({n:vee for n in (*range(19,28),30,31,36)})
        nets.update({3:f'PG_{tag}_N',4:'BIAS_EN_F',6:vb,7:vb,28:vdd,29:vdd,32:f'{tag}_RLIM',33:f'{tag}_FBVEE',34:f'{tag}_FBVDD',35:quiet})
        u=c.add('U','UCC14141QDWNRQ1','AIPE:V3_UCC14141_DWN',nets,page=p,kind='IC',mpn='UCC14141QDWNRQ1',maker=TI,
                source=DS.format('ucc14141-q1'),definitions=ucc14141_pins('passive' if sense else 'power_out'),note='VEEA pin35 isolated on every copper layer; single star at VEE36')
        u['island']=tag
        tie=c.add('NT','VEEA STAR','NetTie:NetTie-2_SMD_Pad0.5mm',{1:quiet,2:vee},page=p,kind='passive',note=f'Physical star at {u["ref"]}.36; no gate/decoupling current through quiet branch')
        tie['star_of']=u['ref']
        for name,upper,top in [('FBVDD',vdd,'87.6k' if sense else '121k'),('FBVEE',com,'16.2k' if sense else '9.76k')]:
            resistor(c,top,upper,f'{tag}_{name}',p,precision=True)
            resistor(c,'16.2k',f'{tag}_{name}',quiet,p,precision=True)
            cap(c,'330p/50V/0603',f'{tag}_{name}',quiet,p,note='Quiet feedback branch only')
        if sense:
            resistor(c,'82',f'{tag}_RLIM',com,p,package='1206',mpn='ERJP08F82R0V',maker='Panasonic',
                     source='https://industrial.panasonic.com/ww/products/pt/small-and-high-power-chip-resistors',note='Three AMC1311: 29.1 mA max +1 mA; Eq.9, 60 ohm internal-R stress assumption')
        else:
            resistor(c,'1k',f'{tag}_RLIM',com,p,package='1206',mpn='ERJP08F1001V',maker='Panasonic',note='RDR source branch, Eq.10 stress calculation')
            resistor(c,'180',f'{tag}_RLIM',f'{tag}_RDR',p,package='1206',mpn='ERJP08F1800V',maker='Panasonic',note='RDR sink branch; 180R + diode parallel with 1k')
            diode(c,'BAT46W-E3-08','Diode_SMD:D_SOD-123',f'{tag}_RDR',com,p,source='https://www.vishay.com/docs/86406/bat46w.pdf',note='Anode COM, cathode RDR resistor: sinks COM charge into RLIM')
        # 50 V bulk removes the near-rating 25 V capacitor at 22.1 V from the previous design.
        for _ in range(3):cap(c,'1u/50V/0805',vdd,vee,p,note='Nominal 3 uF plus local gate reservoir; effective bias capacitance must be characterised')
        for _ in range(2):cap(c,'10u/50V/1210',vdd,vee,p,note='Total nominal 23 uF; >=10 uF effective required at configured output voltage')
        cap(c,'100n/50V/0603',vdd,vee,p,note='Same-side bypass at output pins28/30')
        if sense:cap(c,'10u/25V/1210',com,vee,p)
        resistor(c,'4.7k','3V3',f'PG_{tag}_N',p)

def gate(c,tag,other,drain,p):
    ks,g,vdd,vee=f'KS_{tag}',f'G_{tag}',f'VDD_{tag}',f'VEE_{tag}'
    with c.block(f'driver_{tag}',f'{tag}: isolated gate driver, Kelvin return and clamp'):
        nets={1:f'NTC_{tag}',2:f'OC_{tag}',3:ks,4:f'OUTH_{tag}',5:vdd,6:f'OUTL_{tag}',7:g,8:vee,9:GND,
              10:f'PWM_{tag}_F',11:f'PWM_{other}_F',12:f'RDY_{tag}',13:f'FLT_{tag}_N',14:'DRV_RESET_F',15:'3V3',16:f'TH_{tag}_PWM'}
        c.add('U','UCC21710QDWRQ1','AIPE:V3_UCC21710_HV',nets,page=p,kind='IC',mpn='UCC21710QDWRQ1',maker=TI,source=DS.format('ucc21710-q1'),definitions=UCC21710_PINS,note='CLMPI directly to device gate; COM only to Kelvin source, not power source')
        resistor(c,'10',f'OUTH_{tag}',g,p,package='1206',mpn='ERJP08F10R0V',maker='Panasonic',note='Conservative initial turn-on; double-pulse tuning required')
        resistor(c,'3.3',f'OUTL_{tag}',g,p,package='1206',mpn='ERJP08F3R30V',maker='Panasonic')
        resistor(c,'10k',g,ks,p,package='0805')
        c.add('TP',f'VGS {tag}','TestPoint:TestPoint_2Pads_Pitch2.54mm_Drill0.8mm',{1:g,2:ks},page=p,kind='TP')
        for _ in range(4):cap(c,'1u/50V/0805',vdd,ks,p,note='>=2.2 uF effective positive gate reservoir')
        for _ in range(2):cap(c,'10u/25V/1210',ks,vee,p,note='>=10 uF effective negative gate reservoir')
        for a,b in [(vdd,ks),(ks,vee),('3V3',GND)]:cap(c,'100n/50V/0603',a,b,p)
        cap(c,'1u/50V/0805','3V3',GND,p)
        resistor(c,'3.3k',f'NTC_{tag}',f'NTC_R_{tag}',p)
        resistor(c,'20k',f'NTC_{tag}',ks,p,note='Bounds AIN below4.18V even if NTC opens')
        c.add('RT','10k NTC B3988','Resistor_SMD:R_0805_2012Metric',{1:f'NTC_R_{tag}',2:ks},page=p,kind='R',
              mpn='NCP21XV103J03RA',maker='Murata',source='https://www.murata.com/en-us/products/productdetail?partno=NCP21XV103J03RA',
              note='Board-side driver-island temperature only; APWM conversion. Independent heatsink thermostat is hardware trip')
        cap(c,'1n/50V/0603',f'NTC_{tag}',ks,p)
        for sig in [f'RDY_{tag}',f'FLT_{tag}_N']:resistor(c,'4.7k','3V3',sig,p)
    with c.block(f'desat_{tag}',f'{tag}: drain-voltage short-circuit detection'):
        resistor(c,'2.2k',vdd,f'DESAT_{tag}',p,package='1206',mpn='ERJP08F2201V',maker='Panasonic')
        # Leaded diode provides real lead separation; no tiny SMA HV clearance exemption.
        diode(c,'UF4007-E3/54','Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal',drain,f'DESAT_{tag}',p,
              source='https://www.vishay.com/docs/88755/uf4001.pdf',note='1000 V diode; controlled-input prototype bus <=500 V, switching peak target <=800 V')
        resistor(c,'9.09k',f'DESAT_{tag}',f'OC_{tag}',p,precision=True)
        resistor(c,'1k',f'OC_{tag}',ks,p,precision=True)
        cap(c,'680p/50V/0603',f'OC_{tag}',ks,p,note='~0.44us nominal DESAT blanking; turn-on false-trip and short-circuit survival require double-pulse validation')
        diode(c,'BAT46W-E3-08','Diode_SMD:D_SOD-123',f'OC_{tag}',ks,p,source='https://www.vishay.com/docs/86406/bat46w.pdf',note='OC negative transient clamp')

def power():
    c=Circuit('power'); p='01_stage'
    with c.block('half_bridge','400 V DC link → vertical half bridge → external choke → 200 V output'):
        for tag,drain,source in [('H','BUS','SW'),('L','SW','PGND')]:
            q=c.add('Q','C4MS025120K','AIPE:V3_TO247_4',{1:drain,2:source,3:f'KS_{tag}',4:f'G_{tag}'},page=p,kind='Q',
                    mpn='C4MS025120K',maker='Wolfspeed',source='https://assets.wolfspeed.com/uploads/2025/11/Wolfspeed_C4MS025120K_data_sheet.pdf',
                    definitions=pin_defs('1:D:passive 2:S:passive 3:KS:passive 4:G:input'),note='Device front-view pin order D, power S, driver S, G; tab D; straight leads and chassis thermal fixture')
            q['role']='high_side' if tag=='H' else 'low_side'
        choke=c.add('L','432u at 0A / CHASSIS','',{1:'SW',2:'VOUT'},page=p,kind='L',mpn='CUSTOM-4x0058192A2-28T-AWG10',maker='Custom assembly',
                    source='https://www.mag-inc.com/Media/Magnetics/Datasheets/0058192A2.pdf',note='Four stacked 60u High Flux cores; 28 turns AWG10; chassis supported. See winding specification and bias calculation')
        choke['on_board']=False
        for _ in range(4):
            c.add('C','15u / 900V','AIPE:V3_CIN_15U',{1:'BUS',2:'PGND'},page=p,kind='C',mpn='B32776G9156K000',maker='TDK',source='https://www.tdk-electronics.tdk.com/inf/20/20/db/fc_2009/MKP_B32774_778.pdf',note='42 x20 x39.5 mm; 37.5 x10.2 mm four-lead; 12.5 Arms at70C/10kHz each')
        for _ in range(8):cap(c,'0.47u/630V/2220','BUS','PGND',p,note='Effective HF capacitance under 440 V bias unverified; geometric loop tracked separately from bulk bank')
        for _ in range(2):
            c.add('C','100u / 450V','AIPE:V3_COUT_100U',{1:'VOUT',2:'PGND'},page=p,kind='C',mpn='B32778G4107K000',maker='TDK',source='https://www.tdk-electronics.tdk.com/inf/20/20/db/fc_2009/MKP_B32774_778.pdf',note='57.5 x35 x50 mm; 52.5 x20.3 mm four-lead; output200 uF nominal')
    with c.block('terminals','Chassis circuit connections — refer to system wiring project'):
        for name,net in [('INPUT LINK +','BUS'),('INPUT / OUTPUT RETURN','PGND'),('SW TO CHOKE','SW'),('CHOKE RETURN / OUTPUT +','VOUT'),('OUTPUT RETURN','PGND'),('RAW INPUT SENSE','RAW')]:
            c.add('J',name,'TerminalBlock_Wuerth:Wuerth_REDCUBE-THR_WP-THRSH_74651195_THR',{1:net},page=p,kind='J',mpn='74651195',maker='Wuerth Elektronik',source='https://www.we-online.com/components/products/datasheet/74651195.pdf')
    with c.block('discharge','Passive discharge independent of auxiliary power'):
        for tag,net,value in [('IN','BUS','91k'),('OUT','VOUT','43k')]:
            chain=[net]+[f'BLEED_{tag}_{i}' for i in range(1,4)]+['PGND']
            for a,b in zip(chain,chain[1:]):resistor(c,value,a,b,p,package='2512',note='Series voltage sharing; total discharge target <60s including +5% R/+10% C; validate actual capacitance')
    gate(c,'H','L','BUS','02_hs');gate(c,'L','H','SW','03_ls')
    bias(c,'H','04_hs_bias');bias(c,'L','05_ls_bias')
    p='06_measure'
    for tag,net,count in [('RAW','RAW',4),('BUS','BUS',4),('OUT','VOUT',2)]:
        with c.block(f'voltage_{tag}',f'{tag}: independent high-impedance isolated measurement'):
            chain=[net]+[f'{tag}_DIV{i}' for i in range(1,count)]+[f'{tag}_ADCIN']
            for a,b in zip(chain,chain[1:]):resistor(c,'750k',a,b,p,precision=True,package='1206',note='0.1% 750k; <=110V each at440V input; differential-voltage spacing rule')
            resistor(c,'10k',f'{tag}_ADCIN','PGND',p,precision=True)
            cap(c,'1n/50V/0603',f'{tag}_ADCIN','PGND',p)
            c.add('U','AMC1311BDWVR','AIPE:V3_AMC1311_DWV',{1:'S_5V',2:f'{tag}_ADCIN',3:'PGND',4:'PGND',5:GND,6:f'{tag}_N',7:f'{tag}_P',8:'3V3'},page=p,kind='IC',mpn='AMC1311BDWVR',maker=TI,source=DS.format('amc1311'),definitions=AMC1311_PINS)
            for a,b in [('S_5V','PGND'),('3V3',GND)]:cap(c,'100n/50V/0603',a,b,p);cap(c,'1u/50V/0805',a,b,p)
    bias(c,'S','07_sense_bias',sense=True)
    p='08_interface'
    with c.block('cable','Keyed SELV cable and fail-safe receive inputs'):
        keyed(c,p)
        for sig in ['PWM_H','PWM_L','DRV_RESET','BIAS_EN']:
            resistor(c,'33',sig,sig+'_F',p)
            resistor(c,'10k',sig+'_F',GND,p)
            cap(c,'100p/50V/0603',sig+'_F',GND,p)
        cap(c,'10u/25V/1210','12V_E',GND,p)
        cap(c,'1u/50V/0805','3V3',GND,p)
    mounts(c,p)
    return c

def control_supply(c):
    p='01_supply'
    with c.block('entry','12 V electronics entry: independent 2 A protection'):
        c.add('J','12 V ELECTRONICS','TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',{1:'12V_IN',2:GND},page=p,kind='J',mpn='1715022',maker='Phoenix Contact',source='https://www.phoenixcontact.com/en-pc/products/1715022')
        diode(c,'SMBJ15A','Diode_SMD:D_SMB','12V_IN',GND,p,source='https://www.littelfuse.com/products/tvs-diodes/surface-mount/smbj')
        ic(c,'TPS26400PWPR',{1:'12V_IN',2:'12V_IN',3:'E_UV',5:'E_OV',6:None,7:'E_EN',8:'E_RTN',9:GND,10:'E_IMON',11:'E_ILIM',12:'E_DVDT',14:'AUX_OK_N',15:'12V_E',16:'12V_E',17:'E_RTN'},p,
           note='Separate from contactor coil supply; latched/circuit-breaker mode per datasheet; layout RTN isolated from GND as required')
        for v,a,b in [('107k','12V_IN','E_UV'),('4.42k','E_UV','E_OV'),('10k','E_OV','E_RTN'),('6.04k','E_ILIM','E_RTN'),('14.7k','E_IMON','E_RTN'),('100k','12V_IN','E_EN'),('10k','3V3','AUX_OK_N')]:resistor(c,v,a,b,p)
        cap(c,'100n/50V/0603','E_DVDT','E_RTN',p)
        cap(c,'100n/50V/0603','12V_IN',GND,p)
        cap(c,'100u/25V/elec','12V_E',GND,p)
        tp(c,'E_IMON',p)
    with c.block('buck','5 V logic / sensor buck supply'):
        ic(c,'TPS54302DDCR',{1:GND,2:'SW5',3:'12V_E',4:'FB5',5:'EN5',6:'BST5'},p)
        cap(c,'10u/50V/1210','12V_E',GND,p);cap(c,'100n/50V/0603','12V_E',GND,p)
        cap(c,'100n/50V/0603','BST5','SW5',p)
        resistor(c,'100k','12V_E','EN5',p);resistor(c,'20k','EN5',GND,p)
        c.add('L','10uH','Inductor_SMD:L_Coilcraft_MSS1048-XXX',{1:'SW5',2:'5V'},page=p,kind='L',mpn='MSS1048-103MLC',maker='Coilcraft',source='https://www.coilcraft.com/en-us/products/power/shielded-inductors/ferrite-drum/mss-mos/mss1048/')
        for _ in range(2):cap(c,'22u/25V/1210','5V',GND,p)
        cap(c,'220u/16V/radial','5V',GND,p)
        resistor(c,'100k','5V','FB5',p);resistor(c,'13.3k','FB5',GND,p)
        cap(c,'100p/50V/0603','5V','FB5',p,note='Feed-forward design selection; verify loop transient with actual output capacitance')
    with c.block('ldo','Core-first 1.9 V / 3.3 V supply sequencing'):
        ic(c,'TPS767D301PWPR',{3:GND,4:GND,5:'5V',6:'5V',9:GND,10:'IO_EN_N',11:'5V',12:'5V',17:'3V3',18:'3V3',22:'XRS_N',23:'1V9',24:'1V9',25:'FB19',28:'CORE_OK',29:GND},p)
        for v,a,b in [('18.2k','1V9','FB19'),('30.1k','FB19',GND),('10k','5V','CORE_OK'),('10k','5V','IO_EN_N'),('10k','CORE_OK','SEQ_B'),('100k','SEQ_B',GND)]:resistor(c,v,a,b,p)
        ic(c,'MMBT3904,215',{1:'SEQ_B',2:GND,3:'IO_EN_N'},p,prefix='Q')
        ic(c,'BAT54,215',{1:'XRS_N',3:'CORE_OK'},p,prefix='D')
        cap(c,'22u/25V/1210','5V',GND,p);cap(c,'100n/50V/0603','5V',GND,p)
        for rail in ['1V9','3V3']:
            resistor(c,'0.1',rail,rail+'_BULK',p,package='0805',mpn='RL0805FR-070R1L',maker='Yageo')
            cap(c,'100u/6.3V/polymer',rail+'_BULK',GND,p,note='0.1 ohm series damping + polymer ESR for LDO stability; validate load range')
    with c.block('reset','Supply supervisor; reset also clears the hardware latch'):
        ic(c,'TPS3808G01DBVR',{1:'XRS_N',2:GND,3:'MR_N',4:'RESET_CT',5:'MON5',6:'3V3'},p)
        resistor(c,'101k','5V','MON5',p);resistor(c,'10k','MON5',GND,p)
        resistor(c,'4.7k','3V3','XRS_N',p)
        cap(c,'10n/50V/0603','RESET_CT',GND,p);cap(c,'100n/50V/0603','3V3',GND,p)
        c.header(2,{1:'MR_N',2:GND},p,note='RESET input')

def control_dsp(c):
    # Pin-name-based V3 assignment is independently checked against the verified manufacturer PGF table.
    gpio={'GPIO0':'EPWM_A','GPIO1':'EPWM_B','GPIO2':'ARM_PULSE','GPIO3':'MAIN_CMD','GPIO4':'PRE_CMD',
          'GPIO5':'DRV_RESET','GPIO6':'BIAS_EN','GPIO7':'FLT_H_N','GPIO8':'FLT_L_N','GPIO9':'RDY_H','GPIO10':'RDY_L',
          'GPIO11':'RUN_ENABLE','GPIO12':'ARMED','GPIO13':'CURRENT_OK','GPIO14':'VOLTAGE_OK','GPIO15':'THERM_OK',
          'GPIO16':'AUX_OK_N','GPIO17':'PG_H_N','GPIO18':'PG_L_N','GPIO19':'PG_S_N','GPIO20':'MAIN_FB','GPIO21':'PRE_FB',
          'GPIO24':'FAN_TACH','GPIO25':'TH_H_PWM','GPIO26':'TH_L_PWM','GPIO28':'UART_RX','GPIO29':'UART_TX',
          'GPIO84':'BOOT84','GPIO85':'BOOT85','GPIO86':'BOOT86','GPIO87':'BOOT87'}
    named={'ADCINA0':'ADC_BUS','ADCINA1':'ADC_CURRENT','ADCINA2':'ADC_RAW','ADCINA3':'ADC_OUT','ADCINA4':'ADC_TEMP',
           'ADCINA5':'ADC_IREF','ADCINB0':'ADC_V12','ADCREFM':'ADCREFM','ADCREFP':'ADCREFP','ADCRESEXT':'ADCRESEXT','XRS':'XRS_N','XCLKIN':'CLK30',
           **{x:x for x in ['TDI','TDO','TCK','TMS','TRST','EMU0','EMU1']},**gpio}
    source=ROOT/'examples/sic-buck-400v-200v-5kw/components/tms320f28335_pgf_pins.csv'
    defs,nets={},{}
    with source.open(encoding='utf-8') as handle:
        rows=list(csv.DictReader(handle))
    for row in rows:
        n,name=row['pin'],row['name'];typ='bidirectional' if name.startswith('GPIO') or name in ['EMU0','EMU1'] else 'input'
        if name.startswith(('VDD','VSS')):typ='power_in'
        if name in ['TEST1','TEST2']:typ='no_connect'
        if name in ['X2','XRD','XCLKOUT','ADCREFP','ADCREFM','TDO']:typ='output'
        if name=='XRS':typ='open_collector'
        net=named.get(name)
        if name in ['VDD','VDD1A18','VDD2A18']:net='1V9'
        elif name.startswith('VDD'):net='3V3'
        elif name.startswith('VSS') or name in ['ADCLO','ADCREFIN','X1']:net=GND
        elif name.startswith('ADCIN') and name not in named:net=GND
        defs[n]={'name':name,'type':typ};nets[n]=net
    assert len(nets)==176
    with c.block('dsp','TMS320F28335; ePWM dead-band + asynchronous TZ inputs'):
        u=c.add('U','TMS320F28335PGFA','Package_QFP:LQFP-176_24x24mm_P0.5mm',nets,page='02_dsp',kind='DSP',mpn='TMS320F28335PGFA',maker=TI,source=DS.format('tms320f28335'),definitions=defs)
    p='03_bypass'
    with c.block('pin_bypass','Per-pin capacitors; placement tied to actual DSP supply-pad positions'):
        for n in nets:
            if defs[n]['name'].startswith('VDD'):
                part=cap(c,'100n/50V/0603',nets[n],GND,p,note=f'DSP {u["ref"]}.{n} {defs[n]["name"]}; target supply-pin branch <=2 mm')
                part['near_dsp_pin']=n
        for rail in ['1V9','1V9','3V3','3V3']:cap(c,'2.2u/25V/0805',rail,GND,p)
        for rail in ['ADCREFM','ADCREFP']:cap(c,'2.2u/25V/0805',rail,GND,p,note='At reference pin, quiet ground return')
        resistor(c,'22k','ADCRESEXT',GND,p,precision=True)
    p='04_debug'
    with c.block('clock','30 MHz clock and boot straps'):
        ic(c,'ASV-30.000MHZ-EJ-T',{1:'3V3',2:GND,3:'CLK_SRC',4:'3V3'},p,prefix='Y')
        resistor(c,'33','CLK_SRC','CLK30',p)
        cap(c,'100n/50V/0603','3V3',GND,p)
        for net in ['BOOT84','BOOT85','BOOT86','BOOT87','TMS','TDI','EMU0','EMU1']:resistor(c,'10k','3V3',net,p)
        resistor(c,'2.2k','TRST',GND,p)
    with c.block('debug','JTAG and 3.3 V UART; accessible control domain only'):
        c.header(14,{1:'TMS',2:'TRST',3:'TDI',4:GND,5:'3V3',6:None,7:'TDO',8:GND,9:'TCK',10:GND,11:'TCK',12:GND,13:'EMU0',14:'EMU1'},p,rows=2,note='TI 14-pin JTAG; pin6 key')
        c.header(4,{1:'3V3',2:'UART_TX',3:'UART_RX',4:GND},p,note='3.3 V UART; external cable length <=100 mm')
        resistor(c,'10k','3V3','UART_RX',p)

def control_analog(c):
    p='05_analog'
    with c.block('voltage_receive','Balanced differential voltage receivers; output = 1.5 x differential input'):
        amp={4:'5V',11:GND}
        pins=[(1,2,3),(7,6,5),(8,9,10)]
        for tag,(out,minus,plus) in zip(['RAW','BUS','OUT'],pins):
            amp.update({out:tag+'_V',minus:tag+'_M',plus:tag+'_A'})
            for value,a,b in [('10k',tag+'_N',tag+'_M'),('15k',tag+'_V',tag+'_M'),('10k',tag+'_P',tag+'_A'),('15k',tag+'_A',GND)]:resistor(c,value,a,b,p,precision=True)
            cap(c,'100p/50V/0603',tag+'_V',tag+'_M',p);cap(c,'100p/50V/0603',tag+'_A',GND,p)
        amp.update({12:'MID_DIV',13:'MID1V5',14:'MID1V5'})
        ic(c,'OPA4192IPWR',amp,p,note='Three voltage receivers + midpoint buffer; 5V supply, minimum4.5V')
        cap(c,'100n/50V/0603','5V',GND,p);cap(c,'1u/50V/0805','5V',GND,p)
        ic(c,'REF3130AIDBZR',{1:'5V',2:'REF3',3:GND},p)
        cap(c,'1u/50V/0805','5V',GND,p);cap(c,'1u/50V/0805','REF3',GND,p)
        resistor(c,'10k','REF3','MID_DIV',p,precision=True);resistor(c,'10k','MID_DIV',GND,p,precision=True)
        cap(c,'100n/50V/0603','MID_DIV',GND,p)
    with c.block('current','Bipolar current measurement; buffered actual sensor reference'):
        c.add('J','LEM HO 50-S-0100','Connector_JST:JST_PH_B5B-PH-K_1x05_P2.00mm_Vertical',{1:'5V',2:GND,3:'I_RAW',4:'I_REF',5:'I_OCD_RAW'},page=p,kind='J',mpn='B5B-PH-K-S',maker='JST',source='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',note='LEM p16:1 supply,2 GND,3 output,4 reference,5 OCD. REQUIRED4.7k pullup pin5-to-pin1 at SENSOR END of cable; local3.3k/10k makes unplugged cable inhibit')
        cap(c,'1u/50V/0805','5V',GND,p);cap(c,'100n/50V/0603','5V',GND,p)
        u=ic(c,'OPA2320AIDGKR',{1:'I_REF_BUF',2:'I_REF_BUF',3:'I_REF',4:GND,5:'I_A',6:'I_M',7:'I_V',8:'5V'},p,note='A buffers sensor 130–300 ohm reference; B outputs1.5 +2*(Vout-Vref)')
        start=len(c.parts)
        for value,a,b in [('10k','I_REF_BUF','I_M'),('20k','I_V','I_M'),('10k','I_RAW','I_A'),('20k','MID1V5','I_A')]:resistor(c,value,a,b,p,precision=True)
        cap(c,'100p/50V/0603','I_V','I_M',p);cap(c,'100p/50V/0603','I_A','MID1V5',p)
        for part in c.parts[start:]:part['schematic_owner']=u['ref']+':2'
        cap(c,'100n/50V/0603','5V',GND,p)
        resistor(c,'3.3k','I_OCD_RAW','I_OCD_N',p)
        resistor(c,'10k','I_OCD_N',GND,p,note='Fail-low on cable open; with sensor-end4.7k pullup gives2.78V nominal and2.50V at4.5V supply')
        for net in ['I_RAW','I_REF']:resistor(c,'1M',net,GND,p,note='Weak broken-wire bias; reference loading <=2.5uA, <=0.75mV at300ohm source')
    with c.block('adc','ADC charge reservoirs and input protection'):
        for raw,adc in [('BUS_V','ADC_BUS'),('RAW_V','ADC_RAW'),('OUT_V','ADC_OUT'),('I_V','ADC_CURRENT'),('I_REF_BUF','ADC_IREF'),('TEMP_V','ADC_TEMP'),('V12_DIV','ADC_V12')]:
            resistor(c,'220',raw,adc,p)
            cap(c,'1n/50V/0603',adc,GND,p,note='0.22 us input RC; >=1us acquisition window, verify driver settling')
            # Discrete Schottky clamps use 3V3 rather than loading the precision reference.
            ic(c,'BAT54,215',{1:adc,3:'3V3'},p,prefix='D')
            ic(c,'BAT54,215',{1:GND,3:adc},p,prefix='D')
        resistor(c,'43k','12V_E','V12_DIV',p,precision=True);resistor(c,'10k','V12_DIV',GND,p,precision=True)
        ic(c,'LM61CIM3/NOPB',{1:'3V3',2:'TEMP_V',3:GND},p)
        cap(c,'100n/50V/0603','3V3',GND,p)

def and4(c,inputs,output,p):
    assert len(inputs)==8
    ic(c,'SN74LV21APWR',{1:inputs[0],2:inputs[1],4:inputs[2],5:inputs[3],6:output[0],7:GND,8:output[1],9:inputs[4],10:inputs[5],12:inputs[6],13:inputs[7],14:'3V3'},p)
    cap(c,'100n/50V/0603','3V3',GND,p,note='Dedicated bypass at this logic IC VCC pin, target <=2mm')

def control_trip(c):
    p='06_trip'
    with c.block('thresholds','Hardware current window ±38 A, OVP225 V and UVLO340 V'):
        for tag,top,bottom in [('I_LO','90.9k','9.53k'),('I_HI','9.53k','90.9k'),('V_OV','34k','100k'),('V_UV','77k','100k'),('V_BUSOV','33.2k','100k')]:
            resistor(c,top,'REF3',tag,p,precision=True);resistor(c,bottom,tag,GND,p,precision=True)
            cap(c,'100n/50V/0603',tag,GND,p)
        for raw,protected in [('I_V','I_CMP'),('BUS_V','BUS_CMP'),('RAW_V','RAW_CMP'),('OUT_V','OUT_CMP')]:
            resistor(c,'1k',raw,protected,p,note='Limits comparator clamp current if 5V amplifier saturates; supply sequencing/back-power remains a qualification item')
            ic(c,'BAT54,215',{1:protected,3:'3V3'},p,prefix='D');ic(c,'BAT54,215',{1:GND,3:protected},p,prefix='D')
        ic(c,'TLV3202AIDGKR',{1:'I_LOW_OK',2:'I_LO',3:'I_CMP',4:GND,5:'I_HI',6:'I_CMP',7:'I_HIGH_OK',8:'3V3'},p,note='Push-pull comparator outputs enter logic gates; never wire-OR')
        ic(c,'TLV3202AIDGKR',{1:'V_LOW_OK',2:'V_UV',3:'BUS_CMP',4:GND,5:'V_OV',6:'OUT_CMP',7:'V_HIGH_OK',8:'3V3'},p)
        ic(c,'TLV3202AIDGKR',{1:'BUS_OV_OK',2:'BUS_CMP',3:'V_BUSOV',4:GND,5:'V_BUSOV',6:'RAW_CMP',7:'RAW_OV_OK',8:'3V3'},p,note='452V nominal raw-input and DC-link overvoltage inhibit; functional surge rating is a separate qualification')
        for _ in range(3):cap(c,'100n/50V/0603','3V3',GND,p)
    with c.block('logic','Power-good polarity, asynchronous fault tree and latched inhibit'):
        ic(c,'SN74LV04APWR',{1:'PG_H_N',2:'PG_H_OK',3:'PG_L_N',4:'PG_L_OK',5:'PG_S_N',6:'PG_S_OK',7:GND,8:'COIL_INHIBIT',9:'SYSTEM_OK',10:None,11:GND,12:None,13:GND,14:'3V3'},p)
        cap(c,'100n/50V/0603','3V3',GND,p)
        and4(c,['I_LOW_OK','I_HIGH_OK','I_OCD_N','3V3','V_LOW_OK','V_HIGH_OK','BUS_OV_OK','RAW_OV_OK'],['CURRENT_OK','VOLTAGE_OK'],p)
        and4(c,['FLT_H_N','FLT_L_N','RDY_H','RDY_L','PG_H_OK','PG_L_OK','PG_S_OK','AUX_OK_N'],['DRIVERS_OK','BIAS_OK'],p)
        and4(c,['CURRENT_OK','VOLTAGE_OK','DRIVERS_OK','BIAS_OK','THERM_OK','XRS_N','3V3','3V3'],['STAGE_OK','SYSTEM_OK'],p)
        ic(c,'SN74LVC2G08DCTR',{1:'STAGE_OK',2:'SYSTEM_OK',3:'PWM_ENABLE',4:GND,5:'ARMED',6:'RUN_ENABLE',7:'ALL_GOOD',8:'3V3'},p)
        cap(c,'100n/50V/0603','3V3',GND,p)
        ic(c,'SN74LVC1G74DCTR',{1:'ARM_PULSE',2:'3V3',3:'TRIPPED',4:GND,5:'ARMED',6:'ALL_GOOD',7:'3V3',8:'3V3'},p,
           note='Async clear has priority; DSP reset forces latch clear; manual re-arm edge only after all causes clear; Q also TZ1')
        cap(c,'100n/50V/0603','3V3',GND,p)
        ic(c,'SN74LVC2G08DCTR',{1:'EPWM_A',2:'PWM_ENABLE',3:'PWM_L_SRC',4:GND,5:'EPWM_B',6:'PWM_ENABLE',7:'PWM_H_SRC',8:'3V3'},p)
        cap(c,'100n/50V/0603','3V3',GND,p)
        for net in ['RUN_ENABLE','ARM_PULSE','EPWM_A','EPWM_B','DRV_RESET','BIAS_EN']:resistor(c,'10k',net,GND,p)
        for tag in ['H','L']:resistor(c,'33',f'PWM_{tag}_SRC',f'PWM_{tag}',p)
        tp(c,'TRIPPED',p);tp(c,'ALL_GOOD',p)

def control_actuation(c):
    p='07_actuate'
    with c.block('coil_supply','Dedicated 12 V coil/fan branch; external 8 A fuse and return'):
        c.add('J','12 V COIL / FAN','TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',{1:'12V_COIL',2:GND},page=p,kind='J',mpn='1715022',maker='Phoenix Contact',note='Separate supply harness branch; both contactors <=7.6A/130ms; never through electronics eFuse')
        cap(c,'100u/25V/elec','12V_COIL',GND,p)
    with c.block('coils','Main and precharge drivers; fail-safe default off'):
        for tag in ['MAIN','PRE']:
            c.add('J',tag+' COIL','TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',{1:'12V_COIL',2:tag+'_LOW'},page=p,kind='J',mpn='1715022',maker='Phoenix Contact')
            # Power FET rather than a SOT23 part carrying a 3.8 A pickup pulse.
            c.add('Q','IRLZ44NPBF','Package_TO_SOT_THT:TO-220-3_Vertical',{1:tag+'_G',2:tag+'_LOW',3:GND},page=p,kind='Q',mpn='IRLZ44NPBF',maker='Infineon',source='https://www.infineon.com/part/IRLZ44N',definitions=pin_defs('1:G:input 2:D:passive 3:S:passive'),note='Needs5V gate drive; 55V FET with logic-level specification; exact on-resistance at5V and cooling reviewed')
            resistor(c,'100',tag+'_DRIVE',tag+'_G',p);resistor(c,'10k',tag+'_G',GND,p)
            diode(c,'SSC54-E3/57T','Diode_SMD:D_SMC','12V_COIL',tag+'_LOW',p,source='https://www.vishay.com/docs/88885/ssc53l.pdf',note='External suppression; EV200 internal economizer clamps coil back EMF')
        # TTL-compatible 5V buffer needed; standard 74LVC at5V cannot guarantee 3V3 input VIH.
        c.add('U','SN74AHCT125PWR','Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
              {1:'COIL_INHIBIT',2:'MAIN_CMD',3:'MAIN_DRIVE',4:'COIL_INHIBIT',5:'PRE_CMD',6:'PRE_DRIVE',7:GND,8:None,9:GND,10:'5V',11:None,12:GND,13:'5V',14:'5V'},
              page=p,kind='IC',mpn='SN74AHCT125PWR',maker=TI,source=DS.format('sn74ahct125'),
              definitions=pin_defs('1:1OE_N:input 2:1A:input 3:1Y:tri_state 4:2OE_N:input 5:2A:input 6:2Y:tri_state 7:GND:power_in 8:3Y:tri_state 9:3A:input 10:3OE_N:input 11:4Y:tri_state 12:4A:input 13:4OE_N:input 14:VCC:power_in'))
        cap(c,'100n/50V/0603','5V',GND,p)
        for tag in ['MAIN','PRE']:resistor(c,'10k',tag+'_CMD',GND,p)
    with c.block('feedback','Contactor auxiliary contacts with manufacturer minimum wetting current'):
        for tag in ['MAIN','PRE']:
            c.add('J',tag+' AUX CONTACT','Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',{1:'12V_COIL',2:tag+'_AUX'},page=p,kind='J',mpn='TSW-102-07-G-S',maker='Samtec')
            for _ in range(2):resistor(c,'200',tag+'_AUX',GND,p,package='2512',mpn='CRCW2512200RFKEGHP',maker='Vishay',note='2W pulse-proof variant; two200R parallel ->100R; >=108mA at10.8V')
            resistor(c,'33k',tag+'_AUX',tag+'_FB',p);resistor(c,'10k',tag+'_FB',GND,p)
            cap(c,'10n/50V/0603',tag+'_FB',GND,p)
    with c.block('thermal','Fail-open thermal / emergency-stop loop and fan tachometer'):
        c.header(2,{1:'3V3',2:'THERM_OK'},p,note='Series NC90C sink thermostat + NC110C choke thermostat + NC ESTOP; cable open trips')
        resistor(c,'1k','THERM_OK',GND,p)
        c.header(3,{1:GND,2:'12V_COIL',3:'FAN_TACH'},p,note='12V fan; open-collector tach; fan failure checked by DSP')
        resistor(c,'4.7k','3V3','FAN_TACH',p)

def control():
    c=Circuit('control')
    control_supply(c);control_dsp(c);control_analog(c);control_trip(c);control_actuation(c)
    with c.block('cable','Keyed SELV harness to the power board'):
        keyed(c,'08_interface')
    mounts(c,'08_interface')
    return c

def write():
    d=EXAMPLE/'design';d.mkdir(parents=True,exist_ok=True)
    for c in [power(),control()]:
        (d/f'circuit_{c.board}.json').write_text(json.dumps(c.parts,indent=2)+'\n',encoding='utf-8')
        (d/f'groups_{c.board}.json').write_text(json.dumps({'groups':c.groups,'titles':c.block_titles},indent=2)+'\n',encoding='utf-8')
        print(f'V3 {c.board} model: {len(c.parts)} components; no CAD verification yet')

if __name__=='__main__':write()
