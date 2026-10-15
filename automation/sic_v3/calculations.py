"""Reproducible V3 sizing; analytical estimates, never hardware measurements."""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'examples/sic-buck-400v-200v-5kw-v3/calculations'
FS = 50_000.0
VO = 200.0

def magnetic(current, *, cores=4, turns=28, al_factor=1.0, temperature=100.0):
    """Magnetics High Flux 60u typical fit; source coefficients are not guaranteed bounds."""
    field = 0.4 * math.pi * turns * abs(current) / 12.5
    mu_fraction = 1 / (0.01 + 6.413e-8 * field ** 2.291) / 100
    inductance = cores * 138e-9 * turns**2 * al_factor * mu_fraction
    # Geometric winding estimate, separately qualified against a wound sample.
    mlt = 2 * (cores * 16.13 + (58.04 - 25.58) / 2 + 6.0) / 1000
    length = turns * mlt + 0.25
    rdc = 1.724e-8 * (1 + .00393 * (temperature - 20)) * length / 5.26e-6
    return dict(L_H=inductance, H_Oe=field, relative_permeability=mu_fraction,
                wire_length_m=length, Rdc_ohm=rdc, MLT_m=mlt)

def operating_point(vin, current=25.0, *, al_factor=1.0):
    duty = VO / vin
    peak = current
    for _ in range(30):
        mag = magnetic(peak, al_factor=al_factor)
        ripple = VO * (1-duty) / (mag['L_H'] * FS)
        peak = current + ripple/2
    rms2 = current**2 + ripple**2/12
    bpk = VO * (1-duty) / (2 * 28 * 4 * 229e-6 * FS)
    # Triangular waveform and DC-bias correction are assumptions, not catalogue guarantees.
    pcore = 246.54 * bpk**2.218 * (FS/1000)**1.311 * (4*28.6) / 1000 * 1.30
    pdc = current**2 * mag['Rdc_ohm']
    pac = 6.0 * mag['Rdc_ohm'] * ripple**2/12
    # 33 mOhm guaranteed at 25 C, scaled by typical 175 C / 25 C ratio: conservative screen, not a hot max.
    rds_hot = .033 * (47/25) * 1.10  # extra assumption for17.17V nominal bias below18V data condition
    cond_h = rms2*rds_hot*duty
    cond_l = rms2*rds_hot*(1-duty)
    # Only HS hard switching in positive-current buck CCM. Eon includes reverse recovery.
    sw_h = (470+64)*1e-6*(vin/800)*(current/39.2)*FS*2.5
    dead_loss = 2*300e-9*FS*current*4.6
    fet_total = cond_h+cond_l+sw_h+dead_loss
    cin_rms = math.sqrt(current**2*duty*(1-duty) + ripple**2*duty/12)
    cout_rms = ripple/math.sqrt(12)
    cap_loss = cin_rms**2*(.0091/4) + cout_rms**2*(.0043/2)
    # Provisional copper resistance; replaced with actual path screening after routing.
    copper = 2.5
    auxiliary = 12.0  # includes digital logic, bias and fan; contactor holding power is separately counted
    contactor_hold = 1.7
    bleeders = vin**2/364_000 + VO**2/172_000
    total = fet_total+pcore+pdc+pac+cap_loss+copper+auxiliary+contactor_hold+bleeders
    # Shared heatsink target 0.35 K/W, interface target 0.5 K/W/device, Rjc typical 0.41.
    sink = 40 + fet_total*.35
    p_h = cond_h+sw_h
    p_l = cond_l+dead_loss
    return dict(vin_V=vin, current_A=current, duty=duty, L_at_peak_uH=mag['L_H']*1e6, ripple_pp_A=ripple,
                peak_A=peak, rms_A=math.sqrt(rms2), flux_ac_peak_T=bpk,
                input_cap_rms_A=cin_rms, output_cap_rms_A=cout_rms,
                output_ripple_bound_V=ripple/(8*FS*180e-6)+ripple*(.0043/2),
                dc_link_ripple_V=current*duty*(1-duty)/(54e-6*FS),
                losses_W=dict(fet_h_conduction=cond_h, fet_l_conduction=cond_l, hs_switching=sw_h,
                    dead_time=dead_loss, core=pcore, winding_dc=pdc, winding_ac=pac, capacitors=cap_loss,
                    provisional_copper=copper, auxiliary=auxiliary, contactor=contactor_hold, bleeders=bleeders, total=total),
                efficiency_estimate_percent=100*(VO*current)/(VO*current+total),
                heatsink_target_C=sink, junction_h_estimate_C=sink+p_h*(.5+.41),
                junction_l_estimate_C=sink+p_l*(.5+.41))

def gate_bias():
    vtot=2.5*(1+121/16.2)
    vn=2.5*(1+9.76/16.2)
    vp=vtot-vn
    # Effective capacitance assumptions at DC bias: C2 2.2u, C3 10u, +/-30% imbalance envelope.
    c2,c3,tol=2.2e-6,10e-6,.30
    qg=125e-9*1.25  # typical Qg plus engineering margin
    ratio=c3/(c2+c3)
    imbal_h=abs(c3*(1+tol)/(c3*(1+tol)+c2*(1-tol))-ratio)*qg*FS
    imbal_l=abs(c2*(1+tol)/(c2*(1+tol)+c3*(1-tol))-(1-ratio))*qg*FS
    iq=12e-3  # deliberately bounds driver+DESAT asymmetry; not a claimed IC max
    rint=60.0  # stress assumption, TI only specifies 30 ohm typical
    rh=vp/(imbal_h+iq)-rint
    rl1=vn/(imbal_l+iq)-rint
    rl2=vn/(c3*(1+tol)*.1*vn/.003+iq)-rint
    # RDR asymmetric charge/discharge network: 1k || diode+180R; verify source and sink separately.
    r1,r2,vf=1000.,180.,.5
    source=vp/(r1+rint)
    sink=vn/(r1+rint)+(vn-vf)/(r2+rint)
    return dict(positive_V=vp, negative_V=-vn, total_V=vtot, Qg_screen_C=qg,
                C2_effective_F=c2,C3_effective_F=c3, capacitance_imbalance_fraction=tol,
                quiescent_asymmetry_assumption_A=iq, internal_R_stress_assumption_ohm=rint,
                source_required_A=imbal_h+iq,sink_required_A=imbal_l+iq,
                transient_sink_required_A=c3*(1+tol)*.1*vn/.003+iq,
                single_resistor_upper_bounds_ohm=[rh,rl1,rl2],RDR_R1_ohm=r1,RDR_R2_ohm=r2,
                source_available_A=source,sink_available_A=sink,
                source_margin=source/(imbal_h+iq),sink_margin=sink/max(imbal_l+iq,c3*(1+tol)*.1*vn/.003+iq),
                R1_loss_screen_W=vp**2/r1*.33+(imbal_l+iq)**2*r1*(r2/(r1+r2))**2,
                R2_loss_screen_W=(imbal_l+iq)**2*r2,
                gate_power_W=qg*vtot*FS,selected_resistor_ratings_W=[.66,.66],
                positive_static_max_V=2.5325*(1+121*1.001/(16.2*.999))-2.4675*(1+9.76*.999/(16.2*1.001)),
                positive_static_min_V=2.4675*(1+121*.999/(16.2*1.001))-2.5325*(1+9.76*1.001/(16.2*.999)))

def protection():
    cmax=60e-6*1.1+8*.47e-6*1.2  # film and nominal MLCC tolerance, no DC-bias credit for discharge
    rmax=2200*1.01
    raw=440
    # Include permanent bleeder and three 3.01 M equivalent sensing branches as a pessimistic shunt.
    leakage=1/(1/364000+3/3010000)
    final=raw*leakage/(leakage+rmax)
    tau=(rmax*leakage/(rmax+leakage))*cmax
    t8=-tau*math.log(1-(raw-8)/final)
    return dict(precharge_R_ohm=2200,precharge_resistor='Ohmite HS100 2K2 F',
                initial_current_A=raw/(2200*.99),initial_power_W=raw**2/(2200*.99),
                stored_energy_J=.5*cmax*raw**2,short_fault_energy_1s_J=raw**2/(2200*.99),
                precharge_final_V=final,precharge_to_8V_difference_s=t8,timeout_s=1.0,
                close_residual_energy_J=.5*cmax*8**2,
                dc_link_discharge_s=cmax*364000*1.05*math.log(raw/60),
                output_discharge_s=220e-6*172000*1.05*math.log(225/60),
                main_contactor='TE EV200HAANA',precharge_contactor='TE EV200HAANA',
                coil_inrush_each_A=3.8,coil_inrush_max_ms=130,coil_hold_each_W=1.7,
                aux_contact_wetting_A_at_10V8=10.8/100,aux_contact_wetting_W_at_13V2=13.2**2/100,
                current_trip_nominal_A=[-38,38],current_fault_gate_off_target_us=8,
                inductor_min_L_to_60A_H=4*138e-9*28**2*.92*.5,
                peak_after_8us_bound_A=38+2.4+440*8e-6/(4*138e-9*28**2*.92*.5),
                source_fuse='Littelfuse KLKD020; cable/fire protection, semiconductor I2t coordination unqualified')

def sensing():
    return dict(current_sensor='LEM HO 50-S-0100',sensitivity_V_per_A=.016,reference_buffer_required=True,
                adc_zero_V=1.5,conditioning_gain=2.,adc_slope_V_per_A=.032,
                adc_current_range_A=[-46.875,46.875],adc_resolution_A=3/4096/.032,
                output_at_minus38_0_plus38_V=[.284,1.5,2.716],sensor_bandwidth_Hz=100000,
                sensor_delay_90pct_typ_us=3.5,sensor_delay_max_us=None,
                current_error_25C_A=.0125*50,current_error_105C_A=.048*50,
                raw_and_bus_ratio=1.5/301,output_ratio=1.5/151,
                max_bus_adc_V=440*1.5/301,nominal_output_adc_V=200*1.5/151,
                amc_load_max_A=3*.0097+.001,midrail_RLIM_ohm=82,
                midrail_min_source_A=4.9/(82*1.01+60),midrail_internal_R_bound='60 ohm stress assumption, not a guaranteed maximum')

def calculate():
    return dict(evidence_level='analytical; manufacturer limits distinguished from stated modelling assumptions',
                corners=[operating_point(v,i,al_factor=a) for v in (360,400,440) for i in (25,30) for a in (.92,1.0,1.08)],
                magnetic_sweep=[dict(current_A=i,**magnetic(i)) for i in (0,12.5,25,30,36,45,55,65)],
                alternative_magnetics=[dict(cores=n,turns=t,**magnetic(25,cores=n,turns=t)) for n,t in ((2,34),(3,28),(4,24),(4,28))],
                gate_bias=gate_bias(),protection=protection(),sensing=sensing())

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    data=calculate()
    (OUT/'results.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    rows=['| Vin | Iout | AL factor | L at peak | ripple | peak | loss | efficiency | HS Tj |',
          '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for idx,c in enumerate(data['corners']):
        a=(.92,1.0,1.08)[idx%3]
        rows.append(f"| {c['vin_V']:.0f} V | {c['current_A']:.0f} A | {a:.2f} | {c['L_at_peak_uH']:.1f} uH | {c['ripple_pp_A']:.2f} A | {c['peak_A']:.2f} A | {c['losses_W']['total']:.1f} W | {c['efficiency_estimate_percent']:.2f}% | {c['junction_h_estimate_C']:.1f} C |")
    (OUT/'electrical_design.md').write_text('# V3 reproducible electrical sizing\n\nRun `python -m automation.sic_v3.calculations`. Full numeric precision and assumptions: `results.json`. These are analytical estimates, not measurements or guaranteed efficiency.\n\n'+'\n'.join(rows)+'\n\nThe ripple iteration evaluates inductance at the current peak, rather than using only its DC operating value. Load current, AL tolerance and all three input corners are independent sweep axes.\n',encoding='utf-8')
    print(json.dumps({'worst_rated':max((c for c in data['corners'] if c['current_A']==25),key=lambda c:c['ripple_pp_A']),
                      'bias':data['gate_bias'],'protection':data['protection']},indent=2))

if __name__=='__main__':
    main()
