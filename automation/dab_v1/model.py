"""Circuit models of the DAB-V1 boards, built from the requirement files.

``power(req, board)`` returns the primary or secondary power board (``side`` from design_constraints.yaml),
``control(req)`` the control board.  The topology is engineering judgement written as code; every device, value
bank, pin map and option it uses comes from requirements/components.yaml and requirements/interfaces.yaml.  Functional
blocks are annotated with ``Circuit.block`` for the wired schematic presentation and for the placement regions.
Electrical correctness is established by KiCad ERC/DRC and human review, not by this file.
"""
from __future__ import annotations

from automation.dab_v1 import parts as pp
from automation.dab_v1.parts import GND, TI, cap, diode, ic, mounts, pulse_resistor, resistor, tp
from automation.kicad_tools.sic_buck_common import Circuit, pin_defs

POWER_PAGES = {
    '01_bridge': 'Full bridge, DC link, switch-node terminals, DC-blocking capacitors and transformer current sensor',
    '02_drive_ah': 'Leg A high side: isolated gate driver, DESAT, gate loop and isolated bias',
    '03_drive_al': 'Leg A low side: isolated gate driver, DESAT, gate loop and isolated bias',
    '04_drive_bl': 'Leg B low side: isolated gate driver, DESAT, gate loop and isolated bias',
    '05_drive_bh': 'Leg B high side: isolated gate driver, DESAT, gate loop and isolated bias',
    '06_sense': 'Isolated bus-voltage sensing, isolated sensing supply, Hall-sensor conditioning and temperature',
    '07_interface': 'Keyed control harness, filtered inputs, auxiliary rails and mounting',
}
CONTROL_PAGES = {
    '01_supply': '12 V auxiliary input protection, 5 V buck, 3.3 V LDO and supervisor',
    '02_card': 'TMS320F280039C controlCARD socket and signal assignment',
    '03_pwm_gating': 'Hardware PWM gating by the armed latch',
    '04_fault_logic': 'Hardware fault tree, over-voltage comparators and fault latch',
    '05_analog': 'Isolated-voltage receivers, current buffers and ADC conditioning',
    '06_comms': 'CAN, optional RS-485 and JTAG',
    '07_interface': 'Power-board harnesses, indicators, test points and mounting',
}
TAGS = ('AH', 'AL', 'BL', 'BH')
COMPLEMENT = {'AH': 'AL', 'AL': 'AH', 'BL': 'BH', 'BH': 'BL'}
# device terminals per role: (drain net, source net)
ROLE_NETS = {'AH': ('BUS_P', 'SW_A'), 'AL': ('SW_A', 'PGND'), 'BL': ('SW_B', 'PGND'), 'BH': ('BUS_P', 'SW_B')}
DRIVE_PAGE = {'AH': '02_drive_ah', 'AL': '03_drive_al', 'BL': '04_drive_bl', 'BH': '05_drive_bh'}
FET_PINS = pin_defs('1:D:passive 2:S:passive 3:KS:passive 4:G:input')


def _bias_module(c: Circuit, comp: dict, tag: str, page: str, *, sense: bool = False):
    """UCC14141-Q1 isolated bias with its input filter, feedback dividers, RLIM/RDR branch and output reservoir.

    Gate modules: VDD_x = +15 V, VEE_x = -4 V around the Kelvin source COM (FBVDD 107k/16.2k, FBVEE 9.76k/16.2k).
    Sense module: 16 V total with a 5 V COM above the HV negative rail (S_16V / S_5V / PGND) for the isolated
    sensing ICs (FBVDD 87.6k/16.2k, FBVEE 16.2k/16.2k, RLIM 82 ohm).  Quiet VEEA star through a net tie at VEE.
    """
    bias = comp['isolated_bias']
    if sense:
        vdd, vee, com, quiet = 'S_16V', 'PGND', 'S_5V', 'S_VEEA'
        vin, gnd, rlim, fbvdd, fbvee = '12V_BIAS_S', 'GNDP_S', 'S_RLIM', 'S_FBVDD', 'S_FBVEE'
        fb_top_vdd, fb_top_vee, r_lim = bias['sense_supply']['fb_vdd_top_ohm'], bias['sense_supply']['fb_vee_top_ohm'], bias['sense_supply']['rlim_ohm']
    else:
        vdd, vee, com, quiet = f'VDD_{tag}', f'VEE_{tag}', f'KS_{tag}', f'VEEA_{tag}'
        vin, gnd, rlim, fbvdd, fbvee = f'12V_BIAS_{tag}', f'GNDP_{tag}', f'RLIM_{tag}', f'FBVDD_{tag}', f'FBVEE_{tag}'
        fb_top_vdd, fb_top_vee, r_lim = bias['fb_vdd_top_ohm'], bias['fb_vee_top_ohm'], bias['rlim_ohm']
    label = 'S' if sense else tag
    with c.block(f'bias_{label}', f'{label}: isolated DC/DC bias module, input filter and quiet feedback star'):
        choke = bias['cm_choke']
        c.add('L', choke['mpn'], choke['footprint'], {1: '12V_E', 2: GND, 3: gnd, 4: vin}, page=page, kind='L', mpn=choke['mpn'],
              maker=choke['maker'], source=choke['source'], definitions=pin_defs('1:W1A:passive 2:W2A:passive 3:W2B:passive 4:W1B:passive'),
              note='Common-mode choke at the module input (KR-IS-002)')
        for _ in range(3):
            cap(c, '10u/25V/1210', vin, gnd, page)
        cap(c, '100n/50V/0603', vin, gnd, page, note='Local VIN/GNDP bypass at pins 6-8')
        nets = {n: gnd for n in (1, 2, 5, *range(8, 19))}
        nets.update({n: vee for n in (*range(19, 28), 30, 31, 36)})
        nets.update({3: 'PG_BIAS_N', 4: 'BIAS_ENF', 6: vin, 7: vin, 28: vdd, 29: vdd, 32: rlim, 33: fbvee, 34: fbvdd, 35: quiet})
        u = pp.bias_module(c, nets, page, vee_type='passive' if sense else 'power_out',
                           note=f'{bias["mpn"]}: VDD-VEE {"16 V, COM 5 V above VEE" if sense else "19 V, COM 4 V above VEE (+15 / -4 V gate rails)"}; '
                                'VEEA quiet star at pin 36 through the net tie; PG open-drain wired-AND on PG_BIAS_N')
        u['island'] = label
        tie = c.add('NT', 'VEEA STAR', 'NetTie:NetTie-2_SMD_Pad0.5mm', {1: quiet, 2: vee}, page=page, kind='passive',
                    note=f'Physical star point at {u["ref"]} pin 36; no load current through the quiet branch')
        tie['in_bom'] = False
        tie['star_of'] = u['ref']
        for name, upper, top in ((fbvdd, vdd, fb_top_vdd), (fbvee, com, fb_top_vee)):
            resistor(c, top, upper, name, page, precision=True)
            resistor(c, bias['fb_bottom_ohm'], name, quiet, page, precision=True)
            cap(c, '330p/50V/0603', name, quiet, page, note='Quiet feedback branch only')
        if sense:
            pulse_resistor(c, r_lim, rlim, com, page, note='Sensing ICs about 20 mA on the 5 V COM; RLIM per SLUSF10B Eq. 9')
        else:
            pulse_resistor(c, r_lim, rlim, com, page, note='RDR source branch (SLUSF10B Eq. 10)')
            pulse_resistor(c, bias['rdr_ohm'], rlim, f'RDR_{tag}', page, note='RDR sink branch, 180 ohm + diode in parallel with the 1 k')
            diode(c, 'BAT46W-E3-08', 'Diode_SMD:D_SOD-123', f'RDR_{tag}', com, page, source='https://www.vishay.com/docs/86406/bat46w.pdf',
                  note='Anode COM, cathode RDR resistor: sinks COM charge into RLIM')
        for _ in range(3):
            cap(c, '1u/50V/0805', vdd, vee, page, note='Output reservoir; effective capacitance at bias to be characterised')
        for _ in range(2):
            cap(c, '10u/50V/1210', vdd, vee, page, note='>= 10 uF effective output capacitance required (SLUSF10B)')
        cap(c, '100n/50V/0603', vdd, vee, page, note='Output bypass at pins 28/30')
        if sense:
            cap(c, '10u/25V/1210', com, vee, page, note='5 V COM reservoir for the sensing ICs')
    return u


def _gate_drive(c: Circuit, comp: dict, side: str, tag: str, page: str, drain: str):
    """UCC21710 isolated driver with 2 ohm split gate resistors, Kelvin return, DESAT network and APWM thermistor."""
    drv = comp['gate_driver']
    ks, g, vdd, vee = f'KS_{tag}', f'G_{tag}', f'VDD_{tag}', f'VEE_{tag}'
    with c.block(f'driver_{tag}', f'{tag}: isolated gate driver, Kelvin return, Miller clamp and gate loop'):
        nets = {1: f'NTC_{tag}', 2: f'OC_{tag}', 3: ks, 4: f'OUTH_{tag}', 5: vdd, 6: f'OUTL_{tag}', 7: g, 8: vee, 9: GND,
                10: f'PWMF_{tag}', 11: f'PWMF_{COMPLEMENT[tag]}', 12: f'RDY_{tag}', 13: f'FLT_{tag}_N', 14: 'DRV_RSTF', 15: '3V3', 16: f'TEMP_PWM_{tag}'}
        u = ic(c, drv['mpn'], nets, page, note='CLMPI straight to the device gate; COM only to the Kelvin source; IN- carries the '
                                               'complementary PWM for the hardware shoot-through interlock (KR-GD-009)')
        u['island'] = tag
        pulse_resistor(c, str(drv['r_on_ohm']).rstrip('0').rstrip('.'), f'OUTH_{tag}', g, page, note='Turn-on gate resistor 2 ohm (TIDUES0); double-pulse tuning required')
        pulse_resistor(c, str(drv['r_off_ohm']).rstrip('0').rstrip('.'), f'OUTL_{tag}', g, page, note='Turn-off gate resistor 2 ohm (TIDUES0)')
        resistor(c, '10k', g, ks, page, package='0805', note='Gate-source discharge on the device side of R_G (KR-GD-007)')
        c.add('TP', f'VGS {tag}', 'TestPoint:TestPoint_2Pads_Pitch2.54mm_Drill0.8mm', {1: g, 2: ks}, page=page, kind='TP')
        for _ in range(4):
            cap(c, '1u/50V/0805', vdd, ks, page, note='Positive gate reservoir inside the gate loop (KR-PCB-002)')
        for _ in range(2):
            cap(c, '10u/25V/1210', ks, vee, page, note='Negative gate reservoir')
        for a, b in ((vdd, ks), (ks, vee), ('3V3', GND)):
            cap(c, '100n/50V/0603', a, b, page)
        cap(c, '1u/50V/0805', '3V3', GND, page)
        resistor(c, '3.3k', f'NTC_{tag}', f'NTCR_{tag}', page)
        resistor(c, '20k', f'NTC_{tag}', ks, page, note='Bounds AIN below 4.18 V if the NTC opens')
        ntc = comp['sensing']['heatsink_ntc']
        c.add('RT', '10k NTC B3988', 'Resistor_SMD:R_0805_2012Metric', {1: f'NTCR_{tag}', 2: ks}, page=page, kind='R', mpn=ntc['mpn'],
              maker=ntc['maker'], source=ntc['source'], note='Driver-island temperature through the isolated APWM channel (CB-PR-002); not junction temperature (KR-TH-003)')
        cap(c, '1n/50V/0603', f'NTC_{tag}', ks, page)
        for sig in (f'RDY_{tag}', f'FLT_{tag}_N'):
            resistor(c, '4.7k', '3V3', sig, page)
    with c.block(f'desat_{tag}', f'{tag}: drain-voltage short-circuit detection'):
        ds = comp['desat']
        pulse_resistor(c, ds['pullup_ohm'], vdd, f'DESAT_{tag}', page)
        diode(c, ds['diode_mpn'], ds['diode_footprint'], drain, f'DESAT_{tag}', page, source=ds['diode_source'], maker=ds['diode_maker'],
              note='1200 V ultrafast DESAT diode; leaded package keeps the HV lead spacing on the board')
        resistor(c, ds['divider_top_ohm'], f'DESAT_{tag}', f'OC_{tag}', page, precision=True)
        resistor(c, ds['divider_bottom_ohm'], f'OC_{tag}', ks, page, precision=True)
        cap(c, ds['blanking_cap'], f'OC_{tag}', ks, page, note='Blanking network: re-tune to the 1 us TIDUES0 setting by double-pulse test (KR-GD-004)')
        diode(c, ds['clamp_diode_mpn'], 'Diode_SMD:D_SOD-123', f'OC_{tag}', ks, page, source=ds['clamp_diode_source'], note='OC negative transient clamp')
    return u


def power(req, board: str) -> Circuit:
    """Primary or secondary power board model."""
    cfg = req.board(board)
    side = cfg['side']
    comp = req.components
    iface = req.interfaces
    c = Circuit(board)
    c.side = side
    sw = comp['switches'][side]
    p = '01_bridge'
    with c.block('bridge', f'{side} full bridge: 4x {sw["mpn"]} with Kelvin source (TO-247-4)'):
        for n, tag in enumerate(TAGS, 1):
            drain, source = ROLE_NETS[tag]
            q = c.add('Q', sw['mpn'], sw['footprint'], {1: drain, 2: source, 3: f'KS_{tag}', 4: f'G_{tag}'}, page=p, kind='Q', mpn=sw['mpn'],
                      maker=sw['maker'], source=sw['source'], definitions=FET_PINS, ref=f'Q{n}',
                      note=f'{tag}: lead order D, S, driver S, G (Wolfspeed TO-247-4); tab = drain; insulated pad to the PE-bonded heat sink')
            q['role'] = tag
    with c.block('dc_link', f'{side} DC link: film bulk plus distributed HV ceramics at each leg (KR-CAP-003)'):
        film = comp['dc_link'][side]['film']
        for n in range(film['count']):
            c.add('C', f'{film["capacitance_uF"]}u / {film["voltage_V"]}V', f'AIPE:DAB_FILM_{side.upper()}', {1: 'BUS_P', 2: 'PGND'}, page=p, kind='C',
                  mpn=film['mpn'], maker=film['maker'], source=film['source'], ref=f'C{n + 1}',
                  note=f'TIDUES0 bulk film capacitor; envelope {film["envelope_mm"]} mm to be verified against the TDK drawing')
        ceramic = comp['dc_link'][side]['ceramic']
        for _ in range(ceramic['count']):
            cap(c, ceramic['key'], 'BUS_P', 'PGND', p, note='HF decoupling at the bridge; effective capacitance under DC bias unverified')
    with c.block('bleeder', 'Passive DC-link discharge chain (independent of auxiliary power)'):
        bl = comp['bleeder']
        count = 6 if side == 'primary' else 4
        chain = ['BUS_P'] + [f'BLD{i}' for i in range(1, count)] + ['PGND']
        for a, b in zip(chain, chain[1:]):
            c.add('R', bl['value_ohm'], bl['footprint'], {1: a, 2: b}, page=p, kind='R', mpn=bl['mpn'], maker=bl['maker'], source=bl['source'],
                  note=f'Series discharge chain, {count} elements; <60 s to 60 V (analytical); {bl["note"]}')
    with c.block('terminals', 'Press-in HV terminals: DC bus and the two AC nodes'):
        term = comp['terminals']
        names = {'J1': 'DC BUS +', 'J2': 'DC BUS -', 'J3': 'AC A (switch node A)', 'J4': 'AC B (transformer, via current sensor)'}
        for ref, net in iface['hv_terminals'][side].items():
            c.add('J', names[ref], term['hv_footprint'], {1: net}, page=p, kind='J', mpn=term['hv_mpn'], maker=term['hv_maker'], source=term['hv_source'], ref=ref)
    with c.block('ac_path', 'Leg B AC path: DC-blocking capacitors and transformer current sensor'):
        hall = comp['sensing']['current_hall']
        if side == 'primary':
            blk = comp['dc_block']
            for _ in range(blk['count']):
                c.add('C', f'{blk["capacitance_uF"]}u / {blk["voltage_V"]}V', 'AIPE:DAB_CBLK_FILM', {1: 'SW_B', 2: 'XF_B'}, page=p, kind='C', mpn=blk['mpn'],
                      maker=blk['maker'], source=blk['source'], note='DC-blocking capacitor (TIDUES0 Eq. 20 >= 7.2 uF); ripple-current rating is an open calculation')
            hall_in = 'XF_B'
        else:
            hall_in = 'SW_B'
        u = ic(c, hall['mpn'], {1: hall_in, 2: 'AC_B', 3: GND, 4: GND, 5: None, 6: 'ISNS', 7: 'OC_TRIP_N', 8: 'VOC_SET', 9: '3V3', 10: '3V3'}, p,
               note='Hall sensor in the transformer path: bidirectional 25 mV/A, 1.65 V at zero current, integrated over-current comparator (KR-SN-005); ALERT tied to ground as unused')
        u['barrier'] = 'hall'
        resistor(c, '10k', '3V3', 'OC_TRIP_N', p, note='Open-drain over-current trip to the harness (fast hardware path)')
        resistor(c, '10k', '3V3', 'VOC_SET', p, precision=True)
        resistor(c, '10k', 'VOC_SET', GND, p, precision=True, note='Over-current threshold set point (VOC); target 45 A primary / 70 A secondary per TIDUES0 - '
                                                                   'the SBOSAG0E threshold equation must be applied before release (open item)')
        cap(c, '100n/50V/0603', 'VOC_SET', GND, p)
        cap(c, '100n/50V/0603', '3V3', GND, p, note='Hall sensor VS bypass at pins 9/10')
        cap(c, '1u/50V/0805', '3V3', GND, p)
        cap(c, '1n/50V/0603', 'ISNS', GND, p, note='Output filter before the harness')
    for n, tag in enumerate(TAGS, 1):
        drain = ROLE_NETS[tag][0]
        _gate_drive(c, comp, side, tag, DRIVE_PAGE[tag], drain)
        _bias_module(c, comp, tag, DRIVE_PAGE[tag])
    p = '06_sense'
    _bias_module(c, comp, 'S', p, sense=True)
    with c.block('voltage_sense', f'{side} bus voltage: high-impedance ladder into the isolated amplifier'):
        ladder = comp['sensing']['ladder_resistor']
        steps = 8 if side == 'primary' else 4
        chain = ['BUS_P'] + [f'VDIV{i}' for i in range(1, steps)] + ['VADC_IN']
        for a, b in zip(chain, chain[1:]):
            resistor(c, ladder['value_ohm'], a, b, p, precision=True, package=ladder['package'], note=f'{steps} x 634 k ladder, about 100 V per element (KR-SN-002)')
        resistor(c, '10k', 'VADC_IN', 'PGND', p, precision=True, note='800 V -> 1.57 V (primary) / 400 V -> 1.57 V (secondary) at the 2 V input')
        cap(c, '1n/50V/0603', 'VADC_IN', 'PGND', p)
        amp = comp['sensing']['voltage_isolated_amplifier']
        u = ic(c, amp['mpn'], {1: 'S_5V', 2: 'VADC_IN', 3: 'PGND', 4: 'PGND', 5: GND, 6: 'VSNS_N', 7: 'VSNS_P', 8: '3V3'}, p,
               note='Isolated amplifier, gain 1, differential output to the control board (KR-SN-001)')
        u['barrier'] = 'vsense'
        for a, b in (('S_5V', 'PGND'), ('3V3', GND)):
            cap(c, '100n/50V/0603', a, b, p)
            cap(c, '1u/50V/0805', a, b, p)
        if side == 'secondary':
            chain = ['BUS_P'] + [f'MDIV{i}' for i in range(1, 4)] + ['VMOD_IN']
            for a, b in zip(chain, chain[1:]):
                resistor(c, ladder['value_ohm'], a, b, p, precision=True, package=ladder['package'], note='4 x 634 k ladder for the delta-sigma modulator')
            resistor(c, '3.92k', 'VMOD_IN', 'PGND', p, precision=True, note='400 V -> 0.62 V, 500 V -> 0.77 V at the +/-1 V modulator input')
            cap(c, '1n/50V/0603', 'VMOD_IN', 'PGND', p)
            mod = comp['sensing']['voltage_modulator']
            u = ic(c, mod['mpn'], {1: 'S_5V', 2: 'VMOD_IN', 3: 'PGND', 4: 'PGND', 5: GND, 6: 'SDFM_DOUT', 7: 'SDFM_CLKIN', 8: '3V3'}, p,
                   note='Delta-sigma modulator; bitstream to the C2000 SDFM over the harness (KR-SN-003)')
            u['barrier'] = 'vmod'
            resistor(c, '33', 'SDFM_DOUT', 'SDFM_D', p)
            resistor(c, '33', 'SDFM_CLK', 'SDFM_CLKIN', p)
            for a, b in (('S_5V', 'PGND'), ('3V3', GND)):
                cap(c, '100n/50V/0603', a, b, p)
                cap(c, '1u/50V/0805', a, b, p)
    with c.block('temperature', 'Heat-sink NTC (cabled, SELV) and harness filter'):
        ntc = iface['heatsink_ntc']
        c.add('J', 'HEATSINK NTC', ntc['footprint'], {1: 'NTC_HS', 2: GND}, page=p, kind='J', mpn=ntc['mpn'], maker='JST', source='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',
              ref='J6', note='Cabled 10 k NTC on the PE-bonded heat sink; the sensor must be insulated from the device tabs')
        resistor(c, '10k', '3V3', 'NTC_HS', p, precision=True)
        cap(c, '100n/50V/0603', 'NTC_HS', GND, p)
        resistor(c, '1k', 'NTC_HS', 'TEMP_HS', p)
        cap(c, '10n/50V/0603', 'TEMP_HS', GND, p, note='RC before the harness')
    p = '07_interface'
    with c.block('harness', 'Keyed SELV control harness (40-way) and filtered logic inputs'):
        harness = iface['control_harness']
        nets = {str(k): v for k, v in harness['pins'].items()}
        if side == 'primary':
            for pin, net in list(nets.items()):
                if net in ('SDFM_CLK', 'SDFM_D'):
                    nets[pin] = net  # reserved on the primary: terminated on test points
        term = comp['terminals']
        c.add('J', 'CONTROL HARNESS 40-way', term['harness_footprint'], nets, page=p, kind='J', mpn=term['harness_mpn'], maker=term['harness_maker'],
              source=term['harness_source'], ref='J5', note=harness['keying'])
        for sig in ('PWM_AH', 'PWM_AL', 'PWM_BL', 'PWM_BH'):
            resistor(c, '33', sig, sig.replace('PWM_', 'PWMF_'), p)
            resistor(c, '10k', sig.replace('PWM_', 'PWMF_'), GND, p, note='Fail-safe low when the harness is unplugged')
            cap(c, '100p/50V/0603', sig.replace('PWM_', 'PWMF_'), GND, p)
        for sig in ('DRV_RST', 'BIAS_EN'):
            resistor(c, '33', sig, sig + 'F', p)
            resistor(c, '10k', sig + 'F', GND, p, note='Fail-safe: drivers held in reset / bias disabled with the harness unplugged')
            cap(c, '100p/50V/0603', sig + 'F', GND, p)
        resistor(c, '4.7k', '3V3', 'PG_BIAS_N', p, note='Pull-up of the wired-AND power-good line of the five bias modules')
        if side == 'primary':
            tp(c, 'SDFM_CLK', p)
            tp(c, 'SDFM_D', p)
    with c.block('aux_rails', 'Auxiliary rails from the harness'):
        for _ in range(2):
            cap(c, '10u/25V/1210', '12V_E', GND, p)
        cap(c, '100n/50V/0603', '12V_E', GND, p)
        cap(c, '10u/25V/1210', '3V3', GND, p)
        cap(c, '1u/50V/0805', '3V3', GND, p)
    with c.block('mechanical', 'Heat-sink envelopes and insulated mounting'):
        hs = comp['heatsink']
        for n in (1, 2):
            h = c.add('HS', f'{hs["mpn"]} envelope', 'AIPE:DAB_HEATSINK_ENVELOPE', {}, page=p, kind='H', mpn=hs['mpn'], maker=hs['maker'], source=hs['source'],
                      ref=f'HS{n}', note='Two TO-247-4 per sink on insulating pads; PE-bonded through the chassis; rule area forbids tracks, vias, pours and parts under the base on F.Cu')
            h['in_bom'] = True
        mounts(c, p, len(req.floorplans[board]['mounting_holes']))
    return c


def _harness_nets(req, prefix: str) -> dict:
    harness = req.interfaces['control_harness']
    shared = set(harness['shared_nets'])
    return {str(k): (v if v in shared else f'{prefix}_{v}') for k, v in harness['pins'].items()}


def control(req) -> Circuit:
    """Control board model: controlCARD socket, hardware gating and fault latch, conditioning, communications, supplies."""
    comp = req.components
    iface = req.interfaces
    c = Circuit('control')
    c.side = 'control'
    p = '01_supply'
    with c.block('aux_entry', '12 V auxiliary entry: TVS and TPS2640 eFuse (CB-PR-001)'):
        aux = iface['auxiliary_input']
        c.add('J', '12 V AUXILIARY IN', aux['connector_footprint'], {1: '12V_IN', 2: GND}, page=p, kind='J', mpn=aux['connector_mpn'], maker='Phoenix Contact',
              source='https://www.phoenixcontact.com/en-pc/products/1803578', ref='J4')
        diode(c, 'SMBJ15A', 'Diode_SMD:D_SMB', '12V_IN', GND, p, source=comp['auxiliary_supply']['tvs_source'], maker='Littelfuse', note='Unidirectional TVS, cathode to +12 V')
        ic(c, 'TPS26400PWPR', {1: '12V_IN', 2: '12V_IN', 3: 'E_UV', 5: 'E_OV', 6: None, 7: 'E_EN', 8: 'E_RTN', 9: GND, 10: 'E_IMON', 11: 'E_ILIM', 12: 'E_DVDT',
                               14: 'AUX_FLT_N', 15: '12V_E', 16: '12V_E', 17: 'E_RTN'}, p,
           note='eFuse: UVLO about 9 V, OVP about 15 V, current limit about 2.2 A (TIDUES0 settings); RTN kept separate from GND per SLVSFQ6A')
        for v, a, b in (('107k', '12V_IN', 'E_UV'), ('4.42k', 'E_UV', 'E_OV'), ('10k', 'E_OV', 'E_RTN'), ('6.04k', 'E_ILIM', 'E_RTN'), ('14.7k', 'E_IMON', 'E_RTN'),
                        ('100k', '12V_IN', 'E_EN'), ('10k', '3V3', 'AUX_FLT_N')):
            resistor(c, v, a, b, p)
        cap(c, '100n/50V/0603', 'E_DVDT', 'E_RTN', p)
        cap(c, '100n/50V/0603', '12V_IN', GND, p)
        cap(c, '100u/25V/elec', '12V_E', GND, p)
        tp(c, 'E_IMON', p)
    with c.block('buck_5v', '5 V buck for the controlCARD, logic and transceivers'):
        ic(c, 'TPS54302DDCR', {1: GND, 2: 'SW5', 3: '12V_E', 4: 'FB5', 5: 'EN5', 6: 'BST5'}, p)
        cap(c, '10u/50V/1210', '12V_E', GND, p)
        cap(c, '100n/50V/0603', '12V_E', GND, p)
        cap(c, '100n/50V/0603', 'BST5', 'SW5', p)
        resistor(c, '100k', '12V_E', 'EN5', p)
        resistor(c, '20k', 'EN5', GND, p)
        c.add('L', '10uH', 'Inductor_SMD:L_Coilcraft_MSS1048-XXX', {1: 'SW5', 2: '5V0'}, page=p, kind='L', mpn=comp['auxiliary_supply']['buck_inductor'],
              maker='Coilcraft', source=comp['auxiliary_supply']['buck_inductor_source'])
        for _ in range(2):
            cap(c, '22u/25V/1210', '5V0', GND, p)
        cap(c, '220u/16V/radial', '5V0', GND, p)
        resistor(c, '100k', '5V0', 'FB5', p)
        resistor(c, '13.3k', 'FB5', GND, p)
        cap(c, '100p/50V/0603', '5V0', 'FB5', p, note='Feed-forward; verify the loop with the actual output capacitance')
    with c.block('ldo_3v3', '3.3 V LDO for the on-board logic'):
        ic(c, 'TPS7A2033PDBVR', {1: '5V0', 2: GND, 3: '5V0', 5: '3V3'}, p)
        cap(c, '1u/50V/0805', '5V0', GND, p)
        cap(c, '1u/50V/0805', '3V3', GND, p)
        cap(c, '10u/25V/1210', '3V3', GND, p)
    with c.block('supervisor', '3.3 V supervisor: reset holds the fault latch cleared'):
        ic(c, 'TPS3808G01DBVR', {1: 'NRST', 2: GND, 3: 'MR_N', 4: 'RESET_CT', 5: 'MON3V3', 6: '3V3'}, p)
        resistor(c, '68.1k', '3V3', 'MON3V3', p, precision=True)
        resistor(c, '10k', 'MON3V3', GND, p, precision=True, note='3.16 V threshold with VIT 0.405 V')
        resistor(c, '4.7k', '3V3', 'NRST', p)
        cap(c, '10n/50V/0603', 'RESET_CT', GND, p)
        cap(c, '100n/50V/0603', '3V3', GND, p)
        c.add('J', 'MANUAL RESET', 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical', {1: 'MR_N', 2: GND}, page=p, kind='J', mpn='TSW-102-07-G-S',
              maker='Samtec', source='https://www.samtec.com/products/tsw', ref='J8')
    p = '02_card'
    card = iface['controlcard']
    with c.block('controlcard', 'TMS320F280039C controlCARD socket (signal map ASSUMED - review item R-01)'):
        nets = {str(n): None for n in range(1, 181)}
        for contact, net in card['signals'].items():
            nets[str(contact)] = net
        sock = comp['controller']['socket']
        c.add('J', 'controlCARD HSEC8 180-contact socket', sock['footprint'], nets, page=p, kind='J', mpn=sock['mpn'], maker=sock['maker'], source=sock['source'], ref='J1',
              note=card['pinout_status'])
        for _ in range(4):
            cap(c, '10u/25V/1210', '5V0', GND, p, note='Card supply reservoir at the socket')
        cap(c, '100n/50V/0603', '5V0', GND, p)
        for net in ('ARM', 'RUN_EN', 'DRV_RST_MCU', 'BIAS_EN_MCU'):
            resistor(c, '10k', net, GND, p, note='Default off / reset when the card is absent')
        for net in ('EPWM1A', 'EPWM1B', 'EPWM2A', 'EPWM2B', 'EPWM3A', 'EPWM3B', 'EPWM4A', 'EPWM4B'):
            resistor(c, '10k', net, GND, p)
    p = '03_pwm_gating'
    pwm_map = [('EPWM1A', 'P_PWM_AH'), ('EPWM1B', 'P_PWM_AL'), ('EPWM2A', 'P_PWM_BH'), ('EPWM2B', 'P_PWM_BL'),
               ('EPWM3A', 'S_PWM_AH'), ('EPWM3B', 'S_PWM_AL'), ('EPWM4A', 'S_PWM_BH'), ('EPWM4B', 'S_PWM_BL')]
    with c.block('pwm_gating', 'Every PWM is ANDed with the hardware PWM_ENABLE before it leaves the board'):
        for i in range(0, 8, 2):
            (a_in, a_out), (b_in, b_out) = pwm_map[i], pwm_map[i + 1]
            ic(c, 'SN74LVC2G08DCTR', {1: a_in, 2: 'PWM_ENABLE', 3: b_out + '_SRC', 4: GND, 5: b_in, 6: 'PWM_ENABLE', 7: a_out + '_SRC', 8: '3V3'}, p)
            cap(c, '100n/50V/0603', '3V3', GND, p)
            for src, out in ((a_out + '_SRC', a_out), (b_out + '_SRC', b_out)):
                resistor(c, '33', src, out, p)
    p = '04_fault_logic'
    with c.block('fault_tree', 'Asynchronous hardware fault tree (KR-PR-002): drivers, bias power-good, over-current, over-voltage, supplies'):
        def and4(inputs, output, note=''):
            return inputs, output
        gates = [
            (('P_FLT_AH_N', 'P_FLT_AL_N', 'P_FLT_BH_N', 'P_FLT_BL_N'), 'FLT_P_OK'),
            (('S_FLT_AH_N', 'S_FLT_AL_N', 'S_FLT_BH_N', 'S_FLT_BL_N'), 'FLT_S_OK'),
            (('P_RDY_AH', 'P_RDY_AL', 'P_RDY_BH', 'P_RDY_BL'), 'RDY_P_OK'),
            (('S_RDY_AH', 'S_RDY_AL', 'S_RDY_BH', 'S_RDY_BL'), 'RDY_S_OK'),
            (('PG_P_OK', 'PG_S_OK', 'P_OC_TRIP_N', 'S_OC_TRIP_N'), 'PROT_OK'),
            (('OV_P_OK', 'OV_S_OK', 'AUX_FLT_N', 'NRST'), 'SUPPLY_OK'),
            (('FLT_P_OK', 'FLT_S_OK', 'RDY_P_OK', 'RDY_S_OK'), 'DRIVERS_OK'),
            (('PROT_OK', 'SUPPLY_OK', 'DRIVERS_OK', '3V3'), 'ALL_GOOD'),
        ]
        for i in range(0, 8, 2):
            (ina, outa), (inb, outb) = gates[i], gates[i + 1]
            ic(c, 'SN74LV21APWR', {1: ina[0], 2: ina[1], 4: ina[2], 5: ina[3], 6: outa, 7: GND, 8: outb, 9: inb[0], 10: inb[1], 12: inb[2], 13: inb[3], 14: '3V3'}, p)
            cap(c, '100n/50V/0603', '3V3', GND, p)
        ic(c, 'SN74LV04APWR', {1: 'P_PG_BIAS_N', 2: 'PG_P_OK', 3: 'S_PG_BIAS_N', 4: 'PG_S_OK', 5: 'ALL_GOOD', 6: 'FAULT_RD', 7: GND, 8: None, 9: GND, 10: None, 11: GND, 12: None, 13: GND, 14: '3V3'}, p,
           note='UCC14141 PG is open-drain LOW = good; inverted for the AND tree; FAULT_RD = NOT ALL_GOOD to the card')
        cap(c, '100n/50V/0603', '3V3', GND, p)
        for net in ('P_PG_BIAS_N', 'S_PG_BIAS_N', 'P_OC_TRIP_N', 'S_OC_TRIP_N'):
            resistor(c, '10k', '3V3', net, p, note='Local pull-up: an unplugged harness reads as a fault')
        for net in ('P_FLT_AH_N', 'P_FLT_AL_N', 'P_FLT_BH_N', 'P_FLT_BL_N', 'S_FLT_AH_N', 'S_FLT_AL_N', 'S_FLT_BH_N', 'S_FLT_BL_N'):
            resistor(c, '100k', net, GND, p, note='Weak pull-down: unplugged harness reads as a driver fault')
        for net in ('P_RDY_AH', 'P_RDY_AL', 'P_RDY_BH', 'P_RDY_BL', 'S_RDY_AH', 'S_RDY_AL', 'S_RDY_BH', 'S_RDY_BL'):
            resistor(c, '100k', net, GND, p)
    with c.block('ov_comparators', 'Bus over-voltage comparators on the received isolated signals'):
        ic(c, 'REF3130AIDBZR', {1: '5V0', 2: 'REF3', 3: GND}, p)
        cap(c, '1u/50V/0805', '5V0', GND, p)
        cap(c, '1u/50V/0805', 'REF3', GND, p)
        for tag, top in (('P', '1.3k'), ('S', '590')):
            resistor(c, top, 'REF3', f'V_OV_{tag}', p, precision=True)
            resistor(c, '10k', f'V_OV_{tag}', GND, p, precision=True, note='Trip 900 V primary (2.66 V) / 480 V secondary (2.83 V) at the receiver scaling')
            cap(c, '100n/50V/0603', f'V_OV_{tag}', GND, p)
            resistor(c, '1k', f'{tag}_VBUS_RX', f'{tag}_VBUS_CMP', p)
        ic(c, 'TLV1702AIDGKR', {1: 'OV_P_OK', 2: 'P_VBUS_CMP', 3: 'V_OV_P', 4: GND, 5: 'V_OV_S', 6: 'S_VBUS_CMP', 7: 'OV_S_OK', 8: '3V3'}, p,
           note='Open-collector outputs high while the bus is below threshold')
        for net in ('OV_P_OK', 'OV_S_OK'):
            resistor(c, '10k', '3V3', net, p)
        cap(c, '100n/50V/0603', '3V3', GND, p)
    with c.block('latch', 'Armed latch: asynchronous clear has priority; re-arm needs an edge after every cause has cleared'):
        ic(c, 'SN74LVC1G74DCTR', {1: 'ARM', 2: '3V3', 3: 'TRIPPED', 4: GND, 5: 'ARMED', 6: 'ALL_GOOD', 7: '3V3', 8: '3V3'}, p,
           note='D = 1, CLK = ARM pulse from the card, CLR_N = ALL_GOOD; Q = ARMED feeds the PWM gate and the card TZ input; Q_N = TRIPPED')
        cap(c, '100n/50V/0603', '3V3', GND, p)
        ic(c, 'SN74LVC2G08DCTR', {1: 'ARMED', 2: 'RUN_EN', 3: None, 4: GND, 5: GND, 6: GND, 7: 'PWM_ENABLE', 8: '3V3'}, p, note='PWM_ENABLE = ARMED AND RUN_EN')
        cap(c, '100n/50V/0603', '3V3', GND, p)
        resistor(c, '0', 'ARMED', 'TZ_TRIP', p, note='Card trip-zone input: low = trip (latch cleared)')
        tp(c, 'TRIPPED', p)
        tp(c, 'ALL_GOOD', p)
        tp(c, 'PWM_ENABLE', p)
    p = '05_analog'
    with c.block('receivers', 'Differential receivers (gain 1.5) for the isolated voltage signals and buffers for the Hall outputs'):
        amp = {4: '5V0', 11: GND}
        for tag, (out, minus, plus) in zip(('P', 'S'), ((1, 2, 3), (7, 6, 5))):
            amp.update({out: f'{tag}_VBUS_RX', minus: f'{tag}_VM', plus: f'{tag}_VA'})
            for value, a, b in (('10k', f'{tag}_VSNS_N', f'{tag}_VM'), ('15k', f'{tag}_VBUS_RX', f'{tag}_VM'), ('10k', f'{tag}_VSNS_P', f'{tag}_VA'), ('15k', f'{tag}_VA', GND)):
                resistor(c, value, a, b, p, precision=True)
            cap(c, '100p/50V/0603', f'{tag}_VBUS_RX', f'{tag}_VM', p)
            cap(c, '100p/50V/0603', f'{tag}_VA', GND, p)
        amp.update({8: 'P_ISNS_BUF', 9: 'P_ISNS_BUF', 10: 'P_ISNS', 14: 'S_ISNS_BUF', 13: 'S_ISNS_BUF', 12: 'S_ISNS'})
        ic(c, 'OPA4192IPWR', amp, p, note='A/B: 1.5 x differential receivers (1.574 V at nominal bus -> 2.36 V); C/D: unity buffers for the Hall outputs')
        cap(c, '100n/50V/0603', '5V0', GND, p)
        cap(c, '1u/50V/0805', '5V0', GND, p)
    with c.block('adc_conditioning', 'ADC input RC and Schottky clamps (0.22 us, 3.3 V rails)'):
        channels = [('P_VBUS_RX', 'ADC_VBUS_P'), ('S_VBUS_RX', 'ADC_VBUS_S'), ('P_ISNS_BUF', 'ADC_ITANK_P'), ('S_ISNS_BUF', 'ADC_ITANK_S'),
                    ('P_TEMP_HS', 'ADC_TEMP_P'), ('S_TEMP_HS', 'ADC_TEMP_S'), ('V12_DIV', 'ADC_V12'), ('V5_DIV', 'ADC_5V')]
        for raw, adc in channels:
            resistor(c, '220', raw, adc, p)
            cap(c, '1n/50V/0603', adc, GND, p)
            ic(c, 'BAT54,215', {1: adc, 3: '3V3'}, p, prefix='D')
            ic(c, 'BAT54,215', {1: GND, 3: adc}, p, prefix='D')
        resistor(c, '43k', '12V_E', 'V12_DIV', p, precision=True)
        resistor(c, '10k', 'V12_DIV', GND, p, precision=True)
        resistor(c, '10k', '5V0', 'V5_DIV', p, precision=True)
        resistor(c, '10k', 'V5_DIV', GND, p, precision=True)
    with c.block('digital_io', 'Series terminations of the harness digital signals'):
        for tag in ('P', 'S'):
            for s in ('AH', 'AL', 'BH', 'BL'):
                resistor(c, '33', f'{tag}_TEMP_PWM_{s}', f'TEMP_PWM_{tag}_{s}', p)
            resistor(c, '33', f'SDFM_{tag}_CLK', f'{tag}_SDFM_CLK', p)
            resistor(c, '33', f'{tag}_SDFM_D', f'SDFM_{tag}_D', p)
        resistor(c, '33', 'DRV_RST_MCU', 'DRV_RST', p)
        resistor(c, '33', 'BIAS_EN_MCU', 'BIAS_EN', p)
        resistor(c, '0', 'NRST', 'XRS_CARD', p, note='Supervisor reset to the card reset line (open-drain both sides)')
    p = '06_comms'
    with c.block('can', 'CAN FD transceiver with split termination and ESD protection'):
        can = comp['communications']['can_transceiver']
        ic(c, can['mpn'], {1: 'CAN_TX', 2: GND, 3: '5V0', 4: 'CAN_RX', 5: '3V3', 6: 'CANL', 7: 'CANH', 8: GND}, p, note='STB low = normal mode; VIO 3.3 V, VCC 5 V')
        cap(c, '100n/50V/0603', '5V0', GND, p)
        cap(c, '100n/50V/0603', '3V3', GND, p)
        resistor(c, '60.4', 'CANH', 'CAN_MID', p, precision=True)
        resistor(c, '60.4', 'CANL', 'CAN_MID', p, precision=True)
        cap(c, '4.7n/50V/0603', 'CAN_MID', GND, p, note='Split termination; remove the resistors when the node is not a bus end')
        c.add('D', 'PESD1CAN', 'Package_TO_SOT_SMD:SOT-23', {1: 'CANH', 2: 'CANL', 3: GND}, page=p, kind='D', mpn='PESD1CAN,215', maker='Nexperia',
              source='https://assets.nexperia.com/documents/data-sheet/PESD1CAN.pdf', definitions=pin_defs('1:IO1:passive 2:IO2:passive 3:GND:passive'),
              note='Pinout transcribed (IO1, IO2, common cathode GND) - verify')
        canj = iface['can']
        c.add('J', 'CAN BUS', canj['connector_footprint'], {1: 'CANH', 2: 'CANL', 3: GND}, page=p, kind='J', mpn=canj['connector_mpn'], maker='Phoenix Contact',
              source='https://www.phoenixcontact.com/en-pc/products/1803581', ref='J5')
    with c.block('rs485', 'Optional RS-485 half duplex (not populated)'):
        rs = comp['communications']['rs485_transceiver']
        ic(c, rs['mpn'], {1: 'RS485_RX', 2: 'RS485_DE', 3: 'RS485_DE', 4: 'RS485_TX', 5: GND, 6: 'RS485_A', 7: 'RS485_B', 8: '3V3'}, p, dnp=True,
           note='Receiver enable tied to the driver enable (half duplex)')
        cap(c, '100n/50V/0603', '3V3', GND, p, dnp=True)
        resistor(c, '120', 'RS485_A', 'RS485_B', p, dnp=True)
        rsj = iface['rs485']
        j = c.add('J', 'RS-485', rsj['connector_footprint'], {1: 'RS485_A', 2: 'RS485_B', 3: GND}, page=p, kind='J', mpn=rsj['connector_mpn'], maker='Phoenix Contact',
                  source='https://www.phoenixcontact.com/en-pc/products/1803581', ref='J6', dnp=True)
    with c.block('jtag', 'TI 14-pin JTAG / cJTAG header (card debug contacts ASSUMED)'):
        jt = iface['jtag_header']
        pins = {str(k): v for k, v in jt['pins'].items()}
        c.add('J', 'JTAG 14-pin', jt['footprint'], pins, page=p, kind='J', mpn='TSW-107-07-G-D', maker='Samtec', source='https://www.samtec.com/products/tsw', ref='J7',
              note='Pin 6 removed as key; TCK on pins 9 and 11 (TCK return)')
    p = '07_interface'
    with c.block('harnesses', 'Keyed 40-way harness headers to the primary and secondary power boards'):
        term = comp['terminals']
        for ref, prefix, name in (('J2', 'P', 'PRIMARY POWER BOARD'), ('J3', 'S', 'SECONDARY POWER BOARD')):
            c.add('J', f'{name} harness', term['harness_footprint'], _harness_nets(req, prefix), page=p, kind='J', mpn=term['harness_mpn'], maker=term['harness_maker'],
                  source=term['harness_source'], ref=ref, note=iface['control_harness']['keying'])
        for _ in range(2):
            cap(c, '10u/25V/1210', '12V_E', GND, p)
        cap(c, '10u/25V/1210', '3V3', GND, p)
    with c.block('indicators', 'Status indicators'):
        for name, net, drive in (('PWR', 'LED_PWR_K', '3V3'), ('RUN', 'LED_RUN_K', 'GPIO_LED_RUN'), ('FAULT', 'LED_FAULT_K', 'TRIPPED')):
            c.add('D', f'LED {name}', 'LED_SMD:LED_0805_2012Metric', {1: net, 2: drive}, page=p, kind='D', mpn='LTST-C170KGKT' if name != 'FAULT' else 'LTST-C170KRKT',
                  maker='Lite-On', source='https://optoelectronics.liteon.com/en-global/led/LED-Component/Detail/926', definitions=pin_defs('1:K:passive 2:A:passive'))
            resistor(c, '1.5k', net, GND, p)
        for net in ('5V0', '3V3', GND):
            tp(c, net, p)
    mounts(c, p, len(req.floorplans['control']['mounting_holes']))
    return c


def flag_nets(circuit: Circuit) -> list:
    """PWR_FLAG nets: supplies with power_in pins and no power_out, plus the hazardous rails (ERC provenance only)."""
    nets = {n for p in circuit.parts for n in p['nets'].values() if n}
    if circuit.side == 'control':
        return [n for n in ('12V_IN', '5V0', 'GND_CTRL') if n in nets]
    flags = ['BUS_P', 'PGND', '12V_E', '3V3', 'GND_CTRL', 'S_5V']
    flags += [f'KS_{t}' for t in TAGS] + [f'GNDP_{t}' for t in TAGS] + [f'12V_BIAS_{t}' for t in TAGS] + ['GNDP_S', '12V_BIAS_S']
    return [n for n in flags if n in nets]


def build(req, board: str) -> Circuit:
    return control(req) if board == 'control' else power(req, board)
