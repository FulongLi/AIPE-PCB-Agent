"""Electrical source of truth for the V1 converter; no CAD or implicit wiring."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/buck-48v-24v-1kw"
SO8 = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
EP8 = "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.95x4.9mm_Mask2.71x3.4mm"
SOT = "Package_TO_SOT_SMD:SOT-23"
SOT5 = "Package_TO_SOT_SMD:SOT-23-5"
SOT6 = "Package_TO_SOT_SMD:SOT-23-6"

# Each pin declaration is number:name:type. Types retain meaningful ERC semantics.
IC = {
    "UCC27211DDAR": (EP8,"1:VDD:power_in 2:HB:power_in 3:HO:output 4:HS:passive 5:HI:input 6:LI:input 7:VSS:power_in 8:LO:output 9:EP:power_in","ucc27211"),
    "LM5164DDAR": (EP8,"1:GND:power_in 2:VIN:power_in 3:EN:input 4:RON:passive 5:FB:input 6:PGOOD:open_collector 7:BST:passive 8:SW:power_out 9:EP:power_in","lm5164"),
    "TPS54302DDCR": (SOT6,"1:GND:power_in 2:SW:power_out 3:VIN:power_in 4:FB:input 5:EN:input 6:BOOT:passive","tps54302"),
    "TPS767D301PWPR": ("Package_SO:HTSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP2.85x5.4mm",
        "1:NC:no_connect 2:NC:no_connect 3:GND1:power_in 4:EN1_N:input 5:IN1:power_in 6:IN1:power_in 7:NC:no_connect 8:NC:no_connect 9:GND2:power_in 10:EN2_N:input 11:IN2:power_in 12:IN2:power_in 13:NC:no_connect 14:NC:no_connect 15:NC:no_connect 16:NC:no_connect 17:OUT2:power_out 18:OUT2:passive 19:NC:no_connect 20:NC:no_connect 21:NC:no_connect 22:RESET2_N:open_collector 23:OUT1:power_out 24:OUT1:passive 25:FB1:input 26:NC:no_connect 27:NC:no_connect 28:RESET1_N:open_collector 29:EP:power_in","tps767d3"),
    "INA240A1DR": (SO8,"1:IN-:input 2:GND:power_in 3:REF2:input 4:NC:no_connect 5:OUT:output 6:VS:power_in 7:REF1:input 8:IN+:input","ina240"),
    "LM2903BDR": (SO8,"1:OUT1:open_collector 2:IN1-:input 3:IN1+:input 4:GND:power_in 5:IN2+:input 6:IN2-:input 7:OUT2:open_collector 8:VCC:power_in","lm2903b"),
    "TLV9004IDR": ("Package_SO:SOIC-14_3.9x8.7mm_P1.27mm","1:OUT1:output 2:IN1-:input 3:IN1+:input 4:V+:power_in 5:IN2+:input 6:IN2-:input 7:OUT2:output 8:OUT3:output 9:IN3-:input 10:IN3+:input 11:V-:power_in 12:IN4+:input 13:IN4-:input 14:OUT4:output","tlv9004"),
    "REF3125AIDBZR": (SOT,"1:IN:power_in 2:OUT:power_out 3:GND:power_in","ref3125"),
    "LM61CIM3/NOPB": (SOT,"1:VS:power_in 2:OUT:output 3:GND:power_in","lm61"),
    "SN74LVC1G74DCTR": ("Package_SO:SSOP-8_2.95x2.8mm_P0.65mm","1:CLK:input 2:D:input 3:Q_N:output 4:GND:power_in 5:Q:output 6:CLR_N:input 7:PRE_N:input 8:VCC:power_in","sn74lvc1g74"),
    "SN74LVC2G08DCTR": ("Package_SO:SSOP-8_2.95x2.8mm_P0.65mm","1:1A:input 2:1B:input 3:2Y:output 4:GND:power_in 5:2A:input 6:2B:input 7:1Y:output 8:VCC:power_in","sn74lvc2g08"),
    "SN74LVC1G86DBVR": (SOT5,"1:A:input 2:B:input 3:GND:power_in 4:Y:output 5:VCC:power_in","sn74lvc1g86"),
    "SN74LVC1G08DBVR": (SOT5,"1:A:input 2:B:input 3:GND:power_in 4:Y:output 5:VCC:power_in","sn74lvc1g08"),
    "TPS3808G01DBVR": (SOT6,"1:RESET_N:open_collector 2:GND:power_in 3:MR_N:input 4:CT:passive 5:SENSE:input 6:VDD:power_in","tps3808"),
}


def pin_defs(text):
    return {n:dict(name=name,type=kind) for n,name,kind in (s.split(":") for s in text.split())}


class Circuit:
    def __init__(self):
        self.parts = []
        self.counters = {}

    def add(self, prefix, value, footprint, nets, *, page, kind="passive", mpn="", maker="", source="", definitions=None, ref=None, note="", xy=None):
        self.counters[prefix] = self.counters.get(prefix,0)+1
        ref = ref or prefix+str(self.counters[prefix])
        assert not any(p['ref']==ref for p in self.parts), ref
        nets = {str(k):v for k,v in nets.items()}
        definitions = definitions or {n:dict(name=n,type="passive") for n in nets}
        assert set(definitions) == set(nets), (ref, set(definitions)^set(nets))
        part = dict(ref=ref,value=value,footprint=footprint,nets=nets,page=page,kind=kind,
                    mpn=mpn,maker=maker,source=source,pins=definitions,note=note,xy=xy)
        self.parts.append(part)
        return part

    def resistor(self, value, a, b, page, note="", package="0805"):
        code = value.replace(".","R") if 'k' not in value and 'M' not in value else value.replace('k','K').replace('.','K')
        # Explicit decimal-resistance coding: 4.7k -> 4K7; 0.1 -> 0R1.
        if 'k' in value and '.' in value: code = value.replace('k','').replace('.','K')
        if value.startswith('0.'): code = '0R'+value[2:]
        if value.isdigit(): code += 'R'
        return self.add('R',value,f"Resistor_SMD:R_{package}_{'2012' if package=='0805' else '6332'}Metric",{1:a,2:b},page=page,kind='R',mpn=f"RC{package}FR-07{code}L",maker="Yageo",source="https://www.yageo.com/en/Chart/Download/pdf/RC0805",note=note)

    def cap(self, value, a, b, page, note=""):
        choices = {
            "100n/50V":("GRM21BR71H104KA01L","Murata","0805_2012Metric"),
            "2.2u/100V":("CGA6N3X7R2A225K230AB","TDK","1210_3225Metric"),
            "2.2u/25V":("GRM21BR71E225KA73L","Murata","0805_2012Metric"),
            "22u/25V":("TMK325B7226KMHT","Taiyo Yuden","1210_3225Metric"),
            "1n/50V":("C0805C102J5GACTU","KEMET","0805_2012Metric"),
            "2.2n/50V":("C0805C222K5RACTU","KEMET","0805_2012Metric"),
            "3.3n/50V":("C0805C332K5RACTU","KEMET","0805_2012Metric"),
            "56p/50V":("C0805C560J5GACTU","KEMET","0805_2012Metric"),
            "10n/50V":("C0805C103K5RACTU","KEMET","0805_2012Metric"),
        }
        mpn,maker,package=choices[value]
        return self.add('C',value,'Capacitor_SMD:C_'+package,{1:a,2:b},page=page,kind='C',mpn=mpn,maker=maker,note=note,
                        source="https://www.ti.com/lit/ds/symlink/lm5164.pdf" if value in ('2.2u/100V','22u/25V') else "Manufacturer series specification; exact order code requires BOM review")

    def ic(self, mpn, nets, page, note=""):
        footprint, declaration, source = IC[mpn]
        defs=pin_defs(declaration)
        nets={str(k):v for k,v in nets.items()}
        for n,p in defs.items():
            if p['type']=='no_connect': nets.setdefault(n,None)
        return self.add('U',mpn,footprint,nets,page=page,kind='IC',mpn=mpn,maker="Texas Instruments",source=source,definitions=defs,note=note)

    def header(self, count, nets, page, note="", rows=1):
        label=f"{rows}x{count//rows:02}"
        return self.add('J',note or label,f"Connector_PinHeader_2.54mm:PinHeader_{label}_P2.54mm_Vertical",nets,page=page,kind='J',maker='Samtec',mpn=f"TSW-{count//rows:03}-07-G-{'S' if rows==1 else 'D'}",source='https://www.samtec.com/products/tsw',note=note)

    def diode(self, cathode, anode, page, note=""):
        return self.add('D','BAT54','Package_TO_SOT_SMD:SOT-23',{1:anode,2:None,3:cathode},page=page,kind='IC',maker='Nexperia',mpn='BAT54,215',source='https://assets.nexperia.com/documents/data-sheet/BAT54_SER.pdf',definitions=pin_defs('1:A:passive 2:NC:no_connect 3:K:passive'),note=note)


def build():
    c=Circuit()
    for value,net in [('VIN+','VIN_RAW'),('VIN-','GND'),('VOUT+','VOUT'),('VOUT-','GND')]:
        c.add('J',value,'TerminalBlock_Wuerth:Wuerth_REDCUBE-THR_WP-THRSH_74651195_THR',{1:net},page='01_power',kind='J',mpn='74651195',maker='Wurth Elektronik',source='74651195',note='M5; 85 A at 20 C conditional on PCB and cable; support during torque')
    c.add('F','40A/70V','AIPE:MIDI_70V_M6_P30',{1:'VIN_RAW',2:'VIN'},page='01_power',mpn='4998040.M-NH',maker='Littelfuse',source='https://www.littelfuse.com/assetdocs/littelfuse-datasheet-4998-midihp70v?assetguid=b72fcd7a-c66d-4916-844c-ac55ebed196c',note='Bolt-down; hardware and insulating support required')
    c.add('D','SMCJ54A','Diode_SMD:D_SMC',{1:'VIN',2:'GND'},page='01_power',kind='D',mpn='SMCJ54A-13-F',maker='Diodes Incorporated',source='https://www.diodes.com/part/view/SMCJ54A',note='54 V standoff; 87.1 V max specified pulse clamp, not hotplug qualification')
    for _ in range(14):
        c.add('C','470u/100V','Capacitor_THT:CP_Radial_D18.0mm_P7.50mm',{1:'VIN',2:'GND'},page='02_capacitors',kind='C',mpn='EKY-101ELL471MM25S',maker='Nippon Chemi-Con',source='https://www.chemi-con.co.jp/en/products/detail-condenser.php?part_number=EKY-101ELL471MM25S',note='1.75 Arms at 105 C / 100 kHz; 36 mohm impedance max at 20 C')
    for _ in range(8): c.cap('2.2u/100V','VIN','GND','01_power','Local commutation bypass; do not credit nominal capacitance under bias')
    for gate,drain,source in [('GH1','VIN','SW'),('GH2','VIN','SW'),('GL1','SW','GND'),('GL2','SW','GND')]:
        c.add('Q','CSD19536KCS','Package_TO_SOT_THT:TO-220-3_Vertical',{1:gate,2:drain,3:source},page='01_power',kind='Q',mpn='CSD19536KCS',maker='Texas Instruments',source='csd19536kcs',definitions=pin_defs('1:G:input 2:D:passive 3:S:passive'),note='Tab=drain. Individual insulated thermal interface required.')
        c.resistor('4.7','HO' if gate.startswith('GH') else 'LO',gate,'03_gate')
        c.resistor('10k',gate,source,'03_gate')
    c.add('L','10uH/83A','AIPE:IHXL2000VZ_10uH_Upright',{1:'SW',2:'IL_FORCE'},page='01_power',kind='L',mpn='IHXL2000VZEB100M3A',maker='Vishay',source='ihxl2000vz-3a',note='83 A thermal / 83 A at 20% L drop; 0.86 mohm max; custom support required')
    c.add('R','2m/6W/Kelvin','AIPE:CSS4J_4026_Kelvin',{1:'IL_FORCE',2:'VOUT',3:'ISENSE_P',4:'ISENSE_N'},page='01_power',kind='SHUNT',mpn='CSS4J-4026K-2L00F',maker='Bourns',source='css4j-4026',note='6 W at 70 C terminal; 1%; 4-terminal')
    for _ in range(4):
        c.add('C','1000u/50V','Capacitor_THT:CP_Radial_D16.0mm_P7.50mm',{1:'VOUT',2:'GND'},page='02_capacitors',kind='C',mpn='EKY-500ELL102ML25S',maker='Nippon Chemi-Con',source='https://www.chemi-con.co.jp/en/products/detail-condenser.php?part_number=EKY-500ELL102ML25S',note='2.555 Arms / 25 mohm impedance at 100 kHz')
    for _ in range(2): c.cap('22u/25V','AUX12','GND','03_gate')
    c.resistor('10k','VIN','GND','02_capacitors',package='2512',note='Input bleeder ~0.23 W nominal')
    c.resistor('2.4k','VOUT','GND','02_capacitors',package='2512',note='Output bleeder 0.24 W nominal')
    c.ic('UCC27211DDAR',{1:'AUX12',2:'BOOT',3:'HO',4:'SW',5:'HI',6:'LI',7:'GND',8:'LO',9:'GND'},'03_gate')
    c.cap('2.2u/25V','BOOT','SW','03_gate'); c.cap('100n/50V','BOOT','SW','03_gate')
    c.cap('100n/50V','AUX12','GND','03_gate')
    for net in ('HI','LI'): c.resistor('10k',net,'GND','03_gate')
    c.ic('LM5164DDAR',{1:'GND',2:'VIN',3:'VIN',4:'RON12',5:'FB12',6:'PG12_N',7:'BST12',8:'SW12',9:'GND'},'04_aux12')
    for _ in range(2): c.cap('2.2u/100V','VIN','GND','04_aux12')
    c.cap('2.2n/50V','BST12','SW12','04_aux12')
    c.add('L','68uH','Inductor_SMD:L_Coilcraft_MSS1246T-XXX',{1:'SW12',2:'AUX12'},page='04_aux12',kind='L',mpn='MSS1246T-683MLC',maker='Coilcraft',source='lm5164')
    for _ in range(2): c.cap('22u/25V','AUX12','GND','04_aux12')
    for value,a,b in [('100k','RON12','GND'),('453k','AUX12','FB12'),('49.9k','FB12','GND'),('453k','SW12','RIPPLE12'),('10k','3V3','PG12_N')]: c.resistor(value,a,b,'04_aux12')
    c.cap('3.3n/50V','RIPPLE12','AUX12','04_aux12'); c.cap('56p/50V','RIPPLE12','FB12','04_aux12')
    c.ic('TPS54302DDCR',{1:'GND',2:'SW5',3:'AUX12',4:'FB5',5:'EN5',6:'BST5'},'05_aux5')
    c.resistor('100k','AUX12','EN5','05_aux5'); c.resistor('20k','EN5','GND','05_aux5')
    c.cap('100n/50V','BST5','SW5','05_aux5')
    c.cap('22u/25V','AUX12','GND','05_aux5'); c.cap('100n/50V','AUX12','GND','05_aux5')
    c.add('L','10uH','Inductor_SMD:L_Coilcraft_MSS1048-XXX',{1:'SW5',2:'5V'},page='05_aux5',kind='L',mpn='MSS1048-103MLC',maker='Coilcraft',source='https://www.coilcraft.com/en-us/products/power/shielded-inductors/ferrite-drum/mss-mos/mss1048/mss1048-103/')
    for _ in range(2): c.cap('22u/25V','5V','GND','05_aux5')
    c.resistor('100k','5V','FB5','05_aux5'); c.resistor('13.3k','FB5','GND','05_aux5'); c.cap('56p/50V','5V','FB5','05_aux5')
    c.add('C','220u/16V','Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',{1:'5V',2:'GND'},page='05_aux5',kind='C',mpn='EEU-FR1C221',maker='Panasonic',source='https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models/EEUFR1C221',note='Bulk hold-up; power-down timing needs measurement')
    c.ic('TPS767D301PWPR',{3:'GND',4:'GND',5:'5V',6:'5V',9:'GND',10:'IO_EN_N',11:'5V',12:'5V',17:'3V3',18:'3V3',22:'XRS_N',23:'1V9',24:'1V9',25:'FB19',28:'CORE_OK',29:'GND'},'06_dsp_supplies')
    # Datasheet reference = 1.1834 V; 18.2k / 30.1k sets 1.899 V.
    c.resistor('18.2k','1V9','FB19','06_dsp_supplies'); c.resistor('30.1k','FB19','GND','06_dsp_supplies')
    c.resistor('10k','5V','CORE_OK','06_dsp_supplies'); c.resistor('10k','5V','IO_EN_N','06_dsp_supplies')
    c.resistor('10k','CORE_OK','SEQ_BASE','06_dsp_supplies'); c.resistor('100k','SEQ_BASE','GND','06_dsp_supplies')
    c.add('Q','MMBT3904','Package_TO_SOT_SMD:SOT-23',{1:'SEQ_BASE',2:'GND',3:'IO_EN_N'},page='06_dsp_supplies',kind='IC',mpn='MMBT3904,215',maker='Nexperia',source='https://assets.nexperia.com/documents/data-sheet/MMBT3904.pdf',definitions=pin_defs('1:B:input 2:E:passive 3:C:open_collector'))
    c.diode('CORE_OK','XRS_N','06_dsp_supplies','Core failure asserts reset without 5 V pull-up on DSP')
    for rail in ('1V9','3V3'):
        c.resistor('0.1',rail,rail+'_BULK','06_dsp_supplies','Explicit output-capacitor ESR for LDO stability')
        c.add('C','100u/6.3V','Capacitor_SMD:CP_Elec_6.3x5.8',{1:rail+'_BULK',2:'GND'},page='06_dsp_supplies',kind='C',mpn='6SVP100M',maker='Panasonic',source='https://industrial.panasonic.com/ww/products/pt/os-con/models/6SVP100M',note='Low ESR polymer in series with 0.1 ohm; verify LDO stability')
    c.cap('100n/50V','5V','GND','06_dsp_supplies'); c.cap('22u/25V','5V','GND','06_dsp_supplies')
    c.ic('TPS3808G01DBVR',{1:'XRS_N',2:'GND',3:'3V3',4:'RESET_CT',5:'MON5',6:'3V3'},'06_dsp_supplies')
    c.resistor('105k','5V','MON5','06_dsp_supplies'); c.resistor('10k','MON5','GND','06_dsp_supplies')
    c.cap('10n/50V','RESET_CT','GND','06_dsp_supplies'); c.cap('100n/50V','3V3','GND','06_dsp_supplies')
    c.resistor('10k','3V3','XRS_N','06_dsp_supplies')
    c.header(2,{1:'XRS_N',2:'GND'},'06_dsp_supplies','RESET')

    # Sense/protection nets retain distinct Kelvin force/sense connections.
    c.ic('INA240A1DR',{1:'ISENSE_N_F',2:'GND',3:'GND',5:'CURRENT_RAW',6:'3V3',7:'GND',8:'ISENSE_P_F'},'07_sensing')
    c.resistor('10','ISENSE_P','ISENSE_P_F','07_sensing'); c.resistor('10','ISENSE_N','ISENSE_N_F','07_sensing')
    c.cap('1n/50V','ISENSE_P_F','ISENSE_N_F','07_sensing'); c.cap('100n/50V','3V3','GND','07_sensing')
    c.resistor('121k','VIN','VIN_DIV','07_sensing'); c.resistor('4.99k','VIN_DIV','GND','07_sensing'); c.cap('1n/50V','VIN_DIV','GND','07_sensing')
    c.resistor('49.9k','VOUT','VOUT_DIV','07_sensing'); c.resistor('4.99k','VOUT_DIV','GND','07_sensing'); c.cap('1n/50V','VOUT_DIV','GND','07_sensing')
    c.ic('LM61CIM3/NOPB',{1:'3V3',2:'TEMP_RAW',3:'GND'},'07_sensing','Place adjacent to the low-side MOSFET area')
    c.cap('100n/50V','3V3','GND','07_sensing')
    c.ic('TLV9004IDR',{1:'VIN_BUF',2:'VIN_BUF',3:'VIN_DIV',4:'3V3',5:'VOUT_DIV',6:'VOUT_BUF',7:'VOUT_BUF',8:'CURRENT_BUF',9:'CURRENT_BUF',10:'CURRENT_RAW',11:'GND',12:'TEMP_RAW',13:'TEMP_BUF',14:'TEMP_BUF'},'07_sensing')
    c.cap('100n/50V','3V3','GND','07_sensing')
    for signal in ('VIN','VOUT','CURRENT','TEMP'):
        c.resistor('100',signal+'_BUF','ADC_'+signal,'07_sensing')
        c.cap('1n/50V','ADC_'+signal,'GND','07_sensing')
        c.diode('3V3','ADC_'+signal,'07_sensing','ADC positive clamp; 3 V full-scale, rail clamp is not a precision limiter')
        c.diode('ADC_'+signal,'GND','07_sensing','ADC negative clamp')
    c.ic('REF3125AIDBZR',{1:'3V3',2:'REF2V5',3:'GND'},'08_protection')
    c.cap('100n/50V','3V3','GND','08_protection'); c.cap('2.2u/25V','REF2V5','GND','08_protection')
    for top,bot,net in [('1k','24k','OCP_REF'),('10k','15k','OTP_REF'),('51k','62k','UVLO_REF')]:
        c.resistor(top,'REF2V5',net,'08_protection'); c.resistor(bot,net,'GND','08_protection'); c.cap('100n/50V',net,'GND','08_protection')
    c.ic('LM2903BDR',{1:'FAULT_N',2:'CURRENT_RAW',3:'OCP_REF',4:'GND',5:'REF2V5',6:'VOUT_DIV',7:'FAULT_N',8:'5V'},'08_protection')
    c.ic('LM2903BDR',{1:'FAULT_N',2:'TEMP_RAW',3:'OTP_REF',4:'GND',5:'VIN_DIV',6:'UVLO_REF',7:'FAULT_N',8:'5V'},'08_protection')
    for _ in range(2): c.cap('100n/50V','5V','GND','08_protection')
    c.resistor('4.7k','3V3','FAULT_N','08_protection')
    c.diode('XRS_N','FAULT_N','08_protection','Reset also clears gate-enable latch')
    c.diode('PG12_N','FAULT_N','08_protection','12 V power-good failure also clears gate-enable latch')
    c.header(2,{1:'FAULT_N',2:'GND'},'08_protection','STOP / external open-drain fault')
    c.ic('SN74LVC1G74DCTR',{1:'ARM',2:'3V3',3:None,4:'GND',5:'ARMED',6:'FAULT_N',7:'3V3',8:'3V3'},'09_pwm_logic')
    c.ic('SN74LVC1G86DBVR',{1:'PWM_H',2:'PWM_L',3:'GND',4:'PWM_EXCLUSIVE',5:'3V3'},'09_pwm_logic')
    c.ic('SN74LVC1G08DBVR',{1:'ARMED',2:'PWM_EXCLUSIVE',3:'GND',4:'GATE_OK',5:'3V3'},'09_pwm_logic')
    c.ic('SN74LVC2G08DCTR',{1:'PWM_H',2:'GATE_OK',3:'LI_LOGIC',4:'GND',5:'PWM_L',6:'GATE_OK',7:'HI_LOGIC',8:'3V3'},'09_pwm_logic')
    for a,b in [('HI_LOGIC','HI'),('LI_LOGIC','LI')]: c.resistor('33',a,b,'09_pwm_logic')
    for net in ('PWM_H','PWM_L','ARM'): c.resistor('10k',net,'GND','09_pwm_logic')
    for _ in range(4): c.cap('100n/50V','3V3','GND','09_pwm_logic')

    dsp_defs={}; dsp_nets={}
    with (EXAMPLE/'components/tms320f28335_pgf_pins.csv').open() as stream:
        for pin in csv.DictReader(stream):
            n,name=pin['pin'],pin['name']
            kind='bidirectional' if name.startswith('GPIO') or name in ('EMU0','EMU1') else 'input'
            if name.startswith('VDD'): kind='power_in'
            if name.startswith('VSS'): kind='power_in'
            if name in ('TEST1','TEST2'): kind='no_connect'
            if name in ('X2','XRD','XCLKOUT','ADCREFP','ADCREFM','TDO'): kind='output'
            if name=='XRS': kind='open_collector'
            dsp_defs[n]=dict(name=name,type=kind)
            net=None
            if name=='VDD' or name in ('VDD1A18','VDD2A18'): net='1V9'
            elif name.startswith('VDD'): net='3V3'
            elif name.startswith('VSS') or name in ('ADCLO','ADCREFIN','X1'): net='GND'
            elif name.startswith('ADCIN'): net='GND'
            dsp_nets[n]=net
    dsp_nets.update({'5':'PWM_H','6':'PWM_L','7':'ARM','21':'FAULT_N','2':'UART_TX','141':'UART_RX',
                     '42':'ADC_VIN','41':'ADC_VOUT','40':'ADC_CURRENT','39':'ADC_TEMP','55':'ADCREFM','56':'ADCREFP','57':'ADCBIAS',
                     '76':'TDI','77':'TDO','78':'TRST','79':'TMS','80':'XRS_N','85':'EMU0','86':'EMU1','87':'TCK','105':'CLK30',
                     '169':'BOOT84','172':'BOOT85','173':'BOOT86','174':'BOOT87'})
    c.add('U','TMS320F28335PGFA','Package_QFP:LQFP-176_24x24mm_P0.5mm',dsp_nets,page='10_dsp',kind='DSP',mpn='TMS320F28335PGFA',maker='Texas Instruments',source='tms320f28335',definitions=dsp_defs)
    for n,net in dsp_nets.items():
        if dsp_defs[n]['name'].startswith('VDD'):
            p=c.cap('100n/50V',net,'GND','11_dsp_decoupling',f'DSP pin {n} {dsp_defs[n]["name"]}; place at pin')
            p['near_dsp_pin']=n
    for net in ('1V9','1V9','3V3','3V3'): c.cap('2.2u/25V',net,'GND','11_dsp_decoupling')
    for net in ('ADCREFM','ADCREFP'): c.cap('2.2u/25V',net,'GND','12_clock_debug','ADC reference low-ESR bypass')
    c.resistor('22k','ADCBIAS','GND','12_clock_debug')
    c.add('Y','30MHz/3V3','Oscillator:Oscillator_SMD_SeikoEpson_SG8002CA-4Pin_7.0x5.0mm',{1:'3V3',2:'GND',3:'CLK30_SOURCE',4:'3V3'},page='12_clock_debug',kind='IC',mpn='ASV-30.000MHZ-EJ-T',maker='Abracon',source='asv',definitions=pin_defs('1:OE:input 2:GND:power_in 3:OUT:output 4:VDD:power_in'))
    c.cap('100n/50V','3V3','GND','12_clock_debug'); c.resistor('33','CLK30_SOURCE','CLK30','12_clock_debug')
    for net in ('BOOT84','BOOT85','BOOT86','BOOT87','EMU0','EMU1','TMS','TDI'): c.resistor('4.7k','3V3',net,'12_clock_debug')
    c.resistor('2.2k','TRST','GND','12_clock_debug'); c.resistor('10k','TCK','GND','12_clock_debug')
    c.header(14,{1:'TMS',2:'TRST',3:'TDI',4:'GND',5:'3V3',6:None,7:'TDO',8:'GND',9:'TCK',10:'GND',11:'TCK',12:'GND',13:'EMU0',14:'EMU1'},'12_clock_debug','TI 14-pin JTAG; key pin 6 absent',rows=2)
    c.header(3,{1:'GND',2:'BOOT84',3:'3V3'},'12_clock_debug','BOOT: 1-2 SCI / 2-3 or open Flash')
    c.header(3,{1:'UART_TX',2:'UART_RX',3:'GND'},'12_clock_debug','UART 3.3 V only')
    c.resistor('10k','3V3','UART_RX','12_clock_debug')
    for net in ('VIN','VOUT','GND','AUX12','5V','3V3','1V9','FAULT_N','ARMED','ADC_CURRENT','ADC_VOUT','ADC_VIN'):
        c.add('TP',net,'TestPoint:TestPoint_Pad_D2.0mm',{1:net},page='13_testpoints',kind='TP',note='Bare PCB test point; no purchased component')
    for _ in range(8): c.add('H','M3 support','MountingHole:MountingHole_3.2mm_M3',{},page='13_testpoints',kind='H',note='Mechanical NPTH; standoff hardware specified in assembly notes')
    return c


def write_model():
    circuit=build()
    (EXAMPLE/'design/circuit.json').write_text(json.dumps(circuit.parts,indent=2)+'\n')
    fields=['reference','value','manufacturer','part_number','footprint','datasheet','note']
    for name in ('bom.csv','component_selection.csv'):
        with (EXAMPLE/'components'/name).open('w',newline='',encoding='utf8') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            for p in circuit.parts:
                writer.writerow(dict(reference=p['ref'],value=p['value'],manufacturer=p['maker'],part_number=p['mpn'],footprint=p['footprint'],datasheet=p['source'],note=p['note']))
    print(f"Electrical model: {len(circuit.parts)} parts, {len({n for p in circuit.parts for n in p['nets'].values() if n})} nets")


if __name__=='__main__': write_model()
