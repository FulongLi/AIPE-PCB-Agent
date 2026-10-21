"""Component tables and part helpers of the DAB-V1 models.

Pin tables already verified in this repository (the SiC buck models read the manufacturer datasheets and recorded
the verification level) are imported read-only; tables that are new to the DAB are written here with their own
verification level and are repeated in requirements/components.yaml.  ``PINOUT_SOURCES`` is the single place that
says how far each pin table has been checked; the review report quotes it.  The helpers build parts in the shared
AIPE model format on a ``sic_buck_common.Circuit`` (ref, value, footprint, nets pad -> net, pins, page, kind ...).
"""
from __future__ import annotations

from decimal import Decimal

from automation.kicad_tools.sic_buck_common import Circuit, PASSIVE_CAPS, pin_defs, resistor_code
from automation.kicad_tools.sic_buck_control_model import CONTROL_CAPS, IC as VERIFIED_IC
from automation.kicad_tools.sic_buck_power_model import (AMC1311_PINS, OPA2320_PINS, TMCS1133_PINS, UCC21710_PINS,
                                                          ucc14141_pins)

TI = 'Texas Instruments'
DS = 'https://www.ti.com/lit/ds/symlink/{}.pdf'
GND = 'GND_CTRL'

# Pin tables new to the DAB (transcribed; see PINOUT_SOURCES) and repository tables re-exported for the model.
EXTRA_IC = {
    'OPA4192IPWR': ('Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
                    pin_defs('1:OUTA:output 2:INA-:input 3:INA+:input 4:V+:power_in 5:INB+:input 6:INB-:input 7:OUTB:output '
                             '8:OUTC:output 9:INC-:input 10:INC+:input 11:V-:power_in 12:IND+:input 13:IND-:input 14:OUTD:output'),
                    DS.format('opa4192'), TI),
    'OPA2320AIDGKR': ('Package_SO:VSSOP-8_3x3mm_P0.65mm', OPA2320_PINS, DS.format('opa2320'), TI),
    'AMC1336DWVR': ('AIPE:DAB_AMC1336_DWV',
                    pin_defs('1:AVDD:power_in 2:AINP:input 3:AINN:input 4:AGND:power_in 5:DGND:power_in 6:DOUT:output 7:CLKIN:input 8:DVDD:power_in'),
                    DS.format('amc1336'), TI),
    'TPS7A2033PDBVR': ('Package_TO_SOT_SMD:SOT-23-5', pin_defs('1:IN:power_in 2:GND:power_in 3:EN:input 4:NC:no_connect 5:OUT:power_out'),
                       DS.format('tps7a20'), TI),
    'TCAN1042HGVDRQ1': ('Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
                        pin_defs('1:TXD:input 2:GND:power_in 3:VCC:power_in 4:RXD:output 5:VIO:power_in 6:CANL:bidirectional 7:CANH:bidirectional 8:STB:input'),
                        DS.format('tcan1042-q1'), TI),
    'THVD1450DR': ('Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
                   pin_defs('1:R:output 2:RE_N:input 3:DE:input 4:D:input 5:GND:power_in 6:A:bidirectional 7:B:bidirectional 8:VCC:power_in'),
                   DS.format('thvd1450'), TI),
    'TLV76050DBZR': ('Package_TO_SOT_SMD:SOT-23', pin_defs('1:IN:power_in 2:GND:power_in 3:OUT:power_out'), DS.format('tlv760'), TI),
    'UCC21710QDWRQ1': ('AIPE:DAB_UCC21710_DW_HV', UCC21710_PINS, DS.format('ucc21710-q1'), TI),
    'AMC1311BDWVR': ('AIPE:DAB_AMC1311_DWV', AMC1311_PINS, DS.format('amc1311'), TI),
    'TMCS1133B1QDVGR': ('AIPE:DAB_TMCS1133_DVG', TMCS1133_PINS, DS.format('tmcs1133'), TI),
}

PINOUT_SOURCES = {
    'UCC21710QDWRQ1': 'repository-record: SLUSDH8D pin table verified by the V2 power model (fetched-datasheet)',
    'UCC14141QDWNRQ1': 'repository-record: SLUSF10B Table 6-1 verified by the V2 power model (fetched-datasheet)',
    'AMC1311BDWVR': 'repository-record: SBAS786C verified by the V2 power model (fetched-datasheet)',
    'TMCS1133B1QDVGR': 'repository-record: SBOSAG0E Table 5-1 verified by the V2 power model for the C2A variant; B1 variant pin-compatible per the family table - confirm orderable status',
    'OPA4192IPWR': 'repository-record: V3 control model, fetched-datasheet (source_manifest opa4192)',
    'OPA2320AIDGKR': 'repository-record: V2 power model, fetched-datasheet',
    'TLV1702AIDGKR': 'repository-record: SBOS589D verified by the V2 control model',
    'REF3130AIDBZR': 'repository-record: SBVS046E verified by the V2 control model',
    'TPS26400PWPR': 'repository-record: SLVSFQ6A verified by the V2 control model',
    'TPS54302DDCR': 'repository-record: SLVSDG6C verified by the V2 control model',
    'TPS3808G01DBVR': 'repository-record: SBVS050N verified by the V2 control model',
    'SN74LVC1G74DCTR': 'repository-record: SCES794G verified by the V2 control model',
    'SN74LVC2G08DCTR': 'repository-record: SCES198N verified by the V2 control model',
    'SN74LV21APWR': 'repository-record: SCES340F verified by the V2 control model',
    'SN74LV04APWR': 'repository-record: SCLS388K verified by the V2 control model',
    'MMBT3904,215': 'repository-record: Nexperia data sheet verified by the V2 control model',
    'BAT54,215': 'repository-record: V1 declaration carried over (unverified in the V2 record)',
    'AMC1336DWVR': 'transcribed: SBAS951 DWV pinout written from memory - verify before layout release',
    'TPS7A2033PDBVR': 'transcribed: TPS7A20 DBV pinout written from memory - verify',
    'TCAN1042HGVDRQ1': 'transcribed: TCAN1042 D pinout written from memory - verify',
    'THVD1450DR': 'transcribed: industry-standard RS-485 SOIC-8 pinout - verify',
    'TLV76050DBZR': 'transcribed: TLV760 SOT-23 pinout (IN, GND, OUT) written from memory - verify',
    'C3M0075120K / C3M0030090K': 'repository-record: Wolfspeed TO-247-4 outline PRD 05966 lead order (D, S, driver S, G) as verified for C4MS025120K; same package family - confirm per device',
    'STTH112A': 'library-convention: KiCad DO-41 pad 1 = cathode',
    'BAT46W-E3-08': 'library-convention: KiCad SOD-123 pad 1 = cathode (Vishay 86406 not re-read)',
    'SMBJ15A': 'library-convention: KiCad SMB pad 1 = cathode (unidirectional TVS, cathode to +12 V)',
    'HSEC8-190 socket': 'library-convention: KiCad Connector_Samtec_HSEC8 numbering (odd/even rows); controlCARD signal map ASSUMED (interfaces.yaml)',
    'connectors and passives': 'library-convention: KiCad footprint pad numbering',
}

EXTRA_CAPS = {
    '10u/50V/1210': dict(footprint='Capacitor_SMD:C_1210_3225Metric', mpn='GRM32ER71H106KA12L', maker='Murata',
                         source='https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM32ER71H106KA12-04A.pdf'),
    '0.47u/1kV/2220': dict(footprint='Capacitor_SMD:C_2220_5750Metric', mpn='2220Y1K00474KETWS2', maker='Knowles Syfer',
                           source='https://www.knowlescapacitors.com/syfer'),
    '4.7n/50V/0603': dict(footprint='Capacitor_SMD:C_0603_1608Metric', mpn='GRM188R71H472KA01D', maker='Murata',
                          source='https://www.murata.com/en-us/products/productdetail?partno=GRM188R71H472KA01%23'),
    '2.2n/50V/0603': dict(footprint='Capacitor_SMD:C_0603_1608Metric', mpn='GRM188R71H222KA01D', maker='Murata',
                          source='https://www.murata.com/en-us/products/productdetail?partno=GRM188R71H222KA01%23'),
}


def tnpw_code(value: str, package: str) -> str:
    """Vishay TNPW ordering code for a 0.1 % thin-film resistor (format of the TNPW datasheet; suffix availability unverified)."""
    val = Decimal(value.rstrip('kM')) * (1000 if value.endswith('k') else 1000000 if value.endswith('M') else 1)
    exp = 0
    while val >= 1000:
        val /= 1000
        exp += 3
    token = f'{val:g}'.replace('.', 'K' if exp == 3 else 'M' if exp == 6 else 'R')
    if not any(x in token for x in 'KMR'):
        token += 'K' if exp == 3 else 'M' if exp == 6 else 'R'
    return f'TNPW{package}{token.ljust(4, "0")}BEEA'


def ic(c: Circuit, mpn: str, nets: dict, page: str, *, ref=None, note='', prefix='U', symbol=None, dnp=False):
    """IC from the verified repository table or the DAB table; unlisted no-connect pins default to None."""
    if mpn in EXTRA_IC:
        fp, defs, source, maker = EXTRA_IC[mpn]
    else:
        fp, pins, source, maker = VERIFIED_IC[mpn]
        defs = pin_defs(pins)
        if mpn == 'TLV1702AIDGKR':
            fp = 'AIPE:DAB_DGK8'  # 0.45 mm lands keep the 0.2 mm board clearance at 0.65 mm pitch (library VSSOP-8 leaves 0.15 mm)
    nets = {str(k): v for k, v in nets.items()}
    for n, p in defs.items():
        if p['type'] == 'no_connect':
            nets.setdefault(n, None)
    if mpn == 'BAT54,215':  # two-terminal use of the SOT-23 Schottky: draw the conventional diode glyph instead
        return diode(c, 'BAT46W-E3-08', 'Diode_SMD:D_SOD-123', nets['3'], nets['1'], page,
                     source='https://www.vishay.com/docs/86406/bat46w.pdf', ref=ref, note=note)
    part = c.add(prefix, mpn, fp, nets, page=page, kind='Q' if prefix == 'Q' else 'IC', mpn=mpn, maker=maker, source=source,
                 definitions=defs, ref=ref, note=note, dnp=dnp)
    if symbol:
        part['symbol'] = symbol
    if mpn == 'MMBT3904,215':
        part['symbol'] = 'Transistor_BJT:Q_NPN_BEC'
    if mpn in ('OPA2320AIDGKR', 'OPA4192IPWR', 'TLV1702AIDGKR'):
        channels = [(3, 2, 1), (5, 6, 7)]
        if mpn == 'OPA4192IPWR':
            channels += [(10, 9, 8), (12, 13, 14)]
        part['amplifier_channels'] = [dict(zip(('positive', 'negative', 'output'), map(str, ch))) for ch in channels]
    return part


def bias_module(c: Circuit, nets: dict, page: str, *, vee_type='power_out', ref=None, note=''):
    """UCC14141-Q1 isolated DC/DC module with the verified DWN pin table."""
    defs = ucc14141_pins(vee_type)
    return c.add('U', 'UCC14141QDWNRQ1', 'AIPE:DAB_UCC14141_DWN', {str(k): v for k, v in nets.items()}, page=page, kind='IC',
                 mpn='UCC14141QDWNRQ1', maker=TI, source=DS.format('ucc14141-q1'), definitions=defs, ref=ref, note=note)


def cap(c: Circuit, key: str, a, b, page: str, **kw):
    if key in PASSIVE_CAPS:
        return c.cap(key, a, b, page, **kw)
    spec = EXTRA_CAPS.get(key) or CONTROL_CAPS.get(key)
    if spec is None:
        raise KeyError(f'unknown capacitor key {key!r}')
    value = key.rsplit('/', 1)[0] if key in EXTRA_CAPS else key.split('/')[0]
    return c.add('C', value, spec['footprint'], {1: a, 2: b}, page=page, kind='C', mpn=spec['mpn'], maker=spec['maker'],
                 source=spec['source'], **kw)


def resistor(c: Circuit, value: str, a, b, page: str, *, precision=False, package='0603', **kw):
    """Thick-film (Yageo RC) or, with precision=True, Vishay TNPW 0.1 % thin-film resistor."""
    if kw.get('maker') == 'Panasonic' and 'source' not in kw:
        kw['source'] = 'https://industrial.panasonic.com/ww/products/pt/small-and-high-power-chip-resistors'
    if precision:
        kw.update(mpn=tnpw_code(value, package), maker='Vishay', source='https://www.vishay.com/docs/28773/tnpwe3.pdf')
    return c.resistor(value, a, b, page, package=package, **kw)


def pulse_resistor(c: Circuit, value: str, a, b, page: str, **kw):
    """Panasonic ERJ-P08 1206 pulse-withstanding resistor (gate and bias-module branches)."""
    # ERJ-P08 codes: 2R00 (2 ohm), 10R0, 1001 (1 k), 1800 (180 ohm), 2201 (2.2 k), 82R0
    mpn = 'ERJP08F' + erjp_code(value) + 'V'
    return c.resistor(value, a, b, page, package='1206', mpn=mpn, maker='Panasonic',
                      source='https://industrial.panasonic.com/ww/products/pt/small-and-high-power-chip-resistors', **kw)


def erjp_code(value: str) -> str:
    """Panasonic 4-character 1 % value code (R = decimal point below 100 ohm, else 3 digits + multiplier)."""
    val = Decimal(value.rstrip('kM')) * (1000 if value.endswith('k') else 1000000 if value.endswith('M') else 1)
    if val < 100:
        text = f'{val:.2f}'.rstrip('0').rstrip('.')
        whole, _, frac = text.partition('.')
        return (whole + 'R' + frac).ljust(4, '0')[:4]
    exp = 0
    while val >= 1000:
        val /= 10
        exp += 1
    return f'{int(val):03d}{exp}'


def diode(c: Circuit, mpn: str, fp: str, k, a, page: str, *, source: str, maker='Vishay', note='', ref=None):
    return c.add('D', mpn, fp, {1: k, 2: a}, page=page, kind='D', mpn=mpn, maker=maker, source=source,
                 definitions=pin_defs('1:K:passive 2:A:passive'), note=note, ref=ref)


def tp(c: Circuit, net: str, page: str, *, ref=None):
    return c.add('TP', net, 'TestPoint:TestPoint_Pad_D1.0mm', {1: net}, page=page, kind='TP', ref=ref)


def mounts(c: Circuit, page: str, count: int, note='Insulated M3 standoff; no PCB copper used as a protective conductor'):
    for _ in range(count):
        c.add('H', 'M3 insulated standoff', 'MountingHole:MountingHole_3.2mm_M3', {}, page=page, kind='H', note=note)
